#!/usr/bin/env python3
"""Normal emittance of a coverglass, taken by the referenced thermal method.

Anchor: ECSS-E-ST-20-08C clause 8.7.6. The procedure below is a paraphrase
into implementable steps; no standard text is reproduced.

The clause does not invent an emittance measurement. It points at the
thermal control standard already in force and asks for the coverglass
normal emittance to be taken that way. Two things follow, and both are
routinely skipped. First, the nominated instrument and the specimen
temperature have to sit inside the band that referenced method fixes --
a portable emissometer calibrated near ambient does not become a
cryogenic instrument because the article was cold. Second, a normal
emittance is a weighted average, not a scan, and the weight is the
blackbody spectral exitance at the specimen temperature. A scan that
stops at 15 um has left a real share of that exitance unmeasured at
300 K, and the average quoted from it is an average over the part of
the spectrum the instrument happened to reach.

Two reduction routes exist:

    spectral-band-average    band emittances weighted by exitance share
    reflectometer-kirchhoff  opaque specimen, emittance = 1 - reflectance

The exitance share of a band is obtained from the closed-form blackbody
fractional function, a rapidly converging series in x = c2 / (lambda T),
so no quadrature and no third-party library is needed and the result is
the same on every platform to within float rounding.

Standard library only, offline, deterministic.
"""

from __future__ import annotations

import math

SECOND_RADIATION_CONSTANT_UM_K = 14387.768775  # c2, micrometre kelvin

ACCEPTED_METHODS = (
    "integrating-sphere-reflectometer",
    "calorimetric-steady-state",
    "portable-emissometer",
    "fourier-transform-spectrometer",
)

SPECTRAL_METHODS = (
    "integrating-sphere-reflectometer",
    "fourier-transform-spectrometer",
)

TOTAL_METHODS = (
    "calorimetric-steady-state",
    "portable-emissometer",
)

REDUCTION_SPECTRAL = "spectral-band-average"
REDUCTION_KIRCHHOFF = "reflectometer-kirchhoff"

# Share of the blackbody exitance the measured bands have to span before a
# band average may be called a normal emittance.
MIN_SPECTRAL_COVERAGE = 0.95

# Exitance share below which the measured bands are not on the emitting
# spectrum at all and no average can be formed from them.
MIN_WEIGHTABLE_EXITANCE = 1e-12

# Room-temperature normal emittance band the referenced thermal control
# method is calibrated over.
REFERENCE_TEMPERATURE_BAND_K = (283.0, 323.0)

EMITTANCE_ACCEPTED = "normal-emittance-accepted"
EMITTANCE_NOT_ACCEPTED = "normal-emittance-not-accepted"

REQUIRED_EVIDENCE = (
    "declared_emittance_band",
    "measurement_bands",
    "method",
    "reported_uncertainty",
    "required_uncertainty",
    "specimen_temperature_k",
)

_REL_TOL = 1e-9
_ABS_TOL = 1e-15
_SERIES_TERMS = 4000


def _is_finite_number(value):
    return (
        isinstance(value, (int, float))
        and not isinstance(value, bool)
        and math.isfinite(value)
    )


def _require_positive(name, value):
    if not _is_finite_number(value):
        raise ValueError("%s must be a finite number, got %r" % (name, value))
    if value <= 0.0:
        raise ValueError("%s must be greater than zero, got %r" % (name, value))
    return float(value)


def _require_non_negative(name, value):
    if not _is_finite_number(value):
        raise ValueError("%s must be a finite number, got %r" % (name, value))
    if value < 0.0:
        raise ValueError("%s must not be negative, got %r" % (name, value))
    return float(value)


def _require_unit_interval(name, value):
    number = _require_non_negative(name, value)
    if number > 1.0:
        raise ValueError("%s must not exceed one, got %r" % (name, value))
    return number


def _at_least(value, limit):
    """value >= limit, absorbing floating-point representation error.

    Band edges arrive in micrometres and are compared after a series
    summation, so a value that should land on a limit can miss it by a
    few units in the last place. The limit is never relaxed; only the
    comparison tolerates the representation error.
    """
    return value >= limit or math.isclose(
        value, limit, rel_tol=_REL_TOL, abs_tol=_ABS_TOL
    )


def _at_most(value, limit):
    """value <= limit, absorbing floating-point representation error."""
    return value <= limit or math.isclose(
        value, limit, rel_tol=_REL_TOL, abs_tol=_ABS_TOL
    )


def method_is_accepted(method):
    """Whether the nominated instrument is one the referenced method allows."""
    if not isinstance(method, str):
        raise ValueError("method must be a name, got %r" % (method,))
    return method in ACCEPTED_METHODS


def reduction_route(method):
    """Which reduction the nominated instrument feeds."""
    if method in SPECTRAL_METHODS:
        return REDUCTION_SPECTRAL
    if method in TOTAL_METHODS:
        return REDUCTION_KIRCHHOFF
    raise ValueError(
        "unknown emittance method %r; accepted methods are %s"
        % (method, ", ".join(ACCEPTED_METHODS))
    )


def temperature_within_reference_band(temperature_k):
    """Whether the specimen sat inside the band the referenced method covers."""
    value = _require_positive("specimen_temperature_k", temperature_k)
    low, high = REFERENCE_TEMPERATURE_BAND_K
    return _at_least(value, low) and _at_most(value, high)


def blackbody_fraction_below(wavelength_um, temperature_k):
    """Share of blackbody exitance emitted below a wavelength.

    Closed-form fractional function, summed until the terms stop moving
    the total. No quadrature, so the answer does not depend on a step
    size chosen on one platform and reused on another.
    """
    wavelength = _require_positive("wavelength_um", wavelength_um)
    temperature = _require_positive("temperature_k", temperature_k)
    x = SECOND_RADIATION_CONSTANT_UM_K / (wavelength * temperature)
    if x > 700.0:
        return 0.0
    total = 0.0
    for n in range(1, _SERIES_TERMS + 1):
        exponent = -n * x
        if exponent < -745.0:
            break
        term = math.exp(exponent) / n * (
            x * x * x + 3.0 * x * x / n + 6.0 * x / (n * n) + 6.0 / (n * n * n)
        )
        total += term
        if term < 1e-18 * max(total, 1e-30):
            break
    fraction = 15.0 / (math.pi ** 4) * total
    if fraction < 0.0:
        return 0.0
    if fraction > 1.0:
        return 1.0
    return fraction


def band_exitance_fraction(lower_um, upper_um, temperature_k):
    """Share of blackbody exitance falling inside one measured band."""
    low = _require_positive("lower_um", lower_um)
    high = _require_positive("upper_um", upper_um)
    if not high > low:
        raise ValueError(
            "band upper edge %g um must sit above lower edge %g um" % (high, low)
        )
    upper_share = blackbody_fraction_below(high, temperature_k)
    lower_share = blackbody_fraction_below(low, temperature_k)
    share = upper_share - lower_share
    return share if share > 0.0 else 0.0


def normalized_bands(bands):
    """Validate a measured band list and return it ordered by lower edge.

    Bands may abut but may not overlap: an overlapping pair would count
    the same exitance share twice and pull the average toward whichever
    band was duplicated.
    """
    if not isinstance(bands, (list, tuple)) or not bands:
        raise ValueError("measurement_bands must be a non-empty sequence, got %r" % (bands,))
    cleaned = []
    for index, band in enumerate(bands):
        if not isinstance(band, dict):
            raise ValueError("band %d must be a mapping, got %r" % (index, band))
        low = _require_positive("band %d lower_um" % index, band.get("lower_um"))
        high = _require_positive("band %d upper_um" % index, band.get("upper_um"))
        if not high > low:
            raise ValueError(
                "band %d upper edge %g um must sit above lower edge %g um"
                % (index, high, low)
            )
        emittance = _require_unit_interval(
            "band %d emittance" % index, band.get("emittance")
        )
        cleaned.append({"lower_um": low, "upper_um": high, "emittance": emittance})
    cleaned.sort(key=lambda item: item["lower_um"])
    for first, second in zip(cleaned, cleaned[1:]):
        if second["lower_um"] < first["upper_um"] and not math.isclose(
            second["lower_um"], first["upper_um"], rel_tol=_REL_TOL, abs_tol=_ABS_TOL
        ):
            raise ValueError(
                "measured bands overlap between %g um and %g um"
                % (second["lower_um"], first["upper_um"])
            )
    return tuple(cleaned)


def spectral_coverage(bands, temperature_k):
    """Share of the blackbody exitance the measured bands actually span."""
    total = 0.0
    for band in normalized_bands(bands):
        total += band_exitance_fraction(
            band["lower_um"], band["upper_um"], temperature_k
        )
    return total if total <= 1.0 else 1.0


def band_weighted_emittance(bands, temperature_k):
    """Normal emittance as the exitance-weighted average of the band values.

    The weight is the exitance share, so a band that carries almost no
    energy cannot drag the average, however wide it looks in wavelength.
    """
    weighted = 0.0
    weight = 0.0
    for band in normalized_bands(bands):
        share = band_exitance_fraction(
            band["lower_um"], band["upper_um"], temperature_k
        )
        weighted += band["emittance"] * share
        weight += share
    if weight < MIN_WEIGHTABLE_EXITANCE:
        raise ValueError(
            "the measured bands carry no usable blackbody exitance at %g K; the "
            "scan sits off the emitting spectrum" % (temperature_k,)
        )
    return weighted / weight


def emittance_from_reflectance(reflectance, transmittance=0.0):
    """Kirchhoff reduction of an opaque-backed reflectometer reading."""
    rho = _require_unit_interval("reflectance", reflectance)
    tau = _require_unit_interval("transmittance", transmittance)
    total = rho + tau
    if total > 1.0 and not math.isclose(total, 1.0, rel_tol=_REL_TOL, abs_tol=_ABS_TOL):
        raise ValueError(
            "reflectance %g and transmittance %g sum above unity; the "
            "reading does not close" % (rho, tau)
        )
    value = 1.0 - total
    return value if value > 0.0 else 0.0


def within_declared_band(value, declared_band):
    """Whether a reduced emittance sits inside the drawing band."""
    if not isinstance(declared_band, dict):
        raise ValueError(
            "declared_emittance_band must be a mapping with minimum and maximum"
        )
    low = _require_unit_interval("declared minimum", declared_band.get("minimum"))
    high = _require_unit_interval("declared maximum", declared_band.get("maximum"))
    if not high > low:
        raise ValueError(
            "declared maximum %g must sit above declared minimum %g" % (high, low)
        )
    number = _require_unit_interval("emittance", value)
    return _at_least(number, low) and _at_most(number, high)


def missing_evidence(case):
    """Required inputs the emittance record has not brought."""
    if not isinstance(case, dict):
        raise ValueError("case must be a mapping, got %r" % (case,))
    return tuple(name for name in REQUIRED_EVIDENCE if case.get(name) is None)


def assess_normal_emittance(case):
    """Full clause 8.7.6 judgement of one coverglass emittance record."""
    if not isinstance(case, dict):
        raise ValueError("case must be a mapping, got %r" % (case,))
    absent = missing_evidence(case)
    if absent:
        raise ValueError(
            "coverglass emittance record is missing required evidence: %s"
            % ", ".join(absent)
        )

    method = case.get("method")
    if not method_is_accepted(method):
        raise ValueError(
            "method %r is not one the referenced thermal control method "
            "allows; accepted methods are %s" % (method, ", ".join(ACCEPTED_METHODS))
        )
    route = reduction_route(method)
    temperature = _require_positive(
        "specimen_temperature_k", case.get("specimen_temperature_k")
    )
    reported_uncertainty = _require_non_negative(
        "reported_uncertainty", case.get("reported_uncertainty")
    )
    required_uncertainty = _require_positive(
        "required_uncertainty", case.get("required_uncertainty")
    )

    findings = []
    detail = {}

    if not temperature_within_reference_band(temperature):
        findings.append(
            "specimen temperature %.1f K sits outside the %.0f K to %.0f K band the "
            "referenced thermal control method covers; the instrument calibration "
            "does not reach the article"
            % (temperature, REFERENCE_TEMPERATURE_BAND_K[0], REFERENCE_TEMPERATURE_BAND_K[1])
        )

    coverage = spectral_coverage(case.get("measurement_bands"), temperature)
    detail["spectral_coverage"] = coverage
    if not _at_least(coverage, MIN_SPECTRAL_COVERAGE):
        findings.append(
            "measured bands span %.1f%% of the blackbody exitance at %.0f K, below "
            "the %.0f%% a normal emittance average needs; extend the scan rather "
            "than the claim"
            % (coverage * 100.0, temperature, MIN_SPECTRAL_COVERAGE * 100.0)
        )

    if route == REDUCTION_SPECTRAL:
        emittance = band_weighted_emittance(case.get("measurement_bands"), temperature)
    else:
        reflectance = case.get("hemispherical_reflectance")
        if reflectance is None:
            raise ValueError(
                "method %s reduces through Kirchhoff and needs "
                "hemispherical_reflectance" % method
            )
        emittance = emittance_from_reflectance(
            reflectance, case.get("hemispherical_transmittance", 0.0)
        )
    detail["reduction_route"] = route
    detail["normal_emittance"] = emittance

    in_band = within_declared_band(emittance, case.get("declared_emittance_band"))
    detail["within_declared_band"] = in_band
    if not in_band:
        findings.append(
            "normal emittance %.4f falls outside the band the coverglass drawing "
            "declares" % emittance
        )

    uncertainty_met = _at_most(reported_uncertainty, required_uncertainty)
    if not uncertainty_met:
        findings.append(
            "reported uncertainty %.4f exceeds the required %.4f"
            % (reported_uncertainty, required_uncertainty)
        )

    accepted = not findings
    return {
        "method": method,
        "reduction_route": route,
        "normal_emittance": emittance,
        "spectral_coverage": coverage,
        "specimen_temperature_k": temperature,
        "uncertainty_met": uncertainty_met,
        "detail": detail,
        "verdict": EMITTANCE_ACCEPTED if accepted else EMITTANCE_NOT_ACCEPTED,
        "accepted": accepted,
        "findings": findings,
    }
