#!/usr/bin/env python3
"""Gate 3 contract test: ECSS-E-ST-10-03C §6.4 element protoflight test
baseline.

Exercises scripts/e1003_el_protoflight_logic.py (stdlib unittest,
offline). Contract: docs/harness-contract.md gate 3 - an element with
no dedicated qualification model is categorized as following the
protoflight approach and one with a dedicated model follows
qualification-acceptance; a test spec missing required keys or with
qualification weaker than acceptance is rejected; the baseline for a
valid spec sets level to the qualification level and duration to the
acceptance duration; a matrix rejects duplicate test types and flags
missing required entries; a proposed entry is flagged as a deviation
when its level or duration does not match the standard rule, unless it
carries an approved deviation; an element is ready for protoflight only
when its approach is protoflight and the matrix is complete.
"""

import os
import sys
import unittest

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import e1003_el_protoflight_logic as el  # noqa: E402

_VALID_SPEC = {
    "qualification_level": 20.0,
    "qualification_duration": 120.0,
    "acceptance_level": 10.0,
    "acceptance_duration": 60.0,
}


class DetermineElementApproachTest(unittest.TestCase):
    def test_no_dedicated_model_is_protoflight(self):
        element = {"id": "EL-01", "dedicated_qualification_model": False}
        self.assertEqual(el.determine_element_approach(element), "protoflight")

    def test_dedicated_model_is_qualification_acceptance(self):
        element = {"id": "EL-02", "dedicated_qualification_model": True}
        self.assertEqual(
            el.determine_element_approach(element), "qualification_acceptance"
        )

    def test_missing_key_raises(self):
        with self.assertRaises(ValueError):
            el.determine_element_approach({"id": "EL-03"})


class ValidateTestSpecTest(unittest.TestCase):
    def test_valid_spec_has_no_violations(self):
        self.assertEqual(el.validate_test_spec(_VALID_SPEC), [])

    def test_missing_qualification_level_flagged(self):
        spec = {k: v for k, v in _VALID_SPEC.items() if k != "qualification_level"}
        self.assertIn("qualification_level", el.validate_test_spec(spec))

    def test_missing_acceptance_duration_flagged(self):
        spec = {k: v for k, v in _VALID_SPEC.items() if k != "acceptance_duration"}
        self.assertIn("acceptance_duration", el.validate_test_spec(spec))

    def test_qual_level_below_acceptance_level_flagged(self):
        spec = dict(_VALID_SPEC, qualification_level=5.0)
        violations = el.validate_test_spec(spec)
        self.assertIn("qualification_level_below_acceptance_level", violations)

    def test_qual_duration_below_acceptance_duration_flagged(self):
        spec = dict(_VALID_SPEC, qualification_duration=30.0)
        violations = el.validate_test_spec(spec)
        self.assertIn("qualification_duration_below_acceptance_duration", violations)

    def test_equal_level_is_acceptable(self):
        spec = dict(_VALID_SPEC, qualification_level=10.0, acceptance_level=10.0)
        self.assertEqual(el.validate_test_spec(spec), [])

    def test_valid_spec_is_not_mutated(self):
        original = dict(_VALID_SPEC)
        el.validate_test_spec(original)
        self.assertEqual(original, _VALID_SPEC)


class DeriveBaselineTest(unittest.TestCase):
    def test_level_is_qualification_level(self):
        baseline = el.derive_baseline("thermal_vacuum", _VALID_SPEC)
        self.assertEqual(baseline["level"], _VALID_SPEC["qualification_level"])

    def test_duration_is_acceptance_duration(self):
        baseline = el.derive_baseline("thermal_vacuum", _VALID_SPEC)
        self.assertEqual(baseline["duration"], _VALID_SPEC["acceptance_duration"])

    def test_test_type_preserved(self):
        baseline = el.derive_baseline("sine_vibration", _VALID_SPEC)
        self.assertEqual(baseline["test_type"], "sine_vibration")

    def test_invalid_spec_raises(self):
        bad_spec = dict(_VALID_SPEC, qualification_level=1.0)
        with self.assertRaises(ValueError):
            el.derive_baseline("random_vibration", bad_spec)


class BuildBaselineMatrixTest(unittest.TestCase):
    def _entry(self, test_type):
        return dict(_VALID_SPEC, test_type=test_type)

    def test_single_entry_matrix(self):
        matrix = el.build_baseline_matrix([self._entry("shock")])
        self.assertEqual(len(matrix), 1)
        self.assertEqual(matrix[0]["test_type"], "shock")

    def test_multiple_entries_in_order(self):
        types = ["sine_vibration", "thermal_vacuum", "acoustic"]
        matrix = el.build_baseline_matrix([self._entry(t) for t in types])
        self.assertEqual([e["test_type"] for e in matrix], types)

    def test_duplicate_test_type_raises(self):
        entries = [self._entry("shock"), self._entry("shock")]
        with self.assertRaises(ValueError):
            el.build_baseline_matrix(entries)

    def test_missing_test_type_key_raises(self):
        with self.assertRaises(ValueError):
            el.build_baseline_matrix([dict(_VALID_SPEC)])


class BaselineGapsTest(unittest.TestCase):
    def _matrix_from_types(self, types):
        return [{"test_type": t, "level": 20.0, "duration": 60.0} for t in types]

    def test_no_gaps_when_all_required_present(self):
        required = ["sine_vibration", "thermal_vacuum"]
        matrix = self._matrix_from_types(required)
        self.assertEqual(el.baseline_gaps(required, matrix), [])

    def test_missing_type_reported(self):
        required = ["sine_vibration", "thermal_vacuum", "acoustic"]
        matrix = self._matrix_from_types(["sine_vibration", "thermal_vacuum"])
        self.assertEqual(el.baseline_gaps(required, matrix), ["acoustic"])

    def test_gaps_in_required_order(self):
        required = ["a", "b", "c"]
        matrix = self._matrix_from_types(["b"])
        self.assertEqual(el.baseline_gaps(required, matrix), ["a", "c"])


class MatchesStandardRuleTest(unittest.TestCase):
    def test_exact_match_returns_true(self):
        entry = {"test_type": "emc", "level": 20.0, "duration": 60.0}
        self.assertTrue(el.matches_standard_rule(entry, _VALID_SPEC))

    def test_wrong_level_returns_false(self):
        entry = {"test_type": "emc", "level": 15.0, "duration": 60.0}
        self.assertFalse(el.matches_standard_rule(entry, _VALID_SPEC))

    def test_wrong_duration_returns_false(self):
        entry = {"test_type": "emc", "level": 20.0, "duration": 90.0}
        self.assertFalse(el.matches_standard_rule(entry, _VALID_SPEC))


class FlagDeviationsTest(unittest.TestCase):
    def _entry(self, test_type, level, duration):
        return {"test_type": test_type, "level": level, "duration": duration}

    def test_compliant_entry_not_flagged(self):
        matrix = [self._entry("thermal_vacuum", 20.0, 60.0)]
        specs = {"thermal_vacuum": _VALID_SPEC}
        self.assertEqual(el.flag_deviations(matrix, specs), [])

    def test_deviant_level_flagged(self):
        matrix = [self._entry("thermal_vacuum", 25.0, 60.0)]
        specs = {"thermal_vacuum": _VALID_SPEC}
        self.assertEqual(el.flag_deviations(matrix, specs), ["thermal_vacuum"])

    def test_deviant_duration_flagged(self):
        matrix = [self._entry("thermal_vacuum", 20.0, 90.0)]
        specs = {"thermal_vacuum": _VALID_SPEC}
        self.assertEqual(el.flag_deviations(matrix, specs), ["thermal_vacuum"])

    def test_approved_deviation_not_flagged(self):
        matrix = [self._entry("thermal_vacuum", 25.0, 60.0)]
        specs = {"thermal_vacuum": _VALID_SPEC}
        self.assertEqual(
            el.flag_deviations(matrix, specs, approved_deviations={"thermal_vacuum"}),
            [],
        )

    def test_entry_absent_from_specs_skipped(self):
        matrix = [self._entry("unknown_test", 99.0, 99.0)]
        self.assertEqual(el.flag_deviations(matrix, {}), [])

    def test_multiple_entries_flags_only_deviants(self):
        matrix = [
            self._entry("sine_vibration", 20.0, 60.0),
            self._entry("acoustic", 50.0, 60.0),
        ]
        specs = {"sine_vibration": _VALID_SPEC, "acoustic": _VALID_SPEC}
        self.assertEqual(el.flag_deviations(matrix, specs), ["acoustic"])


class ElementReadyForProtoflightTest(unittest.TestCase):
    def _matrix(self, types):
        return [{"test_type": t, "level": 20.0, "duration": 60.0} for t in types]

    def test_protoflight_element_with_complete_matrix_is_ready(self):
        element = {"id": "EL-10", "dedicated_qualification_model": False}
        matrix = self._matrix(["sine_vibration", "thermal_vacuum"])
        self.assertTrue(
            el.element_ready_for_protoflight(
                element, matrix, ["sine_vibration", "thermal_vacuum"]
            )
        )

    def test_qual_acceptance_element_not_ready_even_with_complete_matrix(self):
        element = {"id": "EL-11", "dedicated_qualification_model": True}
        matrix = self._matrix(["sine_vibration", "thermal_vacuum"])
        self.assertFalse(
            el.element_ready_for_protoflight(
                element, matrix, ["sine_vibration", "thermal_vacuum"]
            )
        )

    def test_protoflight_element_with_incomplete_matrix_not_ready(self):
        element = {"id": "EL-12", "dedicated_qualification_model": False}
        matrix = self._matrix(["sine_vibration"])
        self.assertFalse(
            el.element_ready_for_protoflight(
                element, matrix, ["sine_vibration", "thermal_vacuum"]
            )
        )

    def test_empty_required_list_is_complete(self):
        element = {"id": "EL-13", "dedicated_qualification_model": False}
        self.assertTrue(el.element_ready_for_protoflight(element, [], []))


if __name__ == "__main__":
    unittest.main()
