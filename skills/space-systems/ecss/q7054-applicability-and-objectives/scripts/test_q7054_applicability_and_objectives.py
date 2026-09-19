"""Contract tests for the ultracleaning applicability and objectives logic."""

import unittest

from q7054_applicability_and_objectives_logic import (
    BOTH_DRIVEN,
    MOLECULAR_DRIVEN,
    PARTICULATE_DRIVEN,
    STANDARD_NVR_MG_PER_01M2,
    STANDARD_PARTICULATE_LEVEL,
    STANDARD_SUFFICIENT,
    assess_ultracleaning_applicability,
    nearest_ladder_level,
    particles_per_01m2,
    required_nvr_class,
    required_particulate_level,
    resolve_allowances,
    ultracleaning_objective,
)


def base_case(**overrides):
    """A precision mechanism mounted inside a vented electronics enclosure."""
    case = {
        "item": "bearing cartridge",
        "function_category": "precision-mechanism",
        "exposure_environment": "vented-enclosure",
    }
    case.update(overrides)
    return case


class ParticleDistributionTests(unittest.TestCase):
    def test_count_at_the_level_itself_is_one_particle(self):
        self.assertAlmostEqual(particles_per_01m2(100.0, 100.0), 1.0, places=9)

    def test_count_rises_as_the_reference_size_falls(self):
        coarse = particles_per_01m2(300.0, 100.0)
        fine = particles_per_01m2(300.0, 25.0)
        self.assertGreater(fine, coarse)

    def test_a_size_above_the_level_is_rejected(self):
        with self.assertRaises(ValueError):
            particles_per_01m2(100.0, 250.0)

    def test_non_positive_level_rejected(self):
        with self.assertRaises(ValueError):
            particles_per_01m2(0.0, 5.0)

    def test_non_numeric_size_rejected(self):
        with self.assertRaises(ValueError):
            particles_per_01m2(100.0, "5")

    def test_level_and_count_round_trip(self):
        count = particles_per_01m2(100.0, 5.0)
        self.assertAlmostEqual(
            required_particulate_level(5.0, count), 100.0, places=6
        )


class RequiredLevelTests(unittest.TestCase):
    def test_tight_optical_allowance_lands_well_inside_the_baseline(self):
        level = required_particulate_level(5.0, 60.0)
        self.assertLess(level, STANDARD_PARTICULATE_LEVEL)

    def test_loose_structural_allowance_lands_outside_the_baseline(self):
        level = required_particulate_level(100.0, 9000.0)
        self.assertGreater(level, STANDARD_PARTICULATE_LEVEL)

    def test_allowance_below_one_particle_is_rejected(self):
        with self.assertRaises(ValueError):
            required_particulate_level(5.0, 0.4)

    def test_negative_allowance_rejected(self):
        with self.assertRaises(ValueError):
            required_particulate_level(5.0, -10.0)

    def test_nearest_rung_never_exceeds_the_computed_level(self):
        level = required_particulate_level(25.0, 900.0)
        self.assertLessEqual(nearest_ladder_level(level), level)

    def test_level_below_the_tightest_rung_is_rejected(self):
        with self.assertRaises(ValueError):
            nearest_ladder_level(10.0)

    def test_a_level_exactly_on_a_rung_returns_that_rung(self):
        self.assertAlmostEqual(nearest_ladder_level(300.0), 300.0, places=9)


class ResidueClassTests(unittest.TestCase):
    def test_exact_ladder_value_returns_that_class(self):
        self.assertEqual(required_nvr_class(0.02), "A/50")

    def test_allowance_between_rungs_takes_the_tighter_rung(self):
        self.assertEqual(required_nvr_class(0.15), "A/10")

    def test_baseline_allowance_is_the_b_class(self):
        self.assertEqual(required_nvr_class(STANDARD_NVR_MG_PER_01M2), "B")

    def test_allowance_below_the_tightest_class_is_rejected(self):
        with self.assertRaises(ValueError):
            required_nvr_class(0.005)

    def test_zero_allowance_rejected(self):
        with self.assertRaises(ValueError):
            required_nvr_class(0.0)


class ObjectiveTests(unittest.TestCase):
    def test_both_ladders_beyond_the_baseline(self):
        self.assertEqual(ultracleaning_objective(100.0, 0.1), BOTH_DRIVEN)

    def test_particulate_only(self):
        self.assertEqual(ultracleaning_objective(100.0, 3.0), PARTICULATE_DRIVEN)

    def test_molecular_only(self):
        self.assertEqual(ultracleaning_objective(750.0, 0.1), MOLECULAR_DRIVEN)

    def test_neither_ladder_beyond_the_baseline(self):
        self.assertEqual(ultracleaning_objective(750.0, 3.0), STANDARD_SUFFICIENT)

    def test_a_value_exactly_on_the_baseline_is_not_ultraclean(self):
        self.assertEqual(
            ultracleaning_objective(
                STANDARD_PARTICULATE_LEVEL, STANDARD_NVR_MG_PER_01M2
            ),
            STANDARD_SUFFICIENT,
        )


class AllowanceResolutionTests(unittest.TestCase):
    def test_function_default_is_recorded_as_such(self):
        self.assertEqual(
            resolve_allowances(base_case())["allowance_source"], "function-default"
        )

    def test_a_stated_allowance_overrides_the_default(self):
        resolved = resolve_allowances(base_case(max_nvr_mg_per_01m2=0.05))
        self.assertEqual(resolved["allowance_source"], "case-stated")

    def test_sealed_enclosure_relaxes_the_allowance(self):
        vented = resolve_allowances(base_case())
        sealed = resolve_allowances(base_case(exposure_environment="sealed-enclosure"))
        self.assertGreater(
            sealed["max_nvr_mg_per_01m2"], vented["max_nvr_mg_per_01m2"]
        )

    def test_unknown_function_category_rejected(self):
        with self.assertRaises(ValueError):
            resolve_allowances(base_case(function_category="payload"))

    def test_unknown_environment_rejected(self):
        with self.assertRaises(ValueError):
            resolve_allowances(base_case(exposure_environment="hangar"))

    def test_non_mapping_case_rejected(self):
        with self.assertRaises(ValueError):
            resolve_allowances(["precision-mechanism"])


class ApplicabilityAssessmentTests(unittest.TestCase):
    def test_cryogenic_optics_owes_ultracleaning_on_both_ladders(self):
        result = assess_ultracleaning_applicability(
            base_case(
                function_category="cryogenic-optics",
                exposure_environment="on-orbit-exposed",
            )
        )
        self.assertTrue(result["ultracleaning_required"])
        self.assertEqual(result["objective"], BOTH_DRIVEN)

    def test_plain_structure_does_not_owe_ultracleaning(self):
        result = assess_ultracleaning_applicability(
            base_case(
                function_category="structure",
                exposure_environment="on-orbit-exposed",
            )
        )
        self.assertFalse(result["ultracleaning_required"])
        self.assertEqual(result["verification_methods"], [])

    def test_verification_follows_the_objective(self):
        result = assess_ultracleaning_applicability(
            base_case(
                function_category="thermal-control-surface",
                exposure_environment="on-orbit-exposed",
            )
        )
        self.assertEqual(result["objective"], PARTICULATE_DRIVEN)
        self.assertIn("particle-count-or-obscuration", result["verification_methods"])
        self.assertNotIn(
            "solvent-rinse-residue-weighing", result["verification_methods"]
        )

    def test_molecular_driven_item_warns_against_particle_only_verification(self):
        result = assess_ultracleaning_applicability(
            base_case(
                function_category="structure",
                exposure_environment="on-orbit-exposed",
                max_nvr_mg_per_01m2=0.1,
            )
        )
        self.assertEqual(result["objective"], MOLECULAR_DRIVEN)
        self.assertTrue(
            any("wrong quantity" in f for f in result["findings"])
        )

    def test_default_allowance_raises_a_confirmation_finding(self):
        result = assess_ultracleaning_applicability(base_case())
        self.assertTrue(any("owes confirmation" in f for f in result["findings"]))

    def test_relaxation_is_reported_as_a_finding(self):
        result = assess_ultracleaning_applicability(
            base_case(exposure_environment="sealed-enclosure")
        )
        self.assertTrue(any("relaxed by" in f for f in result["findings"]))

    def test_ladder_level_travels_with_the_assessment(self):
        result = assess_ultracleaning_applicability(
            base_case(exposure_environment="on-orbit-exposed")
        )
        self.assertLessEqual(
            result["ladder_particulate_level_um"],
            result["required_particulate_level_um"],
        )

    def test_residue_class_travels_with_the_assessment(self):
        result = assess_ultracleaning_applicability(
            base_case(
                function_category="oxygen-propulsion",
                exposure_environment="on-orbit-exposed",
            )
        )
        self.assertEqual(result["required_nvr_class"], "A/5")


if __name__ == "__main__":
    unittest.main()
