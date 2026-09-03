---
name: propellant-tank-sizing
description: "Use when you must size a spacecraft propellant tank for the propulsion bus: convert the propellant mass into the liquid volume with the propellant density, add the ullage volume for the required tank ullage fraction, compute the spherical tank volume and radius, size the sphere tank wall thickness from the burst pressure and the material allowable, estimate the tank shell mass, and size the helium pressurant mass for the regulated or blowdown pressurization scheme with the blowdown pressure range. Produces the propellant, ullage and tank volumes, the radius, wall thickness, shell mass, pressurant mass, the tank mass fraction and the pass or fail verdict that gate the spacecraft propulsion bus design. Trigger: propellant tank sizing, propellant volume, tank ullage fraction, pressurant mass, blowdown pressure range, sphere tank wall thickness, spacecraft propulsion bus."
license: Apache-2.0
compliance: STANDARDS-REF
standards:
  - id: ecss
    reference-only: true
gated: false
domain: space-systems
pack: subsystems
compatibility: "agentskills.io SKILL.md; any SKILL.md host (Claude Code, Hermes, OpenClaw)"
metadata:
  domain: space-systems
  subdomain: subsystems
  tags: [propellant-tank-sizing, propellant-volume, tank-ullage-fraction, pressurant-mass, blowdown-pressure-range, sphere-tank-wall-thickness, spacecraft-propulsion-bus]
  version: 0.1.0
  author: Aero Agent Skills
---

# Propellant Tank Sizing (space-systems/subsystems/propellant-tank-sizing)

Use when the task is sizing a spacecraft propellant tank from the
propellant mass budget of the propulsion bus: converting the propellant
mass into the liquid volume with the propellant density, adding the
ullage volume for the required ullage fraction, computing the total
spherical tank volume and its radius, sizing the membrane wall
thickness from the burst pressure and the material allowable,
estimating the tank shell mass, and sizing the pressurant gas mass for
the regulated or blowdown pressurization scheme. This leaf implements
the standard tank sizing chain in pure Python, stdlib only. It pairs
with space-systems/mission-design/mission-delta-v-budget upstream, the
leaf that converts the mission budget into the propellant mass this
sizing consumes, and with space-systems/subsystems/thermal-design, the
other spacecraft bus sizing sibling.

## Domain quick reference

- Propellant volume: V_p = m / rho, where m is the propellant mass and
  rho the propellant density at the reference temperature.
- Ullage volume: the ullage fraction u is a fraction of the TOTAL tank
  volume, so V_ullage = V_p * u / (1 - u). The propellant occupies the
  remaining (1 - u) of the tank.
- Tank volume: V_t = V_p / (1 - u), the sum of the propellant and
  ullage volumes.
- Sphere radius: r = (3 * V_t / (4 * pi))^(1/3) for a spherical tank.
- Burst pressure: p_burst = burst_factor * MEOP, with burst factor 2.0
  a typical proof margin over the maximum expected operating pressure.
- Wall thickness (thin-walled sphere membrane): t = p_burst * r /
  (2 * sigma_ult), from the hoop stress balance 2 * sigma * t / r = p.
- Shell mass: m_shell = 4 * pi * r^2 * t * rho_material * f_boss,
  where f_boss covers bosses and welds.
- Tank mass fraction: m_shell / m_propellant, the sanity metric that
  gates the bus design against a typical 0.20 budget.
- Pressurant mass (ideal gas): m_gas = P * V_ullage / (R * T), at the
  operating pressure of the scheme. A regulated system holds MEOP; a
  blowdown system starts at MEOP and falls to MEOP / ratio.
- Blowdown pressure range: p_initial = MEOP, p_final = MEOP / ratio
  for a given blowdown ratio.
- Units are SI throughout: kg, m3, m, Pa, K. The helium gas constant
  is 2077.0 J/(kg K).
- ECSS frames the spacecraft engineering context; the relations above
  are standard engineering methodology, summary-only.

## Workflow

1. Fix the propellant budget: propellant_mass_kg from the mission
   delta-v work and propellant_density_kg_m3 for the chosen propellant
   (hydrazine is about 1008 kg/m3).
2. Choose the ullage fraction (typically 0.06 of the total volume) and
   convert mass to volume with propellant_volume_m3.
3. Add the gas volume with ullage_volume_m3 and close the total with
   tank_volume_m3, then get the sphere radius with sphere_radius_m.
4. Set the pressure case: meop_pa, the burst factor (typically 2.0)
   and the material ultimate, then burst_pressure_pa and
   wall_thickness_m.
5. Estimate the structure: shell_mass_kg with the material density
   (Ti-6Al-4V is about 4430 kg/m3) and the boss factor (typically
   1.10).
6. Size the pressurant: pressurant_mass_kg at the MEOP for a regulated
   system or at the initial pressure for blowdown, and
   blowdown_pressure_range for the blowdown scheme.
7. Run analyze with the full input dict to get every quantity plus the
   tank mass fraction and the "tank-sizing-pass" or "tank-sizing-fail"
   verdict against the typical 0.20 budget.
8. Confirm the deterministic checks with the contract test
   scripts/test_propellant_tank_sizing.py.

The ullage fraction, burst factor and boss factor are documented
typical values; they are program inputs and must come from the actual
tank specification, not from this leaf.

## Worked example

Hydrazine monopropellant tank: mass 100 kg, density 1008 kg/m3, ullage
fraction 0.06, MEOP 2.0 MPa, burst factor 2.0, Ti-6Al-4V ultimate 900
MPa, material density 4430 kg/m3, helium pressurant at 293 K, regulated
scheme at the MEOP.

- Propellant volume: 100 / 1008 = 0.099206 m3.
- Ullage volume: 0.099206 * 0.06 / 0.94 = 0.0063323 m3.
- Tank volume: 0.099206 / 0.94 = 0.105539 m3.
- Sphere radius: (3 * 0.105539 / (4 * pi))^(1/3) = 0.29319 m.
- Burst pressure: 2.0 * 2.0 = 4.0 MPa; wall thickness: 4e6 * 0.29319 /
  (2 * 900e6) = 6.5153e-4 m = 0.6515 mm.
- Shell mass: 4 * pi * 0.29319^2 * 6.5153e-4 * 4430 * 1.10 = 3.4296 kg.
- Tank mass fraction: 3.4296 / 100 = 0.0343, well inside the 0.20
  budget, so the verdict is "tank-sizing-pass".
- Pressurant mass (regulated at MEOP): 2e6 * 0.0063323 / (2077 * 293) =
  0.020811 kg of helium.
- Blowdown case: ratio 2.5 at the same MEOP gives p_initial 2.0 MPa and
  p_final 0.8 MPa; the pressurant is sized at the initial pressure, so
  the gas mass is the same 0.020811 kg with these inputs.
- Fail construction: keeping the same radius and thickness but a
  material density of 30000 kg/m3 raises the shell to about 23.2 kg,
  fraction 0.232 above 0.20, so the verdict flips to
  "tank-sizing-fail".

## Verification

- Confirm propellant_volume_m3(100, 1008) returns 0.099206 m3.
- Confirm analyze returns a tank volume of 0.105539 m3, a radius of
  0.29319 m, a wall thickness of 6.5153e-4 m and a shell mass of 3.4296
  kg for the worked example inputs.
- Confirm the sphere round-trip: sphere_radius_m then 4/3 * pi * r^3
  recovers the tank volume.
- Confirm the blowdown range p_final = MEOP / ratio and that the
  blowdown pressurant mass is computed at the initial pressure.
- Confirm the verdict flips to "tank-sizing-fail" only when the tank
  mass fraction exceeds 0.20.
- Confirm every non-positive mass, density, pressure, temperature,
  radius and thickness, burst factors at or below 1.0, ullage fractions
  outside (0, 1), an unknown pressurization mode and blowdown without a
  ratio raise ValueError.
- Run the contract test offline: python3
  scripts/test_propellant_tank_sizing.py (49 tests, deterministic).

## Related leaves

- space-systems/mission-design/mission-delta-v-budget: upstream leaf
  that converts the mission budget into the propellant mass this tank
  sizing consumes.
- space-systems/subsystems/thermal-design: the thermal control sizing
  sibling of the spacecraft bus, paired on the same spacecraft.
- space-systems/subsystems/solar-array-sizing: the power side of the
  bus mass and volume trade around the tank.

## Contract test

Run the deterministic contract test (stdlib unittest, offline):

    python3 scripts/test_propellant_tank_sizing.py

The test covers the worked-example sizing contract (volumes, radius,
burst pressure, wall thickness, shell mass, pressurant mass within the
stated tolerances), ullage fraction edges, sphere volume round trip,
boss factor effect, the regulated and blowdown pressurant sizing, the
blowdown pressure range, the fail-verdict construction and its 0.20
boundary, the documented-default analyze path, and ValueError rejection
of non-physical inputs.

## Compliance

- Standards referenced, not reproduced: ECSS is a free ESA download
  (ecss.nl/standards); the tank sizing relations above are standard
  engineering methodology, summary-only per standards-map.yaml.
- compliance: STANDARDS-REF, gated: false.
