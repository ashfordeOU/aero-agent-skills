"""Contract tests for the clause 5.6.14.7 ranging and Doppler tracking logic."""

import unittest

from e50_ranging_and_doppler_tracking_logic import (
    DOPPLER_OUT_OF_BAND,
    RANGE_AMBIGUOUS,
    SPEED_OF_LIGHT_M_PER_S,
    TRACKABLE,
    ambiguity_number,
    ambiguity_resolvable,
    assess_tracking,
    range_from_round_trip,
    range_rate_from_doppler,
    range_resolution_m,
    required_tracking_bandwidth_hz,
    resolve_range,
    round_trip_from_range,
    two_way_doppler_hz,
    unambiguous_range_m,
    validate_distance,
    validate_frequency,
    validate_time,
    validate_turnaround_ratio,
    within_tracking_bandwidth,
)

CODE_PERIOD = 1.0
INTERVAL = 149896229.0
UPLINK = 1.0e9
TURNAROUND = 2.0
CLOSING_RATE = -1000.0
CLOSING_DOPPLER = 13342.563807926083
NEEDED_BANDWIDTH = 26685.127615852165
CHIP_RATE = 1.0e6


class ValidationTests(unittest.TestCase):
    def test_positive_time_accepted(self):
        self.assertAlmostEqual(validate_time(2.0), 2.0, places=9)

    def test_zero_time_rejected(self):
        with self.assertRaises(ValueError):
            validate_time(0.0)

    def test_negative_time_rejected(self):
        with self.assertRaises(ValueError):
            validate_time(-2.0)

    def test_boolean_frequency_rejected(self):
        with self.assertRaises(ValueError):
            validate_frequency(True)

    def test_text_frequency_rejected(self):
        with self.assertRaises(ValueError):
            validate_frequency("1e9")

    def test_infinite_frequency_rejected(self):
        with self.assertRaises(ValueError):
            validate_frequency(float("inf"))

    def test_zero_distance_accepted(self):
        self.assertAlmostEqual(validate_distance(0), 0.0, places=9)

    def test_negative_distance_rejected(self):
        with self.assertRaises(ValueError):
            validate_distance(-1.0)

    def test_zero_turnaround_ratio_rejected(self):
        with self.assertRaises(ValueError):
            validate_turnaround_ratio(0.0)


class RangeGeometryTests(unittest.TestCase):
    def test_range_is_half_the_round_trip(self):
        self.assertAlmostEqual(range_from_round_trip(2.0), SPEED_OF_LIGHT_M_PER_S, places=6)

    def test_round_trip_inverts_the_range(self):
        self.assertAlmostEqual(round_trip_from_range(SPEED_OF_LIGHT_M_PER_S), 2.0, places=9)

    def test_unambiguous_interval_from_the_code_period(self):
        self.assertAlmostEqual(unambiguous_range_m(CODE_PERIOD), INTERVAL, places=6)

    def test_resolution_from_the_chip_rate(self):
        self.assertAlmostEqual(range_resolution_m(CHIP_RATE), 149.896229, places=9)

    def test_a_faster_chip_rate_resolves_finer(self):
        self.assertAlmostEqual(range_resolution_m(2.0 * CHIP_RATE), 74.9481145, places=9)

    def test_zero_code_period_rejected(self):
        with self.assertRaises(ValueError):
            unambiguous_range_m(0.0)


class AmbiguityTests(unittest.TestCase):
    def test_interval_count_from_the_apriori(self):
        self.assertEqual(ambiguity_number(10000.0, 3.0 * INTERVAL + 10000.0, INTERVAL), 3)

    def test_apriori_inside_the_first_interval_counts_zero(self):
        self.assertEqual(ambiguity_number(10000.0, 12000.0, INTERVAL), 0)

    def test_resolution_lifts_the_measurement_onto_the_apriori_interval(self):
        self.assertAlmostEqual(
            resolve_range(10000.0, 3.0 * INTERVAL + 10000.0, INTERVAL),
            3.0 * INTERVAL + 10000.0,
            places=6,
        )

    def test_a_tight_apriori_resolves_the_ambiguity(self):
        self.assertTrue(ambiguity_resolvable(1000.0, INTERVAL))

    def test_apriori_uncertainty_exactly_half_an_interval_still_resolves(self):
        self.assertTrue(ambiguity_resolvable(INTERVAL / 2.0, INTERVAL))

    def test_apriori_looser_than_half_an_interval_cannot_resolve(self):
        self.assertFalse(ambiguity_resolvable(1.0e8, INTERVAL))


class DopplerTests(unittest.TestCase):
    def test_closing_spacecraft_raises_the_received_frequency(self):
        self.assertAlmostEqual(
            two_way_doppler_hz(CLOSING_RATE, UPLINK, TURNAROUND), CLOSING_DOPPLER, places=6
        )

    def test_receding_spacecraft_lowers_it(self):
        self.assertAlmostEqual(
            two_way_doppler_hz(1000.0, UPLINK, TURNAROUND), -CLOSING_DOPPLER, places=6
        )

    def test_a_stationary_spacecraft_shows_no_shift(self):
        self.assertAlmostEqual(two_way_doppler_hz(0.0, UPLINK, TURNAROUND), 0.0, places=9)

    def test_range_rate_inverts_the_doppler_shift(self):
        self.assertAlmostEqual(
            range_rate_from_doppler(CLOSING_DOPPLER, UPLINK, TURNAROUND), CLOSING_RATE, places=6
        )

    def test_turnaround_ratio_scales_the_shift(self):
        single = two_way_doppler_hz(CLOSING_RATE, UPLINK, 1.0)
        doubled = two_way_doppler_hz(CLOSING_RATE, UPLINK, 2.0)
        self.assertAlmostEqual(doubled, 2.0 * single, places=6)

    def test_shift_inside_the_band_is_trackable(self):
        self.assertTrue(within_tracking_bandwidth(CLOSING_DOPPLER, 40000.0))

    def test_shift_exactly_at_the_band_edge_is_trackable(self):
        self.assertTrue(within_tracking_bandwidth(CLOSING_DOPPLER, 2.0 * CLOSING_DOPPLER))

    def test_shift_beyond_the_band_is_not(self):
        self.assertFalse(within_tracking_bandwidth(CLOSING_DOPPLER, 1000.0))

    def test_required_bandwidth_covers_both_signs(self):
        self.assertAlmostEqual(
            required_tracking_bandwidth_hz(CLOSING_RATE, UPLINK, TURNAROUND),
            NEEDED_BANDWIDTH,
            places=6,
        )

    def test_required_bandwidth_ignores_the_sign_of_the_rate(self):
        self.assertAlmostEqual(
            required_tracking_bandwidth_hz(1000.0, UPLINK, TURNAROUND),
            required_tracking_bandwidth_hz(CLOSING_RATE, UPLINK, TURNAROUND),
            places=6,
        )


class AssessTests(unittest.TestCase):
    def near(self, **overrides):
        args = dict(
            round_trip_s=0.5,
            code_period_s=CODE_PERIOD,
            range_rate_mps=CLOSING_RATE,
            uplink_hz=UPLINK,
            turnaround_ratio=TURNAROUND,
            tracking_bandwidth_hz=40000.0,
            chip_rate_hz=CHIP_RATE,
        )
        args.update(overrides)
        return assess_tracking(**args)

    def test_geometry_inside_both_limits_is_trackable(self):
        result = self.near()
        self.assertEqual(result["verdict"], TRACKABLE)
        self.assertEqual(result["findings"], [])

    def test_trackable_geometry_reports_the_range(self):
        self.assertAlmostEqual(self.near()["observed_range_m"], INTERVAL / 2.0, places=6)

    def test_range_beyond_the_interval_without_an_apriori_is_ambiguous(self):
        result = self.near(round_trip_s=4.0)
        self.assertEqual(result["verdict"], RANGE_AMBIGUOUS)
        self.assertIsNone(result["resolved_range_m"])

    def test_ambiguous_geometry_names_both_remedies(self):
        findings = self.near(round_trip_s=4.0)["findings"]
        self.assertTrue(any("an a-priori range known to better than" in f for f in findings))

    def test_a_tight_apriori_makes_a_long_range_trackable(self):
        result = self.near(
            round_trip_s=4.0, apriori_range_m=599584916.0, apriori_uncertainty_m=1000.0
        )
        self.assertEqual(result["verdict"], TRACKABLE)
        self.assertAlmostEqual(result["resolved_range_m"], 599584916.0, places=6)

    def test_a_loose_apriori_leaves_it_ambiguous(self):
        result = self.near(
            round_trip_s=4.0, apriori_range_m=599584916.0, apriori_uncertainty_m=1.0e8
        )
        self.assertEqual(result["verdict"], RANGE_AMBIGUOUS)
        self.assertFalse(result["ambiguity_resolvable"])

    def test_doppler_beyond_the_band_outranks_the_range_verdict(self):
        result = self.near(round_trip_s=4.0, tracking_bandwidth_hz=1000.0)
        self.assertEqual(result["verdict"], DOPPLER_OUT_OF_BAND)

    def test_out_of_band_geometry_states_the_bandwidth_needed(self):
        findings = self.near(tracking_bandwidth_hz=1000.0)["findings"]
        self.assertTrue(any("tracking bandwidth of at least" in f for f in findings))

    def test_stated_bandwidth_actually_brings_it_into_band(self):
        needed = self.near(tracking_bandwidth_hz=1000.0)["required_tracking_bandwidth_hz"]
        self.assertEqual(self.near(tracking_bandwidth_hz=needed)["verdict"], TRACKABLE)

    def test_range_rate_is_recovered_from_the_shift(self):
        self.assertAlmostEqual(self.near()["range_rate_mps"], CLOSING_RATE, places=6)

    def test_range_resolution_is_carried_in_the_result(self):
        self.assertAlmostEqual(self.near()["range_resolution_m"], 149.896229, places=9)

    def test_folded_range_stays_inside_one_interval(self):
        folded = self.near(round_trip_s=4.5)["folded_range_m"]
        self.assertAlmostEqual(folded, INTERVAL / 2.0, places=6)

    def test_bad_round_trip_rejected(self):
        with self.assertRaises(ValueError):
            self.near(round_trip_s=0.0)

    def test_bad_turnaround_ratio_rejected(self):
        with self.assertRaises(ValueError):
            self.near(turnaround_ratio=-1.0)


if __name__ == "__main__":
    unittest.main()
