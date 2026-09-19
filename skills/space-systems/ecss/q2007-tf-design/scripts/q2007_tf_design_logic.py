"""Design and development of test facilities in a space test centre.

Anchor: ECSS-Q-ST-20-07C clause 5.6.1 (paraphrased into an implementable
procedure; no standard text is reproduced).

Procedure implemented here:

1. Categorize the development by the change it makes: a wholly new
   facility, a major modification (one that touches the load path, the
   control system or the safety envelope), or a minor modification. The
   category fixes the review set the development owes before the facility
   may be used, and nothing else about the project changes it.
2. Capture the requirements. Each requirement carries a criticality, a
   verification method, a status and, where it is verified or waived, the
   evidence or waiver reference that supports that status. A requirement
   with a status and no reference behind it is an assertion, not a
   verification.
3. Grade each requirement on the rules that do not depend on the schedule:
   - A safety-critical requirement is not closed by a review of the design
     alone. Someone has to look at, or exercise, the built article.
   - A verified or waived status has to name its evidence.
   - A safety-critical requirement cannot be waived at all; a waiver there
     moves the risk onto the operator, which is not the waiver's to give.
   - An open requirement is not a defect in itself -- it is work in hand --
     but it blocks the readiness decision.
4. Grade the gates. The review set comes from the change category, and the
   reviews are ordered. A later review recorded as closed while an earlier
   one is still open means the sequence was not run; the pair is named so
   the out-of-order closure can be traced.
5. Decide readiness. The facility may be used only when every required
   review is closed in order, every requirement is either verified with
   evidence or properly waived, and no requirement carries a finding.
   Verification coverage is reported as a fraction so a project at 0.95
   is visibly not a project at 1.0.

Stdlib only, offline, deterministic.
"""

CHANGE_NEW = "new-facility"
CHANGE_MAJOR = "major-modification"
CHANGE_MINOR = "minor-modification"
VALID_CHANGE_CATEGORIES = (CHANGE_NEW, CHANGE_MAJOR, CHANGE_MINOR)

GATE_REQUIREMENTS_REVIEW = "requirements-review"
GATE_PRELIMINARY_DESIGN_REVIEW = "preliminary-design-review"
GATE_CRITICAL_DESIGN_REVIEW = "critical-design-review"
GATE_FACILITY_ACCEPTANCE_REVIEW = "facility-acceptance-review"

# Ordered review set per change category. The order is the sequence the
# reviews have to close in, not merely the set that has to exist.
REQUIRED_GATES = {
    CHANGE_NEW: (
        GATE_REQUIREMENTS_REVIEW,
        GATE_PRELIMINARY_DESIGN_REVIEW,
        GATE_CRITICAL_DESIGN_REVIEW,
        GATE_FACILITY_ACCEPTANCE_REVIEW,
    ),
    CHANGE_MAJOR: (
        GATE_REQUIREMENTS_REVIEW,
        GATE_CRITICAL_DESIGN_REVIEW,
        GATE_FACILITY_ACCEPTANCE_REVIEW,
    ),
    CHANGE_MINOR: (
        GATE_REQUIREMENTS_REVIEW,
        GATE_FACILITY_ACCEPTANCE_REVIEW,
    ),
}

METHOD_ANALYSIS = "analysis"
METHOD_INSPECTION = "inspection"
METHOD_TEST = "test"
METHOD_REVIEW_OF_DESIGN = "review-of-design"
VALID_METHODS = (
    METHOD_ANALYSIS,
    METHOD_INSPECTION,
    METHOD_TEST,
    METHOD_REVIEW_OF_DESIGN,
)

CRITICALITY_SAFETY = "safety-critical"
CRITICALITY_PERFORMANCE = "performance"
CRITICALITY_INTERFACE = "interface"
CRITICALITY_OPERATIONAL = "operational"
VALID_CRITICALITIES = (
    CRITICALITY_SAFETY,
    CRITICALITY_PERFORMANCE,
    CRITICALITY_INTERFACE,
    CRITICALITY_OPERATIONAL,
)

STATUS_VERIFIED = "verified"
STATUS_IN_WORK = "in-work"
STATUS_NOT_STARTED = "not-started"
STATUS_WAIVED = "waived"
VALID_STATUSES = (STATUS_VERIFIED, STATUS_IN_WORK, STATUS_NOT_STARTED, STATUS_WAIVED)
OPEN_STATUSES = (STATUS_IN_WORK, STATUS_NOT_STARTED)

FINDING_SAFETY_BY_REVIEW_ONLY = (
    "safety-critical-requirement-closed-by-review-of-design-alone"
)
FINDING_NO_EVIDENCE = "verified-requirement-without-an-evidence-reference"
FINDING_WAIVER_NO_REFERENCE = "waived-requirement-without-a-waiver-reference"
FINDING_SAFETY_WAIVED = "safety-critical-requirement-waived"
FINDING_GATE_OPEN = "required-review-not-closed"
FINDING_GATE_OUT_OF_ORDER = "review-closed-before-an-earlier-review"


def _text(label, value):
    if not isinstance(value, str) or not value.strip():
        raise ValueError("%s must be a non-empty string, got %r" % (label, value))
    return value.strip()


def _optional_text(label, value):
    if value is None:
        return None
    return _text(label, value)


def required_gates(change_category):
    """The ordered review set a development of this category owes."""
    if change_category not in REQUIRED_GATES:
        raise ValueError(
            "unknown change category %r (expected one of %s)"
            % (change_category, ", ".join(VALID_CHANGE_CATEGORIES))
        )
    return tuple(REQUIRED_GATES[change_category])


def validate_requirement(record):
    """Validate one facility requirement and return a normalized copy."""
    if not isinstance(record, dict):
        raise ValueError("requirement record must be a mapping")
    req_id = _text("requirement id", record.get("id"))
    criticality = record.get("criticality")
    if criticality not in VALID_CRITICALITIES:
        raise ValueError(
            "requirement %s has unknown criticality %r (expected one of %s)"
            % (req_id, criticality, ", ".join(VALID_CRITICALITIES))
        )
    method = record.get("verification_method")
    if method not in VALID_METHODS:
        raise ValueError(
            "requirement %s has unknown verification_method %r (expected one of %s)"
            % (req_id, method, ", ".join(VALID_METHODS))
        )
    status = record.get("status", STATUS_NOT_STARTED)
    if status not in VALID_STATUSES:
        raise ValueError(
            "requirement %s has unknown status %r (expected one of %s)"
            % (req_id, status, ", ".join(VALID_STATUSES))
        )
    return {
        "id": req_id,
        "criticality": criticality,
        "verification_method": method,
        "status": status,
        "evidence_reference": _optional_text(
            "requirement %s evidence_reference" % req_id,
            record.get("evidence_reference"),
        ),
        "waiver_reference": _optional_text(
            "requirement %s waiver_reference" % req_id, record.get("waiver_reference")
        ),
    }


def requirement_findings(record):
    """Findings against one requirement, independent of the schedule."""
    norm = validate_requirement(record)
    findings = []
    if (
        norm["criticality"] == CRITICALITY_SAFETY
        and norm["verification_method"] == METHOD_REVIEW_OF_DESIGN
    ):
        findings.append(FINDING_SAFETY_BY_REVIEW_ONLY)
    if norm["status"] == STATUS_VERIFIED and norm["evidence_reference"] is None:
        findings.append(FINDING_NO_EVIDENCE)
    if norm["status"] == STATUS_WAIVED:
        if norm["waiver_reference"] is None:
            findings.append(FINDING_WAIVER_NO_REFERENCE)
        if norm["criticality"] == CRITICALITY_SAFETY:
            findings.append(FINDING_SAFETY_WAIVED)
    return findings


def requirement_is_open(record):
    """True when the requirement is still work in hand."""
    norm = validate_requirement(record)
    return norm["status"] in OPEN_STATUSES


def verification_coverage(requirements):
    """Fraction of requirements carrying a verified status."""
    if not isinstance(requirements, list) or not requirements:
        raise ValueError("requirements must be a non-empty list")
    verified = 0
    for record in requirements:
        if validate_requirement(record)["status"] == STATUS_VERIFIED:
            verified += 1
    return verified / len(requirements)


def validate_gate_record(change_category, closed_gates):
    """Validate the set of closed reviews against the category's review set."""
    wanted = required_gates(change_category)
    if isinstance(closed_gates, (str, bytes)) or not isinstance(
        closed_gates, (list, tuple)
    ):
        raise ValueError("closed_gates must be a list or tuple")
    normalized = []
    for gate in closed_gates:
        name = _text("closed gate", gate)
        if name not in wanted:
            raise ValueError(
                "review %r is not in the review set for a %s (expected one of %s)"
                % (name, change_category, ", ".join(wanted))
            )
        if name in normalized:
            raise ValueError("review %r is recorded closed twice" % (name,))
        normalized.append(name)
    return normalized


def gate_findings(change_category, closed_gates):
    """Findings about missing reviews and reviews closed out of order."""
    wanted = required_gates(change_category)
    closed = set(validate_gate_record(change_category, closed_gates))
    findings = []
    for index, gate in enumerate(wanted):
        if gate not in closed:
            findings.append({"review": gate, "finding": FINDING_GATE_OPEN})
            for later in wanted[index + 1:]:
                if later in closed:
                    findings.append(
                        {
                            "review": later,
                            "finding": FINDING_GATE_OUT_OF_ORDER,
                            "earlier_review": gate,
                        }
                    )
    return findings


def assess_requirement(record):
    """Assess one facility requirement against clause 5.6.1."""
    norm = validate_requirement(record)
    findings = requirement_findings(norm)
    return {
        "id": norm["id"],
        "criticality": norm["criticality"],
        "verification_method": norm["verification_method"],
        "status": norm["status"],
        "open": requirement_is_open(norm),
        "findings": findings,
        "sound": not findings,
    }


def assess_facility_development(project):
    """Run the full clause 5.6.1 assessment over one facility development."""
    if not isinstance(project, dict):
        raise ValueError("project must be a mapping")
    category = project.get("change_category")
    wanted = required_gates(category)
    requirements = project.get("requirements")
    if not isinstance(requirements, list) or not requirements:
        raise ValueError("project requirements must be a non-empty list")
    results = []
    seen = set()
    for record in requirements:
        result = assess_requirement(record)
        if result["id"] in seen:
            raise ValueError("duplicate requirement id %r" % (result["id"],))
        seen.add(result["id"])
        results.append(result)
    gates = gate_findings(category, project.get("closed_gates", []))
    open_ids = [r["id"] for r in results if r["open"]]
    unsound_ids = [r["id"] for r in results if not r["sound"]]
    coverage = verification_coverage(requirements)
    blocking = []
    if gates:
        blocking.append("required-reviews-not-closed-in-order")
    if open_ids:
        blocking.append("requirements-still-open")
    if unsound_ids:
        blocking.append("requirements-carrying-findings")
    return {
        "change_category": category,
        "required_gates": list(wanted),
        "gate_findings": gates,
        "requirements": results,
        "open_requirement_ids": open_ids,
        "unsound_requirement_ids": unsound_ids,
        "verification_coverage": coverage,
        "blocking_reasons": blocking,
        "ready_for_use": not blocking,
    }
