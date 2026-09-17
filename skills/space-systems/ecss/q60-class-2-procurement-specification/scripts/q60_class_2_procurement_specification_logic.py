"""Controlled purchasing specification check for Class 2 EEE part types.

Anchor: ECSS-Q-ST-60C clause 5.3.2 — Class 2 parts are bought against a
controlled written purchasing specification held for each part type.
Paraphrased into an implementable procedure; no standard text is reproduced.

Procedure implemented here
--------------------------
1. Index the specification library by part type. One controlled document owns
   one part type: two documents claiming the same type means the buyer read
   one of them and the other was the requirement that went unmet.
2. Judge each document as a controlled document before judging its content: a
   reference, a revision, a release status and a release date that is not in
   the future relative to the order.
3. Score the mandatory content. A purchasing specification that omits the
   screening regime or the lot acceptance and marking rules is a datasheet
   reprint with a document number on it.
4. Compare the revision the purchase order cites with the revision actually
   released, on a family-aware ordering so numeric and alphabetic revision
   schemes are never silently compared with each other.
5. Report a line bought against a draft, superseded or withdrawn document,
   and a line that cites no specification at all.
6. Reconcile part types on the order against part types in the library, in
   both directions.
7. Report the per-type records, the specified fraction and a verdict carrying
   every finding rather than the first.
"""

import datetime

__all__ = [
    "REQUIRED_SPECIFICATION_CONTENT",
    "SPECIFICATION_STATUSES",
    "BUYABLE_STATUS",
    "COMPLETENESS_TOLERANCE",
    "normalize_token",
    "parse_iso_date",
    "revision_key",
    "compare_revisions",
    "content_completeness",
    "index_specifications",
    "status_findings",
    "revision_findings",
    "assess_specified_line",
    "assess_purchasing_specifications",
]

# The content a controlled purchasing specification owes for a Class 2 part
# type before an order may be raised against it.
REQUIRED_SPECIFICATION_CONTENT = (
    "part-type-identification",
    "electrical-parameter-limits",
    "environmental-and-temperature-limits",
    "screening-requirements",
    "lot-acceptance-and-marking",
    "packaging-and-handling",
    "documentation-deliverables",
)

# Document states a controlled specification can be in.
SPECIFICATION_STATUSES = ("draft", "released", "superseded", "withdrawn")

# The only state an order may be raised against.
BUYABLE_STATUS = "released"

# The completeness score is a ratio of small integers; a score landing on its
# threshold must not be failed on representation alone.
COMPLETENESS_TOLERANCE = 1e-9


def _require_text(value, label):
    """Return a non-blank text field, raising on anything else."""
    if not isinstance(value, str):
        raise ValueError("%s must be a string, got %s" % (label, type(value).__name__))
    text = value.strip()
    if not text:
        raise ValueError("%s must not be blank" % label)
    return text


def _require_mapping(value, label):
    """Return a mapping, raising on anything else."""
    if not isinstance(value, dict):
        raise ValueError("%s must be a mapping" % label)
    return value


def normalize_token(value, label):
    """Return a lower-case hyphenated token from a free-text field."""
    text = _require_text(value, label)
    return "-".join(text.lower().replace("_", " ").replace("-", " ").split())


def parse_iso_date(value, label):
    """Return a date parsed from an ISO calendar string."""
    if isinstance(value, datetime.date) and not isinstance(value, datetime.datetime):
        return value
    text = _require_text(value, label)
    try:
        return datetime.date.fromisoformat(text)
    except ValueError:
        raise ValueError("%s must be an ISO calendar date, got '%s'" % (label, text))


def revision_key(value, label="revision"):
    """Return a family-tagged sort key for a document revision.

    Numeric revisions sort as numbers, alphabetic revisions as letters. The
    family travels with the key so the two schemes are never compared.
    """
    text = _require_text(value, label).strip().upper()
    if text.isdigit():
        return ("numeric", int(text))
    if text.isalpha() and 1 <= len(text) <= 2:
        rank = 0
        for character in text:
            rank = rank * 26 + (ord(character) - ord("A") + 1)
        return ("alphabetic", rank)
    raise ValueError(
        "%s '%s' is neither a numeric nor a one-or-two-letter revision" % (label, text)
    )


def compare_revisions(left, right):
    """Return -1, 0 or 1 comparing two revisions of the same scheme."""
    first = revision_key(left, "cited revision")
    second = revision_key(right, "released revision")
    if first[0] != second[0]:
        raise ValueError(
            "revision '%s' is %s and '%s' is %s; the two schemes are not comparable"
            % (left, first[0], right, second[0])
        )
    if first[1] < second[1]:
        return -1
    if first[1] > second[1]:
        return 1
    return 0


def content_completeness(content):
    """Return the mandatory-content score of a purchasing specification."""
    if not isinstance(content, (list, tuple, set, frozenset)):
        raise ValueError("specification content must be a collection of content tokens")
    held = set()
    for item in content:
        held.add(normalize_token(item, "content entry"))
    missing = [item for item in REQUIRED_SPECIFICATION_CONTENT if item not in held]
    present = len(REQUIRED_SPECIFICATION_CONTENT) - len(missing)
    return {
        "present": present,
        "required": len(REQUIRED_SPECIFICATION_CONTENT),
        "missing": missing,
        "score": present / float(len(REQUIRED_SPECIFICATION_CONTENT)),
    }


def status_findings(specification, order_date):
    """Return the findings raised by the control state of one document."""
    _require_mapping(specification, "specification")
    for key in ("reference", "status", "release_date"):
        if key not in specification:
            raise ValueError("specification missing required key '%s'" % key)
    reference = _require_text(specification["reference"], "specification reference")
    status = normalize_token(specification["status"], "specification status")
    if status not in SPECIFICATION_STATUSES:
        raise ValueError("specification status '%s' is not a known state" % status)
    released = parse_iso_date(specification["release_date"], "release_date")
    on = parse_iso_date(order_date, "order_date")

    findings = []
    if status != BUYABLE_STATUS:
        findings.append(
            "specification '%s' is '%s', so the order was raised against an "
            "uncontrolled issue" % (reference, status)
        )
    if released > on:
        findings.append(
            "specification '%s' was released on %s, after the order date %s"
            % (reference, released.isoformat(), on.isoformat())
        )
    return findings


def revision_findings(cited_revision, specification):
    """Return the findings raised by the revision the order cites."""
    _require_mapping(specification, "specification")
    for key in ("reference", "revision"):
        if key not in specification:
            raise ValueError("specification missing required key '%s'" % key)
    reference = _require_text(specification["reference"], "specification reference")
    released = specification["revision"]
    if cited_revision is None:
        return ["the order cites specification '%s' with no revision" % reference]
    order = compare_revisions(cited_revision, released)
    if order < 0:
        return [
            "the order cites revision '%s' of '%s' where revision '%s' is released"
            % (cited_revision, reference, released)
        ]
    if order > 0:
        return [
            "the order cites revision '%s' of '%s', which is ahead of the released "
            "revision '%s'" % (cited_revision, reference, released)
        ]
    return []


def index_specifications(specifications, order_date):
    """Return the specification library indexed by the part type it owns."""
    if not isinstance(specifications, (list, tuple)) or not specifications:
        raise ValueError("specifications must be a non-empty sequence")
    index = {}
    for position, specification in enumerate(specifications):
        _require_mapping(specification, "specifications[%d]" % position)
        for key in ("part_type", "reference", "revision", "status", "release_date", "content"):
            if key not in specification:
                raise ValueError(
                    "specifications[%d] missing required key '%s'" % (position, key)
                )
        part_type = normalize_token(
            specification["part_type"], "specifications[%d].part_type" % position
        )
        if part_type in index:
            raise ValueError(
                "part type '%s' is owned by two controlled specifications" % part_type
            )
        revision_key(specification["revision"], "specifications[%d].revision" % position)
        record = dict(specification)
        record["part_type"] = part_type
        record["completeness"] = content_completeness(specification["content"])
        record["status_findings"] = status_findings(specification, order_date)
        index[part_type] = record
    return index


def assess_specified_line(line, index, minimum_completeness):
    """Return one ordered-part-type record carrying its findings."""
    _require_mapping(line, "line")
    if "part_type" not in line:
        raise ValueError("line missing required key 'part_type'")
    if not isinstance(minimum_completeness, (int, float)) or isinstance(
        minimum_completeness, bool
    ):
        raise ValueError("minimum_completeness must be a real number")
    threshold = float(minimum_completeness)
    if not 0.0 <= threshold <= 1.0:
        raise ValueError("minimum_completeness must lie in 0..1, got %g" % threshold)

    part_type = normalize_token(line["part_type"], "line part_type")
    if part_type not in index:
        return {
            "part_type": part_type,
            "specified": False,
            "completeness_score": None,
            "findings": [
                "part type '%s' is ordered with no controlled purchasing specification"
                % part_type
            ],
            "acceptable": False,
        }

    specification = index[part_type]
    findings = list(specification["status_findings"])
    findings.extend(revision_findings(line.get("cited_revision"), specification))

    completeness = specification["completeness"]
    if completeness["score"] < threshold - COMPLETENESS_TOLERANCE:
        findings.append(
            "specification '%s' carries %d of %d mandatory content items, short of the "
            "%.3f score required (missing: %s)"
            % (
                specification["reference"],
                completeness["present"],
                completeness["required"],
                threshold,
                ", ".join(completeness["missing"]),
            )
        )

    return {
        "part_type": part_type,
        "specified": True,
        "completeness_score": completeness["score"],
        "missing_content": list(completeness["missing"]),
        "findings": findings,
        "acceptable": not findings,
    }


def assess_purchasing_specifications(order):
    """Run the full clause 5.3.2 purchasing specification assessment.

    order keys: order_reference, order_date, minimum_completeness,
    specifications, lines.
    """
    _require_mapping(order, "order")
    for key in (
        "order_reference",
        "order_date",
        "minimum_completeness",
        "specifications",
        "lines",
    ):
        if key not in order:
            raise ValueError("order missing required key '%s'" % key)

    reference = _require_text(order["order_reference"], "order_reference")
    order_date = parse_iso_date(order["order_date"], "order_date")
    index = index_specifications(order["specifications"], order_date)

    lines = order["lines"]
    if not isinstance(lines, (list, tuple)) or not lines:
        raise ValueError("lines must be a non-empty sequence")

    records = []
    seen = []
    for line in lines:
        record = assess_specified_line(line, index, order["minimum_completeness"])
        if record["part_type"] in seen:
            raise ValueError("part type '%s' appears on two order lines" % record["part_type"])
        seen.append(record["part_type"])
        records.append(record)

    findings = []
    unused = [t for t in sorted(index) if t not in seen]
    for part_type in unused:
        findings.append(
            "controlled specification for part type '%s' is cited by no order line"
            % part_type
        )
    for record in records:
        findings.extend(record["findings"])

    acceptable = [r for r in records if r["acceptable"]]
    return {
        "order_reference": reference,
        "order_date": order_date.isoformat(),
        "lines": records,
        "uncited_specifications": unused,
        "specified_fraction": len(acceptable) / float(len(records)),
        "specifications_controlled": not findings,
        "findings": findings,
    }
