"""Offgassing product identification from chromatographic evidence.

Anchor: ECSS-Q-ST-70-29 analysis step -- naming the products collected from a
material or assembled article destined for a manned crew compartment.
Paraphrased into an implementable procedure; no standard text is reproduced.

Procedure implemented here
--------------------------
1. Validate the integrated peak list and the reference library.
2. For each peak, pick the best library candidate and measure both pieces of
   evidence: the retention-index deviation against the declared window and the
   spectral match score against the confirmation and tentative thresholds.
3. Grade the assignment as confirmed, tentative or unidentified.
4. Detect adjacent peaks separated by less than the column resolution floor and
   hold both back for a second technique.
5. Downgrade any toxicity-driving assignment lacking orthogonal confirmation.
6. Account for the integrated area left unidentified and compare the fraction
   with the declared budget.
"""

import math

__all__ = [
    "SCORE_TOLERANCE",
    "AREA_TOLERANCE",
    "DEFAULT_RI_WINDOW",
    "DEFAULT_CONFIRMED_SCORE",
    "DEFAULT_TENTATIVE_SCORE",
    "DEFAULT_RESOLUTION_FLOOR",
    "DEFAULT_UNIDENTIFIED_BUDGET",
    "GRADE_CONFIRMED",
    "GRADE_TENTATIVE",
    "GRADE_UNIDENTIFIED",
    "validate_peak",
    "validate_library",
    "retention_index_deviation",
    "grade_assignment",
    "best_candidate",
    "identify_peak",
    "coelution_pairs",
    "apply_coelution_holds",
    "apply_confirmation_rule",
    "unidentified_area_fraction",
    "assess_identification",
]

# A match score or a retention deviation computed from float arithmetic can land
# a few ULP on the wrong side of a threshold. Absorb the representation error
# here rather than by moving the threshold.
SCORE_TOLERANCE = 1e-9
AREA_TOLERANCE = 1e-12

DEFAULT_RI_WINDOW = 20.0
DEFAULT_CONFIRMED_SCORE = 850.0
DEFAULT_TENTATIVE_SCORE = 700.0
DEFAULT_RESOLUTION_FLOOR = 5.0
DEFAULT_UNIDENTIFIED_BUDGET = 0.05

GRADE_CONFIRMED = "confirmed"
GRADE_TENTATIVE = "tentative"
GRADE_UNIDENTIFIED = "unidentified"

_GRADE_RANK = {GRADE_UNIDENTIFIED: 0, GRADE_TENTATIVE: 1, GRADE_CONFIRMED: 2}


def _positive(label, value):
    """Return value as a positive finite float or raise ValueError."""
    if not isinstance(value, (int, float)) or isinstance(value, bool):
        raise ValueError("%s must be a real number, got %r" % (label, value))
    v = float(value)
    if not math.isfinite(v):
        raise ValueError("%s must be finite, got %r" % (label, value))
    if v <= 0.0:
        raise ValueError("%s must be positive, got %r" % (label, value))
    return v


def _non_negative(label, value):
    """Return value as a non-negative finite float or raise ValueError."""
    if not isinstance(value, (int, float)) or isinstance(value, bool):
        raise ValueError("%s must be a real number, got %r" % (label, value))
    v = float(value)
    if not math.isfinite(v):
        raise ValueError("%s must be finite, got %r" % (label, value))
    if v < 0.0:
        raise ValueError("%s must not be negative, got %r" % (label, value))
    return v


def validate_peak(peak):
    """Return a normalised peak record: id, retention index, area, candidates."""
    if not isinstance(peak, dict):
        raise ValueError("peak must be a mapping, got %r" % type(peak).__name__)
    for key in ("peak_id", "retention_index", "area_counts"):
        if key not in peak:
            raise ValueError("peak missing required key '%s'" % key)
    peak_id = peak["peak_id"]
    if not isinstance(peak_id, str) or not peak_id.strip():
        raise ValueError("peak_id must be a non-empty string")
    candidates = peak.get("candidates", [])
    if not isinstance(candidates, (list, tuple)):
        raise ValueError("peak candidates must be a sequence")
    normalised = []
    for i, cand in enumerate(candidates):
        if not isinstance(cand, dict):
            raise ValueError("candidate %d of peak %s must be a mapping" % (i, peak_id))
        for key in ("compound", "match_score"):
            if key not in cand:
                raise ValueError(
                    "candidate %d of peak %s missing '%s'" % (i, peak_id, key)
                )
        compound = cand["compound"]
        if not isinstance(compound, str) or not compound.strip():
            raise ValueError("candidate compound must be a non-empty string")
        score = _non_negative("match_score of %s" % compound, cand["match_score"])
        if score > 1000.0:
            raise ValueError("match_score is on a 0-1000 scale, got %g" % score)
        normalised.append({"compound": compound, "match_score": score})
    return {
        "peak_id": peak_id.strip(),
        "retention_index": _positive("retention_index of %s" % peak_id, peak["retention_index"]),
        "area_counts": _positive("area_counts of %s" % peak_id, peak["area_counts"]),
        "candidates": normalised,
        "second_technique": bool(peak.get("second_technique", False)),
    }


def validate_library(library):
    """Return the library as a mapping compound -> reference entry."""
    if not isinstance(library, dict) or not library:
        raise ValueError("library must be a non-empty mapping of compound -> entry")
    out = {}
    for compound, entry in library.items():
        if not isinstance(compound, str) or not compound.strip():
            raise ValueError("library keys must be non-empty compound names")
        if not isinstance(entry, dict):
            raise ValueError("library entry for %s must be a mapping" % compound)
        if "reference_index" not in entry:
            raise ValueError("library entry for %s missing 'reference_index'" % compound)
        out[compound] = {
            "reference_index": _positive(
                "reference_index of %s" % compound, entry["reference_index"]
            ),
            "toxicity_driver": bool(entry.get("toxicity_driver", False)),
        }
    return out


def retention_index_deviation(observed_index, reference_index):
    """Return the absolute retention-index deviation between peak and library."""
    obs = _positive("observed_index", observed_index)
    ref = _positive("reference_index", reference_index)
    return abs(obs - ref)


def grade_assignment(match_score, deviation, ri_window=DEFAULT_RI_WINDOW,
                     confirmed_score=DEFAULT_CONFIRMED_SCORE,
                     tentative_score=DEFAULT_TENTATIVE_SCORE):
    """Grade one candidate from its score and its retention-index deviation."""
    score = _non_negative("match_score", match_score)
    dev = _non_negative("deviation", deviation)
    window = _positive("ri_window", ri_window)
    conf = _non_negative("confirmed_score", confirmed_score)
    tent = _non_negative("tentative_score", tentative_score)
    if tent > conf:
        raise ValueError(
            "tentative_score %g must not exceed confirmed_score %g" % (tent, conf)
        )
    in_window = dev <= window + SCORE_TOLERANCE
    if in_window and score >= conf - SCORE_TOLERANCE:
        return GRADE_CONFIRMED
    if score >= tent - SCORE_TOLERANCE and dev <= 2.0 * window + SCORE_TOLERANCE:
        return GRADE_TENTATIVE
    return GRADE_UNIDENTIFIED


def best_candidate(peak, library, ri_window=DEFAULT_RI_WINDOW,
                   confirmed_score=DEFAULT_CONFIRMED_SCORE,
                   tentative_score=DEFAULT_TENTATIVE_SCORE):
    """Return the best-graded candidate for a peak, or None when none grades."""
    best = None
    for cand in peak["candidates"]:
        entry = library.get(cand["compound"])
        if entry is None:
            continue
        dev = retention_index_deviation(peak["retention_index"], entry["reference_index"])
        grade = grade_assignment(
            cand["match_score"], dev, ri_window, confirmed_score, tentative_score
        )
        record = {
            "compound": cand["compound"],
            "match_score": cand["match_score"],
            "ri_deviation": dev,
            "grade": grade,
            "toxicity_driver": entry["toxicity_driver"],
        }
        if best is None:
            best = record
            continue
        if _GRADE_RANK[grade] > _GRADE_RANK[best["grade"]]:
            best = record
        elif _GRADE_RANK[grade] == _GRADE_RANK[best["grade"]]:
            if record["match_score"] > best["match_score"] + SCORE_TOLERANCE:
                best = record
    return best


def identify_peak(peak, library, ri_window=DEFAULT_RI_WINDOW,
                  confirmed_score=DEFAULT_CONFIRMED_SCORE,
                  tentative_score=DEFAULT_TENTATIVE_SCORE):
    """Return the identification record for one validated peak."""
    valid = validate_peak(peak)
    lib = validate_library(library)
    best = best_candidate(valid, lib, ri_window, confirmed_score, tentative_score)
    record = {
        "peak_id": valid["peak_id"],
        "retention_index": valid["retention_index"],
        "area_counts": valid["area_counts"],
        "second_technique": valid["second_technique"],
        "compound": None,
        "match_score": None,
        "ri_deviation": None,
        "grade": GRADE_UNIDENTIFIED,
        "toxicity_driver": False,
        "notes": [],
    }
    if best is not None and best["grade"] != GRADE_UNIDENTIFIED:
        record.update(
            compound=best["compound"],
            match_score=best["match_score"],
            ri_deviation=best["ri_deviation"],
            grade=best["grade"],
            toxicity_driver=best["toxicity_driver"],
        )
    elif best is not None:
        record["notes"].append(
            "best candidate %s graded unidentified (score %g, deviation %g)"
            % (best["compound"], best["match_score"], best["ri_deviation"])
        )
    return record


def coelution_pairs(records, resolution_floor=DEFAULT_RESOLUTION_FLOOR):
    """Return adjacent peak-id pairs closer than the column resolution floor."""
    floor = _positive("resolution_floor", resolution_floor)
    ordered = sorted(records, key=lambda r: r["retention_index"])
    pairs = []
    for i in range(1, len(ordered)):
        gap = ordered[i]["retention_index"] - ordered[i - 1]["retention_index"]
        if gap < floor - SCORE_TOLERANCE:
            pairs.append((ordered[i - 1]["peak_id"], ordered[i]["peak_id"]))
    return pairs


def apply_coelution_holds(records, resolution_floor=DEFAULT_RESOLUTION_FLOOR):
    """Downgrade confirmed members of an unresolved pair to tentative."""
    pairs = coelution_pairs(records, resolution_floor)
    held = set()
    for left, right in pairs:
        held.add(left)
        held.add(right)
    by_id = {r["peak_id"]: r for r in records}
    for peak_id in sorted(held):
        record = by_id[peak_id]
        if record["second_technique"]:
            record["notes"].append("unresolved pair separated by a second technique")
            continue
        if record["grade"] == GRADE_CONFIRMED:
            record["grade"] = GRADE_TENTATIVE
        record["notes"].append("held back for a second technique: unresolved co-elution")
    return pairs


def apply_confirmation_rule(records):
    """Downgrade toxicity-driving assignments with no orthogonal confirmation."""
    downgraded = []
    for record in records:
        if not record["toxicity_driver"]:
            continue
        if record["grade"] != GRADE_CONFIRMED:
            continue
        if record["second_technique"]:
            continue
        record["grade"] = GRADE_TENTATIVE
        record["notes"].append(
            "toxicity-driving product without orthogonal confirmation"
        )
        downgraded.append(record["peak_id"])
    return downgraded


def unidentified_area_fraction(records):
    """Return the share of integrated area carried by unidentified peaks."""
    if not isinstance(records, (list, tuple)) or not records:
        raise ValueError("records must be a non-empty sequence")
    total = 0.0
    unknown = 0.0
    for record in records:
        area = _positive("area_counts of %s" % record.get("peak_id", "?"),
                         record["area_counts"])
        total += area
        if record["grade"] == GRADE_UNIDENTIFIED:
            unknown += area
    if total <= AREA_TOLERANCE:
        raise ValueError("total integrated area is not usable for a fraction")
    return unknown / total


def assess_identification(spec):
    """Run the full product-identification assessment over a peak list.

    spec keys: peaks (sequence), library (mapping), optional ri_window,
    confirmed_score, tentative_score, resolution_floor, unidentified_budget.
    """
    if not isinstance(spec, dict):
        raise ValueError("spec must be a mapping")
    for key in ("peaks", "library"):
        if key not in spec:
            raise ValueError("spec missing required key '%s'" % key)
    peaks = spec["peaks"]
    if not isinstance(peaks, (list, tuple)) or not peaks:
        raise ValueError("spec['peaks'] must be a non-empty sequence")
    ri_window = spec.get("ri_window", DEFAULT_RI_WINDOW)
    confirmed_score = spec.get("confirmed_score", DEFAULT_CONFIRMED_SCORE)
    tentative_score = spec.get("tentative_score", DEFAULT_TENTATIVE_SCORE)
    resolution_floor = spec.get("resolution_floor", DEFAULT_RESOLUTION_FLOOR)
    budget = _non_negative(
        "unidentified_budget", spec.get("unidentified_budget", DEFAULT_UNIDENTIFIED_BUDGET)
    )
    if budget > 1.0:
        raise ValueError("unidentified_budget is a fraction, got %g" % budget)
    records = [
        identify_peak(peak, spec["library"], ri_window, confirmed_score, tentative_score)
        for peak in peaks
    ]
    seen = set()
    for record in records:
        if record["peak_id"] in seen:
            raise ValueError("duplicate peak_id %r in the peak list" % record["peak_id"])
        seen.add(record["peak_id"])
    pairs = apply_coelution_holds(records, resolution_floor)
    downgraded = apply_confirmation_rule(records)
    fraction = unidentified_area_fraction(records)
    findings = []
    if pairs:
        findings.append(
            "%d unresolved co-eluting pair(s) held back for a second technique" % len(pairs)
        )
    if downgraded:
        findings.append(
            "toxicity-driving product(s) without orthogonal confirmation: %s"
            % ", ".join(downgraded)
        )
    over_budget = fraction > budget + SCORE_TOLERANCE
    if over_budget:
        findings.append(
            "unidentified area fraction %.4f exceeds the budget %.4f" % (fraction, budget)
        )
    counts = {
        GRADE_CONFIRMED: sum(1 for r in records if r["grade"] == GRADE_CONFIRMED),
        GRADE_TENTATIVE: sum(1 for r in records if r["grade"] == GRADE_TENTATIVE),
        GRADE_UNIDENTIFIED: sum(1 for r in records if r["grade"] == GRADE_UNIDENTIFIED),
    }
    return {
        "records": records,
        "grade_counts": counts,
        "coelution_pairs": pairs,
        "unconfirmed_drivers": downgraded,
        "unidentified_area_fraction": fraction,
        "unidentified_budget": budget,
        "inventory_complete": not over_budget,
        "findings": findings,
    }
