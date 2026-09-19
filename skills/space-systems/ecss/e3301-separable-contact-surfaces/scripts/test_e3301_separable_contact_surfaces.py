"""Contract tests for the clause 4.7.5.4.5 separable-contact-surface logic."""

import math
import unittest

from e3301_separable_contact_surfaces_logic import (
    DEFAULT_LIFE_FACTOR,
    GALVANIC_ALLOWANCE_MV,
    MIN_RESIDUAL_PLATING_UM,
    PLATING_PROPERTIES,
    a_spot_radius_mm,
    assess_separable_contact,
    constriction_resistance_ohm,
    contact_resistance_ohm,
    design_cycles,
    film_resistance_ohm,
    fretting_exposure,
    galvanic_couple_mv,
    plating_properties,
    residual_plating_um,
    sliding_distance_mm,
    validate_positive,
    wear_depth_um,
)


def base_spec(**overrides):
    spec = {
        "normal_force_n": 0.6,
        "wipe_length_mm": 1.2,
        "apparent_area_mm2": 0.05,
        "plating": "hard-gold",
        "mating_plating": "hard-gold",
        "plating_thickness_um": 1.27,
        "required_cycles": 200,
        "resistance_budget_ohm": 0.01,
        "environment": "benign",
    }
    spec.update(overrides)
    return spec


class ValidationTests(unittest.TestCase):
    def test_positive_value_returned_as_float(self):
        self.assertAlmostEqual(validate_positive("x", 3), 3.0)

    def test_zero_rejected_by_default(self):
        with self.assertRaises(ValueError):
            validate_positive("x", 0.0)

    def test_zero_allowed_when_requested(self):
        self.assertAlmostEqual(validate_positive("x", 0.0, allow_zero=True), 0.0)

    def test_boolean_rejected(self):
        with self.assertRaises(ValueError):
            validate_positive("x", True)

    def test_non_finite_rejected(self):
        with self.assertRaises(ValueError):
            validate_positive("x", float("nan"))


class PlatingStockTests(unittest.TestCase):
    def test_known_plating_carries_hardness(self):
        self.assertAlmostEqual(plating_properties("hard-gold")["hardness_mpa"], 1600.0)

    def test_lookup_is_case_insensitive(self):
        self.assertEqual(plating_properties("Hard-Gold"), plating_properties("hard-gold"))

    def test_record_is_a_copy(self):
        record = plating_properties("tin")
        record["hardness_mpa"] = 1.0
        self.assertAlmostEqual(PLATING_PROPERTIES["tin"]["hardness_mpa"], 200.0)

    def test_unknown_plating_rejected(self):
        with self.assertRaises(ValueError):
            plating_properties("unobtainium")

    def test_non_string_plating_rejected(self):
        with self.assertRaises(ValueError):
            plating_properties(7)


class DesignCycleTests(unittest.TestCase):
    def test_default_life_factor_doubles_the_requirement(self):
        self.assertEqual(design_cycles(200), 400)

    def test_default_life_factor_value(self):
        self.assertAlmostEqual(DEFAULT_LIFE_FACTOR, 2.0)

    def test_fractional_product_rounds_up(self):
        self.assertEqual(design_cycles(101, 1.5), 152)

    def test_unit_life_factor_keeps_the_requirement(self):
        self.assertEqual(design_cycles(37, 1.0), 37)

    def test_life_factor_below_one_rejected(self):
        with self.assertRaises(ValueError):
            design_cycles(200, 0.9)

    def test_zero_required_cycles_rejected(self):
        with self.assertRaises(ValueError):
            design_cycles(0)

    def test_non_integer_cycles_rejected(self):
        with self.assertRaises(ValueError):
            design_cycles(12.5)


class SlidingAndWearTests(unittest.TestCase):
    def test_two_wipes_per_cycle(self):
        self.assertAlmostEqual(sliding_distance_mm(1.5, 10), 30.0)

    def test_zero_wipe_rejected(self):
        with self.assertRaises(ValueError):
            sliding_distance_mm(0.0, 10)

    def test_archard_depth_matches_closed_form(self):
        depth = wear_depth_um(2.0, 100.0, 1.0e-4, 1000.0, 0.02)
        self.assertAlmostEqual(depth, 1000.0 * (1.0e-4 * 2.0 * 100.0 / 1000.0) / 0.02, places=9)

    def test_depth_scales_linearly_with_force(self):
        low = wear_depth_um(1.0, 100.0, 1.0e-4, 1000.0, 0.02)
        high = wear_depth_um(3.0, 100.0, 1.0e-4, 1000.0, 0.02)
        self.assertAlmostEqual(high, 3.0 * low, places=9)

    def test_harder_plating_wears_less(self):
        soft = wear_depth_um(1.0, 100.0, 1.0e-4, 700.0, 0.02)
        hard = wear_depth_um(1.0, 100.0, 1.0e-4, 8000.0, 0.02)
        self.assertLess(hard, soft)

    def test_wear_coefficient_of_one_rejected(self):
        with self.assertRaises(ValueError):
            wear_depth_um(1.0, 100.0, 1.0, 1000.0, 0.02)

    def test_residual_never_negative(self):
        self.assertAlmostEqual(residual_plating_um(1.0, 4.0), 0.0)

    def test_residual_subtracts_the_worn_depth(self):
        self.assertAlmostEqual(residual_plating_um(1.27, 0.27), 1.0, places=9)


class ResistanceTests(unittest.TestCase):
    def test_holm_radius_matches_closed_form(self):
        self.assertAlmostEqual(
            a_spot_radius_mm(1.0, 1000.0), math.sqrt(1.0 / (math.pi * 1000.0)), places=12
        )

    def test_radius_grows_with_force(self):
        self.assertGreater(a_spot_radius_mm(4.0, 1000.0), a_spot_radius_mm(1.0, 1000.0))

    def test_constriction_resistance_matches_closed_form(self):
        self.assertAlmostEqual(constriction_resistance_ohm(2.0e-5, 0.01), 1.0e-3, places=12)

    def test_film_term_is_zero_without_a_film(self):
        self.assertAlmostEqual(film_resistance_ohm(0.0, 0.01), 0.0)

    def test_film_term_adds_to_the_constriction_term(self):
        clean = contact_resistance_ohm(0.6, "hard-gold", 0.0)
        filmed = contact_resistance_ohm(0.6, "hard-gold", 1.0e-8)
        self.assertGreater(filmed, clean)

    def test_higher_force_lowers_contact_resistance(self):
        self.assertLess(
            contact_resistance_ohm(2.0, "hard-gold"), contact_resistance_ohm(0.2, "hard-gold")
        )

    def test_negative_film_resistivity_rejected(self):
        with self.assertRaises(ValueError):
            film_resistance_ohm(-1.0, 0.01)


class GalvanicAndFrettingTests(unittest.TestCase):
    def test_identical_plating_is_a_zero_couple(self):
        self.assertAlmostEqual(galvanic_couple_mv("silver", "silver"), 0.0)

    def test_couple_is_symmetric(self):
        self.assertAlmostEqual(
            galvanic_couple_mv("tin", "hard-gold"), galvanic_couple_mv("hard-gold", "tin")
        )

    def test_gold_to_tin_is_a_large_couple(self):
        self.assertAlmostEqual(galvanic_couple_mv("hard-gold", "tin"), 650.0, places=9)

    def test_generous_wipe_is_low_exposure(self):
        self.assertEqual(fretting_exposure(1.5, 400, "hard-gold"), "low")

    def test_short_wipe_and_many_cycles_is_high_exposure(self):
        self.assertEqual(fretting_exposure(0.2, 500, "hard-gold"), "high")

    def test_short_wipe_with_few_cycles_on_hard_plating_is_moderate(self):
        self.assertEqual(fretting_exposure(0.2, 10, "hard-gold"), "moderate")

    def test_soft_plating_with_short_wipe_is_high_exposure(self):
        self.assertEqual(fretting_exposure(0.2, 5, "tin"), "high")

    def test_zero_cycles_rejected_by_exposure(self):
        with self.assertRaises(ValueError):
            fretting_exposure(1.0, 0, "hard-gold")


class AssessmentTests(unittest.TestCase):
    def test_sound_interface_reports_no_findings(self):
        result = assess_separable_contact(base_spec())
        self.assertTrue(result["compliant"])
        self.assertEqual(result["findings"], [])

    def test_design_cycles_carry_the_life_factor(self):
        self.assertEqual(assess_separable_contact(base_spec())["design_cycles"], 400)

    def test_thin_plating_is_flagged(self):
        result = assess_separable_contact(base_spec(plating_thickness_um=0.5))
        self.assertFalse(result["compliant"])
        self.assertTrue(any("residual" in f for f in result["findings"]))

    def test_residual_exactly_on_the_floor_is_accepted(self):
        spec = base_spec()
        probe = assess_separable_contact(spec)
        spec["plating_thickness_um"] = probe["wear_depth_um"] + MIN_RESIDUAL_PLATING_UM
        result = assess_separable_contact(spec)
        self.assertAlmostEqual(
            result["residual_plating_um"], MIN_RESIDUAL_PLATING_UM, places=9
        )
        self.assertTrue(result["compliant"])

    def test_tight_resistance_budget_is_flagged(self):
        result = assess_separable_contact(base_spec(resistance_budget_ohm=1.0e-6))
        self.assertFalse(result["compliant"])
        self.assertTrue(any("resistance" in f for f in result["findings"]))

    def test_gold_against_tin_in_a_harsh_environment_is_flagged(self):
        result = assess_separable_contact(
            base_spec(mating_plating="tin", environment="harsh")
        )
        self.assertFalse(result["compliant"])
        self.assertTrue(any("couple" in f for f in result["findings"]))

    def test_allowance_follows_the_environment(self):
        harsh = assess_separable_contact(base_spec(environment="harsh"))
        controlled = assess_separable_contact(base_spec(environment="controlled"))
        self.assertAlmostEqual(harsh["galvanic_allowance_mv"], GALVANIC_ALLOWANCE_MV["harsh"])
        self.assertGreater(
            controlled["galvanic_allowance_mv"], harsh["galvanic_allowance_mv"]
        )

    def test_short_wipe_interface_is_not_compliant(self):
        result = assess_separable_contact(base_spec(wipe_length_mm=0.15))
        self.assertFalse(result["compliant"])
        self.assertEqual(result["fretting_exposure"], "high")

    def test_wear_scales_with_the_life_factor(self):
        single = assess_separable_contact(base_spec(life_factor=1.0))
        doubled = assess_separable_contact(base_spec(life_factor=2.0))
        self.assertAlmostEqual(
            doubled["wear_depth_um"], 2.0 * single["wear_depth_um"], places=9
        )

    def test_unknown_environment_rejected(self):
        with self.assertRaises(ValueError):
            assess_separable_contact(base_spec(environment="lunar-dust"))

    def test_missing_key_rejected(self):
        spec = base_spec()
        del spec["wipe_length_mm"]
        with self.assertRaises(ValueError):
            assess_separable_contact(spec)

    def test_non_mapping_spec_rejected(self):
        with self.assertRaises(ValueError):
            assess_separable_contact(["normal_force_n"])


if __name__ == "__main__":
    unittest.main()
