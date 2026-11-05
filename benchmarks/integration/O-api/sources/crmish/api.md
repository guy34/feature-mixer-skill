GET /v1/contacts?offset=N&limit=N   -> {"items": [{"id", "name"}], "total": N}
GET /v1/contacts/{id}               -> {"id", "name"} | 404 {"error": "not found"}
DELETE /v1/contacts/{id}            -> 204
Auth: Authorization: Bearer <token>. Errors: {"error": message}.
