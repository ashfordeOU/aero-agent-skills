"""Winglet design sizing logic for induced-drag reduction (stdlib only).

Preliminary tip-device trade model for a fixed-wing aircraft: from the
reference wing geometry (span, area, base span efficiency) and the
winglet height and cant, estimate the effective aspect ratio gain, the
improved span efficiency, the induced-drag factor and coefficient at a
reference lift coefficient, and the root bending moment penalty from
the added winglet load.  The e_eff improvement model and the bending
penalty scaling are documented conceptual approximations for a
preliminary trade; a real winglet design needs a VLM/CFD pass and a
structural FEM pass.

All units SI: span and area in m and m^2, angles in degrees.
"""

import math

# Documented typicals (module constants).
K_HEIGHT = 0.8        # fraction of winglet height acting as span extension, typical 0.7-0.9
CANT_LOSS = 0.6       # documented cosine-loss weighting typical; the implemented
                      # cant_factor uses cos(cant) directly so a vertical winglet
                      # keeps full effect and a flat tip loses it
RHO_REF = 1.225       # reference density kg/m^3, optional dimensional bending check
V_REF = 100.0         # reference speed m/s, optional dimensional bending check

_HEIGHT_MIN = 0.0     # direct-function height fraction bounds
_HEIGHT_MAX = 0.6
_CANT_MIN = -90.0     # cant bounds, deg from vertical
_CANT_MAX = 90.0
_SIZE_LO = 0.01       # sizing bisection bracket on height fraction
_SIZE_HI = 0.5
_TOL_REDUCTION = 0.1  # sizing tolerance, percent of drag reduction
_MAX_ITER = 200


def _check_span_area(span_m, area_m2):
    """Raise ValueError unless the reference span and area are positive."""
    if span_m <= 0:
        raise ValueError("span_m must be positive")
    if area_m2 <= 0:
        raise ValueError("area_m2 must be positive")


def _check_height_frac(height_frac):
    """Raise ValueError unless the height fraction lies in [0, 0.6]."""
    if not _HEIGHT_MIN <= height_frac <= _HEIGHT_MAX:
        raise ValueError("height_frac must lie in [0, 0.6]")


def _check_cant(cant_deg):
    """Raise ValueError unless the cant angle lies in [-90, 90] degrees."""
    if not _CANT_MIN <= cant_deg <= _CANT_MAX:
        raise ValueError("cant_deg must lie in [-90, 90]")


def _check_e_base(e_base):
    """Raise ValueError unless the base span efficiency lies in (0, 1]."""
    if not 0.0 < e_base <= 1.0:
        raise ValueError("e_base must lie in (0, 1]")


def _check_cl(cl_ref):
    """Raise ValueError unless the reference lift coefficient is positive."""
    if cl_ref <= 0:
        raise ValueError("cl_ref must be positive")


def _check_taper(taper_frac):
    """Raise ValueError unless the winglet taper ratio lies in (0, 1]."""
    if not 0.0 < taper_frac <= 1.0:
        raise ValueError("taper_frac must lie in (0, 1]")


def validate_inputs(span_m, area_m2, e_base, cl_ref, height_frac, cant_deg,
                    taper_frac=0.35):
    """Validate the full winglet geometry input set; raise ValueError first hit."""
    _check_span_area(span_m, area_m2)
    _check_e_base(e_base)
    _check_cl(cl_ref)
    _check_height_frac(height_frac)
    _check_cant(cant_deg)
    _check_taper(taper_frac)


def effective_span_extension(height_frac):
    """Return the effective span extension as a fraction of semi-span."""
    _check_height_frac(height_frac)
    return K_HEIGHT * height_frac


def cant_factor(cant_deg):
    """Return the cant factor cos(cant); 1.0 vertical, 0.0 flat tip."""
    _check_cant(cant_deg)
    return math.cos(math.radians(cant_deg))


def _span_ratio(height_frac, cant_deg):
    """Return b_eff/b = 1 + 2*cant_factor*K_HEIGHT*height_frac."""
    return 1.0 + 2.0 * cant_factor(cant_deg) * effective_span_extension(height_frac)


def ar_eff(span_m, area_m2, height_frac, cant_deg):
    """Return the effective aspect ratio with both winglet tips fitted."""
    _check_span_area(span_m, area_m2)
    b_eff = span_m * _span_ratio(height_frac, cant_deg)
    return b_eff * b_eff / area_m2


def e_winglet(e_base, height_frac, cant_deg):
    """Return the improved span efficiency e_eff with the winglet fitted.

    Documented approximation: e_eff = 1 - (1 - e_base) / (AR_eff / AR),
    where AR_eff/AR = (1 + 2*cant_factor*K_HEIGHT*height_frac)^2 from the
    extended-span effective aspect ratio.
    """
    _check_e_base(e_base)
    ratio = _span_ratio(height_frac, cant_deg)
    return 1.0 - (1.0 - e_base) / (ratio * ratio)


def induced_drag_factor(e, ar):
    """Return the induced-drag factor k = 1/(pi*e*ar)."""
    if not 0.0 < e <= 1.0:
        raise ValueError("e must lie in (0, 1]")
    if ar <= 0:
        raise ValueError("ar must be positive")
    return 1.0 / (math.pi * e * ar)


def cd_i(cl, e, ar):
    """Return the induced-drag coefficient cd_i = cl^2 / (pi*e*ar)."""
    _check_cl(cl)
    return cl * cl * induced_drag_factor(e, ar)


def drag_reduction_pct(cl_ref, base, wl):
    """Return the percent induced-drag reduction of the winglet case.

    base and wl are induced-drag factors; the lift coefficient cancels
    but is kept as the reference check point.
    """
    _check_cl(cl_ref)
    if base <= 0 or wl <= 0:
        raise ValueError("drag factors must be positive")
    cd_base = cl_ref * cl_ref * base
    cd_wl = cl_ref * cl_ref * wl
    return 100.0 * (1.0 - cd_wl / cd_base)


def root_bending_penalty_pct(height_frac, cant_deg):
    """Return the approximate root bending moment penalty in percent.

    Approximate scaling: the winglet load acts near the tip, so the
    added root moment grows roughly with the height fraction.
    """
    cf = cant_factor(cant_deg)
    _check_height_frac(height_frac)
    return cf * K_HEIGHT * height_frac * 100.0 * (1.0 + 0.5 * height_frac)


def _reduction_at(height_frac, span_m, area_m2, e_base, cl_ref, cant_deg):
    """Return the achieved percent drag reduction at a height fraction."""
    ar_wl = ar_eff(span_m, area_m2, height_frac, cant_deg)
    e_wl = e_winglet(e_base, height_frac, cant_deg)
    ar_base = span_m * span_m / area_m2
    return drag_reduction_pct(
        cl_ref,
        induced_drag_factor(e_base, ar_base),
        induced_drag_factor(e_wl, ar_wl),
    )


def size_winglet(span_m, area_m2, e_base, target_reduction_pct, cl_ref,
                 cant_deg=0.0):
    """Size the winglet height fraction to a target drag reduction.

    Bisection on height_frac in [0.01, 0.5] to a 0.1 pct reduction
    tolerance.  Returns the height fraction, physical height (height
    fraction times the semi-span local reference), effective aspect
    ratio, span efficiency, induced-drag coefficient, achieved
    reduction percent, and root bending penalty percent.
    """
    _check_span_area(span_m, area_m2)
    _check_e_base(e_base)
    _check_cl(cl_ref)
    _check_cant(cant_deg)
    if not 0.0 < target_reduction_pct < 100.0:
        raise ValueError("target_reduction_pct must lie in (0, 100)")
    if _reduction_at(_SIZE_HI, span_m, area_m2, e_base, cl_ref, cant_deg) <= target_reduction_pct:
        raise ValueError("target_reduction_pct exceeds the maximum achievable at the 0.5 height cap")

    lo, hi = _SIZE_LO, _SIZE_HI
    solved = lo
    for _ in range(_MAX_ITER):
        mid = 0.5 * (lo + hi)
        red = _reduction_at(mid, span_m, area_m2, e_base, cl_ref, cant_deg)
        if abs(red - target_reduction_pct) <= _TOL_REDUCTION:
            solved = mid
            break
        if red < target_reduction_pct:
            lo = mid
        else:
            hi = mid
        solved = mid
    red_solved = _reduction_at(solved, span_m, area_m2, e_base, cl_ref, cant_deg)
    ar_wl = ar_eff(span_m, area_m2, solved, cant_deg)
    e_wl = e_winglet(e_base, solved, cant_deg)
    return {
        "height_frac": solved,
        "height_m": solved * 0.5 * span_m,
        "ar_eff": ar_wl,
        "e_eff": e_wl,
        "cd_i": cd_i(cl_ref, e_wl, ar_wl),
        "reduction_pct": red_solved,
        "bending_penalty_pct": root_bending_penalty_pct(solved, cant_deg),
    }
