#!/usr/bin/env python3
"""DO-254 hardware configuration management logic (paraphrase, not copy).

Common-knowledge summary (standards-map.yaml, do-254: gated, listed
reference-only): configuration management for airborne electronic
hardware keeps a hardware configuration index (HCI), freezes baselines
of hardware lifecycle data, and controls changes through engineering
change requests and orders (ECR/ECO). A change class (1 or 2) drives
how much review and reverification apply; complex hardware changes
need independent review.

Units: none. This module operates on nominal categories and
identifiers only (change class, safety effect, HCI strings); no
physical quantities are computed, so no unit conversions apply.
"""

VALID_HARDWARE_CLASSES = ("simple", "complex")
VALID_SAFETY_EFFECTS = ("none", "minor", "major", "hazardous", "catastrophic")


def change_class(change):
    """Classify a DO-254 hardware change as class 1 or class 2.

    change: dict with keys hardware_class ("simple" or "complex"),
    safety_effect ("none", "minor", "major", "hazardous",
    "catastrophic"), and functional_change (bool, True when form,
    fit, or function changes).

    Rule table (paraphrase of DO-254 CM practice): a change is class 1
    (formal ECR/ECO, baseline update, reverification) when it alters
    form/fit/function OR safety_effect != "none" OR the hardware is
    complex; otherwise it is class 2 (documented but lighter review).
    """
    if not isinstance(change, dict):
        raise ValueError("change must be a dict with hardware_class, safety_effect, functional_change")
    hw = change.get("hardware_class")
    se = change.get("safety_effect")
    fc = change.get("functional_change")
    if hw not in VALID_HARDWARE_CLASSES:
        raise ValueError(
            "hardware_class must be one of %s, got %r" % (", ".join(VALID_HARDWARE_CLASSES), hw)
        )
    if se not in VALID_SAFETY_EFFECTS:
        raise ValueError(
            "safety_effect must be one of %s, got %r" % (", ".join(VALID_SAFETY_EFFECTS), se)
        )
    if not isinstance(fc, bool):
        raise ValueError("functional_change must be a bool, got %r" % (fc,))
    if fc or se != "none" or hw == "complex":
        return {
            "class": 1,
            "rationale": "form/fit/function change or safety effect present or complex hardware",
        }
    return {
        "class": 2,
        "rationale": "no form/fit/function change, no safety effect, simple hardware",
    }


def cm_actions(change_class_num):
    """Map a change class to the required configuration management actions.

    Class 1: baseline update, formal ECR/ECO, reverification, and
    independent review all required. Class 2: baseline update and
    ECR/ECO still required (documented), but no reverification and no
    independent review.
    """
    if change_class_num == 1:
        return {
            "baseline_update": True,
            "ecr_required": True,
            "reverification_required": True,
            "independent_review": True,
        }
    if change_class_num == 2:
        return {
            "baseline_update": True,
            "ecr_required": True,
            "reverification_required": False,
            "independent_review": False,
        }
    raise ValueError("change class must be 1 or 2, got %r" % (change_class_num,))


def hci_entry(item, revision, baseline):
    """Format one hardware configuration index line: 'item rev baseline'."""
    if not isinstance(item, str) or not item.strip():
        raise ValueError("item must be a non-empty string, got %r" % (item,))
    if not isinstance(revision, str) or not revision.strip():
        raise ValueError("revision must be a non-empty string, got %r" % (revision,))
    if not isinstance(baseline, str) or not baseline.strip():
        raise ValueError("baseline must be a non-empty string, got %r" % (baseline,))
    return "%s %s %s" % (item.strip(), revision.strip(), baseline.strip())
