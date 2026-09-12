"""
Gate 3 contract test for alignment-geometry-checks.
Stdlib unittest only — offline, deterministic.
Run: python3 test_alignment_geometry_checks.py
"""

import unittest
import sys
import os

sys.path.insert(0, os.path.dirname(__file__))

from alignment_geometry_checks_logic import (
    AlignmentMeasurement,
    DimensionalStabilityMeasurement,
    GeometryControlMeasurement,
    CheckStatus,
    run_alignment_checks,
    run_dimensional_stability_checks,
    run_geometry_control_checks,
    aggregate_compliance,
)


class TestAlignmentChecks(unittest.TestCase):

    def test_alignment_pass_rotational(self):
        m = AlignmentMeasurement("OPT-1", "rx", 4.0, 10.0, "arcsec")
        result = m.check()
        self.assertEqual(result["status"], CheckStatus.PASS)
        self.assertAlmostEqual(result["margin"], 6.0)

    def test_alignment_pass_translational(self):
        m = AlignmentMeasurement("STR-2", "tx", -0.05, 0.1, "mm")
        result = m.check()
        self.assertEqual(result["status"], CheckStatus.PASS)
        self.assertAlmostEqual(result["margin"], 0.05)

    def test_alignment_pass_at_boundary(self):
        m = AlignmentMeasurement("OPT-3", "ry", 10.0, 10.0, "arcsec")
        result = m.check()
        self.assertEqual(result["status"], CheckStatus.PASS)
        self.assertAlmostEqual(result["margin"], 0.0)

    def test_alignment_fail_exceeds_tolerance(self):
        m = AlignmentMeasurement("OPT-4", "rz", -15.0, 10.0, "arcsec")
        result = m.check()
        self.assertEqual(result["status"], CheckStatus.FAIL)
        self.assertAlmostEqual(result["exceedance"], 5.0)

    def test_alignment_error_zero_tolerance(self):
        m = AlignmentMeasurement("STR-5", "tz", 0.0, 0.0, "mm")
        result = m.check()
        self.assertEqual(result["status"], CheckStatus.ERROR)
        self.assertIn("Non-positive tolerance", result["reason"])

    def test_alignment_error_negative_tolerance(self):
        m = AlignmentMeasurement("STR-6", "ty", 1.0, -5.0, "mm")
        result = m.check()
        self.assertEqual(result["status"], CheckStatus.ERROR)

    def test_alignment_error_unknown_axis(self):
        m = AlignmentMeasurement("OPT-7", "rq", 1.0, 10.0, "arcsec")
        result = m.check()
        self.assertEqual(result["status"], CheckStatus.ERROR)
        self.assertIn("Unknown axis", result["reason"])

    def test_run_alignment_checks_returns_list(self):
        measurements = [
            AlignmentMeasurement("A-1", "rx", 2.0, 5.0, "arcsec"),
            AlignmentMeasurement("A-2", "tx", 0.2, 0.5, "mm"),
        ]
        results = run_alignment_checks(measurements)
        self.assertEqual(len(results), 2)
        for r in results:
            self.assertIn("component_id", r)
            self.assertEqual(r["check_type"], "alignment")
            self.assertEqual(r["status"], CheckStatus.PASS)


class TestDimensionalStabilityChecks(unittest.TestCase):

    def test_stability_pass_thermal(self):
        m = DimensionalStabilityMeasurement("PANEL-1", 500.000, 500.003, 0.01, "thermal")
        result = m.check()
        self.assertEqual(result["status"], CheckStatus.PASS)
        self.assertAlmostEqual(result["dimensional_change_mm"], 0.003)
        self.assertAlmostEqual(result["margin_mm"], 0.007)

    def test_stability_pass_hygroscopic(self):
        m = DimensionalStabilityMeasurement("CFRP-2", 200.0, 199.998, 0.005, "hygroscopic")
        result = m.check()
        self.assertEqual(result["status"], CheckStatus.PASS)
        self.assertAlmostEqual(result["dimensional_change_mm"], 0.002)

    def test_stability_pass_creep(self):
        m = DimensionalStabilityMeasurement("STRUT-3", 1000.0, 1000.001, 0.005, "creep")
        result = m.check()
        self.assertEqual(result["status"], CheckStatus.PASS)

    def test_stability_pass_other(self):
        m = DimensionalStabilityMeasurement("BRKT-4", 50.0, 50.0004, 0.001, "other")
        result = m.check()
        self.assertEqual(result["status"], CheckStatus.PASS)

    def test_stability_fail_exceeds_budget(self):
        m = DimensionalStabilityMeasurement("PANEL-5", 300.0, 300.020, 0.010, "thermal")
        result = m.check()
        self.assertEqual(result["status"], CheckStatus.FAIL)
        self.assertAlmostEqual(result["dimensional_change_mm"], 0.020)
        self.assertAlmostEqual(result["exceedance_mm"], 0.010)

    def test_stability_error_unknown_driver(self):
        m = DimensionalStabilityMeasurement("PANEL-6", 100.0, 100.001, 0.005, "radiation")
        result = m.check()
        self.assertEqual(result["status"], CheckStatus.ERROR)
        self.assertIn("Unknown driver", result["reason"])

    def test_stability_error_zero_budget(self):
        m = DimensionalStabilityMeasurement("PANEL-7", 100.0, 100.001, 0.0, "thermal")
        result = m.check()
        self.assertEqual(result["status"], CheckStatus.ERROR)
        self.assertIn("Non-positive stability budget", result["reason"])

    def test_stability_error_negative_budget(self):
        m = DimensionalStabilityMeasurement("PANEL-8", 100.0, 100.001, -0.005, "creep")
        result = m.check()
        self.assertEqual(result["status"], CheckStatus.ERROR)

    def test_run_stability_checks_returns_list(self):
        measurements = [
            DimensionalStabilityMeasurement("S-1", 100.0, 100.002, 0.005, "thermal"),
            DimensionalStabilityMeasurement("S-2", 200.0, 200.001, 0.005, "hygroscopic"),
        ]
        results = run_dimensional_stability_checks(measurements)
        self.assertEqual(len(results), 2)
        for r in results:
            self.assertIn("component_id", r)
            self.assertEqual(r["check_type"], "dimensional_stability")


class TestGeometryControlChecks(unittest.TestCase):

    def test_geometry_pass_flatness(self):
        m = GeometryControlMeasurement("FACE-1", "flatness", 0.005, 0.010)
        result = m.check()
        self.assertEqual(result["status"], CheckStatus.PASS)
        self.assertAlmostEqual(result["margin_mm"], 0.005)

    def test_geometry_pass_circularity(self):
        m = GeometryControlMeasurement("BORE-2", "circularity", 0.003, 0.008)
        result = m.check()
        self.assertEqual(result["status"], CheckStatus.PASS)

    def test_geometry_pass_runout(self):
        m = GeometryControlMeasurement("SHAFT-3", "runout", 0.007, 0.010)
        result = m.check()
        self.assertEqual(result["status"], CheckStatus.PASS)

    def test_geometry_pass_at_boundary(self):
        m = GeometryControlMeasurement("FACE-4", "straightness", 0.010, 0.010)
        result = m.check()
        self.assertEqual(result["status"], CheckStatus.PASS)
        self.assertAlmostEqual(result["margin_mm"], 0.0)

    def test_geometry_fail_flatness_exceeded(self):
        m = GeometryControlMeasurement("FACE-5", "flatness", 0.015, 0.010)
        result = m.check()
        self.assertEqual(result["status"], CheckStatus.FAIL)
        self.assertAlmostEqual(result["exceedance_mm"], 0.005)

    def test_geometry_fail_perpendicularity(self):
        m = GeometryControlMeasurement("WALL-6", "perpendicularity", 0.020, 0.010)
        result = m.check()
        self.assertEqual(result["status"], CheckStatus.FAIL)
        self.assertAlmostEqual(result["exceedance_mm"], 0.010)

    def test_geometry_error_unknown_type(self):
        m = GeometryControlMeasurement("SURF-7", "ovality", 0.005, 0.010)
        result = m.check()
        self.assertEqual(result["status"], CheckStatus.ERROR)
        self.assertIn("Unknown geometry type", result["reason"])

    def test_geometry_error_zero_allowable(self):
        m = GeometryControlMeasurement("FACE-8", "flatness", 0.005, 0.0)
        result = m.check()
        self.assertEqual(result["status"], CheckStatus.ERROR)
        self.assertIn("Non-positive allowable deviation", result["reason"])

    def test_geometry_error_negative_measured(self):
        m = GeometryControlMeasurement("FACE-9", "flatness", -0.002, 0.010)
        result = m.check()
        self.assertEqual(result["status"], CheckStatus.ERROR)
        self.assertIn("Negative measured deviation", result["reason"])

    def test_run_geometry_checks_returns_list(self):
        measurements = [
            GeometryControlMeasurement("G-1", "flatness", 0.003, 0.010),
            GeometryControlMeasurement("G-2", "parallelism", 0.004, 0.010),
            GeometryControlMeasurement("G-3", "angularity", 0.006, 0.010),
        ]
        results = run_geometry_control_checks(measurements)
        self.assertEqual(len(results), 3)
        for r in results:
            self.assertIn("component_id", r)
            self.assertEqual(r["check_type"], "geometry_control")
            self.assertEqual(r["status"], CheckStatus.PASS)


class TestAggregateCompliance(unittest.TestCase):

    def test_all_pass_gives_overall_pass(self):
        a_results = run_alignment_checks([
            AlignmentMeasurement("C-1", "rx", 2.0, 10.0, "arcsec"),
        ])
        s_results = run_dimensional_stability_checks([
            DimensionalStabilityMeasurement("C-1", 100.0, 100.001, 0.005, "thermal"),
        ])
        g_results = run_geometry_control_checks([
            GeometryControlMeasurement("C-1", "flatness", 0.003, 0.010),
        ])
        summary = aggregate_compliance(a_results, s_results, g_results)
        self.assertEqual(summary["overall_status"], CheckStatus.PASS)
        self.assertEqual(summary["failed"], 0)
        self.assertEqual(summary["errors"], 0)
        self.assertEqual(summary["total_checks"], 3)

    def test_one_failure_gives_overall_fail(self):
        a_results = run_alignment_checks([
            AlignmentMeasurement("C-2", "rx", 20.0, 10.0, "arcsec"),  # fail
        ])
        s_results = run_dimensional_stability_checks([
            DimensionalStabilityMeasurement("C-2", 100.0, 100.001, 0.005, "thermal"),  # pass
        ])
        g_results = run_geometry_control_checks([
            GeometryControlMeasurement("C-2", "flatness", 0.003, 0.010),  # pass
        ])
        summary = aggregate_compliance(a_results, s_results, g_results)
        self.assertEqual(summary["overall_status"], CheckStatus.FAIL)
        self.assertEqual(summary["failed"], 1)
        self.assertEqual(summary["passed"], 2)

    def test_error_input_gives_overall_error(self):
        a_results = run_alignment_checks([
            AlignmentMeasurement("C-3", "rx", 2.0, -1.0, "arcsec"),  # error
        ])
        s_results = run_dimensional_stability_checks([])
        g_results = run_geometry_control_checks([])
        summary = aggregate_compliance(a_results, s_results, g_results)
        self.assertEqual(summary["overall_status"], CheckStatus.ERROR)
        self.assertEqual(summary["errors"], 1)

    def test_empty_inputs_give_pass(self):
        summary = aggregate_compliance([], [], [])
        self.assertEqual(summary["overall_status"], CheckStatus.PASS)
        self.assertEqual(summary["total_checks"], 0)
        self.assertEqual(summary["passed"], 0)

    def test_mixed_failures_counted_correctly(self):
        a_results = run_alignment_checks([
            AlignmentMeasurement("D-1", "rx", 12.0, 10.0, "arcsec"),  # fail
            AlignmentMeasurement("D-2", "tx", 0.05, 0.1, "mm"),       # pass
        ])
        s_results = run_dimensional_stability_checks([
            DimensionalStabilityMeasurement("D-3", 200.0, 200.020, 0.010, "hygroscopic"),  # fail
        ])
        g_results = run_geometry_control_checks([
            GeometryControlMeasurement("D-4", "circularity", 0.002, 0.008),  # pass
        ])
        summary = aggregate_compliance(a_results, s_results, g_results)
        self.assertEqual(summary["overall_status"], CheckStatus.FAIL)
        self.assertEqual(summary["total_checks"], 4)
        self.assertEqual(summary["failed"], 2)
        self.assertEqual(summary["passed"], 2)
        self.assertEqual(len(summary["failures"]), 2)


if __name__ == "__main__":
    unittest.main()
