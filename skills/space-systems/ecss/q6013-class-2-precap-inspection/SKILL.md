---
name: q6013-class-2-precap-inspection
description: "Use when a pre-seal record has to become a seal-release verdict. Assess whether the pre-seal inspection of a cavity-package commercial EEE lot meets the intermediate assurance class under ECSS-Q-ST-60-13C clause 5.3.4: answer not-applicable rather than waived where the family has no cavity, void an inspection dated on or after the seal instead of booking it as late, measure the notice the customer had against the agreed lead time, admit the delegation this class allows only where it names an approved procedure and its issue, accept critical internal defects on zero, and hold the lot in front of the seal naming every failing grade. Trigger: ecss, q-st-60-13c-clause-5-3-4, class-two-pre-seal-inspection, cavity-package-precap-applicability, seal-day-inspection-void, precap-notice-lead-time, precap-delegation-approval-reference, critical-internal-defect-accept-on-zero."
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
  tags: [ecss, q-st-60-13-commercial-eee-component-scope, q6013-class-2-precap-inspection, class-two-pre-seal-inspection, cavity-package-precap-applicability, seal-day-inspection-void, precap-notice-lead-time, precap-delegation-approval-reference, critical-internal-defect-accept-on-zero]
  version: 0.1.0
  author: Aero Agent Skills
---

# ECSS Commercial EEE Components -- Class 2 Pre-Cap Inspection (space-systems/ecss/q6013-class-2-precap-inspection)

Use when the task is the clause 5.3.4 pre-seal inspection question of
ECSS-Q-ST-60-13C at the intermediate assurance class: a lot of a
commercial part is waiting at the manufacturer with its lids off, and the
question is whether the customer's inspection of the open devices lets
the seal operation proceed.

## Domain quick reference

- The inspection only exists for a package with a cavity. A solid
  encapsulated device is never opened and never sealed, so there the
  answer is that the requirement does not apply -- a different
  disposition from a requirement that applied and was waived, and worth
  keeping apart in the record because a waiver needs an approval and a
  non-applicability needs only the package family.
- It happens in front of the seal, and the seal day is already too late.
  Once the lid is on, an internal defect is invisible and unrecoverable:
  no later electrical test sees a loose bond wire that is still touching
  or a particle that has not yet moved. An inspection dated on or after
  the seal is void, not late, and cannot be repaired by paperwork.
- The customer has to be able to get there, so the notice is a real
  requirement and not a courtesy. Notice given inside the agreed lead
  time is a finding even where somebody did attend, because the next lot
  is the one nobody reaches.
- This class allows the inspection to be delegated to the manufacturer's
  own quality organisation or to a third party, which the class above
  does not. The delegation is good only where it names an approved
  procedure and that procedure's issue; a pointer with no issue points
  at whatever the document says today, which is not an approval.
- The defects are graded and the grades are not interchangeable. A
  critical internal finding -- the bond, the die attach, the loose
  material that will move under launch vibration -- accepts on zero,
  and that zero cannot be traded upward against a generous minor count.

## Workflow

1. Resolve the package family first and return not-applicable where it
   has no cavity, before reading any inspection evidence at all.
2. Parse the notice, inspection and seal days, refusing a malformed or
   impossible date rather than guessing at its intent.
3. Void the inspection where it is dated on or after the seal, and say
   so as a void record rather than as a late one.
4. Difference the notice day against the seal day and compare the result
   with the agreed lead, treating notice exactly on the lead as good.
5. Read who carried the inspection out; where it was delegated, admit it
   only against an approved procedure reference carrying an issue.
6. Grade the sample against the lot, hold critical findings to zero, and
   compare majors and minors with their accept numbers.
7. Release for seal only when the timing, notice, delegation and every
   defect grade hold; otherwise hold the lot in front of the seal and
   report every failing check, not the first one found.

## Pitfalls

- Recording a post-seal inspection as a late one. The evidence it would
  have produced no longer exists, so the record is void and the lot has
  no pre-seal inspection at all.
- Treating a package with no cavity as a waived requirement. A waiver
  needs an approval behind it; a non-applicability needs only the family,
  and conflating them invents an approval nobody granted.
- Accepting a delegation on a verbal agreement. This class allows the
  delegation, which is exactly why the approved procedure and its issue
  are the thing that makes it real.
- Trading a critical finding against the major and minor counts. The
  critical accept number is zero because the failure mode is loss of the
  unit in flight, and no clean minor count offsets it.
- Reporting only the first failing check. A lot held for short notice
  may also be held for its defects, and fixing one sends it back.

## Behavior contract (gate 3)

The applicability answer, day parsing, seal-day void boundary, notice
lead-time comparison, delegation approval check, graded defect gate and
the release-or-hold disposition are exercised by the gate 3 contract
test: scripts/test_q6013_class_2_precap_inspection.py against
scripts/q6013_class_2_precap_inspection_logic.py (stdlib unittest,
offline). Run:
python3 scripts/test_q6013_class_2_precap_inspection.py

## Compliance

- ECSS standards are freely downloadable (ESA); cite the source and
  paraphrase per standards-map.yaml.
- compliance: STANDARDS-REF, gated: false.
