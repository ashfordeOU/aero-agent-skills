#!/usr/bin/env python3
"""Wind tunnel test data reduction (stdlib only).

Reference implementation for the Aero Agent Skills leaf
skills/aerodynamics/wind-tunnel/windtunnel-data-reduction.

Reduces raw balance and pressure measurements to standard aerodynamic
coefficients through the classical low-speed wind tunnel correction
chain. All corrections are documented approximations of the standard
textbook treatment (paraphrased; see the leaf SKILL.md for the
literature context). Deterministic, offline, no third-party imports.

Correction chain (each step lands in the correction ledger):
  1. tare and tareshift subtraction from raw balance readings
  2. solid blockage from model volume over test section volume
  3. wake blockage from the uncorrected drag coefficient
  4. wall interference (lift induced angle of attack)
  5. streamline curvature (angle of attack and pitching moment)
  6. Reynolds number scaling and Mach corrections
  7. coefficient reduction (CL, CD, Cm, Cp) on corrected dynamic pressure
  8. repeat-run uncertainty from sample statistics

Every public function validates its inputs and raises ValueError on
non-physical values.
"""

import math

# Blockage factor for a three-dimensional model in a closed rectangular
# test section (solid blockage coefficient K1).
K1_CLOSED_RECTANGULAR = 0.96
# Lift interference factor: closed test section (delta), open section 0.125.
DELTA_CLOSED = 0.82
DELTA_OPEN = 0.125
# Turbulent flat plate skin friction exponent for Reynolds scaling.
N_TURBULENT = 0.2
N_LAMINAR = 0.5
GAMMA_AIR = 1.4


def _require_positive(name, value):
    value = float(value)
    if value <= 0.0:
        raise ValueError("%s must be positive, got %r" % (name, value))
    return value


def _require_non_negative(name, value):
    value = float(value)
    if value < 0.0:
        raise ValueError("%s must be non-negative, got %r" % (name, value))
    return value


def _require_finite(name, value):
    """Cast to float and reject NaN or infinite values (signed OK)."""
    value = float(value)
    if not math.isfinite(value):
        raise ValueError("%s must be finite, got %r" % (name, value))
    return value


def interpolate_tare(tare_low, tare_high, alpha_low, alpha_high, alpha):
    """Linearly interpolate a tare reading between two tare runs.

    Tare runs bracket the polar at a low and a high angle of attack; the
    tare at the measurement angle is the linear interpolation between
    them (tareshift correction).

    Raises ValueError if the bracket is degenerate (alpha_high equals
    alpha_low) or alpha lies outside the bracket.
    """
    a_low = float(alpha_low)
    a_high = float(alpha_high)
    a = float(alpha)
    if a_high <= a_low:
        raise ValueError("alpha_high must exceed alpha_low")
    if a < a_low or a > a_high:
        raise ValueError("alpha outside tare bracket [%g, %g]" % (a_low, a_high))
    f = (a - a_low) / (a_high - a_low)
    return float(tare_low) + f * (float(tare_high) - float(tare_low))


def tare_correct_forces(raw, tare):
    """Subtract tare readings from raw balance forces.

    raw and tare are dicts with keys lift, drag, moment (Newtons for
    forces, Newton metres for the moment). Returns a new dict with the
    tare-corrected readings.
    """
    for key in ("lift", "drag", "moment"):
        if key not in raw or key not in tare:
            raise ValueError("raw and tare must both carry lift/drag/moment")
    return {
        key: float(raw[key]) - float(tare[key])
        for key in ("lift", "drag", "moment")
    }


def tare_corrected_drag_offset(raw_drag, tare_drag, tol=1e-9):
    """Absolute residual drag after tare subtraction.

    Returns abs(raw_drag - tare_drag). A model at zero angle of attack
    with no net drag reads only its support tare, so the corrected drag
    offset must be near zero (within tol).
    """
    _require_non_negative("raw_drag", raw_drag)
    _require_non_negative("tare_drag", tare_drag)
    _require_non_negative("tol", tol)
    return abs(float(raw_drag) - float(tare_drag))


def solid_blockage_eps(model_volume, test_section_volume, k1=K1_CLOSED_RECTANGULAR):
    """Solid blockage correction epsilon_sb = K1 * (Vm / Vt).

    Vm is the model volume, Vt the empty test section volume. K1 is the
    shape factor for a closed rectangular test section (0.96 default;
    open sections use ~0.34).
    """
    vm = _require_non_negative("model_volume", model_volume)
    vt = _require_positive("test_section_volume", test_section_volume)
    _require_positive("k1", k1)
    return k1 * vm / vt


def wake_blockage_eps(s_ref, test_section_area, cd_uncorrected):
    """Wake blockage epsilon_wb = 0.25 * (S / C) * CDu.

    S is the model planform area, C the test section cross-sectional
    area, CDu the uncorrected drag coefficient (computed at the
    uncorrected dynamic pressure).
    """
    s = _require_positive("s_ref", s_ref)
    c = _require_positive("test_section_area", test_section_area)
    _require_non_negative("cd_uncorrected", cd_uncorrected)
    return 0.25 * (s / c) * float(cd_uncorrected)


def total_blockage_eps(model_volume, test_section_volume, s_ref,
                       test_section_area, cd_uncorrected,
                       k1=K1_CLOSED_RECTANGULAR):
    """Combined solid plus wake blockage epsilon = eps_sb + eps_wb."""
    eps_sb = solid_blockage_eps(model_volume, test_section_volume, k1)
    eps_wb = wake_blockage_eps(s_ref, test_section_area, cd_uncorrected)
    return eps_sb + eps_wb


def corrected_dynamic_pressure(q_uncorrected, eps):
    """Blockage corrected dynamic pressure q_corr = q_u * (1 + eps)^2."""
    q = _require_positive("q_uncorrected", q_uncorrected)
    _require_non_negative("eps", eps)
    return q * (1.0 + eps) ** 2


def corrected_velocity(v_uncorrected, eps):
    """Blockage corrected tunnel speed V_corr = V_u * (1 + eps)."""
    v = _require_positive("v_uncorrected", v_uncorrected)
    _require_non_negative("eps", eps)
    return v * (1.0 + eps)


def wall_interference_alpha(alpha_deg, s_ref, test_section_area,
                            cl_uncorrected, delta=DELTA_CLOSED):
    """Lift interference angle of attack correction.

    delta_alpha = delta * (S / C) * CL (radians), converted to degrees
    and added to the geometric angle. delta is 0.82 for a closed test
    section and 0.125 for an open one. Returns (delta_alpha_deg,
    alpha_corrected_deg).
    """
    s = _require_positive("s_ref", s_ref)
    c = _require_positive("test_section_area", test_section_area)
    _require_positive("delta", delta)
    cl = _require_finite("cl_uncorrected", cl_uncorrected)
    delta_alpha = delta * (s / c) * cl
    delta_alpha_deg = math.degrees(delta_alpha)
    return delta_alpha_deg, float(alpha_deg) + delta_alpha_deg


def streamline_curvature_corrections(s_ref, test_section_area, chord,
                                     test_section_height, cl_uncorrected,
                                     cm_uncorrected):
    """Streamline curvature corrections to alpha and Cm.

    The curved streamlines around the lifting model act like an added
    camber. Documented approximations: the angle increment scales with
    (S/C) * CL * (chord / (4 * height)) and the pitching moment shift is
    (S/C) * CL * (chord / (8 * height)) with the sign that reduces Cm
    for a positive CL. Returns (delta_alpha_deg, delta_cm).
    """
    s = _require_positive("s_ref", s_ref)
    c = _require_positive("test_section_area", test_section_area)
    chord = _require_positive("chord", chord)
    h = _require_positive("test_section_height", test_section_height)
    cl = _require_finite("cl_uncorrected", cl_uncorrected)
    base = (s / c) * cl
    delta_alpha = base * (chord / (4.0 * h))
    delta_cm = -base * (chord / (8.0 * h))
    return math.degrees(delta_alpha), delta_cm


def reynolds_scale_cd(cd_at_ref, re_ref, re_test, exponent=N_TURBULENT):
    """Scale a drag coefficient between Reynolds numbers.

    CD(Re_test) = CD_ref * (Re_ref / Re_test)^exponent, with the flat
    plate skin friction exponents: 0.2 turbulent, 0.5 laminar.
    """
    cd = _require_non_negative("cd_at_ref", cd_at_ref)
    re_r = _require_positive("re_ref", re_ref)
    re_t = _require_positive("re_test", re_test)
    _require_positive("exponent", exponent)
    return cd * (re_r / re_t) ** exponent


def mach_dynamic_pressure(p_static, mach, gamma=GAMMA_AIR):
    """Compressible dynamic pressure q = 0.5 * gamma * p * M^2.

    Use at M above about 0.3 where the incompressible form 0.5 rho V^2
    starts to lose accuracy.
    """
    p = _require_positive("p_static", p_static)
    m = _require_non_negative("mach", mach)
    _require_positive("gamma", gamma)
    return 0.5 * gamma * p * m * m


def prandtl_glauert_cp(cp_incompressible, mach):
    """Prandtl Glauert compressibility correction for Cp.

    Cp = Cp_inc / sqrt(1 - M^2), valid below M = 1. Returns the
    corrected pressure coefficient.
    """
    m = _require_non_negative("mach", mach)
    if m >= 1.0:
        raise ValueError("prandtl-glauert correction requires M < 1")
    return float(cp_incompressible) / math.sqrt(1.0 - m * m)


def force_coefficients(lift, drag, moment, q, s_ref, c_ref):
    """Reduce forces to CL, CD, Cm.

    CL = L / (q S), CD = D / (q S), Cm = M / (q S c_ref), referenced to
    the model planform area S and reference length c_ref.
    """
    q = _require_positive("q", q)
    s = _require_positive("s_ref", s_ref)
    c = _require_positive("c_ref", c_ref)
    qs = q * s
    return {
        "cl": float(lift) / qs,
        "cd": float(drag) / qs,
        "cm": float(moment) / (qs * c),
    }


def pressure_coefficient(p_local, p_ref_static, q):
    """Pressure coefficient Cp = (p_local - p_ref) / q."""
    q = _require_positive("q", q)
    return (float(p_local) - float(p_ref_static)) / q


def pressure_coefficients(p_local_list, p_ref_static, q):
    """Cp for a list of local pressures (pressure tap array)."""
    q = _require_positive("q", q)
    if not p_local_list:
        raise ValueError("p_local_list must not be empty")
    return [
        (float(p) - float(p_ref_static)) / q for p in p_local_list
    ]


def repeat_run_uncertainty(values, coverage=2.0):
    """Uncertainty of the reported mean from repeated runs.

    Returns sample statistics of the repeated measurements: mean, sample
    standard deviation (n - 1 denominator), standard error of the mean,
    and the expanded uncertainty U = coverage * standard_error. The
    default coverage factor 2 approximates a 95% interval for a normal
    distribution.
    """
    vals = [float(v) for v in values]
    if len(vals) < 2:
        raise ValueError("at least two repeat runs are required")
    _require_positive("coverage", coverage)
    n = len(vals)
    mean = sum(vals) / n
    var = sum((v - mean) ** 2 for v in vals) / (n - 1)
    std = math.sqrt(var)
    se = std / math.sqrt(n)
    return {
        "n": n,
        "mean": mean,
        "std": std,
        "standard_error": se,
        "expanded": coverage * se,
        "coverage": coverage,
    }


def reduce_wind_tunnel_run(raw_lift, raw_drag, raw_moment, alpha_deg,
                           tare_low, tare_high,
                           tare_alpha_low, tare_alpha_high,
                           q_uncorrected, s_ref, c_ref,
                           model_volume, test_section_volume,
                           test_section_area, test_section_height, chord,
                           mach=None, p_static=None,
                           delta=DELTA_CLOSED,
                           k1=K1_CLOSED_RECTANGULAR):
    """Full low-speed data reduction chain with correction ledger.

    Steps: tare and tareshift subtraction, compressible dynamic pressure
    when M >= 0.3 is supplied, uncorrected coefficients, solid and wake
    blockage, corrected dynamic pressure, wall interference and
    streamline curvature corrections, then final coefficients on the
    corrected dynamic pressure. Returns a dict with the corrected
    coefficients and the ledger of every applied correction.
    """
    # 1. Tare and tareshift.
    tare_lift = interpolate_tare(
        tare_low["lift"], tare_high["lift"], tare_alpha_low, tare_alpha_high,
        alpha_deg)
    tare_drag = interpolate_tare(
        tare_low["drag"], tare_high["drag"], tare_alpha_low, tare_alpha_high,
        alpha_deg)
    tare_moment = interpolate_tare(
        tare_low["moment"], tare_high["moment"], tare_alpha_low, tare_alpha_high,
        alpha_deg)
    tare_at_alpha = {"lift": tare_lift, "drag": tare_drag, "moment": tare_moment}
    forces = tare_correct_forces(
        {"lift": raw_lift, "drag": raw_drag, "moment": raw_moment},
        tare_at_alpha)

    ledger = [
        {"step": "tare", "value": tare_drag,
         "note": "support tare and tareshift subtracted from raw drag"},
    ]

    # 2. Reference dynamic pressure (compressible form at M >= 0.3).
    q_ref = float(q_uncorrected)
    if mach is not None and p_static is not None and mach >= 0.3:
        q_ref = mach_dynamic_pressure(p_static, mach)
        ledger.append({"step": "mach", "value": q_ref,
                       "note": "compressible dynamic pressure at M >= 0.3"})

    # 3. Uncorrected coefficients at the uncorrected dynamic pressure.
    coef_u = force_coefficients(
        forces["lift"], forces["drag"], forces["moment"], q_ref, s_ref, c_ref)
    ledger.append({"step": "coefficients-uncorrected", "value": coef_u["cd"],
                   "note": "CD at uncorrected dynamic pressure"})

    # 4. Blockage.
    eps_sb = solid_blockage_eps(model_volume, test_section_volume, k1)
    eps_wb = wake_blockage_eps(s_ref, test_section_area, coef_u["cd"])
    eps = eps_sb + eps_wb
    q_corr = corrected_dynamic_pressure(q_ref, eps)
    ledger.append({"step": "blockage", "value": eps,
                   "note": "eps_sb %g + eps_wb %g" % (eps_sb, eps_wb)})

    # 5. Wall interference and streamline curvature.
    delta_alpha_wall, alpha_corr = wall_interference_alpha(
        alpha_deg, s_ref, test_section_area, coef_u["cl"], delta)
    delta_alpha_curv, delta_cm = streamline_curvature_corrections(
        s_ref, test_section_area, chord, test_section_height,
        coef_u["cl"], coef_u["cm"])
    alpha_total = alpha_corr + delta_alpha_curv
    ledger.append({"step": "wall-interference", "value": delta_alpha_wall,
                   "note": "lift induced angle of attack increment (deg)"})
    ledger.append({"step": "streamline-curvature", "value": delta_cm,
                   "note": "pitching moment increment"})

    # 6. Final coefficients on the corrected dynamic pressure.
    coef_corr = force_coefficients(
        forces["lift"], forces["drag"], forces["moment"], q_corr, s_ref, c_ref)
    coef_corr["cm"] = coef_corr["cm"] + delta_cm
    ledger.append({"step": "coefficients-corrected", "value": coef_corr["cd"],
                   "note": "CD on corrected dynamic pressure"})

    return {
        "tare_at_alpha": tare_at_alpha,
        "forces_corrected": forces,
        "coefficients_uncorrected": coef_u,
        "eps_sb": eps_sb,
        "eps_wb": eps_wb,
        "eps": eps,
        "q_uncorrected": q_ref,
        "q_corrected": q_corr,
        "alpha_corrected_deg": alpha_total,
        "delta_alpha_wall_deg": delta_alpha_wall,
        "delta_alpha_curv_deg": delta_alpha_curv,
        "delta_cm": delta_cm,
        "coefficients_corrected": coef_corr,
        "ledger": ledger,
    }
