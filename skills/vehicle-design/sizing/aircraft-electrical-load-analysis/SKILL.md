---
name: aircraft-electrical-load-analysis
description: "Use when you must analyze the aircraft electrical power system load: roll up consumer apparent power (kVA) with each consumer duty cycle into the continuous load, apply the diversity factor for the coincident peak, total the essential load from the named essential consumers at full steady power, check the generator rating against the single-generator-out case where remaining capacity must cover the essential load, and report the load fraction against the installed capacity. Produces the continuous load, the coincident peak, the essential load, the generator-out margin and verdict, and the load fraction that gate the generator sizing. Trigger: aircraft electrical load analysis, electrical load rollup, generator rating check, duty cycle loading, essential load margin, coincident peak load, normal load fraction, single generator out."
license: Apache-2.0
compliance: STANDARDS-REF
standards:
  - id: far-25
    reference-only: true
gated: false
domain: vehicle-design
pack: sizing
compatibility: "agentskills.io SKILL.md; any SKILL.md host (Claude Code, Hermes, OpenClaw)"
metadata:
  domain: vehicle-design
  subdomain: sizing
  tags: [aircraft-electrical-load-analysis, electrical-load-rollup, generator-rating-check, duty-cycle-loading, essential-load-margin]
  version: 0.1.0
  author: AeroSkills
---

# Aircraft Electrical Load Analysis (vehicle-design/sizing/aircraft-electrical-load-analysis)

Use when you must analyze the aircraft electrical power system load at the
sizing level: rolling consumer apparent power (kVA) with each duty cycle
into the continuous load, discounting by the diversity factor for the
coincident peak, booking the essential load at full steady power, and
checking the generator rating against the single-generator-out case. This
leaf implements the standard aircraft electrical load rollup in pure
Python (stdlib only) and pairs with vehicle-design/sizing/battery-sizing
for the traction energy storage side, which CONSUMES a load requirement
but does not build the AC/DC generator and bus load rollup. It is the
aircraft-side counterpart of the spacecraft EPS budget at
space-systems/subsystems/power-thermal-budget. Does NOT do: traction
battery/ESS sizing and mission energy (battery-sizing); power-input
quality acceptance test benches (avionics/do160/power-input); generator
electrical machine design; fault current and protection coordination;
spacecraft EPS (space-systems).

## Domain quick reference

- Consumer model: consumers = {name: (power_kva, duty)} with duty in
  [0, 1], the fraction of flight time the consumer draws its rated power.
- Continuous load: L_c = sum over consumers of power_kva * duty. The
  rollup keeps every per-consumer duty-weighted term in input order.
- Coincident peak: L_pk = DF * L_c with diversity factor DF in (0, 1].
  DF of 1.0 means all loads coincide, so the peak equals the continuous
  load exactly.
- Essential load: L_e = sum of the FULL power_kva of the named essential
  consumers (conservative full-power bookkeeping; they must stay powered
  continuously in the failure case, duty does not discount them).
- Generator-out margin: with n generators each rated S_g the capacity
  left after one generator fails is (n - 1) * S_g. Margin = ((n - 1) *
  S_g - L_e) / ((n - 1) * S_g); verdict PASS when margin >= 0 else FAIL.
  For n == 1 the remaining capacity is 0.0, margin is -1.0 and the
  verdict is FAIL (no redundancy).
- Load fraction: L_c / installed_kva, with installed_kva = n * S_g.
- FAR 25.1355 context (referenced, not reproduced): no essential load may
  be lost when any one power source fails; the margin and verdict
  operationalize that requirement at the sizing level.

## Workflow

1. List every consumer as {name: (power_kva, duty)}, powers in kVA, duty
   the fraction of flight time spent at rated power.
2. Roll the duty-weighted load up with continuous_load(consumers), which
   returns the continuous_kva and the per-consumer rollup.
3. Apply the load diversity with diversity_peak(continuous_kva,
   diversity_factor) to get the coincident peak the generators actually
   see.
4. Name the essential consumers (flight critical, they must survive a
   source failure) and total them at full power with
   essential_load(consumers, essential_names).
5. Check the redundancy with generator_out_margin(n_generators,
   generator_kva, essential_kva): remaining capacity, margin and verdict.
6. Report the normal operating point with load_fraction(continuous_kva,
   installed_kva).
7. Run the whole analysis in one call with ela_summary(consumers,
   diversity_factor, essential_names, n_generators, generator_kva), which
   returns every key above plus installed_kva.
8. Close with the deterministic checks in the contract test
   scripts/test_aircraft_electrical_load_analysis.py.

## Worked example

Reference transport system, eight consumers (kVA, duty): avionics
4.0 / 1.0, flight-control 12.0 / 0.6, comm-nav 2.5 / 1.0, lighting
6.0 / 0.5, galley 35.0 / 0.35, anti-ice 18.0 / 0.25, hydraulic-pumps
12.0 / 0.8, fuel-boost 3.0 / 0.9. Diversity 0.85. Essential names:
avionics, flight-control, comm-nav, fuel-boost. Two 60 kVA generators.
Real module outputs:

- continuous_load: continuous_kva 45.75; rollup [4.0, 7.2, 2.5, 3.0,
  12.25, 4.5, 9.6, 2.7].
- diversity_peak(45.75, 0.85): coincident peak 38.8875 kVA (38.89).
- essential_load: essential_kva 21.5 (4.0 + 12.0 + 2.5 + 3.0 at full
  power), essential_consumers the four named.
- generator_out_margin(2, 60, 21.5): remaining_kva 60.0, margin 0.641667
  (64.2%), verdict PASS.
- load_fraction(45.75, 120): 0.38125 (38.1%) of the 120 kVA installed.
- ela_summary: continuous 45.75 kVA, coincident peak 38.8875 kVA,
  essential 21.5 kVA, remaining 60.0 kVA, margin 0.641667 PASS, load
  fraction 0.38125, installed 120.0 kVA.

## Verification

- continuous_load with one 10 kVA consumer at duty 1.0 returns 10 kVA and
  at duty 0.5 returns 5 kVA; doubling the power doubles the contribution.
- diversity_peak(45.75, 1.0) returns 45.75 exactly (identity) and factor
  0.5 returns 22.875.
- essential_load of all eight consumers returns 92.5 kVA (full powers
  only); one flight-control consumer (12 kVA at duty 0.6) books 12.0 kVA
  full, not 7.2 duty weighted.
- generator_out_margin identity: essential exactly at the (n - 1)
  generator capacity gives margin 0.0 and verdict PASS; essential 80 with
  two 60 kVA generators gives margin -1/3 and verdict FAIL; a single
  generator gives remaining 0.0, margin -1.0, verdict FAIL.
- load_fraction(45.75, 120) = 0.38125; doubling the installed capacity
  halves the fraction.
- ValueError rejection of non-physical inputs: empty consumer dict; duty
  outside [0, 1] (1.2 or -0.1); power -5; diversity 0 or 1.5; essential
  name not in the dict; n_generators 0; generator_kva 0; installed_kva
  <= 0.
- Determinism: identical inputs give identical outputs (no RNG anywhere).
- Run the contract test offline: python3
  scripts/test_aircraft_electrical_load_analysis.py (35 tests).

## Related leaves

- vehicle-design/sizing/battery-sizing: traction and ESS energy storage
  sizing; it consumes a load requirement but does not roll up the AC/DC
  generator and bus load.
- vehicle-design/sizing/engine-sizing: shaft thrust and power sizing, the
  mechanical side of the same aircraft.
- vehicle-design/sizing/hydraulic-system-sizing: hydraulic consumers
  whose pump drives draw on this electrical budget.
- avionics/do160/power-input: supply power quality acceptance testing,
  separate from the load rollup.
- space-systems/subsystems/power-thermal-budget: the spacecraft EPS
  counterpart in the foreign family; do not mix the two contexts.

## Contract test

Run the deterministic contract test (stdlib unittest, offline):

    python3 scripts/test_aircraft_electrical_load_analysis.py

It covers the worked example (continuous load 45.75 kVA, coincident peak
38.8875 kVA, essential load 21.5 kVA, generator-out margin 0.6417 with
verdict PASS, load fraction 0.38125), the diversity-1.0 and zero-margin
identities, rollup ordering, full-power essential booking, summary dict
keys, determinism, and ValueError rejection of every non-physical input.

## Compliance

- Standards referenced, not reproduced: FAR 25.1355 (electrical system
  no-hazard context) is named and paraphrased only; the load rollup
  relations above are standard engineering methodology, summary-only per
  standards-map.yaml.
- compliance: STANDARDS-REF, gated: false.
