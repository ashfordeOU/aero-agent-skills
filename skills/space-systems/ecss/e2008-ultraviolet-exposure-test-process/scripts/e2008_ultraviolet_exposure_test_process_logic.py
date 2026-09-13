#!/usr/bin/env python3
"""Measuring integrated ultraviolet photon intensity at the test item position.

Anchor: ECSS-E-ST-20-08C clause 6.4.3.15.2. The procedure below is a
paraphrase into implementable steps; no standard text is reproduced.

What the clause asks the process to produce
-------------------------------------------
An accelerated ultraviolet exposure is only worth what its dosimetry is
worth. The article does not report the dose it received; the radiometry
does, and it reports it as an integrated photon intensity at the place
the article sits -- not at the lamp, not at a convenient port in the
chamber wall, and not over whatever band the detector happens to pass.

Four things have to line up before an accumulated figure means anything:

    band        the spectral irradiance is integrated over the required
                ultraviolet band, with the band edges interpolated
                rather than snapped to the nearest sample
    position    the sensor reading is referred to the test item plane,
                through the inverse square of the distance ratio and
                the cosine of the plane tilt
    uniformity  the beam across the item plane is flat enough that one
                reading stands for the whole article
    provenance  the sensor calibration is inside its interval and the
                exposure was sampled often enough to integrate

Photon intensity is not irradiance. A watt of 400 nm light carries twice
the photons of a watt at 200 nm, and the damage is done by photons, so
the band integral is carried in both currencies: watts per square metre
for the dose bookkeeping, photons per square metre per second for the
quantity the clause names.

Standard library only, offline, deterministic.
"""

from __future__ import annotations

import math

__all__ = [
    "DEFAULT_RADIOMETRY_POLICY",
    "INTENSITY_NOT_MEASURED",
    "INTENSITY_RECORD_DEFICIENT",
    "INTENSITY_RECORD_TRACEABLE",
    "PLANCK_CONSTANT_J_S",
    "SECONDS_PER_HOUR",
    "SPEED_OF_LIGHT_M_S",
    "accumulated_dose_j_m2",
    "assess_intensity_measurement",
    "band_irradiance_w_m2",
    "band_photon_flux_per_m2_s",
    "beam_non_uniformity",
    "calibration_in_date",
    "equivalent_sun_hours",
    "integrated_photon_fluence_per_m2",
    "position_correction_factor",
    "sampling_adequate",
    "sensor_at_item_position",
    "validate_radiometry_policy",
]

PLANCK_CONSTANT_J_S = 6.62607015e-34
SPEED_OF_LIGHT_M_S = 299792458.0
SECONDS_PER_HOUR = 3600.0

INTENSITY_NOT_MEASURED = "integrated-intensity-not-measured"
INTENSITY_RECORD_DEFICIENT = "integrated-intensity-record-deficient"
INTENSITY_RECORD_TRACEABLE = "integrated-intensity-record-traceable"

DEFAULT_RADIOMETRY_POLICY = {
    # Near-ultraviolet band the integrated intensity is reported over.
    "band_low_nm": 200.0,
    "band_high_nm": 400.0,
    # How far off the item plane a sensor may sit before its reading has
    # to be referred rather than quoted.
    "max_position_offset_mm": 10.0,
    "max_tilt_deg": 5.0,
    # Beam flatness across the item, as (max - min) / (max + min).
    "max_non_uniformity": 0.10,
    "calibration_interval_days": 365.0,
    "min_samples_per_exposure": 24,
    # One ultraviolet sun over the band, at 1 AU.
    "ultraviolet_sun_irradiance_w_m2": 118.0,
}

_REL_TOL = 1e-9
_ABS_TOL = 1e-12


def _is_finite_number(value):
    return (
        isinstance(value, (int, float))
        and not isinstance(value, bool)
        and math.isfinite(value)
    )


def _require_number(name, value):
    if not _is_finite_number(value):
        raise ValueError("%s must be a finite number, got %r" % (name, value))
    return float(value)


def _require_positive(name, value):
    number = _require_number(name, value)
    if number <= 0.0:
        raise ValueError("%s must be greater than zero, got %r" % (name, value))
    return number


def _require_non_negative(name, value):
    number = _require_number(name, value)
    if number < 0.0:
        raise ValueError("%s must not be negative, got %r" % (name, value))
    return number


def _require_count(name, value):
    if not isinstance(value, int) or isinstance(value, bool) or value <= 0:
        raise ValueError("%s must be a positive whole number, got %r" % (name, value))
    return value


def _at_least(value, limit):
    """value >= limit, absorbing floating-point representation error."""
    return value >= limit or math.isclose(
        value, limit, rel_tol=_REL_TOL, abs_tol=_ABS_TOL
    )


def _at_most(value, limit):
    """value <= limit, absorbing floating-point representation error."""
    return value <= limit or math.isclose(
        value, limit, rel_tol=_REL_TOL, abs_tol=_ABS_TOL
    )


def validate_radiometry_policy(policy):
    """Check a dosimetry policy is complete and self-consistent."""
    if not isinstance(policy, dict):
        raise ValueError("policy must be a mapping, got %r" % (policy,))
    low = _require_positive("band_low_nm", policy.get("band_low_nm"))
    high = _require_positive("band_high_nm", policy.get("band_high_nm"))
    if high <= low:
        raise ValueError(
            "band_high_nm %g must be above band_low_nm %g" % (high, low)
        )
    _require_non_negative(
        "max_position_offset_mm", policy.get("max_position_offset_mm")
    )
    tilt = _require_non_negative("max_tilt_deg", policy.get("max_tilt_deg"))
    if tilt >= 90.0:
        raise ValueError(
            "max_tilt_deg %g leaves the item plane edge-on to the beam" % tilt
        )
    uniformity = _require_non_negative(
        "max_non_uniformity", policy.get("max_non_uniformity")
    )
    if uniformity >= 1.0:
        raise ValueError(
            "max_non_uniformity %g admits a beam with a dark patch" % uniformity
        )
    _require_positive(
        "calibration_interval_days", policy.get("calibration_interval_days")
    )
    _require_count(
        "min_samples_per_exposure", policy.get("min_samples_per_exposure")
    )
    _require_positive(
        "ultraviolet_sun_irradiance_w_m2",
        policy.get("ultraviolet_sun_irradiance_w_m2"),
    )
    return policy


def _validate_spectrum(spectrum):
    """Return the spectral samples as strictly increasing wavelength pairs."""
    if not isinstance(spectrum, (list, tuple)) or len(spectrum) < 2:
        raise ValueError(
            "spectrum must be a sequence of at least two "
            "(wavelength_nm, spectral_irradiance_w_m2_nm) samples"
        )
    samples = []
    previous = None
    for index, sample in enumerate(spectrum):
        if not isinstance(sample, (list, tuple)) or len(sample) != 2:
            raise ValueError(
                "spectrum[%d] must be a (wavelength_nm, "
                "spectral_irradiance_w_m2_nm) pair" % index
            )
        wavelength = _require_positive("spectrum[%d] wavelength_nm" % index, sample[0])
        value = _require_non_negative(
            "spectrum[%d] spectral_irradiance_w_m2_nm" % index, sample[1]
        )
        if previous is not None and wavelength <= previous:
            raise ValueError(
                "spectrum wavelengths must increase strictly; spectrum[%d] is "
                "%g nm after %g nm" % (index, wavelength, previous)
            )
        previous = wavelength
        samples.append((wavelength, value))
    return tuple(samples)


def _interpolate(samples, wavelength):
    """Spectral irradiance at a wavelength inside the sampled span."""
    lower = samples[0][0]
    upper = samples[-1][0]
    target = min(max(wavelength, lower), upper)
    for index in range(len(samples) - 1):
        left = samples[index]
        right = samples[index + 1]
        if left[0] <= target <= right[0]:
            span = right[0] - left[0]
            return left[1] + (right[1] - left[1]) * (target - left[0]) / span
    raise ValueError(
        "wavelength %g nm is outside the sampled span %g to %g nm"
        % (wavelength, lower, upper)
    )


def _band_samples(spectrum, band_low_nm, band_high_nm):
    """Samples of the spectrum clipped to the band, with interpolated edges."""
    samples = _validate_spectrum(spectrum)
    low = _require_positive("band_low_nm", band_low_nm)
    high = _require_positive("band_high_nm", band_high_nm)
    if high <= low:
        raise ValueError(
            "band_high_nm %g must be above band_low_nm %g" % (high, low)
        )
    if not _at_most(samples[0][0], low) or not _at_least(samples[-1][0], high):
        raise ValueError(
            "spectrum spans %g to %g nm and does not cover the %g to %g nm "
            "band the intensity is reported over"
            % (samples[0][0], samples[-1][0], low, high)
        )
    inner = [sample for sample in samples if low < sample[0] < high]
    edges = [(low, _interpolate(samples, low))]
    edges.extend(inner)
    edges.append((high, _interpolate(samples, high)))
    return tuple(edges)


def band_irradiance_w_m2(spectrum, band_low_nm, band_high_nm):
    """Integrate spectral irradiance over the reported ultraviolet band."""
    samples = _band_samples(spectrum, band_low_nm, band_high_nm)
    total = 0.0
    for index in range(len(samples) - 1):
        left = samples[index]
        right = samples[index + 1]
        total += 0.5 * (left[1] + right[1]) * (right[0] - left[0])
    return total


def band_photon_flux_per_m2_s(spectrum, band_low_nm, band_high_nm):
    """Integrate the band as photons rather than watts.

    A photon at wavelength lambda carries h c / lambda joules, so the
    photon rate of a spectral irradiance is E(lambda) lambda / (h c).
    """
    samples = _band_samples(spectrum, band_low_nm, band_high_nm)
    scale = 1.0e-9 / (PLANCK_CONSTANT_J_S * SPEED_OF_LIGHT_M_S)
    total = 0.0
    for index in range(len(samples) - 1):
        left = samples[index]
        right = samples[index + 1]
        left_rate = left[1] * left[0] * scale
        right_rate = right[1] * right[0] * scale
        total += 0.5 * (left_rate + right_rate) * (right[0] - left[0])
    return total


def integrated_photon_fluence_per_m2(photon_flux_per_m2_s, duration_s):
    """Photons per square metre accumulated over the exposure."""
    flux = _require_positive("photon_flux_per_m2_s", photon_flux_per_m2_s)
    duration = _require_positive("duration_s", duration_s)
    return flux * duration


def accumulated_dose_j_m2(irradiance_w_m2, duration_s):
    """Energy per square metre accumulated over the exposure."""
    irradiance = _require_positive("irradiance_w_m2", irradiance_w_m2)
    duration = _require_positive("duration_s", duration_s)
    return irradiance * duration


def equivalent_sun_hours(
    irradiance_w_m2, duration_s, policy=DEFAULT_RADIOMETRY_POLICY
):
    """Accumulated dose expressed in equivalent ultraviolet sun hours."""
    validate_radiometry_policy(policy)
    dose = accumulated_dose_j_m2(irradiance_w_m2, duration_s)
    one_sun = float(policy["ultraviolet_sun_irradiance_w_m2"])
    return dose / (one_sun * SECONDS_PER_HOUR)


def position_correction_factor(
    sensor_distance_mm, item_distance_mm, tilt_deg=0.0
):
    """Factor carrying a sensor reading to the test item plane.

    Irradiance falls with the square of the distance from the source and
    with the cosine of the angle between the beam and the item plane
    normal, so a sensor that is not at the item position reports a
    number that has to be referred before it can be integrated.
    """
    sensor = _require_positive("sensor_distance_mm", sensor_distance_mm)
    item = _require_positive("item_distance_mm", item_distance_mm)
    tilt = _require_non_negative("tilt_deg", tilt_deg)
    if tilt >= 90.0:
        raise ValueError(
            "tilt_deg %g leaves the item plane edge-on to the beam" % tilt
        )
    ratio = sensor / item
    return ratio * ratio * math.cos(math.radians(tilt))


def sensor_at_item_position(
    position_offset_mm, tilt_deg, policy=DEFAULT_RADIOMETRY_POLICY
):
    """True when the sensor stands close enough to quote its reading directly."""
    validate_radiometry_policy(policy)
    offset = _require_non_negative("position_offset_mm", position_offset_mm)
    tilt = _require_non_negative("tilt_deg", tilt_deg)
    return _at_most(offset, float(policy["max_position_offset_mm"])) and _at_most(
        tilt, float(policy["max_tilt_deg"])
    )


def beam_non_uniformity(readings):
    """Flatness of the beam across the item plane, as (max - min)/(max + min)."""
    if not isinstance(readings, (list, tuple)) or len(readings) < 2:
        raise ValueError(
            "readings must be a sequence of at least two item-plane irradiances"
        )
    values = [
        _require_positive("readings[%d]" % index, value)
        for index, value in enumerate(readings)
    ]
    highest = max(values)
    lowest = min(values)
    return (highest - lowest) / (highest + lowest)


def calibration_in_date(
    days_since_calibration, policy=DEFAULT_RADIOMETRY_POLICY
):
    """True while the sensor calibration is inside its declared interval."""
    validate_radiometry_policy(policy)
    days = _require_non_negative(
        "days_since_calibration", days_since_calibration
    )
    return _at_most(days, float(policy["calibration_interval_days"]))


def sampling_adequate(sample_count, policy=DEFAULT_RADIOMETRY_POLICY):
    """True when the exposure was sampled often enough to integrate."""
    validate_radiometry_policy(policy)
    count = _require_count("sample_count", sample_count)
    return count >= int(policy["min_samples_per_exposure"])


def assess_intensity_measurement(case, policy=DEFAULT_RADIOMETRY_POLICY):
    """Full clause 6.4.3.15.2 judgement for one intensity measurement record."""
    if not isinstance(case, dict):
        raise ValueError("case must be a mapping, got %r" % (case,))
    validate_radiometry_policy(policy)
    duration_s = _require_positive("case duration_s", case.get("duration_s"))

    findings = []
    result = {
        "band_low_nm": float(policy["band_low_nm"]),
        "band_high_nm": float(policy["band_high_nm"]),
        "duration_s": duration_s,
        "sensor_irradiance_w_m2": None,
        "item_plane_irradiance_w_m2": None,
        "position_correction_factor": None,
        "photon_flux_per_m2_s": None,
        "integrated_photon_fluence_per_m2": None,
        "accumulated_dose_j_m2": None,
        "equivalent_sun_hours": None,
        "beam_non_uniformity": None,
        "sensor_at_item_position": None,
        "calibration_in_date": None,
        "sampling_adequate": None,
        "findings": findings,
    }

    measurement = case.get("measurement")
    if measurement is None:
        findings.append(
            "no integrated ultraviolet intensity was measured at the test item "
            "position during the exposure"
        )
        result["verdict"] = INTENSITY_NOT_MEASURED
        return result
    if not isinstance(measurement, dict):
        raise ValueError("measurement must be a mapping, got %r" % (measurement,))
    if "spectrum" not in measurement:
        raise ValueError(
            "measurement is missing spectrum; an integrated intensity cannot "
            "be rebuilt from a single broadband number"
        )

    low = float(policy["band_low_nm"])
    high = float(policy["band_high_nm"])
    sensor_irradiance = band_irradiance_w_m2(measurement["spectrum"], low, high)
    if sensor_irradiance <= 0.0:
        raise ValueError(
            "the spectrum integrates to zero over the %g to %g nm band" % (low, high)
        )
    sensor_flux = band_photon_flux_per_m2_s(measurement["spectrum"], low, high)

    sensor_distance = _require_positive(
        "measurement sensor_distance_mm", measurement.get("sensor_distance_mm")
    )
    item_distance = _require_positive(
        "measurement item_distance_mm", measurement.get("item_distance_mm")
    )
    tilt = _require_non_negative(
        "measurement tilt_deg", measurement.get("tilt_deg", 0.0)
    )
    correction = position_correction_factor(sensor_distance, item_distance, tilt)
    item_irradiance = sensor_irradiance * correction
    item_flux = sensor_flux * correction

    offset = abs(sensor_distance - item_distance)
    at_position = sensor_at_item_position(offset, tilt, policy)
    uniformity = beam_non_uniformity(measurement.get("item_plane_readings", ()))
    in_date = calibration_in_date(
        measurement.get("days_since_calibration", 0.0), policy
    )
    sampled = sampling_adequate(measurement.get("sample_count", 1), policy)

    result["sensor_irradiance_w_m2"] = sensor_irradiance
    result["item_plane_irradiance_w_m2"] = item_irradiance
    result["position_correction_factor"] = correction
    result["photon_flux_per_m2_s"] = item_flux
    result["integrated_photon_fluence_per_m2"] = integrated_photon_fluence_per_m2(
        item_flux, duration_s
    )
    result["accumulated_dose_j_m2"] = accumulated_dose_j_m2(
        item_irradiance, duration_s
    )
    result["equivalent_sun_hours"] = equivalent_sun_hours(
        item_irradiance, duration_s, policy
    )
    result["beam_non_uniformity"] = uniformity
    result["sensor_at_item_position"] = at_position
    result["calibration_in_date"] = in_date
    result["sampling_adequate"] = sampled

    if not at_position:
        findings.append(
            "the sensor stands %.3f mm and %.3f deg off the test item plane, "
            "past the %.3f mm and %.3f deg the reading may be quoted over"
            % (
                offset,
                tilt,
                float(policy["max_position_offset_mm"]),
                float(policy["max_tilt_deg"]),
            )
        )
    if not _at_most(uniformity, float(policy["max_non_uniformity"])):
        findings.append(
            "beam non-uniformity of %.4f across the item plane is past the "
            "%.4f one reading may stand for"
            % (uniformity, float(policy["max_non_uniformity"]))
        )
    if not in_date:
        findings.append(
            "the intensity sensor calibration is %.1f days old, past its "
            "%.1f day interval"
            % (
                _require_non_negative(
                    "days_since_calibration",
                    measurement.get("days_since_calibration", 0.0),
                ),
                float(policy["calibration_interval_days"]),
            )
        )
    if not sampled:
        findings.append(
            "the exposure was sampled %d times, short of the %d samples the "
            "integration needs"
            % (
                _require_count("sample_count", measurement.get("sample_count", 1)),
                int(policy["min_samples_per_exposure"]),
            )
        )

    result["verdict"] = (
        INTENSITY_RECORD_TRACEABLE if not findings else INTENSITY_RECORD_DEFICIENT
    )
    return result
