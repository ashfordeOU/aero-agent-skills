---
name: e31-temperature-ranges-allowable-limits-classification
description: "Allocate every item of flight hardware to the cryogenic, conventional or high-temperature range under ECSS-E-ST-31 clauses 3.2, 4.2.1 and 4.2.4, then capture its allowable temperature limits and the uncertainty attached to each prediction, and turn the pair into the margin the thermal control subsystem is actually designed to. Use when a hardware list must be grouped by range before design rules are picked, when an item straddles two ranges and needs both rule sets, or when a predicted temperature has to be inflated by its uncertainty before it is compared with an allowable limit. Trigger: ecss, e-st-31, tcs-temperature-range-grouping, tcs-allowable-temperature-limits, tcs-prediction-uncertainty, tcs-design-margin, tcs-cryogenic-range-boundary, spacecraft-thermal-control."
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
  tags: [ecss, e-st-31-thermal-control-scope, e31-temperature-ranges-allowable-limits-classification, tcs-temperature-range-grouping, tcs-allowable-temperature-limits, tcs-prediction-uncertainty, tcs-design-margin, tcs-cryogenic-range-boundary]
  version: 0.1.0
  author: Aero Agent Skills
---

# ECSS Thermal Control — Temperature Ranges and Allowable Limits (space-systems/ecss/e31-temperature-ranges-allowable-limits-classification)

Use when the task is the clause 3.2 / 4.2.1 / 4.2.4 step of ECSS-E-ST-31:
putting each item of hardware into the temperature range whose design rules
apply to it, recording the allowable limits it must stay inside, and turning
the predicted temperatures plus their uncertainties into the margin the
subsystem is designed to.

## Domain quick reference

- Three ranges carry three different rule sets. Below roughly two hundred
  kelvin the cryogenic rules apply; above roughly four hundred and seventy
  the high-temperature and thermal-protection rules apply; between them sit
  the conventional rules most hardware is designed under. The boundaries are
  not cosmetic — they select which analysis and which material data are
  admissible.
- An item is placed by the range its predicted temperatures occupy, not by
  the range its nominal operating point sits in. A radiator that nominally
  runs at two hundred and eighty kelvin but reaches one hundred and eighty
  in a cold survival case belongs to two ranges and owes both rule sets.
- Allowable limits come in tiers and they are not interchangeable. The
  operational limit bounds the range in which the item must work; the
  survival limit bounds the range in which it must merely still be alive
  afterwards. Comparing a predicted operating temperature with a survival
  limit manufactures margin that does not exist.
- The prediction is not the number to compare. The uncertainty of the model
  is added to the hot prediction and subtracted from the cold one before
  either is compared with a limit; the margin is what remains after that.
  A margin quoted on the raw prediction is the uncertainty quoted twice.
- Uncertainty is not symmetric by nature. A model may be far better known on
  the hot side than the cold, and carrying one number for both directions
  either wastes design margin or hides a cold-case breach.
- Zero margin is a finding, not a pass. An item whose inflated prediction
  lands exactly on its allowable limit has consumed everything, and the
  correct response is to say so rather than to let a rounding decide.

## Workflow

1. Validate each item: a name, a predicted minimum and maximum with the
   maximum not below the minimum, non-negative hot and cold uncertainties,
   and allowable limits with the upper strictly above the lower.
2. Reject a temperature that is not physically real. Absolute zero is a
   floor, and a limit pair that crosses is an input error rather than a
   degenerate case to be reordered silently.
3. Inflate the prediction: the hot case rises by the hot uncertainty, the
   cold case falls by the cold uncertainty. Every later comparison uses the
   inflated pair.
4. Place the inflated range against the two range boundaries, and record
   every range it touches. An item touching more than one is grouped under
   all of them, and that is itself reported.
5. Compute the hot margin as the allowable maximum minus the inflated hot
   prediction, and the cold margin as the inflated cold prediction minus the
   allowable minimum.
6. Decide compliance on those margins, absorbing representation error at the
   boundary with a named tolerance instead of by moving the limit. A margin
   that is zero within tolerance is compliant and flagged as exhausted.
7. Aggregate: count the items in each range, list the breaches hot and cold,
   list the exhausted margins, and name the item with the least margin in
   each direction so the design driver is visible.
8. Report the grouped table as the performance basis the rest of the thermal
   design is argued from.

## Pitfalls

- Placing an item by its nominal operating point. The cold survival case is
  what pulls hardware into the cryogenic range, and it is the case that gets
  left out of the grouping.
- Comparing a raw prediction with an allowable limit. The uncertainty belongs
  on the prediction before the comparison, otherwise the margin reported is
  larger than the margin held.
- Using one uncertainty for both directions because the model report quoted
  one number. The hot and cold sides are rarely known equally well.
- Quoting a survival limit as the operational one. It is the widest number in
  the datasheet and the most tempting, and it does not bound the range the
  item has to work in.
- Treating an item that straddles a boundary as belonging to whichever range
  most of its range falls in. It owes both rule sets, and the cryogenic rules
  in particular are not a subset of the conventional ones.
- Letting a margin of exactly zero pass silently as compliant. It is
  compliant and it is also the finding that the design has nothing left.

## Behavior contract (gate 3)

The item validation, uncertainty inflation, range placement against both
boundaries, hot and cold margin computation, compliance decision under a
named tolerance and the aggregate design-driver selection are exercised by
the gate 3 contract test:
scripts/test_e31_temperature_ranges_allowable_limits_classification.py
against
scripts/e31_temperature_ranges_allowable_limits_classification_logic.py
(stdlib unittest, offline). Run:
python3 scripts/test_e31_temperature_ranges_allowable_limits_classification.py

## Compliance

- ECSS standards are freely downloadable (ESA); cite the source and
  paraphrase per standards-map.yaml.
- compliance: STANDARDS-REF, gated: false.
