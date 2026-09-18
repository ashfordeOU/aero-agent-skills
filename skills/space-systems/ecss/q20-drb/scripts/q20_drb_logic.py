"""Delivery review board convening, disposition and record logic.

Anchor: ECSS-Q-ST-20C clause 5.7.3 (delivery review board -- membership and
authority, the inputs the board reviews, the decision it reaches and the record
it leaves). Paraphrased into an implementable procedure; no standard text is
reproduced.

Procedure implemented here
--------------------------
1. Validate the board roster: the functions that must be represented, who is
   actually present, and whether the quality function sits independently of the
   organisation that built the item.
2. Reconcile the end-item data package presented to the board against the set
   the delivery owes, naming each document still outstanding.
3. Take every open nonconformance to its own disposition: a major one carried
   on use-as-is or repair needs the customer's agreement before it can leave,
   an open one with no disposition at all stops the delivery.
4. Take every deviation or waiver offered to the board to its own approval and
   validity state rather than folding them into one packaging verdict.
5. Combine the findings into deliver, deliver-with-reservation or hold, and
   assemble the minute fields the board record has to carry.
"""

import math

__all__ = [
    "REQUIRED_BOARD_FUNCTIONS",
    "REQUIRED_QUORUM_RATIO",
    "QUORUM_TOLERANCE",
    "REQUIRED_MINUTE_FIELDS",
    "BLOCKING_DISPOSITIONS",
    "normalize_token",
    "validate_board",
    "quorum_ratio",
    "board_findings",
    "data_package_findings",
    "nonconformance_finding",
    "nonconformance_findings",
    "waiver_findings",
    "minute_findings",
    "combine_decision",
    "assess_delivery_review",
]

# Functions whose judgement the board cannot reach a delivery decision without.
REQUIRED_BOARD_FUNCTIONS = (
    "quality-assurance",
    "project-management",
    "engineering",
    "configuration-management",
    "customer-representative",
)

# Every required function has to be in the room; the ratio is reported so a
# board that convened short can say by how much.
REQUIRED_QUORUM_RATIO = 1.0

# A ratio is a division of small integers and can land a few ULPs off an exact
# value. Absorb the representation error here, not by relaxing the rule.
QUORUM_TOLERANCE = 1e-9

# The minute fields that make the board record defensible after the fact.
REQUIRED_MINUTE_FIELDS = (
    "date",
    "chair-function",
    "attendance",
    "inputs-reviewed",
    "decision",
    "actions",
)

# Dispositions that leave the deviation in the delivered item rather than
# removing it, so the customer has to agree to them for a major finding.
BLOCKING_DISPOSITIONS = ("use-as-is", "repair")

_VALID_DISPOSITIONS = ("use-as-is", "repair", "rework", "scrap", "return-to-supplier")
_VALID_CATEGORIES = ("major", "minor")


def normalize_token(value, label="token"):
    """Return a lowercase, hyphen-joined comparison token for a name."""
    if not isinstance(value, str):
        raise ValueError("%s must be a string, got %r" % (label, value))
    token = "-".join(value.strip().lower().replace("_", " ").replace("-", " ").split())
    if not token:
        raise ValueError("%s must not be blank" % label)
    return token


def _require_bool(value, label):
    if not isinstance(value, bool):
        raise ValueError("%s must be a boolean, got %r" % (label, value))
    return value


def validate_board(members):
    """Return the validated board roster as a list of normalized member records."""
    if not isinstance(members, (list, tuple)) or not members:
        raise ValueError("members must be a non-empty sequence of member records")
    seen = set()
    roster = []
    for i, member in enumerate(members):
        if not isinstance(member, dict):
            raise ValueError("members[%d] must be a mapping" % i)
        if "function" not in member:
            raise ValueError("members[%d] is missing 'function'" % i)
        function = normalize_token(member["function"], "members[%d]['function']" % i)
        if function in seen:
            raise ValueError("board function %r is seated twice" % function)
        seen.add(function)
        roster.append(
            {
                "function": function,
                "present": _require_bool(
                    member.get("present", True), "members[%d]['present']" % i
                ),
                "independent": _require_bool(
                    member.get("independent", True), "members[%d]['independent']" % i
                ),
            }
        )
    return roster


def quorum_ratio(roster, required_functions=None):
    """Return the fraction of required board functions actually present."""
    if required_functions is None:
        required_functions = REQUIRED_BOARD_FUNCTIONS
    if not isinstance(required_functions, (list, tuple)) or not required_functions:
        raise ValueError("required_functions must be a non-empty sequence")
    required = tuple(normalize_token(f, "required function") for f in required_functions)
    present = {m["function"] for m in roster if m["present"]}
    hits = sum(1 for f in required if f in present)
    return float(hits) / float(len(required))


def board_findings(roster, required_functions=None):
    """Return the findings about board composition, authority and independence."""
    if required_functions is None:
        required_functions = REQUIRED_BOARD_FUNCTIONS
    if not isinstance(required_functions, (list, tuple)) or not required_functions:
        raise ValueError("required_functions must be a non-empty sequence")
    required = tuple(normalize_token(f, "required function") for f in required_functions)
    present = {m["function"] for m in roster if m["present"]}
    seated = {m["function"] for m in roster}
    findings = []
    for function in required:
        if function not in seated:
            findings.append("board has no %s member" % function)
        elif function not in present:
            findings.append("%s member did not attend" % function)
    for member in roster:
        if member["function"] == "quality-assurance" and not member["independent"]:
            findings.append(
                "quality-assurance member is not independent of the building organisation"
            )
    ratio = quorum_ratio(roster, required)
    if ratio < REQUIRED_QUORUM_RATIO and not math.isclose(
        ratio, REQUIRED_QUORUM_RATIO, rel_tol=0.0, abs_tol=QUORUM_TOLERANCE
    ):
        findings.append("board quorum ratio %.3f is below the required %.3f" % (ratio, REQUIRED_QUORUM_RATIO))
    return findings


def data_package_findings(presented, required):
    """Return the end-item data package documents the board was not given."""
    if not isinstance(required, (list, tuple)):
        raise ValueError("required data package must be a sequence of document names")
    if not isinstance(presented, (list, tuple)):
        raise ValueError("presented data package must be a sequence of document names")
    have = {normalize_token(d, "presented document") for d in presented}
    findings = []
    for document in required:
        token = normalize_token(document, "required document")
        if token not in have:
            findings.append("end-item data package is missing %s" % token)
    return findings


def nonconformance_finding(record, index=0):
    """Return (severity, message) for one nonconformance brought to the board."""
    if not isinstance(record, dict):
        raise ValueError("nonconformances[%d] must be a mapping" % index)
    for key in ("id", "category", "status"):
        if key not in record:
            raise ValueError("nonconformances[%d] is missing '%s'" % (index, key))
    ncr_id = normalize_token(record["id"], "nonconformances[%d]['id']" % index)
    category = normalize_token(record["category"], "nonconformances[%d]['category']" % index)
    if category not in _VALID_CATEGORIES:
        raise ValueError("nonconformance %s category %r is not one of %s" % (ncr_id, category, _VALID_CATEGORIES))
    status = normalize_token(record["status"], "nonconformances[%d]['status']" % index)
    if status not in ("open", "closed"):
        raise ValueError("nonconformance %s status %r must be open or closed" % (ncr_id, status))
    disposition = record.get("disposition")
    if disposition is not None:
        disposition = normalize_token(disposition, "nonconformances[%d]['disposition']" % index)
        if disposition not in _VALID_DISPOSITIONS:
            raise ValueError(
                "nonconformance %s disposition %r is not one of %s" % (ncr_id, disposition, _VALID_DISPOSITIONS)
            )
    approved = _require_bool(
        record.get("customer_approved", False), "nonconformances[%d]['customer_approved']" % index
    )
    if status == "closed":
        return (None, None)
    if disposition is None:
        return ("blocking", "nonconformance %s is open with no disposition" % ncr_id)
    if disposition in BLOCKING_DISPOSITIONS and category == "major" and not approved:
        return (
            "blocking",
            "major nonconformance %s carried on %s without customer agreement" % (ncr_id, disposition),
        )
    if disposition in BLOCKING_DISPOSITIONS:
        return ("reservation", "nonconformance %s delivered on %s" % (ncr_id, disposition))
    return ("reservation", "nonconformance %s still open on %s" % (ncr_id, disposition))


def nonconformance_findings(records):
    """Return the grouped blocking and reservation findings for the whole set."""
    if records is None:
        records = []
    if not isinstance(records, (list, tuple)):
        raise ValueError("nonconformances must be a sequence of records")
    blocking = []
    reservations = []
    for i, record in enumerate(records):
        severity, message = nonconformance_finding(record, i)
        if severity == "blocking":
            blocking.append(message)
        elif severity == "reservation":
            reservations.append(message)
    return {"blocking": blocking, "reservations": reservations}


def waiver_findings(records):
    """Return the grouped findings for the deviations and waivers offered."""
    if records is None:
        records = []
    if not isinstance(records, (list, tuple)):
        raise ValueError("waivers must be a sequence of records")
    blocking = []
    reservations = []
    for i, record in enumerate(records):
        if not isinstance(record, dict):
            raise ValueError("waivers[%d] must be a mapping" % i)
        if "id" not in record:
            raise ValueError("waivers[%d] is missing 'id'" % i)
        waiver_id = normalize_token(record["id"], "waivers[%d]['id']" % i)
        approved = _require_bool(record.get("approved", False), "waivers[%d]['approved']" % i)
        expired = _require_bool(record.get("expired", False), "waivers[%d]['expired']" % i)
        if not approved:
            blocking.append("waiver %s was never approved" % waiver_id)
        elif expired:
            blocking.append("waiver %s has lapsed and no longer covers the delivery" % waiver_id)
        else:
            reservations.append("delivery carries approved waiver %s" % waiver_id)
    return {"blocking": blocking, "reservations": reservations}


def minute_findings(minutes, required_fields=None):
    """Return the board record fields that were left empty."""
    if not isinstance(minutes, dict):
        raise ValueError("minutes must be a mapping")
    required = tuple(required_fields or REQUIRED_MINUTE_FIELDS)
    present = {normalize_token(k, "minute field"): v for k, v in minutes.items()}
    findings = []
    for field in required:
        token = normalize_token(field, "required minute field")
        value = present.get(token)
        if value is None or (isinstance(value, str) and not value.strip()):
            findings.append("board record has no %s" % token)
        elif isinstance(value, (list, tuple)) and not value:
            findings.append("board record has no %s" % token)
    return findings


def combine_decision(blocking, reservations):
    """Return hold, deliver-with-reservation or deliver for the finding sets."""
    if not isinstance(blocking, (list, tuple)) or not isinstance(reservations, (list, tuple)):
        raise ValueError("blocking and reservations must be sequences")
    if blocking:
        return "hold"
    if reservations:
        return "deliver-with-reservation"
    return "deliver"


def assess_delivery_review(spec):
    """Run the full clause 5.7.3 delivery review board assessment.

    spec keys: members, required_data_package, presented_data_package,
    optional nonconformances, waivers, minutes, required_functions.
    """
    if not isinstance(spec, dict):
        raise ValueError("spec must be a mapping")
    for key in ("members", "required_data_package", "presented_data_package"):
        if key not in spec:
            raise ValueError("spec missing required key '%s'" % key)
    roster = validate_board(spec["members"])
    required_functions = spec.get("required_functions")
    composition = board_findings(roster, required_functions)
    package = data_package_findings(
        spec["presented_data_package"], spec["required_data_package"]
    )
    ncr = nonconformance_findings(spec.get("nonconformances"))
    waiver = waiver_findings(spec.get("waivers"))
    minutes = minute_findings(spec.get("minutes", {}))
    blocking = list(composition) + list(package) + list(ncr["blocking"]) + list(waiver["blocking"]) + list(minutes)
    reservations = list(ncr["reservations"]) + list(waiver["reservations"])
    decision = combine_decision(blocking, reservations)
    return {
        "roster": roster,
        "quorum_ratio": quorum_ratio(roster, required_functions),
        "composition_findings": composition,
        "data_package_findings": package,
        "nonconformance_findings": ncr,
        "waiver_findings": waiver,
        "record_findings": minutes,
        "blocking": blocking,
        "reservations": reservations,
        "decision": decision,
        "deliverable": decision != "hold",
    }
