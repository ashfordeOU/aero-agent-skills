#!/usr/bin/env python3
"""The function controlling commercial EEE parts at the intermediate class.

Anchor: ECSS-Q-ST-60-13C clause 5.1.2.1. The procedure below is a
paraphrase into implementable steps; no standard text is reproduced.

The clause asks which organizational function controls commercial EEE
parts when the programme sits at the intermediate assurance class. The
intermediate class is not the highest class with the numbers relaxed; it
is a different shape of answer, and three things follow from that.

Duties may be delegated here, and delegation is what separates this class
from the one above it. A supporting unit exercising a duty on behalf of
the named function is acceptable, but only where the delegation is
recorded. An unrecorded delegation is not a lighter arrangement, it is a
duty nobody can be shown to hold, and it is reported as such.

Part-selection approval is the one duty that does not travel. Whoever may
say yes to a commercial part entering the design is the function this
clause names, so a programme delegating that duty has not named a
function at all, and two units holding it directly have named two.

Embedding is tolerated, and it is priced. A parts function reporting
inside the design authority can be accepted at this class where a product
assurance escalation route is declared, because the route is what lets a
refusal survive the schedule pressure that the reporting line applies.
With no route declared, the embedding is a finding.

Two coverage figures are carried rather than one. The plain coverage says
how many duties are disposed at all; the effective coverage weighs a
delegated duty at a declared credit below one, so an organization run
entirely through delegation reads differently from one run directly, and
the difference is visible before it matters.

The policy numbers below are declared project values, not physical
constants: a project substitutes its own.

Standard library only, offline, deterministic.
"""

from __future__ import annotations

import math

PART_SELECTION_APPROVAL = "part-selection-approval"
PROCUREMENT_SOURCE_APPROVAL = "procurement-source-approval"
EVALUATION_AND_SCREENING_CONTROL = "evaluation-and-screening-control"
NONCONFORMANCE_AND_ALERT_DISPOSITION = "nonconformance-and-alert-disposition"
OBSOLESCENCE_AND_LIFETIME_BUY_CONTROL = "obsolescence-and-lifetime-buy-control"
PARTS_LIST_CUSTODY = "parts-list-custody"

REQUIRED_DUTIES = (
    PART_SELECTION_APPROVAL,
    PROCUREMENT_SOURCE_APPROVAL,
    EVALUATION_AND_SCREENING_CONTROL,
    NONCONFORMANCE_AND_ALERT_DISPOSITION,
    OBSOLESCENCE_AND_LIFETIME_BUY_CONTROL,
    PARTS_LIST_CUSTODY,
)

NON_DELEGABLE_DUTY = PART_SELECTION_APPROVAL

HELD_DIRECTLY = "held-directly"
HELD_BY_RECORDED_DELEGATION = "held-by-recorded-delegation"
CONTESTED = "contested-between-units"
UNASSIGNED = "unassigned"

FUNCTION_NOT_ESTABLISHED = "parts-function-not-established"
ANCHOR_DUTY_DELEGATED = "part-selection-approval-delegated"
ACCOUNTABILITY_CONTESTED = "parts-accountability-contested"
DUTY_COVERAGE_SHORT = "parts-duty-coverage-short"
ESCALATION_ROUTE_NOT_DECLARED = "product-assurance-escalation-route-not-declared"
ORGANIZATION_MEETS_CLASS_TWO = "parts-organization-meets-class-two"

DEFAULT_ORGANIZATION_POLICY = {
    "min_duty_coverage": 1.0,
    "min_effective_coverage": 0.85,
    "delegated_duty_credit": 0.75,
    "min_competence_years": 3.0,
    "marginal_competence_band_years": 1.0,
    "require_escalation_route_when_embedded": True,
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


def _require_fraction(name, value):
    number = _require_number(name, value)
    if number < 0.0 or number > 1.0:
        raise ValueError("%s must sit between zero and one, got %r" % (name, value))
    return number


def _require_label(name, value):
    if not isinstance(value, str):
        raise ValueError("%s must be a string, got %r" % (name, value))
    return value.strip()


def _require_flag(name, value):
    if not isinstance(value, bool):
        raise ValueError("%s must be true or false, got %r" % (name, value))
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


def validate_organization_policy(policy):
    """Check the organization policy is complete and usable."""
    if not isinstance(policy, dict):
        raise ValueError("policy must be a mapping, got %r" % (policy,))
    coverage = _require_fraction("min_duty_coverage", policy.get("min_duty_coverage"))
    effective = _require_fraction(
        "min_effective_coverage", policy.get("min_effective_coverage")
    )
    if effective > coverage:
        raise ValueError(
            "min_effective_coverage %g is above min_duty_coverage %g; a credited "
            "coverage can never exceed the plain one" % (effective, coverage)
        )
    credit = _require_fraction(
        "delegated_duty_credit", policy.get("delegated_duty_credit")
    )
    if credit <= 0.0:
        raise ValueError(
            "delegated_duty_credit must be greater than zero, got %r" % (credit,)
        )
    competence = _require_positive(
        "min_competence_years", policy.get("min_competence_years")
    )
    band = _require_non_negative(
        "marginal_competence_band_years",
        policy.get("marginal_competence_band_years"),
    )
    if band > competence:
        raise ValueError(
            "marginal_competence_band_years %g is wider than the %g year floor; "
            "every compliant unit would be flagged marginal" % (band, competence)
        )
    _require_flag(
        "require_escalation_route_when_embedded",
        policy.get("require_escalation_route_when_embedded"),
    )
    return policy


def _read_duty_list(name, duties):
    if not isinstance(duties, (list, tuple)):
        raise ValueError("%s must be a sequence of duty names" % name)
    named = []
    for duty in duties:
        label = _require_label("duty in %s" % name, duty)
        if label not in REQUIRED_DUTIES:
            raise ValueError(
                "unrecognised duty %r in %s; the duty names are fixed"
                % (label, name)
            )
        if label in named:
            raise ValueError("duty %r is listed twice in %s" % (label, name))
        named.append(label)
    return tuple(named)


def validate_unit_record(unit):
    """Read one declared unit, the duties it holds and the ones it is lent."""
    if not isinstance(unit, dict):
        raise ValueError("unit must be a mapping, got %r" % (unit,))
    identifier = _require_label("unit id", unit.get("id"))
    if not identifier:
        raise ValueError("unit id must not be blank")
    held = _read_duty_list("duties on %s" % identifier, unit.get("duties"))
    delegated = _read_duty_list(
        "delegated_duties on %s" % identifier, unit.get("delegated_duties", ())
    )
    overlap = [duty for duty in delegated if duty in held]
    if overlap:
        raise ValueError(
            "%s holds %s directly and also under delegation; a duty is one or "
            "the other" % (identifier, ", ".join(overlap))
        )
    delegation_recorded = _require_flag(
        "delegation_recorded on %s" % identifier, unit.get("delegation_recorded", False)
    )
    if delegation_recorded and not delegated:
        raise ValueError(
            "%s declares a recorded delegation but is lent no duty" % identifier
        )
    competence = _require_non_negative(
        "competence_years on %s" % identifier, unit.get("competence_years")
    )
    embedded = _require_flag(
        "embedded_in_design_authority on %s" % identifier,
        unit.get("embedded_in_design_authority"),
    )
    mandated = _require_flag(
        "mandated_in_contract on %s" % identifier, unit.get("mandated_in_contract")
    )
    return {
        "id": identifier,
        "duties": held,
        "delegated_duties": delegated,
        "delegation_recorded": delegation_recorded,
        "competence_years": competence,
        "embedded_in_design_authority": embedded,
        "mandated_in_contract": mandated,
    }


def validate_units(units):
    """Read every declared unit, refusing an empty or duplicated set."""
    if not isinstance(units, (list, tuple)):
        raise ValueError("units must be a sequence of unit records")
    if not units:
        raise ValueError("no unit was declared, so no function controls the parts")
    checked = []
    seen = set()
    for unit in units:
        record = validate_unit_record(unit)
        if record["id"] in seen:
            raise ValueError("duplicate unit id %r in the organization" % record["id"])
        seen.add(record["id"])
        checked.append(record)
    return tuple(checked)


def duty_disposition(units):
    """How each required duty is disposed across the declared units."""
    checked = validate_units(units)
    disposition = {}
    for duty in REQUIRED_DUTIES:
        direct = tuple(unit["id"] for unit in checked if duty in unit["duties"])
        lent = tuple(
            unit["id"]
            for unit in checked
            if duty in unit["delegated_duties"] and unit["delegation_recorded"]
        )
        if len(direct) > 1:
            state = CONTESTED
            holders = direct
        elif len(direct) == 1:
            state = HELD_DIRECTLY
            holders = direct
        elif len(lent) > 1:
            state = CONTESTED
            holders = lent
        elif len(lent) == 1:
            state = HELD_BY_RECORDED_DELEGATION
            holders = lent
        else:
            state = UNASSIGNED
            holders = ()
        disposition[duty] = {"state": state, "holders": holders}
    return disposition


def unassigned_duties(units):
    """Required duties no unit holds directly or under a recorded delegation."""
    disposition = duty_disposition(units)
    return tuple(
        duty for duty in REQUIRED_DUTIES if disposition[duty]["state"] == UNASSIGNED
    )


def contested_duties(units):
    """Required duties more than one unit claims at the same standing."""
    disposition = duty_disposition(units)
    return tuple(
        duty for duty in REQUIRED_DUTIES if disposition[duty]["state"] == CONTESTED
    )


def delegated_duties(units):
    """Required duties carried only by a recorded delegation."""
    disposition = duty_disposition(units)
    return tuple(
        duty
        for duty in REQUIRED_DUTIES
        if disposition[duty]["state"] == HELD_BY_RECORDED_DELEGATION
    )


def unrecorded_delegations(units):
    """Unit and duty pairs exercised under a delegation nobody wrote down."""
    checked = validate_units(units)
    found = []
    for unit in checked:
        if unit["delegation_recorded"]:
            continue
        for duty in unit["delegated_duties"]:
            found.append((unit["id"], duty))
    return tuple(found)


def duty_coverage(units):
    """Share of the required duties disposed at all."""
    disposition = duty_disposition(units)
    disposed = sum(
        1
        for duty in REQUIRED_DUTIES
        if disposition[duty]["state"]
        in (HELD_DIRECTLY, HELD_BY_RECORDED_DELEGATION)
    )
    return disposed / len(REQUIRED_DUTIES)


def effective_duty_coverage(units, policy=DEFAULT_ORGANIZATION_POLICY):
    """Coverage with a delegated duty weighed at the declared credit."""
    validate_organization_policy(policy)
    credit = float(policy["delegated_duty_credit"])
    disposition = duty_disposition(units)
    total = 0.0
    for duty in REQUIRED_DUTIES:
        state = disposition[duty]["state"]
        if state == HELD_DIRECTLY:
            total += 1.0
        elif state == HELD_BY_RECORDED_DELEGATION:
            total += credit
    return total / len(REQUIRED_DUTIES)


def named_parts_function(units):
    """The unit holding part-selection approval directly, or None."""
    disposition = duty_disposition(units)
    entry = disposition[NON_DELEGABLE_DUTY]
    if entry["state"] != HELD_DIRECTLY:
        return None
    checked = validate_units(units)
    for unit in checked:
        if unit["id"] == entry["holders"][0]:
            return unit
    return None


def function_is_mandated(units):
    """True when at least one declared unit carries a contractual mandate."""
    checked = validate_units(units)
    return any(unit["mandated_in_contract"] for unit in checked)


def competence_shortfall_years(unit, policy=DEFAULT_ORGANIZATION_POLICY):
    """How far a unit sits below the competence floor, zero when it clears it."""
    validate_organization_policy(policy)
    record = validate_unit_record(unit)
    floor = float(policy["min_competence_years"])
    years = record["competence_years"]
    if _at_least(years, floor):
        return 0.0
    return floor - years


def competence_advisories(units, policy=DEFAULT_ORGANIZATION_POLICY):
    """Name units clearing the competence floor by less than the marginal band.

    These do not move the verdict -- a unit above the floor is compliant --
    but a function drawn correctly and staffed at the edge will not stay
    compliant through one departure, and that is worth saying here rather
    than rediscovering it at the first alert disposition.
    """
    validate_organization_policy(policy)
    checked = validate_units(units)
    floor = float(policy["min_competence_years"])
    band = float(policy["marginal_competence_band_years"])
    advisories = []
    for unit in checked:
        if not _at_least(unit["competence_years"], floor):
            continue
        if _at_most(unit["competence_years"] - floor, band):
            advisories.append(
                "unit %s clears the %.3g year competence floor by %.3g years, "
                "inside the %.3g year marginal band; it is compliant today and "
                "has almost nothing left against one departure"
                % (unit["id"], floor, unit["competence_years"] - floor, band)
            )
    return tuple(advisories)


def assess_parts_organization(case, policy=DEFAULT_ORGANIZATION_POLICY):
    """Full clause 5.1.2.1 decision for one declared parts organization."""
    if not isinstance(case, dict):
        raise ValueError("case must be a mapping, got %r" % (case,))
    validate_organization_policy(policy)

    findings = []
    advisories = []
    result = {
        "named_function_id": None,
        "duty_coverage": None,
        "effective_duty_coverage": None,
        "unassigned_duties": (),
        "contested_duties": (),
        "delegated_duties": (),
        "unrecorded_delegations": (),
        "named_function_competence_years": None,
        "escalation_route": None,
        "findings": findings,
        "advisories": advisories,
    }

    units = case.get("units")
    if units is None:
        findings.append(
            "no parts function is declared, so nothing controls the commercial "
            "parts this programme intends to fly"
        )
        result["verdict"] = FUNCTION_NOT_ESTABLISHED
        return result

    checked = validate_units(units)
    if not function_is_mandated(checked):
        findings.append(
            "no declared unit carries a contractual mandate; an authority that "
            "cannot survive a programme review is not a parts function"
        )
        result["verdict"] = FUNCTION_NOT_ESTABLISHED
        return result

    disposition = duty_disposition(checked)
    gaps = unassigned_duties(checked)
    contested = contested_duties(checked)
    lent = delegated_duties(checked)
    unrecorded = unrecorded_delegations(checked)
    coverage = duty_coverage(checked)
    effective = effective_duty_coverage(checked, policy)

    result["duty_coverage"] = coverage
    result["effective_duty_coverage"] = effective
    result["unassigned_duties"] = gaps
    result["contested_duties"] = contested
    result["delegated_duties"] = lent
    result["unrecorded_delegations"] = unrecorded

    for holder, duty in unrecorded:
        findings.append(
            "%s exercises %s under a delegation nobody recorded, so the duty "
            "reads as covered and cannot be shown to be held" % (holder, duty)
        )

    anchor = disposition[NON_DELEGABLE_DUTY]
    if anchor["state"] == UNASSIGNED:
        findings.append(
            "no unit holds part-selection approval, so this clause has no "
            "function to name"
        )
        result["verdict"] = FUNCTION_NOT_ESTABLISHED
        return result
    if anchor["state"] == CONTESTED:
        findings.append(
            "part-selection approval is claimed by %d units (%s); each will "
            "assume the other exercised it"
            % (len(anchor["holders"]), ", ".join(anchor["holders"]))
        )
        result["verdict"] = ACCOUNTABILITY_CONTESTED
        return result
    if anchor["state"] == HELD_BY_RECORDED_DELEGATION:
        findings.append(
            "part-selection approval is exercised under delegation by %s; this "
            "duty does not travel, and the delegating unit has not been named"
            % anchor["holders"][0]
        )
        result["verdict"] = ANCHOR_DUTY_DELEGATED
        return result

    function = named_parts_function(checked)
    result["named_function_id"] = function["id"]
    result["named_function_competence_years"] = function["competence_years"]
    advisories.extend(competence_advisories(checked, policy))

    for duty in contested:
        findings.append(
            "%s is claimed by more than one unit (%s)"
            % (duty, ", ".join(disposition[duty]["holders"]))
        )
    if contested:
        result["verdict"] = ACCOUNTABILITY_CONTESTED
        return result

    for duty in gaps:
        findings.append("no declared unit holds %s" % duty)

    coverage_short = not _at_least(coverage, float(policy["min_duty_coverage"]))
    effective_short = not _at_least(
        effective, float(policy["min_effective_coverage"])
    )
    if coverage_short or effective_short:
        findings.append(
            "duty coverage is %.3g per cent against the %.3g per cent the class "
            "demands, and the credited coverage is %.3g per cent against %.3g "
            "per cent"
            % (
                coverage * 100.0,
                float(policy["min_duty_coverage"]) * 100.0,
                effective * 100.0,
                float(policy["min_effective_coverage"]) * 100.0,
            )
        )
        result["verdict"] = DUTY_COVERAGE_SHORT
        return result

    route = _require_label(
        "product_assurance_escalation_route",
        case.get("product_assurance_escalation_route", ""),
    )
    result["escalation_route"] = route
    if (
        function["embedded_in_design_authority"]
        and policy["require_escalation_route_when_embedded"]
        and not route
    ):
        findings.append(
            "the named function %s sits inside the design authority with no "
            "product assurance escalation route declared, so a refusal it owes "
            "the project costs it the schedule it shares" % function["id"]
        )
        result["verdict"] = ESCALATION_ROUTE_NOT_DECLARED
        return result

    result["verdict"] = ORGANIZATION_MEETS_CLASS_TWO
    return result
