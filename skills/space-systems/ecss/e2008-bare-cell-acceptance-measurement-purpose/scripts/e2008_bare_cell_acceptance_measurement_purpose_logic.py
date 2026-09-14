#!/usr/bin/env python3
"""Purpose of the bare-cell electrical measurement at acceptance.

Anchor: ECSS-E-ST-20-08C clause 7.3.2.2.1. The procedure below is a
paraphrase into implementable steps; no standard text is reproduced.

A bare cell -- a photovoltaic cell before any coverglass, interconnector
or substrate is attached to it -- has its electrical parameters measured
during acceptance testing. This module answers the question that comes
before the bench is switched on: what has that measurement got to
deliver, and can the measurement as planned deliver it.

Three things decide that.

The decisions the numbers feed. Bare-cell current is not measured for
its own sake. It feeds lot conformity against the source control
drawing, the string and power-budget sizing that the array design rests
on, the baseline that later degradation is read against, and the
screening of a batch into usable and rejected cells. Each of those
decisions leans on a particular parameter, and a plan that does not
measure that parameter cannot serve the decision however carefully it
is run.

The quantities the parameters imply. The short-circuit current and the
current drawn at the stated on-load test voltage give the operating
point power directly, and together with the open-circuit voltage they
give a fill-factor proxy -- the share of the current-voltage rectangle
the cell actually occupies. These are what the acceptance decision is
really about, so they are computed here rather than left to whoever
reads the record.

The resolution the plan has. An acceptance limit defines a band between
the drawing minimum and the nominal cell. If the combined measurement
uncertainty -- irradiance setting, cell temperature, illuminated area,
instrument -- is a large share of that band, the run cannot separate a
conforming cell from a rejected one, and it produces a record that
looks like a decision without being one. The components combine in
quadrature because they are independent, and the ratio of band to
uncertainty is the discrimination the plan has.

The policy numbers below are declared project values, not physical
constants: a project substitutes its own.

Standard library only, offline, deterministic.
"""

from __future__ import annotations

import math

LOT_CONFORMITY = "lot-conformity"
ARRAY_SIZING = "array-sizing"
DEGRADATION_BASELINE = "degradation-baseline"
BATCH_SCREENING = "batch-screening"

SHORT_CIRCUIT_CURRENT = "short-circuit-current"
CURRENT_AT_TEST_VOLTAGE = "current-at-test-voltage"
OPEN_CIRCUIT_VOLTAGE = "open-circuit-voltage"

RECOGNISED_PARAMETERS = (
    SHORT_CIRCUIT_CURRENT,
    CURRENT_AT_TEST_VOLTAGE,
    OPEN_CIRCUIT_VOLTAGE,
)

DECISION_PARAMETERS = {
    LOT_CONFORMITY: (SHORT_CIRCUIT_CURRENT, CURRENT_AT_TEST_VOLTAGE),
    ARRAY_SIZING: (CURRENT_AT_TEST_VOLTAGE,),
    DEGRADATION_BASELINE: (SHORT_CIRCUIT_CURRENT,),
    BATCH_SCREENING: (SHORT_CIRCUIT_CURRENT, CURRENT_AT_TEST_VOLTAGE),
}

DECISION_OBJECTIVES = {
    LOT_CONFORMITY: (
        "show each delivered bare cell reaches the currents the source "
        "control drawing fixes"
    ),
    ARRAY_SIZING: (
        "give the array design the on-load current a string is sized from"
    ),
    DEGRADATION_BASELINE: (
        "fix the pre-environment baseline later degradation is read against"
    ),
    BATCH_SCREENING: (
        "group a delivered batch into cells that may be laid down and cells "
        "that may not"
    ),
}

SHARED_OBJECTIVE = (
    "record the bare-cell currents with a stated illumination and "
    "temperature so a later reviewer can reproduce the acceptance decision"
)

NO_DECISION_DECLARED = "no-acceptance-decision-declared"
PLAN_NOT_ESTABLISHED = "measurement-plan-not-established"
PARAMETER_COVERAGE_INCOMPLETE = "parameter-coverage-incomplete"
MEASUREMENT_CANNOT_DISCRIMINATE = "measurement-cannot-discriminate"
PURPOSE_ESTABLISHED = "bare-cell-measurement-purpose-established"

DEFAULT_PURPOSE_POLICY = {
    "min_discrimination_ratio": 4.0,
    "max_uncertainty_fraction_of_band": 0.25,
}

_REL_TOL = 1e-9
_ABS_TOL = 1e-15


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


def _at_least(value, limit):
    """value >= limit, absorbing floating-point representation error."""
    return value >= limit or math.isclose(
        value, limit, rel_tol=_REL_TOL, abs_tol=_ABS_TOL
    )


def validate_purpose_policy(policy):
    """Check the scoping policy is complete and internally sensible."""
    if not isinstance(policy, dict):
        raise ValueError("policy must be a mapping, got %r" % (policy,))
    ratio = _require_positive(
        "min_discrimination_ratio", policy.get("min_discrimination_ratio")
    )
    fraction = _require_positive(
        "max_uncertainty_fraction_of_band",
        policy.get("max_uncertainty_fraction_of_band"),
    )
    if fraction > 1.0:
        raise ValueError(
            "max_uncertainty_fraction_of_band %g is above one; an uncertainty "
            "wider than the acceptance band cannot admit any plan" % fraction
        )
    if ratio < 1.0:
        raise ValueError(
            "min_discrimination_ratio %g is below one; a band narrower than "
            "its own uncertainty is not a decision" % ratio
        )
    return policy


def acceptance_decision_inventory(decisions):
    """Group the declared acceptance decisions and the parameters they need.

    An unrecognised decision is refused rather than dropped: a decision
    nobody mapped is a decision nobody scoped the measurement for.
    """
    if not isinstance(decisions, (list, tuple)):
        raise ValueError("decisions must be a sequence, got %r" % (decisions,))
    inventory = []
    seen = set()
    for entry in decisions:
        name = _require_label("acceptance decision", entry)
        if not name:
            raise ValueError("an acceptance decision must not be blank")
        if name not in DECISION_PARAMETERS:
            raise ValueError(
                "unrecognised acceptance decision %r; recognised decisions "
                "are %s" % (name, ", ".join(sorted(DECISION_PARAMETERS)))
            )
        if name in seen:
            raise ValueError("duplicate acceptance decision %r" % name)
        seen.add(name)
        inventory.append(
            {
                "decision": name,
                "parameters": DECISION_PARAMETERS[name],
                "objective": DECISION_OBJECTIVES[name],
            }
        )
    return tuple(inventory)


def required_parameters(decisions):
    """The union of parameters the declared decisions lean on, ordered."""
    inventory = acceptance_decision_inventory(decisions)
    wanted = []
    for entry in inventory:
        for parameter in entry["parameters"]:
            if parameter not in wanted:
                wanted.append(parameter)
    return tuple(
        parameter for parameter in RECOGNISED_PARAMETERS if parameter in wanted
    )


def validate_measurement_plan(plan):
    """Check a planned bare-cell measurement can be reasoned about."""
    if not isinstance(plan, dict):
        raise ValueError("plan must be a mapping, got %r" % (plan,))
    parameters = plan.get("planned_parameters")
    if not isinstance(parameters, (list, tuple)):
        raise ValueError("plan must record planned_parameters as a sequence")
    cleaned = []
    for entry in parameters:
        name = _require_label("planned parameter", entry)
        if name not in RECOGNISED_PARAMETERS:
            raise ValueError(
                "unrecognised planned parameter %r; recognised parameters "
                "are %s" % (name, ", ".join(RECOGNISED_PARAMETERS))
            )
        if name in cleaned:
            raise ValueError("duplicate planned parameter %r" % name)
        cleaned.append(name)
    if not cleaned:
        raise ValueError(
            "the plan measures no parameter at all, so there is nothing for "
            "an acceptance decision to rest on"
        )
    return tuple(cleaned)


def operating_point_power_w(current_at_voltage_a, test_voltage_v):
    """Power the bare cell delivers at the stated on-load test voltage."""
    current = _require_positive("current_at_voltage_a", current_at_voltage_a)
    voltage = _require_positive("test_voltage_v", test_voltage_v)
    return current * voltage


def fill_factor_proxy(
    current_at_voltage_a,
    test_voltage_v,
    short_circuit_current_a,
    open_circuit_voltage_v,
):
    """Share of the current-voltage rectangle the stated point occupies."""
    current = _require_positive("current_at_voltage_a", current_at_voltage_a)
    voltage = _require_positive("test_voltage_v", test_voltage_v)
    short_circuit = _require_positive(
        "short_circuit_current_a", short_circuit_current_a
    )
    open_circuit = _require_positive(
        "open_circuit_voltage_v", open_circuit_voltage_v
    )
    if current > short_circuit and not math.isclose(
        current, short_circuit, rel_tol=_REL_TOL, abs_tol=_ABS_TOL
    ):
        raise ValueError(
            "on-load current %g A exceeds the %g A short-circuit current, "
            "which no cell does" % (current, short_circuit)
        )
    if voltage > open_circuit and not math.isclose(
        voltage, open_circuit, rel_tol=_REL_TOL, abs_tol=_ABS_TOL
    ):
        raise ValueError(
            "test voltage %g V exceeds the %g V open-circuit voltage, so the "
            "cell delivers no current there" % (voltage, open_circuit)
        )
    return (current * voltage) / (short_circuit * open_circuit)


def combined_relative_uncertainty(components):
    """Root-sum-square of the independent relative uncertainty components."""
    if not isinstance(components, dict):
        raise ValueError("components must be a mapping, got %r" % (components,))
    if not components:
        raise ValueError(
            "no uncertainty component was declared; a plan with no declared "
            "uncertainty has not been scoped, it has been assumed perfect"
        )
    total = 0.0
    for name, value in components.items():
        label = _require_label("uncertainty component name", name)
        if not label:
            raise ValueError("an uncertainty component must not be blank")
        fraction = _require_non_negative("uncertainty component %s" % label, value)
        if fraction > 1.0:
            raise ValueError(
                "uncertainty component %s is %g, above one; a component wider "
                "than the quantity itself is a data error" % (label, fraction)
            )
        total += fraction * fraction
    return math.sqrt(total)


def acceptance_band_fraction(nominal_current_a, minimum_current_a):
    """How far the drawing minimum sits below nominal, as a fraction."""
    nominal = _require_positive("nominal_current_a", nominal_current_a)
    minimum = _require_positive("minimum_current_a", minimum_current_a)
    if minimum > nominal and not math.isclose(
        minimum, nominal, rel_tol=_REL_TOL, abs_tol=_ABS_TOL
    ):
        raise ValueError(
            "the %g A drawing minimum is above the %g A nominal, so the band "
            "is inverted and no cell can meet it" % (minimum, nominal)
        )
    return (nominal - minimum) / nominal


def discrimination_ratio(band_fraction, uncertainty_fraction):
    """Acceptance band measured in units of the measurement uncertainty."""
    band = _require_non_negative("band_fraction", band_fraction)
    uncertainty = _require_positive("uncertainty_fraction", uncertainty_fraction)
    return band / uncertainty


def measurement_resolves_band(
    band_fraction, uncertainty_fraction, policy=DEFAULT_PURPOSE_POLICY
):
    """True when the plan can separate a conforming cell from a rejected one."""
    validate_purpose_policy(policy)
    ratio = discrimination_ratio(band_fraction, uncertainty_fraction)
    band = _require_non_negative("band_fraction", band_fraction)
    uncertainty = _require_positive("uncertainty_fraction", uncertainty_fraction)
    share = uncertainty / band if band > 0.0 else float("inf")
    if not _at_least(ratio, float(policy["min_discrimination_ratio"])):
        return False
    return _at_least(float(policy["max_uncertainty_fraction_of_band"]), share)


def assess_bare_cell_measurement_purpose(case, policy=DEFAULT_PURPOSE_POLICY):
    """Full clause 7.3.2.2.1 scoping decision for one bare-cell measurement."""
    if not isinstance(case, dict):
        raise ValueError("case must be a mapping, got %r" % (case,))
    validate_purpose_policy(policy)

    findings = []
    result = {
        "decisions": (),
        "objectives": (),
        "required_parameters": (),
        "planned_parameters": (),
        "missing_parameters": (),
        "operating_point_power_w": None,
        "fill_factor_proxy": None,
        "combined_relative_uncertainty": None,
        "acceptance_band_fraction": None,
        "discrimination_ratio": None,
        "findings": findings,
    }

    decisions = case.get("acceptance_decisions")
    if decisions is None:
        raise ValueError("case is missing an acceptance_decisions record")
    inventory = acceptance_decision_inventory(decisions)
    result["decisions"] = tuple(entry["decision"] for entry in inventory)
    if not inventory:
        findings.append(
            "no acceptance decision is declared, so no bare-cell parameter "
            "has anything to feed and the measurement has no purpose to scope"
        )
        result["verdict"] = NO_DECISION_DECLARED
        return result

    result["objectives"] = tuple(
        [entry["objective"] for entry in inventory] + [SHARED_OBJECTIVE]
    )
    wanted = required_parameters(decisions)
    result["required_parameters"] = wanted

    plan = case.get("measurement_plan")
    if plan is None:
        findings.append(
            "acceptance decisions are declared but no measurement is planned, "
            "so nothing will reach them"
        )
        result["verdict"] = PLAN_NOT_ESTABLISHED
        return result
    planned = validate_measurement_plan(plan)
    result["planned_parameters"] = planned

    missing = tuple(name for name in wanted if name not in planned)
    result["missing_parameters"] = missing
    if missing:
        for name in missing:
            findings.append(
                "the plan does not measure %s, which the declared decisions "
                "lean on" % name
            )
        result["verdict"] = PARAMETER_COVERAGE_INCOMPLETE
        return result

    cell = case.get("nominal_cell")
    if isinstance(cell, dict):
        current = _require_positive(
            "current_at_test_voltage_a", cell.get("current_at_test_voltage_a")
        )
        voltage = _require_positive("test_voltage_v", cell.get("test_voltage_v"))
        result["operating_point_power_w"] = operating_point_power_w(
            current, voltage
        )
        if cell.get("open_circuit_voltage_v") is not None:
            result["fill_factor_proxy"] = fill_factor_proxy(
                current,
                voltage,
                cell.get("short_circuit_current_a"),
                cell.get("open_circuit_voltage_v"),
            )

    uncertainty = combined_relative_uncertainty(
        plan.get("relative_uncertainty_components")
    )
    result["combined_relative_uncertainty"] = uncertainty

    limits = case.get("drawing_band")
    if not isinstance(limits, dict):
        raise ValueError("case is missing a drawing_band record")
    band = acceptance_band_fraction(
        limits.get("nominal_current_a"), limits.get("minimum_current_a")
    )
    result["acceptance_band_fraction"] = band
    result["discrimination_ratio"] = discrimination_ratio(band, uncertainty)

    if not measurement_resolves_band(band, uncertainty, policy):
        findings.append(
            "the %.3g combined relative uncertainty against a %.3g acceptance "
            "band leaves a discrimination ratio of %.3g, so the run cannot "
            "separate a conforming cell from a rejected one"
            % (uncertainty, band, result["discrimination_ratio"])
        )
        result["verdict"] = MEASUREMENT_CANNOT_DISCRIMINATE
        return result

    result["verdict"] = PURPOSE_ESTABLISHED
    return result
