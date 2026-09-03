"""Contract test for the shearography-inspection NDT leaf (wave-26).

Deterministic stdlib unittest, offline, runs in well under 20 s:
    python3 test_shearography_inspection.py

Asserts the SKILL worked-example anchors from real module outputs:
strain_from_phase(0.5 rad, 5 mm, 532 nm) with a phase_for_strain round
trip within 1e-12, min detectable strain exactly MIN_SNR (3x) the
single-frame noise strain, shear_for_defect 10 mm to 5 mm and 6 mm to
3 mm, select_load vacuum 6 mm to 40 mbar with 4 mm interpolated to
30 mbar, scan_plan(1.0, 0.25, 0.2) to 5 passes and 80 passes at 0.95
overlap, the accept / review / reject disposition branches, boundary
cases, round-trip identities, and ValueError rejection of non-physical
inputs.
"""

import math
import os
import sys
import unittest

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import shearography_inspection_logic as sg


class TestPhaseStrainConversions(unittest.TestCase):
    """Phase-strain conversions, scaling and round trips."""

    def test_strain_from_phase_worked_value(self):
        # 0.5 rad, 5 mm shear, 532 nm: about 4.23e-6 relative strain.
        strain = sg.strain_from_phase(0.5, 5.0, 532.0)
        self.assertAlmostEqual(strain, 4.2335e-6, places=9)

    def test_phase_for_strain_round_trip_within_1e12(self):
        strain = sg.strain_from_phase(0.5, 5.0, 532.0)
        back = sg.phase_for_strain(strain, 5.0, 532.0)
        self.assertAlmostEqual(back, 0.5, delta=1e-12)
        # Second operating point: 0.25 rad at 3 mm shear, 632.8 nm.
        strain2 = sg.strain_from_phase(0.25, 3.0, 632.8)
        back2 = sg.phase_for_strain(strain2, 3.0, 632.8)
        self.assertAlmostEqual(back2, 0.25, delta=1e-12)

    def test_strain_scaling_properties(self):
        low = sg.strain_from_phase(0.25, 5.0, 532.0)
        high = sg.strain_from_phase(0.5, 5.0, 532.0)
        self.assertAlmostEqual(high, 2.0 * low, places=12)
        near_shear = sg.strain_from_phase(0.5, 5.0, 532.0)
        far_shear = sg.strain_from_phase(0.5, 10.0, 532.0)
        self.assertAlmostEqual(near_shear, 2.0 * far_shear, places=12)
        green = sg.strain_from_phase(0.5, 5.0, 532.0)
        red = sg.strain_from_phase(0.5, 5.0, 632.8)
        self.assertAlmostEqual(red / green, 632.8 / 532.0, places=12)

    def test_negative_phase_negative_strain(self):
        strain = sg.strain_from_phase(-0.5, 5.0, 532.0)
        self.assertLess(strain, 0.0)
        back = sg.phase_for_strain(strain, 5.0, 532.0)
        self.assertAlmostEqual(back, -0.5, delta=1e-12)

    def test_nonpositive_shear_valueerror(self):
        for shear in (0.0, -5.0):
            with self.assertRaises(ValueError):
                sg.strain_from_phase(0.5, shear, 532.0)
            with self.assertRaises(ValueError):
                sg.phase_for_strain(1e-6, shear, 532.0)

    def test_nonfinite_valueerror(self):
        with self.assertRaises(ValueError):
            sg.strain_from_phase(float("nan"), 5.0, 532.0)
        with self.assertRaises(ValueError):
            sg.strain_from_phase(0.5, float("inf"), 532.0)


class TestMinDetectableStrain(unittest.TestCase):
    """Minimum detectable strain contract."""

    def test_ratio_exactly_min_snr(self):
        single = sg.strain_from_phase(0.1, 5.0, 532.0)
        minimum = sg.min_detectable_strain(0.1, 5.0, 532.0)
        # MIN_SNR makes it 3x the single-frame noise strain, so the
        # minimum always sits above the noise-equivalent strain.
        self.assertAlmostEqual(minimum / single, sg.MIN_SNR, places=12)
        self.assertAlmostEqual(minimum / single, 3.0, places=12)
        self.assertGreater(minimum, single)

    def test_min_detectable_scales_with_noise_floor(self):
        low = sg.min_detectable_strain(0.1, 5.0, 532.0)
        high = sg.min_detectable_strain(0.2, 5.0, 532.0)
        self.assertAlmostEqual(high, 2.0 * low, places=12)

    def test_min_detectable_valueerror(self):
        with self.assertRaises(ValueError):
            sg.min_detectable_strain(-0.1, 5.0, 532.0)
        with self.assertRaises(ValueError):
            sg.min_detectable_strain(0.1, 0.0, 532.0)


class TestShearSelection(unittest.TestCase):
    """Shear distance selection for a minimum defect size."""

    def test_shear_for_defect_worked_values(self):
        self.assertEqual(sg.shear_for_defect(10.0), 5.0)
        self.assertEqual(sg.shear_for_defect(6.0), 3.0)

    def test_shear_for_defect_divisor_rule(self):
        # shear = defect / SHEAR_DIVISOR across sizes.
        self.assertEqual(sg.shear_for_defect(4.0), 2.0)
        self.assertEqual(sg.shear_for_defect(2.0), 1.0)

    def test_shear_for_defect_nonpositive_valueerror(self):
        for size in (0.0, -10.0):
            with self.assertRaises(ValueError):
                sg.shear_for_defect(size)


class TestLoadSelection(unittest.TestCase):
    """Typical load step table with vacuum interpolation."""

    def test_select_load_vacuum_interpolation(self):
        # Worked anchors: 6 mm -> 40 mbar, 4 mm -> 30 mbar (interpolated
        # between the 2.0 mm and 6.0 mm breakpoints), 9 mm -> 50 mbar.
        self.assertEqual(sg.select_load(6.0, "vacuum"), 40.0)
        self.assertAlmostEqual(sg.select_load(4.0, "vacuum"), 30.0,
                               places=12)
        self.assertAlmostEqual(sg.select_load(9.0, "vacuum"), 50.0,
                               places=12)

    def test_select_load_vacuum_breakpoints(self):
        self.assertEqual(sg.select_load(2.0, "vacuum"), 20.0)
        self.assertEqual(sg.select_load(12.0, "vacuum"), 60.0)

    def test_select_load_thermal_and_vibration_constants(self):
        self.assertEqual(sg.select_load(3.0, "thermal"), 5.0)
        self.assertEqual(sg.select_load(10.0, "thermal"), 5.0)
        self.assertEqual(sg.select_load(3.0, "vibration"), 30.0)

    def test_select_load_unknown_type_valueerror(self):
        with self.assertRaises(ValueError):
            sg.select_load(6.0, "laser")

    def test_select_load_nonpositive_thickness_valueerror(self):
        for thickness in (0.0, -3.0):
            with self.assertRaises(ValueError):
                sg.select_load(thickness, "vacuum")


class TestScanPlan(unittest.TestCase):
    """Scan plan pass and overlap math."""

    def test_scan_plan_worked_passes(self):
        plan = sg.scan_plan(1.0, 0.25, 0.2)
        self.assertEqual(plan["passes"], 5)
        self.assertAlmostEqual(plan["overlap_area"], 0.25, places=12)
        # 95% overlap drives the pass count to 80.
        plan95 = sg.scan_plan(1.0, 0.25, 0.95)
        self.assertEqual(plan95["passes"], 80)
        # 0.3 m2 FOV at 20% overlap: 1.0 / 0.24 = 4.17 -> 5 passes.
        self.assertEqual(sg.scan_plan(1.0, 0.3, 0.2)["passes"], 5)

    def test_scan_plan_no_overlap(self):
        plan = sg.scan_plan(1.0, 0.25, 0.0)
        self.assertEqual(plan["passes"], 4)
        self.assertEqual(plan["overlap_area"], 0.0)

    def test_scan_plan_single_pass_large_fov(self):
        self.assertEqual(sg.scan_plan(0.5, 1.0, 0.1)["passes"], 1)

    def test_scan_plan_bad_areas_valueerror(self):
        with self.assertRaises(ValueError):
            sg.scan_plan(0.0, 0.25, 0.2)
        with self.assertRaises(ValueError):
            sg.scan_plan(1.0, 0.0, 0.2)
        with self.assertRaises(ValueError):
            sg.scan_plan(-1.0, 0.25, 0.2)

    def test_scan_plan_overlap_out_of_range_valueerror(self):
        for overlap in (-0.1, 0.96, 1.0):
            with self.assertRaises(ValueError):
                sg.scan_plan(1.0, 0.25, overlap)


class TestAnomalyDisposition(unittest.TestCase):
    """Accept / review / reject disposition branches."""

    def test_disposition_reject_oversize(self):
        result = sg.anomaly_disposition(12.0, 10.0, 5.0)
        self.assertEqual(result["verdict"], "reject")
        self.assertTrue(result["reasons"])

    def test_disposition_accept_and_boundaries(self):
        self.assertEqual(sg.anomaly_disposition(9.0, 10.0, 5.0)["verdict"],
                         "accept")
        # Exactly at the limit with adequate SNR: accept.
        self.assertEqual(sg.anomaly_disposition(10.0, 10.0, 5.0)["verdict"],
                         "accept")
        # Beyond the 20% band: reject.
        self.assertEqual(sg.anomaly_disposition(12.5, 10.0, 5.0)["verdict"],
                         "reject")
        # SNR exactly at MIN_SNR still accepts.
        self.assertEqual(sg.anomaly_disposition(9.0, 10.0, 3.0)["verdict"],
                         "accept")

    def test_disposition_review_branches(self):
        # 11 mm is above the 10 mm allowable but within the 20% review
        # band: review. 8 mm within the allowable at SNR 2 (below MIN_SNR
        # 3): review on low signal quality.
        result_band = sg.anomaly_disposition(11.0, 10.0, 5.0)
        self.assertEqual(result_band["verdict"], "review")
        self.assertTrue(result_band["reasons"])
        result_snr = sg.anomaly_disposition(8.0, 10.0, 2.0)
        self.assertEqual(result_snr["verdict"], "review")
        self.assertTrue(result_snr["reasons"])

    def test_disposition_bad_inputs_valueerror(self):
        with self.assertRaises(ValueError):
            sg.anomaly_disposition(-1.0, 10.0, 5.0)
        with self.assertRaises(ValueError):
            sg.anomaly_disposition(9.0, 0.0, 5.0)
        with self.assertRaises(ValueError):
            sg.anomaly_disposition(9.0, 10.0, -1.0)
        with self.assertRaises(ValueError):
            sg.anomaly_disposition(float("nan"), 10.0, 5.0)


class TestSummarizeAndConstants(unittest.TestCase):
    """Planning summary and module constants."""

    def test_summarize_worked_example(self):
        summary = sg.summarize(
            part_thickness_mm=6.0, part_area_m2=1.0, fov_area_m2=0.25,
            overlap=0.2, min_defect_mm=10.0, load_type="vacuum",
            phase_rad=0.5, anomaly_size_mm=12.0, allow_size_mm=10.0,
            snr=5.0)
        self.assertAlmostEqual(summary["shear_mm"], 5.0, places=12)
        self.assertEqual(summary["load_value"], 40.0)
        self.assertEqual(summary["load_type"], "vacuum")
        self.assertEqual(summary["passes"], 5)
        self.assertTrue(summary["coverage_ok"])
        self.assertGreater(summary["min_detectable_strain"], 0.0)
        self.assertEqual(summary["verdict"], "reject")

    def test_summarize_accept_case(self):
        summary = sg.summarize(
            part_thickness_mm=6.0, part_area_m2=1.0, fov_area_m2=0.25,
            overlap=0.2, min_defect_mm=10.0, load_type="vacuum",
            phase_rad=0.5, anomaly_size_mm=9.0, allow_size_mm=10.0,
            snr=5.0)
        self.assertEqual(summary["verdict"], "accept")

    def test_module_constants(self):
        self.assertEqual(sg.LASER_WAVELENGTH_NM, 532.0)
        self.assertEqual(sg.NOISE_FLOOR_PHASE_RAD, 0.1)
        self.assertEqual(sg.MIN_SNR, 3.0)
        self.assertEqual(sg.COVERAGE_MIN, 0.85)
        self.assertEqual(sg.SHEAR_DIVISOR, 2.0)
        self.assertEqual(sg.REVIEW_BAND, 0.2)
        self.assertEqual(sg.TYPICAL_LOAD_STEPS["thermal"], 5.0)
        self.assertEqual(sg.TYPICAL_LOAD_STEPS["vibration"], 30.0)


if __name__ == "__main__":
    unittest.main(verbosity=2)
