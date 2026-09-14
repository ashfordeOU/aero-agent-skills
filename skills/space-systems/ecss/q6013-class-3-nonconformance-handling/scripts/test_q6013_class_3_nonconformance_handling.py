"""Contract tests for the clause 6.5.2 class 3 nonconformance handling logic."""

import unittest

from q6013_class_3_nonconformance_handling_logic import (
    ANALYSIS_DEPTHS,
    CATEGORIES,
    DETECTION_STAGES,
    RECURRENCE_THRESHOLD,
    REPORT_ROUTES,
    RESPONSE_WINDOW_WORKING_DAYS,
    analysis_owed,
    assess_nonconformance,
    categorize_finding,
    containment_population,
    disposition_admissible,
    escape_depth,
    grade_analysis,
    observed_failure_fraction,
    owed_analysis_depth,
    reporting_route,
    working_days_between,
)


def closed_analysis(depth="visual-and-electrical"):
    return {
        "depth": depth,
        "mechanism_identified": True,
        "corrective_action_defined": True,
        "effectivity_stated": True,
        "action_verified": True,
    }


def base_record(**overrides):
    """Return a minor isolated finding caught at incoming verification."""
    record = {
        "nonconformance_id": "NCR-2026-118",
        "mechanism": "isolated-random",
        "detection_stage": "incoming-verification",
        "detection_date": "2026-09-07",
        "response_date": "2026-09-11",
        "effects": ["cosmetic"],
        "recurrence_count": 1,
        "failed_quantity": 2,
        "inspected_quantity": 40,
        "lot_quantity": 500,
        "sister_lot_quantity": 0,
        "disposition": "scrap",
        "analysis": closed_analysis("none"),
        "part_removed": False,
        "procedure_qualified": False,
        "hardware_delivered": False,
    }
    record.update(overrides)
    return record


class StageTests(unittest.TestCase):
    def test_escape_depth_increases_down_the_chain(self):
        self.assertLess(
            escape_depth("incoming-verification"), escape_depth("system-test")
        )

    def test_every_stage_resolves(self):
        for stage in DETECTION_STAGES:
            self.assertGreaterEqual(escape_depth(stage), 0)

    def test_unknown_stage_rejected(self):
        with self.assertRaises(ValueError):
            escape_depth("coffee-break")


class WorkingDayTests(unittest.TestCase):
    def test_same_day_is_zero(self):
        self.assertEqual(working_days_between("2026-09-07", "2026-09-07"), 0)

    def test_monday_to_friday_is_four(self):
        self.assertEqual(working_days_between("2026-09-07", "2026-09-11"), 4)

    def test_weekend_is_not_counted(self):
        self.assertEqual(working_days_between("2026-09-11", "2026-09-14"), 1)

    def test_backwards_range_rejected(self):
        with self.assertRaises(ValueError):
            working_days_between("2026-09-14", "2026-09-07")

    def test_malformed_date_rejected(self):
        with self.assertRaises(ValueError):
            working_days_between("07-09-2026x", "2026-09-14")


class CategorizeTests(unittest.TestCase):
    def test_cosmetic_effect_stays_minor(self):
        self.assertEqual(
            categorize_finding(
                ["cosmetic"], "isolated-random", "incoming-verification"
            )["category"],
            "minor",
        )

    def test_safety_effect_forces_critical(self):
        self.assertEqual(
            categorize_finding(["safety"], "isolated-random", "incoming-verification")[
                "category"
            ],
            "critical",
        )

    def test_performance_effect_forces_major(self):
        self.assertEqual(
            categorize_finding(
                ["performance-degradation"], "workmanship", "incoming-verification"
            )["category"],
            "major",
        )

    def test_highest_effect_wins_over_the_others(self):
        verdict = categorize_finding(
            ["cosmetic", "safety", "schedule"], "workmanship", "incoming-verification"
        )
        self.assertEqual(verdict["category"], "critical")

    def test_lot_related_escape_grades_up_to_major(self):
        verdict = categorize_finding(
            ["cosmetic"], "lot-related", "board-assembly-test"
        )
        self.assertEqual(verdict["category"], "major")

    def test_lot_related_at_incoming_does_not_grade_up(self):
        verdict = categorize_finding(
            ["cosmetic"], "lot-related", "incoming-verification"
        )
        self.assertEqual(verdict["category"], "minor")

    def test_reasons_are_kept_for_defence(self):
        verdict = categorize_finding(["safety"], "unknown", "system-test")
        self.assertTrue(verdict["reasons"])

    def test_no_effect_still_returns_a_category(self):
        verdict = categorize_finding([], "isolated-random", "incoming-verification")
        self.assertIn(verdict["category"], CATEGORIES)

    def test_unknown_effect_rejected(self):
        with self.assertRaises(ValueError):
            categorize_finding(["annoying"], "workmanship", "incoming-verification")

    def test_unknown_mechanism_rejected(self):
        with self.assertRaises(ValueError):
            categorize_finding(["cosmetic"], "gremlins", "incoming-verification")


class AnalysisOwedTests(unittest.TestCase):
    def test_minor_isolated_first_occurrence_owes_nothing(self):
        verdict = analysis_owed("minor", "isolated-random", 1, "incoming-verification")
        self.assertFalse(verdict["owed"])

    def test_major_category_owes_an_analysis(self):
        self.assertTrue(
            analysis_owed("major", "isolated-random", 1, "incoming-verification")["owed"]
        )

    def test_unknown_mechanism_owes_an_analysis(self):
        self.assertTrue(
            analysis_owed("minor", "unknown", 1, "incoming-verification")["owed"]
        )

    def test_recurrence_at_the_threshold_owes_an_analysis(self):
        self.assertTrue(
            analysis_owed(
                "minor", "isolated-random", RECURRENCE_THRESHOLD, "incoming-verification"
            )["owed"]
        )

    def test_deep_escape_owes_an_analysis(self):
        self.assertTrue(
            analysis_owed("minor", "isolated-random", 1, "unit-functional-test")["owed"]
        )

    def test_zero_recurrence_count_rejected(self):
        with self.assertRaises(ValueError):
            analysis_owed("minor", "isolated-random", 0, "incoming-verification")

    def test_owed_depth_is_none_when_nothing_is_owed(self):
        self.assertEqual(
            owed_analysis_depth("minor", "isolated-random", 1, "incoming-verification"),
            "none",
        )

    def test_lot_related_mechanism_earns_the_deepest_route(self):
        self.assertEqual(
            owed_analysis_depth("minor", "lot-related", 1, "incoming-verification"),
            "destructive-physical-analysis",
        )

    def test_major_category_alone_earns_imaging(self):
        self.assertEqual(
            owed_analysis_depth("major", "workmanship", 1, "incoming-verification"),
            "imaging",
        )

    def test_deepest_reason_wins_not_the_first(self):
        depth = owed_analysis_depth("major", "lot-related", 1, "board-assembly-test")
        self.assertEqual(depth, "destructive-physical-analysis")

    def test_every_depth_name_is_recognised(self):
        for depth in ANALYSIS_DEPTHS:
            self.assertIn(depth, ANALYSIS_DEPTHS)


class GradeAnalysisTests(unittest.TestCase):
    def test_complete_analysis_at_the_owed_depth_closes(self):
        verdict = grade_analysis(closed_analysis("imaging"), "imaging")
        self.assertTrue(verdict["complete"])

    def test_deeper_analysis_than_owed_is_accepted(self):
        verdict = grade_analysis(
            closed_analysis("destructive-physical-analysis"), "imaging"
        )
        self.assertTrue(verdict["complete"])

    def test_shallower_analysis_than_owed_is_reported(self):
        verdict = grade_analysis(closed_analysis("visual-and-electrical"), "imaging")
        self.assertFalse(verdict["complete"])

    def test_every_missing_element_is_reported_together(self):
        performed = closed_analysis("imaging")
        performed["effectivity_stated"] = False
        performed["action_verified"] = False
        verdict = grade_analysis(performed, "imaging")
        self.assertEqual(len(verdict["missing"]), 2)

    def test_non_boolean_element_rejected(self):
        performed = closed_analysis("imaging")
        performed["action_verified"] = "later"
        with self.assertRaises(ValueError):
            grade_analysis(performed, "imaging")

    def test_unknown_depth_rejected(self):
        with self.assertRaises(ValueError):
            grade_analysis(closed_analysis("imaging"), "x-ray-vision")


class ReportingRouteTests(unittest.TestCase):
    def test_minor_isolated_finding_stays_in_the_internal_log(self):
        route = reporting_route(
            "minor", ["cosmetic"], "incoming-verification", False, False
        )
        self.assertEqual(route, "internal-log")

    def test_owed_analysis_reaches_the_parts_control_board(self):
        route = reporting_route(
            "minor", ["cosmetic"], "incoming-verification", True, False
        )
        self.assertEqual(route, "parts-control-board")

    def test_safety_effect_reaches_the_customer(self):
        route = reporting_route("critical", ["safety"], "board-assembly-test", True, False)
        self.assertEqual(route, "customer-notification")

    def test_deep_escape_reaches_the_customer(self):
        route = reporting_route("minor", ["cosmetic"], "system-test", False, False)
        self.assertEqual(route, "customer-notification")

    def test_delivered_hardware_reaches_the_customer(self):
        route = reporting_route(
            "minor", ["cosmetic"], "incoming-verification", False, True
        )
        self.assertEqual(route, "customer-notification")

    def test_route_order_is_narrowest_first(self):
        self.assertEqual(REPORT_ROUTES[0], "internal-log")

    def test_non_boolean_delivery_flag_rejected(self):
        with self.assertRaises(ValueError):
            reporting_route("minor", ["cosmetic"], "system-test", False, "yes")


class DispositionTests(unittest.TestCase):
    def test_scrap_always_closes(self):
        verdict = disposition_admissible(
            "scrap", False, "unknown", ["safety"], False, False
        )
        self.assertTrue(verdict["permitted"])

    def test_return_needs_the_part_removed(self):
        verdict = disposition_admissible(
            "return-to-supplier", True, "workmanship", ["cosmetic"], False, True
        )
        self.assertFalse(verdict["permitted"])

    def test_rework_needs_a_qualified_procedure(self):
        verdict = disposition_admissible(
            "rework", True, "workmanship", ["cosmetic"], True, False
        )
        self.assertFalse(verdict["permitted"])

    def test_repair_needs_the_analysis_closed(self):
        verdict = disposition_admissible(
            "repair", False, "workmanship", ["cosmetic"], True, True
        )
        self.assertFalse(verdict["permitted"])

    def test_use_as_is_collects_all_three_refusals(self):
        verdict = disposition_admissible(
            "use-as-is", False, "lot-related", ["safety"], True, True
        )
        self.assertEqual(len(verdict["refusals"]), 3)

    def test_use_as_is_on_a_bounded_finding_is_permitted(self):
        verdict = disposition_admissible(
            "use-as-is", True, "isolated-random", ["cosmetic"], True, True
        )
        self.assertTrue(verdict["permitted"])

    def test_unknown_disposition_rejected(self):
        with self.assertRaises(ValueError):
            disposition_admissible(
                "ignore-it", True, "workmanship", ["cosmetic"], True, True
            )


class ContainmentTests(unittest.TestCase):
    def test_isolated_mechanism_contains_the_failed_parts(self):
        result = containment_population("isolated-random", 2, 40, 500)
        self.assertEqual(result["contained_quantity"], 2)

    def test_lot_related_mechanism_contains_the_whole_lot(self):
        result = containment_population("lot-related", 2, 40, 500)
        self.assertEqual(result["contained_quantity"], 500)

    def test_sister_lot_is_added_to_the_containment(self):
        result = containment_population("lot-related", 2, 40, 500, 300)
        self.assertEqual(result["contained_quantity"], 800)

    def test_uninspected_remainder_is_reported_explicitly(self):
        result = containment_population("lot-related", 2, 40, 500)
        self.assertEqual(result["uninspected_remainder"], 460)

    def test_inspected_quantity_above_the_lot_rejected(self):
        with self.assertRaises(ValueError):
            containment_population("lot-related", 2, 600, 500)

    def test_failed_quantity_above_the_inspected_rejected(self):
        with self.assertRaises(ValueError):
            containment_population("lot-related", 50, 40, 500)

    def test_negative_quantity_rejected(self):
        with self.assertRaises(ValueError):
            containment_population("lot-related", 2, 40, 500, -1)

    def test_observed_fraction_is_over_the_sample(self):
        self.assertAlmostEqual(observed_failure_fraction(2, 40), 0.05, places=9)

    def test_observed_fraction_of_a_clean_sample_is_zero(self):
        self.assertAlmostEqual(observed_failure_fraction(0, 40), 0.0, places=9)

    def test_observed_fraction_of_a_full_sample_is_one(self):
        self.assertAlmostEqual(observed_failure_fraction(40, 40), 1.0, places=9)

    def test_zero_inspected_quantity_rejected(self):
        with self.assertRaises(ValueError):
            observed_failure_fraction(0, 0)


class AssessmentTests(unittest.TestCase):
    def test_minor_isolated_finding_closes(self):
        result = assess_nonconformance(base_record(), "2026-09-14")
        self.assertEqual(result["verdict"], "closed")
        self.assertTrue(result["closed"])

    def test_minor_isolated_finding_owes_no_analysis(self):
        result = assess_nonconformance(base_record(), "2026-09-14")
        self.assertFalse(result["analysis_owed"])
        self.assertEqual(result["analysis_depth_owed"], "none")

    def test_refused_disposition_blocks_first(self):
        record = base_record(
            disposition="use-as-is", mechanism="unknown", analysis=closed_analysis("none")
        )
        result = assess_nonconformance(record, "2026-09-14")
        self.assertEqual(result["verdict"], "disposition-refused")

    def test_incomplete_analysis_is_reported(self):
        record = base_record(
            mechanism="lot-related",
            disposition="scrap",
            analysis=closed_analysis("visual-and-electrical"),
        )
        result = assess_nonconformance(record, "2026-09-14")
        self.assertEqual(result["verdict"], "failure-analysis-incomplete")

    def test_lot_containment_shows_in_the_verdict(self):
        record = base_record(
            mechanism="lot-related",
            disposition="scrap",
            analysis=closed_analysis("destructive-physical-analysis"),
        )
        result = assess_nonconformance(record, "2026-09-14")
        self.assertEqual(result["verdict"], "closed-with-lot-containment")

    def test_late_response_is_reported(self):
        record = base_record(response_date="2026-10-30")
        result = assess_nonconformance(record, "2026-11-02")
        self.assertEqual(result["verdict"], "response-late")

    def test_open_response_keeps_accruing(self):
        record = base_record(response_date=None)
        result = assess_nonconformance(record, "2026-09-14")
        self.assertEqual(result["response_state"], "open")
        self.assertEqual(result["response_working_days"], 5)

    def test_response_window_matches_the_category(self):
        result = assess_nonconformance(base_record(), "2026-09-14")
        self.assertEqual(
            result["response_window_days"], RESPONSE_WINDOW_WORKING_DAYS["minor"]
        )

    def test_observed_fraction_is_carried_through(self):
        result = assess_nonconformance(base_record(), "2026-09-14")
        self.assertAlmostEqual(result["observed_failure_fraction"], 0.05, places=9)

    def test_uninspected_remainder_appears_in_the_findings(self):
        record = base_record(
            mechanism="lot-related",
            disposition="scrap",
            analysis=closed_analysis("destructive-physical-analysis"),
        )
        result = assess_nonconformance(record, "2026-09-14")
        self.assertTrue(
            any("never inspected" in finding for finding in result["findings"])
        )

    def test_unknown_record_key_rejected(self):
        with self.assertRaises(ValueError):
            assess_nonconformance(base_record(budget="none"), "2026-09-14")

    def test_missing_required_key_rejected(self):
        record = base_record()
        del record["mechanism"]
        with self.assertRaises(ValueError):
            assess_nonconformance(record, "2026-09-14")

    def test_response_before_detection_rejected(self):
        with self.assertRaises(ValueError):
            assess_nonconformance(base_record(response_date="2026-09-01"), "2026-09-14")

    def test_as_of_before_detection_rejected(self):
        with self.assertRaises(ValueError):
            assess_nonconformance(base_record(response_date=None), "2026-09-01")

    def test_blank_identity_rejected(self):
        with self.assertRaises(ValueError):
            assess_nonconformance(base_record(nonconformance_id="  "), "2026-09-14")


if __name__ == "__main__":
    unittest.main()
