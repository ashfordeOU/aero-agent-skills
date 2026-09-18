#!/usr/bin/env python3
"""Which verification method discharges each protection-device requirement.

Anchor: ECSS-E-ST-20-20C clause 4.1. The procedure below is a paraphrase
into implementable steps; no standard text is reproduced.

Clause 4.1 is the standard's own overview of compliance: for every
requirement it carries, the method by which compliance is shown has to be
identified. That sentence sounds administrative and is not. Three things
follow from it, and each is a way a protection-device campaign discovers
too late that it cannot close.

A method has to come from a declared vocabulary. "Verified" is not a
method, "by similarity to the last build" is not a method until the
similarity argument is itself an analysis, and an invented token nobody
else on the programme uses cannot be planned, costed or audited. So a
token outside the agreed vocabulary is refused here rather than accepted
and argued about at the review.

Every requirement needs at least one method, and the requirement set is
covered only when the last one has one. A matrix that is ninety per cent
populated is not ninety per cent of a compliance case; the uncovered ten
per cent is exactly the part nobody has planned to demonstrate, and it is
usually the part that needs a latching-current-limiter trip measurement
on real hardware.

A requirement that fixes a number needs a method that produces a number.
Trip current, trip time, off-state leakage and voltage-drop limits are
demonstrated by test or by analysis; a design review can confirm that a
circuit intends to meet them and cannot show that it does. Review of
design and inspection remain admissible methods -- for configuration,
marking, layout separation -- but they do not discharge a quantitative
limit on their own, so that pairing is a finding here.

The policy fractions below are declared project values, not physical
constants: a project substitutes its own.

Standard library only, offline, deterministic.
"""

from __future__ import annotations

import math

METHOD_TEST = "test"
METHOD_ANALYSIS = "analysis"
METHOD_REVIEW_OF_DESIGN = "review-of-design"
METHOD_INSPECTION = "inspection"

ADMISSIBLE_METHODS = (
    METHOD_TEST,
    METHOD_ANALYSIS,
    METHOD_REVIEW_OF_DESIGN,
    METHOD_INSPECTION,
)

# Methods that produce a measured or computed number, and so can discharge
# a requirement that states a quantitative limit.
EVIDENCE_BEARING_METHODS = (METHOD_TEST, METHOD_ANALYSIS)

NO_METHOD = "no-method-declared"
QUANTITATIVE_LIMIT_WITHOUT_EVIDENCE = "quantitative-limit-without-test-or-analysis"

METHOD_NOT_ESTABLISHED = "verification-method-not-established"
COVERAGE_BELOW_POLICY_FLOOR = "verification-coverage-below-policy-floor"
MATRIX_COVERS_REQUIREMENT_SET = "matrix-covers-requirement-set"

DEFAULT_VERIFICATION_POLICY = {
    "min_covered_fraction": 1.0,
    "min_evidence_bearing_fraction": 0.5,
}

_REL_TOL = 1e-9
_ABS_TOL = 1e-15


def _is_finite_number(value):
    return (
        isinstance(value, (int, float))
        and not isinstance(value, bool)
        and math.isfinite(value)
    )


def _require_number(name, value):
    if not _is_finite_number(value):
        raise ValueError("%s must be a finite number, got %r" % (name, value))
    return float(value)


def _require_fraction(name, value):
    number = _require_number(name, value)
    if number < 0.0 or number > 1.0:
        raise ValueError(
            "%s must lie between zero and one inclusive, got %r" % (name, value)
        )
    return number


def _require_label(name, value):
    if not isinstance(value, str):
        raise ValueError("%s must be a string, got %r" % (name, value))
    return value.strip()


def _at_least(value, limit):
    """value >= limit, absorbing floating-point representation error."""
    return value >= limit or math.isclose(
        value, limit, rel_tol=_REL_TOL, abs_tol=_ABS_TOL
    )


def validate_verification_policy(policy):
    """Check the coverage policy the matrix is graded against is usable."""
    if not isinstance(policy, dict):
        raise ValueError("policy must be a mapping, got %r" % (policy,))
    covered = _require_fraction(
        "min_covered_fraction", policy.get("min_covered_fraction")
    )
    evidence = _require_fraction(
        "min_evidence_bearing_fraction",
        policy.get("min_evidence_bearing_fraction"),
    )
    if evidence > covered:
        raise ValueError(
            "min_evidence_bearing_fraction %g is above min_covered_fraction "
            "%g; a requirement cannot carry test or analysis evidence without "
            "first carrying a method" % (evidence, covered)
        )
    return policy


def normalise_method(token):
    """Reduce one declared method token to the agreed vocabulary."""
    text = _require_label("method", token).lower()
    if not text:
        raise ValueError("a method token must not be blank")
    if text not in ADMISSIBLE_METHODS:
        raise ValueError(
            "method %r is outside the declared vocabulary %s; an invented "
            "token cannot be planned, costed or audited"
            % (token, ", ".join(ADMISSIBLE_METHODS))
        )
    return text


def validate_requirement_record(requirement):
    """Read one requirement of the protection-device standard."""
    if not isinstance(requirement, dict):
        raise ValueError("requirement must be a mapping, got %r" % (requirement,))
    identifier = _require_label("requirement id", requirement.get("id"))
    if not identifier:
        raise ValueError("requirement id must not be blank")
    clause = _require_label(
        "clause on %s" % identifier, requirement.get("clause", "")
    )
    raw = requirement.get("methods", ())
    if isinstance(raw, str):
        raise ValueError(
            "methods on %s must be a sequence of tokens, not a single string; "
            "a requirement may be discharged by more than one method"
            % identifier
        )
    if not isinstance(raw, (list, tuple)):
        raise ValueError("methods on %s must be a sequence" % identifier)
    methods = []
    for token in raw:
        method = normalise_method(token)
        if method not in methods:
            methods.append(method)
    quantitative = requirement.get("states_quantitative_limit", False)
    if not isinstance(quantitative, bool):
        raise ValueError(
            "states_quantitative_limit on %s must be a boolean, got %r"
            % (identifier, quantitative)
        )
    return identifier, tuple(methods), quantitative, clause


def requirement_coverage(requirement):
    """Decide whether one requirement's declared methods can discharge it."""
    identifier, methods, quantitative, clause = validate_requirement_record(
        requirement
    )
    findings = []
    if not methods:
        findings.append(NO_METHOD)
    evidence_bearing = tuple(
        method for method in methods if method in EVIDENCE_BEARING_METHODS
    )
    if quantitative and methods and not evidence_bearing:
        findings.append(QUANTITATIVE_LIMIT_WITHOUT_EVIDENCE)
    return {
        "id": identifier,
        "clause": clause,
        "methods": methods,
        "evidence_bearing_methods": evidence_bearing,
        "states_quantitative_limit": quantitative,
        "findings": tuple(findings),
        "covered": not findings,
    }


def requirement_coverages(requirements):
    """Grade every requirement in the set, in record order."""
    if not isinstance(requirements, (list, tuple)):
        raise ValueError("requirements must be a sequence of requirement records")
    if not requirements:
        raise ValueError(
            "the requirement set is empty, so there is no compliance case to "
            "identify methods for"
        )
    coverages = []
    seen = set()
    for requirement in requirements:
        coverage = requirement_coverage(requirement)
        if coverage["id"] in seen:
            raise ValueError(
                "duplicate requirement id %r in the set" % coverage["id"]
            )
        seen.add(coverage["id"])
        coverages.append(coverage)
    return tuple(coverages)


def covered_fraction(coverages):
    """Share of the requirement set whose declared methods can discharge it."""
    if not isinstance(coverages, (list, tuple)) or not coverages:
        raise ValueError("coverages must be a non-empty sequence")
    return sum(1 for cover in coverages if cover["covered"]) / len(coverages)


def evidence_bearing_fraction(coverages):
    """Share of the requirement set carrying a test or analysis method."""
    if not isinstance(coverages, (list, tuple)) or not coverages:
        raise ValueError("coverages must be a non-empty sequence")
    carrying = sum(1 for cover in coverages if cover["evidence_bearing_methods"])
    return carrying / len(coverages)


def requirements_grouped_by_method(coverages):
    """Group requirement identifiers under each method that discharges them."""
    if not isinstance(coverages, (list, tuple)):
        raise ValueError("coverages must be a sequence")
    grouped = {method: [] for method in ADMISSIBLE_METHODS}
    for cover in coverages:
        for method in cover["methods"]:
            grouped[method].append(cover["id"])
    return {method: tuple(ids) for method, ids in grouped.items()}


def uncovered_requirements(coverages):
    """Identifiers of the requirements no declared method can discharge."""
    if not isinstance(coverages, (list, tuple)):
        raise ValueError("coverages must be a sequence")
    return tuple(cover["id"] for cover in coverages if not cover["covered"])


def assess_verification_overview(case, policy=DEFAULT_VERIFICATION_POLICY):
    """Full clause 4.1 compliance-method overview for one requirement set."""
    if not isinstance(case, dict):
        raise ValueError("case must be a mapping, got %r" % (case,))
    validate_verification_policy(policy)

    findings = []
    advisories = []
    result = {
        "matrix_reference": None,
        "requirement_count": 0,
        "coverages": (),
        "covered_fraction": None,
        "evidence_bearing_fraction": None,
        "uncovered_requirements": (),
        "requirements_grouped_by_method": {},
        "findings": findings,
        "advisories": advisories,
    }

    reference = case.get("matrix_reference")
    if reference is None or not _require_label("matrix_reference", reference):
        findings.append(
            "the requirement set carries no verification matrix reference, so "
            "no method identification can be audited against it"
        )
        result["verdict"] = METHOD_NOT_ESTABLISHED
        return result
    result["matrix_reference"] = _require_label("matrix_reference", reference)

    coverages = requirement_coverages(case.get("requirements"))
    result["coverages"] = coverages
    result["requirement_count"] = len(coverages)
    result["covered_fraction"] = covered_fraction(coverages)
    result["evidence_bearing_fraction"] = evidence_bearing_fraction(coverages)
    result["uncovered_requirements"] = uncovered_requirements(coverages)
    result["requirements_grouped_by_method"] = requirements_grouped_by_method(
        coverages
    )

    for cover in coverages:
        if NO_METHOD in cover["findings"]:
            findings.append(
                "requirement %s declares no compliance method, so nobody has "
                "planned how it will be shown" % cover["id"]
            )
        if QUANTITATIVE_LIMIT_WITHOUT_EVIDENCE in cover["findings"]:
            findings.append(
                "requirement %s fixes a number but is discharged by %s alone; "
                "a limit needs test or analysis to produce the number"
                % (cover["id"], " and ".join(cover["methods"]))
            )

    for cover in coverages:
        if cover["covered"] and len(cover["methods"]) == 1:
            advisories.append(
                "requirement %s rests on a single method (%s); losing that "
                "method late leaves no fallback route to compliance"
                % (cover["id"], cover["methods"][0])
            )

    if not _at_least(
        result["covered_fraction"], float(policy["min_covered_fraction"])
    ):
        findings.append(
            "%.4g per cent of the requirement set has a usable method, below "
            "the %.4g per cent the verification policy requires"
            % (
                result["covered_fraction"] * 100.0,
                float(policy["min_covered_fraction"]) * 100.0,
            )
        )
        result["verdict"] = COVERAGE_BELOW_POLICY_FLOOR
        return result

    if not _at_least(
        result["evidence_bearing_fraction"],
        float(policy["min_evidence_bearing_fraction"]),
    ):
        findings.append(
            "only %.4g per cent of the requirement set carries test or "
            "analysis evidence, below the %.4g per cent floor; the case rests "
            "too heavily on review and inspection"
            % (
                result["evidence_bearing_fraction"] * 100.0,
                float(policy["min_evidence_bearing_fraction"]) * 100.0,
            )
        )
        result["verdict"] = COVERAGE_BELOW_POLICY_FLOOR
        return result

    result["verdict"] = MATRIX_COVERS_REQUIREMENT_SET
    return result
