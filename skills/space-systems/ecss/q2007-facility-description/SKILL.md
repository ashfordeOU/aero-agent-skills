---
name: q2007-facility-description
description: "Maintain the facility description a space test centre owes under ECSS-Q-ST-20-07 clause 5.2.2, and say whether the register in place can be booked against. Use when a test centre's facility register is being audited or a customer request has to be placed on a facility: refuse a register never opened, name the entries declaring no capability, no environmental envelope parameter or no reference document, take the centre's declared capabilities against what the entries actually carry, flag the descriptions past their review age, and screen a requested test envelope against one facility, separating a demand that exceeds a bound from a demand on a parameter never declared. Trigger: ecss, q-st-20-07-clause-5-2-2, test-facility-register-completeness, test-facility-environmental-envelope, test-facility-capability-coverage, test-facility-reference-documents."
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
  tags: [ecss, q-st-20-07-test-centre-quality-and-safety-scope, q2007-facility-description, q-st-20-07-clause-5-2-2, test-facility-register-completeness, test-facility-environmental-envelope, test-facility-capability-coverage, test-facility-reference-documents, test-facility-envelope-demand-screening]
  version: 0.1.0
  author: Aero Agent Skills
---

# ECSS Test-Centre Quality and Safety — Facility Description (space-systems/ecss/q2007-facility-description)

Use when the task is clause 5.2.2 of ECSS-Q-ST-20-07: the test centre
keeps a description of each facility it operates — what the facility can
do, the environmental envelope it can hold, and the documents that
govern it — and the question is whether that description is complete
enough to sell against and to test a booking with.

## Domain quick reference

- The description is what a customer is sold against, so completeness is
  taken entry by entry and the incomplete entries are named. An average
  across a register hides the one facility that cannot support a
  booking, which is the only entry anybody needed to know about.
- An envelope is a pair of bounds, not a number. A bound pair that is
  inverted, or a parameter declared with only one side, cannot be tested
  against and is refused at validation rather than half-applied later.
- The interesting demand is the one landing exactly on a bound. A demand
  equal to a limit is inside the envelope, and the margin at that point
  is zero, so the inside call is made with a tolerance and the margin is
  compared to zero the same way — otherwise the same booking is accepted
  on one host and refused on another.
- A demand on a parameter the facility never declared is not a pass and
  not an exceedance. It ranks above an exceedance because the two need
  different corrective actions: one extends the description, the other
  refuses the booking or moves it.
- Capability coverage is taken against the capabilities the centre
  declares it sells, not against the union of what the entries happen to
  carry. A register graded against its own contents always covers
  everything in it.
- A description past its review age is a management flag on a register
  that is otherwise complete, so it is carried as an advisory rather
  than allowed to mask a missing envelope parameter.

## Workflow

1. Validate the register policy first: the envelope parameters every
   entry owes, the reference-document floor, the description review
   interval and the capability coverage required. An unrecognised policy
   key is refused rather than ignored.
2. Validate the register: non-empty identifiers, no facility registered
   twice, no capability listed twice inside one entry, every envelope
   parameter a well-ordered finite bound pair, and no description dated
   after the assessment day.
3. Name the entries that declare no capability at all.
4. Name, per entry, the required envelope parameters the entry does not
   declare.
5. Name the entries holding fewer reference documents than the floor.
6. Take capability coverage against the centre's declared capabilities
   and name the uncovered ones, comparing against the required fraction
   with a tolerance rather than a bare inequality.
7. Carry the descriptions past their review age as advisories.
8. When a booking is supplied, resolve the facility, screen every
   demanded parameter against its bounds, report the signed margin to
   the nearer bound, and let an undeclared parameter outrank an
   exceedance in the booking verdict.
9. Close on one verdict in order: register absent, facility entry
   incomplete, envelope parameter missing, reference documents missing,
   capability coverage short, or facility description maintained.

## Pitfalls

- Averaging completeness across the register. One entry with no
  envelope is the finding; a register-level percentage reports it as
  nearly fine.
- Treating a demand on a bound as an exceedance. It is inside, and a
  bare strict comparison makes that call differently depending on how
  the bound was computed, which turns a booking into a coin toss.
- Folding an undeclared parameter into the exceedance count. The
  facility may well be able to hold it; what is missing is the
  description, and merging the two sends the corrective action to the
  wrong owner.
- Grading capability coverage against the entries themselves. That
  number is one by construction and never finds the service the centre
  sells with no facility behind it.
- Letting a stale description mask a structural gap. Age is advisory;
  a missing envelope parameter is not, and reporting only the newest
  finding loses the one that stops a booking.

## Behavior contract (gate 3)

The policy validation, entry and envelope validation, the capability,
envelope and reference-document gaps, the capability coverage, the
review-age advisories, the bound arithmetic at and past a limit, the
demand screening and the ordered verdict are exercised by the gate 3
contract test: scripts/test_q2007_facility_description.py against
scripts/q2007_facility_description_logic.py (stdlib unittest, offline).
Run: python3 scripts/test_q2007_facility_description.py

## Compliance

- ECSS standards are freely downloadable (ESA); cite the source and
  paraphrase per standards-map.yaml.
- compliance: STANDARDS-REF, gated: false.
