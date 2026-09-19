---
name: q7040-brazing-audits
description: "Scope an audit of a brazing supplier or facility and settle what its findings do to the approval. Use when a shop that makes brazed joints has to be assessed, because the joints themselves cannot be re-opened and the facility is the evidence: cover every area for a shop nobody has seen, rotate a surveillance scope while holding furnace survey and records permanently in it, pull back any area that carried a major finding last time, shorten the next interval from what this visit found, and suspend, condition or maintain the approval on the findings still open. Trigger: ecss, q-st-70-40-brazing, brazing-supplier-audit, brazing-facility-surveillance-scope, braze-furnace-survey-audit-area, braze-audit-finding-severity, brazing-approval-suspension."
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
  tags: [ecss, q-st-70-40-brazing, q7040-brazing-audits, brazing-supplier-audit, brazing-facility-surveillance-scope, braze-audit-finding-severity, brazing-approval-suspension]
  version: 0.1.0
  author: Aero Agent Skills
---

# ECSS Brazing — Supplier and Facility Audits (space-systems/ecss/q7040-brazing-audits)

Use when the task is the audit clause of ECSS-Q-ST-70-40: setting the
scope of a brazing audit, deciding when the next one falls due, and
saying what the findings do to the facility's approval.

## Domain quick reference

- A brazing approval is an approval of a facility, not of a delivery.
  The joint cannot be re-opened afterwards, so confidence in it comes
  from having watched the shop that made it.
- The eight areas cover the whole chain: procedure qualification,
  operator qualification and continuity, furnace calibration and survey,
  filler and flux control, pre-braze cleaning and fit-up, inspection and
  destructive sampling, nonconformance and repair, and records.
- A facility nobody has audited is audited across every area, because
  nothing about it is known and a rotating scope assumes a baseline that
  does not exist.
- A surveillance audit of an approved facility rotates, but two areas
  never rotate out. Furnace calibration and survey drifts silently
  between visits and nothing else catches it. Records is where every
  other area is evidenced, so a rotation that skips it audits nothing.
- An area that carried a major or critical finding last time is
  mandatory again this time. Rotating away from an open problem is how
  a finding becomes a habit.
- The interval is set by the category and then shortened by what was
  found. A critical finding brings the next visit forward to a short
  follow-up; a major one halves the interval; minor findings alone leave
  it where it was.
- The approval turns on findings that are still open, not on findings
  that were raised. A closed critical finding is a facility that fixed
  something; an open one is a facility that has not.
- A finding raised in an area that was not in the scope is not a bonus
  observation. It means the scope record and the audit disagree, and
  one of the two is wrong.

## Workflow

1. Take the facility category. A shop nobody has audited gets the full
   area set and the rotation question does not arise.
2. For a surveillance audit, start the scope from the two permanent
   areas, add the rotation for this cycle, then add back every area
   that carried a major or critical finding last time.
3. Run the audit and record each finding with an identifier, a
   severity, the area it sits in and whether it is closed. Refuse a
   duplicate identifier rather than letting two findings merge.
4. Set the next interval from the category and the worst severity
   found, and turn it into a date so the follow-up is scheduled rather
   than intended.
5. Set the approval from the findings still open: suspended on an open
   critical, conditional on an open major, maintained otherwise.
6. Report a finding raised outside the recorded scope, and a permanent
   area that was rotated out, as notes on the audit itself.

## Pitfalls

- Auditing a new supplier on a surveillance scope because the visit is
  short. The rotation assumes a baseline; a first audit is what creates
  one.
- Rotating furnace survey out of a scope because last year's was clean.
  Survey drift is the failure that shows no symptom until the joints
  from the cold corner of the load come back.
- Grading the approval on findings raised. A shop that raises and
  closes findings is working; a shop with none raised may simply not be
  looking.
- Taking a closing-meeting commitment as closure. Closure is a state of
  the finding with evidence behind it, not an intention recorded in
  minutes.
- Leaving the next audit as an interval rather than a date. An interval
  slips quietly; a date on a calendar is visible when it passes.
- Accepting a finding from outside the scope without noticing. It means
  the audit and its own scope record disagree, and the next audit will
  be planned from whichever one is wrong.

## Behavior contract (gate 3)

The full-coverage rule for a new facility, the permanent and rotating
scope areas, the previous-finding pull-back, the severity-driven
interval and its date arithmetic, the open-finding approval states and
the scope-disagreement notes are exercised by the gate 3 contract test:
scripts/test_q7040_brazing_audits.py against
scripts/q7040_brazing_audits_logic.py (stdlib unittest, offline).
Run:
python3 scripts/test_q7040_brazing_audits.py

## Compliance

- ECSS standards are freely downloadable (ESA); cite the source and
  paraphrase per standards-map.yaml.
- compliance: STANDARDS-REF, gated: false.
