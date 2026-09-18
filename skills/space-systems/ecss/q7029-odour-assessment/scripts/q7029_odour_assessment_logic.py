"""Offgassing odour acceptability from a trained sensory panel.

Anchor: ECSS-Q-ST-70-29 assessment step -- grading the odour an offgassing
sample presents to a trained panel before the material is accepted for a crew
compartment. Paraphrased into an implementable procedure; no standard text is
reproduced.

Procedure implemented here
--------------------------
1. Validate every panel entry: a judge identifier, a qualification flag and a
   score on the bounded intensity scale in permitted half steps.
2. Keep the qualified scores, recording which judges were set aside.
3. Refuse to grade a panel that falls below its minimum size once the
   unqualified judges are removed.
4. Compute the mean intensity and the sample standard deviation of the
   qualified scores.
5. Apply the veto rule for a score at the top of the scale.
6. Grade the mean against the acceptance rating under a named tolerance.
"""

import math

__all__ = [
    "RATING_TOLERANCE",
    "SCALE_MIN",
    "SCALE_MAX",
    "SCALE_STEP",
    "DEFAULT_ACCEPTANCE_RATING",
    "DEFAULT_MIN_PANEL",
    "DEFAULT_DISPERSION_LIMIT",
    "VERDICT_ACCEPTABLE",
    "VERDICT_NOT_ACCEPTABLE",
    "VERDICT_NOT_GRADED",
    "validate_score",
    "validate_entry",
    "qualified_scores",
    "mean_rating",
    "score_dispersion",
    "veto_scores",
    "grade_mean",
    "assess_odour",
]

# The mean is a quotient of sums; a panel that is physically exactly on the
# acceptance rating can land a few ULP either side of it. Absorb the
# representation error here rather than by moving the rating.
RATING_TOLERANCE = 1e-9

SCALE_MIN = 0.0
SCALE_MAX = 4.0
SCALE_STEP = 0.5

DEFAULT_ACCEPTANCE_RATING = 2.5
DEFAULT_MIN_PANEL = 5
DEFAULT_DISPERSION_LIMIT = 1.0

VERDICT_ACCEPTABLE = "acceptable"
VERDICT_NOT_ACCEPTABLE = "not-acceptable"
VERDICT_NOT_GRADED = "not-graded"


def validate_score(score):
    """Return a score on the bounded intensity scale, in permitted half steps."""
    if not isinstance(score, (int, float)) or isinstance(score, bool):
        raise ValueError("score must be a real number, got %r" % (score,))
    value = float(score)
    if not math.isfinite(value):
        raise ValueError("score must be finite, got %r" % (score,))
    if value < SCALE_MIN - RATING_TOLERANCE or value > SCALE_MAX + RATING_TOLERANCE:
        raise ValueError(
            "score %r is outside the scale [%g, %g]" % (score, SCALE_MIN, SCALE_MAX)
        )
    steps = value / SCALE_STEP
    if abs(steps - round(steps)) > 1e-9:
        raise ValueError(
            "score %r is not a multiple of the %g scale step" % (score, SCALE_STEP)
        )
    return min(max(value, SCALE_MIN), SCALE_MAX)


def validate_entry(entry):
    """Return a normalised panel entry: judge, qualified flag, validated score."""
    if not isinstance(entry, dict):
        raise ValueError("panel entry must be a mapping")
    for key in ("judge", "score"):
        if key not in entry:
            raise ValueError("panel entry missing required key '%s'" % key)
    judge = entry["judge"]
    if not isinstance(judge, str) or not judge.strip():
        raise ValueError("judge must be a non-empty string")
    qualified = entry.get("qualified", True)
    if not isinstance(qualified, bool):
        raise ValueError("qualified must be a boolean, got %r" % (qualified,))
    return {
        "judge": judge.strip(),
        "qualified": qualified,
        "score": validate_score(entry["score"]),
    }


def qualified_scores(entries):
    """Return (kept_entries, dropped_judges) after the qualification filter."""
    if not isinstance(entries, (list, tuple)) or not entries:
        raise ValueError("entries must be a non-empty sequence of panel entries")
    kept = []
    dropped = []
    seen = set()
    for entry in entries:
        record = validate_entry(entry)
        if record["judge"] in seen:
            raise ValueError("duplicate judge %r on the panel sheet" % record["judge"])
        seen.add(record["judge"])
        if record["qualified"]:
            kept.append(record)
        else:
            dropped.append(record["judge"])
    return (kept, sorted(dropped))


def mean_rating(scores):
    """Return the mean intensity of a non-empty score sequence."""
    if not isinstance(scores, (list, tuple)) or not scores:
        raise ValueError("scores must be a non-empty sequence")
    values = [validate_score(s) for s in scores]
    return math.fsum(values) / len(values)


def score_dispersion(scores):
    """Return the sample standard deviation of the panel scores."""
    if not isinstance(scores, (list, tuple)) or len(scores) < 2:
        raise ValueError("dispersion needs at least two scores")
    values = [validate_score(s) for s in scores]
    mean = math.fsum(values) / len(values)
    squares = math.fsum((v - mean) ** 2 for v in values)
    return math.sqrt(squares / (len(values) - 1))


def veto_scores(entries):
    """Return the judges whose score sits at the top of the intensity scale."""
    if not isinstance(entries, (list, tuple)):
        raise ValueError("entries must be a sequence of validated panel entries")
    out = []
    for entry in entries:
        if entry["score"] >= SCALE_MAX - RATING_TOLERANCE:
            out.append(entry["judge"])
    return sorted(out)


def grade_mean(mean, acceptance_rating=DEFAULT_ACCEPTANCE_RATING):
    """Return True when the mean intensity meets the acceptance rating."""
    if not isinstance(mean, (int, float)) or isinstance(mean, bool):
        raise ValueError("mean must be a real number")
    value = float(mean)
    if not math.isfinite(value):
        raise ValueError("mean must be finite")
    rating = acceptance_rating
    if not isinstance(rating, (int, float)) or isinstance(rating, bool):
        raise ValueError("acceptance_rating must be a real number")
    rating = float(rating)
    if rating <= SCALE_MIN or rating > SCALE_MAX:
        raise ValueError(
            "acceptance_rating must lie in (%g, %g], got %r"
            % (SCALE_MIN, SCALE_MAX, acceptance_rating)
        )
    return value <= rating + RATING_TOLERANCE


def assess_odour(spec):
    """Run the full odour acceptability assessment over one panel sheet.

    spec keys: entries (sequence of panel entries), optional acceptance_rating,
    min_panel, dispersion_limit.
    """
    if not isinstance(spec, dict):
        raise ValueError("spec must be a mapping")
    if "entries" not in spec:
        raise ValueError("spec missing required key 'entries'")
    min_panel = spec.get("min_panel", DEFAULT_MIN_PANEL)
    if not isinstance(min_panel, int) or isinstance(min_panel, bool) or min_panel < 2:
        raise ValueError("min_panel must be an integer of at least 2, got %r" % (min_panel,))
    dispersion_limit = spec.get("dispersion_limit", DEFAULT_DISPERSION_LIMIT)
    if (not isinstance(dispersion_limit, (int, float))
            or isinstance(dispersion_limit, bool)
            or not math.isfinite(float(dispersion_limit))
            or float(dispersion_limit) <= 0.0):
        raise ValueError("dispersion_limit must be positive, got %r" % (dispersion_limit,))
    dispersion_limit = float(dispersion_limit)
    rating = float(spec.get("acceptance_rating", DEFAULT_ACCEPTANCE_RATING))
    kept, dropped = qualified_scores(spec["entries"])
    findings = []
    if dropped:
        findings.append(
            "scores set aside from judges not currently qualified: %s" % ", ".join(dropped)
        )
    result = {
        "qualified_panel_size": len(kept),
        "dropped_judges": dropped,
        "mean_rating": None,
        "dispersion": None,
        "veto_judges": [],
        "acceptance_rating": rating,
        "verdict": VERDICT_NOT_GRADED,
        "acceptable": False,
        "findings": findings,
    }
    if len(kept) < min_panel:
        findings.append(
            "qualified panel of %d is below the minimum of %d; repeat the test"
            % (len(kept), min_panel)
        )
        return result
    scores = [entry["score"] for entry in kept]
    mean = mean_rating(scores)
    dispersion = score_dispersion(scores)
    veto = veto_scores(kept)
    result["mean_rating"] = mean
    result["dispersion"] = dispersion
    result["veto_judges"] = veto
    within_rating = grade_mean(mean, rating)
    agreed = dispersion <= dispersion_limit + RATING_TOLERANCE
    if not within_rating:
        findings.append(
            "mean intensity %.3f exceeds the acceptance rating %.3f" % (mean, rating)
        )
    if not agreed:
        findings.append(
            "panel dispersion %.3f exceeds the agreement limit %.3f; the sample "
            "presents differently to different judges" % (dispersion, dispersion_limit)
        )
    if veto:
        findings.append(
            "top-of-scale score from: %s; the mean does not override it" % ", ".join(veto)
        )
    acceptable = within_rating and agreed and not veto
    result["acceptable"] = acceptable
    result["verdict"] = VERDICT_ACCEPTABLE if acceptable else VERDICT_NOT_ACCEPTABLE
    return result
