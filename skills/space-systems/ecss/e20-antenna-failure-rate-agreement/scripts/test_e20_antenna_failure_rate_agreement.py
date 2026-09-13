#!/usr/bin/env python3
"""Contract test for e20-antenna-failure-rate-agreement (stdlib unittest)."""

import math
import unittest

from e20_antenna_failure_rate_agreement_logic import (
    FIT_TO_PER_HOUR,
    assess_antenna,
    assess_antenna_set,
    categorize_redundancy,
    failure_rate_within_specified,
    grade_demonstration_evidence,
    reliability_from_failure_rate,
    series_reliability,
    validate_failure_rate_record,
)

GOOD_RECORD = {
    "specified_fit": 120.0,
    "demonstrated_fit": 95.0,
    "evidence": "test",
    "customer_agreed": True,
    "baseline_specified": True,
}


def good_item(**overrides):
    item = {
        "id": "x-band-data-antenna",
        "redundancy_scheme": "none",
        "causes_loss_of_function": True,
        "failure_rate": dict(GOOD_RECORD),
    }
    item.update(overrides)
    return item


class TestRedundancyCategorization(unittest.TestCase):
    def test_non_redundant_with_loss_is_single_point_failure(self):
        self.assertEqual(
            categorize_redundancy("none", True), "single-point-failure"
        )

    def test_single_string_synonym_is_single_point_failure(self):
        self.assertEqual(
            categorize_redundancy("single-string", True), "single-point-failure"
        )

    def test_non_redundant_without_loss_is_tolerated(self):
        self.assertEqual(
            categorize_redundancy("none", False), "non-redundant-tolerated"
        )

    def test_cross_strapped_is_redundant_even_when_function_critical(self):
        self.assertEqual(categorize_redundancy("cross-strapped", True), "redundant")

    def test_scheme_is_case_and_whitespace_insensitive(self):
        self.assertEqual(categorize_redundancy("  Cold-Standby ", True), "redundant")

    def test_unknown_scheme_raises(self):
        with self.assertRaises(ValueError):
            categorize_redundancy("dual-wound", True)

    def test_empty_scheme_raises(self):
        with self.assertRaises(ValueError):
            categorize_redundancy("   ", True)

    def test_non_boolean_loss_flag_raises(self):
        with self.assertRaises(ValueError):
            categorize_redundancy("none", "yes")


class TestEvidenceGrading(unittest.TestCase):
    def test_test_route_outranks_heritage(self):
        self.assertGreater(
            grade_demonstration_evidence("test"),
            grade_demonstration_evidence("in-orbit-heritage"),
        )

    def test_analysis_is_the_weakest_route(self):
        self.assertEqual(grade_demonstration_evidence("analysis"), 1)

    def test_unknown_route_raises(self):
        with self.assertRaises(ValueError):
            grade_demonstration_evidence("engineering-judgement")


class TestRecordValidation(unittest.TestCase):
    def test_valid_record_normalizes(self):
        record = validate_failure_rate_record(dict(GOOD_RECORD))
        self.assertAlmostEqual(record["specified_fit"], 120.0)
        self.assertAlmostEqual(record["demonstrated_fit"], 95.0)
        self.assertEqual(record["evidence"], "test")
        self.assertTrue(record["customer_agreed"])

    def test_absent_flags_default_to_not_agreed(self):
        record = validate_failure_rate_record({"specified_fit": 50.0})
        self.assertFalse(record["customer_agreed"])
        self.assertFalse(record["baseline_specified"])
        self.assertIsNone(record["demonstrated_fit"])

    def test_missing_specified_rate_raises(self):
        with self.assertRaises(ValueError):
            validate_failure_rate_record({"demonstrated_fit": 10.0})

    def test_zero_specified_rate_raises(self):
        with self.assertRaises(ValueError):
            validate_failure_rate_record({"specified_fit": 0.0})

    def test_negative_demonstrated_rate_raises(self):
        with self.assertRaises(ValueError):
            validate_failure_rate_record(
                {"specified_fit": 50.0, "demonstrated_fit": -1.0}
            )

    def test_non_numeric_rate_raises(self):
        with self.assertRaises(ValueError):
            validate_failure_rate_record({"specified_fit": "low"})

    def test_non_mapping_record_raises(self):
        with self.assertRaises(ValueError):
            validate_failure_rate_record([120.0])

    def test_unknown_evidence_in_record_raises(self):
        with self.assertRaises(ValueError):
            validate_failure_rate_record(
                {"specified_fit": 50.0, "evidence": "hearsay"}
            )


class TestRateComparison(unittest.TestCase):
    def test_demonstrated_below_specified_passes(self):
        self.assertTrue(failure_rate_within_specified(95.0, 120.0))

    def test_demonstrated_above_specified_fails(self):
        self.assertFalse(failure_rate_within_specified(140.0, 120.0))

    def test_exact_boundary_sum_of_parts_is_compliant(self):
        # 0.1 + 0.2 lands a few ULPs above 0.3 in binary floating point; a
        # part-count that exactly meets the specified rate stays compliant.
        self.assertTrue(failure_rate_within_specified(0.1 + 0.2, 0.3))

    def test_comparison_rejects_zero_specified_rate(self):
        with self.assertRaises(ValueError):
            failure_rate_within_specified(10.0, 0.0)


class TestReliability(unittest.TestCase):
    def test_survival_matches_closed_form(self):
        value = reliability_from_failure_rate(1000.0, 87600.0)
        self.assertAlmostEqual(value, math.exp(-1000.0 * FIT_TO_PER_HOUR * 87600.0))

    def test_zero_failure_rate_survives(self):
        self.assertAlmostEqual(reliability_from_failure_rate(0.0, 50000.0), 1.0)

    def test_longer_mission_lowers_survival(self):
        short = reliability_from_failure_rate(500.0, 10000.0)
        long = reliability_from_failure_rate(500.0, 90000.0)
        self.assertLess(long, short)

    def test_zero_mission_hours_raises(self):
        with self.assertRaises(ValueError):
            reliability_from_failure_rate(500.0, 0.0)

    def test_negative_failure_rate_raises(self):
        with self.assertRaises(ValueError):
            reliability_from_failure_rate(-5.0, 10000.0)

    def test_series_chain_matches_summed_rate(self):
        chain = series_reliability([100.0, 250.0], 87600.0)
        lumped = reliability_from_failure_rate(350.0, 87600.0)
        self.assertAlmostEqual(chain, lumped, places=12)

    def test_empty_chain_raises(self):
        with self.assertRaises(ValueError):
            series_reliability([], 87600.0)

    def test_non_sequence_chain_raises(self):
        with self.assertRaises(ValueError):
            series_reliability(250.0, 87600.0)


class TestSingleAntennaAssessment(unittest.TestCase):
    def test_fully_agreed_antenna_is_compliant(self):
        result = assess_antenna(good_item(), 87600.0)
        self.assertTrue(result["compliant"])
        self.assertEqual(result["findings"], [])
        self.assertTrue(result["applicable"])
        self.assertAlmostEqual(result["effective_fit"], 95.0)

    def test_redundant_antenna_is_outside_the_obligation(self):
        result = assess_antenna(
            good_item(redundancy_scheme="cross-strapped", failure_rate=None), 87600.0
        )
        self.assertFalse(result["applicable"])
        self.assertTrue(result["compliant"])
        self.assertIsNone(result["reliability"])

    def test_missing_record_on_single_point_failure_is_a_finding(self):
        result = assess_antenna(good_item(failure_rate=None), 87600.0)
        self.assertFalse(result["compliant"])
        self.assertEqual(len(result["findings"]), 1)

    def test_unagreed_rate_is_a_finding(self):
        record = dict(GOOD_RECORD)
        record["customer_agreed"] = False
        result = assess_antenna(good_item(failure_rate=record), 87600.0)
        self.assertFalse(result["compliant"])
        self.assertTrue(any("agreed" in f for f in result["findings"]))

    def test_rate_absent_from_the_baseline_is_a_finding(self):
        record = dict(GOOD_RECORD)
        record["baseline_specified"] = False
        result = assess_antenna(good_item(failure_rate=record), 87600.0)
        self.assertTrue(
            any("requirement-baseline" in f for f in result["findings"])
        )

    def test_analysis_only_demonstration_is_a_finding(self):
        record = dict(GOOD_RECORD)
        record["evidence"] = "analysis"
        result = assess_antenna(good_item(failure_rate=record), 87600.0)
        self.assertTrue(any("too weak" in f for f in result["findings"]))

    def test_similarity_demonstration_closes_the_obligation(self):
        record = dict(GOOD_RECORD)
        record["evidence"] = "similarity"
        result = assess_antenna(good_item(failure_rate=record), 87600.0)
        self.assertTrue(result["compliant"])

    def test_absent_evidence_and_absent_demonstrated_rate_raise_two_findings(self):
        record = {
            "specified_fit": 120.0,
            "customer_agreed": True,
            "baseline_specified": True,
        }
        result = assess_antenna(good_item(failure_rate=record), 87600.0)
        self.assertEqual(len(result["findings"]), 2)
        self.assertAlmostEqual(result["effective_fit"], 120.0)

    def test_demonstrated_rate_over_specified_is_a_finding(self):
        record = dict(GOOD_RECORD)
        record["demonstrated_fit"] = 400.0
        result = assess_antenna(good_item(failure_rate=record), 87600.0)
        self.assertTrue(any("exceeds" in f for f in result["findings"]))

    def test_reliability_below_allocated_floor_is_a_finding(self):
        result = assess_antenna(
            good_item(min_reliability=0.999999), 87600.0
        )
        self.assertTrue(any("allocated floor" in f for f in result["findings"]))

    def test_reliability_exactly_at_its_floor_is_compliant(self):
        floor = math.exp(-95.0 * FIT_TO_PER_HOUR * 87600.0)
        result = assess_antenna(good_item(min_reliability=floor), 87600.0)
        self.assertTrue(result["compliant"])

    def test_missing_identifier_raises(self):
        item = good_item()
        del item["id"]
        with self.assertRaises(ValueError):
            assess_antenna(item, 87600.0)

    def test_non_mapping_item_raises(self):
        with self.assertRaises(ValueError):
            assess_antenna("x-band-antenna", 87600.0)

    def test_negative_mission_hours_raises(self):
        with self.assertRaises(ValueError):
            assess_antenna(good_item(), -10.0)


class TestAntennaSetAssessment(unittest.TestCase):
    def test_compliant_set_rolls_up_clean(self):
        items = [
            good_item(),
            good_item(id="s-band-telecommand-antenna"),
        ]
        summary = assess_antenna_set(items, 87600.0, 0.98)
        self.assertTrue(summary["compliant"])
        self.assertEqual(summary["single_point_failure_count"], 2)
        self.assertTrue(summary["allocation_met"])

    def test_chain_reliability_is_the_product_of_its_items(self):
        items = [good_item(), good_item(id="s-band-telecommand-antenna")]
        summary = assess_antenna_set(items, 87600.0, 0.5)
        expected = reliability_from_failure_rate(
            95.0, 87600.0
        ) * reliability_from_failure_rate(95.0, 87600.0)
        self.assertAlmostEqual(summary["series_reliability"], expected, places=12)

    def test_allocation_exactly_met_by_the_lumped_rate_is_compliant(self):
        # The chain multiplies two exponentials while the allocation is the
        # single exponential of the summed rate; the two differ by a few ULPs
        # and the physically compliant case must still read as met.
        items = [good_item(), good_item(id="s-band-telecommand-antenna")]
        allocation = reliability_from_failure_rate(190.0, 87600.0)
        summary = assess_antenna_set(items, 87600.0, allocation)
        self.assertTrue(summary["allocation_met"])
        self.assertTrue(summary["compliant"])

    def test_allocation_miss_is_reported(self):
        items = [good_item(failure_rate={
            "specified_fit": 900000.0,
            "demonstrated_fit": 900000.0,
            "evidence": "test",
            "customer_agreed": True,
            "baseline_specified": True,
        })]
        summary = assess_antenna_set(items, 87600.0, 0.999)
        self.assertFalse(summary["allocation_met"])
        self.assertFalse(summary["compliant"])

    def test_redundant_items_stay_out_of_the_chain(self):
        items = [
            good_item(),
            good_item(id="ka-band-antenna", redundancy_scheme="hot-standby"),
        ]
        summary = assess_antenna_set(items, 87600.0, 0.5)
        self.assertEqual(summary["single_point_failure_count"], 1)
        self.assertAlmostEqual(
            summary["series_reliability"],
            reliability_from_failure_rate(95.0, 87600.0),
            places=12,
        )

    def test_set_without_single_point_failures_has_unity_chain(self):
        items = [good_item(redundancy_scheme="cross-strapped")]
        summary = assess_antenna_set(items, 87600.0, 0.99)
        self.assertAlmostEqual(summary["series_reliability"], 1.0)
        self.assertTrue(summary["compliant"])

    def test_duplicate_identifier_raises(self):
        with self.assertRaises(ValueError):
            assess_antenna_set([good_item(), good_item()], 87600.0, 0.9)

    def test_empty_set_raises(self):
        with self.assertRaises(ValueError):
            assess_antenna_set([], 87600.0, 0.9)

    def test_allocation_above_unity_raises(self):
        with self.assertRaises(ValueError):
            assess_antenna_set([good_item()], 87600.0, 1.5)

    def test_zero_allocation_raises(self):
        with self.assertRaises(ValueError):
            assess_antenna_set([good_item()], 87600.0, 0.0)


if __name__ == "__main__":
    unittest.main()
