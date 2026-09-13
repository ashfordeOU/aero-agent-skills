"""ECSS-E-ST-20-06C clause 4.2 -- charging standard cross-references.

Offline, deterministic, stdlib-only implementation of the document
placement and normative-reference procedure that clause 4.2 introduces:
the charging standard sits inside the engineering branch of the ECSS
system, under the electrical and electromagnetic discipline, and it
leans on a set of related standards that a project has to carry in its
applicable-document tree.

The module provides:

  * a parser for ECSS document identifiers (branch, document kind,
    discipline, sub-discipline, issue letter, revision number);
  * a placement check that confirms a document belongs to the expected
    branch and discipline;
  * a topic registry mapping each charging-analysis topic onto the
    normative reference that governs it;
  * an audit of a project's declared applicable-document list against
    the references its topics require -- missing entries, malformed
    identifiers, duplicates, superseded issues, off-branch entries and
    supplementary (declared but not required) entries.

No verbatim standard text is reproduced; the clause and the referenced
documents are cited as anchors only.
"""

import re

__all__ = [
    "BRANCH_NAMES",
    "DOCUMENT_KINDS",
    "DISCIPLINE_NAMES",
    "TOPIC_REFERENCES",
    "CHARGING_STANDARD",
    "parse_ecss_identifier",
    "format_ecss_identifier",
    "compare_issue",
    "check_placement",
    "resolve_topic",
    "required_reference_set",
    "audit_declared_documents",
    "build_cross_reference_report",
]

IDENTIFIER_RE = re.compile(
    r"^ECSS-(?P<branch>[EMQS])-(?P<kind>ST|HB|TM)-(?P<discipline>\d{2})"
    r"(?:-(?P<sub>\d{2}))?(?P<issue>[A-Z])(?:-Rev\.(?P<rev>\d+))?$"
)

BRANCH_NAMES = {
    "E": "engineering",
    "M": "project-management",
    "Q": "product-assurance",
    "S": "system-description",
}

DOCUMENT_KINDS = {
    "ST": "standard",
    "HB": "handbook",
    "TM": "technical-memorandum",
}

DISCIPLINE_NAMES = {
    ("E", "10"): "system-engineering",
    ("E", "20"): "electrical-and-electromagnetic",
    ("E", "31"): "thermal-control",
    ("E", "32"): "structures",
    ("E", "40"): "software",
    ("Q", "60"): "electrical-electronic-and-electromechanical-parts",
    ("Q", "70"): "materials-mechanical-parts-and-processes",
    ("S", "00"): "system-description-and-glossary",
}

# The document this leaf is anchored in.
CHARGING_STANDARD = "ECSS-E-ST-20-06C"

# Charging-analysis topic -> the normative reference that governs it.
TOPIC_REFERENCES = {
    "space-plasma-environment-definition": "ECSS-E-ST-10-04C",
    "system-engineering-general-requirements": "ECSS-E-ST-10C",
    "electrical-and-electronic-general-requirements": "ECSS-E-ST-20C",
    "electromagnetic-compatibility-interface": "ECSS-E-ST-20-07C",
    "surface-material-and-treatment-selection": "ECSS-Q-ST-70C",
    "electrostatic-discharge-sensitive-part-control": "ECSS-Q-ST-60C",
    "thermal-control-coating-properties": "ECSS-E-ST-31C",
    "terms-definitions-and-abbreviations": "ECSS-S-ST-00-01C",
}

EXPECTED_BRANCH = "E"
EXPECTED_DISCIPLINE = "20"


def _require_identifier_string(value, label):
    if not isinstance(value, str) or not value.strip():
        raise ValueError("%s must be a non-empty string, got %r"
                         % (label, value))
    return value.strip()


def parse_ecss_identifier(identifier):
    """Split an ECSS document identifier into its structural fields."""
    text = _require_identifier_string(identifier, "identifier")
    match = IDENTIFIER_RE.match(text)
    if match is None:
        raise ValueError(
            "malformed ECSS identifier %r; expected a shape such as "
            "ECSS-E-ST-20-06C or ECSS-Q-ST-70C" % (identifier,)
        )
    branch = match.group("branch")
    kind = match.group("kind")
    discipline = match.group("discipline")
    sub = match.group("sub")
    revision = match.group("rev")
    return {
        "identifier": text,
        "branch": branch,
        "branch_name": BRANCH_NAMES[branch],
        "kind": kind,
        "kind_name": DOCUMENT_KINDS[kind],
        "discipline": discipline,
        "discipline_name": DISCIPLINE_NAMES.get(
            (branch, discipline), "uncategorized-discipline"),
        "subdiscipline": sub,
        "issue": match.group("issue"),
        "revision": int(revision) if revision is not None else 0,
    }


def format_ecss_identifier(parsed):
    """Rebuild an identifier string from parsed fields (round trip)."""
    if not isinstance(parsed, dict):
        raise ValueError("parsed identifier must be a mapping")
    for key in ("branch", "kind", "discipline", "issue"):
        if not parsed.get(key):
            raise ValueError("parsed identifier missing %r" % key)
    text = "ECSS-%s-%s-%s" % (parsed["branch"], parsed["kind"],
                              parsed["discipline"])
    if parsed.get("subdiscipline"):
        text += "-%s" % parsed["subdiscipline"]
    text += parsed["issue"]
    revision = parsed.get("revision") or 0
    if int(revision) > 0:
        text += "-Rev.%d" % int(revision)
    return text


def compare_issue(left, right):
    """Compare the issue of two identifiers of the same document.

    Returns -1 when left is the older issue, 0 when both carry the same
    issue and revision, +1 when left is the newer issue.
    """
    a = parse_ecss_identifier(left)
    b = parse_ecss_identifier(right)
    a_root = (a["branch"], a["kind"], a["discipline"], a["subdiscipline"])
    b_root = (b["branch"], b["kind"], b["discipline"], b["subdiscipline"])
    if a_root != b_root:
        raise ValueError(
            "cannot compare issues of two different documents (%s vs %s)"
            % (a["identifier"], b["identifier"])
        )
    a_key = (a["issue"], a["revision"])
    b_key = (b["issue"], b["revision"])
    if a_key < b_key:
        return -1
    if a_key > b_key:
        return 1
    return 0


def check_placement(identifier, branch=EXPECTED_BRANCH,
                    discipline=EXPECTED_DISCIPLINE):
    """Confirm a document sits in the expected branch and discipline."""
    expected_branch = _require_identifier_string(branch, "branch")
    expected_discipline = _require_identifier_string(discipline,
                                                     "discipline")
    if expected_branch not in BRANCH_NAMES:
        raise ValueError("unknown ECSS branch letter %r" % (branch,))
    parsed = parse_ecss_identifier(identifier)
    findings = []
    if parsed["branch"] != expected_branch:
        findings.append(
            "%s sits in the %s branch, expected %s"
            % (parsed["identifier"], parsed["branch_name"],
               BRANCH_NAMES[expected_branch])
        )
    if parsed["discipline"] != expected_discipline:
        findings.append(
            "%s sits in discipline %s, expected %s"
            % (parsed["identifier"], parsed["discipline"],
               expected_discipline)
        )
    return {
        "identifier": parsed["identifier"],
        "branch_name": parsed["branch_name"],
        "discipline_name": parsed["discipline_name"],
        "placed": not findings,
        "findings": findings,
    }


def resolve_topic(topic):
    """Return the normative reference governing a charging topic."""
    if not isinstance(topic, str):
        raise ValueError("topic must be a string, got %r" % (topic,))
    reference = TOPIC_REFERENCES.get(topic)
    if reference is None:
        raise ValueError(
            "uncategorized charging topic %r; known topics: %s"
            % (topic, ", ".join(sorted(TOPIC_REFERENCES)))
        )
    return reference


def required_reference_set(topics):
    """Sorted set of references required by a list of topics."""
    items = list(topics)
    if not items:
        raise ValueError("topic list must not be empty")
    return sorted({resolve_topic(topic) for topic in items})


def _root_of(identifier):
    parsed = parse_ecss_identifier(identifier)
    return (parsed["branch"], parsed["kind"], parsed["discipline"],
            parsed["subdiscipline"])


def audit_declared_documents(topics, declared):
    """Audit a declared applicable-document list against the topics.

    Reports malformed identifiers, duplicates, missing references,
    superseded issues, newer issues and supplementary entries.
    """
    if not isinstance(declared, (list, tuple)):
        raise ValueError("declared documents must be a list or tuple")
    required = required_reference_set(topics)
    entries = list(declared)

    malformed = []
    duplicates = []
    parsed_entries = []
    seen_identifiers = set()
    seen_roots = {}
    for entry in entries:
        try:
            parsed = parse_ecss_identifier(entry)
        except ValueError:
            malformed.append(entry)
            continue
        if parsed["identifier"] in seen_identifiers:
            duplicates.append(parsed["identifier"])
            continue
        seen_identifiers.add(parsed["identifier"])
        root = (parsed["branch"], parsed["kind"], parsed["discipline"],
                parsed["subdiscipline"])
        if root in seen_roots:
            duplicates.append(parsed["identifier"])
            continue
        seen_roots[root] = parsed["identifier"]
        parsed_entries.append(parsed)

    missing = []
    superseded = []
    newer_issue = []
    for reference in required:
        root = _root_of(reference)
        declared_identifier = seen_roots.get(root)
        if declared_identifier is None:
            missing.append(reference)
            continue
        order = compare_issue(declared_identifier, reference)
        if order < 0:
            superseded.append({
                "declared": declared_identifier,
                "required": reference,
            })
        elif order > 0:
            newer_issue.append({
                "declared": declared_identifier,
                "required": reference,
            })

    required_roots = {_root_of(reference) for reference in required}
    supplementary = [
        parsed["identifier"] for parsed in parsed_entries
        if (parsed["branch"], parsed["kind"], parsed["discipline"],
            parsed["subdiscipline"]) not in required_roots
    ]

    return {
        "required": required,
        "declared": [parsed["identifier"] for parsed in parsed_entries],
        "malformed": malformed,
        "duplicates": duplicates,
        "missing": missing,
        "superseded": superseded,
        "newer_issue": newer_issue,
        "supplementary": sorted(supplementary),
    }


def build_cross_reference_report(topics, declared,
                                 standard=CHARGING_STANDARD):
    """Full clause 4.2 placement plus applicable-document audit."""
    placement = check_placement(standard)
    audit = audit_declared_documents(topics, declared)

    findings = list(placement["findings"])
    for entry in audit["malformed"]:
        findings.append("malformed applicable-document entry %r" % (entry,))
    for entry in audit["duplicates"]:
        findings.append("duplicate applicable-document entry %s" % entry)
    for entry in audit["missing"]:
        findings.append(
            "required normative reference %s is absent from the "
            "applicable-document tree" % entry
        )
    for entry in audit["superseded"]:
        findings.append(
            "declared %s is an older issue than the required %s"
            % (entry["declared"], entry["required"])
        )

    notes = []
    for entry in audit["newer_issue"]:
        notes.append(
            "declared %s is a newer issue than the registered %s; confirm "
            "the tailoring before use" % (entry["declared"], entry["required"])
        )
    for entry in audit["supplementary"]:
        notes.append("%s is declared but not required by the listed topics"
                     % entry)

    report = dict(audit)
    report["standard"] = placement["identifier"]
    report["placement"] = placement
    report["findings"] = findings
    report["notes"] = notes
    report["compliant"] = not findings
    return report
