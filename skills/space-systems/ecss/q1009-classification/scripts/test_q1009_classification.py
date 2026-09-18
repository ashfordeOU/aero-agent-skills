"""Contract tests for the clause 5.2.2.2 severity categorization logic."""

import unittest

from q1009_classification_logic import (
    CUMULATIVE_TOLERANCE,
    DEFAULT_CUMULATIVE_LIMIT,
    DEFAULT_MINOR_COUNT_LIMIT,
    MAJOR_CRITERIA,
    assess_categorization,
    categorize_nonconformance,
    cumulative_assessment,
    cumulative_consumption,
    group_by_item,
    normalize_criterion,
    triggered_criteria,
    validate_consumption,
    validate_nonconformance,
)


def nc(ident, item="su-0007", consumption=0.0, **flags):
    criteria = {c: False for c in MAJOR_CRITERIA}
    for key, value in flags.items():
        criteria[key.replace("_", "-")] = value
    return {"id": ident, "item": item, "criteria": criteria, "consumption": consumption}


class NormalizeCriterionTests(unittest.TestCase):
    def test_canonical_name_passes_through(self):
        self.assertEqual(normalize_criterion("safety"), "safety")

    def test_spaces_and_case_normalised(self):
        self.assertEqual(normalize_criterion("Operational Use"), "operational-use")

    def test_underscores_normalised(self):
        self.assertEqual(normalize_criterion("qualification_validity"), "qualification-validity")

    def test_unknown_criterion_rejected(self):
        with self.assertRaises(ValueError):
            normalize_criterion("looks-untidy")

    def test_empty_criterion_rejected(self):
        with self.assertRaises(ValueError):
            normalize_criterion("  ")

    def test_non_string_criterion_rejected(self):
        with self.assertRaises(ValueError):
            normalize_criterion(None)


class ConsumptionTests(unittest.TestCase):
    def test_share_returned_as_float(self):
        self.assertAlmostEqual(validate_consumption(0.25), 0.25, places=9)

    def test_zero_share_allowed(self):
        self.assertAlmostEqual(validate_consumption(0), 0.0, places=9)

    def test_whole_margin_allowed(self):
        self.assertAlmostEqual(validate_consumption(1), 1.0, places=9)

    def test_negative_share_rejected(self):
        with self.assertRaises(ValueError):
            validate_consumption(-0.1)

    def test_share_above_one_rejected(self):
        with self.assertRaises(ValueError):
            validate_consumption(1.2)

    def test_boolean_share_rejected(self):
        with self.assertRaises(ValueError):
            validate_consumption(True)

    def test_non_finite_share_rejected(self):
        with self.assertRaises(ValueError):
            validate_consumption(float("nan"))


class ValidationTests(unittest.TestCase):
    def test_record_normalised(self):
        record = validate_nonconformance(nc("NCR 0101", item="SU 0007"))
        self.assertEqual(record["id"], "ncr-0101")
        self.assertEqual(record["item"], "su-0007")

    def test_missing_key_rejected(self):
        bad = nc("ncr-0101")
        del bad["item"]
        with self.assertRaises(ValueError):
            validate_nonconformance(bad)

    def test_unanswered_criterion_rejected(self):
        bad = nc("ncr-0101")
        del bad["criteria"]["interface"]
        with self.assertRaises(ValueError):
            validate_nonconformance(bad)

    def test_non_boolean_answer_rejected(self):
        bad = nc("ncr-0101")
        bad["criteria"]["safety"] = "no"
        with self.assertRaises(ValueError):
            validate_nonconformance(bad)

    def test_unknown_criterion_key_rejected(self):
        bad = nc("ncr-0101")
        bad["criteria"]["looks-untidy"] = False
        with self.assertRaises(ValueError):
            validate_nonconformance(bad)

    def test_criteria_must_be_a_mapping(self):
        bad = nc("ncr-0101")
        bad["criteria"] = list(MAJOR_CRITERIA)
        with self.assertRaises(ValueError):
            validate_nonconformance(bad)

    def test_consumption_defaults_to_zero(self):
        bare = nc("ncr-0101")
        del bare["consumption"]
        self.assertAlmostEqual(validate_nonconformance(bare)["consumption"], 0.0, places=9)


class CategorizationTests(unittest.TestCase):
    def test_no_criterion_true_is_minor(self):
        self.assertEqual(categorize_nonconformance(nc("ncr-0101"))["category"], "minor")

    def test_single_safety_criterion_is_major(self):
        result = categorize_nonconformance(nc("ncr-0102", safety=True))
        self.assertEqual(result["category"], "major")
        self.assertEqual(result["triggered"], ("safety",))

    def test_interface_alone_is_major(self):
        self.assertEqual(
            categorize_nonconformance(nc("ncr-0103", interface=True))["category"], "major"
        )

    def test_every_criterion_alone_makes_a_major(self):
        for criterion in MAJOR_CRITERIA:
            record = nc("ncr-x")
            record["criteria"][criterion] = True
            self.assertEqual(
                categorize_nonconformance(record)["category"], "major", criterion
            )

    def test_triggered_criteria_follow_reporting_order(self):
        result = triggered_criteria(nc("ncr-0104", interface=True, safety=True))
        self.assertEqual(result, ("safety", "interface"))

    def test_many_false_answers_do_not_offset_one_true(self):
        result = categorize_nonconformance(nc("ncr-0105", qualification_validity=True))
        self.assertEqual(result["category"], "major")

    def test_consumption_carried_onto_the_categorized_record(self):
        result = categorize_nonconformance(nc("ncr-0106", consumption=0.4))
        self.assertAlmostEqual(result["consumption"], 0.4, places=9)


class GroupingTests(unittest.TestCase):
    def test_departures_grouped_by_item(self):
        grouped = group_by_item([nc("a", item="su-1"), nc("b", item="su-2"), nc("c", item="su-1")])
        self.assertEqual([item for item, _ in grouped], ["su-1", "su-2"])
        self.assertEqual(len(grouped[0][1]), 2)

    def test_first_seen_item_order_preserved(self):
        grouped = group_by_item([nc("a", item="su-9"), nc("b", item="su-1")])
        self.assertEqual([item for item, _ in grouped], ["su-9", "su-1"])

    def test_duplicate_nonconformance_id_rejected(self):
        with self.assertRaises(ValueError):
            group_by_item([nc("a"), nc("A")])

    def test_empty_sequence_rejected(self):
        with self.assertRaises(ValueError):
            group_by_item([])

    def test_non_sequence_rejected(self):
        with self.assertRaises(ValueError):
            group_by_item(nc("a"))


class CumulativeTests(unittest.TestCase):
    def test_minor_shares_sum(self):
        records = [categorize_nonconformance(nc("a", consumption=0.3)),
                   categorize_nonconformance(nc("b", consumption=0.4))]
        self.assertAlmostEqual(cumulative_consumption(records), 0.7, places=9)

    def test_major_share_excluded_from_the_minor_sum(self):
        records = [categorize_nonconformance(nc("a", consumption=0.3)),
                   categorize_nonconformance(nc("b", consumption=0.9, safety=True))]
        self.assertAlmostEqual(cumulative_consumption(records), 0.3, places=9)

    def test_group_under_the_limit_stays_minor(self):
        records = [categorize_nonconformance(nc("a", consumption=0.2)),
                   categorize_nonconformance(nc("b", consumption=0.3))]
        verdict = cumulative_assessment(records)
        self.assertEqual(verdict["effective_category"], "minor")
        self.assertFalse(verdict["escalated"])

    def test_exactly_consumed_margin_escalates(self):
        records = [categorize_nonconformance(nc("a", consumption=0.3)),
                   categorize_nonconformance(nc("b", consumption=0.3)),
                   categorize_nonconformance(nc("c", consumption=0.4))]
        verdict = cumulative_assessment(records)
        self.assertAlmostEqual(
            verdict["cumulative_consumption"], DEFAULT_CUMULATIVE_LIMIT, places=9
        )
        self.assertTrue(verdict["escalated"])
        self.assertIn("cumulative-margin-consumed", verdict["escalation_reasons"])

    def test_count_limit_escalates_a_group_of_small_departures(self):
        records = [
            categorize_nonconformance(nc("n%d" % i, consumption=0.01))
            for i in range(DEFAULT_MINOR_COUNT_LIMIT + 1)
        ]
        verdict = cumulative_assessment(records)
        self.assertTrue(verdict["escalated"])
        self.assertIn("minor-count-limit-exceeded", verdict["escalation_reasons"])

    def test_group_at_the_count_limit_does_not_escalate(self):
        records = [
            categorize_nonconformance(nc("n%d" % i, consumption=0.01))
            for i in range(DEFAULT_MINOR_COUNT_LIMIT)
        ]
        self.assertFalse(cumulative_assessment(records)["escalated"])

    def test_group_already_holding_a_major_is_not_an_escalation(self):
        records = [categorize_nonconformance(nc("a", consumption=0.9, safety=True)),
                   categorize_nonconformance(nc("b", consumption=1.0))]
        verdict = cumulative_assessment(records)
        self.assertEqual(verdict["effective_category"], "major")
        self.assertFalse(verdict["escalated"])

    def test_tolerance_is_small_and_positive(self):
        self.assertGreater(CUMULATIVE_TOLERANCE, 0.0)
        self.assertLess(CUMULATIVE_TOLERANCE, 1e-6)

    def test_tighter_limit_escalates_a_group_the_default_would_pass(self):
        records = [categorize_nonconformance(nc("a", consumption=0.3)),
                   categorize_nonconformance(nc("b", consumption=0.3))]
        self.assertFalse(cumulative_assessment(records)["escalated"])
        self.assertTrue(cumulative_assessment(records, limit=0.5)["escalated"])

    def test_zero_limit_rejected(self):
        records = [categorize_nonconformance(nc("a"))]
        with self.assertRaises(ValueError):
            cumulative_assessment(records, limit=0.0)

    def test_count_limit_below_one_rejected(self):
        records = [categorize_nonconformance(nc("a"))]
        with self.assertRaises(ValueError):
            cumulative_assessment(records, count_limit=0)

    def test_boolean_count_limit_rejected(self):
        records = [categorize_nonconformance(nc("a"))]
        with self.assertRaises(ValueError):
            cumulative_assessment(records, count_limit=True)

    def test_empty_group_rejected(self):
        with self.assertRaises(ValueError):
            cumulative_assessment([])


class AssessmentTests(unittest.TestCase):
    def test_all_minor_run_reports_all_minor(self):
        result = assess_categorization({"nonconformances": [nc("a", consumption=0.1)]})
        self.assertTrue(result["all_minor"])
        self.assertEqual(result["findings"], [])

    def test_major_departure_named_in_the_findings(self):
        result = assess_categorization({"nonconformances": [nc("a", interface=True)]})
        self.assertFalse(result["all_minor"])
        self.assertEqual(result["major_departures"], 1)
        self.assertTrue(any("interface" in f for f in result["findings"]))

    def test_accumulation_escalates_only_the_affected_item(self):
        ncs = [nc("a", item="su-1", consumption=0.6),
               nc("b", item="su-1", consumption=0.5),
               nc("c", item="su-2", consumption=0.1)]
        result = assess_categorization({"nonconformances": ncs})
        self.assertEqual(result["escalated_items"], ("su-1",))

    def test_minor_and_major_counts_add_up(self):
        ncs = [nc("a"), nc("b", safety=True), nc("c")]
        result = assess_categorization({"nonconformances": ncs})
        self.assertEqual(result["minor_departures"], 2)
        self.assertEqual(result["major_departures"], 1)

    def test_custom_limits_honoured(self):
        ncs = [nc("a", consumption=0.2), nc("b", consumption=0.2)]
        result = assess_categorization(
            {"nonconformances": ncs, "cumulative_limit": 0.4, "minor_count_limit": 9}
        )
        self.assertEqual(result["escalated_items"], ("su-0007",))

    def test_missing_spec_key_rejected(self):
        with self.assertRaises(ValueError):
            assess_categorization({})

    def test_non_mapping_spec_rejected(self):
        with self.assertRaises(ValueError):
            assess_categorization([nc("a")])


if __name__ == "__main__":
    unittest.main()
