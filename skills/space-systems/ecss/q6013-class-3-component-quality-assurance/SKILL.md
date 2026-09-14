---
name: q6013-class-3-component-quality-assurance
description: "Assess the quality assurance arrangement a programme owes for commercial EEE parts at the lowest assurance class under ECSS-Q-ST-60-13C clause 6.5: dispose every catalogue duty as retained, relieved or unassigned, refuse relief against a duty the class still makes mandatory, admit a discretionary relief only against a recorded rationale and an approval taken at the level the duty weight and the item criticality earn, carry a weighted evidenced coverage beside a plain one, read the quality plan against its revalidation interval, and price a quality function reporting inside a function it grades. Use when a thin class 3 assurance arrangement must become one verdict before parts are bought. Trigger: ecss, q-st-60-13c-clause-6-5, class-three-commercial-eee-quality-assurance, mandatory-duty-relief-refusal, weighted-evidenced-duty-coverage, relief-approval-authority-level, quality-plan-revalidation-interval."
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
  tags: [ecss, q-st-60-13-commercial-eee-component-scope, q6013-class-3-component-quality-assurance, class-three-commercial-eee-quality-assurance, mandatory-duty-relief-refusal, weighted-evidenced-duty-coverage, relief-approval-authority-level, quality-plan-revalidation-interval]
  version: 0.1.0
  author: Aero Agent Skills
---

# ECSS Commercial EEE Components -- Class 3 Component Quality Assurance (space-systems/ecss/q6013-class-3-component-quality-assurance)

Use when the task is the clause 6.5 framing question of ECSS-Q-ST-60-13C at
the lowest assurance class: a programme has decided to buy commercial parts
with the thinnest arrangement the standard recognises, and the question is
which quality assurance duties survive that decision, who holds each of
them, and what the ones that were stood down were traded for.

## Domain quick reference

- The lowest class is the one where the arrangement is smallest, which is
  exactly why it has to be written down. A programme that performs six
  duties out of ten and a programme that relieved four of them reach the
  same headline figure and are not the same programme.
- Relief is bought, not declared. A discretionary duty can be stood down,
  and the price is a recorded rationale plus an approval taken at the level
  the duty earns. A duty dropped without that record is not a relieved
  duty; it is an unassigned one wearing the same word.
- A small core does not move at any price, even here. Procurement document
  review, nonconformance processing, alert watch and records retention are
  what makes the arrangement an arrangement, so a relief against one of
  them is refused before its rationale is read.
- The price of relief rises with what the duty carries and with what the
  item is. A heavy duty earns a customer-level approval; a light one can be
  settled inside the project. An item at or below the criticality floor
  moves that level up one notch, because the item cannot absorb the duty
  being stood down.
- Three coverage figures are carried, not one. The plain figure credits an
  admissible relief; the evidenced figure credits only a duty with a real
  record; the weighted evidenced figure lets a heavy duty outweigh a light
  one, so relieving two minor duties does not read like relieving incoming
  verification.
- The first missing element is the one reported. A duty with no owner is
  not also graded on the procedure it does not have, because three findings
  against one empty box send three actions to the same place.
- A duty declared but never exercised leaves no evidence reference, which
  is why the evidence field stays separate from the procedure field. One
  says the programme knows how; the other says it did.
- Independence here is structural, not personal. A quality function
  reporting inside design, production, procurement, integration or test
  grades its own line management's output, and the lowest class tolerates
  that only where a refusal has an escalation route to travel along.

## Workflow

1. Validate the policy first: three coverage floors inside the unit
   interval with the evidenced floor no higher than the plain floor, a
   positive plan revalidation interval and a boolean escalation
   requirement. An unknown policy key is refused rather than ignored.
2. Validate every declared duty record: a duty name drawn from the
   catalogue, no duty declared twice, a boolean relief flag and reference
   fields that are strings where present. A blank reference counts as
   absent, not as present.
3. Dispose every duty in the catalogue, including the duties the programme
   never mentioned, so the report length always matches the catalogue
   length and a silent omission cannot read as coverage.
4. Test each relief before crediting it. A mandatory duty refuses it
   outright; a discretionary duty needs both a recorded rationale and an
   approval at or above the level its weight and the item criticality earn,
   and a refused relief leaves the duty unassigned.
5. Take the plain, evidenced and weighted evidenced coverages over the
   whole catalogue and compare each with its floor under a named tolerance,
   so a figure landing exactly on a floor is not read as short.
6. Read the quality plan: its presence first, then its age in whole months
   against the revalidation interval, with an age equal to the interval
   still inside it.
7. Read the reporting line against the functions the quality role grades
   and require a declared escalation route where it is embedded and the
   policy asks for one.
8. Close on the first blocking condition in order -- no plan, a mandatory
   duty relieved, a mandatory duty unassigned, coverage short, no
   escalation route, plan revalidation overdue -- or on the class 3
   arrangement being met, and report all three coverages and every gap
   beside the verdict.

## Pitfalls

- Reading the lowest class as permission to skip the arrangement rather
  than to shrink it. The duties that remain are fewer, and each of them is
  still owed an owner, a procedure and a record.
- Quoting the plain coverage alone. It is the one figure a programme
  running on relief can reach in full, and the gap between it and the
  evidenced figure is the whole point of carrying both.
- Approving a relief at the wrong level because the duty looked minor. The
  level is set by the duty weight and the item criticality together, and a
  critical item raises it whatever the duty costs to perform.
- Relieving incoming verification because the parts are catalogue parts.
  The commercial origin is the reason the duty exists, so the argument for
  dropping it is the argument for keeping it.
- Accepting a procedure reference as evidence. The procedure says the
  programme knows how to do the duty; only the record says it did.
- Letting an undeclared duty vanish from the report. A catalogue duty
  nobody mentioned is the most likely gap in the arrangement, so it is
  reported unassigned rather than dropped from the denominator.
- Treating an embedded quality function as acceptable because the people
  are experienced. The test is structural: with no escalation route a
  refusal cannot survive its own reporting line, whatever the staffing.

## Behavior contract (gate 3)

The policy validation, duty record validation, catalogue-wide disposition,
relief admissibility against the required approval authority, the plain,
evidenced and weighted coverages against their floors, the quality plan
presence and revalidation reading, the independence and escalation route
reading and the closing verdict are exercised by the gate 3 contract test:
scripts/test_q6013_class_3_component_quality_assurance.py against
scripts/q6013_class_3_component_quality_assurance_logic.py (stdlib unittest,
offline). Run:
python3 scripts/test_q6013_class_3_component_quality_assurance.py

## Compliance

- ECSS standards are freely downloadable (ESA); cite the source and
  paraphrase per standards-map.yaml.
- compliance: STANDARDS-REF, gated: false.
