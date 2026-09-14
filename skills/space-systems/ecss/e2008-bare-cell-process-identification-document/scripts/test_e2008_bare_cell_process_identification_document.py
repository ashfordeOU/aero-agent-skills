#!/usr/bin/env python3
"""Contract test for the bare cell process identification document (offline).

Walks the clause workflow step by step: the control parameter band and
its two ways of failing, the ranked process step verdict, the line
binding that makes a step belong to other hardware, the coverage of the
required bare cell process set, the design baseline the document names,
the issue date against the campaign start, and the roll-up into one
document verdict. This is the gate 3 review evidence for the leaf.
"""

import copy
import unittest

from e2008_bare_cell_process_identification_document_logic import (
    DOCUMENT_ACCEPTED,
    DOCUMENT_REJECTED,
    REQUIRED_PROCESS_STEPS,
    STEP_ACCEPTED,
    STEP_NO_CONTROLLING_DOCUMENT,
    STEP_NO_PARAMETER,
    STEP_OFF_QUALIFIED_LINE,
    STEP_PARAMETER_UNCONTROLLED,
    assess_bare_cell_process_document,
    assess_process_step,
    design_baseline_match,
    evaluate_control_parameter,
    issue_precedes_campaign,
    parse_iso_date,
    process_coverage,
)

LINE = "LINE-A"


def _parameter(name="anneal-temperature", nominal=500.0, low=475.0, high=525.0):
    return {"name": name, "nominal": nominal, "band_low": low, "band_high": high}


def _step(name, **overrides):
    record = {
        "name": name,
        "controlling_document": "PD-%s" % name,
        "production_line": LINE,
        "control_parameters": [_parameter()],
    }
    record.update(overrides)
    return record


def _document(steps=None, **overrides):
    case = {
        "qualified_design_id": "CELL-3J-42",
        "document_design_id": "CELL-3J-42",
        "qualified_line": LINE,
        "issue_date": "2026-01-10",
        "campaign_start_date": "2026-02-01",
        "process_steps": steps
        if steps is not None
        else [_step(name) for name in REQUIRED_PROCESS_STEPS],
    }
    case.update(overrides)
    return copy.deepcopy(case)


class ControlParameterTests(unittest.TestCase):
    def test_a_band_bracketing_its_nominal_is_controlled(self):
        graded = evaluate_control_parameter(_parameter(), 0.10)
        self.assertTrue(graded["controlled"])
        self.assertAlmostEqual(graded["band_width_fraction"], 0.10, places=9)

    def test_a_band_exactly_on_the_width_cap_is_accepted(self):
        graded = evaluate_control_parameter(
            _parameter(nominal=100.0, low=95.0, high=105.0), 0.10
        )
        self.assertAlmostEqual(graded["band_width_fraction"], 0.10, places=9)
        self.assertTrue(graded["controlled"])

    def test_a_band_excluding_its_own_nominal_is_reported(self):
        graded = evaluate_control_parameter(
            _parameter(nominal=500.0, low=520.0, high=530.0), 0.10
        )
        self.assertFalse(graded["brackets_nominal"])
        self.assertFalse(graded["controlled"])
        self.assertTrue(graded["findings"])

    def test_a_band_too_wide_to_control_anything_is_reported(self):
        graded = evaluate_control_parameter(
            _parameter(nominal=500.0, low=100.0, high=900.0), 0.10
        )
        self.assertTrue(graded["brackets_nominal"])
        self.assertFalse(graded["controlled"])

    def test_an_inverted_band_rejected(self):
        with self.assertRaises(ValueError):
            evaluate_control_parameter(
                _parameter(nominal=500.0, low=525.0, high=475.0), 0.10
            )

    def test_a_zero_nominal_rejected(self):
        with self.assertRaises(ValueError):
            evaluate_control_parameter(
                _parameter(nominal=0.0, low=-1.0, high=1.0), 0.10
            )


class ProcessStepTests(unittest.TestCase):
    def test_a_controlled_step_on_the_qualified_line_is_accepted(self):
        graded = assess_process_step(_step("contact-anneal"), LINE)
        self.assertEqual(graded["verdict"], STEP_ACCEPTED)
        self.assertEqual(graded["findings"], [])

    def test_a_step_citing_no_production_document_ranks_worst(self):
        graded = assess_process_step(
            _step("contact-anneal", controlling_document=None), LINE
        )
        self.assertEqual(graded["verdict"], STEP_NO_CONTROLLING_DOCUMENT)

    def test_a_step_declaring_no_parameter_holds_nothing(self):
        graded = assess_process_step(
            _step("contact-anneal", control_parameters=[]), LINE
        )
        self.assertEqual(graded["verdict"], STEP_NO_PARAMETER)

    def test_an_uncontrolled_parameter_names_itself(self):
        graded = assess_process_step(
            _step(
                "contact-anneal",
                control_parameters=[
                    _parameter(name="anneal-time", nominal=60.0, low=1.0, high=600.0)
                ],
            ),
            LINE,
        )
        self.assertEqual(graded["verdict"], STEP_PARAMETER_UNCONTROLLED)
        self.assertEqual(graded["uncontrolled_parameters"], ["anneal-time"])

    def test_a_step_run_on_another_line_is_reported(self):
        graded = assess_process_step(
            _step("contact-anneal", production_line="LINE-B"), LINE
        )
        self.assertEqual(graded["verdict"], STEP_OFF_QUALIFIED_LINE)
        self.assertFalse(graded["on_qualified_line"])

    def test_a_step_outside_the_required_set_rejected(self):
        with self.assertRaises(ValueError):
            assess_process_step(_step("painting-the-shipping-crate"), LINE)


class CoverageTests(unittest.TestCase):
    def test_the_full_set_covers_everything(self):
        coverage = process_coverage(list(REQUIRED_PROCESS_STEPS))
        self.assertEqual(coverage["missing_steps"], [])
        self.assertAlmostEqual(coverage["coverage_share"], 1.0, places=12)

    def test_a_missing_step_is_named(self):
        declared = [n for n in REQUIRED_PROCESS_STEPS if n != "mesa-edge-isolation"]
        coverage = process_coverage(declared)
        self.assertEqual(coverage["missing_steps"], ["mesa-edge-isolation"])
        self.assertAlmostEqual(
            coverage["coverage_share"],
            (len(REQUIRED_PROCESS_STEPS) - 1) / len(REQUIRED_PROCESS_STEPS),
            places=12,
        )

    def test_an_empty_required_set_rejected(self):
        with self.assertRaises(ValueError):
            process_coverage(["wafer-preparation"], ())


class BaselineAndDateTests(unittest.TestCase):
    def test_matching_design_identifiers_pass(self):
        self.assertTrue(design_baseline_match("CELL-3J-42", "CELL-3J-42")["matches"])

    def test_a_document_for_another_design_is_reported(self):
        baseline = design_baseline_match("CELL-3J-41", "CELL-3J-42")
        self.assertFalse(baseline["matches"])
        self.assertTrue(baseline["findings"])

    def test_an_issue_date_before_the_campaign_passes(self):
        order = issue_precedes_campaign("2026-01-10", "2026-02-01")
        self.assertTrue(order["precedes_campaign"])

    def test_an_issue_date_after_the_campaign_is_reported(self):
        order = issue_precedes_campaign("2026-03-10", "2026-02-01")
        self.assertFalse(order["precedes_campaign"])
        self.assertTrue(order["findings"])

    def test_a_malformed_date_rejected(self):
        with self.assertRaises(ValueError):
            parse_iso_date("10 January 2026")

    def test_a_date_outside_the_calendar_rejected(self):
        with self.assertRaises(ValueError):
            parse_iso_date("2026-13-01")


class DocumentRollUpTests(unittest.TestCase):
    def test_a_complete_document_is_accepted(self):
        result = assess_bare_cell_process_document(_document())
        self.assertEqual(result["verdict"], DOCUMENT_ACCEPTED)
        self.assertEqual(result["findings"], [])
        self.assertAlmostEqual(result["accepted_share"], 1.0, places=12)

    def test_a_missing_step_rejects_the_document(self):
        steps = [
            _step(name)
            for name in REQUIRED_PROCESS_STEPS
            if name != "antireflective-coating"
        ]
        result = assess_bare_cell_process_document(_document(steps))
        self.assertEqual(result["verdict"], DOCUMENT_REJECTED)
        self.assertFalse(result["coverage_meets_minimum"])
        self.assertEqual(result["coverage"]["missing_steps"],
                         ["antireflective-coating"])

    def test_the_weakest_step_is_named_by_rank(self):
        steps = [_step(name) for name in REQUIRED_PROCESS_STEPS]
        steps[0]["production_line"] = "LINE-B"
        steps[1]["controlling_document"] = None
        result = assess_bare_cell_process_document(_document(steps))
        self.assertEqual(result["weakest_step"], steps[1]["name"])
        self.assertIn(STEP_OFF_QUALIFIED_LINE, result["grouped_steps"])

    def test_a_document_for_another_design_rejects_the_campaign(self):
        result = assess_bare_cell_process_document(
            _document(document_design_id="CELL-3J-41")
        )
        self.assertEqual(result["verdict"], DOCUMENT_REJECTED)
        self.assertFalse(result["baseline"]["matches"])

    def test_a_document_issued_after_the_campaign_records_the_build(self):
        result = assess_bare_cell_process_document(
            _document(issue_date="2026-03-01")
        )
        self.assertEqual(result["verdict"], DOCUMENT_REJECTED)
        self.assertFalse(result["precedence"]["precedes_campaign"])

    def test_a_step_declared_twice_rejected(self):
        steps = [_step(name) for name in REQUIRED_PROCESS_STEPS]
        steps.append(_step("contact-anneal"))
        with self.assertRaises(ValueError):
            assess_bare_cell_process_document(_document(steps))

    def test_an_empty_document_rejected(self):
        with self.assertRaises(ValueError):
            assess_bare_cell_process_document(_document([]))

    def test_a_relaxed_coverage_minimum_accepts_a_partial_document(self):
        steps = [
            _step(name)
            for name in REQUIRED_PROCESS_STEPS
            if name != "cell-electrical-sorting"
        ]
        policy = {"min_coverage_share": 0.5}
        result = assess_bare_cell_process_document(_document(steps, policy=policy))
        self.assertTrue(result["coverage_meets_minimum"])
        self.assertEqual(result["verdict"], DOCUMENT_ACCEPTED)

    def test_non_mapping_case_rejected(self):
        with self.assertRaises(ValueError):
            assess_bare_cell_process_document("the supplier sent the document")


if __name__ == "__main__":
    unittest.main()
