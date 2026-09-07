---
name: vmcl-determination
description: "Use when you must reduce the landing-configuration approach-cut demonstration runs of a multi-engine transport airplane flight test to the approach and landing minimum control speeds VMCL and VMCL-2 in the spirit of the FAR/CS 25.149(f)/(g) method, summary-only: build the asymmetric yawing moment of the critical-engine cut over the operating engine set, solve the rudder authority limited and 150 lbf pedal force limited airspeeds with go-around thrust, classify each run by the bank-5-degree and 20-degree-heading-change control criteria, correct the demonstrated speeds to the most favorable weight and reference landing flap, and add the VMCL-2 second-cut leg for three-plus-engine airplanes with the go-around thrust change. Produces the predicted and demonstrated VMCL in m/s and knots, the run-classed verdict with bracket checks, the stall guard check, and the margin against the operating approach speed set. Trigger: VMCL, VMCL-2, landing minimum control speed, go-around thrust."
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
  tags: [vmcl-determination, landing-minimum-control-speed, approach-configuration-control, go-around-thrust, critical-engine-cut, most-favorable-weight, second-engine-cut]
  version: 0.1.0
  author: AeroSkills
---

# Approach and Landing Minimum Control Speeds VMCL / VMCL-2 (flight-test-operations/envelope/vmcl-determination)

Use when the task is the reduction of the landing-configuration
approach-cut demonstration runs of a multi-engine transport airplane
flight test to the approach and landing minimum control speeds VMCL and
VMCL-2, in the spirit of the FAR/CS 25.149(f)/(g) method, summary-only.
This leaf builds the asymmetric yawing moment of the critical-engine cut
over the operating engine set (the engine-by-engine sum of the go-around
thrusts at their signed lateral arms, with the cut engines contributing
nothing), solves the rudder authority limited and 150 lbf (667 N) pedal
force limited airspeeds at the landing configuration with go-around
thrust on the operating engines, classifies each approach-cut run by the
bank-5-degree and 20-degree-heading-change control criteria, corrects
every demonstrated run speed to the reference condition (most favorable
weight and reference landing flap for the (f) leg, most unfavorable
weight for the (g) leg), and adds the VMCL-2 second-cut leg for
three-plus-engine airplanes where a second critical engine is cut with
one already inoperative. It parallels the airborne takeoff-configuration
minimum control speed leaf
(flight-test-operations/envelope/vmc-determination), whose reduction
structure, boost-factor pedal force family and 150 lbf criterion it
shares, but the governing surface here is the approach and landing
configuration of FAR/CS 25.149(f)/(g): landing flap setting, approach
trim, go-around thrust on the operating engines, and the most favorable
and most unfavorable weight condition sets. The VMC family organizes by
leg: air and ground are claimed by the vmc-determination and
vmcg-determination siblings, and this leaf claims the approach and
landing leg. The windmilling drag of the failed engine is neglected in
the main model (small at approach speeds for jets) and enters only
through the optional s_f_cd term of the authority closed form, single
cut only. Differential braking, dynamic transients, sideslip coupling,
ground effect and the aileron control gearing itself are out of scope
(roll capability at the verdict is a consumed input); the propeller
position content of 25.149(f)(5)/(g)(5) is out of scope (jet transport
model). Single-layer ISA to 11 km only.

## Domain quick reference

- ISA density ratio at pressure altitude h_p with deviation dt_isa:
  delta = (1 - LAPSE*h_p/T0)**EXP, theta = (T0 - LAPSE*h_p + dt_isa)/T0,
  sigma = delta/theta. At 600 m with +12 K, sigma = 0.905430.
- TAS to CAS: v_cas = v_tas*sqrt(sigma); calibrated airspeed input needs
  no density correction.
- Weight correction at fixed lift coefficient: v_corr = v_cas*
  sqrt(w_ref/w_test); w_ref is the most favorable (minimum) approach
  weight for the (f) leg and the most unfavorable (maximum) approach
  weight for the (g) leg.
- Configuration normalization through the landing-configuration lift
  coefficient CL(f) = cl_0 + cl_per_deg*f: v_norm = v_cas*
  sqrt(CL(f_test)/CL(f_ref)); more flap, more lift, lower control speed,
  so a control speed measured at a lower flap setting normalizes down to
  the reference landing flap.
- Asymmetric yawing moment of the cut: N_asym = |sum of T_i*y_i over
  the engines still operating|, T_i the go-around thrust of engine i and
  y_i its signed lateral arm; the cut engines contribute no thrust. This
  engine-by-engine sum reduces exactly to the family static form
  T_op*|y_fail| for a twin and is the form the VMCL-2 second-cut
  geometry requires.
- First critical cut: the engine whose loss leaves the largest
  asymmetric moment; ties resolve to the lower index. Second critical
  cut (VMCL-2, three-plus-engine airplanes): among the engines still
  operating after the first cut, the one whose loss leaves the largest
  asymmetric moment.
- Rudder restoring: N_rud = q*S_v*l_v*C_Lv_delta_r*delta with
  q = 0.5*RHO_SL*V^2; the required deflection delta_req =
  N_asym/(q*S_v*l_v*C_Lv_delta_r) is capped at delta_r_max.
- Authority-limited airspeed: the speed where delta_req reaches
  delta_r_max, q* = N_asym/(S_v*l_v*C_Lv_delta_r*delta_r_max_rad -
  s_f_cd*|y_cut|), V_auth = sqrt(2*q*/RHO_SL); None when the denominator
  is not positive (never authority limited).
- Rudder pedal force: F = q*S_r*c_r*|C_h_delta_r|*min(delta_req,
  delta_r_max_rad)*boost_factor/pedal_arm_m, with the boost factor
  scaling felt force (1.0 manual, smaller for power-boosted systems).
- Pedal-force-limited airspeed: q_F = F_lim*pedal_arm/(S_r*c_r*
  |C_h_delta_r|*delta_r_max_rad*boost_factor) with F_lim = 667 N (the
  150 lbf criterion, paraphrased); V_force = sqrt(2*q_F/RHO_SL). It is
  leg-independent (depends only on the rudder geometry and the boost
  factor).
- Run classes: "control-lost" when the observed bank exceeded 5 deg or
  the recovery heading change exceeded 20 deg, or otherwise when V <
  V_auth (VMCL lies above this run); "at-limit" when held within the
  criteria and V_auth <= V < V_force (the VMCL-qualifying class);
  "with-margin" when held within the criteria and V >= V_force (VMCL
  lies at or below this run). Observed criteria violations override the
  speed class; observed compliance never overrides a speed-based loss.
- VMCL verdict: vmcl_leg = min of the corrected at-limit run speeds;
  bracket_ok requires the verdict to strictly exceed the fastest
  corrected control-lost run when present and to not exceed the slowest
  corrected with-margin run when present.
- Combined demonstrated VMCL: the governing leg carries the higher
  demonstrated value (the approach speed set must clear BOTH legs for a
  three-plus-engine airplane; a twin has only the (f) leg).
- Stall guard: guard_speed = 1.05*vs0 from the sibling stall leaf;
  "stall-guard-ok" when VMCL clears it, else "stall-guard-governs". A
  proximity vmcl/vs0 below 1.10 keeps the guard relevant.
- Lateral control check (25.149(h)(3), paraphrased): roll capability at
  the verdict must move the airplane through 20 degrees in not more
  than 5 seconds; the required average rate is 4 deg/s and the available
  roll rate is a consumed input.
- Approach margin check: margin-ok when the consumed reference approach
  speed v_app_ref >= vmcl (ratio reported); else "vmcl-governs" with
  v_app_required = vmcl.
- Units are SI: N, m, m/s, rad, deg, N m; knots = m/s * 1.94384.
- FAR/CS 25.149(f)/(g)/(h) frame the approach and landing minimum
  control speed test conditions (landing configuration, approach trim,
  go-around thrust on the operating engines, the most favorable (f) and
  most unfavorable (g) weight, the bank and heading criteria, the
  lateral control roll demand); the relations above are standard
  engineering methodology, summary-only.

## Workflow

1. Fix the landing configuration and atmosphere for the leg: the leg
   reference weight (most favorable for the (f) leg, most unfavorable
   for the (g) leg), the reference landing flap with the
   landing-configuration lift coefficient model CL(f) = cl_0 +
   cl_per_deg*f, and the ISA density ratio sigma at the test pressure
   altitude and temperature deviation (isa_sigma).
2. Identify the first critical cut and build the asymmetric yawing
   moment of the cut over the operating engine set (first_cut_index,
   post_cut_moment): the engine-by-engine sum of the go-around thrusts
   at their signed lateral arms with the cut engines contributing
   nothing.
3. For three-plus-engine airplanes identify the second critical cut
   among the engines still operating and build the VMCL-2 moment with
   one engine already inoperative (second_cut_index, post_cut_moment).
4. Solve the rudder authority limited airspeed from the closed form
   (authority_limited_airspeed), the airspeed where the required
   deflection (required_deflection) reaches the rudder limit; treat
   None as never authority limited.
5. Solve the pedal-force limited airspeed with the boost factor against
   the 667 N (150 lbf) pedal force criterion
   (force_limited_airspeed, pedal_force); it is leg-independent.
6. Correct each run speed to standard conditions and classify the run
   into the control-lost, at-limit and with-margin classes
   (corrected_run_speed, approach_run_class): TAS to CAS through the
   density ratio, weight correction to the leg reference weight, flap
   normalization through the landing-configuration lift coefficient,
   class from the measured CAS before corrections with the
   bank-5-degree and 20-degree-heading-change observed criteria.
7. Reduce the qualifying at-limit runs of the leg to the demonstrated
   VMCL verdict with the bracket consistency check against the
   control-lost and with-margin brackets (leg_verdict): vmcl_cas,
   vmcl_knots, bracket_ok and the run counts.
8. Combine the legs (demonstration_summary): the governing leg carries
   the higher demonstrated value, vmcl-1 or vmcl-2.
9. Check the demonstration at the governing verdict: required
   deflection below the rudder limit, required pedal force within the
   667 N limit (force_ok), the authority margin against the analytic
   authority limited airspeed, and the lateral control roll demand
   check (lateral_control_check).
10. Apply the stall protection guard on the landing-configuration
    reference stall speed (stall_guard_check) and check the margin
    against the operating approach speed set (approach_margin_check).

## Worked example

Reference condition set of the (f) leg: most favorable (minimum)
approach weight w_ref_1 = 170000 kg; reference landing flap 25.0 deg
with cl_0 = 0.90 and cl_per_deg = 0.030 per deg (CL(25) = 1.650,
CL(20) = 1.500). Reference condition of the (g) leg: most unfavorable
(maximum) approach weight w_ref_2 = 185000 kg at the same reference
flap. Four-engine widebody-class transport jet in the landing
configuration: go-around thrust 96000 N on every engine at the signed
arms y = -8.0, -3.5, +3.5, +8.0 m (outer left, inner left, inner right,
outer right). Fin S_v = 42 m2 at the CG-to-fin arm l_v = 21 m with
C_Lv_delta_r = 0.90 per rad, rudder limit 30 deg (0.523599 rad), rudder
S_r = 9.5 m2, c_r = 1.5 m, C_h_delta_r = 0.05 per rad, pedal arm 0.35 m,
boost factor 0.20 (power-boosted). Windmilling neglected. The
landing-configuration reference stall speed from the sibling stall leaf
is vs0 = 52.7 m/s and the operating approach reference speed from the
schedule (the v-speeds model places it at 1.3*vs0) is v_app_ref =
68.510000 m/s. Real module outputs:

- Atmosphere: isa_sigma(0, 0) = 1.000000; isa_sigma(600, +12) =
  0.905430; isa_sigma(600, 0) = 0.943654. tas_to_cas(66.8, 500, 8) =
  64.310260 m/s.
- Cut selection and leg moments: the first critical cut is index 0, the
  outer left engine at y = -8.0 m; the engine-sum moment of the
  remaining three engines is N1 = 768000.000000 N m (for the
  equal-thrust symmetric layout the moment of the cut engine's thrust
  at its own arm, 96000 * 8.0). With that engine inoperative the second
  critical cut is index 1, the same-side inner engine at y = -3.5 m:
  cutting it leaves the two right-side engines whose arm sum is
  8.0 + 3.5, so N2 = 96000 * 11.5 = 1104000.000000 N m. The second-cut
  moment exceeds the first-cut moment by 1.4375 times, so the VMCL-2
  leg is the harder demonstration for this quad.
- Analytic limits (landing configuration, go-around thrust):
  authority-limited airspeed leg 1: V_auth1 = 54.925334 m/s
  (106.766308 kt); leg 2: V_auth2 = 65.853162 m/s (128.008306 kt), the
  second-cut boundary exceeding the first-cut boundary by
  sqrt(11.5/8) = 1.198958. Force-limited airspeed (both legs, boost
  0.20): V_force = 71.472200 m/s (138.930842 kt), the speed where a
  full-deflection input demands the 667 N limit. Both legs predict
  71.472200 m/s governed by "pedal-force", the analytic upper bound of
  the qualifying band.
- Leg-1 runs (VMCL, 25.149(f): all engines operating, trimmed for
  approach, go-around thrust, critical cut at the run speed; class from
  the measured CAS before corrections, corrected to w_ref_1 and flap
  25): L1A 52.8 m/s CAS at 178000 kg with bank 6.3 deg and heading
  change 24 deg: control-lost (observed criteria violation, also below
  V_auth1), corrected 51.599843 m/s. L1B 56.3 m/s at 175000 kg, held:
  at-limit, corrected 55.489886 m/s (weight factor sqrt(170000/175000)
  = 0.985611). L1C 58.0 m/s at 170000 kg: at-limit, corrected
  58.000000. L1D 66.8 m/s TRUE airspeed at 500 m +8 K, 172000 kg: TAS
  to CAS 64.310260 m/s, still below V_force: at-limit, corrected
  63.935270 m/s (the altitude and temperature correction path). L1E
  72.5 m/s at 170000 kg: with-margin, corrected 72.500000. L1F 58.5 m/s
  at flap 20 (reference 25): at-limit, corrected 55.777561 m/s (CL
  1.500 to 1.650), the flap normalization path: the run measured at the
  lower flap setting normalizes down to 55.777561 m/s at the reference
  landing flap.
- Leg-1 verdict: vmcl_1 = 55.489886 m/s (107.863709 KCAS), the
  corrected speed of run L1B, the minimum of the four qualifying
  corrected speeds. Brackets: v_lost_max 51.599843 below the verdict
  and v_margin_min 72.500000 at or above it, bracket_ok True. Counts: 4
  at-limit, 1 control-lost, 1 with-margin. Checks at the leg-1 verdict:
  q = 1885.965550 Pa, delta_req = 0.512999 rad (29.392668 deg) below
  the 0.523599 rad limit, required pedal force 393.909945 N, authority
  margin vmcl_1 - V_auth1 = 0.564552 m/s. The leg-1 demonstration
  clears the stall guard by a whisker: guard 55.335000 m/s at proximity
  vmcl_1/vs0 = 1.052939, below the 1.10 threshold that keeps the guard
  relevant.
- Leg-2 runs (VMCL-2, 25.149(g): one critical engine already
  inoperative, trimmed for approach, second critical cut at the run
  speed, operating engines at go-around thrust; corrected to w_ref_2
  and flap 25): L2A 64.5 m/s CAS at 186000 kg with bank 5.8 deg and
  heading change 22 deg: control-lost, corrected 64.326379 m/s. L2B
  66.9 m/s at 185000 kg: at-limit, corrected 66.900000. L2C 68.4 m/s at
  183000 kg: at-limit, corrected 68.772755 m/s. L2D 70.6 m/s at 185000
  kg: at-limit (still below V_force), corrected 70.600000. L2E 73.5 m/s
  at 185000 kg: with-margin, corrected 73.500000.
- Leg-2 verdict: vmcl_2 = 66.900000 m/s (130.043197 KCAS), run L2B's
  corrected speed, the minimum of the three qualifying corrected
  speeds. Brackets: v_lost_max 64.326379 below the verdict and
  v_margin_min 73.500000 at or above it, bracket_ok True. Counts: 3
  at-limit, 1 control-lost, 1 with-margin.
- Combined demonstrated VMCL: the governing leg carries the higher
  demonstrated value, vmcl = 66.900000 m/s (130.043197 KCAS) from leg
  2, governing_leg "vmcl-2". For this quad the second-cut leg, not the
  all-engines cut, sets the approach speed floor: the first-cut leg
  demonstrates control down to 107.9 KCAS while the second-cut leg
  bottoms out at 130.0 KCAS.
- Demonstration checks at the governing verdict: q = 2741.311125 Pa,
  required deflection delta_req = 0.507341 rad (29.068477 deg) below
  the 0.523599 rad limit, required pedal force 566.245546 N within the
  667 N limit (force_ok True), full-deflection pedal force at the
  verdict 584.391339 N, and the authority margin vmcl - V_auth2 =
  1.046838 m/s above the analytic second-cut boundary.
- Stall guard (vs0 = 52.7 m/s): guard speed 1.05 * 52.7 = 55.335000 m/s
  well below the verdict, guard_verdict "stall-guard-ok"; proximity
  vmcl/vs0 = 1.269450, so the guard is not the binding check for the
  final verdict (the leg-1 proximity 1.052939 is the guard-relevant
  case).
- Lateral control: the required average roll rate is 20/5 = 4.000000
  deg/s; the available roll rate at the verdict, 4.8 deg/s (consumed
  input), clears it: lateral_verdict "lateral-control-ok".
- Approach margin: v_app_ref = 1.3 * 52.7 = 68.510000 m/s clears the
  demonstrated VMCL with ratio 1.024066 and clearance 1.610000 m/s:
  margin_verdict "margin-ok". The scheduled landing reference approach
  speed beats the second-cut minimum control speed by 1.61 m/s, a tight
  but legal 2.4% margin.
- Tri-jet cross-check (3-engine VMCL-2 case): three engines at 85000 N
  go-around thrust with wing engines at y = -7.5 and +7.5 m and a
  centerline tail engine at y = 0. First critical cut: wing engine
  (index 0). Second critical cut: the tail engine (index 1, y = 0):
  cutting it leaves only the remaining wing engine, so the VMCL-2
  moment equals the VMCL-1 moment exactly, 637500.000000 N m both legs
  (identity True). This is the case the engine-set sum exists for:
  cutting the y = 0 engine does not zero the residual moment of the
  remaining wing engine.
- Twin identity (shared-core reuse check): for the two-engine layout at
  +-8.0 m the engine sum gives 768000.000000 N m, exactly the family
  static form T_op*|y_fail| of the vmc/vmcg leaves. Quad contrast
  (deviation record): on the four-engine layout the engine sum gives
  768000.000000 N m for the first cut while the T_op*|y_fail| resultant
  convention of the sibling logic files gives 2304000.000000 N m; the
  engine set sum is the pinned multi-engine form here.
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

## Verification

- Confirm isa_sigma(0, 0) = 1.0 and isa_sigma(600, 12) = 0.905430 within
  1e-5; every computed aggregate in the contract test is asserted with a
  tolerance (no exact float equality on computed sums).
- Confirm the cut geometry: first critical cut index 0 and second
  critical cut index 1 on the quad; moments N1 768000.0 and N2
  1104000.0 N m; the twin identity and the tri-jet identity both hold.
- Confirm the authority closed form returns V_auth1 54.925334 m/s
  (106.766308 kt) and V_auth2 65.853162 m/s (128.008306 kt) with the
  sqrt(11.5/8) ratio.
- Confirm the pedal-force family: V_force 71.472200 m/s (138.930842 kt)
  at boost 0.20 against the 667 N (150 lbf) limit, and the required
  pedal force at each leg verdict (393.909945 N and 566.245546 N)
  within the limit.
- Confirm leg_verdict on the worked six-run leg-1 data returns
  55.489886 m/s with bracket_ok True, and on the worked five-run leg-2
  data returns 66.900000 m/s with bracket_ok True, corrected run tables
  within 1e-3 per run, and the single-sided bracket case stays
  bracket_ok True.
- Confirm demonstration_summary returns 66.900000 m/s (130.043197 KCAS)
  with governing_leg "vmcl-2"; the at-verdict checks (q 2741.311125 Pa,
  delta_req 0.507341 rad, pedal force 566.245546 N, full-deflection
  force 584.391339 N, authority margin 1.046838 m/s); the stall guard
  verdict "stall-guard-ok" with proximity 1.269450; the lateral control
  verdict "lateral-control-ok" at 4.8 deg/s available; and the approach
  margin verdict "margin-ok" with ratio 1.024066.
- Confirm ValueError rejection of non-physical inputs: isa_sigma outside
  [0, 11000] m and at non-positive ambient temperature, zero airspeeds,
  non-positive weights, negative flaps, cl_0 at 0, an empty engine list
  or cut set, a second cut on a twin, rudder limit outside (0, 60] deg,
  zero cut arm, boost outside (0, 1], empty run lists, lists with no
  at-limit run, and zero speeds in the stall guard, lateral control and
  approach margin checks.
- Run the contract test offline: python3
  scripts/test_vmcl_determination.py (35 tests, deterministic). It also
  passes under the pre-push hook interpreter
  (~/.pyenv/versions/3.13.12/bin/python3).

## Related leaves

- flight-test-operations/envelope/vmc-determination: the airborne
  takeoff-configuration minimum control speed demonstration with the
  windmilling drag contribution and the takeoff-config stall protection
  guard; this leaf owns the approach and landing configuration leg only.
- flight-test-operations/envelope/vmcg-determination: the ground minimum
  control speed with the nosewheel steering cutout and the
  steering-free ground roll reduction; this leaf owns the ground leg
  only.
- flight-test-operations/envelope/v-speeds: the stall-derived
  certification speed set; the operating approach reference speed
  consumed here sits at 1.3*vs0 per the v-speeds model.
- flight-test-operations/performance/stall-speed-determination: supplies
  the landing-configuration reference stall speed vs0 for the stall
  protection guard.
- flight-test-operations/envelope/vmu-determination: the minimum unstick
  rotation verdict, a takeoff rotation boundary without engine failure
  content.
- flight-test-operations/performance/landing-distance-determination:
  the all-engines landing distance and 50-ft obstacle reduction,
  downstream of the demonstrated VMCL.
- flight-test-operations/performance/engine-failure-takeoff-flight-test:
  the balanced-field V1 and takeoff decision speed of the takeoff
  regime; this leaf never derives V1.
- flight-test-operations/performance/takeoff-distance-determination: the
  all-engines takeoff distance of the takeoff regime.
- flight-mechanics/performance/oei-climb-gradient: the engine-out climb
  gradient of the second-segment regime, unrelated to the control speed
  demonstration.

## Pitfalls

- Using the resultant convention on a multi-engine layout: the
  T_op*|y_fail| static form of the vmc/vmcg siblings is exact for the
  twin layout only; on the quad it would overstate the first-cut moment
  by 3 times (2304000.0 vs the true engine-sum 768000.0 N m), and
  cutting a centerline engine at y = 0 would zero the residual moment of
  the remaining wing engines. Use the engine-by-engine sum over the
  operating set, which reduces to the static form on the twin.
- Confusing the leg that governs: for a three-plus-engine airplane the
  second-cut VMCL-2 leg (25.149(g), most unfavorable weight) usually
  sets the floor: the worked quad demonstrates 66.9 m/s on the second
  cut against 55.49 m/s on the first, 22 kt apart. A twin has only the
  (f) leg.
- Feeding a TAS value as CAS: a true airspeed run at altitude must be
  converted through the ISA density ratio before the corrections; using
  66.8 TAS as CAS at 500 m +8 K overstates the run by 2.49 m/s (64.310
  CAS is the real value).
- Misreading the class boundaries: runs below V_auth are control-lost
  (VMCL lies above them), V_auth itself is at-limit (boundary
  included), and V_force itself is with-margin; an observed bank beyond
  5 degrees or a recovery heading change beyond 20 degrees overrides
  any speed class to control-lost, and observed compliance never
  overrides a speed-based loss. Classify on the measured CAS before
  corrections.
- Applying the reference weight of the wrong leg: the (f) leg corrects
  to the most favorable (minimum) approach weight 170000 kg while the
  (g) leg corrects to the most unfavorable (maximum) weight 185000 kg;
  swapping them shifts every corrected run speed.
- Reporting the (f) leg verdict as final on a quad: the combined VMCL is
  the governing higher leg value; the leg-1 verdict 55.489886 m/s
  (107.9 KCAS) understates the control limit by 22 kt when the VMCL-2
  leg demonstrates 66.9 m/s (130.0 KCAS).
- Forgetting the 1.10 relevance threshold: the leg-1 stall guard
  proximity 1.052939 is the guard-relevant case, not the final verdict
  proximity 1.269450; report the proximity with every guard verdict.
- Scheduling the approach below the demonstrated VMCL: the approach
  speed set must clear BOTH legs; when v_app_ref falls short the verdict
  is vmcl-governs with v_app_required = vmcl, and this leaf checks the
  consumed schedule, it never derives the approach speed.

## Behavior contract (gate 3)

Run the deterministic contract test (stdlib unittest, offline):

    python3 scripts/test_vmcl_determination.py

The test covers the ISA atmosphere anchors and rejection range, the TAS
to CAS conversion, the weight correction anchors and degeneracies, the
flap normalization anchor and round trip through the
landing-configuration lift coefficient, the full correction chain on
the TAS run, the cut selection (first and second critical cuts) with the
quad moments, the twin identity, the quad contrast deviation record and
the tri-jet identity, the authority-limited airspeeds of both legs
against the worked anchors and their sqrt(11.5/8) ratio, the
force-limited airspeed against the 667 N criterion, the required
deflection and pedal force family, the three run class boundary strings
and the observed-criteria overrides, the six-run leg-1 and five-run
leg-2 verdicts with the bracket consistency checks, corrected run tables
and counts, the combined summary with the governing leg, the at-verdict
demonstration checks of both legs, the stall guard verdicts, the lateral
control check, the approach margin check, the module constants, the
determinism of two full scenario runs, and ValueError rejection of every
non-physical input.

## Compliance

- Standards referenced, not reproduced: FAR/CS 25.149(f)/(g)/(h) (14 CFR
  Part 25 and CS-25) frame the approach and landing minimum control
  speed test conditions and the 150 lbf pedal force criterion; the
  relations above are standard engineering methodology, summary-only per
  standards-map.yaml.
- compliance: STANDARDS-REF, gated: false.
