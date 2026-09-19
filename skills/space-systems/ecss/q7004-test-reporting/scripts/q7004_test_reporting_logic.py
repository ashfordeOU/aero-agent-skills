#!/usr/bin/env python3
"""Test report completeness for an ECSS thermal test.

Anchor: ECSS-Q-ST-70-04C, the reporting clauses: the conditions the test
actually ran at, the results obtained, and the anomalies seen along the
way, each in the agreed format. The procedure below is a paraphrase into
implementable steps; no standard text is reproduced.

A report is judged on three things and only the first is obvious. It has
to carry every field the format asks for; a field present but empty is
missing, because an empty cell reads as a zero to everyone downstream and
as an omission to nobody.

It has to be internally consistent. An anomaly logged at cycle 140 in a
report that ran 100 cycles is one of the two numbers being wrong, and the
report cannot say which.

And it has to be honest about its own anomalies. A pass verdict standing
over an open anomaly is the single most expensive thing a report can do,
because it is read as clearance.

Standard library only, offline, deterministic.
"""

from __future__ import annotations

import math

IDENTIFICATION = "identification"
CONDITIONS = "conditions"
RESULTS = "results"
ANOMALIES = "anomalies"
DEVIATIONS = "deviations"
REPORT_SECTIONS = (IDENTIFICATION, CONDITIONS, RESULTS, ANOMALIES, DEVIATIONS)

OPEN = "open"
CLOSED_NO_IMPACT = "closed-no-impact"
CLOSED_REPAIRED = "closed-repaired"
CLOSED_RETESTED = "closed-retested"
DISPOSITIONS = (OPEN, CLOSED_NO_IMPACT, CLOSED_REPAIRED, CLOSED_RETESTED)

RELEASABLE = "releasable"
INCOMPLETE = "incomplete"
BLOCKED = "blocked"

DEFAULT_REPORT_FORMAT = {
    "required_fields": {
        IDENTIFICATION: ("report_id", "item_id", "test_facility", "test_date"),
        CONDITIONS: (
            "temperature_min_k",
            "temperature_max_k",
            "cycle_count",
            "dwell_s",
            "pressure_pa",
        ),
        RESULTS: (
            "verdict",
            "inspection_outcome",
            "functional_outcome",
            "mass_change_pct",
        ),
        DEVIATIONS: ("deviation_summary",),
    },
    "anomaly_fields": (
        "anomaly_id",
        "description",
        "occurred_at_cycle",
        "disposition",
    ),
    "pass_verdicts": ("pass", "passed"),
}

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


def _require_positive_int(name, value):
    if not isinstance(value, int) or isinstance(value, bool) or value < 1:
        raise ValueError(
            "%s must be an integer of at least 1, got %r" % (name, value)
        )
    return value


def _require_non_negative_int(name, value):
    if not isinstance(value, int) or isinstance(value, bool) or value < 0:
        raise ValueError(
            "%s must be an integer of at least 0, got %r" % (name, value)
        )
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


def is_supplied(value):
    """A value counts as supplied only when it carries information.

    Absent, None and a blank string are all missing. A zero is not: a
    measured zero is a result and must never be treated as an omission.
    """
    if value is None:
        return False
    if isinstance(value, str):
        return bool(value.strip())
    if isinstance(value, (list, tuple, dict, set)):
        return len(value) > 0
    return True


def validate_report_format(report_format):
    """Check the format names fields for every section it will be graded on."""
    _require_mapping("report_format", report_format)
    required = _require_mapping(
        "report_format required_fields", report_format.get("required_fields")
    )
    graded = tuple(section for section in REPORT_SECTIONS if section != ANOMALIES)
    missing = set(graded) - set(required)
    if missing:
        raise ValueError(
            "report_format required_fields is missing: %s" % ", ".join(sorted(missing))
        )
    for section, fields in required.items():
        _require_choice("required_fields section", section, REPORT_SECTIONS)
        if not isinstance(fields, (list, tuple)) or not fields:
            raise ValueError("section %s must require at least one field" % section)
        if len(set(fields)) != len(fields):
            raise ValueError("section %s repeats a field" % section)
    anomaly_fields = report_format.get("anomaly_fields")
    if not isinstance(anomaly_fields, (list, tuple)) or not anomaly_fields:
        raise ValueError("report_format must name the anomaly fields")
    if "disposition" not in anomaly_fields:
        raise ValueError(
            "anomaly_fields must include disposition; an anomaly with no "
            "disposition cannot be closed or carried"
        )
    verdicts = report_format.get("pass_verdicts")
    if not isinstance(verdicts, (list, tuple)) or not verdicts:
        raise ValueError("report_format must name the verdict strings that read as a pass")
    return report_format


def missing_fields(section, content, report_format=DEFAULT_REPORT_FORMAT):
    """Fields the format asks for that the section does not actually carry."""
    validate_report_format(report_format)
    _require_choice("section", section, REPORT_SECTIONS)
    if section == ANOMALIES:
        raise ValueError("the anomalies section is graded per record, not per field")
    _require_mapping("content", content)
    required = report_format["required_fields"][section]
    return [field for field in required if not is_supplied(content.get(field))]


def section_completeness(section, content, report_format=DEFAULT_REPORT_FORMAT):
    """Fraction of the section's required fields that carry information."""
    validate_report_format(report_format)
    gaps = missing_fields(section, content, report_format)
    required = report_format["required_fields"][section]
    return (len(required) - len(gaps)) / float(len(required))


def validate_conditions(content):
    """Check the recorded conditions describe a test that could have run."""
    _require_mapping("conditions", content)
    low = _require_number("temperature_min_k", content.get("temperature_min_k"))
    high = _require_number("temperature_max_k", content.get("temperature_max_k"))
    if low <= 0.0 or high <= 0.0:
        raise ValueError("recorded temperatures must be absolute and above zero")
    if high <= low:
        raise ValueError(
            "temperature_max_k %g K must be above temperature_min_k %g K" % (high, low)
        )
    cycles = _require_positive_int("cycle_count", content.get("cycle_count"))
    dwell = _require_number("dwell_s", content.get("dwell_s"))
    if dwell <= 0.0:
        raise ValueError("dwell_s must be greater than zero, got %r" % (dwell,))
    return {
        "temperature_min_k": low,
        "temperature_max_k": high,
        "span_k": high - low,
        "cycle_count": cycles,
        "dwell_s": dwell,
    }


def validate_anomaly(record, cycle_count, report_format=DEFAULT_REPORT_FORMAT):
    """One anomaly record: complete, dispositioned, and inside the test."""
    validate_report_format(report_format)
    _require_mapping("anomaly", record)
    gaps = [
        field
        for field in report_format["anomaly_fields"]
        if not is_supplied(record.get(field))
    ]
    if gaps:
        raise ValueError(
            "anomaly %r is missing: %s"
            % (record.get("anomaly_id", "<unidentified>"), ", ".join(gaps))
        )
    disposition = _require_choice(
        "disposition", record.get("disposition"), DISPOSITIONS
    )
    at_cycle = _require_non_negative_int(
        "occurred_at_cycle", record.get("occurred_at_cycle")
    )
    consistent = at_cycle <= cycle_count
    return {
        "anomaly_id": record["anomaly_id"],
        "occurred_at_cycle": at_cycle,
        "disposition": disposition,
        "is_open": disposition == OPEN,
        "within_test": consistent,
    }


def document_test_report(report, report_format=DEFAULT_REPORT_FORMAT):
    """Grade one test report: completeness, consistency, and releasability."""
    validate_report_format(report_format)
    _require_mapping("report", report)

    sections = {}
    all_gaps = []
    required_total = 0
    supplied_total = 0
    for section in REPORT_SECTIONS:
        if section == ANOMALIES:
            continue
        content = report.get(section)
        if content is None:
            content = {}
        _require_mapping("report %s" % section, content)
        gaps = missing_fields(section, content, report_format)
        required = report_format["required_fields"][section]
        required_total += len(required)
        supplied_total += len(required) - len(gaps)
        sections[section] = {
            "missing": gaps,
            "completeness": section_completeness(section, content, report_format),
        }
        all_gaps.extend("%s.%s" % (section, field) for field in gaps)

    conditions = None
    if not sections[CONDITIONS]["missing"]:
        conditions = validate_conditions(report[CONDITIONS])

    raw_anomalies = report.get(ANOMALIES, [])
    if not isinstance(raw_anomalies, (list, tuple)):
        raise ValueError("report anomalies must be a list of records")
    cycle_count = conditions["cycle_count"] if conditions else 0
    anomalies = [
        validate_anomaly(record, cycle_count, report_format)
        for record in raw_anomalies
    ]
    seen = set()
    for anomaly in anomalies:
        if anomaly["anomaly_id"] in seen:
            raise ValueError(
                "anomaly_id %r appears twice; two findings under one identifier "
                "close together" % anomaly["anomaly_id"]
            )
        seen.add(anomaly["anomaly_id"])

    open_anomalies = [a for a in anomalies if a["is_open"]]
    out_of_range = (
        [a for a in anomalies if not a["within_test"]] if conditions else []
    )
    completeness = supplied_total / float(required_total)

    verdict_field = (report.get(RESULTS) or {}).get("verdict")
    claims_pass = (
        isinstance(verdict_field, str)
        and verdict_field.strip().lower() in tuple(report_format["pass_verdicts"])
    )

    findings = []
    duties = []
    if all_gaps:
        findings.append(
            "the format asks for fields this report does not carry: %s"
            % ", ".join(all_gaps)
        )
    for anomaly in out_of_range:
        findings.append(
            "anomaly %s is logged at cycle %d in a test of %d cycles; one of the "
            "two numbers is wrong and the report cannot say which"
            % (anomaly["anomaly_id"], anomaly["occurred_at_cycle"], cycle_count)
        )
    if claims_pass and open_anomalies:
        findings.append(
            "the results section reads as a pass while %d anomaly record(s) are "
            "still open; the report will be read as clearance"
            % len(open_anomalies)
        )
    if conditions is None:
        findings.append(
            "the conditions section is incomplete, so nothing in this report can be "
            "checked against the test that was actually run"
        )

    if all_gaps:
        verdict = INCOMPLETE
    elif open_anomalies or out_of_range:
        verdict = BLOCKED
    else:
        verdict = RELEASABLE

    duties.append(
        "report an empty field as an omission, never as a zero; a blank cell and a "
        "measured zero are different results"
    )
    if open_anomalies:
        duties.append(
            "carry every open anomaly into the verdict statement rather than into "
            "an annex nobody reads"
        )

    return {
        "sections": sections,
        "missing_fields": all_gaps,
        "completeness": completeness,
        "conditions": conditions,
        "anomaly_count": len(anomalies),
        "open_anomaly_count": len(open_anomalies),
        "inconsistent_anomaly_count": len(out_of_range),
        "claims_pass": claims_pass,
        "verdict": verdict,
        "findings": findings,
        "duties": duties,
    }
