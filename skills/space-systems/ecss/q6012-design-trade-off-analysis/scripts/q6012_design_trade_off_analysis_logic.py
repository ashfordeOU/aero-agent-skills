#!/usr/bin/env python3
"""Architecture trade-off across performance, yield, size and power.

Anchor: ECSS-Q-ST-60-12C clause 7.1.4 (design trade-off -- weighing the
performance, yield, die size and dc power consequences of the candidate
microwave circuit architectures before one is settled on). Paraphrased into an
implementable procedure; no standard text is reproduced.

Procedure implemented here
--------------------------
1. Validate the four trade criteria and their directions: performance and
   yield are better when larger, die area and dc power are better when
   smaller. Each criterion carries a requirement threshold (the value below
   which a candidate is not offerable at all) and a goal value (the value at
   which further improvement buys nothing).
2. Eliminate the candidates that miss a threshold, naming every criterion
   missed rather than stopping at the first, so a near miss on one axis is
   visible as such and the architecture can be reworked.
3. Normalise each surviving candidate's metrics onto a common zero-to-one
   utility between threshold and goal, clamped at both ends so an
   over-delivery on one axis cannot buy a shortfall on another.
4. Weight the utilities and rank. Ties inside a named tolerance are reported
   as ties rather than resolved by float noise, and the ordering falls back to
   the candidate name so a re-run gives the same answer.
5. Perturb each weight and re-rank. A preference that flips under a small
   weight change is a finding: the trade did not actually settle the
   architecture, it settled the weighting.
"""

import math

__all__ = [
    "CRITERIA",
    "HIGHER_IS_BETTER",
    "WEIGHT_SUM_TOLERANCE",
    "SCORE_TIE_TOLERANCE",
    "DEFAULT_WEIGHT_PERTURBATION",
    "validate_weights",
    "validate_bounds",
    "normalise_metric",
    "threshold_violations",
    "candidate_utilities",
    "score_candidate",
    "rank_candidates",
    "weight_sensitivity",
    "select_architecture",
]

# The four axes clause 7.1.4 puts against each other.
CRITERIA = ("performance", "yield", "size", "power")

# Direction of goodness per criterion. Size is die area and power is dc
# consumption, so both improve downwards.
HIGHER_IS_BETTER = {
    "performance": True,
    "yield": True,
    "size": False,
    "power": False,
}

# A weight set is a partition of one; hand-entered weights land a few ULP off.
WEIGHT_SUM_TOLERANCE = 1e-9

# Two weighted scores this close are a tie, not a preference.
SCORE_TIE_TOLERANCE = 1e-9

# How far each weight is moved when the ranking is tested for robustness.
DEFAULT_WEIGHT_PERTURBATION = 0.05


def _require_real(value, label, positive=False):
    """Return value as a finite float, raising on anything that is not one."""
    if not isinstance(value, (int, float)) or isinstance(value, bool):
        raise ValueError("%s must be a real number, got %r" % (label, value))
    out = float(value)
    if not math.isfinite(out):
        raise ValueError("%s must be finite, got %r" % (label, value))
    if positive and out <= 0.0:
        raise ValueError("%s must be positive, got %r" % (label, value))
    return out


def validate_weights(weights):
    """Return the criterion weights normalised, raising on a malformed set."""
    if not isinstance(weights, dict):
        raise ValueError("weights must be a mapping of criterion to weight")
    missing = [c for c in CRITERIA if c not in weights]
    if missing:
        raise ValueError("weights missing criteria: %s" % ", ".join(missing))
    extra = [k for k in weights if k not in CRITERIA]
    if extra:
        raise ValueError("weights carry unknown criteria: %s" % ", ".join(sorted(extra)))
    out = {}
    for criterion in CRITERIA:
        value = _require_real(weights[criterion], "weight for %s" % criterion)
        if value < 0.0:
            raise ValueError("weight for %s must not be negative" % criterion)
        out[criterion] = value
    total = sum(out.values())
    if total <= 0.0:
        raise ValueError("weights must not all be zero")
    if not math.isclose(total, 1.0, rel_tol=0.0, abs_tol=WEIGHT_SUM_TOLERANCE):
        raise ValueError(
            "weights sum to %.12g; a trade weighting must partition one" % total
        )
    return out


def validate_bounds(thresholds, goals):
    """Return the threshold/goal pair per criterion, checking their direction."""
    for label, table in (("thresholds", thresholds), ("goals", goals)):
        if not isinstance(table, dict):
            raise ValueError("%s must be a mapping of criterion to value" % label)
        missing = [c for c in CRITERIA if c not in table]
        if missing:
            raise ValueError("%s missing criteria: %s" % (label, ", ".join(missing)))
    bounds = {}
    for criterion in CRITERIA:
        threshold = _require_real(thresholds[criterion], "threshold for %s" % criterion)
        goal = _require_real(goals[criterion], "goal for %s" % criterion)
        if HIGHER_IS_BETTER[criterion]:
            if goal <= threshold:
                raise ValueError(
                    "goal for %s must exceed its threshold; %g does not exceed %g"
                    % (criterion, goal, threshold)
                )
        elif goal >= threshold:
            raise ValueError(
                "goal for %s must be below its threshold; %g is not below %g"
                % (criterion, goal, threshold)
            )
        bounds[criterion] = (threshold, goal)
    return bounds


def normalise_metric(value, threshold, goal, higher_is_better):
    """Return the clamped zero-to-one utility of one metric between its bounds."""
    metric = _require_real(value, "metric value")
    low = _require_real(threshold, "threshold")
    high = _require_real(goal, "goal")
    if not isinstance(higher_is_better, bool):
        raise ValueError("higher_is_better must be a boolean")
    span = high - low
    if span == 0.0:
        raise ValueError("threshold and goal must differ")
    if higher_is_better and span <= 0.0:
        raise ValueError("a higher-is-better goal must sit above its threshold")
    if not higher_is_better and span >= 0.0:
        raise ValueError("a lower-is-better goal must sit below its threshold")
    utility = (metric - low) / span
    return min(1.0, max(0.0, utility))


def _validate_candidate(candidate):
    """Return one candidate normalised to a name plus its four metrics."""
    if not isinstance(candidate, dict):
        raise ValueError("candidate must be a mapping, got %r" % (candidate,))
    name = candidate.get("name")
    if not isinstance(name, str) or not name.strip():
        raise ValueError("candidate needs a non-empty string 'name'")
    metrics = {}
    for criterion in CRITERIA:
        if criterion not in candidate:
            raise ValueError(
                "candidate %r is missing the %r metric" % (name.strip(), criterion)
            )
        metrics[criterion] = _require_real(
            candidate[criterion], "%s of candidate %r" % (criterion, name.strip())
        )
    return name.strip(), metrics


def threshold_violations(candidate, bounds):
    """Return the criteria a candidate fails its requirement threshold on."""
    _, metrics = _validate_candidate(candidate)
    violated = []
    for criterion in CRITERIA:
        threshold = bounds[criterion][0]
        value = metrics[criterion]
        if HIGHER_IS_BETTER[criterion]:
            if value < threshold - SCORE_TIE_TOLERANCE:
                violated.append(criterion)
        elif value > threshold + SCORE_TIE_TOLERANCE:
            violated.append(criterion)
    return violated


def candidate_utilities(candidate, bounds):
    """Return the per-criterion utilities of one candidate."""
    _, metrics = _validate_candidate(candidate)
    return {
        criterion: normalise_metric(
            metrics[criterion],
            bounds[criterion][0],
            bounds[criterion][1],
            HIGHER_IS_BETTER[criterion],
        )
        for criterion in CRITERIA
    }


def score_candidate(candidate, bounds, weights):
    """Return the weighted trade score of one candidate."""
    weight_set = validate_weights(weights)
    utilities = candidate_utilities(candidate, bounds)
    return sum(weight_set[c] * utilities[c] for c in CRITERIA)


def rank_candidates(candidates, bounds, weights):
    """Return the feasible candidates ordered best first, ties by name."""
    if not isinstance(candidates, (list, tuple)) or not candidates:
        raise ValueError("candidates must be a non-empty sequence")
    weight_set = validate_weights(weights)
    seen = set()
    ranked = []
    for candidate in candidates:
        name, _ = _validate_candidate(candidate)
        if name in seen:
            raise ValueError("candidate %r appears more than once" % name)
        seen.add(name)
        if threshold_violations(candidate, bounds):
            continue
        ranked.append(
            {
                "name": name,
                "score": score_candidate(candidate, bounds, weight_set),
                "utilities": candidate_utilities(candidate, bounds),
            }
        )
    ranked.sort(key=lambda row: (-row["score"], row["name"]))
    return ranked


def weight_sensitivity(candidates, bounds, weights, perturbation=None):
    """Return the weight moves that change which architecture leads."""
    weight_set = validate_weights(weights)
    delta = (
        DEFAULT_WEIGHT_PERTURBATION
        if perturbation is None
        else _require_real(perturbation, "perturbation", positive=True)
    )
    if delta >= 1.0:
        raise ValueError("perturbation must be below one, got %r" % (perturbation,))
    baseline = rank_candidates(candidates, bounds, weight_set)
    if not baseline:
        return []
    leader = baseline[0]["name"]
    flips = []
    for criterion in CRITERIA:
        for sign in (1.0, -1.0):
            moved = weight_set[criterion] + sign * delta
            if moved < 0.0 or moved > 1.0:
                continue
            remainder = 1.0 - moved
            others = [c for c in CRITERIA if c != criterion]
            other_total = sum(weight_set[c] for c in others)
            if other_total <= 0.0:
                continue
            trial = {criterion: moved}
            for other in others:
                trial[other] = weight_set[other] / other_total * remainder
            total = sum(trial.values())
            trial = {k: v / total for k, v in trial.items()}
            trial_rank = rank_candidates(candidates, bounds, trial)
            if trial_rank and trial_rank[0]["name"] != leader:
                flips.append(
                    {
                        "criterion": criterion,
                        "direction": "up" if sign > 0 else "down",
                        "new_leader": trial_rank[0]["name"],
                    }
                )
    return flips


def select_architecture(spec):
    """Run the clause 7.1.4 architecture trade-off and return the preference.

    spec keys: candidates, thresholds, goals, weights, optional perturbation.
    """
    if not isinstance(spec, dict):
        raise ValueError("spec must be a mapping")
    for key in ("candidates", "thresholds", "goals", "weights"):
        if key not in spec:
            raise ValueError("spec missing required key '%s'" % key)
    bounds = validate_bounds(spec["thresholds"], spec["goals"])
    weight_set = validate_weights(spec["weights"])
    candidates = spec["candidates"]
    if not isinstance(candidates, (list, tuple)) or not candidates:
        raise ValueError("spec['candidates'] must be a non-empty sequence")

    eliminated = []
    for candidate in candidates:
        name, _ = _validate_candidate(candidate)
        violated = threshold_violations(candidate, bounds)
        if violated:
            eliminated.append({"name": name, "violated": violated})

    ranked = rank_candidates(candidates, bounds, weight_set)
    findings = []
    for row in eliminated:
        findings.append(
            "architecture %r misses its requirement threshold on %s"
            % (row["name"], ", ".join(row["violated"]))
        )
    if not ranked:
        findings.append(
            "no candidate architecture meets every requirement threshold; the "
            "trade cannot settle an architecture until one does"
        )
        return {
            "preferred": None,
            "ranking": [],
            "eliminated": eliminated,
            "tied_with_leader": [],
            "sensitivity": [],
            "decision_supported": False,
            "findings": findings,
        }

    leader = ranked[0]
    tied = [
        row["name"]
        for row in ranked[1:]
        if math.isclose(
            row["score"], leader["score"], rel_tol=0.0, abs_tol=SCORE_TIE_TOLERANCE
        )
    ]
    if tied:
        findings.append(
            "architecture %r ties with %s on the weighted score; the trade does "
            "not separate them" % (leader["name"], ", ".join(tied))
        )
    flips = weight_sensitivity(
        candidates, bounds, weight_set, spec.get("perturbation")
    )
    for flip in flips:
        findings.append(
            "moving the %s weight %s by the perturbation hands the lead to %r; "
            "the preference follows the weighting, not the architecture"
            % (flip["criterion"], flip["direction"], flip["new_leader"])
        )
    return {
        "preferred": leader["name"],
        "ranking": ranked,
        "eliminated": eliminated,
        "tied_with_leader": tied,
        "sensitivity": flips,
        "decision_supported": not tied and not flips,
        "findings": findings,
    }
