#!/usr/bin/env python3
"""Gate 3 contract test: ECSS-E-ST-20C clause 4.3.2 electrical design
documentation set.

Exercises scripts/e20_electrical_design_documentation_set_logic.py
(stdlib unittest, offline). Contract: docs/harness-contract.md gate 3 --
the owed-analysis set is unconditional for worst case and reliability
and conditional on dissipation, dose and external interfaces for the
other three, with a negative dissipation or dose raising; worst-case
stacking adds tolerance, temperature drift and ageing arithmetically
for extreme value and in quadrature for root sum square, applies them
in the adverse direction, and raises on a non-positive nominal, a
negative fraction, an unknown direction or an unknown method; derating
margin is measured against the derated limit and raises outside its
valid input domain; radiation design margin is a dose ratio and raises
on a non-positive mission dose; report maturity flags absent, not-yet-
issued and stale reports against the milestone; and the documentation
set is complete only when all three finding lists are empty.
"""

import os
import sys
import unittest

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import e20_electrical_design_documentation_set_logic as ds  # noqa: E402


class NormalizeAnalysisKindTest(unittest.TestCase):
    def test_canonical_kind_passes_through(self):
        self.assertEqual(ds.normalize_analysis_kind("worst_case"), "worst_case")

    def test_hyphen_and_case_are_normalized(self):
        self.assertEqual(ds.normalize_analysis_kind("Worst-Case"), "worst_case")

    def test_unknown_kind_raises(self):
        with self.assertRaises(ValueError):
            ds.normalize_analysis_kind("astrology")

    def test_non_string_kind_raises(self):
        with self.assertRaises(ValueError):
            ds.normalize_analysis_kind(3.14)


class RequiredAnalysesTest(unittest.TestCase):
    def test_inert_item_owes_only_the_unconditional_pair(self):
        owed = ds.required_analyses(
            {"power_dissipation_w": 0.0, "mission_dose_krad": 0.0}
        )
        self.assertEqual(owed, ("worst_case", "reliability"))

    def test_dissipation_adds_thermal(self):
        owed = ds.required_analyses({"power_dissipation_w": 2.5})
        self.assertIn("thermal", owed)
        self.assertNotIn("radiation", owed)

    def test_mission_dose_adds_radiation(self):
        owed = ds.required_analyses({"mission_dose_krad": 12.0})
        self.assertIn("radiation", owed)

    def test_external_interfaces_add_electromagnetic(self):
        owed = ds.required_analyses({"has_external_interfaces": True})
        self.assertIn("electromagnetic", owed)

    def test_full_item_owes_all_five_in_canonical_order(self):
        owed = ds.required_analyses(
            {
                "power_dissipation_w": 4.0,
                "mission_dose_krad": 30.0,
                "has_external_interfaces": True,
            }
        )
        self.assertEqual(owed, ds.ANALYSIS_ORDER)

    def test_negative_dissipation_raises(self):
        with self.assertRaises(ValueError):
            ds.required_analyses({"power_dissipation_w": -0.1})

    def test_negative_dose_raises(self):
        with self.assertRaises(ValueError):
            ds.required_analyses({"mission_dose_krad": -5.0})


class WorstCaseValueTest(unittest.TestCase):
    def test_extreme_value_high_side_adds_contributions(self):
        value = ds.worst_case_value(10.0, 0.01, 0.0002, 50.0, 0.02, "high")
        self.assertAlmostEqual(value, 10.0 * 1.04, places=9)

    def test_extreme_value_low_side_subtracts_contributions(self):
        value = ds.worst_case_value(10.0, 0.01, 0.0002, 50.0, 0.02, "low")
        self.assertAlmostEqual(value, 10.0 * 0.96, places=9)

    def test_root_sum_square_is_less_conservative(self):
        extreme = ds.worst_case_value(
            10.0, 0.03, 0.0, 0.0, 0.04, "high", "extreme_value"
        )
        quadrature = ds.worst_case_value(
            10.0, 0.03, 0.0, 0.0, 0.04, "high", "root_sum_square"
        )
        self.assertAlmostEqual(extreme, 10.7, places=9)
        self.assertAlmostEqual(quadrature, 10.5, places=9)
        self.assertLess(quadrature, extreme)

    def test_negative_temperature_coefficient_uses_magnitude(self):
        rising = ds.worst_case_value(5.0, 0.0, 0.001, 20.0, 0.0, "high")
        falling = ds.worst_case_value(5.0, 0.0, -0.001, 20.0, 0.0, "high")
        self.assertAlmostEqual(rising, falling, places=12)

    def test_zero_drift_returns_nominal(self):
        self.assertAlmostEqual(
            ds.worst_case_value(3.3, 0.0, 0.0, 0.0, 0.0, "high"), 3.3, places=12
        )

    def test_non_positive_nominal_raises(self):
        with self.assertRaises(ValueError):
            ds.worst_case_value(0.0, 0.01, 0.0, 0.0, 0.0, "high")

    def test_negative_tolerance_raises(self):
        with self.assertRaises(ValueError):
            ds.worst_case_value(1.0, -0.01, 0.0, 0.0, 0.0, "high")

    def test_negative_ageing_raises(self):
        with self.assertRaises(ValueError):
            ds.worst_case_value(1.0, 0.01, 0.0, 0.0, -0.02, "high")

    def test_negative_temperature_excursion_raises(self):
        with self.assertRaises(ValueError):
            ds.worst_case_value(1.0, 0.01, 0.001, -10.0, 0.0, "high")

    def test_unknown_direction_raises(self):
        with self.assertRaises(ValueError):
            ds.worst_case_value(1.0, 0.01, 0.0, 0.0, 0.0, "sideways")

    def test_unknown_stacking_method_raises(self):
        with self.assertRaises(ValueError):
            ds.worst_case_value(1.0, 0.01, 0.0, 0.0, 0.0, "high", "hand_wave")


class DeratingMarginTest(unittest.TestCase):
    def test_comfortable_part_has_positive_margin(self):
        self.assertAlmostEqual(
            ds.derating_margin(30.0, 100.0, 0.5), 0.4, places=9
        )

    def test_part_exactly_at_derated_limit_has_zero_margin(self):
        self.assertAlmostEqual(
            ds.derating_margin(50.0, 100.0, 0.5), 0.0, places=12
        )

    def test_part_under_rating_but_over_derated_limit_is_negative(self):
        self.assertLess(ds.derating_margin(70.0, 100.0, 0.5), 0.0)

    def test_non_positive_rating_raises(self):
        with self.assertRaises(ValueError):
            ds.derating_margin(10.0, 0.0, 0.5)

    def test_negative_applied_stress_raises(self):
        with self.assertRaises(ValueError):
            ds.derating_margin(-1.0, 100.0, 0.5)

    def test_derating_factor_above_one_raises(self):
        with self.assertRaises(ValueError):
            ds.derating_margin(10.0, 100.0, 1.2)

    def test_zero_derating_factor_raises(self):
        with self.assertRaises(ValueError):
            ds.derating_margin(10.0, 100.0, 0.0)


class RadiationDesignMarginTest(unittest.TestCase):
    def test_ratio_is_rated_over_mission(self):
        self.assertAlmostEqual(
            ds.radiation_design_margin(100.0, 25.0), 4.0, places=9
        )

    def test_negative_rating_raises(self):
        with self.assertRaises(ValueError):
            ds.radiation_design_margin(-1.0, 10.0)

    def test_non_positive_mission_dose_raises(self):
        with self.assertRaises(ValueError):
            ds.radiation_design_margin(100.0, 0.0)


def _reports(state="issued", revision="C"):
    return {
        kind: {"state": state, "design_revision": revision}
        for kind in ds.ANALYSIS_ORDER
    }


class ReportMaturityFindingsTest(unittest.TestCase):
    def test_issued_and_current_reports_have_no_finding(self):
        findings = ds.report_maturity_findings(
            "PCU-1", ("worst_case", "reliability"), _reports(), "cdr", "C"
        )
        self.assertEqual(findings, [])

    def test_absent_report_is_flagged(self):
        findings = ds.report_maturity_findings(
            "PCU-1", ("worst_case", "thermal"), {}, "cdr", "C"
        )
        issues = sorted(finding["issue"] for finding in findings)
        self.assertEqual(
            issues,
            ["missing_design_analysis_report", "missing_design_analysis_report"],
        )

    def test_draft_is_acceptable_at_pdr(self):
        findings = ds.report_maturity_findings(
            "PCU-1", ("worst_case",), _reports("draft"), "pdr", "C"
        )
        self.assertEqual(findings, [])

    def test_draft_is_flagged_at_cdr(self):
        findings = ds.report_maturity_findings(
            "PCU-1", ("worst_case",), _reports("draft"), "cdr", "C"
        )
        self.assertEqual(len(findings), 1)
        self.assertEqual(findings[0]["issue"], "design_analysis_report_not_issued")

    def test_stale_revision_is_flagged(self):
        findings = ds.report_maturity_findings(
            "PCU-1", ("worst_case",), _reports("issued", "B"), "cdr", "C"
        )
        self.assertEqual(len(findings), 1)
        self.assertEqual(findings[0]["issue"], "design_analysis_report_stale")

    def test_draft_and_stale_are_reported_together(self):
        findings = ds.report_maturity_findings(
            "PCU-1", ("worst_case",), _reports("draft", "B"), "qr", "C"
        )
        self.assertEqual(len(findings), 2)

    def test_unknown_milestone_raises(self):
        with self.assertRaises(ValueError):
            ds.report_maturity_findings(
                "PCU-1", ("worst_case",), _reports(), "srr", "C"
            )

    def test_unknown_report_kind_raises(self):
        with self.assertRaises(ValueError):
            ds.report_maturity_findings(
                "PCU-1",
                ("worst_case",),
                {"astrology": {"state": "issued", "design_revision": "C"}},
                "cdr",
                "C",
            )

    def test_unknown_report_state_raises(self):
        with self.assertRaises(ValueError):
            ds.report_maturity_findings(
                "PCU-1",
                ("worst_case",),
                {"worst_case": {"state": "nearly", "design_revision": "C"}},
                "cdr",
                "C",
            )


class MarginFindingsTest(unittest.TestCase):
    def test_healthy_margins_produce_no_finding(self):
        findings = ds.margin_findings(
            "PCU-1",
            [
                {
                    "part": "R12",
                    "applied_stress": 0.2,
                    "rated_stress": 1.0,
                    "derating_factor": 0.5,
                }
            ],
            {"part": "U3", "rated_dose_krad": 100.0, "mission_dose_krad": 20.0},
        )
        self.assertEqual(findings, [])

    def test_overstressed_part_is_flagged(self):
        findings = ds.margin_findings(
            "PCU-1",
            [
                {
                    "part": "R12",
                    "applied_stress": 0.8,
                    "rated_stress": 1.0,
                    "derating_factor": 0.5,
                }
            ],
            None,
        )
        self.assertEqual(len(findings), 1)
        self.assertEqual(findings[0]["issue"], "part_derating_limit_exceeded")
        self.assertAlmostEqual(findings[0]["margin"], -0.6, places=9)

    def test_thin_radiation_margin_is_flagged(self):
        findings = ds.margin_findings(
            "PCU-1",
            (),
            {"part": "U3", "rated_dose_krad": 30.0, "mission_dose_krad": 20.0},
        )
        self.assertEqual(len(findings), 1)
        self.assertEqual(
            findings[0]["issue"], "radiation_design_margin_below_minimum"
        )
        self.assertAlmostEqual(findings[0]["margin"], 1.5, places=9)

    def test_margin_exactly_at_minimum_passes(self):
        findings = ds.margin_findings(
            "PCU-1",
            (),
            {"part": "U3", "rated_dose_krad": 40.0, "mission_dose_krad": 20.0},
        )
        self.assertEqual(findings, [])

    def test_absent_radiation_case_is_skipped(self):
        self.assertEqual(ds.margin_findings("PCU-1", (), None), [])


def _item(**overrides):
    item = {
        "item_id": "PCU-1",
        "power_dissipation_w": 3.0,
        "mission_dose_krad": 20.0,
        "has_external_interfaces": True,
        "design_revision": "C",
        "derating_cases": [
            {
                "part": "R12",
                "applied_stress": 0.2,
                "rated_stress": 1.0,
                "derating_factor": 0.5,
            }
        ],
        "radiation_case": {
            "part": "U3",
            "rated_dose_krad": 100.0,
            "mission_dose_krad": 20.0,
        },
    }
    item.update(overrides)
    return item


class DesignDocumentationReviewTest(unittest.TestCase):
    def test_complete_set_is_accepted(self):
        review = ds.design_documentation_review(_item(), _reports(), "cdr")
        self.assertEqual(review["owed"], ds.ANALYSIS_ORDER)
        self.assertEqual(review["completeness"], [])
        self.assertEqual(review["maturity"], [])
        self.assertEqual(review["margin"], [])
        self.assertTrue(ds.is_documentation_set_complete(review))

    def test_missing_report_breaks_completeness(self):
        reports = _reports()
        del reports["electromagnetic"]
        review = ds.design_documentation_review(_item(), reports, "cdr")
        self.assertEqual(len(review["completeness"]), 1)
        self.assertFalse(ds.is_documentation_set_complete(review))

    def test_unowed_analysis_absence_is_not_a_finding(self):
        item = _item(
            power_dissipation_w=0.0,
            mission_dose_krad=0.0,
            has_external_interfaces=False,
            radiation_case=None,
        )
        reports = {
            "worst_case": {"state": "issued", "design_revision": "C"},
            "reliability": {"state": "issued", "design_revision": "C"},
        }
        review = ds.design_documentation_review(item, reports, "ar")
        self.assertEqual(review["owed"], ("worst_case", "reliability"))
        self.assertTrue(ds.is_documentation_set_complete(review))

    def test_stale_report_breaks_maturity_only(self):
        review = ds.design_documentation_review(
            _item(), _reports("issued", "B"), "cdr"
        )
        self.assertEqual(review["completeness"], [])
        self.assertEqual(len(review["maturity"]), len(ds.ANALYSIS_ORDER))
        self.assertFalse(ds.is_documentation_set_complete(review))

    def test_margin_breach_breaks_the_set_with_full_reports(self):
        item = _item(
            radiation_case={
                "part": "U3",
                "rated_dose_krad": 10.0,
                "mission_dose_krad": 20.0,
            }
        )
        review = ds.design_documentation_review(item, _reports(), "cdr")
        self.assertEqual(review["completeness"], [])
        self.assertEqual(review["maturity"], [])
        self.assertEqual(len(review["margin"]), 1)
        self.assertFalse(ds.is_documentation_set_complete(review))


if __name__ == "__main__":
    unittest.main()
