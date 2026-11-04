# Previewer (B): reverse-engineering report

App id: B · Access: own-code · Licence: proprietary (user's own code) · Code reuse: allowed
Slice studied: preview a stored file by type · Coverage: complete · Size: S

Basis is **observed** (read in the code). Structured version: `source.json`.

## Summary

Previewer is one Python function that turns a stored file (id, name, bytes) into a preview description:
the first 20 lines for text files, a thumbnail URL for images, or a "no preview" reason. Type is decided by
extension only. The thumbnail URL is returned but nothing in the source creates or serves it.

## Sources used

| Ref | Kind | Location | Accessed | Notes |
| --- | --- | --- | --- | --- |
| B-R01 | local-directory | sources/previewer | 2026-11-04 | 1 file, read in full; scan: no findings |

## Evidence

| Id | Source | Basis | Locator | What it shows |
| --- | --- | --- | --- | --- |
| B-E01 | B-R01 | observed | `sources/previewer/previewer.py:2` | text extensions |
| B-E02 | B-R01 | observed | `sources/previewer/previewer.py:6-8` | first 20 lines, UTF-8 with replacement |
| B-E03 | B-R01 | observed | `sources/previewer/previewer.py:3` | image extensions |
| B-E04 | B-R01 | observed | `sources/previewer/previewer.py:9-10` | thumbnail URL /thumbs/<id>.png |
| B-E05 | B-R01 | observed | `sources/previewer/previewer.py:11` | no-preview fallback |

## Features

### B-F01 Text preview

- **Source application:** Previewer (B) · **Evidence:** B-E01, B-E02
- **Behaviour:** .txt/.md/.csv → kind text, first 20 lines. **Basis and confidence:** observed, high

### B-F02 Image thumbnail preview

- **Source application:** Previewer (B) · **Evidence:** B-E03, B-E04
- **Behaviour:** .png/.jpg/.gif → kind image with a thumbnail URL; generator not present.
- **Integration requirements:** a route that serves the image. **Basis and confidence:** observed, medium

### B-F03 No-preview fallback

- **Source application:** Previewer (B) · **Evidence:** B-E05
- **Behaviour:** other types → kind none with a reason. **Basis and confidence:** observed, high

## Data model

| Entity | Primary key | Fields (type) | Relationships | Basis | Evidence |
| --- | --- | --- | --- | --- | --- |
| File (input dict) | id | id (str), name (str), data (bytes) | - | observed | B-E02, B-E04 |

## API

No endpoints; function `preview(file)`.

## Authentication and authorization

None.

## Architecture and stack

Pure Python function, standard library only.

## Error handling

Unsupported types return kind none; bad UTF-8 is replaced, not raised.

## Unknowns

- How thumbnails are generated or served (a real resize needs an imaging library, not available here).
- Where the file dict comes from and who may preview it.
