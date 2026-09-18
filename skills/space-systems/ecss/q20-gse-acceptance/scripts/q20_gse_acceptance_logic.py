"""GSE acceptance grading and release-for-use logic.

Anchor: ECSS-Q-ST-20C clause 5.8.4.2 -- acceptance of ground support equipment:
the acceptance tests and acceptance reviews run against the agreed GSE
requirements, and the decision to release the equipment for use. Paraphrased
into an implementable procedure; no standard text is reproduced.

Procedure implemented here
--------------------------
1. Validate the GSE requirement set: a criticality, a planned acceptance
   method and, where the requirement is quantitative, a bound and the side of
   it the equipment has to stay on.
2. Validate the acceptance results, refusing a result against a requirement
   nobody agreed and an outcome outside the closed vocabulary.
3. Grade each quantitative result on its own measurement, keeping the margin
   rather than only the verdict, and treat a value that lands on the bound as
   inside it.
4. Grade method adequacy separately from outcome: a safety-critical
   requirement is shown by test or inspection, not argued on paper.
5. Compute acceptance coverage over the requirement set, since a requirement
   nobody exercised is not a requirement that passed.
6. Separate a failure carried on an approved waiver, which limits the
   equipment, from one that is not, which stops it, and return the release
   verdict.
"""

import math

__all__ = [
    "CRITICALITIES",
    "ACCEPTANCE_METHODS",
    "DEMONSTRATIVE_METHODS",
    "OUTCOMES",
    "LIMIT_SENSES",
    "MEASUREMENT_TOLERANCE",
    "COVERAGE_TOLERANCE",
    "normalize_token",
    "validate_requirements",
    "validate_results",
    "evaluate_measurement",
    "grade_results",
    "method_adequacy_findings",
    "acceptance_coverage",
    "release_verdict",
    "assess_gse_acceptance",
]

# How much the equipment matters to people and to the flight hardware it touches.
CRITICALITIES = ("safety-critical", "operational", "convenience")

# The acceptance methods a GSE requirement may be closed by.
ACCEPTANCE_METHODS = ("test", "inspection", "analysis", "review-of-design")

# Methods that observe the equipment behaving rather than argue that it will.
DEMONSTRATIVE_METHODS = ("test", "inspection")

# The states an acceptance result may report.
OUTCOMES = ("pass", "fail", "not-run")

# Which side of its bound a quantitative requirement has to stay on.
LIMIT_SENSES = ("max", "min")

# A measured value landing on its bound is inside it; representation error is
# absorbed here rather than argued about at the review.
MEASUREMENT_TOLERANCE = 1e-9

# Coverage is a ratio of two counts and can land a few ULPs short of unity.
COVERAGE_TOLERANCE = 1e-9


def normalize_token(value, label="token"):
    """Return a lowercase, hyphen-joined comparison token for a name."""
    if not isinstance(value, str):
        raise ValueError("%s must be a string, got %r" % (label, value))
    token = "-".join(value.strip().lower().replace("_", " ").replace("-", " ").split())
    if not token:
        raise ValueError("%s must not be blank" % label)
    return token


def _real(value, label):
    if not isinstance(value, (int, float)) or isinstance(value, bool):
        raise ValueError("%s must be a real number, got %r" % (label, value))
    v = float(value)
    if not math.isfinite(v):
        raise ValueError("%s must be finite, got %r" % (label, value))
    return v


def _flag(value, label):
    if not isinstance(value, bool):
        raise ValueError("%s must be a boolean, got %r" % (label, value))
    return value


def validate_requirements(requirements):
    """Return the validated GSE requirement set keyed by identifier."""
    if not isinstance(requirements, (list, tuple)) or not requirements:
        raise ValueError("requirements must be a non-empty sequence of requirement records")
    validated = {}
    for i, requirement in enumerate(requirements):
        if not isinstance(requirement, dict):
            raise ValueError("requirements[%d] must be a mapping" % i)
        for key in ("id", "criticality", "planned_method"):
            if key not in requirement:
                raise ValueError("requirements[%d] is missing '%s'" % (i, key))
        rid = normalize_token(requirement["id"], "requirements[%d]['id']" % i)
        if rid in validated:
            raise ValueError("requirement %r is declared twice" % rid)
        criticality = normalize_token(
            requirement["criticality"], "requirements[%d]['criticality']" % i
        )
        if criticality not in CRITICALITIES:
            raise ValueError("requirements[%d] criticality %r is unknown" % (i, criticality))
        method = normalize_token(
            requirement["planned_method"], "requirements[%d]['planned_method']" % i
        )
        if method not in ACCEPTANCE_METHODS:
            raise ValueError("requirements[%d] method %r is unknown" % (i, method))
        limit = requirement.get("limit")
        sense = requirement.get("limit_sense")
        if limit is not None:
            limit = _real(limit, "requirements[%d]['limit']" % i)
            if sense is None:
                raise ValueError("requirements[%d] has a limit but no limit_sense" % i)
            sense = normalize_token(sense, "requirements[%d]['limit_sense']" % i)
            if sense not in LIMIT_SENSES:
                raise ValueError("requirements[%d] limit_sense %r is unknown" % (i, sense))
        elif sense is not None:
            raise ValueError("requirements[%d] has a limit_sense but no limit" % i)
        validated[rid] = {
            "id": rid,
            "criticality": criticality,
            "planned_method": method,
            "limit": limit,
            "limit_sense": sense,
        }
    return validated


def validate_results(results, requirements):
    """Return the validated acceptance results in the order they were run."""
    agreed = validate_requirements(requirements)
    if not isinstance(results, (list, tuple)):
        raise ValueError("results must be a sequence of acceptance result records")
    validated = []
    for i, result in enumerate(results):
        if not isinstance(result, dict):
            raise ValueError("results[%d] must be a mapping" % i)
        for key in ("requirement_id", "method", "outcome"):
            if key not in result:
                raise ValueError("results[%d] is missing '%s'" % (i, key))
        rid = normalize_token(result["requirement_id"], "results[%d]['requirement_id']" % i)
        if rid not in agreed:
            raise ValueError("results[%d] names requirement %r, which was not agreed" % (i, rid))
        method = normalize_token(result["method"], "results[%d]['method']" % i)
        if method not in ACCEPTANCE_METHODS:
            raise ValueError("results[%d] method %r is unknown" % (i, method))
        outcome = normalize_token(result["outcome"], "results[%d]['outcome']" % i)
        if outcome not in OUTCOMES:
            raise ValueError("results[%d] outcome %r is unknown" % (i, outcome))
        measured = result.get("measured")
        if measured is not None:
            measured = _real(measured, "results[%d]['measured']" % i)
        validated.append(
            {
                "requirement_id": rid,
                "method": method,
                "outcome": outcome,
                "measured": measured,
                "waiver_approved": _flag(
                    result.get("waiver_approved", False),
                    "results[%d]['waiver_approved']" % i,
                ),
            }
        )
    return validated


def evaluate_measurement(measured, limit, sense):
    """Return the pass state and the margin of a measurement against its bound."""
    value = _real(measured, "measured")
    bound = _real(limit, "limit")
    side = normalize_token(sense, "sense")
    if side not in LIMIT_SENSES:
        raise ValueError("sense %r is not a limit sense" % side)
    if side == "max":
        margin = bound - value
    else:
        margin = value - bound
    on_bound = math.isclose(value, bound, rel_tol=0.0, abs_tol=MEASUREMENT_TOLERANCE)
    return {"pass": on_bound or margin > 0.0, "margin": margin}


def grade_results(results, requirements):
    """Return the graded results and the findings their measurements raise."""
    agreed = validate_requirements(requirements)
    graded = validate_results(results, requirements)
    findings = []
    for entry in graded:
        requirement = agreed[entry["requirement_id"]]
        entry["criticality"] = requirement["criticality"]
        entry["margin"] = None
        if requirement["limit"] is not None:
            if entry["outcome"] == "not-run":
                entry["measurement_pass"] = None
            elif entry["measured"] is None:
                raise ValueError(
                    "results for %s report an outcome with no measured value"
                    % entry["requirement_id"]
                )
            else:
                verdict = evaluate_measurement(
                    entry["measured"], requirement["limit"], requirement["limit_sense"]
                )
                entry["margin"] = verdict["margin"]
                entry["measurement_pass"] = verdict["pass"]
                if entry["outcome"] == "pass" and not verdict["pass"]:
                    findings.append(
                        "%s is reported as a pass but its measurement misses the bound by %g"
                        % (entry["requirement_id"], -verdict["margin"])
                    )
        else:
            entry["measurement_pass"] = None
        if entry["outcome"] == "fail" and not entry["waiver_approved"]:
            findings.append(
                "%s failed acceptance with no approved waiver behind it"
                % entry["requirement_id"]
            )
        if entry["method"] != requirement["planned_method"]:
            findings.append(
                "%s was accepted by %s where %s was planned"
                % (entry["requirement_id"], entry["method"], requirement["planned_method"])
            )
    return {"graded": graded, "findings": findings}


def method_adequacy_findings(results, requirements):
    """Return the safety-critical requirements closed without a demonstration."""
    agreed = validate_requirements(requirements)
    graded = validate_results(results, requirements)
    findings = []
    for entry in graded:
        requirement = agreed[entry["requirement_id"]]
        if (
            requirement["criticality"] == "safety-critical"
            and entry["method"] not in DEMONSTRATIVE_METHODS
        ):
            findings.append(
                "safety-critical requirement %s was closed by %s rather than a demonstration"
                % (entry["requirement_id"], entry["method"])
            )
    return findings


def acceptance_coverage(results, requirements):
    """Return the fraction of agreed requirements with a conclusive result."""
    agreed = validate_requirements(requirements)
    graded = validate_results(results, requirements)
    conclusive = set()
    inconclusive = set()
    for entry in graded:
        if entry["outcome"] == "not-run":
            inconclusive.add(entry["requirement_id"])
        else:
            conclusive.add(entry["requirement_id"])
    settled = conclusive - inconclusive
    return len(settled) / float(len(agreed))


def release_verdict(findings, limitations):
    """Return the release-for-use verdict for the graded acceptance."""
    if not isinstance(findings, (list, tuple)):
        raise ValueError("findings must be a sequence")
    if not isinstance(limitations, (list, tuple)):
        raise ValueError("limitations must be a sequence")
    if findings:
        return "not-released"
    if limitations:
        return "released-with-limitations"
    return "released"


def assess_gse_acceptance(spec):
    """Run the full clause 5.8.4.2 GSE acceptance assessment.

    spec keys: requirements, results, required_coverage.
    """
    if not isinstance(spec, dict):
        raise ValueError("spec must be a mapping")
    for key in ("requirements", "results", "required_coverage"):
        if key not in spec:
            raise ValueError("spec missing required key '%s'" % key)
    required_coverage = _real(spec["required_coverage"], "required_coverage")
    if not 0.0 < required_coverage <= 1.0:
        raise ValueError("required_coverage must fall in (0, 1], got %r" % (spec["required_coverage"],))
    graded = grade_results(spec["results"], spec["requirements"])
    method = method_adequacy_findings(spec["results"], spec["requirements"])
    coverage = acceptance_coverage(spec["results"], spec["requirements"])
    findings = list(graded["findings"]) + list(method)
    if coverage < required_coverage and not math.isclose(
        coverage, required_coverage, rel_tol=0.0, abs_tol=COVERAGE_TOLERANCE
    ):
        findings.append(
            "acceptance covered %.1f%% of the requirement set against %.1f%% required"
            % (coverage * 100.0, required_coverage * 100.0)
        )
    limitations = [
        "%s is carried on an approved waiver and limits the equipment" % entry["requirement_id"]
        for entry in graded["graded"]
        if entry["outcome"] == "fail" and entry["waiver_approved"]
    ]
    return {
        "graded": graded["graded"],
        "coverage": coverage,
        "method_findings": method,
        "limitations": limitations,
        "findings": findings,
        "verdict": release_verdict(findings, limitations),
    }
