"""Contract test for the computed-tomography NDT leaf (wave-25).

Deterministic stdlib unittest, offline, runs in well under 20 s:
    python3 test_computed_tomography.py

Covers the SKILL worked example (aluminum casting 50 mm diameter, 200
micron detector pixel pitch, SOD 300 mm, ODD 300 mm: M = 2, voxel
1.000e-4 m, smallest detectable 3.000e-4 m passes the 5.000e-4 m
required flaw, 1609 projections for a 1024 column span, 350 kV for 50
mm aluminum, 160.9 s at 0.1 s per projection, 0.8% porosity, void
diameter 4.963e-3 m), every model function, boundary cases, round-trip
identities, and ValueError rejection of non-physical inputs.
"""

import math
import os
import sys
import unittest

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import computed_tomography_logic as ct

# Worked example module constants (aluminum casting CT inspection).
PIXEL_PITCH = 200e-6      # 200 micron detector pixel pitch
SOD = 0.300               # 300 mm source to object
ODD = 0.300               # 300 mm object to detector
REQUIRED_FLAW = 0.5e-3    # 0.5 mm required flaw
COLUMNS = 1024
MATERIAL = "aluminum"
THICKNESS_MM = 50.0
EXPOSURE_S = 0.1
VOID_VOXELS = 64000
TOTAL_VOXELS = 8000000

MU_WATER = 20.0           # 1/m, representative CT-energy water attenuation


class TestMagnification(unittest.TestCase):
    def test_worked_example_magnification_is_two(self):
        self.assertAlmostEqual(ct.magnification(SOD, ODD), 2.0, places=12)

    def test_magnification_formula_equivalent(self):
        self.assertAlmostEqual(
            ct.magnification(SOD, ODD), (SOD + ODD) / SOD, places=12)

    def test_magnification_touching_detector_is_one(self):
        self.assertAlmostEqual(ct.magnification(0.300, 0.0), 1.0, places=12)

    def test_magnification_grows_with_odd(self):
        self.assertGreater(ct.magnification(0.3, 0.6),
                           ct.magnification(0.3, 0.3))

    def test_magnification_negative_sod_raises(self):
        with self.assertRaises(ValueError):
            ct.magnification(-0.1, 0.3)

    def test_magnification_zero_sod_raises(self):
        with self.assertRaises(ValueError):
            ct.magnification(0.0, 0.3)

    def test_magnification_negative_odd_raises(self):
        with self.assertRaises(ValueError):
            ct.magnification(0.3, -0.1)


class TestVoxelSize(unittest.TestCase):
    def test_worked_example_voxel_size(self):
        self.assertAlmostEqual(
            ct.voxel_size(PIXEL_PITCH, SOD, ODD), 1.000e-4, places=8)

    def test_voxel_size_is_pitch_over_magnification(self):
        self.assertAlmostEqual(
            ct.voxel_size(PIXEL_PITCH, SOD, ODD),
            PIXEL_PITCH / ct.magnification(SOD, ODD), places=12)

    def test_voxel_size_equals_pitch_when_touching(self):
        self.assertAlmostEqual(
            ct.voxel_size(200e-6, 0.300, 0.0), 200e-6, places=12)

    def test_voxel_size_nonpositive_pitch_raises(self):
        with self.assertRaises(ValueError):
            ct.voxel_size(0.0, SOD, ODD)
        with self.assertRaises(ValueError):
            ct.voxel_size(-5e-6, SOD, ODD)


class TestResolutionCheck(unittest.TestCase):
    def test_worked_example_flaw_passes(self):
        verdict = ct.resolution_check(1.000e-4, REQUIRED_FLAW)
        self.assertTrue(verdict.startswith("PASS"))

    def test_worked_example_smallest_detectable(self):
        self.assertAlmostEqual(1.000e-4 * ct.DETECT_FACTOR, 3.000e-4,
                               places=8)

    def test_flaw_below_three_voxels_fails(self):
        verdict = ct.resolution_check(1.000e-4, 2.0e-4)
        self.assertTrue(verdict.startswith("FAIL"))

    def test_flaw_exactly_three_voxels_passes(self):
        verdict = ct.resolution_check(1.000e-4, 3.000e-4)
        self.assertTrue(verdict.startswith("PASS"))

    def test_coarse_voxel_fails_fine_requirement(self):
        verdict = ct.resolution_check(5.000e-4, 0.5e-3)
        self.assertTrue(verdict.startswith("FAIL"))

    def test_resolution_nonpositive_voxel_raises(self):
        with self.assertRaises(ValueError):
            ct.resolution_check(0.0, 0.5e-3)

    def test_resolution_nonpositive_flaw_raises(self):
        with self.assertRaises(ValueError):
            ct.resolution_check(1.0e-4, 0.0)
        with self.assertRaises(ValueError):
            ct.resolution_check(1.0e-4, -0.1e-3)


class TestProjectionCount(unittest.TestCase):
    def test_worked_example_projection_count(self):
        self.assertEqual(ct.projection_count(COLUMNS), 1609)

    def test_projection_count_rule_of_thumb(self):
        self.assertEqual(ct.projection_count(1024),
                         int(math.ceil((math.pi / 2.0) * 1024)))

    def test_projection_count_rounds_up(self):
        self.assertEqual(ct.projection_count(2), 4)  # ceil(pi) = 4

    def test_projection_count_is_integer(self):
        self.assertIsInstance(ct.projection_count(100), int)

    def test_projection_count_nonpositive_raises(self):
        with self.assertRaises(ValueError):
            ct.projection_count(0)
        with self.assertRaises(ValueError):
            ct.projection_count(-50)


class TestTubeEnergy(unittest.TestCase):
    def test_worked_example_aluminum_kv(self):
        self.assertAlmostEqual(ct.tube_energy_kv("aluminum", 50.0), 350.0,
                               places=9)

    def test_tube_energy_scales_with_thickness(self):
        self.assertAlmostEqual(ct.tube_energy_kv("aluminum", 25.0), 175.0,
                               places=9)

    def test_steel_roughly_double_aluminum(self):
        self.assertAlmostEqual(
            ct.tube_energy_kv("steel", 10.0),
            2.0 * ct.tube_energy_kv("aluminum", 10.0), places=9)

    def test_material_case_insensitive(self):
        self.assertAlmostEqual(ct.tube_energy_kv("Aluminum", 10.0),
                               ct.tube_energy_kv("aluminum", 10.0),
                               places=9)

    def test_unknown_material_raises(self):
        with self.assertRaises(ValueError):
            ct.tube_energy_kv("lead", 10.0)

    def test_tube_energy_nonpositive_thickness_raises(self):
        with self.assertRaises(ValueError):
            ct.tube_energy_kv("aluminum", 0.0)
        with self.assertRaises(ValueError):
            ct.tube_energy_kv("aluminum", -5.0)


class TestScanTime(unittest.TestCase):
    def test_worked_example_scan_time(self):
        self.assertAlmostEqual(ct.scan_time(1609, 0.1), 160.9, places=9)

    def test_scan_time_scales_linearly(self):
        self.assertAlmostEqual(ct.scan_time(100, 0.5), 50.0, places=9)

    def test_scan_time_nonpositive_projection_count_raises(self):
        with self.assertRaises(ValueError):
            ct.scan_time(0, 0.1)

    def test_scan_time_nonpositive_exposure_raises(self):
        with self.assertRaises(ValueError):
            ct.scan_time(100, 0.0)
        with self.assertRaises(ValueError):
            ct.scan_time(100, -0.1)


class TestCtNumber(unittest.TestCase):
    def test_water_is_zero_hu(self):
        self.assertAlmostEqual(ct.ct_number(MU_WATER, MU_WATER), 0.0,
                               places=9)

    def test_air_is_minus_1000_hu(self):
        self.assertAlmostEqual(ct.ct_number(0.0, MU_WATER), -1000.0,
                               places=9)

    def test_linear_conversion(self):
        self.assertAlmostEqual(ct.ct_number(1.1 * MU_WATER, MU_WATER),
                               100.0, places=9)

    def test_negative_mu_raises(self):
        with self.assertRaises(ValueError):
            ct.ct_number(-1.0, MU_WATER)

    def test_nonpositive_mu_water_raises(self):
        with self.assertRaises(ValueError):
            ct.ct_number(10.0, 0.0)
        with self.assertRaises(ValueError):
            ct.ct_number(10.0, -1.0)

    def test_ct_number_round_trip(self):
        mu = 25.0
        hu = ct.ct_number(mu, MU_WATER)
        self.assertAlmostEqual(
            MU_WATER * (1.0 + hu / 1000.0), mu, places=9)


class TestMaterialClass(unittest.TestCase):
    def test_air_class(self):
        self.assertEqual(ct.material_class_from_ct_number(-1000.0),
                         "air-or-gas")
        self.assertEqual(ct.material_class_from_ct_number(-960.0),
                         "air-or-gas")

    def test_low_density_void_class(self):
        self.assertEqual(ct.material_class_from_ct_number(-500.0),
                         "low-density-void")

    def test_polymer_composite_class(self):
        self.assertEqual(ct.material_class_from_ct_number(50.0),
                         "polymer-composite")

    def test_light_alloy_class(self):
        self.assertEqual(ct.material_class_from_ct_number(500.0),
                         "light-alloy")

    def test_high_density_metal_class(self):
        self.assertEqual(ct.material_class_from_ct_number(1500.0),
                         "high-density-metal")


class TestPorosity(unittest.TestCase):
    def test_worked_example_porosity_percent(self):
        self.assertAlmostEqual(
            ct.porosity_fraction(VOID_VOXELS, TOTAL_VOXELS), 0.8, places=9)

    def test_clean_part_zero_percent(self):
        self.assertEqual(ct.porosity_fraction(0, TOTAL_VOXELS), 0.0)

    def test_fully_void_one_hundred_percent(self):
        self.assertAlmostEqual(ct.porosity_fraction(500, 500), 100.0,
                               places=9)

    def test_voids_exceed_total_raises(self):
        with self.assertRaises(ValueError):
            ct.porosity_fraction(501, 500)

    def test_negative_void_count_raises(self):
        with self.assertRaises(ValueError):
            ct.porosity_fraction(-1, 500)

    def test_nonpositive_total_raises(self):
        with self.assertRaises(ValueError):
            ct.porosity_fraction(0, 0)


class TestVoidDiameter(unittest.TestCase):
    def test_worked_example_void_diameter(self):
        self.assertAlmostEqual(ct.void_diameter(VOID_VOXELS, 1.000e-4),
                               4.963e-3, delta=1e-6)

    def test_void_diameter_conserves_volume(self):
        vox = 1.0e-4
        d = ct.void_diameter(VOID_VOXELS, vox)
        volume = math.pi / 6.0 * d ** 3
        self.assertAlmostEqual(volume, VOID_VOXELS * vox ** 3, places=8)

    def test_zero_voids_zero_diameter(self):
        self.assertEqual(ct.void_diameter(0, 1.0e-4), 0.0)

    def test_void_diameter_scales_with_voxel_size(self):
        d1 = ct.void_diameter(1000, 1.0e-4)
        d2 = ct.void_diameter(1000, 2.0e-4)
        self.assertAlmostEqual(d2 / d1, 2.0, places=9)

    def test_void_diameter_negative_voids_raises(self):
        with self.assertRaises(ValueError):
            ct.void_diameter(-5, 1.0e-4)

    def test_void_diameter_nonpositive_voxel_raises(self):
        with self.assertRaises(ValueError):
            ct.void_diameter(10, 0.0)


class TestInspectionVerdict(unittest.TestCase):
    def test_verdict_worked_example_keys_and_values(self):
        out = ct.ct_inspection_verdict(
            pixel_pitch=PIXEL_PITCH, sod=SOD, odd=ODD,
            required_flaw_m=REQUIRED_FLAW, columns_span=COLUMNS,
            material=MATERIAL, thickness_mm=THICKNESS_MM,
            num_projections=1609, exposure_s_per_proj=EXPOSURE_S,
            void_voxels=VOID_VOXELS, total_voxels=TOTAL_VOXELS,
            mu=1.4 * MU_WATER, mu_water=MU_WATER)
        self.assertAlmostEqual(out["magnification"], 2.0, places=9)
        self.assertAlmostEqual(out["voxel_size_m"], 1.000e-4, places=8)
        self.assertTrue(out["resolution"].startswith("PASS"))
        self.assertEqual(out["projection_count"], 1609)
        self.assertAlmostEqual(out["tube_energy_kv"], 350.0, places=9)
        self.assertAlmostEqual(out["scan_time_s"], 160.9, places=9)
        self.assertAlmostEqual(out["porosity_percent"], 0.8, places=9)
        self.assertAlmostEqual(out["ct_number_hu"], 400.0, places=9)
        self.assertEqual(out["material_class"], "light-alloy")

    def test_verdict_geometry_only(self):
        out = ct.ct_inspection_verdict(
            pixel_pitch=PIXEL_PITCH, sod=SOD, odd=ODD,
            required_flaw_m=REQUIRED_FLAW, columns_span=COLUMNS,
            material=MATERIAL, thickness_mm=THICKNESS_MM)
        self.assertNotIn("scan_time_s", out)
        self.assertNotIn("porosity_percent", out)
        self.assertNotIn("ct_number_hu", out)

    def test_verdict_propagates_value_error(self):
        with self.assertRaises(ValueError):
            ct.ct_inspection_verdict(
                pixel_pitch=PIXEL_PITCH, sod=SOD, odd=ODD,
                required_flaw_m=REQUIRED_FLAW, columns_span=COLUMNS,
                material="copper", thickness_mm=THICKNESS_MM)


if __name__ == "__main__":
    unittest.main(verbosity=2)
