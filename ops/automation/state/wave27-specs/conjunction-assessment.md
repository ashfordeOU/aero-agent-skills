# Wave-27 leaf spec: conjunction-assessment (space-systems, orbit-mechanics pack)

- Path: skills/space-systems/orbit-mechanics/conjunction-assessment/
- Pack: orbit-mechanics (existing siblings: hohmann-transfer,
  lambert-transfer, low-thrust-spiral, clohessy-wiltshire, eclipse-time,
  orbital-perturbations, satellite-coverage, keplerian-elements,
  sun-synchronous-inclination, orbital-decay, ground-track-repeat,
  gravity-assist-swingby)
- Standards ids: ecss  (Ledger Standard: ecss)
- Family: space-systems

## Claim

Assess the collision risk between two space objects at close approach:
from the relative position and velocity at the screening epoch,
compute the time of closest approach and the miss distance with a
linear relative-motion model, project the combined 1-sigma position
uncertainty onto the encounter plane, estimate the probability of
collision with a small hard-body approximation against the combined
object radius, and compare it with an actionable threshold. Produces
the TCA, miss distance, combined covariance scale, probability of
collision, and the screen verdict that gate conjunction screening.

Does NOT do: estimate the long-term debris environment collision
probability from flux, cross-section, and mission life
(mission-design radiation-debris owns the environment model);
determine an initial orbit from position vectors (gnc-autonomy
orbit-determination); or propagate full nonlinear relative motion
(clohessy-wiltshire owns the linear relative state transition). This
leaf is the two-object conjunction screening with a circular
covariance approximation.

## Model (implement exactly)

Inputs:
- rel_pos_m: [x, y, z] (relative position of the secondary in the
  primary-centered inertial frame at epoch),
- rel_vel_ms: [vx, vy, vz] (relative velocity, assumed constant),
- sigma_combined_m (float, combined 1-sigma position uncertainty,
  scalar; documented circular-covariance simplification),
- hard_body_radius_m (float, combined radius of the two objects,
  default 5.0),
- screen_threshold (float, default 1e-4, actionable Pc threshold).

Functions:
- tca_s(rel_pos_m, rel_vel_ms) -> float:
  tca = -dot(r, v)/dot(v, v) when dot(v,v) > 0 else 0.0; ValueError on
  zero relative velocity.
- miss_distance_m(rel_pos_m, rel_vel_ms, tca) -> float: |r + v*tca|.
- encounter_sigma(sigma_combined_m) -> float: the radial/cross-track
  sigma projected to the encounter plane = sigma_combined_m (the
  circular approximation; document that a full 3x3 covariance
  projection is out of scope).
- probability_of_collision(miss_m, sigma_m, hard_body_m) -> float:
  Pc = exp(-miss^2 / (2*sigma^2)) * (hard_body^2 / (2*sigma^2)).
  (Small hard-body approximation to the 2D Gaussian integral, valid
  when hard_body/sigma <= ~0.1; document and return None-style flag
  via the validity field when violated.)
- screen_verdict(pc, threshold) -> dict {actionable (bool), severity
  (str)}: actionable when pc >= threshold; severity "high" when pc >=
  1e-3, "watch" when >= 1e-4, else "green".
- analyze(...) -> dict {tca, miss_m, sigma_m, pc, actionable,
  severity, valid_approximation (bool)}.

ValueError on: sigma <= 0, hard_body < 0, zero relative velocity.

## Worked example

rel_pos [5000, -3000, 2000] m, rel_vel [-7.0, 1.0, -0.5] m/s (closing).
- dot(r,v) = -35000 - 3000 - 1000 = -39000; dot(v,v) = 49+1+0.25 =
  50.25; tca = 39000/50.25 = 776.1 s (assert within 0.5).
- miss: r + v*tca = [5000-5432.8, -3000+776.1, 2000-388.1] =
  [-432.8, -2223.9, 1611.9]; |.| = sqrt(187315 + 4945731 + 2598222) =
  sqrt(7731268) = 2780.5 m (assert within 1.0). (Matches the anchor
  run: TCA 776.1, miss 2780.5.)
- sigma 100 m, hard body 5 m: Pc = exp(-2780.5^2/20000) *
  (25/20000). The exponent is huge negative -> exp ~ 0 -> Pc ~ 0.0
  (assert the module returns a value < 1e-12 and severity "green").
- Near-miss case: rel_pos [10, 0, 0], rel_vel [-1, 0, 0], sigma 100,
  hard body 5: tca 10 s, miss 0 m, Pc = 1*25/20000 = 1.25e-3
  (assert within 1e-6), actionable True, severity "high".
- Offset case: miss 50 m (rel_pos [50,0,0], vel [-1,0,0]): Pc =
  exp(-2500/20000)*0.00125 = 0.8825*0.00125 = 1.103e-3 (assert within
  1e-6), severity "high".
- Validity flag: hard body 15 m with sigma 100 -> hard_body/sigma =
  0.15 > 0.1 -> valid_approximation False (assert).
- ValueErrors: sigma 0, rel_vel [0,0,0].
Keep at least 16 test methods.

## Corpus tasks (ids w27-conjunction-assessment-1/2)

Distinctive tokens: conjunction assessment, time of closest approach,
miss distance, probability of collision, hard body radius, combined
covariance, close approach screening, actionable threshold. Avoid:
debris flux environment collision probability (mission-design
radiation-debris), gibbs method orbit determination
(gnc orbit-determination), relative motion state transition
(clohessy-wiltshire).

1. "screen the close approach between the two spacecraft: relative
   position 10 m ahead closing at 1 m/s with 100 m combined sigma,
   compute the time of closest approach and the probability of
   collision against the 5 m hard body radius"
2. "assess the conjunction risk for the debris encounter with miss
   distance 50 m and 100 m combined covariance, and give the actionable
   verdict against the 1e-4 threshold"

## SKILL body notes

Pair with radiation-debris (environment risk counterpart), and
orbit-determination (state source). The circular covariance and small
hard-body formulas are documented screening approximations; a full
conjunction analysis needs the 3x3 covariance projection and a
numerical Pc integral. ECSS referenced (space safety context) not
reproduced.
