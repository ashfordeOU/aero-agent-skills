"""Certificate of conformity worked example as the standard sheet format.

Anchor: ECSS-Q-ST-20C Annex H (informative), the worked certificate of
conformity. The example is used here as the house sheet format: a fixed block
order of printed fields, a certificate number built to one pattern, serial
ranges whose arithmetic has to agree with the declared quantity, and an issue
date that cannot sit after the day the sheet is presented. Paraphrased into an
implementable procedure; no standard text is reproduced.

Procedure implemented here
--------------------------
1. Hold the printed block order the worked example fixes and which fields are
   mandatory on every sheet.
2. Validate the submitted sheet: nothing mandatory blank, the quantity a
   positive integer, the issue date an ISO day no later than the presentation
   day.
3. Parse each declared serial range into a prefix, a first and a last serial
   and a width, refusing a mixed prefix, an inverted range or an inconsistent
   zero padding.
4. Check the ranges do not overlap and that the serials they cover add up to
   the declared quantity.
5. Build the certificate number from the contract reference and the sheet
   sequence and compare it with the number printed on the sheet.
6. Render the sheet deterministically in the fixed block order and return the
   findings and the verdict.
"""

import re

__all__ = [
    "BLOCK_ORDER",
    "MANDATORY_FIELDS",
    "SERIAL_RANGE_PATTERN",
    "CERTIFICATE_NUMBER_PATTERN",
    "normalise_identifier",
    "parse_day",
    "parse_serial_range",
    "serial_count",
    "parse_serial_ranges",
    "overlap_findings",
    "quantity_findings",
    "format_certificate_number",
    "number_findings",
    "validate_sheet",
    "date_findings",
    "render_sheet",
    "assess_certificate_sheet",
]

# The printed blocks in the order the worked example lays them out.
BLOCK_ORDER = (
    "certificate_number",
    "supplier_name",
    "contract_reference",
    "item_designation",
    "part_number",
    "serial_ranges",
    "quantity",
    "specification_reference",
    "conformity_statement",
    "issue_date",
    "signatory_name",
    "signatory_function",
)

# Blocks the sheet cannot be presented without.
MANDATORY_FIELDS = (
    "certificate_number",
    "supplier_name",
    "contract_reference",
    "item_designation",
    "part_number",
    "quantity",
    "conformity_statement",
    "issue_date",
    "signatory_name",
    "signatory_function",
)

# A serial range prints as prefix plus a zero-padded number, optionally to a
# second serial of the same prefix and width.
SERIAL_RANGE_PATTERN = re.compile(r"^([a-z0-9\-]*?)(\d+)(?:\s*-\s*([a-z0-9\-]*?)(\d+))?$")

# The certificate number is the contract reference and a four-digit sequence.
CERTIFICATE_NUMBER_PATTERN = "coc-%s-%04d"

_DAY_PATTERN = re.compile(r"^(\d{4})-(\d{2})-(\d{2})$")
_MONTH_LENGTHS = (31, 28, 31, 30, 31, 30, 31, 31, 30, 31, 30, 31)


def normalise_identifier(value, label):
    """Return a trimmed lowercase identifier; raise on anything else."""
    if not isinstance(value, str):
        raise ValueError("%s must be a string, got %r" % (label, value))
    text = value.strip().lower()
    if not text:
        raise ValueError("%s must not be empty" % label)
    return text


def _positive_integer(value, label):
    """Return a positive integer; a float or a boolean is not one."""
    if not isinstance(value, int) or isinstance(value, bool):
        raise ValueError("%s must be an integer, got %r" % (label, value))
    if value <= 0:
        raise ValueError("%s must be positive, got %d" % (label, value))
    return value


def _days_in_month(year, month):
    """Return the length of a month, leap years included."""
    if month != 2:
        return _MONTH_LENGTHS[month - 1]
    leap = (year % 4 == 0 and year % 100 != 0) or year % 400 == 0
    return 29 if leap else 28


def parse_day(value, label):
    """Return an ISO calendar day as a (year, month, day) triple."""
    text = normalise_identifier(value, label)
    match = _DAY_PATTERN.match(text)
    if match is None:
        raise ValueError("%s must be an ISO day, got %r" % (label, value))
    year, month, day = (int(part) for part in match.groups())
    if not 1 <= month <= 12:
        raise ValueError("%s has month %d" % (label, month))
    if not 1 <= day <= _days_in_month(year, month):
        raise ValueError("%s has day %d in month %d" % (label, day, month))
    return (year, month, day)


def parse_serial_range(value, label="serial_range"):
    """Return one serial range as prefix, first, last and printed width."""
    text = normalise_identifier(value, label)
    match = SERIAL_RANGE_PATTERN.match(text)
    if match is None:
        raise ValueError("%s %r is not a serial or a serial range" % (label, value))
    prefix, first_digits, second_prefix, second_digits = match.groups()
    first = int(first_digits)
    width = len(first_digits)
    if second_digits is None:
        return {"prefix": prefix, "first": first, "last": first, "width": width}
    if second_prefix and second_prefix != prefix:
        raise ValueError(
            "%s %r mixes the prefixes %r and %r" % (label, value, prefix, second_prefix)
        )
    if len(second_digits) != width:
        raise ValueError(
            "%s %r pads its two serials to different widths" % (label, value)
        )
    last = int(second_digits)
    if last < first:
        raise ValueError("%s %r runs backwards" % (label, value))
    return {"prefix": prefix, "first": first, "last": last, "width": width}


def serial_count(entry):
    """Return how many serials one parsed range covers."""
    if not isinstance(entry, dict) or "first" not in entry or "last" not in entry:
        raise ValueError("entry must be a parsed serial range")
    return entry["last"] - entry["first"] + 1


def parse_serial_ranges(values):
    """Return the parsed ranges of a sheet, in the order printed."""
    if not isinstance(values, (list, tuple)) or not values:
        raise ValueError("serial_ranges must be a non-empty sequence")
    return [
        parse_serial_range(value, "serial_ranges[%d]" % index)
        for index, value in enumerate(values)
    ]


def overlap_findings(entries):
    """Return findings where two declared ranges cover the same serial."""
    findings = []
    ordered = sorted(entries, key=lambda e: (e["prefix"], e["first"], e["last"]))
    for earlier, later in zip(ordered, ordered[1:]):
        if earlier["prefix"] != later["prefix"]:
            continue
        if later["first"] <= earlier["last"]:
            findings.append(
                "serial ranges %s%0*d-%0*d and %s%0*d-%0*d overlap"
                % (earlier["prefix"], earlier["width"], earlier["first"],
                   earlier["width"], earlier["last"],
                   later["prefix"], later["width"], later["first"],
                   later["width"], later["last"])
            )
    return findings


def quantity_findings(entries, quantity):
    """Return findings where the serials covered do not match the quantity."""
    declared = _positive_integer(quantity, "quantity")
    covered = sum(serial_count(entry) for entry in entries)
    if covered != declared:
        return [
            "the serial ranges cover %d items and the sheet declares a quantity "
            "of %d" % (covered, declared)
        ]
    return []


def format_certificate_number(contract_reference, sequence):
    """Return the certificate number the pattern gives for a sheet."""
    contract = normalise_identifier(contract_reference, "contract_reference")
    number = _positive_integer(sequence, "sequence")
    if number > 9999:
        raise ValueError("sequence must fit the four-digit field, got %d" % number)
    return CERTIFICATE_NUMBER_PATTERN % (contract, number)


def number_findings(printed, contract_reference, sequence):
    """Return findings where the printed number is not the one the pattern gives."""
    expected = format_certificate_number(contract_reference, sequence)
    actual = normalise_identifier(printed, "certificate_number")
    if actual != expected:
        return ["certificate number %s does not match the pattern %s"
                % (actual, expected)]
    return []


def validate_sheet(sheet):
    """Return the normalised certificate sheet and the blanks it carries."""
    if not isinstance(sheet, dict):
        raise ValueError("sheet must be a mapping")
    record = {}
    blanks = []
    for field in BLOCK_ORDER:
        value = sheet.get(field)
        if field == "quantity":
            if value is None:
                blanks.append(field)
                record[field] = None
                continue
            record[field] = _positive_integer(value, "quantity")
            continue
        if field == "serial_ranges":
            record[field] = None if value is None else parse_serial_ranges(value)
            continue
        if value is None or (isinstance(value, str) and not value.strip()):
            if field in MANDATORY_FIELDS:
                blanks.append(field)
            record[field] = None
            continue
        record[field] = normalise_identifier(value, field)
    if record.get("issue_date") is not None:
        parse_day(record["issue_date"], "issue_date")
    return {"fields": record, "blanks": blanks}


def date_findings(issue_date, presented_on):
    """Return findings where the sheet is dated after the day it is presented."""
    issued = parse_day(issue_date, "issue_date")
    presented = parse_day(presented_on, "presented_on")
    if issued > presented:
        return ["the sheet is dated %s and is presented on %s"
                % (issue_date, presented_on)]
    return []


def render_sheet(record):
    """Return the sheet as deterministic printable lines in block order."""
    if not isinstance(record, dict):
        raise ValueError("record must be the normalised field mapping")
    lines = []
    for field in BLOCK_ORDER:
        value = record.get(field)
        if field == "serial_ranges" and value:
            printed = ", ".join(
                "%s%0*d" % (entry["prefix"], entry["width"], entry["first"])
                if entry["first"] == entry["last"]
                else "%s%0*d-%s%0*d" % (entry["prefix"], entry["width"], entry["first"],
                                        entry["prefix"], entry["width"], entry["last"])
                for entry in value
            )
        elif value is None:
            printed = "<blank>"
        else:
            printed = str(value)
        lines.append("%s: %s" % (field.replace("_", " "), printed))
    return lines


def assess_certificate_sheet(sheet, contract_sequence, presented_on):
    """Grade a certificate sheet against the worked-example format."""
    validated = validate_sheet(sheet)
    record = validated["fields"]
    findings = []
    if validated["blanks"]:
        findings.append(
            "mandatory blocks left blank: %s" % ", ".join(validated["blanks"])
        )
    entries = record.get("serial_ranges")
    if entries:
        findings.extend(overlap_findings(entries))
        if record.get("quantity") is not None:
            findings.extend(quantity_findings(entries, record["quantity"]))
    elif record.get("quantity") is not None and record["quantity"] > 1:
        findings.append(
            "a quantity of %d is declared with no serial range printed"
            % record["quantity"]
        )
    if record.get("certificate_number") and record.get("contract_reference"):
        findings.extend(
            number_findings(record["certificate_number"],
                            record["contract_reference"], contract_sequence)
        )
    if record.get("issue_date"):
        findings.extend(date_findings(record["issue_date"], presented_on))
    covered = sum(serial_count(entry) for entry in entries) if entries else 0
    return {
        "fields": record,
        "blanks": validated["blanks"],
        "serials_covered": covered,
        "rendered": render_sheet(record),
        "findings": findings,
        "verdict": "sheet-conforms-to-format" if not findings else "sheet-defective",
    }
