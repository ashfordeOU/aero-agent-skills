"""Kept-document assessment for class 3 commercial EEE part activities.

Anchor: ECSS-Q-ST-60-13C clause 6.7 (the documentation kept for commercial
part control carried out at the lowest assurance level). Paraphrased into an
implementable procedure; no standard text is reproduced.

Procedure implemented here
--------------------------
1. Validate the activity the file belongs to: the part number it covers, the
   supplier behind it and the project keeping the file.
2. Validate every document: a recognized type, an identifier, an issue, a
   date, a custodian drawn from a recognized custody mode, a whole-year
   retention period and the parts it covers. Reject a type declared twice.
3. Compare the class 3 minimum kept set with the types present, name every
   minimum document the file never produced, and separate the documents kept
   above the minimum, which are permitted but never make up a shortfall.
4. Judge custody: a minimum document the supplier holds with no access
   commitment is a document the project cannot produce, so it counts as
   absent in practice even though a copy exists somewhere.
5. Derive each document's retention end from its own date and its declared
   retention in whole years, and compare that end with the horizon the
   project has to reach. Whole-year calendar arithmetic keeps it exact.
6. Return the per-document entries, the absent minimum types, the
   above-minimum types, the completeness fraction and a verdict carrying
   every finding.
"""

import datetime
import math

__all__ = [
    "MINIMUM_DOCUMENTS",
    "ABOVE_MINIMUM_DOCUMENTS",
    "RECOGNIZED_DOCUMENTS",
    "CUSTODY_MODES",
    "PROJECT_REACHABLE_CUSTODY",
    "DEFAULT_RETENTION_FLOOR_YEARS",
    "COMPLETENESS_TOLERANCE",
    "normalize_token",
    "validate_iso_date",
    "validate_document_type",
    "validate_custody",
    "validate_activity",
    "validate_document",
    "retention_end",
    "assess_document",
    "absent_minimum_types",
    "above_minimum_types",
    "minimum_set_completeness",
    "assess_documentation_file",
]

# The documents a class 3 commercial part activity always keeps. The set is
# deliberately short: at the lowest assurance level the file proves what was
# bought, what arrived, what went wrong and where the part ended up.
MINIMUM_DOCUMENTS = (
    "procurement-specification",
    "incoming-inspection-record",
    "as-built-parts-list",
    "nonconformance-and-alert-record",
    "traceability-record",
)

# Documents a class 3 file may also carry. Permitted, never required, and
# never a substitute for a missing minimum document.
ABOVE_MINIMUM_DOCUMENTS = (
    "evaluation-report",
    "screening-report",
    "lot-acceptance-report",
    "destructive-physical-analysis-report",
    "radiation-verification-report",
    "construction-analysis-report",
)

RECOGNIZED_DOCUMENTS = MINIMUM_DOCUMENTS + ABOVE_MINIMUM_DOCUMENTS

# Who physically holds the document, and whether the project can get it.
CUSTODY_MODES = (
    "project-held",
    "supplier-held-with-access",
    "supplier-held-no-access",
)

# Custody modes from which the project can actually produce the document.
PROJECT_REACHABLE_CUSTODY = ("project-held", "supplier-held-with-access")

# Whole years a class 3 document is kept for unless the project declares more.
DEFAULT_RETENTION_FLOOR_YEARS = 2

# Completeness is a quotient of two counts; a full file must not fail on
# representation alone.
COMPLETENESS_TOLERANCE = 1e-9


def _require_text(value, label):
    """Return a non-blank text field, raising on anything else."""
    if not isinstance(value, str):
        raise ValueError("%s must be a string, got %r" % (label, type(value).__name__))
    text = value.strip()
    if not text:
        raise ValueError("%s must not be blank" % label)
    return text


def _positive_int(value, label):
    """Return a strictly positive whole number."""
    if not isinstance(value, int) or isinstance(value, bool):
        raise ValueError("%s must be a whole number, got %r" % (label, value))
    if value < 1:
        raise ValueError("%s must be at least 1, got %d" % (label, value))
    return value


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


def validate_document_type(value):
    """Return the validated document type token."""
    token = normalize_token(value, "document type")
    if token not in RECOGNIZED_DOCUMENTS:
        raise ValueError(
            "document type '%s' is not recognized; expected one of %s"
            % (token, ", ".join(RECOGNIZED_DOCUMENTS))
        )
    return token


def validate_custody(value):
    """Return the validated custody mode token."""
    token = normalize_token(value, "custody")
    if token not in CUSTODY_MODES:
        raise ValueError(
            "custody '%s' is not recognized; expected one of %s"
            % (token, ", ".join(CUSTODY_MODES))
        )
    return token


def validate_activity(activity):
    """Return the validated identity of the activity the file belongs to."""
    if not isinstance(activity, dict):
        raise ValueError("activity must be a mapping")
    for key in ("part_number", "supplier", "project"):
        if key not in activity:
            raise ValueError("activity missing required key '%s'" % key)
    return {
        "part_number": _require_text(activity["part_number"], "part_number"),
        "supplier": _require_text(activity["supplier"], "supplier"),
        "project": _require_text(activity["project"], "project"),
    }


def validate_document(document):
    """Return one validated document entry from the kept file."""
    if not isinstance(document, dict):
        raise ValueError("each document must be a mapping")
    for key in (
        "document_type",
        "identifier",
        "issue",
        "date",
        "custody",
        "retention_years",
    ):
        if key not in document:
            raise ValueError("document missing required key '%s'" % key)
    covered = document.get("covers_part_numbers", [])
    if covered is None:
        covered = []
    if not isinstance(covered, (list, tuple)):
        raise ValueError("covers_part_numbers must be a sequence")
    parts = []
    for index, value in enumerate(covered):
        part_number = _require_text(value, "covers_part_numbers[%d]" % index)
        if part_number in parts:
            raise ValueError("part '%s' is listed twice on one document" % part_number)
        parts.append(part_number)
    access = document.get("access_reference")
    if access is not None:
        access = _require_text(access, "access_reference")
    return {
        "document_type": validate_document_type(document["document_type"]),
        "identifier": _require_text(document["identifier"], "identifier"),
        "issue": _require_text(document["issue"], "issue"),
        "date": validate_iso_date(document["date"], "document date"),
        "custody": validate_custody(document["custody"]),
        "access_reference": access,
        "retention_years": _positive_int(document["retention_years"], "retention_years"),
        "covers_part_numbers": parts,
    }


def retention_end(document_date, retention_years):
    """Return the day a kept document may first be discarded.

    Whole-year arithmetic keeps this exact: the end day is the same calendar
    day a number of years later, with a 29 February start falling back to
    28 February in a year that has no 29th.
    """
    start = validate_iso_date(document_date, "document date")
    years = _positive_int(retention_years, "retention_years")
    year = start.year + years
    day = start.day
    try:
        return datetime.date(year, start.month, day)
    except ValueError:
        return datetime.date(year, start.month, day - 1)


def assess_document(document, floor_years=None, required_until=None):
    """Return one document entry carrying its retention end and its findings."""
    entry = validate_document(document)
    floor = (
        DEFAULT_RETENTION_FLOOR_YEARS
        if floor_years is None
        else _positive_int(floor_years, "retention floor")
    )
    findings = []
    is_minimum = entry["document_type"] in MINIMUM_DOCUMENTS
    reachable = entry["custody"] in PROJECT_REACHABLE_CUSTODY
    if is_minimum and not reachable:
        findings.append(
            "minimum document '%s' is held by the supplier with no access "
            "commitment, so the project cannot produce it" % entry["identifier"]
        )
    if (
        entry["custody"] == "supplier-held-with-access"
        and not entry["access_reference"]
    ):
        findings.append(
            "document '%s' relies on supplier access with no access reference "
            "naming the clause that grants it" % entry["identifier"]
        )
    if entry["retention_years"] < floor:
        findings.append(
            "document '%s' is kept %d year(s), short of the %d-year floor"
            % (entry["identifier"], entry["retention_years"], floor)
        )
    end = retention_end(entry["date"], entry["retention_years"])
    horizon = None
    reaches_horizon = True
    if required_until is not None:
        horizon = validate_iso_date(required_until, "required_retention_until")
        reaches_horizon = end >= horizon
        if not reaches_horizon:
            findings.append(
                "document '%s' may be discarded on %s, before the required %s"
                % (entry["identifier"], end.isoformat(), horizon.isoformat())
            )
    if is_minimum and not entry["covers_part_numbers"]:
        findings.append(
            "minimum document '%s' names no part number it covers"
            % entry["identifier"]
        )
    entry["is_minimum"] = is_minimum
    entry["project_reachable"] = reachable
    entry["retention_floor_years"] = floor
    entry["retention_end"] = end
    entry["required_retention_until"] = horizon
    entry["reaches_horizon"] = reaches_horizon
    entry["findings"] = findings
    entry["acceptable"] = not findings
    return entry


def _present_tokens(present_types):
    """Return the validated set of document types offered by a file."""
    if not isinstance(present_types, (list, tuple, set, frozenset)):
        raise ValueError("present_types must be a collection")
    present = set()
    for value in present_types:
        present.add(validate_document_type(value))
    return present


def absent_minimum_types(present_types):
    """Return the class 3 minimum document types the file does not carry."""
    present = _present_tokens(present_types)
    return [t for t in MINIMUM_DOCUMENTS if t not in present]


def above_minimum_types(present_types):
    """Return the permitted types the file carries beyond the minimum set."""
    present = _present_tokens(present_types)
    return [t for t in ABOVE_MINIMUM_DOCUMENTS if t in present]


def minimum_set_completeness(present_types):
    """Return the fraction of the class 3 minimum set the file carries."""
    absent = absent_minimum_types(present_types)
    return (len(MINIMUM_DOCUMENTS) - len(absent)) / float(len(MINIMUM_DOCUMENTS))


def assess_documentation_file(kept_file):
    """Run the full clause 6.7 assessment of one class 3 documentation file.

    kept_file keys: activity, documents, and optionally
    retention_floor_years and required_retention_until.
    """
    if not isinstance(kept_file, dict):
        raise ValueError("kept_file must be a mapping")
    for key in ("activity", "documents"):
        if key not in kept_file:
            raise ValueError("kept_file missing required key '%s'" % key)

    activity = validate_activity(kept_file["activity"])
    documents = kept_file["documents"]
    if not isinstance(documents, (list, tuple)) or not documents:
        raise ValueError("documents must be a non-empty sequence")

    floor = kept_file.get("retention_floor_years")
    horizon = kept_file.get("required_retention_until")

    entries = []
    findings = []
    seen = set()
    for document in documents:
        entry = assess_document(document, floor, horizon)
        if entry["document_type"] in seen:
            raise ValueError(
                "document type '%s' is declared twice in the file"
                % entry["document_type"]
            )
        seen.add(entry["document_type"])
        entries.append(entry)
        findings.extend(entry["findings"])

    present = [e["document_type"] for e in entries]
    absent = absent_minimum_types(present)
    for document_type in absent:
        findings.append(
            "minimum document '%s' is not in the kept file" % document_type
        )

    unreachable = [
        e["document_type"]
        for e in entries
        if e["is_minimum"] and not e["project_reachable"]
    ]
    reachable_minimum = [
        t for t in present if t in MINIMUM_DOCUMENTS and t not in unreachable
    ]

    completeness = minimum_set_completeness(present)
    effective = minimum_set_completeness(reachable_minimum)
    complete = math.isclose(
        completeness, 1.0, rel_tol=0.0, abs_tol=COMPLETENESS_TOLERANCE
    )
    effectively_complete = math.isclose(
        effective, 1.0, rel_tol=0.0, abs_tol=COMPLETENESS_TOLERANCE
    )

    above = above_minimum_types(present)

    return {
        "activity": activity,
        "documents": entries,
        "absent_minimum_types": absent,
        "above_minimum_types": above,
        "unreachable_minimum_types": unreachable,
        "completeness": completeness,
        "effective_completeness": effective,
        "minimum_set_complete": complete,
        "effectively_complete": effectively_complete,
        "fit_to_keep": not findings,
        "findings": findings,
    }
