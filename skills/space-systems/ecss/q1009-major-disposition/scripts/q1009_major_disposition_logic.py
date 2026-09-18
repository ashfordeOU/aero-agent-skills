#!/usr/bin/env python3
"""Disposition of a major nonconformance at the customer review board.

Anchor: ECSS-Q-ST-10-09C clause 5.2.3.4. The procedure below is a
paraphrase into implementable steps; no standard text is reproduced.

A major nonconformance is the one the customer's nonconformance review
board owns. The board does three things in one sitting: it decides which
disposition the affected items may be given, it attaches the conditions
the disposition is granted against, and it records the concession that a
departure left in the delivered hardware earns.

Dispositions
    use-as-is           the item stays as built, the requirement is not met
    rework              the item is brought back to the original requirement
    repair              the item is made usable by a departure from drawing
    scrap               the item is withdrawn from the programme
    return-to-supplier  the item goes back to the party that furnished it

Only rework and scrap leave nothing behind: use-as-is and repair both
hand over hardware that departs from an agreed requirement, so both earn
a recorded concession decision with a justification behind it.

Standard library only, offline, deterministic.
"""

from __future__ import annotations

DISPOSITIONS = (
    "use-as-is",
    "rework",
    "repair",
    "scrap",
    "return-to-supplier",
)

CONCESSION_DISPOSITIONS = ("use-as-is", "repair")

IMPACT_FLAGS = ("safety_impact", "interface_impact", "lifetime_impact")

BOARD_ROLES = (
    "customer-representative",
    "product-assurance",
    "engineering",
    "project-management",
    "supplier-representative",
)

QUORUM_ROLES = ("customer-representative", "product-assurance", "engineering")

VERDICT_GRANTED = "disposition-granted"
VERDICT_CONDITIONAL = "disposition-granted-with-open-conditions"
VERDICT_REFUSED = "disposition-refused"
VERDICT_DEFERRED = "disposition-deferred-no-quorum"
VERDICT_INCOMPLETE = "disposition-returned-incomplete"


def _require_text(name, value):
    if not isinstance(value, str) or not value.strip():
        raise ValueError("%s must be a non-empty string, got %r" % (name, value))
    return value.strip()


def _require_count(name, value):
    if isinstance(value, bool) or not isinstance(value, int):
        raise ValueError("%s must be an integer, got %r" % (name, value))
    if value <= 0:
        raise ValueError("%s must be greater than zero, got %r" % (name, value))
    return value


def _require_flag(name, value):
    if not isinstance(value, bool):
        raise ValueError("%s must be a boolean, got %r" % (name, value))
    return value


def _require_choice(name, value, allowed):
    if value not in allowed:
        raise ValueError(
            "%s must be one of %s, got %r" % (name, ", ".join(allowed), value)
        )
    return value


def board_quorum(members):
    """Check the roles sitting on the board against the quorum it needs."""
    if not isinstance(members, (list, tuple)):
        raise ValueError("members must be a list of role names, got %r" % (members,))
    if not members:
        raise ValueError("members must not be empty; a board sits with people on it")
    seen = []
    for i, role in enumerate(members):
        _require_choice("members[%d]" % i, role, BOARD_ROLES)
        if role not in seen:
            seen.append(role)
    missing = [role for role in QUORUM_ROLES if role not in seen]
    return {
        "roles_present": tuple(seen),
        "missing_roles": tuple(missing),
        "quorate": not missing,
    }


def requires_concession(disposition):
    """True when the disposition leaves a departure in delivered hardware."""
    _require_choice("disposition", disposition, DISPOSITIONS)
    return disposition in CONCESSION_DISPOSITIONS


def admissible_dispositions(case):
    """Dispositions the board may grant for this item, with the reasons.

    A departure that is left in the hardware may not touch safety, an
    interface or the declared lifetime: those three close use-as-is and
    repair off entirely. Rework needs the item to be reworkable, repair
    needs an approved repair procedure, and return-to-supplier only
    exists when somebody else furnished the item.
    """
    if not isinstance(case, dict):
        raise ValueError("case must be a mapping, got %r" % (case,))
    for flag in IMPACT_FLAGS:
        _require_flag(flag, case.get(flag))
    rework_feasible = _require_flag("rework_feasible", case.get("rework_feasible"))
    repair_approved = _require_flag(
        "repair_procedure_approved", case.get("repair_procedure_approved")
    )
    supplier_furnished = _require_flag(
        "supplier_furnished", case.get("supplier_furnished")
    )
    blocking = [flag for flag in IMPACT_FLAGS if case[flag]]
    reasons = {}
    admissible = []
    for disposition in DISPOSITIONS:
        blockers = []
        if disposition in CONCESSION_DISPOSITIONS and blocking:
            blockers.append(
                "departure touches %s" % ", ".join(f.replace("_", " ") for f in blocking)
            )
        if disposition == "repair" and not repair_approved:
            blockers.append("no approved repair procedure")
        if disposition == "rework" and not rework_feasible:
            blockers.append("item cannot be reworked to the requirement")
        if disposition == "return-to-supplier" and not supplier_furnished:
            blockers.append("item was not supplier furnished")
        if blockers:
            reasons[disposition] = "; ".join(blockers)
        else:
            admissible.append(disposition)
    return {"admissible": tuple(admissible), "blocked": reasons}


def evaluate_conditions(conditions):
    """Grade the conditions a disposition is granted against."""
    if conditions is None:
        conditions = []
    if not isinstance(conditions, (list, tuple)):
        raise ValueError("conditions must be a list, got %r" % (conditions,))
    open_ids = []
    findings = []
    seen_ids = set()
    for i, condition in enumerate(conditions):
        if not isinstance(condition, dict):
            raise ValueError("conditions[%d] must be a mapping, got %r" % (i, condition))
        cid = _require_text("conditions[%d].id" % i, condition.get("id"))
        if cid in seen_ids:
            raise ValueError("duplicate condition id %r" % cid)
        seen_ids.add(cid)
        _require_text("conditions[%d].text" % i, condition.get("text"))
        owner = condition.get("owner")
        if not isinstance(owner, str) or not owner.strip():
            findings.append("condition %s has no owner to carry it" % cid)
        verification = condition.get("verification")
        if not isinstance(verification, str) or not verification.strip():
            findings.append("condition %s names no way of verifying it" % cid)
        if not _require_flag("conditions[%d].closed" % i, condition.get("closed", False)):
            open_ids.append(cid)
    return {
        "count": len(conditions),
        "open_ids": tuple(open_ids),
        "all_closed": not open_ids,
        "findings": tuple(findings),
    }


def concession_record(case, disposition):
    """The concession entry a departure-bearing disposition has to leave."""
    if not requires_concession(disposition):
        return None
    return {
        "ncr_id": _require_text("ncr_id", case.get("ncr_id")),
        "requirement_id": _require_text("requirement_id", case.get("requirement_id")),
        "disposition": disposition,
        "quantity_affected": _require_count(
            "quantity_affected", case.get("quantity_affected")
        ),
        "justification": _require_text("justification", case.get("justification")),
        "approved_by": tuple(board_quorum(case.get("board_members"))["roles_present"]),
    }


def dispose_major_nonconformance(case):
    """Full clause 5.2.3.4 board decision on one major nonconformance."""
    if not isinstance(case, dict):
        raise ValueError("case must be a mapping, got %r" % (case,))
    severity = _require_choice(
        "severity", case.get("severity"), ("major", "minor")
    )
    if severity != "major":
        raise ValueError(
            "clause 5.2.3.4 covers major nonconformances at the customer board; "
            "a minor one is dispositioned by the supplier's own board"
        )
    ncr_id = _require_text("ncr_id", case.get("ncr_id"))
    _require_text("requirement_id", case.get("requirement_id"))
    quantity = _require_count("quantity_affected", case.get("quantity_affected"))
    requested = _require_choice(
        "requested_disposition", case.get("requested_disposition"), DISPOSITIONS
    )
    quorum = board_quorum(case.get("board_members"))
    options = admissible_dispositions(case)
    conditions = evaluate_conditions(case.get("conditions"))
    findings = list(conditions["findings"])
    needs_concession = requires_concession(requested)
    result = {
        "ncr_id": ncr_id,
        "quantity_affected": quantity,
        "requested_disposition": requested,
        "granted_disposition": None,
        "admissible": options["admissible"],
        "quorum": quorum,
        "conditions": conditions,
        "concession_required": needs_concession,
        "concession": None,
        "release_permitted": False,
        "findings": findings,
    }
    if not quorum["quorate"]:
        findings.append(
            "board is not quorate; missing %s" % ", ".join(quorum["missing_roles"])
        )
        result["verdict"] = VERDICT_DEFERRED
        return result
    if requested not in options["admissible"]:
        findings.append(
            "%s is not admissible here: %s" % (requested, options["blocked"][requested])
        )
        result["verdict"] = VERDICT_REFUSED
        return result
    if needs_concession:
        justification = case.get("justification")
        if not isinstance(justification, str) or not justification.strip():
            findings.append(
                "%s leaves a departure in delivered hardware and carries no "
                "justification to record against it" % requested
            )
            result["verdict"] = VERDICT_INCOMPLETE
            return result
        result["concession"] = concession_record(case, requested)
    result["granted_disposition"] = requested
    if conditions["all_closed"]:
        result["verdict"] = VERDICT_GRANTED
        result["release_permitted"] = True
    else:
        result["verdict"] = VERDICT_CONDITIONAL
        findings.append(
            "%d condition(s) still open: %s"
            % (len(conditions["open_ids"]), ", ".join(conditions["open_ids"]))
        )
    return result
