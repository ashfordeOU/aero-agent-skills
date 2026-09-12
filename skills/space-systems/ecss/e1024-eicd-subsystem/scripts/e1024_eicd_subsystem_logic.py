"""
ECSS-E-ST-10-24C §5.8.2 — Engineering Interface Control Document at subsystem level.
Deterministic, offline, stdlib-only.
"""

VALID_INTERFACE_TYPES = frozenset([
    "mechanical",
    "electrical_power",
    "electrical_signal",
    "thermal",
    "data",
    "rf",
    "fluid",
    "optical",
    "pyrotechnic",
])

VALID_VERIFICATION_METHODS = frozenset([
    "test",
    "analysis",
    "inspection",
    "review_of_design",
    "similarity",
])

REQUIRED_INTERFACE_FIELDS = [
    "interface_id",
    "interface_type",
    "subsystem_a",
    "subsystem_b",
    "description",
    "requirement_ids",
    "verification_method",
]

REQUIRED_EICD_SECTIONS = [
    "document_id",
    "revision",
    "space_segment_id",
    "interfaces",
    "applicable_documents",
]


def validate_interface_type(itype):
    """Returns True when itype names a recognized subsystem interface category."""
    return isinstance(itype, str) and itype.lower() in VALID_INTERFACE_TYPES


def check_interface_record(record):
    """
    Inspect a single interface record for completeness and validity.

    Returns a list of finding strings; an empty list means the record is valid.
    Checks: required fields present and non-empty, requirement_ids non-empty list,
    recognized interface_type, recognized verification_method, and distinct subsystems.
    """
    if not isinstance(record, dict):
        return ["record must be a dict"]

    findings = []

    for field in REQUIRED_INTERFACE_FIELDS:
        if field not in record:
            findings.append(f"missing field: {field}")
        elif field == "requirement_ids":
            if not isinstance(record[field], list):
                findings.append("requirement_ids must be a list")
            elif len(record[field]) == 0:
                findings.append(
                    "requirement_ids is empty — at least one system-level requirement must be cited"
                )
        elif not record[field] and record[field] != 0:
            findings.append(f"empty field: {field}")

    if "interface_type" in record and record.get("interface_type"):
        if not validate_interface_type(record["interface_type"]):
            findings.append(f"unrecognized interface_type: {record['interface_type']!r}")

    if "verification_method" in record and record.get("verification_method"):
        vm = record["verification_method"].lower()
        if vm not in VALID_VERIFICATION_METHODS:
            findings.append(
                f"unrecognized verification_method: {record['verification_method']!r}"
            )

    sub_a = record.get("subsystem_a", "")
    sub_b = record.get("subsystem_b", "")
    if sub_a and sub_b and sub_a.strip().lower() == sub_b.strip().lower():
        findings.append("subsystem_a and subsystem_b must be distinct")

    return findings


def check_requirement_traceability(interface_record, requirement_registry):
    """
    Verify each requirement_id in the interface record resolves in requirement_registry.

    requirement_registry must support the 'in' operator (set or dict).
    Returns a list of unresolvable requirement IDs.
    """
    req_ids = interface_record.get("requirement_ids", [])
    if not isinstance(req_ids, list):
        return ["requirement_ids must be a list"]
    return [rid for rid in req_ids if rid not in requirement_registry]


def check_bidirectional_consistency(interfaces):
    """
    Detect duplicate interface entries for the same (subsystem pair, type) combination.

    Two records covering the same pair of subsystems (regardless of direction) with
    the same interface_type are a conflict. Returns a list of conflict description strings.
    """
    seen = {}
    conflicts = []
    for record in interfaces:
        if not isinstance(record, dict):
            continue
        sub_a = record.get("subsystem_a", "")
        sub_b = record.get("subsystem_b", "")
        itype = record.get("interface_type", "")
        iid = record.get("interface_id", "<unknown>")
        if not (sub_a and sub_b and itype):
            continue
        key = (frozenset([sub_a.lower(), sub_b.lower()]), itype.lower())
        if key in seen:
            conflicts.append(
                f"duplicate interface for pair ({sub_a}, {sub_b}) "
                f"type={itype}: {seen[key]!r} and {iid!r}"
            )
        else:
            seen[key] = iid
    return conflicts


def check_eicd_document(eicd_doc):
    """
    Verify top-level EICD document section completeness.

    Returns a list of finding strings; empty means the document structure is valid.
    """
    if not isinstance(eicd_doc, dict):
        return ["eicd_doc must be a dict"]
    findings = []
    for section in REQUIRED_EICD_SECTIONS:
        if section not in eicd_doc:
            findings.append(f"missing EICD section: {section}")
        elif section == "interfaces":
            if not isinstance(eicd_doc[section], list):
                findings.append("interfaces must be a list")
            elif len(eicd_doc[section]) == 0:
                findings.append(
                    "interfaces list is empty — EICD must define at least one interface"
                )
        elif not eicd_doc[section]:
            findings.append(f"empty EICD section: {section}")
    return findings


def assess_eicd(eicd_doc, requirement_registry=None):
    """
    Full EICD assessment per ECSS-E-ST-10-24C §5.8.2.

    Runs four checks in sequence:
      1. Document-level completeness (required sections present and non-empty).
      2. Per-interface record completeness and validity.
      3. Requirement traceability for every interface record.
      4. Bidirectional consistency across all interface records.

    Returns a dict:
      {
        "document_findings": list[str],
        "interface_findings": dict[interface_id, list[str]],
        "traceability_findings": dict[interface_id, list[str]],
        "consistency_findings": list[str],
        "compliant": bool,
      }

    compliant is True only when all four finding collections are empty.
    """
    if requirement_registry is None:
        requirement_registry = set()

    result = {
        "document_findings": [],
        "interface_findings": {},
        "traceability_findings": {},
        "consistency_findings": [],
        "compliant": False,
    }

    result["document_findings"] = check_eicd_document(eicd_doc)
    if not isinstance(eicd_doc, dict):
        return result

    interfaces = eicd_doc.get("interfaces", [])
    if not isinstance(interfaces, list):
        return result

    for record in interfaces:
        iid = record.get("interface_id", "<unknown>") if isinstance(record, dict) else "<unknown>"

        record_findings = check_interface_record(record)
        if record_findings:
            result["interface_findings"][iid] = record_findings

        if isinstance(record, dict):
            unresolved = check_requirement_traceability(record, requirement_registry)
            if unresolved:
                result["traceability_findings"][iid] = unresolved

    result["consistency_findings"] = check_bidirectional_consistency(interfaces)

    result["compliant"] = (
        len(result["document_findings"]) == 0
        and len(result["interface_findings"]) == 0
        and len(result["traceability_findings"]) == 0
        and len(result["consistency_findings"]) == 0
    )

    return result
