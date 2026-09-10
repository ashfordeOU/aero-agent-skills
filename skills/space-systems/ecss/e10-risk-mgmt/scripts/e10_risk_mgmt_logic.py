#!/usr/bin/env python3
"""ECSS-E-ST-10C clause 5.6.8 -- technical risk management (paraphrase,
not copy).

Common-knowledge summary (standards-map.yaml, ecss: gated false):
system engineering manages technical risk across the project --
identification, analysis, mitigation planning, and residual-risk
tracking -- in coordination with the ECSS risk-management standard
(M-ST-80). A risk is identified, then analysed (likelihood x severity,
each 1-5, banded into a risk class). Risk classes that require
mitigation get a recorded mitigation action; the residual risk left
after mitigation is reassessed, and any residual risk still above the
acceptable band is escalated for formal acceptance rather than closed
outright. This module scopes the project-wide risk-management process;
it does not replace the sibling e10-req-risk-analysis leaf (10C clause
5.2.3.3), which scores the technical/requirement risk of an individual
requirement at a flow-down level and feeds the same style of register
entry but does not track residual risk or escalation/acceptance.
"""

LIKELIHOOD_RANGE = range(1, 6)
SEVERITY_RANGE = range(1, 6)

RISK_CLASS_BANDS = (
    (4, "low"),
    (9, "medium"),
    (16, "high"),
    (25, "very_high"),
)

MITIGATION_REQUIRED_CLASSES = ("medium", "high", "very_high")
ACCEPTABLE_RESIDUAL_CLASSES = ("low",)

_OPEN_STATUSES = ("identified", "analysed", "mitigated", "escalated")


def classify_risk(likelihood, severity):
    """(risk_index, risk_class) for a likelihood/severity pair, each an
    int 1-5. risk_index = likelihood * severity; risk_class is the band
    the index falls in (low/medium/high/very_high). Raises ValueError if
    likelihood or severity is out of range."""
    if likelihood not in LIKELIHOOD_RANGE:
        raise ValueError("likelihood must be 1-5: %r" % (likelihood,))
    if severity not in SEVERITY_RANGE:
        raise ValueError("severity must be 1-5: %r" % (severity,))
    risk_index = likelihood * severity
    for ceiling, risk_class in RISK_CLASS_BANDS:
        if risk_index <= ceiling:
            return (risk_index, risk_class)
    raise AssertionError("unreachable: risk_index out of banded range")


def identify_risk(risk_id, title, description, category):
    """Open a new project risk-register entry (dict) at status
    'identified'. risk_id, title, description, category must all be
    non-empty strings. Does not mutate any input."""
    if not risk_id:
        raise ValueError("risk_id must be non-empty")
    if not title:
        raise ValueError("title must be non-empty")
    if not description:
        raise ValueError("description must be non-empty")
    if not category:
        raise ValueError("category must be non-empty")
    return {
        "risk_id": risk_id,
        "title": title,
        "description": description,
        "category": category,
        "status": "identified",
        "likelihood": None,
        "severity": None,
        "risk_index": None,
        "risk_class": None,
        "requires_mitigation": None,
        "mitigation_actions": [],
        "residual_likelihood": None,
        "residual_severity": None,
        "residual_risk_index": None,
        "residual_risk_class": None,
        "acceptance_rationale": None,
        "accepted_by": None,
    }


def analyse_risk(risk, likelihood, severity):
    """Return a new entry with likelihood/severity scored into a risk
    index and class, status advanced to 'analysed'. Raises ValueError if
    risk is not at status 'identified' (analysis runs once, before any
    mitigation work)."""
    if risk["status"] != "identified":
        raise ValueError(
            "risk %r must be 'identified' to analyse, is %r"
            % (risk["risk_id"], risk["status"])
        )
    risk_index, risk_class = classify_risk(likelihood, severity)
    updated = dict(risk)
    updated["status"] = "analysed"
    updated["likelihood"] = likelihood
    updated["severity"] = severity
    updated["risk_index"] = risk_index
    updated["risk_class"] = risk_class
    updated["requires_mitigation"] = risk_class in MITIGATION_REQUIRED_CLASSES
    return updated


def add_mitigation(risk, action_text, owner):
    """Return a new entry with a mitigation action appended and status
    advanced to 'mitigated'. Only valid from status 'analysed' on a risk
    that requires mitigation; raises ValueError otherwise or if
    action_text/owner is empty. Does not mutate risk or its action
    list."""
    if risk["status"] != "analysed":
        raise ValueError(
            "risk %r must be 'analysed' to add a mitigation, is %r"
            % (risk["risk_id"], risk["status"])
        )
    if not risk["requires_mitigation"]:
        raise ValueError(
            "risk %r risk class %r does not require mitigation, close it instead"
            % (risk["risk_id"], risk["risk_class"])
        )
    if not action_text:
        raise ValueError("action_text must be non-empty")
    if not owner:
        raise ValueError("owner must be non-empty")
    updated = dict(risk)
    updated["mitigation_actions"] = risk["mitigation_actions"] + [
        {"action": action_text, "owner": owner}
    ]
    updated["status"] = "mitigated"
    return updated


def close_risk(risk):
    """Return a new entry closed with no mitigation applied. Only valid
    from status 'analysed' on a risk that does not require mitigation
    (low risk class); raises ValueError otherwise. The residual risk is
    recorded as a passthrough of the analysed risk (no mitigation
    changed it)."""
    if risk["status"] != "analysed":
        raise ValueError(
            "risk %r must be 'analysed' to close, is %r"
            % (risk["risk_id"], risk["status"])
        )
    if risk["requires_mitigation"]:
        raise ValueError(
            "risk %r risk class %r requires mitigation, cannot close directly"
            % (risk["risk_id"], risk["risk_class"])
        )
    updated = dict(risk)
    updated["status"] = "closed"
    updated["residual_likelihood"] = risk["likelihood"]
    updated["residual_severity"] = risk["severity"]
    updated["residual_risk_index"] = risk["risk_index"]
    updated["residual_risk_class"] = risk["risk_class"]
    return updated


def assess_residual_risk(risk, residual_likelihood, residual_severity):
    """Return a new entry with the residual risk (after mitigation)
    scored. Status becomes 'closed' when the residual risk class is
    acceptable (low), otherwise 'escalated' for formal acceptance. Only
    valid from status 'mitigated'; raises ValueError otherwise."""
    if risk["status"] != "mitigated":
        raise ValueError(
            "risk %r must be 'mitigated' to assess residual risk, is %r"
            % (risk["risk_id"], risk["status"])
        )
    residual_index, residual_class = classify_risk(residual_likelihood, residual_severity)
    updated = dict(risk)
    updated["residual_likelihood"] = residual_likelihood
    updated["residual_severity"] = residual_severity
    updated["residual_risk_index"] = residual_index
    updated["residual_risk_class"] = residual_class
    updated["status"] = (
        "closed" if residual_class in ACCEPTABLE_RESIDUAL_CLASSES else "escalated"
    )
    return updated


def accept_risk(risk, rationale, authority):
    """Return a new entry formally accepted (terminal status
    'accepted'), recording who accepted the residual risk and why. Only
    valid from status 'escalated'; raises ValueError otherwise or if
    rationale/authority is empty."""
    if risk["status"] != "escalated":
        raise ValueError(
            "risk %r must be 'escalated' to accept, is %r"
            % (risk["risk_id"], risk["status"])
        )
    if not rationale:
        raise ValueError("rationale must be non-empty")
    if not authority:
        raise ValueError("authority must be non-empty")
    updated = dict(risk)
    updated["status"] = "accepted"
    updated["acceptance_rationale"] = rationale
    updated["accepted_by"] = authority
    return updated


def register_status(risks):
    """(ready, open_items) across a project risk register (iterable of
    entries). ready is True only when every risk has reached a terminal
    status ('closed' or 'accepted'). open_items lists the risks still in
    an open status (identified/analysed/mitigated/escalated), in input
    order."""
    open_items = [risk for risk in risks if risk["status"] in _OPEN_STATUSES]
    return (not open_items, open_items)
