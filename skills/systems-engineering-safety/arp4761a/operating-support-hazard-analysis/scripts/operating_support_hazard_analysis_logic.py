#!/usr/bin/env python3
"""Operating and support hazard analysis logic (paraphrase, not copy).

Common-knowledge summary (standards-map.yaml, arp4761a): O&SHA finds
hazards tied to operational use and maintenance of the aircraft or
system. Each hazard is scored by combining a severity category with a
likelihood category on the risk matrix; the resulting risk index maps
to an acceptability band. Safety significant maintenance tasks that
touch hazards outside the fully acceptable band are flagged as
critical tasks and tracked in the hazard log.
"""

SEVERITY_VALUES = {
    "Catastrophic": 5,
    "Hazardous": 4,
    "Major": 3,
    "Minor": 2,
    "Negligible": 1,
}

LIKELIHOOD_VALUES = {
    "Frequent": 5,
    "Probable": 4,
    "Occasional": 3,
    "Remote": 2,
    "Improbable": 1,
}

# (minimum_risk_index, band) in descending threshold order.
ACCEPTABILITY_BANDS = [
    (15, "Unacceptable"),
    (8, "Acceptable with mitigation"),
    (1, "Acceptable"),
]


def risk_index(severity, likelihood):
    """Risk matrix index from the severity and likelihood categories."""
    if severity not in SEVERITY_VALUES:
        raise ValueError("unknown severity: %r" % (severity,))
    if likelihood not in LIKELIHOOD_VALUES:
        raise ValueError("unknown likelihood: %r" % (likelihood,))
    return SEVERITY_VALUES[severity] * LIKELIHOOD_VALUES[likelihood]


def acceptability(index):
    """Acceptability band for a risk index (higher is worse)."""
    for threshold, band in ACCEPTABILITY_BANDS:
        if index >= threshold:
            return band
    raise ValueError("risk index out of range: %r" % (index,))


def add_hazard(hazards, hazard_id, description, severity, likelihood):
    """Append a scored hazard record; duplicate ids raise ValueError."""
    if any(h["id"] == hazard_id for h in hazards):
        raise ValueError("duplicate hazard id: %r" % (hazard_id,))
    index = risk_index(severity, likelihood)
    record = {
        "id": hazard_id,
        "description": description,
        "severity": severity,
        "likelihood": likelihood,
        "risk_index": index,
        "band": acceptability(index),
    }
    hazards.append(record)
    return record


def register(hazards):
    """The hazard log sorted by decreasing risk index."""
    return sorted(hazards, key=lambda h: -h["risk_index"])


def unacceptable_hazards(hazards):
    """Hazard ids that are unacceptable and force design change."""
    return sorted(h["id"] for h in hazards if h["band"] == "Unacceptable")


def critical_tasks(tasks, hazards):
    """Flag tasks that force a critical maintenance action.

    A task is critical when it involves an unacceptable hazard, or when
    it is safety significant and involves a hazard outside the fully
    acceptable band.
    """
    by_id = {h["id"]: h for h in hazards}
    critical = []
    for task in tasks:
        involved = [by_id[h] for h in task.get("hazard_ids", []) if h in by_id]
        has_unacceptable = any(h["band"] == "Unacceptable" for h in involved)
        has_mitigated = any(
            h["band"] == "Acceptable with mitigation" for h in involved
        )
        if has_unacceptable or (task.get("safety_significant") and has_mitigated):
            critical.append(task["id"])
    return sorted(critical)
