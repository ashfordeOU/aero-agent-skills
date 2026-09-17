"""Contract tests for the Table 8-12 legacy class 2 evaluation list logic.

The cases follow the workflow one step at a time: grouping validation and the
accept-on-zero rule for a consuming grouping, the table sample and the accept
number, the source-lot diversity that makes the result describe a part type,
the currency window and the process change that voids it, and the overall
disposition that carries them. Each step is exercised on both sides of its
limit, so a review of the record shows what was judged and not only the
verdict.
"""

import unittest

from q6013_legacy_class_2_evaluation_table_logic import (
    CONSUMING_SUBGROUPS,
    CURRENCY_WINDOW_MONTHS,
    EVALUATION_SUBGROUPS,
    LIMIT_TOLERANCE,
    MARGINAL_FRACTION,
    MIN_SOURCE_LOTS,
    absent_subgroups,
    assess_legacy_class_2_evaluation,
    evaluation_currency,
    source_lot_diversity,
    subgroup_verdict,
    validate_subgroup,
)


def _entry(subgroup="electrical-characterization", sample_size=22, **extra):
    record = {
        "subgroup": subgroup,
        "sample_size": sample_size,
        "required_sample": extra.pop("required_sample", 22),
    }
    record.update(extra)
    return record


def _spec(**overrides):
    spec = {
        "subgroups": [
            _entry("construction-analysis", 4, required_sample=4),
            _entry("electrical-characterization", 22, required_sample=22,
                   accept_number=1),
            _entry("environmental-mechanical", 10, required_sample=10),
            _entry("endurance", 12, required_sample=12),
        ],
        "source_lots": ["2419", "2504"],
        "evaluation_age_months": 18.0,
    }
    spec.update(overrides)
    return spec


class SubgroupValidationTests(unittest.TestCase):
    def test_valid_grouping_is_normalised(self):
        record = validate_subgroup(_entry("electrical-characterization", 30,
                                          required_sample=22, accept_number=2))
        self.assertEqual(record["sample_size"], 30)
        self.assertEqual(record["accept_number"], 2)
        self.assertEqual(record["sample_shortfall"], 0)

    def test_consuming_grouping_is_marked_without_an_override(self):
        record = validate_subgroup(_entry("construction-analysis", 4,
                                          required_sample=4))
        self.assertTrue(record["consuming"])

    def test_non_consuming_grouping_is_not_marked(self):
        record = validate_subgroup(_entry("electrical-characterization", 22,
                                          required_sample=22))
        self.assertFalse(record["consuming"])

    def test_accept_number_above_zero_on_a_consuming_grouping_is_refused(self):
        with self.assertRaises(ValueError):
            validate_subgroup(_entry("endurance", 12, required_sample=12,
                                     accept_number=1))

    def test_grouping_outside_the_table_set_is_refused(self):
        with self.assertRaises(ValueError):
            validate_subgroup(_entry("radiation-characterization", 6,
                                     required_sample=6))

    def test_accept_number_above_the_sample_is_refused(self):
        with self.assertRaises(ValueError):
            validate_subgroup(_entry("electrical-characterization", 5,
                                     required_sample=5, accept_number=6))

    def test_more_failures_than_devices_sampled_is_refused(self):
        with self.assertRaises(ValueError):
            validate_subgroup(_entry("electrical-characterization", 5,
                                     required_sample=5, failures=6))

    def test_zero_sample_is_refused(self):
        with self.assertRaises(ValueError):
            validate_subgroup(_entry("electrical-characterization", 0,
                                     required_sample=22))

    def test_non_mapping_entry_is_refused(self):
        with self.assertRaises(ValueError):
            validate_subgroup(["electrical-characterization", 22])

    def test_missing_required_key_is_refused(self):
        entry = _entry()
        del entry["required_sample"]
        with self.assertRaises(ValueError):
            validate_subgroup(entry)

    def test_boolean_sample_size_is_refused(self):
        with self.assertRaises(ValueError):
            validate_subgroup(_entry("electrical-characterization", True,
                                     required_sample=22))


class SubgroupVerdictTests(unittest.TestCase):
    def test_sample_shortfall_rejects_the_grouping(self):
        record = subgroup_verdict(_entry("endurance", 8, required_sample=12))
        self.assertEqual(record["sample_shortfall"], 4)
        self.assertFalse(record["accepted"])

    def test_failures_within_the_accept_number_are_accepted(self):
        record = subgroup_verdict(_entry("electrical-characterization", 22,
                                         required_sample=22, accept_number=2,
                                         failures=2))
        self.assertTrue(record["accepted"])

    def test_failures_past_the_accept_number_reject(self):
        record = subgroup_verdict(_entry("electrical-characterization", 22,
                                         required_sample=22, accept_number=1,
                                         failures=2))
        self.assertFalse(record["within_accept_number"])

    def test_one_failure_rejects_a_consuming_grouping(self):
        record = subgroup_verdict(_entry("construction-analysis", 4,
                                         required_sample=4, failures=1))
        self.assertFalse(record["accepted"])

    def test_allowance_used_lands_exactly_on_the_marginal_fraction(self):
        record = subgroup_verdict(_entry("electrical-characterization", 22,
                                         required_sample=22, accept_number=5,
                                         failures=4))
        self.assertAlmostEqual(record["allowance_used"], MARGINAL_FRACTION,
                               places=9)
        self.assertTrue(record["marginal"])
        self.assertTrue(record["accepted"])

    def test_a_grouping_below_the_marginal_fraction_is_not_flagged(self):
        record = subgroup_verdict(_entry("electrical-characterization", 22,
                                         required_sample=22, accept_number=5,
                                         failures=1))
        self.assertFalse(record["marginal"])


class SourceLotTests(unittest.TestCase):
    def test_repeated_date_codes_collapse_to_one_lot(self):
        result = source_lot_diversity(["2419", "2419", "2419"])
        self.assertEqual(result["distinct_lots"], 1)
        self.assertFalse(result["accepted"])

    def test_two_distinct_lots_meet_the_requirement(self):
        result = source_lot_diversity(["2419", "2504"])
        self.assertEqual(result["distinct_lots"], MIN_SOURCE_LOTS)
        self.assertTrue(result["accepted"])

    def test_empty_source_lot_list_is_refused(self):
        with self.assertRaises(ValueError):
            source_lot_diversity([])

    def test_non_string_date_code_is_refused(self):
        with self.assertRaises(ValueError):
            source_lot_diversity(["2419", 2504])


class CurrencyTests(unittest.TestCase):
    def test_age_exactly_on_the_window_stays_inside_it(self):
        result = evaluation_currency(CURRENCY_WINDOW_MONTHS)
        self.assertAlmostEqual(result["age_months"], CURRENCY_WINDOW_MONTHS,
                               places=9)
        self.assertTrue(result["within_window"])
        self.assertTrue(result["accepted"])

    def test_age_past_the_window_reports_the_overrun(self):
        result = evaluation_currency(CURRENCY_WINDOW_MONTHS + 6.0)
        self.assertFalse(result["within_window"])
        self.assertAlmostEqual(result["overrun_months"], 6.0, places=9)

    def test_process_change_voids_a_young_evaluation(self):
        result = evaluation_currency(4.0, process_change_since=True)
        self.assertTrue(result["within_window"])
        self.assertFalse(result["accepted"])

    def test_negative_age_is_refused(self):
        with self.assertRaises(ValueError):
            evaluation_currency(-1.0)

    def test_non_boolean_process_change_is_refused(self):
        with self.assertRaises(ValueError):
            evaluation_currency(10.0, process_change_since="yes")


class AbsentSubgroupTests(unittest.TestCase):
    def test_a_complete_set_leaves_nothing_absent(self):
        self.assertEqual(absent_subgroups(list(EVALUATION_SUBGROUPS)), ())

    def test_absent_groupings_are_named(self):
        missing = absent_subgroups(["construction-analysis"])
        self.assertIn("endurance", missing)
        self.assertEqual(len(missing), len(EVALUATION_SUBGROUPS) - 1)

    def test_non_list_names_are_refused(self):
        with self.assertRaises(ValueError):
            absent_subgroups("construction-analysis")


class AssessmentTests(unittest.TestCase):
    def test_a_complete_clean_campaign_evaluates_the_part_type(self):
        result = assess_legacy_class_2_evaluation(_spec())
        self.assertTrue(result["accepted"])
        self.assertEqual(result["disposition"], "part-type-evaluated")
        self.assertEqual(result["findings"], [])

    def test_a_skipped_grouping_is_named_and_holds_the_part_type(self):
        spec = _spec()
        spec["subgroups"] = spec["subgroups"][:3]
        result = assess_legacy_class_2_evaluation(spec)
        self.assertIn("endurance", result["absent_subgroups"])
        self.assertEqual(result["disposition"], "repeat-evaluation")

    def test_a_single_date_code_holds_an_otherwise_clean_campaign(self):
        result = assess_legacy_class_2_evaluation(_spec(source_lots=["2419"]))
        self.assertFalse(result["accepted"])
        self.assertTrue(
            any("production lot" in item for item in result["findings"])
        )

    def test_an_expired_record_holds_the_part_type(self):
        result = assess_legacy_class_2_evaluation(
            _spec(evaluation_age_months=CURRENCY_WINDOW_MONTHS + 12.0)
        )
        self.assertFalse(result["accepted"])
        self.assertTrue(
            any("currency window" in item for item in result["findings"])
        )

    def test_a_declared_process_change_holds_a_young_clean_record(self):
        result = assess_legacy_class_2_evaluation(
            _spec(process_change_since=True)
        )
        self.assertFalse(result["accepted"])
        self.assertTrue(
            any("process change" in item for item in result["findings"])
        )

    def test_a_rejecting_grouping_is_reported_by_name(self):
        spec = _spec()
        spec["subgroups"][3] = _entry("endurance", 12, required_sample=12,
                                      failures=1)
        result = assess_legacy_class_2_evaluation(spec)
        self.assertEqual(result["rejecting_subgroups"], ["endurance"])

    def test_a_marginal_grouping_still_passes_but_is_reported(self):
        spec = _spec()
        spec["subgroups"][1] = _entry("electrical-characterization", 22,
                                      required_sample=22, accept_number=5,
                                      failures=4)
        result = assess_legacy_class_2_evaluation(spec)
        self.assertTrue(result["accepted"])
        self.assertIn("electrical-characterization", result["marginal_subgroups"])

    def test_a_repeated_grouping_is_refused(self):
        spec = _spec()
        spec["subgroups"].append(_entry("endurance", 12, required_sample=12))
        with self.assertRaises(ValueError):
            assess_legacy_class_2_evaluation(spec)

    def test_missing_source_lots_key_is_refused(self):
        spec = _spec()
        del spec["source_lots"]
        with self.assertRaises(ValueError):
            assess_legacy_class_2_evaluation(spec)

    def test_empty_subgroup_list_is_refused(self):
        with self.assertRaises(ValueError):
            assess_legacy_class_2_evaluation(_spec(subgroups=[]))

    def test_non_mapping_spec_is_refused(self):
        with self.assertRaises(ValueError):
            assess_legacy_class_2_evaluation(["not", "a", "mapping"])

    def test_named_constants_are_representation_sized_or_bounded(self):
        self.assertLess(LIMIT_TOLERANCE, 1e-6)
        self.assertLess(MARGINAL_FRACTION, 1.0)
        self.assertGreaterEqual(MIN_SOURCE_LOTS, 2)
        self.assertEqual(len(EVALUATION_SUBGROUPS), 4)
        self.assertTrue(
            set(CONSUMING_SUBGROUPS).issubset(set(EVALUATION_SUBGROUPS))
        )


if __name__ == "__main__":
    unittest.main()
