import unittest
from pathlib import Path

PLAYER = Path(__file__).resolve().parents[1] / "player" / "index.html"


class IntegratedPlayerTests(unittest.TestCase):
    def test_player_shows_the_shared_release_version(self):
        version_file = PLAYER.parents[1] / "release.properties"
        release = dict(
            line.split("=", 1) for line in version_file.read_text(encoding="utf-8").splitlines()
        )
        self.assertIn(
            f'<span id="playerRelease">v{release["versionName"]}</span>',
            PLAYER.read_text(encoding="utf-8"),
        )

    def test_one_player_contains_dj_and_existing_features(self):
        html = PLAYER.read_text(encoding="utf-8")
        for marker in (
            'id="audio"', 'id="aggilliSpectrum"', 'id="aggilliSyncCloud"',
            'id="library"', 'id="aggilliDjPanel"', 'id="aggilliDjPrompt"',
            'id="aggilliDjResults"', 'function playTrack(track)',
        ):
            with self.subTest(marker=marker):
                self.assertIn(marker, html)

    def test_dj_uses_existing_player_queue(self):
        html = PLAYER.read_text(encoding="utf-8")
        self.assertIn('playQueue=ranked.map(x=>x.t.track_id)', html)
        self.assertIn('playTrack(ranked[0].t)', html)
        self.assertIn('playTrack(t)', html)

    def test_no_embedded_model_key_or_raw_audio_urls(self):
        html = PLAYER.read_text(encoding="utf-8")
        dj = html.split('/* AGGILLI_INTEGRATED_DJ_V1 */', 1)[-1]
        self.assertNotIn('AGGILLI_ANI_API_KEY', dj)
        self.assertNotIn('azuracast-api-key', dj)
        self.assertNotIn('download_url=', dj)

    def test_dj_panel_is_unique(self):
        html = PLAYER.read_text(encoding="utf-8")
        self.assertEqual(html.count('id="aggilliDjPanel"'), 1)


if __name__ == "__main__":
    unittest.main()
