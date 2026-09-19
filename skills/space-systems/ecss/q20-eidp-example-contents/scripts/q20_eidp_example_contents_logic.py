"""End item data package contents example as the standard document-set checklist.

Anchor: ECSS-Q-ST-20C Annex G (informative), the worked contents list of the
end item data package. The example is used here as the house checklist for the
assembled package: a fixed order of numbered sections, a slot map saying which
document kind belongs in which section, one tick per line with a document
number and issue, and page ranges that run continuously from the first sheet.
Paraphrased into an implementable procedure; no standard text is reproduced.

Procedure implemented here
--------------------------
1. Hold the section order the worked contents list fixes and which sections
   are mandatory in every package.
2. Normalise the submitted contents lines: one line per document, a section, a
   document number, an issue and a page count on anything ticked.
3. Check each document sits in the section its kind belongs to, using the slot
   map rather than the compiler's judgement.
4. Check the sections appear in the fixed order and that none of the mandatory
   ones is absent.
5. Lay the page ranges out in listed order and check they start at the first
   sheet and run on with no gap and no overlap.
6. Reconcile the declared total page count with the last range, report the
   completion fraction over the ticked lines and return the verdict.
"""

__all__ = [
    "SECTION_ORDER",
    "MANDATORY_SECTIONS",
    "SECTION_SLOTS",
    "FIRST_PAGE",
    "normalise_identifier",
    "section_index",
    "section_for_document",
    "validate_line",
    "validate_contents",
    "order_findings",
    "placement_findings",
    "mandatory_section_findings",
    "page_range_findings",
    "completion_fraction",
    "render_contents",
    "assess_contents_list",
]

# The numbered sections in the order the worked contents list prints them.
SECTION_ORDER = (
    "cover-and-contents",
    "conformity-declarations",
    "configuration-records",
    "acceptance-test-documentation",
    "nonconformance-and-waiver-records",
    "limited-life-and-logbook-records",
    "open-work-and-constraints",
    "handling-and-transport-records",
)

# Sections without which the package does not document a delivery at all.
MANDATORY_SECTIONS = (
    "cover-and-contents",
    "conformity-declarations",
    "configuration-records",
    "acceptance-test-documentation",
)

# Which section each document kind is filed under.
SECTION_SLOTS = {
    "eidp-cover-sheet": "cover-and-contents",
    "eidp-contents-list": "cover-and-contents",
    "certificate-of-conformity": "conformity-declarations",
    "statement-of-compliance": "conformity-declarations",
    "as-built-configuration-list": "configuration-records",
    "part-and-material-list": "configuration-records",
    "serial-number-record": "configuration-records",
    "acceptance-test-procedure": "acceptance-test-documentation",
    "acceptance-test-report": "acceptance-test-documentation",
    "inspection-record": "acceptance-test-documentation",
    "nonconformance-report-list": "nonconformance-and-waiver-records",
    "deviation-and-waiver-list": "nonconformance-and-waiver-records",
    "limited-life-item-list": "limited-life-and-logbook-records",
    "item-logbook": "limited-life-and-logbook-records",
    "open-work-list": "open-work-and-constraints",
    "operating-constraint-note": "open-work-and-constraints",
    "handling-and-storage-instruction": "handling-and-transport-records",
    "transport-record": "handling-and-transport-records",
}

# The contents list itself is sheet one of the package.
FIRST_PAGE = 1


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


def section_index(section):
    """Return the position of a section in the fixed order."""
    key = normalise_identifier(section, "section")
    if key not in SECTION_ORDER:
        raise ValueError(
            "section must be one of %s, got %r" % ("/".join(SECTION_ORDER), section)
        )
    return SECTION_ORDER.index(key)


def section_for_document(document):
    """Return the section a document kind is filed under."""
    key = normalise_identifier(document, "document")
    if key not in SECTION_SLOTS:
        raise ValueError(
            "document kind %r has no section slot in the contents example" % document
        )
    return SECTION_SLOTS[key]


def validate_line(line, index=0):
    """Return one normalised contents line."""
    if not isinstance(line, dict):
        raise ValueError("line[%d] must be a mapping" % index)
    for key in ("document", "section"):
        if key not in line:
            raise ValueError("line[%d] is missing '%s'" % (index, key))
    document = normalise_identifier(line["document"], "line[%d].document" % index)
    section = normalise_identifier(line["section"], "line[%d].section" % index)
    if section not in SECTION_ORDER:
        raise ValueError(
            "line[%d].section %r is not a section of the contents example"
            % (index, section)
        )
    ticked = bool(line.get("ticked", False))
    record = {
        "document": document,
        "section": section,
        "ticked": ticked,
        "document_number": None,
        "issue": None,
        "pages": None,
        "declared_first_page": None,
    }
    if ticked:
        record["document_number"] = normalise_identifier(
            line.get("document_number"), "line[%d].document_number" % index
        )
        record["issue"] = normalise_identifier(
            line.get("issue"), "line[%d].issue" % index
        )
        record["pages"] = _positive_integer(
            line.get("pages"), "line[%d].pages" % index
        )
        if line.get("declared_first_page") is not None:
            record["declared_first_page"] = _positive_integer(
                line["declared_first_page"], "line[%d].declared_first_page" % index
            )
    elif line.get("declared_first_page") is not None:
        raise ValueError(
            "line[%d] is not ticked and cannot carry a tab page" % index
        )
    return record


def validate_contents(lines):
    """Return the normalised contents lines in the order they were listed."""
    if not isinstance(lines, (list, tuple)) or not lines:
        raise ValueError("contents must be a non-empty sequence of lines")
    records = []
    seen = set()
    for index, line in enumerate(lines):
        record = validate_line(line, index)
        if record["document"] in seen:
            raise ValueError("document %r is listed twice" % record["document"])
        seen.add(record["document"])
        records.append(record)
    return records


def order_findings(records):
    """Return findings where the sections do not run in the fixed order."""
    findings = []
    highest = -1
    for record in records:
        position = section_index(record["section"])
        if position < highest:
            findings.append(
                "section %s is listed after %s and belongs before it"
                % (record["section"], SECTION_ORDER[highest])
            )
            continue
        highest = position
    return findings


def placement_findings(records):
    """Return findings where a document is filed under the wrong section."""
    findings = []
    for record in records:
        try:
            expected = section_for_document(record["document"])
        except ValueError:
            findings.append(
                "%s is not a document kind the contents example places"
                % record["document"]
            )
            continue
        if expected != record["section"]:
            findings.append(
                "%s is filed under %s and belongs under %s"
                % (record["document"], record["section"], expected)
            )
    return findings


def mandatory_section_findings(records):
    """Return findings for mandatory sections with no ticked line."""
    filled = {
        record["section"] for record in records if record["ticked"]
    }
    return [
        "mandatory section %s carries no delivered document" % section
        for section in MANDATORY_SECTIONS
        if section not in filled
    ]


def page_range_findings(records):
    """Return the page ranges of the ticked lines and any continuity finding."""
    ranges = []
    findings = []
    next_page = FIRST_PAGE
    for record in records:
        if not record["ticked"]:
            continue
        start = next_page
        end = start + record["pages"] - 1
        ranges.append({
            "document": record["document"],
            "first_page": start,
            "last_page": end,
        })
        next_page = end + 1
    declared = [
        record for record in records
        if record["ticked"] and record.get("declared_first_page") is not None
    ]
    for record in declared:
        match = next(r for r in ranges if r["document"] == record["document"])
        if record["declared_first_page"] != match["first_page"]:
            findings.append(
                "%s is tabbed at page %d and the running count puts it at %d"
                % (record["document"], record["declared_first_page"],
                   match["first_page"])
            )
    return {"ranges": ranges, "total_pages": next_page - 1, "findings": findings}


def completion_fraction(records):
    """Return the fraction of listed lines that carry a delivered document."""
    if not isinstance(records, (list, tuple)) or not records:
        raise ValueError("records must be a non-empty sequence")
    ticked = sum(1 for record in records if record["ticked"])
    return ticked / float(len(records))


def render_contents(records):
    """Return the contents list as deterministic printable lines."""
    rendered = []
    for record in records:
        if record["ticked"]:
            rendered.append(
                "%s | %s | %s issue %s | %d pp"
                % (record["section"], record["document"], record["document_number"],
                   record["issue"], record["pages"])
            )
        else:
            rendered.append(
                "%s | %s | not delivered" % (record["section"], record["document"])
            )
    return rendered


def assess_contents_list(contents, declared_total_pages=None):
    """Grade an assembled contents list against the worked example."""
    records = validate_contents(contents)
    paging = page_range_findings(records)
    findings = []
    findings.extend(order_findings(records))
    findings.extend(placement_findings(records))
    findings.extend(mandatory_section_findings(records))
    findings.extend(paging["findings"])
    open_lines = [record["document"] for record in records if not record["ticked"]]
    if open_lines:
        findings.append(
            "lines listed with no delivered document: %s" % ", ".join(open_lines)
        )
    if declared_total_pages is not None:
        declared = _positive_integer(declared_total_pages, "declared_total_pages")
        if declared != paging["total_pages"]:
            findings.append(
                "cover declares %d pages and the contents list runs to %d"
                % (declared, paging["total_pages"])
            )
    return {
        "line_count": len(records),
        "completion_fraction": completion_fraction(records),
        "page_ranges": paging["ranges"],
        "total_pages": paging["total_pages"],
        "open_lines": open_lines,
        "rendered": render_contents(records),
        "findings": findings,
        "verdict": "contents-list-complete" if not findings else "contents-list-open",
    }
