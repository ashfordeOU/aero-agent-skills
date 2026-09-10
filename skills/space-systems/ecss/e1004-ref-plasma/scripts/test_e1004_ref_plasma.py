#!/usr/bin/env python3
"""Offline, deterministic unittest contract for e1004_ref_plasma_logic."""

import math
import unittest

from e1004_ref_plasma_logic import (
    PLASMA_REGIONS,
    charging_risk_assessment,
    classify_value_against_range,
    log_interpolate,
    plasma_region_reference,
    representative_value,
    select_region,
    validate_density,
    validate_temperature,
)


class TestPlasmaRegionReference(unittest.TestCase):
    def test_known_region_returns_expected_fields(self):
        ref = plasma_region_reference("ionosphere")
        self.assertEqual(ref["density_range_cm3"], (1.0e3, 1.0e6))
        self.assertEqual(ref["temperature_range_ev"], (0.03, 0.3))
        self.assertFalse(ref["charging_risk"])

    def test_unrecognized_region_raises(self):
        with self.assertRaises(ValueError):
            plasma_region_reference("thermosphere")

    def test_returned_dict_is_a_copy(self):
        ref = plasma_region_reference("solar_wind")
        ref["density_range_cm3"] = (0, 0)
        self.assertEqual(
            PLASMA_REGIONS["solar_wind"]["density_range_cm3"], (1.0, 1.0e1)
        )

    def test_all_seven_regions_present(self):
        expected = {
            "ionosphere",
            "plasmasphere",
            "auroral",
            "outer_magnetosphere",
            "solar_wind",
            "magnetosheath",
            "magnetotail_l2",
        }
        self.assertEqual(set(PLASMA_REGIONS), expected)


class TestClassifyValueAgainstRange(unittest.TestCase):
    def test_below_range(self):
        self.assertEqual(classify_value_against_range(1.0, 10.0, 100.0), "below_range")

    def test_within_range_interior(self):
        self.assertEqual(classify_value_against_range(50.0, 10.0, 100.0), "within_range")

    def test_within_range_at_lower_bound(self):
        self.assertEqual(classify_value_against_range(10.0, 10.0, 100.0), "within_range")

    def test_within_range_at_upper_bound(self):
        self.assertEqual(classify_value_against_range(100.0, 10.0, 100.0), "within_range")

    def test_above_range(self):
        self.assertEqual(classify_value_against_range(200.0, 10.0, 100.0), "above_range")

    def test_negative_value_raises(self):
        with self.assertRaises(ValueError):
            classify_value_against_range(-1.0, 10.0, 100.0)

    def test_inverted_range_raises(self):
        with self.assertRaises(ValueError):
            classify_value_against_range(50.0, 100.0, 10.0)


class TestValidateDensityAndTemperature(unittest.TestCase):
    def test_validate_density_within_range(self):
        self.assertEqual(validate_density("plasmasphere", 500.0), "within_range")

    def test_validate_density_below_range(self):
        self.assertEqual(validate_density("plasmasphere", 1.0), "below_range")

    def test_validate_density_unrecognized_region_raises(self):
        with self.assertRaises(ValueError):
            validate_density("no_such_region", 1.0)

    def test_validate_temperature_above_range(self):
        self.assertEqual(validate_temperature("ionosphere", 5.0), "above_range")

    def test_validate_temperature_at_exact_upper_bound(self):
        self.assertEqual(validate_temperature("ionosphere", 0.3), "within_range")


class TestLogInterpolate(unittest.TestCase):
    def test_fraction_zero_returns_lo(self):
        self.assertAlmostEqual(log_interpolate(10.0, 1000.0, 0.0), 10.0)

    def test_fraction_one_returns_hi(self):
        self.assertAlmostEqual(log_interpolate(10.0, 1000.0, 1.0), 1000.0)

    def test_fraction_half_returns_geometric_mean(self):
        result = log_interpolate(10.0, 1000.0, 0.5)
        self.assertAlmostEqual(result, math.sqrt(10.0 * 1000.0))

    def test_fraction_out_of_range_raises(self):
        with self.assertRaises(ValueError):
            log_interpolate(10.0, 100.0, 1.5)

    def test_nonpositive_lo_raises(self):
        with self.assertRaises(ValueError):
            log_interpolate(0.0, 100.0, 0.5)

    def test_inverted_range_raises(self):
        with self.assertRaises(ValueError):
            log_interpolate(100.0, 10.0, 0.5)


class TestRepresentativeValue(unittest.TestCase):
    def test_density_default_fraction(self):
        expected = math.sqrt(1.0e3 * 1.0e6)
        self.assertAlmostEqual(representative_value("ionosphere", "density"), expected)

    def test_temperature_endpoint_fraction(self):
        self.assertAlmostEqual(
            representative_value("auroral", "temperature", fraction=0.0), 1.0e2
        )

    def test_invalid_quantity_raises(self):
        with self.assertRaises(ValueError):
            representative_value("ionosphere", "flux")


class TestSelectRegion(unittest.TestCase):
    def test_all_known_regimes_map(self):
        self.assertEqual(select_region("leo_ionosphere"), "ionosphere")
        self.assertEqual(select_region("meo_plasmasphere_crossing"), "plasmasphere")
        self.assertEqual(select_region("auroral_oval_pass"), "auroral")
        self.assertEqual(select_region("geo_outer_magnetosphere"), "outer_magnetosphere")
        self.assertEqual(select_region("interplanetary_solar_wind"), "solar_wind")
        self.assertEqual(select_region("magnetosheath_crossing"), "magnetosheath")
        self.assertEqual(select_region("magnetotail_or_l2"), "magnetotail_l2")

    def test_unknown_regime_raises(self):
        with self.assertRaises(ValueError):
            select_region("cislunar_transfer")


class TestChargingRiskAssessment(unittest.TestCase):
    def test_flags_hot_tenuous_auroral_condition(self):
        result = charging_risk_assessment("auroral", 5.0, 5000.0)
        self.assertTrue(result["charging_risk_region"])
        self.assertTrue(result["surface_charging_flag"])
        self.assertEqual(result["density_classification"], "within_range")
        self.assertEqual(result["temperature_classification"], "within_range")

    def test_non_risk_region_never_flags(self):
        result = charging_risk_assessment("ionosphere", 1.0e4, 0.2)
        self.assertFalse(result["charging_risk_region"])
        self.assertFalse(result["surface_charging_flag"])

    def test_risk_region_with_cold_reading_not_flagged(self):
        result = charging_risk_assessment("outer_magnetosphere", 0.5, 10.0)
        self.assertEqual(result["temperature_classification"], "below_range")
        self.assertFalse(result["surface_charging_flag"])

    def test_risk_region_with_dense_reading_not_flagged(self):
        result = charging_risk_assessment("magnetotail_l2", 50.0, 5000.0)
        self.assertEqual(result["density_classification"], "above_range")
        self.assertFalse(result["surface_charging_flag"])

    def test_unrecognized_region_raises(self):
        with self.assertRaises(ValueError):
            charging_risk_assessment("no_such_region", 1.0, 1.0)


if __name__ == "__main__":
    unittest.main()
