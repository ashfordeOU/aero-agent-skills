"""Declared components list data item: required fields and approval states.

Anchor: ECSS-Q-ST-60C Annex B (declared components list DRD). Paraphrased into
an implementable procedure; no standard text is reproduced.

Procedure implemented here
--------------------------
1. Validate the document header, because a list with no identifier, issue or
   approving authority cannot be released whatever its lines say.
2. Grade every line on the fields an approval decision cannot be taken
   without, and keep an incomplete line apart from a complete line that fails
   a later check.
3. Resolve the approval state each entry sits in, separating a state that has
   not been decided yet from a decided state that refuses the part.
4. Where a previous state is recorded, check the move into the current state
   is one the approval route allows; a jump straight to approved with no
   review is a process defect the field values alone never show.
5. Insist a conditional approval carries the conditions it is conditional on.
   An approval whose conditions are not written down is an unconditional
   approval in practice, which is not what was granted.
6. Weight the decided-and-usable share by declared quantity rather than by
   line count, compare it with the required level, and return one release
   verdict with ranked findings.
"""

import math

__all__ = [
    "APPROVAL_STATES",
    "ALLOWED_TRANSITIONS",
    "COVERAGE_TOLERANCE",
    "HEADER_FIELDS",
    "LINE_FIELDS",
    "validate_document_header",
    "approval_state_facts",
    "transition_allowed",
    "line_completeness",
    "evaluate_line",
    "approval_profile",
    "usable_quantity_fraction",
    "assess_declared_components_list_drd",
]

# The usable share is a ratio of summed quantities. An exactly-met requirement
# can land a few ULPs low; absorb the representation error here rather than
# lowering the level the project agreed.
COVERAGE_TOLERANCE = 1e-9

# Header fields without which the data item is not a releasable document.
HEADER_FIELDS = (
    "document_id",
    "issue",
    "equipment_item",
    "issue_date",
    "approval_authority",
)

# Line fields without which an approval decision cannot be taken at all.
LINE_FIELDS = (
    "line_id",
    "part_type",
    "manufacturer",
    "part_number",
    "quantity",
    "procurement_reference",
    "approval_state",
)

# Approval state -> whether the customer has decided, and whether the decision
# lets the part stay on the build. The two are independent: a refusal is a
# decision, and an approval still pending is not one.
APPROVAL_STATES = {
    "proposed": {"decided": False, "permits_use": False},
    "under-review": {"decided": False, "permits_use": False},
    "approved": {"decided": True, "permits_use": True},
    "approved-with-conditions": {"decided": True, "permits_use": True},
    "rejected": {"decided": True, "permits_use": False},
    "withdrawn": {"decided": True, "permits_use": False},
}

# The moves the approval route allows. Nothing leaves a withdrawn entry, and
# nothing reaches an approval without passing through review first.
ALLOWED_TRANSITIONS = {
    "proposed": ("under-review", "withdrawn"),
    "under-review": (
        "approved",
        "approved-with-conditions",
        "rejected",
        "withdrawn",
    ),
    "approved": ("withdrawn",),
    "approved-with-conditions": ("approved", "withdrawn"),
    "rejected": ("under-review", "withdrawn"),
    "withdrawn": (),
}

# The state a conditional approval is meaningless without recorded conditions.
_CONDITIONAL_STATE = "approved-with-conditions"

# Disposition -> severity used to rank findings. Lower sorts first.
_SEVERITY = {
    "record-incomplete": 0,
    "unknown-approval-state": 1,
    "invalid-transition": 2,
    "duplicate-entry": 3,
    "condition-not-recorded": 4,
    "decision-outstanding": 5,
    "part-rejected": 6,
    "part-withdrawn": 7,
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


def _require_positive_int(value, label):
    """Return a strictly positive integer, or raise."""
    if isinstance(value, bool) or not isinstance(value, int):
        raise ValueError("%s must be an integer, got %r" % (label, value))
    if value <= 0:
        raise ValueError("%s must be strictly positive, got %d" % (label, value))
    return value


def validate_document_header(header):
    """Return the validated header of one declared components list data item."""
    if not isinstance(header, dict):
        raise ValueError("header must be a mapping")
    validated = {}
    for field in HEADER_FIELDS:
        validated[field] = _require_text(header.get(field), field)
    return validated


def approval_state_facts(state):
    """Return whether a state is decided and whether it permits flight use."""
    name = _require_text(state, "approval_state").lower()
    if name not in APPROVAL_STATES:
        raise ValueError(
            "unknown approval_state %r; known: %s"
            % (state, ", ".join(sorted(APPROVAL_STATES)))
        )
    facts = dict(APPROVAL_STATES[name])
    facts["state"] = name
    return facts


def transition_allowed(from_state, to_state):
    """Return True when the approval route allows this move between states."""
    source = approval_state_facts(from_state)["state"]
    target = approval_state_facts(to_state)["state"]
    if source == target:
        return True
    return target in ALLOWED_TRANSITIONS[source]


def line_completeness(line):
    """Return (missing_fields, completeness_fraction) for one list line."""
    if not isinstance(line, dict):
        raise ValueError(
            "each line must be a mapping, got %r" % (type(line).__name__,)
        )
    missing = []
    for field in LINE_FIELDS:
        if field not in line:
            missing.append(field)
            continue
        value = line[field]
        if value is None:
            missing.append(field)
        elif isinstance(value, str) and not value.strip():
            missing.append(field)
    total = len(LINE_FIELDS)
    fraction = (total - len(missing)) / total
    return (tuple(missing), fraction)


def _entry_key(line):
    """Return the identity a duplicate entry is detected on."""
    return (
        _require_text(line["part_type"], "part_type").lower(),
        _require_text(line["manufacturer"], "manufacturer").lower(),
        _require_text(line["part_number"], "part_number").lower(),
    )


def evaluate_line(line, seen_keys=()):
    """Return the disposition record of one declared components list line."""
    missing, completeness = line_completeness(line)
    raw_label = line.get("line_id")
    label = (
        raw_label.strip()
        if isinstance(raw_label, str) and raw_label.strip()
        else "<unnumbered>"
    )
    record = {
        "line_id": label,
        "part_type": None,
        "missing_fields": missing,
        "completeness": completeness,
        "approval_state": None,
        "previous_state": None,
        "quantity": 0,
        "decided": False,
        "permits_use": False,
        "disposition": "record-incomplete",
        "accepted": False,
    }
    if missing:
        return record

    record["part_type"] = _require_text(line["part_type"], "part_type")
    record["quantity"] = _require_positive_int(line["quantity"], "quantity")

    try:
        facts = approval_state_facts(line["approval_state"])
    except ValueError:
        record["disposition"] = "unknown-approval-state"
        return record
    record["approval_state"] = facts["state"]
    record["decided"] = facts["decided"]
    record["permits_use"] = facts["permits_use"]

    previous = line.get("previous_approval_state")
    if isinstance(previous, str) and previous.strip():
        try:
            prior = approval_state_facts(previous)
        except ValueError:
            record["disposition"] = "unknown-approval-state"
            return record
        record["previous_state"] = prior["state"]
        if not transition_allowed(prior["state"], facts["state"]):
            record["disposition"] = "invalid-transition"
            return record

    if _entry_key(line) in seen_keys:
        record["disposition"] = "duplicate-entry"
        return record

    if facts["state"] == _CONDITIONAL_STATE:
        conditions = line.get("conditions")
        if not isinstance(conditions, str) or not conditions.strip():
            record["disposition"] = "condition-not-recorded"
            return record

    if not facts["decided"]:
        record["disposition"] = "decision-outstanding"
        return record
    if facts["state"] == "rejected":
        record["disposition"] = "part-rejected"
        return record
    if facts["state"] == "withdrawn":
        record["disposition"] = "part-withdrawn"
        return record

    record["disposition"] = _ACCEPTED
    record["accepted"] = True
    return record


def approval_profile(records):
    """Return how many graded lines sit in each approval state."""
    if not isinstance(records, (list, tuple)):
        raise ValueError("records must be a sequence of line records")
    profile = {state: 0 for state in APPROVAL_STATES}
    for record in records:
        if not isinstance(record, dict) or "disposition" not in record:
            raise ValueError("each record must be a mapping carrying 'disposition'")
        state = record.get("approval_state")
        if state in profile:
            profile[state] += 1
    return profile


def usable_quantity_fraction(records):
    """Return the declared quantity share sitting on an accepted line."""
    if not isinstance(records, (list, tuple)) or not records:
        raise ValueError("records must be a non-empty sequence of line records")
    total = 0
    usable = 0
    for record in records:
        if not isinstance(record, dict) or "disposition" not in record:
            raise ValueError("each record must be a mapping carrying 'disposition'")
        quantity = record.get("quantity", 0)
        if isinstance(quantity, bool) or not isinstance(quantity, int) or quantity < 0:
            raise ValueError("record quantity must be a non-negative integer")
        total += quantity
        if record["disposition"] == _ACCEPTED:
            usable += quantity
    if total <= 0:
        raise ValueError("no graded line carries a usable declared quantity")
    return usable / total


def assess_declared_components_list_drd(spec):
    """Run the full Annex B declared components list data item assessment.

    spec keys: header (mapping), lines (sequence of line mappings), optional
    required_usable_fraction (default 1.0).
    """
    if not isinstance(spec, dict):
        raise ValueError("spec must be a mapping")
    for key in ("header", "lines"):
        if key not in spec:
            raise ValueError("spec missing required key '%s'" % key)

    header = validate_document_header(spec["header"])

    lines = spec["lines"]
    if not isinstance(lines, (list, tuple)) or not lines:
        raise ValueError("spec['lines'] must be a non-empty sequence")

    required = spec.get("required_usable_fraction", 1.0)
    if isinstance(required, bool) or not isinstance(required, (int, float)):
        raise ValueError("required_usable_fraction must be a real number")
    required = float(required)
    if not math.isfinite(required) or required < 0.0 or required > 1.0:
        raise ValueError(
            "required_usable_fraction must lie in [0, 1], got %r"
            % (spec["required_usable_fraction"],)
        )

    records = []
    seen_keys = set()
    seen_line_ids = set()
    for line in lines:
        record = evaluate_line(line, seen_keys=seen_keys)
        if record["line_id"] != "<unnumbered>":
            if record["line_id"] in seen_line_ids:
                raise ValueError("line_id %s appears twice" % record["line_id"])
            seen_line_ids.add(record["line_id"])
        if not record["missing_fields"]:
            seen_keys.add(_entry_key(line))
        records.append(record)

    # Every line incomplete is a degenerate list, not a crash: it has no
    # declared quantity to weight, so nothing is usable and the findings carry
    # the whole verdict.
    graded = [record for record in records if record["quantity"] > 0]
    usable = usable_quantity_fraction(records) if graded else 0.0
    profile = approval_profile(records)

    findings = []
    for record in records:
        disposition = record["disposition"]
        if disposition == _ACCEPTED:
            continue
        findings.append(
            {
                "severity": _SEVERITY.get(disposition, 8),
                "reference": record["line_id"],
                "disposition": disposition,
                "detail": _finding_detail(record),
            }
        )
    findings.sort(key=lambda entry: (entry["severity"], entry["reference"]))

    meets = usable > required or math.isclose(
        usable, required, rel_tol=0.0, abs_tol=COVERAGE_TOLERANCE
    )
    releasable = meets and not findings
    return {
        "header": header,
        "records": records,
        "approval_profile": profile,
        "usable_quantity_fraction": usable,
        "required_usable_fraction": required,
        "findings": findings,
        "releasable": releasable,
        "verdict": "release" if releasable else "hold",
    }


def _finding_detail(record):
    """Return the human-readable reason one line blocks the release."""
    disposition = record["disposition"]
    if disposition == "record-incomplete":
        return "line lacks %s; no approval decision can be taken on it" % ", ".join(
            record["missing_fields"]
        )
    if disposition == "unknown-approval-state":
        return "the line carries an approval state the data item does not define"
    if disposition == "invalid-transition":
        return "the entry reached its state by a move the approval route forbids"
    if disposition == "duplicate-entry":
        return "the same part type, manufacturer and part number are listed twice"
    if disposition == "condition-not-recorded":
        return "a conditional approval was granted without recording its conditions"
    if disposition == "decision-outstanding":
        return "the customer has not decided this entry yet"
    if disposition == "part-rejected":
        return "the entry was refused and cannot stay on the build as listed"
    return "the entry was withdrawn and no longer carries an approval"
