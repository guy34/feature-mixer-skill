# Team Hub

The unified app Feature Mixer built in this example: tasks and assignment
(from TaskBoard), approvals, roles and threaded comments (from Approvals),
and a workload dashboard and push notifications (rebuilt from Pulse's public
docs), with one notification engine for in-app, email and push.

It is a JSON API on Python 3.8+ with nothing to install.

```bash
cd examples/team-hub/app
python3 -m teamhub create-user --email you@example.com --name You --role owner --can-approve
python3 -m teamhub serve            # http://127.0.0.1:8000
```

Try it:

```bash
curl -i -X POST localhost:8000/api/session -d '{"email":"you@example.com","password":"..."}'
# copy the session cookie from Set-Cookie, then:
curl -b 'session=...' -X POST localhost:8000/api/tasks -d '{"title":"First task"}'
curl -b 'session=...' localhost:8000/api/dashboard
```

Tests and the integration report:

```bash
python3 -m unittest discover -s tests -t .
python3 run_integration.py          # runs them via Feature Mixer's run_tests.py and verifies the report
```

Settings are environment variables (see `teamhub/config.py`). Email and
push deliveries are queued in the `deliveries` table; connecting a real email
provider or web push service is left to whoever runs it, with their own keys.
