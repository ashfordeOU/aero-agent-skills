#!/usr/bin/env python3
"""Contract test for the CFD validation logic module.

Stdlib unittest, offline, deterministic. Exercises
scripts/cfd_validation_logic.py: validation case selection by flow regime
and application, relative/RMS/max error metrics, Richardson extrapolation
grid convergence, tolerance-band verdicts, U_val uncertainty combination,
and the report skeleton. The workflow is exercised step by step against
fixed reference values; every invalid input must raise ValueError.
"""

import os
import sys
import unittest

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import cfd_validation_logic as cfd  # noqa: E402


class ValidationCaseSelectionTest(unittest.TestCase):
    def test_naca0012_case(self):
        case = cfd.select_validation_case("incompressible", "airfoil")
        self.assertTrue(case["case_id"] == "naca-0012")
        self.assertTrue(abs(case["reference"]["cd"] - 0.0081) < 1e-12)
        self.assertTrue(abs(case["reference"]["cl"] - 0.0) < 1e-12)
        self.assertTrue(abs(case["conditions"]["mach"] - 0.30) < 1e-12)
        self.assertTrue(abs(case["conditions"]["reynolds"] - 6.0e6) < 1e-9)
        self.assertTrue("naca-4412" in case["alternatives"])

    def test_airfoil_regime_alias(self):
        case = cfd.select_validation_case("subsonic", "airfoil")
        self.assertTrue(case["case_id"] == "naca-0012")
        case2 = cfd.select_validation_case("low speed", "2d airfoil")
        self.assertTrue(case2["case_id"] == "naca-0012")

    def test_transonic_wing(self):
        case = cfd.select_validation_case("transonic", "wing")
        self.assertTrue(case["case_id"] == "onera-m6")

    def test_transport_wing_body(self):
        case = cfd.select_validation_case("transport", "wing-body")
        self.assertTrue(case["case_id"] == "dlr-f6")
        case2 = cfd.select_validation_case("transonic", "wing body")
        self.assertTrue(case2["case_id"] == "dlr-f6")

    def test_flat_plate(self):
        case = cfd.select_validation_case("incompressible", "flat-plate")
        self.assertTrue(case["case_id"] == "flat-plate")
        case2 = cfd.select_validation_case("boundary-layer", "flat plate")
        self.assertTrue(case2["case_id"] == "flat-plate")

    def test_unsupported_combo_raises(self):
        with self.assertRaises(ValueError):
            cfd.select_validation_case("hypersonic", "airfoil")
        with self.assertRaises(ValueError):
            cfd.select_validation_case("transonic", "airfoil")
        with self.assertRaises(ValueError):
            cfd.select_validation_case("", "airfoil")


class ComparisonMetricsTest(unittest.TestCase):
    def test_relative_error_within_five_percent(self):
        rel = cfd.relative_error(0.0085, 0.0081)
        self.assertTrue(rel < 0.05)
        self.assertTrue(abs(rel - 0.049382716) < 1e-6)

    def test_relative_error_outside_five_percent(self):
        rel = cfd.relative_error(0.010, 0.0081)
        self.assertTrue(rel > 0.05)
        self.assertTrue(abs(rel - 0.234567901) < 1e-6)

    def test_relative_error_zero_reference_raises(self):
        with self.assertRaises(ValueError):
            cfd.relative_error(1.0, 0.0)

    def test_rms_error(self):
        rms = cfd.rms_error([1.0, 2.0, 3.0], [1.1, 2.1, 2.9])
        self.assertTrue(abs(rms - 0.1) < 1e-12)

    def test_max_error(self):
        mx = cfd.max_error([1.0, 2.0, 3.0], [1.1, 2.1, 2.9])
        self.assertTrue(abs(mx - 0.1) < 1e-12)

    def test_length_mismatch_raises(self):
        with self.assertRaises(ValueError):
            cfd.rms_error([1.0, 2.0], [1.0, 2.0, 3.0])
        with self.assertRaises(ValueError):
            cfd.max_error([1.0], [1.0, 2.0])

    def test_empty_distribution_raises(self):
        with self.assertRaises(ValueError):
            cfd.rms_error([], [])
        with self.assertRaises(ValueError):
            cfd.max_error([], [])

    def test_non_numeric_raises(self):
        with self.assertRaises(ValueError):
            cfd.relative_error("0.0085", 0.0081)
        with self.assertRaises(ValueError):
            cfd.rms_error([1.0, "x"], [1.0, 2.0])


class RichardsonExtrapolationTest(unittest.TestCase):
    def test_extrapolated_value_sensible(self):
        r = cfd.richardson_extrapolation([0.0085, 0.0090, 0.0100], 2.0)
        self.assertTrue(abs(r["apparent_order"] - 1.0) < 1e-9)
        self.assertTrue(abs(r["extrapolated"] - 0.0080) < 1e-9)
        self.assertTrue(r["gci"] > 0.0)
        self.assertTrue(r["monotone"])

    def test_extrapolation_improves_on_finest_mesh(self):
        r = cfd.richardson_extrapolation([0.0085, 0.0090, 0.0100], 2.0)
        ref = 0.0081
        finest_err = abs(r["finest_value"] - ref)
        extrap_err = abs(r["extrapolated"] - ref)
        self.assertTrue(extrap_err < finest_err)

    def test_invalid_refinement_ratio_raises(self):
        with self.assertRaises(ValueError):
            cfd.richardson_extrapolation([1.0, 2.0, 3.0], 1.0)
        with self.assertRaises(ValueError):
            cfd.richardson_extrapolation([1.0, 2.0, 3.0], 0.5)

    def test_non_monotone_raises(self):
        with self.assertRaises(ValueError):
            cfd.richardson_extrapolation([0.0085, 0.0100, 0.0090], 2.0)
        with self.assertRaises(ValueError):
            cfd.richardson_extrapolation([0.0085, 0.0090, 0.0090], 2.0)

    def test_wrong_length_raises(self):
        with self.assertRaises(ValueError):
            cfd.richardson_extrapolation([1.0, 2.0])
        with self.assertRaises(ValueError):
            cfd.richardson_extrapolation([1.0, 2.0, 3.0, 4.0], 2.0)


class ValidationVerdictTest(unittest.TestCase):
    def test_computed_0085_passes_five_percent_band(self):
        v = cfd.validation_verdict(0.0085, 0.0081, 0.05)
        self.assertTrue(v["passed"])
        self.assertTrue(v["verdict"] == "PASS")
        self.assertTrue(v["margin"] >= 0.0)

    def test_computed_010_fails_five_percent_band(self):
        v = cfd.validation_verdict(0.010, 0.0081, 0.05)
        self.assertFalse(v["passed"])
        self.assertTrue(v["verdict"] == "FAIL")
        self.assertTrue(v["margin"] < 0.0)

    def test_wider_band_passes(self):
        v = cfd.validation_verdict(0.010, 0.0081, 0.25)
        self.assertTrue(v["passed"])

    def test_absolute_mode(self):
        v = cfd.validation_verdict(0.0085, 0.0081, 0.0005, mode="absolute")
        self.assertTrue(v["passed"])
        v2 = cfd.validation_verdict(0.0085, 0.0081, 0.0003, mode="absolute")
        self.assertFalse(v2["passed"])

    def test_invalid_inputs_raise(self):
        with self.assertRaises(ValueError):
            cfd.validation_verdict(1.0, 1.0, 0.0)
        with self.assertRaises(ValueError):
            cfd.validation_verdict(1.0, 1.0, -0.05)
        with self.assertRaises(ValueError):
            cfd.validation_verdict(1.0, 0.0, 0.05)
        with self.assertRaises(ValueError):
            cfd.validation_verdict(1.0, 1.0, 0.05, mode="percent")


class ValidationUncertaintyTest(unittest.TestCase):
    def test_quadrature_combination(self):
        u = cfd.validation_uncertainty(
            {"discretization": 0.0002, "modeling": 0.0003, "numerical": 0.0001}
        )
        self.assertTrue(abs(u["u_val"] - 0.0003741657) < 1e-9)
        self.assertTrue(u["dominant"] == "modeling")

    def test_list_of_pairs_input(self):
        u = cfd.validation_uncertainty([("grid", 0.1), ("turbulence", 0.2)])
        self.assertTrue(abs(u["u_val"] - 0.2236067977) < 1e-9)
        self.assertTrue(u["dominant"] == "turbulence")

    def test_invalid_inputs_raise(self):
        with self.assertRaises(ValueError):
            cfd.validation_uncertainty({})
        with self.assertRaises(ValueError):
            cfd.validation_uncertainty([])
        with self.assertRaises(ValueError):
            cfd.validation_uncertainty({"grid": -0.1})
        with self.assertRaises(ValueError):
            cfd.validation_uncertainty("not-a-mapping")


class ReportSkeletonTest(unittest.TestCase):
    """Verifies the report skeleton follows the validation workflow step by step."""

    def test_report_contains_sections_and_values(self):
        case = cfd.select_validation_case("incompressible", "airfoil")
        verdict = cfd.validation_verdict(0.0085, 0.0081, 0.05)
        report = cfd.report_skeleton(
            case, metrics={"relative_error": 0.0494}, verdict=verdict
        )
        self.assertTrue("# CFD Validation Report" in report)
        self.assertTrue("NACA 0012" in report)
        self.assertTrue("0.0081" in report)
        self.assertTrue("PASS" in report)
        self.assertTrue("## Validation Workflow" in report)

    def test_report_deterministic(self):
        a = cfd.report_skeleton("naca-0012")
        b = cfd.report_skeleton("naca-0012")
        self.assertTrue(a == b)

    def test_report_unknown_case_raises(self):
        with self.assertRaises(ValueError):
            cfd.report_skeleton("not-a-case")
        with self.assertRaises(ValueError):
            cfd.report_skeleton(42)


if __name__ == "__main__":
    unittest.main(verbosity=2)
