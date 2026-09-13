#!/usr/bin/env python3
"""Purpose of the coverglass conductive coating adherence test.

Anchor: ECSS-E-ST-20-08C clause 6.4.3.9.1 -- the adherence test exists to show
that the conductive coating carried on the coverglass stays durable in service.
The procedure below is a paraphrase into implementable steps; no standard text
is reproduced.

Why the test exists
-------------------
The coating on a coverglass is not decoration. It is the bleed path that keeps
the front surface of a solar array from charging differentially, and it is a
few tens of nanometres thick. Everything the array meets between coating and
end of life works on that film: thermal cycling shears it against a glass it
does not match, solar ultraviolet and atomic oxygen attack the interface,
ground handling and cleaning abrade it, launch acoustics and vibration shake
it, and damp storage creeps under it. An adherence test is bought to show the
film is still attached after those environments, so the bleed path still
exists when the array is on orbit.

Two things therefore decide whether and why the test is applied:

    what the coverglass carries   a declared conductive coating, or none, in
                                  which case there is no bleed path to lose
                                  and the test has nothing to demonstrate
    what service demands of it    the declared service stressors, each scaled
                                  by how much of its qualification reference
                                  the mission actually spends, accumulated
                                  into one service demand

A planned check only serves the purpose when it reads the coating after the
environments that loosen it, and reads enough subgroup samples to speak for
the lot. A check run on pristine, as-coated glass demonstrates the coating
process, not the durability the clause asks about.
"""

import math

__all__ = [
    "STRESSOR_OBJECTIVES",
    "LOOSENING_STRESSORS",
    "COMMON_OBJECTIVE",
    "DEFAULT_ADHERENCE_POLICY",
    "TEST_NOT_REQUIRED",
    "CHECK_NOT_PLANNED",
    "CHECK_UNDER_SCOPE",
    "CHECK_SERVES_PURPOSE",
    "validate_policy",
    "validate_stressors",
    "objectives_for",
    "service_demand",
    "check_is_justified",
    "grade_planned_check",
    "assess_adherence_purpose",
]

# Each service stressor the coating meets turns into the durability objective
# the adherence check demonstrates against it.
STRESSOR_OBJECTIVES = {
    "thermal-cycling": "coating-adhesion-after-thermal-cycling",
    "solar-ultraviolet": "coating-adhesion-after-ultraviolet-exposure",
    "atomic-oxygen": "coating-adhesion-after-atomic-oxygen-erosion",
    "electrostatic-charging": "front-surface-charge-bleed-continuity",
    "ground-handling-and-cleaning": "coating-adhesion-after-handling-and-cleaning",
    "launch-vibration-and-acoustics": "coating-adhesion-after-launch-loads",
    "humidity-exposure": "coating-adhesion-after-damp-heat",
}

SERVICE_STRESSORS = tuple(sorted(STRESSOR_OBJECTIVES))

# The stressors that physically work on the coating-to-glass interface. A check
# that runs before these has not seen the durability it is meant to report.
LOOSENING_STRESSORS = (
    "thermal-cycling",
    "humidity-exposure",
    "ground-handling-and-cleaning",
    "launch-vibration-and-acoustics",
)

# Every coated coverglass shares this one, whatever else is declared.
COMMON_OBJECTIVE = "front-surface-conductive-path-retention"

# A declared policy, not a physical constant: a project substitutes its own.
# weights: how much of the service demand each stressor can contribute at a
# severity fraction of one. trigger: the demand at which a check is earned.
DEFAULT_ADHERENCE_POLICY = {
    "weights": {
        "thermal-cycling": 1.0,
        "solar-ultraviolet": 0.4,
        "atomic-oxygen": 0.5,
        "electrostatic-charging": 0.6,
        "ground-handling-and-cleaning": 0.8,
        "launch-vibration-and-acoustics": 0.5,
        "humidity-exposure": 0.9,
    },
    "demand_trigger": 1.0,
    "min_subgroup_samples": 4,
}

TEST_NOT_REQUIRED = "test-not-required"
CHECK_NOT_PLANNED = "check-not-planned"
CHECK_UNDER_SCOPE = "check-under-scope"
CHECK_SERVES_PURPOSE = "check-serves-purpose"

_REL_TOL = 1e-9


def _real(value, label):
    """Return a finite float or raise."""
    if not isinstance(value, (int, float)) or isinstance(value, bool):
        raise ValueError("%s must be a real number" % label)
    value = float(value)
    if not math.isfinite(value):
        raise ValueError("%s must be finite" % label)
    return value


def _fraction(value, label):
    """Return a finite float inside the unit interval or raise."""
    value = _real(value, label)
    if value < 0.0 or value > 1.0:
        raise ValueError("%s must sit between 0 and 1: %g" % (label, value))
    return value


def validate_policy(policy=None):
    """Return a validated adherence policy, defaults filled in."""
    if policy is None:
        policy = {}
    if not isinstance(policy, dict):
        raise ValueError("policy must be a mapping")
    merged = {
        "weights": dict(DEFAULT_ADHERENCE_POLICY["weights"]),
        "demand_trigger": DEFAULT_ADHERENCE_POLICY["demand_trigger"],
        "min_subgroup_samples": DEFAULT_ADHERENCE_POLICY["min_subgroup_samples"],
    }
    weights = policy.get("weights")
    if weights is not None:
        if not isinstance(weights, dict) or not weights:
            raise ValueError("policy weights must be a non-empty mapping")
        for name, weight in weights.items():
            if name not in STRESSOR_OBJECTIVES:
                raise ValueError("unrecognised service stressor in policy weights: %s" % name)
            value = _real(weight, "weight of %s" % name)
            if value < 0.0:
                raise ValueError("weight of %s must not be negative" % name)
            merged["weights"][name] = value
    if "demand_trigger" in policy:
        trigger = _real(policy["demand_trigger"], "demand_trigger")
        if trigger <= 0.0:
            raise ValueError("demand_trigger must be positive")
        merged["demand_trigger"] = trigger
    if "min_subgroup_samples" in policy:
        floor = policy["min_subgroup_samples"]
        if not isinstance(floor, int) or isinstance(floor, bool) or floor < 1:
            raise ValueError("min_subgroup_samples must be a positive integer")
        merged["min_subgroup_samples"] = floor
    return merged


def validate_stressors(stressors):
    """Return the validated service stressor inventory as name -> severity."""
    if not isinstance(stressors, (list, tuple)):
        raise ValueError("service stressors must be a sequence of entries")
    inventory = {}
    for index, entry in enumerate(stressors):
        if not isinstance(entry, dict):
            raise ValueError("service stressor %d must be a mapping" % index)
        for key in ("stressor", "severity_fraction"):
            if key not in entry:
                raise ValueError("service stressor %d is missing '%s'" % (index, key))
        name = entry["stressor"]
        if not isinstance(name, str) or name not in STRESSOR_OBJECTIVES:
            raise ValueError("unrecognised service stressor: %r" % (name,))
        if name in inventory:
            raise ValueError("service stressor declared twice: %s" % name)
        inventory[name] = _fraction(
            entry["severity_fraction"], "severity_fraction of %s" % name
        )
    return inventory


def objectives_for(stressors):
    """Return the durability objectives the declared stressors make the check serve."""
    inventory = validate_stressors(stressors)
    objectives = [STRESSOR_OBJECTIVES[name] for name in sorted(inventory)]
    if objectives:
        objectives.append(COMMON_OBJECTIVE)
    return objectives


def service_demand(stressors, policy=None):
    """Return the accumulated service demand on the coating."""
    inventory = validate_stressors(stressors)
    policy = validate_policy(policy)
    weights = policy["weights"]
    return math.fsum(weights[name] * severity for name, severity in inventory.items())


def check_is_justified(has_conductive_coating, demand, policy=None):
    """Return True when a coated coverglass carries enough service demand."""
    if not isinstance(has_conductive_coating, bool):
        raise ValueError("has_conductive_coating must be a boolean")
    policy = validate_policy(policy)
    demand = _real(demand, "demand")
    if demand < 0.0:
        raise ValueError("demand must not be negative")
    if not has_conductive_coating:
        return False
    trigger = policy["demand_trigger"]
    if math.isclose(demand, trigger, rel_tol=_REL_TOL, abs_tol=0.0):
        return True
    return demand > trigger


def grade_planned_check(plan, stressors, policy=None):
    """Return the shortfalls of a planned check against the purpose it must serve."""
    if not isinstance(plan, dict):
        raise ValueError("planned check must be a mapping")
    for key in ("after_environments", "subgroup_samples"):
        if key not in plan:
            raise ValueError("planned check is missing '%s'" % key)
    after = plan["after_environments"]
    if not isinstance(after, (list, tuple)):
        raise ValueError("after_environments must be a sequence")
    for name in after:
        if not isinstance(name, str) or name not in STRESSOR_OBJECTIVES:
            raise ValueError("unrecognised environment in the planned check: %r" % (name,))
    samples = plan["subgroup_samples"]
    if not isinstance(samples, int) or isinstance(samples, bool) or samples < 0:
        raise ValueError("subgroup_samples must be a non-negative integer")
    inventory = validate_stressors(stressors)
    policy = validate_policy(policy)

    shortfalls = []
    missed = [
        name
        for name in sorted(inventory)
        if name in LOOSENING_STRESSORS and name not in after
    ]
    for name in missed:
        shortfalls.append(
            "the check does not follow %s, so it cannot report the coating adherence "
            "that environment leaves behind" % name
        )
    if samples < policy["min_subgroup_samples"]:
        shortfalls.append(
            "the check reads %d subgroup samples against a floor of %d"
            % (samples, policy["min_subgroup_samples"])
        )
    return {
        "after_environments": sorted(set(after)),
        "subgroup_samples": samples,
        "unfollowed_environments": missed,
        "shortfalls": shortfalls,
    }


def assess_adherence_purpose(spec):
    """Run the full clause 6.4.3.9.1 purpose assessment.

    spec keys: has_conductive_coating, service_stressors; optional
    planned_check and policy.
    """
    if not isinstance(spec, dict):
        raise ValueError("spec must be a mapping")
    for key in ("has_conductive_coating", "service_stressors"):
        if key not in spec:
            raise ValueError("spec missing required key '%s'" % key)
    coated = spec["has_conductive_coating"]
    if not isinstance(coated, bool):
        raise ValueError("has_conductive_coating must be a boolean")
    policy = validate_policy(spec.get("policy"))
    inventory = validate_stressors(spec["service_stressors"])
    demand = service_demand(spec["service_stressors"], policy)
    objectives = objectives_for(spec["service_stressors"]) if coated else []
    justified = check_is_justified(coated, demand, policy)

    plan = spec.get("planned_check")
    grading = None
    findings = []
    if not justified:
        verdict = TEST_NOT_REQUIRED
        if not coated:
            findings.append(
                "the coverglass carries no conductive coating, so there is no bleed "
                "path whose durability the check could demonstrate"
            )
        else:
            findings.append(
                "the accumulated service demand of %.3f stays below the trigger of "
                "%.3f" % (demand, policy["demand_trigger"])
            )
    elif plan is None:
        verdict = CHECK_NOT_PLANNED
        findings.append(
            "the coating and its service demand of %.3f earn an adherence check, but "
            "none is planned" % demand
        )
    else:
        grading = grade_planned_check(plan, spec["service_stressors"], policy)
        findings.extend(grading["shortfalls"])
        verdict = CHECK_UNDER_SCOPE if grading["shortfalls"] else CHECK_SERVES_PURPOSE

    return {
        "verdict": verdict,
        "has_conductive_coating": coated,
        "service_demand": demand,
        "demand_trigger": policy["demand_trigger"],
        "justified": justified,
        "stressor_count": len(inventory),
        "objectives": objectives,
        "planned_check": grading,
        "findings": findings,
    }
