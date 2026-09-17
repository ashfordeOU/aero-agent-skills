"""Justification-document data-item assessment for commercial EEE part usage.

Anchor: ECSS-Q-ST-60-13C Annex F (the data item that defines what a
justification record has to contain to support a decision to use a commercial
electrical, electronic and electromechanical part). Paraphrased into an
implementable procedure; no standard text is reproduced.

Procedure implemented here
--------------------------
1. Validate the document identity: the issuing project, the document
   identifier, its issue and its date.
2. Check the data item's required section set against the sections the draft
   actually carries, name every absent section, and express the result as a
   section-coverage fraction judged at unity under a named tolerance.
3. Validate each justification entry: the part it covers, the usage decision
   taken, a written rationale, the residual risk level, the supporting
   evidence items and the authority that approved the entry.
4. Hold each decision to its own evidence demand: a decision taken on heritage
   alone needs different support from one taken on the back of additional
   testing, and a rejection must not carry mitigation actions it will never
   perform.
5. Refuse the combination the data item exists to prevent: a high residual
   risk carried on an accept-as-is decision with no mitigation and no further
   testing behind it.
6. Reconcile the justified parts against the declared commercial-part usage
   list in both directions, and return a verdict carrying every finding.
"""

import datetime
import math

__all__ = [
    "REQUIRED_SECTIONS",
    "OPTIONAL_SECTIONS",
    "RECOGNIZED_SECTIONS",
    "USAGE_DECISIONS",
    "RECOGNIZED_EVIDENCE",
    "REQUIRED_EVIDENCE",
    "RISK_RANK",
    "MAX_RISK_ACCEPT_AS_IS",
    "COVERAGE_TOLERANCE",
    "normalize_token",
    "validate_identity",
    "validate_iso_date",
    "validate_section",
    "absent_sections",
    "section_coverage",
    "validate_decision",
    "validate_risk_level",
    "validate_evidence_item",
    "validate_entry",
    "missing_evidence_types",
    "assess_entry",
    "reconcile_usage_list",
    "assess_justification_document",
]

# The sections the data item requires a justification document to carry.
REQUIRED_SECTIONS = (
    "document-identification",
    "part-identification",
    "intended-application",
    "usage-decision",
    "decision-rationale",
    "supporting-evidence",
    "residual-risk-assessment",
    "mitigation-actions",
    "approval-record",
)

# Sections a document may also carry without being required to.
OPTIONAL_SECTIONS = (
    "reference-documents",
    "open-actions",
    "revision-history",
)

RECOGNIZED_SECTIONS = REQUIRED_SECTIONS + OPTIONAL_SECTIONS

# The decisions a justification entry can record about one commercial part.
USAGE_DECISIONS = (
    "accept-as-is",
    "accept-with-mitigation",
    "accept-with-additional-testing",
    "reject",
)

# The kinds of supporting evidence an entry can cite.
RECOGNIZED_EVIDENCE = (
    "manufacturer-datasheet",
    "manufacturer-assessment",
    "flight-heritage-record",
    "evaluation-test-report",
    "additional-test-plan",
    "additional-test-report",
    "radiation-verification-report",
    "derating-analysis",
    "worst-case-analysis",
    "risk-analysis-record",
    "mitigation-verification-record",
)

# What each decision has to be able to show before it can be issued.
REQUIRED_EVIDENCE = {
    "accept-as-is": (
        "manufacturer-datasheet",
        "manufacturer-assessment",
        "flight-heritage-record",
        "derating-analysis",
    ),
    "accept-with-mitigation": (
        "manufacturer-datasheet",
        "risk-analysis-record",
        "mitigation-verification-record",
        "derating-analysis",
    ),
    "accept-with-additional-testing": (
        "manufacturer-datasheet",
        "additional-test-plan",
        "additional-test-report",
        "evaluation-test-report",
    ),
    "reject": (
        "risk-analysis-record",
    ),
}

# Residual risk levels, ordered.
RISK_RANK = {"low": 1, "medium": 2, "high": 3}

# The highest residual risk an accept-as-is decision may carry.
MAX_RISK_ACCEPT_AS_IS = "medium"

# Section coverage is a quotient of two counts; a complete document must not
# fail on floating-point representation alone.
COVERAGE_TOLERANCE = 1e-9


def _require_text(value, label):
    """Return a non-blank text field, raising on anything else."""
    if not isinstance(value, str):
        raise ValueError("%s must be a string, got %s" % (label, type(value).__name__))
    text = value.strip()
    if not text:
        raise ValueError("%s must not be blank" % label)
    return text


def normalize_token(value, label="token"):
    """Return a normalized lower-case hyphenated token."""
    text = _require_text(value, label)
    return "-".join(text.lower().replace("_", " ").replace("-", " ").split())


def validate_iso_date(value, label):
    """Return a calendar date parsed from an ISO day string."""
    if isinstance(value, datetime.date) and not isinstance(value, datetime.datetime):
        return value
    text = _require_text(value, label)
    try:
        return datetime.date.fromisoformat(text)
    except ValueError:
        raise ValueError("%s must be an ISO calendar day, got '%s'" % (label, text))


def validate_identity(identity):
    """Return the validated identity of the justification document."""
    if not isinstance(identity, dict):
        raise ValueError("identity must be a mapping")
    for key in ("project", "document_identifier", "issue", "date"):
        if key not in identity:
            raise ValueError("identity missing required key '%s'" % key)
    return {
        "project": _require_text(identity["project"], "project"),
        "document_identifier": _require_text(
            identity["document_identifier"], "document_identifier"
        ),
        "issue": _require_text(identity["issue"], "issue"),
        "date": validate_iso_date(identity["date"], "document date"),
    }


def validate_section(value):
    """Return the validated section token."""
    token = normalize_token(value, "section")
    if token not in RECOGNIZED_SECTIONS:
        raise ValueError(
            "section '%s' is not a data-item section; expected one of %s"
            % (token, ", ".join(RECOGNIZED_SECTIONS))
        )
    return token


def absent_sections(present_sections):
    """Return the required sections the draft does not carry."""
    if not isinstance(present_sections, (list, tuple, set, frozenset)):
        raise ValueError("present_sections must be a collection")
    present = set()
    for value in present_sections:
        token = validate_section(value)
        if token in present:
            raise ValueError("section '%s' is declared twice" % token)
        present.add(token)
    return [s for s in REQUIRED_SECTIONS if s not in present]


def section_coverage(present_sections):
    """Return the fraction of the required section set the draft carries."""
    absent = absent_sections(present_sections)
    return (len(REQUIRED_SECTIONS) - len(absent)) / float(len(REQUIRED_SECTIONS))


def validate_decision(value):
    """Return the validated usage decision token."""
    token = normalize_token(value, "usage decision")
    if token not in USAGE_DECISIONS:
        raise ValueError(
            "usage decision '%s' is not recognized; expected one of %s"
            % (token, ", ".join(USAGE_DECISIONS))
        )
    return token


def validate_risk_level(value):
    """Return the validated residual risk level token."""
    token = normalize_token(value, "residual risk")
    if token not in RISK_RANK:
        raise ValueError(
            "residual risk '%s' is not recognized; expected one of %s"
            % (token, ", ".join(sorted(RISK_RANK, key=RISK_RANK.get)))
        )
    return token


def validate_evidence_item(item):
    """Return one validated supporting-evidence citation."""
    if not isinstance(item, dict):
        raise ValueError("each evidence item must be a mapping")
    for key in ("evidence_type", "reference"):
        if key not in item:
            raise ValueError("evidence item missing required key '%s'" % key)
    token = normalize_token(item["evidence_type"], "evidence_type")
    if token not in RECOGNIZED_EVIDENCE:
        raise ValueError(
            "evidence type '%s' is not recognized; expected one of %s"
            % (token, ", ".join(RECOGNIZED_EVIDENCE))
        )
    return {
        "evidence_type": token,
        "reference": _require_text(item["reference"], "evidence reference"),
    }


def validate_entry(entry):
    """Return one validated justification entry."""
    if not isinstance(entry, dict):
        raise ValueError("each justification entry must be a mapping")
    for key in (
        "part_number",
        "intended_application",
        "decision",
        "rationale",
        "residual_risk",
        "approved_by",
    ):
        if key not in entry:
            raise ValueError("justification entry missing required key '%s'" % key)

    rationale = _require_text(entry["rationale"], "rationale")
    if len(rationale) < 20:
        raise ValueError(
            "rationale for '%s' is too short to stand as a justification"
            % _require_text(entry["part_number"], "part_number")
        )

    evidence_raw = entry.get("evidence", [])
    if evidence_raw is None:
        evidence_raw = []
    if not isinstance(evidence_raw, (list, tuple)):
        raise ValueError("evidence must be a sequence")
    evidence = []
    seen_types = set()
    for index, item in enumerate(evidence_raw):
        try:
            validated = validate_evidence_item(item)
        except ValueError as exc:
            raise ValueError("evidence[%d]: %s" % (index, exc))
        if validated["evidence_type"] in seen_types:
            raise ValueError(
                "evidence type '%s' is cited twice on one entry"
                % validated["evidence_type"]
            )
        seen_types.add(validated["evidence_type"])
        evidence.append(validated)

    mitigations_raw = entry.get("mitigations", [])
    if mitigations_raw is None:
        mitigations_raw = []
    if not isinstance(mitigations_raw, (list, tuple)):
        raise ValueError("mitigations must be a sequence")
    mitigations = []
    for index, value in enumerate(mitigations_raw):
        text = _require_text(value, "mitigations[%d]" % index)
        if text in mitigations:
            raise ValueError("mitigation '%s' is listed twice" % text)
        mitigations.append(text)

    return {
        "part_number": _require_text(entry["part_number"], "part_number"),
        "intended_application": _require_text(
            entry["intended_application"], "intended_application"
        ),
        "decision": validate_decision(entry["decision"]),
        "rationale": rationale,
        "residual_risk": validate_risk_level(entry["residual_risk"]),
        "approved_by": _require_text(entry["approved_by"], "approved_by"),
        "evidence": evidence,
        "mitigations": mitigations,
    }


def missing_evidence_types(decision, evidence_types):
    """Return the evidence a decision demands but the entry does not cite."""
    token = validate_decision(decision)
    if not isinstance(evidence_types, (list, tuple, set, frozenset)):
        raise ValueError("evidence_types must be a collection")
    cited = set()
    for value in evidence_types:
        cited.add(normalize_token(value, "evidence_type"))
    return [t for t in REQUIRED_EVIDENCE[token] if t not in cited]


def assess_entry(entry):
    """Return one justification entry carrying its findings."""
    validated = validate_entry(entry)
    findings = []

    absent_evidence = missing_evidence_types(
        validated["decision"], [e["evidence_type"] for e in validated["evidence"]]
    )
    for evidence_type in absent_evidence:
        findings.append(
            "entry '%s' takes decision '%s' without citing %s"
            % (validated["part_number"], validated["decision"], evidence_type)
        )

    risk = validated["residual_risk"]
    decision = validated["decision"]
    if (
        decision == "accept-as-is"
        and RISK_RANK[risk] > RISK_RANK[MAX_RISK_ACCEPT_AS_IS]
    ):
        findings.append(
            "entry '%s' carries %s residual risk on an accept-as-is decision"
            % (validated["part_number"], risk)
        )

    if decision == "accept-with-mitigation" and not validated["mitigations"]:
        findings.append(
            "entry '%s' accepts on mitigation but names no mitigation action"
            % validated["part_number"]
        )

    if decision == "reject" and validated["mitigations"]:
        findings.append(
            "entry '%s' is a rejection yet carries mitigation actions"
            % validated["part_number"]
        )

    validated["missing_evidence"] = absent_evidence
    validated["findings"] = findings
    validated["justified"] = not findings
    return validated


def reconcile_usage_list(usage_list, entries):
    """Return the two-way mismatch between usage list and justified parts."""
    if not isinstance(usage_list, (list, tuple)) or not usage_list:
        raise ValueError("usage_list must be a non-empty sequence")
    listed = []
    for index, value in enumerate(usage_list):
        part_number = _require_text(value, "usage_list[%d]" % index)
        if part_number in listed:
            raise ValueError("part '%s' appears twice on the usage list" % part_number)
        listed.append(part_number)
    if not isinstance(entries, (list, tuple)):
        raise ValueError("entries must be a sequence")
    justified = []
    for item in entries:
        if not isinstance(item, dict) or "part_number" not in item:
            raise ValueError("each entry must be a validated justification mapping")
        part_number = item["part_number"]
        if part_number not in justified:
            justified.append(part_number)
    return {
        "listed": listed,
        "justified": justified,
        "unjustified_parts": [p for p in listed if p not in justified],
        "unlisted_parts": [p for p in justified if p not in listed],
    }


def assess_justification_document(document):
    """Run the full Annex F assessment of one justification document.

    document keys: identity, sections, usage_list, entries.
    """
    if not isinstance(document, dict):
        raise ValueError("document must be a mapping")
    for key in ("identity", "sections", "usage_list", "entries"):
        if key not in document:
            raise ValueError("document missing required key '%s'" % key)

    identity = validate_identity(document["identity"])

    raw_entries = document["entries"]
    if not isinstance(raw_entries, (list, tuple)) or not raw_entries:
        raise ValueError("entries must be a non-empty sequence")

    findings = []
    entries = []
    seen_parts = set()
    for raw in raw_entries:
        assessed = assess_entry(raw)
        if assessed["part_number"] in seen_parts:
            raise ValueError(
                "part '%s' is justified twice in one document"
                % assessed["part_number"]
            )
        seen_parts.add(assessed["part_number"])
        entries.append(assessed)
        findings.extend(assessed["findings"])

    absent = absent_sections(document["sections"])
    for section in absent:
        findings.append("required section '%s' is not in the document" % section)

    coverage = section_coverage(document["sections"])
    sections_complete = math.isclose(
        coverage, 1.0, rel_tol=0.0, abs_tol=COVERAGE_TOLERANCE
    )

    reconciliation = reconcile_usage_list(document["usage_list"], entries)
    for part_number in reconciliation["unjustified_parts"]:
        findings.append(
            "part '%s' is used but the document justifies no decision for it"
            % part_number
        )
    for part_number in reconciliation["unlisted_parts"]:
        findings.append(
            "the document justifies part '%s', which the usage list does not carry"
            % part_number
        )

    return {
        "identity": identity,
        "entries": entries,
        "absent_sections": absent,
        "section_coverage": coverage,
        "sections_complete": sections_complete,
        "reconciliation": reconciliation,
        "fit_to_issue": not findings,
        "findings": findings,
    }
