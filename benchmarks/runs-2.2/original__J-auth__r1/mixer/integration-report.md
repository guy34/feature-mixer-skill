# Unified Identity: integration report

Run `20261105T130716734720Z` by run_tests.py · Command: `python -m unittest discover -s tests -t . (Feature Mixer harness)` · Framework: unittest
Started 2026-11-05T13:07:16+00:00 · Finished 2026-11-05T13:07:22+00:00 · Exit code 0
Evidence: `test-runs/20261105T130716734720Z/output.log` (sha256 cc5ca57ba5f5...), `test-runs/20261105T130716734720Z/results.xml` (sha256 49f7922e0d97...)

Statuses come from the results file of this run. Run `verify_tests.py` to check this report against the evidence; only verified passes prove a feature.

## Summary

| Total | Passed | Failed | Skipped | Not executed | Unverified |
| --- | --- | --- | --- | --- | --- |
| 33 | 33 | 0 | 0 | 0 | 0 |

| Feature | Tests passed | Status |
| --- | --- | --- |
| M01 | 11 of 11 | passing |
| M02 | 11 of 11 | passing |
| M03 | 12 of 12 | passing |
| M04 | 9 of 9 | passing |
| M05 | 11 of 11 | passing |

## Results

| Test | Level | Features | Acceptance | Expected | Actual | Status |
| --- | --- | --- | --- | --- | --- | --- |
| tests.test_identity.TestModuleInterface.test_interface_and_stdlib_only | dependency | M01, M02, M03, M04, M05 | AC01 | AuthError and create_app importable; every interface method present; only standard library imports | as expected | passed |
| tests.test_identity.TestOAuth.test_new_oauth_user_is_viewer_and_stable | feature | M03, M04 | AC06 | first OAuth sign-in creates a viewer; the same provider+subject returns the same user | as expected | passed |
| tests.test_identity.TestOAuth.test_oauth_logout | auth | M02, M03 | AC05 | OAuth sessions are revoked by logout like password sessions | as expected | passed |
| tests.test_identity.TestOAuth.test_oauth_requires_provider_and_subject | form | M03 | AC06 | missing provider or subject raises AuthError | as expected | passed |
| tests.test_identity.TestOAuth.test_only_true_counts_as_verified | authorization | M03 | AC08 | truthy non-boolean email_verified values do not join accounts | as expected | passed |
| tests.test_identity.TestOAuth.test_same_subject_different_provider_is_different_identity | feature | M03 | AC06 | (provider, subject) is the identity key | as expected | passed |
| tests.test_identity.TestOAuth.test_unverified_email_creates_separate_account | interaction | M01, M03 | AC08 | an unverified OAuth email equal to a password account's email creates a separate viewer account | as expected | passed |
| tests.test_identity.TestOAuth.test_unverified_oauth_does_not_block_registration | interaction | M01, M03 | AC08 | an unverified OAuth account never claims its email; the real owner can still register it | as expected | passed |
| tests.test_identity.TestOAuth.test_verified_email_joins_password_account | interaction | M01, M02, M03 | AC07 | a verified OAuth email equal to a password account's email signs in to that account and keeps its role | as expected | passed |
| tests.test_identity.TestOAuth.test_verified_oauth_account_owns_email | interaction | M01, M03 | AC07 | a verified OAuth-created account owns its email: another provider joins it and password registration is refused | as expected | passed |
| tests.test_identity.TestPasswordAccounts.test_duplicate_email_rejected_and_original_kept | feature | M01 | AC02 | registering an existing email (any case) fails; the first password still works | as expected | passed |
| tests.test_identity.TestPasswordAccounts.test_invalid_and_expired_tokens | auth | M02 | AC05 | unknown, None and expired tokens raise AuthError | as expected | passed |
| tests.test_identity.TestPasswordAccounts.test_invalid_registration_input | form | M01 | AC02 | empty or malformed email and empty password are refused | as expected | passed |
| tests.test_identity.TestPasswordAccounts.test_login_is_case_insensitive_on_email | auth | M02 | AC03 | login with a differently cased email reaches the same account; whoami shows the normalised email | as expected | passed |
| tests.test_identity.TestPasswordAccounts.test_logout_invalidates_token | auth | M02 | AC05 | after logout whoami raises AuthError; other sessions survive; logout is idempotent | as expected | passed |
| tests.test_identity.TestPasswordAccounts.test_password_not_stored_in_clear | database | M01 | AC01 | the stored password hash is salted PBKDF2 and never the password | as expected | passed |
| tests.test_identity.TestPasswordAccounts.test_register_returns_id_and_editor_role | feature | M01, M02, M04 | AC01 | register_password returns a user id; the account's role is editor (A's user) | as expected | passed |
| tests.test_identity.TestPasswordAccounts.test_separate_apps_do_not_share_state | unit | M01 | AC01 | two create_app() instances keep separate users | as expected | passed |
| tests.test_identity.TestPasswordAccounts.test_tokens_are_unique_per_login | auth | M02 | AC03 | two logins give two different working tokens | as expected | passed |
| tests.test_identity.TestPasswordAccounts.test_wrong_password_and_unknown_email_raise_autherror | auth | M02 | AC04 | wrong password, unknown email and empty password all raise AuthError | as expected | passed |
| tests.test_identity.TestRoleAdmin.test_admin_changes_role_and_it_applies_at_once | authorization | M04, M05 | AC10 | admin sets ana to viewer then admin; ana's existing session shows each new role | as expected | passed |
| tests.test_identity.TestRoleAdmin.test_admin_may_lower_but_not_raise_own_role | authorization | M05 | AC12 | an admin re-setting admin is a no-op; lowering is allowed; after that they cannot raise it back | as expected | passed |
| tests.test_identity.TestRoleAdmin.test_bootstrap_admin_creates_admin | feature | M05 | AC13 | bootstrap_admin creates an admin who can sign in | as expected | passed |
| tests.test_identity.TestRoleAdmin.test_bootstrap_admin_only_once | authorization | M05 | AC13 | a second bootstrap_admin fails while an admin exists | as expected | passed |
| tests.test_identity.TestRoleAdmin.test_core_journey | journey | M01, M02, M03, M04, M05 | AC01, AC03, AC05, AC06, AC10 | register, log in, OAuth join, admin promotes, logout, all through the public interface | as expected | passed |
| tests.test_identity.TestRoleAdmin.test_invalid_or_logged_out_token_cannot_change_roles | authorization | M02, M05 | AC11 | an unknown or logged-out admin token gets PermissionError (also an AuthError) | as expected | passed |
| tests.test_identity.TestRoleAdmin.test_invalid_role_and_unknown_user | form | M05 | AC12 | a role outside viewer/editor/admin raises ValueError; an unknown user id raises KeyError | as expected | passed |
| tests.test_identity.TestRoleAdmin.test_nobody_raises_their_own_role | authorization | M05 | AC12 | an editor or viewer trying to raise their own role is refused with PermissionError | as expected | passed |
| tests.test_identity.TestRoleAdmin.test_non_admin_cannot_change_roles | authorization | M05 | AC11 | editor and viewer callers get PermissionError and nothing changes | as expected | passed |
| tests.test_identity.TestRoleAdmin.test_role_change_on_joined_oauth_account | journey | M03, M04, M05 | AC07, AC10 | a role set on a password account applies when the same person signs in with a verified provider | as expected | passed |
| tests.test_identity.TestRoleMapping.test_permission_check | authorization | M04 | AC09 | viewer read; editor read and write; admin also manage_roles; unknown roles nothing | as expected | passed |
| tests.test_identity.TestRoleMapping.test_source_role_mapping | unit | M04 | AC09 | A user -> editor, B member -> viewer, C roles unchanged | as expected | passed |
| tests.test_identity.TestRoleMapping.test_unknown_role_or_app_raises_keyerror | unit | M04 | AC09 | unknown roles, roles from the wrong app and unknown apps raise KeyError | as expected | passed |

## Failures and fixes

None in this run.

## Not testable here

| What | Why | How the user can check it |
| --- | --- | --- |
| A real OAuth provider (redirect, code exchange, ID-token signature, audience and nonce checks) | Not in Linkup's provided code (unknown) and network not approved; login_oauth trusts its caller's already-verified provider response | Put a provider library in front of login_oauth and test against the provider's sandbox |
| Persistence across restarts | State is in memory by design (as in the sources) | Add a storage layer and rerun this suite against it |
| Concurrency under load | Only a lock is used; no load test was run | Run parallel register/login/set_role calls against one app |
| Real source data migration | Sources keep no persisted data | Follow design/migration-plan.md if data appears |
