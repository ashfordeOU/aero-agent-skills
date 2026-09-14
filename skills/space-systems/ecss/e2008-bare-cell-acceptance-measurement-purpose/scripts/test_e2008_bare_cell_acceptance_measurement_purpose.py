"""Contract tests for the clause 7.3.2.2.1 bare-cell measurement purpose.

Every workflow step the SKILL.md sets out is exercised here, together with
the stop conditions the gate 3 contract reviews: a refused scoping policy,
an unrecognised acceptance decision, a plan missing a parameter a declared
decision leans on, and a budget too coarse to discriminate against the
drawing band.
"""

import math
import unittest

from e2008_bare_cell_acceptance_measurement_purpose_logic import (
    ARRAY_SIZING,
    BATCH_SCREENING,
    CURRENT_AT_TEST_VOLTAGE,
    DEFAULT_PURPOSE_POLICY,
    DEGRADATION_BASELINE,
    LOT_CONFORMITY,
    MEASUREMENT_CANNOT_DISCRIMINATE,
    NO_DECISION_DECLARED,
    OPEN_CIRCUIT_VOLTAGE,
    PARAMETER_COVERAGE_INCOMPLETE,
    PLAN_NOT_ESTABLISHED,
    PURPOSE_ESTABLISHED,
    SHARED_OBJECTIVE,
    SHORT_CIRCUIT_CURRENT,
    acceptance_band_fraction,
    acceptance_decision_inventory,
    assess_bare_cell_measurement_purpose,
    combined_relative_uncertainty,
    discrimination_ratio,
    fill_factor_proxy,
    measurement_resolves_band,
    operating_point_power_w,
    required_parameters,
    validate_measurement_plan,
    validate_purpose_policy,
)


def _policy(**overrides):
    policy = dict(DEFAULT_PURPOSE_POLICY)
    policy.update(overrides)
    return policy


def _plan(**overrides):
    plan = {
        "planned_parameters": [
            SHORT_CIRCUIT_CURRENT,
            CURRENT_AT_TEST_VOLTAGE,
            OPEN_CIRCUIT_VOLTAGE,
        ],
        "relative_uncertainty_components": {
            "irradiance-setting": 0.01,
            "cell-temperature": 0.005,
            "illuminated-area": 0.004,
            "instrument": 0.003,
        },
    }
    plan.update(overrides)
    return plan


def _case(**overrides):
    case = {
        "acceptance_decisions": [LOT_CONFORMITY, ARRAY_SIZING],
        "measurement_plan": _plan(),
        "nominal_cell": {
            "short_circuit_current_a": 0.5,
            "current_at_test_voltage_a": 0.48,
            "test_voltage_v": 2.35,
            "open_circuit_voltage_v": 2.69,
        },
        "drawing_band": {
            "nominal_current_a": 0.48,
            "minimum_current_a": 0.432,
        },
    }
    case.update(overrides)
    return case


class PolicyTests(unittest.TestCase):
    def test_default_policy_validates(self):
        self.assertIs(
            validate_purpose_policy(DEFAULT_PURPOSE_POLICY),
            DEFAULT_PURPOSE_POLICY,
        )

    def test_non_mapping_policy_rejected(self):
        with self.assertRaises(ValueError):
            validate_purpose_policy("min_discrimination_ratio")

    def test_uncertainty_share_above_one_rejected(self):
        with self.assertRaises(ValueError):
            validate_purpose_policy(_policy(max_uncertainty_fraction_of_band=1.4))

    def test_discrimination_ratio_below_one_rejected(self):
        with self.assertRaises(ValueError):
            validate_purpose_policy(_policy(min_discrimination_ratio=0.5))

    def test_zero_discrimination_ratio_rejected(self):
        with self.assertRaises(ValueError):
            validate_purpose_policy(_policy(min_discrimination_ratio=0.0))


class DecisionInventoryTests(unittest.TestCase):
    def test_each_declared_decision_carries_its_parameters(self):
        inventory = acceptance_decision_inventory([LOT_CONFORMITY])
        self.assertEqual(inventory[0]["decision"], LOT_CONFORMITY)
        self.assertIn(SHORT_CIRCUIT_CURRENT, inventory[0]["parameters"])

    def test_every_decision_carries_a_non_empty_objective(self):
        inventory = acceptance_decision_inventory(
            [LOT_CONFORMITY, ARRAY_SIZING, DEGRADATION_BASELINE, BATCH_SCREENING]
        )
        self.assertEqual(len(inventory), 4)
        for entry in inventory:
            self.assertTrue(entry["objective"].strip())

    def test_unrecognised_decision_rejected(self):
        with self.assertRaises(ValueError):
            acceptance_decision_inventory(["thermal-cycling-survival"])

    def test_duplicate_decision_rejected(self):
        with self.assertRaises(ValueError):
            acceptance_decision_inventory([ARRAY_SIZING, ARRAY_SIZING])

    def test_non_sequence_decision_record_rejected(self):
        with self.assertRaises(ValueError):
            acceptance_decision_inventory(LOT_CONFORMITY)

    def test_required_parameters_are_the_union_in_a_stable_order(self):
        wanted = required_parameters([ARRAY_SIZING, DEGRADATION_BASELINE])
        self.assertEqual(
            wanted, (SHORT_CIRCUIT_CURRENT, CURRENT_AT_TEST_VOLTAGE)
        )


class PlanTests(unittest.TestCase):
    def test_a_complete_plan_validates(self):
        self.assertEqual(len(validate_measurement_plan(_plan())), 3)

    def test_plan_measuring_nothing_rejected(self):
        with self.assertRaises(ValueError):
            validate_measurement_plan(_plan(planned_parameters=[]))

    def test_unrecognised_planned_parameter_rejected(self):
        with self.assertRaises(ValueError):
            validate_measurement_plan(_plan(planned_parameters=["series-resistance"]))

    def test_duplicate_planned_parameter_rejected(self):
        with self.assertRaises(ValueError):
            validate_measurement_plan(
                _plan(planned_parameters=[SHORT_CIRCUIT_CURRENT, SHORT_CIRCUIT_CURRENT])
            )


class QuantityTests(unittest.TestCase):
    def test_operating_point_power_is_the_product(self):
        self.assertAlmostEqual(operating_point_power_w(0.48, 2.35), 1.128, places=9)

    def test_zero_test_voltage_rejected(self):
        with self.assertRaises(ValueError):
            operating_point_power_w(0.48, 0.0)

    def test_fill_factor_proxy_is_the_rectangle_share(self):
        value = fill_factor_proxy(0.48, 2.35, 0.5, 2.69)
        self.assertAlmostEqual(value, (0.48 * 2.35) / (0.5 * 2.69), places=12)

    def test_fill_factor_proxy_admits_the_short_circuit_tie(self):
        value = fill_factor_proxy(0.5, 1.0, 0.5, 2.0)
        self.assertAlmostEqual(value, 0.5, places=12)

    def test_on_load_current_above_short_circuit_rejected(self):
        with self.assertRaises(ValueError):
            fill_factor_proxy(0.6, 2.35, 0.5, 2.69)

    def test_test_voltage_above_open_circuit_rejected(self):
        with self.assertRaises(ValueError):
            fill_factor_proxy(0.48, 3.2, 0.5, 2.69)

    def test_uncertainty_components_combine_in_quadrature(self):
        value = combined_relative_uncertainty({"a": 0.03, "b": 0.04})
        self.assertAlmostEqual(value, 0.05, places=12)

    def test_a_single_component_is_returned_unchanged(self):
        value = combined_relative_uncertainty({"irradiance-setting": 0.02})
        self.assertAlmostEqual(value, 0.02, places=12)

    def test_empty_uncertainty_budget_rejected(self):
        with self.assertRaises(ValueError):
            combined_relative_uncertainty({})

    def test_negative_uncertainty_component_rejected(self):
        with self.assertRaises(ValueError):
            combined_relative_uncertainty({"instrument": -0.01})

    def test_uncertainty_component_above_one_rejected(self):
        with self.assertRaises(ValueError):
            combined_relative_uncertainty({"instrument": 1.2})

    def test_acceptance_band_is_the_shortfall_below_nominal(self):
        self.assertAlmostEqual(
            acceptance_band_fraction(0.48, 0.432), 0.1, places=9
        )

    def test_a_minimum_equal_to_nominal_gives_a_zero_band(self):
        self.assertAlmostEqual(acceptance_band_fraction(0.48, 0.48), 0.0, places=12)

    def test_inverted_drawing_band_rejected(self):
        with self.assertRaises(ValueError):
            acceptance_band_fraction(0.4, 0.5)

    def test_discrimination_ratio_is_band_over_uncertainty(self):
        self.assertAlmostEqual(discrimination_ratio(0.1, 0.02), 5.0, places=9)

    def test_zero_uncertainty_rejected_rather_than_divided_by(self):
        with self.assertRaises(ValueError):
            discrimination_ratio(0.1, 0.0)


class ResolutionTests(unittest.TestCase):
    def test_a_comfortable_plan_resolves_the_band(self):
        self.assertTrue(measurement_resolves_band(0.10, 0.01))

    def test_a_plan_exactly_on_the_policy_ratio_resolves_the_band(self):
        self.assertTrue(measurement_resolves_band(0.20, 0.05))

    def test_a_plan_below_the_policy_ratio_does_not_resolve_the_band(self):
        self.assertFalse(measurement_resolves_band(0.10, 0.05))

    def test_a_zero_band_can_never_be_resolved(self):
        self.assertFalse(measurement_resolves_band(0.0, 0.01))


class AssessmentTests(unittest.TestCase):
    def test_a_scoped_plan_establishes_the_purpose(self):
        result = assess_bare_cell_measurement_purpose(_case())
        self.assertEqual(result["verdict"], PURPOSE_ESTABLISHED)
        self.assertEqual(result["findings"], [])

    def test_the_shared_objective_is_appended(self):
        result = assess_bare_cell_measurement_purpose(_case())
        self.assertIn(SHARED_OBJECTIVE, result["objectives"])

    def test_no_declared_decision_closes_the_assessment(self):
        result = assess_bare_cell_measurement_purpose(_case(acceptance_decisions=[]))
        self.assertEqual(result["verdict"], NO_DECISION_DECLARED)
        self.assertTrue(result["findings"])

    def test_a_missing_plan_closes_on_plan_not_established(self):
        case = _case()
        del case["measurement_plan"]
        result = assess_bare_cell_measurement_purpose(case)
        self.assertEqual(result["verdict"], PLAN_NOT_ESTABLISHED)

    def test_a_plan_missing_a_needed_parameter_is_incomplete(self):
        result = assess_bare_cell_measurement_purpose(
            _case(measurement_plan=_plan(planned_parameters=[SHORT_CIRCUIT_CURRENT]))
        )
        self.assertEqual(result["verdict"], PARAMETER_COVERAGE_INCOMPLETE)
        self.assertIn(CURRENT_AT_TEST_VOLTAGE, result["missing_parameters"])

    def test_a_coarse_plan_cannot_discriminate(self):
        result = assess_bare_cell_measurement_purpose(
            _case(
                measurement_plan=_plan(
                    relative_uncertainty_components={"irradiance-setting": 0.08}
                )
            )
        )
        self.assertEqual(result["verdict"], MEASUREMENT_CANNOT_DISCRIMINATE)
        self.assertTrue(result["findings"])

    def test_the_operating_point_and_fill_factor_are_reported(self):
        result = assess_bare_cell_measurement_purpose(_case())
        self.assertAlmostEqual(
            result["operating_point_power_w"], 0.48 * 2.35, places=12
        )
        self.assertTrue(0.0 < result["fill_factor_proxy"] <= 1.0)

    def test_the_combined_uncertainty_is_reported(self):
        result = assess_bare_cell_measurement_purpose(_case())
        expected = math.sqrt(0.01 ** 2 + 0.005 ** 2 + 0.004 ** 2 + 0.003 ** 2)
        self.assertAlmostEqual(
            result["combined_relative_uncertainty"], expected, places=12
        )

    def test_missing_drawing_band_rejected(self):
        case = _case()
        del case["drawing_band"]
        with self.assertRaises(ValueError):
            assess_bare_cell_measurement_purpose(case)

    def test_missing_decision_record_rejected(self):
        case = _case()
        del case["acceptance_decisions"]
        with self.assertRaises(ValueError):
            assess_bare_cell_measurement_purpose(case)

    def test_non_mapping_case_rejected(self):
        with self.assertRaises(ValueError):
            assess_bare_cell_measurement_purpose([LOT_CONFORMITY])


if __name__ == "__main__":
    unittest.main()
