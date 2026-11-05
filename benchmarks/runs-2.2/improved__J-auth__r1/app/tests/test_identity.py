import importlib.util
import os
import threading
import unittest

from tests.helpers import APP_DIR, FakeClock
from unified import identity
from unified.identity import AuthError, create_app


class PasswordTests(unittest.TestCase):
    def setUp(self):
        self.app = create_app()

    def test_register_and_login_password(self):
        """features: M01, M02, M04
        acceptance: AC01
        expect: register returns an id; login returns a token; whoami shows the id, normalised email and role editor
        level: feature"""
        uid = self.app.register_password("ana@example.com", "correct horse")
        token = self.app.login_password("ana@example.com", "correct horse")
        self.assertIsInstance(token, str)
        self.assertEqual(self.app.whoami(token), {"user_id": uid, "email": "ana@example.com", "role": "editor"})

    def test_email_case_normalised(self):
        """features: M01, M02, M03
        expect: emails are trimmed and lowercased for sign-up, login and linking
        level: feature"""
        uid = self.app.register_password("  Ana@Example.COM ", "pw-1")
        self.assertEqual(self.app.whoami(self.app.login_password("ana@example.com", "pw-1"))["email"], "ana@example.com")
        self.assertEqual(self.app.whoami(self.app.login_password("ANA@EXAMPLE.COM", "pw-1"))["user_id"], uid)
        t = self.app.login_oauth("google", "g-1", "ANA@example.com", True)
        self.assertEqual(self.app.whoami(t)["user_id"], uid)

    def test_duplicate_registration_refused(self):
        """features: M01
        acceptance: AC02
        expect: a second registration of the same email (any case) raises AuthError and the first password still works
        level: feature"""
        self.app.register_password("ana@example.com", "first")
        with self.assertRaises(AuthError):
            self.app.register_password("ANA@example.com", "second")
        self.app.login_password("ana@example.com", "first")
        with self.assertRaises(AuthError):
            self.app.login_password("ana@example.com", "second")

    def test_registration_input_validated(self):
        """features: M01
        expect: invalid emails and empty or non-string passwords are refused with AuthError (a ValueError)
        level: feature"""
        for email in ("", "no-at-sign", "@example.com", "ana@", "a b@example.com", None, 5, "x" * 250 + "@ex.com"):
            with self.assertRaises(AuthError, msg=repr(email)):
                self.app.register_password(email, "pw")
        for pw in ("", None, 123):
            with self.assertRaises(AuthError):
                self.app.register_password("ok@example.com", pw)
        self.assertTrue(issubclass(AuthError, ValueError))

    def test_login_failures_raise_autherror(self):
        """features: M02
        acceptance: AC03
        expect: wrong password, unknown email and malformed input all raise AuthError with the same message
        level: feature"""
        self.app.register_password("ana@example.com", "right")
        messages = set()
        for email, pw in (("ana@example.com", "wrong"), ("nobody@example.com", "right"), ("", "x"), (None, None)):
            with self.assertRaises(AuthError) as ctx:
                self.app.login_password(email, pw)
            messages.add(str(ctx.exception))
        self.assertEqual(messages, {"bad credentials"})

    def test_password_stored_hashed_with_salt(self):
        """features: M01
        expect: no plaintext password is stored; PBKDF2-SHA256 with a 16-byte random salt and 100000 iterations
        level: unit"""
        self.app.register_password("a@example.com", "same-password")
        self.app.register_password("b@example.com", "same-password")
        a, b = self.app._passwords["a@example.com"], self.app._passwords["b@example.com"]
        self.assertEqual(len(a["salt"]), 16)
        self.assertNotEqual(a["salt"], b["salt"])
        self.assertNotEqual(a["hash"], b["hash"])
        self.assertEqual(a["iterations"], 100_000)
        self.assertNotIn(b"same-password", a["hash"])

    def test_user_ids_are_opaque_strings(self):
        """features: M01, M03
        expect: every user id is a unique opaque text id, not a source's counter
        level: unit"""
        ids = [self.app.register_password(f"u{i}@example.com", "pw") for i in range(3)]
        ids.append(self.app.whoami(self.app.login_oauth("google", "s", None, False))["user_id"])
        self.assertEqual(len(set(ids)), 4)
        for uid in ids:
            self.assertIsInstance(uid, str)
            self.assertEqual(len(uid), 32)
            self.assertFalse(uid.isdigit())
            self.assertFalse(uid.startswith("lu-"))


class SessionTests(unittest.TestCase):
    def test_logout_revokes_token(self):
        """features: M02
        acceptance: AC04
        expect: after logout whoami raises AuthError; other sessions stay valid; logout twice is harmless
        level: feature"""
        app = create_app()
        app.register_password("ana@example.com", "pw")
        t1 = app.login_password("ana@example.com", "pw")
        t2 = app.login_password("ana@example.com", "pw")
        self.assertNotEqual(t1, t2)
        app.logout(t1)
        with self.assertRaises(AuthError):
            app.whoami(t1)
        self.assertEqual(app.whoami(t2)["email"], "ana@example.com")
        app.logout(t1)
        app.logout("never-issued")

    def test_whoami_invalid_token(self):
        """features: M02
        expect: unknown, empty and non-string tokens raise AuthError
        level: feature"""
        app = create_app()
        for bad in ("nope", "", None, 42):
            with self.assertRaises(AuthError):
                app.whoami(bad)

    def test_session_expires(self):
        """features: M02, M03
        acceptance: AC04
        expect: a session older than its lifetime raises AuthError
        level: feature"""
        clock = FakeClock()
        app = create_app(session_ttl=60, clock=clock)
        app.register_password("ana@example.com", "pw")
        t = app.login_password("ana@example.com", "pw")
        o = app.login_oauth("google", "s1", "x@example.com", False)
        clock.advance(59)
        app.whoami(t)
        app.whoami(o)
        clock.advance(1)
        for tok in (t, o):
            with self.assertRaises(AuthError):
                app.whoami(tok)

    def test_tokens_not_stored_in_clear(self):
        """features: M02
        expect: the session store keeps only a hash of each token
        level: unit"""
        app = create_app()
        app.register_password("ana@example.com", "pw")
        t = app.login_password("ana@example.com", "pw")
        self.assertNotIn(t, app._sessions)
        self.assertGreaterEqual(len(t), 32)


class OAuthTests(unittest.TestCase):
    def setUp(self):
        self.app = create_app()

    def test_oauth_verified_email_links_existing_account(self):
        """features: M03, M01
        acceptance: AC05
        expect: a provider sign-in with the same verified email returns a token for the same account, role kept
        level: interaction"""
        uid = self.app.register_password("ana@example.com", "pw")
        t = self.app.login_oauth("google", "sub-1", "ana@example.com", True)
        self.assertEqual(self.app.whoami(t), {"user_id": uid, "email": "ana@example.com", "role": "editor"})
        t2 = self.app.login_oauth("google", "sub-1", "ana@example.com", True)
        self.assertEqual(self.app.whoami(t2)["user_id"], uid)

    def test_oauth_unverified_email_creates_separate_account(self):
        """features: M03, M01
        acceptance: AC06
        expect: a provider sign-in with the same but unverified email gets a separate viewer account
        level: interaction"""
        uid = self.app.register_password("ana@example.com", "pw")
        t = self.app.login_oauth("google", "sub-x", "ana@example.com", False)
        me = self.app.whoami(t)
        self.assertNotEqual(me["user_id"], uid)
        self.assertEqual(me["role"], "viewer")
        # the password account is untouched
        self.assertEqual(self.app.whoami(self.app.login_password("ana@example.com", "pw"))["user_id"], uid)
        # the same identity stays separate even if the provider later says verified
        t2 = self.app.login_oauth("google", "sub-x", "ana@example.com", True)
        self.assertEqual(self.app.whoami(t2)["user_id"], me["user_id"])

    def test_oauth_email_verified_must_be_true(self):
        """features: M03
        acceptance: AC06
        expect: truthy non-boolean values such as "true", "false", 1 never count as verified
        level: feature"""
        uid = self.app.register_password("ana@example.com", "pw")
        for i, flag in enumerate(("true", "false", 1, "yes", None)):
            t = self.app.login_oauth("google", f"s-{i}", "ana@example.com", flag)
            self.assertNotEqual(self.app.whoami(t)["user_id"], uid, msg=repr(flag))

    def test_oauth_new_user_is_viewer_and_stable(self):
        """features: M03, M04
        acceptance: AC07
        expect: a new provider identity gets one viewer account, returned again on the next sign-in
        level: feature"""
        t1 = self.app.login_oauth("google", "new-1", "bo@example.com", True)
        t2 = self.app.login_oauth("google", "new-1", "bo@example.com", True)
        a, b = self.app.whoami(t1), self.app.whoami(t2)
        self.assertEqual(a, b)
        self.assertEqual(a["role"], "viewer")
        self.assertEqual(a["email"], "bo@example.com")

    def test_oauth_verified_new_user_owns_email(self):
        """features: M03, M01
        expect: once a verified provider account owns an email, password registration of it is refused and a second
        provider with the same verified email joins the same account
        level: interaction"""
        t = self.app.login_oauth("google", "g1", "cy@example.com", True)
        uid = self.app.whoami(t)["user_id"]
        with self.assertRaises(AuthError):
            self.app.register_password("cy@example.com", "pw")
        t2 = self.app.login_oauth("github", "h1", "cy@example.com", True)
        self.assertEqual(self.app.whoami(t2)["user_id"], uid)

    def test_oauth_unverified_does_not_claim_email(self):
        """features: M03, M01
        expect: an unverified provider email does not block the real owner from registering
        level: interaction"""
        self.app.login_oauth("google", "g1", "dee@example.com", False)
        uid = self.app.register_password("dee@example.com", "pw")
        t = self.app.login_oauth("google", "g2", "dee@example.com", True)
        self.assertEqual(self.app.whoami(t)["user_id"], uid)

    def test_oauth_without_email_creates_separate_account(self):
        """features: M03
        expect: a provider sign-in without an email never links and has email None
        level: feature"""
        self.app.register_password("ana@example.com", "pw")
        me = self.app.whoami(self.app.login_oauth("google", "s1", None, True))
        self.assertIsNone(me["email"])
        self.assertEqual(me["role"], "viewer")

    def test_same_subject_different_providers_are_different_identities(self):
        """features: M03
        expect: identities are keyed by (provider, subject)
        level: feature"""
        a = self.app.whoami(self.app.login_oauth("google", "42", None, False))
        b = self.app.whoami(self.app.login_oauth("github", "42", None, False))
        self.assertNotEqual(a["user_id"], b["user_id"])

    def test_oauth_input_validated(self):
        """features: M03
        expect: empty or non-string provider or subject, and malformed emails, raise AuthError
        level: feature"""
        for args in (("", "s", None, False), ("google", "", None, False), (None, "s", None, False),
                     ("google", 5, None, False), ("google", "s", "not-an-email", True)):
            with self.assertRaises(AuthError, msg=repr(args)):
                self.app.login_oauth(*args)


class RoleChangeTests(unittest.TestCase):
    def setUp(self):
        self.app = create_app()
        self.admin_id = self.app.bootstrap_admin("root@example.com", "admin-pw")
        self.admin = self.app.login_password("root@example.com", "admin-pw")
        self.ed_id = self.app.register_password("ed@example.com", "pw")
        self.ed = self.app.login_password("ed@example.com", "pw")
        self.vi = self.app.login_oauth("google", "v1", "vi@example.com", True)
        self.vi_id = self.app.whoami(self.vi)["user_id"]

    def test_non_admin_cannot_set_role(self):
        """features: M05, M04
        acceptance: AC09
        expect: viewers, editors and invalid sessions get PermissionError and nothing changes
        level: feature"""
        for tok in (self.ed, self.vi, "bogus", None):
            for target in (self.vi_id, self.ed_id, self.admin_id):
                with self.assertRaises(PermissionError):
                    self.app.set_role(tok, target, "viewer")
        self.assertEqual(self.app.whoami(self.ed)["role"], "editor")
        self.assertEqual(self.app.whoami(self.vi)["role"], "viewer")
        self.assertEqual(self.app.whoami(self.admin)["role"], "admin")

    def test_admin_sets_role(self):
        """features: M05, M04
        acceptance: AC10
        expect: an admin changes another user's role and it shows at once; unknown roles and users are refused
        level: feature"""
        self.app.set_role(self.admin, self.vi_id, "editor")
        self.assertEqual(self.app.whoami(self.vi)["role"], "editor")
        self.app.set_role(self.admin, self.ed_id, "admin")
        self.assertEqual(self.app.whoami(self.ed)["role"], "admin")
        self.app.set_role(self.ed, self.vi_id, "viewer")
        self.assertEqual(self.app.whoami(self.vi)["role"], "viewer")
        with self.assertRaises(ValueError):
            self.app.set_role(self.admin, self.vi_id, "superuser")
        with self.assertRaises(ValueError):
            self.app.set_role(self.admin, self.vi_id, "member")
        with self.assertRaises(KeyError):
            self.app.set_role(self.admin, "no-such-user", "viewer")
        self.assertEqual(self.app.whoami(self.vi)["role"], "viewer")

    def test_nobody_raises_own_role(self):
        """features: M05
        acceptance: AC11
        expect: viewers and editors cannot raise their own role; lowering is not raising
        level: feature"""
        with self.assertRaises(PermissionError):
            self.app.set_role(self.vi, self.vi_id, "admin")
        with self.assertRaises(PermissionError):
            self.app.set_role(self.ed, self.ed_id, "admin")
        with self.assertRaises(PermissionError):
            self.app.set_role(self.vi, self.vi_id, "editor")
        self.assertEqual(self.app.whoami(self.vi)["role"], "viewer")
        # the rank rule itself, even for a caller allowed to manage roles
        self.app.set_role(self.admin, self.ed_id, "admin")
        self.app.set_role(self.ed, self.ed_id, "editor")
        self.assertEqual(self.app.whoami(self.ed)["role"], "editor")
        with self.assertRaises(PermissionError):
            self.app.set_role(self.ed, self.ed_id, "admin")

    def test_role_change_needs_live_session(self):
        """features: M05, M02
        expect: an admin's revoked or expired session cannot change roles
        level: feature"""
        self.app.logout(self.admin)
        with self.assertRaises(PermissionError):
            self.app.set_role(self.admin, self.vi_id, "editor")

    def test_bootstrap_admin_only_once(self):
        """features: M05
        acceptance: AC12
        expect: the first bootstrap creates an admin; a second is refused while an admin exists
        level: feature"""
        self.assertEqual(self.app.whoami(self.admin), {"user_id": self.admin_id, "email": "root@example.com",
                                                       "role": "admin"})
        with self.assertRaises(PermissionError):
            self.app.bootstrap_admin("second@example.com", "pw")
        fresh = create_app()
        with self.assertRaises(AuthError):
            fresh.bootstrap_admin("bad-email", "pw")
        uid = fresh.bootstrap_admin("first@example.com", "pw")
        self.assertEqual(fresh.whoami(fresh.login_password("first@example.com", "pw"))["user_id"], uid)


class ModuleTests(unittest.TestCase):
    def test_interface_and_file_import(self):
        """features: M01, M02, M03, M04, M05
        expect: create_app, AuthError and every interface method exist; identity.py also loads as a plain file
        level: unit"""
        app = create_app()
        for name in ("register_password", "login_password", "login_oauth", "whoami", "logout", "set_role",
                     "map_source_role", "bootstrap_admin"):
            self.assertTrue(callable(getattr(app, name)), name)
        self.assertTrue(issubclass(identity.AuthError, Exception))
        path = os.path.join(APP_DIR, "unified", "identity.py")
        spec = importlib.util.spec_from_file_location("identity_as_file", path)
        mod = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(mod)
        a = mod.create_app()
        a.register_password("x@example.com", "pw")
        with self.assertRaises(mod.AuthError):
            a.login_password("x@example.com", "no")

    def test_concurrent_registration_one_winner(self):
        """features: M01
        expect: concurrent registrations of one email create exactly one account
        level: feature"""
        app = create_app(pbkdf2_iterations=1000)
        results = []

        def go():
            try:
                results.append(app.register_password("race@example.com", "pw"))
            except AuthError:
                results.append(None)

        threads = [threading.Thread(target=go) for _ in range(8)]
        for t in threads:
            t.start()
        for t in threads:
            t.join()
        self.assertEqual(len([r for r in results if r]), 1)


if __name__ == "__main__":
    unittest.main()
