#!/usr/bin/env python3
"""Gate 3 contract test: ECSS-E-ST-32C clause 4.6.2 COSPE metallic liner
structural and pressure integrity assessment.

Exercises scripts/cospe_metallic_liner_logic.py (stdlib unittest, offline).
Contract: all accepted metallic liner material types are recognized and an
unrecognized type raises; margin of safety is allowable/applied - 1.0 and
raises for non-positive applied; yield and ultimate margins are positive for
adequate strength and negative when stress exceeds the allowable; proof
pressure ratio at or above 1.1 passes and below 1.1 fails; burst pressure
ratio at or above 2.0 passes and below 2.0 fails; wall thickness at or above
minimum passes and below minimum fails; effective fatigue life (demonstrated
/ 4.0) at or above required passes and below fails; zero or negative MEOP
raises; the compliance review aggregates all checks and the vessel is
compliant only when violations is empty.
"""

import os
import sys
import unittest

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import cospe_metallic_liner_logic as lc  # noqa: E402


def _compliant_liner(liner_id="liner-1"):
    return {
        "liner_id": liner_id,
        "material_type": "aluminum_alloy",
        "hoop_stress_mpa": 200.0,
        "yield_strength_mpa": 270.0,
        "ultimate_strength_mpa": 310.0,
        "proof_pressure_mpa": 11.0,
        "burst_pressure_mpa": 22.0,
        "meop_mpa": 10.0,
        "actual_wall_thickness_mm": 3.0,
        "minimum_wall_thickness_mm": 2.5,
        "cycles_demonstrated": 2000,
        "cycles_required": 400,
    }


class CategorizeLinerMaterialTest(unittest.TestCase):
    def test_aluminum_alloy_accepted(self):
        self.assertEqual(lc.categorize_liner_material("aluminum_alloy"), "aluminum_alloy")

    def test_titanium_alloy_accepted(self):
        self.assertEqual(lc.categorize_liner_material("titanium_alloy"), "titanium_alloy")

    def test_stainless_steel_accepted(self):
        self.assertEqual(lc.categorize_liner_material("stainless_steel"), "stainless_steel")

    def test_nickel_alloy_accepted(self):
        self.assertEqual(lc.categorize_liner_material("nickel_alloy"), "nickel_alloy")

    def test_unknown_material_raises(self):
        with self.assertRaises(ValueError):
            lc.categorize_liner_material("carbon_steel")

    def test_empty_string_raises(self):
        with self.assertRaises(ValueError):
            lc.categorize_liner_material("")


class MarginOfSafetyTest(unittest.TestCase):
    def test_positive_margin(self):
        self.assertAlmostEqual(lc.margin_of_safety(300.0, 200.0), 0.5)

    def test_zero_margin_when_equal(self):
        self.assertAlmostEqual(lc.margin_of_safety(200.0, 200.0), 0.0)

    def test_negative_margin_when_allowable_less_than_applied(self):
        mos = lc.margin_of_safety(150.0, 200.0)
        self.assertLess(mos, 0.0)

    def test_zero_applied_raises(self):
        with self.assertRaises(ValueError):
            lc.margin_of_safety(300.0, 0.0)

    def test_negative_applied_raises(self):
        with self.assertRaises(ValueError):
            lc.margin_of_safety(300.0, -10.0)


class YieldAndUltimateMarginTest(unittest.TestCase):
    def test_yield_margin_positive_for_adequate_strength(self):
        mos = lc.liner_yield_margin(200.0, 270.0)
        self.assertGreater(mos, 0.0)

    def test_yield_margin_negative_when_stress_exceeds_yield(self):
        mos = lc.liner_yield_margin(300.0, 270.0)
        self.assertLess(mos, 0.0)

    def test_ultimate_margin_positive_for_adequate_strength(self):
        mos = lc.liner_ultimate_margin(200.0, 310.0)
        self.assertGreater(mos, 0.0)

    def test_ultimate_margin_zero_at_exact_allowable(self):
        self.assertAlmostEqual(lc.liner_ultimate_margin(310.0, 310.0), 0.0)


class ProofPressureRatioTest(unittest.TestCase):
    def test_ratio_above_minimum_passes(self):
        self.assertTrue(lc.proof_pressure_ratio_adequate(12.0, 10.0))

    def test_ratio_exactly_minimum_passes(self):
        self.assertTrue(lc.proof_pressure_ratio_adequate(11.0, 10.0))

    def test_ratio_below_minimum_fails(self):
        self.assertFalse(lc.proof_pressure_ratio_adequate(10.5, 10.0))

    def test_zero_meop_raises(self):
        with self.assertRaises(ValueError):
            lc.proof_pressure_ratio_adequate(11.0, 0.0)

    def test_negative_proof_pressure_raises(self):
        with self.assertRaises(ValueError):
            lc.proof_pressure_ratio_adequate(-1.0, 10.0)


class BurstPressureRatioTest(unittest.TestCase):
    def test_ratio_above_minimum_passes(self):
        self.assertTrue(lc.burst_pressure_ratio_adequate(25.0, 10.0))

    def test_ratio_exactly_minimum_passes(self):
        self.assertTrue(lc.burst_pressure_ratio_adequate(20.0, 10.0))

    def test_ratio_below_minimum_fails(self):
        self.assertFalse(lc.burst_pressure_ratio_adequate(18.0, 10.0))

    def test_zero_meop_raises(self):
        with self.assertRaises(ValueError):
            lc.burst_pressure_ratio_adequate(20.0, 0.0)


class WallThicknessTest(unittest.TestCase):
    def test_thickness_above_minimum_passes(self):
        self.assertTrue(lc.wall_thickness_adequate(3.0, 2.5))

    def test_thickness_exactly_minimum_passes(self):
        self.assertTrue(lc.wall_thickness_adequate(2.5, 2.5))

    def test_thickness_below_minimum_fails(self):
        self.assertFalse(lc.wall_thickness_adequate(2.0, 2.5))

    def test_negative_actual_raises(self):
        with self.assertRaises(ValueError):
            lc.wall_thickness_adequate(-1.0, 2.5)

    def test_negative_minimum_raises(self):
        with self.assertRaises(ValueError):
            lc.wall_thickness_adequate(2.5, -1.0)


class FatigueLifeTest(unittest.TestCase):
    def test_demonstrated_over_factor_covers_required(self):
        # 2000 / 4.0 = 500 >= 400 required
        self.assertTrue(lc.fatigue_life_adequate(2000, 400))

    def test_demonstrated_exactly_at_threshold_passes(self):
        # 1600 / 4.0 = 400 >= 400 required
        self.assertTrue(lc.fatigue_life_adequate(1600, 400))

    def test_demonstrated_below_threshold_fails(self):
        # 1000 / 4.0 = 250 < 400 required
        self.assertFalse(lc.fatigue_life_adequate(1000, 400))

    def test_negative_demonstrated_raises(self):
        with self.assertRaises(ValueError):
            lc.fatigue_life_adequate(-100, 400)

    def test_negative_required_raises(self):
        with self.assertRaises(ValueError):
            lc.fatigue_life_adequate(2000, -1)


class LinerComplianceReviewTest(unittest.TestCase):
    def test_fully_compliant_liner_has_no_violations(self):
        review = lc.liner_compliance_review(_compliant_liner())
        self.assertEqual(review["violations"], [])
        self.assertTrue(lc.is_liner_compliant(review))

    def test_unknown_material_raises_in_review(self):
        liner = _compliant_liner()
        liner["material_type"] = "unobtainium"
        with self.assertRaises(ValueError):
            lc.liner_compliance_review(liner)

    def test_yield_violation_detected(self):
        liner = _compliant_liner()
        liner["hoop_stress_mpa"] = 280.0
        liner["yield_strength_mpa"] = 270.0
        review = lc.liner_compliance_review(liner)
        issues = [v["issue"] for v in review["violations"]]
        self.assertIn("liner_yield_margin_negative", issues)

    def test_burst_ratio_violation_detected(self):
        liner = _compliant_liner()
        liner["burst_pressure_mpa"] = 18.0
        review = lc.liner_compliance_review(liner)
        issues = [v["issue"] for v in review["violations"]]
        self.assertIn("burst_pressure_ratio_below_minimum", issues)

    def test_proof_ratio_violation_detected(self):
        liner = _compliant_liner()
        liner["proof_pressure_mpa"] = 10.5
        review = lc.liner_compliance_review(liner)
        issues = [v["issue"] for v in review["violations"]]
        self.assertIn("proof_pressure_ratio_below_minimum", issues)

    def test_wall_thickness_violation_detected(self):
        liner = _compliant_liner()
        liner["actual_wall_thickness_mm"] = 2.0
        review = lc.liner_compliance_review(liner)
        issues = [v["issue"] for v in review["violations"]]
        self.assertIn("liner_wall_thickness_below_minimum", issues)

    def test_fatigue_life_violation_detected(self):
        liner = _compliant_liner()
        liner["cycles_demonstrated"] = 1000
        liner["cycles_required"] = 400
        review = lc.liner_compliance_review(liner)
        issues = [v["issue"] for v in review["violations"]]
        self.assertIn("liner_fatigue_life_insufficient", issues)

    def test_multiple_violations_all_collected(self):
        liner = _compliant_liner()
        liner["hoop_stress_mpa"] = 350.0
        liner["burst_pressure_mpa"] = 15.0
        liner["cycles_demonstrated"] = 500
        review = lc.liner_compliance_review(liner)
        self.assertGreaterEqual(len(review["violations"]), 3)
        self.assertFalse(lc.is_liner_compliant(review))

    def test_review_does_not_mutate_input(self):
        liner = _compliant_liner()
        original_stress = liner["hoop_stress_mpa"]
        lc.liner_compliance_review(liner)
        self.assertEqual(liner["hoop_stress_mpa"], original_stress)

    def test_is_liner_compliant_false_when_violations_present(self):
        liner = _compliant_liner()
        liner["burst_pressure_mpa"] = 10.0
        review = lc.liner_compliance_review(liner)
        self.assertFalse(lc.is_liner_compliant(review))


if __name__ == "__main__":
    unittest.main(verbosity=2)
