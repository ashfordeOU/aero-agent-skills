"""Contract tests for the clause 12.6.11.2.1 displacement damage purpose logic."""

import unittest

from e2008_displacement_damage_test_purpose_logic import (
    DEFAULT_DISPLACEMENT_POLICY,
    EXPOSURE_NOT_REQUIRED,
    EXPOSURE_REQUIRED_PLAN_ACCEPTED,
    EXPOSURE_REQUIRED_PLAN_MISSING,
    EXPOSURE_REQUIRED_PLAN_SHORT,
    MAJORITY_CARRIER,
    MINORITY_CARRIER,
    assess_displacement_damage_purpose,
    assess_sensitivity,
    base_transport_ratio,
    degraded_lifetime_s,
    diffusion_length_um,
    displacement_damage_dose,
    equivalent_fluence,
    lifetime_retention,
    required_test_fluence,
    validate_displacement_policy,
    validate_exposure_plan,
    validate_mission_environment,
    validate_technology_profile,
)

ROBUST_DIODE = {
    "technology": "silicon planar blocking diode, wide-base",
    "carrier_type": MINORITY_CARRIER,
    "base_lifetime_s": 1.0e-5,
    "damage_constant_cm2_per_s": 2.0e-8,
    "diffusivity_cm2_per_s": 12.0,
    "base_width_um": 20.0,
}

FRAGILE_DIODE = dict(ROBUST_DIODE, damage_constant_cm2_per_s=5.0e-7)

SWITCHING_PART = dict(
    ROBUST_DIODE,
    technology="unipolar switching element",
    carrier_type=MAJORITY_CARRIER,
    damage_constant_cm2_per_s=5.0e-7,
)

MISSION = {
    "end_of_life_fluence_per_cm2": 3.0e12,
    "niel_mev_cm2_per_g": 2.0e-3,
}

PLAN = {
    "particle": "ten megaelectronvolt protons",
    "planned_fluence_per_cm2": 5.0e12,
    "niel_mev_cm2_per_g": 2.0e-3,
    "sample_count": 8,
}


def _policy(**overrides):
    policy = dict(DEFAULT_DISPLACEMENT_POLICY)
    policy.update(overrides)
    return policy


def _profile(**overrides):
    profile = dict(ROBUST_DIODE)
    profile.update(overrides)
    return profile


def _plan(**overrides):
    plan = dict(PLAN)
    plan.update(overrides)
    return plan


def _case(technology=None, plan=PLAN, mission=None):
    case = {
        "technology": dict(technology if technology is not None else FRAGILE_DIODE),
        "mission": dict(mission if mission is not None else MISSION),
    }
    if plan is not None:
        case["plan"] = dict(plan)
    return case


class PolicyValidationTests(unittest.TestCase):
    def test_default_policy_validates(self):
        self.assertIs(
            validate_displacement_policy(DEFAULT_DISPLACEMENT_POLICY),
            DEFAULT_DISPLACEMENT_POLICY,
        )

    def test_non_mapping_policy_rejected(self):
        with self.assertRaises(ValueError):
            validate_displacement_policy("niel")

    def test_a_transport_margin_below_one_rejected(self):
        with self.assertRaises(ValueError):
            validate_displacement_policy(_policy(base_transport_margin=0.5))

    def test_a_test_margin_factor_below_one_rejected(self):
        with self.assertRaises(ValueError):
            validate_displacement_policy(_policy(test_fluence_margin_factor=0.8))

    def test_a_retention_floor_above_one_rejected(self):
        with self.assertRaises(ValueError):
            validate_displacement_policy(_policy(min_lifetime_retention=1.4))

    def test_a_zero_sample_floor_rejected(self):
        with self.assertRaises(ValueError):
            validate_displacement_policy(_policy(min_sample_count=0))


class InputValidationTests(unittest.TestCase):
    def test_an_unknown_carrier_type_rejected(self):
        with self.assertRaises(ValueError):
            validate_technology_profile(_profile(carrier_type="ambipolar"))

    def test_a_zero_base_width_rejected(self):
        with self.assertRaises(ValueError):
            validate_technology_profile(_profile(base_width_um=0.0))

    def test_a_negative_base_lifetime_rejected(self):
        with self.assertRaises(ValueError):
            validate_technology_profile(_profile(base_lifetime_s=-1.0e-5))

    def test_an_unnamed_technology_rejected(self):
        with self.assertRaises(ValueError):
            validate_technology_profile(_profile(technology="  "))

    def test_a_mission_without_an_end_of_life_fluence_rejected(self):
        with self.assertRaises(ValueError):
            validate_mission_environment({"niel_mev_cm2_per_g": 2.0e-3})

    def test_a_plan_without_a_named_particle_rejected(self):
        with self.assertRaises(ValueError):
            validate_exposure_plan(_plan(particle=""))

    def test_a_boolean_sample_count_rejected(self):
        with self.assertRaises(ValueError):
            validate_exposure_plan(_plan(sample_count=True))

    def test_a_zero_reference_niel_rejected(self):
        with self.assertRaises(ValueError):
            equivalent_fluence(1.0e12, 2.0e-3, 0.0)

    def test_a_zero_lifetime_has_no_diffusion_length(self):
        with self.assertRaises(ValueError):
            diffusion_length_um(12.0, 0.0)


class PhysicsTests(unittest.TestCase):
    def test_damage_dose_is_fluence_times_niel(self):
        dose = displacement_damage_dose(3.0e12, 2.0e-3)
        self.assertAlmostEqual(dose / 6.0e9, 1.0, places=9)

    def test_an_unirradiated_part_takes_no_damage_dose(self):
        self.assertAlmostEqual(displacement_damage_dose(0.0, 2.0e-3), 0.0, places=12)

    def test_a_fluence_at_the_reference_niel_is_its_own_equivalent(self):
        self.assertAlmostEqual(
            equivalent_fluence(3.0e12, 2.0e-3, 2.0e-3) / 3.0e12, 1.0, places=9
        )

    def test_a_harder_particle_is_worth_more_equivalent_fluence(self):
        harder = equivalent_fluence(3.0e12, 4.0e-3, 2.0e-3)
        self.assertAlmostEqual(harder / 6.0e12, 1.0, places=9)

    def test_zero_fluence_leaves_the_starting_lifetime(self):
        self.assertAlmostEqual(
            degraded_lifetime_s(1.0e-5, 2.0e-8, 0.0), 1.0e-5, places=12
        )

    def test_the_messenger_spratt_law_adds_damage_in_reciprocal_lifetime(self):
        self.assertAlmostEqual(
            degraded_lifetime_s(1.0e-5, 2.0e-8, 3.0e12), 6.25e-6, places=12
        )

    def test_retention_is_the_share_of_lifetime_left(self):
        self.assertAlmostEqual(
            lifetime_retention(1.0e-5, 2.0e-8, 3.0e12), 0.625, places=9
        )

    def test_an_unirradiated_part_retains_all_of_its_lifetime(self):
        self.assertAlmostEqual(lifetime_retention(1.0e-5, 2.0e-8, 0.0), 1.0, places=9)

    def test_diffusion_length_is_the_root_of_diffusivity_times_lifetime(self):
        self.assertAlmostEqual(
            diffusion_length_um(12.0, 1.0e-5), 109.544511501, places=6
        )

    def test_a_shorter_lifetime_shortens_the_diffusion_length(self):
        self.assertLess(
            diffusion_length_um(12.0, 6.25e-7), diffusion_length_um(12.0, 1.0e-5)
        )

    def test_the_transport_ratio_counts_base_widths_of_diffusion_length(self):
        self.assertAlmostEqual(
            base_transport_ratio(ROBUST_DIODE, 3.0e12), 4.330127019, places=6
        )


class SensitivityTests(unittest.TestCase):
    def test_a_majority_carrier_part_is_not_sensitive(self):
        outcome = assess_sensitivity(SWITCHING_PART, MISSION)
        self.assertFalse(outcome["sensitive"])
        self.assertIsNone(outcome["lifetime_retention"])

    def test_a_majority_carrier_part_says_why_it_is_exempt(self):
        outcome = assess_sensitivity(SWITCHING_PART, MISSION)
        self.assertTrue(any("majority carriers" in r for r in outcome["reasons"]))

    def test_a_robust_minority_carrier_part_is_not_sensitive(self):
        outcome = assess_sensitivity(ROBUST_DIODE, MISSION)
        self.assertFalse(outcome["sensitive"])
        self.assertAlmostEqual(outcome["lifetime_retention"], 0.625, places=9)

    def test_a_fragile_minority_carrier_part_is_sensitive(self):
        outcome = assess_sensitivity(FRAGILE_DIODE, MISSION)
        self.assertTrue(outcome["sensitive"])
        self.assertAlmostEqual(outcome["lifetime_retention"], 0.0625, places=9)

    def test_a_lost_diffusion_length_is_named_on_its_own(self):
        outcome = assess_sensitivity(FRAGILE_DIODE, MISSION)
        self.assertTrue(any("diffusion length" in r for r in outcome["reasons"]))

    def test_the_two_sensitivity_criteria_fail_independently(self):
        outcome = assess_sensitivity(
            dict(FRAGILE_DIODE, base_width_um=2.0), MISSION
        )
        self.assertTrue(outcome["sensitive"])
        self.assertFalse(any("diffusion length" in r for r in outcome["reasons"]))
        self.assertTrue(
            any("minority-carrier lifetime" in r for r in outcome["reasons"])
        )

    def test_a_retention_floor_on_its_bound_does_not_call_the_part_sensitive(self):
        policy = _policy(min_lifetime_retention=0.625, base_transport_margin=4.0)
        outcome = assess_sensitivity(ROBUST_DIODE, MISSION, policy)
        self.assertFalse(outcome["sensitive"])

    def test_the_damage_dose_is_reported_whatever_the_verdict(self):
        outcome = assess_sensitivity(ROBUST_DIODE, MISSION)
        self.assertAlmostEqual(
            outcome["displacement_damage_dose_mev_per_g"] / 6.0e9, 1.0, places=9
        )


class PlanAdequacyTests(unittest.TestCase):
    def test_the_required_fluence_carries_the_declared_margin(self):
        self.assertAlmostEqual(
            required_test_fluence(MISSION) / 4.5e12, 1.0, places=9
        )

    def test_an_exempt_technology_owes_no_exposure(self):
        outcome = assess_displacement_damage_purpose(_case(SWITCHING_PART, plan=None))
        self.assertEqual(outcome["verdict"], EXPOSURE_NOT_REQUIRED)

    def test_a_sensitive_technology_with_no_plan_is_flagged(self):
        outcome = assess_displacement_damage_purpose(_case(FRAGILE_DIODE, plan=None))
        self.assertEqual(outcome["verdict"], EXPOSURE_REQUIRED_PLAN_MISSING)

    def test_an_adequate_plan_is_accepted(self):
        outcome = assess_displacement_damage_purpose(_case())
        self.assertEqual(outcome["verdict"], EXPOSURE_REQUIRED_PLAN_ACCEPTED)
        self.assertFalse(any("the plan carries" in t for t in outcome["findings"]))

    def test_a_plan_exactly_on_the_required_fluence_is_accepted(self):
        outcome = assess_displacement_damage_purpose(
            _case(plan=_plan(planned_fluence_per_cm2=4.5e12))
        )
        self.assertEqual(outcome["verdict"], EXPOSURE_REQUIRED_PLAN_ACCEPTED)

    def test_a_plan_short_of_the_end_of_life_point_is_refused(self):
        outcome = assess_displacement_damage_purpose(
            _case(plan=_plan(planned_fluence_per_cm2=1.0e12))
        )
        self.assertEqual(outcome["verdict"], EXPOSURE_REQUIRED_PLAN_SHORT)

    def test_a_softer_test_particle_needs_more_of_it(self):
        outcome = assess_displacement_damage_purpose(
            _case(plan=_plan(planned_fluence_per_cm2=5.0e12, niel_mev_cm2_per_g=1.0e-3))
        )
        self.assertEqual(outcome["verdict"], EXPOSURE_REQUIRED_PLAN_SHORT)

    def test_a_harder_test_particle_needs_less_of_it(self):
        outcome = assess_displacement_damage_purpose(
            _case(plan=_plan(planned_fluence_per_cm2=2.5e12, niel_mev_cm2_per_g=4.0e-3))
        )
        self.assertEqual(outcome["verdict"], EXPOSURE_REQUIRED_PLAN_ACCEPTED)

    def test_too_few_parts_is_its_own_finding(self):
        outcome = assess_displacement_damage_purpose(
            _case(plan=_plan(sample_count=2))
        )
        self.assertEqual(outcome["verdict"], EXPOSURE_REQUIRED_PLAN_SHORT)
        self.assertTrue(any("part(s)" in text for text in outcome["findings"]))

    def test_both_shortfalls_are_reported_not_only_the_first(self):
        outcome = assess_displacement_damage_purpose(
            _case(plan=_plan(planned_fluence_per_cm2=1.0e12, sample_count=1))
        )
        self.assertGreaterEqual(len(outcome["findings"]), 3)

    def test_a_case_without_a_technology_is_refused(self):
        with self.assertRaises(ValueError):
            assess_displacement_damage_purpose({"mission": dict(MISSION)})

    def test_a_case_without_a_mission_is_refused(self):
        with self.assertRaises(ValueError):
            assess_displacement_damage_purpose({"technology": dict(FRAGILE_DIODE)})


if __name__ == "__main__":
    unittest.main()
