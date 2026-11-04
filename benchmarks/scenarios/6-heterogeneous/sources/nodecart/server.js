// NodeCart (illustrative): cart and Stripe checkout
const stripe = require('stripe')(process.env.STRIPE_SECRET);
module.exports = (app, prisma) => {
  app.post('/api/cart/items', async (req, res) => res.json(await prisma.cartItem.create({ data: { cartId: req.body.cartId, productId: req.body.productId, quantity: String(req.body.quantity) } }))); // {"productId": string, "quantity": string}
  app.post('/api/checkout', async (req, res) => res.json(await stripe.checkout.sessions.create({ mode: 'payment', line_items: req.body.items })));
};
