"""Contract tests for the clause 4.3.5 date-code lot acceptance logic.

The cases follow the workflow one step at a time: date-code resolution,
sample validation, the subgroup accept-number and percent-defective gate,
the parameter-drift checklist, and the disposition that stops a lot short
of flight release. Each step is exercised on both sides of its limit, so
a review of the record shows what was judged and not only the verdict.
"""

import unittest

from q6013_class_1_lot_acceptance_logic import (
    ACCEPTANCE_TOLERANCE,
    MARGINAL_FRACTION,
    assess_lot_acceptance,
    lot_date_code,
    parameter_drift_rejects,
    percent_defective,
    subgroup_verdict,
    validate_date_code,
    validate_sample,
)


def _subgroup(name="burn-in", sample_size=45, failures=0, **extra):
    record = {"name": name, "sample_size": sample_size, "failures": failures}
    record.update(extra)
    return record


def _spec(**overrides):
    spec = {
        "date_code": "2537",
        "lot_size": 500,
        "allowable_percent": 5.0,
        "subgroups": [
            _subgroup("burn-in", 45, 0, accept_number=1),
            _subgroup("electrical-end-points", 22, 0, accept_number=1),
        ],
    }
    spec.update(overrides)
    return spec


class DateCodeTests(unittest.TestCase):
    def test_parses_year_and_week(self):
        self.assertEqual(validate_date_code("2537"), (25, 37))

    def test_week_fifty_three_admissible(self):
        self.assertEqual(validate_date_code("2453"), (24, 53))

    def test_week_zero_rejected(self):
        with self.assertRaises(ValueError):
            validate_date_code("2500")

    def test_week_above_fifty_three_rejected(self):
        with self.assertRaises(ValueError):
            validate_date_code("2554")

    def test_non_numeric_code_rejected(self):
        with self.assertRaises(ValueError):
            validate_date_code("25W7")

    def test_wrong_length_code_rejected(self):
        with self.assertRaises(ValueError):
            validate_date_code("253")

    def test_non_string_code_rejected(self):
        with self.assertRaises(ValueError):
            validate_date_code(2537)

    def test_single_code_returned_for_homogeneous_lot(self):
        self.assertEqual(lot_date_code(["2537", "2537", "2537"]), "2537")

    def test_mixed_date_codes_refused(self):
        with self.assertRaises(ValueError):
            lot_date_code(["2537", "2538"])

    def test_empty_code_list_refused(self):
        with self.assertRaises(ValueError):
            lot_date_code([])


class SampleTests(unittest.TestCase):
    def test_valid_sample_returned_as_pair(self):
        self.assertEqual(validate_sample(500, 45), (500, 45))

    def test_full_lot_sample_admissible(self):
        self.assertEqual(validate_sample(12, 12), (12, 12))

    def test_sample_larger_than_lot_rejected(self):
        with self.assertRaises(ValueError):
            validate_sample(30, 31)

    def test_zero_sample_rejected(self):
        with self.assertRaises(ValueError):
            validate_sample(30, 0)

    def test_non_integer_sample_rejected(self):
        with self.assertRaises(ValueError):
            validate_sample(30, 5.0)

    def test_percent_defective_is_exact_for_round_ratio(self):
        self.assertAlmostEqual(percent_defective(2, 50), 4.0, places=9)

    def test_percent_defective_rejects_more_failures_than_units(self):
        with self.assertRaises(ValueError):
            percent_defective(6, 5)


class SubgroupVerdictTests(unittest.TestCase):
    def test_zero_failures_accepts(self):
        record = subgroup_verdict(_subgroup(failures=0, accept_number=1), 500, 5.0)
        self.assertTrue(record["accepted"])
        self.assertFalse(record["marginal"])

    def test_failures_over_accept_number_reject(self):
        record = subgroup_verdict(_subgroup(sample_size=45, failures=2, accept_number=1), 500, 50.0)
        self.assertFalse(record["accepted"])
        self.assertFalse(record["within_accept_number"])

    def test_accept_number_met_exactly_accepts(self):
        record = subgroup_verdict(_subgroup(sample_size=50, failures=1, accept_number=1), 500, 5.0)
        self.assertTrue(record["within_accept_number"])
        self.assertTrue(record["accepted"])

    def test_percent_defective_equal_to_allowance_accepts(self):
        record = subgroup_verdict(_subgroup(sample_size=20, failures=1, accept_number=5), 500, 5.0)
        self.assertAlmostEqual(record["percent_defective"], 5.0, places=9)
        self.assertTrue(record["within_allowance"])
        self.assertTrue(record["accepted"])

    def test_percent_defective_over_allowance_rejects(self):
        record = subgroup_verdict(_subgroup(sample_size=20, failures=2, accept_number=5), 500, 5.0)
        self.assertFalse(record["within_allowance"])
        self.assertFalse(record["accepted"])

    def test_marginal_flag_raised_near_the_allowance(self):
        record = subgroup_verdict(_subgroup(sample_size=25, failures=1, accept_number=3), 500, 5.0)
        # 100*1/25 and MARGINAL_FRACTION*5.0 are both exactly 4.0: IEEE-754
        # multiply and divide are correctly rounded, so this subgroup sits ON
        # the marginal trigger, on every platform, rather than near it.
        self.assertEqual(record["percent_defective"], 4.0)
        self.assertEqual(MARGINAL_FRACTION * 5.0, 4.0)
        self.assertTrue(record["marginal"])

    def test_subgroup_without_name_rejected(self):
        bad = {"sample_size": 10, "failures": 0}
        with self.assertRaises(ValueError):
            subgroup_verdict(bad, 500, 5.0)

    def test_allowance_outside_percentage_range_rejected(self):
        with self.assertRaises(ValueError):
            subgroup_verdict(_subgroup(), 500, 140.0)

    def test_subgroup_override_allowance_used(self):
        record = subgroup_verdict(
            _subgroup(sample_size=20, failures=1, accept_number=5, allowable_percent=2.0), 500, 50.0
        )
        self.assertFalse(record["accepted"])


class DriftTests(unittest.TestCase):
    def test_no_drift_accepts(self):
        result = parameter_drift_rejects([(1.0, 1.0), (2.0, 2.0)], 10.0)
        self.assertTrue(result["accepted"])
        self.assertEqual(result["rejects"], 0)

    def test_drift_exactly_on_limit_accepts(self):
        result = parameter_drift_rejects([(100.0, 110.0)], 10.0)
        self.assertAlmostEqual(result["worst_drift_percent"], 10.0, places=9)
        self.assertTrue(result["accepted"])

    def test_drift_past_limit_rejects_that_unit(self):
        result = parameter_drift_rejects([(100.0, 100.5), (100.0, 120.0)], 10.0)
        self.assertEqual(result["reject_indices"], [1])
        self.assertFalse(result["accepted"])

    def test_negative_drift_counted_on_magnitude(self):
        result = parameter_drift_rejects([(100.0, 80.0)], 10.0)
        self.assertAlmostEqual(result["worst_drift_percent"], 20.0, places=9)
        self.assertFalse(result["accepted"])

    def test_zero_initial_reading_rejected(self):
        with self.assertRaises(ValueError):
            parameter_drift_rejects([(0.0, 1.0)], 10.0)

    def test_negative_limit_rejected(self):
        with self.assertRaises(ValueError):
            parameter_drift_rejects([(1.0, 1.0)], -1.0)

    def test_malformed_reading_rejected(self):
        with self.assertRaises(ValueError):
            parameter_drift_rejects([(1.0,)], 10.0)


class AssessmentTests(unittest.TestCase):
    def test_clean_lot_released(self):
        result = assess_lot_acceptance(_spec())
        self.assertTrue(result["accepted"])
        self.assertEqual(result["disposition"], "release-for-flight")
        self.assertEqual(result["date_code"], "2537")
        self.assertEqual(result["findings"], [])

    def test_one_rejecting_subgroup_holds_the_lot(self):
        spec = _spec(
            subgroups=[
                _subgroup("burn-in", 45, 0, accept_number=1),
                _subgroup("electrical-end-points", 22, 3, accept_number=1),
            ]
        )
        result = assess_lot_acceptance(spec)
        self.assertFalse(result["accepted"])
        self.assertEqual(result["disposition"], "hold-lot")
        self.assertEqual(result["rejecting_subgroups"], ["electrical-end-points"])

    def test_subgroups_are_not_averaged_away(self):
        spec = _spec(
            subgroups=[
                _subgroup("burn-in", 100, 0, accept_number=0),
                _subgroup("life-test", 10, 1, accept_number=0),
            ]
        )
        result = assess_lot_acceptance(spec)
        self.assertFalse(result["accepted"])

    def test_drift_reject_holds_an_otherwise_clean_lot(self):
        spec = _spec(drift_readings=[(100.0, 140.0)], drift_limit_percent=10.0)
        result = assess_lot_acceptance(spec)
        self.assertFalse(result["accepted"])
        self.assertTrue(any("drifted" in item for item in result["findings"]))

    def test_drift_readings_without_limit_rejected(self):
        with self.assertRaises(ValueError):
            assess_lot_acceptance(_spec(drift_readings=[(1.0, 1.0)]))

    def test_mixed_date_code_delivery_rejected(self):
        with self.assertRaises(ValueError):
            assess_lot_acceptance(_spec(date_codes=["2537", "2601"]))

    def test_missing_subgroups_rejected(self):
        spec = _spec()
        del spec["subgroups"]
        with self.assertRaises(ValueError):
            assess_lot_acceptance(spec)

    def test_empty_subgroup_list_rejected(self):
        with self.assertRaises(ValueError):
            assess_lot_acceptance(_spec(subgroups=[]))

    def test_non_mapping_spec_rejected(self):
        with self.assertRaises(ValueError):
            assess_lot_acceptance(["not", "a", "mapping"])

    def test_marginal_lot_reported_but_still_released(self):
        spec = _spec(
            subgroups=[_subgroup("burn-in", 25, 1, accept_number=3)],
            allowable_percent=5.0,
        )
        result = assess_lot_acceptance(spec)
        self.assertTrue(result["accepted"])
        self.assertTrue(any("little margin" in item for item in result["findings"]))

    def test_tolerance_is_representation_sized_only(self):
        self.assertLess(ACCEPTANCE_TOLERANCE, 1e-6)


if __name__ == "__main__":
    unittest.main()
