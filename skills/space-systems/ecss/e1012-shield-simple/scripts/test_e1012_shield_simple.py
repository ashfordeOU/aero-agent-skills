"""
Gate-3 contract tests for e1012-shield-simple logic.
Covers planar, spherical, and solid-angle sectoring approaches.
stdlib unittest only — offline, deterministic.
Run: python3 test_e1012_shield_simple.py
"""

import math
import sys
import os
import unittest

sys.path.insert(0, os.path.dirname(__file__))

from e1012_shield_simple_logic import (
    ShieldingError,
    planar_areal_density,
    planar_thickness_from_areal_density,
    spherical_shell_areal_density,
    solid_sphere_areal_density,
    solid_angle_weighted_areal_density,
    total_solid_angle_check,
    build_uniform_sectoring,
    minimum_sector_areal_density,
    maximum_sector_areal_density,
    shielding_summary,
)


class TestPlanarArealDensity(unittest.TestCase):

    def test_standard_aluminium_slab(self):
        # 2 mm Al: thickness=0.2 cm, density=2.7 g/cm³ → 0.54 g/cm²
        self.assertAlmostEqual(planar_areal_density(0.2, 2.7), 0.54, places=6)

    def test_zero_thickness_gives_zero(self):
        self.assertEqual(planar_areal_density(0.0, 2.7), 0.0)

    def test_negative_thickness_raises(self):
        with self.assertRaises(ShieldingError):
            planar_areal_density(-0.5, 2.7)

    def test_zero_density_raises(self):
        with self.assertRaises(ShieldingError):
            planar_areal_density(0.5, 0.0)

    def test_negative_density_raises(self):
        with self.assertRaises(ShieldingError):
            planar_areal_density(0.5, -1.0)

    def test_roundtrip_thickness(self):
        density = 2.7
        original_thickness = 0.35
        ad = planar_areal_density(original_thickness, density)
        recovered = planar_thickness_from_areal_density(ad, density)
        self.assertAlmostEqual(recovered, original_thickness, places=10)

    def test_invert_zero_areal_density(self):
        self.assertEqual(planar_thickness_from_areal_density(0.0, 2.7), 0.0)


class TestSphericalGeometry(unittest.TestCase):

    def test_shell_basic(self):
        # outer=10 cm, inner=9 cm, density=2.7 → shell=1 cm → 2.7 g/cm²
        self.assertAlmostEqual(
            spherical_shell_areal_density(10.0, 9.0, 2.7), 2.7, places=6
        )

    def test_shell_outer_equals_inner_raises(self):
        with self.assertRaises(ShieldingError):
            spherical_shell_areal_density(5.0, 5.0, 2.7)

    def test_shell_outer_less_than_inner_raises(self):
        with self.assertRaises(ShieldingError):
            spherical_shell_areal_density(4.0, 5.0, 2.7)

    def test_shell_negative_inner_radius_raises(self):
        with self.assertRaises(ShieldingError):
            spherical_shell_areal_density(5.0, -1.0, 2.7)

    def test_solid_sphere_basic(self):
        # radius=5 cm, density=2.7 → 13.5 g/cm²
        self.assertAlmostEqual(solid_sphere_areal_density(5.0, 2.7), 13.5, places=6)

    def test_solid_sphere_zero_radius_raises(self):
        with self.assertRaises(ShieldingError):
            solid_sphere_areal_density(0.0, 2.7)

    def test_solid_sphere_negative_radius_raises(self):
        with self.assertRaises(ShieldingError):
            solid_sphere_areal_density(-3.0, 2.7)

    def test_shell_equals_solid_minus_inner(self):
        # Shell(5,4,rho) should equal solid_sphere(5,rho) - solid_sphere(4,rho)
        rho = 2.7
        diff = solid_sphere_areal_density(5.0, rho) - solid_sphere_areal_density(4.0, rho)
        shell = spherical_shell_areal_density(5.0, 4.0, rho)
        self.assertAlmostEqual(diff, shell, places=10)


class TestSolidAngleSectoring(unittest.TestCase):

    def test_uniform_sectoring_count(self):
        sectors = build_uniform_sectoring(8, 2.7, 0.2)
        self.assertEqual(len(sectors), 8)

    def test_uniform_sectoring_solid_angles(self):
        n = 12
        sectors = build_uniform_sectoring(n, 2.7, 0.2)
        expected = 4.0 * math.pi / n
        for s in sectors:
            self.assertAlmostEqual(s["solid_angle_sr"], expected, places=10)

    def test_uniform_sectoring_full_sphere_coverage(self):
        sectors = build_uniform_sectoring(6, 2.7, 0.3)
        self.assertTrue(total_solid_angle_check(sectors))

    def test_uniform_sectoring_zero_density_raises(self):
        with self.assertRaises(ShieldingError):
            build_uniform_sectoring(6, 0.0, 0.2)

    def test_uniform_sectoring_negative_n_raises(self):
        with self.assertRaises(ShieldingError):
            build_uniform_sectoring(-2, 2.7, 0.2)

    def test_weighted_mean_uniform_sectors(self):
        # Uniform sectors — weighted mean equals the per-sector AD
        sectors = build_uniform_sectoring(10, 2.7, 0.5)
        expected_ad = planar_areal_density(0.5, 2.7)
        self.assertAlmostEqual(
            solid_angle_weighted_areal_density(sectors), expected_ad, places=6
        )

    def test_weighted_mean_two_sectors(self):
        # Sectors: (3π sr, AD=1.0) and (π sr, AD=3.0)
        # Weighted mean = (3π×1 + π×3) / 4π = 6π/4π = 1.5
        sectors = [
            {"solid_angle_sr": 3.0 * math.pi, "areal_density_g_cm2": 1.0},
            {"solid_angle_sr": 1.0 * math.pi, "areal_density_g_cm2": 3.0},
        ]
        self.assertAlmostEqual(
            solid_angle_weighted_areal_density(sectors), 1.5, places=6
        )
        self.assertTrue(total_solid_angle_check(sectors))

    def test_empty_sectors_raises(self):
        with self.assertRaises(ShieldingError):
            solid_angle_weighted_areal_density([])

    def test_sector_missing_key_raises(self):
        bad = [{"solid_angle_sr": math.pi}]  # missing areal_density_g_cm2
        with self.assertRaises(ShieldingError):
            solid_angle_weighted_areal_density(bad)

    def test_sector_negative_areal_density_raises(self):
        bad = [{"solid_angle_sr": math.pi, "areal_density_g_cm2": -1.0}]
        with self.assertRaises(ShieldingError):
            solid_angle_weighted_areal_density(bad)

    def test_partial_coverage_fails_check(self):
        # Only π sr — well short of 4π
        sectors = [{"solid_angle_sr": math.pi}]
        self.assertFalse(total_solid_angle_check(sectors))

    def test_min_max_areal_density(self):
        sectors = [
            {"solid_angle_sr": math.pi, "areal_density_g_cm2": 0.5},
            {"solid_angle_sr": 2.0 * math.pi, "areal_density_g_cm2": 1.0},
            {"solid_angle_sr": math.pi, "areal_density_g_cm2": 2.5},
        ]
        self.assertAlmostEqual(minimum_sector_areal_density(sectors), 0.5, places=6)
        self.assertAlmostEqual(maximum_sector_areal_density(sectors), 2.5, places=6)

    def test_shielding_summary_keys(self):
        sectors = build_uniform_sectoring(4, 2.7, 0.2)
        result = shielding_summary(sectors)
        for key in (
            "n_sectors",
            "min_areal_density_g_cm2",
            "max_areal_density_g_cm2",
            "weighted_mean_areal_density_g_cm2",
            "full_sphere_coverage",
        ):
            self.assertIn(key, result)

    def test_shielding_summary_coverage_true(self):
        sectors = build_uniform_sectoring(16, 2.7, 0.3)
        summary = shielding_summary(sectors)
        self.assertTrue(summary["full_sphere_coverage"])
        self.assertEqual(summary["n_sectors"], 16)

    def test_shielding_summary_min_le_mean_le_max(self):
        sectors = [
            {"solid_angle_sr": math.pi, "areal_density_g_cm2": 0.5},
            {"solid_angle_sr": 2.0 * math.pi, "areal_density_g_cm2": 1.2},
            {"solid_angle_sr": math.pi, "areal_density_g_cm2": 2.0},
        ]
        s = shielding_summary(sectors)
        self.assertLessEqual(s["min_areal_density_g_cm2"],
                             s["weighted_mean_areal_density_g_cm2"])
        self.assertLessEqual(s["weighted_mean_areal_density_g_cm2"],
                             s["max_areal_density_g_cm2"])

    def test_empty_shielding_summary_raises(self):
        with self.assertRaises(ShieldingError):
            shielding_summary([])


if __name__ == "__main__":
    unittest.main()
