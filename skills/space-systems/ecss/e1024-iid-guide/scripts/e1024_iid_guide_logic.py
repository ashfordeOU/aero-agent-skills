"""
IID (Interface Identification Document) assembly logic per ECSS-E-ST-10-24C Annex D.
Deterministic, offline, stdlib only.
"""

VALID_INTERFACE_TYPES = frozenset([
    "physical", "electrical", "data", "rf", "thermal", "optical", "fluid"
])

VALID_MATURITY_LEVELS = frozenset([
    "proposed", "agreed", "baselined"
])

REQUIRED_INTERFACE_FIELDS = frozenset([
    "id", "name", "type", "maturity", "side_a", "side_b", "icd_ref"
])


class IIDValidationError(Exception):
    pass


def categorize_interface_type(raw_type):
    """
    Normalize and return a canonical interface type string.
    Raises IIDValidationError for unrecognized types.
    """
    if raw_type is None:
        raise IIDValidationError("interface type cannot be None")
    normalized = str(raw_type).strip().lower()
    if normalized not in VALID_INTERFACE_TYPES:
        raise IIDValidationError(
            "unrecognized interface type '{}'; must be one of {}".format(
                raw_type, sorted(VALID_INTERFACE_TYPES)
            )
        )
    return normalized


def assign_maturity_level(raw_maturity):
    """
    Validate and return a canonical maturity level string.
    Raises IIDValidationError for unrecognized values.
    """
    if raw_maturity is None:
        raise IIDValidationError("maturity level cannot be None")
    normalized = str(raw_maturity).strip().lower()
    if normalized not in VALID_MATURITY_LEVELS:
        raise IIDValidationError(
            "unrecognized maturity level '{}'; must be one of {}".format(
                raw_maturity, sorted(VALID_MATURITY_LEVELS)
            )
        )
    return normalized


def check_icd_linkage(entry):
    """
    Return True if the interface entry has a valid (non-empty, non-TBD) ICD reference.
    """
    icd_ref = str(entry.get("icd_ref", "")).strip()
    return bool(icd_ref) and icd_ref.upper() != "TBD"


def validate_interface_entry(entry):
    """
    Validate a single interface entry dict.
    Returns a list of issue strings; empty list means the entry is valid.
    """
    issues = []

    for field in sorted(REQUIRED_INTERFACE_FIELDS):
        if field not in entry:
            issues.append("missing required field: {}".format(field))
        elif entry[field] is None or str(entry[field]).strip() == "":
            issues.append("empty required field: {}".format(field))

    itype = entry.get("type")
    if itype is not None and str(itype).strip() != "":
        normalized = str(itype).strip().lower()
        if normalized not in VALID_INTERFACE_TYPES:
            issues.append(
                "invalid interface type '{}'; must be one of {}".format(
                    itype, sorted(VALID_INTERFACE_TYPES)
                )
            )

    maturity = entry.get("maturity")
    if maturity is not None and str(maturity).strip() != "":
        normalized = str(maturity).strip().lower()
        if normalized not in VALID_MATURITY_LEVELS:
            issues.append(
                "invalid maturity level '{}'; must be one of {}".format(
                    maturity, sorted(VALID_MATURITY_LEVELS)
                )
            )

    icd_ref = entry.get("icd_ref")
    if icd_ref is not None:
        ref_str = str(icd_ref).strip()
        if ref_str.upper() == "TBD":
            issues.append(
                "icd_ref is TBD; interface lacks a controlling ICD reference"
            )

    return issues


def validate_iid_collection(interfaces):
    """
    Validate a list of interface entry dicts for an IID.
    Returns a dict with keys: errors, warnings, summary, is_valid.
    """
    if not isinstance(interfaces, list):
        raise IIDValidationError("interfaces must be a list")

    errors = []
    warnings = []
    seen_ids = {}

    for idx, entry in enumerate(interfaces):
        entry_issues = validate_interface_entry(entry)
        for issue in entry_issues:
            errors.append({
                "index": idx,
                "id": entry.get("id", "[{}]".format(idx)),
                "issue": issue,
            })

        entry_id = entry.get("id")
        if entry_id is not None:
            if entry_id in seen_ids:
                errors.append({
                    "index": idx,
                    "id": entry_id,
                    "issue": "duplicate interface ID; already seen at index {}".format(
                        seen_ids[entry_id]
                    ),
                })
            else:
                seen_ids[entry_id] = idx

    if interfaces:
        maturities = [
            str(e.get("maturity", "")).strip().lower()
            for e in interfaces
            if e.get("maturity") is not None
        ]
        if maturities and all(m == "proposed" for m in maturities):
            warnings.append(
                "all interfaces are at 'proposed' maturity; none have been agreed or baselined"
            )

    summary = compute_iid_summary(interfaces)

    return {
        "errors": errors,
        "warnings": warnings,
        "summary": summary,
        "is_valid": len(errors) == 0,
    }


def compute_iid_summary(interfaces):
    """
    Compute summary statistics for an IID interface collection.
    Returns counts by type, counts by maturity, and ICD gap details.
    """
    type_counts = {}
    maturity_counts = {}
    icd_gaps = []

    for entry in interfaces:
        itype = str(entry.get("type", "unknown")).strip().lower()
        type_counts[itype] = type_counts.get(itype, 0) + 1

        maturity = str(entry.get("maturity", "unknown")).strip().lower()
        maturity_counts[maturity] = maturity_counts.get(maturity, 0) + 1

        if not check_icd_linkage(entry):
            icd_gaps.append(entry.get("id", "[unknown]"))

    return {
        "total": len(interfaces),
        "by_type": type_counts,
        "by_maturity": maturity_counts,
        "icd_gap_count": len(icd_gaps),
        "icd_gap_ids": icd_gaps,
    }


def identify_completeness_gaps(interfaces):
    """
    Identify completeness gaps in an IID collection:
    - Interfaces without a controlling ICD reference
    - Interfaces still at 'proposed' maturity
    - Interfaces missing a responsible party on either side
    Returns a dict of gap lists keyed by gap type.
    """
    no_icd = []
    proposed_only = []
    no_side_a = []
    no_side_b = []

    for entry in interfaces:
        entry_id = entry.get("id", "[unknown]")

        if not check_icd_linkage(entry):
            no_icd.append(entry_id)

        maturity = str(entry.get("maturity", "")).strip().lower()
        if maturity == "proposed":
            proposed_only.append(entry_id)

        if not str(entry.get("side_a", "")).strip():
            no_side_a.append(entry_id)

        if not str(entry.get("side_b", "")).strip():
            no_side_b.append(entry_id)

    return {
        "no_icd_linkage": no_icd,
        "proposed_maturity": proposed_only,
        "no_side_a_responsible": no_side_a,
        "no_side_b_responsible": no_side_b,
    }
