---
name: q6012-design-documentation-review-item
description: "Audit the design documentation review item of ECSS-Q-ST-60-12C clause 7.3.13 for a microwave die: fold every document identifier onto one canonical spelling, reject a document stated twice at one issue or issued under two types, take the controlling issue of each, confront the record with the document types the programme requires, expose the controlling issues still in draft and the earlier issues still circulating as released, walk every derivation chain to its root to find a dangling reference, a loop or an orphan, then close, action or reject the item. Use when a microwave die design review reaches the assembled design record rather than the design itself. Trigger: ecss, q-st-60-12-microwave-die-scope, design-documentation-record-review, design-record-completeness-check, design-record-issue-currency, design-document-traceability-chain, dangling-design-document-reference, orphan-design-document."
license: Apache-2.0
compliance: STANDARDS-REF
standards:
  - id: ecss
    reference-only: true
gated: false
domain: space-systems
pack: space-systems
compatibility: "agentskills.io SKILL.md; any SKILL.md host (Claude Code, Hermes, OpenClaw)"
metadata:
  domain: space-systems
  subdomain: ecss
  tags: [ecss, q-st-60-12-microwave-die-scope, q6012-design-documentation-review-item, design-documentation-record-review, design-record-completeness-check, design-record-issue-currency, design-document-traceability-chain, dangling-design-document-reference, orphan-design-document]
  version: 0.1.0
  author: Aero Agent Skills
---

# ECSS Microwave Die — Design Documentation Review Item (space-systems/ecss/q6012-design-documentation-review-item)

Use when the task is the design documentation review item of
ECSS-Q-ST-60-12C clause 7.3.13 -- reviewing whether the assembled
design record is complete, current and traceable, rather than reviewing
the die the record describes.

## Domain quick reference

- The record is the deliverable that outlives the design team. Another
  organisation has to build, screen and accept the part from it years
  later, so the item grades three properties of the set: complete,
  current and traceable. A sound die with a broken record fails.
- Completeness is counted against the document types the programme
  requires of a die, not against the documents that happen to exist. A
  required type with nothing behind it is a hole that the quality of
  the other documents cannot fill.
- The record is a set of issues, not a set of documents. Only the
  highest issue of each identifier controls, and every question about
  currency is asked of that issue: is it released, does it predate the
  baseline freeze, and is an earlier issue still circulating as
  released behind it.
- A controlling issue still in draft means the record has nothing
  released behind that document at all. That is a different and worse
  finding than an issue that is released but old, and the two are kept
  apart because one blocks and one is worked off.
- Records are assembled from drawing offices, process owners and test
  groups, so one document arrives spelled several ways. Matching on the
  identifier as typed turns one document into two, hides the duplicate
  issue and breaks a trace that would otherwise resolve.
- Traceability is a walk, not a field. Following each document up
  through the thing it derives from either reaches a root, hits a
  reference the record does not contain, or returns to where it
  started. A document with nothing above it that is not the root of the
  record hangs outside the structure entirely.

## Workflow

1. Fold every document identifier and every parent reference onto one
   canonical spelling before anything is matched, so duplicates and
   traces are found on the document rather than on the typing.
2. Reject the record outright where one document is stated twice at the
   same issue, derives from itself, or appears under two document
   types. Each means the record contradicts itself.
3. Take the highest issue of each identifier as the controlling one and
   set the earlier issues aside; they are only revisited to see whether
   any is still marked released.
4. Confront the controlling set with the required document types.
   Report the absent types and the coverage share over the required
   set, not over the documents present.
5. Grade currency on the controlling issues: a non-released controlling
   issue blocks, an issue predating the baseline freeze and a lingering
   released earlier issue are carried as actions.
6. Walk every derivation chain to its root. Separate a dangling
   reference and a loop, which break the structure, from an orphan,
   which is attached by an action, then close, action or reject.

## Pitfalls

- Counting completeness over the documents that exist. A record of
  twelve well-written documents can still be missing a required type
  entirely, and nothing inside the documents present reveals it.
- Reviewing every issue as though each were current. The superseded
  issues are history; grading them raises findings against documents
  nobody will use and buries the one finding that matters, which is a
  controlling issue still in draft.
- Treating a lingering released earlier issue as a filing detail. Two
  issues of one document both marked released means two versions are
  both usable, and the organisation reading the record downstream has
  no way to tell which one governs.
- Reading a trace as a field on the document. A parent identifier that
  is present and well formed still breaks the chain when the record
  does not contain it, and only walking the chain to a root finds a
  loop where two documents derive from each other.
- Comparing an issue date against the baseline freeze by bare
  arithmetic. Programme days arrive as floating-point quantities, so a
  document issued exactly on the freeze can land a few units in the
  last place on the wrong side of it; the comparison absorbs that
  representation error while the freeze day stays untouched.

## Behavior contract (gate 3)

The identifier canonicalization, duplicate and two-type rejection,
controlling issue selection, required type coverage, release and
staleness grading, derivation chain walk and closure verdict are
exercised by the gate 3 contract test:
scripts/test_q6012_design_documentation_review_item.py against
scripts/q6012_design_documentation_review_item_logic.py (stdlib
unittest, offline). Run:
python3 scripts/test_q6012_design_documentation_review_item.py

## Compliance

- ECSS standards are freely downloadable (ESA); cite the source and
  paraphrase per standards-map.yaml.
- compliance: STANDARDS-REF, gated: false.
