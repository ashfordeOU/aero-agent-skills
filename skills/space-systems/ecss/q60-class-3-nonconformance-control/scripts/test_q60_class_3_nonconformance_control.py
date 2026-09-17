"""Contract tests for the clause 6.5.2 class 3 nonconformance control logic."""

import unittest

from q60_class_3_nonconformance_control_logic import (
    CATEGORY_DISPOSITIONS,
    CATEGORY_RESPONSE_DAYS,
    CONTAINMENT_SCOPES,
    RECURRENCE_THRESHOLD,
    allowed_dispositions,
    analysis_depth,
    assess_class_3_nonconformance,
    categorize_report,
    containment_scope,
    containment_units,
    disposition_records,
    recurrence_state,
    report_ownership,
    working_days_between,
)


def base_report(**overrides):
    """Return a minor drift report raised on a Monday and answered on time."""
    report = {
        "report_id": "NCR-C3-2026-044",
        "unit_id": "U-1001",
        "part_number": "lmv321-sot23",
        "lot_id": "L-55",
        "receipt_batch": "RB-2026-018",
        "date_code": "2412",
        "effect": "parametric-drift",
        "detection_point": "goods-in",
        "function_criticality": "non-critical",
        "mechanism": "lot-related",
        "identity_depth": "receipt-batch",
        "failure_mode": "Offset Drift",
        "quantity": 6,
        "raised_date": "2026-09-07",
        "proposed_disposition": "return-to-supplier",
        "analysis_reference": "FA-C3-011",
        "records_held": ["product-assurance"],
        "responded_date": "2026-09-18",
    }
    report.update(overrides)
    return report


def inventory():
    return [
        {
            "unit_id": "U-1001",
            "part_number": "LMV321-SOT23",
            "lot_id": "L-55",
            "receipt_batch": "RB-2026-018",
            "date_code": "2412",
        },
        {
            "unit_id": "U-1002",
            "part_number": "LMV321-SOT23",
            "lot_id": "L-55",
            "receipt_batch": "RB-2026-018",
            "date_code": "2412",
        },
        {
            "unit_id": "U-1003",
            "part_number": "LMV321-SOT23",
            "lot_id": "L-56",
            "receipt_batch": "RB-2026-019",
            "date_code": "2412",
        },
        {
            "unit_id": "U-1004",
            "part_number": "LMV321-SOT23",
            "lot_id": "L-57",
            "receipt_batch": "RB-2026-020",
            "date_code": "2451",
        },
        {
            "unit_id": "U-2001",
            "part_number": "OTHER-PART",
            "lot_id": "L-55",
            "receipt_batch": "RB-2026-018",
            "date_code": "2412",
        },
    ]


class OwnershipTests(unittest.TestCase):
    def test_goods_in_finding_on_an_uncritical_part_stays_with_the_supplier(self):
        self.assertEqual(
            report_ownership("goods-in", "non-critical", "cosmetic"),
            "supplier-resolved",
        )

    def test_anything_past_goods_in_becomes_programme_controlled(self):
        self.assertEqual(
            report_ownership("board-assembly", "non-critical", "cosmetic"),
            "programme-controlled",
        )

    def test_a_critical_function_pulls_an_early_finding_back_in_house(self):
        self.assertEqual(
            report_ownership("supplier-site", "mission-critical", "cosmetic"),
            "programme-controlled",
        )

    def test_an_out_of_specification_effect_is_never_left_with_the_supplier(self):
        self.assertEqual(
            report_ownership("goods-in", "non-critical", "out-of-specification"),
            "programme-controlled",
        )

    def test_unknown_detection_point_rejected(self):
        with self.assertRaises(ValueError):
            report_ownership("on-the-shelf", "non-critical", "cosmetic")

    def test_unknown_function_criticality_rejected(self):
        with self.assertRaises(ValueError):
            report_ownership("goods-in", "quite-important", "cosmetic")


class CategoryTests(unittest.TestCase):
    def test_paperwork_finding_is_minor_however_late_it_surfaces(self):
        self.assertEqual(
            categorize_report("documentation-only", "system-test", "mission-degrading"),
            "minor",
        )

    def test_out_of_specification_in_a_safety_function_is_critical(self):
        self.assertEqual(
            categorize_report("out-of-specification", "goods-in", "safety-critical"),
            "critical",
        )

    def test_in_service_functional_failure_is_critical(self):
        self.assertEqual(
            categorize_report("functional-failure", "in-service", "non-critical"),
            "critical",
        )

    def test_late_detection_raises_a_mild_effect_to_major(self):
        self.assertEqual(
            categorize_report("cosmetic", "unit-test", "non-critical"), "major"
        )

    def test_critical_function_raises_a_mild_effect_to_major(self):
        self.assertEqual(
            categorize_report("cosmetic", "goods-in", "mission-critical"), "major"
        )

    def test_mild_effect_found_early_on_an_uncritical_part_is_minor(self):
        self.assertEqual(
            categorize_report("cosmetic", "goods-in", "non-critical"), "minor"
        )

    def test_unknown_effect_rejected(self):
        with self.assertRaises(ValueError):
            categorize_report("bent-lead-maybe", "goods-in", "non-critical")


class DispositionTests(unittest.TestCase):
    def test_a_critical_report_has_no_use_as_is_route(self):
        self.assertNotIn("use-as-is", allowed_dispositions("critical"))

    def test_a_major_report_may_still_be_accepted_as_it_stands(self):
        self.assertIn("use-as-is", allowed_dispositions("major"))

    def test_major_use_as_is_earns_a_board_and_an_application_justification(self):
        records = disposition_records("major", "use-as-is")
        self.assertIn("parts-control-board", records)
        self.assertIn("application-justification", records)

    def test_minor_use_as_is_earns_only_product_assurance(self):
        self.assertEqual(disposition_records("minor", "use-as-is"), ("product-assurance",))

    def test_replacing_with_an_upgraded_part_earns_the_customer(self):
        self.assertIn(
            "customer", disposition_records("critical", "replace-with-upgraded-part")
        )

    def test_a_disposition_outside_the_category_is_rejected(self):
        with self.assertRaises(ValueError):
            disposition_records("critical", "use-as-is")

    def test_every_category_has_a_response_deadline(self):
        for category in CATEGORY_DISPOSITIONS:
            self.assertIn(category, CATEGORY_RESPONSE_DAYS)


class AnalysisDepthTests(unittest.TestCase):
    def test_a_one_off_handling_mark_on_a_minor_report_owes_nothing(self):
        self.assertEqual(analysis_depth("handling-induced", "minor", False), "none")

    def test_a_repeated_mode_always_owes_a_full_root_cause(self):
        self.assertEqual(analysis_depth("handling-induced", "minor", True), "full-root-cause")

    def test_a_design_related_mechanism_owes_a_full_root_cause(self):
        self.assertEqual(analysis_depth("design-related", "minor", False), "full-root-cause")

    def test_a_lot_related_mechanism_owes_construction_analysis(self):
        self.assertEqual(
            analysis_depth("lot-related", "minor", False), "construction-analysis"
        )

    def test_an_unknown_mechanism_on_a_minor_report_owes_characterization(self):
        self.assertEqual(
            analysis_depth("unknown", "minor", False), "electrical-characterization"
        )

    def test_a_non_boolean_recurrence_flag_is_rejected(self):
        with self.assertRaises(ValueError):
            analysis_depth("unknown", "minor", "no")


class ContainmentTests(unittest.TestCase):
    def test_an_unknown_mechanism_is_contained_one_step_wider_than_a_known_one(self):
        known = containment_scope("receipt-batch", "lot-related")
        unknown = containment_scope("receipt-batch", "unknown")
        self.assertLess(
            CONTAINMENT_SCOPES.index(known), CONTAINMENT_SCOPES.index(unknown)
        )

    def test_no_identity_beyond_the_part_number_takes_all_stock(self):
        self.assertEqual(
            containment_scope("part-number", "lot-related"), "all-stock-of-part-number"
        )

    def test_a_handling_mark_contains_only_the_units_it_touched(self):
        self.assertEqual(
            containment_scope("lot", "handling-induced"), "affected-units-only"
        )

    def test_a_design_mechanism_takes_every_unit_of_the_part_number(self):
        self.assertEqual(
            containment_scope("lot", "design-related"), "all-stock-of-part-number"
        )

    def test_receipt_batch_scope_holds_the_batch_and_not_its_neighbours(self):
        held = containment_units(
            "same-receipt-batch",
            {
                "unit_id": "U-1001",
                "part_number": "LMV321-SOT23",
                "receipt_batch": "RB-2026-018",
            },
            inventory(),
        )
        self.assertEqual(set(held), {"U-1001", "U-1002"})

    def test_date_code_scope_reaches_across_receipt_batches(self):
        held = containment_units(
            "same-date-code",
            {"unit_id": "U-1001", "part_number": "LMV321-SOT23", "date_code": "2412"},
            inventory(),
        )
        self.assertEqual(set(held), {"U-1001", "U-1002", "U-1003"})

    def test_containment_never_crosses_the_part_number(self):
        held = containment_units(
            "all-stock-of-part-number",
            {"unit_id": "U-1001", "part_number": "LMV321-SOT23"},
            inventory(),
        )
        self.assertNotIn("U-2001", held)

    def test_a_scope_whose_axis_is_not_recorded_is_rejected(self):
        with self.assertRaises(ValueError):
            containment_units(
                "same-lot",
                {"unit_id": "U-1001", "part_number": "LMV321-SOT23"},
                inventory(),
            )

    def test_an_inventory_entry_that_is_not_a_mapping_is_rejected(self):
        with self.assertRaises(ValueError):
            containment_units(
                "same-date-code",
                {"unit_id": "U-1001", "part_number": "LMV321-SOT23", "date_code": "2412"},
                ["U-1002"],
            )


class RecurrenceTests(unittest.TestCase):
    def test_two_occurrences_are_already_systematic_at_this_class(self):
        history = [
            {"part_number": "LMV321-SOT23", "failure_mode": "offset drift", "raised_date": d}
            for d in ("2026-06-01", "2026-08-03")
        ]
        state = recurrence_state("LMV321-SOT23", "Offset Drift", history, "2026-09-21")
        self.assertEqual(state["occurrences_in_window"], RECURRENCE_THRESHOLD)
        self.assertTrue(state["systematic"])
        self.assertEqual(state["escalation"], "assurance-class-upgrade-review")

    def test_an_occurrence_outside_the_window_does_not_count(self):
        history = [
            {
                "part_number": "LMV321-SOT23",
                "failure_mode": "offset drift",
                "raised_date": "2025-01-06",
            }
        ]
        state = recurrence_state("LMV321-SOT23", "offset drift", history, "2026-09-21")
        self.assertEqual(state["occurrences_in_window"], 0)
        self.assertFalse(state["systematic"])

    def test_a_different_mode_on_the_same_part_does_not_count(self):
        history = [
            {
                "part_number": "LMV321-SOT23",
                "failure_mode": "cracked body",
                "raised_date": "2026-08-03",
            }
        ]
        state = recurrence_state("LMV321-SOT23", "offset drift", history, "2026-09-21")
        self.assertEqual(state["occurrences_in_window"], 0)

    def test_a_history_entry_raised_in_the_future_is_rejected(self):
        history = [
            {
                "part_number": "LMV321-SOT23",
                "failure_mode": "offset drift",
                "raised_date": "2026-12-01",
            }
        ]
        with self.assertRaises(ValueError):
            recurrence_state("LMV321-SOT23", "offset drift", history, "2026-09-21")


class WorkingDayTests(unittest.TestCase):
    def test_a_full_week_is_five_working_days(self):
        self.assertEqual(working_days_between("2026-09-07", "2026-09-14"), 5)

    def test_a_weekend_adds_no_working_days(self):
        self.assertEqual(working_days_between("2026-09-11", "2026-09-13"), 0)

    def test_an_end_before_the_start_is_rejected(self):
        with self.assertRaises(ValueError):
            working_days_between("2026-09-14", "2026-09-07")

    def test_a_malformed_date_is_rejected(self):
        with self.assertRaises(ValueError):
            working_days_between("07/09/2026", "2026-09-14")


class AssessmentTests(unittest.TestCase):
    def test_a_clean_minor_report_closes(self):
        result = assess_class_3_nonconformance(
            base_report(), inventory(), [], "2026-09-21"
        )
        self.assertEqual(result["category"], "minor")
        self.assertEqual(result["findings"], [])
        self.assertTrue(result["closeable"])

    def test_a_use_as_is_on_a_critical_report_is_refused(self):
        result = assess_class_3_nonconformance(
            base_report(
                effect="out-of-specification",
                function_criticality="safety-critical",
                proposed_disposition="use-as-is",
            ),
            inventory(),
            [],
            "2026-09-10",
        )
        self.assertEqual(result["category"], "critical")
        self.assertTrue(any("not open to a critical" in f for f in result["findings"]))
        self.assertTrue(any("no use-as-is route" in n for n in result["notes"]))

    def test_a_missing_record_is_named_rather_than_assumed(self):
        result = assess_class_3_nonconformance(
            base_report(
                effect="cosmetic",
                detection_point="unit-test",
                proposed_disposition="use-as-is",
                records_held=["product-assurance"],
                responded_date="2026-09-11",
            ),
            inventory(),
            [],
            "2026-09-21",
        )
        self.assertTrue(
            any("missing the" in f and "record(s)" in f for f in result["findings"])
        )

    def test_an_owed_analysis_with_no_reference_is_a_finding(self):
        result = assess_class_3_nonconformance(
            base_report(analysis_reference=None), inventory(), [], "2026-09-21"
        )
        self.assertTrue(any("owes a" in f for f in result["findings"]))

    def test_an_open_report_keeps_accruing_working_days(self):
        result = assess_class_3_nonconformance(
            base_report(responded_date=None), inventory(), [], "2026-10-12"
        )
        self.assertEqual(result["response_state"], "open")
        self.assertFalse(result["within_deadline"])
        self.assertFalse(result["closeable"])

    def test_an_in_service_report_owes_the_customer_a_statement(self):
        result = assess_class_3_nonconformance(
            base_report(
                detection_point="in-service",
                effect="functional-failure",
                proposed_disposition="scrap",
                records_held=["product-assurance", "parts-control-board"],
                responded_date="2026-09-09",
            ),
            inventory(),
            [],
            "2026-09-21",
        )
        self.assertTrue(any("raised in service" in f for f in result["findings"]))

    def test_a_systematic_mode_moves_the_question_to_the_assurance_class(self):
        history = [
            {"part_number": "LMV321-SOT23", "failure_mode": "offset drift", "raised_date": d}
            for d in ("2026-06-01", "2026-08-03")
        ]
        result = assess_class_3_nonconformance(
            base_report(), inventory(), history, "2026-09-21"
        )
        self.assertEqual(result["escalation"], "assurance-class-upgrade-review")
        self.assertEqual(result["analysis_depth"], "full-root-cause")

    def test_containment_is_reported_with_the_units_it_holds(self):
        result = assess_class_3_nonconformance(
            base_report(), inventory(), [], "2026-09-21"
        )
        self.assertEqual(result["containment_scope"], "same-receipt-batch")
        self.assertEqual(result["contained_unit_count"], 2)

    def test_a_report_with_no_proposed_disposition_is_a_finding(self):
        result = assess_class_3_nonconformance(
            base_report(proposed_disposition=None), inventory(), [], "2026-09-21"
        )
        self.assertTrue(any("no proposed disposition" in f for f in result["findings"]))

    def test_an_as_of_before_the_raised_date_is_rejected(self):
        with self.assertRaises(ValueError):
            assess_class_3_nonconformance(base_report(), inventory(), [], "2026-09-01")

    def test_a_zero_quantity_is_rejected(self):
        with self.assertRaises(ValueError):
            assess_class_3_nonconformance(
                base_report(quantity=0), inventory(), [], "2026-09-21"
            )

    def test_a_missing_required_key_is_rejected(self):
        report = base_report()
        del report["mechanism"]
        with self.assertRaises(ValueError):
            assess_class_3_nonconformance(report, inventory(), [], "2026-09-21")

    def test_a_report_that_is_not_a_mapping_is_rejected(self):
        with self.assertRaises(ValueError):
            assess_class_3_nonconformance(["NCR-1"], inventory(), [], "2026-09-21")


if __name__ == "__main__":
    unittest.main()
