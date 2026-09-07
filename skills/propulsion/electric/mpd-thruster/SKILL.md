---
name: mpd-thruster
description: "Use when you must compute the steady operating point of a magnetoplasmadynamic (self-field electromagnetic) MPD thruster for electric propulsion: electromagnetic thrust from the discharge current squared via the self-field thrust law T = (mu0/(4 pi)) J^2 ln(r_a/r_c) at the anode-to-cathode radius ratio, exhaust velocity and specific impulse from the propellant mass flow, jet kinetic power, and the reference-only thrust-to-power band verdict for the steady-state self-field MPD class. Produces the single-point MPD summary with thrust, exhaust velocity, specific impulse, jet power, thrust-to-power and the class operating-band verdict in one call, bands reported never enforced. Trigger: mpd thruster, magnetoplasmadynamic thruster, self-field electromagnetic arc, discharge current squared thrust law, anode to cathode radius ratio, MPD jet power, thrust-to-power band verdict."
license: Apache-2.0
compliance: STANDARDS-REF
standards:
  - id: ecss
    reference-only: true
gated: false
domain: propulsion
pack: electric
compatibility: "agentskills.io SKILL.md; any SKILL.md host (Claude Code, Hermes, OpenClaw)"
metadata:
  domain: propulsion
  subdomain: electric
  tags: [mpd-thruster, magnetoplasmadynamic-thruster, self-field-thrust-law, electromagnetic-acceleration, discharge-current-scaling]
  version: 0.1.0
  author: AeroSkills
---

# Magnetoplasmadynamic Thruster (propulsion/electric/mpd-thruster)

Use when the task is the steady operating point of a self-field
magnetoplasmadynamic (MPD) electromagnetic thruster for electric
propulsion: the discharge current drives its own azimuthal magnetic
field, and the JxB body force on the coaxial arc is the sole
acceleration mechanism. This leaf computes the electromagnetic thrust
from the current-squared thrust law, the exhaust velocity and specific
impulse from the propellant mass flow, the jet kinetic power and the
thrust-to-power ratio on the jet-power basis, and reports the
reference-only class-band verdict. Pure Python, stdlib only. It pairs
with propulsion/rocket/rocket-sizing for the delta-v mission loop and
with its electrostatic pack siblings, which own the other electric
acceleration mechanisms; this leaf has no voltage input at all and
carries the propellant as a mass-flow label only.

## Domain quick reference

- Self-field electromagnetic thrust: T = (mu0/(4 pi)) * J^2 *
  ln(r_a/r_c), with J the total discharge current (A) and r_a/r_c the
  anode-to-cathode radius ratio of the coaxial electrode pair
  (r_a > r_c). The current-squared law of the steady self-field arc
  (Jahn, "Physics of Electric Propulsion", McGraw-Hill 1968, reported
  in the Sutton Rocket Propulsion Elements electric-propulsion
  chapter); mu0/(4 pi) is the 1e-7 N/A^2 coefficient. Electrode falls,
  ionization and thermal-pressure contributions are neglected: the
  ideal electromagnetic thrust.
- Effective exhaust velocity (definition, not a nozzle expansion):
  v_e = T/m_dot with m_dot the total propellant mass flow.
- Specific impulse: Isp = v_e/g0, g0 = 9.80665 m/s^2.
- Jet kinetic power: P_j = T^2/(2 m_dot); the exact identity
  P_j = 0.5 * m_dot * v_e^2 follows from v_e = T/m_dot.
- Thrust-to-power (jet-power basis): T/P_j = 2 * m_dot / T in N/W,
  reported in mN/kW by scaling by 1e6.
- Reference-only class bands (published ranges for the steady
  self-field MPD class, reported never enforced): Isp 1000-4000 s,
  thrust-to-power 10-40 mN/kW.
- Units are SI throughout: A, N, kg/s, m/s, s, W.
- ECSS E-ST-35-03 frames the space propulsion context; the relations
  above are standard engineering methodology, summary-only.

## Workflow

1. Fix the operating point: discharge current J (A), anode-to-cathode
   radius ratio r_a/r_c (> 1) and propellant mass flow m_dot (kg/s,
   argon carried as a mass-flow label only).
2. Run the self-field electromagnetic thrust traverse with
   self_field_thrust(current_j, radius_ratio): the electromagnetic
   thrust from the discharge-current-squared law. Zero current is
   allowed and returns 0.0 exactly.
3. Run the exhaust-velocity and specific-impulse traverse:
   exhaust_velocity(thrust, mass_flow) gives v_e = T/m_dot, then
   specific_impulse(v_e) gives Isp = v_e/g0.
4. Run the jet-power and thrust-to-power traverse: jet_power(thrust,
   mass_flow) gives P_j = T^2/(2 m_dot), then thrust_to_power(thrust,
   p_j) gives the N/W ratio; scale by 1e6 for mN/kW.
5. Run the band-verdict traverse: mpd_band_verdict(isp,
   thrust_to_power_mn_per_kw) reports the position of the point
   against the reference-only class bands; out-of-band never raises.
6. Collapse the point with mpd_operating_point(current_j,
   radius_ratio, mass_flow), the single-point summary dict with
   thrust, exhaust velocity, specific impulse, jet power,
   thrust-to-power (N/W and mN/kW) and the nested band verdict.
7. Confirm the deterministic checks with the contract test
   scripts/test_mpd_thruster.py.

## Worked example

Steady self-field MPD point at the published anchor: J = 10 kA
(10000 A), r_a/r_c = 10, m_dot = 0.1 g/s = 1.0e-4 kg/s argon.

- Thrust: T = 1e-7 * (1e4)^2 * ln(10) = 23.02585092994046 N, within 1
  percent of the 23.0 N receipt target. The coefficient identity
  holds: T/J^2 = 2.302585093e-7 N/A^2.
- Exhaust velocity: v_e = T/m_dot = 230258.5092994046 m/s.
- Specific impulse: Isp = v_e/g0 = 23479.833510873195 s.
- Jet power: P_j = T^2/(2 m_dot) = 2650949.0552391997 W (about 2.65
  MW); the identity P_j = 0.5 * m_dot * v_e^2 holds.
- Thrust-to-power: T/P_j = 8.685889638065036e-06 N/W =
  8.685889638065037 mN/kW; the identity T/P_j = 2 * m_dot / T holds.
- Band verdict: isp_position 'above' the reported 1000-4000 s class
  band, thrust_to_power_position 'below' the reported 10-40 mN/kW
  band, enforced False. The anchor fixes m_dot at 0.1 g/s, so the
  ideal current-squared law implies an exhaust velocity far above the
  class-typical range; the verdict reports this position and never
  enforces it.
- Query-2 companion point at J = 5 kA (same ratio and mass flow): T =
  5.756462732485115 N, exactly one quarter of the 10 kA thrust by the
  J^2 law; v_e = 57564.62732485115 m/s; Isp = 5869.958377718299 s;
  P_j = 165684.31595244998 W; T/P_j = 3.4743558552260144e-05 N/W =
  34.74355855226015 mN/kW (inside the reported 10-40 mN/kW band);
  verdict isp_position 'above', thrust_to_power_position 'inside',
  enforced False. At fixed mass flow, doubling J quadruples the
  thrust but quarters the jet-power-basis thrust-to-power, the
  discharge-current-scaling signature of the law.

## Verification

- Confirm self_field_thrust(10000, 10) returns 23.02585092994046 N
  and equals 23.0 N within 1 percent.
- Confirm exhaust_velocity(23.02585092994046, 1e-4) is 230258.5092994
  m/s and specific_impulse of that value is 23479.833510873195 s.
- Confirm jet_power(23.02585092994046, 1e-4) is 2650949.0552391997 W
  and equals 0.5 * m_dot * v_e^2; confirm thrust_to_power gives
  8.685889638065037 mN/kW and equals 2 * m_dot / T.
- Confirm the scaling identities: T at 20 kA is 4 * T at 10 kA, T at
  5 kA is T(10 kA)/4, T at ratio 100 is 2 * T at ratio 10 and T at
  ratio 1000 is 3 * T at ratio 10 (all within 1e-12 relative).
- Confirm self_field_thrust(0, 10) is exactly 0.0 and zero-current
  thrust is 0 at any valid ratio.
- Confirm the band verdict reports isp 'above' and thrust-to-power
  'below' at the anchor, 'inside' at (2000 s, 20 mN/kW), and never
  raises on out-of-band points.
- Confirm every non-finite input, negative discharge current, radius
  ratio at or below 1, non-positive mass flow, negative thrust or
  exhaust velocity and non-positive jet power raises ValueError.
- Run the contract test offline: python3
  scripts/test_mpd_thruster.py (32 tests, deterministic).

## Related leaves

- propulsion/electric/hall-thruster,
  propulsion/electric/gridded-ion-thruster and
  propulsion/electric/electrothermal-thruster: the other electric
  pack slots, each owning a distinct acceleration mechanism; this
  leaf owns the electromagnetic self-field slot.
- propulsion/rocket/rocket-sizing: the delta-v and propellant mass
  loop around a single thruster operating point.
- propulsion/rocket/nozzle-design: the chemical-thruster nozzle
  branch, the alternative thrust path this leaf never uses.

## Pitfalls

- Reading the ideal law as total thrust: T = (mu0/(4 pi)) J^2
  ln(r_a/r_c) is the ideal electromagnetic thrust; electrode falls,
  ionization and thermal-pressure contributions are neglected, a
  recorded idealization of the anchor.
- Expecting a voltage input: the model has no voltage, no applied
  magnetic field and no electrode-fall or arc-resistance term; the
  discharge current and geometry alone set the operating point.
- Enforcing the class bands: the 1000-4000 s impulse and 10-40 mN/kW
  thrust-to-power ranges are published class bands that
  mpd_band_verdict reports but never enforces; a point outside the
  band is not an error and never raises.
- Mixing the acceleration mechanisms with the pack siblings: hall,
  gridded and electrothermal thrusters use their own electric
  acceleration or heating mechanisms, while this leaf accelerates the
  coaxial arc electromagnetically through its self-field; do not
  apply the sibling machinery here.
- Feeding a radius ratio at or below 1: a coaxial electrode pair
  needs r_a > r_c, so radius_ratio <= 1 raises ValueError; the
  ln(r_a/r_c) geometry factor is undefined at or below unity.
- Forgetting the jet-power basis: the thrust-to-power here is
  T/P_j = 2 * m_dot / T on the jet kinetic power, reported in mN/kW
  by the 1e6 scale, not on an input electrical power that the model
  does not have.

## Behavior contract (gate 3)

Run the deterministic contract test (stdlib unittest, offline):

    python3 scripts/test_mpd_thruster.py

The test covers the 10 kA worked-example contract (thrust
23.02585092994046 N within 1 percent of 23.0 N, exhaust velocity
230258.5 m/s, specific impulse 23479.83 s, jet power 2.651 MW,
thrust-to-power 8.686 mN/kW), the current-squared scaling of thrust
with discharge current, the log-geometry scaling with radius ratio,
the coefficient identity T/J^2 = 1e-7 ln(10), the definition and
jet-power identities, the zero-current boundary, the band-verdict
semantics including out-of-band points that never raise, ValueError
rejection of non-physical inputs across the module, and determinism
of repeated runs. The suite passes under both /usr/bin/python3
(3.9.6) and the pyenv 3.13.12 interpreter.

## Compliance

- Standards referenced, not reproduced: ECSS E-ST-35-03 is a free ESA
  download (ecss.nl/standards); the MPD relations above are standard
  engineering methodology from Jahn and Sutton, summary-only per
  standards-map.yaml.
- compliance: STANDARDS-REF, gated: false.
