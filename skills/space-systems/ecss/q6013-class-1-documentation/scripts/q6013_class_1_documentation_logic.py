"""Record-package assessment for class 1 commercial EEE part activities.

Anchor: ECSS-Q-ST-60-13C clause 4.7 (the records and reports produced and
retained for commercial part activities carried out at the highest assurance
level). Paraphrased into an implementable procedure; no standard text is
reproduced.

Procedure implemented here
--------------------------
1. Validate the activity the package belongs to: the part number it covers,
   the lot identifier behind it and the project retaining it.
2. Validate every record: a recognized record type, an identifier, an issue, a
   date, an approving authority, a whole-year retention period and the part
   numbers the record covers. Reject a record type declared twice.
3. Compare the mandatory record set with the types present and name every
   report the package never produced, then express the result as a
   completeness fraction judged at unity under a named tolerance.
4. Derive each record's retention end from its own date and its declared
   retention in whole years, and compare that end with the horizon the project
   has to reach. Whole-year arithmetic on dates keeps the comparison exact.
5. Reconcile record coverage against the as-built parts list in both
   directions: a listed part no record covers, and a covered part the list
   does not carry.
6. Return the per-record entries, the absent types, the completeness fraction
   and a verdict carrying every finding.
"""

import datetime
import math

__all__ = [
    "MANDATORY_RECORDS",
    "OPTIONAL_RECORDS",
    "RECOGNIZED_RECORDS",
    "DEFAULT_RETENTION_FLOOR_YEARS",
    "COMPLETENESS_TOLERANCE",
    "normalize_token",
    "validate_activity",
    "validate_iso_date",
    "validate_record_type",
    "validate_record",
    "retention_end",
    "assess_record",
    "absent_record_types",
    "package_completeness",
    "reconcile_part_coverage",
    "assess_record_package",
]

# The reports a class 1 commercial part activity has to be able to produce.
MANDATORY_RECORDS = (
    "part-approval-record",
    "procurement-specification",
    "evaluation-report",
    "incoming-inspection-report",
    "screening-report",
    "lot-acceptance-report",
    "radiation-verification-report",
    "nonconformance-and-alert-record",
    "as-built-parts-list",
    "traceability-record",
)

# Records a package may also carry without being required to.
OPTIONAL_RECORDS = (
    "construction-analysis-report",
    "destructive-physical-analysis-report",
    "derating-analysis-report",
)

RECOGNIZED_RECORDS = MANDATORY_RECORDS + OPTIONAL_RECORDS

# Whole years a record is retained for unless the project declares longer.
DEFAULT_RETENTION_FLOOR_YEARS = 10

# Completeness is a quotient of two counts; a full package must not fail on
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
    """Return a strictly positive integer."""
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


def validate_record_type(value):
    """Return the validated record type token."""
    token = normalize_token(value, "record type")
    if token not in RECOGNIZED_RECORDS:
        raise ValueError(
            "record type '%s' is not recognized; expected one of %s"
            % (token, ", ".join(RECOGNIZED_RECORDS))
        )
    return token


def validate_activity(activity):
    """Return the validated identity of the activity the package belongs to."""
    if not isinstance(activity, dict):
        raise ValueError("activity must be a mapping")
    for key in ("part_number", "lot_identifier", "project"):
        if key not in activity:
            raise ValueError("activity missing required key '%s'" % key)
    return {
        "part_number": _require_text(activity["part_number"], "part_number"),
        "lot_identifier": _require_text(activity["lot_identifier"], "lot_identifier"),
        "project": _require_text(activity["project"], "project"),
    }


def validate_record(record):
    """Return one validated record entry from the package."""
    if not isinstance(record, dict):
        raise ValueError("each record must be a mapping")
    for key in (
        "record_type",
        "identifier",
        "issue",
        "date",
        "approved_by",
        "retention_years",
    ):
        if key not in record:
            raise ValueError("record missing required key '%s'" % key)
    covered = record.get("covers_part_numbers", [])
    if covered is None:
        covered = []
    if not isinstance(covered, (list, tuple)):
        raise ValueError("covers_part_numbers must be a sequence")
    parts = []
    for index, value in enumerate(covered):
        part_number = _require_text(value, "covers_part_numbers[%d]" % index)
        if part_number in parts:
            raise ValueError(
                "part '%s' is listed twice on one record" % part_number
            )
        parts.append(part_number)
    return {
        "record_type": validate_record_type(record["record_type"]),
        "identifier": _require_text(record["identifier"], "identifier"),
        "issue": _require_text(record["issue"], "issue"),
        "date": validate_iso_date(record["date"], "record date"),
        "approved_by": _require_text(record["approved_by"], "approved_by"),
        "retention_years": _positive_int(record["retention_years"], "retention_years"),
        "covers_part_numbers": parts,
    }


def retention_end(record_date, retention_years):
    """Return the day a record may first be discarded.

    Whole-year arithmetic keeps this exact: the end day is the same calendar
    day a number of years later, with a 29 February start falling back to
    28 February in a year that has no 29th.
    """
    start = validate_iso_date(record_date, "record date")
    years = _positive_int(retention_years, "retention_years")
    year = start.year + years
    day = start.day
    try:
        return datetime.date(year, start.month, day)
    except ValueError:
        return datetime.date(year, start.month, day - 1)


def assess_record(record, floor_years=None, required_until=None):
    """Return one record entry carrying its retention end and its findings."""
    entry = validate_record(record)
    floor = (
        DEFAULT_RETENTION_FLOOR_YEARS
        if floor_years is None
        else _positive_int(floor_years, "retention floor")
    )
    findings = []
    if entry["retention_years"] < floor:
        findings.append(
            "record '%s' is retained %d year(s), short of the %d-year floor"
            % (entry["identifier"], entry["retention_years"], floor)
        )
    end = retention_end(entry["date"], entry["retention_years"])
    reaches_horizon = True
    horizon = None
    if required_until is not None:
        horizon = validate_iso_date(required_until, "required_retention_until")
        reaches_horizon = end >= horizon
        if not reaches_horizon:
            findings.append(
                "record '%s' may be discarded on %s, before the required %s"
                % (entry["identifier"], end.isoformat(), horizon.isoformat())
            )
    if not entry["covers_part_numbers"]:
        findings.append(
            "record '%s' names no part number it covers" % entry["identifier"]
        )
    entry["retention_floor_years"] = floor
    entry["retention_end"] = end
    entry["required_retention_until"] = horizon
    entry["reaches_horizon"] = reaches_horizon
    entry["findings"] = findings
    entry["acceptable"] = not findings
    return entry


def absent_record_types(present_types):
    """Return the mandatory record types the package does not carry."""
    if not isinstance(present_types, (list, tuple, set, frozenset)):
        raise ValueError("present_types must be a collection")
    present = set()
    for value in present_types:
        present.add(validate_record_type(value))
    return [t for t in MANDATORY_RECORDS if t not in present]


def package_completeness(present_types):
    """Return the fraction of the mandatory record set the package carries."""
    absent = absent_record_types(present_types)
    return (len(MANDATORY_RECORDS) - len(absent)) / float(len(MANDATORY_RECORDS))


def reconcile_part_coverage(parts_list, entries):
    """Return the two-way mismatch between the parts list and record coverage."""
    if not isinstance(parts_list, (list, tuple)) or not parts_list:
        raise ValueError("parts_list must be a non-empty sequence")
    listed = []
    for index, value in enumerate(parts_list):
        part_number = _require_text(value, "parts_list[%d]" % index)
        if part_number in listed:
            raise ValueError("part '%s' appears twice on the parts list" % part_number)
        listed.append(part_number)
    if not isinstance(entries, (list, tuple)):
        raise ValueError("entries must be a sequence")
    covered = []
    for entry in entries:
        if not isinstance(entry, dict) or "covers_part_numbers" not in entry:
            raise ValueError("each entry must be a validated record mapping")
        for part_number in entry["covers_part_numbers"]:
            if part_number not in covered:
                covered.append(part_number)
    uncovered = [p for p in listed if p not in covered]
    unlisted = [p for p in covered if p not in listed]
    return {"listed": listed, "covered": covered,
            "uncovered_parts": uncovered, "unlisted_parts": unlisted}


def assess_record_package(package):
    """Run the full clause 4.7 assessment of one retained record package.

    package keys: activity, parts_list, records, and optionally
    retention_floor_years and required_retention_until.
    """
    if not isinstance(package, dict):
        raise ValueError("package must be a mapping")
    for key in ("activity", "parts_list", "records"):
        if key not in package:
            raise ValueError("package missing required key '%s'" % key)

    activity = validate_activity(package["activity"])
    records = package["records"]
    if not isinstance(records, (list, tuple)) or not records:
        raise ValueError("records must be a non-empty sequence")

    floor = package.get("retention_floor_years")
    horizon = package.get("required_retention_until")

    entries = []
    findings = []
    seen = set()
    for record in records:
        entry = assess_record(record, floor, horizon)
        if entry["record_type"] in seen:
            raise ValueError(
                "record type '%s' is declared twice in the package"
                % entry["record_type"]
            )
        seen.add(entry["record_type"])
        entries.append(entry)
        findings.extend(entry["findings"])

    absent = absent_record_types([e["record_type"] for e in entries])
    for record_type in absent:
        findings.append("mandatory record '%s' is not in the package" % record_type)

    completeness = package_completeness([e["record_type"] for e in entries])
    complete = math.isclose(
        completeness, 1.0, rel_tol=0.0, abs_tol=COMPLETENESS_TOLERANCE
    )

    coverage = reconcile_part_coverage(package["parts_list"], entries)
    for part_number in coverage["uncovered_parts"]:
        findings.append(
            "part '%s' on the as-built list has no record covering it" % part_number
        )
    for part_number in coverage["unlisted_parts"]:
        findings.append(
            "record coverage names part '%s', which the as-built list does not carry"
            % part_number
        )

    return {
        "activity": activity,
        "records": entries,
        "absent_record_types": absent,
        "completeness": completeness,
        "package_complete": complete,
        "coverage": coverage,
        "fit_to_retain": not findings,
        "findings": findings,
    }
