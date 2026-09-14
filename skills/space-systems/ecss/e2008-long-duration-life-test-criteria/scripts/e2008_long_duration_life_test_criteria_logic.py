#!/usr/bin/env python3
"""Acceptance criterion for the long duration life test of an assembly.

Anchor: ECSS-E-ST-20-08C clause 6.4.3.18.3. The procedure below is a
paraphrase into implementable steps; no standard text is reproduced.

The criterion is one number and one adverbial phrase, and the phrase is
where campaigns lose it: the maximum power degradation stays inside two
per cent, and it stays there across the whole life test.

Across the whole test is not the same as at the end of it. An assembly
that drops three per cent at four thousand hours and reads back at one
and a half per cent at eight thousand has been outside the criterion,
and the recovery is itself a finding -- something reversible is moving
in the article, usually moisture in an encapsulant or an interconnect
making and breaking contact with temperature. Grading endpoints only
turns that into a pass and throws away the one measurement that showed
it.

Degradation is measured against the initial reading of this same test,
not against a datasheet figure and not against the subgroup average. A
life test is a self-referencing measurement: the article is being
compared with itself, so a missing initial reading closes the assessment
rather than being replaced by a nominal.

Readings have to be comparable before they can be differenced. Maximum
power moves with irradiance and with cell temperature, so each reading
is translated to the declared reference conditions first, through the
irradiance ratio and the power temperature coefficient. Differencing raw
watts taken on a warm afternoon against watts taken on a cold morning
reports the weather, not the article.

The limit is a ceiling with the tie admissible: a reading landing
exactly on two per cent is inside. The limit, the reference conditions
and the temperature coefficient below are declared policy, not physical
constants: a project substitutes its own.

Standard library only, offline, deterministic.
"""

from __future__ import annotations

import math

REFERENCE_NOT_ESTABLISHED = "initial-reference-not-established"
DEGRADATION_WITHIN_LIMIT = "degradation-within-limit"
DEGRADATION_EXCEEDS_LIMIT = "degradation-exceeds-limit"

DEFAULT_CRITERIA_POLICY = {
    "maximum_power_degradation_percent": 2.0,
    "reference_irradiance_w_per_m2": 1367.0,
    "reference_temperature_c": 25.0,
    "power_temperature_coefficient_per_c": -0.0035,
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


def _require_label(name, value):
    if not isinstance(value, str):
        raise ValueError("%s must be a string, got %r" % (name, value))
    return value.strip()


def _at_most(value, limit):
    """value <= limit, absorbing floating-point representation error."""
    return value <= limit or math.isclose(
        value, limit, rel_tol=_REL_TOL, abs_tol=_ABS_TOL
    )


def validate_criteria_policy(policy):
    """Check an acceptance policy is complete and physically sensible."""
    if not isinstance(policy, dict):
        raise ValueError("policy must be a mapping, got %r" % (policy,))
    limit = _require_positive(
        "maximum_power_degradation_percent",
        policy.get("maximum_power_degradation_percent"),
    )
    if limit >= 100.0:
        raise ValueError(
            "maximum_power_degradation_percent %g admits an assembly that "
            "delivers nothing at the end of the test" % limit
        )
    _require_positive(
        "reference_irradiance_w_per_m2",
        policy.get("reference_irradiance_w_per_m2"),
    )
    _require_number(
        "reference_temperature_c", policy.get("reference_temperature_c")
    )
    coefficient = _require_number(
        "power_temperature_coefficient_per_c",
        policy.get("power_temperature_coefficient_per_c"),
    )
    if coefficient >= 0.0:
        raise ValueError(
            "power_temperature_coefficient_per_c %g is not negative; maximum "
            "power falls as a cell warms" % coefficient
        )
    if coefficient <= -0.05:
        raise ValueError(
            "power_temperature_coefficient_per_c %g is far outside the range "
            "photovoltaic cells occupy" % coefficient
        )
    return policy


def validate_reading(reading):
    """Check one maximum power reading of the life test."""
    if not isinstance(reading, dict):
        raise ValueError("reading must be a mapping, got %r" % (reading,))
    label = _require_label("reading label", reading.get("label"))
    if not label:
        raise ValueError("reading label must not be blank")
    elapsed = _require_non_negative(
        "elapsed_hours on %s" % label, reading.get("elapsed_hours")
    )
    pmax = _require_positive("pmax_w on %s" % label, reading.get("pmax_w"))
    irradiance = _require_positive(
        "irradiance_w_per_m2 on %s" % label, reading.get("irradiance_w_per_m2")
    )
    temperature = _require_number(
        "cell_temperature_c on %s" % label, reading.get("cell_temperature_c")
    )
    return {
        "label": label,
        "elapsed_hours": elapsed,
        "pmax_w": pmax,
        "irradiance_w_per_m2": irradiance,
        "cell_temperature_c": temperature,
    }


def corrected_pmax_w(reading, policy=DEFAULT_CRITERIA_POLICY):
    """Maximum power of one reading translated to the reference conditions."""
    validate_criteria_policy(policy)
    record = validate_reading(reading)
    irradiance_ratio = (
        float(policy["reference_irradiance_w_per_m2"])
        / record["irradiance_w_per_m2"]
    )
    temperature_factor = 1.0 + float(
        policy["power_temperature_coefficient_per_c"]
    ) * (record["cell_temperature_c"] - float(policy["reference_temperature_c"]))
    if temperature_factor <= 0.0:
        raise ValueError(
            "reading %s sits so far off the reference temperature that the "
            "linear correction inverts; measure it closer to reference "
            "conditions" % record["label"]
        )
    return record["pmax_w"] * irradiance_ratio / temperature_factor


def reading_series(readings, policy=DEFAULT_CRITERIA_POLICY):
    """The life test readings, validated, corrected and ordered in time."""
    if not isinstance(readings, (list, tuple)):
        raise ValueError("readings must be a sequence of reading records")
    if not readings:
        raise ValueError(
            "the life test recorded no reading, so there is no degradation to "
            "judge"
        )
    series = []
    elapsed_seen = []
    labels_seen = []
    for reading in readings:
        record = validate_reading(reading)
        if record["elapsed_hours"] in elapsed_seen:
            raise ValueError(
                "two readings share elapsed hour %g; the series has to be a "
                "single article through one test"
                % record["elapsed_hours"]
            )
        if record["label"] in labels_seen:
            raise ValueError("duplicate reading label %r" % record["label"])
        elapsed_seen.append(record["elapsed_hours"])
        labels_seen.append(record["label"])
        record["corrected_pmax_w"] = corrected_pmax_w(reading, policy)
        series.append(record)
    series.sort(key=lambda record: record["elapsed_hours"])
    return tuple(series)


def initial_reference_w(series):
    """Corrected maximum power of the reading that opens the test."""
    if not isinstance(series, (list, tuple)) or not series:
        raise ValueError("series must be a non-empty sequence of readings")
    first = series[0]
    if first["elapsed_hours"] != 0.0:
        return None
    return first["corrected_pmax_w"]


def degradation_percent(reference_w, corrected_w):
    """Fall from the initial reading, as a percentage of it."""
    reference = _require_positive("reference_w", reference_w)
    corrected = _require_positive("corrected_w", corrected_w)
    return ((reference - corrected) / reference) * 100.0


def series_degradations(series, reference_w):
    """Degradation at every reading of the test, in time order."""
    reference = _require_positive("reference_w", reference_w)
    if not isinstance(series, (list, tuple)) or not series:
        raise ValueError("series must be a non-empty sequence of readings")
    return tuple(
        {
            "label": record["label"],
            "elapsed_hours": record["elapsed_hours"],
            "degradation_percent": degradation_percent(
                reference, record["corrected_pmax_w"]
            ),
        }
        for record in series
    )


def maximum_degradation_percent(degradations):
    """Worst degradation anywhere in the test, not the final one."""
    if not isinstance(degradations, (list, tuple)) or not degradations:
        raise ValueError("degradations must be a non-empty sequence")
    return max(entry["degradation_percent"] for entry in degradations)


def worst_reading(degradations):
    """The reading that carried the worst degradation, earliest on a tie."""
    if not isinstance(degradations, (list, tuple)) or not degradations:
        raise ValueError("degradations must be a non-empty sequence")
    worst = degradations[0]
    for entry in degradations[1:]:
        if entry["degradation_percent"] > worst["degradation_percent"]:
            worst = entry
    return worst


def within_limit(degradation, limit):
    """True while the degradation stays inside the limit; a tie is admissible."""
    value = _require_number("degradation", degradation)
    ceiling = _require_positive("limit", limit)
    return _at_most(value, ceiling)


def recovered_excursions(degradations, limit):
    """Readings that went outside the limit before the test came back inside.

    These do not soften the verdict -- the criterion holds across the whole
    test -- but a reversible excursion says something real about the
    article, so it is reported rather than smoothed over by the last
    reading.
    """
    ceiling = _require_positive("limit", limit)
    if not isinstance(degradations, (list, tuple)) or not degradations:
        raise ValueError("degradations must be a non-empty sequence")
    final = degradations[-1]["degradation_percent"]
    if not within_limit(final, ceiling):
        return ()
    excursions = []
    for entry in degradations[:-1]:
        if not within_limit(entry["degradation_percent"], ceiling):
            excursions.append(
                "reading %s at %g hours reached %.3f per cent before the test "
                "came back inside the %.3f per cent limit; something "
                "reversible is moving in the article"
                % (
                    entry["label"],
                    entry["elapsed_hours"],
                    entry["degradation_percent"],
                    ceiling,
                )
            )
    return tuple(excursions)


def assess_long_duration_life_test_criteria(case, policy=DEFAULT_CRITERIA_POLICY):
    """Full clause 6.4.3.18.3 acceptance decision for one life test."""
    if not isinstance(case, dict):
        raise ValueError("case must be a mapping, got %r" % (case,))
    validate_criteria_policy(policy)
    limit = float(policy["maximum_power_degradation_percent"])

    findings = []
    advisories = []
    result = {
        "limit_percent": limit,
        "initial_reference_w": None,
        "final_degradation_percent": None,
        "maximum_degradation_percent": None,
        "worst_reading_label": None,
        "worst_reading_elapsed_hours": None,
        "degradations": (),
        "findings": findings,
        "advisories": advisories,
    }

    readings = case.get("readings")
    if readings is None:
        findings.append(
            "the life test record carries no reading, so there is no "
            "degradation for this criterion to grade"
        )
        result["verdict"] = REFERENCE_NOT_ESTABLISHED
        return result

    series = reading_series(readings, policy)
    reference = initial_reference_w(series)
    if reference is None:
        findings.append(
            "the series has no reading at zero elapsed hours; degradation in a "
            "life test is measured against the initial reading of that same "
            "test, not against a nominal"
        )
        result["verdict"] = REFERENCE_NOT_ESTABLISHED
        return result
    result["initial_reference_w"] = reference

    if len(series) < 2:
        findings.append(
            "the series holds the initial reading only; a criterion that has "
            "to hold across the whole test needs the test to have been "
            "measured across"
        )
        result["verdict"] = REFERENCE_NOT_ESTABLISHED
        return result

    degradations = series_degradations(series, reference)
    worst = worst_reading(degradations)
    maximum = maximum_degradation_percent(degradations)

    result["degradations"] = degradations
    result["final_degradation_percent"] = degradations[-1]["degradation_percent"]
    result["maximum_degradation_percent"] = maximum
    result["worst_reading_label"] = worst["label"]
    result["worst_reading_elapsed_hours"] = worst["elapsed_hours"]

    advisories.extend(recovered_excursions(degradations, limit))

    if within_limit(maximum, limit):
        result["verdict"] = DEGRADATION_WITHIN_LIMIT
        return result

    findings.append(
        "reading %s at %g hours degraded %.3f per cent, outside the %.3f per "
        "cent the criterion allows anywhere in the test"
        % (worst["label"], worst["elapsed_hours"], maximum, limit)
    )
    result["verdict"] = DEGRADATION_EXCEEDS_LIMIT
    return result
