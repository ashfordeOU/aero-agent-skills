---
name: q20-logbook-drd
description: "Maintain and assess the unit logbook of ECSS-Q-ST-20C Annex C against its document requirements description: validate each history, inspection, modification and environmental entry against the fields its type owes, check the numbering for a gap or a repeat, refuse a date that runs backwards down the sequence, trace the configuration through the modification chain so each one starts where the last left off, flag an environmental excursion or a failed inspection carrying no nonconformance reference, and accumulate the exposure hours recorded. Use when a logbook is opened, written up or reviewed at acceptance. Trigger: ecss, q-st-20c-annex-c, unit-logbook-drd, logbook-history-entries, logbook-inspection-entries, logbook-modification-chain, logbook-environmental-exposure."
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
  tags: [ecss, q-st-20c-quality-assurance-scope, q20-logbook-drd, unit-logbook-drd, logbook-history-entry-fields, logbook-inspection-entry-fields, logbook-modification-configuration-chain, logbook-environmental-exposure-record, logbook-entry-chronology-check]
  version: 0.1.0
  author: Aero Agent Skills
---

# ECSS Unit Logbook DRD (space-systems/ecss/q20-logbook-drd)

Use when the task is the Annex C document requirements description of
ECSS-Q-ST-20C: a logbook travels with a unit, and the question is whether
the record it carries can still reconstruct what happened to that unit
when it is opened years later.

## Domain quick reference

- The logbook carries four kinds of line and each owes different fields. A
  history entry needs the activity, where it happened and the work
  reference; an inspection needs its type, its result and its reference; a
  modification needs the change reference and the configuration either
  side of it; an environmental entry needs the parameter, the value, the
  unit and the duration. A line missing its own fields is not a short
  entry, it is an unusable one.
- The numbering is evidence. A gap means a page was removed or never
  written; a repeat means two hands wrote the same line. Both are found by
  reading the numbers, not the prose.
- Dates never run backwards down the sequence. Two entries on the same day
  are ordinary; an entry dated before the one above it means the book was
  written up from memory afterwards.
- The modification entries form a chain. Each starts from the state the
  previous one left, so the configuration can be walked from the initial
  build standard to whatever the unit stands at now. A modification whose
  before-state does not match the running state means an undocumented
  change happened in between; one whose after-state equals its
  before-state records nothing at all.
- An environmental value past its stated limit is not a defect on its own
  -- it becomes one when nothing ties it to a nonconformance. The same
  holds for a failed or conditional inspection.
- The exposure accumulates. Hours per parameter and in total are what a
  limited-life or a fatigue argument is later built from, so they are
  summed rather than left in the individual lines.

## Workflow

1. Validate each entry against the common fields and the fields its type
   owes, refusing an unknown type, a non-positive number or a date that is
   not an ISO day.
2. Check the numbering for a gap and for a repeat.
3. Walk the entries in sequence order and raise any date earlier than the
   one before it.
4. Trace the configuration from the stated initial build standard through
   every modification entry, raising a broken join and a modification that
   moves nothing.
5. Compare each environmental value with its stated limit, returning the
   excursion and its margin.
6. Require a nonconformance reference on every excursion and on every
   inspection that did not pass.
7. Accumulate the exposure per parameter and in total, then return the
   entry counts, the final configuration and the verdict.

## Pitfalls

- Reading the entries in submitted order. The sequence number is the
  order, and a book handed over out of order hides both the gaps and the
  backdating.
- Comparing an environmental value with a strict inequality against its
  own limit. A value sitting exactly on the limit is inside it, and the
  margin is reported rather than re-derived by the caller.
- Treating an excursion as the finding. The finding is an excursion nobody
  raised; an excursion with a nonconformance reference is a record working
  as intended.
- Trusting the final configuration on the last modification line. It is
  only trustworthy once the whole chain has been walked from the initial
  build standard.
- Leaving the exposure in the individual lines. The number anyone later
  asks for is the total, and summing it at the point of reading is how two
  reviewers get two answers.

## Behavior contract (gate 3)

The per-type field validation, the sequence and chronology checks, the
configuration chain trace, the environmental excursion and margin
computation, the nonconformance reference rules on excursions and failed
inspections, and the cumulative exposure per parameter and in total are
exercised by the gate 3 contract test: scripts/test_q20_logbook_drd.py
against scripts/q20_logbook_drd_logic.py (stdlib unittest, offline). Run:
python3 scripts/test_q20_logbook_drd.py

## Compliance

- ECSS standards are freely downloadable (ESA); cite the source and
  paraphrase per standards-map.yaml.
- compliance: STANDARDS-REF, gated: false.
