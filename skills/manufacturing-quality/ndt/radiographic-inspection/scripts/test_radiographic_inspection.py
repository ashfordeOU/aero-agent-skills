#!/usr/bin/env python3
"""Gate 3 contract test: radiographic inspection (RT) math.

Exercises scripts/radiographic_inspection.py (stdlib unittest, offline).
Contract: docs/harness-contract.md gate 3 - geometric unsharpness
Ug = F * ODD / SOD, exposure time by the inverse-square law
t_new = t_base * (d / d_ref)^2, IQI penetrameter percent sensitivity,
film density verdict against the 2.0 to 4.0 band, discontinuity
classification from the image geometry, and the combined setup verdict
with an unsharpness limit (default 0.25 mm), a sensitivity limit
(default 2.0 percent), and the density band.

All expected values are hand-computed (see each docstring) and were
checked at authoring time.
"""

import os
import sys
import unittest

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import radiographic_inspection as ri  # noqa: E402


class GeometricUnsharpnessTest(unittest.TestCase):
    def test_3_mm_focal_500_sod_30_odd(self):
        # Ug = 3 * 30 / 500 = 0.18 mm.
        self.assertAlmostEqual(ri.geometric_unsharpness(3.0, 500.0, 30.0), 0.18, places=6)

    def test_zero_odd_zero_unsharpness(self):
        # Detector against the object surface: ODD = 0 gives Ug = 0.
        self.assertEqual(ri.geometric_unsharpness(3.0, 500.0, 0.0), 0.0)

    def test_longer_sod_reduces_unsharpness(self):
        # Same focal spot and ODD at double the SOD: Ug halves (0.09 mm).
        far = ri.geometric_unsharpness(3.0, 1000.0, 30.0)
        near = ri.geometric_unsharpness(3.0, 500.0, 30.0)
        self.assertLess(far, near)
        self.assertAlmostEqual(far, 0.09, places=6)

    def test_larger_focal_spot_increases_unsharpness(self):
        # 6 mm focal spot at the same geometry doubles Ug.
        big = ri.geometric_unsharpness(6.0, 500.0, 30.0)
        self.assertAlmostEqual(big, 0.36, places=6)

    def test_zero_sod_raises(self):
        # SOD = 0 leaves the ratio undefined.
        with self.assertRaises(ValueError):
            ri.geometric_unsharpness(3.0, 0.0, 30.0)

    def test_negative_sod_raises(self):
        with self.assertRaises(ValueError):
            ri.geometric_unsharpness(3.0, -500.0, 30.0)

    def test_negative_focal_spot_raises(self):
        with self.assertRaises(ValueError):
            ri.geometric_unsharpness(-3.0, 500.0, 30.0)

    def test_negative_odd_raises(self):
        with self.assertRaises(ValueError):
            ri.geometric_unsharpness(3.0, 500.0, -30.0)


class ExposureTimeTest(unittest.TestCase):
    def test_inverse_square_to_shorter_distance(self):
        # 4 min at 900 mm ref: at 600 mm, 4 * (600/900)^2 = 4 * 4/9 = 16/9.
        self.assertAlmostEqual(ri.exposure_time(4.0, 600.0, 900.0), 16.0 / 9.0, places=6)

    def test_doubling_distance_quadruples_time(self):
        # 4 * (1800/900)^2 = 16 min.
        self.assertAlmostEqual(ri.exposure_time(4.0, 1800.0, 900.0), 16.0, places=6)

    def test_halving_distance_quarters_time(self):
        # 4 * (450/900)^2 = 1 min.
        self.assertAlmostEqual(ri.exposure_time(4.0, 450.0, 900.0), 1.0, places=6)

    def test_same_distance_keeps_time(self):
        self.assertAlmostEqual(ri.exposure_time(4.0, 900.0, 900.0), 4.0, places=6)

    def test_zero_distance_raises(self):
        with self.assertRaises(ValueError):
            ri.exposure_time(4.0, 0.0, 900.0)

    def test_zero_reference_distance_raises(self):
        with self.assertRaises(ValueError):
            ri.exposure_time(4.0, 900.0, 0.0)

    def test_negative_base_time_raises(self):
        with self.assertRaises(ValueError):
            ri.exposure_time(-4.0, 900.0, 900.0)

    def test_negative_distance_raises(self):
        with self.assertRaises(ValueError):
            ri.exposure_time(4.0, -600.0, 900.0)


class IqiSensitivityTest(unittest.TestCase):
    def test_two_percent_sensitivity(self):
        # 0.25 mm visible on a 12.5 mm section: 2.0 percent.
        self.assertAlmostEqual(
            ri.iqi_sensitivity_percent(0.25, 12.5), 2.0, places=6
        )

    def test_one_percent_sensitivity(self):
        # 0.25 mm visible on a 25 mm section: 1.0 percent.
        self.assertAlmostEqual(
            ri.iqi_sensitivity_percent(0.25, 25.0), 1.0, places=6
        )

    def test_visible_exceeds_part_raises(self):
        with self.assertRaises(ValueError):
            ri.iqi_sensitivity_percent(3.0, 2.0)

    def test_zero_visible_thickness_raises(self):
        with self.assertRaises(ValueError):
            ri.iqi_sensitivity_percent(0.0, 12.5)

    def test_zero_part_thickness_raises(self):
        with self.assertRaises(ValueError):
            ri.iqi_sensitivity_percent(0.25, 0.0)


class DensityVerdictTest(unittest.TestCase):
    def test_mid_band_acceptable(self):
        v = ri.density_verdict(3.0)
        self.assertTrue(v["acceptable"])
        self.assertEqual(v["verdict"], "acceptable")

    def test_band_edges_are_inclusive(self):
        self.assertTrue(ri.density_verdict(2.0)["acceptable"])
        self.assertTrue(ri.density_verdict(4.0)["acceptable"])

    def test_below_band_is_too_low(self):
        v = ri.density_verdict(1.9)
        self.assertFalse(v["acceptable"])
        self.assertEqual(v["verdict"], "too-low")

    def test_above_band_is_too_high(self):
        v = ri.density_verdict(4.1)
        self.assertFalse(v["acceptable"])
        self.assertEqual(v["verdict"], "too-high")

    def test_negative_density_raises(self):
        with self.assertRaises(ValueError):
            ri.density_verdict(-0.5)

    def test_nan_density_raises(self):
        with self.assertRaises(ValueError):
            ri.density_verdict(float("nan"))


class DiscontinuityClassTest(unittest.TestCase):
    def test_round_globular_is_porosity(self):
        self.assertEqual(ri.discontinuity_class("round globular gas pockets"), "porosity")

    def test_sharp_elongated_is_crack(self):
        self.assertEqual(ri.discontinuity_class("sharp elongated hairline"), "crack")

    def test_compact_metallic_is_inclusion(self):
        self.assertEqual(ri.discontinuity_class("compact dense metallic foreign material"), "inclusion")

    def test_flat_planar_is_slag(self):
        self.assertEqual(ri.discontinuity_class("flat planar angular weld residue"), "slag")

    def test_unknown_descriptor_raises(self):
        with self.assertRaises(ValueError):
            ri.discontinuity_class("wavy mottled blotch")

    def test_empty_descriptor_raises(self):
        with self.assertRaises(ValueError):
            ri.discontinuity_class("   ")
        with self.assertRaises(ValueError):
            ri.discontinuity_class(None)


class RtSetupVerdictTest(unittest.TestCase):
    def test_clean_setup_is_acceptable(self):
        # Ug 0.18 mm under 0.25, sensitivity 2.0 percent, density 3.0.
        v = ri.rt_setup_verdict(0.18, 2.0, 3.0)
        self.assertTrue(v["acceptable"])
        self.assertEqual(v["reasons"], [])

    def test_unsharpness_over_limit_fails(self):
        v = ri.rt_setup_verdict(0.30, 2.0, 3.0)
        self.assertFalse(v["acceptable"])
        self.assertTrue(any("unsharpness" in r for r in v["reasons"]))

    def test_sensitivity_over_limit_fails(self):
        v = ri.rt_setup_verdict(0.18, 3.5, 3.0)
        self.assertFalse(v["acceptable"])
        self.assertTrue(any("sensitivity" in r for r in v["reasons"]))

    def test_density_out_of_band_fails(self):
        v = ri.rt_setup_verdict(0.18, 2.0, 1.5)
        self.assertFalse(v["acceptable"])
        self.assertTrue(any("density" in r for r in v["reasons"]))

    def test_custom_unsharpness_limit(self):
        # 0.30 mm exceeds the default 0.25 mm limit but passes a 0.5 mm limit.
        v = ri.rt_setup_verdict(0.30, 2.0, 3.0, unsharpness_limit_mm=0.5)
        self.assertTrue(v["acceptable"])

    def test_negative_sensitivity_raises(self):
        with self.assertRaises(ValueError):
            ri.rt_setup_verdict(0.18, -1.0, 3.0)

    def test_non_positive_limit_raises(self):
        with self.assertRaises(ValueError):
            ri.rt_setup_verdict(0.18, 2.0, 3.0, unsharpness_limit_mm=0.0)


if __name__ == "__main__":
    unittest.main()
