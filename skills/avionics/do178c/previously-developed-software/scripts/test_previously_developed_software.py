"""Contract test for the previously-developed-software reuse scoping logic.

Offline, deterministic, stdlib unittest only. Run with:
    python3 scripts/test_previously_developed_software.py
"""

import sys
import os
import unittest

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import previously_developed_software_logic as pds


class ClassifyPdsTests(unittest.TestCase):
    """Reuse classification and credit path contracts."""

    def test_unchanged_direct_credit_class_and_path(self):
        result = pds.classify_pds("do-178c", False, True)
        self.assertEqual(result["reuse_class"], "unchanged-direct-credit")
        self.assertIn("no delta objectives", result["credit_path"])

    def test_modified_pds_class_and_path(self):
        result = pds.classify_pds("do-178c", True, True)
        self.assertEqual(result["reuse_class"], "modified-pds")
        self.assertIn("changed scope", result["credit_path"])
        self.assertIn("affected interfaces", result["credit_path"])

    def test_level_upgrade_regardless_of_modified_flag(self):
        for modified in (False, True):
            with self.subTest(modified=modified):
                result = pds.classify_pds("do-178c", modified, False)
                self.assertEqual(result["reuse_class"], "level-upgrade")

    def test_level_upgrade_credit_path(self):
        result = pds.classify_pds("do-178c", False, False)
        self.assertIn("additional verification", result["credit_path"])
        self.assertIn("higher", result["credit_path"])

    def test_classify_dict_keys(self):
        result = pds.classify_pds("do-178c", True, True)
        self.assertEqual(sorted(result.keys()), ["credit_path", "reuse_class"])

    def test_origin_standard_non_string_valueerror(self):
        with self.assertRaises(ValueError):
            pds.classify_pds(42, False, True)

    def test_origin_standard_empty_and_blank_valueerror(self):
        for origin in ("", "   "):
            with self.subTest(origin=origin):
                with self.assertRaises(ValueError):
                    pds.classify_pds(origin, False, True)

    def test_non_bool_flags_valueerror(self):
        with self.assertRaises(ValueError):
            pds.classify_pds("do-178c", 1, True)


class DeltaObjectiveCoverageTests(unittest.TestCase):
    """Coverage ratio, delta count and verdict contracts."""

    def test_anchor_ratio_delta_and_verdict(self):
        result = pds.delta_objective_coverage(24, 19)
        self.assertEqual(result["coverage_ratio"], 0.7917)
        self.assertEqual(result["delta_objectives"], 5)
        self.assertEqual(result["required"], 24)
        self.assertEqual(result["covered"], 19)
        self.assertEqual(result["verdict"], "delta-qualification-required")

    def test_full_coverage_and_flip_boundary(self):
        full = pds.delta_objective_coverage(24, 24)
        self.assertEqual(full["coverage_ratio"], 1.0)
        self.assertEqual(full["delta_objectives"], 0)
        self.assertEqual(full["verdict"], "full-coverage")
        self.assertEqual(
            pds.delta_objective_coverage(19, 19)["verdict"], "full-coverage"
        )

    def test_doubling_inputs_keeps_ratio(self):
        small = pds.delta_objective_coverage(24, 19)
        large = pds.delta_objective_coverage(48, 38)
        self.assertEqual(large["coverage_ratio"], small["coverage_ratio"])
        self.assertEqual(large["delta_objectives"], 10)

    def test_ratio_rounds_to_four_decimals(self):
        self.assertEqual(pds.delta_objective_coverage(3, 1)["coverage_ratio"], 0.3333)

    def test_coverage_dict_keys(self):
        result = pds.delta_objective_coverage(24, 19)
        self.assertEqual(
            sorted(result.keys()),
            [
                "coverage_ratio",
                "covered",
                "delta_objectives",
                "required",
                "verdict",
            ],
        )

    def test_required_nonpositive_valueerror(self):
        with self.assertRaises(ValueError):
            pds.delta_objective_coverage(0, 0)
        with self.assertRaises(ValueError):
            pds.delta_objective_coverage(-5, 1)

    def test_covered_negative_valueerror(self):
        with self.assertRaises(ValueError):
            pds.delta_objective_coverage(24, -1)

    def test_covered_exceeds_required_valueerror(self):
        with self.assertRaises(ValueError):
            pds.delta_objective_coverage(24, 25)


class ModifiedScopeTests(unittest.TestCase):
    """Regression scope and fraction contracts."""

    def test_anchor_fractions_and_scope(self):
        result = pds.modified_scope(500, 8000, 2, 12)
        self.assertEqual(result["changed_fraction"], 0.0625)
        self.assertEqual(result["interface_fraction"], 0.1667)
        self.assertEqual(result["scope"], "bounded-regression")

    def test_thirty_percent_change_is_broad(self):
        result = pds.modified_scope(2400, 8000, 2, 12)
        self.assertEqual(result["changed_fraction"], 0.3)
        self.assertEqual(result["scope"], "broad-regression")

    def test_high_interface_fraction_is_broad(self):
        self.assertEqual(pds.modified_scope(100, 8000, 7, 12)["scope"], "broad-regression")

    def test_fraction_limits_are_inclusive(self):
        by_change = pds.modified_scope(1600, 8000, 1, 12)
        self.assertEqual(by_change["changed_fraction"], 0.2)
        self.assertEqual(by_change["scope"], "bounded-regression")
        by_interface = pds.modified_scope(800, 8000, 6, 12)
        self.assertEqual(by_interface["interface_fraction"], 0.5)
        self.assertEqual(by_interface["scope"], "bounded-regression")

    def test_changed_fraction_rounds_to_four_decimals(self):
        self.assertEqual(pds.modified_scope(1, 3, 0, 2)["changed_fraction"], 0.3333)

    def test_zero_changed_loc_bounded(self):
        result = pds.modified_scope(0, 8000, 0, 12)
        self.assertEqual(result["changed_fraction"], 0.0)
        self.assertEqual(result["scope"], "bounded-regression")

    def test_scope_dict_keys(self):
        result = pds.modified_scope(500, 8000, 2, 12)
        self.assertEqual(
            sorted(result.keys()),
            ["changed_fraction", "interface_fraction", "scope"],
        )

    def test_changed_loc_valueerrors(self):
        with self.assertRaises(ValueError):
            pds.modified_scope(-1, 8000, 2, 12)
        with self.assertRaises(ValueError):
            pds.modified_scope(500, 0, 2, 12)
        with self.assertRaises(ValueError):
            pds.modified_scope(8001, 8000, 2, 12)

    def test_touched_valueerrors(self):
        with self.assertRaises(ValueError):
            pds.modified_scope(500, 8000, -1, 12)
        with self.assertRaises(ValueError):
            pds.modified_scope(500, 8000, 13, 12)


class PdsReportAndDeterminismTests(unittest.TestCase):
    """Combined report and determinism contracts."""

    def test_report_combines_all_sections(self):
        result = pds.pds_report("do-178c", True, True, 24, 19, 500, 8000, 2, 12)
        self.assertEqual(result["reuse_class"], "modified-pds")
        self.assertEqual(result["coverage_ratio"], 0.7917)
        self.assertEqual(result["verdict"], "delta-qualification-required")
        self.assertEqual(result["delta_objectives"], 5)
        self.assertEqual(result["changed_fraction"], 0.0625)
        self.assertEqual(result["scope"], "bounded-regression")

    def test_report_unchanged_full_coverage_case(self):
        result = pds.pds_report("do-178c", False, True, 24, 24, 0, 8000, 0, 12)
        self.assertEqual(result["reuse_class"], "unchanged-direct-credit")
        self.assertEqual(result["verdict"], "full-coverage")
        self.assertEqual(result["scope"], "bounded-regression")

    def test_report_dict_keys(self):
        result = pds.pds_report("do-178c", True, True, 24, 19, 500, 8000, 2, 12)
        self.assertEqual(
            sorted(result.keys()),
            [
                "changed_fraction",
                "coverage_ratio",
                "covered",
                "credit_path",
                "delta_objectives",
                "interface_fraction",
                "required",
                "reuse_class",
                "scope",
                "verdict",
            ],
        )

    def test_report_propagates_valueerror(self):
        with self.assertRaises(ValueError):
            pds.pds_report("do-178c", True, True, 24, 30, 500, 8000, 2, 12)

    def test_identical_calls_are_deterministic(self):
        first = pds.pds_report("do-178c", True, True, 24, 19, 500, 8000, 2, 12)
        second = pds.pds_report("do-178c", True, True, 24, 19, 500, 8000, 2, 12)
        self.assertEqual(first, second)
        self.assertEqual(
            pds.delta_objective_coverage(24, 19)["coverage_ratio"],
            pds.delta_objective_coverage(24, 19)["coverage_ratio"],
        )


if __name__ == "__main__":
    unittest.main()
