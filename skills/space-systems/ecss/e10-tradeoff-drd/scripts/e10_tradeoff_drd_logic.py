"""ECSS-E-ST-10C Annex L trade-off report DRD (paraphrase, not copy).

Common-knowledge summary (standards-map.yaml, ecss: gated false): the Annex L
Document Requirements Definition governs a trade-off report: the criteria the
options are judged against and their relative weights, the options themselves,
the score of every option against every criterion, the resulting ranking, and
a sensitivity statement showing whether the recommendation survives a
plausible change in the weighting. A trade-off needs at least two options to
be a trade at all; weights must form a normalized set; every option must carry
a score for every criterion, because a missing score silently scores zero and
demotes an option that was never assessed.
"""

SCORE_MIN = 0.0
SCORE_MAX = 10.0
WEIGHT_SUM_TOLERANCE = 1e-6
DEFAULT_SENSITIVITY_DELTA = 0.10
DEFAULT_MARGIN_FRACTION = 0.05


def validate_weights(criteria):
    """Return the criteria weight mapping if it is a usable weighting.

    criteria: {criterion_id: weight}. Raises ValueError for an empty set, a
    negative weight, or weights that do not sum to 1 within tolerance -- an
    unnormalized set makes weighted scores incomparable between reports.
    """
    if not criteria:
        raise ValueError("trade-off needs at least one criterion")
    for cid, w in criteria.items():
        if w < 0:
            raise ValueError("negative weight for criterion %s" % cid)
    total = sum(criteria.values())
    if abs(total - 1.0) > WEIGHT_SUM_TOLERANCE:
        raise ValueError("criterion weights sum to %r, must sum to 1.0" % total)
    return criteria


def zero_weight_criteria(criteria):
    """Criteria carrying zero weight, sorted. They appear in the report but
    cannot affect the outcome, so they are surfaced rather than silently
    carried -- usually a weighting that was never filled in."""
    return sorted(cid for cid, w in criteria.items() if w == 0)


def validate_score(value):
    """Return value if it is a score on the report's scale, else raise."""
    if not isinstance(value, (int, float)) or isinstance(value, bool):
        raise ValueError("score must be numeric, got %r" % (value,))
    if not (SCORE_MIN <= value <= SCORE_MAX):
        raise ValueError("score %r outside %r..%r" % (value, SCORE_MIN, SCORE_MAX))
    return float(value)


def missing_scores(criteria, options):
    """(option_id, criterion_id) pairs with no score on record, in input order.

    Reported rather than defaulted: a missing score treated as zero quietly
    ranks an unassessed option last, which looks like a decision.
    """
    out = []
    for opt in options:
        scores = opt.get("scores", {})
        for cid in criteria:
            if cid not in scores:
                out.append((opt["option_id"], cid))
    return out


def weighted_score(criteria, scores):
    """Weighted total for one option. Raises ValueError if a criterion has no
    score -- the caller must resolve the gap, not average around it."""
    total = 0.0
    for cid, w in criteria.items():
        if cid not in scores:
            raise ValueError("no score for criterion %s" % cid)
        total += w * validate_score(scores[cid])
    return total


def rank_options(criteria, options):
    """[(option_id, weighted_score)] sorted by score descending, then by
    option_id ascending so a tie is broken deterministically rather than by
    input order."""
    scored = [(o["option_id"], weighted_score(criteria, o.get("scores", {})))
              for o in options]
    return sorted(scored, key=lambda p: (-p[1], p[0]))


def decision_margin(ranking):
    """Score gap between the top option and the runner-up. Raises ValueError
    for a ranking with fewer than two options -- there is no margin without a
    comparison."""
    if len(ranking) < 2:
        raise ValueError("margin needs at least two ranked options")
    return ranking[0][1] - ranking[1][1]


def weight_sensitivity(criteria, options, delta=DEFAULT_SENSITIVITY_DELTA):
    """Criteria whose weight, shifted by +/- delta and renormalized, changes
    the winner. Sorted. An empty list means the recommendation is robust to a
    delta-sized change in any single weight.

    Raises ValueError for a delta outside (0, 1).
    """
    if not (0 < delta < 1):
        raise ValueError("delta must lie in (0, 1), got %r" % (delta,))
    base = rank_options(criteria, options)
    if not base:
        return []
    winner = base[0][0]
    flips = set()
    for cid in criteria:
        for signed in (delta, -delta):
            trial = dict(criteria)
            trial[cid] = max(0.0, trial[cid] + signed)
            total = sum(trial.values())
            if total <= 0:
                continue
            trial = {k: v / total for k, v in trial.items()}
            if rank_options(trial, options)[0][0] != winner:
                flips.add(cid)
    return sorted(flips)


def tradeoff_review(report, delta=DEFAULT_SENSITIVITY_DELTA,
                    margin_fraction=DEFAULT_MARGIN_FRACTION):
    """Full Annex L trade-off report review.

    report: {"criteria": {criterion_id: weight},
             "options": [{"option_id": str, "scores": {criterion_id: float}}]}

    Returns {"ranking", "winner", "margin", "sensitive_criteria", "findings"}.
    Raises ValueError for an unusable weighting, a duplicate option id, or a
    score outside the scale.
    """
    criteria = validate_weights(dict(report.get("criteria", {})))
    options = list(report.get("options", []))
    seen = set()
    for o in options:
        oid = o.get("option_id")
        if not oid:
            raise ValueError("option with no option_id")
        if oid in seen:
            raise ValueError("duplicate option_id: %s" % oid)
        seen.add(oid)

    findings = []
    for cid in zero_weight_criteria(criteria):
        findings.append({"criterion_id": cid, "issue": "zero_weight_criterion"})
    gaps = missing_scores(criteria, options)
    for oid, cid in gaps:
        findings.append({"option_id": oid, "criterion_id": cid,
                         "issue": "missing_score"})
    if len(options) < 2:
        findings.append({"issue": "not_a_trade_off", "option_count": len(options)})
    if gaps or len(options) < 2:
        return {"ranking": [], "winner": None, "margin": None,
                "sensitive_criteria": [], "findings": findings}

    ranking = rank_options(criteria, options)
    margin = decision_margin(ranking)
    if margin <= margin_fraction * SCORE_MAX:
        findings.append({"issue": "indecisive_margin", "margin": margin})
    sensitive = weight_sensitivity(criteria, options, delta)
    for cid in sensitive:
        findings.append({"criterion_id": cid, "issue": "winner_sensitive_to_weight"})
    return {"ranking": ranking, "winner": ranking[0][0], "margin": margin,
            "sensitive_criteria": sensitive, "findings": findings}


def is_tradeoff_conclusive(review):
    """True when the report reaches a ranked recommendation with no findings."""
    return review["winner"] is not None and not review["findings"]
