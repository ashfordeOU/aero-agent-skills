---
name: q60-class-1-component-derating-rules
description: "Use when a Class 1 equipment has to show its derating analysis reaches every part it contains. Evaluate whether every Class 1 part in an equipment design carries its stress reduction margin under ECSS-Q-ST-60C clause 4.2.2.5: reconcile the equipment parts list against the lines the derating analysis actually reached, build each worst-case applied stress from its nominal value, tolerance spread and transient uplift, turn each maker rating into the largest applied value the category margin leaves, grade voltage, current, power and hot-spot temperature, then report the coverage gap, the tightest part and one equipment verdict. Trigger: ecss, q-st-60-eee-selection-scope, class-1-equipment-derating-coverage, worst-case-applied-stress-build-up, derating-analysis-coverage-gap, hot-spot-temperature-step-down, tightest-derating-margin-part, equipment-derating-verdict."
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
  tags: [ecss, q-st-60-eee-selection-scope, q60-class-1-component-derating-rules, class-1-equipment-derating-coverage, worst-case-applied-stress-build-up, derating-analysis-coverage-gap, hot-spot-temperature-step-down, tightest-derating-margin-part, equipment-derating-verdict, parts-list-analysis-reconciliation]
  version: 0.1.0
  author: Aero Agent Skills
---

# ECSS EEE Components — Class 1 Component Derating Rules (space-systems/ecss/q60-class-1-component-derating-rules)

Use when the task is the stress reduction of ECSS-Q-ST-60C clause
4.2.2.5 -- showing that every part used in a Class 1 equipment design
works inside a margin against its maker's rating, and that the analysis
saying so reached the whole parts list.

## Domain quick reference

- The clause reaches every part the equipment contains, not the parts
  someone thought to analyse. Coverage and stress are therefore two
  halves of one answer, and the coverage half is asked first.
- A part left out of the derating analysis is not a passing part, it is
  an unknown one. An equipment whose analysed parts all sit inside
  their margins while three list lines were never reached has not
  demonstrated the clause, and calling it compliant hides exactly the
  lines most likely to have been skipped.
- Coverage is measured twice: by line, and weighted by quantity. A
  single missed line carrying a large population is a bigger hole than
  its share of the line count suggests.
- Worst-case applied stress is built, not quoted. Each stress starts
  from its nominal value, opens out by the tolerance spread the design
  carries, and is raised again by any transient uplift the part sees in
  service. A check run on the nominal alone grades a condition the part
  never meets at its worst.
- The margin is applied to the maker's rating, turning it into the
  largest applied value the category leaves. Electrical stresses are
  kept as fractions of the rating; hot-spot temperature is kept as an
  absolute ceiling, a step down from the rated maximum.
- Each part category carries its own margins, because the mechanism the
  reduction protects against differs from one to the next. One blanket
  factor across a board is not a derating rule, it is an average of
  unrelated mechanisms.
- The useful output is the coverage gap, the utilisation of every
  graded stress, and the single tightest part -- that is where a
  thermal excursion, a tolerance change or a rating change lands first.

## Workflow

1. Declare the equipment parts list with a reference and quantity per
   line, and the analysed parts with their category, stresses and
   hot-spot prediction. Reject an uncategorized part rather than
   defaulting it; the margins are chosen by category.
2. Reconcile the two. Report the lines the analysis never reached, by
   line count and by quantity, and reject an analysis that grades a
   part absent from the list at all.
3. Build each worst-case applied stress from its nominal value, its
   tolerance spread and its transient uplift.
4. Turn each maker rating into the largest applied value the category
   margin leaves, so the answer a designer needs is a number rather
   than a verdict, and step the rated maximum hot-spot down to the
   derated ceiling.
5. Grade every stress and the hot-spot. Report a stress sitting exactly
   on its allowable as on-margin and compliant, not as a breach.
6. Name the tightest part by utilisation across the equipment, and
   close with one verdict: demonstrated, incomplete where coverage or a
   thermal prediction is missing, or breached.

## Pitfalls

- Reporting an equipment as compliant because every analysed part
  passed. The clause is about every part used, so the reconciliation
  against the parts list is the check, and the per-part grading only
  finishes it.
- Counting coverage by lines alone. A missed line carrying a large
  population leaves far more parts ungraded than the line count shows,
  so the quantity-weighted figure is reported beside it.
- Grading the nominal stress. The margin exists for the worst case, so
  the tolerance spread and any transient uplift are built in before the
  comparison rather than argued about after it.
- Grading the hot-spot against the maker's rated maximum. The rated
  maximum is where the part is destroyed; the derated ceiling is where
  the project agrees to stop, and the whole step down is the margin.
- Passing a part on its electrical stresses alone. Every ratio can sit
  low while the part runs hot, so an absent hot-spot prediction leaves
  the equipment incomplete rather than demonstrated.
- Applying one blanket factor to every part. The categories fail by
  different mechanisms, so a capacitor and an integrated circuit do not
  share a voltage rule, and averaging them overstresses whichever is
  tighter.
- Comparing a built stress with its allowable by bare arithmetic. The
  stress is a chain of products and the allowable is a single product,
  so a stress built to sit exactly on its allowable can land a few
  units in the last place above it; the comparison absorbs that
  representation error while the allowable stays untouched.

## Behavior contract (gate 3)

The rule-set validation, margin lookup, worst-case stress build-up,
allowable applied value, hot-spot ceiling, per-stress grading, per-part
rollup, parts list reconciliation, tightest-part selection and equipment
verdict are exercised by the gate 3 contract test:
scripts/test_q60_class_1_component_derating_rules.py against
scripts/q60_class_1_component_derating_rules_logic.py (stdlib unittest,
offline). Run:
python3 scripts/test_q60_class_1_component_derating_rules.py

## Compliance

- ECSS standards are freely downloadable (ESA); cite the source and
  paraphrase per standards-map.yaml.
- compliance: STANDARDS-REF, gated: false.
