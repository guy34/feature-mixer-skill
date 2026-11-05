import unittest

from tests import helpers  # noqa: F401
from unified.identity import AuthError, create_app


class JourneyTests(unittest.TestCase):
    def test_journey_full_identity_flow(self):
        """features: M01, M02, M03, M04, M05
        acceptance: AC01, AC05, AC06, AC10
        expect: setup admin; a person signs up with a password, signs in with a verified provider email into the
        same account, an unverified look-alike stays separate, the admin promotes the person, the new role shows,
        and logout ends the session
        level: journey"""
        app = create_app()
        admin_id = app.bootstrap_admin("admin@example.com", "admin-pw")
        admin = app.login_password("admin@example.com", "admin-pw")
        self.assertEqual(app.whoami(admin)["role"], "admin")

        uid = app.register_password("Pat@Example.com", "pat-pw")
        pw_token = app.login_password("pat@example.com", "pat-pw")
        self.assertEqual(app.whoami(pw_token), {"user_id": uid, "email": "pat@example.com", "role": "editor"})

        g_token = app.login_oauth("google", "google-pat", "pat@example.com", True)
        self.assertEqual(app.whoami(g_token)["user_id"], uid)

        imposter = app.login_oauth("other-idp", "x", "pat@example.com", False)
        imposter_me = app.whoami(imposter)
        self.assertNotEqual(imposter_me["user_id"], uid)
        self.assertEqual(imposter_me["role"], "viewer")
        with self.assertRaises(PermissionError):
            app.set_role(imposter, uid, "viewer")
        with self.assertRaises(PermissionError):
            app.set_role(imposter, imposter_me["user_id"], "admin")

        with self.assertRaises(PermissionError):
            app.set_role(pw_token, uid, "admin")
        app.set_role(admin, uid, "admin")
        self.assertEqual(app.whoami(g_token)["role"], "admin")
        self.assertEqual(app.whoami(pw_token)["role"], "admin")
        self.assertEqual(app.map_source_role("B", "member"), "viewer")

        app.logout(g_token)
        with self.assertRaises(AuthError):
            app.whoami(g_token)
        self.assertEqual(app.whoami(pw_token)["user_id"], uid)
        self.assertNotEqual(admin_id, uid)


if __name__ == "__main__":
    unittest.main()
