#!/usr/bin/env python3
"""Wing planform sizing logic (paraphrase, not copy).

Common-knowledge summary (standards-map.yaml, far-25/cs-25: gated
false): the wing planform is the geometry seen in plan view. Given the
design point from the sizing loop, the planform is fixed by a small
set of numbers: the reference wing area S, the aspect ratio AR = b^2/S
with span b, the taper ratio lambda = c_tip / c_root, and the sweep
angle. The wing area follows from the wing loading W/S and the takeoff
gross weight W as S = W / (W/S); the span follows from the aspect
ratio as b = sqrt(AR * S); the root chord is c_root = 2 * S /
(b * (1 + lambda)); the mean aerodynamic chord (MAC) is MAC = (4 * S /
(3 * b)) * (1 + lambda + lambda^2) / (1 + lambda)^2, located at the
spanwise station y_mac = (b / 6) * (1 + 2 * lambda) / (1 + lambda);
and the sweep angle is selected so the section-normal Mach number
M * cos(Lambda) stays at or below the section critical Mach number,
which gives Lambda = arccos(M_crit_section / M_cruise) as the minimum
quarter-chord sweep for a target cruise Mach.

Units are SI throughout: forces in N, areas in m^2, wing loading in
N/m^2, spans and chords in m, Mach numbers unitless, sweep in degrees.
Invalid inputs raise ValueError throughout.
"""

import math

G = 9.80665  # standard gravity, m/s^2 (SI, used for weight conversions)


def _require_positive(value, name):
    """Raise ValueError unless value is a positive finite number."""
    if not isinstance(value, (int, float)):
        raise ValueError("%s must be a number, got %r" % (name, value))
    if value <= 0:
        raise ValueError("%s must be positive, got %r" % (name, value))


def _require_taper(taper_ratio):
    """Raise ValueError unless taper ratio lies in the conventional (0, 1] range."""
    if not isinstance(taper_ratio, (int, float)):
        raise ValueError("taper ratio must be a number, got %r" % (taper_ratio,))
    if not (0 < taper_ratio <= 1):
        raise ValueError(
            "taper ratio must be in (0, 1], got %r" % (taper_ratio,)
        )


def wing_area_from_wing_loading(weight_N, wing_loading_Npm2):
    """Reference wing area S from the takeoff gross weight and wing loading.

    S = W / (W/S), with W in N and W/S in N/m^2. Anchor: W = 480000 N
    and W/S = 6000 N/m^2 give S = 480000 / 6000 = 80.0 m^2.

    Raises ValueError if either input is not positive.
    """
    _require_positive(weight_N, "takeoff gross weight W")
    _require_positive(wing_loading_Npm2, "wing loading W/S")
    return weight_N / wing_loading_Npm2


def wing_loading_from_area(weight_N, area_m2):
    """Wing loading W/S from the takeoff gross weight and the wing area.

    W/S = W / S, with W in N and S in m^2. Anchor: W = 480000 N and
    S = 80.0 m^2 give W/S = 480000 / 80 = 6000.0 N/m^2.

    Raises ValueError if either input is not positive.
    """
    _require_positive(weight_N, "takeoff gross weight W")
    _require_positive(area_m2, "wing area S")
    return weight_N / area_m2


def span_from_aspect_ratio(area_m2, aspect_ratio):
    """Wing span b from the wing area and the aspect ratio.

    b = sqrt(AR * S), with S in m^2 and AR unitless. Anchor:
    S = 80.0 m^2 and AR = 9 give b = sqrt(720) = 26.8328 m.

    Raises ValueError if either input is not positive.
    """
    _require_positive(area_m2, "wing area S")
    _require_positive(aspect_ratio, "aspect ratio AR")
    return math.sqrt(aspect_ratio * area_m2)


def aspect_ratio_from_span(span_m, area_m2):
    """Aspect ratio AR from the span and the wing area.

    AR = b^2 / S, with b in m and S in m^2. Anchor: b = 26.8328 m and
    S = 80.0 m^2 give AR = 720 / 80 = 9.0.

    Raises ValueError if either input is not positive.
    """
    _require_positive(span_m, "wing span b")
    _require_positive(area_m2, "wing area S")
    return span_m * span_m / area_m2


def taper_ratio_from_chords(root_chord_m, tip_chord_m):
    """Taper ratio lambda from the root and tip chord.

    lambda = c_tip / c_root, with both chords in m. Conventional
    planforms taper toward the tip so 0 < c_tip <= c_root. Anchor:
    c_root = 5.0 m and c_tip = 1.5 m give lambda = 1.5 / 5.0 = 0.3.

    Raises ValueError if either chord is not positive or the tip chord
    exceeds the root chord (reverse taper).
    """
    _require_positive(root_chord_m, "root chord c_root")
    _require_positive(tip_chord_m, "tip chord c_tip")
    if tip_chord_m > root_chord_m:
        raise ValueError(
            "tip chord %.6g m exceeds root chord %.6g m; conventional "
            "planforms taper toward the tip" % (tip_chord_m, root_chord_m)
        )
    return tip_chord_m / root_chord_m


def root_chord_from_taper(area_m2, span_m, taper_ratio):
    """Root chord c_root from the area, span, and taper ratio.

    c_root = 2 * S / (b * (1 + lambda)), with S in m^2 and b in m.
    Anchor: S = 80.0 m^2, b = 26.8328 m, lambda = 0.3 give
    c_root = 160 / (26.8328 * 1.3) = 4.5868 m.

    Raises ValueError if area or span is not positive or the taper
    ratio is outside (0, 1].
    """
    _require_positive(area_m2, "wing area S")
    _require_positive(span_m, "wing span b")
    _require_taper(taper_ratio)
    return 2.0 * area_m2 / (span_m * (1.0 + taper_ratio))


def tip_chord_from_taper(root_chord_m, taper_ratio):
    """Tip chord c_tip from the root chord and the taper ratio.

    c_tip = lambda * c_root, with c_root in m. Anchor: c_root = 4.5868 m
    and lambda = 0.3 give c_tip = 0.3 * 4.5868 = 1.3760 m.

    Raises ValueError if the root chord is not positive or the taper
    ratio is outside (0, 1].
    """
    _require_positive(root_chord_m, "root chord c_root")
    _require_taper(taper_ratio)
    return taper_ratio * root_chord_m


def mean_aerodynamic_chord(area_m2, span_m, taper_ratio):
    """Mean aerodynamic chord MAC from the area, span, and taper ratio.

    MAC = (4 * S / (3 * b)) * (1 + lambda + lambda^2) / (1 + lambda)^2,
    with S in m^2 and b in m. Anchor: S = 80.0 m^2, b = 26.8328 m,
    lambda = 0.3 give MAC = 3.2696 m (about 71 percent of the root
    chord, as expected for a moderate taper).

    Raises ValueError if area or span is not positive or the taper
    ratio is outside (0, 1].
    """
    _require_positive(area_m2, "wing area S")
    _require_positive(span_m, "wing span b")
    _require_taper(taper_ratio)
    lam = taper_ratio
    factor = (1.0 + lam + lam * lam) / ((1.0 + lam) * (1.0 + lam))
    return (4.0 * area_m2 / (3.0 * span_m)) * factor


def mac_spanwise_station(span_m, taper_ratio):
    """Spanwise station y_mac of the MAC from the span and taper ratio.

    y_mac = (b / 6) * (1 + 2 * lambda) / (1 + lambda), measured from
    the root, with b in m. Anchor: b = 26.8328 m and lambda = 0.3 give
    y_mac = (26.8328 / 6) * (1.6 / 1.3) = 5.5042 m.

    Raises ValueError if the span is not positive or the taper ratio
    is outside (0, 1].
    """
    _require_positive(span_m, "wing span b")
    _require_taper(taper_ratio)
    return (span_m / 6.0) * (1.0 + 2.0 * taper_ratio) / (1.0 + taper_ratio)


def sweep_angle_from_cruise_mach(cruise_mach, section_crit_mach):
    """Minimum quarter-chord sweep angle (degrees) for a target cruise Mach.

    The section sees the Mach component normal to the isobars,
    M_n = M_cruise * cos(Lambda). Keeping M_n at or below the section
    critical Mach number gives the minimum sweep
    Lambda = arccos(M_crit_section / M_cruise). When the section
    critical Mach already meets or exceeds the cruise Mach, no sweep is
    needed and 0.0 is returned. Anchor: M_cruise = 0.8 and
    M_crit_section = 0.7 give Lambda = arccos(0.875) = 28.96 degrees,
    the classic transonic transport result.

    Raises ValueError if either Mach number is outside (0, 1).
    """
    if not (0 < cruise_mach < 1):
        raise ValueError(
            "cruise Mach must be in (0, 1), got %r" % (cruise_mach,)
        )
    if not (0 < section_crit_mach < 1):
        raise ValueError(
            "section critical Mach must be in (0, 1), got %r" % (section_crit_mach,)
        )
    if section_crit_mach >= cruise_mach:
        return 0.0
    return math.degrees(math.acos(section_crit_mach / cruise_mach))


def mach_normal_component(cruise_mach, sweep_deg):
    """Mach number normal to the quarter-chord line, M_n = M * cos(Lambda).

    Anchor: M_cruise = 0.8 and Lambda = 28.96 degrees give
    M_n = 0.8 * cos(28.96 deg) = 0.7, consistent with the sweep
    selection in sweep_angle_from_cruise_mach.

    Raises ValueError if the Mach number is outside (0, 1) or the
    sweep angle is outside [0, 90] degrees.
    """
    if not (0 < cruise_mach < 1):
        raise ValueError(
            "cruise Mach must be in (0, 1), got %r" % (cruise_mach,)
        )
    if not (0 <= sweep_deg <= 90):
        raise ValueError(
            "sweep angle must be in [0, 90] degrees, got %r" % (sweep_deg,)
        )
    return cruise_mach * math.cos(math.radians(sweep_deg))


def planform_geometry(area_m2, aspect_ratio, taper_ratio):
    """Full planform geometry summary from area, aspect ratio, and taper.

    Returns a dict with span, root_chord, tip_chord, mac, and
    mac_station computed from the sizing relations above. Anchor:
    S = 80.0 m^2, AR = 9, lambda = 0.3 give span 26.8328 m,
    root chord 4.5868 m, tip chord 1.3760 m, MAC 3.2696 m at the
    station 5.5042 m outboard of the root.

    Raises ValueError if any input is invalid (see the component
    functions).
    """
    _require_positive(area_m2, "wing area S")
    _require_positive(aspect_ratio, "aspect ratio AR")
    _require_taper(taper_ratio)
    span = span_from_aspect_ratio(area_m2, aspect_ratio)
    root_chord = root_chord_from_taper(area_m2, span, taper_ratio)
    tip_chord = tip_chord_from_taper(root_chord, taper_ratio)
    mac = mean_aerodynamic_chord(area_m2, span, taper_ratio)
    mac_station = mac_spanwise_station(span, taper_ratio)
    return {
        "span": span,
        "root_chord": root_chord,
        "tip_chord": tip_chord,
        "mac": mac,
        "mac_station": mac_station,
    }
