import unittest
from datetime import datetime, timezone
from commercial.entitlements import allowed_to_play

NOW = datetime(2026, 11, 22, 18, 0, tzinfo=timezone.utc)
USER = {"id": "listener-1", "status": "active"}
SUB = {
    "listener_id": "listener-1",
    "status": "active",
    "plan": "premium",
    "access_until": "2026-12-31T00:00:00Z",
}
RIGHTS = {
    "status": "approved",
    "license_type": "interactive_streaming",
    "agreement_reference": "TEST-AGREEMENT",
    "rights_holder": "Test Holder",
    "recording_rights_confirmed": True,
    "composition_rights_confirmed": True,
    "territories": ["BR"],
    "valid_from": "2026-01-01",
    "valid_until": "2027-01-01",
}


class EntitlementTests(unittest.TestCase):
    def allowed(self, user=USER, sub=SUB, rights=RIGHTS, territory="BR"):
        return allowed_to_play(user, sub, rights, territory, now=NOW)

    def test_valid_paid_access(self):
        self.assertTrue(self.allowed())

    def test_missing_records_denied(self):
        self.assertFalse(self.allowed(user=None))
        self.assertFalse(self.allowed(sub=None))
        self.assertFalse(self.allowed(rights=None))

    def test_suspended_listener_denied(self):
        self.assertFalse(self.allowed(user={**USER, "status": "suspended"}))

    def test_wrong_listener_denied(self):
        self.assertFalse(self.allowed(sub={**SUB, "listener_id": "other"}))

    def test_inactive_subscription_denied(self):
        self.assertFalse(self.allowed(sub={**SUB, "status": "past_due"}))

    def test_free_plan_denied(self):
        self.assertFalse(self.allowed(sub={**SUB, "plan": "free"}))

    def test_expired_access_denied(self):
        self.assertFalse(self.allowed(sub={**SUB, "access_until": "2026-11-22T17:59:59Z"}))

    def test_untrusted_expiry_denied(self):
        self.assertFalse(self.allowed(sub={**SUB, "access_until": "not-a-date"}))
        self.assertFalse(self.allowed(sub={**SUB, "access_until": "2027-01-01T00:00:00"}))

    def test_unlicensed_track_denied(self):
        self.assertFalse(self.allowed(rights={**RIGHTS, "status": "revoked"}))

    def test_territory_denied(self):
        self.assertFalse(self.allowed(territory="US"))

    def test_trial_with_valid_rights(self):
        self.assertTrue(self.allowed(sub={**SUB, "status": "trialing"}))


if __name__ == "__main__":
    unittest.main()
