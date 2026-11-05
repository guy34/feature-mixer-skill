# Faqbot (B): reverse-engineering report

App id: B · Access: own-code · Licence: the user's own code · Code reuse: allowed
Slice studied: FAQ answer suggestion · Coverage: complete · Size: S

Basis markers: **observed** (code), **documented**, **inferred**, **unknown**. Structured
version: `source.json`. Nothing was run.

## Summary

Faqbot is one 4-line Python module: a hard-coded FAQ list (one entry) and `suggest(text)`, which
returns every FAQ whose question shares any lower-cased word with the text. It has no ranking,
stop words or punctuation handling, so common words match almost everything. No UI or storage.

## Sources used

| Ref | Kind | Location | Accessed | Notes |
| --- | --- | --- | --- | --- |
| B-R01 | local-directory | `sources/faqbot` | 2026-11-04 | 1 file |

## Evidence

| Id | Source | Basis | Locator | What it shows |
| --- | --- | --- | --- | --- |
| B-E01 | B-R01 | observed | `faq.py:1` | static FAQ list, one {q, a} entry |
| B-E02 | B-R01 | observed | `faq.py:2-4` | any-shared-word matching, unranked |

## Features

### B-F01 FAQ answer suggestion

- **Source application:** Faqbot (B)
- **Evidence:** B-E02
- **Description:** suggest FAQ entries for free text
- **Observed behaviour:** word-set intersection; any overlap matches; FAQ list order
- **Business logic:** case-insensitive; punctuation kept; stop words match; no limit
- **Data requirements:** FAQ.q, FAQ.a
- **Dependencies:** B-F02
- **Integration requirements:** text to match (in the unified app: the ticket's subject and body)
- **Basis and confidence:** observed, high

### B-F02 FAQ content

- **Source application:** Faqbot (B)
- **Evidence:** B-E01
- **Description:** question and answer pairs
- **Observed behaviour:** hard-coded, one entry, no editing
- **Business logic:** none
- **Data requirements:** FAQ.q, FAQ.a
- **Dependencies:** none
- **Integration requirements:** a store for FAQ entries
- **Basis and confidence:** observed, high

## Data model

| Entity | Primary key | Fields (type) | Relationships | Basis | Evidence |
| --- | --- | --- | --- | --- | --- |
| FAQ | none (list position) | q (str), a (str) | none | observed | B-E01 |

## API

None: `suggest(text)` is a function.

## Authentication and authorization

None.

## Architecture and stack

Python, standard library only.

## Error handling

Empty text returns an empty list; non-string input is not handled.

## Unknowns

- The widget's UI (not in the folder)
- The real FAQ content and who maintains it
- Runtime behaviour: nothing was run
