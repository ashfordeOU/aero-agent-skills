#!/usr/bin/env python3
"""Applicability and objective of an ECSS thermal test campaign.

Anchor: ECSS-Q-ST-70-04C, framework clauses. The procedure below is a
paraphrase into implementable steps; no standard text is reproduced.

Two questions come before any profile is written. Does a thermal test
apply to this item at all, and if it does, what is the campaign for?

The first question is answered from the environment the item is
predicted to see. A cycling run is driven by the span between the
predicted cold and hot extremes; below a declared span there is no
cyclic driver worth a chamber. A vacuum run is driven by the pressure
the item operates at, or by a degradation mechanism that only shows
itself once the surrounding gas is gone.

The second question is answered from where the programme stands. A
screening run is a cheap elimination of weak candidates early, run on
few specimens for few cycles, and it demonstrates nothing. A
qualification run demonstrates capability against the environment, on
the full specimen count for the full cycle count. An acceptance run
verifies that a delivered item is free of workmanship escapes. A
genuinely identical item already qualified over a wider envelope needs
no new test, but only when the envelope, the cycle count and the
process are all covered, and the justification is recorded.

Standard library only, offline, deterministic.
"""

from __future__ import annotations

import math

ITEM_CATEGORIES = ("material", "process", "mechanical-part", "assembly")
PROGRAMME_PHASES = (
    "pre-development",
    "development",
    "qualification",
    "acceptance",
)
HERITAGE_LEVELS = ("none", "similar-item", "identical-qualified")
PRESSURE_ENVIRONMENTS = ("ambient-pressure", "vacuum", "vacuum-and-ambient")

THERMAL_CYCLING = "thermal-cycling"
THERMAL_VACUUM = "thermal-vacuum"
TEST_TYPES = (THERMAL_CYCLING, THERMAL_VACUUM)

SCREENING = "screening"
QUALIFICATION = "qualification"
ACCEPTANCE_VERIFICATION = "acceptance-verification"
NO_NEW_TEST = "no-new-test"
OBJECTIVES = (SCREENING, QUALIFICATION, ACCEPTANCE_VERIFICATION, NO_NEW_TEST)

DEFAULT_APPLICABILITY_POLICY = {
    "cycling_delta_t_threshold_k": 20.0,
    "vacuum_pressure_threshold_pa": 1.0,
    "heritage_envelope_margin_k": 5.0,
    "specimen_count": {
        SCREENING: 3,
        QUALIFICATION: 5,
        ACCEPTANCE_VERIFICATION: 2,
    },
    "cycle_count": {
        SCREENING: 10,
        QUALIFICATION: 100,
        ACCEPTANCE_VERIFICATION: 8,
    },
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


def _require_choice(name, value, allowed):
    if value not in allowed:
        raise ValueError(
            "%s must be one of %s, got %r" % (name, ", ".join(allowed), value)
        )
    return value


def _require_bool(name, value):
    if not isinstance(value, bool):
        raise ValueError("%s must be a boolean, got %r" % (name, value))
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


def validate_applicability_policy(policy):
    """Check an applicability policy carries sane thresholds and tables."""
    if not isinstance(policy, dict):
        raise ValueError("policy must be a mapping, got %r" % (policy,))
    _require_positive(
        "cycling_delta_t_threshold_k", policy.get("cycling_delta_t_threshold_k")
    )
    _require_positive(
        "vacuum_pressure_threshold_pa", policy.get("vacuum_pressure_threshold_pa")
    )
    _require_non_negative(
        "heritage_envelope_margin_k", policy.get("heritage_envelope_margin_k")
    )
    tested_objectives = (SCREENING, QUALIFICATION, ACCEPTANCE_VERIFICATION)
    for key in ("specimen_count", "cycle_count"):
        table = policy.get(key)
        if not isinstance(table, dict):
            raise ValueError("policy %s must be a mapping" % key)
        missing = set(tested_objectives) - set(table)
        if missing:
            raise ValueError(
                "policy %s is missing entries: %s" % (key, ", ".join(sorted(missing)))
            )
        for objective in tested_objectives:
            count = table[objective]
            if not isinstance(count, int) or isinstance(count, bool) or count < 1:
                raise ValueError(
                    "policy %s[%s] must be an integer of at least 1, got %r"
                    % (key, objective, count)
                )
    if policy["cycle_count"][QUALIFICATION] < policy["cycle_count"][SCREENING]:
        raise ValueError(
            "policy cycle_count for qualification is below the screening count"
        )
    return policy


def predicted_span_k(predicted_min_k, predicted_max_k):
    """Span between the predicted cold and hot extremes, in kelvin."""
    low = _require_positive("predicted_min_k", predicted_min_k)
    high = _require_positive("predicted_max_k", predicted_max_k)
    if high < low:
        raise ValueError(
            "predicted_max_k %g K is below predicted_min_k %g K" % (high, low)
        )
    return high - low


def cycling_is_applicable(span_k, policy=DEFAULT_APPLICABILITY_POLICY):
    """A cyclic driver exists when the predicted span reaches the threshold."""
    validate_applicability_policy(policy)
    span = _require_non_negative("span_k", span_k)
    return _at_least(span, policy["cycling_delta_t_threshold_k"])


def vacuum_is_applicable(
    pressure_environment,
    operating_pressure_pa=None,
    vacuum_sensitive=False,
    policy=DEFAULT_APPLICABILITY_POLICY,
):
    """A vacuum driver exists from the operating pressure or a mechanism."""
    validate_applicability_policy(policy)
    _require_choice(
        "pressure_environment", pressure_environment, PRESSURE_ENVIRONMENTS
    )
    _require_bool("vacuum_sensitive", vacuum_sensitive)
    if vacuum_sensitive:
        return True
    if pressure_environment == "ambient-pressure":
        return False
    if operating_pressure_pa is None:
        return True
    pressure = _require_positive("operating_pressure_pa", operating_pressure_pa)
    return _at_most(pressure, policy["vacuum_pressure_threshold_pa"])


def applicable_test_types(case, policy=DEFAULT_APPLICABILITY_POLICY):
    """Test types the predicted environment actually drives, in fixed order."""
    if not isinstance(case, dict):
        raise ValueError("case must be a mapping, got %r" % (case,))
    span = predicted_span_k(case.get("predicted_min_k"), case.get("predicted_max_k"))
    types = []
    if cycling_is_applicable(span, policy):
        types.append(THERMAL_CYCLING)
    if vacuum_is_applicable(
        _require_choice(
            "pressure_environment",
            case.get("pressure_environment"),
            PRESSURE_ENVIRONMENTS,
        ),
        case.get("operating_pressure_pa"),
        bool(case.get("vacuum_sensitive", False)),
        policy,
    ):
        types.append(THERMAL_VACUUM)
    return tuple(types)


def heritage_shortfalls(case, policy=DEFAULT_APPLICABILITY_POLICY):
    """Reasons an identical-item heritage claim fails to cover this case.

    An empty tuple means the claim stands and no new test is owed.
    """
    validate_applicability_policy(policy)
    if not isinstance(case, dict):
        raise ValueError("case must be a mapping, got %r" % (case,))
    heritage = _require_choice("heritage", case.get("heritage"), HERITAGE_LEVELS)
    if heritage != "identical-qualified":
        return ("heritage basis is %s, not an identical qualified item" % heritage,)
    shortfalls = []
    margin = policy["heritage_envelope_margin_k"]
    predicted_min = _require_positive("predicted_min_k", case.get("predicted_min_k"))
    predicted_max = _require_positive("predicted_max_k", case.get("predicted_max_k"))
    qualified_min = _require_positive(
        "qualified_min_k", case.get("qualified_min_k")
    )
    qualified_max = _require_positive(
        "qualified_max_k", case.get("qualified_max_k")
    )
    if not _at_most(qualified_min, predicted_min - margin):
        shortfalls.append(
            "qualified cold extreme %.2f K does not reach %.2f K, the predicted "
            "cold extreme with the heritage margin" % (qualified_min, predicted_min - margin)
        )
    if not _at_least(qualified_max, predicted_max + margin):
        shortfalls.append(
            "qualified hot extreme %.2f K does not reach %.2f K, the predicted "
            "hot extreme with the heritage margin" % (qualified_max, predicted_max + margin)
        )
    qualified_cycles = case.get("qualified_cycles")
    needed_cycles = policy["cycle_count"][QUALIFICATION]
    if qualified_cycles is None:
        shortfalls.append("no qualified cycle count is recorded for the heritage item")
    else:
        if not isinstance(qualified_cycles, int) or isinstance(qualified_cycles, bool):
            raise ValueError(
                "qualified_cycles must be an integer, got %r" % (qualified_cycles,)
            )
        if qualified_cycles < needed_cycles:
            shortfalls.append(
                "heritage item saw %d cycles against the %d this campaign needs"
                % (qualified_cycles, needed_cycles)
            )
    if not bool(case.get("same_process", False)):
        shortfalls.append(
            "the manufacturing process differs from the qualified item, so the "
            "heritage result does not carry across"
        )
    return tuple(shortfalls)


def select_objective(case, policy=DEFAULT_APPLICABILITY_POLICY):
    """Objective the programme phase and the heritage claim jointly force."""
    validate_applicability_policy(policy)
    if not isinstance(case, dict):
        raise ValueError("case must be a mapping, got %r" % (case,))
    phase = _require_choice(
        "programme_phase", case.get("programme_phase"), PROGRAMME_PHASES
    )
    shortfalls = heritage_shortfalls(case, policy)
    if not shortfalls:
        return {
            "objective": NO_NEW_TEST,
            "rationale": (
                "an identical item is qualified beyond this envelope, for at "
                "least the cycle count needed, on the same process"
            ),
            "heritage_shortfalls": shortfalls,
        }
    if phase in ("pre-development", "development"):
        objective = SCREENING
        rationale = (
            "the campaign is an early elimination of weak candidates and "
            "demonstrates no capability"
        )
    elif phase == "qualification":
        objective = QUALIFICATION
        rationale = "the campaign has to demonstrate capability against the environment"
    else:
        objective = ACCEPTANCE_VERIFICATION
        rationale = "the campaign verifies a delivered item against workmanship escapes"
    return {
        "objective": objective,
        "rationale": rationale,
        "heritage_shortfalls": shortfalls,
    }


def campaign_sizing(objective, policy=DEFAULT_APPLICABILITY_POLICY):
    """Specimen count and cycle count the objective demands."""
    validate_applicability_policy(policy)
    _require_choice("objective", objective, OBJECTIVES)
    if objective == NO_NEW_TEST:
        return {"specimen_count": 0, "cycle_count": 0}
    return {
        "specimen_count": policy["specimen_count"][objective],
        "cycle_count": policy["cycle_count"][objective],
    }


def assess_applicability(case, policy=DEFAULT_APPLICABILITY_POLICY):
    """Full framework decision: does a thermal test apply, and what for."""
    validate_applicability_policy(policy)
    if not isinstance(case, dict):
        raise ValueError("case must be a mapping, got %r" % (case,))
    _require_choice("item_category", case.get("item_category"), ITEM_CATEGORIES)
    types = applicable_test_types(case, policy)
    decision = select_objective(case, policy)
    objective = decision["objective"]
    sizing = campaign_sizing(objective, policy)
    findings = []
    duties = []
    span = predicted_span_k(case.get("predicted_min_k"), case.get("predicted_max_k"))
    if not types:
        findings.append(
            "the predicted span of %.2f K and the operating pressure drive neither "
            "a cycling nor a vacuum run" % span
        )
        objective = NO_NEW_TEST
        sizing = campaign_sizing(NO_NEW_TEST, policy)
    if objective == NO_NEW_TEST and types:
        duties.append(
            "record the heritage justification and the qualified envelope it rests on"
        )
    if objective == SCREENING:
        duties.append(
            "state in the report that a screening result qualifies nothing and "
            "the qualification run is still owed"
        )
        for shortfall in decision["heritage_shortfalls"]:
            findings.append(shortfall)
    if objective == QUALIFICATION and THERMAL_VACUUM in types:
        duties.append(
            "run the vacuum extreme on the same specimens that saw the cycling run, "
            "or justify a separate specimen set"
        )
    return {
        "item_category": case["item_category"],
        "objective": objective,
        "rationale": decision["rationale"],
        "test_types": types,
        "predicted_span_k": span,
        "specimen_count": sizing["specimen_count"],
        "cycle_count": sizing["cycle_count"],
        "heritage_shortfalls": decision["heritage_shortfalls"],
        "duties": duties,
        "findings": findings,
    }
