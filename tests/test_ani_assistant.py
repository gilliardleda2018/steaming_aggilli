import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
HTML = (ROOT / "player" / "index.html").read_text(encoding="utf-8")
ACTIVITY = (ROOT / "android/app/src/main/java/br/com/aggillintelligence/music/MainActivity.java").read_text(encoding="utf-8")
MANIFEST = (ROOT / "android/app/src/main/AndroidManifest.xml").read_text(encoding="utf-8")


class AniAssistantPlayerTests(unittest.TestCase):
    def test_named_artist_or_song_is_looked_up_in_the_catalog(self):
        self.assertIn("function catalogMatches(query){", HTML)
        self.assertIn("query:typeof intent.query==='string'?intent.query.slice(0,80):''", HTML)
        # Quando acha o nome, a seleção fica só com essas faixas.
        self.assertIn("foundIds.size?foundIds.has(t.track_id)", HTML)

    def test_ani_starts_playing_and_answers_spoken_requests_aloud(self):
        self.assertIn("if(spoken&&window.aggilliSpeak)window.aggilliSpeak(result.reply,result.play);", HTML)
        self.assertIn("else result.play();", HTML)
        self.assertIn("prompt.dataset.voice='1';", HTML)

    def test_speech_never_blocks_playback(self):
        self.assertIn("speechTimer=setTimeout(speechDone,9000);", HTML)
        self.assertIn("if(data?.type==='spoken'){speechDone();return;}", HTML)

    def test_play_requests_without_wake_word_go_to_the_ani(self):
        self.assertIn("askAni(raw,finish);\n  }else finish('Comando não reconhecido.');", HTML)


class AniAssistantAndroidTests(unittest.TestCase):
    def test_bridge_speaks_replies_in_brazilian_portuguese(self):
        self.assertIn('else if(data.startsWith("say:"))say(data.substring(4));', ACTIVITY)
        self.assertIn('speech.setLanguage(new Locale("pt","BR"))', ACTIVITY)
        self.assertIn('put("type","spoken")', ACTIVITY)
        self.assertIn('android.intent.action.TTS_SERVICE', MANIFEST)

    def test_spoken_requests_can_start_audio(self):
        self.assertIn("settings.setMediaPlaybackRequiresUserGesture(false);", ACTIVITY)

    def test_text_to_speech_is_released(self):
        self.assertIn("speech.shutdown();", ACTIVITY)


if __name__ == "__main__":
    unittest.main()
