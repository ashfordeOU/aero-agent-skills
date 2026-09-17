---
name: q60-class-2-component-derating-rules
description: "Compute whether every Class 2 part in an equipment design works inside its stress reduction margin at the temperature it actually runs at, under ECSS-Q-ST-60C clause 5.2.2.5: cut each maker rating back by the retention its category leaves above the knee, apply the category margin to what survives, build every applied stress from its nominal value, tolerance spread, end-of-life drift and transient uplift, grade each one, then name the tightest part and the ambient rise the equipment still absorbs before the first part crosses its limit. Use when a Class 2 equipment has to show its parts are derated at their real operating temperature. Trigger: ecss, q-st-60c-class-2-selection-scope, class-2-equipment-derating-margin, temperature-adjusted-part-rating, derating-knee-linear-rating-cut, class-2-worst-case-stress-build-up, equipment-ambient-thermal-headroom, class-2-tightest-derating-part."
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
  tags: [ecss, q-st-60c-class-2-selection-scope, q60-class-2-component-derating-rules, class-2-equipment-derating-margin, temperature-adjusted-part-rating, derating-knee-linear-rating-cut, class-2-worst-case-stress-build-up, equipment-ambient-thermal-headroom, class-2-tightest-derating-part]
  version: 0.1.0
  author: Aero Agent Skills
---

# ECSS EEE Components — Class 2 Component Derating Rules (space-systems/ecss/q60-class-2-component-derating-rules)

Use when the task is the stress reduction of ECSS-Q-ST-60C clause
5.2.2.5 -- showing that every part used in a Class 2 equipment design
works inside a margin against the rating it still has at its own
operating temperature, and how much hotter the box can get before that
stops being true.

## Domain quick reference

- Two things decide how far below its rating a part is worked. The
  category sets the fraction, because a capacitor, a relay and an
  integrated circuit fail by different mechanisms. The temperature sets
  what the fraction is taken of.
- A maker's rating is the full rating only up to a knee. Above it the
  rating falls away toward the part's maximum, so the margin is applied
  to what is left at the temperature the part runs at, not to the
  headline number on the data sheet.
- Working the margin on the headline rating is the common error. It
  grades a part against a rating the part does not have and passes
  exactly the parts a hot box is about to destroy.
- At or above its maximum there is no rating left to reduce. That is a
  rejected input rather than a zero allowable, because an equipment
  with a part in that state has a thermal problem, not a derating one.
- The applied stress is built, not quoted. It starts from the nominal
  value, opens out by the design tolerance spread, opens out again by
  the drift allowed by end of life, and is finally raised by any
  transient uplift the part sees in service. A part chosen for a Class
  2 design is the one most likely to drift, so leaving the end-of-life
  term out flatters exactly the parts the clause is aimed at.
- Each part category carries its own fractions and its own knee. One
  blanket factor across a board is not a derating rule, it is an
  average of unrelated mechanisms.
- The output a designer needs is not only a verdict. It is the ambient
  rise the equipment still absorbs before the first part crosses its
  limit, and which part and stress that is, because that is what a
  radiator change, a duty change or a hotter neighbour eats first.
- A stress already past the flat margined rating has no limiting
  temperature at all: no amount of cooling makes it compliant, so it
  reports no headroom rather than a temperature that would read back as
  margin.

## Workflow

1. Declare each part with its category, the temperature it runs at, and
   each stress as a nominal value with its rating, tolerance spread,
   end-of-life drift and transient uplift. Reject an uncategorized part
   rather than defaulting it; the fractions are chosen by category.
2. Take the retention factor at the part temperature: the whole rating
   up to the knee, then falling linearly to the maximum. Reject a part
   at or above its maximum.
3. Cut the maker rating by the retention, then apply the category
   margin, so the allowable is a number a designer can work to.
4. Build each applied stress from its nominal, tolerance, drift and
   uplift, and grade it. Report a stress sitting exactly on its
   allowable as on-margin and compliant, not as a breach.
5. Solve for the temperature at which each stress would reach its
   allowable, and subtract the part temperature to get the ambient
   headroom that stress leaves.
6. Roll up: the tightest part by utilisation, the binding part and
   stress by least headroom, and one verdict -- demonstrated, breached,
   or demonstrated but with less ambient headroom than the project
   floor.

## Pitfalls

- Applying the margin to the headline rating. Above the knee that
  rating no longer exists, and the error is largest on the hottest
  parts, which are the ones the check is for.
- Grading the nominal stress. The margin exists for the worst case, so
  the tolerance spread, the end-of-life drift and any transient uplift
  are built in before the comparison rather than argued about after it.
- Dropping the end-of-life term. A part that meets its limit on the day
  it is fitted and drifts past it in year four has not been derated,
  it has been measured.
- Treating a part at its maximum temperature as a zero allowable. It is
  a rejected input: the thermal design has to move before the derating
  question means anything.
- Applying one blanket factor to every part. The categories fail by
  different mechanisms, so a relay and an integrated circuit do not
  share a voltage rule, and averaging them overstresses whichever is
  tighter.
- Reporting compliance with no ambient headroom beside it. A design
  passing with two degrees to spare and one passing with forty are both
  compliant and are not the same equipment.
- Reading a headroom figure for a stress that is already past the flat
  margined rating. Cooling cannot buy that stress back, so it reports
  no limiting temperature rather than one that looks like margin.
- Comparing an applied stress with its allowable by bare arithmetic.
  Both are chains of products, so a stress built to sit exactly on its
  allowable can land a few units in the last place above it; the
  comparison absorbs that representation error while the allowable
  stays untouched.

## Behavior contract (gate 3)

The rule-set validation, temperature retention factor, adjusted rating,
applied stress build-up, allowable applied value, limiting temperature,
per-stress grading, per-part rollup, ambient headroom and equipment
verdict are exercised by the gate 3 contract test:
scripts/test_q60_class_2_component_derating_rules.py against
scripts/q60_class_2_component_derating_rules_logic.py (stdlib unittest,
offline). Run:
python3 scripts/test_q60_class_2_component_derating_rules.py

## Compliance

- ECSS standards are freely downloadable (ESA); cite the source and
  paraphrase per standards-map.yaml.
- compliance: STANDARDS-REF, gated: false.
