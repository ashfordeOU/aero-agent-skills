"""Gate decision for the device implementation phase review.

Anchor: ECSS-E-ST-20-40C clause 5.7.5 (the review closing the implementation
phase before validation, qualification and acceptance work proceeds).
Paraphrased into an implementable procedure; no standard text is reproduced.

Procedure implemented here
--------------------------
1. Resolve which phase outputs the review actually owes, from the device
   criticality category and the procurement route, rather than demanding the
   full set of every device.
2. Assess each owed output for presence, maturity and customer approval.
3. Weigh the open review actions, escalating an overdue minor action to a
   blocking one because an action already past its date will not be worked
   before validation starts.
4. Weigh the open nonconformances the same way.
5. Return one of three dispositions: proceed, proceed with actions, or hold.
"""

__all__ = [
    "BLOCKING_SEVERITIES",
    "CATEGORIES",
    "DELIVERABLE_APPLICABILITY",
    "DISPOSITIONS",
    "MATURITY_ORDER",
    "REQUIRED_MATURITY",
    "SEVERITY_WEIGHT",
    "validate_category",
    "owed_deliverables",
    "validate_deliverable",
    "assess_deliverables",
    "validate_action",
    "assess_actions",
    "validate_nonconformance",
    "assess_nonconformances",
    "review_disposition",
    "assess_implementation_phase_review",
]

CATEGORIES = ("A", "B", "C", "D")

MATURITY_ORDER = {
    "draft": 0,
    "preliminary": 1,
    "consolidated": 2,
    "final": 3,
}

# Which categories owe which implementation-phase output. The lighter
# categories carry the build evidence but not the formal part-evaluation
# paperwork, so demanding the full set of a category D device is wrong.
DELIVERABLE_APPLICABILITY = {
    "device-database-implementation-update": ("A", "B", "C", "D"),
    "production-test-report": ("A", "B", "C", "D"),
    "device-validation-plan": ("A", "B", "C", "D"),
    "device-data-sheet": ("A", "B", "C"),
    "device-verification-control-document": ("A", "B"),
    "escc-detail-specification": ("A", "B"),
}

# The maturity each owed output has to have reached by this review.
REQUIRED_MATURITY = {
    "device-database-implementation-update": "final",
    "production-test-report": "final",
    "device-validation-plan": "final",
    "device-data-sheet": "consolidated",
    "device-verification-control-document": "consolidated",
    "escc-detail-specification": "preliminary",
}

SEVERITY_WEIGHT = {"minor": 1, "major": 2, "critical": 3}
BLOCKING_SEVERITIES = ("major", "critical")

DISPOSITIONS = ("proceed", "proceed-with-actions", "hold")


def _text(value, label):
    if not isinstance(value, str):
        raise ValueError("%s must be a string, got %r" % (label, value))
    stripped = value.strip()
    if not stripped:
        raise ValueError("%s must not be empty" % label)
    return stripped


def _whole(value, label):
    if not isinstance(value, int) or isinstance(value, bool):
        raise ValueError("%s must be an integer, got %r" % (label, value))
    return value


def validate_category(category):
    """Return the normalised device criticality category."""
    text = _text(category, "criticality category").upper()
    if text not in CATEGORIES:
        raise ValueError(
            "criticality category %r is not one of %s" % (category, ", ".join(CATEGORIES))
        )
    return text


def owed_deliverables(category):
    """Return the sorted outputs this review owes for the given category."""
    cat = validate_category(category)
    return sorted(
        name for name, cats in DELIVERABLE_APPLICABILITY.items() if cat in cats
    )


def validate_deliverable(record):
    """Return a normalised phase-output record."""
    if not isinstance(record, dict):
        raise ValueError("deliverable record must be a mapping, got %r" % (record,))
    name = _text(record.get("name"), "deliverable name").lower()
    if name not in DELIVERABLE_APPLICABILITY:
        raise ValueError(
            "deliverable %r is not an implementation-phase output; expected one of %s"
            % (name, ", ".join(sorted(DELIVERABLE_APPLICABILITY)))
        )
    maturity = _text(record.get("maturity"), "deliverable %s maturity" % name).lower()
    if maturity not in MATURITY_ORDER:
        raise ValueError("deliverable %s has an unknown maturity %r" % (name, maturity))
    approved = record.get("customer_approved", False)
    if not isinstance(approved, bool):
        raise ValueError("deliverable %s customer_approved must be a boolean" % name)
    return {"name": name, "maturity": maturity, "customer_approved": approved}


def assess_deliverables(deliverables, category):
    """Return the presence, maturity and approval picture for the owed outputs."""
    cat = validate_category(category)
    if not isinstance(deliverables, (list, tuple)):
        raise ValueError("deliverables must be a sequence")
    checked = [validate_deliverable(item) for item in deliverables]
    names = [d["name"] for d in checked]
    if len(set(names)) != len(names):
        raise ValueError("the same deliverable is submitted twice")
    present = {d["name"]: d for d in checked}
    owed = owed_deliverables(cat)
    missing = sorted(name for name in owed if name not in present)
    immature = sorted(
        name
        for name in owed
        if name in present
        and MATURITY_ORDER[present[name]["maturity"]]
        < MATURITY_ORDER[REQUIRED_MATURITY[name]]
    )
    unapproved = sorted(
        name for name in owed if name in present and not present[name]["customer_approved"]
    )
    not_owed = sorted(name for name in present if name not in owed)
    satisfied = len(owed) - len(missing) - len(immature)
    return {
        "owed": owed,
        "missing": missing,
        "immature": immature,
        "unapproved": unapproved,
        "submitted_but_not_owed": not_owed,
        "deliverable_fraction": satisfied / float(len(owed)),
    }


def validate_action(record):
    """Return a normalised review-action record."""
    if not isinstance(record, dict):
        raise ValueError("action record must be a mapping, got %r" % (record,))
    aid = _text(record.get("id"), "action id")
    severity = _text(record.get("severity"), "action %s severity" % aid).lower()
    if severity not in SEVERITY_WEIGHT:
        raise ValueError(
            "action %s has an unknown severity %r; expected one of %s"
            % (aid, severity, ", ".join(sorted(SEVERITY_WEIGHT)))
        )
    status = _text(record.get("status"), "action %s status" % aid).lower()
    if status not in ("open", "closed"):
        raise ValueError("action %s status %r must be open or closed" % (aid, status))
    days = _whole(record.get("days_to_due", 0), "action %s days_to_due" % aid)
    owner = record.get("owner")
    if owner is not None:
        owner = _text(owner, "action %s owner" % aid)
    if status == "open" and owner is None:
        raise ValueError("open action %s must name an owner" % aid)
    return {
        "id": aid,
        "severity": severity,
        "status": status,
        "days_to_due": days,
        "owner": owner,
    }


def assess_actions(actions):
    """Return the open-action load, escalating overdue minor actions."""
    if not isinstance(actions, (list, tuple)):
        raise ValueError("actions must be a sequence")
    checked = [validate_action(item) for item in actions]
    ids = [a["id"] for a in checked]
    if len(set(ids)) != len(ids):
        raise ValueError("duplicate action id in the review action list")
    open_actions = [a for a in checked if a["status"] == "open"]
    overdue = sorted(a["id"] for a in open_actions if a["days_to_due"] < 0)
    blocking = set(a["id"] for a in open_actions if a["severity"] in BLOCKING_SEVERITIES)
    # An action already past its date will not be worked before validation
    # starts, so it blocks regardless of the severity it was raised at.
    blocking.update(overdue)
    load = 0
    for action in open_actions:
        weight = SEVERITY_WEIGHT[action["severity"]]
        if action["days_to_due"] < 0:
            weight = max(weight, SEVERITY_WEIGHT["major"])
        load += weight
    return {
        "open_ids": sorted(a["id"] for a in open_actions),
        "overdue_ids": overdue,
        "blocking_ids": sorted(blocking),
        "weighted_load": load,
    }


def validate_nonconformance(record):
    """Return a normalised nonconformance record."""
    if not isinstance(record, dict):
        raise ValueError("nonconformance record must be a mapping, got %r" % (record,))
    nid = _text(record.get("id"), "nonconformance id")
    severity = _text(record.get("severity"), "nonconformance %s severity" % nid).lower()
    if severity not in SEVERITY_WEIGHT:
        raise ValueError("nonconformance %s has an unknown severity %r" % (nid, severity))
    disposition = _text(record.get("disposition"), "nonconformance %s disposition" % nid).lower()
    if disposition not in ("open", "accepted", "repaired", "scrapped"):
        raise ValueError(
            "nonconformance %s disposition %r is not recognised" % (nid, disposition)
        )
    return {"id": nid, "severity": severity, "disposition": disposition}


def assess_nonconformances(nonconformances):
    """Return the open-nonconformance picture for the review."""
    if not isinstance(nonconformances, (list, tuple)):
        raise ValueError("nonconformances must be a sequence")
    checked = [validate_nonconformance(item) for item in nonconformances]
    ids = [n["id"] for n in checked]
    if len(set(ids)) != len(ids):
        raise ValueError("duplicate nonconformance id")
    still_open = [n for n in checked if n["disposition"] == "open"]
    blocking = sorted(n["id"] for n in still_open if n["severity"] in BLOCKING_SEVERITIES)
    return {
        "open_ids": sorted(n["id"] for n in still_open),
        "blocking_ids": blocking,
    }


def review_disposition(deliverable_report, action_report, nonconformance_report):
    """Return proceed, proceed-with-actions or hold for the phase review."""
    for label, report in (
        ("deliverable_report", deliverable_report),
        ("action_report", action_report),
        ("nonconformance_report", nonconformance_report),
    ):
        if not isinstance(report, dict):
            raise ValueError("%s must be a mapping" % label)
    for key in ("missing", "immature", "unapproved"):
        if key not in deliverable_report:
            raise ValueError("deliverable_report missing key '%s'" % key)
    if "blocking_ids" not in action_report or "open_ids" not in action_report:
        raise ValueError("action_report must carry blocking_ids and open_ids")
    if "blocking_ids" not in nonconformance_report:
        raise ValueError("nonconformance_report must carry blocking_ids")
    held = (
        deliverable_report["missing"]
        or deliverable_report["immature"]
        or deliverable_report["unapproved"]
        or action_report["blocking_ids"]
        or nonconformance_report["blocking_ids"]
    )
    if held:
        return "hold"
    if action_report["open_ids"] or nonconformance_report.get("open_ids"):
        return "proceed-with-actions"
    return "proceed"


def assess_implementation_phase_review(spec):
    """Run the full clause 5.7.5 implementation phase review assessment.

    spec keys: category, deliverables; optional actions, nonconformances.
    """
    if not isinstance(spec, dict):
        raise ValueError("spec must be a mapping")
    for key in ("category", "deliverables"):
        if key not in spec:
            raise ValueError("spec missing required key '%s'" % key)
    category = validate_category(spec["category"])
    deliverables = assess_deliverables(spec["deliverables"], category)
    actions = assess_actions(spec.get("actions", []))
    nonconformances = assess_nonconformances(spec.get("nonconformances", []))
    disposition = review_disposition(deliverables, actions, nonconformances)

    findings = []
    if deliverables["missing"]:
        findings.append("owed output(s) not submitted: %s" % ", ".join(deliverables["missing"]))
    if deliverables["immature"]:
        findings.append(
            "owed output(s) below the maturity this review needs: %s"
            % ", ".join(deliverables["immature"])
        )
    if deliverables["unapproved"]:
        findings.append(
            "owed output(s) without customer approval: %s"
            % ", ".join(deliverables["unapproved"])
        )
    if deliverables["submitted_but_not_owed"]:
        findings.append(
            "output(s) submitted that category %s does not owe: %s"
            % (category, ", ".join(deliverables["submitted_but_not_owed"]))
        )
    if actions["overdue_ids"]:
        findings.append(
            "open action(s) already past their date, escalated to blocking: %s"
            % ", ".join(actions["overdue_ids"])
        )
    if actions["blocking_ids"]:
        findings.append("blocking open action(s): %s" % ", ".join(actions["blocking_ids"]))
    if nonconformances["blocking_ids"]:
        findings.append(
            "blocking open nonconformance(s): %s" % ", ".join(nonconformances["blocking_ids"])
        )

    return {
        "category": category,
        "deliverables": deliverables,
        "actions": actions,
        "nonconformances": nonconformances,
        "deliverable_fraction": deliverables["deliverable_fraction"],
        "weighted_action_load": actions["weighted_load"],
        "disposition": disposition,
        "may_proceed": disposition != "hold",
        "findings": findings,
    }
