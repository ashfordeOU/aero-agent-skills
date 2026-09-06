#!/usr/bin/env python3
"""Contract test for the fault-tree-quantification leaf (ARP4761A pack).

Exercises every numbered step of the SKILL.md workflow against the
deterministic stdlib module scripts/fault_tree_quantification_logic.py:
step 1 gathers the analysis inputs (cut sets and basic-event
probabilities) and rejects non-physical data, step 2 runs the rare-event
approximation pass, step 3 runs the Esary-Proschan min-cut upper bound
pass, step 4 runs the exact inclusion-exclusion pass with its 12-cut-set
guard, step 5 truncates the cut-set list below an analyst probability
threshold and reports the retained probability share, step 6 ranks the
cut sets by per-cut-set probability share, step 7 assembles the
quantified top-event probability and bound chain for the SSA predicted
probability feed, and step 8 confirms determinism. Numeric asserts are
order-safe throughout: computed aggregates are compared with
assertAlmostEqual(delta=...) or math.isclose, never by exact float
equality (wave-41 exact-float lesson: this leaf sums cut-set
probabilities).

Run offline: python3 scripts/test_fault_tree_quantification.py
"""

import math
import os
import sys
import unittest

sys.path.insert(
    0, os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
)

import fault_tree_quantification_logic as ftq

# Worked tree: elevator actuation supply loss, dual channel. Five minimal
# cut sets derived by the fta-fmea leaf; several cuts share basic events
# (P-A in cuts 1 and 2, P-B in cuts 1 and 3), so the overlap correction of
# the exact union is non-trivial. Probabilities are per flight hour.
CUT_SETS = [
    {"P-A", "P-B"},     # both pumps lost, q_cut 1.000000e-08
    {"P-A", "RSV"},     # pump A and shared reservoir lost, q_cut 2.000000e-09
    {"P-B", "RSV"},     # pump B and shared reservoir lost, q_cut 2.000000e-09
    {"V-A", "V-B"},     # both servo-valve channels jammed, q_cut 2.500000e-09
    {"C-A", "C-B"},     # both flight-control computers lost, q_cut 1.000000e-10
]
PROBS = {
    "C-A": 1.0e-05,
    "C-B": 1.0e-05,
    "P-A": 1.0e-04,
    "P-B": 1.0e-04,
    "RSV": 2.0e-05,
    "V-A": 5.0e-05,
    "V-B": 5.0e-05,
}


class RareEventApproximationTests(unittest.TestCase):
    """Workflow step 2: the rare-event approximation pass sums the
    cut-set probabilities into the first-order top-event estimate."""

    def test_rare_event_worked_tree(self):
        """Step 2 on the worked tree: the five cut-set products sum to the
        rare-event approximation 1.66e-08 (double nearest the true sum),
        asserted within an absolute 1e-20 tolerance."""
        q_re = ftq.rare_event_probability(CUT_SETS, PROBS)
        self.assertAlmostEqual(q_re, 1.66e-08, delta=1e-20)

    def test_rare_event_disjoint_pair_sums(self):
        """Step 2 with disjoint single-event cuts {P-A} at 2e-4 and {P-B}
        at 3e-4 returns the plain sum 5.0e-4 within 1e-12 relative, above
        the exact union a + b - a*b that step 3 and step 4 reproduce."""
        q_re = ftq.rare_event_probability(
            [{"P-A"}, {"P-B"}], {"P-A": 2.0e-4, "P-B": 3.0e-4}
        )
        self.assertTrue(math.isclose(q_re, 5.0e-4, rel_tol=1e-12))

    def test_rare_event_overlapping_cuts_overestimates(self):
        """Step 2 on cuts that share a basic event, {A,B} and {A,C},
        overestimates the exact union (workflow step 7 bound-chain
        picture): the inclusion-exclusion pair term subtracts the shared
        A*B*C mass, so Q_ie = 4.994e-6 sits below the 5e-6 rare-event
        sum."""
        cut_sets = [{"A", "B"}, {"A", "C"}]
        probs = {"A": 1.0e-3, "B": 2.0e-3, "C": 3.0e-3}
        q_re = ftq.rare_event_probability(cut_sets, probs)
        q_ie = ftq.exact_top_probability(cut_sets, probs)
        self.assertTrue(math.isclose(q_ie, 4.994e-6, rel_tol=1e-9))
        self.assertLess(q_ie, q_re)


class MinCutUpperBoundTests(unittest.TestCase):
    """Workflow step 3: the Esary-Proschan min-cut upper bound pass
    evaluates 1 - product(1 - q_i) over the cut sets."""

    def test_min_cut_upper_worked_tree(self):
        """Step 3 on the worked tree returns the min-cut upper bound
        1.660000015224483e-08 within an absolute 1e-20 tolerance."""
        q_ep = ftq.min_cut_upper_bound(CUT_SETS, PROBS)
        self.assertAlmostEqual(q_ep, 1.660000015224483e-08, delta=1e-20)

    def test_min_cut_upper_disjoint_pair_closed_form(self):
        """Step 3 with disjoint single-event cuts {P-A} at 2e-4 and {P-B}
        at 3e-4 reproduces the exact union 1 - (1-a)(1-b) = 4.9994e-4
        within 1e-12 relative: the upper bound is exact for disjoint
        cuts."""
        q_ep = ftq.min_cut_upper_bound(
            [{"P-A"}, {"P-B"}], {"P-A": 2.0e-4, "P-B": 3.0e-4}
        )
        self.assertTrue(math.isclose(q_ep, 4.9994e-4, rel_tol=1e-12))

    def test_ep_le_re_worked_tree(self):
        """Steps 2 and 3 together on the worked tree: the Esary-Proschan
        bound never exceeds the rare-event sum, Q_ep <= Q_re + 1e-15 (the
        float survival product sits near 1.0, so the contract tolerates
        its rounding floor)."""
        q_re = ftq.rare_event_probability(CUT_SETS, PROBS)
        q_ep = ftq.min_cut_upper_bound(CUT_SETS, PROBS)
        self.assertLessEqual(q_ep, q_re + 1e-15)


class ExactInclusionExclusionTests(unittest.TestCase):
    """Workflow step 4: the exact inclusion-exclusion pass iterates the
    2**n - 1 non-empty cut-set subsets and adds (-1)**(k+1) times the
    union product."""

    def test_exact_ie_worked_tree(self):
        """Step 4 on the worked tree returns the exact top probability
        1.6599599963351046e-08 within an absolute 1e-20 tolerance; the
        pair terms subtract the overlap mass the rare-event sum ignores."""
        q_ie = ftq.exact_top_probability(CUT_SETS, PROBS)
        self.assertAlmostEqual(q_ie, 1.6599599963351046e-08, delta=1e-20)

    def test_single_cut_all_three_formulas(self):
        """Workflow steps 2, 3 and 4 with one cut set {P-A} at 2.0e-4: all
        three top formulas return that cut-set probability within 1e-12
        relative, the spec identity that the approximations are exact for
        a single cut set."""
        cut_sets = [{"P-A"}]
        probs = {"P-A": 2.0e-4}
        q_re = ftq.rare_event_probability(cut_sets, probs)
        q_ep = ftq.min_cut_upper_bound(cut_sets, probs)
        q_ie = ftq.exact_top_probability(cut_sets, probs)
        self.assertTrue(math.isclose(q_re, 2.0e-4, rel_tol=1e-12))
        self.assertTrue(math.isclose(q_ep, 2.0e-4, rel_tol=1e-12))
        self.assertTrue(math.isclose(q_ie, 2.0e-4, rel_tol=1e-12))

    def test_ie_below_ep_worked_gap(self):
        """Steps 3 and 4 bound chain on the worked tree: the Esary-Proschan
        upper bound clears the exact inclusion-exclusion result by
        4.001889e-13 within an absolute 1e-18 tolerance."""
        q_ep = ftq.min_cut_upper_bound(CUT_SETS, PROBS)
        q_ie = ftq.exact_top_probability(CUT_SETS, PROBS)
        self.assertAlmostEqual(q_ep - q_ie, 4.001889e-13, delta=1e-18)
        self.assertLess(q_ie, q_ep)

    def test_ie_below_re_worked_gap(self):
        """Steps 2 and 4 bound chain on the worked tree: the rare-event
        approximation overestimates the exact top probability by
        4.000366e-13 within an absolute 1e-18 tolerance, the overlap mass
        of the shared pumps in the cut sets."""
        q_re = ftq.rare_event_probability(CUT_SETS, PROBS)
        q_ie = ftq.exact_top_probability(CUT_SETS, PROBS)
        self.assertAlmostEqual(q_re - q_ie, 4.000366e-13, delta=1e-18)
        self.assertLess(q_ie, q_re)

    def test_exact_ie_disjoint_pair_union_identity(self):
        """Steps 3 and 4 on disjoint single-event cuts {P-A} at 2e-4 and
        {P-B} at 3e-4 coincide at the exact union a + b - a*b = 4.9994e-4
        within 1e-12 relative: the min-cut upper bound and the
        inclusion-exclusion result are identical for disjoint cuts."""
        q_ep = ftq.min_cut_upper_bound(
            [{"P-A"}, {"P-B"}], {"P-A": 2.0e-4, "P-B": 3.0e-4}
        )
        q_ie = ftq.exact_top_probability(
            [{"P-A"}, {"P-B"}], {"P-A": 2.0e-4, "P-B": 3.0e-4}
        )
        expected = 2.0e-4 + 3.0e-4 - 2.0e-4 * 3.0e-4
        self.assertTrue(math.isclose(q_ie, 4.9994e-4, rel_tol=1e-12))
        self.assertTrue(math.isclose(q_ep, q_ie, rel_tol=1e-12))
        self.assertTrue(math.isclose(q_ie, expected, rel_tol=1e-12))

    def test_exact_ie_guard_13_cuts_raises(self):
        """Step 4 guard: at 13 cut sets, above EXACT_IE_MAX_CUT_SETS = 12,
        the exact pass raises ValueError with a message naming the max 12
        and steering the caller to the step 2 rare-event or step 3
        min-cut bound fallbacks."""
        cut_sets = [{"E%d" % i} for i in range(13)]
        probs = {"E%d" % i: 1.0e-3 for i in range(13)}
        with self.assertRaises(ValueError) as ctx:
            ftq.exact_top_probability(cut_sets, probs)
        self.assertIn("max 12", str(ctx.exception))

    def test_exact_ie_12_disjoint_closed_form(self):
        """Step 4 at the acceptance boundary: 12 single-event disjoint
        cuts at 1e-6 each give Q_ie matching the closed form
        1 - (1 - 1e-6)**12 within 1e-9 relative (alternating-sum rounding
        grows with the 4095-term count, anchored at about 3e-11)."""
        cut_sets = [{"E%d" % i} for i in range(12)]
        probs = {"E%d" % i: 1.0e-6 for i in range(12)}
        q_ie = ftq.exact_top_probability(cut_sets, probs)
        closed = 1.0 - (1.0 - 1.0e-6) ** 12
        self.assertTrue(math.isclose(q_ie, closed, rel_tol=1e-9))


class TruncationTests(unittest.TestCase):
    """Workflow step 5: truncate the cut-set list below an analyst
    probability threshold and report the retained probability share."""

    def test_truncate_keeps_four_at_1e9(self):
        """Step 5 at threshold 1e-9 on the worked tree keeps the 4 cuts
        {P-A,P-B}, {P-A,RSV}, {P-B,RSV}, {V-A,V-B} in input order and
        drops only the {C-A,C-B} cut at 1e-10, with retained probability
        share 0.9939759036144578 within 1e-15."""
        result = ftq.truncate_cut_sets(CUT_SETS, PROBS, 1e-9)
        kept_names = [frozenset(cs) for cs in result["cut_sets"]]
        self.assertEqual(
            kept_names,
            [
                frozenset({"P-A", "P-B"}),
                frozenset({"P-A", "RSV"}),
                frozenset({"P-B", "RSV"}),
                frozenset({"V-A", "V-B"}),
            ],
        )
        self.assertAlmostEqual(
            result["retained_probability_share"], 0.9939759036144578,
            delta=1e-15,
        )

    def test_truncate_dominant_cut_at_6e9(self):
        """Step 5 at threshold 6e-9 on the worked tree keeps only the
        dominant {P-A,P-B} cut at 1e-8, share 0.6024096385542169 within
        1e-15: the both-pumps cut alone carries 60.24 percent of the
        failure mass."""
        result = ftq.truncate_cut_sets(CUT_SETS, PROBS, 6e-9)
        kept_names = [frozenset(cs) for cs in result["cut_sets"]]
        self.assertEqual(kept_names, [frozenset({"P-A", "P-B"})])
        self.assertAlmostEqual(
            result["retained_probability_share"], 0.6024096385542169,
            delta=1e-15,
        )

    def test_truncate_keeps_cut_equal_to_threshold(self):
        """Step 5 boundary semantics: a cut set whose probability equals
        the threshold is kept (drop is strict below the threshold), so at
        threshold 2e-9 both the {P-A,RSV} and {P-B,RSV} cuts at exactly
        2e-9 stay and only the 1e-10 computer cut leaves."""
        result = ftq.truncate_cut_sets(CUT_SETS, PROBS, 2e-9)
        kept_names = [frozenset(cs) for cs in result["cut_sets"]]
        self.assertIn(frozenset({"P-A", "RSV"}), kept_names)
        self.assertIn(frozenset({"P-B", "RSV"}), kept_names)
        self.assertNotIn(frozenset({"C-A", "C-B"}), kept_names)
        self.assertAlmostEqual(
            result["retained_probability_share"], 0.9939759036144578,
            delta=1e-15,
        )

    def test_truncate_threshold_one_drops_all(self):
        """Step 5 at threshold 1.0 drops every cut (all probabilities are
        below one): an empty retained list and share 0.0."""
        result = ftq.truncate_cut_sets(CUT_SETS, PROBS, 1.0)
        self.assertEqual(result["cut_sets"], [])
        self.assertAlmostEqual(result["retained_probability_share"], 0.0,
                               delta=1e-15)

    def test_truncate_tiny_threshold_keeps_all(self):
        """Step 5 at threshold 1e-12 drops nothing: the full input list
        returns in input order with retained probability share 1.0 within
        1e-15."""
        result = ftq.truncate_cut_sets(CUT_SETS, PROBS, 1e-12)
        kept_names = [frozenset(cs) for cs in result["cut_sets"]]
        self.assertEqual(
            kept_names,
            [
                frozenset({"P-A", "P-B"}),
                frozenset({"P-A", "RSV"}),
                frozenset({"P-B", "RSV"}),
                frozenset({"V-A", "V-B"}),
                frozenset({"C-A", "C-B"}),
            ],
        )
        self.assertAlmostEqual(result["retained_probability_share"], 1.0,
                               delta=1e-15)

    def test_truncate_returns_exact_keys(self):
        """Step 5 returns a dict with exactly the keys cut_sets and
        retained_probability_share."""
        result = ftq.truncate_cut_sets(CUT_SETS, PROBS, 1e-9)
        self.assertEqual(sorted(result.keys()),
                         ["cut_sets", "retained_probability_share"])


class RankingTests(unittest.TestCase):
    """Workflow step 6: rank the retained cut sets by per-cut-set
    probability share, descending with input-order tie-break."""

    def test_rank_worked_order(self):
        """Step 6 on the worked tree orders the cut sets by descending
        probability: {P-A,P-B} first, {V-A,V-B} second, the tied 2e-9
        pump-reservoir cuts next in input order, and {C-A,C-B} last."""
        ranked = ftq.rank_cut_sets(CUT_SETS, PROBS)
        order = [frozenset(entry["cut_set"]) for entry in ranked]
        self.assertEqual(
            order,
            [
                frozenset({"P-A", "P-B"}),
                frozenset({"V-A", "V-B"}),
                frozenset({"P-A", "RSV"}),
                frozenset({"P-B", "RSV"}),
                frozenset({"C-A", "C-B"}),
            ],
        )

    def test_rank_worked_shares(self):
        """Step 6 shares on the worked tree: the both-pumps cut carries
        0.6024096385542169 of the mass, the valve cut 0.15060240963855423,
        each tied pump-reservoir cut 0.12048192771084339, and the computer
        cut 0.00602409638554217, each within 1e-12 relative."""
        ranked = ftq.rank_cut_sets(CUT_SETS, PROBS)
        by_cut = {frozenset(entry["cut_set"]): entry["share"]
                  for entry in ranked}
        self.assertTrue(math.isclose(
            by_cut[frozenset({"P-A", "P-B"})], 0.6024096385542169,
            rel_tol=1e-12))
        self.assertTrue(math.isclose(
            by_cut[frozenset({"V-A", "V-B"})], 0.15060240963855423,
            rel_tol=1e-12))
        self.assertTrue(math.isclose(
            by_cut[frozenset({"P-A", "RSV"})], 0.12048192771084339,
            rel_tol=1e-12))
        self.assertTrue(math.isclose(
            by_cut[frozenset({"P-B", "RSV"})], 0.12048192771084339,
            rel_tol=1e-12))
        self.assertTrue(math.isclose(
            by_cut[frozenset({"C-A", "C-B"})], 0.00602409638554217,
            rel_tol=1e-12))

    def test_rank_shares_sum_to_one(self):
        """Step 6 share conservation: the ranking shares sum to 1.0 within
        1e-12, so the dominant-combination readout never loses mass."""
        ranked = ftq.rank_cut_sets(CUT_SETS, PROBS)
        total = sum(entry["share"] for entry in ranked)
        self.assertTrue(math.isclose(total, 1.0, rel_tol=1e-12))

    def test_rank_tie_keeps_input_order(self):
        """Step 6 tie-break: the tied 2e-9 cuts {P-A,RSV} (input position
        2) and {P-B,RSV} (input position 3) keep their input order in the
        descending sort, a stable tie-break for determinism."""
        ranked = ftq.rank_cut_sets(CUT_SETS, PROBS)
        third = frozenset(ranked[2]["cut_set"])
        fourth = frozenset(ranked[3]["cut_set"])
        self.assertEqual(third, frozenset({"P-A", "RSV"}))
        self.assertEqual(fourth, frozenset({"P-B", "RSV"}))

    def test_rank_returns_exact_keys(self):
        """Step 6 entries carry exactly the keys cut_set, probability and
        share."""
        ranked = ftq.rank_cut_sets(CUT_SETS, PROBS)
        for entry in ranked:
            self.assertEqual(sorted(entry.keys()),
                             ["cut_set", "probability", "share"])


class InputRejectionTests(unittest.TestCase):
    """Workflow step 1 input validation: non-physical analysis inputs are
    rejected before any pass of the SKILL.md workflow runs."""

    def test_empty_cut_sets_raise_all_entry_points(self):
        """Step 1 rejects an empty cut-set list from every entry point of
        the quantification workflow."""
        for func in (ftq.rare_event_probability, ftq.min_cut_upper_bound,
                     ftq.exact_top_probability):
            with self.assertRaises(ValueError):
                func([], {"A": 1.0e-3})
        with self.assertRaises(ValueError):
            ftq.truncate_cut_sets([], {"A": 1.0e-3}, 1e-4)
        with self.assertRaises(ValueError):
            ftq.rank_cut_sets([], {"A": 1.0e-3})

    def test_empty_cut_set_entry_raises(self):
        """Step 1 rejects an empty cut-set entry in the gathered list."""
        for func in (ftq.rare_event_probability, ftq.min_cut_upper_bound,
                     ftq.exact_top_probability):
            with self.assertRaises(ValueError):
                func([set()], {"A": 1.0e-3})
        with self.assertRaises(ValueError):
            ftq.truncate_cut_sets([set()], {"A": 1.0e-3}, 1e-4)
        with self.assertRaises(ValueError):
            ftq.rank_cut_sets([set()], {"A": 1.0e-3})

    def test_missing_probability_entry_raises(self):
        """Step 1 rejects a basic event that has no probability entry in
        the probs dict."""
        for func in (ftq.rare_event_probability, ftq.min_cut_upper_bound,
                     ftq.exact_top_probability):
            with self.assertRaises(ValueError):
                func([{"A", "B"}], {"A": 1.0e-3})

    def test_probability_above_one_raises(self):
        """Step 1 rejects a probability of 1.5: probs must lie strictly
        inside (0, 1)."""
        for func in (ftq.rare_event_probability, ftq.min_cut_upper_bound,
                     ftq.exact_top_probability):
            with self.assertRaises(ValueError):
                func([{"A"}], {"A": 1.5})

    def test_probability_zero_raises(self):
        """Step 1 rejects a probability of 0.0, which would silently zero
        every cut set that contains the event."""
        for func in (ftq.rare_event_probability, ftq.min_cut_upper_bound,
                     ftq.exact_top_probability):
            with self.assertRaises(ValueError):
                func([{"A"}], {"A": 0.0})

    def test_threshold_above_one_raises(self):
        """Step 5 rejects a truncation threshold of 1.5: threshold must
        lie in (0, 1]."""
        with self.assertRaises(ValueError):
            ftq.truncate_cut_sets(CUT_SETS, PROBS, 1.5)

    def test_threshold_zero_raises(self):
        """Step 5 rejects a truncation threshold of 0.0, which would keep
        every cut set regardless of probability."""
        with self.assertRaises(ValueError):
            ftq.truncate_cut_sets(CUT_SETS, PROBS, 0.0)


class DeterminismTests(unittest.TestCase):
    """Workflow step 8: the deterministic contract confirms two calls
    return equal structures and the ranking tie-break is stable."""

    def test_two_calls_return_equal_structures(self):
        """Step 8 determinism: repeated rare-event, min-cut bound, exact
        inclusion-exclusion and truncation calls on the worked tree
        return bit-identical structures."""
        self.assertEqual(
            ftq.rare_event_probability(CUT_SETS, PROBS),
            ftq.rare_event_probability(CUT_SETS, PROBS),
        )
        self.assertEqual(
            ftq.min_cut_upper_bound(CUT_SETS, PROBS),
            ftq.min_cut_upper_bound(CUT_SETS, PROBS),
        )
        self.assertEqual(
            ftq.exact_top_probability(CUT_SETS, PROBS),
            ftq.exact_top_probability(CUT_SETS, PROBS),
        )
        self.assertEqual(
            ftq.truncate_cut_sets(CUT_SETS, PROBS, 1e-9),
            ftq.truncate_cut_sets(CUT_SETS, PROBS, 1e-9),
        )

    def test_rank_stable_across_calls(self):
        """Step 8 tie stability: the worked-tree ranking is identical
        across two calls, so the tied pump-reservoir cuts never swap."""
        first = [frozenset(entry["cut_set"])
                 for entry in ftq.rank_cut_sets(CUT_SETS, PROBS)]
        second = [frozenset(entry["cut_set"])
                  for entry in ftq.rank_cut_sets(CUT_SETS, PROBS)]
        self.assertEqual(first, second)


if __name__ == "__main__":
    unittest.main()
