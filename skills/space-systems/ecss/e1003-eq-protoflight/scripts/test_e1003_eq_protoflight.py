#!/usr/bin/env python3
"""Gate 3 contract test: ECSS-E-ST-10-03C clause 5.4 equipment
protoflight test baseline.

Exercises scripts/e1003_eq_protoflight_logic.py (stdlib unittest,
offline). Contract: docs/harness-contract.md gate 3 - equipment with no
dedicated qualification model is categorized as protoflight, otherwise
qualification_acceptance; a test spec is rejected when its
qualification level/duration is weaker than its acceptance
level/duration; the protoflight baseline for a test type sets level to
the qualification level and duration to the acceptance duration; the
baseline matrix rejects a duplicate test type and reports any required
test type still missing; a proposed baseline entry that departs from
the standard rule is flagged unless it has an approved deviation; and
equipment is only reported ready for protoflight testing when it is
categorized as protoflight and its baseline matrix has no gaps.
"""

import os
import sys
import unittest

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import e1003_eq_protoflight_logic as pf  # noqa: E402


VIBRATION_SPEC = {
    "qualification_level": 10.0,
    "qualification_duration": 120,
    "acceptance_level": 7.0,
    "acceptance_duration": 60,
}

THERMAL_VAC_SPEC = {
    "qualification_level": 20,
    "qualification_duration": 8,
    "acceptance_level": 15,
    "acceptance_duration": 4,
}


class ClassifyEquipmentApproachTest(unittest.TestCase):
    def test_no_dedicated_model_is_protoflight(self):
        self.assertEqual(
            pf.classify_equipment_approach({"id": "EQ-1", "dedicated_qualification_model": False}),
            "protoflight",
        )

    def test_dedicated_model_is_qualification_acceptance(self):
        self.assertEqual(
            pf.classify_equipment_approach({"id": "EQ-2", "dedicated_qualification_model": True}),
            "qualification_acceptance",
        )

    def test_missing_key_raises(self):
        with self.assertRaises(ValueError):
            pf.classify_equipment_approach({"id": "EQ-3"})


class ValidateTestSpecTest(unittest.TestCase):
    def test_valid_spec_has_no_violations(self):
        self.assertEqual(pf.validate_test_spec(VIBRATION_SPEC), [])

    def test_missing_keys_reported(self):
        violations = pf.validate_test_spec({"qualification_level": 10.0})
        self.assertIn("qualification_duration", violations)
        self.assertIn("acceptance_level", violations)
        self.assertIn("acceptance_duration", violations)

    def test_qualification_level_below_acceptance_flagged(self):
        spec = dict(VIBRATION_SPEC, qualification_level=5.0)
        self.assertIn("qualification_level_below_acceptance_level", pf.validate_test_spec(spec))

    def test_qualification_duration_below_acceptance_flagged(self):
        spec = dict(VIBRATION_SPEC, qualification_duration=30)
        self.assertIn(
            "qualification_duration_below_acceptance_duration", pf.validate_test_spec(spec)
        )

    def test_does_not_mutate_input(self):
        before = dict(VIBRATION_SPEC)
        pf.validate_test_spec(VIBRATION_SPEC)
        self.assertEqual(VIBRATION_SPEC, before)


class DeriveBaselineTest(unittest.TestCase):
    def test_level_is_qualification_duration_is_acceptance(self):
        self.assertEqual(
            pf.derive_baseline("vibration", VIBRATION_SPEC),
            {"test_type": "vibration", "level": 10.0, "duration": 60},
        )

    def test_invalid_spec_raises(self):
        with self.assertRaises(ValueError):
            pf.derive_baseline("vibration", {"qualification_level": 5.0, "acceptance_level": 7.0})


class BuildBaselineMatrixTest(unittest.TestCase):
    ENTRIES = [
        dict(VIBRATION_SPEC, test_type="vibration"),
        dict(THERMAL_VAC_SPEC, test_type="thermal_vacuum"),
    ]

    def test_matrix_order_and_content(self):
        matrix = pf.build_baseline_matrix(self.ENTRIES)
        self.assertEqual(
            matrix,
            [
                {"test_type": "vibration", "level": 10.0, "duration": 60},
                {"test_type": "thermal_vacuum", "level": 20, "duration": 4},
            ],
        )

    def test_duplicate_test_type_raises(self):
        with self.assertRaises(ValueError):
            pf.build_baseline_matrix(self.ENTRIES + [self.ENTRIES[0]])

    def test_missing_test_type_raises(self):
        with self.assertRaises(ValueError):
            pf.build_baseline_matrix([dict(VIBRATION_SPEC)])

    def test_invalid_entry_raises(self):
        bad_entry = dict(VIBRATION_SPEC, test_type="emc", qualification_level=1.0)
        with self.assertRaises(ValueError):
            pf.build_baseline_matrix([bad_entry])

    def test_does_not_mutate_input(self):
        before = [dict(e) for e in self.ENTRIES]
        pf.build_baseline_matrix(self.ENTRIES)
        self.assertEqual(self.ENTRIES, before)


class BaselineGapsTest(unittest.TestCase):
    def test_detects_gap(self):
        matrix = [{"test_type": "vibration", "level": 10.0, "duration": 60}]
        self.assertEqual(
            pf.baseline_gaps(["vibration", "thermal_vacuum"], matrix),
            ["thermal_vacuum"],
        )

    def test_no_gap(self):
        matrix = [{"test_type": "vibration", "level": 10.0, "duration": 60}]
        self.assertEqual(pf.baseline_gaps(["vibration"], matrix), [])


class MatchesStandardRuleTest(unittest.TestCase):
    def test_matching_entry(self):
        entry = {"test_type": "vibration", "level": 10.0, "duration": 60}
        self.assertTrue(pf.matches_standard_rule(entry, VIBRATION_SPEC))

    def test_mismatched_level(self):
        entry = {"test_type": "vibration", "level": 9.0, "duration": 60}
        self.assertFalse(pf.matches_standard_rule(entry, VIBRATION_SPEC))

    def test_mismatched_duration(self):
        entry = {"test_type": "vibration", "level": 10.0, "duration": 90}
        self.assertFalse(pf.matches_standard_rule(entry, VIBRATION_SPEC))


class FlagDeviationsTest(unittest.TestCase):
    SPECS_BY_TYPE = {"vibration": VIBRATION_SPEC, "thermal_vacuum": THERMAL_VAC_SPEC}

    def test_no_deviation_when_matching(self):
        matrix = [
            {"test_type": "vibration", "level": 10.0, "duration": 60},
            {"test_type": "thermal_vacuum", "level": 20, "duration": 4},
        ]
        self.assertEqual(pf.flag_deviations(matrix, self.SPECS_BY_TYPE), [])

    def test_deviation_flagged(self):
        matrix = [{"test_type": "vibration", "level": 9.0, "duration": 60}]
        self.assertEqual(pf.flag_deviations(matrix, self.SPECS_BY_TYPE), ["vibration"])

    def test_approved_deviation_not_flagged(self):
        matrix = [{"test_type": "vibration", "level": 9.0, "duration": 60}]
        self.assertEqual(
            pf.flag_deviations(matrix, self.SPECS_BY_TYPE, approved_deviations={"vibration"}),
            [],
        )

    def test_unknown_test_type_skipped(self):
        matrix = [{"test_type": "emc", "level": 1.0, "duration": 1}]
        self.assertEqual(pf.flag_deviations(matrix, self.SPECS_BY_TYPE), [])


class EquipmentReadyForProtoflightTest(unittest.TestCase):
    MATRIX = [
        {"test_type": "vibration", "level": 10.0, "duration": 60},
        {"test_type": "thermal_vacuum", "level": 20, "duration": 4},
    ]

    def test_ready_when_protoflight_and_complete(self):
        equipment = {"id": "EQ-1", "dedicated_qualification_model": False}
        self.assertTrue(
            pf.equipment_ready_for_protoflight(equipment, self.MATRIX, ["vibration", "thermal_vacuum"])
        )

    def test_not_ready_when_not_protoflight(self):
        equipment = {"id": "EQ-2", "dedicated_qualification_model": True}
        self.assertFalse(
            pf.equipment_ready_for_protoflight(equipment, self.MATRIX, ["vibration", "thermal_vacuum"])
        )

    def test_not_ready_when_matrix_incomplete(self):
        equipment = {"id": "EQ-1", "dedicated_qualification_model": False}
        self.assertFalse(
            pf.equipment_ready_for_protoflight(
                equipment, self.MATRIX, ["vibration", "thermal_vacuum", "emc"]
            )
        )


if __name__ == "__main__":
    unittest.main(verbosity=2)
