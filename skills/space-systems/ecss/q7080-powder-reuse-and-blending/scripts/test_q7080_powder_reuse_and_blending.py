#!/usr/bin/env python3
"""Contract test for powder reuse and blending control (offline)."""

import copy
import unittest

from q7080_powder_reuse_and_blending_logic import (
    BLEND_ACCEPTED,
    BLEND_ACCEPTED_AFTER_TEST,
    BLEND_REJECTED,
    DEFAULT_REUSE_LIMITS,
    POWDER_TESTS,
    blend_composition,
    exceedances,
    grade_blend,
    manage_powder_reuse,
    required_tests,
    reuse_cycles_after_next_build,
    validate_component,
    validate_reuse_limits,
)

VIRGIN = {
    "lot_id": "virgin-a",
    "mass_kg": 30.0,
    "reuse_cycles": 0,
    "oxygen_ppm": 900.0,
    "psd_d50_um": 34.0,
    "fines_fraction": 0.06,
    "cycles_since_characterisation": 0,
}

USED = {
    "lot_id": "used-b",
    "mass_kg": 70.0,
    "reuse_cycles": 4,
    "oxygen_ppm": 1500.0,
    "psd_d50_um": 37.0,
    "fines_fraction": 0.04,
    "cycles_since_characterisation": 2,
}

ALL_TESTS_DONE = list(POWDER_TESTS)


def _lot(base, **overrides):
    lot = copy.deepcopy(base)
    lot.update(overrides)
    return lot


def _limits(**overrides):
    limits = copy.deepcopy(DEFAULT_REUSE_LIMITS)
    limits.update(overrides)
    return limits


class LimitValidationTests(unittest.TestCase):
    def test_the_default_policy_validates(self):
        self.assertIs(
            validate_reuse_limits(DEFAULT_REUSE_LIMITS), DEFAULT_REUSE_LIMITS
        )

    def test_a_non_mapping_policy_is_rejected(self):
        with self.assertRaises(ValueError):
            validate_reuse_limits("ten cycles")

    def test_a_policy_missing_an_entry_is_rejected(self):
        broken = copy.deepcopy(DEFAULT_REUSE_LIMITS)
        del broken["max_oxygen_ppm"]
        with self.assertRaises(ValueError):
            validate_reuse_limits(broken)

    def test_an_inverted_size_window_is_rejected(self):
        with self.assertRaises(ValueError):
            validate_reuse_limits(_limits(psd_d50_window_um=(45.0, 25.0)))

    def test_a_fractional_cycle_limit_is_rejected(self):
        with self.assertRaises(ValueError):
            validate_reuse_limits(_limits(max_reuse_cycles=10.5))


class ComponentTests(unittest.TestCase):
    def test_a_well_formed_lot_normalizes(self):
        self.assertEqual(validate_component(VIRGIN)["lot_id"], "virgin-a")

    def test_a_lot_without_mass_is_rejected(self):
        with self.assertRaises(ValueError):
            validate_component(_lot(VIRGIN, mass_kg=0.0))

    def test_a_negative_reuse_count_is_rejected(self):
        with self.assertRaises(ValueError):
            validate_component(_lot(VIRGIN, reuse_cycles=-1))

    def test_a_fines_fraction_above_one_is_rejected(self):
        with self.assertRaises(ValueError):
            validate_component(_lot(VIRGIN, fines_fraction=1.4))

    def test_an_unnamed_lot_is_rejected(self):
        with self.assertRaises(ValueError):
            validate_component(_lot(VIRGIN, lot_id="   "))

    def test_atmosphere_exposure_defaults_to_false(self):
        self.assertFalse(validate_component(VIRGIN)["exposed_to_atmosphere"])


class CompositionTests(unittest.TestCase):
    def test_the_blend_mass_is_the_sum_of_its_lots(self):
        self.assertAlmostEqual(
            blend_composition([VIRGIN, USED])["total_mass_kg"], 100.0, places=9
        )

    def test_the_virgin_fraction_is_by_mass(self):
        self.assertAlmostEqual(
            blend_composition([VIRGIN, USED])["virgin_mass_fraction"], 0.30, places=9
        )

    def test_the_oxygen_content_is_mass_weighted(self):
        self.assertAlmostEqual(
            blend_composition([VIRGIN, USED])["mass_weighted_oxygen_ppm"],
            1320.0,
            places=6,
        )

    def test_the_reuse_count_carries_both_the_bulk_and_the_worst_case(self):
        composition = blend_composition([VIRGIN, USED])
        self.assertAlmostEqual(
            composition["mass_weighted_reuse_cycles"], 2.8, places=9
        )
        self.assertEqual(composition["worst_case_reuse_cycles"], 4)

    def test_the_characterisation_clock_takes_the_oldest_lot(self):
        self.assertEqual(
            blend_composition([VIRGIN, USED])["cycles_since_characterisation"], 2
        )

    def test_an_empty_blend_is_rejected(self):
        with self.assertRaises(ValueError):
            blend_composition([])

    def test_a_repeated_lot_identifier_is_rejected(self):
        with self.assertRaises(ValueError):
            blend_composition([VIRGIN, _lot(USED, lot_id="virgin-a")])

    def test_the_blend_order_does_not_change_the_result(self):
        forward = blend_composition([VIRGIN, USED])
        backward = blend_composition([USED, VIRGIN])
        self.assertAlmostEqual(
            forward["mass_weighted_oxygen_ppm"],
            backward["mass_weighted_oxygen_ppm"],
            places=12,
        )
        self.assertEqual(forward["lot_ids"], backward["lot_ids"])

    def test_the_next_build_advances_the_worst_case_count(self):
        self.assertEqual(
            reuse_cycles_after_next_build(blend_composition([VIRGIN, USED])), 5
        )

    def test_a_composition_that_did_not_come_from_the_blend_is_rejected(self):
        with self.assertRaises(ValueError):
            reuse_cycles_after_next_build({"total_mass_kg": 100.0})


class GradingTests(unittest.TestCase):
    def test_a_compliant_blend_has_no_exceedance(self):
        graded = grade_blend(blend_composition([VIRGIN, USED]))
        self.assertEqual(exceedances(graded), ())

    def test_an_oxygen_value_exactly_on_the_limit_is_within_it(self):
        composition = blend_composition(
            [_lot(VIRGIN, oxygen_ppm=1800.0, mass_kg=50.0),
             _lot(USED, oxygen_ppm=1800.0, mass_kg=50.0)]
        )
        self.assertAlmostEqual(
            composition["mass_weighted_oxygen_ppm"], 1800.0, places=9
        )
        self.assertEqual(exceedances(grade_blend(composition)), ())

    def test_an_oxygen_value_above_the_limit_is_an_exceedance(self):
        composition = blend_composition([_lot(USED, oxygen_ppm=2400.0)])
        self.assertIn("mass-weighted-oxygen-ppm", exceedances(grade_blend(composition)))

    def test_a_reuse_count_past_the_limit_is_an_exceedance(self):
        composition = blend_composition([_lot(USED, reuse_cycles=12)])
        self.assertIn("worst-case-reuse-cycles", exceedances(grade_blend(composition)))

    def test_a_virgin_fraction_below_a_declared_floor_is_an_exceedance(self):
        composition = blend_composition([_lot(USED, mass_kg=100.0)])
        graded = grade_blend(composition, _limits(min_virgin_mass_fraction=0.2))
        self.assertIn("virgin-mass-fraction", exceedances(graded))

    def test_a_particle_size_outside_the_window_is_an_exceedance(self):
        composition = blend_composition([_lot(USED, psd_d50_um=18.0)])
        self.assertIn("mass-weighted-d50-um", exceedances(grade_blend(composition)))

    def test_a_fines_fraction_above_the_cap_is_an_exceedance(self):
        composition = blend_composition([_lot(USED, fines_fraction=0.30)])
        self.assertIn(
            "mass-weighted-fines-fraction", exceedances(grade_blend(composition))
        )

    def test_grading_something_that_is_not_a_composition_is_rejected(self):
        with self.assertRaises(ValueError):
            grade_blend({"oxygen": 900.0})


class TestSelectionTests(unittest.TestCase):
    def test_a_blend_of_two_lots_owes_the_blend_test_set(self):
        owed = required_tests(blend_composition([VIRGIN, USED]))
        for name in ("particle-size-distribution", "oxygen-and-nitrogen-chemistry",
                     "flowability"):
            self.assertIn(name, owed)

    def test_a_used_lot_always_owes_a_morphology_check(self):
        self.assertIn("morphology", required_tests(blend_composition([USED])))

    def test_an_untouched_virgin_lot_owes_nothing(self):
        self.assertEqual(required_tests(blend_composition([VIRGIN])), ())

    def test_the_characterisation_interval_pulls_in_the_full_set(self):
        composition = blend_composition(
            [_lot(USED, cycles_since_characterisation=5)]
        )
        self.assertEqual(required_tests(composition), tuple(sorted(POWDER_TESTS)))

    def test_oxygen_near_the_limit_pulls_in_the_chemistry(self):
        composition = blend_composition([_lot(VIRGIN, oxygen_ppm=1750.0)])
        self.assertIn("oxygen-and-nitrogen-chemistry", required_tests(composition))

    def test_atmosphere_exposure_pulls_in_the_moisture_test(self):
        composition = blend_composition(
            [_lot(VIRGIN, exposed_to_atmosphere=True)]
        )
        self.assertIn("moisture", required_tests(composition))


class DispositionTests(unittest.TestCase):
    def test_a_compliant_and_fully_tested_blend_is_accepted(self):
        result = manage_powder_reuse(
            {"components": [VIRGIN, USED], "completed_tests": ALL_TESTS_DONE}
        )
        self.assertEqual(result["disposition"], BLEND_ACCEPTED)

    def test_an_untested_blend_waits_for_its_characterisation(self):
        result = manage_powder_reuse({"components": [VIRGIN, USED]})
        self.assertEqual(result["disposition"], BLEND_ACCEPTED_AFTER_TEST)
        self.assertTrue(result["outstanding_tests"])

    def test_an_exceedance_rejects_the_blend(self):
        result = manage_powder_reuse(
            {"components": [_lot(USED, oxygen_ppm=2400.0)],
             "completed_tests": ALL_TESTS_DONE}
        )
        self.assertEqual(result["disposition"], BLEND_REJECTED)
        self.assertTrue(result["findings"])

    def test_the_last_build_before_the_cycle_limit_is_called_out(self):
        result = manage_powder_reuse(
            {"components": [_lot(USED, reuse_cycles=10)],
             "completed_tests": ALL_TESTS_DONE}
        )
        self.assertEqual(result["reuse_cycles_after_next_build"], 11)
        self.assertTrue(any("last build" in f for f in result["findings"]))

    def test_an_unknown_completed_test_is_rejected(self):
        with self.assertRaises(ValueError):
            manage_powder_reuse(
                {"components": [VIRGIN], "completed_tests": ["taste"]}
            )

    def test_a_non_mapping_case_is_rejected(self):
        with self.assertRaises(ValueError):
            manage_powder_reuse("one drum of virgin powder")

    def test_completed_tests_must_be_a_sequence(self):
        with self.assertRaises(ValueError):
            manage_powder_reuse({"components": [VIRGIN], "completed_tests": 3})


if __name__ == "__main__":
    unittest.main()
