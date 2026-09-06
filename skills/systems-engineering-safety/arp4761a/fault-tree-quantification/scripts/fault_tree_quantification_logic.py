#!/usr/bin/env python3
"""Fault-tree top-event quantification logic per ARP4761A (summary, not copy).

Common-knowledge summary (standards-map.yaml, arp4761a: gated, reference
only): a fault tree top event is the union of its minimal cut sets, where
each cut set is a set of independent basic events that jointly force the
top event. This module quantifies that union from the cut sets and the
basic-event probabilities alone; it never derives cut sets from gate
structure (that is the fta-fmea leaf) and never ranks individual basic
events (that is the fault-tree-importance-measures leaf).

Four quantities are produced:

- rare_event_probability: the rare-event approximation Q_re, the sum of
  the cut-set probabilities (first-order union approximation).
- min_cut_upper_bound: the Esary-Proschan min-cut upper bound Q_ep =
  1 - product over the cut sets of (1 - cut-set probability).
- exact_top_probability: the exact union probability by inclusion-exclusion
  over the 2^n - 1 non-empty subsets of the cut sets, guarded at
  EXACT_IE_MAX_CUT_SETS = 12 cut sets.
- truncate_cut_sets and rank_cut_sets: the analyst-facing cut-set mass
  picture (probability-threshold truncation with the retained probability
  share, and per-cut-set probability-share ranking).

Basic events are independent; a cut set occurs when every basic event in
it fails, at probability equal to the product of its member probabilities.
Deterministic pure stdlib only, no RNG. Probabilities are floats strictly
inside (0, 1) for every event and every cut set is a non-empty set of
event names.
"""

EXACT_IE_MAX_CUT_SETS = 12


def _validate(cut_sets, probs):
    """Common input checks for every entry point: reject an empty cut-set
    list, an empty or non-set cut-set entry, an event name without a
    probability entry, and a probability outside (0, 1)."""
    if not cut_sets:
        raise ValueError("cut_sets must not be empty")
    for cut_set in cut_sets:
        if not isinstance(cut_set, (set, frozenset)) or not cut_set:
            raise ValueError(
                "each cut set must be a non-empty set of basic-event names"
            )
        for name in cut_set:
            if name not in probs:
                raise ValueError(
                    "no probability entry for basic event %r" % (name,)
                )
            p = probs[name]
            if not 0.0 < p < 1.0:
                raise ValueError(
                    "probability of basic event %r must lie strictly "
                    "inside (0, 1)" % (name,)
                )


def _cut_set_probability(cut_set, probs):
    """Probability of one cut set: the product of its member basic-event
    probabilities (independent events, all must fail)."""
    product = 1.0
    for name in cut_set:
        product *= probs[name]
    return product


def rare_event_probability(cut_sets, probs):
    """Rare-event approximation Q_re of the top-event probability: the sum
    of the cut-set probabilities (first-order union approximation, exact
    only for a single cut set)."""
    _validate(cut_sets, probs)
    return sum(_cut_set_probability(cut_set, probs) for cut_set in cut_sets)


def min_cut_upper_bound(cut_sets, probs):
    """Esary-Proschan min-cut upper bound Q_ep on the exact top
    probability: 1 - product over the cut sets of (1 - cut-set
    probability). Upper bound for a coherent tree with independent basic
    events. In real arithmetic Q_ep <= Q_re always; the float survival
    product sits near 1.0, so compare with a 1e-15 absolute tolerance."""
    _validate(cut_sets, probs)
    survival = 1.0
    for cut_set in cut_sets:
        survival *= 1.0 - _cut_set_probability(cut_set, probs)
    return 1.0 - survival


def exact_top_probability(cut_sets, probs):
    """Exact top-event probability by inclusion-exclusion over the union of
    the cut events: for each non-empty subset of the cut sets (mask 1 to
    2**n - 1) add (-1)**(k+1) times the product of the basic-event
    probabilities over the union of the k selected cuts. Independent basic
    events make the intersection product exactly that union product.
    Raises ValueError above EXACT_IE_MAX_CUT_SETS cut sets."""
    _validate(cut_sets, probs)
    n = len(cut_sets)
    if n > EXACT_IE_MAX_CUT_SETS:
        raise ValueError(
            "exact inclusion-exclusion intractable at %d cut sets "
            "(max %d): use rare_event_probability or "
            "min_cut_upper_bound" % (n, EXACT_IE_MAX_CUT_SETS)
        )
    total = 0.0
    for mask in range(1, 1 << n):
        union = set()
        selected = 0
        for idx in range(n):
            if mask & (1 << idx):
                union |= cut_sets[idx]
                selected += 1
        term = 1.0
        for name in union:
            term *= probs[name]
        if selected % 2:
            total += term
        else:
            total -= term
    return total


def truncate_cut_sets(cut_sets, probs, threshold):
    """Truncate the cut sets below an analyst probability threshold: keep
    every cut set whose probability is at least the threshold (drop is
    strict, probability < threshold), and report the retained probability
    share, the sum of the retained cut-set probabilities divided by the
    sum of all cut-set probabilities. An all-dropped call returns an empty
    list with share 0.0; a threshold that drops nothing returns the full
    input with share 1.0. Threshold must lie in (0, 1]."""
    _validate(cut_sets, probs)
    if not 0.0 < threshold <= 1.0:
        raise ValueError("threshold must lie in (0, 1]")
    masses = [_cut_set_probability(cut_set, probs) for cut_set in cut_sets]
    total_mass = sum(masses)
    kept = [
        cut_set
        for cut_set, mass in zip(cut_sets, masses)
        if mass >= threshold
    ]
    kept_mass = sum(
        mass for mass in masses if mass >= threshold
    )
    share = kept_mass / total_mass if total_mass > 0.0 else 0.0
    return {"cut_sets": kept, "retained_probability_share": share}


def rank_cut_sets(cut_sets, probs):
    """Rank the cut sets by per-cut-set probability share: each entry is a
    dict with the keys cut_set, probability and share (cut-set probability
    divided by the sum of all cut-set probabilities), sorted descending by
    probability with a stable input-order tie-break; shares sum to 1.0."""
    _validate(cut_sets, probs)
    masses = [_cut_set_probability(cut_set, probs) for cut_set in cut_sets]
    total_mass = sum(masses)
    ranked = [
        {
            "cut_set": cut_set,
            "probability": mass,
            "share": mass / total_mass,
        }
        for cut_set, mass in zip(cut_sets, masses)
    ]
    ranked.sort(key=lambda entry: entry["probability"], reverse=True)
    return ranked
