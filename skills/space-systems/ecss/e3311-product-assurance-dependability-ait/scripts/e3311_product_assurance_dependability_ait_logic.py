"""Dependability and AIT control for explosive subsystems.

Anchor: ECSS-E-ST-33-11C Rev.1 clause 4.17 (product assurance: dependability
requirements and assembly, integration and test controls applied to explosive
subsystems). Paraphrased into an implementable procedure; no standard text is
reproduced.

Procedure implemented here
--------------------------
1. Model the explosive train as ordered stages, each stage holding one or more
   parallel elements, and compute the reliability the architecture delivers.
2. Apportion a system reliability target across the stages so a stage owner has
   a number to design to.
3. Find the stages that are single-point failures and check each of them is on
   the declared critical-items list.
4. Validate the assembly, integration and test flow: the live device goes in as
   late as the flow allows, nothing that needs an inert vehicle happens after
   it, every powered operation afterwards runs with the inhibit fitted, and the
   installation itself happens in an electrostatically controlled area.
"""

import math

__all__ = [
    "RELIABILITY_TOLERANCE",
    "MAX_STAGES",
    "validate_reliability",
    "validate_stage",
    "stage_reliability",
    "train_reliability",
    "apportion_stage_target",
    "single_point_stages",
    "critical_items_findings",
    "validate_ait_flow",
    "assess_product_assurance",
]

# Reliabilities are multiplied and rooted, so an exactly-on-target architecture
# can land a few ULP below the target. Absorb it here, not in the target.
RELIABILITY_TOLERANCE = 1e-9

# A train longer than this is a modelling error rather than a design.
MAX_STAGES = 200


def validate_reliability(label, value):
    """Return value as a reliability in (0, 1]."""
    if not isinstance(value, (int, float)) or isinstance(value, bool):
        raise ValueError("%s must be a real number, got %r" % (label, value))
    number = float(value)
    if not math.isfinite(number):
        raise ValueError("%s must be finite, got %r" % (label, value))
    if number <= 0.0 or number > 1.0:
        raise ValueError("%s must lie in (0, 1], got %r" % (label, value))
    return number


def validate_stage(stage, index=0):
    """Return a normalised stage mapping."""
    if not isinstance(stage, dict):
        raise ValueError("stages[%d] must be a mapping" % index)
    for key in ("stage_id", "elements", "criticality"):
        if key not in stage:
            raise ValueError("stages[%d] missing '%s'" % (index, key))
    stage_id = stage["stage_id"]
    if not isinstance(stage_id, str) or not stage_id.strip():
        raise ValueError("stages[%d]['stage_id'] must be a non-empty string" % index)
    elements = stage["elements"]
    if not isinstance(elements, (list, tuple)) or not elements:
        raise ValueError("stages[%d]['elements'] must be a non-empty sequence" % index)
    values = [
        validate_reliability("stages[%d]['elements'][%d]" % (index, k), element)
        for k, element in enumerate(elements)
    ]
    criticality = stage["criticality"]
    if not isinstance(criticality, int) or isinstance(criticality, bool):
        raise ValueError("stages[%d]['criticality'] must be an integer" % index)
    if criticality < 1 or criticality > 4:
        raise ValueError(
            "stages[%d]['criticality'] must lie between 1 and 4, got %d" % (index, criticality)
        )
    return {
        "stage_id": stage_id.strip(),
        "elements": values,
        "criticality": criticality,
    }


def stage_reliability(elements):
    """Return the reliability of one stage of parallel elements."""
    if not isinstance(elements, (list, tuple)) or not elements:
        raise ValueError("elements must be a non-empty sequence of reliabilities")
    failure = 1.0
    for index, element in enumerate(elements):
        failure *= 1.0 - validate_reliability("elements[%d]" % index, element)
    value = 1.0 - failure
    if value > 1.0:
        return 1.0
    return value


def train_reliability(stages):
    """Return the reliability of an explosive train of series stages."""
    if not isinstance(stages, (list, tuple)) or not stages:
        raise ValueError("stages must be a non-empty sequence of stage mappings")
    if len(stages) > MAX_STAGES:
        raise ValueError("train of %d stages exceeds the %d modelled" % (len(stages), MAX_STAGES))
    normalized = [validate_stage(stage, index) for index, stage in enumerate(stages)]
    seen = set()
    for stage in normalized:
        if stage["stage_id"] in seen:
            raise ValueError("duplicate stage_id %r" % stage["stage_id"])
        seen.add(stage["stage_id"])
    total = 1.0
    breakdown = []
    for stage in normalized:
        value = stage_reliability(stage["elements"])
        total *= value
        breakdown.append(
            {
                "stage_id": stage["stage_id"],
                "element_count": len(stage["elements"]),
                "reliability": value,
                "criticality": stage["criticality"],
            }
        )
    return {
        "stages": breakdown,
        "reliability": total,
    }


def apportion_stage_target(system_target, stage_count):
    """Return the equal-share reliability each stage of a series train must reach."""
    target = validate_reliability("system_target", system_target)
    if not isinstance(stage_count, int) or isinstance(stage_count, bool):
        raise ValueError("stage_count must be an integer, got %r" % (stage_count,))
    if stage_count < 1:
        raise ValueError("stage_count must be at least 1, got %d" % stage_count)
    if stage_count > MAX_STAGES:
        raise ValueError("stage_count %d exceeds the %d modelled" % (stage_count, MAX_STAGES))
    return target ** (1.0 / stage_count)


def single_point_stages(stages):
    """Return the stages whose failure alone loses the function."""
    if not isinstance(stages, (list, tuple)) or not stages:
        raise ValueError("stages must be a non-empty sequence of stage mappings")
    found = []
    for index, stage in enumerate(stages):
        normalized = validate_stage(stage, index)
        if len(normalized["elements"]) == 1:
            found.append(
                {
                    "stage_id": normalized["stage_id"],
                    "criticality": normalized["criticality"],
                }
            )
    return found


def critical_items_findings(stages, declared_critical_items):
    """Report single-point stages that the critical-items list does not carry."""
    if not isinstance(declared_critical_items, (list, tuple, set, frozenset)):
        raise ValueError("declared_critical_items must be a sequence")
    declared = set()
    for item in declared_critical_items:
        if not isinstance(item, str) or not item.strip():
            raise ValueError("each declared critical item must be a non-empty string")
        declared.add(item.strip())
    singles = single_point_stages(stages)
    missing = []
    findings = []
    for stage in singles:
        if stage["criticality"] <= 2 and stage["stage_id"] not in declared:
            missing.append(stage["stage_id"])
            findings.append(
                "stage %s is a single-point failure at criticality %d and is not on the "
                "critical-items list" % (stage["stage_id"], stage["criticality"])
            )
    return {
        "single_point_stages": [stage["stage_id"] for stage in singles],
        "missing_from_list": missing,
        "complete": not findings,
        "findings": findings,
    }


def validate_ait_flow(operations):
    """Validate the assembly, integration and test flow around the live device."""
    if not isinstance(operations, (list, tuple)) or not operations:
        raise ValueError("operations must be a non-empty sequence of mappings")
    normalized = []
    seen = set()
    for index, operation in enumerate(operations):
        if not isinstance(operation, dict):
            raise ValueError("operations[%d] must be a mapping" % index)
        for key in ("operation_id", "installs_live_device", "requires_inert_vehicle",
                    "powered", "inhibit_fitted", "esd_controlled_area"):
            if key not in operation:
                raise ValueError("operations[%d] missing '%s'" % (index, key))
        operation_id = operation["operation_id"]
        if not isinstance(operation_id, str) or not operation_id.strip():
            raise ValueError("operations[%d]['operation_id'] must be a non-empty string" % index)
        operation_id = operation_id.strip()
        if operation_id in seen:
            raise ValueError("duplicate operation_id %r" % operation_id)
        seen.add(operation_id)
        entry = {"operation_id": operation_id}
        for key in ("installs_live_device", "requires_inert_vehicle", "powered",
                    "inhibit_fitted", "esd_controlled_area"):
            if not isinstance(operation[key], bool):
                raise ValueError("operations[%d]['%s'] must be a boolean" % (index, key))
            entry[key] = operation[key]
        normalized.append(entry)
    install_positions = [
        position for position, entry in enumerate(normalized) if entry["installs_live_device"]
    ]
    findings = []
    if not install_positions:
        findings.append("flow never installs the live device")
        return {
            "operations": normalized,
            "install_position": None,
            "operations_after_install": 0,
            "valid": False,
            "findings": findings,
        }
    if len(install_positions) > 1:
        findings.append(
            "flow installs the live device %d times" % len(install_positions)
        )
    position = install_positions[0]
    install = normalized[position]
    if not install["esd_controlled_area"]:
        findings.append(
            "live device installed in operation %s outside an electrostatically "
            "controlled area" % install["operation_id"]
        )
    after = normalized[position + 1:]
    for entry in after:
        if entry["requires_inert_vehicle"]:
            findings.append(
                "operation %s needs an inert vehicle and is scheduled after installation"
                % entry["operation_id"]
            )
        if entry["powered"] and not entry["inhibit_fitted"]:
            findings.append(
                "operation %s powers the vehicle after installation without the inhibit fitted"
                % entry["operation_id"]
            )
    return {
        "operations": normalized,
        "install_position": position,
        "operations_after_install": len(after),
        "valid": not findings,
        "findings": findings,
    }


def assess_product_assurance(spec):
    """Run the full clause 4.17 dependability and AIT assessment.

    spec keys: stages, system_target, optional critical_items and ait_flow.
    """
    if not isinstance(spec, dict):
        raise ValueError("spec must be a mapping")
    for key in ("stages", "system_target"):
        if key not in spec:
            raise ValueError("spec missing required key '%s'" % key)
    train = train_reliability(spec["stages"])
    target = validate_reliability("system_target", spec["system_target"])
    achieved = train["reliability"]
    shortfall = achieved < target and not math.isclose(
        achieved, target, rel_tol=RELIABILITY_TOLERANCE, abs_tol=0.0
    )
    findings = []
    if shortfall:
        findings.append(
            "train reliability %.9g falls short of the %.9g target" % (achieved, target)
        )
    stage_target = apportion_stage_target(target, len(train["stages"]))
    weak = []
    for stage in train["stages"]:
        below = stage["reliability"] < stage_target and not math.isclose(
            stage["reliability"], stage_target, rel_tol=RELIABILITY_TOLERANCE, abs_tol=0.0
        )
        if below:
            weak.append(stage["stage_id"])
    critical = critical_items_findings(spec["stages"], spec.get("critical_items") or [])
    findings.extend(critical["findings"])
    flow = None
    if "ait_flow" in spec:
        flow = validate_ait_flow(spec["ait_flow"])
        findings.extend(flow["findings"])
    return {
        "train": train,
        "achieved_reliability": achieved,
        "system_target": target,
        "stage_target": stage_target,
        "stages_below_apportionment": weak,
        "critical_items": critical,
        "ait_flow": flow,
        "acceptable": not findings,
        "findings": findings,
    }
