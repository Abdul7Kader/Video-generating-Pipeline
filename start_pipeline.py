"""Start the local web server and open it after the health check succeeds."""

from __future__ import annotations

import http.client
import json
import os
import socket
import sys
import threading
import time
import webbrowser
from pathlib import Path


def _port() -> int:
    value = os.getenv("APP_PORT", "8080")
    if not value.isdecimal() or not 1024 <= int(value) <= 65535:
        raise ValueError("APP_PORT muss eine Zahl zwischen 1024 und 65535 sein.")
    return int(value)


def _pipeline_ready(port: int) -> bool:
    connection = http.client.HTTPConnection("127.0.0.1", port, timeout=2)
    try:
        connection.request("GET", "/api/health")
        response = connection.getresponse()
        if response.status != 200:
            return False
        data = json.loads(response.read(64 * 1024))
        return isinstance(data, dict) and data.get("status") == "ok" and "publication_platforms" in data
    except (OSError, ValueError, http.client.HTTPException):
        return False
    finally:
        connection.close()


def _port_in_use(port: int) -> bool:
    try:
        with socket.create_connection(("127.0.0.1", port), timeout=1):
            return True
    except OSError:
        return False


def _open_when_ready(port: int, url: str) -> None:
    deadline = time.monotonic() + 60
    while time.monotonic() < deadline:
        if _pipeline_ready(port):
            try:
                webbrowser.open(url)
            except webbrowser.Error:
                pass
            return
        time.sleep(0.5)


def main() -> int:
    try:
        import uvicorn
        from dotenv import load_dotenv
    except ImportError:
        print("Python-Abhängigkeiten fehlen. Siehe README.md im Projektordner.", file=sys.stderr)
        return 1
    load_dotenv(Path(__file__).resolve().with_name(".env"), override=False)
    try:
        port = _port()
    except ValueError as exc:
        print(exc, file=sys.stderr)
        return 2
    url = f"http://127.0.0.1:{port}/"
    if _pipeline_ready(port):
        print(f"Pipeline bereits gestartet: {url}")
        try:
            webbrowser.open(url)
        except webbrowser.Error:
            pass
        return 0
    if _port_in_use(port):
        print(f"Port {port} ist durch einen anderen Dienst belegt.", file=sys.stderr)
        return 1

    print(f"Starte die Pipeline lokal unter {url}")
    print("Zum Beenden dieses Fenster schließen oder Strg+C drücken.")
    threading.Thread(target=_open_when_ready, args=(port, url), daemon=True).start()
    uvicorn.run("backend.main:app", host="127.0.0.1", port=port)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
