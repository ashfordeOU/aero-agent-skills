"""Shock-expansion theory for a supersonic diamond (double-wedge) airfoil.

Pure-stdlib module implementing the oblique-shock and Prandtl-Meyer
relations internally (no imports from sibling leaves) and patching them
turn by turn over the four planar surfaces of a diamond airfoil to build
the surface pressure distribution, then integrating panel forces into
section lift, wave drag and leading-edge moment coefficients.

Sign conventions (documented, used throughout):
- Angles in degrees; gamma is the ratio of specific heats (module default
  GAMMA_DEFAULT = 1.4).
- Body axes: x downstream along the chord (leading edge at x = 0),
  y upward.  Positive angle of attack alpha means the freestream velocity
  vector points at +alpha to the chord, i.e. the relative wind comes from
  below and impinges on the LOWER surface (nose-up airfoil).
- The diamond is symmetric about the chord with semi-wedge half-angle
  eps: upper-front surface at +eps, upper-rear at -eps, lower-front at
  -eps, lower-rear at +eps to the chord (four panels, each projecting
  c/2 on the chord).
- Deflection theta is signed: a positive theta compresses the flow
  (oblique shock, weak solution); a negative theta expands the flow
  (Prandtl-Meyer fan).  Upper-front deflection theta_uf = eps - alpha
  (weak shock when alpha < eps, expansion fan when alpha > eps);
  lower-front theta_lf = eps + alpha (shock for alpha > 0); both rear
  corners turn the flow away by 2*eps (expansion).
- Force on each panel is (p - p_inf) * panel_length acting along the
  inward unit normal (pressure pushes into the body).  Lift and drag are
  resolved perpendicular and parallel to the freestream direction, which
  sits at +alpha to the chord in body axes.  Section moment cm_le is
  about the leading edge, positive nose-up.
- Results are sectional (per unit span) and nondimensional; chord c is a
  normalization length and defaults to 1.
"""

import math

GAMMA_DEFAULT = 1.4


# ----------------------------------------------------------------------
# Local gas-dynamic relations (theta-beta-M and Prandtl-Meyer)
# ----------------------------------------------------------------------

def _check_finite(name, value):
    if not math.isfinite(value):
        raise ValueError("non-finite input for %s: %r" % (name, value))


def theta_beta_m(m1, theta_deg, gamma=GAMMA_DEFAULT):
    """Return the weak oblique-shock wave angle beta (deg) for deflection
    theta_deg at upstream Mach m1.  Bisection on the theta-beta-M
    relation over the weak branch.  Raises ValueError when the deflection
    exceeds the maximum turning angle at this Mach number."""
    _check_finite("m1", m1)
    _check_finite("theta_deg", theta_deg)
    _check_finite("gamma", gamma)
    if gamma <= 1.0:
        raise ValueError("gamma must be greater than 1")
    if m1 <= 1.0 + 1e-9:
        raise ValueError("oblique shocks require supersonic m1 > 1, got %r" % m1)
    if theta_deg < 0.0:
        raise ValueError("theta_deg must be non-negative, got %r" % theta_deg)
    theta = math.radians(theta_deg)
    mu = math.asin(1.0 / m1)  # Mach angle, lower end of the weak branch

    def turn_at(beta):
        # theta(beta) from the oblique-shock relation.
        s = math.sin(beta)
        num = 2.0 * (math.cos(beta) / s) * (m1 * m1 * s * s - 1.0)
        den = m1 * m1 * (gamma + math.cos(2.0 * beta)) + 2.0
        return math.atan(num / den)

    # Locate the peak turning angle on (mu, pi/2) by ternary search.
    lo, hi = mu + 1e-10, math.pi / 2.0 - 1e-10
    for _ in range(120):
        a = lo + (hi - lo) / 3.0
        b = hi - (hi - lo) / 3.0
        if turn_at(a) < turn_at(b):
            lo = a
        else:
            hi = b
    beta_peak = 0.5 * (lo + hi)
    theta_max = turn_at(beta_peak)
    if theta > theta_max * (1.0 + 1e-9):
        raise ValueError(
            "deflection %r deg exceeds the max turning angle %.6f deg "
            "at m1 = %r" % (theta_deg, math.degrees(theta_max), m1))
    # Weak solution: bisect beta on [mu, beta_peak].
    lo, hi = mu + 1e-10, beta_peak
    for _ in range(200):
        mid = 0.5 * (lo + hi)
        if turn_at(mid) < theta:
            lo = mid
        else:
            hi = mid
    return math.degrees(0.5 * (lo + hi))


def oblique_shock_ratios(m1, theta_deg, gamma=GAMMA_DEFAULT):
    """Return (m2, p2_p1) across an attached weak oblique shock with
    deflection theta_deg at upstream Mach m1."""
    beta_deg = theta_beta_m(m1, theta_deg, gamma)
    beta = math.radians(beta_deg)
    theta = math.radians(theta_deg)
    mn1 = m1 * math.sin(beta)
    mn1sq = mn1 * mn1
    p2_p1 = 1.0 + (2.0 * gamma / (gamma + 1.0)) * (mn1sq - 1.0)
    mn2sq = (1.0 + 0.5 * (gamma - 1.0) * mn1sq) / (
        gamma * mn1sq - 0.5 * (gamma - 1.0))
    m2 = math.sqrt(mn2sq) / math.sin(beta - theta)
    return m2, p2_p1


def prandtl_meyer_angle(m, gamma=GAMMA_DEFAULT):
    """Return the Prandtl-Meyer function nu(m) in degrees."""
    _check_finite("m", m)
    _check_finite("gamma", gamma)
    if gamma <= 1.0:
        raise ValueError("gamma must be greater than 1")
    if m < 1.0:
        raise ValueError("Prandtl-Meyer angle requires supersonic m >= 1, got %r" % m)
    root = math.sqrt((gamma + 1.0) / (gamma - 1.0))
    inside = math.sqrt(max((gamma - 1.0) * (m * m - 1.0) / (gamma + 1.0), 0.0))
    return math.degrees(root * math.atan(inside) - math.atan(math.sqrt(m * m - 1.0)))


def _prandtl_meyer_mach(nu_deg, gamma=GAMMA_DEFAULT):
    """Invert nu(m) = nu_deg for the Mach number m (internal helper)."""
    target_rad = math.radians(nu_deg)
    nu_max_rad = math.radians(prandtl_meyer_angle(1e6, gamma))
    if target_rad > nu_max_rad:
        raise ValueError(
            "Prandtl-Meyer turn requires nu %.3f deg beyond the limiting "
            "value %.3f deg" % (nu_deg, math.degrees(nu_max_rad)))
    lo, hi = 1.0 + 1e-12, 2.0
    while prandtl_meyer_angle(hi, gamma) < nu_deg:
        hi *= 2.0
    for _ in range(200):
        mid = 0.5 * (lo + hi)
        if prandtl_meyer_angle(mid, gamma) < nu_deg:
            lo = mid
        else:
            hi = mid
    return 0.5 * (lo + hi)


def prandtl_meyer_turn(m1, theta_deg, gamma=GAMMA_DEFAULT):
    """Return (m2, p2_p1) across a Prandtl-Meyer expansion turning the
    flow through theta_deg (positive theta_deg expands the flow)."""
    _check_finite("m1", m1)
    _check_finite("theta_deg", theta_deg)
    if m1 < 1.0:
        raise ValueError("Prandtl-Meyer turn requires supersonic m1 >= 1, got %r" % m1)
    if theta_deg < 0.0:
        raise ValueError("theta_deg must be non-negative, got %r" % theta_deg)
    nu1 = prandtl_meyer_angle(m1, gamma)
    m2 = _prandtl_meyer_mach(nu1 + theta_deg, gamma)
    p2_p1 = ((1.0 + 0.5 * (gamma - 1.0) * m1 * m1) /
             (1.0 + 0.5 * (gamma - 1.0) * m2 * m2)) ** (gamma / (gamma - 1.0))
    return m2, p2_p1


# ----------------------------------------------------------------------
# Diamond airfoil panel model
# ----------------------------------------------------------------------

def _validate_airfoil_inputs(m1, alpha_deg, eps_deg, gamma):
    for name, value in (("m1", m1), ("alpha_deg", alpha_deg),
                        ("eps_deg", eps_deg), ("gamma", gamma)):
        _check_finite(name, value)
    if gamma <= 1.0:
        raise ValueError("gamma must be greater than 1")
    if m1 <= 1.0 + 1e-9:
        raise ValueError("shock-expansion analysis requires supersonic "
                         "m1 > 1, got %r" % m1)
    if abs(alpha_deg) >= 90.0:
        raise ValueError("|alpha| must be below 90 deg, got %r" % alpha_deg)
    if eps_deg < 0.0 or eps_deg >= 45.0:
        raise ValueError("eps (half-angle) must lie in [0, 45) deg, "
                         "got %r" % eps_deg)


def panel_state(m, p_ratio_in, theta_deg, gamma=GAMMA_DEFAULT):
    """Turn-by-turn state calculator.

    Returns (m_out, p_out) where m_out is the Mach number and p_out the
    pressure (as a multiple of the freestream pressure, carried through
    p_ratio_in) after a deflection theta_deg.  Positive theta_deg is a
    compression (oblique shock, weak solution); negative theta_deg is an
    expansion (Prandtl-Meyer fan).  Raises ValueError on detaching turns.
    """
    if theta_deg > 0.0:
        m_out, p2_p1 = oblique_shock_ratios(m, theta_deg, gamma)
    elif theta_deg < 0.0:
        m_out, p2_p1 = prandtl_meyer_turn(m, -theta_deg, gamma)
    else:
        m_out, p2_p1 = m, 1.0
    return m_out, p_ratio_in * p2_p1


def surface_pressures(m1, alpha_deg, eps_deg, gamma=GAMMA_DEFAULT):
    """Return the pressure coefficient Cp on each diamond surface.

    Dict keys: uf (upper front), ur (upper rear), lf (lower front),
    lr (lower rear).  Cp = (p/p_inf - 1) / (0.5 * gamma * m1**2) with the
    freestream dynamic-pressure normalization.  The front-surface state
    is the inlet condition for the rear-surface turn on the same side.
    """
    _validate_airfoil_inputs(m1, alpha_deg, eps_deg, gamma)
    q_ref = 0.5 * gamma * m1 * m1

    # Deflections in degrees, positive = compression, negative = expansion.
    theta_uf = eps_deg - alpha_deg
    theta_lf = eps_deg + alpha_deg
    theta_rear = -2.0 * eps_deg

    m_uf, p_uf = panel_state(m1, 1.0, theta_uf, gamma)
    m_lf, p_lf = panel_state(m1, 1.0, theta_lf, gamma)
    m_ur, p_ur = panel_state(m_uf, p_uf, theta_rear, gamma)
    m_lr, p_lr = panel_state(m_lf, p_lf, theta_rear, gamma)

    surfaces = {
        "uf": {"cp": (p_uf - 1.0) / q_ref, "m": m_uf, "p_pinf": p_uf,
               "theta_deg": theta_uf},
        "ur": {"cp": (p_ur - 1.0) / q_ref, "m": m_ur, "p_pinf": p_ur,
               "theta_deg": theta_rear},
        "lf": {"cp": (p_lf - 1.0) / q_ref, "m": m_lf, "p_pinf": p_lf,
               "theta_deg": theta_lf},
        "lr": {"cp": (p_lr - 1.0) / q_ref, "m": m_lr, "p_pinf": p_lr,
               "theta_deg": theta_rear},
    }
    return surfaces


# Panel geometry on a diamond of chord c: each of the four planar faces
# projects c/2 on the chord, so the physical panel length is
# (c/2)/cos(eps) and the panel runs at +/- eps to the chord.  With the
# upper surface at +eps the outward normals point away from the body;
# pressure forces act along the inward unit normals (below).
#   uf: inward normal ( sin eps, -cos eps), center (c/4,  (c/4) tan eps)
#   ur: inward normal (-sin eps, -cos eps), center (3c/4, (c/4) tan eps)
#   lf: inward normal ( sin eps,  cos eps), center (c/4, -(c/4) tan eps)
#   lr: inward normal (-sin eps,  cos eps), center (3c/4,-(c/4) tan eps)
# Section coefficients use q_ref c and q_ref c**2 with chord c = 1.


def shock_expansion_airfoil(m1, alpha_deg, eps_deg, gamma=GAMMA_DEFAULT):
    """Section shock-expansion solution for a diamond airfoil.

    Returns a summary dict with cl, cd_wave, cm_le (positive nose-up
    about the leading edge), the input state, and the per-surface Cp
    table from surface_pressures.  Lift and wave drag are resolved onto
    the freestream direction, which lies at +alpha to the chord.
    """
    _validate_airfoil_inputs(m1, alpha_deg, eps_deg, gamma)
    surfaces = surface_pressures(m1, alpha_deg, eps_deg, gamma)
    alpha = math.radians(alpha_deg)
    eps = math.radians(eps_deg)
    q_ref = 0.5 * gamma * m1 * m1

    # Per-panel inward normals and face centers (body axes, chord c = 1).
    sin_e, cos_e = math.sin(eps), math.cos(eps)
    normals = {
        "uf": (sin_e, -cos_e), "ur": (-sin_e, -cos_e),
        "lf": (sin_e, cos_e), "lr": (-sin_e, cos_e),
    }
    centers = {
        "uf": (0.25, 0.25 * math.tan(eps)),
        "ur": (0.75, 0.25 * math.tan(eps)),
        "lf": (0.25, -0.25 * math.tan(eps)),
        "lr": (0.75, -0.25 * math.tan(eps)),
    }
    panel_len = 0.5 / cos_e

    fx_body, fy_body, moment_le = 0.0, 0.0, 0.0
    for key in ("uf", "ur", "lf", "lr"):
        dp = surfaces[key]["p_pinf"] - 1.0
        nx, ny = normals[key]
        cx, cy = centers[key]
        force_x = dp * panel_len * nx
        force_y = dp * panel_len * ny
        fx_body += force_x
        fy_body += force_y
        # Moment about the leading edge, positive nose-up (CCW).
        moment_le += cx * force_y - cy * force_x

    # Resolve body-axis forces onto freestream-aligned lift and drag.
    cos_a, sin_a = math.cos(alpha), math.sin(alpha)
    drag = fx_body * cos_a + fy_body * sin_a
    lift = -fx_body * sin_a + fy_body * cos_a
    cl = lift / q_ref
    cd_wave = drag / q_ref
    cm_le = moment_le / q_ref

    return {
        "m1": m1, "alpha_deg": alpha_deg, "eps_deg": eps_deg,
        "gamma": gamma, "cl": cl, "cd_wave": cd_wave, "cm_le": cm_le,
        "surface_cp": {k: v["cp"] for k, v in surfaces.items()},
        "surfaces": surfaces,
    }


