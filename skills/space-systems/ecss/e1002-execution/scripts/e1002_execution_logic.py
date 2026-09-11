"""ECSS-E-ST-10-02 clause 5.3.1 verification execution (paraphrase, not copy).

Common-knowledge summary (standards-map.yaml, ecss: gated false): clause 5.3.1
governs the execution of verification activities against the verification plan
and verification control document. An activity may not start until its
readiness conditions all hold -- approved procedure, available facility, the
article in its declared configuration, qualified personnel. A nonconformance
raised during execution suspends the activity until it is dispositioned; a
departure from the approved procedure requires an approved deviation BEFORE
execution continues, not a note afterwards. What was actually run is recorded
against what was planned, because an as-run that silently differs from the
as-planned invalidates the evidence the activity was meant to produce.
"""

ACTIVITY_STATES = ("planned", "ready", "executing", "suspended", "complete")
READINESS_CONDITIONS = ("procedure_approved", "facility_available",
                        "article_configuration_confirmed", "personnel_qualified")
NC_DISPOSITIONS = ("accept_as_is", "repair", "rework", "scrap", "open")


def validate_state(state):
    """Return state if it is a recognized activity state, else raise."""
    if state not in ACTIVITY_STATES:
        raise ValueError("unknown activity state: %r" % (state,))
    return state


def validate_disposition(disposition):
    """Return disposition if recognized, else raise ValueError."""
    if disposition not in NC_DISPOSITIONS:
        raise ValueError("unknown nonconformance disposition: %r" % (disposition,))
    return disposition


def unmet_readiness(activity):
    """Readiness conditions not satisfied, in declared order. All four must
    hold before an activity leaves 'planned' -- they are conjunctive, not a
    score."""
    conds = activity.get("readiness", {})
    return [c for c in READINESS_CONDITIONS if not conds.get(c)]


def may_start(activity):
    """True when every readiness condition holds and no nonconformance is
    still open against the activity."""
    return not unmet_readiness(activity) and not open_nonconformances(activity)


def open_nonconformances(activity):
    """Nonconformance ids raised against this activity and not dispositioned,
    in input order. An open nonconformance is what suspends execution."""
    out = []
    for nc in activity.get("nonconformances", []):
        ncid = nc.get("nc_id")
        if not ncid:
            raise ValueError("nonconformance with no nc_id")
        if validate_disposition(nc.get("disposition", "open")) == "open":
            out.append(ncid)
    return out


def deviation_violations(activity):
    """Findings for procedure departures executed without prior approval.

    A departure approved after the fact is the defect, not the departure:
    the evidence was produced outside the approved procedure and nobody
    agreed in advance that it would still be valid.
    """
    out = []
    for dev in activity.get("deviations", []):
        did = dev.get("deviation_id")
        if not did:
            raise ValueError("deviation with no deviation_id")
        if not dev.get("approved_before_execution"):
            out.append({"deviation_id": did,
                        "issue": "deviation_not_approved_before_execution"})
    return out


def as_run_violations(activity):
    """Findings where the as-run record departs from the as-planned steps
    without a recorded deviation covering it."""
    planned = list(activity.get("planned_steps", []))
    as_run = list(activity.get("as_run_steps", []))
    covered = {d.get("covers_step") for d in activity.get("deviations", [])}
    out = []
    if not as_run and planned:
        return [{"issue": "no_as_run_record"}]
    for step in planned:
        if step not in as_run and step not in covered:
            out.append({"step": step, "issue": "planned_step_not_run"})
    for step in as_run:
        if step not in planned and step not in covered:
            out.append({"step": step, "issue": "unplanned_step_run"})
    return out


def activity_state(activity):
    """State an activity should be in, derived from its own record rather than
    read from a field: an open nonconformance suspends it, unmet readiness
    keeps it planned, a complete as-run with no gaps completes it."""
    if open_nonconformances(activity):
        return "suspended"
    if unmet_readiness(activity):
        return "planned"
    if not activity.get("as_run_steps"):
        return "ready"
    return "complete" if not as_run_violations(activity) else "executing"


def execution_review(activity):
    """Full clause 5.3.1 execution review for one verification activity.

    Returns {"activity_id", "state", "findings"}. Raises ValueError for an
    unknown disposition, or a nonconformance/deviation with no identifier.
    """
    aid = activity.get("activity_id")
    if not aid:
        raise ValueError("activity with no activity_id")
    findings = []
    for c in unmet_readiness(activity):
        findings.append({"activity_id": aid, "condition": c,
                         "issue": "readiness_condition_unmet"})
    for ncid in open_nonconformances(activity):
        findings.append({"activity_id": aid, "nc_id": ncid,
                         "issue": "open_nonconformance"})
    findings += [dict(f, activity_id=aid) for f in deviation_violations(activity)]
    findings += [dict(f, activity_id=aid) for f in as_run_violations(activity)]
    return {"activity_id": aid, "state": activity_state(activity),
            "findings": findings}


def is_execution_valid(review):
    """True when the activity completed with no findings -- its evidence may
    be carried into the verification control document."""
    return review["state"] == "complete" and not review["findings"]
