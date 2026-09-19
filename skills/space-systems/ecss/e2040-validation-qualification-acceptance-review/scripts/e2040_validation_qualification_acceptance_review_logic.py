#!/usr/bin/env python3
"""Final validation, qualification and acceptance review of a device.

Anchor: ECSS-E-ST-20-40 clause 5.8.6. The procedure below is a
paraphrase into implementable steps; no standard text is reproduced.

The closing gate reads three evidence streams together:

    validation      the right device was specified and built
    qualification   the design survives its environment with margin
    acceptance      this delivered unit was built to that design

Each item of evidence carries the model it was produced on, and a
stream only admits some model kinds. Qualification evidence belongs to
a qualification or protoflight article; acceptance evidence belongs to
the flight or protoflight unit that ships.

Qualification covers acceptance only when the qualification level
envelopes the acceptance level by the declared ratio. Open actions are
budgeted by the criticality category of the device, and a waived item
is an accepted shortfall that needs an approved deviation behind it.

Standard library only, offline, deterministic.
"""

from __future__ import annotations

import math

STREAMS = ("validation", "qualification", "acceptance")
ITEM_STATES = ("closed", "open", "waived", "not-started")
CRITICALITY_CATEGORIES = ("category-1", "category-2", "category-3", "category-4")
MODEL_KINDS = (
    "engineering-model",
    "qualification-model",
    "protoflight-model",
    "flight-model",
)

STREAM_ADMITTED_MODELS = {
    "validation": (
        "engineering-model",
        "qualification-model",
        "protoflight-model",
        "flight-model",
    ),
    "qualification": ("qualification-model", "protoflight-model"),
    "acceptance": ("flight-model", "protoflight-model"),
}

OPEN_ACTION_BUDGET = {
    "category-1": 0,
    "category-2": 0,
    "category-3": 2,
    "category-4": 5,
}

DEFAULT_ENVELOPE_RATIO = 1.25

GATE_OPEN = "review-gate-open"
GATE_OPEN_WITH_ACTIONS = "review-gate-open-against-actions"
GATE_HELD = "review-gate-held"

_REL_TOL = 1e-9
_ABS_TOL = 1e-12


def _is_finite_number(value):
    return (
        isinstance(value, (int, float))
        and not isinstance(value, bool)
        and math.isfinite(value)
    )


def _require_positive(name, value):
    if not _is_finite_number(value):
        raise ValueError("%s must be a finite number, got %r" % (name, value))
    if value <= 0.0:
        raise ValueError("%s must be greater than zero, got %r" % (name, value))
    return float(value)


def _require_choice(name, value, allowed):
    if value not in allowed:
        raise ValueError(
            "%s must be one of %s, got %r" % (name, ", ".join(allowed), value)
        )
    return value


def _at_least(value, limit):
    """value >= limit, absorbing floating-point representation error.

    An envelope ratio is a quotient of two measured levels, so a case
    that is exactly on the requirement can land a few units in the last
    place below it. The requirement is never lowered; only the
    comparison tolerates the representation error.
    """
    return value >= limit or math.isclose(
        value, limit, rel_tol=_REL_TOL, abs_tol=_ABS_TOL
    )


def validate_evidence_item(item):
    """Normalise one evidence item and reject an unusable declaration."""
    if not isinstance(item, dict):
        raise ValueError("evidence item must be a mapping, got %r" % (item,))
    identifier = item.get("id")
    if not isinstance(identifier, str) or not identifier.strip():
        raise ValueError("evidence item needs a non-empty id, got %r" % (identifier,))
    stream = _require_choice("stream", item.get("stream"), STREAMS)
    state = _require_choice("state", item.get("state"), ITEM_STATES)
    model_kind = _require_choice("model_kind", item.get("model_kind"), MODEL_KINDS)
    deviation = item.get("deviation_reference")
    if state == "waived":
        if not isinstance(deviation, str) or not deviation.strip():
            raise ValueError(
                "item %s is waived but carries no approved deviation reference"
                % identifier
            )
        deviation = deviation.strip()
    else:
        deviation = None
    return {
        "id": identifier.strip(),
        "stream": stream,
        "state": state,
        "model_kind": model_kind,
        "deviation_reference": deviation,
    }


def normalise_items(items):
    """Normalise a whole evidence list and reject a duplicate item id."""
    if not isinstance(items, (list, tuple)) or not items:
        raise ValueError("items must be a non-empty sequence of evidence items")
    normalised = []
    seen = set()
    for item in items:
        entry = validate_evidence_item(item)
        if entry["id"] in seen:
            raise ValueError("duplicate evidence item id %r" % entry["id"])
        seen.add(entry["id"])
        normalised.append(entry)
    return normalised


def stream_closure(items, stream):
    """Closure counts and closed fraction for one evidence stream."""
    _require_choice("stream", stream, STREAMS)
    entries = [e for e in normalise_items(items) if e["stream"] == stream]
    total = len(entries)
    if total == 0:
        raise ValueError(
            "stream %s carries no required evidence; the review package is "
            "incomplete" % stream
        )
    counts = {state: 0 for state in ITEM_STATES}
    for entry in entries:
        counts[entry["state"]] += 1
    return {
        "stream": stream,
        "required": total,
        "closed": counts["closed"],
        "open": counts["open"],
        "waived": counts["waived"],
        "not_started": counts["not-started"],
        "closed_fraction": counts["closed"] / float(total),
    }


def model_admissibility_findings(items):
    """Findings for evidence claimed on a model its stream does not admit."""
    findings = []
    for entry in normalise_items(items):
        admitted = STREAM_ADMITTED_MODELS[entry["stream"]]
        if entry["model_kind"] not in admitted:
            findings.append(
                "item %s carries %s evidence produced on a %s; that stream "
                "admits only %s"
                % (
                    entry["id"],
                    entry["stream"],
                    entry["model_kind"],
                    " or ".join(admitted),
                )
            )
    return findings


def envelope_ratio(qualification_level, acceptance_level):
    """Ratio by which the qualification level exceeds the acceptance level."""
    qualification = _require_positive("qualification_level", qualification_level)
    acceptance = _require_positive("acceptance_level", acceptance_level)
    return qualification / acceptance


def envelope_compliant(
    qualification_level, acceptance_level, required_ratio=DEFAULT_ENVELOPE_RATIO
):
    """Does qualification envelope acceptance by the declared ratio."""
    required = _require_positive("required_ratio", required_ratio)
    return _at_least(envelope_ratio(qualification_level, acceptance_level), required)


def open_action_budget(criticality):
    """Open items the gate tolerates for a device of this category."""
    _require_choice("criticality", criticality, CRITICALITY_CATEGORIES)
    return OPEN_ACTION_BUDGET[criticality]


def plan_final_review(case):
    """Full clause 5.8.6 gate decision with the binding finding named."""
    if not isinstance(case, dict):
        raise ValueError("case must be a mapping, got %r" % (case,))
    criticality = _require_choice(
        "criticality", case.get("criticality"), CRITICALITY_CATEGORIES
    )
    entries = normalise_items(case.get("items"))
    closures = {stream: stream_closure(entries, stream) for stream in STREAMS}
    findings = model_admissibility_findings(entries)

    open_total = sum(c["open"] for c in closures.values())
    not_started_total = sum(c["not_started"] for c in closures.values())
    waived_total = sum(c["waived"] for c in closures.values())
    budget = open_action_budget(criticality)

    qualification_level = case.get("qualification_level")
    acceptance_level = case.get("acceptance_level")
    required_ratio = case.get("required_envelope_ratio", DEFAULT_ENVELOPE_RATIO)
    if qualification_level is None or acceptance_level is None:
        ratio = None
        envelope_ok = None
        findings.append(
            "no qualification and acceptance level pair supplied; the envelope "
            "is not demonstrated"
        )
    else:
        ratio = envelope_ratio(qualification_level, acceptance_level)
        envelope_ok = envelope_compliant(
            qualification_level, acceptance_level, required_ratio
        )
        if not envelope_ok:
            findings.append(
                "qualification envelopes acceptance by %.4f against a required "
                "%.4f" % (ratio, _require_positive("required_ratio", required_ratio))
            )

    binding = None
    if not_started_total:
        verdict = GATE_HELD
        binding = "not-started-evidence"
        findings.append(
            "%d evidence item(s) have not been started" % not_started_total
        )
    elif model_admissibility_findings(entries):
        verdict = GATE_HELD
        binding = "model-kind-not-admitted"
    elif envelope_ok is False:
        verdict = GATE_HELD
        binding = "envelope-ratio-not-met"
    elif envelope_ok is None:
        verdict = GATE_HELD
        binding = "envelope-not-demonstrated"
    elif open_total > budget:
        verdict = GATE_HELD
        binding = "open-actions-over-budget"
        findings.append(
            "%d open item(s) against a budget of %d for %s"
            % (open_total, budget, criticality)
        )
    elif open_total or waived_total:
        verdict = GATE_OPEN_WITH_ACTIONS
        binding = "open-actions-within-budget" if open_total else "waiver-outstanding"
    else:
        verdict = GATE_OPEN

    return {
        "device_id": case.get("device_id"),
        "criticality": criticality,
        "closures": closures,
        "open_total": open_total,
        "waived_total": waived_total,
        "not_started_total": not_started_total,
        "open_action_budget": budget,
        "envelope_ratio": ratio,
        "envelope_compliant": envelope_ok,
        "verdict": verdict,
        "binding_finding": binding,
        "findings": findings,
    }
