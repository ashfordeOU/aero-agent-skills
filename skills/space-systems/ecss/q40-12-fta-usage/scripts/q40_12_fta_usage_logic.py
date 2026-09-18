#!/usr/bin/env python3
"""Scoping of fault tree analysis inside an ECSS project.

Anchor: ECSS-Q-ST-40-12C clause 4 (applicability of the adopted
IEC 61025 procedure) and clause 5.1.1 (when a fault tree is the
technique, and how it divides work with an FMECA). The procedure below
is a paraphrase into implementable steps; no standard text is
reproduced.

A fault tree reasons downwards from one undesired consequence to the
combinations of lower-level events that produce it. An FMECA reasons
upwards from every single failure mode of every item to its effect.
The two answer different questions, so the first decision on any
project is which of them the stated need actually asks for, and the
second is which receiving analysis the resulting tree feeds: the
hazard analysis of ECSS-Q-ST-40-02, the dependability analyses of
ECSS-Q-ST-30C, or the critical items list.

Standard library only, offline, deterministic.
"""

from __future__ import annotations

import math

ANALYSIS_DIRECTIONS = (
    "top-down-from-consequence",
    "bottom-up-from-failure-mode",
    "both-directions",
    "not-yet-stated",
)
SEVERITY_CATEGORIES = ("catastrophic", "critical", "major", "minor")

TECHNIQUE_FTA = "fault-tree-analysis"
TECHNIQUE_FMECA = "fmeca"
TECHNIQUE_BOTH = "fault-tree-analysis-with-fmeca"
TECHNIQUE_NONE = "neither-technique-addresses-the-need"

DEPTH_QUALITATIVE = "qualitative-only"
DEPTH_QUANTITATIVE = "qualitative-and-quantitative"

HAZARD_ANALYSIS = "hazard-analysis-q-st-40-02"
DEPENDABILITY_ANALYSIS = "dependability-analysis-q-st-30c"
CRITICAL_ITEMS_LIST = "critical-items-list"

VERDICT_IN_SCOPE = "fta-in-scope"
VERDICT_IN_SCOPE_WITH_FMECA = "fta-in-scope-with-fmeca"
VERDICT_NOT_THE_TECHNIQUE = "fta-not-the-technique"

DEFAULT_TRACEABILITY_THRESHOLD = 1.0

BOOLEAN_NEED_KEYS = (
    "combination_logic_needed",
    "enumerate_all_failure_modes",
    "probability_target_declared",
    "common_cause_suspected",
    "software_or_human_contributors",
    "multi_function_scope",
)

_REL_TOL = 1e-9
_ABS_TOL = 1e-12


def _is_finite_number(value):
    return (
        isinstance(value, (int, float))
        and not isinstance(value, bool)
        and math.isfinite(value)
    )


def _require_choice(name, value, allowed):
    if value not in allowed:
        raise ValueError(
            "%s must be one of %s, got %r" % (name, ", ".join(allowed), value)
        )
    return value


def _require_bool(name, value):
    if not isinstance(value, bool):
        raise ValueError("%s must be a boolean, got %r" % (name, value))
    return value


def _require_text(name, value):
    if not isinstance(value, str) or not value.strip():
        raise ValueError("%s must be a non-empty string, got %r" % (name, value))
    return value.strip()


def _require_fraction(name, value):
    if not _is_finite_number(value):
        raise ValueError("%s must be a finite number, got %r" % (name, value))
    if value < 0.0 or value > 1.0:
        raise ValueError("%s must lie between 0 and 1, got %r" % (name, value))
    return float(value)


def _at_least(value, limit):
    """value >= limit, absorbing floating-point representation error.

    A traceability fraction is a ratio of counts, so a set that is
    exactly complete can land a few units in the last place below one.
    The threshold itself is never lowered; only the comparison tolerates
    the representation error.
    """
    return value >= limit or math.isclose(
        value, limit, rel_tol=_REL_TOL, abs_tol=_ABS_TOL
    )


def validate_need(need):
    """Normalize the statement of what the project actually wants analysed."""
    if not isinstance(need, dict):
        raise ValueError("need must be a mapping, got %r" % (need,))
    normalized = {
        "top_event": _require_text("top_event", need.get("top_event")),
        "direction": _require_choice(
            "direction", need.get("direction"), ANALYSIS_DIRECTIONS
        ),
        "severity": _require_choice(
            "severity", need.get("severity"), SEVERITY_CATEGORIES
        ),
    }
    for key in BOOLEAN_NEED_KEYS:
        normalized[key] = _require_bool(key, need.get(key))
    return normalized


def select_technique(need):
    """Decide whether a tree, an FMECA or both carry the stated need."""
    need = validate_need(need)
    rationale = []
    wants_fta = False
    wants_fmeca = False
    if need["direction"] in ("top-down-from-consequence", "both-directions"):
        wants_fta = True
        rationale.append(
            "the need is stated from a consequence downwards, which is the "
            "direction a tree reasons in"
        )
    if need["direction"] in ("bottom-up-from-failure-mode", "both-directions"):
        wants_fmeca = True
        rationale.append(
            "the need is stated from item failure modes upwards, which is the "
            "direction an FMECA reasons in"
        )
    if need["combination_logic_needed"]:
        wants_fta = True
        rationale.append(
            "combinations of events have to be represented, and an FMECA "
            "carries one failure mode at a time"
        )
    if need["common_cause_suspected"]:
        wants_fta = True
        rationale.append(
            "a common cause is suspected, which only shows up as a shared "
            "event across cut sets"
        )
    if need["multi_function_scope"]:
        wants_fta = True
        rationale.append(
            "the consequence crosses more than one function, so no single "
            "item worksheet holds it"
        )
    if need["software_or_human_contributors"]:
        wants_fta = True
        rationale.append(
            "software and human contributors have no item worksheet, so they "
            "enter as basic events on a tree"
        )
    if need["enumerate_all_failure_modes"]:
        wants_fmeca = True
        rationale.append(
            "every failure mode has to be enumerated, which is the FMECA "
            "obligation and not a tree's"
        )
    if wants_fta and wants_fmeca:
        technique = TECHNIQUE_BOTH
    elif wants_fta:
        technique = TECHNIQUE_FTA
    elif wants_fmeca:
        technique = TECHNIQUE_FMECA
    else:
        technique = TECHNIQUE_NONE
        rationale.append(
            "no direction, combination, common cause or enumeration duty was "
            "declared, so the need does not yet name an analysis"
        )
    return {"technique": technique, "rationale": tuple(rationale)}


def supported_analyses(need):
    """Name the receiving analyses a tree built for this need would feed."""
    need = validate_need(need)
    fed = []
    if need["severity"] in ("catastrophic", "critical"):
        fed.append(HAZARD_ANALYSIS)
        fed.append(CRITICAL_ITEMS_LIST)
    if need["probability_target_declared"]:
        fed.append(DEPENDABILITY_ANALYSIS)
    return tuple(fed)


def required_depth(need):
    """Qualitative cut sets alone, or cut sets plus a quantified top event."""
    need = validate_need(need)
    if need["probability_target_declared"] or need["severity"] == "catastrophic":
        return DEPTH_QUANTITATIVE
    return DEPTH_QUALITATIVE


def iec_61025_elements(need):
    """Procedure elements of the adopted method that this need switches on."""
    need = validate_need(need)
    applicable = ["tree-construction-and-gate-logic", "minimal-cut-set-determination"]
    excluded = []
    if required_depth(need) == DEPTH_QUANTITATIVE:
        applicable.append("top-event-quantification")
        applicable.append("importance-and-sensitivity-evaluation")
    else:
        excluded.append("top-event-quantification")
        excluded.append("importance-and-sensitivity-evaluation")
    if need["common_cause_suspected"]:
        applicable.append("common-cause-event-modelling")
    else:
        excluded.append("common-cause-event-modelling")
    applicable.append("fta-reporting")
    return {"applicable": tuple(applicable), "excluded": tuple(excluded)}


def division_of_labour(technique):
    """Which artefact each technique owns once the split has been made."""
    _require_choice(
        "technique",
        technique,
        (TECHNIQUE_FTA, TECHNIQUE_FMECA, TECHNIQUE_BOTH, TECHNIQUE_NONE),
    )
    if technique == TECHNIQUE_NONE:
        return {}
    owners = {
        "single-item-failure-mode-effects": TECHNIQUE_FMECA,
        "detection-and-compensating-provisions": TECHNIQUE_FMECA,
        "severity-per-failure-mode": TECHNIQUE_FMECA,
        "event-combination-and-gate-logic": TECHNIQUE_FTA,
        "minimal-cut-sets": TECHNIQUE_FTA,
        "top-event-probability": TECHNIQUE_FTA,
        "common-cause-contribution": TECHNIQUE_FTA,
    }
    if technique == TECHNIQUE_BOTH:
        return owners
    return {k: v for k, v in owners.items() if v == technique}


def basic_event_traceability(basic_event_ids, failure_mode_ids):
    """How far the tree's basic events trace back to declared failure modes."""
    if not isinstance(basic_event_ids, (list, tuple)) or not basic_event_ids:
        raise ValueError(
            "basic_event_ids must be a non-empty sequence, got %r" % (basic_event_ids,)
        )
    if not isinstance(failure_mode_ids, (list, tuple, set, frozenset)):
        raise ValueError(
            "failure_mode_ids must be a sequence or set, got %r" % (failure_mode_ids,)
        )
    events = []
    for item in basic_event_ids:
        events.append(_require_text("basic event id", item))
    if len(set(events)) != len(events):
        raise ValueError("basic_event_ids contains a duplicate identifier")
    modes = {_require_text("failure mode id", item) for item in failure_mode_ids}
    untraced = tuple(sorted(event for event in events if event not in modes))
    traced = len(events) - len(untraced)
    return {
        "basic_events": len(events),
        "traced": traced,
        "untraced": untraced,
        "fraction": traced / float(len(events)),
    }


def traceability_verdict(fraction, threshold=DEFAULT_TRACEABILITY_THRESHOLD):
    """Grade a traceability fraction against the project threshold."""
    fraction = _require_fraction("fraction", fraction)
    threshold = _require_fraction("threshold", threshold)
    return "traceable" if _at_least(fraction, threshold) else "traceability-shortfall"


def scope_fta_usage(case, traceability_threshold=DEFAULT_TRACEABILITY_THRESHOLD):
    """Full clause 4 / 5.1.1 scoping decision with a verdict and findings."""
    if not isinstance(case, dict):
        raise ValueError("case must be a mapping, got %r" % (case,))
    need = validate_need(case)
    selection = select_technique(need)
    technique = selection["technique"]
    fed = supported_analyses(need)
    depth = required_depth(need)
    elements = iec_61025_elements(need)
    findings = []
    if technique == TECHNIQUE_BOTH:
        verdict = VERDICT_IN_SCOPE_WITH_FMECA
    elif technique == TECHNIQUE_FTA:
        verdict = VERDICT_IN_SCOPE
    else:
        verdict = VERDICT_NOT_THE_TECHNIQUE
    if technique == TECHNIQUE_FMECA:
        findings.append(
            "the need enumerates failure modes without any combination duty, "
            "so an FMECA answers it and a tree would add nothing"
        )
    if technique == TECHNIQUE_NONE:
        findings.append(
            "the need names neither a consequence to reason down from nor a "
            "set of failure modes to reason up from"
        )
    if not fed:
        findings.append(
            "no receiving analysis was identified: the severity is below the "
            "hazard analysis threshold and no probability target was declared"
        )
    result = {
        "top_event": need["top_event"],
        "technique": technique,
        "rationale": selection["rationale"],
        "supported_analyses": fed,
        "depth": depth,
        "applicable_elements": elements["applicable"],
        "excluded_elements": elements["excluded"],
        "division_of_labour": division_of_labour(technique),
        "verdict": verdict,
        "findings": findings,
    }
    basic_events = case.get("basic_event_ids")
    failure_modes = case.get("failure_mode_ids")
    if basic_events is None or failure_modes is None:
        result.update(
            {
                "traceability": None,
                "traceability_verdict": "traceability-not-evaluated",
            }
        )
        findings.append(
            "no basic event list or failure mode list supplied; the technique "
            "is fixed but the tree is not yet tied back to the item analysis"
        )
        return result
    trace = basic_event_traceability(basic_events, failure_modes)
    grade = traceability_verdict(trace["fraction"], traceability_threshold)
    result.update({"traceability": trace, "traceability_verdict": grade})
    if grade != "traceable":
        findings.append(
            "%d of %d basic events do not resolve to a declared failure mode: %s"
            % (
                len(trace["untraced"]),
                trace["basic_events"],
                ", ".join(trace["untraced"]),
            )
        )
    return result
