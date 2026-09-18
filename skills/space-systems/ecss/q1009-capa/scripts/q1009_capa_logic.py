#!/usr/bin/env python3
"""Corrective and preventive action selection for a nonconformance.

Anchor: ECSS-Q-ST-10-09C clause 5.3. The procedure below is a
paraphrase into implementable steps; no standard text is reproduced.

Three kinds of action follow a nonconformance, and only two of them are
what the clause asks for:

    containment  stops the escape now — segregate, impound, screen the
                 built stock. It buys time and fixes nothing.
    corrective   removes a cause that has already produced a
                 nonconformance, so the same cause stops producing it.
    preventive   removes a cause before it produces one, wherever the
                 same mechanism can reach.

An action is only as strong as the control it installs. Eliminating the
possibility outranks an engineering control, which outranks a written
procedure or a training session, which outranks an added inspection —
an inspection detects the defect again rather than stopping it, so it
never closes a cause on its own.

Standard library only, offline, deterministic.
"""

from __future__ import annotations

ACTION_TYPES = ("containment", "corrective", "preventive")

CAUSE_CATEGORIES = (
    "design",
    "process",
    "procedure",
    "training",
    "material",
    "workmanship",
    "supplier",
    "equipment",
)

SYSTEMIC_CATEGORIES = ("design", "process", "procedure", "training", "supplier")

CONTROL_STRENGTH = {
    "elimination": 5,
    "substitution": 4,
    "engineering-control": 3,
    "procedure-change": 2,
    "training": 2,
    "detection-only": 1,
}

DETECTION_ONLY = "detection-only"

DEFAULT_RECURRENCE_THRESHOLD = 2

VERDICT_ADEQUATE = "capa-adequate"
VERDICT_INSUFFICIENT = "capa-insufficient"
VERDICT_CONTAINMENT_ONLY = "capa-containment-only"


def _require_text(name, value):
    if not isinstance(value, str) or not value.strip():
        raise ValueError("%s must be a non-empty string, got %r" % (name, value))
    return value.strip()


def _require_count(name, value, minimum=0):
    if isinstance(value, bool) or not isinstance(value, int):
        raise ValueError("%s must be an integer, got %r" % (name, value))
    if value < minimum:
        raise ValueError("%s must be at least %d, got %r" % (name, minimum, value))
    return value


def _require_choice(name, value, allowed):
    if value not in allowed:
        raise ValueError(
            "%s must be one of %s, got %r" % (name, ", ".join(allowed), value)
        )
    return value


def control_strength(control):
    """Rank of the control an action installs; higher removes more."""
    _require_choice("control", control, tuple(CONTROL_STRENGTH))
    return CONTROL_STRENGTH[control]


def prevents_recurrence(control):
    """A control that detects the defect again has not removed the cause."""
    return control_strength(control) > CONTROL_STRENGTH[DETECTION_ONLY]


def validate_root_causes(causes, recurrence_threshold=DEFAULT_RECURRENCE_THRESHOLD):
    """Check the cause set and mark which causes owe a preventive action."""
    _require_count("recurrence_threshold", recurrence_threshold, minimum=1)
    if not isinstance(causes, (list, tuple)):
        raise ValueError("causes must be a list, got %r" % (causes,))
    if not causes:
        raise ValueError("causes must not be empty; actions need a cause to remove")
    seen = set()
    findings = []
    preventive_due = []
    grouped = {}
    for i, cause in enumerate(causes):
        if not isinstance(cause, dict):
            raise ValueError("causes[%d] must be a mapping, got %r" % (i, cause))
        cid = _require_text("causes[%d].id" % i, cause.get("id"))
        if cid in seen:
            raise ValueError("duplicate cause id %r" % cid)
        seen.add(cid)
        category = _require_choice(
            "causes[%d].category" % i, cause.get("category"), CAUSE_CATEGORIES
        )
        grouped.setdefault(category, []).append(cid)
        occurrences = _require_count(
            "causes[%d].occurrences" % i, cause.get("occurrences", 1), minimum=1
        )
        evidence = cause.get("evidence")
        if not isinstance(evidence, str) or not evidence.strip():
            findings.append(
                "cause %s is asserted with no evidence behind it" % cid
            )
        if category in SYSTEMIC_CATEGORIES or occurrences >= recurrence_threshold:
            preventive_due.append(cid)
    return {
        "ids": tuple(sorted(seen)),
        "grouped_by_category": {k: tuple(v) for k, v in grouped.items()},
        "preventive_due": tuple(preventive_due),
        "findings": tuple(findings),
    }


def validate_actions(actions, cause_ids):
    """Check every proposed action names a type, a cause and a rationale."""
    if not isinstance(actions, (list, tuple)):
        raise ValueError("actions must be a list, got %r" % (actions,))
    if not actions:
        raise ValueError("actions must not be empty")
    seen = set()
    findings = []
    checked = []
    for i, action in enumerate(actions):
        if not isinstance(action, dict):
            raise ValueError("actions[%d] must be a mapping, got %r" % (i, action))
        aid = _require_text("actions[%d].id" % i, action.get("id"))
        if aid in seen:
            raise ValueError("duplicate action id %r" % aid)
        seen.add(aid)
        atype = _require_choice(
            "actions[%d].type" % i, action.get("type"), ACTION_TYPES
        )
        control = _require_choice(
            "actions[%d].control" % i, action.get("control"), tuple(CONTROL_STRENGTH)
        )
        addresses = action.get("addresses")
        if atype == "containment":
            addresses = None
        else:
            addresses = _require_text("actions[%d].addresses" % i, addresses)
            if addresses not in cause_ids:
                raise ValueError(
                    "actions[%s].addresses names cause %r which is not in the cause set"
                    % (aid, addresses)
                )
        rationale = action.get("rationale")
        if not isinstance(rationale, str) or not rationale.strip():
            findings.append("action %s records no rationale for the choice" % aid)
        checked.append(
            {
                "id": aid,
                "type": atype,
                "control": control,
                "addresses": addresses,
                "strength": control_strength(control),
            }
        )
    return {"actions": tuple(checked), "findings": tuple(findings)}


def coverage_by_cause(checked_actions, cause_ids):
    """Which causes carry a corrective action, and how strong it is."""
    covered = {}
    for action in checked_actions:
        if action["type"] != "corrective":
            continue
        entry = covered.setdefault(
            action["addresses"], {"action_ids": [], "best_strength": 0}
        )
        entry["action_ids"].append(action["id"])
        entry["best_strength"] = max(entry["best_strength"], action["strength"])
    uncovered = tuple(cid for cid in cause_ids if cid not in covered)
    detection_only = tuple(
        cid
        for cid, entry in covered.items()
        if entry["best_strength"] <= CONTROL_STRENGTH[DETECTION_ONLY]
    )
    return {
        "covered": {k: dict(v, action_ids=tuple(v["action_ids"])) for k, v in covered.items()},
        "uncovered": uncovered,
        "detection_only_causes": tuple(sorted(detection_only)),
    }


def preventive_gaps(checked_actions, preventive_due):
    """Causes that owe a preventive action and have not been given one."""
    given = {a["addresses"] for a in checked_actions if a["type"] == "preventive"}
    return tuple(cid for cid in preventive_due if cid not in given)


def select_capa(case, recurrence_threshold=DEFAULT_RECURRENCE_THRESHOLD):
    """Full clause 5.3 adequacy decision over a proposed action set."""
    if not isinstance(case, dict):
        raise ValueError("case must be a mapping, got %r" % (case,))
    causes = validate_root_causes(case.get("root_causes"), recurrence_threshold)
    actions = validate_actions(case.get("actions"), set(causes["ids"]))
    checked = actions["actions"]
    coverage = coverage_by_cause(checked, causes["ids"])
    gaps = preventive_gaps(checked, causes["preventive_due"])
    findings = list(causes["findings"]) + list(actions["findings"])
    corrective = [a for a in checked if a["type"] == "corrective"]
    weakest = min((a["strength"] for a in corrective), default=0)
    result = {
        "cause_ids": causes["ids"],
        "preventive_due": causes["preventive_due"],
        "uncovered_causes": coverage["uncovered"],
        "detection_only_causes": coverage["detection_only_causes"],
        "preventive_gaps": gaps,
        "weakest_corrective_strength": weakest,
        "action_count": len(checked),
        "findings": findings,
    }
    if not corrective:
        findings.append(
            "no corrective action proposed; containment holds the escape but "
            "leaves every cause in place"
        )
        result["verdict"] = VERDICT_CONTAINMENT_ONLY
        result["adequate"] = False
        return result
    if coverage["uncovered"]:
        findings.append(
            "no corrective action removes cause %s" % ", ".join(coverage["uncovered"])
        )
    for cid in coverage["detection_only_causes"]:
        findings.append(
            "cause %s is covered only by added detection, which finds the defect "
            "again rather than removing the cause" % cid
        )
    if gaps:
        findings.append(
            "cause %s can recur beyond this item and owes a preventive action"
            % ", ".join(gaps)
        )
    adequate = not (
        coverage["uncovered"]
        or coverage["detection_only_causes"]
        or gaps
        or actions["findings"]
        or causes["findings"]
    )
    result["adequate"] = adequate
    result["verdict"] = VERDICT_ADEQUATE if adequate else VERDICT_INSUFFICIENT
    return result
