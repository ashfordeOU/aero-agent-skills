"""Contract tests for the clause 4.4.1 feasibility-phase radiation logic."""

import unittest

from q6015_feasibility_phase_rha_activities_logic import (
    ENVIRONMENT_COMPONENTS,
    FEASIBILITY_DELIVERABLES,
    ORBIT_REGIMES,
    REFERENCE_DOSE_RATE_KRAD_PER_YEAR,
    SEE_LET_THRESHOLD_MEV_CM2_MG,
    assess_feasibility_phase,
    categorize_orbit_regime,
    environment_components,
    mission_dose_krad,
    missing_feasibility_deliverables,
    preliminary_tid_requirement_krad,
    reference_dose_rate,
    see_let_threshold,
    solar_activity_weight,
    validate_orbit,
)

ALL_DELIVERABLES = list(FEASIBILITY_DELIVERABLES)


class OrbitValidationTests(unittest.TestCase):
    def test_valid_orbit_returns_floats(self):
        self.assertEqual(validate_orbit(700, 700, 98), (700.0, 700.0, 98.0))

    def test_perigee_above_apogee_rejected(self):
        with self.assertRaises(ValueError):
            validate_orbit(36000.0, 700.0, 0.0)

    def test_zero_altitude_rejected(self):
        with self.assertRaises(ValueError):
            validate_orbit(0.0, 700.0, 51.6)

    def test_inclination_out_of_range_rejected(self):
        with self.assertRaises(ValueError):
            validate_orbit(700.0, 700.0, 190.0)

    def test_non_numeric_inclination_rejected(self):
        with self.assertRaises(ValueError):
            validate_orbit(700.0, 700.0, "polar")

    def test_boolean_altitude_rejected(self):
        with self.assertRaises(ValueError):
            validate_orbit(True, 700.0, 0.0)


class RegimeTests(unittest.TestCase):
    def test_equatorial_low_orbit_is_low_inclination_leo(self):
        self.assertEqual(categorize_orbit_regime(500.0, 550.0, 6.0), "leo-low-inclination")

    def test_sun_synchronous_orbit_is_polar_leo(self):
        self.assertEqual(categorize_orbit_regime(700.0, 720.0, 98.2), "leo-polar")

    def test_navigation_orbit_is_meo(self):
        self.assertEqual(categorize_orbit_regime(23200.0, 23250.0, 56.0), "meo")

    def test_geostationary_orbit_is_geo(self):
        self.assertEqual(categorize_orbit_regime(35780.0, 35790.0, 0.05), "geo")

    def test_inclined_geosynchronous_orbit_is_not_geo(self):
        self.assertNotEqual(categorize_orbit_regime(35780.0, 35790.0, 40.0), "geo")

    def test_transfer_orbit_crosses_the_belts(self):
        self.assertEqual(categorize_orbit_regime(250.0, 35786.0, 6.0), "heo-belt-crossing")

    def test_escape_trajectory_is_interplanetary(self):
        self.assertEqual(
            categorize_orbit_regime(300000.0, 900000.0, 20.0), "interplanetary"
        )

    def test_every_regime_has_a_full_data_row(self):
        for regime in ORBIT_REGIMES:
            self.assertIn(regime, ENVIRONMENT_COMPONENTS)
            self.assertIn(regime, REFERENCE_DOSE_RATE_KRAD_PER_YEAR)
            self.assertIn(regime, SEE_LET_THRESHOLD_MEV_CM2_MG)


class EnvironmentComponentTests(unittest.TestCase):
    def test_belt_crossing_carries_all_four_components(self):
        self.assertEqual(len(environment_components("heo-belt-crossing")), 4)

    def test_interplanetary_has_no_trapped_component(self):
        components = environment_components("interplanetary")
        self.assertNotIn("trapped-protons", components)
        self.assertNotIn("trapped-electrons", components)

    def test_geostationary_carries_trapped_electrons(self):
        self.assertIn("trapped-electrons", environment_components("geo"))

    def test_unknown_regime_rejected(self):
        with self.assertRaises(ValueError):
            environment_components("cislunar-halo")

    def test_non_string_regime_rejected(self):
        with self.assertRaises(ValueError):
            reference_dose_rate(7)


class DoseTests(unittest.TestCase):
    def test_dose_scales_linearly_with_duration(self):
        one = mission_dose_krad("geo", 1.0)
        five = mission_dose_krad("geo", 5.0)
        self.assertAlmostEqual(five, 5.0 * one, places=9)

    def test_cycle_averaged_weight_is_unity(self):
        self.assertAlmostEqual(solar_activity_weight("cycle-averaged"), 1.0, places=9)

    def test_solar_minimum_is_harder_than_solar_maximum(self):
        self.assertGreater(
            solar_activity_weight("solar-minimum"), solar_activity_weight("solar-maximum")
        )

    def test_solar_assumption_is_normalised(self):
        self.assertAlmostEqual(
            solar_activity_weight("Solar Minimum"),
            solar_activity_weight("solar-minimum"),
            places=9,
        )

    def test_unknown_solar_assumption_rejected(self):
        with self.assertRaises(ValueError):
            solar_activity_weight("solar-whenever")

    def test_zero_duration_rejected(self):
        with self.assertRaises(ValueError):
            mission_dose_krad("geo", 0.0)

    def test_meo_accumulates_more_than_low_inclination_leo(self):
        self.assertGreater(mission_dose_krad("meo", 7.0), mission_dose_krad("leo-low-inclination", 7.0))


class RequirementTests(unittest.TestCase):
    def test_design_factor_multiplies_the_dose(self):
        self.assertAlmostEqual(
            preliminary_tid_requirement_krad(30.0, 2.0), 60.0, places=9
        )

    def test_unity_design_factor_is_accepted_at_the_bound(self):
        self.assertAlmostEqual(
            preliminary_tid_requirement_krad(30.0, 1.0), 30.0, places=9
        )

    def test_design_factor_below_unity_rejected(self):
        with self.assertRaises(ValueError):
            preliminary_tid_requirement_krad(30.0, 0.9)

    def test_non_numeric_design_factor_rejected(self):
        with self.assertRaises(ValueError):
            preliminary_tid_requirement_krad(30.0, "two")

    def test_negative_dose_rejected(self):
        with self.assertRaises(ValueError):
            preliminary_tid_requirement_krad(-30.0, 2.0)

    def test_let_threshold_is_hardest_away_from_geomagnetic_shielding(self):
        self.assertGreater(
            see_let_threshold("interplanetary"), see_let_threshold("leo-low-inclination")
        )


class DeliverableTests(unittest.TestCase):
    def test_full_set_leaves_nothing_missing(self):
        self.assertEqual(missing_feasibility_deliverables(ALL_DELIVERABLES), [])

    def test_names_are_normalised_before_matching(self):
        self.assertEqual(
            missing_feasibility_deliverables(
                [item.replace("-", " ").upper() for item in ALL_DELIVERABLES]
            ),
            [],
        )

    def test_absent_item_is_reported_in_canonical_order(self):
        missing = missing_feasibility_deliverables(ALL_DELIVERABLES[1:])
        self.assertEqual(missing, [FEASIBILITY_DELIVERABLES[0]])

    def test_non_sequence_rejected(self):
        with self.assertRaises(ValueError):
            missing_feasibility_deliverables("everything")

    def test_empty_name_rejected(self):
        with self.assertRaises(ValueError):
            missing_feasibility_deliverables(["  "])


class AssessmentTests(unittest.TestCase):
    def _spec(self, **overrides):
        spec = {
            "perigee_km": 35780.0,
            "apogee_km": 35790.0,
            "inclination_deg": 0.05,
            "duration_years": 15.0,
            "design_factor": 2.0,
            "solar_assumption": "cycle-averaged",
            "deliverables": list(ALL_DELIVERABLES),
        }
        spec.update(overrides)
        return spec

    def test_complete_feasibility_study_reports_no_findings(self):
        result = assess_feasibility_phase(self._spec())
        self.assertTrue(result["complete"])
        self.assertEqual(result["findings"], [])

    def test_requirement_is_the_dose_times_the_factor(self):
        result = assess_feasibility_phase(self._spec())
        self.assertAlmostEqual(
            result["preliminary_tid_requirement_krad"],
            result["mission_dose_krad"] * 2.0,
            places=9,
        )

    def test_missing_deliverable_is_a_finding(self):
        result = assess_feasibility_phase(self._spec(deliverables=ALL_DELIVERABLES[:-1]))
        self.assertFalse(result["complete"])
        self.assertEqual(len(result["missing_deliverables"]), 1)

    def test_belt_crossing_raises_the_shielding_finding(self):
        result = assess_feasibility_phase(
            self._spec(perigee_km=250.0, apogee_km=35786.0, inclination_deg=6.0)
        )
        self.assertEqual(result["regime"], "heo-belt-crossing")
        self.assertTrue(any("shielding assumption" in f for f in result["findings"]))

    def test_regime_drives_the_let_threshold(self):
        result = assess_feasibility_phase(self._spec())
        self.assertAlmostEqual(
            result["see_let_threshold_mev_cm2_mg"], see_let_threshold("geo"), places=9
        )

    def test_missing_spec_key_rejected(self):
        spec = self._spec()
        del spec["duration_years"]
        with self.assertRaises(ValueError):
            assess_feasibility_phase(spec)

    def test_non_mapping_spec_rejected(self):
        with self.assertRaises(ValueError):
            assess_feasibility_phase(("geo", 15.0))

    def test_solar_minimum_raises_the_requirement(self):
        low = assess_feasibility_phase(self._spec(solar_assumption="solar-maximum"))
        high = assess_feasibility_phase(self._spec(solar_assumption="solar-minimum"))
        self.assertGreater(
            high["preliminary_tid_requirement_krad"],
            low["preliminary_tid_requirement_krad"],
        )


if __name__ == "__main__":
    unittest.main()
