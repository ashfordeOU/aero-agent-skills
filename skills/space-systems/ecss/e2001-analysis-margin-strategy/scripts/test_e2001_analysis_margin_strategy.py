#!/usr/bin/env python3
"""Contract test for the multipaction margin-strategy choice (offline)."""

import copy
import unittest

from e2001_analysis_margin_strategy_logic import (
    BOUNDING_ENVELOPE_STRATEGY,
    CRITICALITY_LEVELS,
    DEFAULT_MARGIN_POLICY,
    DIMENSION_BASES,
    MEASURED_DATA_STRATEGY,
    MIXED_BASIS_STRATEGY,
    YIELD_BASES,
    achieved_margin_db,
    effective_gap_m,
    effective_peak_yield,
    margin_reduction_from_measurement,
    plan_margin_strategy,
    required_margin_db,
    select_margin_strategy,
    validate_margin_policy,
)

BEST_CASE = {
    "dimension_basis": "measured-hardware",
    "yield_basis": "surface-measured",
    "criticality": "minor",
    "measured_gap_m": 1.0e-3,
    "declared_peak_yield": 1.8,
    "predicted_breakdown_power_w": 400.0,
    "operating_power_w": 100.0,
}

WEAK_CASE = {
    "dimension_basis": "nominal-design",
    "yield_basis": "generic-literature",
    "criticality": "catastrophic",
    "nominal_gap_m": 1.0e-3,
    "declared_peak_yield": 1.6,
    "bounding_peak_yield": 2.1,
    "predicted_breakdown_power_w": 400.0,
    "operating_power_w": 100.0,
}


def _case(base, **overrides):
    case = copy.deepcopy(base)
    case.update(overrides)
    return case


class PolicyTests(unittest.TestCase):
    def test_default_policy_validates(self):
        self.assertIs(validate_margin_policy(DEFAULT_MARGIN_POLICY), DEFAULT_MARGIN_POLICY)

    def test_policy_covers_every_dimension_basis(self):
        for basis in DIMENSION_BASES:
            self.assertIn(basis, DEFAULT_MARGIN_POLICY["dimension_increment_db"])

    def test_policy_covers_every_yield_basis(self):
        for basis in YIELD_BASES:
            self.assertIn(basis, DEFAULT_MARGIN_POLICY["yield_increment_db"])

    def test_policy_covers_every_criticality_level(self):
        for level in CRITICALITY_LEVELS:
            self.assertIn(level, DEFAULT_MARGIN_POLICY["criticality_increment_db"])

    def test_non_mapping_policy_rejected(self):
        with self.assertRaises(ValueError):
            validate_margin_policy("default")

    def test_policy_missing_a_basis_rejected(self):
        broken = copy.deepcopy(DEFAULT_MARGIN_POLICY)
        del broken["yield_increment_db"]["material-measured"]
        with self.assertRaises(ValueError):
            validate_margin_policy(broken)

    def test_policy_with_negative_increment_rejected(self):
        broken = copy.deepcopy(DEFAULT_MARGIN_POLICY)
        broken["dimension_increment_db"]["nominal-design"] = -1.0
        with self.assertRaises(ValueError):
            validate_margin_policy(broken)

    def test_policy_cap_below_base_rejected(self):
        broken = copy.deepcopy(DEFAULT_MARGIN_POLICY)
        broken["max_margin_db"] = 1.0
        with self.assertRaises(ValueError):
            validate_margin_policy(broken)

    def test_policy_with_non_mapping_table_rejected(self):
        broken = copy.deepcopy(DEFAULT_MARGIN_POLICY)
        broken["criticality_increment_db"] = 3.0
        with self.assertRaises(ValueError):
            validate_margin_policy(broken)


class EffectiveGapTests(unittest.TestCase):
    def test_measured_basis_uses_the_measured_gap(self):
        self.assertAlmostEqual(
            effective_gap_m("measured-hardware", measured_gap_m=0.94e-3),
            0.94e-3,
            places=12,
        )

    def test_nominal_basis_uses_the_drawing_value(self):
        self.assertAlmostEqual(
            effective_gap_m("nominal-design", nominal_gap_m=1.0e-3), 1.0e-3, places=12
        )

    def test_worst_case_basis_subtracts_the_tolerance(self):
        self.assertAlmostEqual(
            effective_gap_m(
                "tolerance-worst-case", nominal_gap_m=1.0e-3, tolerance_m=5.0e-5
            ),
            0.95e-3,
            places=12,
        )

    def test_worst_case_gap_is_smaller_than_nominal(self):
        worst = effective_gap_m(
            "tolerance-worst-case", nominal_gap_m=1.0e-3, tolerance_m=5.0e-5
        )
        nominal = effective_gap_m("nominal-design", nominal_gap_m=1.0e-3)
        self.assertLess(worst, nominal)

    def test_unknown_dimension_basis_rejected(self):
        with self.assertRaises(ValueError):
            effective_gap_m("guessed", nominal_gap_m=1.0e-3)

    def test_measured_basis_without_a_measurement_rejected(self):
        with self.assertRaises(ValueError):
            effective_gap_m("measured-hardware")

    def test_worst_case_basis_without_a_tolerance_rejected(self):
        with self.assertRaises(ValueError):
            effective_gap_m("tolerance-worst-case", nominal_gap_m=1.0e-3)

    def test_tolerance_consuming_the_gap_rejected(self):
        with self.assertRaises(ValueError):
            effective_gap_m(
                "tolerance-worst-case", nominal_gap_m=1.0e-3, tolerance_m=1.0e-3
            )

    def test_negative_nominal_gap_rejected(self):
        with self.assertRaises(ValueError):
            effective_gap_m("nominal-design", nominal_gap_m=-1.0e-3)

    def test_negative_tolerance_rejected(self):
        with self.assertRaises(ValueError):
            effective_gap_m(
                "tolerance-worst-case", nominal_gap_m=1.0e-3, tolerance_m=-5.0e-5
            )


class EffectiveYieldTests(unittest.TestCase):
    def test_surface_measured_yield_is_used_as_declared(self):
        result = effective_peak_yield("surface-measured", 1.8)
        self.assertAlmostEqual(result["peak_yield"], 1.8, places=12)
        self.assertFalse(result["bounded"])
        self.assertEqual(result["findings"], [])

    def test_material_measured_yield_is_used_as_declared(self):
        result = effective_peak_yield("material-measured", 2.0)
        self.assertAlmostEqual(result["peak_yield"], 2.0, places=12)

    def test_generic_basis_carries_the_bounding_value(self):
        result = effective_peak_yield("generic-literature", 1.6, bounding_peak_yield=2.1)
        self.assertAlmostEqual(result["peak_yield"], 2.1, places=12)
        self.assertTrue(result["bounded"])
        self.assertTrue(any("bounding" in f for f in result["findings"]))

    def test_generic_basis_keeps_a_higher_declared_value(self):
        result = effective_peak_yield("generic-literature", 2.4, bounding_peak_yield=2.1)
        self.assertAlmostEqual(result["peak_yield"], 2.4, places=12)
        self.assertEqual(result["findings"], [])

    def test_generic_basis_without_a_bounding_value_rejected(self):
        with self.assertRaises(ValueError):
            effective_peak_yield("generic-literature", 1.6)

    def test_unknown_yield_basis_rejected(self):
        with self.assertRaises(ValueError):
            effective_peak_yield("vendor-rumour", 1.8)

    def test_zero_declared_yield_rejected(self):
        with self.assertRaises(ValueError):
            effective_peak_yield("surface-measured", 0.0)

    def test_negative_bounding_yield_rejected(self):
        with self.assertRaises(ValueError):
            effective_peak_yield("generic-literature", 1.6, bounding_peak_yield=-2.1)


class RequiredMarginTests(unittest.TestCase):
    def test_best_data_and_lowest_consequence_give_the_base_margin(self):
        self.assertAlmostEqual(
            required_margin_db("measured-hardware", "surface-measured", "minor"),
            3.0,
            places=12,
        )

    def test_each_weaker_basis_adds_to_the_requirement(self):
        base = required_margin_db("measured-hardware", "surface-measured", "minor")
        worse_gap = required_margin_db("tolerance-worst-case", "surface-measured", "minor")
        worse_yield = required_margin_db("measured-hardware", "material-measured", "minor")
        self.assertGreater(worse_gap, base)
        self.assertGreater(worse_yield, base)

    def test_weakest_bases_with_catastrophic_consequence(self):
        self.assertAlmostEqual(
            required_margin_db("nominal-design", "generic-literature", "catastrophic"),
            12.0,
            places=12,
        )

    def test_requirement_is_capped_by_the_policy(self):
        policy = copy.deepcopy(DEFAULT_MARGIN_POLICY)
        policy["max_margin_db"] = 8.0
        self.assertAlmostEqual(
            required_margin_db(
                "nominal-design", "generic-literature", "catastrophic", policy
            ),
            8.0,
            places=12,
        )

    def test_criticality_raises_the_requirement(self):
        minor = required_margin_db("measured-hardware", "surface-measured", "minor")
        major = required_margin_db("measured-hardware", "surface-measured", "major")
        self.assertGreater(major, minor)

    def test_unknown_criticality_rejected(self):
        with self.assertRaises(ValueError):
            required_margin_db("measured-hardware", "surface-measured", "annoying")

    def test_unknown_dimension_basis_rejected(self):
        with self.assertRaises(ValueError):
            required_margin_db("estimated", "surface-measured", "minor")

    def test_broken_policy_rejected(self):
        broken = copy.deepcopy(DEFAULT_MARGIN_POLICY)
        del broken["base_margin_db"]
        with self.assertRaises(ValueError):
            required_margin_db("measured-hardware", "surface-measured", "minor", broken)


class StrategySelectionTests(unittest.TestCase):
    def test_both_bases_measured_give_the_measured_data_strategy(self):
        result = select_margin_strategy("measured-hardware", "surface-measured")
        self.assertEqual(result["strategy"], MEASURED_DATA_STRATEGY)
        self.assertEqual(result["duties"], [])

    def test_a_weakest_basis_forces_the_bounding_envelope_strategy(self):
        self.assertEqual(
            select_margin_strategy("nominal-design", "surface-measured")["strategy"],
            BOUNDING_ENVELOPE_STRATEGY,
        )
        self.assertEqual(
            select_margin_strategy("measured-hardware", "generic-literature")["strategy"],
            BOUNDING_ENVELOPE_STRATEGY,
        )

    def test_intermediate_bases_give_the_mixed_basis_strategy(self):
        self.assertEqual(
            select_margin_strategy("tolerance-worst-case", "material-measured")[
                "strategy"
            ],
            MIXED_BASIS_STRATEGY,
        )

    def test_nominal_dimension_basis_carries_a_tolerance_duty(self):
        duties = select_margin_strategy("nominal-design", "surface-measured")["duties"]
        self.assertTrue(any("tolerance" in duty for duty in duties))

    def test_generic_yield_basis_carries_a_bounding_duty(self):
        duties = select_margin_strategy("measured-hardware", "generic-literature")[
            "duties"
        ]
        self.assertTrue(any("bounding yield" in duty for duty in duties))

    def test_unknown_basis_rejected(self):
        with self.assertRaises(ValueError):
            select_margin_strategy("measured-hardware", "hearsay")


class AchievedMarginTests(unittest.TestCase):
    def test_factor_of_four_is_about_six_decibel(self):
        self.assertAlmostEqual(achieved_margin_db(400.0, 100.0), 6.0206, places=4)

    def test_equal_levels_give_zero_margin(self):
        self.assertAlmostEqual(achieved_margin_db(100.0, 100.0), 0.0, places=12)

    def test_operating_above_breakdown_gives_a_negative_margin(self):
        self.assertLess(achieved_margin_db(80.0, 100.0), 0.0)

    def test_zero_operating_level_rejected(self):
        with self.assertRaises(ValueError):
            achieved_margin_db(400.0, 0.0)

    def test_non_numeric_breakdown_level_rejected(self):
        with self.assertRaises(ValueError):
            achieved_margin_db("400 W", 100.0)


class MarginReductionTests(unittest.TestCase):
    def test_no_reduction_available_when_both_bases_are_measured(self):
        self.assertAlmostEqual(
            margin_reduction_from_measurement(
                "measured-hardware", "surface-measured", "major"
            ),
            0.0,
            places=12,
        )

    def test_reduction_equals_the_two_increments(self):
        self.assertAlmostEqual(
            margin_reduction_from_measurement(
                "nominal-design", "generic-literature", "minor"
            ),
            6.0,
            places=12,
        )

    def test_reduction_is_never_negative(self):
        for dimension in DIMENSION_BASES:
            for basis in YIELD_BASES:
                self.assertGreaterEqual(
                    margin_reduction_from_measurement(dimension, basis, "major"), 0.0
                )


class PlanTests(unittest.TestCase):
    def test_best_case_plan_is_compliant(self):
        result = plan_margin_strategy(BEST_CASE)
        self.assertEqual(result["strategy"], MEASURED_DATA_STRATEGY)
        self.assertEqual(result["verdict"], "margin-met")
        self.assertTrue(result["compliant"])
        self.assertAlmostEqual(result["required_margin_db"], 3.0, places=12)
        self.assertAlmostEqual(result["achieved_margin_db"], 6.0206, places=4)

    def test_weak_case_plan_is_not_compliant(self):
        result = plan_margin_strategy(WEAK_CASE)
        self.assertEqual(result["strategy"], BOUNDING_ENVELOPE_STRATEGY)
        self.assertEqual(result["verdict"], "margin-not-met")
        self.assertFalse(result["compliant"])
        self.assertAlmostEqual(result["required_margin_db"], 12.0, places=12)
        self.assertTrue(any("achieved" in f for f in result["findings"]))

    def test_weak_case_carries_the_bounding_yield(self):
        result = plan_margin_strategy(WEAK_CASE)
        self.assertTrue(result["yield_is_bounded"])
        self.assertAlmostEqual(result["effective_peak_yield"], 2.1, places=12)

    def test_weak_case_reports_the_reduction_on_offer(self):
        result = plan_margin_strategy(WEAK_CASE)
        self.assertAlmostEqual(result["margin_reduction_available_db"], 6.0, places=12)

    def test_worst_case_gap_is_carried_into_the_plan(self):
        case = _case(
            BEST_CASE,
            dimension_basis="tolerance-worst-case",
            nominal_gap_m=1.0e-3,
            tolerance_m=6.0e-5,
            measured_gap_m=None,
        )
        result = plan_margin_strategy(case)
        self.assertAlmostEqual(result["effective_gap_m"], 0.94e-3, places=12)

    def test_margin_exactly_on_the_requirement_is_compliant(self):
        # 80 W x 10**0.3 evaluates one unit in the last place below 3.0 dB.
        case = _case(
            BEST_CASE,
            operating_power_w=80.0,
            predicted_breakdown_power_w=80.0 * (10.0 ** 0.3),
        )
        self.assertLess(
            achieved_margin_db(case["predicted_breakdown_power_w"], 80.0), 3.0
        )
        result = plan_margin_strategy(case)
        self.assertTrue(result["compliant"])
        self.assertEqual(result["verdict"], "margin-met")

    def test_mixed_basis_margin_exactly_on_the_requirement_is_compliant(self):
        # 42 W x 10**0.5 evaluates one unit in the last place below 5.0 dB.
        case = _case(
            BEST_CASE,
            dimension_basis="tolerance-worst-case",
            yield_basis="material-measured",
            nominal_gap_m=1.0e-3,
            tolerance_m=5.0e-5,
            measured_gap_m=None,
            operating_power_w=42.0,
            predicted_breakdown_power_w=42.0 * (10.0 ** 0.5),
        )
        result = plan_margin_strategy(case)
        self.assertAlmostEqual(result["required_margin_db"], 5.0, places=12)
        self.assertTrue(result["compliant"])

    def test_plan_without_levels_is_not_evaluated(self):
        case = _case(BEST_CASE)
        del case["predicted_breakdown_power_w"]
        result = plan_margin_strategy(case)
        self.assertEqual(result["verdict"], "margin-not-evaluated")
        self.assertIsNone(result["compliant"])
        self.assertIsNone(result["achieved_margin_db"])
        self.assertTrue(any("not yet demonstrated" in f for f in result["findings"]))

    def test_plan_rejects_an_unknown_dimension_basis(self):
        with self.assertRaises(ValueError):
            plan_margin_strategy(_case(BEST_CASE, dimension_basis="sketched"))

    def test_plan_rejects_a_missing_yield_basis(self):
        case = _case(BEST_CASE)
        del case["yield_basis"]
        with self.assertRaises(ValueError):
            plan_margin_strategy(case)

    def test_plan_rejects_a_non_mapping_case(self):
        with self.assertRaises(ValueError):
            plan_margin_strategy("measured-hardware")

    def test_plan_rejects_a_generic_yield_without_a_bounding_value(self):
        case = _case(WEAK_CASE)
        del case["bounding_peak_yield"]
        with self.assertRaises(ValueError):
            plan_margin_strategy(case)

    def test_weaker_data_never_lowers_the_requirement(self):
        strong = plan_margin_strategy(BEST_CASE)["required_margin_db"]
        weak = plan_margin_strategy(WEAK_CASE)["required_margin_db"]
        self.assertGreater(weak, strong)


if __name__ == "__main__":
    unittest.main()
