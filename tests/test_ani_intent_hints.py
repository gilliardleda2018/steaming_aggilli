import re
import unittest
from pathlib import Path

from commercial.ani_dj import ANY_GENRE, PLAYER_GENRES, parse_model_intent

PLAYER = (Path(__file__).resolve().parents[1] / "player" / "index.html").read_text(encoding="utf-8")


class IntentHintTests(unittest.TestCase):
    def parse(self, **fields):
        return parse_model_intent({"mood": "energia", "title": "Pé na estrada", **fields})

    def test_genre_minutes_and_repeats_are_kept_when_valid(self):
        intent = self.parse(genre="Rock", minutes=60, avoid_repeats=True)
        self.assertEqual((intent["genre"], intent["minutes"], intent["avoid_repeats"]), ("Rock", 60, True))

    def test_unknown_or_any_genre_becomes_none(self):
        for genre in (ANY_GENRE, "Heavy Metal", "", None, 3):
            with self.subTest(genre=genre):
                self.assertIsNone(self.parse(genre=genre)["genre"])

    def test_out_of_range_or_non_integer_minutes_are_dropped(self):
        for minutes in (0, 4, 181, 30.5, "30", True, None):
            with self.subTest(minutes=minutes):
                self.assertIsNone(self.parse(minutes=minutes)["minutes"])

    def test_avoid_repeats_requires_literal_true(self):
        for value in ("true", 1, None):
            with self.subTest(value=value):
                self.assertFalse(self.parse(avoid_repeats=value)["avoid_repeats"])

    def test_query_is_plain_bounded_text(self):
        self.assertEqual(self.parse(query="  pink floyd ")["query"], "pink floyd")
        self.assertEqual(self.parse(query="a\nb\x00c")["query"], "a b c")
        self.assertEqual(len(self.parse(query="x" * 500)["query"]), 80)
        for value in (None, 3, ["pink floyd"], {"q": 1}):
            with self.subTest(value=value):
                self.assertEqual(self.parse(query=value)["query"], "")

    def test_server_genres_match_the_player_filter(self):
        names = re.search(r"const genreNames=\[([^\]]+)\]", PLAYER).group(1)
        player = [n.strip().strip("'") for n in names.split(",")]
        self.assertEqual(tuple(n for n in player if n not in ("Todos", "Outros")), PLAYER_GENRES)


if __name__ == "__main__":
    unittest.main()
