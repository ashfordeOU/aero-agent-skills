"""Contract test: attribute agreement analysis (Cohen and Fleiss kappa).

Offline deterministic stdlib unittest. Run:
    python3 scripts/test_attribute_agreement_analysis.py
"""

import unittest

import attribute_agreement_analysis_logic as aaa

COHEN_TABLE = [[24, 3], [5, 8]]  # 40 parts, pass/fail, inspectors A and B

FLEISS_MATRIX = [
    [3, 0, 0], [3, 0, 0], [2, 1, 0], [3, 0, 0], [0, 2, 1],
    [2, 1, 0], [3, 0, 0], [1, 2, 0], [3, 0, 0], [0, 3, 0],
    [2, 1, 0], [3, 0, 0], [1, 2, 0], [0, 2, 1], [2, 1, 0],
    [3, 0, 0], [1, 2, 0], [3, 0, 0], [0, 3, 0], [2, 1, 0],
]  # 20 parts, 3 inspectors, accept/rework/reject


class TestPercentAgreement(unittest.TestCase):
    def test_percent_agreement_worked_example(self):
        self.assertAlmostEqual(aaa.percent_agreement(COHEN_TABLE), 0.8000, places=4)

    def test_percent_agreement_is_diagonal_fraction(self):
        table = [[4, 1, 0], [1, 6, 2], [0, 1, 5]]
        diagonal = 4 + 6 + 5
        total = sum(sum(row) for row in table)
        self.assertEqual(aaa.percent_agreement(table), diagonal / total)

    def test_percent_agreement_non_square_value_error(self):
        with self.assertRaises(ValueError):
            aaa.percent_agreement([[1, 2, 3], [4, 5, 6]])

    def test_percent_agreement_ragged_rows_value_error(self):
        with self.assertRaises(ValueError):
            aaa.percent_agreement([[1, 2], [3]])

    def test_percent_agreement_negative_count_value_error(self):
        with self.assertRaises(ValueError):
            aaa.percent_agreement([[2, -1], [1, 4]])

    def test_percent_agreement_zero_total_value_error(self):
        with self.assertRaises(ValueError):
            aaa.percent_agreement([[0, 0], [0, 0]])

    def test_percent_agreement_empty_table_value_error(self):
        with self.assertRaises(ValueError):
            aaa.percent_agreement([])


class TestCohenKappa(unittest.TestCase):
    def test_cohen_worked_example_kappa(self):
        result = aaa.cohen_kappa(COHEN_TABLE)
        self.assertAlmostEqual(result["kappa"], 0.5252, places=4)
        self.assertEqual(aaa.kappa_verdict(result["kappa"]), "marginal")

    def test_cohen_worked_observed_and_chance_agreement(self):
        result = aaa.cohen_kappa(COHEN_TABLE)
        self.assertAlmostEqual(result["observed_agreement"], 0.8000, places=4)
        self.assertAlmostEqual(result["chance_agreement"], 0.57875, places=5)

    def test_cohen_dict_keys(self):
        self.assertEqual(
            sorted(aaa.cohen_kappa(COHEN_TABLE).keys()),
            ["chance_agreement", "kappa", "observed_agreement"],
        )

    def test_cohen_diagonal_table_kappa_one(self):
        result = aaa.cohen_kappa([[10, 0], [0, 10]])
        self.assertEqual(result["observed_agreement"], 1.0)
        self.assertEqual(result["chance_agreement"], 0.5)
        self.assertEqual(result["kappa"], 1.0)

    def test_cohen_independence_kappa_zero(self):
        result = aaa.cohen_kappa([[5, 5], [5, 5]])
        self.assertEqual(result["observed_agreement"], 0.5)
        self.assertAlmostEqual(result["kappa"], 0.0, places=12)

    def test_cohen_same_value_errors_as_percent_agreement(self):
        with self.assertRaises(ValueError):
            aaa.cohen_kappa([[1, 2, 3], [4, 5, 6]])
        with self.assertRaises(ValueError):
            aaa.cohen_kappa([[1, -2], [3, 4]])
        with self.assertRaises(ValueError):
            aaa.cohen_kappa([[0, 0], [0, 0]])
        with self.assertRaises(ValueError):
            aaa.cohen_kappa([])

    def test_cohen_single_category_chance_one_value_error(self):
        with self.assertRaises(ValueError):
            aaa.cohen_kappa([[5]])


class TestFleissKappa(unittest.TestCase):
    def test_fleiss_worked_example_kappa(self):
        result = aaa.fleiss_kappa(FLEISS_MATRIX)
        self.assertAlmostEqual(result["kappa"], 0.3281, places=4)
        self.assertEqual(aaa.kappa_verdict(result["kappa"]), "poor")

    def test_fleiss_worked_pbar(self):
        result = aaa.fleiss_kappa(FLEISS_MATRIX)
        self.assertAlmostEqual(result["pbar"], 0.6667, places=4)

    def test_fleiss_worked_pe(self):
        result = aaa.fleiss_kappa(FLEISS_MATRIX)
        self.assertAlmostEqual(result["pe"], 0.50389, places=5)

    def test_fleiss_dict_keys(self):
        self.assertEqual(sorted(aaa.fleiss_kappa(FLEISS_MATRIX).keys()), ["kappa", "pbar", "pe"])

    def test_fleiss_unanimous_perfect_agreement_kappa_one(self):
        result = aaa.fleiss_kappa([[3, 0, 0], [0, 3, 0], [3, 0, 0], [0, 3, 0]])
        self.assertAlmostEqual(result["kappa"], 1.0, places=9)
        self.assertAlmostEqual(result["pbar"], 1.0, places=9)

    def test_fleiss_empty_and_ragged_matrix_value_error(self):
        with self.assertRaises(ValueError):
            aaa.fleiss_kappa([])
        with self.assertRaises(ValueError):
            aaa.fleiss_kappa([[2, 0, 0], [1, 1, 0], [0, 3]])

    def test_fleiss_row_sum_below_two_value_error(self):
        with self.assertRaises(ValueError):
            aaa.fleiss_kappa([[2, 0, 0], [1, 0, 0]])

    def test_fleiss_negative_count_value_error(self):
        with self.assertRaises(ValueError):
            aaa.fleiss_kappa([[2, -1, 1], [0, 2, 1]])

    def test_fleiss_pe_one_value_error(self):
        with self.assertRaises(ValueError):
            aaa.fleiss_kappa([[3, 0, 0], [3, 0, 0]])


class TestKappaVerdict(unittest.TestCase):
    def test_verdict_good_band(self):
        self.assertEqual(aaa.kappa_verdict(0.80), "good")
        self.assertEqual(aaa.kappa_verdict(1.0), "good")

    def test_verdict_marginal_band(self):
        self.assertEqual(aaa.kappa_verdict(0.60), "marginal")
        self.assertEqual(aaa.kappa_verdict(0.40), "marginal")

    def test_verdict_poor_band(self):
        self.assertEqual(aaa.kappa_verdict(0.20), "poor")
        self.assertEqual(aaa.kappa_verdict(-0.2), "poor")
        self.assertEqual(aaa.kappa_verdict(-1.0), "poor")

    def test_verdict_band_thresholds(self):
        self.assertEqual(aaa.kappa_verdict(0.75), "good")
        self.assertEqual(aaa.kappa_verdict(0.7499), "marginal")
        self.assertEqual(aaa.kappa_verdict(0.3999), "poor")

    def test_verdict_out_of_range_value_error(self):
        with self.assertRaises(ValueError):
            aaa.kappa_verdict(1.01)
        with self.assertRaises(ValueError):
            aaa.kappa_verdict(-1.01)


class TestAgreementSummary(unittest.TestCase):
    def test_summary_cohen_dispatch(self):
        summary = aaa.agreement_summary(table=COHEN_TABLE)
        self.assertEqual(summary["method"], "cohen")
        self.assertAlmostEqual(summary["kappa"], 0.5252, places=4)
        self.assertEqual(summary["verdict"], "marginal")

    def test_summary_fleiss_dispatch(self):
        summary = aaa.agreement_summary(ratings_matrix=FLEISS_MATRIX)
        self.assertEqual(summary["method"], "fleiss")
        self.assertAlmostEqual(summary["kappa"], 0.3281, places=4)
        self.assertEqual(summary["verdict"], "poor")

    def test_summary_documented_keys(self):
        cohen_summary = aaa.agreement_summary(table=COHEN_TABLE)
        self.assertEqual(
            sorted(cohen_summary.keys()),
            ["chance_agreement", "kappa", "method", "observed_agreement", "verdict"],
        )
        fleiss_summary = aaa.agreement_summary(ratings_matrix=FLEISS_MATRIX)
        self.assertEqual(
            sorted(fleiss_summary.keys()),
            ["kappa", "method", "pbar", "pe", "verdict"],
        )

    def test_summary_requires_exactly_one_input(self):
        with self.assertRaises(ValueError):
            aaa.agreement_summary()
        with self.assertRaises(ValueError):
            aaa.agreement_summary(table=COHEN_TABLE, ratings_matrix=FLEISS_MATRIX)


class TestDeterminism(unittest.TestCase):
    def test_cohen_deterministic(self):
        first = aaa.cohen_kappa(COHEN_TABLE)
        second = aaa.cohen_kappa(COHEN_TABLE)
        self.assertEqual(first, second)

    def test_fleiss_deterministic(self):
        first = aaa.fleiss_kappa(FLEISS_MATRIX)
        second = aaa.fleiss_kappa(FLEISS_MATRIX)
        self.assertEqual(first, second)


if __name__ == "__main__":
    unittest.main()
