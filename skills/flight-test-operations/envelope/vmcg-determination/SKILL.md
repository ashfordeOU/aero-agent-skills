---
name: vmcg-determination
description: "Use when you must reduce the engine-failure ground roll demonstration runs of a transport airplane flight test to the ground minimum control speed Vmcg in the spirit of the FAR/CS 25.149 ground leg method, summary-only: build the asymmetric yawing moment from the failed engine thrust at its lateral arm, apply the nosewheel steering authority below the steering cutout speed, solve the steering-free rudder authority limited and 150 lbf pedal force limited ground speeds with the boost factor, classify runs into the steering-held, departed, at-limit and with-margin classes, and take the minimum corrected at-limit speed as the Vmcg verdict with bracket checks. Produces the corrected run table, the Vmcg in m/s and knots, the bracket verdict, the stall guard check against 1.05 Vs1, and the V1 gate verdict with the required V1 speed. Trigger: ground minimum control speed, vmcg determination, nosewheel steering authority, steering cutout speed, engine failure ground roll run."
license: Apache-2.0
compliance: STANDARDS-REF
standards:
  - id: far-25
    reference-only: true
  - id: cs-25
    reference-only: true
gated: false
domain: flight-test-operations
pack: envelope
compatibility: "agentskills.io SKILL.md; any SKILL.md host (Claude Code, Hermes, OpenClaw)"
metadata:
  domain: flight-test-operations
  subdomain: envelope
  tags: [vmcg-determination, ground-minimum-control-speed, nosewheel-steering-authority, steering-cutout-speed]
  version: 0.1.0
  author: AeroSkills
---

# Ground Minimum Control Speed Vmcg (flight-test-operations/envelope/vmcg-determination)

Use when the task is the ground minimum control speed Vmcg reduction of
the engine-failure ground roll demonstration runs of a transport airplane
flight test, in the spirit of the FAR/CS 25.149 ground leg method,
summary-only. This leaf builds the asymmetric yawing moment from the
operating-engine thrust at the failed engine lateral arm (the critical
engine fails suddenly during the takeoff roll; the windmilling drag of
the failed engine is neglected at ground roll speeds in the main model
and carried as an optional variant), applies the nosewheel steering
authority below the steering cutout speed, solves the steering-free
rudder authority limited and 150 lbf (667 N) pedal force limited ground
speeds with the boost factor, corrects every run to standard conditions,
classifies the runs, and issues the Vmcg verdict with the bracket
consistency check, the stall protection guard on the reference stall
speed and the balanced-field V1 gate. It parallels the airborne minimum
control speed leaf (flight-test-operations/envelope/vmc-determination),
whose reduction structure, boost-factor pedal force family and 150 lbf
criterion it shares, but the governing surface here is the ground roll:
nosewheel steering cutout, steering-free recovery, runway-edge control.
Steering-free reductions only for the qualifying verdict; steering-
engaged runs are practice evidence. The nosewheel steering is modeled as
a friction-limited lateral force at the nose gear active only below the
cutout; differential braking, dynamic ground-roll transients, sideslip
coupling and ground-effect aerodynamics beyond the sigma density
correction are out of scope. Single-layer ISA to 11 km only.

## Domain quick reference

- ISA density ratio at pressure altitude h_p with deviation dt_isa:
  delta = (1 - LAPSE*h_p/T0)**EXP, theta = (T0 - LAPSE*h_p + dt_isa)/T0,
  sigma = delta/theta. At 600 m with +12 K, sigma = 0.905430.
- TAS to CAS: v_cas = v_tas*sqrt(sigma); calibrated airspeed input needs
  no density correction.
- Weight correction at fixed lift coefficient: v_corr = v_cas*
  sqrt(w_ref/w_test), the standard V-speed reduction.
- Configuration normalization through the rotation-limit lift
  coefficient CL(f) = cl_0 + cl_per_deg*f: v_norm = v_cas*
  sqrt(CL(f_test)/CL(f_ref)); more flap, more lift, lower control speed.
- Asymmetric yawing moment on the ground roll: N_asym = T_op*y_fail, the
  operating (non-failed) engine thrusts at the signed lateral arm of the
  failed engine. Windmilling drag is neglected in the main model and
  enters only through the optional s_f_cd term of the authority closed
  form.
- Nosewheel steering authority: below the steering cutout speed V_cut
  the steering provides a friction-limited lateral force at the nose
  gear, N_steer = mu_steer*f_nw*W*g0*l_nw, with f_nw the nose gear static
  load fraction (an input, derived by the vehicle-design landing-gear
  layout sibling) and l_nw the CG-to-nose-gear arm. Steering is engaged
  only while V < V_cut (boundary excluded).
- Rudder restoring: N_rud = q*S_v*l_v*C_Lv_delta_r*delta with
  q = 0.5*RHO_SL*V^2 over the ground speed; the required deflection
  delta_req = N_asym/(q*S_v*l_v*C_Lv_delta_r) is capped at delta_r_max.
- Authority-limited ground speed (steering-free): the speed where
  delta_req reaches delta_r_max, q* = T_op*|y_fail|/(S_v*l_v*
  C_Lv_delta_r*delta_r_max_rad - s_f_cd*|y_fail|), V_auth =
  sqrt(2*q*/RHO_SL); None when the denominator is not positive (never
  authority limited).
- Rudder pedal force: F = q*S_r*c_r*|C_h_delta_r|*min(delta_req,
  delta_r_max_rad)*boost_factor/pedal_arm_m, with the boost factor
  scaling felt force (1.0 manual, smaller for power-boosted systems).
- Pedal-force-limited ground speed: q_F = F_lim*pedal_arm/(S_r*c_r*
  |C_h_delta_r|*delta_r_max_rad*boost_factor) with F_lim = 667 N (the
  150 lbf criterion, paraphrased); V_force = sqrt(2*q_F/RHO_SL). It is
  the speed where a full-deflection input demands the 150 lbf limit.
- Run classes: "steering-held" (steering engaged below the cutout,
  practice run, not qualifying), "departed" (steering-free and V <
  V_auth, Vmcg lies above), "at-limit" (steering-free and V_auth <= V <
  V_force, the Vmcg-qualifying class), "with-margin" (steering-free and
  V >= V_force, Vmcg lies at or below).
- Vmcg verdict: vmcg = min of the corrected at-limit run speeds;
  bracket_ok requires the verdict to strictly exceed the fastest
  corrected departed run when present and to not exceed the slowest
  corrected with-margin run when present.
- Stall guard: guard_speed = 1.05*v_s1g from the sibling stall leaf;
  "stall-guard-ok" when Vmcg clears it, else "stall-guard-governs".
  Vmcg/vs1 proximity below 1.10 keeps the guard relevant.
- V1 gate: the balanced-field schedule must place V1 at or above the
  demonstrated Vmcg; v1_required = vmcg when the supplied V1 falls
  short.
- Units are SI: N, m, m/s, rad, deg, N m; knots = m/s * 1.94384.
- FAR/CS 25.149 frames the ground minimum control speed test condition
  (engine failure during the takeoff roll, recovery without nosewheel
  steering, the 150 lbf pedal force criterion); the relations above are
  standard engineering methodology, summary-only.

## Workflow

1. Fix the ground roll configuration and atmosphere: reference takeoff
   weight, reference takeoff flap with the rotation-limit lift
   coefficient model CL(f) = cl_0 + cl_per_deg*f, and the ISA density
   ratio sigma at the test pressure altitude and temperature deviation
   (isa_sigma).
2. Build the engine-out yawing moment on the ground roll from the
   operating-engine thrust at the failed engine lateral arm
   (asym_yaw_moment_static).
3. Apply the nosewheel steering authority below the steering cutout
   speed: steering_engaged tells whether the run is below the cutout and
   steering_moment gives the friction-limited steering restoring moment
   at the nose gear; the steering-held practice runs are set aside from
   the qualifying set.
4. Solve the steering-free rudder authority limited ground speed from
   the closed form (authority_limited_ground_speed), the speed where the
   required rudder deflection (required_deflection) reaches the limit;
   treat None as never authority limited.
5. Solve the pedal-force limited ground speed with the boost factor
   against the 667 N (150 lbf) pedal force criterion
   (force_limited_ground_speed, pedal_force).
6. Correct each run speed to standard conditions and classify the run
   into the steering-held, departed, at-limit and with-margin classes
   (corrected_run_speed, ground_run_class): calibrated airspeed
   correction for TAS runs, weight correction to the reference takeoff
   weight, flap normalization through the rotation-limit lift
   coefficient, class from the measured CAS before corrections.
7. Reduce the qualifying at-limit runs to the Vmcg verdict with the
   bracket consistency check against the departed and with-margin
   brackets (vmcg_verdict): vmcg_cas, vmcg_knots, bracket_ok and the
   run counts.
8. Check the demonstration at the verdict: required deflection below the
   rudder limit, full-deflection pedal force within the 667 N limit with
   the boost factor (force_ok), the authority margin against the
   analytic authority limited ground speed, and apply the stall
   protection guard on the reference stall speed (stall_guard_check)
   against the 1.05 Vs1 guard.
9. Gate the balanced-field V1 schedule against the demonstrated Vmcg
   (v1_gate): v1_gate_met, the vmcg-gated / schedule-infeasible / ok
   verdict and the required V1 speed, and report the liftoff margin
   against the scheduled rotation and liftoff speeds.

## Worked example

Reference takeoff weight 65000 kg at the reference takeoff flap 15 deg
with cl_0 = 1.10 and cl_per_deg = 0.020 (CL_lim 1.400; CL_lim(10) =
1.300). Twin jet on the ground roll: operating engine thrust 55000 N at
the 8.0 m failed engine lateral arm, fin 26 m2 at 16 m with 0.85 per rad
effectiveness, rudder limit 30 deg (0.52360 rad), rudder 8.5 m2 at 1.3 m
chord, hinge moment coefficient 0.045 per rad, pedal arm 0.35 m, boost
factor 0.34, nose gear load fraction 0.09 at mu 0.8 and the 13.0 m arm,
steering cutout 40.0 m/s. vs1 58.0 m/s, scheduled V1 61.5 m/s, vr 63.9
m/s, liftoff speed 66.4 m/s. Real module outputs:

- Atmosphere: isa_sigma(600, +12) = 0.905430 (sqrt 0.951541);
  isa_sigma(600, 0) = 0.943654. tas_to_cas(67.4, 600, 12) = 64.133853.
- Engine-out yawing moment: N_asym = 55000 * 8.0 = 440000.0 N m.
- Authority-limited ground speed: q* = 2376.521775 Pa, V_auth =
  62.289931 m/s (121.081940 kt). Steering-free rudder alone cannot hold
  the airplane below this speed. Windmilling variant (s_f_cd = 1.2 m2):
  V_auth rises to 63.970485 m/s (124.348675 kt), about 1.68 m/s above
  the no-windmilling boundary.
- Pedal-force-limited ground speed: V_force = 65.617205 m/s (127.549642
  kt) boosted and 38.261077 m/s (74.373583 kt) manual; the
  full-deflection pedal force at the authority speed is 601.071429 N
  boosted (within 667 N, force_ok) and 1767.857143 N manual (not ok).
- Nosewheel steering authority: N_steer = 0.8 * 0.09 * 65000 * 9.80665
  * 13.0 = 596636.586 N m, authority ratio 1.355992 against the
  440000 N m asymmetric moment. Cutout at 40.0 m/s (77.753780 kt):
  steering engaged at 36.8 m/s, disengaged at 40.0 (boundary excluded)
  and at 42.0 m/s.
- Corrected runs and classes (all at the 15 deg reference flap, flap
  factor 1.0): R1 37.144469 m/s steering-held (36.8 CAS, 63800 kg,
  steering engaged, practice run); R2 52.400000 departed (52.4 CAS,
  65000 kg); R3 59.056038 departed (58.6 CAS, 64000 kg, weight factor
  1.007782); R4 63.042941 at-limit (62.8 CAS, 64500 kg, factor
  1.003868); R5 64.133853 at-limit (67.4 TAS at 600 m +12 K, 65000 kg,
  the altitude and temperature correction path); R6 67.054921
  with-margin (66.9 CAS, 64700 kg, factor 1.002316); R7 69.500000
  with-margin (69.5 CAS, 65000 kg).
- Vmcg verdict: vmcg_cas = 63.042941 m/s (122.545674 KCAS), the minimum
  of the two qualifying corrected speeds, i.e. run R4 exactly. Brackets:
  v_departed_max 59.056038 below the verdict and v_margin_min 67.054921
  at or above it, so bracket_ok True. Counts: 2 at-limit, 2 departed,
  2 with-margin, 1 steering-held.
- Demonstration checks at the verdict: q = 2434.327597 Pa, delta_req =
  0.511165 rad (29.287617 deg) below the 0.52360 rad limit, pedal force
  601.071429 N within the 667 N limit (force_ok True), authority margin
  vmcg - V_auth = 0.753010 m/s.
- Stall guard: guard_speed = 1.05 * 58 = 60.900000 m/s below the
  verdict, "stall-guard-ok", proximity vmcg/vs1 = 1.086947 below the
  1.10 threshold that keeps the guard relevant.
- Balanced-field V1 gate: V1 61.5 m/s is below Vmcg 63.042941, so
  v1_gate_met False and the verdict is "vmcg-gated" with v1_required =
  63.042941 m/s (122.545674 kt); the legal window against the scheduled
  rotation speed is [63.042941, 63.9], only 0.857059 m/s wide. The
  demonstrated Vmcg forces V1 up by 1.54 m/s into a narrow band below
  rotation, so the ground control limit governs the takeoff speed
  schedule.
- Liftoff margin: v_lof 66.4 clears the verdict by 3.357059 m/s, ratio
  1.053250.
- Manual-rudder variant (boost 1.0): pedal force at the verdict reaches
  1767.857143 N, force_ok False; the power-boosted system (0.34) is
  required to bring the force under the 667 N limit.
- Flap normalization path: a hypothetical 10 deg flap run at 62.9 m/s
  CAS normalizes to 60.611957 m/s at the 15 deg reference (CL 1.300 to
  1.400), a 3.6% speed drop from the extra flap lift.
- Windmilling recheck: with s_f_cd = 1.2 m2, R4 (measured 62.8)
  reclasses from at-limit to departed while R5 (measured 64.134 CAS)
  stays at-limit, so the no-windmilling assumption changes which runs
  qualify.
- Read-off: this airplane demonstrates Vmcg near 122.5 KCAS at MTOW
  conditions. Nosewheel steering carries ground control below the
  77.8 kt cutout; above it the rudder needs 62.3 m/s steering-free and
  the boosted pedal force stays within 150 lbf through the whole regime.

## Verification

- Confirm isa_sigma(0, 0) = 1.0 and isa_sigma(600, 12) = 0.905430 within
  1e-5; every computed aggregate in the contract test is asserted with a
  tolerance (no exact float equality on computed sums).
- Confirm the authority closed form returns V_auth 62.289931 m/s
  (121.081940 kt) and the windmilling variant 63.970485 m/s.
- Confirm the pedal-force family: V_force 65.617205 m/s boosted and
  38.261077 m/s manual, pedal force 601.071429 N boosted and
  1767.857143 N manual against the 667 N limit.
- Confirm steering_moment 596636.586 N m, authority ratio 1.355992, and
  the cutout behavior at 36.8 / 40.0 / 42.0 m/s against V_cut 40.0.
- Confirm vmcg_verdict on the worked seven-run data returns 63.042941
  m/s with bracket_ok True, the corrected run table within 1e-3 per run,
  and the single-sided bracket case stays bracket_ok True.
- Confirm ValueError rejection of non-physical inputs: isa_sigma outside
  [0, 11000] m and at non-positive ambient temperature, zero airspeeds,
  non-positive weights, negative flaps, cl_0 at 0, rudder limit outside
  (0, 60] deg, zero hinge moment coefficient, boost outside (0, 1],
  non-positive steering inputs, empty run lists, lists with no at-limit
  run, and zero speeds in the stall guard and V1 gate.
- Run the contract test offline: python3
  scripts/test_vmcg_determination.py (29 tests, deterministic). It also
  passes under the pre-push hook interpreter
  (~/.pyenv/versions/3.13.12/bin/python3).

## Related leaves

- flight-test-operations/envelope/vmc-determination: the airborne
  minimum control speed demonstration with the windmilling drag
  contribution and the air-side stall protection guard; this leaf owns
  the ground leg only.
- flight-test-operations/envelope/v-speeds: the stall-derived
  certification speed set; Vmcg is not a stall multiple, but the
  scheduled vr and liftoff speeds frame the V1 gate window.
- flight-test-operations/performance/engine-failure-takeoff-flight-test:
  derives the balanced-field V1; this leaf only gates the supplied
  schedule against the demonstrated Vmcg.
- flight-test-operations/performance/takeoff-distance-determination:
  the all-engines ground roll and obstacle distance, downstream of the
  control speed verdict.
- flight-test-operations/performance/stall-speed-determination:
  supplies the takeoff-configuration reference stall speed Vs1 for the
  stall protection guard.
- flight-test-operations/performance/accelerate-stop-distance: the
  rejected takeoff stop that must begin above Vmcg.
- flight-test-operations/envelope/vmu-determination: the takeoff
  rotation runs and the minimum unstick speed, an in-air rotation
  boundary without engine failure content.
- vehicle-design/sizing/landing-gear-layout: derives the nose gear load
  fraction band and the steering geometry context consumed as inputs
  here.

## Pitfalls

- Qualifying steering-held runs: a run held with the nosewheel steering
  engaged below the cutout is a practice run, never qualifying; the
  Vmcg verdict must come only from steering-free at-limit evidence.
- Feeding a TAS value as CAS: a true airspeed run at altitude must be
  converted through the ISA density ratio before the corrections; using
  67.4 TAS as CAS at 600 m +12 K overstates the run by 3.27 m/s (64.134
  CAS is the real value).
- Neglecting the windmilling shift of the authority boundary: the
  s_f_cd 1.2 m2 variant moves V_auth from 62.289931 to 63.970485 m/s
  and reclasses a marginal at-limit run (R4 measured 62.8 flips to
  departed), so the no-windmilling model understates the boundary by
  about 1.68 m/s.
- Misreading the class boundaries: runs below V_auth are departed (Vmcg
  lies above them), V_auth itself is at-limit (boundary included) and
  V_force itself is with-margin; classifying on the corrected speed
  instead of the measured CAS shifts the bracket.
- Reporting the manual-rudder variant as clearing: at boost 1.0 the
  full-deflection pedal force at the verdict reaches 1767.857143 N,
  above the 667 N limit; only the power-boosted system (0.34) brings it
  under the criterion.
- Scheduling V1 below the demonstrated Vmcg: the balanced-field
  schedule must sit at or above Vmcg (v1_required 63.042941 m/s in the
  worked data), inside the window below the rotation speed; this leaf
  checks the supplied V1, it never derives V1.
- Confusing Vmcg with the airborne Vmc: this leaf reduces the engine-
  failure ground roll demonstration with the nosewheel steering cutout
  and the steering-free rudder balance; the airborne demonstration with
  the windmilling drag is the vmc-determination sibling, and the
  all-engines roll and distances belong to the takeoff distance leaf.

## Behavior contract (gate 3)

Run the deterministic contract test (stdlib unittest, offline):

    python3 scripts/test_vmcg_determination.py

The test covers the ISA atmosphere anchors and rejection range, the TAS
to CAS conversion, the weight correction factors and degeneracies, the
flap normalization anchor and round trip, the full correction chain on
the TAS run, the engine-out yawing moment, the authority-limited and
force-limited ground speed closed forms against the worked anchors
(62.289931 and 65.617205 m/s), the required deflection and pedal force
family (601.071429 N boosted, 1767.857143 N manual) against the 667 N
limit, the nosewheel steering moment and the cutout engagement, the four
run class boundary strings, the seven-run Vmcg verdict with the bracket
consistency checks and counts, the stall protection guard verdicts, the
V1 gate vmcg-gated / ok / schedule-infeasible cases, the liftoff margin,
the windmilling reclassification of the runs, the module constants, and
ValueError rejection of every non-physical input.

## Compliance

- Standards referenced, not reproduced: FAR/CS 25.149 (14 CFR Part 25
  and CS-25) frames the ground minimum control speed test condition and
  its 150 lbf pedal force criterion; the relations above are standard
  engineering methodology, summary-only per standards-map.yaml.
- compliance: STANDARDS-REF, gated: false.
