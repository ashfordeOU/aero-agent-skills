---
name: q6013-class-1-derating-rules
description: "Verify that every electrical and thermal stress on a selected commercial EEE part sits inside the Class 1 derating limits of ECSS-Q-ST-60-13C clause 4.2.2.5: look up the part family's voltage, current and power ratios and its junction step-down, turn each maker rating into the largest applied value the rule leaves, grade the applied stresses and the predicted junction temperature against those limits, name the tightest margin, and state the drop a breach needs. Use when a Class 1 build has to show a commercial part runs inside its derated envelope. Trigger: ecss, q-st-60-13-commercial-eee-scope, class-1-eee-derating-limits, commercial-part-voltage-derating, commercial-part-current-derating, commercial-part-power-dissipation-derating, junction-temperature-step-down, derated-stress-ratio-margin."
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
  tags: [ecss, q-st-60-13-commercial-eee-scope, q6013-class-1-derating-rules, class-1-eee-derating-limits, commercial-part-voltage-derating, commercial-part-current-derating, commercial-part-power-dissipation-derating, junction-temperature-step-down, derated-stress-ratio-margin, commercial-part-family-derating-table]
  version: 0.1.0
  author: Aero Agent Skills
---

# ECSS Commercial EEE — Class 1 Derating Rules (space-systems/ecss/q6013-class-1-derating-rules)

Use when the task is the stress limiting of ECSS-Q-ST-60-13C clause
4.2.2.5 -- turning a commercial part's maker rating into the smaller
envelope a Class 1 build is allowed to work it in, and grading the
applied electrical and thermal stresses against that envelope.

## Domain quick reference

- A commercial part is rated by its maker for a commercial life in a
  commercial environment. A Class 1 build never uses that rating
  directly: a derating factor is applied to every electrical stress and
  a step down to the temperature ceiling, so the part spends its life
  well inside the envelope the datasheet draws.
- Electrical stress is kept as a ratio of applied to rated: the steady
  working voltage against the rated voltage, the steady working current
  against the rated current, and the dissipated power against the rated
  dissipation. Thermal stress is kept as an absolute ceiling, expressed
  as a step down from the rated maximum junction or hot-spot
  temperature.
- Each part family carries its own table, because the mechanism the
  derating protects against differs -- dielectric wear-out on a ceramic
  capacitor, electromigration on a die interconnect, contact erosion on
  a relay. One blanket factor across a board is not a derating rule,
  it is an average of unrelated mechanisms.
- A commercial part earns a tighter table than a space-qualified one.
  The maker's rating was taken over a narrower temperature range, on a
  line that may move without notice, so the extra step down covers
  spread the project cannot see.
- The useful output is not the pass or fail. It is the allowable
  applied value each rule leaves, the headroom against it, and which
  single stress is closest to its limit -- that is the one a thermal
  excursion or a rating change will break first.
- A derating result with no junction temperature is half a result. The
  electrical stresses can all sit low while the part cooks, so an
  absent temperature is reported as not yet demonstrated rather than
  quietly passed.

## Workflow

1. Declare the part family, each applied stress with the maker rating
   it works against, and the predicted junction temperature with its
   rated maximum. Reject an uncategorized family rather than defaulting
   it; the table is chosen by family.
2. Look up the family's voltage, current and power ratios and its
   junction step-down. Reject a table that does not cover every family
   and every stress with a factor inside the rating.
3. Turn each rating into the largest applied value the rule leaves, so
   the answer a designer needs is a number rather than a verdict.
4. Grade each applied stress against its limit and the predicted
   junction against the derated ceiling. Report a stress sitting
   exactly on its limit as on-limit and compliant, not as a breach.
5. Name the tightest margin across the graded stresses; that is where
   the design has the least room and where the next change will land.
6. Close with one verdict and, for every breach, the applied value the
   stress has to drop to or the temperature the junction has to reach.

## Pitfalls

- Applying one blanket factor to every part on the board. The families
  fail by different mechanisms, so a ceramic capacitor and a digital
  integrated circuit do not share a voltage rule, and averaging them
  overstresses whichever is tighter.
- Derating against a peak rather than the steady working stress, or the
  reverse. The ratio has to be built from the stress the rule was
  written for, and mixing a transient peak into a steady-stress rule
  fails parts that are fine and passes parts that are not.
- Grading the junction against the maker's rated maximum. The rated
  maximum is where the part is destroyed; the derated ceiling is where
  the project agrees to stop, and the whole step down is the margin.
- Passing a part on its electrical stresses alone. Every ratio can sit
  low while the junction runs hot, so a missing temperature is an open
  item, not a silent pass.
- Comparing a ratio with its limit by bare arithmetic. The ratio is a
  quotient and the allowable is a product, so a stress built to sit
  exactly on its limit can land a few units in the last place above it;
  the comparison absorbs that representation error while the limit
  stays untouched.

## Behavior contract (gate 3)

The table validation, limit lookup, stress ratio, allowable applied
value, thermal ceiling, per-stress grading, tightest-margin selection
and overall verdict are exercised by the gate 3 contract test:
scripts/test_q6013_class_1_derating_rules.py against
scripts/q6013_class_1_derating_rules_logic.py (stdlib unittest,
offline). Run:
python3 scripts/test_q6013_class_1_derating_rules.py

## Compliance

- ECSS standards are freely downloadable (ESA); cite the source and
  paraphrase per standards-map.yaml.
- compliance: STANDARDS-REF, gated: false.
