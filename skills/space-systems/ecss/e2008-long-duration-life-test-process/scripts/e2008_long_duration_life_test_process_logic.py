#!/usr/bin/env python3
"""Selecting and documenting a long duration life test approach.

Anchor: ECSS-E-ST-20-08C clause 6.4.3.18.2. The procedure below is a
paraphrase into implementable steps; no standard text is reproduced.

The clause hands the supplier a closed menu and one obligation. Four
approaches to a long duration life test are accepted; the supplier picks
one of them and writes down why it is the one. Almost every way a
campaign gets this wrong is a way of not doing one of those two things.

The menu is closed. An approach that is not on it is not a variant to be
argued for in the test report; it is outside the clause, and the right
answer is to say so before the article is in a chamber rather than after.

The selection is singular. Two approaches declared together is not
belt-and-braces, it is an undocumented decision: the two demand
different evidence, they convert laboratory time into service time by
different arithmetic, and a subgroup run half one way and half the other
has no single statement of what it stands for.

The documentation is approach-specific and that is the point. A real
time run needs the article, the conditions and the schedule. An
accelerated temperature run needs all of that plus the activation energy
it leans on, the derivation of the factor and the ceiling above which
the mechanism it assumes stops being the mechanism present. A cycling
run needs the cycle itself, the rate and the conversion from cycles back
to service. An equivalence argument tests nothing new, so it needs the
reference programme, the delta analysis against it and the exposure that
programme actually accumulated. Requiring the same checklist of all four
either over-documents the simple one or lets the hard one through light.

Feasibility is arithmetic, not opinion. Each approach implies a number
of laboratory hours -- the service hours themselves for a real time run,
those hours divided by the factor for an accelerated one, the required
cycles divided by the achievable rate for a cycling one, and none at all
for an equivalence argument, which instead needs the reference exposure
to reach the demand. Comparing that against the window the programme
actually has is what separates an approach the supplier can run from one
that will be quietly abandoned at month nine.

The preference order, the schedule margin and the coverage ratio below
are declared policy, not physical constants: a project substitutes its
own.

Standard library only, offline, deterministic.
"""

from __future__ import annotations

import math

REAL_TIME = "real-time-life-test"
ACCELERATED_TEMPERATURE = "accelerated-temperature-life-test"
ACCELERATED_CYCLING = "accelerated-cycling-life-test"
QUALIFIED_HERITAGE = "qualified-heritage-equivalence"

ACCEPTED_APPROACHES = (
    REAL_TIME,
    ACCELERATED_TEMPERATURE,
    ACCELERATED_CYCLING,
    QUALIFIED_HERITAGE,
)

_COMMON_EVIDENCE = (
    "test-article-definition",
    "operating-conditions-record",
    "measurement-interval-plan",
)

REQUIRED_EVIDENCE = {
    REAL_TIME: _COMMON_EVIDENCE + ("test-duration-plan",),
    ACCELERATED_TEMPERATURE: _COMMON_EVIDENCE
    + (
        "activation-energy-justification",
        "acceleration-factor-derivation",
        "mechanism-ceiling-statement",
    ),
    ACCELERATED_CYCLING: _COMMON_EVIDENCE
    + (
        "cycle-definition",
        "cycle-rate-justification",
        "cycle-to-service-conversion",
    ),
    QUALIFIED_HERITAGE: (
        "operating-conditions-record",
        "reference-programme-identification",
        "design-and-process-delta-analysis",
        "reference-exposure-record",
    ),
}

NO_APPROACH_DECLARED = "no-approach-declared"
APPROACH_NOT_ACCEPTED = "approach-not-accepted"
MORE_THAN_ONE_APPROACH_DECLARED = "more-than-one-approach-declared"
DOCUMENTATION_INCOMPLETE = "approach-documentation-incomplete"
APPROACH_NOT_FEASIBLE = "approach-not-feasible-in-the-window"
APPROACH_SELECTED_AND_DOCUMENTED = "approach-selected-and-documented"

DEFAULT_PROCESS_POLICY = {
    "preference_order": (
        REAL_TIME,
        ACCELERATED_TEMPERATURE,
        ACCELERATED_CYCLING,
        QUALIFIED_HERITAGE,
    ),
    "schedule_margin_fraction": 0.1,
    "minimum_heritage_exposure_ratio": 1.0,
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


def _require_label(name, value):
    if not isinstance(value, str):
        raise ValueError("%s must be a string, got %r" % (name, value))
    return value.strip()


def _at_most(value, limit):
    """value <= limit, absorbing floating-point representation error."""
    return value <= limit or math.isclose(
        value, limit, rel_tol=_REL_TOL, abs_tol=_ABS_TOL
    )


def _at_least(value, limit):
    """value >= limit, absorbing floating-point representation error."""
    return value >= limit or math.isclose(
        value, limit, rel_tol=_REL_TOL, abs_tol=_ABS_TOL
    )


def accepted_approaches():
    """The four approaches this clause admits, in menu order."""
    return ACCEPTED_APPROACHES


def require_accepted_approach(approach):
    """Check a name is on the closed menu and return it normalised."""
    name = _require_label("approach", approach)
    if name not in ACCEPTED_APPROACHES:
        raise ValueError(
            "approach %r is not one of the accepted approaches %s"
            % (approach, ", ".join(ACCEPTED_APPROACHES))
        )
    return name


def required_evidence_for(approach):
    """The documentation the chosen approach has to carry, sorted."""
    name = require_accepted_approach(approach)
    return tuple(sorted(REQUIRED_EVIDENCE[name]))


def validate_process_policy(policy):
    """Check a process policy names every approach exactly once."""
    if not isinstance(policy, dict):
        raise ValueError("policy must be a mapping, got %r" % (policy,))
    order = policy.get("preference_order")
    if not isinstance(order, (list, tuple)):
        raise ValueError("preference_order must be a sequence of approach names")
    seen = []
    for entry in order:
        name = require_accepted_approach(entry)
        if name in seen:
            raise ValueError("duplicate approach %r in preference_order" % name)
        seen.append(name)
    if len(seen) != len(ACCEPTED_APPROACHES):
        raise ValueError(
            "preference_order must rank all %d accepted approaches, got %d"
            % (len(ACCEPTED_APPROACHES), len(seen))
        )
    margin = _require_number(
        "schedule_margin_fraction", policy.get("schedule_margin_fraction")
    )
    if margin < 0.0 or margin >= 1.0:
        raise ValueError(
            "schedule_margin_fraction %g must sit in [0, 1); a margin of one "
            "consumes the whole window before any testing starts" % margin
        )
    ratio = _require_positive(
        "minimum_heritage_exposure_ratio",
        policy.get("minimum_heritage_exposure_ratio"),
    )
    if ratio < 1.0:
        raise ValueError(
            "minimum_heritage_exposure_ratio %g is below one; that accepts a "
            "reference programme shorter than the life it stands for" % ratio
        )
    return policy


def validate_service_demand(demand):
    """Check the demand the chosen approach has to meet."""
    if not isinstance(demand, dict):
        raise ValueError("service demand must be a mapping, got %r" % (demand,))
    hours = _require_positive(
        "required_service_hours", demand.get("required_service_hours")
    )
    cycles = _require_positive(
        "required_service_cycles", demand.get("required_service_cycles")
    )
    return hours, cycles


def declared_approaches(case):
    """The approaches the supplier declared, normalised and de-duplicated."""
    if not isinstance(case, dict):
        raise ValueError("case must be a mapping, got %r" % (case,))
    declared = case.get("declared_approaches")
    if declared is None:
        return ()
    if not isinstance(declared, (list, tuple)):
        raise ValueError(
            "declared_approaches must be a sequence of approach names, got %r"
            % (declared,)
        )
    named = []
    for entry in declared:
        name = _require_label("declared approach", entry)
        if name not in named:
            named.append(name)
    return tuple(named)


def missing_evidence(approach, record):
    """Documentation the record does not carry for the chosen approach."""
    name = require_accepted_approach(approach)
    if not isinstance(record, (list, tuple, set, frozenset)):
        raise ValueError(
            "documentation record must be a sequence of evidence names, got %r"
            % (record,)
        )
    held = set()
    for entry in record:
        held.add(_require_label("evidence item", entry))
    return tuple(item for item in required_evidence_for(name) if item not in held)


def laboratory_hours_for(approach, plan, demand):
    """New laboratory hours the approach implies before it can be sentenced."""
    name = require_accepted_approach(approach)
    hours, cycles = validate_service_demand(demand)
    if not isinstance(plan, dict):
        raise ValueError("plan must be a mapping, got %r" % (plan,))
    if name == REAL_TIME:
        return hours
    if name == ACCELERATED_TEMPERATURE:
        factor = _require_positive(
            "acceleration_factor", plan.get("acceleration_factor")
        )
        if factor < 1.0:
            raise ValueError(
                "acceleration_factor %g is below one; it would make the "
                "accelerated run longer than the service life" % factor
            )
        return hours / factor
    if name == ACCELERATED_CYCLING:
        rate = _require_positive("cycles_per_hour", plan.get("cycles_per_hour"))
        return cycles / rate
    return 0.0


def heritage_exposure_ratio(plan, demand):
    """Reference exposure as a multiple of the service hours it stands for."""
    hours, _cycles = validate_service_demand(demand)
    if not isinstance(plan, dict):
        raise ValueError("plan must be a mapping, got %r" % (plan,))
    exposure = _require_positive(
        "reference_exposure_hours", plan.get("reference_exposure_hours")
    )
    return exposure / hours


def usable_window_hours(available_window_hours, policy=DEFAULT_PROCESS_POLICY):
    """Window hours left once the policy schedule margin is held back."""
    validate_process_policy(policy)
    window = _require_positive(
        "available_window_hours", available_window_hours
    )
    return window * (1.0 - float(policy["schedule_margin_fraction"]))


def approach_feasibility(approach, case, policy=DEFAULT_PROCESS_POLICY):
    """Whether one approach can actually be run inside the programme window."""
    name = require_accepted_approach(approach)
    validate_process_policy(policy)
    if not isinstance(case, dict):
        raise ValueError("case must be a mapping, got %r" % (case,))
    plan = case.get("plan", {})
    demand = case.get("service_demand")
    usable = usable_window_hours(case.get("available_window_hours"), policy)

    reasons = []
    needed = laboratory_hours_for(name, plan, demand)
    feasible = _at_most(needed, usable)
    if not feasible:
        reasons.append(
            "%s needs %.4g laboratory hours against the %.4g usable hours the "
            "window leaves" % (name, needed, usable)
        )
    if name == QUALIFIED_HERITAGE:
        ratio = heritage_exposure_ratio(plan, demand)
        floor = float(policy["minimum_heritage_exposure_ratio"])
        if not _at_least(ratio, floor):
            feasible = False
            reasons.append(
                "the reference programme accumulated only %.3f of the service "
                "exposure being claimed from it" % ratio
            )
    return {
        "approach": name,
        "laboratory_hours": needed,
        "usable_window_hours": usable,
        "feasible": feasible,
        "reasons": tuple(reasons),
    }


def admissible_approaches(case, policy=DEFAULT_PROCESS_POLICY):
    """Every accepted approach the programme could actually run, ranked."""
    validate_process_policy(policy)
    admissible = []
    for name in policy["preference_order"]:
        try:
            report = approach_feasibility(name, case, policy)
        except ValueError:
            continue
        if report["feasible"]:
            admissible.append(name)
    return tuple(admissible)


def select_and_document_life_test_approach(case, policy=DEFAULT_PROCESS_POLICY):
    """Full clause 6.4.3.18.2 approach selection and documentation review."""
    if not isinstance(case, dict):
        raise ValueError("case must be a mapping, got %r" % (case,))
    validate_process_policy(policy)

    findings = []
    advisories = []
    result = {
        "declared_approaches": (),
        "selected_approach": None,
        "required_evidence": (),
        "missing_evidence": (),
        "laboratory_hours": None,
        "usable_window_hours": None,
        "admissible_approaches": (),
        "findings": findings,
        "advisories": advisories,
    }

    declared = declared_approaches(case)
    result["declared_approaches"] = declared

    if not declared:
        findings.append(
            "the supplier declared no approach, so there is nothing to "
            "document and nothing the run can be read against"
        )
        result["verdict"] = NO_APPROACH_DECLARED
        return result

    unrecognised = [name for name in declared if name not in ACCEPTED_APPROACHES]
    if unrecognised:
        findings.append(
            "%s is not on the closed menu of accepted approaches %s"
            % (", ".join(unrecognised), ", ".join(ACCEPTED_APPROACHES))
        )
        result["verdict"] = APPROACH_NOT_ACCEPTED
        return result

    if len(declared) > 1:
        findings.append(
            "%d approaches are declared together; the clause admits one, and "
            "two demand different evidence and different conversions back to "
            "service time" % len(declared)
        )
        result["verdict"] = MORE_THAN_ONE_APPROACH_DECLARED
        return result

    selected = declared[0]
    result["selected_approach"] = selected
    result["required_evidence"] = required_evidence_for(selected)

    record = case.get("documentation_record", ())
    gaps = missing_evidence(selected, record)
    result["missing_evidence"] = gaps

    report = approach_feasibility(selected, case, policy)
    result["laboratory_hours"] = report["laboratory_hours"]
    result["usable_window_hours"] = report["usable_window_hours"]
    result["admissible_approaches"] = admissible_approaches(case, policy)

    for name in result["admissible_approaches"]:
        if name != selected:
            advisories.append(
                "%s would also fit the window; the record should say why %s "
                "was preferred" % (name, selected)
            )

    if gaps:
        findings.append(
            "the record for %s is missing %s" % (selected, ", ".join(gaps))
        )
        result["verdict"] = DOCUMENTATION_INCOMPLETE
        return result

    if not report["feasible"]:
        findings.extend(report["reasons"])
        result["verdict"] = APPROACH_NOT_FEASIBLE
        return result

    result["verdict"] = APPROACH_SELECTED_AND_DOCUMENTED
    return result
