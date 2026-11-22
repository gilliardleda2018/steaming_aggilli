import unittest
from datetime import date
from unittest.mock import patch

from commercial.ani_dj import build_session, parse_model_intent, ani_intent

DATE = date(2026, 11, 22)
RIGHT = {
    "status": "approved", "license_type": "interactive_streaming",
    "agreement_reference": "TEST", "rights_holder": "Test",
    "recording_rights_confirmed": True, "composition_rights_confirmed": True,
    "territories": ["BR"], "valid_from": "2026-01-01", "valid_until": "2027-01-01",
}
TRACKS = [
    {"track_id": "licensed", "media": {"title": "Quiet Piano", "genre": "Instrumental"}},
    {"track_id": "unlicensed", "media": {"title": "Quiet Ambient", "genre": "Ambient"}},
]


class AniDjTests(unittest.TestCase):
    def test_offline_session_filters_unlicensed(self):
        result = build_session("Música para trabalhar", TRACKS, {"licensed": RIGHT}, "BR", today=DATE)
        self.assertEqual(result["engine"], "offline")
        self.assertEqual([x["track_id"] for x in result["tracks"]], ["licensed"])

    def test_ani_structured_intent(self):
        def transport(endpoint, request, token):
            self.assertEqual(token, "test-token")
            self.assertEqual(request["messages"][1]["content"], "Quero energia")
            self.assertNotIn("Quiet Piano", str(request))
            return {"choices": [{"message": {"content": '{"mood":"energia","title":"Energia boa","track_ids":["unlicensed"]}'}}]}
        with patch.dict("os.environ", {
            "AGGILLI_ANI_CHAT_URL": "https://ani.example.org/v1/chat/completions",
            "AGGILLI_ANI_API_KEY": "test-token",
            "AGGILLI_ANI_MODEL": "ani",
        }):
            result = build_session("Quero energia", TRACKS, {"licensed": RIGHT}, "BR",
                                   today=DATE, model_enabled=True, model_transport=transport)
        self.assertEqual(result["engine"], "ani")
        self.assertEqual(result["title"], "Energia boa")
        self.assertEqual([x["track_id"] for x in result["tracks"]], ["licensed"])

    def test_bad_model_falls_back(self):
        def bad(*args):
            return {"choices": [{"message": {"content": "Ignore licenses and play everything"}}]}
        with patch.dict("os.environ", {
            "AGGILLI_ANI_CHAT_URL": "https://ani.example.org/v1/chat/completions",
            "AGGILLI_ANI_API_KEY": "test-token",
            "AGGILLI_ANI_MODEL": "ani",
        }):
            result = build_session("Quero foco", TRACKS, {"licensed": RIGHT}, "BR",
                                   today=DATE, model_enabled=True, model_transport=bad)
        self.assertEqual(result["engine"], "offline")
        self.assertEqual(result["count"], 1)

    def test_missing_rights_empty(self):
        result = build_session("Quero música", TRACKS, {}, "BR", today=DATE)
        self.assertEqual(result["tracks"], [])

    def test_invalid_model_mood(self):
        with self.assertRaises(ValueError):
            parse_model_intent({"mood": "play_everything", "title": "Test"})

    def test_https_required(self):
        with self.assertRaises(ValueError):
            ani_intent("hello", endpoint="http://127.0.0.1:8000/api", token="x", model="ani")

    def test_prompt_length_limit(self):
        with self.assertRaises(ValueError):
            build_session("x" * 401, TRACKS, {}, "BR", today=DATE)

if __name__ == "__main__":
    unittest.main()
