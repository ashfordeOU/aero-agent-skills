"""Contract tests for the ultracleaning process execution logic."""

import unittest

from q7054_cleaning_process_execution_logic import (
    PROCESS_CLOSES,
    PROCESS_OPEN,
    check_step_order,
    drying_adequate,
    execute_cleaning_process,
    require_carryover_fraction,
    residual_after_rinses,
    rinse_stages_required,
    validate_sequence,
)


def sound_steps():
    """Preclean, chemical clean, two rinses, dry, inspect, bag."""
    return [
        {"type": "gross-precleaning"},
        {"type": "chemical-cleaning"},
        {"type": "rinse"},
        {"type": "rinse"},
        {"type": "drying"},
        {"type": "inspection"},
        {"type": "packaging"},
    ]


def base_case(**overrides):
    """The sound sequence with a two-stage cascade that reaches its target."""
    case = {
        "steps": sound_steps(),
        "initial_carryover_mg_per_l": 500.0,
        "target_carryover_mg_per_l": 0.50,
        "carryover_fraction": 0.02,
        "geometry": "blind-hole",
        "volatility": "high",
        "drying_method": "hot-nitrogen-purge",
    }
    case.update(overrides)
    return case


class CarryoverValidationTests(unittest.TestCase):
    def test_a_fraction_inside_the_open_interval_is_accepted(self):
        self.assertAlmostEqual(require_carryover_fraction(0.02), 0.02, places=9)

    def test_a_fraction_of_one_is_rejected(self):
        with self.assertRaises(ValueError):
            require_carryover_fraction(1.0)

    def test_a_fraction_of_zero_is_rejected(self):
        with self.assertRaises(ValueError):
            require_carryover_fraction(0.0)

    def test_a_non_numeric_fraction_is_rejected(self):
        with self.assertRaises(ValueError):
            require_carryover_fraction("0.02")


class RinseCascadeTests(unittest.TestCase):
    def test_the_residual_falls_geometrically(self):
        self.assertAlmostEqual(residual_after_rinses(500.0, 0.02, 2), 0.20, places=9)

    def test_no_stages_leaves_the_initial_concentration(self):
        self.assertAlmostEqual(residual_after_rinses(500.0, 0.02, 0), 500.0, places=9)

    def test_a_cascade_landing_exactly_on_the_target_is_not_rounded_up(self):
        self.assertEqual(rinse_stages_required(100.0, 0.01, 0.1), 4)

    def test_the_exact_cascade_reaches_the_target_value(self):
        stages = rinse_stages_required(100.0, 0.01, 0.1)
        self.assertAlmostEqual(
            residual_after_rinses(100.0, 0.1, stages), 0.01, places=9
        )

    def test_a_partial_stage_rounds_up(self):
        self.assertEqual(rinse_stages_required(500.0, 0.50, 0.02), 2)

    def test_a_target_already_met_needs_no_stage(self):
        self.assertEqual(rinse_stages_required(0.10, 0.50, 0.02), 0)

    def test_a_worse_carryover_needs_more_stages(self):
        poor = rinse_stages_required(500.0, 0.50, 0.30)
        good = rinse_stages_required(500.0, 0.50, 0.02)
        self.assertGreater(poor, good)

    def test_negative_stages_rejected(self):
        with self.assertRaises(ValueError):
            residual_after_rinses(500.0, 0.02, -1)

    def test_fractional_stages_rejected(self):
        with self.assertRaises(ValueError):
            residual_after_rinses(500.0, 0.02, 1.5)

    def test_zero_target_rejected(self):
        with self.assertRaises(ValueError):
            rinse_stages_required(500.0, 0.0, 0.02)


class DryingTests(unittest.TestCase):
    def test_a_purge_reaches_a_blind_hole(self):
        self.assertTrue(drying_adequate("hot-nitrogen-purge", "blind-hole", "high")["adequate"])

    def test_ambient_evaporation_cannot_reach_a_blind_hole(self):
        result = drying_adequate("ambient-evaporation", "blind-hole", "high")
        self.assertFalse(result["adequate"])
        self.assertIn("does not reach", result["reason"])

    def test_a_purge_cannot_clear_a_low_volatility_fluid(self):
        result = drying_adequate("hot-nitrogen-purge", "open-surface", "low")
        self.assertFalse(result["adequate"])
        self.assertIn("volatility", result["reason"])

    def test_a_vacuum_bake_clears_the_hardest_case(self):
        self.assertTrue(
            drying_adequate("vacuum-bake", "internal-passage", "low")["adequate"]
        )

    def test_an_unknown_drying_method_rejected(self):
        with self.assertRaises(ValueError):
            drying_adequate("shake-dry", "open-surface", "high")

    def test_an_unknown_volatility_rejected(self):
        with self.assertRaises(ValueError):
            drying_adequate("vacuum-bake", "open-surface", "explosive")


class SequenceValidationTests(unittest.TestCase):
    def test_a_sound_sequence_validates_and_is_positioned(self):
        checked = validate_sequence(sound_steps())
        self.assertEqual(checked[0]["position"], 1)
        self.assertEqual(len(checked), 7)

    def test_an_unknown_step_type_rejected(self):
        with self.assertRaises(ValueError):
            validate_sequence([{"type": "polishing"}])

    def test_an_empty_sequence_rejected(self):
        with self.assertRaises(ValueError):
            validate_sequence([])

    def test_a_mapping_passed_as_a_sequence_rejected(self):
        with self.assertRaises(ValueError):
            validate_sequence({"type": "rinse"})

    def test_a_blank_step_name_rejected(self):
        with self.assertRaises(ValueError):
            validate_sequence([{"type": "rinse", "name": "  "}])


class StepOrderTests(unittest.TestCase):
    def test_a_sound_sequence_raises_no_ordering_finding(self):
        self.assertEqual(check_step_order(sound_steps()), [])

    def test_coarse_work_after_precision_work_is_a_finding(self):
        steps = sound_steps()
        steps.insert(4, {"type": "gross-precleaning"})
        self.assertTrue(
            any("follows precision work" in f for f in check_step_order(steps))
        )

    def test_a_chemical_step_with_no_rinse_behind_it_is_a_finding(self):
        steps = [
            {"type": "chemical-cleaning"},
            {"type": "drying"},
            {"type": "inspection"},
            {"type": "packaging"},
        ]
        self.assertTrue(
            any("is not followed by a rinse" in f for f in check_step_order(steps))
        )

    def test_inspecting_a_wet_part_is_a_finding(self):
        steps = [
            {"type": "chemical-cleaning"},
            {"type": "rinse"},
            {"type": "inspection"},
            {"type": "drying"},
            {"type": "packaging"},
        ]
        self.assertTrue(
            any("runs on a wet surface" in f for f in check_step_order(steps))
        )

    def test_bagging_a_wet_part_is_a_finding(self):
        steps = [
            {"type": "chemical-cleaning"},
            {"type": "rinse"},
            {"type": "packaging"},
        ]
        self.assertTrue(
            any("closes a bag over a wet surface" in f for f in check_step_order(steps))
        )

    def test_packaging_that_is_not_last_is_a_finding(self):
        steps = sound_steps()
        steps.append({"type": "inspection"})
        self.assertTrue(
            any("is not the last step" in f for f in check_step_order(steps))
        )

    def test_a_sequence_that_never_closes_is_a_finding(self):
        steps = sound_steps()[:-1]
        self.assertTrue(
            any("does not close with packaging" in f for f in check_step_order(steps))
        )

    def test_opening_with_a_rinse_is_a_finding(self):
        steps = [{"type": "rinse"}, {"type": "drying"}, {"type": "packaging"}]
        self.assertTrue(
            any("sequence opens with rinse" in f for f in check_step_order(steps))
        )

    def test_drying_with_nothing_wet_behind_it_is_a_finding(self):
        steps = [
            {"type": "gross-precleaning"},
            {"type": "drying"},
            {"type": "inspection"},
            {"type": "packaging"},
        ]
        self.assertTrue(
            any("no wet step behind it" in f for f in check_step_order(steps))
        )


class ExecutionTests(unittest.TestCase):
    def test_a_sound_process_closes(self):
        result = execute_cleaning_process(base_case())
        self.assertEqual(result["verdict"], PROCESS_CLOSES)
        self.assertEqual(result["findings"], [])

    def test_the_achieved_residual_is_reported(self):
        result = execute_cleaning_process(base_case())
        self.assertAlmostEqual(result["achieved_residual_mg_per_l"], 0.20, places=9)
        self.assertTrue(result["target_met"])

    def test_an_under_rinsed_cascade_opens_the_process(self):
        steps = sound_steps()
        steps.remove({"type": "rinse"})
        result = execute_cleaning_process(base_case(steps=steps))
        self.assertEqual(result["verdict"], PROCESS_OPEN)
        self.assertFalse(result["target_met"])
        self.assertTrue(any("rinse stage(s) against" in f for f in result["findings"]))

    def test_inadequate_drying_opens_the_process(self):
        result = execute_cleaning_process(
            base_case(drying_method="ambient-evaporation")
        )
        self.assertEqual(result["verdict"], PROCESS_OPEN)
        self.assertTrue(any("drying is inadequate" in f for f in result["findings"]))

    def test_the_required_and_provided_stage_counts_both_travel(self):
        result = execute_cleaning_process(base_case())
        self.assertEqual(result["required_rinse_stages"], 2)
        self.assertEqual(result["provided_rinse_stages"], 2)

    def test_a_missing_carryover_fraction_rejected(self):
        case = base_case()
        del case["carryover_fraction"]
        with self.assertRaises(ValueError):
            execute_cleaning_process(case)

    def test_a_non_mapping_case_rejected(self):
        with self.assertRaises(ValueError):
            execute_cleaning_process(sound_steps())


if __name__ == "__main__":
    unittest.main()
