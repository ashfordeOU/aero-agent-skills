#!/usr/bin/env python3
"""Gate 3 contract test for e2006-neutral-gas-density-assessment.

stdlib unittest, offline, deterministic. Run:
    python3 test_e2006_neutral_gas_density_assessment.py
"""

from __future__ import annotations

import math
import os
import sys
import unittest

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import e2006_neutral_gas_density_assessment_logic as logic  # noqa: E402


def ep_source(**over):
    rec = {
        "source_id": "SRC-EP-1",
        "species": "xenon",
        "kind": "electric-thruster-plume",
        "mass_flow_kg_s": 5.0e-6,
        "exit_velocity_m_s": 20000.0,
        "plume_half_angle_deg": 20.0,
    }
    rec.update(over)
    return rec


def vent_source(**over):
    rec = {
        "source_id": "SRC-VENT-1",
        "species": "nitrogen",
        "kind": "cold-gas-vent",
        "mass_flow_kg_s": 1.0e-6,
        "exit_velocity_m_s": 700.0,
        "plume_half_angle_deg": 45.0,
    }
    rec.update(over)
    return rec


def antenna_point(**over):
    rec = {
        "point_id": "PT-ANTENNA",
        "distance_m": 2.0,
        "field_angle_deg": 0.0,
        "characteristic_length_m": 1.0,
        "plasma_density_limit_m3": 1.0e18,
    }
    rec.update(over)
    return rec


AMBIENT = 1.0e10
ELECTRON_TEMPERATURE_EV = 5.0


class TestSourceValidation(unittest.TestCase):
    def test_valid_source_is_normalized(self):
        src = logic.validate_release_source(ep_source())
        self.assertEqual(src["source_id"], "SRC-EP-1")
        self.assertAlmostEqual(src["mass_flow_kg_s"], 5.0e-6, places=15)

    def test_non_mapping_source_rejected(self):
        with self.assertRaises(ValueError):
            logic.validate_release_source("SRC-EP-1")

    def test_missing_identifier_rejected(self):
        rec = ep_source()
        del rec["source_id"]
        with self.assertRaises(ValueError):
            logic.validate_release_source(rec)

    def test_unknown_species_rejected(self):
        with self.assertRaises(ValueError):
            logic.validate_release_source(ep_source(species="neon"))

    def test_unknown_release_kind_rejected(self):
        with self.assertRaises(ValueError):
            logic.validate_release_source(ep_source(kind="sublimation"))

    def test_zero_mass_flow_rejected(self):
        with self.assertRaises(ValueError):
            logic.validate_release_source(ep_source(mass_flow_kg_s=0.0))

    def test_negative_exit_velocity_rejected(self):
        with self.assertRaises(ValueError):
            logic.validate_release_source(ep_source(exit_velocity_m_s=-1.0))

    def test_half_angle_at_ninety_rejected(self):
        with self.assertRaises(ValueError):
            logic.validate_release_source(ep_source(plume_half_angle_deg=90.0))

    def test_half_angle_at_zero_rejected(self):
        with self.assertRaises(ValueError):
            logic.validate_release_source(ep_source(plume_half_angle_deg=0.0))

    def test_non_numeric_half_angle_rejected(self):
        with self.assertRaises(ValueError):
            logic.validate_release_source(ep_source(plume_half_angle_deg="wide"))


class TestEmissionRate(unittest.TestCase):
    def test_rate_matches_hand_calculation(self):
        mass = logic.PROPELLANT_SPECIES["xenon"]["mass_amu"] * logic.AMU_KG
        self.assertAlmostEqual(
            logic.number_emission_rate_s(5.0e-6, "xenon") / (5.0e-6 / mass),
            1.0,
            places=12,
        )

    def test_lighter_species_releases_more_particles(self):
        heavy = logic.number_emission_rate_s(1.0e-6, "xenon")
        light = logic.number_emission_rate_s(1.0e-6, "water-vapour")
        self.assertGreater(light, heavy)

    def test_unknown_species_rejected(self):
        with self.assertRaises(ValueError):
            logic.number_emission_rate_s(1.0e-6, "neon")

    def test_zero_mass_flow_rejected(self):
        with self.assertRaises(ValueError):
            logic.number_emission_rate_s(0.0, "xenon")


class TestPlumeShape(unittest.TestCase):
    def test_forty_five_degree_plume_gives_exponent_two(self):
        self.assertAlmostEqual(logic.plume_shape_exponent(45.0), 2.0, places=9)

    def test_narrow_plume_gives_larger_exponent(self):
        self.assertGreater(
            logic.plume_shape_exponent(10.0), logic.plume_shape_exponent(60.0)
        )

    def test_half_power_angle_is_reproduced(self):
        k = logic.plume_shape_exponent(30.0)
        peak = logic.angular_density_factor(0.0, k)
        half = logic.angular_density_factor(30.0, k)
        self.assertAlmostEqual(half / peak, 0.5, places=9)

    def test_exponent_rejects_out_of_range_angle(self):
        with self.assertRaises(ValueError):
            logic.plume_shape_exponent(95.0)

    def test_exponent_rejects_non_numeric_angle(self):
        with self.assertRaises(ValueError):
            logic.plume_shape_exponent(None)


class TestAngularDistribution(unittest.TestCase):
    def test_distribution_integrates_to_unity_over_the_hemisphere(self):
        k = logic.plume_shape_exponent(25.0)
        steps = 20000
        total = 0.0
        for i in range(steps):
            theta = (i + 0.5) * (math.pi / 2.0) / steps
            total += (
                logic.angular_density_factor(math.degrees(theta), k)
                * math.sin(theta)
                * (math.pi / 2.0)
                / steps
            )
        total *= 2.0 * math.pi
        self.assertAlmostEqual(total, 1.0, places=5)

    def test_off_axis_density_is_lower_than_on_axis(self):
        k = logic.plume_shape_exponent(25.0)
        self.assertGreater(
            logic.angular_density_factor(0.0, k),
            logic.angular_density_factor(40.0, k),
        )

    def test_behind_the_exit_plane_is_zero(self):
        k = logic.plume_shape_exponent(25.0)
        self.assertAlmostEqual(logic.angular_density_factor(90.0, k), 0.0, places=15)
        self.assertAlmostEqual(logic.angular_density_factor(140.0, k), 0.0, places=15)

    def test_negative_field_angle_rejected(self):
        with self.assertRaises(ValueError):
            logic.angular_density_factor(-5.0, 2.0)

    def test_non_positive_exponent_rejected(self):
        with self.assertRaises(ValueError):
            logic.angular_density_factor(10.0, 0.0)


class TestNeutralDensity(unittest.TestCase):
    def test_density_is_positive_on_axis(self):
        self.assertGreater(logic.neutral_number_density_m3(ep_source(), 2.0, 0.0), 0.0)

    def test_density_follows_inverse_square_range(self):
        near = logic.neutral_number_density_m3(ep_source(), 2.0, 0.0)
        far = logic.neutral_number_density_m3(ep_source(), 4.0, 0.0)
        self.assertAlmostEqual(near / far, 4.0, places=6)

    def test_density_behind_the_exit_plane_is_zero(self):
        self.assertAlmostEqual(
            logic.neutral_number_density_m3(ep_source(), 2.0, 120.0), 0.0, places=15
        )

    def test_higher_mass_flow_raises_density(self):
        low = logic.neutral_number_density_m3(ep_source(), 2.0, 0.0)
        high = logic.neutral_number_density_m3(
            ep_source(mass_flow_kg_s=5.0e-5), 2.0, 0.0
        )
        self.assertGreater(high, low)

    def test_zero_distance_rejected(self):
        with self.assertRaises(ValueError):
            logic.neutral_number_density_m3(ep_source(), 0.0, 0.0)


class TestFlowRegime(unittest.TestCase):
    def test_mean_free_path_falls_with_density(self):
        self.assertGreater(logic.mean_free_path_m(1.0e14), logic.mean_free_path_m(1.0e18))

    def test_thin_gas_is_free_molecular(self):
        kn = logic.knudsen_number(1.0e14, 1.0)
        self.assertEqual(logic.categorize_flow_regime(kn), "free-molecular")

    def test_dense_gas_is_continuum(self):
        kn = logic.knudsen_number(1.0e26, 1.0)
        self.assertEqual(logic.categorize_flow_regime(kn), "continuum")

    def test_free_molecular_boundary_is_inclusive(self):
        self.assertEqual(
            logic.categorize_flow_regime(logic.FREE_MOLECULAR_KNUDSEN),
            "free-molecular",
        )

    def test_transitional_boundary_is_inclusive(self):
        self.assertEqual(
            logic.categorize_flow_regime(logic.CONTINUUM_KNUDSEN), "transitional"
        )

    def test_every_regime_is_a_declared_regime(self):
        for kn in (1.0e-6, 1.0, 1.0e6):
            self.assertIn(logic.categorize_flow_regime(kn), logic.FLOW_REGIMES)

    def test_non_positive_knudsen_rejected(self):
        with self.assertRaises(ValueError):
            logic.categorize_flow_regime(0.0)

    def test_zero_characteristic_length_rejected(self):
        with self.assertRaises(ValueError):
            logic.knudsen_number(1.0e14, 0.0)

    def test_zero_density_mean_free_path_rejected(self):
        with self.assertRaises(ValueError):
            logic.mean_free_path_m(0.0)


class TestIonization(unittest.TestCase):
    def test_zero_dwell_gives_zero_fraction(self):
        self.assertAlmostEqual(
            logic.ionization_fraction("electric-thruster-plume", "xenon", 0.0, 5.0),
            0.0,
            places=15,
        )

    def test_fraction_rises_with_dwell_time(self):
        short = logic.ionization_fraction(
            "electric-thruster-plume", "xenon", 1.0e-4, 5.0
        )
        long = logic.ionization_fraction(
            "electric-thruster-plume", "xenon", 1.0e-3, 5.0
        )
        self.assertGreater(long, short)

    def test_fraction_never_exceeds_the_mechanism_ceiling(self):
        ceiling = logic.RELEASE_KINDS["electric-thruster-plume"]["fraction_ceiling"]
        value = logic.ionization_fraction(
            "electric-thruster-plume", "xenon", 1.0e6, 50.0
        )
        self.assertLessEqual(value, ceiling)
        self.assertAlmostEqual(value, ceiling, places=9)

    def test_hotter_electrons_ionize_more(self):
        cool = logic.ionization_fraction("electric-thruster-plume", "xenon", 1.0e-4, 2.0)
        hot = logic.ionization_fraction("electric-thruster-plume", "xenon", 1.0e-4, 20.0)
        self.assertGreater(hot, cool)

    def test_low_potential_species_ionizes_more_readily(self):
        iodine = logic.ionization_fraction(
            "electric-thruster-plume", "iodine", 1.0e-4, 5.0
        )
        argon = logic.ionization_fraction(
            "electric-thruster-plume", "argon", 1.0e-4, 5.0
        )
        self.assertGreater(iodine, argon)

    def test_cold_gas_vent_ionizes_far_less_than_a_plume(self):
        plume = logic.ionization_fraction(
            "electric-thruster-plume", "xenon", 1.0e-3, 5.0
        )
        vent = logic.ionization_fraction("cold-gas-vent", "xenon", 1.0e-3, 5.0)
        self.assertGreater(plume, vent)

    def test_unknown_kind_rejected(self):
        with self.assertRaises(ValueError):
            logic.ionization_fraction("sublimation", "xenon", 1.0e-4, 5.0)

    def test_unknown_species_rejected(self):
        with self.assertRaises(ValueError):
            logic.ionization_fraction("electric-thruster-plume", "neon", 1.0e-4, 5.0)

    def test_non_positive_electron_temperature_rejected(self):
        with self.assertRaises(ValueError):
            logic.ionization_fraction("electric-thruster-plume", "xenon", 1.0e-4, 0.0)

    def test_negative_dwell_rejected(self):
        with self.assertRaises(ValueError):
            logic.ionization_fraction("electric-thruster-plume", "xenon", -1.0, 5.0)


class TestPlasmaQuantities(unittest.TestCase):
    def test_electron_density_adds_the_ambient_background(self):
        self.assertAlmostEqual(
            logic.induced_electron_density_m3(1.0e14, 1.0e-3, 1.0e10),
            1.0e11 + 1.0e10,
            places=2,
        )

    def test_fraction_above_unity_rejected(self):
        with self.assertRaises(ValueError):
            logic.induced_electron_density_m3(1.0e14, 1.2)

    def test_negative_ambient_rejected(self):
        with self.assertRaises(ValueError):
            logic.induced_electron_density_m3(1.0e14, 1.0e-3, -1.0)

    def test_plasma_frequency_matches_the_standard_coefficient(self):
        # 8.98 kHz at 1 particle per cubic centimetre, i.e. 1e6 per cubic metre.
        self.assertAlmostEqual(logic.plasma_frequency_hz(1.0e6) / 1.0e3, 8.979, places=2)

    def test_plasma_frequency_scales_as_the_square_root_of_density(self):
        low = logic.plasma_frequency_hz(1.0e12)
        high = logic.plasma_frequency_hz(4.0e12)
        self.assertAlmostEqual(high / low, 2.0, places=9)

    def test_empty_plasma_has_zero_frequency(self):
        self.assertAlmostEqual(logic.plasma_frequency_hz(0.0), 0.0, places=15)

    def test_negative_density_frequency_rejected(self):
        with self.assertRaises(ValueError):
            logic.plasma_frequency_hz(-1.0)

    def test_debye_length_falls_with_density(self):
        self.assertGreater(
            logic.debye_length_m(1.0e10, 5.0), logic.debye_length_m(1.0e12, 5.0)
        )

    def test_debye_length_rises_with_temperature(self):
        self.assertGreater(
            logic.debye_length_m(1.0e11, 20.0), logic.debye_length_m(1.0e11, 5.0)
        )

    def test_zero_density_debye_length_rejected(self):
        with self.assertRaises(ValueError):
            logic.debye_length_m(0.0, 5.0)


class TestRfCompatibility(unittest.TestCase):
    def test_link_well_above_the_plasma_frequency_is_compatible(self):
        result = logic.assess_rf_compatibility(1.0e11, 2.2e9, 5.0)
        self.assertTrue(result["compatible"])

    def test_link_below_the_plasma_frequency_is_not_compatible(self):
        result = logic.assess_rf_compatibility(1.0e14, 1.0e6, 1.0)
        self.assertFalse(result["compatible"])

    def test_carrier_exactly_on_the_required_headroom_is_compatible(self):
        probe = logic.assess_rf_compatibility(1.0e12, 1.0e9, 3.0)
        exact = logic.assess_rf_compatibility(
            1.0e12, probe["required_headroom_hz"], 3.0
        )
        self.assertTrue(exact["compatible"])

    def test_representation_error_on_the_headroom_is_absorbed(self):
        probe = logic.assess_rf_compatibility(1.0e12, 1.0e9, 3.0)
        required = probe["required_headroom_hz"]
        carrier = math.nextafter(required, 0.0)
        self.assertLess(carrier, required)
        edge = logic.assess_rf_compatibility(1.0e12, carrier, 3.0)
        self.assertTrue(edge["compatible"])

    def test_larger_margin_factor_tightens_the_check(self):
        loose = logic.assess_rf_compatibility(1.0e12, 1.2e7, 1.0)
        tight = logic.assess_rf_compatibility(1.0e12, 1.2e7, 100.0)
        self.assertTrue(loose["compatible"])
        self.assertFalse(tight["compatible"])

    def test_non_positive_carrier_rejected(self):
        with self.assertRaises(ValueError):
            logic.assess_rf_compatibility(1.0e12, 0.0)

    def test_non_positive_margin_rejected(self):
        with self.assertRaises(ValueError):
            logic.assess_rf_compatibility(1.0e12, 2.2e9, 0.0)


class TestObservationPoint(unittest.TestCase):
    def test_nominal_point_is_compliant(self):
        result = logic.assess_observation_point(
            antenna_point(), [ep_source()], AMBIENT, ELECTRON_TEMPERATURE_EV
        )
        self.assertTrue(result["compliant"])
        self.assertEqual(result["findings"], [])
        self.assertEqual(result["flow_regime"], "free-molecular")

    def test_point_behind_the_exit_plane_sees_no_release(self):
        result = logic.assess_observation_point(
            antenna_point(field_angle_deg=150.0),
            [ep_source()],
            AMBIENT,
            ELECTRON_TEMPERATURE_EV,
        )
        self.assertEqual(result["contributions"], [])
        self.assertAlmostEqual(result["neutral_density_m3"], 0.0, places=15)
        self.assertAlmostEqual(result["electron_density_m3"], AMBIENT, places=2)

    def test_contributions_sum_into_the_electron_density(self):
        result = logic.assess_observation_point(
            antenna_point(), [ep_source(), vent_source()], AMBIENT, ELECTRON_TEMPERATURE_EV
        )
        total = sum(c["electron_density_m3"] for c in result["contributions"]) + AMBIENT
        self.assertAlmostEqual(result["electron_density_m3"] / total, 1.0, places=12)

    def test_tight_density_limit_is_flagged(self):
        result = logic.assess_observation_point(
            antenna_point(plasma_density_limit_m3=1.0),
            [ep_source()],
            AMBIENT,
            ELECTRON_TEMPERATURE_EV,
        )
        self.assertFalse(result["compliant"])
        self.assertTrue(any("exceeds the limit" in f for f in result["findings"]))

    def test_density_exactly_on_the_limit_is_compliant(self):
        probe = logic.assess_observation_point(
            antenna_point(), [ep_source()], AMBIENT, ELECTRON_TEMPERATURE_EV
        )
        exact = logic.assess_observation_point(
            antenna_point(plasma_density_limit_m3=probe["electron_density_m3"]),
            [ep_source()],
            AMBIENT,
            ELECTRON_TEMPERATURE_EV,
        )
        self.assertTrue(exact["compliant"])

    def test_representation_error_on_the_density_limit_is_absorbed(self):
        probe = logic.assess_observation_point(
            antenna_point(), [ep_source(), vent_source()], AMBIENT, ELECTRON_TEMPERATURE_EV
        )
        density = probe["electron_density_m3"]
        limit = math.nextafter(density, 0.0)
        self.assertLess(limit, density)
        edge = logic.assess_observation_point(
            antenna_point(plasma_density_limit_m3=limit),
            [ep_source(), vent_source()],
            AMBIENT,
            ELECTRON_TEMPERATURE_EV,
        )
        self.assertTrue(edge["compliant"])

    def test_missing_density_limit_with_traffic_is_a_finding(self):
        point = antenna_point()
        del point["plasma_density_limit_m3"]
        result = logic.assess_observation_point(
            point, [ep_source()], AMBIENT, ELECTRON_TEMPERATURE_EV
        )
        self.assertFalse(result["compliant"])
        self.assertTrue(any("no plasma-density limit" in f for f in result["findings"]))

    def test_missing_density_limit_without_traffic_is_not_a_finding(self):
        point = antenna_point(field_angle_deg=150.0)
        del point["plasma_density_limit_m3"]
        result = logic.assess_observation_point(
            point, [ep_source()], AMBIENT, ELECTRON_TEMPERATURE_EV
        )
        self.assertTrue(result["compliant"])
        self.assertEqual(result["findings"], [])

    def test_collision_dominated_near_field_is_flagged(self):
        dense = ep_source(mass_flow_kg_s=1.0, exit_velocity_m_s=1000.0)
        result = logic.assess_observation_point(
            antenna_point(distance_m=0.01, plasma_density_limit_m3=1.0e40),
            [dense],
            AMBIENT,
            ELECTRON_TEMPERATURE_EV,
        )
        self.assertEqual(result["flow_regime"], "continuum")
        self.assertTrue(
            any("free-molecular far-field" in f for f in result["findings"])
        )
        self.assertFalse(result["compliant"])

    def test_blocked_radio_link_is_flagged(self):
        result = logic.assess_observation_point(
            antenna_point(carrier_frequency_hz=1.0e3),
            [ep_source()],
            AMBIENT,
            ELECTRON_TEMPERATURE_EV,
        )
        self.assertFalse(result["compliant"])
        self.assertTrue(any("exceeds the " in f for f in result["findings"]))

    def test_clear_radio_link_is_reported_compatible(self):
        result = logic.assess_observation_point(
            antenna_point(carrier_frequency_hz=2.2e9, rf_margin_factor=5.0),
            [ep_source()],
            AMBIENT,
            ELECTRON_TEMPERATURE_EV,
        )
        self.assertTrue(result["rf"]["compatible"])
        self.assertTrue(result["compliant"])

    def test_debye_length_is_reported_when_plasma_is_present(self):
        result = logic.assess_observation_point(
            antenna_point(), [ep_source()], AMBIENT, ELECTRON_TEMPERATURE_EV
        )
        self.assertIsNotNone(result["debye_length_m"])
        self.assertGreater(result["debye_length_m"], 0.0)

    def test_non_mapping_point_rejected(self):
        with self.assertRaises(ValueError):
            logic.assess_observation_point(
                "PT-ANTENNA", [ep_source()], AMBIENT, ELECTRON_TEMPERATURE_EV
            )

    def test_missing_point_identifier_rejected(self):
        point = antenna_point()
        del point["point_id"]
        with self.assertRaises(ValueError):
            logic.assess_observation_point(
                point, [ep_source()], AMBIENT, ELECTRON_TEMPERATURE_EV
            )

    def test_zero_distance_point_rejected(self):
        with self.assertRaises(ValueError):
            logic.assess_observation_point(
                antenna_point(distance_m=0.0),
                [ep_source()],
                AMBIENT,
                ELECTRON_TEMPERATURE_EV,
            )

    def test_negative_ambient_density_rejected(self):
        with self.assertRaises(ValueError):
            logic.assess_observation_point(
                antenna_point(), [ep_source()], -1.0, ELECTRON_TEMPERATURE_EV
            )


class TestEnvironmentAssessment(unittest.TestCase):
    def test_campaign_reports_the_worst_point(self):
        near = antenna_point(point_id="PT-NEAR", distance_m=1.0)
        far = antenna_point(point_id="PT-FAR", distance_m=8.0)
        result = logic.assess_neutral_gas_environment(
            [near, far], [ep_source()], AMBIENT, ELECTRON_TEMPERATURE_EV
        )
        self.assertEqual(result["worst_point_id"], "PT-NEAR")
        self.assertTrue(result["compliant"])

    def test_campaign_aggregates_findings(self):
        good = antenna_point(point_id="PT-GOOD")
        bad = antenna_point(point_id="PT-BAD", plasma_density_limit_m3=1.0)
        result = logic.assess_neutral_gas_environment(
            [good, bad], [ep_source()], AMBIENT, ELECTRON_TEMPERATURE_EV
        )
        self.assertFalse(result["compliant"])
        self.assertTrue(any("PT-BAD" in f for f in result["findings"]))

    def test_empty_point_list_rejected(self):
        with self.assertRaises(ValueError):
            logic.assess_neutral_gas_environment(
                [], [ep_source()], AMBIENT, ELECTRON_TEMPERATURE_EV
            )

    def test_empty_source_list_rejected(self):
        with self.assertRaises(ValueError):
            logic.assess_neutral_gas_environment(
                [antenna_point()], [], AMBIENT, ELECTRON_TEMPERATURE_EV
            )


if __name__ == "__main__":
    unittest.main()
