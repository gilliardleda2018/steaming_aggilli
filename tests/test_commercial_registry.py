import json
import tempfile
import unittest
from datetime import date
from pathlib import Path
from commercial.registry import RightsRegistry

APPROVED = {
    "status": "approved",
    "license_type": "interactive_streaming",
    "agreement_reference": "SAMPLE-ONLY",
    "rights_holder": "Test Rights Holder",
    "recording_rights_confirmed": True,
    "composition_rights_confirmed": True,
    "territories": ["BR"],
    "valid_from": "2026-01-01",
    "valid_until": "2027-01-01",
}

class RegistryTests(unittest.TestCase):
    def setUp(self):
        self.directory = tempfile.TemporaryDirectory()
        self.addCleanup(self.directory.cleanup)
        self.path = Path(self.directory.name) / "rights.json"
        self.registry = RightsRegistry(self.path)

    def test_empty_registry_denies_all(self):
        self.assertEqual(self.registry.catalog([{"track_id": "x"}], "BR"), [])

    def test_save_and_filter(self):
        self.registry.put("a", APPROVED)
        tracks = [{"track_id": "a"}, {"track_id": "b"}]
        self.assertEqual(self.registry.catalog(tracks, "BR", date(2026, 11, 22)), [tracks[0]])
        self.assertEqual(self.registry.catalog(tracks, "US", date(2026, 11, 22)), [])
        self.assertEqual(self.path.stat().st_mode & 0o777, 0o600)

    def test_revocation_immediately_blocks(self):
        self.registry.put("a", APPROVED)
        self.registry.revoke("a")
        self.assertEqual(self.registry.catalog([{"track_id": "a"}], "BR", date(2026, 11, 22)), [])
        self.assertEqual(self.registry.read()["a"]["status"], "revoked")

    def test_invalid_registry_fails_closed(self):
        self.path.write_text(json.dumps(["not a registry"]))
        with self.assertRaises(ValueError):
            self.registry.catalog([{"track_id": "a"}], "BR")

    def test_reject_invalid_record(self):
        with self.assertRaises(ValueError):
            self.registry.put("a", "approved")

if __name__ == "__main__":
    unittest.main()
