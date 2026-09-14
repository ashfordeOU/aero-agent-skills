"""Contract tests for the clause 4.6.5 microwave-monolithic-circuit logic."""

import math
import unittest

from q6013_class_1_microwave_integrated_circuits_logic import (
    BOLTZMANN_EV_PER_K,
    CHANNEL_TEMPERATURE_LIMIT_C,
    TEMPERATURE_TOLERANCE_C,
    assess_mmic_procurement,
    channel_temperature_c,
    channel_temperature_margin_c,
    median_life_hours,
    pcm_lot_acceptance,
    procurement_route,
    rf_drift_fraction,
    technology_channel_limit_c,
)

PCM_LIMITS = {
    "sheet-resistance-ohm-per-square": (120.0, 180.0),
    "pinch-off-voltage-v": (-2.2, -1.4),
    "saturated-drain-current-ma-per-mm": (300.0, 460.0),
}

PCM_GOOD = {
    "sheet-resistance-ohm-per-square": 152.0,
    "pinch-off-voltage-v": -1.8,
    "saturated-drain-current-ma-per-mm": 390.0,
}


def clean_spec(**overrides):
    """A space-evaluated pHEMT amplifier die that should buy as-is."""
    spec = {
        "technology": "gaas-phemt",
        "line_standing": "space-evaluated-line",
        "has_lot_pcm_data": True,
        "upscreening_available": True,
        "base_temperature_c": 60.0,
        "dissipated_power_w": 2.0,
        "thermal_resistance_c_per_w": 12.0,
        "reference_life_hours": 1.0e6,
        "reference_channel_temp_c": 150.0,
        "activation_energy_ev": 1.5,
        "required_life_hours": 1.5e5,
        "pcm_measurements": dict(PCM_GOOD),
        "pcm_limits": dict(PCM_LIMITS),
        "rf_initial": 21.0,
        "rf_final": 20.8,
        "allowed_rf_drift_fraction": 0.05,
    }
    spec.update(overrides)
    return spec


class TechnologyLimitTests(unittest.TestCase):
    def test_gallium_arsenide_phemt_ceiling(self):
        self.assertAlmostEqual(technology_channel_limit_c("gaas-phemt"), 110.0, places=9)

    def test_gallium_nitride_ceiling_is_the_highest(self):
        limits = sorted(CHANNEL_TEMPERATURE_LIMIT_C.items(), key=lambda kv: kv[1])
        self.assertEqual(limits[-1][0], "gan-hemt")

    def test_lookup_is_case_and_space_insensitive(self):
        self.assertAlmostEqual(technology_channel_limit_c("  SiGe-HBT "), 125.0, places=9)

    def test_unknown_technology_rejected(self):
        with self.assertRaises(ValueError):
            technology_channel_limit_c("germanium-tunnel")

    def test_empty_technology_rejected(self):
        with self.assertRaises(ValueError):
            technology_channel_limit_c("")


class ChannelTemperatureTests(unittest.TestCase):
    def test_rise_is_power_times_resistance(self):
        self.assertAlmostEqual(channel_temperature_c(60.0, 2.0, 12.0), 84.0, places=9)

    def test_zero_dissipation_leaves_the_base_temperature(self):
        self.assertAlmostEqual(channel_temperature_c(70.0, 0.0, 30.0), 70.0, places=9)

    def test_negative_base_temperature_is_allowed(self):
        self.assertAlmostEqual(channel_temperature_c(-40.0, 1.0, 10.0), -30.0, places=9)

    def test_negative_dissipation_rejected(self):
        with self.assertRaises(ValueError):
            channel_temperature_c(60.0, -2.0, 12.0)

    def test_base_below_absolute_zero_rejected(self):
        with self.assertRaises(ValueError):
            channel_temperature_c(-300.0, 2.0, 12.0)

    def test_non_numeric_resistance_rejected(self):
        with self.assertRaises(ValueError):
            channel_temperature_c(60.0, 2.0, "12")


class MarginTests(unittest.TestCase):
    def test_margin_is_limit_minus_channel(self):
        result = channel_temperature_margin_c("gaas-phemt", 84.0)
        self.assertAlmostEqual(result["margin_c"], 26.0, places=9)
        self.assertTrue(result["within_limit"])

    def test_exactly_at_the_ceiling_is_inside(self):
        result = channel_temperature_margin_c("gaas-phemt", 110.0)
        self.assertAlmostEqual(result["margin_c"], 0.0, places=9)
        self.assertTrue(result["within_limit"])

    def test_above_the_ceiling_is_outside(self):
        result = channel_temperature_margin_c("gaas-phemt", 130.0)
        self.assertFalse(result["within_limit"])
        self.assertAlmostEqual(result["margin_c"], -20.0, places=9)

    def test_tolerance_is_tight(self):
        self.assertLessEqual(TEMPERATURE_TOLERANCE_C, 1e-6)


class MedianLifeTests(unittest.TestCase):
    def test_life_at_the_reference_point_is_the_reference(self):
        self.assertAlmostEqual(
            median_life_hours(1.0e6, 150.0, 150.0, 1.5), 1.0e6, places=3
        )

    def test_cooler_channel_extends_life(self):
        cool = median_life_hours(1.0e6, 150.0, 100.0, 1.5)
        self.assertGreater(cool, 1.0e6)

    def test_hotter_channel_shortens_life(self):
        hot = median_life_hours(1.0e6, 150.0, 200.0, 1.5)
        self.assertLess(hot, 1.0e6)

    def test_life_matches_the_closed_form(self):
        expected = 1.0e6 * math.exp(
            (1.5 / BOLTZMANN_EV_PER_K) * (1.0 / 373.15 - 1.0 / 423.15)
        )
        self.assertAlmostEqual(
            median_life_hours(1.0e6, 150.0, 100.0, 1.5) / expected, 1.0, places=9
        )

    def test_non_positive_reference_life_rejected(self):
        with self.assertRaises(ValueError):
            median_life_hours(0.0, 150.0, 100.0, 1.5)

    def test_channel_below_absolute_zero_rejected(self):
        with self.assertRaises(ValueError):
            median_life_hours(1.0e6, 150.0, -400.0, 1.5)


class PcmTests(unittest.TestCase):
    def test_all_inside_limits_accepts(self):
        result = pcm_lot_acceptance(dict(PCM_GOOD), dict(PCM_LIMITS))
        self.assertTrue(result["accepted"])
        self.assertEqual(result["out_of_limit"], ())

    def test_value_on_the_lower_limit_is_inside(self):
        measurements = dict(PCM_GOOD)
        measurements["sheet-resistance-ohm-per-square"] = 120.0
        self.assertTrue(pcm_lot_acceptance(measurements, dict(PCM_LIMITS))["accepted"])

    def test_value_on_the_upper_limit_is_inside(self):
        measurements = dict(PCM_GOOD)
        measurements["saturated-drain-current-ma-per-mm"] = 460.0
        self.assertTrue(pcm_lot_acceptance(measurements, dict(PCM_LIMITS))["accepted"])

    def test_outlier_is_named(self):
        measurements = dict(PCM_GOOD)
        measurements["pinch-off-voltage-v"] = -2.6
        result = pcm_lot_acceptance(measurements, dict(PCM_LIMITS))
        self.assertFalse(result["accepted"])
        self.assertEqual(result["out_of_limit"], ("pinch-off-voltage-v",))

    def test_missing_limit_pair_rejected(self):
        measurements = dict(PCM_GOOD)
        measurements["gate-leakage-ua-per-mm"] = 0.4
        with self.assertRaises(ValueError):
            pcm_lot_acceptance(measurements, dict(PCM_LIMITS))

    def test_inverted_limit_pair_rejected(self):
        with self.assertRaises(ValueError):
            pcm_lot_acceptance({"a": 1.0}, {"a": (5.0, 2.0)})

    def test_empty_measurement_set_rejected(self):
        with self.assertRaises(ValueError):
            pcm_lot_acceptance({}, dict(PCM_LIMITS))

    def test_malformed_limit_rejected(self):
        with self.assertRaises(ValueError):
            pcm_lot_acceptance({"a": 1.0}, {"a": 5.0})


class DriftTests(unittest.TestCase):
    def test_drift_is_a_magnitude(self):
        self.assertAlmostEqual(rf_drift_fraction(20.0, 19.0), 0.05, places=9)

    def test_upward_and_downward_drift_match(self):
        self.assertAlmostEqual(
            rf_drift_fraction(20.0, 21.0), rf_drift_fraction(20.0, 19.0), places=9
        )

    def test_zero_initial_value_rejected(self):
        with self.assertRaises(ValueError):
            rf_drift_fraction(0.0, 1.0)


class RouteTests(unittest.TestCase):
    def test_space_qualified_line_buys_as_is(self):
        self.assertEqual(procurement_route("space-qualified-line", True, False),
                         "buy-as-is")

    def test_commercial_line_needs_upscreening(self):
        self.assertEqual(procurement_route("commercial-line", True, True),
                         "buy-with-upscreening")

    def test_commercial_line_without_upscreening_is_refused(self):
        self.assertEqual(procurement_route("commercial-line", True, False), "reject")

    def test_absent_lot_monitor_data_is_refused_on_any_line(self):
        self.assertEqual(procurement_route("space-qualified-line", False, True),
                         "reject")

    def test_unknown_standing_rejected(self):
        with self.assertRaises(ValueError):
            procurement_route("hobby-line", True, True)

    def test_non_boolean_flag_rejected(self):
        with self.assertRaises(ValueError):
            procurement_route("commercial-line", "yes", True)


class AssessmentTests(unittest.TestCase):
    def test_clean_case_buys_as_is(self):
        result = assess_mmic_procurement(clean_spec())
        self.assertEqual(result["disposition"], "buy-as-is")
        self.assertEqual(result["findings"], [])

    def test_commercial_line_is_dispositioned_with_upscreening(self):
        result = assess_mmic_procurement(clean_spec(line_standing="commercial-line"))
        self.assertEqual(result["disposition"], "buy-with-upscreening")
        self.assertEqual(len(result["findings"]), 1)

    def test_hot_channel_rejects(self):
        result = assess_mmic_procurement(clean_spec(thermal_resistance_c_per_w=40.0))
        self.assertEqual(result["disposition"], "reject")
        self.assertFalse(result["thermal"]["within_limit"])

    def test_short_life_rejects(self):
        result = assess_mmic_procurement(clean_spec(required_life_hours=1.0e12))
        self.assertEqual(result["disposition"], "reject")

    def test_monitor_outlier_rejects(self):
        measurements = dict(PCM_GOOD)
        measurements["sheet-resistance-ohm-per-square"] = 240.0
        result = assess_mmic_procurement(clean_spec(pcm_measurements=measurements))
        self.assertEqual(result["disposition"], "reject")
        self.assertEqual(result["pcm"]["out_of_limit"],
                         ("sheet-resistance-ohm-per-square",))

    def test_excess_rf_drift_rejects(self):
        result = assess_mmic_procurement(clean_spec(rf_final=18.0))
        self.assertEqual(result["disposition"], "reject")

    def test_drift_exactly_at_the_allowance_is_accepted(self):
        spec = clean_spec(rf_initial=20.0, rf_final=19.0,
                          allowed_rf_drift_fraction=0.05)
        result = assess_mmic_procurement(spec)
        self.assertAlmostEqual(result["rf_drift_fraction"], 0.05, places=9)
        self.assertEqual(result["disposition"], "buy-as-is")

    def test_channel_temperature_is_reported(self):
        result = assess_mmic_procurement(clean_spec())
        self.assertAlmostEqual(result["thermal"]["channel_temp_c"], 84.0, places=9)

    def test_missing_lot_monitor_data_rejects(self):
        result = assess_mmic_procurement(clean_spec(has_lot_pcm_data=False))
        self.assertEqual(result["disposition"], "reject")
        self.assertEqual(result["route"], "reject")

    def test_missing_key_rejected(self):
        spec = clean_spec()
        del spec["technology"]
        with self.assertRaises(ValueError):
            assess_mmic_procurement(spec)

    def test_non_mapping_spec_rejected(self):
        with self.assertRaises(ValueError):
            assess_mmic_procurement(("technology",))

    def test_life_falls_when_the_base_plate_runs_hotter(self):
        cool = assess_mmic_procurement(clean_spec(base_temperature_c=40.0))
        warm = assess_mmic_procurement(clean_spec(base_temperature_c=70.0))
        self.assertLess(warm["median_life_hours"], cool["median_life_hours"])


if __name__ == "__main__":
    unittest.main()
