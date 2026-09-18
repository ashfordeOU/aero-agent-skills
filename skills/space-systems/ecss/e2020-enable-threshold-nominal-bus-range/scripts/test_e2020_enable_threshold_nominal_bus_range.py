"""Contract tests for the clause 5.4.4.1.1 enable threshold range logic."""

import unittest

from e2020_enable_threshold_nominal_bus_range_logic import (
    COVERAGE_TOLERANCE_PCT,
    REFERENCE_NAMES,
    assess_enable_threshold_range,
    band_coverage,
    ladder_settings_pct,
    ladder_span_pct,
    ladder_volts,
    normalise_reference,
    percent_to_volts,
    step_resolution_v,
    usable_settings_pct,
    validate_percent,
    validate_voltage,
)

# A 28 V nominal main bus. The turn on threshold is adjustable from 60 to 90
# percent in 2.5 percent steps, so the ladder holds 13 settings, one step
# moves the threshold 0.7 V, and the crossable window runs from the 18.0 V
# equipment floor to the 24.0 V lowest steady state bus.
BASE = {
    "nominal_v": 28.0,
    "lowest_pct": 60.0,
    "step_pct": 2.5,
    "setting_count": 13,
    "required_low_pct": 62.0,
    "required_high_pct": 88.0,
    "floor_v": 18.0,
    "lowest_steady_v": 24.0,
}


def spec(**overrides):
    merged = dict(BASE)
    merged.update(overrides)
    return merged


class ReferenceTests(unittest.TestCase):
    def test_canonical_reference_passes_through(self):
        self.assertEqual(normalise_reference("nominal-main-bus"), "nominal-main-bus")

    def test_alias_and_case_are_folded(self):
        self.assertEqual(normalise_reference("  Vnom "), "nominal-main-bus")
        self.assertEqual(normalise_reference("MAX-BUS"), "maximum-bus")

    def test_absent_reference_is_unstated(self):
        self.assertEqual(normalise_reference(None), "unstated")
        self.assertEqual(normalise_reference("   "), "unstated")

    def test_unknown_reference_rejected(self):
        with self.assertRaises(ValueError):
            normalise_reference("battery-end-of-charge")

    def test_non_string_reference_rejected(self):
        with self.assertRaises(ValueError):
            normalise_reference(28.0)

    def test_every_reference_name_is_reachable(self):
        for name in REFERENCE_NAMES:
            self.assertEqual(normalise_reference(name), name)


class ValidationTests(unittest.TestCase):
    def test_voltage_returned_as_float(self):
        self.assertEqual(validate_voltage(28, "nominal_v"), 28.0)

    def test_zero_voltage_rejected_unless_allowed(self):
        with self.assertRaises(ValueError):
            validate_voltage(0.0, "nominal_v")

    def test_boolean_voltage_rejected(self):
        with self.assertRaises(ValueError):
            validate_voltage(True, "nominal_v")

    def test_percent_returned_as_float(self):
        self.assertAlmostEqual(validate_percent(60, "lowest_pct"), 60.0, places=9)

    def test_fraction_style_percentage_rejected(self):
        with self.assertRaises(ValueError):
            validate_percent(0.0, "lowest_pct")

    def test_absurd_percentage_rejected(self):
        with self.assertRaises(ValueError):
            validate_percent(600.0, "lowest_pct")


class LadderTests(unittest.TestCase):
    def test_ladder_holds_every_setting(self):
        settings = ladder_settings_pct(60.0, 2.5, 13)
        self.assertEqual(len(settings), 13)
        self.assertAlmostEqual(settings[0], 60.0, places=9)
        self.assertAlmostEqual(settings[-1], 90.0, places=9)

    def test_top_setting_is_exact_not_accumulated(self):
        settings = ladder_settings_pct(60.0, 0.1, 101)
        self.assertAlmostEqual(settings[-1], 70.0, places=9)

    def test_single_setting_is_not_an_adjustable_threshold(self):
        with self.assertRaises(ValueError):
            ladder_settings_pct(60.0, 2.5, 1)

    def test_non_integer_setting_count_rejected(self):
        with self.assertRaises(ValueError):
            ladder_settings_pct(60.0, 2.5, 13.0)

    def test_zero_step_rejected(self):
        with self.assertRaises(ValueError):
            ladder_settings_pct(60.0, 0.0, 13)

    def test_span_is_the_lowest_and_highest_setting(self):
        low, high = ladder_span_pct(ladder_settings_pct(60.0, 2.5, 13))
        self.assertAlmostEqual(low, 60.0, places=9)
        self.assertAlmostEqual(high, 90.0, places=9)

    def test_empty_ladder_rejected(self):
        with self.assertRaises(ValueError):
            ladder_span_pct([])


class ReferralTests(unittest.TestCase):
    def test_percentage_is_referred_through_the_nominal_bus(self):
        self.assertAlmostEqual(percent_to_volts(70.0, 28.0), 19.6, places=9)

    def test_same_percentage_on_a_higher_bus_is_more_volts(self):
        self.assertAlmostEqual(percent_to_volts(70.0, 100.0), 70.0, places=9)

    def test_every_setting_is_referred(self):
        volts = ladder_volts([60.0, 75.0, 90.0], 28.0)
        self.assertEqual(len(volts), 3)
        self.assertAlmostEqual(volts[1], 21.0, places=9)

    def test_one_step_buys_the_step_percentage_in_volts(self):
        self.assertAlmostEqual(step_resolution_v(2.5, 28.0), 0.7, places=9)


class CoverageTests(unittest.TestCase):
    def test_band_inside_the_ladder_is_covered(self):
        result = band_coverage(ladder_settings_pct(60.0, 2.5, 13), 62.0, 88.0)
        self.assertTrue(result["covers_low"])
        self.assertTrue(result["covers_high"])

    def test_band_landing_exactly_on_both_ends_is_covered(self):
        result = band_coverage(ladder_settings_pct(60.0, 2.5, 13), 60.0, 90.0)
        self.assertTrue(result["covers_low"])
        self.assertTrue(result["covers_high"])

    def test_low_end_shortfall_is_reported_on_its_own(self):
        result = band_coverage(ladder_settings_pct(60.0, 2.5, 13), 55.0, 88.0)
        self.assertFalse(result["covers_low"])
        self.assertTrue(result["covers_high"])
        self.assertAlmostEqual(result["low_shortfall_pct"], 5.0, places=9)

    def test_high_end_shortfall_is_reported_on_its_own(self):
        result = band_coverage(ladder_settings_pct(60.0, 2.5, 13), 62.0, 95.0)
        self.assertTrue(result["covers_low"])
        self.assertFalse(result["covers_high"])
        self.assertAlmostEqual(result["high_shortfall_pct"], 5.0, places=9)

    def test_inverted_required_band_rejected(self):
        with self.assertRaises(ValueError):
            band_coverage(ladder_settings_pct(60.0, 2.5, 13), 88.0, 62.0)


class WindowTests(unittest.TestCase):
    def test_settings_outside_the_window_are_dropped(self):
        usable = usable_settings_pct(
            ladder_settings_pct(60.0, 2.5, 13), 28.0, 18.0, 24.0
        )
        self.assertEqual(len(usable), 9)
        self.assertAlmostEqual(usable[0], 65.0, places=9)
        self.assertAlmostEqual(usable[-1], 85.0, places=9)

    def test_setting_exactly_on_a_window_bound_is_kept(self):
        usable = usable_settings_pct([75.0], 28.0, 21.0, 21.0)
        self.assertEqual(len(usable), 1)

    def test_empty_window_rejected(self):
        with self.assertRaises(ValueError):
            usable_settings_pct([75.0], 28.0, 24.0, 18.0)

    def test_window_above_the_whole_ladder_leaves_nothing(self):
        usable = usable_settings_pct(
            ladder_settings_pct(60.0, 2.5, 13), 28.0, 26.0, 27.0
        )
        self.assertEqual(usable, [])


class AssessmentTests(unittest.TestCase):
    def test_covering_ladder_is_compliant(self):
        result = assess_enable_threshold_range(spec())
        self.assertEqual(result["verdict"], "compliant")
        self.assertEqual(result["findings"], [])
        self.assertTrue(result["covers_required_band"])

    def test_resolution_and_usable_count_are_reported(self):
        result = assess_enable_threshold_range(spec())
        self.assertAlmostEqual(result["step_resolution_v"], 0.7, places=9)
        self.assertEqual(result["usable_setting_count"], 9)

    def test_ladder_short_at_the_low_end_fails(self):
        result = assess_enable_threshold_range(spec(required_low_pct=55.0))
        self.assertEqual(result["verdict"], "non-compliant")
        self.assertTrue(any("cannot be set below" in f for f in result["findings"]))

    def test_ladder_short_at_the_high_end_fails(self):
        result = assess_enable_threshold_range(spec(required_high_pct=95.0))
        self.assertEqual(result["verdict"], "non-compliant")
        self.assertTrue(any("stops at" in f for f in result["findings"]))

    def test_maximum_bus_reference_is_a_finding(self):
        result = assess_enable_threshold_range(spec(reference="maximum-bus"))
        self.assertEqual(result["reference"], "maximum-bus")
        self.assertEqual(result["verdict"], "non-compliant")
        self.assertTrue(any("nominal main bus" in f for f in result["findings"]))

    def test_unstated_reference_is_a_finding(self):
        result = assess_enable_threshold_range(spec(reference=None))
        self.assertEqual(result["reference"], "unstated")
        self.assertEqual(result["verdict"], "non-compliant")

    def test_step_exactly_on_the_allowed_maximum_passes(self):
        result = assess_enable_threshold_range(spec(max_step_v=0.7))
        self.assertEqual(result["verdict"], "compliant")

    def test_step_coarser_than_allowed_fails(self):
        result = assess_enable_threshold_range(spec(max_step_v=0.5))
        self.assertEqual(result["verdict"], "non-compliant")
        self.assertTrue(any("coarser than" in f for f in result["findings"]))

    def test_ladder_entirely_outside_the_window_fails(self):
        result = assess_enable_threshold_range(spec(floor_v=26.0, lowest_steady_v=27.0))
        self.assertEqual(result["usable_setting_count"], 0)
        self.assertTrue(any("no ladder setting" in f for f in result["findings"]))

    def test_settings_are_returned_in_percent_and_volts(self):
        result = assess_enable_threshold_range(spec())
        self.assertEqual(len(result["settings_pct"]), 13)
        self.assertEqual(len(result["settings_v"]), 13)
        self.assertAlmostEqual(result["settings_v"][0], 16.8, places=9)

    def test_missing_key_rejected(self):
        broken = spec()
        del broken["step_pct"]
        with self.assertRaises(ValueError):
            assess_enable_threshold_range(broken)

    def test_non_mapping_spec_rejected(self):
        with self.assertRaises(ValueError):
            assess_enable_threshold_range([28.0, 60.0])

    def test_coverage_tolerance_is_representation_sized(self):
        self.assertLess(COVERAGE_TOLERANCE_PCT, 1e-6)


if __name__ == "__main__":
    unittest.main()
