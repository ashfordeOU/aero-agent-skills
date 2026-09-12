"""
ECSS-E-ST-10-24C Annex B ICD DRD validation logic.

Deterministic, offline checks for Interface Control Document completeness
and DRD compliance. Reference: ECSS-E-ST-10-24C clause 5 / Annex B
(paraphrased — no verbatim standard text).
"""

KNOWN_INTERFACE_TYPES = frozenset({
    "mechanical", "electrical", "thermal", "data", "RF", "optical", "fluid"
})

REQUIRED_SECTIONS = frozenset({
    "scope",
    "reference_documents",
    "interface_description",
    "verification_requirements",
})

KNOWN_VERIFICATION_METHODS = frozenset({
    "analysis", "test", "inspection", "review_of_design"
})


class ICDValidationError(ValueError):
    """Raised when the ICD input is structurally malformed."""


def validate_identification(icd):
    """
    Check mandatory identification fields: icd_id, revision, interface_pair.
    Returns a list of finding strings; empty list means all fields are present.
    """
    findings = []
    if not isinstance(icd.get("icd_id", ""), str) or not icd.get("icd_id", "").strip():
        findings.append("icd_id is missing or empty")
    if not isinstance(icd.get("revision", ""), str) or not icd.get("revision", "").strip():
        findings.append("revision is missing or empty")
    pair = icd.get("interface_pair")
    if not isinstance(pair, (list, tuple)):
        findings.append("interface_pair must be a list or tuple with exactly two item names")
    elif len(pair) != 2:
        findings.append(
            f"interface_pair must contain exactly two items; got {len(pair)}"
        )
    else:
        if not isinstance(pair[0], str) or not pair[0].strip():
            findings.append("first item in interface_pair is missing or empty")
        if not isinstance(pair[1], str) or not pair[1].strip():
            findings.append("second item in interface_pair is missing or empty")
    return findings


def validate_interface_types(types_list):
    """
    Confirm every interface type in types_list is from KNOWN_INTERFACE_TYPES.
    Requires at least one type. Returns finding strings for violations.

    A finding names only the offending value. The accepted vocabulary is
    referenced by constant name and never interpolated into the message, so a
    finding can be attributed unambiguously to the one input that caused it.
    """
    if not isinstance(types_list, (list, tuple)) or len(types_list) == 0:
        return ["interface_types must be a non-empty list; at least one type required"]
    findings = []
    for t in types_list:
        if t not in KNOWN_INTERFACE_TYPES:
            findings.append(
                f"unrecognized interface type '{t}'; "
                f"expected a value from KNOWN_INTERFACE_TYPES "
                f"({len(KNOWN_INTERFACE_TYPES)} accepted values)"
            )
    return findings


def validate_required_sections(sections):
    """
    Confirm all mandatory DRD sections are present and non-empty.
    Returns finding strings for missing or empty sections.
    """
    if not isinstance(sections, dict):
        return ["sections must be a dict mapping section name to content"]
    findings = []
    for sec in sorted(REQUIRED_SECTIONS):
        if sec not in sections:
            findings.append(f"mandatory section missing: '{sec}'")
        elif not sections[sec]:
            findings.append(f"mandatory section is present but empty: '{sec}'")
    return findings


def validate_requirement_traceability(requirements):
    """
    Each requirement must carry a parent_ref linking it to an IRD or
    system-level requirement. Returns finding strings for missing links.
    Requires at least one requirement.
    """
    if not isinstance(requirements, (list, tuple)) or len(requirements) == 0:
        return ["requirements must be a non-empty list; at least one interface requirement expected"]
    findings = []
    for req in requirements:
        req_id = req.get("req_id", "<unknown>") if isinstance(req, dict) else "<unknown>"
        if not isinstance(req, dict):
            findings.append(f"requirement entry is not a dict: {req!r}")
            continue
        if not req.get("parent_ref", "").strip():
            findings.append(
                f"requirement '{req_id}' has no parent_ref "
                "(IRD or system-level traceability link missing)"
            )
    return findings


def validate_verification_coverage(requirements, verification_methods):
    """
    Each requirement must have a verification method from KNOWN_VERIFICATION_METHODS
    recorded in verification_methods. verification_methods is a list of dicts with
    keys 'req_id' and 'method'. Returns finding strings for missing or invalid methods.

    As with interface types, a finding names only the offending method value,
    never the accepted vocabulary.
    """
    if not isinstance(verification_methods, (list, tuple)):
        return ["verification_methods must be a list"]
    method_map = {}
    for vm in verification_methods:
        if isinstance(vm, dict) and "req_id" in vm and "method" in vm:
            method_map[vm["req_id"]] = vm["method"]

    findings = []
    for req in requirements:
        if not isinstance(req, dict):
            continue
        req_id = req.get("req_id", "<unknown>")
        method = method_map.get(req_id, "")
        if not method:
            findings.append(
                f"requirement '{req_id}' has no assigned verification method"
            )
        elif method not in KNOWN_VERIFICATION_METHODS:
            findings.append(
                f"requirement '{req_id}' has unrecognized verification method "
                f"'{method}'; expected a value from KNOWN_VERIFICATION_METHODS "
                f"({len(KNOWN_VERIFICATION_METHODS)} accepted values)"
            )
    return findings


def validate_icd_drd_compliance(icd):
    """
    Full DRD compliance check for an ICD dict.

    Runs all five checks in sequence and returns an aggregated list of
    finding strings. An empty list means the ICD satisfies all DRD criteria.

    Raises ICDValidationError if icd is not a dict.
    """
    if not isinstance(icd, dict):
        raise ICDValidationError(f"icd must be a dict; got {type(icd).__name__}")
    findings = []
    findings.extend(validate_identification(icd))
    findings.extend(validate_interface_types(icd.get("interface_types", [])))
    findings.extend(validate_required_sections(icd.get("sections", {})))
    findings.extend(validate_requirement_traceability(icd.get("requirements", [])))
    findings.extend(validate_verification_coverage(
        icd.get("requirements", []),
        icd.get("verification_methods", []),
    ))
    return findings
