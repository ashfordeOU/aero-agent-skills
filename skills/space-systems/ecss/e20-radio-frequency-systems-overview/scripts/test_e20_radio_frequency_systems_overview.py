#!/usr/bin/env python3
"""Gate 3 contract test for the ECSS-E-ST-20C clause 7.1 radio-frequency
systems overview leaf. Stdlib unittest, offline, deterministic."""

import math
import unittest

import e20_radio_frequency_systems_overview_logic as rf


def nominal_system():
    """A describable system with a healthy link margin."""
    return {
        "elements": [
            "travelling_wave_tube_amplifier",
            "low_noise_amplifier",
            "reflector_antenna",
            "rectangular_waveguide",
        ],
        "transmitter_power_dbw": 13.0,
        "transmit_feeder_loss_db": 1.0,
        "transmit_antenna_gain_dbi": 30.0,
        "transmit_vswr": 1.2,
        "slant_range_m": 4.0e7,
        "carrier_frequency_hz": 8.4e9,
        "receive_antenna_gain_dbi": 60.0,
        "receive_feeder_loss_db": 0.5,
        "receive_vswr": 1.3,
        "system_noise_temperature_k": 100.0,
        "required_energy_per_bit_db": 2.5,
        "data_rate_bps": 2.0e6,
    }


class ElementFamilyTests(unittest.TestCase):
    def test_transmitter_chain_element(self):
        self.assertEqual(
            rf.categorize_rf_element("travelling_wave_tube_amplifier"),
            "transmitter_chain",
        )

    def test_receiver_chain_element(self):
        self.assertEqual(rf.categorize_rf_element("low_noise_amplifier"), "receiver_chain")

    def test_antenna_element(self):
        self.assertEqual(rf.categorize_rf_element("horn_antenna"), "antenna")

    def test_transmission_line_element(self):
        self.assertEqual(rf.categorize_rf_element("rotary_joint"), "transmission_line")

    def test_hyphen_and_case_are_normalised(self):
        self.assertEqual(
            rf.categorize_rf_element("  Pre-Selection-Filter "), "receiver_chain"
        )

    def test_every_registry_entry_lands_in_a_known_family(self):
        for element_type in rf.RF_ELEMENT_FAMILIES:
            self.assertIn(rf.categorize_rf_element(element_type), rf.RF_FAMILIES)

    def test_unrecognised_element_is_rejected(self):
        with self.assertRaises(ValueError):
            rf.categorize_rf_element("star_tracker")

    def test_empty_element_type_is_rejected(self):
        with self.assertRaises(ValueError):
            rf.categorize_rf_element("   ")

    def test_non_string_element_type_is_rejected(self):
        with self.assertRaises(ValueError):
            rf.categorize_rf_element(17)


class ChainCompletenessTests(unittest.TestCase):
    def test_chain_with_all_four_families_is_complete(self):
        review = rf.review_rf_chain_completeness(
            ["modulator", "demodulator", "helix_antenna", "coaxial_cable"]
        )
        self.assertTrue(review["complete"])
        self.assertEqual(review["findings"], [])

    def test_missing_families_are_reported(self):
        review = rf.review_rf_chain_completeness(["modulator", "up_converter"])
        self.assertFalse(review["complete"])
        self.assertEqual(
            review["missing_families"],
            ["receiver_chain", "antenna", "transmission_line"],
        )
        self.assertEqual(len(review["findings"]), 3)

    def test_elements_are_grouped_under_their_family(self):
        review = rf.review_rf_chain_completeness(
            ["modulator", "up_converter", "demodulator", "patch_array_antenna", "microstrip_line"]
        )
        self.assertEqual(len(review["populated"]["transmitter_chain"]), 2)
        self.assertEqual(len(review["populated"]["antenna"]), 1)

    def test_empty_inventory_is_rejected(self):
        with self.assertRaises(ValueError):
            rf.review_rf_chain_completeness([])

    def test_string_inventory_is_rejected(self):
        with self.assertRaises(ValueError):
            rf.review_rf_chain_completeness("modulator")

    def test_unrecognised_member_is_rejected(self):
        with self.assertRaises(ValueError):
            rf.review_rf_chain_completeness(["modulator", "reaction_wheel"])


class RadiatedPowerTests(unittest.TestCase):
    def test_feeder_is_subtracted_and_gain_added(self):
        self.assertAlmostEqual(
            rf.compute_effective_isotropic_radiated_power_dbw(13.0, 1.0, 30.0), 42.0
        )

    def test_lossless_feeder_leaves_output_plus_gain(self):
        self.assertAlmostEqual(
            rf.compute_effective_isotropic_radiated_power_dbw(10.0, 0.0, 25.0), 35.0
        )

    def test_negative_feeder_loss_is_rejected(self):
        with self.assertRaises(ValueError):
            rf.compute_effective_isotropic_radiated_power_dbw(13.0, -0.5, 30.0)

    def test_non_numeric_transmitter_output_is_rejected(self):
        with self.assertRaises(ValueError):
            rf.compute_effective_isotropic_radiated_power_dbw("13", 1.0, 30.0)

    def test_non_finite_gain_is_rejected(self):
        with self.assertRaises(ValueError):
            rf.compute_effective_isotropic_radiated_power_dbw(13.0, 1.0, float("inf"))

    def test_boolean_is_not_accepted_as_a_number(self):
        with self.assertRaises(ValueError):
            rf.compute_effective_isotropic_radiated_power_dbw(True, 1.0, 30.0)


class PathLossTests(unittest.TestCase):
    def test_one_kilometre_at_one_gigahertz_matches_the_textbook_constant(self):
        # Independent form: 32.44 + 20log10(km) + 20log10(MHz).
        expected = 32.44 + 20.0 * math.log10(1.0) + 20.0 * math.log10(1000.0)
        self.assertAlmostEqual(rf.free_space_path_loss_db(1000.0, 1.0e9), expected, places=1)

    def test_doubling_the_range_adds_six_decibels(self):
        near = rf.free_space_path_loss_db(4.0e7, 8.4e9)
        far = rf.free_space_path_loss_db(8.0e7, 8.4e9)
        self.assertAlmostEqual(far - near, 6.0206, places=3)

    def test_doubling_the_frequency_adds_six_decibels(self):
        low = rf.free_space_path_loss_db(4.0e7, 4.2e9)
        high = rf.free_space_path_loss_db(4.0e7, 8.4e9)
        self.assertAlmostEqual(high - low, 6.0206, places=3)

    def test_zero_range_is_rejected(self):
        with self.assertRaises(ValueError):
            rf.free_space_path_loss_db(0.0, 8.4e9)

    def test_negative_frequency_is_rejected(self):
        with self.assertRaises(ValueError):
            rf.free_space_path_loss_db(4.0e7, -8.4e9)


class MismatchTests(unittest.TestCase):
    def test_perfect_match_costs_nothing(self):
        self.assertAlmostEqual(rf.mismatch_loss_db(1.0), 0.0)

    def test_two_to_one_ratio_costs_about_half_a_decibel(self):
        self.assertAlmostEqual(rf.mismatch_loss_db(2.0), 0.5115, places=4)

    def test_loss_grows_with_the_ratio(self):
        self.assertGreater(rf.mismatch_loss_db(3.0), rf.mismatch_loss_db(2.0))

    def test_ratio_below_unity_is_rejected(self):
        with self.assertRaises(ValueError):
            rf.mismatch_loss_db(0.9)

    def test_non_numeric_ratio_is_rejected(self):
        with self.assertRaises(ValueError):
            rf.mismatch_loss_db(None)

    def test_interface_below_the_maximum_is_acceptable(self):
        assessment = rf.assess_interface_mismatch(1.2)
        self.assertTrue(assessment["acceptable"])
        self.assertAlmostEqual(assessment["mismatch_loss_db"], 0.03604, places=5)

    def test_interface_exactly_at_the_maximum_is_acceptable(self):
        limit = rf.mismatch_loss_db(1.5)
        assessment = rf.assess_interface_mismatch(1.5, limit)
        self.assertTrue(assessment["acceptable"])

    def test_interface_above_the_maximum_is_flagged(self):
        assessment = rf.assess_interface_mismatch(2.0)
        self.assertFalse(assessment["acceptable"])

    def test_non_positive_maximum_is_rejected(self):
        with self.assertRaises(ValueError):
            rf.assess_interface_mismatch(1.2, 0.0)


class ReceivedCarrierTests(unittest.TestCase):
    def test_carrier_level_follows_the_chain(self):
        carrier = rf.compute_received_carrier_dbw(42.0, 200.0, 60.0, 0.5, 0.1)
        self.assertAlmostEqual(carrier, -98.6)

    def test_non_positive_path_loss_is_rejected(self):
        with self.assertRaises(ValueError):
            rf.compute_received_carrier_dbw(42.0, 0.0, 60.0, 0.5)

    def test_negative_additional_loss_is_rejected(self):
        with self.assertRaises(ValueError):
            rf.compute_received_carrier_dbw(42.0, 200.0, 60.0, 0.5, -0.2)

    def test_negative_receive_feeder_loss_is_rejected(self):
        with self.assertRaises(ValueError):
            rf.compute_received_carrier_dbw(42.0, 200.0, 60.0, -0.5)


class FigureOfMeritTests(unittest.TestCase):
    def test_figure_of_merit_known_value(self):
        self.assertAlmostEqual(rf.compute_figure_of_merit_db_per_k(60.0, 0.5, 100.0), 39.5)

    def test_colder_receiver_has_a_better_figure_of_merit(self):
        cold = rf.compute_figure_of_merit_db_per_k(60.0, 0.5, 50.0)
        warm = rf.compute_figure_of_merit_db_per_k(60.0, 0.5, 100.0)
        self.assertGreater(cold, warm)

    def test_zero_noise_temperature_is_rejected(self):
        with self.assertRaises(ValueError):
            rf.compute_figure_of_merit_db_per_k(60.0, 0.5, 0.0)


class NoiseDensityTests(unittest.TestCase):
    def test_available_density_from_carrier_and_temperature(self):
        density = rf.compute_carrier_to_noise_density_dbhz(-101.6, 100.0)
        self.assertAlmostEqual(density, 107.0, places=6)

    def test_warmer_receiver_lowers_the_available_density(self):
        cold = rf.compute_carrier_to_noise_density_dbhz(-101.6, 100.0)
        warm = rf.compute_carrier_to_noise_density_dbhz(-101.6, 200.0)
        self.assertAlmostEqual(cold - warm, 3.0103, places=4)

    def test_negative_noise_temperature_is_rejected(self):
        with self.assertRaises(ValueError):
            rf.compute_carrier_to_noise_density_dbhz(-101.6, -100.0)

    def test_required_density_from_rate_and_energy_per_bit(self):
        self.assertAlmostEqual(
            rf.required_carrier_to_noise_density_dbhz(2.5, 2.0e6), 65.5103, places=4
        )

    def test_required_density_adds_the_implementation_shortfall(self):
        plain = rf.required_carrier_to_noise_density_dbhz(2.5, 2.0e6)
        with_loss = rf.required_carrier_to_noise_density_dbhz(2.5, 2.0e6, 1.5)
        self.assertAlmostEqual(with_loss - plain, 1.5)

    def test_zero_data_rate_is_rejected(self):
        with self.assertRaises(ValueError):
            rf.required_carrier_to_noise_density_dbhz(2.5, 0.0)

    def test_negative_implementation_loss_is_rejected(self):
        with self.assertRaises(ValueError):
            rf.required_carrier_to_noise_density_dbhz(2.5, 2.0e6, -0.5)


class LinkMarginTests(unittest.TestCase):
    def test_margin_above_the_minimum_is_compliant(self):
        assessment = rf.assess_link_margin(107.0, 65.5)
        self.assertTrue(assessment["compliant"])
        self.assertAlmostEqual(assessment["margin_db"], 41.5)
        self.assertAlmostEqual(assessment["shortfall_db"], 0.0)

    def test_margin_exactly_at_the_minimum_is_compliant(self):
        # 64.99 - 61.99 evaluates a few units in the last place below 3.0;
        # the decibel limit is not widened, the round-off is absorbed.
        self.assertLess(64.99 - 61.99, rf.MINIMUM_LINK_MARGIN_DB)
        assessment = rf.assess_link_margin(64.99, 61.99)
        self.assertTrue(assessment["compliant"])
        self.assertAlmostEqual(assessment["shortfall_db"], 0.0)

    def test_margin_below_the_minimum_reports_the_shortfall(self):
        assessment = rf.assess_link_margin(66.5, 65.5)
        self.assertFalse(assessment["compliant"])
        self.assertAlmostEqual(assessment["shortfall_db"], 2.0)

    def test_negative_margin_is_not_compliant(self):
        assessment = rf.assess_link_margin(60.0, 65.5)
        self.assertFalse(assessment["compliant"])
        self.assertAlmostEqual(assessment["margin_db"], -5.5)

    def test_negative_minimum_margin_is_rejected(self):
        with self.assertRaises(ValueError):
            rf.assess_link_margin(107.0, 65.5, -1.0)


class SystemReviewTests(unittest.TestCase):
    def test_nominal_system_is_compliant(self):
        review = rf.review_radio_frequency_system(nominal_system())
        self.assertTrue(review["compliant"])
        self.assertEqual(review["findings"], [])
        self.assertTrue(review["chain"]["complete"])

    def test_nominal_system_link_figures(self):
        review = rf.review_radio_frequency_system(nominal_system())
        self.assertAlmostEqual(review["eirp_dbw"], 42.0)
        self.assertAlmostEqual(review["free_space_path_loss_db"], 202.9746, places=3)
        self.assertAlmostEqual(review["figure_of_merit_db_per_k"], 39.5)
        self.assertAlmostEqual(review["link_margin"]["margin_db"], 41.5046, places=3)

    def test_additional_loss_sums_both_guided_wave_interfaces(self):
        review = rf.review_radio_frequency_system(nominal_system())
        expected = rf.mismatch_loss_db(1.2) + rf.mismatch_loss_db(1.3)
        self.assertAlmostEqual(review["additional_loss_db"], expected)

    def test_high_data_rate_exhausts_the_margin(self):
        system = nominal_system()
        system["data_rate_bps"] = 5.0e10
        review = rf.review_radio_frequency_system(system)
        self.assertFalse(review["compliant"])
        self.assertTrue(any("link-margin" in f for f in review["findings"]))

    def test_missing_family_is_reported_as_a_finding(self):
        system = nominal_system()
        system["elements"] = ["travelling_wave_tube_amplifier", "reflector_antenna"]
        review = rf.review_radio_frequency_system(system)
        self.assertFalse(review["compliant"])
        self.assertFalse(review["chain"]["complete"])
        self.assertTrue(any("receiver_chain" in f for f in review["findings"]))

    def test_excessive_interface_ratio_is_reported(self):
        system = nominal_system()
        system["receive_vswr"] = 2.5
        review = rf.review_radio_frequency_system(system)
        self.assertFalse(review["receive_interface"]["acceptable"])
        self.assertTrue(any("mismatch-loss" in f for f in review["findings"]))

    def test_atmospheric_loss_is_carried_into_the_carrier_level(self):
        base = rf.review_radio_frequency_system(nominal_system())
        system = nominal_system()
        system["atmospheric_loss_db"] = 2.0
        attenuated = rf.review_radio_frequency_system(system)
        self.assertAlmostEqual(
            base["received_carrier_dbw"] - attenuated["received_carrier_dbw"], 2.0
        )

    def test_missing_required_key_is_rejected(self):
        system = nominal_system()
        del system["system_noise_temperature_k"]
        with self.assertRaises(ValueError):
            rf.review_radio_frequency_system(system)

    def test_non_mapping_system_is_rejected(self):
        with self.assertRaises(ValueError):
            rf.review_radio_frequency_system(["modulator"])

    def test_tighter_project_minimum_can_turn_a_pass_into_a_finding(self):
        system = nominal_system()
        system["minimum_margin_db"] = 45.0
        review = rf.review_radio_frequency_system(system)
        self.assertFalse(review["compliant"])


if __name__ == "__main__":
    unittest.main()
