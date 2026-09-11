#!/usr/bin/env python3
"""ECSS-E-ST-10C clause 5.3.3 + Annex L trade-off analysis
(paraphrase, not copy).

Common-knowledge summary (standards-map.yaml, ecss: gated false): the
system engineering process standard requires that a choice between
candidate solutions be made through a documented trade-off analysis --
a fixed set of evaluation criteria, each carrying a weight, is applied
to every candidate to produce a comparable score, and the outcome
(ranking, recommendation, and any sensitivity of that recommendation
to the weighting assumptions) is recorded in a trade-off report per
the Annex L layout. This module implements criteria/weight validation,
per-candidate scoring including mandatory pass/fail criteria,
competition-style ranking with tie handling, and a close-call
sensitivity flag; it does not define what the criteria or their
weights should be for a given project -- that is an engineering
judgment captured as input.
"""

MIN_SCORE = 0.0
MAX_SCORE = 10.0


def validate_criteria(criteria):
    """Validate a criteria mapping: {criterion_id: {"weight": float,
    "mandatory": bool (optional, default False), "pass_threshold":
    float (required if mandatory)}}. Raises ValueError for an empty
    mapping, a non-positive weight, or a mandatory criterion missing
    pass_threshold. Does not mutate criteria."""
    if not criteria:
        raise ValueError(
            "criteria must be a non-empty mapping of criterion_id to "
            "weight/definition"
        )
    for criterion_id, definition in criteria.items():
        weight = definition.get("weight")
        if weight is None or weight <= 0:
            raise ValueError(
                "criterion %r must have a positive weight" % (criterion_id,)
            )
        if definition.get("mandatory") and "pass_threshold" not in definition:
            raise ValueError(
                "mandatory criterion %r must define pass_threshold"
                % (criterion_id,)
            )


def normalized_weights(criteria):
    """Weight of each criterion as a fraction of the total weight, so
    the weighted scores of different trade-off studies are
    comparable. Raises ValueError via validate_criteria for invalid
    input."""
    validate_criteria(criteria)
    total_weight = sum(definition["weight"] for definition in criteria.values())
    return {
        criterion_id: definition["weight"] / total_weight
        for criterion_id, definition in criteria.items()
    }


def validate_score(criterion_id, score):
    """Raises ValueError when score falls outside the fixed
    [MIN_SCORE, MAX_SCORE] evaluation scale."""
    if not (MIN_SCORE <= score <= MAX_SCORE):
        raise ValueError(
            "score %r for criterion %r is outside the [%s, %s] scale"
            % (score, criterion_id, MIN_SCORE, MAX_SCORE)
        )


def validate_candidate_scores(candidate_id, scores, criteria):
    """Raises ValueError when a candidate's scores do not cover
    exactly the criteria set (missing or extra criterion_id) or when
    any score is outside the evaluation scale."""
    criterion_ids = set(criteria)
    scored_ids = set(scores)
    missing = criterion_ids - scored_ids
    if missing:
        raise ValueError(
            "candidate %r is missing scores for criteria: %s"
            % (candidate_id, sorted(missing))
        )
    extra = scored_ids - criterion_ids
    if extra:
        raise ValueError(
            "candidate %r has scores for unrecognized criteria: %s"
            % (candidate_id, sorted(extra))
        )
    for criterion_id, score in scores.items():
        validate_score(criterion_id, score)


def mandatory_failures(scores, criteria):
    """List of mandatory criterion_ids on which a candidate's score
    falls below the criterion's pass_threshold. An empty list means
    the candidate clears every mandatory (pass/fail) criterion and is
    eligible for weighted scoring."""
    failures = []
    for criterion_id, definition in criteria.items():
        if definition.get("mandatory") and scores[criterion_id] < definition["pass_threshold"]:
            failures.append(criterion_id)
    return failures


def weighted_score(scores, weights):
    """Sum of normalized_weight x score across every criterion in
    weights. Assumes scores already covers the same criteria set
    (see validate_candidate_scores)."""
    return sum(weights[criterion_id] * scores[criterion_id] for criterion_id in weights)


def rank_candidates(candidates, criteria):
    """Full clause 5.3.3 scoring pass over every candidate.

    candidates: {candidate_id: {criterion_id: score, ...}}. criteria:
    see validate_criteria. Raises ValueError for an empty candidates
    mapping or via the criteria/score validation helpers.

    A candidate that fails a mandatory criterion is disqualified (no
    weighted_score, rank None) rather than scored -- a mandatory
    criterion is a pass/fail gate, not something a high score on other
    criteria can outweigh. Qualified candidates are ranked by
    descending weighted_score using standard competition ranking
    (tied scores share a rank; the next distinct score resumes at its
    1-based position). Returns a list: qualified candidates first
    (best rank first), then disqualified candidates."""
    if not candidates:
        raise ValueError(
            "candidates must be a non-empty mapping of candidate_id to scores"
        )
    weights = normalized_weights(criteria)
    for candidate_id, scores in candidates.items():
        validate_candidate_scores(candidate_id, scores, criteria)

    entries = []
    for candidate_id, scores in candidates.items():
        failures = mandatory_failures(scores, criteria)
        if failures:
            entries.append(
                {
                    "candidate_id": candidate_id,
                    "disqualified": True,
                    "mandatory_failures": failures,
                    "weighted_score": None,
                    "rank": None,
                }
            )
        else:
            entries.append(
                {
                    "candidate_id": candidate_id,
                    "disqualified": False,
                    "mandatory_failures": [],
                    "weighted_score": weighted_score(scores, weights),
                    "rank": None,
                }
            )

    qualified = sorted(
        (entry for entry in entries if not entry["disqualified"]),
        key=lambda entry: entry["weighted_score"],
        reverse=True,
    )
    disqualified = [entry for entry in entries if entry["disqualified"]]

    current_rank = 0
    previous_score = None
    for index, entry in enumerate(qualified):
        if entry["weighted_score"] != previous_score:
            current_rank = index + 1
            previous_score = entry["weighted_score"]
        entry["rank"] = current_rank

    return qualified + disqualified


def is_close_call(ranked, margin_fraction=0.05):
    """True when the trade-off outcome is sensitive to the input
    weights/scores rather than a clear-cut recommendation: the top two
    qualified candidates are tied, or the leader's weighted_score is
    within margin_fraction of the runner-up's. Annex L expects a
    trade-off report to flag this rather than present a razor-thin
    margin as a settled decision. False when fewer than two candidates
    qualify. Raises ValueError for margin_fraction outside (0, 1)."""
    if not (0.0 < margin_fraction < 1.0):
        raise ValueError("margin_fraction must be between 0 and 1")
    qualified = [entry for entry in ranked if not entry["disqualified"]]
    if len(qualified) < 2:
        return False
    leader, runner_up = qualified[0], qualified[1]
    if leader["rank"] == runner_up["rank"]:
        return True
    if leader["weighted_score"] == 0:
        return False
    spread = leader["weighted_score"] - runner_up["weighted_score"]
    return (spread / leader["weighted_score"]) < margin_fraction


def tradeoff_report(criteria, candidates, margin_fraction=0.05):
    """Full trade-off report for one Annex L study: ranks every
    candidate (see rank_candidates), determines a winner only when
    exactly one candidate holds rank 1 and the outcome is not a close
    call, and always reports the close-call sensitivity flag alongside
    the ranking so a tied or marginal result is never silently
    resolved into a false recommendation. Returns {"ranking": [...],
    "winner": candidate_id | None, "close_call": bool,
    "all_disqualified": bool}."""
    ranked = rank_candidates(candidates, criteria)
    qualified = [entry for entry in ranked if not entry["disqualified"]]
    close_call = is_close_call(ranked, margin_fraction)

    winner = None
    if qualified and not close_call:
        leaders = [entry for entry in qualified if entry["rank"] == 1]
        if len(leaders) == 1:
            winner = leaders[0]["candidate_id"]

    return {
        "ranking": ranked,
        "winner": winner,
        "close_call": close_call,
        "all_disqualified": len(qualified) == 0,
    }
