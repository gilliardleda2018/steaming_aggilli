import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
HTML = (ROOT / "player" / "index.html").read_text(encoding="utf-8")


class PlayerBrandAndClickTests(unittest.TestCase):
    def test_official_logo_in_player_header(self):
        self.assertRegex(HTML, r'src="aggilli-music-logo\.jpg(?:\?v=[\da-f]+)?"')
        self.assertIn('alt="Logomarca oficial Aggilli Music"', HTML)
        self.assertTrue((ROOT / "player" / "aggilli-music-logo.jpg").is_file())

    def test_library_row_clicks_play(self):
        self.assertIn('row.onclick=()=>playTrack(t)', HTML)

    def test_queue_row_clicks_play(self):
        self.assertIn("line.addEventListener('click',e=>{if(e.target.closest('button'))return;playTrack(track);})", HTML)

    def test_dj_row_clicks_play(self):
        self.assertIn("line.addEventListener('click',select)", HTML)
        self.assertIn("line.append(info);results.append(line)", HTML)

    def test_no_track_play_button_in_queue(self):
        queue = HTML.split("/* AGGILLI_UNIFIED_QUEUE_V1 */", 1)[1].split("</script>", 1)[0]
        self.assertNotIn("button.textContent='▶'", queue)

if __name__ == "__main__":
    unittest.main()
