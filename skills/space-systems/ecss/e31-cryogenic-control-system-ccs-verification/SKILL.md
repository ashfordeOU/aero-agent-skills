---
name: e31-cryogenic-control-system-ccs-verification
description: "Verify a cryogenic control system against its agreed objectives and setups per ECSS-E-ST-31C clause 4.5.2.2. Use when a cooler, cold stage, thermal strap or cryo-radiator has to be shown compliant at the level the programme agreed: compute heat-lift margin at the operating point, peak-to-peak stability across the observation window, cooldown slack and the parasitic-load roll-up against its allocation, then confirm each objective closed at a level at least as detailed as agreed and by the agreed method, and refuse a run whose sink temperature, chamber pressure or boundary simulator never met the agreed setup. Trigger: ecss, e-st-31-thermal-control, e31-cryogenic-control-system-ccs-verification, cryogenic-cooler-heat-lift-margin, cryogenic-temperature-stability-window, ccs-verification-level-coverage, cryogenic-parasitic-heat-load-budget, cryogenic-test-setup-sink-conditions."
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
  tags: [ecss, e-st-31-thermal-control, e31-cryogenic-control-system-ccs-verification, cryogenic-cooler-heat-lift-margin, cryogenic-temperature-stability-window, ccs-verification-level-coverage, cryogenic-parasitic-heat-load-budget, cryogenic-test-setup-sink-conditions]
  version: 0.1.0
  author: Aero Agent Skills
---

# ECSS Thermal Control — Cryogenic Control System Verification (space-systems/ecss/e31-cryogenic-control-system-ccs-verification)

Use when the task is the cryogenic step of ECSS-E-ST-31C clause 4.5.2.2 --
showing that the cryogenic control system meets the verification objectives
that were agreed for it, at the level they were agreed at, in the test setup
that was agreed for them.

## Domain quick reference

- The clause has three nouns and all three are graded: the objective, the
  level, and the setup. A perfect measurement taken in a setup nobody agreed
  to is evidence about that setup, not about the cryogenic chain.
- Level matters in one direction only. An instrument-level objective exists
  because it exercises an interface that disappears once the instrument is
  inside the subsystem, so a subsystem run cannot close it. The reverse
  substitution -- an instrument run closing a subsystem objective -- is a
  finding about paperwork, not about coverage.
- Heat lift is graded as a fraction of the required duty, not as a watt
  difference. A 50 mW shortfall is trivial on a 5 W cooler and fatal on a
  100 mW one, and only the fraction says which case is on the bench.
- Stability is a peak-to-peak excursion over a stated observation window. A
  mean and a standard deviation hide the single transient that breaks a
  detector's integration, so the window is reduced by max minus min.
- Parasitic heat is a budget with named paths, and the roll-up carries the
  dominant path with it. Knowing the total is over by 40 mW is useless;
  knowing the struts carry 300 mW of it is the design action.
- Sink temperature, chamber pressure and the boundary simulator are the
  three setup conditions that silently flatter a cryogenic result: a cold
  shroud, a hard vacuum or an absent warm boundary each removes load the
  flight configuration will apply.
- Margins and slacks are differences and quotients of measured floats. A
  quantity sitting exactly on its limit is absorbed by a named tolerance far
  below any sensor resolution, not by relaxing the limit.

## Workflow

1. List the agreed verification objectives. For each, record the quantity it
   grades, the level it was agreed at, the method agreed to close it, and the
   level and method it was actually closed at.
2. Refuse the register when a level or method is outside the agreed
   vocabulary, when an objective identifier repeats, or when an objective
   carries no quantity to grade.
3. Grade the achieved setup against the agreed setup before looking at any
   result: sink temperature no warmer, chamber pressure no higher, boundary
   simulator installed where agreed.
4. Compute heat-lift margin as the fractional excess of available lift over
   the required duty at the operating temperature.
5. Reduce the stability window to its peak-to-peak excursion and compare it
   with the allowance using the named tolerance.
6. Compute cooldown slack as the agreed duration minus the measured one, so
   an overrun reads as a negative number rather than a boolean.
7. Sum the parasitic paths, compare with the allocation, and carry the
   dominant path into the report.
8. Close the coverage loop: every required quantity needs a conforming
   objective, and a non-conforming objective covers nothing.

## Pitfalls

- Accepting a subsystem run as closure of an instrument-level objective
  because the number looks good. The number is right and the interface it
  was written to exercise was never in the loop.
- Grading heat lift in watts. The same watt shortfall is noise on one cooler
  and a mission loss on another; the fraction is the graded quantity.
- Reporting stability as a mean and a spread. The excursion that matters is
  the extreme pair in the window, and averaging removes it.
- Reading a clean result out of an over-cold shroud or an over-hard vacuum.
  Both remove parasitic load the flight case applies, so the setup is graded
  first and the result is withheld until it conforms.
- Rolling the parasitic budget up to a single total. Without the dominant
  path the report names an overspend but no design action.
- Using a strict comparison at the allocation or the duty point. These are
  quotients and sums of floats; a value exactly on the limit must conform on
  every platform, which is what the named tolerance is for.
- Treating a non-conforming objective as coverage of its quantity. A closed
  objective that deviates on level or method leaves the quantity open.

## Behavior contract (gate 3)

The level and method vocabularies, the heat-lift margin, the peak-to-peak
stability reduction and its tolerance, cooldown slack, the parasitic
roll-up with its dominant path, setup grading and the objective coverage
loop are exercised by the gate 3 contract test:
scripts/test_e31_cryogenic_control_system_ccs_verification.py against
scripts/e31_cryogenic_control_system_ccs_verification_logic.py (stdlib
unittest, offline). Boundary cases are graded with assertAlmostEqual so a
value landing on its limit reads the same on every platform.
Run: python3 scripts/test_e31_cryogenic_control_system_ccs_verification.py

## Compliance

- ECSS standards are freely downloadable (ESA); cite the source and
  paraphrase per standards-map.yaml.
- compliance: STANDARDS-REF, gated: false.
