#!/usr/bin/env python3
"""Acceptance criteria for solar cell assembly flatness.

Anchor: ECSS-E-ST-20-08C clause 6.4.3.17.3 -- the measured deflection is
accepted when it stays below the limiting value defined for the geometry of
the assembly. The procedure below is a paraphrase into implementable steps; no
standard text is reproduced.

What the criterion actually is
------------------------------
The limit is not one number for every part. A long assembly is allowed to
stand off its seating plane further than a short one, because the same radius
of curvature spends more standoff over a longer span; a very small assembly
still needs a floor, because below some standoff nothing can be measured
apart from the tooling; and no assembly is allowed an unbounded standoff
however long it is, because the panel stack height and the bond line run out.
A limit derived from the span with a floor and a ceiling captures all three.

Where a control drawing states a limit for the part, that stated limit governs
and the derived envelope becomes a cross check. A drawing that states a limit
above the derived envelope is not wrong by construction, but it is a decision
somebody made and it is reported rather than absorbed.

A measured deflection arrives with an uncertainty. Three outcomes follow, not
two:

    accepted   the deflection and its whole guard band stay at or under the
               limit, so no rounding of the measurement can cross it

    marginal   the bare deflection is at or under the limit but the guard band
               crosses it, so the part passes only if the instrument is
               believed exactly

    rejected   the bare deflection is already over the limit

The boundary belongs to the passing side: a deflection landing exactly on its
limit is accepted, and the comparison tolerance absorbs representation error
rather than moving the limit.
"""

import math

__all__ = [
    "DEFAULT_FLATNESS_CRITERIA_POLICY",
    "SAMPLE_ACCEPTED",
    "SAMPLE_MARGINAL",
    "SAMPLE_REJECTED",
    "LOT_UNDERSIZED",
    "LOT_REJECTED",
    "LOT_REFERRED",
    "LOT_ACCEPTED",
    "PROVENANCE_DRAWING",
    "PROVENANCE_DERIVED",
    "validate_policy",
    "validate_geometry",
    "characteristic_span",
    "derive_flatness_limit",
    "resolve_governing_limit",
    "sentence_sample",
    "assess_flatness_criteria",
]

# A declared policy, not a physical constant: a project substitutes its own.
# The derived limit is slope * span, held between a floor and a ceiling.
DEFAULT_FLATNESS_CRITERIA_POLICY = {
    "slope_um_per_mm": 1.0,
    "floor_um": 50.0,
    "ceiling_um": 250.0,
    "min_subgroup_samples": 4,
}

SAMPLE_ACCEPTED = "flatness-accepted"
SAMPLE_MARGINAL = "flatness-marginal"
SAMPLE_REJECTED = "flatness-rejected"

LOT_UNDERSIZED = "lot-undersized"
LOT_REJECTED = "lot-rejected"
LOT_REFERRED = "lot-referred"
LOT_ACCEPTED = "lot-accepted"

PROVENANCE_DRAWING = "drawing-stated"
PROVENANCE_DERIVED = "geometry-derived"

_REL_TOL = 1e-9


def _real(value, label):
    """Return a finite float or raise."""
    if not isinstance(value, (int, float)) or isinstance(value, bool):
        raise ValueError("%s must be a real number" % label)
    value = float(value)
    if not math.isfinite(value):
        raise ValueError("%s must be finite" % label)
    return value


def _positive(value, label):
    """Return a finite, strictly positive float or raise."""
    value = _real(value, label)
    if value <= 0.0:
        raise ValueError("%s must be positive: %g" % (label, value))
    return value


def _non_negative(value, label):
    """Return a finite, non-negative float or raise."""
    value = _real(value, label)
    if value < 0.0:
        raise ValueError("%s must not be negative: %g" % (label, value))
    return value


def _at_most(value, bound):
    """Return True when value is at or below bound, equality included."""
    if math.isclose(value, bound, rel_tol=_REL_TOL, abs_tol=0.0):
        return True
    return value < bound


def validate_policy(policy=None):
    """Return a validated acceptance policy, defaults filled in."""
    if policy is None:
        policy = {}
    if not isinstance(policy, dict):
        raise ValueError("policy must be a mapping")
    for key in policy:
        if key not in DEFAULT_FLATNESS_CRITERIA_POLICY:
            raise ValueError("unrecognised acceptance policy key: %s" % key)
    merged = dict(DEFAULT_FLATNESS_CRITERIA_POLICY)
    for key in ("slope_um_per_mm", "floor_um", "ceiling_um"):
        if key in policy:
            merged[key] = _positive(policy[key], key)
    if "min_subgroup_samples" in policy:
        floor = policy["min_subgroup_samples"]
        if not isinstance(floor, int) or isinstance(floor, bool) or floor < 1:
            raise ValueError("min_subgroup_samples must be a positive integer")
        merged["min_subgroup_samples"] = floor
    if merged["ceiling_um"] < merged["floor_um"]:
        raise ValueError("ceiling_um must not sit below floor_um")
    return merged


def validate_geometry(geometry):
    """Return the validated assembly geometry in millimetres."""
    if not isinstance(geometry, dict):
        raise ValueError("geometry must be a mapping")
    for key in ("length_mm", "width_mm"):
        if key not in geometry:
            raise ValueError("geometry is missing '%s'" % key)
    return {
        "length_mm": _positive(geometry["length_mm"], "length_mm"),
        "width_mm": _positive(geometry["width_mm"], "width_mm"),
    }


def characteristic_span(geometry):
    """Return the diagonal span of the assembly in millimetres."""
    geometry = validate_geometry(geometry)
    length = geometry["length_mm"]
    width = geometry["width_mm"]
    # sqrt is correctly rounded under IEEE 754, so the span is reproducible on
    # every platform the suite runs on.
    return math.sqrt(length * length + width * width)


def derive_flatness_limit(geometry, policy=None):
    """Return the limiting deflection the assembly geometry defines."""
    policy = validate_policy(policy)
    span = characteristic_span(geometry)
    raw = policy["slope_um_per_mm"] * span
    limit = raw
    binding = "span"
    if limit < policy["floor_um"]:
        limit = policy["floor_um"]
        binding = "floor"
    if limit > policy["ceiling_um"]:
        limit = policy["ceiling_um"]
        binding = "ceiling"
    return {
        "span_mm": span,
        "raw_limit_um": raw,
        "limit_um": limit,
        "binding_term": binding,
    }


def resolve_governing_limit(geometry, drawing_limit_um=None, policy=None):
    """Return the limit that governs, with its provenance and any finding."""
    policy = validate_policy(policy)
    derived = derive_flatness_limit(geometry, policy)
    findings = []
    if drawing_limit_um is None:
        governing = derived["limit_um"]
        provenance = PROVENANCE_DERIVED
    else:
        governing = _positive(drawing_limit_um, "drawing_limit_um")
        provenance = PROVENANCE_DRAWING
        if not _at_most(governing, derived["limit_um"]):
            findings.append(
                "the drawing-stated limit of %.3f um sits above the envelope of "
                "%.3f um the assembly geometry derives, so the allowance is a "
                "decision that has to be traceable rather than a default"
                % (governing, derived["limit_um"])
            )
    return {
        "governing_limit_um": governing,
        "provenance": provenance,
        "derived": derived,
        "findings": findings,
    }


def sentence_sample(deflection_um, uncertainty_um, limit_um):
    """Return the disposition of one measured deflection against its limit."""
    deflection = _non_negative(deflection_um, "deflection_um")
    uncertainty = _non_negative(uncertainty_um, "uncertainty_um")
    limit = _positive(limit_um, "limit_um")
    guarded = deflection + uncertainty
    if not _at_most(deflection, limit):
        disposition = SAMPLE_REJECTED
    elif _at_most(guarded, limit):
        disposition = SAMPLE_ACCEPTED
    else:
        disposition = SAMPLE_MARGINAL
    return {
        "deflection_um": deflection,
        "uncertainty_um": uncertainty,
        "guard_banded_um": guarded,
        "limit_um": limit,
        "margin_um": limit - deflection,
        "disposition": disposition,
    }


def assess_flatness_criteria(spec):
    """Run the full clause 6.4.3.17.3 acceptance assessment.

    spec keys: geometry, samples; optional drawing_limit_um and policy.
    Each sample is {sample_id, max_deflection_um, uncertainty_um}.
    """
    if not isinstance(spec, dict):
        raise ValueError("spec must be a mapping")
    for key in ("geometry", "samples"):
        if key not in spec:
            raise ValueError("spec missing required key '%s'" % key)
    policy = validate_policy(spec.get("policy"))
    geometry = validate_geometry(spec["geometry"])
    resolved = resolve_governing_limit(geometry, spec.get("drawing_limit_um"), policy)
    limit = resolved["governing_limit_um"]

    samples = spec["samples"]
    if not isinstance(samples, (list, tuple)) or not samples:
        raise ValueError("samples must be a non-empty sequence")

    sentenced = []
    seen = set()
    for index, sample in enumerate(samples):
        if not isinstance(sample, dict):
            raise ValueError("sample %d must be a mapping" % index)
        for key in ("sample_id", "max_deflection_um", "uncertainty_um"):
            if key not in sample:
                raise ValueError("sample %d is missing '%s'" % (index, key))
        sample_id = sample["sample_id"]
        if not isinstance(sample_id, str) or not sample_id.strip():
            raise ValueError("sample %d has no usable identifier" % index)
        if sample_id in seen:
            raise ValueError("sample identifier repeated: %s" % sample_id)
        seen.add(sample_id)
        result = sentence_sample(
            sample["max_deflection_um"], sample["uncertainty_um"], limit
        )
        result["sample_id"] = sample_id
        sentenced.append(result)

    findings = list(resolved["findings"])
    rejected = [r for r in sentenced if r["disposition"] == SAMPLE_REJECTED]
    marginal = [r for r in sentenced if r["disposition"] == SAMPLE_MARGINAL]

    if len(sentenced) < policy["min_subgroup_samples"]:
        verdict = LOT_UNDERSIZED
        findings.append(
            "the record carries %d samples against a subgroup floor of %d, so it "
            "cannot speak for the lot whatever it measured"
            % (len(sentenced), policy["min_subgroup_samples"])
        )
    elif rejected:
        verdict = LOT_REJECTED
        for result in rejected:
            findings.append(
                "%s deflects %.3f um against a limit of %.3f um"
                % (result["sample_id"], result["deflection_um"], limit)
            )
    elif marginal:
        verdict = LOT_REFERRED
        for result in marginal:
            findings.append(
                "%s deflects %.3f um inside a limit of %.3f um, but its guard band "
                "reaches %.3f um" % (
                    result["sample_id"],
                    result["deflection_um"],
                    limit,
                    result["guard_banded_um"],
                )
            )
    else:
        verdict = LOT_ACCEPTED

    worst = max(sentenced, key=lambda r: r["guard_banded_um"])
    return {
        "verdict": verdict,
        "governing_limit_um": limit,
        "provenance": resolved["provenance"],
        "derived_limit_um": resolved["derived"]["limit_um"],
        "binding_term": resolved["derived"]["binding_term"],
        "span_mm": resolved["derived"]["span_mm"],
        "sample_count": len(sentenced),
        "rejected_ids": [r["sample_id"] for r in rejected],
        "marginal_ids": [r["sample_id"] for r in marginal],
        "worst_sample_id": worst["sample_id"],
        "worst_guard_banded_um": worst["guard_banded_um"],
        "samples": sentenced,
        "findings": findings,
    }
