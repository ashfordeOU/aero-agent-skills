"""Contract tests for the clause 6.4.4 probabilistic safety target logic."""

import math
import unittest

from q40_probabilistic_safety_targets_logic import (
    DEFAULT_TARGETS,
    PROBABILITY_BANDS,
    RISK_ACCEPTANCE,
    SEVERITY_ORDER,
    aggregate_probability,
    allocate_target,
    assess_probabilistic_targets,
    compare_to_target,
    probability_band,
    risk_acceptance,
    validate_probability,
    validate_severity,
    validate_targets,
)


def hazard(identifier, severity, probability, weight=None):
    """Build one hazard contribution record."""
    record = {
        "id": identifier,
        "severity": severity,
        "predicted_probability": probability,
    }
    if weight is not None:
        record["weight"] = weight
    return record


class SeverityTests(unittest.TestCase):
    def test_categories_run_most_severe_first(self):
        self.assertEqual(SEVERITY_ORDER, ("catastrophic", "critical", "major", "minor"))

    def test_severity_is_trimmed_and_lowered(self):
        self.assertEqual(validate_severity("  Catastrophic "), "catastrophic")

    def test_unknown_severity_rejected(self):
        with self.assertRaises(ValueError):
            validate_severity("annoying")

    def test_non_string_severity_rejected(self):
        with self.assertRaises(ValueError):
            validate_severity(1)


class ProbabilityTests(unittest.TestCase):
    def test_probability_of_one_is_allowed(self):
        self.assertAlmostEqual(validate_probability(1.0, "p"), 1.0, places=9)

    def test_zero_probability_rejected(self):
        with self.assertRaises(ValueError):
            validate_probability(0.0, "p")

    def test_probability_above_one_rejected(self):
        with self.assertRaises(ValueError):
            validate_probability(1.5, "p")

    def test_boolean_probability_rejected(self):
        with self.assertRaises(ValueError):
            validate_probability(True, "p")

    def test_non_finite_probability_rejected(self):
        with self.assertRaises(ValueError):
            validate_probability(float("nan"), "p")


class TargetSetTests(unittest.TestCase):
    def test_default_set_validates(self):
        targets = validate_targets()
        self.assertAlmostEqual(targets["catastrophic"], DEFAULT_TARGETS["catastrophic"], places=9)

    def test_default_set_is_stricter_as_severity_rises(self):
        targets = validate_targets()
        for index in range(1, len(SEVERITY_ORDER)):
            self.assertLess(targets[SEVERITY_ORDER[index - 1]], targets[SEVERITY_ORDER[index]])

    def test_missing_category_rejected(self):
        with self.assertRaises(ValueError):
            validate_targets({"catastrophic": 1.0e-4, "critical": 1.0e-3, "major": 1.0e-2})

    def test_unknown_category_rejected(self):
        bad = dict(DEFAULT_TARGETS)
        bad["annoying"] = 0.5
        with self.assertRaises(ValueError):
            validate_targets(bad)

    def test_non_monotone_set_rejected(self):
        bad = dict(DEFAULT_TARGETS)
        bad["catastrophic"] = 1.0e-2
        with self.assertRaises(ValueError):
            validate_targets(bad)

    def test_equal_neighbouring_targets_rejected(self):
        bad = dict(DEFAULT_TARGETS)
        bad["critical"] = bad["catastrophic"]
        with self.assertRaises(ValueError):
            validate_targets(bad)

    def test_tailored_set_accepted(self):
        targets = validate_targets(
            {"catastrophic": 1.0e-6, "critical": 1.0e-5, "major": 1.0e-3, "minor": 1.0e-2}
        )
        self.assertAlmostEqual(targets["minor"], 1.0e-2, places=9)


class AllocationTests(unittest.TestCase):
    def test_equal_weights_split_evenly(self):
        shares = allocate_target(1.0e-4, {"a": 1.0, "b": 1.0})
        self.assertAlmostEqual(shares["a"], 5.0e-5, places=12)
        self.assertAlmostEqual(shares["b"], 5.0e-5, places=12)

    def test_allocation_sums_back_to_the_target(self):
        shares = allocate_target(1.0e-3, {"a": 2.0, "b": 3.0, "c": 5.0})
        self.assertAlmostEqual(math.fsum(shares.values()), 1.0e-3, places=12)

    def test_weights_drive_the_share(self):
        shares = allocate_target(1.0e-3, {"a": 1.0, "b": 3.0})
        self.assertAlmostEqual(shares["b"], 3.0 * shares["a"], places=12)

    def test_single_contributor_takes_the_whole_target(self):
        shares = allocate_target(1.0e-4, {"only": 7.0})
        self.assertAlmostEqual(shares["only"], 1.0e-4, places=12)

    def test_empty_weights_rejected(self):
        with self.assertRaises(ValueError):
            allocate_target(1.0e-4, {})

    def test_zero_weight_rejected(self):
        with self.assertRaises(ValueError):
            allocate_target(1.0e-4, {"a": 0.0})

    def test_negative_weight_rejected(self):
        with self.assertRaises(ValueError):
            allocate_target(1.0e-4, {"a": -1.0})

    def test_blank_contributor_key_rejected(self):
        with self.assertRaises(ValueError):
            allocate_target(1.0e-4, {"  ": 1.0})


class AggregationTests(unittest.TestCase):
    def test_single_value_returns_itself(self):
        self.assertAlmostEqual(aggregate_probability([1.0e-3]), 1.0e-3, places=12)

    def test_union_is_below_the_naive_sum(self):
        union = aggregate_probability([0.1, 0.1])
        self.assertAlmostEqual(union, 0.19, places=12)

    def test_union_of_small_values_is_close_to_the_sum(self):
        union = aggregate_probability([1.0e-6, 2.0e-6])
        self.assertAlmostEqual(union, 3.0e-6, places=11)

    def test_union_never_reaches_one_for_valid_inputs(self):
        union = aggregate_probability([0.9, 0.9, 0.9])
        self.assertLess(union, 1.0)

    def test_empty_sequence_gives_zero(self):
        self.assertAlmostEqual(aggregate_probability([]), 0.0, places=12)

    def test_invalid_member_rejected(self):
        with self.assertRaises(ValueError):
            aggregate_probability([0.1, 0.0])


class BandTests(unittest.TestCase):
    def test_bands_ascend_in_upper_bound(self):
        bounds = [bound for _, bound in PROBABILITY_BANDS]
        self.assertEqual(bounds, sorted(bounds))

    def test_value_on_a_bound_belongs_to_the_band_that_bound_closes(self):
        self.assertEqual(probability_band(1.0e-2), "occasional")

    def test_value_just_inside_a_bound_stays_in_the_band(self):
        self.assertEqual(probability_band(9.0e-3), "occasional")

    def test_value_above_a_bound_moves_up_a_band(self):
        self.assertEqual(probability_band(2.0e-2), "probable")

    def test_very_small_value_is_extremely_improbable(self):
        self.assertEqual(probability_band(1.0e-12), "extremely-improbable")

    def test_certainty_is_probable(self):
        self.assertEqual(probability_band(1.0), "probable")


class AcceptanceTests(unittest.TestCase):
    def test_matrix_covers_every_severity_and_band(self):
        names = [name for name, _ in PROBABILITY_BANDS]
        for severity in SEVERITY_ORDER:
            self.assertEqual(sorted(RISK_ACCEPTANCE[severity]), sorted(names))

    def test_occasional_catastrophic_is_unacceptable(self):
        self.assertEqual(risk_acceptance("catastrophic", 5.0e-3), "unacceptable")

    def test_extremely_improbable_catastrophic_is_acceptable(self):
        self.assertEqual(risk_acceptance("catastrophic", 1.0e-10), "acceptable")

    def test_remote_catastrophic_is_undesirable(self):
        self.assertEqual(risk_acceptance("catastrophic", 5.0e-5), "undesirable")

    def test_same_probability_is_milder_at_lower_severity(self):
        self.assertEqual(risk_acceptance("minor", 5.0e-3), "acceptable")

    def test_unknown_severity_rejected_by_the_matrix(self):
        with self.assertRaises(ValueError):
            risk_acceptance("moderate", 1.0e-5)


class ComparisonTests(unittest.TestCase):
    def test_prediction_below_target_is_within(self):
        result = compare_to_target(1.0e-5, 1.0e-4)
        self.assertTrue(result["within_target"])
        self.assertAlmostEqual(result["margin_ratio"], 10.0, places=9)

    def test_prediction_equal_to_target_is_within(self):
        result = compare_to_target(1.0e-4, 1.0e-4)
        self.assertTrue(result["within_target"])
        self.assertAlmostEqual(result["margin_ratio"], 1.0, places=9)

    def test_prediction_above_target_is_not_within(self):
        result = compare_to_target(1.0e-3, 1.0e-4)
        self.assertFalse(result["within_target"])

    def test_margin_ratio_is_target_over_prediction(self):
        result = compare_to_target(2.0e-4, 1.0e-3)
        self.assertAlmostEqual(result["margin_ratio"], 5.0, places=9)


class AssessmentTests(unittest.TestCase):
    def test_compliant_case_reports_targets_met(self):
        result = assess_probabilistic_targets(
            {"hazards": [hazard("HZ-1", "catastrophic", 1.0e-7)]}
        )
        self.assertEqual(result["verdict"], "targets-met")
        self.assertEqual(result["findings"], [])

    def test_budget_is_the_allocated_share_not_the_whole_target(self):
        result = assess_probabilistic_targets(
            {
                "hazards": [
                    hazard("HZ-1", "catastrophic", 1.0e-7),
                    hazard("HZ-2", "catastrophic", 1.0e-7),
                ]
            }
        )
        budgets = {row["id"]: row["allocated_target"] for row in result["hazards"]}
        self.assertAlmostEqual(budgets["HZ-1"], 5.0e-5, places=12)

    def test_weighted_hazard_receives_the_larger_budget(self):
        result = assess_probabilistic_targets(
            {
                "hazards": [
                    hazard("HZ-1", "critical", 1.0e-7, weight=3.0),
                    hazard("HZ-2", "critical", 1.0e-7, weight=1.0),
                ]
            }
        )
        budgets = {row["id"]: row["allocated_target"] for row in result["hazards"]}
        self.assertAlmostEqual(budgets["HZ-1"], 3.0 * budgets["HZ-2"], places=12)

    def test_overrun_against_the_allocated_budget_is_a_finding(self):
        result = assess_probabilistic_targets(
            {
                "hazards": [
                    hazard("HZ-1", "catastrophic", 9.0e-5),
                    hazard("HZ-2", "catastrophic", 1.0e-8),
                ]
            }
        )
        self.assertEqual(result["verdict"], "targets-not-met")
        self.assertTrue(any("allocated budget" in f for f in result["findings"]))

    def test_group_aggregate_is_graded_against_the_group_target(self):
        result = assess_probabilistic_targets(
            {"hazards": [hazard("HZ-1", "minor", 1.0e-3)]}
        )
        group = result["groups"][0]
        self.assertEqual(group["severity"], "minor")
        self.assertAlmostEqual(group["aggregate_probability"], 1.0e-3, places=12)
        self.assertTrue(group["within_target"])

    def test_groups_are_reported_in_severity_order(self):
        result = assess_probabilistic_targets(
            {
                "hazards": [
                    hazard("HZ-2", "minor", 1.0e-3),
                    hazard("HZ-1", "catastrophic", 1.0e-8),
                ]
            }
        )
        self.assertEqual([row["severity"] for row in result["groups"]], ["catastrophic", "minor"])

    def test_unacceptable_pair_is_reported_even_within_budget(self):
        result = assess_probabilistic_targets(
            {
                "hazards": [hazard("HZ-1", "catastrophic", 5.0e-3)],
                "targets": {
                    "catastrophic": 1.0e-2,
                    "critical": 5.0e-2,
                    "major": 1.0e-1,
                    "minor": 5.0e-1,
                },
            }
        )
        self.assertTrue(any("cannot be carried" in f for f in result["findings"]))

    def test_duplicate_hazard_id_rejected(self):
        with self.assertRaises(ValueError):
            assess_probabilistic_targets(
                {
                    "hazards": [
                        hazard("HZ-1", "major", 1.0e-4),
                        hazard("HZ-1", "major", 1.0e-4),
                    ]
                }
            )

    def test_unknown_hazard_key_rejected(self):
        bad = hazard("HZ-1", "major", 1.0e-4)
        bad["owner"] = "avionics"
        with self.assertRaises(ValueError):
            assess_probabilistic_targets({"hazards": [bad]})

    def test_empty_hazard_set_rejected(self):
        with self.assertRaises(ValueError):
            assess_probabilistic_targets({"hazards": []})

    def test_missing_hazards_key_rejected(self):
        with self.assertRaises(ValueError):
            assess_probabilistic_targets({"targets": DEFAULT_TARGETS})

    def test_non_mapping_spec_rejected(self):
        with self.assertRaises(ValueError):
            assess_probabilistic_targets(["HZ-1"])


if __name__ == "__main__":
    unittest.main()
