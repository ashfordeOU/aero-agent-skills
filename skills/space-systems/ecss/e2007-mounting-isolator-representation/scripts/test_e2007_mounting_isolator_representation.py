#!/usr/bin/env python3
"""Gate 3 contract test for e2007-mounting-isolator-representation.

Offline, deterministic, stdlib unittest only.
"""

import unittest

import e2007_mounting_isolator_representation_logic as logic


def hard_base():
    return {"isolator_count": 0, "stand_off_height_mm": 0.0}


def isolator_base(family="elastomeric", count=4, height=12.0):
    return {
        "isolator_count": count,
        "isolator_family": family,
        "stack_height_mm": height,
    }


def strap(length=60.0, width=20.0, thickness=0.5):
    return {"length_mm": length, "width_mm": width, "thickness_mm": thickness}


class CategorizeMountingBaseTests(unittest.TestCase):
    def test_direct_metal_contact_is_hard_mounted(self):
        self.assertEqual(logic.categorize_mounting_base(hard_base()),
                         "hard-mounted")

    def test_missing_optional_keys_default_to_hard_mounted(self):
        self.assertEqual(logic.categorize_mounting_base({}), "hard-mounted")

    def test_isolator_count_drives_isolator_mounted(self):
        self.assertEqual(logic.categorize_mounting_base(isolator_base()),
                         "isolator-mounted")

    def test_spacers_without_isolators_are_stand_off_mounted(self):
        base = {"isolator_count": 0, "stand_off_height_mm": 6.0}
        self.assertEqual(logic.categorize_mounting_base(base),
                         "stand-off-mounted")

    def test_every_category_is_in_the_declared_tuple(self):
        for base in (hard_base(), isolator_base(),
                     {"stand_off_height_mm": 3.0}):
            self.assertIn(logic.categorize_mounting_base(base),
                          logic.MOUNTING_CATEGORIES)

    def test_non_mapping_record_is_rejected(self):
        with self.assertRaises(ValueError):
            logic.categorize_mounting_base(["isolator_count", 4])

    def test_negative_isolator_count_is_rejected(self):
        with self.assertRaises(ValueError):
            logic.categorize_mounting_base({"isolator_count": -1})

    def test_non_integer_isolator_count_is_rejected(self):
        with self.assertRaises(ValueError):
            logic.categorize_mounting_base({"isolator_count": 2.5})

    def test_isolator_count_without_family_is_rejected(self):
        with self.assertRaises(ValueError):
            logic.categorize_mounting_base({"isolator_count": 4,
                                            "stack_height_mm": 10.0})

    def test_unknown_isolator_family_is_rejected(self):
        base = isolator_base(family="cork-pad")
        with self.assertRaises(ValueError):
            logic.categorize_mounting_base(base)

    def test_family_declared_without_isolators_is_rejected(self):
        with self.assertRaises(ValueError):
            logic.categorize_mounting_base({"isolator_count": 0,
                                            "isolator_family": "wire-rope"})

    def test_isolator_stack_height_is_required(self):
        with self.assertRaises(ValueError):
            logic.categorize_mounting_base({"isolator_count": 4,
                                            "isolator_family": "wire-rope"})

    def test_zero_isolator_stack_height_is_rejected(self):
        with self.assertRaises(ValueError):
            logic.categorize_mounting_base(isolator_base(height=0.0))

    def test_negative_stand_off_height_is_rejected(self):
        with self.assertRaises(ValueError):
            logic.categorize_mounting_base({"stand_off_height_mm": -2.0})


class IsolatorStackTests(unittest.TestCase):
    def test_stack_resistance_falls_with_isolator_count(self):
        single = logic.isolator_stack_resistance("wire-rope", 1)
        quad = logic.isolator_stack_resistance("wire-rope", 4)
        self.assertAlmostEqual(quad, single / 4.0, places=12)

    def test_wire_rope_stack_resistance_value(self):
        self.assertAlmostEqual(
            logic.isolator_stack_resistance("wire-rope", 4), 1.25e-3, places=9
        )

    def test_conducting_family_keeps_a_chassis_path(self):
        self.assertTrue(logic.stack_provides_chassis_path("wire-rope", 4))

    def test_conductive_elastomer_keeps_a_chassis_path(self):
        self.assertTrue(
            logic.stack_provides_chassis_path("conductive-elastomer", 2)
        )

    def test_dielectric_family_leaves_no_chassis_path(self):
        self.assertFalse(logic.stack_provides_chassis_path("elastomeric", 8))
        self.assertFalse(
            logic.stack_provides_chassis_path("dielectric-washer", 8)
        )

    def test_zero_isolator_count_has_no_stack(self):
        with self.assertRaises(ValueError):
            logic.isolator_stack_resistance("wire-rope", 0)

    def test_unknown_family_has_no_stack_resistance(self):
        with self.assertRaises(ValueError):
            logic.isolator_stack_resistance("cork-pad", 4)


class BondingStrapTests(unittest.TestCase):
    def test_resistance_follows_resistivity_length_and_area(self):
        value = logic.bonding_strap_resistance(100.0, 25.0, 0.5)
        expected = 1.72e-8 * 0.1 / (0.025 * 0.0005)
        self.assertAlmostEqual(value, expected, places=12)

    def test_resistance_halves_when_width_doubles(self):
        narrow = logic.bonding_strap_resistance(80.0, 10.0, 0.4)
        wide = logic.bonding_strap_resistance(80.0, 20.0, 0.4)
        self.assertAlmostEqual(wide, narrow / 2.0, places=12)

    def test_aspect_ratio_is_length_over_width(self):
        self.assertAlmostEqual(
            logic.bonding_strap_aspect_ratio(90.0, 30.0), 3.0, places=12
        )

    def test_short_wide_strap_raises_no_finding(self):
        result = logic.check_bonding_strap(strap())
        self.assertEqual(result["findings"], [])
        self.assertLess(result["aspect_ratio"], 5.0)

    def test_long_narrow_strap_is_graded_on_aspect_ratio(self):
        result = logic.check_bonding_strap(strap(length=300.0, width=10.0))
        joined = " ".join(result["findings"])
        self.assertIn("bonding-strap-aspect-ratio-exceeded", joined)

    def test_thin_strap_is_graded_on_resistance(self):
        result = logic.check_bonding_strap(
            strap(length=100.0, width=25.0, thickness=0.0002)
        )
        joined = " ".join(result["findings"])
        self.assertIn("bonding-strap-resistance-exceeded", joined)

    def test_aspect_ratio_exactly_at_the_limit_passes(self):
        result = logic.check_bonding_strap(strap(length=125.0, width=25.0))
        self.assertAlmostEqual(result["aspect_ratio"], 5.0, places=12)
        self.assertEqual(
            [f for f in result["findings"] if "aspect-ratio" in f], []
        )

    def test_zero_width_strap_is_rejected(self):
        with self.assertRaises(ValueError):
            logic.check_bonding_strap(strap(width=0.0))

    def test_negative_thickness_is_rejected(self):
        with self.assertRaises(ValueError):
            logic.bonding_strap_resistance(50.0, 20.0, -0.3)

    def test_non_mapping_strap_is_rejected(self):
        with self.assertRaises(ValueError):
            logic.check_bonding_strap("60x20x0.5")


class StackHeightComparisonTests(unittest.TestCase):
    def test_identical_heights_are_within_tolerance(self):
        result = logic.compare_stack_height(12.0, 12.0)
        self.assertTrue(result["within_tolerance"])
        self.assertAlmostEqual(result["deviation_mm"], 0.0, places=12)

    def test_allowance_scales_with_the_flight_height(self):
        tall = logic.compare_stack_height(40.0, 40.0)
        short = logic.compare_stack_height(4.0, 4.0)
        self.assertAlmostEqual(tall["allowed_mm"], 4.0, places=12)
        self.assertAlmostEqual(short["allowed_mm"], 0.4, places=12)

    def test_deviation_beyond_the_allowance_is_flagged(self):
        result = logic.compare_stack_height(10.0, 13.0)
        self.assertFalse(result["within_tolerance"])
        self.assertAlmostEqual(result["deviation_mm"], 3.0, places=12)

    def test_representation_error_at_the_boundary_is_absorbed(self):
        # 8.91 - 8.1 evaluates a few ULPs above the 0.81 mm allowance while
        # being exactly on the engineering limit; the compliant case must pass.
        result = logic.compare_stack_height(8.1, 8.91, 0.1)
        self.assertGreater(result["deviation_mm"], result["allowed_mm"])
        self.assertTrue(result["within_tolerance"])

    def test_zero_flight_height_is_rejected(self):
        with self.assertRaises(ValueError):
            logic.compare_stack_height(0.0, 1.0)

    def test_tolerance_above_unity_is_rejected(self):
        with self.assertRaises(ValueError):
            logic.compare_stack_height(10.0, 10.0, 1.5)

    def test_zero_tolerance_is_rejected(self):
        with self.assertRaises(ValueError):
            logic.compare_stack_height(10.0, 10.0, 0.0)


class MountingBaseComparisonTests(unittest.TestCase):
    def test_matching_isolator_arrangements_raise_no_finding(self):
        result = logic.compare_mounting_base(isolator_base(), isolator_base())
        self.assertEqual(result["findings"], [])

    def test_hard_mounting_an_isolator_mounted_unit_is_a_mismatch(self):
        result = logic.compare_mounting_base(isolator_base(), hard_base())
        self.assertEqual(len(result["findings"]), 1)
        self.assertIn("mounting-base-category-mismatch", result["findings"][0])

    def test_family_substitution_is_flagged(self):
        result = logic.compare_mounting_base(
            isolator_base(family="wire-rope"),
            isolator_base(family="elastomeric"),
        )
        self.assertIn("isolator-family-mismatch", " ".join(result["findings"]))

    def test_isolator_count_substitution_is_flagged(self):
        result = logic.compare_mounting_base(isolator_base(count=4),
                                             isolator_base(count=3))
        self.assertIn("isolator-count-mismatch", " ".join(result["findings"]))

    def test_stack_height_deviation_is_flagged(self):
        result = logic.compare_mounting_base(isolator_base(height=12.0),
                                             isolator_base(height=18.0))
        self.assertIn("isolator-stack-height-deviation",
                      " ".join(result["findings"]))

    def test_stand_off_height_deviation_is_flagged(self):
        flight = {"stand_off_height_mm": 6.0}
        test = {"stand_off_height_mm": 9.0}
        result = logic.compare_mounting_base(flight, test)
        self.assertIn("stand-off-height-deviation",
                      " ".join(result["findings"]))

    def test_matching_hard_mounts_raise_no_finding(self):
        result = logic.compare_mounting_base(hard_base(), hard_base())
        self.assertEqual(result["findings"], [])


class AssessmentTests(unittest.TestCase):
    def base_setup(self, **overrides):
        setup = {
            "unit_id": "RIU-A",
            "flight_arrangement_known": True,
            "flight_mounting_base": isolator_base(family="wire-rope"),
            "test_mounting_base": isolator_base(family="wire-rope"),
        }
        setup.update(overrides)
        return setup

    def test_conducting_isolator_stack_needs_no_strap(self):
        result = logic.assess_mounting_isolator_representation(self.base_setup())
        self.assertTrue(result["representative"])
        self.assertTrue(result["chassis_path_through_stack"])
        self.assertEqual(result["findings"], [])

    def test_dielectric_stack_without_a_strap_is_flagged(self):
        setup = self.base_setup(
            flight_mounting_base=isolator_base(family="elastomeric"),
            test_mounting_base=isolator_base(family="elastomeric"),
        )
        result = logic.assess_mounting_isolator_representation(setup)
        self.assertFalse(result["representative"])
        self.assertIn("chassis-reference-path-missing",
                      " ".join(result["findings"]))

    def test_dielectric_stack_with_a_sound_strap_passes(self):
        setup = self.base_setup(
            flight_mounting_base=isolator_base(family="elastomeric"),
            test_mounting_base=isolator_base(family="elastomeric"),
            bonding_strap=strap(),
        )
        result = logic.assess_mounting_isolator_representation(setup)
        self.assertTrue(result["representative"])
        self.assertIsNotNone(result["bonding_strap"])

    def test_dielectric_stack_with_an_inductive_strap_is_flagged(self):
        setup = self.base_setup(
            flight_mounting_base=isolator_base(family="elastomeric"),
            test_mounting_base=isolator_base(family="elastomeric"),
            bonding_strap=strap(length=400.0, width=8.0),
        )
        result = logic.assess_mounting_isolator_representation(setup)
        self.assertIn("bonding-strap-aspect-ratio-exceeded",
                      " ".join(result["findings"]))

    def test_unknown_flight_arrangement_is_a_finding_on_its_own(self):
        setup = self.base_setup(flight_arrangement_known=False)
        result = logic.assess_mounting_isolator_representation(setup)
        self.assertFalse(result["representative"])
        self.assertIn("flight-mounting-arrangement-unknown",
                      " ".join(result["findings"]))

    def test_declared_worst_case_bounds_an_unknown_arrangement(self):
        setup = self.base_setup(flight_arrangement_known=False,
                                declared_worst_case=True)
        result = logic.assess_mounting_isolator_representation(setup)
        self.assertTrue(result["representative"])

    def test_hard_mounted_bench_setup_reports_both_categories(self):
        setup = self.base_setup(test_mounting_base=hard_base())
        result = logic.assess_mounting_isolator_representation(setup)
        self.assertEqual(result["flight_category"], "isolator-mounted")
        self.assertEqual(result["test_category"], "hard-mounted")
        self.assertIsNone(result["isolator_stack_resistance_ohm"])
        self.assertFalse(result["representative"])

    def test_stack_resistance_is_reported_for_the_test_arrangement(self):
        result = logic.assess_mounting_isolator_representation(self.base_setup())
        self.assertAlmostEqual(result["isolator_stack_resistance_ohm"],
                               1.25e-3, places=9)

    def test_missing_unit_id_is_rejected(self):
        setup = self.base_setup()
        del setup["unit_id"]
        with self.assertRaises(ValueError):
            logic.assess_mounting_isolator_representation(setup)

    def test_blank_unit_id_is_rejected(self):
        with self.assertRaises(ValueError):
            logic.assess_mounting_isolator_representation(
                self.base_setup(unit_id="   ")
            )

    def test_missing_test_mounting_base_is_rejected(self):
        setup = self.base_setup()
        del setup["test_mounting_base"]
        with self.assertRaises(ValueError):
            logic.assess_mounting_isolator_representation(setup)

    def test_non_mapping_setup_is_rejected(self):
        with self.assertRaises(ValueError):
            logic.assess_mounting_isolator_representation("RIU-A")

    def test_uncategorized_hardware_stops_the_assessment(self):
        setup = self.base_setup(
            test_mounting_base=isolator_base(family="cork-pad")
        )
        with self.assertRaises(ValueError):
            logic.assess_mounting_isolator_representation(setup)


if __name__ == "__main__":
    unittest.main()
