import unittest
from pathlib import Path

HTML = (Path(__file__).resolve().parents[1] / "player" / "index.html").read_text(encoding="utf-8")


class VoicePhraseParserTests(unittest.TestCase):
    """Guards the tolerant parser for transcripts from Android's recognizer.

    The real phrase that failed on the device was "coloque o volume em 40%".
    """

    def test_volume_accepts_imperative_article_and_preposition(self):
        self.assertIn("(?:(?:coloca|coloque|colocar|poe|ponha|deixa|deixe|deixar|ajusta|ajuste|ajustar|muda|mude|mudar|bota|bote|botar)\\s+)?(?:o\\s+)?(?:volume|som)(?:\\s+(?:em|para|pra|a|no|na|ao|de))?", HTML)
        self.assertIn("minimo:0,maximo:100", HTML)

    def test_volume_can_step_up_and_down(self):
        self.assertIn("^(aumenta|aumente|aumentar|sobe|suba|subir|abaixa|abaixe|abaixar|baixa|baixe|baixar|diminui|diminua|diminuir)", HTML)
        self.assertIn("Math.max(0,Math.min(100,Number(control.value)+(/^(aum|sob|sub)/.test(step[1])?10:-10)))", HTML)

    def test_courtesy_and_wake_word_are_ignored(self):
        self.assertIn(".replace(/^(?:(?:ok|ei|oi|hey|ola|por favor)\\s+)+/,'')", HTML)
        self.assertIn(".replace(/\\s+por favor$/,'')", HTML)

    def test_station_names_tolerate_recognizer_spellings(self):
        self.assertIn(".replace(/^a(?:g+|j|gu)il+[ei]/,'aggilli')||'aggilli'", HTML)
        self.assertIn("buttons.find(item=>stationKey(item.title)===stationKey(target))", HTML)

    def test_generic_verbs_need_radio_keyword(self):
        self.assertIn("(?:toque|toca|tocar|ouvir|ouca|abre|abra|abrir|liga|ligue|ligar|coloca|coloque|colocar)\\s+(?:(?:a|o|na|no)\\s+)?(?:radio|estacao)\\b", HTML)

    def test_hidden_and_wide_characters_are_normalized(self):
        self.assertIn("text.normalize('NFKD').toLowerCase()", HTML)
        self.assertIn(".replace(/\\p{Cf}/gu,'')", HTML)

    def test_timer_accepts_infinitive(self):
        self.assertIn("^(?:desligue|desliga|desligar|pare|parar|temporizador|timer)", HTML)


if __name__ == "__main__":
    unittest.main()
