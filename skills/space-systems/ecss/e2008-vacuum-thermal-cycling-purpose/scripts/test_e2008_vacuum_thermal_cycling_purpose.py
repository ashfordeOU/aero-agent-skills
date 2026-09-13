"""Contract tests for the clause 5.5.3.11.1 vacuum thermal-cycling purpose logic."""

import unittest

from e2008_vacuum_thermal_cycling_purpose_logic import (
    ITEM_CATEGORIES,
    ITEM_OBJECTIVES,
    LIMIT_TOLERANCE,
    VACUUM_PRESSURE_LIMIT_PA,
    VACUUM_SENSITIVE_ITEMS,
    assess_article_coverage,
    assess_vacuum_cycling_purpose,
    at_or_above,
    at_or_below,
    evaluate_environment_bounds,
    group_demonstration_objectives,
    pressure_margin_decades,
    validate_campaign_policy,
)

# A declared inventory that spans all three item families and carries one
# vacuum-only failure mode, so the run is a vacuum run rather than an air one.
ITEMS = [
    {"item_id": "cell-stack-a", "item_class": "solar-cell-assembly"},
    {"item_id": "bus-joint-1", "item_class": "bus-bar-joint"},
    {"item_id": "connector-j1", "item_class": "connector-interface"},
]

# An inventory whose every failure mode also exists in air.
AIR_EQUIVALENT_ITEMS = [
    {"item_id": "cell-stack-a", "item_class": "solar-cell-assembly"},
    {"item_id": "bus-joint-1", "item_class": "bus-bar-joint"},
]

PREDICTED = {"hot_extreme_c": 85.0, "cold_extreme_c": -90.0, "cycle_count": 1000.0}

POLICY = {
    "vacuum_pressure_limit_pa": 1.3e-3,
    "temperature_margin_c": 10.0,
    "cycle_coverage_factor": 1.5,
}


def _planned(**overrides):
    run = {
        "chamber_pressure_pa": 1.0e-4,
        "hot_extreme_c": 95.0,
        "cold_extreme_c": -100.0,
        "cycle_count": 1500.0,
    }
    run.update(overrides)
    return run


def _spec(**overrides):
    spec = {
        "items": [dict(item) for item in ITEMS],
        "policy": dict(POLICY),
        "planned_run": _planned(),
        "predicted_environment": dict(PREDICTED),
    }
    spec.update(overrides)
    return spec


class BoundHelperTests(unittest.TestCase):
    def test_value_below_upper_bound_passes(self):
        self.assertTrue(at_or_below(1.0e-5, VACUUM_PRESSURE_LIMIT_PA))

    def test_value_above_upper_bound_fails(self):
        self.assertFalse(at_or_below(1.0e-1, VACUUM_PRESSURE_LIMIT_PA))

    def test_exact_equality_respects_upper_bound(self):
        self.assertTrue(at_or_below(VACUUM_PRESSURE_LIMIT_PA, VACUUM_PRESSURE_LIMIT_PA))

    def test_equality_within_tolerance_respects_upper_bound(self):
        self.assertTrue(at_or_below(0.05 + LIMIT_TOLERANCE / 2.0, 0.05))

    def test_exact_equality_respects_lower_bound(self):
        self.assertTrue(at_or_above(95.0, 95.0))

    def test_value_below_lower_bound_fails(self):
        self.assertFalse(at_or_above(80.0, 95.0))

    def test_non_numeric_bound_argument_rejected(self):
        with self.assertRaises(ValueError):
            at_or_below("1e-4", VACUUM_PRESSURE_LIMIT_PA)

    def test_boolean_is_not_a_number(self):
        with self.assertRaises(ValueError):
            at_or_above(True, 0.0)


class PressureMarginTests(unittest.TestCase):
    def test_two_decades_below_the_limit(self):
        self.assertAlmostEqual(
            pressure_margin_decades(1.3e-5, 1.3e-3), 2.0, places=9
        )

    def test_sitting_on_the_limit_is_zero_decades(self):
        self.assertAlmostEqual(
            pressure_margin_decades(1.3e-3, 1.3e-3), 0.0, places=9
        )

    def test_above_the_limit_is_negative(self):
        self.assertLess(pressure_margin_decades(1.3e-1, 1.3e-3), 0.0)

    def test_zero_pressure_rejected(self):
        with self.assertRaises(ValueError):
            pressure_margin_decades(0.0)

    def test_negative_pressure_rejected(self):
        with self.assertRaises(ValueError):
            pressure_margin_decades(-1.0e-4)


class CampaignPolicyTests(unittest.TestCase):
    def test_defaults_applied_to_an_empty_policy(self):
        policy = validate_campaign_policy({})
        self.assertAlmostEqual(
            policy["vacuum_pressure_limit_pa"], VACUUM_PRESSURE_LIMIT_PA, places=12
        )
        self.assertAlmostEqual(policy["cycle_coverage_factor"], 1.0, places=12)

    def test_coverage_factor_below_unity_rejected(self):
        with self.assertRaises(ValueError):
            validate_campaign_policy({"cycle_coverage_factor": 0.9})

    def test_negative_temperature_margin_rejected(self):
        with self.assertRaises(ValueError):
            validate_campaign_policy({"temperature_margin_c": -5.0})

    def test_non_mapping_policy_rejected(self):
        with self.assertRaises(ValueError):
            validate_campaign_policy(["temperature_margin_c"])


class ObjectiveGroupingTests(unittest.TestCase):
    def test_every_item_receives_an_objective(self):
        grouped = group_demonstration_objectives(ITEMS)
        self.assertEqual(len(grouped["objectives"]), 3)
        for record in grouped["objectives"]:
            self.assertEqual(record["objective"], ITEM_OBJECTIVES[record["item_class"]])

    def test_all_three_families_are_reported(self):
        grouped = group_demonstration_objectives(ITEMS)
        self.assertEqual(
            grouped["categories"], ["assembly", "component", "interface"]
        )

    def test_vacuum_only_failure_mode_is_marked(self):
        grouped = group_demonstration_objectives(ITEMS)
        self.assertEqual(grouped["vacuum_specific_items"], ["connector-j1"])
        self.assertTrue(grouped["vacuum_environment_required"])

    def test_air_equivalent_inventory_does_not_require_vacuum(self):
        grouped = group_demonstration_objectives(AIR_EQUIVALENT_ITEMS)
        self.assertFalse(grouped["vacuum_environment_required"])

    def test_every_catalogued_class_has_a_category_and_an_objective(self):
        self.assertEqual(set(ITEM_CATEGORIES), set(ITEM_OBJECTIVES))
        self.assertTrue(VACUUM_SENSITIVE_ITEMS.issubset(set(ITEM_CATEGORIES)))

    def test_unrecognised_item_class_rejected(self):
        with self.assertRaises(ValueError):
            group_demonstration_objectives(
                [{"item_id": "x", "item_class": "flux-capacitor"}]
            )

    def test_duplicate_item_id_rejected(self):
        with self.assertRaises(ValueError):
            group_demonstration_objectives([
                {"item_id": "dup", "item_class": "interconnector"},
                {"item_id": "dup", "item_class": "bus-bar-joint"},
            ])

    def test_empty_inventory_rejected(self):
        with self.assertRaises(ValueError):
            group_demonstration_objectives([])

    def test_non_boolean_article_flag_rejected(self):
        with self.assertRaises(ValueError):
            group_demonstration_objectives([
                {"item_id": "a", "item_class": "interconnector", "on_cycled_article": "yes"}
            ])


class ArticleCoverageTests(unittest.TestCase):
    def test_full_inventory_is_complete(self):
        coverage = assess_article_coverage(group_demonstration_objectives(ITEMS)["objectives"])
        self.assertTrue(coverage["complete"])
        self.assertAlmostEqual(coverage["coverage_fraction"], 1.0, places=12)

    def test_absent_item_is_named_with_its_family(self):
        items = [dict(item) for item in ITEMS]
        items[2]["on_cycled_article"] = False
        coverage = assess_article_coverage(
            group_demonstration_objectives(items)["objectives"]
        )
        self.assertFalse(coverage["complete"])
        self.assertEqual(coverage["missing_items"], ["connector-j1"])
        self.assertEqual(coverage["missing_categories"], ["interface"])
        self.assertAlmostEqual(coverage["coverage_fraction"], 2.0 / 3.0, places=12)

    def test_empty_record_list_rejected(self):
        with self.assertRaises(ValueError):
            assess_article_coverage([])


class EnvironmentBoundsTests(unittest.TestCase):
    def test_a_bounding_run_reports_no_shortfall(self):
        bounds = evaluate_environment_bounds(_planned(), PREDICTED, POLICY)
        self.assertTrue(bounds["bounds_environment"])
        self.assertEqual(bounds["shortfalls"], [])

    def test_owed_extremes_and_cycles_carry_the_margin(self):
        bounds = evaluate_environment_bounds(_planned(), PREDICTED, POLICY)
        self.assertAlmostEqual(bounds["owed_hot_extreme_c"], 95.0, places=9)
        self.assertAlmostEqual(bounds["owed_cold_extreme_c"], -100.0, places=9)
        self.assertAlmostEqual(bounds["owed_cycle_count"], 1500.0, places=9)

    def test_a_run_exactly_on_every_owed_value_still_bounds(self):
        bounds = evaluate_environment_bounds(
            _planned(hot_extreme_c=95.0, cold_extreme_c=-100.0, cycle_count=1500.0),
            PREDICTED,
            POLICY,
        )
        self.assertTrue(bounds["bounds_environment"])

    def test_chamber_above_the_vacuum_limit_is_a_shortfall(self):
        bounds = evaluate_environment_bounds(
            _planned(chamber_pressure_pa=1.0), PREDICTED, POLICY
        )
        self.assertFalse(bounds["pressure_within_limit"])
        self.assertEqual(len(bounds["shortfalls"]), 1)

    def test_short_hot_extreme_is_a_shortfall(self):
        bounds = evaluate_environment_bounds(
            _planned(hot_extreme_c=88.0), PREDICTED, POLICY
        )
        self.assertFalse(bounds["hot_extreme_bounds"])

    def test_short_cold_extreme_is_a_shortfall(self):
        bounds = evaluate_environment_bounds(
            _planned(cold_extreme_c=-92.0), PREDICTED, POLICY
        )
        self.assertFalse(bounds["cold_extreme_bounds"])

    def test_short_cycle_count_is_a_shortfall(self):
        bounds = evaluate_environment_bounds(
            _planned(cycle_count=1200.0), PREDICTED, POLICY
        )
        self.assertFalse(bounds["cycle_count_bounds"])

    def test_inverted_planned_profile_rejected(self):
        with self.assertRaises(ValueError):
            evaluate_environment_bounds(
                _planned(hot_extreme_c=-120.0), PREDICTED, POLICY
            )

    def test_inverted_predicted_profile_rejected(self):
        with self.assertRaises(ValueError):
            evaluate_environment_bounds(
                _planned(), {"hot_extreme_c": -90.0, "cold_extreme_c": 85.0,
                             "cycle_count": 1000.0}, POLICY
            )

    def test_missing_planned_key_rejected(self):
        run = _planned()
        del run["chamber_pressure_pa"]
        with self.assertRaises(ValueError):
            evaluate_environment_bounds(run, PREDICTED, POLICY)


class PurposeAssessmentTests(unittest.TestCase):
    def test_bounding_run_serves_the_purpose(self):
        result = assess_vacuum_cycling_purpose(_spec())
        self.assertEqual(result["verdict"], "planned-run-bounds-the-flight-environment")
        self.assertTrue(result["purpose_served"])
        self.assertEqual(result["findings"], [])

    def test_air_equivalent_inventory_does_not_earn_a_vacuum_run(self):
        result = assess_vacuum_cycling_purpose(
            _spec(items=[dict(item) for item in AIR_EQUIVALENT_ITEMS])
        )
        self.assertEqual(result["verdict"], "vacuum-environment-not-required")
        self.assertIsNone(result["bounds"])

    def test_justified_but_unplanned_run_is_its_own_verdict(self):
        spec = _spec()
        del spec["planned_run"]
        result = assess_vacuum_cycling_purpose(spec)
        self.assertEqual(result["verdict"], "justified-but-nothing-planned")
        self.assertFalse(result["purpose_served"])

    def test_under_bounds_run_names_its_shortfalls(self):
        result = assess_vacuum_cycling_purpose(
            _spec(planned_run=_planned(cold_extreme_c=-91.0, cycle_count=900.0))
        )
        self.assertEqual(result["verdict"], "planned-run-under-bounds")
        self.assertEqual(len(result["findings"]), 2)

    def test_item_absent_from_the_article_blocks_the_purpose(self):
        items = [dict(item) for item in ITEMS]
        items[2]["on_cycled_article"] = False
        result = assess_vacuum_cycling_purpose(_spec(items=items))
        self.assertFalse(result["purpose_served"])
        self.assertEqual(len(result["findings"]), 1)

    def test_planned_run_without_prediction_rejected(self):
        spec = _spec()
        del spec["predicted_environment"]
        with self.assertRaises(ValueError):
            assess_vacuum_cycling_purpose(spec)

    def test_missing_items_key_rejected(self):
        spec = _spec()
        del spec["items"]
        with self.assertRaises(ValueError):
            assess_vacuum_cycling_purpose(spec)

    def test_non_mapping_spec_rejected(self):
        with self.assertRaises(ValueError):
            assess_vacuum_cycling_purpose(["items"])


if __name__ == "__main__":
    unittest.main()
