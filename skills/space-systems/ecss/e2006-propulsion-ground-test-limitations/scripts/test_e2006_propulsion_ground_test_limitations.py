#!/usr/bin/env python3
"""Gate 3 contract test for e2006-propulsion-ground-test-limitations."""

import math
import unittest

import e2006_propulsion_ground_test_limitations_logic as logic


def campaign(**overrides):
    base = {
        "mass_flow_kg_s": 5.0e-6,
        "pumping_speed_m3_s": 100.0,
        "species_mass_amu": 131.3,
        "gas_temperature_k": 300.0,
        "max_background_pressure_pa": 1.0e-3,
        "axial_distance_m": 5.0,
        "chamber_radius_m": 2.5,
        "plume_half_angle_deg": 20.0,
        "plume_path_length_m": 3.0,
        "cex_cross_section_m2": 5.0e-19,
    }
    base.update(overrides)
    return base


def effects():
    return [
        {
            "id": "elevated-background-pressure",
            "magnitude": 9.5e-4,
            "influenced_quantity": "plume-current-density",
            "relative_influence": 0.12,
            "correction_factor": 0.93,
        },
        {
            "id": "back-sputtered-wall-material",
            "magnitude": 4.0e-11,
            "influenced_quantity": "surface-resistivity",
            "relative_influence": 0.004,
        },
        {
            "id": "grounded-wall-potential-clamp",
            "magnitude": 12.0,
            "influenced_quantity": "article-floating-potential",
            "correction_factor": 1.0,
        },
        {
            "id": "plume-truncation-by-wall",
            "magnitude": 0.03,
            "influenced_quantity": "divergence-half-angle",
            "relative_influence": 0.01,
        },
    ]


class CategorizeChamberEffect(unittest.TestCase):
    def test_background_pressure_is_pressure_driven(self):
        self.assertEqual(
            logic.categorize_chamber_effect("elevated-background-pressure"),
            "pressure-driven",
        )

    def test_charge_exchange_is_pressure_driven(self):
        self.assertEqual(
            logic.categorize_chamber_effect("charge-exchange-enhancement"),
            "pressure-driven",
        )

    def test_back_sputtered_material_is_wall_material(self):
        self.assertEqual(
            logic.categorize_chamber_effect("back-sputtered-wall-material"),
            "wall-material",
        )

    def test_potential_clamp_is_electrical_boundary(self):
        self.assertEqual(
            logic.categorize_chamber_effect("grounded-wall-potential-clamp"),
            "electrical-boundary",
        )

    def test_artificial_current_return_is_electrical_boundary(self):
        self.assertEqual(
            logic.categorize_chamber_effect("artificial-current-return"),
            "electrical-boundary",
        )

    def test_plume_truncation_is_geometric(self):
        self.assertEqual(
            logic.categorize_chamber_effect("plume-truncation-by-wall"),
            "geometric-truncation",
        )

    def test_thermal_reflux_is_thermal_boundary(self):
        self.assertEqual(
            logic.categorize_chamber_effect("beam-dump-thermal-reflux"),
            "thermal-boundary",
        )

    def test_effect_id_is_case_and_space_insensitive(self):
        self.assertEqual(
            logic.categorize_chamber_effect("  Artificial-Current-Return "),
            "electrical-boundary",
        )

    def test_uncategorized_effect_raises(self):
        with self.assertRaises(ValueError):
            logic.categorize_chamber_effect("solar-simulator-glare")

    def test_empty_effect_id_raises(self):
        with self.assertRaises(ValueError):
            logic.categorize_chamber_effect("")

    def test_non_string_effect_id_raises(self):
        with self.assertRaises(ValueError):
            logic.categorize_chamber_effect(None)


class PropellantThroughput(unittest.TestCase):
    def test_xenon_throughput_value(self):
        value = logic.propellant_throughput(5.0e-6, 131.3, 300.0)
        self.assertAlmostEqual(value / 0.09498624471, 1.0, places=8)

    def test_throughput_scales_with_mass_flow(self):
        low = logic.propellant_throughput(5.0e-6, 131.3, 300.0)
        high = logic.propellant_throughput(1.0e-5, 131.3, 300.0)
        self.assertAlmostEqual(high / low, 2.0, places=10)

    def test_zero_mass_flow_gives_zero_throughput(self):
        self.assertAlmostEqual(
            logic.propellant_throughput(0.0, 131.3, 300.0), 0.0, places=15
        )

    def test_negative_mass_flow_raises(self):
        with self.assertRaises(ValueError):
            logic.propellant_throughput(-1.0e-6, 131.3, 300.0)

    def test_zero_species_mass_raises(self):
        with self.assertRaises(ValueError):
            logic.propellant_throughput(5.0e-6, 0.0, 300.0)

    def test_zero_temperature_raises(self):
        with self.assertRaises(ValueError):
            logic.propellant_throughput(5.0e-6, 131.3, 0.0)


class BackgroundPressure(unittest.TestCase):
    def test_operating_point_pressure_value(self):
        value = logic.background_pressure(5.0e-6, 100.0, 131.3, 300.0)
        self.assertAlmostEqual(value / 9.49862447e-4, 1.0, places=8)

    def test_a_bigger_pump_lowers_the_pressure(self):
        small = logic.background_pressure(5.0e-6, 50.0, 131.3, 300.0)
        large = logic.background_pressure(5.0e-6, 200.0, 131.3, 300.0)
        self.assertAlmostEqual(small / large, 4.0, places=10)

    def test_zero_pumping_speed_raises(self):
        with self.assertRaises(ValueError):
            logic.background_pressure(5.0e-6, 0.0, 131.3, 300.0)

    def test_negative_pumping_speed_raises(self):
        with self.assertRaises(ValueError):
            logic.background_pressure(5.0e-6, -10.0, 131.3, 300.0)

    def test_missing_mass_flow_raises(self):
        with self.assertRaises(ValueError):
            logic.background_pressure(None, 100.0, 131.3, 300.0)


class RequiredPumpingSpeed(unittest.TestCase):
    def test_required_speed_for_a_target_pressure(self):
        value = logic.required_pumping_speed(5.0e-6, 1.0e-3, 131.3, 300.0)
        self.assertAlmostEqual(value / 94.98624471, 1.0, places=8)

    def test_round_trip_reproduces_the_target_pressure(self):
        speed = logic.required_pumping_speed(5.0e-6, 1.0e-3, 131.3, 300.0)
        pressure = logic.background_pressure(5.0e-6, speed, 131.3, 300.0)
        self.assertAlmostEqual(pressure / 1.0e-3, 1.0, places=12)

    def test_zero_target_pressure_raises(self):
        with self.assertRaises(ValueError):
            logic.required_pumping_speed(5.0e-6, 0.0, 131.3, 300.0)

    def test_negative_target_pressure_raises(self):
        with self.assertRaises(ValueError):
            logic.required_pumping_speed(5.0e-6, -1.0e-3, 131.3, 300.0)


class ResidualGasNumberDensity(unittest.TestCase):
    def test_density_at_operating_pressure(self):
        value = logic.residual_gas_number_density(9.49862447e-4, 300.0)
        self.assertAlmostEqual(value / 2.29327523e17, 1.0, places=7)

    def test_zero_pressure_gives_zero_density(self):
        self.assertAlmostEqual(
            logic.residual_gas_number_density(0.0, 300.0), 0.0, places=12
        )

    def test_negative_pressure_raises(self):
        with self.assertRaises(ValueError):
            logic.residual_gas_number_density(-1.0e-4, 300.0)

    def test_zero_temperature_raises(self):
        with self.assertRaises(ValueError):
            logic.residual_gas_number_density(1.0e-4, 0.0)


class ChargeExchangeFraction(unittest.TestCase):
    def test_fraction_over_a_three_metre_path(self):
        value = logic.charge_exchange_fraction(9.49862447e-4, 3.0, 5.0e-19, 300.0)
        self.assertAlmostEqual(value, 0.29106489, places=7)

    def test_zero_path_length_gives_no_exchange(self):
        self.assertAlmostEqual(
            logic.charge_exchange_fraction(9.5e-4, 0.0, 5.0e-19, 300.0),
            0.0,
            places=12,
        )

    def test_fraction_saturates_at_unity_for_a_long_dense_path(self):
        value = logic.charge_exchange_fraction(1.0, 100.0, 5.0e-19, 300.0)
        self.assertLessEqual(value, 1.0)
        self.assertAlmostEqual(value, 1.0, places=12)

    def test_fraction_stays_strictly_inside_the_unit_interval(self):
        value = logic.charge_exchange_fraction(1.0e-2, 3.0, 5.0e-19, 300.0)
        self.assertGreater(value, 0.0)
        self.assertLess(value, 1.0)

    def test_fraction_grows_with_pressure(self):
        low = logic.charge_exchange_fraction(1.0e-4, 3.0, 5.0e-19, 300.0)
        high = logic.charge_exchange_fraction(1.0e-3, 3.0, 5.0e-19, 300.0)
        self.assertGreater(high, low)

    def test_negative_path_length_raises(self):
        with self.assertRaises(ValueError):
            logic.charge_exchange_fraction(9.5e-4, -1.0, 5.0e-19, 300.0)

    def test_zero_cross_section_raises(self):
        with self.assertRaises(ValueError):
            logic.charge_exchange_fraction(9.5e-4, 3.0, 0.0, 300.0)


class WallInterception(unittest.TestCase):
    def test_contained_cone_reports_clearance(self):
        result = logic.wall_interception(5.0, 2.5, 20.0)
        self.assertTrue(result["contained"])
        self.assertFalse(result["truncated"])
        self.assertAlmostEqual(result["plume_radius_m"], 1.81985117, places=7)
        self.assertAlmostEqual(result["clearance_m"], 0.68014882, places=7)

    def test_wide_cone_is_truncated(self):
        result = logic.wall_interception(5.0, 2.5, 45.0)
        self.assertTrue(result["truncated"])
        self.assertLess(result["clearance_m"], 0.0)

    def test_grazing_cone_is_contained(self):
        radius = 5.0 * math.tan(math.radians(30.0))
        result = logic.wall_interception(5.0, radius, 30.0)
        self.assertTrue(result["contained"])

    def test_longer_chamber_widens_the_cone(self):
        near = logic.wall_interception(2.0, 10.0, 20.0)
        far = logic.wall_interception(4.0, 10.0, 20.0)
        self.assertAlmostEqual(far["plume_radius_m"] / near["plume_radius_m"], 2.0)

    def test_zero_axial_distance_raises(self):
        with self.assertRaises(ValueError):
            logic.wall_interception(0.0, 2.5, 20.0)

    def test_zero_chamber_radius_raises(self):
        with self.assertRaises(ValueError):
            logic.wall_interception(5.0, 0.0, 20.0)

    def test_half_angle_at_ninety_degrees_raises(self):
        with self.assertRaises(ValueError):
            logic.wall_interception(5.0, 2.5, 90.0)

    def test_zero_half_angle_raises(self):
        with self.assertRaises(ValueError):
            logic.wall_interception(5.0, 2.5, 0.0)


class BackSputteredMassFlux(unittest.TestCase):
    def test_graphite_wall_flux_value(self):
        value = logic.back_sputtered_mass_flux(1.0, 0.5, 12.0, 2.5, 0.05)
        self.assertAlmostEqual(value / 3.95885939e-11, 1.0, places=7)

    def test_flux_scales_linearly_with_beam_current(self):
        low = logic.back_sputtered_mass_flux(1.0, 0.5, 12.0, 2.5, 0.05)
        high = logic.back_sputtered_mass_flux(3.0, 0.5, 12.0, 2.5, 0.05)
        self.assertAlmostEqual(high / low, 3.0, places=10)

    def test_zero_return_fraction_gives_no_deposition(self):
        self.assertAlmostEqual(
            logic.back_sputtered_mass_flux(1.0, 0.5, 12.0, 2.5, 0.0),
            0.0,
            places=18,
        )

    def test_negative_beam_current_raises(self):
        with self.assertRaises(ValueError):
            logic.back_sputtered_mass_flux(-1.0, 0.5, 12.0, 2.5, 0.05)

    def test_negative_sputter_yield_raises(self):
        with self.assertRaises(ValueError):
            logic.back_sputtered_mass_flux(1.0, -0.5, 12.0, 2.5, 0.05)

    def test_zero_target_mass_raises(self):
        with self.assertRaises(ValueError):
            logic.back_sputtered_mass_flux(1.0, 0.5, 0.0, 2.5, 0.05)

    def test_return_fraction_above_one_raises(self):
        with self.assertRaises(ValueError):
            logic.back_sputtered_mass_flux(1.0, 0.5, 12.0, 2.5, 1.5)

    def test_zero_chamber_radius_raises(self):
        with self.assertRaises(ValueError):
            logic.back_sputtered_mass_flux(1.0, 0.5, 12.0, 0.0, 0.05)


class FacilityCorrectedValue(unittest.TestCase):
    def test_single_correction_scales_the_measurement(self):
        self.assertAlmostEqual(logic.facility_corrected_value(100.0, [0.93]), 93.0)

    def test_corrections_compose(self):
        self.assertAlmostEqual(
            logic.facility_corrected_value(100.0, [0.9, 1.1]), 99.0, places=10
        )

    def test_empty_correction_list_is_identity(self):
        self.assertAlmostEqual(logic.facility_corrected_value(42.5, []), 42.5)

    def test_zero_correction_factor_raises(self):
        with self.assertRaises(ValueError):
            logic.facility_corrected_value(100.0, [0.0])

    def test_negative_correction_factor_raises(self):
        with self.assertRaises(ValueError):
            logic.facility_corrected_value(100.0, [-1.0])

    def test_non_numeric_correction_factor_raises(self):
        with self.assertRaises(ValueError):
            logic.facility_corrected_value(100.0, ["0.9"])

    def test_correction_list_must_be_a_sequence(self):
        with self.assertRaises(ValueError):
            logic.facility_corrected_value(100.0, 0.9)


class EffectIsEstablished(unittest.TestCase):
    def test_corrected_effect_is_established(self):
        result = logic.effect_is_established(effects()[0])
        self.assertTrue(result["established"])
        self.assertEqual(result["disposition"], "corrected")
        self.assertEqual(result["family"], "pressure-driven")

    def test_negligible_effect_is_established(self):
        result = logic.effect_is_established(effects()[1])
        self.assertTrue(result["established"])
        self.assertEqual(result["disposition"], "negligible-within-tolerance")

    def test_missing_magnitude_is_not_established(self):
        record = dict(effects()[1])
        record["magnitude"] = None
        result = logic.effect_is_established(record)
        self.assertFalse(result["established"])
        self.assertEqual(result["reason"], "magnitude-not-established")

    def test_missing_influenced_quantity_is_not_established(self):
        record = dict(effects()[1])
        record["influenced_quantity"] = ""
        result = logic.effect_is_established(record)
        self.assertFalse(result["established"])
        self.assertEqual(result["reason"], "influence-on-result-not-stated")

    def test_uncorrected_large_influence_is_not_established(self):
        record = dict(effects()[1])
        record["relative_influence"] = 0.25
        result = logic.effect_is_established(record)
        self.assertFalse(result["established"])
        self.assertEqual(result["reason"], "uncorrected-and-not-negligible")

    def test_no_influence_and_no_correction_is_not_established(self):
        record = dict(effects()[1])
        record.pop("relative_influence")
        result = logic.effect_is_established(record)
        self.assertFalse(result["established"])

    def test_negative_influence_uses_its_magnitude(self):
        record = dict(effects()[1])
        record["relative_influence"] = -0.004
        self.assertTrue(logic.effect_is_established(record)["established"])

    def test_influence_exactly_at_tolerance_from_a_float_sum(self):
        record = dict(effects()[1])
        record["relative_influence"] = 0.1 + 0.2
        self.assertGreater(record["relative_influence"], 0.3)
        result = logic.effect_is_established(record, negligible_influence=0.3)
        self.assertTrue(result["established"])
        self.assertEqual(result["disposition"], "negligible-within-tolerance")

    def test_influence_just_beyond_tolerance_is_not_established(self):
        record = dict(effects()[1])
        record["relative_influence"] = 0.31
        result = logic.effect_is_established(record, negligible_influence=0.3)
        self.assertFalse(result["established"])

    def test_zero_correction_factor_raises(self):
        record = dict(effects()[0])
        record["correction_factor"] = 0.0
        with self.assertRaises(ValueError):
            logic.effect_is_established(record)

    def test_non_numeric_magnitude_raises(self):
        record = dict(effects()[1])
        record["magnitude"] = "small"
        with self.assertRaises(ValueError):
            logic.effect_is_established(record)

    def test_non_numeric_influence_raises(self):
        record = dict(effects()[1])
        record["relative_influence"] = "tiny"
        with self.assertRaises(ValueError):
            logic.effect_is_established(record)

    def test_negative_tolerance_raises(self):
        with self.assertRaises(ValueError):
            logic.effect_is_established(effects()[1], negligible_influence=-0.1)

    def test_effect_record_must_be_a_mapping(self):
        with self.assertRaises(ValueError):
            logic.effect_is_established("elevated-background-pressure")

    def test_unknown_effect_id_raises(self):
        with self.assertRaises(ValueError):
            logic.effect_is_established({"id": "operator-error", "magnitude": 1.0})


class MissingEffectFamilies(unittest.TestCase):
    def test_full_coverage_leaves_nothing_missing(self):
        self.assertEqual(logic.missing_effect_families(effects()), [])

    def test_dropping_the_electrical_family_is_reported(self):
        reduced = [e for e in effects() if e["id"] != "grounded-wall-potential-clamp"]
        self.assertEqual(
            logic.missing_effect_families(reduced), ["electrical-boundary"]
        )

    def test_empty_effect_list_misses_every_required_family(self):
        self.assertEqual(
            logic.missing_effect_families([]), list(logic.REQUIRED_EFFECT_FAMILIES)
        )

    def test_thermal_family_alone_is_not_sufficient(self):
        missing = logic.missing_effect_families(
            [{"id": "beam-dump-thermal-reflux", "magnitude": 1.0}]
        )
        self.assertEqual(len(missing), 4)

    def test_effects_must_be_a_list(self):
        with self.assertRaises(ValueError):
            logic.missing_effect_families({"id": "elevated-background-pressure"})


class AssessGroundTestLimitations(unittest.TestCase):
    def test_well_established_campaign_is_representative(self):
        report = logic.assess_ground_test_limitations(campaign(), effects())
        self.assertTrue(report["flight_representative"])
        self.assertEqual(report["findings"], [])
        self.assertTrue(report["background_pressure_within_limit"])
        self.assertAlmostEqual(
            report["background_pressure_pa"] / 9.49862447e-4, 1.0, places=8
        )

    def test_charge_exchange_fraction_is_reported(self):
        report = logic.assess_ground_test_limitations(campaign(), effects())
        self.assertAlmostEqual(report["charge_exchange_fraction"], 0.29106489, places=7)

    def test_pressure_at_exactly_the_limit_passes(self):
        speed = logic.required_pumping_speed(5.0e-6, 1.0e-3, 131.3, 300.0)
        report = logic.assess_ground_test_limitations(
            campaign(pumping_speed_m3_s=speed), effects()
        )
        self.assertTrue(report["background_pressure_within_limit"])
        self.assertTrue(report["flight_representative"])

    def test_undersized_pump_is_flagged_with_the_required_speed(self):
        report = logic.assess_ground_test_limitations(
            campaign(pumping_speed_m3_s=10.0), effects()
        )
        self.assertFalse(report["background_pressure_within_limit"])
        self.assertFalse(report["flight_representative"])
        self.assertIn("required pumping-speed", report["findings"][0])

    def test_truncated_plume_is_flagged(self):
        report = logic.assess_ground_test_limitations(
            campaign(plume_half_angle_deg=45.0), effects()
        )
        self.assertTrue(report["geometry"]["truncated"])
        self.assertTrue(
            any(f.startswith("plume-truncation") for f in report["findings"])
        )

    def test_unestablished_effect_is_flagged(self):
        broken = effects()
        broken[1] = dict(broken[1])
        broken[1]["relative_influence"] = 0.4
        report = logic.assess_ground_test_limitations(campaign(), broken)
        self.assertFalse(report["flight_representative"])
        self.assertIn("uncorrected-and-not-negligible", report["findings"][0])

    def test_missing_family_is_flagged(self):
        reduced = [e for e in effects() if e["id"] != "plume-truncation-by-wall"]
        report = logic.assess_ground_test_limitations(campaign(), reduced)
        self.assertTrue(
            any("geometric-truncation" in f for f in report["findings"])
        )

    def test_correction_factors_are_collected(self):
        report = logic.assess_ground_test_limitations(campaign(), effects())
        self.assertEqual(len(report["correction_factors"]), 2)
        self.assertAlmostEqual(
            logic.facility_corrected_value(100.0, report["correction_factors"]),
            93.0,
            places=10,
        )

    def test_duplicate_effect_id_raises(self):
        duplicated = effects() + [dict(effects()[0])]
        with self.assertRaises(ValueError):
            logic.assess_ground_test_limitations(campaign(), duplicated)

    def test_missing_pressure_limit_raises(self):
        with self.assertRaises(ValueError):
            logic.assess_ground_test_limitations(
                campaign(max_background_pressure_pa=None), effects()
            )

    def test_empty_effect_list_raises(self):
        with self.assertRaises(ValueError):
            logic.assess_ground_test_limitations(campaign(), [])

    def test_campaign_must_be_a_mapping(self):
        with self.assertRaises(ValueError):
            logic.assess_ground_test_limitations("chamber-a", effects())

    def test_missing_chamber_geometry_raises(self):
        with self.assertRaises(ValueError):
            logic.assess_ground_test_limitations(
                campaign(chamber_radius_m=None), effects()
            )


if __name__ == "__main__":
    unittest.main()
