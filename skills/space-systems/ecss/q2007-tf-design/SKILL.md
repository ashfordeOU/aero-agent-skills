---
name: q2007-tf-design
description: "Design and clear a new or modified test facility for use under ECSS-Q-ST-20-07C clause 5.6.1. Use when a facility development has to prove it is finished rather than merely delivered: take the ordered review set from the change category, capture each requirement with a criticality, verification method, status and reference, refuse a safety-critical requirement closed by design review alone or waived at all, name a review closed before an earlier one, report verification coverage as a fraction, and hold the facility out of use while anything blocks. Trigger: ecss, q-st-20-07-test-centre, q2007-tf-design, test-facility-development-review-set, facility-requirement-verification-coverage, facility-modification-change-category, verification-before-facility-use, facility-acceptance-review-sequence."
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
  tags: [ecss, q-st-20-07-test-centre, q2007-tf-design, test-facility-development-review-set, facility-requirement-verification-coverage, facility-modification-change-category, verification-before-facility-use, facility-acceptance-review-sequence]
  version: 0.1.0
  author: Aero Agent Skills
---

# ECSS Test Centre — Test Facility Design and Development (space-systems/ecss/q2007-tf-design)

Use when the task is the facility-development step of ECSS-Q-ST-20-07C
clause 5.6.1 -- capturing what a new or modified test facility has to do,
designing it against that, and demonstrating it before the first flight
article is put into it.

## Domain quick reference

- The change category is the first decision and it fixes everything else.
  A wholly new facility, a major modification (one that touches the load
  path, the control system or the safety envelope) and a minor
  modification owe different review sets, and nothing about the project's
  cost, urgency or size moves the category.
- The review set is ordered, not merely a set. Every category starts at a
  requirements review and ends at a facility acceptance review, and the
  reviews in between close in sequence. A later review recorded as closed
  while an earlier one is open means the sequence was not run, and the
  pair is reported so the out-of-order closure can be traced.
- A requirement carries four facts, and the fourth is the one that gets
  dropped: criticality, verification method, status, and the reference
  that supports the status. A requirement marked verified with no evidence
  reference is an assertion, and an assertion is what an audit finds.
- A safety-critical requirement is not closed by a review of the design
  alone. The design can be correct and the built article still wrong;
  somebody has to inspect or exercise the thing that exists.
- A safety-critical requirement cannot be waived at all. A waiver moves
  residual risk onto whoever operates the facility, and that is not the
  waiver board's risk to give away.
- An open requirement is not a defect. It is work in hand, and it is
  correctly reported as blocking the readiness decision rather than as a
  finding against the requirement. Mixing the two makes an honest project
  plan look like a quality failure and encourages premature closure.
- Verification coverage is reported as a fraction because a project at
  0.95 is visibly not a project at 1.0. A waived requirement is not
  verified and does not count toward coverage, however legitimate the
  waiver.
- Readiness for use is one decision with three independent blockers:
  reviews not closed in order, requirements still open, requirements
  carrying findings. Reporting which blocker applies is what lets the
  facility owner see what actually stands between them and first use.

## Workflow

1. Categorize the development as new, major modification or minor
   modification, and read the ordered review set off the category.
2. Capture the requirement register. Give each requirement an identifier,
   a criticality, the method it will be verified by, its status, and the
   evidence or waiver reference behind that status.
3. Refuse the register when a criticality, method or status is
   unrecognised, when a reference is blank rather than absent, or when an
   identifier repeats.
4. Grade each requirement on the schedule-independent rules: safety
   closed by design review alone, verified with no evidence, waived with
   no reference, safety waived at all.
5. Grade the gate record. Flag each required review that is not closed,
   and for each one, name every later review that was closed ahead of it.
6. Compute verification coverage over the whole register.
7. Decide readiness. The facility is clear for use only when the gate
   findings, the open list and the findings list are all empty; otherwise
   report which of the three blocks it.

## Pitfalls

- Letting the category follow the budget. A modification that touches the
  safety envelope is a major modification whether or not it was funded as
  one.
- Checking the review set as a set and never as a sequence, so an
  acceptance review signed before the design review reads as complete.
- Marking a requirement verified with the evidence "to follow". The
  reference is the verification; without it there is a status and nothing
  underneath it.
- Closing a safety-critical requirement on a review of the design. The
  design being right is not the built facility being right.
- Waiving a safety-critical requirement with a properly minuted waiver.
  The minute is real and the waiver is still not available.
- Counting a waived requirement in the verification coverage, which
  quietly returns the project to 1.0 on the day the waiver is signed.
- Reporting "not ready" without the blocker. The owner cannot act on a
  verdict that does not say which of the three things to fix.

## Behavior contract (gate 3)

The change-category review sets, requirement validation, safety and
evidence rules, waiver rules, gate sequencing with out-of-order detection,
verification coverage and the three-blocker readiness decision are
exercised by the gate 3 contract test: scripts/test_q2007_tf_design.py
against scripts/q2007_tf_design_logic.py (stdlib unittest, offline).
Run: python3 scripts/test_q2007_tf_design.py

## Compliance

- ECSS standards are freely downloadable (ESA); cite the source and
  paraphrase per standards-map.yaml.
- compliance: STANDARDS-REF, gated: false.
