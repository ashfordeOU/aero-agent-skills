---
name: brake-energy-sizing
description: "Use when you must size the aircraft wheel brake system from the kinetic energy it must absorb: compute the rejected-takeoff (RTO) brake energy at the decision speed and the landing-stop brake energy at the touchdown speed, divide the total energy over the braked wheels, estimate the required carbon heat sink mass per brake from the allowable temperature rise and the specific heat, check the temperature rise of the selected heat sink, and estimate the braking distance at the design deceleration. Produces the RTO and landing energies, the per-brake energy, the governing case, the required heat sink mass, the temperature rise and margin, the braking distance, and the pass or fail verdict that gates the wheel brake sizing. Trigger: brake energy sizing, rejected takeoff energy, wheel brake heat sink, carbon brake mass, brake temperature rise, braking distance at V1, rto brake energy, landing stop brake energy."
license: Apache-2.0
compliance: STANDARDS-REF
standards:
  - id: far-25
    reference-only: true
  - id: cs-25
    reference-only: true
gated: false
domain: vehicle-design
pack: sizing
compatibility: "agentskills.io SKILL.md; any SKILL.md host (Claude Code, Hermes, OpenClaw)"
metadata:
  domain: vehicle-design
  subdomain: sizing
  tags: [brake-energy-sizing, rejected-takeoff-energy, wheel-brake-heat-sink, carbon-brake-mass, brake-temperature-rise, braking-distance-v1, rto-brake-energy, landing-stop-brake-energy]
  version: 0.1.0
  author: Aero Agent Skills
---

# Wheel Brake Energy Sizing (vehicle-design/sizing/brake-energy-sizing)

Use when the task is sizing the wheel brake heat sink of an aircraft at
the conceptual level: converting the kinetic energy the brakes must
absorb at the rejected takeoff (RTO) decision speed and at the landing
touchdown speed into a per-brake energy, a required carbon heat sink
mass, and a temperature rise check of the selected heat sink. This leaf
implements the standard brake energy sizing model in pure Python, stdlib
only (scripts/brake_energy_sizing_logic.py). It pairs with
vehicle-design/sizing/landing-gear-sizing for the gear context and
vehicle-design/sizing/tire-sizing for the tire context; the
flight-test-operations/performance/accelerate-stop-distance leaf covers
the rejected takeoff distance demonstration of a flight test, while this
leaf sizes the brakes from the kinetic energy of the same stop. The
carbon specific heat, the reverse-thrust credit and the design
deceleration are program inputs with documented typical defaults.

## Domain quick reference

- RTO energy at the rejected takeoff: E_rto = 0.5 * m_to * V1^2, with
  m_to the takeoff mass (normally MTOW) and V1 the decision speed.
- Landing-stop energy: E_land = 0.5 * m_lw * v_td^2, with m_lw the
  landing mass (normally MLW) and v_td the touchdown speed.
- Per-brake share with reverse-thrust credit: E_b = E_total *
  (1 - r_rev) / n_b, over n_b braked wheels; the conservative default
  credit r_rev is 0.
- Required heat sink mass per brake: m_hs = E_b / (c_p * delta_t_allow),
  with c_p the heat sink specific heat (carbon default 1200 J/(kg K))
  and delta_t_allow the allowable temperature rise.
- Actual temperature rise of the selected heat sink: delta_t = E_b /
  (m_hs * c_p); the margin is delta_t_allow - delta_t.
- Governing case: the stop with the larger per-brake energy sizes the
  heat sink; for a normal transport the RTO stop at V1 governs.
- Braking distance at the design deceleration: s = v^2 / (2 * a) with
  a = decel_g * G0 and G0 = 9.80665 m/s^2.
- Certification context: FAR-25 and CS-25 treat the rejected takeoff
  condition as the brake energy design case for transport category
  airplanes; the brakes must absorb that energy within the heat sink
  temperature limits. Summary context only, standards not reproduced.
- SI units throughout: J, kg, K, m/s.

## Workflow

1. Fix the program inputs: MTOW and V1 for the RTO stop, MLW and
   touchdown speed for the landing stop, the number of braked wheels,
   the heat sink specific heat, the allowable temperature rise, the
   available heat sink mass per brake and the design deceleration.
2. Compute the stop energies: rto_energy_J(mtow_kg, v1_m_s) and
   landing_energy_J(mlw_kg, touchdown_speed_m_s).
3. Divide each stop energy over the braked wheels, applying the
   reverse-thrust credit, with per_brake_energy_J(total_energy_J,
   n_braked_wheels, reverse_credit).
4. Identify the governing case: the larger per-brake energy (rto or
   landing) drives the sizing.
5. Size the heat sink: required_heat_sink_mass_kg(energy_per_brake_J,
   cp, delta_t_K) for the governing per-brake energy.
6. Check the selected heat sink: temperature_rise_K(energy_per_brake_J,
   mass_kg, cp) with the available mass per brake, and form the margin
   delta_t_allowable - actual rise.
7. Estimate the braking distance at V1 with
   braking_distance_m(v_m_s, decel_g) at the design deceleration.
8. Run analyze(inputs) on the full input dict for the complete report:
   both energies, both per-brake values, the governing case, the
   required mass, the actual rise, the margin, the braking distance and
   the verdict.
9. Read the verdict: brake-energy-pass when the margin is non-negative
   and the required mass fits the available mass, else
   brake-energy-fail. Confirm with the contract test.

## Worked example

Regional transport: MTOW 70000 kg, V1 = 70 m/s; MLW 58000 kg, touchdown
speed 65 m/s; 4 braked wheels; carbon cp 1200 J/(kg K); allowable rise
300 K; available heat sink 130 kg per brake; deceleration 0.35 g;
reverse-thrust credit 0.

- E_rto = 0.5 * 70000 * 70^2 = 171,500,000 J (171.5 MJ).
- E_land = 0.5 * 58000 * 65^2 = 122,525,000 J (122.5 MJ).
- Per-brake RTO energy = 171.5e6 / 4 = 42,875,000 J (42.875 MJ);
  per-brake landing energy = 122.525e6 / 4 = 30.63 MJ, so the RTO stop
  governs.
- Required heat sink mass = 42.875e6 / (1200 * 300) = 119.10 kg.
- Actual rise with 130 kg = 42.875e6 / (130 * 1200) = 274.84 K, margin
  300 - 274.84 = 25.16 K; required mass 119.10 <= 130 kg, verdict
  brake-energy-pass.
- With a 100 kg heat sink the rise is 357.29 K, above the 300 K
  allowable, verdict brake-energy-fail.
- Braking distance at V1 = 70^2 / (2 * 0.35 * 9.80665) = 713.8 m.

## Verification

- Confirm rto_energy_J(70000, 70) returns 171.5e6 J and
  landing_energy_J(58000, 65) returns 122.525e6 J.
- Confirm required_heat_sink_mass_kg(42.875e6, 1200, 300) returns
  119.10 kg and temperature_rise_K(42.875e6, 130, 1200) returns 274.84 K
  with margin 25.16 K.
- Confirm braking_distance_m(70, 0.35) returns 713.8 m.
- Confirm analyze on the example dict reports governing_case "rto" and
  verdict "brake-energy-pass"; with heat_sink_mass_available_kg 100 the
  verdict flips to "brake-energy-fail".
- Confirm the round trip: the required mass computed for the allowable
  rise gives exactly that rise back when re-checked.
- Confirm every non-positive mass, speed, wheel count, specific heat,
  allowable rise and deceleration, and every reverse credit outside
  0..1, raises ValueError.
- Run the contract test offline: python3
  scripts/test_brake_energy_sizing.py (35 tests, deterministic).

## Related leaves

- vehicle-design/sizing/landing-gear-sizing: the landing gear and shock
  strut context around the wheels.
- vehicle-design/sizing/tire-sizing: tire load and footprint context for
  the same landing gear.
- flight-test-operations/performance/accelerate-stop-distance: the
  rejected takeoff distance demonstration whose stop this leaf sizes the
  brakes for.
- vehicle-design/sizing/weight-estimation: the MTOW and MLW inputs for
  the stop energies.

## Contract test

Run the deterministic contract test (stdlib unittest, offline):

    python3 scripts/test_brake_energy_sizing.py

The test covers the regional transport sizing contract (RTO energy
171.5 MJ, landing energy 122.5 MJ, per-brake RTO energy 42.875 MJ,
required mass 119.10 kg, rise 274.84 K with 130 kg and margin 25.16 K,
rise 357.29 K with 100 kg, braking distance 713.8 m), the quadratic
speed scaling of both stop energies and of the braking distance, the
per-brake split with a 20% reverse-thrust credit and the zero-credit
default, the inverse scaling of required mass with the allowable rise,
the rto and landing governing cases, the pass and fail verdicts, the
round-trip identity between required mass and temperature rise, and
ValueError rejection of non-positive mass, speed, wheel count, specific
heat, allowable rise and deceleration and out-of-range reverse credit.

## Compliance

- Standards referenced, not reproduced: FAR-25 (14 CFR Part 25
  Airworthiness Standards for Transport Category Airplanes) and CS-25
  (Certification Specifications for Large Aeroplanes) frame the
  transport category brake energy absorption context; the relations
  above are standard engineering methodology, summary-only per
  standards-map.yaml.
- compliance: STANDARDS-REF, gated: false.
