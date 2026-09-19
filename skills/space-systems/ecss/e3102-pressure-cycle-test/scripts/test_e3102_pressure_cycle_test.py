"""Contract test for the pressure-cycle-test leaf (stdlib unittest)."""

import unittest

from e3102_pressure_cycle_test_logic import (
    CYCLE_TOLERANCE,
    DEFAULT_MAX_CYCLE_RATE_HZ,
    DEFAULT_MAX_RAMP_RATE_PA_PER_S,
    MIN_SCATTER_FACTOR,
    assess_cycle_count,
    assess_cycle_rate,
    assess_post_cycle_leak,
    assess_pressure_cycle_test,
    assess_pressure_range,
    assess_ramp_rate,
    assess_temperature_band,
    cycle_rate_hz,
    require_count,
    require_positive,
    require_real,
    required_cycle_count,
    validate_pressure_range,
    validate_scatter_factor,
)


def good_spec(**overrides):
    spec = {
        "service_cycles": 1000,
        "scatter_factor": 4.0,
        "applied_cycles": 4000,
        "duration_s": 40000.0,
        "applied_low_pa": 0.0,
        "applied_high_pa": 2.2e6,
        "service_low_pa": 1.0e5,
        "service_high_pa": 2.0e6,
        "ramp_rate_pa_per_s": 5.0e4,
        "test_temperature_k": 293.15,
        "band_low_k": 273.15,
        "band_high_k": 323.15,
        "leak_detected_during": False,
        "measured_leak_rate": 1.0e-8,
        "allowable_leak_rate": 1.0e-6,
    }
    spec.update(overrides)
    return spec


class TestValidators(unittest.TestCase):
    def test_require_real_rejects_boolean(self):
        with self.assertRaises(ValueError):
            require_real("x", True)

    def test_require_positive_rejects_zero(self):
        with self.assertRaises(ValueError):
            require_positive("x", 0)

    def test_require_count_rejects_float(self):
        with self.assertRaises(ValueError):
            require_count("n", 1000.0)

    def test_require_count_rejects_zero(self):
        with self.assertRaises(ValueError):
            require_count("n", 0)

    def test_require_count_rejects_boolean(self):
        with self.assertRaises(ValueError):
            require_count("n", True)


class TestCycleCount(unittest.TestCase):
    def test_scatter_factor_of_one_is_the_floor(self):
        self.assertAlmostEqual(validate_scatter_factor(MIN_SCATTER_FACTOR),
                               MIN_SCATTER_FACTOR, places=9)

    def test_scatter_factor_below_one_is_refused(self):
        with self.assertRaises(ValueError):
            validate_scatter_factor(0.5)

    def test_required_count_is_the_product(self):
        self.assertEqual(required_cycle_count(1000, 4.0), 4000)

    def test_required_count_rounds_up_to_whole_cycles(self):
        self.assertEqual(required_cycle_count(333, 1.5), 500)

    def test_exact_product_does_not_gain_a_spurious_cycle(self):
        self.assertEqual(required_cycle_count(1500, 2.5), 3750)

    def test_count_exactly_meeting_the_requirement_passes(self):
        result = assess_cycle_count(4000, 1000, 4.0)
        self.assertTrue(result["compliant"])
        self.assertEqual(result["shortfall"], 0)

    def test_short_count_reports_the_shortfall(self):
        result = assess_cycle_count(3000, 1000, 4.0)
        self.assertFalse(result["compliant"])
        self.assertEqual(result["shortfall"], 1000)


class TestPressureRange(unittest.TestCase):
    def test_validated_range_is_returned_as_a_pair(self):
        self.assertEqual(validate_pressure_range(0.0, 2.0e6), (0.0, 2.0e6))

    def test_inverted_range_raises(self):
        with self.assertRaises(ValueError):
            validate_pressure_range(2.0e6, 1.0e6)

    def test_zero_width_range_raises(self):
        with self.assertRaises(ValueError):
            validate_pressure_range(1.0e6, 1.0e6)

    def test_enveloping_range_is_compliant(self):
        result = assess_pressure_range(0.0, 2.2e6, 1.0e5, 2.0e6)
        self.assertTrue(result["compliant"])
        self.assertGreater(result["amplitude_ratio"], 1.0)

    def test_range_matching_the_service_exactly_is_compliant(self):
        result = assess_pressure_range(1.0e5, 2.0e6, 1.0e5, 2.0e6)
        self.assertTrue(result["compliant"])
        self.assertAlmostEqual(result["amplitude_ratio"], 1.0, places=9)

    def test_peak_below_the_service_maximum_fails(self):
        result = assess_pressure_range(0.0, 1.5e6, 1.0e5, 2.0e6)
        self.assertFalse(result["covers_high"])
        self.assertFalse(result["compliant"])

    def test_trough_above_the_service_minimum_fails(self):
        result = assess_pressure_range(5.0e5, 2.2e6, 1.0e5, 2.0e6)
        self.assertFalse(result["covers_low"])
        self.assertTrue(any("low end" in f for f in result["findings"]))


class TestRates(unittest.TestCase):
    def test_mean_rate_is_cycles_over_duration(self):
        self.assertAlmostEqual(cycle_rate_hz(4000, 40000.0), 0.1, places=9)

    def test_rate_exactly_at_the_ceiling_passes(self):
        result = assess_cycle_rate(500, 1000.0, max_rate_hz=0.5)
        self.assertTrue(result["compliant"])
        self.assertAlmostEqual(result["rate_hz"], 0.5, places=9)

    def test_rate_above_the_ceiling_fails(self):
        result = assess_cycle_rate(4000, 1000.0, max_rate_hz=DEFAULT_MAX_CYCLE_RATE_HZ)
        self.assertFalse(result["compliant"])
        self.assertTrue(any("heats" in f for f in result["findings"]))

    def test_zero_duration_raises(self):
        with self.assertRaises(ValueError):
            cycle_rate_hz(4000, 0.0)

    def test_ramp_rate_within_the_ceiling_passes(self):
        self.assertTrue(assess_ramp_rate(5.0e4)["compliant"])

    def test_ramp_rate_exactly_at_the_ceiling_passes(self):
        result = assess_ramp_rate(DEFAULT_MAX_RAMP_RATE_PA_PER_S)
        self.assertTrue(result["compliant"])

    def test_ramp_rate_above_the_ceiling_fails(self):
        self.assertFalse(assess_ramp_rate(5.0e5)["compliant"])

    def test_negative_ramp_rate_raises(self):
        with self.assertRaises(ValueError):
            assess_ramp_rate(-1.0)


class TestTemperatureBand(unittest.TestCase):
    def test_temperature_inside_the_band_passes(self):
        self.assertTrue(assess_temperature_band(293.15, 273.15, 323.15)["compliant"])

    def test_temperature_at_the_lower_edge_passes(self):
        self.assertTrue(assess_temperature_band(273.15, 273.15, 323.15)["compliant"])

    def test_temperature_at_the_upper_edge_passes(self):
        self.assertTrue(assess_temperature_band(323.15, 273.15, 323.15)["compliant"])

    def test_temperature_outside_the_band_fails(self):
        result = assess_temperature_band(350.0, 273.15, 323.15)
        self.assertFalse(result["compliant"])
        self.assertTrue(result["findings"])

    def test_inverted_band_raises(self):
        with self.assertRaises(ValueError):
            assess_temperature_band(293.15, 323.15, 273.15)


class TestPostCycleLeak(unittest.TestCase):
    def test_clean_run_within_the_allowable_passes(self):
        result = assess_post_cycle_leak(False, 1.0e-8, 1.0e-6)
        self.assertTrue(result["compliant"])
        self.assertGreater(result["margin"], 0.0)

    def test_rate_exactly_at_the_allowable_passes(self):
        result = assess_post_cycle_leak(False, 1.0e-6, 1.0e-6)
        self.assertTrue(result["compliant"])
        self.assertAlmostEqual(result["margin"], 0.0, places=9)

    def test_rate_above_the_allowable_fails(self):
        self.assertFalse(assess_post_cycle_leak(False, 1.0e-5, 1.0e-6)["compliant"])

    def test_leak_during_cycling_fails_even_with_a_clean_final_rate(self):
        result = assess_post_cycle_leak(True, 1.0e-9, 1.0e-6)
        self.assertFalse(result["compliant"])
        self.assertTrue(any("during cycling" in f for f in result["findings"]))

    def test_non_boolean_observation_raises(self):
        with self.assertRaises(ValueError):
            assess_post_cycle_leak("none", 1.0e-9, 1.0e-6)


class TestWholeTest(unittest.TestCase):
    def test_good_campaign_is_compliant(self):
        report = assess_pressure_cycle_test(good_spec())
        self.assertTrue(report["compliant"])
        self.assertEqual(report["findings"], [])

    def test_short_count_names_the_failed_check(self):
        report = assess_pressure_cycle_test(good_spec(applied_cycles=2000))
        self.assertFalse(report["compliant"])
        self.assertIn("cycle_count", report["failed_checks"])

    def test_clipped_peak_names_the_failed_check(self):
        report = assess_pressure_cycle_test(good_spec(applied_high_pa=1.5e6))
        self.assertIn("pressure_range", report["failed_checks"])

    def test_hot_run_names_the_failed_check(self):
        report = assess_pressure_cycle_test(good_spec(test_temperature_k=400.0))
        self.assertIn("temperature", report["failed_checks"])

    def test_fast_run_names_the_failed_check(self):
        report = assess_pressure_cycle_test(good_spec(duration_s=1000.0))
        self.assertIn("cycle_rate", report["failed_checks"])

    def test_missing_key_raises(self):
        spec = good_spec()
        del spec["ramp_rate_pa_per_s"]
        with self.assertRaises(ValueError):
            assess_pressure_cycle_test(spec)

    def test_non_mapping_spec_raises(self):
        with self.assertRaises(ValueError):
            assess_pressure_cycle_test(4000)

    def test_tolerance_is_a_representation_allowance_only(self):
        self.assertLess(CYCLE_TOLERANCE, 1e-6)


if __name__ == "__main__":
    unittest.main()
