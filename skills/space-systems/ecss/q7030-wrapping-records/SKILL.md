---
name: q7030-wrapping-records
description: "Audit the traceability record set behind a wrapped assembly under ECSS-Q-ST-70-30C records rules. Use when a build package is closed or reviewed: tie every wrap to the operator who made it and the tool that made it, hold the tool calibration in date on the wrap date rather than the audit date, require the tool setup verification inside its own short window and never after the work, demand a pull-test reference for each operator, tool and gauge group, flag records running out of retention, and return coverage with an itemized list of what is missing. Trigger: ecss, q-st-70-30c, wire-wrap-record-traceability, wire-wrap-tool-calibration-date, wire-wrap-tool-setup-verification, wire-wrap-pull-test-reference, wire-wrap-record-retention, wire-wrap-build-package-closure."
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
  tags: [ecss, q-st-70-30c, q7030-wrapping-records, wire-wrap-record-traceability, wire-wrap-tool-calibration-date, wire-wrap-tool-setup-verification, wire-wrap-pull-test-reference, wire-wrap-record-retention, wire-wrap-build-package-closure]
  version: 0.1.0
  author: Aero Agent Skills
---

# ECSS Wire Wrapping — Wrapping Records (space-systems/ecss/q7030-wrapping-records)

Use when the task is the record set behind a wrapped assembly under
ECSS-Q-ST-70-30C -- establishing that every wrap on the hardware can be
traced to the hand, the machine and the test evidence that stand behind
it, before the build package is closed.

## Domain quick reference

- The record set exists for a containment action that has not happened
  yet. When one wrap fails in service the question is which other wraps
  share its operator, its tool and its gauge, and a package that cannot
  answer that question turns a bounded recall into an unbounded one.
- Traceability is per wrap, not per assembly. A package that names the
  operators who worked on the assembly, without saying which wrap each
  one made, has recorded a fact that no containment action can use.
- Calibration is graded against the wrap date, never the audit date. A
  tool whose calibration lapsed in June taints the wraps it made in
  July and leaves the wraps it made in May untouched, so a single
  in-date-today check either condemns sound work or clears bad work.
- The setup verification is a different clock from the calibration. The
  bit and sleeve are set at the start of a shift and drift with use, so
  the verification covers a day rather than a year -- and a
  verification dated after the wrap it covers is a record written
  backwards, which is a finding of its own.
- The pull test is evidence about a group, not about a wrap. Operator,
  tool and gauge together are what the destructive test demonstrates,
  so every such group present on the assembly owes at least one
  referenced test, and one reference covers every wrap in its group.
- Retention is part of the record, not an archiving detail. A record
  set that falls out of retention while the hardware is still flying is
  evidence that will not exist on the day it is needed.

## Workflow

1. Read the package: the assembly identity, the certified-operator
   list, one record per tool with its calibration and setup dates, and
   one record per wrap.
2. Grade each wrap for traceability: an operator who is on the
   certified list, a tool that the package describes, and an inspection
   reference.
3. Age the tool against that wrap: the calibration must not have
   expired before the wrap date, and the setup verification must sit on
   or before the wrap date and inside its own window.
4. Group the wraps by operator, tool and gauge, and list every group
   with no pull-test reference anywhere in it.
5. Age the records themselves against the retention period and list
   those past it.
6. Return the traceability coverage with the untraceable wraps, the
   uncovered groups and the expiring records named, so the package is
   closed on an itemized list rather than on a percentage.

## Pitfalls

- Checking tool calibration as at the audit. The tool is in date today
  and was not in date in July, or the other way round; only the wrap
  date answers the question the record set was kept to answer.
- Accepting a setup verification that post-dates the wrap. It reads as
  present in a checklist and it demonstrates nothing, because the
  verification was performed on a tool state that the wrap never saw.
- Demanding a pull test per wrap. The test is destructive, so a record
  scheme that asks for one per wrap either goes unmet or has people
  recording tests that never happened; the group is the right unit.
- Closing a package on a coverage percentage. Ninety-five per cent
  traceable means one in twenty wraps cannot be reached by a
  containment action, and the missing five per cent is exactly the part
  that will matter.
- Comparing a coverage ratio against one by bare arithmetic. It is a
  quotient of two counts, so a fully covered set can land a few units
  in the last place below one; the comparison absorbs that
  representation error without letting a genuinely short set read as
  complete.

## Behavior contract (gate 3)

The per-wrap traceability findings, the wrap-date calibration
comparison, the setup-verification window and its backwards-dated case,
the group pull-test coverage, the retention clock and the coverage
verdict are exercised by the gate 3 contract test:
scripts/test_q7030_wrapping_records.py against
scripts/q7030_wrapping_records_logic.py (stdlib unittest, offline).
Run:
python3 scripts/test_q7030_wrapping_records.py

## Compliance

- ECSS standards are freely downloadable (ESA); cite the source and
  paraphrase per standards-map.yaml.
- compliance: STANDARDS-REF, gated: false.
