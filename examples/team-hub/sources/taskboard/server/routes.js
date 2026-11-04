// TaskBoard API routes (fictional example source)
const SESSION_IDLE_MINUTES = 60;

module.exports = (app, db, session) => {
  app.use(session({ cookie: { httpOnly: true }, rolling: true, maxAge: SESSION_IDLE_MINUTES * 60000 }));

  // Sign in: checks the password hash and starts a cookie session
  app.post('/api/login', async (req, res) => {
    const user = await db.users.findByEmail(req.body.email);
    if (!user || !(await db.users.checkPassword(user, req.body.password))) return res.status(401).json({ error: 'bad login' });
    req.session.userId = user.id;
    res.json({ id: user.id, name: user.name });
  });

  app.get('/api/users/:id', requireSession, async (req, res) => {
    const u = await db.users.get(req.params.id);
    res.json({ id: u.id, name: u.name, role: u.role });
  });

  app.get('/api/tasks', requireSession, async (req, res) => res.json(await db.tasks.list(req.query)));
  app.post('/api/tasks', requireSession, async (req, res) => res.status(201).json(await db.tasks.create(req.body, req.session.userId)));

  // Move a task between columns or assign it; the new assignee gets an in-app notification
  app.patch('/api/tasks/:id', requireSession, async (req, res) => {
    const task = await db.tasks.update(req.params.id, { status: req.body.status, assignee_id: req.body.assignee_id });
    if (req.body.assignee_id) await db.notifications.create(req.body.assignee_id, `You were assigned "${task.title}"`);
    res.json(task);
  });

  app.get('/api/tasks/:id/comments', requireSession, async (req, res) => res.json(await db.comments.forTask(req.params.id)));
  app.post('/api/tasks/:id/comments', requireSession, async (req, res) => res.status(201).json(await db.comments.add(req.params.id, req.session.userId, req.body.body)));

  // Notification bell: list and mark as read
  app.get('/api/notifications', requireSession, async (req, res) => res.json(await db.notifications.forUser(req.session.userId)));
  app.post('/api/notifications/:id/read', requireSession, async (req, res) => res.json(await db.notifications.markRead(req.params.id, req.session.userId)));

  // Share link: anyone holding the token can edit the board without an account
  app.get('/share/:token', async (req, res) => res.json(await db.boards.openShared(req.params.token)));

  function requireSession(req, res, next) {
    if (!req.session.userId) return res.status(401).json({ error: 'sign in' });
    next();
  }
};
