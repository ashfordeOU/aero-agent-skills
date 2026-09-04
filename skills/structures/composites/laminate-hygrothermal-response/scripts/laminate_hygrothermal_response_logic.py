"""Laminate hygrothermal response: exact classical lamination theory.

Pure stdlib module computing, for a symmetric balanced composite
laminate, the equilibrium moisture content from a linear isotherm, the
stiffness-weighted laminate coefficients of thermal and moisture
expansion (CTE and CME) by the exact 2x2 CLT inversion, the
hygrothermal laminate strain from a temperature and moisture change,
and the residual strain from the cure-cooldown temperature drop.

Ply properties are INPUTS (documented typical bounds in the SKILL); the
code path is exact CLT arithmetic. All coefficients are stored raw SI:
alpha in 1/K, beta per unit moisture mass fraction, strain unitless.
Deterministic, no RNG, stdlib only.

Ply dict keys: e1, e2 (Pa), nu12 (unitless), g12 (Pa), theta_deg (deg,
in [-90, 90]), t (m, ply thickness), alpha_1, alpha_2 (1/K, material
axes), beta_1, beta_2 (per unit moisture mass fraction, material axes).
"""

import math

M_SAT_DEFAULT = 0.015  # mass-fraction saturation moisture content input default
_T_RT_DEFAULT_C = 21.0  # nominal room temperature for the cure cooldown
_ANGLE_MIN_DEG = -90.0
_ANGLE_MAX_DEG = 90.0


def _require_finite(value, name):
    """Raise ValueError when a scalar is not finite."""
    if not math.isfinite(value):
        raise ValueError("%s must be finite, got %r" % (name, value))


def equilibrium_moisture_content(rh_fraction, m_sat=M_SAT_DEFAULT):
    """Return M = m_sat * rh_fraction (linear isotherm).

    ValueError when rh_fraction is outside [0, 1] or m_sat is not
    strictly positive.
    """
    _require_finite(rh_fraction, "rh_fraction")
    _require_finite(m_sat, "m_sat")
    if rh_fraction < 0.0 or rh_fraction > 1.0:
        raise ValueError("rh_fraction must be in [0, 1], got %r" % (rh_fraction,))
    if m_sat <= 0.0:
        raise ValueError("m_sat must be > 0, got %r" % (m_sat,))
    return m_sat * rh_fraction


def plane_stress_q(e1, e2, nu12, g12):
    """Return {q11, q22, q12, q66} plane-stress reduced stiffness.

    q11 = e1/d, q22 = e2/d, q12 = nu12*e2/d = nu21*e1/d, q66 = g12 with
    nu21 = nu12*e2/e1 and d = 1 - nu12*nu21.  ValueErrors on
    non-positive moduli or nu12*nu21 >= 1.
    """
    for value, name in ((e1, "e1"), (e2, "e2"), (g12, "g12"), (nu12, "nu12")):
        _require_finite(value, name)
    if e1 <= 0.0 or e2 <= 0.0 or g12 <= 0.0:
        raise ValueError("moduli e1, e2, g12 must be > 0, got (%r, %r, %r)" % (e1, e2, g12))
    nu21 = nu12 * e2 / e1
    denom = 1.0 - nu12 * nu21
    if denom <= 0.0:
        raise ValueError("nu12*nu21 = %r must be < 1" % (nu12 * nu21,))
    return {
        "q11": e1 / denom,
        "q22": e2 / denom,
        "q12": nu12 * e2 / denom,
        "q66": g12,
    }


def qbar(q, theta_deg):
    """Return {qbar11, qbar22, qbar12, qbar16, qbar26, qbar66}.

    Standard cos/sin power transform of the plane-stress stiffness with
    m = cos(theta), n = sin(theta), theta from theta_deg.
    """
    _require_finite(theta_deg, "theta_deg")
    theta = math.radians(theta_deg)
    m = math.cos(theta)
    n = math.sin(theta)
    q11 = q["q11"]
    q22 = q["q22"]
    q12 = q["q12"]
    q66 = q["q66"]
    m2 = m * m
    n2 = n * n
    m4 = m2 * m2
    n4 = n2 * n2
    m3n = m2 * m * n
    mn3 = m * n2 * n
    qbar11 = q11 * m4 + 2.0 * (q12 + 2.0 * q66) * m2 * n2 + q22 * n4
    qbar22 = q11 * n4 + 2.0 * (q12 + 2.0 * q66) * m2 * n2 + q22 * m4
    qbar12 = (q11 + q22 - 4.0 * q66) * m2 * n2 + q12 * (m4 + n4)
    qbar66 = (q11 + q22 - 2.0 * q12 - 2.0 * q66) * m2 * n2 + q66 * (m4 + n4)
    qbar16 = (q11 - q12 - 2.0 * q66) * m3n + (q12 - q22 + 2.0 * q66) * mn3
    qbar26 = (q11 - q12 - 2.0 * q66) * mn3 + (q12 - q22 + 2.0 * q66) * m3n
    return {
        "qbar11": qbar11,
        "qbar22": qbar22,
        "qbar12": qbar12,
        "qbar16": qbar16,
        "qbar26": qbar26,
        "qbar66": qbar66,
    }


def _ply_laminate_axes(ply):
    """Return (alpha_x, alpha_y, beta_x, beta_y) of one ply in laminate
    axes from its material-axis coefficients and angle (2nd-order
    tensor rotation)."""
    theta = math.radians(ply["theta_deg"])
    m2 = math.cos(theta) ** 2
    n2 = math.sin(theta) ** 2
    a1 = ply["alpha_1"]
    a2 = ply["alpha_2"]
    b1 = ply["beta_1"]
    b2 = ply["beta_2"]
    return a1 * m2 + a2 * n2, a1 * n2 + a2 * m2, b1 * m2 + b2 * n2, b1 * n2 + b2 * m2


def _qbar_from_ply(ply):
    """Reduced stiffness of one ply rotated to laminate axes."""
    q = plane_stress_q(ply["e1"], ply["e2"], ply["nu12"], ply["g12"])
    return qbar(q, ply["theta_deg"])


def _solve_2x2(a11, a12, a22, b1, b2):
    """Solve [a11 a12; a12 a22] [x1; x2] = [b1; b2] by determinant."""
    det = a11 * a22 - a12 * a12
    if det <= 0.0 or not math.isfinite(det):
        raise ValueError("in-plane stiffness A is singular (det = %r)" % (det,))
    x1 = (a22 * b1 - a12 * b2) / det
    x2 = (a11 * b2 - a12 * b1) / det
    return x1, x2


def laminate_cte_cme(plies):
    """Return {alpha_x, alpha_y, beta_x, beta_y} (raw SI) of a
    symmetric balanced laminate by the exact CLT free-expansion
    solution.

    Builds the 2x2 in-plane stiffness A = sum_k Qbar_k * t_k (rows
    [qbar11, qbar12; qbar12, qbar22]; the shear row is dropped for the
    balanced case) and the thermal force resultant per unit temperature
    Nth = sum_k Qbar_k * [alpha_x_k, alpha_y_k]^T * t_k, then solves
    A * [alpha_x, alpha_y]^T = Nth.  The moisture vector uses
    [beta_x_k, beta_y_k] the same way.  The exact inversion is required:
    the simplified stiffness-weighted scalar ratio fails the
    unidirectional identity (a 0-deg unidirectional laminate must
    return alpha_1 exactly).  ValueErrors: empty ply list, non-positive
    thickness, angle outside [-90, 90], singular A.
    """
    if not plies:
        raise ValueError("plies must contain at least one ply")
    a11 = 0.0
    a12 = 0.0
    a22 = 0.0
    nth1 = 0.0
    nth2 = 0.0
    nm1 = 0.0
    nm2 = 0.0
    for ply in plies:
        theta_deg = ply["theta_deg"]
        _require_finite(theta_deg, "theta_deg")
        if theta_deg < _ANGLE_MIN_DEG or theta_deg > _ANGLE_MAX_DEG:
            raise ValueError("ply angle must be in [-90, 90], got %r" % (theta_deg,))
        t = ply["t"]
        _require_finite(t, "t")
        if t <= 0.0:
            raise ValueError("ply thickness t must be > 0, got %r" % (t,))
        qb = _qbar_from_ply(ply)
        ax, ay, bx, by = _ply_laminate_axes(ply)
        a11 += qb["qbar11"] * t
        a12 += qb["qbar12"] * t
        a22 += qb["qbar22"] * t
        nth1 += (qb["qbar11"] * ax + qb["qbar12"] * ay) * t
        nth2 += (qb["qbar12"] * ax + qb["qbar22"] * ay) * t
        nm1 += (qb["qbar11"] * bx + qb["qbar12"] * by) * t
        nm2 += (qb["qbar12"] * bx + qb["qbar22"] * by) * t
    alpha_x, alpha_y = _solve_2x2(a11, a12, a22, nth1, nth2)
    beta_x, beta_y = _solve_2x2(a11, a12, a22, nm1, nm2)
    return {
        "alpha_x": alpha_x,
        "alpha_y": alpha_y,
        "beta_x": beta_x,
        "beta_y": beta_y,
    }


def hygrothermal_strain(alpha, beta, delta_t_k, delta_m):
    """Return eps = alpha*delta_t_k + beta*delta_m (one laminate axis).

    No ValueError beyond non-finite guards.
    """
    for value, name in ((alpha, "alpha"), (beta, "beta"),
                        (delta_t_k, "delta_t_k"), (delta_m, "delta_m")):
        _require_finite(value, name)
    return alpha * delta_t_k + beta * delta_m


def cure_cooldown_strain(alpha_x, t_cure_c, t_rt_c=_T_RT_DEFAULT_C):
    """Return the residual x strain from the cure-cooldown drop.

    delta_t = t_rt_c - t_cure_c (negative for a cooldown) and strain =
    alpha_x*delta_t.
    """
    _require_finite(alpha_x, "alpha_x")
    _require_finite(t_cure_c, "t_cure_c")
    _require_finite(t_rt_c, "t_rt_c")
    return alpha_x * (t_rt_c - t_cure_c)


def cte_ppm(alpha):
    """Return alpha * 1e6 (reporting helper; alpha in raw 1/K)."""
    _require_finite(alpha, "alpha")
    return alpha * 1.0e6


def laminate_hygrothermal_response(plies, rh_fraction, delta_t_k,
                                   delta_m=None, m_sat=M_SAT_DEFAULT,
                                   t_cure_c=None):
    """One-call laminate hygrothermal assessment.

    Returns {equilibrium_moisture_content, alpha_x, alpha_y, beta_x,
    beta_y, hygrothermal_strain_x, hygrothermal_strain_y,
    cure_strain_x (None when t_cure_c is None)}.  delta_m defaults to
    the equilibrium moisture content when not given.  All coefficients
    raw SI; cte_ppm(alpha) = alpha*1e6 is the reporting helper.
    ValueErrors propagate.
    """
    m_eq = equilibrium_moisture_content(rh_fraction, m_sat)
    if delta_m is None:
        delta_m = m_eq
    coefs = laminate_cte_cme(plies)
    eps_x = hygrothermal_strain(coefs["alpha_x"], coefs["beta_x"],
                                delta_t_k, delta_m)
    eps_y = hygrothermal_strain(coefs["alpha_y"], coefs["beta_y"],
                                delta_t_k, delta_m)
    if t_cure_c is not None:
        cure_x = cure_cooldown_strain(coefs["alpha_x"], t_cure_c)
    else:
        cure_x = None
    return {
        "equilibrium_moisture_content": m_eq,
        "alpha_x": coefs["alpha_x"],
        "alpha_y": coefs["alpha_y"],
        "beta_x": coefs["beta_x"],
        "beta_y": coefs["beta_y"],
        "hygrothermal_strain_x": eps_x,
        "hygrothermal_strain_y": eps_y,
        "cure_strain_x": cure_x,
    }
