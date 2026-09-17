"""The post-receipt control route for a Class 3 EEE lot.

Anchor: ECSS-Q-ST-60C clause 6.5.1 (the entry point to the control measures a
Class 3 part is put through once it has been received). Paraphrased into an
implementable procedure; no standard text is reproduced.

Procedure implemented here
--------------------------
1. Derive which control activities this particular lot owes from its profile,
   keeping the activities every lot owes apart from the ones an attribute of the
   part or of the delivery brings in.
2. Close the set over its prerequisites, because a triggered activity can
   depend on one the profile never triggered, then resolve the whole set into
   the order the prerequisites impose by a deterministic topological pass that
   refuses a cycle and refuses a prerequisite missing from the route.
3. Admit an omission only where the activity is attribute-driven and a recorded
   justification carries an identifier and a named approver.
4. Read the closure records against the route, and report an activity recorded
   as closed while something it depends on is still open.
5. Take a weighted completeness over the route so a heavy activity left open is
   not offset by several light ones that are closed.
6. Return one release decision for the lot, with every reason named.
"""

__all__ = [
    "RELEASE_VERDICTS",
    "CONTROL_ACTIVITIES",
    "PROFILE_ATTRIBUTES",
    "RECORD_STATUSES",
    "mandatory_activities",
    "applicable_activities",
    "resolve_route",
    "omission_admissible",
    "ordering_findings",
    "route_completeness",
    "release_verdict",
    "assess_control_route",
]

# Release decisions, from a lot that may go to stores to one that may not stay.
RELEASE_VERDICTS = (
    "release-to-stores",
    "release-pending-conditional",
    "hold-in-quarantine",
    "reject-lot",
)

# The control measures this clause opens onto. "trigger" is the profile
# attribute that brings an activity in; None marks one every lot owes.
CONTROL_ACTIVITIES = {
    "receiving-inspection": {
        "trigger": None,
        "requires": (),
        "weight": 3,
    },
    "documentation-review": {
        "trigger": None,
        "requires": (),
        "weight": 3,
    },
    "external-visual-examination": {
        "trigger": None,
        "requires": ("receiving-inspection",),
        "weight": 2,
    },
    "lot-homogeneity-check": {
        "trigger": "mixed_date_codes",
        "requires": ("documentation-review",),
        "weight": 2,
    },
    "incoming-electrical-verification": {
        "trigger": "manufacturer_screening_incomplete",
        "requires": ("external-visual-examination", "lot-homogeneity-check"),
        "weight": 3,
    },
    "destructive-physical-analysis": {
        "trigger": "destructive_analysis_required",
        "requires": ("external-visual-examination",),
        "weight": 4,
    },
    "radiation-lot-verification": {
        "trigger": "radiation_sensitive",
        "requires": ("documentation-review",),
        "weight": 4,
    },
    "particle-impact-noise-detection": {
        "trigger": "cavity_device",
        "requires": ("external-visual-examination",),
        "weight": 2,
    },
    "serialisation-and-bagging": {
        "trigger": None,
        "requires": ("external-visual-examination",),
        "weight": 1,
    },
}

# The attributes a lot profile may carry; anything else is a typo, not a flag.
PROFILE_ATTRIBUTES = tuple(
    sorted(
        entry["trigger"]
        for entry in CONTROL_ACTIVITIES.values()
        if entry["trigger"] is not None
    )
)

RECORD_STATUSES = ("open", "closed", "failed")


def mandatory_activities():
    """Return the activities every received lot owes, whatever it is."""
    return tuple(
        sorted(
            name
            for name, entry in CONTROL_ACTIVITIES.items()
            if entry["trigger"] is None
        )
    )


def applicable_activities(profile):
    """Return the activities this lot owes, mandatory ones plus triggered ones."""
    if not isinstance(profile, dict):
        raise ValueError("profile must be a mapping of attribute to bool")
    for key, value in profile.items():
        if key not in PROFILE_ATTRIBUTES:
            raise ValueError("profile carries unknown attribute %r" % (key,))
        if not isinstance(value, bool):
            raise ValueError("profile[%r] must be a bool, got %r" % (key, value))
    owed = set(mandatory_activities())
    for name, entry in CONTROL_ACTIVITIES.items():
        trigger = entry["trigger"]
        if trigger is not None and profile.get(trigger, False):
            owed.add(name)
    return tuple(sorted(owed))


def resolve_route(activities):
    """Return the activities in the order their prerequisites impose.

    The pass is deterministic: whenever several activities are ready at once the
    lexicographically first is taken, so the same route comes out every time and
    on every platform.
    """
    if not isinstance(activities, (list, tuple, set, frozenset)):
        raise ValueError("activities must be a collection of activity names")
    names = [str(name).strip() for name in activities]
    if len(set(names)) != len(names):
        raise ValueError("an activity is named twice in the route")
    unknown = [name for name in names if name not in CONTROL_ACTIVITIES]
    if unknown:
        raise ValueError("unknown control activity %r" % (sorted(unknown)[0],))
    present = set(names)
    pending = {}
    for name in names:
        requires = set(CONTROL_ACTIVITIES[name]["requires"])
        missing = requires - present
        if missing:
            raise ValueError(
                "%s requires %s, which is not in the route"
                % (name, sorted(missing)[0])
            )
        pending[name] = requires
    ordered = []
    while pending:
        ready = sorted(name for name, needs in pending.items() if not needs)
        if not ready:
            raise ValueError(
                "the prerequisites form a cycle across %s" % sorted(pending)
            )
        chosen = ready[0]
        ordered.append(chosen)
        del pending[chosen]
        for needs in pending.values():
            needs.discard(chosen)
    return tuple(ordered)


def omission_admissible(activity, justification):
    """Return whether an activity may be dropped, and why it may not."""
    name = str(activity).strip()
    if name not in CONTROL_ACTIVITIES:
        raise ValueError("unknown control activity %r" % (activity,))
    reasons = []
    if CONTROL_ACTIVITIES[name]["trigger"] is None:
        reasons.append("this activity is owed by every received lot")
    if not isinstance(justification, dict) or not justification:
        reasons.append("no justification was recorded")
        return {"admissible": False, "reasons": tuple(reasons)}
    for field in ("reference", "approved_by"):
        value = justification.get(field)
        if not isinstance(value, str) or not value.strip():
            reasons.append("the justification carries no %s" % field.replace("_", " "))
    return {"admissible": not reasons, "reasons": tuple(reasons)}


def ordering_findings(route, records):
    """Return activities closed while something they depend on is still open."""
    if not isinstance(route, (list, tuple)):
        raise ValueError("route must be a sequence of activity names")
    if not isinstance(records, dict):
        raise ValueError("records must be a mapping of activity to status record")
    for name, record in records.items():
        if str(name).strip() not in CONTROL_ACTIVITIES:
            raise ValueError("records name unknown control activity %r" % (name,))
        status = record.get("status") if isinstance(record, dict) else record
        if status not in RECORD_STATUSES:
            raise ValueError(
                "record for %r must carry a status in %s, got %r"
                % (name, RECORD_STATUSES, status)
            )

    def status_of(name):
        record = records.get(name)
        if record is None:
            return "open"
        return record.get("status") if isinstance(record, dict) else record

    findings = []
    for name in route:
        if status_of(name) != "closed":
            continue
        for prerequisite in CONTROL_ACTIVITIES[name]["requires"]:
            if prerequisite in route and status_of(prerequisite) != "closed":
                findings.append(
                    "%s is recorded closed while %s is not" % (name, prerequisite)
                )
    return tuple(findings)


def route_completeness(route, records):
    """Return the weighted share of the route that is closed.

    Weighting matters because a destructive analysis left open is not offset by
    a serialisation step that is closed, and a plain count says it is.
    """
    if not isinstance(route, (list, tuple)) or not route:
        raise ValueError("route must be a non-empty sequence of activity names")
    if not isinstance(records, dict):
        raise ValueError("records must be a mapping of activity to status record")
    total = 0
    closed = 0
    open_names = []
    failed_names = []
    for name in route:
        if name not in CONTROL_ACTIVITIES:
            raise ValueError("unknown control activity %r" % (name,))
        weight = CONTROL_ACTIVITIES[name]["weight"]
        total += weight
        record = records.get(name)
        status = (
            "open"
            if record is None
            else (record.get("status") if isinstance(record, dict) else record)
        )
        if status == "closed":
            closed += weight
        elif status == "failed":
            failed_names.append(name)
        else:
            open_names.append(name)
    return {
        "weight_total": total,
        "weight_closed": closed,
        "index": closed / total,
        "open": tuple(open_names),
        "failed": tuple(failed_names),
        "complete": closed == total,
    }


def release_verdict(mandatory_open, conditional_open, failed, ordering_breaches):
    """Return the release decision the lot has earned."""
    for label, value in (
        ("mandatory_open", mandatory_open),
        ("conditional_open", conditional_open),
        ("failed", failed),
        ("ordering_breaches", ordering_breaches),
    ):
        if not isinstance(value, int) or isinstance(value, bool) or value < 0:
            raise ValueError("%s must be a non-negative integer, got %r" % (label, value))
    if failed:
        return "reject-lot"
    if ordering_breaches or mandatory_open:
        return "hold-in-quarantine"
    if conditional_open:
        return "release-pending-conditional"
    return "release-to-stores"


def assess_control_route(profile, records=None, omissions=None):
    """Run the full clause 6.5.1 post-receipt control assessment for one lot."""
    owed = set(applicable_activities(profile))
    records = records or {}
    omissions = omissions or {}
    if not isinstance(omissions, dict):
        raise ValueError("omissions must be a mapping of activity to justification")

    findings = []

    # A triggered activity can depend on one the profile never triggered, so the
    # dependency closure is taken before anything is dropped. An activity pulled
    # in this way is reported, not faulted: the route needed it.
    pulled_in = []
    changed = True
    while changed:
        changed = False
        for name in sorted(owed):
            for prerequisite in CONTROL_ACTIVITIES[name]["requires"]:
                if prerequisite not in owed:
                    owed.add(prerequisite)
                    pulled_in.append(prerequisite)
                    changed = True

    candidates = []
    refused = []
    for activity, justification in omissions.items():
        name = str(activity).strip()
        if name not in owed:
            raise ValueError("%s is not in this lot's route and cannot be omitted" % name)
        verdict = omission_admissible(name, justification)
        if verdict["admissible"]:
            candidates.append(name)
        else:
            refused.append((name, verdict["reasons"]))

    # An omission that something still in the route depends on is refused, however
    # well justified: dropping it would leave the route unresolvable.
    remaining = owed - set(candidates)
    dropped = []
    for name in sorted(candidates):
        depended_on = sorted(
            other
            for other in remaining
            if name in CONTROL_ACTIVITIES[other]["requires"]
        )
        if depended_on:
            refused.append(
                (name, ("%s in the route depends on it" % depended_on[0],))
            )
        else:
            dropped.append(name)
    for name, reasons in sorted(refused):
        findings.append(
            "the omission of %s is not admissible: %s" % (name, "; ".join(reasons))
        )
    owed -= set(dropped)

    route = resolve_route(owed)
    breaches = ordering_findings(route, records)
    findings.extend(breaches)
    completeness = route_completeness(route, records)

    mandatory = set(mandatory_activities())
    mandatory_open = [
        name for name in completeness["open"] if name in mandatory
    ]
    conditional_open = [
        name for name in completeness["open"] if name not in mandatory
    ]
    for name in completeness["failed"]:
        findings.append("%s is recorded as failed" % name)
    for name in mandatory_open:
        findings.append("%s is owed by every lot and is still open" % name)

    verdict = release_verdict(
        len(mandatory_open),
        len(conditional_open),
        len(completeness["failed"]),
        len(breaches),
    )
    return {
        "route": route,
        "route_length": len(route),
        "omitted": tuple(sorted(dropped)),
        "pulled_in": tuple(sorted(set(pulled_in))),
        "completeness": completeness,
        "mandatory_open": tuple(mandatory_open),
        "conditional_open": tuple(conditional_open),
        "ordering_breaches": breaches,
        "verdict": verdict,
        "findings": findings,
        "route_clear": not findings,
    }
