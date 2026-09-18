#!/usr/bin/env python3
"""Susceptibility threshold determination, ECSS-E-ST-20-07C clause 5.2.10.3.

Paraphrased procedure, no verbatim standard text. When a susceptibility
indication appears during a run, the clause requires the injected level to be
reduced until the indication is no longer observed; that level is the
susceptibility threshold and is recorded with the conditions that produced it.
This module turns that into a deterministic reduction:

  level search -> validated descending sequence
  sequence     -> cessation level, and the bracket it is known to
  observation  -> margin against the required immunity level -> category
  run          -> governing frequency, findings, limitations

stdlib only, offline, deterministic.
"""

from __future__ import annotations

import math

# Decibel comparison tolerance. Margins and brackets are differences of two
# float levels, so an exactly-satisfied bound can land a few units in the last
# place off. The tolerance absorbs that representation error only; it never
# lowers a required margin.
DB_TOL = 1e-9

# Conventional margin the recorded threshold must hold above the required
# immunity level, decibels.
DEFAULT_REQUIRED_MARGIN_DB = 6.0

# Widest step between the last disturbed and first undisturbed level for the
# threshold to count as resolved rather than merely bracketed, decibels.
DEFAULT_MAX_BRACKET_DB = 2.0

RECOGNIZED_MODULATIONS = (
    "continuous-wave",
    "pulse-modulated",
    "amplitude-modulated",
    "frequency-modulated",
)

RECOGNIZED_RUN_TYPES = (
    "radiated-susceptibility",
    "conducted-susceptibility",
)

CATEGORY_COMPLIANT = "compliant"
CATEGORY_MARGINAL = "marginal"
CATEGORY_SUSCEPTIBLE = "susceptible"
CATEGORIES = (CATEGORY_COMPLIANT, CATEGORY_MARGINAL, CATEGORY_SUSCEPTIBLE)


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


def at_least(value_db, requirement_db, tol_db=DB_TOL):
    """True when value meets the requirement, absorbing float error only."""
    if value_db >= requirement_db:
        return True
    return math.isclose(value_db, requirement_db, rel_tol=0.0, abs_tol=tol_db)


def at_most(value_db, bound_db, tol_db=DB_TOL):
    """True when value stays within the bound, absorbing float error only."""
    if value_db <= bound_db:
        return True
    return math.isclose(value_db, bound_db, rel_tol=0.0, abs_tol=tol_db)


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


def normalize_run_type(name):
    """Return the recognized susceptibility run type for a raw designation."""
    if not isinstance(name, str):
        raise ValueError("run type must be a string, got %r" % (name,))
    key = name.strip().lower()
    if key not in RECOGNIZED_RUN_TYPES:
        raise ValueError(
            "unrecognized run type %r; recognized: %s"
            % (name, ", ".join(RECOGNIZED_RUN_TYPES))
        )
    return key


def validate_level_search(points):
    """Validate one descending injected-level search and normalize it.

    points: ordered records of {level_dbuv, disturbance}. The search starts at
    a level where the indication is present and steps down until it ceases.
    """
    where = "level_search"
    if not isinstance(points, (list, tuple)):
        raise ValueError("%s: points must be a list" % where)
    if len(points) < 2:
        raise ValueError(
            "%s: a search needs at least a disturbed and an undisturbed level" % where
        )
    out = []
    previous = None
    for index, point in enumerate(points):
        tag = "%s[%d]" % (where, index)
        if not isinstance(point, dict):
            raise ValueError("%s: point must be a mapping" % tag)
        level = _number(point, "level_dbuv", tag)
        if previous is not None and level >= previous:
            raise ValueError(
                "%s: injected level must fall strictly (%g dBuV after %g dBuV)"
                % (tag, level, previous)
            )
        previous = level
        out.append({"level_dbuv": level, "disturbance": _flag(point, "disturbance", tag)})

    if not out[0]["disturbance"]:
        raise ValueError(
            "%s: the search must start at a level where the indication is present; "
            "a search that never disturbs the unit has no threshold to record" % where
        )
    ceased = None
    for index, point in enumerate(out):
        if not point["disturbance"]:
            ceased = index
            break
    if ceased is None:
        raise ValueError(
            "%s: the indication is still present at the lowest level searched; "
            "the threshold lies below the sequence and is not yet bracketed" % where
        )
    for point in out[ceased:]:
        if point["disturbance"]:
            raise ValueError(
                "%s: the indication returns at %g dBuV after ceasing higher up; the "
                "search is inconsistent and cannot be reduced to one threshold"
                % (where, point["level_dbuv"])
            )
    return out


def cessation_index(points):
    """Index of the first level at which the indication is no longer present."""
    for index, point in enumerate(points):
        if not point["disturbance"]:
            return index
    raise ValueError("cessation_index: the indication never ceases in this search")


def cessation_level_dbuv(points):
    """Recorded susceptibility threshold: the level at which it ceases."""
    return points[cessation_index(points)]["level_dbuv"]


def last_disturbed_level_dbuv(points):
    """Lowest level at which the indication was still present."""
    index = cessation_index(points)
    if index == 0:
        raise ValueError(
            "last_disturbed_level_dbuv: the search never observed the indication"
        )
    return points[index - 1]["level_dbuv"]


def search_bracket_db(points):
    """Step between the last disturbed level and the recorded threshold."""
    return last_disturbed_level_dbuv(points) - cessation_level_dbuv(points)


def bracket_is_resolved(bracket_db, max_bracket_db=DEFAULT_MAX_BRACKET_DB):
    """True when the step is fine enough for the threshold to be resolved."""
    bound = _number({"v": max_bracket_db}, "v", "max_bracket_db")
    if bound <= 0.0:
        raise ValueError("max_bracket_db must be > 0, got %g" % bound)
    return at_most(bracket_db, bound)


def susceptibility_margin_db(threshold_dbuv, required_level_dbuv):
    """Decibels by which the threshold stands above the required level."""
    return threshold_dbuv - required_level_dbuv


def categorize_margin(margin_db, required_margin_db=DEFAULT_REQUIRED_MARGIN_DB):
    """Categorize one observation by the margin its threshold leaves."""
    required = _number({"v": required_margin_db}, "v", "required_margin_db")
    if required < 0.0:
        raise ValueError("required_margin_db must be >= 0, got %g" % required)
    if margin_db <= 0.0:
        # Disturbed at or below the level the unit is required to withstand.
        return CATEGORY_SUSCEPTIBLE
    if at_least(margin_db, required):
        return CATEGORY_COMPLIANT
    return CATEGORY_MARGINAL


def validate_observation(record):
    """Validate one recorded susceptibility observation and normalize it."""
    where = "observation"
    if not isinstance(record, dict):
        raise ValueError("%s: record must be a mapping" % where)
    frequency = _number(record, "frequency_hz", where)
    if frequency <= 0.0:
        raise ValueError("%s: frequency_hz must be > 0, got %g" % (where, frequency))
    required_level = _number(record, "required_level_dbuv", where)
    return {
        "frequency_hz": frequency,
        "modulation": normalize_modulation(record.get("modulation")),
        "affected_function": _text(record, "affected_function", where),
        "observed_parameter": _text(record, "observed_parameter", where),
        "required_level_dbuv": required_level,
        "search": validate_level_search(record.get("search")),
    }


def determine_threshold(
    record,
    required_margin_db=DEFAULT_REQUIRED_MARGIN_DB,
    max_bracket_db=DEFAULT_MAX_BRACKET_DB,
):
    """Reduce one observation to a recorded threshold and its category."""
    observation = validate_observation(record)
    points = observation["search"]
    threshold = cessation_level_dbuv(points)
    bracket = search_bracket_db(points)
    margin = susceptibility_margin_db(threshold, observation["required_level_dbuv"])
    result = dict(observation)
    result["threshold_dbuv"] = threshold
    result["last_disturbed_dbuv"] = last_disturbed_level_dbuv(points)
    result["bracket_db"] = bracket
    result["resolved"] = bracket_is_resolved(bracket, max_bracket_db)
    result["margin_db"] = margin
    result["category"] = categorize_margin(margin, required_margin_db)
    result["steps"] = len(points)
    return result


def governing_observation(results):
    """Return the observation holding the smallest margin."""
    if not isinstance(results, (list, tuple)) or len(results) == 0:
        raise ValueError("governing_observation: at least one result is required")
    return min(results, key=lambda r: r["margin_db"])


def validate_run_context(context):
    """Validate the run context in which the thresholds were recorded."""
    where = "context"
    if not isinstance(context, dict):
        raise ValueError("%s: record must be a mapping" % where)
    run_type = normalize_run_type(context.get("run_type"))
    if not _flag(context, "function_monitored", where):
        raise ValueError(
            "%s: the affected function must be monitored while the level is "
            "reduced, or the level at which the indication ceases is not observed"
            % where
        )
    required_margin = _number(context, "required_margin_db", where)
    if required_margin < 0.0:
        raise ValueError(
            "%s: required_margin_db must be >= 0, got %g" % (where, required_margin)
        )
    max_bracket = _number(context, "max_bracket_db", where)
    if max_bracket <= 0.0:
        raise ValueError("%s: max_bracket_db must be > 0, got %g" % (where, max_bracket))
    return {
        "run_type": run_type,
        "function_monitored": True,
        "required_margin_db": required_margin,
        "max_bracket_db": max_bracket,
    }


def assess_susceptibility_thresholds(context, observations):
    """Full clause 5.2.10.3 assessment of a set of recorded observations."""
    run = validate_run_context(context)
    if not isinstance(observations, (list, tuple)) or len(observations) == 0:
        raise ValueError("observations: at least one recorded observation is required")

    results = [
        determine_threshold(record, run["required_margin_db"], run["max_bracket_db"])
        for record in observations
    ]
    results.sort(key=lambda r: r["frequency_hz"])

    counts = dict((category, 0) for category in CATEGORIES)
    findings = []
    limitations = []
    for result in results:
        counts[result["category"]] += 1
        if result["category"] == CATEGORY_SUSCEPTIBLE:
            findings.append(
                "susceptibility of %s at %g Hz: threshold %.1f dBuV, margin %.1f dB"
                % (
                    result["affected_function"],
                    result["frequency_hz"],
                    result["threshold_dbuv"],
                    result["margin_db"],
                )
            )
        elif result["category"] == CATEGORY_MARGINAL:
            limitations.append(
                "margin of only %.1f dB on %s at %g Hz"
                % (result["margin_db"], result["affected_function"], result["frequency_hz"])
            )
        if not result["resolved"]:
            limitations.append(
                "threshold at %g Hz bracketed to %.1f dB only"
                % (result["frequency_hz"], result["bracket_db"])
            )

    governing = governing_observation(results)
    return {
        "context": run,
        "observations": results,
        "counts": counts,
        "governing_frequency_hz": governing["frequency_hz"],
        "governing_margin_db": governing["margin_db"],
        "findings": findings,
        "limitations": limitations,
        "verdict": "immunity-demonstrated" if not findings else "susceptibility-finding",
    }
