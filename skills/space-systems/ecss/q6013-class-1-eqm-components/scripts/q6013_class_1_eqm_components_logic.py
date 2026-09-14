"""Commercial components fitted to an engineering qualification model.

Anchor: ECSS-Q-ST-60-13C clause 4.1.6 (commercial components used on
engineering qualification models, and how representative of the flight build
they have to be). Paraphrased into an implementable procedure; no standard
text is reproduced.

Procedure implemented here
--------------------------
1. Validate the attribute weight set used to grade representativeness.
2. Compare each fitted component with its flight-intended counterpart,
   attribute by attribute, and collect the deviations.
3. Weight the deviations into a representativeness index for the component.
4. Map each deviation onto the qualification test domains whose results stop
   transferring to the flight build because of it -- a package substitution
   breaks the mechanical and thermal argument, a die-lot substitution breaks
   the lifetime and radiation argument. A deviation on the manufacturer or the
   part number is not a weighted deduction at all: the model carries a
   different part, and nothing transfers.
5. Categorize each component, accumulate the retest set the deviations create,
   and return one model-level transfer verdict.
"""

import math

__all__ = [
    "INDEX_TOLERANCE",
    "DEFAULT_ATTRIBUTE_WEIGHTS",
    "DEVIATION_IMPACT",
    "FUNDAMENTAL_ATTRIBUTES",
    "PART_CATEGORIES",
    "validate_weights",
    "compare_component",
    "representativeness_index",
    "invalidated_domains",
    "part_category",
    "evaluate_component",
    "retest_set",
    "assess_eqm_representativeness",
]

# The index is a sum of weights subtracted from unity; an exactly-met threshold
# can land a few ULPs low. Absorb that here, not by moving the threshold.
INDEX_TOLERANCE = 1e-9

# Build-standard attributes and the share of the representativeness argument
# each one carries. The weights sum to unity.
DEFAULT_ATTRIBUTE_WEIGHTS = {
    "manufacturer": 0.20,
    "part_number": 0.20,
    "package": 0.15,
    "die_lot": 0.15,
    "screening_level": 0.15,
    "mounting_technology": 0.15,
}

# Deviating attribute -> the qualification test domains whose result no longer
# carries over to the flight build.
DEVIATION_IMPACT = {
    "manufacturer": ("electrical", "lifetime", "mechanical", "radiation", "thermal"),
    "part_number": ("electrical", "lifetime", "mechanical", "radiation", "thermal"),
    "package": ("mechanical", "thermal"),
    "die_lot": ("lifetime", "radiation"),
    "screening_level": ("lifetime",),
    "mounting_technology": ("mechanical", "thermal"),
}

# Attributes on which a deviation makes the fitted part a different part
# rather than a less representative one. No weighting rescues these: the
# qualification result was produced on something else.
FUNDAMENTAL_ATTRIBUTES = ("manufacturer", "part_number")

PART_CATEGORIES = (
    "representative",
    "partially-representative",
    "non-representative",
)

_CATEGORY_SEVERITY = {
    "non-representative": 0,
    "partially-representative": 1,
    "representative": 2,
}


def _require_text(value, label):
    """Return a non-blank stripped string, or raise."""
    if not isinstance(value, str):
        raise ValueError("%s must be a string, got %r" % (label, value))
    text = value.strip()
    if not text:
        raise ValueError("%s must not be blank" % label)
    return text


def _require_positive_int(value, label):
    """Return a strictly positive integer, or raise."""
    if isinstance(value, bool) or not isinstance(value, int):
        raise ValueError("%s must be an integer, got %r" % (label, value))
    if value <= 0:
        raise ValueError("%s must be strictly positive, got %d" % (label, value))
    return value


def validate_weights(weights=None):
    """Return a validated attribute weight mapping summing to unity."""
    if weights is None:
        weights = DEFAULT_ATTRIBUTE_WEIGHTS
    if not isinstance(weights, dict) or not weights:
        raise ValueError("weights must be a non-empty mapping")
    cleaned = {}
    for name, value in weights.items():
        attribute = _require_text(name, "weight attribute name")
        if isinstance(value, bool) or not isinstance(value, (int, float)):
            raise ValueError("weight of %s must be a real number" % attribute)
        number = float(value)
        if not math.isfinite(number) or number <= 0.0:
            raise ValueError("weight of %s must be positive and finite" % attribute)
        if attribute not in DEVIATION_IMPACT:
            raise ValueError(
                "attribute %s has no declared qualification impact; add it to the "
                "impact map before weighting it" % attribute
            )
        cleaned[attribute] = number
    total = math.fsum(cleaned.values())
    if not math.isclose(total, 1.0, rel_tol=0.0, abs_tol=INDEX_TOLERANCE):
        raise ValueError("attribute weights must sum to unity, got %.12f" % total)
    return cleaned


def compare_component(fitted, intended, weights=None):
    """Return the deviating attributes between a fitted and an intended part."""
    for label, mapping in (("fitted", fitted), ("intended", intended)):
        if not isinstance(mapping, dict):
            raise ValueError("%s component must be a mapping" % label)
    graded = validate_weights(weights)
    deviations = []
    for attribute in sorted(graded):
        if attribute not in fitted:
            raise ValueError("fitted component lacks the attribute %s" % attribute)
        if attribute not in intended:
            raise ValueError("intended component lacks the attribute %s" % attribute)
        left = _require_text(fitted[attribute], "fitted %s" % attribute).lower()
        right = _require_text(intended[attribute], "intended %s" % attribute).lower()
        if left != right:
            deviations.append(attribute)
    return tuple(deviations)


def representativeness_index(deviations, weights=None):
    """Return the weighted representativeness index of a fitted component."""
    graded = validate_weights(weights)
    if not isinstance(deviations, (list, tuple)):
        raise ValueError("deviations must be a sequence of attribute names")
    lost = 0.0
    seen = set()
    for attribute in deviations:
        name = _require_text(attribute, "deviation attribute")
        if name not in graded:
            raise ValueError("deviation %s is not a weighted attribute" % name)
        if name in seen:
            raise ValueError("deviation %s listed more than once" % name)
        seen.add(name)
        lost += graded[name]
    index = 1.0 - lost
    if index < 0.0:
        index = 0.0
    return index


def invalidated_domains(deviations):
    """Return the qualification domains whose result stops transferring."""
    if not isinstance(deviations, (list, tuple)):
        raise ValueError("deviations must be a sequence of attribute names")
    domains = set()
    for attribute in deviations:
        name = _require_text(attribute, "deviation attribute")
        if name not in DEVIATION_IMPACT:
            raise ValueError("deviation %s has no declared qualification impact" % name)
        domains.update(DEVIATION_IMPACT[name])
    return tuple(sorted(domains))


def part_category(index, deviations, threshold):
    """Return the representativeness category earned by a fitted component."""
    if isinstance(index, bool) or not isinstance(index, (int, float)):
        raise ValueError("index must be a real number")
    value = float(index)
    if not math.isfinite(value) or value < 0.0 or value > 1.0:
        raise ValueError("index must lie in [0, 1], got %r" % (index,))
    if isinstance(threshold, bool) or not isinstance(threshold, (int, float)):
        raise ValueError("threshold must be a real number")
    limit = float(threshold)
    if not math.isfinite(limit) or limit < 0.0 or limit > 1.0:
        raise ValueError("threshold must lie in [0, 1], got %r" % (threshold,))
    if not isinstance(deviations, (list, tuple)):
        raise ValueError("deviations must be a sequence of attribute names")
    names = [_require_text(name, "deviation attribute") for name in deviations]
    if not names:
        return "representative"
    if any(name in FUNDAMENTAL_ATTRIBUTES for name in names):
        return "non-representative"
    if value > limit or math.isclose(value, limit, rel_tol=0.0, abs_tol=INDEX_TOLERANCE):
        return "partially-representative"
    return "non-representative"


def evaluate_component(item, weights=None, threshold=0.6):
    """Return the representativeness record of one fitted component.

    item keys: reference, fitted (mapping), intended (mapping), optional
    quantity (default 1).
    """
    if not isinstance(item, dict):
        raise ValueError("each component item must be a mapping")
    reference = _require_text(item.get("reference"), "reference")
    quantity = _require_positive_int(item.get("quantity", 1), "quantity")
    deviations = compare_component(item.get("fitted"), item.get("intended"), weights)
    index = representativeness_index(deviations, weights)
    domains = invalidated_domains(deviations)
    return {
        "reference": reference,
        "quantity": quantity,
        "deviations": deviations,
        "index": index,
        "invalidated_domains": domains,
        "category": part_category(index, deviations, threshold),
    }


def retest_set(records):
    """Return the qualification domains that have to be repeated on the flight build."""
    if not isinstance(records, (list, tuple)) or not records:
        raise ValueError("records must be a non-empty sequence of component records")
    domains = set()
    for record in records:
        if not isinstance(record, dict) or "invalidated_domains" not in record:
            raise ValueError("each record must carry 'invalidated_domains'")
        if record.get("category") == "representative":
            continue
        domains.update(record["invalidated_domains"])
    return tuple(sorted(domains))


def assess_eqm_representativeness(spec):
    """Run the full clause 4.1.6 engineering qualification model assessment.

    spec keys: components (sequence of items), optional weights, optional
    threshold (default 0.6).
    """
    if not isinstance(spec, dict):
        raise ValueError("spec must be a mapping")
    if "components" not in spec:
        raise ValueError("spec missing required key 'components'")
    components = spec["components"]
    if not isinstance(components, (list, tuple)) or not components:
        raise ValueError("spec['components'] must be a non-empty sequence")
    threshold = spec.get("threshold", 0.6)
    weights = validate_weights(spec.get("weights"))

    records = [evaluate_component(item, weights, threshold) for item in components]
    total_quantity = sum(record["quantity"] for record in records)
    model_index = (
        math.fsum(record["index"] * record["quantity"] for record in records) / total_quantity
    )
    counts = {category: 0 for category in PART_CATEGORIES}
    for record in records:
        counts[record["category"]] += 1
    domains = retest_set(records)

    findings = []
    for record in records:
        if record["category"] == "representative":
            continue
        findings.append(
            {
                "severity": _CATEGORY_SEVERITY[record["category"]],
                "reference": record["reference"],
                "detail": "%s deviates on %s; %s results do not transfer"
                % (
                    record["reference"],
                    ", ".join(record["deviations"]),
                    ", ".join(record["invalidated_domains"]),
                ),
            }
        )
    findings.sort(key=lambda item: (item["severity"], item["reference"]))

    if counts["non-representative"]:
        verdict = "not-transferable"
    elif counts["partially-representative"]:
        verdict = "transferable-with-retest"
    else:
        verdict = "transferable"
    return {
        "records": records,
        "model_index": model_index,
        "threshold": float(threshold),
        "category_counts": counts,
        "retest_domains": domains,
        "findings": findings,
        "verdict": verdict,
    }
