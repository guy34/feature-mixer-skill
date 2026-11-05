# Scenario O: one contacts client over two APIs

- **A (CRMish)**, `sources/crmish/api.md`: bearer-token auth, offset pagination (`?offset=&limit=`, at most 2 per
  page), errors as `{"error": "..."}`, API version v1.
- **B (Addressly)**, `sources/addressly/api.md`: API key in the `X-Api-Key` header, cursor pagination
  (`?cursor=`; `next_cursor` is null on the last page), errors as problem+json (`{"title", "status"}`),
  rate limited: 429 with a `Retry-After` header (seconds). API v2 renamed `full_name` to `name`. **B has no
  delete endpoint.**

Both are reached through the mock transport in `transport.py` (the same one the hidden tests use).

Build `unified/contacts.py`:

```python
client = create_client(transport, a_token, b_key, sleep)   # sleep(seconds): call it, never time.sleep
client.list_all() -> [{"source": "A" | "B", "id", "name"}]   # every page of both APIs
client.get("A" | "B", id) -> {"source", "id", "name"}       # raises NotFound (importable) for 404s
client.delete("A" | "B", id)                                 # raises NotSupported (importable) for B
```
Errors from either API raise `ApiError(source, status, message)` (importable). Retry a 429 after the time
`Retry-After` says, at most 3 times. Call only the endpoints the two specs list.
