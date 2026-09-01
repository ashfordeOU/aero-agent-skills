#!/usr/bin/env python3
"""Flat plate and skin panel buckling (paraphrase, not copy).

Common-knowledge summary of elastic plate stability (Bruhn, Niu,
Timoshenko; standards-map.yaml far-25 and cs-25 gated false,
reference-only): a flat rectangular plate of thickness t and width b
(measured across the load direction) under uniform edge compression
or edge shear buckles elastically when the applied stress reaches the
critical value

    sigma_cr = k * pi^2 * E / (12 * (1 - nu^2)) * (t / b)^2
    tau_cr  = k_s * pi^2 * E / (12 * (1 - nu^2)) * (t / b)^2

where E is the Young's modulus, nu the Poisson ratio, and k (or k_s)
the plate buckling coefficient set by the edge conditions and the
panel aspect ratio a / b (a = loaded length, b = width).

Compression coefficient, simply supported all around (exact,
minimized over the half-wave count m):

    k = min_m (m / a_r + a_r / m)^2,   a_r = a / b

which gives the long-plate value k = 4.0. The clamped long plate
approximation is k = 6.97.

Shear coefficient (simply supported, Timoshenko):

    k_s = 5.34 + 4 / a_r^2   for a_r >= 1
    k_s = 5.34 * a_r^2 + 4   for a_r <  1

and clamped:

    k_s = 8.98 + 5.6 / a_r^2  for a_r >= 1
    k_s = 8.98 * a_r^2 + 5.6  for a_r <  1

Combined compression and shear interacts approximately as

    sigma / sigma_cr + (tau / tau_cr)^2 <= 1

(linear in compression, quadratic in shear). In the post-buckling
range the stiffened skin carries load through an effective width
(von Karman): b_e = 1.9 * t * sqrt(E / sigma_edge), capped at the
panel width. Only the Python standard library is used.

Worked anchors (verified by running this module): an aluminum skin
with E = 70 GPa, nu = 0.33, t = 2 mm, stringer pitch b = 150 mm and
a/b = 2, simply supported, has k = 4.0 and sigma_cr = 45.9 MPa; an
aluminum spar web with t = 1.5 mm, depth b = 250 mm and a/b = 2 has
k_s = 6.34 and tau_cr = 14.7 MPa; an applied compression of 30 MPa
with 8 MPa of shear gives interaction index 0.947 and margin 0.056;
at an edge stress of 200 MPa the same 2 mm skin has an effective
width of 71.1 mm.

Units: SI throughout. E in Pa, t and b in m, stresses in Pa. One unit
convention, no mixing.
"""

import math

_PI2_OVER_12 = math.pi * math.pi / 12.0

# Canonical edge conditions for the flat plate.
_EDGE_ALIASES = {
    "ssss": "ssss",
    "ss": "ssss",
    "simplysupported": "ssss",
    "simply-supported": "ssss",
    "simply supported": "ssss",
    "pinned": "ssss",
    "pinned-pinned": "ssss",
    "cccc": "cccc",
    "cc": "cccc",
    "clamped": "cccc",
    "fixed": "cccc",
    "clamped-clamped": "cccc",
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


def _check_poisson(nu):
    """Validate the Poisson ratio: a finite number in [0, 0.5)."""
    if isinstance(nu, bool) or not isinstance(nu, (int, float)):
        raise ValueError("nu must be a number, got %r" % (nu,))
    nu = float(nu)
    if not math.isfinite(nu):
        raise ValueError("nu must be finite, got %r" % (nu,))
    if nu < 0.0 or nu >= 0.5:
        raise ValueError("nu must be in [0, 0.5), got %r" % (nu,))
    return nu


def _normalize_edge(edge_condition):
    """Normalize an edge-condition name to 'ssss' or 'cccc'."""
    if not isinstance(edge_condition, str):
        raise ValueError(
            "edge_condition must be a name like 'ssss' or 'cccc', got %r"
            % (edge_condition,)
        )
    name = edge_condition.strip().lower()
    canonical = _EDGE_ALIASES.get(name, _EDGE_ALIASES.get(name.replace(" ", "-")))
    if canonical is None:
        raise ValueError(
            "unknown edge_condition %r; use 'ssss' (simply supported) or "
            "'cccc' (clamped)" % (edge_condition,)
        )
    return canonical


def compression_coefficient(aspect_ratio, edge_condition="ssss"):
    """Plate buckling coefficient k for uniform edge compression.

    aspect_ratio = a / b with a the loaded length and b the width
    across the load. For 'ssss' (simply supported all around) the
    exact minimization k = min_m (m / a_r + a_r / m)^2 over the
    half-wave count m is used; a long plate gives k = 4.0. For 'cccc'
    (clamped all around) the long-plate approximation k = 6.97 is
    returned, valid for aspect_ratio >= 1; shorter clamped plates
    have a higher coefficient and need tabulated data.

    Worked anchors: a/b = 2 and a/b = 1 give k = 4.0, a/b = 1.5 gives
    k = 4.340, a/b = 0.5 gives k = 6.25, and the clamped long plate
    gives 6.97.

    Raises ValueError for a non-positive or non-finite aspect ratio,
    an unknown edge condition, or 'cccc' with aspect_ratio < 1.
    """
    a_r = _check_positive(aspect_ratio, "aspect_ratio")
    edge = _normalize_edge(edge_condition)
    if edge == "ssss":
        best = float("inf")
        for m in range(1, int(math.ceil(a_r)) + 3):
            k = (m / a_r + a_r / m) ** 2
            if k < best:
                best = k
        return best
    # 'cccc'
    if a_r < 1.0:
        raise ValueError(
            "clamped compression coefficient is only defined for "
            "aspect_ratio >= 1 (long-plate value 6.97); for shorter "
            "clamped plates use tabulated data, got %r" % (aspect_ratio,)
        )
    return 6.97


def shear_coefficient(aspect_ratio, edge_condition="ssss"):
    """Shear buckling coefficient k_s for uniform edge shear.

    Simply supported: k_s = 5.34 + 4 / a_r^2 (a_r >= 1) or
    k_s = 5.34 * a_r^2 + 4 (a_r < 1). Clamped: k_s = 8.98 + 5.6 / a_r^2
    (a_r >= 1) or k_s = 8.98 * a_r^2 + 5.6 (a_r < 1), with
    a_r = a / b the panel aspect ratio.

    Worked anchors: a/b = 2 simply supported gives k_s = 6.34, a/b =
    0.5 gives 5.335, clamped a/b = 2 gives 10.38 and a/b = 0.5 gives
    7.845.

    Raises ValueError for a non-positive or non-finite aspect ratio or
    an unknown edge condition.
    """
    a_r = _check_positive(aspect_ratio, "aspect_ratio")
    edge = _normalize_edge(edge_condition)
    if edge == "ssss":
        base, inv = 5.34, 4.0
    else:
        base, inv = 8.98, 5.6
    if a_r >= 1.0:
        return base + inv / a_r**2
    return base * a_r**2 + inv


def _plate_buckling_stress(E, nu, t, b, coefficient):
    """Critical plate stress sigma_cr = k * pi^2 * E / (12*(1-nu^2)) * (t/b)^2."""
    e = _check_positive(E, "E")
    n = _check_poisson(nu)
    th = _check_positive(t, "t")
    width = _check_positive(b, "b")
    k = _check_positive(coefficient, "coefficient")
    return k * _PI2_OVER_12 * e / (1.0 - n * n) * (th / width) ** 2


def compression_buckling_stress(E, nu, t, b, coefficient):
    """Critical compression buckling stress of a flat plate [Pa].

    sigma_cr = k * pi^2 * E / (12 * (1 - nu^2)) * (t / b)^2 with b the
    width across the load (for a skin panel, the stringer pitch).

    Worked anchor: E = 70 GPa, nu = 0.33, t = 2 mm, b = 150 mm and
    k = 4.0 give sigma_cr = 45.9 MPa.

    Raises ValueError for non-positive or non-finite inputs.
    """
    return _plate_buckling_stress(E, nu, t, b, coefficient)


def shear_buckling_stress(E, nu, t, b, coefficient):
    """Critical shear buckling stress of a flat web or panel [Pa].

    tau_cr = k_s * pi^2 * E / (12 * (1 - nu^2)) * (t / b)^2 with b the
    web depth across the shear.

    Worked anchor: E = 70 GPa, nu = 0.33, t = 1.5 mm, b = 250 mm and
    k_s = 6.34 give tau_cr = 14.7 MPa.

    Raises ValueError for non-positive or non-finite inputs.
    """
    return _plate_buckling_stress(E, nu, t, b, coefficient)


def compression_panel_check(E, nu, t, a, b, edge_condition, applied_stress):
    """Complete compression buckling check of one flat skin panel.

    Returns a dict with the resolved coefficient k, the critical
    buckling stress sigma_cr, the margin of safety
    sigma_cr / applied_stress - 1 and the stable verdict (True when
    the applied stress is below the critical stress).

    Worked anchor: E = 70 GPa, nu = 0.33, t = 2 mm, a = 300 mm,
    b = 150 mm (a/b = 2), 'ssss', applied 30 MPa gives k = 4.0,
    sigma_cr = 45.9 MPa, margin = 0.531 and stable = True.

    Raises ValueError for non-positive or non-finite inputs or an
    unknown edge condition.
    """
    e = _check_positive(E, "E")
    n = _check_poisson(nu)
    th = _check_positive(t, "t")
    length = _check_positive(a, "a")
    width = _check_positive(b, "b")
    applied = _check_positive(applied_stress, "applied_stress")
    edge = _normalize_edge(edge_condition)
    a_r = length / width
    k = compression_coefficient(a_r, edge)
    sig_cr = k * _PI2_OVER_12 * e / (1.0 - n * n) * (th / width) ** 2
    return {
        "coefficient": k,
        "critical_stress": sig_cr,
        "margin_of_safety": sig_cr / applied - 1.0,
        "stable": applied < sig_cr,
    }


def shear_panel_check(E, nu, t, a, b, edge_condition, applied_shear):
    """Complete shear buckling check of one flat web or panel.

    Returns a dict with the resolved coefficient k_s, the critical
    shear buckling stress tau_cr, the margin of safety
    tau_cr / applied_shear - 1 and the stable verdict.

    Worked anchor: E = 70 GPa, nu = 0.33, t = 1.5 mm, a = 500 mm,
    b = 250 mm (a/b = 2), 'ssss', applied 8 MPa gives k_s = 6.34,
    tau_cr = 14.7 MPa, margin = 0.844 and stable = True.

    Raises ValueError for non-positive or non-finite inputs or an
    unknown edge condition.
    """
    e = _check_positive(E, "E")
    n = _check_poisson(nu)
    th = _check_positive(t, "t")
    length = _check_positive(a, "a")
    width = _check_positive(b, "b")
    applied = _check_positive(applied_shear, "applied_shear")
    edge = _normalize_edge(edge_condition)
    a_r = length / width
    k_s = shear_coefficient(a_r, edge)
    tau_cr = k_s * _PI2_OVER_12 * e / (1.0 - n * n) * (th / width) ** 2
    return {
        "coefficient": k_s,
        "critical_stress": tau_cr,
        "margin_of_safety": tau_cr / applied - 1.0,
        "stable": applied < tau_cr,
    }


def interaction_index(compression_stress, compression_critical, shear_stress, shear_critical):
    """Combined compression and shear interaction of a flat panel.

    Index = sigma / sigma_cr + (tau / tau_cr)^2. The panel is stable
    when the index is below 1. Returns a dict with the index, the
    stable verdict and the margin of safety 1 / index - 1.

    Worked anchor: sigma = 30 MPa, sigma_cr = 45.9 MPa, tau = 8 MPa,
    tau_cr = 14.7 MPa gives index = 0.947, stable = True and margin =
    0.056.

    Raises ValueError for non-positive or non-finite inputs.
    """
    s = _check_positive(compression_stress, "compression_stress")
    s_cr = _check_positive(compression_critical, "compression_critical")
    t_sh = _check_positive(shear_stress, "shear_stress")
    t_cr = _check_positive(shear_critical, "shear_critical")
    index = s / s_cr + (t_sh / t_cr) ** 2
    return {
        "index": index,
        "stable": index <= 1.0,
        "margin_of_safety": 1.0 / index - 1.0,
    }


def effective_width(E, sigma_edge, t, constant=1.9):
    """Von Karman effective width of stiffened skin [m].

    b_e = constant * t * sqrt(E / sigma_edge) with the classic
    constant 1.9 for the total effective width (0.95 per edge). Valid
    in the post-buckling range when the edge stress exceeds the panel
    buckling stress; the result is capped by the caller at the panel
    width.

    Worked anchor: E = 70 GPa, sigma_edge = 200 MPa and t = 2 mm give
    b_e = 71.1 mm.

    Raises ValueError for non-positive or non-finite inputs.
    """
    e = _check_positive(E, "E")
    sig = _check_positive(sigma_edge, "sigma_edge")
    th = _check_positive(t, "t")
    c = _check_positive(constant, "constant")
    return c * th * math.sqrt(e / sig)
