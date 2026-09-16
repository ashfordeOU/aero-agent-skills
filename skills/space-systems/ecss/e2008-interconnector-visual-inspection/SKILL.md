---
name: e2008-interconnector-visual-inspection
description: "Use when acceptance testing has finished and the interconnector population needs grading. Compute and apply the interconnector defect allowances of ECSS-E-ST-20-08C clause 5.5.3.2.10 once an acceptance test programme concludes: take the pre-test baseline and the end-of-test condition of each interconnector, derive the intact legs, the broken and cracked leg fractions and the lifted weld fraction, disposition every item against its own allowance and against the intact-leg reserve, separate the defects the programme produced from the ones it inherited, report what is left of the coupon-wide affected and test-induced allowances, and hold the coupon open while any interconnector carries no end-of-test record. Trigger: ecss, e-st-20-08c, clause-5-5-3-2-10, interconnector-defect-allowance-at-acceptance, interconnector-broken-leg-limits, interconnector-test-induced-damage, interconnector-remaining-defect-budget."
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
  tags: [ecss, e-st-20-08-photovoltaic-assembly-scope, e2008-interconnector-visual-inspection, interconnector-defect-allowance-at-acceptance, interconnector-broken-leg-limits, interconnector-test-induced-damage, interconnector-remaining-defect-budget, coupon-interconnector-population-screen]
  version: 0.1.0
  author: Aero Agent Skills
---

# ECSS Photovoltaic — Interconnector Visual Inspection (space-systems/ecss/e2008-interconnector-visual-inspection)

Use when the task is the interconnector allowance of ECSS-E-ST-20-08C
clause 5.5.3.2.10 -- applying the defect allowances to the
interconnectors of a coupon at the point acceptance testing concludes,
and keeping the coupon open until each one has an end-of-test record.

## Domain quick reference

- The allowance is applied at the end of the programme, not during it.
  What matters is the condition each interconnector is in when testing
  stops, so an intermediate inspection is a data point and never the
  disposition.
- An interconnector is redundant on purpose. It carries current over
  several parallel legs, so the useful figure is how many legs are
  still intact, not how many are gone. A reserve of intact legs sits
  underneath every fraction allowance, and an item can satisfy the
  fraction and still fall through the reserve.
- A broken leg and a cracked leg are not the same defect. A broken one
  has already stopped carrying; a cracked one is on its way there
  under thermal cycling. The broken allowance is therefore never wider
  than the cracked one, and an allowance set written the other way
  round is contradictory rather than lenient.
- Welds are counted against the weld population, not the leg
  population. Folding them together grades a lifted weld against the
  wrong denominator.
- The baseline matters as much as the end state. A defect the
  programme inherited was dispositioned before testing started; one
  that appeared between the baseline and the end of test was produced
  by the programme, and that is evidence about the design or the
  process rather than about one joint.
- The two coupon allowances answer different questions. The affected
  fraction bounds how much of the population may carry anything at
  all; the test-induced fraction bounds how much of it the programme
  is allowed to have created. An item inside every one of its own
  allowances still consumes both.
- What is left of an allowance is worth reporting. A coupon two items
  from its limit and a coupon with room to spare both read as a pass
  unless the remaining budget is on the page.

## Workflow

1. Take the declared interconnector count and the end-of-test records.
   Refuse a record set larger than the declared count, and report the
   shortfall when it is smaller.
2. Read each item's pre-test baseline and post-test condition, refusing
   a count that exceeds the leg or weld population and a post-test
   count that has fallen below its own baseline.
3. Derive the intact legs and the broken, cracked and lifted-weld
   fractions, and take the difference from the baseline as the induced
   defects.
4. Disposition the item: an open interconnector or one below the intact
   leg reserve rejects; a fraction past its allowance refers, and past
   the review margin rejects.
5. Roll the coupon up: how many items carry anything, how many picked
   something up during testing, and how much of each coupon allowance
   is left.
6. Report the worst verdict, the items not accepted, the remaining
   allowances and the completeness flag. The coupon closes only when
   the record set is complete.

## Pitfalls

- Grading the end-of-test state without the baseline. The
  interconnector that arrived with a cracked leg and the one the
  vibration run cracked read identically in a post-test-only record,
  and only one of them is a programme finding.
- Reporting a fraction and stopping there. Two intact legs out of four
  and two out of eight are the same fraction and a different amount of
  redundancy left.
- Counting lifted welds against the leg count. The weld population is
  the denominator that makes the allowance mean anything.
- Writing an allowance set that permits more broken legs than cracked
  ones. It inverts the severity of the two defects and lets the worse
  one through.
- Accepting an item because no single allowance was breached while the
  coupon quietly runs out of budget. The remaining allowance is the
  number that shows it.
- Applying a coupon allowance to a short record set. The fraction is
  then taken over the wrong population and reads better than the
  coupon is.
- Comparing a counted number of legs, welds or items with a derived
  allowance by bare arithmetic. The allowance is a product of a
  declared fraction and a counted population, so a count sitting
  exactly on it can evaluate a few units in the last place above it;
  the comparison absorbs that representation error while the allowance
  stays untouched.

## Behavior contract (gate 3)

The baseline and end-of-test state reading, intact-leg and fraction
derivations, the item allowances and intact-leg reserve, the induced
defect separation, the coupon affected and test-induced allowances with
their remaining budgets and the completeness rollup are exercised by the
gate 3 contract test:
scripts/test_e2008_interconnector_visual_inspection.py against
scripts/e2008_interconnector_visual_inspection_logic.py (stdlib
unittest, offline). Run:
python3 scripts/test_e2008_interconnector_visual_inspection.py

## Compliance

- ECSS standards are freely downloadable (ESA); cite the source and
  paraphrase per standards-map.yaml.
- compliance: STANDARDS-REF, gated: false.
