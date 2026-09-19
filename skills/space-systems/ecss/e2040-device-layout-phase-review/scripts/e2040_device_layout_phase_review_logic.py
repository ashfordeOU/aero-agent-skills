"""Gate closing the device layout phase.

Anchor: ECSS-E-ST-20-40C clause 5.6.8 (paraphrased into an
implementable procedure; no standard text is reproduced).

Procedure implemented here:

1. Entry criteria decide whether the review is holdable. Each required
   input has to exist, be issued rather than in draft, and have been
   distributed at least the required number of working days before the
   review date.
2. Actions carried over from the previous gate have to be closed at
   this one, because the phase just finished consumed the input each
   of them was raised against.
3. Open review items are disposed of by severity, not by count. A
   major item blocks. A minor item blocks when it has no owner or no
   close-out date, and minor items above the agreed cap block.
4. The outcome is derived from those two judgements: repeat when the
   gate cannot be held or anything blocking is open, pass-with-actions
   when only dated and owned minor items remain inside the cap, pass
   when nothing is open.

Day numbers are working-day ordinals on the project calendar, so the
lead time is a difference of integers and carries no calendar library.

Stdlib only, offline, deterministic.
"""

REQUIRED_INPUTS = (
    "layout-verification-report",
    "consolidated-validation-plan",
    "updated-device-data-sheet",
    "updated-device-database-record",
    "preliminary-escc-detail-specification",
)

# Owed only by a device routed towards formal part evaluation; every
# other required input is owed by every device.
CONDITIONAL_INPUTS = ("preliminary-escc-detail-specification",)

STATUS_ISSUED = "issued"
STATUS_DRAFT = "draft"
STATUS_ABSENT = "absent"
VALID_INPUT_STATUSES = (STATUS_ISSUED, STATUS_DRAFT, STATUS_ABSENT)

SEVERITY_MAJOR = "major"
SEVERITY_MINOR = "minor"
VALID_SEVERITIES = (SEVERITY_MAJOR, SEVERITY_MINOR)

ACTION_CLOSED = "closed"
ACTION_OPEN = "open"
VALID_ACTION_STATUSES = (ACTION_CLOSED, ACTION_OPEN)

OUTCOME_PASS = "pass"
OUTCOME_PASS_WITH_ACTIONS = "pass-with-actions"
OUTCOME_REPEAT = "repeat"

FINDING_INPUT_ABSENT = "required-input-absent"
FINDING_INPUT_IN_DRAFT = "required-input-still-in-draft"
FINDING_INPUT_LATE = "required-input-distributed-inside-the-lead-time"
FINDING_CARRIED_ACTION_OPEN = "action-from-the-previous-gate-still-open"
FINDING_MAJOR_ITEM_OPEN = "open-review-item-of-major-severity"
FINDING_MINOR_ITEM_UNOWNED = "open-minor-item-without-an-owner"
FINDING_MINOR_ITEM_UNDATED = "open-minor-item-without-a-close-out-date"
FINDING_MINOR_ITEMS_ABOVE_CAP = "open-minor-items-above-the-agreed-cap"


def _text(label, value):
    if not isinstance(value, str) or not value.strip():
        raise ValueError("%s must be a non-empty string, got %r" % (label, value))
    return value.strip()


def _day(label, value):
    if not isinstance(value, int) or isinstance(value, bool):
        raise ValueError("%s must be an integer day number, got %r" % (label, value))
    return value


def _count(label, value):
    value = _day(label, value)
    if value < 0:
        raise ValueError("%s must be >= 0, got %r" % (label, value))
    return value


def validate_review(review):
    """Validate the review record and return a normalized copy."""
    if not isinstance(review, dict):
        raise ValueError("review must be a mapping")
    device_id = _text("review device_id", review.get("device_id"))
    review_day = _day("review review_day", review.get("review_day"))
    lead_time = _count(
        "review required_lead_working_days", review.get("required_lead_working_days", 10)
    )
    cap = _count("review minor_item_cap", review.get("minor_item_cap", 5))
    evaluation_route = review.get("evaluation_route", False)
    if not isinstance(evaluation_route, bool):
        raise ValueError("review evaluation_route must be a boolean")
    return {
        "device_id": device_id,
        "review_day": review_day,
        "required_lead_working_days": lead_time,
        "minor_item_cap": cap,
        "evaluation_route": evaluation_route,
    }


def required_inputs(review):
    """The input names this review owes, given the device route."""
    norm = validate_review(review)
    names = []
    for name in REQUIRED_INPUTS:
        if name in CONDITIONAL_INPUTS and not norm["evaluation_route"]:
            continue
        names.append(name)
    return names


def validate_input_record(record):
    """Validate one review-input record and normalize it."""
    if not isinstance(record, dict):
        raise ValueError("input record must be a mapping")
    name = _text("input name", record.get("name"))
    if name not in REQUIRED_INPUTS:
        raise ValueError(
            "unknown review input %r (expected one of %s)"
            % (name, ", ".join(REQUIRED_INPUTS))
        )
    status = record.get("status")
    if status not in VALID_INPUT_STATUSES:
        raise ValueError(
            "input %s has unknown status %r (expected one of %s)"
            % (name, status, ", ".join(VALID_INPUT_STATUSES))
        )
    distributed_day = record.get("distributed_day")
    if distributed_day is not None:
        distributed_day = _day("input %s distributed_day" % name, distributed_day)
    return {"name": name, "status": status, "distributed_day": distributed_day}


def lead_working_days(distributed_day, review_day):
    """Working days between distribution and the review date."""
    distributed = _day("distributed_day", distributed_day)
    review = _day("review_day", review_day)
    return review - distributed


def check_input(record, review):
    """Entry-criteria findings for one required input."""
    norm_review = validate_review(review)
    norm = validate_input_record(record)
    findings = []
    if norm["status"] == STATUS_ABSENT:
        return [FINDING_INPUT_ABSENT]
    if norm["status"] == STATUS_DRAFT:
        findings.append(FINDING_INPUT_IN_DRAFT)
    if norm["distributed_day"] is None:
        findings.append(FINDING_INPUT_LATE)
        return findings
    lead = lead_working_days(norm["distributed_day"], norm_review["review_day"])
    if lead < norm_review["required_lead_working_days"]:
        findings.append(FINDING_INPUT_LATE)
    return findings


def validate_action(action):
    """Validate one carried-over action record and normalize it."""
    if not isinstance(action, dict):
        raise ValueError("action must be a mapping")
    action_id = _text("action id", action.get("id"))
    status = action.get("status")
    if status not in VALID_ACTION_STATUSES:
        raise ValueError(
            "action %s has unknown status %r (expected one of %s)"
            % (action_id, status, ", ".join(VALID_ACTION_STATUSES))
        )
    return {"id": action_id, "status": status}


def validate_item(item):
    """Validate one open review item and normalize it."""
    if not isinstance(item, dict):
        raise ValueError("review item must be a mapping")
    item_id = _text("item id", item.get("id"))
    severity = item.get("severity")
    if severity not in VALID_SEVERITIES:
        raise ValueError(
            "item %s has unknown severity %r (expected one of %s)"
            % (item_id, severity, ", ".join(VALID_SEVERITIES))
        )
    owner = item.get("owner")
    if owner is not None:
        owner = _text("item %s owner" % item_id, owner)
    close_out_day = item.get("close_out_day")
    if close_out_day is not None:
        close_out_day = _day("item %s close_out_day" % item_id, close_out_day)
    return {
        "id": item_id,
        "severity": severity,
        "owner": owner,
        "close_out_day": close_out_day,
    }


def group_items_by_severity(items):
    """Group open review items into severity buckets."""
    if not isinstance(items, list):
        raise ValueError("items must be a list")
    grouped = {severity: [] for severity in VALID_SEVERITIES}
    seen = set()
    for item in items:
        norm = validate_item(item)
        if norm["id"] in seen:
            raise ValueError("duplicate review item id %r" % (norm["id"],))
        seen.add(norm["id"])
        grouped[norm["severity"]].append(norm)
    return grouped


def disposition_findings(items, review):
    """Blocking findings from the open review items."""
    norm_review = validate_review(review)
    grouped = group_items_by_severity(items)
    findings = []
    for item in grouped[SEVERITY_MAJOR]:
        findings.append((item["id"], FINDING_MAJOR_ITEM_OPEN))
    for item in grouped[SEVERITY_MINOR]:
        if item["owner"] is None:
            findings.append((item["id"], FINDING_MINOR_ITEM_UNOWNED))
        if item["close_out_day"] is None:
            findings.append((item["id"], FINDING_MINOR_ITEM_UNDATED))
    if len(grouped[SEVERITY_MINOR]) > norm_review["minor_item_cap"]:
        findings.append((norm_review["device_id"], FINDING_MINOR_ITEMS_ABOVE_CAP))
    return findings


def assess_device_layout_phase_review(review, inputs, actions=None, items=None):
    """Assess the clause 5.6.8 gate and derive its outcome."""
    norm_review = validate_review(review)
    if not isinstance(inputs, list):
        raise ValueError("inputs must be a list")
    actions = [] if actions is None else actions
    items = [] if items is None else items
    if not isinstance(actions, list):
        raise ValueError("actions must be a list")
    by_name = {}
    for record in inputs:
        norm = validate_input_record(record)
        if norm["name"] in by_name:
            raise ValueError("duplicate review input %r" % (norm["name"],))
        by_name[norm["name"]] = norm
    entry_findings = []
    lead_times = {}
    for name in required_inputs(norm_review):
        record = by_name.get(name)
        if record is None:
            entry_findings.append((name, FINDING_INPUT_ABSENT))
            continue
        if record["distributed_day"] is not None:
            lead_times[name] = lead_working_days(
                record["distributed_day"], norm_review["review_day"]
            )
        for finding in check_input(record, norm_review):
            entry_findings.append((name, finding))
    action_findings = []
    seen_actions = set()
    for action in actions:
        norm = validate_action(action)
        if norm["id"] in seen_actions:
            raise ValueError("duplicate action id %r" % (norm["id"],))
        seen_actions.add(norm["id"])
        if norm["status"] != ACTION_CLOSED:
            action_findings.append((norm["id"], FINDING_CARRIED_ACTION_OPEN))
    item_findings = disposition_findings(items, norm_review)
    grouped = group_items_by_severity(items)
    holdable = not entry_findings
    blocking = action_findings + item_findings
    if not holdable or blocking:
        outcome = OUTCOME_REPEAT
    elif grouped[SEVERITY_MINOR]:
        outcome = OUTCOME_PASS_WITH_ACTIONS
    else:
        outcome = OUTCOME_PASS
    return {
        "device_id": norm_review["device_id"],
        "holdable": holdable,
        "entry_findings": entry_findings,
        "lead_working_days": lead_times,
        "blocking_findings": blocking,
        "open_minor_ids": [item["id"] for item in grouped[SEVERITY_MINOR]],
        "open_major_ids": [item["id"] for item in grouped[SEVERITY_MAJOR]],
        "outcome": outcome,
    }
