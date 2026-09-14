"""Contract tests for the clause 8.7.11.2.1 adherence-purpose logic."""

import unittest

from e2008_coverglass_coating_adherence_purpose_logic import (
    ADHERENCE_MARGIN_SHORTFALL,
    DEFAULT_PURPOSE_POLICY,
    EXTENDED_STORAGE,
    HUMIDITY_SOAK,
    PURPOSE_ESTABLISHED,
    RECOGNISED_CONDITIONINGS,
    THERMAL_CYCLING,
    VERIFICATION_MISSEQUENCED,
    VERIFICATION_NOT_PLANNED,
    VERIFICATION_NOT_REQUIRED,
    assess_coating_adherence_purpose,
    charge_control_intact,
    check_follows_conditioning,
    conditioning_inventory,
    interfacial_shear_stress_mpa,
    margin_of_safety,
    retained_transmission,
    transmission_loss,
    validate_purpose_policy,
    verification_required,
)


def _policy(**overrides):
    policy = dict(DEFAULT_PURPOSE_POLICY)
    policy.update(overrides)
    return policy


def _sequence(check_order=3):
    return [
        {"step": HUMIDITY_SOAK, "order": 1},
        {"step": THERMAL_CYCLING, "order": 2},
        {"step": "coating-adherence-check", "order": check_order},
    ]


def _case(**overrides):
    case = {
        "declared_conditionings": [HUMIDITY_SOAK, THERMAL_CYCLING],
        "excursion_c": 120.0,
        "coating_modulus_gpa": 70.0,
        "cte_mismatch_ppm_per_c": 4.0,
        "poisson_ratio": 0.2,
        "interfacial_strength_mpa": 63.0,
        "detached_area_fraction": 0.01,
        "coated_transmission": 0.96,
        "bare_glass_transmission": 0.92,
        "verification_planned": True,
        "sequence": _sequence(),
    }
    case.update(overrides)
    return case


class PolicyTests(unittest.TestCase):
    def test_default_policy_validates(self):
        self.assertIs(
            validate_purpose_policy(DEFAULT_PURPOSE_POLICY), DEFAULT_PURPOSE_POLICY
        )

    def test_non_mapping_policy_rejected(self):
        with self.assertRaises(ValueError):
            validate_purpose_policy("adherence")

    def test_detached_fraction_above_one_rejected(self):
        with self.assertRaises(ValueError):
            validate_purpose_policy(_policy(max_detached_area_fraction=1.5))

    def test_conduction_break_below_the_optical_limit_rejected(self):
        with self.assertRaises(ValueError):
            validate_purpose_policy(_policy(conduction_break_fraction=0.01))

    def test_zero_excursion_threshold_rejected(self):
        with self.assertRaises(ValueError):
            validate_purpose_policy(_policy(min_excursion_c=0.0))


class ShearTests(unittest.TestCase):
    def test_shear_follows_modulus_mismatch_and_excursion(self):
        self.assertAlmostEqual(
            interfacial_shear_stress_mpa(70.0, 4.0, 120.0, 0.2), 42.0, places=9
        )

    def test_a_cooling_excursion_loads_the_interface_the_same_way(self):
        self.assertAlmostEqual(
            interfacial_shear_stress_mpa(70.0, -4.0, 120.0, 0.2),
            interfacial_shear_stress_mpa(70.0, 4.0, 120.0, 0.2),
            places=9,
        )

    def test_a_matched_expansion_pair_loads_nothing(self):
        self.assertAlmostEqual(
            interfacial_shear_stress_mpa(70.0, 0.0, 120.0, 0.2), 0.0, places=12
        )

    def test_wider_excursion_raises_the_shear(self):
        self.assertGreater(
            interfacial_shear_stress_mpa(70.0, 4.0, 240.0, 0.2),
            interfacial_shear_stress_mpa(70.0, 4.0, 120.0, 0.2) + 1.0,
        )

    def test_poisson_ratio_of_one_half_rejected(self):
        with self.assertRaises(ValueError):
            interfacial_shear_stress_mpa(70.0, 4.0, 120.0, 0.5)

    def test_zero_excursion_rejected(self):
        with self.assertRaises(ValueError):
            interfacial_shear_stress_mpa(70.0, 4.0, 0.0, 0.2)

    def test_margin_is_strength_over_shear_less_one(self):
        self.assertAlmostEqual(margin_of_safety(63.0, 42.0), 0.5, places=9)

    def test_strength_equal_to_the_shear_leaves_no_margin(self):
        self.assertAlmostEqual(margin_of_safety(42.0, 42.0), 0.0, places=12)

    def test_zero_applied_shear_rejected(self):
        with self.assertRaises(ValueError):
            margin_of_safety(63.0, 0.0)


class DetachmentCostTests(unittest.TestCase):
    def test_an_intact_coating_retains_its_own_transmission(self):
        self.assertAlmostEqual(
            retained_transmission(0.0, 0.96, 0.92), 0.96, places=12
        )

    def test_a_wholly_detached_coating_leaves_bare_glass(self):
        self.assertAlmostEqual(
            retained_transmission(1.0, 0.96, 0.92), 0.92, places=12
        )

    def test_a_detached_patch_blends_the_two_surfaces(self):
        self.assertAlmostEqual(
            retained_transmission(0.25, 0.96, 0.92), 0.95, places=12
        )

    def test_loss_is_the_gap_from_the_intact_article(self):
        self.assertAlmostEqual(
            transmission_loss(0.25, 0.96, 0.92), 0.01, places=12
        )

    def test_bare_glass_brighter_than_the_coated_face_rejected(self):
        with self.assertRaises(ValueError):
            retained_transmission(0.1, 0.90, 0.96)

    def test_detached_fraction_above_one_rejected(self):
        with self.assertRaises(ValueError):
            retained_transmission(1.5, 0.96, 0.92)

    def test_charge_path_survives_a_small_patch(self):
        self.assertTrue(charge_control_intact(0.29))

    def test_charge_path_breaks_at_the_declared_fraction(self):
        self.assertFalse(charge_control_intact(0.30))


class ConditioningInventoryTests(unittest.TestCase):
    def test_every_recognised_conditioning_maps_to_an_objective(self):
        inventory = conditioning_inventory(list(RECOGNISED_CONDITIONINGS))
        self.assertEqual(len(inventory), len(RECOGNISED_CONDITIONINGS) + 1)

    def test_the_shared_objective_is_appended_once(self):
        inventory = conditioning_inventory([HUMIDITY_SOAK])
        self.assertEqual(inventory[-1][0], "shared")

    def test_an_empty_declaration_maps_to_nothing(self):
        self.assertEqual(conditioning_inventory([]), ())

    def test_a_repeated_conditioning_is_grouped_once(self):
        inventory = conditioning_inventory([HUMIDITY_SOAK, HUMIDITY_SOAK])
        self.assertEqual(len(inventory), 2)

    def test_an_unrecognised_conditioning_is_refused_not_ignored(self):
        with self.assertRaises(ValueError):
            conditioning_inventory([HUMIDITY_SOAK, "shaken-in-a-bag"])

    def test_a_non_sequence_declaration_rejected(self):
        with self.assertRaises(ValueError):
            conditioning_inventory(HUMIDITY_SOAK)


class RequirementTests(unittest.TestCase):
    def test_no_conditioning_means_no_verification(self):
        self.assertFalse(verification_required([], 200.0))

    def test_a_humidity_soak_requires_it_whatever_the_excursion(self):
        self.assertTrue(verification_required([HUMIDITY_SOAK], 1.0))

    def test_storage_alone_requires_it(self):
        self.assertTrue(verification_required([EXTENDED_STORAGE], 1.0))

    def test_cycling_under_the_threshold_does_not_require_it(self):
        self.assertFalse(verification_required([THERMAL_CYCLING], 19.0))

    def test_cycling_exactly_on_the_threshold_requires_it(self):
        self.assertTrue(verification_required([THERMAL_CYCLING], 20.0))


class SequenceTests(unittest.TestCase):
    def test_a_check_after_the_conditioning_follows_it(self):
        follows, check_step, last = check_follows_conditioning(_sequence())
        self.assertTrue(follows)
        self.assertEqual((check_step, last), (3, 2))

    def test_a_check_before_the_conditioning_does_not(self):
        follows, check_step, last = check_follows_conditioning(_sequence(0))
        self.assertFalse(follows)
        self.assertEqual((check_step, last), (0, 2))

    def test_a_sequence_without_a_check_does_not_follow(self):
        follows, check_step, _last = check_follows_conditioning(_sequence()[:2])
        self.assertFalse(follows)
        self.assertIsNone(check_step)

    def test_a_check_with_no_conditioning_before_it_does_not_follow(self):
        follows, _check, last = check_follows_conditioning(
            [{"step": "coating-adherence-check", "order": 1}]
        )
        self.assertFalse(follows)
        self.assertIsNone(last)

    def test_two_steps_at_one_order_rejected(self):
        with self.assertRaises(ValueError):
            check_follows_conditioning(
                [
                    {"step": HUMIDITY_SOAK, "order": 1},
                    {"step": THERMAL_CYCLING, "order": 1},
                ]
            )

    def test_a_repeated_adherence_check_rejected(self):
        with self.assertRaises(ValueError):
            check_follows_conditioning(
                [
                    {"step": "coating-adherence-check", "order": 1},
                    {"step": "coating-adherence-check", "order": 2},
                ]
            )


class VerdictTests(unittest.TestCase):
    def test_a_defensible_case_establishes_the_purpose(self):
        result = assess_coating_adherence_purpose(_case())
        self.assertEqual(result["verdict"], PURPOSE_ESTABLISHED)
        self.assertEqual(result["findings"], [])

    def test_the_derived_numbers_are_reported_on_the_accepted_case(self):
        result = assess_coating_adherence_purpose(_case())
        self.assertAlmostEqual(result["interfacial_shear_mpa"], 42.0, places=9)
        self.assertAlmostEqual(result["margin_of_safety"], 0.5, places=9)
        self.assertAlmostEqual(result["retained_transmission"], 0.9596, places=9)
        self.assertTrue(result["charge_control_intact"])

    def test_no_conditioning_stops_the_run_before_the_shear_is_derived(self):
        result = assess_coating_adherence_purpose(
            _case(declared_conditionings=[], excursion_c=5.0)
        )
        self.assertEqual(result["verdict"], VERIFICATION_NOT_REQUIRED)
        self.assertIsNone(result["interfacial_shear_mpa"])
        self.assertIsNone(result["margin_of_safety"])

    def test_an_unplanned_verification_is_its_own_outcome(self):
        result = assess_coating_adherence_purpose(
            _case(verification_planned=False)
        )
        self.assertEqual(result["verdict"], VERIFICATION_NOT_PLANNED)

    def test_a_check_ahead_of_the_conditioning_is_missequenced(self):
        result = assess_coating_adherence_purpose(_case(sequence=_sequence(0)))
        self.assertEqual(result["verdict"], VERIFICATION_MISSEQUENCED)
        self.assertTrue(any("coater" in f for f in result["findings"]))

    def test_a_missing_check_step_is_missequenced_too(self):
        result = assess_coating_adherence_purpose(_case(sequence=_sequence()[:2]))
        self.assertEqual(result["verdict"], VERIFICATION_MISSEQUENCED)

    def test_a_margin_exactly_on_the_floor_is_accepted(self):
        result = assess_coating_adherence_purpose(
            _case(interfacial_strength_mpa=42.0)
        )
        self.assertEqual(result["verdict"], PURPOSE_ESTABLISHED)
        self.assertAlmostEqual(result["margin_of_safety"], 0.0, places=12)

    def test_a_weak_interface_is_a_shortfall(self):
        result = assess_coating_adherence_purpose(
            _case(interfacial_strength_mpa=21.0)
        )
        self.assertEqual(result["verdict"], ADHERENCE_MARGIN_SHORTFALL)
        self.assertTrue(any("margin of safety" in f for f in result["findings"]))

    def test_an_over_detached_lot_is_a_shortfall(self):
        result = assess_coating_adherence_purpose(
            _case(detached_area_fraction=0.40)
        )
        self.assertEqual(result["verdict"], ADHERENCE_MARGIN_SHORTFALL)
        self.assertFalse(result["charge_control_intact"])

    def test_every_shortfall_is_listed_not_only_the_first(self):
        result = assess_coating_adherence_purpose(
            _case(interfacial_strength_mpa=21.0, detached_area_fraction=0.40)
        )
        self.assertGreaterEqual(len(result["findings"]), 3)

    def test_detachment_exactly_on_the_area_limit_is_accepted(self):
        result = assess_coating_adherence_purpose(
            _case(detached_area_fraction=0.02)
        )
        self.assertEqual(result["verdict"], PURPOSE_ESTABLISHED)

    def test_missing_conditioning_declaration_rejected(self):
        case = _case()
        del case["declared_conditionings"]
        with self.assertRaises(ValueError):
            assess_coating_adherence_purpose(case)

    def test_missing_excursion_rejected(self):
        case = _case()
        del case["excursion_c"]
        with self.assertRaises(ValueError):
            assess_coating_adherence_purpose(case)

    def test_non_mapping_case_rejected(self):
        with self.assertRaises(ValueError):
            assess_coating_adherence_purpose(["declared_conditionings"])


if __name__ == "__main__":
    unittest.main()
