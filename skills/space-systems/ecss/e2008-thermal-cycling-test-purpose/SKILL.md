---
name: e2008-thermal-cycling-test-purpose
description: "Compute the cycle count, temperature extremes and cycle equivalence a solar-array thermal-cycling run has to reach before it demonstrates the fatigue endurance of the components and the assembly processes of a photovoltaic assembly, anchored at ECSS-E-ST-20-08C clause 5.5.1.3.1. Use when the task is sizing or reviewing that run: derive the in-orbit cycle count from the orbit period, the mission duration and the eclipse fraction, form the crack-growth equivalence between the in-orbit swing and the wider test swing, convert it into a required test-cycle count, check the test extremes envelope the predicted extremes with their margin, bound the transition ramp and the dwell, and confirm every flight component and process family appears on the cycled article. Trigger: ecss, e-st-20-08c, solar-array-thermal-cycling, fatigue-endurance-demonstration, in-orbit-cycle-count, cycle-equivalence-exponent, cycling-temperature-extremes, cycling-ramp-rate-bound, process-family-coverage."
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
  tags: [ecss, e-st-20-electrical-scope, e-st-20-08c, e2008-thermal-cycling-test-purpose, solar-array-thermal-cycling, fatigue-endurance-demonstration, in-orbit-cycle-count, cycle-equivalence-exponent, cycling-temperature-extremes]
  version: 0.1.0
  author: Aero Agent Skills
---

# ECSS Photovoltaic Assemblies — Thermal Cycling Test Purpose (space-systems/ecss/e2008-thermal-cycling-test-purpose)

Use when the task is the purpose rule of ECSS-E-ST-20-08C clause
5.5.1.3.1 — showing that a thermal-cycling run on a photovoltaic
assembly actually demonstrates the fatigue endurance of its components
and of the processes that joined them, rather than being a fixed number
of cycles carried over from an earlier programme.

## Domain quick reference

- The damage the run has to reproduce is fatigue at the joints: the
  cell-to-interconnect weld, the coverglass bond, the substrate bond and
  the string-to-harness termination. Each joins materials whose
  expansion coefficients differ, so every eclipse entry and exit works
  the joint. Endurance is therefore demonstrated by cycle count against
  swing, never by a single soak at an extreme.
- The in-orbit count follows from the mission, not from a habit. Orbits
  per year is the year length divided by the orbit period; the fraction
  of those orbits that carry an eclipse turns orbits into cycles. A low
  orbit gives thousands of cycles a year, a geostationary one fewer than
  a hundred, and the same assembly therefore needs very different runs.
- A run is shortened by widening the swing, not by dropping cycles.
  Crack growth per cycle scales with the swing raised to a power, so a
  test swing wider than the in-orbit swing makes one test cycle stand
  for several in-orbit cycles. The exponent is a property of the joint,
  conventionally two for a ductile joint and higher for a brittle one,
  and it is declared before the count is derived.
- The extremes are bounded from both directions. They envelope the
  predicted extremes plus the design margin, so the run is at least as
  severe as flight; the transition ramp stays under its bound and the
  dwell is long enough for the assembly to reach its extreme, so the run
  is not severe in a way flight never is and not milder than it reads.
- A family absent from the cycled article is a family the run
  demonstrates nothing about. Coverage of the flight component and
  process families is part of the purpose, not a separate bookkeeping
  step, because an uncycled process carries no endurance evidence at
  all.

## Workflow

1. Validate the predicted in-orbit extremes and the extremes the run is
   driven between; an inverted or collapsed pair is an input error, not
   a degenerate case to be clamped. Form both swings in kelvin.
2. Derive the in-orbit cycle count from the orbit period, the mission
   duration and the eclipse fraction, rounding up to a whole cycle but
   absorbing representation error so an exactly integral count is not
   bumped by one.
3. Form the cycle equivalence from the swing ratio and the declared
   exponent. Record it: a narrower test swing gives a factor below one
   and lengthens the run rather than shortening it.
4. Convert the in-orbit count into the required test-cycle count,
   applying the demonstration factor, and keep a floor so a favourable
   equivalence can never reduce a demonstration to a token run.
5. Check the test extremes envelope the predicted extremes with their
   margin, treating an extreme sitting exactly on its required value as
   compliant — the tolerance belongs on the comparison, never on the
   margin.
6. Check the dwell against what the assembly needs to stabilise and, when
   a transition time is declared, the ramp rate against its bound.
7. Compare the article's component and process families against the
   flight set and name every family the run would leave uncycled. The
   purpose is demonstrated only when the finding list is empty.

## Pitfalls

- Carrying a cycle count across from another programme. The count is a
  function of orbit period, mission duration and eclipse fraction; the
  same article on a different orbit needs a different run, and reusing a
  number silently swaps one mission's fatigue exposure for another's.
- Shortening the run by dropping cycles instead of widening the swing.
  Cycles are only tradable through the equivalence, and the equivalence
  needs a declared exponent; without one the shortened run demonstrates
  a shorter mission, not the same one.
- Taking the exponent from the most favourable joint on the article. The
  governing joint is the most brittle one, so an exponent chosen to
  shrink the count is exactly the exponent that does not describe the
  joint most likely to crack.
- Widening the test extremes to buy equivalence without checking the
  ramp and the dwell. A wider swing reached too fast, or held too
  briefly, tests the chamber rather than the assembly and can add a
  failure mode flight never produces.
- Cycling an article that omits a process family. The evidence follows
  the hardware, so a termination or bond absent from the coupon leaves
  that process with no endurance demonstration however many cycles the
  rest of the article survives.
- Relaxing the margin to close a boundary case. An extreme exactly on
  its required value is compliant already; the representation error is
  absorbed by a named kelvin-scale tolerance inside the comparison.

## Behavior contract (gate 3)

The extreme validation, in-orbit cycle derivation, cycle equivalence,
required-count conversion, envelope, ramp and dwell checks and the
process-family coverage are exercised by the gate 3 contract test:
scripts/test_e2008_thermal_cycling_test_purpose.py against
scripts/e2008_thermal_cycling_test_purpose_logic.py (stdlib unittest,
offline). Run:
python3 scripts/test_e2008_thermal_cycling_test_purpose.py

## Compliance

- ECSS standards are freely downloadable (ESA); cite the source and
  paraphrase per standards-map.yaml.
- compliance: STANDARDS-REF, gated: false.
