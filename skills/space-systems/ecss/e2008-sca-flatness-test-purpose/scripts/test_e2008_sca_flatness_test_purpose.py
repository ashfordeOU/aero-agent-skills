"""Contract tests for the clause 6.4.3.17.1 cell assembly flatness purpose logic."""

import unittest

from e2008_sca_flatness_test_purpose_logic import (
    COMMON_OBJECTIVE,
    DEFAULT_FLATNESS_PURPOSE_POLICY,
    MEASUREMENT_NOT_PLANNED,
    MEASUREMENT_NOT_REQUIRED,
    MEASUREMENT_SERVES_PURPOSE,
    MEASUREMENT_UNDER_SCOPE,
    SHAPE_SETTING_OPERATIONS,
    STEP_OBJECTIVES,
    assess_flatness_purpose,
    grade_planned_measurement,
    integration_demand,
    measurement_is_justified,
    objectives_for,
    validate_integration_steps,
    validate_operations,
    validate_policy,
)

# A representative rigid-panel integration route for a completed assembly.
STEPS = [
    {"step": "adhesive-bonding-to-panel", "sensitivity_fraction": 0.8},
    {"step": "coverglass-clamp-down", "sensitivity_fraction": 0.5},
    {"step": "panel-thermal-contact", "sensitivity_fraction": 0.4},
]

OPERATIONS = ["coverglass-bonding", "interconnect-welding"]

PLAN = {
    "after_operations": ["coverglass-bonding", "interconnect-welding"],
    "before_integration": True,
    "subgroup_samples": 6,
}


def _spec(**overrides):
    spec = {
        "integrated_onto_rigid_panel": True,
        "integration_steps": [dict(s) for s in STEPS],
        "assembly_operations": list(OPERATIONS),
        "planned_measurement": dict(PLAN),
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
            validate_policy({"weights": {"paint-touch-up": 1.0}})

    def test_negative_weight_rejected(self):
        with self.assertRaises(ValueError):
            validate_policy({"weights": {"coverglass-clamp-down": -0.5}})

    def test_non_positive_trigger_rejected(self):
        with self.assertRaises(ValueError):
            validate_policy({"demand_trigger": 0.0})

    def test_non_integer_sample_floor_rejected(self):
        with self.assertRaises(ValueError):
            validate_policy({"min_subgroup_samples": 3.5})

    def test_non_mapping_policy_rejected(self):
        with self.assertRaises(ValueError):
            validate_policy(["demand_trigger"])


class IntegrationInventoryTests(unittest.TestCase):
    def test_inventory_is_normalized(self):
        inventory = validate_integration_steps(STEPS)
        self.assertEqual(len(inventory), 3)
        self.assertAlmostEqual(inventory["adhesive-bonding-to-panel"], 0.8, places=9)

    def test_unrecognised_step_rejected(self):
        with self.assertRaises(ValueError):
            validate_integration_steps([{"step": "shipping", "sensitivity_fraction": 0.4}])

    def test_repeated_step_rejected(self):
        with self.assertRaises(ValueError):
            validate_integration_steps(STEPS + [dict(STEPS[0])])

    def test_sensitivity_above_unity_rejected(self):
        with self.assertRaises(ValueError):
            validate_integration_steps(
                [{"step": "coverglass-clamp-down", "sensitivity_fraction": 1.2}]
            )

    def test_negative_sensitivity_rejected(self):
        with self.assertRaises(ValueError):
            validate_integration_steps(
                [{"step": "coverglass-clamp-down", "sensitivity_fraction": -0.2}]
            )

    def test_missing_sensitivity_rejected(self):
        with self.assertRaises(ValueError):
            validate_integration_steps([{"step": "coverglass-clamp-down"}])

    def test_empty_inventory_is_allowed_and_empty(self):
        self.assertEqual(validate_integration_steps([]), {})


class OperationValidationTests(unittest.TestCase):
    def test_operations_are_sorted(self):
        self.assertEqual(
            validate_operations(["interconnect-welding", "coverglass-bonding"]),
            ["coverglass-bonding", "interconnect-welding"],
        )

    def test_unrecognised_operation_rejected(self):
        with self.assertRaises(ValueError):
            validate_operations(["laser-marking"])

    def test_repeated_operation_rejected(self):
        with self.assertRaises(ValueError):
            validate_operations(["adhesive-cure", "adhesive-cure"])

    def test_known_operations_are_a_closed_set(self):
        for name in SHAPE_SETTING_OPERATIONS:
            self.assertIn(name, validate_operations(list(SHAPE_SETTING_OPERATIONS)))


class ObjectiveMappingTests(unittest.TestCase):
    def test_every_step_maps_to_an_objective(self):
        objectives = objectives_for(STEPS)
        self.assertIn(STEP_OBJECTIVES["adhesive-bonding-to-panel"], objectives)
        self.assertIn(STEP_OBJECTIVES["panel-thermal-contact"], objectives)

    def test_shared_objective_is_appended_once(self):
        self.assertEqual(objectives_for(STEPS).count(COMMON_OBJECTIVE), 1)

    def test_no_step_yields_no_objective(self):
        self.assertEqual(objectives_for([]), [])

    def test_envelope_step_carries_the_stack_height_objective(self):
        objectives = objectives_for(
            [{"step": "stay-out-envelope-fit", "sensitivity_fraction": 1.0}]
        )
        self.assertIn("panel-stack-height-envelope", objectives)


class IntegrationDemandTests(unittest.TestCase):
    def test_demand_is_the_weighted_sum(self):
        expected = 1.0 * 0.8 + 0.9 * 0.5 + 0.6 * 0.4
        self.assertAlmostEqual(integration_demand(STEPS), expected, places=9)

    def test_no_step_is_no_demand(self):
        self.assertAlmostEqual(integration_demand([]), 0.0, places=9)

    def test_zero_sensitivity_contributes_nothing(self):
        quiet = [{"step": "adhesive-bonding-to-panel", "sensitivity_fraction": 0.0}]
        self.assertAlmostEqual(integration_demand(quiet), 0.0, places=9)

    def test_declared_weight_changes_the_demand(self):
        demand = integration_demand(
            [{"step": "coverglass-clamp-down", "sensitivity_fraction": 1.0}],
            {"weights": {"coverglass-clamp-down": 2.0}},
        )
        self.assertAlmostEqual(demand, 2.0, places=9)


class JustificationTests(unittest.TestCase):
    def test_unconstrained_mounting_is_never_justified(self):
        self.assertFalse(measurement_is_justified(False, 9.0))

    def test_demand_above_the_trigger_justifies_the_measurement(self):
        self.assertTrue(measurement_is_justified(True, 1.5))

    def test_demand_below_the_trigger_does_not(self):
        self.assertFalse(measurement_is_justified(True, 0.4))

    def test_demand_landing_on_the_trigger_justifies_the_measurement(self):
        trigger = DEFAULT_FLATNESS_PURPOSE_POLICY["demand_trigger"]
        self.assertAlmostEqual(trigger, 1.0, places=9)
        self.assertTrue(measurement_is_justified(True, trigger))

    def test_non_boolean_mounting_flag_rejected(self):
        with self.assertRaises(ValueError):
            measurement_is_justified("rigid", 1.5)

    def test_negative_demand_rejected(self):
        with self.assertRaises(ValueError):
            measurement_is_justified(True, -0.5)


class PlannedMeasurementTests(unittest.TestCase):
    def test_plan_following_every_operation_is_clean(self):
        grading = grade_planned_measurement(PLAN, OPERATIONS)
        self.assertEqual(grading["shortfalls"], [])
        self.assertEqual(grading["unfollowed_operations"], [])

    def test_unfollowed_operation_is_a_shortfall(self):
        plan = dict(PLAN, after_operations=["coverglass-bonding"])
        grading = grade_planned_measurement(plan, OPERATIONS)
        self.assertEqual(grading["unfollowed_operations"], ["interconnect-welding"])
        self.assertEqual(len(grading["shortfalls"]), 1)

    def test_run_after_integration_is_a_shortfall(self):
        grading = grade_planned_measurement(dict(PLAN, before_integration=False), OPERATIONS)
        self.assertEqual(len(grading["shortfalls"]), 1)

    def test_too_few_samples_is_a_shortfall(self):
        grading = grade_planned_measurement(dict(PLAN, subgroup_samples=2), OPERATIONS)
        self.assertEqual(
            len([s for s in grading["shortfalls"] if "subgroup samples" in s]), 1
        )

    def test_unrecognised_planned_operation_rejected(self):
        with self.assertRaises(ValueError):
            grade_planned_measurement(dict(PLAN, after_operations=["sunbathing"]), OPERATIONS)

    def test_negative_sample_count_rejected(self):
        with self.assertRaises(ValueError):
            grade_planned_measurement(dict(PLAN, subgroup_samples=-1), OPERATIONS)

    def test_non_boolean_before_integration_rejected(self):
        with self.assertRaises(ValueError):
            grade_planned_measurement(dict(PLAN, before_integration="yes"), OPERATIONS)

    def test_missing_plan_key_rejected(self):
        plan = dict(PLAN)
        del plan["subgroup_samples"]
        with self.assertRaises(ValueError):
            grade_planned_measurement(plan, OPERATIONS)


class PurposeAssessmentTests(unittest.TestCase):
    def test_nominal_case_serves_the_purpose(self):
        result = assess_flatness_purpose(_spec())
        self.assertEqual(result["verdict"], MEASUREMENT_SERVES_PURPOSE)
        self.assertEqual(result["findings"], [])

    def test_unconstrained_mounting_does_not_earn_a_measurement(self):
        result = assess_flatness_purpose(_spec(integrated_onto_rigid_panel=False))
        self.assertEqual(result["verdict"], MEASUREMENT_NOT_REQUIRED)
        self.assertEqual(result["objectives"], [])

    def test_insensitive_route_does_not_earn_a_measurement(self):
        quiet = [{"step": "interconnect-stress-relief", "sensitivity_fraction": 0.2}]
        result = assess_flatness_purpose(_spec(integration_steps=quiet))
        self.assertEqual(result["verdict"], MEASUREMENT_NOT_REQUIRED)
        self.assertFalse(result["justified"])

    def test_justified_but_unplanned_is_its_own_verdict(self):
        spec = _spec()
        del spec["planned_measurement"]
        result = assess_flatness_purpose(spec)
        self.assertEqual(result["verdict"], MEASUREMENT_NOT_PLANNED)

    def test_plan_run_before_the_operations_is_under_scope(self):
        result = assess_flatness_purpose(
            _spec(planned_measurement=dict(PLAN, after_operations=[]))
        )
        self.assertEqual(result["verdict"], MEASUREMENT_UNDER_SCOPE)
        self.assertEqual(len(result["findings"]), 2)

    def test_objectives_are_reported_for_a_rigid_route(self):
        result = assess_flatness_purpose(_spec())
        self.assertIn(COMMON_OBJECTIVE, result["objectives"])
        self.assertEqual(result["step_count"], 3)

    def test_declared_trigger_can_stand_the_measurement_down(self):
        result = assess_flatness_purpose(_spec(policy={"demand_trigger": 5.0}))
        self.assertEqual(result["verdict"], MEASUREMENT_NOT_REQUIRED)

    def test_demand_is_echoed_with_its_trigger(self):
        result = assess_flatness_purpose(_spec())
        self.assertAlmostEqual(result["demand_trigger"], 1.0, places=9)
        self.assertAlmostEqual(
            result["integration_demand"], integration_demand(STEPS), places=9
        )

    def test_operations_are_echoed_sorted(self):
        result = assess_flatness_purpose(
            _spec(assembly_operations=["interconnect-welding", "coverglass-bonding"])
        )
        self.assertEqual(
            result["shape_setting_operations"],
            ["coverglass-bonding", "interconnect-welding"],
        )

    def test_non_boolean_mounting_flag_rejected(self):
        with self.assertRaises(ValueError):
            assess_flatness_purpose(_spec(integrated_onto_rigid_panel="true"))

    def test_missing_spec_key_rejected(self):
        spec = _spec()
        del spec["integration_steps"]
        with self.assertRaises(ValueError):
            assess_flatness_purpose(spec)

    def test_non_mapping_spec_rejected(self):
        with self.assertRaises(ValueError):
            assess_flatness_purpose(["integration_steps"])


if __name__ == "__main__":
    unittest.main()
