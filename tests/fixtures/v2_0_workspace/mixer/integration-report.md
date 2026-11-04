# Team Hub: integration report

Run: `python3 app/run_integration.py` · Date: 2026-11-04 · Structured copy: `integration-report.json`

## Summary

| Total | Passed | Failed | Skipped |
| --- | --- | --- | --- |
| 23 | 23 | 0 | 0 |

Every kept feature with its proof:

| Feature | Tests passed | Status |
| --- | --- | --- |
| M01 | 7 of 7 | verified |
| M04 | 5 of 5 | verified |
| M05 | 4 of 4 | verified |
| M07 | 3 of 3 | verified |
| M08 | 3 of 3 | verified |
| M09 | 3 of 3 | verified |
| M10 | 8 of 8 | verified |
| M11 | 4 of 4 | verified |
| M12 | 3 of 3 | verified |
| M13 | 5 of 5 | verified |
| M14 | 2 of 2 | verified |

## Results

| Test | Level | Features | Expected | Actual | Status |
| --- | --- | --- | --- | --- | --- |
| test_teamhub.AccountsTest.test_account_rules | form | M01 | bad emails, short passwords, unknown roles and duplicate emails are rejected | as expected | pass |
| test_teamhub.AccountsTest.test_session_expires_after_idle_timeout | auth | M01 | a session unused for more than 30 minutes is ended | as expected | pass |
| test_teamhub.AccountsTest.test_sign_in_and_wrong_password | auth | M01 | the right password starts a session for that user; a wrong one is refused with 401 | as expected | pass |
| test_teamhub.AccountsTest.test_unified_roles_and_approve_permission | authorization | M08, M09 | owners and admins manage users; members do not; approving needs the approve permission | as expected | pass |
| test_teamhub.ApprovalsTest.test_approval_journey | journey | M13, M10, M11 | approvers are told about a request, the decision is recorded, and the requester is told | as expected | pass |
| test_teamhub.ApprovalsTest.test_approval_rules | authorization | M13, M09 | members without the permission cannot decide, nobody decides their own request, and a decision is final | as expected | pass |
| test_teamhub.ApprovalsTest.test_pending_approval_blocks_closing | interaction | M13, M04 | a task cannot be moved to done while its approval is pending, and can once it is decided | as expected | pass |
| test_teamhub.CommentsTest.test_comment_rules | form | M07 | empty comments, replies across items and comments on missing items are rejected | as expected | pass |
| test_teamhub.CommentsTest.test_threaded_comments_on_tasks_and_approvals | feature | M07, M10 | replies nest under their parent, the parent's author is notified, and approvals take comments too | as expected | pass |
| test_teamhub.DashboardTest.test_workload_counts | feature | M14 | open tasks per person exclude done ones, overdue counts open tasks due before today (UTC), pending approvals are counted | as expected | pass |
| test_teamhub.DatabaseTest.test_integrity | database | M04, M13, M01 | foreign keys and checks hold: no approval for a missing task, deleting a task removes its approvals, no unknown roles | as expected | pass |
| test_teamhub.HttpApiTest.test_api_errors | api | M01 | no session gives 401, bad JSON gives 400, an unknown path gives 404, a wrong method gives 405, all in one error format | as expected | pass |
| test_teamhub.HttpApiTest.test_end_to_end_journey | journey | M01, M04, M05, M07, M08, M09, M10, M11, M13, M14 | an owner adds people, a member creates and assigns a task, asks for approval, an approver approves after a threaded discussion, the task closes, and every step shows up in notifications and the dashboard | as expected | pass |
| test_teamhub.HttpApiTest.test_push_subscription_over_http | api | M12 | a signed-in user can register an https push endpoint over the API | as expected | pass |
| test_teamhub.HttpApiTest.test_sign_out | auth | M01 | after signing out the old session cookie no longer works | as expected | pass |
| test_teamhub.NotificationEngineTest.test_preferences_choose_channels | feature | M10, M11, M12 | turning email off stops email deliveries; in-app always arrives | as expected | pass |
| test_teamhub.NotificationEngineTest.test_push_channel_for_opted_in_browsers | feature | M12, M10 | after opting in, a notification also queues a push to each subscribed browser; http endpoints are refused | as expected | pass |
| test_teamhub.NotificationEngineTest.test_read_and_privacy | auth | M10 | a user can mark their own notification read, and cannot see or touch anyone else's | as expected | pass |
| test_teamhub.TasksTest.test_assignee_must_exist | error | M05 | assigning to an unknown user is rejected | as expected | pass |
| test_teamhub.TasksTest.test_assignment_notifies_on_every_channel_once | interaction | M05, M10, M11 | the assignee gets one in-app notification and one queued email, even if assigned twice | as expected | pass |
| test_teamhub.TasksTest.test_no_notification_for_assigning_yourself | feature | M05, M10 | assigning a task to yourself sends nothing | as expected | pass |
| test_teamhub.TasksTest.test_only_allowed_people_move_tasks | authorization | M04, M08 | someone who is not the creator, assignee, owner or admin cannot move a task | as expected | pass |
| test_teamhub.TasksTest.test_task_board_flow | feature | M04 | a task starts in todo, moves to doing and done, and rejects unknown statuses and bad titles | as expected | pass |

## Failures and fixes

None in this run. Two problems were found and fixed while building: the server did not answer PUT with the JSON 405 error (added the handler), and a journey test expected the reply notification on the wrong person (corrected the test). See mixer-log.md.

## Not testable here

| What | Why | How the user can check it |
| --- | --- | --- |
| Email actually arriving in an inbox | No email provider is connected in this example; deliveries stop at the outbox | Connect a provider with your own keys, send one notification, check the inbox |
| Push actually showing in a browser | Needs a real web push service and a browser | Subscribe a browser over HTTPS, trigger an assignment, watch for the push |
