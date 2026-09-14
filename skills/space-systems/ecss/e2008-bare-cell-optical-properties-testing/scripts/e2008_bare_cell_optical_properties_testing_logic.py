#!/usr/bin/env python3
"""Optical property testing of a bare solar cell.

Anchor: ECSS-E-ST-20-08C clause 7.5.6. The procedure below is a
paraphrase into implementable steps; no standard text is reproduced.

A bare cell is judged optically by two different measurements that get
quoted together and mean different things.

The first is a reflectance scan. A spectrophotometer sweeps the cell
front surface across a wavelength band and returns a reflected fraction
at each point. The single number the thermal and current budgets want
is not any one of those points but their average weighted by the
spectral irradiance that actually falls on the cell, because a high
reflectance where there is no light to reflect costs nothing. What the
scan owes, therefore, is coverage: it has to span the declared band and
it has to step finely enough that the trapezoidal average between two
samples is not inventing the shape of the curve between them.

The second is the coverglass gain. The same cell is measured bare and
again with its coverglass fitted, and the ratio of the two short-circuit
currents is the gain. A coverglass with a matched antireflective stack
returns slightly more current than the bare cell; an unmatched or
clouded one returns less. The gain is therefore a signed statement about
the glass and the cell together, and it cannot be recovered from the
reflectance scan of the bare surface alone.

The band, the sample step, the reflectance ceiling and the gain floor
below are a declared policy, not physical constants: a project
substitutes its own.

Standard library only, offline, deterministic.
"""

from __future__ import annotations

import math

SCAN_INADEQUATE = "reflectance-scan-inadequate"
COVERGLASS_GAIN_NOT_MEASURED = "coverglass-gain-not-measured"
OPTICAL_PERFORMANCE_DEFICIENT = "bare-cell-optical-performance-deficient"
OPTICAL_PERFORMANCE_ACCEPTED = "bare-cell-optical-performance-accepted"

DEFAULT_OPTICAL_POLICY = {
    "band_start_nm": 400.0,
    "band_end_nm": 1800.0,
    "max_sample_gap_nm": 50.0,
    "min_scan_points": 8,
    "max_band_reflectance": 0.12,
    "min_coverglass_gain": 0.98,
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


def validate_optical_policy(policy):
    """Check an optical-acceptance policy is complete and self-consistent."""
    if not isinstance(policy, dict):
        raise ValueError("policy must be a mapping, got %r" % (policy,))
    start = _require_positive("band_start_nm", policy.get("band_start_nm"))
    end = _require_positive("band_end_nm", policy.get("band_end_nm"))
    if end <= start:
        raise ValueError(
            "band_end_nm %g must be above band_start_nm %g" % (end, start)
        )
    _require_positive("max_sample_gap_nm", policy.get("max_sample_gap_nm"))
    _require_count("min_scan_points", policy.get("min_scan_points"))
    ceiling = _require_number(
        "max_band_reflectance", policy.get("max_band_reflectance")
    )
    if not 0.0 < ceiling <= 1.0:
        raise ValueError(
            "max_band_reflectance must sit inside (0, 1], got %r" % (ceiling,)
        )
    _require_positive("min_coverglass_gain", policy.get("min_coverglass_gain"))
    return policy


def normalise_reflectance_scan(scan):
    """Validate and order a reflectance scan into wavelength-ascending pairs.

    Each sample is a (wavelength_nm, reflected_fraction) pair. The
    reflected fraction is a fraction, never a percentage, so anything
    outside 0 to 1 is a unit error rather than a measurement.
    """
    if not isinstance(scan, (list, tuple)):
        raise ValueError("scan must be a sequence of samples, got %r" % (scan,))
    if len(scan) < 2:
        raise ValueError("a reflectance scan needs at least two samples")
    seen = {}
    for sample in scan:
        if not isinstance(sample, (list, tuple)) or len(sample) != 2:
            raise ValueError(
                "each sample must be a (wavelength_nm, reflectance) pair, got %r"
                % (sample,)
            )
        wavelength = _require_positive("sample wavelength_nm", sample[0])
        reflectance = _require_number("sample reflectance", sample[1])
        if reflectance < 0.0 or reflectance > 1.0:
            raise ValueError(
                "reflectance must be a fraction between 0 and 1, got %r"
                % (sample[1],)
            )
        if wavelength in seen:
            raise ValueError(
                "wavelength %g nm appears twice in the scan" % (wavelength,)
            )
        seen[wavelength] = reflectance
    return tuple((w, seen[w]) for w in sorted(seen))


def scan_band_span_nm(scan):
    """First and last wavelength the scan actually reaches."""
    ordered = normalise_reflectance_scan(scan)
    return (ordered[0][0], ordered[-1][0])


def max_sample_gap_nm(scan):
    """Widest step between two neighbouring samples in the scan."""
    ordered = normalise_reflectance_scan(scan)
    return max(
        ordered[index + 1][0] - ordered[index][0]
        for index in range(len(ordered) - 1)
    )


def scan_covers_band(scan, policy=DEFAULT_OPTICAL_POLICY):
    """True when the scan reaches both edges of the declared band."""
    validate_optical_policy(policy)
    start, end = scan_band_span_nm(scan)
    return _at_most(start, float(policy["band_start_nm"])) and _at_least(
        end, float(policy["band_end_nm"])
    )


def band_averaged_reflectance(scan, spectral_weights=None):
    """Reflectance averaged over the band, weighted by spectral irradiance.

    Trapezoidal over the sampled wavelengths. With no weights supplied
    every wavelength counts equally, which is a wavelength average, not
    a solar-weighted one -- useful for a bare comparison, wrong for a
    current budget.
    """
    ordered = normalise_reflectance_scan(scan)
    if spectral_weights is None:
        weights = [1.0] * len(ordered)
    else:
        if not isinstance(spectral_weights, (list, tuple)):
            raise ValueError(
                "spectral_weights must be a sequence, got %r" % (spectral_weights,)
            )
        if len(spectral_weights) != len(ordered):
            raise ValueError(
                "spectral_weights holds %d entries for %d scan samples"
                % (len(spectral_weights), len(ordered))
            )
        weights = [
            _require_positive("spectral weight", weight)
            for weight in spectral_weights
        ]
    numerator = 0.0
    denominator = 0.0
    for index in range(len(ordered) - 1):
        step = ordered[index + 1][0] - ordered[index][0]
        low_weight = weights[index]
        high_weight = weights[index + 1]
        numerator += (
            0.5
            * (ordered[index][1] * low_weight + ordered[index + 1][1] * high_weight)
            * step
        )
        denominator += 0.5 * (low_weight + high_weight) * step
    if denominator <= 0.0:
        raise ValueError("the weighted band has zero width and cannot be averaged")
    return numerator / denominator


def effective_absorptance(band_reflectance):
    """Fraction of the incident band the bare cell front surface takes in."""
    reflectance = _require_number("band_reflectance", band_reflectance)
    if reflectance < 0.0 or reflectance > 1.0:
        raise ValueError(
            "band_reflectance must be a fraction between 0 and 1, got %r"
            % (band_reflectance,)
        )
    return 1.0 - reflectance


def coverglass_gain(bare_short_circuit_a, covered_short_circuit_a):
    """Ratio of covered to bare short-circuit current for the same cell."""
    bare = _require_positive("bare_short_circuit_a", bare_short_circuit_a)
    covered = _require_positive("covered_short_circuit_a", covered_short_circuit_a)
    return covered / bare


def coverglass_gain_percent(gain):
    """The gain expressed as a signed percentage change against the bare cell."""
    value = _require_positive("gain", gain)
    return (value - 1.0) * 100.0


def assess_bare_cell_optical_properties(case, policy=DEFAULT_OPTICAL_POLICY):
    """Full clause 7.5.6 judgement for one bare cell optical measurement."""
    if not isinstance(case, dict):
        raise ValueError("case must be a mapping, got %r" % (case,))
    validate_optical_policy(policy)
    if "reflectance_scan" not in case:
        raise ValueError(
            "case is missing reflectance_scan; an absent scan is not an empty one"
        )
    ordered = normalise_reflectance_scan(case["reflectance_scan"])
    weights = case.get("spectral_weights")
    reflectance = band_averaged_reflectance(ordered, weights)
    span = scan_band_span_nm(ordered)
    gap = max_sample_gap_nm(ordered)

    findings = []
    result = {
        "scan_points": len(ordered),
        "scan_span_nm": span,
        "max_sample_gap_nm": gap,
        "solar_weighted": weights is not None,
        "band_averaged_reflectance": reflectance,
        "effective_absorptance": effective_absorptance(reflectance),
        "coverglass_gain": None,
        "coverglass_gain_percent": None,
        "findings": findings,
    }

    scan_ok = True
    if len(ordered) < int(policy["min_scan_points"]):
        scan_ok = False
        findings.append(
            "the scan holds %d samples, below the %d the policy asks for"
            % (len(ordered), int(policy["min_scan_points"]))
        )
    if not scan_covers_band(ordered, policy):
        scan_ok = False
        findings.append(
            "the scan spans %.1f to %.1f nm and does not reach the %.1f to "
            "%.1f nm band"
            % (
                span[0],
                span[1],
                float(policy["band_start_nm"]),
                float(policy["band_end_nm"]),
            )
        )
    if not _at_most(gap, float(policy["max_sample_gap_nm"])):
        scan_ok = False
        findings.append(
            "the widest sample step is %.1f nm, above the %.1f nm the "
            "trapezoidal average stays honest over"
            % (gap, float(policy["max_sample_gap_nm"]))
        )
    if not scan_ok:
        result["verdict"] = SCAN_INADEQUATE
        return result

    if not _at_most(reflectance, float(policy["max_band_reflectance"])):
        findings.append(
            "the band-averaged reflectance %.4f stands above the %.4f ceiling"
            % (reflectance, float(policy["max_band_reflectance"]))
        )

    coverglass = case.get("coverglass")
    if coverglass is None:
        findings.append(
            "no covered-cell measurement is present, so the coverglass gain "
            "is not established by the bare scan alone"
        )
        result["verdict"] = COVERGLASS_GAIN_NOT_MEASURED
        return result
    if not isinstance(coverglass, dict):
        raise ValueError("coverglass must be a mapping, got %r" % (coverglass,))

    gain = coverglass_gain(
        coverglass.get("bare_short_circuit_a"),
        coverglass.get("covered_short_circuit_a"),
    )
    result["coverglass_gain"] = gain
    result["coverglass_gain_percent"] = coverglass_gain_percent(gain)
    if not _at_least(gain, float(policy["min_coverglass_gain"])):
        findings.append(
            "the coverglass gain %.4f falls under the %.4f floor, so the glass "
            "costs the cell current rather than returning it"
            % (gain, float(policy["min_coverglass_gain"]))
        )

    result["verdict"] = (
        OPTICAL_PERFORMANCE_ACCEPTED if not findings else OPTICAL_PERFORMANCE_DEFICIENT
    )
    return result
