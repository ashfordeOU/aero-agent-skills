"""Contract test for fault_tree_importance_measures_logic.py (wave-38).

Deterministic, offline, stdlib unittest. Run from the repo root:

    python3 skills/systems-engineering-safety/arp4761a/fault-tree-importance-measures/scripts/test_fault_tree_importance_measures.py

Anchor tree (spec worked example): cut_sets = [{"A", "B"}, {"C"}],
probs = {"A": 0.01, "B": 0.02, "C": 0.03}; Q = 0.030194, C dominates.
Assert targets are the real module outputs, inside the spec magnitude
bounds, plus ValueError rejection of non-physical inputs.
"""

import math
import os
import sys
import unittest

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import fault_tree_importance_measures_logic as ftim

CUT_SETS = [{"A", "B"}, {"C"}]
PROBS = {"A": 0.01, "B": 0.02, "C": 0.03}


class TopEventProbabilityTests(unittest.TestCase):
    def test_top_probability_two_cut_set_anchor(self):
        self.assertAlmostEqual(
            ftim.top_event_probability(CUT_SETS, PROBS), 0.030194, places=6
        )

    def test_top_probability_single_cut_set_equals_event_probability(self):
        self.assertAlmostEqual(
            ftim.top_event_probability([{"A"}], {"A": 0.25}), 0.25, places=12
        )

    def test_top_probability_three_independent_cut_sets_closed_form(self):
        cut_sets = [{"A"}, {"B"}, {"C"}]
        probs = {"A": 0.1, "B": 0.2, "C": 0.3}
        expected = 1.0 - 0.9 * 0.8 * 0.7
        self.assertAlmostEqual(
            ftim.top_event_probability(cut_sets, probs), expected, places=12
        )

    def test_top_probability_four_cut_sets_mask_loop(self):
        cut_sets = [{"A"}, {"B"}, {"C"}, {"D"}]
        probs = {"A": 0.1, "B": 0.2, "C": 0.3, "D": 0.1}
        expected = 1.0 - 0.9 * 0.8 * 0.7 * 0.9
        self.assertAlmostEqual(
            ftim.top_event_probability(cut_sets, probs), expected, places=12
        )

    def test_top_probability_union_of_overlapping_cut_sets(self):
        cut_sets = [{"A", "B"}, {"B", "C"}]
        probs = {"A": 0.1, "B": 0.2, "C": 0.3}
        expected = 0.02 + 0.06 - 0.02 * 0.06
        self.assertAlmostEqual(
            ftim.top_event_probability(cut_sets, probs), expected, places=12
        )

    def test_top_probability_empty_cut_sets_raises(self):
        with self.assertRaises(ValueError):
            ftim.top_event_probability([], PROBS)
        with self.assertRaises(ValueError):
            ftim.top_event_probability([set(), {"C"}], PROBS)

    def test_top_probability_unknown_event_raises(self):
        with self.assertRaises(ValueError):
            ftim.top_event_probability([{"A", "Z"}], PROBS)

    def test_top_probability_probability_outside_open_unit_interval_raises(self):
        for bad_prob in (0.0, 1.0, -0.1, 1.5):
            bad_probs = dict(PROBS)
            bad_probs["C"] = bad_prob
            with self.assertRaises(ValueError):
                ftim.top_event_probability(CUT_SETS, bad_probs)


class BirnbaumTests(unittest.TestCase):
    def test_birnbaum_anchor_values(self):
        self.assertAlmostEqual(
            ftim.birnbaum_measure(CUT_SETS, PROBS, "C"), 0.9998, places=4
        )
        self.assertAlmostEqual(
            ftim.birnbaum_measure(CUT_SETS, PROBS, "A"), 0.0194, places=4
        )
        self.assertAlmostEqual(
            ftim.birnbaum_measure(CUT_SETS, PROBS, "B"), 0.0097, places=4
        )

    def test_birnbaum_half_probability_only_cut_set_is_one(self):
        self.assertAlmostEqual(
            ftim.birnbaum_measure([{"A"}], {"A": 0.5}, "A"), 1.0, places=12
        )

    def test_birnbaum_rejects_unknown_or_non_contributing_event(self):
        with self.assertRaises(ValueError):
            ftim.birnbaum_measure(CUT_SETS, PROBS, "Z")
        probs = {"A": 0.5, "X": 0.2}
        with self.assertRaises(ValueError):
            ftim.birnbaum_measure([{"A"}], probs, "X")


class FussellVeselyTests(unittest.TestCase):
    def test_fussell_vesely_anchor_values(self):
        self.assertAlmostEqual(
            ftim.fussell_vesely_measure(CUT_SETS, PROBS, "C"), 0.9934, places=4
        )
        self.assertAlmostEqual(
            ftim.fussell_vesely_measure(CUT_SETS, PROBS, "A"), 0.006425, places=6
        )
        self.assertAlmostEqual(
            ftim.fussell_vesely_measure(CUT_SETS, PROBS, "B"), 0.006425, places=6
        )

    def test_fussell_vesely_at_most_one_for_anchor_events(self):
        for event in ("A", "B", "C"):
            value = ftim.fussell_vesely_measure(CUT_SETS, PROBS, event)
            self.assertLessEqual(value, 1.0)
            self.assertGreaterEqual(value, 0.0)

    def test_fussell_vesely_single_event_only_cut_set_is_one(self):
        self.assertAlmostEqual(
            ftim.fussell_vesely_measure([{"A"}], {"A": 0.5}, "A"), 1.0, places=12
        )


class RawRrwTests(unittest.TestCase):
    def test_risk_achievement_worth_anchor_values(self):
        self.assertAlmostEqual(
            ftim.risk_achievement_worth(CUT_SETS, PROBS, "A"), 1.6361, places=4
        )
        self.assertAlmostEqual(
            ftim.risk_achievement_worth(CUT_SETS, PROBS, "B"), 1.3148, places=4
        )
        self.assertAlmostEqual(
            ftim.risk_achievement_worth(CUT_SETS, PROBS, "C"), 33.1192, places=4
        )

    def test_risk_reduction_worth_anchor_values(self):
        self.assertAlmostEqual(
            ftim.risk_reduction_worth(CUT_SETS, PROBS, "A"), 1.00647, places=5
        )
        self.assertAlmostEqual(
            ftim.risk_reduction_worth(CUT_SETS, PROBS, "B"), 1.00647, places=5
        )
        self.assertAlmostEqual(
            ftim.risk_reduction_worth(CUT_SETS, PROBS, "C"), 150.97, places=2
        )

    def test_closed_form_identities_link_all_four_measures(self):
        top = ftim.top_event_probability(CUT_SETS, PROBS)
        for event in ("A", "B", "C"):
            birnbaum = ftim.birnbaum_measure(CUT_SETS, PROBS, event)
            fv = ftim.fussell_vesely_measure(CUT_SETS, PROBS, event)
            raw = ftim.risk_achievement_worth(CUT_SETS, PROBS, event)
            rrw = ftim.risk_reduction_worth(CUT_SETS, PROBS, event)
            self.assertAlmostEqual(fv, 1.0 - 1.0 / rrw, places=10)
            self.assertAlmostEqual(raw, birnbaum / top + 1.0 / rrw, places=10)

    def test_raw_and_rrw_at_least_one_for_contributing_events(self):
        for event in ("A", "B", "C"):
            self.assertGreaterEqual(
                ftim.risk_achievement_worth(CUT_SETS, PROBS, event), 1.0
            )
            self.assertGreaterEqual(
                ftim.risk_reduction_worth(CUT_SETS, PROBS, event), 1.0
            )

    def test_lone_single_event_cut_set_identities(self):
        cut_sets = [{"A"}]
        probs = {"A": 0.5}
        top = ftim.top_event_probability(cut_sets, probs)
        self.assertAlmostEqual(top, 0.5, places=12)
        self.assertAlmostEqual(
            ftim.risk_achievement_worth(cut_sets, probs, "A"), 1.0 / top, places=12
        )
        self.assertTrue(math.isinf(ftim.risk_reduction_worth(cut_sets, probs, "A")))

    def test_ordering_q1_geq_q_geq_q0(self):
        top = ftim.top_event_probability(CUT_SETS, PROBS)
        for event in ("A", "B", "C"):
            q1 = ftim.risk_achievement_worth(CUT_SETS, PROBS, event) * top
            q0 = top / ftim.risk_reduction_worth(CUT_SETS, PROBS, event)
            self.assertGreaterEqual(q1, top)
            self.assertGreaterEqual(top, q0)

    def test_measure_functions_non_negative(self):
        for event in ("A", "B", "C"):
            self.assertGreaterEqual(
                ftim.birnbaum_measure(CUT_SETS, PROBS, event), 0.0
            )
            self.assertGreaterEqual(
                ftim.fussell_vesely_measure(CUT_SETS, PROBS, event), 0.0
            )
            self.assertGreaterEqual(
                ftim.risk_achievement_worth(CUT_SETS, PROBS, event), 0.0
            )
            self.assertGreaterEqual(
                ftim.risk_reduction_worth(CUT_SETS, PROBS, event), 0.0
            )

    def test_measure_functions_reject_unknown_or_non_contributing_event(self):
        for fn in (
            ftim.fussell_vesely_measure,
            ftim.risk_achievement_worth,
            ftim.risk_reduction_worth,
        ):
            with self.assertRaises(ValueError):
                fn(CUT_SETS, PROBS, "Z")
        probs = {"A": 0.5, "X": 0.2}
        for fn in (
            ftim.fussell_vesely_measure,
            ftim.risk_achievement_worth,
            ftim.risk_reduction_worth,
        ):
            with self.assertRaises(ValueError):
                fn([{"A"}], probs, "X")


class ImportanceMeasuresDictTests(unittest.TestCase):
    def test_importance_measures_dict_keys_exact(self):
        measures = ftim.importance_measures(CUT_SETS, PROBS)
        self.assertEqual(sorted(measures), ["A", "B", "C"])
        for event in ("A", "B", "C"):
            self.assertEqual(
                set(measures[event]), {"birnbaum", "fussell_vesely", "raw", "rrw"}
            )

    def test_importance_measures_consistent_with_single_functions(self):
        measures = ftim.importance_measures(CUT_SETS, PROBS)
        for event in ("A", "B", "C"):
            self.assertAlmostEqual(
                measures[event]["birnbaum"],
                ftim.birnbaum_measure(CUT_SETS, PROBS, event),
                places=12,
            )
            self.assertAlmostEqual(
                measures[event]["fussell_vesely"],
                ftim.fussell_vesely_measure(CUT_SETS, PROBS, event),
                places=12,
            )
            self.assertAlmostEqual(
                measures[event]["raw"],
                ftim.risk_achievement_worth(CUT_SETS, PROBS, event),
                places=12,
            )
            self.assertAlmostEqual(
                measures[event]["rrw"],
                ftim.risk_reduction_worth(CUT_SETS, PROBS, event),
                places=12,
            )

    def test_importance_measures_deterministic(self):
        self.assertEqual(
            ftim.importance_measures(CUT_SETS, PROBS),
            ftim.importance_measures(CUT_SETS, PROBS),
        )


class RankTests(unittest.TestCase):
    def test_rank_events_fussell_vesely_anchor_order(self):
        ranked = ftim.rank_events(CUT_SETS, PROBS, "fussell_vesely")
        self.assertEqual([event for event, _ in ranked], ["C", "A", "B"])
        self.assertAlmostEqual(ranked[0][1], 0.9934, places=4)

    def test_rank_events_tie_break_alphabetical(self):
        ranked = ftim.rank_events(CUT_SETS, PROBS, "fussell_vesely")
        self.assertEqual(ranked[1][0], "A")
        self.assertEqual(ranked[2][0], "B")
        self.assertAlmostEqual(ranked[1][1], ranked[2][1], places=12)

    def test_rank_events_by_birnbaum_descending(self):
        ranked = ftim.rank_events(CUT_SETS, PROBS, "birnbaum")
        values = [value for _, value in ranked]
        self.assertEqual(values, sorted(values, reverse=True))

    def test_rank_events_default_measure_is_fussell_vesely(self):
        explicit = ftim.rank_events(CUT_SETS, PROBS, "fussell_vesely")
        defaulted = ftim.rank_events(CUT_SETS, PROBS)
        self.assertEqual(explicit, defaulted)

    def test_rank_events_unknown_measure_raises(self):
        with self.assertRaises(ValueError):
            ftim.rank_events(CUT_SETS, PROBS, "minimal-cut-set")

    def test_rank_order_by_fv_equals_rank_by_raw_anchor(self):
        by_fv = [
            event
            for event, _ in ftim.rank_events(CUT_SETS, PROBS, "fussell_vesely")
        ]
        by_raw = [event for event, _ in ftim.rank_events(CUT_SETS, PROBS, "raw")]
        self.assertEqual(by_fv, by_raw)
        self.assertEqual(by_raw, ["C", "A", "B"])

    def test_rank_events_deterministic_across_calls(self):
        self.assertEqual(
            ftim.rank_events(CUT_SETS, PROBS, "rrw"),
            ftim.rank_events(CUT_SETS, PROBS, "rrw"),
        )


class DominantContributorsTests(unittest.TestCase):
    def test_dominant_contributors_anchor(self):
        self.assertEqual(ftim.dominant_contributors(CUT_SETS, PROBS), ["C"])

    def test_dominant_contributors_strict_at_threshold(self):
        cut_sets = [{"A"}]
        probs = {"A": 0.5}
        self.assertEqual(
            ftim.dominant_contributors(cut_sets, probs, threshold=1.0), []
        )
        self.assertEqual(
            ftim.dominant_contributors(cut_sets, probs, threshold=0.99), ["A"]
        )

    def test_dominant_contributors_invalid_inputs_raise(self):
        with self.assertRaises(ValueError):
            ftim.dominant_contributors([], PROBS)
        for bad_prob in (0.0, 1.0):
            bad_probs = dict(PROBS)
            bad_probs["C"] = bad_prob
            with self.assertRaises(ValueError):
                ftim.dominant_contributors(CUT_SETS, bad_probs)


if __name__ == "__main__":
    unittest.main()
