---
name: q60-class-2-part-material-restrictions
description: "Evaluate a candidate Class 2 part's case style and material content against the ECSS-Q-ST-60C clause 5.2.2.2 limits: decide whether the package is hermetic, and for a non-hermetic one grade its moisture sensitivity level against the build ceiling and its demonstrated damp life against the humid hours the mission asks for with margin; grade every surface finish against the lead mass fraction that keeps a tin coating off the whisker route; grade each declared metal against the trace it is allowed at; then roll the worst axis into one verdict and list the mitigations the part carries before purchase. Use when a Class 2 build has to show a chosen part's package and finish are allowed. Trigger: ecss, q-st-60c-class-2-selection-scope, class-2-non-hermetic-packaging-limit, class-2-pure-tin-whisker-restriction, class-2-restricted-material-trace-limit, class-2-moisture-sensitivity-ceiling, non-hermetic-damp-life-cover, class-2-finish-mitigation-route."
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
  tags: [ecss, q-st-60c-class-2-selection-scope, q60-class-2-part-material-restrictions, class-2-non-hermetic-packaging-limit, class-2-pure-tin-whisker-restriction, class-2-restricted-material-trace-limit, class-2-moisture-sensitivity-ceiling, non-hermetic-damp-life-cover, class-2-finish-mitigation-route]
  version: 0.1.0
  author: Aero Agent Skills
---

# ECSS EEE Components — Class 2 Part and Material Restrictions (space-systems/ecss/q60-class-2-part-material-restrictions)

Use when the task is the limit set of ECSS-Q-ST-60C clause 5.2.2.2 --
deciding whether a candidate Class 2 part's case style and material
content are allowed at all, and what the part has to carry before it
can be bought.

## Domain quick reference

- Two unrelated limits sit on the same choice. One is about the case:
  how long the die is kept away from moisture. The other is about what
  the part is made of: what leaves the part and attacks whatever is
  standing next to it. A part can be clean on one and barred on the
  other, so they are graded separately and rolled up at the end.
- The Class 2 assurance level does not remove either limit; it changes
  what closes them. A non-hermetic case is an available route rather
  than an exception, but the route is only open against two numbers: a
  moisture sensitivity level inside the ceiling the build works to, and
  a demonstrated damp life covering the humid hours the mission asks
  for with margin on top.
- A non-hermetic part with neither number is not a failing part, it is
  an unproven one. Reporting it as refused loses the distinction that
  matters to a buyer, because the first is closed by a test report and
  the second is not closed at all.
- A tin coating leaves the whisker route once enough lead is alloyed
  into it. Below that fraction the finish stays restricted, and on
  Class 2 it may be carried on a mitigation that physically removes the
  growth route rather than one that merely records the finish in a
  list.
- Cadmium and zinc are barred outright. No mitigation buys them back,
  so a mitigation declared against them is a sign the grading was run
  on the wrong axis.
- A restricted metal is graded against the trace it is allowed at, not
  against its presence. Every real plating carries impurities, so a
  presence test refuses parts that are in fact inside the limit.
- The useful output is the per-axis verdict, the worst axis, the list
  of mitigations the part now carries, and the damp life headroom in
  hours -- that last number is what a mission extension eats first.

## Workflow

1. Declare the part with its package style, the humid hours its mission
   asks for, every surface finish with its material, and every metal
   the maker declares with a mass fraction. Reject an undeclared
   package style rather than defaulting it.
2. Grade the case. A hermetic case closes here. A non-hermetic one is
   graded on its moisture sensitivity level against the build ceiling
   and its demonstrated damp life against the mission hours raised by
   the project margin.
3. Grade each finish. Bar cadmium and zinc outright; take a tin-bearing
   finish at or above the lead mass fraction threshold as accepted;
   carry one below it only on a mitigation from the agreed set, and
   refuse a mitigation that only records the finish.
4. Grade each declared metal against its trace allowance, leaving a
   metal the policy does not restrict untouched.
5. Roll the axes up by worst verdict, so a refusal outranks an open
   evidence gap and an open gap outranks a mitigation.
6. Report the verdict, the refused axes, the open evidence, the
   mitigations the part now carries, and the damp life headroom.

## Pitfalls

- Treating a non-hermetic package as an exception to argue about. On
  Class 2 it is a route with an entry price, and the price is two
  numbers rather than a paragraph of justification.
- Refusing a non-hermetic part that simply has not been characterised
  yet. Missing evidence and failed evidence lead to different actions,
  so they are reported as different verdicts.
- Testing a restricted metal for presence. The clause allows a trace,
  so a presence test refuses compliant platings and tells the buyer
  nothing about the ones that are actually over.
- Accepting any declared mitigation against a near-pure-tin finish. A
  mitigation that removes the growth route and a mitigation that writes
  the finish into a list are not the same thing, and only the first is
  taken.
- Letting a mitigation buy back cadmium or zinc. Those are barred by
  the material, not by the risk, so the mitigation field is ignored on
  that axis.
- Rolling the axes up by counting. One barred finish decides the part
  no matter how many clean axes sit beside it, so the rollup is a worst
  case and never an average.
- Comparing a demonstrated damp life with its requirement by bare
  arithmetic. The requirement is a product of hours and a margin, so a
  life built to sit exactly on it can land a few units in the last
  place below; the comparison absorbs that representation error while
  the requirement stays untouched.

## Behavior contract (gate 3)

The policy validation, damp life requirement, packaging grading, finish
grading, restricted metal trace grading, worst-axis rollup and
mitigation list are exercised by the gate 3 contract test:
scripts/test_q60_class_2_part_material_restrictions.py against
scripts/q60_class_2_part_material_restrictions_logic.py (stdlib
unittest, offline). Run:
python3 scripts/test_q60_class_2_part_material_restrictions.py

## Compliance

- ECSS standards are freely downloadable (ESA); cite the source and
  paraphrase per standards-map.yaml.
- compliance: STANDARDS-REF, gated: false.
