#!/usr/bin/env python3
"""Airfoil shape optimization logic (deterministic, offline, stdlib only).

Common-knowledge summary (standards-map.yaml, naca-tr-824: public
domain): airfoil shape optimization varies a parameterized section to
improve an aerodynamic objective subject to geometric constraints.
Design variables come from two common parameterizations: the NACA
4-digit family (camber m, camber position p, thickness t, per NACA
Report 824) and the PARSEC 11-parameter family (open literature,
Sobieczky) used here with the exact conventions stated in
parsec_coefficients. Objectives used in practice include the
lift-to-drag ratio at the design condition, the maximum lift
coefficient margin, and the low-drag bucket width of laminar
sections. Trade studies sweep one design variable over a grid,
sensitivity analysis ranks how strongly each variable moves the
objective, and a Pareto filter keeps the non-dominated designs when
two objectives compete (for example thickness versus lift-to-drag).
All functions here are pure stdlib: deterministic, offline, and they
raise ValueError on nonsense input.
"""

import math

# The 11 PARSEC-style parameters in fixed order (documented convention).
PARSEC_KEYS = (
    "r_le",
    "x_top",
    "y_top",
    "y_xx_top",
    "x_bot",
    "y_bot",
    "y_xx_bot",
    "y_te_u",
    "y_te_l",
    "alpha_te",
    "beta_te",
)


def _check_x(x):
    if not (0.0 <= x <= 1.0):
        raise ValueError("chordwise station x must be in [0, 1], got %r" % (x,))


def _check_parsec_params(params):
    missing = [k for k in PARSEC_KEYS if k not in params]
    if missing:
        raise ValueError("PARSEC parameters missing: %s" % ", ".join(missing))
    if params["r_le"] <= 0.0:
        raise ValueError("leading edge radius r_le must be positive, got %r" % (params["r_le"],))
    for k in ("x_top", "x_bot"):
        if not (0.0 < params[k] < 1.0):
            raise ValueError("%s must be in (0, 1), got %r" % (k, params[k]))
    for k in ("alpha_te", "beta_te"):
        if not (-math.pi / 2.0 < params[k] < math.pi / 2.0):
            raise ValueError(
                "%s must be in (-pi/2, pi/2) radians, got %r" % (k, params[k])
            )
    for k in PARSEC_KEYS:
        if not math.isfinite(params[k]):
            raise ValueError("PARSEC parameter %s is not finite" % (k,))


def _solve_linear(A, b):
    """Solve A x = b by Gaussian elimination with partial pivoting."""
    n = len(b)
    M = [row[:] + [b[i]] for i, row in enumerate(A)]
    for col in range(n):
        piv = max(range(col, n), key=lambda r: abs(M[r][col]))
        if abs(M[piv][col]) < 1e-15:
            raise ValueError("singular linear system in PARSEC coefficient solve")
        if piv != col:
            M[col], M[piv] = M[piv], M[col]
        for r in range(col + 1, n):
            f = M[r][col] / M[col][col]
            for c in range(col, n + 1):
                M[r][c] -= f * M[col][c]
    x = [0.0] * n
    for r in range(n - 1, -1, -1):
        s = M[r][n] - sum(M[r][c] * x[c] for c in range(r + 1, n))
        x[r] = s / M[r][r]
    return x


def _solve_side(x_c, y_c, y_xx, r_le, sgn, y_te, angle_te):
    """Solve the 5x5 PARSEC coefficient system for one surface.

    The surface series is y(x) = sum_{i=1..6} c_i * x^(i - 1/2) with
    the leading coefficient fixed by the leading-edge radius:
    c_1 = sgn * sqrt(2 * r_le), sgn = +1 for the upper surface and -1
    for the lower. The remaining five coefficients satisfy, at the
    crest station x_c:
      y(x_c) = y_c, y'(x_c) = 0, y''(x_c) = y_xx,
    and at the trailing edge:
      y(1) = y_te, y'(1) = tan(angle_te).
    Returns the six coefficients [c_1 .. c_6].
    """
    c1 = sgn * math.sqrt(2.0 * r_le)
    A = []
    b = []
    # y(x_c) = y_c
    A.append([x_c ** (j - 0.5) for j in range(2, 7)])
    b.append(y_c - c1 * x_c ** 0.5)
    # y'(x_c) = 0
    A.append([(j - 0.5) * x_c ** (j - 1.5) for j in range(2, 7)])
    b.append(-0.5 * c1 * x_c ** -0.5)
    # y''(x_c) = y_xx
    A.append([(j - 0.5) * (j - 1.5) * x_c ** (j - 2.5) for j in range(2, 7)])
    b.append(y_xx + 0.25 * c1 * x_c ** -1.5)
    # y(1) = y_te
    A.append([1.0] * 5)
    b.append(y_te - c1)
    # y'(1) = tan(angle_te)
    A.append([(j - 0.5) for j in range(2, 7)])
    b.append(math.tan(angle_te) - 0.5 * c1)
    return [c1] + _solve_linear(A, b)


def parsec_coefficients(params):
    """PARSEC-style 11-parameter surface coefficients.

    Documented convention (angles in radians):
      upper: y_u(x) = sum_{i=1..6} a_i * x^(i - 1/2) with
        a_1 = sqrt(2 * r_le),
        y_u(x_top) = y_top, y_u'(x_top) = 0, y_u''(x_top) = y_xx_top,
        y_u(1) = y_te_u, y_u'(1) = tan(alpha_te);
      lower: y_l(x) = sum_{i=1..6} b_i * x^(i - 1/2) with
        b_1 = -sqrt(2 * r_le),
        y_l(x_bot) = y_bot, y_l'(x_bot) = 0, y_l''(x_bot) = y_xx_bot,
        y_l(1) = y_te_l, y_l'(1) = tan(beta_te).
    The eleven parameters are r_le, x_top, y_top, y_xx_top, x_bot,
    y_bot, y_xx_bot, y_te_u, y_te_l, alpha_te, beta_te. Returns
    {'upper': [a_1..a_6], 'lower': [b_1..b_6]}.
    """
    _check_parsec_params(params)
    upper = _solve_side(
        params["x_top"],
        params["y_top"],
        params["y_xx_top"],
        params["r_le"],
        1.0,
        params["y_te_u"],
        params["alpha_te"],
    )
    lower = _solve_side(
        params["x_bot"],
        params["y_bot"],
        params["y_xx_bot"],
        params["r_le"],
        -1.0,
        params["y_te_l"],
        params["beta_te"],
    )
    return {"upper": upper, "lower": lower}


def parsec_ordinates(coeffs, x):
    """Upper and lower ordinates (y_u, y_l) from coefficients at station x."""
    _check_x(x)
    yu = sum(coeffs["upper"][i] * x ** (i + 0.5) for i in range(6))
    yl = sum(coeffs["lower"][i] * x ** (i + 0.5) for i in range(6))
    return (yu, yl)


def parsec_slope(coeffs, x):
    """Upper and lower surface slopes dy/dx from coefficients at station x.

    The PARSEC series has an infinite slope at the leading edge
    (x = 0), so x = 0 raises ValueError.
    """
    _check_x(x)
    if x == 0.0:
        raise ValueError("PARSEC slope is singular at the leading edge x = 0")
    su = sum((i + 0.5) * coeffs["upper"][i] * x ** (i - 0.5) for i in range(6))
    sl = sum((i + 0.5) * coeffs["lower"][i] * x ** (i - 0.5) for i in range(6))
    return (su, sl)


def parsec_curvature(coeffs, x):
    """Upper and lower surface curvatures d2y/dx2 from coefficients at x.

    The second derivative is singular at x = 0; x = 0 raises
    ValueError.
    """
    _check_x(x)
    if x == 0.0:
        raise ValueError("PARSEC curvature is singular at the leading edge x = 0")
    ku = sum(
        (i + 0.5) * (i - 0.5) * coeffs["upper"][i] * x ** (i - 1.5) for i in range(6)
    )
    kl = sum(
        (i + 0.5) * (i - 0.5) * coeffs["lower"][i] * x ** (i - 1.5) for i in range(6)
    )
    return (ku, kl)


def parsec_surface(params, x):
    """Upper and lower ordinates at station x for a full PARSEC parameter set."""
    return parsec_ordinates(parsec_coefficients(params), x)


def lift_drag_ratio(cl, cd):
    """Lift-to-drag ratio objective at the design point: cl / cd.

    cd must be positive; non-finite values raise ValueError.
    """
    if not math.isfinite(cl) or not math.isfinite(cd):
        raise ValueError("lift and drag coefficients must be finite, got %r %r" % (cl, cd))
    if cd <= 0.0:
        raise ValueError("drag coefficient must be positive, got %r" % (cd,))
    return cl / cd


def drag_bucket_width(polar, tolerance=0.2):
    """Width of the low-drag bucket from a (cl, cd) polar table.

    polar is a list of (cl, cd) pairs. The bucket is the cl range over
    which cd <= cd_min * (1 + tolerance), cd_min being the minimum
    drag coefficient in the table. Returns a dict with cd_min,
    threshold, cl_min, cl_max, and width (0.0 with cl_min/cl_max None
    when fewer than two polar points fall inside the bucket).
    """
    if tolerance <= 0.0:
        raise ValueError("tolerance must be positive, got %r" % (tolerance,))
    if not polar:
        raise ValueError("polar must be a non-empty list of (cl, cd) pairs")
    for cl, cd in polar:
        if not math.isfinite(cl) or not math.isfinite(cd):
            raise ValueError("polar contains a non-finite (cl, cd) pair: %r %r" % (cl, cd))
    cd_min = min(cd for _, cd in polar)
    threshold = cd_min * (1.0 + tolerance)
    bucket = [cl for cl, cd in polar if cd <= threshold]
    if len(bucket) < 2:
        return {
            "cd_min": cd_min,
            "threshold": threshold,
            "cl_min": None,
            "cl_max": None,
            "width": 0.0,
        }
    return {
        "cd_min": cd_min,
        "threshold": threshold,
        "cl_min": min(bucket),
        "cl_max": max(bucket),
        "width": max(bucket) - min(bucket),
    }


def clmax_trend_model(camber, clmax_ref, slope):
    """Local linear trend for clmax versus camber: clmax_ref + slope * camber.

    The slope must be calibrated from the user's own polar data (for
    example two XFOIL runs at different cambers). This is a local
    trend model for trade studies, not a physics prediction.
    """
    for v in (camber, clmax_ref, slope):
        if not math.isfinite(v):
            raise ValueError("clmax trend inputs must be finite, got %r" % (v,))
    return clmax_ref + slope * camber


def clmax_margin(clmax_candidate, clmax_required):
    """Relative clmax margin: (candidate - required) / required."""
    if not math.isfinite(clmax_candidate) or not math.isfinite(clmax_required):
        raise ValueError("clmax inputs must be finite, got %r %r" % (clmax_candidate, clmax_required))
    if clmax_required <= 0.0:
        raise ValueError("required clmax must be positive, got %r" % (clmax_required,))
    return (clmax_candidate - clmax_required) / clmax_required


def constraint_violations(design, constraints):
    """Check bound constraints; return the list of violated variable names.

    design maps variable names to values. constraints maps variable
    names to a {'min': ..., 'max': ...} mapping, either bound optional.
    Raises ValueError when a constraint names an unknown variable,
    when min > max, or when a design value is not finite.
    """
    violated = []
    for var, bounds in constraints.items():
        if var not in design:
            raise ValueError("constraint variable %r is not in the design" % (var,))
        if not isinstance(bounds, dict):
            raise ValueError(
                "constraint for %r must be a {'min'/'max'} mapping, got %r" % (var, bounds)
            )
        lo = bounds.get("min")
        hi = bounds.get("max")
        if lo is not None and hi is not None and lo > hi:
            raise ValueError("constraint min %r > max %r for %r" % (lo, hi, var))
        v = design[var]
        if not math.isfinite(v):
            raise ValueError("design value for %r is not finite: %r" % (var, v))
        if lo is not None and v < lo:
            violated.append(var)
        elif hi is not None and v > hi:
            violated.append(var)
    return violated


def trade_sweep(objective_fn, param_values, minimize=False):
    """Evaluate objective_fn over a one-dimensional parameter sweep.

    param_values is an iterable of parameter values. Returns a list of
    (param, value) tuples sorted by value (descending, or ascending
    when minimize is True); ties break by parameter value ascending for
    determinism.
    """
    vals = list(param_values)
    if not vals:
        raise ValueError("param_values must be non-empty")
    points = []
    for p in vals:
        if not math.isfinite(p):
            raise ValueError("parameter value is not finite: %r" % (p,))
        points.append((p, objective_fn(p)))
    points.sort(key=lambda pair: (pair[1], pair[0]))
    if not minimize:
        points.reverse()
    return points


def best_trade_point(sweep_points, minimize=False):
    """Best (param, value) from a trade_sweep result; ties break on lower param."""
    if not sweep_points:
        raise ValueError("sweep_points must be non-empty")
    if minimize:
        return min(sweep_points, key=lambda pair: (pair[1], pair[0]))
    return min(sweep_points, key=lambda pair: (-pair[1], pair[0]))


def central_difference_gradient(f, x0, h=1e-5):
    """Gradient of scalar f at x0 by central finite differences.

    x0 is a sequence of coordinates, h the step applied to each
    variable. Returns the list of partial derivatives df/dx_i.
    """
    x = [float(v) for v in x0]
    if not x:
        raise ValueError("x0 must be non-empty")
    if not (h > 0.0):
        raise ValueError("step h must be positive, got %r" % (h,))
    grad = []
    for i in range(len(x)):
        xp = list(x)
        xm = list(x)
        xp[i] += h
        xm[i] -= h
        fp = f(xp)
        fm = f(xm)
        if not math.isfinite(fp) or not math.isfinite(fm):
            raise ValueError("objective is not finite at perturbation of variable %d" % i)
        grad.append((fp - fm) / (2.0 * h))
    return grad


def relative_sensitivity(f, x0, h=1e-5):
    """Normalized sensitivity (df/dx_i) * (x_i / f(x0)) at x0.

    Ranks which design variable moves the objective most per unit
    relative change. Raises ValueError when f(x0) is zero, where the
    normalization is undefined.
    """
    f0 = f(x0)
    if not math.isfinite(f0):
        raise ValueError("objective is not finite at x0")
    if f0 == 0.0:
        raise ValueError("relative sensitivity is undefined at a zero objective")
    grad = central_difference_gradient(f, x0, h)
    return [g * x0[i] / f0 for i, g in enumerate(grad)]


def _dominates(a, b, minimize_both):
    """True when point a dominates point b on both objectives."""
    better = (lambda x, y: x < y) if minimize_both else (lambda x, y: x > y)
    worse = (lambda x, y: x > y) if minimize_both else (lambda x, y: x < y)
    if not (better(a[0], b[0]) or better(a[1], b[1])):
        return False
    return not (worse(a[0], b[0]) or worse(a[1], b[1]))


def pareto_front(points, minimize_both=True):
    """Two-objective Pareto filter; returns the non-dominated points.

    points is a list of (obj1, obj2, label) tuples. A point dominates
    another when it is no worse on both objectives and strictly better
    on at least one ('better' means lower when minimize_both, higher
    otherwise). The result is sorted by (obj1, label) for determinism.
    """
    if not points:
        raise ValueError("points must be non-empty")
    non_dominated = []
    for a in points:
        if not any(_dominates(b, a, minimize_both) for b in points if b is not a):
            non_dominated.append(a)
    non_dominated.sort(key=lambda t: (t[0], t[2]))
    return non_dominated
