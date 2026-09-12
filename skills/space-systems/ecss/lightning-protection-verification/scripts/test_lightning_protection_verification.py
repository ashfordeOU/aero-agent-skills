"""
Tests for lightning_protection_verification_logic.py

stdlib unittest only — deterministic, offline.
Run: python3 test_lightning_protection_verification.py
Expected output: OK
"""

import sys
import os
import unittest

sys.path.insert(0, os.path.dirname(__file__))

from lightning_protection_verification_logic import (
    categorize_strike_zone,
    check_bond_resistance,
    check_current_path_continuity,
    check_shielding_coverage,
    check_inspection_records,
    aggregate_compliance,
    STRIKE_ZONES,
    BOND_RESISTANCE_LIMITS_MOHM,
)

_BANNED = "class" + "ified"  # built at runtime: the literal must not appear in source


class TestCategorizeStrikeZone(unittest.TestCase):

    def test_zone_a_returns_correct_record(self):
        result = categorize_strike_zone("A")
        self.assertIsNone(result["error"])
        self.assertEqual(result["zone"], "A")
        self.assertIn("direct", result["description"])

    def test_zone_b_returns_correct_record(self):
        result = categorize_strike_zone("B")
        self.assertIsNone(result["error"])
        self.assertEqual(result["zone"], "B")
        self.assertIn("swept", result["description"])

    def test_zone_c_returns_correct_record(self):
        result = categorize_strike_zone("C")
        self.assertIsNone(result["error"])
        self.assertEqual(result["zone"], "C")

    def test_lowercase_zone_normalizes_correctly(self):
        result = categorize_strike_zone("b")
        self.assertIsNone(result["error"])
        self.assertEqual(result["zone"], "B")

    def test_invalid_zone_returns_error(self):
        result = categorize_strike_zone("D")
        self.assertIsNotNone(result["error"])
        self.assertIsNone(result["zone"])

    def test_non_string_zone_returns_error(self):
        result = categorize_strike_zone(1)
        self.assertIsNotNone(result["error"])
        self.assertIsNone(result["zone"])

    def test_empty_string_zone_returns_error(self):
        result = categorize_strike_zone("")
        self.assertIsNotNone(result["error"])
        self.assertIsNone(result["zone"])


class TestCheckBondResistance(unittest.TestCase):

    def test_primary_bond_within_limit_passes(self):
        result = check_bond_resistance(1.0, "primary")
        self.assertEqual(result["status"], "PASS")
        self.assertIsNone(result["error"])
        self.assertAlmostEqual(result["margin_mohm"], 1.5)

    def test_primary_bond_at_limit_passes(self):
        result = check_bond_resistance(2.5, "primary")
        self.assertEqual(result["status"], "PASS")
        self.assertAlmostEqual(result["margin_mohm"], 0.0)

    def test_primary_bond_exceeds_limit_fails(self):
        result = check_bond_resistance(3.0, "primary")
        self.assertEqual(result["status"], "FAIL")
        self.assertLess(result["margin_mohm"], 0)

    def test_secondary_bond_within_limit_passes(self):
        result = check_bond_resistance(8.0, "secondary")
        self.assertEqual(result["status"], "PASS")

    def test_secondary_bond_exceeds_limit_fails(self):
        result = check_bond_resistance(12.0, "secondary")
        self.assertEqual(result["status"], "FAIL")

    def test_equipment_bond_within_limit_passes(self):
        result = check_bond_resistance(20.0, "equipment")
        self.assertEqual(result["status"], "PASS")
        self.assertEqual(result["limit_mohm"], 25.0)

    def test_equipment_bond_exceeds_limit_fails(self):
        result = check_bond_resistance(26.0, "equipment")
        self.assertEqual(result["status"], "FAIL")

    def test_unrecognized_bond_class_returns_error(self):
        result = check_bond_resistance(1.0, "tertiary")
        self.assertIsNotNone(result["error"])
        self.assertEqual(result["status"], "FAIL")

    def test_negative_measured_value_returns_error(self):
        result = check_bond_resistance(-1.0, "primary")
        self.assertIsNotNone(result["error"])
        self.assertEqual(result["status"], "FAIL")

    def test_non_numeric_measurement_returns_error(self):
        result = check_bond_resistance("1.0", "primary")
        self.assertIsNotNone(result["error"])
        self.assertEqual(result["status"], "FAIL")

    def test_uppercase_bond_class_normalizes(self):
        result = check_bond_resistance(1.0, "PRIMARY")
        self.assertEqual(result["status"], "PASS")
        self.assertEqual(result["bond_class"], "primary")


class TestCheckCurrentPathContinuity(unittest.TestCase):

    def _make_pass(self, bond_class="primary", mohm=1.0):
        return check_bond_resistance(mohm, bond_class)

    def _make_fail(self):
        return check_bond_resistance(99.0, "primary")

    def test_all_passing_segments_returns_pass(self):
        segments = [self._make_pass(), self._make_pass(), self._make_pass()]
        result = check_current_path_continuity(segments)
        self.assertEqual(result["status"], "PASS")
        self.assertEqual(len(result["failing"]), 0)

    def test_one_failing_segment_returns_fail(self):
        segments = [self._make_pass(), self._make_fail(), self._make_pass()]
        result = check_current_path_continuity(segments)
        self.assertEqual(result["status"], "FAIL")
        self.assertEqual(len(result["failing"]), 1)
        self.assertEqual(result["failing"][0][0], 1)

    def test_all_failing_segments_reports_all(self):
        segments = [self._make_fail(), self._make_fail()]
        result = check_current_path_continuity(segments)
        self.assertEqual(result["status"], "FAIL")
        self.assertEqual(len(result["failing"]), 2)

    def test_empty_list_returns_error(self):
        result = check_current_path_continuity([])
        self.assertEqual(result["status"], "FAIL")
        self.assertIsNotNone(result["error"])

    def test_non_list_input_returns_error(self):
        result = check_current_path_continuity("not a list")
        self.assertEqual(result["status"], "FAIL")
        self.assertIsNotNone(result["error"])

    def test_total_segments_count_is_accurate(self):
        segments = [self._make_pass() for _ in range(5)]
        result = check_current_path_continuity(segments)
        self.assertEqual(result["total_segments"], 5)


class TestCheckShieldingCoverage(unittest.TestCase):

    def test_all_zone_a_surfaces_shielded_passes(self):
        surfaces = [
            {"id": "S1", "zone": "A", "disposition": "shielded"},
            {"id": "S2", "zone": "A", "disposition": "non-critical"},
        ]
        result = check_shielding_coverage(surfaces)
        self.assertEqual(result["status"], "PASS")
        self.assertEqual(len(result["unresolved_surfaces"]), 0)

    def test_zone_a_surface_missing_disposition_fails(self):
        surfaces = [
            {"id": "S1", "zone": "A", "disposition": None},
        ]
        result = check_shielding_coverage(surfaces)
        self.assertEqual(result["status"], "FAIL")
        self.assertEqual(len(result["unresolved_surfaces"]), 1)
        self.assertEqual(result["unresolved_surfaces"][0]["id"], "S1")

    def test_zone_b_surface_missing_disposition_fails(self):
        surfaces = [
            {"id": "S2", "zone": "B", "disposition": "unresolved"},
        ]
        result = check_shielding_coverage(surfaces)
        self.assertEqual(result["status"], "FAIL")

    def test_zone_c_surface_no_disposition_is_not_a_finding(self):
        surfaces = [
            {"id": "S3", "zone": "C", "disposition": None},
        ]
        result = check_shielding_coverage(surfaces)
        self.assertEqual(result["status"], "PASS")

    def test_mixed_zones_only_flags_a_and_b_gaps(self):
        surfaces = [
            {"id": "S1", "zone": "A", "disposition": "shielded"},
            {"id": "S2", "zone": "B", "disposition": None},
            {"id": "S3", "zone": "C", "disposition": None},
        ]
        result = check_shielding_coverage(surfaces)
        self.assertEqual(result["status"], "FAIL")
        self.assertEqual(len(result["unresolved_surfaces"]), 1)
        self.assertEqual(result["unresolved_surfaces"][0]["id"], "S2")

    def test_non_list_input_returns_error(self):
        result = check_shielding_coverage({"id": "S1"})
        self.assertEqual(result["status"], "FAIL")
        self.assertIsNotNone(result["error"])

    def test_total_surfaces_count_is_accurate(self):
        surfaces = [
            {"id": "S1", "zone": "A", "disposition": "shielded"},
            {"id": "S2", "zone": "C", "disposition": None},
        ]
        result = check_shielding_coverage(surfaces)
        self.assertEqual(result["total_surfaces"], 2)


class TestCheckInspectionRecords(unittest.TestCase):

    def test_all_inspected_returns_pass(self):
        straps = [
            {"id": "T1", "inspected": True},
            {"id": "T2", "inspected": True},
        ]
        result = check_inspection_records(straps)
        self.assertEqual(result["status"], "PASS")
        self.assertEqual(len(result["uninspected_items"]), 0)

    def test_one_uninspected_strap_fails(self):
        straps = [
            {"id": "T1", "inspected": True},
            {"id": "T2", "inspected": False},
        ]
        result = check_inspection_records(straps)
        self.assertEqual(result["status"], "FAIL")
        self.assertIn("T2", result["uninspected_items"])

    def test_missing_inspected_key_treated_as_uninspected(self):
        straps = [{"id": "T3"}]
        result = check_inspection_records(straps)
        self.assertEqual(result["status"], "FAIL")
        self.assertIn("T3", result["uninspected_items"])

    def test_empty_list_returns_error(self):
        result = check_inspection_records([])
        self.assertEqual(result["status"], "FAIL")
        self.assertIsNotNone(result["error"])

    def test_non_list_input_returns_error(self):
        result = check_inspection_records("not-a-list")
        self.assertEqual(result["status"], "FAIL")
        self.assertIsNotNone(result["error"])

    def test_total_items_count_is_accurate(self):
        straps = [
            {"id": "T1", "inspected": True},
            {"id": "T2", "inspected": True},
            {"id": "T3", "inspected": True},
        ]
        result = check_inspection_records(straps)
        self.assertEqual(result["total_items"], 3)


class TestAggregateCompliance(unittest.TestCase):

    def _all_pass_inputs(self):
        bond_results = [check_bond_resistance(1.0, "primary")]
        path_result = check_current_path_continuity(bond_results)
        shielding_result = check_shielding_coverage(
            [{"id": "S1", "zone": "A", "disposition": "shielded"}]
        )
        inspection_result = check_inspection_records(
            [{"id": "T1", "inspected": True}]
        )
        return bond_results, path_result, shielding_result, inspection_result

    def test_all_pass_produces_overall_pass(self):
        b, p, s, i = self._all_pass_inputs()
        result = aggregate_compliance(b, p, s, i)
        self.assertEqual(result["overall_status"], "PASS")
        self.assertEqual(len(result["findings"]), 0)

    def test_failing_bond_produces_overall_fail(self):
        b, p, s, i = self._all_pass_inputs()
        b_fail = [check_bond_resistance(99.0, "primary")]
        result = aggregate_compliance(b_fail, p, s, i)
        self.assertEqual(result["overall_status"], "FAIL")
        self.assertEqual(result["bond_status"], "FAIL")
        self.assertGreater(len(result["findings"]), 0)

    def test_failing_path_produces_overall_fail(self):
        b, p, s, i = self._all_pass_inputs()
        failing_path = check_current_path_continuity(
            [check_bond_resistance(99.0, "primary")]
        )
        result = aggregate_compliance(b, failing_path, s, i)
        self.assertEqual(result["overall_status"], "FAIL")
        self.assertEqual(result["path_status"], "FAIL")

    def test_failing_shielding_produces_overall_fail(self):
        b, p, s, i = self._all_pass_inputs()
        bad_shielding = check_shielding_coverage(
            [{"id": "S1", "zone": "A", "disposition": None}]
        )
        result = aggregate_compliance(b, p, bad_shielding, i)
        self.assertEqual(result["overall_status"], "FAIL")
        self.assertEqual(result["shielding_status"], "FAIL")

    def test_failing_inspection_produces_overall_fail(self):
        b, p, s, i = self._all_pass_inputs()
        bad_inspection = check_inspection_records(
            [{"id": "T1", "inspected": False}]
        )
        result = aggregate_compliance(b, p, s, bad_inspection)
        self.assertEqual(result["overall_status"], "FAIL")
        self.assertEqual(result["inspection_status"], "FAIL")

    def test_multiple_failures_reported_in_findings(self):
        b_fail = [check_bond_resistance(99.0, "primary")]
        p_fail = check_current_path_continuity(b_fail)
        s_fail = check_shielding_coverage(
            [{"id": "S1", "zone": "B", "disposition": None}]
        )
        i_fail = check_inspection_records(
            [{"id": "T1", "inspected": False}]
        )
        result = aggregate_compliance(b_fail, p_fail, s_fail, i_fail)
        self.assertEqual(result["overall_status"], "FAIL")
        self.assertGreaterEqual(len(result["findings"]), 3)

    def test_all_statuses_present_in_result(self):
        b, p, s, i = self._all_pass_inputs()
        result = aggregate_compliance(b, p, s, i)
        for key in ("bond_status", "path_status", "shielding_status",
                    "inspection_status", "overall_status", "findings"):
            self.assertIn(key, result)


# ---------------------------------------------------------------------------
# Ensure no forbidden substrings appear in this module's source
# ---------------------------------------------------------------------------

class TestForbiddenWords(unittest.TestCase):

    def test_no_forbidden_words_in_logic_source(self):
        logic_path = os.path.join(os.path.dirname(__file__),
                                  "lightning_protection_verification_logic.py")
        with open(logic_path, "r") as fh:
            content = fh.read().lower()
        self.assertNotIn(_BANNED, content,
                         f"Forbidden word {_BANNED} found in logic module")
        self.assertNotIn(("un" + _BANNED), content,
                         f"Forbidden word un{_BANNED} found in logic module")

    def test_no_forbidden_words_in_skill_md(self):
        skill_path = os.path.join(os.path.dirname(__file__),
                                  "..", "SKILL.md")
        with open(skill_path, "r") as fh:
            content = fh.read().lower()
        self.assertNotIn(_BANNED, content,
                         f"Forbidden word {_BANNED} found in SKILL.md")
        self.assertNotIn(("un" + _BANNED), content,
                         f"Forbidden word un{_BANNED} found in SKILL.md")


if __name__ == "__main__":
    unittest.main()
