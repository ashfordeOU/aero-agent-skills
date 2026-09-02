---
name: hohmann-transfer
description: "Use when you must size a Hohmann transfer between two coplanar circular orbits of a spacecraft: compute the transfer-orbit semimajor axis and period, the circular-orbit velocity at the departure and arrival radii, the periapsis and apoapsis speeds on the transfer ellipse with the vis-viva equation, and the departure and arrival burn impulses that make up the hohmann-transfer delta-v budget. Produces the transfer time, the two impulse burns, and the total delta-v that gate orbit-raising and orbit-lowering maneuver planning and the rendezvous phase angle for a target in the outer orbit. Trigger: hohmann-transfer, delta-v, transfer-orbit, burn-impulse, vis-viva, coplanar-transfer, orbit-raising, transfer-time."
license: Apache-2.0
compliance: STANDARDS-REF
standards:
  - id: ecss
    reference-only: true
gated: false
domain: space-systems
pack: space-systems
compatibility: "agentskills.io SKILL.md; any SKILL.md host (Claude Code, Hermes, OpenClaw)"
metadata:
  domain: space-systems
  subdomain: orbit-mechanics
  tags: [hohmann-transfer, transfer-orbit, burn-impulse, circular-orbit-velocity, transfer-time, orbit-raising, orbit-lowering, coplanar-transfer, rendezvous-phase-angle]
  version: 0.1.0
  author: Aero Agent Skills
---

# Hohmann Transfer (space-systems/orbit-mechanics/hohmann-transfer)

Use when the task is sizing a two-impulse Hohmann transfer between two
coplanar circular orbits: transfer-orbit geometry, circular and
transfer-ellipse velocities, the departure and arrival burn impulses,
the total delta-v budget, the transfer time, and the rendezvous lead
angle.

## Domain quick reference

- Circular orbit velocity: v = sqrt(mu / r), with mu the gravitational
  parameter (3.986004418e14 m^3/s^2 for Earth) and r the orbit radius
  in meters. A low earth orbit at 6878 km radius flies at about 7613
  m/s; a geostationary orbit at 42164 km radius flies at about 3075
  m/s.
- Transfer-orbit semimajor axis: a = (r1 + r2) / 2. The transfer
  ellipse is tangent to the inner circular orbit at periapsis and to
  the outer circular orbit at apoapsis, so the semimajor axis is the
  mean of the two radii.
- Transfer period: T = 2 * pi * sqrt(a^3 / mu). The Hohmann transfer
  covers half the ellipse, so the one-way transfer time is T / 2. A
  low-earth to geostationary transfer takes about 19107 s, roughly
  5.31 hours.
- Vis-viva on the transfer ellipse: v = sqrt(mu * (2 / r - 1 / a)).
  At r1 this is the periapsis speed, at r2 the apoapsis speed.
- Departure burn impulse: dv1 = |v_transfer(r1) - v_circular(r1)|.
  The first impulse at periapsis raises the spacecraft from the inner
  circular orbit onto the transfer ellipse; for an outward transfer it
  is prograde, for an inward transfer retrograde.
- Arrival burn impulse: dv2 = |v_circular(r2) - v_transfer(r2)|. The
  second impulse at apoapsis circularizes the transfer ellipse into
  the outer circular orbit.
- Total delta-v budget: dv_total = dv1 + dv2. The low-earth to
  geostationary coplanar transfer totals about 3816 m/s, the classic
  reference of about 3.9 km/s before any plane change.
- Burn timing: the departure burn fires at periapsis of the transfer
  ellipse (tangent to the inner orbit) and the arrival burn fires at
  apoapsis (tangent to the outer orbit); both burns are impulsive and
  aligned with the velocity vector for a coplanar transfer.
- Rendezvous phase angle: the chaser covers 180 degrees of true
  anomaly during the transfer while the target in the outer circular
  orbit sweeps (t_transfer / T2) * 360 degrees, so the chaser must
  lead the target by lead = 180 - (t_transfer / T2) * 360 degrees at
  departure. For the low-earth to geostationary case the lead angle is
  about 100.2 degrees.
- Specific orbital energy: epsilon = -mu / (2 * a). The transfer
  ellipse energy sits between the energies of the inner and outer
  circular orbits, which is why both impulses add energy for an
  outward transfer.
- Circular orbit period: T = 2 * pi * sqrt(r^3 / mu). A geostationary
  orbit period is about 86164 s, one sidereal day.

## Workflow

1. Establish the two circular orbit radii r1 and r2 in meters (radius,
   not altitude) and the gravitational parameter mu of the central
   body.
2. Compute the circular-orbit velocities at both radii with
   circular_velocity to know what the spacecraft has before and after
   the transfer.
3. Build the transfer ellipse with transfer_semimajor_axis, then the
   one-way transfer time with transfer_time (or the full period with
   transfer_period).
4. Evaluate the periapsis and apoapsis speeds on the transfer ellipse
   with vis_viva_velocity and confirm they bracket the circular
   speeds.
5. Compute the departure and arrival burns with departure_delta_v and
   arrival_delta_v, then the total with total_delta_v; check the
   budget against the propulsion capability.
6. For a rendezvous, compute the departure lead angle with
   rendezvous_phase_angle so the target is met at the outer orbit.
7. Sanity-check the result: the total delta-v for a low-earth to
   geostationary coplanar transfer is about 3.9 km/s and the transfer
   time about 5.3 hours.

## Pitfalls

- Using altitude instead of radius: the formulas take the distance
  from the body center; a 500 km altitude orbit has radius 6878 km,
  and mixing the two changes every velocity and time.
- Summing the impulses with the wrong sign: dv1 and dv2 are both
  positive magnitudes; the burn directions differ (prograde at
  departure, prograde at arrival for an outward transfer, retrograde
  for an inward transfer), and the budget never subtracts them.
- Using the full transfer period as the transfer time: the Hohmann
  arc is half the ellipse, so the time is T / 2; using the full period
  doubles the coast and breaks the rendezvous phase angle.
- Burning at the wrong point: the departure burn must fire at
  periapsis of the transfer ellipse and the arrival burn at apoapsis;
  an off-tangent burn wastes delta-v and leaves the transfer ellipse
  misaligned.
- Ignoring the plane change: the numbers above are for coplanar
  transfers; an inclination change between the two orbits adds its own
  delta-v on top of the Hohmann budget.
- Forgetting the target motion in a rendezvous: the chaser must lead
  the target by the rendezvous phase angle at departure, or the target
  has moved past the meeting point when the chaser arrives.
- Confusing the Hohmann transfer with the rocket equation: the rocket
  equation converts a delta-v budget into propellant mass through the
  specific impulse; the Hohmann transfer sizes the delta-v itself, and
  the two models are separate steps in the maneuver design.
- Assuming equal radii are a transfer: r1 equal to r2 means the
  spacecraft is already on the target orbit and no Hohmann burn
  exists; the logic rejects that input.

## Behavior contract (gate 3)

The Hohmann transfer math is exercised by the gate 3 contract test:
scripts/test_hohmann_transfer.py against
scripts/hohmann_transfer_logic.py (stdlib unittest, offline). Run:
python3 scripts/test_hohmann_transfer.py

## Compliance

- Standards referenced, not reproduced: ECSS-E-ST-10C (systems
  engineering general requirements) frames mission analysis and orbit
  design within the ECSS lifecycle, and the transfer geometry and
  vis-viva relationships above are common astrodynamics methodology,
  summary-only per standards-map.yaml.
- compliance: STANDARDS-REF, gated: false.
