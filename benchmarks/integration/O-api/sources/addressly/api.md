GET /v2/people?cursor=C             -> {"data": [{"id", "name"}], "next_cursor": C | null}
GET /v2/people/{id}                 -> {"id", "name"} | 404 problem+json {"title", "status"}
(v1 used "full_name"; v2 uses "name".) No delete.
Auth: X-Api-Key: <key>. 429 Too Many Requests with Retry-After: <seconds>.
