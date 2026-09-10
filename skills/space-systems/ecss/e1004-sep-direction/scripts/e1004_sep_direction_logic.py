#!/usr/bin/env python3
"""ECSS-E-ST-10-04C clause 9.2.2.5 directional solar particle flux
(paraphrase, not copy).

Common-knowledge summary (standards-map.yaml, ecss: gated false): a
solar particle event (SPE) streams outward along the interplanetary
magnetic field (IMF) line connecting its solar source region to the
observation point; that line is wound into a Parker spiral by solar
rotation, so an event's magnetic connection quality depends on how
closely its source heliolongitude matches the spiral's footpoint
offset for the event's solar wind speed. Anisotropy is strongest near
event onset and decays toward a quasi-isotropic diffusive state as
pitch-angle scattering randomizes arrival directions. Magnetospheric
entry is direction-dependent on a separate geometry: arrival close to
locally field-aligned reaches a point via the open-field-line polar
cusp with minimal impedance, while quasi-perpendicular arrival needs
the point's Stormer cutoff rigidity to be satisfied. This module
implements the spiral-angle/connection geometry, event-phase
classification, cone-angle geometry, anisotropy scaling of an
already-available omnidirectional-equivalent flux, and the
entry-channel/cutoff-check flagging; it does not compute the Stormer
cutoff rigidity itself or select/fit the omnidirectional SPE flux
model.
"""

import math

AU_KM = 1.496e8
SOLAR_SIDEREAL_ROTATION_PERIOD_S = 25.38 * 86400.0

ONSET_ANISOTROPIC_MAX_HR = 24.0
MIN_ANISOTROPY_FACTOR = 0.1
DEFAULT_CONNECTION_TOLERANCE_DEG = 20.0

FIELD_ALIGNED_CONE_ANGLE_MAX_DEG = 30.0
OBLIQUE_CONE_ANGLE_MAX_DEG = 60.0

FIELD_ALIGNED_POLAR_ACCESS = "field_aligned_polar_access"
OBLIQUE_TRANSITIONAL = "oblique_transitional"
QUASI_PERPENDICULAR_ACCESS = "quasi_perpendicular_access"

ANISOTROPIC_ONSET = "anisotropic_onset"
ISOTROPIC_DIFFUSIVE = "isotropic_diffusive"


def parker_spiral_angle_deg(solar_wind_speed_km_s):
    """Parker spiral angle (degrees) between the IMF line and the
    Sun-Earth radial direction at 1 AU, for a given solar wind speed.
    tan(psi) = Omega * r / V, Omega the Sun's sidereal rotation rate,
    r = 1 AU. Raises ValueError for a non-positive speed."""
    if solar_wind_speed_km_s <= 0:
        raise ValueError("solar_wind_speed_km_s must be > 0")
    omega_rad_s = 2.0 * math.pi / SOLAR_SIDEREAL_ROTATION_PERIOD_S
    tan_psi = (omega_rad_s * AU_KM) / solar_wind_speed_km_s
    return math.degrees(math.atan(tan_psi))


def classify_magnetic_connection(
    source_longitude_deg_w, solar_wind_speed_km_s, tolerance_deg=DEFAULT_CONNECTION_TOLERANCE_DEG
):
    """"well_connected" if the event source's heliolongitude (degrees
    west of central meridian) lies within tolerance_deg of the Parker
    spiral angle for solar_wind_speed_km_s, else "poorly_connected".
    Raises ValueError for a negative tolerance."""
    if tolerance_deg < 0:
        raise ValueError("tolerance_deg must be >= 0")
    spiral_angle_deg = parker_spiral_angle_deg(solar_wind_speed_km_s)
    if abs(source_longitude_deg_w - spiral_angle_deg) <= tolerance_deg:
        return "well_connected"
    return "poorly_connected"


def classify_arrival_phase(hours_since_onset):
    """ANISOTROPIC_ONSET while hours_since_onset is inside the onset
    window (< ONSET_ANISOTROPIC_MAX_HR), otherwise ISOTROPIC_DIFFUSIVE.
    Raises ValueError for a negative elapsed time."""
    if hours_since_onset < 0:
        raise ValueError("hours_since_onset must be >= 0")
    if hours_since_onset < ONSET_ANISOTROPIC_MAX_HR:
        return ANISOTROPIC_ONSET
    return ISOTROPIC_DIFFUSIVE


def cone_angle_between(direction_a_deg, direction_b_deg):
    """Angular separation (degrees, 0-180) between two directions given
    in the same angle convention, wrapping each to [0, 360) first."""
    a = direction_a_deg % 360.0
    b = direction_b_deg % 360.0
    diff = abs(a - b)
    return diff if diff <= 180.0 else 360.0 - diff


def anisotropy_factor(cone_angle_deg, phase, peak_anisotropy_ratio=None):
    """Scale factor applied to an omnidirectional-equivalent flux for a
    given cone_angle_deg (0 = field-aligned) and event phase. Returns
    1.0 for ISOTROPIC_DIFFUSIVE. For ANISOTROPIC_ONSET, peaks at
    peak_anisotropy_ratio when cone_angle_deg is 0 and falls off with
    cos(cone_angle_deg), floored at MIN_ANISOTROPY_FACTOR. Raises
    ValueError for cone_angle_deg outside [0, 180], an unrecognized
    phase, or (for ANISOTROPIC_ONSET) a missing or sub-1.0
    peak_anisotropy_ratio."""
    if not 0.0 <= cone_angle_deg <= 180.0:
        raise ValueError("cone_angle_deg must be within [0, 180]")
    if phase == ISOTROPIC_DIFFUSIVE:
        return 1.0
    if phase != ANISOTROPIC_ONSET:
        raise ValueError("unrecognized arrival phase %r" % (phase,))
    if peak_anisotropy_ratio is None or peak_anisotropy_ratio < 1.0:
        raise ValueError("peak_anisotropy_ratio must be >= 1.0 for anisotropic_onset")
    factor = 1.0 + (peak_anisotropy_ratio - 1.0) * math.cos(math.radians(cone_angle_deg))
    return max(MIN_ANISOTROPY_FACTOR, factor)


def directional_flux(
    omni_equivalent_flux, cone_angle_deg, hours_since_onset, peak_anisotropy_ratio=None
):
    """Directional flux for a look/arrival direction at cone_angle_deg
    from the field-aligned streaming direction, hours_since_onset into
    the event. Classifies the arrival phase, applies anisotropy_factor,
    and multiplies omni_equivalent_flux by it. Raises ValueError for a
    negative omni_equivalent_flux (elapsed-time and cone-angle
    validation is delegated to classify_arrival_phase and
    anisotropy_factor)."""
    if omni_equivalent_flux < 0:
        raise ValueError("omni_equivalent_flux must be >= 0")
    phase = classify_arrival_phase(hours_since_onset)
    factor = anisotropy_factor(cone_angle_deg, phase, peak_anisotropy_ratio)
    return omni_equivalent_flux * factor


def entry_channel_for_cone_angle(cone_angle_deg):
    """Magnetospheric entry channel for a cone_angle_deg between an
    arrival direction and the local geomagnetic field line:
    FIELD_ALIGNED_POLAR_ACCESS (<= FIELD_ALIGNED_CONE_ANGLE_MAX_DEG),
    OBLIQUE_TRANSITIONAL (<= OBLIQUE_CONE_ANGLE_MAX_DEG), otherwise
    QUASI_PERPENDICULAR_ACCESS. Raises ValueError for cone_angle_deg
    outside [0, 180]."""
    if not 0.0 <= cone_angle_deg <= 180.0:
        raise ValueError("cone_angle_deg must be within [0, 180]")
    if cone_angle_deg <= FIELD_ALIGNED_CONE_ANGLE_MAX_DEG:
        return FIELD_ALIGNED_POLAR_ACCESS
    if cone_angle_deg <= OBLIQUE_CONE_ANGLE_MAX_DEG:
        return OBLIQUE_TRANSITIONAL
    return QUASI_PERPENDICULAR_ACCESS


def requires_stormer_cutoff_check(entry_channel):
    """True unless entry_channel is FIELD_ALIGNED_POLAR_ACCESS (open
    field lines, no cutoff-rigidity gate). Raises ValueError for an
    unrecognized entry_channel."""
    if entry_channel == FIELD_ALIGNED_POLAR_ACCESS:
        return False
    if entry_channel in (OBLIQUE_TRANSITIONAL, QUASI_PERPENDICULAR_ACCESS):
        return True
    raise ValueError("unrecognized entry channel %r" % (entry_channel,))


def directional_case_violations(case):
    """Violation list (empty if compliant) for one directional SEP
    case. case: {"case_id": str, "hours_since_onset": float,
    "cone_angle_deg": float | None, "peak_anisotropy_ratio": float |
    None, "stormer_cutoff_checked": bool}. Flags a missing cone angle
    or peak anisotropy ratio while the case is in the anisotropic-onset
    phase, and flags a missing Stormer cutoff-rigidity check when the
    case's entry channel requires one. Does not mutate case."""
    case_id = case["case_id"]
    violations = []
    phase = classify_arrival_phase(case["hours_since_onset"])
    cone_angle_deg = case.get("cone_angle_deg")
    peak_anisotropy_ratio = case.get("peak_anisotropy_ratio")

    if phase == ANISOTROPIC_ONSET:
        if cone_angle_deg is None:
            violations.append(
                {"issue": "missing_cone_angle_for_anisotropic_case", "case": case_id}
            )
        if peak_anisotropy_ratio is None:
            violations.append(
                {"issue": "missing_peak_anisotropy_ratio", "case": case_id}
            )

    if cone_angle_deg is not None:
        entry_channel = entry_channel_for_cone_angle(cone_angle_deg)
        if requires_stormer_cutoff_check(entry_channel) and not case.get(
            "stormer_cutoff_checked"
        ):
            violations.append(
                {
                    "issue": "missing_stormer_cutoff_check",
                    "case": case_id,
                    "entry_channel": entry_channel,
                }
            )

    return violations


def is_directional_compliant(violations):
    """True when a directional_case_violations() result is empty --
    the case satisfies clause 9.2.2.5 for this assessment."""
    return len(violations) == 0
