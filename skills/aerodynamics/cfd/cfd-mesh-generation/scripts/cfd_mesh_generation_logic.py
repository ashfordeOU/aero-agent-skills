#!/usr/bin/env python3
"""CFD mesh generation logic for aerospace cases.

Common-knowledge mesh-generation methodology (standards-map.yaml,
naca-tr-824: public domain reference data only): the near-wall mesh
is sized from the target dimensionless wall distance y+ = y * u_tau /
nu, so the first cell height is y = y+ * nu / u_tau, with u_tau
derived from the skin friction coefficient u_tau = v_inf *
sqrt(cf / 2). Boundary-layer prism layers grow the first cell outward
with a geometric growth ratio until the boundary-layer thickness is
covered. Grid type selection trades geometry complexity against
boundary-layer resolution needs: structured grids for simple
geometries, unstructured grids for complex geometries without an
explicit boundary-layer mesh, hybrid grids (prisms near the wall,
unstructured elsewhere) for wall-bounded complex geometries. Cell
quality is checked against skewness, orthogonality angle, and aspect
ratio limits. All inputs are SI: meters, m/s, m^2/s, Pa, kg/m^3.
"""

import math


def first_cell_height(y_plus_target, u_tau_ms, nu_m2_s):
    """First cell height y = y+ * nu / u_tau from a target y+.

    Raises ValueError when any input is not positive.
    """
    if y_plus_target <= 0:
        raise ValueError("y_plus_target must be > 0, got %r" % (y_plus_target,))
    if u_tau_ms <= 0:
        raise ValueError("u_tau must be > 0, got %r" % (u_tau_ms,))
    if nu_m2_s <= 0:
        raise ValueError("nu must be > 0, got %r" % (nu_m2_s,))
    return y_plus_target * nu_m2_s / u_tau_ms


def first_cell_height_from_cf(y_plus_target, cf, v_inf_ms, nu_m2_s):
    """First cell height from skin friction coefficient.

    Computes u_tau = v_inf * sqrt(cf / 2), then y = y+ * nu / u_tau.
    Raises ValueError when any input is not positive.
    """
    if cf <= 0:
        raise ValueError("cf must be > 0, got %r" % (cf,))
    if v_inf_ms <= 0:
        raise ValueError("v_inf must be > 0, got %r" % (v_inf_ms,))
    u_tau = v_inf_ms * math.sqrt(cf / 2.0)
    return first_cell_height(y_plus_target, u_tau, nu_m2_s)


def achieved_y_plus(first_cell_m, u_tau_ms, nu_m2_s):
    """Achieved y+ = y * u_tau / nu for a given first cell height.

    Raises ValueError when any input is not positive.
    """
    if first_cell_m <= 0:
        raise ValueError("first_cell_m must be > 0, got %r" % (first_cell_m,))
    if u_tau_ms <= 0:
        raise ValueError("u_tau must be > 0, got %r" % (u_tau_ms,))
    if nu_m2_s <= 0:
        raise ValueError("nu must be > 0, got %r" % (nu_m2_s,))
    return first_cell_m * u_tau_ms / nu_m2_s


def prism_layer_count(first_cell_m, boundary_layer_thickness_m, growth_ratio):
    """Number of prism layers to cover the boundary layer.

    Prism layers stack with a geometric growth ratio: total height
    after n layers is h1 * (r^n - 1) / (r - 1). Returns the smallest
    n >= 1 whose total covers boundary_layer_thickness_m. A thickness
    no larger than the first cell height needs one layer. Raises
    ValueError when first_cell_m or boundary_layer_thickness_m is not
    positive or when growth_ratio is not > 1.
    """
    if first_cell_m <= 0:
        raise ValueError("first_cell_m must be > 0, got %r" % (first_cell_m,))
    if boundary_layer_thickness_m <= 0:
        raise ValueError(
            "boundary_layer_thickness_m must be > 0, got %r"
            % (boundary_layer_thickness_m,)
        )
    if growth_ratio <= 1.0:
        raise ValueError("growth_ratio must be > 1, got %r" % (growth_ratio,))
    if boundary_layer_thickness_m <= first_cell_m:
        return 1
    n = math.log(
        1.0 + (growth_ratio - 1.0) * boundary_layer_thickness_m / first_cell_m
    ) / math.log(growth_ratio)
    return max(1, math.ceil(n))


def grid_type_recommendation(geometry_complexity, boundary_layer_resolution):
    """Recommend structured, unstructured, or hybrid grid.

    geometry_complexity is 'simple', 'moderate', or 'complex';
    boundary_layer_resolution is a bool saying whether the mesh must
    resolve the boundary layer with prism layers. Mapping: simple ->
    structured; moderate -> hybrid when boundary-layer resolved else
    unstructured; complex -> hybrid when boundary-layer resolved else
    unstructured. Raises ValueError on invalid inputs.
    """
    if geometry_complexity not in ("simple", "moderate", "complex"):
        raise ValueError(
            "geometry_complexity must be simple/moderate/complex, got %r"
            % (geometry_complexity,)
        )
    if not isinstance(boundary_layer_resolution, bool):
        raise ValueError(
            "boundary_layer_resolution must be a bool, got %r"
            % (boundary_layer_resolution,)
        )
    if geometry_complexity == "simple":
        return "structured"
    if boundary_layer_resolution:
        return "hybrid"
    return "unstructured"


def quality_flags(skewness, orthogonality_deg, aspect_ratio, boundary_layer_cell=False):
    """Check cell quality against skewness, orthogonality, aspect ratio.

    General-cell limits: skewness <= 0.9, orthogonality angle >= 20
    deg, aspect ratio <= 10. Boundary-layer cells legitimately carry
    high aspect ratio, so boundary_layer_cell=True skips the aspect
    ratio check. Returns a dict with per-metric 'ok' flags and an
    overall 'pass' verdict. Raises ValueError when skewness is not in
    [0, 1], orthogonality_deg or aspect_ratio is not positive, or
    boundary_layer_cell is not a bool.
    """
    if not 0.0 <= skewness <= 1.0:
        raise ValueError("skewness must be in [0, 1], got %r" % (skewness,))
    if orthogonality_deg <= 0:
        raise ValueError(
            "orthogonality_deg must be > 0, got %r" % (orthogonality_deg,)
        )
    if aspect_ratio <= 0:
        raise ValueError("aspect_ratio must be > 0, got %r" % (aspect_ratio,))
    if not isinstance(boundary_layer_cell, bool):
        raise ValueError(
            "boundary_layer_cell must be a bool, got %r" % (boundary_layer_cell,)
        )
    skew_ok = skewness <= 0.9
    ortho_ok = orthogonality_deg >= 20.0
    aspect_ok = boundary_layer_cell or aspect_ratio <= 10.0
    return {
        "skewness_ok": skew_ok,
        "orthogonality_ok": ortho_ok,
        "aspect_ratio_ok": aspect_ok,
        "pass": skew_ok and ortho_ok and aspect_ok,
    }


def estimate_cell_count(lx, ly, lz, dx, dy, dz):
    """Estimate hexahedral cell count for a box domain.

    N = ceil(lx/dx) * ceil(ly/dy) * ceil(lz/dz). Raises ValueError
    when any dimension or spacing is not positive.
    """
    dims = (lx, ly, lz)
    spacings = (dx, dy, dz)
    for d, label in zip(dims, ("lx", "ly", "lz")):
        if d <= 0:
            raise ValueError("%s must be > 0, got %r" % (label, d))
    for s, label in zip(spacings, ("dx", "dy", "dz")):
        if s <= 0:
            raise ValueError("%s must be > 0, got %r" % (label, s))
    n = 1
    for d, s in zip(dims, spacings):
        n *= int(math.ceil(d / s))
    return n


def refinement_sizes(base_cell_size, levels, ratio=2.0):
    """Cell sizes across refinement levels: size_n = base / ratio^n.

    Returns a list of levels + 1 sizes starting at base_cell_size.
    Raises ValueError when base_cell_size is not positive, levels is
    negative, or ratio is not > 1.
    """
    if base_cell_size <= 0:
        raise ValueError(
            "base_cell_size must be > 0, got %r" % (base_cell_size,)
        )
    if levels < 0:
        raise ValueError("levels must be >= 0, got %r" % (levels,))
    if ratio <= 1.0:
        raise ValueError("ratio must be > 1, got %r" % (ratio,))
    return [base_cell_size / (ratio ** n) for n in range(levels + 1)]
