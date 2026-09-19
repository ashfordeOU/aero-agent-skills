"""Contract tests for the particle and UV radiation test applicability logic."""

import unittest

from q7006_applicability_and_objectives_logic import (
    OBJECTIVES,
    PARTICLE_SCREENING_FLUENCE,
    PENETRATING_ENERGY_MEV,
    SECONDS_PER_YEAR,
    TEST_LEVEL_FACTOR,
    UV_SCREENING_ESH,
    applicable_agents,
    assess_applicability,
    degradation_properties,
    exposure_regime,
    heritage_findings,
    mission_particle_fluence,
    mission_uv_dose_esh,
    test_level,
    test_objective,
    validate_positive,
)


def base_spec(**overrides):
    """An externally mounted polymeric thermal-control film on a 5-year LEO flight."""
    spec = {
        "location": "external",
        "shielding_mm_al": 0.0,
        "material_category": "polymer",
        "function": "thermal-control",
        "particle_flux_per_cm2_s": 2.0e5,
        "duration_years": 5.0,
        "sun_fraction": 0.6,
        "spectrum_max_mev": 5.0,
    }
    spec.update(overrides)
    return spec


class ValidationTests(unittest.TestCase):
    def test_positive_value_returns_float(self):
        self.assertEqual(validate_positive(3, "x"), 3.0)

    def test_zero_rejected_by_default(self):
        with self.assertRaises(ValueError):
            validate_positive(0.0, "x")

    def test_zero_allowed_when_requested(self):
        self.assertEqual(validate_positive(0, "x", allow_zero=True), 0.0)

    def test_boolean_rejected(self):
        with self.assertRaises(ValueError):
            validate_positive(True, "x")

    def test_non_finite_rejected(self):
        with self.assertRaises(ValueError):
            validate_positive(float("nan"), "x")

    def test_string_rejected(self):
        with self.assertRaises(ValueError):
            validate_positive("3", "x")


class MissionExposureTests(unittest.TestCase):
    def test_fluence_is_flux_times_seconds(self):
        value = mission_particle_fluence(1.0, 1.0)
        self.assertAlmostEqual(value, SECONDS_PER_YEAR, places=9)

    def test_duty_fraction_scales_the_fluence(self):
        full = mission_particle_fluence(10.0, 2.0)
        half = mission_particle_fluence(10.0, 2.0, 0.5)
        self.assertAlmostEqual(half * 2.0, full, places=9)

    def test_zero_flux_gives_zero_fluence(self):
        self.assertAlmostEqual(mission_particle_fluence(0.0, 3.0), 0.0, places=9)

    def test_duty_fraction_above_one_rejected(self):
        with self.assertRaises(ValueError):
            mission_particle_fluence(10.0, 1.0, 1.5)

    def test_negative_duty_fraction_rejected(self):
        with self.assertRaises(ValueError):
            mission_particle_fluence(10.0, 1.0, -0.1)

    def test_uv_dose_of_a_fully_illuminated_year(self):
        self.assertAlmostEqual(
            mission_uv_dose_esh(1.0, 1.0), SECONDS_PER_YEAR / 3600.0, places=9
        )

    def test_uv_intensity_multiplies_the_dose(self):
        one = mission_uv_dose_esh(0.5, 1.0, 1.0)
        three = mission_uv_dose_esh(0.5, 1.0, 3.0)
        self.assertAlmostEqual(three, 3.0 * one, places=9)

    def test_eclipsed_orbit_reduces_the_dose(self):
        self.assertLess(mission_uv_dose_esh(0.6, 1.0), mission_uv_dose_esh(1.0, 1.0))

    def test_zero_duration_rejected(self):
        with self.assertRaises(ValueError):
            mission_uv_dose_esh(0.6, 0.0)


class ExposureRegimeTests(unittest.TestCase):
    def test_bare_external_surface(self):
        self.assertEqual(exposure_regime("external", 0.0), "external-surface")

    def test_covered_external_item_is_shielded(self):
        self.assertEqual(exposure_regime("external", 1.0), "shielded-internal")

    def test_internal_item_is_shielded_even_with_no_cover(self):
        self.assertEqual(exposure_regime("internal", 0.0), "shielded-internal")

    def test_case_and_padding_tolerated(self):
        self.assertEqual(exposure_regime("  External ", 0.0), "external-surface")

    def test_unknown_location_rejected(self):
        with self.assertRaises(ValueError):
            exposure_regime("deployed", 0.0)

    def test_negative_shielding_rejected(self):
        with self.assertRaises(ValueError):
            exposure_regime("external", -1.0)


class ApplicableAgentTests(unittest.TestCase):
    def test_external_polymer_sees_both_agents(self):
        agents = applicable_agents("external-surface", 1.0e12, 5000.0, 5.0)
        self.assertEqual(agents, ("particles", "ultraviolet"))

    def test_shielded_item_never_sees_ultraviolet(self):
        agents = applicable_agents("shielded-internal", 1.0e12, 5000.0, 5.0)
        self.assertEqual(agents, ("particles",))

    def test_shielded_item_below_penetrating_energy_sees_nothing(self):
        agents = applicable_agents(
            "shielded-internal", 1.0e12, 5000.0, PENETRATING_ENERGY_MEV / 2.0
        )
        self.assertEqual(agents, ())

    def test_low_exposure_is_not_proportionate(self):
        agents = applicable_agents(
            "external-surface", PARTICLE_SCREENING_FLUENCE / 10.0, UV_SCREENING_ESH / 10.0, 5.0
        )
        self.assertEqual(agents, ())

    def test_optical_item_is_tested_at_any_exposure(self):
        agents = applicable_agents(
            "external-surface",
            PARTICLE_SCREENING_FLUENCE / 1000.0,
            UV_SCREENING_ESH / 1000.0,
            5.0,
            optically_functional=True,
        )
        self.assertEqual(agents, ("particles", "ultraviolet"))

    def test_metal_structure_is_exempt(self):
        agents = applicable_agents(
            "external-surface", 1.0e14, 50000.0, 5.0, material_category="metal"
        )
        self.assertEqual(agents, ())

    def test_optical_glass_is_not_exempt(self):
        agents = applicable_agents(
            "external-surface",
            1.0e14,
            50000.0,
            5.0,
            optically_functional=True,
            material_category="glass",
        )
        self.assertEqual(agents, ("particles", "ultraviolet"))

    def test_unknown_regime_rejected(self):
        with self.assertRaises(ValueError):
            applicable_agents("orbit", 1.0e12, 5000.0, 5.0)

    def test_unknown_material_category_rejected(self):
        with self.assertRaises(ValueError):
            applicable_agents(
                "external-surface", 1.0e12, 5000.0, 5.0, material_category="unobtainium"
            )


class ObjectiveAndLevelTests(unittest.TestCase):
    def test_no_agents_means_no_campaign(self):
        self.assertEqual(test_objective((), False), "not-applicable")

    def test_model_data_drives_characterization(self):
        self.assertEqual(
            test_objective(("particles",), False, model_data_required=True),
            "characterization",
        )

    def test_accepted_heritage_reduces_to_screening(self):
        self.assertEqual(test_objective(("particles",), True), "screening")

    def test_default_objective_is_qualification(self):
        self.assertEqual(test_objective(("particles",), False), "qualification")

    def test_non_boolean_heritage_flag_rejected(self):
        with self.assertRaises(ValueError):
            test_objective(("particles",), "yes")

    def test_every_objective_has_a_level_factor(self):
        for name in OBJECTIVES:
            self.assertIn(name, TEST_LEVEL_FACTOR)

    def test_qualification_runs_above_the_mission(self):
        self.assertGreater(test_level(100.0, "qualification"), test_level(100.0, "screening"))

    def test_screening_runs_at_the_mission_level(self):
        self.assertAlmostEqual(test_level(1234.5, "screening"), 1234.5, places=9)

    def test_extra_factor_compounds(self):
        self.assertAlmostEqual(
            test_level(100.0, "qualification", 1.5),
            100.0 * TEST_LEVEL_FACTOR["qualification"] * 1.5,
            places=9,
        )

    def test_unknown_objective_rejected(self):
        with self.assertRaises(ValueError):
            test_level(100.0, "demonstration")


class PropertySetTests(unittest.TestCase):
    def test_thermal_control_polymer_properties(self):
        self.assertEqual(
            degradation_properties("polymer", "thermal-control"),
            ("infrared-emittance", "mass-loss", "solar-absorptance"),
        )

    def test_coating_adds_adhesion(self):
        self.assertIn("coating-adhesion", degradation_properties("coating", "optical"))

    def test_structural_composite_reads_mechanical_properties(self):
        props = degradation_properties("composite", "structural")
        self.assertIn("tensile-strength", props)
        self.assertIn("elongation-at-break", props)

    def test_metal_adds_nothing_of_its_own(self):
        self.assertEqual(
            degradation_properties("metal", "electrical"),
            ("dielectric-strength", "surface-resistivity"),
        )

    def test_property_set_is_sorted_and_unique(self):
        props = degradation_properties("adhesive", "sealing")
        self.assertEqual(list(props), sorted(set(props)))

    def test_unknown_function_rejected(self):
        with self.assertRaises(ValueError):
            degradation_properties("polymer", "decorative")


class HeritageTests(unittest.TestCase):
    def _claim(self, **overrides):
        claim = {
            "fluence": 1.0e13,
            "uv_esh": 12000.0,
            "max_energy_mev": 8.0,
            "same_process": True,
            "same_material": True,
        }
        claim.update(overrides)
        return claim

    def test_enveloping_claim_has_no_findings(self):
        self.assertEqual(heritage_findings(self._claim(), 1.0e12, 5000.0, 5.0), [])

    def test_exactly_matching_claim_is_admissible(self):
        claim = self._claim(fluence=1.0e12, uv_esh=5000.0, max_energy_mev=5.0)
        self.assertEqual(heritage_findings(claim, 1.0e12, 5000.0, 5.0), [])

    def test_short_fluence_is_a_finding(self):
        claim = self._claim(fluence=1.0e11)
        self.assertEqual(len(heritage_findings(claim, 1.0e12, 5000.0, 5.0)), 1)

    def test_short_uv_dose_is_a_finding(self):
        claim = self._claim(uv_esh=100.0)
        self.assertTrue(
            any("ultraviolet" in note for note in heritage_findings(claim, 1.0e12, 5000.0, 5.0))
        )

    def test_softer_spectrum_is_a_finding(self):
        claim = self._claim(max_energy_mev=1.0)
        self.assertTrue(
            any("spectrum" in note for note in heritage_findings(claim, 1.0e12, 5000.0, 5.0))
        )

    def test_different_process_is_a_finding(self):
        claim = self._claim(same_process=False)
        self.assertTrue(
            any("process" in note for note in heritage_findings(claim, 1.0e12, 5000.0, 5.0))
        )

    def test_missing_key_rejected(self):
        claim = self._claim()
        del claim["same_material"]
        with self.assertRaises(ValueError):
            heritage_findings(claim, 1.0e12, 5000.0, 5.0)

    def test_non_mapping_claim_rejected(self):
        with self.assertRaises(ValueError):
            heritage_findings(["fluence"], 1.0e12, 5000.0, 5.0)


class AssessApplicabilityTests(unittest.TestCase):
    def test_external_film_needs_a_qualification_campaign(self):
        result = assess_applicability(base_spec())
        self.assertTrue(result["test_required"])
        self.assertEqual(result["objective"], "qualification")
        self.assertEqual(result["agents"], ("particles", "ultraviolet"))

    def test_test_level_is_the_factored_mission_level(self):
        result = assess_applicability(base_spec())
        self.assertAlmostEqual(
            result["test_uv_dose_esh"],
            result["mission_uv_dose_esh"] * TEST_LEVEL_FACTOR["qualification"],
            places=9,
        )

    def test_shielded_item_has_no_ultraviolet_level(self):
        result = assess_applicability(base_spec(location="internal", shielding_mm_al=2.0))
        self.assertAlmostEqual(result["test_uv_dose_esh"], 0.0, places=9)
        self.assertEqual(result["agents"], ("particles",))

    def test_exempt_metal_needs_no_campaign(self):
        result = assess_applicability(base_spec(material_category="metal", function="structural"))
        self.assertFalse(result["test_required"])
        self.assertEqual(result["properties"], ())

    def test_good_heritage_reduces_the_objective(self):
        spec = base_spec(
            heritage={
                "fluence": 1.0e20,
                "uv_esh": 1.0e9,
                "max_energy_mev": 50.0,
                "same_process": True,
                "same_material": True,
            }
        )
        result = assess_applicability(spec)
        self.assertTrue(result["heritage_accepted"])
        self.assertEqual(result["objective"], "screening")
        self.assertEqual(result["findings"], [])

    def test_weak_heritage_is_reported_and_ignored(self):
        spec = base_spec(
            heritage={
                "fluence": 1.0,
                "uv_esh": 1.0,
                "max_energy_mev": 0.5,
                "same_process": False,
                "same_material": True,
            }
        )
        result = assess_applicability(spec)
        self.assertFalse(result["heritage_accepted"])
        self.assertEqual(result["objective"], "qualification")
        self.assertGreaterEqual(len(result["findings"]), 3)

    def test_model_data_request_wins_over_heritage(self):
        spec = base_spec(
            model_data_required=True,
            heritage={
                "fluence": 1.0e20,
                "uv_esh": 1.0e9,
                "max_energy_mev": 50.0,
                "same_process": True,
                "same_material": True,
            },
        )
        self.assertEqual(assess_applicability(spec)["objective"], "characterization")

    def test_missing_key_rejected(self):
        spec = base_spec()
        del spec["function"]
        with self.assertRaises(ValueError):
            assess_applicability(spec)

    def test_non_mapping_spec_rejected(self):
        with self.assertRaises(ValueError):
            assess_applicability(["location"])

    def test_optical_function_is_detected_without_an_explicit_flag(self):
        spec = base_spec(
            function="optical",
            material_category="glass",
            particle_flux_per_cm2_s=1.0,
            sun_fraction=0.001,
            duration_years=0.01,
        )
        result = assess_applicability(spec)
        self.assertTrue(result["test_required"])


if __name__ == "__main__":
    unittest.main()
