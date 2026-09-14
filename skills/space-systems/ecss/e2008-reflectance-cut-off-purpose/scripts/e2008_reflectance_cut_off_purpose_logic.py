#!/usr/bin/env python3
"""Why the cut-off point is kept when a high reflectance band is described.

Anchor: ECSS-E-ST-20-08C clause 8.7.5.3.2. The procedure below is a
paraphrase into implementable steps; no standard text is reproduced.

A coverglass coating is specified by the band it reflects, and a band is
not described by a peak. Two coatings can both read 92 percent at their
maximum and do entirely different jobs, because one holds that level to
1150 nm and the other has given it up by 900 nm. The cut-off is the
long-wavelength edge that turns a peak into a band, and that is the
reason it is written down beside the peak rather than instead of it.

What the edge is wanted for depends on what the coating is there to do:

    solar reflector edge      where the band stops decides how much of
                              the solar spectrum is turned away
    ultraviolet rejection     the edge position is the rejection itself
    absorptance budgeting     the band edges bound the integral the
                              thermal budget is written on
    lot-to-lot monitoring     a drifting edge is a drifting deposition
                              run, visible long before the peak moves

Three outcomes are kept apart. A coating with no declared high
reflectance function needs no edge kept. A function declared with no
edge measured is a documentation gap. An edge measured on a scan that
stops inside the band is a number that is not the edge.

The band peak floor, the minimum described width and the scan margin
below are a declared policy, not a physical constant: a project
substitutes its own.

Standard library only, offline, deterministic.
"""

from __future__ import annotations

import math

# Coating function -> what the recorded cut-off feeds for that function.
BAND_FUNCTIONS = {
    "solar-reflector-band-placement": "band-placement-against-the-solar-spectrum",
    "ultraviolet-rejection-stack": "ultraviolet-rejection-edge-position",
    "coverglass-blue-red-reflector-band": "reflected-band-width-on-the-coverglass",
    "thermal-control-absorptance-budget": "solar-absorptance-integral-bounds",
    "coating-lot-to-lot-drift-monitoring": "lot-to-lot-band-edge-drift",
}

RECOGNISED_FUNCTIONS = tuple(sorted(BAND_FUNCTIONS))

COMMON_OBJECTIVE = "high-reflectance-band-description"

CUT_OFF_RECORD_NOT_REQUIRED = "cut-off-record-not-required"
CUT_OFF_NOT_RECORDED = "cut-off-not-recorded"
CUT_OFF_RECORD_INADEQUATE = "cut-off-record-inadequate"
BAND_WIDTH_SHORTFALL = "described-band-width-shortfall"
HIGH_REFLECTANCE_BAND_DESCRIBED = "high-reflectance-band-described"

DEFAULT_BAND_POLICY = {
    "min_band_peak_percent": 60.0,
    "min_described_band_width_nm": 50.0,
    "scan_margin_nm": 20.0,
    "max_credible_wavelength_nm": 2500.0,
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


def validate_band_policy(policy):
    """Check a band-description policy is complete and self-consistent."""
    if not isinstance(policy, dict):
        raise ValueError("policy must be a mapping, got %r" % (policy,))
    peak_floor = _require_positive(
        "min_band_peak_percent", policy.get("min_band_peak_percent")
    )
    if peak_floor > 100.0:
        raise ValueError(
            "min_band_peak_percent %g cannot exceed a fully reflecting band"
            % (peak_floor,)
        )
    _require_positive(
        "min_described_band_width_nm", policy.get("min_described_band_width_nm")
    )
    _require_non_negative("scan_margin_nm", policy.get("scan_margin_nm"))
    ceiling = _require_positive(
        "max_credible_wavelength_nm", policy.get("max_credible_wavelength_nm")
    )
    if ceiling <= float(policy["min_described_band_width_nm"]):
        raise ValueError(
            "max_credible_wavelength_nm %g must be wider than the %g nm minimum "
            "described band" % (ceiling, float(policy["min_described_band_width_nm"]))
        )
    return policy


def function_inventory(functions):
    """Group the declared coating functions, rejecting an unrecognised one."""
    if not isinstance(functions, (list, tuple, set, frozenset)):
        raise ValueError("functions must be a collection of coating function names")
    grouped = []
    for function in functions:
        if function not in BAND_FUNCTIONS:
            raise ValueError(
                "unknown coating function %r; recognised functions are %s"
                % (function, ", ".join(RECOGNISED_FUNCTIONS))
            )
        if function not in grouped:
            grouped.append(function)
    return tuple(sorted(grouped))


def record_objectives(functions):
    """What the kept cut-off feeds, given the declared coating functions."""
    grouped = function_inventory(functions)
    if not grouped:
        return ()
    objectives = [BAND_FUNCTIONS[function] for function in grouped]
    objectives.append(COMMON_OBJECTIVE)
    return tuple(objectives)


def band_width_nm(cut_on_nm, cut_off_nm):
    """How wide the described band is between its two half-level edges."""
    lower = _require_positive("cut_on_nm", cut_on_nm)
    upper = _require_positive("cut_off_nm", cut_off_nm)
    if not upper > lower:
        raise ValueError(
            "cut_off_nm %g must lie beyond cut_on_nm %g; the cut-off is the "
            "long-wavelength edge" % (upper, lower)
        )
    return upper - lower


def band_centre_nm(cut_on_nm, cut_off_nm):
    """The midpoint of the described band, useful for placement checks."""
    band_width_nm(cut_on_nm, cut_off_nm)
    return (float(cut_on_nm) + float(cut_off_nm)) / 2.0


def band_is_high_reflectance(peak_percent, policy=DEFAULT_BAND_POLICY):
    """True when the band is reflective enough for its edges to describe it."""
    validate_band_policy(policy)
    peak = _require_non_negative("peak_percent", peak_percent)
    return _at_least(peak, float(policy["min_band_peak_percent"]))


def scan_reaches_the_edge(scan_upper_nm, cut_off_nm, policy=DEFAULT_BAND_POLICY):
    """True when the scan ran past the cut-off by at least the policy margin."""
    validate_band_policy(policy)
    upper = _require_positive("scan_upper_nm", scan_upper_nm)
    edge = _require_positive("cut_off_nm", cut_off_nm)
    return _at_least(upper, edge + float(policy["scan_margin_nm"]))


def edge_is_credible(cut_off_nm, policy=DEFAULT_BAND_POLICY):
    """True when the reported edge sits inside the credible spectral range."""
    validate_band_policy(policy)
    edge = _require_positive("cut_off_nm", cut_off_nm)
    return _at_most(edge, float(policy["max_credible_wavelength_nm"]))


def assess_cut_off_purpose(case, policy=DEFAULT_BAND_POLICY):
    """Full clause 8.7.5.3.2 judgement for one described reflectance band."""
    if not isinstance(case, dict):
        raise ValueError("case must be a mapping, got %r" % (case,))
    validate_band_policy(policy)
    if "band_functions" not in case:
        raise ValueError(
            "case is missing band_functions; an absent inventory is not an "
            "empty one"
        )
    functions = function_inventory(case["band_functions"])
    objectives = record_objectives(case["band_functions"])

    band = case.get("band")
    if not isinstance(band, dict):
        raise ValueError("case is missing a band block")
    peak = _require_non_negative("band peak_percent", band.get("peak_percent"))
    high = band_is_high_reflectance(peak, policy)

    findings = []
    result = {
        "band_functions": functions,
        "objectives": objectives,
        "band_peak_percent": peak,
        "band_is_high_reflectance": high,
        "cut_off_nm": None,
        "cut_on_nm": None,
        "band_width_nm": None,
        "band_centre_nm": None,
        "scan_upper_nm": None,
        "scan_reaches_the_edge": None,
        "edge_is_credible": None,
        "findings": findings,
    }

    if not (functions and high):
        if not functions:
            findings.append(
                "no high reflectance function is declared for the coating, so "
                "no band needs describing"
            )
        if not high:
            findings.append(
                "the band peaks at %.3f percent, below the %.3f percent at which "
                "a coating is described as a high reflectance band"
                % (peak, float(policy["min_band_peak_percent"]))
            )
        result["required"] = False
        result["verdict"] = CUT_OFF_RECORD_NOT_REQUIRED
        return result

    result["required"] = True
    measurement = case.get("measurement")
    if measurement is None:
        findings.append(
            "the band is described as high reflectance and a function depends on "
            "its edge, but no cut-off is kept with the description"
        )
        result["verdict"] = CUT_OFF_NOT_RECORDED
        return result
    if not isinstance(measurement, dict):
        raise ValueError("measurement must be a mapping, got %r" % (measurement,))
    if measurement.get("cut_off_nm") is None:
        findings.append(
            "the measurement block carries no cut-off figure; the peak alone "
            "does not say where the band stops"
        )
        result["verdict"] = CUT_OFF_NOT_RECORDED
        return result

    cut_off = _require_positive("measurement cut_off_nm", measurement["cut_off_nm"])
    cut_on = measurement.get("cut_on_nm")
    scan_upper = _require_positive(
        "measurement scan_upper_nm", measurement.get("scan_upper_nm")
    )
    reaches = scan_reaches_the_edge(scan_upper, cut_off, policy)
    credible = edge_is_credible(cut_off, policy)

    result["cut_off_nm"] = cut_off
    result["scan_upper_nm"] = scan_upper
    result["scan_reaches_the_edge"] = reaches
    result["edge_is_credible"] = credible

    if cut_on is not None:
        cut_on = _require_positive("measurement cut_on_nm", cut_on)
        result["cut_on_nm"] = cut_on
        result["band_width_nm"] = band_width_nm(cut_on, cut_off)
        result["band_centre_nm"] = band_centre_nm(cut_on, cut_off)

    if not reaches:
        findings.append(
            "the scan stopped at %.3f nm against a cut-off of %.3f nm, short of "
            "the %.3f nm margin an edge needs to be seen rather than assumed"
            % (scan_upper, cut_off, float(policy["scan_margin_nm"]))
        )
    if not credible:
        findings.append(
            "the reported cut-off of %.3f nm is beyond the %.3f nm at which a "
            "coverglass band edge stays credible"
            % (cut_off, float(policy["max_credible_wavelength_nm"]))
        )
    if cut_on is None:
        findings.append(
            "no cut-on accompanies the cut-off, so the description states where "
            "the band stops but not how wide it is"
        )

    if findings:
        result["verdict"] = CUT_OFF_RECORD_INADEQUATE
        return result

    width = result["band_width_nm"]
    if not _at_least(width, float(policy["min_described_band_width_nm"])):
        findings.append(
            "the described band is %.3f nm wide against the %.3f nm a band has "
            "to span before its edges describe anything"
            % (width, float(policy["min_described_band_width_nm"]))
        )
        result["verdict"] = BAND_WIDTH_SHORTFALL
        return result

    result["verdict"] = HIGH_REFLECTANCE_BAND_DESCRIBED
    return result
