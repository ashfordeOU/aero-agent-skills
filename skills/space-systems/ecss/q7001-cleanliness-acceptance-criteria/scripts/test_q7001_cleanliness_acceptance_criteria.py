"""Contract tests for the ECSS-Q-ST-70-01C cleanliness acceptance logic."""

import unittest

from q7001_cleanliness_acceptance_criteria_logic import (
    LIMIT_TOLERANCE,
    MINOR_RATIO_CEILING,
    categorize_nonconformance,
    decide_against_limit,
    disposition_for,
    exceedance_ratio,
    expanded_uncertainty,
    handle_result,
    summarise_acceptance,
    validate_result,
)


def result(**overrides):
    record = {
        "id": "CLN-010",
        "value": 8.0,
        "limit": 10.0,
        "standard_uncertainty": 0.5,
    }
    record.update(overrides)
    return record


class ValidateResultTests(unittest.TestCase):
    def test_defaults_are_applied(self):
        record = validate_result(result())
        self.assertEqual(record["decision_rule"], "guard-banded")
        self.assertAlmostEqual(record["coverage_factor"], 2.0, places=9)
        self.assertFalse(record["critical"])
        self.assertTrue(record["recleanable"])

    def test_identifier_is_stripped(self):
        self.assertEqual(validate_result(result(id="  CLN-020 "))["id"], "CLN-020")

    def test_negative_value_rejected(self):
        with self.assertRaises(ValueError):
            validate_result(result(value=-1.0))

    def test_zero_limit_rejected(self):
        with self.assertRaises(ValueError):
            validate_result(result(limit=0.0))

    def test_negative_uncertainty_rejected(self):
        with self.assertRaises(ValueError):
            validate_result(result(standard_uncertainty=-0.1))

    def test_unknown_decision_rule_rejected(self):
        with self.assertRaises(ValueError):
            validate_result(result(decision_rule="best-effort"))

    def test_missing_limit_rejected(self):
        record = result()
        del record["limit"]
        with self.assertRaises(ValueError):
            validate_result(record)

    def test_empty_identifier_rejected(self):
        with self.assertRaises(ValueError):
            validate_result(result(id="   "))

    def test_non_mapping_result_rejected(self):
        with self.assertRaises(ValueError):
            validate_result(["CLN-010"])


class UncertaintyTests(unittest.TestCase):
    def test_default_coverage_doubles_the_standard_uncertainty(self):
        self.assertAlmostEqual(expanded_uncertainty(0.5), 1.0, places=9)

    def test_declared_coverage_is_used(self):
        self.assertAlmostEqual(expanded_uncertainty(0.5, 3.0), 1.5, places=9)

    def test_zero_uncertainty_is_allowed(self):
        self.assertAlmostEqual(expanded_uncertainty(0.0), 0.0, places=12)

    def test_negative_coverage_rejected(self):
        with self.assertRaises(ValueError):
            expanded_uncertainty(0.5, -2.0)


class DecisionRuleTests(unittest.TestCase):
    def test_guard_banded_accept_needs_the_uncertainty_inside(self):
        self.assertEqual(decide_against_limit(8.0, 10.0, 1.0), "accept")

    def test_guard_banded_straddle_is_indeterminate(self):
        self.assertEqual(decide_against_limit(9.8, 10.0, 1.0), "indeterminate")

    def test_guard_banded_reject_needs_the_uncertainty_outside(self):
        self.assertEqual(decide_against_limit(12.0, 10.0, 1.0), "reject")

    def test_value_exactly_at_the_limit_without_uncertainty_is_accepted(self):
        self.assertEqual(decide_against_limit(10.0, 10.0, 0.0), "accept")

    def test_shared_risk_ignores_the_uncertainty(self):
        self.assertEqual(
            decide_against_limit(9.8, 10.0, 1.0, "shared-risk"), "accept"
        )

    def test_shared_risk_rejects_just_above_the_limit(self):
        self.assertEqual(
            decide_against_limit(10.2, 10.0, 1.0, "shared-risk"), "reject"
        )

    def test_unknown_rule_rejected(self):
        with self.assertRaises(ValueError):
            decide_against_limit(8.0, 10.0, 1.0, "optimistic")

    def test_negative_expanded_uncertainty_rejected(self):
        with self.assertRaises(ValueError):
            decide_against_limit(8.0, 10.0, -1.0)


class RatioAndCategoryTests(unittest.TestCase):
    def test_ratio_is_value_over_limit(self):
        self.assertAlmostEqual(exceedance_ratio(12.5, 10.0), 1.25, places=9)

    def test_ratio_below_one_is_allowed_to_be_computed(self):
        self.assertAlmostEqual(exceedance_ratio(5.0, 10.0), 0.5, places=9)

    def test_zero_limit_ratio_rejected(self):
        with self.assertRaises(ValueError):
            exceedance_ratio(5.0, 0.0)

    def test_small_exceedance_on_a_normal_surface_is_minor(self):
        self.assertEqual(categorize_nonconformance(1.1), "minor")

    def test_exceedance_exactly_at_the_ceiling_is_minor(self):
        self.assertEqual(
            categorize_nonconformance(MINOR_RATIO_CEILING), "minor"
        )

    def test_large_exceedance_is_major(self):
        self.assertEqual(categorize_nonconformance(2.0), "major")

    def test_any_exceedance_on_a_critical_surface_is_major(self):
        self.assertEqual(categorize_nonconformance(1.02, critical=True), "major")

    def test_repeat_exceedance_is_major(self):
        self.assertEqual(categorize_nonconformance(1.02, repeat=True), "major")

    def test_non_exceedance_cannot_be_categorized(self):
        with self.assertRaises(ValueError):
            categorize_nonconformance(0.9)

    def test_non_boolean_criticality_rejected(self):
        with self.assertRaises(ValueError):
            categorize_nonconformance(1.5, critical="yes")


class DispositionTests(unittest.TestCase):
    def test_minor_on_a_recleanable_surface_is_recleaned(self):
        self.assertEqual(disposition_for("minor"), "reclean-and-reverify")

    def test_major_on_a_recleanable_surface_is_still_recleaned_first(self):
        self.assertEqual(disposition_for("major"), "reclean-and-reverify")

    def test_major_on_a_closed_surface_escalates(self):
        self.assertEqual(
            disposition_for("major", recleanable=False), "escalate-to-review-board"
        )

    def test_repeat_exceedance_escalates(self):
        self.assertEqual(
            disposition_for("major", repeat=True), "escalate-to-review-board"
        )

    def test_accepted_impact_analysis_allows_use_as_is(self):
        self.assertEqual(
            disposition_for("major", recleanable=False, impact_analysis_accepted=True),
            "use-as-is-with-impact-analysis",
        )

    def test_unknown_category_rejected(self):
        with self.assertRaises(ValueError):
            disposition_for("cosmetic")

    def test_non_boolean_flag_rejected(self):
        with self.assertRaises(ValueError):
            disposition_for("minor", recleanable="yes")


class HandleResultTests(unittest.TestCase):
    def test_clear_pass_is_accepted(self):
        entry = handle_result(result())
        self.assertEqual(entry["verdict"], "accept")
        self.assertEqual(entry["disposition"], "accept")
        self.assertEqual(entry["findings"], [])

    def test_straddling_result_repeats_the_measurement(self):
        entry = handle_result(result(value=9.8))
        self.assertEqual(entry["verdict"], "indeterminate")
        self.assertEqual(entry["disposition"], "repeat-the-measurement")
        self.assertTrue(any("straddles" in item for item in entry["findings"]))

    def test_minor_exceedance_is_recleaned(self):
        entry = handle_result(result(value=11.5, standard_uncertainty=0.1))
        self.assertEqual(entry["verdict"], "reject")
        self.assertEqual(entry["category"], "minor")
        self.assertEqual(entry["disposition"], "reclean-and-reverify")

    def test_repeat_exceedance_escalates(self):
        entry = handle_result(
            result(value=11.5, standard_uncertainty=0.1, repeat_exceedance=True)
        )
        self.assertEqual(entry["category"], "major")
        self.assertEqual(entry["disposition"], "escalate-to-review-board")

    def test_critical_surface_exceedance_is_reported_as_major(self):
        entry = handle_result(
            result(value=10.5, standard_uncertainty=0.1, critical=True)
        )
        self.assertEqual(entry["category"], "major")
        self.assertTrue(
            any("criticality-driven" in item for item in entry["findings"])
        )

    def test_use_as_is_records_what_it_rests_on(self):
        entry = handle_result(
            result(
                value=30.0,
                standard_uncertainty=0.1,
                recleanable=False,
                impact_analysis_accepted=True,
            )
        )
        self.assertEqual(entry["disposition"], "use-as-is-with-impact-analysis")
        self.assertTrue(any("impact analysis" in item for item in entry["findings"]))

    def test_exact_limit_with_no_uncertainty_is_accepted(self):
        entry = handle_result(result(value=10.0, standard_uncertainty=0.0))
        self.assertEqual(entry["verdict"], "accept")
        self.assertAlmostEqual(entry["exceedance_ratio"], 1.0, places=9)
        self.assertLessEqual(abs(entry["exceedance_ratio"] - 1.0), LIMIT_TOLERANCE)

    def test_expanded_uncertainty_is_reported(self):
        entry = handle_result(result(standard_uncertainty=0.25, coverage_factor=3.0))
        self.assertAlmostEqual(entry["expanded_uncertainty"], 0.75, places=9)


class SummaryTests(unittest.TestCase):
    def test_all_accepted_set(self):
        summary = summarise_acceptance([result(), result(id="CLN-011", value=4.0)])
        self.assertTrue(summary["all_accepted"])
        self.assertAlmostEqual(summary["accepted_fraction"], 1.0, places=9)

    def test_mixed_set_counts_each_verdict(self):
        summary = summarise_acceptance(
            [
                result(),
                result(id="CLN-011", value=9.8),
                result(id="CLN-012", value=20.0, standard_uncertainty=0.1),
            ]
        )
        self.assertEqual(summary["counts"]["accept"], 1)
        self.assertEqual(summary["counts"]["indeterminate"], 1)
        self.assertEqual(summary["counts"]["reject"], 1)
        self.assertAlmostEqual(summary["accepted_fraction"], 1.0 / 3.0, places=9)

    def test_escalated_identifiers_are_listed(self):
        summary = summarise_acceptance(
            [
                result(
                    id="CLN-030",
                    value=40.0,
                    standard_uncertainty=0.1,
                    recleanable=False,
                )
            ]
        )
        self.assertEqual(summary["escalated"], ["CLN-030"])

    def test_findings_are_aggregated(self):
        summary = summarise_acceptance(
            [result(value=9.8), result(id="CLN-011", value=9.8)]
        )
        self.assertEqual(len(summary["findings"]), 2)

    def test_duplicate_identifier_rejected(self):
        with self.assertRaises(ValueError):
            summarise_acceptance([result(), result()])

    def test_empty_set_rejected(self):
        with self.assertRaises(ValueError):
            summarise_acceptance([])


if __name__ == "__main__":
    unittest.main()
