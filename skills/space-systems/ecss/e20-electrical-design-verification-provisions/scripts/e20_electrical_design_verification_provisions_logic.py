#!/usr/bin/env python3
"""ECSS-E-ST-20C clause 4.3.1 electrical design verification provisions
(paraphrase, not copy).

Common-knowledge summary (standards-map.yaml, ecss: gated false): the
electrical and electronic engineering standard requires every
requirement of its design clause to carry a verification provision --
a verification method (analysis, review-of-design, test, inspection),
the project milestone at which that method closes the requirement, and
the evidence artefact produced. Method choice is constrained by the
requirement characteristic (an observable workmanship requirement is
not testable; a quantitative performance requirement is not closed by
a design-data argument) and by what is available (representative
hardware, destructiveness). Milestone choice is constrained by when
the evidence can exist: a design-data argument at PDR, an analysis
once the detailed design is frozen at CDR, an inspection or a
qualification test once hardware exists at QR, an acceptance test on
flight hardware at AR.

This module implements method acceptability, preferred-method
selection, earliest-closure-milestone derivation, per-provision
checking and two-way matrix coverage. It does not model the content of
any individual analysis or test procedure, and it does not schedule
the project reviews themselves.
"""

VERIFICATION_METHODS = frozenset(
    {"analysis", "review_of_design", "test", "inspection"}
)

# Project reviews in chronological order. A verification provision
# closes at one of these; the index is the ordering key.
MILESTONE_SEQUENCE = ("srr", "pdr", "cdr", "qr", "ar")

# Methods that can actually produce evidence for a given requirement
# characteristic. A method outside the set cannot close the requirement.
ACCEPTABLE_METHODS = {
    "functional_behaviour": frozenset({"test", "analysis", "review_of_design"}),
    "performance_margin": frozenset({"test", "analysis"}),
    "interface_compatibility": frozenset(
        {"test", "analysis", "review_of_design", "inspection"}
    ),
    "electromagnetic_compatibility": frozenset({"test", "analysis"}),
    "workmanship": frozenset({"inspection"}),
    "part_selection": frozenset({"review_of_design", "inspection"}),
}

REQUIREMENT_CHARACTERISTICS = frozenset(ACCEPTABLE_METHODS)

# Characteristics whose evidence is produced by exercising hardware;
# the remaining characteristics are observational or design-data based.
HARDWARE_DEMONSTRABLE = frozenset(
    {
        "functional_behaviour",
        "performance_margin",
        "interface_compatibility",
        "electromagnetic_compatibility",
    }
)


def normalize_method(method):
    """Canonical verification method name. Raises ValueError for a
    method outside the four recognized by clause 4.3.1."""
    if not isinstance(method, str):
        raise ValueError("verification method must be a string, got %r" % (method,))
    candidate = method.strip().lower().replace("-", "_").replace(" ", "_")
    if candidate not in VERIFICATION_METHODS:
        raise ValueError(
            "unrecognized verification method %r under E-ST-20C clause 4.3.1"
            % (method,)
        )
    return candidate


def milestone_index(milestone):
    """Position of a project review in MILESTONE_SEQUENCE. Raises
    ValueError for a milestone outside the recognized sequence."""
    if not isinstance(milestone, str):
        raise ValueError("milestone must be a string, got %r" % (milestone,))
    candidate = milestone.strip().lower()
    if candidate not in MILESTONE_SEQUENCE:
        raise ValueError("unrecognized verification milestone %r" % (milestone,))
    return MILESTONE_SEQUENCE.index(candidate)


def method_is_acceptable(characteristic, method):
    """True when the method can produce evidence for that requirement
    characteristic. Raises ValueError for an unrecognized
    characteristic or an unrecognized method."""
    if characteristic not in REQUIREMENT_CHARACTERISTICS:
        raise ValueError(
            "unrecognized requirement characteristic %r under E-ST-20C "
            "clause 4.3.1" % (characteristic,)
        )
    return normalize_method(method) in ACCEPTABLE_METHODS[characteristic]


def select_verification_method(
    characteristic, quantitative, representative_hardware_available, destructive
):
    """Preferred verification method for one requirement.

    Observational characteristics close by the method their evidence
    allows (workmanship by inspection, part selection by a design-data
    argument). For a hardware-demonstrable characteristic, test wins
    when representative hardware exists and demonstrating the
    requirement would not destroy it; otherwise a quantitative
    requirement falls to analysis and a qualitative one to
    review-of-design when that is acceptable. Raises ValueError for an
    unrecognized characteristic."""
    if characteristic not in REQUIREMENT_CHARACTERISTICS:
        raise ValueError(
            "unrecognized requirement characteristic %r under E-ST-20C "
            "clause 4.3.1" % (characteristic,)
        )
    if characteristic == "workmanship":
        return "inspection"
    if characteristic == "part_selection":
        return "review_of_design"
    if representative_hardware_available and not destructive:
        return "test"
    if quantitative:
        return "analysis"
    if "review_of_design" in ACCEPTABLE_METHODS[characteristic]:
        return "review_of_design"
    return "analysis"


def earliest_closure_milestone(method, qualification_model_available):
    """Earliest project review at which the method can produce its
    evidence: a design-data argument at PDR, an analysis once the
    detailed design exists at CDR, an inspection on built hardware at
    QR, a test at QR when a qualification model exists and otherwise on
    flight hardware at AR. Raises ValueError for an unrecognized
    method."""
    canonical = normalize_method(method)
    if canonical == "review_of_design":
        return "pdr"
    if canonical == "analysis":
        return "cdr"
    if canonical == "inspection":
        return "qr"
    return "qr" if qualification_model_available else "ar"


def provision_findings(requirement, provision):
    """Finding list (empty if acceptable) for one requirement and the
    provision written against it.

    requirement: {"requirement_id", "characteristic", ...}.
    provision: {"requirement_id", "method", "milestone",
    "evidence_artefact", optional "qualification_model_available"}.
    Raises ValueError for an unrecognized characteristic, method or
    milestone. Mutates neither argument."""
    characteristic = requirement["characteristic"]
    requirement_id = requirement["requirement_id"]
    method = normalize_method(provision["method"])
    planned = provision["milestone"]
    planned_index = milestone_index(planned)
    findings = []
    if not method_is_acceptable(characteristic, method):
        findings.append(
            {
                "issue": "method_not_acceptable_for_characteristic",
                "requirement": requirement_id,
                "characteristic": characteristic,
                "method": method,
            }
        )
    earliest = earliest_closure_milestone(
        method, provision.get("qualification_model_available", False)
    )
    if planned_index < milestone_index(earliest):
        findings.append(
            {
                "issue": "milestone_earlier_than_method_can_close",
                "requirement": requirement_id,
                "method": method,
                "planned_milestone": planned.strip().lower(),
                "earliest_milestone": earliest,
            }
        )
    if not provision.get("evidence_artefact"):
        findings.append(
            {
                "issue": "missing_evidence_artefact",
                "requirement": requirement_id,
                "method": method,
            }
        )
    return findings


def coverage_findings(requirements, provisions):
    """Two-way coverage finding list for the verification matrix: a
    requirement with no provision, and a provision naming an identifier
    that is not in the requirement set. Raises ValueError for a
    duplicated requirement identifier (coverage by identifier would be
    unprovable) or an empty requirement set."""
    requirement_ids = []
    for requirement in requirements:
        requirement_id = requirement["requirement_id"]
        if requirement_id in requirement_ids:
            raise ValueError(
                "duplicate requirement identifier %r in the verification matrix"
                % (requirement_id,)
            )
        requirement_ids.append(requirement_id)
    if not requirement_ids:
        raise ValueError("verification matrix holds no clause 4 requirement")
    covered = {provision["requirement_id"] for provision in provisions}
    findings = []
    for requirement_id in requirement_ids:
        if requirement_id not in covered:
            findings.append(
                {
                    "issue": "requirement_without_verification_provision",
                    "requirement": requirement_id,
                }
            )
    known = set(requirement_ids)
    for provision in provisions:
        if provision["requirement_id"] not in known:
            findings.append(
                {
                    "issue": "orphan_verification_provision",
                    "requirement": provision["requirement_id"],
                }
            )
    return findings


def verification_provision_review(requirements, provisions):
    """Full clause 4.3.1 review of a verification matrix. Returns
    {"provision": [...], "coverage": [...]}, each a finding list.
    Provisions naming an unknown requirement are reported by the
    coverage check only and are not method-checked."""
    by_id = {
        requirement["requirement_id"]: requirement for requirement in requirements
    }
    provision_issues = []
    for provision in provisions:
        requirement = by_id.get(provision["requirement_id"])
        if requirement is None:
            continue
        provision_issues.extend(provision_findings(requirement, provision))
    return {
        "provision": provision_issues,
        "coverage": coverage_findings(requirements, provisions),
    }


def is_verification_plan_compliant(review):
    """True when both finding lists of a verification_provision_review
    result are empty -- the matrix satisfies clause 4.3.1 for this
    assessment."""
    return all(len(findings) == 0 for findings in review.values())
