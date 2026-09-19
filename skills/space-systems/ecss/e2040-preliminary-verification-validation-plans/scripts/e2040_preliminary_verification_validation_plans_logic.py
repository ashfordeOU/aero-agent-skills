#!/usr/bin/env python3
"""Preliminary verification and validation plans (ECSS-E-ST-20-40C 5.2.4).

Offline, deterministic, standard library only. The ECSS clause is cited as
the anchor; the procedure below is a paraphrase into implementable logic.

Model
-----
While the device is still being defined, two preliminary plans are
written: how it will be verified, and how it will be validated. They are
judged on intention rather than procedure, and three properties decide
whether the definition phase can close on them:

* every requirement carries a provisional method and an article to run
  it on. The article is what turns a method into a cost and a build, and
  the article has to be one the development plan actually declares;
* every validation objective carries an activity deep enough to answer
  it. A review confirms that somebody intended the right thing; only an
  end-to-end run or an operational demonstration independently answers a
  mission-level objective;
* the two plans stay distinct. Verification asks whether the device
  meets its requirements, validation asks whether those were the right
  requirements, and an objective restated as a requirement row deletes
  the second question while improving the coverage figure.

Maturity is reported as two fractions and their mean, because a full
verification plan averaged with an empty validation plan looks like
progress on both. The fractions land exactly on the phase-gate target,
so the comparison absorbs the representation error of a division.
"""

import math

# Provisional verification methods.
VERIFICATION_METHODS = ("analysis", "review-of-design", "inspection", "test")
_METHOD_ALIASES = {
    "analysis": "analysis",
    "a": "analysis",
    "similarity": "analysis",
    "review-of-design": "review-of-design",
    "review of design": "review-of-design",
    "rod": "review-of-design",
    "inspection": "inspection",
    "i": "inspection",
    "test": "test",
    "t": "test",
}

# Levels a verification activity can run at.
VERIFICATION_LEVELS = ("device", "subsystem", "system")
_LEVEL_ALIASES = {
    "device": "device",
    "equipment": "device",
    "unit": "device",
    "subsystem": "subsystem",
    "string": "subsystem",
    "system": "system",
    "spacecraft": "system",
}

# The kind of need a validation objective answers, shallowest first.
OBJECTIVE_KINDS = ("interface-agreement", "operational-scenario", "mission-need")
_OBJECTIVE_KIND_ALIASES = {
    "interface-agreement": "interface-agreement",
    "interface": "interface-agreement",
    "operational-scenario": "operational-scenario",
    "operations": "operational-scenario",
    "scenario": "operational-scenario",
    "mission-need": "mission-need",
    "mission": "mission-need",
    "user-need": "mission-need",
}

# Validation activities, with the depth each one reaches.
VALIDATION_ACTIVITIES = (
    "document-review",
    "model-simulation",
    "operational-demonstration",
    "end-to-end-test",
)
_ACTIVITY_ALIASES = {
    "document-review": "document-review",
    "review": "document-review",
    "desk-check": "document-review",
    "model-simulation": "model-simulation",
    "simulation": "model-simulation",
    "digital-twin-run": "model-simulation",
    "operational-demonstration": "operational-demonstration",
    "demonstration": "operational-demonstration",
    "end-to-end-test": "end-to-end-test",
    "end to end test": "end-to-end-test",
    "e2e": "end-to-end-test",
}
ACTIVITY_DEPTH = {
    "document-review": 1,
    "model-simulation": 2,
    "operational-demonstration": 3,
    "end-to-end-test": 4,
}
# The shallowest activity that can answer each kind of objective.
REQUIRED_DEPTH = {
    "interface-agreement": 1,
    "operational-scenario": 2,
    "mission-need": 3,
}

REL_TOL = 1e-12
ABS_TOL = 1e-18

_PLAN_REQUIRED_KEYS = ("models", "verification", "validation")
_PLAN_OPTIONAL_KEYS = ("maturity_target",)
_ENTRY_KEYS = ("requirement", "method", "model", "level")
_OBJECTIVE_KEYS = ("id", "kind", "activities", "statement")


def _text(name, value, allow_empty=False):
    if not isinstance(value, str):
        raise ValueError("%s must be a string, got %r" % (name, value))
    out = value.strip()
    if not out and not allow_empty:
        raise ValueError("%s must be a non-empty string" % name)
    return out


def _key(value):
    return " ".join(str(value).strip().lower().replace("_", " ").split())


def _fraction(name, value):
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise ValueError("%s must be a real number, got %r" % (name, value))
    out = float(value)
    if math.isnan(out) or math.isinf(out):
        raise ValueError("%s must be finite, got %r" % (name, value))
    if not 0.0 <= out <= 1.0:
        raise ValueError("%s must lie in [0, 1], got %g" % (name, out))
    return out


def meets_maturity_target(achieved, target):
    """True when a maturity fraction reaches the target, landings included."""
    achieved = _fraction("achieved", achieved)
    target = _fraction("target", target)
    return achieved > target or math.isclose(
        achieved, target, rel_tol=REL_TOL, abs_tol=ABS_TOL
    )


def _fold(name, value, aliases, vocabulary):
    key = _key(_text(name, value))
    for candidate in (key, key.replace(" ", "-"), key.replace("-", " ")):
        if candidate in aliases:
            return aliases[candidate]
    raise ValueError(
        "unknown %s %r; use one of %s" % (name, value, ", ".join(vocabulary))
    )


def normalize_method(value):
    """Fold a provisional verification method onto one of the four names."""
    return _fold("method", value, _METHOD_ALIASES, VERIFICATION_METHODS)


def normalize_level(value):
    """Fold a verification level onto device, subsystem or system."""
    return _fold("level", value, _LEVEL_ALIASES, VERIFICATION_LEVELS)


def normalize_objective_kind(value):
    """Fold the kind of need a validation objective answers."""
    return _fold("kind", value, _OBJECTIVE_KIND_ALIASES, OBJECTIVE_KINDS)


def normalize_activity(value):
    """Fold a validation activity onto one of the recognised activities."""
    return _fold("activity", value, _ACTIVITY_ALIASES, VALIDATION_ACTIVITIES)


def activity_depth(activity):
    """How deeply a validation activity can answer an objective."""
    return ACTIVITY_DEPTH[normalize_activity(activity)]


def depth_required_for(kind):
    """Shallowest activity depth that can answer this kind of objective."""
    return REQUIRED_DEPTH[normalize_objective_kind(kind)]


def validate_model_set(models):
    """Fold the model set the development plan declares."""
    if not isinstance(models, (list, tuple)):
        raise ValueError("models must be a list of development models")
    resolved = []
    for index, model in enumerate(models):
        name = _text("models[%d]" % index, model)
        if name not in resolved:
            resolved.append(name)
    if not resolved:
        raise ValueError("the plan must declare at least one development model")
    return resolved


def validate_verification_entries(entries):
    """Check the preliminary verification entries in declared order."""
    if not isinstance(entries, (list, tuple)):
        raise ValueError("verification must be a list of requirement entries")
    resolved = []
    seen = set()
    for index, entry in enumerate(entries):
        if not isinstance(entry, dict):
            raise ValueError("verification[%d] must be a mapping" % index)
        unknown = sorted(set(entry) - set(_ENTRY_KEYS))
        if unknown:
            raise ValueError(
                "verification[%d] has unknown keys: %s" % (index, ", ".join(unknown))
            )
        if "requirement" not in entry:
            raise ValueError("verification[%d] missing key: requirement" % index)
        requirement = _text(
            "verification[%d].requirement" % index, entry["requirement"]
        )
        if requirement in seen:
            raise ValueError("duplicate verification requirement %r" % requirement)
        seen.add(requirement)
        raw_method = entry.get("method", "")
        raw_level = entry.get("level", "")
        resolved.append(
            {
                "requirement": requirement,
                "method": normalize_method(raw_method)
                if str(raw_method).strip()
                else "",
                "model": _text(
                    "verification[%d].model" % index,
                    entry.get("model", ""),
                    allow_empty=True,
                ),
                "level": normalize_level(raw_level)
                if str(raw_level).strip()
                else "",
            }
        )
    return resolved


def validate_validation_objectives(entries):
    """Check the validation objectives in declared order."""
    if not isinstance(entries, (list, tuple)):
        raise ValueError("validation must be a list of objectives")
    resolved = []
    seen = set()
    for index, entry in enumerate(entries):
        if not isinstance(entry, dict):
            raise ValueError("validation[%d] must be a mapping" % index)
        unknown = sorted(set(entry) - set(_OBJECTIVE_KEYS))
        if unknown:
            raise ValueError(
                "validation[%d] has unknown keys: %s" % (index, ", ".join(unknown))
            )
        for key in ("id", "kind"):
            if key not in entry:
                raise ValueError("validation[%d] missing key: %s" % (index, key))
        objective_id = _text("validation[%d].id" % index, entry["id"])
        if objective_id in seen:
            raise ValueError("duplicate validation objective %r" % objective_id)
        seen.add(objective_id)
        activities = entry.get("activities", [])
        if not isinstance(activities, (list, tuple)):
            raise ValueError("validation[%d].activities must be a list" % index)
        folded = []
        for activity in activities:
            name = normalize_activity(activity)
            if name not in folded:
                folded.append(name)
        resolved.append(
            {
                "id": objective_id,
                "kind": normalize_objective_kind(entry["kind"]),
                "activities": folded,
                "statement": _text(
                    "validation[%d].statement" % index,
                    entry.get("statement", ""),
                    allow_empty=True,
                ),
            }
        )
    return resolved


def entry_is_allocated(entry, models):
    """True when an entry carries a method and an article the plan builds."""
    return bool(entry["method"]) and entry["model"] in models


def verification_maturity(entries, models):
    """Share of requirements carrying both a method and a declared article."""
    if not entries:
        raise ValueError("verification_maturity needs at least one entry")
    allocated = sum(1 for entry in entries if entry_is_allocated(entry, models))
    return allocated / len(entries)


def objective_is_answerable(objective):
    """True when at least one activity is deep enough for the objective."""
    needed = REQUIRED_DEPTH[objective["kind"]]
    return any(ACTIVITY_DEPTH[a] >= needed for a in objective["activities"])


def validation_maturity(objectives):
    """Share of validation objectives carrying an activity deep enough."""
    if not objectives:
        raise ValueError("validation_maturity needs at least one objective")
    answerable = sum(1 for o in objectives if objective_is_answerable(o))
    return answerable / len(objectives)


def preliminary_maturity(verification_fraction, validation_fraction):
    """The mean of the two plan maturities, reported beside both."""
    left = _fraction("verification_fraction", verification_fraction)
    right = _fraction("validation_fraction", validation_fraction)
    return (left + right) / 2.0


def evaluate_preliminary_vv_plans(plan):
    """Full clause 5.2.4 assessment of the two preliminary plans.

    Returns the two maturities, their mean, the findings and whether the
    definition phase can close on them.
    """
    if not isinstance(plan, dict):
        raise ValueError(
            "plan must be a mapping of models, verification and validation"
        )
    known = set(_PLAN_REQUIRED_KEYS) | set(_PLAN_OPTIONAL_KEYS)
    unknown = sorted(set(plan) - known)
    if unknown:
        raise ValueError("unknown plan keys: %s" % ", ".join(unknown))
    missing = [key for key in _PLAN_REQUIRED_KEYS if key not in plan]
    if missing:
        raise ValueError("plan missing required keys: %s" % ", ".join(missing))

    models = validate_model_set(plan["models"])
    entries = validate_verification_entries(plan["verification"])
    objectives = validate_validation_objectives(plan["validation"])
    if not entries:
        raise ValueError("the preliminary verification plan carries no requirement")
    if not objectives:
        raise ValueError("the preliminary validation plan carries no objective")
    target = _fraction("maturity_target", plan.get("maturity_target", 0.8))

    findings = []
    for entry in entries:
        if not entry["method"]:
            findings.append(
                {
                    "code": "requirement-without-provisional-method",
                    "requirement": entry["requirement"],
                    "detail": "requirement %s carries no provisional verification "
                    "method" % entry["requirement"],
                }
            )
        if not entry["model"]:
            findings.append(
                {
                    "code": "requirement-without-model-allocation",
                    "requirement": entry["requirement"],
                    "detail": "requirement %s names no article to be verified on"
                    % entry["requirement"],
                }
            )
        elif entry["model"] not in models:
            findings.append(
                {
                    "code": "model-not-in-declared-set",
                    "requirement": entry["requirement"],
                    "model": entry["model"],
                    "detail": "requirement %s is allocated to %r, which the "
                    "development plan does not build"
                    % (entry["requirement"], entry["model"]),
                }
            )

    requirement_ids = {entry["requirement"] for entry in entries}
    for objective in objectives:
        if not objective["activities"]:
            findings.append(
                {
                    "code": "validation-objective-without-activity",
                    "objective": objective["id"],
                    "detail": "objective %s carries no validation activity"
                    % objective["id"],
                }
            )
        elif not objective_is_answerable(objective):
            findings.append(
                {
                    "code": "validation-depth-insufficient",
                    "objective": objective["id"],
                    "kind": objective["kind"],
                    "detail": "a %s objective cannot be answered by %s alone"
                    % (objective["kind"], ", ".join(objective["activities"])),
                }
            )
        if objective["id"] in requirement_ids:
            findings.append(
                {
                    "code": "validation-objective-restated-as-requirement",
                    "objective": objective["id"],
                    "detail": "objective %s also appears as a verification "
                    "requirement, so only one of the two questions is being asked"
                    % objective["id"],
                }
            )

    verification_fraction = verification_maturity(entries, models)
    validation_fraction = validation_maturity(objectives)
    combined = preliminary_maturity(verification_fraction, validation_fraction)

    for name, value in (
        ("verification", verification_fraction),
        ("validation", validation_fraction),
    ):
        if not meets_maturity_target(value, target):
            findings.append(
                {
                    "code": "preliminary-plan-below-maturity-target",
                    "plan": name,
                    "achieved": value,
                    "target": target,
                    "detail": "the preliminary %s plan reaches %.1f %% maturity "
                    "against a %.1f %% target"
                    % (name, 100.0 * value, 100.0 * target),
                }
            )

    return {
        "models": models,
        "requirement_count": len(entries),
        "objective_count": len(objectives),
        "verification_maturity": verification_fraction,
        "validation_maturity": validation_fraction,
        "preliminary_maturity": combined,
        "maturity_target": target,
        "findings": findings,
        "phase_gate_ready": not findings,
    }
