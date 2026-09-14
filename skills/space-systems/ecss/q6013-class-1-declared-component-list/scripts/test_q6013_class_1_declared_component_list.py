"""Contract tests for the clause 4.1.4 declared component list logic."""

import unittest

from q6013_class_1_declared_component_list_logic import (
    APPROVAL_ROUTES,
    COVERAGE_TOLERANCE,
    MANDATORY_LINE_ATTRIBUTES,
    approval_coverage,
    approval_route,
    assess_declared_component_list,
    duplicate_line_ids,
    evaluate_line,
    line_completeness,
    validate_equipment_id,
)

EQUIPMENT = "PCDU-A"


def line(**overrides):
    """Return a complete, releasable commercial line with optional overrides."""
    base = {
        "line_id": "L001",
        "part_number": "XC7A35T",
        "manufacturer": "Vendor-A",
        "component_type": "fpga",
        "procurement_category": "commercial",
        "equipment_id": EQUIPMENT,
        "quantity": 2,
        "approval_state": "granted",
    }
    base.update(overrides)
    return base


class ValidateEquipmentTests(unittest.TestCase):
    def test_strips_surrounding_space(self):
        self.assertEqual(validate_equipment_id("  PCDU-A "), "PCDU-A")

    def test_blank_rejected(self):
        with self.assertRaises(ValueError):
            validate_equipment_id("   ")

    def test_non_string_rejected(self):
        with self.assertRaises(ValueError):
            validate_equipment_id(17)


class ApprovalRouteTests(unittest.TestCase):
    def test_commercial_routes_to_customer(self):
        self.assertEqual(approval_route("commercial"), "customer-approval")

    def test_upscreened_still_routes_to_customer(self):
        self.assertEqual(approval_route("commercial-upscreened"), "customer-approval")

    def test_qualified_routes_to_project_declaration(self):
        self.assertEqual(approval_route("ecss-qualified"), "project-declaration")

    def test_route_lookup_is_case_insensitive(self):
        self.assertEqual(approval_route("EPPL"), "project-declaration")

    def test_unknown_category_rejected(self):
        with self.assertRaises(ValueError):
            approval_route("whatever-we-had-in-the-drawer")

    def test_every_known_category_has_a_route(self):
        for category in APPROVAL_ROUTES:
            self.assertIn(approval_route(category), ("customer-approval", "project-declaration"))


class LineCompletenessTests(unittest.TestCase):
    def test_complete_line_scores_one(self):
        missing, fraction = line_completeness(line())
        self.assertEqual(missing, ())
        self.assertAlmostEqual(fraction, 1.0, places=9)

    def test_missing_attribute_is_named(self):
        incomplete = line()
        del incomplete["manufacturer"]
        missing, fraction = line_completeness(incomplete)
        self.assertEqual(missing, ("manufacturer",))
        expected = (len(MANDATORY_LINE_ATTRIBUTES) - 1) / len(MANDATORY_LINE_ATTRIBUTES)
        self.assertAlmostEqual(fraction, expected, places=9)

    def test_blank_string_counts_as_missing(self):
        missing, _ = line_completeness(line(part_number="   "))
        self.assertEqual(missing, ("part_number",))

    def test_none_counts_as_missing(self):
        missing, _ = line_completeness(line(component_type=None))
        self.assertEqual(missing, ("component_type",))

    def test_non_mapping_line_rejected(self):
        with self.assertRaises(ValueError):
            line_completeness(["L001"])


class EvaluateLineTests(unittest.TestCase):
    def test_granted_commercial_line_is_released(self):
        record = evaluate_line(line(), EQUIPMENT)
        self.assertEqual(record["disposition"], "released")
        self.assertTrue(record["releasable"])

    def test_incomplete_line_is_not_a_pending_approval(self):
        incomplete = line()
        del incomplete["quantity"]
        record = evaluate_line(incomplete, EQUIPMENT)
        self.assertEqual(record["disposition"], "record-incomplete")
        self.assertFalse(record["releasable"])

    def test_line_for_another_equipment_is_an_orphan(self):
        record = evaluate_line(line(equipment_id="AOCS-B"), EQUIPMENT)
        self.assertEqual(record["disposition"], "orphan-line")

    def test_never_requested_is_kept_apart_from_open(self):
        missing = evaluate_line(line(approval_state="not-requested"), EQUIPMENT)
        still_open = evaluate_line(line(approval_state="in-review"), EQUIPMENT)
        self.assertEqual(missing["disposition"], "approval-missing")
        self.assertEqual(still_open["disposition"], "approval-open")

    def test_refusal_is_kept_apart_from_absence(self):
        record = evaluate_line(line(approval_state="refused"), EQUIPMENT)
        self.assertEqual(record["disposition"], "approval-refused")

    def test_withdrawn_reads_as_refused(self):
        record = evaluate_line(line(approval_state="withdrawn"), EQUIPMENT)
        self.assertEqual(record["disposition"], "approval-refused")

    def test_approval_granted_for_other_equipment_does_not_transfer(self):
        record = evaluate_line(line(approval_equipment_id="AOCS-B"), EQUIPMENT)
        self.assertEqual(record["disposition"], "approval-not-transferable")
        self.assertFalse(record["releasable"])

    def test_approval_granted_for_other_application_does_not_transfer(self):
        record = evaluate_line(
            line(approval_application="bench-monitor", application="latch-drive"), EQUIPMENT
        )
        self.assertEqual(record["disposition"], "approval-not-transferable")

    def test_approval_scoped_to_this_equipment_transfers(self):
        record = evaluate_line(line(approval_equipment_id=EQUIPMENT), EQUIPMENT)
        self.assertEqual(record["disposition"], "released")

    def test_project_declaration_does_not_discharge_a_commercial_line(self):
        record = evaluate_line(line(approval_state="declared"), EQUIPMENT)
        self.assertEqual(record["disposition"], "wrong-route-state")

    def test_qualified_line_is_carried_by_a_declaration(self):
        record = evaluate_line(
            line(procurement_category="ecss-qualified", approval_state="declared"), EQUIPMENT
        )
        self.assertEqual(record["disposition"], "released")

    def test_qualified_line_without_a_declaration_is_missing(self):
        record = evaluate_line(
            line(procurement_category="eppl", approval_state="not-requested"), EQUIPMENT
        )
        self.assertEqual(record["disposition"], "approval-missing")

    def test_unknown_approval_state_rejected(self):
        with self.assertRaises(ValueError):
            evaluate_line(line(approval_state="probably-fine"), EQUIPMENT)

    def test_zero_quantity_rejected(self):
        with self.assertRaises(ValueError):
            evaluate_line(line(quantity=0), EQUIPMENT)

    def test_boolean_quantity_rejected(self):
        with self.assertRaises(ValueError):
            evaluate_line(line(quantity=True), EQUIPMENT)


class DuplicateLineIdTests(unittest.TestCase):
    def test_duplicates_are_reported(self):
        self.assertEqual(
            duplicate_line_ids([line(), line(part_number="OTHER"), line(line_id="L002")]),
            ("L001",),
        )

    def test_unique_list_has_none(self):
        self.assertEqual(duplicate_line_ids([line(), line(line_id="L002")]), ())

    def test_non_sequence_rejected(self):
        with self.assertRaises(ValueError):
            duplicate_line_ids("L001")


class ApprovalCoverageTests(unittest.TestCase):
    def test_all_released_is_full_coverage(self):
        records = [evaluate_line(line(), EQUIPMENT), evaluate_line(line(line_id="L002"), EQUIPMENT)]
        self.assertAlmostEqual(approval_coverage(records), 1.0, places=9)

    def test_coverage_is_weighted_by_installed_quantity(self):
        records = [
            evaluate_line(line(quantity=3), EQUIPMENT),
            evaluate_line(line(line_id="L002", quantity=1, approval_state="not-requested"), EQUIPMENT),
        ]
        self.assertAlmostEqual(approval_coverage(records), 0.75, places=9)

    def test_incomplete_line_carries_no_quantity_and_no_credit(self):
        incomplete = line(line_id="L002")
        del incomplete["manufacturer"]
        records = [evaluate_line(line(quantity=4), EQUIPMENT), evaluate_line(incomplete, EQUIPMENT)]
        self.assertAlmostEqual(approval_coverage(records), 1.0, places=9)

    def test_empty_records_rejected(self):
        with self.assertRaises(ValueError):
            approval_coverage([])

    def test_records_without_quantity_rejected(self):
        with self.assertRaises(ValueError):
            approval_coverage([{"disposition": "released", "quantity": -1}])


class AssessDeclaredComponentListTests(unittest.TestCase):
    def _spec(self, **overrides):
        base = {
            "equipment_id": EQUIPMENT,
            "lines": [line(), line(line_id="L002", part_number="LM317", quantity=4)],
        }
        base.update(overrides)
        return base

    def test_clean_list_releases(self):
        result = assess_declared_component_list(self._spec())
        self.assertEqual(result["verdict"], "release")
        self.assertTrue(result["releasable"])
        self.assertEqual(result["findings"], [])
        self.assertAlmostEqual(result["approval_coverage"], 1.0, places=9)

    def test_one_unapproved_line_holds_the_list(self):
        spec = self._spec(
            lines=[line(), line(line_id="L002", quantity=4, approval_state="not-requested")]
        )
        result = assess_declared_component_list(spec)
        self.assertEqual(result["verdict"], "hold")
        self.assertAlmostEqual(result["approval_coverage"], 2.0 / 6.0, places=9)

    def test_findings_are_ranked_worst_first(self):
        broken = line(line_id="L003")
        del broken["component_type"]
        spec = self._spec(
            lines=[
                line(line_id="L001", approval_state="in-review"),
                line(line_id="L002", quantity=4, equipment_id="AOCS-B"),
                broken,
            ]
        )
        result = assess_declared_component_list(spec)
        dispositions = [item["disposition"] for item in result["findings"]]
        self.assertEqual(dispositions[0], "record-incomplete")
        self.assertEqual(dispositions[1], "orphan-line")
        self.assertEqual(dispositions[-1], "approval-open")

    def test_duplicate_line_id_is_a_finding(self):
        spec = self._spec(lines=[line(), line(part_number="LM317")])
        result = assess_declared_component_list(spec)
        self.assertIn("duplicate-line-id", [item["disposition"] for item in result["findings"]])
        self.assertEqual(result["verdict"], "hold")

    def test_threshold_met_exactly_is_not_a_shortfall(self):
        spec = self._spec(
            lines=[
                line(quantity=3),
                line(line_id="L002", quantity=1, procurement_category="ecss-qualified",
                     approval_state="declared"),
            ],
            required_coverage=1.0,
        )
        result = assess_declared_component_list(spec)
        self.assertAlmostEqual(result["approval_coverage"], result["required_coverage"], places=9)
        self.assertEqual(result["verdict"], "release")

    def test_tolerance_is_small_enough_to_be_representation_only(self):
        self.assertLess(COVERAGE_TOLERANCE, 1e-6)

    def test_missing_lines_key_rejected(self):
        with self.assertRaises(ValueError):
            assess_declared_component_list({"equipment_id": EQUIPMENT})

    def test_empty_lines_rejected(self):
        with self.assertRaises(ValueError):
            assess_declared_component_list(self._spec(lines=[]))

    def test_non_mapping_spec_rejected(self):
        with self.assertRaises(ValueError):
            assess_declared_component_list(["equipment"])

    def test_out_of_range_required_coverage_rejected(self):
        with self.assertRaises(ValueError):
            assess_declared_component_list(self._spec(required_coverage=1.4))


if __name__ == "__main__":
    unittest.main()
