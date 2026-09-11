#!/usr/bin/env python3
"""ECSS-E-ST-10C clause 5.4.2.2 configuration baseline establishment
(paraphrase, not copy).

Common-knowledge summary (standards-map.yaml, ecss: gated false): the
system engineering process establishes three successive configuration
baselines -- functional (top-level requirements, gated by the system
requirements review), allocated (requirements allocated to each
configuration item, gated by the preliminary design review), and
product (build-to design and as-built record, gated by the critical
design review) -- with configuration control governed under the
ECSS-M-ST-40 discipline. Each baseline may only be established after
every earlier baseline in the sequence is already established, after
its gating milestone review has passed, and once its required
configuration-management artifacts are on record. This module
implements the sequence check, milestone-gate check, and artifact
completeness check, and aggregates them into a per-baseline review; it
does not define the ECSS-M-ST-40 change-control process that governs a
baseline once established.
"""

BASELINE_ORDER = ("functional", "allocated", "product")

BASELINE_MILESTONE = {
    "functional": "SRR",
    "allocated": "PDR",
    "product": "CDR",
}

BASELINE_REQUIRED_ARTIFACTS = {
    "functional": frozenset({"top_level_requirements_doc", "functional_interface_spec"}),
    "allocated": frozenset({"configuration_item_requirements", "interface_control_documents"}),
    "product": frozenset(
        {"build_to_documentation", "as_built_configuration_list", "verification_closeout_record"}
    ),
}

KNOWN_MILESTONES = frozenset({"SRR", "PDR", "CDR", "QR", "AR"})


def validate_baseline_type(baseline_type):
    """baseline_type unchanged if it is one of BASELINE_ORDER, else
    raises ValueError."""
    if baseline_type not in BASELINE_ORDER:
        raise ValueError(
            "unrecognized configuration baseline type %r under "
            "E-ST-10C clause 5.4.2.2" % (baseline_type,)
        )
    return baseline_type


def validate_milestone(milestone):
    """milestone unchanged if it is a known program review milestone,
    else raises ValueError."""
    if milestone not in KNOWN_MILESTONES:
        raise ValueError("unrecognized program milestone %r" % (milestone,))
    return milestone


def required_milestone(baseline_type):
    """Gating review milestone for a baseline type. Raises ValueError
    for an unrecognized baseline type."""
    validate_baseline_type(baseline_type)
    return BASELINE_MILESTONE[baseline_type]


def required_artifacts(baseline_type):
    """Frozen set of configuration-management artifact ids required to
    establish a baseline type. Raises ValueError for an unrecognized
    baseline type."""
    validate_baseline_type(baseline_type)
    return BASELINE_REQUIRED_ARTIFACTS[baseline_type]


def prior_baseline_types(baseline_type):
    """Tuple of baseline types that must already be established before
    baseline_type, in sequence order. Raises ValueError for an
    unrecognized baseline type."""
    validate_baseline_type(baseline_type)
    index = BASELINE_ORDER.index(baseline_type)
    return BASELINE_ORDER[:index]


def sequence_violations(baseline_type, established_baselines):
    """Violation list (empty if in sequence) for establishing
    baseline_type given the set of baseline types already established.
    Flags any earlier baseline in BASELINE_ORDER that is not yet
    established. Raises ValueError for an unrecognized baseline type."""
    missing = [
        prior
        for prior in prior_baseline_types(baseline_type)
        if prior not in established_baselines
    ]
    if missing:
        return [
            {
                "issue": "out_of_sequence_baseline",
                "baseline": baseline_type,
                "missing_prior": missing,
            }
        ]
    return []


def milestone_violations(baseline_type, completed_milestones):
    """Violation list (empty if the gate is passed) for establishing
    baseline_type given the set of completed program milestones. Raises
    ValueError for an unrecognized baseline type."""
    milestone = required_milestone(baseline_type)
    if milestone not in completed_milestones:
        return [
            {
                "issue": "milestone_not_passed",
                "baseline": baseline_type,
                "required_milestone": milestone,
            }
        ]
    return []


def artifact_violations(baseline_type, available_artifacts):
    """Violation list (empty if complete) for establishing baseline_type
    given the set of available configuration-management artifact ids.
    Raises ValueError for an unrecognized baseline type."""
    missing = sorted(required_artifacts(baseline_type) - set(available_artifacts))
    if missing:
        return [
            {
                "issue": "missing_baseline_artifacts",
                "baseline": baseline_type,
                "missing_artifacts": missing,
            }
        ]
    return []


def evaluate_baseline(baseline_type, completed_milestones, established_baselines, available_artifacts):
    """Aggregated violation list for one baseline type: sequence check,
    milestone-gate check, then artifact completeness check. An empty
    list means the baseline is ready to establish. Raises ValueError for
    an unrecognized baseline type. Does not mutate any input."""
    violations = []
    violations.extend(sequence_violations(baseline_type, established_baselines))
    violations.extend(milestone_violations(baseline_type, completed_milestones))
    violations.extend(artifact_violations(baseline_type, available_artifacts))
    return violations


def is_baseline_ready(violations):
    """True when an evaluate_baseline violation list is empty."""
    return len(violations) == 0


def configuration_baseline_review(program):
    """Full clause 5.4.2.2 review across all three baseline types.

    program: {"completed_milestones": iterable of milestone names,
    "established_baselines": iterable of baseline types already
    established, "artifacts": {baseline_type: iterable of artifact
    ids}}. Returns {baseline_type: [violation, ...]} for every type in
    BASELINE_ORDER. Raises ValueError for an unrecognized milestone
    name or an unrecognized established baseline type. Does not mutate
    program."""
    completed_milestones = set(program.get("completed_milestones", []))
    for milestone in completed_milestones:
        validate_milestone(milestone)
    established_baselines = set(program.get("established_baselines", []))
    for baseline_type in established_baselines:
        validate_baseline_type(baseline_type)
    artifacts_by_baseline = program.get("artifacts", {})

    review = {}
    for baseline_type in BASELINE_ORDER:
        available_artifacts = set(artifacts_by_baseline.get(baseline_type, []))
        review[baseline_type] = evaluate_baseline(
            baseline_type, completed_milestones, established_baselines, available_artifacts
        )
    return review


def is_baseline_program_compliant(review):
    """True when every baseline type in a configuration_baseline_review
    result has an empty violation list."""
    return all(len(violations) == 0 for violations in review.values())


def next_establishable_baseline(established_baselines, completed_milestones):
    """The earliest not-yet-established baseline type (in BASELINE_ORDER)
    whose milestone gate has already passed, or None if the next
    baseline in sequence has not reached its milestone yet. Enforces
    sequence: a later baseline's passed milestone is never returned
    ahead of an earlier, still-unestablished baseline. Does not check
    artifact completeness -- pair with evaluate_baseline for the full
    gate. Raises ValueError for an unrecognized milestone name."""
    established_baselines = set(established_baselines)
    completed_milestones = set(completed_milestones)
    for milestone in completed_milestones:
        validate_milestone(milestone)
    for baseline_type in BASELINE_ORDER:
        if baseline_type in established_baselines:
            continue
        milestone = BASELINE_MILESTONE[baseline_type]
        if milestone in completed_milestones:
            return baseline_type
        return None
    return None
