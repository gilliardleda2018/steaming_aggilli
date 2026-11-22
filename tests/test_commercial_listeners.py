import os
import tempfile
import unittest
from datetime import datetime, timedelta, timezone
from pathlib import Path
from unittest.mock import patch

from fastapi.testclient import TestClient
from commercial import listener_api
from commercial.listeners import ListenerStore, hash_password, verify_password
from commercial.registry import RightsRegistry

TOKEN = "A" * 48
PASSWORD = "strong-password-for-testing"
RIGHTS = {
    "status": "approved", "license_type": "interactive_streaming",
    "agreement_reference": "TEST-ONLY", "rights_holder": "Test Holder",
    "recording_rights_confirmed": True, "composition_rights_confirmed": True,
    "territories": ["BR"], "valid_from": "2026-01-01", "valid_until": "2030-01-01",
}


class ListenerTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.patch = patch.dict(os.environ, {
            "AGGILLI_COMMERCIAL_DATA_DIR": self.tmp.name,
            "AGGILLI_COMMERCIAL_ADMIN_TOKEN": TOKEN,
        })
        self.patch.start()
        self.addCleanup(self.patch.stop)
        self.client = TestClient(listener_api.app)
        self.db = ListenerStore(Path(self.tmp.name) / "listeners.db")

    def register(self):
        response = self.client.post("/listeners/register", json={"email": "user@example.org", "password": PASSWORD})
        self.assertEqual(response.status_code, 201, response.text)
        return response.json()["id"]

    def login(self):
        response = self.client.post("/listeners/login", json={"email": "user@example.org", "password": PASSWORD})
        self.assertEqual(response.status_code, 200, response.text)
        return response.json()["access_token"]

    def test_password_hashing(self):
        encoded = hash_password(PASSWORD)
        self.assertNotIn(PASSWORD, encoded)
        self.assertTrue(verify_password(PASSWORD, encoded))
        self.assertFalse(verify_password("wrong", encoded))

    def test_registration_and_duplicate(self):
        self.register()
        self.assertEqual(self.client.post("/listeners/register", json={"email": "USER@example.org", "password": PASSWORD}).status_code, 409)

    def test_login_logout(self):
        self.register()
        token = self.login()
        headers = {"Authorization": "Bearer " + token}
        self.assertEqual(self.client.get("/listeners/me", headers=headers).status_code, 200)
        self.assertEqual(self.client.post("/listeners/logout", headers=headers).status_code, 200)
        self.assertEqual(self.client.get("/listeners/me", headers=headers).status_code, 401)

    def test_wrong_password(self):
        self.register()
        self.assertEqual(self.client.post("/listeners/login", json={"email": "user@example.org", "password": "not-the-right-password"}).status_code, 401)

    def test_access_denied_without_license(self):
        self.register()
        token = self.login()
        self.assertFalse(self.client.get("/listeners/access/song1", headers={"Authorization": "Bearer " + token}).json()["allowed"])

    def test_access_requires_admin_set_subscription_and_rights(self):
        listener_id = self.register()
        token = self.login()
        headers = {"Authorization": "Bearer " + token}
        expiry = (datetime.now(timezone.utc) + timedelta(days=10)).isoformat()
        payload = {"listener_id": listener_id, "plan": "premium", "status": "active", "access_until": expiry}
        self.assertEqual(self.client.put("/admin/subscriptions", json=payload).status_code, 401)
        self.assertEqual(self.client.put("/admin/subscriptions", json=payload, headers={"Authorization": "Bearer " + TOKEN}).status_code, 200)
        self.assertFalse(self.client.get("/listeners/access/song1", headers=headers).json()["allowed"])
        RightsRegistry(Path(self.tmp.name) / "rights.json").put("song1", RIGHTS)
        self.assertTrue(self.client.get("/listeners/access/song1", headers=headers).json()["allowed"])
        self.assertFalse(self.client.get("/listeners/access/song1?territory=US", headers=headers).json()["allowed"])

    def test_unconfigured_admin_denied(self):
        with patch.dict(os.environ, {"AGGILLI_COMMERCIAL_ADMIN_TOKEN": ""}):
            self.assertEqual(self.client.put("/admin/subscriptions", json={},
                headers={"Authorization": "Bearer " + TOKEN}).status_code, 503)

if __name__ == "__main__":
    unittest.main()
