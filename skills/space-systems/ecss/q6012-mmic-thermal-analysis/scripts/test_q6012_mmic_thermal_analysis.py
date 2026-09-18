"""Contract tests for the clause 7.2.5 MMIC junction-temperature logic."""

import math
import unittest

from q6012_mmic_thermal_analysis_logic import (
    DEFAULT_SPREAD_ANGLE_DEG,
    DOMINANT_LAYER_SHARE,
    MAX_VOID_FRACTION,
    TEMPERATURE_TOLERANCE_C,
    assess_mmic_thermal,
    derated_limit_c,
    effective_conductivity,
    finger_peak_to_mean_factor,
    junction_temperature_c,
    layer_footprint_um,
    peak_channel_temperature_c,
    spreading_resistance_k_per_w,
    stack_resistance,
    validate_positive,
    validate_void_fraction,
)

# A GaAs die on a gold-tin attach over a copper-molybdenum carrier.
LAYERS = [
    {"name": "gaas-die", "thickness_um": 100.0, "conductivity_w_mk": 46.0},
    {
        "name": "ausn-attach",
        "thickness_um": 25.0,
        "conductivity_w_mk": 57.0,
        "void_fraction": 0.03,
    },
    {"name": "cumo-carrier", "thickness_um": 1000.0, "conductivity_w_mk": 180.0},
]


def base_spec(**overrides):
    spec = {
        "source_width_um": 200.0,
        "source_length_um": 100.0,
        "layers": [dict(layer) for layer in LAYERS],
        "power_w": 1.0,
        "reference_temperature_c": 70.0,
        "limit_temperature_c": 175.0,
        "derating_margin_c": 25.0,
        "finger_count": 8,
        "finger_pitch_um": 40.0,
        "substrate_thickness_um": 100.0,
    }
    spec.update(overrides)
    return spec


class ValidationHelperTests(unittest.TestCase):
    def test_positive_returns_float(self):
        self.assertAlmostEqual(validate_positive("x", 46), 46.0, places=9)

    def test_positive_rejects_zero(self):
        with self.assertRaises(ValueError):
            validate_positive("x", 0.0)

    def test_positive_rejects_boolean(self):
        with self.assertRaises(ValueError):
            validate_positive("x", False)

    def test_void_fraction_accepts_zero(self):
        self.assertAlmostEqual(validate_void_fraction(0.0), 0.0, places=12)

    def test_void_fraction_rejects_unity(self):
        with self.assertRaises(ValueError):
            validate_void_fraction(1.0)

    def test_void_fraction_rejects_negative(self):
        with self.assertRaises(ValueError):
            validate_void_fraction(-0.01)

    def test_voiding_removes_conduction_area(self):
        self.assertAlmostEqual(effective_conductivity(100.0, 0.25), 75.0, places=9)

    def test_unvoided_conductivity_is_unchanged(self):
        self.assertAlmostEqual(effective_conductivity(57.0), 57.0, places=9)


class SpreadingResistanceTests(unittest.TestCase):
    def test_square_source_closed_form(self):
        value = spreading_resistance_k_per_w(200.0, 200.0, 100.0, 46.0)
        growth = 2.0 * 100e-6 * math.tan(math.radians(45.0))
        expected = 100e-6 / (46.0 * 200e-6 * (200e-6 + growth))
        self.assertAlmostEqual(value, expected, places=9)

    def test_rectangle_branch_meets_the_square_branch(self):
        # The two branches are the same integral; near the square limit the log
        # form loses digits to cancellation, so the agreement is graded as a
        # ratio rather than as an absolute difference at magnitude 27.
        square = spreading_resistance_k_per_w(200.0, 200.0, 100.0, 46.0)
        near_square = spreading_resistance_k_per_w(200.0, 200.0001, 100.0, 46.0)
        self.assertAlmostEqual(square / near_square, 1.0, places=5)

    def test_mildly_rectangular_source_is_close_to_the_square(self):
        square = spreading_resistance_k_per_w(200.0, 200.0, 100.0, 46.0)
        oblong = spreading_resistance_k_per_w(200.0, 210.0, 100.0, 46.0)
        self.assertAlmostEqual(square / oblong, 1.0, places=1)

    def test_orientation_does_not_change_the_resistance(self):
        wide = spreading_resistance_k_per_w(200.0, 100.0, 100.0, 46.0)
        tall = spreading_resistance_k_per_w(100.0, 200.0, 100.0, 46.0)
        self.assertAlmostEqual(wide, tall, places=12)

    def test_resistance_is_positive_for_a_rectangle(self):
        self.assertGreater(spreading_resistance_k_per_w(200.0, 100.0, 100.0, 46.0), 0.0)

    def test_zero_spread_angle_is_the_plain_prism(self):
        value = spreading_resistance_k_per_w(200.0, 100.0, 100.0, 46.0, 0.0)
        expected = 100e-6 / (46.0 * 200e-6 * 100e-6)
        self.assertAlmostEqual(value, expected, places=9)

    def test_spreading_lowers_the_resistance(self):
        no_spread = spreading_resistance_k_per_w(200.0, 100.0, 100.0, 46.0, 0.0)
        spread = spreading_resistance_k_per_w(200.0, 100.0, 100.0, 46.0, 45.0)
        self.assertLess(spread, no_spread)

    def test_better_conductor_lowers_the_resistance(self):
        poor = spreading_resistance_k_per_w(200.0, 100.0, 100.0, 46.0)
        good = spreading_resistance_k_per_w(200.0, 100.0, 100.0, 460.0)
        self.assertAlmostEqual(poor / good, 10.0, places=9)

    def test_spread_angle_of_ninety_rejected(self):
        with self.assertRaises(ValueError):
            spreading_resistance_k_per_w(200.0, 100.0, 100.0, 46.0, 90.0)

    def test_negative_spread_angle_rejected(self):
        with self.assertRaises(ValueError):
            spreading_resistance_k_per_w(200.0, 100.0, 100.0, 46.0, -10.0)

    def test_zero_thickness_rejected(self):
        with self.assertRaises(ValueError):
            spreading_resistance_k_per_w(200.0, 100.0, 0.0, 46.0)

    def test_default_spread_angle_is_the_named_constant(self):
        self.assertAlmostEqual(DEFAULT_SPREAD_ANGLE_DEG, 45.0, places=9)


class FootprintTests(unittest.TestCase):
    def test_footprint_grows_by_twice_the_thickness_at_forty_five_degrees(self):
        width, length = layer_footprint_um(200.0, 100.0, 100.0, 45.0)
        self.assertAlmostEqual(width, 400.0, places=6)
        self.assertAlmostEqual(length, 300.0, places=6)

    def test_zero_angle_leaves_the_footprint_alone(self):
        width, length = layer_footprint_um(200.0, 100.0, 100.0, 0.0)
        self.assertAlmostEqual(width, 200.0, places=9)
        self.assertAlmostEqual(length, 100.0, places=9)

    def test_non_numeric_angle_rejected(self):
        with self.assertRaises(ValueError):
            layer_footprint_um(200.0, 100.0, 100.0, "45")


class StackResistanceTests(unittest.TestCase):
    def test_total_is_the_sum_of_the_layers(self):
        stack = stack_resistance(200.0, 100.0, [dict(x) for x in LAYERS])
        self.assertAlmostEqual(
            stack["total_resistance_k_per_w"],
            sum(r["resistance_k_per_w"] for r in stack["layers"]),
            places=9,
        )

    def test_shares_sum_to_one(self):
        stack = stack_resistance(200.0, 100.0, [dict(x) for x in LAYERS])
        self.assertAlmostEqual(sum(r["share_of_total"] for r in stack["layers"]), 1.0, places=9)

    def test_footprint_grows_down_the_stack(self):
        stack = stack_resistance(200.0, 100.0, [dict(x) for x in LAYERS])
        widths = [r["entry_width_um"] for r in stack["layers"]]
        self.assertEqual(widths, sorted(widths))

    def test_exit_footprint_exceeds_the_source(self):
        stack = stack_resistance(200.0, 100.0, [dict(x) for x in LAYERS])
        self.assertGreater(stack["exit_width_um"], 200.0)

    def test_voided_attach_raises_that_layer_resistance(self):
        clean = [dict(x) for x in LAYERS]
        clean[1]["void_fraction"] = 0.0
        voided = [dict(x) for x in LAYERS]
        voided[1]["void_fraction"] = 0.30
        clean_stack = stack_resistance(200.0, 100.0, clean)
        void_stack = stack_resistance(200.0, 100.0, voided)
        self.assertGreater(
            void_stack["layers"][1]["resistance_k_per_w"],
            clean_stack["layers"][1]["resistance_k_per_w"],
        )

    def test_duplicate_layer_name_rejected(self):
        layers = [dict(x) for x in LAYERS]
        layers[1]["name"] = "gaas-die"
        with self.assertRaises(ValueError):
            stack_resistance(200.0, 100.0, layers)

    def test_empty_stack_rejected(self):
        with self.assertRaises(ValueError):
            stack_resistance(200.0, 100.0, [])

    def test_unnamed_layer_rejected(self):
        layers = [dict(x) for x in LAYERS]
        del layers[0]["name"]
        with self.assertRaises(ValueError):
            stack_resistance(200.0, 100.0, layers)

    def test_non_mapping_layer_rejected(self):
        with self.assertRaises(ValueError):
            stack_resistance(200.0, 100.0, ["gaas-die"])

    def test_missing_conductivity_rejected(self):
        layers = [dict(x) for x in LAYERS]
        del layers[2]["conductivity_w_mk"]
        with self.assertRaises(ValueError):
            stack_resistance(200.0, 100.0, layers)


class TemperatureTests(unittest.TestCase):
    def test_junction_rise_is_power_times_resistance(self):
        self.assertAlmostEqual(junction_temperature_c(70.0, 2.0, 50.0), 170.0, places=9)

    def test_reference_below_absolute_zero_rejected(self):
        with self.assertRaises(ValueError):
            junction_temperature_c(-300.0, 2.0, 50.0)

    def test_non_numeric_reference_rejected(self):
        with self.assertRaises(ValueError):
            junction_temperature_c("70", 2.0, 50.0)

    def test_zero_power_rejected(self):
        with self.assertRaises(ValueError):
            junction_temperature_c(70.0, 0.0, 50.0)

    def test_unity_factor_leaves_the_mean_untouched(self):
        self.assertAlmostEqual(
            peak_channel_temperature_c(70.0, 2.0, 50.0, 1.0), 170.0, places=9
        )

    def test_factor_scales_only_the_rise(self):
        self.assertAlmostEqual(
            peak_channel_temperature_c(70.0, 2.0, 50.0, 1.5), 70.0 + 150.0, places=9
        )

    def test_cooling_factor_rejected(self):
        with self.assertRaises(ValueError):
            peak_channel_temperature_c(70.0, 2.0, 50.0, 0.9)

    def test_derated_limit_subtracts_the_margin(self):
        self.assertAlmostEqual(derated_limit_c(175.0, 25.0), 150.0, places=9)

    def test_zero_derating_leaves_the_limit(self):
        self.assertAlmostEqual(derated_limit_c(175.0, 0.0), 175.0, places=9)

    def test_negative_derating_rejected(self):
        with self.assertRaises(ValueError):
            derated_limit_c(175.0, -5.0)


class FingerFactorTests(unittest.TestCase):
    def test_single_finger_is_uniform(self):
        self.assertAlmostEqual(finger_peak_to_mean_factor(1, 40.0, 100.0), 1.0, places=12)

    def test_symmetric_pair_is_uniform(self):
        self.assertAlmostEqual(finger_peak_to_mean_factor(2, 40.0, 100.0), 1.0, places=12)

    def test_three_fingers_are_not_uniform(self):
        self.assertGreater(finger_peak_to_mean_factor(3, 40.0, 100.0), 1.0)

    def test_more_fingers_raise_the_non_uniformity(self):
        few = finger_peak_to_mean_factor(3, 40.0, 100.0)
        many = finger_peak_to_mean_factor(8, 40.0, 100.0)
        self.assertGreater(many, few)

    def test_far_apart_fingers_are_uniform_again(self):
        self.assertAlmostEqual(
            finger_peak_to_mean_factor(8, 1.0e7, 100.0), 1.0, places=5
        )

    def test_zero_fingers_rejected(self):
        with self.assertRaises(ValueError):
            finger_peak_to_mean_factor(0, 40.0, 100.0)

    def test_non_integer_finger_count_rejected(self):
        with self.assertRaises(ValueError):
            finger_peak_to_mean_factor(8.5, 40.0, 100.0)

    def test_zero_pitch_rejected(self):
        with self.assertRaises(ValueError):
            finger_peak_to_mean_factor(8, 0.0, 100.0)


class AssessMmicThermalTests(unittest.TestCase):
    def test_nominal_stack_is_compliant(self):
        result = assess_mmic_thermal(base_spec())
        self.assertTrue(result["compliant"], result["findings"])

    def test_peak_exceeds_the_mean(self):
        result = assess_mmic_thermal(base_spec())
        self.assertGreater(
            result["peak_channel_temperature_c"], result["mean_junction_temperature_c"]
        )

    def test_single_finger_peak_equals_the_mean(self):
        result = assess_mmic_thermal(base_spec(finger_count=1))
        self.assertAlmostEqual(
            result["peak_channel_temperature_c"],
            result["mean_junction_temperature_c"],
            places=9,
        )

    def test_margin_is_limit_minus_peak(self):
        result = assess_mmic_thermal(base_spec())
        self.assertAlmostEqual(
            result["margin_c"],
            result["derated_limit_c"] - result["peak_channel_temperature_c"],
            places=9,
        )

    def test_derated_limit_is_reported(self):
        result = assess_mmic_thermal(base_spec())
        self.assertAlmostEqual(result["derated_limit_c"], 150.0, places=9)

    def test_dominant_layer_is_the_die(self):
        result = assess_mmic_thermal(base_spec())
        self.assertEqual(result["dominant_layer"], "gaas-die")

    def test_excess_power_breaches_the_limit(self):
        result = assess_mmic_thermal(base_spec(power_w=4.0))
        self.assertFalse(result["compliant"])
        self.assertTrue(any("exceeds the derated limit" in f for f in result["findings"]))

    def test_excess_voiding_is_a_finding(self):
        layers = [dict(x) for x in LAYERS]
        layers[1]["void_fraction"] = 0.25
        result = assess_mmic_thermal(base_spec(layers=layers))
        self.assertTrue(any("void fraction" in f for f in result["findings"]))

    def test_void_limit_is_the_named_constant(self):
        self.assertAlmostEqual(MAX_VOID_FRACTION, 0.10, places=12)

    def test_dominant_share_threshold_is_the_named_constant(self):
        self.assertAlmostEqual(DOMINANT_LAYER_SHARE, 0.60, places=12)

    def test_tolerance_is_a_named_constant(self):
        self.assertAlmostEqual(TEMPERATURE_TOLERANCE_C, 1e-9, places=15)

    def test_hotter_baseplate_raises_the_junction(self):
        cool = assess_mmic_thermal(base_spec(reference_temperature_c=20.0))
        warm = assess_mmic_thermal(base_spec(reference_temperature_c=70.0))
        self.assertAlmostEqual(
            warm["mean_junction_temperature_c"] - cool["mean_junction_temperature_c"],
            50.0,
            places=9,
        )

    def test_rise_is_linear_in_power(self):
        low = assess_mmic_thermal(base_spec(power_w=1.0))
        high = assess_mmic_thermal(base_spec(power_w=2.0))
        low_rise = low["mean_junction_temperature_c"] - 70.0
        high_rise = high["mean_junction_temperature_c"] - 70.0
        self.assertAlmostEqual(high_rise / low_rise, 2.0, places=9)

    def test_missing_key_rejected(self):
        spec = base_spec()
        del spec["power_w"]
        with self.assertRaises(ValueError):
            assess_mmic_thermal(spec)

    def test_non_mapping_spec_rejected(self):
        with self.assertRaises(ValueError):
            assess_mmic_thermal(["layers"])

    def test_multi_finger_without_pitch_rejected(self):
        spec = base_spec()
        del spec["finger_pitch_um"]
        with self.assertRaises(ValueError):
            assess_mmic_thermal(spec)

    def test_layer_records_are_returned_in_stack_order(self):
        result = assess_mmic_thermal(base_spec())
        self.assertEqual(
            [r["name"] for r in result["layers"]],
            ["gaas-die", "ausn-attach", "cumo-carrier"],
        )

    def test_exactly_at_the_limit_stays_compliant(self):
        probe = assess_mmic_thermal(base_spec())
        peak = probe["peak_channel_temperature_c"]
        result = assess_mmic_thermal(
            base_spec(limit_temperature_c=peak + 25.0, derating_margin_c=25.0)
        )
        self.assertTrue(result["compliant"])


if __name__ == "__main__":
    unittest.main()
