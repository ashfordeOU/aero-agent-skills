#!/usr/bin/env python3
"""Gate 3 contract test: ECSS-E-ST-10-02C clause 5.2.6.2 GSE
qualification for verification tooling.

Exercises scripts/e1002_gse_tools_logic.py (stdlib unittest, offline).
Contract: docs/harness-contract.md gate 3 - GSE is categorized MGSE or
EGSE from its primary function; required qualification actions follow
fixed rules (flight-item contact -> ICD, plus proof test/periodic
re-proof for MGSE or interface safety verification for EGSE; formal
measurement use -> calibration with traceability regardless of class);
the register covers every GSE item with no duplicates; qualification
gaps and periodic re-proof due dates are detected fail-safe.
"""

import os
import sys
import unittest

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import e1002_gse_tools_logic as gt  # noqa: E402


class ClassifyGseTest(unittest.TestCase):
    def test_handling_is_mgse(self):
        self.assertEqual(gt.classify_gse("handling"), "mgse")

    def test_stimulation_is_egse(self):
        self.assertEqual(gt.classify_gse("stimulation"), "egse")

    def test_unknown_function_raises(self):
        with self.assertRaises(ValueError):
            gt.classify_gse("catering")


class RequiredQualificationActionsTest(unittest.TestCase):
    def test_mgse_contacting_flight_item(self):
        gse = {"id": "GSE-001", "primary_function": "lifting", "contacts_flight_item": True}
        self.assertEqual(
            gt.required_qualification_actions(gse),
            ("interface_control_document", "periodic_re_proof", "proof_test_before_first_use"),
        )

    def test_egse_contacting_flight_item(self):
        gse = {"id": "GSE-002", "primary_function": "stimulation", "contacts_flight_item": True}
        self.assertEqual(
            gt.required_qualification_actions(gse),
            ("interface_control_document", "interface_safety_verification"),
        )

    def test_no_flight_item_contact_no_measurement_use(self):
        gse = {"id": "GSE-003", "primary_function": "transport"}
        self.assertEqual(gt.required_qualification_actions(gse), ())

    def test_formal_measurement_use_adds_calibration_regardless_of_class(self):
        gse = {
            "id": "GSE-004",
            "primary_function": "signal_checkout",
            "used_for_formal_verification_measurement": True,
        }
        self.assertEqual(gt.required_qualification_actions(gse), ("calibration_with_traceability",))

    def test_missing_id_raises(self):
        with self.assertRaises(ValueError):
            gt.required_qualification_actions({"primary_function": "handling"})

    def test_unknown_function_raises(self):
        with self.assertRaises(ValueError):
            gt.required_qualification_actions({"id": "GSE-005", "primary_function": "catering"})


class BuildGseRegisterTest(unittest.TestCase):
    GSE_ITEMS = [
        {"id": "GSE-001", "primary_function": "lifting", "contacts_flight_item": True},
        {
            "id": "GSE-002",
            "primary_function": "signal_checkout",
            "contacts_flight_item": True,
            "used_for_formal_verification_measurement": True,
        },
    ]

    def test_register_order_and_content(self):
        register = gt.build_gse_register(self.GSE_ITEMS)
        self.assertEqual(
            register,
            [
                {
                    "id": "GSE-001",
                    "class": "mgse",
                    "required_actions": ("interface_control_document", "periodic_re_proof", "proof_test_before_first_use"),
                },
                {
                    "id": "GSE-002",
                    "class": "egse",
                    "required_actions": (
                        "calibration_with_traceability",
                        "interface_control_document",
                        "interface_safety_verification",
                    ),
                },
            ],
        )

    def test_duplicate_id_raises(self):
        with self.assertRaises(ValueError):
            gt.build_gse_register(self.GSE_ITEMS + [self.GSE_ITEMS[0]])

    def test_does_not_mutate_input(self):
        before = [dict(item) for item in self.GSE_ITEMS]
        gt.build_gse_register(self.GSE_ITEMS)
        self.assertEqual(self.GSE_ITEMS, before)


class FindUnqualifiedGseTest(unittest.TestCase):
    REGISTER = [
        {"id": "GSE-001", "class": "mgse", "required_actions": ("interface_control_document", "proof_test_before_first_use")},
        {"id": "GSE-002", "class": "egse", "required_actions": ()},
    ]

    def test_flags_incomplete_actions(self):
        completed = {"GSE-001": {"interface_control_document"}}
        self.assertEqual(gt.find_unqualified_gse(self.REGISTER, completed), ["GSE-001"])

    def test_fully_complete_item_not_flagged(self):
        completed = {
            "GSE-001": {"interface_control_document", "proof_test_before_first_use"},
        }
        self.assertEqual(gt.find_unqualified_gse(self.REGISTER, completed), [])

    def test_missing_entry_treated_as_incomplete(self):
        self.assertEqual(gt.find_unqualified_gse(self.REGISTER, {}), ["GSE-001"])


class MeasurementChainGseIdsTest(unittest.TestCase):
    def test_only_calibration_requiring_ids_returned(self):
        register = [
            {"id": "GSE-001", "class": "mgse", "required_actions": ("proof_test_before_first_use",)},
            {"id": "GSE-002", "class": "egse", "required_actions": ("calibration_with_traceability",)},
        ]
        self.assertEqual(gt.measurement_chain_gse_ids(register), ["GSE-002"])


class ReproofDueTest(unittest.TestCase):
    def test_modified_since_last_proof_is_due(self):
        status = {"modified_since_last_proof": True, "uses_since_last_proof": 0, "max_uses_between_proofs": 10}
        self.assertTrue(gt.reproof_due(status))

    def test_uses_at_max_is_due(self):
        status = {"modified_since_last_proof": False, "uses_since_last_proof": 10, "max_uses_between_proofs": 10}
        self.assertTrue(gt.reproof_due(status))

    def test_uses_below_max_is_not_due(self):
        status = {"modified_since_last_proof": False, "uses_since_last_proof": 3, "max_uses_between_proofs": 10}
        self.assertFalse(gt.reproof_due(status))


class FindGseDueForReproofTest(unittest.TestCase):
    REGISTER = [
        {"id": "GSE-001", "class": "mgse", "required_actions": ("periodic_re_proof",)},
        {"id": "GSE-002", "class": "egse", "required_actions": ("interface_safety_verification",)},
    ]

    def test_untracked_item_requiring_reproof_is_due(self):
        self.assertEqual(gt.find_gse_due_for_reproof(self.REGISTER, {}), ["GSE-001"])

    def test_tracked_not_due_item_excluded(self):
        status = {"GSE-001": {"modified_since_last_proof": False, "uses_since_last_proof": 1, "max_uses_between_proofs": 10}}
        self.assertEqual(gt.find_gse_due_for_reproof(self.REGISTER, status), [])

    def test_item_not_requiring_reproof_never_flagged(self):
        self.assertEqual(gt.find_gse_due_for_reproof(self.REGISTER, {"GSE-002": None}), ["GSE-001"])


if __name__ == "__main__":
    unittest.main(verbosity=2)
