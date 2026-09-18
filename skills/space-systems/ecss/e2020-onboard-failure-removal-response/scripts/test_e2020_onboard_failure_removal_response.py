"""Contract tests for the clause 5.2.14.2.1 onboard-response logic."""

import unittest

from e2020_onboard_failure_removal_response_logic import (
    ABSOLUTE_ZERO_C,
    ONBOARD_ACTIONS,
    SURVIVAL_TOLERANCE_K,
    assess_onboard_removal_response,
    dissipation_w,
    part_response,
    residual_current_a,
    thermal_time_constant_s,
    time_to_limit_s,
    transient_temperature_c,
    validate_response_case,
)

# 28 V across the failed switch at 2.0 A is 56 W. The hybrid substrate is
# coupled 1.5 K/W with 40 J/K, so it runs to 124 C with a 60 s time constant
# against a 100 C limit; the board track is 0.8 K/W with 200 J/K and settles
# at 84.8 C against a 105 C limit, so it never reaches its own bound.
PARTS = [
    {
        "name": "hybrid-substrate",
        "coupling_k_per_w": 1.5,
        "heat_capacity_j_per_k": 40.0,
        "rated_max_c": 125.0,
        "derating_margin_k": 25.0,
    },
    {
        "name": "board-track",
        "coupling_k_per_w": 0.8,
        "heat_capacity_j_per_k": 200.0,
        "rated_max_c": 125.0,
        "derating_margin_k": 20.0,
    },
]


def case_with(**overrides):
    spec = {
        "switch": "LCL-6 main switch",
        "voltage_drop_v": 28.0,
        "failed_current_a": 2.0,
        "reference_temp_c": 40.0,
        "action": "reduce-load",
        "reduced_current_a": 0.4,
        "response_latency_s": 12.0,
        "parts": [dict(part) for part in PARTS],
    }
    spec.update(overrides)
    return spec


def switch_off_case(effective=True, latency_s=12.0):
    spec = case_with()
    del spec["reduced_current_a"]
    spec["action"] = "switch-off"
    spec["off_command_effective"] = effective
    spec["response_latency_s"] = latency_s
    return spec


def no_action_case():
    spec = case_with()
    del spec["reduced_current_a"]
    del spec["response_latency_s"]
    spec["action"] = "none"
    return spec


class ValidationTests(unittest.TestCase):
    def test_valid_case_is_normalised_with_part_time_constants(self):
        case = validate_response_case(case_with())
        self.assertEqual(case["switch"], "LCL-6 main switch")
        self.assertEqual(case["action"], "reduce-load")
        self.assertAlmostEqual(case["parts"][0]["time_constant_s"], 60.0, places=9)
        self.assertAlmostEqual(case["parts"][1]["time_constant_s"], 160.0, places=9)

    def test_derated_limit_is_the_rating_less_the_withheld_margin(self):
        case = validate_response_case(case_with())
        self.assertAlmostEqual(case["parts"][0]["derated_limit_c"], 100.0, places=9)

    def test_non_mapping_case_rejected(self):
        with self.assertRaises(ValueError):
            validate_response_case("reduce-load")

    def test_missing_action_rejected(self):
        spec = case_with()
        del spec["action"]
        with self.assertRaises(ValueError):
            validate_response_case(spec)

    def test_unknown_action_rejected(self):
        with self.assertRaises(ValueError):
            validate_response_case(case_with(action="reset-the-bus"))

    def test_reduce_load_without_a_reduced_current_rejected(self):
        spec = case_with()
        del spec["reduced_current_a"]
        with self.assertRaises(ValueError):
            validate_response_case(spec)

    def test_a_reduced_current_that_does_not_reduce_is_rejected(self):
        with self.assertRaises(ValueError):
            validate_response_case(case_with(reduced_current_a=2.0))

    def test_reduced_current_on_a_switch_off_action_rejected(self):
        spec = switch_off_case()
        spec["reduced_current_a"] = 0.4
        with self.assertRaises(ValueError):
            validate_response_case(spec)

    def test_switch_off_without_an_effectiveness_flag_rejected(self):
        spec = switch_off_case()
        del spec["off_command_effective"]
        with self.assertRaises(ValueError):
            validate_response_case(spec)

    def test_non_boolean_effectiveness_flag_rejected(self):
        spec = switch_off_case()
        spec["off_command_effective"] = "yes"
        with self.assertRaises(ValueError):
            validate_response_case(spec)

    def test_an_action_without_a_latency_rejected(self):
        spec = case_with()
        del spec["response_latency_s"]
        with self.assertRaises(ValueError):
            validate_response_case(spec)

    def test_a_latency_on_a_none_action_rejected(self):
        spec = no_action_case()
        spec["response_latency_s"] = 12.0
        with self.assertRaises(ValueError):
            validate_response_case(spec)

    def test_zero_heat_capacity_rejected(self):
        parts = [dict(PARTS[0])]
        parts[0]["heat_capacity_j_per_k"] = 0.0
        with self.assertRaises(ValueError):
            validate_response_case(case_with(parts=parts))

    def test_duplicate_part_name_rejected(self):
        with self.assertRaises(ValueError):
            validate_response_case(case_with(parts=[dict(PARTS[0]), dict(PARTS[0])]))

    def test_reference_below_absolute_zero_rejected(self):
        with self.assertRaises(ValueError):
            validate_response_case(case_with(reference_temp_c=ABSOLUTE_ZERO_C - 5.0))

    def test_a_part_already_at_its_limit_rejected(self):
        with self.assertRaises(ValueError):
            validate_response_case(case_with(reference_temp_c=110.0))

    def test_the_action_vocabulary_is_the_documented_one(self):
        self.assertEqual(ONBOARD_ACTIONS, ("reduce-load", "switch-off", "none"))


class ThermalTests(unittest.TestCase):
    def test_dissipation_is_the_drop_times_the_current(self):
        self.assertAlmostEqual(dissipation_w(28.0, 2.0), 56.0, places=9)

    def test_dissipation_of_an_opened_switch_is_zero(self):
        self.assertAlmostEqual(dissipation_w(28.0, 0.0), 0.0, places=9)

    def test_dissipation_rejects_a_negative_current(self):
        with self.assertRaises(ValueError):
            dissipation_w(28.0, -0.1)

    def test_time_constant_is_coupling_times_heat_capacity(self):
        self.assertAlmostEqual(thermal_time_constant_s(1.5, 40.0), 60.0, places=9)

    def test_transient_starts_at_the_reference_temperature(self):
        self.assertAlmostEqual(
            transient_temperature_c(40.0, 56.0, 1.5, 60.0, 0.0), 40.0, places=9
        )

    def test_transient_reaches_the_expected_temperature_at_the_latency(self):
        self.assertAlmostEqual(
            transient_temperature_c(40.0, 56.0, 1.5, 60.0, 12.0), 55.226617, places=6
        )

    def test_transient_rejects_a_negative_elapsed_time(self):
        with self.assertRaises(ValueError):
            transient_temperature_c(40.0, 56.0, 1.5, 60.0, -1.0)

    def test_time_to_limit_is_the_documented_value(self):
        self.assertAlmostEqual(
            time_to_limit_s(40.0, 56.0, 1.5, 60.0, 100.0), 75.165778, places=6
        )

    def test_time_to_limit_is_none_when_the_asymptote_stays_under_the_bound(self):
        self.assertIsNone(time_to_limit_s(40.0, 56.0, 0.8, 160.0, 105.0))

    def test_time_to_limit_is_none_when_the_asymptote_lands_on_the_bound(self):
        # 56 W through 1.0 K/W from 40 C settles at exactly 96 C.
        self.assertIsNone(time_to_limit_s(40.0, 56.0, 1.0, 100.0, 96.0))

    def test_survival_tolerance_is_narrow_enough_to_catch_a_real_overshoot(self):
        self.assertLess(SURVIVAL_TOLERANCE_K, 1e-6)


class ResidualTests(unittest.TestCase):
    def test_reduce_load_leaves_the_reduced_current_running(self):
        case = validate_response_case(case_with())
        self.assertAlmostEqual(residual_current_a(case), 0.4, places=9)

    def test_an_effective_off_command_leaves_nothing_running(self):
        case = validate_response_case(switch_off_case(effective=True))
        self.assertAlmostEqual(residual_current_a(case), 0.0, places=9)

    def test_an_ineffective_off_command_leaves_the_failed_current_running(self):
        case = validate_response_case(switch_off_case(effective=False))
        self.assertAlmostEqual(residual_current_a(case), 2.0, places=9)

    def test_no_action_leaves_the_failed_current_running(self):
        case = validate_response_case(no_action_case())
        self.assertAlmostEqual(residual_current_a(case), 2.0, places=9)

    def test_part_response_reports_both_halves_for_one_part(self):
        case = validate_response_case(case_with())
        item = part_response(case["parts"][0], case, 56.0, 11.2)
        self.assertAlmostEqual(item["temperature_at_response_c"], 55.226617, places=6)
        self.assertAlmostEqual(item["residual_temperature_c"], 56.8, places=9)
        self.assertTrue(item["survives_transient"])
        self.assertTrue(item["survives_residual"])


class AssessmentTests(unittest.TestCase):
    def test_a_fast_load_reduction_is_compliant(self):
        result = assess_onboard_removal_response(case_with())
        self.assertEqual(result["verdict"], "compliant")
        self.assertEqual(result["effective_action"], "reduce-load")
        self.assertEqual(result["findings"], [])
        self.assertAlmostEqual(result["residual_power_w"], 11.2, places=9)

    def test_a_load_reduction_carries_a_residual_note(self):
        result = assess_onboard_removal_response(case_with())
        self.assertEqual(len(result["notes"]), 1)

    def test_an_effective_off_command_removes_the_residual_entirely(self):
        result = assess_onboard_removal_response(switch_off_case(effective=True))
        self.assertEqual(result["verdict"], "compliant")
        self.assertAlmostEqual(result["residual_power_w"], 0.0, places=9)
        self.assertEqual(result["notes"], [])

    def test_an_ineffective_off_command_degenerates_to_no_response(self):
        result = assess_onboard_removal_response(switch_off_case(effective=False))
        self.assertEqual(result["declared_action"], "switch-off")
        self.assertEqual(result["effective_action"], "none")
        self.assertEqual(result["verdict"], "non-compliant")
        self.assertEqual(result["residual_casualties"], ["hybrid-substrate"])

    def test_no_declared_action_is_reported_against_the_uncleared_case(self):
        result = assess_onboard_removal_response(no_action_case())
        self.assertEqual(result["effective_action"], "none")
        self.assertEqual(result["verdict"], "non-compliant")
        self.assertIn("no onboard response", result["findings"][0])

    def test_a_slow_response_loses_the_part_during_the_latency(self):
        result = assess_onboard_removal_response(
            switch_off_case(effective=True, latency_s=120.0)
        )
        self.assertEqual(result["verdict"], "non-compliant")
        self.assertEqual(result["transient_casualties"], ["hybrid-substrate"])
        self.assertEqual(result["residual_casualties"], [])

    def test_the_transient_finding_names_the_time_the_part_had(self):
        result = assess_onboard_removal_response(
            switch_off_case(effective=True, latency_s=120.0)
        )
        joined = " | ".join(result["findings"])
        self.assertIn("hybrid-substrate", joined)
        self.assertIn("75.2 s", joined)

    def test_the_latency_budget_is_the_earliest_part_to_reach_its_limit(self):
        result = assess_onboard_removal_response(case_with())
        self.assertAlmostEqual(result["latency_budget_s"], 75.165778, places=6)

    def test_a_part_that_never_reaches_its_limit_reports_no_time(self):
        result = assess_onboard_removal_response(case_with())
        board = [i for i in result["part_responses"] if i["name"] == "board-track"][0]
        self.assertIsNone(board["time_to_limit_s"])

    def test_a_deep_enough_reduction_still_fails_when_the_residual_is_too_high(self):
        result = assess_onboard_removal_response(case_with(reduced_current_a=1.8))
        self.assertEqual(result["verdict"], "non-compliant")
        self.assertEqual(result["residual_casualties"], ["hybrid-substrate"])
        self.assertEqual(result["transient_casualties"], [])

    def test_the_pre_response_dissipation_is_reported(self):
        result = assess_onboard_removal_response(case_with())
        self.assertAlmostEqual(result["pre_response_power_w"], 56.0, places=9)
        self.assertAlmostEqual(result["response_latency_s"], 12.0, places=9)

    def test_every_part_gets_its_own_response_row(self):
        result = assess_onboard_removal_response(case_with())
        self.assertEqual(
            [i["name"] for i in result["part_responses"]],
            ["hybrid-substrate", "board-track"],
        )


if __name__ == "__main__":
    unittest.main()
