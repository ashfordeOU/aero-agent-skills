---
name: fuel-jettison-sizing
description: "Use when you must size the fuel jettison system: from the maximum takeoff weight and the maximum landing weight, compute the fuel mass that must be dumpable and the required average jettison rate to reach the landing weight within the 15-minute limit of FAR 25.1001, apply the design margin to the required rate, split the design flow over the dump mast count, and verify the resulting time to landing weight against the 900 s limit. Produces the dumpable fuel mass, the required and design jettison rates, the per-mast flow, and the time-to-landing-weight PASS or FAIL verdict that gate the jettison system sizing. Trigger: fuel jettison sizing, fuel dump rate, jettison time to landing weight, dump mast flow split, FAR 25.1001, 15-minute landing weight rule."
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
  tags: [fuel-jettison-sizing, fuel-dump-rate, jettison-time-to-landing-weight, fuel-jettison-mast]
  version: 0.1.0
  author: AeroSkills
---

# Fuel Jettison Sizing (vehicle-design/sizing/fuel-jettison-sizing)

Use when the task is sizing the fuel jettison system at the conceptual
level so the aircraft can reach its maximum landing weight within the
15-minute limit after takeoff at maximum takeoff weight, the FAR 25.1001
context. From MTOW and MLW this leaf computes the fuel mass that must be
dumpable, the required average jettison rate over the 900 s limit, the
design rate with margin, the per-mast flow over the dump mast count, and
the time-to-landing-weight verdict. It implements the standard method in
pure Python, stdlib only, deterministic and offline. It pairs with
vehicle-design/sizing/fuel-tank-sizing for the storage context and
vehicle-design/sizing/engine-sizing for the fuel flow demand side.

## Domain quick reference

- Dumpable fuel mass: m_dump = MTOW - MLW. This is the excess weight
  that must be jettisoned so the aircraft can land at or below the
  maximum landing weight.
- Required average jettison rate: q_req = (MTOW - MLW) / t_limit, with
  t_limit = 900 s (the 15-minute limit). The full excess fuel is dumped
  evenly over the limit.
- Design jettison rate: q_design = q_req * margin, margin >= 1 (default
  1.1, a 10 percent design margin). Margins below 1 are undersized and
  rejected.
- Per-mast flow: q_mast = q_design / n_masts, n_masts >= 1. The design
  flow is split evenly over the dump masts.
- Time to landing weight: t_dump = m_dump / q_design. The verdict is
  PASS when t_dump <= 900 s and FAIL otherwise.
- Identity checks: t_dump = m_dump / q_design exactly, and when
  q_design = q_req * margin then t_dump = 900 / margin exactly (margin
  1.0 gives exactly 900 s, PASS at the boundary).
- Units are SI throughout: kg, kg/s, s.
- FAR 25.1001 frames the fuel jettison requirement context; the
  relations above are standard engineering methodology, summary-only.

## Workflow

1. Fix the weights: maximum takeoff weight mtow_kg and maximum landing
   weight mlw_kg (aircraft certification data, kg).
2. Compute the dumpable fuel mass with dumpable_fuel_mass: the excess
   MTOW - MLW that the jettison system must be able to remove.
3. Compute the required average rate with required_jettison_rate over
   the 900 s limit (default JETTISON_LIMIT_S), or over a different
   limit_s when the requirement differs.
4. Apply the design margin with design_jettison_rate (default
   DESIGN_MARGIN_DEFAULT = 1.1); any margin below 1 raises ValueError.
5. Split the design flow over the dump masts with per_mast_flow using
   the mast count from the jettison system architecture.
6. Re-check the design with time_to_landing_weight and confirm the
   verdict: PASS requires the design time within the 900 s limit.
7. For the full sizing picture call jettison_summary once and read the
   dumpable mass, required and design rates, per-mast flow, time and
   verdict from one dict.
8. Confirm the deterministic checks with the contract test
   scripts/test_fuel_jettison_sizing.py.

## Worked example

Reference transport: MTOW 79,000 kg, MLW 66,500 kg, two dump masts, 10
percent design margin (default 1.1).

- Dumpable fuel mass: dumpable_fuel_mass(79000, 66500) = 12,500 kg.
- Required average rate: required_jettison_rate(79000, 66500) =
  13.8889 kg/s (12500 / 900).
- Design rate: design_jettison_rate(13.8889) = 15.2778 kg/s
  (13.8889 * 1.1).
- Per-mast flow: per_mast_flow(15.2778, 2) = 7.6389 kg/s per mast.
- Time to landing weight: time_to_landing_weight(12500, 15.2778) gives
  time_s 818.18 s and verdict PASS (818.18 <= 900).
- Summary: jettison_summary(79000, 66500, 2) returns dumpable_mass_kg
  12500.0, required_rate_kg_s 13.8889, design_rate_kg_s 15.2778,
  per_mast_flow_kg_s 7.6389, limit_s 900.0, time_s 818.18, verdict
  PASS.
- Identity: 818.18 s equals 12500 / 15.2778 and equals 900 / 1.1.

## Verification

- Confirm dumpable_fuel_mass(79000, 66500) returns 12500.0 kg.
- Confirm required_jettison_rate(79000, 66500) returns exactly
  (79000 - 66500) / 900 = 13.8889 kg/s.
- Confirm design_jettison_rate with margin 1.0 leaves the rate
  unchanged and margin 1.2 scales it by exactly 1.2.
- Confirm time_to_landing_weight at margin 1.0 returns exactly 900 s
  with verdict PASS at the boundary, and that an undersized design
  (margin 0.9 is rejected; a 950 s requirement at margin 1.0 instead)
  returns a time above 900 s with verdict FAIL.
- Confirm two masts halve the per-mast flow and a single mast carries
  the full design rate.
- Confirm identical inputs produce identical outputs (deterministic).
- Confirm every non-physical input raises ValueError: mtow <= 0, mlw
  <= 0, mlw > mtow, limit_s <= 0, margin < 1, n_masts < 1, negative
  dumpable mass, design rate <= 0.
- Run the contract test offline: python3
  scripts/test_fuel_jettison_sizing.py (35 tests, deterministic).

## Related leaves

- vehicle-design/sizing/fuel-tank-sizing: the storage side of the fuel
  system that the jettison system draws from.
- vehicle-design/sizing/fuel-feed-system-sizing: the delivery side of
  the fuel system that supplies the engines.
- vehicle-design/sizing/engine-sizing: the fuel flow demand side that
  sets the overall system flow scale.

## Contract test

Run the deterministic contract test (stdlib unittest, offline):

    python3 scripts/test_fuel_jettison_sizing.py

The test covers the worked example sizing contract (12,500 kg dumpable,
13.8889 kg/s required, 15.2778 kg/s design, 7.6389 kg/s per mast,
818.18 s PASS), the exact rate identity (MTOW - MLW) / 900, margin
scaling at 1.0 and 1.2, the PASS boundary at exactly 900 s and the FAIL
verdict above it, mast split behavior, summary dict keys and re-check,
determinism, and ValueError rejection of every non-physical input.

## Compliance

- Standards referenced, not reproduced: FAR 25.1001 (fuel jettison
  context) is named as the requirement frame; the sizing relations
  above are standard engineering methodology, summary-only per
  standards-map.yaml.
- compliance: STANDARDS-REF, gated: false.
