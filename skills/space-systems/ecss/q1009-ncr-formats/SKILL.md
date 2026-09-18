---
name: q1009-ncr-formats
description: "Validate a nonconformance report against the programme's format and content fields under ECSS-Q-ST-10-09C clause 5.5.1. Use when reports are being raised on inconsistent forms, when a status code or a disposition field has to be checked against the rest of the record, or when an audit needs the missing fields named: check every field against its kind, derive the conditional duties a departure disposition or a closed status creates, refuse a status code that moves backwards, and report completeness section by section. Trigger: ecss, q-st-10-09c, ncr-form-fields, ncr-status-codes, ncr-field-consistency, conditional-field-duty, ncr-completeness-audit, report-format-conformance."
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
  tags: [ecss, q-st-10-09c-nonconformance-scope, q1009-ncr-formats, ncr-form-fields, ncr-status-codes, ncr-field-consistency, conditional-field-duty, ncr-completeness-audit, report-format-conformance]
  version: 0.1.0
  author: Aero Agent Skills
---

# ECSS Nonconformance Control — Report Format and Content Fields (space-systems/ecss/q1009-ncr-formats)

Use when the task is the report-format step of ECSS-Q-ST-10-09C clause
5.5.1 — making every nonconformance report carry the same fields, in
the same sections, with the same status vocabulary, so a reader who was
not there can still work out what happened.

## Domain quick reference

- The report is read by people who were not in the room: a review board
  months later, an audit years later, an investigation after a failure.
  A consistent form is what makes that possible; a free-form note is
  not a lesser version of it, it is a different artefact.
- Seven sections carry the content: identification, item data,
  description, categorization, disposition, actions and status. A field
  belongs to exactly one of them, and a section that is empty when it
  is owed is a gap the report has to show rather than hide.
- Fields have kinds, and the kind is what makes a field usable later.
  An identifier the register can hold, an ISO calendar date, a whole
  count of items, an explicit yes or no, a list with at least one entry,
  a value from a fixed set — each of them refuses a different kind of
  mush.
- Some duties are conditional. A departure disposition owes its
  concession reference, a major report owes an action reference, a
  report in a dispositioned or closed state owes its disposition, and a
  closed report owes a closure date. These are the duties a free-form
  form loses, because nothing prompts for them.
- Consistency between fields is a separate check from the fields
  themselves. A closure date on an open report, a concession against a
  rework, a safety impact on a report graded minor, a closure that
  predates the raising — each field passes alone and the record still
  contradicts itself.
- Status codes are a controlled vocabulary with a direction. A report
  holds its state or moves on; it does not move back without a recorded
  reopening, and it is not cancelled after it has been closed.

## Workflow

1. Take the record and separate the fields the format knows from
   anything else it carries; fields outside the format are reported
   rather than silently accepted.
2. Derive the required set for this particular report: the base fields
   every report owes, plus the conditional duties its severity,
   disposition and status create.
3. Check each required field for presence, then check every filled
   field — required or not — against its kind, so an optional field
   that is filled with rubbish is still caught.
4. Run the cross-field checks that no single field can see, and report
   each contradiction in the terms the reader will recognise.
5. Where a status change is being applied, check it against the
   vocabulary's direction before writing it.
6. Roll completeness up per section as well as overall, so the
   originator is told which part of the form to return to rather than a
   bare percentage.
7. Report a conformance verdict with the missing fields, the invalid
   values, the unknown fields and the contradictions listed separately;
   they are fixed by different people.

## Pitfalls

- Treating the form as paperwork around the real content. The fields
  are the content: the disposition, the effectivity and the requirement
  departed from are what every later decision is taken against.
- Filling the disposition section while the report is still open. It
  reads as a board decision that has not happened, and the record can
  no longer show when the decision was actually taken.
- Naming serial numbers in free text. A list of items is what makes the
  effectivity searchable; a sentence describing which units were
  affected cannot be matched against a later build record.
- Letting a project invent its own status words. Local vocabulary makes
  a report unreadable to the customer's system and silently breaks any
  roll-up across projects.
- Grading a report minor while its safety field says yes. One of the
  two fields is wrong, and the form is the only place that
  contradiction will ever surface.
- Reporting completeness as a single percentage. A report that is 90
  percent complete with an empty disposition section is not nearly
  done; it is missing the part everything downstream depends on.

## Behavior contract (gate 3)

The field-kind checks, conditional duty derivation, status-code
direction, cross-field consistency and the per-section completeness
roll-up are exercised by the gate 3 contract test:
scripts/test_q1009_ncr_formats.py against
scripts/q1009_ncr_formats_logic.py (stdlib unittest, offline).
Run: python3 scripts/test_q1009_ncr_formats.py

## Compliance

- ECSS standards are freely downloadable (ESA); cite the source and
  paraphrase per standards-map.yaml.
- compliance: STANDARDS-REF, gated: false.
