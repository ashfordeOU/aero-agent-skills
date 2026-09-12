"""
Structural data exchange logic — ECSS-E-ST-32C clause 4.9.

Validates data items exchanged between structural engineering disciplines
(design, analysis, manufacturing, subsystems, test). Checks required
fields, allowed formats, ICD-pair authorization, and traceability.
"""

REQUIRED_FIELDS = (
    "item_id",
    "data_type",
    "sender",
    "receiver",
    "format",
    "version",
    "source_doc",
)

ALLOWED_FORMATS = {
    "fem_model":     ["nastran_bdf", "abaqus_inp", "ansys_cdb", "step"],
    "cad_model":     ["step", "iges", "catia_model", "jt"],
    "loads_file":    ["csv", "txt", "nastran_bdf"],
    "material_card": ["csv", "txt", "json"],
    "test_results":  ["csv", "txt", "pdf"],
    "icd":           ["pdf", "docx"],
}

DISCIPLINE_MAP = {
    "design":        ["cad_model", "icd"],
    "analysis":      ["fem_model", "loads_file", "material_card"],
    "manufacturing": ["material_card"],
    "test":          ["test_results"],
}


def validate_item(item):
    """
    Validate a single data exchange item dict.

    Returns {"valid": bool, "errors": list[str]}.
    Errors use the form "missing_field:<name>",
    "unknown_data_type:<type>", or "invalid_format:<fmt> allowed:<list>".
    """
    errors = []

    for field in REQUIRED_FIELDS:
        if field not in item or not str(item[field]).strip():
            errors.append("missing_field:" + field)

    if errors:
        return {"valid": False, "errors": errors}

    data_type = item["data_type"]
    if data_type not in ALLOWED_FORMATS:
        errors.append("unknown_data_type:" + data_type)
    elif item["format"] not in ALLOWED_FORMATS[data_type]:
        allowed = ",".join(ALLOWED_FORMATS[data_type])
        errors.append("invalid_format:" + item["format"] + " allowed:" + allowed)

    return {"valid": len(errors) == 0, "errors": errors}


def check_icd_authorization(item, icd_pairs):
    """
    Return True if (sender, receiver) from item appears in icd_pairs.

    icd_pairs: sequence of (sender, receiver) tuples.
    """
    return (item.get("sender"), item.get("receiver")) in icd_pairs


def validate_package(items, icd_pairs):
    """
    Validate an entire data exchange package.

    items     — list of data item dicts.
    icd_pairs — list of (sender, receiver) tuples authorizing exchanges.

    Returns:
        {
            "valid": bool,
            "item_results": list of per-item result dicts,
            "unauthorized_pairs": list of {"item_id": str, "pair": tuple},
        }
    The package is valid only when all items pass validation and all
    sender–receiver pairs are ICD-authorized.
    """
    item_results = []
    unauthorized_pairs = []

    for item in items:
        result = validate_item(item)
        result["item_id"] = item.get("item_id", "")
        item_results.append(result)

        if not check_icd_authorization(item, icd_pairs):
            unauthorized_pairs.append({
                "item_id": item.get("item_id", ""),
                "pair": (item.get("sender"), item.get("receiver")),
            })

    package_valid = (
        all(r["valid"] for r in item_results)
        and len(unauthorized_pairs) == 0
    )
    return {
        "valid": package_valid,
        "item_results": item_results,
        "unauthorized_pairs": unauthorized_pairs,
    }


def build_traceability_matrix(items):
    """
    Build a traceability matrix from a list of data items.

    Detects duplicate item_id values; a duplicate creates an ambiguous
    traceability chain and must be resolved before the package is accepted.

    Returns:
        {
            "matrix": list of {item_id, data_type, source_doc, version},
            "duplicates": list of item_id strings that appear more than once,
            "traceable": bool — True only when no duplicates are present,
        }
    """
    seen = {}
    duplicates = []
    matrix = []

    for item in items:
        iid = item.get("item_id", "")
        if iid in seen:
            if iid not in duplicates:
                duplicates.append(iid)
        else:
            seen[iid] = True
            matrix.append({
                "item_id":   iid,
                "data_type": item.get("data_type"),
                "source_doc": item.get("source_doc"),
                "version":   item.get("version"),
            })

    return {
        "matrix":     matrix,
        "duplicates": duplicates,
        "traceable":  len(duplicates) == 0,
    }


def categorize_items(items):
    """
    Assign data items to discipline groups based on data_type.

    An item may belong to multiple groups (e.g. material_card appears in
    both analysis and manufacturing). Items whose data_type is not
    recognized by DISCIPLINE_MAP go into the uncategorized group.

    Returns a dict mapping each discipline name (and "uncategorized")
    to a list of item_id strings.
    """
    result = {discipline: [] for discipline in DISCIPLINE_MAP}
    result["uncategorized"] = []

    for item in items:
        dt = item.get("data_type", "")
        iid = item.get("item_id", "")
        placed = False
        for discipline, types in DISCIPLINE_MAP.items():
            if dt in types:
                result[discipline].append(iid)
                placed = True
        if not placed:
            result["uncategorized"].append(iid)

    return result
