#!/usr/bin/env python3
"""Facility test report, ECSS-Q-ST-20-07C clause 5.7.4.1.

Paraphrased clause intent, no verbatim standard text. A test centre
records, per campaign, which facility was used, in which configuration,
holding which conditions, measured by which instruments. This module
turns that record into a deterministic completeness assessment:

  mandatory sections   -> what the report does not yet say
  configuration items  -> is each one identified as an object
  condition samples    -> which stretches of the window are unevidenced
  calibration expiry   -> which readings the certificates cannot support

stdlib only, offline, deterministic.
"""

from __future__ import annotations

import math

# Comparison tolerance. Sample times and intervals are floats, so a
# sample landing exactly one interval after its predecessor can compute
# a few units in the last place over that interval. The tolerance
# absorbs that representation error only; it never lengthens the
# interval the record is kept at.
REL_TOL = 1e-12
ABS_TOL = 1e-12

REQUIRED_SECTIONS = (
    "configuration_items",
    "condition_log",
    "facility_identification",
    "instrument_list",
    "test_configuration",
)

REPORT_COMPLETE = "facility-report-complete"
REPORT_INCOMPLETE = "facility-report-incomplete"


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


def at_most(value, bound):
    """True when a value stays under an upper bound, absorbing float error."""
    if value <= bound:
        return True
    return math.isclose(value, bound, rel_tol=REL_TOL, abs_tol=ABS_TOL)


def at_least(value, bound):
    """True when a value reaches a lower bound, absorbing float error."""
    if value >= bound:
        return True
    return math.isclose(value, bound, rel_tol=REL_TOL, abs_tol=ABS_TOL)


def validate_campaign(campaign):
    """Validate the campaign window and its sampling interval."""
    where = "campaign"
    if not isinstance(campaign, dict):
        raise ValueError("%s: record must be a mapping" % where)
    start = _number(campaign, "start_s", where)
    end = _number(campaign, "end_s", where)
    interval = _number(campaign, "max_interval_s", where)
    if not end > start:
        raise ValueError(
            "%s: end_s (%g) must follow start_s (%g)" % (where, end, start)
        )
    if interval <= 0.0:
        raise ValueError("%s: max_interval_s must be > 0, got %g" % (where, interval))
    return {"start_s": start, "end_s": end, "max_interval_s": interval}


def missing_sections(report, required=REQUIRED_SECTIONS):
    """List the mandatory report sections that are absent or empty."""
    if not isinstance(report, dict):
        raise ValueError("report: record must be a mapping")
    if not isinstance(required, (list, tuple)) or not required:
        raise ValueError("required: must be a non-empty sequence of section names")
    gaps = []
    for key in required:
        value = report.get(key)
        if value is None:
            gaps.append(key)
        elif isinstance(value, str) and not value.strip():
            gaps.append(key)
        elif isinstance(value, (list, tuple, dict)) and not value:
            gaps.append(key)
    return sorted(gaps)


def validate_configuration_items(items):
    """Validate that every configuration item names an identifiable object."""
    if not isinstance(items, (list, tuple)) or not items:
        raise ValueError("items: must be a non-empty sequence")
    seen = set()
    out = []
    for index, item in enumerate(items):
        where = "items[%d]" % index
        if not isinstance(item, dict):
            raise ValueError("%s: record must be a mapping" % where)
        entry = {}
        for key in ("identifier", "configuration"):
            value = item.get(key)
            if not isinstance(value, str) or not value.strip():
                raise ValueError(
                    "%s: %s must be a non-empty string" % (where, key)
                )
            entry[key] = value.strip()
        if entry["identifier"] in seen:
            raise ValueError(
                "%s: identifier %r already used by another configuration item"
                % (where, entry["identifier"])
            )
        seen.add(entry["identifier"])
        out.append(entry)
    return out


def ordered_samples(samples, campaign):
    """Sort the condition samples and refuse any outside the campaign window."""
    window = validate_campaign(campaign)
    if not isinstance(samples, (list, tuple)):
        raise ValueError("samples: must be a sequence")
    out = []
    for index, sample in enumerate(samples):
        where = "samples[%d]" % index
        if not isinstance(sample, dict):
            raise ValueError("%s: record must be a mapping" % where)
        time_s = _number(sample, "time_s", where)
        value = _number(sample, "value", where)
        if not at_least(time_s, window["start_s"]) or not at_most(
            time_s, window["end_s"]
        ):
            raise ValueError(
                "%s: time %g lies outside the campaign window %g to %g"
                % (where, time_s, window["start_s"], window["end_s"])
            )
        out.append({"time_s": time_s, "value": value})
    out.sort(key=lambda entry: entry["time_s"])
    return out


def condition_log_gaps(samples, campaign):
    """Stretches of the campaign window longer than the sampling interval."""
    window = validate_campaign(campaign)
    ordered = ordered_samples(samples, campaign)
    interval = window["max_interval_s"]
    gaps = []
    cursor = window["start_s"]
    for sample in ordered:
        if not at_most(sample["time_s"] - cursor, interval):
            gaps.append({"from_s": cursor, "to_s": sample["time_s"]})
        cursor = sample["time_s"]
    if not at_most(window["end_s"] - cursor, interval):
        gaps.append({"from_s": cursor, "to_s": window["end_s"]})
    return gaps


def coverage_fraction(samples, campaign):
    """Fraction of the campaign window the condition log actually evidences."""
    window = validate_campaign(campaign)
    span = window["end_s"] - window["start_s"]
    covered = span
    for gap in condition_log_gaps(samples, campaign):
        covered -= (gap["to_s"] - gap["from_s"]) - window["max_interval_s"]
    if covered < 0.0:
        covered = 0.0
    if covered > span:
        covered = span
    return covered / span


def calibration_findings(instruments, campaign):
    """Report instruments whose calibration lapsed before the campaign closed."""
    window = validate_campaign(campaign)
    if not isinstance(instruments, (list, tuple)) or not instruments:
        raise ValueError("instruments: must be a non-empty sequence")
    out = []
    for index, instrument in enumerate(instruments):
        where = "instruments[%d]" % index
        if not isinstance(instrument, dict):
            raise ValueError("%s: record must be a mapping" % where)
        identifier = instrument.get("identifier")
        if not isinstance(identifier, str) or not identifier.strip():
            raise ValueError("%s: identifier must be a non-empty string" % where)
        due = _number(instrument, "calibration_due_s", where)
        if not at_least(due, window["end_s"]):
            out.append(
                "%s: calibration expired at %g, before the campaign closed at %g, so "
                "its readings after that point rest on no certificate"
                % (identifier.strip(), due, window["end_s"])
            )
    return out


def compile_facility_test_report(report, campaign):
    """Full clause 5.7.4.1 assembly and completeness check of one record."""
    if not isinstance(report, dict):
        raise ValueError("report: record must be a mapping")
    window = validate_campaign(campaign)
    gaps = missing_sections(report)

    items = []
    instruments_findings = []
    log_gaps = []
    covered = 0.0
    findings = []

    for section in gaps:
        findings.append("the report has no %s section" % section.replace("_", " "))

    if "configuration_items" not in gaps:
        items = validate_configuration_items(report["configuration_items"])
    if "condition_log" not in gaps:
        log_gaps = condition_log_gaps(report["condition_log"], campaign)
        covered = coverage_fraction(report["condition_log"], campaign)
        for gap in log_gaps:
            findings.append(
                "the condition log leaves %g s to %g s unevidenced against a %g s "
                "interval" % (gap["from_s"], gap["to_s"], window["max_interval_s"])
            )
    if "instrument_list" not in gaps:
        instruments_findings = calibration_findings(report["instrument_list"], campaign)
        findings.extend(instruments_findings)

    return {
        "campaign": window,
        "missing_sections": gaps,
        "configuration_items": items,
        "condition_log_gaps": log_gaps,
        "coverage_fraction": covered,
        "calibration_findings": instruments_findings,
        "findings": findings,
        "verdict": REPORT_COMPLETE if not findings else REPORT_INCOMPLETE,
    }
