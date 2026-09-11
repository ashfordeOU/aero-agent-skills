#!/usr/bin/env python3
"""Gate 3 contract test: ECSS-E-ST-10-11C §4.7.9 medical facilities and
provisions assessment.

Exercises scripts/e1011_medical_logic.py (stdlib unittest, offline).
Contract: provision items are categorized into exactly one of emergency,
diagnostic, routine, or preventive; an unrecognized type raises; mission
duration maps deterministically to short/medium/long tier; required
provision set grows monotonically with tier; missing provisions are
detected and reported; consumable requirement equals daily rate × crew ×
days × 1.10; a shortfall is flagged when available quantity is below
the requirement; the aggregated medical HFE review is compliant only
when both missing-provision and consumable-shortfall lists are empty.
"""

import os
import sys
import unittest

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import e1011_medical_logic as med  # noqa: E402


class CategorizationTest(unittest.TestCase):
    def test_trauma_kit_is_emergency(self):
        self.assertEqual(med.categorize_provision("trauma_kit"), "emergency")

    def test_defibrillator_is_emergency(self):
        self.assertEqual(med.categorize_provision("defibrillator"), "emergency")

    def test_pulse_oximeter_is_diagnostic(self):
        self.assertEqual(med.categorize_provision("pulse_oximeter"), "diagnostic")

    def test_ultrasound_is_diagnostic(self):
        self.assertEqual(med.categorize_provision("ultrasound"), "diagnostic")

    def test_first_aid_kit_is_routine(self):
        self.assertEqual(med.categorize_provision("first_aid_kit"), "routine")

    def test_wound_care_is_routine(self):
        self.assertEqual(med.categorize_provision("wound_care"), "routine")

    def test_vitamins_is_preventive(self):
        self.assertEqual(med.categorize_provision("vitamins"), "preventive")

    def test_exercise_equipment_is_preventive(self):
        self.assertEqual(med.categorize_provision("exercise_equipment"), "preventive")

    def test_unknown_provision_raises(self):
        with self.assertRaises(ValueError):
            med.categorize_provision("magic_pill")

    def test_empty_string_provision_raises(self):
        with self.assertRaises(ValueError):
            med.categorize_provision("")


class MissionDurationCategoryTest(unittest.TestCase):
    def test_30_days_is_short(self):
        self.assertEqual(med.mission_duration_category(30), "short")

    def test_1_day_is_short(self):
        self.assertEqual(med.mission_duration_category(1), "short")

    def test_31_days_is_medium(self):
        self.assertEqual(med.mission_duration_category(31), "medium")

    def test_180_days_is_medium(self):
        self.assertEqual(med.mission_duration_category(180), "medium")

    def test_181_days_is_long(self):
        self.assertEqual(med.mission_duration_category(181), "long")

    def test_zero_days_raises(self):
        with self.assertRaises(ValueError):
            med.mission_duration_category(0)

    def test_negative_days_raises(self):
        with self.assertRaises(ValueError):
            med.mission_duration_category(-10)


class RequiredProvisionsTest(unittest.TestCase):
    def test_short_mission_requires_core_emergency_items(self):
        req = med.required_provisions(14)
        self.assertIn("trauma_kit", req)
        self.assertIn("emergency_medications", req)
        self.assertIn("oxygen_supply", req)

    def test_short_mission_does_not_require_long_duration_items(self):
        req = med.required_provisions(14)
        self.assertNotIn("vitamins", req)
        self.assertNotIn("exercise_equipment", req)

    def test_medium_mission_requires_full_diagnostic_suite(self):
        req = med.required_provisions(90)
        self.assertIn("ultrasound", req)
        self.assertIn("blood_pressure_monitor", req)
        self.assertIn("radiation_dosimeter", req)

    def test_long_mission_requires_preventive_items(self):
        req = med.required_provisions(365)
        self.assertIn("vitamins", req)
        self.assertIn("exercise_equipment", req)

    def test_long_mission_includes_all_medium_requirements(self):
        req_medium = med.required_provisions(90)
        req_long = med.required_provisions(365)
        self.assertTrue(req_medium.issubset(req_long))


class MissingProvisionsTest(unittest.TestCase):
    def test_no_missing_when_all_short_items_present(self):
        available = list(med.REQUIRED_SHORT)
        self.assertEqual(med.missing_provisions(available, 14), [])

    def test_detects_single_missing_item(self):
        available = [t for t in med.REQUIRED_SHORT if t != "trauma_kit"]
        result = med.missing_provisions(available, 14)
        self.assertIn("trauma_kit", result)

    def test_result_is_sorted(self):
        result = med.missing_provisions([], 14)
        self.assertEqual(result, sorted(result))

    def test_medium_mission_detects_missing_from_extended_set(self):
        available = list(med.REQUIRED_SHORT)  # only short items, medium mission
        missing = med.missing_provisions(available, 90)
        self.assertIn("ultrasound", missing)
        self.assertIn("defibrillator", missing)

    def test_empty_inventory_for_long_mission_flags_all_required(self):
        missing = med.missing_provisions([], 365)
        self.assertEqual(sorted(missing), missing)
        self.assertTrue(len(missing) >= len(med.REQUIRED_LONG))


class ConsumableRequirementTest(unittest.TestCase):
    def test_basic_computation_with_margin(self):
        # 2 crew, 10 days, 1.0 unit/person/day → 2 × 10 × 1.1 = 22.0
        self.assertAlmostEqual(med.consumable_requirement(2, 10, 1.0), 22.0)

    def test_zero_rate_requires_zero(self):
        self.assertAlmostEqual(med.consumable_requirement(4, 30, 0.0), 0.0)

    def test_margin_is_ten_percent(self):
        baseline = 3 * 7 * 2.0
        req = med.consumable_requirement(3, 7, 2.0)
        self.assertAlmostEqual(req, baseline * med.CONSUMABLE_MARGIN)

    def test_zero_crew_raises(self):
        with self.assertRaises(ValueError):
            med.consumable_requirement(0, 10, 1.0)

    def test_negative_crew_raises(self):
        with self.assertRaises(ValueError):
            med.consumable_requirement(-1, 10, 1.0)

    def test_zero_duration_raises(self):
        with self.assertRaises(ValueError):
            med.consumable_requirement(2, 0, 1.0)

    def test_negative_rate_raises(self):
        with self.assertRaises(ValueError):
            med.consumable_requirement(2, 10, -0.5)


class ConsumableShortfallTest(unittest.TestCase):
    def test_adequate_quantity_returns_empty(self):
        # Need 2 × 10 × 1.0 × 1.1 = 22; providing 25 is adequate.
        result = med.consumable_shortfall("emergency_medications", 25.0, 2, 10, 1.0)
        self.assertEqual(result, [])

    def test_shortfall_is_flagged(self):
        # Need 22; providing 10 is a shortfall.
        result = med.consumable_shortfall("emergency_medications", 10.0, 2, 10, 1.0)
        self.assertEqual(len(result), 1)
        self.assertEqual(result[0]["issue"], "consumable_quantity_shortfall")
        self.assertEqual(result[0]["provision_id"], "emergency_medications")
        self.assertAlmostEqual(result[0]["required"], 22.0)
        self.assertAlmostEqual(result[0]["available"], 10.0)

    def test_exact_required_quantity_is_adequate(self):
        req = med.consumable_requirement(2, 10, 1.0)
        result = med.consumable_shortfall("oxygen_supply", req, 2, 10, 1.0)
        self.assertEqual(result, [])


class MedicalHfeReviewTest(unittest.TestCase):
    def _short_mission_config(self, extra_provisions=None, overrides=None):
        provisions = [{"provision_type": t} for t in med.REQUIRED_SHORT]
        if extra_provisions:
            provisions.extend(extra_provisions)
        config = {
            "crew_size": 2,
            "duration_days": 14,
            "provisions": provisions,
        }
        if overrides:
            config.update(overrides)
        return config

    def test_compliant_short_mission(self):
        review = med.medical_hfe_review(self._short_mission_config())
        self.assertTrue(med.is_medical_hfe_compliant(review))

    def test_missing_provision_flagged(self):
        config = self._short_mission_config()
        config["provisions"] = [
            {"provision_type": t}
            for t in med.REQUIRED_SHORT
            if t != "trauma_kit"
        ]
        review = med.medical_hfe_review(config)
        self.assertIn("trauma_kit", review["missing_provisions"])
        self.assertFalse(med.is_medical_hfe_compliant(review))

    def test_consumable_shortfall_flagged(self):
        provisions = [{"provision_type": t} for t in med.REQUIRED_SHORT]
        provisions.append({
            "provision_type": "oxygen_supply",
            "available_qty": 0.1,
            "daily_rate_per_person": 5.0,
        })
        config = {
            "crew_size": 2,
            "duration_days": 14,
            "provisions": provisions,
        }
        review = med.medical_hfe_review(config)
        issues = [f["issue"] for f in review["consumable_shortfalls"]]
        self.assertIn("consumable_quantity_shortfall", issues)

    def test_unknown_provision_type_raises(self):
        config = {
            "crew_size": 2,
            "duration_days": 14,
            "provisions": [{"provision_type": "mystery_spray"}],
        }
        with self.assertRaises(ValueError):
            med.medical_hfe_review(config)

    def test_long_mission_requires_preventive_items(self):
        provisions = [{"provision_type": t} for t in med.REQUIRED_SHORT]
        config = {
            "crew_size": 3,
            "duration_days": 365,
            "provisions": provisions,
        }
        review = med.medical_hfe_review(config)
        self.assertIn("vitamins", review["missing_provisions"])
        self.assertIn("exercise_equipment", review["missing_provisions"])

    def test_compliant_long_mission_with_full_inventory(self):
        provisions = [{"provision_type": t} for t in med.REQUIRED_LONG]
        config = {
            "crew_size": 3,
            "duration_days": 365,
            "provisions": provisions,
        }
        review = med.medical_hfe_review(config)
        self.assertEqual(review["missing_provisions"], [])
        self.assertTrue(med.is_medical_hfe_compliant(review))

    def test_empty_inventory_on_medium_mission_flags_many(self):
        config = {
            "crew_size": 2,
            "duration_days": 90,
            "provisions": [],
        }
        review = med.medical_hfe_review(config)
        self.assertTrue(len(review["missing_provisions"]) >= len(med.REQUIRED_MEDIUM))

    def test_is_compliant_false_when_only_shortfalls(self):
        provisions = list(med.REQUIRED_SHORT)
        provision_entries = []
        for t in provisions:
            provision_entries.append({
                "provision_type": t,
                "available_qty": 0.0,
                "daily_rate_per_person": 1.0,
            })
        config = {
            "crew_size": 2,
            "duration_days": 14,
            "provisions": provision_entries,
        }
        review = med.medical_hfe_review(config)
        self.assertFalse(med.is_medical_hfe_compliant(review))


if __name__ == "__main__":
    unittest.main(verbosity=2)
