"""Visual inspection (VT) math for aerospace NDT.

Deterministic, offline, stdlib-only helpers for direct and assisted
visual inspection: borescope aperture ratio that sets light gathering
and image brightness, eye resolution limit and the magnification needed
to resolve a target indication size at a given viewing distance,
illuminance from lamp intensity by the inverse-square law and the
reverse conversions, lux to foot-candle conversion, field of view and
the number of scan positions for full surface coverage with overlap,
and the acceptance verdict when a measured surface indication is
compared with the acceptance criteria. All units are SI: aperture
diameter, working distance, resolvable size, and indication length in
meters, luminous intensity in candela, illuminance in lux, field of
view in meters, area in m2.

Contract exercised by scripts/test_visual_inspection.py.
"""

import math

# Normal visual acuity limit: 1 arcminute, the smallest angle the
# average eye resolves, in radians. An inspector resolving a detail at
# the 250 mm near point sees features of about 72.7 micrometers.
EYE_ACUITY_ARCMIN = 1.0
ARCMIN_RAD = math.radians(EYE_ACUITY_ARCMIN)
LUX_PER_FOOT_CANDLE = 10.76391  # 1 foot-candle = 10.76391 lux


def aperture_ratio(aperture_diameter, working_distance):
    """Return the borescope aperture ratio A = D / d.

    D is the objective aperture diameter in meters and d the working
    distance in meters. The aperture ratio sets the light-gathering
    power of the optic: a larger ratio admits more light and gives a
    brighter image, which matters when the illumination falls off with
    distance. A 6 mm objective at a 100 mm working distance gives
    A = 0.06, a common fast borescope optic.

    Raises ValueError for a non-positive aperture diameter or working
    distance.
    """
    if aperture_diameter <= 0:
        raise ValueError(
            "aperture diameter must be > 0, got %r" % (aperture_diameter,)
        )
    if working_distance <= 0:
        raise ValueError(
            "working distance must be > 0, got %r" % (working_distance,)
        )
    return aperture_diameter / working_distance


def eye_resolvable_size(viewing_distance, eye_angle_arcmin=EYE_ACUITY_ARCMIN):
    """Return the smallest detail the unaided eye resolves, in meters.

    s = d * tan(theta), with d the viewing distance in meters and theta
    the angular resolution limit. At the standard 1 arcminute acuity
    limit and a 300 mm viewing distance the eye resolves about
    8.727e-5 m (87.3 micrometers); at the 250 mm near point about
    7.272e-5 m (72.7 micrometers).

    Raises ValueError for a non-positive viewing distance or a
    non-positive acuity angle.
    """
    if viewing_distance <= 0:
        raise ValueError(
            "viewing distance must be > 0, got %r" % (viewing_distance,)
        )
    if eye_angle_arcmin <= 0:
        raise ValueError(
            "eye acuity angle must be > 0 arcmin, got %r" % (eye_angle_arcmin,)
        )
    return viewing_distance * math.tan(math.radians(eye_angle_arcmin / 60.0))


def resolvable_size(magnification, viewing_distance, eye_angle_arcmin=EYE_ACUITY_ARCMIN):
    """Return the smallest indication size resolved with magnification.

    s = d * tan(theta) / M: the eye resolution limit divided by the
    magnification M of the magnifier, borescope eyepiece, or video
    system. A 10x magnifier at the 250 mm near point resolves about
    7.272e-6 m (7.3 micrometers); a 5x system at 300 mm about
    1.745e-5 m (17.5 micrometers).

    Raises ValueError for a non-positive magnification, viewing
    distance, or acuity angle.
    """
    if magnification <= 0:
        raise ValueError(
            "magnification must be > 0, got %r" % (magnification,)
        )
    if viewing_distance <= 0:
        raise ValueError(
            "viewing distance must be > 0, got %r" % (viewing_distance,)
        )
    if eye_angle_arcmin <= 0:
        raise ValueError(
            "eye acuity angle must be > 0 arcmin, got %r" % (eye_angle_arcmin,)
        )
    return (
        viewing_distance
        * math.tan(math.radians(eye_angle_arcmin / 60.0))
        / magnification
    )


def magnification_for_resolution(target_size, viewing_distance, eye_angle_arcmin=EYE_ACUITY_ARCMIN):
    """Return the magnification needed to resolve a target indication.

    M = d * tan(theta) / s, the inverse of resolvable_size. Resolving
    a 25 micrometer indication at the 250 mm near point needs about
    2.91x; a 50 micrometer indication at 300 mm needs about 1.75x. If
    the required magnification exceeds what the tool provides, the
    indication class cannot be reliably seen and the method or optic
    must change.

    Raises ValueError for a non-positive target size, viewing distance,
    or acuity angle.
    """
    if target_size <= 0:
        raise ValueError("target size must be > 0, got %r" % (target_size,))
    if viewing_distance <= 0:
        raise ValueError(
            "viewing distance must be > 0, got %r" % (viewing_distance,)
        )
    if eye_angle_arcmin <= 0:
        raise ValueError(
            "eye acuity angle must be > 0 arcmin, got %r" % (eye_angle_arcmin,)
        )
    return (
        viewing_distance
        * math.tan(math.radians(eye_angle_arcmin / 60.0))
        / target_size
    )


def illuminance_from_intensity(luminous_intensity, distance):
    """Return the illuminance in lux at a distance from a point lamp.

    Inverse-square law E = I / d^2, with I the luminous intensity in
    candela and d the distance in meters. A 250 cd lamp at 0.5 m gives
    1000 lux, the level commonly required for close visual inspection
    of fine detail; the same lamp at 1 m gives 250 lux, too dim for
    fine indications.

    Raises ValueError for a non-positive luminous intensity or
    distance.
    """
    if luminous_intensity <= 0:
        raise ValueError(
            "luminous intensity must be > 0, got %r" % (luminous_intensity,)
        )
    if distance <= 0:
        raise ValueError("distance must be > 0, got %r" % (distance,))
    return luminous_intensity / (distance * distance)


def intensity_for_illuminance(illuminance, distance):
    """Return the lamp intensity in candela for a target illuminance.

    I = E * d^2, the inverse of the inverse-square law. Reaching 1000
    lux at a 0.5 m working distance needs a 250 cd lamp; reaching the
    same 1000 lux at 1 m needs 1000 cd, four times the intensity,
    because the light spreads over four times the area.

    Raises ValueError for a non-positive illuminance or distance.
    """
    if illuminance <= 0:
        raise ValueError(
            "illuminance must be > 0, got %r" % (illuminance,)
        )
    if distance <= 0:
        raise ValueError("distance must be > 0, got %r" % (distance,))
    return illuminance * distance * distance


def distance_for_illuminance(luminous_intensity, illuminance):
    """Return the lamp distance in meters that gives a target illuminance.

    d = sqrt(I / E), the inverse-square law solved for distance. A
    250 cd lamp must sit within 0.5 m of the surface to hold 1000 lux;
    beyond that the illumination falls below the inspection
    requirement.

    Raises ValueError for a non-positive luminous intensity or
    illuminance.
    """
    if luminous_intensity <= 0:
        raise ValueError(
            "luminous intensity must be > 0, got %r" % (luminous_intensity,)
        )
    if illuminance <= 0:
        raise ValueError(
            "illuminance must be > 0, got %r" % (illuminance,)
        )
    return math.sqrt(luminous_intensity / illuminance)


def foot_candles_to_lux(foot_candles):
    """Return the illuminance in lux for a value in foot-candles.

    lux = fc * 10.76391. Many legacy and US procedures state the
    minimum as 100 foot-candles, about 1076.4 lux, for direct visual
    inspection of fine detail.

    Raises ValueError for a negative foot-candle value.
    """
    if foot_candles < 0:
        raise ValueError(
            "foot-candles must be >= 0, got %r" % (foot_candles,)
        )
    return foot_candles * LUX_PER_FOOT_CANDLE


def lux_to_foot_candles(lux):
    """Return the illuminance in foot-candles for a value in lux.

    fc = lux / 10.76391. A 1000 lux requirement is about 92.9
    foot-candles, so a procedure that states 100 fc is slightly
    stricter than one that states 1000 lux.

    Raises ValueError for a negative lux value.
    """
    if lux < 0:
        raise ValueError("lux must be >= 0, got %r" % (lux,))
    return lux / LUX_PER_FOOT_CANDLE


def field_of_view(working_distance, full_angle_deg):
    """Return the borescope field of view width in meters.

    FOV = 2 * d * tan(full_angle / 2), with d the working distance in
    meters and full_angle_deg the total angular field of the optic.
    A 40 degree borescope at a 50 mm working distance covers about
    3.64e-2 m (36.4 mm); at 100 mm with a 60 degree field about
    1.155e-1 m (115.5 mm).

    Raises ValueError for a non-positive working distance or an angle
    outside (0, 180) degrees.
    """
    if working_distance <= 0:
        raise ValueError(
            "working distance must be > 0, got %r" % (working_distance,)
        )
    if full_angle_deg <= 0 or full_angle_deg >= 180:
        raise ValueError(
            "full field angle must be in (0, 180) degrees, got %r"
            % (full_angle_deg,)
        )
    return 2.0 * working_distance * math.tan(math.radians(full_angle_deg / 2.0))


def scan_positions(part_area, field_area, overlap_fraction):
    """Return the number of field-of-view positions to cover a surface.

    n = ceil(part_area / (field_area * (1 - overlap_fraction))): the
    number of fields needed when each field overlaps the next by the
    given fraction to avoid missing indications at the seams. A 0.01 m2
    surface covered with a 1.6e-3 m2 field at 20 percent overlap needs
    ceil(0.01 / 0.00128) = 8 positions.

    Raises ValueError for a negative part area, a non-positive field
    area, or an overlap fraction outside [0, 1).
    """
    if part_area < 0:
        raise ValueError("part area must be >= 0, got %r" % (part_area,))
    if field_area <= 0:
        raise ValueError("field area must be > 0, got %r" % (field_area,))
    if overlap_fraction < 0 or overlap_fraction >= 1.0:
        raise ValueError(
            "overlap fraction must be in [0, 1), got %r" % (overlap_fraction,)
        )
    if part_area == 0:
        return 0
    effective = field_area * (1.0 - overlap_fraction)
    return int(math.ceil(part_area / effective))


def acceptance_verdict(measured_length, acceptance_limit):
    """Return True when a measured indication meets the acceptance criteria.

    A surface indication is acceptable when its measured length is at
    or below the acceptance limit from the engineering specification.
    A 1.2 mm indication against a 1.0 mm limit returns False (reject);
    a 0.8 mm indication against the same limit returns True (accept).
    The limit itself comes from the specification, not from the math.

    Raises ValueError for a negative measured length or a non-positive
    acceptance limit.
    """
    if measured_length < 0:
        raise ValueError(
            "measured length must be >= 0, got %r" % (measured_length,)
        )
    if acceptance_limit <= 0:
        raise ValueError(
            "acceptance limit must be > 0, got %r" % (acceptance_limit,)
        )
    return measured_length <= acceptance_limit
