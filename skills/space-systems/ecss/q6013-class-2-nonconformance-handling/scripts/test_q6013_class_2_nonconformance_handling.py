"""Contract tests for the clause 5.5.2 class 2 nonconformance logic."""

import datetime
import unittest

from q6013_class_2_nonconformance_handling_logic import (
    ANALYSIS_DEPTHS,
    BOUND_TOLERANCE,
    RESPONSE_HOURS,
    analysis_completeness,
    assess_class_two_nonconformance,
    categorize_finding,
    containment_scope,
    disposition_admissible,
    failure_analysis_required,
    owed_analysis_depth,
    response_timeliness,
)


def _analysis(**over):
    base = {
        "depth_performed": "destructive-physical-analysis",
        "mechanism_identified": True,
        "corrective_action": "supplier screen added at wafer probe",
        "effectivity": "date codes 2431 onward",
        "corrective_action_verified": True,
    }
    base.update(over)
    return base


def _record(**over):
    base = {
        "nonconformance_id": "NCR-2C-0091",
        "mechanism": "isolated",
        "detection_stage": "incoming-inspection",
        "disposition": "scrap",
        "lot_size": 500,
        "inspected_quantity": 100,
        "failed_quantity": 2,
        "detected_at": "2025-05-02T08:00:00",
        "analysis_started_at": "2025-05-02T12:00:00",
    }
    base.update(over)
    return base


class CategorizationTests(unittest.TestCase):
    def test_a_plain_finding_is_minor(self):
        state = categorize_finding([], "isolated", "incoming-inspection")
        self.assertEqual(state["category"], "minor")
        self.assertEqual(state["reasons"], [])

    def test_a_safety_effect_makes_it_major(self):
        state = categorize_finding(["safety"], "isolated", "incoming-inspection")
        self.assertEqual(state["category"], "major")
        self.assertIn("effect on safety", state["reasons"])

    def test_a_lot_related_escape_is_graded_up(self):
        state = categorize_finding([], "lot-related", "board-assembly-test")
        self.assertEqual(state["category"], "major")
        self.assertTrue(state["escaped_part_screens"])

    def test_a_lot_related_finding_caught_early_stays_minor(self):
        state = categorize_finding([], "lot-related", "part-screening")
        self.assertEqual(state["category"], "minor")
        self.assertFalse(state["escaped_part_screens"])

    def test_duplicate_effects_are_collapsed(self):
        state = categorize_finding(["safety", "safety"], "isolated", "part-screening")
        self.assertEqual(state["effects"], ["safety"])

    def test_unknown_effect_rejected(self):
        with self.assertRaises(ValueError):
            categorize_finding(["cosmetic"], "isolated", "part-screening")

    def test_unknown_stage_rejected(self):
        with self.assertRaises(ValueError):
            categorize_finding([], "isolated", "shipping")

    def test_unknown_mechanism_rejected(self):
        with self.assertRaises(ValueError):
            categorize_finding([], "sporadic", "part-screening")


class AnalysisOwedTests(unittest.TestCase):
    def test_a_minor_isolated_early_finding_owes_nothing(self):
        owed = failure_analysis_required("minor", "isolated", "incoming-inspection")
        self.assertFalse(owed["required"])

    def test_a_major_finding_always_owes_an_analysis(self):
        owed = failure_analysis_required("major", "isolated", "incoming-inspection")
        self.assertTrue(owed["required"])

    def test_a_lot_related_mechanism_owes_an_analysis(self):
        owed = failure_analysis_required("minor", "lot-related", "part-screening")
        self.assertTrue(owed["required"])

    def test_an_unknown_mechanism_owes_an_analysis(self):
        owed = failure_analysis_required("minor", "unknown", "part-screening")
        self.assertTrue(owed["required"])

    def test_recurrence_at_the_threshold_owes_an_analysis(self):
        owed = failure_analysis_required("minor", "isolated", "part-screening", 2, 2)
        self.assertTrue(owed["required"])

    def test_recurrence_below_the_threshold_does_not(self):
        owed = failure_analysis_required("minor", "isolated", "part-screening", 1, 2)
        self.assertFalse(owed["required"])

    def test_a_system_test_escape_owes_an_analysis(self):
        owed = failure_analysis_required("minor", "isolated", "system-test")
        self.assertTrue(owed["required"])

    def test_zero_recurrence_threshold_rejected(self):
        with self.assertRaises(ValueError):
            failure_analysis_required("minor", "isolated", "part-screening", 1, 0)

    def test_negative_recurrence_rejected(self):
        with self.assertRaises(ValueError):
            failure_analysis_required("minor", "isolated", "part-screening", -1)


class DepthTests(unittest.TestCase):
    def test_a_minor_early_finding_owes_the_shallowest_depth(self):
        self.assertEqual(
            owed_analysis_depth("minor", "isolated", "incoming-inspection"),
            "visual-and-electrical",
        )

    def test_a_major_finding_owes_non_destructive_imaging(self):
        self.assertEqual(
            owed_analysis_depth("major", "isolated", "incoming-inspection"),
            "non-destructive-imaging",
        )

    def test_a_board_test_escape_owes_non_destructive_imaging(self):
        self.assertEqual(
            owed_analysis_depth("minor", "isolated", "board-assembly-test"),
            "non-destructive-imaging",
        )

    def test_a_lot_related_mechanism_owes_the_deepest_analysis(self):
        self.assertEqual(
            owed_analysis_depth("minor", "lot-related", "part-screening"),
            "destructive-physical-analysis",
        )

    def test_a_system_test_escape_owes_the_deepest_analysis(self):
        self.assertEqual(
            owed_analysis_depth("minor", "isolated", "system-test"),
            "destructive-physical-analysis",
        )

    def test_recurrence_at_the_threshold_owes_the_deepest_analysis(self):
        self.assertEqual(
            owed_analysis_depth("minor", "isolated", "part-screening", 3, 2),
            "destructive-physical-analysis",
        )

    def test_depth_ladder_is_ordered_shallow_to_deep(self):
        self.assertEqual(ANALYSIS_DEPTHS[0], "visual-and-electrical")
        self.assertEqual(ANALYSIS_DEPTHS[-1], "destructive-physical-analysis")


class CompletenessTests(unittest.TestCase):
    def test_a_full_analysis_at_depth_is_complete(self):
        state = analysis_completeness(_analysis(), "destructive-physical-analysis")
        self.assertTrue(state["complete"])
        self.assertEqual(state["missing"], [])

    def test_a_shallow_analysis_is_short_of_the_owed_depth(self):
        state = analysis_completeness(
            _analysis(depth_performed="visual-and-electrical"),
            "destructive-physical-analysis",
        )
        self.assertIn("depth-below-owed", state["missing"])

    def test_a_deeper_analysis_than_owed_is_accepted(self):
        state = analysis_completeness(_analysis(), "visual-and-electrical")
        self.assertTrue(state["complete"])

    def test_an_unidentified_mechanism_is_named(self):
        state = analysis_completeness(
            _analysis(mechanism_identified=False), "visual-and-electrical"
        )
        self.assertIn("mechanism-not-identified", state["missing"])

    def test_a_missing_effectivity_is_named(self):
        state = analysis_completeness(_analysis(effectivity="  "), "visual-and-electrical")
        self.assertIn("effectivity-not-stated", state["missing"])

    def test_an_unverified_corrective_action_is_named(self):
        state = analysis_completeness(
            _analysis(corrective_action_verified=False), "visual-and-electrical"
        )
        self.assertIn("corrective-action-not-verified", state["missing"])

    def test_every_missing_element_is_reported_not_just_the_first(self):
        state = analysis_completeness(
            _analysis(
                mechanism_identified=False,
                corrective_action=None,
                effectivity=None,
                corrective_action_verified=False,
            ),
            "visual-and-electrical",
        )
        self.assertEqual(len(state["missing"]), 4)

    def test_an_absent_analysis_is_incomplete(self):
        state = analysis_completeness(None, "visual-and-electrical")
        self.assertFalse(state["complete"])
        self.assertIn("no-analysis-performed", state["missing"])

    def test_unknown_performed_depth_rejected(self):
        with self.assertRaises(ValueError):
            analysis_completeness(_analysis(depth_performed="teardown"), "visual-and-electrical")

    def test_non_boolean_verification_flag_rejected(self):
        with self.assertRaises(ValueError):
            analysis_completeness(
                _analysis(corrective_action_verified="yes"), "visual-and-electrical"
            )


class DispositionTests(unittest.TestCase):
    def test_scrap_is_always_permitted(self):
        state = disposition_admissible(
            "scrap", "major", "lot-related", ["safety"], {"complete": False}
        )
        self.assertTrue(state["permitted"])

    def test_a_return_needs_the_part_removed(self):
        state = disposition_admissible(
            "return-to-supplier", "minor", "isolated", [], {"complete": True}, False
        )
        self.assertFalse(state["permitted"])

    def test_a_return_of_a_removed_part_is_permitted(self):
        state = disposition_admissible(
            "return-to-supplier", "minor", "isolated", [], {"complete": True}, True
        )
        self.assertTrue(state["permitted"])

    def test_rework_needs_a_qualified_procedure(self):
        state = disposition_admissible(
            "rework", "minor", "isolated", [], {"complete": True}, False, False
        )
        self.assertFalse(state["permitted"])

    def test_repair_needs_the_analysis_closed(self):
        state = disposition_admissible(
            "repair", "minor", "isolated", [], {"complete": False}, False, True
        )
        self.assertFalse(state["permitted"])

    def test_use_as_is_needs_a_closed_analysis(self):
        state = disposition_admissible(
            "use-as-is", "minor", "isolated", [], {"complete": False}
        )
        self.assertIn(
            "use-as-is needs the failure analysis closed at the owed depth",
            state["refusals"],
        )

    def test_use_as_is_refused_on_a_lot_related_mechanism(self):
        state = disposition_admissible(
            "use-as-is", "minor", "lot-related", [], {"complete": True}
        )
        self.assertFalse(state["permitted"])

    def test_use_as_is_refused_on_a_safety_effect(self):
        state = disposition_admissible(
            "use-as-is", "major", "isolated", ["safety"], {"complete": True}
        )
        self.assertFalse(state["permitted"])

    def test_use_as_is_on_a_closed_isolated_finding_is_permitted(self):
        state = disposition_admissible(
            "use-as-is", "minor", "isolated", [], {"complete": True}
        )
        self.assertTrue(state["permitted"])

    def test_every_refusal_is_collected(self):
        state = disposition_admissible(
            "use-as-is", "major", "lot-related", ["safety"], {"complete": False}
        )
        self.assertEqual(len(state["refusals"]), 3)

    def test_unknown_disposition_rejected(self):
        with self.assertRaises(ValueError):
            disposition_admissible("ignore", "minor", "isolated", [], {"complete": True})

    def test_analysis_state_must_carry_completeness(self):
        with self.assertRaises(ValueError):
            disposition_admissible("scrap", "minor", "isolated", [], {})


class ContainmentTests(unittest.TestCase):
    def test_an_isolated_mechanism_contains_the_failed_parts(self):
        scope = containment_scope("isolated", 500, 100, 3)
        self.assertEqual(scope["contained_quantity"], 3)
        self.assertEqual(scope["uninspected_remainder"], 0)

    def test_a_lot_related_mechanism_contains_the_whole_lot(self):
        scope = containment_scope("lot-related", 500, 100, 3)
        self.assertEqual(scope["contained_quantity"], 500)
        self.assertEqual(scope["uninspected_remainder"], 400)

    def test_sister_lots_join_a_lot_related_containment(self):
        scope = containment_scope("lot-related", 500, 100, 3, [200, 50])
        self.assertEqual(scope["contained_quantity"], 750)
        self.assertEqual(scope["sister_lot_quantity"], 250)

    def test_observed_fraction_is_over_the_inspected_sample(self):
        scope = containment_scope("isolated", 500, 80, 4)
        self.assertAlmostEqual(scope["observed_failure_fraction"], 0.05, places=9)

    def test_a_whole_sample_failure_reads_one(self):
        scope = containment_scope("isolated", 500, 40, 40)
        self.assertAlmostEqual(scope["observed_failure_fraction"], 1.0, places=9)

    def test_failed_beyond_inspected_rejected(self):
        with self.assertRaises(ValueError):
            containment_scope("isolated", 500, 10, 11)

    def test_inspected_beyond_the_lot_rejected(self):
        with self.assertRaises(ValueError):
            containment_scope("isolated", 100, 101, 1)

    def test_zero_inspected_rejected(self):
        with self.assertRaises(ValueError):
            containment_scope("isolated", 100, 0, 0)

    def test_zero_sister_lot_rejected(self):
        with self.assertRaises(ValueError):
            containment_scope("lot-related", 100, 10, 1, [0])


class TimelinessTests(unittest.TestCase):
    def test_a_prompt_start_is_on_time(self):
        state = response_timeliness(
            "2025-05-02T08:00:00", "2025-05-02T12:00:00", "major"
        )
        self.assertTrue(state["on_time"])
        self.assertAlmostEqual(state["elapsed_hours"], 4.0, places=9)

    def test_a_start_exactly_on_the_deadline_is_on_time(self):
        state = response_timeliness(
            "2025-05-02T08:00:00", "2025-05-03T08:00:00", "major"
        )
        self.assertAlmostEqual(state["elapsed_hours"], RESPONSE_HOURS["major"], places=9)
        self.assertTrue(state["on_time"])
        self.assertAlmostEqual(state["overrun_hours"], 0.0, places=9)

    def test_a_late_start_reports_its_overrun(self):
        state = response_timeliness(
            "2025-05-02T08:00:00", "2025-05-04T08:00:00", "major"
        )
        self.assertFalse(state["on_time"])
        self.assertAlmostEqual(state["overrun_hours"], 24.0, places=9)

    def test_a_minor_finding_gets_the_longer_window(self):
        state = response_timeliness(
            "2025-05-02T08:00:00", "2025-05-04T08:00:00", "minor"
        )
        self.assertTrue(state["on_time"])

    def test_datetime_objects_accepted(self):
        state = response_timeliness(
            datetime.datetime(2025, 5, 2, 8), datetime.datetime(2025, 5, 2, 9), "major"
        )
        self.assertAlmostEqual(state["elapsed_hours"], 1.0, places=9)

    def test_a_start_before_detection_rejected(self):
        with self.assertRaises(ValueError):
            response_timeliness("2025-05-02T08:00:00", "2025-05-01T08:00:00", "major")

    def test_malformed_timestamp_rejected(self):
        with self.assertRaises(ValueError):
            response_timeliness("02/05/2025 08:00", "2025-05-02T12:00:00", "major")

    def test_non_positive_owed_window_rejected(self):
        with self.assertRaises(ValueError):
            response_timeliness(
                "2025-05-02T08:00:00", "2025-05-02T09:00:00", "major", {"major": 0.0}
            )


class AssessmentTests(unittest.TestCase):
    def test_a_minor_isolated_scrap_closes(self):
        result = assess_class_two_nonconformance(_record())
        self.assertEqual(result["verdict"], "closed")
        self.assertTrue(result["closed"])
        self.assertFalse(result["analysis_required"])

    def test_a_safety_finding_without_analysis_is_incomplete(self):
        result = assess_class_two_nonconformance(_record(effects=["safety"]))
        self.assertEqual(result["category"], "major")
        self.assertEqual(result["verdict"], "failure-analysis-incomplete")

    def test_a_closed_analysis_on_a_lot_related_finding_contains_the_lot(self):
        result = assess_class_two_nonconformance(
            _record(
                mechanism="lot-related",
                detection_stage="board-assembly-test",
                analysis=_analysis(),
                detected_at="2025-05-02T08:00:00",
                analysis_started_at="2025-05-02T10:00:00",
            )
        )
        self.assertEqual(result["verdict"], "closed-with-lot-containment")
        self.assertEqual(result["containment"]["contained_quantity"], 500)

    def test_use_as_is_on_an_open_analysis_is_refused(self):
        result = assess_class_two_nonconformance(
            _record(disposition="use-as-is", effects=["mission-reliability"])
        )
        self.assertEqual(result["verdict"], "disposition-refused")

    def test_a_late_start_on_a_major_finding_is_named(self):
        result = assess_class_two_nonconformance(
            _record(
                effects=["interchangeability"],
                analysis=_analysis(depth_performed="non-destructive-imaging"),
                analysis_started_at="2025-05-05T08:00:00",
            )
        )
        self.assertEqual(result["verdict"], "response-late")

    def test_the_owed_depth_travels_with_the_verdict(self):
        result = assess_class_two_nonconformance(
            _record(mechanism="lot-related", detection_stage="system-test")
        )
        self.assertEqual(result["owed_analysis_depth"], "destructive-physical-analysis")

    def test_recurrence_deepens_the_owed_analysis(self):
        result = assess_class_two_nonconformance(
            _record(recurrence_count=4, recurrence_threshold=2)
        )
        self.assertEqual(result["owed_analysis_depth"], "destructive-physical-analysis")

    def test_the_observed_fraction_is_reported(self):
        result = assess_class_two_nonconformance(
            _record(inspected_quantity=50, failed_quantity=5)
        )
        self.assertAlmostEqual(
            result["containment"]["observed_failure_fraction"], 0.1, places=9
        )

    def test_a_rework_without_a_procedure_is_refused(self):
        result = assess_class_two_nonconformance(_record(disposition="rework"))
        self.assertEqual(result["verdict"], "disposition-refused")

    def test_a_rework_with_a_procedure_closes(self):
        result = assess_class_two_nonconformance(
            _record(disposition="rework", qualified_procedure=True)
        )
        self.assertEqual(result["verdict"], "closed")

    def test_tolerance_is_the_documented_size(self):
        self.assertAlmostEqual(BOUND_TOLERANCE, 1e-9, places=12)

    def test_missing_record_key_rejected(self):
        record = _record()
        del record["lot_size"]
        with self.assertRaises(ValueError):
            assess_class_two_nonconformance(record)

    def test_blank_identity_rejected(self):
        with self.assertRaises(ValueError):
            assess_class_two_nonconformance(_record(nonconformance_id="   "))

    def test_record_must_be_a_mapping(self):
        with self.assertRaises(ValueError):
            assess_class_two_nonconformance([_record()])


if __name__ == "__main__":
    unittest.main(verbosity=1)
