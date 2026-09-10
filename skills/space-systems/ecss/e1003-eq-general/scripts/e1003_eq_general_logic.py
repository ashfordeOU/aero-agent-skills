#!/usr/bin/env python3
"""ECSS-E-ST-10-03C clause 5.1 general equipment test requirements
(paraphrase, not copy).

Common-knowledge summary (standards-map.yaml, ecss: gated false): the
equipment test programme carries rules that apply regardless of which
baseline (qualification, acceptance, protoflight) is run -- which test
model is entitled to which campaign, how the test configuration must
relate to the flight configuration, when interface checks are
mandatory, and when functional and performance tests must be run. This
module implements the model-applicability check, the test-configuration
check, the interface-check bookend rule, and the functional/
performance-test rules; it does not define the qualification,
acceptance, or protoflight test baselines themselves (see the sibling
e1003-eq-qual / e1003-eq-acceptance / e1003-eq-protoflight leaves) and
does not define the test models (see the sibling e1002-models leaf).
"""

MODEL_CAMPAIGN = {
    "QM": "qualification",
    "PFM": "protoflight",
    "FM": "acceptance",
}


def required_campaign(model):
    """Test campaign the given model is entitled to run under clause
    5.1 ("QM" -> "qualification", "PFM" -> "protoflight", "FM" ->
    "acceptance"). Raises ValueError for a model that carries no formal
    equipment test campaign under this clause (e.g. "EM")."""
    if model not in MODEL_CAMPAIGN:
        raise ValueError(
            "model %r carries no formal equipment test campaign under "
            "E-ST-10-03C clause 5.1" % (model,)
        )
    return MODEL_CAMPAIGN[model]


def model_applicability_violations(model, campaign):
    """Violation list (empty if compliant) for running the given
    campaign against the given test model. A single-entry list is
    returned when the model is not entitled to that campaign."""
    expected = required_campaign(model)
    if expected == campaign:
        return []
    return [
        {
            "issue": "campaign_not_applicable_to_model",
            "model": model,
            "campaign": campaign,
            "expected_campaign": expected,
        }
    ]


def configuration_violations(configuration, required_interfaces):
    """Violation list (empty if compliant) for a test configuration.

    configuration: {"representative": bool, "deviations": [str, ...],
    "interfaces_simulated": [str, ...]}. required_interfaces: iterable
    of interface ids the campaign depends on. Flags an unrepresentative
    configuration with no recorded deviation, and any required
    interface not represented by GSE or a simulator. Does not mutate
    either input."""
    violations = []
    representative = configuration.get("representative", False)
    deviations = configuration.get("deviations") or []
    if not representative and not deviations:
        violations.append({"issue": "unrepresentative_configuration_undocumented"})
    simulated = set(configuration.get("interfaces_simulated") or [])
    for interface_id in required_interfaces:
        if interface_id not in simulated:
            violations.append({"issue": "interface_not_simulated", "interface": interface_id})
    return violations


def missing_interface_checks(test_sequence):
    """Violation list (empty if compliant) for the mandatory interface-
    check bookends: a pre-interface check on the first step, a post-
    interface check on the last step. test_sequence: non-empty list of
    step dicts with boolean keys "pre_interface_check" and
    "post_interface_check". Raises ValueError if test_sequence is
    empty."""
    if not test_sequence:
        raise ValueError("test sequence is empty")
    violations = []
    if not test_sequence[0].get("pre_interface_check"):
        violations.append({"issue": "missing_pre_interface_check", "step": 0})
    last_index = len(test_sequence) - 1
    if not test_sequence[-1].get("post_interface_check"):
        violations.append({"issue": "missing_post_interface_check", "step": last_index})
    return violations


def functional_test_gaps(test_sequence):
    """Violation list (empty if compliant) for the functional-test
    rule: every step carries a functional test immediately before and
    immediately after it, keyed "functional_test_before" and
    "functional_test_after". Raises ValueError if test_sequence is
    empty."""
    if not test_sequence:
        raise ValueError("test sequence is empty")
    gaps = []
    for index, step in enumerate(test_sequence):
        if not step.get("functional_test_before"):
            gaps.append({"issue": "missing_functional_test_before", "step": index})
        if not step.get("functional_test_after"):
            gaps.append({"issue": "missing_functional_test_after", "step": index})
    return gaps


def missing_performance_tests(test_sequence):
    """Violation list (empty if compliant) for the performance-test
    bookend rule: the first and last steps carry a performance test,
    keyed "performance_test". Raises ValueError if test_sequence is
    empty."""
    if not test_sequence:
        raise ValueError("test sequence is empty")
    violations = []
    if not test_sequence[0].get("performance_test"):
        violations.append({"issue": "missing_performance_test", "step": 0})
    last_index = len(test_sequence) - 1
    if not test_sequence[-1].get("performance_test"):
        violations.append({"issue": "missing_performance_test", "step": last_index})
    return violations


def general_equipment_test_review(model, campaign, configuration, required_interfaces, test_sequence):
    """Full clause 5.1 general-requirements review for one equipment
    test campaign. Returns a dict keyed "model_applicability",
    "configuration", "interface_checks", "functional_tests",
    "performance_tests", each a violation list (empty means that rule
    is satisfied). Raises ValueError if test_sequence is empty or model
    is unknown."""
    return {
        "model_applicability": model_applicability_violations(model, campaign),
        "configuration": configuration_violations(configuration, required_interfaces),
        "interface_checks": missing_interface_checks(test_sequence),
        "functional_tests": functional_test_gaps(test_sequence),
        "performance_tests": missing_performance_tests(test_sequence),
    }


def is_general_compliant(review):
    """True when every category in a general_equipment_test_review
    result is empty -- the campaign satisfies clause 5.1 and is ready
    for its baseline (qualification/acceptance/protoflight) selection."""
    return all(len(violations) == 0 for violations in review.values())
