#!/usr/bin/env python3
"""Dimensional inspection of additively manufactured parts.

Anchor: ECSS-Q-ST-70-80C, Inspection -- the dimensional half, including
the first-article check that opens a part number. The procedure below
is a paraphrase into implementable steps; no standard text is
reproduced.

A built part reaches its dimensions through a shrinking, distorting
thermal history and a surface that is rough before anything is
machined. Three questions follow, and this module answers them in
order:

    can the instrument see the tolerance?
        expanded measurement uncertainty against the tolerance band,
        and the guard band that uncertainty forces on the acceptance
        limits

    is the feature conforming?
        the measured value against the guarded limits, with an
        indeterminate zone between the guarded and the drawing limits
        rather than a coin toss

    how much has to be measured?
        every feature on a first article; on production, the features
        whose demonstrated process capability does not earn a reduced
        check

Standard library only, offline, deterministic.
"""

from __future__ import annotations

import math

FEATURE_CRITICALITIES = ("critical", "interface", "standard")
STAGES = ("first-article", "production")

CAPABLE = "capable"
CONDITIONAL = "conditionally-capable"
NOT_CAPABLE = "not-capable"

CONFORMING = "conforming"
NON_CONFORMING = "non-conforming"
INDETERMINATE = "indeterminate"

DEFAULT_DIMENSIONAL_POLICY = {
    "capable_ratio": 0.10,
    "conditional_ratio": 0.25,
    "coverage_factor": 2.0,
    "reduced_check_cpk": 1.33,
    "min_first_article_features": 1,
    "always_measured": ("critical", "interface"),
    "production_sample_fraction": 0.2,
}

_REL_TOL = 1e-9
_ABS_TOL = 1e-12


def _is_finite_number(value):
    return (
        isinstance(value, (int, float))
        and not isinstance(value, bool)
        and math.isfinite(value)
    )


def _require_positive(name, value):
    if not _is_finite_number(value):
        raise ValueError("%s must be a finite number, got %r" % (name, value))
    if value <= 0.0:
        raise ValueError("%s must be greater than zero, got %r" % (name, value))
    return float(value)


def _require_non_negative(name, value):
    if not _is_finite_number(value):
        raise ValueError("%s must be a finite number, got %r" % (name, value))
    if value < 0.0:
        raise ValueError("%s must not be negative, got %r" % (name, value))
    return float(value)


def _require_number(name, value):
    if not _is_finite_number(value):
        raise ValueError("%s must be a finite number, got %r" % (name, value))
    return float(value)


def _require_choice(name, value, allowed):
    if value not in allowed:
        raise ValueError(
            "%s must be one of %s, got %r" % (name, ", ".join(allowed), value)
        )
    return value


def _at_least(value, limit):
    """value >= limit, absorbing floating-point representation error."""
    return value >= limit or math.isclose(
        value, limit, rel_tol=_REL_TOL, abs_tol=_ABS_TOL
    )


def _at_most(value, limit):
    """value <= limit, absorbing floating-point representation error."""
    return value <= limit or math.isclose(
        value, limit, rel_tol=_REL_TOL, abs_tol=_ABS_TOL
    )


def validate_dimensional_policy(policy):
    """Check an inspection policy has sane, ordered thresholds."""
    if not isinstance(policy, dict):
        raise ValueError("policy must be a mapping, got %r" % (policy,))
    capable = _require_positive("capable_ratio", policy.get("capable_ratio"))
    conditional = _require_positive(
        "conditional_ratio", policy.get("conditional_ratio")
    )
    if conditional <= capable:
        raise ValueError("conditional_ratio must sit above capable_ratio")
    if conditional >= 1.0:
        raise ValueError("conditional_ratio must stay below one")
    _require_positive("coverage_factor", policy.get("coverage_factor"))
    _require_positive("reduced_check_cpk", policy.get("reduced_check_cpk"))
    fraction = _require_non_negative(
        "production_sample_fraction", policy.get("production_sample_fraction")
    )
    if fraction > 1.0:
        raise ValueError("production_sample_fraction exceeds one")
    always = policy.get("always_measured")
    if not isinstance(always, (list, tuple)) or not always:
        raise ValueError("policy always_measured must be a non-empty sequence")
    for entry in always:
        _require_choice("always_measured entry", entry, FEATURE_CRITICALITIES)
    return policy


def tolerance_band_mm(lower_limit_mm, upper_limit_mm):
    """Width of the drawing tolerance band."""
    lower = _require_number("lower_limit_mm", lower_limit_mm)
    upper = _require_number("upper_limit_mm", upper_limit_mm)
    if upper <= lower:
        raise ValueError(
            "upper_limit_mm %g does not exceed lower_limit_mm %g; the band is empty"
            % (upper, lower)
        )
    return upper - lower


def expanded_uncertainty_mm(
    repeatability_mm, reproducibility_mm, coverage_factor=None, policy=None
):
    """Expanded measurement uncertainty from the two variation sources.

    Repeatability (one operator, one setup) and reproducibility (setup
    to setup, operator to operator) are independent, so they combine in
    quadrature before the coverage factor is applied.
    """
    policy = DEFAULT_DIMENSIONAL_POLICY if policy is None else policy
    validate_dimensional_policy(policy)
    repeatability = _require_non_negative("repeatability_mm", repeatability_mm)
    reproducibility = _require_non_negative("reproducibility_mm", reproducibility_mm)
    if repeatability == 0.0 and reproducibility == 0.0:
        raise ValueError(
            "a measurement with no repeatability and no reproducibility "
            "component has not been characterized"
        )
    factor = (
        policy["coverage_factor"] if coverage_factor is None else coverage_factor
    )
    factor = _require_positive("coverage_factor", factor)
    combined = math.sqrt(repeatability * repeatability + reproducibility * reproducibility)
    return factor * combined


def capability_ratio(expanded_uncertainty_mm_value, tolerance_band):
    """Share of the tolerance band consumed by measurement uncertainty."""
    uncertainty = _require_non_negative(
        "expanded_uncertainty_mm", expanded_uncertainty_mm_value
    )
    band = _require_positive("tolerance_band", tolerance_band)
    return uncertainty / band


def capability_category(ratio, policy=None):
    """Group a measurement capability ratio against the declared bands."""
    policy = DEFAULT_DIMENSIONAL_POLICY if policy is None else policy
    validate_dimensional_policy(policy)
    value = _require_non_negative("ratio", ratio)
    if _at_most(value, policy["capable_ratio"]):
        return CAPABLE
    if _at_most(value, policy["conditional_ratio"]):
        return CONDITIONAL
    return NOT_CAPABLE


def guarded_limits_mm(lower_limit_mm, upper_limit_mm, expanded_uncertainty_mm_value):
    """Acceptance limits pulled in by the measurement uncertainty.

    Acceptance has to be decided inside the drawing limits by at least
    the uncertainty, or a part outside the drawing can be accepted on a
    reading that happens to fall inside it.
    """
    band = tolerance_band_mm(lower_limit_mm, upper_limit_mm)
    uncertainty = _require_non_negative(
        "expanded_uncertainty_mm", expanded_uncertainty_mm_value
    )
    if 2.0 * uncertainty >= band:
        raise ValueError(
            "an uncertainty of %g mm consumes the %g mm tolerance band; no "
            "acceptance zone survives the guard band" % (uncertainty, band)
        )
    return (
        _require_number("lower_limit_mm", lower_limit_mm) + uncertainty,
        _require_number("upper_limit_mm", upper_limit_mm) - uncertainty,
    )


def process_capability_index(lower_limit_mm, upper_limit_mm, process_sigma_mm):
    """Spread-only capability of the build and post-process route."""
    band = tolerance_band_mm(lower_limit_mm, upper_limit_mm)
    sigma = _require_positive("process_sigma_mm", process_sigma_mm)
    return band / (6.0 * sigma)


def centred_capability_index(
    lower_limit_mm, upper_limit_mm, process_mean_mm, process_sigma_mm
):
    """Capability with the offset of the mean taken into account."""
    lower = _require_number("lower_limit_mm", lower_limit_mm)
    upper = _require_number("upper_limit_mm", upper_limit_mm)
    tolerance_band_mm(lower, upper)
    mean = _require_number("process_mean_mm", process_mean_mm)
    sigma = _require_positive("process_sigma_mm", process_sigma_mm)
    return min(upper - mean, mean - lower) / (3.0 * sigma)


def evaluate_feature(feature, policy=None):
    """Conformance verdict for one measured feature, guard band included."""
    policy = DEFAULT_DIMENSIONAL_POLICY if policy is None else policy
    validate_dimensional_policy(policy)
    if not isinstance(feature, dict):
        raise ValueError("feature must be a mapping, got %r" % (feature,))
    name = feature.get("name")
    if not isinstance(name, str) or not name.strip():
        raise ValueError("feature name must be a non-empty string")
    criticality = _require_choice(
        "criticality", feature.get("criticality"), FEATURE_CRITICALITIES
    )
    lower = _require_number("lower_limit_mm", feature.get("lower_limit_mm"))
    upper = _require_number("upper_limit_mm", feature.get("upper_limit_mm"))
    band = tolerance_band_mm(lower, upper)
    uncertainty = expanded_uncertainty_mm(
        feature.get("repeatability_mm"),
        feature.get("reproducibility_mm"),
        policy=policy,
    )
    ratio = capability_ratio(uncertainty, band)
    category = capability_category(ratio, policy)
    findings = []
    if category == NOT_CAPABLE:
        findings.append(
            "%s: uncertainty takes %.1f%% of the tolerance band; the "
            "instrument cannot decide this feature" % (name, 100.0 * ratio)
        )
    guard_low, guard_high = guarded_limits_mm(lower, upper, uncertainty)
    measured = feature.get("measured_mm")
    if measured is None:
        verdict = INDETERMINATE
        findings.append("%s: no measured value supplied; the feature is open" % name)
        measured_value = None
    else:
        measured_value = _require_number("measured_mm", measured)
        inside_drawing = _at_least(measured_value, lower) and _at_most(
            measured_value, upper
        )
        inside_guard = _at_least(measured_value, guard_low) and _at_most(
            measured_value, guard_high
        )
        if inside_guard:
            verdict = CONFORMING
        elif inside_drawing:
            verdict = INDETERMINATE
            findings.append(
                "%s: %.4f mm sits in the guard band; re-measure or accept the "
                "risk explicitly" % (name, measured_value)
            )
        else:
            verdict = NON_CONFORMING
            findings.append(
                "%s: %.4f mm is outside the drawing limits %.4f to %.4f mm"
                % (name, measured_value, lower, upper)
            )
    return {
        "name": name,
        "criticality": criticality,
        "tolerance_band_mm": band,
        "expanded_uncertainty_mm": uncertainty,
        "capability_ratio": ratio,
        "capability": category,
        "guarded_lower_mm": guard_low,
        "guarded_upper_mm": guard_high,
        "measured_mm": measured_value,
        "verdict": verdict,
        "findings": findings,
    }


def reduced_check_allowed(feature, policy=None):
    """Whether demonstrated capability earns this feature a reduced check."""
    policy = DEFAULT_DIMENSIONAL_POLICY if policy is None else policy
    validate_dimensional_policy(policy)
    if not isinstance(feature, dict):
        raise ValueError("feature must be a mapping, got %r" % (feature,))
    criticality = _require_choice(
        "criticality", feature.get("criticality"), FEATURE_CRITICALITIES
    )
    if criticality in tuple(policy["always_measured"]):
        return {"allowed": False, "reason": "%s features are always measured" % criticality}
    mean = feature.get("process_mean_mm")
    sigma = feature.get("process_sigma_mm")
    if mean is None or sigma is None:
        return {
            "allowed": False,
            "reason": "no demonstrated capability; the first article has not "
            "established a mean and a spread",
        }
    cpk = centred_capability_index(
        feature.get("lower_limit_mm"), feature.get("upper_limit_mm"), mean, sigma
    )
    allowed = _at_least(cpk, policy["reduced_check_cpk"])
    return {
        "allowed": allowed,
        "cpk": cpk,
        "reason": "demonstrated centred capability %.3f against %.3f"
        % (cpk, policy["reduced_check_cpk"]),
    }


def inspection_scope(features, stage, policy=None):
    """Which features are measured at this stage, and why."""
    policy = DEFAULT_DIMENSIONAL_POLICY if policy is None else policy
    validate_dimensional_policy(policy)
    _require_choice("stage", stage, STAGES)
    if not isinstance(features, (list, tuple)) or not features:
        raise ValueError("features must be a non-empty sequence")
    measured = []
    reduced = []
    for feature in features:
        if not isinstance(feature, dict):
            raise ValueError("each feature must be a mapping, got %r" % (feature,))
        name = feature.get("name")
        if not isinstance(name, str) or not name.strip():
            raise ValueError("feature name must be a non-empty string")
        if stage == "first-article":
            measured.append(name)
            continue
        decision = reduced_check_allowed(feature, policy)
        if decision["allowed"]:
            reduced.append(name)
        else:
            measured.append(name)
    if stage == "first-article" and len(measured) < policy["min_first_article_features"]:
        raise ValueError("a first article must measure at least one feature")
    return {
        "stage": stage,
        "measured": measured,
        "reduced": reduced,
        "measured_fraction": len(measured) / float(len(features)),
    }


def assess_dimensional_inspection(case, policy=None):
    """Full dimensional inspection verdict for one part at one stage."""
    policy = DEFAULT_DIMENSIONAL_POLICY if policy is None else policy
    validate_dimensional_policy(policy)
    if not isinstance(case, dict):
        raise ValueError("case must be a mapping, got %r" % (case,))
    stage = _require_choice("stage", case.get("stage"), STAGES)
    features = case.get("features")
    if not isinstance(features, (list, tuple)) or not features:
        raise ValueError("case features must be a non-empty sequence")
    scope = inspection_scope(features, stage, policy)
    results = []
    findings = []
    for feature in features:
        if feature.get("name") not in scope["measured"]:
            continue
        evaluated = evaluate_feature(feature, policy)
        findings.extend(evaluated["findings"])
        results.append(evaluated)
    non_conforming = [r["name"] for r in results if r["verdict"] == NON_CONFORMING]
    indeterminate = [r["name"] for r in results if r["verdict"] == INDETERMINATE]
    not_capable = [r["name"] for r in results if r["capability"] == NOT_CAPABLE]
    if non_conforming:
        verdict = "dimensionally-non-conforming"
        compliant = False
    elif indeterminate or not_capable:
        verdict = "dimensionally-open"
        compliant = False
    else:
        verdict = "dimensionally-conforming"
        compliant = True
    return {
        "stage": stage,
        "scope": scope,
        "features": results,
        "non_conforming": non_conforming,
        "indeterminate": indeterminate,
        "not_capable": not_capable,
        "compliant": compliant,
        "verdict": verdict,
        "findings": findings,
    }
