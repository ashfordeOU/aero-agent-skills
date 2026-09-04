---
name: injector-design
description: "Use when you must design the rocket engine injection elements and their atomization basis: orifice discharge flow from discharge coefficient and pressure drop, injection velocity, the momentum flux ratio of impinging unlike-doublet elements, the fuel and oxidizer orifice counts for a chamber mass flow at a given mixture ratio, and the per-element flow balance. Produces per-orifice mass flow, injection velocity, momentum flux ratio, fuel and oxidizer orifice counts, and per-element mass flow for the element layout. Trigger: unlike doublet, impinging jet, atomization, injector pressure drop, momentum flux ratio, orifice count, discharge coefficient, injection velocity, mixture ratio."
license: Apache-2.0
compliance: STANDARDS-REF
standards:
  - id: ecss
    reference-only: true
gated: false
domain: propulsion
pack: rocket
compatibility: "agentskills.io SKILL.md; any SKILL.md host (Claude Code, Hermes, OpenClaw)"
metadata:
  domain: propulsion
  subdomain: rocket
  tags: [injector-design, unlike-doublet, impinging-jet-atomization, injector-pressure-drop, momentum-flux-ratio, orifice-flow-count]
  version: 0.1.0
  author: AeroSkills
---

# Rocket Engine Injector Design (propulsion/rocket/injector-design)

Use when you must design rocket engine injection elements and their
atomization basis: sizing the orifices that meter propellant into the
chamber, checking the impinging doublet momentum balance, and laying
out the element count for a chamber mass flow and mixture ratio. This
leaf implements the standard injector hydraulics model in pure Python,
stdlib only: orifice discharge with a discharge coefficient, injection
velocity from the Bernoulli head, momentum flux ratio, per-propellant
orifice counts and the per-element flow balance. It pairs with
propulsion/rocket/combustion-chamber-design for the chamber geometry
upstream of the face and propulsion/rocket/rocket-engine-cycle for the
feed pressure context.

## Domain quick reference

- Orifice area: A = pi * d^2 / 4 for a round orifice of diameter d.
- Injection velocity: v = Cd * sqrt(2 * dP / rho), the discharge
  coefficient applied to the Bernoulli head of the pressure drop dP
  across the orifice.
- Orifice discharge: m_dot = rho * A * v = Cd * A * sqrt(2 * rho * dP),
  the standard discharge law written through the jet velocity.
- Momentum flux ratio: J = (rho_o * v_o^2) / (rho_f * v_f^2) per
  impinging unlike-doublet pair. For equal fuel and oxidizer pressure
  drops the Cd, dP and density factors cancel and J = 1 exactly, a
  known design consequence of equal-dP doublets; near-unity J gives a
  well-mixed atomized sheet, large excursions leave one jet dominant.
- Mass split at mixture ratio O/F: m_dot_f = m_dot_c / (1 + O/F) and
  m_dot_ox = m_dot_c - m_dot_f for the chamber mass flow m_dot_c.
- Orifice count: N = ceil(m_dot / m_dot_per_orifice) per propellant,
  rounded up to whole orifices.
- Element flow: the element layout fixes fuel and oxidizer orifices per
  element; the element carries fuel_orifices * m_dot_f_orifice plus
  oxidizer_orifices * m_dot_ox_orifice.
- ECSS E-ST-35-03 frames the liquid propulsion context; the relations
  above are standard engineering methodology, summary-only.
- Units are SI throughout: m, Pa, kg/m^3, m/s, kg/s, dimensionless
  ratios. Typical liquid engine values: Cd 0.6-0.9, injection dP
  1-3 MPa, orifice diameters 1-3 mm.

## Workflow

1. Fix the operating point: chamber mass flow and mixture ratio
   (injector_layout_summary arguments) and the propellant densities.
2. Choose the discharge coefficient Cd and the fuel and oxidizer
   pressure drops; equal drops are the usual unlike-doublet baseline
   because they give J = 1.
3. Pick the orifice diameters, then size one orifice of each
   propellant with orifice_mass_flow (area, jet velocity, per-orifice
   mass flow) or read the same values from the summary.
4. Check the momentum balance with momentum_flux_ratio; recompute J
   for unequal drops and confirm the dP ratio scaling.
5. Get the per-propellant orifice counts with orifice_count and the
   element count with the summary (binding side over orifices per
   element).
6. Balance one element with element_mass_flow and confirm the element
   count times the per-element flow covers the chamber flow.
7. Report the face layout: per-orifice flows, velocities, momentum
   flux ratio, orifice counts, element count and element balance from
   injector_layout_summary.
8. Confirm the deterministic checks with the contract test
   scripts/test_injector_design.py.

## Worked example

RP-1/LOX injector: chamber flow 70.686 kg/s at O/F 2.56, Cd 0.8,
dP 2.0 MPa on both sides, 2.5 mm orifices, RP-1 density 820 kg/m3,
LOX density 1140 kg/m3, element layout one fuel plus two oxidizer
orifices. Real module outputs:

- Orifice area: A = 4.9087e-6 m2 (anchor 4.909e-6 m2).
- Fuel injection velocity: 55.874 m/s, fuel per-orifice flow
  0.22490 kg/s (anchors 55.87 m/s, 0.2249 kg/s).
- LOX injection velocity: 47.388 m/s, LOX per-orifice flow
  0.26518 kg/s (anchors 47.39 m/s, 0.2652 kg/s).
- Momentum flux ratio: J = 1.000000 exactly on the equal-dP case.
- Mass split: fuel 19.856 kg/s, LOX 50.830 kg/s (anchors 19.86,
  50.83); oxidizer over fuel is 2.56 exactly.
- Fuel orifices: ceil(19.856 / 0.22490) = ceil(88.28) = 89; LOX
  orifices: ceil(50.830 / 0.26518) = ceil(191.68) = 192.
- Element: 1 fuel + 2 LOX carries 0.22490 + 2 * 0.26518 = 0.75527 kg/s
  (anchor 0.7553 kg/s); the binding element count is 96 (LOX
  192 orifices at two per element), and 96 * 0.75527 = 72.51 kg/s
  covers the 70.686 kg/s chamber flow.

## Verification

- Confirm orifice_mass_flow returns mass_flow_kgs equal to density
  times area times velocity to 1e-12 and matching Cd * A *
  sqrt(2 rho dP) to 1e-9.
- Confirm momentum_flux_ratio on the equal-dP worked case returns
  1.0 to 1e-9 and that an unequal case (2.5 MPa oxidizer against
  2.0 MPa fuel) returns J = 1.25, the dP ratio.
- Confirm orifice_count ceil behavior: 88.28 to 89, 191.68 to 192, and
  no bump for exactly integral requirements.
- Confirm element_mass_flow(1, 2, 0.2249, 0.2652) totals 0.7553 kg/s
  to 1e-4 and the summary element count times the element flow covers
  the chamber flow.
- Confirm every non-positive Cd, pressure drop, density, diameter,
  orifice count, chamber flow and mixture ratio raises ValueError.
- Run the contract test offline: python3
  scripts/test_injector_design.py (30 tests, deterministic).

## Related leaves

- propulsion/rocket/combustion-chamber-design: the chamber this
  injector faces; boundary is chamber geometry and combustion
  performance upstream of the injection face.
- propulsion/rocket/rocket-engine-cycle: the feed system pressure
  context that sets the injection pressure drops.
- propulsion/rocket/propellant-selection: propellant property context
  for the density terms.

## Contract test

Run the deterministic contract test (stdlib unittest, offline):

    python3 scripts/test_injector_design.py

The test covers the worked-example anchors (orifice area 4.909e-6 m2,
fuel velocity 55.87 m/s and 0.2249 kg/s per orifice, LOX velocity
47.39 m/s and 0.2652 kg/s per orifice, mass split 19.86/50.83 kg/s,
orifice counts 89/192, element balance 0.7553 kg/s), the discharge
identity mass flow equals density times area times velocity, the
equal-dP momentum flux ratio identity J = 1.0 and the unequal-dP
1.25 scaling, ceil behavior of orifice counts, layout summary dict
keys, determinism, chamber-flow coverage by the element count, and
ValueError rejection of non-positive Cd, pressure drop, density,
diameter, counts and mixture ratio.

## Compliance

- Standards referenced, not reproduced: ECSS E-ST-35-03 is a free ESA
  download (ecss.nl/standards); the injector hydraulics relations above
  are standard engineering methodology, summary-only per
  standards-map.yaml.
- compliance: STANDARDS-REF, gated: false.
