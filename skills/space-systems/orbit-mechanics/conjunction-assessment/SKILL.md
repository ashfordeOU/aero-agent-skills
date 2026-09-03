---
name: conjunction-assessment
description: "Use when you must screen a close approach between two objects and assess the collision risk: compute the time of closest approach from the relative position and velocity with a linear relative-motion model, the miss distance at TCA, the encounter-plane sigma from the combined 1-sigma position uncertainty, the probability of collision with the small hard-body approximation against the combined object radius, and the screen verdict against an actionable threshold. Produces the TCA, miss distance, probability of collision, and the high, watch or green severity verdict. Trigger: conjunction assessment, time of closest approach, miss distance, probability of collision, hard body radius, combined covariance, close approach screening, actionable threshold."
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
  tags: [conjunction-assessment, time-of-closest-approach, miss-distance, probability-of-collision, hard-body-radius, combined-covariance, close-approach-screening, actionable-threshold]
  version: 0.1.0
  author: Aero Agent Skills
---

# Conjunction Assessment (space-systems/orbit-mechanics/conjunction-assessment)

Use when you must assess the collision risk between two space objects
at close approach, for example an operational spacecraft screened
against a debris object or a secondary spacecraft. From the relative
position and velocity at the screening epoch this leaf computes the
time of closest approach and the miss distance under a linear
relative-motion model, projects the combined 1-sigma position
uncertainty onto the encounter plane, estimates the probability of
collision with a small hard-body approximation against the combined
object radius, and returns the actionable verdict against a screen
threshold. It pairs with space-systems/mission-design/radiation-debris
for the long-term environment risk counterpart and
gnc-autonomy/space/orbit-determination for the state source of the
primary; the relative states themselves can come from a propagation of
the two orbits.

## Domain quick reference

- Time of closest approach: tca = -dot(r, v) / dot(v, v) when the
  relative velocity is constant, with r the relative position and v the
  relative velocity at the screening epoch. A closing geometry gives a
  positive TCA; a receding geometry gives a negative TCA, meaning
  closest approach already passed. Zero relative velocity is rejected.
- Miss distance: d_miss = |r + v * tca|, the norm of the relative
  position at the TCA epoch. The miss vector is orthogonal to the
  relative velocity at TCA, dot(r + v * tca, v) = 0.
- Encounter-plane sigma: sigma_enc = sigma_combined, the combined 1-sigma
  position uncertainty of both objects under the circular covariance
  approximation. A full 3x3 covariance projection onto the encounter
  plane is out of scope for this screening model.
- Probability of collision: Pc = exp(-d_miss^2 / (2 * sigma^2)) *
  (r_hb^2 / (2 * sigma^2)), the small hard-body approximation to the 2D
  Gaussian encounter integral with r_hb the combined radius of the two
  objects. The approximation is valid when r_hb / sigma is at most
  about 0.1; above that limit the value is only a rough screen
  indicator and analyze() reports valid_approximation False.
- Screen verdict: actionable when Pc >= threshold (default 1e-4);
  severity "high" when Pc >= 1e-3, "watch" when Pc >= 1e-4, else
  "green".
- Units are SI throughout: m, m/s, s; Pc is dimensionless.
- ECSS frames the space safety context of the screen; the relations
  above are standard engineering methodology, summary-only.

## Workflow

1. Assemble the screening state: the relative position rel_pos_m and
   the relative velocity rel_vel_ms of the secondary in the
   primary-centered frame at the epoch, the combined 1-sigma position
   uncertainty sigma_combined_m, and the combined object radius
   hard_body_radius_m (default 5 m).
2. Compute the time of closest approach with tca_s; check the sign to
   confirm whether the encounter lies ahead of the epoch.
3. Evaluate the miss distance with miss_distance_m at that TCA and the
   encounter-plane sigma with encounter_sigma.
4. Estimate the probability of collision with
   probability_of_collision on the miss distance, sigma, and hard body
   radius.
5. Screen the result with screen_verdict against the actionable
   threshold (default 1e-4) to get the high, watch or green severity.
6. Run the full screen in one call with analyze, which returns the
   TCA, miss distance, sigma, Pc, actionable flag, severity, and the
   valid_approximation flag for the small hard-body model.
7. Confirm the deterministic checks with the contract test
   scripts/test_conjunction_assessment.py.

## Worked example

A spacecraft is screened against a debris object. At the screening
epoch the relative position is [5000, -3000, 2000] m and the relative
velocity [-7.0, 1.0, -0.5] m/s (closing).

- dot(r, v) = -39000, dot(v, v) = 50.25, so tca = 39000 / 50.25 =
  776.1 s (analyze returns 776.12 s).
- Miss: r + v * tca = [-432.8, -2223.9, 1611.9], so the miss distance
  is sqrt(7731268) = 2780.5 m (analyze returns 2780.53 m).
- Combined sigma 100 m, hard body radius 5 m: the exponent
  -2780.5^2 / 20000 is huge negative, so Pc is effectively zero
  (analyze returns 1.6e-171, below 1e-12), actionable False, severity
  "green", valid_approximation True.
- Near-miss case: relative position [10, 0, 0] m closing at 1 m/s
  gives tca 10 s, miss 0 m, and Pc = 1 * 25 / 20000 = 1.25e-3,
  actionable True, severity "high".
- Offset case: a 50 m miss with sigma 100 m and hard body 5 m gives
  Pc = exp(-2500 / 20000) * 0.00125 = 1.103e-3, actionable True,
  severity "high". The offset is realized with the relative position
  [0, 50, 0] m perpendicular to the closing velocity [-1, 0, 0] m/s
  (a closing velocity aligned with the relative position vector drives
  the miss to zero at TCA, so the perpendicular geometry is the one
  that produces a 50 m miss).
- Validity flag: hard body 15 m with sigma 100 m gives r_hb / sigma =
  0.15 above the 0.1 limit, so valid_approximation is False while Pc
  still evaluates as a rough screen indicator.

## Verification

- Confirm tca_s([5000, -3000, 2000], [-7.0, 1.0, -0.5]) returns 776.1 s
  within 0.5 s and miss_distance_m at that TCA returns 2780.5 m within
  1.0 m.
- Confirm probability_of_collision(0, 100, 5) returns exactly 1.25e-3
  and probability_of_collision(50, 100, 5) returns 1.103e-3 within
  1e-6, with severity "high" for both.
- Confirm the miss vector at TCA is orthogonal to the relative
  velocity: dot(r + v * tca, v) = 0.
- Confirm analyze reports valid_approximation False when the hard body
  radius exceeds 0.1 sigma (for example 15 m against 100 m).
- Confirm every non-positive sigma, negative hard body radius, and
  zero relative velocity raises ValueError.
- Run the contract test offline: python3
  scripts/test_conjunction_assessment.py (35 tests, deterministic).

## Related leaves

- space-systems/mission-design/radiation-debris: the long-term debris
  environment collision probability from flux, cross-section, and
  mission life, the environment-level counterpart of this screen.
- gnc-autonomy/space/orbit-determination: recovers the orbit state of
  the primary and secondary from observations as the source of the
  screening state vectors.
- space-systems/orbit-mechanics/clohessy-wiltshire: propagates the
  linearized relative motion of a deputy about a chief, a way to move
  the relative state to the screening epoch when the objects share a
  circular orbit.

## Contract test

Run the deterministic contract test (stdlib unittest, offline):

    python3 scripts/test_conjunction_assessment.py

The test covers the worked-example TCA and miss distance, the closing,
receding, and perpendicular TCA geometries, the zero-relative-velocity
rejection, the miss orthogonality identity at TCA, the circular
encounter-plane sigma projection, the Pc formula at zero, 50 m, and
2780 m miss distances, the hard body squared and inverse sigma squared
scalings, the high, watch, and green verdict bands with default and
custom thresholds, the full analyze dict, the validity flag at and
above the small hard-body limit, and ValueError rejection of
non-positive sigma, negative hard body radius, negative probability,
and zero relative velocity.

## Compliance

- Standards referenced, not reproduced: ECSS space safety standards
  frame the conjunction screening context (ecss.nl/standards); the
  relations above are standard engineering methodology, summary-only
  per standards-map.yaml. No ECSS text is reproduced.
- compliance: STANDARDS-REF, gated: false.
