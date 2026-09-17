"""Editable declared components list issued for each Class 3 equipment item.

Anchor: ECSS-Q-ST-60C clause 6.1.4 (an editable declared components list is
issued for every Class 3 equipment item). Paraphrased into an implementable
procedure; no standard text is reproduced.

Procedure implemented here
--------------------------
1. Validate the build. Every equipment item carries an identifier, a product
   category, the build standard it is currently at, and a strictly positive
   count of the parts it installs.
2. Select the items this clause raises the obligation for. A Class 3 item owes
   a list of its own; an item of another category owes nothing here and must
   sit on neither side of the coverage ratio.
3. Grade each issued file on the fields an acceptance decision cannot be taken
   without, and hold an incomplete record apart from a complete record that
   simply fails a check.
4. Decide editability in two parts, because one alone is not enough: the
   container has to be revisable in place, and the file has to declare the
   column schema that makes its rows machine-readable. A spreadsheet holding
   one free-text column per row is revisable and still unusable.
5. Compare the build standard the list was issued against with the standard the
   item is currently at, keeping a list issued behind the hardware apart from
   one issued ahead of it: the two have opposite corrections.
6. Check the declared line count against the installed part count, which is a
   cheap independent read on scope no format or revision field gives.
7. Weight the closed items by installed part count, compare that coverage with
   the level the project agreed, and return one build-level verdict carrying
   findings ranked worst first.
"""

import math

__all__ = [
    "CLASS_3_CATEGORY",
    "CONTAINER_FORMATS",
    "COVERAGE_TOLERANCE",
    "MANDATORY_ISSUE_FIELDS",
    "validate_identifier",
    "container_revisable",
    "issue_completeness",
    "editability_decision",
    "build_standard_alignment",
    "obliged_class_3_items",
    "evaluate_issue",
    "coverage_by_part_count",
    "assess_class_3_declared_components_list",
]

# The product category whose items owe a list under this clause.
CLASS_3_CATEGORY = "class-3"

# Coverage is a ratio of summed part counts. An exactly-met requirement can
# land a few units in the last place low; absorb that representation error
# here rather than lowering the level the project agreed.
COVERAGE_TOLERANCE = 1e-9

# Container format -> can a reviewer revise the delivered file in place. The
# question is the file itself, never the words printed inside it.
CONTAINER_FORMATS = {
    "csv": True,
    "tsv": True,
    "xlsx": True,
    "ods": True,
    "xml": True,
    "json": True,
    "docx": True,
    "markdown": True,
    "pdf-flat": False,
    "pdf-scan": False,
    "pdf-form": False,
    "tiff": False,
    "png": False,
    "paper": False,
}

# The fields without which no acceptance decision can be taken at all.
MANDATORY_ISSUE_FIELDS = (
    "issue_id",
    "item_id",
    "container_format",
    "schema_declared",
    "issued_build_standard",
    "declared_line_count",
)

# Disposition -> rank used to order findings. Lower sorts first.
_SEVERITY = {
    "issue-record-incomplete": 0,
    "unknown-equipment-item": 1,
    "repeat-issue-for-closed-item": 2,
    "container-not-revisable": 3,
    "schema-not-declared": 4,
    "build-standard-ahead": 5,
    "build-standard-behind": 6,
    "line-count-below-installed-parts": 7,
    "no-list-issued": 8,
    "outside-class-3-obligation": 9,
    "accepted": 10,
}

_ACCEPTED = "accepted"


def _require_text(value, label):
    """Return a non-blank stripped string, or raise ValueError."""
    if not isinstance(value, str):
        raise ValueError("%s must be a string, got %r" % (label, value))
    text = value.strip()
    if not text:
        raise ValueError("%s must not be blank" % label)
    return text


def _require_non_negative_int(value, label):
    """Return a non-negative integer, or raise ValueError."""
    if isinstance(value, bool) or not isinstance(value, int):
        raise ValueError("%s must be an integer, got %r" % (label, value))
    if value < 0:
        raise ValueError("%s must not be negative, got %d" % (label, value))
    return value


def _require_positive_int(value, label):
    """Return a strictly positive integer, or raise ValueError."""
    value = _require_non_negative_int(value, label)
    if value == 0:
        raise ValueError("%s must be strictly positive" % label)
    return value


def _require_bool(value, label):
    """Return a real boolean, or raise ValueError."""
    if not isinstance(value, bool):
        raise ValueError("%s must be a boolean, got %r" % (label, value))
    return value


def validate_identifier(value):
    """Return the validated identifier of one equipment item or one issue."""
    return _require_text(value, "identifier")


def container_revisable(container_format):
    """Return True when the container the list arrived in can be revised."""
    fmt = _require_text(container_format, "container_format").lower()
    if fmt not in CONTAINER_FORMATS:
        raise ValueError(
            "unknown container_format %r; known: %s"
            % (container_format, ", ".join(sorted(CONTAINER_FORMATS)))
        )
    return CONTAINER_FORMATS[fmt]


def issue_completeness(issue):
    """Return (missing_fields, completeness_fraction) for one issued list."""
    if not isinstance(issue, dict):
        raise ValueError(
            "each issued list must be a mapping, got %r" % (type(issue).__name__,)
        )
    missing = []
    for field in MANDATORY_ISSUE_FIELDS:
        if field not in issue:
            missing.append(field)
            continue
        value = issue[field]
        if value is None:
            missing.append(field)
        elif isinstance(value, str) and not value.strip():
            missing.append(field)
    total = len(MANDATORY_ISSUE_FIELDS)
    return (tuple(missing), (total - len(missing)) / total)


def editability_decision(container_format, schema_declared):
    """Return the editability verdict of one issued file.

    Editable means two things at once: the container can be revised in place,
    and the file declares the column schema that makes its rows readable by
    something other than a human eye.
    """
    revisable = container_revisable(container_format)
    declared = _require_bool(schema_declared, "schema_declared")
    if not revisable:
        return "container-not-revisable"
    if not declared:
        return "schema-not-declared"
    return "editable"


def build_standard_alignment(issued_standard, item_standard):
    """Return how an issue's build standard stands against the item's."""
    issued = _require_non_negative_int(issued_standard, "issued_build_standard")
    current = _require_non_negative_int(item_standard, "item build_standard")
    if issued == current:
        return "aligned"
    if issued < current:
        return "behind-build"
    return "ahead-of-build"


def obliged_class_3_items(items):
    """Return the identifiers of the items this clause obliges a list for."""
    if not isinstance(items, (list, tuple)) or not items:
        raise ValueError("items must be a non-empty sequence of item mappings")
    obliged = []
    seen = set()
    for item in items:
        if not isinstance(item, dict):
            raise ValueError("each equipment item must be a mapping")
        item_id = validate_identifier(item.get("item_id"))
        if item_id in seen:
            raise ValueError("equipment item %s appears twice in the build" % item_id)
        seen.add(item_id)
        category = _require_text(item.get("product_category"), "product_category").lower()
        _require_non_negative_int(item.get("build_standard"), "build_standard")
        _require_positive_int(item.get("installed_part_count"), "installed_part_count")
        if category == CLASS_3_CATEGORY:
            obliged.append(item_id)
    if not obliged:
        raise ValueError("the build carries no %s equipment item" % CLASS_3_CATEGORY)
    return tuple(obliged)


def evaluate_issue(issue, item_index, closed_items=()):
    """Return the disposition record of one issued declared components list."""
    if not isinstance(item_index, dict) or not item_index:
        raise ValueError("item_index must be a non-empty mapping of item_id -> item")
    missing, completeness = issue_completeness(issue)
    raw_label = issue.get("issue_id")
    label = (
        raw_label.strip()
        if isinstance(raw_label, str) and raw_label.strip()
        else "<unnamed>"
    )
    record = {
        "issue_id": label,
        "item_id": None,
        "missing_fields": missing,
        "completeness": completeness,
        "editability": None,
        "build_alignment": None,
        "installed_part_count": 0,
        "disposition": "issue-record-incomplete",
        "accepted": False,
    }
    if missing:
        return record

    item_id = validate_identifier(issue["item_id"])
    record["item_id"] = item_id
    if item_id not in item_index:
        record["disposition"] = "unknown-equipment-item"
        return record

    item = item_index[item_id]
    category = _require_text(item.get("product_category"), "product_category").lower()
    installed = _require_positive_int(
        item.get("installed_part_count"), "installed_part_count"
    )
    record["installed_part_count"] = installed

    if category != CLASS_3_CATEGORY:
        record["disposition"] = "outside-class-3-obligation"
        return record

    if item_id in closed_items:
        record["disposition"] = "repeat-issue-for-closed-item"
        return record

    editability = editability_decision(
        issue["container_format"], issue["schema_declared"]
    )
    record["editability"] = editability
    alignment = build_standard_alignment(
        issue["issued_build_standard"], item.get("build_standard")
    )
    record["build_alignment"] = alignment
    declared_lines = _require_non_negative_int(
        issue["declared_line_count"], "declared_line_count"
    )

    if editability != "editable":
        record["disposition"] = editability
        return record
    if alignment == "ahead-of-build":
        record["disposition"] = "build-standard-ahead"
        return record
    if alignment == "behind-build":
        record["disposition"] = "build-standard-behind"
        return record
    if declared_lines < installed:
        record["disposition"] = "line-count-below-installed-parts"
        return record

    record["disposition"] = _ACCEPTED
    record["accepted"] = True
    return record


def coverage_by_part_count(records, item_index, obliged):
    """Return the obliged installed-part count now sitting behind a list."""
    if not isinstance(records, (list, tuple)):
        raise ValueError("records must be a sequence of issue records")
    if not isinstance(obliged, (list, tuple)) or not obliged:
        raise ValueError("obliged must be a non-empty sequence of item identifiers")
    total = 0
    for item_id in obliged:
        if item_id not in item_index:
            raise ValueError("obliged item %s is not in the item index" % item_id)
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


def _finding_detail(record):
    """Return the reason one issued list was not accepted."""
    disposition = record["disposition"]
    if disposition == "issue-record-incomplete":
        return "the issue record lacks %s, so no decision can be taken on it" % ", ".join(
            record["missing_fields"]
        )
    if disposition == "unknown-equipment-item":
        return "the issue names an equipment item that is not in the build"
    if disposition == "repeat-issue-for-closed-item":
        return "a further list arrived for an item an accepted list already closed"
    if disposition == "container-not-revisable":
        return "the container cannot be revised in place whatever it prints"
    if disposition == "schema-not-declared":
        return "the file declares no column schema, so its rows are not readable"
    if disposition == "build-standard-ahead":
        return "the list was issued against a standard the item has not been built to"
    if disposition == "build-standard-behind":
        return "the list was issued against a superseded build standard of the item"
    if disposition == "line-count-below-installed-parts":
        return "the list declares fewer lines than the item installs parts"
    return "the issue sits outside the obligation this clause raises"


def assess_class_3_declared_components_list(spec):
    """Run the full clause 6.1.4 list-issue assessment over one build.

    spec keys: items (sequence of equipment item mappings), issues (sequence
    of issued list mappings), optional required_coverage (default 1.0).
    """
    if not isinstance(spec, dict):
        raise ValueError("spec must be a mapping")
    for key in ("items", "issues"):
        if key not in spec:
            raise ValueError("spec missing required key '%s'" % key)

    items = spec["items"]
    obliged = obliged_class_3_items(items)
    item_index = {validate_identifier(item["item_id"]): item for item in items}

    issues = spec["issues"]
    if not isinstance(issues, (list, tuple)):
        raise ValueError("spec['issues'] must be a sequence")

    required = spec.get("required_coverage", 1.0)
    if isinstance(required, bool) or not isinstance(required, (int, float)):
        raise ValueError("required_coverage must be a real number")
    required = float(required)
    if not math.isfinite(required) or required < 0.0 or required > 1.0:
        raise ValueError(
            "required_coverage must lie in [0, 1], got %r" % (spec["required_coverage"],)
        )

    records = []
    closed_items = set()
    for issue in issues:
        record = evaluate_issue(issue, item_index, closed_items=closed_items)
        # Only an accepted list closes an item. A corrected file arriving after
        # a rejection is the fix for that rejection, never a repeat issue.
        if record["disposition"] == _ACCEPTED and record["item_id"] is not None:
            closed_items.add(record["item_id"])
        records.append(record)

    addressed = {r["item_id"] for r in records if r["item_id"] is not None}
    not_issued = tuple(
        sorted(item_id for item_id in obliged if item_id not in addressed)
    )

    coverage = coverage_by_part_count(records, item_index, obliged)

    findings = []
    for record in records:
        disposition = record["disposition"]
        if disposition in (_ACCEPTED, "outside-class-3-obligation"):
            continue
        findings.append(
            {
                "severity": _SEVERITY.get(disposition, 9),
                "reference": record["issue_id"],
                "disposition": disposition,
                "detail": _finding_detail(record),
            }
        )
    for item_id in not_issued:
        findings.append(
            {
                "severity": _SEVERITY["no-list-issued"],
                "reference": item_id,
                "disposition": "no-list-issued",
                "detail": "no declared components list was issued for this item",
            }
        )
    findings.sort(key=lambda entry: (entry["severity"], entry["reference"]))

    meets = coverage > required or math.isclose(
        coverage, required, rel_tol=0.0, abs_tol=COVERAGE_TOLERANCE
    )
    issuable = meets and not findings
    return {
        "obliged_items": obliged,
        "records": records,
        "items_without_a_list": not_issued,
        "part_count_coverage": coverage,
        "required_coverage": required,
        "findings": findings,
        "issuable": issuable,
        "verdict": "issue" if issuable else "hold",
    }
