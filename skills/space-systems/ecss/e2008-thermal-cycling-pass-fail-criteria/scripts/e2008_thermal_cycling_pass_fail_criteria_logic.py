#!/usr/bin/env python3
"""Acceptance criteria for a thermally cycled photovoltaic-assembly coupon.

Anchor: ECSS-E-ST-20-08C Rev.2 clause 5.5.1.3.5. The procedure below is a
paraphrase into implementable steps; no standard text is reproduced.

A cycling campaign ends with two questions about the coupon, and they
are not the same question:

    continuity    did the string stay electrically whole? A cracked
                  interconnect can read as an open circuit, as a risen
                  series resistance, or as nothing at all between two
                  cycles while showing up as momentary dropouts on the
                  monitor that watched the coupon during the run
    power         did the coupon still deliver what it delivered before?
                  Output power is only comparable between two readings
                  once both have been corrected to the same reference
                  irradiance and the same cell temperature

Both readings are taken after the campaign and compared with the ones
taken before it. The comparison is a ratio against a declared threshold,
so the decision is reproducible and the threshold is visible.

The thresholds below are a declared project criteria set, not a physical
constant: a project substitutes its own source control drawing values.

Standard library only, offline, deterministic.
"""

from __future__ import annotations

import math

COUPON_ACCEPTED = "coupon-accepted"
COUPON_REJECTED = "coupon-rejected"

OPEN_CIRCUIT = "open-circuit"
RESISTANCE_DRIFT = "resistance-drift"
DISCONTINUITY_EVENTS = "discontinuity-events"
POWER_RETENTION = "power-retention"

DEFAULT_ACCEPTANCE_CRITERIA = {
    "max_resistance_drift_ratio": 0.05,
    "max_discontinuity_events": 0,
    "min_power_retention_ratio": 0.98,
    "reference_temperature_c": 25.0,
    "reference_irradiance_w_m2": 1367.0,
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


def validate_acceptance_criteria(criteria):
    """Check a criteria set is complete and internally sensible."""
    if not isinstance(criteria, dict):
        raise ValueError("criteria must be a mapping, got %r" % (criteria,))
    drift = _require_non_negative(
        "max_resistance_drift_ratio", criteria.get("max_resistance_drift_ratio")
    )
    if drift >= 1.0:
        raise ValueError(
            "max_resistance_drift_ratio %g allows the series resistance to "
            "double; that is not an acceptance criterion" % drift
        )
    events = criteria.get("max_discontinuity_events")
    if not isinstance(events, int) or isinstance(events, bool) or events < 0:
        raise ValueError(
            "max_discontinuity_events must be a non-negative integer, got %r"
            % (events,)
        )
    retention = _require_positive(
        "min_power_retention_ratio", criteria.get("min_power_retention_ratio")
    )
    if retention > 1.0:
        raise ValueError(
            "min_power_retention_ratio %g demands more power after cycling "
            "than before it" % retention
        )
    _require_number("reference_temperature_c", criteria.get("reference_temperature_c"))
    _require_positive(
        "reference_irradiance_w_m2", criteria.get("reference_irradiance_w_m2")
    )
    return criteria


def correct_power_to_reference(
    reading,
    power_temperature_coefficient_per_k,
    criteria=DEFAULT_ACCEPTANCE_CRITERIA,
):
    """Bring one output-power reading to the reference conditions.

    A reading taken warmer or under weaker illumination than the
    reference is not comparable with one taken at the reference. Scaling
    by the irradiance ratio and dividing out the temperature coefficient
    makes the before and after readings answer the same question.
    """
    validate_acceptance_criteria(criteria)
    if not isinstance(reading, dict):
        raise ValueError("reading must be a mapping, got %r" % (reading,))
    power = _require_non_negative("power_w", reading.get("power_w"))
    temperature = _require_number(
        "cell_temperature_c", reading.get("cell_temperature_c")
    )
    if temperature <= -273.15:
        raise ValueError(
            "cell_temperature_c %g C is at or below absolute zero" % temperature
        )
    irradiance = _require_positive("irradiance_w_m2", reading.get("irradiance_w_m2"))
    alpha = _require_number(
        "power_temperature_coefficient_per_k", power_temperature_coefficient_per_k
    )
    if not _at_most(abs(alpha), 0.05):
        raise ValueError(
            "power_temperature_coefficient_per_k %g is outside the physically "
            "plausible band for a photovoltaic cell" % alpha
        )
    delta_t = temperature - float(criteria["reference_temperature_c"])
    temperature_factor = 1.0 + alpha * delta_t
    if temperature_factor <= 0.0:
        raise ValueError(
            "the temperature correction inverts the reading; the coefficient "
            "and the temperature delta are inconsistent"
        )
    irradiance_factor = float(criteria["reference_irradiance_w_m2"]) / irradiance
    return power * irradiance_factor / temperature_factor


def resistance_drift_ratio(before_ohm, after_ohm):
    """Fractional rise in string series resistance across the campaign."""
    before = _require_positive("before_ohm", before_ohm)
    after = _require_non_negative("after_ohm", after_ohm)
    return (after - before) / before


def evaluate_continuity(
    before_ohm,
    after_ohm,
    discontinuity_events,
    criteria=DEFAULT_ACCEPTANCE_CRITERIA,
):
    """Decide whether the coupon stayed electrically whole.

    An after-reading of None stands for a string that no longer conducts.
    That is not a large drift, it is an open circuit, and it is reported
    as its own criterion rather than as a number.
    """
    validate_acceptance_criteria(criteria)
    if not isinstance(discontinuity_events, int) or isinstance(
        discontinuity_events, bool
    ):
        raise ValueError(
            "discontinuity_events must be an integer, got %r" % (discontinuity_events,)
        )
    if discontinuity_events < 0:
        raise ValueError(
            "discontinuity_events must not be negative, got %r" % (discontinuity_events,)
        )
    failed = []
    findings = []
    if after_ohm is None or (
        isinstance(after_ohm, float) and math.isinf(after_ohm)
    ):
        _require_positive("before_ohm", before_ohm)
        failed.append(OPEN_CIRCUIT)
        findings.append("the string reads open after cycling")
        drift = None
    else:
        drift = resistance_drift_ratio(before_ohm, after_ohm)
        if not _at_most(drift, float(criteria["max_resistance_drift_ratio"])):
            failed.append(RESISTANCE_DRIFT)
            findings.append(
                "series resistance rose %.4f against an allowed %.4f"
                % (drift, criteria["max_resistance_drift_ratio"])
            )
    if discontinuity_events > int(criteria["max_discontinuity_events"]):
        failed.append(DISCONTINUITY_EVENTS)
        findings.append(
            "%d monitored discontinuity events against an allowed %d"
            % (discontinuity_events, criteria["max_discontinuity_events"])
        )
    return {
        "drift_ratio": drift,
        "open_circuit": OPEN_CIRCUIT in failed,
        "discontinuity_events": discontinuity_events,
        "failed_criteria": failed,
        "compliant": not failed,
        "findings": findings,
    }


def power_retention_ratio(
    before_reading,
    after_reading,
    power_temperature_coefficient_per_k,
    criteria=DEFAULT_ACCEPTANCE_CRITERIA,
):
    """Corrected output power after the campaign over the power before it."""
    before = correct_power_to_reference(
        before_reading, power_temperature_coefficient_per_k, criteria
    )
    after = correct_power_to_reference(
        after_reading, power_temperature_coefficient_per_k, criteria
    )
    if before <= 0.0:
        raise ValueError(
            "the corrected pre-cycling power is zero; there is nothing to "
            "retain against"
        )
    return after / before


def evaluate_power_retention(
    before_reading,
    after_reading,
    power_temperature_coefficient_per_k,
    criteria=DEFAULT_ACCEPTANCE_CRITERIA,
):
    """Decide whether the coupon held on to its output power."""
    validate_acceptance_criteria(criteria)
    ratio = power_retention_ratio(
        before_reading, after_reading, power_temperature_coefficient_per_k, criteria
    )
    threshold = float(criteria["min_power_retention_ratio"])
    compliant = _at_least(ratio, threshold)
    findings = []
    if not compliant:
        findings.append(
            "corrected output power retained %.4f of the pre-cycling value "
            "against a required %.4f" % (ratio, threshold)
        )
    return {
        "retention_ratio": ratio,
        "loss_ratio": 1.0 - ratio,
        "compliant": compliant,
        "findings": findings,
    }


def evaluate_cycling_acceptance(case, criteria=DEFAULT_ACCEPTANCE_CRITERIA):
    """Full clause 5.5.1.3.5 acceptance decision for one cycled coupon."""
    if not isinstance(case, dict):
        raise ValueError("case must be a mapping, got %r" % (case,))
    validate_acceptance_criteria(criteria)
    for key in ("before_resistance_ohm", "after_resistance_ohm"):
        if key not in case:
            raise ValueError(
                "case is missing %s; an absent reading is not an open circuit" % key
            )
    continuity = evaluate_continuity(
        case["before_resistance_ohm"],
        case["after_resistance_ohm"],
        case.get("discontinuity_events", 0),
        criteria,
    )
    power = evaluate_power_retention(
        case.get("before_reading"),
        case.get("after_reading"),
        case.get("power_temperature_coefficient_per_k"),
        criteria,
    )
    failed = list(continuity["failed_criteria"])
    if not power["compliant"]:
        failed.append(POWER_RETENTION)
    findings = list(continuity["findings"]) + list(power["findings"])
    accepted = not failed
    return {
        "drift_ratio": continuity["drift_ratio"],
        "open_circuit": continuity["open_circuit"],
        "discontinuity_events": continuity["discontinuity_events"],
        "retention_ratio": power["retention_ratio"],
        "failed_criteria": failed,
        "accepted": accepted,
        "verdict": COUPON_ACCEPTED if accepted else COUPON_REJECTED,
        "findings": findings,
    }
