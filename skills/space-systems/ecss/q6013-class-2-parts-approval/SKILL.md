---
name: q6013-class-2-parts-approval
description: "Determine which approval route a commercial EEE part needs at the intermediate assurance class under ECSS-Q-ST-60-13C clause 5.2.4 and grade the justification standing behind it: raise the route every declared escalation driver demands, refuse a record with no reference, issue or permitted approver, credit an element carried by an identified referenced document below one, treat a heading with no rationale as untreated, take the covered share and the weighted completeness against their floors, and close on route below the required level, approval lapsed, or approval recorded after the first procurement commitment. Use when a part-approval file has to become a verdict. Trigger: ecss, q-st-60-13c-clause-5-2-4, class-two-parts-approval-route, parts-approval-escalation-driver, parts-approval-justification-record, parts-approval-validity-lapse, approval-before-procurement-commitment."
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
  tags: [ecss, q-st-60-13-commercial-eee-component-scope, q6013-class-2-parts-approval, q-st-60-13c-clause-5-2-4, class-two-parts-approval-route, parts-approval-escalation-driver, parts-approval-justification-record, parts-approval-validity-lapse, approval-before-procurement-commitment]
  version: 0.1.0
  author: Aero Agent Skills
---

# ECSS Commercial EEE Components -- Class 2 Parts Approval (space-systems/ecss/q6013-class-2-parts-approval)

Use when the task is the clause 5.2.4 approval question of ECSS-Q-ST-60-13C at
the intermediate assurance class: a commercial electrical, electronic and
electromechanical part is proposed for a build, and the question is which
authority has to approve it and whether the justification recorded behind that
approval is the one the class asks for.

## Domain quick reference

- Approval at this class is a route, not a signature. The route ladder runs
  from the delegated project component engineer, through the parts control
  board, to a board decision the customer has agreed. A part with nothing
  unusual about it sits at the bottom of that ladder, and every declared
  escalation driver raises the floor.
- The drivers are properties of the buy, not opinions about it: no approved
  equivalent already on the project, supply from outside the franchised
  network, use beyond the published temperature range, no published radiation
  data, a single-point-failure function, obsolescence at the order date. The
  required route is the highest any one driver demands, so adding a second
  board-level driver changes nothing while adding one customer-level driver
  changes everything.
- Approving above the required route is not a defect. It costs review time and
  is recorded as an observation; approving below it is the finding, because
  the authority that carries the residual risk never saw the part.
- The justification is what the approval is later defended with. It has to
  state the need, the alternatives examined, the residual risk, the
  compensating measures applied, and the scope the approval is valid over.
  Each of those is required; the record is judged on whether it treats them.
- This class allows an element to be carried by a referenced document rather
  than restated, but only where the pointer names a document and an issue, and
  the credited weight stays below one. Without that credit a file assembled
  entirely out of pointers scores the same as one that argues its own case.
- An element named with no rationale behind it is untreated for this purpose.
  That is the common way an approval file reads complete and decides nothing:
  the headings match the required list while every section is a title.
- The weighted completeness runs over the full required element list, so
  deleting a weak element can only lower the figure, which is the way round it
  has to be. A figure landing exactly on its floor is admissible, the
  comparison tolerance being there to absorb representation error rather than
  to widen the floor.
- An approval carries a validity period. An approval older than its validity
  has lapsed: the supply, the lot and the obsolescence position have all moved
  since the decision, and the file no longer describes the part being bought.
- Position decides whether the approval controlled anything. An approval
  recorded after the first procurement commitment documents a choice already
  made, and no amount of justification recovers the lots bought against no
  decision.

## Workflow

1. Validate the grading policy: the covered share floor, the weighted
   completeness floor, the credit a referenced element earns and the marginal
   band. A completeness floor above the covered floor, a credit of nothing or
   of one, or a band wider than the floor is refused rather than used.
2. Validate the approval record: a non-blank reference and issue, an approver
   drawn from the permitted authorities, a recognised declared route, the
   approval and first-commitment positions, the validity period and the age.
   An absent record closes the assessment on approval not established.
3. Build the required route from the declared escalation drivers, rejecting an
   unrecognised or repeated driver, and name the drivers that raised it.
4. Compare the declared route with the required one. Below it is a finding
   naming both; above it is an advisory.
5. Dispose every required justification element as written, carried by an
   identified referenced document, stated without a rationale, or absent, and
   report the absent and heading-only lists in full rather than truncating at
   the first entry.
6. Take the covered share and the weighted completeness over the full required
   list and compare both with their floors under a named tolerance.
7. Check the age against the validity, and the approval position against the
   first procurement commitment.
8. Close on one verdict: approval not established, approval route below the
   required level, approval lapsed, approval recorded after the procurement
   commitment, justification record short of the required content, or part
   approved for class 2 use.

## Pitfalls

- Grading the approval on who signed it. A senior signature on the wrong route
  still leaves the authority that carries the residual risk unaware of the
  part; the route is the check, the signature is the evidence of it.
- Counting drivers instead of ranking them. Three board-level drivers still
  demand the board route, while one customer-level driver on its own demands
  the customer-agreed route, so the ladder is a maximum and never a tally.
- Accepting a pointer that names a document but no issue. The justification
  then changes whenever the other document is reissued, and the approval made
  last quarter cannot be shown to have been made against anything.
- Crediting a referenced element in full. Reference is permitted here and it
  is a thinner treatment than arguing the case, which is what the credit
  records.
- Averaging depth only over the elements that exist. Deleting a weak element
  would then raise the score, which is exactly backwards, so the denominator
  stays the full required element list.
- Reading a met floor as a closed file. The floor is an aggregate; a single
  absent residual-risk statement can sit under a comfortable figure and still
  be the reason the approval cannot be defended.
- Letting an approval outlive its validity because the part number has not
  changed. The lot, the source and the obsolescence position move underneath a
  stable part number, which is what the validity period exists to catch.
- Recording the approval after the first order is placed. The decision then
  describes a purchase already made, and the parts bought against no decision
  stay in the build.

## Behavior contract (gate 3)

The policy validation, approval-record validation, route ladder and driver
escalation, citation validation, the written, referenced, heading-only and
absent dispositions, the covered share, the weighted completeness, the
validity state, the commitment-position check, the marginal advisories and the
approval verdict are exercised by the gate 3 contract test:
scripts/test_q6013_class_2_parts_approval.py against
scripts/q6013_class_2_parts_approval_logic.py (stdlib unittest, offline). Run:
python3 scripts/test_q6013_class_2_parts_approval.py

## Compliance

- ECSS standards are freely downloadable (ESA); cite the source and
  paraphrase per standards-map.yaml.
- compliance: STANDARDS-REF, gated: false.
