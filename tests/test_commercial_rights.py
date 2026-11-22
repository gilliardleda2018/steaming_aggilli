import unittest
from datetime import date
from commercial.rights import eligible_for_streaming, commercial_catalog

TODAY = date(2026, 11, 22)
RIGHTS = {
    "status": "approved",
    "license_type": "interactive_streaming",
    "agreement_reference": "AGREEMENT-EXAMPLE",
    "rights_holder": "Example Label",
    "recording_rights_confirmed": True,
    "composition_rights_confirmed": True,
    "territories": ["BR"],
    "valid_from": "2026-01-01",
    "valid_until": "2027-01-01",
}

class RightsTests(unittest.TestCase):
    def test_valid_rights(self):
        self.assertTrue(eligible_for_streaming(RIGHTS, "BR", TODAY))

    def test_missing_rights_denied(self):
        self.assertFalse(eligible_for_streaming(None, "BR", TODAY))
        self.assertFalse(eligible_for_streaming({}, "BR", TODAY))

    def test_expired_denied(self):
        self.assertFalse(eligible_for_streaming(RIGHTS, "BR", date(2028, 1, 1)))

    def test_wrong_territory_denied(self):
        self.assertFalse(eligible_for_streaming(RIGHTS, "US", TODAY))

    def test_missing_recording_or_composition_denied(self):
        for key in ("recording_rights_confirmed", "composition_rights_confirmed"):
            self.assertFalse(eligible_for_streaming({**RIGHTS, key: False}, "BR", TODAY))

    def test_radio_license_not_sufficient(self):
        self.assertFalse(eligible_for_streaming({**RIGHTS, "license_type": "web_radio"}, "BR", TODAY))

    def test_unapproved_denied(self):
        self.assertFalse(eligible_for_streaming({**RIGHTS, "status": "pending"}, "BR", TODAY))

    def test_catalog_filters_without_modifying_original(self):
        tracks = [{"track_id": "licensed"}, {"track_id": "unlicensed"}]
        result = commercial_catalog(tracks, {"licensed": RIGHTS}, "BR", TODAY)
        self.assertEqual(result, [tracks[0]])
        self.assertEqual(len(tracks), 2)

if __name__ == "__main__":
    unittest.main()
