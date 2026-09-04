# Wave-35 leaf spec: landing-gear-retraction-sizing (vehicle-design, sizing pack)

- Path: skills/vehicle-design/sizing/landing-gear-retraction-sizing/
- Pack: sizing. Closest siblings: landing-gear-sizing (static strut
  loads, nose/main wheelbase CG split, shock absorber stroke, tire
  rating - the demand side at touchdown, and stops before any
  mechanism), tire-sizing (tire dimensions and footprint),
  hydraulic-system-sizing (actuator flow/pump sizing for the
  hydraulic power source; this leaf takes the actuator FORCE as a
  demand), structures/loads/landing-ground-loads (ground load
  cases). Whole-tree grep proves ZERO owners for retraction,
  up-lock/down-lock, drag brace, gear bay stowage, retraction
  actuator (only hits: propulsion thrust-vector gimbal actuator,
  GNC actuators, space ADCS - all foreign).
- Standards id: far-25 (reference-only; 25.729 retraction system
  context). Ledger Standard: far-25.
- Family: vehicle-design

## Claim

Size the landing gear retraction mechanism at the conceptual level:
the gear moment about the retract pivot from the gear weight and its
CG arm, the retraction actuator force from that moment and the
actuator arm with a design factor, the actuator stroke from the
four-bar or cross-fold linkage geometry between the down-locked and
up-locked positions by the law of cosines, the down-lock and up-lock
hold loads at their lock arms, and the gear bay stowage fit of the
wheel and folded strut envelope against the bay dimensions. Produces
the retraction moment, the required actuator force and stroke, the
lock hold loads, and a stowage PASS/FAIL verdict that gate the gear
kinematic layout.

Does NOT do: strut load distribution, wheelbase/CG static split,
shock absorber stroke from sink speed (landing-gear-sizing); tire
dimensions and load capacity (tire-sizing); hydraulic pump/flow
sizing for the actuator supply (hydraulic-system-sizing); retraction
DYNAMICS during gear cycling transients (uplock latch dynamics,
drop tests, FAR 25.729 certification testing).

## Model (implement exactly)

Module constants:
- DESIGN_FACTOR_DEFAULT = 1.5 (sizing factor on the retraction
  moment for the actuator force).
- LOCK_FACTOR_DEFAULT = 1.0.
- DEG_PER_RAD not needed (use math.radians).

Conventions: gear weight in N, arms in m, angles in degrees. The
linkage is a triangle with two fixed links a (pivot to gear attach)
and b (pivot to actuator attach) enclosing the angle between the
down-locked and the retracted actuator line; the effective link
length L between the two attach points follows the law of cosines.

Functions (pure stdlib):
- retraction_moment(gear_weight_n, cg_arm_m) -> dict {moment_nm,
  cg_arm_m} = W * d. ValueErrors on non-positive inputs.
- actuator_force(moment_nm, actuator_arm_m, design_factor =
  DESIGN_FACTOR_DEFAULT) -> dict {force_n, moment_nm,
  actuator_arm_m} = design_factor * moment / actuator_arm_m.
  ValueErrors: moment <= 0, actuator_arm <= 0, design_factor < 1.
- link_length(a_m, b_m, angle_deg) -> sqrt(a^2 + b^2 - 2 a b
  cos(angle)). ValueErrors: a/b <= 0; angle outside (0, 180);
  geometry impossible when |a-b| > link bound (link_length must lie
  between |a-b| and a+b; if angle makes L > a+b or L < |a-b| raise).
  Note: for the physically realizable range L in [|a-b|, a+b] the
  angle is in [0,180]; the callers clamp usage to that.
- actuator_stroke(a_m, b_m, down_angle_deg, up_angle_deg) -> dict
  {down_link_m, up_link_m, stroke_m} = L(down) - L(up). ValueErrors:
  stroke <= 0 (up-lock geometry longer than down-lock means the
  actuator cannot retract the gear; raise "up-lock not reachable").
- lock_reaction(moment_nm, lock_arm_m, factor = LOCK_FACTOR_DEFAULT)
  -> dict {reaction_n, lock_arm_m} = factor * moment / lock_arm_m.
  ValueErrors on non-positive inputs.
- stowage_check(wheel_diameter_m, wheel_width_m, folded_strut_m,
  bay_length_m, bay_width_m, bay_depth_m) -> dict {verdict,
  reasons} where verdict PASS when wheel_diameter <= bay_length,
  wheel_width <= bay_width and folded_strut <= bay_depth, else FAIL
  with the list of violated dimensions. ValueErrors on non-positive
  dimensions.
- retraction_summary(gear_weight_n, cg_arm_m, actuator_arm_m,
  a_m, b_m, down_angle_deg, up_angle_deg, down_lock_arm_m,
  up_lock_arm_m, wheel_diameter_m, wheel_width_m, folded_strut_m,
  bay_length_m, bay_width_m, bay_depth_m, design_factor =
  DESIGN_FACTOR_DEFAULT) -> dict with all keys above plus stowage.

Round-trip identity to test: for a given moment and arm, doubling the
design factor doubles the actuator force; for a fixed pair (a,b),
link_length at angle theta equals link_length at -theta (cos even).

## Worked example

Reference main gear: gear weight 14000 N with CG arm 1.10 m ahead of
the retract pivot, actuator attach arm 0.35 m, design factor 1.5;
four-bar triangle links a = 0.55 m and b = 0.40 m; down-locked angle
85 deg, up-locked angle 8 deg; down-lock arm 0.80 m, up-lock arm
0.60 m; wheel 0.66 m diameter x 0.22 m wide; folded strut 2.80 m;
bay 0.70 m x 0.30 m x 3.00 m.

Run your module and take the real outputs as assert targets, then
check the magnitude bounds (independently verified at prep):
- retraction_moment: 14000 * 1.10 = 15400.0 N m.
- actuator_force: 1.5 * 15400 / 0.35 = 66000.0 N (66.0 kN).
- link_length down: a=0.55, b=0.40, 85 deg -> 0.6513 m; up at 8 deg
  -> 0.1637 m.
- actuator_stroke: 0.6513 - 0.1637 = 0.4876 m (about 488 mm).
- lock_reaction down: 15400 / 0.80 = 19250.0 N; up (use the
  up-lock hold moment at the same gear moment for the sizing check,
  factor 1.0): 15400 / 0.60 = 25666.7 N.
- stowage_check: 0.66 <= 0.70 PASS, 0.22 <= 0.30 PASS, 2.80 <= 3.00
  PASS -> verdict PASS.

If a value falls outside its bound, your implementation has a bug:
find it before writing tests. In the SKILL.md worked example show
your module's real outputs (do not invent them).

## Validation list (contract test must include)

- ValueError: non-positive weight/arm/link/angle/dimension; angle
  outside (0, 180); design_factor < 1; stroke <= 0 (up-lock not
  reachable).
- Linkage: a = b = 1.0 m at 60 deg -> link_length = 1.0 m (equilateral
  law of cosines); a = b = 1.0 at 90 deg -> sqrt(2) = 1.4142.
- Moment/force scaling: doubling weight doubles moment; doubling the
  design factor doubles actuator force; doubling the actuator arm
  halves the force.
- Stroke sign guard: down angle smaller than up angle (e.g. 8 down,
  85 up) raises ValueError.
- Lock reaction: 15400 at 0.80 m = 19250 N; reaction inversely
  proportional to lock arm.
- Stowage: nominal PASS; oversize wheel (0.75 m diameter vs 0.70 m
  bay) FAIL with reason list length 1; oversize strut and wheel FAIL
  with 2 reasons.
- Determinism: identical inputs -> identical outputs.
- Convenience dict keys exactly as documented.

## Corpus fragment (eval/hit1-wave35-landing-gear-retraction-sizing.yaml)

Query 1 (copy verbatim):
  "size the main landing gear retraction actuator force and stroke from the linkage geometry between the down and up locked positions"
  intent: "vehicle-design; retraction actuator force and stroke from linkage geometry"
  expected_skill: "vehicle-design/sizing/landing-gear-retraction-sizing"
Query 2 (copy verbatim):
  "check the landing gear up lock and down lock hold load and the gear bay stowage fit at the conceptual design level"
  intent: "vehicle-design; landing gear lock hold loads and gear bay stowage fit"
  expected_skill: "vehicle-design/sizing/landing-gear-retraction-sizing"
Task ids: w35-landing-gear-retraction-sizing-1 and -2.

## Description/tag guidance (gate 1/2 and tag-steal rules)

Description must open "Use when you must size the landing gear
retraction mechanism:" and include the outputs in the Claim. First
tag: landing-gear-retraction-sizing. Additional tags ONLY:
retraction-actuator-sizing, landing-gear-kinematics, up-lock-down-lock,
gear-stowage-check. NEVER single generic words (retraction, actuator,
lock, stowage, gear, kinematics, landing). 50-150 words, <=1000
chars, no em dash, no "classified", action verb present.

FORBIDDEN TOKENS (belong to siblings): shock absorber stroke, sink
speed, tire rating, wheelbase, strut load, static load split, nose
gear share, main gear share (landing-gear-sizing); tire diameter,
tire width, footprint, inflation pressure (tire-sizing); actuator
FLOW, pump flow, accumulator, reservoir (hydraulic-system-sizing);
retraction dynamics, drop test (certification, excluded by claim).
