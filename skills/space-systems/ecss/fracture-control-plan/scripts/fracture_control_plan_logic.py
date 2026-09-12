"""
Fracture Control Plan logic per ECSS-E-ST-32C DRD Annex F, clause 5.2.

Deterministic offline module — stdlib only, no external dependencies.
All functions return plain dicts or raise ValueError for invalid input.
"""

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

# Fracture criticality designations
FC = "fracture_critical"
NFC = "non_fracture_critical"

# Failure consequence levels (descending severity)
CONSEQUENCE_CATASTROPHIC = "catastrophic"
CONSEQUENCE_CRITICAL = "critical"
CONSEQUENCE_MARGINAL = "marginal"
CONSEQUENCE_NEGLIGIBLE = "negligible"

VALID_CONSEQUENCES = frozenset({
    CONSEQUENCE_CATASTROPHIC,
    CONSEQUENCE_CRITICAL,
    CONSEQUENCE_MARGINAL,
    CONSEQUENCE_NEGLIGIBLE,
})

# Consequence levels that require fracture-critical designation
FC_REQUIRED_CONSEQUENCES = frozenset({CONSEQUENCE_CATASTROPHIC, CONSEQUENCE_CRITICAL})

# NDE method options recognized by this plan framework
NDE_METHODS = frozenset({
    "radiography",
    "ultrasonic",
    "dye_penetrant",
    "magnetic_particle",
    "eddy_current",
})

# Life management approach options
APPROACH_SAFE_LIFE = "safe_life"
APPROACH_FAIL_SAFE = "fail_safe"
APPROACH_DAMAGE_TOLERANT = "damage_tolerant"

VALID_LIFE_APPROACHES = frozenset({
    APPROACH_SAFE_LIFE,
    APPROACH_FAIL_SAFE,
    APPROACH_DAMAGE_TOLERANT,
})

# Verification methods accepted for FC parts
VERIFICATION_ANALYSIS = "analysis"
VERIFICATION_TEST = "test"
VERIFICATION_ANALYSIS_AND_TEST = "analysis_and_test"

VALID_VERIFICATION_METHODS = frozenset({
    VERIFICATION_ANALYSIS,
    VERIFICATION_TEST,
    VERIFICATION_ANALYSIS_AND_TEST,
})

# Required sections in a conforming Fracture Control Plan document
REQUIRED_PLAN_SECTIONS = frozenset({
    "part_inventory",
    "fracture_criticality_rationale",
    "nde_requirements",
    "life_approach",
    "verification_methods",
    "approval_authority",
    "update_triggers",
})

# Change types that mandatorily trigger a plan update per DRD Annex F
MANDATORY_UPDATE_TRIGGERS = frozenset({
    "design_change",
    "material_change",
    "load_increase",
    "new_fc_finding",
    "inspection_finding",
})


# ---------------------------------------------------------------------------
# Part categorization
# ---------------------------------------------------------------------------

def categorize_part(part_id: str, failure_consequence: str) -> dict:
    """
    Determine fracture criticality of a part based on its failure consequence.

    Returns a dict with keys: part_id, failure_consequence, designation.
    Raises ValueError for unrecognized consequence levels or empty part_id.
    """
    if not part_id or not str(part_id).strip():
        raise ValueError("part_id must be a non-empty string")
    if failure_consequence not in VALID_CONSEQUENCES:
        raise ValueError(
            f"Unrecognized failure consequence '{failure_consequence}'. "
            f"Valid values: {sorted(VALID_CONSEQUENCES)}"
        )
    designation = FC if failure_consequence in FC_REQUIRED_CONSEQUENCES else NFC
    return {
        "part_id": part_id,
        "failure_consequence": failure_consequence,
        "designation": designation,
    }


# ---------------------------------------------------------------------------
# FC item completeness check
# ---------------------------------------------------------------------------

def check_fc_item_completeness(item: dict) -> dict:
    """
    Verify that a fracture-critical item record carries all required fields.

    Required fields for an FC item:
      - part_id (non-empty str)
      - nde_method (one of NDE_METHODS)
      - nde_detection_limit_mm (float > 0)
      - life_approach (one of VALID_LIFE_APPROACHES)
      - verification_method (one of VALID_VERIFICATION_METHODS)
      - design_life_cycles (int or float > 0)

    Returns {"pass": True, "findings": []} on success, or
            {"pass": False, "findings": [<str>]} listing every deficiency.
    """
    findings = []

    part_id = item.get("part_id", "")
    if not part_id or not str(part_id).strip():
        findings.append("missing or empty part_id")

    nde_method = item.get("nde_method")
    if nde_method is None:
        findings.append("missing nde_method")
    elif nde_method not in NDE_METHODS:
        findings.append(f"unrecognized nde_method '{nde_method}'")

    detection_limit = item.get("nde_detection_limit_mm")
    if detection_limit is None:
        findings.append("missing nde_detection_limit_mm")
    else:
        try:
            if float(detection_limit) <= 0:
                findings.append("nde_detection_limit_mm must be > 0")
        except (TypeError, ValueError):
            findings.append("nde_detection_limit_mm must be a positive number")

    life_approach = item.get("life_approach")
    if life_approach is None:
        findings.append("missing life_approach")
    elif life_approach not in VALID_LIFE_APPROACHES:
        findings.append(f"unrecognized life_approach '{life_approach}'")

    verification_method = item.get("verification_method")
    if verification_method is None:
        findings.append("missing verification_method")
    elif verification_method not in VALID_VERIFICATION_METHODS:
        findings.append(f"unrecognized verification_method '{verification_method}'")

    design_life = item.get("design_life_cycles")
    if design_life is None:
        findings.append("missing design_life_cycles")
    else:
        try:
            if float(design_life) <= 0:
                findings.append("design_life_cycles must be > 0")
        except (TypeError, ValueError):
            findings.append("design_life_cycles must be a positive number")

    return {"pass": len(findings) == 0, "findings": findings}


# ---------------------------------------------------------------------------
# Plan section completeness check
# ---------------------------------------------------------------------------

def check_plan_sections(present_sections: list) -> dict:
    """
    Verify that a Fracture Control Plan document contains all required sections.

    present_sections: list of section identifier strings present in the plan.

    Returns {"pass": True, "missing": []} if all required sections are present,
            {"pass": False, "missing": [<section names>]} otherwise.
    """
    present_set = set(present_sections)
    missing = sorted(REQUIRED_PLAN_SECTIONS - present_set)
    return {"pass": len(missing) == 0, "missing": missing}


# ---------------------------------------------------------------------------
# Plan approval check
# ---------------------------------------------------------------------------

def check_plan_approval(approval_record: dict) -> dict:
    """
    Verify that a Fracture Control Plan has been approved at the required levels.

    approval_record must contain:
      - project_engineer_signed (bool)
      - fracture_control_authority_signed (bool)
      - customer_accepted (bool)

    Returns {"pass": True, "unsigned_roles": []} if all three are True,
            {"pass": False, "unsigned_roles": [<role names>]} otherwise.
    Raises ValueError if any required key is absent from approval_record.
    """
    required_keys = {
        "project_engineer_signed",
        "fracture_control_authority_signed",
        "customer_accepted",
    }
    missing_keys = required_keys - set(approval_record.keys())
    if missing_keys:
        raise ValueError(f"approval_record missing keys: {sorted(missing_keys)}")

    role_map = {
        "project_engineer_signed": "project_engineer",
        "fracture_control_authority_signed": "fracture_control_authority",
        "customer_accepted": "customer",
    }
    unsigned = [role for key, role in role_map.items() if not approval_record[key]]
    return {"pass": len(unsigned) == 0, "unsigned_roles": sorted(unsigned)}


# ---------------------------------------------------------------------------
# Update trigger check
# ---------------------------------------------------------------------------

def is_update_required(change_type: str) -> dict:
    """
    Determine whether a given change type mandatorily triggers a plan update.

    Returns {"update_required": bool, "change_type": str, "reason": str}.
    """
    required = change_type in MANDATORY_UPDATE_TRIGGERS
    if required:
        reason = (
            f"Change type '{change_type}' is a mandatory FCP update trigger "
            "per ECSS-E-ST-32C DRD Annex F."
        )
    else:
        reason = (
            f"Change type '{change_type}' does not match any mandatory FCP "
            "update trigger under ECSS-E-ST-32C DRD Annex F."
        )
    return {
        "update_required": required,
        "change_type": change_type,
        "reason": reason,
    }


# ---------------------------------------------------------------------------
# Full plan validation
# ---------------------------------------------------------------------------

def validate_fracture_control_plan(plan: dict) -> dict:
    """
    Run all FCP checks against a plan dict and return an aggregated result.

    Expected plan structure:
      {
        "sections":  [<section name strings>],
        "approval":  {<approval_record dict>},
        "fc_items":  [<FC item dicts>],
      }

    Returns:
      {
        "overall_pass":   bool,
        "section_check":  <result of check_plan_sections>,
        "approval_check": <result of check_plan_approval>,
        "fc_item_checks": [<result of check_fc_item_completeness per item>],
      }
    Raises ValueError on malformed input.
    """
    if not isinstance(plan, dict):
        raise ValueError("plan must be a dict")

    sections = plan.get("sections", [])
    approval = plan.get("approval", {})
    fc_items = plan.get("fc_items", [])

    section_result = check_plan_sections(sections)
    approval_result = check_plan_approval(approval)

    item_results = [check_fc_item_completeness(item) for item in fc_items]

    all_items_pass = all(r["pass"] for r in item_results) if item_results else True
    overall = section_result["pass"] and approval_result["pass"] and all_items_pass

    return {
        "overall_pass": overall,
        "section_check": section_result,
        "approval_check": approval_result,
        "fc_item_checks": item_results,
    }
