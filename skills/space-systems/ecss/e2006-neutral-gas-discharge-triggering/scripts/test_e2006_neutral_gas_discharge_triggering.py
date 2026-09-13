#!/usr/bin/env python3
"""Gate 3 contract test for e2006-neutral-gas-discharge-triggering."""

import math
import unittest

import e2006_neutral_gas_discharge_triggering_logic as logic


class ReleasePathTests(unittest.TestCase):
    def test_thruster_plume_is_a_commanded_transient(self):
        self.assertEqual(
            logic.release_path_behaviour("attitude-thruster-plume"),
            "commanded-transient",
        )

    def test_pressurant_leak_is_continuous(self):
        self.assertEqual(logic.release_path_behaviour("pressurant-leak"), "continuous")

    def test_material_outgassing_is_decaying(self):
        self.assertEqual(logic.release_path_behaviour("material-outgassing"), "decaying")

    def test_unknown_release_path_is_rejected(self):
        with self.assertRaises(ValueError):
            logic.release_path_behaviour("meteoroid-impact")

    def test_non_string_release_path_is_rejected(self):
        with self.assertRaises(ValueError):
            logic.release_path_behaviour(None)

    def test_decaying_family_holds_both_desorption_paths(self):
        self.assertEqual(
            logic.paths_with_behaviour("decaying"),
            ["material-outgassing", "water-desorption"],
        )

    def test_unknown_behaviour_family_is_rejected(self):
        with self.assertRaises(ValueError):
            logic.paths_with_behaviour("explosive")

    def test_every_catalogued_path_has_a_known_behaviour(self):
        for path in logic.RELEASE_PATHS:
            self.assertIn(logic.release_path_behaviour(path), logic.BEHAVIOURS)


class ThermalSpeedTests(unittest.TestCase):
    def test_xenon_mean_speed_at_room_temperature(self):
        self.assertAlmostEqual(
            logic.mean_thermal_speed("xenon", 300.0), 219.9515319, places=5
        )

    def test_lighter_species_is_faster(self):
        self.assertGreater(
            logic.mean_thermal_speed("water-vapour", 300.0),
            logic.mean_thermal_speed("xenon", 300.0),
        )

    def test_helium_is_the_fastest_catalogued_species(self):
        speeds = {
            s: logic.mean_thermal_speed(s, 300.0) for s in logic.GAS_PROPERTIES
        }
        self.assertEqual(max(speeds, key=speeds.get), "helium")

    def test_speed_scales_with_the_square_root_of_temperature(self):
        ratio = (logic.mean_thermal_speed("nitrogen", 1200.0) /
                 logic.mean_thermal_speed("nitrogen", 300.0))
        self.assertAlmostEqual(ratio, 2.0, places=9)

    def test_unknown_species_is_rejected(self):
        with self.assertRaises(ValueError):
            logic.mean_thermal_speed("hydrazine", 300.0)

    def test_non_positive_temperature_is_rejected(self):
        with self.assertRaises(ValueError):
            logic.mean_thermal_speed("xenon", 0.0)

    def test_non_numeric_temperature_is_rejected(self):
        with self.assertRaises(ValueError):
            logic.mean_thermal_speed("xenon", "300")


class ParticleRateTests(unittest.TestCase):
    def test_particle_rate_from_a_xenon_mass_rate(self):
        self.assertAlmostEqual(
            logic.particle_rate(1.0e-6, "xenon") / 1.0e18, 4.5867950, places=6
        )

    def test_lighter_species_yields_more_particles_per_kilogram(self):
        self.assertGreater(
            logic.particle_rate(1.0e-6, "helium"),
            logic.particle_rate(1.0e-6, "xenon"),
        )

    def test_zero_mass_rate_is_rejected(self):
        with self.assertRaises(ValueError):
            logic.particle_rate(0.0, "xenon")

    def test_negative_mass_rate_is_rejected(self):
        with self.assertRaises(ValueError):
            logic.particle_rate(-1.0e-6, "xenon")

    def test_boolean_mass_rate_is_rejected(self):
        with self.assertRaises(ValueError):
            logic.particle_rate(True, "xenon")


class DensityAndPressureTests(unittest.TestCase):
    def test_free_molecular_density_value(self):
        density = logic.local_number_density(1.0e20, 1.0, 500.0)
        self.assertAlmostEqual(density / 1.0e16, 3.1830988618, places=6)

    def test_density_falls_with_the_square_of_distance(self):
        near = logic.local_number_density(1.0e20, 1.0, 500.0)
        far = logic.local_number_density(1.0e20, 2.0, 500.0)
        self.assertAlmostEqual(near / far, 4.0, places=9)

    def test_narrower_expansion_cone_raises_the_density(self):
        wide = logic.local_number_density(1.0e20, 1.0, 500.0, 4.0 * math.pi)
        narrow = logic.local_number_density(1.0e20, 1.0, 500.0, 0.5)
        self.assertGreater(narrow, wide)

    def test_non_positive_distance_is_rejected(self):
        with self.assertRaises(ValueError):
            logic.local_number_density(1.0e20, 0.0, 500.0)

    def test_non_positive_flow_speed_is_rejected(self):
        with self.assertRaises(ValueError):
            logic.local_number_density(1.0e20, 1.0, -5.0)

    def test_solid_angle_above_full_sphere_is_rejected(self):
        with self.assertRaises(ValueError):
            logic.local_number_density(1.0e20, 1.0, 500.0, 13.0)

    def test_neutral_pressure_value(self):
        pressure = logic.neutral_pressure(1.0e16, 300.0)
        self.assertAlmostEqual(pressure / 1.0e-5, 4.1419470, places=6)

    def test_neutral_pressure_rejects_non_positive_density(self):
        with self.assertRaises(ValueError):
            logic.neutral_pressure(0.0, 300.0)

    def test_release_pressure_uses_the_thermal_speed_by_default(self):
        pressure = logic.local_pressure_from_release(1.0e-6, "xenon", 1.0, 300.0)
        self.assertAlmostEqual(pressure / 1.0e-5, 1.3746970, places=5)

    def test_faster_flow_speed_lowers_the_local_pressure(self):
        thermal = logic.local_pressure_from_release(1.0e-6, "xenon", 1.0, 300.0)
        fast = logic.local_pressure_from_release(
            1.0e-6, "xenon", 1.0, 300.0, flow_speed_m_per_s=5000.0
        )
        self.assertLess(fast, thermal)

    def test_release_pressure_rejects_a_missing_mass_rate(self):
        with self.assertRaises(ValueError):
            logic.local_pressure_from_release(None, "xenon", 1.0, 300.0)


class PaschenCurveTests(unittest.TestCase):
    def test_air_curve_minimum(self):
        pd_min, v_min = logic.paschen_minimum("air")
        self.assertAlmostEqual(pd_min, 1.1151287322, places=8)
        self.assertAlmostEqual(v_min, 305.3222468722, places=6)

    def test_xenon_curve_minimum(self):
        pd_min, v_min = logic.paschen_minimum("xenon")
        self.assertAlmostEqual(pd_min, 0.5480928292, places=8)
        self.assertAlmostEqual(v_min, 143.8743676745, places=6)

    def test_helium_minimum_voltage_is_below_air(self):
        self.assertLess(
            logic.paschen_minimum("helium")[1], logic.paschen_minimum("air")[1]
        )

    def test_critical_product_sits_below_the_minimum_for_every_species(self):
        for species in logic.GAS_PROPERTIES:
            pd_min, _ = logic.paschen_minimum(species)
            self.assertLess(logic.critical_pressure_gap_product(species), pd_min)

    def test_below_the_critical_product_no_breakdown_is_possible(self):
        self.assertEqual(
            logic.paschen_breakdown_voltage("air", 1.0, 0.01), math.inf
        )

    def test_breakdown_voltage_at_the_curve_minimum(self):
        pd_min, v_min = logic.paschen_minimum("air")
        voltage = logic.paschen_breakdown_voltage("air", pd_min / 0.01, 0.01)
        self.assertAlmostEqual(voltage / v_min, 1.0, places=9)

    def test_breakdown_voltage_rises_on_the_right_branch(self):
        low = logic.paschen_breakdown_voltage("air", 1000.0, 0.01)
        high = logic.paschen_breakdown_voltage("air", 10000.0, 0.01)
        self.assertGreater(high, low)

    def test_breakdown_voltage_falls_towards_the_minimum_on_the_left_branch(self):
        near_critical = logic.paschen_breakdown_voltage("air", 45.0, 0.01)
        near_minimum = logic.paschen_breakdown_voltage("air", 110.0, 0.01)
        self.assertGreater(near_critical, near_minimum)

    def test_curve_minimum_is_the_lowest_breakdown_voltage(self):
        pd_min, v_min = logic.paschen_minimum("nitrogen")
        for factor in (0.6, 0.8, 1.3, 2.0, 10.0):
            voltage = logic.paschen_breakdown_voltage(
                "nitrogen", pd_min * factor / 0.02, 0.02
            )
            self.assertGreaterEqual(voltage, v_min - 1.0e-9)

    def test_unknown_species_is_rejected_by_the_curve(self):
        with self.assertRaises(ValueError):
            logic.paschen_breakdown_voltage("methane", 100.0, 0.01)

    def test_non_positive_pressure_is_rejected_by_the_curve(self):
        with self.assertRaises(ValueError):
            logic.paschen_breakdown_voltage("air", 0.0, 0.01)

    def test_non_positive_gap_is_rejected_by_the_curve(self):
        with self.assertRaises(ValueError):
            logic.paschen_breakdown_voltage("air", 100.0, -0.01)


class BranchTests(unittest.TestCase):
    def test_small_product_is_out_of_reach_of_breakdown(self):
        self.assertEqual(
            logic.paschen_branch("air", 1.0, 0.01), "no-breakdown-possible"
        )

    def test_product_between_critical_and_minimum_is_the_left_branch(self):
        self.assertEqual(logic.paschen_branch("air", 100.0, 0.01), "left-branch")

    def test_product_at_the_minimum_is_reported_as_the_minimum(self):
        pd_min, _ = logic.paschen_minimum("air")
        self.assertEqual(
            logic.paschen_branch("air", pd_min / 0.01, 0.01), "paschen-minimum"
        )

    def test_large_product_is_the_right_branch(self):
        self.assertEqual(logic.paschen_branch("air", 5000.0, 0.01), "right-branch")

    def test_gap_size_moves_the_same_pressure_between_branches(self):
        self.assertEqual(
            logic.paschen_branch("air", 100.0, 1.0e-4), "no-breakdown-possible"
        )
        self.assertEqual(logic.paschen_branch("air", 100.0, 0.1), "right-branch")


class MarginTests(unittest.TestCase):
    def test_margin_is_the_voltage_ratio(self):
        self.assertAlmostEqual(logic.breakdown_margin(300.0, 600.0), 2.0, places=12)

    def test_unreachable_breakdown_gives_an_unbounded_margin(self):
        self.assertEqual(logic.breakdown_margin(300.0, math.inf), math.inf)

    def test_non_positive_applied_voltage_is_rejected(self):
        with self.assertRaises(ValueError):
            logic.breakdown_margin(0.0, 600.0)

    def test_non_positive_breakdown_voltage_is_rejected(self):
        with self.assertRaises(ValueError):
            logic.breakdown_margin(300.0, -600.0)

    def test_exactly_met_margin_passes(self):
        self.assertTrue(logic.is_margin_met(300.0, 600.0, 2.0))

    def test_margin_a_few_ulps_low_is_absorbed(self):
        self.assertTrue(logic.is_margin_met(300.0, 600.0 * (1.0 - 1.0e-15), 2.0))

    def test_genuinely_short_margin_fails(self):
        self.assertFalse(logic.is_margin_met(300.0, 570.0, 2.0))

    def test_unreachable_breakdown_always_meets_the_margin(self):
        self.assertTrue(logic.is_margin_met(300.0, math.inf, 5.0))

    def test_non_positive_required_margin_is_rejected(self):
        with self.assertRaises(ValueError):
            logic.is_margin_met(300.0, 600.0, 0.0)


class SafePressureTests(unittest.TestCase):
    def test_highest_safe_pressure_for_a_ten_millimetre_gap(self):
        pressure = logic.maximum_safe_pressure("air", 0.01, 300.0, 2.0)
        self.assertAlmostEqual(pressure, 52.0129323751, places=6)

    def test_the_returned_pressure_sits_on_the_required_voltage(self):
        pressure = logic.maximum_safe_pressure("air", 0.01, 300.0, 2.0)
        voltage = logic.paschen_breakdown_voltage("air", pressure, 0.01)
        self.assertAlmostEqual(voltage / 600.0, 1.0, places=6)

    def test_low_applied_voltage_clears_the_whole_curve(self):
        self.assertEqual(
            logic.maximum_safe_pressure("air", 0.01, 100.0, 2.0), math.inf
        )

    def test_non_positive_gap_is_rejected(self):
        with self.assertRaises(ValueError):
            logic.maximum_safe_pressure("air", 0.0, 300.0, 2.0)

    def test_non_positive_applied_voltage_is_rejected(self):
        with self.assertRaises(ValueError):
            logic.maximum_safe_pressure("air", 0.01, -300.0, 2.0)

    def test_non_positive_required_margin_is_rejected(self):
        with self.assertRaises(ValueError):
            logic.maximum_safe_pressure("air", 0.01, 300.0, 0.0)


class OutgassingDecayTests(unittest.TestCase):
    def test_inverse_first_power_decay_halves_in_double_the_time(self):
        pressure = logic.outgassing_pressure_at_time(1.0e-2, 1.0, 2.0, 1.0)
        self.assertAlmostEqual(pressure, 5.0e-3, places=12)

    def test_inverse_square_decay_quarters_in_double_the_time(self):
        pressure = logic.outgassing_pressure_at_time(1.0e-2, 1.0, 2.0, 2.0)
        self.assertAlmostEqual(pressure, 2.5e-3, places=12)

    def test_decay_and_inversion_round_trip(self):
        target = logic.outgassing_pressure_at_time(1.0e-2, 1.0, 37.0, 1.3)
        recovered = logic.time_to_reach_pressure(1.0e-2, 1.0, target, 1.3)
        self.assertAlmostEqual(recovered, 37.0, places=6)

    def test_target_above_the_reference_needs_no_wait(self):
        self.assertAlmostEqual(
            logic.time_to_reach_pressure(1.0e-3, 2.0, 1.0e-2, 1.0), 2.0, places=12
        )

    def test_non_positive_reference_pressure_is_rejected(self):
        with self.assertRaises(ValueError):
            logic.outgassing_pressure_at_time(0.0, 1.0, 2.0, 1.0)

    def test_non_positive_elapsed_time_is_rejected(self):
        with self.assertRaises(ValueError):
            logic.outgassing_pressure_at_time(1.0e-2, 1.0, 0.0, 1.0)

    def test_non_positive_decay_exponent_is_rejected(self):
        with self.assertRaises(ValueError):
            logic.time_to_reach_pressure(1.0e-2, 1.0, 1.0e-4, 0.0)


class ScenarioAssessmentTests(unittest.TestCase):
    def clean_vent(self):
        return {
            "path": "commanded-vent",
            "species": "water-vapour",
            "gap_m": 0.005,
            "applied_voltage_v": 100.0,
            "local_pressure_pa": 1.0e-3,
        }

    def marginal_leak(self):
        return {
            "path": "pressurant-leak",
            "species": "air",
            "gap_m": 0.01,
            "applied_voltage_v": 300.0,
            "local_pressure_pa": 100.0,
        }

    def outgassing_case(self):
        return {
            "path": "material-outgassing",
            "species": "water-vapour",
            "gap_m": 0.01,
            "applied_voltage_v": 300.0,
            "local_pressure_pa": 100.0,
            "reference_time_h": 1.0,
            "decay_exponent": 1.0,
        }

    def test_clean_vent_is_out_of_reach_of_breakdown(self):
        result = logic.assess_release_path(self.clean_vent())
        self.assertTrue(result["compliant"])
        self.assertEqual(result["branch"], "no-breakdown-possible")
        self.assertEqual(result["margin"], math.inf)
        self.assertEqual(result["findings"], [])

    def test_marginal_leak_fails_on_the_left_branch(self):
        result = logic.assess_release_path(self.marginal_leak())
        self.assertFalse(result["compliant"])
        self.assertEqual(result["branch"], "left-branch")
        self.assertLess(result["margin"], 2.0)
        self.assertTrue(result["findings"])

    def test_continuous_path_gets_no_activation_window(self):
        result = logic.assess_release_path(self.marginal_leak())
        self.assertIsNone(result["activation_inhibit_h"])

    def test_decaying_path_yields_an_activation_inhibit(self):
        result = logic.assess_release_path(self.outgassing_case())
        self.assertFalse(result["compliant"])
        self.assertGreater(result["activation_inhibit_h"], 0.0)
        self.assertTrue(math.isfinite(result["activation_inhibit_h"]))

    def test_the_inhibit_window_reaches_the_safe_pressure(self):
        case = self.outgassing_case()
        result = logic.assess_release_path(case)
        safe = logic.maximum_safe_pressure("water-vapour", 0.01, 300.0, 2.0)
        reached = logic.outgassing_pressure_at_time(
            case["local_pressure_pa"], 1.0, result["activation_inhibit_h"], 1.0
        )
        self.assertAlmostEqual(reached / safe, 1.0, places=6)

    def test_compliant_decaying_path_needs_no_inhibit(self):
        case = self.outgassing_case()
        case["local_pressure_pa"] = 1.0e-4
        result = logic.assess_release_path(case)
        self.assertTrue(result["compliant"])
        self.assertIsNone(result["activation_inhibit_h"])

    def test_pressure_is_derived_from_a_mass_rate_when_not_given(self):
        result = logic.assess_release_path(
            {
                "path": "propulsion-plume",
                "species": "xenon",
                "gap_m": 0.01,
                "applied_voltage_v": 500.0,
                "mass_rate_kg_per_s": 5.0e-6,
                "distance_m": 0.5,
                "temperature_k": 500.0,
            }
        )
        self.assertTrue(result["compliant"])
        self.assertGreater(result["local_pressure_pa"], 0.0)
        self.assertEqual(result["behaviour"], "commanded-transient")

    def test_pressure_gap_product_is_reported(self):
        result = logic.assess_release_path(self.marginal_leak())
        self.assertAlmostEqual(result["pressure_gap_product_pa_m"], 1.0, places=12)

    def test_scenario_must_be_a_mapping(self):
        with self.assertRaises(ValueError):
            logic.assess_release_path(["commanded-vent"])

    def test_scenario_missing_a_required_key_is_rejected(self):
        case = self.marginal_leak()
        del case["gap_m"]
        with self.assertRaises(ValueError):
            logic.assess_release_path(case)

    def test_scenario_with_an_unknown_path_is_rejected(self):
        case = self.marginal_leak()
        case["path"] = "solar-wind"
        with self.assertRaises(ValueError):
            logic.assess_release_path(case)


class EnvironmentAggregationTests(unittest.TestCase):
    def clean_case(self):
        return {
            "path": "commanded-vent",
            "species": "water-vapour",
            "gap_m": 0.005,
            "applied_voltage_v": 100.0,
            "local_pressure_pa": 1.0e-3,
        }

    def bad_case(self):
        return {
            "path": "material-outgassing",
            "species": "water-vapour",
            "gap_m": 0.01,
            "applied_voltage_v": 300.0,
            "local_pressure_pa": 100.0,
        }

    def test_all_clean_paths_aggregate_to_compliant(self):
        result = logic.assess_gas_environment([self.clean_case(), self.clean_case()])
        self.assertTrue(result["compliant"])
        self.assertEqual(result["findings"], [])
        self.assertAlmostEqual(result["activation_inhibit_h"], 0.0, places=12)

    def test_one_bad_path_fails_the_environment(self):
        result = logic.assess_gas_environment([self.clean_case(), self.bad_case()])
        self.assertFalse(result["compliant"])
        self.assertTrue(result["findings"])

    def test_the_longest_inhibit_window_governs(self):
        short = self.bad_case()
        long = self.bad_case()
        long["local_pressure_pa"] = 400.0
        result = logic.assess_gas_environment([short, long])
        windows = [r["activation_inhibit_h"] for r in result["results"]]
        self.assertAlmostEqual(result["activation_inhibit_h"], max(windows), places=9)

    def test_every_result_is_returned(self):
        result = logic.assess_gas_environment([self.clean_case(), self.bad_case()])
        self.assertEqual(len(result["results"]), 2)

    def test_empty_scenario_list_is_rejected(self):
        with self.assertRaises(ValueError):
            logic.assess_gas_environment([])

    def test_non_list_scenarios_are_rejected(self):
        with self.assertRaises(ValueError):
            logic.assess_gas_environment(self.clean_case())


if __name__ == "__main__":
    unittest.main()
