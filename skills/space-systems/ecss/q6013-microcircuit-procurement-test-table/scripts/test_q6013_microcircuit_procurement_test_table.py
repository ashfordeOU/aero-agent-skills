"""Contract tests for the Table 8-6 microcircuit procurement matrix logic.

The cases follow the workflow one step at a time: row validation and the
accept-on-zero rule for consuming rows, the burn-in percent defective
allowable and its bounded exclusion, parameter drift, temperature-point
coverage, the life-test duration and the lot disposition that carries them.
Each step is exercised on both sides of its limit, so a review of the record
shows what was judged and not only the verdict.
"""

import unittest

from q6013_microcircuit_procurement_test_table_logic import (
    LIMIT_TOLERANCE,
    MARGINAL_FRACTION,
    MAX_EXCLUSION_FRACTION,
    TEMPERATURE_POINTS,
    assess_microcircuit_test_matrix,
    burn_in_pda,
    life_test_verdict,
    parameter_drift_rejects,
    row_verdict,
    temperature_coverage,
    validate_row,
)


def _row(method="external-visual", sample_size=20, **extra):
    record = {"method": method, "sample_size": sample_size}
    record.update(extra)
    return record


def _spec(**overrides):
    spec = {
        "lot_size": 300,
        "allowable_percent": 5.0,
        "rows": [
            _row("external-visual", 30, accept_number=1, failures=0),
            _row("electrical-end-points", 30, accept_number=1, failures=0),
            _row("seal-fine-and-gross", 12, accept_number=0, failures=0),
            _row("construction-analysis", 4, accept_number=0, failures=0),
        ],
    }
    spec.update(overrides)
    return spec


class RowValidationTests(unittest.TestCase):
    def test_valid_row_is_normalised(self):
        record = validate_row(_row("external-visual", 30, accept_number=2), 300)
        self.assertEqual(record["sample_size"], 30)
        self.assertEqual(record["accept_number"], 2)

    def test_consuming_method_is_flagged_without_an_override(self):
        record = validate_row(_row("construction-analysis", 4), 300)
        self.assertTrue(record["destructive"])

    def test_non_consuming_method_defaults_to_returnable(self):
        record = validate_row(_row("external-visual", 30), 300)
        self.assertFalse(record["destructive"])

    def test_consuming_row_with_an_accept_number_refused(self):
        with self.assertRaises(ValueError):
            validate_row(_row("construction-analysis", 4, accept_number=1), 300)

    def test_consuming_row_on_accept_on_zero_is_admissible(self):
        record = validate_row(_row("construction-analysis", 4, accept_number=0), 300)
        self.assertEqual(record["accept_number"], 0)

    def test_sample_larger_than_lot_rejected(self):
        with self.assertRaises(ValueError):
            validate_row(_row("external-visual", 301), 300)

    def test_zero_sample_rejected(self):
        with self.assertRaises(ValueError):
            validate_row(_row("external-visual", 0), 300)

    def test_more_failures_than_sampled_rejected(self):
        with self.assertRaises(ValueError):
            validate_row(_row("external-visual", 5, failures=6), 300)

    def test_non_mapping_row_rejected(self):
        with self.assertRaises(ValueError):
            validate_row(["external-visual", 5], 300)


class BurnInTests(unittest.TestCase):
    def test_rate_taken_on_the_devices_that_entered(self):
        record = burn_in_pda(200, 4, 5.0)
        self.assertAlmostEqual(record["percent_defective"], 2.0, places=9)
        self.assertTrue(record["accepted"])

    def test_rate_exactly_on_the_allowance_is_admissible(self):
        record = burn_in_pda(200, 10, 5.0)
        self.assertAlmostEqual(record["percent_defective"], 5.0, places=9)
        self.assertTrue(record["accepted"])

    def test_rate_over_the_allowance_rejects(self):
        record = burn_in_pda(200, 14, 5.0)
        self.assertFalse(record["accepted"])

    def test_excluded_handling_failures_lower_the_rate(self):
        record = burn_in_pda(200, 12, 5.0, excluded_failures=2)
        self.assertAlmostEqual(record["percent_defective"], 5.0, places=9)
        self.assertEqual(record["device_failures"], 10)

    def test_exclusion_beyond_the_cap_is_challenged(self):
        record = burn_in_pda(200, 8, 5.0, excluded_failures=5)
        self.assertTrue(record["exclusion_challenged"])

    def test_exclusion_inside_the_cap_is_not_challenged(self):
        record = burn_in_pda(200, 8, 5.0, excluded_failures=2)
        self.assertFalse(record["exclusion_challenged"])

    def test_excluding_more_than_the_failures_rejected(self):
        with self.assertRaises(ValueError):
            burn_in_pda(200, 3, 5.0, excluded_failures=4)

    def test_failures_above_the_entered_population_rejected(self):
        with self.assertRaises(ValueError):
            burn_in_pda(50, 51, 5.0)

    def test_zero_entered_population_rejected(self):
        with self.assertRaises(ValueError):
            burn_in_pda(0, 0, 5.0)

    def test_marginal_burn_in_is_flagged_but_accepted(self):
        record = burn_in_pda(200, 9, 5.0)
        self.assertTrue(record["accepted"])
        self.assertTrue(record["marginal"])


class DriftTests(unittest.TestCase):
    def test_small_drift_accepts(self):
        record = parameter_drift_rejects([(10.0, 10.2), (10.0, 9.9)], 5.0)
        self.assertTrue(record["accepted"])

    def test_downward_drift_counts_by_magnitude(self):
        record = parameter_drift_rejects([(10.0, 9.0)], 5.0)
        self.assertFalse(record["accepted"])
        self.assertAlmostEqual(record["worst_drift_percent"], 10.0, places=9)

    def test_drift_exactly_on_the_limit_is_admissible(self):
        record = parameter_drift_rejects([(10.0, 10.5)], 5.0)
        self.assertTrue(record["accepted"])
        self.assertAlmostEqual(record["worst_drift_percent"], 5.0, places=9)

    def test_zero_initial_reading_rejected(self):
        with self.assertRaises(ValueError):
            parameter_drift_rejects([(0.0, 1.0)], 5.0)

    def test_malformed_reading_pair_rejected(self):
        with self.assertRaises(ValueError):
            parameter_drift_rejects([(10.0,)], 5.0)

    def test_negative_delta_limit_rejected(self):
        with self.assertRaises(ValueError):
            parameter_drift_rejects([(10.0, 10.1)], -1.0)


class TemperatureCoverageTests(unittest.TestCase):
    def test_all_three_points_accept(self):
        record = temperature_coverage(["cold", "room", "hot"])
        self.assertTrue(record["accepted"])
        self.assertEqual(record["missing"], [])

    def test_room_alone_is_not_the_row(self):
        record = temperature_coverage(["room"])
        self.assertFalse(record["accepted"])
        self.assertEqual(record["missing"], ["cold", "hot"])

    def test_repeated_point_collapses(self):
        record = temperature_coverage(["hot", "hot", "cold", "room"])
        self.assertTrue(record["accepted"])
        self.assertEqual(len(record["covered"]), len(TEMPERATURE_POINTS))

    def test_unknown_point_rejected(self):
        with self.assertRaises(ValueError):
            temperature_coverage(["cold", "tepid", "hot"])

    def test_empty_point_set_rejected(self):
        with self.assertRaises(ValueError):
            temperature_coverage([])


class LifeTestTests(unittest.TestCase):
    def test_full_duration_without_failures_accepts(self):
        record = life_test_verdict(1000.0, 1000.0, 0, 22)
        self.assertTrue(record["accepted"])
        self.assertAlmostEqual(record["shortfall_hours"], 0.0, places=9)

    def test_duration_exactly_met_is_admissible(self):
        record = life_test_verdict(1000.0, 1000.0, 0, 22)
        self.assertTrue(record["duration_met"])

    def test_short_run_is_held_even_with_no_failures(self):
        record = life_test_verdict(720.0, 1000.0, 0, 22)
        self.assertFalse(record["accepted"])
        self.assertAlmostEqual(record["shortfall_hours"], 280.0, places=9)

    def test_failures_over_the_accept_number_reject(self):
        record = life_test_verdict(1000.0, 1000.0, 2, 22, accept_number=1)
        self.assertFalse(record["accepted"])
        self.assertFalse(record["within_accept_number"])

    def test_failures_within_the_accept_number_accept(self):
        record = life_test_verdict(1000.0, 1000.0, 1, 22, accept_number=1)
        self.assertTrue(record["accepted"])

    def test_non_positive_required_duration_rejected(self):
        with self.assertRaises(ValueError):
            life_test_verdict(1000.0, 0.0, 0, 22)

    def test_failures_above_the_sample_rejected(self):
        with self.assertRaises(ValueError):
            life_test_verdict(1000.0, 1000.0, 23, 22)


class RowVerdictTests(unittest.TestCase):
    def test_rate_exactly_on_the_allowance_is_admissible(self):
        record = row_verdict(validate_row(_row("external-visual", 20, accept_number=3, failures=1), 300), 5.0)
        self.assertTrue(record["within_allowance"])
        self.assertAlmostEqual(record["percent_defective"], 5.0, places=9)

    def test_rate_over_the_allowance_rejects_within_the_accept_number(self):
        record = row_verdict(validate_row(_row("external-visual", 10, accept_number=3, failures=2), 300), 5.0)
        self.assertFalse(record["accepted"])
        self.assertTrue(record["within_accept_number"])

    def test_marginal_row_is_flagged_but_accepted(self):
        record = row_verdict(validate_row(_row("external-visual", 25, accept_number=3, failures=1), 300), 5.0)
        self.assertTrue(record["accepted"])
        self.assertTrue(record["marginal"])

    def test_allowance_outside_zero_to_hundred_rejected(self):
        with self.assertRaises(ValueError):
            row_verdict(validate_row(_row("external-visual", 20), 300), -1.0)


class MatrixAssessmentTests(unittest.TestCase):
    def test_clean_matrix_accepts_the_lot(self):
        result = assess_microcircuit_test_matrix(_spec())
        self.assertTrue(result["accepted"])
        self.assertEqual(result["disposition"], "accept-microcircuit-lot")

    def test_every_rejecting_row_is_named_not_only_the_first(self):
        spec = _spec(
            rows=[
                _row("external-visual", 30, accept_number=0, failures=3),
                _row("electrical-end-points", 30, accept_number=0, failures=2),
                _row("seal-fine-and-gross", 12, accept_number=0, failures=0),
            ]
        )
        result = assess_microcircuit_test_matrix(spec)
        self.assertEqual(
            result["rejecting_rows"], ["external-visual", "electrical-end-points"]
        )

    def test_repeated_method_rejected(self):
        spec = _spec(rows=[_row("external-visual", 30), _row("external-visual", 12)])
        with self.assertRaises(ValueError):
            assess_microcircuit_test_matrix(spec)

    def test_burn_in_rate_holds_a_clean_matrix(self):
        spec = _spec(burn_in={"devices_entered": 200, "failures": 20, "allowable_percent": 5.0})
        result = assess_microcircuit_test_matrix(spec)
        self.assertFalse(result["accepted"])
        self.assertEqual(result["rejecting_rows"], [])

    def test_challenged_exclusion_is_reported_on_an_accepted_lot(self):
        spec = _spec(
            burn_in={
                "devices_entered": 200,
                "failures": 8,
                "allowable_percent": 5.0,
                "excluded_failures": 6,
            }
        )
        result = assess_microcircuit_test_matrix(spec)
        self.assertTrue(result["accepted"])
        self.assertTrue(any("excluded as handling damage" in item for item in result["findings"]))

    def test_drift_reject_holds_the_lot(self):
        spec = _spec(drift={"readings": [(10.0, 12.0)], "delta_limit_percent": 5.0})
        result = assess_microcircuit_test_matrix(spec)
        self.assertFalse(result["accepted"])
        self.assertTrue(any("drifted past" in item for item in result["findings"]))

    def test_missing_temperature_point_holds_the_lot(self):
        result = assess_microcircuit_test_matrix(_spec(electrical_points=["room"]))
        self.assertFalse(result["accepted"])
        self.assertTrue(any("missing the" in item for item in result["findings"]))

    def test_short_life_test_holds_the_lot(self):
        spec = _spec(
            life_test={
                "hours_completed": 500.0,
                "hours_required": 1000.0,
                "failures": 0,
                "sample_size": 22,
            }
        )
        result = assess_microcircuit_test_matrix(spec)
        self.assertFalse(result["accepted"])
        self.assertTrue(any("stopped" in item for item in result["findings"]))

    def test_missing_rows_key_rejected(self):
        spec = _spec()
        del spec["rows"]
        with self.assertRaises(ValueError):
            assess_microcircuit_test_matrix(spec)

    def test_non_mapping_spec_rejected(self):
        with self.assertRaises(ValueError):
            assess_microcircuit_test_matrix(["not", "a", "mapping"])

    def test_non_mapping_burn_in_block_rejected(self):
        with self.assertRaises(ValueError):
            assess_microcircuit_test_matrix(_spec(burn_in=[200, 4]))

    def test_named_constants_are_representation_sized_or_bounded(self):
        self.assertLess(LIMIT_TOLERANCE, 1e-6)
        self.assertLess(MARGINAL_FRACTION, 1.0)
        self.assertLess(MAX_EXCLUSION_FRACTION, 1.0)


if __name__ == "__main__":
    unittest.main()
