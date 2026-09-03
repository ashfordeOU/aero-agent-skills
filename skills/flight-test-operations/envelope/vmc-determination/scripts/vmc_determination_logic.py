"""Vmc (minimum control speed) prediction for multi-engine airplanes.

First-order engine-out yaw balance in the spirit of the FAR/CS 25.149
minimum-control-speed method, summary-only (no regulatory text):
identify the critical engine from the engine-out yawing-moment
geometry, build the asymmetric yawing moment from the operating-engine
thrust at the failed-engine lateral arm plus the failed-engine
windmilling drag contribution, solve the rudder-authority-limited
speed, apply the rudder pedal-force criterion with the boost factor,
and apply the stall-protection guard on the reference stall speed.

Model simplifications (documented in the SKILL body): first-order yaw
balance without sideslip coupling, sea-level density for the dynamic
pressure, operating engines at maximum takeoff thrust.

Pure Python stdlib, deterministic, offline.
"""

import math

RHO_SL = 1.225                 # sea-level air density, kg/m^3
G0 = 9.80665                   # standard gravity, m/s^2
F_LIM_N = 667.0                # 150 lbf pedal-force limit in newtons
STALL_GUARD = 1.05             # default stall-protection guard factor
D2R = 0.017453292519943295     # degrees to radians
KT_PER_MPS = 1.94384           # m/s to knots

_ENGINE_KEYS = ("thrust_N", "y_m")


def _validate_engines(engines):
    """Return the engine list after structural validation.

    Raises ValueError for an empty list, missing keys, or any non-positive
    thrust_N, which are non-physical for the Vmc analysis.
    """
    if not isinstance(engines, list) or len(engines) == 0:
        raise ValueError("engines must be a non-empty list")
    for idx, eng in enumerate(engines):
        for key in _ENGINE_KEYS:
            if key not in eng:
                raise ValueError("engine %d missing key '%s'" % (idx, key))
        if eng["thrust_N"] <= 0:
            raise ValueError("engine %d thrust_N must be > 0" % idx)
    return engines


def _validate(inputs):
    """Validate every input field; raises ValueError on non-physical values."""
    required = (
        "engines", "failed_engine_index", "windmilling_drag_area_m2",
        "vertical_tail_area_m2", "tail_arm_m", "rudder_effectiveness_per_rad",
        "rudder_deflection_max_deg", "rudder_area_m2", "rudder_chord_m",
        "hinge_moment_coefficient_per_rad", "pedal_arm_m", "boost_factor",
        "v_s1g", "pedal_force_limit_N", "stall_guard",
    )
    for key in required:
        if key not in inputs:
            raise ValueError("missing input '%s'" % key)
    _validate_engines(inputs["engines"])
    n_eng = len(inputs["engines"])
    if not (0 <= inputs["failed_engine_index"] < n_eng):
        raise ValueError("failed_engine_index out of range")
    if inputs["windmilling_drag_area_m2"] < 0:
        raise ValueError("windmilling_drag_area_m2 must be >= 0")
    if inputs["vertical_tail_area_m2"] <= 0:
        raise ValueError("vertical_tail_area_m2 must be > 0")
    if inputs["tail_arm_m"] <= 0:
        raise ValueError("tail_arm_m must be > 0")
    if inputs["rudder_effectiveness_per_rad"] <= 0:
        raise ValueError("rudder_effectiveness_per_rad must be > 0")
    d_max = inputs["rudder_deflection_max_deg"]
    if d_max <= 0 or d_max > 60:
        raise ValueError("rudder_deflection_max_deg must be in (0, 60]")
    if inputs["rudder_area_m2"] <= 0:
        raise ValueError("rudder_area_m2 must be > 0")
    if inputs["rudder_chord_m"] <= 0:
        raise ValueError("rudder_chord_m must be > 0")
    if inputs["hinge_moment_coefficient_per_rad"] == 0:
        raise ValueError("hinge_moment_coefficient_per_rad must be non-zero")
    if inputs["pedal_arm_m"] <= 0:
        raise ValueError("pedal_arm_m must be > 0")
    boost = inputs["boost_factor"]
    if boost <= 0 or boost > 1:
        raise ValueError("boost_factor must be in (0, 1]")
    if inputs["v_s1g"] <= 0:
        raise ValueError("v_s1g must be > 0")
    if inputs["pedal_force_limit_N"] <= 0:
        raise ValueError("pedal_force_limit_N must be > 0")
    if inputs["stall_guard"] <= 0:
        raise ValueError("stall_guard must be > 0")


def _t_op(inputs):
    """Sum of the thrust of the engines that are NOT failed (operating set)."""
    engines = inputs["engines"]
    failed = inputs["failed_engine_index"]
    return sum(eng["thrust_N"] for idx, eng in enumerate(engines)
               if idx != failed)


def _y_fail(inputs):
    """Lateral arm of the failed engine, y_m, signed."""
    return inputs["engines"][inputs["failed_engine_index"]]["y_m"]


def critical_engine_index(engines):
    """Index of the engine whose failure creates the largest adverse yaw.

    The candidate is the engine with the largest |thrust*y_m| product,
    the engine-out yawing-moment geometry term; ties resolve to the
    lower index. Raises ValueError on an empty list or non-positive
    thrust.
    """
    _validate_engines(engines)
    best_idx = 0
    best_mag = abs(engines[0]["thrust_N"] * engines[0]["y_m"])
    for idx in range(1, len(engines)):
        mag = abs(engines[idx]["thrust_N"] * engines[idx]["y_m"])
        if mag > best_mag:
            best_mag = mag
            best_idx = idx
    return best_idx


def asymmetric_yaw_moment_Nm(V, engines, failed_index,
                             windmilling_drag_area_m2):
    """Asymmetric yawing moment N_asym about the CG, N m.

    N_asym = T_op*y_fail + 0.5*RHO*V^2*S_f*Cd*y_fail, with T_op the
    operating-engine thrust sum and y_fail the signed lateral arm of the
    failed engine. Sign follows y_fail; downstream balance uses the
    magnitude with an opposing rudder deflection.
    """
    _validate_engines(engines)
    if V < 0:
        raise ValueError("V must be >= 0")
    if windmilling_drag_area_m2 < 0:
        raise ValueError("windmilling_drag_area_m2 must be >= 0")
    if not (0 <= failed_index < len(engines)):
        raise ValueError("failed_engine_index out of range")
    t_op = sum(eng["thrust_N"] for idx, eng in enumerate(engines)
               if idx != failed_index)
    y_fail = engines[failed_index]["y_m"]
    drag = 0.5 * RHO_SL * V * V * windmilling_drag_area_m2
    return t_op * y_fail + drag * y_fail


def rudder_deflection_required_rad(N_asym, V, inputs):
    """Rudder deflection magnitude needed to balance N_asym, radians.

    delta = |N_asym| / (q*S_v*l_v*C_Lv_delta_r). The deflection opposes
    the asymmetric moment, so the magnitude is used.
    """
    _validate(inputs)
    if V <= 0:
        raise ValueError("V must be > 0 for the dynamic pressure")
    q = 0.5 * RHO_SL * V * V
    denom = (q * inputs["vertical_tail_area_m2"] * inputs["tail_arm_m"]
             * inputs["rudder_effectiveness_per_rad"])
    return abs(N_asym) / denom


def authority_limited_speed(inputs):
    """Airspeed where the required deflection reaches the rudder limit.

    Closed form from q* = T_op*|y_fail| / (S_v*l_v*C_Lv_delta_r*
    delta_r_max_rad - S_f*Cd*|y_fail|); returns None when the
    denominator is not positive, i.e. the configuration is never
    authority limited.
    """
    _validate(inputs)
    num = _t_op(inputs) * abs(_y_fail(inputs))
    if num <= 0:
        raise ValueError("T_op*|y_fail| must be > 0 for an authority limit")
    delta_max_rad = inputs["rudder_deflection_max_deg"] * D2R
    denom = (inputs["vertical_tail_area_m2"] * inputs["tail_arm_m"]
             * inputs["rudder_effectiveness_per_rad"] * delta_max_rad
             - inputs["windmilling_drag_area_m2"] * abs(_y_fail(inputs)))
    if denom <= 0:
        return None
    q_star = num / denom
    return math.sqrt(2.0 * q_star / RHO_SL)


def pedal_force_at_speed_N(V, inputs):
    """Felt rudder pedal force at airspeed V, newtons.

    F = q*S_r*c_r*|C_h_delta_r|*min(delta_req, delta_r_max_rad)*
    boost_factor / pedal_arm_m. The deflection is capped at the rudder
    limit for speeds below the authority limit.
    """
    _validate(inputs)
    if V <= 0:
        raise ValueError("V must be > 0 for the dynamic pressure")
    engines = inputs["engines"]
    failed = inputs["failed_engine_index"]
    n_asym = asymmetric_yaw_moment_Nm(V, engines, failed,
                                      inputs["windmilling_drag_area_m2"])
    delta_req = rudder_deflection_required_rad(n_asym, V, inputs)
    delta_max_rad = inputs["rudder_deflection_max_deg"] * D2R
    q = 0.5 * RHO_SL * V * V
    hinge = (q * inputs["rudder_area_m2"] * inputs["rudder_chord_m"]
             * abs(inputs["hinge_moment_coefficient_per_rad"])
             * min(delta_req, delta_max_rad))
    return hinge * inputs["boost_factor"] / inputs["pedal_arm_m"]


def _force_limited_speed(inputs):
    """Airspeed where the pedal force reaches the limit at max deflection."""
    delta_max_rad = inputs["rudder_deflection_max_deg"] * D2R
    q_f = (inputs["pedal_force_limit_N"] * inputs["pedal_arm_m"]
           / (inputs["rudder_area_m2"] * inputs["rudder_chord_m"]
              * abs(inputs["hinge_moment_coefficient_per_rad"])
              * delta_max_rad * inputs["boost_factor"]))
    return math.sqrt(2.0 * q_f / RHO_SL)


def vmc_predict(inputs):
    """Full Vmc prediction; returns the result dictionary.

    Fields: critical_engine, asymmetric_moment_at_vmc, vmc_m_s, vmc_kt,
    v_auth_m_s, v_force_m_s, stall_guard_speed_m_s, governing,
    force_at_vmc_N, force_ok, guard_verdict, flight_test_go.
    """
    _validate(inputs)
    engines = inputs["engines"]
    failed = inputs["failed_engine_index"]
    crit = critical_engine_index(engines)
    v_auth = authority_limited_speed(inputs)
    v_force = _force_limited_speed(inputs)
    v_auth_eff = 0.0 if v_auth is None else v_auth
    vmc = max(v_auth_eff, v_force)
    governing = "rudder-authority" if v_auth_eff >= v_force else "pedal-force"
    stall_guard_speed = inputs["stall_guard"] * inputs["v_s1g"]
    force_at_vmc = pedal_force_at_speed_N(vmc, inputs)
    force_ok = force_at_vmc <= inputs["pedal_force_limit_N"]
    if vmc < stall_guard_speed:
        guard_verdict = "stall-guard-governs"
    else:
        guard_verdict = "stall-guard-ok"
    guard_ok = guard_verdict == "stall-guard-ok"
    moment_at_vmc = asymmetric_yaw_moment_Nm(
        vmc, engines, failed, inputs["windmilling_drag_area_m2"])
    return {
        "critical_engine": crit,
        "asymmetric_moment_at_vmc": moment_at_vmc,
        "vmc_m_s": vmc,
        "vmc_kt": vmc * KT_PER_MPS,
        "v_auth_m_s": v_auth,
        "v_force_m_s": v_force,
        "stall_guard_speed_m_s": stall_guard_speed,
        "governing": governing,
        "force_at_vmc_N": force_at_vmc,
        "force_ok": force_ok,
        "guard_verdict": guard_verdict,
        "flight_test_go": bool(force_ok and guard_ok and vmc > 0),
    }
