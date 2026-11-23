import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
CONF = (ROOT / "infra" / "apache" / "aggilli-music-player-cache.conf").read_text(encoding="utf-8")
INSTALLER = (ROOT / "scripts" / "install-player-cache.sh").read_text(encoding="utf-8")


class PlayerCacheConfigTests(unittest.TestCase):
    def test_only_player_page_is_revalidated(self):
        self.assertIn('<LocationMatch "^/music/(index\\.html)?$">', CONF)
        self.assertIn('Header set Cache-Control "no-cache"', CONF)
        self.assertNotIn("no-store", CONF)

    def test_installer_validates_and_rolls_back(self):
        self.assertIn("if ! apache2ctl -t; then rollback; exit 1; fi", INSTALLER)
        self.assertIn("systemctl reload apache2", INSTALLER)
        self.assertNotIn("restart", INSTALLER)
        self.assertIn("grep -qi '^cache-control: no-cache'", INSTALLER)


if __name__ == "__main__":
    unittest.main()
