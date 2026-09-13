"""Contract tests for the clause 6.4.3.9.1 coating adherence purpose logic."""

import unittest

from e2008_coating_adherence_test_purpose_logic import (
    CHECK_NOT_PLANNED,
    CHECK_SERVES_PURPOSE,
    CHECK_UNDER_SCOPE,
    COMMON_OBJECTIVE,
    DEFAULT_ADHERENCE_POLICY,
    LOOSENING_STRESSORS,
    STRESSOR_OBJECTIVES,
    TEST_NOT_REQUIRED,
    assess_adherence_purpose,
    check_is_justified,
    grade_planned_check,
    objectives_for,
    service_demand,
    validate_policy,
    validate_stressors,
)

# A representative low Earth orbit service life for a coated coverglass.
STRESSORS = [
    {"stressor": "thermal-cycling", "severity_fraction": 0.8},
    {"stressor": "solar-ultraviolet", "severity_fraction": 0.6},
    {"stressor": "ground-handling-and-cleaning", "severity_fraction": 0.5},
]

PLAN = {
    "after_environments": ["thermal-cycling", "ground-handling-and-cleaning"],
    "subgroup_samples": 6,
}


def _spec(**overrides):
    spec = {
        "has_conductive_coating": True,
        "service_stressors": [dict(s) for s in STRESSORS],
        "planned_check": dict(PLAN),
    }
    spec.update(overrides)
    return spec


class PolicyValidationTests(unittest.TestCase):
    def test_default_policy_is_returned(self):
        policy = validate_policy()
        self.assertAlmostEqual(policy["demand_trigger"], 1.0, places=9)
        self.assertEqual(policy["min_subgroup_samples"], 4)

    def test_declared_trigger_overrides_the_default(self):
        policy = validate_policy({"demand_trigger": 2.5})
        self.assertAlmostEqual(policy["demand_trigger"], 2.5, places=9)

    def test_unrecognised_weight_rejected(self):
        with self.assertRaises(ValueError):
            validate_policy({"weights": {"micrometeoroid-flux": 1.0}})

    def test_negative_weight_rejected(self):
        with self.assertRaises(ValueError):
            validate_policy({"weights": {"thermal-cycling": -1.0}})

    def test_non_positive_trigger_rejected(self):
        with self.assertRaises(ValueError):
            validate_policy({"demand_trigger": 0.0})

    def test_non_integer_sample_floor_rejected(self):
        with self.assertRaises(ValueError):
            validate_policy({"min_subgroup_samples": 4.5})

    def test_non_mapping_policy_rejected(self):
        with self.assertRaises(ValueError):
            validate_policy(["demand_trigger"])


class StressorInventoryTests(unittest.TestCase):
    def test_inventory_is_normalized(self):
        inventory = validate_stressors(STRESSORS)
        self.assertEqual(len(inventory), 3)
        self.assertAlmostEqual(inventory["thermal-cycling"], 0.8, places=9)

    def test_unrecognised_stressor_rejected(self):
        with self.assertRaises(ValueError):
            validate_stressors([{"stressor": "orbital-debris", "severity_fraction": 0.5}])

    def test_repeated_stressor_rejected(self):
        with self.assertRaises(ValueError):
            validate_stressors(STRESSORS + [dict(STRESSORS[0])])

    def test_severity_above_unity_rejected(self):
        with self.assertRaises(ValueError):
            validate_stressors([{"stressor": "thermal-cycling", "severity_fraction": 1.4}])

    def test_negative_severity_rejected(self):
        with self.assertRaises(ValueError):
            validate_stressors([{"stressor": "thermal-cycling", "severity_fraction": -0.1}])

    def test_missing_severity_rejected(self):
        with self.assertRaises(ValueError):
            validate_stressors([{"stressor": "thermal-cycling"}])

    def test_empty_inventory_is_allowed_and_empty(self):
        self.assertEqual(validate_stressors([]), {})


class ObjectiveMappingTests(unittest.TestCase):
    def test_every_stressor_maps_to_an_objective(self):
        objectives = objectives_for(STRESSORS)
        self.assertIn(STRESSOR_OBJECTIVES["thermal-cycling"], objectives)
        self.assertIn(STRESSOR_OBJECTIVES["solar-ultraviolet"], objectives)

    def test_shared_objective_is_appended_once(self):
        objectives = objectives_for(STRESSORS)
        self.assertEqual(objectives.count(COMMON_OBJECTIVE), 1)

    def test_no_stressor_yields_no_objective(self):
        self.assertEqual(objectives_for([]), [])

    def test_charge_bleed_is_the_electrostatic_objective(self):
        objectives = objectives_for(
            [{"stressor": "electrostatic-charging", "severity_fraction": 1.0}]
        )
        self.assertIn("front-surface-charge-bleed-continuity", objectives)


class ServiceDemandTests(unittest.TestCase):
    def test_demand_is_the_weighted_sum(self):
        expected = 1.0 * 0.8 + 0.4 * 0.6 + 0.8 * 0.5
        self.assertAlmostEqual(service_demand(STRESSORS), expected, places=9)

    def test_no_stressor_is_no_demand(self):
        self.assertAlmostEqual(service_demand([]), 0.0, places=9)

    def test_zero_severity_contributes_nothing(self):
        quiet = [{"stressor": "thermal-cycling", "severity_fraction": 0.0}]
        self.assertAlmostEqual(service_demand(quiet), 0.0, places=9)

    def test_declared_weight_changes_the_demand(self):
        demand = service_demand(
            [{"stressor": "thermal-cycling", "severity_fraction": 1.0}],
            {"weights": {"thermal-cycling": 2.0}},
        )
        self.assertAlmostEqual(demand, 2.0, places=9)


class JustificationTests(unittest.TestCase):
    def test_uncoated_coverglass_is_never_justified(self):
        self.assertFalse(check_is_justified(False, 9.0))

    def test_demand_above_the_trigger_justifies_the_check(self):
        self.assertTrue(check_is_justified(True, 1.5))

    def test_demand_below_the_trigger_does_not(self):
        self.assertFalse(check_is_justified(True, 0.3))

    def test_demand_landing_on_the_trigger_justifies_the_check(self):
        trigger = DEFAULT_ADHERENCE_POLICY["demand_trigger"]
        self.assertAlmostEqual(trigger, 1.0, places=9)
        self.assertTrue(check_is_justified(True, trigger))

    def test_non_boolean_coating_flag_rejected(self):
        with self.assertRaises(ValueError):
            check_is_justified("yes", 1.5)

    def test_negative_demand_rejected(self):
        with self.assertRaises(ValueError):
            check_is_justified(True, -1.0)


class PlannedCheckTests(unittest.TestCase):
    def test_plan_following_every_loosening_environment_is_clean(self):
        grading = grade_planned_check(PLAN, STRESSORS)
        self.assertEqual(grading["shortfalls"], [])
        self.assertEqual(grading["unfollowed_environments"], [])

    def test_unfollowed_loosening_environment_is_a_shortfall(self):
        plan = dict(PLAN, after_environments=["ground-handling-and-cleaning"])
        grading = grade_planned_check(plan, STRESSORS)
        self.assertEqual(grading["unfollowed_environments"], ["thermal-cycling"])
        self.assertEqual(len(grading["shortfalls"]), 1)

    def test_a_non_loosening_stressor_is_not_demanded(self):
        # Solar ultraviolet is declared but is not a loosening environment, so
        # a plan that never follows it carries no shortfall for it.
        grading = grade_planned_check(PLAN, STRESSORS)
        self.assertNotIn("solar-ultraviolet", grading["unfollowed_environments"])

    def test_too_few_samples_is_a_shortfall(self):
        grading = grade_planned_check(dict(PLAN, subgroup_samples=2), STRESSORS)
        self.assertEqual(
            len([s for s in grading["shortfalls"] if "subgroup samples" in s]), 1
        )

    def test_unrecognised_planned_environment_rejected(self):
        with self.assertRaises(ValueError):
            grade_planned_check(dict(PLAN, after_environments=["sunbathing"]), STRESSORS)

    def test_negative_sample_count_rejected(self):
        with self.assertRaises(ValueError):
            grade_planned_check(dict(PLAN, subgroup_samples=-1), STRESSORS)

    def test_missing_plan_key_rejected(self):
        plan = dict(PLAN)
        del plan["subgroup_samples"]
        with self.assertRaises(ValueError):
            grade_planned_check(plan, STRESSORS)

    def test_loosening_set_is_a_subset_of_the_known_stressors(self):
        for name in LOOSENING_STRESSORS:
            self.assertIn(name, STRESSOR_OBJECTIVES)


class PurposeAssessmentTests(unittest.TestCase):
    def test_nominal_case_serves_the_purpose(self):
        result = assess_adherence_purpose(_spec())
        self.assertEqual(result["verdict"], CHECK_SERVES_PURPOSE)
        self.assertEqual(result["findings"], [])

    def test_uncoated_coverglass_does_not_earn_a_check(self):
        result = assess_adherence_purpose(_spec(has_conductive_coating=False))
        self.assertEqual(result["verdict"], TEST_NOT_REQUIRED)
        self.assertEqual(result["objectives"], [])

    def test_quiet_service_life_does_not_earn_a_check(self):
        quiet = [{"stressor": "solar-ultraviolet", "severity_fraction": 0.1}]
        result = assess_adherence_purpose(_spec(service_stressors=quiet))
        self.assertEqual(result["verdict"], TEST_NOT_REQUIRED)
        self.assertFalse(result["justified"])

    def test_justified_but_unplanned_is_its_own_verdict(self):
        spec = _spec()
        del spec["planned_check"]
        result = assess_adherence_purpose(spec)
        self.assertEqual(result["verdict"], CHECK_NOT_PLANNED)

    def test_plan_run_before_the_environments_is_under_scope(self):
        result = assess_adherence_purpose(
            _spec(planned_check=dict(PLAN, after_environments=[]))
        )
        self.assertEqual(result["verdict"], CHECK_UNDER_SCOPE)
        self.assertEqual(len(result["findings"]), 2)

    def test_objectives_are_reported_for_a_coated_coverglass(self):
        result = assess_adherence_purpose(_spec())
        self.assertIn(COMMON_OBJECTIVE, result["objectives"])
        self.assertEqual(result["stressor_count"], 3)

    def test_declared_trigger_can_stand_the_check_down(self):
        result = assess_adherence_purpose(_spec(policy={"demand_trigger": 5.0}))
        self.assertEqual(result["verdict"], TEST_NOT_REQUIRED)

    def test_demand_is_echoed_with_its_trigger(self):
        result = assess_adherence_purpose(_spec())
        self.assertAlmostEqual(result["demand_trigger"], 1.0, places=9)
        self.assertAlmostEqual(result["service_demand"], service_demand(STRESSORS), places=9)

    def test_non_boolean_coating_flag_rejected(self):
        with self.assertRaises(ValueError):
            assess_adherence_purpose(_spec(has_conductive_coating="true"))

    def test_missing_spec_key_rejected(self):
        spec = _spec()
        del spec["service_stressors"]
        with self.assertRaises(ValueError):
            assess_adherence_purpose(spec)

    def test_non_mapping_spec_rejected(self):
        with self.assertRaises(ValueError):
            assess_adherence_purpose(["has_conductive_coating"])


if __name__ == "__main__":
    unittest.main()
