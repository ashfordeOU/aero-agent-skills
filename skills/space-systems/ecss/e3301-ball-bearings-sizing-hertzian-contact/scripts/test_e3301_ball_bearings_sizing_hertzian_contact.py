"""Contract tests for the clause 4.7.5.4.6 ball-bearing sizing logic."""

import math
import unittest

from e3301_ball_bearings_sizing_hertzian_contact_logic import (
    BEARING_MATERIALS,
    DEFAULT_STATIC_LOAD_FACTOR,
    MIN_DESIGN_FACTOR,
    STRIBECK_RADIAL_FACTOR,
    assess_bearing_sizing,
    basic_static_load_rating_n,
    bearing_material,
    design_load_n,
    max_ball_load_n,
    peak_hertzian_stress_mpa,
    static_equivalent_load_n,
    static_safety_factor,
    validate_positive,
)


def base_spec(**overrides):
    spec = {
        "rows": 1,
        "balls_per_row": 12,
        "ball_diameter_mm": 6.0,
        "contact_angle_deg": 15.0,
        "radial_limit_load_n": 400.0,
        "axial_limit_load_n": 250.0,
        "material": "aisi-440c",
    }
    spec.update(overrides)
    return spec


class ValidationTests(unittest.TestCase):
    def test_positive_value_returned_as_float(self):
        self.assertAlmostEqual(validate_positive("x", 5), 5.0)

    def test_negative_rejected(self):
        with self.assertRaises(ValueError):
            validate_positive("x", -1.0)

    def test_boolean_rejected(self):
        with self.assertRaises(ValueError):
            validate_positive("x", False)

    def test_infinite_rejected(self):
        with self.assertRaises(ValueError):
            validate_positive("x", float("inf"))


class MaterialTests(unittest.TestCase):
    def test_known_material_carries_allowable(self):
        self.assertAlmostEqual(
            bearing_material("aisi-52100")["allowable_stress_mpa"], 4200.0
        )

    def test_corrosion_resistant_steel_has_a_lower_allowable(self):
        self.assertLess(
            bearing_material("aisi-440c")["allowable_stress_mpa"],
            bearing_material("aisi-52100")["allowable_stress_mpa"],
        )

    def test_record_is_a_copy(self):
        record = bearing_material("m50")
        record["allowable_stress_mpa"] = 1.0
        self.assertAlmostEqual(BEARING_MATERIALS["m50"]["allowable_stress_mpa"], 4000.0)

    def test_unknown_material_rejected(self):
        with self.assertRaises(ValueError):
            bearing_material("balsa")


class StaticRatingTests(unittest.TestCase):
    def test_rating_matches_the_iso_form(self):
        rating = basic_static_load_rating_n(1, 10, 5.0, 0.0, 12.0)
        self.assertAlmostEqual(rating, 12.0 * 1 * 10 * 25.0, places=9)

    def test_rating_scales_with_the_square_of_ball_diameter(self):
        small = basic_static_load_rating_n(1, 10, 3.0, 0.0)
        large = basic_static_load_rating_n(1, 10, 6.0, 0.0)
        self.assertAlmostEqual(large, 4.0 * small, places=9)

    def test_second_row_doubles_the_rating(self):
        one = basic_static_load_rating_n(1, 10, 5.0, 20.0)
        two = basic_static_load_rating_n(2, 10, 5.0, 20.0)
        self.assertAlmostEqual(two, 2.0 * one, places=9)

    def test_contact_angle_reduces_the_radial_rating(self):
        self.assertLess(
            basic_static_load_rating_n(1, 10, 5.0, 30.0),
            basic_static_load_rating_n(1, 10, 5.0, 0.0),
        )

    def test_default_static_load_factor_value(self):
        self.assertAlmostEqual(DEFAULT_STATIC_LOAD_FACTOR, 12.3)

    def test_zero_balls_rejected(self):
        with self.assertRaises(ValueError):
            basic_static_load_rating_n(1, 0, 5.0, 0.0)

    def test_ninety_degree_contact_angle_rejected(self):
        with self.assertRaises(ValueError):
            basic_static_load_rating_n(1, 10, 5.0, 90.0)

    def test_out_of_range_static_load_factor_rejected(self):
        with self.assertRaises(ValueError):
            basic_static_load_rating_n(1, 10, 5.0, 0.0, 250.0)


class EquivalentLoadTests(unittest.TestCase):
    def test_pure_radial_load_is_its_own_equivalent(self):
        self.assertAlmostEqual(static_equivalent_load_n(1000.0, 0.0), 1000.0)

    def test_axial_component_raises_the_equivalent_load(self):
        self.assertAlmostEqual(static_equivalent_load_n(1000.0, 2000.0), 1600.0, places=9)

    def test_pure_axial_load_uses_the_axial_factor(self):
        self.assertAlmostEqual(static_equivalent_load_n(0.0, 2000.0), 1000.0, places=9)

    def test_unloaded_bearing_rejected(self):
        with self.assertRaises(ValueError):
            static_equivalent_load_n(0.0, 0.0)

    def test_negative_axial_load_rejected(self):
        with self.assertRaises(ValueError):
            static_equivalent_load_n(100.0, -5.0)


class DesignLoadTests(unittest.TestCase):
    def test_minimum_design_factor_value(self):
        self.assertAlmostEqual(MIN_DESIGN_FACTOR, 1.45)

    def test_default_factor_applied(self):
        self.assertAlmostEqual(design_load_n(1000.0), 1450.0, places=9)

    def test_larger_factor_accepted(self):
        self.assertAlmostEqual(design_load_n(1000.0, 2.0), 2000.0, places=9)

    def test_factor_exactly_at_the_floor_accepted(self):
        self.assertAlmostEqual(design_load_n(200.0, MIN_DESIGN_FACTOR), 290.0, places=9)

    def test_factor_below_the_floor_rejected(self):
        with self.assertRaises(ValueError):
            design_load_n(1000.0, 1.25)


class StressAndBallLoadTests(unittest.TestCase):
    def test_stress_at_the_static_rating_is_the_reference(self):
        self.assertAlmostEqual(
            peak_hertzian_stress_mpa(5000.0, 5000.0, 4200.0), 4200.0, places=9
        )

    def test_stress_follows_the_cube_root_of_load(self):
        low = peak_hertzian_stress_mpa(1000.0, 8000.0, 4200.0)
        high = peak_hertzian_stress_mpa(8000.0, 8000.0, 4200.0)
        self.assertAlmostEqual(high, 2.0 * low, places=9)

    def test_stress_below_the_rating_is_below_the_reference(self):
        self.assertLess(peak_hertzian_stress_mpa(500.0, 5000.0, 4200.0), 4200.0)

    def test_zero_rating_rejected(self):
        with self.assertRaises(ValueError):
            peak_hertzian_stress_mpa(500.0, 0.0, 4200.0)

    def test_stribeck_factor_value(self):
        self.assertAlmostEqual(STRIBECK_RADIAL_FACTOR, 5.0)

    def test_most_loaded_ball_matches_the_stribeck_form(self):
        self.assertAlmostEqual(max_ball_load_n(1200.0, 10, 0.0), 600.0, places=9)

    def test_more_balls_share_the_load(self):
        self.assertLess(max_ball_load_n(1200.0, 20, 0.0), max_ball_load_n(1200.0, 10, 0.0))

    def test_safety_factor_is_the_rating_over_the_load(self):
        self.assertAlmostEqual(static_safety_factor(5000.0, 2000.0), 2.5, places=9)


class AssessmentTests(unittest.TestCase):
    def test_well_sized_bearing_reports_no_findings(self):
        result = assess_bearing_sizing(base_spec())
        self.assertTrue(result["compliant"])
        self.assertEqual(result["findings"], [])

    def test_design_load_carries_the_factor(self):
        result = assess_bearing_sizing(base_spec())
        self.assertAlmostEqual(
            result["design_equivalent_load_n"],
            MIN_DESIGN_FACTOR * result["limit_equivalent_load_n"],
            places=9,
        )

    def test_overloaded_bearing_is_flagged(self):
        result = assess_bearing_sizing(
            base_spec(radial_limit_load_n=6000.0, axial_limit_load_n=4000.0)
        )
        self.assertFalse(result["compliant"])
        self.assertTrue(any("Hertzian" in f for f in result["findings"]))

    def test_stress_exactly_at_the_allowable_is_accepted(self):
        spec = base_spec(material="aisi-52100", axial_limit_load_n=0.0)
        probe = assess_bearing_sizing(spec)
        rating = probe["basic_static_load_rating_n"]
        allowable = probe["allowable_stress_mpa"]
        reference = allowable  # aisi-52100 allowable equals its reference stress
        target_design = rating * (allowable / reference) ** 3.0
        spec["radial_limit_load_n"] = target_design / MIN_DESIGN_FACTOR
        result = assess_bearing_sizing(spec)
        self.assertAlmostEqual(
            result["peak_hertzian_stress_mpa"], allowable, places=6
        )
        self.assertTrue(result["compliant"])

    def test_a_larger_design_factor_raises_the_stress(self):
        base = assess_bearing_sizing(base_spec())
        heavy = assess_bearing_sizing(base_spec(design_factor=2.0))
        self.assertGreater(
            heavy["peak_hertzian_stress_mpa"], base["peak_hertzian_stress_mpa"]
        )

    def test_hybrid_ceramic_raises_the_allowable(self):
        steel = assess_bearing_sizing(base_spec(material="aisi-440c"))
        hybrid = assess_bearing_sizing(base_spec(material="silicon-nitride-hybrid"))
        self.assertGreater(hybrid["allowable_stress_mpa"], steel["allowable_stress_mpa"])

    def test_required_safety_factor_can_fail_a_sized_bearing(self):
        result = assess_bearing_sizing(base_spec(required_static_safety_factor=20.0))
        self.assertFalse(result["compliant"])
        self.assertTrue(any("safety factor" in f for f in result["findings"]))

    def test_max_ball_load_reported_for_a_radially_loaded_bearing(self):
        result = assess_bearing_sizing(base_spec())
        self.assertIsNotNone(result["max_ball_load_n"])

    def test_max_ball_load_absent_for_a_purely_axial_bearing(self):
        result = assess_bearing_sizing(
            base_spec(radial_limit_load_n=0.0, axial_limit_load_n=500.0)
        )
        self.assertIsNone(result["max_ball_load_n"])

    def test_design_factor_below_the_floor_rejected(self):
        with self.assertRaises(ValueError):
            assess_bearing_sizing(base_spec(design_factor=1.2))

    def test_missing_key_rejected(self):
        spec = base_spec()
        del spec["material"]
        with self.assertRaises(ValueError):
            assess_bearing_sizing(spec)

    def test_non_mapping_spec_rejected(self):
        with self.assertRaises(ValueError):
            assess_bearing_sizing(("rows", 1))

    def test_more_balls_lower_the_peak_stress(self):
        few = assess_bearing_sizing(base_spec(balls_per_row=8))
        many = assess_bearing_sizing(base_spec(balls_per_row=20))
        self.assertLess(
            many["peak_hertzian_stress_mpa"], few["peak_hertzian_stress_mpa"]
        )

    def test_rating_is_consistent_with_the_standalone_helper(self):
        result = assess_bearing_sizing(base_spec())
        self.assertAlmostEqual(
            result["basic_static_load_rating_n"],
            basic_static_load_rating_n(1, 12, 6.0, 15.0),
            places=9,
        )


if __name__ == "__main__":
    unittest.main()
