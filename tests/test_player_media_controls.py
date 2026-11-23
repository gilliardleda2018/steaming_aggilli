import unittest
from pathlib import Path

HTML = (Path(__file__).resolve().parents[1] / "player" / "index.html").read_text(encoding="utf-8")


class PlayerMediaControlsTests(unittest.TestCase):
    def test_existing_player_remains_unified(self):
        for marker in ('id="audio"', 'id="radioBtn"', 'id="aggilliDjPanel"',
                       'id="aggilliQueuePanel"', 'id="aggilliSyncCloud"'):
            with self.subTest(marker=marker):
                self.assertEqual(HTML.count(marker), 1)

    def test_queue_can_reorder_and_remove(self):
        self.assertIn("Mover para cima", HTML)
        self.assertIn("Mover para baixo", HTML)
        self.assertIn("Remover da fila", HTML)
        self.assertIn("playQueue=playQueue.filter(id=>id!==track.track_id)", HTML)

    def test_removing_playing_track_stops_it(self):
        self.assertIn("if(currentTrackId===track.track_id&&playbackMode==='track'){stopAudio();currentTrackId=null;}", HTML)

    def test_media_session_supports_headset_controls(self):
        self.assertIn("/* AGGILLI_MEDIA_SESSION_V1 */", HTML)
        self.assertIn("media.setActionHandler(action,fn)", HTML)
        self.assertIn("previoustrack:()=>previousTrack()", HTML)
        self.assertIn("nexttrack:()=>nextTrack()", HTML)
        self.assertIn("if(!('mediaSession' in navigator)||!('MediaMetadata' in window))return;", HTML)

    def test_loading_status_clears_when_track_starts(self):
        self.assertIn("function markTrackPlaying(event){", HTML)
        self.assertIn("status.textContent==='Carregando faixa…')status.textContent='Reproduzindo'", HTML)
        self.assertIn("audio.addEventListener('playing',markTrackPlaying);", HTML)
        self.assertIn("cloudVideo.addEventListener('playing',markTrackPlaying);", HTML)

if __name__ == "__main__":
    unittest.main()
