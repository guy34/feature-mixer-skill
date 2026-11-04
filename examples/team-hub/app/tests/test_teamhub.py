"""Team Hub tests. Each docstring names the menu features and acceptance criteria it
proves, what is expected, and the test level. Feature Mixer's run_tests.py
reads them when it runs the suite and records the evidence."""

import json
import os
import threading
import unittest
import urllib.error
import urllib.request
from datetime import datetime, timedelta, timezone

os.environ.setdefault("TEAMHUB_PASSWORD_ITERATIONS", "1000")  # fast hashing in tests only

from teamhub import approvals, auth, comments, dashboard, db, notifications, server, tasks  # noqa: E402
from teamhub.errors import Conflict, Forbidden, Invalid, NotFound, Unauthorized  # noqa: E402

PW = "correct horse battery"


class Base(unittest.TestCase):
    def setUp(self):
        self.conn = db.connect()
        self.owner = auth.create_user(self.conn, "olu@example.com", "Olu", PW, "owner", can_approve=True)
        self.amy = auth.create_user(self.conn, "amy@example.com", "Amy", PW)
        self.ben = auth.create_user(self.conn, "ben@example.com", "Ben", PW, can_approve=True)

    def tearDown(self):
        self.conn.close()

    def events(self, user):
        return [n["event"] for n in notifications.list_for(self.conn, user)]


class AccountsTest(Base):
    def test_sign_in_and_wrong_password(self):
        """features: M01
        acceptance: AC01
        expect: the right password starts a session for that user; a wrong one is refused with 401
        level: auth"""
        token, user = auth.login(self.conn, "AMY@example.com ", PW)
        self.assertEqual(auth.user_for_session(self.conn, token)["id"], self.amy["id"])
        with self.assertRaises(Unauthorized):
            auth.login(self.conn, "amy@example.com", "wrong password")

    def test_session_expires_after_idle_timeout(self):
        """features: M01
        acceptance: AC02
        expect: a session unused for more than 30 minutes is ended
        level: auth"""
        start = datetime.now(timezone.utc)
        token, _ = auth.login(self.conn, "amy@example.com", PW, at=start)
        auth.user_for_session(self.conn, token, at=start + timedelta(minutes=29))
        with self.assertRaises(Unauthorized):
            auth.user_for_session(self.conn, token, at=start + timedelta(minutes=60))

    def test_account_rules(self):
        """features: M01
        expect: bad emails, short passwords, unknown roles and duplicate emails are rejected
        level: form"""
        with self.assertRaises(Invalid):
            auth.create_user(self.conn, "not-an-email", "X", PW)
        with self.assertRaises(Invalid):
            auth.create_user(self.conn, "x@example.com", "X", "short")
        with self.assertRaises(Invalid):
            auth.create_user(self.conn, "x@example.com", "X", PW, role="requester")
        with self.assertRaises(Conflict):
            auth.create_user(self.conn, "amy@example.com", "Amy again", PW)

    def test_unified_roles_and_approve_permission(self):
        """features: M08, M09
        acceptance: AC10
        expect: owners and admins manage users; members do not; approving needs the approve permission
        level: authorization"""
        self.assertTrue(auth.can(self.owner, "user.manage"))
        self.assertFalse(auth.can(self.amy, "user.manage"))
        self.assertFalse(auth.can(self.amy, "approval.decide"))
        self.assertTrue(auth.can(self.ben, "approval.decide"))
        with self.assertRaises(Forbidden):
            auth.create_user(self.conn, "eve@example.com", "Eve", PW, acting=self.amy)
        admin = auth.create_user(self.conn, "ada@example.com", "Ada", PW, "admin", acting=self.owner)
        self.assertTrue(auth.can(admin, "task.manage_any"))


class TasksTest(Base):
    def test_task_board_flow(self):
        """features: M04
        acceptance: AC03
        expect: a task starts in todo, moves to doing and done, and rejects unknown statuses and bad titles
        level: feature"""
        t = tasks.create_task(self.conn, self.amy, "  Draft the plan  ", due_on="2026-12-01")
        self.assertEqual((t["title"], t["status"]), ("Draft the plan", "todo"))
        self.assertEqual(tasks.move_task(self.conn, self.amy, t["id"], "doing")["status"], "doing")
        self.assertEqual(tasks.move_task(self.conn, self.amy, t["id"], "done")["status"], "done")
        with self.assertRaises(Invalid):
            tasks.move_task(self.conn, self.amy, t["id"], "archived")
        with self.assertRaises(Invalid):
            tasks.create_task(self.conn, self.amy, "x" * 201)
        with self.assertRaises(Invalid):
            tasks.create_task(self.conn, self.amy, "Plan", due_on="next week")

    def test_only_allowed_people_move_tasks(self):
        """features: M04, M08
        expect: someone who is not the creator, assignee, owner or admin cannot move a task
        level: authorization"""
        t = tasks.create_task(self.conn, self.amy, "Private")
        with self.assertRaises(Forbidden):
            tasks.move_task(self.conn, self.ben, t["id"], "doing")
        self.assertEqual(tasks.move_task(self.conn, self.owner, t["id"], "doing")["status"], "doing")

    def test_assignment_notifies_on_every_channel_once(self):
        """features: M05, M10, M11
        acceptance: AC04
        expect: the assignee gets one in-app notification and one queued email, even if assigned twice
        level: interaction"""
        t = tasks.create_task(self.conn, self.amy, "Review budget")
        tasks.assign_task(self.conn, self.amy, t["id"], self.ben["id"])
        tasks.assign_task(self.conn, self.amy, t["id"], self.ben["id"])
        self.assertEqual(self.events(self.ben), ["task.assigned"])
        emails = notifications.outbox(self.conn, "email")
        self.assertEqual([e["target"] for e in emails], ["ben@example.com"])

    def test_no_notification_for_assigning_yourself(self):
        """features: M05, M10
        expect: assigning a task to yourself sends nothing
        level: feature"""
        tasks.create_task(self.conn, self.amy, "Mine", assignee_id=self.amy["id"])
        self.assertEqual(self.events(self.amy), [])

    def test_assignee_must_exist(self):
        """features: M05
        expect: assigning to an unknown user is rejected
        level: error"""
        t = tasks.create_task(self.conn, self.amy, "Plan")
        with self.assertRaises(Invalid):
            tasks.assign_task(self.conn, self.amy, t["id"], "00000000-0000-0000-0000-000000000000")


class NotificationEngineTest(Base):
    def test_push_channel_for_opted_in_browsers(self):
        """features: M12, M10
        acceptance: AC08
        expect: after opting in, a notification also queues a push to each subscribed browser; http endpoints are refused
        level: feature"""
        with self.assertRaises(Invalid):
            notifications.subscribe_push(self.conn, self.ben, "http://insecure.example/push")
        notifications.subscribe_push(self.conn, self.ben, "https://push.example/ben-laptop")
        with self.assertRaises(Conflict):
            notifications.subscribe_push(self.conn, self.ben, "https://push.example/ben-laptop")
        notifications.notify(self.conn, self.ben["id"], "test", "hello", "test:1")
        self.conn.commit()
        self.assertEqual([d["target"] for d in notifications.outbox(self.conn, "push")],
                         ["https://push.example/ben-laptop"])

    def test_preferences_choose_channels(self):
        """features: M10, M11, M12
        expect: turning email off stops email deliveries; in-app always arrives
        level: feature"""
        notifications.set_preferences(self.conn, self.ben, email=False)
        notifications.notify(self.conn, self.ben["id"], "test", "hello", "test:2")
        self.conn.commit()
        self.assertEqual(notifications.outbox(self.conn), [])
        self.assertEqual(self.events(self.ben), ["test"])
        with self.assertRaises(Invalid):
            notifications.set_preferences(self.conn, self.ben, email="yes")

    def test_read_and_privacy(self):
        """features: M10
        expect: a user can mark their own notification read, and cannot see or touch anyone else's
        level: auth"""
        nid = notifications.notify(self.conn, self.ben["id"], "test", "hello", "test:3")
        self.conn.commit()
        self.assertEqual(notifications.unread_count(self.conn, self.ben), 1)
        with self.assertRaises(NotFound):
            notifications.mark_read(self.conn, self.amy, nid)
        notifications.mark_read(self.conn, self.ben, nid)
        self.assertEqual(notifications.unread_count(self.conn, self.ben), 0)
        self.assertEqual(notifications.list_for(self.conn, self.amy), [])


class ApprovalsTest(Base):
    def setUp(self):
        super().setUp()
        self.task = tasks.create_task(self.conn, self.amy, "Buy laptops")

    def test_approval_journey(self):
        """features: M13, M10, M11
        acceptance: AC05
        expect: approvers are told about a request, the decision is recorded, and the requester is told
        level: journey"""
        a = approvals.request_approval(self.conn, self.amy, self.task["id"], "Budget line 4")
        self.assertIn("approval.requested", self.events(self.ben))
        self.assertIn("approval.requested", self.events(self.owner))
        done = approvals.decide(self.conn, self.ben, a["id"], "approved")
        self.assertEqual((done["status"], done["approver_id"]), ("approved", self.ben["id"]))
        self.assertEqual(self.events(self.amy), ["approval.decided"])

    def test_approval_rules(self):
        """features: M13, M09
        acceptance: AC05, AC10
        expect: members without the permission cannot decide, nobody decides their own request, and a decision is final
        level: authorization"""
        a = approvals.request_approval(self.conn, self.ben, self.task["id"])
        with self.assertRaises(Forbidden):
            approvals.decide(self.conn, self.amy, a["id"], "approved")
        with self.assertRaises(Forbidden):
            approvals.decide(self.conn, self.ben, a["id"], "approved")
        approvals.decide(self.conn, self.owner, a["id"], "rejected")
        with self.assertRaises(Conflict):
            approvals.decide(self.conn, self.owner, a["id"], "approved")
        with self.assertRaises(Invalid):
            approvals.decide(self.conn, self.owner, a["id"], "maybe")

    def test_pending_approval_blocks_closing(self):
        """features: M13, M04
        acceptance: AC06
        expect: a task cannot be moved to done while its approval is pending, and can once it is decided
        level: interaction"""
        a = approvals.request_approval(self.conn, self.amy, self.task["id"])
        with self.assertRaises(Conflict):
            approvals.request_approval(self.conn, self.amy, self.task["id"])
        with self.assertRaises(Conflict):
            tasks.move_task(self.conn, self.amy, self.task["id"], "done")
        approvals.decide(self.conn, self.ben, a["id"], "approved")
        self.assertEqual(tasks.move_task(self.conn, self.amy, self.task["id"], "done")["status"], "done")


class CommentsTest(Base):
    def test_threaded_comments_on_tasks_and_approvals(self):
        """features: M07, M10
        acceptance: AC07
        expect: replies nest under their parent, the parent's author is notified, and approvals take comments too
        level: feature"""
        t = tasks.create_task(self.conn, self.amy, "Plan")
        first = comments.add_comment(self.conn, self.amy, "task", t["id"], "Thoughts?")
        comments.add_comment(self.conn, self.ben, "task", t["id"], "Looks good", parent_id=first["id"])
        tree = comments.thread(self.conn, "task", t["id"])
        self.assertEqual(len(tree), 1)
        self.assertEqual(tree[0]["replies"][0]["body"], "Looks good")
        self.assertEqual(self.events(self.amy), ["comment.reply"])
        a = approvals.request_approval(self.conn, self.amy, t["id"])
        comments.add_comment(self.conn, self.ben, "approval", a["id"], "Which vendor?")
        self.assertEqual(len(comments.thread(self.conn, "approval", a["id"])), 1)

    def test_comment_rules(self):
        """features: M07
        expect: empty comments, replies across items and comments on missing items are rejected
        level: form"""
        t1 = tasks.create_task(self.conn, self.amy, "One")
        t2 = tasks.create_task(self.conn, self.amy, "Two")
        c = comments.add_comment(self.conn, self.amy, "task", t1["id"], "Hi")
        with self.assertRaises(Invalid):
            comments.add_comment(self.conn, self.amy, "task", t1["id"], "   ")
        with self.assertRaises(Invalid):
            comments.add_comment(self.conn, self.amy, "task", t2["id"], "Reply", parent_id=c["id"])
        with self.assertRaises(NotFound):
            comments.add_comment(self.conn, self.amy, "task", "00000000-0000-0000-0000-000000000000", "Hi")


class DashboardTest(Base):
    def test_workload_counts(self):
        """features: M14
        acceptance: AC09
        expect: open tasks per person exclude done ones, overdue counts open tasks due before today (UTC), pending approvals are counted
        level: feature"""
        a = tasks.create_task(self.conn, self.owner, "Late", assignee_id=self.amy["id"], due_on="2026-01-01")
        tasks.create_task(self.conn, self.owner, "Soon", assignee_id=self.amy["id"], due_on="2026-12-31")
        b = tasks.create_task(self.conn, self.owner, "Finished", assignee_id=self.ben["id"], due_on="2026-01-01")
        tasks.move_task(self.conn, self.owner, b["id"], "done")
        approvals.request_approval(self.conn, self.amy, a["id"])
        w = dashboard.workload(self.conn, self.owner, today="2026-06-01")
        people = {p["name"]: p["open"] for p in w["open_by_person"]}
        self.assertEqual(people, {"Amy": 2, "Ben": 0, "Olu": 0})
        self.assertEqual(w["overdue"], 1)
        self.assertEqual(w["pending_approvals"], 1)
        self.assertEqual(w["tasks_by_status"], {"todo": 2, "doing": 0, "done": 1})


class DatabaseTest(Base):
    def test_integrity(self):
        """features: M04, M13, M01
        expect: foreign keys and checks hold: no approval for a missing task, deleting a task removes its approvals, no unknown roles
        level: database"""
        import sqlite3
        t = tasks.create_task(self.conn, self.amy, "Plan")
        approvals.request_approval(self.conn, self.amy, t["id"])
        with self.assertRaises(sqlite3.IntegrityError):
            self.conn.execute("insert into approvals (id, task_id, requester_id, created_at) values ('x', 'missing', ?, 'now')",
                              (self.amy["id"],))
        self.conn.execute("delete from tasks where id = ?", (t["id"],))
        self.assertEqual(self.conn.execute("select count(*) from approvals").fetchone()[0], 0)
        with self.assertRaises(sqlite3.IntegrityError):
            self.conn.execute("update users set role = 'requester' where id = ?", (self.amy["id"],))


class HttpApiTest(unittest.TestCase):
    """The whole app over HTTP, the way a client uses it."""

    @classmethod
    def setUpClass(cls):
        cls.conn = db.connect()
        auth.create_user(cls.conn, "olu@example.com", "Olu", PW, "owner", can_approve=True)
        cls.httpd = server.serve(cls.conn, "127.0.0.1", 0)
        cls.base = f"http://127.0.0.1:{cls.httpd.server_address[1]}"
        cls.thread = threading.Thread(target=cls.httpd.serve_forever, daemon=True)
        cls.thread.start()

    @classmethod
    def tearDownClass(cls):
        cls.httpd.shutdown()
        cls.httpd.server_close()
        cls.conn.close()

    def call(self, method, path, body=None, cookie=None):
        data = json.dumps(body).encode() if body is not None else None
        req = urllib.request.Request(self.base + path, data=data, method=method)
        req.add_header("Content-Type", "application/json")
        if cookie:
            req.add_header("Cookie", cookie)
        try:
            with urllib.request.urlopen(req) as r:
                return r.status, json.loads(r.read()), r.headers
        except urllib.error.HTTPError as e:
            return e.code, json.loads(e.read()), e.headers

    def sign_in(self, email):
        status, body, headers = self.call("POST", "/api/session", {"email": email, "password": PW})
        self.assertEqual(status, 200, body)
        cookie = headers["Set-Cookie"]
        self.assertIn("HttpOnly", cookie)
        return cookie.split(";")[0]

    def test_end_to_end_journey(self):
        """features: M01, M04, M05, M07, M08, M09, M10, M11, M13, M14
        expect: an owner adds people, a member creates and assigns a task, asks for approval, an approver approves after a threaded discussion, the task closes, and every step shows up in notifications and the dashboard
        level: journey"""
        olu = self.sign_in("olu@example.com")
        s, b, _ = self.call("POST", "/api/users", {"email": "amy@example.com", "name": "Amy", "password": PW}, olu)
        self.assertEqual(s, 201, b)
        s, b, _ = self.call("POST", "/api/users", {"email": "ben@example.com", "name": "Ben", "password": PW,
                                                    "can_approve": True}, olu)
        ben_id = b["user"]["id"]
        amy, ben = self.sign_in("amy@example.com"), self.sign_in("ben@example.com")

        s, b, _ = self.call("POST", "/api/users", {"email": "eve@example.com", "name": "Eve", "password": PW}, amy)
        self.assertEqual((s, b["error"]["code"]), (403, "forbidden"))

        s, b, _ = self.call("POST", "/api/tasks", {"title": "Order laptops", "assignee_id": ben_id}, amy)
        self.assertEqual(s, 201, b)
        task_id = b["task"]["id"]
        s, b, _ = self.call("PATCH", f"/api/tasks/{task_id}", {"status": "doing"}, amy)
        self.assertEqual(b["task"]["status"], "doing")

        s, b, _ = self.call("POST", f"/api/tasks/{task_id}/approvals", {"note": "Two units"}, amy)
        self.assertEqual(s, 201, b)
        approval_id = b["approval"]["id"]
        s, b, _ = self.call("PATCH", f"/api/tasks/{task_id}", {"status": "done"}, amy)
        self.assertEqual((s, b["error"]["code"]), (409, "conflict"))

        s, b, _ = self.call("POST", f"/api/approvals/{approval_id}/comments", {"body": "Which model?"}, ben)
        parent = b["comment"]["id"]
        self.call("POST", f"/api/approvals/{approval_id}/comments", {"body": "The 14 inch", "parent_id": parent}, amy)
        s, b, _ = self.call("GET", f"/api/approvals/{approval_id}/comments", cookie=ben)
        self.assertEqual(b["comments"][0]["replies"][0]["body"], "The 14 inch")

        s, b, _ = self.call("POST", f"/api/approvals/{approval_id}/decision", {"decision": "approved"}, amy)
        self.assertEqual(s, 403)
        s, b, _ = self.call("POST", f"/api/approvals/{approval_id}/decision", {"decision": "approved"}, ben)
        self.assertEqual(b["approval"]["status"], "approved")
        s, b, _ = self.call("PATCH", f"/api/tasks/{task_id}", {"status": "done"}, amy)
        self.assertEqual(b["task"]["status"], "done")

        s, b, _ = self.call("GET", "/api/notifications", cookie=amy)
        self.assertEqual([n["event"] for n in b["notifications"]], ["approval.decided"])
        s, b, _ = self.call("GET", "/api/notifications", cookie=ben)
        self.assertEqual(sorted(n["event"] for n in b["notifications"]),
                         ["approval.requested", "comment.reply", "task.assigned"])
        s, b, _ = self.call("GET", "/api/dashboard", cookie=olu)
        self.assertEqual((b["tasks_by_status"]["done"], b["pending_approvals"]), (1, 0))

    def test_api_errors(self):
        """features: M01
        expect: no session gives 401, bad JSON gives 400, an unknown path gives 404, a wrong method gives 405, all in one error format
        level: api"""
        s, b, _ = self.call("GET", "/api/tasks")
        self.assertEqual((s, b["error"]["code"]), (401, "unauthorized"))
        req = urllib.request.Request(self.base + "/api/session", data=b"{not json", method="POST")
        try:
            urllib.request.urlopen(req)
        except urllib.error.HTTPError as e:
            self.assertEqual(e.code, 400)
        s, b, _ = self.call("GET", "/api/nothing-here")
        self.assertEqual(s, 404)
        s, b, _ = self.call("PUT", "/api/tasks")
        self.assertEqual(s, 405)
        s, b, _ = self.call("POST", "/api/session", {"email": "olu@example.com", "password": "nope"})
        self.assertEqual((s, b["error"]["message"]), (401, "wrong email or password"))

    def test_push_subscription_over_http(self):
        """features: M12
        expect: a signed-in user can register an https push endpoint over the API
        level: api"""
        olu = self.sign_in("olu@example.com")
        s, b, _ = self.call("POST", "/api/push-subscriptions", {"endpoint": "https://push.example/olu"}, olu)
        self.assertEqual(s, 201, b)
        s, b, _ = self.call("PATCH", "/api/me/notification-settings", {"email": False}, olu)
        self.assertEqual(b, {"email": False, "push": True})

    def test_sign_out(self):
        """features: M01
        expect: after signing out the old session cookie no longer works
        level: auth"""
        olu = self.sign_in("olu@example.com")
        self.assertEqual(self.call("GET", "/api/me", cookie=olu)[0], 200)
        self.call("DELETE", "/api/session", cookie=olu)
        self.assertEqual(self.call("GET", "/api/me", cookie=olu)[0], 401)


if __name__ == "__main__":
    unittest.main()
