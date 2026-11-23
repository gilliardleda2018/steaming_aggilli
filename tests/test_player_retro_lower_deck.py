import unittest
from pathlib import Path

HTML = (Path(__file__).resolve().parents[1] / "player" / "index.html").read_text(encoding="utf-8")
DECK = HTML.split("/* AGGILLI_RETRO_LOWER_DECK_V1", 1)[1].split("</style>", 1)[0]


class RetroLowerDeckTests(unittest.TestCase):
    def test_lower_panels_reuse_the_receiver_materials(self):
        for token in ("var(--metal)", "var(--switch)", "var(--glass)", "ui-monospace"):
            with self.subTest(token=token):
                self.assertIn(token, DECK)

    def test_every_lower_panel_is_covered(self):
        for panel in ("#aggilliDjPanel", "#aggilliQueuePanel", "#aggilliSyncCloudPanel", "#aggilliUploadPanel",
                      ".genre-card", ".library-views button", ".list-head", "#search"):
            with self.subTest(panel=panel):
                self.assertIn(panel, DECK)

    def test_deck_styles_load_last_so_they_win(self):
        self.assertLess(HTML.index("AGGILLI_RETRO_LOWER_DECK_V1"), HTML.index("</head>"))
        self.assertGreater(HTML.index("AGGILLI_RETRO_LOWER_DECK_V1"), HTML.index("Rotary controls on the aluminum faceplate"))


if __name__ == "__main__":
    unittest.main()
