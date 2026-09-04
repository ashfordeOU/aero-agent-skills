---
name: subsonic-inlet-recovery
description: "Use when you must compute subsonic inlet total pressure recovery at a flight condition: the ram recovery ratio from free-stream Mach (unity below Mach 1, MIL-E-5008B style roll-off above), the isentropic stagnation pressure ratio, the engine face total pressure after the duct total-pressure efficiency, the capture area for the engine mass flow at flight speed and density, and the capture verdict against the intake highlight, spillage when the required capture exceeds the highlight. Produces ram recovery, face total pressure, capture area and the full-capture or spillage verdict for the cycle deck inlet. Trigger: subsonic intake recovery, ram recovery ratio, engine face total pressure, intake capture area, duct total pressure efficiency."
license: Apache-2.0
compliance: STANDARDS-REF
standards:
  - id: far-33
    reference-only: true
gated: false
domain: propulsion
pack: gas-turbine-cycle
compatibility: "agentskills.io SKILL.md; any SKILL.md host (Claude Code, Hermes, OpenClaw)"
metadata:
  domain: propulsion
  subdomain: gas-turbine-cycle
  tags: [subsonic-inlet-recovery, ram-recovery-ratio, engine-face-total-pressure, intake-capture-area, spillage-verdict, duct-total-pressure-efficiency]
  version: 0.1.0
  author: AeroSkills
---

# Subsonic Inlet Recovery (propulsion/gas-turbine-cycle/subsonic-inlet-recovery)

Use when you must compute the total-pressure recovery and the
compressor-face condition for a subsonic turbofan or turboprop intake
at a flight condition: the ram recovery ratio from the free-stream
Mach number, the free-stream stagnation pressure ratio from the
isentropic relation, the total pressure delivered at the engine face
after the duct total-pressure efficiency, the required capture area
for the engine mass flow at the flight speed and density, and the
capture verdict against the intake highlight area. This leaf
implements the standard subsonic intake model in pure Python, stdlib
only. It pairs with propulsion/gas-turbine-cycle/gas-turbine-cycle and
propulsion/turbofan/turbofan-cycle, whose cycle decks take the face
total pressure this leaf produces as an input at the fan face station;
the shock-dominated intake regimes of the ramjet
family belong to propulsion/ramjet/ramjet-inlet, and the exhaust side
is handled by propulsion/gas-turbine-cycle/propelling-nozzle.

## Domain quick reference

- Ram recovery ratio: the fraction of the free-stream total pressure
  that survives the intake at the engine face, before the duct loss.
  It is unity at and below Mach 1, and rolls off above Mach 1 with a
  MIL-E-5008B style curve, rr = 1 - 0.075 * (M - 1)^1.35 for
  1 < M < 5. Beyond Mach 5 the subsonic model no longer applies.
- Free-stream stagnation pressure ratio: p0_ratio = (1 + 0.2 * M^2)^3.5
  from the isentropic relation at gamma = 1.4 (standard atmosphere
  still air total-to-static ratio at the flight Mach).
- Engine face total pressure: pt_face = p0 * p0_ratio * rr *
  duct_efficiency. The duct total-pressure efficiency carries all duct
  losses between the intake highlight and the fan face, so at subsonic
  Mach with a perfect duct the face total pressure is simply
  p0 * p0_ratio, the free-stream stagnation value.
- Capture area: the streamtube area that passes the engine mass flow at
  the free-stream condition, A_cap = m_dot / (rho * V), with the
  free-stream density rho = p0 / (R * T0) and speed
  V = M * sqrt(gamma * R * T0), R = 287.0 J/(kg K), gamma = 1.4.
- Capture verdict: full-capture when A_cap <= A_highlight, the capture
  streamtube fits inside the intake highlight area; spillage when
  A_cap > A_highlight, the intake spills the excess flow around the
  lip and the engine is starved of its demanded streamtube.
- Units are SI throughout: Pa, K, kg/s, m2, m/s, Mach dimensionless.
- FAR Part 25 frames the installation context (the intake is part of
  the engine installation); the relations above are standard
  engineering methodology, summary-only.

## Workflow

1. Fix the flight condition: free-stream static pressure p0, static
   temperature T0 and Mach number M (free-stream values, not total).
2. Get the ram recovery ratio with ram_recovery(M): unity at subsonic
   Mach, rolled off above Mach 1 by the MIL-E-5008B style curve.
3. Promote the free stream to stagnation with
   stagnation_pressure_ratio(M).
4. Apply the duct total-pressure efficiency and form the engine face
   total pressure with face_total_pressure(p0, M, duct_efficiency);
   this value is the inlet station input for the cycle deck.
5. Size the intake for the engine mass flow with
   capture_area(mass_flow, p0, T0, M), which builds the free-stream
   density and speed and divides the mass flow by their product.
6. Judge the intake against its highlight area with
   capture_verdict(capture_area, highlight_area): full-capture or
   spillage.
7. Confirm the deterministic checks with the contract test
   scripts/test_subsonic-inlet-recovery.py.

## Worked example

Flight condition (11 km standard day): Mach 0.82, p0 = 101325 Pa,
T0 = 216.65 K, duct_efficiency 0.98, engine mass flow 200 kg/s.

- Ram recovery: ram_recovery(0.82) = 1.0, full recovery at subsonic
  Mach. At Mach 1.5 the roll-off gives ram_recovery(1.5) =
  0.9705781, and ram_recovery(2.0) = 0.925 exactly.
- Stagnation ratio: stagnation_pressure_ratio(0.82) = 1.5552097, so
  the free-stream stagnation pressure is 101325 * 1.5552097 =
  157581.5 Pa.
- Face total pressure: face_total_pressure(101325, 0.82, 0.98) =
  154429.99 Pa, the stagnation pressure cut by the 0.98 duct
  efficiency (spec anchor 154430 Pa, matched within 1 Pa).
- Capture area: rho = 101325 / (287.0 * 216.65) = 1.62958 kg/m3,
  V = 0.82 * sqrt(1.4 * 287.0 * 216.65) = 241.935 m/s, and
  capture_area(200, 101325, 216.65, 0.82) = 200 / (1.62958 *
  241.935) = 0.507289 m2 (spec bound 0.5075 m2, matched within 1e-3).
- Capture verdict: against a 0.60 m2 highlight the intake is in
  full-capture; against a 0.45 m2 highlight the same flow demands a
  larger streamtube than the lip admits, so the verdict is spillage.

## Verification

- Confirm ram_recovery(0.82) returns 1.0 and ram_recovery(2.0) returns
  0.925 exactly.
- Confirm face_total_pressure(101325, 0.82, 0.98) returns 154429.99 Pa,
  within 1 Pa of the 154430 Pa spec anchor.
- Confirm capture_area(200, 101325, 216.65, 0.82) returns 0.507289 m2,
  within 1e-3 of the 0.5075 m2 spec bound, and that doubling the
  free-stream density halves the required area (inverse density
  scaling identity).
- Confirm capture_verdict(0.507289, 0.60) is "full-capture" and
  capture_verdict(0.507289, 0.45) is "spillage".
- Confirm negative Mach, Mach at or above 5, non-positive pressure,
  temperature or mass flow, zero or negative duct efficiency, duct
  efficiency above 1 and non-positive capture or highlight areas all
  raise ValueError.
- Run the contract test offline: python3
  scripts/test_subsonic-inlet-recovery.py (31 tests, deterministic).

## Related leaves

- propulsion/gas-turbine-cycle/gas-turbine-cycle: consumes the face
  total pressure this leaf produces as the cycle inlet condition.
- propulsion/turbofan/turbofan-cycle: fan-face station input from the
  intake recovery at the turbofan design point.
- propulsion/ramjet/ramjet-inlet: the shock-dominated ramjet intake
  model for the regimes this leaf does not cover.
- propulsion/gas-turbine-cycle/propelling-nozzle: the exhaust side
  counterpart that turns the cycle exit state into thrust.
- propulsion/gas-turbine-cycle/real-cycle-effects: component loss
  bookkeeping that complements the single duct efficiency here.

## Pitfalls

- Feeding total conditions as the free-stream static state: the model
  takes free-stream static p0 and T0, not stagnation values; the
  stagnation ratio and ram recovery are applied on top of p0 to reach
  the face total pressure.
- Expecting the ram recovery to fall below unity at subsonic Mach:
  rr = 1.0 for all M <= 1.0, the roll-off only begins above Mach 1, so
  a Mach 0.82 intake with duct efficiency 0.98 loses all of its 1.5%
  pressure loss in the duct, not in the external stream.
- Reading the face total pressure as the free-stream total pressure:
  the duct total-pressure efficiency is a separate multiplier, 0.98 in
  the worked example, that the free-stream stagnation value does not
  include (157581.5 Pa against 154429.99 Pa at the face).
- Judging capture without the highlight area: a small capture area is
  not by itself good or bad; the verdict compares it with the intake
  highlight area, and the same 0.5073 m2 streamtube is full-capture at
  a 0.60 m2 highlight and spillage at 0.45 m2.
- Extending the recovery curve to high Mach: the MIL-E-5008B style
  roll-off is only valid below Mach 5, and the whole model is subsonic
  in intent, so Mach 5 and above raises ValueError by design.

## Behavior contract (gate 3)

Run the deterministic contract test (stdlib unittest, offline):

    python3 scripts/test_subsonic-inlet-recovery.py

The test covers the worked-example contract (face total pressure
154430 Pa within 1 Pa, capture area 0.5075 m2 within 1e-3), the ram
recovery truth table at Mach 1.2 and 2.0 and the 0.970578 bound at
Mach 1.5, unity recovery across the subsonic range, the stagnation
pressure ratio formula and its Mach 0.82 anchor, the subsonic
full-recovery identity pt_face = p0 * p0_ratio at duct efficiency 1.0,
the inverse-density capture area identity, the full-capture and
spillage verdicts against both highlight areas, determinism of every
function, and ValueError rejection of negative Mach, Mach at or above
5, non-positive pressure, temperature and mass flow, duct efficiency
outside (0, 1] and non-positive capture or highlight areas.

## Compliance

- Standards referenced, not reproduced: far-33 (family spine, the
  engine installation context in which the intake lives, FAR Part 25
  installation text named only); the recovery curve follows MIL-E-5008B
  style practice, summary-only per standards-map.yaml.
- compliance: STANDARDS-REF, gated: false.
