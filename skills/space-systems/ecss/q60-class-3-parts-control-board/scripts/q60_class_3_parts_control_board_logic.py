"""Customer-triggered board approval of part selection and usage, class 3.

Anchor: ECSS-Q-ST-60C clause 6.1.3 (customer-triggered board approval of part
selection and usage for class 3 equipment). Paraphrased into an implementable
procedure; no standard text is reproduced.

Procedure implemented here
--------------------------
1. Read the customer triggers declared against one part usage and keep only
   the recognised ones that are active and carry a reference.
2. Decide whether a board approval is required at all: on class 3 the board
   convenes because the customer asked for it, not by default.
3. Where it is required, test the approval record: raised before the
   procurement commitment, a board chair named, the customer represented, both
   the selection and the usage inside its scope, and the part identified.
4. Return one disposition per usage: board-approval-not-required,
   board-approval-valid, board-approval-deficient or board-approval-missing.
5. Take docket readiness across the usages and judge it against its floor.
"""

import datetime
import math

__all__ = [
    "APPROVAL_SCOPES",
    "BOUND_TOLERANCE",
    "CUSTOMER_TRIGGERS",
    "DOCKET_READINESS_FLOOR",
    "usage_id",
    "recognised_triggers",
    "active_triggers",
    "trigger_defects",
    "board_approval_required",
    "approval_scopes",
    "scope_coverage",
    "approval_lead_days",
    "approval_defects",
    "usage_disposition",
    "compile_class_3_board_approval",
    "approval_docket",
    "docket_readiness",
    "readiness_meets_floor",
]

# Readiness is a quotient of small counts; a docket sitting exactly on the
# floor can land a few ULP on the wrong side. Absorb the representation error
# here, never by moving the floor itself.
BOUND_TOLERANCE = 1e-9

# The ways a customer puts a class 3 part usage in front of the board. Nothing
# outside this list convenes it.
CUSTOMER_TRIGGERS = (
    "customer-contract-clause",
    "customer-written-request",
    "customer-flagged-critical-function",
    "customer-reserved-part-family",
    "customer-deviation-response",
)

_TRIGGER_ORDER = {name: index for index, name in enumerate(CUSTOMER_TRIGGERS)}

# The two things the board approves. An approval covering one of them has not
# approved the other.
APPROVAL_SCOPES = ("part-selection", "part-usage")

_SCOPE_ORDER = {name: index for index, name in enumerate(APPROVAL_SCOPES)}

# Every usage on the docket has to clear; the board carries no allowance for a
# part that flies without its approval.
DOCKET_READINESS_FLOOR = 1.0


def _require_number(value, label, allow_negative=False):
    """Return a validated finite float or raise."""
    if not isinstance(value, (int, float)) or isinstance(value, bool):
        raise ValueError("%s must be a real number, got %r" % (label, value))
    number = float(value)
    if not math.isfinite(number):
        raise ValueError("%s must be finite, got %r" % (label, value))
    if not allow_negative and number < 0.0:
        raise ValueError("%s must not be negative, got %g" % (label, number))
    return number


def _require_text(value, label):
    """Return a stripped non-empty string or raise."""
    if not isinstance(value, str) or not value.strip():
        raise ValueError("%s must be a non-empty string, got %r" % (label, value))
    return value.strip()


def _is_text(value):
    return isinstance(value, str) and bool(value.strip())


def _require_date(value, label):
    """Return a calendar date read from an ISO day stamp, or raise."""
    text = _require_text(value, label)
    try:
        return datetime.date.fromisoformat(text)
    except ValueError:
        raise ValueError("%s must be an ISO calendar day, got %r" % (label, value))


def _require_usage(usage):
    if not isinstance(usage, dict):
        raise ValueError("usage must be a mapping, got %r" % (usage,))
    return usage


def usage_id(usage):
    """Return the usage identifier, or a stable placeholder when none is given."""
    _require_usage(usage)
    if _is_text(usage.get("usage_id")):
        return usage["usage_id"].strip()
    return "unnamed-usage"


def _trigger_entries(usage):
    _require_usage(usage)
    entries = usage.get("triggers", [])
    if not isinstance(entries, (list, tuple)):
        raise ValueError("triggers must be a sequence")
    for entry in entries:
        if not isinstance(entry, dict):
            raise ValueError("trigger must be a mapping, got %r" % (entry,))
    return list(entries)


def _trigger_name(entry):
    named = entry.get("trigger")
    if not _is_text(named):
        return None
    folded = named.strip().casefold()
    if folded not in _TRIGGER_ORDER:
        return None
    return folded


def recognised_triggers(usage):
    """Return the recognised customer triggers declared, in report order."""
    names = []
    for entry in _trigger_entries(usage):
        name = _trigger_name(entry)
        if name is not None and name not in names:
            names.append(name)
    return sorted(names, key=lambda name: _TRIGGER_ORDER[name])


def active_triggers(usage):
    """Return the triggers that actually put the usage in front of the board.

    A trigger counts when it is recognised, marked active and carries the
    reference that shows where the customer asked for it.
    """
    names = []
    for entry in _trigger_entries(usage):
        name = _trigger_name(entry)
        if name is None or name in names:
            continue
        if entry.get("active") is not True:
            continue
        if not _is_text(entry.get("reference")):
            continue
        names.append(name)
    return sorted(names, key=lambda name: _TRIGGER_ORDER[name])


def trigger_defects(usage):
    """Return the defect codes the declared trigger list carries."""
    defects = []
    unknown = False
    unevidenced = False
    for entry in _trigger_entries(usage):
        if _trigger_name(entry) is None:
            unknown = True
            continue
        if entry.get("active") is True and not _is_text(entry.get("reference")):
            unevidenced = True
    if unknown:
        defects.append("trigger-not-recognised")
    if unevidenced:
        defects.append("active-trigger-without-reference")
    return defects


def board_approval_required(usage):
    """Return True when a customer trigger puts this usage in front of the board."""
    return bool(active_triggers(usage))


def approval_scopes(approval):
    """Return the recognised scopes one approval record covers, in report order."""
    if not isinstance(approval, dict):
        raise ValueError("approval must be a mapping, got %r" % (approval,))
    declared = approval.get("scopes", [])
    if not isinstance(declared, (list, tuple, set, frozenset)):
        raise ValueError("scopes must be a sequence or set")
    names = []
    for item in declared:
        name = _require_text(item, "scope").casefold()
        if name in _SCOPE_ORDER and name not in names:
            names.append(name)
    return sorted(names, key=lambda name: _SCOPE_ORDER[name])


def scope_coverage(approval):
    """Return the share of the two approval scopes one record covers."""
    return len(approval_scopes(approval)) / float(len(APPROVAL_SCOPES))


def approval_lead_days(usage):
    """Return the days between the board approval and the procurement commitment.

    A positive number is an approval taken before the commitment; a negative
    one is an approval taken after the project had already committed.
    """
    _require_usage(usage)
    approval = usage.get("approval")
    if not isinstance(approval, dict):
        raise ValueError("usage carries no approval record")
    approved = _require_date(approval.get("approval_date"), "approval date")
    committed = _require_date(usage.get("commitment_date"), "commitment date")
    return (committed - approved).days


def approval_defects(usage):
    """Return the defect codes the board approval record carries.

    An empty list means the approval stands. approval keys read here:
    approval_date, board_chair, customer_representative, scopes and
    part_identity; the usage supplies commitment_date.
    """
    _require_usage(usage)
    approval = usage.get("approval")
    if not isinstance(approval, dict):
        return ["approval-record-absent"]
    defects = []
    try:
        approved = _require_date(approval.get("approval_date"), "approval date")
    except ValueError:
        approved = None
        defects.append("approval-date-not-stated")
    try:
        committed = _require_date(usage.get("commitment_date"), "commitment date")
    except ValueError:
        committed = None
        defects.append("commitment-date-not-stated")
    if approved is not None and committed is not None:
        if (committed - approved).days < 0:
            defects.append("approval-after-commitment")
    if not _is_text(approval.get("board_chair")):
        defects.append("board-chair-not-named")
    if not _is_text(approval.get("customer_representative")):
        defects.append("customer-representative-absent")
    covered = approval_scopes(approval)
    for scope in APPROVAL_SCOPES:
        if scope not in covered:
            defects.append("%s-not-approved" % scope)
    if not _is_text(approval.get("part_identity")):
        defects.append("part-identity-not-stated")
    return defects


def usage_disposition(usage):
    """Return the board disposition of one class 3 part usage."""
    _require_usage(usage)
    if not board_approval_required(usage):
        return "board-approval-not-required"
    defects = approval_defects(usage)
    if defects == ["approval-record-absent"]:
        return "board-approval-missing"
    if defects:
        return "board-approval-deficient"
    return "board-approval-valid"


def compile_class_3_board_approval(usage):
    """Grade the clause 6.1.3 board position of one class 3 part usage.

    usage keys: usage_id, triggers, commitment_date and approval.
    """
    _require_usage(usage)
    required = board_approval_required(usage)
    disposition = usage_disposition(usage)
    approval = usage.get("approval")
    coverage = scope_coverage(approval) if isinstance(approval, dict) else 0.0
    lead = None
    if isinstance(approval, dict):
        try:
            lead = approval_lead_days(usage)
        except ValueError:
            lead = None
    return {
        "usage": usage_id(usage),
        "recognised_triggers": recognised_triggers(usage),
        "active_triggers": active_triggers(usage),
        "trigger_defects": trigger_defects(usage),
        "board_approval_required": required,
        "approval_defects": approval_defects(usage) if required else [],
        "approval_scope_coverage": coverage,
        "approval_lead_days": lead,
        "disposition": disposition,
        "usage_cleared": disposition in ("board-approval-not-required",
                                         "board-approval-valid"),
    }


def approval_docket(usages):
    """Return one board position per usage, ordered by usage identifier."""
    if not isinstance(usages, (list, tuple)):
        raise ValueError("usages must be a sequence")
    if not usages:
        raise ValueError("usages must name at least one part usage")
    entries = [compile_class_3_board_approval(usage) for usage in usages]
    return sorted(entries, key=lambda entry: entry["usage"])


def docket_readiness(usages):
    """Return the share of usages that are cleared for the equipment."""
    entries = approval_docket(usages)
    cleared = [entry for entry in entries if entry["usage_cleared"]]
    return len(cleared) / float(len(entries))


def readiness_meets_floor(readiness, floor=DOCKET_READINESS_FLOOR):
    """Return True when the docket readiness reaches its floor."""
    value = _require_number(readiness, "readiness")
    limit = _require_number(floor, "floor")
    if value > 1.0 + BOUND_TOLERANCE:
        raise ValueError("readiness must not exceed one, got %g" % value)
    return value >= limit - BOUND_TOLERANCE
