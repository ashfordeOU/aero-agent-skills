#!/usr/bin/env python3
"""Wave drag and Whitcomb area rule logic (paraphrase, offline, stdlib).

Common-knowledge summary (standards-map.yaml, naca-tr-824: public
domain): at transonic speeds the zero-lift wave drag of a wing-body
combination depends mainly on the streamwise distribution of the total
cross-sectional area (fuselage plus wing and nacelle contributions),
not on the details of the individual components. That is Whitcomb's
area rule (NACA Report 1273, 1952, US government work, summary only):
the fuselage is pinched where the wing adds area so the total
distribution stays smooth, the classic coke-bottle waist.

The minimum-wave-drag body of revolution for a given length and volume
is the Sears-Haack body (Haack 1941, Sears 1947), with radius
distribution r(x) = r_max * (4 * (x / L) * (1 - x / L))^(3/4) over
0 <= x <= L, volume V = (3 * pi^2 / 16) * r_max^2 * L, and zero-lift
wave drag area D/q = (9 * pi / 2) * (A_max / L)^2, with A_max =
pi * r_max^2 the maximum cross-sectional area (drag-area form used in
Raymer, Aircraft Design; algebraically identical to the volume form
D/q = (128 / pi) * (V / L^3)^2). The wave drag coefficient based on
A_max is C_Dw = (9 * pi / 2) * (A_max / L^2).

Wave drag is negligible below the critical Mach number and rises
steeply past the drag-divergence Mach number M_DD, which sits roughly
0.05 to 0.08 above M_cr for typical sections. The rise above M_DD is
commonly modeled as parabolic, Delta C_Dw = k * (M - M_DD)^2 with an
empirical configuration-dependent constant k.
"""

import math

DRAG_DIVERGENCE_MARGIN = 0.065  # typical M_DD - M_cr band is 0.05-0.08


def _check_length(length):
    if not (length > 0.0):
        raise ValueError("body length must be positive, got %r" % (length,))


def _check_r_max(r_max):
    if not (r_max > 0.0):
        raise ValueError("maximum radius must be positive, got %r" % (r_max,))


def sears_haack_radius(x, length, r_max):
    """Sears-Haack body radius at streamwise station x in [0, length].

    r(x) = r_max * (4 * (x / L) * (1 - x / L))^(3/4). Zero at both
    ends, r_max at the midpoint.
    """
    _check_length(length)
    _check_r_max(r_max)
    if not (0.0 <= x <= length):
        raise ValueError("station x must be in [0, length], got %r" % (x,))
    t = 4.0 * (x / length) * (1.0 - x / length)
    return r_max * t ** 0.75


def sears_haack_area(x, length, r_max):
    """Cross-sectional area pi * r(x)^2 of the Sears-Haack body at x."""
    r = sears_haack_radius(x, length, r_max)
    return math.pi * r * r


def sears_haack_volume(length, r_max):
    """Volume of the Sears-Haack body: (3 * pi^2 / 16) * r_max^2 * L."""
    _check_length(length)
    _check_r_max(r_max)
    return (3.0 * math.pi * math.pi / 16.0) * r_max * r_max * length


def sears_haack_wave_drag_area(length, r_max):
    """Zero-lift wave drag area D/q of the Sears-Haack body.

    (9 * pi / 2) * (A_max / L)^2 with A_max = pi * r_max^2. Multiply
    by the dynamic pressure q to get the wave drag force.
    """
    _check_length(length)
    _check_r_max(r_max)
    a_max = math.pi * r_max * r_max
    return (9.0 * math.pi / 2.0) * (a_max / length) ** 2


def sears_haack_wave_drag_coef(length, r_max):
    """Wave drag coefficient based on maximum cross-sectional area.

    C_Dw = (9 * pi / 2) * (A_max / L^2), the drag area divided by
    A_max. A slender body (large length to diameter ratio) has a small
    coefficient; a fineness ratio of 10 gives about 0.11.
    """
    _check_length(length)
    _check_r_max(r_max)
    a_max = math.pi * r_max * r_max
    return (9.0 * math.pi / 2.0) * (a_max / (length * length))


def wave_drag_force(q_inf, length, r_max):
    """Wave drag force D = q_inf * (D/q) of the Sears-Haack body."""
    if not (q_inf >= 0.0):
        raise ValueError("dynamic pressure must be non-negative, got %r" % (q_inf,))
    return q_inf * sears_haack_wave_drag_area(length, r_max)


def area_rule_fuselage_area(target_area, wing_area):
    """Fuselage cross-sectional area needed at a station (area rule).

    The total area at a station is the fuselage area plus the wing (or
    nacelle) contribution. To keep the total distribution on the
    smooth target, the fuselage is pinched to target_area minus
    wing_area. Raises when the wing contribution already exceeds the
    target: the pinch would need a negative fuselage area.
    """
    if not (target_area > 0.0):
        raise ValueError("target total area must be positive, got %r" % (target_area,))
    if not (0.0 <= wing_area < target_area):
        raise ValueError(
            "wing area must be in [0, target), got %r with target %r"
            % (wing_area, target_area)
        )
    return target_area - wing_area


def area_rule_deviation(total_areas, target_areas):
    """RMS deviation of a total area distribution from its target.

    Quantifies how far the actual streamwise area distribution sits
    from the ideal smooth (Sears-Haack-like) target. Zero for an exact
    match; larger values mean a rougher equivalent body and higher wave
    drag at transonic speeds.
    """
    if not isinstance(total_areas, (list, tuple)) or not isinstance(
        target_areas, (list, tuple)
    ):
        raise ValueError("area distributions must be lists or tuples")
    if len(total_areas) == 0:
        raise ValueError("area distributions must not be empty")
    if len(total_areas) != len(target_areas):
        raise ValueError(
            "distributions must have equal length, got %d and %d"
            % (len(total_areas), len(target_areas))
        )
    for value in list(total_areas) + list(target_areas):
        if not (value >= 0.0):
            raise ValueError("area values must be non-negative, got %r" % (value,))
    n = len(total_areas)
    squares = sum(
        (total_areas[i] - target_areas[i]) ** 2 for i in range(n)
    )
    return math.sqrt(squares / n)


def drag_divergence_mach(critical_mach, margin=DRAG_DIVERGENCE_MARGIN):
    """Drag-divergence Mach number estimate: M_cr + margin.

    M_DD sits roughly 0.05 to 0.08 above the critical Mach for typical
    sections; the default margin is 0.065. Raises when the result
    reaches 1: the divergence point would be supersonic and the
    transonic estimate no longer applies.
    """
    if not (0.0 < critical_mach < 1.0):
        raise ValueError("critical Mach must be in (0, 1), got %r" % (critical_mach,))
    if not (0.0 <= margin <= 0.1):
        raise ValueError("margin must be in [0, 0.1], got %r" % (margin,))
    m_dd = critical_mach + margin
    if m_dd >= 1.0:
        raise ValueError(
            "drag-divergence Mach %r reaches 1; the transonic estimate "
            "does not apply there" % (m_dd,)
        )
    return m_dd


def wave_drag_rise_coef(mach, m_dd, k=20.0):
    """Wave drag rise above the drag-divergence Mach number.

    Parabolic approximation Delta C_Dw = k * (M - M_DD)^2 for M > M_DD,
    zero at and below the divergence Mach. k is an empirical,
    configuration-dependent constant (commonly 10 to 40 for transport
    configurations; default 20).
    """
    if not (mach >= 0.0 and mach < 1.0):
        raise ValueError("Mach number must be in [0, 1), got %r" % (mach,))
    if not (0.0 < m_dd < 1.0):
        raise ValueError("drag-divergence Mach must be in (0, 1), got %r" % (m_dd,))
    if not (k > 0.0):
        raise ValueError("parabolic constant k must be positive, got %r" % (k,))
    if mach <= m_dd:
        return 0.0
    return k * (mach - m_dd) ** 2
