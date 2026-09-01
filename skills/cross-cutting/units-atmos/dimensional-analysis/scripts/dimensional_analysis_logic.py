#!/usr/bin/env python3
"""Dimensional analysis logic (stdlib, offline).

The classic dimensional analysis workflow for engineering relations:
checking whether equation terms are dimensionally homogeneous,
applying the Buckingham Pi theorem to form the dimensionless groups of
a problem, computing the similarity numbers (Reynolds, Mach, Froude),
and scaling wind tunnel model test results to full scale under dynamic
similarity. Pure functions; invalid inputs raise ValueError. No
network; stdlib only.
"""

import math

# SI base dimension labels in exponent order. Every exponent tuple in
# this module follows this order: mass M, length L, time T, temperature
# Theta, electric current I, amount of substance N, luminous intensity J.
BASE_DIMS = ("M", "L", "T", "Theta", "I", "N", "J")

# Standard gravity, m/s^2 (SI).
G0 = 9.80665

# ISA sea-level speed of sound, m/s (shared convention with unit-conversion).
SPEED_OF_SOUND_SL = 340.294

_EPS = 1e-9


def _dims_tuple(dims, name):
    """Coerce a dimension exponent sequence to a float tuple or raise."""
    if dims is None:
        raise ValueError("dimension exponents for %r must be numeric, got None" % (name,))
    try:
        out = tuple(float(d) for d in dims)
    except (TypeError, ValueError):
        raise ValueError(
            "dimension exponents for %r must be numeric, got %r" % (name, dims)
        )
    return out


def check_homogeneity(terms):
    """Return (homogeneous, common_dims) for equation terms.

    terms is a list of (name, dims) pairs, where dims is an exponent
    tuple over the SI base dimensions, e.g. ("p", (1, -1, -2)) for a
    pressure term (M L^-1 T^-2). Every term must carry the same number
    of exponents. A term with the same dimension vector as the others
    is dimensionally consistent with them. Raises ValueError for an
    empty list, malformed pairs, or ragged exponent tuples.
    """
    if not terms:
        raise ValueError("check_homogeneity needs at least one term")
    parsed = []
    length = None
    for t in terms:
        if not isinstance(t, (tuple, list)) or len(t) != 2:
            raise ValueError(
                "each term must be a (name, dims) pair, got %r" % (t,)
            )
        name, dims = t
        dims = _dims_tuple(dims, name)
        if length is None:
            length = len(dims)
        elif len(dims) != length:
            raise ValueError(
                "term %r has %d exponents, expected %d" % (name, len(dims), length)
            )
        parsed.append((name, dims))
    first = parsed[0][1]
    homogeneous = all(
        math.isclose(d[i], first[i], abs_tol=1e-12)
        for _, d in parsed[1:]
        for i in range(length)
    )
    return homogeneous, first


def _rref(a, tol=_EPS):
    """Gauss-Jordan elimination with partial pivoting.

    Returns (rref_rows, pivot_cols). Pivot columns are the columns of
    the identity-block positions; rows are in pivot order.
    """
    a = [row[:] for row in a]
    rows, cols = len(a), len(a[0])
    pivot_cols = []
    r = 0
    for c in range(cols):
        pivot = None
        for i in range(r, rows):
            if abs(a[i][c]) > tol:
                pivot = i
                break
        if pivot is None:
            continue
        a[r], a[pivot] = a[pivot], a[r]
        pv = a[r][c]
        a[r] = [x / pv for x in a[r]]
        for i in range(rows):
            if i != r and abs(a[i][c]) > tol:
                f = a[i][c]
                a[i] = [x - f * y for x, y in zip(a[i], a[r])]
        pivot_cols.append(c)
        r += 1
        if r == rows:
            break
    return a, pivot_cols


def _matrix_rank(rows, tol=_EPS):
    """Rank of a list of row vectors via RREF."""
    if not rows:
        return 0
    _, pivots = _rref(rows, tol)
    return len(pivots)


def buckingham_pi(variables, base_dims=BASE_DIMS):
    """Apply the Buckingham Pi theorem to a variable set.

    variables maps each variable name to its dimension exponent tuple
    over base_dims, e.g. sphere drag with base_dims ("M", "L", "T"):
    {"F": (1, 1, -2), "D": (0, 1, 0), "rho": (1, -3, 0),
     "V": (0, 1, -1), "mu": (1, -1, -1)}.

    Returns a dict with:
      rank        rank of the dimension matrix (independent base dims)
      n_variables number of variables
      n_pi        n_variables - rank (number of dimensionless groups)
      pi_groups   list of dicts {variable: exponent}, one per group
      base_dims   the base dimension labels used

    Each pi_groups entry is a null-space basis vector of the dimension
    matrix: every variable exponent is raised to its entry, so the
    product is dimensionless. Sign-normalized so the first nonzero
    exponent is positive. Raises ValueError for an empty or malformed
    variable set or a base_dims length mismatch.
    """
    if not isinstance(variables, dict) or not variables:
        raise ValueError(
            "variables must be a non-empty dict of {name: dims_tuple}"
        )
    names = list(variables.keys())
    ndims = len(base_dims)
    matrix = []
    for name in names:
        dims = _dims_tuple(variables[name], name)
        if len(dims) != ndims:
            raise ValueError(
                "variable %r has %d exponents, expected %d for base_dims %r"
                % (name, len(dims), ndims, base_dims)
            )
        matrix.append(dims)
    # Dimension matrix A: rows = base dimensions, cols = variables.
    a = [[matrix[v][b] for v in range(len(names))] for b in range(ndims)]
    rref, pivot_cols = _rref(a)
    rank = len(pivot_cols)
    n = len(names)
    pivot_set = set(pivot_cols)
    free_cols = [c for c in range(n) if c not in pivot_set]
    groups = []
    for j in free_cols:
        vec = [0.0] * n
        vec[j] = 1.0
        for r, pc in enumerate(pivot_cols):
            vec[pc] = -rref[r][j]
        # Zero tiny roundoff; normalize first nonzero entry positive.
        vec = [0.0 if abs(x) < 1e-9 else x for x in vec]
        for x in vec:
            if abs(x) > 1e-9:
                if x < 0.0:
                    vec = [-x for x in vec]
                break
        groups.append({names[i]: vec[i] for i in range(n) if abs(vec[i]) > 1e-12})
    return {
        "rank": rank,
        "n_variables": n,
        "n_pi": n - rank,
        "pi_groups": groups,
        "base_dims": list(base_dims),
    }


def reynolds_number(rho, v, l, mu):
    """Reynolds number Re = rho * v * l / mu (SI units).

    rho density kg/m3, v speed m/s, l characteristic length m,
    mu dynamic viscosity Pa.s. All must be positive.
    """
    for name, value in (("rho", rho), ("v", v), ("l", l), ("mu", mu)):
        if value <= 0:
            raise ValueError("%s must be > 0, got %r" % (name, value))
    return rho * v * l / mu


def mach_number(v, speed_of_sound=SPEED_OF_SOUND_SL):
    """Mach number M = v / a. speed_of_sound must be > 0, v >= 0."""
    if speed_of_sound <= 0:
        raise ValueError(
            "speed_of_sound must be > 0, got %r" % (speed_of_sound,)
        )
    if v < 0:
        raise ValueError("v must be >= 0, got %r" % (v,))
    return v / speed_of_sound


def froude_number(v, l, g=G0):
    """Froude number Fr = v / sqrt(g * l) for free-surface flows."""
    if v < 0:
        raise ValueError("v must be >= 0, got %r" % (v,))
    if l <= 0:
        raise ValueError("l must be > 0, got %r" % (l,))
    if g <= 0:
        raise ValueError("g must be > 0, got %r" % (g,))
    return v / math.sqrt(g * l)


def required_model_speed(scale_ratio, prototype_speed,
                         kinematic_viscosity_ratio=1.0):
    """Model speed (m/s) matching full-scale Reynolds number.

    scale_ratio = L_proto / L_model (e.g. 10 for a 1:10 model),
    prototype_speed is the full-scale speed m/s, and
    kinematic_viscosity_ratio = nu_model / nu_proto (1.0 for the same
    fluid). Re matching gives V_model = V_proto * scale_ratio *
    kinematic_viscosity_ratio.
    """
    if scale_ratio <= 0:
        raise ValueError("scale_ratio must be > 0, got %r" % (scale_ratio,))
    if prototype_speed < 0:
        raise ValueError(
            "prototype_speed must be >= 0, got %r" % (prototype_speed,)
        )
    if kinematic_viscosity_ratio <= 0:
        raise ValueError(
            "kinematic_viscosity_ratio must be > 0, got %r"
            % (kinematic_viscosity_ratio,)
        )
    return prototype_speed * scale_ratio * kinematic_viscosity_ratio


def force_scaling(force_model, scale_ratio, density_ratio, velocity_ratio):
    """Full-scale force from a model measurement under dynamic similarity.

    With the same dimensionless force coefficient on model and full
    scale, F_proto = F_model * scale_ratio**2 * density_ratio *
    velocity_ratio**2, where scale_ratio = L_proto / L_model,
    density_ratio = rho_proto / rho_model, and
    velocity_ratio = V_proto / V_model.
    """
    if force_model < 0:
        raise ValueError("force_model must be >= 0, got %r" % (force_model,))
    for name, value in (("scale_ratio", scale_ratio),
                        ("density_ratio", density_ratio),
                        ("velocity_ratio", velocity_ratio)):
        if value <= 0:
            raise ValueError("%s must be > 0, got %r" % (name, value))
    return force_model * scale_ratio ** 2 * density_ratio * velocity_ratio ** 2
