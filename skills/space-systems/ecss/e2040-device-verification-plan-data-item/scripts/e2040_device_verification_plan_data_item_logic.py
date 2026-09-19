#!/usr/bin/env python3
"""Device verification plan contents (ECSS-E-ST-20-40C Annex C).

Offline, deterministic, standard library only. The ECSS clause is cited as
the anchor; the procedure below is a paraphrase into implementable logic.

Model
-----
The data item fixes three things a device verification plan has to carry:
the strategy it follows, the methods it will use, and the coverage it
commits to reach. Each one is checkable, and the useful checks run
between them rather than inside any one of them:

* the strategy names the approach and the levels verification happens at,
  and every requirement has to be assigned to a level the strategy
  actually declares;
* each requirement nominates one or more of the four methods, and the
  method has to be able to answer that kind of requirement. Inspection
  can confirm a connector is present; it cannot close a timing figure,
  so a performance requirement carrying inspection alone is unclosable
  however complete the plan looks;
* coverage goals are fractions of the requirement set, compared against
  what the plan actually assigns. A goal met exactly is met, so the
  comparison absorbs representation error rather than failing on the
  last bit of a division.

Every requirement also has to be covered at all. A requirement with no
method is the defect the coverage figure is meant to surface, so it is
counted and reported, never dropped from the denominator.
"""

import math

# The four verification methods.
ANALYSIS = "analysis"
REVIEW_OF_DESIGN = "review-of-design"
INSPECTION = "inspection"
TEST = "test"
VERIFICATION_METHODS = (ANALYSIS, REVIEW_OF_DESIGN, INSPECTION, TEST)
_METHOD_ALIASES = {
    "analysis": ANALYSIS,
    "a": ANALYSIS,
    "similarity": ANALYSIS,
    "review-of-design": REVIEW_OF_DESIGN,
    "review of design": REVIEW_OF_DESIGN,
    "rod": REVIEW_OF_DESIGN,
    "design review": REVIEW_OF_DESIGN,
    "inspection": INSPECTION,
    "i": INSPECTION,
    "test": TEST,
    "t": TEST,
}

# Requirement kinds the plan may carry, from the specification data item.
REQUIREMENT_KINDS = ("function", "performance", "interface", "quality")

# Methods able to answer each kind of requirement.
SUITABLE_METHODS = {
    "function": (TEST, ANALYSIS, REVIEW_OF_DESIGN),
    "performance": (TEST, ANALYSIS),
    "interface": (TEST, INSPECTION, ANALYSIS),
    "quality": (TEST, ANALYSIS, INSPECTION, REVIEW_OF_DESIGN),
}

# Approaches the strategy may declare.
APPROACHES = ("single-step", "incremental", "staged-with-heritage")

REL_TOL = 1e-12
ABS_TOL = 1e-18

_PLAN_REQUIRED_KEYS = ("strategy", "requirements")
_PLAN_OPTIONAL_KEYS = ("coverage_goals",)
_STRATEGY_KEYS = ("approach", "levels", "rationale")
_REQUIREMENT_KEYS = ("id", "kind", "methods", "level")


def _text(name, value, allow_empty=False):
    if not isinstance(value, str):
        raise ValueError("%s must be a string, got %r" % (name, value))
    out = value.strip()
    if not out and not allow_empty:
        raise ValueError("%s must be a non-empty string" % name)
    return out


def _fraction(name, value):
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise ValueError("%s must be a real number, got %r" % (name, value))
    out = float(value)
    if math.isnan(out) or math.isinf(out):
        raise ValueError("%s must be finite, got %r" % (name, value))
    if not 0.0 <= out <= 1.0:
        raise ValueError("%s must lie in [0, 1], got %g" % (name, out))
    return out


def meets_coverage_goal(achieved, goal):
    """True when achieved coverage reaches the goal, exact landings included."""
    achieved = _fraction("achieved", achieved)
    goal = _fraction("goal", goal)
    return achieved > goal or math.isclose(
        achieved, goal, rel_tol=REL_TOL, abs_tol=ABS_TOL
    )


def normalize_method(value):
    """Fold a method spelling onto one of the four recognised names."""
    key = " ".join(_text("method", value).lower().split())
    if key in _METHOD_ALIASES:
        return _METHOD_ALIASES[key]
    raise ValueError(
        "unknown verification method %r; use one of %s"
        % (value, ", ".join(VERIFICATION_METHODS))
    )


def normalize_kind(value):
    """Check a requirement kind against the four the specification carries."""
    key = " ".join(_text("kind", value).lower().split())
    aliases = {
        "function": "function",
        "functional": "function",
        "performance": "performance",
        "interface": "interface",
        "quality": "quality",
    }
    if key in aliases:
        return aliases[key]
    raise ValueError(
        "unknown requirement kind %r; use one of %s"
        % (value, ", ".join(REQUIREMENT_KINDS))
    )


def normalize_approach(value):
    """Check the strategy approach against the recognised names."""
    key = " ".join(_text("approach", value).lower().replace("_", " ").split())
    key = key.replace(" ", "-")
    if key in APPROACHES:
        return key
    raise ValueError(
        "unknown approach %r; use one of %s" % (value, ", ".join(APPROACHES))
    )


def suitable_methods_for(kind):
    """Methods able to answer this kind of requirement."""
    return SUITABLE_METHODS[normalize_kind(kind)]


def assess_method_suitability(kind, methods):
    """True when at least one nominated method can answer this kind."""
    allowed = set(suitable_methods_for(kind))
    if not isinstance(methods, (list, tuple, set)):
        raise ValueError("methods must be a list, tuple or set")
    nominated = {normalize_method(m) for m in methods}
    return bool(nominated & allowed)


def validate_strategy(strategy):
    """Check the strategy block and return the approach and levels."""
    if not isinstance(strategy, dict):
        raise ValueError("strategy must be a mapping")
    unknown = sorted(set(strategy) - set(_STRATEGY_KEYS))
    if unknown:
        raise ValueError("strategy has unknown keys: %s" % ", ".join(unknown))
    approach = strategy.get("approach", "")
    approach = normalize_approach(approach) if str(approach).strip() else ""
    levels = strategy.get("levels", [])
    if not isinstance(levels, (list, tuple)):
        raise ValueError("strategy.levels must be a list of verification levels")
    resolved = []
    for index, level in enumerate(levels):
        name = _text("strategy.levels[%d]" % index, level)
        if name in resolved:
            raise ValueError("duplicate verification level %r in strategy" % name)
        resolved.append(name)
    rationale = _text(
        "strategy.rationale", strategy.get("rationale", ""), allow_empty=True
    )
    return {"approach": approach, "levels": resolved, "rationale": rationale}


def validate_requirements(entries):
    """Check the requirement list and return it resolved in declared order."""
    if not isinstance(entries, (list, tuple)):
        raise ValueError("requirements must be a list")
    resolved = []
    seen = set()
    for index, entry in enumerate(entries):
        if not isinstance(entry, dict):
            raise ValueError("requirements[%d] must be a mapping" % index)
        unknown = sorted(set(entry) - set(_REQUIREMENT_KEYS))
        if unknown:
            raise ValueError(
                "requirements[%d] has unknown keys: %s" % (index, ", ".join(unknown))
            )
        for key in ("id", "kind"):
            if key not in entry:
                raise ValueError("requirements[%d] missing key: %s" % (index, key))
        req_id = _text("requirements[%d].id" % index, entry["id"])
        if req_id in seen:
            raise ValueError("duplicate requirement id %r" % req_id)
        seen.add(req_id)
        methods = entry.get("methods", [])
        if not isinstance(methods, (list, tuple)):
            raise ValueError("requirements[%d].methods must be a list" % index)
        resolved.append(
            {
                "id": req_id,
                "kind": normalize_kind(entry["kind"]),
                "methods": [normalize_method(m) for m in methods],
                "level": _text(
                    "requirements[%d].level" % index,
                    entry.get("level", ""),
                    allow_empty=True,
                ),
            }
        )
    return resolved


def coverage_by_method(requirements):
    """Fraction of the requirement set each method is nominated on."""
    total = len(requirements)
    if total == 0:
        raise ValueError("coverage_by_method needs at least one requirement")
    counts = {method: 0 for method in VERIFICATION_METHODS}
    for requirement in requirements:
        for method in set(requirement["methods"]):
            counts[method] += 1
    return {method: counts[method] / total for method in VERIFICATION_METHODS}


def overall_coverage(requirements):
    """Fraction of requirements carrying at least one method."""
    total = len(requirements)
    if total == 0:
        raise ValueError("overall_coverage needs at least one requirement")
    covered = sum(1 for r in requirements if r["methods"])
    return covered / total


def uncovered_requirements(requirements):
    """Requirement ids with no verification method at all."""
    return sorted(r["id"] for r in requirements if not r["methods"])


def evaluate_verification_plan(plan):
    """Full Annex C assessment of one device verification plan.

    Returns the resolved strategy, the per-method and overall coverage,
    the findings and the verdict.
    """
    if not isinstance(plan, dict):
        raise ValueError("plan must be a mapping of strategy, requirements and goals")
    known = set(_PLAN_REQUIRED_KEYS) | set(_PLAN_OPTIONAL_KEYS)
    unknown = sorted(set(plan) - known)
    if unknown:
        raise ValueError("unknown plan keys: %s" % ", ".join(unknown))
    missing = [key for key in _PLAN_REQUIRED_KEYS if key not in plan]
    if missing:
        raise ValueError("plan missing required keys: %s" % ", ".join(missing))

    strategy = validate_strategy(plan["strategy"])
    requirements = validate_requirements(plan["requirements"])
    if not requirements:
        raise ValueError("plan must carry at least one requirement to verify")

    goals = plan.get("coverage_goals", {}) or {}
    if not isinstance(goals, dict):
        raise ValueError("coverage_goals must be a mapping of method to fraction")
    stray = sorted(set(goals) - set(VERIFICATION_METHODS) - {"overall"})
    if stray:
        raise ValueError("coverage_goals names unknown methods: %s" % ", ".join(stray))

    findings = []
    if not strategy["approach"]:
        findings.append(
            {
                "code": "strategy-without-approach",
                "detail": "the strategy names no approach from %s"
                % ", ".join(APPROACHES),
            }
        )
    if not strategy["levels"]:
        findings.append(
            {
                "code": "strategy-without-levels",
                "detail": "the strategy declares no verification level, so no "
                "requirement can be placed",
            }
        )

    for requirement in requirements:
        if not requirement["methods"]:
            findings.append(
                {
                    "code": "requirement-without-method",
                    "requirement": requirement["id"],
                    "detail": "requirement %s nominates no verification method"
                    % requirement["id"],
                }
            )
        elif not assess_method_suitability(
            requirement["kind"], requirement["methods"]
        ):
            findings.append(
                {
                    "code": "method-unsuitable-for-requirement-kind",
                    "requirement": requirement["id"],
                    "kind": requirement["kind"],
                    "methods": requirement["methods"],
                    "detail": "a %s requirement cannot be closed by %s; use one of "
                    "%s"
                    % (
                        requirement["kind"],
                        ", ".join(requirement["methods"]),
                        ", ".join(suitable_methods_for(requirement["kind"])),
                    ),
                }
            )
        if not requirement["level"]:
            findings.append(
                {
                    "code": "requirement-without-level",
                    "requirement": requirement["id"],
                    "detail": "requirement %s is placed at no verification level"
                    % requirement["id"],
                }
            )
        elif strategy["levels"] and requirement["level"] not in strategy["levels"]:
            findings.append(
                {
                    "code": "verification-level-not-in-strategy",
                    "requirement": requirement["id"],
                    "level": requirement["level"],
                    "detail": "requirement %s is placed at %r, which the strategy "
                    "does not declare" % (requirement["id"], requirement["level"]),
                }
            )

    per_method = coverage_by_method(requirements)
    overall = overall_coverage(requirements)
    for name, goal in sorted(goals.items()):
        goal_value = _fraction("coverage_goals[%s]" % name, goal)
        achieved = overall if name == "overall" else per_method[name]
        if not meets_coverage_goal(achieved, goal_value):
            findings.append(
                {
                    "code": "coverage-goal-missed",
                    "goal_name": name,
                    "achieved": achieved,
                    "goal": goal_value,
                    "detail": "%s coverage reaches %.1f %% against a %.1f %% goal"
                    % (name, 100.0 * achieved, 100.0 * goal_value),
                }
            )

    return {
        "approach": strategy["approach"],
        "levels": strategy["levels"],
        "requirement_count": len(requirements),
        "coverage_by_method": per_method,
        "overall_coverage": overall,
        "uncovered_requirements": uncovered_requirements(requirements),
        "findings": findings,
        "acceptable": not findings,
    }
