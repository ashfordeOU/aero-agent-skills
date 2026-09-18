"""Contract tests for the clause 5.4.7 blind-commanding logic."""

import unittest

from e50_commanding_in_the_blind_logic import (
    FIT_TOLERANCE_S,
    MAX_REPETITIONS,
    assess_blind_commanding,
    categorize_blind_suitability,
    command_duration_s,
    categorize_blind_suitability as _grouping_alias,
    required_repetitions,
    residual_failure_probability,
    sequence_duration_s,
    validate_window,
)

SEQUENCE = [
    {"name": "TC_TX_ON", "bits": 512.0, "idempotent": True, "state_dependent": False},
    {"name": "TC_SAFE_EXIT", "bits": 512.0, "idempotent": True, "state_dependent": False},
]


def base_spec(**overrides):
    spec = {
        "commands": SEQUENCE,
        "window_s": 600.0,
        "guard_time_s": 60.0,
        "uplink_rate_bps": 2000.0,
        "loss_probability": 0.1,
        "target_confidence": 0.999,
        "inter_command_gap_s": 1.0,
    }
    spec.update(overrides)
    return spec


class WindowTests(unittest.TestCase):
    def test_guard_time_is_held_back(self):
        self.assertAlmostEqual(validate_window(600.0, 60.0), 540.0)

    def test_zero_guard_time_leaves_the_whole_window(self):
        self.assertAlmostEqual(validate_window(600.0, 0.0), 600.0)

    def test_guard_time_equal_to_the_window_rejected(self):
        with self.assertRaises(ValueError):
            validate_window(600.0, 600.0)

    def test_negative_window_rejected(self):
        with self.assertRaises(ValueError):
            validate_window(-600.0, 10.0)

    def test_non_numeric_guard_time_rejected(self):
        with self.assertRaises(ValueError):
            validate_window(600.0, "60")


class DurationTests(unittest.TestCase):
    def test_command_duration_is_bits_over_rate(self):
        self.assertAlmostEqual(command_duration_s(2000.0, 1000.0), 2.0)

    def test_zero_uplink_rate_rejected(self):
        with self.assertRaises(ValueError):
            command_duration_s(2000.0, 0.0)

    def test_sequence_duration_counts_every_slot_gap(self):
        # two commands, three repetitions, 6000 bits total at 1000 bps, five gaps
        value = sequence_duration_s([1000.0, 1000.0], 3, 1000.0, 2.0)
        self.assertAlmostEqual(value, 6.0 + 10.0)

    def test_sequence_duration_without_gaps_is_pure_on_air_time(self):
        self.assertAlmostEqual(sequence_duration_s([1000.0], 4, 1000.0), 4.0)

    def test_empty_sequence_rejected(self):
        with self.assertRaises(ValueError):
            sequence_duration_s([], 3, 1000.0)

    def test_zero_repetitions_rejected(self):
        with self.assertRaises(ValueError):
            sequence_duration_s([1000.0], 0, 1000.0)

    def test_boolean_repetitions_rejected(self):
        with self.assertRaises(ValueError):
            sequence_duration_s([1000.0], True, 1000.0)


class RepetitionTests(unittest.TestCase):
    def test_residual_is_the_product_of_the_losses(self):
        self.assertAlmostEqual(residual_failure_probability(0.5, 3), 0.125, places=12)

    def test_certain_loss_never_decays(self):
        self.assertAlmostEqual(residual_failure_probability(1.0, 9), 1.0, places=12)

    def test_three_tenths_loss_needs_three_copies_for_three_nines(self):
        self.assertEqual(required_repetitions(0.1, 0.999), 3)

    def test_exact_boundary_is_not_pushed_to_an_extra_copy(self):
        residual = residual_failure_probability(0.1, 3)
        self.assertAlmostEqual(residual, 1.0 - 0.999, places=12)
        self.assertEqual(required_repetitions(0.1, 0.999), 3)

    def test_a_worse_link_needs_more_copies(self):
        self.assertGreater(required_repetitions(0.5, 0.999), required_repetitions(0.1, 0.999))

    def test_a_tighter_confidence_needs_more_copies(self):
        self.assertGreater(
            required_repetitions(0.1, 0.9999999), required_repetitions(0.1, 0.99)
        )

    def test_loss_probability_of_one_cannot_be_planned_against(self):
        with self.assertRaises(ValueError):
            required_repetitions(1.0, 0.999)

    def test_zero_loss_probability_rejected(self):
        with self.assertRaises(ValueError):
            required_repetitions(0.0, 0.999)

    def test_confidence_of_one_rejected(self):
        with self.assertRaises(ValueError):
            required_repetitions(0.1, 1.0)

    def test_repetition_ceiling_is_finite(self):
        self.assertGreater(MAX_REPETITIONS, 0)


class SuitabilityTests(unittest.TestCase):
    def test_idempotent_stateless_commands_are_repeatable(self):
        grouping = categorize_blind_suitability(SEQUENCE)
        self.assertEqual(len(grouping["repeatable"]), 2)
        self.assertEqual(grouping["unsafe"], [])

    def test_non_idempotent_command_is_unsafe(self):
        grouping = categorize_blind_suitability(
            [{"name": "TC_STEP", "bits": 256.0, "idempotent": False, "state_dependent": False}]
        )
        self.assertEqual(grouping["unsafe"], ["TC_STEP"])

    def test_state_dependent_command_is_unsafe_even_when_idempotent(self):
        grouping = categorize_blind_suitability(
            [{"name": "TC_IF_MODE", "bits": 256.0, "idempotent": True, "state_dependent": True}]
        )
        self.assertEqual(grouping["unsafe"], ["TC_IF_MODE"])

    def test_duplicate_command_name_rejected(self):
        with self.assertRaises(ValueError):
            categorize_blind_suitability(SEQUENCE + [SEQUENCE[0]])

    def test_non_boolean_flag_rejected(self):
        with self.assertRaises(ValueError):
            categorize_blind_suitability(
                [{"name": "TC_X", "bits": 256.0, "idempotent": 1, "state_dependent": False}]
            )

    def test_missing_flag_rejected(self):
        with self.assertRaises(ValueError):
            categorize_blind_suitability([{"name": "TC_X", "bits": 256.0, "idempotent": True}])

    def test_grouping_alias_is_the_same_callable(self):
        self.assertIs(_grouping_alias, categorize_blind_suitability)


class AssessmentTests(unittest.TestCase):
    def test_workable_session_is_compliant(self):
        result = assess_blind_commanding(base_spec())
        self.assertTrue(result["compliant"])
        self.assertEqual(result["findings"], [])

    def test_repetition_count_is_carried_out(self):
        self.assertEqual(assess_blind_commanding(base_spec())["repetitions"], 3)

    def test_unsafe_command_blocks_the_session(self):
        commands = list(SEQUENCE) + [
            {"name": "TC_NUDGE", "bits": 256.0, "idempotent": False, "state_dependent": False}
        ]
        result = assess_blind_commanding(base_spec(commands=commands))
        self.assertFalse(result["compliant"])
        self.assertEqual(result["unsafe"], ["TC_NUDGE"])

    def test_short_window_is_flagged(self):
        result = assess_blind_commanding(base_spec(window_s=62.0, guard_time_s=60.0))
        self.assertFalse(result["fits_window"])
        self.assertTrue(any("usable after the guard" in f for f in result["findings"]))

    def test_sequence_ending_exactly_on_the_window_edge_fits(self):
        spec = base_spec(inter_command_gap_s=0.0, guard_time_s=0.0)
        duration = sequence_duration_s(
            [record["bits"] for record in SEQUENCE], 3, spec["uplink_rate_bps"], 0.0
        )
        spec["window_s"] = duration
        result = assess_blind_commanding(spec)
        self.assertTrue(result["fits_window"])
        self.assertLessEqual(
            abs(result["sequence_duration_s"] - result["usable_window_s"]), FIT_TOLERANCE_S
        )

    def test_residual_probability_is_reported(self):
        result = assess_blind_commanding(base_spec())
        self.assertAlmostEqual(result["residual_failure_probability"], 0.001, places=12)

    def test_missing_spec_key_rejected(self):
        spec = base_spec()
        del spec["uplink_rate_bps"]
        with self.assertRaises(ValueError):
            assess_blind_commanding(spec)

    def test_non_mapping_spec_rejected(self):
        with self.assertRaises(ValueError):
            assess_blind_commanding("window")


if __name__ == "__main__":
    unittest.main()
