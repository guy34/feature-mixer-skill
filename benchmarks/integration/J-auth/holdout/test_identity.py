import unittest
import identity as m


class IdentityHoldout(unittest.TestCase):
    def setUp(self):
        self.app = m.create_app()
        self.admin = self.app.bootstrap_admin("root@example.test", "S3cure-pass!")
        self.uid = self.app.register_password("ana@example.test", "correct horse")

    def token(self, email="ana@example.test", pw="correct horse"):
        return self.app.login_password(email, pw)

    def test_password_sign_in(self):
        me = self.app.whoami(self.token())
        self.assertEqual((me["user_id"], me["email"]), (self.uid, "ana@example.test"))
        with self.assertRaises(m.AuthError):
            self.app.login_password("ana@example.test", "wrong")

    def test_verified_federated_email_links_to_the_same_account(self):
        t = self.app.login_oauth("google", "sub-1", "ANA@example.test", True)
        self.assertEqual(self.app.whoami(t)["user_id"], self.uid)

    def test_unverified_email_never_takes_over(self):
        t = self.app.login_oauth("google", "attacker", "ana@example.test", False)
        self.assertNotEqual(self.app.whoami(t)["user_id"], self.uid)

    def test_same_federated_identity_is_one_account(self):
        a = self.app.whoami(self.app.login_oauth("google", "sub-9", "bo@example.test", True))["user_id"]
        b = self.app.whoami(self.app.login_oauth("google", "sub-9", "bo@example.test", True))["user_id"]
        self.assertEqual(a, b)

    def test_logout_and_bad_tokens(self):
        t = self.token()
        self.app.logout(t)
        for bad in (t, "", "forged-token"):
            with self.assertRaises(m.AuthError):
                self.app.whoami(bad)
        self.assertNotEqual(self.token(), self.token())

    def test_role_mapping_is_explicit(self):
        self.assertEqual(self.app.map_source_role("A", "user"), "editor")
        self.assertEqual(self.app.map_source_role("B", "member"), "viewer")
        for r in ("viewer", "editor", "admin"):
            self.assertEqual(self.app.map_source_role("C", r), r)
        with self.assertRaises(KeyError):
            self.app.map_source_role("B", "owner")

    def test_only_admin_sets_roles(self):
        other = self.app.register_password("cy@example.test", "pw-cy-123")
        with self.assertRaises(PermissionError):
            self.app.set_role(self.token(), other, "admin")
        admin_t = self.app.login_password("root@example.test", "S3cure-pass!")
        self.app.set_role(admin_t, other, "viewer")
        self.assertEqual(self.app.whoami(self.app.login_password("cy@example.test", "pw-cy-123"))["role"], "viewer")

    def test_no_self_promotion(self):
        t = self.token()
        with self.assertRaises(PermissionError):
            self.app.set_role(t, self.uid, "admin")
        self.assertNotEqual(self.app.whoami(t)["role"], "admin")

    def test_new_password_accounts_get_the_mapped_role(self):
        self.assertEqual(self.app.whoami(self.token())["role"], "editor")
        t = self.app.login_oauth("google", "sub-5", "di@example.test", True)
        self.assertEqual(self.app.whoami(t)["role"], "viewer")
