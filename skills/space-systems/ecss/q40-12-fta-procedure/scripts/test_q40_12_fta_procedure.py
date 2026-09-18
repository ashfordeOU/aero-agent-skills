#!/usr/bin/env python3
"""Contract test for the adopted fault tree analysis procedure (offline)."""

import copy
import unittest

from q40_12_fta_procedure_logic import (
    GATE_TYPES,
    IMPORTANCE_MEASURES,
    QUANTIFICATION_METHODS,
    TARGET_MET,
    TARGET_NOT_DECLARED,
    TARGET_NOT_MET,
    birnbaum_importance,
    criticality_importance,
    cut_set_order_profile,
    cut_set_probability,
    fta_report,
    fussell_vesely_importance,
    minimal_cut_sets,
    rank_importance,
    sensitivity_sweep,
    single_point_failures,
    top_event_probability,
    unreachable_gates,
    validate_tree,
)

TREE = {
    "top": "T",
    "gates": {
        "T": {"type": "OR", "inputs": ["G1", "b3"]},
        "G1": {"type": "AND", "inputs": ["b1", "b2"]},
    },
    "basic_events": {"b1": 0.1, "b2": 0.2, "b3": 0.05},
}

VOTING_TREE = {
    "top": "K",
    "gates": {"K": {"type": "KOFN", "inputs": ["b1", "b2", "b3"], "k": 2}},
    "basic_events": {"b1": 0.1, "b2": 0.2, "b3": 0.05},
}

SINGLE_CUT_SET_TREE = {
    "top": "S",
    "gates": {"S": {"type": "AND", "inputs": ["b1", "b2"]}},
    "basic_events": {"b1": 0.1, "b2": 0.2},
}


def _tree(base, **overrides):
    tree = copy.deepcopy(base)
    tree.update(overrides)
    return tree


class ConstructionTests(unittest.TestCase):
    def test_a_well_formed_tree_validates(self):
        self.assertEqual(validate_tree(TREE)["top"], "T")

    def test_a_non_mapping_tree_is_rejected(self):
        with self.assertRaises(ValueError):
            validate_tree("T = b1 AND b2")

    def test_a_top_event_that_is_not_a_gate_is_rejected(self):
        with self.assertRaises(ValueError):
            validate_tree(_tree(TREE, top="b1"))

    def test_an_unknown_gate_type_is_rejected(self):
        broken = copy.deepcopy(TREE)
        broken["gates"]["T"]["type"] = "NOT"
        with self.assertRaises(ValueError):
            validate_tree(broken)

    def test_a_gate_with_one_input_is_rejected(self):
        broken = copy.deepcopy(TREE)
        broken["gates"]["T"]["inputs"] = ["G1"]
        with self.assertRaises(ValueError):
            validate_tree(broken)

    def test_a_dangling_input_is_rejected(self):
        broken = copy.deepcopy(TREE)
        broken["gates"]["G1"]["inputs"] = ["b1", "b9"]
        with self.assertRaises(ValueError):
            validate_tree(broken)

    def test_a_cycle_is_rejected(self):
        broken = copy.deepcopy(TREE)
        broken["gates"]["G1"]["inputs"] = ["b1", "T"]
        with self.assertRaises(ValueError):
            validate_tree(broken)

    def test_a_probability_outside_the_unit_interval_is_rejected(self):
        broken = copy.deepcopy(TREE)
        broken["basic_events"]["b1"] = 1.4
        with self.assertRaises(ValueError):
            validate_tree(broken)

    def test_a_voting_gate_needs_k_within_range(self):
        broken = copy.deepcopy(VOTING_TREE)
        broken["gates"]["K"]["k"] = 4
        with self.assertRaises(ValueError):
            validate_tree(broken)

    def test_an_identifier_used_twice_is_rejected(self):
        broken = copy.deepcopy(TREE)
        broken["basic_events"]["G1"] = 0.01
        with self.assertRaises(ValueError):
            validate_tree(broken)

    def test_every_declared_gate_type_is_coherent(self):
        self.assertEqual(GATE_TYPES, ("AND", "OR", "KOFN"))

    def test_an_undeveloped_gate_is_reported(self):
        drifted = copy.deepcopy(TREE)
        drifted["gates"]["G9"] = {"type": "AND", "inputs": ["b1", "b3"]}
        self.assertEqual(unreachable_gates(drifted), ("G9",))


class CutSetTests(unittest.TestCase):
    def test_the_tree_expands_to_its_minimal_cut_sets(self):
        self.assertEqual(minimal_cut_sets(TREE), (("b3",), ("b1", "b2")))

    def test_a_voting_gate_expands_to_every_k_subset(self):
        self.assertEqual(
            minimal_cut_sets(VOTING_TREE),
            (("b1", "b2"), ("b1", "b3"), ("b2", "b3")),
        )

    def test_a_superset_cut_set_is_removed(self):
        redundant = {
            "top": "T",
            "gates": {
                "T": {"type": "OR", "inputs": ["b1", "G1"]},
                "G1": {"type": "AND", "inputs": ["b1", "b2"]},
            },
            "basic_events": {"b1": 0.1, "b2": 0.2},
        }
        self.assertEqual(minimal_cut_sets(redundant), (("b1",),))

    def test_the_order_profile_counts_each_order(self):
        self.assertEqual(cut_set_order_profile(minimal_cut_sets(TREE)), {1: 1, 2: 1})

    def test_order_one_cut_sets_are_single_point_failures(self):
        self.assertEqual(single_point_failures(minimal_cut_sets(TREE)), ("b3",))

    def test_a_tree_with_no_order_one_cut_set_has_no_single_point_failure(self):
        self.assertEqual(single_point_failures(minimal_cut_sets(VOTING_TREE)), ())

    def test_an_empty_cut_set_is_rejected(self):
        with self.assertRaises(ValueError):
            cut_set_order_profile([()])

    def test_a_cut_set_probability_is_the_product_of_its_events(self):
        self.assertAlmostEqual(
            cut_set_probability(("b1", "b2"), TREE["basic_events"]), 0.02, places=12
        )

    def test_a_cut_set_naming_an_unknown_event_is_rejected(self):
        with self.assertRaises(ValueError):
            cut_set_probability(("b1", "b9"), TREE["basic_events"])


class QuantificationTests(unittest.TestCase):
    def test_the_exact_top_event_probability_is_inclusion_exclusion(self):
        self.assertAlmostEqual(
            top_event_probability(TREE, "exact"), 0.069, places=12
        )

    def test_the_rare_event_approximation_omits_the_overlap_term(self):
        self.assertAlmostEqual(
            top_event_probability(TREE, "rare-event"), 0.07, places=12
        )

    def test_the_min_cut_upper_bound_matches_the_exact_value_here(self):
        self.assertAlmostEqual(
            top_event_probability(TREE, "min-cut-upper-bound"),
            top_event_probability(TREE, "exact"),
            places=12,
        )

    def test_the_rare_event_value_is_conservative_against_the_exact_value(self):
        rare = top_event_probability(TREE, "rare-event")
        exact = top_event_probability(TREE, "exact")
        self.assertGreater(rare - exact, 1e-6)

    def test_one_cut_set_makes_every_method_agree(self):
        values = [
            top_event_probability(SINGLE_CUT_SET_TREE, method)
            for method in QUANTIFICATION_METHODS
        ]
        for value in values:
            self.assertAlmostEqual(value, 0.02, places=12)

    def test_an_unknown_method_is_rejected(self):
        with self.assertRaises(ValueError):
            top_event_probability(TREE, "monte-carlo")

    def test_a_certain_basic_event_drives_the_top_event_to_one(self):
        certain = copy.deepcopy(TREE)
        certain["basic_events"]["b3"] = 1.0
        self.assertAlmostEqual(
            top_event_probability(certain, "exact"), 1.0, places=12
        )


class ImportanceTests(unittest.TestCase):
    def test_birnbaum_is_the_swing_between_the_event_states(self):
        self.assertAlmostEqual(
            birnbaum_importance(TREE, "b3"), 0.98, places=12
        )

    def test_fussell_vesely_is_the_share_of_the_top_event(self):
        self.assertAlmostEqual(
            fussell_vesely_importance(TREE, "b3"), 0.05 / 0.069, places=9
        )

    def test_criticality_weights_birnbaum_by_the_event_probability(self):
        self.assertAlmostEqual(
            criticality_importance(TREE, "b3"),
            birnbaum_importance(TREE, "b3") * 0.05 / top_event_probability(TREE),
            places=12,
        )

    def test_the_single_point_failure_ranks_first(self):
        ranked = rank_importance(TREE, "fussell-vesely")
        self.assertEqual(ranked[0][0], "b3")

    def test_every_measure_ranks_every_basic_event(self):
        for measure in IMPORTANCE_MEASURES:
            self.assertEqual(len(rank_importance(TREE, measure)), 3)

    def test_an_unknown_measure_is_rejected(self):
        with self.assertRaises(ValueError):
            rank_importance(TREE, "risk-reduction-worth")

    def test_an_unknown_event_is_rejected(self):
        with self.assertRaises(ValueError):
            birnbaum_importance(TREE, "b9")

    def test_a_zero_probability_tree_has_no_defined_importance(self):
        dead = copy.deepcopy(TREE)
        dead["basic_events"] = {"b1": 0.0, "b2": 0.0, "b3": 0.0}
        with self.assertRaises(ValueError):
            fussell_vesely_importance(dead, "b3")


class SensitivityTests(unittest.TestCase):
    def test_a_unit_factor_reproduces_the_baseline(self):
        swept = sensitivity_sweep(TREE, "b3", (1.0,))
        self.assertAlmostEqual(swept[0]["ratio_to_baseline"], 1.0, places=12)

    def test_raising_the_event_raises_the_top_event(self):
        swept = sensitivity_sweep(TREE, "b3", (1.0, 10.0))
        self.assertGreater(
            swept[1]["top_event_probability"] - swept[0]["top_event_probability"],
            1e-6,
        )

    def test_a_factor_is_clipped_at_certainty(self):
        swept = sensitivity_sweep(TREE, "b3", (100.0,))
        self.assertAlmostEqual(swept[0]["event_probability"], 1.0, places=12)

    def test_a_non_positive_factor_is_rejected(self):
        with self.assertRaises(ValueError):
            sensitivity_sweep(TREE, "b3", (0.0,))

    def test_an_empty_factor_list_is_rejected(self):
        with self.assertRaises(ValueError):
            sensitivity_sweep(TREE, "b3", ())


class ReportTests(unittest.TestCase):
    def test_the_report_carries_the_cut_sets_and_every_method(self):
        report = fta_report(TREE)
        self.assertEqual(report["cut_set_count"], 2)
        for method in QUANTIFICATION_METHODS:
            self.assertIsNotNone(report["probabilities"][method])

    def test_a_target_exactly_on_the_quantified_value_is_met(self):
        report = fta_report(TREE, target_probability=0.069)
        self.assertEqual(report["verdict"], TARGET_MET)

    def test_a_target_below_the_quantified_value_is_not_met(self):
        report = fta_report(TREE, target_probability=1.0e-4)
        self.assertEqual(report["verdict"], TARGET_NOT_MET)

    def test_no_target_leaves_the_verdict_open(self):
        self.assertEqual(fta_report(TREE)["verdict"], TARGET_NOT_DECLARED)

    def test_the_report_names_the_single_point_failure(self):
        report = fta_report(TREE)
        self.assertTrue(any("single point failure" in f for f in report["findings"]))

    def test_the_report_carries_a_sensitivity_sweep_on_request(self):
        report = fta_report(TREE, sensitivity_event="b3")
        self.assertEqual(len(report["sensitivity"]), 3)

    def test_an_invalid_target_is_rejected(self):
        with self.assertRaises(ValueError):
            fta_report(TREE, target_probability=1.5)


if __name__ == "__main__":
    unittest.main()
