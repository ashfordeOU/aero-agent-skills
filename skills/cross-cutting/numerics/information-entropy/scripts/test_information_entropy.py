"""Contract test for information_entropy_logic (offline, stdlib unittest).

Run: python3 test_information_entropy.py  -> exit 0.
Covers the spec validation list: worked-example anchors, identities,
ValueError rejection, bounds, determinism, and dict-key contracts.
"""

import unittest

from information_entropy_logic import (
    shannon_entropy,
    binary_entropy,
    uniform_entropy,
    min_bit_rate,
    entropy_summary,
)

WORKED = [0.5, 0.25, 0.125, 0.125]
SKEW = [0.9, 0.05, 0.03, 0.02]


class ShannonEntropyTests(unittest.TestCase):
    def test_worked_example_entropy_1_75(self):
        self.assertAlmostEqual(shannon_entropy(WORKED)["entropy_bits"], 1.75, delta=1e-4)

    def test_max_entropy_bound_holds(self):
        self.assertLessEqual(shannon_entropy(WORKED)["entropy_bits"], 2.0)
        self.assertLess(shannon_entropy(SKEW)["entropy_bits"], 2.0)

    def test_entropy_nonnegative_for_valid_distributions(self):
        for dist in ([1.0], [0.5, 0.5], [0.25] * 4, [5, 3, 2], [10, 0, 0], SKEW):
            self.assertGreaterEqual(shannon_entropy(dist)["entropy_bits"], 0.0)

    def test_deterministic_distributions_zero(self):
        self.assertEqual(shannon_entropy([1.0])["entropy_bits"], 0.0)
        self.assertEqual(shannon_entropy([10])["entropy_bits"], 0.0)
        self.assertEqual(shannon_entropy([1.0, 0.0])["entropy_bits"], 0.0)
        self.assertEqual(shannon_entropy([7, 0])["entropy_bits"], 0.0)

    def test_counts_normalize_identically_to_probabilities(self):
        self.assertAlmostEqual(
            shannon_entropy([5, 5])["entropy_bits"], 1.0, delta=1e-12
        )
        self.assertAlmostEqual(
            shannon_entropy([5, 5])["entropy_bits"],
            shannon_entropy([0.5, 0.5])["entropy_bits"],
            delta=1e-12,
        )
        self.assertAlmostEqual(
            shannon_entropy([3, 1])["entropy_bits"],
            shannon_entropy([0.75, 0.25])["entropy_bits"],
            delta=1e-12,
        )
        self.assertAlmostEqual(
            shannon_entropy([3, 1])["entropy_bits"], 0.8112781244591328, delta=1e-9
        )

    def test_uniform_probs_equal_uniform_entropy_function(self):
        self.assertAlmostEqual(
            shannon_entropy([0.25] * 4)["entropy_bits"], uniform_entropy(4), delta=1e-12
        )
        self.assertAlmostEqual(
            shannon_entropy([0.5, 0.5])["entropy_bits"], uniform_entropy(2), delta=1e-12
        )

    def test_normalized_values_contract(self):
        result = shannon_entropy(WORKED)
        self.assertEqual(result["normalized"], [0.5, 0.25, 0.125, 0.125])
        self.assertAlmostEqual(sum(shannon_entropy([3, 1, 6])["normalized"]), 1.0, delta=1e-12)

    def test_shannon_dict_keys_exact(self):
        self.assertEqual(
            set(shannon_entropy(WORKED).keys()), {"entropy_bits", "normalized"}
        )

    def test_shannon_empty_input_raises(self):
        with self.assertRaises(ValueError):
            shannon_entropy([])

    def test_shannon_negative_value_raises(self):
        with self.assertRaises(ValueError):
            shannon_entropy([-0.5, 1.5])
        with self.assertRaises(ValueError):
            shannon_entropy([1, -2, 3])

    def test_shannon_zero_sum_raises(self):
        with self.assertRaises(ValueError):
            shannon_entropy([0, 0])
        with self.assertRaises(ValueError):
            shannon_entropy([0])

    def test_shannon_determinism(self):
        self.assertEqual(shannon_entropy(WORKED), shannon_entropy(WORKED))


class BinaryEntropyTests(unittest.TestCase):
    def test_worked_example_binary_entropy_0_469(self):
        self.assertAlmostEqual(binary_entropy(0.9), 0.4690, delta=1e-4)

    def test_binary_entropy_half_is_one(self):
        self.assertEqual(binary_entropy(0.5), 1.0)

    def test_binary_entropy_endpoints_zero(self):
        self.assertEqual(binary_entropy(0.0), 0.0)
        self.assertEqual(binary_entropy(1.0), 0.0)

    def test_binary_entropy_symmetry(self):
        for p in (0.3, 0.7, 0.1, 0.9, 0.45, 0.99):
            self.assertAlmostEqual(binary_entropy(p), binary_entropy(1.0 - p), delta=1e-12)

    def test_binary_entropy_between_zero_and_one(self):
        for p in (0.001, 0.25, 0.5, 0.75, 0.999):
            self.assertGreaterEqual(binary_entropy(p), 0.0)
            self.assertLessEqual(binary_entropy(p), 1.0)

    def test_binary_entropy_out_of_range_raises(self):
        with self.assertRaises(ValueError):
            binary_entropy(-0.1)
        with self.assertRaises(ValueError):
            binary_entropy(1.1)


class UniformEntropyTests(unittest.TestCase):
    def test_uniform_entropy_exact_values(self):
        self.assertEqual(uniform_entropy(1), 0.0)
        self.assertEqual(uniform_entropy(2), 1.0)
        self.assertEqual(uniform_entropy(4), 2.0)
        self.assertEqual(uniform_entropy(8), 3.0)
        self.assertEqual(uniform_entropy(16), 4.0)
        self.assertEqual(uniform_entropy(32), 5.0)

    def test_uniform_entropy_invalid_n_raises(self):
        with self.assertRaises(ValueError):
            uniform_entropy(0)
        with self.assertRaises(ValueError):
            uniform_entropy(-3)


class MinBitRateTests(unittest.TestCase):
    def test_worked_example_bit_rate_1750(self):
        self.assertAlmostEqual(min_bit_rate(1.75, 1000.0), 1750.0, delta=1e-9)

    def test_worked_example_uniform8_rate_and_reduction(self):
        self.assertAlmostEqual(min_bit_rate(3.0, 1000.0), 3000.0, delta=1e-9)
        reduction = (min_bit_rate(3.0, 1000.0) - min_bit_rate(1.75, 1000.0)) / min_bit_rate(3.0, 1000.0)
        self.assertAlmostEqual(reduction, 0.4166666666666667, delta=1e-3)

    def test_min_bit_rate_zero_edges(self):
        self.assertEqual(min_bit_rate(0.0, 1000.0), 0.0)
        self.assertEqual(min_bit_rate(1.75, 0.0), 0.0)
        self.assertAlmostEqual(min_bit_rate(1.75, 2000.0), 3500.0, delta=1e-9)

    def test_min_bit_rate_negative_inputs_raise(self):
        with self.assertRaises(ValueError):
            min_bit_rate(-0.5, 1000.0)
        with self.assertRaises(ValueError):
            min_bit_rate(1.0, -10.0)


class EntropySummaryTests(unittest.TestCase):
    def test_worked_example_summary(self):
        result = entropy_summary(WORKED, 1000.0)
        self.assertAlmostEqual(result["entropy_bits"], 1.75, delta=1e-4)
        self.assertEqual(result["n_symbols"], 4)
        self.assertAlmostEqual(result["uniform_bound_bits"], 2.0, delta=1e-12)
        self.assertAlmostEqual(result["redundancy"], 0.125, delta=1e-9)
        self.assertAlmostEqual(result["min_bit_rate_bps"], 1750.0, delta=1e-9)

    def test_summary_dict_keys_exact(self):
        self.assertEqual(
            set(entropy_summary(WORKED, 1000.0).keys()),
            {"entropy_bits", "n_symbols", "uniform_bound_bits", "redundancy", "min_bit_rate_bps"},
        )

    def test_summary_uniform_source_zero_redundancy(self):
        result = entropy_summary([0.25] * 4, 2000.0)
        self.assertAlmostEqual(result["redundancy"], 0.0, delta=1e-12)
        self.assertAlmostEqual(result["uniform_bound_bits"], 2.0, delta=1e-12)
        self.assertAlmostEqual(result["min_bit_rate_bps"], 4000.0, delta=1e-9)

    def test_summary_deterministic_source_full_redundancy(self):
        result = entropy_summary([1.0, 0.0], 100.0)
        self.assertAlmostEqual(result["entropy_bits"], 0.0, delta=1e-12)
        self.assertAlmostEqual(result["redundancy"], 1.0, delta=1e-12)
        self.assertAlmostEqual(result["min_bit_rate_bps"], 0.0, delta=1e-12)

    def test_summary_redundancy_within_unit_interval(self):
        for dist in (WORKED, SKEW, [0.25] * 4, [0.9, 0.1], [1.0, 0.0]):
            r = entropy_summary(dist, 500.0)["redundancy"]
            self.assertGreaterEqual(r, 0.0)
            self.assertLessEqual(r, 1.0)

    def test_summary_accepts_raw_counts(self):
        result = entropy_summary([5, 5], 1000.0)
        self.assertAlmostEqual(result["entropy_bits"], 1.0, delta=1e-12)
        self.assertAlmostEqual(result["min_bit_rate_bps"], 1000.0, delta=1e-9)

    def test_summary_too_few_symbols_raises(self):
        with self.assertRaises(ValueError):
            entropy_summary([], 1000.0)
        with self.assertRaises(ValueError):
            entropy_summary([0.5], 1000.0)
        with self.assertRaises(ValueError):
            entropy_summary([1.0], 1000.0)

    def test_summary_determinism(self):
        self.assertEqual(entropy_summary(WORKED, 1000.0), entropy_summary(WORKED, 1000.0))


if __name__ == "__main__":
    unittest.main()
