"""The record a board repair has to leave behind it.

Anchor: ECSS-Q-ST-70-28C, documentation clause -- what is written down when a
printed circuit board assembly is repaired or modified: where on the board the
work was done, by what method, with which materials, and what verification was
performed afterwards. Paraphrased into an implementable procedure; no standard
text is reproduced.

Procedure implemented here
--------------------------
1. Score the mandatory header fields that identify the assembly, the
   authorization the work was done under and the person who did it.
2. Test the location for an unambiguous identification. A side of the board
   plus a reference designator or a grid reference locates the work; a
   sentence of prose does not, however descriptive it reads.
3. Test the method against the approved set, and require the revision of the
   procedure that was followed rather than its number alone.
4. Test every material for a designation, a batch identity and a shelf life
   that had not expired on the day the material was used.
5. Test the verification activities actually recorded against the set the
   method requires, and report each one that is missing.
6. Read the dates in order: a repair cannot precede its authorization and a
   verification cannot precede the repair it verifies.
7. Check the retention period the record is held for.
8. Return the audit with every finding grouped by the part of the record it
   came from, plus a completeness score over the check groups.
"""

from datetime import date

__all__ = [
    "REQUIRED_HEADER_FIELDS",
    "APPROVED_METHODS",
    "BOARD_SIDES",
    "REQUIRED_MATERIAL_FIELDS",
    "RETENTION_YEARS",
    "CHECK_GROUPS",
    "parse_record_date",
    "missing_header_fields",
    "location_findings",
    "method_findings",
    "required_verifications",
    "material_findings",
    "verification_findings",
    "chronology_findings",
    "retention_findings",
    "audit_repair_record",
]

# The fields without which the record does not identify what was repaired,
# under whose authority, or by whom.
REQUIRED_HEADER_FIELDS = (
    "assembly-part-number",
    "assembly-serial-number",
    "repair-authorization",
    "operator-identity",
    "procedure-reference",
    "repair-date",
)

# Each approved repair method and the verification activities its record has
# to carry. The set differs by method because the failure each method can
# leave behind differs.
APPROVED_METHODS = {
    "jumper-wire": ("visual", "electrical-continuity", "ionic-cleanliness"),
    "land-rebuild": ("visual", "bond-pull-test", "ionic-cleanliness"),
    "eyelet-insertion": ("visual", "electrical-continuity", "radiographic"),
    "laminate-fill": ("visual", "dielectric-withstand"),
    "coating-touch-up": ("visual", "coating-thickness"),
    "component-replacement": (
        "visual",
        "electrical-continuity",
        "insulation-resistance",
        "ionic-cleanliness",
    ),
}

BOARD_SIDES = ("top", "bottom")

# A material entry that cannot be traced to a batch cannot be traced at all.
REQUIRED_MATERIAL_FIELDS = ("designation", "batch", "expiry-date")

# Years the repair record is kept for after the work.
RETENTION_YEARS = 10

# The parts of the record the audit scores.
CHECK_GROUPS = (
    "header",
    "location",
    "method",
    "materials",
    "verification",
    "chronology",
    "retention",
)


def _require_mapping(value, label):
    if not isinstance(value, dict):
        raise ValueError("%s must be a mapping" % label)
    return value


def _token(value, label):
    if not isinstance(value, str) or not value.strip():
        raise ValueError("%s must be a non-empty string" % label)
    return value.strip().lower()


def parse_record_date(value, label):
    """Return a date from an ISO day string or a date object."""
    if isinstance(value, date):
        return value
    if not isinstance(value, str) or not value.strip():
        raise ValueError("%s must be an ISO date string or a date" % label)
    try:
        return date.fromisoformat(value.strip())
    except ValueError:
        raise ValueError("%s is not an ISO date: %r" % (label, value))


def missing_header_fields(record):
    """Return the mandatory header fields that are absent or blank."""
    _require_mapping(record, "record")
    missing = []
    for field in REQUIRED_HEADER_FIELDS:
        value = record.get(field)
        if value is None:
            missing.append(field)
        elif isinstance(value, str) and not value.strip():
            missing.append(field)
    return missing


def location_findings(location):
    """Report a location that does not identify where on the board work was done."""
    if location is None:
        return ["no repair location recorded"]
    _require_mapping(location, "location")
    findings = []
    side = location.get("side")
    if side is None:
        findings.append("repair location does not say which side of the board")
    else:
        if _token(side, "side") not in BOARD_SIDES:
            findings.append(
                "repair location side '%s' is not one of %s"
                % (_token(side, "side"), ", ".join(BOARD_SIDES))
            )
    designator = location.get("reference-designator")
    grid = location.get("grid")
    has_designator = isinstance(designator, str) and bool(designator.strip())
    has_grid = (
        isinstance(grid, (list, tuple))
        and len(grid) == 2
        and all(isinstance(g, str) and g.strip() for g in grid)
    )
    if grid is not None and not has_grid:
        findings.append("repair location grid must be a (column, row) pair of labels")
    if not has_designator and not has_grid:
        findings.append(
            "repair location gives neither a reference designator nor a grid "
            "reference; prose alone does not locate the work"
        )
    return findings


def method_findings(method, revision=None):
    """Report a method outside the approved set or a procedure with no revision."""
    name = _token(method, "method")
    findings = []
    if name not in APPROVED_METHODS:
        findings.append(
            "repair method '%s' is not in the approved set: %s"
            % (name, ", ".join(sorted(APPROVED_METHODS)))
        )
    if revision is None or (isinstance(revision, str) and not revision.strip()):
        findings.append(
            "procedure revision is not recorded; a procedure number alone does "
            "not say which text was followed"
        )
    return findings


def required_verifications(method):
    """Return the verification activities a method's record has to carry."""
    name = _token(method, "method")
    if name not in APPROVED_METHODS:
        raise ValueError(
            "unknown repair method '%s'; known: %s"
            % (name, ", ".join(sorted(APPROVED_METHODS)))
        )
    return APPROVED_METHODS[name]


def material_findings(materials, repair_day):
    """Report materials with no batch identity or with an expired shelf life."""
    if isinstance(materials, dict) or not isinstance(materials, (list, tuple)):
        raise ValueError("materials must be a sequence of material entries")
    used_on = parse_record_date(repair_day, "repair_date")
    findings = []
    if not materials:
        findings.append("no materials recorded for the repair")
    for index, entry in enumerate(materials):
        _require_mapping(entry, "material entry %d" % index)
        label = entry.get("designation") or "material entry %d" % index
        for field in REQUIRED_MATERIAL_FIELDS:
            value = entry.get(field)
            if value is None or (isinstance(value, str) and not value.strip()):
                findings.append("material '%s' has no %s recorded" % (label, field))
        expiry = entry.get("expiry-date")
        if expiry is not None and not (isinstance(expiry, str) and not expiry.strip()):
            expired_on = parse_record_date(expiry, "expiry-date of '%s'" % label)
            if expired_on < used_on:
                findings.append(
                    "material '%s' expired on %s and was used on %s"
                    % (label, expired_on.isoformat(), used_on.isoformat())
                )
    return findings


def verification_findings(method, performed):
    """Report verification activities the method requires but the record lacks."""
    required = required_verifications(method)
    if isinstance(performed, str) or not isinstance(performed, (list, tuple, set)):
        raise ValueError("performed verifications must be a sequence of tokens")
    done = set(_token(p, "verification activity") for p in performed)
    unknown = sorted(done - set(required))
    findings = [
        "verification '%s' required by a %s repair is not recorded"
        % (activity, _token(method, "method"))
        for activity in required
        if activity not in done
    ]
    for extra in unknown:
        findings.append(
            "verification '%s' is recorded but is not part of a %s repair; check "
            "the method the record names" % (extra, _token(method, "method"))
        )
    return findings


def chronology_findings(authorization_day, repair_day, verification_day):
    """Report dates that do not run authorization, repair, verification."""
    authorised = parse_record_date(authorization_day, "authorization_date")
    repaired = parse_record_date(repair_day, "repair_date")
    verified = parse_record_date(verification_day, "verification_date")
    findings = []
    if repaired < authorised:
        findings.append(
            "the repair on %s precedes its authorization on %s"
            % (repaired.isoformat(), authorised.isoformat())
        )
    if verified < repaired:
        findings.append(
            "the verification on %s precedes the repair on %s it verifies"
            % (verified.isoformat(), repaired.isoformat())
        )
    return findings


def retention_findings(retention_years):
    """Report a retention period shorter than the record has to be kept."""
    if not isinstance(retention_years, (int, float)) or isinstance(retention_years, bool):
        raise ValueError("retention_years must be a number of years")
    years = float(retention_years)
    if years < 0.0:
        raise ValueError("retention_years must be non-negative, got %g" % years)
    if years < RETENTION_YEARS:
        return [
            "record retention of %g years is shorter than the %d years the repair "
            "record is kept for" % (years, RETENTION_YEARS)
        ]
    return []


def audit_repair_record(record):
    """Audit one repair record and return the findings grouped by record part.

    record keys: the mandatory header fields, plus location, repair_method,
    procedure_revision, materials, verifications, authorization_date,
    verification_date and retention_years.
    """
    _require_mapping(record, "record")
    grouped = dict((group, []) for group in CHECK_GROUPS)

    for field in missing_header_fields(record):
        grouped["header"].append("mandatory field '%s' is missing from the record" % field)

    grouped["location"].extend(location_findings(record.get("location")))

    method = record.get("repair_method")
    if method is None:
        grouped["method"].append("no repair method recorded")
    else:
        grouped["method"].extend(method_findings(method, record.get("procedure_revision")))

    repair_day = record.get("repair-date")
    if repair_day is None:
        grouped["materials"].append(
            "materials cannot be checked against a shelf life without a repair date"
        )
    else:
        grouped["materials"].extend(
            material_findings(record.get("materials", ()), repair_day)
        )

    if method is not None and _token(method, "repair_method") in APPROVED_METHODS:
        grouped["verification"].extend(
            verification_findings(method, record.get("verifications", ()))
        )
    else:
        grouped["verification"].append(
            "the required verification set cannot be resolved without an approved method"
        )

    dates = (
        record.get("authorization_date"),
        repair_day,
        record.get("verification_date"),
    )
    if any(d is None for d in dates):
        grouped["chronology"].append(
            "the authorization, repair and verification dates are not all recorded"
        )
    else:
        grouped["chronology"].extend(chronology_findings(*dates))

    grouped["retention"].extend(retention_findings(record.get("retention_years", 0)))

    findings = []
    for group in CHECK_GROUPS:
        findings.extend(grouped[group])
    clean_groups = sum(1 for group in CHECK_GROUPS if not grouped[group])

    return {
        "grouped_findings": grouped,
        "findings": findings,
        "clean_groups": clean_groups,
        "check_groups": len(CHECK_GROUPS),
        "completeness_score": clean_groups / float(len(CHECK_GROUPS)),
        "complete": not findings,
    }
