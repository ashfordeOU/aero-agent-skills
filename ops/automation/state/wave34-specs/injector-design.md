# Wave-34 leaf spec: injector-design (propulsion, rocket pack)

- Path: skills/propulsion/rocket/injector-design/
- Pack: rocket. Closest siblings: combustion-chamber-design (sizes the
  chamber volume and contraction, ZERO injector-face content),
  rocket-engine-cycle (mentions injector once as a fixed 2.0 MPa
  pump-discharge pressure loss term, no design outputs),
  propellant-selection (propellant families), nozzle-design (expansion).
  Repo-wide grep: zero hits for atomization, droplet, Sauter, impinging
  jet, spray in any propulsion leaf (hits are icing and shock-expansion
  contexts only).
- Standards id: ecss (reference-only; rocket-pack convention). Ledger
  Standard: ecss.
- Family: propulsion

## Claim

Design rocket engine injection elements and their atomization basis:
orifice discharge flow for a given discharge coefficient and pressure
drop, injection velocity, the momentum flux ratio of impinging doublet
elements, the element count and injector face sizing for a chamber mass
flow and mixture ratio, and the per-element flow balance check.
Produces per-orifice mass flow, injection velocity, momentum flux
ratio, fuel and oxidizer orifice counts, and the per-element mass flow
for the element layout.

Does NOT do: chamber sizing and c-star (combustion-chamber-design);
cycle pump discharge pressures (rocket-engine-cycle); combustion
instability acoustics; spray evaporation or combustion drop burning
models; propellant thermochemistry.

## Model (implement exactly)

Module constants:
- PI = math.pi.
- The worked example assumes a doublet (unlike doublet) element with
  one fuel orifice and two oxidizer orifices; momentum flux ratio
  J = (rho_ox v_ox^2)/(rho_f v_f^2) computed per pair.

Conventions: orifice discharge flow m_dot = Cd rho A v with
v = Cd sqrt(2 dP / rho); A = pi d^2/4 for a round orifice. Injection
velocity uses the same Cd on the Bernoulli head.

Functions (pure stdlib):
- orifice_area(diameter_m) -> pi d^2 / 4. ValueError on non-positive
  diameter.
- injection_velocity(discharge_coefficient, pressure_drop_pa,
  density) -> v = Cd sqrt(2 dP / rho). ValueErrors on non-positive
  inputs.
- orifice_mass_flow(discharge_coefficient, pressure_drop_pa, density,
  diameter_m) -> dict {area_m2, velocity_m_s, mass_flow_kgs}.
  ValueErrors on non-positive inputs.
- momentum_flux_ratio(oxidizer_density, oxidizer_velocity,
  fuel_density, fuel_velocity) -> J = (rho_o v_o^2)/(rho_f v_f^2).
  ValueErrors on non-positive inputs.
- orifice_count(total_mass_flow_kgs, per_orifice_mass_flow_kgs) ->
  ceil(total / per_orifice); ValueError when per_orifice <= 0 or total
  < 0.
- element_mass_flow(fuel_orifices_per_element, oxidizer_orifices_per_
  element, fuel_per_orifice_kgs, oxidizer_per_orifice_kgs) -> dict
  {fuel_kgs, oxidizer_kgs, total_kgs} per element. ValueErrors on
  non-positive inputs.
- injector_layout_summary(chamber_mass_flow_kgs, mixture_ratio_of,
  fuel_density, oxidizer_density, fuel_pressure_drop_pa,
  oxidizer_pressure_drop_pa, discharge_coefficient, fuel_orifice_diam,
  oxidizer_orifice_diam, fuel_orifices_per_element,
  oxidizer_orifices_per_element) -> dict with mdot_f, mdot_ox,
  per-orifice flows, velocities, momentum flux ratio, orifice counts,
  element count (from the limiting orifice count over orifices per
  element) and the per-element flow balance.

The momentum-ratio identity to test: when fuel and oxidizer see the
SAME pressure drop, J = (rho_o v_o^2)/(rho_f v_f^2) with v = Cd
sqrt(2 dP/rho) gives J = 1 exactly (the Cd and dP cancel) - this is a
known design consequence of equal-dP doublets and a strong identity
assert.

## Worked example

Chamber flow 70.686 kg/s at O/F 2.56; Cd 0.8, dP 2.0 MPa; fuel RP-1
density 820 kg/m3, oxidizer LOX density 1140 kg/m3; orifice diameter
2.5 mm for both.

Run your module and take the real outputs as assert targets, then check
the magnitude bounds (independently verified at prep):
- orifice_area = 4.909e-6 m2.
- fuel injection velocity = 0.8 sqrt(2*2.0e6/820) = 55.87 m/s; fuel
  per-orifice mass flow = 0.2249 kg/s.
- LOX injection velocity = 0.8 sqrt(2*2.0e6/1140) = 47.39 m/s; LOX
  per-orifice mass flow = 0.2652 kg/s.
- momentum flux ratio J = 1.000000 exactly (equal-dP identity).
- Fuel mass flow = 70.686/(1+2.56) = 19.86 kg/s; oxidizer mass flow =
  50.83 kg/s.
- Fuel orifice count = ceil(19.86/0.2249) = ceil(88.28) = 89; LOX
  orifice count = ceil(50.83/0.2652) = ceil(191.68) = 192.
- A 1-fuel + 2-LOX element carries 0.2249 + 2*0.2652 = 0.7553 kg/s.

If a value falls outside its bound, your implementation has a bug: find
it before writing tests. In the SKILL.md worked example show your
module's real outputs (do not invent them).

## Validation list (contract test must include)

- ValueError: non-positive Cd/dP/density/diameter/counts/mixture
  ratio; mixture_ratio <= 0.
- Discharge identity: orifice_mass_flow equals density * area *
  velocity to 1e-12; injection_velocity equals Cd sqrt(2 dP/rho).
- Momentum flux ratio: worked equal-dP case gives J = 1.0 exactly to
  1e-9; unequal pressure drops give J different from 1 with the
  expected scaling (J proportional to dP_o/dP_f at equal density? no:
  verify by direct recomputation of the ratio for a second case, e.g.
  dP_o = 2.5 MPa, dP_f = 2.0 MPa - recompute J by hand and assert).
- Counts: ceil behavior - 88.28 -> 89 and 191.68 -> 192; exactly
  integral flow gives count == flow/per_orifice (no ceil bump).
- Element balance: 1 fuel + 2 LOX element total = 0.7553 kg/s within
  1e-4; 6 elements of that type cover the chamber flow (0.7553*6*?
  check against 70.686 - use the real element count from the summary).
- Determinism: identical floats run-to-run (no RNG).
- Convenience dict keys exactly as documented.

## Corpus fragment (eval/hit1-wave34-injector-design.yaml)

Query 1 (copy verbatim):
  "design the rocket engine injector orifices and compute the injection velocity and per orifice mass flow from the discharge coefficient and pressure drop"
  intent: "propulsion; rocket injector orifice flow and injection velocity"
  expected_skill: "propulsion/rocket/injector-design"
Query 2 (copy verbatim):
  "compute the impinging doublet momentum flux ratio and the fuel and oxidizer orifice counts for a rocket engine injector face at a given mixture ratio"
  intent: "propulsion; unlike doublet momentum flux ratio and injector orifice count"
  expected_skill: "propulsion/rocket/injector-design"
Task ids: w34-injector-design-1 and -2.

## Description/tag guidance (gate 1/2 and tag-steal rules)

Description must open "Use when you must design the rocket engine
injection elements and their atomization basis:" and include the
outputs in the Claim. First tag: injector-design. Additional tags
ONLY: unlike-doublet, impinging-jet-atomization, injector-pressure-
drop, momentum-flux-ratio, orifice-flow-count. NEVER single generic
words (injector, orifice, flow, atomization, jet, droplet, design).
50-150 words, <=1000 chars, no em dash, no "classified", action verb
present.

FORBIDDEN TOKENS (belong to siblings): chamber volume, contraction
ratio, c-star (combustion-chamber-design); pump discharge pressure,
cycle (rocket-engine-cycle); expansion ratio, nozzle (nozzle-design);
propellant selection, families (propellant-selection). The words
"injector", "orifice", "momentum flux ratio", "impinging", "atomization"
are this leaf's own.

Tags: [injector-design, unlike-doublet, impinging-jet-atomization,
injector-pressure-drop, momentum-flux-ratio, orifice-flow-count]

Sibling-citation lines for Related leaves:
propulsion/rocket/combustion-chamber-design (the chamber this injector
faces; boundary: chamber volume/c-star vs injection elements),
propulsion/rocket/rocket-engine-cycle (feed-system pressure context),
propulsion/rocket/propellant-selection (propellant property context).

Ledger Standard: ecss.
