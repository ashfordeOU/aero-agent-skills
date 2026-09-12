"""
Gate-3 contract tests for fracture_material_data_logic.
Offline, deterministic, stdlib unittest only.
Run: python3 test_fracture_material_data.py
"""

import math
import os
import sys
import unittest

sys.path.insert(0, os.path.dirname(__file__))

from fracture_material_data_logic import (
    HANDBOOK_KNOCKDOWN,
    LIMITED_DATA_KNOCKDOWN,
    MIN_PARIS_DATA_POINTS,
    REGION_NEAR_KIC,
    REGION_PARIS,
    REGION_THRESHOLD,
    apply_knockdown,
    categorize_data_source,
    crack_growth_region,
    derive_paris_parameters,
    paris_crack_growth_rate,
    summarise_material_record,
    threshold_for_r_ratio,
    validate_kic_specimen,
)


class TestKicSpecimenValidity(unittest.TestCase):

    def test_valid_specimen_returns_true(self):
        # criterion = 2.5*(30/600)^2 = 0.00625 m; B=a=0.025 m → margin = 3.0
        result = validate_kic_specimen(B=0.025, a=0.025, KIC=30.0, sigma_ys=600.0)
        self.assertTrue(result["is_valid"])
        self.assertAlmostEqual(result["criterion_value"], 0.00625, places=8)
        self.assertGreater(result["margin_B"], 0.0)
        self.assertGreater(result["margin_a"], 0.0)

    def test_thin_specimen_fails_on_B(self):
        # B=0.005 m < criterion 0.00625 m → invalid
        result = validate_kic_specimen(B=0.005, a=0.025, KIC=30.0, sigma_ys=600.0)
        self.assertFalse(result["is_valid"])
        self.assertLess(result["margin_B"], 0.0)
        self.assertGreater(result["margin_a"], 0.0)

    def test_short_crack_fails_on_a(self):
        result = validate_kic_specimen(B=0.025, a=0.005, KIC=30.0, sigma_ys=600.0)
        self.assertFalse(result["is_valid"])
        self.assertGreater(result["margin_B"], 0.0)
        self.assertLess(result["margin_a"], 0.0)

    def test_zero_B_raises(self):
        with self.assertRaises(ValueError):
            validate_kic_specimen(B=0.0, a=0.025, KIC=30.0, sigma_ys=600.0)

    def test_negative_KIC_raises(self):
        with self.assertRaises(ValueError):
            validate_kic_specimen(B=0.025, a=0.025, KIC=-5.0, sigma_ys=600.0)

    def test_zero_sigma_ys_raises(self):
        with self.assertRaises(ValueError):
            validate_kic_specimen(B=0.025, a=0.025, KIC=30.0, sigma_ys=0.0)


class TestParisCrackGrowthRate(unittest.TestCase):

    def test_basic_paris_rate(self):
        # da/dN = 1e-11 * 20^3 = 8e-8
        rate = paris_crack_growth_rate(delta_K=20.0, C=1e-11, n=3.0)
        self.assertAlmostEqual(rate, 8e-8, places=20)

    def test_zero_rate_at_or_below_threshold(self):
        rate = paris_crack_growth_rate(delta_K=5.0, C=1e-11, n=3.0, delta_Kth=8.0)
        self.assertEqual(rate, 0.0)

    def test_zero_rate_exactly_at_threshold(self):
        rate = paris_crack_growth_rate(delta_K=8.0, C=1e-11, n=3.0, delta_Kth=8.0)
        self.assertEqual(rate, 0.0)

    def test_growth_above_threshold(self):
        rate = paris_crack_growth_rate(delta_K=10.0, C=1e-11, n=3.0, delta_Kth=8.0)
        self.assertAlmostEqual(rate, 1e-11 * 10.0 ** 3.0, places=20)

    def test_negative_delta_K_raises(self):
        with self.assertRaises(ValueError):
            paris_crack_growth_rate(delta_K=-1.0, C=1e-11, n=3.0)

    def test_non_positive_C_raises(self):
        with self.assertRaises(ValueError):
            paris_crack_growth_rate(delta_K=10.0, C=0.0, n=3.0)


class TestThresholdForRRatio(unittest.TestCase):

    def test_r_zero_no_change(self):
        result = threshold_for_r_ratio(delta_Kth_R0=5.0, R=0.0)
        self.assertAlmostEqual(result, 5.0, places=10)

    def test_r_positive_reduces_threshold(self):
        # γ=0.5: ΔKth(0.5) = 5.0 * sqrt(0.5)
        expected = 5.0 * (0.5 ** 0.5)
        result = threshold_for_r_ratio(delta_Kth_R0=5.0, R=0.5)
        self.assertAlmostEqual(result, expected, places=10)

    def test_compressive_R_treated_as_zero(self):
        result = threshold_for_r_ratio(delta_Kth_R0=5.0, R=-0.5)
        self.assertAlmostEqual(result, 5.0, places=10)

    def test_r_one_raises(self):
        with self.assertRaises(ValueError):
            threshold_for_r_ratio(delta_Kth_R0=5.0, R=1.0)

    def test_r_above_one_raises(self):
        with self.assertRaises(ValueError):
            threshold_for_r_ratio(delta_Kth_R0=5.0, R=1.5)

    def test_custom_walker_exponent(self):
        # γ=1.0: ΔKth(R) = ΔKth(0) * (1-R)
        result = threshold_for_r_ratio(delta_Kth_R0=10.0, R=0.4, walker_exponent=1.0)
        self.assertAlmostEqual(result, 10.0 * 0.6, places=10)


class TestCategorizeDataSource(unittest.TestCase):

    def test_test_derived_accepted(self):
        self.assertEqual(categorize_data_source("test-derived"), "test-derived")

    def test_handbook_accepted(self):
        self.assertEqual(categorize_data_source("handbook"), "handbook")

    def test_limited_accepted(self):
        self.assertEqual(categorize_data_source("limited"), "limited")

    def test_whitespace_and_case_normalised(self):
        self.assertEqual(categorize_data_source("  Handbook  "), "handbook")

    def test_unknown_source_raises(self):
        with self.assertRaises(ValueError):
            categorize_data_source("estimate")

    def test_empty_string_raises(self):
        with self.assertRaises(ValueError):
            categorize_data_source("")


class TestCrackGrowthRegion(unittest.TestCase):

    def test_threshold_region_below_delta_kth(self):
        region = crack_growth_region(delta_K=2.0, delta_Kth=4.0, KIC=50.0)
        self.assertEqual(region, REGION_THRESHOLD)

    def test_threshold_region_at_delta_kth(self):
        region = crack_growth_region(delta_K=4.0, delta_Kth=4.0, KIC=50.0)
        self.assertEqual(region, REGION_THRESHOLD)

    def test_paris_region_between_threshold_and_near_kic(self):
        region = crack_growth_region(delta_K=10.0, delta_Kth=4.0, KIC=50.0, R=0.0)
        self.assertEqual(region, REGION_PARIS)

    def test_near_kic_region(self):
        # Kmax = 45/(1-0) = 45; 0.8*50 = 40; 45 >= 40 → near-KIC
        region = crack_growth_region(delta_K=45.0, delta_Kth=4.0, KIC=50.0, R=0.0)
        self.assertEqual(region, REGION_NEAR_KIC)

    def test_zero_KIC_raises(self):
        with self.assertRaises(ValueError):
            crack_growth_region(delta_K=10.0, delta_Kth=4.0, KIC=0.0)

    def test_R_at_one_raises(self):
        with self.assertRaises(ValueError):
            crack_growth_region(delta_K=10.0, delta_Kth=4.0, KIC=50.0, R=1.0)


class TestDeriveParisParsameters(unittest.TestCase):

    def test_exact_fit_recovers_exponent(self):
        C_true, n_true = 1e-11, 3.0
        dk = [10.0, 20.0, 30.0, 40.0]
        dadn = [C_true * v ** n_true for v in dk]
        result = derive_paris_parameters(dk, dadn)
        self.assertAlmostEqual(result["n"], n_true, places=5)
        self.assertAlmostEqual(result["r_squared"], 1.0, places=8)
        self.assertEqual(result["n_points"], 4)

    def test_exact_fit_recovers_coefficient(self):
        C_true, n_true = 2.5e-12, 3.5
        dk = [15.0, 25.0, 35.0, 45.0]
        dadn = [C_true * v ** n_true for v in dk]
        result = derive_paris_parameters(dk, dadn)
        self.assertAlmostEqual(result["C"], C_true, delta=C_true * 1e-4)

    def test_too_few_points_raises(self):
        with self.assertRaises(ValueError):
            derive_paris_parameters([10.0, 20.0], [1e-8, 2e-8])

    def test_mismatched_lengths_raises(self):
        with self.assertRaises(ValueError):
            derive_paris_parameters([10.0, 20.0, 30.0], [1e-8, 2e-8])

    def test_nonpositive_delta_K_raises(self):
        with self.assertRaises(ValueError):
            derive_paris_parameters([0.0, 20.0, 30.0], [1e-8, 2e-8, 3e-8])

    def test_nonpositive_da_dn_raises(self):
        with self.assertRaises(ValueError):
            derive_paris_parameters([10.0, 20.0, 30.0], [-1e-8, 2e-8, 3e-8])

    def test_minimum_three_points_accepted(self):
        C_true, n_true = 1e-11, 3.0
        dk = [10.0, 20.0, 30.0]
        dadn = [C_true * v ** n_true for v in dk]
        result = derive_paris_parameters(dk, dadn)
        self.assertEqual(result["n_points"], MIN_PARIS_DATA_POINTS)


class TestApplyKnockdown(unittest.TestCase):

    def test_test_derived_no_knockdown(self):
        self.assertAlmostEqual(apply_knockdown(50.0, "test-derived"), 50.0)

    def test_handbook_knockdown_applied(self):
        self.assertAlmostEqual(
            apply_knockdown(50.0, "handbook"), 50.0 * HANDBOOK_KNOCKDOWN
        )

    def test_limited_knockdown_applied(self):
        self.assertAlmostEqual(
            apply_knockdown(50.0, "limited"), 50.0 * LIMITED_DATA_KNOCKDOWN
        )

    def test_unknown_source_raises(self):
        with self.assertRaises(ValueError):
            apply_knockdown(50.0, "unknown")


class TestSummariseMaterialRecord(unittest.TestCase):

    def test_test_derived_no_warnings_no_knockdown(self):
        record = summarise_material_record(
            name="AlLi-2195", KIC=35.0, delta_Kth=4.5,
            paris_C=1e-11, paris_n=3.2, source_type="test-derived", R_ratio=0.1,
        )
        self.assertEqual(record["name"], "AlLi-2195")
        self.assertAlmostEqual(record["KIC_adjusted"], 35.0)
        self.assertEqual(len(record["warnings"]), 0)

    def test_handbook_record_carries_warning(self):
        record = summarise_material_record(
            name="Ti-6Al-4V", KIC=80.0, delta_Kth=6.0,
            paris_C=5e-12, paris_n=3.5, source_type="handbook", R_ratio=0.0,
        )
        self.assertTrue(any("Handbook data" in w for w in record["warnings"]))

    def test_limited_record_applies_knockdown(self):
        record = summarise_material_record(
            name="SS-304", KIC=60.0, delta_Kth=5.0,
            paris_C=8e-12, paris_n=3.1, source_type="limited", R_ratio=0.0,
        )
        self.assertAlmostEqual(
            record["KIC_adjusted"], 60.0 * LIMITED_DATA_KNOCKDOWN
        )

    def test_limited_record_carries_warning(self):
        record = summarise_material_record(
            name="SS-304", KIC=60.0, delta_Kth=5.0,
            paris_C=8e-12, paris_n=3.1, source_type="limited", R_ratio=0.0,
        )
        self.assertTrue(any("Limited data" in w for w in record["warnings"]))

    def test_high_r_ratio_generates_warning(self):
        record = summarise_material_record(
            name="Al-7075", KIC=25.0, delta_Kth=3.0,
            paris_C=2e-11, paris_n=2.8, source_type="test-derived", R_ratio=0.7,
        )
        self.assertTrue(any("R ratio" in w for w in record["warnings"]))

    def test_empty_name_raises(self):
        with self.assertRaises(ValueError):
            summarise_material_record(
                name="", KIC=30.0, delta_Kth=4.0,
                paris_C=1e-11, paris_n=3.0, source_type="test-derived",
            )

    def test_negative_KIC_raises(self):
        with self.assertRaises(ValueError):
            summarise_material_record(
                name="Mat-A", KIC=-10.0, delta_Kth=4.0,
                paris_C=1e-11, paris_n=3.0, source_type="test-derived",
            )

    def test_r_ratio_adjustment_reflected_in_threshold(self):
        # At R=0.5, Walker γ=0.5: ΔKth(0.5) = 5.0 * sqrt(0.5) ≈ 3.536
        record = summarise_material_record(
            name="Mat-B", KIC=50.0, delta_Kth=5.0,
            paris_C=1e-11, paris_n=3.0, source_type="test-derived", R_ratio=0.5,
        )
        expected = 5.0 * (0.5 ** 0.5)  # no knockdown for test-derived
        self.assertAlmostEqual(record["delta_Kth_adjusted"], expected, places=8)


if __name__ == "__main__":
    unittest.main()
