#!/usr/bin/env python3
"""Dependability of a test facility against its declared targets.

Anchor: ECSS-Q-ST-20-07 clause 5.6.6, the requirement that a test
facility carries availability and reliability targets and that its
performance against them is monitored. The procedure below is a
paraphrase into implementable steps; no standard text is reproduced.

Four things follow from what the clause is for.

Achieved and inherent availability are different quantities and both
are reported. The achieved value falls straight out of the record as
operating time over operating plus downtime. The inherent value is the
mean time between failures over that time plus the mean time to
restore, and it says what the facility would reach if none of its
downtime were logistic.

The gap between the two is the finding. A facility with good mean times
and poor achieved availability is waiting on parts, people or access
rather than breaking more often, and a reliability programme is the
wrong correction for it.

A period with no failure has no mean time between failures. The
quantity is not defined on that record, and reporting it as unbounded
lets an infinity propagate into the inherent availability and makes
every downstream comparison pass.

Repair hours drive the mean time to restore; the waiting hours around
them do not. Folding the two together turns a spares problem into an
apparent repair problem.

The target numbers below are declared test-centre values, not physical
constants: a test centre substitutes its own.

Standard library only, offline, deterministic.
"""

from __future__ import annotations

import math

NO_DEPENDABILITY_RECORD = "test-facility-no-dependability-record"
MONITORING_STALE = "test-facility-dependability-monitoring-stale"
AVAILABILITY_TARGET_MISSED = "test-facility-availability-target-missed"
RELIABILITY_TARGET_MISSED = "test-facility-reliability-target-missed"
RESTORE_TARGET_MISSED = "test-facility-restore-target-missed"
LOGISTIC_GAP_UNDER_WATCH = "test-facility-logistic-downtime-gap-under-watch"
TARGETS_MET = "test-facility-dependability-targets-met"

DEFAULT_DEPENDABILITY_TARGETS = {
    "availability_target": 0.95,
    "mtbf_target_hours": 200.0,
    "mttr_target_hours": 8.0,
    "review_interval_days": 180,
    "logistic_gap_watch": 0.02,
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


def _require_fraction(name, value):
    number = _require_number(name, value)
    if number < 0.0 or number > 1.0:
        raise ValueError("%s must sit between zero and one, got %r" % (name, value))
    return number


def _require_count(name, value):
    if isinstance(value, bool) or not isinstance(value, int):
        raise ValueError("%s must be a whole count, got %r" % (name, value))
    if value < 0:
        raise ValueError("%s must not be negative, got %r" % (name, value))
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


def _above(value, limit):
    """value > limit, and not merely by representation error."""
    return value > limit and not math.isclose(
        value, limit, rel_tol=_REL_TOL, abs_tol=_ABS_TOL
    )


def validate_dependability_targets(targets):
    """Check the availability and mean time targets the facility carries."""
    if not isinstance(targets, dict):
        raise ValueError("targets must be a mapping, got %r" % (targets,))
    availability = _require_fraction(
        "availability_target", targets.get("availability_target")
    )
    if availability <= 0.0:
        raise ValueError(
            "an availability target of zero asks nothing of the facility, "
            "got %r" % (targets.get("availability_target"),)
        )
    _require_positive("mtbf_target_hours", targets.get("mtbf_target_hours"))
    _require_positive("mttr_target_hours", targets.get("mttr_target_hours"))
    interval = _require_count(
        "review_interval_days", targets.get("review_interval_days")
    )
    if interval == 0:
        raise ValueError("review_interval_days must be greater than zero")
    _require_fraction("logistic_gap_watch", targets.get("logistic_gap_watch"))
    return targets


def validate_operating_record(record):
    """Read the facility operating record for one monitoring period."""
    if not isinstance(record, dict):
        raise ValueError("operating record must be a mapping, got %r" % (record,))
    period = _require_positive("period_hours", record.get("period_hours"))
    operating = _require_non_negative(
        "operating_hours", record.get("operating_hours")
    )
    repair = _require_non_negative("repair_hours", record.get("repair_hours"))
    waiting = _require_non_negative("waiting_hours", record.get("waiting_hours", 0.0))
    accounted = operating + repair + waiting
    if _above(accounted, period):
        raise ValueError(
            "the record accounts for %.6g hours inside a %.6g hour period"
            % (accounted, period)
        )
    failures = _require_count("failure_count", record.get("failure_count"))
    repairs = _require_count("repair_count", record.get("repair_count", failures))
    if repairs == 0 and repair > 0.0:
        raise ValueError(
            "the record logs %.6g repair hours against no repair at all" % repair
        )
    return {
        "period_hours": period,
        "operating_hours": operating,
        "repair_hours": repair,
        "waiting_hours": waiting,
        "failure_count": failures,
        "repair_count": repairs,
    }


def downtime_hours(record):
    """Total hours the facility was unavailable, repair plus waiting."""
    checked = validate_operating_record(record)
    return checked["repair_hours"] + checked["waiting_hours"]


def achieved_availability(record):
    """Operating hours over operating plus total downtime hours."""
    checked = validate_operating_record(record)
    down = downtime_hours(checked)
    denominator = checked["operating_hours"] + down
    if denominator <= 0.0:
        raise ValueError(
            "the record logs neither operating nor downtime hours, so no "
            "availability can be taken from it"
        )
    return checked["operating_hours"] / denominator


def mean_time_between_failures(record):
    """Operating hours per failure, or None on a period with no failure."""
    checked = validate_operating_record(record)
    if checked["failure_count"] == 0:
        return None
    return checked["operating_hours"] / float(checked["failure_count"])


def mean_time_to_restore(record):
    """Repair hours per repair, with the waiting hours left out."""
    checked = validate_operating_record(record)
    if checked["repair_count"] == 0:
        return None
    return checked["repair_hours"] / float(checked["repair_count"])


def inherent_availability(record):
    """Availability the mean times imply, excluding logistic delay."""
    mtbf = mean_time_between_failures(record)
    mttr = mean_time_to_restore(record)
    if mtbf is None or mttr is None:
        return None
    denominator = mtbf + mttr
    if denominator <= 0.0:
        raise ValueError("the mean times sum to zero, so no availability follows")
    return mtbf / denominator


def logistic_gap(record):
    """How much of the shortfall is waiting rather than repairing."""
    inherent = inherent_availability(record)
    if inherent is None:
        return None
    return inherent - achieved_availability(record)


def monitoring_is_current(last_review_day, as_of_day, targets=None):
    """True when the dependability record was reviewed inside its interval."""
    targets = validate_dependability_targets(
        targets or DEFAULT_DEPENDABILITY_TARGETS
    )
    day = _require_count("as_of_day", as_of_day)
    if last_review_day is None:
        return False
    last = _require_count("last_review_day", last_review_day)
    if last > day:
        raise ValueError(
            "last_review_day %d sits after as_of_day %d" % (last, day)
        )
    return (day - last) <= int(targets["review_interval_days"])


def assess_facility_dependability(case):
    """Grade a facility against its dependability targets and monitoring."""
    if not isinstance(case, dict):
        raise ValueError("case must be a mapping, got %r" % (case,))
    targets = validate_dependability_targets(
        case.get("targets") or DEFAULT_DEPENDABILITY_TARGETS
    )

    findings = []
    advisories = []
    result = {
        "achieved_availability": None,
        "inherent_availability": None,
        "mtbf_hours": None,
        "mttr_hours": None,
        "logistic_gap": None,
        "monitoring_current": False,
        "verdict": None,
        "findings": findings,
        "advisories": advisories,
    }

    record = case.get("record")
    if record is None:
        findings.append(
            "no operating record was supplied, so the facility has targets "
            "and nothing measured against them"
        )
        result["verdict"] = NO_DEPENDABILITY_RECORD
        return result

    checked = validate_operating_record(record)
    as_of_day = _require_count("as_of_day", case.get("as_of_day"))
    current = monitoring_is_current(case.get("last_review_day"), as_of_day, targets)
    result["monitoring_current"] = current
    if not current:
        findings.append(
            "the dependability record was last reviewed further back than "
            "the %d day interval, so the facility is not being monitored"
            % int(targets["review_interval_days"])
        )
        result["verdict"] = MONITORING_STALE
        return result

    result["achieved_availability"] = achieved_availability(checked)
    result["mtbf_hours"] = mean_time_between_failures(checked)
    result["mttr_hours"] = mean_time_to_restore(checked)
    result["inherent_availability"] = inherent_availability(checked)
    result["logistic_gap"] = logistic_gap(checked)

    if result["mtbf_hours"] is None:
        advisories.append(
            "the period logged no failure, so no mean time between failures "
            "is defined on it and the reliability target is not graded here"
        )

    if not _at_least(
        result["achieved_availability"], float(targets["availability_target"])
    ):
        findings.append(
            "the facility achieved %.5g availability against the %.5g target"
            % (
                result["achieved_availability"],
                float(targets["availability_target"]),
            )
        )
        result["verdict"] = AVAILABILITY_TARGET_MISSED
        return result

    if result["mtbf_hours"] is not None and not _at_least(
        result["mtbf_hours"], float(targets["mtbf_target_hours"])
    ):
        findings.append(
            "the mean time between failures reached %.5g hour(s) against the "
            "%.5g hour target"
            % (result["mtbf_hours"], float(targets["mtbf_target_hours"]))
        )
        result["verdict"] = RELIABILITY_TARGET_MISSED
        return result

    if result["mttr_hours"] is not None and not _at_most(
        result["mttr_hours"], float(targets["mttr_target_hours"])
    ):
        findings.append(
            "the mean time to restore reached %.5g hour(s) against the %.5g "
            "hour target"
            % (result["mttr_hours"], float(targets["mttr_target_hours"]))
        )
        result["verdict"] = RESTORE_TARGET_MISSED
        return result

    if result["logistic_gap"] is not None and _above(
        result["logistic_gap"], float(targets["logistic_gap_watch"])
    ):
        advisories.append(
            "the inherent availability sits %.5g above the achieved value, so "
            "the shortfall is waiting rather than failing"
            % result["logistic_gap"]
        )
        result["verdict"] = LOGISTIC_GAP_UNDER_WATCH
        return result

    result["verdict"] = TARGETS_MET
    return result
