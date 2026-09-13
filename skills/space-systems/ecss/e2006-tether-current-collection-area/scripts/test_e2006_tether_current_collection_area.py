#!/usr/bin/env python3
"""Contract test for the clause 10.2.2 collecting-surface sizing logic."""

import unittest

from e2006_tether_current_collection_area_logic import (
    GEOMETRIES,
    GEOMETRY_CYLINDER,
    GEOMETRY_FLAT_TAPE,
    GEOMETRY_SPHERE,
    REQUIRED_AREA_MARGIN,
    area_margin,
    collected_current,
    debye_length_m,
    density_within_rating,
    effective_current_density,
    mean_flux_speed,
    oml_enhancement,
    required_collecting_area,
    sized_collecting_area,
    surface_current_density,
    thermal_current_density,
    thin_sheath_valid,
    verify_collecting_surface,
)

# Reference low-orbit ionospheric condition used across the cases.
DENSITY = 1.0e11
TEMPERATURE = 0.1
BIAS = 200.0


def spec(**overrides):
    base = {
        "operating_current_a": 0.5,
        "available_area_m2": 0.4,
        "electron_density_m3": DENSITY,
        "electron_temperature_ev": TEMPERATURE,
        "bias_v": BIAS,
        "geometry": GEOMETRY_SPHERE,
    }
    base.update(overrides)
    return base


class TestPlasmaQuantities(unittest.TestCase):
    def test_mean_flux_speed_at_a_tenth_of_an_electronvolt(self):
        self.assertAlmostEqual(mean_flux_speed(TEMPERATURE), 52907.929341766, places=3)

    def test_flux_speed_scales_as_the_square_root_of_temperature(self):
        self.assertAlmostEqual(
            mean_flux_speed(0.4) / mean_flux_speed(0.1), 2.0, places=9
        )

    def test_thermal_current_density_reference_value(self):
        self.assertAlmostEqual(
            thermal_current_density(DENSITY, TEMPERATURE), 8.476784814470048e-04,
            places=12,
        )

    def test_thermal_current_density_is_linear_in_density(self):
        low = thermal_current_density(1.0e11, TEMPERATURE)
        high = thermal_current_density(3.0e11, TEMPERATURE)
        self.assertAlmostEqual(high / low, 3.0, places=9)

    def test_debye_length_reference_value(self):
        self.assertAlmostEqual(
            debye_length_m(DENSITY, TEMPERATURE), 0.007433941994700464, places=9
        )

    def test_debye_length_shrinks_with_density(self):
        self.assertLess(
            debye_length_m(1.0e12, TEMPERATURE), debye_length_m(1.0e11, TEMPERATURE)
        )

    def test_zero_temperature_rejected(self):
        with self.assertRaises(ValueError):
            mean_flux_speed(0.0)

    def test_negative_density_rejected(self):
        with self.assertRaises(ValueError):
            thermal_current_density(-1.0e11, TEMPERATURE)

    def test_non_numeric_density_rejected(self):
        with self.assertRaises(ValueError):
            thermal_current_density("1e11", TEMPERATURE)

    def test_infinite_temperature_rejected(self):
        with self.assertRaises(ValueError):
            debye_length_m(DENSITY, float("inf"))


class TestThinSheath(unittest.TestCase):
    def test_small_collector_is_inside_the_thin_sheath_regime(self):
        self.assertTrue(thin_sheath_valid(0.001, debye_length_m(DENSITY, TEMPERATURE)))

    def test_large_collector_leaves_the_regime(self):
        self.assertFalse(thin_sheath_valid(0.5, debye_length_m(DENSITY, TEMPERATURE)))

    def test_radius_exactly_at_the_debye_length_stays_valid(self):
        debye = debye_length_m(DENSITY, TEMPERATURE)
        self.assertTrue(thin_sheath_valid(debye, debye))

    def test_zero_radius_rejected(self):
        with self.assertRaises(ValueError):
            thin_sheath_valid(0.0, 0.01)

    def test_zero_debye_rejected(self):
        with self.assertRaises(ValueError):
            thin_sheath_valid(0.01, 0.0)


class TestEnhancement(unittest.TestCase):
    def test_sphere_enhancement_is_linear_in_bias(self):
        self.assertAlmostEqual(
            oml_enhancement(BIAS, TEMPERATURE, GEOMETRY_SPHERE), 2001.0, places=9
        )

    def test_cylinder_enhancement_is_square_root_like(self):
        self.assertAlmostEqual(
            oml_enhancement(BIAS, TEMPERATURE, GEOMETRY_CYLINDER),
            50.47526452644959,
            places=9,
        )

    def test_flat_tape_gains_nothing(self):
        self.assertAlmostEqual(
            oml_enhancement(BIAS, TEMPERATURE, GEOMETRY_FLAT_TAPE), 1.0, places=12
        )

    def test_unbiased_sphere_collects_the_random_flux_only(self):
        self.assertAlmostEqual(
            oml_enhancement(0.0, TEMPERATURE, GEOMETRY_SPHERE), 1.0, places=12
        )

    def test_sphere_beats_cylinder_at_high_bias(self):
        self.assertGreater(
            oml_enhancement(BIAS, TEMPERATURE, GEOMETRY_SPHERE),
            oml_enhancement(BIAS, TEMPERATURE, GEOMETRY_CYLINDER),
        )

    def test_every_geometry_is_supported(self):
        for geometry in GEOMETRIES:
            self.assertGreaterEqual(oml_enhancement(10.0, TEMPERATURE, geometry), 1.0)

    def test_negative_bias_rejected(self):
        with self.assertRaises(ValueError):
            oml_enhancement(-50.0, TEMPERATURE, GEOMETRY_SPHERE)

    def test_unknown_geometry_rejected(self):
        with self.assertRaises(ValueError):
            oml_enhancement(BIAS, TEMPERATURE, "conical-shell")

    def test_zero_temperature_rejected_in_enhancement(self):
        with self.assertRaises(ValueError):
            oml_enhancement(BIAS, 0.0, GEOMETRY_SPHERE)


class TestCurrentAndArea(unittest.TestCase):
    def test_effective_density_reference_value(self):
        self.assertAlmostEqual(
            effective_current_density(DENSITY, TEMPERATURE, BIAS, GEOMETRY_SPHERE),
            1.6962046413754566,
            places=9,
        )

    def test_collected_current_scales_with_area(self):
        one = collected_current(1.0, DENSITY, TEMPERATURE, BIAS, GEOMETRY_SPHERE)
        two = collected_current(2.0, DENSITY, TEMPERATURE, BIAS, GEOMETRY_SPHERE)
        self.assertAlmostEqual(two / one, 2.0, places=9)

    def test_required_area_reference_value(self):
        self.assertAlmostEqual(
            required_collecting_area(
                0.5, DENSITY, TEMPERATURE, BIAS, GEOMETRY_SPHERE
            ),
            0.29477575276208934,
            places=9,
        )

    def test_cylinder_needs_far_more_area_than_a_sphere(self):
        sphere = required_collecting_area(
            0.5, DENSITY, TEMPERATURE, BIAS, GEOMETRY_SPHERE
        )
        cylinder = required_collecting_area(
            0.5, DENSITY, TEMPERATURE, BIAS, GEOMETRY_CYLINDER
        )
        self.assertGreater(cylinder, sphere)
        self.assertAlmostEqual(cylinder, 11.685848242912225, places=6)

    def test_unbiased_flat_tape_needs_the_largest_area(self):
        self.assertAlmostEqual(
            required_collecting_area(
                0.5, DENSITY, TEMPERATURE, BIAS, GEOMETRY_FLAT_TAPE
            ),
            589.8462812769408,
            places=4,
        )

    def test_area_and_current_are_inverse(self):
        area = required_collecting_area(
            0.5, DENSITY, TEMPERATURE, BIAS, GEOMETRY_SPHERE
        )
        back = collected_current(area, DENSITY, TEMPERATURE, BIAS, GEOMETRY_SPHERE)
        self.assertAlmostEqual(back, 0.5, places=12)

    def test_sized_area_carries_the_margin(self):
        required = required_collecting_area(
            0.5, DENSITY, TEMPERATURE, BIAS, GEOMETRY_SPHERE
        )
        sized = sized_collecting_area(
            0.5, DENSITY, TEMPERATURE, BIAS, GEOMETRY_SPHERE
        )
        self.assertAlmostEqual(sized / required, REQUIRED_AREA_MARGIN, places=9)

    def test_margin_of_one_is_accepted(self):
        sized = sized_collecting_area(
            0.5, DENSITY, TEMPERATURE, BIAS, GEOMETRY_SPHERE, margin=1.0
        )
        self.assertAlmostEqual(sized, 0.29477575276208934, places=9)

    def test_margin_below_one_rejected(self):
        with self.assertRaises(ValueError):
            sized_collecting_area(
                0.5, DENSITY, TEMPERATURE, BIAS, GEOMETRY_SPHERE, margin=0.8
            )

    def test_zero_margin_rejected(self):
        with self.assertRaises(ValueError):
            sized_collecting_area(
                0.5, DENSITY, TEMPERATURE, BIAS, GEOMETRY_SPHERE, margin=0.0
            )

    def test_zero_target_current_rejected(self):
        with self.assertRaises(ValueError):
            required_collecting_area(
                0.0, DENSITY, TEMPERATURE, BIAS, GEOMETRY_SPHERE
            )

    def test_zero_area_rejected(self):
        with self.assertRaises(ValueError):
            collected_current(0.0, DENSITY, TEMPERATURE, BIAS, GEOMETRY_SPHERE)

    def test_area_margin_ratio(self):
        self.assertAlmostEqual(area_margin(0.6, 0.3), 2.0, places=9)

    def test_area_margin_rejects_zero_requirement(self):
        with self.assertRaises(ValueError):
            area_margin(0.6, 0.0)


class TestSurfaceDensityRating(unittest.TestCase):
    def test_surface_density_value(self):
        self.assertAlmostEqual(surface_current_density(0.5, 0.25), 2.0, places=9)

    def test_density_inside_rating(self):
        self.assertTrue(density_within_rating(0.5, 1.0, 2.0))

    def test_density_outside_rating(self):
        self.assertFalse(density_within_rating(5.0, 1.0, 2.0))

    def test_exact_rating_boundary_passes_despite_float_error(self):
        # 0.1 + 0.2 is a sum of powers that lands a few ULPs above 0.3; a
        # physically compliant case must not be failed by that artefact.
        self.assertTrue(density_within_rating(0.1 + 0.2, 1.0, 0.3))

    def test_zero_rating_rejected(self):
        with self.assertRaises(ValueError):
            density_within_rating(0.5, 1.0, 0.0)

    def test_zero_current_rejected(self):
        with self.assertRaises(ValueError):
            surface_current_density(0.0, 1.0)


class TestVerifyCollectingSurface(unittest.TestCase):
    def test_adequate_sphere_passes(self):
        result = verify_collecting_surface(spec())
        self.assertTrue(result["compliant"])
        self.assertEqual(result["findings"], [])
        self.assertAlmostEqual(result["required_area_m2"], 0.29477575276208934, places=9)
        self.assertAlmostEqual(result["sized_area_m2"], 0.3537309033145072, places=9)
        self.assertGreater(result["area_margin"], REQUIRED_AREA_MARGIN)

    def test_area_exactly_at_the_sized_value_passes(self):
        sized = sized_collecting_area(
            0.5, DENSITY, TEMPERATURE, BIAS, GEOMETRY_SPHERE
        )
        # One representation step below the sized value: still the compliant
        # case, and the comparison must absorb the difference.
        result = verify_collecting_surface(
            spec(available_area_m2=sized - abs(sized) * 1e-15)
        )
        self.assertTrue(result["compliant"])

    def test_area_short_of_the_margin_is_reported(self):
        sized = sized_collecting_area(
            0.5, DENSITY, TEMPERATURE, BIAS, GEOMETRY_SPHERE
        )
        result = verify_collecting_surface(spec(available_area_m2=0.9 * sized))
        self.assertFalse(result["compliant"])
        self.assertEqual(len(result["findings"]), 1)
        self.assertIn("below", result["findings"][0])

    def test_area_short_of_the_bare_requirement_reports_both(self):
        result = verify_collecting_surface(spec(available_area_m2=0.1))
        self.assertFalse(result["compliant"])
        self.assertEqual(len(result["findings"]), 2)
        self.assertLess(result["collectable_current_a"], 0.5)

    def test_cylinder_of_the_same_area_falls_short(self):
        result = verify_collecting_surface(spec(geometry=GEOMETRY_CYLINDER))
        self.assertFalse(result["compliant"])
        self.assertAlmostEqual(result["required_area_m2"], 11.685848242912225, places=6)

    def test_material_rating_violation_is_reported(self):
        result = verify_collecting_surface(spec(max_current_density_a_per_m2=0.5))
        self.assertFalse(result["compliant"])
        self.assertTrue(any("rating" in f for f in result["findings"]))
        self.assertAlmostEqual(
            result["surface_current_density_a_per_m2"], 1.25, places=9
        )

    def test_material_rating_satisfied(self):
        result = verify_collecting_surface(spec(max_current_density_a_per_m2=5.0))
        self.assertTrue(result["compliant"])

    def test_thin_sheath_violation_is_reported(self):
        result = verify_collecting_surface(spec(characteristic_radius_m=0.5))
        self.assertFalse(result["compliant"])
        self.assertFalse(result["thin_sheath_valid"])
        self.assertTrue(any("Debye" in f for f in result["findings"]))

    def test_thin_sheath_respected(self):
        result = verify_collecting_surface(spec(characteristic_radius_m=0.002))
        self.assertTrue(result["compliant"])
        self.assertTrue(result["thin_sheath_valid"])

    def test_debye_length_is_reported_even_without_a_radius(self):
        result = verify_collecting_surface(spec())
        self.assertAlmostEqual(result["debye_length_m"], 0.007433941994700464, places=9)

    def test_custom_required_margin_tightens_the_check(self):
        result = verify_collecting_surface(spec(required_margin=2.0))
        self.assertFalse(result["compliant"])

    def test_bad_required_margin_rejected(self):
        with self.assertRaises(ValueError):
            verify_collecting_surface(spec(required_margin=0.5))

    def test_missing_field_rejected(self):
        broken = spec()
        del broken["bias_v"]
        with self.assertRaises(ValueError):
            verify_collecting_surface(broken)

    def test_unknown_geometry_rejected(self):
        with self.assertRaises(ValueError):
            verify_collecting_surface(spec(geometry="toroid"))

    def test_non_mapping_spec_rejected(self):
        with self.assertRaises(ValueError):
            verify_collecting_surface("sphere")

    def test_negative_operating_current_rejected(self):
        with self.assertRaises(ValueError):
            verify_collecting_surface(spec(operating_current_a=-0.5))

    def test_negative_available_area_rejected(self):
        with self.assertRaises(ValueError):
            verify_collecting_surface(spec(available_area_m2=-1.0))


if __name__ == "__main__":
    unittest.main()
