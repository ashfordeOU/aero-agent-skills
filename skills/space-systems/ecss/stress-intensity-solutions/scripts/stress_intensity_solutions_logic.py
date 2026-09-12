"""
stress_intensity_solutions_logic.py

Stress intensity factor (K) selection and computation for common crack
geometries in metallic spacecraft structures, per ECSS-E-ST-32C clause 7.2.7.

Implements geometry categorization, K-solution selection from ESACRACK /
approved compendia analogues, and analytical K evaluation for:
  - Surface semi-elliptical crack in a flat plate (Newman-Raju 1984)
  - Center through crack in an infinite plate (Irwin)
  - Center through crack in a finite-width plate (Feddersen secant)
  - Single edge through crack in a finite-width plate (Tada-Paris-Irwin)
  - Quarter-elliptical corner crack at a circular hole (Kt-augmented)

All K values are in the same stress * length^0.5 units as the inputs.
No external dependencies — stdlib only.
"""

import math
from typing import Any, Dict, Optional


# ---------------------------------------------------------------------------
# Geometry type catalogue
# ---------------------------------------------------------------------------

CRACK_GEOMETRIES = frozenset({
    "surface_semi_elliptical",   # semi-ellipse on a plate surface
    "through_infinite",          # center through crack, infinite plate
    "through_finite_center",     # center through crack, finite-width plate
    "edge_through",              # single edge through crack, finite-width plate
    "corner_at_hole",            # quarter-elliptical corner crack at a circular hole
})


# ---------------------------------------------------------------------------
# Input validation helpers
# ---------------------------------------------------------------------------

def _validate_positive(name: str, value: float) -> None:
    if not isinstance(value, (int, float)):
        raise TypeError(f"{name} must be numeric, got {type(value).__name__}")
    if value <= 0.0:
        raise ValueError(f"{name} must be > 0, got {value!r}")


def validate_geometry_type(geometry: str) -> None:
    """Raise ValueError if geometry is not in the supported catalogue."""
    if geometry not in CRACK_GEOMETRIES:
        raise ValueError(
            f"Unknown crack geometry '{geometry}'. "
            f"Supported: {sorted(CRACK_GEOMETRIES)}"
        )


# ---------------------------------------------------------------------------
# Geometry categorization
# ---------------------------------------------------------------------------

def categorize_crack_geometry(
    a: float,
    c: Optional[float] = None,
    t: Optional[float] = None,
    W: Optional[float] = None,
    at_hole: bool = False,
    is_edge: bool = False,
) -> str:
    """
    Categorize a crack into one of the supported K-solution geometry families.

    Parameters
    ----------
    a        : crack depth (surface crack) or crack half-length (through crack)
    c        : surface half-length; required for surface_semi_elliptical and corner_at_hole
    t        : plate thickness; required for surface_semi_elliptical and corner_at_hole
    W        : plate half-width (center crack) or full width (edge crack); required for
               through_finite_center and edge_through
    at_hole  : True → quarter-elliptical corner crack at a circular hole
    is_edge  : True → single edge through crack (requires W)

    Returns
    -------
    Geometry-type string from CRACK_GEOMETRIES.
    """
    _validate_positive("a", a)

    if at_hole:
        if c is None or t is None:
            raise ValueError("corner_at_hole requires both c and t")
        _validate_positive("c", c)
        _validate_positive("t", t)
        return "corner_at_hole"

    if c is not None and t is not None:
        _validate_positive("c", c)
        _validate_positive("t", t)
        if a >= t:
            raise ValueError(
                f"Surface crack depth a={a} must be less than plate thickness t={t}"
            )
        return "surface_semi_elliptical"

    if is_edge:
        if W is None:
            raise ValueError("edge_through requires plate width W")
        _validate_positive("W", W)
        if a >= W:
            raise ValueError(
                f"Edge crack length a={a} must be less than plate width W={W}"
            )
        return "edge_through"

    if W is not None:
        _validate_positive("W", W)
        if a >= W:
            raise ValueError(
                f"Through-crack half-length a={a} must be less than plate half-width W={W}"
            )
        return "through_finite_center"

    return "through_infinite"


# ---------------------------------------------------------------------------
# Shape factor
# ---------------------------------------------------------------------------

def shape_factor_elliptic(a_over_c: float) -> float:
    """
    Flaw-shape parameter Q (≈ squared complete elliptic integral of the second
    kind), per the Newman-Raju (1984) approximation.

    Q = 1 + 1.464 * (a/c)^1.65   for a/c <= 1
    For a/c > 1 the crack is taller than it is wide; invert the ratio before
    calling, then multiply back the appropriate correction in the K formula.
    """
    if a_over_c <= 0.0:
        raise ValueError(f"a/c must be > 0, got {a_over_c!r}")
    ratio = min(a_over_c, 1.0)
    return 1.0 + 1.464 * (ratio ** 1.65)


# ---------------------------------------------------------------------------
# K-solution implementations
# ---------------------------------------------------------------------------

def K_surface_semi_elliptical(
    sigma: float,
    a: float,
    c: float,
    t: float,
    phi_deg: float = 90.0,
) -> float:
    """
    Mode-I K for a surface semi-elliptical crack in a flat plate under remote
    tension, per Newman-Raju (1984) Engineering Fracture Mechanics 15, 185-192
    (tension-only term, no finite-width correction applied).

    K = sigma * F * sqrt(pi * a / Q)

    Parameters
    ----------
    sigma   : remote tensile stress (> 0)
    a       : crack depth (perpendicular to plate surface)
    c       : surface half-crack-length (along the surface)
    t       : plate thickness  (a < t required)
    phi_deg : parametric angle in degrees; 90 = deepest point, 0 = surface ends
    """
    _validate_positive("sigma", sigma)
    _validate_positive("a", a)
    _validate_positive("c", c)
    _validate_positive("t", t)
    if a >= t:
        raise ValueError(
            f"Crack depth a={a} must be less than plate thickness t={t}"
        )
    if not (0.0 <= phi_deg <= 90.0):
        raise ValueError(f"phi_deg must be in [0, 90], got {phi_deg!r}")

    a_over_c = a / c
    a_over_t = a / t
    phi = math.radians(phi_deg)

    # Shape factor Q
    if a_over_c <= 1.0:
        Q = shape_factor_elliptic(a_over_c)
    else:
        Q = shape_factor_elliptic(1.0 / a_over_c)

    # Boundary-correction coefficients M1, M2, M3 (Newman-Raju 1984 Table 1)
    if a_over_c <= 1.0:
        M1 = 1.13 - 0.09 * a_over_c
        M2 = -0.54 + 0.89 / (0.2 + a_over_c)
        M3 = 0.5 - 1.0 / (0.65 + a_over_c) + 14.0 * ((1.0 - a_over_c) ** 24)
    else:
        M1 = math.sqrt(a_over_c) * (1.0 + 0.04 / a_over_c)
        M2 = 0.2 * (a_over_c ** 4)
        M3 = -0.11 * (a_over_c ** 4)

    # Angular correction g (equals 1.0 at phi=90°, deepest point)
    g = 1.0 + (0.1 + 0.35 * (a_over_t ** 2)) * ((1.0 - math.sin(phi)) ** 2)

    # Angular function f_phi
    f_phi = ((a_over_c ** 2) * (math.cos(phi) ** 2) + math.sin(phi) ** 2) ** 0.25

    # Boundary-correction factor F (no finite-width term; fw = 1)
    F = (M1 + M2 * (a_over_t ** 2) + M3 * (a_over_t ** 4)) * g * f_phi

    return sigma * F * math.sqrt(math.pi * a / Q)


def K_through_infinite(sigma: float, a: float) -> float:
    """
    Mode-I K for a center through crack in an infinite plate (Irwin):
        K = sigma * sqrt(pi * a)
    """
    _validate_positive("sigma", sigma)
    _validate_positive("a", a)
    return sigma * math.sqrt(math.pi * a)


def K_through_finite_center(sigma: float, a: float, W: float) -> float:
    """
    Mode-I K for a center through crack in a finite-width plate of half-width W,
    using the Feddersen (1966) secant correction:
        K = sigma * sqrt(pi * a * sec(pi * a / (2 * W)))

    a : crack half-length  (a < W required)
    W : plate half-width
    """
    _validate_positive("sigma", sigma)
    _validate_positive("a", a)
    _validate_positive("W", W)
    if a >= W:
        raise ValueError(
            f"Crack half-length a={a} must be less than plate half-width W={W}"
        )
    arg = math.pi * a / (2.0 * W)
    sec_val = 1.0 / math.cos(arg)
    return sigma * math.sqrt(math.pi * a * sec_val)


def K_edge_through(sigma: float, a: float, W: float) -> float:
    """
    Mode-I K for a single edge through crack in a finite-width plate of width W,
    using the Tada-Paris-Irwin (2000) polynomial correction (valid for a/W < 0.6):
        F(a/W) = 1.12 - 0.231*(a/W) + 10.55*(a/W)^2 - 21.72*(a/W)^3 + 30.39*(a/W)^4
        K = sigma * sqrt(pi * a) * F(a/W)

    a : crack length from the free edge
    W : full plate width (a < W and a/W < 0.6 required)
    """
    _validate_positive("sigma", sigma)
    _validate_positive("a", a)
    _validate_positive("W", W)
    if a >= W:
        raise ValueError(
            f"Edge crack length a={a} must be less than plate width W={W}"
        )
    r = a / W
    if r >= 0.6:
        raise ValueError(
            f"a/W = {r:.4f} exceeds the polynomial validity bound of 0.6; "
            "use a full-range formula or compendium table for large a/W."
        )
    F = (
        1.12
        - 0.231 * r
        + 10.55 * r ** 2
        - 21.72 * r ** 3
        + 30.39 * r ** 4
    )
    return sigma * math.sqrt(math.pi * a) * F


def K_corner_at_hole(
    sigma: float, a: float, R: float, t: float
) -> float:
    """
    Simplified Mode-I K for a quarter-elliptical (corner) crack emanating from
    the bore of a circular hole of radius R in a plate of thickness t under
    remote tension (Newman 1971 simplified form):

        Kt_eff = 3 * (1 - a / (a + R))
        K = sigma * 0.97 * Kt_eff * sqrt(pi * a / Q)

    where Q is the shape factor for a quarter-circular crack (a/c = 1).
    The 0.97 factor accounts for the free-surface condition at the hole bore.

    a : corner crack length (depth into plate or along bore)
    R : hole radius
    t : plate thickness (a <= t required)
    """
    _validate_positive("sigma", sigma)
    _validate_positive("a", a)
    _validate_positive("R", R)
    _validate_positive("t", t)
    if a > t:
        raise ValueError(
            f"Corner crack depth a={a} should not exceed plate thickness t={t}"
        )
    Q = shape_factor_elliptic(1.0)   # quarter-circular crack: a/c = 1
    Kt_eff = 3.0 * (1.0 - a / (a + R))
    F_hole = 0.97 * Kt_eff
    return sigma * F_hole * math.sqrt(math.pi * a / Q)


# ---------------------------------------------------------------------------
# LEFM dominance check
# ---------------------------------------------------------------------------

def check_lefm_dominance(K: float, sigma: float, a: float) -> Dict[str, Any]:
    """
    Report the geometric correction factor and a coarse LEFM-dominance
    indicator.  The ratio K² / (sigma² * pi * a) equals F²/Q; values between
    0.5 and 5.0 are well within the range of standard K-solution corrections.

    Returns a dict: K_over_Kref (= sqrt(ratio)), ratio, lefm_indicator.
    """
    _validate_positive("K", K)
    _validate_positive("sigma", sigma)
    _validate_positive("a", a)
    ratio = (K ** 2) / (sigma ** 2 * math.pi * a)
    indicator = "within_bounds" if 0.5 <= ratio <= 5.0 else "check_required"
    return {
        "K_over_Kref": math.sqrt(ratio),
        "ratio": ratio,
        "lefm_indicator": indicator,
    }


# ---------------------------------------------------------------------------
# Main dispatcher
# ---------------------------------------------------------------------------

def select_and_compute_K(
    crack_geometry: str,
    sigma: float,
    params: Dict[str, Any],
) -> Dict[str, Any]:
    """
    Select the applicable K-solution for the stated crack geometry and compute K.

    Parameters
    ----------
    crack_geometry : one of CRACK_GEOMETRIES
    sigma          : remote applied stress
    params         : geometry-parameter dict; required keys by geometry:
        surface_semi_elliptical  → a, c, t; optional phi_deg (default 90)
        through_infinite         → a
        through_finite_center    → a, W
        edge_through             → a, W
        corner_at_hole           → a, R, t

    Returns
    -------
    dict: geometry, K, solution_ref, params_used
    """
    validate_geometry_type(crack_geometry)
    _validate_positive("sigma", sigma)

    if crack_geometry == "surface_semi_elliptical":
        phi_deg = params.get("phi_deg", 90.0)
        K = K_surface_semi_elliptical(
            sigma, params["a"], params["c"], params["t"], phi_deg
        )
        ref = "Newman-Raju (1984) EFM 15:185-192 Eq.1-5; ESACRACK surface-crack"

    elif crack_geometry == "through_infinite":
        K = K_through_infinite(sigma, params["a"])
        ref = "Irwin (1957); ESACRACK center-through-infinite"

    elif crack_geometry == "through_finite_center":
        K = K_through_finite_center(sigma, params["a"], params["W"])
        ref = "Feddersen (1966) secant correction; ESACRACK center-through-finite"

    elif crack_geometry == "edge_through":
        K = K_edge_through(sigma, params["a"], params["W"])
        ref = "Tada-Paris-Irwin (2000) Table 2.1; ESACRACK edge-through"

    elif crack_geometry == "corner_at_hole":
        K = K_corner_at_hole(sigma, params["a"], params["R"], params["t"])
        ref = "Newman (1971) simplified; ESACRACK corner-at-hole"

    else:
        raise ValueError(f"Unhandled geometry: {crack_geometry}")

    return {
        "geometry": crack_geometry,
        "K": K,
        "solution_ref": ref,
        "params_used": dict(params, sigma=sigma),
    }
