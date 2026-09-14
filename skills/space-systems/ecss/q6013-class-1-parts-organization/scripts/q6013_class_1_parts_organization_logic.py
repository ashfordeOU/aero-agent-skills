#!/usr/bin/env python3
"""The unit accountable for commercial EEE part control at the highest class.

Anchor: ECSS-Q-ST-60-13C clause 4.1.2.1. The procedure below is a
paraphrase into implementable steps; no standard text is reproduced.

The clause asks a narrow question and it is worth stating exactly: when a
project intends to fly commercial EEE parts under the highest assurance
class, which unit is accountable for controlling them. Four things follow
from that sentence, and each is a way a programme gets it wrong.

Accountability is singular per duty. A commercial part reaches a flight
board through selection, a procurement source, an evaluation, a screening
decision, an alert disposition and an obsolescence call. A duty nobody
holds is a gap; a duty two units both hold is worse, because each assumes
the other exercised it and neither record shows the decision.

The anchor duty is part-selection approval. Whoever may say yes to a
commercial part entering the design is the unit this clause identifies,
so zero holders and two holders are both refusals rather than degenerate
cases to be resolved by picking one.

Independence from the design authority is structural, not personal. A
parts unit reporting into the team whose schedule a refusal would slip
cannot refuse, and the competence of its staff is not the point.

A mandate that lives only in a presentation is not a mandate, and the
customer escalation route is part of the organization rather than
something invented during the first disagreement.

The policy numbers below are declared project values, not physical
constants: a project substitutes its own.

Standard library only, offline, deterministic.
"""

from __future__ import annotations

import math

PART_SELECTION_APPROVAL = "part-selection-approval"
PROCUREMENT_SOURCE_APPROVAL = "procurement-source-approval"
EVALUATION_AUTHORITY = "evaluation-authority"
SCREENING_AND_LOT_ACCEPTANCE_CONTROL = "screening-and-lot-acceptance-control"
NONCONFORMANCE_AND_ALERT_DISPOSITION = "nonconformance-and-alert-disposition"
OBSOLESCENCE_AND_LIFETIME_BUY_CONTROL = "obsolescence-and-lifetime-buy-control"
PARTS_LIST_AND_TRACEABILITY_CUSTODY = "parts-list-and-traceability-custody"

REQUIRED_ACCOUNTABILITIES = (
    PART_SELECTION_APPROVAL,
    PROCUREMENT_SOURCE_APPROVAL,
    EVALUATION_AUTHORITY,
    SCREENING_AND_LOT_ACCEPTANCE_CONTROL,
    NONCONFORMANCE_AND_ALERT_DISPOSITION,
    OBSOLESCENCE_AND_LIFETIME_BUY_CONTROL,
    PARTS_LIST_AND_TRACEABILITY_CUSTODY,
)

ANCHOR_ACCOUNTABILITY = PART_SELECTION_APPROVAL

ORGANIZATION_NOT_ESTABLISHED = "parts-organization-not-established"
ACCOUNTABILITY_NOT_SINGULAR = "parts-accountability-not-singular"
ACCOUNTABLE_UNIT_NOT_INDEPENDENT = "accountable-unit-not-independent"
ESCALATION_ROUTE_NOT_DECLARED = "customer-escalation-route-not-declared"
ORGANIZATION_MEETS_CLASS_ONE = "parts-organization-meets-class-one"

DEFAULT_ORGANIZATION_POLICY = {
    "min_accountability_coverage": 1.0,
    "min_competence_years": 5.0,
    "marginal_competence_band_years": 1.0,
    "require_customer_escalation_route": True,
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
    """Check the organization policy is complete and sensible."""
    if not isinstance(policy, dict):
        raise ValueError("policy must be a mapping, got %r" % (policy,))
    coverage = _require_non_negative(
        "min_accountability_coverage", policy.get("min_accountability_coverage")
    )
    if coverage > 1.0:
        raise ValueError(
            "min_accountability_coverage %g is above one; no organization can "
            "hold more duties than the clause names" % coverage
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
            "marginal_competence_band_years %g is wider than the %g year "
            "floor; every compliant unit would be flagged marginal"
            % (band, competence)
        )
    _require_flag(
        "require_customer_escalation_route",
        policy.get("require_customer_escalation_route"),
    )
    return policy


def validate_unit_record(unit):
    """Read one declared organizational unit and the duties it holds."""
    if not isinstance(unit, dict):
        raise ValueError("unit must be a mapping, got %r" % (unit,))
    identifier = _require_label("unit id", unit.get("id"))
    if not identifier:
        raise ValueError("unit id must not be blank")
    duties = unit.get("accountabilities")
    if not isinstance(duties, (list, tuple)):
        raise ValueError(
            "accountabilities on %s must be a sequence of duty names" % identifier
        )
    named = []
    for duty in duties:
        label = _require_label("accountability on %s" % identifier, duty)
        if label not in REQUIRED_ACCOUNTABILITIES:
            raise ValueError(
                "unrecognised accountability %r on %s; the duty names are fixed"
                % (label, identifier)
            )
        if label in named:
            raise ValueError(
                "accountability %r is listed twice on %s" % (label, identifier)
            )
        named.append(label)
    competence = _require_non_negative(
        "competence_years on %s" % identifier, unit.get("competence_years")
    )
    independent = _require_flag(
        "independent_of_design_authority on %s" % identifier,
        unit.get("independent_of_design_authority"),
    )
    mandated = _require_flag(
        "mandated_in_contract on %s" % identifier, unit.get("mandated_in_contract")
    )
    return {
        "id": identifier,
        "accountabilities": tuple(named),
        "competence_years": competence,
        "independent_of_design_authority": independent,
        "mandated_in_contract": mandated,
    }


def validate_units(units):
    """Read every declared unit, refusing an empty or duplicated set."""
    if not isinstance(units, (list, tuple)):
        raise ValueError("units must be a sequence of unit records")
    if not units:
        raise ValueError("no organizational unit was declared, so nothing is accountable")
    checked = []
    seen = set()
    for unit in units:
        record = validate_unit_record(unit)
        if record["id"] in seen:
            raise ValueError("duplicate unit id %r in the organization" % record["id"])
        seen.add(record["id"])
        checked.append(record)
    return tuple(checked)


def accountability_assignment(units):
    """Map each required duty to the units that claim it, in record order."""
    checked = validate_units(units)
    assignment = {}
    for duty in REQUIRED_ACCOUNTABILITIES:
        holders = tuple(
            unit["id"] for unit in checked if duty in unit["accountabilities"]
        )
        assignment[duty] = holders
    return assignment


def unassigned_accountabilities(units):
    """Required duties no declared unit holds."""
    assignment = accountability_assignment(units)
    return tuple(
        duty for duty in REQUIRED_ACCOUNTABILITIES if not assignment[duty]
    )


def split_accountabilities(units):
    """Required duties more than one declared unit holds."""
    assignment = accountability_assignment(units)
    return tuple(
        duty for duty in REQUIRED_ACCOUNTABILITIES if len(assignment[duty]) > 1
    )


def accountability_coverage(units):
    """Share of the required duties held by exactly one unit."""
    assignment = accountability_assignment(units)
    singular = sum(1 for duty in REQUIRED_ACCOUNTABILITIES if len(assignment[duty]) == 1)
    return singular / len(REQUIRED_ACCOUNTABILITIES)


def nominated_accountable_unit(units):
    """The unit holding the anchor duty, or None when nobody or two hold it."""
    assignment = accountability_assignment(units)
    holders = assignment[ANCHOR_ACCOUNTABILITY]
    if len(holders) != 1:
        return None
    checked = validate_units(units)
    for unit in checked:
        if unit["id"] == holders[0]:
            return unit
    return None


def organization_is_mandated(units):
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
    but an organization drawn correctly and staffed at the edge will not
    stay compliant through one resignation, and that is worth saying once
    here rather than rediscovering it at the first alert disposition.
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
    """Full clause 4.1.2.1 accountability decision for one declared organization."""
    if not isinstance(case, dict):
        raise ValueError("case must be a mapping, got %r" % (case,))
    validate_organization_policy(policy)

    findings = []
    advisories = []
    result = {
        "accountable_unit_id": None,
        "accountability_coverage": None,
        "unassigned_accountabilities": (),
        "split_accountabilities": (),
        "accountable_unit_competence_years": None,
        "customer_escalation_route": None,
        "findings": findings,
        "advisories": advisories,
    }

    units = case.get("units")
    if units is None:
        findings.append(
            "no parts organization is declared, so no unit is accountable for "
            "commercial part control"
        )
        result["verdict"] = ORGANIZATION_NOT_ESTABLISHED
        return result

    checked = validate_units(units)
    if not organization_is_mandated(checked):
        findings.append(
            "no declared unit carries a contractual mandate; an authority that "
            "cannot survive a programme review is not an accountability"
        )
        result["verdict"] = ORGANIZATION_NOT_ESTABLISHED
        return result

    coverage = accountability_coverage(checked)
    gaps = unassigned_accountabilities(checked)
    splits = split_accountabilities(checked)
    result["accountability_coverage"] = coverage
    result["unassigned_accountabilities"] = gaps
    result["split_accountabilities"] = splits

    accountable = nominated_accountable_unit(checked)
    if accountable is None:
        holders = accountability_assignment(checked)[ANCHOR_ACCOUNTABILITY]
        if not holders:
            findings.append(
                "no unit holds part-selection approval, so the clause has "
                "nobody to identify"
            )
            result["verdict"] = ORGANIZATION_NOT_ESTABLISHED
            return result
        findings.append(
            "part-selection approval is held by %d units (%s); each will assume "
            "the other exercised it" % (len(holders), ", ".join(holders))
        )
        result["verdict"] = ACCOUNTABILITY_NOT_SINGULAR
        return result

    result["accountable_unit_id"] = accountable["id"]
    result["accountable_unit_competence_years"] = accountable["competence_years"]

    for duty in gaps:
        findings.append("no declared unit holds %s" % duty)
    for duty in splits:
        findings.append(
            "%s is held by more than one unit (%s)"
            % (duty, ", ".join(accountability_assignment(checked)[duty]))
        )
    advisories.extend(competence_advisories(checked, policy))

    if gaps or splits or not _at_least(
        coverage, float(policy["min_accountability_coverage"])
    ):
        findings.append(
            "accountability coverage is %.3g per cent against the %.3g per cent "
            "the class demands"
            % (
                coverage * 100.0,
                float(policy["min_accountability_coverage"]) * 100.0,
            )
        )
        result["verdict"] = ACCOUNTABILITY_NOT_SINGULAR
        return result

    if not accountable["independent_of_design_authority"]:
        findings.append(
            "the accountable unit %s reports inside the design authority, so a "
            "refusal it owes the project costs it the schedule it shares"
            % accountable["id"]
        )
        result["verdict"] = ACCOUNTABLE_UNIT_NOT_INDEPENDENT
        return result

    route = _require_label("customer_escalation_route", case.get("customer_escalation_route", ""))
    result["customer_escalation_route"] = route
    if policy["require_customer_escalation_route"] and not route:
        findings.append(
            "no customer escalation route is declared; at this class the "
            "customer carries the residual risk of a commercial part"
        )
        result["verdict"] = ESCALATION_ROUTE_NOT_DECLARED
        return result

    result["verdict"] = ORGANIZATION_MEETS_CLASS_ONE
    return result
