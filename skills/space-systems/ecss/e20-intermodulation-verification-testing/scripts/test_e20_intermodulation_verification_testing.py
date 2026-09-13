#!/usr/bin/env python3
"""Gate 3 contract test -- ECSS-E-ST-20C clause 7.4.4 verification testing."""

import math
import unittest

import e20_intermodulation_verification_testing_logic as logic

HALF_POWER_DB = 10.0 * math.log10(2.0)
ACCEPTANCE_DBM = -100.0
REQUIRED_HEADROOM_DB = 10.0


def run(**overrides):
    record = {
        "carrier_count": 2,
        "carrier_frequencies_hz": [1.80e9, 1.83e9],
        "carrier_power_dbm": 43.0,
        "measurement_bandwidth_hz": 1.0e6,
        "dwell_s": 60.0,
        "residual_dbm": -125.0,
        "uncertainty_db": 2.0,
        "measured_order": 3,
        "reading_dbm": -110.0,
    }
    record.update(overrides)
    return record


def flight_plan(**overrides):
    plan = {"carrier_count": 2, "carrier_power_dbm": 43.0}
    plan.update(overrides)
    return plan


class TestPowerHelpers(unittest.TestCase):
    def test_zero_dbm_is_one_milliwatt(self):
        self.assertAlmostEqual(logic.dbm_to_mw(0.0), 1.0, places=12)

    def test_power_sum_of_two_equal_readings_adds_three_db(self):
        self.assertAlmostEqual(
            logic.power_sum_dbm([-110.0, -110.0]), -110.0 + HALF_POWER_DB, places=10
        )

    def test_power_sum_of_one_reading_is_that_reading(self):
        self.assertAlmostEqual(logic.power_sum_dbm([-107.25]), -107.25, places=10)

    def test_power_sum_is_dominated_by_the_strongest_reading(self):
        self.assertAlmostEqual(logic.power_sum_dbm([-100.0, -130.0]), -99.99566, places=4)

    def test_power_sum_rejects_an_empty_sequence(self):
        with self.assertRaises(ValueError):
            logic.power_sum_dbm([])

    def test_power_sum_rejects_a_non_numeric_reading(self):
        with self.assertRaises(ValueError):
            logic.power_sum_dbm([-110.0, "-110"])

    def test_dbm_conversion_rejects_infinity(self):
        with self.assertRaises(ValueError):
            logic.dbm_to_mw(float("inf"))


class TestOrderSelection(unittest.TestCase):
    def test_lowest_critical_order_is_selected(self):
        self.assertEqual(logic.select_measured_order([3, 5, 7]), 3)

    def test_selection_does_not_depend_on_input_ordering(self):
        self.assertEqual(logic.select_measured_order([7, 5, 3]), 3)

    def test_a_single_critical_order_is_returned(self):
        self.assertEqual(logic.select_measured_order([5]), 5)

    def test_empty_critical_set_is_rejected(self):
        with self.assertRaises(ValueError):
            logic.select_measured_order([])

    def test_order_below_three_is_rejected(self):
        with self.assertRaises(ValueError):
            logic.select_measured_order([2, 5])

    def test_non_integer_order_is_rejected(self):
        with self.assertRaises(ValueError):
            logic.select_measured_order([3.0])

    def test_boolean_order_is_rejected(self):
        with self.assertRaises(ValueError):
            logic.select_measured_order([True])


class TestConfigurationValidation(unittest.TestCase):
    def test_valid_configuration_is_normalised(self):
        record = logic.validate_test_configuration(run())
        self.assertEqual(record["carrier_count"], 2)
        self.assertEqual(record["measured_order"], 3)
        self.assertAlmostEqual(record["carrier_power_dbm"], 43.0, places=10)
        self.assertAlmostEqual(record["dwell_s"], 60.0, places=10)

    def test_dwell_defaults_to_zero(self):
        config = run()
        del config["dwell_s"]
        self.assertAlmostEqual(
            logic.validate_test_configuration(config)["dwell_s"], 0.0, places=10
        )

    def test_non_mapping_configuration_is_rejected(self):
        with self.assertRaises(ValueError):
            logic.validate_test_configuration([1.8e9, 1.83e9])

    def test_single_carrier_run_is_rejected(self):
        with self.assertRaises(ValueError):
            logic.validate_test_configuration(
                run(carrier_count=1, carrier_frequencies_hz=[1.8e9])
            )

    def test_non_integer_carrier_count_is_rejected(self):
        with self.assertRaises(ValueError):
            logic.validate_test_configuration(run(carrier_count=2.0))

    def test_frequency_list_length_must_match_the_carrier_count(self):
        with self.assertRaises(ValueError):
            logic.validate_test_configuration(run(carrier_frequencies_hz=[1.8e9]))

    def test_duplicate_carrier_frequencies_are_rejected(self):
        with self.assertRaises(ValueError):
            logic.validate_test_configuration(
                run(carrier_frequencies_hz=[1.8e9, 1.8e9])
            )

    def test_non_positive_carrier_frequency_is_rejected(self):
        with self.assertRaises(ValueError):
            logic.validate_test_configuration(
                run(carrier_frequencies_hz=[0.0, 1.83e9])
            )

    def test_non_positive_measurement_bandwidth_is_rejected(self):
        with self.assertRaises(ValueError):
            logic.validate_test_configuration(run(measurement_bandwidth_hz=0.0))

    def test_negative_dwell_is_rejected(self):
        with self.assertRaises(ValueError):
            logic.validate_test_configuration(run(dwell_s=-1.0))

    def test_measured_order_below_three_is_rejected(self):
        with self.assertRaises(ValueError):
            logic.validate_test_configuration(run(measured_order=2))

    def test_missing_residual_is_rejected(self):
        config = run()
        del config["residual_dbm"]
        with self.assertRaises(ValueError):
            logic.validate_test_configuration(config)

    def test_negative_uncertainty_is_rejected(self):
        with self.assertRaises(ValueError):
            logic.validate_test_configuration(run(uncertainty_db=-0.5))


class TestConfigurationAgainstFlight(unittest.TestCase):
    def test_matched_configuration_raises_no_finding(self):
        self.assertEqual(
            logic.check_configuration_against_flight(run(), flight_plan(), 3, 2.0e6), []
        )

    def test_equal_carrier_power_is_accepted_at_the_boundary(self):
        self.assertEqual(
            logic.check_configuration_against_flight(
                run(carrier_power_dbm=43.0), flight_plan(carrier_power_dbm=43.0), 3
            ),
            [],
        )

    def test_test_power_below_flight_is_a_finding(self):
        findings = logic.check_configuration_against_flight(
            run(carrier_power_dbm=40.0), flight_plan(), 3
        )
        self.assertTrue(any("below the flight" in f for f in findings))

    def test_test_power_above_flight_is_acceptable(self):
        self.assertEqual(
            logic.check_configuration_against_flight(
                run(carrier_power_dbm=46.0), flight_plan(), 3
            ),
            [],
        )

    def test_fewer_carriers_than_flight_is_a_finding(self):
        findings = logic.check_configuration_against_flight(
            run(), flight_plan(carrier_count=3), 3
        )
        self.assertTrue(any("carrier count" in f for f in findings))

    def test_measuring_the_wrong_order_is_a_finding(self):
        findings = logic.check_configuration_against_flight(
            run(measured_order=7), flight_plan(), 3
        )
        self.assertTrue(any("lowest critical order" in f for f in findings))

    def test_measurement_bandwidth_wider_than_the_band_is_a_finding(self):
        findings = logic.check_configuration_against_flight(
            run(measurement_bandwidth_hz=5.0e6), flight_plan(), 3, 2.0e6
        )
        self.assertTrue(any("measurement-bandwidth" in f for f in findings))

    def test_measurement_bandwidth_equal_to_the_band_is_accepted(self):
        self.assertEqual(
            logic.check_configuration_against_flight(
                run(measurement_bandwidth_hz=2.0e6), flight_plan(), 3, 2.0e6
            ),
            [],
        )

    def test_non_mapping_flight_plan_is_rejected(self):
        with self.assertRaises(ValueError):
            logic.check_configuration_against_flight(run(), [43.0], 3)

    def test_non_integer_flight_carrier_count_is_rejected(self):
        with self.assertRaises(ValueError):
            logic.check_configuration_against_flight(
                run(), flight_plan(carrier_count="2"), 3
            )

    def test_non_positive_victim_bandwidth_is_rejected(self):
        with self.assertRaises(ValueError):
            logic.check_configuration_against_flight(run(), flight_plan(), 3, 0.0)


class TestBenchCapability(unittest.TestCase):
    def test_headroom_is_the_gap_to_the_residual(self):
        self.assertAlmostEqual(
            logic.residual_headroom_db(ACCEPTANCE_DBM, -125.0), 25.0, places=10
        )

    def test_headroom_is_negative_when_the_residual_is_above_the_limit(self):
        self.assertAlmostEqual(
            logic.residual_headroom_db(ACCEPTANCE_DBM, -95.0), -5.0, places=10
        )

    def test_a_bench_with_ample_headroom_is_capable(self):
        self.assertTrue(
            logic.measurement_is_capable(ACCEPTANCE_DBM, -125.0, REQUIRED_HEADROOM_DB)
        )

    def test_a_bench_exactly_at_the_required_headroom_is_capable(self):
        self.assertTrue(
            logic.measurement_is_capable(ACCEPTANCE_DBM, -110.0, REQUIRED_HEADROOM_DB)
        )

    def test_a_bench_short_of_the_required_headroom_is_not_capable(self):
        self.assertFalse(
            logic.measurement_is_capable(ACCEPTANCE_DBM, -105.0, REQUIRED_HEADROOM_DB)
        )

    def test_negative_required_headroom_is_rejected(self):
        with self.assertRaises(ValueError):
            logic.measurement_is_capable(ACCEPTANCE_DBM, -125.0, -1.0)

    def test_worst_case_adds_the_uncertainty(self):
        self.assertAlmostEqual(logic.worst_case_level_dbm(-110.0, 2.0), -108.0, places=10)

    def test_worst_case_rejects_a_negative_uncertainty(self):
        with self.assertRaises(ValueError):
            logic.worst_case_level_dbm(-110.0, -2.0)


class TestReadingVerdicts(unittest.TestCase):
    def evaluate(self, reading, uncertainty=2.0, residual=-125.0, headroom=REQUIRED_HEADROOM_DB):
        return logic.evaluate_reading(
            reading, uncertainty, ACCEPTANCE_DBM, residual, headroom
        )

    def test_comfortable_reading_passes(self):
        outcome = self.evaluate(-110.0)
        self.assertEqual(outcome["verdict"], logic.VERDICT_PASS)
        self.assertAlmostEqual(outcome["worst_case_dbm"], -108.0, places=10)

    def test_worst_case_exactly_at_the_limit_passes(self):
        uncertainty = 0.1 + 0.2  # deliberately not representable exactly
        outcome = self.evaluate(ACCEPTANCE_DBM - uncertainty, uncertainty=uncertainty)
        self.assertEqual(outcome["verdict"], logic.VERDICT_PASS)
        self.assertAlmostEqual(outcome["worst_case_dbm"], ACCEPTANCE_DBM, places=9)

    def test_reading_clearing_but_worst_case_failing_is_uncertainty_limited(self):
        outcome = self.evaluate(-101.0)
        self.assertEqual(outcome["verdict"], logic.VERDICT_UNCERTAINTY_LIMITED)

    def test_reading_above_the_limit_fails(self):
        outcome = self.evaluate(-95.0)
        self.assertEqual(outcome["verdict"], logic.VERDICT_FAIL)
        self.assertIn("exceeds the limit", outcome["note"])

    def test_reading_exactly_at_the_limit_with_no_uncertainty_passes(self):
        outcome = self.evaluate(ACCEPTANCE_DBM, uncertainty=0.0)
        self.assertEqual(outcome["verdict"], logic.VERDICT_PASS)

    def test_bench_without_headroom_is_instrument_limited(self):
        outcome = self.evaluate(-110.0, residual=-105.0)
        self.assertEqual(outcome["verdict"], logic.VERDICT_INSTRUMENT_LIMITED)
        self.assertFalse(outcome["capable"])

    def test_an_uncapable_bench_is_instrument_limited_even_for_a_high_reading(self):
        outcome = self.evaluate(-90.0, residual=-105.0)
        self.assertEqual(outcome["verdict"], logic.VERDICT_INSTRUMENT_LIMITED)

    def test_reading_at_the_residual_bounds_the_unit(self):
        outcome = self.evaluate(-125.0)
        self.assertEqual(outcome["verdict"], logic.VERDICT_PASS)
        self.assertTrue(outcome["at_residual"])

    def test_reading_below_the_residual_is_also_a_residual_reading(self):
        outcome = self.evaluate(-130.0)
        self.assertTrue(outcome["at_residual"])

    def test_headroom_is_reported_with_every_reading(self):
        self.assertAlmostEqual(self.evaluate(-110.0)["headroom_db"], 25.0, places=10)

    def test_non_numeric_reading_is_rejected(self):
        with self.assertRaises(ValueError):
            self.evaluate("-110")


class TestCampaign(unittest.TestCase):
    def campaign(self, runs, **kwargs):
        kwargs.setdefault("critical_orders", [3, 5])
        return logic.evaluate_campaign(
            runs, ACCEPTANCE_DBM, REQUIRED_HEADROOM_DB, **kwargs
        )

    def test_a_clean_campaign_is_verified(self):
        result = self.campaign([run()], flight_plan=flight_plan(), victim_bandwidth_hz=2e6)
        self.assertEqual(result["verdict"], logic.CAMPAIGN_PASS)
        self.assertTrue(result["verified"])
        self.assertEqual(result["lowest_critical_order"], 3)
        self.assertEqual(result["findings"], [])

    def test_a_failing_run_fails_the_campaign(self):
        result = self.campaign([run(reading_dbm=-90.0)])
        self.assertEqual(result["verdict"], logic.CAMPAIGN_FAIL)
        self.assertFalse(result["verified"])

    def test_an_uncertainty_limited_run_leaves_the_campaign_inconclusive(self):
        result = self.campaign([run(reading_dbm=-101.0)])
        self.assertEqual(result["verdict"], logic.CAMPAIGN_INCONCLUSIVE)
        self.assertTrue(result["aggregate_uncertainty_limited"])
        self.assertFalse(result["aggregate_exceeds"])

    def test_an_aggregate_only_the_uncertainty_pushes_over_is_not_a_fail(self):
        result = self.campaign(
            [
                run(reading_dbm=-104.0, uncertainty_db=2.0),
                run(reading_dbm=-104.0, uncertainty_db=2.0,
                    carrier_frequencies_hz=[1.81e9, 1.84e9]),
            ]
        )
        self.assertFalse(result["aggregate_exceeds"])
        self.assertTrue(result["aggregate_uncertainty_limited"])
        self.assertEqual(result["verdict"], logic.CAMPAIGN_INCONCLUSIVE)

    def test_an_instrument_limited_run_leaves_the_campaign_inconclusive(self):
        result = self.campaign([run(residual_dbm=-104.0)])
        self.assertEqual(result["verdict"], logic.CAMPAIGN_INCONCLUSIVE)

    def test_measuring_only_a_high_order_is_inconclusive(self):
        result = self.campaign([run(measured_order=5)])
        self.assertEqual(result["verdict"], logic.CAMPAIGN_INCONCLUSIVE)
        self.assertTrue(any("never measured" in f for f in result["findings"]))

    def test_two_products_power_sum_into_the_band_verdict(self):
        reading = ACCEPTANCE_DBM - HALF_POWER_DB
        result = self.campaign(
            [
                run(reading_dbm=reading, uncertainty_db=0.0),
                run(reading_dbm=reading, uncertainty_db=0.0, carrier_frequencies_hz=[1.81e9, 1.84e9]),
            ]
        )
        self.assertAlmostEqual(result["aggregate_dbm"], ACCEPTANCE_DBM, places=9)
        self.assertFalse(result["aggregate_exceeds"])
        self.assertEqual(result["verdict"], logic.CAMPAIGN_PASS)

    def test_two_individually_passing_products_can_fail_the_aggregate(self):
        result = self.campaign(
            [
                run(reading_dbm=-100.5, uncertainty_db=0.0),
                run(reading_dbm=-100.5, uncertainty_db=0.0, carrier_frequencies_hz=[1.81e9, 1.84e9]),
            ]
        )
        self.assertTrue(result["aggregate_exceeds"])
        self.assertEqual(result["verdict"], logic.CAMPAIGN_FAIL)

    def test_aggregate_carries_the_worst_uncertainty(self):
        result = self.campaign([run(reading_dbm=-110.0, uncertainty_db=2.0)])
        self.assertAlmostEqual(
            result["aggregate_worst_case_dbm"], -108.0, places=9
        )

    def test_configuration_findings_block_a_pass(self):
        result = self.campaign(
            [run(carrier_power_dbm=38.0)], flight_plan=flight_plan()
        )
        self.assertEqual(result["verdict"], logic.CAMPAIGN_INCONCLUSIVE)
        self.assertTrue(any("below the flight" in f for f in result["findings"]))

    def test_every_run_is_reported_with_its_index_and_order(self):
        result = self.campaign([run(), run(reading_dbm=-112.0)])
        self.assertEqual([r["index"] for r in result["runs"]], [0, 1])
        self.assertEqual({r["measured_order"] for r in result["runs"]}, {3})

    def test_empty_campaign_is_rejected(self):
        with self.assertRaises(ValueError):
            self.campaign([])

    def test_non_mapping_run_is_rejected(self):
        with self.assertRaises(ValueError):
            self.campaign([[-110.0]])

    def test_run_without_a_reading_is_rejected(self):
        config = run()
        del config["reading_dbm"]
        with self.assertRaises(ValueError):
            self.campaign([config])

    def test_empty_critical_order_set_is_rejected(self):
        with self.assertRaises(ValueError):
            self.campaign([run()], critical_orders=[])


if __name__ == "__main__":
    unittest.main()
