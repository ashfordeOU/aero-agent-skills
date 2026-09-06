# Wave-43 leaf spec: vmu-determination (flight-test-operations,
# envelope pack)

- Path: skills/flight-test-operations/envelope/vmu-determination/
- Pack: envelope (present siblings envelope-expansion, v-speeds,
  load-factor-envelope, stall-characteristics-testing,
  flight-loads-survey, structural-coupling-test, high-angle-of-attack-
  testing, spin-testing, icing-flight-test, buffet-boundary-testing,
  vmc-determination; adjacent fences in
  flight-test-operations/performance (stall-speed-determination,
  takeoff-distance-determination, accelerate-stop-distance,
  engine-failure-takeoff-flight-test) and in vehicle-design/sizing
  (landing-gear-layout)).
- Claim fences (quoted from the sibling frontmatter at prep, none owns
  the minimum unstick speed reduction of the takeoff rotation runs):
  - v-speeds (this pack) computes the certification speed SET from
    stall speeds: its description reads "derive the vref reference
    landing speed as 1.3 times the vs0 stalling speed in landing
    configuration, the v2 takeoff safety speed as 1.2 times the vs1
    stalling speed in takeoff configuration, and the vr rotation speed
    as 1.1 times vs1". No unstick speed, no rotation-limit check, no
    measured-run reduction anywhere in the leaf; Vr there is a stall
    multiple, not a demonstrated rotation-limit speed.
  - vmc-determination (this pack) owns the minimum control AIR speed,
    the FAR 25.149 demonstration: its description reads "identify the
    critical engine from the engine-out yawing moment geometry, build
    the asymmetric yawing moment from the operating-engine thrust at
    the failed engine lateral arm plus the windmilling drag
    contribution, solve the rudder authority limited speed, apply the
    rudder pedal force criterion with the boost factor against the 150
    lbf pedal limit". The new leaf parallels its reduction structure
    (run inputs, per-run checks, standard-condition verdict) but the
    governing limit is the GROUND rotation-to-tail-strike unstick
    boundary of FAR 25.107(b), not engine-out directional control.
  - takeoff-distance-determination (performance, this family) covers
    the 35-ft obstacle distance: its description reads "integrate the
    measured ground speed samples over the ground roll, add the
    rotation distance at the rotation speed, and close the airborne
    climb segment to the 35 ft obstacle height with the climb rate".
    No unstick limit, no rotation-limit classification; it consumes a
    rotation speed instead of producing one.
  - landing-gear-layout (vehicle-design/sizing) owns the tail-strike
    rotation GEOMETRY margin: its description reads "compute the
    tipback angle at the aft CG limit about the main gear contact, the
    tail strike clearance angle at rotation, the lateral turnover
    angle from the wheel track", its quick reference fixes
    ROTATION_REF_DEG = 10.0 deg as "the typical transport unstick
    rotation reference", and its worked example reports a tail strike
    at 16.2602 deg with a 6.2602 deg margin against that 10.0 deg
    reference. The GEOMETRY (limit angle available before tail
    contact) is theirs; the SPEED at which that limit is reached
    during takeoff rotation runs is this leaf's verdict.
  - stall-speed-determination (performance, this family) computes Vs1g
    from wing loading and weight; it supplies the reference Vs1 input
    used in the stall floor check here, it does not touch unstick.
  - engine-failure-takeoff-flight-test and accelerate-stop-distance
    (performance, this family) own the balanced-field decision speed
    V1 with VEF recognition and the rejected-takeoff stop; the new
    leaf gates V1/VR scheduling by the Vmu verdict but does not
    compute V1, VEF or stopping distance.
  Whole-tree greps at prep: "vmu|unstick" returns matches ONLY inside
  vehicle-design/sizing/landing-gear-layout (geometry context, the
  ROTATION_REF_DEG = 10.0 deg reference and the 6.2602 deg margin
  worked example) and zero hits in any flight-test-operations leaf;
  the corpus tokens vmu-determination, minimum-unstick-speed,
  rotation-limit-speed and unstick-certification return 0 hits in
  eval/hit1-corpus.yaml and in every eval/*.yaml fragment (grep -l
  empty, grep -c 0 per token). GENUINE flight-test-operations gap
  (probe receipt C4, verified zero-owner, GO): no leaf reduces the
  takeoff rotation runs to the FAR 25.107(b) minimum unstick speed.
- Standards id: far-25 (14 CFR Part 25: Airworthiness Standards for
  Transport Category Airplanes) and cs-25 (CS-25: Certification
  Specifications and Acceptable Means of Compliance for Large
  Aeroplanes), both reference-only and both present in
  standards-map.yaml. Ledger Standard: far-25, cs-25.
- Family: flight-test-operations

## Claim

Reduce the takeoff rotation runs of a transport airplane flight test
to the minimum unstick speed Vmu in the spirit of the FAR/CS 25.107(b)
method, summary-only. Per run, take the measured liftoff/rotation speed
(calibrated airspeed by default, true airspeed accepted) at the test
gross weight, test pressure altitude, ISA temperature deviation and
flap setting, then classify the run geometrically against the certified
tail-strike/rotation limit: a run that reached the limit and unstuck is
the Vmu-qualifying class limit-unstick; a run that reached the limit
without unsticking proves Vmu lies ABOVE its speed (no-unstick lower
bracket); a run that unstuck before reaching the limit proves Vmu lies
at or BELOW its speed (premature-unstick upper bracket). Correct every
qualifying speed to standard conditions: true to calibrated airspeed
through the ISA density ratio sigma at the test altitude and
temperature deviation, weight correction v*sqrt(w_ref/w_test) to the
reference takeoff weight, and configuration normalization to the
reference takeoff flap through the rotation-limit lift coefficient
CL(f) = cl_0 + cl_per_deg*f. Issue the Vmu verdict as the minimum of
the corrected limit-unstick run speeds, in m/s and knots, with the
bracket consistency check against the fastest no-unstick and the
slowest premature-unstick runs. Then gate the V1/VR scheduling: report
the certification margins against the 1.08*Vmu liftoff constraint (the
geometrically limited transport liftoff margin, VLOF >= 1.08*Vmu with
all engines operative) and the 1.10*Vs1 rotation floor (the
stall-based floor on the scheduled rotation speed, where Vs1 is the
takeoff-configuration reference stall speed supplied by the sibling
stall-speed-determination leaf), each check applied where the
corresponding scheduled speed is supplied, and output the rotation
speed required to clear the Vmu gate when the supplied schedule falls
short. Does NOT do: the Vref/V2/Vr speed set computed from stall
speeds (v-speeds); Vmc and the engine-inoperative control limit
(vmc-determination); ground roll, rotation distance or the 35-ft
obstacle takeoff distance (takeoff-distance-determination); tail-strike
clearance or tipback GEOMETRY angles or the 10.0 deg unstick rotation
reference margin (landing-gear-layout); Vs1g from wing loading
(stall-speed-determination); balanced-field V1, VEF or rejected-takeoff
stopping (engine-failure-takeoff-flight-test, accelerate-stop-
distance). All-engines-operating reductions only; the 1.04*Vmu
engine-inoperative liftoff margin, sideslip, dynamic rotation-rate
transients and ground-effect aerodynamics beyond the sigma density
correction are out of scope. Single-layer ISA to 11 km only.

## Model (implement exactly)

Pure stdlib, math only, closed form. Module constants: RHO_SL = 1.225
kg/m3, T0 = 288.15 K, LAPSE = 0.0065 K/m, G0 = 9.80665 m/s2, R_AIR =
287.05 J/(kg K), EXP = G0/(R_AIR*LAPSE) (about 5.2559, the ISA pressure
exponent), KT2MS = 0.514444444444 m/s per knot (1852/3600). KT2MS
appears only to quote the verdict in knots; every speed verdict is a
CAS m/s value at reference conditions.

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
  sqrt(CL(f_test)/CL(f_ref)); more flap, more lift, lower unstick
  speed, so speeds measured at a lower flap setting rise when
  normalized up to the reference flap.
- Unstick boundary: the airplane unsticks when the wing lift at the
  achieved rotation angle carries the weight; the certified
  tail-strike/rotation limit angle theta_lim is the geometric stop of
  the demonstration, so the run class follows from theta_unstick
  versus theta_lim and from whether liftoff occurred at all.

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
- rotation_run_class(theta_unstick, unstuck, theta_lim) -> str
  "no-unstick" when unstuck is False (the limit was reached, no
  liftoff; Vmu lies above this run); "limit-unstick" when unstuck and
  theta_unstick >= theta_lim (the Vmu-qualifying class); otherwise
  "premature-unstick" (unstuck before reaching the limit; Vmu lies at
  or below this run). ValueError if theta_lim <= 0 or theta_unstick
  < 0.
- corrected_run_speed(v_meas, w_test, w_ref, flap_test, flap_ref,
  cl_0, cl_per_deg, h_p = 0.0, dt_isa = 0.0, tas_input = False) ->
  float
  the full standard-condition reduction of one measured liftoff speed:
  tas_to_cas first when tas_input (CAS input is used directly), then
  weight_corrected_speed, then flap_normalized_speed. ValueError if
  v_meas <= 0 (CAS path) or any argument fails its sub-check; the
  chain is commutative with the flap factor at 1.0.
- vmu_verdict(runs, theta_lim, w_ref, flap_ref, cl_0, cl_per_deg) ->
  dict
  reduces the run list. Each run dict: id, speed (m/s), weight (kg),
  flap (deg), theta (deg, pitch at unstick; the limit angle for
  no-unstick runs), unstuck (bool), h_p (m), dt_isa (K),
  tas_input (bool, default False). Per run computes the corrected
  speed and the class; vmu_cas = min of the corrected limit-unstick
  speeds; vmu_knots = vmu_cas/KT2MS; reports v_no_unstick_max and
  v_premature_min (None when a bracket is empty), bracket_ok (True
  only when vmu strictly exceeds the no-unstick max when present and
  does not exceed the premature-unstick min when present) and
  n_qualifying. ValueError if runs is empty or no run classifies as
  limit-unstick (Vmu not defined by the data).
- liftoff_margin_108(vmu_cas, v_lof_cas) -> dict
  the geometrically limited liftoff margin: required_108 = 1.08*vmu,
  margin_mps = v_lof - required_108, ratio_vlof_over_vmu, met = v_lof
  >= 1.08*vmu (all engines operative). ValueError if either speed
  <= 0.
- scheduling_gate(vmu_cas, vr_cas, vs1_cas = None) -> dict
  the V1/VR scheduling gate: vmu gate met = vr >= 1.08*vmu
  (req_vr_vmu_108); when vs1_cas is supplied, the stall floor met =
  vr >= 1.10*vs1 (req_vr_stall_110); vr_required = max of the
  applicable floors; verdict "ok", "vmu-gated", "stall-gated" or
  "dual-gated". ValueError if any supplied speed <= 0. This leaf only
  CHECKS a supplied schedule; it never derives Vr from Vs1 (that is
  the v-speeds computation).

Identities to test (closed form, exact):
- isa_sigma(0, 0) == 1.0 exactly and tas_to_cas(v, 0, 0) == v exactly;
  sigma falls with warm-day altitude: sigma(600, +12) < sigma(600, 0)
  < 1 (real anchor 0.905430 vs 0.943654).
- Same-weight and same-flap degeneracy:
  weight_corrected_speed(v, w, w) == v and flap_normalized_speed(v, f,
  f, cl_0, cl_per_deg) == v exactly; corrected_run_speed with
  tas_input False, w_test == w_ref and flap_test == flap_ref returns
  the input unchanged.
- Weight sqrt scaling: weight_corrected_speed(v, w, 4*w) == 2*v
  exactly (real anchor 120.000000 from 60.0).
- Flap normalization round trip:
  flap_normalized_speed(flap_normalized_speed(v, f1, f2, ...), f2,
  f1, ...) == v within 1e-9 (real anchor residual 0.000e+00) and the
  normalization direction is correct: a speed measured at the lower
  flap setting 10 deg rises when normalized to 15 deg (real anchor
  60.611957 from 62.9, CL 1.300 to 1.400).
- Reduction chain: corrected_run_speed with tas_input True equals
  weight_corrected_speed(tas_to_cas(v, h, dt), w, w_ref) when the flap
  factor is 1.0 (real anchor 61.855904 on both sides, residual
  0.000e+00).
- Class boundaries: theta >= theta_lim with unstuck is limit-unstick
  (boundary included: 11.0 vs 11.0), theta < theta_lim with unstuck is
  premature-unstick, unstuck False is no-unstick at any theta; the
  three class strings are exactly the spec strings.
- Verdict minimum: vmu_cas equals the corrected speed of the fastest
  qualifying run only when that run is the minimum; in the worked data
  vmu = run 5's corrected speed (61.175752) exactly, since run 5 is
  the minimum of the three limit-unstick runs (61.385567, 61.855904,
  61.175752).
- Bracket logic: bracket_ok True with v_no_unstick_max < vmu <
  v_premature_min in the worked data (59.6 < 61.175752 <= 62.9), and
  removing the premature run keeps bracket_ok True while removing the
  no-unstick run also keeps it True (single-sided brackets allowed).
- Margin identity: required_108 == 1.08*vmu_cas exactly; the liftoff
  margin met flips to False when v_lof drops below 1.08*vmu (real
  anchor margin 0.330187 m/s at v_lof 66.4, met True); scheduling gate
  verdict is "vmu-gated" when the stall floor is met but 1.08*vmu is
  not, with vr_required == 1.08*vmu.
- Stall proximity: worked vmu/vs1 = 1.054754 sits below 1.10, the
  stall-proximity threshold that keeps the stall guard relevant.
- ValueErrors across the module: isa_sigma at h_p -1 and 12000 and at
  a non-positive ambient temperature; tas_to_cas at v_tas 0;
  weight_corrected_speed at w_test 0 and w_ref 0; flap_normalized_speed
  at negative flap, cl_0 0, cl_per_deg -0.01 and at a non-positive
  lift coefficient; rotation_run_class at theta_lim 0 and theta_unstick
  -1; vmu_verdict on an empty list and on a list with no
  limit-unstick run; liftoff_margin_108 and scheduling_gate at zero
  speeds; scheduling_gate at vs1_cas 0.
- Determinism; no imports beyond math; constants fixed (EXP about
  5.2559, KT2MS 0.514444444444).

## Worked example

Reference takeoff weight w_ref = 79000 kg, certified
tail-strike/rotation limit theta_lim = 11.0 deg, reference takeoff
flap flap_ref = 15.0 deg with cl_0 = 1.10 and cl_per_deg = 0.020 per
deg (CL_lim(15) = 1.400, CL_lim(10) = 1.300). Test day: pressure
altitude 600 m, ISA deviation +12 K. The takeoff-configuration stall
speed from the sibling leaf is vs1 = 58.0 m/s, the scheduled rotation
speed is vr = 63.9 m/s and the scheduled liftoff speed is v_lof = 66.4
m/s. All values below are REAL outputs of the prep anchor
/tmp/w43spec/anchor_vmu.py (stdlib math, closed form).
- Atmosphere: isa_sigma(600, +12) = 0.905430, sqrt(sigma) = 0.951541;
  isa_sigma(600, 0) = 0.943654; isa_sigma(0, 0) = 1.000000. The warm
  day at 600 m is about 5% less dense than sea level standard.
  tas_to_cas(64.8, 600, 12) = 61.659846 m/s.
- Rotation run classification (theta_lim = 11.0 deg): theta 11.4
  unstuck -> limit-unstick; 9.8 unstuck -> premature-unstick; 11.0
  NOT unstuck -> no-unstick (limit reached, no liftoff); 11.2 unstuck
  -> limit-unstick; 11.3 unstuck -> limit-unstick; 10.2 unstuck ->
  premature-unstick; 11.0 unstuck -> limit-unstick (boundary
  included).
- Per-run corrections and classes (all runs at flap 15 deg except
  where noted, so the flap factor is 1.0 in the verdict data):
  - run 1: v 60.8 m/s CAS, 77500 kg -> corrected 61.385567 m/s,
    limit-unstick (theta 11.4).
  - run 2: v 62.9 m/s CAS, 79000 kg -> corrected 62.900000 m/s,
    premature-unstick (theta 9.8): unstuck before the limit, upper
    bracket only.
  - run 3: v 59.6 m/s CAS, 79000 kg -> corrected 59.600000 m/s,
    no-unstick (limit reached at theta 11.0, no liftoff): lower
    bracket, Vmu lies above this speed.
  - run 4: v 64.8 m/s TRUE airspeed (tas_input), 78500 kg: TAS to CAS
    61.659846 m/s, then weight correction to 61.855904 m/s,
    limit-unstick (theta 11.2). Demonstrates the altitude and
    temperature correction path on a warm-day 600 m run.
  - run 5: v 60.2 m/s CAS, 76500 kg -> corrected 61.175752 m/s,
    limit-unstick (theta 11.3).
  Weight corrections alone: (60.8, 77500 to 79000) = 61.385567 m/s,
  (60.2, 76500 to 79000) = 61.175752 m/s; the weight factor
  sqrt(79000/77500) = 1.009631 pulls the heavy-run speeds up about
  1%.
- Vmu verdict: vmu_cas = 61.175752 m/s, the minimum of the three
  qualifying corrected speeds (61.385567, 61.855904, 61.175752), i.e.
  run 5 exactly; vmu_knots = 118.916149 KCAS. Brackets:
  v_no_unstick_max = 59.6 m/s below the verdict and
  v_premature_min = 62.9 m/s at or above it, so bracket_ok = True and
  the verdict is bracketed by real run evidence: the airplane failed
  to unstick at 59.6 m/s, unstuck at the limit at 61.176 m/s, and had
  unstuck prematurely by 62.9 m/s.
- Certification margins (vs1 = 58.0 m/s, vr = 63.9 m/s, v_lof = 66.4
  m/s):
  - Liftoff constraint (1.08*Vmu, AEO): required_108 = 66.069813 m/s;
    margin = 66.4 - 66.069813 = 0.330187 m/s; ratio v_lof/vmu =
    1.085397 >= 1.08, met = True. The scheduled liftoff clears the
    geometrically limited margin by about a third of a m/s.
  - Rotation stall floor (1.10*Vs1): required = 63.800000 m/s;
    vr 63.9 >= 63.8, met = True.
  - Vmu gate on the scheduled rotation speed: vr 63.9 is BELOW
    1.08*vmu = 66.069813 m/s, so vmu_gate_met = False and the gate
    verdict is "vmu-gated": vr_required = 66.069813 m/s. The Vmu
    verdict forces the rotation speed up by 2.17 m/s (or the V1
    schedule down) before the certification takeoff is consistent
    with the demonstrated minimum unstick speed.
  - Stall proximity: vmu/vs1 = 1.054754, below the 1.10 threshold,
    the regime where the stall guard remains relevant.
- Read-off: this airplane demonstrates Vmu near 118.9 KCAS at MTOW
  conditions. The tail-strike-limited liftoff clears 1.08*Vmu with
  only 0.33 m/s to spare, while the stall-based rotation speed of
  63.9 m/s (124.2 KCAS) sits 2.17 m/s below the 1.08*Vmu gate, so the
  Vmu verdict governs the takeoff speed schedule. The flap
  normalization path is shown separately: a hypothetical run at 10 deg
  flap with v = 62.9 m/s CAS would normalize to 60.611957 m/s at the
  15 deg reference (CL 1.300 to 1.400), a 3.6% speed drop from the
  extra flap lift.
Run your module and take the real outputs as assert targets; the
anchors above are real prep outputs of /tmp/w43spec/anchor_vmu.py
(stdlib math, closed form, exit 0).

## Validation list (contract test must include)

- isa_sigma(0, 0) = 1.0 within 1e-12; isa_sigma(600, 12) = 0.905430
  within 1e-5 and below isa_sigma(600, 0) = 0.943654;
  tas_to_cas(64.8, 600, 12) = 61.659846 within 1e-3; tas_to_cas(v, 0,
  0) = v within 1e-12.
- weight_corrected_speed(60.8, 77500, 79000) = 61.385567 within 1e-3;
  weight_corrected_speed(60.2, 76500, 79000) = 61.175752 within 1e-3;
  weight_corrected_speed(60.0, w, 4*w) = 120.0 within 1e-9;
  same-weight call returns the input within 1e-12.
- flap_normalized_speed(62.9, 10, 15, 1.10, 0.020) = 60.611957 within
  1e-3 (CL 1.300 to 1.400); same-flap call returns the input; the
  10-to-15-to-10 round trip returns 62.9 within 1e-9; negative flap
  and cl_0 at 0 raise.
- corrected_run_speed(64.8, 78500, 79000, 15, 15, 1.10, 0.020, 600,
  12, tas_input = True) = 61.855904 within 1e-3 and equals the manual
  chain weight_corrected_speed(tas_to_cas(64.8, 600, 12), 78500,
  79000) within 1e-9.
- rotation_run_class returns exactly "limit-unstick" for (11.4, True,
  11.0) and (11.0, True, 11.0), "premature-unstick" for (9.8, True,
  11.0), "no-unstick" for (11.0, False, 11.0); theta_lim at 0 and
  theta_unstick at -1 raise.
- vmu_verdict on the worked five-run data: vmu_cas = 61.175752 within
  1e-3 (equals the run 5 corrected speed within 1e-9), vmu_knots =
  118.916149 within 0.01, bracket_ok True with v_no_unstick_max = 59.6
  within 1e-9 below the verdict and v_premature_min = 62.9 at or above
  it, n_qualifying = 3; the corrected run speeds match the table
  within 1e-3 each.
- vmu_verdict raises on an empty run list and on a run list whose only
  run is premature-unstick (no limit-unstick run).
- liftoff_margin_108(61.175752, 66.4): required_108 = 66.069813 within
  1e-3, margin_mps = 0.330187 within 1e-3, ratio 1.085397 within 1e-5,
  met True; the same call with v_lof = 66.0 gives met False.
- scheduling_gate(61.175752, 63.9, 58.0): vmu_gate_met False,
  stall_floor_met True, req_vr_vmu_108 = 66.069813 within 1e-3,
  req_vr_stall_110 = 63.8 within 1e-9, vr_required = 66.069813 within
  1e-3, verdict "vmu-gated"; with vr = 67.0 the verdict is "ok" and
  with vr = 63.0 and vs1 = 58.0 it is "dual-gated".
- ValueErrors: isa_sigma at h_p -1 and 12000 and at a non-positive
  temperature; tas_to_cas at 0; weight_corrected_speed at w_test 0;
  flap_normalized_speed at cl_per_deg -0.01; liftoff_margin_108 at a
  zero speed; scheduling_gate at vr 0 and at vs1_cas 0.
- Determinism; no imports beyond math; constants fixed.

## Corpus fragment (eval/hit1-wave43-vmu-determination.yaml)

Query 1 (copy verbatim):
  "reduce the takeoff rotation runs of the transport flight test to
  the vmu-determination minimum-unstick-speed with the
  rotation-limit-speed tail strike check and the standard weight and
  density corrections"
  intent: "flight-test-operations; FAR 25.107(b) minimum unstick
  speed reduction from measured takeoff rotation runs with the
  certified rotation-limit classification and the standard-condition
  weight and density corrections"
  expected_skill: "flight-test-operations/envelope/vmu-determination"
Query 2 (copy verbatim):
  "issue the unstick-certification verdict from the corrected
  rotation runs that gates the V1 and VR scheduling against the 1.08
  Vmu liftoff margin and the 1.10 Vs1 stall floor"
  intent: "flight-test-operations; Vmu verdict from corrected
  rotation runs gating the V1/VR schedule against the 1.08 Vmu
  liftoff margin and the 1.10 Vs1 rotation stall floor"
  expected_skill: "flight-test-operations/envelope/vmu-determination"
Task ids: w43-vmu-determination-1 and -2. Prep grep (run at spec
time): each of the tokens vmu-determination, minimum-unstick-speed,
rotation-limit-speed and unstick-certification returns 0 matches in
eval/hit1-corpus.yaml and in every eval/*.yaml fragment (grep -c 0,
grep -l empty), and "vmu|unstick" appears in the skills tree only in
vehicle-design/sizing/landing-gear-layout (geometry context), so the
queries above are collision-free; the sibling flight-test-operations
tasks route on stall-derived speed multiples (v-speeds), the
engine-out control limit (vmc-determination), the 35-ft obstacle
distance (takeoff-distance-determination) and the rejected-takeoff
decision speed (accelerate-stop-distance), none of which carry unstick
or rotation-limit content.

## Description/tag guidance (gate 1/2 and tag-steal rules)

Description must open "Use when you must reduce the takeoff rotation
runs of a transport airplane flight test to the minimum unstick speed
Vmu in the spirit of the FAR/CS 25.107(b) method, summary-only:" and
include the outputs in the Claim. First tag: vmu-determination.
Additional tags ONLY: minimum-unstick-speed, rotation-limit-speed,
unstick-certification, takeoff-rotation-run. NEVER single generic
words (speed, unstick, rotation, takeoff, liftoff, stall, weight,
density, flap, altitude, certification) and NEVER vmu alone (too
generic) nor any sibling token below. 50-150 words, <=1000 chars, no
em dash, no content-policy sweep term (the banned word from the
builder kit), action verb present. Recommended wording
(outputs and verdict in Claim order, 133 words, 897 chars, verified):
"Use when you must reduce the takeoff rotation runs of a transport
airplane flight test to the minimum unstick speed Vmu in the spirit of
the FAR/CS 25.107(b) method, summary-only: classify each measured
rotation run against the certified tail-strike rotation limit, correct
each liftoff speed from the test weight, altitude, temperature, and
flap setting to the reference conditions, and take the minimum
corrected speed of the limit-reaching runs as the Vmu verdict with the
no-unstick and premature-unstick bracket checks. Produces the
corrected run table, the Vmu in m/s and knots, the bracket consistency
verdict, and the certification margins against the 1.08 Vmu liftoff
constraint and the 1.10 Vs1 rotation floor that gate the V1/VR
scheduling. Trigger: minimum unstick speed, vmu determination,
rotation limit speed, unstick certification, tail strike rotation
limit, takeoff rotation run."

FORBIDDEN TOKENS (belong to siblings): vref, v2, vno, vne, vs0,
vr-as-1.1-times-vs1 derivation, stall-speed-multiple speed set
(v-speeds); minimum-control-speed, vmc, critical-engine,
asymmetric-yawing-moment, rudder-pedal-force, windmilling-drag,
150-lbf, engine-inoperative control limit (vmc-determination);
ground-roll-integration, rotation-distance, 35-ft-obstacle,
takeoff-field-length, climb-segment (takeoff-distance-determination);
tipback-angle, tail-strike-clearance-angle, lateral-turnover-angle,
nose-gear-load-fraction, wheel-track, tail-strike geometry margin
against the 10.0 deg reference (landing-gear-layout, vehicle-design);
vs1g-from-wing-loading, stall-speed computation (stall-speed-
determination); balanced-field-v1, vef, rejected-takeoff-stop,
braking-deceleration (engine-failure-takeoff-flight-test,
accelerate-stop-distance).
