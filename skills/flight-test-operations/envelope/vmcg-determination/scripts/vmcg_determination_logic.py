"""vmcg_determination_logic.py

Ground minimum control speed Vmcg reduction for the engine-failure ground
roll demonstration runs of a transport airplane flight test, in the spirit
of the FAR/CS 25.149 ground leg method, summary-only.

This module implements the standard-engineering closed-form model of the
spec (ops/automation/state/wave44-specs/vmcg-determination.md): the
asymmetric yawing moment of the operating-engine thrust at the failed
engine lateral arm, the nosewheel steering authority below the steering
cutout speed, the steering-free rudder authority-limited and
pedal-force-limited ground speeds with the boost factor, the per-run
standard-condition corrections and steering-held/departed/at-limit/
with-margin classification, the Vmcg verdict with the bracket
consistency check, the stall protection guard on the reference stall
speed and the balanced-field V1 gate.

Every speed verdict is a CAS m/s value at reference conditions; knots
appear only to quote the verdict. Windmilling drag of the failed engine
is neglected in the main model and enters only through the optional
s_f_cd term of the authority closed form. Pure Python stdlib (math
only), deterministic, no network.
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


def isa_sigma(h_p, dt_isa=0.0):
    """ISA density ratio delta/theta at pressure altitude h_p (m) with
    temperature deviation dt_isa (K), single-layer closed form.

    delta = (1 - LAPSE*h_p/T0)**EXP, theta = (T0 - LAPSE*h_p + dt_isa)/T0,
    sigma = delta/theta.

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

    Returns v_cas unchanged when w_test == w_ref. ValueError if v_cas <= 0
    or either weight <= 0.
    """
    if v_cas <= 0.0:
        raise ValueError("calibrated airspeed %r not positive" % v_cas)
    if w_test <= 0.0 or w_ref <= 0.0:
        raise ValueError("test weight %r and reference weight %r must be positive"
                         % (w_test, w_ref))
    return v_cas * math.sqrt(w_ref / w_test)


def flap_normalized_speed(v_cas, flap_test, flap_ref, cl_0, cl_per_deg):
    """Configuration normalization through the rotation-limit lift
    coefficient CL(f) = cl_0 + cl_per_deg*f:
    v_cas*sqrt(CL(flap_test)/CL(flap_ref)).

    More flap, more lift, lower control speed, so a speed measured at a
    lower flap setting rises when normalized up to the reference flap.
    Returns v_cas unchanged when flap_test == flap_ref. ValueError if
    v_cas <= 0, either flap negative, cl_0 <= 0, cl_per_deg < 0, or the
    lift coefficient at either flap setting is not positive.
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
        raise ValueError("rotation-limit lift coefficients %r, %r not positive"
                         % (cl_test, cl_ref))
    return v_cas * math.sqrt(cl_test / cl_ref)


def corrected_run_speed(v_meas, w_test, w_ref, flap_test, flap_ref,
                        cl_0, cl_per_deg, h_p=0.0, dt_isa=0.0,
                        tas_input=False):
    """Full standard-condition reduction of one measured failure speed:
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


def asym_yaw_moment_static(t_op, y_fail):
    """Engine-out yawing moment on the ground roll: t_op*|y_fail|, the
    operating (non-failed) engine thrust at the signed lateral arm of the
    failed engine. Windmilling drag of the failed engine is neglected in
    the main model (small at ground roll speeds).

    ValueError if t_op <= 0 or y_fail <= 0.
    """
    if t_op <= 0.0:
        raise ValueError("operating thrust %r not positive" % t_op)
    if y_fail <= 0.0:
        raise ValueError("failed engine lateral arm %r not positive" % y_fail)
    return t_op * abs(y_fail)


def authority_limited_ground_speed(t_op, y_fail, s_v, l_v, c_lv_delta_r,
                                   delta_max_rad, s_f_cd=0.0):
    """Steering-free rudder authority-limited ground speed: the speed
    where the required rudder deflection reaches delta_r_max.

    Closed form q* = t_op*|y_fail| / (s_v*l_v*c_lv_delta_r*delta_max_rad
    - s_f_cd*|y_fail|), V_auth = sqrt(2*q*/RHO_SL). Returns None when the
    denominator is not positive (the configuration is never authority
    limited). s_f_cd is the optional windmilling drag area term of the
    failed engine.

    ValueError if t_op, y_fail, s_v or l_v <= 0, c_lv_delta_r <= 0,
    delta_r_max outside (0, 60] deg, or s_f_cd < 0.
    """
    if t_op <= 0.0 or y_fail <= 0.0:
        raise ValueError("thrust %r and lateral arm %r must be positive"
                         % (t_op, y_fail))
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
             - s_f_cd * abs(y_fail))
    if denom <= 0.0:
        return None
    q_star = t_op * abs(y_fail) / denom
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
    pedal_arm <= 0, or c_h_delta_r == 0.
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
        raise ValueError("rudder area %r and chord %r must be positive" % (s_r, c_r))
    return q * s_r * c_r * abs(c_h_delta_r) * delta_used * boost / pedal_arm


def force_limited_ground_speed(f_lim, pedal_arm, s_r, c_r, c_h_delta_r,
                               delta_max_rad, boost):
    """Pedal-force-limited ground speed: the speed where a full-deflection
    rudder input demands the pedal force limit, from
    q_F = f_lim*pedal_arm/(s_r*c_r*|c_h_delta_r|*delta_max_rad*boost),
    V_force = sqrt(2*q_F/RHO_SL).

    ValueErrors as in pedal_force.
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
        raise ValueError("rudder area %r and chord %r must be positive" % (s_r, c_r))
    q_f = f_lim * pedal_arm / (s_r * c_r * abs(c_h_delta_r)
                               * delta_max_rad * boost)
    return math.sqrt(2.0 * q_f / RHO_SL)


def steering_moment(w_kg, f_nw, mu_steer, l_nw):
    """Nosewheel steering authority below the cutout: the friction-limited
    lateral force at the nose gear, mu_steer*f_nw*w_kg*g0*l_nw, with f_nw
    the nose gear static load fraction (consumed as an input, derived by
    the vehicle-design landing-gear-layout sibling) and l_nw the
    CG-to-nose-gear arm.

    ValueError if any input <= 0.
    """
    if w_kg <= 0.0 or f_nw <= 0.0 or mu_steer <= 0.0 or l_nw <= 0.0:
        raise ValueError("steering inputs weight %r, load fraction %r, "
                         "friction %r, arm %r must all be positive"
                         % (w_kg, f_nw, mu_steer, l_nw))
    return mu_steer * f_nw * w_kg * G0 * l_nw


def steering_engaged(v_ground, v_cut):
    """Whether the nosewheel steering is engaged at the ground speed:
    v_ground < v_cut (the cutout boundary is excluded).

    ValueError if v_ground < 0 or v_cut <= 0.
    """
    if v_ground < 0.0:
        raise ValueError("ground speed %r negative" % v_ground)
    if v_cut <= 0.0:
        raise ValueError("cutout speed %r not positive" % v_cut)
    return v_ground < v_cut


def ground_run_class(steering_on, v_ef_cas, v_auth, v_force):
    """Classify one ground roll run from the measured CAS and the
    steering state. Exactly one of the four spec strings:
    - "steering-held" when the steering is engaged (only possible below
      the cutout; practice run, not qualifying),
    - "departed" when steering-free and v < v_auth (Vmcg lies above),
    - "at-limit" when steering-free and v_auth <= v < v_force (the
      Vmcg-qualifying class),
    - "with-margin" when steering-free and v >= v_force (Vmcg lies at
      or below this run).

    ValueError if v_ef_cas <= 0 or v_auth or v_force is None/<= 0.
    """
    if v_ef_cas <= 0.0:
        raise ValueError("run speed %r not positive" % v_ef_cas)
    if v_auth is None or v_force is None or v_auth <= 0.0 or v_force <= 0.0:
        raise ValueError("authority and force limits must be positive "
                         "ground speeds")
    if steering_on:
        return "steering-held"
    if v_ef_cas < v_auth:
        return "departed"
    if v_ef_cas < v_force:
        return "at-limit"
    return "with-margin"


def vmcg_verdict(runs, v_auth, v_force, w_ref, flap_ref, cl_0, cl_per_deg):
    """Reduce the ground roll run list to the Vmcg verdict.

    Each run dict: id, speed (m/s, CAS or TAS by tas_input), weight (kg),
    flap (deg), steering_on (bool), h_p (m), dt_isa (K), tas_input (bool,
    default False). Per run the corrected speed is computed and the class
    taken from the measured CAS (TAS converted first, before
    corrections); vmcg_cas = min of the corrected at-limit speeds;
    vmcg_knots = vmcg_cas/KT2MS. Reports v_departed_max and v_margin_min
    (None when a bracket is empty), bracket_ok (True only when the
    verdict strictly exceeds the departed max when present and does not
    exceed the margin min when present), n_qualifying, n_departed,
    n_margin, n_steering_held and the per-run corrected table.

    ValueError if runs is empty or no run classifies as at-limit (Vmcg
    not defined by the data).
    """
    if not runs:
        raise ValueError("run list empty, no Vmcg data")
    per_run = []
    at_limit = []
    departed_max = None
    margin_min = None
    n_departed = 0
    n_margin = 0
    n_steering_held = 0
    for r in runs:
        speed = r["speed"]
        h_p = r.get("h_p", 0.0)
        dt_isa = r.get("dt_isa", 0.0)
        tas_input = r.get("tas_input", False)
        v_class = tas_to_cas(speed, h_p, dt_isa) if tas_input else speed
        cls = ground_run_class(r["steering_on"], v_class, v_auth, v_force)
        corr = corrected_run_speed(speed, r["weight"], w_ref, r["flap"],
                                   flap_ref, cl_0, cl_per_deg, h_p,
                                   dt_isa, tas_input)
        per_run.append({"id": r.get("id"), "class": cls, "corrected": corr})
        if cls == "at-limit":
            at_limit.append(corr)
        elif cls == "departed":
            n_departed += 1
            if departed_max is None or corr > departed_max:
                departed_max = corr
        elif cls == "with-margin":
            n_margin += 1
            if margin_min is None or corr < margin_min:
                margin_min = corr
        elif cls == "steering-held":
            n_steering_held += 1
    if not at_limit:
        raise ValueError("no run classifies as at-limit, Vmcg undefined")
    vmcg = min(at_limit)
    bracket_ok = True
    if departed_max is not None and vmcg <= departed_max:
        bracket_ok = False
    if margin_min is not None and vmcg > margin_min:
        bracket_ok = False
    return {
        "vmcg_cas": vmcg,
        "vmcg_knots": vmcg / KT2MS,
        "runs": per_run,
        "v_departed_max": departed_max,
        "v_margin_min": margin_min,
        "bracket_ok": bracket_ok,
        "n_qualifying": len(at_limit),
        "n_departed": n_departed,
        "n_margin": n_margin,
        "n_steering_held": n_steering_held,
    }


def stall_guard_check(vmcg_cas, vs1, guard_factor=1.05):
    """Stall protection guard on the reference stall speed: guard_speed =
    guard_factor*vs1 (1.05 default, vs1 the takeoff-configuration
    reference stall speed supplied by the sibling stall-speed-
    determination leaf). Verdict "stall-guard-ok" when Vmcg clears the
    guard, else "stall-guard-governs"; reports the proximity ratio
    vmcg/vs1 (below 1.10 keeps the guard relevant).

    ValueError if either speed <= 0.
    """
    if vmcg_cas <= 0.0:
        raise ValueError("vmcg %r not positive" % vmcg_cas)
    if vs1 <= 0.0:
        raise ValueError("reference stall speed %r not positive" % vs1)
    guard_speed = guard_factor * vs1
    verdict = "stall-guard-ok" if vmcg_cas >= guard_speed \
        else "stall-guard-governs"
    return {"guard_speed": guard_speed, "guard_verdict": verdict,
            "proximity": vmcg_cas / vs1}


def v1_gate(vmcg_cas, v1_cas, vr_cas=None):
    """Balanced-field V1 gate against the demonstrated Vmcg.

    v1_gate_met = v1 >= vmcg. When not met the verdict is "vmcg-gated"
    with v1_required = vmcg, or "schedule-infeasible" when a vr is
    supplied and vr < vmcg (no legal V1 below the rotation speed
    exists); when met the verdict is "ok". With vr supplied, reports the
    legal window [vmcg, vr] and its width. This leaf only CHECKS a
    supplied V1; it never derives V1 (that is the
    engine-failure-takeoff-flight-test computation).

    ValueError if vmcg_cas or v1_cas <= 0, or a supplied vr_cas <= 0.
    """
    if vmcg_cas <= 0.0:
        raise ValueError("vmcg %r not positive" % vmcg_cas)
    if v1_cas <= 0.0:
        raise ValueError("scheduled V1 %r not positive" % v1_cas)
    if vr_cas is not None and vr_cas <= 0.0:
        raise ValueError("rotation speed %r not positive" % vr_cas)
    gate_met = v1_cas >= vmcg_cas
    result = {"v1_gate_met": gate_met}
    if vr_cas is not None and vr_cas < vmcg_cas:
        result["verdict"] = "schedule-infeasible"
        result["window"] = None
        result["width"] = None
    elif gate_met:
        result["verdict"] = "ok"
        if vr_cas is not None:
            result["window"] = [vmcg_cas, vr_cas]
            result["width"] = vr_cas - vmcg_cas
    else:
        result["verdict"] = "vmcg-gated"
        result["v1_required"] = vmcg_cas
        if vr_cas is not None:
            result["window"] = [vmcg_cas, vr_cas]
            result["width"] = vr_cas - vmcg_cas
    return result
