# Tallyho public API (v2)
GET /v2/expenses?budget_id=..  -> [{id, merchant, amount, currency, date, category}]
POST /v2/expenses              -> create an expense
GET /v2/budgets                -> budgets the token's user belongs to
Auth: personal access token in the Authorization header. Rate limit: 60 requests per minute.
