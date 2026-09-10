#!/usr/bin/env python3
"""ECSS-E-ST-10C clause 5.2.3.3 -- requirement risk analysis (paraphrase,
not copy).

Common-knowledge summary (standards-map.yaml, ecss: gated false): at each
level of the requirement flow-down (customer TS through each lower-level
TS), the technical/requirement risk of a candidate or derived requirement
is analysed and entered into the project risk register, using a
likelihood x severity index consistent with the ECSS risk-management
standard (M-ST-80). Risks above the acceptable band require a defined
mitigation before the requirement can be baselined; low risks may be
logged without one. This module scopes only requirement-level risk
analysis feeding the register -- it does not replace the broader
technical risk management process (identification, analysis, mitigation,
residual risk tracking across the whole project) which is the sibling
e10-risk-mgmt leaf (10C clause 5.6.8).
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


def mitigation_required(risk_class):
    """True when M-ST-80-consistent practice requires a defined
    mitigation before the requirement can be baselined."""
    return risk_class in MITIGATION_REQUIRED_CLASSES


def analyse_requirement_risk(requirement_id, level, likelihood, severity, description):
    """Analyse one requirement's technical/requirement risk at a given
    flow-down level and return a new risk-register entry (dict). Does
    not mutate any input. requirement_id and level and description must
    be non-empty strings. The entry starts with mitigation=None and
    status='identified'; use add_mitigation() to close it."""
    if not requirement_id:
        raise ValueError("requirement_id must be non-empty")
    if not level:
        raise ValueError("level must be non-empty")
    if not description:
        raise ValueError("description must be non-empty")
    risk_index, risk_class = classify_risk(likelihood, severity)
    return {
        "requirement_id": requirement_id,
        "level": level,
        "likelihood": likelihood,
        "severity": severity,
        "risk_index": risk_index,
        "risk_class": risk_class,
        "description": description,
        "requires_mitigation": mitigation_required(risk_class),
        "mitigation": None,
        "status": "identified",
    }


def add_mitigation(entry, mitigation_text):
    """Return a new risk-register entry with the mitigation recorded and
    status set to 'mitigated'. Does not mutate entry. Raises ValueError
    if mitigation_text is empty."""
    if not mitigation_text:
        raise ValueError("mitigation_text must be non-empty")
    updated = dict(entry)
    updated["mitigation"] = mitigation_text
    updated["status"] = "mitigated"
    return updated


def waive_mitigation(entry, rationale):
    """Return a new risk-register entry accepted without mitigation
    (status 'waived') with a recorded rationale. Only valid for entries
    that do not require mitigation; raises ValueError otherwise or if
    rationale is empty."""
    if entry["requires_mitigation"]:
        raise ValueError(
            "requirement %r risk class %r requires a mitigation, cannot waive"
            % (entry["requirement_id"], entry["risk_class"])
        )
    if not rationale:
        raise ValueError("rationale must be non-empty")
    updated = dict(entry)
    updated["mitigation"] = rationale
    updated["status"] = "waived"
    return updated


def register_status(entries):
    """(ready, open_items) across a risk register (iterable of entries).
    ready is True only when every entry that requires mitigation has one
    recorded (status 'mitigated' or 'waived' is not possible for
    required entries, only 'mitigated'). open_items lists the entries
    still 'identified' while requiring mitigation, in input order."""
    open_items = [
        entry
        for entry in entries
        if entry["requires_mitigation"] and entry["status"] == "identified"
    ]
    return (not open_items, open_items)


def level_risk_register(entries, level):
    """Entries in the register belonging to one flow-down level, in
    input order."""
    return [entry for entry in entries if entry["level"] == level]
