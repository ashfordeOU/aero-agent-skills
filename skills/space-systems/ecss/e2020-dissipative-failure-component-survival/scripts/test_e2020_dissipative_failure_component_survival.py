"""Contract tests for the clause 5.2.14.1.1 dissipative-failure survival logic."""

import unittest

from e2020_dissipative_failure_component_survival_logic import (
    ABSOLUTE_ZERO_C,
    SURVIVAL_TOLERANCE_K,
    allowable_power_w,
    assess_dissipative_failure_survival,
    derated_limit_c,
    dissipated_power_w,
    part_outcome,
    part_temperature_c,
    validate_case,
)

# 28 V across the failed switch at a 2.0 A limit is 56 W held indefinitely.
# The board part rises 0.8 K/W to 84.8 C against a 105 C limit; the adjacent
# capacitor rises 0.5 K/W to 68 C against an 85 C limit.
SURVIVES = {
    "switch": "LCL-3 main switch",
    "voltage_drop_v": 28.0,
    "limited_current_a": 2.0,
    "reference_temp_c": 40.0,
    "parts": [
        {"name": "board-track", "coupling_k_per_w": 0.8, "rated_max_c": 125.0, "derating_margin_k": 20.0},
        {"name": "adjacent-capacitor", "coupling_k_per_w": 0.5, "rated_max_c": 105.0, "derating_margin_k": 20.0},
    ],
}

# The same switch beside a part coupled hard enough to be taken out.
EXCEEDED = {
    "switch": "LCL-4 main switch",
    "voltage_drop_v": 28.0,
    "limited_current_a": 2.0,
    "reference_temp_c": 40.0,
    "parts": [
        {"name": "board-track", "coupling_k_per_w": 0.8, "rated_max_c": 125.0, "derating_margin_k": 20.0},
        {"name": "hybrid-substrate", "coupling_k_per_w": 1.5, "rated_max_c": 125.0, "derating_margin_k": 25.0},
    ],
}

# Exactly on the bound: 56 W through 1.0 K/W from 40 C reaches 96 C, and the
# derated limit is 100 - 4 = 96 C.
ON_THE_LIMIT = {
    "switch": "LCL-5 main switch",
    "voltage_drop_v": 28.0,
    "limited_current_a": 2.0,
    "reference_temp_c": 40.0,
    "parts": [
        {"name": "shunt-resistor", "coupling_k_per_w": 1.0, "rated_max_c": 100.0, "derating_margin_k": 4.0},
    ],
}


def case_with(**overrides):
    spec = {
        "switch": SURVIVES["switch"],
        "voltage_drop_v": SURVIVES["voltage_drop_v"],
        "limited_current_a": SURVIVES["limited_current_a"],
        "reference_temp_c": SURVIVES["reference_temp_c"],
        "parts": [dict(part) for part in SURVIVES["parts"]],
    }
    spec.update(overrides)
    return spec


class ValidationTests(unittest.TestCase):
    def test_valid_case_returns_every_field(self):
        switch, drop, current, reference, parts, clearing = validate_case(SURVIVES)
        self.assertEqual(switch, "LCL-3 main switch")
        self.assertAlmostEqual(drop, 28.0, places=9)
        self.assertAlmostEqual(current, 2.0, places=9)
        self.assertAlmostEqual(reference, 40.0, places=9)
        self.assertEqual(len(parts), 2)
        self.assertIsNone(clearing)

    def test_derating_margin_defaults_to_zero(self):
        _, _, _, _, parts, _ = validate_case(
            case_with(parts=[{"name": "p", "coupling_k_per_w": 0.5, "rated_max_c": 125.0}])
        )
        self.assertAlmostEqual(parts[0]["derating_margin_k"], 0.0, places=9)
        self.assertAlmostEqual(parts[0]["derated_limit_c"], 125.0, places=9)

    def test_non_mapping_case_rejected(self):
        with self.assertRaises(ValueError):
            validate_case([28.0, 2.0])

    def test_missing_parts_key_rejected(self):
        with self.assertRaises(ValueError):
            validate_case(
                {
                    "switch": "S",
                    "voltage_drop_v": 28.0,
                    "limited_current_a": 2.0,
                    "reference_temp_c": 40.0,
                }
            )

    def test_zero_voltage_drop_rejected(self):
        with self.assertRaises(ValueError):
            validate_case(case_with(voltage_drop_v=0.0))

    def test_negative_current_rejected(self):
        with self.assertRaises(ValueError):
            validate_case(case_with(limited_current_a=-2.0))

    def test_boolean_current_rejected(self):
        with self.assertRaises(ValueError):
            validate_case(case_with(limited_current_a=True))

    def test_reference_below_absolute_zero_rejected(self):
        with self.assertRaises(ValueError):
            validate_case(case_with(reference_temp_c=ABSOLUTE_ZERO_C - 1.0))

    def test_empty_part_list_rejected(self):
        with self.assertRaises(ValueError):
            validate_case(case_with(parts=[]))

    def test_duplicate_part_name_rejected(self):
        with self.assertRaises(ValueError):
            validate_case(
                case_with(
                    parts=[
                        {"name": "p", "coupling_k_per_w": 0.5, "rated_max_c": 125.0},
                        {"name": "p", "coupling_k_per_w": 0.6, "rated_max_c": 125.0},
                    ]
                )
            )

    def test_zero_thermal_coupling_rejected(self):
        with self.assertRaises(ValueError):
            validate_case(
                case_with(parts=[{"name": "p", "coupling_k_per_w": 0.0, "rated_max_c": 125.0}])
            )

    def test_negative_derating_margin_rejected(self):
        with self.assertRaises(ValueError):
            validate_case(
                case_with(
                    parts=[
                        {
                            "name": "p",
                            "coupling_k_per_w": 0.5,
                            "rated_max_c": 125.0,
                            "derating_margin_k": -5.0,
                        }
                    ]
                )
            )

    def test_part_already_at_its_limit_before_the_failure_rejected(self):
        with self.assertRaises(ValueError):
            validate_case(
                case_with(
                    reference_temp_c=90.0,
                    parts=[
                        {
                            "name": "p",
                            "coupling_k_per_w": 0.5,
                            "rated_max_c": 100.0,
                            "derating_margin_k": 20.0,
                        }
                    ],
                )
            )

    def test_clearing_path_without_a_time_rejected(self):
        with self.assertRaises(ValueError):
            validate_case(case_with(external_clearing={"name": "fuse"}))

    def test_clearing_path_is_returned_when_declared(self):
        *_, clearing = validate_case(
            case_with(external_clearing={"name": "bus-fuse", "clears_after_s": 0.5})
        )
        self.assertEqual(clearing["name"], "bus-fuse")
        self.assertAlmostEqual(clearing["clears_after_s"], 0.5, places=9)


class ArithmeticTests(unittest.TestCase):
    def test_dissipation_is_the_drop_times_the_limited_current(self):
        self.assertAlmostEqual(dissipated_power_w(28.0, 2.0), 56.0, places=9)

    def test_dissipation_rejects_a_zero_current(self):
        with self.assertRaises(ValueError):
            dissipated_power_w(28.0, 0.0)

    def test_derated_limit_subtracts_the_withheld_margin(self):
        self.assertAlmostEqual(derated_limit_c(125.0, 20.0), 105.0, places=9)

    def test_part_temperature_rises_by_coupling_times_power(self):
        self.assertAlmostEqual(part_temperature_c(40.0, 56.0, 0.8), 84.8, places=9)

    def test_allowable_power_inverts_the_temperature_rise(self):
        part = {"name": "p", "coupling_k_per_w": 0.8, "derated_limit_c": 105.0}
        self.assertAlmostEqual(allowable_power_w(part, 40.0), 81.25, places=9)

    def test_a_part_landing_on_its_limit_survives(self):
        _, _, _, reference, parts, _ = validate_case(ON_THE_LIMIT)
        outcome = part_outcome(parts[0], reference, 56.0)
        self.assertAlmostEqual(outcome["temperature_c"], outcome["derated_limit_c"], places=9)
        self.assertTrue(outcome["survives"])

    def test_survival_tolerance_is_narrow_enough_to_catch_a_real_overshoot(self):
        self.assertLess(SURVIVAL_TOLERANCE_K, 1e-6)


class AssessmentTests(unittest.TestCase):
    def test_a_surviving_layout_is_compliant(self):
        result = assess_dissipative_failure_survival(SURVIVES)
        self.assertEqual(result["verdict"], "compliant")
        self.assertTrue(result["survives_uncleared_failure"])
        self.assertEqual(result["exceeded_parts"], [])
        self.assertEqual(result["findings"], [])

    def test_the_dissipation_and_the_worst_part_are_reported(self):
        result = assess_dissipative_failure_survival(SURVIVES)
        self.assertAlmostEqual(result["dissipated_power_w"], 56.0, places=9)
        self.assertEqual(result["worst_part"], "adjacent-capacitor")
        self.assertAlmostEqual(result["worst_margin_k"], 17.0, places=9)

    def test_an_exceeded_part_makes_the_case_non_compliant(self):
        result = assess_dissipative_failure_survival(EXCEEDED)
        self.assertEqual(result["verdict"], "non-compliant")
        self.assertEqual(result["exceeded_parts"], ["hybrid-substrate"])
        self.assertEqual(result["surviving_parts"], ["board-track"])

    def test_the_finding_names_the_part_and_the_overshoot(self):
        result = assess_dissipative_failure_survival(EXCEEDED)
        self.assertEqual(len(result["findings"]), 1)
        self.assertIn("hybrid-substrate", result["findings"][0])

    def test_the_limiting_allowable_power_is_the_smallest_of_the_parts(self):
        result = assess_dissipative_failure_survival(EXCEEDED)
        self.assertAlmostEqual(result["limiting_allowable_power_w"], 40.0, places=9)

    def test_headroom_ratio_is_below_one_when_a_part_is_exceeded(self):
        result = assess_dissipative_failure_survival(EXCEEDED)
        self.assertAlmostEqual(result["power_headroom_ratio"], 40.0 / 56.0, places=9)
        self.assertFalse(result["survives_uncleared_failure"])

    def test_headroom_ratio_is_one_on_the_bound(self):
        result = assess_dissipative_failure_survival(ON_THE_LIMIT)
        self.assertAlmostEqual(result["power_headroom_ratio"], 1.0, places=9)
        self.assertEqual(result["verdict"], "compliant")

    def test_a_declared_clearing_path_is_a_note_and_does_not_excuse_the_steady_state(self):
        spec = dict(EXCEEDED)
        spec["external_clearing"] = {"name": "bus-fuse", "clears_after_s": 0.25}
        result = assess_dissipative_failure_survival(spec)
        self.assertTrue(result["externally_cleared"])
        self.assertEqual(result["verdict"], "non-compliant")
        self.assertEqual(len(result["notes"]), 1)

    def test_no_clearing_path_leaves_the_note_list_empty(self):
        result = assess_dissipative_failure_survival(SURVIVES)
        self.assertFalse(result["externally_cleared"])
        self.assertEqual(result["notes"], [])

    def test_every_part_gets_its_own_outcome_row(self):
        result = assess_dissipative_failure_survival(SURVIVES)
        self.assertEqual([item["name"] for item in result["part_outcomes"]],
                         ["board-track", "adjacent-capacitor"])
        self.assertAlmostEqual(result["part_outcomes"][0]["temperature_c"], 84.8, places=9)

    def test_a_higher_reference_temperature_can_flip_a_surviving_layout(self):
        hot = dict(SURVIVES)
        hot["reference_temp_c"] = 70.0
        result = assess_dissipative_failure_survival(hot)
        self.assertEqual(result["verdict"], "non-compliant")
        self.assertIn("board-track", result["exceeded_parts"])


if __name__ == "__main__":
    unittest.main()
