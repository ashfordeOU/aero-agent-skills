"""Editable declared components list issued for each Class 1 equipment item.

Anchor: ECSS-Q-ST-60C clause 4.1.4 (an editable declared components list is
issued for every Class 1 equipment item). Paraphrased into an implementable
procedure; no standard text is reproduced.

Procedure implemented here
--------------------------
1. Validate the build: every equipment item carries an identifier, a product
   category, a current build revision and a declared installed part count.
2. Select the items the clause actually obliges. A list is owed by each
   Class 1 item; an item of another category is outside this obligation and
   must not be counted either as covered or as a shortfall.
3. Grade each delivered list on the attributes an acceptance decision cannot
   be taken without, and keep an incomplete delivery record apart from a
   complete one that simply fails a check.
4. Decide editability from the exchange format the file actually arrived in.
   A flattened print or a scan carries the same words as a spreadsheet and is
   still not an editable issue, because the reviewer cannot revise it.
5. Compare the revision the list was issued against with the revision the
   item is currently built to, keeping a stale issue apart from one raised
   ahead of a build standard the item has not reached.
6. Weight the accepted items by declared part count, compare the resulting
   coverage with the required level, and return one build-level verdict with
   ranked findings.
"""

import math

__all__ = [
    "COVERAGE_TOLERANCE",
    "EXCHANGE_FORMATS",
    "MANDATORY_DELIVERY_ATTRIBUTES",
    "OBLIGED_CATEGORY",
    "validate_item_id",
    "format_editability",
    "delivery_completeness",
    "revision_state",
    "obliged_items",
    "evaluate_delivery",
    "item_coverage",
    "assess_declared_components_list",
]

# Coverage is a ratio of summed part counts. An exactly-met requirement can
# land a few ULPs low; absorb the representation error here rather than
# lowering the level the project agreed.
COVERAGE_TOLERANCE = 1e-9

# Exchange format -> can a reviewer revise the delivered file in place. The
# distinction is the file, not the words inside it.
EXCHANGE_FORMATS = {
    "csv": True,
    "tsv": True,
    "xlsx": True,
    "ods": True,
    "xml": True,
    "json": True,
    "docx": True,
    "markdown": True,
    "pdf-form": False,
    "pdf-flat": False,
    "pdf-scan": False,
    "tiff": False,
    "png": False,
    "paper": False,
}

# The attributes without which an acceptance decision cannot be taken at all.
MANDATORY_DELIVERY_ATTRIBUTES = (
    "delivery_id",
    "item_id",
    "exchange_format",
    "issued_revision",
    "line_count",
)

# The product category this clause raises the obligation for.
OBLIGED_CATEGORY = "class-1"

# Disposition -> severity used to rank findings. Lower sorts first.
_SEVERITY = {
    "record-incomplete": 0,
    "unknown-item": 1,
    "duplicate-item-delivery": 2,
    "format-not-editable": 3,
    "revision-ahead-of-build": 4,
    "revision-stale": 5,
    "line-count-short": 6,
    "list-not-issued": 7,
    "outside-obligation": 8,
    "accepted": 9,
}

_ACCEPTED = "accepted"


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


def validate_item_id(value):
    """Return the validated identifier of one equipment item."""
    return _require_text(value, "item_id")


def format_editability(exchange_format):
    """Return True when the delivered exchange format can be revised in place."""
    fmt = _require_text(exchange_format, "exchange_format").lower()
    if fmt not in EXCHANGE_FORMATS:
        raise ValueError(
            "unknown exchange_format %r; known: %s"
            % (exchange_format, ", ".join(sorted(EXCHANGE_FORMATS)))
        )
    return EXCHANGE_FORMATS[fmt]


def delivery_completeness(delivery):
    """Return (missing_attributes, completeness_fraction) for one delivery."""
    if not isinstance(delivery, dict):
        raise ValueError(
            "each delivery must be a mapping, got %r" % (type(delivery).__name__,)
        )
    missing = []
    for attribute in MANDATORY_DELIVERY_ATTRIBUTES:
        if attribute not in delivery:
            missing.append(attribute)
            continue
        value = delivery[attribute]
        if value is None:
            missing.append(attribute)
        elif isinstance(value, str) and not value.strip():
            missing.append(attribute)
    total = len(MANDATORY_DELIVERY_ATTRIBUTES)
    fraction = (total - len(missing)) / total
    return (tuple(missing), fraction)


def revision_state(issued_revision, item_revision):
    """Return how a list's issue revision stands against the item's build."""
    issued = _require_non_negative_int(issued_revision, "issued_revision")
    current = _require_non_negative_int(item_revision, "item build_revision")
    if issued == current:
        return "current"
    if issued < current:
        return "stale"
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
        category = _require_text(item.get("product_category"), "product_category").lower()
        _require_non_negative_int(item.get("build_revision"), "build_revision")
        _require_positive_int(item.get("declared_part_count"), "declared_part_count")
        if category == OBLIGED_CATEGORY:
            obliged.append(item_id)
    if not obliged:
        raise ValueError("the build carries no %s equipment item" % OBLIGED_CATEGORY)
    return tuple(obliged)


def evaluate_delivery(delivery, item_index, already_seen=()):
    """Return the disposition record of one delivered declared components list."""
    if not isinstance(item_index, dict) or not item_index:
        raise ValueError("item_index must be a non-empty mapping of item_id -> item")
    missing, completeness = delivery_completeness(delivery)
    raw_label = delivery.get("delivery_id")
    label = raw_label.strip() if isinstance(raw_label, str) and raw_label.strip() else "<unnamed>"
    record = {
        "delivery_id": label,
        "item_id": None,
        "missing_attributes": missing,
        "completeness": completeness,
        "editable": None,
        "revision_state": None,
        "part_count": 0,
        "disposition": "record-incomplete",
        "accepted": False,
    }
    if missing:
        return record

    item_id = validate_item_id(delivery["item_id"])
    record["item_id"] = item_id
    if item_id not in item_index:
        record["disposition"] = "unknown-item"
        return record

    item = item_index[item_id]
    category = _require_text(item.get("product_category"), "product_category").lower()
    part_count = _require_positive_int(item.get("declared_part_count"), "declared_part_count")
    record["part_count"] = part_count

    if category != OBLIGED_CATEGORY:
        record["disposition"] = "outside-obligation"
        return record

    if item_id in already_seen:
        record["disposition"] = "duplicate-item-delivery"
        return record

    editable = format_editability(delivery["exchange_format"])
    record["editable"] = editable
    state = revision_state(delivery["issued_revision"], item.get("build_revision"))
    record["revision_state"] = state
    line_count = _require_non_negative_int(delivery["line_count"], "line_count")

    if not editable:
        record["disposition"] = "format-not-editable"
        return record
    if state == "ahead-of-build":
        record["disposition"] = "revision-ahead-of-build"
        return record
    if state == "stale":
        record["disposition"] = "revision-stale"
        return record
    if line_count < part_count:
        record["disposition"] = "line-count-short"
        return record

    record["disposition"] = _ACCEPTED
    record["accepted"] = True
    return record


def item_coverage(records, item_index, obliged):
    """Return the obliged part count sitting behind an accepted list."""
    if not isinstance(records, (list, tuple)):
        raise ValueError("records must be a sequence of delivery records")
    if not isinstance(obliged, (list, tuple)) or not obliged:
        raise ValueError("obliged must be a non-empty sequence of item identifiers")
    total = 0
    for item_id in obliged:
        item = item_index[item_id]
        total += _require_positive_int(
            item.get("declared_part_count"), "declared_part_count"
        )
    covered = 0
    accepted_items = set()
    for record in records:
        if not isinstance(record, dict) or "disposition" not in record:
            raise ValueError("each record must be a mapping carrying 'disposition'")
        if record["disposition"] != _ACCEPTED:
            continue
        item_id = record.get("item_id")
        if item_id in accepted_items or item_id not in obliged:
            continue
        accepted_items.add(item_id)
        covered += item_index[item_id]["declared_part_count"]
    if total <= 0:
        raise ValueError("no obliged item carries a usable declared part count")
    return covered / total


def assess_declared_components_list(spec):
    """Run the full clause 4.1.4 declared components list issue assessment.

    spec keys: items (sequence of equipment item mappings), deliveries
    (sequence of delivered list mappings), optional required_coverage
    (default 1.0).
    """
    if not isinstance(spec, dict):
        raise ValueError("spec must be a mapping")
    for key in ("items", "deliveries"):
        if key not in spec:
            raise ValueError("spec missing required key '%s'" % key)
    items = spec["items"]
    obliged = obliged_items(items)
    item_index = {validate_item_id(item["item_id"]): item for item in items}

    deliveries = spec["deliveries"]
    if not isinstance(deliveries, (list, tuple)):
        raise ValueError("spec['deliveries'] must be a sequence")

    required = spec.get("required_coverage", 1.0)
    if isinstance(required, bool) or not isinstance(required, (int, float)):
        raise ValueError("required_coverage must be a real number")
    required = float(required)
    if not math.isfinite(required) or required < 0.0 or required > 1.0:
        raise ValueError(
            "required_coverage must lie in [0, 1], got %r" % (spec["required_coverage"],)
        )

    records = []
    seen_items = set()
    for delivery in deliveries:
        record = evaluate_delivery(delivery, item_index, already_seen=seen_items)
        # Only an ACCEPTED list closes an item. A corrected resubmission after a
        # rejected delivery is a fresh submission, not a duplicate.
        if record["disposition"] == _ACCEPTED and record["item_id"] is not None:
            seen_items.add(record["item_id"])
        records.append(record)

    addressed = {r["item_id"] for r in records if r["item_id"] is not None}
    not_issued = tuple(sorted(item_id for item_id in obliged if item_id not in addressed))

    coverage = item_coverage(records, item_index, obliged)

    findings = []
    for record in records:
        disposition = record["disposition"]
        if disposition in (_ACCEPTED, "outside-obligation"):
            continue
        findings.append(
            {
                "severity": _SEVERITY.get(disposition, 8),
                "reference": record["delivery_id"],
                "disposition": disposition,
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
    findings.sort(key=lambda entry: (entry["severity"], entry["reference"]))

    meets = coverage > required or math.isclose(
        coverage, required, rel_tol=0.0, abs_tol=COVERAGE_TOLERANCE
    )
    issuable = meets and not findings
    return {
        "obliged_items": obliged,
        "records": records,
        "items_without_a_list": not_issued,
        "item_coverage": coverage,
        "required_coverage": required,
        "findings": findings,
        "issuable": issuable,
        "verdict": "issue" if issuable else "hold",
    }


def _finding_detail(record):
    """Return the human-readable reason a delivered list is not accepted."""
    disposition = record["disposition"]
    if disposition == "record-incomplete":
        return "delivery lacks %s; no acceptance decision can be taken on it" % ", ".join(
            record["missing_attributes"]
        )
    if disposition == "unknown-item":
        return "delivery names an equipment item that is not in the build"
    if disposition == "duplicate-item-delivery":
        return "a second list was delivered for an item already covered"
    if disposition == "format-not-editable":
        return "the file arrived in a form the reviewer cannot revise in place"
    if disposition == "revision-ahead-of-build":
        return "the list was issued against a build standard the item has not reached"
    if disposition == "revision-stale":
        return "the list was issued against a superseded build revision of the item"
    if disposition == "line-count-short":
        return "the list holds fewer lines than the item's declared installed parts"
    return "delivery is outside the obligation this clause raises"
