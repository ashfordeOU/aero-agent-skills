#!/usr/bin/env python3
"""Purpose of recording the cut-on when a high reflectance band is characterised.

Anchor: ECSS-E-ST-20-08C clause 8.7.5.2.2. The procedure below is a
paraphrase into implementable steps; no standard text is reproduced.

A coating with a high reflectance band is bought for where that band
sits, not for how tall it is. The plateau reflectance says how well the
coating rejects inside the band; it says nothing about where the band
starts. The cut-on is the one number that places the short-wavelength
edge, and it is recorded because three separate budgets are written
against that edge:

    thermal       an optical solar reflector or a reflecting coverglass
                  earns its place by what it rejects. The band edge
                  decides how much of the incoming spectrum falls
                  inside the rejection band at all.
    power         the same edge, moved the wrong way, reflects light
                  the cell underneath was meant to convert. A rejection
                  band that creeps into the photo-response band buys
                  thermal margin with array current.
    repeatability a deposition run is accepted on where its edge landed.
                  Two lots with the same plateau and a fifteen
                  nanometre edge shift are two different coatings, and
                  only the cut-on shows it.

The clause therefore asks for one wavelength, but that wavelength is
only worth recording under conditions:

    A band has to exist.        Halving a reflectance that never rises
                                to a high reflectance level places a
                                cut-on on a feature that is not a band.
    The scan has to bracket it. A curve that starts inside the edge, or
                                stops before the plateau, cannot place
                                the edge it claims to have placed.
    The edge has to be judged.  A cut-on nobody compares with the edge
                                the budgets assume is a number in a
                                report, not a result.

The direction the edge moved is part of the answer. A cut-on below the
required edge widens the rejection band into wavelengths the cell wants
and costs array current; a cut-on above it leaves the low end of the
required rejection band uncovered and costs thermal margin. Reporting
only the magnitude of the miss leaves the two indistinguishable and
they have opposite fixes.

The drivers, thresholds and tolerances below are a declared policy, not
a physical constant: a project substitutes its own.

Standard library only, offline, deterministic.
"""

from __future__ import annotations

import math

# Driver that wants the cut-on -> the quantity the cut-on feeds it.
CUT_ON_DRIVERS = {
    "coverglass-uv-reflector-band": "uv-rejection-band-edge-placement",
    "optical-solar-reflector-thermal-budget": "reflector-absorptance-budget",
    "cell-photo-response-band-protection": "in-band-reflection-power-loss",
    "coating-lot-acceptance-repeatability": "coating-deposition-band-repeatability",
    "post-environmental-coating-degradation": "band-edge-drift-after-exposure",
}

RECOGNISED_DRIVERS = tuple(sorted(CUT_ON_DRIVERS))

COMMON_OBJECTIVE = "high-reflectance-band-edge-traceability"

CUT_ON_CHARACTERISATION_NOT_REQUIRED = "cut-on-characterisation-not-required"
CUT_ON_NOT_MEASURED = "cut-on-not-measured"
CUT_ON_MEASUREMENT_INADEQUATE = "cut-on-measurement-inadequate"
CUT_ON_PLACEMENT_SHORTFALL = "cut-on-placement-shortfall"
CUT_ON_CHARACTERISED = "cut-on-characterised"

VERDICTS = (
    CUT_ON_CHARACTERISATION_NOT_REQUIRED,
    CUT_ON_NOT_MEASURED,
    CUT_ON_MEASUREMENT_INADEQUATE,
    CUT_ON_PLACEMENT_SHORTFALL,
    CUT_ON_CHARACTERISED,
)

EDGE_ON_TARGET = "edge-on-target"
EDGE_BELOW_REQUIRED = "edge-below-required-costs-array-current"
EDGE_ABOVE_REQUIRED = "edge-above-required-costs-thermal-margin"

DEFAULT_CUT_ON_PURPOSE_POLICY = {
    "min_plateau_reflectance": 0.60,
    "band_edge_tolerance_nm": 10.0,
    "min_scan_margin_nm": 20.0,
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


def _require_fraction(name, value):
    number = _require_number(name, value)
    if number < 0.0 or number > 1.0:
        raise ValueError(
            "%s must be a fraction between zero and one, got %r" % (name, value)
        )
    return number


def _require_identifier(name, value):
    if not isinstance(value, str) or not value.strip():
        raise ValueError("%s must be a non-empty string, got %r" % (name, value))
    return value.strip()


def _close(value, other):
    return math.isclose(value, other, rel_tol=_REL_TOL, abs_tol=_ABS_TOL)


def _at_least(value, limit):
    """value >= limit, absorbing floating-point representation error."""
    return value >= limit or _close(value, limit)


def _at_most(value, limit):
    """value <= limit, absorbing floating-point representation error."""
    return value <= limit or _close(value, limit)


def validate_cut_on_purpose_policy(policy):
    """Check the declared thresholds the purpose question is judged against."""
    if policy is None:
        policy = DEFAULT_CUT_ON_PURPOSE_POLICY
    if not isinstance(policy, dict):
        raise ValueError("policy must be a mapping, got %r" % (policy,))
    plateau = _require_fraction(
        "min_plateau_reflectance",
        policy.get(
            "min_plateau_reflectance",
            DEFAULT_CUT_ON_PURPOSE_POLICY["min_plateau_reflectance"],
        ),
    )
    if plateau <= 0.0:
        raise ValueError(
            "min_plateau_reflectance must be above zero; a threshold of zero "
            "calls every feature a high reflectance band"
        )
    tolerance = _require_positive(
        "band_edge_tolerance_nm",
        policy.get(
            "band_edge_tolerance_nm",
            DEFAULT_CUT_ON_PURPOSE_POLICY["band_edge_tolerance_nm"],
        ),
    )
    margin = _require_positive(
        "min_scan_margin_nm",
        policy.get(
            "min_scan_margin_nm",
            DEFAULT_CUT_ON_PURPOSE_POLICY["min_scan_margin_nm"],
        ),
    )
    return {
        "min_plateau_reflectance": plateau,
        "band_edge_tolerance_nm": tolerance,
        "min_scan_margin_nm": margin,
    }


def group_band_drivers(drivers):
    """Group the declared drivers and map each to the quantity it feeds."""
    if drivers is None:
        drivers = []
    if isinstance(drivers, str) or not isinstance(drivers, (list, tuple)):
        raise ValueError(
            "drivers must be a list of declared driver names, got %r" % (drivers,)
        )
    grouped = []
    seen = set()
    for driver in drivers:
        name = _require_identifier("driver", driver)
        if name not in CUT_ON_DRIVERS:
            raise ValueError(
                "driver %r is not one of the recognised cut-on drivers (%s); an "
                "unrecognised driver is refused rather than ignored"
                % (name, ", ".join(RECOGNISED_DRIVERS))
            )
        if name in seen:
            raise ValueError("driver %r is declared twice" % name)
        seen.add(name)
        grouped.append({"driver": name, "objective": CUT_ON_DRIVERS[name]})
    objectives = [entry["objective"] for entry in grouped]
    if grouped:
        objectives.append(COMMON_OBJECTIVE)
    return {"drivers": grouped, "objectives": tuple(objectives)}


def band_is_high_reflectance(plateau_reflectance, policy=None):
    """Is the plateau tall enough for there to be a band edge worth placing?"""
    checked = validate_cut_on_purpose_policy(policy)
    plateau = _require_fraction("plateau_reflectance", plateau_reflectance)
    return _at_least(plateau, checked["min_plateau_reflectance"])


def absorbed_fraction_in_band(plateau_reflectance):
    """What the coating does not reject inside the band -- the thermal load."""
    return 1.0 - _require_fraction("plateau_reflectance", plateau_reflectance)


def band_edge_offset_nm(measured_cut_on_nm, required_edge_nm):
    """Signed distance from the required band edge to the measured cut-on."""
    measured = _require_positive("measured_cut_on_nm", measured_cut_on_nm)
    required = _require_positive("required_edge_nm", required_edge_nm)
    return measured - required


def band_edge_direction(offset_nm, tolerance_nm):
    """Name which way an out-of-tolerance edge moved, and what it costs."""
    offset = _require_number("offset_nm", offset_nm)
    tolerance = _require_positive("tolerance_nm", tolerance_nm)
    if _at_most(abs(offset), tolerance):
        return EDGE_ON_TARGET
    return EDGE_BELOW_REQUIRED if offset < 0.0 else EDGE_ABOVE_REQUIRED


def band_coverage_fraction(
    cut_on_nm, band_end_nm, required_start_nm, required_end_nm
):
    """Fraction of the required rejection band the measured band covers."""
    cut_on = _require_positive("cut_on_nm", cut_on_nm)
    band_end = _require_positive("band_end_nm", band_end_nm)
    required_start = _require_positive("required_start_nm", required_start_nm)
    required_end = _require_positive("required_end_nm", required_end_nm)
    if not band_end > cut_on:
        raise ValueError(
            "band_end_nm must sit above the cut-on, got %g and %g"
            % (cut_on, band_end)
        )
    if not required_end > required_start:
        raise ValueError(
            "required_end_nm must sit above required_start_nm, got %g and %g"
            % (required_start, required_end)
        )
    overlap = min(band_end, required_end) - max(cut_on, required_start)
    if overlap <= 0.0:
        return 0.0
    return overlap / (required_end - required_start)


def assess_scan_bracket(measurement, policy=None):
    """Does the scan reach far enough either side to place the edge it claims?"""
    checked = validate_cut_on_purpose_policy(policy)
    if not isinstance(measurement, dict):
        raise ValueError("measurement must be a mapping, got %r" % (measurement,))
    cut_on = _require_positive("cut_on_nm", measurement.get("cut_on_nm"))
    scan_start = _require_positive("scan_start_nm", measurement.get("scan_start_nm"))
    scan_end = _require_positive("scan_end_nm", measurement.get("scan_end_nm"))
    plateau_wavelength = _require_positive(
        "plateau_wavelength_nm", measurement.get("plateau_wavelength_nm")
    )
    if not scan_end > scan_start:
        raise ValueError(
            "scan_end_nm must sit above scan_start_nm, got %g and %g"
            % (scan_start, scan_end)
        )

    margin = checked["min_scan_margin_nm"]
    shortfalls = []
    below_margin = cut_on - scan_start
    if not _at_least(below_margin, margin):
        shortfalls.append(
            "the scan starts %g nm below the cut-on, short of the %g nm needed "
            "to show the curve rising into the edge" % (below_margin, margin)
        )
    if not plateau_wavelength > cut_on:
        shortfalls.append(
            "the band plateau at %g nm is not above the cut-on at %g nm, so the "
            "curve the cut-on was read off is not a rising edge"
            % (plateau_wavelength, cut_on)
        )
    if not _at_least(scan_end, plateau_wavelength):
        shortfalls.append(
            "the scan stops at %g nm, before the band plateau at %g nm, so the "
            "absolute reflectance the half level came from was never recorded"
            % (scan_end, plateau_wavelength)
        )
    return {
        "adequate": not shortfalls,
        "below_edge_margin_nm": below_margin,
        "shortfalls": shortfalls,
    }


def assess_cut_on_purpose(case, policy=None):
    """Say why the cut-on is wanted here and whether the report delivers it."""
    checked = validate_cut_on_purpose_policy(policy)
    if not isinstance(case, dict):
        raise ValueError("case must be a mapping, got %r" % (case,))
    coating_id = _require_identifier("coating_id", case.get("coating_id"))

    grouped = group_band_drivers(case.get("drivers"))
    plateau = _require_fraction(
        "plateau_reflectance", case.get("plateau_reflectance")
    )
    required_start = _require_positive(
        "required_band_start_nm", case.get("required_band_start_nm")
    )
    required_end = _require_positive(
        "required_band_end_nm", case.get("required_band_end_nm")
    )
    if not required_end > required_start:
        raise ValueError(
            "required_band_end_nm must sit above required_band_start_nm, got %g "
            "and %g" % (required_start, required_end)
        )
    required_edge = _require_positive(
        "required_edge_nm", case.get("required_edge_nm", required_start)
    )

    absorbed = absorbed_fraction_in_band(plateau)
    band_exists = _at_least(plateau, checked["min_plateau_reflectance"])

    result = {
        "coating_id": coating_id,
        "drivers": grouped["drivers"],
        "objectives": grouped["objectives"],
        "plateau_reflectance": plateau,
        "absorbed_fraction_in_band": absorbed,
        "band_is_high_reflectance": band_exists,
        "required_edge_nm": required_edge,
        "band_edge_tolerance_nm": checked["band_edge_tolerance_nm"],
        "cut_on_nm": None,
        "band_edge_offset_nm": None,
        "band_edge_margin_nm": None,
        "band_edge_direction": None,
        "band_coverage_fraction": None,
        "findings": [],
    }

    if not grouped["drivers"] or not band_exists:
        if not grouped["drivers"]:
            result["findings"].append(
                "no driver declares a use for the band edge, so the cut-on has "
                "no budget to serve and the plateau reflectance already answers "
                "what the coating rejects"
            )
        if not band_exists:
            result["findings"].append(
                "the plateau reaches only %g, under the %g a high reflectance "
                "band has to reach; halving it would place an edge on a feature "
                "that is not a band"
                % (plateau, checked["min_plateau_reflectance"])
            )
        result["verdict"] = CUT_ON_CHARACTERISATION_NOT_REQUIRED
        return result

    measurement = case.get("measurement")
    if measurement is None:
        result["verdict"] = CUT_ON_NOT_MEASURED
        result["findings"].append(
            "%d driver(s) want the band edge and the plateau is high enough for "
            "one to exist, but no cut-on was measured; the coating is accepted "
            "on a plateau that says nothing about where the band starts"
            % len(grouped["drivers"])
        )
        return result

    bracket = assess_scan_bracket(measurement, policy)
    cut_on = _require_positive("cut_on_nm", measurement.get("cut_on_nm"))
    band_end = _require_positive("band_end_nm", measurement.get("band_end_nm"))
    result["cut_on_nm"] = cut_on
    result["scan_below_edge_margin_nm"] = bracket["below_edge_margin_nm"]

    if not bracket["adequate"]:
        result["verdict"] = CUT_ON_MEASUREMENT_INADEQUATE
        result["findings"].extend(bracket["shortfalls"])
        return result

    coverage = band_coverage_fraction(
        cut_on, band_end, required_start, required_end
    )
    offset = band_edge_offset_nm(cut_on, required_edge)
    tolerance = checked["band_edge_tolerance_nm"]
    margin = tolerance - abs(offset)
    direction = band_edge_direction(offset, tolerance)

    result["band_coverage_fraction"] = coverage
    result["band_edge_offset_nm"] = offset
    result["band_edge_margin_nm"] = margin
    result["band_edge_direction"] = direction

    if direction == EDGE_ON_TARGET:
        result["verdict"] = CUT_ON_CHARACTERISED
        result["findings"].append(
            "the cut-on sits at %.4f nm against a required edge of %.4f nm, "
            "inside the %.4f nm tolerance, and the measured band covers %.4f of "
            "the required rejection band"
            % (cut_on, required_edge, tolerance, coverage)
        )
        return result

    result["verdict"] = CUT_ON_PLACEMENT_SHORTFALL
    if direction == EDGE_BELOW_REQUIRED:
        result["findings"].append(
            "the cut-on sits %.4f nm below the required edge, past the %.4f nm "
            "tolerance; the rejection band has widened into wavelengths the "
            "cell was meant to convert and the miss is paid in array current"
            % (abs(offset), tolerance)
        )
    else:
        result["findings"].append(
            "the cut-on sits %.4f nm above the required edge, past the %.4f nm "
            "tolerance; the low end of the required rejection band is "
            "uncovered and the miss is paid in thermal margin"
            % (abs(offset), tolerance)
        )
    return result
