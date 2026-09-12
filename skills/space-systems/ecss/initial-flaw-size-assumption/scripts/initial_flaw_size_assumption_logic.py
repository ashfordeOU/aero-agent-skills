"""
Initial flaw size assumption logic for ECSS fracture control.

Governing clause: ECSS-E-ST-32C §7.2.6 — Initial crack size/shape
selection from NDT detection capability (Figures 7-1..7-3).

All flaw dimensions in millimetres. No external dependencies.
"""

from dataclasses import dataclass
from typing import Optional, List


# ---------------------------------------------------------------------------
# NDT capability table (paraphrased from ECSS-E-ST-32C §7.2.6 guidance;
# values represent minimum reliably detectable flaw dimensions at 95 % PoD /
# 90 % confidence, applicable to standard metallic aerospace structure).
# ---------------------------------------------------------------------------
#
# Keys:
#   a_mm  — minimum detectable crack depth (mm)
#   c_mm  — minimum detectable crack half-surface-length (mm); None for
#            volumetric methods that do not resolve surface half-length directly
#   native_shape — flaw shape this method characterises natively
#
_NDT_CAPABILITY: dict = {
    "PT": {
        "a_mm": 0.75,
        "c_mm": 1.25,
        "native_shape": "surface_semi_elliptical",
        "description": "Liquid penetrant testing — surface-breaking flaws only",
    },
    "MT": {
        "a_mm": 0.50,
        "c_mm": 1.00,
        "native_shape": "surface_semi_elliptical",
        "description": "Magnetic particle testing — ferromagnetic materials, surface/near-surface",
    },
    "ET": {
        "a_mm": 0.40,
        "c_mm": 0.80,
        "native_shape": "surface_semi_elliptical",
        "description": "Eddy current testing — electrically conductive materials, surface cracks",
    },
    "RT": {
        "a_mm": 1.25,
        "c_mm": None,
        "native_shape": "through_crack",
        "description": "Radiographic testing — volumetric flaws; governs through-thickness geometry",
    },
    "UT": {
        "a_mm": 0.50,
        "c_mm": None,
        "native_shape": "through_crack",
        "description": "Ultrasonic testing — volumetric flaws; governs through-thickness geometry",
    },
    "UNINSPECTED": {
        "a_mm": 1.27,
        "c_mm": 1.905,
        "native_shape": "surface_semi_elliptical",
        "description": "No NDT inspection — standard uninspected-part default flaw",
    },
}

# Recognised geometry tokens and the flaw shape each maps to
_GEOMETRY_SHAPE_MAP: dict = {
    "surface": "surface_semi_elliptical",
    "corner": "corner_quarter_circle",
    "through": "through_crack",
    "edge": "corner_quarter_circle",
    "hole": "corner_quarter_circle",
}

VALID_NDT_METHODS: List[str] = list(_NDT_CAPABILITY.keys())
VALID_GEOMETRIES: List[str] = list(_GEOMETRY_SHAPE_MAP.keys())


@dataclass
class FlawAssumption:
    ndt_method: str
    depth_mm: float
    half_length_mm: Optional[float]   # None for through-cracks
    shape: str
    aspect_ratio: Optional[float]     # a/c; None for through-cracks
    compliant: bool                   # depth_mm < critical_flaw_size_mm
    critical_flaw_size_mm: Optional[float]
    notes: str


def _validate_ndt_method(method: str) -> None:
    if method not in _NDT_CAPABILITY:
        raise ValueError(
            f"Unknown NDT method '{method}'. "
            f"Accepted values: {', '.join(VALID_NDT_METHODS)}."
        )


def _validate_geometry(geometry: str) -> None:
    if geometry not in _GEOMETRY_SHAPE_MAP:
        raise ValueError(
            f"Unknown geometry '{geometry}'. "
            f"Accepted values: {', '.join(VALID_GEOMETRIES)}."
        )


def _validate_positive(value: float, label: str) -> None:
    if value <= 0.0:
        raise ValueError(f"'{label}' must be positive; got {value}.")


def get_ndt_capability(method: str) -> dict:
    """Return the capability entry for a single NDT method."""
    _validate_ndt_method(method)
    return dict(_NDT_CAPABILITY[method])


def select_most_sensitive_method(methods: List[str]) -> str:
    """
    From a list of NDT methods applied to the same region, return the
    method with the smallest minimum detectable crack depth (most sensitive).
    Ties are broken by smallest half-length (c_mm); further ties favour the
    first method encountered in the list.
    """
    if not methods:
        raise ValueError("At least one NDT method must be provided.")
    for m in methods:
        _validate_ndt_method(m)

    def sort_key(m: str):
        cap = _NDT_CAPABILITY[m]
        c = cap["c_mm"] if cap["c_mm"] is not None else float("inf")
        return (cap["a_mm"], c)

    return min(methods, key=sort_key)


def assign_flaw_shape(geometry: str, ndt_method: str) -> str:
    """
    Return the flaw shape token for the given component geometry.
    For corner/edge/hole geometries the shape is always corner_quarter_circle
    regardless of NDT method.  For surface or through geometry the shape
    follows the geometry mapping.
    """
    _validate_geometry(geometry)
    _validate_ndt_method(ndt_method)
    return _GEOMETRY_SHAPE_MAP[geometry]


def compute_aspect_ratio(depth_mm: float, half_length_mm: float) -> float:
    """
    Compute flaw aspect ratio a/c. Both arguments must be positive.
    An aspect ratio of 1.0 denotes a semi-circular or quarter-circular crack.
    """
    _validate_positive(depth_mm, "depth_mm")
    _validate_positive(half_length_mm, "half_length_mm")
    return depth_mm / half_length_mm


def determine_initial_flaw(
    ndt_method: str,
    geometry: str,
    critical_flaw_size_mm: Optional[float] = None,
) -> FlawAssumption:
    """
    Determine the initial flaw size assumption.

    Parameters
    ----------
    ndt_method : str
        Governing NDT method (or 'UNINSPECTED').
    geometry : str
        Component geometry token: 'surface', 'corner', 'edge', 'hole',
        or 'through'.
    critical_flaw_size_mm : float, optional
        Material/stress-state critical crack depth a_c.  When provided,
        compliance is checked; otherwise compliant is set to True and
        a note records that no critical size was supplied.

    Returns
    -------
    FlawAssumption dataclass.
    """
    _validate_ndt_method(ndt_method)
    _validate_geometry(geometry)

    cap = _NDT_CAPABILITY[ndt_method]
    shape = assign_flaw_shape(geometry, ndt_method)

    # Depth is always defined.
    depth_mm = cap["a_mm"]

    # Half-length and aspect ratio depend on shape.
    if shape == "through_crack":
        # Through-cracks are characterised by half-length b, not a separate depth.
        # Use the NDT a_mm as the half-crack-length b for through geometry;
        # aspect ratio is not applicable.
        half_length_mm = None
        aspect_ratio = None
    elif shape == "corner_quarter_circle":
        # Corner crack: a = c = radius; half_length == depth by definition.
        half_length_mm = depth_mm
        aspect_ratio = 1.0
    else:
        # Surface semi-elliptical: use capability c_mm if available,
        # else fall back to depth (treating it as semi-circular).
        half_length_mm = cap["c_mm"] if cap["c_mm"] is not None else depth_mm
        aspect_ratio = compute_aspect_ratio(depth_mm, half_length_mm)

    # Compliance check.
    if critical_flaw_size_mm is not None:
        _validate_positive(critical_flaw_size_mm, "critical_flaw_size_mm")
        compliant = depth_mm < critical_flaw_size_mm
        note_suffix = (
            f"depth {depth_mm} mm < critical {critical_flaw_size_mm} mm — compliant."
            if compliant
            else (
                f"depth {depth_mm} mm >= critical {critical_flaw_size_mm} mm — "
                "NON-COMPLIANT: part may be critical at initial flaw size."
            )
        )
    else:
        compliant = True
        note_suffix = "No critical flaw size supplied; compliance not evaluated."

    notes = (
        f"Method: {ndt_method} | Shape: {shape} | Geometry: {geometry} | {note_suffix}"
    )

    return FlawAssumption(
        ndt_method=ndt_method,
        depth_mm=depth_mm,
        half_length_mm=half_length_mm,
        shape=shape,
        aspect_ratio=aspect_ratio,
        compliant=compliant,
        critical_flaw_size_mm=critical_flaw_size_mm,
        notes=notes,
    )


def determine_initial_flaw_from_methods(
    ndt_methods: List[str],
    geometry: str,
    critical_flaw_size_mm: Optional[float] = None,
) -> FlawAssumption:
    """
    Determine initial flaw from multiple inspection methods applied to the
    same region.  The most sensitive (smallest a_min) method governs.
    """
    governing = select_most_sensitive_method(ndt_methods)
    result = determine_initial_flaw(governing, geometry, critical_flaw_size_mm)
    # Annotate that multiple methods were evaluated.
    superseded = [m for m in ndt_methods if m != governing]
    if superseded:
        result = FlawAssumption(
            ndt_method=result.ndt_method,
            depth_mm=result.depth_mm,
            half_length_mm=result.half_length_mm,
            shape=result.shape,
            aspect_ratio=result.aspect_ratio,
            compliant=result.compliant,
            critical_flaw_size_mm=result.critical_flaw_size_mm,
            notes=(
                result.notes
                + f" | Superseded methods: {', '.join(superseded)}."
            ),
        )
    return result
