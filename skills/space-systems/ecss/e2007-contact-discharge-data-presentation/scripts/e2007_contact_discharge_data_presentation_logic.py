#!/usr/bin/env python3
"""Contact discharge data presentation, ECSS-E-ST-20-07C clause 5.4.14.5.

Paraphrased requirement, no verbatim standard text. The clause says what
a contact discharge result has to look like when it reaches a reader:
the generator settings it was produced with, the oscilloscope records
from the waveform calibration, and a table of compliance covering the
application points. This module turns that into a deterministic audit:

  declared settings block   -> which required fields are actually filled
  oscilloscope records      -> one per applied level and polarity
  trace bandwidth + edge    -> is the scope fast enough, and what did it add
  table rows                -> verdict re-derived from the observed response
  rows vs the declared plan -> point, polarity and discharge-count coverage

stdlib only, offline, deterministic.
"""

from __future__ import annotations

import math

# Comparison tolerances. Bandwidths, rise times and fractions are floats,
# so a value that exactly meets a limit can land a few units in the last
# place off it. These absorb representation error only.
REL_TOL = 1e-12
ABS_TOL = 1e-12

# Rise-time to bandwidth product of a single-pole front end. An edge of
# t seconds needs a scope of about this over t to be recorded as itself.
RISE_BANDWIDTH_PRODUCT = 0.35

# Once the instrument contributes more than this fraction of the recorded
# edge, the reported rise time is as much the scope as the generator and
# the de-embedded value has to travel with it.
SCOPE_CONTRIBUTION_NOTICE = 0.10

# The edge the contact discharge event is specified to have. Bandwidth
# adequacy is graded against THIS, never against the edge the trace
# reports: a slow instrument records a slow edge, and grading it against
# its own output would call every slow scope fast enough for what it
# managed to capture.
DEFAULT_SPECIFIED_RISE_TIME_S = 0.8e-9

REQUIRED_SETTINGS_FIELDS = (
    "charge_voltage_levels_kv",
    "discharge_resistance_ohm",
    "discharges_per_point",
    "polarities",
    "storage_capacitance_f",
    "tip_type",
)

RESPONSE_RANKS = {
    "no-effect": 0,
    "self-recovering": 1,
    "operator-recovered": 2,
    "permanent-degradation": 3,
}

RESPONSE_TOKENS = {
    "no-effect": "no-effect",
    "no effect": "no-effect",
    "none": "no-effect",
    "nominal": "no-effect",
    "self-recovering": "self-recovering",
    "self recovering": "self-recovering",
    "auto-recovered": "self-recovering",
    "operator-recovered": "operator-recovered",
    "operator recovered": "operator-recovered",
    "reset-required": "operator-recovered",
    "permanent-degradation": "permanent-degradation",
    "permanent degradation": "permanent-degradation",
    "damage": "permanent-degradation",
}

CRITERION_ALLOWANCE = {
    "criterion-a": 0,
    "criterion-b": 1,
    "criterion-c": 2,
}

CRITERION_TOKENS = {
    "a": "criterion-a",
    "criterion-a": "criterion-a",
    "criterion a": "criterion-a",
    "b": "criterion-b",
    "criterion-b": "criterion-b",
    "criterion b": "criterion-b",
    "c": "criterion-c",
    "criterion-c": "criterion-c",
    "criterion c": "criterion-c",
}

VERDICT_TOKENS = {
    "compliant": "compliant",
    "pass": "compliant",
    "passed": "compliant",
    "conforming": "compliant",
    "non-compliant": "non-compliant",
    "noncompliant": "non-compliant",
    "not compliant": "non-compliant",
    "fail": "non-compliant",
    "failed": "non-compliant",
}

POLARITY_TOKENS = {
    "+": "positive",
    "pos": "positive",
    "positive": "positive",
    "-": "negative",
    "neg": "negative",
    "negative": "negative",
}

COMPLIANT = "compliant"
NON_COMPLIANT = "non-compliant"

PRESENTATION_COMPLETE = "presentation-complete"
PRESENTATION_WITH_LIMITATIONS = "presentation-complete-with-limitations"
PRESENTATION_INCOMPLETE = "presentation-incomplete"


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


def _scalar(value, name):
    return _number({"v": value}, "v", name)


def _label(record, key, where):
    if key not in record:
        raise ValueError("%s: missing required field %r" % (where, key))
    value = record[key]
    if not isinstance(value, str) or not value.strip():
        raise ValueError("%s: field %r must be a non-empty label" % (where, key))
    return value.strip()


def at_least(value, bound):
    """True when a value reaches a lower bound, absorbing float error."""
    if value >= bound:
        return True
    return math.isclose(value, bound, rel_tol=REL_TOL, abs_tol=ABS_TOL)


def at_most(value, bound):
    """True when a value stays under an upper bound, absorbing float error."""
    if value <= bound:
        return True
    return math.isclose(value, bound, rel_tol=REL_TOL, abs_tol=ABS_TOL)


def normalize_polarity(token):
    """Map a polarity cell onto 'positive' or 'negative'."""
    if not isinstance(token, str):
        raise ValueError("polarity must be a string, got %r" % (token,))
    key = token.strip().lower()
    if key not in POLARITY_TOKENS:
        raise ValueError("unrecognized polarity %r" % (token,))
    return POLARITY_TOKENS[key]


def normalize_response(token):
    """Map an observed-response cell onto one of the four response groups."""
    if not isinstance(token, str):
        raise ValueError("response must be a string, got %r" % (token,))
    key = " ".join(token.strip().lower().split())
    if key not in RESPONSE_TOKENS:
        raise ValueError(
            "unrecognized response %r; recognized: %s"
            % (token, ", ".join(sorted(RESPONSE_RANKS)))
        )
    return RESPONSE_TOKENS[key]


def response_rank(response):
    """Severity order of a response group; higher is worse."""
    return RESPONSE_RANKS[normalize_response(response)]


def normalize_criterion(token):
    """Map a performance-criterion cell onto its canonical name."""
    if not isinstance(token, str):
        raise ValueError("criterion must be a string, got %r" % (token,))
    key = " ".join(token.strip().lower().split())
    if key not in CRITERION_TOKENS:
        raise ValueError(
            "unrecognized performance criterion %r; recognized: %s"
            % (token, ", ".join(sorted(CRITERION_ALLOWANCE)))
        )
    return CRITERION_TOKENS[key]


def criterion_allowance(criterion):
    """Worst response group the criterion still admits."""
    return CRITERION_ALLOWANCE[normalize_criterion(criterion)]


def normalize_verdict(token):
    """Map a verdict cell onto 'compliant' or 'non-compliant'."""
    if not isinstance(token, str):
        raise ValueError("verdict must be a string, got %r" % (token,))
    key = " ".join(token.strip().lower().split())
    if key not in VERDICT_TOKENS:
        raise ValueError("unrecognized verdict %r" % (token,))
    return VERDICT_TOKENS[key]


def verdict_from_response(response, criterion):
    """Re-derive a row verdict from the response it reports and its criterion."""
    if response_rank(response) <= criterion_allowance(criterion):
        return COMPLIANT
    return NON_COMPLIANT


def required_bandwidth_hz(rise_time_s):
    """Front-end bandwidth an edge of this rise time needs to be recorded."""
    edge = _scalar(rise_time_s, "rise_time_s")
    if edge <= 0.0:
        raise ValueError("rise_time_s must be > 0, got %g" % edge)
    return RISE_BANDWIDTH_PRODUCT / edge


def scope_rise_time_s(bandwidth_hz):
    """Rise time the instrument contributes on its own."""
    bandwidth = _scalar(bandwidth_hz, "bandwidth_hz")
    if bandwidth <= 0.0:
        raise ValueError("bandwidth_hz must be > 0, got %g" % bandwidth)
    return RISE_BANDWIDTH_PRODUCT / bandwidth


def deembed_rise_time_s(measured_rise_time_s, bandwidth_hz):
    """Remove the instrument's own edge from a recorded rise time."""
    measured = _scalar(measured_rise_time_s, "measured_rise_time_s")
    if measured <= 0.0:
        raise ValueError("measured_rise_time_s must be > 0, got %g" % measured)
    instrument = scope_rise_time_s(bandwidth_hz)
    if measured < instrument and not math.isclose(
        measured, instrument, rel_tol=REL_TOL, abs_tol=ABS_TOL
    ):
        raise ValueError(
            "recorded edge %g s is faster than the instrument's own %g s, so the "
            "trace cannot have been produced by this scope" % (measured, instrument)
        )
    difference = measured * measured - instrument * instrument
    if difference < 0.0:
        difference = 0.0
    return math.sqrt(difference)


def scope_contribution_fraction(measured_rise_time_s, bandwidth_hz):
    """Share of the recorded edge that the instrument put there."""
    measured = _scalar(measured_rise_time_s, "measured_rise_time_s")
    actual = deembed_rise_time_s(measured_rise_time_s, bandwidth_hz)
    return (measured - actual) / measured


def bandwidth_is_adequate(bandwidth_hz, specified_rise_time_s):
    """True when the instrument is fast enough for the edge the event has.

    Graded against the specified edge of the discharge, not against the
    edge the trace reports: a slow front end records a slow edge, so an
    adequacy test fed its own output can never fail.
    """
    bandwidth = _scalar(bandwidth_hz, "bandwidth_hz")
    if bandwidth <= 0.0:
        raise ValueError("bandwidth_hz must be > 0, got %g" % bandwidth)
    return at_least(bandwidth, required_bandwidth_hz(specified_rise_time_s))


def audit_generator_settings(settings):
    """Report which required generator-settings fields the report leaves empty."""
    where = "generator_settings"
    if not isinstance(settings, dict):
        raise ValueError("%s: record must be a mapping" % where)
    present = {}
    missing = []
    for field in REQUIRED_SETTINGS_FIELDS:
        if field not in settings:
            missing.append(field)
            continue
        value = settings[field]
        if value is None:
            missing.append(field)
            continue
        if isinstance(value, str):
            if not value.strip():
                missing.append(field)
                continue
            present[field] = value.strip()
            continue
        if isinstance(value, (list, tuple)):
            if not value:
                missing.append(field)
                continue
            present[field] = list(value)
            continue
        if isinstance(value, bool) or not isinstance(value, (int, float)):
            raise ValueError(
                "%s: field %r must be a label, a sequence or a number, got %r"
                % (where, field, value)
            )
        present[field] = float(value)
    return {"present": present, "missing": sorted(missing)}


def validate_scope_record(record, index=0):
    """Validate one calibration oscilloscope record and return it normalized."""
    where = "oscilloscope_records[%d]" % index
    if not isinstance(record, dict):
        raise ValueError("%s: record must be a mapping" % where)
    trace_id = _label(record, "trace_id", where)
    level = _number(record, "level_kv", where)
    if level <= 0.0:
        raise ValueError("%s: level_kv must be > 0, got %g" % (where, level))
    polarity = normalize_polarity(record.get("polarity", ""))
    bandwidth = _number(record, "bandwidth_hz", where)
    if bandwidth <= 0.0:
        raise ValueError("%s: bandwidth_hz must be > 0, got %g" % (where, bandwidth))
    rise_time = _number(record, "measured_rise_time_s", where)
    if rise_time <= 0.0:
        raise ValueError(
            "%s: measured_rise_time_s must be > 0, got %g" % (where, rise_time)
        )
    if "specified_rise_time_s" in record:
        specified = _number(record, "specified_rise_time_s", where)
        if specified <= 0.0:
            raise ValueError(
                "%s: specified_rise_time_s must be > 0, got %g" % (where, specified)
            )
    else:
        specified = DEFAULT_SPECIFIED_RISE_TIME_S
    return {
        "trace_id": trace_id,
        "level_kv": level,
        "polarity": polarity,
        "bandwidth_hz": bandwidth,
        "measured_rise_time_s": rise_time,
        "specified_rise_time_s": specified,
    }


def grade_scope_record(record, index=0):
    """Grade one oscilloscope record for bandwidth adequacy and de-embedding."""
    normalized = validate_scope_record(record, index)
    needed = required_bandwidth_hz(normalized["specified_rise_time_s"])
    adequate = bandwidth_is_adequate(
        normalized["bandwidth_hz"], normalized["specified_rise_time_s"]
    )
    deembedded = deembed_rise_time_s(
        normalized["measured_rise_time_s"], normalized["bandwidth_hz"]
    )
    contribution = scope_contribution_fraction(
        normalized["measured_rise_time_s"], normalized["bandwidth_hz"]
    )
    normalized.update(
        {
            "required_bandwidth_hz": needed,
            "bandwidth_is_adequate": adequate,
            "deembedded_rise_time_s": deembedded,
            "scope_contribution_fraction": contribution,
        }
    )
    return normalized


def validate_row(row, index=0):
    """Validate one compliance-table row; an empty response cell is carried."""
    where = "rows[%d]" % index
    if not isinstance(row, dict):
        raise ValueError("%s: record must be a mapping" % where)
    row_id = _label(row, "row_id", where)
    point = _label(row, "application_point", where)
    polarity = normalize_polarity(row.get("polarity", ""))
    level = _number(row, "level_kv", where)
    if level <= 0.0:
        raise ValueError("%s: level_kv must be > 0, got %g" % (where, level))
    applied = _number(row, "discharges_applied", where)
    if applied < 1.0 or applied != math.floor(applied):
        raise ValueError(
            "%s: discharges_applied must be a whole number >= 1, got %g"
            % (where, applied)
        )
    criterion = normalize_criterion(row.get("required_criterion", ""))
    verdict = normalize_verdict(row.get("verdict", ""))
    response = row.get("observed_response")
    if response is None or (isinstance(response, str) and not response.strip()):
        response_value = None
    else:
        response_value = normalize_response(response)
    return {
        "row_id": row_id,
        "application_point": point,
        "polarity": polarity,
        "level_kv": level,
        "discharges_applied": int(applied),
        "required_criterion": criterion,
        "verdict": verdict,
        "observed_response": response_value,
    }


def grade_row(row, index=0):
    """Compare one row's entered verdict with the response it reports."""
    normalized = validate_row(row, index)
    if normalized["observed_response"] is None:
        normalized.update(
            {
                "derived_verdict": None,
                "verdict_agrees": None,
                "margin_steps": None,
            }
        )
        return normalized
    derived = verdict_from_response(
        normalized["observed_response"], normalized["required_criterion"]
    )
    allowance = criterion_allowance(normalized["required_criterion"])
    normalized.update(
        {
            "derived_verdict": derived,
            "verdict_agrees": derived == normalized["verdict"],
            "margin_steps": allowance - response_rank(normalized["observed_response"]),
        }
    )
    return normalized


def grade_rows(rows):
    """Grade every compliance-table row, refusing a duplicated row identifier."""
    if isinstance(rows, (str, bytes)) or not isinstance(rows, (list, tuple)):
        raise ValueError("rows: must be a sequence of compliance-table rows")
    if not rows:
        raise ValueError("rows: the compliance table has no rows at all")
    graded = []
    seen = set()
    for index, row in enumerate(rows):
        record = grade_row(row, index)
        if record["row_id"] in seen:
            raise ValueError("rows: row_id %r appears twice" % record["row_id"])
        seen.add(record["row_id"])
        graded.append(record)
    return graded


def coverage_gaps(graded_rows, declared_points, declared_polarities,
                  required_discharges):
    """Find the declared exposure the table carries no evidence of."""
    if isinstance(declared_points, (str, bytes)) or not isinstance(
        declared_points, (list, tuple)
    ):
        raise ValueError("declared_points: must be a sequence of point labels")
    if not declared_points:
        raise ValueError("declared_points: at least one point must be declared")
    polarities = []
    for token in declared_polarities or []:
        polarities.append(normalize_polarity(token))
    if not polarities:
        raise ValueError("declared_polarities: at least one polarity must be declared")
    required = _scalar(required_discharges, "required_discharges")
    if required < 1.0 or required != math.floor(required):
        raise ValueError(
            "required_discharges must be a whole number >= 1, got %g" % required
        )

    gaps = []
    covered = {}
    for record in graded_rows:
        covered.setdefault(record["application_point"], set()).add(record["polarity"])
    for point in declared_points:
        label = point.strip() if isinstance(point, str) else point
        if label not in covered:
            gaps.append(
                "declared application point %s appears in no row of the table" % label
            )
            continue
        for polarity in polarities:
            if polarity not in covered[label]:
                gaps.append(
                    "point %s carries no %s polarity row" % (label, polarity)
                )
    for record in graded_rows:
        if record["discharges_applied"] < int(required):
            gaps.append(
                "row %s reports %d discharges against the %d the plan called for"
                % (record["row_id"], record["discharges_applied"], int(required))
            )
    return gaps


def missing_scope_records(graded_rows, scope_records):
    """Applied level and polarity pairs that no oscilloscope record covers."""
    covered = set()
    for record in scope_records:
        covered.add((round(record["level_kv"], 9), record["polarity"]))
    missing = []
    for record in graded_rows:
        key = (round(record["level_kv"], 9), record["polarity"])
        if key not in covered and key not in [tuple(m) for m in missing]:
            missing.append([key[0], key[1]])
    return [tuple(item) for item in missing]


def assess_contact_discharge_presentation(report):
    """Full clause 5.4.14.5 audit of a contact discharge report."""
    if not isinstance(report, dict):
        raise ValueError("report: record must be a mapping")

    settings = audit_generator_settings(report.get("generator_settings", {}))
    graded_rows = grade_rows(report.get("rows"))

    raw_scope = report.get("oscilloscope_records", [])
    if isinstance(raw_scope, (str, bytes)) or not isinstance(
        raw_scope, (list, tuple)
    ):
        raise ValueError("oscilloscope_records: must be a sequence of trace records")
    scope_records = [grade_scope_record(r, i) for i, r in enumerate(raw_scope)]

    findings = []
    limitations = []

    for field in settings["missing"]:
        findings.append(
            "generator settings field %s is not on the page, so the run cannot be "
            "reproduced from the report" % field
        )

    if not scope_records:
        findings.append(
            "no calibration oscilloscope record is presented, so nothing on the "
            "page shows what the generator actually delivered"
        )
    for record in scope_records:
        if not record["bandwidth_is_adequate"]:
            findings.append(
                "trace %s was taken at %.3g Hz against the %.3g Hz a %g s "
                "specified edge needs, so the recorded rise time is the "
                "instrument's rather than the event's"
                % (
                    record["trace_id"],
                    record["bandwidth_hz"],
                    record["required_bandwidth_hz"],
                    record["specified_rise_time_s"],
                )
            )
        elif record["scope_contribution_fraction"] > SCOPE_CONTRIBUTION_NOTICE:
            limitations.append(
                "trace %s has %.1f%% of its recorded edge from the instrument; the "
                "de-embedded rise time is %.3g s"
                % (
                    record["trace_id"],
                    100.0 * record["scope_contribution_fraction"],
                    record["deembedded_rise_time_s"],
                )
            )

    for pair in missing_scope_records(graded_rows, scope_records):
        findings.append(
            "no oscilloscope record covers the %g kV %s events the table reports"
            % (pair[0], pair[1])
        )

    for record in graded_rows:
        if record["observed_response"] is None:
            findings.append(
                "row %s asserts a verdict with the observed response cell empty, "
                "so nothing on the page says what it was decided on"
                % record["row_id"]
            )
            continue
        if not record["verdict_agrees"]:
            findings.append(
                "row %s is entered %s while its %s response against %s derives %s"
                % (
                    record["row_id"],
                    record["verdict"],
                    record["observed_response"],
                    record["required_criterion"],
                    record["derived_verdict"],
                )
            )
        elif record["margin_steps"] == 0 and record["verdict"] == COMPLIANT:
            limitations.append(
                "row %s sits at the worst response its criterion still admits, so "
                "it passes with no room left" % record["row_id"]
            )

    gaps = coverage_gaps(
        graded_rows,
        report.get("declared_application_points", []),
        report.get("declared_polarities", []),
        report.get("required_discharges_per_point", 1),
    )
    findings.extend(gaps)

    if findings:
        verdict = PRESENTATION_INCOMPLETE
    elif limitations:
        verdict = PRESENTATION_WITH_LIMITATIONS
    else:
        verdict = PRESENTATION_COMPLETE

    return {
        "generator_settings": settings,
        "oscilloscope_records": scope_records,
        "rows": graded_rows,
        "coverage_gaps": gaps,
        "findings": findings,
        "limitations": limitations,
        "verdict": verdict,
    }
