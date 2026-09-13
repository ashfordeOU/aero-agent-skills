#!/usr/bin/env python3
"""ECSS-E-ST-20C clause 7.2.2.3.1 radiating element characterisation
(paraphrase, not copy).

Common-knowledge summary (standards-map.yaml, ecss: gated false): the
electrical engineering standard expects the performance of a complete
antenna to be predicted from the characterised behaviour of its
radiating element, characterised in isolation. This module implements
the checkable part of that clause: categorization of an element type
into a radiator family, the characterisation quantities each family
must carry, isolated directivity from mouth area and aperture
efficiency, realised element gain after mismatch and dissipative
losses, a cosine-exponent element pattern fitted to a measured
half-power beamwidth, the cross-polar separation and the phase-centre
defocus checks, and the decision that lattice spacing or measured
mutual coupling has made the isolated record an invalid input to the
whole-antenna prediction. It does not run a full-wave solver, does not
synthesise an element geometry, and does not substitute for a measured
embedded-element pattern.
"""

import math

# Relative tolerance that absorbs floating-point representation error
# when a quantity sits exactly on a limit. It widens no engineering
# limit: it only stops a value that is mathematically equal to the
# limit from reading as a violation a few ULPs out.
LIMIT_REL_TOL = 1e-9

SPEED_OF_LIGHT_M_PER_S = 299792458.0

# Level returned for a direction outside the forward hemisphere, where
# the cosine-exponent element model is not defined.
NO_FORWARD_RADIATION_DBI = -200.0

APERTURE_TYPE_ELEMENTS = frozenset(
    {
        "pyramidal_horn",
        "conical_horn",
        "corrugated_horn",
        "open_ended_waveguide",
        "septum_polariser_horn",
    }
)
RESONANT_PRINTED_ELEMENTS = frozenset(
    {
        "microstrip_patch",
        "stacked_patch",
        "printed_dipole",
        "annular_slot",
        "crossed_slot",
    }
)
TRAVELLING_WAVE_ELEMENTS = frozenset(
    {
        "axial_mode_helix",
        "quadrifilar_helix",
        "archimedean_spiral",
        "dielectric_rod",
        "tapered_slot_radiator",
    }
)

COMMON_CHARACTERISATION_QUANTITIES = frozenset(
    {
        "co_polar_pattern",
        "cross_polar_pattern",
        "input_reflection_coefficient",
        "phase_centre_location",
    }
)
FAMILY_EXTRA_QUANTITIES = {
    "aperture_type": frozenset({"aperture_efficiency", "aperture_field_taper"}),
    "resonant_printed": frozenset(
        {"impedance_bandwidth", "surface_wave_efficiency"}
    ),
    "travelling_wave": frozenset(
        {"axial_ratio_pattern", "radiation_phase_progression"}
    ),
}
RECOGNISED_QUANTITIES = frozenset(
    set(COMMON_CHARACTERISATION_QUANTITIES).union(
        *[set(v) for v in FAMILY_EXTRA_QUANTITIES.values()]
    )
)

# Below this lattice spacing, or above this worst-case coupling level,
# the active element behaviour differs enough from the isolated
# behaviour that an embedded-element pattern is required.
ISOLATED_PATTERN_MIN_SPACING_WAVELENGTHS = 0.6
ISOLATED_PATTERN_MAX_COUPLING_DB = -20.0


def _meets_lower_limit(value, limit):
    """True when value is at or above limit, treating a value equal to
    the limit within LIMIT_REL_TOL as meeting it."""
    return value >= limit or math.isclose(value, limit, rel_tol=LIMIT_REL_TOL)


def _within_upper_limit(value, limit):
    """True when value is at or below limit, treating a value equal to
    the limit within LIMIT_REL_TOL as within it."""
    return value <= limit or math.isclose(value, limit, rel_tol=LIMIT_REL_TOL)


def categorize_radiating_element(element_type):
    """Radiator family for an element type: "aperture_type",
    "resonant_printed" or "travelling_wave". Raises ValueError for an
    element type outside the clause 7.2.2.3.1 element set."""
    if element_type in APERTURE_TYPE_ELEMENTS:
        return "aperture_type"
    if element_type in RESONANT_PRINTED_ELEMENTS:
        return "resonant_printed"
    if element_type in TRAVELLING_WAVE_ELEMENTS:
        return "travelling_wave"
    raise ValueError("uncategorized radiating element type: %r" % (element_type,))


def required_characterisation_quantities(element_type):
    """Quantity set the characterisation record must carry for this
    element type: the common four plus the family extras."""
    family = categorize_radiating_element(element_type)
    return frozenset(
        set(COMMON_CHARACTERISATION_QUANTITIES) | set(FAMILY_EXTRA_QUANTITIES[family])
    )


def missing_characterisation_quantities(element_type, recorded_quantities):
    """Sorted list of required quantities absent from the record.
    Raises ValueError when the record carries a token that is not a
    recognised characterisation quantity."""
    recorded = set(recorded_quantities)
    unknown = sorted(recorded - set(RECOGNISED_QUANTITIES))
    if unknown:
        raise ValueError("unrecognised characterisation quantity: %s" % unknown[0])
    return sorted(set(required_characterisation_quantities(element_type)) - recorded)


def wavelength_m(frequency_hz):
    """Free-space wavelength in metres. Raises ValueError for a
    non-positive frequency."""
    if frequency_hz <= 0.0:
        raise ValueError("frequency must be positive, got %r" % (frequency_hz,))
    return SPEED_OF_LIGHT_M_PER_S / float(frequency_hz)


def isolated_directivity_dbi(aperture_area_m2, frequency_hz, aperture_efficiency):
    """Isolated directivity of an aperture-type radiator, in dBi, from
    its physical mouth area, the operating frequency and the aperture
    efficiency. Raises ValueError for a non-positive area or an
    efficiency outside the open interval zero to one inclusive."""
    if aperture_area_m2 <= 0.0:
        raise ValueError("aperture area must be positive, got %r" % (aperture_area_m2,))
    if not 0.0 < aperture_efficiency <= 1.0:
        raise ValueError(
            "aperture efficiency must be in (0, 1], got %r" % (aperture_efficiency,)
        )
    lam = wavelength_m(frequency_hz)
    directivity = 4.0 * math.pi * aperture_area_m2 * aperture_efficiency / (lam * lam)
    return 10.0 * math.log10(directivity)


def mismatch_efficiency(standing_wave_ratio):
    """Fraction of incident power accepted by the element input, from
    its voltage standing-wave ratio. Raises ValueError below unity."""
    if standing_wave_ratio < 1.0:
        raise ValueError(
            "standing-wave ratio must be at least 1.0, got %r" % (standing_wave_ratio,)
        )
    gamma = (standing_wave_ratio - 1.0) / (standing_wave_ratio + 1.0)
    return 1.0 - gamma * gamma


def realised_element_gain_dbi(
    directivity_dbi, standing_wave_ratio, radiation_efficiency
):
    """Realised element gain, in dBi: isolated directivity reduced by
    the mismatch loss of the input and by the dissipative loss of the
    radiator. Raises ValueError for a radiation efficiency outside the
    open interval zero to one inclusive."""
    if not 0.0 < radiation_efficiency <= 1.0:
        raise ValueError(
            "radiation efficiency must be in (0, 1], got %r" % (radiation_efficiency,)
        )
    eta_match = mismatch_efficiency(standing_wave_ratio)
    return directivity_dbi + 10.0 * math.log10(eta_match * radiation_efficiency)


def cosine_pattern_exponent(half_power_beamwidth_deg):
    """Exponent of the cosine power pattern whose half-power beamwidth
    matches the measured one. Raises ValueError for a beamwidth outside
    the open interval zero to 180 degrees."""
    if not 0.0 < half_power_beamwidth_deg < 180.0:
        raise ValueError(
            "half-power beamwidth must be in (0, 180) degrees, got %r"
            % (half_power_beamwidth_deg,)
        )
    half_angle = math.radians(half_power_beamwidth_deg / 2.0)
    return math.log(0.5) / math.log(math.cos(half_angle))


def element_pattern_gain_dbi(peak_gain_dbi, exponent, theta_deg):
    """Element gain, in dBi, at an angle from boresight under the
    cosine-exponent model. Directions outside the forward hemisphere
    return NO_FORWARD_RADIATION_DBI. Raises ValueError for a
    non-positive exponent or an angle beyond 180 degrees."""
    if exponent <= 0.0:
        raise ValueError("pattern exponent must be positive, got %r" % (exponent,))
    if abs(theta_deg) > 180.0:
        raise ValueError("angle must be within 180 degrees, got %r" % (theta_deg,))
    if abs(theta_deg) >= 90.0:
        return NO_FORWARD_RADIATION_DBI
    return peak_gain_dbi + 10.0 * exponent * math.log10(
        math.cos(math.radians(theta_deg))
    )


def cross_polar_discrimination_db(co_polar_peak_dbi, cross_polar_peak_dbi):
    """Separation between the co-polar peak and the worst cross-polar
    peak, in decibels. Raises ValueError when the cross-polar peak is
    above the co-polar peak, which is not a co-polarised element
    characterisation."""
    if cross_polar_peak_dbi > co_polar_peak_dbi:
        raise ValueError(
            "cross-polar peak %r above co-polar peak %r"
            % (cross_polar_peak_dbi, co_polar_peak_dbi)
        )
    return co_polar_peak_dbi - cross_polar_peak_dbi


def phase_centre_defocus_deg(
    phase_centre_offset_m, frequency_hz, subtended_half_angle_deg
):
    """Peak phase error, in degrees, produced across the subtended
    half-angle by a phase-centre offset along the boresight axis.
    Raises ValueError for a negative offset or a half-angle outside the
    open interval zero to 90 degrees inclusive."""
    if phase_centre_offset_m < 0.0:
        raise ValueError(
            "phase-centre offset must not be negative, got %r" % (phase_centre_offset_m,)
        )
    if not 0.0 < subtended_half_angle_deg <= 90.0:
        raise ValueError(
            "subtended half-angle must be in (0, 90] degrees, got %r"
            % (subtended_half_angle_deg,)
        )
    lam = wavelength_m(frequency_hz)
    travel = phase_centre_offset_m * (
        1.0 - math.cos(math.radians(subtended_half_angle_deg))
    )
    return 360.0 * travel / lam


def embedded_pattern_required(spacing_wavelengths, worst_coupling_db):
    """True when the lattice spacing or the worst measured element
    mutual coupling makes the isolated characterisation an invalid
    input to the whole-antenna prediction. Raises ValueError for a
    non-positive spacing or a coupling level above zero decibels."""
    if spacing_wavelengths <= 0.0:
        raise ValueError(
            "lattice spacing must be positive, got %r" % (spacing_wavelengths,)
        )
    if worst_coupling_db > 0.0:
        raise ValueError(
            "coupling level must not exceed 0 dB, got %r" % (worst_coupling_db,)
        )
    too_close = not _meets_lower_limit(
        spacing_wavelengths, ISOLATED_PATTERN_MIN_SPACING_WAVELENGTHS
    )
    too_coupled = not _within_upper_limit(
        worst_coupling_db, ISOLATED_PATTERN_MAX_COUPLING_DB
    )
    return bool(too_close or too_coupled)


def _require(record, key):
    if key not in record:
        raise ValueError("characterisation record missing key %r" % (key,))
    return record[key]


def assess_radiating_element(record):
    """Assess one radiating-element characterisation record against
    clause 7.2.2.3.1 and return the aggregated result.

    Required keys: element_type, frequency_hz, recorded_quantities,
    standing_wave_ratio, radiation_efficiency, required_gain_dbi,
    half_power_beamwidth_deg, cross_polar_peak_dbi, required_xpd_db,
    phase_centre_offset_m, subtended_half_angle_deg,
    max_phase_centre_defocus_deg. An aperture-type element also needs
    aperture_area_m2 and aperture_efficiency; the other families need a
    measured_directivity_dbi. Optional keys spacing_wavelengths and
    worst_coupling_db trigger the embedded-pattern decision.
    """
    if not isinstance(record, dict):
        raise ValueError("characterisation record must be a mapping")
    element_type = _require(record, "element_type")
    family = categorize_radiating_element(element_type)
    frequency_hz = _require(record, "frequency_hz")
    findings = []

    missing = missing_characterisation_quantities(
        element_type, _require(record, "recorded_quantities")
    )
    findings.extend("missing_characterisation_quantity:%s" % q for q in missing)

    if family == "aperture_type":
        directivity = isolated_directivity_dbi(
            _require(record, "aperture_area_m2"),
            frequency_hz,
            _require(record, "aperture_efficiency"),
        )
    else:
        directivity = float(_require(record, "measured_directivity_dbi"))

    realised_gain = realised_element_gain_dbi(
        directivity,
        _require(record, "standing_wave_ratio"),
        _require(record, "radiation_efficiency"),
    )
    required_gain = _require(record, "required_gain_dbi")
    if not _meets_lower_limit(realised_gain, required_gain):
        findings.append("realised_element_gain_below_requirement")

    exponent = cosine_pattern_exponent(_require(record, "half_power_beamwidth_deg"))

    xpd = cross_polar_discrimination_db(
        realised_gain, _require(record, "cross_polar_peak_dbi")
    )
    required_xpd = _require(record, "required_xpd_db")
    if not _meets_lower_limit(xpd, required_xpd):
        findings.append("cross_polar_discrimination_below_requirement")

    defocus = phase_centre_defocus_deg(
        _require(record, "phase_centre_offset_m"),
        frequency_hz,
        _require(record, "subtended_half_angle_deg"),
    )
    if not _within_upper_limit(defocus, _require(record, "max_phase_centre_defocus_deg")):
        findings.append("phase_centre_defocus_above_limit")

    needs_embedded = False
    if "spacing_wavelengths" in record or "worst_coupling_db" in record:
        needs_embedded = embedded_pattern_required(
            _require(record, "spacing_wavelengths"),
            _require(record, "worst_coupling_db"),
        )
        if needs_embedded:
            findings.append("embedded_element_pattern_required")

    return {
        "element_family": family,
        "missing_quantities": missing,
        "isolated_directivity_dbi": directivity,
        "realised_element_gain_dbi": realised_gain,
        "pattern_exponent": exponent,
        "cross_polar_discrimination_db": xpd,
        "phase_centre_defocus_deg": defocus,
        "embedded_pattern_required": needs_embedded,
        "findings": findings,
        "supports_antenna_prediction": not findings,
    }
