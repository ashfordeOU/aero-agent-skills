"""Contract tests for the clause 5.4.4.2.1 maximum-bus enable range logic."""

import unittest

from e2020_enable_threshold_maximum_bus_range_logic import (
    CLAUSE_REFERENCE,
    REFERENCE_NAMES,
    SPAN_TOLERANCE_V,
    assess_maximum_referenced_range,
    ladder_span_v,
    normalise_reference,
    percent_of_maximum_to_volts,
    percent_of_nominal_to_volts,
    reference_shift_v,
    restate_on_maximum_pct,
    setting_volts,
    usable_settings_v,
    validate_bus_pair,
    validate_percent,
    validate_voltage,
)

# A bus whose nominal value is 28 V and whose maximum value is 32 V. The turn
# on threshold can be set to 55, 60, 65, 70 or 75 percent of the maximum, so
# the ladder commands 17.6 V through 24.0 V, and the crossable window runs
# from the 18.0 V equipment turn on floor to the 24.0 V lowest steady bus.
BASE = {
    "nominal_v": 28.0,
    "maximum_v": 32.0,
    "settings_pct": [55.0, 60.0, 65.0, 70.0, 75.0],
    "floor_v": 18.0,
    "lowest_steady_v": 24.0,
}


def spec(**overrides):
    merged = dict(BASE)
    merged.update(overrides)
    return merged


class ReferenceTests(unittest.TestCase):
    def test_clause_reference_is_the_maximum_bus(self):
        self.assertEqual(CLAUSE_REFERENCE, "maximum-bus")

    def test_alias_and_case_are_folded(self):
        self.assertEqual(normalise_reference("  Vmax "), "maximum-bus")
        self.assertEqual(normalise_reference("NOMINAL-BUS"), "nominal-main-bus")

    def test_absent_reference_is_unstated(self):
        self.assertEqual(normalise_reference(None), "unstated")
        self.assertEqual(normalise_reference("  "), "unstated")

    def test_unknown_reference_rejected(self):
        with self.assertRaises(ValueError):
            normalise_reference("battery-end-of-discharge")

    def test_non_string_reference_rejected(self):
        with self.assertRaises(ValueError):
            normalise_reference(32.0)

    def test_every_reference_name_is_reachable(self):
        for name in REFERENCE_NAMES:
            self.assertEqual(normalise_reference(name), name)


class ValidationTests(unittest.TestCase):
    def test_voltage_returned_as_float(self):
        self.assertEqual(validate_voltage(32, "maximum_v"), 32.0)

    def test_zero_voltage_rejected(self):
        with self.assertRaises(ValueError):
            validate_voltage(0.0, "maximum_v")

    def test_boolean_voltage_rejected(self):
        with self.assertRaises(ValueError):
            validate_voltage(True, "maximum_v")

    def test_percent_returned_as_float(self):
        self.assertAlmostEqual(validate_percent(70, "percent"), 70.0, places=9)

    def test_non_positive_percentage_rejected(self):
        with self.assertRaises(ValueError):
            validate_percent(0.0, "percent")
        with self.assertRaises(ValueError):
            validate_percent(-5.0, "percent")

    def test_absurd_percentage_rejected(self):
        with self.assertRaises(ValueError):
            validate_percent(600.0, "percent")

    def test_bus_pair_returned_in_order(self):
        self.assertEqual(validate_bus_pair(28.0, 32.0), (28.0, 32.0))

    def test_maximum_below_nominal_rejected(self):
        with self.assertRaises(ValueError):
            validate_bus_pair(32.0, 28.0)

    def test_equal_nominal_and_maximum_accepted(self):
        self.assertEqual(validate_bus_pair(28.0, 28.0), (28.0, 28.0))


class ReferralTests(unittest.TestCase):
    def test_maximum_referenced_setting_in_volts(self):
        self.assertAlmostEqual(percent_of_maximum_to_volts(70.0, 32.0), 22.4, places=9)

    def test_nominal_referenced_setting_in_volts(self):
        self.assertAlmostEqual(percent_of_nominal_to_volts(70.0, 28.0), 19.6, places=9)

    def test_setting_volts_follows_the_stated_reference(self):
        self.assertAlmostEqual(
            setting_volts(70.0, "maximum-bus", 28.0, 32.0), 22.4, places=9
        )
        self.assertAlmostEqual(
            setting_volts(70.0, "nominal-main-bus", 28.0, 32.0), 19.6, places=9
        )

    def test_unstated_reference_is_read_against_the_maximum_bus(self):
        self.assertAlmostEqual(
            setting_volts(70.0, None, 28.0, 32.0), 22.4, places=9
        )


class RestatementTests(unittest.TestCase):
    def test_maximum_referenced_setting_restates_to_itself(self):
        self.assertAlmostEqual(
            restate_on_maximum_pct(70.0, "maximum-bus", 28.0, 32.0), 70.0, places=9
        )

    def test_nominal_referenced_setting_restates_by_the_bus_ratio(self):
        self.assertAlmostEqual(
            restate_on_maximum_pct(70.0, "nominal-main-bus", 28.0, 32.0),
            61.25,
            places=9,
        )

    def test_restatement_commands_the_same_volts(self):
        original = setting_volts(70.0, "nominal-main-bus", 28.0, 32.0)
        restated = restate_on_maximum_pct(70.0, "nominal-main-bus", 28.0, 32.0)
        self.assertAlmostEqual(
            percent_of_maximum_to_volts(restated, 32.0), original, places=9
        )

    def test_reference_shift_is_the_volts_the_number_moves_by(self):
        self.assertAlmostEqual(reference_shift_v(70.0, 28.0, 32.0), 2.8, places=9)

    def test_no_shift_when_the_two_bus_values_agree(self):
        self.assertAlmostEqual(reference_shift_v(70.0, 28.0, 28.0), 0.0, places=9)


class LadderTests(unittest.TestCase):
    def test_span_is_highest_minus_lowest(self):
        self.assertAlmostEqual(ladder_span_v([17.6, 19.2, 24.0]), 6.4, places=9)

    def test_empty_ladder_rejected(self):
        with self.assertRaises(ValueError):
            ladder_span_v([])

    def test_settings_outside_the_window_are_dropped(self):
        usable = usable_settings_v([17.6, 19.2, 20.8, 22.4, 24.0], 18.0, 24.0)
        self.assertEqual(len(usable), 4)
        self.assertAlmostEqual(usable[0], 19.2, places=9)

    def test_setting_exactly_on_a_window_bound_is_kept(self):
        self.assertEqual(len(usable_settings_v([18.0, 24.0], 18.0, 24.0)), 2)

    def test_empty_window_rejected(self):
        with self.assertRaises(ValueError):
            usable_settings_v([20.0, 21.0], 24.0, 18.0)

    def test_window_above_the_whole_ladder_leaves_nothing(self):
        self.assertEqual(usable_settings_v([17.6, 19.2], 26.0, 30.0), [])


class AssessmentTests(unittest.TestCase):
    def test_maximum_referenced_ladder_is_compliant(self):
        result = assess_maximum_referenced_range(spec())
        self.assertEqual(result["verdict"], "compliant")
        self.assertEqual(result["findings"], [])
        self.assertEqual(result["reference"], "maximum-bus")

    def test_ladder_is_reported_in_volts_and_restated_percent(self):
        result = assess_maximum_referenced_range(spec())
        self.assertAlmostEqual(result["settings_v"][0], 17.6, places=9)
        self.assertAlmostEqual(result["settings_v"][-1], 24.0, places=9)
        self.assertAlmostEqual(result["settings_pct_of_maximum"][-1], 75.0, places=9)

    def test_span_and_usable_count_are_reported(self):
        result = assess_maximum_referenced_range(spec())
        self.assertAlmostEqual(result["ladder_span_v"], 6.4, places=9)
        self.assertEqual(result["usable_setting_count"], 4)

    def test_nominal_referenced_ladder_is_a_finding_and_is_restated(self):
        result = assess_maximum_referenced_range(spec(reference="nominal-main-bus"))
        self.assertEqual(result["verdict"], "non-compliant")
        self.assertTrue(any("nominal bus" in f for f in result["findings"]))
        self.assertAlmostEqual(
            result["settings_pct_of_maximum"][3], 61.25, places=9
        )

    def test_unstated_reference_reports_the_working_assumption(self):
        result = assess_maximum_referenced_range(spec(reference=None))
        self.assertEqual(result["reference"], "unstated")
        self.assertTrue(any("working assumption" in f for f in result["findings"]))

    def test_setting_above_the_maximum_bus_is_unreachable(self):
        result = assess_maximum_referenced_range(
            spec(settings_pct=[70.0, 105.0], lowest_steady_v=30.0)
        )
        self.assertEqual(result["verdict"], "non-compliant")
        self.assertTrue(any("never reaches" in f for f in result["findings"]))

    def test_span_exactly_on_the_requirement_is_accepted(self):
        result = assess_maximum_referenced_range(spec(required_span_v=6.4))
        self.assertEqual(result["verdict"], "compliant")

    def test_span_short_of_the_requirement_fails(self):
        result = assess_maximum_referenced_range(spec(required_span_v=8.0))
        self.assertEqual(result["verdict"], "non-compliant")
        self.assertTrue(any("short of" in f for f in result["findings"]))

    def test_ladder_entirely_outside_the_window_fails(self):
        result = assess_maximum_referenced_range(
            spec(floor_v=26.0, lowest_steady_v=28.0)
        )
        self.assertEqual(result["usable_setting_count"], 0)
        self.assertTrue(any("no setting lands" in f for f in result["findings"]))

    def test_reference_shift_is_reported_per_setting(self):
        result = assess_maximum_referenced_range(spec())
        self.assertEqual(len(result["reference_shift_v"]), 5)
        self.assertAlmostEqual(result["reference_shift_v"][3], 2.8, places=9)

    def test_single_setting_is_not_an_adjustable_threshold(self):
        with self.assertRaises(ValueError):
            assess_maximum_referenced_range(spec(settings_pct=[70.0]))

    def test_missing_key_rejected(self):
        broken = spec()
        del broken["maximum_v"]
        with self.assertRaises(ValueError):
            assess_maximum_referenced_range(broken)

    def test_non_mapping_spec_rejected(self):
        with self.assertRaises(ValueError):
            assess_maximum_referenced_range([28.0, 32.0])

    def test_maximum_below_nominal_rejected_by_the_assessment(self):
        with self.assertRaises(ValueError):
            assess_maximum_referenced_range(spec(maximum_v=20.0))

    def test_span_tolerance_is_representation_sized(self):
        self.assertLess(SPAN_TOLERANCE_V, 1e-6)


if __name__ == "__main__":
    unittest.main()
