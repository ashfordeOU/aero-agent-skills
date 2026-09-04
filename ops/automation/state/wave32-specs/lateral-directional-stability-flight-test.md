# Wave-32 leaf spec: lateral-directional-stability-flight-test (flight-test-operations, stability pack)

- Path: skills/flight-test-operations/stability/lateral-directional-stability-flight-test/
- Pack: stability. FTO siblings: static-stability-flight-test (pitch
  axis: trim curve, neutral point, static margin), dynamic-stability-
  flight-test (mode damping: Dutch roll, roll subsidence, spiral).
- Standards id: far-25 (reference-only; FAR 25.177 static lateral-
  directional stability, paraphrase only). Ledger Standard: far-25.
- Family: flight-test-operations

## Claim

Plan and reduce the static lateral-directional stability flight test of
a fixed-wing aircraft from steady-heading sideslip data: build the
sideslip sweep test matrix (rudder-fixed and rudder-free runs at a
constant airspeed), fit the measured rudder deflection versus sideslip
angle slope and the aileron deflection versus sideslip slope, estimate
the measured directional stability contribution from the fitted rudder
gradient with a declared rudder control-power input, estimate the
measured lateral (dihedral) stability contribution from the fitted
aileron gradient with a declared aileron control-power input, record the
pedal-force gradient for the rudder-free case, and issue the weathercock
and dihedral stability verdicts against the FAR 25.177-style
requirement. Produces the sideslip sweep matrix, the fitted gradients,
the estimated directional and lateral stability parameters, the
pedal-force gradient and the stability verdicts that gate the static
lateral-directional stability demonstration.

Does NOT do: predicting Cn_beta or Cl_beta from geometry
(flight-mechanics/stability-control/lateral-directional-stability owns
tail-volume-coefficient-based derivative prediction - this leaf reduces
measured flight-test data and takes control-power parameters as INPUTS);
dynamic mode flight testing (dynamic-stability-flight-test owns Dutch
roll, roll subsidence, spiral damping from transient records); pitch-
axis static stability (static-stability-flight-test owns trim curve,
neutral point, elevator-per-g); spin or departure testing.

## Model (implement exactly)

Convention (document this in the SKILL body): measured in a
steady-heading sideslip (SHS) maneuver at constant CAS and altitude.
beta is the sideslip angle in degrees, positive when the nose is LEFT
of the velocity vector (left slip).  The pilot holds the heading with
aileron and uses the rudder to set and hold the sideslip.  For a
directionally STABLE aircraft the pilot must push the rudder INTO the
slip to increase it, so the fitted rudder deflection versus beta slope
s_r = d(delta_r)/d(beta) is POSITIVE with the conventional control
sign (delta_r positive = right pedal).  For a laterally STABLE
aircraft (dihedral effect) the pilot holds left slip with aileron
against the roll, so the fitted aileron slope s_a =
d(delta_a)/d(beta) is NEGATIVE with the conventional control sign
(delta_a positive = right aileron / left roll).  The trim balances
give the signed estimates:

- Cn_beta_est = -cn_dr * s_r   (rad/rad, using s_r deg/deg unitless;
  the deg/deg and rad/rad ratios are numerically identical)
- Cl_beta_est = -cl_da * s_a   (rad/rad)

With cn_dr < 0 and cl_da < 0 as conventional signed control powers
(right pedal produces a positive (nose-right) yawing moment, right
aileron produces a negative (left-wing-down) rolling moment in the
convention used here), a stable aircraft yields Cn_beta_est > 0 and
Cl_beta_est < 0.  FAR 25.177-style criteria are paraphrased in the
verdict functions (weathercock stable when the directional estimate is
positive, lateral stable when the dihedral estimate is negative);
never reproduce the regulation text.

Constants:
- DEG_TO_RAD = math.pi / 180.0
- BETA_SWEEP_MIN = 2 (points), BETA_SWEEP_MAX = 40.
- SIDESLIP_LIMIT_DEG = 15.0 (declared test limit).

Functions (pure stdlib, deterministic):

- fit_slope(xs, ys) -> slope dy/dx by two-parameter least squares
  (offset + slope); return slope float. ValueError on length mismatch,
  fewer than BETA_SWEEP_MIN points, or zero x variance.
- rudder_gradient(beta_deg, delta_r_deg) -> s_r = fit_slope(beta_deg,
  delta_r_deg) in deg/deg (unitless).
- aileron_gradient(beta_deg, delta_a_deg) -> s_a in deg/deg.
- pedal_force_gradient(beta_deg, pedal_force_N) -> g_p = fit_slope(...)
  in N/deg.
- signed_directional_estimate(cn_dr_per_rad, rudder_gradient_per_deg)
  -> Cn_beta_est = -cn_dr_per_rad * rudder_gradient_per_deg (/rad).
  ValueError if cn_dr_per_rad == 0.
- signed_lateral_estimate(cl_da_per_rad, aileron_gradient_per_deg) ->
  Cl_beta_est = -cl_da_per_rad * aileron_gradient_per_deg (/rad).
  ValueError if cl_da_per_rad == 0.
- weathercock_verdict(cn_beta_est_per_rad) -> "stable" when
  cn_beta_est_per_rad > 0 else "unstable".
- dihedral_verdict(cl_beta_est_per_rad) -> "stable" when
  cl_beta_est_per_rad < 0 else "unstable".
- build_sideslip_matrix(beta_targets_deg, cas_ms, altitude_m) -> list
  of dicts {beta_target_deg, cas_ms, altitude_m}. ValueError if any
  beta target outside [-SIDESLIP_LIMIT_DEG, SIDESLIP_LIMIT_DEG] or
  cas <= 0.
- reduce_sideslip_sweep(beta_deg, delta_r_deg, delta_a_deg,
  pedal_force_N=None, cn_dr_per_rad=None, cl_da_per_rad=None) -> dict:
  {rudder_gradient_per_deg, aileron_gradient_per_deg,
  pedal_force_gradient_N_per_deg (None when pedal_force_N is None),
  cn_beta_estimate_per_rad (None when cn_dr is None),
  cl_beta_estimate_per_rad (None when cl_da is None),
  weathercock_verdict (None when cn_dr is None), dihedral_verdict
  (None when cl_da is None), point_count}.  ValueErrors propagate.

ALL functions deterministic, no RNG, stdlib only.

## Worked example

Measured steady-heading sideslip sweeps at constant CAS 80 m/s and
altitude 3000 m on a stable transport configuration: beta (deg) =
[2, 5, 8, 11, 14]; rudder deflection delta_r (deg) = [+0.24, +0.58,
+0.96, +1.34, +1.70] (pilot pushes right pedal into the left slip:
positive slope); aileron deflection delta_a (deg) = [-0.35, -0.80,
-1.30, -1.80, -2.30] (pilot holds the left slip against the dihedral
roll: negative slope); pedal force (N) in the rudder-free run =
[0, -95, -185, -275, -360].  Declared control power inputs cn_dr =
-0.90 /rad and cl_da = -0.35 /rad (predicted by the FM analysis leaf
or wind tunnel; inputs here, never claimed as measured).

Run your module and take the real outputs as assert targets, then check
magnitude bounds:
- rudder_gradient about +0.122 deg/deg (fit through the 5 points, in
  0.10-0.15).
- aileron_gradient about -0.163 deg/deg (in -0.20 to -0.12).
- pedal_force_gradient about -30.0 N/deg (in -40 to -20).
- cn_beta_estimate = -(-0.90) * (+0.12267) = +0.110 /rad (in 0.08-0.15),
  weathercock_verdict "stable".
- cl_beta_estimate = -(-0.35) * (-0.16333) = -0.057 /rad (in -0.10 to
  -0.03), dihedral_verdict "stable".
- build_sideslip_matrix([0, 5, 10], 80, 3000) returns 3 rows with
  beta_target_deg [0, 5, 10] and cas_ms 80; a beta target of 20 deg
  raises ValueError (outside the +-15 deg declared limit).

If a value falls outside its bound, your implementation has a bug: find
it before writing tests. In the SKILL.md worked example show your
module's real outputs (do not invent them).
## Validation list (contract test must include)

- ValueError: length mismatch, fewer than 2 points, zero x variance,
  cn_dr_per_rad == 0, cl_da_per_rad == 0, beta target outside
  [-15, 15] deg, cas <= 0.
- Rudder gradient positive for the stable worked sweep (+0.12267,
  exact LSQ through the 5 points); aileron gradient negative
  (-0.16333); pedal gradient (-30.0 N/deg).
- Cn_beta estimate +0.1104 /rad (exact: -(-0.90)*0.122667), weathercock
  verdict stable; Cl_beta estimate -0.05717 /rad (exact:
  -(-0.35)*(-0.16333)), dihedral verdict stable.
- Sign logic: with a NEGATIVE rudder slope (reverse control or
  directionally unstable aircraft), weathercock_verdict returns
  "unstable"; with a positive aileron slope, dihedral_verdict returns
  "unstable".
- Verdict threshold edges: cn_beta_estimate exactly 0.0 -> "unstable";
  cl_beta_estimate exactly 0.0 -> "unstable".
- reduce_sideslip_sweep returns None fields for the optional inputs
  when not provided, and the exact documented keys when provided.
- build_sideslip_matrix rows carry the documented keys.
- Determinism: no RNG, run-to-run identical floats.
- Convenience dict contains exactly the documented keys.

## Corpus fragment (eval/hit1-wave32-lateral-directional-stability-flight-test.yaml)

Query 1 (copy verbatim):
  "reduce steady-heading sideslip flight test data to the measured rudder and aileron gradients and estimate the directional and lateral stability parameters for the stability demonstration"
  intent: "flight-test-operations; steady-heading sideslip reduction to Cn beta and Cl beta estimates"
  expected_skill: "flight-test-operations/stability/lateral-directional-stability-flight-test"
Query 2 (copy verbatim):
  "plan the rudder-fixed and rudder-free sideslip sweeps of a static lateral-directional stability flight test and judge the weathercock and dihedral stability verdicts from the measured control gradients"
  intent: "flight-test-operations; lateral-directional static stability flight test matrix and verdicts"
  expected_skill: "flight-test-operations/stability/lateral-directional-stability-flight-test"
Task ids: w32-lateral-directional-stability-flight-test-1 and -2.

## Description/tag guidance (gate 1/2 and tag-steal rules)

Description must open "Use when you must plan and reduce the static
lateral-directional stability flight test from steady-heading sideslip
data:" and include the outputs in the Claim. First tag:
lateral-directional-stability-flight-test. Additional tags ONLY:
steady-sideslip-sweep, rudder-fixed-stability, rudder-free-stability,
weathercock-stability, dihedral-effect, pedal-force-gradient. NEVER
single generic words (stability, flight, test, sideslip, rudder,
aileron). 50-150 words, <=1000 chars, no em dash, no "classified",
action verb present.

FORBIDDEN TOKENS (belong to siblings): neutral point, static margin,
trim curve, elevator per g, pitch axis (static-stability-flight-test);
Dutch roll, roll subsidence, spiral mode, short period, phugoid,
damping ratio, log decrement, transient (dynamic-stability-flight-test);
tail volume coefficient, fin lift slope, Cn beta prediction from
geometry, vertical tail sizing (flight-mechanics/stability-control/
lateral-directional-stability owns the PREDICTION leaf - carry
measured/gradient/estimate tokens, never geometry-prediction tokens);
spin, departure. Note the FM leaf also owns the words "dihedral" and
"weathercock" as prediction topics; pair them always with
flight-test-method tokens (steady-heading sideslip, rudder gradient,
pedal-force) so routing stays with this leaf.

Tags: [lateral-directional-stability-flight-test,
steady-sideslip-sweep, rudder-fixed-stability,
rudder-free-stability, weathercock-stability, dihedral-effect,
pedal-force-gradient]

Sibling-citation lines for Related leaves:
flight-test-operations/stability/static-stability-flight-test,
flight-test-operations/stability/dynamic-stability-flight-test,
flight-mechanics/stability-control/lateral-directional-stability (the
prediction sibling; this leaf's control-power inputs come from there),
flight-test-operations/planning/test-point-matrix-design.

Ledger Standard: far-25.
