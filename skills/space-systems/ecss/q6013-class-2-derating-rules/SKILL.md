---
name: q6013-class-2-derating-rules
description: "Use when a Class 2 build has to show a commercial part runs inside its derated envelope. Verify that every electrical and thermal stress on a selected commercial EEE part sits inside the intermediate assurance derating limits of ECSS-Q-ST-60-13C clause 5.2.2.5: look up the part family's voltage, current and power ratios and its junction step-down, turn each maker rating into the largest applied value the rule leaves, derive a junction temperature from a measured case temperature where none was predicted, grade each applied stress, carry a stress past its limit only inside the approved relaxation band, and name the tightest margin. Trigger: ecss, q-st-60-13c-clause-5-2-2-5, class-two-eee-derating-limits, commercial-part-voltage-derating, commercial-part-power-dissipation-derating, junction-temperature-step-down, approved-derating-relaxation-band, junction-from-case-temperature."
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
  tags: [ecss, q-st-60-13-commercial-eee-component-scope, q6013-class-2-derating-rules, class-two-eee-derating-limits, commercial-part-voltage-derating, commercial-part-current-derating, commercial-part-power-dissipation-derating, junction-temperature-step-down, approved-derating-relaxation-band, junction-from-case-temperature]
  version: 0.1.0
  author: Aero Agent Skills
---

# ECSS Commercial EEE Components -- Class 2 Derating Rules (space-systems/ecss/q6013-class-2-derating-rules)

Use when the task is the stress limiting of ECSS-Q-ST-60-13C clause
5.2.2.5 at the intermediate assurance class -- turning a commercial
part's maker rating into the smaller envelope the build is allowed to
work it in, and grading the applied electrical and thermal stresses
against that envelope.

## Domain quick reference

- A commercial part is rated by its maker for a commercial life in a
  commercial environment. The rating is never used directly: a derating
  factor is applied to every electrical stress and a step down to the
  temperature ceiling, so the part spends its life inside the envelope
  the datasheet draws.
- Electrical stress is kept as a ratio of applied to rated: the steady
  working voltage against the rated voltage, the steady working current
  against the rated current, and the dissipated power against the rated
  dissipation. Thermal stress is kept as an absolute ceiling, expressed
  as a step down from the rated maximum junction or hot-spot
  temperature.
- Each part family carries its own table, because the mechanism the
  derating protects against differs -- dielectric wear-out on a ceramic
  capacitor, electromigration on a die interconnect, contact erosion on
  a relay. One blanket factor across a board is not a derating rule, it
  is an average of unrelated mechanisms.
- The table at this class is looser than the one above it. More of the
  maker's rating is left available, because the class carries a lower
  assurance target and pays for it with less margin against the spread
  a commercial line can move by.
- This class also admits a bounded relaxation, which the class above
  does not. A single electrical stress may be carried past its table
  limit by no more than a fixed band where a derating relaxation record
  has been raised and approved for that stress on that part. Past the
  band the record buys nothing.
- The thermal ceiling takes no relaxation at any class. The step down
  is the whole of the margin against a wear-out mechanism, so a record
  that moves it is moving the mechanism, not the paperwork.
- A junction temperature that was never predicted directly can still be
  had: the measured case temperature, the junction-to-case thermal
  resistance and the dissipated power give it. A result with no
  junction figure at all is half a result and is reported as not yet
  demonstrated rather than quietly passed.
- The useful output is not the pass or fail. It is the allowable
  applied value each rule leaves, the headroom against it, and which
  single stress is closest to its limit -- that is the one a thermal
  excursion or a rating change will break first.

## Workflow

1. Declare the part family, each applied stress with the maker rating
   it works against, any approved relaxation record per stress, and
   either a predicted junction temperature or the case temperature,
   thermal resistance and dissipation to derive one. Reject an
   uncategorized family rather than defaulting it; the table is chosen
   by family.
2. Look up the family's voltage, current and power ratios and its
   junction step-down. Reject a table that does not cover every family
   and every stress with a factor inside the rating.
3. Turn each rating into the largest applied value the rule leaves, so
   the answer a designer needs is a number rather than a verdict.
4. Grade each applied stress. A stress sitting exactly on its limit is
   on-limit and compliant. A stress past the limit is a breach unless
   an approved record covers that stress and the overshoot stays inside
   the band.
5. Resolve the junction temperature, derive it from the case where it
   was not predicted, and grade it against the derated ceiling with no
   relaxation available.
6. Name the tightest margin across the graded stresses; that is where
   the design has the least room and where the next change will land.
7. Close with one verdict, separating a clean pass from one that leans
   on an approved relaxation, and for every breach give the applied
   value the stress has to drop to or the temperature the junction has
   to reach.

## Pitfalls

- Applying one blanket factor to every part on the board. The families
  fail by different mechanisms, so a ceramic capacitor and a digital
  integrated circuit do not share a voltage rule, and averaging them
  overstresses whichever is tighter.
- Reading the looser table as the whole of the class difference. The
  relaxation band is the other half, and it only opens where a record
  names the stress and the part; an unrecorded overshoot is a breach at
  this class exactly as it is above.
- Letting an approved record carry a stress any distance. The band is
  bounded, and a record covering an overshoot past it is a waiver
  against a mechanism rather than a derating decision.
- Relaxing the junction ceiling. The step down is the margin, and the
  record that would move it is moving the wear-out life of the part.
- Passing a part on its electrical stresses alone. Every ratio can sit
  low while the junction runs hot, so a missing temperature that cannot
  be derived is an open item, not a silent pass.
- Comparing a ratio with its limit by bare arithmetic. The ratio is a
  quotient and the allowable is a product, so a stress built to sit
  exactly on its limit or on the band edge can land a few units in the
  last place above it; the comparison absorbs that representation error
  while the limit stays untouched.

## Behavior contract (gate 3)

The table validation, limit lookup, stress ratio, allowable applied
value, relaxation band, junction derivation from case temperature,
thermal ceiling, per-stress grading, tightest-margin selection and
overall verdict are exercised by the gate 3 contract test:
scripts/test_q6013_class_2_derating_rules.py against
scripts/q6013_class_2_derating_rules_logic.py (stdlib unittest,
offline). Run:
python3 scripts/test_q6013_class_2_derating_rules.py

## Compliance

- ECSS standards are freely downloadable (ESA); cite the source and
  paraphrase per standards-map.yaml.
- compliance: STANDARDS-REF, gated: false.
