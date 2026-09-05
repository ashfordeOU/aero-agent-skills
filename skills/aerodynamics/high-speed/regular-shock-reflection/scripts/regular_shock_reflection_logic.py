"""regular_shock_reflection_logic.py

Two-shock regular reflection of an oblique shock on a wall or symmetry
plane.  Pure stdlib math only, deterministic, no randomness.

An oblique shock impinging on a wall turns the flow toward the wall.  The
wall forces the flow to return parallel to it, so a reflected oblique shock
appears downstream of the impingement point.  The interaction is a REGULAR
reflection when the reflected shock can turn the flow by the same
deflection angle at the reduced Mach number behind the incident shock; it
becomes a MACH reflection when the required reflected deflection reaches
or exceeds the reflected-shock detachment limit at that Mach number.

The module solves the theta-beta-M relation for the incident weak shock,
marches the full state behind it (oblique_shock_state), then solves the
theta-beta-M relation again on the downstream state for the reflected
shock.  Mach-reflection flow details (triple point, Mach stem, slip line)
are not modeled; the verdict is the reflected-shock detachment criterion
flag only.  A detached incident shock raises ValueError.

Reference: NACA-TR-824 frames the oblique-shock relations; the formulas
here are standard compressible-flow methodology, name and paraphrase only.
"""

import math

# Module constants (standard air and solver tolerances).
GAMMA = 1.4
SHOCK_SOLVE_TOL_RAD = 1e-13
DETACH_SOLVE_TOL_RAD = 1e-12

_RAD2DEG = 180.0 / math.pi


def _deflection_formula(M1, beta_rad, gamma):
    """Raw theta-beta-M deflection at shock angle beta_rad, no validation.

    tan(theta) = 2 cot(beta) (M1^2 sin^2(beta) - 1) /
                 (M1^2 (gamma + cos(2 beta)) + 2)
    Returns the deflection angle in radians.
    """
    sin_b = math.sin(beta_rad)
    cot_b = math.cos(beta_rad) / sin_b
    top = 2.0 * cot_b * (M1 * M1 * sin_b * sin_b - 1.0)
    bottom = M1 * M1 * (gamma + math.cos(2.0 * beta_rad)) + 2.0
    return math.atan(top / bottom)


def _golden_detach(M1, gamma):
    """Golden-section peak of the deflection over the shock-angle interval.

    Returns (theta_max_deg, beta_det_rad): the maximum deflection angle in
    degrees (the attached-shock detachment limit) and the shock angle in
    radians at which it is attained.  Deterministic: fixed bracket, fixed
    golden ratio, no randomness.
    """
    mu = math.asin(1.0 / M1)
    inv_phi = (math.sqrt(5.0) - 1.0) / 2.0
    lo = mu
    hi = math.pi / 2.0
    c = hi - inv_phi * (hi - lo)
    d = lo + inv_phi * (hi - lo)
    fc = _deflection_formula(M1, c, gamma)
    fd = _deflection_formula(M1, d, gamma)
    while (hi - lo) > DETACH_SOLVE_TOL_RAD:
        if fc > fd:
            hi = d
            d = c
            fd = fc
            c = hi - inv_phi * (hi - lo)
            fc = _deflection_formula(M1, c, gamma)
        else:
            lo = c
            c = d
            fc = fd
            d = lo + inv_phi * (hi - lo)
            fd = _deflection_formula(M1, d, gamma)
    beta_det = 0.5 * (lo + hi)
    theta_max = _deflection_formula(M1, beta_det, gamma)
    return theta_max * _RAD2DEG, beta_det


def deflection_angle(M1, beta_deg, gamma=GAMMA):
    """Flow deflection angle theta (deg) for a shock angle beta (deg).

    Evaluates the theta-beta-M relation solved for the deflection at a
    given shock angle.  ValueError unless M1 > 1 and beta_deg lies
    strictly between the Mach angle asin(1/M1) and 90 degrees.
    """
    if M1 <= 1.0:
        raise ValueError("M1 must be greater than 1 for an oblique shock")
    mach_angle = math.degrees(math.asin(1.0 / M1))
    if not (mach_angle < beta_deg < 90.0):
        raise ValueError(
            "beta_deg must lie strictly between the Mach angle %.12f "
            "and 90 degrees" % mach_angle
        )
    return _deflection_formula(M1, math.radians(beta_deg), gamma) * _RAD2DEG


def maximum_deflection_angle(M1, gamma=GAMMA):
    """Maximum flow deflection theta_max (deg) for an attached shock.

    The peak of deflection_angle over shock angles from the Mach angle to
    90 degrees (the attached-shock detachment limit), located by a
    deterministic golden-section maximizer.  ValueError unless M1 > 1.
    """
    if M1 <= 1.0:
        raise ValueError("M1 must be greater than 1 for an oblique shock")
    theta_max, _ = _golden_detach(M1, gamma)
    return theta_max


def shock_angle_weak(M1, theta_deg, gamma=GAMMA):
    """Weak-branch shock angle beta (deg) for deflection theta (deg).

    Bisection over the shock-angle interval from the Mach angle to the
    detachment angle, where the deflection rises monotonically from 0 to
    theta_max.  Returns the Mach angle exactly when theta_deg is 0.
    ValueError unless M1 > 1, theta_deg >= 0, and theta_deg is below the
    maximum deflection angle (a detached or strong incident shock is out
    of scope).
    """
    if M1 <= 1.0:
        raise ValueError("M1 must be greater than 1 for an oblique shock")
    if theta_deg < 0.0:
        raise ValueError("theta_deg must be non-negative")
    theta_max, beta_det = _golden_detach(M1, gamma)
    if theta_deg >= theta_max:
        raise ValueError(
            "theta_deg %.12f reaches the maximum deflection angle %.12f, "
            "the incident shock is detached" % (theta_deg, theta_max)
        )
    mu = math.asin(1.0 / M1)
    if theta_deg == 0.0:
        return math.degrees(mu)
    lo = mu
    hi = beta_det
    target = math.radians(theta_deg)
    while (hi - lo) > SHOCK_SOLVE_TOL_RAD:
        mid = 0.5 * (lo + hi)
        if _deflection_formula(M1, mid, gamma) < target:
            lo = mid
        else:
            hi = mid
    return math.degrees(0.5 * (lo + hi))


def _total_pressure_ratio(mn1, gamma):
    """Normal-shock stagnation pressure ratio p02/p01 at normal Mach Mn1.

    Standard compressible-flow total-pressure relation across a normal
    shock at Mach number Mn1 (name and paraphrase only).
    """
    g = gamma
    term1 = (g + 1.0) * mn1 * mn1 / (2.0 + (g - 1.0) * mn1 * mn1)
    term2 = (g + 1.0) / (2.0 * g * mn1 * mn1 - (g - 1.0))
    return term1 ** (g / (g - 1.0)) * term2 ** (1.0 / (g - 1.0))


def oblique_shock_state(M1, theta_deg, gamma=GAMMA):
    """Full state behind a weak oblique shock at (M1, theta_deg).

    Returns a dict with keys beta_deg, Mn1, Mn2, M2, p2_p1, rho2_rho1,
    T2_T1 and p02_p01.  beta comes from shock_angle_weak; Mn1 = M1
    sin(beta); the density, pressure and temperature ratios and the
    downstream normal Mach number follow the standard oblique-shock
    relations; M2 = Mn2 / sin(beta - theta); p02_p01 comes from the
    normal-shock total-pressure formula evaluated at Mn1.
    """
    beta_deg = shock_angle_weak(M1, theta_deg, gamma)
    beta = math.radians(beta_deg)
    theta = math.radians(theta_deg)
    mn1 = M1 * math.sin(beta)
    mn1_2 = mn1 * mn1
    rho2_rho1 = (gamma + 1.0) * mn1_2 / ((gamma - 1.0) * mn1_2 + 2.0)
    p2_p1 = 1.0 + 2.0 * gamma * (mn1_2 - 1.0) / (gamma + 1.0)
    t2_t1 = p2_p1 / rho2_rho1
    mn2_2 = (mn1_2 + 2.0 / (gamma - 1.0)) / (
        2.0 * gamma * mn1_2 / (gamma - 1.0) - 1.0
    )
    mn2 = math.sqrt(mn2_2)
    m2 = mn2 / math.sin(beta - theta)
    return {
        "beta_deg": beta_deg,
        "Mn1": mn1,
        "Mn2": mn2,
        "M2": m2,
        "p2_p1": p2_p1,
        "rho2_rho1": rho2_rho1,
        "T2_T1": t2_t1,
        "p02_p01": _total_pressure_ratio(mn1, gamma),
    }


def shock_reflection(M1, theta_deg, gamma=GAMMA):
    """Two-shock regular reflection verdict and states at (M1, theta_deg).

    Returns a dict with keys verdict, theta_deg, M2, theta_max_ref_deg,
    incident, reflected and reason.  The incident state comes from
    oblique_shock_state(M1, theta_deg); the reflected shock must turn the
    flow back parallel to the wall, so its deflection equals theta_deg
    (straight-wall geometry).  Verdict is "regular" when M2 > 1 and
    theta_deg < theta_max_ref_deg, where theta_max_ref_deg =
    maximum_deflection_angle(M2) is the reflected-shock detachment limit;
    otherwise verdict is "mach", reflected is None and reason reports
    that the required deflection reaches the reflected-shock detachment
    limit at M2 (when the incident shock leaves M2 at or below 1 there is
    no supersonic downstream flow, theta_max_ref_deg degenerates to 0.0,
    and the verdict is "mach" for the same reason string).  A detached
    incident shock raises ValueError.
    """
    incident = oblique_shock_state(M1, theta_deg, gamma)
    m2 = incident["M2"]
    if m2 > 1.0:
        theta_max_ref = maximum_deflection_angle(m2, gamma)
    else:
        theta_max_ref = 0.0
    result = {
        "verdict": None,
        "theta_deg": theta_deg,
        "M2": m2,
        "theta_max_ref_deg": theta_max_ref,
        "incident": incident,
        "reflected": None,
        "reason": None,
    }
    if m2 > 1.0 and theta_deg < theta_max_ref:
        result["verdict"] = "regular"
        result["reflected"] = oblique_shock_state(m2, theta_deg, gamma)
    else:
        result["verdict"] = "mach"
        result["reason"] = (
            "the required deflection reaches the reflected-shock "
            "detachment limit at M2, regular reflection cannot be "
            "sustained"
        )
    return result
