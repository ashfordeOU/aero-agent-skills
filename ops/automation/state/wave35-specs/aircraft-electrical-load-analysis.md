# Wave-35 leaf spec: aircraft-electrical-load-analysis (vehicle-design, sizing pack)

- Path: skills/vehicle-design/sizing/aircraft-electrical-load-analysis/
- Pack: sizing. Closest siblings: battery-sizing (traction/ESS
  energy storage sizing for electric aircraft, depth of discharge,
  C-rate, pack voltage; CONSUMES a load requirement but does not
  build the AC/DC generator and bus load rollup), engine-sizing
  (shaft thrust sizing), hydraulic-system-sizing (a consumer of
  electrical power), space-systems power-thermal-budget (spacecraft
  EPS, solar arrays, foreign family). Repo-wide grep proves ZERO
  owners for electrical load rollup, generator rating check, duty
  cycle loading, essential load margin in the aircraft context; the
  only kVA/bus-load hits are spacecraft solar-array sizing.
- Standards id: far-25 (reference-only; 25.1355 electrical system
  no-hazard context). Ledger Standard: far-25.
- Family: vehicle-design

## Claim

Analyze the aircraft electrical power system load at the sizing
level: roll up the consumer apparent power (kVA) with each consumer
duty cycle into the continuous load, apply the diversity factor to
the continuous load for the coincident peak, total the essential
load from the named essential consumers at their full steady power,
check the generator rating against the single-generator-out case
where the remaining capacity must cover the essential load, and
report the normal load fraction against the installed capacity.
Produces the continuous load, the coincident peak, the essential
load, the generator-out margin and verdict, and the load fraction
that gate the generator sizing (FAR 25.1355 context: no essential
load may be lost when any one power source fails).

Does NOT do: traction battery/ESS sizing, mission energy (battery-
sizing); DO-160 power-input QUALITY testing (avionics/do160/power-
input owns supply voltage transient, frequency, interruption tests);
generator electrical machine design; fault current and protection
coordination; spacecraft EPS (space-systems).

## Model (implement exactly)

Module constants: none required (pure rollup arithmetic).

Conventions: consumers are given as a dict {name: (power_kva,
duty)} with duty in [0, 1] (fraction of flight time the consumer
draws its rated power). The continuous load sums the duty-weighted
powers. The essential load totals the FULL rated power of the named
essential consumers (they must be powered continuously in the
failure case; conservative full-power bookkeeping).

Functions (pure stdlib):
- continuous_load(consumers) -> dict {continuous_kva, rollup} where
  rollup is the list of per-consumer duty-weighted values in the
  given order. ValueErrors: empty dict; any duty outside [0, 1];
  any power < 0.
- diversity_peak(continuous_kva, diversity_factor) ->
  diversity * continuous_kva. ValueError: continuous < 0;
  diversity outside (0, 1].
- essential_load(consumers, essential_names) -> dict
  {essential_kva, essential_consumers} summing FULL powers of the
  named consumers. ValueErrors: empty consumers; name not in
  consumers.
- generator_out_margin(n_generators, generator_kva,
  essential_kva) -> dict {remaining_kva, margin, verdict} where
  remaining = (n - 1) * generator_kva, margin = (remaining -
  essential) / remaining, verdict PASS when margin >= 0 else FAIL.
  ValueErrors: n < 1, generator_kva <= 0, essential < 0. For n == 1
  remaining = 0.0 and margin = -1.0 with verdict FAIL (no
  redundancy).
- load_fraction(continuous_kva, installed_kva) ->
  continuous / installed. ValueErrors: installed <= 0.
- ela_summary(consumers, diversity_factor, essential_names,
  n_generators, generator_kva) -> dict with all keys above plus
  installed_kva.

Identity to test: with diversity 1.0 the coincident peak equals the
continuous load; with n generators and essential exactly at the
(n-1) generator capacity the margin is exactly 0.

## Worked example

Reference system: eight consumers (kVA, duty): avionics 4.0 / 1.0,
flight-control 12.0 / 0.6, comm-nav 2.5 / 1.0, lighting 6.0 / 0.5,
galley 35.0 / 0.35, anti-ice 18.0 / 0.25, hydraulic-pumps 12.0 /
0.8, fuel-boost 3.0 / 0.9. Diversity 0.85. Essential names:
avionics, flight-control, comm-nav, fuel-boost. Two 60 kVA
generators.

Run your module and take the real outputs as assert targets, then
check the magnitude bounds (independently verified at prep):
- continuous_load: 4.0 + 7.2 + 2.5 + 3.0 + 12.25 + 4.5 + 9.6 + 2.7
  = 45.75 kVA.
- diversity_peak(45.75, 0.85) = 38.8875 kVA (38.89).
- essential_load = 4.0 + 12.0 + 2.5 + 3.0 = 21.5 kVA.
- generator_out_margin(2, 60, 21.5): remaining 60 kVA; margin
  (60 - 21.5) / 60 = 0.641667 (64.2%); verdict PASS.
- load_fraction(45.75, 120) = 0.38125 (38.1%).

If a value falls outside its bound, your implementation has a bug:
find it before writing tests. In the SKILL.md worked example show
your module's real outputs (do not invent them).

## Validation list (contract test must include)

- ValueError: empty consumer dict; duty 1.2 or -0.1; power -5;
  diversity 0 or 1.5; essential name not in dict; n_generators 0;
  generator_kva 0.
- Continuous rollup: single consumer 10 kVA at duty 1.0 -> 10; at
  duty 0.5 -> 5; doubling power doubles its contribution.
- Diversity: factor 1.0 returns the continuous load exactly;
  factor 0.5 halves it.
- Essential: all eight named essential -> 4+12+2.5+3+6+35+18+12+3
  wait -> sum full powers of the named subset only; full set sum =
  92.5 kVA (all consumers full); one named essential at full power.
- Generator-out: worked case margin 0.6417 within 1e-9; essential
  equal to 60 -> margin 0 PASS; essential 80 with two 60 kVA gens
  -> margin -0.333 FAIL; single generator -> remaining 0, margin
  -1.0, FAIL.
- Load fraction: 45.75 / 120 = 0.38125; doubling installed halves
  the fraction.
- Determinism: identical inputs -> identical outputs.
- Convenience dict keys exactly as documented.

## Corpus fragment (eval/hit1-wave35-aircraft-electrical-load-analysis.yaml)

Query 1 (copy verbatim):
  "roll up the aircraft electrical load with duty cycles and check the generator rating for the continuous and coincident peak load"
  intent: "vehicle-design; electrical load rollup with duty cycle and generator rating check"
  expected_skill: "vehicle-design/sizing/aircraft-electrical-load-analysis"
Query 2 (copy verbatim):
  "compute the single generator out margin that the remaining generator capacity covers the essential electrical load"
  intent: "vehicle-design; essential load margin with one generator failed"
  expected_skill: "vehicle-design/sizing/aircraft-electrical-load-analysis"
Task ids: w35-aircraft-electrical-load-analysis-1 and -2.

## Description/tag guidance (gate 1/2 and tag-steal rules)

Description must open "Use when you must analyze the aircraft
electrical power system load:" and include the outputs in the Claim.
First tag: aircraft-electrical-load-analysis. Additional tags ONLY:
electrical-load-rollup, generator-rating-check, duty-cycle-loading,
essential-load-margin. NEVER single generic words (electrical, load,
generator, duty, power, bus, analysis). 50-150 words, <=1000 chars,
no em dash, no "classified", action verb present.

FORBIDDEN TOKENS (belong to siblings): battery pack energy, depth
of discharge, C-rate, pack voltage, series parallel cell count
(battery-sizing); voltage transient, frequency variation, power
interruption, DO-160 power input tests (avionics/do160/power-input);
solar array, spacecraft bus, eclipse (space-systems); actuator flow
(hydraulic-system-sizing).
