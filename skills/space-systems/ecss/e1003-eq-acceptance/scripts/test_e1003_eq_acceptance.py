#!/usr/bin/env python3
"""Gate 3 contract test: ECSS-E-ST-10-03C clause 5.3 equipment
acceptance test baseline (Tables 5-3/5-4).

Exercises scripts/e1003_eq_acceptance_logic.py (stdlib unittest,
offline). Contract: docs/harness-contract.md gate 3 - the acceptance
baseline only applies to equipment on the acceptance test path (not
protoflight); a derived acceptance level or duration that fails to
sit below its qualification counterpart is flagged rather than
silently accepted; and baseline release requires every required test
type to be present with a flag-free entry.
"""

import os
import sys
import unittest

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import e1003_eq_acceptance_logic as eqa  # noqa: E402


class CheckTestPathTest(unittest.TestCase):
    def test_acceptance_path_applies(self):
        self.assertTrue(eqa.check_test_path("acceptance"))

    def test_protoflight_path_does_not_apply(self):
        self.assertFalse(eqa.check_test_path("protoflight"))

    def test_unknown_path_raises(self):
        with self.assertRaises(ValueError):
            eqa.check_test_path("qualification_only")


class DeriveAcceptanceLevelTest(unittest.TestCase):
    def test_derives_reduced_level(self):
        self.assertAlmostEqual(eqa.derive_acceptance_level(14.0, 1.4), 10.0)

    def test_margin_factor_must_exceed_one(self):
        with self.assertRaises(ValueError):
            eqa.derive_acceptance_level(10.0, 1.0)

    def test_margin_factor_below_one_raises(self):
        with self.assertRaises(ValueError):
            eqa.derive_acceptance_level(10.0, 0.8)


class DeriveAcceptanceDurationTest(unittest.TestCase):
    def test_derives_reduced_duration(self):
        self.assertAlmostEqual(eqa.derive_acceptance_duration(8.0, 0.5), 4.0)

    def test_duration_factor_above_one_raises(self):
        with self.assertRaises(ValueError):
            eqa.derive_acceptance_duration(8.0, 1.5)

    def test_duration_factor_zero_raises(self):
        with self.assertRaises(ValueError):
            eqa.derive_acceptance_duration(8.0, 0.0)

    def test_duration_factor_of_one_is_allowed(self):
        self.assertAlmostEqual(eqa.derive_acceptance_duration(8.0, 1.0), 8.0)


class ConsistencyChecksTest(unittest.TestCase):
    def test_level_below_qualification_is_consistent(self):
        self.assertTrue(eqa.check_level_consistency(10.0, 14.0))

    def test_level_equal_to_qualification_is_inconsistent(self):
        self.assertFalse(eqa.check_level_consistency(14.0, 14.0))

    def test_duration_at_or_below_qualification_is_consistent(self):
        self.assertTrue(eqa.check_duration_consistency(4.0, 8.0))
        self.assertTrue(eqa.check_duration_consistency(8.0, 8.0))

    def test_duration_above_qualification_is_inconsistent(self):
        self.assertFalse(eqa.check_duration_consistency(9.0, 8.0))


class DefineTestBaselineTest(unittest.TestCase):
    BASE = {
        "test_type": "random_vibration",
        "qualification_level": 14.0,
        "qualification_duration": 8.0,
        "margin_factor": 1.4,
        "duration_factor": 0.5,
    }

    def test_clean_baseline_is_ok(self):
        self.assertEqual(
            eqa.define_test_baseline(self.BASE),
            {
                "test_type": "random_vibration",
                "acceptance_level": 10.0,
                "acceptance_duration": 4.0,
                "status": "ok",
            },
        )

    def test_missing_test_type_raises(self):
        test = dict(self.BASE)
        del test["test_type"]
        with self.assertRaises(ValueError):
            eqa.define_test_baseline(test)

    def test_does_not_mutate_input(self):
        before = dict(self.BASE)
        eqa.define_test_baseline(self.BASE)
        self.assertEqual(self.BASE, before)


class BuildEquipmentAcceptanceBaselineTest(unittest.TestCase):
    TESTS = [
        {
            "test_type": "random_vibration",
            "qualification_level": 14.0,
            "qualification_duration": 8.0,
            "margin_factor": 1.4,
            "duration_factor": 0.5,
        },
        {
            "test_type": "thermal_cycling",
            "qualification_level": 90.0,
            "qualification_duration": 16.0,
            "margin_factor": 1.2,
            "duration_factor": 0.5,
        },
    ]

    def test_builds_ordered_entries(self):
        result = eqa.build_equipment_acceptance_baseline("acceptance", self.TESTS)
        self.assertEqual([e["test_type"] for e in result], ["random_vibration", "thermal_cycling"])
        self.assertEqual(result[0]["status"], "ok")
        self.assertEqual(result[1]["status"], "ok")

    def test_protoflight_path_raises(self):
        with self.assertRaises(ValueError):
            eqa.build_equipment_acceptance_baseline("protoflight", self.TESTS)

    def test_duplicate_test_type_raises(self):
        with self.assertRaises(ValueError):
            eqa.build_equipment_acceptance_baseline("acceptance", self.TESTS + [self.TESTS[0]])


class MissingTestTypesTest(unittest.TestCase):
    def test_detects_gap(self):
        entries = [{"test_type": "random_vibration", "status": "ok"}]
        self.assertEqual(
            eqa.missing_test_types(
                ["random_vibration", "thermal_cycling", "shock"], entries
            ),
            ["thermal_cycling", "shock"],
        )

    def test_no_gap(self):
        entries = [{"test_type": "random_vibration", "status": "ok"}]
        self.assertEqual(eqa.missing_test_types(["random_vibration"], entries), [])


class CloseOutAcceptanceBaselineTest(unittest.TestCase):
    def test_complete_and_clean_baseline_is_ready(self):
        entries = [
            {"test_type": "random_vibration", "acceptance_level": 10.0, "acceptance_duration": 4.0, "status": "ok"},
            {"test_type": "thermal_cycling", "acceptance_level": 75.0, "acceptance_duration": 8.0, "status": "ok"},
        ]
        self.assertEqual(
            eqa.close_out_acceptance_baseline(
                ["random_vibration", "thermal_cycling"], entries
            ),
            (True, []),
        )

    def test_missing_type_blocks_release(self):
        entries = [
            {"test_type": "random_vibration", "acceptance_level": 10.0, "acceptance_duration": 4.0, "status": "ok"},
        ]
        ready, open_items = eqa.close_out_acceptance_baseline(
            ["random_vibration", "thermal_cycling"], entries
        )
        self.assertFalse(ready)
        self.assertEqual(open_items, [{"test_type": "thermal_cycling", "status": "missing"}])

    def test_flagged_entry_blocks_release(self):
        entries = [
            {"test_type": "random_vibration", "acceptance_level": 14.0, "acceptance_duration": 4.0, "status": "flagged_level_not_reduced"},
        ]
        ready, open_items = eqa.close_out_acceptance_baseline(["random_vibration"], entries)
        self.assertFalse(ready)
        self.assertEqual(
            open_items, [{"test_type": "random_vibration", "status": "flagged_level_not_reduced"}]
        )


if __name__ == "__main__":
    unittest.main(verbosity=2)
