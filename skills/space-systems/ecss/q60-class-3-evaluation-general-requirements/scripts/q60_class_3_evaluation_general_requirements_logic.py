#!/usr/bin/env python3
"""When a Class 3 part evaluation becomes necessary, and how much of one.

Anchor: ECSS-Q-ST-60C clause 6.2.3.1. The procedure below is a paraphrase
into implementable steps; no standard text is reproduced.

A Class 3 part arrives with no qualification against a specification the
project accepts. The question the clause asks is therefore not "is this part
any good" but "what about this procurement is unknown enough that it has to be
found out before the part is used".

The unknowns are declared as trigger conditions. Each carries a weight, and a
few of them are hard: a hard trigger forces the full programme on its own,
whatever the arithmetic says and whatever anybody is willing to sign.

    necessity index   the weighted share of the declared unknowns, opened out
                      by how severe the application is
    hard trigger      an unknown no index and no signature can stand in for
    waiver            admissible against a soft trigger with a written
                      justification; refused against a hard one

The programme that comes out is expressed as the elements still owed, not as
a template, so an evaluation plan starts from what this procurement is
actually missing.

Standard library only, offline, deterministic.
"""

from __future__ import annotations

import math

TRIGGER_CONDITIONS = {
    "no-qualification-against-accepted-specification": {"weight": 0.45, "hard": True},
    "manufacturing-line-not-identified": {"weight": 0.35, "hard": True},
    "use-outside-the-rated-envelope": {"weight": 0.30, "hard": True},
    "technology-new-to-the-project": {"weight": 0.30, "hard": False},
    "package-or-die-change-notified": {"weight": 0.25, "hard": False},
    "single-lot-procurement-with-no-lot-history": {"weight": 0.20, "hard": False},
    "radiation-behaviour-unknown": {"weight": 0.20, "hard": False},
    "no-traceability-to-a-date-code": {"weight": 0.15, "hard": False},
}

TRIGGER_ELEMENTS = {
    "no-qualification-against-accepted-specification": ("evaluation-testing",),
    "manufacturing-line-not-identified": ("manufacturer-line-review",),
    "use-outside-the-rated-envelope": ("evaluation-testing",),
    "technology-new-to-the-project": ("constructional-analysis", "evaluation-testing"),
    "package-or-die-change-notified": ("constructional-analysis",),
    "single-lot-procurement-with-no-lot-history": ("lot-homogeneity-check",),
    "radiation-behaviour-unknown": ("radiation-behaviour-assessment",),
    "no-traceability-to-a-date-code": ("lot-homogeneity-check",),
}

ALWAYS_OWED_ELEMENTS = ("manufacturer-line-review", "constructional-analysis")

APPLICATION_SEVERITY = {
    "non-critical": 0.80,
    "standard": 1.00,
    "mission-critical": 1.30,
}

EVALUATION_NOT_REQUIRED = "class-3-evaluation-not-required"
REDUCED_EVALUATION_REQUIRED = "class-3-reduced-evaluation-required"
FULL_EVALUATION_REQUIRED = "class-3-full-evaluation-required"

FULL_EVALUATION_THRESHOLD = 0.50
REDUCED_EVALUATION_THRESHOLD = 0.20

DECISION_TOLERANCE = 1e-9

TOTAL_TRIGGER_WEIGHT = sum(
    entry["weight"] for entry in TRIGGER_CONDITIONS.values()
)


def _require_text(name, value):
    if not isinstance(value, str) or not value.strip():
        raise ValueError("%s must be a non-empty string, got %r" % (name, value))
    return value.strip()


def _at_least(value, bound):
    """value >= bound, absorbing floating-point representation error."""
    return value >= bound or math.isclose(
        value, bound, rel_tol=DECISION_TOLERANCE, abs_tol=1e-12
    )


def validate_trigger_id(trigger):
    """Reject anything that is not a declared trigger condition."""
    name = _require_text("trigger", trigger)
    if name not in TRIGGER_CONDITIONS:
        raise ValueError(
            "unknown trigger condition %r; the declared set is %s"
            % (name, ", ".join(sorted(TRIGGER_CONDITIONS)))
        )
    return name


def trigger_weight(trigger):
    """Weight this unknown carries in the necessity index."""
    return float(TRIGGER_CONDITIONS[validate_trigger_id(trigger)]["weight"])


def is_hard_trigger(trigger):
    """True when this unknown forces the full programme on its own."""
    return bool(TRIGGER_CONDITIONS[validate_trigger_id(trigger)]["hard"])


def severity_multiplier(application_severity):
    """How much the application opens the weighted unknowns out."""
    name = _require_text("application_severity", application_severity)
    if name not in APPLICATION_SEVERITY:
        raise ValueError(
            "unknown application severity %r; expected one of %s"
            % (name, ", ".join(sorted(APPLICATION_SEVERITY)))
        )
    return APPLICATION_SEVERITY[name]


def validate_declared_triggers(declared):
    """Read the declared unknowns into an ordered, duplicate-free list."""
    if not isinstance(declared, (list, tuple)):
        raise ValueError("declared triggers must be a sequence, got %r" % (declared,))
    seen = []
    for item in declared:
        name = validate_trigger_id(item)
        if name in seen:
            raise ValueError("trigger condition %s is declared twice" % name)
        seen.append(name)
    return seen


def apply_waivers(active_triggers, waivers):
    """Sort waivers into granted and refused, and refuse them on hard triggers.

    A waiver is a project statement that an unknown does not have to be
    resolved. It can be granted against a soft trigger when it carries a
    written justification. Against a hard trigger it is refused, because the
    thing being waived is the reason the clause was reached at all.
    """
    active = validate_declared_triggers(active_triggers)
    if waivers is None:
        waivers = []
    if not isinstance(waivers, (list, tuple)):
        raise ValueError("waivers must be a sequence, got %r" % (waivers,))
    granted = []
    refused = []
    findings = []
    seen = set()
    for index, waiver in enumerate(waivers):
        if not isinstance(waiver, dict):
            raise ValueError("waivers[%d] must be a mapping" % index)
        target = validate_trigger_id(waiver.get("trigger"))
        if target in seen:
            raise ValueError("trigger condition %s is waived twice" % target)
        seen.add(target)
        justification = waiver.get("justification")
        if target not in active:
            raise ValueError(
                "waiver raised against %s, which was never declared" % target
            )
        if is_hard_trigger(target):
            refused.append(
                {"trigger": target, "reason": "hard-trigger-cannot-be-waived"}
            )
            findings.append(
                "the waiver against %s is refused; that unknown forces the full "
                "programme whatever is signed against it" % target
            )
            continue
        if not isinstance(justification, str) or not justification.strip():
            refused.append({"trigger": target, "reason": "no-written-justification"})
            findings.append(
                "the waiver against %s carries no written justification, so the "
                "unknown stays open" % target
            )
            continue
        granted.append({"trigger": target, "justification": justification.strip()})
    waived = {item["trigger"] for item in granted}
    remaining = [name for name in active if name not in waived]
    return {
        "remaining": remaining,
        "granted": granted,
        "refused": refused,
        "findings": findings,
    }


def necessity_index(remaining_triggers, application_severity="standard"):
    """Weighted share of the unknowns left, opened out by the application."""
    remaining = validate_declared_triggers(remaining_triggers)
    multiplier = severity_multiplier(application_severity)
    raw = sum(trigger_weight(name) for name in remaining)
    index = (raw / TOTAL_TRIGGER_WEIGHT) * multiplier
    return min(index, 1.0)


def outstanding_elements(remaining_triggers, decision):
    """Programme elements still owed once the decision is taken."""
    remaining = validate_declared_triggers(remaining_triggers)
    if decision not in (
        EVALUATION_NOT_REQUIRED,
        REDUCED_EVALUATION_REQUIRED,
        FULL_EVALUATION_REQUIRED,
    ):
        raise ValueError("unknown decision %r" % (decision,))
    if decision == EVALUATION_NOT_REQUIRED:
        return []
    owed = set(ALWAYS_OWED_ELEMENTS)
    for name in remaining:
        owed.update(TRIGGER_ELEMENTS[name])
    if decision == FULL_EVALUATION_REQUIRED:
        owed.update(("evaluation-testing", "lot-homogeneity-check"))
    return sorted(owed)


def assess_evaluation_necessity(case):
    """Full clause 6.2.3.1 decision for one Class 3 candidate part."""
    if not isinstance(case, dict):
        raise ValueError("case must be a mapping, got %r" % (case,))
    manufacturer = _require_text("manufacturer", case.get("manufacturer"))
    part_number = _require_text("part_number", case.get("part_number"))
    severity_name = _require_text(
        "application_severity", case.get("application_severity", "standard")
    )
    multiplier = severity_multiplier(severity_name)
    declared = validate_declared_triggers(case.get("declared_triggers", []))
    waiver_result = apply_waivers(declared, case.get("waivers"))
    remaining = waiver_result["remaining"]
    index = necessity_index(remaining, severity_name)
    hard = [name for name in remaining if is_hard_trigger(name)]
    if hard:
        decision = FULL_EVALUATION_REQUIRED
        driver = "hard-trigger"
    elif _at_least(index, FULL_EVALUATION_THRESHOLD):
        decision = FULL_EVALUATION_REQUIRED
        driver = "necessity-index"
    elif _at_least(index, REDUCED_EVALUATION_THRESHOLD):
        decision = REDUCED_EVALUATION_REQUIRED
        driver = "necessity-index"
    else:
        decision = EVALUATION_NOT_REQUIRED
        driver = "no-unknown-left-open"
    findings = list(waiver_result["findings"])
    for name in hard:
        findings.append(
            "%s is a hard trigger and is still open, so the full programme "
            "stands whatever the index reads" % name
        )
    if decision == EVALUATION_NOT_REQUIRED and declared:
        findings.append(
            "every declared unknown was waived with a written justification; "
            "the justifications carry the decision, not the index"
        )
    owed = outstanding_elements(remaining, decision)
    return {
        "manufacturer": manufacturer,
        "part_number": part_number,
        "application_severity": severity_name,
        "severity_multiplier": multiplier,
        "declared_triggers": declared,
        "remaining_triggers": remaining,
        "waivers_granted": waiver_result["granted"],
        "waivers_refused": waiver_result["refused"],
        "hard_triggers_open": hard,
        "necessity_index": index,
        "decision": decision,
        "decision_driver": driver,
        "evaluation_required": decision != EVALUATION_NOT_REQUIRED,
        "outstanding_elements": owed,
        "findings": findings,
    }
