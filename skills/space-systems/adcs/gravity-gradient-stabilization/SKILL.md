---
name: gravity-gradient-stabilization
description: "Use when you must design or analyze passive gravity-gradient stabilization: check the inertia-ratio stability criterion I_y > I_x > I_z with y along the orbit normal for a nadir-pointing spacecraft, compute the pitch libration frequency and period from the mean motion and the inertia spread, estimate the gravity-gradient restoring torque at a pitch offset, and size a gravity boom tip mass for a target libration stiffness. Produces the stability verdict, the libration period, the restoring torque and the boom sizing that gate the passive attitude design of a nadir-pointing spacecraft. Trigger: gravity-gradient stabilization, inertia-ratio criterion, pitch libration frequency and period, gravity boom sizing, nadir-pointing spacecraft, passive attitude stabilization."
license: Apache-2.0
compliance: STANDARDS-REF
standards:
  - id: ecss
    reference-only: true
gated: false
domain: space-systems
pack: adcs
compatibility: "agentskills.io SKILL.md; any SKILL.md host (Claude Code, Hermes, OpenClaw)"
metadata:
  domain: space-systems
  subdomain: adcs
  tags: [gravity-gradient-stabilization, gravity-boom, libration-frequency, inertia-ratio-criterion, passive-attitude-stabilization, nadir-pointing]
  version: 0.1.0
  author: AeroSkills
---

# Gravity-Gradient Stabilization (space-systems/adcs/gravity-gradient-stabilization)

Use when the task is designing or analyzing passive gravity-gradient
stabilization for a nadir-pointing spacecraft: a long, slender body in a
circular orbit aligns itself with the local vertical because the gravity
gradient of the Earth field makes the smallest-inertia axis point nadir,
provided the intermediate-inertia axis lies along the orbit normal. This
leaf implements the passive design view in pure Python, stdlib only: the
inertia-ratio stability criterion, the pitch libration frequency and
period, the restoring torque at a pitch offset, and gravity boom tip-mass
sizing for a target libration stiffness. It pairs with
gnc-autonomy/space/attitude-dynamics, which models the ambient gravity
torque and propagates the full rigid-body state over the same nadir
geometry, and with the active actuation leaves of this pack, which replace
passive stiffness with momentum exchange.

## Domain quick reference

- Mean motion of the circular orbit: n = sqrt(mu / r^3), with mu the
  gravitational parameter and r the orbital radius. At 500 km altitude
  the radius is 6,878 km and n = 1.1068e-3 rad/s.
- Inertia-ratio stability criterion: passive nadir pointing is stable when
  I_y > I_x > I_z, where x lies along the velocity direction, y along the
  orbit normal and z points nadir. The largest principal moment must be
  about the orbit normal. Verdict via stability_verdict(ix, iy, iz).
- Pitch libration frequency: omega_p = sqrt(3 * n^2 * (I_x - I_z) / I_y),
  computed by pitch_libration_frequency; the period follows as
  2 * pi / omega_p via libration_period.
- Libration period identity: T_lib = T_orbit / sqrt(3 * (I_x - I_z) /
  I_y). When the spread fraction (I_x - I_z) / I_y stays below one third,
  the libration period exceeds the orbital period (6555 s versus 5677 s at
  the worked example, a 1.155 ratio).
- Gravity-gradient restoring torque at a pitch offset theta:
  T = (3/2) * n^2 * (I_x - I_z) * sin(2 * theta), from restoring_torque.
  The torque is zero at 0 and 90 degrees and largest in magnitude at
  45 degrees.
- Gravity boom sizing: a point tip mass m at the end of a boom of length L
  contributes m * L^2 to the inertia spread I_x - I_z, so
  m_tip = target_spread / L^2 via boom_tip_mass_for_stiffness.
- Units are SI throughout: kg m^2 for inertia, s for period, N m for
  torque.
- ECSS frames the space environment and system context; the relations
  above are standard engineering methodology, summary-only.

## Workflow

1. Fix the orbit and geometry: the gravitational parameter mu and the
   circular orbital radius r, then set the mean motion with
   mean_motion(mu, radius).
2. Fix the principal moments I_x, I_y, I_z and run the inertia-ratio
   criterion with stability_verdict(ix, iy, iz); confirm the ranking with
   moment_ordering(ix, iy, iz), which returns the axes by descending
   moment, for example "y > x > z".
3. When the criterion holds, compute the pitch libration frequency with
   pitch_libration_frequency(ix, iy, iz, mu, radius) and the libration
   period with libration_period(ix, iy, iz, mu, radius).
4. Estimate the gravity-gradient restoring torque at the governing pitch
   offset with restoring_torque(ix, iy, iz, mu, radius,
   pitch_offset_deg); use 45 degrees for the largest restoring torque.
5. Size the gravity boom for the required stiffness:
   boom_tip_mass_for_stiffness(ix_other, target_ix_minus_iz,
   boom_length) returns the tip mass that adds the target inertia spread.
6. Gather the design report with gg_report(ix, iy, iz, mu, radius,
   pitch_offset_deg), a dict with keys stable, ordering, omega_p,
   period_s, period_min and torque; quantity keys are None when the
   criterion fails.
7. Confirm the deterministic checks with the contract test
   scripts/test_gravity_gradient_stabilization.py.

## Worked example

Circular orbit at 500 km: mu = 3.986004418e14 m3/s2 and
r = 6.878e6 m give n = 1.1068e-3 rad/s (mean_motion). The principal
moments are I = (60, 80, 40) kg m2 with x along velocity, y along the
orbit normal and z nadir.

- Inertia-ratio criterion: stability_verdict(60, 80, 40) is True because
  80 > 60 > 40; moment_ordering returns "y > x > z". A swap to
  I = (80, 60, 40) fails the verdict (x would be the largest moment).
- Pitch libration: omega_p = 9.585e-4 rad/s and the period is 6555 s,
  equal to 109.25 min, about 1.155 orbital periods (the 5677 s orbit
  period divided by sqrt(3 * 20 / 80)).
- Restoring torque: at a 45 degree pitch offset the torque is 3.675e-5
  N m (36.75 uN m), the largest value; it is exactly zero at 0 and
  90 degrees.
- Boom sizing: for a target inertia spread of 20 kg m2 with a 10 m boom,
  boom_tip_mass_for_stiffness(60, 20, 10) returns 0.2 kg.
- Report: gg_report(60, 80, 40, mu, r) returns stable True, ordering
  "y > x > z", omega_p 9.585e-4 rad/s, period_s 6555, period_min 109.25
  and torque 3.675e-5 N m at the default 45 degree offset.

## Verification

- Confirm mean_motion(3.986004418e14, 6.878e6) returns 1.1068e-3 rad/s
  within 1e-6.
- Confirm stability_verdict returns True on (60, 80, 40), False on
  (80, 60, 40) where ix exceeds iy, and False on (60, 40, 80) where iz is
  not the smallest moment.
- Confirm libration_period returns 6555 s within 20 s and 109.25 min
  within 0.5 min.
- Confirm restoring_torque at 45 degrees is 3.675e-5 N m within 1e-6 and
  exactly zero at 0 degrees.
- Confirm the identities: the period equals the orbital period divided by
  sqrt(3 * (ix - iz) / iy), and doubling the inertia spread raises
  omega_p by sqrt(2).
- Confirm boom_tip_mass_for_stiffness(60, 20, 10) returns 0.2 kg within
  0.01.
- Confirm every non-positive inertia, a negative spread (ix - iz < 0),
  mu or radius at or below zero, and a pitch offset magnitude above
  90 degrees raises ValueError.
- Confirm gg_report keys are exactly stable, ordering, omega_p, period_s,
  period_min and torque, and that repeated calls are deterministic.
- Run the contract test offline: python3
  scripts/test_gravity_gradient_stabilization.py.

## Related leaves

- gnc-autonomy/space/attitude-dynamics: the ambient gravity torque model
  and full rigid-body state propagation over the same nadir-pointing
  geometry; this leaf adds the stability criterion, libration and boom
  sizing that attitude-dynamics deliberately does not compute.
- space-systems/adcs/attitude-control-sizing: sizing the active pointing
  alternative when the passive stiffness and damping budget is set.
- space-systems/orbit-mechanics/three-body-libration: the libration of a
  body about the collinear equilibrium points of the restricted three
  body problem, a distinct regime from the Earth-orbiting nadir libration
  treated here.

## Pitfalls

- Treating the inertia spread as the whole criterion: the libration
  relations need only a positive spread I_x - I_z, but passive stability
  needs the full rank order I_y > I_x > I_z; a body with spread yet
  I_x >= I_y fails the verdict and its report quantities come back None.
- Feeding altitude instead of radius: mean_motion takes the orbital
  radius r = R_earth + h (6,878 km at 500 km altitude); using 500 km in
  its place overstates the mean motion by a factor of about 51.
- Expecting the libration period below the orbital period: with the
  spread fraction below one third, omega_p stays below n and the
  libration period exceeds the orbit period (6555 s against 5677 s), so
  the 2 * pi / n guess understates the true period.
- Using the small-angle torque at large offsets: restoring_torque uses
  sin(2 * theta), which vanishes at 90 degrees; the linear torque
  3 * n^2 * (I_x - I_z) * theta is valid only near the nadir equilibrium.
- Treating the boom sizing as exact: m_tip = spread / L^2 is the
  point-mass approximation and ignores the boom's own mass and finite tip
  size, so it is a preliminary sizing, not a final mass budget.
- Mixing torque units: the restoring torque runs at tens of uN m
  (3.675e-5 N m at the worked example); report in N m and convert
  deliberately.

## Behavior contract (gate 3)

Run the deterministic contract test (stdlib unittest, offline):

    python3 scripts/test_gravity_gradient_stabilization.py

The test covers the worked-example anchors (mean motion at 500 km within
1e-6 rad/s, libration period 6555 s within 20 s, restoring torque
3.675e-5 N m at 45 degrees, boom tip mass 0.2 kg), the inertia-ratio
verdict on all three orderings of the example moments, the libration
period identity against the orbital period and the sqrt(2) scaling of
omega_p with a doubled inertia spread, torque zero crossings at 0 and
90 degrees with the maximum at 45 degrees, gg_report key structure and
unstable-configuration behavior, run-to-run determinism, and ValueError
rejection of non-positive inertia, negative inertia spread, non-positive
mu or radius, and pitch offsets outside the -90 to 90 degree range.

## Compliance

- Standards referenced, not reproduced: ECSS standards are copyright ESA
  and freely downloadable; this leaf cites ECSS as reference only per
  standards-map.yaml. The logic here is generic passive attitude control
  physics (inertia-ratio criterion, pitch libration, gravity boom
  stiffness), not ECSS text.
- compliance: STANDARDS-REF, gated: false.
