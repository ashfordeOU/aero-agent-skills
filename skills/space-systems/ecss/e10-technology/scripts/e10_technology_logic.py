#!/usr/bin/env python3
"""ECSS-E-ST-10C clause 5.6.7 -- technology plan and technology matrix
(paraphrase, not copy).

Common-knowledge summary (standards-map.yaml, ecss: gated false): the
project identifies technologies that are critical to it (not yet mature
enough for the intended use), assesses their current maturity on the
nine-level Technology Readiness Level (TRL) scale defined by E-AS-11
(ISO 16290), defines the TRL required for the project's intended use,
and plans the development activities that close any gap, tracking the
associated technology risk. This module scopes the assessment process
feeding the technology matrix and plan -- it does not format that
content into the Annex E/F DRD document structures, which are the
sibling e10-tp-drd and e10-tech-matrix-drd leaves.
"""

TRL_LEVELS = range(1, 10)

TRL_DEFINITIONS = {
    1: "basic principles observed and reported",
    2: "technology concept and/or application formulated",
    3: "analytical and experimental critical function and/or "
       "characteristic proof-of-concept",
    4: "component and/or breadboard validation in laboratory environment",
    5: "component and/or breadboard validation in relevant environment",
    6: "system/subsystem model or prototype demonstration in a "
       "relevant environment (ground or space)",
    7: "system prototype demonstration in an operational environment "
       "(ground or space)",
    8: "actual system completed and qualified through test and "
       "demonstration (ground or space)",
    9: "actual system flight proven through successful mission operations",
}

RISK_CLASS_BANDS = (
    (0, "none"),
    (1, "low"),
    (2, "medium"),
)

DEVELOPMENT_PENDING_STATUSES = ("identified",)


def validate_trl(trl):
    """Raise ValueError unless trl is an int in 1-9 (E-AS-11/ISO 16290
    scale)."""
    if trl not in TRL_LEVELS:
        raise ValueError("trl must be 1-9: %r" % (trl,))


def technology_gap(current_trl, target_trl):
    """TRL gap (target minus current, floored at zero) between an
    assessed current TRL and the TRL required for the project's
    intended use. Raises ValueError if either TRL is out of 1-9."""
    validate_trl(current_trl)
    validate_trl(target_trl)
    return max(0, target_trl - current_trl)


def classify_technology_risk(gap):
    """Technology risk class for a non-negative TRL gap: 0 is 'none',
    1 is 'low', 2 is 'medium', 3 or more is 'high'. Raises ValueError
    if gap is negative."""
    if gap < 0:
        raise ValueError("gap must be non-negative: %r" % (gap,))
    for ceiling, risk_class in RISK_CLASS_BANDS:
        if gap <= ceiling:
            return risk_class
    return "high"


def assess_technology(technology_id, description, current_trl, target_trl,
                       mission_applicability):
    """Assess one technology's maturity against the TRL required for
    the project and return a new technology-matrix entry (dict). Does
    not mutate any input. technology_id, description, and
    mission_applicability must be non-empty strings. The entry starts
    with development_activity=None, schedule=None, and status
    'identified' if critical (gap > 0) else 'mature'."""
    if not technology_id:
        raise ValueError("technology_id must be non-empty")
    if not description:
        raise ValueError("description must be non-empty")
    if not mission_applicability:
        raise ValueError("mission_applicability must be non-empty")
    gap = technology_gap(current_trl, target_trl)
    critical = gap > 0
    return {
        "technology_id": technology_id,
        "description": description,
        "current_trl": current_trl,
        "target_trl": target_trl,
        "mission_applicability": mission_applicability,
        "gap": gap,
        "risk_class": classify_technology_risk(gap),
        "critical": critical,
        "development_activity": None,
        "schedule": None,
        "status": "identified" if critical else "mature",
    }


def add_development_plan(entry, activity, schedule):
    """Return a new technology-matrix entry with a development activity
    and schedule recorded and status set to 'planned'. Does not mutate
    entry. Only valid for critical entries (gap > 0); raises ValueError
    otherwise, or if activity or schedule is empty."""
    if not entry["critical"]:
        raise ValueError(
            "technology %r is not critical (gap 0), no development "
            "plan needed" % (entry["technology_id"],)
        )
    if not activity:
        raise ValueError("activity must be non-empty")
    if not schedule:
        raise ValueError("schedule must be non-empty")
    updated = dict(entry)
    updated["development_activity"] = activity
    updated["schedule"] = schedule
    updated["status"] = "planned"
    return updated


def close_technology_gap(entry, achieved_trl):
    """Return a new technology-matrix entry after re-assessing a
    planned technology at a newly achieved TRL. Does not mutate entry.
    Only valid for entries with a recorded development plan (status
    'planned'); raises ValueError otherwise, or if achieved_trl is out
    of 1-9 or lower than the entry's current_trl. Recomputes gap and
    risk_class against the entry's target_trl; status becomes 'mature'
    once the gap closes, otherwise stays 'planned'."""
    if entry["status"] != "planned":
        raise ValueError(
            "technology %r has no development plan to close (status %r)"
            % (entry["technology_id"], entry["status"])
        )
    validate_trl(achieved_trl)
    if achieved_trl < entry["current_trl"]:
        raise ValueError(
            "achieved_trl %r must not be lower than current_trl %r"
            % (achieved_trl, entry["current_trl"])
        )
    gap = technology_gap(achieved_trl, entry["target_trl"])
    updated = dict(entry)
    updated["current_trl"] = achieved_trl
    updated["gap"] = gap
    updated["risk_class"] = classify_technology_risk(gap)
    updated["critical"] = gap > 0
    updated["status"] = "mature" if gap == 0 else "planned"
    return updated


def technology_plan_status(entries):
    """(ready, open_items) across a technology matrix (iterable of
    entries). ready is True only when every critical entry has a
    recorded development plan (status 'planned' or 'mature'; not
    'identified'). open_items lists the critical entries still
    'identified', in input order."""
    open_items = [
        entry
        for entry in entries
        if entry["critical"] and entry["status"] in DEVELOPMENT_PENDING_STATUSES
    ]
    return (not open_items, open_items)


def matrix_for_mission(entries, mission_applicability):
    """Entries in the technology matrix applicable to one mission or
    sub-system, in input order."""
    return [
        entry for entry in entries
        if entry["mission_applicability"] == mission_applicability
    ]
