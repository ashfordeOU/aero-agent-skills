---
name: bi-elliptic-transfer
description: "Use when you must analyze the bi-elliptic three-impulse transfer between two coplanar circular orbits and compare it against the Hohmann transfer: compute the three burn delta-v values (the perigee raise to the intermediate apogee radius, the intermediate-apogee burn that raises the perigee to the target radius, and the target circularization), the total bi-elliptic delta-v, the Hohmann delta-v for the same orbit pair as the comparison baseline, the delta-v saving of the cheaper strategy, and the chosen transfer verdict. Produces the three impulse magnitudes, the two transfer totals, the saving, and the strategy verdict that gate an orbit-transfer design choice at large radius ratios. Trigger: bi-elliptic-transfer, three-impulse-transfer, intermediate-apogee, delta-v-saving, orbit-transfer-comparison, bi-elliptic-crossover."
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
  tags: [bi-elliptic-transfer, three-impulse-transfer, intermediate-apogee, delta-v-saving, orbit-transfer-comparison, bi-elliptic-crossover]
  version: 0.1.0
  author: Aero Agent Skills
---

# Bi-Elliptic Transfer (space-systems/orbit-mechanics/bi-elliptic-transfer)

Use when the task is analyzing the bi-elliptic three-impulse transfer
between two coplanar circular orbits: the perigee raise to an
intermediate apogee radius r_b, the burn at r_b that raises the perigee
to the target radius, the circularization at the target, the total
delta-v, and the crossover comparison against the Hohmann two-impulse
transfer for the same orbit pair. This leaf implements the standard
three-burn model in pure Python, stdlib only. It pairs with
space-systems/orbit-mechanics/hohmann-transfer, which owns the
two-impulse Hohmann transfer itself; this leaf re-derives the Hohmann
budget only as the internal comparison baseline that decides whether the
three-burn strategy wins at large radius ratios.

## Domain quick reference

- Circular orbit speed: v = sqrt(mu / r), with mu the gravitational
  parameter (3.986004418e14 m^3/s^2 for Earth) and r the orbit radius
  in meters.
- First burn (perigee raise): dv1 = sqrt(mu * (2/r1 - 2/(r1 + r_b))) -
  sqrt(mu / r1). At the inner circular orbit radius r1 the spacecraft
  accelerates onto a transfer ellipse whose apogee reaches the
  intermediate radius r_b above the target radius r2.
- Second burn (at the intermediate apogee): dv2 =
  sqrt(mu * (2/r_b - 2/(r_b + r2))) - sqrt(mu * (2/r_b - 2/(r1 + r_b))).
  At r_b the spacecraft changes from the first ellipse (perigee r1) to
  the second ellipse (perigee r2), so it arrives at the target radius
  from above.
- Third burn (circularization): dv3 = sqrt(mu * (2/r2 - 2/(r_b + r2))) -
  sqrt(mu / r2). The spacecraft meets r2 at the perigee of the second
  ellipse, faster than the circular speed, so the closing impulse is
  retrograde and dv3 is the positive magnitude of that speed gap.
- Bi-elliptic total: dv_bi = dv1 + dv2 + dv3. The three impulses are
  magnitudes; the arrival burn direction differs from the first two.
- Hohmann baseline: dv1_h = sqrt(mu * (2/r1 - 2/(r1 + r2))) -
  sqrt(mu/r1) and dv2_h = sqrt(mu/r2) - sqrt(mu * (2/r2 - 2/(r1 + r2))),
  summed for the two-impulse total of the same orbit pair.
- Crossover saving: saving = dv_hohmann - dv_bi. The bi-elliptic
  transfer is cheaper for large radius ratios (roughly r2/r1 above
  11.94 at the best r_b); at small ratios the extra middle burn only
  adds cost. Ties go to hohmann, the simpler strategy.
- Transfer time: the sum of the two half-period coasts, t = pi *
  sqrt((r1 + r_b)^3 / (8 mu)) + pi * sqrt((r_b + r2)^3 / (8 mu)). The
  overshoot to r_b costs days: the worked example below coasts about
  14.5 days.

## Workflow

1. Establish the gravitational parameter mu and the two circular orbit
   radii r1 (start) and r2 (target, larger) in meters; radius, not
   altitude.
2. Choose the intermediate apogee radius r_b above r2. The classic
   choice r_b = 2 * r2 shows the crossover saving at large radius
   ratios; r_b close to r2 degenerates into the Hohmann budget.
3. Compute the Hohmann baseline for the orbit pair with
   hohmann_delta_v(mu, r1, r2) to know what the two-burn strategy
   costs.
4. Compute the three impulses with bi_elliptic_delta_v(mu, r1, r_b,
   r2); check that dv3 is small compared with dv1 when r_b is far
   above r2, as the closing burn happens near the target.
5. Compare strategies with transfer_comparison(mu, r1, r2, r_b) and
   read the saving and the verdict ("bi-elliptic" when the three-burn
   total is lower, "hohmann" otherwise).
6. When mission time matters, size the coast with
   transfer_time_bi_elliptic(mu, r1, r_b, r2) and convert to days;
   the bi-elliptic option trades a much longer transfer time for its
   delta-v saving.
7. Sanity-check the choice: an intermediate apogee at 2 * r2 with
   r2 = 30 * r1 saves about 113 m/s over Hohmann, while at r2 = 2 * r1
   the three-burn option loses and the verdict is "hohmann".

## Worked example

Earth mu = 3.986004418e14 m^3/s^2. Start radius r1 = 6578 km (300 km
circular orbit), target radius r2 = 30 * r1 = 197340 km, intermediate
apogee r_b = 2 * r2 = 394680 km. Module outputs (deterministic):

- Hohmann baseline: dv1 = 3045.4 m/s, dv2 = 1060.2 m/s, total =
  4105.6 m/s.
- Bi-elliptic: dv1 = 3133.8 m/s, dv2 = 638.6 m/s, dv3 = 219.9 m/s,
  total = 3992.2 m/s.
- Crossover: saving = 113.4 m/s, verdict "bi-elliptic": the three-burn
  transfer is cheaper at this radius ratio with r_b = 2 * r2.
- Transfer time: 1248552.7 s, about 14.45 days, versus the roughly
  5.3-hour Hohmann coast for the same orbit pair.


## Pitfalls

- Passing altitude instead of radius: all inputs are circular orbit
  radii in meters (r1, r2, r_b), so a 300 km orbit enters as
  6578000 m, not 300000.
- Choosing r_b at or below the target: the intermediate apogee must
  sit above r2 (r_b <= r2 raises ValueError); r_b close to r2 just
  degenerates into the Hohmann budget and buys nothing.
- Reversing the transfer direction: an inward transfer (r2 <= r1) is
  rejected with ValueError - this leaf models outward raises only.
- Expecting the extra burn to always pay: the bi-elliptic total only
  beats Hohmann at large radius ratios (the worked example saves
  113.4 m/s at r2 = 30 r1); at small ratios like r2 = 2 r1 the
  verdict is "hohmann" and ties go to the simpler two-burn strategy.
- Comparing strategies on delta-v alone: the bi-elliptic coast runs
  14.45 days versus a 5.3-hour Hohmann coast in the worked example,
  so a delta-v saving can be a mission-time loss.
- Forgetting the burn directions: dv1 and dv2 are prograde raises,
  but dv3 is the retrograde circularization at the target perigee;
  the three values are magnitudes, and only their sum forms the
  total.
## Verification

- Worked-example bounds (contract anchors): Hohmann total in
  3900-4300 m/s, bi-elliptic total in 3850-4150 m/s, saving in
  50-180 m/s, verdict "bi-elliptic", transfer time in 10-40 days. The
  module outputs above sit inside every bound.
- Sanity at a small ratio: with r2 = 2 * r1 and a moderate r_b the
  Hohmann total stays below the bi-elliptic total and the verdict is
  "hohmann".
- Degenerate limit: with r_b very close to r2 (r_b = 1.01 * r2) the
  bi-elliptic total approaches the Hohmann total from above
  (bi_total > hohmann_total - 1.0 m/s).
- Round-trip: every impulse equals the difference of the two vis-viva
  speeds it is defined from, and the total equals dv1 + dv2 + dv3
  within 1e-6.
- Determinism: pure math on module constants, no random number
  generation anywhere; repeated calls return identical floats.
- ValueError rejection of every non-physical input: mu <= 0, r1 <= 0,
  r2 <= 0, r1 == r2, r_b <= r2, and an inward transfer (r2 <= r1).
- Run the contract test offline: python3
  scripts/test_bi_elliptic_transfer.py (33 tests, deterministic).

## Related leaves

- space-systems/orbit-mechanics/hohmann-transfer: owns the two-impulse
  Hohmann transfer that this leaf re-derives only as the comparison
  baseline.
- space-systems/orbit-mechanics/keplerian-elements: the two-body
  orbital elements that frame both circular end orbits.
- space-systems/orbit-mechanics/orbital-perturbations: J2 and drag
  effects that a many-day transfer arc accumulates.

## Behavior contract (gate 3)

Run the deterministic contract test (stdlib unittest, offline):

    python3 scripts/test_bi_elliptic_transfer.py

The test covers the worked example (Hohmann and bi-elliptic anchors
with their magnitude bounds, the 50-180 m/s saving window, the
"bi-elliptic" verdict, the 10-40 day time bound), the circular-speed
identity, the small-radius-ratio sanity check with a "hohmann" verdict,
the degenerate r_b near r2 limit, vis-viva round trips for every
impulse, exact convenience-dict keys, run-to-run determinism, and
ValueError rejection of every non-physical input in the validation
list.

## Compliance

- Standards referenced, not reproduced: ECSS-E-ST-10C (systems
  engineering general requirements) frames mission analysis and orbit
  design within the ECSS lifecycle, and the three-burn transfer
  geometry and vis-viva relationships above are common astrodynamics
  methodology, summary-only per standards-map.yaml.
- compliance: STANDARDS-REF, gated: false.
