// Jotter API (illustrative)
const { v4: uuid } = require('uuid');
const notes = new Map(); // id (uuid) -> { id, title, content, labels: [], pinned, updatedAt }

module.exports = (app) => {
  app.get('/api/notes', (req, res) => res.json([...notes.values()].sort((a, b) => b.pinned - a.pinned)));
  app.post('/api/notes', (req, res) => { const n = { id: uuid(), title: req.body.title, content: req.body.content, labels: [], pinned: false, updatedAt: new Date() }; notes.set(n.id, n); res.status(201).json(n); });
  app.put('/api/notes/:id', (req, res) => { const n = Object.assign(notes.get(req.params.id), req.body); res.json(n); });
  app.delete('/api/notes/:id', (req, res) => { notes.delete(req.params.id); res.status(204).end(); });
  // labels work like tags
  app.post('/api/notes/:id/labels', (req, res) => { notes.get(req.params.id).labels.push(req.body.label); res.json(notes.get(req.params.id)); });
  // search only matches titles
  app.get('/api/search', (req, res) => res.json([...notes.values()].filter(n => n.title.includes(req.query.q))));
  // pin a note to the top of the list
  app.post('/api/notes/:id/pin', (req, res) => { notes.get(req.params.id).pinned = true; res.json(notes.get(req.params.id)); });
  // export all notes as Markdown files in a zip
  app.get('/api/export', (req, res) => res.json([...notes.values()].map(n => ({ file: `${n.title}.md`, text: n.content }))));
};
