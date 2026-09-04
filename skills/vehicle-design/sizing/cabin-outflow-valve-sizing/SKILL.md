---
name: cabin-outflow-valve-sizing
description: "Use when you must size the cabin outflow valve: compute the choked-flow mass flux G = p sqrt(gamma/(R T)) (2/(gamma+1))^((gamma+1)/(2(gamma-1))) at the cruise cabin condition, divide the governing pack inflow by that flux for the outflow valve effective area, and size the pressure-relief valve effective area to dump the same pack flow at the 8.9 psi differential pressure clamp ceiling. Produces the choked-flow mass flux, the effective area and equivalent diameter for the outflow and relief cases, and a fit verdict against the nominal valve diameter limit. Trigger: cabin outflow valve sizing, outflow valve area, pressure relief valve sizing, cabin choked flow, pressurization valve, differential pressure clamp."
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
  tags: [cabin-outflow-valve-sizing, outflow-valve-area, pressure-relief-valve-sizing, cabin-choked-flow, pressurization-valve, differential-pressure-clamp]
  version: 0.1.0
  author: AeroSkills
---

# Cabin Outflow Valve Sizing (vehicle-design/sizing/cabin-outflow-valve-sizing)

Use when the task is sizing the cabin outflow and pressure-relief valve
effective area of a pressurized transport at the conceptual level: the
valve must pass the governing pack inflow through a choked orifice at the
cabin pressure, so the effective area follows from the choked-flow
mass-flux relation G = p sqrt(gamma/(R T)) (2/(gamma+1))^((gamma+1)/
(2(gamma-1))) as A = m_dot / G. This leaf implements the choked-flow
valve sizing step in pure Python, stdlib only. It consumes the pack mass
flow and cruise cabin pressure from vehicle-design/sizing/environmental-
control-sizing, which owns the pressurization schedule; this leaf covers
only the valve discharge sizing step for the outflow and relief cases.

## Domain quick reference

- Choked-flow mass flux: G = p * sqrt(gamma/(R T)) * (2/(gamma+1))^
  ((gamma+1)/(2(gamma-1))), with gamma 1.4, R 287.0 J/(kg K). The
  flux factor (2/(gamma+1))^((gamma+1)/(2(gamma-1))) equals 0.578704
  for air, so G = 0.578704 * p * sqrt(gamma/(R T)).
- Critical pressure ratio: (2/(gamma+1))^(gamma/(gamma-1)) = 0.528282.
  The flow chokes only while p_amb/p_cab stays below this threshold; at
  the threshold itself the flow is not choked (strict). The rounded
  0.528 lies just below the exact threshold, so a cabin ratio of 0.528
  is still choked; the module applies the strict comparison against the
  exact constant.
- Effective area and diameter: A = m_dot / G, D = sqrt(4*A/pi). The
  area is an effective flow area, not a geometric orifice area.
- Outflow valve at cruise: sized with p_cab at the cruise cabin pressure
  (75262 Pa for the 8000 ft cabin at 39,000 ft) and the cruise pack
  inflow m_pack from the ECS sizing as the governing flow.
- Pressure-relief valve at the clamp: upstream pressure p_cab = p_amb +
  dp_clamp (11597 + 61363 = 72960 Pa at 50,000 ft with the 8.9 psi
  clamp); the same pack flow then needs a larger effective area because
  the relief upstream pressure is lower than the cruise cabin pressure.
- Fit verdict: PASS when the equivalent diameter stays at or below the
  nominal valve diameter limit, FAIL otherwise.
- Units are SI throughout: Pa, K, kg/s, m2, m.
- FAR 25.841 frames the cabin pressurization context; the relations
  above are standard engineering methodology, summary-only.

## Workflow

1. Take the governing inputs from the ECS sizing leaf: pack mass flow
   m_pack, cruise cabin pressure p_cab, and the ISA ambient pressure at
   the sizing altitude (19677 Pa at 39,000 ft).
2. Confirm the cruise flow is choked with is_choked (pressure ratio
   19677/75262 = 0.2614 is well below the 0.528 threshold); the sizing
   functions raise ValueError on an unchoked condition.
3. Compute the cruise mass flux with choked_mass_flux at the cabin
   temperature (default 288 K).
4. Size the outflow valve: outflow_valve_sizing(m_pack, p_cab, p_amb,
   max_valve_diameter_m) returns the choked flag, mass flux, effective
   area, equivalent diameter and the PASS/FAIL fit verdict against the
   nominal diameter limit.
5. For the pressure-relief case, take the ISA ambient at the relief
   altitude (11597 Pa at 50,000 ft) and the differential pressure clamp
   (default 61363 Pa, 8.9 psi).
6. Size the relief valve: relief_valve_sizing(m_pack, p_amb,
   dp_clamp_pa, max_valve_diameter_m) with upstream pressure
   p_amb + dp_clamp and its own choked check at the clamp ceiling.
7. Compare both diameters with the nominal valve diameter limit and
   report the fit verdicts with the effective areas.
8. Confirm the deterministic checks with the contract test
   scripts/test_cabin_outflow_valve_sizing.py.

## Worked example

Reference installation: cruise at 39,000 ft with p_cab = 75262 Pa
(8000 ft cabin), pack inflow 3.156617 kg/s; relief case at 50,000 ft
with the 8.9 psi (61363 Pa) differential clamp; nominal valve diameter
limit 0.16 m.

- Cruise pressure ratio: 19677/75262 = 0.2614, below 0.528, so the
  outflow is choked.
- Cruise mass flux: choked_mass_flux(75262) = 179.2499 kg/(m2 s).
- Outflow valve: outflow_valve_sizing(3.156617, 75262, 19677, 0.16)
  gives area 0.017610 m2, diameter 0.14974 m (149.7 mm), fit verdict
  PASS against the 0.16 m limit.
- Relief upstream pressure: 11597 + 61363 = 72960 Pa; ratio 11597/72960
  = 0.1590, choked.
- Relief mass flux: 173.7672 kg/(m2 s); relief_valve_sizing(3.156617,
  11597, 61363, 0.16) gives area 0.018166 m2, diameter 0.15208 m
  (152.1 mm), fit verdict PASS.
- The relief valve is 3.2% larger in effective area than the outflow
  valve because its upstream pressure at the clamp ceiling is lower.

## Verification

- Confirm choked_mass_flux(75262) returns 179.2499 kg/(m2 s) and that
  G/(p*sqrt(gamma/(R T))) equals the closed-form flux factor 0.578704
  within 1e-6.
- Confirm outflow_valve_sizing(3.156617, 75262, 19677, 0.16) returns
  area 0.017610 m2 within 1e-5 and diameter 0.1497 m within 1e-3, with
  fit verdict PASS; against a 0.14 m limit the verdict is FAIL.
- Confirm relief_valve_sizing(3.156617, 11597, 61363, 0.16) returns
  area 0.018166 m2 within 1e-5 and diameter 0.1521 m within 1e-3.
- Confirm the is_choked truth table: ratio 0.2614 -> True; 0.7 -> False;
  at the critical ratio itself -> False (strict threshold).
- Confirm the area round trip: pi*(D/2)^2 recovers the effective area.
- Confirm ValueError rejection of non-positive mass flow, pressure,
  temperature, differential clamp and diameter limit, and of unchoked
  outflow and relief conditions (e.g. pressure ratio 0.7).
- Run the contract test offline: python3
  scripts/test_cabin_outflow_valve_sizing.py (34 tests, deterministic).

## Related leaves

- vehicle-design/sizing/environmental-control-sizing: computes the
  governing pack inflow m_pack, the cabin pressure at cruise and the
  pressurization schedule that are the inputs to this sizing step.
- vehicle-design/sizing/avionics-bay-cooling-sizing: equipment cooling
  flow sizing, a separate ECS discipline that does not touch the cabin
  outflow path.
- vehicle-design/sizing/aircraft-oxygen-system-sizing: the emergency
  oxygen side of cabin altitude protection, complementary to the
  pressure-relief path.

## Pitfalls

- Sizing the outflow valve from the pressurization schedule alone: the
  valve area follows from the choked-flow relation at the cruise cabin
  pressure, A = m_dot / G; the schedule regimes belong to the ECS
  sizing leaf and only set the operating point used here.
- Applying the relation when the flow is not choked: the mass-flux
  formula is valid only below the critical pressure ratio 0.528; an
  unchoked case (ratio 0.7) must raise, not silently return an area.
- Mixing the cruise and relief upstream pressures: the outflow valve
  sees the cruise cabin pressure 75262 Pa, while the relief valve sees
  the clamp ceiling p_amb + dp_clamp = 72960 Pa at 50,000 ft, a lower
  upstream pressure that yields a 3.2% larger effective area for the
  same pack flow.
- Treating the pack inflow as a valve output: m_pack is the governing
  flow computed by the ECS sizing leaf from the occupant and thermal
  requirements; this leaf only sizes the discharge path for it.
- Reporting effective area as geometric orifice area: A = m_dot / G is
  an effective flow area; a real valve adds discharge coefficient and
  trim effects that belong to a later detailed design step.
- Using sea-level ambient pressure: the cruise anchor is 19677 Pa at
  39,000 ft and the relief anchor 11597 Pa at 50,000 ft; ambient at the
  wrong altitude shifts the choked ratio and the area.

## Behavior contract (gate 3)

Run the deterministic contract test (stdlib unittest, offline):

    python3 scripts/test_cabin_outflow_valve_sizing.py

The test covers the choked-flow mass flux at the cruise and relief
worked conditions (179.2499 and 173.7672 kg/(m2 s)), the closed-form
flux identity G/(p*sqrt(gamma/(R T))) = 0.578704 within 1e-6, the
is_choked truth table with the strict critical-ratio threshold, the
outflow valve effective area 0.017610 m2 within 1e-5 and diameter
0.1497 m within 1e-3 with PASS/FAIL fit verdicts against 0.16 m and
0.14 m limits, the relief valve area 0.018166 m2 within 1e-5 and
diameter 0.1521 m within 1e-3, the area round trip through the
equivalent diameter, the relief upstream pressure as p_amb plus the
clamp, determinism, exact dict keys, and ValueError rejection of every
non-physical input and of unchoked outflow and relief conditions.

## Compliance

- Standards referenced, not reproduced: FAR 25.841 is the
  pressurization cabin context (cabin pressure altitude limits and the
  differential pressure clamp); the choked-flow relations above are
  standard engineering methodology, summary-only per standards-map.yaml.
- compliance: STANDARDS-REF, gated: false.
