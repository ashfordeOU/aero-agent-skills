"""Contract test for the direct surface IR measurement leaf (stdlib unittest)."""

import math
import unittest

from q7005_direct_surface_ir_measurement_logic import (
    ATR_SAMPLING_DEPTH_UM,
    DIFFUSE_REFLECTANCE,
    GRAZING_MAX_ANGLE_DEG,
    GRAZING_MIN_ANGLE_DEG,
    INTERNAL_REFLECTION,
    MIN_SPECULAR_REFLECTANCE,
    REFLECTION_ABSORPTION,
    areal_mass_ug_per_cm2,
    assess_direct_measurement,
    film_thickness_um,
    net_reflection_absorbance,
    path_enhancement,
    select_technique,
    validate_incidence_angle,
    validate_surface,
)


def surface(**kw):
    record = {
        "finish": "specular",
        "specular_reflectance": 0.92,
        "accessible": True,
        "spot_diameter_mm": 3.0,
        "aperture_diameter_mm": 8.0,
    }
    record.update(kw)
    return record


def spec(**kw):
    base = {
        "surface": surface(),
        "incidence_angle_deg": 60.0,
        "sample_absorbance": 0.0250,
        "reference_absorbance": 0.0050,
        "sample_substrate": "aluminium-6061-polished",
        "reference_substrate": "aluminium-6061-polished",
        "absorptivity_abs_per_um": 0.05,
        "density_g_per_cm3": 1.0,
    }
    base.update(kw)
    return base


class TestValidateSurface(unittest.TestCase):
    def test_valid_record_normalises(self):
        norm = validate_surface(surface(specular_reflectance=1))
        self.assertAlmostEqual(norm["specular_reflectance"], 1.0, places=9)
        self.assertEqual(norm["finish"], "specular")

    def test_non_mapping_raises(self):
        with self.assertRaises(ValueError):
            validate_surface("specular")

    def test_missing_key_raises(self):
        record = surface()
        del record["accessible"]
        with self.assertRaises(ValueError):
            validate_surface(record)

    def test_unknown_finish_raises(self):
        with self.assertRaises(ValueError):
            validate_surface(surface(finish="anodised-matte"))

    def test_reflectance_above_unity_raises(self):
        with self.assertRaises(ValueError):
            validate_surface(surface(specular_reflectance=1.4))

    def test_non_boolean_accessible_raises(self):
        with self.assertRaises(ValueError):
            validate_surface(surface(accessible="yes"))

    def test_zero_spot_diameter_raises(self):
        with self.assertRaises(ValueError):
            validate_surface(surface(spot_diameter_mm=0.0))


class TestSelectTechnique(unittest.TestCase):
    def test_bright_specular_surface_gets_the_grazing_route(self):
        technique, reason = select_technique(surface())
        self.assertEqual(technique, REFLECTION_ABSORPTION)
        self.assertEqual(reason, "specular-substrate-returns-the-beam")

    def test_dark_specular_surface_falls_back_to_diffuse(self):
        technique, reason = select_technique(surface(specular_reflectance=0.20))
        self.assertEqual(technique, DIFFUSE_REFLECTANCE)
        self.assertEqual(reason, "specular-beam-too-weak-for-grazing")

    def test_reflectance_exactly_at_the_floor_keeps_the_grazing_route(self):
        technique, _ = select_technique(
            surface(specular_reflectance=MIN_SPECULAR_REFLECTANCE)
        )
        self.assertEqual(technique, REFLECTION_ABSORPTION)

    def test_diffuse_finish_gets_diffuse_reflectance(self):
        technique, reason = select_technique(
            surface(finish="diffuse", specular_reflectance=0.05)
        )
        self.assertEqual(technique, DIFFUSE_REFLECTANCE)
        self.assertEqual(reason, "scattering-finish-has-no-specular-beam")

    def test_compliant_surface_gets_internal_reflection(self):
        technique, _ = select_technique(
            surface(finish="compliant", specular_reflectance=0.10)
        )
        self.assertEqual(technique, INTERNAL_REFLECTION)

    def test_unreachable_surface_raises(self):
        with self.assertRaises(ValueError):
            select_technique(surface(accessible=False))


class TestIncidenceAngle(unittest.TestCase):
    def test_angle_inside_the_grazing_window_is_returned(self):
        self.assertAlmostEqual(
            validate_incidence_angle(80.0, REFLECTION_ABSORPTION), 80.0, places=9
        )

    def test_angle_below_the_grazing_window_raises(self):
        with self.assertRaises(ValueError):
            validate_incidence_angle(30.0, REFLECTION_ABSORPTION)

    def test_angle_at_the_lower_edge_is_accepted(self):
        self.assertAlmostEqual(
            validate_incidence_angle(GRAZING_MIN_ANGLE_DEG, REFLECTION_ABSORPTION),
            GRAZING_MIN_ANGLE_DEG,
            places=9,
        )

    def test_angle_at_the_upper_edge_is_accepted(self):
        self.assertAlmostEqual(
            validate_incidence_angle(GRAZING_MAX_ANGLE_DEG, REFLECTION_ABSORPTION),
            GRAZING_MAX_ANGLE_DEG,
            places=9,
        )

    def test_angle_of_ninety_degrees_raises(self):
        with self.assertRaises(ValueError):
            validate_incidence_angle(90.0, DIFFUSE_REFLECTANCE)

    def test_unknown_technique_raises(self):
        with self.assertRaises(ValueError):
            validate_incidence_angle(60.0, "transmission")


class TestPathEnhancement(unittest.TestCase):
    def test_double_pass_at_sixty_degrees_is_four(self):
        self.assertAlmostEqual(
            path_enhancement(60.0, REFLECTION_ABSORPTION), 4.0, places=9
        )

    def test_enhancement_grows_towards_grazing(self):
        near = path_enhancement(60.0, REFLECTION_ABSORPTION)
        far = path_enhancement(85.0, REFLECTION_ABSORPTION)
        self.assertGreater(far, near * 2.0)

    def test_enhancement_matches_the_closed_form(self):
        expected = 2.0 / math.cos(math.radians(75.0))
        self.assertAlmostEqual(
            path_enhancement(75.0, REFLECTION_ABSORPTION), expected, places=9
        )

    def test_diffuse_collection_has_no_geometric_factor(self):
        self.assertAlmostEqual(
            path_enhancement(30.0, DIFFUSE_REFLECTANCE), 1.0, places=9
        )

    def test_internal_reflection_has_no_geometric_factor(self):
        self.assertAlmostEqual(
            path_enhancement(45.0, INTERNAL_REFLECTION), 1.0, places=9
        )


class TestNetReflectionAbsorbance(unittest.TestCase):
    def test_reference_is_subtracted(self):
        net = net_reflection_absorbance(0.0250, 0.0050, "alu", "alu")
        self.assertAlmostEqual(net, 0.0200, places=9)

    def test_different_substrate_raises(self):
        with self.assertRaises(ValueError):
            net_reflection_absorbance(0.025, 0.005, "alu", "titanium")

    def test_empty_substrate_name_raises(self):
        with self.assertRaises(ValueError):
            net_reflection_absorbance(0.025, 0.005, "  ", "  ")

    def test_reference_absorbing_more_than_the_sample_raises(self):
        with self.assertRaises(ValueError):
            net_reflection_absorbance(0.005, 0.400, "alu", "alu")

    def test_noise_level_negative_is_floored_at_zero(self):
        net = net_reflection_absorbance(0.010000, 0.010050, "alu", "alu")
        self.assertAlmostEqual(net, 0.0, places=9)


class TestThicknessAndMass(unittest.TestCase):
    def test_thickness_divides_by_absorptivity_and_enhancement(self):
        self.assertAlmostEqual(film_thickness_um(0.02, 0.05, 4.0), 0.1, places=9)

    def test_zero_absorptivity_raises(self):
        with self.assertRaises(ValueError):
            film_thickness_um(0.02, 0.0, 4.0)

    def test_zero_enhancement_raises(self):
        with self.assertRaises(ValueError):
            film_thickness_um(0.02, 0.05, 0.0)

    def test_areal_mass_uses_the_density_conversion(self):
        self.assertAlmostEqual(areal_mass_ug_per_cm2(0.1, 1.0), 10.0, places=9)

    def test_areal_mass_scales_with_density(self):
        self.assertAlmostEqual(areal_mass_ug_per_cm2(0.1, 0.95), 9.5, places=9)

    def test_negative_thickness_raises(self):
        with self.assertRaises(ValueError):
            areal_mass_ug_per_cm2(-0.1, 1.0)


class TestAssessDirectMeasurement(unittest.TestCase):
    def test_nominal_grazing_case(self):
        out = assess_direct_measurement(spec())
        self.assertEqual(out["technique"], REFLECTION_ABSORPTION)
        self.assertAlmostEqual(out["path_enhancement"], 4.0, places=9)
        self.assertAlmostEqual(out["net_absorbance"], 0.02, places=9)
        self.assertAlmostEqual(out["film_thickness_um"], 0.1, places=9)
        self.assertAlmostEqual(out["areal_mass_ug_per_cm2"], 10.0, places=9)
        self.assertTrue(out["acceptable"])

    def test_spot_larger_than_aperture_is_a_finding(self):
        out = assess_direct_measurement(
            spec(surface=surface(spot_diameter_mm=12.0, aperture_diameter_mm=8.0))
        )
        self.assertTrue(any("aperture" in f for f in out["findings"]))
        self.assertFalse(out["acceptable"])

    def test_spot_equal_to_aperture_raises_no_finding(self):
        out = assess_direct_measurement(
            spec(surface=surface(spot_diameter_mm=8.0, aperture_diameter_mm=8.0))
        )
        self.assertEqual(out["findings"], [])

    def test_dark_substrate_records_the_fallback_finding(self):
        out = assess_direct_measurement(
            spec(surface=surface(specular_reflectance=0.20),
                 incidence_angle_deg=30.0)
        )
        self.assertEqual(out["technique"], DIFFUSE_REFLECTANCE)
        self.assertTrue(any("grazing-route floor" in f for f in out["findings"]))

    def test_diffuse_route_warns_the_figure_is_comparative(self):
        out = assess_direct_measurement(
            spec(surface=surface(finish="diffuse", specular_reflectance=0.05),
                 incidence_angle_deg=20.0)
        )
        self.assertTrue(any("comparative figure" in f for f in out["findings"]))

    def test_thick_film_on_the_internal_reflection_route_is_bounded(self):
        out = assess_direct_measurement(
            spec(surface=surface(finish="compliant", specular_reflectance=0.10),
                 incidence_angle_deg=45.0,
                 sample_absorbance=0.505,
                 reference_absorbance=0.005)
        )
        self.assertEqual(out["technique"], INTERNAL_REFLECTION)
        self.assertTrue(out["bounded_lower_limit"])
        self.assertGreater(out["film_thickness_um"], ATR_SAMPLING_DEPTH_UM)

    def test_grazing_angle_outside_the_window_raises(self):
        with self.assertRaises(ValueError):
            assess_direct_measurement(spec(incidence_angle_deg=20.0))

    def test_missing_key_raises(self):
        broken = spec()
        del broken["density_g_per_cm3"]
        with self.assertRaises(ValueError):
            assess_direct_measurement(broken)

    def test_non_mapping_spec_raises(self):
        with self.assertRaises(ValueError):
            assess_direct_measurement(["surface"])

    def test_unreachable_surface_raises_in_the_assessment(self):
        with self.assertRaises(ValueError):
            assess_direct_measurement(spec(surface=surface(accessible=False)))


if __name__ == "__main__":
    unittest.main(verbosity=1)
