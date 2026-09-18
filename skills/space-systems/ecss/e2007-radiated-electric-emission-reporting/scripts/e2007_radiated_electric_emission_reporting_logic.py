#!/usr/bin/env python3
"""Radiated electric emission reporting, ECSS-E-ST-20-07C clause 5.4.6.5.

Paraphrased procedure, no verbatim standard text. The clause asks that the
recorded radiated emission data not travel on its own: a statement of the
measuring antenna's electrical continuity has to be delivered alongside it,
so a reader knows the levels were taken through an antenna that was actually
connected. This module turns that into a deterministic assessment:

  continuity statement            -> continuous, marginal or open
  antennas named in the data      -> antennas with no statement at all
  statement timing vs the run     -> statements that do not bracket the run
  recorded level vs its limit     -> margins and exceedances
  data + statements together      -> complete, data-only or unsupported

stdlib only, offline, deterministic.
"""

from __future__ import annotations

import math

# Comparison tolerance. Resistances, levels and time offsets are floats
# written by bench software, so two values meant to be equal can differ by
# a few units in the last place. The tolerance absorbs that representation
# error only; it never turns a real exceedance into a pass.
REL_TOL = 1e-12
ABS_TOL = 1e-9

# Resistance an antenna continuity path is expected to stay under.
DEFAULT_CONTINUITY_LIMIT_OHM = 0.1

# Fraction of the limit above which a passing resistance is still worth
# calling out, because the path is closed but not comfortably so.
MARGINAL_FRACTION = 0.8

CONTINUITY_CONTINUOUS = "continuous"
CONTINUITY_MARGINAL = "marginal"
CONTINUITY_OPEN = "open"
CONTINUITY_CATEGORIES = (
    CONTINUITY_CONTINUOUS,
    CONTINUITY_MARGINAL,
    CONTINUITY_OPEN,
)

PACKAGE_COMPLETE = "complete"
PACKAGE_DATA_ONLY = "data-only"
PACKAGE_UNSUPPORTED = "unsupported"
PACKAGE_CATEGORIES = (PACKAGE_COMPLETE, PACKAGE_DATA_ONLY, PACKAGE_UNSUPPORTED)

CONTINUITY_METHODS = ("four-wire", "two-wire")
POLARIZATIONS = ("horizontal", "vertical")


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


def _token(record, key, where, allowed=None):
    if key not in record:
        raise ValueError("%s: missing required field %r" % (where, key))
    value = record[key]
    if not isinstance(value, str) or not value.strip():
        raise ValueError("%s: field %r must be a non-empty string" % (where, key))
    token = value.strip().lower()
    if allowed is not None and token not in allowed:
        raise ValueError(
            "%s: field %r must be one of %s, got %r" % (where, key, list(allowed), token)
        )
    return token


def _close(left, right):
    return math.isclose(left, right, rel_tol=REL_TOL, abs_tol=ABS_TOL)


def at_least(value, bound):
    """True when value meets bound, absorbing float representation error."""
    if value >= bound:
        return True
    return _close(value, bound)


def at_most(value, bound):
    """True when value stays at or under bound, absorbing float error."""
    if value <= bound:
        return True
    return _close(value, bound)


def validate_continuity_statement(statement, where="continuity_statement"):
    """Validate one antenna electrical continuity statement."""
    if not isinstance(statement, dict):
        raise ValueError("%s: must be a mapping" % where)
    antenna = _token(statement, "antenna_id", where)
    resistance = _number(statement, "resistance_ohm", where)
    measured_at = _number(statement, "measured_at_s", where)
    method = _token(statement, "method", where, CONTINUITY_METHODS)
    recorded_by = _token(statement, "recorded_by", where)
    if resistance < 0.0:
        raise ValueError(
            "%s: resistance_ohm must be >= 0, got %g" % (where, resistance)
        )
    if measured_at < 0.0:
        raise ValueError(
            "%s: measured_at_s must be >= 0, got %g" % (where, measured_at)
        )
    return {
        "antenna_id": antenna,
        "resistance_ohm": resistance,
        "measured_at_s": measured_at,
        "method": method,
        "recorded_by": recorded_by,
    }


def validate_continuity_statements(statements):
    """Validate the delivered continuity statements and return them ordered."""
    where = "continuity_statements"
    if not isinstance(statements, (list, tuple)):
        raise ValueError("%s: must be a list" % where)
    out = []
    for index, statement in enumerate(statements):
        out.append(
            validate_continuity_statement(statement, "%s[%d]" % (where, index))
        )
    out.sort(key=lambda s: (s["antenna_id"], s["measured_at_s"]))
    return out


def categorize_continuity(statement, limit_ohm=DEFAULT_CONTINUITY_LIMIT_OHM):
    """Group a continuity statement as continuous, marginal or open."""
    limit = _scalar(limit_ohm, "limit_ohm")
    if limit <= 0.0:
        raise ValueError("limit_ohm must be > 0, got %g" % limit)
    record = validate_continuity_statement(statement)
    if not at_most(record["resistance_ohm"], limit):
        return CONTINUITY_OPEN
    if at_least(record["resistance_ohm"], limit * MARGINAL_FRACTION):
        return CONTINUITY_MARGINAL
    return CONTINUITY_CONTINUOUS


def validate_emission_record(record, where="emission_record"):
    """Validate one recorded radiated electric field level."""
    if not isinstance(record, dict):
        raise ValueError("%s: must be a mapping" % where)
    frequency = _number(record, "frequency_hz", where)
    level = _number(record, "level_dbuv_per_m", where)
    limit = _number(record, "limit_dbuv_per_m", where)
    antenna = _token(record, "antenna_id", where)
    polarization = _token(record, "polarization", where, POLARIZATIONS)
    if frequency <= 0.0:
        raise ValueError("%s: frequency_hz must be > 0, got %g" % (where, frequency))
    return {
        "frequency_hz": frequency,
        "level_dbuv_per_m": level,
        "limit_dbuv_per_m": limit,
        "antenna_id": antenna,
        "polarization": polarization,
    }


def validate_emission_records(records):
    """Validate the recorded emission data and return it ordered."""
    where = "emission_records"
    if not isinstance(records, (list, tuple)):
        raise ValueError("%s: must be a list" % where)
    if len(records) == 0:
        raise ValueError("%s: at least one recorded level is required" % where)
    out = []
    for index, record in enumerate(records):
        out.append(validate_emission_record(record, "%s[%d]" % (where, index)))
    out.sort(key=lambda r: (r["antenna_id"], r["polarization"], r["frequency_hz"]))
    return out


def margin_db(record):
    """How far a recorded level sits under its limit; negative means over."""
    entry = validate_emission_record(record)
    return entry["limit_dbuv_per_m"] - entry["level_dbuv_per_m"]


def exceedances(records):
    """Recorded levels that sit above their limit."""
    over = []
    for entry in validate_emission_records(records):
        if not at_least(margin_db(entry), 0.0):
            over.append(dict(entry, margin_db=margin_db(entry)))
    return over


def worst_margin_db(records):
    """Smallest margin anywhere in the recorded data."""
    return min(margin_db(entry) for entry in validate_emission_records(records))


def antennas_in_data(records):
    """Measuring antennas the recorded data was taken through."""
    return sorted({entry["antenna_id"] for entry in validate_emission_records(records)})


def antennas_without_statement(records, statements):
    """Antennas named in the data that no continuity statement covers."""
    stated = {s["antenna_id"] for s in validate_continuity_statements(statements)}
    return [name for name in antennas_in_data(records) if name not in stated]


def statements_outside_run(statements, run_start_s, run_end_s):
    """Statements taken outside the run window, so they do not cover it."""
    start = _scalar(run_start_s, "run_start_s")
    end = _scalar(run_end_s, "run_end_s")
    if start < 0.0:
        raise ValueError("run_start_s must be >= 0, got %g" % start)
    if end <= start or _close(end, start):
        raise ValueError("run_end_s (%g) must exceed run_start_s (%g)" % (end, start))
    stale = []
    for statement in validate_continuity_statements(statements):
        moment = statement["measured_at_s"]
        if not at_least(moment, start) or not at_most(moment, end):
            stale.append(statement)
    return stale


def conflicting_statements(statements):
    """Antennas carrying more than one continuity statement in the package."""
    seen = {}
    for statement in validate_continuity_statements(statements):
        seen.setdefault(statement["antenna_id"], []).append(statement)
    return sorted(name for name, group in seen.items() if len(group) > 1)


def governing_statement(statements, antenna_id):
    """The worst-case statement for an antenna, which is the one that governs."""
    name = _token({"antenna_id": antenna_id}, "antenna_id", "antenna_id")
    group = [
        s for s in validate_continuity_statements(statements) if s["antenna_id"] == name
    ]
    if not group:
        raise ValueError("no continuity statement for antenna %r" % name)
    return max(group, key=lambda s: s["resistance_ohm"])


def categorize_package(records, statements, limit_ohm=DEFAULT_CONTINUITY_LIMIT_OHM):
    """Group the delivered package as complete, data-only or unsupported."""
    missing = antennas_without_statement(records, statements)
    if missing:
        return PACKAGE_DATA_ONLY
    for name in antennas_in_data(records):
        if categorize_continuity(governing_statement(statements, name), limit_ohm) == (
            CONTINUITY_OPEN
        ):
            return PACKAGE_UNSUPPORTED
    return PACKAGE_COMPLETE


def assemble_emission_report(
    records,
    statements,
    run_start_s,
    run_end_s,
    limit_ohm=DEFAULT_CONTINUITY_LIMIT_OHM,
):
    """Full clause 5.4.6.5 assessment of a radiated emission report package."""
    ordered = validate_emission_records(records)
    stated = validate_continuity_statements(statements)
    missing = antennas_without_statement(ordered, stated)
    stale = statements_outside_run(stated, run_start_s, run_end_s)
    conflicts = conflicting_statements(stated)
    package = categorize_package(ordered, stated, limit_ohm)
    over = exceedances(ordered)

    continuity = []
    for name in antennas_in_data(ordered):
        if name in missing:
            continue
        governing = governing_statement(stated, name)
        continuity.append(
            {
                "antenna_id": name,
                "resistance_ohm": governing["resistance_ohm"],
                "method": governing["method"],
                "category": categorize_continuity(governing, limit_ohm),
            }
        )

    findings = []
    for name in missing:
        findings.append(
            "emission data was taken through antenna %s with no continuity "
            "statement delivered alongside it" % name
        )
    for entry in continuity:
        if entry["category"] == CONTINUITY_OPEN:
            findings.append(
                "antenna %s states %g ohm against a %g ohm allowance, so the "
                "recorded levels are not supported"
                % (entry["antenna_id"], entry["resistance_ohm"], limit_ohm)
            )
    for statement in stale:
        findings.append(
            "continuity statement for antenna %s was taken at %g s, outside the "
            "run it is offered as support for"
            % (statement["antenna_id"], statement["measured_at_s"])
        )

    limitations = []
    for entry in continuity:
        if entry["category"] == CONTINUITY_MARGINAL:
            limitations.append(
                "antenna %s states %g ohm, close to the %g ohm allowance"
                % (entry["antenna_id"], entry["resistance_ohm"], limit_ohm)
            )
        if entry["method"] == "two-wire":
            limitations.append(
                "antenna %s continuity was stated by a two-wire measurement, "
                "which carries the lead resistance with it" % entry["antenna_id"]
            )
    for name in conflicts:
        limitations.append(
            "antenna %s carries more than one continuity statement; the "
            "worst-case value governs" % name
        )
    for entry in over:
        limitations.append(
            "recorded level at %g Hz exceeds its limit by %g dB"
            % (entry["frequency_hz"], -entry["margin_db"])
        )

    return {
        "records": ordered,
        "statements": stated,
        "antennas": antennas_in_data(ordered),
        "continuity": continuity,
        "missing_statements": missing,
        "stale_statements": stale,
        "conflicting_antennas": conflicts,
        "exceedances": over,
        "worst_margin_db": worst_margin_db(ordered),
        "package": package,
        "findings": findings,
        "limitations": limitations,
        "verdict": "reportable" if not findings else "report-incomplete",
    }
