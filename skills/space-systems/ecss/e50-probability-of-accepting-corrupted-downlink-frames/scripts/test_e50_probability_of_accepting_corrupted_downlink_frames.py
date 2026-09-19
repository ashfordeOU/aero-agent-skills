#!/usr/bin/env python3
"""Gate 3 contract test for e50-probability-of-accepting-corrupted-downlink-frames.

stdlib unittest, offline, deterministic. Run:
    python3 test_e50_probability_of_accepting_corrupted_downlink_frames.py
"""

import unittest

from e50_probability_of_accepting_corrupted_downlink_frames_logic import (
    BOUND_OBLIGATION,
    DERIVATION_OBLIGATION,
    MAX_CHECK_BITS,
    MET,
    MISSION_OBLIGATION,
    NOT_MET,
    OBLIGATIONS,
    REQUIRED_DECLARATIONS,
    assess_corrupted_downlink_frame_acceptance,
    escape_probability,
    mission_acceptance_probability,
    miscorrection_probability,
    per_frame_acceptance_probability,
    undeclared_inputs,
    validate_count,
    validate_probability,
    within_bound,
)

CODEWORD_SYMBOLS = 255
CORRECTABLE_SYMBOLS = 16
SYMBOL_BITS = 8
CHECK_BITS = 32
INTERLEAVE_DEPTH = 5
CODEWORD_FAILURE = 4.69e-11
MISSION_FRAMES = 100000000

DECLARED = {
    "assumed_ber": 1e-5,
    "codeword_symbols": CODEWORD_SYMBOLS,
    "correctable_symbols": CORRECTABLE_SYMBOLS,
    "symbol_bits": SYMBOL_BITS,
    "check_bits": CHECK_BITS,
}


def used(**overrides):
    values = dict(DECLARED)
    values.update(overrides)
    return values


class TestValidation(unittest.TestCase):
    def test_a_boolean_is_not_a_probability(self):
        with self.assertRaises(ValueError):
            validate_probability(True, "p")

    def test_a_fractional_symbol_count_is_refused(self):
        with self.assertRaises(ValueError):
            validate_count(255.5, "codeword_symbols")

    def test_a_check_field_of_zero_bits_is_refused(self):
        with self.assertRaises(ValueError):
            escape_probability(0)

    def test_an_absurd_check_field_length_is_refused(self):
        with self.assertRaises(ValueError):
            escape_probability(MAX_CHECK_BITS + 1)

    def test_a_code_that_cannot_hold_its_parity_is_refused(self):
        with self.assertRaises(ValueError):
            miscorrection_probability(20, 16, SYMBOL_BITS)

    def test_a_symbol_alphabet_beyond_sixty_four_bits_is_refused(self):
        with self.assertRaises(ValueError):
            miscorrection_probability(255, 16, 128)


class TestMiscorrection(unittest.TestCase):
    def test_a_strong_code_miscorrects_far_less_often_than_a_weak_one(self):
        strong = miscorrection_probability(255, 32, SYMBOL_BITS)
        weak = miscorrection_probability(255, 8, SYMBOL_BITS)
        self.assertLess(strong, weak / 1e20)

    def test_the_figure_is_a_probability(self):
        for t in (1, 4, 8, 16, 32):
            with self.subTest(t=t):
                value = miscorrection_probability(255, t, SYMBOL_BITS)
                self.assertGreaterEqual(value, 0.0)
                self.assertLessEqual(value, 1.0)

    def test_a_decoder_that_corrects_nothing_never_miscorrects_much(self):
        self.assertAlmostEqual(
            miscorrection_probability(255, 0, SYMBOL_BITS), 1.0, places=9
        )

    def test_the_figure_is_the_same_number_on_every_call(self):
        first = miscorrection_probability(255, 16, SYMBOL_BITS)
        second = miscorrection_probability(255, 16, SYMBOL_BITS)
        self.assertEqual(first, second)

    def test_a_wider_symbol_alphabet_lowers_the_miscorrection(self):
        self.assertLess(
            miscorrection_probability(63, 4, 16), miscorrection_probability(63, 4, 8)
        )


class TestEscape(unittest.TestCase):
    def test_a_thirty_two_bit_check_field_escapes_one_in_four_billion(self):
        self.assertAlmostEqual(escape_probability(32), 1.0 / 4294967296.0, places=18)

    def test_each_extra_check_bit_halves_the_escape(self):
        self.assertAlmostEqual(
            escape_probability(17) * 2.0, escape_probability(16), places=15
        )


class TestPerFrameFigure(unittest.TestCase):
    def test_both_gates_have_to_open_before_a_frame_is_accepted(self):
        miss = miscorrection_probability(
            CODEWORD_SYMBOLS, CORRECTABLE_SYMBOLS, SYMBOL_BITS
        )
        slip = escape_probability(CHECK_BITS)
        figure = per_frame_acceptance_probability(
            CODEWORD_FAILURE, miss, slip, INTERLEAVE_DEPTH
        )
        self.assertAlmostEqual(
            figure / (INTERLEAVE_DEPTH * CODEWORD_FAILURE * miss * slip),
            1.0,
            places=6,
        )

    def test_a_perfect_check_field_leaves_nothing_to_accept(self):
        self.assertAlmostEqual(
            per_frame_acceptance_probability(
                CODEWORD_FAILURE, 1.0, escape_probability(MAX_CHECK_BITS), 5
            ),
            0.0,
            places=18,
        )

    def test_a_codeword_that_never_fails_gives_a_figure_of_zero(self):
        self.assertEqual(
            per_frame_acceptance_probability(0.0, 1.0, escape_probability(16), 5), 0.0
        )

    def test_a_deeper_interleave_raises_the_frame_figure(self):
        shallow = per_frame_acceptance_probability(1e-9, 1e-6, 1e-9, 1)
        deep = per_frame_acceptance_probability(1e-9, 1e-6, 1e-9, 10)
        self.assertAlmostEqual(deep / shallow, 10.0, places=6)

    def test_the_mission_figure_exceeds_the_per_frame_figure(self):
        per_frame = 1e-15
        self.assertGreater(
            mission_acceptance_probability(per_frame, MISSION_FRAMES), per_frame
        )

    def test_a_mission_frame_count_of_zero_is_refused(self):
        with self.assertRaises(ValueError):
            mission_acceptance_probability(1e-15, 0)


class TestDeclaredDerivation(unittest.TestCase):
    def test_a_fully_declared_derivation_has_no_offender(self):
        self.assertEqual(undeclared_inputs(DECLARED, used()), ())

    def test_every_required_input_is_checked(self):
        self.assertEqual(
            set(undeclared_inputs({}, used())), set(REQUIRED_DECLARATIONS)
        )

    def test_an_input_used_at_a_different_value_is_named(self):
        self.assertEqual(
            undeclared_inputs(DECLARED, used(assumed_ber=1e-7)), ("assumed_ber",)
        )

    def test_an_input_declared_as_nothing_is_named(self):
        declaration = dict(DECLARED)
        declaration["check_bits"] = None
        self.assertEqual(undeclared_inputs(declaration, used()), ("check_bits",))

    def test_a_rate_written_two_ways_is_still_the_same_input(self):
        self.assertEqual(undeclared_inputs(DECLARED, used(assumed_ber=0.00001)), ())

    def test_a_non_mapping_declaration_is_refused(self):
        with self.assertRaises(ValueError):
            undeclared_inputs("assumed_ber=1e-5", used())


class TestThreeObligations(unittest.TestCase):
    def test_a_sound_case_meets_all_three(self):
        report = assess_corrupted_downlink_frame_acceptance(
            CODEWORD_FAILURE, CODEWORD_SYMBOLS, CORRECTABLE_SYMBOLS, CHECK_BITS,
            1e-20, 1e-12, DECLARED, used(), SYMBOL_BITS, INTERLEAVE_DEPTH,
            MISSION_FRAMES,
        )
        self.assertEqual(report["verdict"], MET)
        self.assertTrue(report["compliant"])
        self.assertEqual(report["failed_obligations"], ())

    def test_all_three_obligations_are_graded_separately(self):
        report = assess_corrupted_downlink_frame_acceptance(
            CODEWORD_FAILURE, CODEWORD_SYMBOLS, CORRECTABLE_SYMBOLS, CHECK_BITS,
            1e-20, 1e-12, DECLARED, used(), SYMBOL_BITS, INTERLEAVE_DEPTH,
            MISSION_FRAMES,
        )
        self.assertEqual(
            tuple(g["obligation"] for g in report["obligations"]), OBLIGATIONS
        )

    def test_an_undeclared_input_fails_only_the_derivation_obligation(self):
        report = assess_corrupted_downlink_frame_acceptance(
            CODEWORD_FAILURE, CODEWORD_SYMBOLS, CORRECTABLE_SYMBOLS, CHECK_BITS,
            1e-20, 1e-12, DECLARED, used(assumed_ber=1e-9), SYMBOL_BITS,
            INTERLEAVE_DEPTH, MISSION_FRAMES,
        )
        self.assertEqual(report["failed_obligations"], (DERIVATION_OBLIGATION,))
        self.assertFalse(report["compliant"])
        self.assertEqual(report["undeclared_inputs"], ("assumed_ber",))

    def test_a_per_frame_pass_can_still_fail_the_mission_obligation(self):
        report = assess_corrupted_downlink_frame_acceptance(
            1e-6, CODEWORD_SYMBOLS, 4, 16, 1e-6, 1e-9, used(
                correctable_symbols=4, check_bits=16
            ), used(correctable_symbols=4, check_bits=16), SYMBOL_BITS,
            INTERLEAVE_DEPTH, MISSION_FRAMES,
        )
        grades = {g["obligation"]: g["grade"] for g in report["obligations"]}
        self.assertEqual(grades[BOUND_OBLIGATION], MET)
        self.assertEqual(grades[MISSION_OBLIGATION], NOT_MET)

    def test_a_weak_check_field_fails_the_per_frame_obligation(self):
        report = assess_corrupted_downlink_frame_acceptance(
            1e-3, CODEWORD_SYMBOLS, 4, 8, 1e-20, 1.0, used(
                correctable_symbols=4, check_bits=8
            ), used(correctable_symbols=4, check_bits=8), SYMBOL_BITS,
            INTERLEAVE_DEPTH, MISSION_FRAMES,
        )
        grades = {g["obligation"]: g["grade"] for g in report["obligations"]}
        self.assertEqual(grades[BOUND_OBLIGATION], NOT_MET)
        self.assertIn(BOUND_OBLIGATION, report["finding"])

    def test_a_figure_landing_on_its_bound_meets_the_obligation(self):
        first = assess_corrupted_downlink_frame_acceptance(
            CODEWORD_FAILURE, CODEWORD_SYMBOLS, CORRECTABLE_SYMBOLS, CHECK_BITS,
            1e-20, 1e-12, DECLARED, used(), SYMBOL_BITS, INTERLEAVE_DEPTH,
            MISSION_FRAMES,
        )
        exact = assess_corrupted_downlink_frame_acceptance(
            CODEWORD_FAILURE, CODEWORD_SYMBOLS, CORRECTABLE_SYMBOLS, CHECK_BITS,
            first["per_frame_probability"], 1e-12, DECLARED, used(), SYMBOL_BITS,
            INTERLEAVE_DEPTH, MISSION_FRAMES,
        )
        grades = {g["obligation"]: g["grade"] for g in exact["obligations"]}
        self.assertEqual(grades[BOUND_OBLIGATION], MET)

    def test_the_report_keeps_both_escape_gates_visible(self):
        report = assess_corrupted_downlink_frame_acceptance(
            CODEWORD_FAILURE, CODEWORD_SYMBOLS, CORRECTABLE_SYMBOLS, CHECK_BITS,
            1e-20, 1e-12, DECLARED, used(), SYMBOL_BITS, INTERLEAVE_DEPTH,
            MISSION_FRAMES,
        )
        self.assertAlmostEqual(
            report["miscorrection_probability"],
            miscorrection_probability(
                CODEWORD_SYMBOLS, CORRECTABLE_SYMBOLS, SYMBOL_BITS
            ),
            places=18,
        )
        self.assertAlmostEqual(
            report["escape_probability"], escape_probability(CHECK_BITS), places=18
        )


class TestBoundComparison(unittest.TestCase):
    def test_a_figure_on_its_bound_is_within_it(self):
        self.assertTrue(within_bound(1e-12, 1e-12))

    def test_a_figure_clearly_over_its_bound_is_not(self):
        self.assertFalse(within_bound(1e-9, 1e-12))


if __name__ == "__main__":
    unittest.main()
