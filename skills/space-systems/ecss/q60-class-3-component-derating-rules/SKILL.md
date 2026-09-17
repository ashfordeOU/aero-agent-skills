---
name: q60-class-3-component-derating-rules
description: "Verify that every Class 3 part in an equipment design is worked inside its stress reduction margin under ECSS-Q-ST-60C clause 6.2.2.5: walk each maker rating down its derating line from the reference point toward the zero-rating temperature at the case temperature this part actually runs at, discount a rating taken from a typical column rather than a guaranteed limit, apply the category margin to what is left, open the applied stress out by its measurement uncertainty, and name the tightest part. Use when a Class 3 box has to show its parts are derated at their real operating temperature. Trigger: ecss, q-st-60c, q60-class-3-component-derating-rules, q60-c3-temperature-derated-rating, q60-c3-rating-source-discount, q60-c3-tightest-derated-part, q60-c3-derating-verdict."
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
  tags: [ecss, q-st-60c-eee-selection-scope, q-st-60c, q60-class-3-component-derating-rules, q60-c3-temperature-derated-rating, q60-c3-rating-source-discount, q60-c3-applied-stress-uncertainty, q60-c3-tightest-derated-part, q60-c3-derating-verdict]
  version: 0.1.0
  author: Aero Agent Skills
---

# ECSS EEE Components — Class 3 Component Derating Rules (space-systems/ecss/q60-class-3-component-derating-rules)

Use when the task is clause 6.2.2.5 of ECSS-Q-ST-60C: showing that every Class
3 part used in an equipment design is worked inside a stress reduction margin.
The leaf exists because a Class 3 part comes off a line the project does not
control, so the number printed beside it is the first thing that has to be
corrected, not the thing the margin is applied to.

## Domain quick reference

- Three corrections stand between a printed rating and the largest stress a
  designer may apply, and they are applied in order: temperature first, then
  the confidence the rating deserves, then the category margin.
- A rating is quoted at a reference point. Above that point it falls along a
  straight line and reaches nothing at the part's zero-rating temperature. The
  rating that matters is the one left at the case temperature this part runs
  at, which is why a part with no declared case temperature cannot be graded
  at all.
- Where the number came from changes what it is worth. A guaranteed limit
  stands as printed; a typical column is a central value with a population
  around it, and a vendor estimate is weaker still. The discount is applied to
  the temperature-corrected rating, before the margin.
- The margin is applied last, to what the first two corrections left. Applying
  it to the printed number is the common error, and it is the one that puts a
  hot part over its real limit while every ratio on the sheet looks healthy.
- The applied stress is opened out by the measurement uncertainty the project
  carries on it. A stress known to a few per cent is not the same input as one
  measured on a bench at the flight temperature.
- Case temperature carries its own check, a step down from the rated maximum,
  because an electrically comfortable part can still sit above the temperature
  at which its package is qualified to work.
- The useful outputs are the per-stress utilisation, the tightest part in the
  equipment, and a verdict that keeps a breach and an ungradeable part apart.

## Workflow

1. Declare each part with its reference, category, quantity, case temperature
   and rated maximum case temperature. Reject an uncategorized part rather
   than defaulting it; the margins are chosen by category.
2. For every declared stress, walk the rating down its derating line to the
   part's case temperature, returning the full rating at or below the
   reference point and nothing at or above the zero-rating point.
3. Discount the corrected rating by its source, then apply the category
   margin, producing the largest applied value the clause leaves.
4. Build the applied stress from its nominal value and the measurement
   uncertainty carried on it.
5. Grade each stress. Report an applied value sitting exactly on its allowable
   as on-margin and compliant, not as a breach.
6. Grade the case temperature against the stepped-down ceiling.
7. Close with one equipment verdict — satisfied, indeterminate where a case
   temperature or a rated maximum is missing, or exceeded — plus the tightest
   part and the share of the population actually graded.

## Pitfalls

- Applying the margin to the printed rating. The printed number belongs to a
  reference temperature the part is not running at, so the margin computed
  from it is an allowance against a condition that never occurs.
- Treating a part with no declared case temperature as passing. Its rating
  cannot be placed on the derating line, so the honest answer is
  indeterminate, and rolling it in with the passes hides it.
- Reading a typical column as a limit. It is a central value, and half the
  population sits the other side of it.
- Grading the nominal applied stress. The uncertainty the project carries on
  the measurement belongs inside the comparison, not in a footnote under it.
- Passing a part on its electrical ratios alone. Every ratio can sit low while
  the case runs above the temperature its package is qualified for.
- Reporting only the first breached stress on a part. Each breach names a
  different repair, and a design change needs all of them.
- Comparing an applied stress with its allowable by bare arithmetic. Both
  sides are chains of products, so a stress built to sit exactly on its
  allowable can land a few units in the last place either side; the comparison
  absorbs that representation error while the allowable stays untouched.

## Behavior contract (gate 3)

The margin table validation, source discount, temperature-derated rating,
applied-stress build-up, allowable applied value, per-stress grading, case
temperature ceiling, per-part rollup, tightest-part selection and equipment
verdict are exercised by the gate 3 contract test:
scripts/test_q60_class_3_component_derating_rules.py against
scripts/q60_class_3_component_derating_rules_logic.py (stdlib unittest,
offline). Run:
python3 scripts/test_q60_class_3_component_derating_rules.py

## Compliance

- ECSS standards are freely downloadable (ESA); cite the source and
  paraphrase per standards-map.yaml.
- compliance: STANDARDS-REF, gated: false.
