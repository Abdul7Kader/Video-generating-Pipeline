from __future__ import annotations

import tempfile
import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch
from urllib.parse import parse_qs

from backend import mastodon


class MastodonTests(unittest.TestCase):
    def test_base_url_requires_fixed_https_instance(self):
        self.assertEqual(mastodon.validate_base_url("https://social.example"), ("social.example", None))
        for invalid in ("http://social.example", "https://user:pass@social.example", "https://social.example/path"):
            with self.assertRaises(RuntimeError):
                mastodon.validate_base_url(invalid)

    def test_status_payload_is_bounded_and_contains_media(self):
        job = {"language": "de", "script": {"title": "Titel", "description": "x" * 1000}}
        with patch.object(mastodon, "settings", SimpleNamespace(mastodon_visibility="private")):
            payload = parse_qs(mastodon.build_status_payload(job, "media-1").decode())
        self.assertEqual(payload["media_ids[]"], ["media-1"])
        self.assertEqual(payload["visibility"], ["private"])
        self.assertLessEqual(len(payload["status"][0]), 480)

    def test_publish_uses_processed_media_and_stable_post_reference(self):
        with tempfile.TemporaryDirectory() as temp:
            video = Path(temp) / "video.mp4"
            video.write_bytes(b"x" * 10_000)
            job = {
                "id": "job-1",
                "language": "de",
                "output_sha256": "a" * 64,
                "approved_output_sha256": "a" * 64,
                "script": {"title": "Titel", "description": "Beschreibung"},
            }
            calls = []

            def request(method, path, **kwargs):
                calls.append((method, path, kwargs))
                if method == "GET":
                    return {"id": "media-1", "url": "https://social.example/media/1"}
                return {"id": "post-1", "url": "https://social.example/@creator/1"}

            with (
                patch.object(mastodon, "settings", SimpleNamespace(
                    mastodon_enabled=True,
                    mastodon_base_url="https://social.example",
                    mastodon_access_token="secret",
                    mastodon_visibility="private",
                )),
                patch.object(mastodon, "_upload_media", return_value={"id": "media-1", "url": None}),
                patch.object(mastodon, "_request_json", side_effect=request),
                patch.object(mastodon.time, "sleep"),
            ):
                result = mastodon.publish_video(job, video)

        self.assertEqual(result, ("post-1", "https://social.example/@creator/1"))
        post_headers = calls[-1][2]["headers"]
        self.assertEqual(post_headers["Idempotency-Key"], f"publish:v1:job-1:mastodon:{'a' * 64}")


if __name__ == "__main__":
    unittest.main()
