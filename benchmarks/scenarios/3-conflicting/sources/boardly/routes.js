// Boardly API (illustrative). Cookie sessions; every post waits for a moderator.
const MAX_POST_LENGTH = 5000;
module.exports = (app, db) => {
  app.post('/api/login', async (req, res) => { req.session.userId = (await db.users.check(req.body)).id; res.json({ ok: true }); });
  app.get('/api/posts/:id', requireSession, async (req, res) => res.json(await db.posts.get(req.params.id)));   // { id: uuid, body, status }
  app.post('/api/posts', requireSession, async (req, res) => res.status(201).json(await db.posts.create(req.session.userId, req.body.body))); // status: pending
  // moderation queue: moderators publish or reject pending posts
  app.get('/api/moderation', requireModerator, async (req, res) => res.json(await db.posts.pending()));
  app.post('/api/moderation/:id', requireModerator, async (req, res) => res.json(await db.posts.setStatus(req.params.id, req.body.decision)));
};
