import os
import tempfile
import unittest
from unittest.mock import patch

from fastapi.testclient import TestClient

from commercial.listener_api import app


class ValidationErrorPrivacyTests(unittest.TestCase):
    def test_short_password_is_not_echoed_back(self):
        secret = "segredo-curto"[:11]
        with tempfile.TemporaryDirectory() as data_dir, \
             patch.dict(os.environ, {"AGGILLI_COMMERCIAL_DATA_DIR": data_dir}):
            response = TestClient(app).post("/listeners/register",
                                            json={"email": "qa@example.test", "password": secret})
        self.assertEqual(response.status_code, 422)
        self.assertNotIn(secret, response.text)
        self.assertEqual(response.json()["detail"][0]["loc"], ["body", "password"])
        self.assertNotIn("input", response.json()["detail"][0])

    def test_login_helper_never_prints_the_raw_error_body(self):
        from pathlib import Path
        script = (Path(__file__).resolve().parents[1] / "scripts" / "commercial-staging-login.sh").read_text(encoding="utf-8")
        self.assertNotIn("error.read()", script)


if __name__ == "__main__":
    unittest.main()
