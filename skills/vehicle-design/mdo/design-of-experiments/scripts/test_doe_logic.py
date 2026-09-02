#!/usr/bin/env python3
"""Contract test for the DOE leaf logic (design-of-experiments).

Offline, deterministic, stdlib unittest only. Covers: full and
fractional factorial construction with the principal-fraction
identity, latin hypercube stratification and uniqueness at fixed
seed, central composite run count and axial layout, exact
worked-example main effects and interaction effects, dispatch
through build_design_matrix, and ValueError rejection of invalid
levels, factor counts, sample counts, and mismatched responses.

Run: python3 scripts/test_doe_logic.py
"""

import itertools
import math
import unittest

from doe_logic import (
    analyze_interactions,
    analyze_main_effects,
    build_design_matrix,
    central_composite,
    check_principal_fraction,
    factor_label,
    fractional_factorial_2k,
    full_factorial,
    latin_hypercube,
)


def linear_response_k2(row):
    """y = 2*A + 1.5*B + A*B on the coded levels of a two-factor run."""
    a, b = row
    return 2.0 * a + 1.5 * b + a * b


class TestFullFactorial(unittest.TestCase):
    def test_two_level_two_factor_four_runs(self):
        design = full_factorial([2, 2])
        self.assertEqual(len(design), 4)
        self.assertEqual(
            set(design), {(-1, -1), (-1, 1), (1, -1), (1, 1)}
        )
        for row in design:
            self.assertTrue(all(v in (-1, 1) for v in row))

    def test_two_level_three_factor_eight_runs(self):
        design = full_factorial([2, 2, 2])
        self.assertEqual(len(design), 8)
        self.assertEqual(len(set(design)), 8)
        self.assertEqual(design[0], (-1, -1, -1))
        self.assertEqual(design[-1], (1, 1, 1))

    def test_two_level_seven_factor_cap_one_twenty_eight_runs(self):
        self.assertEqual(len(full_factorial([2] * 7)), 128)

    def test_mixed_and_multi_level_coding(self):
        mixed = full_factorial([2, 3, 2])
        self.assertEqual(len(mixed), 12)
        self.assertEqual({row[0] for row in mixed}, {-1, 1})
        self.assertEqual({row[1] for row in mixed}, {0, 1, 2})
        self.assertEqual({row[2] for row in mixed}, {-1, 1})
        self.assertEqual(full_factorial([3]), [(0,), (1,), (2,)])

    def test_invalid_level_counts_raise(self):
        for bad in ([], [1, 2], [2, 0], [2, -1], [2.5, 2], ["2", 2]):
            with self.assertRaises(ValueError):
                full_factorial(bad)


class TestFractionalFactorial(unittest.TestCase):
    def test_full_fraction_matches_full_factorial(self):
        for k in (2, 3, 5):
            self.assertEqual(
                fractional_factorial_2k(k, fraction=1),
                full_factorial([2] * k),
            )

    def test_half_fraction_k4_eight_runs_principal_fraction(self):
        design = fractional_factorial_2k(4, fraction=2)
        self.assertEqual(len(design), 8)
        expected = {
            (a, b, c, a * b * c)
            for a, b, c in itertools.product((-1, 1), repeat=3)
        }
        self.assertEqual(set(design), expected)
        self.assertTrue(check_principal_fraction(design, "ABCD"))
        self.assertFalse(check_principal_fraction(design, "ABC"))
        self.assertEqual(fractional_factorial_2k(4, fraction=2), design)

    def test_half_fraction_run_counts_k5_to_k7(self):
        for k, runs in ((5, 16), (6, 32), (7, 64)):
            design = fractional_factorial_2k(k, fraction=2)
            self.assertEqual(len(design), runs)
            self.assertTrue(check_principal_fraction(design, "ABCDEFG"[:k]))

    def test_half_fraction_custom_generator_word(self):
        design = fractional_factorial_2k(4, fraction=2, generator_words=["ABD"])
        self.assertEqual(len(design), 8)
        self.assertTrue(check_principal_fraction(design, "ABD"))

    def test_invalid_k_and_fraction_raise(self):
        with self.assertRaises(ValueError):
            fractional_factorial_2k(0, fraction=1)
        with self.assertRaises(ValueError):
            fractional_factorial_2k(8, fraction=1)
        with self.assertRaises(ValueError):
            fractional_factorial_2k(1.5, fraction=1)
        for bad_fraction in (0, 3, 4):
            with self.assertRaises(ValueError):
                fractional_factorial_2k(5, fraction=bad_fraction)
        with self.assertRaises(ValueError):
            fractional_factorial_2k(3, fraction=2)  # half needs k >= 4
        with self.assertRaises(ValueError):
            fractional_factorial_2k(8, fraction=2)

    def test_invalid_generator_words_raise(self):
        with self.assertRaises(ValueError):
            fractional_factorial_2k(4, fraction=1, generator_words=["ABCD"])
        for bad in ([], ["ABC", "ABD"], ["AABC"], ["ABCDE"], ["A"], [123]):
            with self.assertRaises(ValueError):
                fractional_factorial_2k(4, fraction=2, generator_words=bad)


class TestLatinHypercube(unittest.TestCase):
    EXPECTED_SEED5 = [
        (0.25, 0.45), (0.35, 0.95), (0.15, 0.65), (0.05, 0.55),
        (0.85, 0.75), (0.75, 0.35), (0.65, 0.85), (0.55, 0.15),
        (0.45, 0.25), (0.95, 0.05),
    ]

    def test_shape_unique_rows_and_determinism(self):
        design = latin_hypercube(10, 2, seed=5)
        self.assertEqual(design, self.EXPECTED_SEED5)
        self.assertEqual(len(design), 10)
        self.assertEqual(len(set(design)), 10)
        for row in design:
            self.assertEqual(len(row), 2)
            self.assertTrue(all(0.0 < value < 1.0 for value in row))
        self.assertEqual(latin_hypercube(10, 2, seed=5), design)

    def test_different_seed_changes_sample(self):
        self.assertNotEqual(
            set(latin_hypercube(10, 2, seed=5)),
            set(latin_hypercube(10, 2, seed=6)),
        )

    def test_stratification_per_column(self):
        design = latin_hypercube(10, 2, seed=5)
        for j in range(2):
            strata = sorted(int(row[j] * 10) for row in design)
            self.assertEqual(strata, list(range(10)))
        cube = latin_hypercube(6, 3, seed=11)
        self.assertEqual(len(set(cube)), 6)
        for j in range(3):
            strata = sorted(int(row[j] * 6) for row in cube)
            self.assertEqual(strata, list(range(6)))

    def test_invalid_inputs_raise(self):
        for bad_n in (1, 0, -3, 2.5):
            with self.assertRaises(ValueError):
                latin_hypercube(bad_n, 2, seed=5)
        for bad_k in (0, -1, 1.5):
            with self.assertRaises(ValueError):
                latin_hypercube(10, bad_k, seed=5)
        for bad_seed in (5.5, "five", None):
            with self.assertRaises(ValueError):
                latin_hypercube(10, 2, seed=bad_seed)


class TestCentralComposite(unittest.TestCase):
    def test_k2_center1_layout_and_axial_alpha(self):
        design = central_composite(2, center=1, alpha="axial")
        self.assertEqual(len(design), 9)
        self.assertEqual(2**2 + 2 * 2 + 1, 9)
        alpha = 2.0 ** (2.0 / 4.0)
        self.assertAlmostEqual(alpha, math.sqrt(2.0), places=12)
        self.assertEqual(set(design[:4]), {(-1, -1), (-1, 1), (1, -1), (1, 1)})
        self.assertEqual(
            set(design[4:8]),
            {(alpha, 0.0), (-alpha, 0.0), (0.0, alpha), (0.0, -alpha)},
        )
        self.assertEqual(design[8], (0.0, 0.0))

    def test_k3_center2_run_count_sixteen(self):
        design = central_composite(3, center=2)
        self.assertEqual(len(design), 16)
        self.assertEqual(design.count((0.0, 0.0, 0.0)), 2)
        alpha = 2.0 ** (3.0 / 4.0)
        self.assertAlmostEqual(design[8][0], alpha, places=12)

    def test_faced_and_numeric_alpha(self):
        faced = central_composite(2, center=1, alpha="faced")
        self.assertEqual(
            set(faced[4:8]),
            {(1.0, 0.0), (-1.0, 0.0), (0.0, 1.0), (0.0, -1.0)},
        )
        numeric = central_composite(2, center=1, alpha=2.0)
        self.assertEqual(
            set(numeric[4:8]),
            {(2.0, 0.0), (-2.0, 0.0), (0.0, 2.0), (0.0, -2.0)},
        )

    def test_invalid_inputs_raise(self):
        for bad_k in (1, 8, 0, 2.5):
            with self.assertRaises(ValueError):
                central_composite(bad_k)
        for bad_center in (0, -1, 1.5):
            with self.assertRaises(ValueError):
                central_composite(2, center=bad_center)
        for bad_alpha in ("face", 0.0, -1.0):
            with self.assertRaises(ValueError):
                central_composite(2, center=1, alpha=bad_alpha)


class TestMainEffects(unittest.TestCase):
    def test_worked_example_main_effect_of_a_is_four(self):
        design = full_factorial([2, 2])
        responses = [linear_response_k2(row) for row in design]
        result = analyze_main_effects(design, responses)
        self.assertEqual(result["n_runs"], 4)
        by_factor = {entry["factor"]: entry for entry in result["effects"]}
        self.assertEqual(by_factor["A"]["effect"], 4.0)
        self.assertEqual(by_factor["A"]["low_mean"], -2.0)
        self.assertEqual(by_factor["A"]["high_mean"], 2.0)
        self.assertEqual(by_factor["B"]["effect"], 3.0)
        self.assertEqual(result["ranking"], ["A", "B"])
        flipped = analyze_main_effects(design, [-y for y in responses])
        self.assertEqual(flipped["effects"][0]["effect"], -4.0)

    def test_quadratic_and_linear_response_shapes(self):
        quadratic = full_factorial([2])
        result = analyze_main_effects(
            quadratic, [(row[0] - 0.3) ** 2 for row in quadratic]
        )
        self.assertAlmostEqual(result["effects"][0]["effect"], -1.2, places=10)
        linear = full_factorial([2])
        half = analyze_main_effects(linear, [0.5 * row[0] for row in linear])
        self.assertEqual(half["effects"][0]["effect"], 1.0)  # 2 * 0.5

    def test_ties_rank_in_factor_order(self):
        design = full_factorial([2, 2, 2])
        result = analyze_main_effects(design, [1.0] * 8)
        self.assertEqual(result["ranking"], ["A", "B", "C"])
        self.assertTrue(all(entry["effect"] == 0.0 for entry in result["effects"]))

    def test_validation_raises(self):
        design = full_factorial([2, 2])
        with self.assertRaises(ValueError):
            analyze_main_effects(design, [1.0, 2.0, 3.0])  # short responses
        with self.assertRaises(ValueError):
            analyze_main_effects([], [])
        with self.assertRaises(ValueError):
            analyze_main_effects([[0, 1], [1, 1]], [1.0, 2.0])  # not two-level
        with self.assertRaises(ValueError):
            analyze_main_effects(full_factorial([2, 3]), [1.0] * 6)  # 3-level
        with self.assertRaises(ValueError):
            analyze_main_effects(design, ["a", "b", "c", "d"])  # non-numeric


class TestInteractions(unittest.TestCase):
    def test_worked_example_ab_interaction_is_two(self):
        design = full_factorial([2, 2])
        responses = [linear_response_k2(row) for row in design]
        result = analyze_interactions(design, responses)
        self.assertEqual(result["n_runs"], 4)
        self.assertEqual(len(result["interactions"]), 1)
        entry = result["interactions"][0]
        self.assertEqual(entry["factors"], ("A", "B"))
        self.assertEqual(entry["label"], "AB")
        self.assertEqual(entry["effect"], 2.0)

    def test_pure_interaction_and_additive_models(self):
        design3 = full_factorial([2, 2, 2])
        result = analyze_interactions(design3, [row[0] * row[1] for row in design3])
        by_label = {
            entry["label"]: entry["effect"] for entry in result["interactions"]
        }
        self.assertEqual(by_label["AB"], 2.0)
        self.assertEqual(by_label["AC"], 0.0)
        self.assertEqual(by_label["BC"], 0.0)
        self.assertEqual(
            [entry["label"] for entry in result["interactions"]],
            ["AB", "AC", "BC"],
        )
        additive = analyze_interactions(
            full_factorial([2, 2]), [row[0] + row[1] for row in full_factorial([2, 2])]
        )
        self.assertEqual(additive["interactions"][0]["effect"], 0.0)

    def test_validation_raises(self):
        with self.assertRaises(ValueError):
            analyze_interactions(full_factorial([2]), [1.0, 2.0])  # one factor
        with self.assertRaises(ValueError):
            analyze_interactions(full_factorial([2, 2]), [1.0, 2.0, 3.0])


class TestBuildDesignMatrix(unittest.TestCase):
    def test_dispatch_full_and_fractional(self):
        full = build_design_matrix("full-factorial", levels_per_factor=[2, 2, 2])
        self.assertEqual(full["kind"], "full-factorial")
        self.assertEqual(full["run_count"], 8)
        half = build_design_matrix("fractional-factorial", k=4, fraction=2)
        self.assertEqual(half["run_count"], 8)
        self.assertTrue(check_principal_fraction(half["matrix"], "ABCD"))
        by_alias = build_design_matrix(
            "fractional-factorial-2k", k=5, fraction=1
        )
        self.assertEqual(by_alias["run_count"], 32)

    def test_dispatch_latin_hypercube(self):
        result = build_design_matrix(
            "latin-hypercube", n_samples=10, k_factors=2, seed=5
        )
        self.assertEqual(result["run_count"], 10)
        self.assertEqual(len(set(result["matrix"])), 10)

    def test_dispatch_central_composite_run_count_formula(self):
        for k, center in ((2, 1), (3, 2), (4, 1)):
            result = build_design_matrix(
                "central-composite", k=k, center=center, alpha="axial"
            )
            self.assertEqual(result["run_count"], 2**k + 2 * k + center)

    def test_unknown_kind_and_bad_params_raise(self):
        with self.assertRaises(ValueError):
            build_design_matrix("box-behnken", k=3)
        with self.assertRaises(ValueError):
            build_design_matrix(42)
        with self.assertRaises(ValueError):
            build_design_matrix("latin-hypercube", n_samples=1, k_factors=2, seed=5)
        with self.assertRaises(ValueError):
            build_design_matrix("central-composite", k=1)


class TestHelpers(unittest.TestCase):
    def test_factor_labels(self):
        self.assertEqual(factor_label(0), "A")
        self.assertEqual(factor_label(2), "C")
        self.assertEqual(factor_label(25), "Z")
        self.assertEqual(factor_label(26), "F27")
        with self.assertRaises(ValueError):
            factor_label(-1)

    def test_check_principal_fraction_rejects_bad_word(self):
        design = fractional_factorial_2k(4, fraction=2)
        with self.assertRaises(ValueError):
            check_principal_fraction(design, "ABCDE")
        with self.assertRaises(ValueError):
            check_principal_fraction([[0, 1]], "AB")

    def test_round_trip_identity_and_offline_determinism(self):
        design = full_factorial([2, 2])
        responses = [linear_response_k2(row) for row in design]
        first = analyze_main_effects(design, responses)
        rebuilt = build_design_matrix("full-factorial", levels_per_factor=[2, 2])
        second = analyze_main_effects(rebuilt["matrix"], responses)
        self.assertEqual(first["effects"], second["effects"])
        self.assertEqual(first["ranking"], second["ranking"])
        self.assertEqual(
            latin_hypercube(20, 4, seed=99), latin_hypercube(20, 4, seed=99)
        )
        self.assertEqual(
            central_composite(3, center=3, alpha="axial"),
            central_composite(3, center=3, alpha="axial"),
        )


if __name__ == "__main__":
    unittest.main()
