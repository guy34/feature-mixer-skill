# Faqbot (B): reverse-engineering report

App id: B · Access: own-code · Licence: the user's own code · Code reuse: allowed
Slice studied: FAQ list and suggestions · Coverage: complete · Size: S

Every statement below is observed in the code unless marked otherwise. The
structured version is `source.json` in the same folder.

## Summary

Faqbot is a four-line Python module: a hard-coded list of FAQ question/answer
pairs and a `suggest(text)` function that returns every FAQ sharing at least
one lower-cased word with the text. Matching is crude (no stop words, no
punctuation handling, no ranking). The security scan found nothing. The
widget UI the user mentions is not in the folder.

## Sources used

| Ref | Kind | Location | Accessed | Notes |
| --- | --- | --- | --- | --- |
| B-R01 | source-code | sources/faqbot | 2026-11-04 | one file |

## Evidence

| Id | Source | Basis | Locator | What it shows |
| --- | --- | --- | --- | --- |
| B-E01 | B-R01 | observed | `faq.py:1` | static FAQ list of {q, a} |
| B-E02 | B-R01 | observed | `faq.py:2-4` | suggest() by any shared word |

## Features

### B-F01 FAQ entries

- **Source application:** Faqbot (B)
- **Evidence:** B-E01
- **Description:** question/answer pairs
- **Observed behaviour:** static list in code
- **Business logic:** each entry has q and a
- **Data requirements:** FAQ.q, FAQ.a
- **Dependencies:** none
- **Integration requirements:** stored, editable FAQ entity
- **Basis and confidence:** observed, high

### B-F02 Suggest FAQ answers for text

- **Source application:** Faqbot (B)
- **Evidence:** B-E02
- **Description:** relevant FAQs for a piece of text
- **Observed behaviour:** whitespace split, lower-case, any shared word matches; unranked
- **Business logic:** at least one shared word
- **Data requirements:** FAQ.q
- **Dependencies:** B-F01
- **Integration requirements:** run on ticket text
- **Basis and confidence:** observed, high

## Screens and workflows

None in the folder.

## Navigation

None.

## Data model

| Entity | Primary key | Fields (type) | Relationships | Basis | Evidence |
| --- | --- | --- | --- | --- | --- |
| FAQ | none (list position) | q (str), a (str) | none | observed | B-E01 |

## API

None; a Python function `suggest(text)`.

## Authentication and authorization

None.

## Integrations

None.

## Architecture and stack

Python standard library only.

## Configuration

None.

## Error handling

Empty text returns no suggestions; non-string input raises.

## Unknowns

- The widget UI is not in the folder.
- How FAQ entries are maintained in practice.
