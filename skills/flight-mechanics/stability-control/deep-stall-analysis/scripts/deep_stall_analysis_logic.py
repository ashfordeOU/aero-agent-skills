"""Deep stall analysis logic: wake-blanked tail pitch trim model.

Pure stdlib, offline deterministic. Assesses whether a T-tail or
aft-fuselage-mounted-tail airplane can enter a deep stall (a
self-sustaining high-angle-of-attack trim beyond the stall, sometimes
called alpha lock) and whether the elevator retains enough pitch-down
authority to recover.

All wake and separation coefficients below are documented typical
engineering-model constants, not standard values (FAR/CS 25 referenced
for stall and controllability context only, never reproduced).
"""

import math

# Module constants (documented typicals)
VISC_STALL_SHIFT_DEG = 2.0   # viscous stall-angle shift above the linear clmax/a slope
BLANK_DELTA_DEG = 10.0       # deg over which tail blanking ramps to the blanked efficiency
SEP_RISE_RAD = 0.6           # rad beyond stall over which separated-flow pitch-up rises linearly
SEP_FADE_RAD = 0.4           # rad over which separated-flow pitch-up fades back to zero
R2D = 57.29578               # radians to degrees
D2R = 0.0174533              # degrees to radians
BISECT_TOL_RAD = 1e-9        # bisection angle tolerance in radians
SCAN_STEP_DEG = 0.5          # sign-change scan step over the search interval
HUMP_SAMPLES = 200           # samples for the pitch-up hump maximum

# Documented typical tail-aft T-tail transport (worked example)
TYPICAL_TTAIL_TRANSPORT = {
    "clmax": 1.5,
    "a_w": 5.7,
    "cm0_wb": 0.02,
    "cm_alpha_wb": -0.6,
    "v_h": 0.9,
    "a_t": 4.2,
    "eta_t0": 0.9,
    "eta_blank": 0.25,
    "alpha_wake_deg": 20.0,
    "d_eps_dalpha": 0.35,
    "sep_contrib": 3.0,
    "cm_delta": -1.1,
    "delta_e_max_deg": -25.0,
}

_REQUIRED_KEYS = (
    "clmax", "a_w", "cm0_wb", "cm_alpha_wb", "v_h", "a_t", "eta_t0",
    "eta_blank", "alpha_wake_deg", "d_eps_dalpha", "sep_contrib",
    "cm_delta", "delta_e_max_deg",
)


def _check_inputs(inputs):
    """Validate the input dict, raising ValueError on non-physical values."""
    for key in _REQUIRED_KEYS:
        if key not in inputs:
            raise ValueError("missing input: %s" % key)
    if inputs["clmax"] <= 0:
        raise ValueError("clmax must be positive")
    if inputs["a_w"] <= 0:
        raise ValueError("a_w must be positive")
    if inputs["v_h"] <= 0:
        raise ValueError("v_h must be positive")
    if inputs["eta_t0"] <= 0 or inputs["eta_t0"] > 1.0:
        raise ValueError("eta_t0 must be in (0, 1]")
    if inputs["eta_blank"] < 0 or inputs["eta_blank"] > inputs["eta_t0"]:
        raise ValueError("eta_blank must satisfy 0 <= eta_blank <= eta_t0")
    if inputs["alpha_wake_deg"] <= 0:
        raise ValueError("alpha_wake_deg must be positive")
    if not 0.0 <= inputs["d_eps_dalpha"] <= 1.0:
        raise ValueError("d_eps_dalpha must be within [0, 1]")
    if inputs["sep_contrib"] <= 0:
        raise ValueError("sep_contrib must be positive")
    if inputs["cm_delta"] >= 0:
        raise ValueError("cm_delta must be negative (down elevator nose-down)")
    if inputs["delta_e_max_deg"] >= 0:
        raise ValueError("delta_e_max_deg must be negative (down travel)")
    if inputs["cm_alpha_wb"] >= 0:
        raise ValueError("cm_alpha_wb must be negative (statically stable wing-body)")


def _blank_ratio(inputs):
    """Blanking ratio eta_blank / eta_t0 from an input dict."""
    return inputs["eta_blank"] / inputs["eta_t0"]


def stall_angle_deg(clmax, a_w):
    """Viscous stall angle in degrees from the linear clmax/a slope."""
    if clmax <= 0:
        raise ValueError("clmax must be positive")
    if a_w <= 0:
        raise ValueError("a_w must be positive")
    return (clmax / a_w) * R2D + VISC_STALL_SHIFT_DEG


def blanking_factor(alpha_deg, alpha_wake_deg, blank_ratio):
    """Tail blanking factor that multiplies eta_t0.

    1.0 below the wake angle, linear ramp to blank_ratio across
    [wake, wake + BLANK_DELTA_DEG], constant blank_ratio above.
    """
    if alpha_wake_deg <= 0:
        raise ValueError("alpha_wake_deg must be positive")
    if not 0.0 <= blank_ratio <= 1.0:
        raise ValueError("blank_ratio must be within [0, 1]")
    if alpha_deg <= alpha_wake_deg:
        return 1.0
    end = alpha_wake_deg + BLANK_DELTA_DEG
    if alpha_deg >= end:
        return blank_ratio
    fraction = (alpha_deg - alpha_wake_deg) / BLANK_DELTA_DEG
    return 1.0 - fraction * (1.0 - blank_ratio)


def separation_pitch_up(alpha_r, alpha_stall_r, sep_contrib):
    """Separated-flow wing-body pitch-up increment vs angle (radians)."""
    if sep_contrib <= 0:
        raise ValueError("sep_contrib must be positive")
    x = alpha_r - alpha_stall_r
    if x <= 0.0:
        return 0.0
    if x <= SEP_RISE_RAD:
        return sep_contrib * x
    if x <= SEP_RISE_RAD + SEP_FADE_RAD:
        return sep_contrib * SEP_RISE_RAD * (
            1.0 - (x - SEP_RISE_RAD) / SEP_FADE_RAD
        )
    return 0.0


def cm_total(alpha_deg, inputs):
    """Total pitching moment coefficient at alpha_deg for the input set."""
    _check_inputs(inputs)
    alpha_r = alpha_deg * D2R
    alpha_stall_r = stall_angle_deg(inputs["clmax"], inputs["a_w"]) * D2R
    eta = inputs["eta_t0"] * blanking_factor(
        alpha_deg, inputs["alpha_wake_deg"], _blank_ratio(inputs)
    )
    tail = -inputs["v_h"] * eta * inputs["a_t"] * (
        1.0 - inputs["d_eps_dalpha"]
    ) * alpha_r
    sep = separation_pitch_up(alpha_r, alpha_stall_r, inputs["sep_contrib"])
    return inputs["cm0_wb"] + inputs["cm_alpha_wb"] * alpha_r + sep + tail


def _bisect_root(lo_deg, hi_deg, inputs, tol_deg):
    """Bisection root of cm_total on a sign-changing bracket [lo, hi]."""
    f_lo = cm_total(lo_deg, inputs)
    while (hi_deg - lo_deg) * D2R > BISECT_TOL_RAD:
        mid = 0.5 * (lo_deg + hi_deg)
        f_mid = cm_total(mid, inputs)
        if f_mid == 0.0:
            return mid
        if (f_lo > 0.0) != (f_mid > 0.0):
            hi_deg = mid
        else:
            lo_deg = mid
            f_lo = f_mid
    return 0.5 * (lo_deg + hi_deg)


def find_deep_stall_trim(inputs, lo_deg=None, hi_deg=60.0):
    """Post-stall trim angle in degrees, or None when Cm never crosses.

    Scans [lo_deg, hi_deg] for sign changes of cm_total and returns the
    highest-angle crossing, the stable high-alpha trim where the fading
    separated-flow pitch-up lets Cm fall back below zero. None when
    cm_total keeps one sign across the whole interval (no crossing).
    """
    _check_inputs(inputs)
    if lo_deg is None:
        lo_deg = stall_angle_deg(inputs["clmax"], inputs["a_w"]) + 5.0
    if hi_deg <= lo_deg:
        raise ValueError("hi_deg must exceed lo_deg")
    tol_deg = BISECT_TOL_RAD / D2R
    points = []
    deg = lo_deg
    while deg < hi_deg - 1e-12:
        points.append(deg)
        deg += SCAN_STEP_DEG
    points.append(hi_deg)
    roots = []
    prev_sign = None
    prev_deg = lo_deg
    for deg in points:
        cm = cm_total(deg, inputs)
        if cm == 0.0:
            roots.append(deg)
            prev_sign = None
        else:
            sign = 1.0 if cm > 0.0 else -1.0
            if prev_sign is not None and prev_sign != sign:
                roots.append(_bisect_root(prev_deg, deg, inputs, tol_deg))
            prev_sign = sign
        prev_deg = deg
    return max(roots) if roots else None


def lock_depth_deg(alpha_lock_deg, alpha_stall_deg):
    """Lock depth: how far the post-stall trim sits above the stall angle."""
    return max(0.0, alpha_lock_deg - alpha_stall_deg)


def cm_at_stall(inputs):
    """Total pitching moment coefficient at the viscous stall angle."""
    _check_inputs(inputs)
    return cm_total(stall_angle_deg(inputs["clmax"], inputs["a_w"]), inputs)


def recovery_margin(inputs, alpha_lock_deg):
    """Elevator pitch-down authority margin over the pitch-up hump.

    Positive when full down elevator can push the nose back below the
    stall from the post-stall trim; infinite when no post-stall trim
    exists.
    """
    _check_inputs(inputs)
    max_down_moment = abs(inputs["cm_delta"]) * abs(inputs["delta_e_max_deg"] * D2R)
    if alpha_lock_deg is None:
        return float("inf")
    stall = stall_angle_deg(inputs["clmax"], inputs["a_w"])
    hump = max(
        cm_total(
            stall + (alpha_lock_deg - stall) * i / (HUMP_SAMPLES - 1), inputs
        )
        for i in range(HUMP_SAMPLES)
    )
    required = max(0.0, hump)
    return max_down_moment - required


def analyze(inputs):
    """Full deep-stall assessment dict for the input set."""
    _check_inputs(inputs)
    stall = stall_angle_deg(inputs["clmax"], inputs["a_w"])
    lock = find_deep_stall_trim(inputs)
    depth = lock_depth_deg(lock, stall) if lock is not None else 0.0
    blanking = (
        None
        if lock is None
        else blanking_factor(lock, inputs["alpha_wake_deg"], _blank_ratio(inputs))
    )
    cm_stall = cm_at_stall(inputs)
    margin = recovery_margin(inputs, lock)
    deep_stall = lock is not None and depth >= 3.0
    alpha_lock = deep_stall and margin < 0.0
    if not deep_stall:
        verdict = "no deep-stall trim"
    elif margin < 0.0:
        verdict = "deep-stall alpha lock, elevator insufficient"
    else:
        verdict = "deep-stall trim, elevator recovers"
    return {
        "alpha_stall_deg": stall,
        "alpha_lock_deg": lock,
        "lock_depth_deg": depth,
        "blanking_at_lock": blanking,
        "cm_at_stall": cm_stall,
        "recovery_margin": margin,
        "deep_stall": deep_stall,
        "alpha_lock": alpha_lock,
        "verdict": verdict,
    }


if __name__ == "__main__":
    # Lightweight smoke output when run as a file (python3 -c is blocked).
    res = analyze(TYPICAL_TTAIL_TRANSPORT)
    print("stall_angle_deg =", res["alpha_stall_deg"])
    print("alpha_lock_deg  =", res["alpha_lock_deg"])
    print("verdict         =", res["verdict"])
