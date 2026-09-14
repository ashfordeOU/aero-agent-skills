"""Reduced evaluation campaign for commercial parts at the lowest assurance class.

Anchor: ECSS-Q-ST-60-13C clause 6.2.3.1 (the reduced evaluation that has to
prove a commercial part suitable when it is used at the lowest assurance
class). Paraphrased into an implementable procedure; no standard text is
reproduced.

Offline, deterministic, python3 standard library only.

Procedure implemented here
--------------------------
* The lowest assurance class does not delete the evaluation, it shrinks it.
  The campaign is still the full element set; what changes is how much of each
  element the programme is allowed to leave unproven.
* Each element carries a weight -- the share of the suitability argument it
  supplies -- and an extent, which says how far it was actually taken. An
  extent retains a fraction of the weight: performing the element in full
  retains all of it, a reduced run retains most, manufacturer-published data
  retains half, a same-family similarity argument retains a third, and an
  omission retains nothing.
* What is not retained is dropped weight, and the dropped weight is spent
  against a reduction allowance. The allowance is set by the environment the
  part has to survive: a benign environment buys a large reduction, a severe
  one almost none. Spending more than the allowance is an over-reduced
  campaign whatever the individual elements look like.
* Two elements are irreducible at any allowance, because they answer what the
  part is and who makes it, and nothing downstream means anything without
  them. A third, the radiation suitability review, is reducible only while the
  declared environment is benign.
* An element nobody mentioned is omitted silently, not excused. The full
  element set is graded every time, so a thin declaration cannot shrink the
  campaign it is measured against.
"""

from __future__ import annotations

import math

# Campaign elements and the share of the suitability argument each supplies.
ELEMENT_WEIGHTS = {
    "manufacturer-assessment": 1.0,
    "construction-and-technology-review": 1.0,
    "radiation-suitability-review": 0.9,
    "electrical-characterisation-over-temperature": 0.8,
    "environmental-stress-sample": 0.7,
    "endurance-sample": 0.7,
    "assembly-and-mounting-compatibility": 0.5,
    "materials-and-outgassing-review": 0.4,
}

# Elements no allowance reaches: they answer what the part is and who built it.
IRREDUCIBLE_ELEMENTS = (
    "manufacturer-assessment",
    "construction-and-technology-review",
)

# Reducible only while the declared environment stays benign.
ENVIRONMENT_GATED_ELEMENT = "radiation-suitability-review"

# Fraction of an element's weight each extent retains.
EXTENT_RETENTION = {
    "performed-in-full": 1.0,
    "performed-reduced": 0.6,
    "covered-by-manufacturer-data": 0.5,
    "covered-by-similar-part-family": 0.35,
    "omitted-with-rationale": 0.0,
    "omitted-silently": 0.0,
}

# Share of the total campaign weight the programme may leave unproven.
SEVERITY_ALLOWANCE = {
    "benign": 0.45,
    "moderate": 0.30,
    "severe": 0.15,
}

VERDICTS = (
    "reduced-evaluation-sufficient",
    "reduced-evaluation-conditional",
    "reduced-evaluation-over-reduced",
)

# Retention is a ratio of sums of products; a campaign that lands exactly on
# its allowance can miss it by a few units in the last place. The allowance
# itself is never widened by this tolerance.
WEIGHT_TOLERANCE = 1e-9


def _real(value, label):
    """Return ``value`` as a finite float or raise for anything else."""
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise ValueError("%s must be a real number, got %r" % (label, value))
    number = float(value)
    if not math.isfinite(number):
        raise ValueError("%s must be finite, got %r" % (label, value))
    return number


def element_weight(name):
    """Weight of one campaign element; unknown element names are rejected."""
    if name not in ELEMENT_WEIGHTS:
        raise ValueError(
            "unknown campaign element %r (known: %s)"
            % (name, ", ".join(sorted(ELEMENT_WEIGHTS)))
        )
    return ELEMENT_WEIGHTS[name]


def extent_retention(extent):
    """Fraction of an element's weight the declared extent retains."""
    if extent not in EXTENT_RETENTION:
        raise ValueError(
            "unknown element extent %r (known: %s)"
            % (extent, ", ".join(sorted(EXTENT_RETENTION)))
        )
    return EXTENT_RETENTION[extent]


def severity_allowance(severity):
    """Share of the campaign weight the declared environment lets go unproven."""
    if severity not in SEVERITY_ALLOWANCE:
        raise ValueError(
            "unknown environment severity %r (known: %s)"
            % (severity, ", ".join(sorted(SEVERITY_ALLOWANCE)))
        )
    return SEVERITY_ALLOWANCE[severity]


def normalize_element(raw):
    """Validate one element declaration and fill in its defaults."""
    if not isinstance(raw, dict):
        raise ValueError("element must be a mapping, got %r" % (type(raw).__name__,))
    name = raw.get("element")
    element_weight(name)  # validation only
    extent = raw.get("extent", "omitted-silently")
    extent_retention(extent)  # validation only
    return {"element": name, "extent": extent}


def assess_element(raw, severity):
    """Grade one element into retained weight, dropped weight and findings."""
    entry = normalize_element(raw)
    allowance = severity_allowance(severity)  # validation only
    del allowance
    name = entry["element"]
    extent = entry["extent"]
    weight = element_weight(name)
    retention = extent_retention(extent)
    findings = []
    blocking = False
    if name in IRREDUCIBLE_ELEMENTS and retention < 1.0 - WEIGHT_TOLERANCE:
        findings.append("irreducible-element-reduced")
        blocking = True
    if (
        name == ENVIRONMENT_GATED_ELEMENT
        and severity != "benign"
        and retention < 1.0 - WEIGHT_TOLERANCE
    ):
        findings.append("environment-gated-element-reduced")
        blocking = True
    if extent == "omitted-silently":
        findings.append("element-omitted-without-rationale")
        blocking = True
    elif extent == "omitted-with-rationale":
        findings.append("element-omitted-under-rationale")
    elif extent == "covered-by-similar-part-family":
        findings.append("part-family-similarity-credit-taken")
    elif extent == "covered-by-manufacturer-data":
        findings.append("manufacturer-data-credit-taken")
    elif extent == "performed-reduced":
        findings.append("element-run-in-reduced-extent")
    return {
        "element": name,
        "extent": extent,
        "weight": weight,
        "retention": retention,
        "retained_weight": weight * retention,
        "dropped_weight": weight * (1.0 - retention),
        "findings": findings,
        "blocking": blocking,
    }


def reduction_budget(total_weight, severity):
    """Weight the programme may leave unproven at this environment severity."""
    total = _real(total_weight, "total_weight")
    if total <= 0.0:
        raise ValueError("total_weight must be positive, got %r" % (total_weight,))
    return total * severity_allowance(severity)


def retained_fraction(records):
    """Retained weight of a set of graded elements over the total weight."""
    if not isinstance(records, (list, tuple)):
        raise ValueError(
            "records must be a list or tuple, got %r" % (type(records).__name__,)
        )
    if len(records) == 0:
        raise ValueError("a campaign must carry at least one element")
    total_weight = 0.0
    retained = 0.0
    for record in records:
        total_weight += _real(record["weight"], "weight")
        retained += _real(record["retained_weight"], "retained_weight")
    if total_weight <= 0.0:
        raise ValueError("total campaign weight must be positive")
    return retained / total_weight


def assess_reduced_campaign(part_id, severity, elements):
    """Grade the reduced evaluation standing behind one commercial part type.

    Every element the reduced campaign owes is graded, including the ones the
    declaration left out entirely -- an element nobody mentioned is omitted
    silently, not excused.
    """
    if not isinstance(part_id, str) or not part_id.strip():
        raise ValueError("part_id must be a non-empty string, got %r" % (part_id,))
    severity_allowance(severity)  # validation only
    if not isinstance(elements, (list, tuple)):
        raise ValueError(
            "elements must be a list or tuple, got %r" % (type(elements).__name__,)
        )
    declared = {}
    for raw in elements:
        entry = normalize_element(raw)
        if entry["element"] in declared:
            raise ValueError("duplicate campaign element %r" % (entry["element"],))
        declared[entry["element"]] = entry
    records = []
    for name in sorted(ELEMENT_WEIGHTS):
        records.append(
            assess_element(
                declared.get(name, {"element": name, "extent": "omitted-silently"}),
                severity,
            )
        )
    total_weight = sum(record["weight"] for record in records)
    dropped_weight = sum(record["dropped_weight"] for record in records)
    allowance = reduction_budget(total_weight, severity)
    findings = []
    blocking = False
    for record in records:
        if record["blocking"]:
            blocking = True
        for finding in record["findings"]:
            findings.append({"element": record["element"], "finding": finding})
    over_budget = dropped_weight > allowance + WEIGHT_TOLERANCE
    if over_budget:
        findings.append(
            {"element": "campaign", "finding": "reduction-allowance-exceeded"}
        )
    if over_budget or blocking:
        verdict = "reduced-evaluation-over-reduced"
    elif findings:
        verdict = "reduced-evaluation-conditional"
    else:
        verdict = "reduced-evaluation-sufficient"
    return {
        "part_id": part_id,
        "environment_severity": severity,
        "records": records,
        "total_weight": total_weight,
        "dropped_weight": dropped_weight,
        "reduction_allowance": allowance,
        "retained_fraction": retained_fraction(records),
        "allowance_exceeded": over_budget,
        "findings": findings,
        "verdict": verdict,
        "suitable_at_class_3": verdict != "reduced-evaluation-over-reduced",
    }
