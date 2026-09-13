#!/usr/bin/env python3
"""Ambient conducted-level baseline check, ECSS-E-ST-20-07C clause 5.2.2.4.

Paraphrased procedure, no verbatim standard text. The clause requires the
conducted background on the power-leads to be recorded with the
unit-under-test removed and a load standing in its place. This module turns
that into a deterministic grading:

  dummy-load    -> representative substitution or rejection
  configuration -> valid baseline or rejection
  lead sweeps   -> headroom per frequency -> category
  leads         -> worst point per lead -> governing lead

stdlib only, offline, deterministic.
"""

from __future__ import annotations

import math

# Decibel comparison tolerance. Headroom is a difference of two float
# levels, so an exactly-satisfied requirement can land a few units in the
# last place short. The tolerance absorbs that representation error only;
# it never lowers the required separation.
DB_TOL = 1e-9

# Conventional separation between the recorded background and the
# applicable conducted-emission-limit, decibels.
DEFAULT_REQUIRED_HEADROOM_DB = 6.0

# Default fraction by which the dummy-load current may depart from the
# unit's nominal bus current and still be representative.
DEFAULT_CURRENT_TOLERANCE_FRACTION = 0.10

# Relative tolerance on the bus voltage match between baseline and graded run.
BUS_VOLTAGE_REL_TOL = 0.02

# Line-impedance-stabilisation-network inductances recognized for spacecraft
# power-lead measurements, microhenry.
RECOGNIZED_LISN_INDUCTANCE_UH = (5.0, 50.0)

RECOGNIZED_LEADS = (
    "primary-positive",
    "primary-return",
    "secondary-positive",
    "secondary-return",
)

CATEGORY_COMPLIANT = "compliant"
CATEGORY_MARGINAL = "marginal"
CATEGORY_EXCEEDANCE = "exceedance"
CATEGORIES = (CATEGORY_COMPLIANT, CATEGORY_MARGINAL, CATEGORY_EXCEEDANCE)


def _number(record, key, where):
    if key not in record:
        raise ValueError("%s: missing required field %r" % (where, key))
    value = record[key]
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise ValueError("%s: field %r must be numeric, got %r" % (where, key, value))
    value = float(value)
    if math.isnan(value) or math.isinf(value):
        raise ValueError("%s: field %r must be finite, got %r" % (where, key, value))
    return value


def _flag(record, key, where):
    if key not in record:
        raise ValueError("%s: missing required field %r" % (where, key))
    value = record[key]
    if not isinstance(value, bool):
        raise ValueError("%s: field %r must be a boolean, got %r" % (where, key, value))
    return value


def at_least(value_db, requirement_db, tol_db=DB_TOL):
    """True when value meets the requirement, absorbing float error only."""
    if value_db >= requirement_db:
        return True
    return math.isclose(value_db, requirement_db, rel_tol=0.0, abs_tol=tol_db)


def current_tolerance_band(nominal_current_a, tolerance_fraction=DEFAULT_CURRENT_TOLERANCE_FRACTION):
    """Return the acceptable dummy-load current band around the nominal draw."""
    nominal = _number({"v": nominal_current_a}, "v", "nominal_current_a")
    fraction = _number({"v": tolerance_fraction}, "v", "tolerance_fraction")
    if nominal <= 0.0:
        raise ValueError("nominal_current_a must be > 0, got %g" % nominal)
    if not 0.0 < fraction < 1.0:
        raise ValueError(
            "tolerance_fraction must lie in (0, 1), got %g" % fraction
        )
    return (nominal * (1.0 - fraction), nominal * (1.0 + fraction))


def validate_dummy_load(load, unit, tolerance_fraction=DEFAULT_CURRENT_TOLERANCE_FRACTION):
    """Validate the substitution load against the unit it replaces.

    load: resistive (bool), current_a, bus_voltage_v.
    unit: nominal_current_a, bus_voltage_v.
    """
    where = "dummy_load"
    if not isinstance(load, dict):
        raise ValueError("%s: record must be a mapping" % where)
    if not isinstance(unit, dict):
        raise ValueError("unit: record must be a mapping")
    if not _flag(load, "resistive", where):
        raise ValueError(
            "%s: the substitution load must be resistive; a switching or "
            "inductive load injects its own conducted spectrum" % where
        )
    current = _number(load, "current_a", where)
    if current <= 0.0:
        raise ValueError("%s: current_a must be > 0, got %g" % (where, current))
    load_voltage = _number(load, "bus_voltage_v", where)
    if load_voltage <= 0.0:
        raise ValueError("%s: bus_voltage_v must be > 0, got %g" % (where, load_voltage))

    nominal = _number(unit, "nominal_current_a", "unit")
    unit_voltage = _number(unit, "bus_voltage_v", "unit")
    if unit_voltage <= 0.0:
        raise ValueError("unit: bus_voltage_v must be > 0, got %g" % unit_voltage)
    if not math.isclose(
        load_voltage, unit_voltage, rel_tol=BUS_VOLTAGE_REL_TOL, abs_tol=0.0
    ):
        raise ValueError(
            "%s: bus voltage %g V does not match the graded run voltage %g V"
            % (where, load_voltage, unit_voltage)
        )

    low, high = current_tolerance_band(nominal, tolerance_fraction)
    inside = (low <= current <= high) or math.isclose(
        current, low, rel_tol=1e-12, abs_tol=DB_TOL
    ) or math.isclose(current, high, rel_tol=1e-12, abs_tol=DB_TOL)
    if not inside:
        raise ValueError(
            "%s: current %g A is outside the representative band %g-%g A for a "
            "nominal draw of %g A" % (where, current, low, high, nominal)
        )
    return {
        "resistive": True,
        "current_a": current,
        "bus_voltage_v": load_voltage,
        "nominal_current_a": nominal,
        "current_band_a": (low, high),
    }


def validate_conducted_configuration(config, reference_bandwidth_hz=None):
    """Validate the baseline run configuration and return a normalized copy."""
    where = "configuration"
    if not isinstance(config, dict):
        raise ValueError("%s: record must be a mapping" % where)
    if _flag(config, "unit_connected", where):
        raise ValueError(
            "%s: the unit-under-test must be disconnected for the baseline run"
            % where
        )
    if not _flag(config, "dummy_load_installed", where):
        raise ValueError(
            "%s: a dummy-load must replace the unit; open leads unload the supply"
            % where
        )
    if not _flag(config, "support_equipment_powered", where):
        raise ValueError(
            "%s: the support-equipment must stay operating during the baseline run"
            % where
        )
    inductance = _number(config, "lisn_inductance_uh", where)
    recognized = any(
        math.isclose(inductance, value, rel_tol=1e-9, abs_tol=DB_TOL)
        for value in RECOGNIZED_LISN_INDUCTANCE_UH
    )
    if not recognized:
        raise ValueError(
            "%s: unrecognized line-impedance-stabilisation-network inductance "
            "%g uH; recognized: %s"
            % (where, inductance, ", ".join("%g" % v for v in RECOGNIZED_LISN_INDUCTANCE_UH))
        )
    bandwidth = _number(config, "receiver_bandwidth_hz", where)
    if bandwidth <= 0.0:
        raise ValueError(
            "%s: receiver_bandwidth_hz must be > 0, got %g" % (where, bandwidth)
        )
    if reference_bandwidth_hz is not None:
        reference = _number(
            {"v": reference_bandwidth_hz}, "v", "%s.reference_bandwidth_hz" % where
        )
        if reference <= 0.0:
            raise ValueError("%s: reference bandwidth must be > 0" % where)
        if not math.isclose(bandwidth, reference, rel_tol=1e-9, abs_tol=DB_TOL):
            raise ValueError(
                "%s: baseline receiver bandwidth %g Hz does not match the graded "
                "run bandwidth %g Hz" % (where, bandwidth, reference)
            )
    return {
        "unit_connected": False,
        "dummy_load_installed": True,
        "support_equipment_powered": True,
        "lisn_inductance_uh": inductance,
        "receiver_bandwidth_hz": bandwidth,
    }


def normalize_lead(lead):
    """Return the recognized lead designation for a raw designation."""
    if not isinstance(lead, str):
        raise ValueError("lead designation must be a string, got %r" % (lead,))
    key = lead.strip().lower()
    if key not in RECOGNIZED_LEADS:
        raise ValueError(
            "unrecognized lead %r; recognized: %s" % (lead, ", ".join(RECOGNIZED_LEADS))
        )
    return key


def validate_lead_sweep(points):
    """Validate one lead's background sweep and return normalized points."""
    where = "lead_sweep"
    if not isinstance(points, (list, tuple)):
        raise ValueError("%s: points must be a list" % where)
    if len(points) == 0:
        raise ValueError("%s: at least one recorded point is required" % where)
    out = []
    previous = None
    for index, point in enumerate(points):
        tag = "%s[%d]" % (where, index)
        if not isinstance(point, dict):
            raise ValueError("%s: point must be a mapping" % tag)
        frequency = _number(point, "frequency_hz", tag)
        if frequency <= 0.0:
            raise ValueError("%s: frequency_hz must be > 0, got %g" % (tag, frequency))
        if previous is not None and frequency <= previous:
            raise ValueError(
                "%s: frequencies must increase strictly (%g Hz after %g Hz)"
                % (tag, frequency, previous)
            )
        previous = frequency
        out.append(
            {
                "frequency_hz": frequency,
                "background_dbuv": _number(point, "background_dbuv", tag),
                "limit_dbuv": _number(point, "limit_dbuv", tag),
            }
        )
    return out


def point_headroom_db(point):
    """Headroom of a single point: applicable limit minus recorded background."""
    return point["limit_dbuv"] - point["background_dbuv"]


def categorize_point(point, required_headroom_db=DEFAULT_REQUIRED_HEADROOM_DB):
    """Categorize one lead point by the headroom it leaves."""
    required = _number({"v": required_headroom_db}, "v", "required_headroom_db")
    if required < 0.0:
        raise ValueError("required_headroom_db must be >= 0, got %g" % required)
    headroom = point_headroom_db(point)
    if headroom <= 0.0:
        # Background at or above the applicable limit leaves nothing to grade.
        return CATEGORY_EXCEEDANCE
    if at_least(headroom, required):
        return CATEGORY_COMPLIANT
    return CATEGORY_MARGINAL


def grade_lead(lead, points, required_headroom_db=DEFAULT_REQUIRED_HEADROOM_DB):
    """Grade one power-lead sweep and reduce it to its worst-case point."""
    designation = normalize_lead(lead)
    sweep = validate_lead_sweep(points)
    graded = []
    counts = dict((category, 0) for category in CATEGORIES)
    for point in sweep:
        category = categorize_point(point, required_headroom_db)
        counts[category] += 1
        graded.append(
            {
                "frequency_hz": point["frequency_hz"],
                "background_dbuv": point["background_dbuv"],
                "limit_dbuv": point["limit_dbuv"],
                "headroom_db": point_headroom_db(point),
                "category": category,
            }
        )
    worst = min(graded, key=lambda g: g["headroom_db"])
    return {
        "lead": designation,
        "points": graded,
        "counts": counts,
        "worst_case": worst,
        "usable": counts[CATEGORY_EXCEEDANCE] == 0,
    }


def governing_lead(lead_reports):
    """Return the lead report holding the smallest worst-case headroom."""
    if not isinstance(lead_reports, (list, tuple)) or len(lead_reports) == 0:
        raise ValueError("governing_lead: at least one graded lead is required")
    return min(lead_reports, key=lambda r: r["worst_case"]["headroom_db"])


def assess_ambient_conducted_level(
    config,
    load,
    unit,
    lead_sweeps,
    required_headroom_db=DEFAULT_REQUIRED_HEADROOM_DB,
    current_tolerance_fraction=DEFAULT_CURRENT_TOLERANCE_FRACTION,
    reference_bandwidth_hz=None,
):
    """Full clause 5.2.2.4 ambient conducted baseline assessment.

    lead_sweeps: mapping of lead designation -> list of sweep points.
    """
    configuration = validate_conducted_configuration(config, reference_bandwidth_hz)
    substitution = validate_dummy_load(load, unit, current_tolerance_fraction)
    if not isinstance(lead_sweeps, dict):
        raise ValueError("lead_sweeps: must be a mapping of lead -> points")
    if len(lead_sweeps) == 0:
        raise ValueError("lead_sweeps: at least one power-lead must be recorded")

    reports = []
    for lead in sorted(lead_sweeps):
        reports.append(grade_lead(lead, lead_sweeps[lead], required_headroom_db))

    findings = []
    limitations = []
    for report in reports:
        for entry in report["points"]:
            if entry["category"] == CATEGORY_EXCEEDANCE:
                findings.append(
                    "background exceedance on %s at %g Hz: %.1f dB headroom"
                    % (report["lead"], entry["frequency_hz"], entry["headroom_db"])
                )
            elif entry["category"] == CATEGORY_MARGINAL:
                limitations.append(
                    "marginal headroom %.1f dB on %s at %g Hz"
                    % (entry["headroom_db"], report["lead"], entry["frequency_hz"])
                )

    governing = governing_lead(reports)
    return {
        "configuration": configuration,
        "substitution": substitution,
        "leads": reports,
        "governing_lead": governing["lead"],
        "governing_point": governing["worst_case"],
        "findings": findings,
        "limitations": limitations,
        "verdict": "usable-baseline" if not findings else "baseline-rejected",
    }
