---
name: gravity-assist-swingby
description: "Use when you must analyze a gravity-assist swing-by maneuver of a spacecraft past a planet or moon: compute the periapsis speed from the hyperbolic excess velocity with the vis-viva energy integral, the flyby turn angle, the delta-v gain for the heliocentric velocity change, and the outgoing direction for outside or inside passes, and check close approach feasibility against the body radius and minimum altitude. Produces the single-flyby summary with periapsis speed, turn angle, delta-v gain and the pass verdict that gates interplanetary trajectory design. Trigger: gravity assist, swing-by, hyperbolic excess velocity, turn angle, periapsis speed, delta-v gain, patched conic flyby, close approach altitude."
license: Apache-2.0
compliance: STANDARDS-REF
standards:
  - id: ecss
    reference-only: true
gated: false
domain: space-systems
pack: orbit-mechanics
compatibility: "agentskills.io SKILL.md; any SKILL.md host (Claude Code, Hermes, OpenClaw)"
metadata:
  domain: space-systems
  subdomain: orbit-mechanics
  tags: [gravity-assist-swingby, gravity-assist, swing-by, hyperbolic-excess-velocity, turn-angle, periapsis-speed, delta-v-gain, close-approach-altitude, patched-conic-flyby]
  version: 0.1.0
  author: Aero Agent Skills
---

# Gravity Assist Swing-by (space-systems/orbit-mechanics/gravity-assist-swingby)

Use when the task is analyzing a single gravity-assist (swing-by)
flyby of a spacecraft past a planet or moon: the spacecraft arrives
on a hyperbolic approach with excess speed v_inf, swings through
periapsis at radius rp, and leaves with the same excess speed
magnitude but a rotated direction. This leaf computes the periapsis
speed from the vis-viva energy integral, the flyby turn angle, the
heliocentric delta-v gain, the outgoing excess velocity direction,
and the close-approach feasibility verdict against the body radius
plus a minimum altitude. It implements the standard single-flyby
patched-conic model in pure Python, stdlib only. It pairs with
space-systems/orbit-mechanics/lambert-transfer and
space-systems/orbit-mechanics/hohmann-transfer as the transfer
method alternatives around the flyby, and with
space-systems/orbit-mechanics/orbital-perturbations for the flyby
perturbation context.

## Domain quick reference

- Periapsis speed from the energy integral: vp = sqrt(v_inf^2 +
  2*mu/rp), with mu the body gravitational parameter. At periapsis the
  excess speed is purely radial, so the vis-viva equation collapses to
  this form.
- Hyperbola eccentricity: e = 1 + rp*v_inf^2/mu. The excess speed
  fixes the specific energy, the periapsis radius fixes the angular
  momentum, and together they set the eccentricity.
- Turn angle: delta = 2*asin(1/e), the rotation of the excess
  velocity vector during the flyby. Fast, distant passes turn little;
  slow, grazing passes can turn beyond 90 degrees.
- Delta-v gain: dv = 2*v_inf*sin(delta/2). For a single unpowered
  flyby the excess speed magnitude is unchanged, so the change of the
  heliocentric velocity vector has this magnitude.
- Outgoing direction: outgoing = incoming + turn_sign * delta, with
  turn_sign +1 for the outside pass and -1 for the inside pass
  geometry relative to the central body.
- Feasibility: altitude = rp - body_radius; the pass is feasible when
  altitude >= min_alt and rp >= body_radius (the flyby clears the
  surface by the minimum altitude).
- Units are SI throughout: m/s, m, m^3/s^2, radians and degrees.
- ECSS frames the mission analysis context (ECSS-E-ST-10 series); the
  relations above are standard engineering methodology, summary-only.

## Workflow

1. Gather the flyby inputs: the arrival hyperbolic excess speed
   v_inf_ms, the periapsis radius rp_m, and the body gravitational
   parameter mu_body (default MU_EARTH = 3.986004418e14 m^3/s^2).
2. Get the periapsis speed with periapsis_speed: vp = sqrt(v_inf^2 +
   2*mu/rp). This is the peak speed the spacecraft sees at closest
   approach, the driver for the thermal and delta-v bookkeeping.
3. Compute the turn angle with turn_angle_rad and convert to degrees
   for reporting; this is how much the excess velocity vector swings.
4. Get the delta-v gain with dv_gain(v_inf_ms, delta_rad), the
   heliocentric velocity change the planet imparts for free.
5. Resolve the outgoing excess velocity direction with
   outgoing_direction_deg, picking turn_sign +1 (outside pass) or
   -1 (inside pass) for the flyby geometry at hand.
6. Check the geometry with feasibility(rp_m, body_radius_m,
   min_alt_m): the altitude above the body surface and the pass
   verdict against the minimum altitude.
7. Run the full summary with analyze(v_inf_ms, rp_m, incoming_deg,
   mu_body, body_radius_m, min_alt_m) and report vp, delta, dv,
   outgoing direction, altitude and the pass verdict together.
8. Confirm the deterministic checks with the contract test
   scripts/test_gravity_assist_swingby.py.

## Worked example

Earth swing-by with v_inf = 3000 m/s at rp = 7000 km, body radius
6371 km, mu = 3.986004418e14 m^3/s^2.

- Periapsis speed: vp = sqrt(9e6 + 2*3.986004418e14/7e6) =
  sqrt(1.22886e8) = 11085.4 m/s.
- Turn angle: e = 1 + 7e6*9e6/3.986004418e14 = 1.15806, so delta =
  2*asin(1/1.15806) = 2*asin(0.86351) = 119.43 deg.
- Delta-v gain: dv = 2*3000*sin(59.714 deg) = 6000*0.86351 =
  5181.1 m/s.
- Altitude: 7000 - 6371 = 629 km, above the 200 km minimum, so the
  pass is feasible.
- Outgoing direction: incoming 0 deg with turn_sign +1 gives
  119.43 deg.
- Second case: v_inf = 5000 m/s at the same rp gives vp = 11785.0
  m/s, delta = 88.04 deg, dv = 6949 m/s; the faster flyby turns less
  and gains more heliocentric speed.

## Verification

- Confirm periapsis_speed(3000.0, 7000e3, MU_EARTH) returns 11085.4
  m/s within 0.5 and analyze on the same case returns delta 119.43
  deg, dv 5181.1 m/s, altitude 629 km and pass True.
- Confirm the 5000 m/s case: vp 11785.0 m/s, delta 88.04 deg,
  dv 6949 m/s.
- Confirm the energy-integral round trip: vp^2 - v_inf^2 equals
  2*mu/rp for any valid input.
- Confirm ValueError rejection of v_inf below zero, rp at or below
  zero, mu at or below zero, a flyby periapsis inside the body when
  the body radius is supplied, and a turn_sign other than +1 or -1.
- Run the contract test offline: python3
  scripts/test_gravity_assist_swingby.py (33 tests, deterministic).

## Related leaves

- space-systems/orbit-mechanics/lambert-transfer: the two-position
  boundary-value transfer that replaces or follows the flyby.
- space-systems/orbit-mechanics/hohmann-transfer: the coplanar
  two-impulse alternative for the transfer budget.
- space-systems/orbit-mechanics/orbital-perturbations: flyby effects
  and third-body context around the patched-conic assumption.
- space-systems/mission-design/launch-window-analysis: the
  interplanetary geometry that sets the incoming excess speed.

## Contract test

Run the deterministic contract test (stdlib unittest, offline):

    python3 scripts/test_gravity_assist_swingby.py

The test covers both worked examples (periapsis speed, turn angle and
delta-v gain at 3 km/s and 5 km/s excess speed), the Mars flyby
feasibility case, periapsis-speed bounds and the energy-integral
round-trip identity, turn angle bounds, the dv-gain formula identity,
inside and outside pass outgoing directions, feasibility verdicts at
and below the minimum altitude and inside the body, the full analyze
summary dict, and ValueError rejection of negative excess speed,
non-positive periapsis radius or gravitational parameter, flybys
inside the body, and invalid turn signs.

## Compliance

- Standards referenced, not reproduced: ECSS (ECSS-E-ST-10 series) is
  a free ESA download (ecss.nl/standards); the swing-by relations
  above are standard engineering methodology, summary-only per
  standards-map.yaml.
- compliance: STANDARDS-REF, gated: false.
