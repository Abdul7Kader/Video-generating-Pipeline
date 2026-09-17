from __future__ import annotations

import unittest
from pathlib import Path
from tempfile import TemporaryDirectory
from types import SimpleNamespace

from backend.publishing import configured_automatic_platforms, platform_catalog, profile_for
from backend.schemas import JobCreate


class PublishingCatalogTests(unittest.TestCase):
    def test_job_accepts_deduplicated_multiple_targets_and_keeps_legacy_field(self):
        job = JobCreate(
            topic="Mehrfach veröffentlichen",
            target_platform="youtube",
            target_platforms=["youtube", "mastodon", "youtube", "spotify_podcast"],
        )
        self.assertEqual(job.target_platform, "youtube")
        self.assertEqual(job.target_platforms, ["youtube", "mastodon", "spotify_podcast"])

    def test_catalog_distinguishes_api_rss_and_distributor_targets(self):
        self.assertEqual(profile_for("youtube")["delivery_mode"], "automatic")
        self.assertEqual(profile_for("apple_podcasts")["delivery_mode"], "rss")
        self.assertEqual(profile_for("spotify_music")["delivery_mode"], "distributor")
        self.assertEqual(profile_for("tiktok")["preferred_aspect_ratio"], "9:16")

    def test_only_fully_configured_automatic_targets_are_enabled(self):
        with TemporaryDirectory() as directory:
            secrets = Path(directory) / "client.json"
            token = Path(directory) / "token.json"
            secrets.write_text("{}", encoding="utf-8")
            token.write_text("{}", encoding="utf-8")
            settings = SimpleNamespace(
                youtube_enabled=True,
                youtube_client_secrets=secrets,
                youtube_token=token,
                mastodon_enabled=True,
                mastodon_base_url="https://social.example",
                mastodon_access_token="secret",
                mastodon_visibility="private",
            )
            self.assertEqual(configured_automatic_platforms(settings), {"youtube", "mastodon"})
            catalog = {item["id"]: item for item in platform_catalog(settings)}
            self.assertTrue(catalog["mastodon"]["configured"])
            self.assertFalse(catalog["tiktok"]["configured"])
            self.assertNotIn("secret", str(catalog))

            token.unlink()
            self.assertEqual(configured_automatic_platforms(settings), {"mastodon"})


if __name__ == "__main__":
    unittest.main()
