"""GSE delivery review board and GSE delivery authorisation logic.

Anchor: ECSS-Q-ST-20C clauses 5.8.4.3 and 5.8.4.4 -- holding the delivery
review for ground support equipment and carrying out the delivery itself: the
conformity evidence presented, the certificates that back it, and the
documentation that travels with the equipment. Paraphrased into an
implementable procedure; no standard text is reproduced.

Procedure implemented here
--------------------------
1. Validate the delivery review board: the functions that have to be in the
   room, and a chair who is not the function whose work is being reviewed.
2. Check the agenda actually covered every subject the review owes, rather
   than accepting that a meeting happened.
3. Grade the action list: a blocking action still open holds the delivery, an
   ordinary action due before delivery becomes a reservation, and the board
   decision falls out of the two.
4. Derive the conformity certificates the equipment owes from its own states
   and check each one against the delivery date, since a certificate that has
   expired or has not started is not evidence.
5. Reconcile the delivery documentation set, then authorise the delivery only
   when the board decision and every finding allow it.
"""

from datetime import date

__all__ = [
    "MANDATORY_BOARD_FUNCTIONS",
    "MANDATORY_AGENDA_ITEMS",
    "BASE_DELIVERY_DOCUMENTS",
    "ACTION_SEVERITIES",
    "ACTION_STATES",
    "normalize_token",
    "parse_day",
    "validate_board",
    "board_findings",
    "validate_actions",
    "action_findings",
    "board_decision",
    "required_certificates",
    "certificate_findings",
    "delivery_document_findings",
    "assess_gse_delivery",
]

# Functions that have to be represented for the delivery review to be a review.
MANDATORY_BOARD_FUNCTIONS = (
    "quality-assurance",
    "gse-engineering",
    "operations-user",
    "configuration-management",
)

# Subjects the delivery review owes whatever else it discusses.
MANDATORY_AGENDA_ITEMS = (
    "acceptance-status",
    "open-nonconformances",
    "open-actions",
    "configuration-status",
    "data-package-status",
    "limitations-of-use",
)

# Paperwork that travels with every delivered GSE item.
BASE_DELIVERY_DOCUMENTS = (
    "delivery-note",
    "handover-record",
    "operating-and-handling-manual",
    "delivery-review-minutes",
)

# How much an open action weighs on the delivery.
ACTION_SEVERITIES = ("blocking", "standard")

# Where an action stands when the board closes.
ACTION_STATES = ("open", "closed")


def normalize_token(value, label="token"):
    """Return a lowercase, hyphen-joined comparison token for a name."""
    if not isinstance(value, str):
        raise ValueError("%s must be a string, got %r" % (label, value))
    token = "-".join(value.strip().lower().replace("_", " ").replace("-", " ").split())
    if not token:
        raise ValueError("%s must not be blank" % label)
    return token


def parse_day(value, label="date"):
    """Return an ISO calendar date parsed from a string or passed through."""
    if isinstance(value, date):
        return value
    if not isinstance(value, str):
        raise ValueError("%s must be an ISO date string, got %r" % (label, value))
    try:
        return date.fromisoformat(value.strip())
    except ValueError:
        raise ValueError("%s %r is not an ISO calendar date" % (label, value))


def _flag(value, label):
    if not isinstance(value, bool):
        raise ValueError("%s must be a boolean, got %r" % (label, value))
    return value


def validate_board(board):
    """Return the validated delivery review board record."""
    if not isinstance(board, dict):
        raise ValueError("board must be a mapping")
    for key in ("chair_function", "attending_functions", "agenda_items"):
        if key not in board:
            raise ValueError("board is missing '%s'" % key)
    attending = board["attending_functions"]
    agenda = board["agenda_items"]
    if not isinstance(attending, (list, tuple)):
        raise ValueError("board attending_functions must be a sequence")
    if not isinstance(agenda, (list, tuple)):
        raise ValueError("board agenda_items must be a sequence")
    return {
        "chair_function": normalize_token(board["chair_function"], "chair_function"),
        "attending_functions": [normalize_token(f, "attending function") for f in attending],
        "agenda_items": [normalize_token(a, "agenda item") for a in agenda],
        "reviewed_function": normalize_token(
            board.get("reviewed_function", "gse-engineering"), "reviewed_function"
        ),
    }


def board_findings(board):
    """Return the findings about how the delivery review was constituted and run."""
    record = validate_board(board)
    findings = []
    attending = set(record["attending_functions"])
    for function in MANDATORY_BOARD_FUNCTIONS:
        if function not in attending:
            findings.append("delivery review board had no %s representative" % function)
    if record["chair_function"] == record["reviewed_function"]:
        findings.append(
            "delivery review was chaired by %s, the function whose work is under review"
            % record["chair_function"]
        )
    if record["chair_function"] not in attending:
        findings.append(
            "chair function %s is not listed among the attendees" % record["chair_function"]
        )
    covered = set(record["agenda_items"])
    for item in MANDATORY_AGENDA_ITEMS:
        if item not in covered:
            findings.append("delivery review did not cover %s" % item)
    return findings


def validate_actions(actions):
    """Return the validated delivery review action list."""
    if not isinstance(actions, (list, tuple)):
        raise ValueError("actions must be a sequence of action records")
    validated = []
    seen = set()
    for i, action in enumerate(actions):
        if not isinstance(action, dict):
            raise ValueError("actions[%d] must be a mapping" % i)
        for key in ("id", "severity", "state"):
            if key not in action:
                raise ValueError("actions[%d] is missing '%s'" % (i, key))
        aid = normalize_token(action["id"], "actions[%d]['id']" % i)
        if aid in seen:
            raise ValueError("action %r is listed twice" % aid)
        seen.add(aid)
        severity = normalize_token(action["severity"], "actions[%d]['severity']" % i)
        if severity not in ACTION_SEVERITIES:
            raise ValueError("actions[%d] severity %r is unknown" % (i, severity))
        state = normalize_token(action["state"], "actions[%d]['state']" % i)
        if state not in ACTION_STATES:
            raise ValueError("actions[%d] state %r is unknown" % (i, state))
        validated.append(
            {
                "id": aid,
                "severity": severity,
                "state": state,
                "due_before_delivery": _flag(
                    action.get("due_before_delivery", False),
                    "actions[%d]['due_before_delivery']" % i,
                ),
            }
        )
    return validated


def action_findings(actions):
    """Return the findings the open action list raises against the delivery."""
    validated = validate_actions(actions)
    findings = []
    for action in validated:
        if action["state"] != "open":
            continue
        if action["severity"] == "blocking":
            findings.append("blocking action %s is still open" % action["id"])
        elif action["due_before_delivery"]:
            findings.append(
                "action %s was due before delivery and is still open" % action["id"]
            )
    return findings


def board_decision(actions):
    """Return the delivery review outcome the action list supports."""
    validated = validate_actions(actions)
    blocking = [a for a in validated if a["state"] == "open" and a["severity"] == "blocking"]
    if blocking:
        return "hold"
    reservations = [a for a in validated if a["state"] == "open"]
    if reservations:
        return "deliver-with-reservation"
    return "deliver"


def required_certificates(item):
    """Return the conformity certificates this GSE item's own states make mandatory."""
    if not isinstance(item, dict):
        raise ValueError("item must be a mapping")
    certificates = ["certificate-of-conformity"]
    if _flag(item.get("calibrated", False), "calibrated"):
        certificates.append("calibration-certificate")
    if _flag(item.get("lifting_duty", False), "lifting_duty"):
        certificates.append("proof-load-certificate")
    if _flag(item.get("pressurised", False), "pressurised"):
        certificates.append("pressure-test-certificate")
    if _flag(item.get("mains_powered", False), "mains_powered"):
        certificates.append("electrical-safety-certificate")
    return certificates


def certificate_findings(certificates, required_names, delivery_date):
    """Return the certificates missing, unsigned or not valid on the delivery day."""
    if not isinstance(certificates, (list, tuple)):
        raise ValueError("certificates must be a sequence of certificate records")
    if not isinstance(required_names, (list, tuple)):
        raise ValueError("required_names must be a sequence of certificate names")
    day = parse_day(delivery_date, "delivery_date")
    held = {}
    for i, certificate in enumerate(certificates):
        if not isinstance(certificate, dict):
            raise ValueError("certificates[%d] must be a mapping" % i)
        for key in ("name", "issued_on", "valid_until"):
            if key not in certificate:
                raise ValueError("certificates[%d] is missing '%s'" % (i, key))
        token = normalize_token(certificate["name"], "certificates[%d]['name']" % i)
        issued = parse_day(certificate["issued_on"], "certificates[%d]['issued_on']" % i)
        until = parse_day(certificate["valid_until"], "certificates[%d]['valid_until']" % i)
        if until < issued:
            raise ValueError("certificates[%d] expires before it was issued" % i)
        signatory = certificate.get("signatory")
        if signatory is not None:
            signatory = normalize_token(signatory, "certificates[%d]['signatory']" % i)
        held[token] = {"issued_on": issued, "valid_until": until, "signatory": signatory}
    findings = []
    for name in required_names:
        token = normalize_token(name, "required certificate")
        entry = held.get(token)
        if entry is None:
            findings.append("no %s is presented with the equipment" % token)
            continue
        if entry["signatory"] is None:
            findings.append("%s carries no signatory" % token)
        if day < entry["issued_on"]:
            findings.append("%s is dated after the delivery day" % token)
        elif day > entry["valid_until"]:
            findings.append("%s had expired by the delivery day" % token)
    return findings


def delivery_document_findings(carried_documents, limitations_apply):
    """Return the delivery documents the handover is not carrying."""
    if not isinstance(carried_documents, (list, tuple)):
        raise ValueError("carried_documents must be a sequence of document names")
    required = list(BASE_DELIVERY_DOCUMENTS)
    if _flag(limitations_apply, "limitations_apply"):
        required.append("operating-limitations-notice")
    have = {normalize_token(d, "carried document") for d in carried_documents}
    return ["delivery does not carry %s" % name for name in required if name not in have]


def assess_gse_delivery(spec):
    """Run the full clause 5.8.4.3-5.8.4.4 GSE delivery assessment.

    spec keys: board, actions, item, certificates, delivery_date,
    carried_documents, limitations_apply.
    """
    if not isinstance(spec, dict):
        raise ValueError("spec must be a mapping")
    for key in (
        "board",
        "actions",
        "item",
        "certificates",
        "delivery_date",
        "carried_documents",
        "limitations_apply",
    ):
        if key not in spec:
            raise ValueError("spec missing required key '%s'" % key)
    board = board_findings(spec["board"])
    actions = action_findings(spec["actions"])
    decision = board_decision(spec["actions"])
    required = required_certificates(spec["item"])
    certificates = certificate_findings(
        spec["certificates"], required, spec["delivery_date"]
    )
    documents = delivery_document_findings(
        spec["carried_documents"], spec["limitations_apply"]
    )
    findings = list(board) + list(actions) + list(certificates) + list(documents)
    return {
        "board_findings": board,
        "action_findings": actions,
        "board_decision": decision,
        "required_certificates": required,
        "certificate_findings": certificates,
        "document_findings": documents,
        "findings": findings,
        "delivery_authorised": decision != "hold" and not findings,
    }
