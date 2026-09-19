"""Contract tests for the Annex G architecture definition report data-item logic."""

import unittest

from e2040_architecture_definition_report_data_item_logic import (
    REQUIRED_SECTIONS,
    SCORE_TIE_TOLERANCE,
    allocation_map,
    assess_architecture_report,
    coupling_ratio,
    decision_margin,
    external_degree,
    missing_sections,
    most_connected_block,
    option_scores,
    partitioning_findings,
    rank_options,
    sensitivity_flips,
    split_connections,
    validate_blocks,
    validate_connections,
    validate_functions,
    validate_trade_study,
)

ALL_SECTIONS = list(REQUIRED_SECTIONS)
BLOCKS = ["B-CORE", "B-IO", "B-PWR"]

FUNCTIONS = [
    {"id": "F-1", "allocated_to": "B-CORE"},
    {"id": "F-2", "allocated_to": "B-CORE"},
    {"id": "F-3", "allocated_to": "B-IO"},
    {"id": "F-4", "allocated_to": "B-PWR"},
]

CONNECTIONS = [("F-1", "F-2"), ("F-1", "F-3"), ("F-1", "F-4")]

STUDY = {
    "criteria": {"mass": 0.5, "power": 0.25, "heritage": 0.25},
    "score_scale": (1.0, 5.0),
    "options": {
        "OPT-A": {"mass": 5.0, "power": 3.0, "heritage": 2.0},
        "OPT-B": {"mass": 2.0, "power": 4.0, "heritage": 5.0},
    },
}


class SectionTests(unittest.TestCase):
    def test_complete_section_list_has_no_gap(self):
        self.assertEqual(missing_sections(ALL_SECTIONS), [])

    def test_absent_trade_off_section_is_named(self):
        partial = [s for s in ALL_SECTIONS if s != "design-trade-offs"]
        self.assertEqual(missing_sections(partial), ["design-trade-offs"])

    def test_non_sequence_section_list_rejected(self):
        with self.assertRaises(ValueError):
            missing_sections({"scope": True})


class BlockAndAllocationTests(unittest.TestCase):
    def test_blocks_are_returned_in_order(self):
        self.assertEqual(validate_blocks(BLOCKS), BLOCKS)

    def test_duplicate_block_rejected(self):
        with self.assertRaises(ValueError):
            validate_blocks(["B-CORE", "B-CORE"])

    def test_empty_block_list_rejected(self):
        with self.assertRaises(ValueError):
            validate_blocks([])

    def test_string_allocation_is_wrapped(self):
        records = validate_functions(FUNCTIONS, BLOCKS)
        self.assertEqual(records[0]["allocated_to"], ["B-CORE"])

    def test_allocation_to_an_undeclared_block_rejected(self):
        with self.assertRaises(ValueError):
            validate_functions([{"id": "F-1", "allocated_to": "B-GHOST"}], BLOCKS)

    def test_duplicate_function_identifier_rejected(self):
        with self.assertRaises(ValueError):
            validate_functions(
                [{"id": "F-1", "allocated_to": "B-CORE"}, {"id": "F-1", "allocated_to": "B-IO"}],
                BLOCKS,
            )

    def test_clean_partitioning_has_no_defect(self):
        records = validate_functions(FUNCTIONS, BLOCKS)
        defects = partitioning_findings(records, BLOCKS)
        self.assertEqual(defects["unallocated_functions"], [])
        self.assertEqual(defects["doubly_allocated_functions"], [])
        self.assertEqual(defects["empty_blocks"], [])

    def test_doubly_allocated_function_is_reported(self):
        functions = [{"id": "F-1", "allocated_to": ["B-CORE", "B-IO"]},
                     {"id": "F-2", "allocated_to": "B-PWR"}]
        records = validate_functions(functions, BLOCKS)
        defects = partitioning_findings(records, BLOCKS)
        self.assertEqual(defects["doubly_allocated_functions"], ["F-1"])

    def test_unallocated_function_is_reported(self):
        functions = [{"id": "F-1", "allocated_to": []}, {"id": "F-2", "allocated_to": "B-CORE"}]
        records = validate_functions(functions, BLOCKS)
        defects = partitioning_findings(records, BLOCKS)
        self.assertEqual(defects["unallocated_functions"], ["F-1"])

    def test_block_hosting_nothing_is_reported(self):
        functions = [{"id": "F-1", "allocated_to": "B-CORE"}]
        records = validate_functions(functions, BLOCKS)
        defects = partitioning_findings(records, BLOCKS)
        self.assertEqual(defects["empty_blocks"], ["B-IO", "B-PWR"])

    def test_allocation_map_skips_an_ambiguous_function(self):
        functions = [{"id": "F-1", "allocated_to": ["B-CORE", "B-IO"]},
                     {"id": "F-2", "allocated_to": "B-PWR"}]
        records = validate_functions(functions, BLOCKS)
        self.assertEqual(allocation_map(records), {"F-2": "B-PWR"})


class ConnectionTests(unittest.TestCase):
    def setUp(self):
        self.records = validate_functions(FUNCTIONS, BLOCKS)
        self.ids = [r["id"] for r in self.records]
        self.allocation = allocation_map(self.records)

    def test_duplicate_pair_is_collapsed(self):
        pairs = validate_connections([("F-1", "F-2"), ("F-2", "F-1")], self.ids)
        self.assertEqual(len(pairs), 1)

    def test_dangling_endpoint_rejected(self):
        with self.assertRaises(ValueError):
            validate_connections([("F-1", "F-99")], self.ids)

    def test_self_connection_rejected(self):
        with self.assertRaises(ValueError):
            validate_connections([("F-1", "F-1")], self.ids)

    def test_split_follows_the_allocation(self):
        pairs = validate_connections(CONNECTIONS, self.ids)
        within, across = split_connections(pairs, self.allocation)
        self.assertEqual(len(within), 1)
        self.assertEqual(len(across), 2)

    def test_coupling_ratio_is_the_across_share(self):
        pairs = validate_connections(CONNECTIONS, self.ids)
        within, across = split_connections(pairs, self.allocation)
        self.assertAlmostEqual(coupling_ratio(within, across), 2.0 / 3.0, places=9)

    def test_moving_a_function_changes_the_ratio(self):
        moved = [
            {"id": "F-1", "allocated_to": "B-CORE"},
            {"id": "F-2", "allocated_to": "B-CORE"},
            {"id": "F-3", "allocated_to": "B-CORE"},
            {"id": "F-4", "allocated_to": "B-PWR"},
        ]
        records = validate_functions(moved, BLOCKS)
        pairs = validate_connections(CONNECTIONS, [r["id"] for r in records])
        within, across = split_connections(pairs, allocation_map(records))
        self.assertAlmostEqual(coupling_ratio(within, across), 1.0 / 3.0, places=9)

    def test_ratio_with_no_connections_rejected(self):
        with self.assertRaises(ValueError):
            coupling_ratio([], [])

    def test_external_degree_counts_both_ends(self):
        pairs = validate_connections(CONNECTIONS, self.ids)
        _, across = split_connections(pairs, self.allocation)
        degree = external_degree(BLOCKS, across, self.allocation)
        self.assertEqual(degree["B-CORE"], 2)
        self.assertEqual(degree["B-IO"], 1)

    def test_hub_block_is_the_highest_degree(self):
        pairs = validate_connections(CONNECTIONS, self.ids)
        _, across = split_connections(pairs, self.allocation)
        degree = external_degree(BLOCKS, across, self.allocation)
        self.assertEqual(most_connected_block(degree), "B-CORE")

    def test_empty_degree_mapping_rejected(self):
        with self.assertRaises(ValueError):
            most_connected_block({})


class TradeStudyTests(unittest.TestCase):
    def test_weights_summing_off_one_rejected(self):
        bad = {"criteria": {"mass": 0.5, "power": 0.2}, "score_scale": (1.0, 5.0),
               "options": {"A": {"mass": 3.0, "power": 3.0}, "B": {"mass": 4.0, "power": 2.0}}}
        with self.assertRaises(ValueError):
            validate_trade_study(bad)

    def test_negative_weight_rejected(self):
        bad = {"criteria": {"mass": 1.5, "power": -0.5}, "score_scale": (1.0, 5.0),
               "options": {"A": {"mass": 3.0, "power": 3.0}, "B": {"mass": 4.0, "power": 2.0}}}
        with self.assertRaises(ValueError):
            validate_trade_study(bad)

    def test_score_outside_the_scale_rejected(self):
        bad = {"criteria": {"mass": 1.0}, "score_scale": (1.0, 5.0),
               "options": {"A": {"mass": 9.0}, "B": {"mass": 2.0}}}
        with self.assertRaises(ValueError):
            validate_trade_study(bad)

    def test_missing_score_rejected(self):
        bad = {"criteria": {"mass": 0.5, "power": 0.5}, "score_scale": (1.0, 5.0),
               "options": {"A": {"mass": 3.0}, "B": {"mass": 4.0, "power": 2.0}}}
        with self.assertRaises(ValueError):
            validate_trade_study(bad)

    def test_single_option_rejected(self):
        bad = {"criteria": {"mass": 1.0}, "score_scale": (1.0, 5.0),
               "options": {"A": {"mass": 3.0}}}
        with self.assertRaises(ValueError):
            validate_trade_study(bad)

    def test_weighted_scores_are_computed(self):
        scores = option_scores(STUDY)
        self.assertAlmostEqual(scores["OPT-A"], 3.75, places=9)
        self.assertAlmostEqual(scores["OPT-B"], 3.25, places=9)

    def test_ranking_is_by_descending_score(self):
        self.assertEqual(rank_options(option_scores(STUDY)), ["OPT-A", "OPT-B"])

    def test_decision_margin_is_the_gap_to_the_runner_up(self):
        self.assertAlmostEqual(decision_margin(option_scores(STUDY)), 0.5, places=9)

    def test_tied_options_give_a_zero_margin(self):
        tied = {"criteria": {"mass": 1.0}, "score_scale": (1.0, 5.0),
                "options": {"A": {"mass": 3.0}, "B": {"mass": 3.0}}}
        self.assertAlmostEqual(decision_margin(option_scores(tied)), 0.0, places=9)

    def test_margin_needs_two_options(self):
        with self.assertRaises(ValueError):
            decision_margin({"A": 3.0})

    def test_a_decisive_study_does_not_flip(self):
        decisive = {"criteria": {"mass": 0.5, "power": 0.25, "heritage": 0.25},
                    "score_scale": (1.0, 5.0),
                    "options": {"A": {"mass": 5.0, "power": 5.0, "heritage": 5.0},
                                "B": {"mass": 1.0, "power": 1.0, "heritage": 1.0}}}
        self.assertEqual(sensitivity_flips(decisive, 0.1), [])

    def test_a_close_study_flips_on_the_criterion_that_carried_it(self):
        flips = sensitivity_flips(STUDY, 0.3)
        self.assertIn("heritage", flips)

    def test_sensitivity_step_outside_the_open_unit_interval_rejected(self):
        with self.assertRaises(ValueError):
            sensitivity_flips(STUDY, 1.0)


class AssessmentTests(unittest.TestCase):
    def _report(self, **overrides):
        report = {
            "sections": list(ALL_SECTIONS),
            "blocks": list(BLOCKS),
            "functions": [dict(f) for f in FUNCTIONS],
            "connections": list(CONNECTIONS),
            "trade_study": STUDY,
            "max_coupling_ratio": 0.7,
            "sensitivity_step": 0.05,
        }
        report.update(overrides)
        return report

    def test_clean_report_is_compliant(self):
        result = assess_architecture_report(self._report())
        self.assertTrue(result["compliant"])
        self.assertEqual(result["findings"], [])
        self.assertEqual(result["recommended_option"], "OPT-A")

    def test_coupling_above_the_limit_is_a_finding(self):
        result = assess_architecture_report(self._report(max_coupling_ratio=0.5))
        self.assertFalse(result["compliant"])
        self.assertTrue(any("coupling ratio" in f for f in result["findings"]))

    def test_coupling_exactly_at_the_limit_is_accepted(self):
        result = assess_architecture_report(self._report(max_coupling_ratio=2.0 / 3.0))
        self.assertTrue(result["compliant"])

    def test_double_allocation_suppresses_the_coupling_figure(self):
        functions = [dict(f) for f in FUNCTIONS]
        functions[0]["allocated_to"] = ["B-CORE", "B-IO"]
        result = assess_architecture_report(self._report(functions=functions))
        self.assertIsNone(result["coupling_ratio"])
        self.assertFalse(result["compliant"])

    def test_empty_block_is_a_finding(self):
        functions = [f for f in FUNCTIONS if f["allocated_to"] != "B-PWR"]
        connections = [("F-1", "F-2"), ("F-1", "F-3")]
        result = assess_architecture_report(
            self._report(functions=functions, connections=connections)
        )
        self.assertTrue(any("hosts no function" in f for f in result["findings"]))

    def test_hub_block_is_reported(self):
        result = assess_architecture_report(self._report())
        self.assertEqual(result["most_connected_block"], "B-CORE")

    def test_flipping_study_is_a_finding(self):
        result = assess_architecture_report(self._report(sensitivity_step=0.3))
        self.assertTrue(any("flips" in f for f in result["findings"]))

    def test_tied_study_is_a_finding(self):
        tied = {"criteria": {"mass": 0.5, "power": 0.5}, "score_scale": (1.0, 5.0),
                "options": {"A": {"mass": 3.0, "power": 3.0}, "B": {"mass": 3.0, "power": 3.0}}}
        result = assess_architecture_report(self._report(trade_study=tied))
        self.assertLessEqual(result["decision_margin"], SCORE_TIE_TOLERANCE)
        self.assertTrue(any("no usable margin" in f for f in result["findings"]))

    def test_limit_outside_unit_interval_rejected(self):
        with self.assertRaises(ValueError):
            assess_architecture_report(self._report(max_coupling_ratio=1.4))

    def test_missing_report_key_rejected(self):
        report = self._report()
        del report["connections"]
        with self.assertRaises(ValueError):
            assess_architecture_report(report)

    def test_non_mapping_report_rejected(self):
        with self.assertRaises(ValueError):
            assess_architecture_report("report")


if __name__ == "__main__":
    unittest.main()
