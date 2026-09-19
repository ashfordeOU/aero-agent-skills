"""Contract tests for the clause 4.7.5.4.7 gear design logic."""

import math
import unittest

from e3301_gear_design_logic import (
    BENDING_LIFE_EXPONENT,
    CONTACT_LIFE_EXPONENT,
    GEAR_MATERIALS,
    LIFE_REFERENCE_CYCLES,
    MIN_BACKLASH_MM,
    assess_gear_design,
    assess_lubricant,
    backlash_range_mm,
    bending_stress_mpa,
    centre_distance_change_mm,
    contact_stress_mpa,
    elastic_coefficient,
    gear_material,
    lewis_form_factor,
    life_derating_factor,
    lubricant_properties,
    pitch_diameter_mm,
    tangential_force_n,
    validate_positive,
)


def base_spec(**overrides):
    spec = {
        "module_mm": 0.8,
        "pinion_teeth": 20,
        "wheel_teeth": 60,
        "face_width_mm": 6.0,
        "torque_nm": 1.2,
        "pinion_material": "nitrided-steel",
        "wheel_material": "nitrided-steel",
        "lubricant": "mac-grease",
        "nominal_backlash_mm": 0.05,
        "housing_cte": 23.0e-6,
        "assembly_temp_c": 22.0,
        "min_temp_c": -40.0,
        "max_temp_c": 80.0,
        "required_cycles": 2.0e7,
    }
    spec.update(overrides)
    return spec


class ValidationTests(unittest.TestCase):
    def test_positive_value_returned_as_float(self):
        self.assertAlmostEqual(validate_positive("x", 2), 2.0)

    def test_zero_rejected(self):
        with self.assertRaises(ValueError):
            validate_positive("x", 0)

    def test_boolean_rejected(self):
        with self.assertRaises(ValueError):
            validate_positive("x", True)

    def test_nan_rejected(self):
        with self.assertRaises(ValueError):
            validate_positive("x", float("nan"))


class StockTests(unittest.TestCase):
    def test_gear_material_carries_allowables(self):
        self.assertAlmostEqual(
            gear_material("nitrided-steel")["bending_allowable_mpa"], 380.0
        )

    def test_gear_material_record_is_a_copy(self):
        record = gear_material("peek-polymer")
        record["modulus_mpa"] = 1.0
        self.assertAlmostEqual(GEAR_MATERIALS["peek-polymer"]["modulus_mpa"], 3600.0)

    def test_unknown_gear_material_rejected(self):
        with self.assertRaises(ValueError):
            gear_material("driftwood")

    def test_lubricant_carries_a_temperature_range(self):
        props = lubricant_properties("pfpe-grease")
        self.assertLess(props["min_temp_c"], props["max_temp_c"])

    def test_unknown_lubricant_rejected(self):
        with self.assertRaises(ValueError):
            lubricant_properties("olive-oil")


class GeometryTests(unittest.TestCase):
    def test_pitch_diameter_is_module_times_teeth(self):
        self.assertAlmostEqual(pitch_diameter_mm(0.8, 20), 16.0, places=9)

    def test_too_few_teeth_rejected(self):
        with self.assertRaises(ValueError):
            pitch_diameter_mm(0.8, 4)

    def test_non_integer_teeth_rejected(self):
        with self.assertRaises(ValueError):
            pitch_diameter_mm(0.8, 20.5)

    def test_tangential_force_matches_closed_form(self):
        self.assertAlmostEqual(tangential_force_n(1.2, 16.0), 150.0, places=9)

    def test_larger_diameter_lowers_the_tooth_force(self):
        self.assertLess(tangential_force_n(1.2, 32.0), tangential_force_n(1.2, 16.0))


class FormFactorTests(unittest.TestCase):
    def test_tabulated_point_returned_exactly(self):
        self.assertAlmostEqual(lewis_form_factor(20), 0.322)

    def test_interpolates_between_tabulated_points(self):
        value = lewis_form_factor(45)
        self.assertGreater(value, 0.389)
        self.assertLess(value, 0.409)

    def test_form_factor_rises_with_tooth_count(self):
        self.assertGreater(lewis_form_factor(60), lewis_form_factor(17))

    def test_above_the_table_saturates(self):
        self.assertAlmostEqual(lewis_form_factor(400), lewis_form_factor(200))

    def test_undercut_tooth_count_rejected(self):
        with self.assertRaises(ValueError):
            lewis_form_factor(9)


class StressTests(unittest.TestCase):
    def test_lewis_bending_matches_closed_form(self):
        self.assertAlmostEqual(
            bending_stress_mpa(150.0, 6.0, 0.8, 0.322),
            150.0 / (6.0 * 0.8 * 0.322),
            places=9,
        )

    def test_dynamic_factor_raises_the_bending_stress(self):
        plain = bending_stress_mpa(150.0, 6.0, 0.8, 0.322, 1.0)
        dynamic = bending_stress_mpa(150.0, 6.0, 0.8, 0.322, 1.4)
        self.assertAlmostEqual(dynamic, 1.4 * plain, places=9)

    def test_dynamic_factor_below_unity_rejected(self):
        with self.assertRaises(ValueError):
            bending_stress_mpa(150.0, 6.0, 0.8, 0.322, 0.8)

    def test_elastic_coefficient_is_symmetric(self):
        self.assertAlmostEqual(
            elastic_coefficient("nitrided-steel", "aluminium-bronze"),
            elastic_coefficient("aluminium-bronze", "nitrided-steel"),
            places=9,
        )

    def test_soft_pairing_lowers_the_elastic_coefficient(self):
        self.assertLess(
            elastic_coefficient("peek-polymer", "peek-polymer"),
            elastic_coefficient("nitrided-steel", "nitrided-steel"),
        )

    def test_contact_stress_follows_the_square_root_of_force(self):
        low = contact_stress_mpa(100.0, 6.0, 16.0, 0.09, 190.0)
        high = contact_stress_mpa(400.0, 6.0, 16.0, 0.09, 190.0)
        self.assertAlmostEqual(high, 2.0 * low, places=9)

    def test_wider_face_lowers_the_contact_stress(self):
        self.assertLess(
            contact_stress_mpa(150.0, 12.0, 16.0, 0.09, 190.0),
            contact_stress_mpa(150.0, 6.0, 16.0, 0.09, 190.0),
        )


class LifeTests(unittest.TestCase):
    def test_reference_life_gives_unity(self):
        self.assertAlmostEqual(
            life_derating_factor(LIFE_REFERENCE_CYCLES, BENDING_LIFE_EXPONENT), 1.0, places=9
        )

    def test_short_life_gets_no_credit(self):
        self.assertAlmostEqual(
            life_derating_factor(1.0e5, BENDING_LIFE_EXPONENT), 1.0, places=9
        )

    def test_long_life_derates_the_allowable(self):
        self.assertLess(life_derating_factor(1.0e9, BENDING_LIFE_EXPONENT), 1.0)

    def test_contact_derates_faster_than_bending(self):
        self.assertLess(
            life_derating_factor(1.0e9, CONTACT_LIFE_EXPONENT),
            life_derating_factor(1.0e9, BENDING_LIFE_EXPONENT),
        )

    def test_exponent_at_or_above_unity_rejected(self):
        with self.assertRaises(ValueError):
            life_derating_factor(1.0e9, 1.0)


class BacklashTests(unittest.TestCase):
    def test_matched_expansion_leaves_the_centre_distance_alone(self):
        self.assertAlmostEqual(
            centre_distance_change_mm(32.0, 11.5e-6, 11.5e-6, 60.0), 0.0, places=12
        )

    def test_hotter_aluminium_housing_opens_the_centre_distance(self):
        self.assertGreater(centre_distance_change_mm(32.0, 11.5e-6, 23.0e-6, 60.0), 0.0)

    def test_cold_case_closes_the_backlash(self):
        low, high = backlash_range_mm(
            0.05, 32.0, 11.5e-6, 23.0e-6, 22.0, -40.0, 80.0
        )
        self.assertLess(low, 0.05)
        self.assertGreater(high, 0.05)

    def test_matched_materials_hold_the_backlash_constant(self):
        low, high = backlash_range_mm(
            0.05, 32.0, 11.5e-6, 11.5e-6, 22.0, -40.0, 80.0
        )
        self.assertAlmostEqual(low, 0.05, places=12)
        self.assertAlmostEqual(high, 0.05, places=12)

    def test_inverted_temperature_range_rejected(self):
        with self.assertRaises(ValueError):
            backlash_range_mm(0.05, 32.0, 11.5e-6, 23.0e-6, 22.0, 80.0, -40.0)

    def test_pressure_angle_at_or_above_forty_five_rejected(self):
        with self.assertRaises(ValueError):
            backlash_range_mm(0.05, 32.0, 11.5e-6, 23.0e-6, 22.0, -40.0, 80.0, 45.0)

    def test_temperature_below_absolute_zero_rejected(self):
        with self.assertRaises(ValueError):
            backlash_range_mm(0.05, 32.0, 11.5e-6, 23.0e-6, 22.0, -300.0, 80.0)


class LubricantTests(unittest.TestCase):
    def test_compatible_selection_reports_nothing(self):
        self.assertEqual(
            assess_lubricant("mac-grease", "nitrided-steel", -40.0, 80.0, 700.0), []
        )

    def test_cold_case_outside_the_rating_is_reported(self):
        findings = assess_lubricant("mac-grease", "nitrided-steel", -90.0, 80.0, 700.0)
        self.assertTrue(any("cold case" in f for f in findings))

    def test_hot_case_outside_the_rating_is_reported(self):
        findings = assess_lubricant("pfpe-grease", "nitrided-steel", -40.0, 200.0, 700.0)
        self.assertTrue(any("hot case" in f for f in findings))

    def test_contact_stress_past_the_film_credit_is_reported(self):
        findings = assess_lubricant("pfpe-grease", "nitrided-steel", -40.0, 80.0, 1300.0)
        self.assertTrue(any("credited" in f for f in findings))

    def test_excluded_material_pairing_is_reported(self):
        findings = assess_lubricant("mos2-dry-film", "peek-polymer", -40.0, 80.0, 50.0)
        self.assertTrue(any("may not be used" in f for f in findings))

    def test_unlubricated_steel_mesh_is_reported(self):
        findings = assess_lubricant("unlubricated", "aisi-440c", -40.0, 80.0, 300.0)
        self.assertTrue(any("may not be used" in f for f in findings))


class AssessmentTests(unittest.TestCase):
    def test_sound_mesh_reports_no_findings(self):
        result = assess_gear_design(base_spec())
        self.assertTrue(result["compliant"])
        self.assertEqual(result["findings"], [])

    def test_centre_distance_is_the_mean_pitch_radius_sum(self):
        result = assess_gear_design(base_spec())
        self.assertAlmostEqual(result["centre_distance_mm"], 32.0, places=9)

    def test_overloaded_mesh_fails_on_bending(self):
        result = assess_gear_design(base_spec(torque_nm=12.0, face_width_mm=2.0))
        self.assertFalse(result["compliant"])
        self.assertTrue(any("bending" in f for f in result["findings"]))

    def test_polymer_wheel_fails_on_flank_contact(self):
        result = assess_gear_design(
            base_spec(pinion_material="peek-polymer", wheel_material="peek-polymer",
                      lubricant="pfpe-grease")
        )
        self.assertFalse(result["compliant"])
        self.assertTrue(any("flank contact" in f for f in result["findings"]))

    def test_tight_backlash_with_an_aluminium_housing_is_flagged(self):
        result = assess_gear_design(base_spec(nominal_backlash_mm=0.006))
        self.assertFalse(result["compliant"])
        self.assertTrue(any("backlash falls" in f for f in result["findings"]))

    def test_backlash_bound_can_fail_the_hot_case(self):
        result = assess_gear_design(base_spec(max_backlash_mm=0.055))
        self.assertFalse(result["compliant"])
        self.assertTrue(any("opens to" in f for f in result["findings"]))

    def test_backlash_floor_exactly_met_is_accepted(self):
        spec = base_spec()
        probe = assess_gear_design(spec)
        shortfall = probe["backlash_min_mm"] - MIN_BACKLASH_MM
        spec["nominal_backlash_mm"] = spec["nominal_backlash_mm"] - shortfall
        result = assess_gear_design(spec)
        self.assertAlmostEqual(result["backlash_min_mm"], MIN_BACKLASH_MM, places=9)
        self.assertTrue(result["compliant"])

    def test_longer_life_lowers_both_allowables(self):
        short = assess_gear_design(base_spec(required_cycles=1.0e7))
        long_life = assess_gear_design(base_spec(required_cycles=1.0e10))
        self.assertLess(long_life["bending_allowable_mpa"], short["bending_allowable_mpa"])
        self.assertLess(long_life["contact_allowable_mpa"], short["contact_allowable_mpa"])

    def test_lubricant_finding_fails_the_mesh(self):
        result = assess_gear_design(base_spec(lubricant="unlubricated"))
        self.assertFalse(result["compliant"])
        self.assertTrue(result["lubricant_findings"])

    def test_dynamic_factor_raises_both_stresses(self):
        quiet = assess_gear_design(base_spec())
        noisy = assess_gear_design(base_spec(dynamic_factor=1.5))
        self.assertGreater(noisy["bending_stress_mpa"], quiet["bending_stress_mpa"])
        self.assertGreater(noisy["contact_stress_mpa"], quiet["contact_stress_mpa"])

    def test_missing_key_rejected(self):
        spec = base_spec()
        del spec["lubricant"]
        with self.assertRaises(ValueError):
            assess_gear_design(spec)

    def test_non_mapping_spec_rejected(self):
        with self.assertRaises(ValueError):
            assess_gear_design("module_mm")

    def test_unknown_wheel_material_rejected(self):
        with self.assertRaises(ValueError):
            assess_gear_design(base_spec(wheel_material="cheese"))


if __name__ == "__main__":
    unittest.main()
