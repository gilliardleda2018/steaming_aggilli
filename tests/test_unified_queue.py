import unittest
from pathlib import Path

HTML = (Path(__file__).resolve().parents[1] / "player" / "index.html").read_text(encoding="utf-8")


class UnifiedQueueTests(unittest.TestCase):
    def test_one_player_with_queue_and_dj(self):
        for identifier in ('id="audio"', 'id="aggilliDjPanel"', 'id="aggilliQueuePanel"',
                           'id="aggilliQueueItems"', 'id="library"', 'id="radioBtn"'):
            with self.subTest(identifier=identifier):
                self.assertEqual(HTML.count(identifier), 1)

    def test_dj_queue_survives_library_render(self):
        self.assertIn("if(!aggilliDjQueueActive)playQueue=filtered.map(t=>t.track_id)", HTML)
        self.assertIn("aggilliDjQueueActive=true;", HTML)

    def test_return_to_library(self):
        self.assertIn("aggilliDjQueueActive=false;", HTML)
        self.assertIn("window.aggilliRenderQueue()", HTML)

    def test_queue_uses_existing_playback(self):
        self.assertIn("line.addEventListener('click',e=>{if(e.target.closest('button'))return;playTrack(track);})", HTML)
        self.assertIn("function refreshNow(){", HTML)

if __name__ == "__main__":
    unittest.main()
