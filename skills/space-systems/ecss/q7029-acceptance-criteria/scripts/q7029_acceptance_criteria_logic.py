"""Offgassing acceptance criteria applied to one test article.

Anchor: ECSS-Q-ST-70-29 acceptance step -- combining per-compound limits,
chemical-class caps, the governing toxicity total, the odour verdict and the
unidentified-area budget into a single verdict on the article. Paraphrased
into an implementable procedure; no standard text is reproduced.

Procedure implemented here
--------------------------
1. Validate the applicable limit sets and the reported product set.
2. Compute the utilisation of every reported compound against its own limit;
   a compound with no limit becomes an open item, never a zero utilisation.
3. Sum the reported concentrations inside each chemical class and compute the
   class utilisation against its cap.
4. Compute the utilisation of the governing toxicity total, the unidentified
   peak-area fraction, and take the odour verdict as a pass or fail criterion.
5. Select the governing criterion as the one with the highest utilisation and
   return the verdict, the breaches and the open items.
"""

import math

__all__ = [
    "UTILISATION_TOLERANCE",
    "VERDICT_ACCEPTED",
    "VERDICT_REJECTED",
    "VERDICT_OPEN",
    "ODOUR_PASS",
    "ODOUR_FAIL",
    "ODOUR_NOT_GRADED",
    "validate_limit_map",
    "utilisation",
    "compound_criteria",
    "class_criteria",
    "toxicity_criterion",
    "odour_criterion",
    "unidentified_criterion",
    "governing_criterion",
    "apply_acceptance",
]

# Every criterion is a quotient; a value that is physically exactly on its
# limit can land a few ULP either side of it. Absorb the representation error
# here rather than by widening the limit.
UTILISATION_TOLERANCE = 1e-9

VERDICT_ACCEPTED = "accepted"
VERDICT_REJECTED = "rejected"
VERDICT_OPEN = "open"

ODOUR_PASS = "pass"
ODOUR_FAIL = "fail"
ODOUR_NOT_GRADED = "not-graded"

_ODOUR_VALUES = {ODOUR_PASS, ODOUR_FAIL, ODOUR_NOT_GRADED}


def _real(label, value):
    if not isinstance(value, (int, float)) or isinstance(value, bool):
        raise ValueError("%s must be a real number, got %r" % (label, value))
    v = float(value)
    if not math.isfinite(v):
        raise ValueError("%s must be finite, got %r" % (label, value))
    return v


def _positive(label, value):
    v = _real(label, value)
    if v <= 0.0:
        raise ValueError("%s must be positive, got %r" % (label, value))
    return v


def _non_negative(label, value):
    v = _real(label, value)
    if v < 0.0:
        raise ValueError("%s must not be negative, got %r" % (label, value))
    return v


def validate_limit_map(limits, name="limits"):
    """Return a mapping of key -> positive limit, refusing malformed entries."""
    if not isinstance(limits, dict):
        raise ValueError("%s must be a mapping of key -> limit" % name)
    out = {}
    for key, value in limits.items():
        if not isinstance(key, str) or not key.strip():
            raise ValueError("%s keys must be non-empty strings" % name)
        out[key.strip()] = _positive("%s[%s]" % (name, key), value)
    return out


def utilisation(observed, limit):
    """Return the observed value as a fraction of its limit."""
    value = _non_negative("observed", observed)
    bound = _positive("limit", limit)
    return value / bound


def _criterion(name, observed, limit, detail):
    used = utilisation(observed, limit)
    return {
        "criterion": name,
        "observed": observed,
        "limit": limit,
        "utilisation": used,
        "met": used <= 1.0 + UTILISATION_TOLERANCE,
        "detail": detail,
    }


def compound_criteria(products, compound_limits):
    """Return (criteria, open_items) for the per-compound concentration limits."""
    if not isinstance(products, (list, tuple)) or not products:
        raise ValueError("products must be a non-empty sequence")
    limits = validate_limit_map(compound_limits, "compound_limits")
    criteria = []
    open_items = []
    seen = set()
    for item in products:
        if not isinstance(item, dict):
            raise ValueError("each product must be a mapping")
        for key in ("compound", "concentration_mg_m3", "chemical_class"):
            if key not in item:
                raise ValueError("product missing required key '%s'" % key)
        compound = item["compound"]
        if not isinstance(compound, str) or not compound.strip():
            raise ValueError("compound must be a non-empty string")
        compound = compound.strip()
        if compound in seen:
            raise ValueError("duplicate compound %r in the product set" % compound)
        seen.add(compound)
        conc = _non_negative("concentration of %s" % compound, item["concentration_mg_m3"])
        limit = limits.get(compound)
        if limit is None:
            open_items.append(
                "no concentration limit published for %s; open item, not a pass" % compound
            )
            continue
        criteria.append(
            _criterion("compound-limit", conc, limit, compound)
        )
    return (criteria, open_items)


def class_criteria(products, class_caps):
    """Return the criteria comparing each class sum with its cap."""
    if not isinstance(products, (list, tuple)) or not products:
        raise ValueError("products must be a non-empty sequence")
    caps = validate_limit_map(class_caps, "class_caps")
    sums = {}
    for item in products:
        chem_class = item["chemical_class"]
        if not isinstance(chem_class, str) or not chem_class.strip():
            raise ValueError("chemical_class must be a non-empty string")
        chem_class = chem_class.strip()
        conc = _non_negative("concentration", item["concentration_mg_m3"])
        sums[chem_class] = sums.get(chem_class, 0.0) + conc
    criteria = []
    open_items = []
    for chem_class in sorted(sums):
        cap = caps.get(chem_class)
        if cap is None:
            open_items.append(
                "no class cap published for %s; open item, not a pass" % chem_class
            )
            continue
        criteria.append(_criterion("class-cap", sums[chem_class], cap, chem_class))
    return (criteria, open_items, sums)


def toxicity_criterion(governing_t_value, t_limit=1.0):
    """Return the criterion comparing the governing toxicity total with its bound."""
    return _criterion(
        "toxicity-total",
        _non_negative("governing_t_value", governing_t_value),
        _positive("t_limit", t_limit),
        "governing toxicological group total",
    )


def odour_criterion(odour_verdict):
    """Return the odour criterion, treating an ungraded panel as an open item."""
    if odour_verdict not in _ODOUR_VALUES:
        raise ValueError(
            "odour_verdict must be one of %s, got %r"
            % (sorted(_ODOUR_VALUES), odour_verdict)
        )
    met = odour_verdict == ODOUR_PASS
    return {
        "criterion": "odour",
        "observed": odour_verdict,
        "limit": ODOUR_PASS,
        "utilisation": 0.0 if met else 2.0,
        "met": met,
        "detail": "sensory panel verdict",
    }


def unidentified_criterion(unidentified_fraction, budget):
    """Return the criterion comparing the unidentified area fraction with its budget."""
    fraction = _non_negative("unidentified_fraction", unidentified_fraction)
    if fraction > 1.0:
        raise ValueError("unidentified_fraction is a fraction, got %g" % fraction)
    bound = _positive("unidentified_budget", budget)
    if bound > 1.0:
        raise ValueError("unidentified_budget is a fraction, got %g" % bound)
    return _criterion("unidentified-area", fraction, bound, "unaccounted peak area")


def governing_criterion(criteria):
    """Return the criterion carrying the highest utilisation."""
    if not isinstance(criteria, (list, tuple)) or not criteria:
        raise ValueError("criteria must be a non-empty sequence")
    best = None
    for item in criteria:
        if not isinstance(item, dict) or "utilisation" not in item:
            raise ValueError("each criterion must be a mapping carrying 'utilisation'")
        if best is None:
            best = item
            continue
        if item["utilisation"] > best["utilisation"] + UTILISATION_TOLERANCE:
            best = item
    return best


def apply_acceptance(spec):
    """Apply every acceptance criterion and return the article verdict.

    spec keys: products, compound_limits, class_caps, governing_t_value,
    odour_verdict, unidentified_fraction, unidentified_budget, optional
    t_limit.
    """
    if not isinstance(spec, dict):
        raise ValueError("spec must be a mapping")
    required = (
        "products", "compound_limits", "class_caps", "governing_t_value",
        "odour_verdict", "unidentified_fraction", "unidentified_budget",
    )
    for key in required:
        if key not in spec:
            raise ValueError("spec missing required key '%s'" % key)
    compound_crits, open_items = compound_criteria(spec["products"], spec["compound_limits"])
    class_crits, class_open, class_sums = class_criteria(spec["products"], spec["class_caps"])
    open_items = list(open_items) + list(class_open)
    criteria = list(compound_crits) + list(class_crits)
    criteria.append(toxicity_criterion(spec["governing_t_value"], spec.get("t_limit", 1.0)))
    criteria.append(odour_criterion(spec["odour_verdict"]))
    criteria.append(
        unidentified_criterion(spec["unidentified_fraction"], spec["unidentified_budget"])
    )
    if spec["odour_verdict"] == ODOUR_NOT_GRADED:
        open_items.append("odour panel was not graded; open item, not a pass")
    breaches = [c for c in criteria if not c["met"]]
    governing = governing_criterion(criteria)
    if breaches:
        verdict = VERDICT_REJECTED
    elif open_items:
        verdict = VERDICT_OPEN
    else:
        verdict = VERDICT_ACCEPTED
    return {
        "criteria": criteria,
        "class_sums": class_sums,
        "breached": [
            "%s (%s) at %.3f of its limit" % (c["criterion"], c["detail"], c["utilisation"])
            for c in breaches
        ],
        "open_items": open_items,
        "governing_criterion": governing["criterion"],
        "governing_detail": governing["detail"],
        "governing_utilisation": governing["utilisation"],
        "verdict": verdict,
        "accepted": verdict == VERDICT_ACCEPTED,
    }
