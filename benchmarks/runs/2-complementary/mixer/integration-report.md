# FileShare (Uploader + Previewer + ShareLink): integration report

Run `20261104T125111798138Z` by run_tests.py · Command: `python -m unittest discover -s tests -t . (Feature Mixer harness)` · Framework: unittest
Started 2026-11-04T12:51:11+00:00 · Finished 2026-11-04T12:51:13+00:00 · Exit code 0
Evidence: `test-runs/20261104T125111798138Z/output.log` (sha256 84504762758d...), `test-runs/20261104T125111798138Z/results.xml` (sha256 8683064de173...)

Statuses come from the results file of this run. Run `verify_tests.py` to check this report against the evidence; only verified passes prove a feature.

## Summary

| Total | Passed | Failed | Skipped | Not executed | Unverified |
| --- | --- | --- | --- | --- | --- |
| 38 | 38 | 0 | 0 | 0 | 0 |

| Feature | Tests passed | Status |
| --- | --- | --- |
| M01 | 11 of 11 | passing |
| M02 | 8 of 8 | passing |
| M03 | 3 of 3 | passing |
| M04 | 7 of 7 | passing |
| M05 | 3 of 3 | passing |
| M06 | 2 of 2 | passing |
| M07 | 8 of 8 | passing |
| M08 | 4 of 4 | passing |
| M09 | 11 of 11 | passing |
| M10 | 3 of 3 | passing |

## Results

| Test | Level | Features | Acceptance | Expected | Actual | Status |
| --- | --- | --- | --- | --- | --- | --- |
| tests.test_journey.DependencyTests.test_app_imports_only_the_standard_library | dependency | M01, M04, M07 |  | every import in the fileshare package is the standard library or the package itself | as expected | passed |
| tests.test_journey.JourneyTests.test_upload_preview_share_open_revoke | journey | M01, M02, M04, M07, M08, M09, M10 | AC13 | register, upload, list, preview, share with a password, recipient opens and downloads, owner revokes, link dies | as expected | passed |
| tests.test_v1_core.AccountsTests.test_account_password_is_salted_pbkdf2 | database | M01 |  | account passwords are stored as pbkdf2_sha256 with a per-user salt, never in plain text | as expected | passed |
| tests.test_v1_core.AccountsTests.test_register_login_logout | auth | M01, M02 |  | register sets an http-only session cookie; logout ends it; login with the right password restores it | as expected | passed |
| tests.test_v1_core.AccountsTests.test_session_expires | auth | M02 |  | a session older than 7 days answers 401 | as expected | passed |
| tests.test_v1_core.AccountsTests.test_wrong_password_and_duplicate_username | auth | M01 |  | wrong password is 401 bad_credentials; a taken username is 409; short passwords are 400 | as expected | passed |
| tests.test_v1_core.FallbackPreviewTests.test_other_types_have_no_preview | feature | M06 | AC08 | .pdf, .zip and extensionless files preview as kind none with the reason | as expected | passed |
| tests.test_v1_core.ListTests.test_each_user_sees_only_their_files | auth | M02 | AC04 | two users each list only their own files, newest first | as expected | passed |
| tests.test_v1_core.ListTests.test_empty_list | feature | M02 |  | a new user gets an empty list | as expected | passed |
| tests.test_v1_core.PlatformTests.test_invalid_json_is_400 | api | M07 |  | a malformed JSON body answers 400 invalid_json | as expected | passed |
| tests.test_v1_core.PlatformTests.test_pages_and_unknown_routes | navigation | M02, M09 |  | / and /s/<token> serve HTML; unknown routes are 404 and wrong methods 405, both in the JSON error shape | as expected | passed |
| tests.test_v1_core.PlatformTests.test_schema_created_from_empty_with_foreign_keys | database | M01 |  | every table exists after start and foreign keys cascade from files | as expected | passed |
| tests.test_v1_core.TextPreviewTests.test_preview_of_someone_elses_file_is_404 | auth | M04 |  | previewing another user's file answers 404 not_found | as expected | passed |
| tests.test_v1_core.TextPreviewTests.test_text_preview_first_20_lines | feature | M04 | AC06 | .txt, .md and .csv (any case) preview as kind text with at most 20 lines | as expected | passed |
| tests.test_v1_core.TextPreviewTests.test_text_preview_replaces_invalid_utf8 | feature | M04 | AC06 | undecodable bytes become replacement characters instead of an error | as expected | passed |
| tests.test_v1_core.UploadTests.test_file_endpoints_need_sign_in | auth | M01, M02, M03, M04, M07 | AC03 | every owner endpoint answers 401 with the JSON error shape when nobody is signed in | as expected | passed |
| tests.test_v1_core.UploadTests.test_upload_limit_is_10_mb | feature | M01 | AC02 | exactly 10485760 bytes is accepted; 10485761 is 413 file_too_large and nothing is stored | as expected | passed |
| tests.test_v1_core.UploadTests.test_upload_rejects_oversize_content_length_before_reading | api | M01 | AC02 | a Content-Length over the limit is refused with 413 without reading the body | as expected | passed |
| tests.test_v1_core.UploadTests.test_upload_returns_file | api | M01 | AC01 | 201 with id, name, size and a guessed content type | as expected | passed |
| tests.test_v1_core.UploadTests.test_upload_validation | form | M01 |  | missing or unsafe names are 400 invalid_name; a missing Content-Length is 411 | as expected | passed |
| tests.test_v2_sharing.CreateLinkTests.test_custom_expiry_and_validation | form | M07 | AC09 | positive hours are honoured; 0, negative, text, booleans and null are 400 invalid_expiry | as expected | passed |
| tests.test_v2_sharing.CreateLinkTests.test_default_expiry_is_24_hours | feature | M07 | AC09 | a link without expires_in_hours expires exactly 24 h after creation and has a 16-byte url-safe token | as expected | passed |
| tests.test_v2_sharing.CreateLinkTests.test_expired_link_is_404 | feature | M07, M09 | AC09 | a link opens up to its expiry second and answers 404 not_found after it | as expected | passed |
| tests.test_v2_sharing.CreateLinkTests.test_only_the_owner_can_create_links | auth | M07 | AC09 | another user creating a link to alice's file gets 404 and no link is stored; unknown files are 404 | as expected | passed |
| tests.test_v2_sharing.OpenLinkTests.test_anonymous_download | api | M09 | AC11 | the content route returns the exact bytes as an attachment for non-image types | as expected | passed |
| tests.test_v2_sharing.OpenLinkTests.test_anonymous_open_shows_metadata_and_preview | interaction | M09, M04 | AC11 | without a session the link returns name, size, content type and the text preview | as expected | passed |
| tests.test_v2_sharing.OpenLinkTests.test_link_gives_access_to_one_file_only | auth | M09, M02 |  | a link holder cannot list the owner's files or reach other files through owner routes | as expected | passed |
| tests.test_v2_sharing.OpenLinkTests.test_unknown_token_is_404 | api | M09 | AC11 | an unknown token answers 404 with the same message as an expired one | as expected | passed |
| tests.test_v3_should.DeleteTests.test_cannot_delete_someone_elses_file | auth | M03 | AC05 | bob deleting alice's file gets 404 and alice still has it | as expected | passed |
| tests.test_v3_should.DeleteTests.test_delete_removes_file_and_its_links | database | M03, M09 | AC05 | 204; the file leaves the list, its bytes are gone, and its share link answers 404 | as expected | passed |
| tests.test_v3_should.ImagePreviewTests.test_image_preview_through_a_share_link | interaction | M05, M09 | AC07 | a shared image previews with a link-scoped URL that serves the image without a session | as expected | passed |
| tests.test_v3_should.ImagePreviewTests.test_image_preview_url_serves_the_image | feature | M05 | AC07 | .png/.jpg/.gif preview as kind image; the URL serves the bytes inline with an image content type | as expected | passed |
| tests.test_v3_should.ImagePreviewTests.test_svg_and_html_are_downloads_not_inline | feature | M05, M06 |  | types outside png/jpg/gif (svg, html) get no image preview and are served as attachments | as expected | passed |
| tests.test_v3_should.PasswordLinkTests.test_invalid_password_value | form | M08 |  | an empty or non-string password is 400 invalid_password | as expected | passed |
| tests.test_v3_should.PasswordLinkTests.test_password_required_and_checked | feature | M08, M09 | AC10 | no password is 403 password_required, a wrong one 403 wrong_password, the right one opens metadata and content | as expected | passed |
| tests.test_v3_should.PasswordLinkTests.test_password_stored_as_salted_slow_hash | database | M08 | AC10 | the stored hash is pbkdf2_sha256 with a salt, not ShareLink's unsalted SHA-256 hex, and two links with the same password differ | as expected | passed |
| tests.test_v3_should.RevokeTests.test_other_user_cannot_revoke | auth | M10 | AC12 | bob revoking alice's link gets 404 and the link keeps working | as expected | passed |
| tests.test_v3_should.RevokeTests.test_owner_revokes_link | feature | M10, M09 | AC12 | 204, after which the link answers 404; revoking again is 404 | as expected | passed |

## Failures and fixes

None in this run.

## Not testable here

Added by Claude after the run (not from the results file):

- The two HTML pages' JavaScript (index.html, share.html): no browser was used; only that the pages are served was tested.
- A real socket server (`python3 -m fileshare` via wsgiref): tests call the WSGI app in-process; the server was not started (no network use approved).
- Production PBKDF2 cost: tests use 1000 iterations for speed; the default 200000 was not exercised.
- Load, concurrency, rate limiting and a security review: not done.
