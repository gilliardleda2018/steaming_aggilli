import os
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from fastapi.testclient import TestClient
from commercial import admin_api

TOKEN = "t" * 48
VALID = {
    "status": "approved",
    "license_type": "interactive_streaming",
    "agreement_reference": "TEST-CONTRACT",
    "rights_holder": "Test Label",
    "recording_rights_confirmed": True,
    "composition_rights_confirmed": True,
    "territories": ["BR"],
    "valid_from": "2026-01-01",
    "valid_until": "2027-01-01",
}


class AdminApiTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        root = Path(self.tmp.name)
        self.patches = [
            patch.object(admin_api, "DATA_DIR", root),
            patch.object(admin_api, "REGISTRY", root / "rights.json"),
            patch.object(admin_api, "AUDIT", root / "audit.jsonl"),
            patch.object(admin_api, "LOCK", root / "lock"),
            patch.dict(os.environ, {"AGGILLI_COMMERCIAL_ADMIN_TOKEN": TOKEN}),
        ]
        for p in self.patches:
            p.start()
            self.addCleanup(p.stop)
        self.client = TestClient(admin_api.app)
        self.headers = {"Authorization": "Bearer " + TOKEN}

    def test_health(self):
        self.assertEqual(self.client.get("/health").status_code, 200)

    def test_auth_required(self):
        self.assertEqual(self.client.get("/admin/rights").status_code, 401)
        self.assertEqual(self.client.get("/admin/rights", headers={"Authorization": "Bearer wrong"}).status_code, 403)

    def test_missing_token_fails_closed(self):
        with patch.dict(os.environ, {"AGGILLI_COMMERCIAL_ADMIN_TOKEN": ""}):
            self.assertEqual(self.client.get("/admin/rights", headers=self.headers).status_code, 503)

    def test_create_read_revoke_and_audit(self):
        self.assertEqual(self.client.put("/admin/rights/song1", json=VALID, headers=self.headers).status_code, 200)
        self.assertEqual(self.client.get("/admin/rights", headers=self.headers).json()["song1"]["status"], "approved")
        self.assertEqual(self.client.post("/admin/rights/song1/revoke", headers=self.headers).status_code, 200)
        self.assertEqual(self.client.get("/admin/rights", headers=self.headers).json()["song1"]["status"], "revoked")
        self.assertEqual(len(admin_api.AUDIT.read_text().splitlines()), 2)

    def test_invalid_license_rejected(self):
        bad = {**VALID, "valid_until": "2020-01-01"}
        self.assertEqual(self.client.put("/admin/rights/song1", json=bad, headers=self.headers).status_code, 422)
        self.assertFalse(admin_api.REGISTRY.exists())

    def test_unknown_revoke(self):
        self.assertEqual(self.client.post("/admin/rights/missing/revoke", headers=self.headers).status_code, 404)


if __name__ == "__main__":
    unittest.main()
