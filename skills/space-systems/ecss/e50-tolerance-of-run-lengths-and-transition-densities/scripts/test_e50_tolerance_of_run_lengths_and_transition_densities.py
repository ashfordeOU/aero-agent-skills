"""Contract tests for the clause 5.6.11.3 run length and transition logic."""

import unittest

from e50_tolerance_of_run_lengths_and_transition_densities_logic import (
    COMPLIANT,
    DENSITY_TOO_LOW,
    RUN_TOO_LONG,
    assess_bit_stream,
    longest_run,
    randomisation_needed,
    run_lengths,
    runs_over_limit,
    transition_count,
    transition_density,
    transition_shortfall,
    transitions_needed,
    validate_density,
    validate_positive_int,
    validate_stream,
    worst_window,
)

# Hand-counted streams. ALTERNATING has a transition at every one of its nine
# opportunities; MIXED has four runs of three and three transitions in eleven
# opportunities; STARVED opens with eight identical symbols and transitions
# once in nine.
ALTERNATING = "0101010101"
MIXED = "000111000111"
STARVED = "0000000011"


class ValidationTests(unittest.TestCase):
    def test_binary_text_accepted(self):
        self.assertEqual(validate_stream("0110"), (0, 1, 1, 0))

    def test_integer_sequence_accepted(self):
        self.assertEqual(validate_stream([0, 1, 1, 0]), (0, 1, 1, 0))

    def test_non_binary_character_rejected(self):
        with self.assertRaises(ValueError):
            validate_stream("01x0")

    def test_out_of_range_integer_rejected(self):
        with self.assertRaises(ValueError):
            validate_stream([0, 2, 1])

    def test_boolean_symbol_rejected(self):
        with self.assertRaises(ValueError):
            validate_stream([0, True, 1])

    def test_empty_stream_rejected(self):
        with self.assertRaises(ValueError):
            validate_stream("")

    def test_non_sequence_stream_rejected(self):
        with self.assertRaises(ValueError):
            validate_stream(1010)

    def test_zero_limit_rejected(self):
        with self.assertRaises(ValueError):
            validate_positive_int(0)

    def test_fractional_limit_rejected(self):
        with self.assertRaises(ValueError):
            validate_positive_int(3.5)

    def test_density_above_one_rejected(self):
        with self.assertRaises(ValueError):
            validate_density(1.5)

    def test_negative_density_rejected(self):
        with self.assertRaises(ValueError):
            validate_density(-0.1)

    def test_density_of_one_accepted(self):
        self.assertAlmostEqual(validate_density(1), 1.0, places=9)


class RunTests(unittest.TestCase):
    def test_runs_are_grouped_by_symbol(self):
        self.assertEqual(len(run_lengths(MIXED)), 4)

    def test_alternating_stream_is_all_single_symbol_runs(self):
        self.assertEqual(len(run_lengths(ALTERNATING)), 10)

    def test_longest_run_of_a_mixed_stream(self):
        self.assertEqual(longest_run(MIXED)["length"], 3)

    def test_longest_run_reports_where_it_starts(self):
        self.assertEqual(longest_run(STARVED)["start"], 0)

    def test_longest_run_reports_the_symbol(self):
        self.assertEqual(longest_run(STARVED)["symbol"], 0)

    def test_a_tie_reports_the_earliest_run(self):
        self.assertEqual(longest_run("001100")["start"], 0)

    def test_runs_over_limit_are_listed(self):
        self.assertEqual(len(runs_over_limit(STARVED, 4)), 1)

    def test_no_run_exceeds_a_generous_limit(self):
        self.assertEqual(runs_over_limit(MIXED, 3), [])

    def test_a_single_symbol_stream_is_one_run(self):
        self.assertEqual(longest_run("1")["length"], 1)


class DensityTests(unittest.TestCase):
    def test_alternating_stream_transitions_everywhere(self):
        self.assertEqual(transition_count(ALTERNATING), 9)

    def test_alternating_density_is_one(self):
        self.assertAlmostEqual(transition_density(ALTERNATING), 1.0, places=9)

    def test_mixed_stream_transitions_three_times(self):
        self.assertEqual(transition_count(MIXED), 3)

    def test_mixed_density_is_three_in_eleven(self):
        self.assertAlmostEqual(transition_density(MIXED), 3.0 / 11.0, places=9)

    def test_starved_density_is_one_in_nine(self):
        self.assertAlmostEqual(transition_density(STARVED), 1.0 / 9.0, places=9)

    def test_a_single_symbol_stream_has_no_density(self):
        self.assertIsNone(transition_density("1"))

    def test_a_constant_stream_has_no_transitions(self):
        self.assertEqual(transition_count("00000"), 0)


class WindowTests(unittest.TestCase):
    def test_alternating_worst_window_is_still_full(self):
        self.assertAlmostEqual(worst_window(ALTERNATING, 4)["density"], 1.0, places=9)

    def test_mixed_worst_window_is_one_in_three(self):
        self.assertAlmostEqual(worst_window(MIXED, 4)["density"], 1.0 / 3.0, places=9)

    def test_starved_worst_window_is_empty(self):
        lean = worst_window(STARVED, 4)
        self.assertAlmostEqual(lean["density"], 0.0, places=9)
        self.assertEqual(lean["start"], 0)

    def test_a_window_of_one_symbol_is_rejected(self):
        with self.assertRaises(ValueError):
            worst_window(MIXED, 1)

    def test_a_window_longer_than_the_stream_is_rejected(self):
        with self.assertRaises(ValueError):
            worst_window(MIXED, 20)

    def test_transitions_needed_rounds_up_to_a_whole_edge(self):
        self.assertEqual(transitions_needed(4, 0.5), 2)

    def test_transitions_needed_at_an_exact_boundary_does_not_round_up(self):
        self.assertEqual(transitions_needed(4, 1.0 / 3.0), 1)

    def test_no_density_asked_needs_no_transition(self):
        self.assertEqual(transitions_needed(4, 0.0), 0)

    def test_shortfall_counts_the_missing_edges(self):
        self.assertEqual(transition_shortfall(STARVED, 4, 0.5), 2)

    def test_a_satisfied_window_is_short_by_nothing(self):
        self.assertEqual(transition_shortfall(ALTERNATING, 4, 0.5), 0)


class ConditioningTests(unittest.TestCase):
    def test_a_clean_stream_needs_no_conditioning(self):
        self.assertFalse(randomisation_needed(ALTERNATING, 4, 0.5, 4))

    def test_a_long_run_forces_conditioning(self):
        self.assertTrue(randomisation_needed(STARVED, 4, 0.0, 4))

    def test_a_lean_window_forces_conditioning(self):
        self.assertTrue(randomisation_needed(MIXED, 8, 0.5, 4))


class AssessTests(unittest.TestCase):
    def test_a_compliant_stream_passes(self):
        result = assess_bit_stream(ALTERNATING, 4, 0.5, 4)
        self.assertEqual(result["verdict"], COMPLIANT)
        self.assertTrue(result["run_ok"])
        self.assertTrue(result["density_ok"])

    def test_a_long_run_is_the_binding_failure(self):
        result = assess_bit_stream(STARVED, 4, 0.0, 4)
        self.assertEqual(result["verdict"], RUN_TOO_LONG)
        self.assertFalse(result["run_ok"])

    def test_a_lean_window_fails_on_density(self):
        result = assess_bit_stream(MIXED, 8, 0.5, 4)
        self.assertEqual(result["verdict"], DENSITY_TOO_LOW)
        self.assertFalse(result["density_ok"])

    def test_a_run_exactly_on_the_limit_is_tolerated(self):
        result = assess_bit_stream(MIXED, 3, 0.0, 4)
        self.assertEqual(result["longest_run"], result["max_run"])
        self.assertTrue(result["run_ok"])

    def test_a_density_exactly_on_the_limit_is_tolerated(self):
        result = assess_bit_stream(ALTERNATING, 4, 1.0, 4)
        self.assertAlmostEqual(result["transition_density"], result["min_density"], places=9)
        self.assertAlmostEqual(result["worst_window_density"], result["min_density"], places=9)
        self.assertTrue(result["density_ok"])

    def test_a_window_exactly_on_the_limit_passes_the_window_test(self):
        result = assess_bit_stream(MIXED, 3, 1.0 / 3.0, 4)
        self.assertAlmostEqual(result["worst_window_density"], 1.0 / 3.0, places=9)
        self.assertTrue(result["window_density_ok"])

    def test_a_lean_average_fails_even_when_every_window_passes(self):
        result = assess_bit_stream(MIXED, 3, 1.0 / 3.0, 4)
        self.assertFalse(result["overall_density_ok"])
        self.assertEqual(result["verdict"], DENSITY_TOO_LOW)
        self.assertTrue(any("overall transition density" in f for f in result["findings"]))

    def test_the_run_finding_names_the_position(self):
        result = assess_bit_stream(STARVED, 4, 0.0, 4)
        self.assertTrue(any("starts at position 0" in f for f in result["findings"]))

    def test_the_run_finding_recommends_conditioning(self):
        result = assess_bit_stream(STARVED, 4, 0.0, 4)
        self.assertTrue(any("transition-rich line code" in f for f in result["findings"]))

    def test_the_density_finding_names_the_window(self):
        result = assess_bit_stream(MIXED, 8, 0.5, 4)
        self.assertTrue(any("leanest 4 symbol window" in f for f in result["findings"]))

    def test_the_density_finding_counts_the_missing_edges(self):
        result = assess_bit_stream(MIXED, 8, 0.5, 4)
        self.assertEqual(result["window_transition_shortfall"], 1)

    def test_a_compliant_stream_reports_no_findings(self):
        self.assertEqual(assess_bit_stream(ALTERNATING, 4, 0.5, 4)["findings"], [])

    def test_a_good_average_can_still_hide_a_lean_window(self):
        stream = "0101010101" + "00000000"
        result = assess_bit_stream(stream, 12, 0.4, 6)
        self.assertGreater(result["transition_density"], result["worst_window_density"])
        self.assertFalse(result["density_ok"])

    def test_the_result_carries_the_conditioning_decision(self):
        self.assertTrue(assess_bit_stream(STARVED, 4, 0.0, 4)["randomisation_needed"])

    def test_the_result_carries_the_stream_length_and_run_count(self):
        result = assess_bit_stream(MIXED, 3, 0.0, 4)
        self.assertEqual(result["length"], 12)
        self.assertEqual(result["runs"], 4)

    def test_a_window_longer_than_the_stream_rejected_by_the_assessment(self):
        with self.assertRaises(ValueError):
            assess_bit_stream(MIXED, 3, 0.5, 40)

    def test_a_zero_run_limit_rejected_by_the_assessment(self):
        with self.assertRaises(ValueError):
            assess_bit_stream(MIXED, 0, 0.5, 4)

    def test_an_out_of_range_density_rejected_by_the_assessment(self):
        with self.assertRaises(ValueError):
            assess_bit_stream(MIXED, 3, 2.0, 4)


if __name__ == "__main__":
    unittest.main()
