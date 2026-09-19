from __future__ import annotations

import json
import os
import subprocess
import threading
import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch

from backend.antigravity import AntigravityError, _invoke_cli, generate_structured


SCHEMA = {
    "type": "object",
    "additionalProperties": False,
    "properties": {"answer": {"type": "string"}},
    "required": ["answer"],
}


def adapter_settings(**overrides):
    values = {
        "antigravity_enabled": True,
        "antigravity_command": "agy",
        "antigravity_model": "gemini-3.1-pro-high",
        "antigravity_effort": "high",
        "antigravity_timeout_seconds": 120,
    }
    values.update(overrides)
    return SimpleNamespace(**values)


class FakeProcess:
    def __init__(self, stdout: str, stderr: str = "", returncode: int = 0):
        self.stdout_value = stdout
        self.stderr_value = stderr
        self.returncode = returncode
        self.input = ""
        self.timeout = 0
        self.killed = False

    def communicate(self, input: str, timeout: int):
        self.input = input
        self.timeout = timeout
        return self.stdout_value, self.stderr_value

    def kill(self):
        self.killed = True


class TimeoutProcess(FakeProcess):
    def communicate(self, input: str, timeout: int):
        self.input = input
        self.timeout = timeout
        if not self.killed:
            raise subprocess.TimeoutExpired("agy", timeout)
        return "", ""


def success_stream(output: dict) -> str:
    return "\n".join([
        json.dumps({"event": "init", "init": {"cwd": "isolated", "tools": []}}),
        json.dumps({
            "event": "result",
            "result": {
                "conversation_id": "must-not-be-persisted",
                "status": "SUCCESS",
                "structured_output": output,
                "duration_seconds": 1.25,
                "usage": {"input_tokens": 12, "output_tokens": 7, "total_tokens": 19},
            },
        }),
    ]) + "\n"


class AntigravityAdapterTests(unittest.TestCase):
    def test_cli_receives_prompt_only_over_stdin_in_an_isolated_tool_restricted_run(self):
        process = FakeProcess(success_stream({"answer": "ok"}))
        with patch("backend.antigravity.settings", adapter_settings()), \
             patch("backend.antigravity.shutil.which", return_value=r"C:\tools\agy.exe"), \
             patch("backend.antigravity.subprocess.Popen", return_value=process) as start:
            result, metrics = _invoke_cli("private prompt", SCHEMA)

        args = start.call_args.args[0]
        cwd = Path(start.call_args.kwargs["cwd"])
        self.assertNotIn("private prompt", args)
        self.assertEqual(json.loads(process.input)["message"]["content"], "private prompt")
        self.assertIn("--input-format", args)
        self.assertIn("stream-json", args)
        self.assertIn("--json-schema", args)
        self.assertIn("--sandbox", args)
        self.assertIn("--mode", args)
        self.assertIn("plan", args)
        self.assertIn("--disable-slash-commands", args)
        self.assertIn("--log-file", args)
        self.assertEqual(args[args.index("--log-file") + 1], os.devnull)
        self.assertNotEqual(cwd, Path.cwd())
        self.assertFalse(cwd.exists())
        self.assertEqual(result, {"answer": "ok"})
        self.assertEqual(metrics["model"], "gemini-3.1-pro-high")
        self.assertEqual(metrics["total_tokens"], 19)
        self.assertNotIn("conversation_id", metrics)

    def test_tool_attempt_is_rejected_even_when_cli_reports_success(self):
        stream = "\n".join([
            json.dumps({"event": "step_update", "step_update": {"step_type": "tool", "tool_name": "run_command"}}),
            success_stream({"answer": "unsafe"}),
        ])
        process = FakeProcess(stream)
        with patch("backend.antigravity.settings", adapter_settings()), \
             patch("backend.antigravity.shutil.which", return_value="agy"), \
             patch("backend.antigravity.subprocess.Popen", return_value=process):
            with self.assertRaises(AntigravityError) as raised:
                _invoke_cli("do not use tools", SCHEMA)
        self.assertEqual(raised.exception.code, "policy_violation")
        self.assertNotIn("run_command", str(raised.exception))

    def test_timeout_kills_process_and_returns_a_sanitized_error(self):
        process = TimeoutProcess("")
        with patch("backend.antigravity.settings", adapter_settings(antigravity_timeout_seconds=45)), \
             patch("backend.antigravity.shutil.which", return_value="agy"), \
             patch("backend.antigravity.subprocess.Popen", return_value=process):
            with self.assertRaises(AntigravityError) as raised:
                _invoke_cli("secret topic", SCHEMA)
        self.assertTrue(process.killed)
        self.assertEqual(raised.exception.code, "timeout")
        self.assertNotIn("secret topic", str(raised.exception))

    def test_authentication_error_does_not_expose_cli_diagnostics(self):
        secret_diagnostic = "You are not logged into Antigravity token=private-session"
        stream = json.dumps({
            "event": "result",
            "result": {"status": "ERROR", "error": secret_diagnostic},
        })
        process = FakeProcess(stream, stderr=secret_diagnostic, returncode=1)
        with patch("backend.antigravity.settings", adapter_settings()), \
             patch("backend.antigravity.shutil.which", return_value="agy"), \
             patch("backend.antigravity.subprocess.Popen", return_value=process):
            with self.assertRaises(AntigravityError) as raised:
                _invoke_cli("topic", SCHEMA)
        self.assertEqual(raised.exception.code, "auth_required")
        self.assertNotIn("private-session", str(raised.exception))

    def test_invalid_stream_is_rejected_without_exposing_output(self):
        process = FakeProcess("not-json token=private-session")
        with patch("backend.antigravity.settings", adapter_settings()), \
             patch("backend.antigravity.shutil.which", return_value="agy"), \
             patch("backend.antigravity.subprocess.Popen", return_value=process):
            with self.assertRaises(AntigravityError) as raised:
                _invoke_cli("topic", SCHEMA)
        self.assertEqual(raised.exception.code, "invalid_response")
        self.assertNotIn("private-session", str(raised.exception))

    def test_process_launch_error_is_sanitized(self):
        with patch("backend.antigravity.settings", adapter_settings()), \
             patch("backend.antigravity.shutil.which", return_value="agy"), \
             patch("backend.antigravity.subprocess.Popen", side_effect=OSError("secret-user-path")):
            with self.assertRaises(AntigravityError) as raised:
                _invoke_cli("topic", SCHEMA)
        self.assertEqual(raised.exception.code, "unavailable")
        self.assertNotIn("secret-user-path", str(raised.exception))

    def test_identical_concurrent_requests_share_one_cli_run(self):
        entered = threading.Event()
        release = threading.Event()
        calls = []
        results = []

        def slow_invoke(_prompt, _schema):
            calls.append(True)
            entered.set()
            release.wait(timeout=2)
            return {"answer": "shared"}, {"model": "gemini-3.1-pro-high"}

        def run():
            results.append(generate_structured("same", SCHEMA))

        with patch("backend.antigravity.settings", adapter_settings()), \
             patch("backend.antigravity._invoke_cli", side_effect=slow_invoke):
            first = threading.Thread(target=run)
            second = threading.Thread(target=run)
            first.start()
            self.assertTrue(entered.wait(timeout=1))
            second.start()
            second.join(timeout=0.2)
            release.set()
            first.join(timeout=2)
            second.join(timeout=2)

        self.assertEqual(len(calls), 1)
        self.assertEqual(len(results), 2)
        self.assertEqual(results[0], results[1])


if __name__ == "__main__":
    unittest.main()
