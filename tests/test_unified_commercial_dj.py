import unittest
from pathlib import Path

HTML = (Path(__file__).resolve().parents[1] / "player" / "index.html").read_text(encoding="utf-8")


class UnifiedCommercialDjTests(unittest.TestCase):
    def test_same_player_hosts_both_modes(self):
        for marker in ('id="audio"', 'id="aggilliDjPanel"',
                       'id="aggilliDjCommercial"', 'id="aggilliDjCommercialResults"',
                       'id="aggilliQueuePanel"', 'id="radioBtn"'):
            with self.subTest(marker=marker):
                self.assertEqual(HTML.count(marker), 1)

    def test_authenticated_dj_api_is_optional(self):
        self.assertIn("'/listeners/dj/session'", HTML)
        self.assertIn("base.protocol!=='https:'", HTML)
        self.assertIn("token.value.length<32", HTML)
        self.assertIn("redirect:'error'", HTML)

    def test_commercial_results_do_not_invoke_public_player(self):
        commercial = HTML.split('/* AGGILLI_UNIFIED_COMMERCIAL_DJ_V1 */', 1)[1]
        self.assertNotIn('playTrack(', commercial)
        self.assertNotIn('audio.src', commercial)
        self.assertNotIn('playQueue=', commercial)
        self.assertNotIn('innerHTML', commercial)

    def test_token_not_persisted(self):
        commercial = HTML.split('/* AGGILLI_UNIFIED_COMMERCIAL_DJ_V1 */', 1)[1]
        self.assertNotIn('localStorage', commercial)
        self.assertNotIn('sessionStorage', commercial)
        self.assertNotIn('AGGILLI_ANI_API_KEY', commercial)


if __name__ == "__main__":
    unittest.main()
