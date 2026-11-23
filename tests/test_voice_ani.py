import re
import unittest
from pathlib import Path

HTML = (Path(__file__).resolve().parents[1] / "player" / "index.html").read_text(encoding="utf-8")


def js_regex(name):
    source, flags = re.search(r"const " + name + r"=/(.+?)/(i?);\n", HTML).groups()
    return re.compile(source, re.IGNORECASE if flags else 0)


ANI_CALL = js_regex("aniCall")      # roda sobre o texto já normalizado (sem acentos, minúsculo)
ANI_PREFIX = js_regex("aniPrefix")  # roda sobre a frase original, para manter acentos no pedido


class VoiceToAniTests(unittest.TestCase):
    def test_spoken_requests_reach_the_ani(self):
        for heard, normalized in [
            ("ANI, uma hora de som pesado para dirigir", "ani uma hora de som pesado para dirigir"),
            ("Annie meia hora de MPB sem repetir", "annie meia hora de mpb sem repetir"),
            ("peça à ANI algo calmo para estudar", "peca a ani algo calmo para estudar"),
            ("DJ, forró para a festa", "dj forro para a festa"),
        ]:
            with self.subTest(heard=heard):
                self.assertIsNotNone(ANI_CALL.match(normalized))
                request = ANI_PREFIX.sub("", heard, count=1)
                self.assertFalse(re.match(r"(?i)(ani|annie|dj|peça)\b", request), request)
                self.assertTrue(request[0].isalnum())

    def test_player_commands_are_not_sent_to_the_ani(self):
        for normalized in ("volume em 40", "proxima faixa", "sintonize aggilli", "pausa", "animado"):
            with self.subTest(normalized=normalized):
                self.assertIsNone(ANI_CALL.match(normalized))

    def test_ani_panel_has_its_own_microphone(self):
        self.assertIn('id="aggilliDjMic"', HTML)
        self.assertIn("aniMic.addEventListener('click',()=>listen(aniMic,", HTML)
        # A ponte nativa do APK entrega o texto ao microfone que começou a escuta.
        self.assertIn("target.onText(data.text.trim())", HTML)


if __name__ == "__main__":
    unittest.main()
