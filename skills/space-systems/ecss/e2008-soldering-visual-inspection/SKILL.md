---
name: e2008-soldering-visual-inspection
description: "Assess the solder joints at a solar-array string termination against the workmanship standard agreed with the customer under ECSS-E-ST-20-08C clause 5.5.3.2.13: refuse to disposition anything until the agreement is named, issued, customer-approved and already in force on the inspection date, then take each joint's wetting angle, fillet coverage fraction and void area fraction against the figures that agreement carries, refuse a cracked, disturbed, cold or dewetted joint on the attribute alone, spend the rework-cycle budget before another heat cycle is promised, and return a string verdict naming the standard it was graded against. Use when string terminations have been examined and the solder record needs a defensible disposition. Trigger: ecss, e-st-20-08c, clause-5-5-3-2-13, string-termination-solder-joint-inspection, customer-agreed-workmanship-standard, solder-fillet-coverage-assessment, solder-wetting-angle-screen, solder-joint-void-fraction-limit."
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
  tags: [ecss, e-st-20-08-photovoltaic-assembly-scope, e2008-soldering-visual-inspection, string-termination-solder-joint-inspection, customer-agreed-workmanship-standard, solder-fillet-coverage-assessment, solder-wetting-angle-screen, solder-joint-void-fraction-limit, solder-rework-cycle-budget]
  version: 0.1.0
  author: Aero Agent Skills
---

# ECSS Photovoltaic — Soldering Visual Inspection (space-systems/ecss/e2008-soldering-visual-inspection)

Use when the task is the soldering examination of ECSS-E-ST-20-08C
clause 5.5.3.2.13 -- the joints where a string terminates, judged
against a workmanship standard that the supplier and the customer
agreed, and turned into a record that names the standard it used.

## Domain quick reference

- The clause does not carry the acceptance figures. It points at an
  agreed workmanship standard, and that changes what the first step of
  the inspection is: the agreement is an input to be checked, not a
  background assumption. An inspector grading a joint against
  remembered numbers has produced an opinion, and the record cannot be
  defended in a review.
- Four things make an agreement usable and every one of them is
  refused rather than defaulted: a reference, an issue, explicit
  customer approval, and an effective date that is not after the day
  the joints were looked at. An issue that took effect afterwards
  means the joints were graded against something not yet in force.
- Three geometric measurements decide a joint and the worst of them
  governs. The wetting angle says whether the solder wetted the base
  metal or stood off it. The fillet coverage fraction says how much of
  the termination is actually joined. The void area fraction says how
  much of the footprint is gas rather than metal.
- Those three fail in different physics, which is why none of them can
  stand in for the others: a joint can wet beautifully over a third of
  its length, and a fully covered joint can be half voided underneath.
- Four attributes carry no acceptance figure at all. A cracked joint, a
  joint disturbed while the solder froze, a cold joint that never
  reached wetting temperature and solder that dewetted off the base
  metal are refused on the attribute, and a good set of geometry
  numbers does not reach them.
- Rework is finite. Each rework is another heat cycle into the same
  termination and the same cell interconnect behind it, so the agreed
  standard carries a cycle budget; a joint at its limit is refused
  rather than sent back for a further cycle nobody has left to spend.
- An empty survey is not a clean string. A string with no joints
  recorded against its terminations has not been inspected, and the
  record says so rather than returning a pass.

## Workflow

1. Take the agreement first: reference, issue, customer approval and
   effective date against the inspection date. Refuse the record here
   if any of them is missing; nothing downstream is meaningful without
   a standard to grade against.
2. Open the record against a string identifier so each joint has a
   traceable place in the rework record.
3. Categorize each joint by the termination it sits on, and reject an
   unrecognized termination type rather than defaulting it.
4. Screen the not-tolerated attributes before reading anything into
   the geometry, and reject an unrecognized attribute rather than
   passing it through as unremarkable.
5. Measure each joint three ways -- wetting angle, fillet coverage
   fraction, void area fraction -- and take the worst call of the
   three.
6. Apply the rework-cycle budget: a joint already at its limit
   converts a rework call into a reject.
7. Close with the string verdict, the joints refused on attribute
   listed apart from those refused on measurement, the re-inspection
   duty a rework creates, and the standard reference and issue the
   grading used.

## Pitfalls

- Grading joints with no agreed standard in hand. The clause's whole
  mechanism is the agreement; without it the figures used are
  undocumented and the record cannot be reproduced by a reviewer.
- Using an issue of the standard that took effect after the
  inspection. The joints were accepted against criteria that were not
  in force, and the finding surfaces at delivery review rather than at
  the bench.
- Accepting a fully covered joint on coverage alone. Coverage is
  measured on the outside and voids are inside; the two measurements
  exist because one does not predict the other.
- Reading a large wetting angle as cosmetic. A high angle is solder
  standing off the base metal, which is the same condition as a cold
  joint one step before it becomes one.
- Sending a joint back for its third or fourth rework. Each cycle puts
  heat into the interconnect behind the termination, and the budget in
  the agreed standard is what stops a joint being cooked to a pass.
- Returning a pass for a string with no joints recorded. An empty
  survey looks identical to a clean one on a summary line and means
  the opposite.
- Comparing a measurement with a limit by bare arithmetic. A coverage
  fraction is a quotient of two measured lengths, so a joint exactly
  on the limit can evaluate a few units in the last place below it;
  the comparison absorbs that representation error while the limit
  stays untouched.

## Behavior contract (gate 3)

The agreement validation, the wetting-angle, fillet-coverage and
void-fraction grading, the attribute refusals, the rework-cycle budget
and the string rollup are exercised by the gate 3 contract test:
scripts/test_e2008_soldering_visual_inspection.py against
scripts/e2008_soldering_visual_inspection_logic.py (stdlib unittest,
offline). Run:
python3 scripts/test_e2008_soldering_visual_inspection.py

## Compliance

- ECSS standards are freely downloadable (ESA); cite the source and
  paraphrase per standards-map.yaml.
- compliance: STANDARDS-REF, gated: false.
