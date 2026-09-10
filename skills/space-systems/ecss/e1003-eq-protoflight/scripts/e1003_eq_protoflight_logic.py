#!/usr/bin/env python3
"""ECSS-E-ST-10-03C clause 5.4 equipment protoflight test baseline
(paraphrase, not copy).

Common-knowledge summary (standards-map.yaml, ecss: gated false): an
equipment item follows the protoflight test approach when a single
hardware model must demonstrate both design qualification and flight
acceptance (no separate, dedicated qualification model). Table 5-5
gives, per test type, the qualification-level and acceptance-level
test severities (qualification carries more margin); Table 5-6 gives
the associated qualification and acceptance durations/cycle counts
(qualification runs longer). The protoflight baseline combines the
two: test level set at the qualification level, test duration set at
the acceptance duration, so the flight article demonstrates
qualification-level margin without the full qualification exposure.
This module implements the approach classification, the baseline
derivation, matrix completeness, and deviation-flagging logic; it does
not draft the test specification or procedure itself.
"""

REQUIRED_SPEC_KEYS = (
    "qualification_level",
    "qualification_duration",
    "acceptance_level",
    "acceptance_duration",
)


def classify_equipment_approach(equipment):
    """Test approach for one equipment dict (key:
    'dedicated_qualification_model', bool). Returns 'protoflight' when
    no dedicated qualification model exists, otherwise
    'qualification_acceptance'. Raises ValueError if the key is
    missing."""
    if "dedicated_qualification_model" not in equipment:
        raise ValueError(
            "equipment %r missing 'dedicated_qualification_model'" % (equipment.get("id"),)
        )
    if equipment["dedicated_qualification_model"]:
        return "qualification_acceptance"
    return "protoflight"


def validate_test_spec(spec):
    """Violations in a test-type spec (keys: qualification_level,
    qualification_duration, acceptance_level, acceptance_duration).
    Reports a missing key, or a qualification level/duration weaker
    than the acceptance one. Returns a list of violation strings; does
    not mutate the input."""
    violations = [key for key in REQUIRED_SPEC_KEYS if key not in spec]
    if violations:
        return violations
    if spec["qualification_level"] < spec["acceptance_level"]:
        violations.append("qualification_level_below_acceptance_level")
    if spec["qualification_duration"] < spec["acceptance_duration"]:
        violations.append("qualification_duration_below_acceptance_duration")
    return violations


def derive_baseline(test_type, spec):
    """Protoflight baseline for one test type: level = qualification
    level, duration = acceptance duration. Raises ValueError when
    validate_test_spec finds any violation in spec."""
    violations = validate_test_spec(spec)
    if violations:
        raise ValueError("invalid test spec for %r: %s" % (test_type, violations))
    return {
        "test_type": test_type,
        "level": spec["qualification_level"],
        "duration": spec["acceptance_duration"],
    }


def build_baseline_matrix(test_entries):
    """Protoflight baseline matrix for a list of test entries (each a
    dict with 'test_type' plus the REQUIRED_SPEC_KEYS). Returns one
    baseline dict per entry, in input order. Raises ValueError for an
    entry missing a test_type, a duplicate test_type, or an invalid
    spec."""
    matrix = []
    seen = set()
    for entry in test_entries:
        if "test_type" not in entry:
            raise ValueError("test entry is missing a test_type")
        test_type = entry["test_type"]
        if test_type in seen:
            raise ValueError("duplicate test_type: %r" % (test_type,))
        seen.add(test_type)
        spec = {key: entry[key] for key in REQUIRED_SPEC_KEYS if key in entry}
        matrix.append(derive_baseline(test_type, spec))
    return matrix


def baseline_gaps(required_test_types, matrix):
    """Test types present in required_test_types but absent from the
    baseline matrix, in required_test_types order -- the completeness
    check for 'every required test type has a baseline'."""
    present = {entry["test_type"] for entry in matrix}
    return [test_type for test_type in required_test_types if test_type not in present]


def matches_standard_rule(entry, spec):
    """True when a baseline entry follows the standard protoflight
    rule for spec: level equals the qualification level and duration
    equals the acceptance duration."""
    return (
        entry["level"] == spec["qualification_level"]
        and entry["duration"] == spec["acceptance_duration"]
    )


def flag_deviations(proposed_matrix, specs_by_type, approved_deviations=frozenset()):
    """Test types in proposed_matrix whose level or duration does not
    match the standard-rule baseline derived from specs_by_type (dict
    test_type -> spec), skipping any test type already listed in
    approved_deviations or absent from specs_by_type. Returned in
    proposed_matrix order."""
    flagged = []
    for entry in proposed_matrix:
        test_type = entry["test_type"]
        if test_type in approved_deviations:
            continue
        spec = specs_by_type.get(test_type)
        if spec is None:
            continue
        if not matches_standard_rule(entry, spec):
            flagged.append(test_type)
    return flagged


def equipment_ready_for_protoflight(equipment, matrix, required_test_types):
    """True only when equipment is categorized as following the
    protoflight approach and its baseline matrix has no missing
    required test types."""
    if classify_equipment_approach(equipment) != "protoflight":
        return False
    return len(baseline_gaps(required_test_types, matrix)) == 0
