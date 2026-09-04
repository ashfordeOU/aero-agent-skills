"""Contract test for acceptance_sampling_logic (wave-37, as9100 pack).

Runs offline with stdlib unittest only:
    python3 scripts/test_acceptance_sampling.py

Covers the spec validation list: code letter truth table across the lot
size bands and inspection levels, the single-sampling plan lookup, the
accept/reject decision truth table (Ac accepts, Ac + 1 rejects), the OC
anchor values 0.9534 at p = 0.01 and 0.3748 at p = 0.04 for the (80, 2)
plan within 1e-3, the identities oc(p = 0) = 1.0 and oc(p = 1) = 0 for
Ac < n, determinism, and ValueError rejection of non-physical inputs
(lot_size <= 0, unknown inspection level, unknown (code, AQL) pair, p
outside [0, 1], negative nonconforming count, lot size outside the
documented bands).
"""

import sys
import unittest

sys.path.insert(0, "scripts")

from acceptance_sampling_logic import (
    INSPECTION_LEVELS,
    LOT_SIZE_BANDS,
    code_letter,
    lot_decision,
    oc_acceptance_probability,
    oc_curve,
    sampling_plan,
)


class TestCodeLetter(unittest.TestCase):
    """Sample size code letter from lot size and inspection level."""

    def test_code_letter_anchor_medium_ii_is_J(self):
        # Spec worked example: lot 500 (medium band), level II -> code J.
        self.assertEqual(code_letter(500, "II"), "J")

    def test_code_letter_ii_band_letters(self):
        # Truth table for level II across the documented bands.
        self.assertEqual(code_letter(60, "II"), "F")     # small
        self.assertEqual(code_letter(300, "II"), "J")    # medium
        self.assertEqual(code_letter(1500, "II"), "J")   # large
        self.assertEqual(code_letter(20000, "II"), "L")  # very-large

    def test_code_letter_medium_at_levels_i_and_iii(self):
        self.assertEqual(code_letter(300, "I"), "F")
        self.assertEqual(code_letter(300, "III"), "K")

    def test_code_letter_band_boundaries_inclusive(self):
        self.assertEqual(code_letter(51, "II"), "F")    # small lower edge
        self.assertEqual(code_letter(90, "II"), "F")    # small upper edge
        self.assertEqual(code_letter(281, "II"), "J")   # medium lower edge
        self.assertEqual(code_letter(35000, "II"), "L")  # very-large upper edge

    def test_code_letter_consistent_for_band_midpoints(self):
        for _name, lower, upper in LOT_SIZE_BANDS:
            mid = (lower + upper) // 2
            self.assertEqual(code_letter(mid, "II"), code_letter(mid, "II"))

    def test_code_letter_levels_tuple(self):
        self.assertEqual(INSPECTION_LEVELS, ("I", "II", "III"))

    def test_code_letter_rejects_nonpositive_lot_size(self):
        with self.assertRaises(ValueError):
            code_letter(0, "II")
        with self.assertRaises(ValueError):
            code_letter(-25, "II")

    def test_code_letter_rejects_unknown_level(self):
        with self.assertRaises(ValueError):
            code_letter(500, "IV")
        with self.assertRaises(ValueError):
            code_letter(500, "ii")

    def test_code_letter_rejects_out_of_band_lot_size(self):
        # Sizes between the documented bands have no code letter.
        for bad in (10, 100, 600, 3500, 40000, 50, 91):
            with self.assertRaises(ValueError):
                code_letter(bad, "II")

    def test_code_letter_rejects_non_integer_lot_size(self):
        with self.assertRaises(ValueError):
            code_letter(500.5, "II")


class TestSamplingPlan(unittest.TestCase):
    """Single-sampling plan lookup by code letter and AQL."""

    def test_plan_anchor_j_aql_1(self):
        # Spec worked example: code J, AQL 1.0 -> (80, 2, 3).
        self.assertEqual(sampling_plan("J", 1.0), (80, 2, 3))
        self.assertEqual(sampling_plan("J", "1.0"), (80, 2, 3))

    def test_plan_h_and_l_rows(self):
        self.assertEqual(sampling_plan("H", "1.0"), (50, 1, 2))
        self.assertEqual(sampling_plan("L", "1.0"), (200, 5, 6))

    def test_plan_re_equals_ac_plus_one(self):
        for code in ("J", "H", "L"):
            n, ac, re = sampling_plan(code, "1.0")
            self.assertEqual(re, ac + 1)
            self.assertGreater(n, re)

    def test_plan_rejects_unknown_code_letter(self):
        with self.assertRaises(ValueError):
            sampling_plan("F", "1.0")
        with self.assertRaises(ValueError):
            sampling_plan("K", "1.0")

    def test_plan_rejects_unknown_aql(self):
        with self.assertRaises(ValueError):
            sampling_plan("J", "4.0")
        with self.assertRaises(ValueError):
            sampling_plan("J", 0.65)

    def test_plan_rejects_non_string_code(self):
        with self.assertRaises(ValueError):
            sampling_plan(80, "1.0")


class TestLotDecision(unittest.TestCase):
    """Accept/reject verdict from the nonconforming units found."""

    def test_decision_accepts_at_or_below_ac(self):
        self.assertEqual(lot_decision(0, (80, 2, 3)), "accept")
        self.assertEqual(lot_decision(1, (80, 2, 3)), "accept")
        # Identity: exactly Ac nonconforming units still accepts the lot.
        self.assertEqual(lot_decision(2, (80, 2, 3)), "accept")

    def test_decision_rejects_at_ac_plus_one(self):
        # Identity: Ac + 1 nonconforming units rejects the lot.
        self.assertEqual(lot_decision(3, (80, 2, 3)), "reject")
        self.assertEqual(lot_decision(25, (80, 2, 3)), "reject")

    def test_decision_h_plan_boundary(self):
        self.assertEqual(lot_decision(1, (50, 1, 2)), "accept")
        self.assertEqual(lot_decision(2, (50, 1, 2)), "reject")

    def test_decision_rejects_negative_count(self):
        with self.assertRaises(ValueError):
            lot_decision(-1, (80, 2, 3))

    def test_decision_rejects_non_integer_count(self):
        with self.assertRaises(ValueError):
            lot_decision(1.5, (80, 2, 3))


class TestOCProbability(unittest.TestCase):
    """Binomial operating-characteristic probability of acceptance."""

    def test_oc_anchor_p_001(self):
        # Spec anchor: oc(80, 2, 0.01) = 0.9534 within 1e-3.
        self.assertAlmostEqual(
            oc_acceptance_probability(80, 2, 0.01), 0.9534, delta=1e-3
        )

    def test_oc_anchor_p_004(self):
        # Spec anchor: oc(80, 2, 0.04) = 0.3748 within 1e-3.
        self.assertAlmostEqual(
            oc_acceptance_probability(80, 2, 0.04), 0.3748, delta=1e-3
        )

    def test_oc_identity_at_p_zero_and_one(self):
        # Identity: oc(p = 0) = 1.0; oc(p = 1) = 0 when Ac < n.
        self.assertEqual(oc_acceptance_probability(80, 2, 0.0), 1.0)
        self.assertEqual(oc_acceptance_probability(80, 2, 1.0), 0.0)

    def test_oc_monotone_decreasing_in_p(self):
        p_vals = [0.005, 0.01, 0.02, 0.04, 0.08, 0.15]
        probs = [oc_acceptance_probability(80, 2, p) for p in p_vals]
        self.assertEqual(probs, sorted(probs, reverse=True))

    def test_oc_is_probability_between_zero_and_one(self):
        for p in (0.001, 0.01, 0.04, 0.1, 0.5):
            prob = oc_acceptance_probability(80, 2, p)
            self.assertGreaterEqual(prob, 0.0)
            self.assertLessEqual(prob, 1.0)

    def test_oc_rejects_p_outside_unit_interval(self):
        with self.assertRaises(ValueError):
            oc_acceptance_probability(80, 2, -0.01)
        with self.assertRaises(ValueError):
            oc_acceptance_probability(80, 2, 1.01)

    def test_oc_rejects_non_positive_n(self):
        with self.assertRaises(ValueError):
            oc_acceptance_probability(0, 0, 0.01)
        with self.assertRaises(ValueError):
            oc_acceptance_probability(-80, 2, 0.01)

    def test_oc_rejects_negative_ac(self):
        with self.assertRaises(ValueError):
            oc_acceptance_probability(80, -1, 0.01)


class TestOCCurve(unittest.TestCase):
    """OC curve point list and determinism."""

    def test_curve_returns_point_pairs_in_order(self):
        p_vals = [0.005, 0.01, 0.04, 0.1]
        curve = oc_curve(80, 2, p_vals)
        self.assertEqual([point[0] for point in curve], p_vals)
        for p, prob in curve:
            self.assertAlmostEqual(prob, oc_acceptance_probability(80, 2, p))

    def test_curve_empty_input_returns_empty(self):
        self.assertEqual(oc_curve(80, 2, []), [])

    def test_curve_deterministic(self):
        p_vals = [0.005, 0.01, 0.02, 0.04, 0.08, 0.1, 0.2]
        self.assertEqual(oc_curve(80, 2, p_vals), oc_curve(80, 2, p_vals))

    def test_curve_rejects_out_of_range_p(self):
        with self.assertRaises(ValueError):
            oc_curve(80, 2, [0.01, 1.5])


class TestWorkedExampleFlow(unittest.TestCase):
    """End-to-end spec worked example: lot 500, level II, AQL 1.0."""

    def test_worked_example_full_flow(self):
        code = code_letter(500, "II")
        plan = sampling_plan(code, 1.0)
        self.assertEqual(code, "J")
        self.assertEqual(plan, (80, 2, 3))
        self.assertEqual(lot_decision(1, plan), "accept")
        self.assertEqual(lot_decision(3, plan), "reject")
        self.assertAlmostEqual(
            oc_acceptance_probability(80, 2, 0.01), 0.9534, delta=1e-3
        )
        self.assertAlmostEqual(
            oc_acceptance_probability(80, 2, 0.04), 0.3748, delta=1e-3
        )

    def test_module_deterministic_across_calls(self):
        self.assertEqual(
            oc_curve(80, 2, [0.01, 0.04]), oc_curve(80, 2, [0.01, 0.04])
        )


if __name__ == "__main__":
    unittest.main(verbosity=2)
