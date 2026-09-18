"""Logbook cover page as the standard record header.

Anchor: ECSS-Q-ST-20C Annex E (informative), the worked logbook cover page.
The example is used here as the house header format for the record whose
content Annex C fixes: the same fields, in the same order, on every logbook so
a reviewer opening any unit's book finds the identification in the same place.
Paraphrased into an implementable procedure; no standard text is reproduced.

Procedure implemented here
--------------------------
1. Hold the cover field order the example fixes, and which fields are
   mandatory on every cover.
2. Validate a submitted cover: nothing blank, the issue a positive integer,
   the period dates ISO days the right way round, and the sheet numbering
   inside its own total.
3. Render the cover deterministically, labels aligned to one column so the
   sheet is the same shape whoever fills it.
4. Compute the sheet count the entry count actually needs at the lines-per-
   sheet the book is ruled for.
5. Cross-check the cover against the entries it heads: same serial number,
   every entry date inside the declared period, and a declared sheet total
   that matches the computed one.
"""

from datetime import date

__all__ = [
    "COVER_FIELDS",
    "MANDATORY_FIELDS",
    "DEFAULT_LINES_PER_SHEET",
    "normalise_identifier",
    "parse_day",
    "validate_cover",
    "render_cover",
    "sheet_count",
    "cover_body_findings",
    "assess_cover_page",
]

# The cover in the order the worked example prints it.
COVER_FIELDS = (
    "project",
    "item_name",
    "part_number",
    "serial_number",
    "manufacturer",
    "logbook_number",
    "issue",
    "period_from",
    "period_to",
    "sheet_number",
    "sheet_total",
    "custodian",
)

# Fields that make the cover an identification rather than a decoration.
MANDATORY_FIELDS = (
    "project",
    "item_name",
    "part_number",
    "serial_number",
    "manufacturer",
    "logbook_number",
    "issue",
    "period_from",
    "period_to",
    "sheet_number",
    "sheet_total",
)

# How many entry lines one ruled sheet of the book holds.
DEFAULT_LINES_PER_SHEET = 20

# Fields rendered as something other than a plain identifier.
_INTEGER_FIELDS = ("issue", "sheet_number", "sheet_total")
_DATE_FIELDS = ("period_from", "period_to")


def normalise_identifier(value, label):
    """Return a trimmed lowercase identifier; raise on anything else."""
    if not isinstance(value, str):
        raise ValueError("%s must be a string, got %r" % (label, value))
    text = value.strip().lower()
    if not text:
        raise ValueError("%s must not be empty" % label)
    return text


def parse_day(value, label):
    """Return an ISO date; raise on anything that is not one."""
    if isinstance(value, date):
        return value
    if not isinstance(value, str):
        raise ValueError("%s must be an ISO date string, got %r" % (label, value))
    try:
        return date.fromisoformat(value.strip())
    except ValueError:
        raise ValueError("%s must be an ISO date (YYYY-MM-DD), got %r" % (label, value))


def _positive_integer(value, label):
    """Return a positive integer; raise on anything else."""
    if isinstance(value, bool) or not isinstance(value, int) or value < 1:
        raise ValueError("%s must be an integer of at least 1, got %r" % (label, value))
    return value


def validate_cover(cover):
    """Return the normalised cover page; raise on a malformed one."""
    if not isinstance(cover, dict):
        raise ValueError("cover must be a mapping")
    unknown = sorted(key for key in cover if key not in COVER_FIELDS)
    if unknown:
        raise ValueError("cover carries fields the header has no place for: %s" % ", ".join(unknown))
    result = {}
    for field in COVER_FIELDS:
        if field not in cover or cover[field] is None:
            result[field] = None
            continue
        if field in _INTEGER_FIELDS:
            result[field] = _positive_integer(cover[field], "cover[%r]" % field)
        elif field in _DATE_FIELDS:
            result[field] = parse_day(cover[field], "cover[%r]" % field)
        else:
            result[field] = normalise_identifier(cover[field], "cover[%r]" % field)
    absent = [field for field in MANDATORY_FIELDS if result[field] is None]
    if absent:
        raise ValueError("cover leaves mandatory fields blank: %s" % ", ".join(absent))
    if result["period_to"] < result["period_from"]:
        raise ValueError(
            "cover period runs from %s to %s, which is backwards"
            % (result["period_from"].isoformat(), result["period_to"].isoformat())
        )
    if result["sheet_number"] > result["sheet_total"]:
        raise ValueError(
            "cover declares sheet %d of %d"
            % (result["sheet_number"], result["sheet_total"])
        )
    return result


def _render_value(field, value):
    """Return the printed form of one cover value."""
    if value is None:
        return "-"
    if field in _DATE_FIELDS:
        return value.isoformat()
    return str(value)


def render_cover(normalised):
    """Return the cover as aligned label and value lines."""
    if not isinstance(normalised, dict):
        raise ValueError("normalised must be the mapping returned by validate_cover")
    width = max(len(field) for field in COVER_FIELDS)
    lines = []
    for field in COVER_FIELDS:
        label = field.replace("_", " ").upper()
        lines.append("%s : %s" % (label.ljust(width), _render_value(field, normalised.get(field))))
    return tuple(lines)


def sheet_count(entry_count, lines_per_sheet=DEFAULT_LINES_PER_SHEET):
    """Return the sheets an entry count needs at the given ruling."""
    if isinstance(entry_count, bool) or not isinstance(entry_count, int) or entry_count < 0:
        raise ValueError("entry_count must be a non-negative integer, got %r" % entry_count)
    if (
        isinstance(lines_per_sheet, bool)
        or not isinstance(lines_per_sheet, int)
        or lines_per_sheet < 1
    ):
        raise ValueError(
            "lines_per_sheet must be an integer of at least 1, got %r" % lines_per_sheet
        )
    if entry_count == 0:
        return 1
    return -(-entry_count // lines_per_sheet)


def cover_body_findings(normalised, entries, lines_per_sheet=DEFAULT_LINES_PER_SHEET):
    """Return findings where the cover disagrees with the entries it heads."""
    if not isinstance(entries, (list, tuple)):
        raise ValueError("entries must be a sequence of logbook entries")
    findings = []
    dates = []
    for index, entry in enumerate(entries):
        if not isinstance(entry, dict):
            raise ValueError("entries[%d] must be a mapping" % index)
        serial = normalise_identifier(
            entry.get("serial_number"), "entries[%d].serial_number" % index
        )
        if serial != normalised["serial_number"]:
            findings.append(
                "entry %d is for serial %s while the cover reads %s"
                % (index + 1, serial, normalised["serial_number"])
            )
        dates.append(parse_day(entry.get("entry_date"), "entries[%d].entry_date" % index))
    for position, day in enumerate(dates, start=1):
        if day < normalised["period_from"]:
            findings.append(
                "entry %d is dated %s, before the cover period opens on %s"
                % (position, day.isoformat(), normalised["period_from"].isoformat())
            )
        elif day > normalised["period_to"]:
            findings.append(
                "entry %d is dated %s, after the cover period closes on %s"
                % (position, day.isoformat(), normalised["period_to"].isoformat())
            )
    needed = sheet_count(len(entries), lines_per_sheet)
    if normalised["sheet_total"] != needed:
        findings.append(
            "the cover declares %d sheet(s) while %d entries need %d"
            % (normalised["sheet_total"], len(entries), needed)
        )
    return findings


def assess_cover_page(cover, entries, lines_per_sheet=DEFAULT_LINES_PER_SHEET):
    """Grade a logbook cover page and the book it heads."""
    normalised = validate_cover(cover)
    findings = cover_body_findings(normalised, entries, lines_per_sheet)
    span = (normalised["period_to"] - normalised["period_from"]).days
    return {
        "serial_number": normalised["serial_number"],
        "issue": normalised["issue"],
        "period_days": span,
        "entry_count": len(entries),
        "sheets_needed": sheet_count(len(entries), lines_per_sheet),
        "rendered": render_cover(normalised),
        "findings": findings,
        "verdict": "cover-conformant" if not findings else "cover-nonconformant",
    }
