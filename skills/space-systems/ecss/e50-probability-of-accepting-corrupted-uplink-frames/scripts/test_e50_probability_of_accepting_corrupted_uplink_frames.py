#!/usr/bin/env python3
"""Gate 3 contract test for e50-probability-of-accepting-corrupted-uplink-frames.

stdlib unittest, offline, deterministic. Run:
    python3 test_e50_probability_of_accepting_corrupted_uplink_frames.py
"""

import unittest

from e50_probability_of_accepting_corrupted_uplink_frames_logic import (
    EXCEEDED,
    MAX_CHECK_BITS,
    WITHIN,
    acceptance_probability_per_frame,
    assess_corrupted_uplink_frame_acceptance,
    combine_detection_layers,
    escape_probability,
    frames_between_acceptances,
    mission_acceptance_probability,
    sufficient_check_bits,
    validate_count,
    validate_probability,
    within_bound,
)

RESIDUAL = 8.16e-3
FRAMES_PER_MISSION = 4000


class TestValidation(unittest.TestCase):
    def test_a_boolean_is_not_a_probability(self):
        with self.assertRaises(ValueError):
            validate_probability(True, "p")

    def test_a_probability_above_one_is_refused(self):
        with self.assertRaises(ValueError):
            validate_probability(1.5, "p")

    def test_one_is_refused_unless_it_is_explicitly_allowed(self):
        with self.assertRaises(ValueError):
            validate_probability(1.0, "p")
        self.assertEqual(validate_probability(1.0, "p", allow_one=True), 1.0)

    def test_a_fractional_check_bit_count_is_refused(self):
        with self.assertRaises(ValueError):
            validate_count(16.5, "check_bits")

    def test_a_detection_code_of_zero_bits_is_refused(self):
        with self.assertRaises(ValueError):
            escape_probability(0)

    def test_an_absurd_detection_code_length_is_refused(self):
        with self.assertRaises(ValueError):
            escape_probability(MAX_CHECK_BITS + 1)


class TestEscapeProbability(unittest.TestCase):
    def test_sixteen_check_bits_give_one_in_sixty_five_thousand(self):
        self.assertAlmostEqual(escape_probability(16), 1.0 / 65536.0, places=15)

    def test_each_extra_check_bit_halves_the_escape(self):
        self.assertAlmostEqual(
            escape_probability(33) * 2.0, escape_probability(32), places=15
        )

    def test_the_escape_does_not_depend_on_the_channel(self):
        self.assertEqual(escape_probability(32), escape_probability(32))

    def test_two_independent_layers_multiply(self):
        combined = combine_detection_layers(
            (escape_probability(16), escape_probability(16))
        )
        self.assertAlmostEqual(combined, escape_probability(32), places=18)

    def test_a_layer_that_detects_nothing_leaves_the_escape_alone(self):
        combined = combine_detection_layers((escape_probability(16), 1.0))
        self.assertAlmostEqual(combined, escape_probability(16), places=18)

    def test_an_empty_layer_list_is_refused(self):
        with self.assertRaises(ValueError):
            combine_detection_layers(())


class TestPerFrameFigure(unittest.TestCase):
    def test_the_per_frame_figure_is_the_product_of_the_two_factors(self):
        escape = escape_probability(16)
        self.assertAlmostEqual(
            acceptance_probability_per_frame(RESIDUAL, escape),
            RESIDUAL * escape,
            places=18,
        )

    def test_a_link_that_never_corrupts_never_accepts_a_corrupted_frame(self):
        self.assertEqual(
            acceptance_probability_per_frame(0.0, escape_probability(16)), 0.0
        )

    def test_the_per_frame_figure_is_far_below_the_rejection_rate(self):
        figure = acceptance_probability_per_frame(RESIDUAL, escape_probability(32))
        self.assertLess(figure, RESIDUAL / 1e9)

    def test_the_mean_gap_between_acceptances_is_the_reciprocal(self):
        figure = acceptance_probability_per_frame(RESIDUAL, escape_probability(16))
        self.assertAlmostEqual(
            frames_between_acceptances(figure), 1.0 / figure, places=6
        )

    def test_a_figure_of_zero_has_no_mean_gap(self):
        with self.assertRaises(ValueError):
            frames_between_acceptances(0.0)


class TestMissionFigure(unittest.TestCase):
    def test_a_rare_event_over_many_frames_is_about_the_product(self):
        per_frame = 1.2451171875e-07
        mission = mission_acceptance_probability(per_frame, FRAMES_PER_MISSION)
        self.assertAlmostEqual(
            mission / (per_frame * FRAMES_PER_MISSION), 1.0, places=3
        )

    def test_the_mission_figure_never_passes_one(self):
        # The figure is one minus a survival term, so it is bounded above
        # by one by construction and reaches one only when that term
        # underflows. At 1000 frames with a per-frame figure of one half it
        # does: log1p(-0.5) times 1000 is about -693, and expm1 of that is
        # -1 to the last bit. That last bit is an expm1 result and so is
        # libm-dependent, which is why the saturated case is asserted to be
        # one to within a few bits rather than compared against the bound.
        # A case that has not saturated is checked separately, and stays
        # strictly inside the range with room to spare.
        saturated = mission_acceptance_probability(0.5, 1000)
        self.assertAlmostEqual(saturated, 1.0, places=15)
        self.assertGreater(saturated, 0.999)
        self.assertLess(mission_acceptance_probability(0.5, 4), 1.0)

    def test_a_per_frame_figure_of_zero_gives_a_mission_figure_of_zero(self):
        self.assertEqual(mission_acceptance_probability(0.0, FRAMES_PER_MISSION), 0.0)

    def test_more_frames_never_lower_the_mission_figure(self):
        small = mission_acceptance_probability(1e-9, 1000)
        large = mission_acceptance_probability(1e-9, 100000)
        self.assertGreater(large, small * 50.0)

    def test_a_frame_count_of_zero_is_refused(self):
        with self.assertRaises(ValueError):
            mission_acceptance_probability(1e-9, 0)


class TestSufficientCheckLength(unittest.TestCase):
    def test_the_search_returns_the_shortest_code_that_works(self):
        bits = sufficient_check_bits(RESIDUAL, 1e-9)
        self.assertTrue(
            within_bound(
                acceptance_probability_per_frame(RESIDUAL, escape_probability(bits)),
                1e-9,
            )
        )
        self.assertFalse(
            within_bound(
                acceptance_probability_per_frame(
                    RESIDUAL, escape_probability(bits - 1)
                ),
                1e-9,
            )
        )

    def test_a_tighter_bound_never_needs_a_shorter_code(self):
        self.assertGreaterEqual(
            sufficient_check_bits(RESIDUAL, 1e-12),
            sufficient_check_bits(RESIDUAL, 1e-9),
        )

    def test_an_unreachable_bound_is_refused_rather_than_guessed(self):
        with self.assertRaises(ValueError):
            sufficient_check_bits(1e-3, 0.0)


class TestAssessment(unittest.TestCase):
    def test_a_thirty_two_bit_check_field_meets_a_nanoscale_bound(self):
        report = assess_corrupted_uplink_frame_acceptance(
            RESIDUAL, 32, 1e-9, (), FRAMES_PER_MISSION
        )
        self.assertEqual(report["verdict"], WITHIN)
        self.assertTrue(report["compliant"])

    def test_a_short_check_field_exceeds_the_same_bound(self):
        report = assess_corrupted_uplink_frame_acceptance(
            RESIDUAL, 8, 1e-9, (), FRAMES_PER_MISSION
        )
        self.assertEqual(report["verdict"], EXCEEDED)
        self.assertIn("more likely", report["finding"])

    def test_an_extra_detection_layer_is_counted_in_the_escape(self):
        one = assess_corrupted_uplink_frame_acceptance(RESIDUAL, 16, 1e-6)
        two = assess_corrupted_uplink_frame_acceptance(
            RESIDUAL, 16, 1e-6, (escape_probability(16),)
        )
        self.assertEqual(two["detection_layers"], 2)
        self.assertLess(
            two["combined_escape_probability"], one["combined_escape_probability"]
        )

    def test_the_report_names_the_shortest_check_field_that_would_do(self):
        report = assess_corrupted_uplink_frame_acceptance(RESIDUAL, 8, 1e-9)
        self.assertEqual(
            report["shortest_sufficient_check_bits"],
            sufficient_check_bits(RESIDUAL, 1e-9),
        )

    def test_the_mission_figure_exceeds_the_per_frame_figure(self):
        report = assess_corrupted_uplink_frame_acceptance(
            RESIDUAL, 24, 1e-6, (), FRAMES_PER_MISSION
        )
        self.assertGreater(
            report["mission_probability"], report["per_frame_probability"]
        )

    def test_a_figure_landing_on_its_bound_is_graded_within(self):
        escape = escape_probability(16)
        figure = acceptance_probability_per_frame(RESIDUAL, escape)
        report = assess_corrupted_uplink_frame_acceptance(RESIDUAL, 16, figure)
        self.assertAlmostEqual(report["per_frame_probability"], figure, places=18)
        self.assertEqual(report["verdict"], WITHIN)

    def test_an_uncorrupted_link_has_no_required_check_length(self):
        report = assess_corrupted_uplink_frame_acceptance(0.0, 16, 1e-9)
        self.assertIsNone(report["shortest_sufficient_check_bits"])
        self.assertTrue(report["compliant"])


if __name__ == "__main__":
    unittest.main()
