"""
ECSS-E-ST-10C Annex A — Technical requirements specification (TS) DRD validation.
Implements deterministic, offline checks for TS document completeness and
requirement integrity per the ECSS document requirements definition.
Citation anchor: ECSS-E-ST-10C Annex A (DRD-TS).
"""

MANDATORY_SECTIONS = [
    "identification",
    "mission_context",
    "technical_performance_requirements",
    "interface_requirements",
    "environmental_requirements",
    "verification_table",
]

VERIFICATION_METHOD_MAP = {
    "test": "T",
    "t": "T",
    "analysis": "A",
    "a": "A",
    "inspection": "I",
    "i": "I",
    "review of design": "R",
    "rod": "R",
    "r": "R",
    "review": "R",
}

REQUIREMENT_TYPES = frozenset(
    ["functional", "performance", "interface", "design", "environmental"]
)

REQUIREMENT_SECTIONS = [
    "technical_performance_requirements",
    "interface_requirements",
    "environmental_requirements",
]


class TsValidationError(ValueError):
    """Raised when input data fails structural pre-validation."""


def validate_ts_structure(ts_doc):
    """
    Return a list of findings for each mandatory section absent from ts_doc.
    Each finding: {section, issue, severity}.
    """
    if not isinstance(ts_doc, dict):
        raise TsValidationError("ts_doc must be a dict")
    findings = []
    for section in MANDATORY_SECTIONS:
        if ts_doc.get(section) is None:
            findings.append(
                {
                    "section": section,
                    "issue": f"Mandatory section '{section}' is absent from TS document",
                    "severity": "major",
                }
            )
    return findings


def categorize_verification_method(method_str):
    """
    Map a verification method string to its canonical code (T / A / I / R).
    Returns None for an unrecognized input.
    """
    if not isinstance(method_str, str):
        return None
    return VERIFICATION_METHOD_MAP.get(method_str.strip().lower())


def validate_requirement(req):
    """
    Validate a single requirement dict.
    Expected keys: id, text, verification_method, req_type (optional).
    Returns a list of findings, each: {req_id, issue, severity}.
    """
    if not isinstance(req, dict):
        raise TsValidationError("req must be a dict")
    findings = []
    req_id = str(req.get("id", "")).strip()
    label = req_id if req_id else "<no-id>"

    if not req_id:
        findings.append(
            {
                "req_id": label,
                "issue": "Requirement is missing a unique identifier",
                "severity": "critical",
            }
        )

    if not str(req.get("text", "")).strip():
        findings.append(
            {
                "req_id": label,
                "issue": "Requirement text is empty",
                "severity": "critical",
            }
        )

    vm = req.get("verification_method")
    if not vm:
        findings.append(
            {
                "req_id": label,
                "issue": "Requirement has no verification method assigned",
                "severity": "major",
            }
        )
    else:
        if categorize_verification_method(str(vm)) is None:
            findings.append(
                {
                    "req_id": label,
                    "issue": (
                        f"Unrecognized verification method '{vm}';"
                        " expected test / analysis / inspection / review of design"
                    ),
                    "severity": "major",
                }
            )

    req_type = req.get("req_type")
    if req_type is not None and req_type not in REQUIREMENT_TYPES:
        findings.append(
            {
                "req_id": label,
                "issue": (
                    f"Requirement type '{req_type}' is not recognized;"
                    f" expected one of {sorted(REQUIREMENT_TYPES)}"
                ),
                "severity": "minor",
            }
        )

    return findings


def check_interface_requirement_linkage(req, registered_icds):
    """
    For a requirement of type 'interface', verify the referenced ICD is registered.
    Returns a list of findings (empty if req is not an interface type).
    """
    if not isinstance(req, dict):
        raise TsValidationError("req must be a dict")
    if not isinstance(registered_icds, (list, set, frozenset)):
        raise TsValidationError("registered_icds must be a list or set")

    if req.get("req_type") != "interface":
        return []

    req_id = str(req.get("id", "<no-id>")).strip()
    icd_ref = req.get("icd_reference")

    if not icd_ref:
        return [
            {
                "req_id": req_id,
                "issue": "Interface requirement has no ICD reference",
                "severity": "major",
            }
        ]

    if icd_ref not in registered_icds:
        return [
            {
                "req_id": req_id,
                "issue": f"ICD reference '{icd_ref}' is not in the registered ICD list",
                "severity": "major",
            }
        ]

    return []


def score_ts_completeness(ts_doc):
    """
    Return a completeness score (0.0 – 1.0) based on mandatory sections present.
    """
    if not isinstance(ts_doc, dict):
        raise TsValidationError("ts_doc must be a dict")
    present = sum(1 for s in MANDATORY_SECTIONS if ts_doc.get(s) is not None)
    return present / len(MANDATORY_SECTIONS)


def validate_ts_document(ts_doc, registered_icds=None):
    """
    Full TS document validation against ECSS-E-ST-10C Annex A DRD.
    Returns a dict:
      {
        "structure_findings": [...],
        "requirement_findings": [...],
        "interface_findings": [...],
        "completeness_score": float,
        "compliant": bool,
      }
    """
    if registered_icds is None:
        registered_icds = []

    structure_findings = validate_ts_structure(ts_doc)
    req_findings = []
    iface_findings = []

    for section_key in REQUIREMENT_SECTIONS:
        requirements = ts_doc.get(section_key) or []
        for req in requirements:
            req_findings.extend(validate_requirement(req))
            iface_findings.extend(
                check_interface_requirement_linkage(req, registered_icds)
            )

    completeness = score_ts_completeness(ts_doc)
    critical_or_major = {"critical", "major"}
    compliant = (
        len(structure_findings) == 0
        and not any(f["severity"] in critical_or_major for f in req_findings)
        and not any(f["severity"] in critical_or_major for f in iface_findings)
    )

    return {
        "structure_findings": structure_findings,
        "requirement_findings": req_findings,
        "interface_findings": iface_findings,
        "completeness_score": completeness,
        "compliant": compliant,
    }
