#!/usr/bin/env python3
"""Execution of the adopted fault tree analysis procedure.

Anchor: ECSS-Q-ST-40-12C clause 5.1.2, which adopts the IEC 61025
procedure. The steps below are a paraphrase into implementable form; no
standard text is reproduced.

The procedure runs in one order and every step depends on the one
before it: the tree is constructed and its gate logic checked, the tree
is expanded to its minimal cut sets, the cut sets are evaluated
qualitatively by order, the top event is quantified from the cut sets,
the contributors are ranked by importance, the result is swept for
sensitivity to the weakest input, and the whole is reported.

Only coherent gate types are handled: AND, OR and k-out-of-n. A
non-coherent tree needs a different expansion and is rejected rather
than silently approximated.

Standard library only, offline, deterministic. Every product is taken
over a sorted event list so a rerun reproduces the same float.
"""

from __future__ import annotations

import itertools
import math

GATE_TYPES = ("AND", "OR", "KOFN")
QUANTIFICATION_METHODS = ("exact", "rare-event", "min-cut-upper-bound")
IMPORTANCE_MEASURES = ("birnbaum", "fussell-vesely", "criticality")

MAX_EXACT_CUT_SETS = 16
MAX_CUT_SETS = 4096

TARGET_MET = "target-met"
TARGET_NOT_MET = "target-not-met"
TARGET_NOT_DECLARED = "target-not-declared"

_REL_TOL = 1e-9
_ABS_TOL = 1e-15


def _is_finite_number(value):
    return (
        isinstance(value, (int, float))
        and not isinstance(value, bool)
        and math.isfinite(value)
    )


def _require_probability(name, value):
    if not _is_finite_number(value):
        raise ValueError("%s must be a finite number, got %r" % (name, value))
    if value < 0.0 or value > 1.0:
        raise ValueError("%s must lie between 0 and 1, got %r" % (name, value))
    return float(value)


def _require_positive(name, value):
    if not _is_finite_number(value):
        raise ValueError("%s must be a finite number, got %r" % (name, value))
    if value <= 0.0:
        raise ValueError("%s must be greater than zero, got %r" % (name, value))
    return float(value)


def _require_identifier(name, value):
    if not isinstance(value, str) or not value.strip():
        raise ValueError("%s must be a non-empty string, got %r" % (name, value))
    return value.strip()


def _at_most(value, limit):
    """value <= limit, absorbing floating-point representation error.

    A top event probability is a sum of signed products, so a case that
    sits exactly on its target can land a few units in the last place
    above it. The target is never relaxed; only the comparison tolerates
    the representation error.
    """
    return value <= limit or math.isclose(
        value, limit, rel_tol=_REL_TOL, abs_tol=_ABS_TOL
    )


def validate_tree(tree):
    """Check construction and gate logic before anything is expanded."""
    if not isinstance(tree, dict):
        raise ValueError("tree must be a mapping, got %r" % (tree,))
    gates = tree.get("gates")
    basic_events = tree.get("basic_events")
    if not isinstance(gates, dict) or not gates:
        raise ValueError("tree needs a non-empty gates mapping")
    if not isinstance(basic_events, dict) or not basic_events:
        raise ValueError("tree needs a non-empty basic_events mapping")
    overlap = set(gates) & set(basic_events)
    if overlap:
        raise ValueError(
            "identifier used as both a gate and a basic event: %s"
            % ", ".join(sorted(overlap))
        )
    top = _require_identifier("top", tree.get("top"))
    if top not in gates:
        raise ValueError("top event %r is not a gate in the tree" % top)
    events = {}
    for name, probability in basic_events.items():
        key = _require_identifier("basic event id", name)
        events[key] = _require_probability("probability of %s" % key, probability)
    normalized_gates = {}
    for name, gate in gates.items():
        key = _require_identifier("gate id", name)
        if not isinstance(gate, dict):
            raise ValueError("gate %s must be a mapping, got %r" % (key, gate))
        gate_type = gate.get("type")
        if gate_type not in GATE_TYPES:
            raise ValueError(
                "gate %s has type %r; only coherent gates %s are handled"
                % (key, gate_type, ", ".join(GATE_TYPES))
            )
        inputs = gate.get("inputs")
        if not isinstance(inputs, (list, tuple)) or len(inputs) < 2:
            raise ValueError("gate %s needs at least two inputs" % key)
        resolved = [_require_identifier("input of gate %s" % key, i) for i in inputs]
        if len(set(resolved)) != len(resolved):
            raise ValueError("gate %s repeats an input" % key)
        for child in resolved:
            if child not in gates and child not in events:
                raise ValueError(
                    "gate %s refers to %r, which is neither a gate nor a basic event"
                    % (key, child)
                )
        entry = {"type": gate_type, "inputs": tuple(resolved)}
        if gate_type == "KOFN":
            k = gate.get("k")
            if not isinstance(k, int) or isinstance(k, bool):
                raise ValueError("gate %s needs an integer k" % key)
            if k < 1 or k > len(resolved):
                raise ValueError(
                    "gate %s has k=%d outside 1..%d" % (key, k, len(resolved))
                )
            entry["k"] = k
        normalized_gates[key] = entry
    normalized = {"top": top, "gates": normalized_gates, "basic_events": events}
    _reject_cycles(normalized)
    return normalized


def _reject_cycles(tree):
    visiting = set()
    done = set()

    def walk(node, path):
        if node in tree["basic_events"] or node in done:
            return
        if node in visiting:
            raise ValueError(
                "tree contains a cycle: %s" % " -> ".join(path + [node])
            )
        visiting.add(node)
        for child in tree["gates"][node]["inputs"]:
            walk(child, path + [node])
        visiting.discard(node)
        done.add(node)

    walk(tree["top"], [])


def unreachable_gates(tree):
    """Gates drawn on the sheet that the top event never develops."""
    tree = validate_tree(tree)
    reached = set()

    def walk(node):
        if node in tree["basic_events"] or node in reached:
            return
        reached.add(node)
        for child in tree["gates"][node]["inputs"]:
            walk(child)

    walk(tree["top"])
    return tuple(sorted(set(tree["gates"]) - reached))


def _minimize(sets):
    ordered = sorted(sets, key=lambda s: (len(s), sorted(s)))
    minimal = []
    for candidate in ordered:
        if not any(existing <= candidate for existing in minimal):
            minimal.append(candidate)
    return minimal


def _combine_and(groups):
    combined = [frozenset()]
    for group in groups:
        merged = []
        for left in combined:
            for right in group:
                merged.append(left | right)
        combined = _minimize(merged)
        if len(combined) > MAX_CUT_SETS:
            raise ValueError(
                "expansion exceeded %d cut sets; reduce the tree or modularize it"
                % MAX_CUT_SETS
            )
    return combined


def minimal_cut_sets(tree):
    """Expand the tree to its minimal cut sets, smallest order first."""
    tree = validate_tree(tree)
    cache = {}

    def expand(node):
        if node in tree["basic_events"]:
            return [frozenset([node])]
        if node in cache:
            return cache[node]
        gate = tree["gates"][node]
        groups = [expand(child) for child in gate["inputs"]]
        if gate["type"] == "OR":
            combined = _minimize([s for group in groups for s in group])
        elif gate["type"] == "AND":
            combined = _combine_and(groups)
        else:
            k = gate["k"]
            collected = []
            for choice in itertools.combinations(range(len(groups)), k):
                collected.extend(_combine_and([groups[i] for i in choice]))
            combined = _minimize(collected)
        if len(combined) > MAX_CUT_SETS:
            raise ValueError(
                "expansion exceeded %d cut sets; reduce the tree or modularize it"
                % MAX_CUT_SETS
            )
        cache[node] = combined
        return combined

    result = expand(tree["top"])
    return tuple(tuple(sorted(s)) for s in _minimize(result))


def cut_set_order_profile(cut_sets):
    """How many cut sets sit at each order, lowest order first."""
    if not isinstance(cut_sets, (list, tuple)):
        raise ValueError("cut_sets must be a sequence, got %r" % (cut_sets,))
    profile = {}
    for cut_set in cut_sets:
        if not isinstance(cut_set, (list, tuple, frozenset, set)) or not cut_set:
            raise ValueError("every cut set must be a non-empty sequence")
        order = len(set(cut_set))
        profile[order] = profile.get(order, 0) + 1
    return dict(sorted(profile.items()))


def single_point_failures(cut_sets):
    """The order-one cut sets: one event on its own reaches the top."""
    profile_input = cut_sets
    if not isinstance(profile_input, (list, tuple)):
        raise ValueError("cut_sets must be a sequence, got %r" % (cut_sets,))
    return tuple(
        sorted(tuple(sorted(cs))[0] for cs in cut_sets if len(set(cs)) == 1)
    )


def cut_set_probability(cut_set, basic_events):
    """Probability of one cut set, taken over a sorted event list."""
    if not isinstance(basic_events, dict) or not basic_events:
        raise ValueError("basic_events must be a non-empty mapping")
    if not isinstance(cut_set, (list, tuple, frozenset, set)) or not cut_set:
        raise ValueError("cut_set must be a non-empty sequence")
    product = 1.0
    for event in sorted(set(cut_set)):
        if event not in basic_events:
            raise ValueError("cut set names unknown basic event %r" % event)
        product *= _require_probability(
            "probability of %s" % event, basic_events[event]
        )
    return product


def _exact_from_cut_sets(cut_sets, basic_events):
    count = len(cut_sets)
    if count == 0:
        return 0.0
    if count > MAX_EXACT_CUT_SETS:
        raise ValueError(
            "exact quantification needs at most %d minimal cut sets, got %d; "
            "use the min-cut-upper-bound method instead"
            % (MAX_EXACT_CUT_SETS, count)
        )
    total = 0.0
    for size in range(1, count + 1):
        for choice in itertools.combinations(range(count), size):
            union = set()
            for index in choice:
                union |= set(cut_sets[index])
            term = cut_set_probability(sorted(union), basic_events)
            total += term if size % 2 == 1 else -term
    return min(max(total, 0.0), 1.0)


def top_event_probability(tree, method="exact", cut_sets=None):
    """Quantify the top event from the minimal cut sets."""
    if method not in QUANTIFICATION_METHODS:
        raise ValueError(
            "method must be one of %s, got %r"
            % (", ".join(QUANTIFICATION_METHODS), method)
        )
    tree = validate_tree(tree)
    if cut_sets is None:
        cut_sets = minimal_cut_sets(tree)
    events = tree["basic_events"]
    if method == "exact":
        return _exact_from_cut_sets(list(cut_sets), events)
    if method == "rare-event":
        total = 0.0
        for cut_set in cut_sets:
            total += cut_set_probability(cut_set, events)
        return min(total, 1.0)
    survival = 1.0
    for cut_set in cut_sets:
        survival *= 1.0 - cut_set_probability(cut_set, events)
    return 1.0 - survival


def _with_probability(tree, event, probability):
    events = dict(tree["basic_events"])
    if event not in events:
        raise ValueError("unknown basic event %r" % event)
    events[event] = _require_probability("substituted probability", probability)
    return {"top": tree["top"], "gates": tree["gates"], "basic_events": events}


def birnbaum_importance(tree, event, cut_sets=None):
    """Sensitivity of the top event to the state of one basic event."""
    tree = validate_tree(tree)
    event = _require_identifier("event", event)
    if event not in tree["basic_events"]:
        raise ValueError("unknown basic event %r" % event)
    if cut_sets is None:
        cut_sets = minimal_cut_sets(tree)
    present = _exact_from_cut_sets(
        list(cut_sets), _with_probability(tree, event, 1.0)["basic_events"]
    )
    absent = _exact_from_cut_sets(
        list(cut_sets), _with_probability(tree, event, 0.0)["basic_events"]
    )
    return present - absent


def fussell_vesely_importance(tree, event, cut_sets=None):
    """Share of the top event carried by cut sets containing the event."""
    tree = validate_tree(tree)
    event = _require_identifier("event", event)
    if event not in tree["basic_events"]:
        raise ValueError("unknown basic event %r" % event)
    if cut_sets is None:
        cut_sets = minimal_cut_sets(tree)
    total = _exact_from_cut_sets(list(cut_sets), tree["basic_events"])
    if total <= 0.0:
        raise ValueError(
            "top event probability is zero; importance measures are undefined"
        )
    involved = [cs for cs in cut_sets if event in set(cs)]
    if not involved:
        return 0.0
    return _exact_from_cut_sets(involved, tree["basic_events"]) / total


def criticality_importance(tree, event, cut_sets=None):
    """Birnbaum importance weighted by the event's own probability."""
    tree = validate_tree(tree)
    if cut_sets is None:
        cut_sets = minimal_cut_sets(tree)
    total = _exact_from_cut_sets(list(cut_sets), tree["basic_events"])
    if total <= 0.0:
        raise ValueError(
            "top event probability is zero; importance measures are undefined"
        )
    birnbaum = birnbaum_importance(tree, event, cut_sets)
    return birnbaum * tree["basic_events"][event] / total


def rank_importance(tree, measure="fussell-vesely", cut_sets=None):
    """Rank every basic event by one importance measure, largest first."""
    if measure not in IMPORTANCE_MEASURES:
        raise ValueError(
            "measure must be one of %s, got %r"
            % (", ".join(IMPORTANCE_MEASURES), measure)
        )
    tree = validate_tree(tree)
    if cut_sets is None:
        cut_sets = minimal_cut_sets(tree)
    functions = {
        "birnbaum": birnbaum_importance,
        "fussell-vesely": fussell_vesely_importance,
        "criticality": criticality_importance,
    }
    scored = []
    for event in sorted(tree["basic_events"]):
        scored.append((event, functions[measure](tree, event, cut_sets)))
    scored.sort(key=lambda item: (-item[1], item[0]))
    return tuple(scored)


def sensitivity_sweep(tree, event, factors=(0.1, 1.0, 10.0), cut_sets=None):
    """Sweep one basic event probability and report the top event response."""
    tree = validate_tree(tree)
    event = _require_identifier("event", event)
    if event not in tree["basic_events"]:
        raise ValueError("unknown basic event %r" % event)
    if not isinstance(factors, (list, tuple)) or not factors:
        raise ValueError("factors must be a non-empty sequence, got %r" % (factors,))
    if cut_sets is None:
        cut_sets = minimal_cut_sets(tree)
    baseline = _exact_from_cut_sets(list(cut_sets), tree["basic_events"])
    swept = []
    for factor in factors:
        scale = _require_positive("factor", factor)
        scaled = min(1.0, tree["basic_events"][event] * scale)
        events = _with_probability(tree, event, scaled)["basic_events"]
        probability = _exact_from_cut_sets(list(cut_sets), events)
        swept.append(
            {
                "factor": scale,
                "event_probability": scaled,
                "top_event_probability": probability,
                "ratio_to_baseline": (
                    probability / baseline if baseline > 0.0 else None
                ),
            }
        )
    return tuple(swept)


def fta_report(tree, target_probability=None, sensitivity_event=None,
               sensitivity_factors=(0.1, 1.0, 10.0)):
    """Run the whole procedure and assemble the reporting record."""
    tree = validate_tree(tree)
    cut_sets = minimal_cut_sets(tree)
    findings = []
    orphans = unreachable_gates(tree)
    if orphans:
        findings.append(
            "gates drawn but never developed from the top event: %s"
            % ", ".join(orphans)
        )
    spf = single_point_failures(cut_sets)
    if spf:
        findings.append(
            "order-one cut sets present, each a single point failure: %s"
            % ", ".join(spf)
        )
    probabilities = {}
    for method in QUANTIFICATION_METHODS:
        try:
            probabilities[method] = top_event_probability(tree, method, cut_sets)
        except ValueError as exc:
            probabilities[method] = None
            findings.append("%s quantification unavailable: %s" % (method, exc))
    report = {
        "top_event": tree["top"],
        "minimal_cut_sets": cut_sets,
        "cut_set_count": len(cut_sets),
        "order_profile": cut_set_order_profile(cut_sets),
        "single_point_failures": spf,
        "probabilities": probabilities,
        "findings": findings,
    }
    exact = probabilities.get("exact")
    if exact is not None and exact > 0.0:
        report["importance"] = {
            measure: rank_importance(tree, measure, cut_sets)
            for measure in IMPORTANCE_MEASURES
        }
    else:
        report["importance"] = {}
        findings.append(
            "importance ranking omitted: the top event probability is zero or "
            "was not quantified exactly"
        )
    if sensitivity_event is not None:
        report["sensitivity"] = sensitivity_sweep(
            tree, sensitivity_event, sensitivity_factors, cut_sets
        )
    else:
        report["sensitivity"] = ()
    if target_probability is None:
        report["verdict"] = TARGET_NOT_DECLARED
        return report
    target = _require_probability("target_probability", target_probability)
    reference = exact if exact is not None else probabilities["min-cut-upper-bound"]
    report["target_probability"] = target
    report["verdict"] = TARGET_MET if _at_most(reference, target) else TARGET_NOT_MET
    if report["verdict"] == TARGET_NOT_MET:
        findings.append(
            "quantified %.6g against a target of %.6g" % (reference, target)
        )
    return report
