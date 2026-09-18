#!/usr/bin/env python3
"""Contract test for the fault tree analysis usage scoping (offline)."""

import copy
import unittest

from q40_12_fta_usage_logic import (
    ANALYSIS_DIRECTIONS,
    CRITICAL_ITEMS_LIST,
    DEPENDABILITY_ANALYSIS,
    DEPTH_QUALITATIVE,
    DEPTH_QUANTITATIVE,
    HAZARD_ANALYSIS,
    SEVERITY_CATEGORIES,
    TECHNIQUE_BOTH,
    TECHNIQUE_FMECA,
    TECHNIQUE_FTA,
    TECHNIQUE_NONE,
    VERDICT_IN_SCOPE,
    VERDICT_IN_SCOPE_WITH_FMECA,
    VERDICT_NOT_THE_TECHNIQUE,
    basic_event_traceability,
    division_of_labour,
    iec_61025_elements,
    required_depth,
    scope_fta_usage,
    select_technique,
    supported_analyses,
    traceability_verdict,
    validate_need,
)

TREE_NEED = {
    "top_event": "loss of attitude control authority",
    "direction": "top-down-from-consequence",
    "severity": "catastrophic",
    "combination_logic_needed": True,
    "enumerate_all_failure_modes": False,
    "probability_target_declared": True,
    "common_cause_suspected": True,
    "software_or_human_contributors": True,
    "multi_function_scope": True,
}

WORKSHEET_NEED = {
    "top_event": "effects of every valve failure mode",
    "direction": "bottom-up-from-failure-mode",
    "severity": "major",
    "combination_logic_needed": False,
    "enumerate_all_failure_modes": True,
    "probability_target_declared": False,
    "common_cause_suspected": False,
    "software_or_human_contributors": False,
    "multi_function_scope": False,
}

EMPTY_NEED = {
    "top_event": "a review action with no stated direction",
    "direction": "top-down-from-consequence",
    "severity": "minor",
    "combination_logic_needed": False,
    "enumerate_all_failure_modes": False,
    "probability_target_declared": False,
    "common_cause_suspected": False,
    "software_or_human_contributors": False,
    "multi_function_scope": False,
}


def _need(base, **overrides):
    need = copy.deepcopy(base)
    need.update(overrides)
    return need


class NeedValidationTests(unittest.TestCase):
    def test_a_well_formed_need_normalizes(self):
        self.assertEqual(
            validate_need(TREE_NEED)["direction"], "top-down-from-consequence"
        )

    def test_a_non_mapping_need_is_rejected(self):
        with self.assertRaises(ValueError):
            validate_need("loss of control")

    def test_an_unknown_direction_is_rejected(self):
        with self.assertRaises(ValueError):
            validate_need(_need(TREE_NEED, direction="sideways"))

    def test_an_unknown_severity_is_rejected(self):
        with self.assertRaises(ValueError):
            validate_need(_need(TREE_NEED, severity="annoying"))

    def test_an_empty_top_event_is_rejected(self):
        with self.assertRaises(ValueError):
            validate_need(_need(TREE_NEED, top_event="   "))

    def test_a_non_boolean_flag_is_rejected(self):
        with self.assertRaises(ValueError):
            validate_need(_need(TREE_NEED, common_cause_suspected="yes"))

    def test_every_declared_direction_validates(self):
        self.assertIn("not-yet-stated", ANALYSIS_DIRECTIONS)
        for direction in ANALYSIS_DIRECTIONS:
            self.assertEqual(
                validate_need(_need(TREE_NEED, direction=direction))["direction"],
                direction,
            )

    def test_every_declared_severity_validates(self):
        for severity in SEVERITY_CATEGORIES:
            self.assertEqual(
                validate_need(_need(TREE_NEED, severity=severity))["severity"],
                severity,
            )


class TechniqueSelectionTests(unittest.TestCase):
    def test_a_consequence_need_selects_the_tree(self):
        self.assertEqual(select_technique(TREE_NEED)["technique"], TECHNIQUE_FTA)

    def test_an_enumeration_need_selects_the_worksheet(self):
        self.assertEqual(select_technique(WORKSHEET_NEED)["technique"], TECHNIQUE_FMECA)

    def test_a_two_way_need_selects_both(self):
        both = _need(TREE_NEED, direction="both-directions",
                     enumerate_all_failure_modes=True)
        self.assertEqual(select_technique(both)["technique"], TECHNIQUE_BOTH)

    def test_a_need_with_no_duty_selects_neither(self):
        bare = _need(EMPTY_NEED, direction="not-yet-stated")
        self.assertEqual(select_technique(bare)["technique"], TECHNIQUE_NONE)

    def test_common_cause_alone_pulls_the_work_onto_a_tree(self):
        need = _need(WORKSHEET_NEED, common_cause_suspected=True)
        self.assertEqual(select_technique(need)["technique"], TECHNIQUE_BOTH)

    def test_the_selection_carries_a_written_rationale(self):
        self.assertTrue(select_technique(TREE_NEED)["rationale"])


class ReceivingAnalysisTests(unittest.TestCase):
    def test_a_catastrophic_top_event_feeds_the_hazard_analysis(self):
        self.assertIn(HAZARD_ANALYSIS, supported_analyses(TREE_NEED))

    def test_a_catastrophic_top_event_feeds_the_critical_items_list(self):
        self.assertIn(CRITICAL_ITEMS_LIST, supported_analyses(TREE_NEED))

    def test_a_probability_target_feeds_the_dependability_analyses(self):
        self.assertIn(DEPENDABILITY_ANALYSIS, supported_analyses(TREE_NEED))

    def test_a_minor_top_event_without_a_target_feeds_nothing(self):
        self.assertEqual(supported_analyses(EMPTY_NEED), ())


class DepthAndElementTests(unittest.TestCase):
    def test_a_declared_probability_target_forces_quantification(self):
        need = _need(WORKSHEET_NEED, probability_target_declared=True)
        self.assertEqual(required_depth(need), DEPTH_QUANTITATIVE)

    def test_a_catastrophic_severity_forces_quantification_on_its_own(self):
        need = _need(EMPTY_NEED, severity="catastrophic")
        self.assertEqual(required_depth(need), DEPTH_QUANTITATIVE)

    def test_a_minor_top_event_without_a_target_stays_qualitative(self):
        self.assertEqual(required_depth(EMPTY_NEED), DEPTH_QUALITATIVE)

    def test_quantification_elements_switch_on_with_the_depth(self):
        elements = iec_61025_elements(TREE_NEED)
        self.assertIn("top-event-quantification", elements["applicable"])
        self.assertNotIn("top-event-quantification", elements["excluded"])

    def test_quantification_elements_switch_off_when_qualitative(self):
        elements = iec_61025_elements(EMPTY_NEED)
        self.assertIn("top-event-quantification", elements["excluded"])

    def test_cut_set_determination_is_always_applicable(self):
        for need in (TREE_NEED, WORKSHEET_NEED, EMPTY_NEED):
            self.assertIn(
                "minimal-cut-set-determination", iec_61025_elements(need)["applicable"]
            )

    def test_common_cause_modelling_follows_the_declaration(self):
        self.assertIn(
            "common-cause-event-modelling", iec_61025_elements(TREE_NEED)["applicable"]
        )
        self.assertIn(
            "common-cause-event-modelling",
            iec_61025_elements(WORKSHEET_NEED)["excluded"],
        )


class DivisionOfLabourTests(unittest.TestCase):
    def test_the_tree_owns_the_cut_sets(self):
        self.assertEqual(
            division_of_labour(TECHNIQUE_FTA)["minimal-cut-sets"], TECHNIQUE_FTA
        )

    def test_the_worksheet_owns_the_single_mode_effects(self):
        owners = division_of_labour(TECHNIQUE_FMECA)
        self.assertEqual(
            owners["single-item-failure-mode-effects"], TECHNIQUE_FMECA
        )
        self.assertNotIn("minimal-cut-sets", owners)

    def test_a_joint_split_covers_every_artefact(self):
        self.assertEqual(len(division_of_labour(TECHNIQUE_BOTH)), 7)

    def test_no_technique_owns_nothing(self):
        self.assertEqual(division_of_labour(TECHNIQUE_NONE), {})

    def test_an_unknown_technique_is_rejected(self):
        with self.assertRaises(ValueError):
            division_of_labour("guesswork")


class TraceabilityTests(unittest.TestCase):
    def test_a_fully_traced_tree_scores_one(self):
        trace = basic_event_traceability(["b1", "b2"], ["b1", "b2", "b3"])
        self.assertAlmostEqual(trace["fraction"], 1.0, places=9)
        self.assertEqual(trace["untraced"], ())

    def test_an_untraced_event_is_named(self):
        trace = basic_event_traceability(["b1", "sw-timeout"], ["b1"])
        self.assertEqual(trace["untraced"], ("sw-timeout",))
        self.assertAlmostEqual(trace["fraction"], 0.5, places=9)

    def test_an_empty_basic_event_list_is_rejected(self):
        with self.assertRaises(ValueError):
            basic_event_traceability([], ["b1"])

    def test_a_duplicate_basic_event_is_rejected(self):
        with self.assertRaises(ValueError):
            basic_event_traceability(["b1", "b1"], ["b1"])

    def test_a_non_sequence_failure_mode_list_is_rejected(self):
        with self.assertRaises(ValueError):
            basic_event_traceability(["b1"], "b1")

    def test_a_fraction_exactly_on_the_threshold_is_traceable(self):
        self.assertEqual(traceability_verdict(0.9, 0.9), "traceable")

    def test_a_fraction_below_the_threshold_is_a_shortfall(self):
        self.assertEqual(traceability_verdict(0.5, 0.9), "traceability-shortfall")

    def test_a_threshold_outside_the_unit_interval_is_rejected(self):
        with self.assertRaises(ValueError):
            traceability_verdict(0.5, 1.4)


class ScopingTests(unittest.TestCase):
    def test_a_consequence_case_lands_in_scope(self):
        result = scope_fta_usage(dict(TREE_NEED, basic_event_ids=["b1"],
                                      failure_mode_ids=["b1"]))
        self.assertEqual(result["verdict"], VERDICT_IN_SCOPE)
        self.assertEqual(result["traceability_verdict"], "traceable")

    def test_a_two_way_case_lands_in_scope_with_the_worksheet(self):
        both = _need(TREE_NEED, direction="both-directions",
                     enumerate_all_failure_modes=True)
        self.assertEqual(scope_fta_usage(both)["verdict"], VERDICT_IN_SCOPE_WITH_FMECA)

    def test_an_enumeration_case_is_not_a_tree(self):
        result = scope_fta_usage(WORKSHEET_NEED)
        self.assertEqual(result["verdict"], VERDICT_NOT_THE_TECHNIQUE)
        self.assertTrue(result["findings"])

    def test_a_case_without_event_lists_defers_traceability(self):
        result = scope_fta_usage(TREE_NEED)
        self.assertIsNone(result["traceability"])
        self.assertEqual(result["traceability_verdict"], "traceability-not-evaluated")

    def test_an_untraced_event_raises_a_finding(self):
        result = scope_fta_usage(
            dict(TREE_NEED, basic_event_ids=["b1", "sw-timeout"],
                 failure_mode_ids=["b1"])
        )
        self.assertEqual(result["traceability_verdict"], "traceability-shortfall")
        self.assertTrue(any("sw-timeout" in f for f in result["findings"]))

    def test_a_non_mapping_case_is_rejected(self):
        with self.assertRaises(ValueError):
            scope_fta_usage("loss of control")

    def test_a_case_with_no_receiving_analysis_raises_a_finding(self):
        result = scope_fta_usage(_need(EMPTY_NEED, combination_logic_needed=True))
        self.assertEqual(result["supported_analyses"], ())
        self.assertTrue(any("receiving analysis" in f for f in result["findings"]))


if __name__ == "__main__":
    unittest.main()
