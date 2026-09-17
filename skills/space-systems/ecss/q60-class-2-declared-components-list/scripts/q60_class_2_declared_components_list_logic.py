"""Editable declared components list issued per Class 2 equipment item.

Anchor: ECSS-Q-ST-60C clause 5.1.4 (an editable declared components list is
issued for each Class 2 equipment item). Paraphrased into an implementable
procedure; no standard text is reproduced.

Procedure implemented here
--------------------------
1. Validate the build and select the items this clause raises the obligation
   for. An item of another reliability class is outside the obligation and is
   counted neither as covered nor as a shortfall.
2. Decide editability from the form the file was issued in, not from what it
   says. A source spreadsheet, a database export and a structured text export
   can be revised; a flattened print, a scan and a locked document cannot,
   whatever the words inside them are.
3. Grade the list line by line. A line is the unit a procurement or a
   nonconformance decision is taken on, so the mandatory fields are counted
   per line and the mean line completeness is reported beside the deficient
   line references themselves.
4. Compare the revision the list was issued against with the revision the
   item is currently built to, keeping a list behind the build apart from one
   raised against a standard the item has not reached.
5. Age every parts board decision that has to reach the list against a
   declared response time, separating those still open from those that
   landed late, and keep the slowest incorporation.
6. Weight the accepted items by installed part count, compare the resulting
   coverage with the required level, and return one issue verdict.
"""

import math

__all__ = [
    "COVERAGE_TOLERANCE",
    "FILE_FORMS",
    "MANDATORY_LINE_FIELDS",
    "MANDATORY_ISSUE_ATTRIBUTES",
    "OBLIGED_RELIABILITY_CLASS",
    "validate_item_id",
    "form_is_editable",
    "line_completeness",
    "issue_line_completeness",
    "revision_alignment",
    "obliged_items",
    "evaluate_issue",
    "update_latency",
    "item_issue_coverage",
    "assess_declared_components_list",
]

# Coverage and line completeness are ratios of summed integers. An exactly-met
# level can land a few ULPs low; absorb the representation error here rather
# than lowering the level the programme agreed.
COVERAGE_TOLERANCE = 1e-9

# The form the list was issued in -> can the reviewer revise it in place.
FILE_FORMS = {
    "source-spreadsheet": True,
    "database-export": True,
    "structured-text-export": True,
    "revisable-document": True,
    "flattened-print": False,
    "image-scan": False,
    "locked-document": False,
    "paper-copy": False,
}

# The fields a line has to carry before a procurement or nonconformance
# decision can be taken on it.
MANDATORY_LINE_FIELDS = (
    "part_number",
    "manufacturer",
    "procurement_specification",
    "quality_level",
    "quantity",
)

# The attributes without which an issue cannot be assessed at all.
MANDATORY_ISSUE_ATTRIBUTES = (
    "issue_id",
    "item_id",
    "file_form",
    "issued_revision",
    "lines",
)

# The reliability class this clause raises the obligation for.
OBLIGED_RELIABILITY_CLASS = "class-2"

# Disposition -> severity used to rank findings. Lower sorts first.
_SEVERITY = {
    "record-incomplete": 0,
    "unknown-item": 1,
    "duplicate-item-issue": 2,
    "form-not-editable": 3,
    "revision-ahead-of-build": 4,
    "revision-behind-build": 5,
    "line-count-short": 6,
    "line-fields-incomplete": 7,
    "list-not-issued": 8,
    "update-open": 9,
    "update-late": 10,
    "outside-obligation": 11,
    "accepted": 12,
}

_ACCEPTED = "accepted"
_OUTSIDE = "outside-obligation"


def _require_text(value, label):
    """Return a non-blank stripped string, or raise."""
    if not isinstance(value, str):
        raise ValueError("%s must be a string, got %r" % (label, value))
    text = value.strip()
    if not text:
        raise ValueError("%s must not be blank" % label)
    return text


def _require_non_negative_int(value, label):
    """Return a non-negative integer, or raise."""
    if isinstance(value, bool) or not isinstance(value, int):
        raise ValueError("%s must be an integer, got %r" % (label, value))
    if value < 0:
        raise ValueError("%s must not be negative, got %d" % (label, value))
    return value


def _require_positive_int(value, label):
    """Return a strictly positive integer, or raise."""
    value = _require_non_negative_int(value, label)
    if value == 0:
        raise ValueError("%s must be strictly positive" % label)
    return value


def _require_fraction(value, label):
    """Return a real number inside [0, 1], or raise."""
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise ValueError("%s must be a real number" % label)
    number = float(value)
    if not math.isfinite(number) or number < 0.0 or number > 1.0:
        raise ValueError("%s must lie in [0, 1], got %r" % (label, value))
    return number


def _meets(achieved, required):
    """Return True when achieved reaches required within the named tolerance."""
    return achieved > required or math.isclose(
        achieved, required, rel_tol=0.0, abs_tol=COVERAGE_TOLERANCE
    )


def validate_item_id(value):
    """Return the validated identifier of one equipment item."""
    return _require_text(value, "item_id")


def form_is_editable(file_form):
    """Return True when the form the list was issued in can be revised."""
    form = _require_text(file_form, "file_form").lower()
    if form not in FILE_FORMS:
        raise ValueError(
            "unknown file_form %r; known: %s"
            % (file_form, ", ".join(sorted(FILE_FORMS)))
        )
    return FILE_FORMS[form]


def line_completeness(line):
    """Return (missing_fields, completeness_fraction) for one list line."""
    if not isinstance(line, dict):
        raise ValueError("each line must be a mapping, got %r" % (type(line).__name__,))
    missing = []
    for field in MANDATORY_LINE_FIELDS:
        if field not in line:
            missing.append(field)
            continue
        value = line[field]
        if value is None:
            missing.append(field)
        elif isinstance(value, str) and not value.strip():
            missing.append(field)
        elif isinstance(value, bool):
            missing.append(field)
        elif isinstance(value, int) and value <= 0:
            missing.append(field)
    total = len(MANDATORY_LINE_FIELDS)
    return (tuple(missing), (total - len(missing)) / total)


def issue_line_completeness(lines):
    """Return (mean_completeness, deficient_line_references) for one issue."""
    if not isinstance(lines, (list, tuple)) or not lines:
        raise ValueError("an issued list must carry at least one line")
    total = 0.0
    deficient = []
    for position, line in enumerate(lines, start=1):
        missing, fraction = line_completeness(line)
        total += fraction
        if missing:
            reference = line.get("part_number")
            label = (
                reference.strip()
                if isinstance(reference, str) and reference.strip()
                else "line %d" % position
            )
            deficient.append(label)
    return (total / len(lines), tuple(deficient))


def revision_alignment(issued_revision, build_revision):
    """Return how an issue's revision stands against the item's build."""
    issued = _require_non_negative_int(issued_revision, "issued_revision")
    built = _require_non_negative_int(build_revision, "build_revision")
    if issued == built:
        return "aligned"
    if issued < built:
        return "behind-build"
    return "ahead-of-build"


def obliged_items(items):
    """Return the equipment items this clause raises a list obligation for."""
    if not isinstance(items, (list, tuple)) or not items:
        raise ValueError("items must be a non-empty sequence of item mappings")
    obliged = []
    seen = set()
    for item in items:
        if not isinstance(item, dict):
            raise ValueError("each item must be a mapping")
        item_id = validate_item_id(item.get("item_id"))
        if item_id in seen:
            raise ValueError("equipment item %s appears twice in the build" % item_id)
        seen.add(item_id)
        reliability = _require_text(
            item.get("reliability_class"), "reliability_class"
        ).lower()
        _require_non_negative_int(item.get("build_revision"), "build_revision")
        _require_positive_int(item.get("installed_part_count"), "installed_part_count")
        if reliability == OBLIGED_RELIABILITY_CLASS:
            obliged.append(item_id)
    if not obliged:
        raise ValueError(
            "the build carries no %s equipment item" % OBLIGED_RELIABILITY_CLASS
        )
    return tuple(obliged)


def _issue_completeness(issue):
    """Return (missing_attributes, completeness_fraction) for one issue."""
    if not isinstance(issue, dict):
        raise ValueError(
            "each issue must be a mapping, got %r" % (type(issue).__name__,)
        )
    missing = []
    for attribute in MANDATORY_ISSUE_ATTRIBUTES:
        if attribute not in issue:
            missing.append(attribute)
            continue
        value = issue[attribute]
        if value is None:
            missing.append(attribute)
        elif isinstance(value, str) and not value.strip():
            missing.append(attribute)
        elif attribute == "lines" and not value:
            missing.append(attribute)
    total = len(MANDATORY_ISSUE_ATTRIBUTES)
    return (tuple(missing), (total - len(missing)) / total)


def evaluate_issue(issue, item_index, required_line_completeness=1.0, already_seen=()):
    """Return the disposition record of one issued declared components list."""
    if not isinstance(item_index, dict) or not item_index:
        raise ValueError("item_index must be a non-empty mapping of item_id -> item")
    required = _require_fraction(
        required_line_completeness, "required_line_completeness"
    )
    missing, completeness = _issue_completeness(issue)
    raw_label = issue.get("issue_id")
    label = (
        raw_label.strip()
        if isinstance(raw_label, str) and raw_label.strip()
        else "<unlabelled>"
    )
    record = {
        "issue_id": label,
        "item_id": None,
        "missing_attributes": missing,
        "record_completeness": completeness,
        "editable": None,
        "revision_alignment": None,
        "line_count": 0,
        "line_completeness": 0.0,
        "deficient_lines": (),
        "part_count": 0,
        "disposition": "record-incomplete",
        "accepted": False,
    }
    if missing:
        return record

    item_id = validate_item_id(issue["item_id"])
    record["item_id"] = item_id
    if item_id not in item_index:
        record["disposition"] = "unknown-item"
        return record

    item = item_index[item_id]
    reliability = _require_text(
        item.get("reliability_class"), "reliability_class"
    ).lower()
    part_count = _require_positive_int(
        item.get("installed_part_count"), "installed_part_count"
    )
    record["part_count"] = part_count
    if reliability != OBLIGED_RELIABILITY_CLASS:
        record["disposition"] = _OUTSIDE
        return record

    if item_id in already_seen:
        record["disposition"] = "duplicate-item-issue"
        return record

    record["editable"] = form_is_editable(issue["file_form"])
    record["revision_alignment"] = revision_alignment(
        issue["issued_revision"], item.get("build_revision")
    )
    mean, deficient = issue_line_completeness(issue["lines"])
    record["line_count"] = len(issue["lines"])
    record["line_completeness"] = mean
    record["deficient_lines"] = deficient

    if not record["editable"]:
        record["disposition"] = "form-not-editable"
        return record
    if record["revision_alignment"] == "ahead-of-build":
        record["disposition"] = "revision-ahead-of-build"
        return record
    if record["revision_alignment"] == "behind-build":
        record["disposition"] = "revision-behind-build"
        return record
    if record["line_count"] < part_count:
        record["disposition"] = "line-count-short"
        return record
    if not _meets(mean, required):
        record["disposition"] = "line-fields-incomplete"
        return record

    record["disposition"] = _ACCEPTED
    record["accepted"] = True
    return record


def update_latency(decisions, assessment_day, response_days):
    """Return how the board decisions that must reach the list have aged."""
    if not isinstance(decisions, (list, tuple)):
        raise ValueError("decisions must be a sequence of decision mappings")
    today = _require_non_negative_int(assessment_day, "assessment_day")
    window = _require_non_negative_int(response_days, "update_response_days")
    open_items = []
    late_items = []
    slowest = None
    seen = set()
    for decision in decisions:
        if not isinstance(decision, dict):
            raise ValueError("each decision must be a mapping")
        reference = _require_text(decision.get("decision_id"), "decision_id")
        if reference in seen:
            raise ValueError("board decision %s appears twice" % reference)
        seen.add(reference)
        raised = _require_non_negative_int(decision.get("decision_day"), "decision_day")
        if raised > today:
            raise ValueError(
                "decision %s is dated after the assessment day" % reference
            )
        landed = decision.get("incorporated_day")
        if landed is None:
            waited = today - raised
            if waited > window:
                open_items.append((reference, waited))
            continue
        landed = _require_non_negative_int(landed, "incorporated_day")
        if landed < raised:
            raise ValueError(
                "decision %s was incorporated before it was taken" % reference
            )
        took = landed - raised
        if slowest is None or took > slowest[1]:
            slowest = (reference, took)
        if took > window:
            late_items.append((reference, took))
    return {
        "open_past_response": tuple(sorted(open_items)),
        "late_but_incorporated": tuple(sorted(late_items)),
        "slowest_incorporation": slowest,
    }


def item_issue_coverage(records, item_index, obliged):
    """Return the obliged part count sitting behind an accepted issue."""
    if not isinstance(records, (list, tuple)):
        raise ValueError("records must be a sequence of issue records")
    if not isinstance(obliged, (list, tuple)) or not obliged:
        raise ValueError("obliged must be a non-empty sequence of item identifiers")
    total = 0
    for item_id in obliged:
        total += _require_positive_int(
            item_index[item_id].get("installed_part_count"), "installed_part_count"
        )
    covered = 0
    closed = set()
    for record in records:
        if not isinstance(record, dict) or "disposition" not in record:
            raise ValueError("each record must be a mapping carrying 'disposition'")
        if record["disposition"] != _ACCEPTED:
            continue
        item_id = record.get("item_id")
        if item_id in closed or item_id not in obliged:
            continue
        closed.add(item_id)
        covered += item_index[item_id]["installed_part_count"]
    if total <= 0:
        raise ValueError("no obliged item carries a usable installed part count")
    return covered / total


def assess_declared_components_list(spec):
    """Run the full clause 5.1.4 declared components list issue assessment.

    spec keys: items (sequence of equipment item mappings), issues (sequence
    of issued list mappings), optional board_decisions, assessment_day,
    update_response_days, required_line_completeness and
    required_item_coverage.
    """
    if not isinstance(spec, dict):
        raise ValueError("spec must be a mapping")
    for key in ("items", "issues"):
        if key not in spec:
            raise ValueError("spec missing required key '%s'" % key)

    items = spec["items"]
    obliged = obliged_items(items)
    item_index = {validate_item_id(item["item_id"]): item for item in items}

    issues = spec["issues"]
    if not isinstance(issues, (list, tuple)):
        raise ValueError("spec['issues'] must be a sequence")

    required_lines = _require_fraction(
        spec.get("required_line_completeness", 1.0), "required_line_completeness"
    )
    required_coverage = _require_fraction(
        spec.get("required_item_coverage", 1.0), "required_item_coverage"
    )
    assessment_day = _require_non_negative_int(
        spec.get("assessment_day", 0), "assessment_day"
    )
    response_days = _require_non_negative_int(
        spec.get("update_response_days", 30), "update_response_days"
    )

    records = []
    closed_items = set()
    seen_issue_ids = set()
    for issue in issues:
        record = evaluate_issue(
            issue, item_index, required_lines, already_seen=closed_items
        )
        if record["issue_id"] != "<unlabelled>":
            if record["issue_id"] in seen_issue_ids:
                raise ValueError("issue %s appears twice" % record["issue_id"])
            seen_issue_ids.add(record["issue_id"])
        # Only an accepted issue closes an item; a corrected reissue after a
        # refused one is a fresh issue, not a duplicate.
        if record["disposition"] == _ACCEPTED and record["item_id"] is not None:
            closed_items.add(record["item_id"])
        records.append(record)

    addressed = {r["item_id"] for r in records if r["item_id"] is not None}
    not_issued = tuple(
        sorted(item_id for item_id in obliged if item_id not in addressed)
    )
    coverage = item_issue_coverage(records, item_index, obliged)
    latency = update_latency(
        spec.get("board_decisions", ()), assessment_day, response_days
    )

    findings = []
    for record in records:
        if record["disposition"] in (_ACCEPTED, _OUTSIDE):
            continue
        findings.append(
            {
                "severity": _SEVERITY.get(record["disposition"], 8),
                "reference": record["issue_id"],
                "disposition": record["disposition"],
                "detail": _finding_detail(record),
            }
        )
    for item_id in not_issued:
        findings.append(
            {
                "severity": _SEVERITY["list-not-issued"],
                "reference": item_id,
                "disposition": "list-not-issued",
                "detail": "no declared components list was issued for this equipment item",
            }
        )
    for reference, waited in latency["open_past_response"]:
        findings.append(
            {
                "severity": _SEVERITY["update-open"],
                "reference": reference,
                "disposition": "update-open",
                "detail": "a board decision has waited %d days to reach the list" % waited,
            }
        )
    for reference, took in latency["late_but_incorporated"]:
        findings.append(
            {
                "severity": _SEVERITY["update-late"],
                "reference": reference,
                "disposition": "update-late",
                "detail": "a board decision took %d days to reach the list" % took,
            }
        )
    findings.sort(key=lambda entry: (entry["severity"], entry["reference"]))

    coverage_met = _meets(coverage, required_coverage)
    issuable = coverage_met and not findings
    return {
        "obliged_items": obliged,
        "records": records,
        "items_without_a_list": not_issued,
        "item_coverage": coverage,
        "required_item_coverage": required_coverage,
        "required_line_completeness": required_lines,
        "update_latency": latency,
        "findings": findings,
        "issuable": issuable,
        "verdict": "lists issuable" if issuable else "lists not issuable",
    }


def _finding_detail(record):
    """Return the human-readable reason one issued list is not accepted."""
    disposition = record["disposition"]
    if disposition == "record-incomplete":
        return "issue lacks %s; no decision can be taken on it" % ", ".join(
            record["missing_attributes"]
        )
    if disposition == "unknown-item":
        return "the issue names an equipment item that is not in the build"
    if disposition == "duplicate-item-issue":
        return "a second list was issued for an item already closed"
    if disposition == "form-not-editable":
        return "the list arrived in a form the reviewer cannot revise in place"
    if disposition == "revision-ahead-of-build":
        return "the list was issued against a build standard the item has not reached"
    if disposition == "revision-behind-build":
        return "the list was issued against a superseded build revision"
    if disposition == "line-count-short":
        return "the list holds fewer lines than the item's installed parts"
    if disposition == "line-fields-incomplete":
        return "lines are short of their mandatory fields: %s" % ", ".join(
            record["deficient_lines"]
        )
    return "issue is outside the obligation this clause raises"
