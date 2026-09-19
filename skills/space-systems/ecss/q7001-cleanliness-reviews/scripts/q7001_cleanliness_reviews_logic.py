#!/usr/bin/env python3
"""Cleanliness status inputs to design and production readiness reviews.

Anchor: ECSS-Q-ST-70-01C, programme reviews. The procedure below is a
paraphrase into implementable steps; no standard text is reproduced.

A readiness review is a gate on evidence. Contamination control owes
each gate a specific set of items -- a preliminary design review wants
requirements, a budget and a plan; a test readiness review wants the
facility, the monitoring set-up and the level the article entered
with. Contamination-sensitive hardware (optics, cryogenic surfaces,
detectors, propulsion feed systems) widens that set, because a general
areal budget does not say what the deposit costs in performance.

Items are mandatory or supporting and the two never trade: a missing
mandatory item stops the gate, a missing supporting item raises an
action. Open contamination actions are weighted by severity, and a
major carries a veto.

Standard library only, offline, deterministic.
"""

from __future__ import annotations

PDR = "preliminary-design-review"
CDR = "critical-design-review"
MRR = "manufacturing-readiness-review"
TRR = "test-readiness-review"
FAR = "flight-acceptance-review"

REVIEW_TYPES = (PDR, CDR, MRR, TRR, FAR)

# item name -> mandatory at this review
REVIEW_ITEMS = {
    PDR: {
        "contamination-requirements": True,
        "contamination-budget-apportionment": True,
        "contamination-control-plan-draft": True,
        "cleanliness-critical-item-list": False,
    },
    CDR: {
        "contamination-requirements": True,
        "contamination-budget-apportionment": True,
        "contamination-control-plan-issued": True,
        "contamination-transport-model": True,
        "cleaning-and-verification-procedures": True,
        "materials-outgassing-screening-record": False,
    },
    MRR: {
        "contamination-control-plan-issued": True,
        "cleanroom-facility-qualification-record": True,
        "cleaning-and-verification-procedures": True,
        "personnel-training-record": True,
        "handling-and-packaging-procedures": False,
    },
    TRR: {
        "test-facility-cleanliness-qualification": True,
        "contamination-monitoring-setup": True,
        "incoming-cleanliness-measurement": True,
        "contamination-control-plan-issued": False,
        "witness-sample-plan": False,
    },
    FAR: {
        "as-delivered-cleanliness-measurement": True,
        "contamination-history-record": True,
        "contamination-budget-status": True,
        "open-contamination-nonconformance-list": True,
        "packaging-and-purge-record": False,
    },
}

SENSITIVITY_CRITICAL = "contamination-critical"
SENSITIVITY_SENSITIVE = "contamination-sensitive"
SENSITIVITY_STANDARD = "standard"

SENSITIVITY_LEVELS = (
    SENSITIVITY_CRITICAL,
    SENSITIVITY_SENSITIVE,
    SENSITIVITY_STANDARD,
)

# Items that contamination-sensitive hardware additionally owes.
SENSITIVITY_ITEMS = {
    SENSITIVITY_SENSITIVE: {"contamination-sensitivity-analysis": True},
    SENSITIVITY_CRITICAL: {
        "contamination-sensitivity-analysis": True,
        "end-of-life-performance-prediction": True,
        "surface-cleanliness-witness-history": False,
    },
}

SEVERITY_MAJOR = "major"
SEVERITY_MINOR = "minor"
SEVERITY_OBSERVATION = "observation"

ACTION_SEVERITIES = (SEVERITY_MAJOR, SEVERITY_MINOR, SEVERITY_OBSERVATION)

ACTION_WEIGHTS = {
    SEVERITY_MAJOR: 5,
    SEVERITY_MINOR: 2,
    SEVERITY_OBSERVATION: 0,
}

VERDICT_READY = "review-ready"
VERDICT_CONDITIONAL = "review-ready-with-actions"
VERDICT_NOT_READY = "review-not-ready"

TOL = 1e-9


def _require_text(name, value):
    if not isinstance(value, str) or not value.strip():
        raise ValueError("%s must be a non-empty string, got %r" % (name, value))
    return value.strip()


def _require_choice(name, value, allowed):
    if value not in allowed:
        raise ValueError(
            "%s must be one of %s, got %r" % (name, ", ".join(allowed), value)
        )
    return value


def _require_flag(name, value):
    if not isinstance(value, bool):
        raise ValueError("%s must be a boolean, got %r" % (name, value))
    return value


def required_items(review, sensitivity):
    """Data-pack items this gate owes, each flagged mandatory or supporting."""
    _require_choice("review", review, REVIEW_TYPES)
    _require_choice("sensitivity", sensitivity, SENSITIVITY_LEVELS)
    items = dict(REVIEW_ITEMS[review])
    for name, mandatory in SENSITIVITY_ITEMS.get(sensitivity, {}).items():
        items[name] = mandatory
    return dict(items)


def submitted_set(submitted):
    """The pack actually handed to the board, with blank entries refused."""
    if not isinstance(submitted, (list, tuple)):
        raise ValueError("submitted must be a list, got %r" % (submitted,))
    out = set()
    for i, name in enumerate(submitted):
        out.add(_require_text("submitted[%d]" % i, name))
    return out


def pack_shortfall(review, sensitivity, submitted):
    """What is absent, split so a mandatory gap cannot hide behind a full pack."""
    needed = required_items(review, sensitivity)
    held = submitted_set(submitted)
    missing_mandatory = tuple(
        sorted(n for n, m in needed.items() if m and n not in held)
    )
    missing_supporting = tuple(
        sorted(n for n, m in needed.items() if not m and n not in held)
    )
    mandatory_total = sum(1 for m in needed.values() if m)
    mandatory_held = mandatory_total - len(missing_mandatory)
    completeness = (
        mandatory_held / mandatory_total if mandatory_total else 1.0
    )
    return {
        "required": tuple(sorted(needed)),
        "mandatory_total": mandatory_total,
        "mandatory_held": mandatory_held,
        "missing_mandatory": missing_mandatory,
        "missing_supporting": missing_supporting,
        "mandatory_completeness": completeness,
        "extra_submitted": tuple(sorted(held - set(needed))),
    }


def normalise_action(action, index=0):
    """One open contamination action, validated rather than defaulted."""
    if not isinstance(action, dict):
        raise ValueError("action[%d] must be a mapping, got %r" % (index, action))
    return {
        "id": _require_text("action[%d].id" % index, action.get("id")),
        "severity": _require_choice(
            "action[%d].severity" % index, action.get("severity"), ACTION_SEVERITIES
        ),
        "closed": _require_flag(
            "action[%d].closed" % index, action.get("closed", False)
        ),
    }


def action_load(actions):
    """Severity counts and a weighted load over the actions still open."""
    if actions is None:
        actions = []
    if not isinstance(actions, (list, tuple)):
        raise ValueError("actions must be a list, got %r" % (actions,))
    counts = {severity: 0 for severity in ACTION_SEVERITIES}
    open_ids = []
    for i, action in enumerate(actions):
        row = normalise_action(action, i)
        if row["closed"]:
            continue
        counts[row["severity"]] += 1
        open_ids.append(row["id"])
    weighted = sum(ACTION_WEIGHTS[s] * n for s, n in counts.items())
    return {
        "counts": counts,
        "open_ids": tuple(open_ids),
        "open_total": len(open_ids),
        "weighted_load": weighted,
        "has_major": counts[SEVERITY_MAJOR] > 0,
    }


def assess_cleanliness_review(case):
    """Full readiness decision on the cleanliness inputs to one review."""
    if not isinstance(case, dict):
        raise ValueError("case must be a mapping, got %r" % (case,))
    item = _require_text("item", case.get("item"))
    review = _require_choice("review", case.get("review"), REVIEW_TYPES)
    sensitivity = _require_choice(
        "sensitivity", case.get("sensitivity"), SENSITIVITY_LEVELS
    )
    shortfall = pack_shortfall(review, sensitivity, case.get("submitted"))
    load = action_load(case.get("actions"))
    blocking = []
    conditions = []
    for name in shortfall["missing_mandatory"]:
        blocking.append("mandatory item absent from the pack: %s" % name)
    if load["has_major"]:
        blocking.append(
            "%d major contamination action(s) still open at the gate"
            % load["counts"][SEVERITY_MAJOR]
        )
    for name in shortfall["missing_supporting"]:
        conditions.append("supporting item absent from the pack: %s" % name)
    if load["counts"][SEVERITY_MINOR]:
        conditions.append(
            "%d minor contamination action(s) to close after the board"
            % load["counts"][SEVERITY_MINOR]
        )
    if blocking:
        verdict = VERDICT_NOT_READY
    elif conditions:
        verdict = VERDICT_CONDITIONAL
    else:
        verdict = VERDICT_READY
    return {
        "item": item,
        "review": review,
        "sensitivity": sensitivity,
        "pack": shortfall,
        "actions": load,
        "blocking": tuple(blocking),
        "conditions": tuple(conditions),
        "ready": verdict == VERDICT_READY,
        "gate_may_open": verdict != VERDICT_NOT_READY,
        "verdict": verdict,
    }
