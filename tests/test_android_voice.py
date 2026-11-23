import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
ANDROID = ROOT / "android" / "app"
MANIFEST = (ANDROID / "src" / "main" / "AndroidManifest.xml").read_text(encoding="utf-8")
ACTIVITY = (ANDROID / "src" / "main" / "java" / "br" / "com" / "aggillintelligence" / "music" / "MainActivity.java").read_text(encoding="utf-8")
GRADLE = (ANDROID / "build.gradle").read_text(encoding="utf-8")
HTML = (ROOT / "player" / "index.html").read_text(encoding="utf-8")


class AndroidVoiceBridgeTests(unittest.TestCase):
    def test_manifest_requests_microphone_and_sees_recognizer(self):
        self.assertIn('android.permission.RECORD_AUDIO', MANIFEST)
        self.assertIn('<action android:name="android.speech.RecognitionService" />', MANIFEST)

    def test_bridge_is_limited_to_player_main_frame(self):
        self.assertIn("implementation 'androidx.webkit:webkit:", GRADLE)
        self.assertIn('private static final String ORIGIN="https://server.taila400aa.ts.net";', ACTIVITY)
        self.assertIn('WebViewCompat.addWebMessageListener(web,"AggilliVoice",Collections.singleton(ORIGIN),', ACTIVITY)
        self.assertIn("if(!isMainFrame||message.getData()==null)return;", ACTIVITY)
        self.assertNotIn("addJavascriptInterface", ACTIVITY)

    def test_native_recognizer_uses_portuguese_and_runtime_permission(self):
        self.assertIn('intent.putExtra(RecognizerIntent.EXTRA_LANGUAGE,"pt-BR");', ACTIVITY)
        self.assertIn("requestPermissions(new String[]{Manifest.permission.RECORD_AUDIO},MIC_REQUEST);", ACTIVITY)
        self.assertIn('else sendVoice("error","denied");', ACTIVITY)
        self.assertIn("@Override protected void onPause(){cancelVoice();super.onPause();}", ACTIVITY)

    def test_player_prefers_native_bridge_and_reuses_commands(self):
        self.assertIn("const nativeVoice=window.AggilliVoice;", HTML)
        self.assertIn("nativeVoice.postMessage('start');", HTML)
        self.assertIn("nativeVoice.postMessage('cancel');", HTML)
        self.assertLess(HTML.index("if(nativeVoice){nativeListening=true;"), HTML.index("if(!Recognition){report("))
        self.assertIn("if(data?.type==='result'&&typeof data.text==='string')target.onText(data.text.trim());", HTML)
        self.assertIn("onText:text=>{input.value=text.slice(0,100);execute(input.value);}", HTML)


if __name__ == "__main__":
    unittest.main()
