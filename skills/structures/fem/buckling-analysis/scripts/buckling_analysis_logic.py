#!/usr/bin/env python3
"""Euler column buckling analysis (paraphrase, not copy).

Common-knowledge summary (standards-map.yaml, far-25 and cs-25:
gated false, reference-only): a slender straight column loaded in
axial compression becomes laterally unstable at the Euler critical
buckling load Pcr = pi^2 * E * I / (K * L)^2, where E is the Young's
modulus, I the second moment of area about the buckling (weak) axis,
L the actual member length and K the effective length factor set by
the end conditions (pinned-pinned K = 1, fixed-fixed K = 0.5,
fixed-pinned K = 0.7, fixed-free cantilever K = 2). The effective
length is Le = K * L and the slenderness ratio is lambda = Le / r
with r = sqrt(I / A) the radius of gyration. The Euler buckling
stress is sigma_cr = Pcr / A = pi^2 * E / lambda^2 and it only
governs above the transition slenderness lambda_1 = pi * sqrt(E /
sigma_y): below it the material yields before the elastic
instability and Euler overpredicts the capacity. Only the Python
standard library is used.

Worked anchor (verified by running this module): a steel column with
E = 200 GPa, I = 1e-6 m^4 and L = 3 m buckles at Pcr = 219.3 kN when
pinned at both ends (K = 1), at 54.8 kN as a cantilever (K = 2,
fixed-free) and at 877.3 kN when fixed at both ends (K = 0.5); with
A = 1e-3 m^2 its radius of gyration is r = 0.03162 m, its slenderness
ratio is 94.87 and the buckling stress is 219.3 MPa. For a steel
yield strength of 250 MPa the transition slenderness is 88.86, so
that column is in the slender range where Euler governs.

Units: SI throughout. E in Pa, I in m^4, A in m^2, L in m, forces in
N, stresses in Pa. One unit convention, no mixing.
"""

import math

_PI2 = math.pi * math.pi

# Canonical end conditions -> effective length factor K.
# Key: normalized name, aliases are resolved in effective_length_factor().
_END_CONDITIONS = {
    "pinned-pinned": 1.0,
    "fixed-fixed": 0.5,
    "fixed-pinned": 0.7,
    "fixed-free": 2.0,
}

_ALIASES = {
    "pinned": "pinned-pinned",
    "hinged": "pinned-pinned",
    "hinged-hinged": "pinned-pinned",
    "fixed": "fixed-fixed",
    "clamped": "fixed-fixed",
    "clamped-clamped": "fixed-fixed",
    "built-in": "fixed-fixed",
    "pinned-fixed": "fixed-pinned",
    "clamped-pinned": "fixed-pinned",
    "pinned-clamped": "fixed-pinned",
    "cantilever": "fixed-free",
    "clamped-free": "fixed-free",
}


def _check_positive(value, name):
    """Return float(value) after checking it is a positive finite number."""
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise ValueError("%s must be a number, got %r" % (name, value))
    value = float(value)
    if not math.isfinite(value):
        raise ValueError("%s must be finite, got %r" % (name, value))
    if value <= 0.0:
        raise ValueError("%s must be > 0, got %r" % (name, value))
    return value


def _normalize_end_condition(end_condition):
    """Normalize an end-condition name: lowercase, spaces to hyphens."""
    if not isinstance(end_condition, str):
        raise ValueError(
            "end_condition must be a name like 'pinned-pinned', 'fixed-fixed', "
            "'fixed-pinned' or 'cantilever', got %r" % (end_condition,)
        )
    name = end_condition.strip().lower().replace(" ", "-")
    while "--" in name:
        name = name.replace("--", "-")
    return name


def effective_length_factor(end_condition):
    """Effective length factor K for a named end condition.

    K = 1.0 pinned at both ends (pinned-pinned, pinned, hinged)
    K = 0.5 fixed at both ends (fixed-fixed, fixed, clamped)
    K = 0.7 one end fixed, one pinned (fixed-pinned, pinned-fixed)
    K = 2.0 cantilever, one end fixed and one free (fixed-free, cantilever)

    Worked anchor: the same steel column (E = 200 GPa, I = 1e-6 m^4,
    L = 3 m) buckles at 219.3 kN when pinned-pinned (K = 1), at
    877.3 kN when fixed-fixed (K = 0.5) and at 54.8 kN as a
    cantilever (K = 2); the K factor enters squared, so doubling K
    quarters Pcr.

    Raises ValueError for an unknown end-condition name.
    """
    name = _normalize_end_condition(end_condition)
    name = _ALIASES.get(name, name)
    if name not in _END_CONDITIONS:
        raise ValueError(
            "unknown end condition %r; use one of pinned-pinned, fixed-fixed, "
            "fixed-pinned, fixed-free (or aliases pinned, fixed, clamped, "
            "cantilever)" % (end_condition,)
        )
    return _END_CONDITIONS[name]


def critical_buckling_load(E, I, L, K=1.0):
    """Euler critical buckling load Pcr = pi^2 * E * I / (K * L)^2 [N].

    Worked anchor: steel column E = 200 GPa, I = 1e-6 m^4, L = 3 m,
    pinned-pinned (K = 1) gives Pcr = 219.3 kN; the same column as a
    cantilever (K = 2) gives 54.8 kN, and fixed-fixed (K = 0.5)
    gives 877.3 kN. Pcr scales with E and I and drops with the square
    of the effective length K * L.

    Raises ValueError unless E > 0, I > 0, L > 0 and K > 0.
    """
    e = _check_positive(E, "E")
    i = _check_positive(I, "I")
    length = _check_positive(L, "L")
    k = _check_positive(K, "K")
    return _PI2 * e * i / (k * length) ** 2


def effective_length(L, K=1.0):
    """Effective (buckling) length Le = K * L [m].

    Worked anchor: L = 3 m pinned-pinned (K = 1) gives Le = 3 m; the
    same member as a cantilever (K = 2) gives Le = 6 m, which is why
    the cantilever buckles at a quarter of the pinned-pinned load.
    """
    length = _check_positive(L, "L")
    k = _check_positive(K, "K")
    return k * length


def radius_of_gyration(I, A):
    """Radius of gyration r = sqrt(I / A) [m].

    Worked anchor: a solid circular column of diameter d = 0.1 m has
    I = pi * d^4 / 64 = 4.9087e-6 m^4 and A = pi * d^2 / 4 =
    7.854e-3 m^2, giving r = d / 4 = 0.025 m.
    """
    i = _check_positive(I, "I")
    a = _check_positive(A, "A")
    return math.sqrt(i / a)


def slenderness_ratio(L, K, r):
    """Effective slenderness ratio lambda = K * L / r (dimensionless).

    Worked anchor: L = 3 m, K = 1, r = 0.025 m (d = 0.1 m circular
    column) gives lambda = 120; the steel column with I = 1e-6 m^4
    and A = 1e-3 m^2 has r = 0.03162 m and lambda = 94.87.
    """
    length = _check_positive(L, "L")
    k = _check_positive(K, "K")
    radius = _check_positive(r, "r")
    return k * length / radius


def buckling_stress(E, I, A, L, K=1.0):
    """Euler buckling stress sigma_cr = Pcr / A = pi^2 * E / lambda^2 [Pa].

    Worked anchor: E = 200 GPa, I = 1e-6 m^4, A = 1e-3 m^2, L = 3 m,
    K = 1 gives sigma_cr = 219.3 MPa, identical to
    euler_stress(E, 94.87).
    """
    e = _check_positive(E, "E")
    i = _check_positive(I, "I")
    a = _check_positive(A, "A")
    length = _check_positive(L, "L")
    k = _check_positive(K, "K")
    return _PI2 * e * i / (a * (k * length) ** 2)


def euler_stress(E, slenderness):
    """Euler stress from the slenderness ratio: pi^2 * E / lambda^2 [Pa].

    Worked anchor: E = 200 GPa and lambda = 94.87 gives 219.3 MPa;
    doubling the slenderness quarters the Euler stress.
    """
    e = _check_positive(E, "E")
    lam = _check_positive(slenderness, "slenderness")
    return _PI2 * e / lam**2


def transition_slenderness(E, yield_strength):
    """Transition slenderness lambda_1 = pi * sqrt(E / sigma_y).

    Above lambda_1 the Euler elastic buckling stress is below the
    yield strength and Euler governs; below it the material yields
    first and Euler overpredicts the capacity.

    Worked anchor: steel E = 200 GPa, sigma_y = 250 MPa gives
    lambda_1 = 88.86, so the column with lambda = 94.87 is slender
    and the column with lambda = 50 is not.
    """
    e = _check_positive(E, "E")
    sy = _check_positive(yield_strength, "yield_strength")
    return math.pi * math.sqrt(e / sy)


def column_check(E, I, A, L, end_condition, applied_load, yield_strength):
    """Complete Euler buckling check of one axially loaded column.

    end_condition is a name resolved by effective_length_factor()
    ('pinned-pinned', 'fixed-fixed', 'fixed-pinned', 'cantilever',
    plus the aliases pinned, fixed, clamped) or a numeric K.

    Returns a dict with the effective length, radius of gyration,
    slenderness ratio, critical buckling load, buckling stress,
    transition slenderness, the euler_governs verdict (True when
    lambda > lambda_1) and the margin of safety
    Pcr / applied_load - 1 against the limit applied load.

    Worked anchor: E = 200 GPa, I = 1e-6 m^4, A = 1e-3 m^2, L = 3 m,
    pinned-pinned, applied load 100 kN, sigma_y = 250 MPa gives
    Pcr = 219.3 kN, lambda = 94.87 > lambda_1 = 88.86 (Euler
    governs), margin of safety = 1.19.

    Raises ValueError unless every input is positive and the end
    condition resolves.
    """
    e = _check_positive(E, "E")
    i = _check_positive(I, "I")
    a = _check_positive(A, "A")
    length = _check_positive(L, "L")
    load = _check_positive(applied_load, "applied_load")
    sy = _check_positive(yield_strength, "yield_strength")

    if isinstance(end_condition, str):
        name = _normalize_end_condition(end_condition)
        name = _ALIASES.get(name, name)
        if name not in _END_CONDITIONS:
            raise ValueError(
                "unknown end condition %r; use one of pinned-pinned, "
                "fixed-fixed, fixed-pinned, fixed-free (or aliases pinned, "
                "fixed, clamped, cantilever)" % (end_condition,)
            )
        k = _END_CONDITIONS[name]
        canonical = name
    elif isinstance(end_condition, bool) or not isinstance(
        end_condition, (int, float)
    ):
        raise ValueError(
            "end_condition must be a name string or a numeric K, got %r"
            % (end_condition,)
        )
    else:
        k = _check_positive(end_condition, "K")
        canonical = None

    le = k * length
    r = math.sqrt(i / a)
    lam = le / r
    pcr = _PI2 * e * i / le**2
    sig = pcr / a
    lam1 = math.pi * math.sqrt(e / sy)

    return {
        "end_condition": canonical,
        "effective_length_factor": k,
        "effective_length": le,
        "radius_of_gyration": r,
        "slenderness_ratio": lam,
        "critical_buckling_load": pcr,
        "buckling_stress": sig,
        "transition_slenderness": lam1,
        "euler_governs": lam > lam1,
        "margin_of_safety": pcr / load - 1.0,
    }
