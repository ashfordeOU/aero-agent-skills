"""Contract tests for the compression and shear method logic.

The cases read a run the way a reviewer does: whether the arrangement that
was used can deliver the property that was asked for, whether a compression
specimen was short enough that the peak load was material rather than column
behaviour, and whether a shear result was divided by every plane that
actually carried the load.
"""

import math
import unittest

from q7045_compression_and_shear_testing_logic import (
    BUCKLING_ALERT_RATIO,
    MODES,
    SLENDERNESS_BAND,
    assess_compression_and_shear_test,
    compressive_strength_mpa,
    euler_buckling_stress_mpa,
    method_for_property,
    radius_of_gyration_mm,
    shear_plane_area_mm2,
    shear_strength_mpa,
    slenderness_ratio,
)

DIAMETER = 10.0
AREA = math.pi * 25.0          # pi * d^2 / 4 for d = 10 mm
MODULUS = 70000.0
PEAK_LOAD = 25000.0
SHEAR_LOAD = 20000.0


def _compression_spec(**overrides):
    spec = {
        "property": "compressive-ultimate-strength",
        "mode": "compression",
        "diameter_mm": DIAMETER,
        "length_mm": 25.0,
        "modulus_mpa": MODULUS,
        "peak_load_n": PEAK_LOAD,
    }
    spec.update(overrides)
    return spec


def _shear_spec(**overrides):
    spec = {
        "property": "ultimate-shear-strength-pin",
        "mode": "double-shear",
        "diameter_mm": DIAMETER,
        "peak_load_n": SHEAR_LOAD,
    }
    spec.update(overrides)
    return spec


class MethodApplicabilityTests(unittest.TestCase):
    def test_compressive_property_maps_to_compression(self):
        self.assertEqual(method_for_property("compressive-yield-strength"),
                         "compression")

    def test_pin_shear_property_maps_to_double_shear(self):
        self.assertEqual(method_for_property("ultimate-shear-strength-pin"),
                         "double-shear")

    def test_coupon_shear_property_maps_to_single_shear(self):
        self.assertEqual(method_for_property("ultimate-shear-strength-coupon"),
                         "single-shear")

    def test_shear_modulus_is_outside_the_method_set(self):
        self.assertIsNone(method_for_property("shear-modulus"))

    def test_unknown_property_rejected(self):
        with self.assertRaises(ValueError):
            method_for_property("bearing-strength")

    def test_non_string_property_rejected(self):
        with self.assertRaises(ValueError):
            method_for_property(7)

    def test_three_arrangements_are_covered(self):
        self.assertEqual(len(MODES), 3)


class GeometryTests(unittest.TestCase):
    def test_radius_of_gyration_is_a_quarter_of_the_diameter(self):
        self.assertAlmostEqual(radius_of_gyration_mm(DIAMETER), 2.5, places=9)

    def test_slenderness_of_a_short_specimen(self):
        self.assertAlmostEqual(slenderness_ratio(25.0, DIAMETER), 10.0, places=9)

    def test_zero_diameter_rejected(self):
        with self.assertRaises(ValueError):
            radius_of_gyration_mm(0.0)

    def test_negative_length_rejected(self):
        with self.assertRaises(ValueError):
            slenderness_ratio(-25.0, DIAMETER)

    def test_euler_stress_at_slenderness_ten(self):
        value = euler_buckling_stress_mpa(MODULUS, 10.0)
        self.assertAlmostEqual(value / (700.0 * math.pi * math.pi), 1.0, places=9)

    def test_euler_stress_falls_with_the_square_of_slenderness(self):
        near = euler_buckling_stress_mpa(MODULUS, 10.0)
        far = euler_buckling_stress_mpa(MODULUS, 20.0)
        self.assertAlmostEqual(4.0 * far / near, 1.0, places=9)

    def test_end_fixity_scales_the_euler_stress(self):
        pinned = euler_buckling_stress_mpa(MODULUS, 10.0)
        fixed = euler_buckling_stress_mpa(MODULUS, 10.0, 4.0)
        self.assertAlmostEqual(fixed / pinned, 4.0, places=9)

    def test_zero_slenderness_rejected(self):
        with self.assertRaises(ValueError):
            euler_buckling_stress_mpa(MODULUS, 0.0)


class ShearAreaTests(unittest.TestCase):
    def test_single_shear_area(self):
        self.assertAlmostEqual(
            shear_plane_area_mm2(DIAMETER, "single-shear") / AREA, 1.0, places=9
        )

    def test_double_shear_area_is_twice_the_single(self):
        single = shear_plane_area_mm2(DIAMETER, "single-shear")
        double = shear_plane_area_mm2(DIAMETER, "double-shear")
        self.assertAlmostEqual(double / single, 2.0, places=9)

    def test_compression_is_not_a_shear_arrangement(self):
        with self.assertRaises(ValueError):
            shear_plane_area_mm2(DIAMETER, "compression")

    def test_unknown_arrangement_rejected(self):
        with self.assertRaises(ValueError):
            shear_plane_area_mm2(DIAMETER, "torsion")

    def test_single_shear_strength(self):
        value = shear_strength_mpa(SHEAR_LOAD, DIAMETER, "single-shear")
        self.assertAlmostEqual(value / (SHEAR_LOAD / AREA), 1.0, places=9)

    def test_double_shear_halves_the_strength(self):
        single = shear_strength_mpa(SHEAR_LOAD, DIAMETER, "single-shear")
        double = shear_strength_mpa(SHEAR_LOAD, DIAMETER, "double-shear")
        self.assertAlmostEqual(2.0 * double / single, 1.0, places=9)

    def test_zero_load_rejected(self):
        with self.assertRaises(ValueError):
            shear_strength_mpa(0.0, DIAMETER, "single-shear")

    def test_compressive_strength_uses_the_full_section(self):
        value = compressive_strength_mpa(PEAK_LOAD, DIAMETER)
        self.assertAlmostEqual(value / (PEAK_LOAD / AREA), 1.0, places=9)


class CompressionAssessmentTests(unittest.TestCase):
    def test_short_specimen_delivers_the_property(self):
        result = assess_compression_and_shear_test(_compression_spec())
        self.assertTrue(result["property_delivered"])
        self.assertEqual(result["findings"], [])

    def test_reported_strength_matches_the_section_area(self):
        result = assess_compression_and_shear_test(_compression_spec())
        self.assertAlmostEqual(
            result["strength_mpa"] / (PEAK_LOAD / AREA), 1.0, places=9
        )

    def test_short_specimen_sits_inside_the_slenderness_band(self):
        result = assess_compression_and_shear_test(_compression_spec())
        low, high = SLENDERNESS_BAND
        self.assertGreater(result["length_to_diameter"], low)
        self.assertLess(result["length_to_diameter"], high)

    def test_slender_specimen_is_reported_twice(self):
        result = assess_compression_and_shear_test(_compression_spec(length_mm=100.0))
        self.assertFalse(result["property_delivered"])
        self.assertEqual(len(result["findings"]), 2)

    def test_buckling_utilisation_is_reported(self):
        result = assess_compression_and_shear_test(_compression_spec(length_mm=100.0))
        self.assertGreater(result["buckling_utilisation"], BUCKLING_ALERT_RATIO)

    def test_compression_run_without_modulus_rejected(self):
        spec = _compression_spec()
        del spec["modulus_mpa"]
        with self.assertRaises(ValueError):
            assess_compression_and_shear_test(spec)

    def test_shear_property_asked_of_a_compression_run_is_reported(self):
        result = assess_compression_and_shear_test(
            _compression_spec(property="ultimate-shear-strength-pin")
        )
        self.assertFalse(result["property_delivered"])
        self.assertIn("double-shear", result["findings"][0])


class ShearAssessmentTests(unittest.TestCase):
    def test_pin_shear_delivers_the_property(self):
        result = assess_compression_and_shear_test(_shear_spec())
        self.assertTrue(result["property_delivered"])
        self.assertEqual(result["planes"], 2)

    def test_declared_plane_count_match_is_silent(self):
        result = assess_compression_and_shear_test(_shear_spec(declared_planes=2))
        self.assertEqual(result["findings"], [])

    def test_declared_plane_count_mismatch_is_reported(self):
        result = assess_compression_and_shear_test(_shear_spec(declared_planes=1))
        self.assertFalse(result["property_delivered"])
        self.assertIn("plane", result["findings"][0])

    def test_non_integer_plane_count_rejected(self):
        with self.assertRaises(ValueError):
            assess_compression_and_shear_test(_shear_spec(declared_planes=2.0))

    def test_property_outside_the_method_set_is_reported(self):
        result = assess_compression_and_shear_test(_shear_spec(property="shear-modulus"))
        self.assertFalse(result["property_delivered"])
        self.assertIn("cannot be obtained", result["findings"][0])

    def test_coupon_property_on_a_pin_rig_is_reported(self):
        result = assess_compression_and_shear_test(
            _shear_spec(property="ultimate-shear-strength-coupon")
        )
        self.assertFalse(result["property_delivered"])

    def test_unknown_mode_rejected(self):
        with self.assertRaises(ValueError):
            assess_compression_and_shear_test(_shear_spec(mode="torsion"))

    def test_missing_spec_key_rejected(self):
        spec = _shear_spec()
        del spec["peak_load_n"]
        with self.assertRaises(ValueError):
            assess_compression_and_shear_test(spec)

    def test_non_mapping_spec_rejected(self):
        with self.assertRaises(ValueError):
            assess_compression_and_shear_test(["double-shear"])


if __name__ == "__main__":
    unittest.main()
