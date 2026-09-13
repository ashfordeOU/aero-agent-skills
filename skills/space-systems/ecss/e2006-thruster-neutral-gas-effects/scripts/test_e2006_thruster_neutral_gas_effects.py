#!/usr/bin/env python3
"""Gate 3 contract test for e2006-thruster-neutral-gas-effects."""

import math
import unittest

import e2006_thruster_neutral_gas_effects_logic as logic

AMU = 1.66053906660e-27


def thruster(**overrides):
    base = {
        "propellant": "xenon",
        "species_mass_amu": 131.3,
        "exhaust_speed_m_s": 3.0e4,
        "divergence_exponent": 12.0,
        "sources": [
            {"type": "beam-directed-efflux", "mass_flow_kg_s": 5.0e-6},
        ],
    }
    base.update(overrides)
    return base


def surface(**overrides):
    base = {
        "id": "sa-string-1",
        "range_m": 1.0,
        "off_axis_deg": 0.0,
        "gap_m": 0.002,
        "applied_bias_v": 100.0,
        "gas_temperature_k": 300.0,
        "ionization_fraction": 1.0e-5,
        "ionization_cross_section_m2": 5.0e-19,
    }
    base.update(overrides)
    return base


class CategorizeGasSource(unittest.TestCase):
    def test_beam_directed_efflux_family(self):
        self.assertEqual(
            logic.categorize_gas_source("beam-directed-efflux"), "accelerated-beam"
        )

    def test_unionized_propellant_family(self):
        self.assertEqual(
            logic.categorize_gas_source("unionized-propellant"), "discharge-chamber"
        )

    def test_neutralizer_flow_family(self):
        self.assertEqual(
            logic.categorize_gas_source("neutralizer-flow"), "cathode-feed"
        )

    def test_valve_leak_family(self):
        self.assertEqual(logic.categorize_gas_source("valve-leak"), "feed-system")

    def test_source_type_is_case_and_space_insensitive(self):
        self.assertEqual(
            logic.categorize_gas_source("  Valve-Leak "), "feed-system"
        )

    def test_uncategorized_source_type_raises(self):
        with self.assertRaises(ValueError):
            logic.categorize_gas_source("solar-array-outgassing")

    def test_empty_source_type_raises(self):
        with self.assertRaises(ValueError):
            logic.categorize_gas_source("   ")

    def test_non_string_source_type_raises(self):
        with self.assertRaises(ValueError):
            logic.categorize_gas_source(7)


class EmittedParticleRate(unittest.TestCase):
    def test_unit_mass_flow_gives_unit_rate(self):
        self.assertAlmostEqual(logic.emitted_particle_rate(AMU, 1.0), 1.0, places=9)

    def test_xenon_beam_rate(self):
        rate = logic.emitted_particle_rate(5.0e-6, 131.3)
        self.assertAlmostEqual(rate / 2.293275233e19, 1.0, places=7)

    def test_zero_mass_flow_is_allowed(self):
        self.assertAlmostEqual(logic.emitted_particle_rate(0.0, 131.3), 0.0, places=12)

    def test_negative_mass_flow_raises(self):
        with self.assertRaises(ValueError):
            logic.emitted_particle_rate(-1.0e-6, 131.3)

    def test_zero_species_mass_raises(self):
        with self.assertRaises(ValueError):
            logic.emitted_particle_rate(1.0e-6, 0.0)

    def test_none_species_mass_raises(self):
        with self.assertRaises(ValueError):
            logic.emitted_particle_rate(1.0e-6, None)


class Directionality(unittest.TestCase):
    def test_isotropic_hemisphere_on_axis(self):
        self.assertAlmostEqual(logic.directionality(0.0, 0.0), 1.0 / (2.0 * math.pi))

    def test_forward_hemisphere_is_normalized(self):
        steps = 90000
        total = 0.0
        for i in range(steps):
            theta = (i + 0.5) * (math.pi / 2.0) / steps
            total += (
                logic.directionality(math.degrees(theta), 12.0)
                * 2.0
                * math.pi
                * math.sin(theta)
                * (math.pi / 2.0)
                / steps
            )
        self.assertAlmostEqual(total, 1.0, places=5)

    def test_density_falls_off_axis(self):
        self.assertLess(
            logic.directionality(30.0, 12.0), logic.directionality(0.0, 12.0)
        )

    def test_backflow_branch_at_exit_plane(self):
        peak = 13.0 / (2.0 * math.pi)
        self.assertAlmostEqual(logic.directionality(90.0, 12.0), peak * 1.0e-3)

    def test_backflow_decays_one_decay_length_behind_plane(self):
        self.assertAlmostEqual(
            logic.directionality(120.0, 12.0), 7.611478098e-4, places=10
        )

    def test_backflow_is_monotonically_decreasing(self):
        self.assertLess(
            logic.directionality(150.0, 12.0), logic.directionality(100.0, 12.0)
        )

    def test_angle_beyond_180_raises(self):
        with self.assertRaises(ValueError):
            logic.directionality(181.0, 12.0)

    def test_negative_angle_raises(self):
        with self.assertRaises(ValueError):
            logic.directionality(-1.0, 12.0)

    def test_negative_divergence_exponent_raises(self):
        with self.assertRaises(ValueError):
            logic.directionality(10.0, -2.0)


class PlumeNumberDensity(unittest.TestCase):
    def test_on_axis_isotropic_point_source(self):
        value = logic.plume_number_density(AMU, 1.0, 1.0, 1.0, 0.0, 0.0)
        self.assertAlmostEqual(value, 1.0 / (2.0 * math.pi), places=9)

    def test_xenon_beam_on_axis_at_one_metre(self):
        value = logic.plume_number_density(5.0e-6, 131.3, 3.0e4, 1.0, 0.0, 12.0)
        self.assertAlmostEqual(value / 1.5816063866e15, 1.0, places=7)

    def test_inverse_square_range_dependence(self):
        near = logic.plume_number_density(5.0e-6, 131.3, 3.0e4, 1.0, 0.0, 12.0)
        far = logic.plume_number_density(5.0e-6, 131.3, 3.0e4, 2.0, 0.0, 12.0)
        self.assertAlmostEqual(near / far, 4.0, places=9)

    def test_backflow_density_is_small_but_non_zero(self):
        value = logic.plume_number_density(5.0e-6, 131.3, 3.0e4, 1.0, 120.0, 12.0)
        self.assertGreater(value, 0.0)
        self.assertLess(value, 1.0e13)

    def test_zero_range_raises(self):
        with self.assertRaises(ValueError):
            logic.plume_number_density(5.0e-6, 131.3, 3.0e4, 0.0, 0.0, 12.0)

    def test_zero_exhaust_speed_raises(self):
        with self.assertRaises(ValueError):
            logic.plume_number_density(5.0e-6, 131.3, 0.0, 1.0, 0.0, 12.0)


class LocalGasPressure(unittest.TestCase):
    def test_pressure_of_a_plume_density(self):
        self.assertAlmostEqual(
            logic.local_gas_pressure(1.5816063866e15, 300.0) / 6.5509298e-06,
            1.0,
            places=6,
        )

    def test_zero_density_gives_zero_pressure(self):
        self.assertAlmostEqual(logic.local_gas_pressure(0.0, 300.0), 0.0, places=15)

    def test_negative_density_raises(self):
        with self.assertRaises(ValueError):
            logic.local_gas_pressure(-1.0, 300.0)

    def test_zero_temperature_raises(self):
        with self.assertRaises(ValueError):
            logic.local_gas_pressure(1.0e15, 0.0)


class ElectronMeanFreePath(unittest.TestCase):
    def test_mean_free_path_value(self):
        self.assertAlmostEqual(
            logic.electron_mean_free_path(1.0e18, 1.0e-18), 1.0, places=9
        )

    def test_zero_density_is_unbounded(self):
        self.assertEqual(logic.electron_mean_free_path(0.0, 5.0e-19), math.inf)

    def test_zero_cross_section_raises(self):
        with self.assertRaises(ValueError):
            logic.electron_mean_free_path(1.0e18, 0.0)

    def test_negative_density_raises(self):
        with self.assertRaises(ValueError):
            logic.electron_mean_free_path(-1.0e18, 5.0e-19)


class PaschenBreakdown(unittest.TestCase):
    def test_above_the_minimum_has_a_solution(self):
        value = logic.paschen_breakdown_voltage(200.0, 0.002, "xenon")
        self.assertAlmostEqual(value, 353.8687217, places=5)

    def test_below_the_minimum_has_no_branch(self):
        self.assertIsNone(logic.paschen_breakdown_voltage(6.55e-06, 0.002, "xenon"))

    def test_zero_pressure_has_no_branch(self):
        self.assertIsNone(logic.paschen_breakdown_voltage(0.0, 0.002, "xenon"))

    def test_gas_name_is_case_insensitive(self):
        self.assertAlmostEqual(
            logic.paschen_breakdown_voltage(200.0, 0.002, "XENON"),
            353.8687217,
            places=5,
        )

    def test_argon_fit_differs_from_xenon(self):
        self.assertNotAlmostEqual(
            logic.paschen_breakdown_voltage(200.0, 0.002, "argon"),
            logic.paschen_breakdown_voltage(200.0, 0.002, "xenon"),
            places=2,
        )

    def test_unknown_gas_raises(self):
        with self.assertRaises(ValueError):
            logic.paschen_breakdown_voltage(200.0, 0.002, "helium")

    def test_zero_gap_raises(self):
        with self.assertRaises(ValueError):
            logic.paschen_breakdown_voltage(200.0, 0.0, "xenon")

    def test_negative_pressure_raises(self):
        with self.assertRaises(ValueError):
            logic.paschen_breakdown_voltage(-1.0, 0.002, "xenon")


class IonizedPlasmaDensity(unittest.TestCase):
    def test_plasma_density_value(self):
        self.assertAlmostEqual(
            logic.ionized_plasma_density(1.0e15, 1.0e-5) / 1.0e10, 1.0, places=9
        )

    def test_full_ionization_returns_neutral_density(self):
        self.assertAlmostEqual(
            logic.ionized_plasma_density(2.0e14, 1.0) / 2.0e14, 1.0, places=12
        )

    def test_fraction_above_one_raises(self):
        with self.assertRaises(ValueError):
            logic.ionized_plasma_density(1.0e15, 1.5)

    def test_negative_fraction_raises(self):
        with self.assertRaises(ValueError):
            logic.ionized_plasma_density(1.0e15, -0.1)

    def test_negative_neutral_density_raises(self):
        with self.assertRaises(ValueError):
            logic.ionized_plasma_density(-1.0, 0.1)


class DebyeLength(unittest.TestCase):
    def test_debye_length_value(self):
        self.assertAlmostEqual(logic.debye_length(1.0e12, 1.0), 0.0074339419, places=9)

    def test_denser_plasma_has_shorter_debye_length(self):
        self.assertLess(logic.debye_length(1.0e14, 1.0), logic.debye_length(1.0e12, 1.0))

    def test_zero_density_raises(self):
        with self.assertRaises(ValueError):
            logic.debye_length(0.0, 1.0)

    def test_zero_electron_temperature_raises(self):
        with self.assertRaises(ValueError):
            logic.debye_length(1.0e12, 0.0)


class DischargeCriteria(unittest.TestCase):
    def test_typical_plume_is_density_limited(self):
        result = logic.evaluate_discharge_criteria(
            1.5816063866e15, 0.002, 100.0, "xenon", 300.0, 1.0e-5, 5.0e-19
        )
        self.assertTrue(result["density_too_low"])
        self.assertFalse(result["discharge_sustained"])
        self.assertEqual(
            result["governing_criterion"],
            "plasma-density-below-sustaining-threshold",
        )
        self.assertGreater(result["margin_ratio"], 1.0e3)

    def test_no_breakdown_branch_is_reported_not_failed(self):
        result = logic.evaluate_discharge_criteria(
            1.0e18, 0.002, 100.0, "xenon", 300.0, 1.0e-9, 5.0e-19
        )
        self.assertIsNone(result["breakdown_voltage_v"])
        self.assertTrue(result["bias_below_breakdown"])
        self.assertFalse(result["discharge_sustained"])

    def test_sustained_discharge_case(self):
        result = logic.evaluate_discharge_criteria(
            3.5e25, 0.002, 20000.0, "xenon", 300.0, 0.01, 5.0e-19
        )
        self.assertTrue(result["avalanche_possible"])
        self.assertFalse(result["bias_below_breakdown"])
        self.assertFalse(result["density_too_low"])
        self.assertTrue(result["discharge_sustained"])
        self.assertEqual(result["governing_criterion"], "discharge-sustainable")
        self.assertAlmostEqual(result["breakdown_voltage_v"], 14535.06480, places=3)

    def test_bias_exactly_at_breakdown_voltage_is_compliant(self):
        pressure = logic.local_gas_pressure(3.5e25, 300.0)
        breakdown = logic.paschen_breakdown_voltage(pressure, 0.002, "xenon")
        result = logic.evaluate_discharge_criteria(
            3.5e25, 0.002, breakdown, "xenon", 300.0, 0.01, 5.0e-19
        )
        self.assertTrue(result["bias_below_breakdown"])
        self.assertFalse(result["discharge_sustained"])

    def test_boundary_plasma_density_from_float_sum_is_compliant(self):
        fraction = 0.1 + 0.2
        threshold = 3.0e13
        self.assertGreater(1.0e14 * fraction, threshold)
        result = logic.evaluate_discharge_criteria(
            1.0e14,
            0.002,
            100.0,
            "xenon",
            300.0,
            fraction,
            5.0e-19,
            sustaining_density_m3=threshold,
        )
        self.assertTrue(result["density_too_low"])
        self.assertFalse(result["discharge_sustained"])

    def test_gap_equal_to_mean_free_path_is_collisionless(self):
        result = logic.evaluate_discharge_criteria(
            1.0e18, 1.0, 100.0, "xenon", 300.0, 1.0e-9, 1.0e-18
        )
        self.assertFalse(result["avalanche_possible"])

    def test_collisionless_gap_governs_when_density_is_high(self):
        result = logic.evaluate_discharge_criteria(
            1.0e20, 1.0, 5000.0, "xenon", 300.0, 1.0, 1.0e-21
        )
        self.assertFalse(result["density_too_low"])
        self.assertFalse(result["bias_below_breakdown"])
        self.assertEqual(
            result["governing_criterion"], "gap-collisionless-for-electrons"
        )
        self.assertFalse(result["discharge_sustained"])

    def test_pressure_gap_product_is_reported(self):
        result = logic.evaluate_discharge_criteria(
            3.5e25, 0.002, 20000.0, "xenon", 300.0, 0.01, 5.0e-19
        )
        self.assertAlmostEqual(
            result["pressure_gap_product_pa_m"] / 289.93629, 1.0, places=7
        )

    def test_negative_bias_raises(self):
        with self.assertRaises(ValueError):
            logic.evaluate_discharge_criteria(
                1.0e15, 0.002, -5.0, "xenon", 300.0, 1.0e-5, 5.0e-19
            )

    def test_zero_sustaining_density_raises(self):
        with self.assertRaises(ValueError):
            logic.evaluate_discharge_criteria(
                1.0e15,
                0.002,
                100.0,
                "xenon",
                300.0,
                1.0e-5,
                5.0e-19,
                sustaining_density_m3=0.0,
            )


class SurfaceNeutralDensity(unittest.TestCase):
    def test_contributions_sum_over_sources(self):
        thr = thruster(
            sources=[
                {"type": "beam-directed-efflux", "mass_flow_kg_s": 5.0e-6},
                {"type": "neutralizer-flow", "mass_flow_kg_s": 5.0e-7},
            ]
        )
        result = logic.surface_neutral_density(thr, surface())
        self.assertAlmostEqual(
            result["total_m3"],
            result["by_source"]["beam-directed-efflux"]
            + result["by_source"]["neutralizer-flow"],
            delta=1.0e3,
        )

    def test_families_are_listed(self):
        thr = thruster(
            sources=[
                {"type": "beam-directed-efflux", "mass_flow_kg_s": 5.0e-6},
                {"type": "valve-leak", "mass_flow_kg_s": 1.0e-9},
            ]
        )
        result = logic.surface_neutral_density(thr, surface())
        self.assertEqual(result["families"], ["accelerated-beam", "feed-system"])

    def test_missing_geometry_raises(self):
        bad = surface()
        del bad["range_m"]
        with self.assertRaises(ValueError):
            logic.surface_neutral_density(thruster(), bad)

    def test_surface_must_be_a_mapping(self):
        with self.assertRaises(ValueError):
            logic.surface_neutral_density(thruster(), ["sa-string-1"])


class AssessSurface(unittest.TestCase):
    def test_typical_surface_is_compliant(self):
        record = logic.assess_surface(thruster(), surface())
        self.assertTrue(record["compliant"])
        self.assertEqual(record["findings"], [])
        self.assertEqual(
            record["criteria"]["governing_criterion"],
            "plasma-density-below-sustaining-threshold",
        )

    def test_missing_ionization_fraction_is_an_evidence_gap(self):
        record = logic.assess_surface(thruster(), surface(ionization_fraction=None))
        self.assertFalse(record["compliant"])
        self.assertIsNone(record["criteria"])
        self.assertIn("evidence-gap", record["findings"][0])

    def test_missing_bias_and_gap_are_both_named(self):
        record = logic.assess_surface(
            thruster(), surface(applied_bias_v=None, gap_m=None)
        )
        self.assertIn("gap_m", record["findings"][0])
        self.assertIn("applied_bias_v", record["findings"][0])

    def test_rear_mounted_surface_sees_backflow_only(self):
        record = logic.assess_surface(thruster(), surface(off_axis_deg=135.0))
        self.assertGreater(record["neutral_density_m3"], 0.0)
        self.assertTrue(record["compliant"])


class AssessReport(unittest.TestCase):
    def test_report_over_several_surfaces_is_compliant(self):
        report = logic.assess_thruster_neutral_gas_effects(
            thruster(),
            [surface(), surface(id="sa-string-2", off_axis_deg=120.0)],
        )
        self.assertTrue(report["compliant"])
        self.assertTrue(report["evidence_complete"])
        self.assertEqual(report["surface_count"], 2)

    def test_report_flags_an_evidence_gap(self):
        report = logic.assess_thruster_neutral_gas_effects(
            thruster(),
            [surface(), surface(id="sa-string-2", ionization_fraction=None)],
        )
        self.assertFalse(report["compliant"])
        self.assertFalse(report["evidence_complete"])
        self.assertEqual(len(report["findings"]), 1)

    def test_duplicate_surface_id_raises(self):
        with self.assertRaises(ValueError):
            logic.assess_thruster_neutral_gas_effects(
                thruster(), [surface(), surface()]
            )

    def test_empty_surface_list_raises(self):
        with self.assertRaises(ValueError):
            logic.assess_thruster_neutral_gas_effects(thruster(), [])

    def test_unknown_propellant_raises(self):
        with self.assertRaises(ValueError):
            logic.assess_thruster_neutral_gas_effects(
                thruster(propellant="helium"), [surface()]
            )

    def test_empty_source_list_raises(self):
        with self.assertRaises(ValueError):
            logic.assess_thruster_neutral_gas_effects(
                thruster(sources=[]), [surface()]
            )

    def test_uncategorized_source_in_thruster_raises(self):
        with self.assertRaises(ValueError):
            logic.assess_thruster_neutral_gas_effects(
                thruster(sources=[{"type": "mli-outgassing", "mass_flow_kg_s": 1e-9}]),
                [surface()],
            )

    def test_thruster_must_be_a_mapping(self):
        with self.assertRaises(ValueError):
            logic.assess_thruster_neutral_gas_effects("xenon", [surface()])

    def test_surface_entry_must_be_a_mapping(self):
        with self.assertRaises(ValueError):
            logic.assess_thruster_neutral_gas_effects(thruster(), ["sa-string-1"])


if __name__ == "__main__":
    unittest.main()
