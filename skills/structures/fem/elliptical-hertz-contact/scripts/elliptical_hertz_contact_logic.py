"""General Hertz elliptical contact patch of unequal principal curvatures.

Computes the general Hertz contact solution for two smooth elastic bodies
whose combined curvature differs between the two principal planes: the
per-plane curvature coefficients A and B (A less than or equal to B) built
from the signed principal radii of both bodies, the eccentricity e of the
contact ellipse solved from the classical Hertz transcendental relation in
the complete elliptic integrals K(e) and E(e) by deterministic bisection,
the contact-ellipse major and minor semi-axes a and b (a not equal to b),
the peak contact pressure p0 = 3P/(2 pi a b) of the half-ellipsoidal
pressure distribution, the mutual approach, the patch area, and the
yield-limit load and margin of the peak pressure under the circular-arm
and line-arm static conventions of the sibling leaf.

The solution reduces exactly to the circular-patch closed form when the
curvatures are equal (e = 0 gives a = b = (3P/(4E*(A+B)))^(1/3)). Geometry
classes covered: a ball in a conforming groove or raceway, and crossed
cylinders of unequal radii. Material properties enter only through the
equivalent elastic modulus E* and the yield strength sigma_y.

Out of scope (structures/fem/hertzian-contact-stress owns these): the
circular patch (a = b), the strip of line contact of finite length L, the
point-arm and line-arm closed forms of the equal-curvature or
zero-curvature degeneracies, the subsurface shear and von Mises depth
scans. The depth-resolved subsurface stress field of the elliptical patch
itself is out of scope (numerical-integration-only slice the wave doctrine
declines); this leaf reports only the static arm conventions that bracket
first yield. FE penalty or Lagrange contact enforcement is out of scope
(structures/fem/contact-analysis).

Pure stdlib (math only), deterministic, no network, no RNG. SI units
throughout (m, N, Pa).
"""

import math

E_STEEL = 207.0e9
NU_STEEL = 0.3
E_STAR_STEEL = 113736263736.26373
P0_YIELD_POINT_FACTOR = 3.3
P0_YIELD_LINE_FACTOR = 1.6
PI = math.pi

_AGM_MAX_ITERS = 200
_AGM_DIFF_FLOOR = 1e-14
_ECC_BISECTION_ITERS = 200
_ECC_LO_FLOOR = 1e-14
_ECC_HI_CEIL = 1.0 - 1e-13
_ECC_SERIES_CUTOFF = 1e-6
_ECC_EQUAL_TOL = 1e-15


def complete_elliptic_integrals(m):
    """Complete elliptic integrals K(m), E(m) at parameter m = e^2 by AGM.

    Arithmetic-geometric mean iteration (a_0 = 1, b_0 = sqrt(1 - m)) with
    the Legendre correction sum E = K * (1 - sum_n 2^(n-1) (a_n^2 - b_n^2)),
    the first term (n = 0) equal to 0.5 * m. Iterated to a difference floor
    of 1e-16 between successive a_n, b_n.
    """
    if not (0.0 <= m < 1.0):
        raise ValueError("m must lie in [0, 1)")
    a = 1.0
    b = math.sqrt(1.0 - m)
    total = 0.5 * (a * a - b * b)
    coeff = 1.0
    for _ in range(_AGM_MAX_ITERS):
        if abs(a - b) < _AGM_DIFF_FLOOR:
            break
        a_next = 0.5 * (a + b)
        b_next = math.sqrt(a * b)
        a, b = a_next, b_next
        total += coeff * (a * a - b * b)
        coeff *= 2.0
    agm = a
    k_val = PI / (2.0 * agm)
    e_val = k_val * (1.0 - total)
    return k_val, e_val


def equivalent_modulus(e1, nu1, e2, nu2):
    """Equivalent elastic modulus E* in Pa from 1/E* = (1-nu1^2)/E1 + (1-nu2^2)/E2."""
    if e1 <= 0 or e2 <= 0:
        raise ValueError("elastic moduli must be positive")
    if not (0.0 < nu1 < 0.5) or not (0.0 < nu2 < 0.5):
        raise ValueError("Poisson ratios must lie in (0, 0.5)")
    inv_e_star = (1.0 - nu1 * nu1) / e1 + (1.0 - nu2 * nu2) / e2
    return 1.0 / inv_e_star


def curvature_sums(r1_a, r1_b, r2_a, r2_b, phi=0.0):
    """Per-plane curvature coefficients A <= B in 1/m.

    r1_a, r1_b are the two signed principal radii of body 1 and r2_a, r2_b
    of body 2 (convex positive, concave negative, flat +inf). phi is the
    angle in radians between the first principal directions of the two
    bodies (0 for aligned frames, pi/2 for crossed cylinders).
    """
    if 0.0 in (r1_a, r1_b, r2_a, r2_b):
        raise ValueError("principal radii must be nonzero")
    if not (0.0 <= phi <= PI / 2.0):
        raise ValueError("phi must lie in [0, pi/2]")
    k1a = 1.0 / r1_a
    k1b = 1.0 / r1_b
    k2a = 1.0 / r2_a
    k2b = 1.0 / r2_b
    sum_ab = 0.5 * (k1a + k1b + k2a + k2b)
    diff1 = k1a - k1b
    diff2 = k2a - k2b
    diff_ba = 0.5 * math.sqrt(
        diff1 * diff1 + diff2 * diff2 + 2.0 * diff1 * diff2 * math.cos(2.0 * phi)
    )
    a_curv = (sum_ab - diff_ba) / 2.0
    b_curv = (sum_ab + diff_ba) / 2.0
    if a_curv + b_curv <= 0.0:
        raise ValueError("curvature sum A + B must be positive to contact")
    if a_curv <= 0.0:
        raise ValueError("A must be strictly positive for the elliptical patch (A = 0 strip case belongs to hertzian-contact-stress)")
    return a_curv, b_curv


def _hertz_ratio(e):
    """Right side of the Hertz eccentricity relation B/A = f(e)."""
    if e < _ECC_SERIES_CUTOFF:
        e2 = e * e
        return (8.0 + e2) / (8.0 - 5.0 * e2)
    m = e * e
    k_val, e_val = complete_elliptic_integrals(m)
    return (e_val - (1.0 - m) * k_val) / ((1.0 - m) * (k_val - e_val))


def eccentricity(a_curv, b_curv):
    """Contact-ellipse eccentricity e in [0, 1) from the Hertz relation.

    Solves B/A = (E(e) - (1-e^2)K(e)) / ((1-e^2)(K(e)-E(e))) by
    deterministic bisection on e over [1e-14, 1 - 1e-13].
    """
    if a_curv <= 0:
        raise ValueError("a_curv must be positive (the strip case belongs to hertzian-contact-stress)")
    if b_curv < a_curv:
        raise ValueError("b_curv must be at least a_curv")
    ratio_target = b_curv / a_curv
    if ratio_target <= 1.0 + _ECC_EQUAL_TOL:
        return 0.0
    lo = _ECC_LO_FLOOR
    hi = _ECC_HI_CEIL
    for _ in range(_ECC_BISECTION_ITERS):
        mid = 0.5 * (lo + hi)
        if _hertz_ratio(mid) < ratio_target:
            lo = mid
        else:
            hi = mid
    return 0.5 * (lo + hi)


def elliptical_patch(load, e_star, a_curv, b_curv):
    """Elliptical Hertz contact patch dict for the given load and curvatures.

    Returns e, a (m, major semi-axis in the plane of curvature A), b (m,
    minor semi-axis in the plane of curvature B), ab_ratio (a/b), p0 (Pa),
    delta (m, mutual approach), area (m^2, pi a b).
    """
    if load <= 0:
        raise ValueError("load must be positive")
    if e_star <= 0:
        raise ValueError("e_star must be positive")
    e = eccentricity(a_curv, b_curv)
    m = e * e
    k_val, e_val = complete_elliptic_integrals(m)
    curv_sum = a_curv + b_curv
    base = (3.0 * load / (4.0 * e_star * curv_sum)) ** (1.0 / 3.0)
    scale = (2.0 * e_val / (PI * (1.0 - m))) ** (1.0 / 3.0)
    a_axis = base * scale
    b_axis = a_axis * math.sqrt(1.0 - m)
    p0 = 3.0 * load / (2.0 * PI * a_axis * b_axis)
    delta = 3.0 * load * k_val / (2.0 * PI * e_star * a_axis)
    area = PI * a_axis * b_axis
    return {
        "e": e,
        "a": a_axis,
        "b": b_axis,
        "ab_ratio": a_axis / b_axis,
        "p0": p0,
        "delta": delta,
        "area": area,
    }


def yield_limit_pressure(sigma_y, line_arm=False):
    """Yield-limit peak pressure: 3.3 sigma_y (point arm) or 1.6 sigma_y (line arm)."""
    if sigma_y <= 0:
        raise ValueError("sigma_y must be positive")
    factor = P0_YIELD_LINE_FACTOR if line_arm else P0_YIELD_POINT_FACTOR
    return factor * sigma_y


def yield_limit_load(p0_yield, a_val, b_val):
    """Yield-limit load in N: P_y = 2 pi a b p0_yield / 3, inverting p0 = 3P/(2 pi a b)."""
    if p0_yield <= 0 or a_val <= 0 or b_val <= 0:
        raise ValueError("p0_yield, a_val and b_val must be positive")
    return 2.0 * PI * a_val * b_val * p0_yield / 3.0


def yield_margin(p0, sigma_y, line_arm=False):
    """Margin p0_yield/p0 and pass/fail verdict against the peak pressure."""
    if p0 <= 0:
        raise ValueError("p0 must be positive")
    p0_yield = yield_limit_pressure(sigma_y, line_arm)
    margin = p0_yield / p0
    verdict = "pass" if margin >= 1.0 else "fail"
    return margin, verdict
