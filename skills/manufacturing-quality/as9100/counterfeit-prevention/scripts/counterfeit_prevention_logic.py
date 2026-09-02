#!/usr/bin/env python3
"""AS9100 counterfeit prevention planning logic (paraphrase).

Common-knowledge summary (standards-map.yaml, as9100: proprietary
IAQG/SAE, summary only): AS9100 clause 8.1.4 requires counterfeit
parts prevention: procurement from approved sources, verification
plans for suspect items, and reporting of confirmed counterfeit
parts. The risk model here is a project-defined control checklist:
authentic source, verification plan, approved distributor, and
incoming inspection. Missing controls count as absent.
"""

CONTROL_KEYS = ("authentic_source", "verification_plan",
                "distributor_approved", "incoming_inspection")


def counterfeit_risk(controls):
    """'low' (all controls), 'medium' (three), else 'high'."""
    present = sum(1 for key in CONTROL_KEYS if controls.get(key))
    if present == len(CONTROL_KEYS):
        return "low"
    if present == len(CONTROL_KEYS) - 1:
        return "medium"
    return "high"


def reporting_required(level):
    """True when a confirmed or suspected counterfeit must be reported."""
    if level not in ("low", "medium", "high"):
        raise ValueError("unknown risk level %r" % (level,))
    return level != "low"


def procurement_control_ok(controls):
    """True when every counterfeit prevention control is present."""
    return all(controls.get(key) for key in CONTROL_KEYS)
