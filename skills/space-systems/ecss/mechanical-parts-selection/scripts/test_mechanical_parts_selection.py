#!/usr/bin/env python3
"""Gate 3 contract test: ECSS-E-ST-32C clause 4.5.7 mechanical parts
selection.

Exercises scripts/mechanical_parts_selection_logic.py (stdlib unittest,
offline). Contract: a part type maps to exactly fastener, insert, or
bearing, and an unrecognized type raises; a part absent from the
qualified-parts set is flagged; margin of safety equals rated/applied - 1
and a negative MS is flagged while a non-positive load raises; a part's
rated temperature range must encompass the full mission thermal envelope and
a violation is raised for each bound that fails; a material pair in the
high-galvanic-risk set is flagged; the aggregated review is compliant only
when all violation lists are empty.
"""

import os
import sys
import unittest

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import mechanical_parts_selection_logic as mp  # noqa: E402


class CategorizationTest(unittest.TestCase):
    def test_bolt_is_fastener(self):
        self.assertEqual(mp.categorize_part("bolt"), "fastener")

    def test_screw_is_fastener(self):
        self.assertEqual(mp.categorize_part("screw"), "fastener")

    def test_rivet_is_fastener(self):
        self.assertEqual(mp.categorize_part("rivet"), "fastener")

    def test_helicoil_insert_is_insert(self):
        self.assertEqual(mp.categorize_part("helicoil_insert"), "insert")

    def test_key_locking_insert_is_insert(self):
        self.assertEqual(mp.categorize_part("key_locking_insert"), "insert")

    def test_ball_bearing_is_bearing(self):
        self.assertEqual(mp.categorize_part("ball_bearing"), "bearing")

    def test_roller_bearing_is_bearing(self):
        self.assertEqual(mp.categorize_part("roller_bearing"), "bearing")

    def test_bush_bearing_is_bearing(self):
        self.assertEqual(mp.categorize_part("bush_bearing"), "bearing")

    def test_unknown_part_type_raises(self):
        with self.assertRaises(ValueError):
            mp.categorize_part("spring_clip")


class QualificationStatusTest(unittest.TestCase):
    def test_part_on_qpl_no_violation(self):
        self.assertEqual(
            mp.check_qualification_status("P1001", {"P1001", "P1002"}), []
        )

    def test_part_absent_from_qpl_flagged(self):
        violations = mp.check_qualification_status("P9999", {"P1001", "P1002"})
        self.assertEqual(len(violations), 1)
        self.assertEqual(violations[0]["issue"], "part_not_on_qualified_parts_list")
        self.assertEqual(violations[0]["part"], "P9999")

    def test_empty_qpl_flags_any_part(self):
        violations = mp.check_qualification_status("P1001", set())
        self.assertEqual(len(violations), 1)


class MarginOfSafetyTest(unittest.TestCase):
    def test_rated_exceeds_applied_positive_ms(self):
        self.assertAlmostEqual(mp.compute_margin_of_safety(100.0, 150.0), 0.5)

    def test_rated_equals_applied_zero_ms(self):
        self.assertAlmostEqual(mp.compute_margin_of_safety(100.0, 100.0), 0.0)

    def test_rated_less_than_applied_negative_ms(self):
        self.assertAlmostEqual(mp.compute_margin_of_safety(100.0, 80.0), -0.2)

    def test_zero_applied_load_raises(self):
        with self.assertRaises(ValueError):
            mp.compute_margin_of_safety(0.0, 100.0)

    def test_negative_applied_load_raises(self):
        with self.assertRaises(ValueError):
            mp.compute_margin_of_safety(-10.0, 100.0)

    def test_zero_rated_load_raises(self):
        with self.assertRaises(ValueError):
            mp.compute_margin_of_safety(100.0, 0.0)


class LoadComplianceTest(unittest.TestCase):
    def test_positive_ms_compliant(self):
        self.assertEqual(
            mp.check_load_compliance("P1001", 100.0, 120.0), []
        )

    def test_zero_ms_compliant(self):
        self.assertEqual(
            mp.check_load_compliance("P1001", 100.0, 100.0), []
        )

    def test_negative_ms_flagged(self):
        violations = mp.check_load_compliance("P1001", 100.0, 80.0)
        self.assertEqual(len(violations), 1)
        self.assertEqual(violations[0]["issue"], "negative_load_margin_of_safety")
        self.assertLess(violations[0]["margin_of_safety"], 0.0)


class TemperatureRangeTest(unittest.TestCase):
    def test_part_range_encompasses_mission_compliant(self):
        self.assertEqual(
            mp.check_temperature_range("P1001", -60.0, 80.0, -70.0, 100.0), []
        )

    def test_part_rated_min_too_high_flagged(self):
        violations = mp.check_temperature_range("P1001", -60.0, 80.0, -50.0, 100.0)
        self.assertEqual(len(violations), 1)
        self.assertEqual(violations[0]["issue"], "part_rated_min_exceeds_mission_min")

    def test_part_rated_max_too_low_flagged(self):
        violations = mp.check_temperature_range("P1001", -60.0, 80.0, -70.0, 70.0)
        self.assertEqual(len(violations), 1)
        self.assertEqual(violations[0]["issue"], "part_rated_max_below_mission_max")

    def test_both_bounds_violated_two_findings(self):
        violations = mp.check_temperature_range("P1001", -60.0, 80.0, -40.0, 70.0)
        self.assertEqual(len(violations), 2)

    def test_part_range_exactly_matches_mission_compliant(self):
        self.assertEqual(
            mp.check_temperature_range("P1001", -60.0, 80.0, -60.0, 80.0), []
        )


class GalvanicCompatibilityTest(unittest.TestCase):
    def test_same_material_no_violation(self):
        self.assertEqual(
            mp.check_galvanic_compatibility("P1001", "steel", "steel"), []
        )

    def test_titanium_with_steel_no_violation(self):
        self.assertEqual(
            mp.check_galvanic_compatibility("P1001", "titanium", "steel"), []
        )

    def test_aluminum_steel_pair_flagged(self):
        violations = mp.check_galvanic_compatibility("P1001", "aluminum", "steel")
        self.assertEqual(len(violations), 1)
        self.assertEqual(violations[0]["issue"], "high_galvanic_risk_material_pair")

    def test_cfrp_aluminum_pair_flagged(self):
        violations = mp.check_galvanic_compatibility("P1001", "cfrp", "aluminum")
        self.assertEqual(len(violations), 1)

    def test_pair_order_does_not_matter(self):
        v1 = mp.check_galvanic_compatibility("P1001", "aluminum", "steel")
        v2 = mp.check_galvanic_compatibility("P1001", "steel", "aluminum")
        self.assertEqual(len(v1), len(v2))
        self.assertEqual(len(v1), 1)


class MechanicalPartReviewTest(unittest.TestCase):
    def _compliant_part(self):
        return {
            "part_id": "BOLT-A1",
            "part_type": "bolt",
            "qualified_parts_set": {"BOLT-A1", "BOLT-A2"},
            "applied_load_n": 500.0,
            "rated_load_n": 1000.0,
            "mission_min_c": -60.0,
            "mission_max_c": 80.0,
            "part_rated_min_c": -80.0,
            "part_rated_max_c": 120.0,
            "part_material": "steel",
            "mating_material": "steel",
        }

    def test_fully_compliant_review(self):
        review = mp.mechanical_part_review(self._compliant_part())
        self.assertEqual(review["category"], "fastener")
        self.assertEqual(review["qualification"], [])
        self.assertEqual(review["load"], [])
        self.assertEqual(review["temperature"], [])
        self.assertEqual(review["galvanic"], [])
        self.assertTrue(mp.is_part_compliant(review))

    def test_unqualified_part_review_non_compliant(self):
        part = self._compliant_part()
        part["qualified_parts_set"] = {"BOLT-A2"}  # BOLT-A1 absent
        review = mp.mechanical_part_review(part)
        self.assertTrue(len(review["qualification"]) > 0)
        self.assertFalse(mp.is_part_compliant(review))

    def test_overloaded_part_review_non_compliant(self):
        part = self._compliant_part()
        part["applied_load_n"] = 1500.0  # exceeds rated 1000 N
        review = mp.mechanical_part_review(part)
        self.assertTrue(len(review["load"]) > 0)
        self.assertFalse(mp.is_part_compliant(review))

    def test_galvanic_risk_review_non_compliant(self):
        part = self._compliant_part()
        part["part_material"] = "aluminum"
        part["mating_material"] = "steel"
        review = mp.mechanical_part_review(part)
        self.assertTrue(len(review["galvanic"]) > 0)
        self.assertFalse(mp.is_part_compliant(review))

    def test_unknown_part_type_raises_in_review(self):
        part = self._compliant_part()
        part["part_type"] = "mystery_clip"
        with self.assertRaises(ValueError):
            mp.mechanical_part_review(part)

    def test_review_skips_load_check_when_loads_absent(self):
        part = self._compliant_part()
        del part["applied_load_n"]
        del part["rated_load_n"]
        review = mp.mechanical_part_review(part)
        self.assertEqual(review["load"], [])

    def test_review_skips_temp_check_when_temps_absent(self):
        part = self._compliant_part()
        del part["mission_min_c"]
        review = mp.mechanical_part_review(part)
        self.assertEqual(review["temperature"], [])

    def test_review_skips_galvanic_check_when_materials_absent(self):
        part = self._compliant_part()
        del part["part_material"]
        review = mp.mechanical_part_review(part)
        self.assertEqual(review["galvanic"], [])

    def test_bearing_part_type_resolves_correctly(self):
        part = self._compliant_part()
        part["part_id"] = "BEARING-B1"
        part["part_type"] = "ball_bearing"
        part["qualified_parts_set"] = {"BEARING-B1"}
        review = mp.mechanical_part_review(part)
        self.assertEqual(review["category"], "bearing")

    def test_insert_part_type_resolves_correctly(self):
        part = self._compliant_part()
        part["part_id"] = "INS-C1"
        part["part_type"] = "helicoil_insert"
        part["qualified_parts_set"] = {"INS-C1"}
        review = mp.mechanical_part_review(part)
        self.assertEqual(review["category"], "insert")


if __name__ == "__main__":
    unittest.main(verbosity=2)
