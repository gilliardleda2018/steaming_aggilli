import unittest
from datetime import date
from commercial.intelligence import interpret_intent, recommend

DATE = date(2026, 11, 22)
RIGHT = {
    "status": "approved", "license_type": "interactive_streaming",
    "agreement_reference": "TEST", "rights_holder": "Test",
    "recording_rights_confirmed": True, "composition_rights_confirmed": True,
    "territories": ["BR"], "valid_from": "2026-01-01", "valid_until": "2027-01-01",
}
TRACKS = [
    {"track_id": "a", "media": {"title": "Quiet Piano", "artist": "Alpha", "genre": "Instrumental"}},
    {"track_id": "b", "media": {"title": "Dance Energy", "artist": "Beta", "genre": "Electronic"}},
    {"track_id": "c", "media": {"title": "Focus Ambient", "artist": "Gamma", "genre": "Ambient"}},
    {"track_id": "d", "media": {"title": "Secret Ambient", "artist": "Delta", "genre": "Ambient"}},
]

class IntelligenceTests(unittest.TestCase):
    def test_pt_intents(self):
        self.assertEqual(interpret_intent("Quero trabalhar com foco"), "foco")
        self.assertEqual(interpret_intent("Algo tranquilo para relaxar"), "relaxar")
        self.assertEqual(interpret_intent("Surpreenda-me"), "descoberta")

    def test_no_rights_no_music(self):
        self.assertEqual(recommend(TRACKS, {}, "BR", today=DATE), [])

    def test_territory_and_revocation(self):
        rights = {"a": RIGHT, "b": {**RIGHT, "status": "revoked"}}
        self.assertEqual(recommend(TRACKS, rights, "US", today=DATE), [])
        self.assertEqual([x["track_id"] for x in recommend(TRACKS, rights, "BR", today=DATE)], ["a"])

    def test_focused_ranking(self):
        rights = {x["track_id"]: RIGHT for x in TRACKS}
        result = recommend(TRACKS, rights, "BR", mood="foco", today=DATE)
        self.assertIn(result[0]["track_id"], {"a", "c"})
        self.assertEqual(len(result), 4)
        self.assertTrue(all("download_url" not in x for x in result))

    def test_history_reduces_repeats(self):
        rights = {x["track_id"]: RIGHT for x in TRACKS}
        result = recommend(TRACKS, rights, "BR", mood="foco", history=["a"], today=DATE)
        self.assertEqual(result[0]["track_id"], "c")

    def test_duplicate_ids_deduplicated(self):
        rights = {"a": RIGHT}
        result = recommend([TRACKS[0], TRACKS[0]], rights, "BR", today=DATE)
        self.assertEqual(len(result), 1)

    def test_invalid_mood_and_limit(self):
        with self.assertRaises(ValueError):
            recommend(TRACKS, {}, "BR", mood="invalid")
        with self.assertRaises(ValueError):
            recommend(TRACKS, {}, "BR", limit=0)

if __name__ == "__main__":
    unittest.main()
