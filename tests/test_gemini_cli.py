from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path
from types import SimpleNamespace

from backend.gemini_cli import GeminiCliPool, parse_profile_names, provision_profile


class GeminiCliPoolTests(unittest.TestCase):
    def test_profile_names_are_deduplicated_and_path_traversal_is_rejected(self):
        self.assertEqual(parse_profile_names("primary,secondary,primary"), ("primary", "secondary"))
        with self.assertRaisesRegex(ValueError, "Profilname"):
            parse_profile_names("primary,..\\escape")

    def test_profile_provisioning_creates_tool_deny_policy_without_credentials(self):
        with tempfile.TemporaryDirectory() as temp:
            profile = provision_profile(Path(temp), "primary")
            settings = json.loads((profile / ".gemini" / "settings.json").read_text(encoding="utf-8"))
            policy = (profile / ".gemini" / "policies" / "pipeline-deny-all.toml").read_text(encoding="utf-8")
            self.assertEqual(settings["tools"]["core"], [])
            self.assertTrue(settings["security"]["disableYoloMode"])
            self.assertNotIn("output", settings)
            self.assertIn('toolName = "*"', policy)
            self.assertIn('decision = "deny"', policy)
            self.assertIn("priority = 999", policy)
            self.assertNotRegex(json.dumps(settings) + policy, r"(?i)token|password|cookie")

    def test_reprovisioning_does_not_overwrite_cli_managed_authentication_setting(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            profile = provision_profile(root, "primary")
            settings_path = profile / ".gemini" / "settings.json"
            settings = json.loads(settings_path.read_text(encoding="utf-8"))
            settings["security"]["auth"] = {"selectedType": "oauth-personal"}
            settings_path.write_text(json.dumps(settings), encoding="utf-8")
            provision_profile(root, "primary")
            preserved = json.loads(settings_path.read_text(encoding="utf-8"))
            self.assertEqual(preserved["security"]["auth"]["selectedType"], "oauth-personal")

    def test_successful_call_uses_stdin_isolated_home_and_empty_workspace(self):
        calls = []

        def run(command, **kwargs):
            calls.append((command, kwargs))
            return SimpleNamespace(
                returncode=0,
                stdout=json.dumps({"response": '{"ok":true}', "stats": {"models": {"gemini-test": {}}}}),
                stderr="",
            )

        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            provision_profile(root, "primary")
            pool = GeminiCliPool(("primary",), root, command="gemini-test-command", run_process=run)
            result = pool.generate("exact stored input")
            command, kwargs = calls[0]
            self.assertEqual(command, ["gemini-test-command", "--output-format", "json"])
            self.assertEqual(kwargs["input"], "exact stored input")
            self.assertNotIn("exact stored input", " ".join(command))
            self.assertEqual(Path(kwargs["cwd"]), root / "primary" / "workspace")
            self.assertEqual(kwargs["env"]["GEMINI_CLI_HOME"], str(root / "primary"))
            self.assertNotIn("GEMINI_API_KEY", kwargs["env"])
            self.assertEqual(result.profile, "primary")
            self.assertEqual(result.model, "gemini-test")
            self.assertEqual(result.response, '{"ok":true}')

    def test_quota_failure_cools_first_profile_and_restarts_same_input_on_second(self):
        inputs = []

        def run(_command, **kwargs):
            inputs.append(kwargs["input"])
            if len(inputs) == 1:
                return SimpleNamespace(returncode=1, stdout="", stderr="429 RESOURCE_EXHAUSTED Retry-After: 60")
            return SimpleNamespace(
                returncode=0,
                stdout=json.dumps({"response": "done", "stats": {"models": {"gemini-next": {}}}}),
                stderr="",
            )

        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            provision_profile(root, "primary")
            provision_profile(root, "secondary")
            pool = GeminiCliPool(("primary", "secondary"), root, run_process=run)
            result = pool.generate("immutable step input")
            states = {item["name"]: item for item in pool.statuses()}
            self.assertEqual(inputs, ["immutable step input", "immutable step input"])
            self.assertEqual(result.profile, "secondary")
            self.assertEqual(states["primary"]["status"], "cooldown")
            self.assertIsNotNone(states["primary"]["cooldown_until"])
            self.assertEqual(states["primary"]["last_error"], "quota_or_rate_limit")
            self.assertNotIn("remaining_tokens", states["primary"])

    def test_profile_state_survives_pool_restart_without_storing_cli_credentials(self):
        def fail(_command, **_kwargs):
            return SimpleNamespace(returncode=1, stdout="", stderr="401 UNAUTHENTICATED login required")

        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            provision_profile(root, "primary")
            pool = GeminiCliPool(("primary",), root, run_process=fail)
            with self.assertRaisesRegex(RuntimeError, "Kein Gemini-Profil"):
                pool.generate("input")
            restarted = GeminiCliPool(("primary",), root, run_process=fail)
            status = restarted.statuses()[0]
            self.assertEqual(status["status"], "needs_login")
            self.assertEqual(status["last_error"], "authentication")
            state_text = (root / "primary" / "pipeline-state.json").read_text(encoding="utf-8")
            self.assertNotRegex(state_text, r"(?i)credential|access_token|refresh_token|cookie")

    def test_official_cli_missing_auth_error_is_classified_as_needs_login(self):
        def fail(_command, **_kwargs):
            return SimpleNamespace(
                returncode=1,
                stdout=json.dumps({"error": {"message": "Please set an Auth method", "code": 41}}),
                stderr="",
            )

        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            provision_profile(root, "primary")
            pool = GeminiCliPool(("primary",), root, run_process=fail)
            with self.assertRaisesRegex(RuntimeError, "Kein Gemini-Profil"):
                pool.generate("input")
            self.assertEqual(pool.statuses()[0]["status"], "needs_login")
            self.assertEqual(pool.statuses()[0]["last_error"], "authentication")

    def test_deprecated_consumer_login_is_classified_as_access_denied(self):
        category, retry_after = GeminiCliPool._classify_failure(
            "This client is no longer supported for Gemini Code Assist for individuals."
        )
        self.assertEqual(category, "access_denied")
        self.assertIsNone(retry_after)


if __name__ == "__main__":
    unittest.main()
