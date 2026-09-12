"""
drd_fci_lists_logic.py

Deterministic logic for ECSS-E-ST-32C Annex G fracture-critical item
registers (PFCIL / FCIL / FLLIL). Paraphrased procedure only -- no
verbatim ECSS text is reproduced here. Normative anchor: ECSS-E-ST-32C
Annex G. stdlib only; no external dependencies.
"""

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

VALID_FAILURE_CONSEQUENCES = frozenset({
    "loss_of_life",
    "loss_of_vehicle",
    "loss_of_mission",
})

VALID_DISPOSITIONS = frozenset({
    "fracture_proof",
    "safe_life",
    "leak_before_burst",
    "retirement",
})

FCIL_REQUIRED_FIELDS = frozenset({
    "item_id",
    "description",
    "material",
    "flaw_assumption_mm",
    "fracture_toughness_mpa_sqrt_m",
    "stress_mpa",
    "required_life_cycles",
    "computed_life_cycles",
    "disposition",
})

PFCIL_EXTRA_FIELDS = frozenset({"failure_consequence"})
FLLIL_EXTRA_FIELDS = frozenset({"life_limit_cycles", "retest_interval_cycles"})


# ---------------------------------------------------------------------------
# Margin of safety
# ---------------------------------------------------------------------------

def compute_margin_of_safety(computed_life, required_life):
    """
    Fracture life margin of safety: (computed_life / required_life) - 1.
    Negative result means the item does not meet its service-life requirement.

    Args:
        computed_life (float): fracture life from analysis, in cycles
        required_life (float): required service life, in cycles

    Returns:
        float: margin of safety

    Raises:
        ValueError: if either argument is <= 0
    """
    if required_life <= 0:
        raise ValueError("required_life must be > 0")
    if computed_life <= 0:
        raise ValueError("computed_life must be > 0")
    return (computed_life / required_life) - 1.0


# ---------------------------------------------------------------------------
# Entry validation
# ---------------------------------------------------------------------------

def validate_fcil_entry(entry):
    """
    Validate a single FCIL entry dict.

    Args:
        entry (dict): item data

    Returns:
        list[str]: finding strings; empty list means the entry is valid
    """
    findings = []

    missing = FCIL_REQUIRED_FIELDS - entry.keys()
    if missing:
        findings.append("missing fields: {}".format(sorted(missing)))
        return findings  # cannot do numeric checks without the fields

    if entry["flaw_assumption_mm"] <= 0:
        findings.append("flaw_assumption_mm must be > 0")
    if entry["fracture_toughness_mpa_sqrt_m"] <= 0:
        findings.append("fracture_toughness_mpa_sqrt_m must be > 0")
    if entry["stress_mpa"] <= 0:
        findings.append("stress_mpa must be > 0")
    if entry["required_life_cycles"] <= 0:
        findings.append("required_life_cycles must be > 0")
    if entry["computed_life_cycles"] <= 0:
        findings.append("computed_life_cycles must be > 0")
    if entry["disposition"] not in VALID_DISPOSITIONS:
        findings.append(
            "disposition must be one of {}".format(sorted(VALID_DISPOSITIONS))
        )
    return findings


def validate_pfcil_entry(entry):
    """
    Validate a single PFCIL entry dict.
    Inherits all FCIL checks and adds failure_consequence validation.

    Args:
        entry (dict): item data

    Returns:
        list[str]: finding strings; empty list means the entry is valid
    """
    findings = validate_fcil_entry(entry)

    missing_extra = PFCIL_EXTRA_FIELDS - entry.keys()
    if missing_extra:
        findings.append("missing PFCIL fields: {}".format(sorted(missing_extra)))
        return findings

    if entry["failure_consequence"] not in VALID_FAILURE_CONSEQUENCES:
        findings.append(
            "failure_consequence must be one of {}".format(
                sorted(VALID_FAILURE_CONSEQUENCES)
            )
        )
    return findings


def validate_fllil_entry(entry):
    """
    Validate a single FLLIL entry dict.
    Inherits all FCIL checks and adds life-limit consistency validation.

    Args:
        entry (dict): item data

    Returns:
        list[str]: finding strings; empty list means the entry is valid
    """
    findings = validate_fcil_entry(entry)

    missing_extra = FLLIL_EXTRA_FIELDS - entry.keys()
    if missing_extra:
        findings.append("missing FLLIL fields: {}".format(sorted(missing_extra)))
        return findings

    if entry["life_limit_cycles"] < entry.get("required_life_cycles", 0):
        findings.append(
            "life_limit_cycles must be >= required_life_cycles"
        )
    if entry["retest_interval_cycles"] > entry["life_limit_cycles"]:
        findings.append(
            "retest_interval_cycles must be <= life_limit_cycles"
        )
    return findings


# ---------------------------------------------------------------------------
# Item categorization
# ---------------------------------------------------------------------------

def categorize_item(failure_consequence, has_life_limit, is_fracture_critical):
    """
    Determine which register lists an item belongs to.

    Rules (from ECSS-E-ST-32C Annex G, paraphrased):
      - is_fracture_critical=False: screened out; no lists returned
      - failure_consequence in VALID_FAILURE_CONSEQUENCES: PFCIL + FCIL
      - has_life_limit=True: FLLIL + FCIL
      - otherwise: FCIL only
    PFCIL and FLLIL are always also on the FCIL (subsets).

    Args:
        failure_consequence (str or None): consequence if the item fractures
        has_life_limit (bool): True if the item has a finite service life limit
        is_fracture_critical (bool): True if the item is fracture-critical

    Returns:
        list[str]: list names from {"PFCIL", "FCIL", "FLLIL"}; empty if screened out
    """
    if not is_fracture_critical:
        return []

    lists = ["FCIL"]

    if failure_consequence in VALID_FAILURE_CONSEQUENCES:
        lists.append("PFCIL")

    if has_life_limit:
        lists.append("FLLIL")

    return lists


# ---------------------------------------------------------------------------
# Register builder
# ---------------------------------------------------------------------------

def build_register(items):
    """
    Screen a list of structural items and partition them into the PFCIL,
    FCIL, and FLLIL registers.

    Each item dict must have:
      - item_id (str): unique identifier
      - is_fracture_critical (bool): fracture-criticality screening result
      - failure_consequence (str or None): one of VALID_FAILURE_CONSEQUENCES or None
      - has_life_limit (bool): True if the item carries a finite life limit

    Args:
        items (list[dict]): items to process

    Returns:
        dict: keys "PFCIL", "FCIL", "FLLIL", "screened_out", each mapping to
              a list of item_id strings

    Raises:
        ValueError: if any item is missing item_id
    """
    register = {"PFCIL": [], "FCIL": [], "FLLIL": [], "screened_out": []}

    for item in items:
        item_id = item.get("item_id")
        if not item_id:
            raise ValueError("item missing item_id: {}".format(item))

        if not item.get("is_fracture_critical", False):
            register["screened_out"].append(item_id)
            continue

        lists = categorize_item(
            failure_consequence=item.get("failure_consequence"),
            has_life_limit=item.get("has_life_limit", False),
            is_fracture_critical=True,
        )

        for lst in lists:
            register[lst].append(item_id)

    return register


# ---------------------------------------------------------------------------
# Cross-reference checks
# ---------------------------------------------------------------------------

def check_pfcil_subset_of_fcil(pfcil_ids, fcil_ids):
    """
    Verify every PFCIL item ID also appears on the FCIL.

    Args:
        pfcil_ids (list[str]): IDs on the PFCIL
        fcil_ids (list[str]): IDs on the FCIL

    Returns:
        list[str]: PFCIL item IDs absent from the FCIL; empty means no gap
    """
    fcil_set = set(fcil_ids)
    return [iid for iid in pfcil_ids if iid not in fcil_set]


def check_fllil_subset_of_fcil(fllil_ids, fcil_ids):
    """
    Verify every FLLIL item ID also appears on the FCIL.

    Args:
        fllil_ids (list[str]): IDs on the FLLIL
        fcil_ids (list[str]): IDs on the FCIL

    Returns:
        list[str]: FLLIL item IDs absent from the FCIL; empty means no gap
    """
    fcil_set = set(fcil_ids)
    return [iid for iid in fllil_ids if iid not in fcil_set]
