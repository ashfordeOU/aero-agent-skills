# Wave-45 leaf spec: vmcl-determination (flight-test-operations,
# envelope pack)

- Path: skills/flight-test-operations/envelope/vmcl-determination/
- Pack: envelope (present siblings envelope-expansion, v-speeds,
  load-factor-envelope, stall-characteristics-testing,
  flight-loads-survey, structural-coupling-test, high-angle-of-attack-
  testing, spin-testing, icing-flight-test, buffet-boundary-testing,
  vmc-determination, vmcg-determination, vmu-determination; adjacent
  fences in flight-test-operations/performance
  (stall-speed-determination, landing-distance-determination,
  engine-failure-takeoff-flight-test, takeoff-distance-determination)
  and in flight-mechanics/performance (oei-climb-gradient)).
- Claim fences (quoted from the sibling frontmatter/body at spec time;
  none owns the approach and landing minimum control speed reduction of
  the landing-configuration approach-cut demonstration runs):
  - vmc-determination (this pack) owns the airborne takeoff-
    configuration minimum control AIR speed demonstration of the FAR/CS
    25.149(b)-(e) leg. Its frontmatter description reads "identify the
    critical engine from the engine-out yawing moment geometry, build
    the asymmetric yawing moment from the operating-engine thrust at
    the failed engine lateral arm plus the windmilling drag
    contribution, solve the rudder authority limited speed, apply the
    rudder pedal force criterion with the boost factor against the 150
    lbf pedal limit, and apply the stall protection guard on the
    reference stall speed". Its whole SKILL.md body at spec time
    contains zero approach or landing configuration content: whole-body
    grep count 0 for landing|approach|vmcl (grep -c 0). Its Related
    leaves block (lines 177-189) lists five neighbors and claims no
    approach/landing-configuration leg. The new leaf parallels its
    reduction structure and its 150 lbf pedal-force criterion family
    with the boost factor, but the governing surface is the APPROACH
    and LANDING configuration of FAR/CS 25.149(f)/(g): landing flap
    setting, approach trim, go-around thrust on the operating engines,
    most favorable (f) and most unfavorable (g) weight, and the
    bank-5-degree and 20-degree-heading-change run criteria.
  - vmcg-determination (this pack, wave 44) owns the GROUND leg only.
    Its SKILL.md Related leaves first bullet reads "the airborne
    minimum control speed demonstration with the windmilling drag
    contribution and the air-side stall protection guard; this leaf
    owns the ground leg only", and its whole body (grep at spec time)
    shows zero approach or landing content beyond the
    vehicle-design/sizing landing-gear-layout sibling leaf name (grep
    count 2, both the landing-gear-layout name). The VMC family
    organizes by leg: air and ground claimed by the two siblings, the
    approach and landing leg VMCL and the three-plus-engine second-cut
    leg VMCL-2 unclaimed.
  - Pack router skills/flight-test-operations/SKILL.md lines 140 and
    166: "Vmc determination questions ... route to the vmc-
    determination sub-skill" and "Ground-leg minimum-control-speed
    questions ... route to the envelope vmcg-determination sub-skill,
    not the air-side vmc-determination". Air leg and ground leg are
    routed; no router row names an approach or landing control speed
    leg.
  - Wave-44 scope note on the record (ops/automation/state/wave44-leaf-
    plan.md): line 57 "DO NOT also build Vmcl; tokens vmcg-
    determination/ground-minimum-control-speed/nosewheel-steering-
    authority, never bare minimum-control-speed/vmc (FTO-3762 steal
    risk)" and line 158 "do NOT build Vmcl" inside the vmcg triage
    fallback. Both are wave-44 scope discipline for that wave's single
    VMC-family build (vmcg over vmcl) plus the FTO-3762 token-steal
    rule carried into this spec; there is no dead-end rationale on the
    record, and the FAR/CS 25.149(f)/(g) landing legs remain the last
    unfilled VMC-family regulatory legs after vmcl-determination is
    built.
  - Whole-tree greps at spec time: "vmcl" returns 0 matches in skills/
    (exit 1) and 0 matches in eval/hit1-corpus.yaml (exit 1); "vmca"
    returns 0 matches in skills/; the tokens vmcl-determination,
    landing-minimum-control-speed, approach-configuration-control,
    go-around-thrust, critical-engine-cut, most-favorable-weight and
    second-engine-cut each return 0 matches across skills/ and the
    whole eval/ tree (grep -c 0, grep -l empty). GENUINE
    flight-test-operations gap (probe receipt verified zero-owner, GO):
    no leaf reduces the landing-configuration approach-cut
    demonstration runs to the FAR/CS 25.149 approach and landing
    minimum control speeds VMCL and VMCL-2.
- Standards id: far-25 (14 CFR Part 25: Airworthiness Standards for
  Transport Category Airplanes) and cs-25 (CS-25: Certification
  Specifications and Acceptable Means of Compliance for Large
  Aeroplanes), both reference-only and both present in
  standards-map.yaml (gated false). Ledger Standard: far-25, cs-25.
- Family: flight-test-operations

## Claim

Reduce the landing-configuration approach-cut demonstration runs of a
multi-engine transport airplane flight test to the approach and landing
minimum control speeds VMCL and VMCL-2 in the spirit of the FAR/CS
25.149(f)/(g) method, summary-only. Build the asymmetric yawing moment
of the critical-engine cut over the operating engine set (the
engine-by-engine sum of the go-around thrusts at their lateral arms,
with the cut engines contributing nothing), solve the rudder
authority-limited and 150 lbf pedal-force-limited airspeeds at the
landing configuration with go-around thrust on the operating engines,
classify each approach-cut run by the bank-5-degree and
20-degree-heading-change control criteria, correct the demonstrated run
speeds to the reference condition (most favorable weight and reference
landing flap for the (f) leg, most unfavorable weight for the (g) leg),
and for three-plus-engine airplanes add the VMCL-2 second-cut leg where
a second critical engine is cut with one already inoperative and the
operating engines go to go-around thrust. Per run the reduction takes
the measured cut speed (calibrated airspeed by default, true airspeed
accepted) at the test gross weight, pressure altitude, ISA temperature
deviation and flap setting, then classifies the run: control-lost when
control was not held within the bank and heading criteria (VMCL lies
above this run), at-limit when control was held within the criteria
with the rudder at or near its limit (the VMCL-qualifying class), and
with-margin when control was held with the required deflection below
the limit (VMCL lies at or below this run); an observed recovery
heading change beyond 20 degrees or bank beyond 5 degrees always
overrides the class to control-lost. Correct every run speed to
standard conditions: true to calibrated airspeed through the ISA
density ratio sigma, weight correction v*sqrt(w_ref/w_test), and
configuration normalization to the reference landing flap through the
landing-configuration lift coefficient CL(f) = cl_0 + cl_per_deg*f.
Issue the per-leg demonstrated verdict as the minimum of the corrected
at-limit run speeds in m/s and knots with the bracket consistency check
against the fastest control-lost and the slowest with-margin runs, and
report the combined VMCL as the governing (higher) leg value. Check the
demonstration at the verdict: required deflection below the rudder
limit, required pedal force within the 667 N limit with the boost
factor (force_ok), the authority margin against the analytic
authority-limited airspeed, and the lateral control check that the roll
capability at the verdict meets the 20-degrees-in-5-seconds demand.
Apply the stall protection guard on the landing-configuration reference
stall speed (1.05*Vs0, Vs0 supplied by the sibling
stall-speed-determination leaf) and report the margin against the
operating approach speed set (v_app_ref consumed from the operating
schedule, the v-speeds sibling model places it at 1.3*Vs0): margin-ok
when the reference approach speed clears the demonstrated VMCL, else
vmcl-governs with the required approach speed. Does NOT do: the
airborne takeoff-configuration Vmc demonstration with the windmilling
drag contribution, the critical-engine ranking and the takeoff-config
stall protection guard (vmc-determination); the ground minimum control
speed Vmcg with the nosewheel steering cutout and the steering-free
ground roll reduction (vmcg-determination); the minimum unstick
rotation verdict (vmu-determination); the stall-derived vref/v2/vr
speed multiple set (v-speeds); Vs0/Vs1g from wing loading
(stall-speed-determination); the balanced-field V1 or the takeoff
decision speed (engine-failure-takeoff-flight-test); the all-engines
landing distance and 50-ft obstacle reduction
(landing-distance-determination); the takeoff distance
(takeoff-distance-determination); the engine-out climb gradient
(oei-climb-gradient). Propeller position content of 25.149(f)(5)/(g)(5)
is out of scope (jet transport model); differential braking, dynamic
transients, sideslip coupling, ground effect and the aileron control
gearing itself are out of scope (roll capability at the verdict is a
consumed input). The windmilling drag of the failed engine is neglected
in the main model (small at approach speeds for jets) and enters only
through the optional s_f_cd term of the authority closed form, single
cut only. Single-layer ISA to 11 km only.

## Model (implement exactly)

Pure stdlib, math only, closed form. Module constants: RHO_SL = 1.225
kg/m3, T0 = 288.15 K, LAPSE = 0.0065 K/m, G0 = 9.80665 m/s2, R_AIR =
287.05 J/(kg K), EXP = G0/(R_AIR*LAPSE) (about 5.2559, the ISA pressure
exponent), KT2MS = 0.514444444444 m/s per knot (1852/3600), F_LIM =
667.0 N (the 150 lbf pedal force criterion of the test condition,
paraphrased), STALL_GUARD = 1.05, BANK_LIM_DEG = 5.0, HEADING_LIM_DEG =
20.0, ROLL_DEG = 20.0, ROLL_TIME_S = 5.0. KT2MS appears only to quote
the verdict in knots; every speed verdict is a CAS m/s value at
reference conditions.

Defining relations (pin these exactly; every function below derives
from them):
- ISA density ratio at pressure altitude h_p with temperature
  deviation dt_isa: delta = (1 - LAPSE*h_p/T0)**EXP, theta = (T0 -
  LAPSE*h_p + dt_isa)/T0, sigma = delta/theta. At 600 m with a +12 K
  warm day the real anchor sigma = 0.905430 (sqrt 0.951541), matching
  the family value exercised by the vmcg leaf.
- TAS to CAS: v_cas = v_tas*sqrt(sigma); CAS input needs no density
  correction.
- Weight correction at fixed lift coefficient: v_corr = v_cas*
  sqrt(w_ref/w_test). The reference weight is the most favorable
  (minimum) approach weight for the (f) leg and the most unfavorable
  (maximum) approach weight for the (g) leg, per the respective
  condition sets (25.149(f)(4) and (g)(4), applicant option for a
  function of weight acknowledged; summary-only).
- Configuration normalization through the landing-configuration lift
  coefficient CL(f) = cl_0 + cl_per_deg*f: v_norm = v_cas*
  sqrt(CL(f_test)/CL(f_ref)); more flap, more lift, lower control
  speed, so a control speed measured at a lower flap setting normalizes
  down to the reference landing flap.
- Asymmetric yawing moment of the cut: N_asym = |sum of T_i*y_i over
  the engines still operating|, T_i the go-around thrust of engine i
  and y_i its signed lateral arm; the cut engines contribute no thrust.
  This is the engine-by-engine sum of the standard published method,
  which reduces EXACTLY to the family static form T_op*|y_fail| when
  exactly one of two equal-thrust symmetric engines fails (the twin
  identity the vmc and vmcg leaves exercise), and it is the form the
  VMCL-2 second-cut geometry requires: cutting a centerline engine at
  y = 0 leaves the residual moment of the remaining wing engines, which
  a resultant-at-the-cut-arm convention would zero. Spec-time triage
  note: the T_op*|y_fail| resultant convention of the sibling logic
  files is exact for the twin layout those leaves exercise and is
  deliberately generalized here to the engine set sum for layouts of
  three and more engines (see the quad contrast identity below); all
  downstream solve forms are the family closed forms verbatim.
- First critical cut: the engine whose loss leaves the largest
  asymmetric moment; ties resolve to the lower index. For an
  equal-thrust symmetric layout this is the family critical-engine
  geometry ranking |T*y| (largest lateral arm).
- Second critical cut (VMCL-2, three-plus-engine airplanes): among the
  engines still operating after the first cut, the one whose loss
  leaves the largest asymmetric moment; ties resolve to the lower
  index. For an equal-thrust symmetric four-engine layout with an
  outer first cut this is the SAME-SIDE inner engine (the residual
  outboard moment grows).
- Rudder restoring: N_rud = q*S_v*l_v*C_Lv_delta_r*delta, with q =
  0.5*RHO_SL*V^2, S_v the fin area, l_v the CG-to-fin arm and
  C_Lv_delta_r the effective fin lift slope per rudder deflection.
  Required deflection delta_req = N_asym/(q*S_v*l_v*C_Lv_delta_r),
  capped at delta_r_max.
- Rudder-authority limited airspeed: the speed where delta_req reaches
  delta_r_max. Closed form q* = N_asym/(S_v*l_v*C_Lv_delta_r*
  delta_r_max_rad - s_f_cd*|y_cut|); V_auth = sqrt(2*q*/RHO_SL). If
  the denominator is not positive the configuration is never authority
  limited (V_auth = None). s_f_cd is the optional windmilling drag
  area term acting at the cut engine arm |y_cut| (main model 0.0, and
  only meaningful for a single-cut leg).
- Rudder pedal force: F = q*S_r*c_r*|C_h_delta_r|*min(delta_req,
  delta_r_max_rad)*boost_factor/pedal_arm_m, with C_h_delta_r the hinge
  moment coefficient per radian (magnitude used), S_r and c_r the
  rudder area and chord, and the boost factor scaling felt force (1.0
  manual, smaller for power-boosted systems).
- Pedal-force limit: F_lim = 667 N (150 lbf criterion of the test
  condition, paraphrased). The force-limited airspeed follows from the
  full-deflection quadratic F(V) at the deflection limit, q_F =
  F_lim*pedal_arm/(S_r*c_r*|C_h_delta_r|*delta_r_max_rad*boost_factor),
  V_force = sqrt(2*q_F/RHO_SL). It is leg-independent (depends only on
  the rudder geometry and the boost factor).
- Per-leg analytic prediction (family convention): predicted = max(V_auth,
  V_force) with the governing label "rudder-authority" when V_auth >=
  V_force else "pedal-force".
- Run classes (from the measured CAS, TAS converted first, before the
  standard-condition corrections, plus the observed recovery outcome):
  "control-lost" when the observed bank exceeded BANK_LIM_DEG or the
  observed recovery heading change exceeded HEADING_LIM_DEG, or
  otherwise when V < V_auth (VMCL lies above this run); "at-limit" when
  held within the criteria and V_auth <= V < V_force (the
  VMCL-qualifying class); "with-margin" when held within the criteria
  and V >= V_force (VMCL lies at or below this run). Observed criteria
  violations are direct evidence of control loss and override the speed
  class; observed compliance never overrides a speed-based loss.
- Per-leg demonstrated verdict: vmcl_leg = min of the corrected
  at-limit run speeds; bracket_ok requires the verdict to strictly
  exceed the fastest corrected control-lost run when present and to not
  exceed the slowest corrected with-margin run when present.
- Combined demonstrated VMCL: the governing leg carries the higher
  demonstrated value (the approach speed set must clear BOTH legs for a
  three-plus-engine airplane; a twin has only the (f) leg).
- Stall guard: guard_speed = 1.05*vs0 from the sibling stall leaf;
  guard verdict "stall-guard-ok" when VMCL clears it, else
  "stall-guard-governs". A proximity vmcl/vs0 below 1.10 keeps the
  guard relevant.
- Lateral control check (25.149(h)(3), paraphrased): roll capability at
  the verdict must move the airplane through 20 degrees in not more
  than 5 seconds; the available roll rate is a consumed input and the
  required average rate is 20/5 = 4 deg/s.
- Approach margin check: margin-ok when the consumed reference approach
  speed v_app_ref >= vmcl (ratio v_app_ref/vmcl reported); else
  "vmcl-governs" with v_app_required = vmcl.
- Units are SI: N, m, m/s, rad, deg, N m; knots = m/s * 1.94384
  (1/KT2MS).
- FAR/CS 25.149(f)/(g)/(h) frame the approach and landing minimum
  control speed test conditions (landing configuration, approach trim,
  go-around thrust on the operating engines, the most favorable (f)
  and most unfavorable (g) weight, the bank and heading criteria, the
  lateral control roll demand); the relations above are standard
  engineering methodology, summary-only.

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
  the full standard-condition reduction of one measured cut speed:
  tas_to_cas first when tas_input (CAS input is used directly), then
  weight_corrected_speed, then flap_normalized_speed. ValueError if
  v_meas <= 0 or any argument fails its sub-check.
- post_cut_moment(engines, cut_indices) -> float
  |sum of T_i*y_i over the engines NOT in cut_indices|, N m. engines
  is a list of dicts {"thrust_N", "y_m"} with y_m signed positive
  right. ValueError for an empty or structurally invalid engine list,
  any thrust_N <= 0, an empty cut_indices, or any cut index out of
  range.
- first_cut_index(engines) -> int
  the engine whose loss leaves the largest post_cut_moment; ties to
  the lower index. ValueError as in post_cut_moment.
- second_cut_index(engines, first_idx) -> int
  the second critical cut among the engines still operating after
  first_idx is out. ValueError if first_idx out of range or fewer than
  three engines (VMCL-2 requires three or more).
- authority_limited_airspeed(n_asym, y_cut, s_v, l_v, c_lv_delta_r,
  delta_max_rad, s_f_cd = 0.0) -> float or None
  the airspeed where the required deflection reaches the rudder limit
  from the closed form above; None when the denominator is not
  positive (never authority limited). ValueError if n_asym <= 0,
  y_cut == 0, s_v or l_v <= 0, c_lv_delta_r <= 0, delta_max outside
  (0, 60] deg, or s_f_cd < 0.
- required_deflection(n_asym, q, s_v, l_v, c_lv_delta_r) -> float
  n_asym/(q*s_v*l_v*c_lv_delta_r). ValueError if n_asym <= 0 or q <= 0.
- pedal_force(q, s_r, c_r, c_h_delta_r, delta_used, boost, pedal_arm)
  -> float
  q*s_r*c_r*|c_h_delta_r|*delta_used*boost/pedal_arm. ValueError if q
  <= 0, delta_used <= 0, boost outside (0, 1], pedal_arm <= 0,
  c_h_delta_r == 0, or s_r/c_r <= 0.
- force_limited_airspeed(f_lim, pedal_arm, s_r, c_r, c_h_delta_r,
  delta_max_rad, boost) -> float
  the airspeed where a full-deflection input demands the pedal force
  limit, from the q_F closed form above. ValueErrors as in
  pedal_force, plus f_lim <= 0 and delta_max_rad <= 0.
- approach_run_class(v_cut_cas, v_auth, v_force, bank_max_deg = None,
  heading_change_deg = None) -> str
  the three class strings exactly as spec'd above; an observed bank
  beyond BANK_LIM_DEG or heading change beyond HEADING_LIM_DEG
  overrides to "control-lost". ValueError if v_cut_cas <= 0 or v_auth
  or v_force is None/<= 0.
- leg_verdict(runs, leg, v_auth, v_force, w_ref, flap_ref, cl_0,
  cl_per_deg) -> dict
  reduces the approach-cut run list of one leg. Each run dict: id,
  speed (m/s, CAS or TAS by tas_input), weight (kg), flap (deg),
  bank_max_deg, heading_change_deg, h_p (m, default 0), dt_isa (K,
  default 0), tas_input (bool, default False). Per run the class comes
  from the measured CAS (TAS converted first, before corrections) and
  the corrected speed uses the full standard-condition chain;
  vmcl_cas = min of the corrected at-limit speeds; vmcl_knots =
  vmcl_cas/KT2MS; reports v_lost_max and v_margin_min (None when a
  bracket is empty), bracket_ok (True only when the verdict strictly
  exceeds the lost max when present and does not exceed the margin min
  when present), n_qualifying, n_lost, n_margin and the per-run
  corrected table. ValueError if runs is empty or no run classifies as
  at-limit (VMCL not defined by the data).
- stall_guard_check(vmcl_cas, vs0, guard_factor = 1.05) -> dict
  guard_speed = 1.05*vs0, guard verdict "stall-guard-ok" or
  "stall-guard-governs", and the proximity ratio vmcl/vs0. ValueError
  if either speed <= 0.
- lateral_control_check(phi_dot_avail_deg_s, phi_req_deg = 20.0,
  t_req_s = 5.0) -> dict
  required average rate phi_req_deg/t_req_s (4.0 deg/s at the
  defaults); verdict "lateral-control-ok" when the consumed available
  roll rate meets it, else "lateral-control-insufficient". ValueError
  if the available rate <= 0 or the demand/time <= 0.
- approach_margin_check(vmcl_cas, v_app_ref) -> dict
  the margin against the operating approach speed set: margin_ok =
  v_app_ref >= vmcl, ratio v_app_ref/vmcl, clearance v_app_ref -
  vmcl; verdict "margin-ok" or "vmcl-governs" with v_app_required =
  vmcl when governing. ValueError if either speed <= 0.
- demonstration_summary(verdict_1, verdict_2 = None) -> dict
  combined demonstrated VMCL: vmcl_cas and vmcl_knots of the governing
  (higher) leg and the governing_leg label "vmcl-1" or "vmcl-2".

Identities to test (closed form, exact):
- isa_sigma(0, 0) == 1.0 exactly and tas_to_cas(v, 0, 0) == v exactly;
  sigma falls with warm-day altitude: sigma(600, +12) < sigma(600, 0)
  < 1 (real anchor 0.905430 vs 0.943654, sqrt 0.951541).
- Same-weight and same-flap degeneracy:
  weight_corrected_speed(v, w, w) == v and flap_normalized_speed(v, f,
  f, cl_0, cl_per_deg) == v exactly.
- Weight sqrt scaling: weight_corrected_speed(60.0, w, 4*w) == 120.0
  exactly (real anchor 120.000000 from 60.0).
- Flap normalization round trip:
  flap_normalized_speed(flap_normalized_speed(v, f1, f2, ...), f2,
  f1, ...) == v within 1e-9; the normalization direction is correct: a
  control speed measured at the lower flap setting 20 deg normalizes
  down to the 25 deg reference (real anchor 55.777561 from 58.5, CL
  1.500 to 1.650).
- Reduction chain: corrected_run_speed with tas_input True equals
  weight_corrected_speed(tas_to_cas(v, h, dt), w, w_ref) when the flap
  factor is 1.0 (real anchor 63.935270 on the L1D side, the TAS run at
  500 m +8 K).
- Twin identity: for two equal-thrust symmetric engines the engine-sum
  moment equals the family static form T_op*|y_fail| exactly (real
  anchor 768000.000000 on both sides).
- Quad contrast (deviation record): for the four-engine layout the
  engine-sum first-cut moment is 768000.000000 N m while the
  T_op*|y_fail| resultant convention of the sibling logic files gives
  2304000.000000 N m; the resultant convention is exact only for the
  twin, so the multi-engine legs use the engine sum.
- Tri-jet identity: for a three-engine layout with wing engines at
  +-7.5 m and a centerline tail engine at y = 0 the second critical
  cut is the tail engine and the VMCL-2 moment equals the VMCL-1
  moment exactly (real anchor 637500.000000 N m both legs, identity
  True).
- Second-cut geometry: with an outer first cut on the equal-thrust
  quad the second critical cut is the same-side inner engine and the
  VMCL-2 moment exceeds the VMCL-1 moment by the factor
  (y_outer + y_inner)/y_outer = 11.5/8 (real anchor 1104000.000000
  vs 768000.000000 N m).
- Authority closed form: V_auth1 = 54.925334 m/s (106.766308 kt) and
  V_auth2 = 65.853162 m/s (128.008306 kt) on the worked quad geometry;
  the second-cut boundary exceeds the first-cut boundary by the sqrt
  of the moment ratio, sqrt(11.5/8) = 1.198958, matching the real
  speed ratio 65.853162/54.925334 = 1.198958 within 1e-6.
- Pedal-force family: force_limited_airspeed = 71.472200 m/s
  (138.930842 kt) at boost 0.20, leg-independent; the required pedal
  force at the required deflection is speed-independent (real anchors
  393.909945 N for leg 1 and 566.245546 N for leg 2 at their verdicts,
  both within the 667 N limit).
- Class boundaries: V_auth itself is at-limit (boundary included),
  V_auth - 0.01 is control-lost, V_force itself is with-margin, and an
  observed bank or heading violation overrides at-limit and
  with-margin speeds to control-lost; the three class strings are
  exactly the spec strings.
- Verdict minimum: per leg vmcl equals the corrected speed of the
  slowest qualifying run; in the worked data vmcl_1 = run L1B's
  corrected speed (55.489886) exactly and vmcl_2 = run L2B's corrected
  speed (66.900000) exactly, since those are the minima of the
  qualifying corrected speeds.
- Bracket logic: bracket_ok True with v_lost_max 51.599843 < vmcl_1
  55.489886 <= v_margin_min 72.500000 and v_lost_max 64.326379 <
  vmcl_2 66.900000 <= v_margin_min 73.500000 in the worked data;
  removing the with-margin runs keeps bracket_ok True (single-sided
  brackets allowed) while a verdict at or below the lost max flips it
  False.
- Governing leg: the combined demonstrated VMCL is the higher leg
  value, 66.900000 m/s from leg 2 (governing_leg "vmcl-2"), the
  second-cut leg setting the approach speed floor for the quad.
- At-verdict check (leg 2): q = 2741.311125 Pa, delta_req = 0.507341
  rad (29.068477 deg) below the 0.523599 rad limit, required pedal
  force 566.245546 N within the 667 N limit, full-deflection pedal
  force 584.391339 N, authority margin vmcl - V_auth2 = 1.046838 m/s.
- Stall guard: guard_speed 55.335000 m/s at vs0 52.7 clears the
  verdict (stall-guard-ok, proximity 1.269450); the leg-1 proximity
  1.052939 sits below the 1.10 threshold that keeps the guard
  relevant.
- Lateral control: required average rate 4.000000 deg/s (20 degrees in
  5 seconds), available 4.8 deg/s gives "lateral-control-ok".
- Approach margin: v_app_ref 68.510000 m/s (1.3*52.7) clears the
  verdict with ratio 1.024066 and clearance 1.610000 m/s
  (margin-ok).
- ValueErrors across the module: isa_sigma at h_p -1 and 12000 and at
  a non-positive ambient temperature; tas_to_cas at v_tas 0;
  weight_corrected_speed at w_test 0; flap_normalized_speed at a
  negative flap; post_cut_moment on an empty engine list;
  second_cut_index on a twin; authority_limited_airspeed at
  delta_max 61 deg; leg_verdict on an empty list and on a list with no
  at-limit run; stall_guard_check, lateral_control_check and
  approach_margin_check at zero speeds.
- Determinism; no imports beyond math; constants fixed (EXP about
  5.2559, KT2MS 0.514444444444, F_LIM 667.0, BANK_LIM_DEG 5.0,
  HEADING_LIM_DEG 20.0).

## Worked example

Reference condition set of the (f) leg: most favorable (minimum)
approach weight w_ref_1 = 170000 kg; reference landing flap 25.0 deg
with cl_0 = 0.90 and cl_per_deg = 0.030 per deg (CL(25) = 1.650,
CL(20) = 1.500). Reference condition of the (g) leg: most unfavorable
(maximum) approach weight w_ref_2 = 185000 kg at the same reference
flap. Four-engine widebody-class transport jet in the landing
configuration: go-around thrust 96000 N on every engine at the signed
arms y = -8.0, -3.5, +3.5, +8.0 m (outer left, inner left, inner
right, outer right). Fin S_v = 42 m2 at the CG-to-fin arm l_v = 21 m
with C_Lv_delta_r = 0.90 per rad, rudder limit 30 deg (0.523599 rad),
rudder S_r = 9.5 m2, c_r = 1.5 m, C_h_delta_r = 0.05 per rad, pedal
arm 0.35 m, boost factor 0.20 (power-boosted). Windmilling neglected
in the main model. The landing-configuration reference stall speed
from the sibling stall leaf is vs0 = 52.7 m/s and the operating
approach reference speed from the schedule (the v-speeds model places
it at 1.3*vs0) is v_app_ref = 68.510000 m/s. All values below are REAL
outputs of the spec anchor /tmp/w45spec/anchor_vmcl_determination.py
(stdlib math, closed form, exit 0, deterministic).

- Atmosphere: isa_sigma(0, 0) = 1.000000; isa_sigma(600, +12) =
  0.905430 (sqrt 0.951541), the family anchor reproduced; isa_sigma(600,
  0) = 0.943654. tas_to_cas(66.8, 500, 8) = 64.310260 m/s.
- Cut selection and leg moments: the first critical cut is index 0,
  the outer left engine at y = -8.0 m; the engine-sum moment of the
  remaining three engines is N1 = 768000.000000 N m (for the
  equal-thrust symmetric layout the moment of the cut engine's thrust
  at its own arm, 96000 * 8.0). With that engine inoperative the
  second critical cut is index 1, the same-side inner engine at y =
  -3.5 m: cutting it leaves the two right-side engines whose arm sum
  is 8.0 + 3.5, so N2 = 96000 * 11.5 = 1104000.000000 N m. The
  second-cut moment exceeds the first-cut moment by 1.4375 times, so
  the VMCL-2 leg is the harder demonstration for this quad.
- Analytic limits (landing configuration, go-around thrust):
  - Authority-limited airspeed leg 1: q* = 1847.785293 Pa, V_auth1 =
    54.925334 m/s (106.766308 kt). Below this speed the rudder cannot
    balance the first-cut moment within the 5 degree bank allowance.
  - Authority-limited airspeed leg 2: q* = 2656.191354 Pa, V_auth2 =
    65.853162 m/s (128.008306 kt), the boundary of the second-cut leg.
  - Force-limited airspeed (both legs, boost 0.20): q_F =
    3128.818666 Pa, V_force = 71.472200 m/s (138.930842 kt), the speed
    where a full-deflection input demands the 667 N limit.
  - Per-leg analytic predictions (family max convention): both legs
    predict 71.472200 m/s governed by "pedal-force", the analytic
    upper bound of the qualifying band; the demonstrated values below
    come from the qualifying run evidence between the authority and
    force boundaries, as in the vmcg reduction.
- Leg-1 runs (VMCL, 25.149(f): all engines operating, trimmed for
  approach, go-around thrust, critical cut at the run speed; class
  from the measured CAS before corrections, corrected to w_ref_1 and
  flap 25):
  - L1A: 52.8 m/s CAS at 178000 kg, bank 6.3 deg, heading change
    24 deg. Control not held within the criteria (heading change
    beyond 20 deg) and below V_auth1: control-lost. Corrected
    51.599843 m/s (weight factor sqrt(170000/178000)).
  - L1B: 56.3 m/s CAS at 175000 kg, bank 3.1 deg, heading change
    12 deg. Held within the criteria: at-limit. Corrected 55.489886
    m/s (weight factor sqrt(170000/175000) = 0.985611).
  - L1C: 58.0 m/s CAS at 170000 kg, bank 2.6 deg, heading change
    9 deg. At-limit. Corrected 58.000000 m/s (reference weight).
  - L1D: 66.8 m/s TRUE airspeed at 500 m pressure altitude, +8 K,
    172000 kg, bank 2.2 deg, heading change 7 deg. TAS to CAS
    64.310260 m/s, still below V_force: at-limit. Corrected 63.935270
    m/s. Demonstrates the altitude and temperature correction path.
  - L1E: 72.5 m/s CAS at 170000 kg, bank 1.8 deg, heading change
    5 deg. At or above V_force with control to spare: with-margin.
    Corrected 72.500000 m/s.
  - L1F: 58.5 m/s CAS at 170000 kg at flap 20 (reference flap 25),
    bank 3.0 deg, heading change 11 deg. At-limit. Corrected 55.777561
    m/s (CL 1.500 to 1.650), the flap normalization path: the run
    measured at the lower flap setting normalizes down to 55.777561 m/s
    at the reference landing flap, a 4.65% speed drop from the extra
    flap lift.
- Leg-1 verdict: vmcl_1 = 55.489886 m/s (107.863709 KCAS), the
  corrected speed of run L1B, the minimum of the four qualifying
  corrected speeds (55.489886, 58.000000, 63.935270, 55.777561).
  Brackets: v_lost_max 51.599843 below the verdict and v_margin_min
  72.500000 at or above it, so bracket_ok True. Counts: 4 at-limit,
  1 control-lost, 1 with-margin. Checks at the leg-1 verdict: q =
  1885.965550 Pa, delta_req = 0.512999 rad (29.392668 deg) below the
  0.523599 rad limit, required pedal force 393.909945 N, authority
  margin vmcl_1 - V_auth1 = 0.564552 m/s. The leg-1 demonstration
  clears the stall guard by a whisker: guard 55.335000 m/s at
  proximity vmcl_1/vs0 = 1.052939, below the 1.10 threshold that keeps
  the guard relevant.
- Leg-2 runs (VMCL-2, 25.149(g): one critical engine already
  inoperative, trimmed for approach, second critical cut at the run
  speed, operating engines at go-around thrust; corrected to w_ref_2
  and flap 25):
  - L2A: 64.5 m/s CAS at 186000 kg, bank 5.8 deg, heading change
    22 deg. Not held within the criteria and below V_auth2:
    control-lost. Corrected 64.326379 m/s.
  - L2B: 66.9 m/s CAS at 185000 kg, bank 3.4 deg, heading change
    13 deg. Held: at-limit. Corrected 66.900000 m/s (reference
    weight).
  - L2C: 68.4 m/s CAS at 183000 kg, bank 3.8 deg, heading change
    15 deg. At-limit. Corrected 68.772755 m/s.
  - L2D: 70.6 m/s CAS at 185000 kg, bank 4.2 deg, heading change
    16 deg. At-limit (still below V_force 71.472200). Corrected
    70.600000 m/s.
  - L2E: 73.5 m/s CAS at 185000 kg, bank 2.9 deg, heading change
    8 deg. With-margin. Corrected 73.500000 m/s.
- Leg-2 verdict: vmcl_2 = 66.900000 m/s (130.043197 KCAS), run L2B's
  corrected speed, the minimum of the three qualifying corrected
  speeds (66.900000, 68.772755, 70.600000). Brackets: v_lost_max
  64.326379 below the verdict and v_margin_min 73.500000 at or above
  it, so bracket_ok True. Counts: 3 at-limit, 1 control-lost,
  1 with-margin.
- Combined demonstrated VMCL: the governing leg carries the higher
  demonstrated value, vmcl = 66.900000 m/s (130.043197 KCAS) from leg
  2, governing_leg "vmcl-2". For this quad the second-cut leg, not
  the all-engines cut, sets the approach speed floor: the first-cut
  leg demonstrates control down to 107.9 KCAS while the second-cut leg
  bottoms out at 130.0 KCAS.
- Demonstration checks at the governing verdict: q = 2741.311125 Pa,
  required deflection delta_req = 0.507341 rad (29.068477 deg) below
  the 0.523599 rad limit, required pedal force 566.245546 N within the
  667 N limit (force_ok True), full-deflection pedal force at the
  verdict 584.391339 N, and the authority margin vmcl - V_auth2 =
  1.046838 m/s above the analytic second-cut boundary.
- Stall guard (vs0 = 52.7 m/s): guard speed 1.05 * 52.7 =
  55.335000 m/s well below the verdict, guard_verdict
  "stall-guard-ok"; proximity vmcl/vs0 = 1.269450, so the guard is not
  the binding check for the final verdict (the leg-1 proximity 1.052939
  is the guard-relevant case).
- Lateral control: the required average roll rate is 20/5 =
  4.000000 deg/s; the available roll rate at the verdict, 4.8 deg/s
  (consumed input), clears it: lateral_verdict "lateral-control-ok".
- Approach margin: v_app_ref = 1.3 * 52.7 = 68.510000 m/s clears the
  demonstrated VMCL with ratio 1.024066 and clearance 1.610000 m/s:
  margin_verdict "margin-ok". The scheduled landing reference approach
  speed beats the second-cut minimum control speed by 1.61 m/s, a
  tight but legal 2.4% margin.
- Tri-jet cross-check (3-engine VMCL-2 case): three engines at
  85000 N go-around thrust with wing engines at y = -7.5 and +7.5 m
  and a centerline tail engine at y = 0. First critical cut: wing
  engine (index 0). Second critical cut: the tail engine (index 1,
  y = 0): cutting it leaves only the remaining wing engine, so the
  VMCL-2 moment equals the VMCL-1 moment exactly, 637500.000000 N m
  both legs (identity True). This is the case the engine-set sum
  exists for: cutting the y = 0 engine does not zero the residual
  moment of the remaining wing engine, and VMCL-2 reproduces VMCL for
  the centerline-tail tri-jet.
- Twin identity (shared-core reuse check): for the two-engine layout
  at +-8.0 m the engine sum gives 768000.000000 N m, exactly the
  family static form T_op*|y_fail| of the vmc/vmcg leaves. Quad
  contrast (deviation record): on the four-engine layout the engine
  sum gives 768000.000000 N m for the first cut while the T_op*|y_fail|
  resultant convention of the sibling logic files gives 2304000.000000
  N m; the engine set sum is the pinned multi-engine form here.
- Read-off: this airplane demonstrates VMCL near 130.0 KCAS at the
  landing configuration, set by the VMCL-2 second-cut leg, 22 kt above
  the first-cut leg. The analytic authority boundaries sit at 106.8 kt
  (one cut) and 128.0 kt (second cut); the qualifying runs bracket the
  demonstrated 66.9 m/s between the 64.3 m/s control-lost run and the
  73.5 m/s with-margin run, and the full-deflection pedal force stays
  within the 150 lbf criterion through the qualifying band. The
  scheduled approach reference speed clears the verdict by 1.6 m/s, so
  the control limit does not force the approach schedule up, but the
  2.4% margin is the certification-relevant number for this airplane.
Run your module and take the real outputs as assert targets; the
anchors above are real prep outputs of
/tmp/w45spec/anchor_vmcl_determination.py (stdlib math, closed form,
exit 0).

## Validation list (contract test must include)

1. isa_sigma(0, 0) = 1.0 within 1e-12; isa_sigma(600, 12) = 0.905430
   within 1e-5 and below isa_sigma(600, 0) = 0.943654;
   tas_to_cas(66.8, 500, 8) = 64.310260 within 1e-3; tas_to_cas(v, 0,
   0) = v within 1e-12.
2. weight_corrected_speed(60.0, w, 4*w) = 120.0 within 1e-9; weight
   factor sqrt(170000/175000) = 0.985611 within 1e-6; same-weight call
   returns the input within 1e-12.
3. flap_normalized_speed(58.5, 20, 25, 0.90, 0.030) = 55.777561 within
   1e-3 (CL 1.500 to 1.650); same-flap call returns the input; the
   20-to-25-to-20 round trip returns 58.5 within 1e-9; negative flap
   and cl_0 at 0 raise.
4. corrected_run_speed(66.8, 172000, 170000, 25, 25, 0.90, 0.030, 500,
   8, tas_input = True) = 63.935270 within 1e-3 and equals the manual
   chain weight_corrected_speed(tas_to_cas(66.8, 500, 8), 172000,
   170000) within 1e-9.
5. post_cut_moment on the worked quad: first cut (index 0) leaves
   768000.0 within 1e-6 N m; second cut (index 1 with index 0 out)
   leaves 1104000.0 within 1e-6; first_cut_index returns 0 and
   second_cut_index returns 1; the twin layout gives 768000.0 equal to
   the family T_op*|y_fail| product within 1e-6; the tri-jet layout
   gives 637500.0 for both legs; empty engine list and a second cut on
   a twin raise ValueError.
6. authority_limited_airspeed(768000.0, 8.0, 42, 21, 0.90,
   radians(30)) = 54.925334 within 1e-3 (106.766308 kt within 0.01);
   authority_limited_airspeed(1104000.0, 3.5, 42, 21, 0.90,
   radians(30)) = 65.853162 within 1e-3 (128.008306 kt within 0.01);
   the second-cut value exceeds the first-cut value by the ratio
   sqrt(11.5/8) = 1.198957 within 1e-5; delta_max at 61 deg and
   y_cut at 0 raise.
7. force_limited_airspeed(667.0, 0.35, 9.5, 1.5, 0.05, radians(30),
   0.20) = 71.472200 within 1e-3 (138.930842 kt within 0.01); the
   full-deflection pedal force at the leg-2 verdict (q 2741.311125) is
   584.391339 N within 1e-2, below 667; boost outside (0, 1] raises.
8. approach_run_class returns exactly "at-limit" for
   (54.925334, 54.925334, 71.472200) (boundary included) and for
   (65.853162, 65.853162, 71.472200); "control-lost" for
   (54.915334, 54.925334, 71.472200); "with-margin" for
   (71.472200, 54.925334, 71.472200) (boundary included); observed
   violation (bank 5.8, heading 23) at 70.0 overrides to
   "control-lost" and (bank 6.1, heading 19) at 60.0 overrides to
   "control-lost"; the three class strings are exactly the spec
   strings.
9. leg_verdict on the worked six-run leg-1 data (w_ref 170000, flap 25,
   v_auth 54.925334, v_force 71.472200): vmcl_cas = 55.489886 within
   1e-3 (equals the L1B corrected speed within 1e-9), vmcl_knots =
   107.863709 within 0.01, bracket_ok True with v_lost_max = 51.599843
   within 1e-3 below the verdict and v_margin_min = 72.500000 at or
   above it, n_qualifying = 4, n_lost = 1, n_margin = 1; the corrected
   run speeds match the table within 1e-3 each (51.599843, 55.489886,
   58.000000, 63.935270, 72.500000, 55.777561).
10. leg_verdict on the worked five-run leg-2 data (w_ref 185000, flap
    25, v_auth 65.853162, v_force 71.472200): vmcl_cas = 66.900000
    within 1e-3 (equals the L2B corrected speed within 1e-9),
    vmcl_knots = 130.043197 within 0.01, bracket_ok True with
    v_lost_max = 64.326379 within 1e-3 below the verdict and
    v_margin_min = 73.500000 at or above it, counts 3/1/1; corrected
    speeds 64.326379, 66.900000, 68.772755, 70.600000, 73.500000
    within 1e-3 each.
11. Removing the with-margin runs from either leg keeps bracket_ok True
    (single-sided brackets allowed); a manufactured verdict at or below
    the lost max flips bracket_ok False; leg_verdict raises on an empty
    run list and on a run list whose only run is control-lost (no
    at-limit run).
12. demonstration_summary(leg1, leg2) on the worked verdicts returns
    vmcl_cas = 66.900000 within 1e-9, vmcl_knots = 130.043197 within
    0.01 and governing_leg "vmcl-2"; with only the leg-1 verdict it
    returns 55.489886 and "vmcl-1".
13. At the governing verdict: q = 2741.311125 Pa within 0.01,
    required_deflection(1104000.0, 2741.311125, 42, 21, 0.90) =
    0.507341 within 1e-5 (29.068477 deg within 1e-3) below the
    0.523599 rad limit; pedal_force(2741.311125, 9.5, 1.5, 0.05,
    0.507341, 0.20, 0.35) = 566.245546 within 1e-2 and force_ok True;
    full-deflection pedal force at the verdict 584.391339 within 1e-2;
    authority margin vmcl - V_auth2 = 1.046838 within 1e-5; the
    leg-1 at-verdict values (q 1885.965550, delta_req 0.512999 rad,
    29.392668 deg, force 393.909945 N, margin 0.564552) within the
    same tolerances.
14. stall_guard_check(66.9, 52.7): guard_speed = 55.335 within 1e-9,
    verdict "stall-guard-ok", proximity 1.269450 within 1e-5;
    stall_guard_check(55.489886, 52.7) gives proximity 1.052939 within
    1e-5 below the 1.10 relevance threshold.
15. lateral_control_check(4.8): required_rate_deg_s = 4.0 within 1e-9,
    verdict "lateral-control-ok"; lateral_control_check(3.5) gives
    "lateral-control-insufficient"; zero available rate raises.
16. approach_margin_check(66.9, 68.51): margin_ok True, ratio 1.024066
    within 1e-5, clearance 1.610000 within 1e-6, verdict "margin-ok";
    approach_margin_check(66.9, 66.3) gives "vmcl-governs" with
    v_app_required 66.9; zero speeds raise.
17. Identities: weight_corrected_speed and flap_normalized_speed
    same-value degeneracies; the 4x-weight sqrt scaling; the flap
    round trip; the twin identity; the tri-jet identity; the quad
    contrast (768000.0 engine sum vs 2304000.0 resultant, recorded as
    the deviation); the class boundary strings; the verdict minima
    equal to the slowest qualifying run per leg.
18. ValueErrors: isa_sigma at h_p -1 and 12000 and at non-positive
    ambient temperature; tas_to_cas at 0; weight_corrected_speed at
    w_test 0; flap_normalized_speed at negative flap;
    post_cut_moment at empty engines or an empty cut set;
    second_cut_index on a two-engine layout;
    authority_limited_airspeed at delta_max 61 deg and y_cut 0;
    leg_verdict at empty and no-qualifying inputs;
    stall_guard_check, lateral_control_check and approach_margin_check
    at zero speeds.
19. Determinism: two full runs of the worked scenario produce
    byte-identical output; no imports beyond math; constants fixed
    (EXP about 5.2559, KT2MS 0.514444444444, F_LIM 667.0,
    BANK_LIM_DEG 5.0, HEADING_LIM_DEG 20.0, ROLL_DEG 20.0,
    ROLL_TIME_S 5.0).
20. Test passes under BOTH interpreters (/usr/bin/python3 3.9.6 and
    ~/.pyenv/versions/3.13.12/bin/python3). No exact-float equality on
    computed sums; use assertAlmostEqual/math.isclose everywhere.

## Corpus fragment (eval/hit1-wave45-vmcl-determination.yaml)

Query 1 (copy verbatim):
  "reduce the landing-configuration VMCL demonstration runs to the
  approach minimum-control-speed after the critical-engine cut with
  go-around thrust"
  intent: "flight-test-operations; FAR/CS 25.149(f) approach and
  landing minimum control speed VMCL reduction of the landing-
  configuration critical-engine-cut demonstration runs at go-around
  thrust with the bank-5-degree and 20-degree-heading-change run
  classification and the standard-condition corrections"
  expected_skill: "flight-test-operations/envelope/vmcl-determination"
Query 2 (copy verbatim):
  "VMCL-2 second-critical-engine cut on approach, three-degree path
  thrust change to go-around, directional control speed reduction"
  intent: "flight-test-operations; FAR/CS 25.149(g) VMCL-2 second-cut
  leg for three-plus-engine airplanes: second critical engine cut on
  approach with one engine inoperative and the operating engines at
  go-around thrust, directional control speed reduction against the
  landing configuration authority and pedal force limits"
  expected_skill: "flight-test-operations/envelope/vmcl-determination"
Task ids: w45-vmcl-determination-1 and -2. Prep grep (run at spec
time): each of the tokens vmcl-determination,
landing-minimum-control-speed, approach-configuration-control,
go-around-thrust, critical-engine-cut, most-favorable-weight and
second-engine-cut returns 0 matches in eval/hit1-corpus.yaml and in
every eval/*.yaml fragment (grep -c 0, grep -l empty), and
"vmcl|vmca" appears nowhere in skills/ or eval/, so the queries above
are collision-free; the sibling flight-test-operations tasks route on
the airborne takeoff-configuration minimum control speed demonstration
(vmc-determination), the ground minimum control speed
(vmcg-determination), the stall-derived speed multiples (v-speeds), the
unstick rotation verdict (vmu-determination), the all-engines landing
distance (landing-distance-determination) and the balanced-field
takeoff speeds (engine-failure-takeoff-flight-test), none of which
carry landing-configuration directional control content. The queries
deliberately carry only the qualified tokens above; a bare
minimum-control-speed or bare vmc query routes FTO-3762 to the
airborne takeoff-config sibling vmc-determination and must never be
used here.

## Description/tag guidance (gate 1/2 and tag-steal rules)

Description must open "Use when you must reduce the landing-
configuration approach-cut demonstration runs of a multi-engine
transport airplane flight test to the approach and landing minimum
control speeds VMCL and VMCL-2 in the spirit of the FAR/CS
25.149(f)/(g) method, summary-only:" and include the outputs in the
Claim. First tag: vmcl-determination. Additional tags ONLY:
landing-minimum-control-speed, approach-configuration-control,
go-around-thrust, critical-engine-cut, most-favorable-weight,
second-engine-cut. NEVER single generic words (speed, landing,
approach, cut, bank, heading, flap, thrust, engine, pedal, force,
rudder, weight) and NEVER bare minimum-control-speed or vmc/vmcl alone
(too generic; routes FTO-3762 to the airborne takeoff-config sibling
vmc-determination) nor any sibling token below. 50-150 words, <=1000
chars, no em dash, no content-policy sweep term (the banned word from
the builder kit), action verb present. Recommended wording (outputs
and verdict in Claim order, 141 words, 990 chars, verified):
"Use when you must reduce the landing-configuration approach-cut
demonstration runs of a multi-engine transport airplane flight test to
the approach and landing minimum control speeds VMCL and VMCL-2 in the
spirit of the FAR/CS 25.149(f)/(g) method, summary-only: build the
asymmetric yawing moment of the critical-engine cut over the operating
engine set, solve the rudder authority limited and 150 lbf pedal force
limited airspeeds with go-around thrust, classify each run by the
bank-5-degree and 20-degree-heading-change control criteria, correct
the demonstrated speeds to the most favorable weight and reference
landing flap, and add the VMCL-2 second-cut leg for three-plus-engine
airplanes with the go-around thrust change. Produces the predicted and
demonstrated VMCL in m/s and knots, the run-classed verdict with
bracket checks, the stall guard check, and the margin against the
operating approach speed set. Trigger: VMCL, VMCL-2, landing minimum
control speed, go-around thrust."

FORBIDDEN TOKENS (belong to siblings): vref, v2, vno, vne, vs0-multiple
derivation, stall-speed-multiple speed set (v-speeds);
minimum-control-speed alone, vmc alone, vmca, critical-engine ranking,
asymmetric-yawing-moment, windmilling-drag main-model content,
engine-inoperative-flight-test, rudder-authority airspeed demonstration
of the takeoff configuration, airborne takeoff-config Vmc
(vmc-determination); ground-minimum-control-speed,
nosewheel-steering-authority, steering-cutout-speed, vmcg, ground roll,
steering-free recovery (vmcg-determination); minimum-unstick-speed,
rotation-limit-speed, unstick-certification, tail-strike rotation limit
(vmu-determination); landing-distance, 50-ft obstacle, landing ground
roll, landing-distance-determination tag itself
(landing-distance-determination); balanced-field-v1, vef,
decision-speed, continued-takeoff (engine-failure-takeoff-flight-test);
vs1g-from-wing-loading, stall-speed computation
(stall-speed-determination); takeoff-field-length, climb-segment
(takeoff-distance-determination); engine-out-climb-gradient,
oei-climb-gradient (flight-mechanics oei-climb-gradient).
