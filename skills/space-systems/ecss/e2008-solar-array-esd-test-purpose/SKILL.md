---
name: e2008-solar-array-esd-test-purpose
description: "Determine whether a planned electrostatic-discharge test on a solar-array coupon can show what ECSS-E-ST-20-08C clause 5.5.1.5.1 asks of it: that the design rules applied to the array hold the discharge risk down. Use when a coupon campaign is scoped or reviewed before it runs: derive from the declared environment which discharge mechanisms the coupon can really be driven into, group design-rule provisions by the mechanism each limits, keeping only those embodied on the coupon, check the planned conditions drive every mechanism with a bias and string current bounding the worst case, check the discharge population against the campaign minimum, then report covered and uncovered mechanisms with the coverage fraction. Trigger: ecss, e-st-20-08c, solar-array-coupon-esd-test-purpose, array-design-rule-effectiveness, triple-junction-inception-driver, differential-surface-charging-driver, string-to-string-arc-propagation, coupon-representativeness-screening, esd-test-bias-envelope, discharge-population-adequacy."
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
  tags: [ecss, e-st-20-electrical-scope, e2008-solar-array-esd-test-purpose, e-st-20-08c, solar-array-coupon-esd-test, array-design-rule-effectiveness, triple-junction-inception-driver, differential-surface-charging-driver, string-to-string-arc-propagation, coupon-representativeness-screening]
  version: 0.1.0
  author: Aero Agent Skills
---

# ECSS Photovoltaic Assemblies — Array ESD Test Purpose (space-systems/ecss/e2008-solar-array-esd-test-purpose)

Use when the task is the clause 5.5.1.5.1 objective of ECSS-E-ST-20-08C:
an electrostatic-discharge test is to be run on a solar-array coupon, and
what the test exists to show is that the design rules carried by the
array keep the discharge risk within bounds. The decision to make before
the campaign runs is whether the planned test can demonstrate that at
all.

## Domain quick reference

- The clause states a purpose rather than a measurement, and a purpose
  can be missed by a test that passes. A campaign that never drives the
  mechanism a design rule was written against, or that drives it on a
  coupon the rule is not embodied on, produces a clean record while
  demonstrating nothing about the flight array.
- Three coupon-level mechanisms carry design rules of their own.
  Differential surface charging needs exposed ungrounded dielectric and a
  surface potential past the charging onset. Triple-junction inception
  needs the dielectric-to-conductor potential to reach the inception
  threshold set by coverglass and interconnect geometry. String-to-string
  propagation needs the string voltage to reach the propagation threshold
  and the string to be able to feed the discharge current.
- A mechanism the environment cannot drive is outside the purpose of the
  test, not a gap in it. Narrowing the objective to the mechanisms the
  environment really drives is what keeps the campaign honest; padding it
  with mechanisms a 28 V bus can never reach is not conservatism.
- Embodied and representative are two different questions about the same
  provision. A rule can be present on the coupon in a form that does not
  reproduce the flight geometry, material or grounding, and that coupon
  exercises the mechanism without saying anything about the rule. Both
  flags have to hold before a provision counts toward the objective.
- The applied envelope has to bound the environment, per mechanism. For
  the two surface mechanisms the applied bias is compared against the
  worst-case differential potential; for propagation it is the
  string-to-string voltage and the current the string can feed that have
  to be bounded, since a discharge that the supply cannot sustain says
  nothing about a design rule meant to stop propagation.

## Workflow

1. Validate the declared environment and derive the driving mechanisms
   from it, treating a value exactly at a threshold as driving rather
   than as clear.
2. Validate the declared design-rule provisions — unique identifiers,
   recognized mechanism, explicit embodied and representative flags — and
   group them under the mechanism each one limits.
3. For each driving mechanism, keep the provisions that are both embodied
   on the coupon and representative. None surviving is a finding, worded
   differently depending on whether no rule was declared at all or the
   declared rules failed to reach the coupon.
4. Check the planned conditions against each driving mechanism: the
   mechanism has to appear in the exercised set, and the applied bias —
   plus the applied string current for propagation — has to bound the
   worst case, with an exact equality admitted through a named tolerance.
5. Raise a standing finding for every provision embodied in a
   non-representative form, even on a mechanism that is otherwise
   covered, and check the planned discharge population against the
   campaign minimum.
6. Report the driving, covered and uncovered mechanisms, the coverage
   fraction and the findings. The purpose is demonstrable only when the
   finding list is empty.

## Pitfalls

- Reading a clean discharge record as evidence that the design rules
  work. Evidence requires the mechanism to have been driven on a coupon
  that carries the rule; without both, the record is silent rather than
  favourable.
- Testing the coupon at the bus voltage instead of at the worst-case
  differential potential. Surface charging drives the dielectric far past
  the bus, and an envelope built on the bus figure leaves the mechanism
  untested.
- Counting a declared design rule as demonstrated. A provision on a
  drawing that never reached the coupon, or reached it in a
  non-representative form, cannot be shown effective by that coupon.
- Padding the objective with mechanisms the environment cannot drive. It
  inflates the campaign and buries the mechanisms that matter; the
  environment is what fixes the scope.
- Running a handful of discharges. A design rule limits a risk rate, so a
  discharge population short of the campaign minimum cannot separate an
  effective rule from a lucky coupon.

## Behavior contract (gate 3)

The environment-driven mechanism derivation, the design-rule grouping and
embodiment screening, the per-mechanism envelope check, the discharge
population check and the aggregated objective verdict are exercised by
the gate 3 contract test:
scripts/test_e2008_solar_array_esd_test_purpose.py against
scripts/e2008_solar_array_esd_test_purpose_logic.py (stdlib unittest,
offline). Run:
python3 scripts/test_e2008_solar_array_esd_test_purpose.py

## Compliance

- ECSS standards are freely downloadable (ESA); cite the source and
  paraphrase per standards-map.yaml.
- compliance: STANDARDS-REF, gated: false.
