"""Contract test for means_of_compliance_logic (wave-24r).

Runs offline with stdlib unittest only:
    python3 scripts/test_means_of_compliance.py
"""

import sys
import os
import unittest

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from means_of_compliance_logic import (
    MOC_NAMES,
    accept_item,
    build_compliance_matrix,
    compliance_verdict,
    coverage_score,
    moc_suitability,
)

# Spec worked example certification items.
FCS_1 = {
    "item_id": "FCS-1",
    "regulation_paragraph": "25.671",
    "item_kind": "systems",
    "severity": "catastrophic",
    "dal": "A",
    "novel": True,
}
STR_1 = {
    "item_id": "STR-1",
    "regulation_paragraph": "25.307",
    "item_kind": "structure",
    "severity": "hazardous",
    "dal": "n/a",
    "novel": False,
}
PP_1 = {
    "item_id": "PP-1",
    "regulation_paragraph": "25.901",
    "item_kind": "powerplant",
    "severity": "major",
    "dal": "n/a",
    "novel": False,
}
WORKED_EXAMPLE = [FCS_1, STR_1, PP_1]


class TestSuitability(unittest.TestCase):
    def test_structure_non_novel_analysis_primary(self):
        rec = moc_suitability("structure", "hazardous", "n/a", False)
        self.assertEqual(rec[0], 1)
        self.assertIn(2, rec)

    def test_structure_novel_upgrade_has_test_moc(self):
        rec = moc_suitability("structure", "hazardous", "n/a", True)
        self.assertIn(1, rec)
        self.assertTrue(2 in rec or 3 in rec)

    def test_systems_catastrophic_requires_moc6(self):
        rec = moc_suitability("systems", "catastrophic", "A", False)
        self.assertIn(6, rec)
        self.assertIn(1, rec)

    def test_systems_catastrophic_novel_has_test_moc(self):
        rec = moc_suitability("systems", "catastrophic", "A", True)
        self.assertIn(6, rec)
        self.assertTrue(2 in rec or 3 in rec)
        self.assertIn(1, rec)

    def test_systems_hazardous_requires_moc6(self):
        self.assertIn(6, moc_suitability("systems", "hazardous", "A", False))

    def test_systems_major_dal_c_uses_moc4(self):
        rec = moc_suitability("systems", "major", "C", False)
        self.assertIn(4, rec)
        self.assertNotIn(6, rec)

    def test_systems_minor_dal_d_no_moc6(self):
        rec = moc_suitability("systems", "minor", "D", False)
        self.assertNotIn(6, rec)

    def test_powerplant_ground_and_flight_test(self):
        rec = moc_suitability("powerplant", "major", "n/a", False)
        self.assertIn(2, rec)
        self.assertIn(3, rec)
        self.assertEqual(rec[0], 2)

    def test_equipment_ground_test_with_analysis(self):
        self.assertEqual(moc_suitability("equipment", "minor", "n/a", False), [2, 1])

    def test_software_analysis_and_tool(self):
        self.assertEqual(moc_suitability("software", "major", "B", False), [1, 4])

    def test_hardware_analysis_and_verification(self):
        self.assertEqual(moc_suitability("hardware", "hazardous", "A", False), [1, 2])

    def test_performance_flight_test_primary(self):
        rec = moc_suitability("performance", "major", "n/a", False)
        self.assertEqual(rec[0], 3)
        self.assertIn(1, rec)
        self.assertIn(4, rec)

    def test_handling_flight_test(self):
        self.assertIn(3, moc_suitability("handling", "minor", "n/a", False))

    def test_unknown_kind_raises(self):
        with self.assertRaises(ValueError):
            moc_suitability("quantum", "n/a", "n/a", False)

    def test_unknown_severity_raises(self):
        with self.assertRaises(ValueError):
            moc_suitability("systems", "very-bad", "A", False)

    def test_unknown_dal_raises(self):
        with self.assertRaises(ValueError):
            moc_suitability("systems", "major", "Z", False)

    def test_returned_list_is_a_copy(self):
        rec = moc_suitability("structure", "n/a", "n/a", False)
        rec.append(99)
        self.assertNotIn(99, moc_suitability("structure", "n/a", "n/a", False))

    def test_moc_scheme_has_six_classes(self):
        self.assertEqual(len(MOC_NAMES), 6)
        self.assertEqual(MOC_NAMES[6], "safety assessment")


class TestAcceptItem(unittest.TestCase):
    def test_catastrophic_without_moc6_rejected(self):
        item = dict(FCS_1)
        ok, reason = accept_item(item, [1, 4])
        self.assertFalse(ok)
        self.assertIn("MOC 6", reason)

    def test_catastrophic_with_moc6_accepted(self):
        ok, reason = accept_item(dict(FCS_1), [1, 6, 2])
        self.assertTrue(ok)

    def test_novel_item_rejects_moc5(self):
        item = dict(STR_1)
        item["novel"] = True
        ok, reason = accept_item(item, [1, 5])
        self.assertFalse(ok)
        self.assertIn("MOC 5", reason)

    def test_novel_structure_needs_test_moc(self):
        item = dict(STR_1)
        item["novel"] = True
        ok, _ = accept_item(item, [1])
        self.assertFalse(ok)

    def test_novel_systems_with_test_moc_accepted(self):
        ok, _ = accept_item(dict(FCS_1), [1, 6, 3])
        self.assertTrue(ok)

    def test_empty_assignment_rejected(self):
        ok, _ = accept_item(dict(STR_1), [])
        self.assertFalse(ok)


class TestComplianceMatrix(unittest.TestCase):
    def test_worked_example_matrix_rows(self):
        matrix = build_compliance_matrix(WORKED_EXAMPLE)
        rows = {row["item_id"]: row for row in matrix["items"]}
        self.assertEqual(len(rows), 3)
        self.assertFalse(matrix["issues"])
        fcs = rows["FCS-1"]
        self.assertEqual(fcs["regulation_paragraph"], "25.671")
        self.assertTrue(fcs["accepted"])
        self.assertIn(6, fcs["mocs"])
        self.assertTrue(2 in fcs["mocs"] or 3 in fcs["mocs"])
        str1 = rows["STR-1"]
        self.assertTrue(str1["accepted"])
        self.assertEqual(str1["primary_moc"], 1)
        self.assertNotIn(6, str1["mocs"])
        pp1 = rows["PP-1"]
        self.assertTrue(pp1["accepted"])
        self.assertTrue(2 in pp1["mocs"] or 3 in pp1["mocs"])

    def test_matrix_coverage_full_set_is_one(self):
        matrix = build_compliance_matrix(WORKED_EXAMPLE)
        overall, per_kind = coverage_score(matrix)
        self.assertEqual(overall, 1.0)
        self.assertEqual(per_kind["systems"], 1.0)
        self.assertEqual(per_kind["structure"], 1.0)
        self.assertEqual(per_kind["powerplant"], 1.0)

    def test_verdict_pass_on_full_set(self):
        matrix = build_compliance_matrix(WORKED_EXAMPLE)
        verdict, reasons = compliance_verdict(matrix)
        self.assertEqual(verdict, "PASS")
        self.assertTrue(reasons)

    def test_verdict_fail_when_moc6_missing(self):
        bad_fcs = dict(FCS_1)
        bad_fcs["assigned_mocs"] = [1, 4]
        matrix = build_compliance_matrix([bad_fcs, STR_1, PP_1])
        verdict, reasons = compliance_verdict(matrix)
        self.assertEqual(verdict, "FAIL")
        joined = " ".join(reasons)
        self.assertIn("MOC 6", joined)

    def test_verdict_fail_on_uncovered_item(self):
        bad_str = dict(STR_1)
        bad_str["assigned_mocs"] = []
        matrix = build_compliance_matrix([FCS_1, bad_str, PP_1])
        verdict, reasons = compliance_verdict(matrix)
        self.assertEqual(verdict, "FAIL")
        self.assertTrue(any("STR-1" in r for r in reasons))

    def test_partial_per_kind_coverage(self):
        bad_str = dict(STR_1)
        bad_str["novel"] = True
        bad_str["assigned_mocs"] = [1, 5]
        matrix = build_compliance_matrix([FCS_1, bad_str])
        overall, per_kind = coverage_score(matrix)
        self.assertAlmostEqual(overall, 0.5)
        self.assertEqual(per_kind["systems"], 1.0)
        self.assertEqual(per_kind["structure"], 0.0)
        verdict, _ = compliance_verdict(matrix)
        self.assertEqual(verdict, "FAIL")

    def test_issues_populated_for_rejected(self):
        bad_fcs = dict(FCS_1)
        bad_fcs["assigned_mocs"] = [1, 4]
        matrix = build_compliance_matrix([bad_fcs])
        self.assertEqual(len(matrix["issues"]), 1)
        self.assertEqual(matrix["issues"][0][0], "FCS-1")

    def test_empty_item_list_raises(self):
        with self.assertRaises(ValueError):
            build_compliance_matrix([])

    def test_matrix_unknown_kind_raises(self):
        with self.assertRaises(ValueError):
            build_compliance_matrix([{"item_id": "X-1", "item_kind": "quantum"}])

    def test_matrix_missing_kind_raises(self):
        with self.assertRaises(ValueError):
            build_compliance_matrix([{"item_id": "X-1"}])


if __name__ == "__main__":
    unittest.main()

