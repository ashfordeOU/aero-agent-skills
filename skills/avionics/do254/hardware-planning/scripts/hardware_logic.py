#!/usr/bin/env python3
"""DO-254 hardware design assurance planning logic (paraphrase, not copy).

Common-knowledge summary (standards-map.yaml, do-254: gated): DO-254
distinguishes simple from complex airborne electronic hardware (AEH).
Complex AEH - programmable logic, processors, significant internal state,
or hardware whose correct behavior cannot be fully established from
top-level data alone, plus safety-significant items treated conservatively -
follows the full design assurance process (PHAC through verification);
simple AEH uses a reduced but still planned process.
"""

_COMPLEX_ARTIFACTS = (
    "phac",
    "requirements-capture",
    "conceptual-design",
    "detailed-design",
    "verification",
    "configuration-management",
    "process-assurance",
)
_SIMPLE_ARTIFACTS = ("hardware-plan", "verification", "configuration-management")


def classify_aeh(has_programmable_logic, has_internal_state,
                 fully_verifiable_from_top_data, safety_significant):
    """Return 'complex' or 'simple' for a DO-254 AEH item.

    Conservative planning default: when in doubt, treat the item as complex
    so the full design assurance process applies.
    """
    if has_programmable_logic or has_internal_state:
        return "complex"
    if not fully_verifiable_from_top_data:
        return "complex"
    if safety_significant:
        return "complex"
    return "simple"


def planning_artifacts(classification):
    """Planning artifact set per AEH class; unknown class -> ValueError."""
    if classification == "complex":
        return list(_COMPLEX_ARTIFACTS)
    if classification == "simple":
        return list(_SIMPLE_ARTIFACTS)
    raise ValueError("unknown AEH classification: %r" % (classification,))
