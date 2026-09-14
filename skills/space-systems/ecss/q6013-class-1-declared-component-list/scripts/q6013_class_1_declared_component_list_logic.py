"""Declared component list issued per equipment, and the approval route of each line.

Anchor: ECSS-Q-ST-60-13C clause 4.1.4 (the declared component list raised for an
equipment and the route by which its lines are approved). Paraphrased into an
implementable procedure; no standard text is reproduced.

Procedure implemented here
--------------------------
1. Validate the equipment the list is raised for, and every line on it.
2. Grade each line on the attributes an approval decision cannot be taken
   without, and keep an incomplete record apart from a complete record whose
   approval is simply not there yet.
3. Route each line to the authority its procurement category obliges: a
   commercial category owes a customer approval, an already-qualified category
   is carried by a project declaration.
4. Separate the approval states that look alike on a spreadsheet: never
   requested, still open, refused, and granted against a different equipment or
   a different application and therefore not transferable to this one.
5. Weight the releasable lines by installed quantity, compare the resulting
   coverage with the release threshold, and return one list-level verdict with
   ranked findings.
"""

import math

__all__ = [
    "COVERAGE_TOLERANCE",
    "MANDATORY_LINE_ATTRIBUTES",
    "APPROVAL_ROUTES",
    "APPROVAL_STATES",
    "validate_equipment_id",
    "approval_route",
    "line_completeness",
    "duplicate_line_ids",
    "evaluate_line",
    "approval_coverage",
    "assess_declared_component_list",
]

# Coverage is a ratio of summed quantities. An exactly-met threshold can land a
# few ULPs low; absorb the representation error here rather than lowering the
# threshold the project agreed.
COVERAGE_TOLERANCE = 1e-9

# The attributes without which an approval decision cannot be taken at all. A
# line missing any of them is an incomplete record, not a pending approval.
MANDATORY_LINE_ATTRIBUTES = (
    "line_id",
    "part_number",
    "manufacturer",
    "component_type",
    "procurement_category",
    "equipment_id",
    "quantity",
    "approval_state",
)

# Procurement category -> the authority that owns the approval decision.
APPROVAL_ROUTES = {
    "commercial": "customer-approval",
    "commercial-upscreened": "customer-approval",
    "custom": "customer-approval",
    "ecss-qualified": "project-declaration",
    "eppl": "project-declaration",
}

# The states a line's approval can be in. They are not interchangeable: three
# of them mean "no approval exists" for three different reasons.
APPROVAL_STATES = (
    "granted",
    "declared",
    "submitted",
    "in-review",
    "refused",
    "withdrawn",
    "not-requested",
)

_OPEN_STATES = ("submitted", "in-review")
_REFUSED_STATES = ("refused", "withdrawn")

# Disposition -> severity used to rank findings. Lower sorts first.
_SEVERITY = {
    "record-incomplete": 0,
    "orphan-line": 1,
    "approval-refused": 2,
    "approval-not-transferable": 3,
    "approval-missing": 4,
    "approval-open": 5,
    "wrong-route-state": 6,
    "released": 9,
}

_RELEASABLE = ("released",)


def _require_text(value, label):
    """Return a non-blank stripped string, or raise."""
    if not isinstance(value, str):
        raise ValueError("%s must be a string, got %r" % (label, value))
    text = value.strip()
    if not text:
        raise ValueError("%s must not be blank" % label)
    return text


def _require_positive_int(value, label):
    """Return a strictly positive integer quantity, or raise."""
    if isinstance(value, bool) or not isinstance(value, int):
        raise ValueError("%s must be an integer, got %r" % (label, value))
    if value <= 0:
        raise ValueError("%s must be strictly positive, got %d" % (label, value))
    return value


def validate_equipment_id(value):
    """Return the validated identifier of the equipment the list is raised for."""
    return _require_text(value, "equipment_id")


def approval_route(procurement_category):
    """Return the approval authority obliged by a procurement category."""
    category = _require_text(procurement_category, "procurement_category").lower()
    if category not in APPROVAL_ROUTES:
        raise ValueError(
            "unknown procurement_category %r; known: %s"
            % (procurement_category, ", ".join(sorted(APPROVAL_ROUTES)))
        )
    return APPROVAL_ROUTES[category]


def line_completeness(line):
    """Return (missing_attributes, completeness_fraction) for one list line."""
    if not isinstance(line, dict):
        raise ValueError("each line must be a mapping, got %r" % (type(line).__name__,))
    missing = []
    for attribute in MANDATORY_LINE_ATTRIBUTES:
        if attribute not in line:
            missing.append(attribute)
            continue
        value = line[attribute]
        if value is None:
            missing.append(attribute)
        elif isinstance(value, str) and not value.strip():
            missing.append(attribute)
    total = len(MANDATORY_LINE_ATTRIBUTES)
    fraction = (total - len(missing)) / total
    return (tuple(missing), fraction)


def duplicate_line_ids(lines):
    """Return the line identifiers that appear more than once on the list."""
    if not isinstance(lines, (list, tuple)):
        raise ValueError("lines must be a sequence")
    seen = {}
    for line in lines:
        if not isinstance(line, dict):
            raise ValueError("each line must be a mapping")
        raw = line.get("line_id")
        if not isinstance(raw, str) or not raw.strip():
            continue
        key = raw.strip()
        seen[key] = seen.get(key, 0) + 1
    return tuple(sorted(key for key, count in seen.items() if count > 1))


def evaluate_line(line, equipment_id):
    """Return the disposition record of one declared component list line."""
    equipment = validate_equipment_id(equipment_id)
    missing, completeness = line_completeness(line)
    label = line.get("line_id") if isinstance(line.get("line_id"), str) else "<unnamed>"
    record = {
        "line_id": label.strip() or "<unnamed>",
        "missing_attributes": missing,
        "completeness": completeness,
        "route": None,
        "disposition": "record-incomplete",
        "quantity": 0,
        "releasable": False,
    }
    if missing:
        return record

    line_equipment = _require_text(line["equipment_id"], "line equipment_id")
    quantity = _require_positive_int(line["quantity"], "line quantity")
    record["quantity"] = quantity
    state = _require_text(line["approval_state"], "approval_state").lower()
    if state not in APPROVAL_STATES:
        raise ValueError(
            "unknown approval_state %r; known: %s"
            % (line["approval_state"], ", ".join(APPROVAL_STATES))
        )
    route = approval_route(line["procurement_category"])
    record["route"] = route

    if line_equipment != equipment:
        record["disposition"] = "orphan-line"
        return record

    if route == "project-declaration":
        if state in ("granted", "declared"):
            record["disposition"] = "released"
            record["releasable"] = True
        elif state in _OPEN_STATES:
            record["disposition"] = "approval-open"
        elif state in _REFUSED_STATES:
            record["disposition"] = "approval-refused"
        else:
            record["disposition"] = "approval-missing"
        return record

    # Customer-approval route: a granted approval still has to have been
    # granted for THIS equipment and THIS application to carry over.
    if state == "granted":
        scope_equipment = line.get("approval_equipment_id")
        scope_application = line.get("approval_application")
        line_application = line.get("application")
        transferable = True
        if isinstance(scope_equipment, str) and scope_equipment.strip():
            transferable = scope_equipment.strip() == equipment
        if transferable and isinstance(scope_application, str) and scope_application.strip():
            if isinstance(line_application, str) and line_application.strip():
                transferable = scope_application.strip() == line_application.strip()
        if transferable:
            record["disposition"] = "released"
            record["releasable"] = True
        else:
            record["disposition"] = "approval-not-transferable"
        return record

    if state == "declared":
        # A project declaration does not discharge a customer-approval line.
        record["disposition"] = "wrong-route-state"
        return record
    if state in _OPEN_STATES:
        record["disposition"] = "approval-open"
        return record
    if state in _REFUSED_STATES:
        record["disposition"] = "approval-refused"
        return record
    record["disposition"] = "approval-missing"
    return record


def approval_coverage(records):
    """Return the installed-quantity fraction sitting on a releasable line."""
    if not isinstance(records, (list, tuple)) or not records:
        raise ValueError("records must be a non-empty sequence of line records")
    total = 0
    released = 0
    for record in records:
        if not isinstance(record, dict) or "disposition" not in record:
            raise ValueError("each record must be a mapping carrying 'disposition'")
        quantity = record.get("quantity", 0)
        if isinstance(quantity, bool) or not isinstance(quantity, int) or quantity < 0:
            raise ValueError("record quantity must be a non-negative integer")
        total += quantity
        if record["disposition"] in _RELEASABLE:
            released += quantity
    if total <= 0:
        raise ValueError("no line on the list carries a usable installed quantity")
    return released / total


def assess_declared_component_list(spec):
    """Run the full clause 4.1.4 declared component list assessment.

    spec keys: equipment_id, lines (sequence of line mappings), optional
    required_coverage (default 1.0).
    """
    if not isinstance(spec, dict):
        raise ValueError("spec must be a mapping")
    for key in ("equipment_id", "lines"):
        if key not in spec:
            raise ValueError("spec missing required key '%s'" % key)
    equipment = validate_equipment_id(spec["equipment_id"])
    lines = spec["lines"]
    if not isinstance(lines, (list, tuple)) or not lines:
        raise ValueError("spec['lines'] must be a non-empty sequence")
    required = spec.get("required_coverage", 1.0)
    if isinstance(required, bool) or not isinstance(required, (int, float)):
        raise ValueError("required_coverage must be a real number")
    required = float(required)
    if not math.isfinite(required) or required < 0.0 or required > 1.0:
        raise ValueError("required_coverage must lie in [0, 1], got %r" % (spec["required_coverage"],))

    records = [evaluate_line(line, equipment) for line in lines]
    coverage = approval_coverage(records)
    duplicates = duplicate_line_ids(lines)

    findings = []
    for record in records:
        disposition = record["disposition"]
        if disposition in _RELEASABLE:
            continue
        findings.append(
            {
                "severity": _SEVERITY.get(disposition, 8),
                "line_id": record["line_id"],
                "disposition": disposition,
                "detail": _finding_detail(record),
            }
        )
    for line_id in duplicates:
        findings.append(
            {
                "severity": 1,
                "line_id": line_id,
                "disposition": "duplicate-line-id",
                "detail": "line identifier %s appears more than once on the list" % line_id,
            }
        )
    findings.sort(key=lambda item: (item["severity"], item["line_id"]))

    meets_threshold = coverage > required or math.isclose(
        coverage, required, rel_tol=0.0, abs_tol=COVERAGE_TOLERANCE
    )
    releasable = meets_threshold and not findings
    return {
        "equipment_id": equipment,
        "records": records,
        "approval_coverage": coverage,
        "required_coverage": required,
        "duplicate_line_ids": duplicates,
        "findings": findings,
        "releasable": releasable,
        "verdict": "release" if releasable else "hold",
    }


def _finding_detail(record):
    """Return the human-readable reason a line is not releasable."""
    disposition = record["disposition"]
    if disposition == "record-incomplete":
        return "line lacks %s; no approval decision can be taken on it" % ", ".join(
            record["missing_attributes"]
        )
    if disposition == "orphan-line":
        return "line is raised against another equipment; the list is issued per equipment"
    if disposition == "approval-not-transferable":
        return "approval exists but was granted for another equipment or application"
    if disposition == "approval-refused":
        return "approval was refused or withdrawn; the line needs a replacement part"
    if disposition == "approval-open":
        return "approval is still open with the authority"
    if disposition == "wrong-route-state":
        return "line carries a project declaration where a customer approval is owed"
    return "no approval has been requested for this line"
