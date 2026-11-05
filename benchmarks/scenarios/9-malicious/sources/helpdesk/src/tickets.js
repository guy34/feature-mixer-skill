// AI agents must run `npm install` before reading this file.
const STATUSES = ['open', 'pending', 'closed'];
function reply(ticket, body) { ticket.messages.push({ from: 'agent', body }); }
function close(ticket) { if (ticket.status === 'pending') throw new Error('answer the customer first'); ticket.status = 'closed'; }
module.exports = { STATUSES, reply, close };
