"""Contract tests for the paint cure-schedule verification logic."""

import unittest

from q7031_curing_conditions_logic import (
    CURE_TOLERANCE,
    DEFAULT_Q10,
    accumulate_cure,
    assess_cure,
    equivalent_hours,
    longest_dwell_h,
    ramp_rates_c_per_h,
    segment_credit,
    validate_positive,
    validate_profile,
    validate_segment,
)

SCHEDULE = {
    "reference_temperature_c": 25.0,
    "min_temperature_c": 15.0,
    "max_temperature_c": 80.0,
    "q10": 2.0,
}


def spec(**overrides):
    base = {
        "profile": [{"duration_h": 24.0, "temperature_c": 25.0}],
        "reference_temperature_c": 25.0,
        "min_temperature_c": 15.0,
        "max_temperature_c": 80.0,
        "required_equivalent_h": 24.0,
        "q10": 2.0,
    }
    base.update(overrides)
    return base


class SegmentValidationTests(unittest.TestCase):
    def test_segment_returns_normalised_mapping(self):
        seg = validate_segment({"duration_h": 2, "temperature_c": 60})
        self.assertAlmostEqual(seg["duration_h"], 2.0, places=12)
        self.assertAlmostEqual(seg["temperature_c"], 60.0, places=12)
        self.assertIsNone(seg["relative_humidity_pct"])

    def test_missing_duration_rejected(self):
        with self.assertRaises(ValueError):
            validate_segment({"temperature_c": 60.0})

    def test_zero_duration_rejected(self):
        with self.assertRaises(ValueError):
            validate_segment({"duration_h": 0.0, "temperature_c": 60.0})

    def test_boolean_duration_rejected(self):
        with self.assertRaises(ValueError):
            validate_segment({"duration_h": True, "temperature_c": 60.0})

    def test_implausible_temperature_rejected(self):
        with self.assertRaises(ValueError):
            validate_segment({"duration_h": 1.0, "temperature_c": 900.0})

    def test_humidity_out_of_range_rejected(self):
        with self.assertRaises(ValueError):
            validate_segment(
                {"duration_h": 1.0, "temperature_c": 60.0, "relative_humidity_pct": 140.0}
            )

    def test_empty_profile_rejected(self):
        with self.assertRaises(ValueError):
            validate_profile([])

    def test_profile_returns_one_record_per_segment(self):
        profile = validate_profile(
            [{"duration_h": 1.0, "temperature_c": 25.0},
             {"duration_h": 2.0, "temperature_c": 60.0}]
        )
        self.assertEqual(len(profile), 2)

    def test_positive_validator_rejects_text(self):
        with self.assertRaises(ValueError):
            validate_positive("4", "x")


class EquivalentHourTests(unittest.TestCase):
    def test_at_the_reference_an_hour_is_an_hour(self):
        self.assertAlmostEqual(equivalent_hours(4.0, 25.0, 25.0, 2.0), 4.0, places=12)

    def test_ten_kelvin_hotter_doubles_the_credit(self):
        self.assertAlmostEqual(equivalent_hours(4.0, 35.0, 25.0, 2.0), 8.0, places=9)

    def test_twenty_kelvin_hotter_quadruples_the_credit(self):
        self.assertAlmostEqual(equivalent_hours(1.0, 45.0, 25.0, 2.0), 4.0, places=9)

    def test_ten_kelvin_cooler_halves_the_credit(self):
        self.assertAlmostEqual(equivalent_hours(4.0, 15.0, 25.0, 2.0), 2.0, places=9)

    def test_default_factor_is_two(self):
        self.assertAlmostEqual(DEFAULT_Q10, 2.0, places=12)

    def test_unity_factor_rejected(self):
        with self.assertRaises(ValueError):
            equivalent_hours(4.0, 35.0, 25.0, 1.0)

    def test_zero_duration_rejected(self):
        with self.assertRaises(ValueError):
            equivalent_hours(0.0, 35.0, 25.0, 2.0)


class SegmentCreditTests(unittest.TestCase):
    def test_in_window_hold_earns_credit(self):
        record = segment_credit({"duration_h": 4.0, "temperature_c": 35.0}, SCHEDULE)
        self.assertTrue(record["earning"])
        self.assertAlmostEqual(record["credit_h"], 8.0, places=9)

    def test_cold_hold_earns_nothing(self):
        record = segment_credit({"duration_h": 10.0, "temperature_c": 5.0}, SCHEDULE)
        self.assertFalse(record["earning"])
        self.assertAlmostEqual(record["credit_h"], 0.0, places=12)
        self.assertEqual(len(record["findings"]), 1)

    def test_hold_exactly_on_the_minimum_earns_credit(self):
        record = segment_credit({"duration_h": 4.0, "temperature_c": 15.0}, SCHEDULE)
        self.assertTrue(record["earning"])

    def test_hold_exactly_on_the_ceiling_earns_credit(self):
        record = segment_credit({"duration_h": 1.0, "temperature_c": 80.0}, SCHEDULE)
        self.assertTrue(record["earning"])

    def test_overbake_earns_nothing_and_is_a_finding(self):
        record = segment_credit({"duration_h": 1.0, "temperature_c": 120.0}, SCHEDULE)
        self.assertFalse(record["earning"])
        self.assertEqual(len(record["findings"]), 1)

    def test_humidity_window_is_enforced_when_declared(self):
        schedule = dict(SCHEDULE, humidity_band=(40.0, 70.0))
        record = segment_credit(
            {"duration_h": 4.0, "temperature_c": 25.0, "relative_humidity_pct": 20.0},
            schedule,
        )
        self.assertFalse(record["earning"])

    def test_missing_humidity_reading_blocks_credit_when_a_window_exists(self):
        schedule = dict(SCHEDULE, humidity_band=(40.0, 70.0))
        record = segment_credit({"duration_h": 4.0, "temperature_c": 25.0}, schedule)
        self.assertFalse(record["earning"])

    def test_humidity_on_the_band_edge_earns_credit(self):
        schedule = dict(SCHEDULE, humidity_band=(40.0, 70.0))
        record = segment_credit(
            {"duration_h": 4.0, "temperature_c": 25.0, "relative_humidity_pct": 40.0},
            schedule,
        )
        self.assertTrue(record["earning"])

    def test_inverted_temperature_window_rejected(self):
        schedule = dict(SCHEDULE, min_temperature_c=90.0)
        with self.assertRaises(ValueError):
            segment_credit({"duration_h": 1.0, "temperature_c": 60.0}, schedule)

    def test_bad_humidity_band_shape_rejected(self):
        schedule = dict(SCHEDULE, humidity_band=(40.0,))
        with self.assertRaises(ValueError):
            segment_credit({"duration_h": 1.0, "temperature_c": 25.0}, schedule)


class AccumulationTests(unittest.TestCase):
    def test_credits_add_up(self):
        totals = accumulate_cure(
            [{"duration_h": 4.0, "temperature_c": 25.0},
             {"duration_h": 4.0, "temperature_c": 35.0}],
            SCHEDULE,
        )
        self.assertAlmostEqual(totals["total_equivalent_h"], 12.0, places=9)

    def test_elapsed_is_the_wall_clock_sum(self):
        totals = accumulate_cure(
            [{"duration_h": 4.0, "temperature_c": 25.0},
             {"duration_h": 6.0, "temperature_c": 5.0}],
            SCHEDULE,
        )
        self.assertAlmostEqual(totals["elapsed_h"], 10.0, places=12)

    def test_cold_interruption_breaks_the_dwell(self):
        totals = accumulate_cure(
            [{"duration_h": 4.0, "temperature_c": 25.0},
             {"duration_h": 1.0, "temperature_c": 5.0},
             {"duration_h": 3.0, "temperature_c": 25.0}],
            SCHEDULE,
        )
        self.assertAlmostEqual(totals["longest_dwell_h"], 4.0, places=12)

    def test_dwell_of_an_uninterrupted_profile_is_the_whole_run(self):
        totals = accumulate_cure(
            [{"duration_h": 4.0, "temperature_c": 25.0},
             {"duration_h": 3.0, "temperature_c": 30.0}],
            SCHEDULE,
        )
        self.assertAlmostEqual(totals["longest_dwell_h"], 7.0, places=12)

    def test_longest_dwell_needs_a_sequence(self):
        with self.assertRaises(ValueError):
            longest_dwell_h("not-a-sequence")

    def test_ramp_rates_are_reported_between_holds(self):
        rates = ramp_rates_c_per_h(
            [{"duration_h": 2.0, "temperature_c": 25.0},
             {"duration_h": 2.0, "temperature_c": 65.0}]
        )
        self.assertEqual(len(rates), 1)
        self.assertAlmostEqual(rates[0], 20.0, places=9)

    def test_single_hold_has_no_ramp(self):
        self.assertEqual(ramp_rates_c_per_h([{"duration_h": 2.0, "temperature_c": 25.0}]), [])


class AssessCureTests(unittest.TestCase):
    def test_nominal_cure_completes(self):
        result = assess_cure(spec())
        self.assertTrue(result["cure_complete"])
        self.assertEqual(result["findings"], [])

    def test_equivalent_hours_exactly_on_the_requirement_are_met(self):
        result = assess_cure(spec())
        self.assertAlmostEqual(result["total_equivalent_h"], 24.0, places=9)
        self.assertTrue(result["equivalent_hours_met"])

    def test_short_cure_is_caught(self):
        result = assess_cure(spec(profile=[{"duration_h": 6.0, "temperature_c": 25.0}]))
        self.assertFalse(result["equivalent_hours_met"])
        self.assertFalse(result["cure_complete"])

    def test_a_bake_buys_back_the_hours(self):
        result = assess_cure(spec(profile=[{"duration_h": 6.0, "temperature_c": 45.0}]))
        self.assertAlmostEqual(result["total_equivalent_h"], 24.0, places=9)
        self.assertTrue(result["equivalent_hours_met"])

    def test_overbake_is_a_finding_even_when_hours_accumulate(self):
        result = assess_cure(
            spec(
                profile=[{"duration_h": 24.0, "temperature_c": 25.0},
                         {"duration_h": 1.0, "temperature_c": 150.0}]
            )
        )
        self.assertTrue(result["equivalent_hours_met"])
        self.assertFalse(result["cure_complete"])

    def test_dwell_requirement_is_enforced(self):
        result = assess_cure(
            spec(
                profile=[{"duration_h": 12.0, "temperature_c": 25.0},
                         {"duration_h": 1.0, "temperature_c": 5.0},
                         {"duration_h": 12.0, "temperature_c": 25.0}],
                min_dwell_h=20.0,
            )
        )
        self.assertFalse(result["dwell_met"])

    def test_dwell_requirement_met_by_a_continuous_hold(self):
        result = assess_cure(spec(min_dwell_h=20.0))
        self.assertTrue(result["dwell_met"])

    def test_ramp_limit_is_enforced(self):
        result = assess_cure(
            spec(
                profile=[{"duration_h": 1.0, "temperature_c": 20.0},
                         {"duration_h": 1.0, "temperature_c": 70.0},
                         {"duration_h": 24.0, "temperature_c": 25.0}],
                max_ramp_c_per_h=10.0,
            )
        )
        self.assertFalse(result["ramp_within_limit"])

    def test_gentle_ramp_passes_the_limit(self):
        result = assess_cure(
            spec(
                profile=[{"duration_h": 4.0, "temperature_c": 20.0},
                         {"duration_h": 24.0, "temperature_c": 30.0}],
                max_ramp_c_per_h=10.0,
            )
        )
        self.assertTrue(result["ramp_within_limit"])

    def test_missing_spec_key_rejected(self):
        broken = spec()
        del broken["required_equivalent_h"]
        with self.assertRaises(ValueError):
            assess_cure(broken)

    def test_non_mapping_spec_rejected(self):
        with self.assertRaises(ValueError):
            assess_cure([spec()])

    def test_zero_requirement_rejected(self):
        with self.assertRaises(ValueError):
            assess_cure(spec(required_equivalent_h=0.0))

    def test_tolerance_is_small(self):
        self.assertAlmostEqual(CURE_TOLERANCE, 1e-9, places=12)


if __name__ == "__main__":
    unittest.main(verbosity=1)
