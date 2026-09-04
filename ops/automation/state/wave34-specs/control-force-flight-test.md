# Wave-34 leaf spec: control-force-flight-test (flight-test-operations, stability pack)

- Path: skills/flight-test-operations/stability/control-force-flight-test/
- Pack: stability. Closest siblings: static-stability-flight-test
  (owns pitch control POSITION trim curves: elevator angle vs CL,
  stick-fixed/free neutral points, elevator ANGLE per g, deflection
  reduction), lateral-directional-stability-flight-test (owns lateral
  pedal-force-gradient on the directional axis as one of many
  outputs), dynamic-stability-flight-test (mode damping). flight-
  mechanics/control-surface-effectiveness (analytic hinge moment stick
  force for DESIGN sizing, not measured-record reduction),
  flight-mechanics/static stability leaves (predicted trim).
  Repo-wide: the only force token in FTO is lateral pedal-force-
  gradient; no leaf anywhere reduces measured longitudinal control
  FORCE records.
- Standards id: far-25 (reference-only; stability-pack convention).
  Ledger Standard: far-25.
- Family: flight-test-operations

## Claim

Reduce measured longitudinal control-force flight-test records: force
transducer calibration from known applied loads and recorded counts,
the stick force gradient versus calibrated airspeed from a speed sweep
(pull positive, aft positive convention) with a stability verdict, the
stick force per g from pull-up maneuvers, the breakout force from the
push-pull hysteresis width, and the centering check of the residual
against the limit. Produces the calibrated force conversion, the
gradient fit and stability verdict, force per g, breakout force and the
centering verdict, the measured-force complement to the deflection
trim curves of the stability pack.

Does NOT do: elevator deflection trim curves and neutral points from
angle records (static-stability-flight-test owns the position side);
lateral-directional flight test with pedal force as one output among
many (lateral-directional-stability-flight-test); analytic hinge-moment
stick force prediction for design (flight-mechanics
control-surface-effectiveness); handling-qualities criteria
evaluation (dynamic-stability-flight-test).

## Model (implement exactly)

Conventions: pull (aft) forces are POSITIVE; push forces negative.
Calibration: linear least-squares slope and intercept of applied load
(lbf) vs recorded counts. Speeds in knots calibrated (KCAS). Load
factors in g. All fits use ordinary least squares over the input
arrays (numpy-free pure stdlib; implement the closed-form sums).

Functions (pure stdlib):
- calibrate_force_transducer(known_lbf, counts) -> dict
  {slope_lbf_per_count, intercept_lbf, predicted_lbf (list)} by
  least-squares y = a x + b with x counts, y lbf. ValueErrors: fewer
  than 2 points, length mismatch, any count < 0.
- stick_force_gradient(speeds_kts, forces_lbf) -> dict
  {slope_lbf_per_kt, intercept_lbf, r2, verdict} fitting force vs
  speed; verdict "stable-gradient" when slope > 0 (pull force
  increases with speed, the stable convention), else
  "unstable-gradient". ValueErrors: fewer than 3 points, length
  mismatch, any speed <= 0.
- force_per_g(load_factors, forces_lbf) -> dict {slope_lbf_per_g,
  intercept_lbf, r2} fitting force vs load factor. ValueErrors as
  above with load factors >= 1... allow any but reject fewer than 3.
- breakout_force(push_lbf, pull_lbf) -> dict {hysteresis_width_lbf,
  breakout_lbf} = (pull - push) and (pull - push)/2 (half-width).
  ValueError when pull <= push (non-physical ordering).
- centering_check(residual_deg, limit_deg) -> dict {residual_deg,
  limit_deg, margin_deg, verdict} with margin = limit - residual,
  verdict "centered" when margin >= 0 else "exceeds-limit".
  ValueErrors: residual < 0, limit <= 0.
- control_force_report(...) -> dict combining all outputs.

Regression identity to test: the calibration reproduces the applied
loads at the calibration points (predicted_lbf equals known_lbf to
floating tolerance on noise-free inputs); stick_force_gradient on
perfectly linear data returns r2 = 1.0.

## Worked example

Reference transport pitch-force flight test:
- Calibration: applied loads 20 lbf at 1230 counts and 60 lbf at 3250
  counts, predicting 2100 counts.
- Speed sweep: V = 120, 130, 140, 150 kts with stick force Fe = -3.8,
  -1.6, 0.6, 2.9 lbf.
- Pull-ups: n = 1.0, 1.5, 2.0, 2.5 with Fe = 1.2, 7.9, 14.3, 20.8 lbf.
- Breakout: push -4.2 lbf, pull 6.4 lbf.
- Centering: residual 0.42 deg, limit 0.50 deg.

Run your module and take the real outputs as assert targets, then check
the magnitude bounds (independently verified at prep):
- calibrate_force_transducer([20, 60], [1230, 3250]):
  slope = 0.019802 lbf/count, intercept = -4.35644 lbf; predicted at
  2100 counts = 37.2277 lbf.
- stick_force_gradient: slope = 0.222 lbf/kt, intercept = -30.47,
  r2 = 0.99927, verdict stable-gradient.
- force_per_g: slope = 13.14 lbf/g, intercept = -12.07, r2 =
  0.99962.
- breakout_force(-4.2, 6.4): hysteresis width 10.6 lbf, breakout
  5.3 lbf.
- centering_check(0.42, 0.50): margin 0.08 deg, verdict centered.

If a value falls outside its bound, your implementation has a bug: find
it before writing tests. In the SKILL.md worked example show your
module's real outputs (do not invent them).

## Validation list (contract test must include)

- ValueError: fewer than 2 calibration points; fewer than 3 points for
  gradient/per-g fits; length mismatches; counts < 0; speeds <= 0;
  pull <= push in breakout; residual < 0; limit <= 0.
- Calibration: two-point case gives slope/intercept matching the
  worked values to 1e-6; predicted at the calibration x equals y to
  1e-9; a third point on the same line gives zero residual.
- Gradient: worked slope 0.222 lbf/kt and r2 0.99927 to 1e-4;
  reversed (force decreasing with speed) gives unstable-gradient.
- Force per g: worked 13.14 lbf/g to 1e-2, r2 0.99962 to 1e-4.
- Breakout: (6.4 - -4.2)/2 = 5.3; symmetric push/pull gives the
  half-width exactly.
- Centering: margin 0.08; residual above the limit returns
  exceeds-limit with negative margin.
- Determinism: identical floats run-to-run (no RNG).
- Convenience dict keys exactly as documented.

## Corpus fragment (eval/hit1-wave34-control-force-flight-test.yaml)

Query 1 (copy verbatim):
  "reduce the measured control force flight test records to the stick force gradient versus calibrated airspeed and the stick force per g from pull up maneuvers"
  intent: "flight-test-operations; control force flight test stick force gradient and force per g reduction"
  expected_skill: "flight-test-operations/stability/control-force-flight-test"
Query 2 (copy verbatim):
  "calibrate the force transducer from applied loads and recorded counts and compute the breakout force and centering check of the control force test"
  intent: "flight-test-operations; force transducer calibration, breakout force and centering"
  expected_skill: "flight-test-operations/stability/control-force-flight-test"
Task ids: w34-control-force-flight-test-1 and -2.

## Description/tag guidance (gate 1/2 and tag-steal rules)

Description must open "Use when you must reduce the measured control
force records of a longitudinal flight test:" and include the outputs
in the Claim. First tag: control-force-flight-test. Additional tags
ONLY: stick-force-gradient, stick-force-per-g, breakout-force,
control-centering-check, force-transducer-calibration,
stick-force-stability. NEVER single generic words (control, force,
stick, gradient, flight, test). 50-150 words, <=1000 chars, no em
dash, no "classified", action verb present.

FORBIDDEN TOKENS (belong to siblings): elevator angle per g, stick
free neutral point, deflection trim curve (static-stability-flight-
test owns the position side); pedal force (lateral-directional-
stability-flight-test owns the lateral axis); hinge moment prediction,
design stick force (flight-mechanics control-surface-effectiveness);
handling qualities level (dynamic-stability-flight-test). The words
"stick force gradient", "force per g", "breakout force", "centering
check", "force transducer" are this leaf's own.

Tags: [control-force-flight-test, stick-force-gradient,
stick-force-per-g, breakout-force, control-centering-check,
force-transducer-calibration, stick-force-stability]

Sibling-citation lines for Related leaves:
flight-test-operations/stability/static-stability-flight-test (the
position-side sibling; this leaf is the measured force complement),
flight-test-operations/stability/lateral-directional-stability-flight-
test (lateral axis sibling),
flight-mechanics/stability-control/control-surface-effectiveness
(analytic design prediction boundary).

Ledger Standard: far-25.
