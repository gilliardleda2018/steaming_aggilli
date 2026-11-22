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
            self.assertEqual(self.client.put("/admin/subscriptions", json={"listener_id": "any", "plan": "premium", "status": "active", "access_until": "2030-01-01T00:00:00Z"},
                headers={"Authorization": "Bearer " + TOKEN}).status_code, 503)

    def test_private_playback_rechecks_rights_on_each_range(self):
        listener_id = self.register()
        headers = {"Authorization": "Bearer " + self.login()}
        url = "/listeners/playback/song1"
        expiry = (datetime.now(timezone.utc) + timedelta(days=1)).isoformat()
        self.db.set_subscription(listener_id, "premium", "active", expiry)
        media_dir = Path(self.tmp.name) / "private-media"
        media_dir.mkdir()
        (media_dir / "song1.mp3").write_bytes(b"0123456789")
        rights = RightsRegistry(Path(self.tmp.name) / "rights.json")

        with patch.dict(os.environ, {"AGGILLI_COMMERCIAL_MEDIA_DIR": ""}):
            self.assertEqual(self.client.get(url, headers=headers).status_code, 503)
        with patch.dict(os.environ, {
            "AGGILLI_COMMERCIAL_MEDIA_DIR": str(media_dir),
            "AGGILLI_COMMERCIAL_PLAYBACK_TERRITORY": "BR",
            "AGGILLI_COMMERCIAL_PLAYBACK_SECRET": "S" * 32,
        }):
            self.assertEqual(self.client.get(url).status_code, 401)
            self.assertEqual(self.client.get(url, headers=headers).status_code, 403)
            rights.put("song1", RIGHTS)
            self.assertEqual(self.client.get(url, headers=headers).content, b"0123456789")
            self.assertEqual(self.client.head(url, headers=headers).headers["Content-Length"], "10")
            ranged = {**headers, "Range": "bytes=2-4"}
            result = self.client.get(url, headers=ranged)
            self.assertEqual(result.status_code, 206)
            self.assertEqual(result.content, b"234")
            self.assertEqual(result.headers["Content-Range"], "bytes 2-4/10")
            self.assertEqual(result.headers["Cache-Control"], "private, no-store")
            self.assertEqual(self.client.get(url, headers={**headers, "Range": "bytes=20-"}).status_code, 416)
            self.assertEqual(self.client.post(url + "/grant").status_code, 401)
            grant = self.client.post(url + "/grant", headers=headers).json()["grant"]
            audio = url + "/audio"
            params = {"grant": grant}
            self.assertEqual(self.client.get(audio, params=params, headers={"Range": "bytes=2-4"}).content, b"234")
            self.assertEqual(self.client.get(audio.replace("song1", "song2"), params=params).status_code, 403)
            with patch.object(listener_api.time, "time", return_value=int(grant.split(".")[1])):
                self.assertEqual(self.client.get(audio, params=params).status_code, 403)
            rights.revoke("song1")
            self.assertEqual(self.client.get(url, headers=ranged).status_code, 403)
            self.assertEqual(self.client.get(audio, params=params).status_code, 403)
            rights.put("song1", RIGHTS)
            self.client.post("/listeners/logout", headers=headers)
            self.assertEqual(self.client.get(audio, params=params).status_code, 401)

if __name__ == "__main__":
    unittest.main()
