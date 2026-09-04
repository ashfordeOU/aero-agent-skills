---
name: plane-change-maneuver
description: "Use when you must compute the delta-v of an orbital plane change maneuver and compare the pure inclination change against the combined burn that merges the plane change with an orbit transfer: evaluate the circular-orbit speed at the maneuver radius with sqrt(mu/r), the pure plane change delta-v 2 v sin(di/2), the speed on the elliptic transfer orbit at the maneuver point with the vis-viva equation, and the combined-burn delta-v from the law of cosines when the plane change rides the circularization burn at apogee. Produces the orbit speeds, the pure and combined delta-v values, and the maneuver-selection verdict that gate the orbit maneuver plan. Trigger: plane-change-maneuver, inclination-change-delta-v, combined-burn, orbital-plane-change, apsidal-plane-change, 2-v-sin-half-inclination, inclination-change, orbital-maneuver-plan."
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
  tags: [plane-change-maneuver, inclination-change-delta-v, combined-burn, orbital-plane-change, apsidal-plane-change, 2-v-sin-half-inclination, inclination-change, orbital-maneuver-plan, circular-orbit-speed, vis-viva-speed]
  version: 0.1.0
  author: Aero Agent Skills
---

# Plane Change Maneuver (space-systems/orbit-mechanics/plane-change-maneuver)

Use when the task is sizing an impulsive orbital plane change maneuver
and trading the pure inclination-change burn against the combined burn
that folds the plane change into an orbit transfer impulse. An
inclination change at circular speed costs 2 v sin(di/2), which is
brutal in LEO (3.803 km/s for 28.5 deg at 300 km) and mild at GEO
altitude, so mission design pushes the plane change onto the slow
apoapsis of a transfer ellipse and often merges it with the
circularization burn there. This leaf implements the circular-orbit
speed, the pure plane change law, the vis-viva transfer speed at the
maneuver point, and the law-of-cosines combined burn in pure Python,
stdlib only. It pairs with space-systems/orbit-mechanics/hohmann-transfer
for the coplanar transfer ellipse that sets up the apsidal plane
change, and with space-systems/mission-design/mission-delta-v-budget
where the resulting contribution is summed into the mission budget.

## Domain quick reference

- Circular orbit speed: v_c = sqrt(mu / r), with mu = 398600.4418
  km3/s2 and r in km. At 300 km circular altitude (r = 6678 km) v_c =
  7.7258 km/s; at geostationary radius (r = 42164 km) v_c = 3.0747
  km/s.
- Pure plane change: dv = 2 v sin(di/2) rotates the velocity vector by
  the inclination change di with no speed change. At the LEO circular
  speed a 28.5 deg change costs 3.803 km/s; at the GEO circular speed
  the same change costs only 1.514 km/s.
- Transfer speed at the maneuver point (vis-viva): v = sqrt(mu (2/r -
  1/a)) holds at any point of the transfer ellipse, periapsis or
  apoapsis, and every ellipse point satisfies r < 2a. On the GTO
  ellipse of semimajor axis 24421 km the speed at the 42164 km apogee
  is 1.6078 km/s.
- Combined one-burn delta-v: dv = sqrt(v1^2 + v2^2 - 2 v1 v2 cos(di))
  from the law of cosines over the angle between the velocity vectors
  before and after the burn, used when the plane change and the speed
  change are applied by one impulse.
- Separate total: (v_after - v_before) + 2 v_after sin(di/2), the two
  burns done independently at the same point.
- Maneuver verdict: 'combined-cheaper' when the combined burn is below
  the separate total by more than 1e-9, otherwise 'pure-cheaper-or-
  equal'; the pure-only case returns 'pure-only'.
- Units are km, km3/s2, km/s and degrees throughout.
- ECSS E-ST-32 frames spacecraft dynamics and maneuver analysis; the
  relations above are standard engineering methodology, summary-only.

## Workflow

1. Fix the maneuver geometry: the circular orbit radius (radius_km) and
   the inclination change di in degrees.
2. Get the reference speed at the maneuver point with
   circular_orbit_speed(mu, radius_km), then the pure burn cost with
   plane_change_dv(speed, di).
3. For an apsidal plane change at the end of a transfer, set the
   transfer semimajor axis a = (r1 + r2) / 2 (the coplanar Hohmann
   ellipse from hohmann-transfer) and the maneuver radius at the
   apoapsis end.
4. Evaluate the transfer speed at the apoapsis with
   transfer_speed_at_radius(mu, apogee_radius_km, a) and the target
   circular speed at the same radius.
5. Compare the one-burn combined_burn_dv(v_before, v_after, di) against
   the separate total (v_after - v_before) plus the pure change, and
   read the winner from maneuver_verdict.
6. Run analyze_plane_change(mu, radius_km, di,
   transfer_semimajor_axis_km, target_radius_km) for the summary dict,
   or with only radius_km and di for the pure-only case.
7. Confirm the deterministic anchors with the contract test
   scripts/test_plane_change_maneuver.py.

## Worked example

Case A, pure plane change: 28.5 deg inclination change on a 300 km
circular orbit (r = 6678 km).

- circular_orbit_speed(MU_EARTH, 6678) = 7.7258 km/s.
- plane_change_dv(7.7258, 28.5) = 2 * 7.7258 * sin(14.25 deg) = 3.803
  km/s.
- At GEO radius the same change costs plane_change_dv(3.0747, 28.5) =
  1.514 km/s, which is why plane changes prefer high orbits.

Case B, combined with the transfer: GTO from 300 km to GEO with the
28.5 deg plane change done at apogee together with the circularization
burn. Transfer semimajor axis a = (6678 + 42164) / 2 = 24421 km.

- transfer_speed_at_radius(MU_EARTH, 42164, 24421) = 1.6078 km/s (the
  exact model value; the classic quoted GTO apogee speed 1.6057 km/s
  corresponds to a 24411 km ellipse and sits within 1e-2 of it).
- circular_orbit_speed(MU_EARTH, 42164) = 3.0747 km/s.
- combined_burn_dv(1.6078, 3.0747, 28.5) = 1.8302 km/s; the classic
  1.832 km/s quote follows from the rounded 1.6057 km/s apogee input,
  both round to the familiar ~1.83 km/s combined GTO-to-GEO burn.
- Separate total: (3.0747 - 1.6078) + 1.514 = 2.981 km/s (within 0.01
  of the 2.983 km/s rounded reference).
- maneuver_verdict(2.981, 1.8302) = 'combined-cheaper': the combined
  burn saves about 1.15 km/s.


## Pitfalls

- Doing the plane change in LEO out of habit: a 28.5 deg change at
  300 km circular costs 3.803 km/s versus 1.514 km/s at GEO, so the
  maneuver radius dominates the cost and the burn belongs at the
  slow apoapsis end of the transfer.
- Quoting the separate burns when one burn can do both: the combined
  apogee burn is 1.8302 km/s against a 2.981 km/s separate total in
  the worked example; the verdict function exists precisely to catch
  a plan that pays the inclination change twice.
- Mixing the transfer ellipse with the target orbit: the apogee
  speed on the GTO ellipse (1.6078 km/s at 42164 km) is not the GEO
  circular speed (3.0747 km/s); the combined burn is the law-of-
  cosines gap between them.
- Forgetting every point of an ellipse satisfies r < 2a: a maneuver
  radius with 2 a <= r is off the ellipse and raises ValueError.
- Feeding an inclination change outside (-180, 180] or a negative
  speed: the law-of-cosines geometry and the pure-change formula
  both reject non-physical inputs instead of returning a number.
- Expecting the model to pick the plane: this leaf sizes a specified
  di; choosing the target inclination (sun-synchronous geometry,
  launch-site constraints) belongs to the sun-synchronous-inclination
  and launch-window-analysis leaves.
## Verification

- Confirm circular_orbit_speed(MU_EARTH, 6678) returns 7.7258 km/s and
  circular_orbit_speed(MU_EARTH, 42164) returns 3.0747 km/s.
- Confirm plane_change_dv(7.7258, 28.5) returns 3.803 km/s and
  plane_change_dv(3.0747, 28.5) returns 1.514 km/s.
- Confirm transfer_speed_at_radius(MU_EARTH, 42164, 24421) returns
  1.6078 km/s, above the GEO circular speed at periapsis and below it
  at apoapsis.
- Confirm combined_burn_dv(1.6057, 3.0747, 28.5) returns 1.832 km/s
  within 0.001 and that di = 0 reduces the combined burn to the pure
  speed difference v_after - v_before.
- Confirm di = 0 returns zero delta-v, di = 90 at the LEO circular
  speed returns v * sqrt(2) = 10.926 km/s within 0.001, and di = 180
  returns 2 v.
- Confirm every radius and semimajor axis of 0 or less, every point off
  the ellipse with 2 a <= r, every negative speed, and every di outside
  (-180, 180] raises ValueError.
- Run the contract test offline: python3
  scripts/test_plane_change_maneuver.py (35 tests, deterministic).

## Related leaves

- space-systems/orbit-mechanics/hohmann-transfer: the coplanar two-
  impulse transfer ellipse this leaf extends with an inclination
  change; hohmann-transfer treats coplanar orbits and defers plane
  changes here.
- space-systems/orbit-mechanics/low-thrust-spiral: the continuous
  low-thrust plane change alternative over many revolutions, opposite
  of the impulsive burn here.
- space-systems/mission-design/mission-delta-v-budget: sums this leaf's
  maneuver contribution with margin and converts the budget to
  propellant.
- space-systems/mission-design/launch-window-analysis: the launch-side
  plane change geometry that sets the initial orbital plane.
- space-systems/orbit-mechanics/sun-synchronous-inclination: the
  inclination target set by sun-synchronous geometry.

## Behavior contract (gate 3)

Run the deterministic contract test (stdlib unittest, offline):

    python3 scripts/test_plane_change_maneuver.py

The test covers the circular speed anchors at LEO and GEO, the pure
plane change anchors 3.803 and 1.514 km/s with the 2 v sin(di/2) law,
the vis-viva GTO apogee speed 1.6078 km/s and its identity, the
combined-burn anchor 1.832 km/s from the spec inputs (1.6057, 3.0747,
28.5) with the law-of-cosines identity, the separate total 2.983 km/s
within 0.01, the combined-cheaper verdict and the ~1.15 km/s saving,
the di = 0 zero delta-v and speed-difference limits, the di = 90 sanity
value 10.926 km/s and di = 180 full-retrograde cases, the analyze chain
dicts for the pure-only and combined cases, and ValueError rejection of
non-positive radii, semimajor axes and mu, points off the ellipse with
2 a <= r, negative speeds, and inclination changes outside (-180, 180].

## Compliance

- Standards referenced, not reproduced: ECSS E-ST-32 is a free ESA
  download (ecss.nl/standards); the plane change relations above are
  standard engineering methodology, summary-only per standards-map.yaml.
- compliance: STANDARDS-REF, gated: false.
