#!/usr/bin/env python3
"""Wing planform design logic (common knowledge, deterministic).

Pure stdlib functions for the reference geometry and spanwise loading
of a straight-tapered (trapezoidal) wing. All methods are documented in
the skill's Domain quick reference:

- Aspect ratio: AR = span**2 / area.
- Taper ratio: lambda = tip_chord / root_chord, 0 < lambda <= 1.
- Trapezoidal planform: root chord cr = 2*S/(b*(1+lambda)),
  tip chord ct = lambda*cr, mean geometric chord cbar = S/b.
- Local chord at span station eta = 2y/b: c(eta) = cr*(1 - (1-lambda)*eta).
- Mean aerodynamic chord: MAC = (2/3)*cr*(1+lambda+lambda**2)/(1+lambda).
- MAC spanwise station from the root: y_MAC = (b/6)*(1+2*lambda)/(1+lambda).
- Sweep reference conversion (chord fraction m from the leading edge):
  tan(Lambda_m) = tan(Lambda_LE) - 4*m*(1-lambda)/(AR*(1+lambda)), so
  tan(Lambda_to) = tan(Lambda_from) + 4*(from_ref - to_ref)*(1-lambda)/(AR*(1+lambda)).
- Schrenk spanwise loading approximation:
  l(eta) = CL*[2*S/(pi*b)*sqrt(1-eta**2) + c(eta)/2],
  local cl(eta) = l(eta)/c(eta). The loading integrates to CL*S.
- Washout (linear twist, nose-down at the tip): local angle of attack
  alpha_eff(eta) = alpha_root - washout_tip*eta, and the washout needed
  so the tip reaches its clmax no earlier than the root is
  epsilon = (tip_local_cl - tip_clmax)/a, clamped at zero.

NACA Report 824 (public domain, standards-map.yaml) supplies the section
data anchor for the clmax values used in the washout sizing. All
functions are deterministic, stdlib-only, offline. Invalid inputs raise
ValueError.
"""

import math


def aspect_ratio(span, area):
    """Aspect ratio AR = span**2 / area. Raises ValueError when span
    or area is not > 0."""
    if span <= 0:
        raise ValueError("span must be > 0, got %r" % (span,))
    if area <= 0:
        raise ValueError("area must be > 0, got %r" % (area,))
    return span * span / area


def taper_ratio(tip_chord, root_chord):
    """Taper ratio lambda = tip_chord / root_chord, 0 < lambda <= 1.
    Raises ValueError when either chord is not > 0 or the tip chord
    exceeds the root chord."""
    if root_chord <= 0:
        raise ValueError("root chord must be > 0, got %r" % (root_chord,))
    if tip_chord <= 0:
        raise ValueError("tip chord must be > 0, got %r" % (tip_chord,))
    if tip_chord > root_chord:
        raise ValueError(
            "tip chord %r must not exceed root chord %r (taper <= 1)"
            % (tip_chord, root_chord)
        )
    return tip_chord / root_chord


def _check_taper(taper):
    if taper <= 0 or taper > 1:
        raise ValueError("taper ratio must be in (0, 1], got %r" % (taper,))


def trapezoidal_chords(span, area, taper):
    """(root_chord, tip_chord, mean_geometric_chord) of a trapezoidal
    wing. Raises ValueError on invalid span, area, or taper."""
    if span <= 0:
        raise ValueError("span must be > 0, got %r" % (span,))
    if area <= 0:
        raise ValueError("area must be > 0, got %r" % (area,))
    _check_taper(taper)
    root = 2.0 * area / (span * (1.0 + taper))
    return root, taper * root, area / span


def chord_at_station(span, area, taper, eta):
    """Local chord c(eta) at spanwise fraction eta = 2y/b in [0, 1],
    eta = 0 at the root and eta = 1 at the tip."""
    root, _tip, _mgc = trapezoidal_chords(span, area, taper)
    if eta < 0 or eta > 1:
        raise ValueError("span station eta must be in [0, 1], got %r" % (eta,))
    return root * (1.0 - (1.0 - taper) * eta)


def mean_aerodynamic_chord(root_chord, taper):
    """Mean aerodynamic chord MAC = (2/3)*cr*(1+lambda+lambda**2)/(1+lambda)."""
    if root_chord <= 0:
        raise ValueError("root chord must be > 0, got %r" % (root_chord,))
    _check_taper(taper)
    return (2.0 / 3.0) * root_chord * (1.0 + taper + taper * taper) / (1.0 + taper)


def mac_span_station(span, taper):
    """Spanwise station of the MAC measured from the root,
    y_MAC = (b/6)*(1+2*lambda)/(1+lambda)."""
    if span <= 0:
        raise ValueError("span must be > 0, got %r" % (span,))
    _check_taper(taper)
    return (span / 6.0) * (1.0 + 2.0 * taper) / (1.0 + taper)


def sweep_convert(sweep_deg, from_ref, to_ref, span, area, taper):
    """Convert the sweep angle between chord-fraction reference lines.

    ref is the chord fraction measured back from the leading edge:
    0.0 = leading edge, 0.25 = quarter chord, 0.5 = mid chord,
    1.0 = trailing edge. Formula:
    tan(Lambda_to) = tan(Lambda_from) + 4*(from_ref - to_ref)*(1-lambda)/(AR*(1+lambda)).
    Sweep must lie in (-90, 90) degrees; refs in [0, 1]; from != to.
    """
    if not (-90.0 < sweep_deg < 90.0):
        raise ValueError(
            "sweep must be in (-90, 90) degrees, got %r" % (sweep_deg,)
        )
    if not (0.0 <= from_ref <= 1.0):
        raise ValueError("from_ref must be in [0, 1], got %r" % (from_ref,))
    if not (0.0 <= to_ref <= 1.0):
        raise ValueError("to_ref must be in [0, 1], got %r" % (to_ref,))
    if from_ref == to_ref:
        raise ValueError("from_ref and to_ref must differ, both %r" % (from_ref,))
    ar = aspect_ratio(span, area)
    _check_taper(taper)
    k = (1.0 - taper) / (ar * (1.0 + taper))
    tan_to = math.tan(math.radians(sweep_deg)) + 4.0 * (from_ref - to_ref) * k
    return math.degrees(math.atan(tan_to))


def schrenk_loading(span, area, taper, cl_wing, eta):
    """Schrenk spanwise loading at station eta in [0, 1].

    Returns (loading, local_cl): loading l(eta) in force per unit span
    per unit dynamic pressure, l = CL*[2*S/(pi*b)*sqrt(1-eta**2) + c(eta)/2],
    and local_cl = l(eta)/c(eta). The loading integrates to CL*S, so the
    approximation carries the exact total lift.
    """
    if span <= 0:
        raise ValueError("span must be > 0, got %r" % (span,))
    if area <= 0:
        raise ValueError("area must be > 0, got %r" % (area,))
    _check_taper(taper)
    if eta < 0 or eta > 1:
        raise ValueError("span station eta must be in [0, 1], got %r" % (eta,))
    c = chord_at_station(span, area, taper, eta)
    elliptic = 2.0 * area / (math.pi * span) * math.sqrt(1.0 - eta * eta)
    loading = cl_wing * (elliptic + 0.5 * c)
    return loading, loading / c


def linear_washout_angle(alpha_root_deg, washout_tip_deg, eta):
    """Local angle of attack with a linear washout (twist) schedule.

    alpha_eff(eta) = alpha_root - washout_tip*eta, washout_tip in degrees
    (positive twists the tip nose-down relative to the root).
    """
    if eta < 0 or eta > 1:
        raise ValueError("span station eta must be in [0, 1], got %r" % (eta,))
    return alpha_root_deg - washout_tip_deg * eta


def washout_required(root_clmax, tip_clmax, root_local_cl, tip_local_cl, section_slope):
    """Washout (degrees) needed so the tip reaches clmax no earlier than
    the root: epsilon = (tip_local_cl - tip_clmax)/a, clamped at zero.

    section_slope is the local lift curve slope per radian. Raises
    ValueError when clmax values or the slope are not > 0.
    """
    if root_clmax <= 0:
        raise ValueError("root clmax must be > 0, got %r" % (root_clmax,))
    if tip_clmax <= 0:
        raise ValueError("tip clmax must be > 0, got %r" % (tip_clmax,))
    if section_slope <= 0:
        raise ValueError("section slope must be > 0, got %r" % (section_slope,))
    excess = tip_local_cl - tip_clmax
    if excess <= 0:
        return 0.0
    return math.degrees(excess / section_slope)
