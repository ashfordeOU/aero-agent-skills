#!/usr/bin/env python3
"""Purpose of the spectral response measurement on a solar cell assembly.

Anchor: ECSS-E-ST-20-08C clause 6.4.3.5.1. The procedure below is a
paraphrase into implementable steps; no standard text is reproduced.

Spectral response is not measured for its own sake. The data has two
jobs downstream, and both of them are about somebody else's number:

    checking the simulator   A sun simulator does not reproduce the
                             reference spectrum exactly. How much that
                             matters depends on where the article and
                             the reference cell put their response, so
                             the same lamp is fine for one pair of cells
                             and unusable for another. The spectral
                             mismatch factor is the quantity that says
                             which, and it cannot be computed without
                             the response curves of both cells.
    supporting the error     The departure of that factor from unity is
    calculation              a term in the current measurement's
                             uncertainty budget, and the largest one a
                             well-run illuminated measurement usually
                             has. Left out, the budget looks better than
                             the measurement is.

The factor combines four curves -- the reference spectrum, the
simulator spectrum, the test article's response and the reference
cell's response -- as a ratio of four integrals. A factor of one means
the simulator's departure from the reference spectrum affects both
cells identically and cancels; anything else is a correction the
measured current needs, and an uncertainty the budget has to carry.

The wavelength grid decides what the integrals can see. A grid that
stops short of the article's response band silently drops the part of
the spectrum the article actually converts, and a coarse grid
straightens curvature the lamp puts into its output.

Standard library only, offline, deterministic.
"""

from __future__ import annotations

import math

SPECTRAL_DATA_INSUFFICIENT = "spectral-data-insufficient"
SIMULATOR_SPECTRUM_NOT_ACCEPTED = "simulator-spectrum-not-accepted"
ERROR_BUDGET_EXCEEDED = "error-budget-exceeded"
SPECTRAL_RESPONSE_SUPPORTED = "spectral-response-supported"

SERIES_NAMES = (
    "reference_spectrum",
    "simulator_spectrum",
    "test_cell_response",
    "reference_cell_response",
)

DEFAULT_SPECTRAL_POLICY = {
    "min_samples": 20,
    "max_wavelength_step_nm": 25.0,
    "band_start_nm": 350.0,
    "band_end_nm": 1800.0,
    "max_mismatch_deviation": 0.02,
    "max_combined_uncertainty_fraction": 0.03,
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


def validate_spectral_policy(policy):
    """Check a spectral-response policy is complete and self-consistent."""
    if not isinstance(policy, dict):
        raise ValueError("policy must be a mapping, got %r" % (policy,))
    samples = _require_count("min_samples", policy.get("min_samples"))
    if samples < 3:
        raise ValueError(
            "min_samples %d cannot describe a response curve" % samples
        )
    _require_positive(
        "max_wavelength_step_nm", policy.get("max_wavelength_step_nm")
    )
    start = _require_positive("band_start_nm", policy.get("band_start_nm"))
    end = _require_positive("band_end_nm", policy.get("band_end_nm"))
    if end <= start:
        raise ValueError(
            "band_end_nm %g must stand above band_start_nm %g" % (end, start)
        )
    _require_positive(
        "max_mismatch_deviation", policy.get("max_mismatch_deviation")
    )
    _require_positive(
        "max_combined_uncertainty_fraction",
        policy.get("max_combined_uncertainty_fraction"),
    )
    return policy


def validate_series(name, samples):
    """Order-check one wavelength series and reject an unusable curve."""
    if not isinstance(samples, (list, tuple)):
        raise ValueError("%s must be a sequence of wavelength-value pairs" % name)
    if len(samples) < 3:
        raise ValueError(
            "%s holds %d samples and cannot describe a curve" % (name, len(samples))
        )
    series = []
    for index, pair in enumerate(samples):
        if not isinstance(pair, (list, tuple)) or len(pair) != 2:
            raise ValueError(
                "%s sample %d must be a wavelength-value pair, got %r"
                % (name, index, pair)
            )
        wavelength = _require_positive("%s wavelength_nm %d" % (name, index), pair[0])
        value = _require_non_negative("%s value %d" % (name, index), pair[1])
        series.append((wavelength, value))
    for (w0, _), (w1, _) in zip(series, series[1:]):
        if not w1 > w0:
            raise ValueError(
                "%s is not ordered by increasing wavelength at %g nm" % (name, w0)
            )
    return tuple(series)


def sample_count(name, samples):
    """How many samples the series holds."""
    return len(validate_series(name, samples))


def max_wavelength_step_nm(name, samples):
    """Largest gap between neighbouring sampled wavelengths."""
    series = validate_series(name, samples)
    return max(w1 - w0 for (w0, _), (w1, _) in zip(series, series[1:]))


def band_span_nm(name, samples):
    """First and last wavelength the series covers."""
    series = validate_series(name, samples)
    return (series[0][0], series[-1][0])


def band_is_covered(name, samples, policy=DEFAULT_SPECTRAL_POLICY):
    """True when the series spans the whole band the policy asks for."""
    validate_spectral_policy(policy)
    start, end = band_span_nm(name, samples)
    return _at_most(start, float(policy["band_start_nm"])) and _at_least(
        end, float(policy["band_end_nm"])
    )


def shared_grid(first_name, first, second_name, second):
    """Wavelength grid two series share, refusing a mismatched pair."""
    left = validate_series(first_name, first)
    right = validate_series(second_name, second)
    if len(left) != len(right):
        raise ValueError(
            "%s holds %d samples and %s holds %d; the integrals need one grid"
            % (first_name, len(left), second_name, len(right))
        )
    for (w0, _), (w1, _) in zip(left, right):
        if not math.isclose(w0, w1, rel_tol=_REL_TOL, abs_tol=_ABS_TOL):
            raise ValueError(
                "%s and %s diverge at %g nm against %g nm"
                % (first_name, second_name, w0, w1)
            )
    return tuple(wavelength for wavelength, _ in left)


def trapezoidal_integral(name, samples):
    """Area under one series, by the trapezoidal rule."""
    series = validate_series(name, samples)
    total = 0.0
    for (w0, v0), (w1, v1) in zip(series, series[1:]):
        total += 0.5 * (v0 + v1) * (w1 - w0)
    return total


def weighted_integral(spectrum_name, spectrum, response_name, response):
    """Area under the product of a spectrum and a response on one grid."""
    grid = shared_grid(spectrum_name, spectrum, response_name, response)
    left = validate_series(spectrum_name, spectrum)
    right = validate_series(response_name, response)
    product = [
        (grid[index], left[index][1] * right[index][1])
        for index in range(len(grid))
    ]
    return trapezoidal_integral("%s times %s" % (spectrum_name, response_name), product)


def spectral_mismatch_factor(
    reference_spectrum, simulator_spectrum, test_cell_response, reference_cell_response
):
    """Correction the simulator's spectrum imposes on the measured current."""
    reference_on_reference_cell = weighted_integral(
        "reference_spectrum", reference_spectrum,
        "reference_cell_response", reference_cell_response,
    )
    simulator_on_test_cell = weighted_integral(
        "simulator_spectrum", simulator_spectrum,
        "test_cell_response", test_cell_response,
    )
    reference_on_test_cell = weighted_integral(
        "reference_spectrum", reference_spectrum,
        "test_cell_response", test_cell_response,
    )
    simulator_on_reference_cell = weighted_integral(
        "simulator_spectrum", simulator_spectrum,
        "reference_cell_response", reference_cell_response,
    )
    denominator = reference_on_test_cell * simulator_on_reference_cell
    if denominator <= 0.0:
        raise ValueError(
            "the response curves and the spectra share no overlap, so no "
            "mismatch factor exists"
        )
    return (reference_on_reference_cell * simulator_on_test_cell) / denominator


def mismatch_deviation(factor):
    """How far the mismatch factor stands from unity."""
    value = _require_positive("factor", factor)
    return abs(value - 1.0)


def mismatch_within_tolerance(factor, policy=DEFAULT_SPECTRAL_POLICY):
    """True when the simulator's spectrum needs no more than a small correction."""
    validate_spectral_policy(policy)
    return _at_most(
        mismatch_deviation(factor), float(policy["max_mismatch_deviation"])
    )


def corrected_short_circuit_current_a(measured_current_a, factor):
    """Measured current moved onto the reference spectrum."""
    measured = _require_positive("measured_current_a", measured_current_a)
    value = _require_positive("factor", factor)
    return measured / value


def combined_uncertainty_fraction(terms):
    """Independent uncertainty terms combined as a root sum of squares."""
    if not isinstance(terms, (list, tuple)):
        raise ValueError("terms must be a sequence of uncertainty fractions")
    if not terms:
        raise ValueError("an uncertainty budget with no terms is not a budget")
    total = 0.0
    for index, term in enumerate(terms):
        value = _require_non_negative("uncertainty term %d" % index, term)
        total += value * value
    return math.sqrt(total)


def assess_spectral_response_purpose(case, policy=DEFAULT_SPECTRAL_POLICY):
    """Full clause 6.4.3.5.1 judgement for one spectral response data set."""
    if not isinstance(case, dict):
        raise ValueError("case must be a mapping, got %r" % (case,))
    validate_spectral_policy(policy)
    for name in SERIES_NAMES:
        if name not in case:
            raise ValueError(
                "case is missing %s; the mismatch factor needs all four curves"
                % name
            )
        validate_series(name, case[name])

    findings = []
    result = {
        "sample_counts": {},
        "max_wavelength_steps_nm": {},
        "band_gaps": [],
        "mismatch_factor": None,
        "mismatch_deviation": None,
        "mismatch_in_tolerance": None,
        "corrected_current_a": None,
        "combined_uncertainty_fraction": None,
        "findings": findings,
    }
    for name in SERIES_NAMES:
        result["sample_counts"][name] = sample_count(name, case[name])
        result["max_wavelength_steps_nm"][name] = max_wavelength_step_nm(
            name, case[name]
        )
        if not _at_least(
            result["sample_counts"][name], int(policy["min_samples"])
        ):
            findings.append(
                "%s holds %d samples against the %d the policy asks for"
                % (name, result["sample_counts"][name], int(policy["min_samples"]))
            )
        if not _at_most(
            result["max_wavelength_steps_nm"][name],
            float(policy["max_wavelength_step_nm"]),
        ):
            findings.append(
                "%s steps %.4g nm at its coarsest against the %.4g nm limit"
                % (
                    name,
                    result["max_wavelength_steps_nm"][name],
                    float(policy["max_wavelength_step_nm"]),
                )
            )
        if not band_is_covered(name, case[name], policy):
            start, end = band_span_nm(name, case[name])
            result["band_gaps"].append(name)
            findings.append(
                "%s covers %.6g nm to %.6g nm and leaves part of the %.6g to "
                "%.6g nm band unsampled"
                % (
                    name,
                    start,
                    end,
                    float(policy["band_start_nm"]),
                    float(policy["band_end_nm"]),
                )
            )
    if findings:
        result["verdict"] = SPECTRAL_DATA_INSUFFICIENT
        return result

    factor = spectral_mismatch_factor(
        case["reference_spectrum"],
        case["simulator_spectrum"],
        case["test_cell_response"],
        case["reference_cell_response"],
    )
    deviation = mismatch_deviation(factor)
    result["mismatch_factor"] = factor
    result["mismatch_deviation"] = deviation
    result["mismatch_in_tolerance"] = mismatch_within_tolerance(factor, policy)

    measured = case.get("measured_short_circuit_current_a")
    if measured is not None:
        result["corrected_current_a"] = corrected_short_circuit_current_a(
            measured, factor
        )

    other_terms = case.get("other_uncertainty_fractions", ())
    if not isinstance(other_terms, (list, tuple)):
        raise ValueError(
            "other_uncertainty_fractions must be a sequence, got %r" % (other_terms,)
        )
    result["combined_uncertainty_fraction"] = combined_uncertainty_fraction(
        list(other_terms) + [deviation]
    )

    if not result["mismatch_in_tolerance"]:
        findings.append(
            "the simulator gives a mismatch factor of %.6g, %.4g from unity, "
            "beyond the %.4g the policy accepts without a spectrum correction"
            % (factor, deviation, float(policy["max_mismatch_deviation"]))
        )
        result["verdict"] = SIMULATOR_SPECTRUM_NOT_ACCEPTED
        return result

    if not _at_most(
        result["combined_uncertainty_fraction"],
        float(policy["max_combined_uncertainty_fraction"]),
    ):
        findings.append(
            "the combined current measurement uncertainty reaches %.4g with "
            "the mismatch term included, above the %.4g the budget allows"
            % (
                result["combined_uncertainty_fraction"],
                float(policy["max_combined_uncertainty_fraction"]),
            )
        )
        result["verdict"] = ERROR_BUDGET_EXCEEDED
        return result

    result["verdict"] = SPECTRAL_RESPONSE_SUPPORTED
    return result
