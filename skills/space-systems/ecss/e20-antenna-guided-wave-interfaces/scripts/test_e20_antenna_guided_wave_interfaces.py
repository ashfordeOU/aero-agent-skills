"""Contract test for the ECSS-E-ST-20C 7.2.3.1 guided-wave-interface leaf.

Offline, deterministic, stdlib unittest only.
"""

import math
import unittest

from e20_antenna_guided_wave_interfaces_logic import (
    COAXIAL_NOMINAL_IMPEDANCE_OHM,
    IDEAL_RETURN_LOSS_DB,
    SPEED_OF_LIGHT_M_S,
    assess_antenna_port_set,
    assess_guided_wave_port,
    categorize_port_interface,
    coaxial_characteristic_impedance_ohm,
    coaxial_higher_order_mode_onset_hz,
    derated_power_rating_w,
    effective_peak_power_w,
    mismatch_loss_db,
    power_handling_margin_db,
    rectangular_waveguide_cutoff_hz,
    reflection_coefficient_from_vswr,
    return_loss_db,
    standing_wave_power_enhancement,
    vswr_from_reflection_coefficient,
    waveguide_single_mode_band_hz,
)

WR90_BROAD_M = 0.02286
WR90_NARROW_M = 0.01016


def waveguide_port(**overrides):
    port = {
        "id": "tx-feed-flange",
        "interface": "waveguide-flange",
        "operating_frequency_hz": 10.0e9,
        "broad_wall_m": WR90_BROAD_M,
        "narrow_wall_m": WR90_NARROW_M,
        "measured_vswr": 1.25,
        "allowable_vswr": 1.30,
        "applied_peak_power_w": 40.0,
        "rated_power_w": 400.0,
        "vacuum_derating_factor": 0.5,
        "temperature_derating_factor": 0.8,
        "required_power_margin_db": 3.0,
    }
    port.update(overrides)
    return port


def coaxial_port(**overrides):
    port = {
        "id": "rx-coax-port",
        "interface": "sma",
        "operating_frequency_hz": 10.0e9,
        "inner_radius_m": 0.001,
        "outer_radius_m": 0.0023026,
        "relative_permittivity": 1.0,
        "measured_vswr": 1.20,
        "allowable_vswr": 1.35,
        "applied_peak_power_w": 5.0,
        "rated_power_w": 100.0,
        "vacuum_derating_factor": 0.5,
        "temperature_derating_factor": 0.9,
        "required_power_margin_db": 6.0,
    }
    port.update(overrides)
    return port


class InterfaceCategorisation(unittest.TestCase):
    def test_flange_names_map_to_waveguide(self):
        self.assertEqual(
            categorize_port_interface("waveguide-flange"), "waveguide-flange"
        )
        self.assertEqual(categorize_port_interface("  WR-90 "), "waveguide-flange")

    def test_connector_names_map_to_coaxial(self):
        self.assertEqual(categorize_port_interface("sma"), "coaxial-connector")
        self.assertEqual(categorize_port_interface("Type-N"), "coaxial-connector")

    def test_uncategorized_interface_is_rejected(self):
        with self.assertRaises(ValueError):
            categorize_port_interface("optical-ferrule")

    def test_non_string_interface_is_rejected(self):
        with self.assertRaises(ValueError):
            categorize_port_interface(None)


class MismatchFigures(unittest.TestCase):
    def test_reflection_coefficient_of_a_two_to_one_mismatch(self):
        self.assertAlmostEqual(
            reflection_coefficient_from_vswr(2.0), 1.0 / 3.0, places=12
        )

    def test_matched_port_reflects_nothing(self):
        self.assertAlmostEqual(reflection_coefficient_from_vswr(1.0), 0.0, places=12)

    def test_vswr_below_unity_is_rejected(self):
        with self.assertRaises(ValueError):
            reflection_coefficient_from_vswr(0.9)

    def test_infinite_vswr_is_rejected(self):
        with self.assertRaises(ValueError):
            reflection_coefficient_from_vswr(float("inf"))

    def test_round_trip_through_the_reflection_coefficient(self):
        gamma = reflection_coefficient_from_vswr(1.45)
        self.assertAlmostEqual(vswr_from_reflection_coefficient(gamma), 1.45, places=10)

    def test_unit_reflection_coefficient_is_rejected(self):
        with self.assertRaises(ValueError):
            vswr_from_reflection_coefficient(1.0)

    def test_return_loss_of_a_two_to_one_mismatch(self):
        self.assertAlmostEqual(return_loss_db(2.0), 9.5424250944, places=8)

    def test_matched_port_reports_the_ideal_return_loss(self):
        self.assertAlmostEqual(return_loss_db(1.0), IDEAL_RETURN_LOSS_DB, places=9)

    def test_mismatch_loss_of_a_two_to_one_mismatch(self):
        self.assertAlmostEqual(mismatch_loss_db(2.0), 0.5115252245, places=8)

    def test_matched_port_loses_no_transmitted_power(self):
        self.assertAlmostEqual(mismatch_loss_db(1.0), 0.0, places=12)

    def test_standing_wave_enhancement_of_a_two_to_one_mismatch(self):
        self.assertAlmostEqual(
            standing_wave_power_enhancement(2.0), (4.0 / 3.0) ** 2, places=12
        )

    def test_effective_peak_power_uses_the_enhancement(self):
        self.assertAlmostEqual(
            effective_peak_power_w(40.0, 1.25), 40.0 * (10.0 / 9.0) ** 2, places=9
        )

    def test_zero_applied_power_is_rejected(self):
        with self.assertRaises(ValueError):
            effective_peak_power_w(0.0, 1.25)


class WaveguideModing(unittest.TestCase):
    def test_dominant_cutoff_of_a_wr90_guide(self):
        expected = SPEED_OF_LIGHT_M_S / (2.0 * WR90_BROAD_M)
        self.assertAlmostEqual(
            rectangular_waveguide_cutoff_hz(WR90_BROAD_M, WR90_NARROW_M),
            expected,
            places=3,
        )

    def test_first_higher_order_cutoff_is_twice_the_dominant(self):
        dominant = rectangular_waveguide_cutoff_hz(WR90_BROAD_M, WR90_NARROW_M, 1, 0)
        higher = rectangular_waveguide_cutoff_hz(WR90_BROAD_M, WR90_NARROW_M, 2, 0)
        self.assertAlmostEqual(higher / dominant, 2.0, places=9)

    def test_narrow_wall_wider_than_broad_wall_is_rejected(self):
        with self.assertRaises(ValueError):
            rectangular_waveguide_cutoff_hz(0.01, 0.02)

    def test_zero_order_pair_is_rejected(self):
        with self.assertRaises(ValueError):
            rectangular_waveguide_cutoff_hz(WR90_BROAD_M, WR90_NARROW_M, 0, 0)

    def test_negative_mode_order_is_rejected(self):
        with self.assertRaises(ValueError):
            rectangular_waveguide_cutoff_hz(WR90_BROAD_M, WR90_NARROW_M, -1, 0)

    def test_single_mode_band_brackets_the_dominant_cutoff(self):
        cutoff = rectangular_waveguide_cutoff_hz(WR90_BROAD_M, WR90_NARROW_M)
        lower, upper = waveguide_single_mode_band_hz(WR90_BROAD_M, WR90_NARROW_M)
        self.assertGreater(lower, cutoff)
        self.assertGreater(upper, lower)
        self.assertAlmostEqual(lower / cutoff, 1.25, places=9)


class CoaxialModing(unittest.TestCase):
    def test_air_line_geometry_gives_a_fifty_ohm_impedance(self):
        self.assertAlmostEqual(
            coaxial_characteristic_impedance_ohm(0.001, 0.0023026, 1.0),
            COAXIAL_NOMINAL_IMPEDANCE_OHM,
            places=1,
        )

    def test_dielectric_fill_lowers_the_impedance(self):
        air = coaxial_characteristic_impedance_ohm(0.001, 0.0023026, 1.0)
        ptfe = coaxial_characteristic_impedance_ohm(0.001, 0.0023026, 2.1)
        self.assertLess(ptfe, air)
        self.assertAlmostEqual(ptfe * math.sqrt(2.1), air, places=9)

    def test_outer_radius_not_larger_than_inner_is_rejected(self):
        with self.assertRaises(ValueError):
            coaxial_characteristic_impedance_ohm(0.002, 0.002, 1.0)

    def test_permittivity_below_vacuum_is_rejected(self):
        with self.assertRaises(ValueError):
            coaxial_characteristic_impedance_ohm(0.001, 0.002, 0.5)

    def test_higher_order_mode_onset_of_the_air_line(self):
        expected = SPEED_OF_LIGHT_M_S / (math.pi * (0.001 + 0.0023026))
        self.assertAlmostEqual(
            coaxial_higher_order_mode_onset_hz(0.001, 0.0023026, 1.0) / 1e9,
            expected / 1e9,
            places=6,
        )

    def test_a_larger_line_modes_at_a_lower_frequency(self):
        small = coaxial_higher_order_mode_onset_hz(0.001, 0.0023026)
        large = coaxial_higher_order_mode_onset_hz(0.002, 0.0046052)
        self.assertLess(large, small)

    def test_onset_rejects_a_degenerate_cross_section(self):
        with self.assertRaises(ValueError):
            coaxial_higher_order_mode_onset_hz(0.002, 0.001)


class PowerDerating(unittest.TestCase):
    def test_successive_factors_multiply(self):
        self.assertAlmostEqual(derated_power_rating_w(400.0, 0.5, 0.8), 160.0, places=9)

    def test_no_factors_leaves_the_rating_alone(self):
        self.assertAlmostEqual(derated_power_rating_w(400.0), 400.0, places=9)

    def test_factor_above_unity_is_rejected(self):
        with self.assertRaises(ValueError):
            derated_power_rating_w(400.0, 1.2)

    def test_zero_factor_is_rejected(self):
        with self.assertRaises(ValueError):
            derated_power_rating_w(400.0, 0.0)

    def test_zero_rating_is_rejected(self):
        with self.assertRaises(ValueError):
            derated_power_rating_w(0.0, 0.5)

    def test_margin_is_the_decibel_ratio(self):
        self.assertAlmostEqual(power_handling_margin_db(160.0, 16.0), 10.0, places=9)

    def test_overdriven_interface_has_a_negative_margin(self):
        self.assertLess(power_handling_margin_db(50.0, 100.0), 0.0)

    def test_margin_rejects_zero_applied_power(self):
        with self.assertRaises(ValueError):
            power_handling_margin_db(160.0, 0.0)


class PortAssessment(unittest.TestCase):
    def test_nominal_waveguide_port_is_compliant(self):
        result = assess_guided_wave_port(waveguide_port())
        self.assertTrue(result["compliant"])
        self.assertEqual(result["findings"], [])
        self.assertEqual(result["interface_category"], "waveguide-flange")
        self.assertAlmostEqual(result["derated_rating_w"], 160.0, places=9)
        self.assertAlmostEqual(result["power_handling_margin_db"], 5.1055, places=3)

    def test_nominal_coaxial_port_is_compliant(self):
        result = assess_guided_wave_port(coaxial_port())
        self.assertTrue(result["compliant"])
        self.assertEqual(result["interface_category"], "coaxial-connector")
        self.assertAlmostEqual(
            result["characteristic_impedance_ohm"], 50.0, places=1
        )

    def test_frequency_below_cutoff_is_flagged(self):
        result = assess_guided_wave_port(waveguide_port(operating_frequency_hz=4.0e9))
        self.assertIn(
            "operating-frequency-at-or-below-waveguide-cutoff", result["findings"]
        )

    def test_frequency_above_the_single_mode_band_is_flagged(self):
        result = assess_guided_wave_port(waveguide_port(operating_frequency_hz=14.0e9))
        self.assertIn(
            "operating-frequency-outside-single-mode-band", result["findings"]
        )

    def test_frequency_exactly_at_the_band_edge_is_in_band(self):
        lower, _ = waveguide_single_mode_band_hz(WR90_BROAD_M, WR90_NARROW_M)
        result = assess_guided_wave_port(waveguide_port(operating_frequency_hz=lower))
        self.assertNotIn(
            "operating-frequency-outside-single-mode-band", result["findings"]
        )

    def test_coaxial_port_above_its_mode_onset_is_flagged(self):
        result = assess_guided_wave_port(coaxial_port(operating_frequency_hz=40.0e9))
        self.assertIn(
            "operating-frequency-above-higher-order-mode-onset", result["findings"]
        )

    def test_frequency_exactly_at_the_mode_onset_is_accepted(self):
        onset = coaxial_higher_order_mode_onset_hz(0.001, 0.0023026, 1.0)
        result = assess_guided_wave_port(coaxial_port(operating_frequency_hz=onset))
        self.assertNotIn(
            "operating-frequency-above-higher-order-mode-onset", result["findings"]
        )

    def test_dielectric_fill_pushes_the_impedance_out_of_tolerance(self):
        result = assess_guided_wave_port(coaxial_port(relative_permittivity=2.1))
        self.assertIn("characteristic-impedance-outside-tolerance", result["findings"])

    def test_vswr_above_the_allowable_is_flagged(self):
        result = assess_guided_wave_port(waveguide_port(measured_vswr=1.6))
        self.assertIn("measured-vswr-exceeds-allowable", result["findings"])

    def test_vswr_exactly_at_the_allowable_is_compliant(self):
        result = assess_guided_wave_port(waveguide_port(measured_vswr=1.30))
        self.assertNotIn("measured-vswr-exceeds-allowable", result["findings"])

    def test_missing_allowable_vswr_is_itself_a_finding(self):
        port = waveguide_port()
        del port["allowable_vswr"]
        result = assess_guided_wave_port(port)
        self.assertIn("no-allowable-vswr-on-record", result["findings"])

    def test_missing_measured_vswr_is_rejected(self):
        port = waveguide_port()
        del port["measured_vswr"]
        with self.assertRaises(ValueError):
            assess_guided_wave_port(port)

    def test_overdriven_port_fails_the_power_margin(self):
        result = assess_guided_wave_port(waveguide_port(applied_peak_power_w=150.0))
        self.assertIn("power-handling-margin-below-required", result["findings"])
        self.assertFalse(result["compliant"])

    def test_margin_exactly_at_the_required_value_is_compliant(self):
        baseline = assess_guided_wave_port(waveguide_port())
        tight = assess_guided_wave_port(
            waveguide_port(
                required_power_margin_db=baseline["power_handling_margin_db"]
            )
        )
        self.assertNotIn("power-handling-margin-below-required", tight["findings"])
        self.assertTrue(tight["compliant"])

    def test_port_without_an_id_is_rejected(self):
        port = waveguide_port()
        del port["id"]
        with self.assertRaises(ValueError):
            assess_guided_wave_port(port)

    def test_non_mapping_port_is_rejected(self):
        with self.assertRaises(ValueError):
            assess_guided_wave_port("tx-feed-flange")

    def test_zero_operating_frequency_is_rejected(self):
        with self.assertRaises(ValueError):
            assess_guided_wave_port(waveguide_port(operating_frequency_hz=0.0))


class PortSetAssessment(unittest.TestCase):
    def test_a_compliant_set_reports_the_worst_margin(self):
        result = assess_antenna_port_set([waveguide_port(), coaxial_port()])
        self.assertTrue(result["compliant"])
        self.assertEqual(result["non_compliant_ports"], [])
        margins = [p["power_handling_margin_db"] for p in result["ports"]]
        self.assertAlmostEqual(
            result["worst_power_handling_margin_db"], min(margins), places=12
        )

    def test_one_bad_port_sinks_the_set(self):
        result = assess_antenna_port_set(
            [waveguide_port(measured_vswr=1.9), coaxial_port()]
        )
        self.assertFalse(result["compliant"])
        self.assertEqual(result["non_compliant_ports"], ["tx-feed-flange"])

    def test_duplicate_port_ids_are_rejected(self):
        with self.assertRaises(ValueError):
            assess_antenna_port_set([waveguide_port(), waveguide_port()])

    def test_empty_port_list_is_rejected(self):
        with self.assertRaises(ValueError):
            assess_antenna_port_set([])


if __name__ == "__main__":
    unittest.main()
