#!/usr/bin/env python3
"""Who is accountable for electronic part control at the highest class.

Anchor: ECSS-Q-ST-60C clause 4.1.2.1. The procedure below is a
paraphrase into implementable steps; no standard text is reproduced.

At the highest reliability class the supplier has to name one unit that
owns electronic part control and give it a lead, an appointment behind
that lead, and the standing to say no. The clause is satisfied by an
organization, not by a sentence in a plan saying part control is taken
seriously.

Four things follow, and each is a way an organization chart reads
complete and controls nothing.

A control function written against a name with no competence behind it
and no effort allocated to it is uncovered. A chart that lists every
function against one overloaded engineer matches the required list and
covers none of it, so an unqualified holder or an effort below the
declared floor reads as no holder at all.

Coverage and staffing are two different numbers. The covered share
answers how many required functions have a real holder; the
effort-weighted staffing answers how much of a person stands behind the
set, over the full required denominator so that deleting a function
cannot raise the score.

The reporting line is part of the constitution. A part control unit
reporting into the authority whose cost and schedule it constrains has
no standing to refuse a part, so the accepted lines are declared and
checked rather than assumed.

Concentration is its own failure. One holder carrying most of the
required functions is a single point of failure whatever the coverage
share says, so the peak holder load is computed and capped.

The policy numbers below are declared project values, not physical
constants: a project substitutes its own.

Standard library only, offline, deterministic.
"""

from __future__ import annotations

import math

PART_SELECTION_AND_DECLARED_LISTS = "part-selection-and-declared-lists"
PROCUREMENT_AND_SOURCE_SURVEILLANCE = "procurement-and-source-surveillance"
EVALUATION_AND_QUALIFICATION_ROUTE = "evaluation-and-qualification-route"
SCREENING_AND_LOT_ACCEPTANCE = "screening-and-lot-acceptance"
DERATING_AND_APPLICATION_REVIEW = "derating-and-application-review"
RADIATION_HARDNESS_ASSURANCE = "radiation-hardness-assurance"
OBSOLESCENCE_AND_AVAILABILITY = "obsolescence-and-availability-management"
ALERT_AND_NONCONFORMANCE_HANDLING = "alert-and-nonconformance-handling"

REQUIRED_CONTROL_FUNCTIONS = (
    PART_SELECTION_AND_DECLARED_LISTS,
    PROCUREMENT_AND_SOURCE_SURVEILLANCE,
    EVALUATION_AND_QUALIFICATION_ROUTE,
    SCREENING_AND_LOT_ACCEPTANCE,
    DERATING_AND_APPLICATION_REVIEW,
    RADIATION_HARDNESS_ASSURANCE,
    OBSOLESCENCE_AND_AVAILABILITY,
    ALERT_AND_NONCONFORMANCE_HANDLING,
)

ORGANIZATION_NOT_ESTABLISHED = "parts-control-organization-not-established"
FUNCTION_COVERAGE_SHORT = "parts-control-function-coverage-short"
REPORTING_LINE_NOT_ACCEPTED = "parts-control-reporting-line-not-accepted"
ORGANIZATION_NOT_INDEPENDENT = "parts-control-organization-not-independent"
CONTROL_CONCENTRATED_ON_ONE_HOLDER = "parts-control-concentrated-on-one-holder"
ORGANIZATION_NOT_AGREED = "parts-control-organization-not-agreed-with-customer"
ORGANIZATION_MEETS_CLASS_ONE = "parts-control-organization-meets-class-one"

PRODUCT_ASSURANCE_MANAGER = "product-assurance-manager"

DEFAULT_ORGANIZATION_POLICY = {
    "min_function_coverage": 1.0,
    "min_function_effort": 0.1,
    "max_holder_function_share": 0.5,
    "marginal_effort_band": 0.05,
    "require_design_independence": True,
    "require_customer_agreement": True,
    "accepted_reporting_lines": (PRODUCT_ASSURANCE_MANAGER,),
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
    """Check the organization adequacy policy is complete and sensible."""
    if not isinstance(policy, dict):
        raise ValueError("policy must be a mapping, got %r" % (policy,))
    _require_fraction("min_function_coverage", policy.get("min_function_coverage"))
    effort = _require_positive(
        "min_function_effort", policy.get("min_function_effort")
    )
    if effort > 1.0:
        raise ValueError(
            "min_function_effort %g is above one; no holder can allocate more "
            "than a whole person to one function" % effort
        )
    share = _require_positive(
        "max_holder_function_share", policy.get("max_holder_function_share")
    )
    if share > 1.0:
        raise ValueError(
            "max_holder_function_share %g is above one; the cap would never "
            "bind and the concentration check would be decorative" % share
        )
    band = _require_fraction(
        "marginal_effort_band", policy.get("marginal_effort_band")
    )
    if band > effort:
        raise ValueError(
            "marginal_effort_band %g is wider than the %g effort floor; every "
            "covered function would be flagged thin" % (band, effort)
        )
    _require_flag(
        "require_design_independence", policy.get("require_design_independence")
    )
    _require_flag(
        "require_customer_agreement", policy.get("require_customer_agreement")
    )
    lines = policy.get("accepted_reporting_lines")
    if not isinstance(lines, (list, tuple)) or not lines:
        raise ValueError(
            "accepted_reporting_lines must be a non-empty sequence of line names"
        )
    for line in lines:
        if not _require_label("accepted reporting line", line):
            raise ValueError("an accepted reporting line name is blank")
    return policy


def validate_organization_identity(organization):
    """Check the unit can be named and its standing read."""
    if not isinstance(organization, dict):
        raise ValueError("organization must be a mapping, got %r" % (organization,))
    unit = _require_label("unit_name", organization.get("unit_name"))
    lead = _require_label("accountable_lead", organization.get("accountable_lead"))
    appointment = _require_label(
        "appointment_reference", organization.get("appointment_reference")
    )
    reports_to = _require_label("reports_to", organization.get("reports_to"))
    independent = _require_flag(
        "independent_of_design_authority",
        organization.get("independent_of_design_authority"),
    )
    agreed = _require_flag(
        "agreed_with_customer", organization.get("agreed_with_customer")
    )
    return {
        "unit_name": unit,
        "accountable_lead": lead,
        "appointment_reference": appointment,
        "reports_to": reports_to,
        "independent_of_design_authority": independent,
        "agreed_with_customer": agreed,
    }


def validate_assignment_record(assignment):
    """Read one function assignment, its holder, effort and competence flag."""
    if not isinstance(assignment, dict):
        raise ValueError("assignment must be a mapping, got %r" % (assignment,))
    function = _require_label("function", assignment.get("function"))
    if function not in REQUIRED_CONTROL_FUNCTIONS:
        raise ValueError(
            "unrecognised control function %r; the required function names are "
            "fixed" % function
        )
    holder = _require_label("holder on %s" % function, assignment.get("holder", ""))
    effort = _require_fraction(
        "allocated_effort on %s" % function, assignment.get("allocated_effort")
    )
    qualified = _require_flag(
        "holder_qualified on %s" % function, assignment.get("holder_qualified")
    )
    return {
        "function": function,
        "holder": holder,
        "allocated_effort": effort,
        "holder_qualified": qualified,
    }


def validate_assignments(assignments):
    """Read every assignment, refusing a function assigned twice."""
    if not isinstance(assignments, (list, tuple)):
        raise ValueError("assignments must be a sequence of assignment records")
    checked = []
    seen = set()
    for assignment in assignments:
        record = validate_assignment_record(assignment)
        if record["function"] in seen:
            raise ValueError(
                "control function %r is assigned twice" % record["function"]
            )
        seen.add(record["function"])
        checked.append(record)
    return tuple(checked)


def assignment_index(assignments):
    """Map each assigned function name to its record."""
    return {record["function"]: record for record in validate_assignments(assignments)}


def function_is_covered(record, policy=DEFAULT_ORGANIZATION_POLICY):
    """True when a function has a named, competent holder with real effort."""
    validate_organization_policy(policy)
    checked = validate_assignment_record(record)
    if not checked["holder"] or not checked["holder_qualified"]:
        return False
    return _at_least(
        checked["allocated_effort"], float(policy["min_function_effort"])
    )


def unassigned_functions(assignments, policy=DEFAULT_ORGANIZATION_POLICY):
    """Required functions the organization does not name a holder for at all."""
    validate_organization_policy(policy)
    index = assignment_index(assignments)
    return tuple(
        name for name in REQUIRED_CONTROL_FUNCTIONS if name not in index
    )


def under_resourced_functions(assignments, policy=DEFAULT_ORGANIZATION_POLICY):
    """Assigned functions with a blank, unqualified or under-funded holder."""
    validate_organization_policy(policy)
    index = assignment_index(assignments)
    return tuple(
        name
        for name in REQUIRED_CONTROL_FUNCTIONS
        if name in index and not function_is_covered(index[name], policy)
    )


def function_coverage(assignments, policy=DEFAULT_ORGANIZATION_POLICY):
    """Share of the required control functions that have a real holder."""
    validate_organization_policy(policy)
    index = assignment_index(assignments)
    covered = sum(
        1
        for name in REQUIRED_CONTROL_FUNCTIONS
        if name in index and function_is_covered(index[name], policy)
    )
    return covered / len(REQUIRED_CONTROL_FUNCTIONS)


def effort_weighted_staffing(assignments, policy=DEFAULT_ORGANIZATION_POLICY):
    """Mean allocated effort over the full required function list.

    An unassigned function counts as zero effort rather than dropping out
    of the average, so deleting a thin function cannot raise the score. A
    function standing on a blank or unqualified holder counts as zero for
    the same reason.
    """
    validate_organization_policy(policy)
    index = assignment_index(assignments)
    total = 0.0
    for name in REQUIRED_CONTROL_FUNCTIONS:
        record = index.get(name)
        if record is None or not record["holder"] or not record["holder_qualified"]:
            continue
        total += record["allocated_effort"]
    return total / len(REQUIRED_CONTROL_FUNCTIONS)


def holder_function_load(assignments, policy=DEFAULT_ORGANIZATION_POLICY):
    """Count the required functions each named holder carries."""
    validate_organization_policy(policy)
    index = assignment_index(assignments)
    load = {}
    for name in REQUIRED_CONTROL_FUNCTIONS:
        record = index.get(name)
        if record is None or not record["holder"]:
            continue
        load[record["holder"]] = load.get(record["holder"], 0) + 1
    return load


def peak_holder_share(assignments, policy=DEFAULT_ORGANIZATION_POLICY):
    """The most loaded holder and the share of required functions held.

    Returns (None, 0.0) when no function carries a named holder at all.
    Ties resolve to the alphabetically first holder so the report is
    reproducible.
    """
    load = holder_function_load(assignments, policy)
    if not load:
        return None, 0.0
    peak = max(sorted(load), key=lambda holder: load[holder])
    return peak, load[peak] / len(REQUIRED_CONTROL_FUNCTIONS)


def weakest_covered_function(assignments, policy=DEFAULT_ORGANIZATION_POLICY):
    """The covered function carrying the least effort, or None when none is."""
    validate_organization_policy(policy)
    index = assignment_index(assignments)
    covered = [
        index[name]
        for name in REQUIRED_CONTROL_FUNCTIONS
        if name in index and function_is_covered(index[name], policy)
    ]
    if not covered:
        return None
    return min(covered, key=lambda record: record["allocated_effort"])


def marginal_effort_advisories(assignments, policy=DEFAULT_ORGANIZATION_POLICY):
    """Name covered functions clearing the effort floor by less than the band.

    These do not move the verdict -- a covered function is covered -- but a
    function funded to the last decimal will not survive the first
    reassignment, and that is worth saying once here rather than
    rediscovering it when the holder moves on.
    """
    validate_organization_policy(policy)
    index = assignment_index(assignments)
    floor = float(policy["min_function_effort"])
    band = float(policy["marginal_effort_band"])
    advisories = []
    for name in REQUIRED_CONTROL_FUNCTIONS:
        record = index.get(name)
        if record is None or not function_is_covered(record, policy):
            continue
        if _at_most(record["allocated_effort"] - floor, band):
            advisories.append(
                "function %s is covered at an effort of %.3g against a %.3g "
                "floor, inside the %.3g marginal band; it counts today and has "
                "almost nothing left against a reassignment"
                % (name, record["allocated_effort"], floor, band)
            )
    return tuple(advisories)


def assess_parts_control_organization(case, policy=DEFAULT_ORGANIZATION_POLICY):
    """Full clause 4.1.2.1 adequacy decision for one parts control unit."""
    if not isinstance(case, dict):
        raise ValueError("case must be a mapping, got %r" % (case,))
    validate_organization_policy(policy)

    findings = []
    advisories = []
    result = {
        "unit_name": None,
        "accountable_lead": None,
        "function_coverage": None,
        "effort_weighted_staffing": None,
        "unassigned_functions": (),
        "under_resourced_functions": (),
        "peak_holder": None,
        "peak_holder_share": None,
        "weakest_covered_function": None,
        "weakest_covered_effort": None,
        "findings": findings,
        "advisories": advisories,
    }

    organization = case.get("organization")
    if organization is None:
        findings.append(
            "no parts control organization is declared, so no unit answers for "
            "the electronic parts that go into the build"
        )
        result["verdict"] = ORGANIZATION_NOT_ESTABLISHED
        return result

    identity = validate_organization_identity(organization)
    result["unit_name"] = identity["unit_name"]
    result["accountable_lead"] = identity["accountable_lead"]
    if (
        not identity["unit_name"]
        or not identity["accountable_lead"]
        or not identity["appointment_reference"]
    ):
        findings.append(
            "the organization carries no unit name, no accountable lead or no "
            "appointment behind that lead, so the accountability is a claim "
            "rather than a post"
        )
        result["verdict"] = ORGANIZATION_NOT_ESTABLISHED
        return result

    assignments = organization.get("assignments")
    if assignments is None:
        raise ValueError("the organization declares no assignments sequence")
    checked = validate_assignments(assignments)

    coverage = function_coverage(checked, policy)
    staffing = effort_weighted_staffing(checked, policy)
    unassigned = unassigned_functions(checked, policy)
    thin = under_resourced_functions(checked, policy)
    result["function_coverage"] = coverage
    result["effort_weighted_staffing"] = staffing
    result["unassigned_functions"] = unassigned
    result["under_resourced_functions"] = thin

    peak, share = peak_holder_share(checked, policy)
    result["peak_holder"] = peak
    result["peak_holder_share"] = share

    weakest = weakest_covered_function(checked, policy)
    if weakest is not None:
        result["weakest_covered_function"] = weakest["function"]
        result["weakest_covered_effort"] = weakest["allocated_effort"]

    for name in unassigned:
        findings.append("no holder is named for %s" % name)
    for name in thin:
        findings.append(
            "the holder named for %s is blank, not competent for the function "
            "or funded below the effort floor" % name
        )
    advisories.extend(marginal_effort_advisories(checked, policy))

    if not _at_least(coverage, float(policy["min_function_coverage"])):
        findings.append(
            "function coverage is %.3g per cent against the %.3g per cent the "
            "class demands, at an effort-weighted staffing of %.3g"
            % (
                coverage * 100.0,
                float(policy["min_function_coverage"]) * 100.0,
                staffing,
            )
        )
        result["verdict"] = FUNCTION_COVERAGE_SHORT
        return result

    if identity["reports_to"] not in tuple(policy["accepted_reporting_lines"]):
        findings.append(
            "the unit reports to %s, which is not an accepted line; a unit "
            "reporting into the authority whose cost it constrains cannot "
            "refuse a part" % identity["reports_to"]
        )
        result["verdict"] = REPORTING_LINE_NOT_ACCEPTED
        return result

    if policy["require_design_independence"] and not identity[
        "independent_of_design_authority"
    ]:
        findings.append(
            "the unit is not independent of the design authority, so a part "
            "chosen by the design cannot be refused by the control unit"
        )
        result["verdict"] = ORGANIZATION_NOT_INDEPENDENT
        return result

    if not _at_most(share, float(policy["max_holder_function_share"])):
        findings.append(
            "holder %s carries %.3g per cent of the required functions against "
            "a %.3g per cent cap; the control is one person deep"
            % (
                peak,
                share * 100.0,
                float(policy["max_holder_function_share"]) * 100.0,
            )
        )
        result["verdict"] = CONTROL_CONCENTRATED_ON_ONE_HOLDER
        return result

    if policy["require_customer_agreement"] and not identity["agreed_with_customer"]:
        findings.append(
            "the organization is not agreed with the customer; at this class "
            "the customer carries the residual part risk and has to know who "
            "holds the control"
        )
        result["verdict"] = ORGANIZATION_NOT_AGREED
        return result

    result["verdict"] = ORGANIZATION_MEETS_CLASS_ONE
    return result
