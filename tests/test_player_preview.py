import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SCRIPT = (ROOT / "scripts" / "preview-unified-player.sh").read_text()


class PreviewSafetyTests(unittest.TestCase):
    def test_preview_is_separate_from_production(self):
        self.assertIn('PREVIEW="/var/www/aggilli-music-preview"', SCRIPT)
        self.assertIn('LIVE="/var/www/aggilli-music"', SCRIPT)
        self.assertIn('install -m 0644 "$SOURCE" "$PREVIEW/index.html"', SCRIPT)
        self.assertNotIn('"$LIVE/index.html"', SCRIPT)

    def test_localhost_only(self):
        self.assertIn('--bind 127.0.0.1', SCRIPT)

    def test_requires_existing_catalog(self):
        self.assertIn('! -f "$LIVE/catalogo.json"', SCRIPT)

    def test_does_not_restart_or_stop_services(self):
        self.assertNotIn('systemctl restart', SCRIPT)
        self.assertNotIn('systemctl stop', SCRIPT)
        self.assertNotIn('docker restart', SCRIPT)

if __name__ == "__main__":
    unittest.main()
