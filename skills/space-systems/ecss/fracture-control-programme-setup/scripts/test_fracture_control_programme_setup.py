"""
Offline stdlib unittest for fracture_control_programme_setup_logic.
Run: python3 test_fracture_control_programme_setup.py
Expected output: OK
"""

import sys
import os
import unittest

sys.path.insert(0, os.path.dirname(__file__))

from fracture_control_programme_setup_logic import (
    StructuralItem,
    SubtierSupplier,
    ProgrammeSpec,
    programme_triggered,
    triggering_items,
    categorize_items,
    check_fcb_charter,
    check_subtier_coverage,
    check_tailoring,
    run_programme_setup_check,
)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _catastrophic(item_id: str, pressurised: bool = False) -> StructuralItem:
    return StructuralItem(item_id, "desc", "CATASTROPHIC", is_pressurised=pressurised)


def _critical(item_id: str) -> StructuralItem:
    return StructuralItem(item_id, "desc", "CRITICAL")


def _marginal(item_id: str) -> StructuralItem:
    return StructuralItem(item_id, "desc", "MARGINAL")


def _negligible(item_id: str) -> StructuralItem:
    return StructuralItem(item_id, "desc", "NEGLIGIBLE")


def _full_fcb_roles() -> list:
    return ["chair", "structural_lead", "qa_representative"]


def _valid_spec_triggered() -> ProgrammeSpec:
    return ProgrammeSpec(
        items=[_catastrophic("ITEM-01"), _critical("ITEM-02")],
        fcb_roles_present=_full_fcb_roles(),
        subtier_suppliers=[],
        tailoring_ref="FCB-TAIL-001",
        mission_risk_category="CAT-1",
        tailoring_approved=True,
    )


# ---------------------------------------------------------------------------
# Tests: programme trigger
# ---------------------------------------------------------------------------

class TestProgrammeTriggered(unittest.TestCase):

    def test_triggered_by_single_catastrophic_item(self):
        items = [_catastrophic("ITEM-A")]
        self.assertTrue(programme_triggered(items))

    def test_not_triggered_when_no_catastrophic_items(self):
        items = [_critical("ITEM-B"), _marginal("ITEM-C"), _negligible("ITEM-D")]
        self.assertFalse(programme_triggered(items))

    def test_triggered_by_catastrophic_among_many(self):
        items = [_negligible("N1"), _marginal("M1"), _catastrophic("C1"), _critical("CR1")]
        self.assertTrue(programme_triggered(items))

    def test_empty_item_list_not_triggered(self):
        self.assertFalse(programme_triggered([]))

    def test_invalid_hazard_category_raises(self):
        bad_item = StructuralItem("X1", "desc", "UNKNOWN_HAZARD")
        with self.assertRaises(ValueError):
            programme_triggered([bad_item])

    def test_triggering_items_returns_correct_ids(self):
        items = [_catastrophic("C1"), _critical("CR1"), _catastrophic("C2")]
        ids = triggering_items(items)
        self.assertEqual(sorted(ids), ["C1", "C2"])

    def test_triggering_items_empty_when_no_catastrophic(self):
        items = [_marginal("M1"), _negligible("N1")]
        self.assertEqual(triggering_items(items), [])


# ---------------------------------------------------------------------------
# Tests: item categorization (fracture-critical vs. non-fracture-critical)
# ---------------------------------------------------------------------------

class TestCategorizeItems(unittest.TestCase):

    def test_catastrophic_item_is_fracture_critical(self):
        items = [_catastrophic("C1")]
        fc, nfc = categorize_items(items)
        self.assertIn("C1", fc)
        self.assertNotIn("C1", nfc)

    def test_critical_item_without_pressure_or_rotation_is_non_fracture_critical(self):
        items = [_critical("CR1")]
        fc, nfc = categorize_items(items)
        self.assertNotIn("CR1", fc)
        self.assertIn("CR1", nfc)

    def test_pressurised_item_is_fracture_critical_regardless_of_hazard(self):
        item = StructuralItem("P1", "desc", "MARGINAL", is_pressurised=True)
        fc, nfc = categorize_items([item])
        self.assertIn("P1", fc)
        self.assertNotIn("P1", nfc)

    def test_rotating_item_is_fracture_critical(self):
        item = StructuralItem("R1", "desc", "NEGLIGIBLE", has_rotating_parts=True)
        fc, nfc = categorize_items([item])
        self.assertIn("R1", fc)

    def test_mixed_list_splits_correctly(self):
        items = [
            _catastrophic("C1"),
            _critical("CR1"),
            StructuralItem("P1", "desc", "MARGINAL", is_pressurised=True),
            _negligible("N1"),
        ]
        fc, nfc = categorize_items(items)
        self.assertCountEqual(fc, ["C1", "P1"])
        self.assertCountEqual(nfc, ["CR1", "N1"])


# ---------------------------------------------------------------------------
# Tests: FCB charter
# ---------------------------------------------------------------------------

class TestCheckFcbCharter(unittest.TestCase):

    def test_all_roles_present_returns_empty(self):
        missing = check_fcb_charter(["chair", "structural_lead", "qa_representative"])
        self.assertEqual(missing, [])

    def test_missing_chair_flagged(self):
        missing = check_fcb_charter(["structural_lead", "qa_representative"])
        self.assertIn("chair", missing)

    def test_missing_qa_representative_flagged(self):
        missing = check_fcb_charter(["chair", "structural_lead"])
        self.assertIn("qa_representative", missing)

    def test_empty_roles_flags_all_required(self):
        missing = check_fcb_charter([])
        self.assertCountEqual(missing, ["chair", "structural_lead", "qa_representative"])

    def test_extra_roles_beyond_required_accepted(self):
        missing = check_fcb_charter(
            ["chair", "structural_lead", "qa_representative", "materials_expert"]
        )
        self.assertEqual(missing, [])


# ---------------------------------------------------------------------------
# Tests: sub-tier supplier coverage
# ---------------------------------------------------------------------------

class TestCheckSubtierCoverage(unittest.TestCase):

    def test_supplier_with_own_fcb_is_covered(self):
        s = SubtierSupplier("SUP-1", has_own_fcb=True)
        self.assertEqual(check_subtier_coverage([s]), [])

    def test_supplier_with_upward_delegation_is_covered(self):
        s = SubtierSupplier("SUP-2", has_upward_delegation=True)
        self.assertEqual(check_subtier_coverage([s]), [])

    def test_supplier_with_no_coverage_is_flagged(self):
        s = SubtierSupplier("SUP-3")
        result = check_subtier_coverage([s])
        self.assertIn("SUP-3", result)

    def test_mixed_suppliers_only_flags_uncovered(self):
        suppliers = [
            SubtierSupplier("SUP-A", has_own_fcb=True),
            SubtierSupplier("SUP-B"),
            SubtierSupplier("SUP-C", has_upward_delegation=True),
        ]
        result = check_subtier_coverage(suppliers)
        self.assertEqual(result, ["SUP-B"])


# ---------------------------------------------------------------------------
# Tests: tailoring
# ---------------------------------------------------------------------------

class TestCheckTailoring(unittest.TestCase):

    def test_valid_tailoring_returns_no_findings(self):
        findings = check_tailoring("FCB-TAIL-001", "CAT-1", True)
        self.assertEqual(findings, [])

    def test_missing_tailoring_ref_flagged(self):
        findings = check_tailoring(None, "CAT-2", True)
        self.assertTrue(any("tailoring_ref" in f for f in findings))

    def test_unrecognised_risk_category_flagged(self):
        findings = check_tailoring("FCB-TAIL-002", "CAT-9", True)
        self.assertTrue(any("CAT-9" in f for f in findings))

    def test_unapproved_tailoring_flagged(self):
        findings = check_tailoring("FCB-TAIL-003", "CAT-3", False)
        self.assertTrue(any("tailoring_approved" in f for f in findings))

    def test_all_tailoring_gaps_reported_together(self):
        findings = check_tailoring(None, "UNKNOWN", False)
        self.assertEqual(len(findings), 3)


# ---------------------------------------------------------------------------
# Tests: full programme-setup check
# ---------------------------------------------------------------------------

class TestRunProgrammeSetupCheck(unittest.TestCase):

    def test_compliant_setup_returns_no_findings(self):
        result = run_programme_setup_check(_valid_spec_triggered())
        self.assertTrue(result.programme_required)
        self.assertTrue(result.is_compliant())
        self.assertEqual(result.fcb_findings, [])
        self.assertEqual(result.tailoring_findings, [])

    def test_programme_not_required_when_no_catastrophic_items(self):
        spec = ProgrammeSpec(
            items=[_critical("CR1"), _marginal("M1")],
            fcb_roles_present=[],
            tailoring_ref=None,
            mission_risk_category=None,
            tailoring_approved=False,
        )
        result = run_programme_setup_check(spec)
        self.assertFalse(result.programme_required)
        self.assertFalse(result.is_compliant())

    def test_missing_fcb_roles_captured_in_result(self):
        spec = _valid_spec_triggered()
        spec.fcb_roles_present = ["chair"]
        result = run_programme_setup_check(spec)
        self.assertIn("structural_lead", result.fcb_findings)
        self.assertIn("qa_representative", result.fcb_findings)

    def test_uncovered_subtier_supplier_captured(self):
        spec = _valid_spec_triggered()
        spec.subtier_suppliers = [SubtierSupplier("SUP-X")]
        result = run_programme_setup_check(spec)
        self.assertIn("SUP-X", result.subtier_findings)

    def test_triggering_item_ids_populated(self):
        spec = _valid_spec_triggered()
        result = run_programme_setup_check(spec)
        self.assertIn("ITEM-01", result.triggering_item_ids)
        self.assertNotIn("ITEM-02", result.triggering_item_ids)

    def test_catastrophic_item_in_fracture_critical_list(self):
        spec = _valid_spec_triggered()
        result = run_programme_setup_check(spec)
        self.assertIn("ITEM-01", result.fracture_critical_item_ids)

    def test_invalid_item_raises_before_check(self):
        spec = ProgrammeSpec(
            items=[StructuralItem("BAD", "desc", "NOT_A_CATEGORY")],
        )
        with self.assertRaises(ValueError):
            run_programme_setup_check(spec)


if __name__ == "__main__":
    unittest.main()
