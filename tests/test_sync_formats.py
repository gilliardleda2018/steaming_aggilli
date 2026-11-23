import importlib.util
import shutil
import subprocess
import tempfile
import unittest
from pathlib import Path

PATH = Path(__file__).resolve().parents[1] / "integrations" / "nextcloud_azura" / "sync.py"
SPEC = importlib.util.spec_from_file_location("aggilli_nextcloud_sync_formats", PATH)
sync = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(sync)


class ImportableNameTests(unittest.TestCase):
    def test_accepts_audio_and_video_sources(self):
        for name in ("faixa.mp3", "clipe.mp4", "ESTL - Voyage voyage [wn1OPI6lwnY].m4a",
                     "HAUSER - Oblivion.M4A", "show ao vivo.webm"):
            with self.subTest(name=name):
                self.assertTrue(sync.importable(name))

    def test_skips_downloader_fragments_and_unfinished_files(self):
        for name in ("001_Goodbye Blue Sky (AI Music Video).f251.webm",
                     "001_Enigma Music 2026.f616.mp4",
                     "001_Enigma Music 2026.temp.mp4",
                     "Gentleman Dark Blues.f616.mp4.ytdl",
                     "faixa.part"):
            with self.subTest(name=name):
                self.assertFalse(sync.importable(name))

    def test_rejects_hidden_and_path_like_names(self):
        for name in ("", ".oculto.m4a", "pasta/faixa.mp3", "pasta\\faixa.mp3"):
            with self.subTest(name=name):
                self.assertFalse(sync.importable(name))


@unittest.skipUnless(shutil.which("ffmpeg"), "ffmpeg not installed")
class ConversionTests(unittest.TestCase):
    def test_m4a_and_webm_become_mp3(self):
        with tempfile.TemporaryDirectory() as td:
            for suffix, codec in ((".m4a", "aac"), (".webm", "libopus")):
                with self.subTest(suffix=suffix):
                    source = Path(td) / ("tom" + suffix)
                    subprocess.run(
                        ["ffmpeg", "-nostdin", "-loglevel", "error", "-y", "-f", "lavfi",
                         "-i", "sine=frequency=440:duration=1", "-c:a", codec, str(source)],
                        check=True,
                    )
                    target = Path(td) / ("tom" + suffix + ".mp3")
                    sync.convert_to_mp3(source, target)
                    self.assertGreater(target.stat().st_size, 1000)
                    self.assertIn(target.read_bytes()[:3], (b"ID3", b"\xff\xfb", b"\xff\xf3"))


if __name__ == "__main__":
    unittest.main()
