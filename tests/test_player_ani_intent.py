import os
import tempfile
import unittest
from unittest.mock import patch

from fastapi.testclient import TestClient

from commercial import listener_api
from commercial.listener_api import app

ORIGIN = {"Origin": "https://server.taila400aa.ts.net"}


class PlayerAniIntentTests(unittest.TestCase):
    def setUp(self):
        listener_api._player_calls.clear()
        self.data = tempfile.TemporaryDirectory()
        self.env = patch.dict(os.environ, {"AGGILLI_COMMERCIAL_DATA_DIR": self.data.name,
                                           "AGGILLI_ANI_ENABLED": "false"})
        self.env.start()
        self.client = TestClient(app)

    def tearDown(self):
        self.env.stop()
        self.data.cleanup()

    def test_player_gets_an_intent_without_a_listener_account(self):
        response = self.client.post("/player/dj/intent", json={"prompt": "algo calmo"}, headers=ORIGIN)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.headers["cache-control"], "private, no-store")
        body = response.json()
        self.assertEqual(body["engine"], "offline")
        self.assertNotIn("tracks", body)

    def test_other_origins_are_refused(self):
        for headers in ({}, {"Origin": "https://example.com"}, {"Origin": "http://server.taila400aa.ts.net"}):
            with self.subTest(headers=headers):
                response = self.client.post("/player/dj/intent", json={"prompt": "rock"}, headers=headers)
                self.assertEqual(response.status_code, 403)

    def test_quota_caps_calls_per_minute_and_day(self):
        self.assertEqual([listener_api.consume_player_quota(now=1000) for _ in range(12)], [0] * 12)
        self.assertGreater(listener_api.consume_player_quota(now=1000), 0)
        self.assertEqual(listener_api.consume_player_quota(now=1061), 0)
        listener_api._player_calls.clear()
        for minute in range(500 // 12 + 1):
            for _ in range(12):
                listener_api.consume_player_quota(now=minute * 61)
        self.assertGreater(listener_api.consume_player_quota(now=50 * 61), 3600)

    def test_quota_answer_is_429_with_retry_after(self):
        for _ in range(12):
            self.client.post("/player/dj/intent", json={"prompt": "rock"}, headers=ORIGIN)
        response = self.client.post("/player/dj/intent", json={"prompt": "rock"}, headers=ORIGIN)
        self.assertEqual(response.status_code, 429)
        self.assertIn("retry-after", response.headers)


if __name__ == "__main__":
    unittest.main()
