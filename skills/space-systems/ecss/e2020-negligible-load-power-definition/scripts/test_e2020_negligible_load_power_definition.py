#!/usr/bin/env python3
"""Contract test for the negligible load power definition (offline)."""

import copy
import unittest

from e2020_negligible_load_power_definition_logic import (
    ADVISORY_NEAR_THRESHOLD,
    ADVISORY_NOTHING_EXCUSED,
    DEFAULT_BUDGET,
    DEFAULT_DEFINITION,
    FINDING_AGGREGATE,
    FINDING_THRESHOLD_VS_UNCERTAINTY,
    VERDICT_DEFENSIBLE,
    VERDICT_NOT_DEFENSIBLE,
    aggregate_cap_w,
    assess_load,
    budgeted_total_w,
    evaluate_negligibility_definition,
    excused_total_w,
    is_negligible_w,
    negligibility_threshold_w,
    validate_budget,
    validate_definition,
    validate_load,
    validate_load_list,
)

NOMINAL_LOADS = (
    {"name": "transponder", "consumption_w": 18.0},
    {"name": "reaction-wheel-set", "consumption_w": 42.0},
    {"name": "bus-pull-up-network", "consumption_w": 0.04},
    {"name": "latch-status-divider", "consumption_w": 0.02},
    {"name": "harness-bleed-resistor", "consumption_w": 0.095},
)


def _definition(**overrides):
    rule = copy.deepcopy(DEFAULT_DEFINITION)
    rule.update(overrides)
    return rule


def _budget(**overrides):
    context = copy.deepcopy(DEFAULT_BUDGET)
    context.update(overrides)
    return context


def _loads(*extra):
    return [copy.deepcopy(row) for row in NOMINAL_LOADS] + [
        copy.deepcopy(row) for row in extra
    ]


class DefinitionValidationTests(unittest.TestCase):
    def test_default_definition_validates(self):
        rule = validate_definition(DEFAULT_DEFINITION)
        self.assertAlmostEqual(rule["absolute_threshold_w"], 0.10, places=12)

    def test_non_mapping_definition_rejected(self):
        with self.assertRaises(ValueError):
            validate_definition("negligible is small")

    def test_undeclared_absolute_threshold_rejected(self):
        rule = _definition()
        del rule["absolute_threshold_w"]
        with self.assertRaises(ValueError):
            validate_definition(rule)

    def test_undeclared_aggregate_cap_rejected(self):
        rule = _definition()
        del rule["aggregate_cap_fraction"]
        with self.assertRaises(ValueError):
            validate_definition(rule)

    def test_relative_threshold_at_or_above_unity_rejected(self):
        with self.assertRaises(ValueError):
            validate_definition(_definition(relative_threshold=1.0))

    def test_aggregate_cap_at_or_above_unity_rejected(self):
        with self.assertRaises(ValueError):
            validate_definition(_definition(aggregate_cap_fraction=1.5))

    def test_zero_absolute_threshold_rejected(self):
        with self.assertRaises(ValueError):
            validate_definition(_definition(absolute_threshold_w=0.0))

    def test_negative_near_threshold_band_rejected(self):
        with self.assertRaises(ValueError):
            validate_definition(_definition(near_threshold_band=-0.05))

    def test_boolean_threshold_rejected(self):
        with self.assertRaises(ValueError):
            validate_definition(_definition(absolute_threshold_w=True))


class BudgetValidationTests(unittest.TestCase):
    def test_default_budget_validates(self):
        context = validate_budget(DEFAULT_BUDGET)
        self.assertAlmostEqual(context["reference_power_w"], 400.0, places=12)

    def test_budget_missing_uncertainty_rejected(self):
        context = _budget()
        del context["budget_uncertainty_w"]
        with self.assertRaises(ValueError):
            validate_budget(context)

    def test_zero_reference_power_rejected(self):
        with self.assertRaises(ValueError):
            validate_budget(_budget(reference_power_w=0.0))

    def test_non_mapping_budget_rejected(self):
        with self.assertRaises(ValueError):
            validate_budget(400.0)


class LoadValidationTests(unittest.TestCase):
    def test_nominal_load_validates(self):
        row = validate_load({"name": "transponder", "consumption_w": 18.0})
        self.assertEqual(row["name"], "transponder")

    def test_blank_load_name_rejected(self):
        with self.assertRaises(ValueError):
            validate_load({"name": "  ", "consumption_w": 1.0})

    def test_negative_consumption_rejected(self):
        with self.assertRaises(ValueError):
            validate_load({"name": "bleed", "consumption_w": -0.01})

    def test_zero_consumption_accepted(self):
        row = validate_load({"name": "spare-pin", "consumption_w": 0.0})
        self.assertAlmostEqual(row["consumption_w"], 0.0, places=12)

    def test_empty_load_list_rejected(self):
        with self.assertRaises(ValueError):
            validate_load_list([])

    def test_repeated_load_name_rejected(self):
        with self.assertRaises(ValueError):
            validate_load_list(
                [
                    {"name": "bleed", "consumption_w": 0.01},
                    {"name": "bleed", "consumption_w": 0.02},
                ]
            )

    def test_mapping_instead_of_a_sequence_rejected(self):
        with self.assertRaises(ValueError):
            validate_load_list({"name": "bleed", "consumption_w": 0.01})


class ThresholdTests(unittest.TestCase):
    def test_absolute_figure_binds_on_a_large_reference(self):
        threshold = negligibility_threshold_w(DEFAULT_DEFINITION, 400.0)
        self.assertAlmostEqual(threshold, 0.10, places=9)

    def test_relative_share_binds_on_a_small_reference(self):
        threshold = negligibility_threshold_w(DEFAULT_DEFINITION, 100.0)
        self.assertAlmostEqual(threshold, 0.05, places=9)

    def test_threshold_never_exceeds_either_declared_figure(self):
        for reference in (25.0, 100.0, 200.0, 400.0, 2000.0):
            threshold = negligibility_threshold_w(DEFAULT_DEFINITION, reference)
            self.assertLessEqual(threshold, DEFAULT_DEFINITION["absolute_threshold_w"])
            self.assertLessEqual(
                threshold, DEFAULT_DEFINITION["relative_threshold"] * reference
            )

    def test_aggregate_cap_scales_with_the_reference_power(self):
        self.assertAlmostEqual(aggregate_cap_w(DEFAULT_DEFINITION, 400.0), 4.0, places=9)

    def test_zero_reference_power_rejected_at_the_threshold_call(self):
        with self.assertRaises(ValueError):
            negligibility_threshold_w(DEFAULT_DEFINITION, 0.0)

    def test_consumption_exactly_on_the_threshold_is_excused(self):
        threshold = negligibility_threshold_w(DEFAULT_DEFINITION, 400.0)
        self.assertTrue(is_negligible_w(threshold, threshold))

    def test_consumption_above_the_threshold_is_not_excused(self):
        threshold = negligibility_threshold_w(DEFAULT_DEFINITION, 400.0)
        self.assertFalse(is_negligible_w(threshold * 2.0, threshold))

    def test_zero_threshold_rejected(self):
        with self.assertRaises(ValueError):
            is_negligible_w(0.01, 0.0)


class LoadScreeningTests(unittest.TestCase):
    def test_large_consumer_is_budgeted(self):
        result = assess_load({"name": "transponder", "consumption_w": 18.0})
        self.assertFalse(result["negligible"])
        self.assertTrue(result["budgeted"])

    def test_small_consumer_is_excused(self):
        result = assess_load({"name": "divider", "consumption_w": 0.02})
        self.assertTrue(result["negligible"])
        self.assertEqual(result["advisories"], [])

    def test_consumer_just_under_the_threshold_raises_an_advisory(self):
        result = assess_load({"name": "bleed", "consumption_w": 0.095})
        self.assertTrue(result["negligible"])
        self.assertTrue(any(ADVISORY_NEAR_THRESHOLD in a for a in result["advisories"]))

    def test_share_of_threshold_is_the_consumption_over_the_threshold(self):
        threshold = negligibility_threshold_w(DEFAULT_DEFINITION, 400.0)
        result = assess_load({"name": "bleed", "consumption_w": threshold})
        self.assertAlmostEqual(result["share_of_threshold"], 1.0, places=9)

    def test_a_smaller_reference_power_can_budget_a_previously_excused_load(self):
        big = assess_load({"name": "bleed", "consumption_w": 0.08})
        small = assess_load(
            {"name": "bleed", "consumption_w": 0.08}, budget=_budget(reference_power_w=100.0)
        )
        self.assertTrue(big["negligible"])
        self.assertFalse(small["negligible"])


class TotalsTests(unittest.TestCase):
    def test_excused_and_budgeted_totals_add_to_the_list_total(self):
        rows = _loads()
        total = sum(row["consumption_w"] for row in rows)
        self.assertAlmostEqual(
            excused_total_w(rows) + budgeted_total_w(rows), total, places=9
        )

    def test_excused_total_covers_only_the_small_consumers(self):
        self.assertAlmostEqual(excused_total_w(_loads()), 0.155, places=9)

    def test_budgeted_total_covers_only_the_large_consumers(self):
        self.assertAlmostEqual(budgeted_total_w(_loads()), 60.0, places=9)


class EvaluationTests(unittest.TestCase):
    def test_nominal_list_yields_a_defensible_rule(self):
        result = evaluate_negligibility_definition(_loads())
        self.assertEqual(result["verdict"], VERDICT_DEFENSIBLE)
        self.assertEqual(result["findings"], [])

    def test_many_small_consumers_breach_the_aggregate_cap(self):
        crowd = [
            {"name": "bleed-%03d" % i, "consumption_w": 0.10} for i in range(41)
        ]
        result = evaluate_negligibility_definition(_loads(*crowd))
        self.assertEqual(result["verdict"], VERDICT_NOT_DEFENSIBLE)
        self.assertTrue(any(FINDING_AGGREGATE in f for f in result["findings"]))

    def test_a_threshold_above_the_budget_uncertainty_is_a_finding(self):
        result = evaluate_negligibility_definition(
            _loads(), budget=_budget(budget_uncertainty_w=0.05)
        )
        self.assertEqual(result["verdict"], VERDICT_NOT_DEFENSIBLE)
        self.assertTrue(
            any(FINDING_THRESHOLD_VS_UNCERTAINTY in f for f in result["findings"])
        )

    def test_a_threshold_exactly_on_the_budget_uncertainty_is_accepted(self):
        threshold = negligibility_threshold_w(DEFAULT_DEFINITION, 400.0)
        result = evaluate_negligibility_definition(
            _loads(), budget=_budget(budget_uncertainty_w=threshold)
        )
        self.assertAlmostEqual(result["threshold_slack_w"], 0.0, places=9)
        self.assertFalse(
            any(FINDING_THRESHOLD_VS_UNCERTAINTY in f for f in result["findings"])
        )

    def test_a_rule_that_excuses_nothing_raises_an_advisory(self):
        result = evaluate_negligibility_definition(
            [{"name": "transponder", "consumption_w": 18.0}]
        )
        self.assertEqual(result["verdict"], VERDICT_DEFENSIBLE)
        self.assertTrue(any(ADVISORY_NOTHING_EXCUSED in a for a in result["advisories"]))

    def test_unbudgeted_residual_equals_the_excused_total(self):
        rows = _loads()
        result = evaluate_negligibility_definition(rows)
        self.assertAlmostEqual(
            result["unbudgeted_residual_w"], excused_total_w(rows), places=12
        )

    def test_residual_shares_are_reported_against_reference_and_uncertainty(self):
        result = evaluate_negligibility_definition(_loads())
        self.assertAlmostEqual(
            result["residual_share_of_reference"], 0.155 / 400.0, places=12
        )
        self.assertAlmostEqual(
            result["residual_share_of_uncertainty"], 0.155 / 20.0, places=12
        )

    def test_negligible_and_budgeted_name_lists_partition_the_input(self):
        rows = _loads()
        result = evaluate_negligibility_definition(rows)
        self.assertEqual(
            sorted(result["negligible_loads"] + result["budgeted_loads"]),
            sorted(row["name"] for row in rows),
        )

    def test_aggregate_slack_shrinks_as_small_consumers_are_added(self):
        lean = evaluate_negligibility_definition(_loads())
        fat = evaluate_negligibility_definition(
            _loads(*[{"name": "bleed-%03d" % i, "consumption_w": 0.09} for i in range(10)])
        )
        self.assertGreater(lean["aggregate_slack_w"], fat["aggregate_slack_w"])

    def test_evaluation_reports_one_assessment_per_load(self):
        rows = _loads()
        result = evaluate_negligibility_definition(rows)
        self.assertEqual(len(result["assessments"]), len(rows))

    def test_evaluation_rejects_a_broken_rule(self):
        with self.assertRaises(ValueError):
            evaluate_negligibility_definition(
                _loads(), definition=_definition(relative_threshold=2.0)
            )

    def test_evaluation_rejects_a_broken_load_list(self):
        with self.assertRaises(ValueError):
            evaluate_negligibility_definition([{"name": "bleed"}])


if __name__ == "__main__":
    unittest.main()
