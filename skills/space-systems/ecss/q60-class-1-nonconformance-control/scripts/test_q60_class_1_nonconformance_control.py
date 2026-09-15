"""Contract tests for the clause 4.5.2 nonconformance and failure control logic."""

import unittest

from q60_class_1_nonconformance_control_logic import (
    EFFECT_CATEGORIES,
    GRADE_CLOSURE_DAYS,
    GRADE_DISPOSITIONS,
    RECURRENCE_THRESHOLD,
    allowed_dispositions,
    approval_chain,
    assess_nonconformance,
    containment_lots,
    failure_analysis_required,
    grade_nonconformance,
    recurrence_state,
    working_days_between,
)


def base_report(**overrides):
    """Return a minor parametric report raised on a Monday and closed on time."""
    report = {
        "report_id": "NCR-2026-118",
        "lot_id": "LOT-A",
        "part_number": "rh1020-ccg84b",
        "wafer_lot": "W-7741",
        "date_code": "2336",
        "effect": "parametric-drift",
        "reach": "stores",
        "failure_mode": "Threshold Shift",
        "quantity": 12,
        "safety_relevant": False,
        "raised_date": "2026-09-07",
        "proposed_disposition": "rework",
        "signatures": ["product-assurance"],
        "closed_date": "2026-09-18",
    }
    report.update(overrides)
    return report


def inventory():
    return [
        {"lot_id": "LOT-A", "part_number": "RH1020-CCG84B", "wafer_lot": "W-7741"},
        {"lot_id": "LOT-B", "part_number": "RH1020-CCG84B", "wafer_lot": "W-7741"},
        {"lot_id": "LOT-C", "part_number": "RH1020-CCG84B", "date_code": "2336"},
        {"lot_id": "LOT-D", "part_number": "RH1020-CCG84B", "wafer_lot": "W-9002"},
        {"lot_id": "LOT-E", "part_number": "OTHER-PART", "wafer_lot": "W-7741"},
    ]


class GradeTests(unittest.TestCase):
    def test_cosmetic_defect_in_stores_is_minor(self):
        self.assertEqual(grade_nonconformance("cosmetic", "stores", False), "minor")

    def test_out_of_specification_is_major(self):
        self.assertEqual(
            grade_nonconformance("out-of-specification", "incoming", False), "major"
        )

    def test_functional_failure_is_major(self):
        self.assertEqual(
            grade_nonconformance("functional-failure", "incoming", False), "major"
        )

    def test_escape_into_assembled_hardware_is_major(self):
        self.assertEqual(grade_nonconformance("cosmetic", "assembled", False), "major")

    def test_safety_relevance_overrides_a_paperwork_effect(self):
        self.assertEqual(
            grade_nonconformance("documentation-only", "incoming", True), "major"
        )

    def test_unknown_effect_rejected(self):
        with self.assertRaises(ValueError):
            grade_nonconformance("scratched-lid", "stores", False)

    def test_unknown_reach_rejected(self):
        with self.assertRaises(ValueError):
            grade_nonconformance("cosmetic", "in-orbit", False)

    def test_non_boolean_safety_flag_rejected(self):
        with self.assertRaises(ValueError):
            grade_nonconformance("cosmetic", "stores", "yes")

    def test_effect_order_is_monotone(self):
        self.assertLess(
            EFFECT_CATEGORIES["cosmetic"], EFFECT_CATEGORIES["functional-failure"]
        )


class DispositionTests(unittest.TestCase):
    def test_minor_dispositions_exclude_repair(self):
        self.assertNotIn("repair", allowed_dispositions("minor"))

    def test_major_dispositions_include_repair(self):
        self.assertIn("repair", allowed_dispositions("major"))

    def test_unknown_grade_rejected(self):
        with self.assertRaises(ValueError):
            allowed_dispositions("critical")

    def test_minor_use_as_is_needs_only_product_assurance(self):
        self.assertEqual(approval_chain("minor", "use-as-is"), ("product-assurance",))

    def test_major_use_as_is_needs_the_board_and_the_customer(self):
        chain = approval_chain("major", "use-as-is")
        self.assertIn("failure-review-board", chain)
        self.assertIn("customer", chain)

    def test_major_scrap_does_not_need_the_customer(self):
        self.assertNotIn("customer", approval_chain("major", "scrap"))

    def test_disposition_outside_the_grade_rejected(self):
        with self.assertRaises(ValueError):
            approval_chain("minor", "repair")

    def test_every_allowed_disposition_has_an_approval_chain(self):
        for grade, dispositions in GRADE_DISPOSITIONS.items():
            for disposition in dispositions:
                self.assertTrue(approval_chain(grade, disposition))


class FailureAnalysisTests(unittest.TestCase):
    def test_functional_failure_always_owes_an_analysis(self):
        self.assertTrue(failure_analysis_required("functional-failure", "major"))

    def test_major_parametric_drift_owes_an_analysis(self):
        self.assertTrue(failure_analysis_required("parametric-drift", "major"))

    def test_minor_cosmetic_defect_does_not(self):
        self.assertFalse(failure_analysis_required("cosmetic", "minor"))

    def test_major_paperwork_report_does_not(self):
        self.assertFalse(failure_analysis_required("documentation-only", "major"))

    def test_unknown_grade_rejected(self):
        with self.assertRaises(ValueError):
            failure_analysis_required("cosmetic", "severe")


class ContainmentTests(unittest.TestCase):
    def test_failing_lot_is_always_contained(self):
        contained = containment_lots(
            {"lot_id": "LOT-A", "part_number": "RH1020-CCG84B", "wafer_lot": "W-7741"},
            inventory(),
        )
        self.assertEqual(contained[0], "LOT-A")

    def test_same_wafer_lot_is_pulled_in(self):
        contained = containment_lots(
            {"lot_id": "LOT-A", "part_number": "RH1020-CCG84B", "wafer_lot": "W-7741"},
            inventory(),
        )
        self.assertIn("LOT-B", contained)

    def test_same_date_code_is_pulled_in(self):
        contained = containment_lots(
            {
                "lot_id": "LOT-A",
                "part_number": "RH1020-CCG84B",
                "wafer_lot": "W-7741",
                "date_code": "2336",
            },
            inventory(),
        )
        self.assertIn("LOT-C", contained)

    def test_different_wafer_lot_is_left_alone(self):
        contained = containment_lots(
            {"lot_id": "LOT-A", "part_number": "RH1020-CCG84B", "wafer_lot": "W-7741"},
            inventory(),
        )
        self.assertNotIn("LOT-D", contained)

    def test_same_wafer_lot_on_another_part_number_is_left_alone(self):
        contained = containment_lots(
            {"lot_id": "LOT-A", "part_number": "RH1020-CCG84B", "wafer_lot": "W-7741"},
            inventory(),
        )
        self.assertNotIn("LOT-E", contained)

    def test_lot_records_without_a_part_number_rejected(self):
        with self.assertRaises(ValueError):
            containment_lots(
                {"lot_id": "LOT-A", "part_number": "RH1020-CCG84B"},
                [{"lot_id": "LOT-B"}],
            )

    def test_inventory_must_be_a_sequence(self):
        with self.assertRaises(ValueError):
            containment_lots(
                {"lot_id": "LOT-A", "part_number": "RH1020-CCG84B"},
                {"lot_id": "LOT-B"},
            )


class RecurrenceTests(unittest.TestCase):
    def history(self):
        return [
            {
                "part_number": "RH1020-CCG84B",
                "failure_mode": "threshold shift",
                "raised_date": "2026-03-02",
            },
            {
                "part_number": "RH1020-CCG84B",
                "failure_mode": "Threshold Shift",
                "raised_date": "2026-06-15",
            },
            {
                "part_number": "RH1020-CCG84B",
                "failure_mode": "threshold shift",
                "raised_date": "2024-01-08",
            },
            {
                "part_number": "RH1020-CCG84B",
                "failure_mode": "seal leak",
                "raised_date": "2026-05-05",
            },
        ]

    def test_matching_mode_inside_the_window_counts(self):
        state = recurrence_state(
            "RH1020-CCG84B", "threshold shift", self.history(), "2026-09-14"
        )
        self.assertEqual(state["occurrences_in_window"], 2)

    def test_case_differences_do_not_split_a_mode(self):
        state = recurrence_state(
            "rh1020-ccg84b", "Threshold Shift", self.history(), "2026-09-14"
        )
        self.assertEqual(state["occurrences_in_window"], 2)

    def test_an_entry_older_than_the_window_is_excluded(self):
        state = recurrence_state(
            "RH1020-CCG84B", "threshold shift", self.history(), "2026-09-14"
        )
        self.assertNotIn("2024-01-08", state["occurrence_dates"])

    def test_below_threshold_is_not_systematic(self):
        state = recurrence_state(
            "RH1020-CCG84B", "threshold shift", self.history(), "2026-09-14"
        )
        self.assertFalse(state["systematic"])

    def test_reaching_the_threshold_is_systematic(self):
        history = self.history() + [
            {
                "part_number": "RH1020-CCG84B",
                "failure_mode": "threshold shift",
                "raised_date": "2026-08-03",
            }
        ]
        state = recurrence_state(
            "RH1020-CCG84B", "threshold shift", history, "2026-09-14"
        )
        self.assertEqual(state["occurrences_in_window"], RECURRENCE_THRESHOLD)
        self.assertTrue(state["systematic"])

    def test_another_mode_does_not_count(self):
        state = recurrence_state(
            "RH1020-CCG84B", "seal leak", self.history(), "2026-09-14"
        )
        self.assertEqual(state["occurrences_in_window"], 1)

    def test_a_future_dated_history_entry_is_rejected(self):
        history = [
            {
                "part_number": "RH1020-CCG84B",
                "failure_mode": "threshold shift",
                "raised_date": "2027-01-01",
            }
        ]
        with self.assertRaises(ValueError):
            recurrence_state("RH1020-CCG84B", "threshold shift", history, "2026-09-14")

    def test_empty_failure_mode_rejected(self):
        with self.assertRaises(ValueError):
            recurrence_state("RH1020-CCG84B", "  ", self.history(), "2026-09-14")


class WorkingDayTests(unittest.TestCase):
    def test_monday_to_friday_is_four_working_days(self):
        self.assertEqual(working_days_between("2026-09-07", "2026-09-11"), 4)

    def test_a_weekend_adds_nothing(self):
        self.assertEqual(working_days_between("2026-09-11", "2026-09-13"), 0)

    def test_same_day_is_zero(self):
        self.assertEqual(working_days_between("2026-09-07", "2026-09-07"), 0)

    def test_reversed_dates_rejected(self):
        with self.assertRaises(ValueError):
            working_days_between("2026-09-11", "2026-09-07")

    def test_malformed_date_rejected(self):
        with self.assertRaises(ValueError):
            working_days_between("07-09-2026", "2026-09-11")


class AssessNonconformanceTests(unittest.TestCase):
    def test_clean_minor_report_is_closeable(self):
        result = assess_nonconformance(base_report(), inventory(), [], "2026-09-21")
        self.assertEqual(result["grade"], "minor")
        self.assertEqual(result["findings"], [])
        self.assertTrue(result["closeable"])

    def test_sibling_lots_are_reported_with_the_failing_lot(self):
        result = assess_nonconformance(base_report(), inventory(), [], "2026-09-21")
        self.assertEqual(result["contained_lot_count"], 3)
        self.assertTrue(any("sibling lot" in note for note in result["notes"]))

    def test_functional_failure_without_an_analysis_raises_a_finding(self):
        result = assess_nonconformance(
            base_report(effect="functional-failure", proposed_disposition="scrap",
                        signatures=["product-assurance", "failure-review-board"]),
            inventory(),
            [],
            "2026-09-21",
        )
        self.assertTrue(result["failure_analysis_required"])
        self.assertTrue(
            any("owes a failure analysis" in f for f in result["findings"])
        )

    def test_missing_customer_signature_on_a_major_use_as_is(self):
        result = assess_nonconformance(
            base_report(
                effect="functional-failure",
                proposed_disposition="use-as-is",
                failure_analysis_reference="FA-2026-07",
                signatures=["product-assurance", "failure-review-board"],
            ),
            inventory(),
            [],
            "2026-09-21",
        )
        self.assertIn("customer", result["required_signatures"])
        self.assertTrue(any("customer" in f for f in result["findings"]))

    def test_disposition_outside_the_grade_raises_a_finding(self):
        result = assess_nonconformance(
            base_report(proposed_disposition="repair"), inventory(), [], "2026-09-21"
        )
        self.assertTrue(any("is not open to" in f for f in result["findings"]))
        self.assertFalse(result["closeable"])

    def test_an_open_report_keeps_accruing_working_days(self):
        result = assess_nonconformance(
            base_report(closed_date=None), inventory(), [], "2026-09-21"
        )
        self.assertEqual(result["closure_state"], "open")
        self.assertEqual(result["closure_working_days"], 10)

    def test_a_major_report_gets_the_shorter_deadline(self):
        result = assess_nonconformance(
            base_report(
                effect="functional-failure",
                proposed_disposition="scrap",
                failure_analysis_reference="FA-2026-07",
                signatures=["product-assurance", "failure-review-board"],
            ),
            inventory(),
            [],
            "2026-09-21",
        )
        self.assertEqual(result["closure_deadline_days"], GRADE_CLOSURE_DAYS["major"])

    def test_overrunning_the_deadline_raises_a_finding(self):
        result = assess_nonconformance(
            base_report(
                effect="functional-failure",
                proposed_disposition="scrap",
                failure_analysis_reference="FA-2026-07",
                signatures=["product-assurance", "failure-review-board"],
                closed_date="2026-10-05",
            ),
            inventory(),
            [],
            "2026-10-05",
        )
        self.assertFalse(result["within_deadline"])
        self.assertTrue(any("working days against" in f for f in result["findings"]))

    def test_delivered_hardware_owes_an_in_service_statement(self):
        result = assess_nonconformance(
            base_report(reach="delivered", proposed_disposition="scrap",
                        failure_analysis_reference="FA-2026-07",
                        signatures=["product-assurance", "failure-review-board"]),
            inventory(),
            [],
            "2026-09-21",
        )
        self.assertTrue(any("already delivered" in f for f in result["findings"]))

    def test_a_systematic_mode_escalates_beyond_the_project(self):
        history = [
            {
                "part_number": "RH1020-CCG84B",
                "failure_mode": "threshold shift",
                "raised_date": date,
            }
            for date in ("2026-02-02", "2026-05-04", "2026-08-03")
        ]
        result = assess_nonconformance(
            base_report(), inventory(), history, "2026-09-21"
        )
        self.assertEqual(result["escalation"], "corrective-action-board")

    def test_missing_proposed_disposition_raises_a_finding(self):
        result = assess_nonconformance(
            base_report(proposed_disposition=None), inventory(), [], "2026-09-21"
        )
        self.assertTrue(any("no proposed disposition" in f for f in result["findings"]))

    def test_as_of_before_the_raised_date_rejected(self):
        with self.assertRaises(ValueError):
            assess_nonconformance(base_report(), inventory(), [], "2026-09-01")

    def test_zero_quantity_rejected(self):
        with self.assertRaises(ValueError):
            assess_nonconformance(
                base_report(quantity=0), inventory(), [], "2026-09-21"
            )

    def test_missing_required_key_rejected(self):
        report = base_report()
        del report["failure_mode"]
        with self.assertRaises(ValueError):
            assess_nonconformance(report, inventory(), [], "2026-09-21")

    def test_report_must_be_a_mapping(self):
        with self.assertRaises(ValueError):
            assess_nonconformance(["NCR-1"], inventory(), [], "2026-09-21")


if __name__ == "__main__":
    unittest.main()
