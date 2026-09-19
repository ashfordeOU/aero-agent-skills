#!/usr/bin/env python3
"""Gate 3 contract test for e2040-device-netlist-generation.

Offline, deterministic, stdlib unittest. Run:
    python3 test_e2040_device_netlist_generation.py
"""

import os
import sys
import unittest

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from e2040_device_netlist_generation_logic import (  # noqa: E402
    ADVISORY,
    BLOCKING,
    INFORMATIONAL,
    WARNING_CATEGORIES,
    evaluate_netlist_generation,
    normalize_warning_category,
    resources_over_budget,
    run_is_reproducible,
    undispositioned_warnings,
    unpinned_inputs,
    utilisation_ratio,
    validate_file_set,
    validate_library,
    validate_outputs,
    validate_tool,
    validate_utilisation,
    validate_warnings,
    within_utilisation_budget,
)


def base_run():
    return {
        "sources": [
            {"id": "core.vhd", "revision": "r41"},
            {"id": "interface.vhd", "revision": "r17"},
        ],
        "constraints": [{"id": "timing.sdc", "revision": "r9"}],
        "tool": {"name": "synthesis-tool", "version": "2026.1", "options": "effort high"},
        "technology_library": {"id": "lib-65nm-rh", "version": "4.2"},
        "outputs": {
            "netlist": "device-netlist.v",
            "reports": ["area-report.txt", "timing-report.txt"],
        },
        "utilisation": [
            {"resource": "logic-cells", "used": 60000.0, "available": 100000.0,
             "budget": 0.8},
            {"resource": "block-memory", "used": 40.0, "available": 100.0,
             "budget": 0.5},
        ],
        "unresolved_cells": [],
        "warnings": [
            {"id": "W-1", "category": "advisory", "subject": "latch inferred"},
            {"id": "W-2", "category": "blocking", "disposition": "constraint added"},
        ],
    }


def codes(result):
    return sorted({f["code"] for f in result["findings"]})


class TestWarningCategoryFolding(unittest.TestCase):
    def test_error_folds_to_blocking(self):
        self.assertEqual(normalize_warning_category("Error"), BLOCKING)

    def test_warning_folds_to_advisory(self):
        self.assertEqual(normalize_warning_category("warning"), ADVISORY)

    def test_note_folds_to_informational(self):
        self.assertEqual(normalize_warning_category("note"), INFORMATIONAL)

    def test_unknown_category_rejected(self):
        with self.assertRaises(ValueError):
            normalize_warning_category("interesting")

    def test_three_categories_are_the_whole_set(self):
        self.assertEqual(len(WARNING_CATEGORIES), 3)


class TestUtilisationArithmetic(unittest.TestCase):
    def test_a_ratio_is_used_over_available(self):
        self.assertAlmostEqual(utilisation_ratio(60000.0, 100000.0), 0.6, places=12)

    def test_zero_available_rejected(self):
        with self.assertRaises(ValueError):
            utilisation_ratio(1.0, 0.0)

    def test_negative_used_rejected(self):
        with self.assertRaises(ValueError):
            utilisation_ratio(-1.0, 100.0)

    def test_a_ratio_inside_its_budget_passes(self):
        self.assertTrue(within_utilisation_budget(0.6, 0.8))

    def test_a_ratio_exactly_on_its_budget_is_inside(self):
        self.assertTrue(within_utilisation_budget(0.8, 0.8))

    def test_a_computed_two_thirds_on_a_two_thirds_budget_is_inside(self):
        self.assertTrue(within_utilisation_budget(2 / 3, 2 / 3))

    def test_a_ratio_over_its_budget_fails(self):
        self.assertFalse(within_utilisation_budget(0.81, 0.8))

    def test_a_budget_above_one_rejected(self):
        with self.assertRaises(ValueError):
            within_utilisation_budget(0.5, 1.5)


class TestInputValidation(unittest.TestCase):
    def test_sources_resolve_in_declared_order(self):
        sources = validate_file_set("sources", base_run()["sources"])
        self.assertEqual([s["id"] for s in sources], ["core.vhd", "interface.vhd"])

    def test_duplicate_source_id_rejected(self):
        records = base_run()["sources"]
        records.append(dict(records[0]))
        with self.assertRaises(ValueError):
            validate_file_set("sources", records)

    def test_unknown_source_key_rejected(self):
        records = base_run()["sources"]
        records[0]["author"] = "someone"
        with self.assertRaises(ValueError):
            validate_file_set("sources", records)

    def test_tool_resolves(self):
        tool = validate_tool(base_run()["tool"])
        self.assertEqual(tool["version"], "2026.1")

    def test_tool_without_a_name_rejected(self):
        with self.assertRaises(ValueError):
            validate_tool({"version": "2026.1"})

    def test_unknown_tool_key_rejected(self):
        with self.assertRaises(ValueError):
            validate_tool({"name": "t", "licence": "x"})

    def test_library_without_an_id_rejected(self):
        with self.assertRaises(ValueError):
            validate_library({"version": "4.2"})

    def test_outputs_resolve_and_drop_repeats(self):
        outputs = validate_outputs({"netlist": "n.v", "reports": ["a.txt", "a.txt"]})
        self.assertEqual(outputs["reports"], ["a.txt"])

    def test_non_list_reports_rejected(self):
        with self.assertRaises(ValueError):
            validate_outputs({"netlist": "n.v", "reports": "a.txt"})

    def test_duplicate_utilisation_resource_rejected(self):
        records = base_run()["utilisation"]
        records.append(dict(records[0]))
        with self.assertRaises(ValueError):
            validate_utilisation(records)

    def test_utilisation_budget_defaults_to_the_whole_device(self):
        figures = validate_utilisation([{"resource": "r", "used": 1.0, "available": 2.0}])
        self.assertAlmostEqual(figures[0]["budget"], 1.0, places=12)

    def test_duplicate_warning_id_rejected(self):
        records = base_run()["warnings"]
        records.append(dict(records[0]))
        with self.assertRaises(ValueError):
            validate_warnings(records)

    def test_no_warnings_is_an_empty_list(self):
        self.assertEqual(validate_warnings(None), [])


class TestReproducibility(unittest.TestCase):
    def setUp(self):
        run = base_run()
        self.sources = validate_file_set("sources", run["sources"])
        self.constraints = validate_file_set("constraints", run["constraints"])
        self.tool = validate_tool(run["tool"])
        self.library = validate_library(run["technology_library"])

    def test_a_fully_pinned_run_is_reproducible(self):
        self.assertTrue(
            run_is_reproducible(self.sources, self.constraints, self.tool, self.library)
        )
        self.assertEqual(
            unpinned_inputs(self.sources, self.constraints, self.tool, self.library), []
        )

    def test_an_unpinned_source_breaks_reproducibility(self):
        records = base_run()["sources"]
        records[0]["revision"] = ""
        sources = validate_file_set("sources", records)
        self.assertFalse(
            run_is_reproducible(sources, self.constraints, self.tool, self.library)
        )
        self.assertIn(
            ("source", "core.vhd"),
            unpinned_inputs(sources, self.constraints, self.tool, self.library),
        )

    def test_an_unpinned_library_breaks_reproducibility(self):
        library = validate_library({"id": "lib-65nm-rh"})
        self.assertFalse(
            run_is_reproducible(self.sources, self.constraints, self.tool, library)
        )
        self.assertIn(
            ("technology-library", "lib-65nm-rh"),
            unpinned_inputs(self.sources, self.constraints, self.tool, library),
        )

    def test_an_unpinned_tool_breaks_reproducibility(self):
        tool = validate_tool({"name": "synthesis-tool"})
        self.assertFalse(
            run_is_reproducible(self.sources, self.constraints, tool, self.library)
        )

    def test_an_empty_constraint_set_breaks_reproducibility(self):
        self.assertFalse(
            run_is_reproducible(self.sources, [], self.tool, self.library)
        )


class TestBudgetsAndWarnings(unittest.TestCase):
    def test_no_resource_is_over_budget_in_the_base_run(self):
        figures = validate_utilisation(base_run()["utilisation"])
        self.assertEqual(resources_over_budget(figures), [])

    def test_a_resource_over_budget_is_found(self):
        records = base_run()["utilisation"]
        records[0]["used"] = 90000.0
        figures = validate_utilisation(records)
        found = resources_over_budget(figures)
        self.assertEqual(len(found), 1)
        self.assertEqual(found[0][0], "logic-cells")

    def test_a_resource_exactly_on_budget_is_not_over(self):
        records = base_run()["utilisation"]
        records[0]["used"] = 80000.0
        figures = validate_utilisation(records)
        self.assertEqual(resources_over_budget(figures), [])

    def test_an_answered_blocking_warning_is_not_reported(self):
        warnings = validate_warnings(base_run()["warnings"])
        self.assertEqual(undispositioned_warnings(warnings), [])

    def test_an_unanswered_blocking_warning_is_reported(self):
        records = base_run()["warnings"]
        records[1]["disposition"] = ""
        warnings = validate_warnings(records)
        self.assertEqual(undispositioned_warnings(warnings), ["W-2"])

    def test_an_unanswered_advisory_warning_is_not_reported(self):
        warnings = validate_warnings(
            [{"id": "W-5", "category": "advisory"}]
        )
        self.assertEqual(undispositioned_warnings(warnings), [])


class TestEvaluateNetlistGeneration(unittest.TestCase):
    def test_a_complete_run_record_is_acceptable(self):
        result = evaluate_netlist_generation(base_run())
        self.assertTrue(result["acceptable"])
        self.assertTrue(result["reproducible"])
        self.assertEqual(result["findings"], [])

    def test_figures_reach_the_result(self):
        result = evaluate_netlist_generation(base_run())
        self.assertEqual(result["source_count"], 2)
        self.assertAlmostEqual(result["utilisation"]["logic-cells"], 0.6, places=12)

    def test_an_unpinned_input_is_reported(self):
        run = base_run()
        run["technology_library"] = {"id": "lib-65nm-rh"}
        result = evaluate_netlist_generation(run)
        self.assertIn("input-not-pinned", codes(result))
        self.assertFalse(result["reproducible"])

    def test_a_run_without_constraints_is_reported(self):
        run = base_run()
        run["constraints"] = []
        result = evaluate_netlist_generation(run)
        self.assertIn("run-without-constraints", codes(result))

    def test_an_unrecorded_netlist_is_reported(self):
        run = base_run()
        run["outputs"]["netlist"] = ""
        result = evaluate_netlist_generation(run)
        self.assertIn("netlist-output-not-recorded", codes(result))

    def test_unrecorded_reports_are_reported(self):
        run = base_run()
        run["outputs"]["reports"] = []
        result = evaluate_netlist_generation(run)
        self.assertIn("synthesis-reports-not-recorded", codes(result))

    def test_an_unresolved_cell_is_reported(self):
        run = base_run()
        run["unresolved_cells"] = ["custom_pll"]
        result = evaluate_netlist_generation(run)
        self.assertIn("unresolved-cell-in-netlist", codes(result))
        self.assertEqual(result["unresolved_cells"], ["custom_pll"])

    def test_a_resource_over_budget_is_reported(self):
        run = base_run()
        run["utilisation"][0]["used"] = 90000.0
        result = evaluate_netlist_generation(run)
        self.assertIn("resource-over-budget", codes(result))

    def test_a_resource_exactly_on_budget_is_not_reported(self):
        run = base_run()
        run["utilisation"][0]["used"] = 80000.0
        result = evaluate_netlist_generation(run)
        self.assertNotIn("resource-over-budget", codes(result))

    def test_an_unanswered_blocking_warning_is_reported(self):
        run = base_run()
        run["warnings"][1]["disposition"] = ""
        result = evaluate_netlist_generation(run)
        self.assertIn("blocking-warning-without-disposition", codes(result))

    def test_unknown_run_key_rejected(self):
        run = base_run()
        run["machine"] = "build-host"
        with self.assertRaises(ValueError):
            evaluate_netlist_generation(run)

    def test_missing_outputs_rejected(self):
        run = base_run()
        del run["outputs"]
        with self.assertRaises(ValueError):
            evaluate_netlist_generation(run)

    def test_a_run_with_no_source_rejected(self):
        run = base_run()
        run["sources"] = []
        with self.assertRaises(ValueError):
            evaluate_netlist_generation(run)

    def test_non_list_unresolved_cells_rejected(self):
        run = base_run()
        run["unresolved_cells"] = "custom_pll"
        with self.assertRaises(ValueError):
            evaluate_netlist_generation(run)

    def test_non_mapping_run_rejected(self):
        with self.assertRaises(ValueError):
            evaluate_netlist_generation([("sources", [])])


if __name__ == "__main__":
    unittest.main()
