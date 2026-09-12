"""
Gate 3 contract tests for welded_joint_analysis_logic.py.

stdlib unittest only; offline; deterministic. Run:
    python3 test_welded_joint_analysis.py
"""

import math
import sys
import os
import unittest

# Allow running from the scripts/ directory directly.
sys.path.insert(0, os.path.dirname(__file__))

from welded_joint_analysis_logic import (
    WELD_QUALITY_CLASSES,
    VON_MISES_SHEAR,
    assess_welded_joint,
    categorize_weld_quality,
    check_combined_criterion,
    compute_allowable_stresses,
    compute_applied_stresses,
    compute_margin_of_safety,
    compute_weld_throat_area,
)


class TestCategorizeWeldQuality(unittest.TestCase):

    def test_wq1_efficiency(self):
        rec = categorize_weld_quality("WQ1")
        self.assertAlmostEqual(rec["efficiency"], 1.00)

    def test_wq2_efficiency(self):
        rec = categorize_weld_quality("WQ2")
        self.assertAlmostEqual(rec["efficiency"], 0.85)

    def test_wq3_efficiency(self):
        rec = categorize_weld_quality("WQ3")
        self.assertAlmostEqual(rec["efficiency"], 0.70)

    def test_case_insensitive(self):
        rec = categorize_weld_quality("wq2")
        self.assertAlmostEqual(rec["efficiency"], 0.85)

    def test_unknown_quality_class_raises(self):
        with self.assertRaises(ValueError):
            categorize_weld_quality("WQ9")

    def test_empty_string_raises(self):
        with self.assertRaises(ValueError):
            categorize_weld_quality("")

    def test_returns_quality_class_key(self):
        rec = categorize_weld_quality("WQ1")
        self.assertEqual(rec["quality_class"], "WQ1")


class TestComputeWeldThroatArea(unittest.TestCase):

    def test_butt_weld_area(self):
        # length=100, throat=10 → area=1000
        area = compute_weld_throat_area("butt", 100.0, 10.0)
        self.assertAlmostEqual(area, 1000.0)

    def test_fillet_weld_area(self):
        # length=100, leg=10 → area = 100 * 0.70711 * 10 ≈ 707.11
        area = compute_weld_throat_area("fillet", 100.0, 10.0)
        self.assertAlmostEqual(area, 100.0 * (math.sqrt(2) / 2.0) * 10.0, places=6)

    def test_fillet_smaller_than_butt_same_dimension(self):
        butt = compute_weld_throat_area("butt", 50.0, 8.0)
        fillet = compute_weld_throat_area("fillet", 50.0, 8.0)
        self.assertLess(fillet, butt)

    def test_invalid_weld_type_raises(self):
        with self.assertRaises(ValueError):
            compute_weld_throat_area("groove", 100.0, 10.0)

    def test_zero_length_raises(self):
        with self.assertRaises(ValueError):
            compute_weld_throat_area("butt", 0.0, 10.0)

    def test_negative_leg_raises(self):
        with self.assertRaises(ValueError):
            compute_weld_throat_area("fillet", 50.0, -5.0)

    def test_case_insensitive_weld_type(self):
        area = compute_weld_throat_area("BUTT", 100.0, 5.0)
        self.assertAlmostEqual(area, 500.0)


class TestComputeAllowableStresses(unittest.TestCase):

    def test_wq1_full_efficiency(self):
        # WQ1 η=1.0: σ_allow = 400 * 1.0 / 2.0 = 200 MPa
        res = compute_allowable_stresses(400.0, "WQ1", 2.0)
        self.assertAlmostEqual(res["sigma_allow"], 200.0)

    def test_wq2_reduced_allowable(self):
        # WQ2 η=0.85: σ_allow = 400 * 0.85 / 2.0 = 170 MPa
        res = compute_allowable_stresses(400.0, "WQ2", 2.0)
        self.assertAlmostEqual(res["sigma_allow"], 170.0)

    def test_wq3_further_reduced(self):
        # WQ3 η=0.70: σ_allow = 400 * 0.70 / 2.0 = 140 MPa
        res = compute_allowable_stresses(400.0, "WQ3", 2.0)
        self.assertAlmostEqual(res["sigma_allow"], 140.0)

    def test_tau_allow_is_von_mises_fraction(self):
        res = compute_allowable_stresses(400.0, "WQ1", 2.0)
        expected_tau = VON_MISES_SHEAR * res["sigma_allow"]
        self.assertAlmostEqual(res["tau_allow"], expected_tau)

    def test_zero_ftu_raises(self):
        with self.assertRaises(ValueError):
            compute_allowable_stresses(0.0, "WQ1", 2.0)

    def test_zero_safety_factor_raises(self):
        with self.assertRaises(ValueError):
            compute_allowable_stresses(400.0, "WQ1", 0.0)


class TestComputeAppliedStresses(unittest.TestCase):

    def test_normal_stress(self):
        # N=10000 N, A=100 mm² → σ=100 MPa
        res = compute_applied_stresses(10000.0, 0.0, 100.0)
        self.assertAlmostEqual(res["sigma_applied"], 100.0)

    def test_shear_stress(self):
        # V=5000 N, A=100 mm² → τ=50 MPa
        res = compute_applied_stresses(0.0, 5000.0, 100.0)
        self.assertAlmostEqual(res["tau_applied"], 50.0)

    def test_zero_area_raises(self):
        with self.assertRaises(ValueError):
            compute_applied_stresses(1000.0, 500.0, 0.0)


class TestComputeMarginOfSafety(unittest.TestCase):

    def test_positive_margin(self):
        # allow=200, applied=100 → MoS=1.0
        mos = compute_margin_of_safety(100.0, 200.0)
        self.assertAlmostEqual(mos, 1.0)

    def test_zero_margin(self):
        # allow=applied → MoS=0.0
        mos = compute_margin_of_safety(150.0, 150.0)
        self.assertAlmostEqual(mos, 0.0)

    def test_negative_margin(self):
        # allow=100, applied=200 → MoS=-0.5
        mos = compute_margin_of_safety(200.0, 100.0)
        self.assertAlmostEqual(mos, -0.5)

    def test_zero_applied_gives_inf(self):
        mos = compute_margin_of_safety(0.0, 200.0)
        self.assertEqual(mos, math.inf)

    def test_zero_allowable_raises(self):
        with self.assertRaises(ValueError):
            compute_margin_of_safety(100.0, 0.0)


class TestCheckCombinedCriterion(unittest.TestCase):

    def test_pure_normal_at_limit(self):
        # σ = σ_allow, τ = 0 → R=1.0, MoS=0.0
        res = check_combined_criterion(100.0, 0.0, 100.0, 57.74)
        self.assertAlmostEqual(res["interaction_ratio"], 1.0)
        self.assertAlmostEqual(res["mos_combined"], 0.0)

    def test_well_within_limit(self):
        # σ/σ_allow = 0.5, τ/τ_allow = 0.5 → R = sqrt(0.5) ≈ 0.707
        res = check_combined_criterion(50.0, 28.87, 100.0, 57.74)
        self.assertLess(res["interaction_ratio"], 1.0)
        self.assertTrue(res["compliant"])

    def test_exceeds_limit(self):
        # Both components at allowable → R = sqrt(2) > 1.0
        res = check_combined_criterion(100.0, 57.74, 100.0, 57.74)
        self.assertGreater(res["interaction_ratio"], 1.0)
        self.assertFalse(res["compliant"])
        self.assertLess(res["mos_combined"], 0.0)

    def test_zero_stresses_gives_inf(self):
        res = check_combined_criterion(0.0, 0.0, 100.0, 57.74)
        self.assertEqual(res["mos_combined"], math.inf)
        self.assertTrue(res["compliant"])

    def test_negative_sigma_allow_raises(self):
        with self.assertRaises(ValueError):
            check_combined_criterion(50.0, 20.0, -100.0, 57.74)


class TestAssessWeldedJoint(unittest.TestCase):

    def _compliant_case(self):
        """WQ1 butt weld, large area, low loads — expect all MoS positive."""
        return assess_welded_joint(
            weld_type="butt",
            quality_class="WQ1",
            weld_length=200.0,   # mm
            throat_or_leg=10.0,  # mm → area = 2000 mm²
            parent_ftu=400.0,    # MPa
            safety_factor=1.5,
            normal_load=50000.0,  # N → σ = 25 MPa
            shear_load=20000.0,   # N → τ = 10 MPa
        )

    def test_compliant_joint_is_compliant(self):
        res = self._compliant_case()
        self.assertTrue(res["compliant"])
        self.assertEqual(res["findings"], [])

    def test_compliant_joint_positive_mos_normal(self):
        res = self._compliant_case()
        self.assertGreater(res["mos_normal"], 0.0)

    def test_compliant_joint_positive_mos_shear(self):
        res = self._compliant_case()
        self.assertGreater(res["mos_shear"], 0.0)

    def test_compliant_joint_positive_mos_combined(self):
        res = self._compliant_case()
        self.assertGreater(res["mos_combined"], 0.0)

    def test_overloaded_joint_not_compliant(self):
        # Very high normal load → MoS < 0
        res = assess_welded_joint(
            weld_type="butt",
            quality_class="WQ3",
            weld_length=10.0,   # mm — short weld
            throat_or_leg=5.0,  # mm → area = 50 mm²
            parent_ftu=300.0,   # MPa
            safety_factor=2.0,
            normal_load=50000.0,  # N → σ_applied = 1000 MPa >> σ_allow = 300*0.7/2=105
            shear_load=0.0,
        )
        self.assertFalse(res["compliant"])
        self.assertGreater(len(res["findings"]), 0)
        self.assertLess(res["mos_normal"], 0.0)

    def test_wq1_higher_allowable_than_wq3(self):
        common = dict(
            weld_length=100.0, throat_or_leg=10.0,
            parent_ftu=500.0, safety_factor=1.5,
            normal_load=10000.0, shear_load=5000.0,
        )
        res_wq1 = assess_welded_joint(weld_type="butt", quality_class="WQ1", **common)
        res_wq3 = assess_welded_joint(weld_type="butt", quality_class="WQ3", **common)
        self.assertGreater(res_wq1["sigma_allow"], res_wq3["sigma_allow"])
        self.assertGreater(res_wq1["mos_normal"], res_wq3["mos_normal"])

    def test_fillet_weld_area_used_correctly(self):
        # Fillet weld should give smaller area than equivalent butt weld
        res_butt = assess_welded_joint(
            weld_type="butt", quality_class="WQ1",
            weld_length=100.0, throat_or_leg=10.0,
            parent_ftu=400.0, safety_factor=1.5,
            normal_load=5000.0, shear_load=0.0,
        )
        res_fillet = assess_welded_joint(
            weld_type="fillet", quality_class="WQ1",
            weld_length=100.0, throat_or_leg=10.0,
            parent_ftu=400.0, safety_factor=1.5,
            normal_load=5000.0, shear_load=0.0,
        )
        self.assertLess(res_fillet["weld_area"], res_butt["weld_area"])
        # Smaller area → higher applied stress → lower MoS
        self.assertGreater(res_fillet["sigma_applied"], res_butt["sigma_applied"])

    def test_zero_loads_give_inf_mos(self):
        res = assess_welded_joint(
            weld_type="butt", quality_class="WQ2",
            weld_length=100.0, throat_or_leg=8.0,
            parent_ftu=350.0, safety_factor=1.5,
            normal_load=0.0, shear_load=0.0,
        )
        self.assertEqual(res["mos_normal"], math.inf)
        self.assertEqual(res["mos_shear"], math.inf)
        self.assertTrue(res["compliant"])

    def test_weld_area_returned_correctly_butt(self):
        res = assess_welded_joint(
            weld_type="butt", quality_class="WQ1",
            weld_length=50.0, throat_or_leg=4.0,
            parent_ftu=400.0, safety_factor=2.0,
            normal_load=1000.0, shear_load=0.0,
        )
        self.assertAlmostEqual(res["weld_area"], 200.0)  # 50 * 4 = 200

    def test_invalid_quality_class_raises(self):
        with self.assertRaises(ValueError):
            assess_welded_joint(
                weld_type="butt", quality_class="WQ5",
                weld_length=100.0, throat_or_leg=10.0,
                parent_ftu=400.0, safety_factor=1.5,
                normal_load=5000.0, shear_load=0.0,
            )

    def test_efficiency_recorded_in_result(self):
        res = assess_welded_joint(
            weld_type="butt", quality_class="WQ2",
            weld_length=100.0, throat_or_leg=10.0,
            parent_ftu=400.0, safety_factor=2.0,
            normal_load=5000.0, shear_load=0.0,
        )
        self.assertAlmostEqual(res["efficiency"], 0.85)


if __name__ == "__main__":
    unittest.main()
