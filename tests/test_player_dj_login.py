import unittest
from pathlib import Path

HTML = (Path(__file__).resolve().parents[1] / "player" / "index.html").read_text(encoding="utf-8")
COMMERCIAL = HTML.split('/* AGGILLI_UNIFIED_COMMERCIAL_DJ_V1 */', 1)[1].split('</script>', 1)[0]


class PlayerDjLoginTests(unittest.TestCase):
    def test_login_form_uses_password_manager_friendly_fields(self):
        self.assertIn('id="aggilliDjLogin"', HTML)
        self.assertIn('autocomplete="username"', HTML)
        self.assertIn('autocomplete="current-password"', HTML)

    def test_login_only_talks_to_same_origin_https_api(self):
        self.assertIn("base.protocol!=='https:'||base.origin!==location.origin", COMMERCIAL)
        self.assertIn("'/listeners/login'", COMMERCIAL)
        self.assertIn("'/listeners/register'", COMMERCIAL)
        self.assertIn("credentials:'omit'", COMMERCIAL)

    def test_password_is_cleared_and_never_stored_or_shown(self):
        self.assertIn("finally{password.value=''", COMMERCIAL)
        self.assertNotIn('localStorage', COMMERCIAL)
        self.assertNotIn('sessionStorage', COMMERCIAL)
        self.assertNotIn('password.value+', COMMERCIAL)
        self.assertNotIn('await response.text()', COMMERCIAL)

    def test_clearing_access_revokes_the_session(self):
        self.assertIn("'/listeners/logout'", COMMERCIAL)


if __name__ == "__main__":
    unittest.main()
