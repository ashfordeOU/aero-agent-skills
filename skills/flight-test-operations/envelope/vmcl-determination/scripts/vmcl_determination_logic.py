"""vmcl_determination_logic.py

Approach and landing minimum control speeds VMCL and VMCL-2 for the
landing-configuration approach-cut demonstration runs of a multi-engine
transport airplane flight test, in the spirit of the FAR/CS 25.149(f)/(g)
method, summary-only.

This module implements the standard-engineering closed-form model of the
spec (ops/automation/state/wave45-specs/vmcl-determination.md): the
asymmetric yawing moment of the critical-engine cut over the operating
engine set (the engine-by-engine sum of the go-around thrusts at their
signed lateral arms, the cut engines contributing nothing), the rudder
authority-limited and 150 lbf (667 N) pedal-force-limited airspeeds at
the landing configuration with go-around thrust on the operating
engines, the bank-5-degree and 20-degree-heading-change run
classification, the standard-condition corrections (ISA density ratio,
weight correction to the most favorable or most unfavorable reference
weight, landing-configuration lift coefficient flap normalization), the
per-leg demonstrated verdict with the bracket consistency check, the
VMCL-2 second-cut leg for three-plus-engine airplanes, the stall
protection guard on the landing-configuration reference stall speed and
the approach margin check against the operating approach speed set.

Every speed verdict is a CAS m/s value at reference conditions; knots
appear only to quote the verdict. The windmilling drag of the failed
engine is neglected in the main model (small at approach speeds for
jets) and enters only through the optional s_f_cd term of the authority
closed form, single cut only. Pure Python stdlib (math only),
deterministic, no network.
"""

import math

# ISA single-layer standard atmosphere to 11 km.
RHO_SL = 1.225          # sea level density, kg/m3
T0 = 288.15             # sea level temperature, K
LAPSE = 0.0065          # temperature lapse rate, K/m
G0 = 9.80665            # standard gravity, m/s2
R_AIR = 287.05          # specific gas constant, J/(kg K)
EXP = G0 / (R_AIR * LAPSE)   # ISA pressure exponent, about 5.2559
KT2MS = 0.514444444444  # m/s per knot, 1852/3600
F_LIM = 667.0           # 150 lbf rudder pedal force criterion, N (paraphrased)
STALL_GUARD = 1.05      # stall protection guard factor on the reference stall speed
BANK_LIM_DEG = 5.0      # bank criterion of the approach-cut run, deg
HEADING_LIM_DEG = 20.0  # heading change criterion of the approach-cut run, deg
ROLL_DEG = 20.0         # lateral control roll demand of the check, deg
ROLL_TIME_S = 5.0       # lateral control time demand of the check, s


def isa_sigma(h_p, dt_isa=0.0):
    """ISA density ratio delta/theta at pressure altitude h_p (m) with
    temperature deviation dt_isa (K), single-layer closed form.

    delta = (1 - LAPSE*h_p/T0)**EXP, theta = (T0 - LAPSE*h_p + dt_isa)/T0,
    sigma = delta/theta. At 600 m with +12 K the warm-day sigma is
    0.905430 (sqrt 0.951541), the family anchor of the envelope leaves.

    ValueError if h_p outside [0, 11000] m or the actual ambient
    temperature (T0 - LAPSE*h_p + dt_isa) is not positive.
    """
    if h_p < 0.0 or h_p > 11000.0:
        raise ValueError("pressure altitude %r outside [0, 11000] m" % h_p)
    ambient = T0 - LAPSE * h_p + dt_isa
    if ambient <= 0.0:
        raise ValueError("ambient temperature %r K not positive" % ambient)
    delta = (1.0 - LAPSE * h_p / T0) ** EXP
    theta = ambient / T0
    return delta / theta


def tas_to_cas(v_tas, h_p, dt_isa=0.0):
    """Convert true airspeed to calibrated airspeed: v_tas*sqrt(sigma).

    Calibrated airspeed already collapses the density, so CAS inputs
    need no density correction. Degenerates to v_tas at sea level
    standard conditions. ValueError if v_tas <= 0.
    """
    if v_tas <= 0.0:
        raise ValueError("true airspeed %r not positive" % v_tas)
    return v_tas * math.sqrt(isa_sigma(h_p, dt_isa))


def weight_corrected_speed(v_cas, w_test, w_ref):
    """Weight correction at fixed lift coefficient: v_cas*sqrt(w_ref/w_test).

    The reference weight is the most favorable (minimum) approach weight
    for the (f) leg and the most unfavorable (maximum) approach weight
    for the (g) leg. Returns v_cas unchanged when w_test == w_ref.
    ValueError if v_cas <= 0 or either weight <= 0.
    """
    if v_cas <= 0.0:
        raise ValueError("calibrated airspeed %r not positive" % v_cas)
    if w_test <= 0.0 or w_ref <= 0.0:
        raise ValueError("test weight %r and reference weight %r must be positive"
                         % (w_test, w_ref))
    return v_cas * math.sqrt(w_ref / w_test)


def flap_normalized_speed(v_cas, flap_test, flap_ref, cl_0, cl_per_deg):
    """Configuration normalization through the landing-configuration lift
    coefficient CL(f) = cl_0 + cl_per_deg*f: v_cas*sqrt(CL(flap_test)/
    CL(flap_ref)).

    More flap, more lift, lower control speed, so a control speed
    measured at a lower flap setting normalizes down to the reference
    landing flap. Returns v_cas unchanged when flap_test == flap_ref.
    ValueError if v_cas <= 0, either flap negative, cl_0 <= 0,
    cl_per_deg < 0, or the lift coefficient at either flap setting is
    not positive.
    """
    if v_cas <= 0.0:
        raise ValueError("calibrated airspeed %r not positive" % v_cas)
    if flap_test < 0.0 or flap_ref < 0.0:
        raise ValueError("flap settings %r and %r must be non-negative"
                         % (flap_test, flap_ref))
    if cl_0 <= 0.0:
        raise ValueError("zero-lift intercept cl_0 %r not positive" % cl_0)
    if cl_per_deg < 0.0:
        raise ValueError("flap lift slope cl_per_deg %r negative" % cl_per_deg)
    cl_test = cl_0 + cl_per_deg * flap_test
    cl_ref = cl_0 + cl_per_deg * flap_ref
    if cl_test <= 0.0 or cl_ref <= 0.0:
        raise ValueError("landing-configuration lift coefficients %r, %r "
                         "not positive" % (cl_test, cl_ref))
    return v_cas * math.sqrt(cl_test / cl_ref)


def corrected_run_speed(v_meas, w_test, w_ref, flap_test, flap_ref,
                        cl_0, cl_per_deg, h_p=0.0, dt_isa=0.0,
                        tas_input=False):
    """Full standard-condition reduction of one measured cut speed:
    tas_to_cas first when tas_input (CAS input is used directly), then
    weight_corrected_speed, then flap_normalized_speed.

    ValueError if v_meas <= 0 or any argument fails its sub-check.
    """
    if v_meas <= 0.0:
        raise ValueError("measured speed %r not positive" % v_meas)
    v = tas_to_cas(v_meas, h_p, dt_isa) if tas_input else v_meas
    v = weight_corrected_speed(v, w_test, w_ref)
    v = flap_normalized_speed(v, flap_test, flap_ref, cl_0, cl_per_deg)
    return v


def _validate_engines(engines):
    """Structural validation of the engine set: a non-empty list of dicts
    each carrying a positive thrust_N and a numeric y_m (signed positive
    right). ValueError otherwise.
    """
    if not engines:
        raise ValueError("engine list empty")
    for idx, eng in enumerate(engines):
        if not isinstance(eng, dict):
            raise ValueError("engine %d not a dict" % idx)
        try:
            thrust = eng["thrust_N"]
            y_m = eng["y_m"]
        except KeyError:
            raise ValueError("engine %d missing thrust_N or y_m" % idx)
        if thrust is None or y_m is None:
            raise ValueError("engine %d thrust or arm is None" % idx)
        if thrust <= 0.0:
            raise ValueError("engine %d go-around thrust %r not positive"
                             % (idx, thrust))


def post_cut_moment(engines, cut_indices):
    """Asymmetric yawing moment of the cut over the operating engine set:
    |sum of T_i*y_i over the engines NOT in cut_indices|, N m. T_i is the
    go-around thrust of engine i and y_i its signed lateral arm; the cut
    engines contribute no thrust. This engine-by-engine sum reduces
    exactly to the family static form T_op*|y_fail| for a twin and is
    the form the VMCL-2 second-cut geometry requires (cutting a
    centerline engine at y = 0 leaves the residual moment of the
    remaining wing engines).

    ValueError for an empty or structurally invalid engine list, any
    thrust_N <= 0, an empty cut_indices, or any cut index out of range.
    """
    _validate_engines(engines)
    if not cut_indices:
        raise ValueError("cut set empty")
    n = len(engines)
    cut = set()
    for idx in cut_indices:
        if not isinstance(idx, int) or isinstance(idx, bool) \
                or idx < 0 or idx >= n:
            raise ValueError("cut index %r out of range for %d engines"
                             % (idx, n))
        cut.add(idx)
    moment = 0.0
    for idx, eng in enumerate(engines):
        if idx in cut:
            continue
        moment += eng["thrust_N"] * eng["y_m"]
    return abs(moment)


def first_cut_index(engines):
    """First critical cut: the engine whose loss leaves the largest
    post_cut_moment; ties resolve to the lower index. For an
    equal-thrust symmetric layout this is the family critical-engine
    geometry ranking |T*y| (largest lateral arm). ValueError as in
    post_cut_moment.
    """
    _validate_engines(engines)
    best_idx = 0
    best_moment = None
    for idx in range(len(engines)):
        moment = post_cut_moment(engines, [idx])
        if best_moment is None or moment > best_moment:
            best_moment = moment
            best_idx = idx
    return best_idx


def second_cut_index(engines, first_idx):
    """Second critical cut (VMCL-2, three-plus-engine airplanes): among
    the engines still operating after first_idx is out, the one whose
    loss leaves the largest asymmetric moment; ties resolve to the lower
    index. For an equal-thrust symmetric four-engine layout with an
    outer first cut this is the same-side inner engine. ValueError if
    first_idx out of range or fewer than three engines (VMCL-2 requires
    three or more).
    """
    _validate_engines(engines)
    if len(engines) < 3:
        raise ValueError("second critical cut requires three or more engines")
    if not isinstance(first_idx, int) or isinstance(first_idx, bool) \
            or first_idx < 0 or first_idx >= len(engines):
        raise ValueError("first cut index %r out of range" % first_idx)
    best_idx = None
    best_moment = None
    for idx in range(len(engines)):
        if idx == first_idx:
            continue
        moment = post_cut_moment(engines, [first_idx, idx])
        if best_moment is None or moment > best_moment:
            best_moment = moment
            best_idx = idx
    return best_idx


def authority_limited_airspeed(n_asym, y_cut, s_v, l_v, c_lv_delta_r,
                               delta_max_rad, s_f_cd=0.0):
    """Rudder-authority limited airspeed: the airspeed where the required
    deflection reaches the rudder limit.

    Closed form q* = n_asym/(s_v*l_v*c_lv_delta_r*delta_max_rad -
    s_f_cd*|y_cut|), V_auth = sqrt(2*q*/RHO_SL). Returns None when the
    denominator is not positive (the configuration is never authority
    limited). s_f_cd is the optional windmilling drag area term acting
    at the cut engine arm |y_cut| (main model 0.0, and only meaningful
    for a single-cut leg).

    ValueError if n_asym <= 0, y_cut == 0, s_v or l_v <= 0,
    c_lv_delta_r <= 0, delta_max outside (0, 60] deg, or s_f_cd < 0.
    """
    if n_asym <= 0.0:
        raise ValueError("asymmetric moment %r not positive" % n_asym)
    if y_cut == 0.0:
        raise ValueError("cut engine lateral arm %r zero" % y_cut)
    if s_v <= 0.0 or l_v <= 0.0:
        raise ValueError("fin area %r and arm %r must be positive" % (s_v, l_v))
    if c_lv_delta_r <= 0.0:
        raise ValueError("fin lift slope per rudder deflection %r not positive"
                         % c_lv_delta_r)
    delta_deg = math.degrees(delta_max_rad)
    if not (0.0 < delta_deg <= 60.0):
        raise ValueError("rudder limit %r deg outside (0, 60]" % delta_deg)
    if s_f_cd < 0.0:
        raise ValueError("windmilling drag area %r negative" % s_f_cd)
    denom = (s_v * l_v * c_lv_delta_r * delta_max_rad
             - s_f_cd * abs(y_cut))
    if denom <= 0.0:
        return None
    q_star = n_asym / denom
    return math.sqrt(2.0 * q_star / RHO_SL)


def required_deflection(n_asym, q, s_v, l_v, c_lv_delta_r):
    """Required rudder deflection to balance the asymmetric moment at
    dynamic pressure q: n_asym/(q*s_v*l_v*c_lv_delta_r), capped at
    delta_r_max by the caller. ValueError if n_asym <= 0 or q <= 0.
    """
    if n_asym <= 0.0:
        raise ValueError("asymmetric moment %r not positive" % n_asym)
    if q <= 0.0:
        raise ValueError("dynamic pressure %r not positive" % q)
    return n_asym / (q * s_v * l_v * c_lv_delta_r)


def pedal_force(q, s_r, c_r, c_h_delta_r, delta_used, boost, pedal_arm):
    """Rudder pedal force with the boost factor:
    q*s_r*c_r*|c_h_delta_r|*delta_used*boost/pedal_arm, with
    c_h_delta_r the hinge moment coefficient per radian (magnitude used)
    and boost scaling felt force (1.0 manual, smaller for power-boosted
    systems).

    ValueError if q <= 0, delta_used <= 0, boost outside (0, 1],
    pedal_arm <= 0, c_h_delta_r == 0, or s_r/c_r <= 0.
    """
    if q <= 0.0:
        raise ValueError("dynamic pressure %r not positive" % q)
    if delta_used <= 0.0:
        raise ValueError("deflection %r not positive" % delta_used)
    if not (0.0 < boost <= 1.0):
        raise ValueError("boost factor %r outside (0, 1]" % boost)
    if pedal_arm <= 0.0:
        raise ValueError("pedal arm %r not positive" % pedal_arm)
    if c_h_delta_r == 0.0:
        raise ValueError("hinge moment coefficient zero")
    if s_r <= 0.0 or c_r <= 0.0:
        raise ValueError("rudder area %r and chord %r must be positive"
                         % (s_r, c_r))
    return q * s_r * c_r * abs(c_h_delta_r) * delta_used * boost / pedal_arm


def force_limited_airspeed(f_lim, pedal_arm, s_r, c_r, c_h_delta_r,
                           delta_max_rad, boost):
    """Pedal-force-limited airspeed: the speed where a full-deflection
    rudder input demands the pedal force limit, from
    q_F = f_lim*pedal_arm/(s_r*c_r*|c_h_delta_r|*delta_max_rad*boost),
    V_force = sqrt(2*q_F/RHO_SL). It is leg-independent (depends only on
    the rudder geometry and the boost factor).

    ValueErrors as in pedal_force, plus f_lim <= 0 and delta_max_rad
    <= 0.
    """
    if f_lim <= 0.0:
        raise ValueError("pedal force limit %r not positive" % f_lim)
    if delta_max_rad <= 0.0:
        raise ValueError("full deflection %r not positive" % delta_max_rad)
    if not (0.0 < boost <= 1.0):
        raise ValueError("boost factor %r outside (0, 1]" % boost)
    if pedal_arm <= 0.0:
        raise ValueError("pedal arm %r not positive" % pedal_arm)
    if c_h_delta_r == 0.0:
        raise ValueError("hinge moment coefficient zero")
    if s_r <= 0.0 or c_r <= 0.0:
        raise ValueError("rudder area %r and chord %r must be positive"
                         % (s_r, c_r))
    q_f = f_lim * pedal_arm / (s_r * c_r * abs(c_h_delta_r)
                               * delta_max_rad * boost)
    return math.sqrt(2.0 * q_f / RHO_SL)


def approach_run_class(v_cut_cas, v_auth, v_force, bank_max_deg=None,
                       heading_change_deg=None):
    """Classify one approach-cut run from the measured CAS and the
    observed recovery outcome. Exactly one of the three spec strings:
    - "control-lost" when the observed bank exceeded BANK_LIM_DEG or the
      observed recovery heading change exceeded HEADING_LIM_DEG, or
      otherwise when V < V_auth (VMCL lies above this run),
    - "at-limit" when held within the criteria and V_auth <= V < V_force
      (the VMCL-qualifying class),
    - "with-margin" when held within the criteria and V >= V_force (VMCL
      lies at or below this run).
    Observed criteria violations override the speed class; observed
    compliance never overrides a speed-based loss.

    ValueError if v_cut_cas <= 0 or v_auth or v_force is None/<= 0.
    """
    if v_cut_cas <= 0.0:
        raise ValueError("run speed %r not positive" % v_cut_cas)
    if v_auth is None or v_force is None or v_auth <= 0.0 or v_force <= 0.0:
        raise ValueError("authority and force limits must be positive "
                         "airspeeds")
    lost = False
    if bank_max_deg is not None and bank_max_deg > BANK_LIM_DEG:
        lost = True
    if heading_change_deg is not None and heading_change_deg > HEADING_LIM_DEG:
        lost = True
    if lost or v_cut_cas < v_auth:
        return "control-lost"
    if v_cut_cas < v_force:
        return "at-limit"
    return "with-margin"


def leg_verdict(runs, leg, v_auth, v_force, w_ref, flap_ref, cl_0,
                cl_per_deg):
    """Reduce the approach-cut run list of one leg to the demonstrated
    verdict.

    Each run dict: id, speed (m/s, CAS or TAS by tas_input), weight (kg),
    flap (deg), bank_max_deg, heading_change_deg, h_p (m, default 0),
    dt_isa (K, default 0), tas_input (bool, default False). Per run the
    class comes from the measured CAS (TAS converted first, before
    corrections) and the corrected speed uses the full standard-
    condition chain (weight correction to the leg reference weight and
    flap normalization to the reference landing flap); vmcl_cas = min of
    the corrected at-limit speeds; vmcl_knots = vmcl_cas/KT2MS. Reports
    v_lost_max and v_margin_min (None when a bracket is empty),
    bracket_ok (True only when the verdict strictly exceeds the lost max
    when present and does not exceed the margin min when present),
    n_qualifying, n_lost, n_margin and the per-run corrected table.

    ValueError if runs is empty or no run classifies as at-limit (VMCL
    not defined by the data).
    """
    if not runs:
        raise ValueError("run list empty, no VMCL data")
    per_run = []
    at_limit = []
    lost_max = None
    margin_min = None
    n_lost = 0
    n_margin = 0
    for r in runs:
        speed = r["speed"]
        h_p = r.get("h_p", 0.0)
        dt_isa = r.get("dt_isa", 0.0)
        tas_input = r.get("tas_input", False)
        v_class = tas_to_cas(speed, h_p, dt_isa) if tas_input else speed
        cls = approach_run_class(v_class, v_auth, v_force,
                                 r.get("bank_max_deg"),
                                 r.get("heading_change_deg"))
        corr = corrected_run_speed(speed, r["weight"], w_ref, r["flap"],
                                   flap_ref, cl_0, cl_per_deg, h_p,
                                   dt_isa, tas_input)
        per_run.append({"id": r.get("id"), "class": cls, "corrected": corr})
        if cls == "at-limit":
            at_limit.append(corr)
        elif cls == "control-lost":
            n_lost += 1
            if lost_max is None or corr > lost_max:
                lost_max = corr
        elif cls == "with-margin":
            n_margin += 1
            if margin_min is None or corr < margin_min:
                margin_min = corr
    if not at_limit:
        raise ValueError("no run classifies as at-limit, VMCL undefined")
    vmcl = min(at_limit)
    bracket_ok = True
    if lost_max is not None and vmcl <= lost_max:
        bracket_ok = False
    if margin_min is not None and vmcl > margin_min:
        bracket_ok = False
    return {
        "leg": leg,
        "vmcl_cas": vmcl,
        "vmcl_knots": vmcl / KT2MS,
        "runs": per_run,
        "v_lost_max": lost_max,
        "v_margin_min": margin_min,
        "bracket_ok": bracket_ok,
        "n_qualifying": len(at_limit),
        "n_lost": n_lost,
        "n_margin": n_margin,
    }


def stall_guard_check(vmcl_cas, vs0, guard_factor=STALL_GUARD):
    """Stall protection guard on the landing-configuration reference
    stall speed: guard_speed = guard_factor*vs0 (1.05 default, vs0 the
    reference stall speed supplied by the sibling stall-speed-
    determination leaf). Verdict "stall-guard-ok" when VMCL clears the
    guard, else "stall-guard-governs"; reports the proximity ratio
    vmcl/vs0 (below 1.10 keeps the guard relevant).

    ValueError if either speed <= 0.
    """
    if vmcl_cas <= 0.0:
        raise ValueError("vmcl %r not positive" % vmcl_cas)
    if vs0 <= 0.0:
        raise ValueError("reference stall speed %r not positive" % vs0)
    guard_speed = guard_factor * vs0
    verdict = "stall-guard-ok" if vmcl_cas >= guard_speed \
        else "stall-guard-governs"
    return {"guard_speed": guard_speed, "guard_verdict": verdict,
            "proximity": vmcl_cas / vs0}


def lateral_control_check(phi_dot_avail_deg_s, phi_req_deg=ROLL_DEG,
                          t_req_s=ROLL_TIME_S):
    """Lateral control check of the demonstration (25.149(h)(3),
    paraphrased): roll capability at the verdict must move the airplane
    through phi_req_deg in not more than t_req_s. The required average
    rate is phi_req_deg/t_req_s (4.0 deg/s at the defaults); verdict
    "lateral-control-ok" when the consumed available roll rate meets it,
    else "lateral-control-insufficient".

    ValueError if the available rate <= 0 or the demand/time <= 0.
    """
    if phi_dot_avail_deg_s <= 0.0:
        raise ValueError("available roll rate %r not positive"
                         % phi_dot_avail_deg_s)
    if phi_req_deg <= 0.0 or t_req_s <= 0.0:
        raise ValueError("roll demand %r and time %r must be positive"
                         % (phi_req_deg, t_req_s))
    required = phi_req_deg / t_req_s
    verdict = "lateral-control-ok" if phi_dot_avail_deg_s >= required \
        else "lateral-control-insufficient"
    return {"required_rate_deg_s": required,
            "available_rate_deg_s": phi_dot_avail_deg_s,
            "verdict": verdict}


def approach_margin_check(vmcl_cas, v_app_ref):
    """Approach margin check against the operating approach speed set:
    margin_ok = v_app_ref >= vmcl, with the ratio v_app_ref/vmcl and the
    clearance v_app_ref - vmcl; verdict "margin-ok" when the reference
    approach speed clears the demonstrated VMCL, else "vmcl-governs"
    with v_app_required = vmcl (the control limit forces the approach
    schedule up).

    ValueError if either speed <= 0.
    """
    if vmcl_cas <= 0.0:
        raise ValueError("vmcl %r not positive" % vmcl_cas)
    if v_app_ref <= 0.0:
        raise ValueError("reference approach speed %r not positive"
                         % v_app_ref)
    margin_ok = v_app_ref >= vmcl_cas
    result = {"margin_ok": margin_ok,
              "ratio": v_app_ref / vmcl_cas,
              "clearance": v_app_ref - vmcl_cas}
    if margin_ok:
        result["verdict"] = "margin-ok"
    else:
        result["verdict"] = "vmcl-governs"
        result["v_app_required"] = vmcl_cas
    return result


def demonstration_summary(verdict_1, verdict_2=None):
    """Combined demonstrated VMCL: the governing leg carries the higher
    demonstrated value (the approach speed set must clear BOTH legs for
    a three-plus-engine airplane; a twin has only the (f) leg).
    Returns vmcl_cas and vmcl_knots of the governing leg and the
    governing_leg label "vmcl-1" or "vmcl-2". verdict_1 and verdict_2
    are leg_verdict dicts.
    """
    if verdict_2 is None or verdict_1["vmcl_cas"] >= verdict_2["vmcl_cas"]:
        gov = verdict_1
        label = "vmcl-1"
    else:
        gov = verdict_2
        label = "vmcl-2"
    return {"vmcl_cas": gov["vmcl_cas"], "vmcl_knots": gov["vmcl_knots"],
            "governing_leg": label}
