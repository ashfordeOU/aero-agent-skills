# Wave-44 leaf spec: vmcg-determination (flight-test-operations,
# envelope pack)

- Path: skills/flight-test-operations/envelope/vmcg-determination/
- Pack: envelope (present siblings envelope-expansion, v-speeds,
  load-factor-envelope, stall-characteristics-testing,
  flight-loads-survey, structural-coupling-test, high-angle-of-attack-
  testing, spin-testing, icing-flight-test, buffet-boundary-testing,
  vmc-determination, vmu-determination; adjacent fences in
  flight-test-operations/performance (stall-speed-determination,
  takeoff-distance-determination, accelerate-stop-distance,
  engine-failure-takeoff-flight-test) and in vehicle-design/sizing
  (landing-gear-layout)).
- Claim fences (quoted from the sibling frontmatter at prep, none owns
  the ground minimum control speed reduction of the engine-failure
  ground roll runs):
  - vmc-determination (this pack) owns the minimum control AIR speed,
    the FAR/CS 25.149 airborne demonstration: its description reads
    "identify the critical engine from the engine-out yawing moment
    geometry, build the asymmetric yawing moment from the
    operating-engine thrust at the failed engine lateral arm plus the
    windmilling drag contribution, solve the rudder authority limited
    speed, apply the rudder pedal force criterion with the boost factor
    against the 150 lbf pedal limit, and apply the stall protection
    guard on the reference stall speed", and its whole SKILL.md body
    contains zero mentions of the ground roll, Vmcg, steering or the
    nosewheel (whole-body grep count at prep: 0 for
    ground|vmcg|steer|nosewheel). The new leaf parallels its reduction
    structure (run inputs, per-run checks, standard-condition verdict)
    and its 150 lbf pedal-force criterion family with the boost factor,
    but the governing surface is the GROUND roll of FAR/CS 25.149
    (nosewheel steering cutout, runway-edge deviation, steering-free
    recovery), not the airborne demonstration.
  - engine-failure-takeoff-flight-test (performance, this family) owns
    the balanced-field decision speed V1: its description reads "locate
    the engine failure point in the measured ground run at the failure
    speed VEF, add the V1 recognition time segment, integrate the
    continued takeoff to the 35 ft obstacle at the measured engine out
    climb rate, and set the decision speed V1 at the balanced field
    intersection where the stop distance curve equals the continued
    engine out takeoff distance curve". It integrates DISTANCE along
    the roll; it has no directional-control function, no steering or
    rudder balance and no control-speed verdict. The new leaf gates the
    V1 schedule by the demonstrated Vmcg but does not compute VEF, V1,
    or any stop or takeoff distance.
  - takeoff-distance-determination (performance, this family) covers
    the all-engines ground roll and the 35-ft obstacle distance: its
    description reads "integrate the measured ground speed samples over
    the ground roll, add the rotation distance at the rotation speed,
    and close the airborne climb segment to the 35 ft obstacle height
    with the climb rate". No directional control, no failure condition,
    no control-speed verdict; it consumes speeds instead of producing
    one.
  - v-speeds (this pack) computes the certification speed SET from
    stall speeds: vr is 1.1 times vs1, vref 1.3 times vs0, v2 1.2
    times vs1, with the vno/vne guard. Vmcg is not a stall multiple;
    the new leaf consumes the scheduled vr and liftoff speed as margin
    context only.
  - stall-speed-determination (performance, this family) computes Vs1g
    from wing loading and weight; it supplies the reference Vs1 input
    used in the stall guard check here, it does not touch ground
    control.
  - accelerate-stop-distance (performance, this family) owns the
    rejected takeoff stop from V1 with the braking deceleration; the
    new leaf checks V1 against Vmcg but does not compute the stop.
  - vmu-determination (this pack, wave 43) reduces the takeoff rotation
    runs to the FAR/CS 25.107(b) minimum unstick speed at the
    tail-strike rotation limit; an in-air rotation boundary at liftoff,
    no engine failure, no ground-roll directional content.
  - landing-gear-layout (vehicle-design/sizing) owns the nose gear load
    fraction band across the CG travel and the steering GEOMETRY
    context: its description reads "compute the tipback angle at the
    aft CG limit about the main gear contact, the tail strike clearance
    angle at rotation, the lateral turnover angle from the wheel track
    at the forward CG limit, and the nose gear load fraction band
    across the CG travel". The load fraction band is theirs; the new
    leaf CONSUMES a nose gear load fraction value as an input parameter
    of the steering authority model and does not derive it.
  Whole-tree greps at prep: "vmcg|vmcl|ground-minimum-control" returns
  0 matches in skills/ and 0 matches in eval/ (grep -l empty, grep -c
  0 per token across eval/hit1-corpus.yaml and every eval/*.yaml
  fragment); the corpus tokens vmcg-determination,
  ground-minimum-control-speed and nosewheel-steering-authority return
  0 hits in eval/hit1-corpus.yaml; the word "nosewheel" appears nowhere
  in the skills tree. GENUINE flight-test-operations gap (probe receipt
  verified zero-owner, GO): no leaf reduces the engine-failure ground
  roll demonstration runs to the FAR/CS 25.149 ground minimum control
  speed Vmcg.
- Standards id: far-25 (14 CFR Part 25: Airworthiness Standards for
  Transport Category Airplanes) and cs-25 (CS-25: Certification
  Specifications and Acceptable Means of Compliance for Large
  Aeroplanes), both reference-only and both present in
  standards-map.yaml (gated false). Ledger Standard: far-25, cs-25.
- Family: flight-test-operations

## Claim

Reduce the engine-failure ground roll demonstration runs of a transport
airplane flight test to the ground minimum control speed Vmcg in the
spirit of the FAR/CS 25.149 ground leg method, summary-only. Build the
asymmetric yawing moment from the operating-engine thrust at the failed
engine lateral arm (the critical engine fails suddenly during the
takeoff roll; the windmilling drag of the failed engine is neglected at
ground roll speeds in the main model and carried as an optional
variant). Apply the nosewheel steering authority: below the steering
cutout speed the steering provides a friction-limited lateral force at
the nose gear with a constant restoring moment, and a run held with the
steering engaged is a steering-held practice run; above the cutout the
airplane is steering-free and the rudder aerodynamics must carry the
recovery. Solve the steering-free authority-limited ground speed where
the required rudder deflection reaches the limit and the 150 lbf
pedal-force-limited ground speed with the boost factor (the speed where
a full-deflection input demands the 667 N limit, 150 lbf criterion
paraphrased). Per ground roll run, take the measured failure speed
(calibrated airspeed by default, true airspeed accepted) at the test
gross weight, test pressure altitude, ISA temperature deviation and
flap setting, then classify the run: departed when steering-free
control was lost below the authority-limited ground speed (Vmcg lies
above this run), at-limit when steering-free control was held with the
rudder at its limit (the Vmcg-qualifying class), with-margin when
steering-free control was held with the rudder deflection to spare
(Vmcg lies at or below this run), and steering-held when the nosewheel
steering carried the recovery (practice run, not qualifying). Correct
every run speed to standard conditions: true to calibrated airspeed
through the ISA density ratio sigma at the test altitude and
temperature deviation, weight correction v*sqrt(w_ref/w_test) to the
reference takeoff weight, and configuration normalization to the
reference takeoff flap through the rotation-limit lift coefficient
CL(f) = cl_0 + cl_per_deg*f. Issue the Vmcg verdict as the minimum of
the corrected at-limit run speeds, in m/s and knots, with the bracket
consistency check against the fastest departed and the slowest
with-margin runs. Check the demonstration at the verdict: required
deflection below the rudder limit, full-deflection pedal force within
the 667 N limit with the boost factor (force_ok), and the authority
margin against the analytic authority-limited ground speed. Apply the
stall protection guard on the reference stall speed (1.05*Vs1, where
Vs1 is the takeoff-configuration reference stall speed supplied by the
sibling stall-speed-determination leaf) and gate the balanced-field V1
schedule: report whether the scheduled V1 clears the demonstrated Vmcg
and output the required V1 speed when it falls short. Does NOT do: the
airborne Vmc demonstration with the windmilling contribution and the
stall-protection guard on the air minimum control speed
(vmc-determination); VEF, the recognition segment, the balanced-field
V1 intersection or the 35-ft obstacle distances (engine-failure-
takeoff-flight-test); the all-engines ground roll or takeoff distance
(takeoff-distance-determination); the stall-derived vref/v2/vr set
(v-speeds); Vs1g from wing loading (stall-speed-determination); the
rejected takeoff stop (accelerate-stop-distance); the unstick rotation
verdict of the takeoff rotation runs (vmu-determination); the nose gear
load fraction band or the steering geometry (landing-gear-layout).
Steering-free reductions only for the qualifying verdict; steering-
engaged runs are practice evidence. The nosewheel steering is modeled
as a friction-limited lateral force at the nose gear active only below
the cutout speed; differential braking, dynamic ground-roll transients,
sideslip coupling and ground-effect aerodynamics beyond the sigma
density correction are out of scope. Single-layer ISA to 11 km only.

## Model (implement exactly)

Pure stdlib, math only, closed form. Module constants: RHO_SL = 1.225
kg/m3, T0 = 288.15 K, LAPSE = 0.0065 K/m, G0 = 9.80665 m/s2, R_AIR =
287.05 J/(kg K), EXP = G0/(R_AIR*LAPSE) (about 5.2559, the ISA pressure
exponent), KT2MS = 0.514444444444 m/s per knot (1852/3600), F_LIM =
667.0 N (the 150 lbf pedal force criterion of the test condition,
paraphrased). KT2MS appears only to quote the verdict in knots; every
speed verdict is a CAS m/s value at reference conditions.

Defining relations (pin these exactly; every function below derives
from them):
- ISA density ratio at pressure altitude h_p with temperature
  deviation dt_isa: delta = (1 - LAPSE*h_p/T0)**EXP, theta = (T0 -
  LAPSE*h_p + dt_isa)/T0, sigma = delta/theta. At 600 m with a +12 K
  warm day the real anchor sigma = 0.905430, sqrt(sigma) = 0.951541.
- TAS to CAS: v_cas = v_tas*sqrt(sigma); CAS input needs no density
  correction because calibrated airspeed already collapses it.
- Weight correction at fixed lift coefficient: v_corr = v_cas*
  sqrt(w_ref/w_test) (CAS scaling, the standard V-speed reduction).
- Configuration normalization through the rotation-limit lift
  coefficient CL(f) = cl_0 + cl_per_deg*f: v_norm = v_cas*
  sqrt(CL(f_test)/CL(f_ref)); more flap, more lift, lower control
  speed, so speeds measured at a lower flap setting rise when
  normalized up to the reference flap.
- Asymmetric yawing moment on the ground roll: N_asym = T_op*y_fail,
  the sum of the operating (non-failed) engine thrusts at the signed
  lateral arm of the failed engine. Windmilling drag of the failed
  engine is neglected in the main model (small at ground roll speeds)
  and enters only through the optional s_f_cd term of the authority
  closed form.
- Nosewheel steering authority: below the steering cutout speed V_cut
  the steering provides a friction-limited lateral force at the nose
  gear, N_steer = mu_steer*f_nw*W*g0*l_nw, where f_nw is the nose gear
  static load fraction (consumed as an input, derived by the
  vehicle-design landing-gear-layout sibling), mu_steer the lateral
  friction coefficient, W the gross weight in kg and l_nw the
  CG-to-nose-gear arm. Steering is engaged only while V < V_cut
  (boundary excluded); the qualifying Vmcg determination is
  steering-free.
- Rudder restoring: N_rud = q*S_v*l_v*C_Lv_delta_r*delta, with q =
  0.5*RHO_SL*V^2 over the ground speed, S_v the fin area, l_v the
  CG-to-fin arm and C_Lv_delta_r the effective fin lift slope per
  rudder deflection. Required deflection delta_req = N_asym/(q*S_v*l_v
  *C_Lv_delta_r), capped at delta_r_max.
- Rudder-authority limited ground speed (steering-free): the speed
  where delta_req reaches delta_r_max. Closed form q* = T_op*|y_fail|
  / (S_v*l_v*C_Lv_delta_r*delta_r_max_rad - s_f_cd*|y_fail|); V_auth =
  sqrt(2*q*/RHO_SL). If the denominator is not positive the
  configuration is never authority limited (V_auth = None).
- Rudder pedal force: F = q*S_r*c_r*|C_h_delta_r|*min(delta_req,
  delta_r_max_rad)*boost_factor/pedal_arm_m, with C_h_delta_r the hinge
  moment coefficient per radian (magnitude used), S_r and c_r the
  rudder area and chord, and the boost factor scaling felt force (1.0
  manual, smaller for power-boosted systems).
- Pedal-force limit: F_lim = 667 N (150 lbf criterion of the test
  condition, paraphrased). The pedal-force-limited ground speed V_force
  follows from the full-deflection quadratic F(V) at the deflection
  limit, q_F = F_lim*pedal_arm/(S_r*c_r*|C_h_delta_r|*delta_r_max_rad*
  boost_factor), V_force = sqrt(2*q_F/RHO_SL). It is the speed at
  which a full-deflection rudder input demands the 150 lbf limit; at
  the Vmcg verdict the required (not full) deflection force is checked
  against it.
- Run classes (from the measured CAS and the steering state):
  "steering-held" when the steering is engaged (only possible below the
  cutout; practice run, not qualifying), "departed" when steering-free
  and V < V_auth (Vmcg lies above this run), "at-limit" when
  steering-free and V_auth <= V < V_force (the Vmcg-qualifying class),
  "with-margin" when steering-free and V >= V_force (Vmcg lies at or
  below this run).
- Vmcg verdict: vmcg = min of the corrected at-limit run speeds;
  bracket_ok requires the verdict to strictly exceed the fastest
  corrected departed run when present and to not exceed the slowest
  corrected with-margin run when present.
- Stall guard: guard_speed = 1.05*v_s1g from the sibling stall leaf;
  guard verdict "stall-guard-ok" when Vmcg clears it, else
  "stall-guard-governs". Vmcg/vs1 proximity below 1.10 keeps the guard
  relevant.
- V1 gate: the balanced-field schedule must place V1 at or above the
  demonstrated Vmcg; v1_required = vmcg when the supplied V1 falls
  short.
- Units are SI: N, m, m/s, rad, deg, N m; knots = m/s * 1.94384
  (1/KT2MS).
- FAR/CS 25.149 frames the ground minimum control speed test condition
  (engine failure during the takeoff roll, recovery without nosewheel
  steering, the 150 lbf pedal force criterion); the relations above are
  standard engineering methodology, summary-only.

Functions:
- isa_sigma(h_p, dt_isa = 0.0) -> float
  delta/theta of the single-layer standard atmosphere, closed form.
  ValueError if h_p outside [0, 11000] m or the actual ambient
  temperature (T0 - LAPSE*h_p + dt_isa) is not positive.
- tas_to_cas(v_tas, h_p, dt_isa = 0.0) -> float
  v_tas*sqrt(isa_sigma(h_p, dt_isa)). ValueError if v_tas <= 0.
  Degenerates to v_tas at sea level standard conditions.
- weight_corrected_speed(v_cas, w_test, w_ref) -> float
  v_cas*sqrt(w_ref/w_test). ValueError if v_cas <= 0 or either weight
  <= 0. Returns v_cas unchanged when w_test == w_ref.
- flap_normalized_speed(v_cas, flap_test, flap_ref, cl_0, cl_per_deg)
  -> float
  v_cas*sqrt((cl_0 + cl_per_deg*flap_test)/(cl_0 + cl_per_deg*
  flap_ref)). ValueError if v_cas <= 0, either flap negative, cl_0 <=
  0, cl_per_deg < 0, or the lift coefficient at either flap setting is
  not positive. Returns v_cas unchanged when flap_test == flap_ref.
- corrected_run_speed(v_meas, w_test, w_ref, flap_test, flap_ref,
  cl_0, cl_per_deg, h_p = 0.0, dt_isa = 0.0, tas_input = False) ->
  float
  the full standard-condition reduction of one measured failure speed:
  tas_to_cas first when tas_input (CAS input is used directly), then
  weight_corrected_speed, then flap_normalized_speed. ValueError if
  v_meas <= 0 (CAS path) or any argument fails its sub-check.
- asym_yaw_moment_static(t_op, y_fail) -> float
  the engine-out yawing moment on the ground roll, t_op*|y_fail|.
  ValueError if t_op <= 0 or y_fail <= 0.
- authority_limited_ground_speed(t_op, y_fail, s_v, l_v,
  c_lv_delta_r, delta_max_rad, s_f_cd = 0.0) -> float or None
  the steering-free authority limit over the ground speed from the
  closed form; None when the denominator is not positive (never
  authority limited). ValueError if t_op, y_fail, s_v or l_v <= 0,
  c_lv_delta_r <= 0, delta_r_max outside (0, 60] deg, or s_f_cd < 0.
- required_deflection(n_asym, q, s_v, l_v, c_lv_delta_r) -> float
  n_asym/(q*s_v*l_v*c_lv_delta_r). ValueError if n_asym <= 0 or q <= 0.
- pedal_force(q, s_r, c_r, c_h_delta_r, delta_used, boost, pedal_arm)
  -> float
  q*s_r*c_r*|c_h_delta_r|*delta_used*boost/pedal_arm. ValueError if q
  <= 0, delta_used <= 0, boost outside (0, 1], pedal_arm <= 0, or
  c_h_delta_r == 0.
- force_limited_ground_speed(f_lim, pedal_arm, s_r, c_r, c_h_delta_r,
  delta_max_rad, boost) -> float
  the ground speed where a full-deflection input demands the pedal
  force limit, from q_F = f_lim*pedal_arm/(s_r*c_r*|c_h_delta_r|*
  delta_max_rad*boost). ValueErrors as in pedal_force.
- steering_moment(w_kg, f_nw, mu_steer, l_nw) -> float
  mu_steer*f_nw*w_kg*g0*l_nw, the friction-limited steering restoring
  moment below the cutout. ValueError if any input <= 0.
- steering_engaged(v_ground, v_cut) -> bool
  v_ground < v_cut (cutout boundary excluded). ValueError if
  v_ground < 0 or v_cut <= 0.
- ground_run_class(steering_on, v_ef_cas, v_auth, v_force) -> str
  the four class strings exactly as spec'd above; steering_on implies
  "steering-held" (the caller only passes it below the cutout).
  ValueError if v_ef_cas <= 0 or v_auth or v_force is None/<= 0.
- vmcg_verdict(runs, v_auth, v_force, w_ref, flap_ref, cl_0,
  cl_per_deg) -> dict
  reduces the run list. Each run dict: id, speed (m/s, CAS or TAS by
  tas_input), weight (kg), flap (deg), steering_on (bool), h_p (m),
  dt_isa (K), tas_input (bool, default False). Per run computes the
  corrected speed and the class (class from the measured CAS, TAS
  converted first, before corrections); vmcg_cas = min of the
  corrected at-limit speeds; vmcg_knots = vmcg_cas/KT2MS; reports
  v_departed_max and v_margin_min (None when a bracket is empty),
  bracket_ok (True only when the verdict strictly exceeds the departed
  max when present and does not exceed the margin min when present),
  n_qualifying, n_departed, n_margin, n_steering_held. ValueError if
  runs is empty or no run classifies as at-limit (Vmcg not defined by
  the data).
- stall_guard_check(vmcg_cas, vs1, guard_factor = 1.05) -> dict
  guard_speed = 1.05*vs1, guard verdict "stall-guard-ok" or
  "stall-guard-governs", and the proximity ratio vmcg/vs1. ValueError
  if either speed <= 0.
- v1_gate(vmcg_cas, v1_cas, vr_cas = None) -> dict
  the balanced-field V1 gate: v1_gate_met = v1 >= vmcg; when not met,
  verdict "vmcg-gated" with v1_required = vmcg, or
  "schedule-infeasible" when a vr is supplied and vr < vmcg (no legal
  V1 below the rotation speed exists); when met, verdict "ok". With vr
  supplied, reports the legal window [vmcg, vr] and its width. This
  leaf only CHECKS a supplied V1; it never derives V1 (that is the
  engine-failure-takeoff-flight-test computation).

Identities to test (closed form, exact):
- isa_sigma(0, 0) == 1.0 exactly and tas_to_cas(v, 0, 0) == v exactly;
  sigma falls with warm-day altitude: sigma(600, +12) < sigma(600, 0)
  < 1 (real anchor 0.905430 vs 0.943654, sqrt 0.951541).
- Same-weight and same-flap degeneracy:
  weight_corrected_speed(v, w, w) == v and flap_normalized_speed(v, f,
  f, cl_0, cl_per_deg) == v exactly.
- Weight sqrt scaling: weight_corrected_speed(v, w, 4*w) == 2*v
  exactly (real anchor 120.000000 from 60.0).
- Flap normalization round trip:
  flap_normalized_speed(flap_normalized_speed(v, f1, f2, ...), f2,
  f1, ...) == v within 1e-9 and the normalization direction is
  correct: a speed measured at the lower flap setting 10 deg rises
  when normalized to 15 deg (real anchor 60.611957 from 62.9, CL
  1.300 to 1.400).
- Reduction chain: corrected_run_speed with tas_input True equals
  weight_corrected_speed(tas_to_cas(v, h, dt), w, w_ref) when the flap
  factor is 1.0 (real anchor 64.133853 on the R5 side, the TAS run at
  600 m +12 K).
- Asymmetric moment: asym_yaw_moment_static(55000, 8.0) == 440000.0
  exactly; the authority closed form reproduces V_auth 62.289931 m/s
  (121.081940 kt) and rises to 63.970485 m/s with s_f_cd = 1.2 m2.
- Pedal-force family: force_limited_ground_speed boosted (b = 0.34)
  65.617205 m/s (127.549642 kt) and manual (b = 1.0) 38.261077 m/s
  (74.373583 kt); the full-deflection pedal force at the authority
  speed is 601.071429 N boosted (force_ok True) and 1767.857143 N
  manual (force_ok False).
- Steering: steering_moment(65000, 0.09, 0.8, 13.0) = 596636.586 N m,
  steering authority ratio N_steer/N_asym = 1.355992; steering_engaged
  True at 36.8 m/s and False at 40.0 m/s (boundary excluded) and at
  42.0 m/s.
- Class boundaries: v_auth itself is at-limit (boundary included),
  v_force itself is with-margin, v_auth - 0.01 is departed, and a
  steering-engaged run below the cutout is steering-held; the four
  class strings are exactly the spec strings.
- Verdict minimum: vmcg_cas equals the corrected speed of the slowest
  qualifying run; in the worked data vmcg = run R4's corrected speed
  (63.042941) exactly, since R4 is the minimum of the two at-limit
  runs (63.042941 and 64.133853).
- Bracket logic: bracket_ok True with v_departed_max 59.056038 <
  vmcg 63.042941 <= v_margin_min 67.054921 in the worked data;
  removing the with-margin runs keeps bracket_ok True (single-sided
  brackets allowed) while a qualifying verdict below the departed max
  flips it False.
- At-verdict check: q = 2434.327597 Pa, delta_req = 0.511165 rad
  (29.287617 deg) below the 0.52360 rad limit, pedal force 601.071429
  N within the 667 N limit, authority margin vmcg - V_auth =
  0.753010 m/s.
- Stall guard: guard_speed 60.9 m/s at vs1 58.0 clears the verdict,
  guard verdict "stall-guard-ok", proximity vmcg/vs1 = 1.086947 below
  the 1.10 threshold that keeps the stall guard relevant.
- V1 gate: v1 61.5 below vmcg gives v1_gate_met False, v1_required =
  63.042941 m/s (122.545674 kt), verdict "vmcg-gated" and the legal
  window [63.042941, 63.9] width 0.857059 m/s against the scheduled
  vr; vr below vmcg gives "schedule-infeasible"; v1 at or above vmcg
  gives "ok".
- Liftoff margin: V_LOF - vmcg = 3.357059 m/s, ratio V_LOF/vmcg =
  1.053250.
- Manual-rudder variant: pedal force at the verdict 1767.857143 N
  exceeds the 667 N limit, force_ok False, the flight test cannot
  clear with the unboosted rudder.
- Windmilling shift: with s_f_cd = 1.2 m2 the authority speed rises to
  63.970485 m/s, so the R4 run (measured 62.8 m/s) reclasses from
  at-limit to departed while R5 (measured 64.134) stays at-limit.
- ValueErrors across the module: isa_sigma at h_p -1 and 12000 and at
  a non-positive ambient temperature; tas_to_cas at v_tas 0;
  weight_corrected_speed at w_test 0; flap_normalized_speed at a
  negative flap; authority_limited_ground_speed at delta_max 61 deg;
  vmcg_verdict on an empty list and on a list with no at-limit run;
  v1_gate at zero speeds.
- Determinism; no imports beyond math; constants fixed (EXP about
  5.2559, KT2MS 0.514444444444, F_LIM 667.0).

## Worked example

Reference takeoff weight w_ref = 65000 kg, reference takeoff flap
flap_ref = 15.0 deg with cl_0 = 1.10 and cl_per_deg = 0.020 per deg
(CL_lim(15) = 1.400, CL_lim(10) = 1.300). Twin jet on the ground roll:
operating engine thrust at the failure moment T_op = 55000 N at the
failed engine lateral arm y_fail = 8.0 m (N_asym = 440000 N m), fin
S_v = 26 m2, l_v = 16 m, C_Lv_delta_r = 0.85 per rad, rudder limit 30
deg (0.52360 rad), rudder S_r = 8.5 m2, c_r = 1.3 m, C_h_delta_r
0.045 per rad, pedal arm 0.35 m, boost factor 0.34 (power-boosted),
nose gear load fraction f_nw = 0.09 with mu_steer = 0.8 on dry runway
at the CG-to-nose-gear arm l_nw = 13.0 m, steering cutout V_cut = 40.0
m/s. The takeoff-configuration stall speed from the sibling leaf is
vs1 = 58.0 m/s, the scheduled balanced-field V1 is 61.5 m/s, the
scheduled rotation speed is vr = 63.9 m/s and the scheduled liftoff
speed is v_lof = 66.4 m/s. All values below are REAL outputs of the
prep anchor /tmp/w44spec/anchor_vmcg.py (stdlib math, closed form).
- Atmosphere: isa_sigma(600, +12) = 0.905430, sqrt(sigma) = 0.951541;
  isa_sigma(600, 0) = 0.943654; isa_sigma(0, 0) = 1.000000. The warm
  day at 600 m is about 5% less dense than sea level standard.
  tas_to_cas(67.4, 600, 12) = 64.133853 m/s.
- Analytic ground limits (windmilling neglected):
  - Asymmetric yawing moment N_asym = 55000 * 8.0 = 440000.0 N m.
  - Authority-limited ground speed: q* = 2376.521775 Pa, V_auth =
    62.289931 m/s = 121.081940 kt. Steering-free rudder alone cannot
    hold the airplane below this speed.
  - Pedal-force-limited ground speed: q_F at full deflection and the
    667 N limit gives V_force = 65.617205 m/s = 127.549642 kt boosted
    (b = 0.34) and 38.261077 m/s = 74.373583 kt manual (b = 1.0).
  - Full-deflection pedal force at the authority speed: 601.071429 N
    boosted (within the 667 N limit, force_ok True) and 1767.857143 N
    manual (force_ok False).
  - Windmilling variant (s_f_cd = 1.2 m2): the denominator shrinks and
    V_auth rises to 63.970485 m/s = 124.348675 kt, so the
    no-windmilling assumption understates the boundary by about 1.68
    m/s.
- Nosewheel steering authority: N_steer = 0.8 * 0.09 * 65000 * 9.80665
  * 13.0 = 596636.586 N m, an authority ratio of 1.355992 against the
  440000 N m asymmetric moment; the steering out-moments the failed
  engine by more than a third below the cutout. The cutout sits at
  40.0 m/s (77.753780 kt): steering engaged at 36.8 m/s, disengaged at
  40.0 m/s (boundary excluded) and at 42.0 m/s. Between the cutout and
  V_auth (40 to 62.3 m/s) the airplane is steering-free and below
  aerodynamic control, the departed-run band.
- Per-run classes and corrections (all runs at flap 15 deg, so the
  flap factor is 1.0 in the verdict data):
  - R1: v 36.8 m/s CAS, 63800 kg -> corrected 37.144469 m/s,
    steering-held (below the cutout with the steering engaged, a
    practice run; not qualifying).
  - R2: v 52.4 m/s CAS, 65000 kg -> corrected 52.400000 m/s, departed
    (steering-free at 52.4 < 62.29, control lost; Vmcg lies above).
  - R3: v 58.6 m/s CAS, 64000 kg -> corrected 59.056038 m/s, departed
    (weight factor sqrt(65000/64000) = 1.007782 pulls the light-run
    speed up).
  - R4: v 62.8 m/s CAS, 64500 kg -> corrected 63.042941 m/s,
    at-limit (62.8 in [62.29, 65.62); the qualifying class; weight
    factor sqrt(65000/64500) = 1.003868).
  - R5: v 67.4 m/s TRUE airspeed (tas_input) at 600 m, +12 K, 65000
    kg: TAS to CAS 64.133853 m/s, corrected 64.133853 m/s, at-limit
    (64.134 < 65.617). Demonstrates the altitude and temperature
    correction path on a warm-day run.
  - R6: v 66.9 m/s CAS, 64700 kg -> corrected 67.054921 m/s,
    with-margin (66.9 >= 65.617; weight factor sqrt(65000/64700) =
    1.002316).
  - R7: v 69.5 m/s CAS, 65000 kg -> corrected 69.500000 m/s,
    with-margin.
- Vmcg verdict: vmcg_cas = 63.042941 m/s, the minimum of the two
  qualifying corrected speeds (63.042941, 64.133853), i.e. run R4
  exactly; vmcg_knots = 122.545674 KCAS. Brackets: v_departed_max =
  59.056038 m/s below the verdict and v_margin_min = 67.054921 m/s at
  or above it, so bracket_ok = True and the verdict is bracketed by
  real run evidence: the airplane lost steering-free control at 59.06
  m/s, held with the rudder at its limit at 63.04 m/s, and held with
  deflection to spare by 67.05 m/s. Counts: 2 at-limit, 2 departed, 2
  with-margin, 1 steering-held.
- Demonstration checks at the verdict: q = 2434.327597 Pa, required
  deflection delta_req = 0.511165 rad (29.287617 deg) below the
  0.52360 rad limit, pedal force = 601.071429 N within the 667 N
  limit (force_ok True), and the authority margin vmcg - V_auth =
  0.753010 m/s above the analytic boundary.
- Stall guard (vs1 = 58.0 m/s): guard speed 1.05 * 58 = 60.900000 m/s
  below the verdict, guard_verdict "stall-guard-ok"; proximity
  vmcg/vs1 = 1.086947, below the 1.10 threshold that keeps the stall
  guard relevant.
- Balanced-field V1 gate (v1 = 61.5 m/s): v1 61.5 is BELOW vmcg
  63.042941, so v1_gate_met = False and the gate verdict is
  "vmcg-gated": v1_required = 63.042941 m/s (122.545674 kt). The
  legal window against the scheduled rotation speed is
  [63.042941, 63.9], only 0.857059 m/s wide: the demonstrated Vmcg
  forces the decision speed up by 1.54 m/s into a narrow band below
  rotation.
- Liftoff margin: v_lof 66.4 clears the verdict by 3.357059 m/s,
  ratio v_lof/vmcg = 1.053250.
- Manual-rudder variant (b = 1.0): pedal force at the verdict reaches
  1767.857143 N, force_ok False and the flight test cannot clear; the
  power-boosted system (b = 0.34) is required to bring the
  full-deflection force under the 667 N limit.
- Windmilling recheck: with s_f_cd = 1.2 m2 the authority speed rises
  to 63.970485 m/s and the R4 run (measured 62.8) reclasses to
  departed while R5 (measured 64.134) stays at-limit, so the
  no-windmilling assumption changes which runs qualify.
- Read-off: this airplane demonstrates Vmcg near 122.5 KCAS at MTOW
  conditions. Nosewheel steering carries ground control below the
  77.8 kt cutout; above it the rudder needs 62.3 m/s (121.1 kt)
  steering-free, and the boosted pedal force stays within 150 lbf
  through the whole regime. The balanced field cannot legally schedule
  V1 = 61.5 m/s: the Vmcg verdict forces V1 up to 63.04 m/s, into a
  0.86 m/s window below the 63.9 m/s rotation speed, so the
  ground-control limit governs the takeoff speed schedule. The flap
  normalization path is shown separately: a hypothetical run at 10 deg
  flap with v = 62.9 m/s CAS would normalize to 60.611957 m/s at the
  15 deg reference (CL 1.300 to 1.400), a 3.6% speed drop from the
  extra flap lift.
Run your module and take the real outputs as assert targets; the
anchors above are real prep outputs of /tmp/w44spec/anchor_vmcg.py
(stdlib math, closed form, exit 0).

## Validation list (contract test must include)

- isa_sigma(0, 0) = 1.0 within 1e-12; isa_sigma(600, 12) = 0.905430
  within 1e-5 and below isa_sigma(600, 0) = 0.943654;
  tas_to_cas(67.4, 600, 12) = 64.133853 within 1e-3; tas_to_cas(v, 0,
  0) = v within 1e-12.
- weight_corrected_speed(60.0, w, 4*w) = 120.0 within 1e-9;
  weight factors sqrt(65000/64000) = 1.007782, sqrt(65000/64500) =
  1.003868 and sqrt(65000/64700) = 1.002316 within 1e-6; same-weight
  call returns the input within 1e-12.
- flap_normalized_speed(62.9, 10, 15, 1.10, 0.020) = 60.611957 within
  1e-3 (CL 1.300 to 1.400); same-flap call returns the input; the
  10-to-15-to-10 round trip returns 62.9 within 1e-9; negative flap
  and cl_0 at 0 raise.
- corrected_run_speed(67.4, 65000, 65000, 15, 15, 1.10, 0.020, 600,
  12, tas_input = True) = 64.133853 within 1e-3 and equals the manual
  chain weight_corrected_speed(tas_to_cas(67.4, 600, 12), 65000,
  65000) within 1e-9.
- asym_yaw_moment_static(55000, 8.0) = 440000.0 within 1e-9;
  authority_limited_ground_speed(55000, 8.0, 26, 16, 0.85,
  radians(30)) = 62.289931 within 1e-3 (121.081940 kt within 0.01);
  with s_f_cd = 1.2 it rises to 63.970485 within 1e-3; delta_max at 61
  deg raises.
- force_limited_ground_speed boosted (b = 0.34) = 65.617205 within
  1e-3 (127.549642 kt within 0.01); manual (b = 1.0) = 38.261077
  within 1e-3; pedal_force full-deflection at the authority speed =
  601.071429 N boosted within 1e-2 and 1767.857143 N manual within
  1e-2; the boosted value is <= 667 and the manual value exceeds it.
- steering_moment(65000, 0.09, 0.8, 13.0) = 596636.586 within 1.0;
  ratio against 440000 = 1.355992 within 1e-5; steering_engaged True
  at 36.8, False at 40.0 and at 42.0 against v_cut 40.0.
- ground_run_class returns exactly "steering-held" for (True, 36.8,
  62.289931, 65.617205), "departed" for (False, 62.28, 62.289931,
  65.617205), "at-limit" for (False, 62.289931, 62.289931,
  65.617205) (boundary included) and (False, 64.134, ...), and
  "with-margin" for (False, 65.617205, 62.289931, 65.617205) and
  (False, 69.5, ...).
- vmcg_verdict on the worked seven-run data: vmcg_cas = 63.042941
  within 1e-3 (equals the run R4 corrected speed within 1e-9),
  vmcg_knots = 122.545674 within 0.01, bracket_ok True with
  v_departed_max = 59.056038 within 1e-3 below the verdict and
  v_margin_min = 67.054921 at or above it, n_qualifying = 2,
  n_departed = 2, n_margin = 2, n_steering_held = 1; the corrected
  run speeds match the table within 1e-3 each; removing the with-margin
  runs keeps bracket_ok True; a manufactured verdict below the departed
  max flips bracket_ok False.
- vmcg_verdict raises on an empty run list and on a run list whose only
  run is departed (no at-limit run).
- At the verdict: required_deflection(440000, 2434.327597, 26, 16,
  0.85) = 0.511165 within 1e-5 (29.287617 deg within 1e-3);
  pedal_force(2434.327597, 8.5, 1.3, 0.045, 0.511165, 0.34, 0.35) =
  601.071429 within 1e-2 and force_ok True; the same at boost 1.0
  gives 1767.857143 and force_ok False.
- stall_guard_check(63.042941, 58.0): guard_speed = 60.9 within 1e-9,
  verdict "stall-guard-ok", proximity 1.086947 within 1e-5.
- v1_gate(63.042941, 61.5, 63.9): v1_gate_met False, v1_required =
  63.042941 within 1e-9 (122.545674 kt within 0.01), verdict
  "vmcg-gated", window width 0.857059 within 1e-5; with v1 = 64.0 the
  verdict is "ok"; with vr = 62.0 the verdict is
  "schedule-infeasible"; zero speeds raise.
- ValueErrors: isa_sigma at h_p -1 and 12000 and at a non-positive
  temperature; tas_to_cas at 0; weight_corrected_speed at w_test 0;
  flap_normalized_speed at negative flap; authority_limited_ground_speed
  at delta_max 61 deg; vmcg_verdict at empty and no-qualifying inputs.
- Determinism; no imports beyond math; constants fixed (EXP about
  5.2559, KT2MS 0.514444444444, F_LIM 667.0).

## Corpus fragment (eval/hit1-wave44-vmcg-determination.yaml)

Query 1 (copy verbatim):
  "reduce the engine-failure ground roll demonstration runs of the
  transport flight test to the vmcg-determination
  ground-minimum-control-speed with the nosewheel-steering-authority
  cutout check and the steering-free rudder balance on the ground"
  intent: "flight-test-operations; FAR/CS 25.149 ground minimum
  control speed Vmcg reduction from the engine-failure takeoff roll
  runs with the nosewheel steering cutout and the steering-free rudder
  authority and pedal force checks"
  expected_skill: "flight-test-operations/envelope/vmcg-determination"
Query 2 (copy verbatim):
  "issue the ground-control verdict from the corrected steering-free
  roll runs with the 150 lbf rudder pedal force criterion that gates
  the balanced field V1 schedule above the demonstrated vmcg-
  determination ground-minimum-control-speed"
  intent: "flight-test-operations; Vmcg verdict from corrected
  steering-free roll runs gating the balanced-field V1 schedule with
  the 150 lbf pedal force criterion and the boost factor"
  expected_skill: "flight-test-operations/envelope/vmcg-determination"
Task ids: w44-vmcg-determination-1 and -2. Prep grep (run at spec
time): each of the tokens vmcg-determination,
ground-minimum-control-speed and nosewheel-steering-authority returns 0
matches in eval/hit1-corpus.yaml and in every eval/*.yaml fragment
(grep -c 0, grep -l empty), and "vmcg|vmcl|ground-minimum-control"
appears nowhere in the skills tree, so the queries above are
collision-free; the sibling flight-test-operations tasks route on the
airborne minimum control speed demonstration (vmc-determination), the
stall-derived speed multiples (v-speeds), the unstick rotation verdict
(vmu-determination), the 35-ft obstacle distance
(takeoff-distance-determination), the balanced-field V1 computation
(engine-failure-takeoff-flight-test) and the rejected-takeoff stop
(accelerate-stop-distance), none of which carry ground roll directional
control content. The queries deliberately carry only the qualified
tokens above; a bare minimum-control-speed or bare vmc query routes
FTO-3762 to the air-side sibling vmc-determination and must never be
used here.

## Description/tag guidance (gate 1/2 and tag-steal rules)

Description must open "Use when you must reduce the engine-failure
ground roll demonstration runs of a transport airplane flight test to
the ground minimum control speed Vmcg in the spirit of the FAR/CS
25.149 ground leg method, summary-only:" and include the outputs in
the Claim. First tag: vmcg-determination. Additional tags ONLY:
ground-minimum-control-speed, nosewheel-steering-authority,
steering-cutout-speed. NEVER single generic words (speed, ground,
roll, control, steering, rudder, takeoff, engine, pedal, force,
runway) and NEVER bare minimum-control-speed or vmc alone (too
generic; routes FTO-3762 to the air-side sibling) nor any sibling
token below. 50-150 words, <=1000 chars, no em dash, no content-policy
sweep term (the banned word from the builder kit), action verb
present. Recommended wording (outputs and verdict in Claim order, 150
words, 981 chars, verified):
"Use when you must reduce the engine-failure ground roll demonstration
runs of a transport airplane flight test to the ground minimum control
speed Vmcg in the spirit of the FAR/CS 25.149 ground leg method,
summary-only: build the asymmetric yawing moment from the failed
engine thrust at its lateral arm, apply the nosewheel steering
authority below the steering cutout speed, solve the steering-free
rudder authority limited and 150 lbf pedal force limited ground
speeds with the boost factor, classify runs into the steering-held,
departed, at-limit and with-margin classes, and take the minimum
corrected at-limit speed as the Vmcg verdict with bracket checks.
Produces the corrected run table, the Vmcg in m/s and knots, the
bracket verdict, the stall guard check against 1.05 Vs1, and the V1
gate verdict with the required V1 speed. Trigger: ground minimum
control speed, vmcg determination, nosewheel steering authority,
steering cutout speed, engine failure ground roll run."

FORBIDDEN TOKENS (belong to siblings): vref, v2, vno, vne, vs0,
vr-as-1.1-times-vs1 derivation, stall-speed-multiple speed set
(v-speeds); minimum-control-speed alone, vmc alone, critical-engine,
asymmetric-yawing-moment, windmilling-drag, engine-inoperative-flight-
test, rudder-authority airspeed demonstration, airborne Vmc
(vmc-determination); minimum-unstick-speed, rotation-limit-speed,
unstick-certification, tail-strike rotation limit
(vmu-determination); ground-roll-integration, rotation-distance,
35-ft-obstacle, takeoff-field-length, climb-segment
(takeoff-distance-determination); balanced-field-v1, vef, decision-
speed, continued-takeoff, field-length-verdict, engine-failure-takeoff-
flight-test tag itself (engine-failure-takeoff-flight-test); vef-
recognition, braking-deceleration, accelerate-stop-distance,
rejected-takeoff-stop (accelerate-stop-distance); vs1g-from-wing-
loading, stall-speed computation (stall-speed-determination);
nose-gear-load-fraction, tipback-angle, tail-strike-clearance-angle,
lateral-turnover-angle, wheel-track (landing-gear-layout,
vehicle-design).
