"""The controlled purchasing specification each Class 3 part type is bought to.

Anchor: ECSS-Q-ST-60C clause 6.3.2 (buying Class 3 parts against a controlled
written purchasing specification held for each part type).

Offline, deterministic, python3 standard library only.

Procedure implemented here (paraphrased, no standard text reproduced):

* One controlled document owns one part type. A library in which two documents
  claim the same type has no answer to "what was this bought to", so the
  duplicate is refused rather than resolved by picking one.
* Not every document cited as a purchasing specification is one. A project
  specification and a manufacturer detail specification are controlled by
  nature; a catalogue datasheet is controlled only when it carries an issue
  identifier and is held under configuration control. An uncontrolled sheet is
  the defect this catches, and it is the commonest one at this category.
* The content the specification owes is scored as a fraction, so a project may
  set the completeness it will buy against, and every absent item is still
  named separately.
* A line raised against a draft, superseded or withdrawn issue is not raised
  against a released one, and neither is a line raised before the issue it
  cites existed.
* The revision the order cites and the revision actually released are compared
  on a family-aware ordering, so B1 is read as later than B and earlier than C.
* Lines and the library are reconciled in both directions.
"""

from __future__ import annotations

import datetime
import re

# Document kinds that can be cited as a purchasing specification.
SPECIFICATION_KINDS = (
    "project-purchasing-specification",
    "manufacturer-detail-specification",
    "catalogue-datasheet",
)

# Kinds that are controlled documents by their nature.
CONTROL_BEARING_KINDS = (
    "project-purchasing-specification",
    "manufacturer-detail-specification",
)

# What a Class 3 purchasing specification still owes.
REQUIRED_SPECIFICATION_CONTENT = (
    "part-type-and-manufacturer-identification",
    "electrical-and-functional-parameters",
    "rated-environmental-limits",
    "marking-and-packaging-requirements",
    "lot-identification-and-traceability-requirement",
    "acceptance-criteria-on-delivery",
)

SPECIFICATION_STATUSES = ("draft", "released", "superseded", "withdrawn")

BUYABLE_STATUS = "released"

TARGET_CATEGORY = "class-3"

# A completeness fraction is a division; a case meant to sit on the project
# minimum can land a few units in the last place away from it.
COMPLETENESS_TOLERANCE = 1e-9

REVISION_RE = re.compile(r"^([A-Z]{1,2})([0-9]{0,2})$")

LINE_STATUSES = (
    "class-3-line-bought-to-a-controlled-specification",
    "class-3-line-specification-defective",
    "class-3-line-has-no-specification",
)


def _require_text(value, label):
    """Return a required non-empty string field or raise."""
    if not isinstance(value, str) or not value.strip():
        raise ValueError("%s must be a non-empty string, got %r" % (label, value))
    return value.strip()


def _require_mapping(value, label):
    """Return a required mapping field or raise."""
    if not isinstance(value, dict):
        raise ValueError("%s must be a mapping, got %r" % (label, type(value).__name__))
    return value


def _require_flag(mapping, key):
    """Return a required boolean field of a mapping or raise."""
    value = mapping.get(key)
    if not isinstance(value, bool):
        raise ValueError("%s must be a boolean, got %r" % (key, value))
    return value


def _require_fraction(value, label):
    """Return a required fraction in the closed unit interval or raise."""
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise ValueError("%s must be a real number, got %r" % (label, value))
    number = float(value)
    if not (0.0 <= number <= 1.0):
        raise ValueError("%s must lie between 0 and 1, got %r" % (label, value))
    return number


def _name_set(raw, allowed, label):
    """Validate a declared collection of names drawn from a closed set."""
    if isinstance(raw, str) or not isinstance(raw, (list, tuple, set, frozenset)):
        raise ValueError("%s must be a list or tuple of names, got %r" % (label, raw))
    names = []
    for name in raw:
        if name not in allowed:
            raise ValueError(
                "unknown %s %r (known: %s)" % (label, name, ", ".join(allowed))
            )
        if name not in names:
            names.append(name)
    return tuple(names)


def parse_iso_date(value, label):
    """Return an ISO calendar date or raise for anything else."""
    text = _require_text(value, label)
    try:
        return datetime.date.fromisoformat(text)
    except ValueError:
        raise ValueError("%s must be an ISO calendar date, got %r" % (label, value))


def revision_key(value, label="revision"):
    """Sortable key for a revision such as A, B, B1 or AA."""
    text = _require_text(value, label).upper()
    match = REVISION_RE.match(text)
    if not match:
        raise ValueError("%s must look like A, B1 or AA, got %r" % (label, value))
    letters, digits = match.group(1), match.group(2)
    letter_rank = 0
    for character in letters:
        letter_rank = letter_rank * 26 + (ord(character) - ord("A") + 1)
    return (letter_rank, int(digits) if digits else 0)


def compare_revisions(left, right):
    """Return -1, 0 or 1 comparing two revisions on the family-aware order."""
    left_key, right_key = revision_key(left), revision_key(right)
    if left_key < right_key:
        return -1
    if left_key > right_key:
        return 1
    return 0


def missing_content(declared_content):
    """Content items the specification never supplied."""
    present = _name_set(
        declared_content, REQUIRED_SPECIFICATION_CONTENT, "specification content"
    )
    return tuple(
        item for item in REQUIRED_SPECIFICATION_CONTENT if item not in present
    )


def content_completeness(declared_content):
    """Fraction of the owed content the specification actually carries."""
    absent = missing_content(declared_content)
    total = len(REQUIRED_SPECIFICATION_CONTENT)
    return float(total - len(absent)) / float(total)


def kind_findings(specification):
    """Findings raised by the kind of document cited as the specification."""
    entry = _require_mapping(specification, "specification")
    kind = entry.get("kind")
    if kind not in SPECIFICATION_KINDS:
        raise ValueError(
            "unknown specification kind %r (known: %s)"
            % (kind, ", ".join(SPECIFICATION_KINDS))
        )
    if kind in CONTROL_BEARING_KINDS:
        return ()
    identifier = entry.get("issue_identifier")
    controlled = _require_flag(entry, "held_under_configuration_control")
    has_identifier = isinstance(identifier, str) and bool(identifier.strip())
    if has_identifier and controlled:
        return ()
    return (
        {
            "finding": "uncontrolled-datasheet-cited-as-a-purchasing-specification",
            "detail": "%s%s"
            % (
                "no issue identifier" if not has_identifier else "issue identifier ok",
                "" if controlled else "; not under configuration control",
            ),
        },
    )


def status_findings(specification, order_date):
    """Findings raised by the issue status the line was raised against."""
    entry = _require_mapping(specification, "specification")
    status = entry.get("status")
    if status not in SPECIFICATION_STATUSES:
        raise ValueError(
            "unknown specification status %r (known: %s)"
            % (status, ", ".join(SPECIFICATION_STATUSES))
        )
    findings = []
    if status != BUYABLE_STATUS:
        findings.append(
            {
                "finding": "line-raised-against-a-specification-not-released",
                "detail": status,
            }
        )
    released_on = parse_iso_date(entry.get("released_on"), "released_on")
    if released_on > order_date:
        findings.append(
            {
                "finding": "specification-released-after-the-order-date",
                "detail": "%s after %s" % (released_on.isoformat(), order_date.isoformat()),
            }
        )
    return tuple(findings)


def revision_findings(cited_revision, specification):
    """Findings raised by the revision the order cites."""
    entry = _require_mapping(specification, "specification")
    released = entry.get("revision")
    order = compare_revisions(cited_revision, released)
    if order == 0:
        return ()
    if order > 0:
        return (
            {
                "finding": "order-cites-a-revision-that-was-never-released",
                "detail": "%s against %s" % (cited_revision, released),
            },
        )
    return (
        {
            "finding": "order-cites-a-superseded-revision",
            "detail": "%s against %s" % (cited_revision, released),
        },
    )


def index_specifications(specifications):
    """Index the specification library by part type, one document per type."""
    if isinstance(specifications, str) or not isinstance(
        specifications, (list, tuple)
    ):
        raise ValueError(
            "specifications must be a list or tuple of mappings, got %r"
            % (specifications,)
        )
    if not specifications:
        raise ValueError("at least one specification is required")
    index = {}
    for raw in specifications:
        entry = _require_mapping(raw, "specification")
        part_type = _require_text(entry.get("part_type"), "part_type")
        _require_text(entry.get("document_id"), "document_id")
        if part_type in index:
            raise ValueError(
                "two documents claim part_type %r; one type has one owner"
                % (part_type,)
            )
        revision_key(entry.get("revision"))
        index[part_type] = entry
    return index


def assess_specified_line(line, index, order_date, minimum_completeness=1.0):
    """Read one ordered line against the specification it was bought to."""
    entry = _require_mapping(line, "line")
    part_type = _require_text(entry.get("part_type"), "part_type")
    minimum = _require_fraction(minimum_completeness, "minimum_content_completeness")
    specification = index.get(part_type)
    if specification is None:
        return {
            "part_type": part_type,
            "status": "class-3-line-has-no-specification",
            "completeness": 0.0,
            "missing_content": list(REQUIRED_SPECIFICATION_CONTENT),
            "findings": [
                {
                    "part_type": part_type,
                    "finding": "part-type-ordered-against-no-purchasing-specification",
                    "detail": part_type,
                }
            ],
            "specified": False,
        }

    findings = []
    findings.extend(kind_findings(specification))
    findings.extend(status_findings(specification, order_date))
    findings.extend(revision_findings(entry.get("cited_revision"), specification))

    absent = missing_content(specification.get("content", []))
    completeness = content_completeness(specification.get("content", []))
    if completeness < minimum - COMPLETENESS_TOLERANCE:
        for item in absent:
            findings.append(
                {
                    "finding": "purchasing-specification-content-missing",
                    "detail": item,
                }
            )
    for finding in findings:
        finding["part_type"] = part_type

    specified = not findings
    return {
        "part_type": part_type,
        "document_id": specification.get("document_id"),
        "status": (
            "class-3-line-bought-to-a-controlled-specification"
            if specified
            else "class-3-line-specification-defective"
        ),
        "completeness": completeness,
        "missing_content": list(absent),
        "findings": findings,
        "specified": specified,
    }


def assess_class_3_purchasing_specifications(order):
    """Judge a Class 3 order against the purchasing specification library."""
    entry = _require_mapping(order, "order")
    order_id = _require_text(entry.get("order_id"), "order_id")
    category = _require_text(entry.get("declared_category"), "declared_category")
    order_date = parse_iso_date(entry.get("order_date"), "order_date")
    index = index_specifications(entry.get("specifications"))
    lines = entry.get("lines")
    if isinstance(lines, str) or not isinstance(lines, (list, tuple)):
        raise ValueError("lines must be a list or tuple of mappings, got %r" % (lines,))
    if not lines:
        raise ValueError("at least one ordered line is required")
    minimum = _require_fraction(
        entry.get("minimum_content_completeness", 1.0),
        "minimum_content_completeness",
    )

    findings = []
    if category != TARGET_CATEGORY:
        findings.append(
            {
                "part_type": "-",
                "finding": "declared-category-is-not-the-one-being-checked",
                "detail": category,
            }
        )

    records = []
    seen = set()
    for line in lines:
        record = assess_specified_line(line, index, order_date, minimum)
        if record["part_type"] in seen:
            raise ValueError("duplicate ordered part_type %r" % (record["part_type"],))
        seen.add(record["part_type"])
        records.append(record)
        findings.extend(record["findings"])

    never_ordered = tuple(
        part_type for part_type in sorted(index) if part_type not in seen
    )
    for part_type in never_ordered:
        findings.append(
            {
                "part_type": part_type,
                "finding": "specification-held-for-a-type-nobody-ordered",
                "detail": part_type,
            }
        )

    specified = [r["part_type"] for r in records if r["specified"]]
    defective = [r["part_type"] for r in records if not r["specified"]]
    return {
        "order_id": order_id,
        "line_records": records,
        "specified_part_types": specified,
        "defective_part_types": defective,
        "specifications_never_ordered": list(never_ordered),
        "specified_fraction": float(len(specified)) / float(len(records)),
        "findings": findings,
        "order_documented": not findings,
    }
