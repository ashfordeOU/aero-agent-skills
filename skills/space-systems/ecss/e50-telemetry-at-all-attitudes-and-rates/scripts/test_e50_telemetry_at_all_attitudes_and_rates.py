"""Contract tests for the clause 5.5.1 telemetry-availability logic."""

import math
import unittest

from e50_telemetry_at_all_attitudes_and_rates_logic import (
    BOLTZMANN_DBW_PER_K_HZ,
    MARGIN_TOLERANCE_DB,
    assess_telemetry_availability,
    coverage_fraction,
    eirp_dbw,
    evaluate_pattern,
    link_margin_db,
    outage_duration_s,
    received_ebno_db,
    validate_pattern,
)

# A low-gain pattern sampled in six 30 deg bands from boresight to the back lobe.
PATTERN = [
    {"angle_deg": 15.0, "width_deg": 30.0, "gain_dbi": 0.0},
    {"angle_deg": 45.0, "width_deg": 30.0, "gain_dbi": -2.0},
    {"angle_deg": 75.0, "width_deg": 30.0, "gain_dbi": -4.0},
    {"angle_deg": 105.0, "width_deg": 30.0, "gain_dbi": -6.0},
    {"angle_deg": 135.0, "width_deg": 30.0, "gain_dbi": -9.0},
    {"angle_deg": 165.0, "width_deg": 30.0, "gain_dbi": -15.0},
]

BUDGET = {
    "tx_power_dbw": 3.0,
    "circuit_loss_db": 2.0,
    "path_loss_db": 217.0,
    "station_g_over_t_db": 32.0,
    "data_rate_bps": 500.0,
    "required_ebno_db": 3.0,
}


def base_spec(**overrides):
    spec = {
        "samples": PATTERN,
        "budget": BUDGET,
        "body_rate_range_deg_s": (0.5, 6.0),
        "receiver_hold_s": 90.0,
    }
    spec.update(overrides)
    return spec


class PatternValidationTests(unittest.TestCase):
    def test_pattern_is_returned_sample_by_sample(self):
        self.assertEqual(len(validate_pattern(PATTERN)), 6)

    def test_negative_gain_is_allowed(self):
        validated = validate_pattern([{"angle_deg": 170.0, "width_deg": 10.0, "gain_dbi": -20.0}])
        self.assertAlmostEqual(validated[0]["gain_dbi"], -20.0)

    def test_angle_beyond_the_back_lobe_rejected(self):
        with self.assertRaises(ValueError):
            validate_pattern([{"angle_deg": 200.0, "width_deg": 10.0, "gain_dbi": 0.0}])

    def test_zero_width_sample_rejected(self):
        with self.assertRaises(ValueError):
            validate_pattern([{"angle_deg": 15.0, "width_deg": 0.0, "gain_dbi": 0.0}])

    def test_negative_angle_rejected(self):
        with self.assertRaises(ValueError):
            validate_pattern([{"angle_deg": -15.0, "width_deg": 10.0, "gain_dbi": 0.0}])

    def test_empty_pattern_rejected(self):
        with self.assertRaises(ValueError):
            validate_pattern([])

    def test_sample_missing_a_field_rejected(self):
        with self.assertRaises(ValueError):
            validate_pattern([{"angle_deg": 15.0, "width_deg": 10.0}])


class BudgetTermTests(unittest.TestCase):
    def test_eirp_adds_gain_and_subtracts_circuit_loss(self):
        self.assertAlmostEqual(eirp_dbw(3.0, 2.0, -4.0), -3.0)

    def test_negative_circuit_loss_rejected(self):
        with self.assertRaises(ValueError):
            eirp_dbw(3.0, -2.0, 0.0)

    def test_doubling_the_data_rate_costs_three_db(self):
        slow = received_ebno_db(0.0, 217.0, 32.0, 500.0)
        fast = received_ebno_db(0.0, 217.0, 32.0, 1000.0)
        self.assertAlmostEqual(slow - fast, 10.0 * math.log10(2.0), places=9)

    def test_boltzmann_term_is_carried_in_the_link(self):
        value = received_ebno_db(0.0, 100.0, 0.0, 1.0)
        self.assertAlmostEqual(value, -100.0 - BOLTZMANN_DBW_PER_K_HZ, places=9)

    def test_zero_data_rate_rejected(self):
        with self.assertRaises(ValueError):
            received_ebno_db(0.0, 217.0, 32.0, 0.0)

    def test_margin_subtracts_the_requirement_and_the_implementation_loss(self):
        self.assertAlmostEqual(link_margin_db(10.0, 3.0, 1.5), 5.5)

    def test_negative_implementation_loss_rejected(self):
        with self.assertRaises(ValueError):
            link_margin_db(10.0, 3.0, -1.5)


class PatternEvaluationTests(unittest.TestCase):
    def test_every_sample_gets_a_margin(self):
        records = evaluate_pattern(PATTERN, BUDGET)
        self.assertEqual(len(records), 6)
        self.assertTrue(all("margin_db" in record for record in records))

    def test_boresight_has_the_best_margin(self):
        records = evaluate_pattern(PATTERN, BUDGET)
        self.assertAlmostEqual(records[0]["margin_db"], max(r["margin_db"] for r in records))

    def test_the_back_lobe_sample_does_not_close(self):
        records = evaluate_pattern(PATTERN, BUDGET)
        self.assertFalse(records[-1]["closes"])
        self.assertTrue(records[-2]["closes"])

    def test_a_margin_landing_exactly_on_zero_still_closes(self):
        sample = [{"angle_deg": 15.0, "width_deg": 30.0, "gain_dbi": 0.0}]
        eirp = eirp_dbw(BUDGET["tx_power_dbw"], BUDGET["circuit_loss_db"], 0.0)
        ebno = received_ebno_db(
            eirp, BUDGET["path_loss_db"], BUDGET["station_g_over_t_db"], BUDGET["data_rate_bps"]
        )
        budget = dict(BUDGET, required_ebno_db=ebno)
        records = evaluate_pattern(sample, budget)
        self.assertTrue(records[0]["closes"])
        self.assertLessEqual(abs(records[0]["margin_db"]), MARGIN_TOLERANCE_DB)

    def test_budget_missing_a_key_rejected(self):
        budget = dict(BUDGET)
        del budget["required_ebno_db"]
        with self.assertRaises(ValueError):
            evaluate_pattern(PATTERN, budget)

    def test_non_mapping_budget_rejected(self):
        with self.assertRaises(ValueError):
            evaluate_pattern(PATTERN, ["tx_power_dbw"])


class CoverageTests(unittest.TestCase):
    def test_coverage_is_width_weighted(self):
        records = evaluate_pattern(PATTERN, BUDGET)
        self.assertAlmostEqual(coverage_fraction(records), 5.0 / 6.0)

    def test_a_wide_failing_band_costs_more_coverage(self):
        pattern = [
            {"angle_deg": 15.0, "width_deg": 10.0, "gain_dbi": 0.0},
            {"angle_deg": 165.0, "width_deg": 30.0, "gain_dbi": -40.0},
        ]
        records = evaluate_pattern(pattern, BUDGET)
        self.assertAlmostEqual(coverage_fraction(records), 10.0 / 40.0)

    def test_empty_record_set_rejected(self):
        with self.assertRaises(ValueError):
            coverage_fraction([])

    def test_malformed_record_rejected(self):
        with self.assertRaises(ValueError):
            coverage_fraction([{"width_deg": 10.0}])


class OutageDurationTests(unittest.TestCase):
    def test_duration_is_width_over_rate(self):
        self.assertAlmostEqual(outage_duration_s(30.0, 6.0), 5.0)

    def test_a_slower_body_rate_lengthens_the_outage(self):
        self.assertGreater(outage_duration_s(30.0, 0.5), outage_duration_s(30.0, 6.0))

    def test_zero_body_rate_rejected(self):
        with self.assertRaises(ValueError):
            outage_duration_s(30.0, 0.0)

    def test_zero_outage_width_rejected(self):
        with self.assertRaises(ValueError):
            outage_duration_s(0.0, 6.0)


class AvailabilityTests(unittest.TestCase):
    def test_pattern_hole_is_reported_with_its_width(self):
        result = assess_telemetry_availability(base_spec())
        self.assertFalse(result["compliant"])
        self.assertAlmostEqual(result["outage_width_deg"], 30.0)

    def test_a_generous_receiver_hold_rides_the_hole_through(self):
        result = assess_telemetry_availability(base_spec(receiver_hold_s=90.0))
        self.assertTrue(result["rides_through"])

    def test_a_short_receiver_hold_does_not_ride_it_through(self):
        result = assess_telemetry_availability(base_spec(receiver_hold_s=10.0))
        self.assertFalse(result["rides_through"])
        self.assertTrue(any("holds lock" in f for f in result["findings"]))

    def test_the_slowest_rate_sets_the_outage_duration(self):
        result = assess_telemetry_availability(base_spec())
        self.assertAlmostEqual(result["worst_outage_s"], 60.0)

    def test_a_pattern_that_closes_everywhere_is_compliant(self):
        budget = dict(BUDGET, path_loss_db=200.0)
        result = assess_telemetry_availability(base_spec(budget=budget))
        self.assertTrue(result["compliant"])
        self.assertEqual(result["findings"], [])
        self.assertAlmostEqual(result["coverage_fraction"], 1.0)

    def test_coverage_fraction_is_reported(self):
        result = assess_telemetry_availability(base_spec())
        self.assertAlmostEqual(result["coverage_fraction"], 5.0 / 6.0)

    def test_inverted_body_rate_range_rejected(self):
        with self.assertRaises(ValueError):
            assess_telemetry_availability(base_spec(body_rate_range_deg_s=(6.0, 0.5)))

    def test_malformed_body_rate_range_rejected(self):
        with self.assertRaises(ValueError):
            assess_telemetry_availability(base_spec(body_rate_range_deg_s=(1.0,)))

    def test_zero_receiver_hold_rejected(self):
        with self.assertRaises(ValueError):
            assess_telemetry_availability(base_spec(receiver_hold_s=0.0))

    def test_missing_spec_key_rejected(self):
        spec = base_spec()
        del spec["budget"]
        with self.assertRaises(ValueError):
            assess_telemetry_availability(spec)

    def test_non_mapping_spec_rejected(self):
        with self.assertRaises(ValueError):
            assess_telemetry_availability(["samples"])


if __name__ == "__main__":
    unittest.main()
