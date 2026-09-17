"""Contract tests for the clause 5.5.2 class 2 nonconformance control logic."""

import unittest

from q60_class_2_nonconformance_control_logic import (
    GRADE_CLOSURE_DAYS,
    GRADE_DISPOSITIONS,
    MODE_FAMILIES,
    RECURRENCE_THRESHOLD,
    RECURRENCE_WINDOW_DAYS,
    allowed_dispositions,
    approval_chain,
    assess_class_2_nonconformance,
    closure_state,
    containment_lots,
    escalated_handling,
    failure_analysis_required,
    grade_nonconformance,
    recurrence_rate,
    recurrence_state,
    working_days_between,
)


def _report(**over):
    base = {
        "lot_id": "LOT-A",
        "part_number": "SN74LV00A",
        "manufacturer": "Northgate Semiconductor",
        "date_code": "2418",
        "failure_mode": "output-stuck-low",
        "mode_family": "lot-related",
        "effect": "parametric-drift",
        "reach": "stores",
        "safety_consequence": False,
        "usage_criticality": "non-critical",
        "single_point_failure": False,
        "raised_on": "2026-03-02",
    }
    base.update(over)
    return base


INVENTORY = [
    {"lot_id": "LOT-A", "part_number": "SN74LV00A",
     "manufacturer": "Northgate Semiconductor", "date_code": "2418"},
    {"lot_id": "LOT-B", "part_number": "SN74LV00A",
     "manufacturer": "Northgate Semiconductor", "date_code": "2418"},
    {"lot_id": "LOT-C", "part_number": "SN74LV00A",
     "manufacturer": "Northgate Semiconductor", "date_code": "2530"},
    {"lot_id": "LOT-D", "part_number": "SN74LV00A",
     "manufacturer": "Eastvale Devices", "date_code": "2418"},
    {"lot_id": "LOT-E", "part_number": "AD8021",
     "manufacturer": "Northgate Semiconductor", "date_code": "2418"},
]


class EscalationTests(unittest.TestCase):
    def test_a_non_critical_usage_does_not_escalate(self):
        self.assertFalse(escalated_handling(_report()))

    def test_a_safety_critical_usage_escalates(self):
        self.assertTrue(escalated_handling(_report(usage_criticality="safety-critical")))

    def test_a_single_point_failure_escalates(self):
        self.assertTrue(escalated_handling(_report(single_point_failure=True)))

    def test_a_mission_critical_usage_alone_does_not_escalate(self):
        self.assertFalse(
            escalated_handling(_report(usage_criticality="mission-critical"))
        )

    def test_an_unknown_criticality_rejected(self):
        with self.assertRaises(ValueError):
            escalated_handling(_report(usage_criticality="somewhat-critical"))

    def test_report_must_be_a_mapping(self):
        with self.assertRaises(ValueError):
            escalated_handling(["LOT-A"])


class GradingTests(unittest.TestCase):
    def test_a_cosmetic_report_in_stores_is_minor(self):
        self.assertEqual(grade_nonconformance(_report(effect="cosmetic")), "minor")

    def test_a_functional_failure_is_major(self):
        self.assertEqual(
            grade_nonconformance(_report(effect="functional-failure")), "major"
        )

    def test_an_out_of_specification_part_in_stores_stays_minor(self):
        self.assertEqual(
            grade_nonconformance(_report(effect="out-of-specification")), "minor"
        )

    def test_the_same_part_already_assembled_is_major(self):
        self.assertEqual(
            grade_nonconformance(
                _report(effect="out-of-specification", reach="assembled")
            ),
            "major",
        )

    def test_a_safety_consequence_is_critical_whatever_the_effect(self):
        self.assertEqual(
            grade_nonconformance(_report(effect="cosmetic", safety_consequence=True)),
            "critical",
        )

    def test_escalation_lifts_a_minor_report_to_major(self):
        self.assertEqual(
            grade_nonconformance(_report(single_point_failure=True)), "major"
        )

    def test_escalation_lifts_a_major_report_to_critical(self):
        self.assertEqual(
            grade_nonconformance(
                _report(effect="functional-failure",
                        usage_criticality="safety-critical")
            ),
            "critical",
        )

    def test_an_unknown_effect_rejected(self):
        with self.assertRaises(ValueError):
            grade_nonconformance(_report(effect="smells-odd"))

    def test_an_unknown_reach_rejected(self):
        with self.assertRaises(ValueError):
            grade_nonconformance(_report(reach="in-a-drawer"))

    def test_a_non_boolean_safety_consequence_rejected(self):
        with self.assertRaises(ValueError):
            grade_nonconformance(_report(safety_consequence="yes"))


class DispositionTests(unittest.TestCase):
    def test_a_minor_report_may_be_used_as_is(self):
        self.assertIn("use-as-is", allowed_dispositions("minor"))

    def test_a_critical_report_may_never_be_used_as_is(self):
        self.assertNotIn("use-as-is", allowed_dispositions("critical"))

    def test_a_critical_report_may_only_leave_or_be_scrapped(self):
        self.assertEqual(sorted(allowed_dispositions("critical")),
                         ["return-to-supplier", "scrap"])

    def test_every_grade_offers_at_least_one_disposition(self):
        for grade in GRADE_DISPOSITIONS:
            self.assertTrue(allowed_dispositions(grade))

    def test_an_unknown_grade_rejected(self):
        with self.assertRaises(ValueError):
            allowed_dispositions("catastrophic")


class ApprovalTests(unittest.TestCase):
    def test_a_minor_use_as_is_needs_product_assurance_only(self):
        self.assertEqual(approval_chain("minor", "use-as-is"), ["product-assurance"])

    def test_a_major_use_as_is_reaches_the_customer(self):
        self.assertIn("customer", approval_chain("major", "use-as-is"))

    def test_a_major_scrap_does_not_reach_the_customer(self):
        self.assertNotIn("customer", approval_chain("major", "scrap"))

    def test_a_critical_scrap_reaches_the_customer(self):
        self.assertIn("customer", approval_chain("critical", "scrap"))

    def test_the_parts_control_board_signs_every_major_disposition(self):
        for choice in GRADE_DISPOSITIONS["major"]:
            self.assertIn("parts-control-board", approval_chain("major", choice))

    def test_a_disposition_outside_the_grade_rejected(self):
        with self.assertRaises(ValueError):
            approval_chain("critical", "use-as-is")


class FailureAnalysisTests(unittest.TestCase):
    def test_a_major_report_always_owes_an_analysis(self):
        self.assertTrue(failure_analysis_required(_report(), "major"))

    def test_a_critical_report_always_owes_an_analysis(self):
        self.assertTrue(failure_analysis_required(_report(), "critical"))

    def test_a_plain_minor_report_does_not(self):
        self.assertFalse(failure_analysis_required(_report(), "minor"))

    def test_a_minor_functional_failure_still_owes_one(self):
        self.assertTrue(
            failure_analysis_required(_report(effect="functional-failure"), "minor")
        )

    def test_a_systematic_minor_report_owes_one(self):
        self.assertTrue(failure_analysis_required(_report(), "minor", True))

    def test_a_non_boolean_systematic_flag_rejected(self):
        with self.assertRaises(ValueError):
            failure_analysis_required(_report(), "minor", "yes")


class ContainmentTests(unittest.TestCase):
    def test_a_lot_related_mode_impounds_the_same_date_code(self):
        self.assertEqual(containment_lots(_report(), INVENTORY), ["LOT-B"])

    def test_a_design_related_mode_reaches_every_date_code(self):
        impounded = containment_lots(_report(mode_family="design-related"), INVENTORY)
        self.assertEqual(impounded, ["LOT-B", "LOT-C"])

    def test_an_assembly_induced_mode_impounds_nothing(self):
        self.assertEqual(
            containment_lots(_report(mode_family="assembly-induced"), INVENTORY), []
        )

    def test_a_handling_induced_mode_impounds_nothing(self):
        self.assertEqual(
            containment_lots(_report(mode_family="handling-induced"), INVENTORY), []
        )

    def test_a_second_source_part_is_never_swept_in(self):
        impounded = containment_lots(_report(mode_family="design-related"), INVENTORY)
        self.assertNotIn("LOT-D", impounded)

    def test_another_part_number_is_never_swept_in(self):
        impounded = containment_lots(_report(mode_family="design-related"), INVENTORY)
        self.assertNotIn("LOT-E", impounded)

    def test_the_failing_lot_is_not_listed_as_its_own_sibling(self):
        self.assertNotIn("LOT-A", containment_lots(_report(), INVENTORY))

    def test_every_mode_family_is_handled(self):
        for family in MODE_FAMILIES:
            containment_lots(_report(mode_family=family), INVENTORY)

    def test_an_unknown_mode_family_rejected(self):
        with self.assertRaises(ValueError):
            containment_lots(_report(mode_family="cosmic"), INVENTORY)

    def test_inventory_must_be_a_sequence(self):
        with self.assertRaises(ValueError):
            containment_lots(_report(), "LOT-B")


class RecurrenceTests(unittest.TestCase):
    def _history(self, *dates):
        return [
            {"failure_mode": "output-stuck-low", "part_number": "SN74LV00A",
             "raised_on": date}
            for date in dates
        ]

    def test_a_single_occurrence_is_not_systematic(self):
        state = recurrence_state(_report(), self._history("2026-03-02"), "2026-03-02")
        self.assertFalse(state["systematic"])

    def test_the_threshold_makes_a_mode_systematic(self):
        dates = ["2026-01-05", "2026-02-09", "2026-03-02"]
        self.assertEqual(len(dates), RECURRENCE_THRESHOLD)
        state = recurrence_state(_report(), self._history(*dates), "2026-03-02")
        self.assertTrue(state["systematic"])

    def test_an_occurrence_outside_the_window_is_not_counted(self):
        state = recurrence_state(
            _report(), self._history("2024-01-05", "2026-02-09", "2026-03-02"),
            "2026-03-02",
        )
        self.assertEqual(state["occurrences_in_window"], 2)

    def test_another_failure_mode_is_not_counted(self):
        history = self._history("2026-02-09")
        history.append({"failure_mode": "open-circuit-bond",
                        "part_number": "SN74LV00A", "raised_on": "2026-02-10"})
        state = recurrence_state(_report(), history, "2026-03-02")
        self.assertEqual(state["occurrences_in_window"], 1)

    def test_another_part_number_is_not_counted(self):
        history = self._history("2026-02-09")
        history.append({"failure_mode": "output-stuck-low",
                        "part_number": "AD8021", "raised_on": "2026-02-10"})
        state = recurrence_state(_report(), history, "2026-03-02")
        self.assertEqual(state["occurrences_in_window"], 1)

    def test_the_window_is_the_documented_length(self):
        self.assertEqual(RECURRENCE_WINDOW_DAYS, 365)

    def test_the_window_bounds_are_reported(self):
        state = recurrence_state(
            _report(), self._history("2026-01-05", "2026-03-02"), "2026-03-02"
        )
        self.assertEqual(state["first_in_window"], "2026-01-05")
        self.assertEqual(state["last_in_window"], "2026-03-02")

    def test_an_empty_history_reports_no_bounds(self):
        state = recurrence_state(_report(), [], "2026-03-02")
        self.assertIsNone(state["first_in_window"])
        self.assertIsNone(state["last_in_window"])

    def test_a_malformed_date_rejected(self):
        with self.assertRaises(ValueError):
            recurrence_state(_report(), self._history("02-03-2026"), "2026-03-02")

    def test_history_must_be_a_sequence(self):
        with self.assertRaises(ValueError):
            recurrence_state(_report(), "2026-03-02", "2026-03-02")

    def test_a_non_positive_window_rejected(self):
        with self.assertRaises(ValueError):
            recurrence_state(_report(), [], "2026-03-02", 0)


class RecurrenceRateTests(unittest.TestCase):
    def test_no_occurrence_reads_zero(self):
        self.assertAlmostEqual(recurrence_rate(0, 8), 0.0, places=9)

    def test_every_lot_affected_reads_one(self):
        self.assertAlmostEqual(recurrence_rate(8, 8), 1.0, places=9)

    def test_a_quarter_of_the_lots_reads_a_quarter(self):
        self.assertAlmostEqual(recurrence_rate(2, 8), 0.25, places=9)

    def test_more_occurrences_than_lots_rejected(self):
        with self.assertRaises(ValueError):
            recurrence_rate(9, 8)

    def test_no_lots_examined_rejected(self):
        with self.assertRaises(ValueError):
            recurrence_rate(0, 0)

    def test_a_non_integer_count_rejected(self):
        with self.assertRaises(ValueError):
            recurrence_rate(2.0, 8)


class ClosureTests(unittest.TestCase):
    def test_working_days_skip_the_weekend(self):
        self.assertEqual(working_days_between("2026-03-06", "2026-03-09"), 1)

    def test_a_same_day_closure_uses_no_working_day(self):
        self.assertEqual(working_days_between("2026-03-02", "2026-03-02"), 0)

    def test_a_full_week_counts_five(self):
        self.assertEqual(working_days_between("2026-03-02", "2026-03-09"), 5)

    def test_a_closing_date_before_the_raising_date_rejected(self):
        with self.assertRaises(ValueError):
            working_days_between("2026-03-09", "2026-03-02")

    def test_a_critical_report_has_the_shortest_deadline(self):
        self.assertLess(GRADE_CLOSURE_DAYS["critical"], GRADE_CLOSURE_DAYS["minor"])

    def test_a_prompt_closure_is_within_the_deadline(self):
        state = closure_state("critical", "2026-03-02", "2026-03-05")
        self.assertTrue(state["within_deadline"])
        self.assertTrue(state["closed"])

    def test_an_open_report_still_accrues_working_days(self):
        state = closure_state("critical", "2026-03-02", None, "2026-03-20")
        self.assertFalse(state["closed"])
        self.assertFalse(state["within_deadline"])
        self.assertGreater(state["overdue_by"], 0)

    def test_a_closure_state_needs_an_endpoint(self):
        with self.assertRaises(ValueError):
            closure_state("minor", "2026-03-02")


class AssessmentTests(unittest.TestCase):
    def test_a_routine_report_reads_minor_and_contained(self):
        result = assess_class_2_nonconformance(_report(), INVENTORY, [], "2026-03-02")
        self.assertEqual(result["grade"], "minor")
        self.assertEqual(result["impounded_lots"], ["LOT-B"])
        self.assertFalse(result["failure_analysis_required"])

    def test_a_safety_report_reads_critical_and_owes_an_analysis(self):
        result = assess_class_2_nonconformance(
            _report(safety_consequence=True), INVENTORY, [], "2026-03-02"
        )
        self.assertEqual(result["grade"], "critical")
        self.assertTrue(result["failure_analysis_required"])
        self.assertNotIn("use-as-is", result["allowed_dispositions"])

    def test_a_chosen_disposition_carries_its_approval_chain(self):
        result = assess_class_2_nonconformance(
            _report(effect="functional-failure"), INVENTORY, [], "2026-03-02",
            "use-as-is",
        )
        self.assertIn("customer", result["approval_chain"])

    def test_no_chosen_disposition_leaves_the_chain_empty(self):
        result = assess_class_2_nonconformance(_report(), INVENTORY, [], "2026-03-02")
        self.assertEqual(result["approval_chain"], [])

    def test_a_systematic_mode_is_reported(self):
        history = [
            {"failure_mode": "output-stuck-low", "part_number": "SN74LV00A",
             "raised_on": date}
            for date in ("2026-01-05", "2026-02-09", "2026-03-02")
        ]
        result = assess_class_2_nonconformance(_report(), INVENTORY, history,
                                               "2026-03-02")
        self.assertTrue(result["recurrence"]["systematic"])
        self.assertTrue(result["failure_analysis_required"])

    def test_the_escalation_flag_is_reported(self):
        result = assess_class_2_nonconformance(
            _report(single_point_failure=True), INVENTORY, [], "2026-03-02"
        )
        self.assertTrue(result["escalated"])
        self.assertEqual(result["grade"], "major")

    def test_a_disposition_outside_the_grade_rejected(self):
        with self.assertRaises(ValueError):
            assess_class_2_nonconformance(
                _report(safety_consequence=True), INVENTORY, [], "2026-03-02",
                "use-as-is",
            )

    def test_report_must_be_a_mapping(self):
        with self.assertRaises(ValueError):
            assess_class_2_nonconformance([_report()], INVENTORY, [], "2026-03-02")


if __name__ == "__main__":
    unittest.main(verbosity=1)
