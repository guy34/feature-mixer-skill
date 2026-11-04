// Approvals API (fictional example source)
const jwt = require('jsonwebtoken');
const TOKEN_IDLE_MINUTES = 30;

module.exports = (app, db, mailer) => {
  // Sign in: returns a JWT the client sends as "Authorization: Bearer ..."
  app.post('/api/v1/auth/token', async (req, res) => {
    const user = await db.users.verify(req.body.email, req.body.password);
    if (!user) return res.status(401).json({ message: 'invalid credentials' });
    res.json({ token: jwt.sign({ sub: user.id, role: user.role }, process.env.JWT_SECRET, { expiresIn: `${TOKEN_IDLE_MINUTES}m` }) });
  });

  app.get('/api/v1/users/:id', bearer, async (req, res) => {
    const u = await db.users.get(Number(req.params.id));
    res.json({ id: u.id, full_name: u.full_name, role: u.role });
  });

  app.post('/api/v1/requests', bearer, async (req, res) => res.status(201).json(await db.requests.create(req.user.sub, req.body.title)));

  // Decide: only approvers and admins, never on your own request; the requester is emailed
  app.post('/api/v1/requests/:id/decision', bearer, async (req, res) => {
    if (!['approver', 'admin'].includes(req.user.role)) return res.status(403).json({ message: 'approvers only' });
    const request = await db.requests.get(Number(req.params.id));
    if (request.requester_id === req.user.sub) return res.status(403).json({ message: 'cannot approve your own request' });
    const decided = await db.requests.decide(request.id, req.user.sub, req.body.decision);
    await db.outbox.queue(decided.requester_email, `Request ${decided.status}`, `"${decided.title}" was ${decided.status}.`);
    res.json(decided);
  });

  // Threaded comments: a reply carries parent_id
  app.get('/api/v1/requests/:id/comments', bearer, async (req, res) => res.json(await db.comments.thread(Number(req.params.id))));
  app.post('/api/v1/requests/:id/comments', bearer, async (req, res) => res.status(201).json(await db.comments.add(Number(req.params.id), req.user.sub, req.body.body, req.body.parent_id)));

  function bearer(req, res, next) {
    try { req.user = jwt.verify((req.headers.authorization || '').replace('Bearer ', ''), process.env.JWT_SECRET); next(); }
    catch (e) { res.status(401).json({ message: 'token required' }); }
  }
};
