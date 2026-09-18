#!/usr/bin/env python3
"""Susceptibility data presentation, ECSS-E-ST-20-07C clause 5.2.10.4.

Paraphrased procedure, no verbatim standard text. The clause requires the
susceptibility results to be presented together with the pass criteria that
were agreed for them, so a reader can see what the unit was required to do
before reading what it did. This module turns that into a deterministic audit
of a report package:

  criteria register -> agreed, referenced, uniquely identified criteria
  result records    -> the fields a reader needs to reproduce the verdict
  result x criterion -> outcome and margin against the agreed limit
  coverage          -> results citing no criterion, criteria no result covers

stdlib only, offline, deterministic.
"""

from __future__ import annotations

import math

# Float comparison tolerance. An outcome is decided on a difference of two
# float quantities, so an observation that exactly meets its limit can land a
# few units in the last place the wrong side of it. The tolerance absorbs that
# representation error only; it never relaxes an agreed limit.
TOL = 1e-9

DIRECTION_NOT_TO_EXCEED = "not-to-exceed"
DIRECTION_NOT_TO_FALL_BELOW = "not-to-fall-below"
RECOGNIZED_DIRECTIONS = (DIRECTION_NOT_TO_EXCEED, DIRECTION_NOT_TO_FALL_BELOW)

RECOGNIZED_MODULATIONS = (
    "continuous-wave",
    "pulse-modulated",
    "amplitude-modulated",
    "frequency-modulated",
)

# Fraction of the agreed limit inside which a passing result is reported as
# close to its criterion rather than comfortably clear of it.
DEFAULT_MARGINAL_BAND_FRACTION = 0.05

# Fields a presented result must carry for the verdict to be reproducible.
REQUIRED_RESULT_FIELDS = (
    "criterion_id",
    "frequency_hz",
    "injected_level_dbuv",
    "modulation",
    "observed_value",
)

OUTCOME_PASS = "pass"
OUTCOME_FAIL = "fail"
OUTCOMES = (OUTCOME_PASS, OUTCOME_FAIL)


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


def _text(record, key, where):
    if key not in record:
        raise ValueError("%s: missing required field %r" % (where, key))
    value = record[key]
    if not isinstance(value, str) or not value.strip():
        raise ValueError(
            "%s: field %r must be a non-empty string, got %r" % (where, key, value)
        )
    return value.strip()


def at_least(value, bound, tol=TOL):
    """True when value meets the bound, absorbing float error only."""
    if value >= bound:
        return True
    return math.isclose(value, bound, rel_tol=0.0, abs_tol=tol)


def at_most(value, bound, tol=TOL):
    """True when value stays within the bound, absorbing float error only."""
    if value <= bound:
        return True
    return math.isclose(value, bound, rel_tol=0.0, abs_tol=tol)


def normalize_direction(name):
    """Return the recognized sense of a criterion limit."""
    if not isinstance(name, str):
        raise ValueError("direction must be a string, got %r" % (name,))
    key = name.strip().lower()
    if key not in RECOGNIZED_DIRECTIONS:
        raise ValueError(
            "unrecognized direction %r; recognized: %s"
            % (name, ", ".join(RECOGNIZED_DIRECTIONS))
        )
    return key


def normalize_modulation(name):
    """Return the recognized modulation designation for a raw designation."""
    if not isinstance(name, str):
        raise ValueError("modulation must be a string, got %r" % (name,))
    key = name.strip().lower()
    if key not in RECOGNIZED_MODULATIONS:
        raise ValueError(
            "unrecognized modulation %r; recognized: %s"
            % (name, ", ".join(RECOGNIZED_MODULATIONS))
        )
    return key


def normalize_criterion(record):
    """Validate one agreed pass criterion and return a normalized copy."""
    where = "criterion"
    if not isinstance(record, dict):
        raise ValueError("%s: record must be a mapping" % where)
    criterion_id = _text(record, "criterion_id", where)
    if not _flag(record, "agreed", where):
        raise ValueError(
            "%s %s: a criterion that was never agreed cannot be restated in the "
            "report as an agreed pass criterion" % (where, criterion_id)
        )
    return {
        "criterion_id": criterion_id,
        "function": _text(record, "function", where),
        "parameter": _text(record, "parameter", where),
        "limit_value": _number(record, "limit_value", where),
        "unit": _text(record, "unit", where),
        "direction": normalize_direction(record.get("direction")),
        "agreement_reference": _text(record, "agreement_reference", where),
        "agreed": True,
    }


def build_criteria_register(records):
    """Build the agreed-criteria register, rejecting duplicate identifiers."""
    where = "criteria"
    if not isinstance(records, (list, tuple)):
        raise ValueError("%s: must be a list of criteria" % where)
    if len(records) == 0:
        raise ValueError("%s: at least one agreed pass criterion is required" % where)
    register = {}
    for record in records:
        criterion = normalize_criterion(record)
        key = criterion["criterion_id"]
        if key in register:
            raise ValueError(
                "%s: duplicate criterion identifier %r; one identifier names one "
                "criterion" % (where, key)
            )
        register[key] = criterion
    return register


def restate_criterion(criterion):
    """One-line restatement of a criterion for presentation beside its result."""
    return "%s / %s %s %g %s (agreed: %s)" % (
        criterion["function"],
        criterion["parameter"],
        criterion["direction"],
        criterion["limit_value"],
        criterion["unit"],
        criterion["agreement_reference"],
    )


def normalize_result(record):
    """Validate one presented result and return a normalized copy."""
    where = "result"
    if not isinstance(record, dict):
        raise ValueError("%s: record must be a mapping" % where)
    missing = [field for field in REQUIRED_RESULT_FIELDS if field not in record]
    if missing:
        raise ValueError(
            "%s: a presented result must carry %s; missing %s"
            % (where, ", ".join(REQUIRED_RESULT_FIELDS), ", ".join(missing))
        )
    frequency = _number(record, "frequency_hz", where)
    if frequency <= 0.0:
        raise ValueError("%s: frequency_hz must be > 0, got %g" % (where, frequency))
    return {
        "criterion_id": _text(record, "criterion_id", where),
        "frequency_hz": frequency,
        "injected_level_dbuv": _number(record, "injected_level_dbuv", where),
        "modulation": normalize_modulation(record.get("modulation")),
        "observed_value": _number(record, "observed_value", where),
    }


def result_margin(result, criterion):
    """Signed margin of an observation against its agreed limit."""
    if criterion["direction"] == DIRECTION_NOT_TO_EXCEED:
        return criterion["limit_value"] - result["observed_value"]
    return result["observed_value"] - criterion["limit_value"]


def evaluate_result(
    result, criterion, marginal_band_fraction=DEFAULT_MARGINAL_BAND_FRACTION
):
    """Grade one presented result against the criterion it cites."""
    fraction = _number(
        {"v": marginal_band_fraction}, "v", "marginal_band_fraction"
    )
    if not 0.0 <= fraction < 1.0:
        raise ValueError(
            "marginal_band_fraction must lie in [0, 1), got %g" % fraction
        )
    margin = result_margin(result, criterion)
    outcome = OUTCOME_PASS if at_least(margin, 0.0) else OUTCOME_FAIL
    band = abs(criterion["limit_value"]) * fraction
    close = outcome == OUTCOME_PASS and at_most(margin, band)
    return {
        "criterion_id": criterion["criterion_id"],
        "frequency_hz": result["frequency_hz"],
        "injected_level_dbuv": result["injected_level_dbuv"],
        "modulation": result["modulation"],
        "observed_value": result["observed_value"],
        "limit_value": criterion["limit_value"],
        "unit": criterion["unit"],
        "direction": criterion["direction"],
        "function": criterion["function"],
        "margin": margin,
        "outcome": outcome,
        "close_to_limit": close,
        "restated_criterion": restate_criterion(criterion),
    }


def presentation_gaps(register, results):
    """Return the results citing no criterion and the criteria no result covers."""
    cited = set()
    orphans = []
    for result in results:
        key = result["criterion_id"]
        if key in register:
            cited.add(key)
        else:
            orphans.append(key)
    uncovered = [key for key in sorted(register) if key not in cited]
    return orphans, uncovered


def group_by_function(entries):
    """Group graded entries by the function their criterion governs."""
    grouped = {}
    for entry in entries:
        grouped.setdefault(entry["function"], []).append(entry)
    return grouped


def assess_susceptibility_presentation(
    criteria, results, marginal_band_fraction=DEFAULT_MARGINAL_BAND_FRACTION
):
    """Full clause 5.2.10.4 audit of a susceptibility report package."""
    register = build_criteria_register(criteria)
    if not isinstance(results, (list, tuple)):
        raise ValueError("results: must be a list of presented results")
    if len(results) == 0:
        raise ValueError("results: at least one presented result is required")

    normalized = [normalize_result(record) for record in results]
    orphans, uncovered = presentation_gaps(register, normalized)

    entries = []
    for result in normalized:
        criterion = register.get(result["criterion_id"])
        if criterion is None:
            continue
        entries.append(evaluate_result(result, criterion, marginal_band_fraction))
    entries.sort(key=lambda e: (e["criterion_id"], e["frequency_hz"]))

    counts = dict((outcome, 0) for outcome in OUTCOMES)
    findings = []
    limitations = []
    for entry in entries:
        counts[entry["outcome"]] += 1
        if entry["outcome"] == OUTCOME_FAIL:
            findings.append(
                "result at %g Hz misses criterion %s by %.3f %s"
                % (
                    entry["frequency_hz"],
                    entry["criterion_id"],
                    abs(entry["margin"]),
                    entry["unit"],
                )
            )
        elif entry["close_to_limit"]:
            limitations.append(
                "result at %g Hz sits %.3f %s from criterion %s"
                % (
                    entry["frequency_hz"],
                    entry["margin"],
                    entry["unit"],
                    entry["criterion_id"],
                )
            )
    for key in orphans:
        findings.append(
            "presented result cites criterion %s, which is not in the agreed "
            "register" % key
        )
    for key in uncovered:
        findings.append(
            "agreed criterion %s is restated by no presented result" % key
        )

    return {
        "criteria": register,
        "entries": entries,
        "by_function": group_by_function(entries),
        "counts": counts,
        "orphan_criterion_ids": orphans,
        "uncovered_criterion_ids": uncovered,
        "findings": findings,
        "limitations": limitations,
        "verdict": "report-complete" if not findings else "report-incomplete",
    }
