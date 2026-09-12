"""
PFCI / FCI / FLLI list management logic — ECSS-E-ST-32C clause 6.4.2.

Implements deterministic, offline checks for:
  - Item categorization (exempt / pfci / fci / flli)
  - PFCIL / FCIL / FLLIL compilation
  - Per-item documentation requirements
  - List-level configuration control requirements
"""

SAFE_LIFE_RATIO_THRESHOLD = 4.0

REQUIRED_DOCS = {
    "pfci": frozenset({
        "pfci_screening_record",
        "fracture_sensitivity_justification",
    }),
    "fci": frozenset({
        "pfci_screening_record",
        "fracture_sensitivity_justification",
        "fracture_control_analysis",
        "initial_flaw_assumption",
        "inspection_plan",
    }),
    "flli": frozenset({
        "pfci_screening_record",
        "fracture_sensitivity_justification",
        "fracture_control_analysis",
        "initial_flaw_assumption",
        "inspection_plan",
        "life_limit_calculation",
        "replacement_or_retirement_plan",
    }),
}

VALID_COMPLIANCE_METHODS = frozenset({"analysis", "proof_test"})
VALID_FAILURE_CONSEQUENCES = frozenset({"catastrophic", "critical", "non-critical"})


def categorize_item(item):
    """
    Return the fracture control category for a structural item dict.

    Required item keys:
        fracture_sensitive (bool)
        failure_consequence (str): "catastrophic", "critical", or "non-critical"
        compliance_method (str or None): "analysis", "proof_test", or None
        safe_life_ratio (float or None): required when compliance_method is set
        has_life_limit (bool)
        life_limit_cycles (int or None)

    Returns one of: "exempt", "pfci", "fci", "flli"
    Raises TypeError if item is not a dict.
    Raises ValueError for missing or invalid required fields.
    """
    if not isinstance(item, dict):
        raise TypeError("item must be a dict")

    if "fracture_sensitive" not in item:
        raise ValueError("item missing required key: fracture_sensitive")
    fracture_sensitive = item["fracture_sensitive"]

    if "failure_consequence" not in item:
        raise ValueError("item missing required key: failure_consequence")
    failure_consequence = item["failure_consequence"]

    if failure_consequence not in VALID_FAILURE_CONSEQUENCES:
        raise ValueError(
            "failure_consequence must be one of "
            f"{sorted(VALID_FAILURE_CONSEQUENCES)}, got: {failure_consequence!r}"
        )

    if not fracture_sensitive or failure_consequence == "non-critical":
        return "exempt"

    has_life_limit = item.get("has_life_limit", False)
    life_limit_cycles = item.get("life_limit_cycles")

    if has_life_limit and life_limit_cycles is not None:
        return "flli"

    compliance_method = item.get("compliance_method")
    if compliance_method is not None and compliance_method not in VALID_COMPLIANCE_METHODS:
        raise ValueError(
            "compliance_method must be one of "
            f"{sorted(VALID_COMPLIANCE_METHODS)} or None, got: {compliance_method!r}"
        )

    safe_life_ratio = item.get("safe_life_ratio")

    if compliance_method in VALID_COMPLIANCE_METHODS:
        if safe_life_ratio is None:
            raise ValueError(
                "safe_life_ratio must be provided when compliance_method is set"
            )
        if safe_life_ratio < 0:
            raise ValueError("safe_life_ratio cannot be negative")
        if safe_life_ratio >= SAFE_LIFE_RATIO_THRESHOLD:
            return "pfci"
        return "fci"

    return "pfci"


def build_pfcil(items):
    """
    Compile the Potentially Fracture Critical Items List from structural items.

    Returns a new list of dicts (each item dict plus "_category" key).
    Includes all items with category pfci, fci, or flli. Exempt items excluded.
    The original item dicts are not mutated.
    """
    result = []
    for item in items:
        cat = categorize_item(item)
        if cat != "exempt":
            entry = dict(item)
            entry["_category"] = cat
            result.append(entry)
    return result


def build_fcil(items):
    """
    Compile the Fracture Critical Items List from structural items.

    Returns a new list of dicts with "_category" key. Includes items
    with category fci or flli. Exempt and pfci-only items are excluded.
    """
    result = []
    for item in items:
        cat = categorize_item(item)
        if cat in ("fci", "flli"):
            entry = dict(item)
            entry["_category"] = cat
            result.append(entry)
    return result


def build_fllil(items):
    """
    Compile the Flight Limited Life Items List from structural items.

    Returns a new list of dicts with "_category" = "flli" only.
    """
    result = []
    for item in items:
        cat = categorize_item(item)
        if cat == "flli":
            entry = dict(item)
            entry["_category"] = cat
            result.append(entry)
    return result


def check_documentation(item):
    """
    Return a sorted list of missing required document identifiers for the item.

    An exempt item has no documentation requirements and returns [].
    """
    cat = categorize_item(item)
    if cat == "exempt":
        return []
    required = REQUIRED_DOCS[cat]
    present = set(item.get("docs", []))
    return sorted(required - present)


def check_config_control(list_metadata, list_entries):
    """
    Check configuration control requirements for a fracture control list.

    list_metadata: dict with list-level control attributes.
        Checked keys: issue_number, approval_date, approved_by
    list_entries: list of item dicts; each should have an "id" key.
        Removed items (status == "removed") require a "removal_justification".

    Returns a sorted list of finding strings. An empty list means no findings.
    Raises TypeError for non-dict metadata or non-list entries.
    """
    if not isinstance(list_metadata, dict):
        raise TypeError("list_metadata must be a dict")
    if not isinstance(list_entries, list):
        raise TypeError("list_entries must be a list")

    findings = []

    if not list_metadata.get("issue_number"):
        findings.append("list_missing_issue_number")
    if not list_metadata.get("approval_date"):
        findings.append("list_missing_approval_date")
    if not list_metadata.get("approved_by"):
        findings.append("list_missing_approved_by")

    seen_ids = {}
    for idx, entry in enumerate(list_entries):
        item_id = entry.get("id")
        if not item_id:
            findings.append(f"entry[{idx}]_missing_item_id")
            continue
        if item_id in seen_ids:
            findings.append(f"duplicate_item_id:{item_id}")
        else:
            seen_ids[item_id] = idx
        if entry.get("status") == "removed" and not entry.get("removal_justification"):
            findings.append(f"item:{item_id}:removed_without_justification")

    return sorted(findings)
