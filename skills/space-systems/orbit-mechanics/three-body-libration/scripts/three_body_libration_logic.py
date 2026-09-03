"""Circular restricted three-body problem (CR3BP) libration point analysis.

Pure stdlib. Nondimensional rotating frame: the heavier primary 1 sits at
x = -mu, the lighter primary 2 at x = 1 - mu, the barycenter at x = 0, and
distances are normalized by the primary separation a. The collinear points
L1, L2, L3 are roots of the rotating-frame force balance

    f(x) = x - (1 - mu) * (x + mu) / |x + mu|**3
              - mu * (x - (1 - mu)) / |x - (1 - mu)|**3

solved with a bracketed Newton iteration and a bisection fallback. The
triangular points L4, L5 come from the closed-form equilateral construction.
The Jacobi constant evaluates an energy-like integral of motion for a given
planar rotating-frame state.
"""

import math

# Module constants (SI where dimensional).
GRAV = 6.67430e-11              # m^3 / (kg s^2), gravitational constant
MU_EARTH_MOON_DEFAULT = 0.01215  # representative Earth-Moon mass ratio
ND_TOL = 1e-12                  # Newton convergence on |f(x)|
ND_MAX_ITER = 80                # Newton iteration cap before bisection fallback
BISECT_STEPS = 200              # bisection fallback step count
PRIMARY_SINGULARITY = 1e-12     # exclusion radius around a primary position

_DEFAULT_GUESS = {"L2": 1.2, "L3": -1.2}


def _bracket(mu, branch):
    """Return the (lo, hi) root bracket for a collinear branch at mass ratio mu."""
    if branch == "L1":
        return (-mu + 1e-6, 1.0 - mu - 1e-6)
    if branch == "L2":
        return (1.0 - mu + 1e-6, 5.0)
    return (-5.0, -mu - 1e-6)  # L3


def mass_ratio(mass_primary, mass_secondary):
    """mu = m2 / (m1 + m2) for a primary m1 and secondary m2.

    Raises ValueError if either mass is non-positive or if the secondary is
    not lighter than the primary (mu >= 0.5 breaks the frame convention).
    """
    if mass_primary <= 0 or mass_secondary <= 0:
        raise ValueError("primary and secondary masses must be positive")
    mu = mass_secondary / (mass_primary + mass_secondary)
    if mu >= 0.5:
        raise ValueError("secondary mass must be below the primary mass, mu < 0.5")
    return mu


def collinear_force_balance(x, mu):
    """Rotating-frame force balance f(x) for the collinear points.

    f(x) = x - (1 - mu)(x + mu)/|x + mu|^3 - mu(x - (1 - mu))/|x - (1 - mu)|^3.
    Roots are L1 (between the primaries), L2 (beyond the secondary) and L3
    (beyond the primary). Raises ValueError if x lands on a primary.
    """
    if not (0.0 < mu < 0.5):
        raise ValueError("mass ratio mu must lie in (0, 0.5)")
    r1 = abs(x + mu)
    r2 = abs(x - (1.0 - mu))
    if r1 < PRIMARY_SINGULARITY or r2 < PRIMARY_SINGULARITY:
        raise ValueError("force balance is singular on a primary position")
    f = x - (1.0 - mu) * (x + mu) / r1 ** 3 - mu * (x - (1.0 - mu)) / r2 ** 3
    return f


def _force_balance_derivative(x, mu):
    """Analytic derivative of the collinear force balance.

    d/dx[(x + c)/|x + c|^3] = -2/|x + c|^3 away from the singularity, so
    f'(x) = 1 + 2(1 - mu)/|x + mu|^3 + 2 mu/|x - (1 - mu)|^3 > 0.
    """
    r1 = abs(x + mu)
    r2 = abs(x - (1.0 - mu))
    return 1.0 + 2.0 * (1.0 - mu) / r1 ** 3 + 2.0 * mu / r2 ** 3


def _bisection(mu, branch, lo, hi):
    """Bisection fallback: BISECT_STEPS halvings on a sign-change bracket."""
    f_lo = collinear_force_balance(lo, mu)
    for _ in range(BISECT_STEPS):
        mid = 0.5 * (lo + hi)
        f_mid = collinear_force_balance(mid, mu)
        if f_lo * f_mid <= 0.0:
            hi = mid
        else:
            lo = mid
            f_lo = f_mid
    return 0.5 * (lo + hi)


def collinear_point(mu, branch, x_guess=None):
    """Solve f(x) = 0 for one collinear libration point.

    Newton iteration from x_guess (defaults: L1 at the midpoint 0.5 - mu
    between the primaries, L2 at 1.2, L3 at -1.2). If Newton leaves the branch
    bracket or does not converge within ND_MAX_ITER, fall back to a 200-step
    bisection on the branch bracket. Raises ValueError for an unknown branch
    or mu outside (0, 0.5). Returns the converged dimensionless x.
    """
    if branch not in ("L1", "L2", "L3"):
        raise ValueError("branch must be one of L1, L2, L3")
    if not (0.0 < mu < 0.5):
        raise ValueError("mass ratio mu must lie in (0, 0.5)")
    lo, hi = _bracket(mu, branch)
    if x_guess is None:
        x_guess = 0.5 - mu if branch == "L1" else _DEFAULT_GUESS[branch]
    x = x_guess
    converged = False
    for _ in range(ND_MAX_ITER):
        f = collinear_force_balance(x, mu)
        if abs(f) < ND_TOL:
            converged = True
            break
        df = _force_balance_derivative(x, mu)
        x_new = x - f / df
        if not (lo < x_new < hi):
            break  # Newton left the branch bracket, use bisection
        x = x_new
    if not converged:
        x = _bisection(mu, branch, lo, hi)
    return x


def lagrange_points(mu):
    """All five libration points as a dict.

    L1, L2, L3 map to their dimensionless x (roots of the force balance);
    L4 and L5 map to (x, y) tuples from the equilateral construction,
    x = 0.5 - mu, y = +/- sqrt(3)/2 in the barycentric frame.
    """
    if not (0.0 < mu < 0.5):
        raise ValueError("mass ratio mu must lie in (0, 0.5)")
    s3 = math.sqrt(3.0) / 2.0
    return {
        "L1": collinear_point(mu, "L1"),
        "L2": collinear_point(mu, "L2"),
        "L3": collinear_point(mu, "L3"),
        "L4": (0.5 - mu, s3),
        "L5": (0.5 - mu, -s3),
    }


def physical_distance_from_primary(x, mu, separation_m, primary=1):
    """Convert a dimensionless x to a physical distance from one primary.

    Primary 1 (heavier, at x = -mu): distance = (x + mu) * separation_m.
    Primary 2 (lighter, at x = 1 - mu): distance = abs(x - (1 - mu)) *
    separation_m. Raises ValueError if separation_m is non-positive or primary
    is not 1 or 2.
    """
    if separation_m <= 0:
        raise ValueError("primary separation must be positive")
    if primary not in (1, 2):
        raise ValueError("primary must be 1 (heavier) or 2 (lighter)")
    if not (0.0 < mu < 0.5):
        raise ValueError("mass ratio mu must lie in (0, 0.5)")
    if primary == 1:
        return (x + mu) * separation_m
    return abs(x - (1.0 - mu)) * separation_m


def jacobi_constant(mu, x, y, vx, vy):
    """Jacobi constant C for a planar rotating-frame state.

    C = x^2 + y^2 + 2(1 - mu)/r1 + 2 mu/r2 - (vx^2 + vy^2) with
    r1 = sqrt((x + mu)^2 + y^2), r2 = sqrt((x - (1 - mu))^2 + y^2).
    Raises ValueError if the state sits on top of a primary (r < 1e-12).
    """
    if not (0.0 < mu < 0.5):
        raise ValueError("mass ratio mu must lie in (0, 0.5)")
    r1 = math.sqrt((x + mu) ** 2 + y ** 2)
    r2 = math.sqrt((x - (1.0 - mu)) ** 2 + y ** 2)
    if r1 < 1e-12 or r2 < 1e-12:
        raise ValueError("state is on top of a primary, distance below 1e-12")
    return (x ** 2 + y ** 2 + 2.0 * (1.0 - mu) / r1
            + 2.0 * mu / r2 - (vx ** 2 + vy ** 2))


def three_body_assessment(mass_primary, mass_secondary, separation_m, state=None):
    """One-shot three-body libration assessment.

    Returns {mu, lagrange_points, L1_distance_from_primary_km,
    L2_distance_from_primary_km, jacobi_constant (only if state given)}.
    The L1 distance is quoted from the heavier primary (primary 1, e.g.
    Earth); L2, which lies beyond the lighter primary, is quoted from the
    lighter primary (primary 2, e.g. the Moon). state is a dict {x, y, vx,
    vy} in dimensionless rotating-frame units. Distances are in kilometers.
    """
    mu = mass_ratio(mass_primary, mass_secondary)
    points = lagrange_points(mu)
    x_l1 = points["L1"]
    x_l2 = points["L2"]
    result = {
        "mu": mu,
        "lagrange_points": points,
        "L1_distance_from_primary_km": physical_distance_from_primary(
            x_l1, mu, separation_m, primary=1) / 1000.0,
        "L2_distance_from_primary_km": physical_distance_from_primary(
            x_l2, mu, separation_m, primary=2) / 1000.0,
    }
    if state is not None:
        result["jacobi_constant"] = jacobi_constant(
            mu, state["x"], state["y"], state["vx"], state["vy"])
    return result
