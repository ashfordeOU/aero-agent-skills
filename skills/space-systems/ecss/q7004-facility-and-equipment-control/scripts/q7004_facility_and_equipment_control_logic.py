#!/usr/bin/env python3
"""Facility, fixture and instrumentation control for an ECSS thermal test.

Anchor: ECSS-Q-ST-70-04C, the quality assurance clauses covering the test
facility, the fixturing and the measuring equipment. The procedure below
is a paraphrase into implementable steps; no standard text is reproduced.

Three things have to be under control before a chamber door closes, and
they fail in different ways.

The instrumentation fails quietly. A sensor inside its calibration
interval can still be the wrong sensor: what matters is the ratio between
the tolerance the test has to hold and the uncertainty the instrument
brings. A ratio below the house minimum means the measurement is
arguing with itself.

The facility fails at the edges. A chamber whose capability only just
reaches the required extreme has no margin for the overshoot it will
take to get there, so the envelope is checked with a margin and not on
equality.

The fixture fails by succeeding. A fixture heavy against the item drives
the item's thermal response, and the profile that gets run is the
fixture's, not the specimen's.

Days are handled as integer day numbers supplied by the caller: no clock,
no locale, no file access.

Standard library only, offline, deterministic.
"""

from __future__ import annotations

import math

CONTROLLING_SENSOR = "controlling-sensor"
MONITORING_SENSOR = "monitoring-sensor"
CHAMBER_CONTROLLER = "chamber-controller"
INSTRUMENT_ROLES = (CONTROLLING_SENSOR, MONITORING_SENSOR, CHAMBER_CONTROLLER)

VALID = "valid"
DUE_SOON = "due-soon"
EXPIRED = "expired"

READY = "ready"
NOT_READY = "not-ready"

DEFAULT_FACILITY_POLICY = {
    "min_test_accuracy_ratio": 4.0,
    "calibration_warning_days": 30,
    "envelope_margin_k": 5.0,
    "max_fixture_to_item_mass_ratio": 2.0,
    "min_temperature_sensors": 2,
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


def _require_int(name, value):
    if not isinstance(value, int) or isinstance(value, bool):
        raise ValueError("%s must be an integer, got %r" % (name, value))
    return value


def _require_positive_int(name, value):
    number = _require_int(name, value)
    if number < 1:
        raise ValueError("%s must be at least 1, got %r" % (name, value))
    return number


def _require_bool(name, value):
    if not isinstance(value, bool):
        raise ValueError("%s must be a boolean, got %r" % (name, value))
    return value


def _require_choice(name, value, allowed):
    if value not in allowed:
        raise ValueError(
            "%s must be one of %s, got %r" % (name, ", ".join(allowed), value)
        )
    return value


def _require_mapping(name, value):
    if not isinstance(value, dict):
        raise ValueError("%s must be a mapping, got %r" % (name, value))
    return value


def _at_least(value, limit):
    """value >= limit, absorbing floating-point representation error."""
    return value >= limit or math.isclose(
        value, limit, rel_tol=_REL_TOL, abs_tol=_ABS_TOL
    )


def validate_facility_policy(policy):
    """Check the control thresholds are present and defensible."""
    _require_mapping("policy", policy)
    ratio = _require_positive(
        "min_test_accuracy_ratio", policy.get("min_test_accuracy_ratio")
    )
    if not _at_least(ratio, 1.0):
        raise ValueError(
            "min_test_accuracy_ratio %g lets the instrument be less certain than "
            "the tolerance it measures" % ratio
        )
    _require_positive_int(
        "calibration_warning_days", policy.get("calibration_warning_days")
    )
    _require_positive("envelope_margin_k", policy.get("envelope_margin_k"))
    _require_positive(
        "max_fixture_to_item_mass_ratio",
        policy.get("max_fixture_to_item_mass_ratio"),
    )
    _require_positive_int(
        "min_temperature_sensors", policy.get("min_temperature_sensors")
    )
    return policy


def calibration_status(
    calibrated_on_day, interval_days, test_day, policy=DEFAULT_FACILITY_POLICY
):
    """Where the test day falls in an instrument's calibration interval."""
    validate_facility_policy(policy)
    calibrated = _require_int("calibrated_on_day", calibrated_on_day)
    interval = _require_positive_int("interval_days", interval_days)
    day = _require_int("test_day", test_day)
    if day < calibrated:
        raise ValueError(
            "test_day %d precedes the calibration day %d; the record cannot apply "
            "to this test" % (day, calibrated)
        )
    due_day = calibrated + interval
    days_remaining = due_day - day
    if days_remaining < 0:
        status = EXPIRED
    elif days_remaining <= policy["calibration_warning_days"]:
        status = DUE_SOON
    else:
        status = VALID
    return {
        "status": status,
        "days_remaining": days_remaining,
        "due_day": due_day,
        "is_valid": days_remaining >= 0,
    }


def test_accuracy_ratio(required_tolerance_k, instrument_uncertainty_k):
    """Tolerance the test must hold against the uncertainty measuring it."""
    tolerance = _require_positive("required_tolerance_k", required_tolerance_k)
    uncertainty = _require_positive(
        "instrument_uncertainty_k", instrument_uncertainty_k
    )
    return tolerance / uncertainty


def instrument_is_adequate(ratio, policy=DEFAULT_FACILITY_POLICY):
    """True when the accuracy ratio reaches the house minimum."""
    validate_facility_policy(policy)
    value = _require_positive("ratio", ratio)
    return _at_least(value, policy["min_test_accuracy_ratio"])


def assess_instrument(record, test_day, policy=DEFAULT_FACILITY_POLICY):
    """One instrument: role, calibration standing and accuracy ratio."""
    validate_facility_policy(policy)
    _require_mapping("instrument", record)
    tag = record.get("tag")
    if not isinstance(tag, str) or not tag.strip():
        raise ValueError("instrument tag must be a non-empty string")
    role = _require_choice("role", record.get("role"), INSTRUMENT_ROLES)
    calibration = calibration_status(
        record.get("calibrated_on_day"),
        record.get("interval_days"),
        test_day,
        policy,
    )
    ratio = test_accuracy_ratio(
        record.get("required_tolerance_k"), record.get("uncertainty_k")
    )
    adequate = instrument_is_adequate(ratio, policy)
    reasons = []
    if not calibration["is_valid"]:
        reasons.append(
            "%s is %d days past its calibration due day and cannot carry a result"
            % (tag, -calibration["days_remaining"])
        )
    elif calibration["status"] == DUE_SOON:
        reasons.append(
            "%s falls due in %d days; a long campaign will run it out mid-test"
            % (tag, calibration["days_remaining"])
        )
    if not adequate:
        reasons.append(
            "%s brings an accuracy ratio of %.2f against a minimum of %.2f, so the "
            "measurement cannot resolve the tolerance it is there to hold"
            % (tag, ratio, policy["min_test_accuracy_ratio"])
        )
    return {
        "tag": tag,
        "role": role,
        "calibration": calibration,
        "accuracy_ratio": ratio,
        "is_adequate": adequate,
        "is_usable": calibration["is_valid"] and adequate,
        "reasons": reasons,
    }


def envelope_check(
    required_min_k,
    required_max_k,
    capability_min_k,
    capability_max_k,
    policy=DEFAULT_FACILITY_POLICY,
):
    """Whether the chamber reaches the required extremes with margin to spare."""
    validate_facility_policy(policy)
    req_low = _require_positive("required_min_k", required_min_k)
    req_high = _require_positive("required_max_k", required_max_k)
    cap_low = _require_positive("capability_min_k", capability_min_k)
    cap_high = _require_positive("capability_max_k", capability_max_k)
    if req_high <= req_low:
        raise ValueError(
            "required_max_k %g K must be above required_min_k %g K"
            % (req_high, req_low)
        )
    if cap_high <= cap_low:
        raise ValueError(
            "capability_max_k %g K must be above capability_min_k %g K"
            % (cap_high, cap_low)
        )
    margin = policy["envelope_margin_k"]
    cold_margin = req_low - cap_low
    hot_margin = cap_high - req_high
    cold_ok = _at_least(cold_margin, margin)
    hot_ok = _at_least(hot_margin, margin)
    reasons = []
    if not cold_ok:
        reasons.append(
            "the cold end leaves %.2f K of chamber margin against the %.2f K the "
            "policy asks for" % (cold_margin, margin)
        )
    if not hot_ok:
        reasons.append(
            "the hot end leaves %.2f K of chamber margin against the %.2f K the "
            "policy asks for" % (hot_margin, margin)
        )
    return {
        "cold_margin_k": cold_margin,
        "hot_margin_k": hot_margin,
        "is_adequate": cold_ok and hot_ok,
        "reasons": reasons,
    }


def fixture_check(
    fixture_mass_kg, item_mass_kg, attachment_conforms, policy=DEFAULT_FACILITY_POLICY
):
    """Whether the fixture carries the item without driving its response."""
    validate_facility_policy(policy)
    fixture = _require_non_negative("fixture_mass_kg", fixture_mass_kg)
    item = _require_positive("item_mass_kg", item_mass_kg)
    conforms = _require_bool("attachment_conforms", attachment_conforms)
    ratio = fixture / item
    limit = policy["max_fixture_to_item_mass_ratio"]
    within = _at_least(limit, ratio)
    reasons = []
    if not within:
        reasons.append(
            "the fixture is %.2f times the item's mass against a limit of %.2f, so "
            "the profile the item sees is the fixture's, not the chamber's"
            % (ratio, limit)
        )
    if not conforms:
        reasons.append(
            "the attachment does not conform to the declared interface, so the "
            "conducted path into the item is not the one that was analysed"
        )
    return {
        "mass_ratio": ratio,
        "attachment_conforms": conforms,
        "is_adequate": within and conforms,
        "reasons": reasons,
    }


def verify_facility_control(case, policy=DEFAULT_FACILITY_POLICY):
    """Whole-facility readiness: instruments, envelope and fixture together."""
    validate_facility_policy(policy)
    _require_mapping("case", case)
    facility = case.get("facility_id")
    if not isinstance(facility, str) or not facility.strip():
        raise ValueError("case facility_id must be a non-empty string")
    test_day = _require_int("test_day", case.get("test_day"))
    instruments = case.get("instruments")
    if not isinstance(instruments, (list, tuple)) or not instruments:
        raise ValueError("case instruments must be a non-empty list")

    assessed = [assess_instrument(record, test_day, policy) for record in instruments]
    seen = set()
    for instrument in assessed:
        if instrument["tag"] in seen:
            raise ValueError(
                "instrument tag %r appears twice; two channels under one tag cannot "
                "both be traced" % instrument["tag"]
            )
        seen.add(instrument["tag"])

    envelope = envelope_check(
        case.get("required_min_k"),
        case.get("required_max_k"),
        case.get("capability_min_k"),
        case.get("capability_max_k"),
        policy,
    )
    fixture = fixture_check(
        case.get("fixture_mass_kg"),
        case.get("item_mass_kg"),
        case.get("attachment_conforms"),
        policy,
    )

    sensors = [
        i for i in assessed if i["role"] in (CONTROLLING_SENSOR, MONITORING_SENSOR)
    ]
    controlling = [i for i in assessed if i["role"] == CONTROLLING_SENSOR]
    unusable = [i for i in assessed if not i["is_usable"]]

    findings = []
    duties = []
    for instrument in assessed:
        findings.extend(instrument["reasons"])
    findings.extend(envelope["reasons"])
    findings.extend(fixture["reasons"])
    if len(sensors) < policy["min_temperature_sensors"]:
        findings.append(
            "%d temperature sensor(s) against a minimum of %d; a single channel has "
            "nothing to be checked against"
            % (len(sensors), policy["min_temperature_sensors"])
        )
    if not controlling:
        findings.append(
            "no controlling sensor is declared, so nothing in the setup defines "
            "where the profile is actually held"
        )

    ready = (
        not unusable
        and envelope["is_adequate"]
        and fixture["is_adequate"]
        and len(sensors) >= policy["min_temperature_sensors"]
        and bool(controlling)
    )

    duties.append(
        "record the instrument tags, their calibration due days and the fixture "
        "configuration in the test report; a readiness statement nobody can trace "
        "is not evidence"
    )
    if any(i["calibration"]["status"] == DUE_SOON for i in assessed):
        duties.append(
            "re-check every due-soon instrument against the campaign end day, not "
            "against the start day"
        )

    return {
        "facility_id": facility,
        "test_day": test_day,
        "instruments": assessed,
        "instrument_count": len(assessed),
        "unusable_instrument_count": len(unusable),
        "temperature_sensor_count": len(sensors),
        "controlling_sensor_count": len(controlling),
        "envelope": envelope,
        "fixture": fixture,
        "verdict": READY if ready else NOT_READY,
        "findings": findings,
        "duties": duties,
    }
