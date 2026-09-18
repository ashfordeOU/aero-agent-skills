#!/usr/bin/env python3
"""Contract test for the thermal test temperature limit derivation (offline)."""

import copy
import unittest

from q7004_temperature_limit_derivation_logic import (
    ACCEPTANCE,
    CORRELATED_MODEL,
    DATA_BASES,
    DEFAULT_LIMIT_POLICY,
    MEASURED_HARDWARE,
    OBJECTIVES,
    QUALIFICATION,
    UNCORRELATED_MODEL,
    capability_check,
    derive_test_limits,
    limit_ladder_k,
    margin_build_up_k,
    margin_reduction_available_k,
    uncertainty_margin_k,
    validate_limit_policy,
    widen_limits_k,
)

CORRELATED_CASE = {
    "data_basis": CORRELATED_MODEL,
    "objective": QUALIFICATION,
    "predicted_min_k": 253.15,
    "predicted_max_k": 333.15,
    "capability_min_k": 200.0,
    "capability_max_k": 400.0,
}

MEASURED_CASE = {
    "data_basis": MEASURED_HARDWARE,
    "objective": ACCEPTANCE,
    "predicted_min_k": 253.15,
    "predicted_max_k": 333.15,
    "capability_min_k": 200.0,
    "capability_max_k": 400.0,
}


def _case(base, **overrides):
    case = copy.deepcopy(base)
    case.update(overrides)
    return case


class PolicyTests(unittest.TestCase):
    def test_default_policy_validates(self):
        self.assertIs(validate_limit_policy(DEFAULT_LIMIT_POLICY), DEFAULT_LIMIT_POLICY)

    def test_policy_covers_every_data_basis(self):
        for basis in DATA_BASES:
            self.assertIn(basis, DEFAULT_LIMIT_POLICY["uncertainty_margin_k"])

    def test_policy_missing_a_basis_rejected(self):
        broken = copy.deepcopy(DEFAULT_LIMIT_POLICY)
        del broken["uncertainty_margin_k"][CORRELATED_MODEL]
        with self.assertRaises(ValueError):
            validate_limit_policy(broken)

    def test_policy_inverting_the_data_basis_rejected(self):
        broken = copy.deepcopy(DEFAULT_LIMIT_POLICY)
        broken["uncertainty_margin_k"][UNCORRELATED_MODEL] = 1.0
        with self.assertRaises(ValueError):
            validate_limit_policy(broken)

    def test_policy_with_a_negative_acceptance_margin_rejected(self):
        broken = copy.deepcopy(DEFAULT_LIMIT_POLICY)
        broken["acceptance_margin_k"] = -5.0
        with self.assertRaises(ValueError):
            validate_limit_policy(broken)

    def test_policy_ceiling_below_the_acceptance_margin_rejected(self):
        broken = copy.deepcopy(DEFAULT_LIMIT_POLICY)
        broken["max_total_margin_k"] = 1.0
        with self.assertRaises(ValueError):
            validate_limit_policy(broken)

    def test_non_mapping_policy_rejected(self):
        with self.assertRaises(ValueError):
            validate_limit_policy("standard margins")


class UncertaintyTests(unittest.TestCase):
    def test_measured_hardware_owes_no_uncertainty_margin(self):
        self.assertAlmostEqual(uncertainty_margin_k(MEASURED_HARDWARE), 0.0, places=9)

    def test_an_uncorrelated_model_owes_the_most(self):
        margins = [uncertainty_margin_k(basis) for basis in DATA_BASES]
        self.assertAlmostEqual(
            max(margins), uncertainty_margin_k(UNCORRELATED_MODEL), places=9
        )

    def test_a_correlated_model_sits_between_the_two(self):
        self.assertGreater(
            uncertainty_margin_k(CORRELATED_MODEL),
            uncertainty_margin_k(MEASURED_HARDWARE),
        )
        self.assertLess(
            uncertainty_margin_k(CORRELATED_MODEL),
            uncertainty_margin_k(UNCORRELATED_MODEL),
        )

    def test_an_unknown_data_basis_rejected(self):
        with self.assertRaises(ValueError):
            uncertainty_margin_k("engineering judgement")


class BuildUpTests(unittest.TestCase):
    def test_an_acceptance_run_carries_no_qualification_increment(self):
        build_up = margin_build_up_k(MEASURED_HARDWARE, ACCEPTANCE)
        self.assertAlmostEqual(build_up["qualification_k"], 0.0, places=9)
        self.assertAlmostEqual(build_up["total_k"], 5.0, places=9)

    def test_a_qualification_run_adds_its_increment(self):
        build_up = margin_build_up_k(MEASURED_HARDWARE, QUALIFICATION)
        self.assertAlmostEqual(build_up["total_k"], 15.0, places=9)

    def test_a_weaker_data_basis_widens_the_total(self):
        weak = margin_build_up_k(UNCORRELATED_MODEL, QUALIFICATION)["total_k"]
        strong = margin_build_up_k(MEASURED_HARDWARE, QUALIFICATION)["total_k"]
        self.assertGreater(weak, strong)

    def test_the_programme_ceiling_caps_the_total(self):
        build_up = margin_build_up_k(UNCORRELATED_MODEL, QUALIFICATION)
        self.assertTrue(build_up["capped"])
        self.assertAlmostEqual(
            build_up["total_k"], DEFAULT_LIMIT_POLICY["max_total_margin_k"], places=9
        )

    def test_a_total_exactly_on_the_ceiling_is_not_capped(self):
        policy = copy.deepcopy(DEFAULT_LIMIT_POLICY)
        policy["max_total_margin_k"] = 15.0
        build_up = margin_build_up_k(MEASURED_HARDWARE, QUALIFICATION, policy)
        self.assertFalse(build_up["capped"])
        self.assertAlmostEqual(build_up["total_k"], 15.0, places=9)

    def test_an_unknown_objective_rejected(self):
        with self.assertRaises(ValueError):
            margin_build_up_k(MEASURED_HARDWARE, "protoflight-ish")


class WideningTests(unittest.TestCase):
    def test_widening_moves_both_ends_outward(self):
        widened = widen_limits_k(253.15, 333.15, 10.0)
        self.assertAlmostEqual(widened["min_k"], 243.15, places=9)
        self.assertAlmostEqual(widened["max_k"], 343.15, places=9)

    def test_a_zero_margin_leaves_the_envelope_alone(self):
        widened = widen_limits_k(253.15, 333.15, 0.0)
        self.assertAlmostEqual(widened["min_k"], 253.15, places=9)
        self.assertAlmostEqual(widened["max_k"], 333.15, places=9)

    def test_inverted_predictions_rejected(self):
        with self.assertRaises(ValueError):
            widen_limits_k(333.15, 253.15, 10.0)

    def test_a_margin_that_crosses_absolute_zero_rejected(self):
        with self.assertRaises(ValueError):
            widen_limits_k(5.0, 333.15, 20.0)

    def test_a_negative_margin_rejected(self):
        with self.assertRaises(ValueError):
            widen_limits_k(253.15, 333.15, -5.0)


class LadderTests(unittest.TestCase):
    def test_the_ladder_widens_at_every_step(self):
        ladder = limit_ladder_k(253.15, 333.15, CORRELATED_MODEL)
        self.assertLess(ladder["design"]["min_k"], ladder["predicted"]["min_k"])
        self.assertLess(ladder["acceptance"]["min_k"], ladder["design"]["min_k"])
        self.assertLess(ladder["qualification"]["min_k"], ladder["acceptance"]["min_k"])

    def test_the_hot_end_widens_in_step_with_the_cold_end(self):
        ladder = limit_ladder_k(253.15, 333.15, CORRELATED_MODEL)
        cold_growth = ladder["predicted"]["min_k"] - ladder["qualification"]["min_k"]
        hot_growth = ladder["qualification"]["max_k"] - ladder["predicted"]["max_k"]
        self.assertAlmostEqual(cold_growth, hot_growth, places=9)

    def test_a_measured_basis_gives_design_limits_at_the_prediction(self):
        ladder = limit_ladder_k(253.15, 333.15, MEASURED_HARDWARE)
        self.assertAlmostEqual(
            ladder["design"]["min_k"], ladder["predicted"]["min_k"], places=9
        )

    def test_the_qualification_step_is_the_policy_increment(self):
        ladder = limit_ladder_k(253.15, 333.15, MEASURED_HARDWARE)
        self.assertAlmostEqual(
            ladder["acceptance"]["max_k"]
            + DEFAULT_LIMIT_POLICY["qualification_margin_k"],
            ladder["qualification"]["max_k"],
            places=9,
        )

    def test_an_unknown_basis_in_the_ladder_rejected(self):
        with self.assertRaises(ValueError):
            limit_ladder_k(253.15, 333.15, "a feeling")


class CapabilityTests(unittest.TestCase):
    def test_limits_inside_the_capability_pass(self):
        check = capability_check(240.0, 350.0, 200.0, 400.0)
        self.assertTrue(check["within_capability"])
        self.assertAlmostEqual(check["remaining_margin_k"], 40.0, places=9)

    def test_a_hot_limit_beyond_the_capability_fails(self):
        check = capability_check(240.0, 420.0, 200.0, 400.0)
        self.assertFalse(check["hot_within_capability"])
        self.assertTrue(check["cold_within_capability"])

    def test_a_cold_limit_beyond_the_capability_fails(self):
        check = capability_check(180.0, 350.0, 200.0, 400.0)
        self.assertFalse(check["cold_within_capability"])

    def test_a_limit_exactly_on_the_capability_is_inside_it(self):
        check = capability_check(200.0, 400.0, 200.0, 400.0)
        self.assertTrue(check["within_capability"])
        self.assertAlmostEqual(check["remaining_margin_k"], 0.0, places=9)

    def test_an_inverted_capability_envelope_rejected(self):
        with self.assertRaises(ValueError):
            capability_check(240.0, 350.0, 400.0, 200.0)

    def test_a_non_numeric_capability_rejected(self):
        with self.assertRaises(ValueError):
            capability_check(240.0, 350.0, 200.0, "four hundred")


class ReductionTests(unittest.TestCase):
    def test_a_measured_basis_has_nothing_left_to_take_back(self):
        self.assertAlmostEqual(
            margin_reduction_available_k(MEASURED_HARDWARE), 0.0, places=9
        )

    def test_an_uncorrelated_model_has_the_most_to_take_back(self):
        self.assertGreater(
            margin_reduction_available_k(UNCORRELATED_MODEL),
            margin_reduction_available_k(CORRELATED_MODEL),
        )

    def test_the_reduction_is_never_negative(self):
        for basis in DATA_BASES:
            self.assertGreaterEqual(margin_reduction_available_k(basis), 0.0)


class DerivationTests(unittest.TestCase):
    def test_the_correlated_qualification_case_derives_the_expected_limits(self):
        result = derive_test_limits(CORRELATED_CASE)
        self.assertAlmostEqual(result["build_up"]["total_k"], 20.0, places=9)
        self.assertAlmostEqual(result["test_min_k"], 233.15, places=9)
        self.assertAlmostEqual(result["test_max_k"], 353.15, places=9)
        self.assertTrue(result["acceptable"])

    def test_the_measured_acceptance_case_is_the_narrowest(self):
        measured = derive_test_limits(MEASURED_CASE)
        correlated = derive_test_limits(CORRELATED_CASE)
        self.assertGreater(measured["test_min_k"], correlated["test_min_k"])
        self.assertLess(measured["test_max_k"], correlated["test_max_k"])

    def test_a_capped_build_up_is_reported(self):
        result = derive_test_limits(
            _case(CORRELATED_CASE, data_basis=UNCORRELATED_MODEL)
        )
        self.assertTrue(result["build_up"]["capped"])
        self.assertTrue(any("capped" in f for f in result["findings"]))

    def test_a_hot_limit_beyond_capability_makes_the_case_unacceptable(self):
        result = derive_test_limits(_case(CORRELATED_CASE, capability_max_k=340.0))
        self.assertFalse(result["acceptable"])
        self.assertTrue(any("hot limit" in f for f in result["findings"]))

    def test_a_cold_limit_beyond_capability_makes_the_case_unacceptable(self):
        result = derive_test_limits(_case(CORRELATED_CASE, capability_min_k=240.0))
        self.assertFalse(result["acceptable"])
        self.assertTrue(any("cold limit" in f for f in result["findings"]))

    def test_a_model_basis_owes_the_measurement_note(self):
        result = derive_test_limits(CORRELATED_CASE)
        self.assertTrue(any("measuring the flight hardware" in d for d in result["duties"]))

    def test_a_measured_basis_owes_no_measurement_note(self):
        result = derive_test_limits(MEASURED_CASE)
        self.assertFalse(
            any("measuring the flight hardware" in d for d in result["duties"])
        )

    def test_every_derivation_owes_the_traceability_duty(self):
        result = derive_test_limits(MEASURED_CASE)
        self.assertTrue(any("traced back" in d for d in result["duties"]))

    def test_the_ladder_travels_with_the_result(self):
        result = derive_test_limits(CORRELATED_CASE)
        self.assertIn("qualification", result["ladder"])
        self.assertIn("design", result["ladder"])

    def test_every_objective_and_basis_combination_derives(self):
        for basis in DATA_BASES:
            for objective in OBJECTIVES:
                result = derive_test_limits(
                    _case(CORRELATED_CASE, data_basis=basis, objective=objective)
                )
                self.assertGreater(result["test_max_k"], result["test_min_k"])

    def test_a_case_without_a_capability_envelope_rejected(self):
        case = _case(CORRELATED_CASE)
        del case["capability_max_k"]
        with self.assertRaises(ValueError):
            derive_test_limits(case)

    def test_an_unknown_data_basis_in_the_case_rejected(self):
        with self.assertRaises(ValueError):
            derive_test_limits(_case(CORRELATED_CASE, data_basis="a feeling"))

    def test_a_non_mapping_case_rejected(self):
        with self.assertRaises(ValueError):
            derive_test_limits("minus twenty to plus sixty")


if __name__ == "__main__":
    unittest.main()
