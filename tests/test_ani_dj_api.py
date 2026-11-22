import json
import os
import tempfile
import unittest
from datetime import datetime, timedelta, timezone
from pathlib import Path
from unittest.mock import patch

from fastapi.testclient import TestClient
from commercial.listener_api import app
from commercial.listeners import ListenerStore
from commercial.registry import RightsRegistry

RIGHT = {
    "status": "approved", "license_type": "interactive_streaming",
    "agreement_reference": "TEST", "rights_holder": "Test",
    "recording_rights_confirmed": True, "composition_rights_confirmed": True,
    "territories": ["BR"], "valid_from": "2026-01-01", "valid_until": "2030-01-01",
}

class DjApiTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name)
        self.env = patch.dict(os.environ, {
            "AGGILLI_COMMERCIAL_DATA_DIR": self.tmp.name,
            "AGGILLI_COMMERCIAL_CATALOG_FILE": str(self.root / "catalog.json"),
            "AGGILLI_ANI_ENABLED": "false",
        })
        self.env.start()
        self.addCleanup(self.env.stop)
        self.client = TestClient(app)
        response = self.client.post("/listeners/register", json={
            "email": "dj@example.org", "password": "strong-test-password"
        })
        self.assertEqual(response.status_code, 201, response.text)
        self.listener_id = response.json()["id"]
        response = self.client.post("/listeners/login", json={
            "email": "dj@example.org", "password": "strong-test-password"
        })
        self.headers = {"Authorization": "Bearer " + response.json()["access_token"]}
        (self.root / "catalog.json").write_text(json.dumps([
            {"track_id": "ok", "media": {"title": "Piano Instrumental", "genre": "Instrumental"}},
            {"track_id": "no", "media": {"title": "Secret Song", "genre": "Ambient"}},
        ]))
        RightsRegistry(self.root / "rights.json").put("ok", RIGHT)

    def test_authentication_required(self):
        self.assertEqual(self.client.post("/listeners/dj/session", json={"prompt": "foco"}).status_code, 401)

    def test_free_listener_denied(self):
        self.assertEqual(self.client.post("/listeners/dj/session", json={"prompt": "foco"}, headers=self.headers).status_code, 403)

    def test_premium_only_licensed(self):
        expiry = (datetime.now(timezone.utc) + timedelta(days=30)).isoformat()
        ListenerStore(self.root / "listeners.db").set_subscription(
            self.listener_id, "premium", "active", expiry)
        response = self.client.post("/listeners/dj/session", json={"prompt": "Quero foco"}, headers=self.headers)
        self.assertEqual(response.status_code, 200, response.text)
        self.assertEqual([t["track_id"] for t in response.json()["tracks"]], ["ok"])
        self.assertEqual(response.json()["engine"], "offline")

    def test_missing_catalog_denied(self):
        expiry = (datetime.now(timezone.utc) + timedelta(days=30)).isoformat()
        ListenerStore(self.root / "listeners.db").set_subscription(
            self.listener_id, "premium", "active", expiry)
        (self.root / "catalog.json").unlink()
        self.assertEqual(self.client.post("/listeners/dj/session", json={"prompt": "foco"}, headers=self.headers).status_code, 503)

if __name__ == "__main__":
    unittest.main()
