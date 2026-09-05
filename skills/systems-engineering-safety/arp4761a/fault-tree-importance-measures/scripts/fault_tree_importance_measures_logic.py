"""Fault tree importance measures (systems-engineering-safety, arp4761a pack).

Rank the basic events of a fault tree by their contribution to the top
event probability, given the minimal cut sets and the basic-event
probabilities. Pure stdlib, deterministic, offline.

Conventions (spec wave-38):
- cut_sets: list of sets of basic-event names, one set per minimal cut set.
- probs: dict mapping each basic-event name to its probability in (0, 1).
- The top event probability Q is the union probability of the cut sets
  under event independence, computed by exact inclusion-exclusion over
  the 2**n - 1 non-empty subsets of the n cut sets.
- Non-physical inputs raise ValueError: empty cut_sets, an empty cut
  set, an unknown event name, a probability outside (0, 1), an event
  that appears in no cut set, or an unknown measure name.
"""

import math

DEFAULT_DOMINANCE_THRESHOLD = 0.1
MEASURE_KEYS = ("birnbaum", "fussell_vesely", "raw", "rrw")


def _validate_inputs(cut_sets, probs):
    """Check cut_sets and probs are physical; raise ValueError otherwise."""
    if not cut_sets:
        raise ValueError("cut_sets must be a non-empty list of event-name sets")
    for cut_set in cut_sets:
        if not cut_set:
            raise ValueError("each cut set must contain at least one basic event")
        for event in cut_set:
            if event not in probs:
                raise ValueError("unknown basic event %r: no probability given" % (event,))
    for event, prob in probs.items():
        if not (0.0 < prob < 1.0):
            raise ValueError(
                "event probability must lie in (0, 1): %r = %r" % (event, prob)
            )


def _tree_events(cut_sets):
    """Return the sorted unique basic-event names that appear in cut_sets."""
    names = set()
    for cut_set in cut_sets:
        names.update(cut_set)
    return sorted(names)


def _require_contributing_event(cut_sets, probs, event):
    """Check an event is rated: known and present in at least one cut set."""
    if event not in probs:
        raise ValueError("unknown basic event %r: no probability given" % (event,))
    if not any(event in cut_set for cut_set in cut_sets):
        raise ValueError(
            "event %r appears in no cut set; its importance is undefined" % (event,)
        )


def _union_probability(cut_sets, probs):
    """Union probability of the cut sets by exact inclusion-exclusion."""
    n = len(cut_sets)
    total = 0.0
    for mask in range(1, 1 << n):
        product = 1.0
        terms = 0
        for index in range(n):
            if mask & (1 << index):
                terms += 1
                for event in cut_sets[index]:
                    product *= probs[event]
        if terms % 2 == 1:
            total += product
        else:
            total -= product
    return total


def _forced_probability(cut_sets, probs, event, forced_value):
    """Union probability with one event probability replaced by forced_value."""
    adjusted = dict(probs)
    adjusted[event] = forced_value
    return _union_probability(cut_sets, adjusted)


def top_event_probability(cut_sets, probs):
    """Return Q, the exact union probability of the cut sets."""
    _validate_inputs(cut_sets, probs)
    return _union_probability(cut_sets, probs)


def birnbaum_measure(cut_sets, probs, event):
    """Return the Birnbaum measure Q(q=1) - Q(q=0) for the event."""
    _validate_inputs(cut_sets, probs)
    _require_contributing_event(cut_sets, probs, event)
    prob_one = _forced_probability(cut_sets, probs, event, 1.0)
    prob_zero = _forced_probability(cut_sets, probs, event, 0.0)
    return prob_one - prob_zero


def fussell_vesely_measure(cut_sets, probs, event):
    """Return the Fussell-Vesely measure (Q - Q(q=0)) / Q for the event."""
    _validate_inputs(cut_sets, probs)
    _require_contributing_event(cut_sets, probs, event)
    top = _union_probability(cut_sets, probs)
    prob_zero = _forced_probability(cut_sets, probs, event, 0.0)
    return (top - prob_zero) / top


def risk_achievement_worth(cut_sets, probs, event):
    """Return the risk achievement worth Q(q=1) / Q for the event."""
    _validate_inputs(cut_sets, probs)
    _require_contributing_event(cut_sets, probs, event)
    top = _union_probability(cut_sets, probs)
    prob_one = _forced_probability(cut_sets, probs, event, 1.0)
    return prob_one / top


def risk_reduction_worth(cut_sets, probs, event):
    """Return the risk reduction worth Q / Q(q=0) for the event.

    When forcing the event false removes every failure path (Q(q=0) is
    zero, e.g. a lone single-event cut set), the worth is unbounded and
    reported as positive infinity.
    """
    _validate_inputs(cut_sets, probs)
    _require_contributing_event(cut_sets, probs, event)
    top = _union_probability(cut_sets, probs)
    prob_zero = _forced_probability(cut_sets, probs, event, 0.0)
    if prob_zero == 0.0:
        return math.inf
    return top / prob_zero


def importance_measures(cut_sets, probs):
    """Return {event: {birnbaum, fussell_vesely, raw, rrw}} for every event."""
    _validate_inputs(cut_sets, probs)
    measures = {}
    for event in _tree_events(cut_sets):
        measures[event] = {
            "birnbaum": birnbaum_measure(cut_sets, probs, event),
            "fussell_vesely": fussell_vesely_measure(cut_sets, probs, event),
            "raw": risk_achievement_worth(cut_sets, probs, event),
            "rrw": risk_reduction_worth(cut_sets, probs, event),
        }
    return measures


def rank_events(cut_sets, probs, measure="fussell_vesely"):
    """Return [(event, value)] sorted descending by the named measure.

    Ties break alphabetically by event name for determinism.
    """
    if measure not in MEASURE_KEYS:
        raise ValueError(
            "unknown measure %r; choose one of %s" % (measure, ", ".join(MEASURE_KEYS))
        )
    _validate_inputs(cut_sets, probs)
    if measure == "birnbaum":
        values = {e: birnbaum_measure(cut_sets, probs, e) for e in _tree_events(cut_sets)}
    elif measure == "fussell_vesely":
        values = {
            e: fussell_vesely_measure(cut_sets, probs, e) for e in _tree_events(cut_sets)
        }
    elif measure == "raw":
        values = {
            e: risk_achievement_worth(cut_sets, probs, e) for e in _tree_events(cut_sets)
        }
    else:
        values = {
            e: risk_reduction_worth(cut_sets, probs, e) for e in _tree_events(cut_sets)
        }
    ranked = sorted(values.items(), key=lambda pair: (-pair[1], pair[0]))
    return [(event, value) for event, value in ranked]


def dominant_contributors(cut_sets, probs, threshold=DEFAULT_DOMINANCE_THRESHOLD):
    """Return events whose Fussell-Vesely measure exceeds the threshold.

    Strictly greater than the threshold; sorted descending by measure
    with alphabetical tie-break.
    """
    _validate_inputs(cut_sets, probs)
    ranked = rank_events(cut_sets, probs, measure="fussell_vesely")
    return [event for event, value in ranked if value > threshold]
