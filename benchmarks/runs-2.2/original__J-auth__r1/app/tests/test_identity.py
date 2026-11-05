import os
import sys
import unittest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from unified.identity import AuthError, create_app  # noqa: E402


class FakeClock:
    def __init__(self):
        self.now = 1_000_000.0

    def __call__(self):
        return self.now


# ----------------------------------------------------------------------------- V1: sign-in

class TestPasswordAccounts(unittest.TestCase):
    def setUp(self):
        self.app = create_app()

    def test_register_returns_id_and_editor_role(self):
        """features: M01, M02, M04
        acceptance: AC01
        expect: register_password returns a user id; the account's role is editor (A's user)
        level: feature"""
        uid = self.app.register_password("ana@example.com", "s3cret")
        self.assertTrue(uid)
        me = self.app.whoami(self.app.login_password("ana@example.com", "s3cret"))
        self.assertEqual(me, {"user_id": uid, "email": "ana@example.com", "role": "editor"})

    def test_duplicate_email_rejected_and_original_kept(self):
        """features: M01
        acceptance: AC02
        expect: registering an existing email (any case) fails; the first password still works
        level: feature"""
        uid = self.app.register_password("ana@example.com", "first")
        with self.assertRaises(AuthError):
            self.app.register_password("ANA@Example.com ", "second")
        with self.assertRaises(ValueError):
            self.app.register_password("ana@example.com", "third")
        self.assertEqual(self.app.whoami(self.app.login_password("ana@example.com", "first"))["user_id"], uid)
        with self.assertRaises(AuthError):
            self.app.login_password("ana@example.com", "second")

    def test_invalid_registration_input(self):
        """features: M01
        acceptance: AC02
        expect: empty or malformed email and empty password are refused
        level: form"""
        for email, pw in [("", "pw"), ("not-an-email", "pw"), (None, "pw"), ("a@b.c", ""), ("a@b.c", None)]:
            with self.assertRaises(ValueError):
                self.app.register_password(email, pw)

    def test_login_is_case_insensitive_on_email(self):
        """features: M02
        acceptance: AC03
        expect: login with a differently cased email reaches the same account; whoami shows the normalised email
        level: auth"""
        uid = self.app.register_password("Ana@Example.com", "pw")
        me = self.app.whoami(self.app.login_password("ANA@EXAMPLE.COM", "pw"))
        self.assertEqual(me["user_id"], uid)
        self.assertEqual(me["email"], "ana@example.com")

    def test_wrong_password_and_unknown_email_raise_autherror(self):
        """features: M02
        acceptance: AC04
        expect: wrong password, unknown email and empty password all raise AuthError
        level: auth"""
        self.app.register_password("ana@example.com", "pw")
        for email, pw in [("ana@example.com", "nope"), ("bob@example.com", "pw"), ("ana@example.com", ""),
                          ("ana@example.com", None)]:
            with self.assertRaises(AuthError):
                self.app.login_password(email, pw)

    def test_tokens_are_unique_per_login(self):
        """features: M02
        acceptance: AC03
        expect: two logins give two different working tokens
        level: auth"""
        self.app.register_password("ana@example.com", "pw")
        t1 = self.app.login_password("ana@example.com", "pw")
        t2 = self.app.login_password("ana@example.com", "pw")
        self.assertNotEqual(t1, t2)
        self.assertEqual(self.app.whoami(t1), self.app.whoami(t2))

    def test_logout_invalidates_token(self):
        """features: M02
        acceptance: AC05
        expect: after logout whoami raises AuthError; other sessions survive; logout is idempotent
        level: auth"""
        self.app.register_password("ana@example.com", "pw")
        t1 = self.app.login_password("ana@example.com", "pw")
        t2 = self.app.login_password("ana@example.com", "pw")
        self.app.logout(t1)
        with self.assertRaises(AuthError):
            self.app.whoami(t1)
        self.assertEqual(self.app.whoami(t2)["email"], "ana@example.com")
        self.app.logout(t1)
        self.app.logout("never-issued")

    def test_invalid_and_expired_tokens(self):
        """features: M02
        acceptance: AC05
        expect: unknown, None and expired tokens raise AuthError
        level: auth"""
        clock = FakeClock()
        app = create_app(clock=clock, session_ttl_seconds=60)
        app.register_password("ana@example.com", "pw")
        token = app.login_password("ana@example.com", "pw")
        for bad in ["garbage", "", None, 123]:
            with self.assertRaises(AuthError):
                app.whoami(bad)
        clock.now += 59
        self.assertEqual(app.whoami(token)["email"], "ana@example.com")
        clock.now += 2
        with self.assertRaises(AuthError):
            app.whoami(token)

    def test_password_not_stored_in_clear(self):
        """features: M01
        acceptance: AC01
        expect: the stored password hash is salted PBKDF2 and never the password
        level: database"""
        uid = self.app.register_password("ana@example.com", "pw-unique-123")
        user = self.app._accounts.get(uid)
        self.assertTrue(user.password_hash.startswith("pbkdf2_sha256$"))
        self.assertNotIn("pw-unique-123", user.password_hash)
        uid2 = self.app.register_password("bob@example.com", "pw-unique-123")
        self.assertNotEqual(user.password_hash, self.app._accounts.get(uid2).password_hash)

    def test_separate_apps_do_not_share_state(self):
        """features: M01
        acceptance: AC01
        expect: two create_app() instances keep separate users
        level: unit"""
        other = create_app()
        self.app.register_password("ana@example.com", "pw")
        with self.assertRaises(AuthError):
            other.login_password("ana@example.com", "pw")


class TestOAuth(unittest.TestCase):
    def setUp(self):
        self.app = create_app()

    def test_new_oauth_user_is_viewer_and_stable(self):
        """features: M03, M04
        acceptance: AC06
        expect: first OAuth sign-in creates a viewer; the same provider+subject returns the same user
        level: feature"""
        me1 = self.app.whoami(self.app.login_oauth("google", "sub-1", "cara@example.com", True))
        self.assertEqual(me1["role"], "viewer")
        self.assertEqual(me1["email"], "cara@example.com")
        me2 = self.app.whoami(self.app.login_oauth("google", "sub-1", "cara@example.com", True))
        self.assertEqual(me1["user_id"], me2["user_id"])

    def test_verified_email_joins_password_account(self):
        """features: M01, M02, M03
        acceptance: AC07
        expect: a verified OAuth email equal to a password account's email signs in to that account and keeps its role
        level: interaction"""
        uid = self.app.register_password("ana@example.com", "pw")
        me = self.app.whoami(self.app.login_oauth("google", "g-ana", "ANA@example.com", True))
        self.assertEqual(me["user_id"], uid)
        self.assertEqual(me["role"], "editor")
        self.assertEqual(self.app.whoami(self.app.login_password("ana@example.com", "pw"))["user_id"], uid)

    def test_unverified_email_creates_separate_account(self):
        """features: M01, M03
        acceptance: AC08
        expect: an unverified OAuth email equal to a password account's email creates a separate viewer account
        level: interaction"""
        uid = self.app.register_password("ana@example.com", "pw")
        me = self.app.whoami(self.app.login_oauth("google", "attacker", "ana@example.com", False))
        self.assertNotEqual(me["user_id"], uid)
        self.assertEqual(me["role"], "viewer")
        ana = self.app.whoami(self.app.login_password("ana@example.com", "pw"))
        self.assertEqual((ana["user_id"], ana["role"]), (uid, "editor"))
        # a later verified sign-in with the same email still joins the real owner
        me2 = self.app.whoami(self.app.login_oauth("google", "g-ana", "ana@example.com", True))
        self.assertEqual(me2["user_id"], uid)

    def test_only_true_counts_as_verified(self):
        """features: M03
        acceptance: AC08
        expect: truthy non-boolean email_verified values do not join accounts
        level: authorization"""
        uid = self.app.register_password("ana@example.com", "pw")
        for i, flag in enumerate(["true", 1, "yes", None]):
            me = self.app.whoami(self.app.login_oauth("google", f"s{i}", "ana@example.com", flag))
            self.assertNotEqual(me["user_id"], uid)

    def test_unverified_oauth_does_not_block_registration(self):
        """features: M01, M03
        acceptance: AC08
        expect: an unverified OAuth account never claims its email; the real owner can still register it
        level: interaction"""
        squatter = self.app.whoami(self.app.login_oauth("google", "x", "dan@example.com", False))
        uid = self.app.register_password("dan@example.com", "pw")
        self.assertNotEqual(uid, squatter["user_id"])
        self.assertEqual(self.app.whoami(self.app.login_password("dan@example.com", "pw"))["user_id"], uid)

    def test_verified_oauth_account_owns_email(self):
        """features: M01, M03
        acceptance: AC07
        expect: a verified OAuth-created account owns its email: another provider joins it and password registration is refused
        level: interaction"""
        me = self.app.whoami(self.app.login_oauth("google", "g-eve", "eve@example.com", True))
        me2 = self.app.whoami(self.app.login_oauth("github", "gh-eve", "eve@example.com", True))
        self.assertEqual(me["user_id"], me2["user_id"])
        with self.assertRaises(AuthError):
            self.app.register_password("eve@example.com", "pw")
        with self.assertRaises(AuthError):
            self.app.login_password("eve@example.com", "")

    def test_same_subject_different_provider_is_different_identity(self):
        """features: M03
        acceptance: AC06
        expect: (provider, subject) is the identity key
        level: feature"""
        a = self.app.whoami(self.app.login_oauth("google", "1", None, False))
        b = self.app.whoami(self.app.login_oauth("github", "1", None, False))
        self.assertNotEqual(a["user_id"], b["user_id"])

    def test_oauth_requires_provider_and_subject(self):
        """features: M03
        acceptance: AC06
        expect: missing provider or subject raises AuthError
        level: form"""
        for p, s in [("", "1"), ("google", ""), (None, "1"), ("google", None)]:
            with self.assertRaises(AuthError):
                self.app.login_oauth(p, s, "x@example.com", True)

    def test_oauth_logout(self):
        """features: M02, M03
        acceptance: AC05
        expect: OAuth sessions are revoked by logout like password sessions
        level: auth"""
        t = self.app.login_oauth("google", "1", "x@example.com", True)
        self.app.logout(t)
        with self.assertRaises(AuthError):
            self.app.whoami(t)


# ----------------------------------------------------------------------------- V2: roles

class TestRoleMapping(unittest.TestCase):
    def setUp(self):
        self.app = create_app()

    def test_source_role_mapping(self):
        """features: M04
        acceptance: AC09
        expect: A user -> editor, B member -> viewer, C roles unchanged
        level: unit"""
        m = self.app.map_source_role
        self.assertEqual(m("A", "user"), "editor")
        self.assertEqual(m("B", "member"), "viewer")
        for r in ("viewer", "editor", "admin"):
            self.assertEqual(m("C", r), r)
        self.assertEqual(m("passbook", "user"), "editor")
        self.assertEqual(m("Linkup", "member"), "viewer")
        self.assertEqual(m("roster", "admin"), "admin")

    def test_unknown_role_or_app_raises_keyerror(self):
        """features: M04
        acceptance: AC09
        expect: unknown roles, roles from the wrong app and unknown apps raise KeyError
        level: unit"""
        m = self.app.map_source_role
        for app_id, role in [("A", "admin"), ("A", "member"), ("B", "user"), ("B", "admin"), ("C", "user"),
                             ("C", "owner"), ("Z", "user"), ("A", ""), ("A", None)]:
            with self.assertRaises(KeyError):
                m(app_id, role)

    def test_permission_check(self):
        """features: M04
        acceptance: AC09
        expect: viewer read; editor read and write; admin also manage_roles; unknown roles nothing
        level: authorization"""
        can = self.app.can
        self.assertTrue(can("viewer", "read"))
        self.assertFalse(can("viewer", "write"))
        self.assertTrue(can("editor", "write"))
        self.assertFalse(can("editor", "manage_roles"))
        self.assertTrue(can("admin", "manage_roles"))
        self.assertFalse(can("user", "read"))


class TestRoleAdmin(unittest.TestCase):
    def setUp(self):
        self.app = create_app()
        self.admin_id = self.app.bootstrap_admin("root@example.com", "rootpw")
        self.admin = self.app.login_password("root@example.com", "rootpw")
        self.uid = self.app.register_password("ana@example.com", "pw")
        self.ana = self.app.login_password("ana@example.com", "pw")

    def test_bootstrap_admin_creates_admin(self):
        """features: M05
        acceptance: AC13
        expect: bootstrap_admin creates an admin who can sign in
        level: feature"""
        self.assertEqual(self.app.whoami(self.admin),
                         {"user_id": self.admin_id, "email": "root@example.com", "role": "admin"})

    def test_bootstrap_admin_only_once(self):
        """features: M05
        acceptance: AC13
        expect: a second bootstrap_admin fails while an admin exists
        level: authorization"""
        with self.assertRaises(PermissionError):
            self.app.bootstrap_admin("other@example.com", "pw")
        with self.assertRaises(AuthError):
            self.app.bootstrap_admin("other@example.com", "pw")
        with self.assertRaises(AuthError):
            self.app.login_password("other@example.com", "pw")

    def test_admin_changes_role_and_it_applies_at_once(self):
        """features: M04, M05
        acceptance: AC10
        expect: admin sets ana to viewer then admin; ana's existing session shows each new role
        level: authorization"""
        self.app.set_role(self.admin, self.uid, "viewer")
        self.assertEqual(self.app.whoami(self.ana)["role"], "viewer")
        self.app.set_role(self.admin, self.uid, "admin")
        self.assertEqual(self.app.whoami(self.ana)["role"], "admin")
        # the new admin can now manage roles
        other = self.app.register_password("bob@example.com", "pw")
        self.app.set_role(self.ana, other, "viewer")
        self.assertEqual(self.app.whoami(self.app.login_password("bob@example.com", "pw"))["role"], "viewer")

    def test_non_admin_cannot_change_roles(self):
        """features: M05
        acceptance: AC11
        expect: editor and viewer callers get PermissionError and nothing changes
        level: authorization"""
        bob = self.app.register_password("bob@example.com", "pw")
        with self.assertRaises(PermissionError):
            self.app.set_role(self.ana, bob, "viewer")
        viewer_tok = self.app.login_oauth("google", "v", "v@example.com", True)
        with self.assertRaises(PermissionError):
            self.app.set_role(viewer_tok, bob, "admin")
        self.assertEqual(self.app.whoami(self.app.login_password("bob@example.com", "pw"))["role"], "editor")

    def test_invalid_or_logged_out_token_cannot_change_roles(self):
        """features: M02, M05
        acceptance: AC11
        expect: an unknown or logged-out admin token gets PermissionError (also an AuthError)
        level: authorization"""
        with self.assertRaises(PermissionError):
            self.app.set_role("garbage", self.uid, "admin")
        self.app.logout(self.admin)
        with self.assertRaises(PermissionError):
            self.app.set_role(self.admin, self.uid, "admin")
        with self.assertRaises(AuthError):
            self.app.set_role(self.admin, self.uid, "admin")
        self.assertEqual(self.app.whoami(self.ana)["role"], "editor")

    def test_nobody_raises_their_own_role(self):
        """features: M05
        acceptance: AC12
        expect: an editor or viewer trying to raise their own role is refused with PermissionError
        level: authorization"""
        with self.assertRaises(PermissionError):
            self.app.set_role(self.ana, self.uid, "admin")
        v = self.app.login_oauth("google", "v", "v@example.com", True)
        vid = self.app.whoami(v)["user_id"]
        for role in ("editor", "admin"):
            with self.assertRaises(PermissionError):
                self.app.set_role(v, vid, role)
        self.assertEqual(self.app.whoami(v)["role"], "viewer")

    def test_admin_may_lower_but_not_raise_own_role(self):
        """features: M05
        acceptance: AC12
        expect: an admin re-setting admin is a no-op; lowering is allowed; after that they cannot raise it back
        level: authorization"""
        self.app.set_role(self.admin, self.admin_id, "admin")
        self.app.set_role(self.admin, self.admin_id, "editor")
        self.assertEqual(self.app.whoami(self.admin)["role"], "editor")
        with self.assertRaises(PermissionError):
            self.app.set_role(self.admin, self.admin_id, "admin")

    def test_invalid_role_and_unknown_user(self):
        """features: M05
        acceptance: AC12
        expect: a role outside viewer/editor/admin raises ValueError; an unknown user id raises KeyError
        level: form"""
        for bad in ("superuser", "user", "member", "", None):
            with self.assertRaises(ValueError):
                self.app.set_role(self.admin, self.uid, bad)
        with self.assertRaises(KeyError):
            self.app.set_role(self.admin, "no-such-user", "viewer")
        self.assertEqual(self.app.whoami(self.ana)["role"], "editor")

    def test_role_change_on_joined_oauth_account(self):
        """features: M03, M04, M05
        acceptance: AC07, AC10
        expect: a role set on a password account applies when the same person signs in with a verified provider
        level: journey"""
        self.app.set_role(self.admin, self.uid, "viewer")
        me = self.app.whoami(self.app.login_oauth("google", "g-ana", "ana@example.com", True))
        self.assertEqual((me["user_id"], me["role"]), (self.uid, "viewer"))

    def test_core_journey(self):
        """features: M01, M02, M03, M04, M05
        acceptance: AC01, AC03, AC05, AC06, AC10
        expect: register, log in, OAuth join, admin promotes, logout, all through the public interface
        level: journey"""
        uid = self.app.register_password("zed@example.com", "pw")
        t = self.app.login_password("zed@example.com", "pw")
        t2 = self.app.login_oauth("google", "z", "zed@example.com", True)
        self.assertEqual(self.app.whoami(t2)["user_id"], uid)
        self.app.set_role(self.admin, uid, "admin")
        self.assertEqual(self.app.whoami(t)["role"], "admin")
        self.app.logout(t)
        with self.assertRaises(AuthError):
            self.app.whoami(t)
        self.assertEqual(self.app.whoami(t2)["role"], "admin")


class TestModuleInterface(unittest.TestCase):
    def test_interface_and_stdlib_only(self):
        """features: M01, M02, M03, M04, M05
        acceptance: AC01
        expect: AuthError and create_app importable; every interface method present; only standard library imports
        level: dependency"""
        import ast
        import unified.identity as mod
        app = mod.create_app()
        for name in ("register_password", "login_password", "login_oauth", "whoami", "logout", "set_role",
                     "map_source_role", "bootstrap_admin"):
            self.assertTrue(callable(getattr(app, name)), name)
        self.assertTrue(issubclass(mod.AuthError, Exception))
        tree = ast.parse(open(mod.__file__, encoding="utf-8").read())
        imported = {a.name.split(".")[0] for n in ast.walk(tree) if isinstance(n, ast.Import) for a in n.names}
        imported |= {n.module.split(".")[0] for n in ast.walk(tree) if isinstance(n, ast.ImportFrom) and n.module}
        stdlib = {"hashlib", "hmac", "os", "secrets", "threading", "time", "uuid"}
        self.assertTrue(imported <= stdlib, imported - stdlib)


if __name__ == "__main__":
    unittest.main()
