#!/usr/bin/env python3
"""Gate 3 contract test: ECSS-E-ST-10C clause 5.6.4 system-level
interface management/control.

Exercises scripts/e10_interface_control_logic.py (stdlib unittest,
offline). Contract: docs/harness-contract.md gate 3 - an interface
domain is one of the five recognized physical domains and an
unrecognized domain raises; an interface's responsibility boundary is
internal when both owners match and external otherwise, and a missing
owner raises; the required control document is the formal ICD for an
external interface and the interface control note for an internal one;
a control-status transition only succeeds exactly one step forward
along the fixed sequence, and a skipped step, backward move, no-op, or
unrecognized status raises; the documentation check flags a missing
IRD once drafting starts and a missing boundary-appropriate document
once baselining starts; the parameter check flags a value present on
only one side and a mismatched value on both sides; and the aggregated
review is under control only when both categories are empty.
"""

import os
import sys
import unittest

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import e10_interface_control_logic as ic  # noqa: E402


class ClassifyInterfaceDomainTest(unittest.TestCase):
    def test_mechanical_is_recognized(self):
        self.assertEqual(ic.classify_interface_domain("mechanical"), "mechanical")

    def test_electrical_is_recognized(self):
        self.assertEqual(ic.classify_interface_domain("electrical"), "electrical")

    def test_thermal_is_recognized(self):
        self.assertEqual(ic.classify_interface_domain("thermal"), "thermal")

    def test_data_is_recognized(self):
        self.assertEqual(ic.classify_interface_domain("data"), "data")

    def test_fluid_is_recognized(self):
        self.assertEqual(ic.classify_interface_domain("fluid"), "fluid")

    def test_unknown_domain_raises(self):
        with self.assertRaises(ValueError):
            ic.classify_interface_domain("acoustic")


class InterfaceBoundaryTest(unittest.TestCase):
    def test_matching_owners_is_internal(self):
        self.assertEqual(ic.interface_boundary("bus-team", "bus-team"), "internal")

    def test_differing_owners_is_external(self):
        self.assertEqual(ic.interface_boundary("spacecraft-prime", "launcher-authority"), "external")

    def test_missing_side_a_owner_raises(self):
        with self.assertRaises(ValueError):
            ic.interface_boundary("", "bus-team")

    def test_missing_side_b_owner_raises(self):
        with self.assertRaises(ValueError):
            ic.interface_boundary("bus-team", None)


class RequiredControlDocumentTest(unittest.TestCase):
    def test_external_requires_icd(self):
        self.assertEqual(ic.required_control_document("external"), "ICD")

    def test_internal_requires_control_note(self):
        self.assertEqual(
            ic.required_control_document("internal"), "interface_control_note"
        )

    def test_unrecognized_boundary_raises(self):
        with self.assertRaises(ValueError):
            ic.required_control_document("orbital")


class ValidateStatusTransitionTest(unittest.TestCase):
    def test_identified_to_ird_drafted_is_valid(self):
        self.assertEqual(
            ic.validate_status_transition("identified", "ird_drafted"), "ird_drafted"
        )

    def test_ird_agreed_to_icd_baselined_is_valid(self):
        self.assertEqual(
            ic.validate_status_transition("ird_agreed", "icd_baselined"),
            "icd_baselined",
        )

    def test_icd_baselined_to_verified_is_valid(self):
        self.assertEqual(
            ic.validate_status_transition("icd_baselined", "verified"), "verified"
        )

    def test_skipped_step_raises(self):
        with self.assertRaises(ValueError):
            ic.validate_status_transition("identified", "icd_baselined")

    def test_backward_move_raises(self):
        with self.assertRaises(ValueError):
            ic.validate_status_transition("verified", "icd_baselined")

    def test_no_op_raises(self):
        with self.assertRaises(ValueError):
            ic.validate_status_transition("ird_drafted", "ird_drafted")

    def test_unrecognized_current_status_raises(self):
        with self.assertRaises(ValueError):
            ic.validate_status_transition("proposed", "ird_drafted")

    def test_unrecognized_next_status_raises(self):
        with self.assertRaises(ValueError):
            ic.validate_status_transition("identified", "closed")


class InterfaceDocumentViolationsTest(unittest.TestCase):
    def test_identified_status_needs_no_documents(self):
        self.assertEqual(
            ic.interface_document_violations("if-1", "identified", "external", []), []
        )

    def test_ird_drafted_without_ird_flagged(self):
        violations = ic.interface_document_violations("if-1", "ird_drafted", "external", [])
        self.assertEqual(violations, [{"issue": "missing_ird", "interface": "if-1"}])

    def test_ird_drafted_with_ird_on_record_not_flagged(self):
        self.assertEqual(
            ic.interface_document_violations("if-1", "ird_drafted", "external", ["IRD"]), []
        )

    def test_icd_baselined_without_icd_flagged_for_external(self):
        violations = ic.interface_document_violations(
            "if-1", "icd_baselined", "external", ["IRD"]
        )
        self.assertEqual(
            violations,
            [
                {
                    "issue": "missing_required_control_document",
                    "interface": "if-1",
                    "required_document": "ICD",
                }
            ],
        )

    def test_icd_baselined_with_icd_on_record_not_flagged(self):
        self.assertEqual(
            ic.interface_document_violations("if-1", "icd_baselined", "external", ["IRD", "ICD"]),
            [],
        )

    def test_internal_boundary_requires_control_note_not_icd(self):
        violations = ic.interface_document_violations(
            "if-2", "icd_baselined", "internal", ["IRD", "ICD"]
        )
        self.assertEqual(
            violations,
            [
                {
                    "issue": "missing_required_control_document",
                    "interface": "if-2",
                    "required_document": "interface_control_note",
                }
            ],
        )

    def test_unrecognized_status_raises(self):
        with self.assertRaises(ValueError):
            ic.interface_document_violations("if-1", "proposed", "external", [])


class InterfaceParameterViolationsTest(unittest.TestCase):
    def test_matching_parameters_no_violation(self):
        self.assertEqual(
            ic.interface_parameter_violations(
                "if-1", {"voltage_v": 28}, {"voltage_v": 28}
            ),
            [],
        )

    def test_mismatched_value_flagged(self):
        violations = ic.interface_parameter_violations(
            "if-1", {"voltage_v": 28}, {"voltage_v": 24}
        )
        self.assertEqual(
            violations,
            [
                {
                    "issue": "parameter_mismatch",
                    "interface": "if-1",
                    "parameter": "voltage_v",
                    "side_a": 28,
                    "side_b": 24,
                }
            ],
        )

    def test_parameter_missing_on_side_b_flagged(self):
        violations = ic.interface_parameter_violations(
            "if-1", {"connector_type": "D38999"}, {}
        )
        self.assertEqual(
            violations,
            [
                {
                    "issue": "parameter_missing_side_b",
                    "interface": "if-1",
                    "parameter": "connector_type",
                }
            ],
        )

    def test_parameter_missing_on_side_a_flagged(self):
        violations = ic.interface_parameter_violations(
            "if-1", {}, {"data_rate_mbps": 100}
        )
        self.assertEqual(
            violations,
            [
                {
                    "issue": "parameter_missing_side_a",
                    "interface": "if-1",
                    "parameter": "data_rate_mbps",
                }
            ],
        )


class InterfaceControlReviewTest(unittest.TestCase):
    def test_fully_controlled_review(self):
        interface = {
            "interface_id": "if-10",
            "domain": "electrical",
            "side_a_owner": "spacecraft-prime",
            "side_b_owner": "instrument-team",
            "status": "verified",
            "control_documents": ["IRD", "ICD"],
            "side_a_parameters": {"voltage_v": 28, "connector_type": "D38999"},
            "side_b_parameters": {"voltage_v": 28, "connector_type": "D38999"},
        }
        review = ic.interface_control_review(interface)
        self.assertEqual(review, {"documentation": [], "parameters": []})
        self.assertTrue(ic.is_interface_controlled(review))

    def test_review_surfaces_each_category_independently(self):
        interface = {
            "interface_id": "if-11",
            "domain": "data",
            "side_a_owner": "spacecraft-prime",
            "side_b_owner": "ground-segment",
            "status": "icd_baselined",
            "control_documents": ["IRD"],
            "side_a_parameters": {"data_rate_mbps": 100},
            "side_b_parameters": {"data_rate_mbps": 50},
        }
        review = ic.interface_control_review(interface)
        self.assertTrue(review["documentation"])
        self.assertTrue(review["parameters"])
        self.assertFalse(ic.is_interface_controlled(review))

    def test_internal_interface_uses_control_note_not_icd(self):
        interface = {
            "interface_id": "if-12",
            "domain": "mechanical",
            "side_a_owner": "bus-team",
            "side_b_owner": "bus-team",
            "status": "icd_baselined",
            "control_documents": ["IRD", "interface_control_note"],
            "side_a_parameters": {"bolt_pattern": "M6x8"},
            "side_b_parameters": {"bolt_pattern": "M6x8"},
        }
        review = ic.interface_control_review(interface)
        self.assertEqual(review, {"documentation": [], "parameters": []})

    def test_review_raises_on_unknown_domain(self):
        interface = {
            "interface_id": "if-13",
            "domain": "acoustic",
            "side_a_owner": "bus-team",
            "side_b_owner": "bus-team",
            "status": "identified",
            "control_documents": [],
            "side_a_parameters": {},
            "side_b_parameters": {},
        }
        with self.assertRaises(ValueError):
            ic.interface_control_review(interface)

    def test_review_raises_on_missing_owner(self):
        interface = {
            "interface_id": "if-14",
            "domain": "thermal",
            "side_a_owner": "bus-team",
            "side_b_owner": "",
            "status": "identified",
            "control_documents": [],
            "side_a_parameters": {},
            "side_b_parameters": {},
        }
        with self.assertRaises(ValueError):
            ic.interface_control_review(interface)


if __name__ == "__main__":
    unittest.main(verbosity=2)
