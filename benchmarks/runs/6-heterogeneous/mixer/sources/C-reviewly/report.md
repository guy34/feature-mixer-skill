# Reviewly (C): reverse-engineering report

App id: C · Access: closed · Licence: proprietary · Code reuse: not-allowed
Slice studied: product reviews (core loop) · Coverage: partial · Size: S

Basis marks: **observed**, **documented** (official docs or a published spec), **inferred**, **unknown**.
The structured version of this report is `source.json` in the same folder.

## Summary

Reviewly is a closed product that adds product reviews to a shop. From its
public overview and OpenAPI spec (the only inputs given): customers leave a
1-5 star rating and a comment, shops can reply, and reviews appear only
after a purchase is confirmed. The spec lists two v2 endpoints (list and
post reviews) with no schemas, auth or errors. Nothing was observed running;
everything is documented or inferred, and it must be rebuilt, never copied.

## Sources used

| Ref | Kind | Location | Accessed | Notes |
| --- | --- | --- | --- | --- |
| C-R01 | documentation | sources/reviewly-docs/overview.md | 2026-11-04 | 3 lines; scanned first (no findings) |
| C-R02 | api-spec | sources/reviewly-docs/openapi.yaml | 2026-11-04 | OpenAPI 3.0.3, 1 path, 2 methods, no schemas |

## Evidence

| Id | Source | Basis | Locator | What it shows |
| --- | --- | --- | --- | --- |
| C-E01 | C-R01 | documented | `overview.md:2` | 1-5 star rating and a comment |
| C-E02 | C-R01 | documented | `overview.md:2` | shops can reply |
| C-E03 | C-R01 | documented | `overview.md:3` | reviews appear after a purchase is confirmed |
| C-E04 | C-R02 | documented | `openapi.yaml#/paths/.../get` | GET /v2/products/{productId}/reviews |
| C-E05 | C-R02 | documented | `openapi.yaml#/paths/.../post` | POST /v2/products/{productId}/reviews, rating 1-5 and comment |
| C-E06 | C-R02 | unknown | `openapi.yaml` | no schemas, auth, errors or reply endpoint |

## Features

### C-F01 List product reviews

- **Source application:** Reviewly (C)
- **Evidence:** C-E04
- **Description:** show reviews for a product
- **Observed behaviour:** not observed (documented only)
- **Business logic:** only purchase-confirmed reviews appear (C-F04)
- **Basis and confidence:** documented, medium

### C-F02 Leave a product review

- **Source application:** Reviewly (C)
- **Evidence:** C-E01, C-E05
- **Description:** rate 1-5 stars and comment
- **Business logic:** rating 1..5
- **Integration requirements:** signed-in customer; product catalog
- **Basis and confidence:** documented, medium

### C-F03 Shop replies to reviews

- **Source application:** Reviewly (C)
- **Evidence:** C-E02, C-E06
- **Description:** shop answers a review
- **Business logic:** unknown; no endpoint documented
- **Dependencies:** C-F02
- **Integration requirements:** a shop/admin role
- **Basis and confidence:** documented, low

### C-F04 Verified-purchase reviews

- **Source application:** Reviewly (C)
- **Evidence:** C-E03
- **Description:** a review shows only after the reviewer's purchase is confirmed
- **Business logic:** visibility depends on a confirmed purchase (refuse vs hide not documented)
- **Dependencies:** C-F02
- **Integration requirements:** an order record with confirmed payment in the unified app
- **Basis and confidence:** documented, medium

## Screens and workflows

None documented.

## Navigation

Not documented.

## Data model

| Entity | Primary key | Fields (type) | Relationships | Basis | Evidence |
| --- | --- | --- | --- | --- | --- |
| Review | unknown | product_id (unknown), rating (integer 1-5), comment (text) | product | inferred | C-E01, C-E05 |

## API

| Method | Path | Auth | Request | Response | Errors | Evidence |
| --- | --- | --- | --- | --- | --- | --- |
| GET | `/v2/products/{productId}/reviews` | unknown | - | not documented | not documented | C-E04 |
| POST | `/v2/products/{productId}/reviews` | unknown | rating, comment (shape not documented) | not documented | not documented | C-E05 |

## Authentication and authorization

Not documented (no security scheme in the spec).

## Integrations

None documented.

## Architecture and stack

Unknown: closed product, nothing documented.

## Configuration

Not documented.

## Error handling

Not documented.

## Unknowns

- Request/response schemas, field names and types.
- Authentication scheme.
- Error responses.
- Shop reply endpoint and data shape.
- Meaning of "purchase confirmed" and whether unpurchased reviews are refused or hidden.
- Moderation, editing, deleting.
- Stack and architecture.
