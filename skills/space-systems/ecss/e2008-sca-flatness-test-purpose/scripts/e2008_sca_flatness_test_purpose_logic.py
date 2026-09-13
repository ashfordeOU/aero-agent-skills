#!/usr/bin/env python3
"""Purpose of the solar cell assembly flatness measurement.

Anchor: ECSS-E-ST-20-08C clause 6.4.3.17.1 -- the flatness measurement exists
to establish how flat a completed cell assembly is before it is integrated.
The procedure below is a paraphrase into implementable steps; no standard text
is reproduced.

Why the measurement exists
--------------------------
A cell assembly leaves its build line as a stack of unlike materials that were
bonded, welded and cured at different temperatures: a thin brittle cell, a
coverglass bonded to its front, interconnects welded to its back. The stack
relaxes into a shape of its own. Nothing on the build line cares about that
shape; everything downstream does. An adhesive laydown onto a panel needs a
bond line it can hold to thickness, a hold-down or clamp bends a bowed
assembly until the coverglass carries the bending stress, thermal contact to
the facesheet is only as good as the area that actually touches, vacuum
tooling cannot seat what it cannot pull flat, and a stack height envelope on
the panel is spent by the bow before the assembly is even placed.

Two things therefore decide whether and why the measurement is applied:

    where the assembly goes    onto a rigid bonded panel, whose own surface
                               cannot take up the shape of the assembly, or
                               onto nothing that constrains it, in which case
                               a pre-integration shape has nothing to protect

    what integration demands   the declared integration steps, each scaled by
                               how sensitive it is to out-of-plane deviation,
                               accumulated into one integration demand

A planned measurement only serves the purpose when it follows every operation
that sets the shape of the stack, is taken before the assembly is integrated,
and reads enough subgroup samples to speak for the lot. A reading taken on a
bare cell before its coverglass is bonded reports the cell, not the assembly
that will be placed on the panel.
"""

import math

__all__ = [
    "STEP_OBJECTIVES",
    "SHAPE_SETTING_OPERATIONS",
    "COMMON_OBJECTIVE",
    "DEFAULT_FLATNESS_PURPOSE_POLICY",
    "MEASUREMENT_NOT_REQUIRED",
    "MEASUREMENT_NOT_PLANNED",
    "MEASUREMENT_UNDER_SCOPE",
    "MEASUREMENT_SERVES_PURPOSE",
    "validate_policy",
    "validate_integration_steps",
    "validate_operations",
    "objectives_for",
    "integration_demand",
    "measurement_is_justified",
    "grade_planned_measurement",
    "assess_flatness_purpose",
]

# Each integration step turns into the flatness objective the measurement
# demonstrates against it.
STEP_OBJECTIVES = {
    "adhesive-bonding-to-panel": "uniform-bond-line-thickness",
    "coverglass-clamp-down": "coverglass-bending-stress-limit",
    "panel-thermal-contact": "assembly-to-facesheet-contact-area",
    "vacuum-laydown-tooling": "vacuum-hold-down-seating",
    "stay-out-envelope-fit": "panel-stack-height-envelope",
    "automated-pick-and-place": "pick-and-place-nozzle-seating",
    "interconnect-stress-relief": "interconnect-loop-clearance",
}

INTEGRATION_STEPS = tuple(sorted(STEP_OBJECTIVES))

# The operations that set the shape of the stack. A measurement taken before
# any of them reports a part that no longer exists by integration.
SHAPE_SETTING_OPERATIONS = (
    "coverglass-bonding",
    "interconnect-welding",
    "cell-to-cell-stringing",
    "adhesive-cure",
)

# Every completed assembly bound for a rigid panel shares this one.
COMMON_OBJECTIVE = "pre-integration-assembly-planarity"

# A declared policy, not a physical constant: a project substitutes its own.
# weights: how much of the integration demand each step can contribute at a
# sensitivity fraction of one. trigger: the demand at which a measurement is
# earned.
DEFAULT_FLATNESS_PURPOSE_POLICY = {
    "weights": {
        "adhesive-bonding-to-panel": 1.0,
        "coverglass-clamp-down": 0.9,
        "panel-thermal-contact": 0.6,
        "vacuum-laydown-tooling": 0.7,
        "stay-out-envelope-fit": 0.5,
        "automated-pick-and-place": 0.4,
        "interconnect-stress-relief": 0.3,
    },
    "demand_trigger": 1.0,
    "min_subgroup_samples": 4,
}

MEASUREMENT_NOT_REQUIRED = "measurement-not-required"
MEASUREMENT_NOT_PLANNED = "measurement-not-planned"
MEASUREMENT_UNDER_SCOPE = "measurement-under-scope"
MEASUREMENT_SERVES_PURPOSE = "measurement-serves-purpose"

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
    """Return a validated flatness purpose policy, defaults filled in."""
    if policy is None:
        policy = {}
    if not isinstance(policy, dict):
        raise ValueError("policy must be a mapping")
    merged = {
        "weights": dict(DEFAULT_FLATNESS_PURPOSE_POLICY["weights"]),
        "demand_trigger": DEFAULT_FLATNESS_PURPOSE_POLICY["demand_trigger"],
        "min_subgroup_samples": DEFAULT_FLATNESS_PURPOSE_POLICY["min_subgroup_samples"],
    }
    weights = policy.get("weights")
    if weights is not None:
        if not isinstance(weights, dict) or not weights:
            raise ValueError("policy weights must be a non-empty mapping")
        for name, weight in weights.items():
            if name not in STEP_OBJECTIVES:
                raise ValueError("unrecognised integration step in policy weights: %s" % name)
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


def validate_integration_steps(steps):
    """Return the validated integration inventory as step -> sensitivity."""
    if not isinstance(steps, (list, tuple)):
        raise ValueError("integration steps must be a sequence of entries")
    inventory = {}
    for index, entry in enumerate(steps):
        if not isinstance(entry, dict):
            raise ValueError("integration step %d must be a mapping" % index)
        for key in ("step", "sensitivity_fraction"):
            if key not in entry:
                raise ValueError("integration step %d is missing '%s'" % (index, key))
        name = entry["step"]
        if not isinstance(name, str) or name not in STEP_OBJECTIVES:
            raise ValueError("unrecognised integration step: %r" % (name,))
        if name in inventory:
            raise ValueError("integration step declared twice: %s" % name)
        inventory[name] = _fraction(
            entry["sensitivity_fraction"], "sensitivity_fraction of %s" % name
        )
    return inventory


def validate_operations(operations):
    """Return the declared shape-setting operations, deduplicated and sorted."""
    if not isinstance(operations, (list, tuple)):
        raise ValueError("assembly operations must be a sequence")
    seen = []
    for name in operations:
        if not isinstance(name, str) or name not in SHAPE_SETTING_OPERATIONS:
            raise ValueError("unrecognised assembly operation: %r" % (name,))
        if name in seen:
            raise ValueError("assembly operation declared twice: %s" % name)
        seen.append(name)
    return sorted(seen)


def objectives_for(steps):
    """Return the flatness objectives the declared integration steps demand."""
    inventory = validate_integration_steps(steps)
    objectives = [STEP_OBJECTIVES[name] for name in sorted(inventory)]
    if objectives:
        objectives.append(COMMON_OBJECTIVE)
    return objectives


def integration_demand(steps, policy=None):
    """Return the accumulated integration demand on assembly flatness."""
    inventory = validate_integration_steps(steps)
    policy = validate_policy(policy)
    weights = policy["weights"]
    return math.fsum(weights[name] * value for name, value in inventory.items())


def measurement_is_justified(integrated_onto_rigid_panel, demand, policy=None):
    """Return True when a rigidly integrated assembly carries enough demand."""
    if not isinstance(integrated_onto_rigid_panel, bool):
        raise ValueError("integrated_onto_rigid_panel must be a boolean")
    policy = validate_policy(policy)
    demand = _real(demand, "demand")
    if demand < 0.0:
        raise ValueError("demand must not be negative")
    if not integrated_onto_rigid_panel:
        return False
    trigger = policy["demand_trigger"]
    if math.isclose(demand, trigger, rel_tol=_REL_TOL, abs_tol=0.0):
        return True
    return demand > trigger


def grade_planned_measurement(plan, operations, policy=None):
    """Return the shortfalls of a planned run against the purpose it serves."""
    if not isinstance(plan, dict):
        raise ValueError("planned measurement must be a mapping")
    for key in ("after_operations", "before_integration", "subgroup_samples"):
        if key not in plan:
            raise ValueError("planned measurement is missing '%s'" % key)
    after = plan["after_operations"]
    if not isinstance(after, (list, tuple)):
        raise ValueError("after_operations must be a sequence")
    for name in after:
        if not isinstance(name, str) or name not in SHAPE_SETTING_OPERATIONS:
            raise ValueError("unrecognised operation in the planned run: %r" % (name,))
    before = plan["before_integration"]
    if not isinstance(before, bool):
        raise ValueError("before_integration must be a boolean")
    samples = plan["subgroup_samples"]
    if not isinstance(samples, int) or isinstance(samples, bool) or samples < 0:
        raise ValueError("subgroup_samples must be a non-negative integer")
    declared = validate_operations(operations)
    policy = validate_policy(policy)

    shortfalls = []
    missed = [name for name in declared if name not in after]
    for name in missed:
        shortfalls.append(
            "the run does not follow %s, so it reports a shape that operation "
            "still changes" % name
        )
    if not before:
        shortfalls.append(
            "the run is taken after integration, so it reports the shape the panel "
            "imposed rather than the shape the assembly brought"
        )
    if samples < policy["min_subgroup_samples"]:
        shortfalls.append(
            "the run reads %d subgroup samples against a floor of %d"
            % (samples, policy["min_subgroup_samples"])
        )
    return {
        "after_operations": sorted(set(after)),
        "before_integration": before,
        "subgroup_samples": samples,
        "unfollowed_operations": missed,
        "shortfalls": shortfalls,
    }


def assess_flatness_purpose(spec):
    """Run the full clause 6.4.3.17.1 purpose assessment.

    spec keys: integrated_onto_rigid_panel, integration_steps,
    assembly_operations; optional planned_measurement and policy.
    """
    if not isinstance(spec, dict):
        raise ValueError("spec must be a mapping")
    for key in ("integrated_onto_rigid_panel", "integration_steps", "assembly_operations"):
        if key not in spec:
            raise ValueError("spec missing required key '%s'" % key)
    rigid = spec["integrated_onto_rigid_panel"]
    if not isinstance(rigid, bool):
        raise ValueError("integrated_onto_rigid_panel must be a boolean")
    policy = validate_policy(spec.get("policy"))
    inventory = validate_integration_steps(spec["integration_steps"])
    operations = validate_operations(spec["assembly_operations"])
    demand = integration_demand(spec["integration_steps"], policy)
    objectives = objectives_for(spec["integration_steps"]) if rigid else []
    justified = measurement_is_justified(rigid, demand, policy)

    plan = spec.get("planned_measurement")
    grading = None
    findings = []
    if not justified:
        verdict = MEASUREMENT_NOT_REQUIRED
        if not rigid:
            findings.append(
                "the assembly is not integrated onto a rigid panel, so a shape "
                "measured before integration protects nothing downstream"
            )
        else:
            findings.append(
                "the accumulated integration demand of %.3f stays below the trigger "
                "of %.3f" % (demand, policy["demand_trigger"])
            )
    elif plan is None:
        verdict = MEASUREMENT_NOT_PLANNED
        findings.append(
            "the integration route and its demand of %.3f earn a flatness "
            "measurement, but none is planned" % demand
        )
    else:
        grading = grade_planned_measurement(plan, spec["assembly_operations"], policy)
        findings.extend(grading["shortfalls"])
        verdict = MEASUREMENT_UNDER_SCOPE if grading["shortfalls"] else MEASUREMENT_SERVES_PURPOSE

    return {
        "verdict": verdict,
        "integrated_onto_rigid_panel": rigid,
        "integration_demand": demand,
        "demand_trigger": policy["demand_trigger"],
        "justified": justified,
        "step_count": len(inventory),
        "shape_setting_operations": operations,
        "objectives": objectives,
        "planned_measurement": grading,
        "findings": findings,
    }
