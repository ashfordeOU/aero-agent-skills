---
name: mission-delta-v-budget
description: "Use when you must build the spacecraft mission delta-v budget: sum the launch insertion, orbit transfer, plane change, station keeping, and deorbit contributions, apply a margin allocation, and convert the budget into propellant mass with the Tsiolkovsky rocket equation from the dry mass and the specific impulse. Produces the nominal and margined delta-v totals, the required propellant and wet masses, and the budget verdict that closes the propulsion sizing. Trigger: mission delta-v budget, delta-v summation, propellant mass, tsiolkovsky, specific impulse, dry mass, station keeping, deorbit."
license: Apache-2.0
compliance: STANDARDS-REF
standards:
  - id: ecss
    reference-only: true
gated: false
domain: space-systems
pack: mission-design
compatibility: "agentskills.io SKILL.md; any SKILL.md host (Claude Code, Hermes, OpenClaw)"
metadata:
  domain: space-systems
  subdomain: mission-design
  tags: [mission-delta-v-budget, delta-v-budget, launch-insertion, station-keeping, deorbit, propellant-mass, specific-impulse, dry-mass, margin-allocation, tsiolkovsky]
  version: 0.1.0
  author: AeroSkills
---

# Mission Delta-V Budget (space-systems/mission-design/mission-delta-v-budget)

Use when the task is a spacecraft mission delta-v budget: summing the
launch insertion, orbit transfer, plane change, station keeping, and
deorbit contributions, applying a margin allocation, and converting the
budgeted delta-v into propellant mass with the Tsiolkovsky rocket
equation from the dry mass and the specific impulse.

Units convention (stated once): delta-v in m/s, masses in kg, specific
impulse in seconds, g0 = 9.80665 m/s^2 (standard gravity), margin as a
fraction (0.15 means 15 percent). No km/s or tonne mixing anywhere.

## Domain quick reference

- Total delta-v budget: dv_total = sum of the contributions, each a
  positive magnitude in m/s. The classic low earth orbit to
  geostationary orbit mission sums launch insertion of about 1600 m/s
  (orbit circularization after the launch vehicle injection), the
  coplanar Hohmann transfer of about 3816 m/s, station keeping of about
  50 m/s per year, and a deorbit burn of about 150 m/s, for a nominal
  total of about 5616 m/s before margin.
- Margin allocation: dv_budget = dv_total * (1 + margin_fraction). A 10
  percent margin on the 5616 m/s example gives 6177.6 m/s; the margin
  covers modeling uncertainty, dispersions, and off-nominal maneuvers.
- Tsiolkovsky rocket equation: dv = Isp * g0 * ln(m0 / mf), with m0 the
  initial (wet) mass and mf the final (dry) mass. A mass ratio of e at
  300 s specific impulse gives exactly 2941.995 m/s.
- Propellant mass: m_prop = m_dry * (exp(dv / (Isp * g0)) - 1). The
  example budget of 6177.6 m/s with a 1500 kg dry mass and a 310 s
  specific impulse (bipropellant class) needs about 9945 kg of
  propellant, so the wet mass is about 11445 kg.
- Wet mass: m0 = m_dry + m_prop, the initial mass the propulsion
  subsystem must accelerate. The propellant fraction m_prop / m0 for
  the example is about 0.87, typical of a large chemical delta-v
  budget.
- Plane change: an inclination change between orbits adds its own
  contribution, roughly 2 * v * sin(delta_i / 2); a 28.5 degree plane
  change at geostationary transfer orbit speed adds about 1800 m/s on
  top of the coplanar transfer, which is why inclined injection is
  preferred.
- Budget verdict: the budget closes when the budgeted delta-v (nominal
  plus margin) is at most the available delta-v of the propulsion
  subsystem; a negative reserve is a design failure, not a rounding
  detail.
- ECSS-E-ST-10C (systems engineering general requirements) frames
  mission analysis and the delta-v budget within the ECSS lifecycle;
  ECSS standards are free to download from https://ecss.nl/standards/
  (name + paraphrase + link only).

## Workflow

1. List the delta-v contributions in m/s: launch insertion, orbit
   transfer (Hohmann or other), plane change, station keeping over the
   mission life, and the deorbit or disposal burn.
2. Sum the contributions with sum_delta_v to get the nominal total; a
   contribution is never subtracted from the budget.
3. Apply the margin allocation with apply_margin (typically 5 to 15
   percent for a pre-critical design budget) to get the budgeted
   delta-v.
4. Convert the budgeted delta-v into propellant mass with
   propellant_mass from the dry mass and the specific impulse, and get
   the wet mass with wet_mass.
5. Build the MissionDeltaVBudget with the contributions, margin, dry
   mass, and specific impulse; use fits to check the budget against the
   available delta-v of the propulsion subsystem.
6. Sanity-check the result: a low earth orbit to geostationary orbit
   mission with margin lands near 6 km/s budgeted, and the propellant
   fraction of a chemical spacecraft with several km/s of budget sits
   above 0.8.

## Pitfalls

- Summing the margin twice: the margin allocation is applied to the
  nominal total once, and the margined total feeds the rocket equation;
  adding margin again inside the propellant conversion inflates the
  tank sizing.
- Forgetting a contribution: station keeping accumulates over the
  mission life (about 50 m/s per year for geostationary, more for
  constellations), and omitting the deorbit or disposal burn understates
  the budget and can miss the 25-year disposal rule.
- Using the nominal total for propellant sizing: the propellant mass
  must come from the budgeted delta-v (nominal plus margin), or any
  dispersion eats the reserve.
- Confusing dry mass and wet mass: the rocket equation works from the
  dry (final) mass; feeding the wet mass as mf understates the
  propellant requirement.
- Mixing units: a delta-v in km/s or a specific impulse in newtons per
  kilogram of fuel flow breaks the exponential; keep m/s and seconds.
- Treating the margin as optional: the founder mandate is a budget with
  margin; a zero-margin budget is a point estimate, not a budget.
- Ignoring the plane change: a coplanar Hohmann transfer is not the
  mission delta-v; the inclination change adds its own contribution and
  often dominates for high-inclination targets.

## Behavior contract (gate 3)

The delta-v summation, margin allocation, Tsiolkovsky conversion, and
budget class logic is exercised by the gate 3 contract test:
scripts/test_mission_delta_v_budget.py against
scripts/mission_delta_v_budget_logic.py (stdlib unittest, offline).
Run from the repo root:
python3 skills/space-systems/mission-design/mission-delta-v-budget/scripts/test_mission_delta_v_budget.py

## Compliance

- Standards referenced, not reproduced: ECSS-E-ST-10C (systems
  engineering general requirements) frames mission analysis and the
  delta-v budget within the ECSS lifecycle, and the Tsiolkovsky rocket
  equation above is common astrodynamics methodology, summary-only per
  standards-map.yaml.
- compliance: STANDARDS-REF, gated: false.
