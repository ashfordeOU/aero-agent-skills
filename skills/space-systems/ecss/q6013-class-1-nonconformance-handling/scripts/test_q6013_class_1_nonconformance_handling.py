"""Contract tests for the clause 4.5.2 nonconformance handling logic."""

import unittest

from q6013_class_1_nonconformance_handling_logic import (
    MAJOR_DEADLINE_H,
    MINOR_DEADLINE_H,
    assess_nonconformance,
    assess_reporting,
    categorize_severity,
    containment,
    disposition_permitted,
    reporting_deadline_h,
    required_concurrence,
    validate_record,
)


def base_record(**overrides):
    """Return a minor, isolated, understood finding found at incoming inspection."""
    record = {
        "lot_id": "LOT-2317-A",
        "detection_stage": "incoming-inspection",
        "lot_size": 500,
        "quantity_inspected": 50,
        "quantity_failed": 1,
        "detected_at_h": 100.0,
        "reported_at_h": 104.0,
        "proposed_disposition": "scrap",
        "affects_safety": False,
        "affects_interchangeability": False,
        "outside_specified_limits": False,
        "affects_mission_reliability": False,
        "root_cause_known": True,
        "mechanism_is_lot_related": False,
        "qualified_procedure_available": True,
        "part_removed": False,
    }
    record.update(overrides)
    return record


class ValidateRecordTests(unittest.TestCase):
    def test_normalises_a_good_record(self):
        normalised = validate_record(base_record())
        self.assertEqual(normalised["lot_id"], "LOT-2317-A")
        self.assertEqual(normalised["stage_rank"], 0)

    def test_blank_lot_id_rejected(self):
        with self.assertRaises(ValueError):
            validate_record(base_record(lot_id="   "))

    def test_unknown_detection_stage_rejected(self):
        with self.assertRaises(ValueError):
            validate_record(base_record(detection_stage="shelf-life-review"))

    def test_unknown_disposition_rejected(self):
        with self.assertRaises(ValueError):
            validate_record(base_record(proposed_disposition="waive"))

    def test_inspected_above_lot_size_rejected(self):
        with self.assertRaises(ValueError):
            validate_record(base_record(lot_size=10, quantity_inspected=11))

    def test_failed_above_inspected_rejected(self):
        with self.assertRaises(ValueError):
            validate_record(base_record(quantity_inspected=5, quantity_failed=6))

    def test_zero_failed_rejected(self):
        with self.assertRaises(ValueError):
            validate_record(base_record(quantity_failed=0))

    def test_report_before_detection_rejected(self):
        with self.assertRaises(ValueError):
            validate_record(base_record(detected_at_h=100.0, reported_at_h=99.0))

    def test_boolean_quantity_rejected(self):
        with self.assertRaises(ValueError):
            validate_record(base_record(quantity_failed=True))

    def test_missing_flag_rejected(self):
        record = base_record()
        del record["root_cause_known"]
        with self.assertRaises(ValueError):
            validate_record(record)

    def test_non_boolean_flag_rejected(self):
        with self.assertRaises(ValueError):
            validate_record(base_record(affects_safety="yes"))

    def test_non_mapping_rejected(self):
        with self.assertRaises(ValueError):
            validate_record(["LOT-2317-A"])


class CategorizeSeverityTests(unittest.TestCase):
    def test_clean_isolated_finding_is_minor(self):
        self.assertEqual(categorize_severity(base_record())["severity"], "minor")

    def test_safety_effect_makes_it_major(self):
        result = categorize_severity(base_record(affects_safety=True))
        self.assertEqual(result["severity"], "major")
        self.assertTrue(any("safety" in r for r in result["reasons"]))

    def test_out_of_limit_parameter_makes_it_major(self):
        self.assertEqual(
            categorize_severity(base_record(outside_specified_limits=True))["severity"],
            "major",
        )

    def test_interchangeability_effect_makes_it_major(self):
        self.assertEqual(
            categorize_severity(base_record(affects_interchangeability=True))["severity"],
            "major",
        )

    def test_lot_related_escape_at_board_test_grades_up(self):
        result = categorize_severity(
            base_record(
                detection_stage="board-assembly-test", mechanism_is_lot_related=True
            )
        )
        self.assertEqual(result["severity"], "major")

    def test_lot_related_finding_caught_at_incoming_stays_minor(self):
        result = categorize_severity(base_record(mechanism_is_lot_related=True))
        self.assertEqual(result["severity"], "minor")

    def test_reasons_are_empty_for_a_minor_finding(self):
        self.assertEqual(categorize_severity(base_record())["reasons"], [])


class ReportingClockTests(unittest.TestCase):
    def test_major_deadline_is_shorter_than_minor(self):
        self.assertLess(reporting_deadline_h("major"), reporting_deadline_h("minor"))

    def test_unknown_severity_rejected(self):
        with self.assertRaises(ValueError):
            reporting_deadline_h("critical")

    def test_report_exactly_on_the_deadline_is_timely(self):
        result = assess_reporting(10.0, 10.0 + MAJOR_DEADLINE_H, "major")
        self.assertTrue(result["timely"])
        self.assertAlmostEqual(result["elapsed_h"], MAJOR_DEADLINE_H, places=9)
        self.assertAlmostEqual(result["overdue_h"], 0.0, places=9)

    def test_report_past_the_deadline_is_late(self):
        result = assess_reporting(0.0, MAJOR_DEADLINE_H + 6.0, "major")
        self.assertFalse(result["timely"])
        self.assertAlmostEqual(result["overdue_h"], 6.0, places=9)

    def test_minor_finding_gets_the_longer_clock(self):
        result = assess_reporting(0.0, MAJOR_DEADLINE_H + 6.0, "minor")
        self.assertTrue(result["timely"])
        self.assertAlmostEqual(result["deadline_h"], MINOR_DEADLINE_H, places=9)

    def test_backwards_clock_rejected(self):
        with self.assertRaises(ValueError):
            assess_reporting(20.0, 10.0, "minor")

    def test_non_numeric_clock_rejected(self):
        with self.assertRaises(ValueError):
            assess_reporting("20", 30.0, "minor")


class ConcurrenceTests(unittest.TestCase):
    def test_minor_scrap_stops_at_the_review_board(self):
        self.assertEqual(
            required_concurrence("minor", "scrap"), ("project-review-board",)
        )

    def test_major_finding_reaches_the_customer(self):
        self.assertIn("customer", required_concurrence("major", "scrap"))

    def test_use_as_is_reaches_customer_even_when_minor(self):
        authorities = required_concurrence("minor", "use-as-is")
        self.assertIn("customer", authorities)
        self.assertIn("design-authority", authorities)

    def test_return_to_supplier_adds_procurement(self):
        self.assertIn(
            "procurement-authority", required_concurrence("minor", "return-to-supplier")
        )

    def test_unknown_disposition_rejected(self):
        with self.assertRaises(ValueError):
            required_concurrence("minor", "waive")


class DispositionPermissionTests(unittest.TestCase):
    def test_scrap_is_always_permitted(self):
        result = disposition_permitted(base_record(root_cause_known=False))
        self.assertTrue(result["permitted"])

    def test_use_as_is_refused_while_root_cause_open(self):
        result = disposition_permitted(
            base_record(proposed_disposition="use-as-is", root_cause_known=False)
        )
        self.assertFalse(result["permitted"])
        self.assertTrue(any("root cause" in o for o in result["objections"]))

    def test_use_as_is_refused_for_a_lot_related_mechanism(self):
        result = disposition_permitted(
            base_record(proposed_disposition="use-as-is", mechanism_is_lot_related=True)
        )
        self.assertFalse(result["permitted"])

    def test_use_as_is_permitted_for_an_understood_isolated_finding(self):
        result = disposition_permitted(base_record(proposed_disposition="use-as-is"))
        self.assertTrue(result["permitted"])

    def test_repair_needs_a_qualified_procedure(self):
        result = disposition_permitted(
            base_record(
                proposed_disposition="repair", qualified_procedure_available=False
            )
        )
        self.assertFalse(result["permitted"])

    def test_rework_needs_a_qualified_procedure(self):
        result = disposition_permitted(
            base_record(
                proposed_disposition="rework", qualified_procedure_available=False
            )
        )
        self.assertFalse(result["permitted"])

    def test_return_to_supplier_needs_the_part_off_the_board(self):
        result = disposition_permitted(
            base_record(
                proposed_disposition="return-to-supplier",
                detection_stage="system-test",
                part_removed=False,
            )
        )
        self.assertFalse(result["permitted"])

    def test_return_to_supplier_clears_once_removed(self):
        result = disposition_permitted(
            base_record(
                proposed_disposition="return-to-supplier",
                detection_stage="system-test",
                part_removed=True,
            )
        )
        self.assertTrue(result["permitted"])


class ContainmentTests(unittest.TestCase):
    def test_isolated_mechanism_contains_only_the_failed_parts(self):
        scope = containment(base_record())
        self.assertEqual(scope["parts_at_risk"], 1)
        self.assertEqual(scope["scope"], "failed-parts-only")

    def test_lot_related_mechanism_contains_the_whole_lot(self):
        scope = containment(base_record(mechanism_is_lot_related=True))
        self.assertEqual(scope["parts_at_risk"], 500)
        self.assertEqual(scope["uninspected_at_risk"], 450)

    def test_observed_failure_fraction_is_over_the_inspected_sample(self):
        scope = containment(base_record(quantity_inspected=40, quantity_failed=2))
        self.assertAlmostEqual(scope["observed_failure_fraction"], 0.05, places=9)


class AssessNonconformanceTests(unittest.TestCase):
    def test_clean_minor_scrap_closes(self):
        result = assess_nonconformance(base_record())
        self.assertTrue(result["closeable"])
        self.assertEqual(result["findings"], [])

    def test_late_major_report_is_a_finding(self):
        result = assess_nonconformance(
            base_record(
                affects_safety=True, detected_at_h=0.0, reported_at_h=48.0
            )
        )
        self.assertEqual(result["severity"], "major")
        self.assertFalse(result["closeable"])
        self.assertTrue(any("past the" in f for f in result["findings"]))

    def test_refused_use_as_is_blocks_closure(self):
        result = assess_nonconformance(
            base_record(proposed_disposition="use-as-is", root_cause_known=False)
        )
        self.assertFalse(result["disposition_permitted"])
        self.assertFalse(result["closeable"])

    def test_lot_related_escape_reports_uninspected_parts(self):
        result = assess_nonconformance(
            base_record(
                detection_stage="board-assembly-test",
                mechanism_is_lot_related=True,
                detected_at_h=0.0,
                reported_at_h=2.0,
            )
        )
        self.assertEqual(result["severity"], "major")
        self.assertTrue(any("never inspected" in f for f in result["findings"]))

    def test_major_result_lists_the_customer_as_concurring_authority(self):
        result = assess_nonconformance(base_record(affects_mission_reliability=True))
        self.assertIn("customer", result["required_concurrence"])

    def test_non_mapping_spec_rejected(self):
        with self.assertRaises(ValueError):
            assess_nonconformance("LOT-2317-A")


if __name__ == "__main__":
    unittest.main()
