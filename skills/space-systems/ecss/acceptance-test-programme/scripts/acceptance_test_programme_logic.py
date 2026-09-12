#!/usr/bin/env python3
"""ECSS-E-ST-32C clause 5.5 acceptance proof and leak test programme
(paraphrase, not copy).

Common-knowledge summary (standards-map.yaml, ecss: gated false): the
structural mechanical systems standard's acceptance test clause requires
two test families for flight hardware: proof tests (applied pressure
sustained for a minimum hold duration at acceptance level to demonstrate
structural integrity at the maximum design pressure) and leak tests
(measured leak rate compared against the allowable limit from the sealing
requirement). The programme passes only when every individual test item
in both families records a pass. This module implements proof-pressure
computation, proof-test condition checking, leak-test evaluation, and
programme-level aggregation; it does not define the test procedure steps
themselves or the analytical methods for deriving MDP.
"""

ACCEPTED_TEST_TYPES = frozenset({"proof", "leak"})

# Acceptance-level proof factor for flight hardware per ECSS-E-ST-32C
# clause 5.5 (1.0 × MDP, distinct from the qualification proof factor).
ACCEPTANCE_PROOF_FACTOR = 1.0

# Minimum hold duration at proof pressure (seconds). Assemblies not
# holding for at least this duration have an inconclusive proof test.
MIN_PROOF_HOLD_DURATION_S = 300


def validate_test_type(test_type):
    """Confirm test_type is a recognized acceptance test family:
    "proof" or "leak". Raises ValueError for any other value."""
    if test_type not in ACCEPTED_TEST_TYPES:
        raise ValueError(
            "unrecognized acceptance test type %r; expected one of %s"
            % (test_type, sorted(ACCEPTED_TEST_TYPES))
        )
    return test_type


def compute_proof_pressure(mdp_kpa, proof_factor):
    """Required proof pressure (kPa) = MDP × proof_factor.
    Raises ValueError for a non-positive MDP or a non-positive factor."""
    if mdp_kpa <= 0:
        raise ValueError("mdp_kpa must be > 0, got %r" % (mdp_kpa,))
    if proof_factor <= 0:
        raise ValueError("proof_factor must be > 0, got %r" % (proof_factor,))
    return mdp_kpa * proof_factor


def check_proof_test(
    test_id,
    applied_pressure_kpa,
    required_proof_pressure_kpa,
    hold_duration_s,
    min_hold_duration_s=MIN_PROOF_HOLD_DURATION_S,
):
    """Violation list (empty if compliant) for one proof test item.
    applied_pressure_kpa: highest pressure reached during the test.
    required_proof_pressure_kpa: computed from compute_proof_pressure.
    hold_duration_s: time the applied pressure was sustained.
    min_hold_duration_s: minimum dwell requirement (default constant).
    Does not raise; violations are returned as structured dicts."""
    violations = []
    if applied_pressure_kpa < required_proof_pressure_kpa:
        violations.append(
            {
                "issue": "proof_pressure_not_reached",
                "test_id": test_id,
                "required_kpa": required_proof_pressure_kpa,
                "applied_kpa": applied_pressure_kpa,
            }
        )
    if hold_duration_s < min_hold_duration_s:
        violations.append(
            {
                "issue": "hold_duration_insufficient",
                "test_id": test_id,
                "required_s": min_hold_duration_s,
                "actual_s": hold_duration_s,
            }
        )
    return violations


def check_leak_test(test_id, measured_leak_rate, allowable_leak_rate):
    """Violation list (empty if compliant) for one leak test item.
    measured_leak_rate: recorded leak rate in test-consistent units.
    allowable_leak_rate: limit from the sealing requirement, or None
    if the requirement was never captured (itself a finding).
    Raises ValueError for a negative measured rate."""
    if measured_leak_rate < 0:
        raise ValueError(
            "measured_leak_rate must be >= 0, got %r" % (measured_leak_rate,)
        )
    if allowable_leak_rate is None:
        return [
            {
                "issue": "missing_allowable_leak_rate",
                "test_id": test_id,
                "measured": measured_leak_rate,
            }
        ]
    if allowable_leak_rate <= 0:
        raise ValueError(
            "allowable_leak_rate must be > 0 when provided, got %r"
            % (allowable_leak_rate,)
        )
    if measured_leak_rate > allowable_leak_rate:
        return [
            {
                "issue": "leak_rate_exceeded",
                "test_id": test_id,
                "allowable": allowable_leak_rate,
                "measured": measured_leak_rate,
            }
        ]
    return []


def acceptance_test_result(test_item):
    """Full acceptance result for one test item.

    test_item for proof: {"test_id": str, "test_type": "proof",
      "applied_pressure_kpa": float, "required_proof_pressure_kpa": float,
      "hold_duration_s": float}.
    test_item for leak: {"test_id": str, "test_type": "leak",
      "measured_leak_rate": float, "allowable_leak_rate": float | None}.

    Returns {"test_id": str, "test_type": str, "violations": list,
      "passed": bool}. Raises ValueError for an unrecognized test_type
    or an invalid field value."""
    test_id = test_item["test_id"]
    test_type = validate_test_type(test_item["test_type"])
    if test_type == "proof":
        violations = check_proof_test(
            test_id,
            test_item["applied_pressure_kpa"],
            test_item["required_proof_pressure_kpa"],
            test_item["hold_duration_s"],
        )
    else:
        violations = check_leak_test(
            test_id,
            test_item["measured_leak_rate"],
            test_item["allowable_leak_rate"],
        )
    return {
        "test_id": test_id,
        "test_type": test_type,
        "violations": violations,
        "passed": len(violations) == 0,
    }


def acceptance_programme_result(test_items):
    """Overall acceptance programme result for a list of test items.
    Returns {"results": [acceptance_test_result, ...],
      "programme_passed": bool}. Programme passes only when every
    individual item passes. Does not mutate test_items."""
    results = [acceptance_test_result(item) for item in test_items]
    programme_passed = all(r["passed"] for r in results)
    return {"results": results, "programme_passed": programme_passed}
