"""Alloy selection against stress-corrosion-cracking resistance ratings.

Anchor: ECSS-Q-ST-70-36C, the selection clauses that decide which candidate
alloy states may be used in an application of a given SCC criticality.
Paraphrased into an implementable procedure; no standard text is reproduced.

Procedure implemented here
--------------------------
1. Read the published SCC resistance rating of each candidate alloy state.
2. Downgrade that rating one step when the sustained tensile stress acts along
   the short-transverse grain direction of the product form, because that is
   the direction the published ratings are weakest in.
3. Apply the acceptance rule for the criticality of the application: an SCC
   critical item needs a resistant state outright, accepts an intermediate one
   only against documented test evidence, and cannot take a susceptible one
   without a formal approval.
4. Rank the acceptable candidates by effective rating, then by the strength
   they buy, and break any remaining tie on the candidate identifier so the
   recommendation is reproducible.
"""

import math

__all__ = [
    "RANK_TOLERANCE",
    "RESISTANCE_CATEGORIES",
    "CRITICALITY_GRADES",
    "GRAIN_DIRECTIONS",
    "ACCEPTANCE_RULES",
    "normalize_category",
    "normalize_criticality",
    "normalize_direction",
    "category_rank",
    "downgrade_category",
    "effective_category",
    "acceptance_for",
    "evaluate_candidate",
    "rank_candidates",
    "select_alloy",
]

# Strength values are compared to order candidates of equal rating; two values
# an engineer means to be equal must not order differently because of a float
# representation error.
RANK_TOLERANCE = 1e-9

# Ratings ordered from most to least resistant.
RESISTANCE_CATEGORIES = ("high", "medium", "low")

# Criticality grades an application can carry into the selection.
CRITICALITY_GRADES = ("scc-critical", "scc-monitored", "not-scc-critical")

# Grain directions relative to the sustained tensile stress. The
# short-transverse direction is the weak one for the published ratings.
GRAIN_DIRECTIONS = ("longitudinal", "long-transverse", "short-transverse")

# What each criticality grade will take, per effective rating.
ACCEPTANCE_RULES = {
    "scc-critical": {
        "high": "accepted",
        "medium": "accepted-with-evidence",
        "low": "rejected",
    },
    "scc-monitored": {
        "high": "accepted",
        "medium": "accepted",
        "low": "accepted-with-evidence",
    },
    "not-scc-critical": {
        "high": "accepted",
        "medium": "accepted",
        "low": "accepted",
    },
}

_CATEGORY_ALIASES = {
    "high-resistance": "high",
    "resistant": "high",
    "moderate": "medium",
    "medium-resistance": "medium",
    "intermediate": "medium",
    "low-resistance": "low",
    "susceptible": "low",
}

_CRITICALITY_ALIASES = {
    "critical": "scc-critical",
    "monitored": "scc-monitored",
    "cleared": "not-scc-critical",
    "non-critical": "not-scc-critical",
}

_DIRECTION_ALIASES = {
    "l": "longitudinal",
    "lt": "long-transverse",
    "t": "long-transverse",
    "transverse": "long-transverse",
    "st": "short-transverse",
    "through-thickness": "short-transverse",
}


def _token(value, label):
    """Return a lower-cased dash-normalized token, or raise."""
    if not isinstance(value, str):
        raise ValueError("%s must be a string, got %r" % (label, type(value).__name__))
    text = value.strip().lower().replace("_", "-").replace(" ", "-")
    if not text:
        raise ValueError("%s must not be blank" % label)
    return text


def normalize_category(value):
    """Return the canonical SCC resistance rating token."""
    token = _token(value, "resistance category")
    token = _CATEGORY_ALIASES.get(token, token)
    if token not in RESISTANCE_CATEGORIES:
        raise ValueError(
            "resistance category %r is not one of %s"
            % (value, ", ".join(RESISTANCE_CATEGORIES))
        )
    return token


def normalize_criticality(value):
    """Return the canonical application criticality token."""
    token = _token(value, "criticality")
    token = _CRITICALITY_ALIASES.get(token, token)
    if token not in CRITICALITY_GRADES:
        raise ValueError(
            "criticality %r is not one of %s" % (value, ", ".join(CRITICALITY_GRADES))
        )
    return token


def normalize_direction(value):
    """Return the canonical grain direction token."""
    token = _token(value, "grain direction")
    token = _DIRECTION_ALIASES.get(token, token)
    if token not in GRAIN_DIRECTIONS:
        raise ValueError(
            "grain direction %r is not one of %s" % (value, ", ".join(GRAIN_DIRECTIONS))
        )
    return token


def category_rank(category):
    """Return 0 for the most resistant rating, rising as resistance falls."""
    return RESISTANCE_CATEGORIES.index(normalize_category(category))


def downgrade_category(category, steps=1):
    """Return the rating that many steps less resistant, floored at the lowest."""
    if not isinstance(steps, int) or isinstance(steps, bool):
        raise ValueError("steps must be an integer")
    if steps < 0:
        raise ValueError("steps must not be negative, got %d" % steps)
    index = min(category_rank(category) + steps, len(RESISTANCE_CATEGORIES) - 1)
    return RESISTANCE_CATEGORIES[index]


def effective_category(published_category, grain_direction):
    """Return the rating that governs, after the grain-direction downgrade."""
    direction = normalize_direction(grain_direction)
    published = normalize_category(published_category)
    if direction == "short-transverse":
        return downgrade_category(published, 1)
    return published


def acceptance_for(criticality, category):
    """Return the acceptance verdict for a rating at a criticality grade."""
    grade = normalize_criticality(criticality)
    rating = normalize_category(category)
    return ACCEPTANCE_RULES[grade][rating]


def _strength(value, label):
    """Return a strictly positive finite strength value."""
    if not isinstance(value, (int, float)) or isinstance(value, bool):
        raise ValueError("%s must be a real number" % label)
    number = float(value)
    if not math.isfinite(number) or number <= 0.0:
        raise ValueError("%s must be positive and finite, got %r" % (label, value))
    return number


def evaluate_candidate(candidate, criticality):
    """Return the selection record for one candidate alloy state."""
    if not isinstance(candidate, dict):
        raise ValueError("candidate must be a mapping")
    for key in ("id", "resistance_category", "grain_direction", "yield_strength_mpa"):
        if key not in candidate:
            raise ValueError("candidate missing required key %r" % key)
    candidate_id = _token(candidate["id"], "candidate id")
    published = normalize_category(candidate["resistance_category"])
    direction = normalize_direction(candidate["grain_direction"])
    effective = effective_category(published, direction)
    verdict = acceptance_for(criticality, effective)
    strength = _strength(candidate["yield_strength_mpa"], "yield_strength_mpa")
    notes = []
    if effective != published:
        notes.append(
            "published rating %s downgraded to %s: the sustained stress acts "
            "short-transverse" % (published, effective)
        )
    if verdict == "accepted-with-evidence":
        notes.append("usable only against documented SCC test evidence for this state")
    if verdict == "rejected":
        notes.append("not usable at this criticality without a formal approval")
    return {
        "id": candidate_id,
        "published_category": published,
        "grain_direction": direction,
        "effective_category": effective,
        "effective_rank": category_rank(effective),
        "yield_strength_mpa": strength,
        "verdict": verdict,
        "acceptable": verdict != "rejected",
        "notes": notes,
    }


def rank_candidates(candidates, criticality):
    """Return every candidate record, best first.

    Ordering: most resistant effective rating first, then the higher yield
    strength, then the candidate identifier so ties are reproducible.
    """
    if not isinstance(candidates, (list, tuple)) or not candidates:
        raise ValueError("candidates must be a non-empty sequence of mappings")
    records = []
    seen = set()
    for candidate in candidates:
        record = evaluate_candidate(candidate, criticality)
        if record["id"] in seen:
            raise ValueError("duplicate candidate id %r" % record["id"])
        seen.add(record["id"])
        records.append(record)
    def key(record):
        strength = record["yield_strength_mpa"]
        # Quantise the strength so two values meant to be equal cannot order on
        # a representation difference; the identifier then breaks the tie.
        quantised = round(strength / RANK_TOLERANCE)
        return (record["effective_rank"], -quantised, record["id"])
    return sorted(records, key=key)


def select_alloy(candidates, criticality):
    """Recommend an alloy state and report the whole ranked field."""
    grade = normalize_criticality(criticality)
    ranked = rank_candidates(candidates, grade)
    acceptable = [r for r in ranked if r["acceptable"]]
    outright = [r for r in acceptable if r["verdict"] == "accepted"]
    recommended = outright[0] if outright else (acceptable[0] if acceptable else None)
    findings = []
    if recommended is None:
        findings.append(
            "no candidate is usable at criticality %s; every state is rated "
            "susceptible in its loaded direction" % grade
        )
    elif recommended["verdict"] == "accepted-with-evidence":
        findings.append(
            "recommended candidate %s is usable only against documented SCC test "
            "evidence; no outright-acceptable state was offered" % recommended["id"]
        )
    for record in ranked:
        if record["effective_category"] != record["published_category"]:
            findings.append(
                "candidate %s loses a rating step to short-transverse loading"
                % record["id"]
            )
    return {
        "criticality": grade,
        "ranked": ranked,
        "acceptable_count": len(acceptable),
        "recommended": recommended,
        "compliant": recommended is not None and recommended["verdict"] == "accepted",
        "findings": findings,
    }
