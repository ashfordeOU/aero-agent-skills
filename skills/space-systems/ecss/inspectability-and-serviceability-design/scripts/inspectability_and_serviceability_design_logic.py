#!/usr/bin/env python3
"""ECSS-E-ST-32C clauses 4.5.1-4.5.4 inspectability and serviceability
design assessment (paraphrase, not copy).

Common-knowledge summary (standards-map.yaml, ecss: gated false): the
structural general requirements standard's serviceability clauses cover
four design properties — inspectability (access method and clearance for
critical structural joints), interchangeability (fully defined interface
tolerances for replaceable parts, no manual adjustment), maintainability
(access clearance, tooling, and procedure defined for each planned
maintenance action), and dismountability (joint cycle rating meets the
programme requirement; galling-risk material pairs carry an anti-galling
treatment). This module implements each check with explicit error paths
and deterministic violation lists.
"""

INSPECTION_METHODS = frozenset({"visual", "borescope", "ultrasonic_probe", "eddy_current"})

# Minimum access clearance (mm) by inspection method.
MIN_INSPECTION_CLEARANCE_MM = {
    "visual": 50.0,
    "borescope": 15.0,
    "ultrasonic_probe": 5.0,
    "eddy_current": 5.0,
}

JOINT_CRITICALITIES = frozenset({"primary", "secondary", "non_structural"})

MAINTENANCE_ACTION_TYPES = frozenset(
    {"inspection", "replacement", "repair", "lubrication", "adjustment"}
)

# Minimum access clearance (mm) by maintenance action type.
MIN_MAINTENANCE_CLEARANCE_MM = {
    "inspection": 50.0,
    "replacement": 100.0,
    "repair": 80.0,
    "lubrication": 30.0,
    "adjustment": 50.0,
}

# Sorted material-pair tuples with known galling risk under repeated
# disassembly (without an anti-galling treatment).
GALLING_RISK_MATERIAL_PAIRS = frozenset(
    {
        ("aluminum", "aluminum"),
        ("stainless_steel", "stainless_steel"),
        ("titanium", "titanium"),
        ("steel", "steel"),
        ("inconel", "stainless_steel"),
    }
)


def categorize_access_method(method):
    """Access category for an inspection method: 'direct' for visual
    (unobstructed naked-eye or camera), 'tool_aided' for all other
    recognised methods. Raises ValueError for an unrecognized method."""
    if method not in INSPECTION_METHODS:
        raise ValueError(
            "unrecognized inspection method %r under "
            "E-ST-32C clause 4.5.1" % (method,)
        )
    if method == "visual":
        return "direct"
    return "tool_aided"


def check_inspectability(joint_id, criticality, inspection_method, clearance_mm):
    """Inspectability violation list for one structural joint.

    joint_id: str identifier.
    criticality: 'primary' | 'secondary' | 'non_structural'.
    inspection_method: str in INSPECTION_METHODS, or None if no access
      path exists.
    clearance_mm: float, available access clearance in mm (>= 0).
    Returns a list of violation dicts (empty if compliant). Non-structural
    joints have no requirement and always return []. Raises ValueError for
    an unrecognized criticality or negative clearance.
    """
    if criticality not in JOINT_CRITICALITIES:
        raise ValueError(
            "unrecognized joint criticality %r under "
            "E-ST-32C clause 4.5.1" % (criticality,)
        )
    if clearance_mm < 0:
        raise ValueError("clearance_mm must be >= 0")

    if criticality == "non_structural":
        return []

    if inspection_method is None:
        return [
            {
                "issue": "no_inspection_access",
                "joint": joint_id,
                "criticality": criticality,
            }
        ]

    if inspection_method not in INSPECTION_METHODS:
        raise ValueError(
            "unrecognized inspection method %r" % (inspection_method,)
        )

    min_clearance = MIN_INSPECTION_CLEARANCE_MM[inspection_method]
    if clearance_mm < min_clearance:
        return [
            {
                "issue": "insufficient_inspection_clearance",
                "joint": joint_id,
                "inspection_method": inspection_method,
                "clearance_mm": clearance_mm,
                "required_mm": min_clearance,
            }
        ]
    return []


def check_interchangeability(part_id, replaceable, tolerance_defined, adjustment_required):
    """Interchangeability violation list for one component.

    part_id: str identifier.
    replaceable: bool — True if the part is designed for in-service
      replacement.
    tolerance_defined: bool — True if interface tolerances are fully
      defined in the engineering drawing set.
    adjustment_required: bool — True if manual fitting, shimming, or
      custom adjustment is required for installation.
    Returns a list of violation dicts. Non-replaceable parts return [].
    """
    if not replaceable:
        return []

    violations = []
    if not tolerance_defined:
        violations.append(
            {
                "issue": "interface_tolerances_not_defined",
                "part": part_id,
            }
        )
    if adjustment_required:
        violations.append(
            {
                "issue": "manual_adjustment_required",
                "part": part_id,
            }
        )
    return violations


def check_maintainability(
    action_id, action_type, access_clearance_mm, tooling_defined, procedure_defined
):
    """Maintainability violation list for one planned maintenance action.

    action_id: str identifier.
    action_type: str in MAINTENANCE_ACTION_TYPES.
    access_clearance_mm: float, available clearance for the action (>= 0).
    tooling_defined: bool — True if required tooling is documented.
    procedure_defined: bool — True if a maintenance procedure document
      exists and is referenced.
    Returns a list of violation dicts. Raises ValueError for an unrecognized
    action_type or negative clearance.
    """
    if action_type not in MAINTENANCE_ACTION_TYPES:
        raise ValueError(
            "unrecognized maintenance action type %r under "
            "E-ST-32C clause 4.5.3" % (action_type,)
        )
    if access_clearance_mm < 0:
        raise ValueError("access_clearance_mm must be >= 0")

    violations = []
    min_clearance = MIN_MAINTENANCE_CLEARANCE_MM[action_type]
    if access_clearance_mm < min_clearance:
        violations.append(
            {
                "issue": "insufficient_maintenance_clearance",
                "action": action_id,
                "action_type": action_type,
                "clearance_mm": access_clearance_mm,
                "required_mm": min_clearance,
            }
        )
    if not tooling_defined:
        violations.append(
            {
                "issue": "tooling_not_defined",
                "action": action_id,
            }
        )
    if not procedure_defined:
        violations.append(
            {
                "issue": "procedure_not_defined",
                "action": action_id,
            }
        )
    return violations


def is_galling_risk_pair(material_a, material_b):
    """True if the material combination has known galling risk under
    repeated disassembly without an anti-galling treatment. Comparison
    is case-insensitive; order of arguments does not matter."""
    pair = tuple(sorted([material_a.lower(), material_b.lower()]))
    return pair in GALLING_RISK_MATERIAL_PAIRS


def check_dismountability(
    joint_id, design_cycles, required_cycles, material_a, material_b, anti_galling_treatment
):
    """Dismountability violation list for one joint intended for repeated
    disassembly.

    joint_id: str identifier.
    design_cycles: int, assembly-disassembly cycles the joint is rated for.
    required_cycles: int, cycles required by the programme.
    material_a, material_b: str, fastener and mating-part materials.
    anti_galling_treatment: str or None — treatment name (e.g.
      'silver_plating', 'dry_film_lubricant'); None means no treatment
      is specified.
    Returns a list of violation dicts. Raises ValueError for negative
    cycle counts.
    """
    if design_cycles < 0:
        raise ValueError("design_cycles must be >= 0")
    if required_cycles < 0:
        raise ValueError("required_cycles must be >= 0")

    violations = []
    if design_cycles < required_cycles:
        violations.append(
            {
                "issue": "insufficient_dismount_cycles",
                "joint": joint_id,
                "design_cycles": design_cycles,
                "required_cycles": required_cycles,
            }
        )
    if is_galling_risk_pair(material_a, material_b) and not anti_galling_treatment:
        violations.append(
            {
                "issue": "missing_anti_galling_treatment",
                "joint": joint_id,
                "material_a": material_a,
                "material_b": material_b,
            }
        )
    return violations


def serviceability_review(item):
    """Full ECSS-E-ST-32C clauses 4.5.1-4.5.4 serviceability review for
    one structural item.

    item: {
        "item_id": str,
        "criticality": str,               # for inspectability
        "inspection_method": str | None,
        "inspection_clearance_mm": float,
        "replaceable": bool,
        "tolerance_defined": bool,
        "adjustment_required": bool,
        "maintenance_actions": [           # list, may be empty
            {
                "action_id": str,
                "action_type": str,
                "access_clearance_mm": float,
                "tooling_defined": bool,
                "procedure_defined": bool,
            }
        ],
        "dismount_joints": [               # list, may be empty
            {
                "joint_id": str,
                "design_cycles": int,
                "required_cycles": int,
                "material_a": str,
                "material_b": str,
                "anti_galling_treatment": str | None,
            }
        ],
    }
    Returns {
        "inspectability": [...],
        "interchangeability": [...],
        "maintainability": [...],
        "dismountability": [...],
    }, each a violation list. Raises ValueError on invalid inputs.
    Does not mutate the input dict.
    """
    item_id = item["item_id"]

    inspectability_violations = check_inspectability(
        item_id,
        item["criticality"],
        item.get("inspection_method"),
        item.get("inspection_clearance_mm", 0.0),
    )

    interchangeability_violations = check_interchangeability(
        item_id,
        item.get("replaceable", False),
        item.get("tolerance_defined", False),
        item.get("adjustment_required", False),
    )

    maintainability_violations = []
    for action in item.get("maintenance_actions", []):
        maintainability_violations.extend(
            check_maintainability(
                action["action_id"],
                action["action_type"],
                action["access_clearance_mm"],
                action.get("tooling_defined", False),
                action.get("procedure_defined", False),
            )
        )

    dismountability_violations = []
    for joint in item.get("dismount_joints", []):
        dismountability_violations.extend(
            check_dismountability(
                joint["joint_id"],
                joint["design_cycles"],
                joint["required_cycles"],
                joint["material_a"],
                joint["material_b"],
                joint.get("anti_galling_treatment"),
            )
        )

    return {
        "inspectability": inspectability_violations,
        "interchangeability": interchangeability_violations,
        "maintainability": maintainability_violations,
        "dismountability": dismountability_violations,
    }


def is_serviceability_compliant(review):
    """True when all four categories in a serviceability_review result are
    empty — the item satisfies ECSS-E-ST-32C clauses 4.5.1-4.5.4."""
    return all(len(violations) == 0 for violations in review.values())
