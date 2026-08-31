#!/usr/bin/env python3
"""Trade study and Pugh matrix analysis logic (paraphrase).

Common decision-analysis methodology (standards-map.yaml, arp4754a:
gated, reference-only): alternative concepts for an aerospace system
or subsystem are evaluated against weighted decision criteria, the
candidates are compared with a Pugh matrix against a baseline
concept, the ranking is checked for sensitivity to the weights, the
selection margin between the best and the runner-up is judged, and
the rationale traces to requirement ids. ARP4754A sets the
development-planning context: alternative concepts are evaluated and
the chosen concept is justified as part of the development plan.
"""

WEIGHT_TOLERANCE = 1e-9
PUGH_MARKS = (-1, 0, 1)
DEFAULT_MARGIN_THRESHOLD = 0.05


def weighted_score(weights, scores):
    """Weighted score sum(w_i * s_i) with weights validated to sum 1.0.

    Raises ValueError on empty lists, a length mismatch, or weights
    whose sum deviates from 1.0 by more than WEIGHT_TOLERANCE.
    """
    if not weights or not scores:
        raise ValueError("weights and scores must be non-empty lists")
    if len(weights) != len(scores):
        raise ValueError(
            "weights and scores length mismatch: %d vs %d"
            % (len(weights), len(scores))
        )
    total = sum(weights)
    if abs(total - 1.0) > WEIGHT_TOLERANCE:
        raise ValueError("weights must sum to 1.0 (got %r)" % total)
    return sum(w * s for w, s in zip(weights, scores))


def _validate_pugh_matrix(pugh_matrix, baseline_index):
    if not pugh_matrix:
        raise ValueError("pugh matrix must be non-empty (at least one criterion row)")
    n_alt = len(pugh_matrix[0])
    for row in pugh_matrix:
        if not row:
            raise ValueError("pugh matrix rows must be non-empty")
        if len(row) != n_alt:
            raise ValueError(
                "pugh matrix rows must all have the same width (got %d and %d)"
                % (n_alt, len(row))
            )
        for cell in row:
            if cell not in PUGH_MARKS:
                raise ValueError("pugh matrix cells must be in {-1, 0, 1} (got %r)" % cell)
    if not (0 <= baseline_index < n_alt):
        raise ValueError(
            "baseline_index %d out of range for %d alternatives"
            % (baseline_index, n_alt)
        )
    return n_alt


def pugh_matrix_verdict(pugh_matrix, baseline_index=0):
    """Rank alternatives by net score relative to the baseline concept.

    Each cell is +1 (better), 0 (same), or -1 (worse) than the
    baseline. Net score of an alternative = sum over rows of
    (cell - baseline cell), so the baseline nets 0 by definition.
    Returns a list of verdict dicts sorted by net descending, then by
    alternative index ascending for determinism:
    {"index", "net", "plus", "minus"}.
    """
    n_alt = _validate_pugh_matrix(pugh_matrix, baseline_index)
    verdicts = []
    for j in range(n_alt):
        net = sum(row[j] - row[baseline_index] for row in pugh_matrix)
        plus = sum(1 for row in pugh_matrix if row[j] == 1)
        minus = sum(1 for row in pugh_matrix if row[j] == -1)
        verdicts.append({"index": j, "net": net, "plus": plus, "minus": minus})
    verdicts.sort(key=lambda v: (-v["net"], v["index"]))
    return verdicts


def _renormalize(weights, criterion, perturbation):
    """Weights with weight[criterion] raised by perturbation, the rest
    scaled proportionally so the set still sums to 1.0."""
    w = list(weights)
    if not (0.0 <= perturbation <= 1.0):
        raise ValueError("perturbation must be in [0.0, 1.0] (got %r)" % perturbation)
    if not (0 <= criterion < len(w)):
        raise ValueError("criterion index %d out of range" % criterion)
    new_i = w[criterion] + perturbation
    if new_i > 1.0:
        raise ValueError(
            "perturbation %r pushes weight %d above 1.0" % (perturbation, criterion)
        )
    others = sum(w) - w[criterion]
    if others == 0.0:
        raise ValueError("cannot renormalize: all weight sits on criterion %d" % criterion)
    out = []
    for i, wi in enumerate(w):
        if i == criterion:
            out.append(new_i)
        else:
            out.append(wi * (1.0 - new_i) / others)
    return out


def sensitivity_ranking(weights, scores, perturbation):
    """Re-rank the alternatives after perturbing each weight in turn.

    scores is a list of per-alternative score lists aligned with
    weights. Returns {"base": {...}, "scenarios": [...]} where each
    scenario perturbs one criterion weight upward, renormalizes, and
    records the new ranking, winner, and whether the winner changed
    relative to the base ranking.
    """
    if not scores:
        raise ValueError("scores must be non-empty")
    n_crit = len(weights)
    base_scores = [weighted_score(weights, s) for s in scores]
    base_ranking = _rank(base_scores)
    base_winner = base_ranking[0]
    scenarios = []
    for i in range(n_crit):
        w2 = _renormalize(weights, i, perturbation)
        s2 = [weighted_score(w2, s) for s in scores]
        ranking = _rank(s2)
        winner = ranking[0]
        scenarios.append(
            {
                "criterion": i,
                "weights": w2,
                "ranking": ranking,
                "winner": winner,
                "changed": winner != base_winner,
            }
        )
    return {"base": {"ranking": base_ranking, "winner": base_winner}, "scenarios": scenarios}


def _rank(scores):
    """Alternative indices sorted by score descending, index ascending."""
    return [i for i, _ in sorted(enumerate(scores), key=lambda t: (-t[1], t[0]))]


def selection_verdict(best_score, runner_up_score, margin_threshold=DEFAULT_MARGIN_THRESHOLD):
    """Selection decision with margin and tie handling.

    Returns {"winner", "margin", "tie", "confident"}: a tie when the
    margin is at or below the numerical tolerance; otherwise the best
    alternative wins, and the decision is confident only when the
    margin reaches the threshold.
    """
    margin = best_score - runner_up_score
    tie = margin <= WEIGHT_TOLERANCE
    if tie:
        winner = "tie"
    else:
        winner = "best"
    return {
        "winner": winner,
        "margin": margin,
        "tie": tie,
        "confident": (not tie) and margin >= margin_threshold,
    }


def traceability_check(alternatives, requirement_ids):
    """Verdict on requirement traceability of the trade study.

    alternatives is a list of dicts {"id", "requirements": [...]}.
    The check passes only when every alternative cites at least one
    requirement and every requirement in requirement_ids is covered
    by at least one alternative.
    """
    missing_alt = [
        alt["id"] for alt in alternatives if not alt.get("requirements")
    ]
    cited = set()
    for alt in alternatives:
        cited.update(alt.get("requirements") or [])
    uncovered = [r for r in requirement_ids if r not in cited]
    return {
        "ok": (not missing_alt) and (not uncovered),
        "alternatives_missing": missing_alt,
        "uncovered_requirements": uncovered,
    }
