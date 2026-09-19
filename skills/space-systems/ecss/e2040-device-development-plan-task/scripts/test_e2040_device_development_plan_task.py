#!/usr/bin/env python3
"""Gate 3 contract test for e2040-device-development-plan-task.

Offline, deterministic, stdlib unittest. Run:
    python3 test_e2040_device_development_plan_task.py
"""

import os
import sys
import unittest

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from e2040_device_development_plan_task_logic import (  # noqa: E402
    DEVELOPMENT_MODELS,
    PROCUREMENT_ROUTES,
    QUALIFICATION_BEARING_MODELS,
    carries_qualification,
    evaluate_development_plan,
    normalize_model,
    normalize_route,
    not_earlier_than,
    not_later_than,
    phase_continuity_findings,
    same_month,
    sequence_in_canonical_order,
    total_duration,
    validate_milestones,
    validate_model_sequence,
    validate_phases,
    validate_procurements,
    validate_technologies,
)


def base_plan():
    return {
        "models": ["breadboard", "engineering-model", "qualification-model",
                   "flight-model"],
        "phases": [
            {"name": "definition", "start_month": 0.0, "end_month": 6.0},
            {"name": "design", "start_month": 6.0, "end_month": 18.0},
            {"name": "qualification", "start_month": 18.0, "end_month": 30.0},
        ],
        "milestones": [
            {"name": "PDR", "month": 6.0, "phase": "definition"},
            {"name": "CDR", "month": 18.0, "phase": "design"},
            {"name": "QR", "month": 30.0, "phase": "qualification"},
        ],
        "technologies": [
            {
                "name": "wide-bandgap switch",
                "trl": 4,
                "maturation_activity": "coupon campaign and radiation lot test",
                "maturation_complete_month": 12.0,
                "needed_by_month": 15.0,
            },
            {"name": "magnetic core", "trl": 8},
        ],
        "procurements": [
            {"item": "control board", "route": "make"},
            {"item": "connector set", "route": "buy", "source": "qualified vendor"},
        ],
        "trl_floor": 5,
        "target_duration_months": 30.0,
    }


def codes(result):
    return sorted({finding["code"] for finding in result["findings"]})


class TestModelFolding(unittest.TestCase):
    def test_short_model_name_folds(self):
        self.assertEqual(normalize_model("EQM"), "engineering-qualification-model")

    def test_spaced_model_name_folds(self):
        self.assertEqual(normalize_model("Proto Flight Model"), "proto-flight-model")

    def test_unknown_model_rejected(self):
        with self.assertRaises(ValueError):
            normalize_model("mockup")

    def test_repeated_model_rejected(self):
        with self.assertRaises(ValueError):
            validate_model_sequence(["em", "engineering-model"])

    def test_empty_model_sequence_rejected(self):
        with self.assertRaises(ValueError):
            validate_model_sequence([])

    def test_model_vocabulary_is_closed(self):
        self.assertEqual(len(DEVELOPMENT_MODELS), 8)
        self.assertEqual(len(QUALIFICATION_BEARING_MODELS), 3)
        self.assertEqual(len(PROCUREMENT_ROUTES), 2)


class TestModelSequence(unittest.TestCase):
    def test_canonical_sequence_accepted(self):
        models = validate_model_sequence(base_plan()["models"])
        self.assertTrue(sequence_in_canonical_order(models))

    def test_reversed_sequence_is_a_finding(self):
        plan = base_plan()
        plan["models"] = ["qualification-model", "engineering-model", "flight-model"]
        result = evaluate_development_plan(plan)
        self.assertIn("model-sequence-out-of-order", codes(result))

    def test_missing_qualification_article_is_a_finding(self):
        plan = base_plan()
        plan["models"] = ["breadboard", "engineering-model", "flight-model"]
        result = evaluate_development_plan(plan)
        self.assertIn("no-qualification-bearing-model", codes(result))
        self.assertFalse(result["qualification_bearing"])

    def test_protoflight_carries_qualification(self):
        self.assertTrue(carries_qualification(["proto-flight-model"]))

    def test_flight_model_alone_does_not_carry_qualification(self):
        self.assertFalse(carries_qualification(["flight-model"]))


class TestPhases(unittest.TestCase):
    def test_contiguous_windows_have_no_finding(self):
        phases = validate_phases(base_plan()["phases"])
        self.assertEqual(phase_continuity_findings(phases), [])

    def test_gap_between_phases_is_reported(self):
        plan = base_plan()
        plan["phases"][2]["start_month"] = 20.0
        result = evaluate_development_plan(plan)
        self.assertIn("phase-window-gap", codes(result))

    def test_overlap_between_phases_is_reported(self):
        plan = base_plan()
        plan["phases"][1]["start_month"] = 4.0
        result = evaluate_development_plan(plan)
        self.assertIn("phase-window-overlap", codes(result))

    def test_zero_length_window_rejected(self):
        with self.assertRaises(ValueError):
            validate_phases([{"name": "a", "start_month": 3.0, "end_month": 3.0}])

    def test_reversed_window_rejected(self):
        with self.assertRaises(ValueError):
            validate_phases([{"name": "a", "start_month": 5.0, "end_month": 2.0}])

    def test_duplicate_phase_name_rejected(self):
        phases = base_plan()["phases"]
        phases.append({"name": "design", "start_month": 30.0, "end_month": 32.0})
        with self.assertRaises(ValueError):
            validate_phases(phases)

    def test_total_duration_spans_first_to_last(self):
        phases = validate_phases(base_plan()["phases"])
        self.assertAlmostEqual(total_duration(phases), 30.0, places=9)

    def test_negative_month_rejected(self):
        with self.assertRaises(ValueError):
            validate_phases([{"name": "a", "start_month": -1.0, "end_month": 2.0}])


class TestMilestones(unittest.TestCase):
    def test_milestone_on_the_phase_boundary_is_inside(self):
        result = evaluate_development_plan(base_plan())
        self.assertNotIn("milestone-outside-phase", codes(result))

    def test_milestone_outside_its_phase_is_reported(self):
        plan = base_plan()
        plan["milestones"][1]["month"] = 24.0
        result = evaluate_development_plan(plan)
        self.assertIn("milestone-outside-phase", codes(result))

    def test_milestone_naming_an_undeclared_phase_is_reported(self):
        plan = base_plan()
        plan["milestones"][0]["phase"] = "phase-zero"
        result = evaluate_development_plan(plan)
        self.assertIn("milestone-phase-not-declared", codes(result))

    def test_duplicate_milestone_rejected(self):
        milestones = base_plan()["milestones"]
        milestones.append(dict(milestones[0]))
        with self.assertRaises(ValueError):
            validate_milestones(milestones)

    def test_milestone_missing_phase_rejected(self):
        with self.assertRaises(ValueError):
            validate_milestones([{"name": "PDR", "month": 1.0}])


class TestTechnologies(unittest.TestCase):
    def test_low_readiness_without_maturation_is_reported(self):
        plan = base_plan()
        plan["technologies"][0]["maturation_activity"] = ""
        result = evaluate_development_plan(plan)
        self.assertIn("low-readiness-without-maturation", codes(result))

    def test_maturation_without_completion_date_is_reported(self):
        plan = base_plan()
        del plan["technologies"][0]["maturation_complete_month"]
        result = evaluate_development_plan(plan)
        self.assertIn("maturation-without-completion-date", codes(result))

    def test_maturation_after_the_need_date_is_reported(self):
        plan = base_plan()
        plan["technologies"][0]["maturation_complete_month"] = 17.0
        result = evaluate_development_plan(plan)
        self.assertIn("maturation-later-than-needed", codes(result))

    def test_maturation_exactly_on_the_need_date_passes(self):
        plan = base_plan()
        plan["technologies"][0]["maturation_complete_month"] = 15.0
        result = evaluate_development_plan(plan)
        self.assertNotIn("maturation-later-than-needed", codes(result))

    def test_technology_above_the_floor_needs_nothing(self):
        result = evaluate_development_plan(base_plan())
        self.assertEqual(result["findings"], [])

    def test_readiness_level_out_of_range_rejected(self):
        with self.assertRaises(ValueError):
            validate_technologies([{"name": "x", "trl": 11}])

    def test_boolean_readiness_level_rejected(self):
        with self.assertRaises(ValueError):
            validate_technologies([{"name": "x", "trl": True}])

    def test_duplicate_technology_rejected(self):
        with self.assertRaises(ValueError):
            validate_technologies(
                [{"name": "x", "trl": 4}, {"name": "x", "trl": 6}]
            )


class TestProcurement(unittest.TestCase):
    def test_bought_item_without_source_is_reported(self):
        plan = base_plan()
        plan["procurements"][1]["source"] = ""
        result = evaluate_development_plan(plan)
        self.assertIn("bought-item-without-source", codes(result))

    def test_made_item_with_external_source_is_reported(self):
        plan = base_plan()
        plan["procurements"][0]["source"] = "external house"
        result = evaluate_development_plan(plan)
        self.assertIn("made-item-sourced-externally", codes(result))

    def test_route_alias_folds(self):
        self.assertEqual(normalize_route("Subcontract"), "buy")

    def test_unknown_route_rejected(self):
        with self.assertRaises(ValueError):
            normalize_route("borrow")

    def test_duplicate_procurement_item_rejected(self):
        with self.assertRaises(ValueError):
            validate_procurements(
                [{"item": "x", "route": "buy", "source": "v"},
                 {"item": "x", "route": "make"}]
            )


class TestSchedulePortability(unittest.TestCase):
    def test_joins_that_differ_in_the_last_place_are_the_same_month(self):
        self.assertTrue(same_month(0.1 + 0.2, 0.3))

    def test_point_on_the_bound_is_not_later(self):
        self.assertTrue(not_later_than(0.1 + 0.2, 0.3))

    def test_point_on_the_bound_is_not_earlier(self):
        self.assertTrue(not_earlier_than(0.1 + 0.2, 0.3))

    def test_duration_exactly_on_the_target_passes(self):
        result = evaluate_development_plan(base_plan())
        self.assertNotIn("plan-exceeds-target-duration", codes(result))

    def test_duration_over_the_target_is_reported(self):
        plan = base_plan()
        plan["target_duration_months"] = 24.0
        result = evaluate_development_plan(plan)
        self.assertIn("plan-exceeds-target-duration", codes(result))


class TestPlanAssessment(unittest.TestCase):
    def test_clean_plan_is_coherent(self):
        result = evaluate_development_plan(base_plan())
        self.assertTrue(result["coherent"])
        self.assertEqual(result["phase_count"], 3)
        self.assertAlmostEqual(result["duration_months"], 30.0, places=9)

    def test_unknown_plan_key_rejected(self):
        plan = base_plan()
        plan["budget"] = 1
        with self.assertRaises(ValueError):
            evaluate_development_plan(plan)

    def test_missing_phases_rejected(self):
        plan = base_plan()
        del plan["phases"]
        with self.assertRaises(ValueError):
            evaluate_development_plan(plan)

    def test_readiness_floor_out_of_range_rejected(self):
        plan = base_plan()
        plan["trl_floor"] = 0
        with self.assertRaises(ValueError):
            evaluate_development_plan(plan)

    def test_non_mapping_plan_rejected(self):
        with self.assertRaises(ValueError):
            evaluate_development_plan([("models", [])])


if __name__ == "__main__":
    unittest.main()
