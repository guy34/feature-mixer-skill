# Unified Identity: integration report

Run `20261105T130255807151Z-0dd3fe` by run_tests.py · Command: `python -m unittest discover -s tests -t . (Feature Mixer harness)` · Framework: unittest
Started 2026-11-05T13:02:55+00:00 · Finished 2026-11-05T13:02:57+00:00 · Exit code 0 · Outcome exited · **Verdict: passed**
Evidence: `test-runs/20261105T130255807151Z-0dd3fe/output.log` (sha256 7750d0171a71...), `test-runs/20261105T130255807151Z-0dd3fe/results.xml` (sha256 b4c0c3d0a39f...)

Statuses come from the results file of this run. Run `verify_tests.py` to check this report against the evidence; only verified passes prove a feature.

## Summary

| Total | Passed | Failed | Skipped | Not executed | Unverified |
| --- | --- | --- | --- | --- | --- |
| 32 | 32 | 0 | 0 | 0 | 0 |

| Feature | Tests passed | Status |
| --- | --- | --- |
| M01 | 14 of 14 | passing |
| M02 | 11 of 11 | passing |
| M03 | 15 of 15 | passing |
| M04 | 10 of 10 | passing |
| M05 | 8 of 8 | passing |

## Results

| Test | Level | Features | Acceptance | Expected | Actual | Status |
| --- | --- | --- | --- | --- | --- | --- |
| tests.test_dependencies.DependencyTests.test_standard_library_only | dependency | M01, M02, M03, M04, M05 |  | the unified package imports only the standard library and itself | as expected | passed |
| tests.test_identity.ModuleTests.test_concurrent_registration_one_winner | feature | M01 |  | concurrent registrations of one email create exactly one account | as expected | passed |
| tests.test_identity.ModuleTests.test_interface_and_file_import | unit | M01, M02, M03, M04, M05 |  | create_app, AuthError and every interface method exist; identity.py also loads as a plain file | as expected | passed |
| tests.test_identity.OAuthTests.test_oauth_email_verified_must_be_true | feature | M03 | AC06 | truthy non-boolean values such as "true", "false", 1 never count as verified | as expected | passed |
| tests.test_identity.OAuthTests.test_oauth_input_validated | feature | M03 |  | empty or non-string provider or subject, and malformed emails, raise AuthError | as expected | passed |
| tests.test_identity.OAuthTests.test_oauth_new_user_is_viewer_and_stable | feature | M03, M04 | AC07 | a new provider identity gets one viewer account, returned again on the next sign-in | as expected | passed |
| tests.test_identity.OAuthTests.test_oauth_unverified_does_not_claim_email | interaction | M03, M01 |  | an unverified provider email does not block the real owner from registering | as expected | passed |
| tests.test_identity.OAuthTests.test_oauth_unverified_email_creates_separate_account | interaction | M03, M01 | AC06 | a provider sign-in with the same but unverified email gets a separate viewer account | as expected | passed |
| tests.test_identity.OAuthTests.test_oauth_verified_email_links_existing_account | interaction | M03, M01 | AC05 | a provider sign-in with the same verified email returns a token for the same account, role kept | as expected | passed |
| tests.test_identity.OAuthTests.test_oauth_verified_new_user_owns_email | interaction | M03, M01 |  | once a verified provider account owns an email, password registration of it is refused and a second | as expected | passed |
| tests.test_identity.OAuthTests.test_oauth_without_email_creates_separate_account | feature | M03 |  | a provider sign-in without an email never links and has email None | as expected | passed |
| tests.test_identity.OAuthTests.test_same_subject_different_providers_are_different_identities | feature | M03 |  | identities are keyed by (provider, subject) | as expected | passed |
| tests.test_identity.PasswordTests.test_duplicate_registration_refused | feature | M01 | AC02 | a second registration of the same email (any case) raises AuthError and the first password still works | as expected | passed |
| tests.test_identity.PasswordTests.test_email_case_normalised | feature | M01, M02, M03 |  | emails are trimmed and lowercased for sign-up, login and linking | as expected | passed |
| tests.test_identity.PasswordTests.test_login_failures_raise_autherror | feature | M02 | AC03 | wrong password, unknown email and malformed input all raise AuthError with the same message | as expected | passed |
| tests.test_identity.PasswordTests.test_password_stored_hashed_with_salt | unit | M01 |  | no plaintext password is stored; PBKDF2-SHA256 with a 16-byte random salt and 100000 iterations | as expected | passed |
| tests.test_identity.PasswordTests.test_register_and_login_password | feature | M01, M02, M04 | AC01 | register returns an id; login returns a token; whoami shows the id, normalised email and role editor | as expected | passed |
| tests.test_identity.PasswordTests.test_registration_input_validated | feature | M01 |  | invalid emails and empty or non-string passwords are refused with AuthError (a ValueError) | as expected | passed |
| tests.test_identity.PasswordTests.test_user_ids_are_opaque_strings | unit | M01, M03 |  | every user id is a unique opaque text id, not a source's counter | as expected | passed |
| tests.test_identity.RoleChangeTests.test_admin_sets_role | feature | M05, M04 | AC10 | an admin changes another user's role and it shows at once; unknown roles and users are refused | as expected | passed |
| tests.test_identity.RoleChangeTests.test_bootstrap_admin_only_once | feature | M05 | AC12 | the first bootstrap creates an admin; a second is refused while an admin exists | as expected | passed |
| tests.test_identity.RoleChangeTests.test_nobody_raises_own_role | feature | M05 | AC11 | viewers and editors cannot raise their own role; lowering is not raising | as expected | passed |
| tests.test_identity.RoleChangeTests.test_non_admin_cannot_set_role | feature | M05, M04 | AC09 | viewers, editors and invalid sessions get PermissionError and nothing changes | as expected | passed |
| tests.test_identity.RoleChangeTests.test_role_change_needs_live_session | feature | M05, M02 |  | an admin's revoked or expired session cannot change roles | as expected | passed |
| tests.test_identity.SessionTests.test_logout_revokes_token | feature | M02 | AC04 | after logout whoami raises AuthError; other sessions stay valid; logout twice is harmless | as expected | passed |
| tests.test_identity.SessionTests.test_session_expires | feature | M02, M03 | AC04 | a session older than its lifetime raises AuthError | as expected | passed |
| tests.test_identity.SessionTests.test_tokens_not_stored_in_clear | unit | M02 |  | the session store keeps only a hash of each token | as expected | passed |
| tests.test_identity.SessionTests.test_whoami_invalid_token | feature | M02 |  | unknown, empty and non-string tokens raise AuthError | as expected | passed |
| tests.test_journey.JourneyTests.test_journey_full_identity_flow | journey | M01, M02, M03, M04, M05 | AC01, AC05, AC06, AC10 | setup admin; a person signs up with a password, signs in with a verified provider email into the | as expected | passed |
| tests.test_roles.RoleMappingTests.test_map_source_role | unit | M04 | AC08 | A user->editor, B member->viewer, C roles unchanged; unknown roles and apps raise KeyError | as expected | passed |
| tests.test_roles.RoleMappingTests.test_no_source_role_maps_to_admin_except_roster_admin | unit | M04 |  | only C's admin becomes admin; no source role is escalated | as expected | passed |
| tests.test_roles.RoleMappingTests.test_permission_check | unit | M04 |  | viewer reads; editor reads and writes; only admin manages roles; unknown roles get nothing | as expected | passed |

## Failures and fixes

None in this run.

## Not testable here

| What | Why | How the user can check it |
| --- | --- | --- |
| A real OAuth provider (redirect, code exchange, ID-token signature, audience and expiry checks) | not in Linkup's source; no network, no provider account here (external_api unavailable) | wire login_oauth behind a provider library that verifies the ID token, then test against the provider's test tenant |
| Persistence and data migration from the sources | sources keep data in memory only; nothing to migrate | if data is imported later, follow design/migration-plan.md with its own approval |
| Load and concurrency beyond one process | in-memory store, one process | load test once a persistent store exists |
