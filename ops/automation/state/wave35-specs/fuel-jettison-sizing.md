# Wave-35 leaf spec: fuel-jettison-sizing (vehicle-design, sizing pack)

- Path: skills/vehicle-design/sizing/fuel-jettison-sizing/
- Pack: sizing. Closest siblings: fuel-tank-sizing (volume, ullage,
  tank capacity fit), fuel-feed-system-sizing (wave-35: feed line
  and boost pump delivery), sizing-mission-profile (block/reserve
  fuel), engine-sizing (fuel flow demand). Whole-tree grep proves
  ZERO owners for fuel jettison, fuel dump, 25.1001; no leaf cites
  the 15-minute landing-weight rule.
- Standards id: far-25 (reference-only; 25.1001 fuel jettison
  context). Ledger Standard: far-25.
- Family: vehicle-design

## Claim

Size the fuel jettison system for FAR 25.1001 compliance at the
conceptual level: from the maximum takeoff weight and the maximum
landing weight, compute the fuel mass that must be dumpable and the
required average jettison rate to reach the landing weight within
the 15-minute (900 s) limit, apply the design margin to the required
rate, split the design flow over the dump mast count, and verify the
resulting time to landing weight against the 900 s limit. Produces
the dumpable fuel mass, the required and design jettison rates, the
per-mast flow, and the time-to-landing-weight verdict that gate the
jettison system sizing.

Does NOT do: tank volume and ullage (fuel-tank-sizing); feed line
and boost pump sizing (fuel-feed-system-sizing); block and reserve
fuel computation (sizing-mission-profile); dump mast aerodynamic
detail; jettison operating procedure and dispatch rules.

## Model (implement exactly)

Module constants:
- JETTISON_LIMIT_S = 900.0 (15-minute rule).
- DESIGN_MARGIN_DEFAULT = 1.1 (10 percent design margin on the
  required average rate).

Conventions: masses in kg, rates in kg/s, times in s. The required
average rate assumes the full excess fuel (MTOW - MLW) is dumped
evenly over the limit.

Functions (pure stdlib):
- dumpable_fuel_mass(mtow_kg, mlw_kg) -> mtow - mlw. ValueErrors:
  mtow <= 0, mlw <= 0, mlw > mtow.
- required_jettison_rate(mtow_kg, mlw_kg, limit_s =
  JETTISON_LIMIT_S) -> (mtow - mlw) / limit_s. ValueErrors as above;
  limit_s <= 0.
- design_jettison_rate(required_rate_kg_s, margin =
  DESIGN_MARGIN_DEFAULT) -> required * margin. ValueErrors:
  required <= 0, margin < 1.
- per_mast_flow(design_rate_kg_s, n_masts) -> design_rate /
  n_masts. ValueErrors: n_masts < 1, rate <= 0.
- time_to_landing_weight(dumpable_mass_kg, design_rate_kg_s) ->
  dict {time_s, verdict} where verdict PASS when time <= 900 s else
  FAIL. ValueErrors: dumpable < 0, design_rate <= 0.
- jettison_summary(mtow_kg, mlw_kg, n_masts, margin =
  DESIGN_MARGIN_DEFAULT) -> dict with all keys above plus the
  design-time re-check.

Identity to test: the design time equals dumpable mass divided by
the design rate, and equals 900 / margin when the design rate is
exactly the required rate scaled by the margin.

## Worked example

Reference transport: MTOW 79,000 kg, MLW 66,500 kg, two dump masts,
10 percent design margin.

Run your module and take the real outputs as assert targets, then
check the magnitude bounds (independently verified at prep):
- dumpable_fuel_mass: 79000 - 66500 = 12500 kg.
- required_jettison_rate: 12500 / 900 = 13.889 kg/s.
- design_jettison_rate: 13.889 * 1.1 = 15.278 kg/s.
- per_mast_flow: 15.278 / 2 = 7.639 kg/s per mast.
- time_to_landing_weight: 12500 / 15.278 = 818 s <= 900 -> PASS.

If a value falls outside its bound, your implementation has a bug:
find it before writing tests. In the SKILL.md worked example show
your module's real outputs (do not invent them).

## Validation list (contract test must include)

- ValueError: mtow <= 0; mlw <= 0; mlw > mtow; limit_s <= 0;
  margin < 1; n_masts < 1; negative dumpable; rate <= 0.
- Rate identity: required rate == (MTOW - MLW)/900 exactly; margin
  1.0 leaves the rate unchanged; margin 1.2 scales it by 1.2.
- Time: worked case 818 s within 1 s; with margin 1.0 the time is
  exactly 900 s (verdict PASS at the boundary); an undersized
  design (margin 0.9 is rejected; use margin 1.0 with a 950 s
  requirement instead) FAILs when time > limit.
- Mast split: two masts halve the per-mast flow; single mast equals
  the design rate.
- Determinism: identical inputs -> identical outputs.
- Convenience dict keys exactly as documented.

## Corpus fragment (eval/hit1-wave35-fuel-jettison-sizing.yaml)

Query 1 (copy verbatim):
  "compute the required fuel jettison rate to reach the maximum landing weight within 15 minutes per FAR 25.1001"
  intent: "vehicle-design; fuel jettison rate to landing weight within 15 minutes"
  expected_skill: "vehicle-design/sizing/fuel-jettison-sizing"
Query 2 (copy verbatim):
  "size the fuel dump mast flow split and verify the time to landing weight for the aircraft jettison system"
  intent: "vehicle-design; fuel dump mast flow and jettison time check"
  expected_skill: "vehicle-design/sizing/fuel-jettison-sizing"
Task ids: w35-fuel-jettison-sizing-1 and -2.

## Description/tag guidance (gate 1/2 and tag-steal rules)

Description must open "Use when you must size the fuel jettison
system:" and include the outputs in the Claim. First tag:
fuel-jettison-sizing. Additional tags ONLY: fuel-dump-rate,
jettison-time-to-landing-weight, fuel-jettison-mast. NEVER single
generic words (jettison, dump, fuel, rate, mast, landing). 50-150
words, <=1000 chars, no em dash, no "classified", action verb
present.

FORBIDDEN TOKENS (belong to siblings): ullage, usable fuel, tank
capacity, tank volume (fuel-tank-sizing); boost pump, feed line,
npsh, pressure loss (fuel-feed-system-sizing); block fuel, reserve
fuel, payload range (sizing-mission-profile).
