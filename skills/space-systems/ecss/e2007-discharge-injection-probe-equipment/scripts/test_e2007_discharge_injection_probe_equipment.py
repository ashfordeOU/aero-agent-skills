"""Contract tests for the clause 5.4.13.2 injection-probe bench-fitness logic."""

import math
import unittest

from e2007_discharge_injection_probe_equipment_logic import (
    CATEGORIES,
    MARGINAL_RATIO,
    RATIO_TOLERANCE,
    RISE_TIME_BANDWIDTH_PRODUCT,
    assess_bench,
    assess_item,
    cable_attenuation_db,
    categorize_ratio,
    delivered_fraction,
    mismatch_loss_db,
    reflection_coefficient,
    required_drive_voltage_v,
    rise_time_bandwidth_hz,
    voltage_standing_wave_ratio,
)


def make_spec(**overrides):
    """Return a matched, adequately sized injection-probe bench specification."""
    spec = {
        "required_current_a": 10.0,
        "required_rise_time_s": 5.0e-9,
        "probe_insertion_impedance_ohm": 50.0,
        "system_impedance_ohm": 50.0,
        "cable_impedance_ohm": 50.0,
        "cable_length_m": 3.0,
        "cable_attenuation_db_per_m_at_ref": 0.05,
        "cable_reference_frequency_hz": 1.0e8,
        "generator_open_circuit_v": 1500.0,
        "generator_rise_time_s": 2.0e-9,
        "connector_voltage_rating_v": 2000.0,
        "generator_bandwidth_hz": 2.5e8,
    }
    spec.update(overrides)
    return spec


class BandwidthTests(unittest.TestCase):
    def test_bandwidth_follows_the_rise_time_product(self):
        self.assertAlmostEqual(
            rise_time_bandwidth_hz(3.5e-9) / 1.0e8, 1.0, places=9
        )

    def test_faster_edge_demands_more_bandwidth(self):
        slow = rise_time_bandwidth_hz(1.0e-8)
        fast = rise_time_bandwidth_hz(1.0e-9)
        self.assertAlmostEqual(fast / slow, 10.0, places=9)

    def test_product_constant_is_the_published_one(self):
        self.assertAlmostEqual(RISE_TIME_BANDWIDTH_PRODUCT, 0.35, places=12)

    def test_zero_rise_time_rejected(self):
        with self.assertRaises(ValueError):
            rise_time_bandwidth_hz(0.0)

    def test_non_numeric_rise_time_rejected(self):
        with self.assertRaises(ValueError):
            rise_time_bandwidth_hz("5ns")


class MismatchTests(unittest.TestCase):
    def test_matched_cable_reflects_nothing(self):
        self.assertAlmostEqual(reflection_coefficient(50.0, 50.0), 0.0, places=12)

    def test_seventy_five_ohm_cable_in_a_fifty_ohm_chain(self):
        self.assertAlmostEqual(reflection_coefficient(75.0, 50.0), 0.2, places=12)
        self.assertAlmostEqual(voltage_standing_wave_ratio(75.0, 50.0), 1.5, places=12)

    def test_reflection_sign_flips_below_the_system_impedance(self):
        self.assertLess(reflection_coefficient(25.0, 50.0), 0.0)

    def test_matched_cable_has_unit_vswr(self):
        self.assertAlmostEqual(voltage_standing_wave_ratio(50.0, 50.0), 1.0, places=12)

    def test_matched_cable_loses_nothing_to_the_mismatch(self):
        self.assertAlmostEqual(mismatch_loss_db(50.0, 50.0), 0.0, places=12)

    def test_mismatch_loss_is_positive_for_any_mismatch(self):
        self.assertGreater(mismatch_loss_db(75.0, 50.0), 0.0)

    def test_mismatch_loss_is_symmetric_in_the_ratio(self):
        self.assertAlmostEqual(
            mismatch_loss_db(100.0, 50.0), mismatch_loss_db(25.0, 50.0), places=9
        )

    def test_negative_impedance_rejected(self):
        with self.assertRaises(ValueError):
            reflection_coefficient(-50.0, 50.0)


class AttenuationTests(unittest.TestCase):
    def test_attenuation_at_the_reference_frequency_is_the_quoted_figure(self):
        value = cable_attenuation_db(10.0, 0.1, 1.0e8, 1.0e8)
        self.assertAlmostEqual(value, 1.0, places=9)

    def test_attenuation_scales_with_the_square_root_of_frequency(self):
        value = cable_attenuation_db(10.0, 0.1, 4.0e8, 1.0e8)
        self.assertAlmostEqual(value, 2.0, places=9)

    def test_attenuation_scales_linearly_with_length(self):
        short = cable_attenuation_db(2.0, 0.1, 1.0e8, 1.0e8)
        long_run = cable_attenuation_db(6.0, 0.1, 1.0e8, 1.0e8)
        self.assertAlmostEqual(long_run / short, 3.0, places=9)

    def test_lossless_cable_is_allowed(self):
        self.assertAlmostEqual(cable_attenuation_db(3.0, 0.0, 1.0e8, 1.0e8), 0.0, places=12)

    def test_negative_attenuation_rejected(self):
        with self.assertRaises(ValueError):
            cable_attenuation_db(3.0, -0.05, 1.0e8, 1.0e8)

    def test_zero_length_rejected(self):
        with self.assertRaises(ValueError):
            cable_attenuation_db(0.0, 0.05, 1.0e8, 1.0e8)


class DriveTests(unittest.TestCase):
    def test_lossless_chain_delivers_everything(self):
        self.assertAlmostEqual(delivered_fraction(0.0), 1.0, places=12)

    def test_twenty_db_delivers_a_tenth(self):
        self.assertAlmostEqual(delivered_fraction(20.0), 0.1, places=9)

    def test_negative_loss_rejected(self):
        with self.assertRaises(ValueError):
            delivered_fraction(-3.0)

    def test_drive_is_current_times_insertion_impedance_when_lossless(self):
        self.assertAlmostEqual(required_drive_voltage_v(10.0, 50.0, 0.0), 500.0, places=9)

    def test_loss_raises_the_drive_demanded(self):
        self.assertAlmostEqual(required_drive_voltage_v(10.0, 50.0, 20.0), 5000.0, places=6)

    def test_zero_required_current_rejected(self):
        with self.assertRaises(ValueError):
            required_drive_voltage_v(0.0, 50.0, 0.0)


class CategorizeTests(unittest.TestCase):
    def test_categories_are_the_three_published_ones(self):
        self.assertEqual(CATEGORIES, ("adequate", "marginal", "inadequate"))

    def test_shortfall_is_inadequate(self):
        self.assertEqual(categorize_ratio(0.9), "inadequate")

    def test_exactly_meeting_the_requirement_is_marginal_not_inadequate(self):
        self.assertEqual(categorize_ratio(1.0), "marginal")

    def test_exactly_at_the_headroom_band_is_adequate(self):
        self.assertEqual(categorize_ratio(MARGINAL_RATIO), "adequate")

    def test_comfortable_headroom_is_adequate(self):
        self.assertEqual(categorize_ratio(4.0), "adequate")

    def test_tolerance_is_small_enough_to_be_representation_only(self):
        self.assertLess(RATIO_TOLERANCE, 1.0e-6)

    def test_zero_ratio_rejected(self):
        with self.assertRaises(ValueError):
            categorize_ratio(0.0)


class AssessItemTests(unittest.TestCase):
    def test_higher_is_better_item_forms_capability_over_requirement(self):
        item = assess_item("pulse-generator-open-circuit-voltage", 1000.0, 500.0)
        self.assertAlmostEqual(item["ratio"], 2.0, places=12)
        self.assertEqual(item["category"], "adequate")

    def test_lower_is_better_item_inverts_the_ratio(self):
        item = assess_item("pulse-generator-rise-time", 2.0e-9, 5.0e-9, higher_is_better=False)
        self.assertAlmostEqual(item["ratio"], 2.5, places=12)

    def test_lower_is_better_item_fails_when_it_is_too_slow(self):
        item = assess_item("pulse-generator-rise-time", 1.0e-8, 5.0e-9, higher_is_better=False)
        self.assertEqual(item["category"], "inadequate")

    def test_blank_item_name_rejected(self):
        with self.assertRaises(ValueError):
            assess_item("   ", 1000.0, 500.0)

    def test_boolean_capability_rejected(self):
        with self.assertRaises(ValueError):
            assess_item("pulse-generator-open-circuit-voltage", True, 500.0)


class AssessBenchTests(unittest.TestCase):
    def test_matched_bench_fits(self):
        result = assess_bench(make_spec())
        self.assertTrue(result["bench_fit"])
        self.assertEqual(result["inadequate_items"], [])
        self.assertEqual(len(result["items"]), 6)

    def test_bandwidth_comes_from_the_required_edge(self):
        result = assess_bench(make_spec())
        self.assertAlmostEqual(result["chain_bandwidth_hz"] / 7.0e7, 1.0, places=9)

    def test_matched_cable_reports_unit_vswr(self):
        self.assertAlmostEqual(assess_bench(make_spec())["cable_vswr"], 1.0, places=12)

    def test_undersized_generator_is_inadequate_and_governs(self):
        result = assess_bench(make_spec(generator_open_circuit_v=300.0))
        self.assertFalse(result["bench_fit"])
        self.assertIn("pulse-generator-open-circuit-voltage", result["inadequate_items"])
        self.assertEqual(result["governing_item"], "pulse-generator-open-circuit-voltage")

    def test_mismatched_cable_is_caught(self):
        result = assess_bench(make_spec(cable_impedance_ohm=75.0))
        self.assertFalse(result["bench_fit"])
        self.assertIn("coaxial-cable-impedance-match", result["inadequate_items"])
        self.assertGreater(result["cable_vswr"], 1.4)

    def test_slow_generator_edge_is_caught(self):
        result = assess_bench(make_spec(generator_rise_time_s=2.0e-8))
        self.assertIn("pulse-generator-rise-time", result["inadequate_items"])

    def test_underrated_connector_is_caught(self):
        result = assess_bench(make_spec(connector_voltage_rating_v=400.0))
        self.assertIn("coaxial-connector-voltage-rating", result["inadequate_items"])

    def test_long_lossy_cable_raises_the_drive_demanded(self):
        short = assess_bench(make_spec())
        long_run = assess_bench(make_spec(cable_length_m=40.0))
        self.assertGreater(
            long_run["required_drive_voltage_v"], short["required_drive_voltage_v"]
        )
        self.assertGreater(long_run["total_loss_db"], short["total_loss_db"])

    def test_bandwidth_item_is_optional(self):
        spec = make_spec()
        del spec["generator_bandwidth_hz"]
        result = assess_bench(spec)
        self.assertEqual(len(result["items"]), 5)
        self.assertNotIn("pulse-generator-bandwidth", [i["item"] for i in result["items"]])

    def test_narrow_band_generator_is_caught_when_declared(self):
        result = assess_bench(make_spec(generator_bandwidth_hz=3.0e7))
        self.assertIn("pulse-generator-bandwidth", result["inadequate_items"])

    def test_marginal_generator_is_listed_without_failing_the_bench(self):
        drive = assess_bench(make_spec())["required_drive_voltage_v"]
        result = assess_bench(make_spec(generator_open_circuit_v=drive * 1.1))
        self.assertTrue(result["bench_fit"])
        self.assertIn("pulse-generator-open-circuit-voltage", result["marginal_items"])

    def test_governing_item_is_the_least_headroom(self):
        result = assess_bench(make_spec())
        ratios = [item["ratio"] for item in result["items"]]
        self.assertAlmostEqual(result["governing_ratio"], min(ratios), places=12)

    def test_delivered_fraction_agrees_with_the_total_loss(self):
        result = assess_bench(make_spec(cable_length_m=20.0))
        self.assertAlmostEqual(
            result["delivered_fraction"],
            math.pow(10.0, -result["total_loss_db"] / 20.0),
            places=12,
        )

    def test_missing_key_rejected(self):
        spec = make_spec()
        del spec["cable_length_m"]
        with self.assertRaises(ValueError):
            assess_bench(spec)

    def test_non_mapping_spec_rejected(self):
        with self.assertRaises(ValueError):
            assess_bench(["required_current_a"])


if __name__ == "__main__":
    unittest.main()
