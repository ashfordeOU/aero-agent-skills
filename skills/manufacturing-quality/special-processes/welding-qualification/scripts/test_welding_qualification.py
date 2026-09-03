"""Offline deterministic contract test for welding_qualification_logic.

Run with: python3 test_welding_qualification.py
Covers the worked example anchors from the wave-28 welding-qualification
spec: gtaw heat input 1.2139 kJ/mm, gma-pulse 1.0318 kJ/mm at the 0.85
efficiency default, thickness coverage boundaries 4.7625 and 12.7 mm,
preheat margin +7 degC, the coupon matrix, coverage verdicts, summary
all_ok and findings, and ValueError rejection of non-physical inputs.
"""

import os
import sys
import unittest

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from welding_qualification_logic import (
    DEFAULT_PROCESS_EFFICIENCY,
    HEAT_INPUT_UNITS,
    JOINT_TYPES,
    PROCESSES,
    THICKNESS_RANGE_DEFAULT,
    TYPICAL_COUPON_MATRIX,
    coverage_verdict,
    heat_input_kj_mm,
    interpass_ok,
    preheat_margin_degC,
    qualification_summary,
    thickness_coverage,
)


def base_inputs():
    """Passing-case input dict from the worked example."""
    return {
        "process": "gtaw",
        "joint_type": "butt",
        "voltage_V": 11.5,
        "current_A": 190,
        "travel_speed_mm_s": 1.8,
        "qualified_thickness_mm": 6.35,
        "production_thickness_mm": 8.0,
        "required_min_preheat_degC": 15,
        "measured_preheat_degC": 22,
        "max_interpass_degC": 150,
        "measured_interpass_degC": 96,
        "qualified_heat_input_range_kj_mm": (0.8, 2.0),
        "qualified_current_range_A": (160, 220),
        "qualified_voltage_range_V": (10.5, 13.0),
    }


class TestHeatInput(unittest.TestCase):
    def test_heat_input_units_constant(self):
        self.assertEqual(HEAT_INPUT_UNITS, "kJ/mm")

    def test_gtaw_heat_input_anchor(self):
        # 11.5 * 190 * 1.0 / (1.8 * 1000) = 2185 / 1800 = 1.2139 kJ/mm
        self.assertAlmostEqual(
            heat_input_kj_mm(11.5, 190, 1.8, 1.0), 1.2139, delta=1e-4)

    def test_gma_pulse_heat_input_anchor(self):
        # 11.5 * 190 * 0.85 / 1800 = 1.0318 kJ/mm at the 0.85 default
        self.assertAlmostEqual(
            heat_input_kj_mm(11.5, 190, 1.8, 0.85), 1.0318, delta=1e-4)

    def test_gmaw_heat_input_at_default_efficiency(self):
        # 11.5 * 190 * 0.8 / 1800 = 0.9711 kJ/mm at the 0.8 default
        self.assertAlmostEqual(
            heat_input_kj_mm(11.5, 190, 1.8, 0.8), 0.9711, delta=1e-4)

    def test_efficiency_defaults_per_process(self):
        self.assertEqual(DEFAULT_PROCESS_EFFICIENCY,
                         {"gtaw": 1.0, "gmaw": 0.8, "gma-pulse": 0.85})

    def test_heat_input_valueerror_nonphysical(self):
        for kwargs in ({"voltage_V": 0, "current_A": 190, "travel_speed_mm_s": 1.8},
                       {"voltage_V": -5, "current_A": 190, "travel_speed_mm_s": 1.8},
                       {"voltage_V": 11.5, "current_A": -1, "travel_speed_mm_s": 1.8},
                       {"voltage_V": 11.5, "current_A": 190, "travel_speed_mm_s": 0}):
            with self.assertRaises(ValueError):
                heat_input_kj_mm(kwargs["voltage_V"], kwargs["current_A"],
                                 kwargs["travel_speed_mm_s"], 1.0)
        with self.assertRaises(ValueError):
            heat_input_kj_mm(11.5, 190, 1.8, 0.0)
        with self.assertRaises(ValueError):
            heat_input_kj_mm(11.5, 190, 1.8, 1.5)


class TestCoverageVerdict(unittest.TestCase):
    def test_coverage_verdict_no_stated_range(self):
        self.assertEqual(coverage_verdict(1.2139, None), "in-range")

    def test_coverage_verdict_inclusive_bounds_in_range(self):
        self.assertEqual(coverage_verdict(0.8, (0.8, 2.0)), "in-range")
        self.assertEqual(coverage_verdict(2.0, (0.8, 2.0)), "in-range")
        self.assertEqual(coverage_verdict(1.2139, (0.8, 2.0)), "in-range")

    def test_coverage_verdict_out_of_range(self):
        self.assertEqual(coverage_verdict(0.79, (0.8, 2.0)), "out-of-range")
        self.assertEqual(coverage_verdict(2.01, (0.8, 2.0)), "out-of-range")

    def test_coverage_verdict_valueerror_reversed_range(self):
        with self.assertRaises(ValueError):
            coverage_verdict(1.0, (2.0, 0.8))


class TestThicknessCoverage(unittest.TestCase):
    def test_thickness_coverage_anchor_bounds(self):
        tc = thickness_coverage(6.35, 8.0)
        self.assertAlmostEqual(tc["lo_mm"], 4.7625, places=4)
        self.assertEqual(tc["hi_mm"], 12.7)
        self.assertEqual(THICKNESS_RANGE_DEFAULT, (0.75, 2.0))

    def test_thickness_coverage_8mm_covered(self):
        tc = thickness_coverage(6.35, 8.0)
        self.assertTrue(tc["covered"])
        self.assertEqual(tc["verdict"], "in-range")

    def test_thickness_coverage_boundaries_inclusive_and_outside(self):
        self.assertTrue(thickness_coverage(6.35, 4.7625)["covered"])
        self.assertTrue(thickness_coverage(6.35, 12.7)["covered"])
        self.assertFalse(thickness_coverage(6.35, 4.7624)["covered"])
        self.assertFalse(thickness_coverage(6.35, 12.7001)["covered"])

    def test_thickness_coverage_4mm_not_covered(self):
        tc = thickness_coverage(6.35, 4.0)
        self.assertFalse(tc["covered"])
        self.assertEqual(tc["verdict"], "out-of-range")

    def test_thickness_coverage_custom_fractions(self):
        tc = thickness_coverage(10.0, 12.0, range_fractions=(0.5, 1.5))
        self.assertEqual((tc["lo_mm"], tc["hi_mm"]), (5.0, 15.0))
        self.assertTrue(tc["covered"])
        self.assertFalse(thickness_coverage(
            10.0, 16.0, range_fractions=(0.5, 1.5))["covered"])

    def test_thickness_coverage_valueerror_nonpositive_and_bad_fractions(self):
        for qt, pt in ((0.0, 8.0), (6.35, 0.0), (-1.0, 8.0), (6.35, -2.0)):
            with self.assertRaises(ValueError):
                thickness_coverage(qt, pt)
        with self.assertRaises(ValueError):
            thickness_coverage(6.35, 8.0, range_fractions=(2.0, 0.75))
        with self.assertRaises(ValueError):
            thickness_coverage(6.35, 8.0, range_fractions=(0.0, 1.0))


class TestPreheatAndInterpass(unittest.TestCase):
    def test_preheat_margin_anchor_plus7(self):
        self.assertEqual(preheat_margin_degC(22, 15), 7)

    def test_preheat_margin_negative_when_below_minimum(self):
        self.assertEqual(preheat_margin_degC(10, 15), -5)

    def test_preheat_margin_valueerror_below_absolute_zero(self):
        with self.assertRaises(ValueError):
            preheat_margin_degC(20, -300.0)

    def test_interpass_ok_true_within_and_at_cap(self):
        self.assertTrue(interpass_ok(96, 150))
        self.assertTrue(interpass_ok(150, 150))

    def test_interpass_ok_false_above_cap(self):
        self.assertFalse(interpass_ok(160, 150))

    def test_interpass_ok_valueerror_nonpositive_max(self):
        for bad in (0, -150):
            with self.assertRaises(ValueError):
                interpass_ok(96, bad)


class TestCouponMatrix(unittest.TestCase):
    def test_coupon_matrix_gtaw_butt_exact_list(self):
        self.assertEqual(
            TYPICAL_COUPON_MATRIX["gtaw"]["butt"],
            ["tensile-x2", "guided-bend-x4", "radiography-100pct"])

    def test_coupon_matrix_fillet_per_process(self):
        for process in PROCESSES:
            self.assertEqual(
                TYPICAL_COUPON_MATRIX[process]["fillet"],
                ["macro-etch-x2", "fillet-break-x2"])

    def test_coupon_matrix_pipe_per_process(self):
        for process in PROCESSES:
            self.assertEqual(
                TYPICAL_COUPON_MATRIX[process]["pipe"],
                ["tensile-x2", "guided-bend-x4", "macro-etch"])

    def test_coupon_matrix_butt_all_processes(self):
        for process in PROCESSES:
            for joint in JOINT_TYPES:
                self.assertIn(joint, TYPICAL_COUPON_MATRIX[process])
            self.assertEqual(
                TYPICAL_COUPON_MATRIX[process]["butt"][0], "tensile-x2")
            self.assertEqual(
                TYPICAL_COUPON_MATRIX[process]["butt"][1], "guided-bend-x4")


class TestQualificationSummary(unittest.TestCase):
    def test_summary_passing_case_anchors(self):
        s = qualification_summary(base_inputs())
        self.assertAlmostEqual(s["heat_input_kj_mm"], 1.2139, delta=1e-4)
        self.assertEqual(s["heat_input_coverage"], "in-range")
        self.assertEqual(s["current_coverage"], "in-range")
        self.assertEqual(s["voltage_coverage"], "in-range")
        self.assertEqual(s["preheat_margin_degC"], 7)
        self.assertTrue(s["interpass_ok"])
        self.assertTrue(s["thickness_coverage"]["covered"])
        self.assertEqual(
            s["coupon_matrix"],
            ["tensile-x2", "guided-bend-x4", "radiography-100pct"])
        self.assertTrue(s["all_ok"])
        self.assertEqual(s["findings"], [])

    def test_summary_failing_case_findings(self):
        inputs = base_inputs()
        inputs["production_thickness_mm"] = 4.0
        inputs["measured_interpass_degC"] = 160
        s = qualification_summary(inputs)
        self.assertFalse(s["all_ok"])
        self.assertIn("thickness-coverage", s["findings"])
        self.assertIn("interpass", s["findings"])
        self.assertEqual(
            s["findings"], ["thickness-coverage", "interpass"])

    def test_summary_gma_pulse_efficiency_default_applied(self):
        inputs = base_inputs()
        inputs["process"] = "gma-pulse"
        s = qualification_summary(inputs)
        self.assertAlmostEqual(s["heat_input_kj_mm"], 1.0318, delta=1e-4)

    def test_summary_voltage_out_of_range_finding(self):
        inputs = base_inputs()
        inputs["voltage_V"] = 9.5
        s = qualification_summary(inputs)
        self.assertIn("voltage-range", s["findings"])
        self.assertFalse(s["all_ok"])
        self.assertEqual(s["voltage_coverage"], "out-of-range")

    def test_summary_all_ranges_none_ok(self):
        inputs = base_inputs()
        inputs["qualified_heat_input_range_kj_mm"] = None
        inputs["qualified_current_range_A"] = None
        inputs["qualified_voltage_range_V"] = None
        s = qualification_summary(inputs)
        self.assertEqual(s["heat_input_coverage"], "in-range")
        self.assertEqual(s["current_coverage"], "in-range")
        self.assertEqual(s["voltage_coverage"], "in-range")
        self.assertTrue(s["all_ok"])
        self.assertEqual(s["findings"], [])

    def test_summary_valueerror_process_and_joint(self):
        inputs = base_inputs()
        inputs["process"] = "smaw"
        with self.assertRaises(ValueError):
            qualification_summary(inputs)
        inputs = base_inputs()
        inputs["joint_type"] = "lap"
        with self.assertRaises(ValueError):
            qualification_summary(inputs)

    def test_summary_valueerror_nonphysical_inputs(self):
        bad_cases = (
            {"voltage_V": 0},
            {"current_A": -1},
            {"travel_speed_mm_s": 0},
            {"production_thickness_mm": 0},
            {"qualified_thickness_mm": -5},
            {"max_interpass_degC": 0},
            {"required_min_preheat_degC": -300.0},
            {"process_efficiency": 1.4},
        )
        for change in bad_cases:
            inputs = base_inputs()
            inputs.update(change)
            with self.assertRaises(ValueError):
                qualification_summary(inputs)


if __name__ == "__main__":
    unittest.main(verbosity=2)
