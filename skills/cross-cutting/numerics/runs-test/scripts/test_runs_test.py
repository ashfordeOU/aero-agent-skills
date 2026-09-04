"""test_runs_test.py

Offline deterministic contract test for the runs-test leaf
(cross-cutting/numerics/runs-test). Runs with:
python3 scripts/test_runs_test.py

Covers the Wald-Wolfowitz worked-example anchors (R = 4, E = 11.000,
Var = 4.7368, sd = 2.1764, z = -3.216, verdict REJECT), the runs
count identities (alternating sequence of length 10 gives the maximum
10 runs), the fail-to-reject random-looking fixture, the verdict
boundary semantics at the critical value, dict key contract,
determinism, and ValueError rejection of every non-physical input.
"""

import unittest

from runs_test_logic import (
    Z_CRIT_95_TWOTAIL,
    count_runs,
    expected_runs,
    runs_test,
    runs_variance,
)

# Worked example: +++++ ----- +++++ ----- (five plus, five minus,
# five plus, five minus), n1 = n2 = 10.
ANCHOR = [
    1, 1, 1, 1, 1, -1, -1, -1, -1, -1,
    1, 1, 1, 1, 1, -1, -1, -1, -1, -1,
]

# Alternating sequence of length 10 with 5 plus and 5 minus.
ALT10 = [1, -1, 1, -1, 1, -1, 1, -1, 1, -1]

# Random-looking fixture: ++-- repeated three times, n1 = n2 = 6.
RAND = [1, 1, -1, -1, 1, 1, -1, -1, 1, 1, -1, -1]

RESULT_KEYS = {"n1", "n2", "runs", "expected", "variance", "sd", "z", "verdict"}


class TestCountRuns(unittest.TestCase):
    def test_anchor_fixture_runs_is_four(self):
        self.assertEqual(count_runs(ANCHOR), 4)

    def test_alternating_ten_signs_maximum_runs(self):
        self.assertEqual(count_runs(ALT10), 10)

    def test_small_mixed_sequence_counts_blocks(self):
        self.assertEqual(count_runs([1, -1, -1, 1]), 3)

    def test_single_sign_sequence_value_error(self):
        with self.assertRaises(ValueError):
            count_runs([1, 1, 1, 1, 1])

    def test_too_short_sequence_value_error(self):
        with self.assertRaises(ValueError):
            count_runs([1, -1, 1])

    def test_empty_sequence_value_error(self):
        with self.assertRaises(ValueError):
            count_runs([])

    def test_invalid_zero_sign_value_error(self):
        with self.assertRaises(ValueError):
            count_runs([1, 0, -1, 1])

class TestExpectedRuns(unittest.TestCase):
    def test_balanced_ten_expected_is_eleven(self):
        self.assertAlmostEqual(expected_runs(10, 10), 11.0, delta=1e-9)

    def test_expected_symmetric_in_sign_counts(self):
        self.assertAlmostEqual(expected_runs(6, 4), expected_runs(4, 6), delta=1e-12)

    def test_expected_small_balanced_case(self):
        self.assertAlmostEqual(expected_runs(2, 2), 3.0, delta=1e-12)

    def test_expected_nonpositive_n1_value_error(self):
        with self.assertRaises(ValueError):
            expected_runs(0, 5)

    def test_expected_nonpositive_n2_value_error(self):
        with self.assertRaises(ValueError):
            expected_runs(5, -1)


class TestRunsVariance(unittest.TestCase):
    def test_variance_anchor_within_spec_bound(self):
        self.assertAlmostEqual(runs_variance(10, 10), 4.7368, delta=1e-4)

    def test_sd_anchor_within_spec_bound(self):
        sd = runs_variance(10, 10) ** 0.5
        self.assertAlmostEqual(sd, 2.1764, delta=1e-4)

    def test_variance_symmetric_in_sign_counts(self):
        self.assertAlmostEqual(runs_variance(7, 5), runs_variance(5, 7), delta=1e-12)

    def test_variance_small_balanced_case(self):
        # n1 = n2 = 2: 2*4*(8-4)/(16*3) = 2/3.
        self.assertAlmostEqual(runs_variance(2, 2), 2.0 / 3.0, delta=1e-12)

    def test_variance_positive_finite_for_anchor(self):
        v = runs_variance(10, 10)
        self.assertGreater(v, 0.0)
        self.assertTrue(v == v)  # not NaN

    def test_variance_nonpositive_n1_value_error(self):
        with self.assertRaises(ValueError):
            runs_variance(0, 4)

    def test_variance_total_below_four_value_error(self):
        with self.assertRaises(ValueError):
            runs_variance(1, 2)


class TestRunsTest(unittest.TestCase):
    def test_anchor_z_and_verdict(self):
        r = runs_test(ANCHOR)
        self.assertAlmostEqual(r["z"], -3.216, delta=1e-3)
        self.assertEqual(r["verdict"], "REJECT")

    def test_anchor_counts_and_components(self):
        r = runs_test(ANCHOR)
        self.assertEqual(r["n1"], 10)
        self.assertEqual(r["n2"], 10)
        self.assertEqual(r["runs"], 4)
        self.assertAlmostEqual(r["expected"], 11.0, delta=1e-9)

    def test_anchor_abs_z_exceeds_1_96(self):
        r = runs_test(ANCHOR)
        self.assertGreaterEqual(abs(r["z"]), Z_CRIT_95_TWOTAIL)

    def test_random_looking_fixture_fails_to_reject(self):
        r = runs_test(RAND)
        self.assertLess(abs(r["z"]), Z_CRIT_95_TWOTAIL)
        self.assertEqual(r["verdict"], "FAIL_TO_REJECT")

    def test_random_fixture_counts(self):
        r = runs_test(RAND)
        self.assertEqual(r["n1"], 6)
        self.assertEqual(r["n2"], 6)
        self.assertEqual(r["runs"], 6)
        self.assertAlmostEqual(r["expected"], 7.0, delta=1e-9)

    def test_strict_critical_value_rejects_random_fixture(self):
        r = runs_test(RAND, z_crit=0.5)
        self.assertEqual(r["verdict"], "REJECT")

    def test_relaxed_critical_value_accepts_anchor(self):
        r = runs_test(ANCHOR, z_crit=5.0)
        self.assertEqual(r["verdict"], "FAIL_TO_REJECT")

    def test_verdict_boundary_at_critical_value_is_reject(self):
        r = runs_test(ANCHOR)
        at_crit = runs_test(ANCHOR, z_crit=abs(r["z"]))
        self.assertEqual(at_crit["verdict"], "REJECT")

    def test_result_dict_keys_exactly_as_documented(self):
        self.assertEqual(set(runs_test(ANCHOR).keys()), RESULT_KEYS)

    def test_result_deterministic_across_calls(self):
        self.assertEqual(runs_test(ANCHOR), runs_test(ANCHOR))

    def test_runs_test_rejects_too_short(self):
        with self.assertRaises(ValueError):
            runs_test([1, -1, 1])

    def test_runs_test_rejects_single_sign(self):
        with self.assertRaises(ValueError):
            runs_test([1, 1, 1, 1])

    def test_default_critical_value_is_1_96(self):
        self.assertEqual(Z_CRIT_95_TWOTAIL, 1.96)


if __name__ == "__main__":
    unittest.main()
