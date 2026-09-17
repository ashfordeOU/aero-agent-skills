"""Board-level approval route for electronic parts at reliability Class 2.

Anchor: ECSS-Q-ST-60C clause 5.1.3 (selection and use of electronic parts at
Class 2 is approved through the parts control board). Paraphrased into an
implementable procedure; no standard text is reproduced.

Procedure implemented here
--------------------------
1. Read the board as it actually sat: a function counts as seated when its
   holder attended or an accepted proxy stood in for it, and the chair is
   counted separately because a delegated decision rests on the chair alone.
2. Derive the decision level each part category needs. A part already on the
   approved range can be cleared by a delegated chair decision; a part off
   the range, one whose use depends on an evaluation programme, and a waiver
   each need the board, and the last two need something beyond it.
3. Dispose of every submission. A submission with no reference, category,
   decision or dates cannot be routed; an incomplete data package cannot be
   decided on; a decision dated before its submission is a record error.
4. Compare the route the decision actually took with the route the category
   needed, and refuse a route that sits below it. A board route also needs
   the quorum to have been there on the day.
5. Require the evidence the level rests on: evaluation results where the
   category depends on them, a recorded customer agreement where the level
   reaches that far, and a minute reference for anything the board decided.
6. Age each decision against the declared turnaround, flag every part
   committed to procurement before its decision, and return the approval
   share with one board verdict.
"""

import math

__all__ = [
    "QUORUM_TOLERANCE",
    "BOARD_FUNCTIONS",
    "MANDATORY_FUNCTIONS",
    "PART_CATEGORIES",
    "DECISION_LEVELS",
    "DECISION_OUTCOMES",
    "MANDATORY_REQUEST_ATTRIBUTES",
    "validate_request_id",
    "validate_part_category",
    "required_decision_level",
    "level_rank",
    "seated_functions",
    "board_state",
    "request_completeness",
    "decision_turnaround",
    "evaluate_request",
    "approval_share",
    "assess_parts_control_board",
]

# Quorum is a ratio of counted seats. An exactly-met floor can land a few ULPs
# low; absorb the representation error here rather than lowering the floor.
QUORUM_TOLERANCE = 1e-9

# The functions a Class 2 parts control board is constituted from, and whether
# the board can sit at all without them.
BOARD_FUNCTIONS = {
    "parts-engineering": True,
    "product-assurance": True,
    "design-authority": True,
    "procurement": False,
    "reliability-engineering": False,
    "radiation-engineering": False,
}

MANDATORY_FUNCTIONS = frozenset(
    name for name, mandatory in BOARD_FUNCTIONS.items() if mandatory
)

# Decision level -> its rank. A route may sit at or above what the category
# needs, never below it.
DECISION_LEVELS = {
    "chair-delegated": 1,
    "board-decision": 2,
    "board-decision-with-evaluation-evidence": 3,
    "board-decision-with-customer-agreement": 4,
}

# Part category -> the lowest decision level that category may be cleared at.
PART_CATEGORIES = {
    "approved-range-part": "chair-delegated",
    "non-standard-part": "board-decision",
    "part-requiring-evaluation": "board-decision-with-evaluation-evidence",
    "part-outside-the-approved-range": "board-decision-with-customer-agreement",
    "waiver-request": "board-decision-with-customer-agreement",
}

# Outcome -> does it close the submission with the part usable.
DECISION_OUTCOMES = {
    "approved": True,
    "approved-with-restrictions": True,
    "rejected": False,
    "deferred": False,
}

# The attributes without which a submission cannot be routed at all.
MANDATORY_REQUEST_ATTRIBUTES = (
    "request_id",
    "part_reference",
    "part_category",
    "decision",
    "route_taken",
    "submitted_day",
    "decision_day",
)

# Disposition -> severity used to rank findings. Lower sorts first.
_SEVERITY = {
    "record-incomplete": 0,
    "category-unrecognised": 1,
    "outcome-unrecognised": 2,
    "route-unrecognised": 3,
    "duplicate-request": 4,
    "decision-before-submission": 5,
    "data-package-incomplete": 6,
    "route-below-required-level": 7,
    "quorum-not-met": 8,
    "evaluation-evidence-absent": 9,
    "customer-agreement-absent": 10,
    "minute-reference-absent": 11,
    "committed-before-decision": 12,
    "turnaround-exceeded": 13,
    "closed-not-usable": 14,
    "accepted": 15,
}

_ACCEPTED = "accepted"
_CLOSED = "closed-not-usable"


def _require_text(value, label):
    """Return a non-blank stripped string, or raise."""
    if not isinstance(value, str):
        raise ValueError("%s must be a string, got %r" % (label, value))
    text = value.strip()
    if not text:
        raise ValueError("%s must not be blank" % label)
    return text


def _require_bool(value, label):
    """Return a boolean, or raise."""
    if not isinstance(value, bool):
        raise ValueError("%s must be a boolean, got %r" % (label, value))
    return value


def _require_non_negative_int(value, label):
    """Return a non-negative integer, or raise."""
    if isinstance(value, bool) or not isinstance(value, int):
        raise ValueError("%s must be an integer, got %r" % (label, value))
    if value < 0:
        raise ValueError("%s must not be negative, got %d" % (label, value))
    return value


def _is_present(value):
    """Return True when an optional text field actually carries something."""
    return isinstance(value, str) and bool(value.strip())


def validate_request_id(value):
    """Return the validated identifier of one board submission."""
    return _require_text(value, "request_id")


def validate_part_category(value):
    """Return the canonical name of one recognised part category."""
    name = _require_text(value, "part_category").lower()
    if name not in PART_CATEGORIES:
        raise ValueError(
            "unknown part_category %r; known: %s"
            % (value, ", ".join(sorted(PART_CATEGORIES)))
        )
    return name


def required_decision_level(part_category):
    """Return the lowest decision level a part category may be cleared at."""
    return PART_CATEGORIES[validate_part_category(part_category)]


def level_rank(level):
    """Return the rank of a decision level, higher meaning further up."""
    name = _require_text(level, "decision level").lower()
    if name not in DECISION_LEVELS:
        raise ValueError(
            "unknown decision level %r; known: %s"
            % (level, ", ".join(sorted(DECISION_LEVELS)))
        )
    return DECISION_LEVELS[name]


def seated_functions(board):
    """Return the functions that counted as seated on the day."""
    if not isinstance(board, dict):
        raise ValueError("board must be a mapping")
    seats = board.get("seats")
    if not isinstance(seats, (list, tuple)) or not seats:
        raise ValueError("board['seats'] must be a non-empty sequence of seat mappings")
    seated = set()
    declared = set()
    for seat in seats:
        if not isinstance(seat, dict):
            raise ValueError("each seat must be a mapping")
        function = _require_text(seat.get("function"), "function").lower()
        if function not in BOARD_FUNCTIONS:
            raise ValueError(
                "unknown board function %r; known: %s"
                % (seat.get("function"), ", ".join(sorted(BOARD_FUNCTIONS)))
            )
        if function in declared:
            raise ValueError("board function %s is seated twice" % function)
        declared.add(function)
        present = _require_bool(seat.get("present", False), "present")
        proxy = _require_bool(seat.get("proxy_accepted", False), "proxy_accepted")
        if present or proxy:
            seated.add(function)
    return frozenset(seated)


def board_state(board):
    """Return how the board stood: seated functions, quorum and the chair."""
    seated = seated_functions(board)
    chair = _require_text(board.get("chair_function"), "chair_function").lower()
    if chair not in BOARD_FUNCTIONS:
        raise ValueError("unknown chair_function %r" % (board.get("chair_function"),))
    absent = tuple(sorted(MANDATORY_FUNCTIONS - seated))
    quorum = len(MANDATORY_FUNCTIONS & seated) / len(MANDATORY_FUNCTIONS)
    return {
        "seated": seated,
        "chair_function": chair,
        "chair_seated": chair in seated,
        "absent_mandatory_functions": absent,
        "quorum": quorum,
        "minute_reference": board.get("minute_reference"),
    }


def request_completeness(request):
    """Return (missing_attributes, completeness_fraction) for one submission."""
    if not isinstance(request, dict):
        raise ValueError(
            "each request must be a mapping, got %r" % (type(request).__name__,)
        )
    missing = []
    for attribute in MANDATORY_REQUEST_ATTRIBUTES:
        if attribute not in request:
            missing.append(attribute)
            continue
        value = request[attribute]
        if value is None:
            missing.append(attribute)
        elif isinstance(value, str) and not value.strip():
            missing.append(attribute)
    total = len(MANDATORY_REQUEST_ATTRIBUTES)
    return (tuple(missing), (total - len(missing)) / total)


def decision_turnaround(submitted_day, decision_day):
    """Return the days a submission waited for its decision."""
    submitted = _require_non_negative_int(submitted_day, "submitted_day")
    decided = _require_non_negative_int(decision_day, "decision_day")
    if decided < submitted:
        raise ValueError("decision_day %d precedes submitted_day %d" % (decided, submitted))
    return decided - submitted


def evaluate_request(request, state, turnaround_limit, required_quorum, already_seen=()):
    """Return the disposition record of one board submission."""
    if not isinstance(state, dict) or "seated" not in state:
        raise ValueError("state must be the mapping returned by board_state")
    limit = _require_non_negative_int(turnaround_limit, "turnaround_days")
    floor = _require_quorum(required_quorum)
    missing, completeness = request_completeness(request)
    raw_label = request.get("request_id")
    label = (
        raw_label.strip()
        if isinstance(raw_label, str) and raw_label.strip()
        else "<unreferenced>"
    )
    record = {
        "request_id": label,
        "part_reference": None,
        "part_category": None,
        "required_level": None,
        "route_taken": None,
        "decision": None,
        "turnaround": None,
        "usable": False,
        "disposition": "record-incomplete",
        "accepted": False,
        "missing_attributes": missing,
        "completeness": completeness,
    }
    if missing:
        return record

    category = _require_text(request["part_category"], "part_category").lower()
    record["part_category"] = category
    if category not in PART_CATEGORIES:
        record["disposition"] = "category-unrecognised"
        return record
    required_level = PART_CATEGORIES[category]
    record["required_level"] = required_level

    decision = _require_text(request["decision"], "decision").lower()
    record["decision"] = decision
    if decision not in DECISION_OUTCOMES:
        record["disposition"] = "outcome-unrecognised"
        return record

    route = _require_text(request["route_taken"], "route_taken").lower()
    record["route_taken"] = route
    if route not in DECISION_LEVELS:
        record["disposition"] = "route-unrecognised"
        return record

    record["part_reference"] = _require_text(request["part_reference"], "part_reference")

    if label in already_seen:
        record["disposition"] = "duplicate-request"
        return record

    submitted = _require_non_negative_int(request["submitted_day"], "submitted_day")
    decided = _require_non_negative_int(request["decision_day"], "decision_day")
    if decided < submitted:
        record["disposition"] = "decision-before-submission"
        return record
    record["turnaround"] = decision_turnaround(submitted, decided)

    if not DECISION_OUTCOMES[decision]:
        record["disposition"] = _CLOSED
        return record
    record["usable"] = True

    if not _require_bool(
        request.get("data_package_complete", False), "data_package_complete"
    ):
        record["disposition"] = "data-package-incomplete"
        return record

    if DECISION_LEVELS[route] < DECISION_LEVELS[required_level]:
        record["disposition"] = "route-below-required-level"
        return record

    if DECISION_LEVELS[route] >= DECISION_LEVELS["board-decision"]:
        if state["quorum"] < floor and not math.isclose(
            state["quorum"], floor, rel_tol=0.0, abs_tol=QUORUM_TOLERANCE
        ):
            record["disposition"] = "quorum-not-met"
            return record
        if not _is_present(state.get("minute_reference")):
            record["disposition"] = "minute-reference-absent"
            return record
    elif not state["chair_seated"]:
        record["disposition"] = "quorum-not-met"
        return record

    if DECISION_LEVELS[required_level] >= DECISION_LEVELS[
        "board-decision-with-evaluation-evidence"
    ] and not _is_present(request.get("evaluation_reference")):
        record["disposition"] = "evaluation-evidence-absent"
        return record

    if DECISION_LEVELS[required_level] >= DECISION_LEVELS[
        "board-decision-with-customer-agreement"
    ] and not _is_present(request.get("customer_agreement_reference")):
        record["disposition"] = "customer-agreement-absent"
        return record

    commitment = request.get("procurement_commitment_day")
    if commitment is not None:
        committed = _require_non_negative_int(
            commitment, "procurement_commitment_day"
        )
        if committed < decided:
            record["disposition"] = "committed-before-decision"
            return record

    if record["turnaround"] > limit:
        record["disposition"] = "turnaround-exceeded"
        return record

    record["disposition"] = _ACCEPTED
    record["accepted"] = True
    return record


def approval_share(records):
    """Return the share of routed submissions that ended in a usable approval."""
    if not isinstance(records, (list, tuple)) or not records:
        raise ValueError("records must be a non-empty sequence of request records")
    routed = 0
    approved = 0
    for record in records:
        if not isinstance(record, dict) or "disposition" not in record:
            raise ValueError("each record must be a mapping carrying 'disposition'")
        if record["disposition"] == "record-incomplete":
            continue
        routed += 1
        if record["disposition"] == _ACCEPTED:
            approved += 1
    if routed == 0:
        raise ValueError("no submission carried enough record to be routed")
    return approved / routed


def assess_parts_control_board(spec):
    """Run the full clause 5.1.3 board approval route assessment.

    spec keys: board (mapping with seats, chair_function and an optional
    minute_reference), requests (sequence of submission mappings), optional
    turnaround_days (default 30) and required_quorum (default 1.0).
    """
    if not isinstance(spec, dict):
        raise ValueError("spec must be a mapping")
    for key in ("board", "requests"):
        if key not in spec:
            raise ValueError("spec missing required key '%s'" % key)

    state = board_state(spec["board"])
    requests = spec["requests"]
    if not isinstance(requests, (list, tuple)) or not requests:
        raise ValueError("spec['requests'] must be a non-empty sequence")

    limit = _require_non_negative_int(spec.get("turnaround_days", 30), "turnaround_days")
    floor = _require_quorum(spec.get("required_quorum", 1.0))

    records = []
    seen = set()
    for request in requests:
        record = evaluate_request(request, state, limit, floor, already_seen=seen)
        if record["request_id"] != "<unreferenced>":
            seen.add(record["request_id"])
        records.append(record)

    findings = []
    for record in records:
        if record["disposition"] in (_ACCEPTED, _CLOSED):
            continue
        findings.append(
            {
                "severity": _SEVERITY.get(record["disposition"], 13),
                "reference": record["request_id"],
                "disposition": record["disposition"],
                "detail": _finding_detail(record, state),
            }
        )
    findings.sort(key=lambda entry: (entry["severity"], entry["reference"]))

    approved_parts = tuple(
        sorted(r["part_reference"] for r in records if r["disposition"] == _ACCEPTED)
    )
    share = approval_share(records)
    sound = not findings
    return {
        "board": state,
        "records": records,
        "approved_parts": approved_parts,
        "approval_share": share,
        "turnaround_days": limit,
        "required_quorum": floor,
        "findings": findings,
        "route_sound": sound,
        "verdict": "board route sound" if sound else "board route not established",
    }


def _require_quorum(value):
    """Return a quorum floor inside [0, 1], or raise."""
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise ValueError("required_quorum must be a real number")
    number = float(value)
    if not math.isfinite(number) or number < 0.0 or number > 1.0:
        raise ValueError("required_quorum must lie in [0, 1], got %r" % (value,))
    return number


def _finding_detail(record, state):
    """Return the human-readable reason one submission is not a clean approval."""
    disposition = record["disposition"]
    if disposition == "record-incomplete":
        return "submission lacks %s; it cannot be routed" % ", ".join(
            record["missing_attributes"]
        )
    if disposition == "category-unrecognised":
        return "the part category is outside the set the board routes on"
    if disposition == "outcome-unrecognised":
        return "the recorded outcome is not one the board may take"
    if disposition == "route-unrecognised":
        return "the route taken is not a decision level the board offers"
    if disposition == "duplicate-request":
        return "a second submission carries a reference already decided"
    if disposition == "decision-before-submission":
        return "the decision is dated before the submission it answers"
    if disposition == "data-package-incomplete":
        return "the part was approved on an incomplete data package"
    if disposition == "route-below-required-level":
        return "cleared at %s where the category needs %s" % (
            record["route_taken"],
            record["required_level"],
        )
    if disposition == "quorum-not-met":
        return "the board lacked %s on the day" % (
            ", ".join(state["absent_mandatory_functions"]) or "its chair"
        )
    if disposition == "minute-reference-absent":
        return "a board decision was taken with no minute reference behind it"
    if disposition == "evaluation-evidence-absent":
        return "the category depends on an evaluation programme and cites none"
    if disposition == "customer-agreement-absent":
        return "the level reached needs a recorded customer agreement and has none"
    if disposition == "committed-before-decision":
        return "the part was committed to procurement before the board decided"
    if disposition == "turnaround-exceeded":
        return "the decision took %d days against a declared turnaround" % (
            record["turnaround"],
        )
    return "submission is not a clean approval"
