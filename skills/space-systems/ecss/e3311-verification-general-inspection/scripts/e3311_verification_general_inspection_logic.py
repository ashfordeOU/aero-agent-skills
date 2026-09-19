#!/usr/bin/env python3
"""Verification strategy and inspection for explosive hardware.

Anchor: ECSS-E-ST-33-11C clauses 4.14.1 and 4.14.2. The procedure below
is a paraphrase into implementable steps; no standard text is reproduced.

Explosive hardware breaks the usual verification chain: the test that
proves an initiator fires consumes it, so the article that flies is
never the article that was tested. Every piece of evidence therefore
carries the article it came from.

Requirement kind -> method, article
    function      test; on a lot sample when the item is one-shot, with a
                  companion inspection inherited by the flight article
    performance   test; on a lot sample when the demonstration destroys it
    interface     inspection on the flight article
    workmanship   inspection on the flight article
    material      analysis, with review of design where heritage exists
    marking       inspection on the flight article

Sample size is a property of the lot: a fraction, rounded up, clamped
between a floor and a ceiling, and never the whole lot. Inspection
coverage is graded with no exemption for a critical characteristic.

Standard library only, offline, deterministic.
"""

from __future__ import annotations

import math

VERIFICATION_METHODS = ("test", "analysis", "review-of-design", "inspection")
REQUIREMENT_KINDS = (
    "function",
    "performance",
    "interface",
    "workmanship",
    "material",
    "marking",
)
ARTICLES = ("flight-article", "lot-sample")

MATRIX_CLOSED = "verification-closed"
MATRIX_OPEN = "verification-open"
COVERAGE_MET = "inspection-coverage-met"
COVERAGE_NOT_MET = "inspection-coverage-not-met"

DEFAULT_VERIFICATION_POLICY = {
    "lot_sample_fraction": 0.10,
    "min_lot_sample": 2,
    "max_lot_sample": 10,
    "min_inspection_coverage": 0.95,
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


def _require_choice(name, value, allowed):
    if value not in allowed:
        raise ValueError(
            "%s must be one of %s, got %r" % (name, ", ".join(allowed), value)
        )
    return value


def _require_flag(name, value):
    if not isinstance(value, bool):
        raise ValueError("%s must be true or false, got %r" % (name, value))
    return value


def _require_count(name, value, minimum=1):
    if isinstance(value, bool) or not isinstance(value, int):
        raise ValueError("%s must be a whole number, got %r" % (name, value))
    if value < minimum:
        raise ValueError("%s must be at least %d, got %r" % (name, minimum, value))
    return value


def _at_least(value, limit):
    """value >= limit, absorbing floating-point representation error.

    A coverage fraction is a quotient of counts, so a case that sits
    exactly on the threshold can land a few units in the last place
    below it. The threshold is never lowered; only the comparison
    tolerates the representation error.
    """
    return value >= limit or math.isclose(
        value, limit, rel_tol=_REL_TOL, abs_tol=_ABS_TOL
    )


def validate_verification_policy(policy):
    """Check a verification policy carries a usable sampling rule."""
    if not isinstance(policy, dict):
        raise ValueError("policy must be a mapping, got %r" % (policy,))
    fraction = _require_positive("lot_sample_fraction", policy.get("lot_sample_fraction"))
    if fraction >= 1.0:
        raise ValueError(
            "policy lot_sample_fraction must be below unity; a sample that "
            "takes the whole lot leaves nothing to fly"
        )
    floor = _require_count("min_lot_sample", policy.get("min_lot_sample"))
    ceiling = _require_count("max_lot_sample", policy.get("max_lot_sample"))
    if ceiling < floor:
        raise ValueError("policy max_lot_sample is below min_lot_sample")
    coverage = _require_positive(
        "min_inspection_coverage", policy.get("min_inspection_coverage")
    )
    if coverage > 1.0:
        raise ValueError(
            "policy min_inspection_coverage must not exceed unity, got %r"
            % (policy.get("min_inspection_coverage"),)
        )
    return policy


def select_verification_method(
    requirement_kind,
    destructive_demonstration=False,
    one_shot_device=False,
    heritage_available=False,
):
    """Pick the method, the article it applies to, and any companion duty."""
    _require_choice("requirement_kind", requirement_kind, REQUIREMENT_KINDS)
    destructive = _require_flag(
        "destructive_demonstration", destructive_demonstration
    )
    one_shot = _require_flag("one_shot_device", one_shot_device)
    heritage = _require_flag("heritage_available", heritage_available)
    companions = []
    if requirement_kind in ("function", "performance"):
        method = "test"
        if destructive or one_shot:
            article = "lot-sample"
            companions.append("inspection")
            rationale = (
                "the demonstration consumes the article, so the test moves onto "
                "a lot sample and the flight article inherits an inspection that "
                "confirms lot identity"
            )
        else:
            article = "flight-article"
            rationale = (
                "the demonstration leaves the article usable, so the flight unit "
                "is tested directly"
            )
    elif requirement_kind == "material":
        method = "review-of-design" if heritage else "analysis"
        article = "flight-article"
        rationale = (
            "a material property is closed on records rather than on a firing; "
            "qualified heritage carries it by review of design"
            if heritage
            else "a material property is closed by analysis of the declared data"
        )
    else:
        method = "inspection"
        article = "flight-article"
        rationale = (
            "an interface, workmanship or marking requirement is observable on "
            "the flight article without consuming it"
        )
    return {
        "requirement_kind": requirement_kind,
        "method": method,
        "article": article,
        "companion_methods": companions,
        "rationale": rationale,
    }


def lot_sample_size(lot_size, policy=DEFAULT_VERIFICATION_POLICY):
    """Units to draw from a lot for a destructive demonstration."""
    validate_verification_policy(policy)
    lot = _require_count("lot_size", lot_size)
    raw = math.ceil(lot * policy["lot_sample_fraction"])
    sample = max(policy["min_lot_sample"], min(policy["max_lot_sample"], raw))
    if sample >= lot:
        raise ValueError(
            "a sample of %d from a lot of %d consumes the lot; the lot is too "
            "small for a destructive demonstration" % (sample, lot)
        )
    return sample


def inspection_coverage(characteristics, policy=DEFAULT_VERIFICATION_POLICY):
    """Grade inspection coverage, with no exemption for a critical item."""
    validate_verification_policy(policy)
    if not isinstance(characteristics, (list, tuple)) or not characteristics:
        raise ValueError("characteristics must be a non-empty list")
    seen = set()
    inspected = 0
    critical_gaps = []
    gaps = []
    for index, characteristic in enumerate(characteristics):
        if not isinstance(characteristic, dict):
            raise ValueError(
                "characteristic %d must be a mapping, got %r" % (index, characteristic)
            )
        identifier = characteristic.get("id")
        if not isinstance(identifier, str) or not identifier.strip():
            raise ValueError("characteristic %d needs a non-empty string id" % index)
        if identifier in seen:
            raise ValueError("duplicate characteristic id %r" % identifier)
        seen.add(identifier)
        is_critical = _require_flag("critical", characteristic.get("critical", False))
        is_inspected = _require_flag(
            "inspected", characteristic.get("inspected", False)
        )
        if is_inspected:
            inspected += 1
        else:
            gaps.append(identifier)
            if is_critical:
                critical_gaps.append(identifier)
    total = len(characteristics)
    fraction = inspected / total
    threshold = policy["min_inspection_coverage"]
    fraction_met = _at_least(fraction, threshold)
    met = fraction_met and not critical_gaps
    findings = []
    if not fraction_met:
        findings.append(
            "inspection covers %d of %d characteristics, a fraction of %.4f "
            "below the required %.4f" % (inspected, total, fraction, threshold)
        )
    for identifier in critical_gaps:
        findings.append(
            "critical characteristic %s is not inspected; an average coverage "
            "figure cannot stand in for it" % identifier
        )
    return {
        "total": total,
        "inspected": inspected,
        "coverage_fraction": fraction,
        "required_fraction": threshold,
        "gaps": gaps,
        "critical_gaps": critical_gaps,
        "verdict": COVERAGE_MET if met else COVERAGE_NOT_MET,
        "findings": findings,
    }


def screen_verification_matrix(rows, policy=DEFAULT_VERIFICATION_POLICY):
    """Every row needs a method, an article and evidence to count as closed."""
    validate_verification_policy(policy)
    if not isinstance(rows, (list, tuple)) or not rows:
        raise ValueError("rows must be a non-empty verification matrix")
    seen = set()
    closed = []
    open_items = []
    findings = []
    for index, row in enumerate(rows):
        if not isinstance(row, dict):
            raise ValueError("row %d must be a mapping, got %r" % (index, row))
        identifier = row.get("id")
        if not isinstance(identifier, str) or not identifier.strip():
            raise ValueError("row %d needs a non-empty string id" % index)
        if identifier in seen:
            raise ValueError("duplicate requirement id %r in the matrix" % identifier)
        seen.add(identifier)
        method = _require_choice("method", row.get("method"), VERIFICATION_METHODS)
        article = _require_choice("article", row.get("article"), ARTICLES)
        evidence = row.get("evidence")
        has_evidence = isinstance(evidence, str) and bool(evidence.strip())
        if has_evidence:
            closed.append(identifier)
        else:
            open_items.append(identifier)
            findings.append(
                "requirement %s has a %s method on the %s and no evidence; the "
                "row decides how it will be closed, not that it is"
                % (identifier, method, article)
            )
    return {
        "row_count": len(rows),
        "closed": closed,
        "open_items": open_items,
        "verdict": MATRIX_CLOSED if not open_items else MATRIX_OPEN,
        "findings": findings,
    }


def plan_verification(case, policy=DEFAULT_VERIFICATION_POLICY):
    """Full clause 4.14.1 and 4.14.2 strategy with a combined verdict."""
    validate_verification_policy(policy)
    if not isinstance(case, dict):
        raise ValueError("case must be a mapping, got %r" % (case,))
    requirements = case.get("requirements")
    if not isinstance(requirements, (list, tuple)) or not requirements:
        raise ValueError("case needs a non-empty requirements list")
    one_shot = _require_flag("one_shot_device", case.get("one_shot_device", False))
    heritage = _require_flag(
        "heritage_available", case.get("heritage_available", False)
    )
    selections = []
    needs_sample = False
    for index, requirement in enumerate(requirements):
        if not isinstance(requirement, dict):
            raise ValueError(
                "requirement %d must be a mapping, got %r" % (index, requirement)
            )
        identifier = requirement.get("id")
        if not isinstance(identifier, str) or not identifier.strip():
            raise ValueError("requirement %d needs a non-empty string id" % index)
        selection = select_verification_method(
            requirement.get("kind"),
            requirement.get("destructive_demonstration", False),
            one_shot,
            heritage,
        )
        selection["id"] = identifier
        if selection["article"] == "lot-sample":
            needs_sample = True
        selections.append(selection)
    findings = []
    sample = None
    if needs_sample:
        if case.get("lot_size") is None:
            findings.append(
                "a destructive demonstration moves onto a lot sample and no lot "
                "size was supplied; the sample cannot be sized"
            )
        else:
            sample = lot_sample_size(case["lot_size"], policy)
    coverage = None
    if case.get("characteristics") is not None:
        coverage = inspection_coverage(case["characteristics"], policy)
        findings.extend(coverage["findings"])
    else:
        findings.append(
            "no inspection characteristics supplied; the flight article's "
            "inspection coverage is not yet graded"
        )
    matrix = None
    if case.get("matrix") is not None:
        matrix = screen_verification_matrix(case["matrix"], policy)
        findings.extend(matrix["findings"])
    else:
        findings.append(
            "no verification matrix supplied; no requirement is shown to carry "
            "evidence yet"
        )
    closed = (
        coverage is not None
        and coverage["verdict"] == COVERAGE_MET
        and matrix is not None
        and matrix["verdict"] == MATRIX_CLOSED
        and (not needs_sample or sample is not None)
    )
    return {
        "selections": selections,
        "needs_lot_sample": needs_sample,
        "lot_sample_size": sample,
        "coverage": coverage,
        "matrix": matrix,
        "closed": closed,
        "verdict": MATRIX_CLOSED if closed else MATRIX_OPEN,
        "findings": findings,
    }
