"""Ground support equipment design, development and verification assurance logic.

Anchor: ECSS-Q-ST-20C clause 5.8.1 -- quality assurance of ground support
equipment design, development and verification: the traceability of GSE
requirements, the verification records that close them, and the quality review
of the GSE design before it is allowed near flight hardware. Paraphrased into an
implementable procedure; no standard text is reproduced.

Procedure implemented here
--------------------------
1. Validate the GSE requirement set: unique identifiers, a stated criticality,
   a planned verification method and a named parent in the source set.
2. Trace each requirement upward to a source requirement that actually exists,
   so a requirement invented inside the GSE design is visible as such.
3. Trace each requirement downward to a verification record, and compare the
   method the record used with the method the requirement planned.
4. Grade method adequacy separately: a requirement protecting flight hardware
   or personnel is not closed by review of design alone.
5. Compute the closure coverage of the whole set, then combine the findings
   into an approved, approved-with-actions or not-approved design review.
"""

import math

__all__ = [
    "VERIFICATION_METHODS",
    "CRITICALITIES",
    "RESULTS",
    "TEST_ONLY_CRITICALITIES",
    "COVERAGE_TOLERANCE",
    "normalize_token",
    "validate_requirement",
    "validate_requirement_set",
    "validate_verification_records",
    "upward_trace_findings",
    "verification_findings",
    "method_adequacy_findings",
    "closure_coverage",
    "review_verdict",
    "assess_gse_design_assurance",
]

VERIFICATION_METHODS = ("test", "analysis", "inspection", "review-of-design")
CRITICALITIES = ("safety-critical", "flight-hardware-interfacing", "standard")
RESULTS = ("passed", "failed", "open")

# Criticalities whose requirements a paper method cannot close on its own.
TEST_ONLY_CRITICALITIES = ("safety-critical", "flight-hardware-interfacing")

# Coverage is a ratio of small integers and can land a few ULPs off unity.
COVERAGE_TOLERANCE = 1e-9


def normalize_token(value, label="token"):
    """Return a lowercase, hyphen-joined comparison token for an identifier."""
    if not isinstance(value, str):
        raise ValueError("%s must be a string, got %r" % (label, value))
    token = "-".join(value.strip().lower().replace("_", " ").replace("-", " ").split())
    if not token:
        raise ValueError("%s must not be blank" % label)
    return token


def validate_requirement(record, index=0):
    """Return one validated GSE requirement record."""
    if not isinstance(record, dict):
        raise ValueError("requirements[%d] must be a mapping" % index)
    for key in ("id", "criticality", "planned_method"):
        if key not in record:
            raise ValueError("requirements[%d] is missing '%s'" % (index, key))
    req_id = normalize_token(record["id"], "requirements[%d]['id']" % index)
    criticality = normalize_token(record["criticality"], "requirements[%d]['criticality']" % index)
    if criticality not in CRITICALITIES:
        raise ValueError(
            "requirement %s criticality %r is not one of %s" % (req_id, criticality, CRITICALITIES)
        )
    method = normalize_token(record["planned_method"], "requirements[%d]['planned_method']" % index)
    if method not in VERIFICATION_METHODS:
        raise ValueError(
            "requirement %s planned method %r is not one of %s" % (req_id, method, VERIFICATION_METHODS)
        )
    parent = record.get("parent_id")
    if parent is not None:
        parent = normalize_token(parent, "requirements[%d]['parent_id']" % index)
    return {
        "id": req_id,
        "criticality": criticality,
        "planned_method": method,
        "parent_id": parent,
    }


def validate_requirement_set(records):
    """Return the validated GSE requirement set, refusing a duplicated identifier."""
    if not isinstance(records, (list, tuple)) or not records:
        raise ValueError("requirements must be a non-empty sequence of requirement records")
    seen = set()
    validated = []
    for i, record in enumerate(records):
        requirement = validate_requirement(record, i)
        if requirement["id"] in seen:
            raise ValueError("requirement %s is declared twice" % requirement["id"])
        seen.add(requirement["id"])
        validated.append(requirement)
    return validated


def validate_verification_records(records):
    """Return the validated verification records for the GSE design."""
    if records is None:
        records = []
    if not isinstance(records, (list, tuple)):
        raise ValueError("verification records must be a sequence")
    seen = set()
    validated = []
    for i, record in enumerate(records):
        if not isinstance(record, dict):
            raise ValueError("verification_records[%d] must be a mapping" % i)
        for key in ("id", "requirement_id", "method", "result"):
            if key not in record:
                raise ValueError("verification_records[%d] is missing '%s'" % (i, key))
        rec_id = normalize_token(record["id"], "verification_records[%d]['id']" % i)
        if rec_id in seen:
            raise ValueError("verification record %s is declared twice" % rec_id)
        seen.add(rec_id)
        method = normalize_token(record["method"], "verification_records[%d]['method']" % i)
        if method not in VERIFICATION_METHODS:
            raise ValueError(
                "verification record %s method %r is not one of %s" % (rec_id, method, VERIFICATION_METHODS)
            )
        result = normalize_token(record["result"], "verification_records[%d]['result']" % i)
        if result not in RESULTS:
            raise ValueError(
                "verification record %s result %r is not one of %s" % (rec_id, result, RESULTS)
            )
        validated.append(
            {
                "id": rec_id,
                "requirement_id": normalize_token(
                    record["requirement_id"], "verification_records[%d]['requirement_id']" % i
                ),
                "method": method,
                "result": result,
            }
        )
    return validated


def upward_trace_findings(requirements, source_ids):
    """Return the requirements that trace to nothing in the declared source set."""
    if not isinstance(source_ids, (list, tuple)):
        raise ValueError("source_ids must be a sequence of source requirement identifiers")
    sources = {normalize_token(s, "source requirement id") for s in source_ids}
    findings = []
    for requirement in requirements:
        parent = requirement["parent_id"]
        if parent is None:
            findings.append("GSE requirement %s names no source requirement" % requirement["id"])
        elif parent not in sources:
            findings.append(
                "GSE requirement %s traces to %s, which is not in the source set"
                % (requirement["id"], parent)
            )
    return findings


def verification_findings(requirements, records):
    """Return the downward traceability and verification-result findings."""
    by_requirement = {}
    known = {requirement["id"] for requirement in requirements}
    findings = []
    for record in records:
        if record["requirement_id"] not in known:
            findings.append(
                "verification record %s closes %s, which is not a GSE requirement"
                % (record["id"], record["requirement_id"])
            )
            continue
        by_requirement.setdefault(record["requirement_id"], []).append(record)
    for requirement in requirements:
        matched = by_requirement.get(requirement["id"], [])
        if not matched:
            findings.append("GSE requirement %s has no verification record" % requirement["id"])
            continue
        for record in matched:
            if record["method"] != requirement["planned_method"]:
                findings.append(
                    "GSE requirement %s planned %s but record %s used %s"
                    % (requirement["id"], requirement["planned_method"], record["id"], record["method"])
                )
            if record["result"] == "failed":
                findings.append(
                    "verification record %s for GSE requirement %s failed"
                    % (record["id"], requirement["id"])
                )
            elif record["result"] == "open":
                findings.append(
                    "verification record %s for GSE requirement %s is still open"
                    % (record["id"], requirement["id"])
                )
    return findings


def method_adequacy_findings(requirements):
    """Return the requirements whose criticality a paper method cannot close."""
    findings = []
    for requirement in requirements:
        if (
            requirement["criticality"] in TEST_ONLY_CRITICALITIES
            and requirement["planned_method"] != "test"
        ):
            findings.append(
                "%s GSE requirement %s is planned for %s; this criticality is closed by test"
                % (requirement["criticality"], requirement["id"], requirement["planned_method"])
            )
    return findings


def closure_coverage(requirements, records):
    """Return the fraction of GSE requirements closed by a passed record."""
    if not requirements:
        raise ValueError("requirements must not be empty")
    passed = {r["requirement_id"] for r in records if r["result"] == "passed"}
    failed_or_open = {r["requirement_id"] for r in records if r["result"] != "passed"}
    closed = sum(
        1
        for requirement in requirements
        if requirement["id"] in passed and requirement["id"] not in failed_or_open
    )
    return float(closed) / float(len(requirements))


def review_verdict(blocking, actions):
    """Return approved, approved-with-actions or not-approved for the finding sets."""
    if not isinstance(blocking, (list, tuple)) or not isinstance(actions, (list, tuple)):
        raise ValueError("blocking and actions must be sequences")
    if blocking:
        return "not-approved"
    if actions:
        return "approved-with-actions"
    return "approved"


def assess_gse_design_assurance(spec):
    """Run the full clause 5.8.1 GSE design assurance assessment.

    spec keys: requirements, source_ids, optional verification_records and
    required_coverage.
    """
    if not isinstance(spec, dict):
        raise ValueError("spec must be a mapping")
    for key in ("requirements", "source_ids"):
        if key not in spec:
            raise ValueError("spec missing required key '%s'" % key)
    requirements = validate_requirement_set(spec["requirements"])
    records = validate_verification_records(spec.get("verification_records"))
    trace = upward_trace_findings(requirements, spec["source_ids"])
    verification = verification_findings(requirements, records)
    adequacy = method_adequacy_findings(requirements)
    coverage = closure_coverage(requirements, records)

    required_coverage = spec.get("required_coverage", 1.0)
    if not isinstance(required_coverage, (int, float)) or isinstance(required_coverage, bool):
        raise ValueError("required_coverage must be a real number")
    required_coverage = float(required_coverage)
    if not math.isfinite(required_coverage) or not 0.0 <= required_coverage <= 1.0:
        raise ValueError("required_coverage must lie in [0, 1], got %r" % (spec["required_coverage"],))

    blocking = list(trace) + list(adequacy)
    actions = []
    for finding in verification:
        if "failed" in finding or "no verification record" in finding or "not a GSE requirement" in finding:
            blocking.append(finding)
        else:
            actions.append(finding)
    if coverage < required_coverage and not math.isclose(
        coverage, required_coverage, rel_tol=0.0, abs_tol=COVERAGE_TOLERANCE
    ):
        blocking.append(
            "verification closure coverage %.3f is below the required %.3f"
            % (coverage, required_coverage)
        )
    verdict = review_verdict(blocking, actions)
    return {
        "requirements": requirements,
        "verification_records": records,
        "upward_trace_findings": trace,
        "verification_findings": verification,
        "method_adequacy_findings": adequacy,
        "closure_coverage": coverage,
        "required_coverage": required_coverage,
        "blocking": blocking,
        "actions": actions,
        "verdict": verdict,
        "design_usable": verdict != "not-approved",
    }
