#!/usr/bin/env python3
"""Definition of the reflectance cut-on wavelength of a coating.

Anchor: ECSS-E-ST-20-08C clause 8.7.5.2.1. The procedure below is a
paraphrase into implementable steps; no standard text is reproduced.

The cut-on is the short-wavelength point at which a measured
reflectance curve reaches half of the absolute measured reflectance of
the band. It is a definition rather than a threshold, and three of its
four words carry weight:

    absolute      the reflectance the instrument measured in absolute
                  terms, not a ratio against a reference mirror. Half
                  of a relative curve is half of the wrong number.
    measured      the peak the scan actually recorded inside the band
                  of interest, not a design plateau or a datasheet
                  figure. The half level moves with the article.
    short         the rising edge below the band, never the falling
    wavelength    edge above it. A plateau has two half-reflectance
                  crossings and only the lower one is the cut-on.

Fixing the level is therefore the first half of the work: take the
absolute measured reflectance across the band of interest, halve it,
and that number -- not a fixed percentage -- is the level the crossing
is read at. A band window narrows which part of the scan supplies the
peak, and moving that window moves the half level and so the cut-on.

Reading the crossing is the second half. The scan is a set of samples,
so the crossing almost never lands on one. The pair of samples that
bracket the half level fixes the answer, and the crossing wavelength is
linearly interpolated between them. That bracket is also the honest
resolution of the result: a cut-on read between samples twenty
nanometres apart is not known to a nanometre, however many decimals the
interpolation prints.

Two situations have no cut-on rather than a default one. A scan whose
shortest wavelength already sits above the half level has its edge
below the scanned range, so the number does not exist inside the
measurement. A band whose absolute reflectance is too low to be a high
reflectance band at all has nothing worth halving.

Reflectance here is a fraction between zero and one. A scan recorded in
per cent is normalised before it arrives; halving a percentage curve
against a fractional level silently yields a cut-on off the end of the
band.

Standard library only, offline, deterministic.
"""

from __future__ import annotations

import math

CUT_ON_DETERMINED = "cut-on-determined"
CUT_ON_BAND_TOO_WEAK = "reflectance-band-below-threshold"
CUT_ON_EDGE_OUTSIDE_SCAN = "cut-on-outside-the-scanned-range"
CUT_ON_RESOLUTION_INSUFFICIENT = "cut-on-resolution-insufficient"

VERDICTS = (
    CUT_ON_DETERMINED,
    CUT_ON_BAND_TOO_WEAK,
    CUT_ON_EDGE_OUTSIDE_SCAN,
    CUT_ON_RESOLUTION_INSUFFICIENT,
)

HALF_FRACTION = 0.5

DEFAULT_CUT_ON_POLICY = {
    "min_absolute_reflectance": 0.30,
    "max_bracket_width_nm": 5.0,
}

MIN_SCAN_POINTS = 2

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


def _close(value, other):
    return math.isclose(value, other, rel_tol=_REL_TOL, abs_tol=_ABS_TOL)


def _at_least(value, limit):
    """value >= limit, absorbing floating-point representation error."""
    return value >= limit or _close(value, limit)


def _at_most(value, limit):
    """value <= limit, absorbing floating-point representation error."""
    return value <= limit or _close(value, limit)


def validate_reflectance_scan(scan):
    """Check a measured reflectance scan and return it normalised.

    A scan is a sequence of (wavelength_nm, reflectance) pairs with
    strictly increasing wavelength and reflectance as a fraction of
    unity. A curve still in per cent is refused rather than rescaled,
    because guessing the unit would silently move every level derived
    from it.
    """
    if isinstance(scan, dict) or not isinstance(scan, (list, tuple)):
        raise ValueError(
            "scan must be a sequence of (wavelength_nm, reflectance) pairs, "
            "got %r" % (scan,)
        )
    if len(scan) < MIN_SCAN_POINTS:
        raise ValueError(
            "a scan needs at least %d samples to bracket a crossing, got %d"
            % (MIN_SCAN_POINTS, len(scan))
        )
    points = []
    previous_wavelength = None
    for index, point in enumerate(scan):
        if isinstance(point, dict):
            wavelength = point.get("wavelength_nm")
            reflectance = point.get("reflectance")
        elif isinstance(point, (list, tuple)) and len(point) == 2:
            wavelength, reflectance = point
        else:
            raise ValueError(
                "scan sample %d must be a (wavelength_nm, reflectance) pair or "
                "a mapping carrying both, got %r" % (index, point)
            )
        wavelength = _require_positive("sample %d wavelength_nm" % index, wavelength)
        reflectance = _require_number("sample %d reflectance" % index, reflectance)
        if reflectance < 0.0:
            raise ValueError(
                "sample %d reflectance is negative; a measured reflectance "
                "cannot be below zero" % index
            )
        if reflectance > 1.0:
            raise ValueError(
                "sample %d reflectance is above one; the scan looks to be in "
                "per cent and must be normalised to a fraction before the half "
                "level is taken" % index
            )
        if previous_wavelength is not None and not wavelength > previous_wavelength:
            raise ValueError(
                "scan wavelengths must strictly increase; sample %d at %g nm "
                "does not advance on %g nm"
                % (index, wavelength, previous_wavelength)
            )
        previous_wavelength = wavelength
        points.append((wavelength, reflectance))
    return tuple(points)


def validate_band_window(window, scan):
    """Check the band window that supplies the absolute reflectance."""
    points = validate_reflectance_scan(scan)
    if window is None:
        return (points[0][0], points[-1][0])
    if isinstance(window, dict):
        window = (window.get("start_nm"), window.get("end_nm"))
    if not isinstance(window, (list, tuple)) or len(window) != 2:
        raise ValueError(
            "band window must be a (start_nm, end_nm) pair, got %r" % (window,)
        )
    start = _require_positive("band window start_nm", window[0])
    end = _require_positive("band window end_nm", window[1])
    if not end > start:
        raise ValueError(
            "band window end_nm must be above start_nm, got %g and %g"
            % (start, end)
        )
    inside = [wl for wl, _ in points if _at_least(wl, start) and _at_most(wl, end)]
    if not inside:
        raise ValueError(
            "band window %g to %g nm contains no scan sample; there is nothing "
            "in it to take an absolute reflectance from" % (start, end)
        )
    return (start, end)


def _peak_index(points, window):
    start, end = window
    best_index = None
    for index, (wavelength, reflectance) in enumerate(points):
        if not (_at_least(wavelength, start) and _at_most(wavelength, end)):
            continue
        if best_index is None or reflectance > points[best_index][1]:
            best_index = index
    return best_index


def absolute_measured_reflectance(scan, window=None):
    """Peak reflectance the scan actually recorded inside the band window."""
    points = validate_reflectance_scan(scan)
    checked_window = validate_band_window(window, scan)
    index = _peak_index(points, checked_window)
    return points[index][1]


def peak_wavelength_nm(scan, window=None):
    """Wavelength at which the absolute measured reflectance was recorded."""
    points = validate_reflectance_scan(scan)
    checked_window = validate_band_window(window, scan)
    index = _peak_index(points, checked_window)
    return points[index][0]


def half_reflectance_level(scan, window=None):
    """Half of the absolute measured reflectance -- the crossing level."""
    return HALF_FRACTION * absolute_measured_reflectance(scan, window)


def describe_cut_on(scan, window=None):
    """Locate the short-wavelength half-reflectance crossing in full."""
    points = validate_reflectance_scan(scan)
    checked_window = validate_band_window(window, scan)
    peak_index = _peak_index(points, checked_window)
    peak_value = points[peak_index][1]
    if peak_value <= 0.0:
        raise ValueError(
            "the band window records no reflectance at all; there is no "
            "absolute measured reflectance to halve"
        )
    half_level = HALF_FRACTION * peak_value

    first_wavelength, first_reflectance = points[0]
    if _close(first_reflectance, half_level):
        return {
            "cut_on_wavelength_nm": first_wavelength,
            "absolute_reflectance": peak_value,
            "half_level": half_level,
            "peak_wavelength_nm": points[peak_index][0],
            "bracket_nm": (first_wavelength, first_wavelength),
            "bracket_width_nm": 0.0,
            "edge_slope_per_nm": 0.0,
            "on_sample": True,
            "band_window_nm": checked_window,
        }
    if first_reflectance > half_level:
        raise ValueError(
            "the shortest scanned wavelength %g nm already reads %g, above the "
            "%g half level; the short-wavelength edge lies below the scanned "
            "range and no cut-on exists inside this measurement"
            % (first_wavelength, first_reflectance, half_level)
        )

    for index in range(peak_index):
        low_wavelength, low_reflectance = points[index]
        high_wavelength, high_reflectance = points[index + 1]
        if low_reflectance >= half_level:
            continue
        if not _at_least(high_reflectance, half_level):
            continue
        span = high_reflectance - low_reflectance
        if span <= 0.0:
            raise ValueError(
                "the bracketing samples at %g and %g nm do not rise, so the "
                "crossing cannot be placed between them"
                % (low_wavelength, high_wavelength)
            )
        step = high_wavelength - low_wavelength
        if _close(high_reflectance, half_level):
            # The crossing landed on a measured sample, so nothing was
            # interpolated and the bracket carries no width.
            cut_on = high_wavelength
            on_sample = True
            bracket = (high_wavelength, high_wavelength)
            width = 0.0
        else:
            fraction = (half_level - low_reflectance) / span
            cut_on = low_wavelength + fraction * step
            on_sample = False
            bracket = (low_wavelength, high_wavelength)
            width = step
        return {
            "cut_on_wavelength_nm": cut_on,
            "absolute_reflectance": peak_value,
            "half_level": half_level,
            "peak_wavelength_nm": points[peak_index][0],
            "bracket_nm": bracket,
            "bracket_width_nm": width,
            "edge_slope_per_nm": span / step,
            "on_sample": on_sample,
            "band_window_nm": checked_window,
        }

    raise ValueError(
        "no short-wavelength crossing of the %g half level was found below the "
        "band peak at %g nm" % (half_level, points[peak_index][0])
    )


def cut_on_wavelength_nm(scan, window=None):
    """The cut-on: short-wavelength crossing of half the absolute reflectance."""
    return describe_cut_on(scan, window)["cut_on_wavelength_nm"]


def validate_cut_on_policy(policy):
    """Check the declared thresholds the determination is judged against."""
    if policy is None:
        policy = DEFAULT_CUT_ON_POLICY
    if not isinstance(policy, dict):
        raise ValueError("policy must be a mapping, got %r" % (policy,))
    minimum = _require_positive(
        "min_absolute_reflectance",
        policy.get(
            "min_absolute_reflectance",
            DEFAULT_CUT_ON_POLICY["min_absolute_reflectance"],
        ),
    )
    if minimum > 1.0:
        raise ValueError(
            "min_absolute_reflectance is a fraction of unity and cannot exceed "
            "one, got %g" % minimum
        )
    bracket = _require_positive(
        "max_bracket_width_nm",
        policy.get(
            "max_bracket_width_nm", DEFAULT_CUT_ON_POLICY["max_bracket_width_nm"]
        ),
    )
    return {
        "min_absolute_reflectance": minimum,
        "max_bracket_width_nm": bracket,
    }


def assess_cut_on_determination(scan, policy=None, window=None):
    """Decide whether a scan yields a defensible cut-on, and report it."""
    checked_policy = validate_cut_on_policy(policy)
    points = validate_reflectance_scan(scan)
    checked_window = validate_band_window(window, scan)
    peak_index = _peak_index(points, checked_window)
    peak_value = points[peak_index][1]

    findings = []
    if not _at_least(peak_value, checked_policy["min_absolute_reflectance"]):
        findings.append(
            "the absolute measured reflectance in the band is %g, under the %g "
            "a high reflectance band has to reach; halving it would place a "
            "cut-on on a band that is not there"
            % (peak_value, checked_policy["min_absolute_reflectance"])
        )
        return {
            "verdict": CUT_ON_BAND_TOO_WEAK,
            "cut_on_wavelength_nm": None,
            "absolute_reflectance": peak_value,
            "half_level": HALF_FRACTION * peak_value,
            "band_window_nm": checked_window,
            "findings": findings,
        }

    try:
        described = describe_cut_on(scan, window)
    except ValueError as error:
        findings.append(str(error))
        return {
            "verdict": CUT_ON_EDGE_OUTSIDE_SCAN,
            "cut_on_wavelength_nm": None,
            "absolute_reflectance": peak_value,
            "half_level": HALF_FRACTION * peak_value,
            "band_window_nm": checked_window,
            "findings": findings,
        }

    result = dict(described)
    if _at_most(
        described["bracket_width_nm"], checked_policy["max_bracket_width_nm"]
    ):
        result["verdict"] = CUT_ON_DETERMINED
        findings.append(
            "the cut-on sits at %.4f nm, where the curve reaches %g, half of "
            "the %g absolute measured reflectance of the band"
            % (
                described["cut_on_wavelength_nm"],
                described["half_level"],
                described["absolute_reflectance"],
            )
        )
    else:
        result["verdict"] = CUT_ON_RESOLUTION_INSUFFICIENT
        findings.append(
            "the crossing is bracketed by samples %g nm apart, wider than the "
            "%g nm the cut-on is meant to be resolved to; the interpolated "
            "%.4f nm is not known to the decimals it prints"
            % (
                described["bracket_width_nm"],
                checked_policy["max_bracket_width_nm"],
                described["cut_on_wavelength_nm"],
            )
        )
    result["findings"] = findings
    return result
