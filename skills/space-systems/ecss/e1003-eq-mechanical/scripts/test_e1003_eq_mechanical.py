#!/usr/bin/env python3
"""Gate 3 contract test: ECSS-E-ST-10-03C clause 5.5.2 equipment
mechanical tests.

Exercises scripts/e1003_eq_mechanical_logic.py (stdlib unittest,
offline). Contract: docs/harness-contract.md gate 3 - acceleration
method derivation treats sine-burst and spin as mutually exclusive
alternatives and raises on an ambiguous request; test applicability
follows the item's characteristics (load significance, envelopment,
area-to-mass ratio, shock exposure, micro-vibration role) rather than
running the full set unconditionally; evidence requirements match each
applicable test/method; the mechanical test record covers every
equipment item with no duplicates; a dual-role micro-vibration item
with only one role closed is flagged; the campaign is only reported
complete when every equipment item has every applicable test closed.
"""

import os
import sys
import unittest

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import e1003_eq_mechanical_logic as ml  # noqa: E402


class AccelerationMethodTest(unittest.TestCase):
    def test_none_when_load_not_significant(self):
        self.assertIsNone(ml.acceleration_method({"static_load_significant": False}))

    def test_static_is_default_method(self):
        self.assertEqual(
            ml.acceleration_method({"static_load_significant": True}), "static"
        )

    def test_spin_when_spinning_mounted(self):
        self.assertEqual(
            ml.acceleration_method({
                "static_load_significant": True,
                "spinning_mounted": True,
            }),
            "spin",
        )

    def test_sine_burst_when_requested(self):
        self.assertEqual(
            ml.acceleration_method({
                "static_load_significant": True,
                "use_sine_burst": True,
            }),
            "sine_burst",
        )

    def test_both_sine_burst_and_spin_raises(self):
        with self.assertRaises(ValueError):
            ml.acceleration_method({
                "static_load_significant": True,
                "use_sine_burst": True,
                "spinning_mounted": True,
            })


class RequiredTestsTest(unittest.TestCase):
    def test_physical_properties_always_present(self):
        tests = dict(ml.required_tests({"id": "EQ-001"}))
        self.assertIn("physical_properties", tests)

    def test_minimal_equipment_gets_baseline_vibration(self):
        tests = dict(ml.required_tests({"id": "EQ-001"}))
        self.assertIn("sine_vibration", tests)
        self.assertIn("random_vibration", tests)
        self.assertNotIn("acceleration", tests)
        self.assertNotIn("acoustic", tests)
        self.assertNotIn("shock", tests)
        self.assertNotIn("microvibration_source", tests)
        self.assertNotIn("microvibration_sensitive", tests)

    def test_enveloped_item_skips_sine_and_random_vibration(self):
        tests = dict(ml.required_tests({
            "id": "EQ-001",
            "enveloped_by_higher_level_test": True,
        }))
        self.assertNotIn("sine_vibration", tests)
        self.assertNotIn("random_vibration", tests)
        self.assertIn("physical_properties", tests)

    def test_acceleration_evidence_is_method_specific(self):
        tests = dict(ml.required_tests({
            "id": "EQ-001",
            "static_load_significant": True,
            "spinning_mounted": True,
        }))
        self.assertEqual(tests["acceleration"], "acceleration_spin_result")

    def test_high_area_to_mass_adds_acoustic_not_instead_of_random(self):
        tests = dict(ml.required_tests({
            "id": "EQ-001",
            "area_to_mass_ratio_high": True,
        }))
        self.assertIn("acoustic", tests)
        self.assertIn("random_vibration", tests)

    def test_shock_exposed_adds_shock(self):
        tests = dict(ml.required_tests({"id": "EQ-001", "shock_exposed": True}))
        self.assertIn("shock", tests)

    def test_microvibration_roles_are_independent(self):
        source_only = dict(ml.required_tests({
            "id": "EQ-001",
            "microvibration_source": True,
        }))
        self.assertIn("microvibration_source", source_only)
        self.assertNotIn("microvibration_sensitive", source_only)

        both = dict(ml.required_tests({
            "id": "EQ-002",
            "microvibration_source": True,
            "microvibration_sensitive": True,
        }))
        self.assertIn("microvibration_source", both)
        self.assertIn("microvibration_sensitive", both)


class AssessEquipmentTest(unittest.TestCase):
    def test_closed_when_all_evidence_supplied(self):
        result = ml.assess_equipment({
            "id": "EQ-001",
            "evidence": ["physical_properties_result", "sine_vibration_result",
                         "random_vibration_result"],
        })
        self.assertEqual(result["status"], "closed")

    def test_open_when_evidence_missing(self):
        result = ml.assess_equipment({
            "id": "EQ-001",
            "evidence": ["physical_properties_result"],
        })
        self.assertEqual(result["status"], "open")
        self.assertIn("sine_vibration", ml.open_tests(result))

    def test_missing_id_raises(self):
        with self.assertRaises(ValueError):
            ml.assess_equipment({"evidence": []})

    def test_does_not_mutate_input(self):
        equipment = {"id": "EQ-001", "evidence": ["physical_properties_result"]}
        before = dict(equipment)
        ml.assess_equipment(equipment)
        self.assertEqual(equipment, before)


class BuildMechanicalTestRecordTest(unittest.TestCase):
    EQUIPMENT = [
        {
            "id": "EQ-001",
            "evidence": ["physical_properties_result", "sine_vibration_result",
                         "random_vibration_result"],
        },
        {
            "id": "EQ-002",
            "shock_exposed": True,
            "evidence": ["physical_properties_result", "sine_vibration_result",
                         "random_vibration_result"],
        },
    ]

    def test_record_order_and_status(self):
        record = ml.build_mechanical_test_record(self.EQUIPMENT)
        self.assertEqual(record[0]["id"], "EQ-001")
        self.assertEqual(record[0]["status"], "closed")
        self.assertEqual(record[1]["id"], "EQ-002")
        self.assertEqual(record[1]["status"], "open")  # shock_result missing

    def test_duplicate_id_raises(self):
        with self.assertRaises(ValueError):
            ml.build_mechanical_test_record(self.EQUIPMENT + [self.EQUIPMENT[0]])


class CampaignCompletionTest(unittest.TestCase):
    def test_open_equipment_lists_open_ids(self):
        record = [
            {"id": "EQ-001", "status": "closed"},
            {"id": "EQ-002", "status": "open"},
        ]
        self.assertEqual(ml.open_equipment(record), ["EQ-002"])

    def test_campaign_complete_true_when_all_closed(self):
        record = [{"id": "EQ-001", "status": "closed"}]
        self.assertTrue(ml.campaign_complete(record))

    def test_campaign_complete_false_when_any_open(self):
        record = [
            {"id": "EQ-001", "status": "closed"},
            {"id": "EQ-002", "status": "open"},
        ]
        self.assertFalse(ml.campaign_complete(record))


class FindIncompleteDualRoleMicrovibrationTest(unittest.TestCase):
    def test_flags_partially_closed_dual_role_item(self):
        record = ml.build_mechanical_test_record([{
            "id": "EQ-001",
            "microvibration_source": True,
            "microvibration_sensitive": True,
            "evidence": ["physical_properties_result", "sine_vibration_result",
                         "random_vibration_result", "microvibration_source_result"],
        }])
        self.assertEqual(
            ml.find_incomplete_dual_role_microvibration(record), ["EQ-001"]
        )

    def test_fully_closed_dual_role_item_not_flagged(self):
        record = ml.build_mechanical_test_record([{
            "id": "EQ-001",
            "microvibration_source": True,
            "microvibration_sensitive": True,
            "evidence": ["physical_properties_result", "sine_vibration_result",
                         "random_vibration_result", "microvibration_source_result",
                         "microvibration_sensitive_result"],
        }])
        self.assertEqual(ml.find_incomplete_dual_role_microvibration(record), [])

    def test_single_role_item_not_flagged(self):
        record = ml.build_mechanical_test_record([{
            "id": "EQ-001",
            "microvibration_source": True,
            "evidence": ["physical_properties_result", "sine_vibration_result",
                         "random_vibration_result", "microvibration_source_result"],
        }])
        self.assertEqual(ml.find_incomplete_dual_role_microvibration(record), [])


if __name__ == "__main__":
    unittest.main(verbosity=2)
