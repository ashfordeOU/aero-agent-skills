#!/usr/bin/env python3
"""Contract test for the clause 7.2.2.3.5 antenna feed-chain leaf.

stdlib unittest, offline, deterministic. Run: python3 test_e20_antenna_rf_chain_characterisation.py
"""

import math
import unittest

from e20_antenna_rf_chain_characterisation_logic import (
    STANDARD_PHYSICAL_TEMPERATURE_K,
    _ge,
    _le,
    assess_rf_chain,
    cascade_insertion_loss_db,
    cascade_noise_temperature_k,
    categorize_stage,
    chain_group_delay_ns,
    figure_of_merit_penalty_db,
    forward_power_profile,
    group_delay_ripple_ns,
    input_port_reflection,
    input_port_standing_wave_ratio,
    mismatch_ripple_db,
    power_handling_margins,
    reflection_from_return_loss,
    stage_loss_factor,
    validate_chain,
    worst_interface_ripple,
)


def transmit_chain():
    return [
        {
            "id": "WR-01",
            "kind": "waveguide-run",
            "insertion_loss_db": 0.15,
            "return_loss_db": 28.0,
            "power_rating_w": 500.0,
            "group_delay_ns": 3.0,
            "group_delay_ripple_ns": 0.2,
        },
        {
            "id": "FL-01",
            "kind": "filter",
            "insertion_loss_db": 0.25,
            "return_loss_db": 26.0,
            "power_rating_w": 400.0,
            "group_delay_ns": 8.0,
            "group_delay_ripple_ns": 0.5,
        },
        {
            "id": "OMT-01",
            "kind": "orthomode-transducer",
            "insertion_loss_db": 0.12,
            "return_loss_db": 30.0,
            "power_rating_w": 600.0,
            "group_delay_ns": 1.5,
            "group_delay_ripple_ns": 0.1,
        },
        {
            "id": "RJ-01",
            "kind": "rotary-joint",
            "insertion_loss_db": 0.20,
            "return_loss_db": 28.0,
            "power_rating_w": 450.0,
            "group_delay_ns": 2.0,
            "group_delay_ripple_ns": 0.3,
        },
    ]


def receive_chain():
    return [
        {
            "id": "WR-02",
            "kind": "waveguide-run",
            "insertion_loss_db": 0.15,
            "return_loss_db": 28.0,
            "group_delay_ns": 3.0,
            "group_delay_ripple_ns": 0.2,
        },
        {
            "id": "OMT-02",
            "kind": "orthomode-transducer",
            "insertion_loss_db": 0.12,
            "return_loss_db": 30.0,
            "group_delay_ns": 1.5,
            "group_delay_ripple_ns": 0.1,
        },
    ]


class StageValidationTests(unittest.TestCase):
    def test_known_stage_kind_is_categorized(self):
        self.assertEqual(categorize_stage(transmit_chain()[1]), "filter")

    def test_unknown_stage_kind_rejected(self):
        stage = transmit_chain()[0]
        stage["kind"] = "amplifier"
        with self.assertRaises(ValueError):
            categorize_stage(stage)

    def test_stage_without_id_rejected(self):
        stage = transmit_chain()[0]
        del stage["id"]
        with self.assertRaises(ValueError):
            categorize_stage(stage)

    def test_stage_with_gain_rejected(self):
        stage = transmit_chain()[0]
        stage["insertion_loss_db"] = -0.5
        with self.assertRaises(ValueError):
            categorize_stage(stage)

    def test_absurdly_lossy_stage_rejected(self):
        stage = transmit_chain()[0]
        stage["insertion_loss_db"] = 60.0
        with self.assertRaises(ValueError):
            categorize_stage(stage)

    def test_stage_without_return_loss_rejected(self):
        stage = transmit_chain()[0]
        del stage["return_loss_db"]
        with self.assertRaises(ValueError):
            categorize_stage(stage)

    def test_non_mapping_stage_rejected(self):
        with self.assertRaises(ValueError):
            categorize_stage("WR-01")

    def test_chain_kinds_returned_in_order(self):
        self.assertEqual(
            validate_chain(transmit_chain()),
            ["waveguide-run", "filter", "orthomode-transducer", "rotary-joint"],
        )

    def test_empty_chain_rejected(self):
        with self.assertRaises(ValueError):
            validate_chain([])

    def test_non_list_chain_rejected(self):
        with self.assertRaises(ValueError):
            validate_chain({"id": "WR-01"})

    def test_duplicate_stage_id_rejected(self):
        chain = transmit_chain()
        chain[1]["id"] = "WR-01"
        with self.assertRaises(ValueError):
            validate_chain(chain)


class ScalarConversionTests(unittest.TestCase):
    def test_twenty_db_return_loss_is_a_tenth(self):
        self.assertAlmostEqual(reflection_from_return_loss(20.0), 0.1, places=12)

    def test_return_loss_improves_the_match(self):
        self.assertLess(reflection_from_return_loss(30.0), reflection_from_return_loss(20.0))

    def test_zero_return_loss_rejected(self):
        with self.assertRaises(ValueError):
            reflection_from_return_loss(0.0)

    def test_negative_return_loss_rejected(self):
        with self.assertRaises(ValueError):
            reflection_from_return_loss(-10.0)

    def test_non_numeric_return_loss_rejected(self):
        with self.assertRaises(ValueError):
            reflection_from_return_loss("20 dB")

    def test_three_db_stage_halves_the_through_signal(self):
        self.assertAlmostEqual(stage_loss_factor(10.0 * math.log10(2.0)), 2.0, places=12)

    def test_lossless_stage_has_unit_factor(self):
        self.assertAlmostEqual(stage_loss_factor(0.0), 1.0, places=12)

    def test_negative_insertion_loss_rejected(self):
        with self.assertRaises(ValueError):
            stage_loss_factor(-0.1)


class CascadeTests(unittest.TestCase):
    def test_insertion_loss_is_the_sum_of_the_stages(self):
        self.assertAlmostEqual(cascade_insertion_loss_db(transmit_chain()), 0.72, places=12)

    def test_noise_temperature_matches_the_single_loss_identity(self):
        chain = transmit_chain()
        total_factor = 10.0 ** (cascade_insertion_loss_db(chain) / 10.0)
        expected = (total_factor - 1.0) * STANDARD_PHYSICAL_TEMPERATURE_K
        self.assertAlmostEqual(cascade_noise_temperature_k(chain), expected, places=9)

    def test_lossless_chain_adds_no_noise(self):
        chain = receive_chain()
        for stage in chain:
            stage["insertion_loss_db"] = 0.0
        self.assertAlmostEqual(cascade_noise_temperature_k(chain), 0.0, places=12)

    def test_colder_hardware_adds_less_noise(self):
        chain = receive_chain()
        self.assertLess(
            cascade_noise_temperature_k(chain, 150.0), cascade_noise_temperature_k(chain, 290.0)
        )

    def test_zero_physical_temperature_rejected(self):
        with self.assertRaises(ValueError):
            cascade_noise_temperature_k(receive_chain(), 0.0)

    def test_negative_physical_temperature_rejected(self):
        with self.assertRaises(ValueError):
            cascade_noise_temperature_k(receive_chain(), -20.0)


class MismatchTests(unittest.TestCase):
    def test_ripple_between_two_tenth_reflections(self):
        expected = 20.0 * math.log10(1.01 / 0.99)
        self.assertAlmostEqual(mismatch_ripple_db(0.1, 0.1), expected, places=12)

    def test_a_perfect_interface_ripples_nothing(self):
        self.assertAlmostEqual(mismatch_ripple_db(0.0, 0.2), 0.0, places=12)

    def test_total_reflection_rejected(self):
        with self.assertRaises(ValueError):
            mismatch_ripple_db(1.0, 0.2)

    def test_worst_interface_is_reported_with_its_pair(self):
        result = worst_interface_ripple(transmit_chain())
        self.assertEqual(result["pair"], ("WR-01", "FL-01"))
        self.assertGreater(result["ripple_db"], 0.0)

    def test_single_stage_chain_has_no_interface(self):
        result = worst_interface_ripple(transmit_chain()[:1])
        self.assertIsNone(result["pair"])
        self.assertAlmostEqual(result["ripple_db"], 0.0, places=12)

    def test_input_reflection_of_a_single_stage(self):
        chain = [
            {
                "id": "WR-01",
                "kind": "waveguide-run",
                "insertion_loss_db": 0.0,
                "return_loss_db": 20.0,
            }
        ]
        self.assertAlmostEqual(input_port_reflection(chain), 0.1, places=12)

    def test_a_deep_stage_contributes_through_the_round_trip_loss(self):
        chain = [
            {
                "id": "WR-01",
                "kind": "waveguide-run",
                "insertion_loss_db": 10.0,
                "return_loss_db": 20.0,
            },
            {
                "id": "FL-01",
                "kind": "filter",
                "insertion_loss_db": 0.0,
                "return_loss_db": 20.0,
            },
        ]
        self.assertAlmostEqual(input_port_reflection(chain), 0.11, places=12)

    def test_standing_wave_ratio_from_the_input_reflection(self):
        chain = [
            {
                "id": "WR-01",
                "kind": "waveguide-run",
                "insertion_loss_db": 0.0,
                "return_loss_db": 20.0,
            }
        ]
        self.assertAlmostEqual(input_port_standing_wave_ratio(chain), 1.1 / 0.9, places=12)

    def test_an_impossible_chain_match_is_rejected(self):
        chain = [
            {
                "id": "S%d" % index,
                "kind": "filter",
                "insertion_loss_db": 0.0,
                "return_loss_db": 3.0,
            }
            for index in range(4)
        ]
        with self.assertRaises(ValueError):
            input_port_standing_wave_ratio(chain)


class TransmitHandlingTests(unittest.TestCase):
    def test_first_stage_sees_the_full_forward_power(self):
        profile = dict(forward_power_profile(transmit_chain(), 200.0))
        self.assertAlmostEqual(profile["WR-01"], 200.0, places=12)

    def test_downstream_stage_sees_the_attenuated_forward_power(self):
        chain = transmit_chain()
        chain[0]["insertion_loss_db"] = 10.0
        profile = dict(forward_power_profile(chain, 100.0))
        self.assertAlmostEqual(profile["FL-01"], 10.0, places=12)

    def test_zero_input_power_rejected(self):
        with self.assertRaises(ValueError):
            forward_power_profile(transmit_chain(), 0.0)

    def test_negative_input_power_rejected(self):
        with self.assertRaises(ValueError):
            forward_power_profile(transmit_chain(), -50.0)

    def test_handling_margin_value(self):
        chain = transmit_chain()[:1]
        chain[0]["power_rating_w"] = 400.0
        margins = power_handling_margins(chain, 200.0)
        self.assertEqual(len(margins), 1)
        self.assertAlmostEqual(margins[0]["margin_db"], 10.0 * math.log10(2.0), places=12)

    def test_stage_without_a_rating_is_not_graded(self):
        chain = transmit_chain()
        del chain[0]["power_rating_w"]
        margins = power_handling_margins(chain, 200.0)
        self.assertEqual(len(margins), 3)

    def test_zero_rating_rejected(self):
        chain = transmit_chain()
        chain[0]["power_rating_w"] = 0.0
        with self.assertRaises(ValueError):
            power_handling_margins(chain, 200.0)


class DelayTests(unittest.TestCase):
    def test_chain_delay_is_the_sum_of_the_stages(self):
        self.assertAlmostEqual(chain_group_delay_ns(transmit_chain()), 14.5, places=12)

    def test_absent_delay_counts_as_zero(self):
        chain = receive_chain()
        for stage in chain:
            del stage["group_delay_ns"]
        self.assertAlmostEqual(chain_group_delay_ns(chain), 0.0, places=12)

    def test_negative_delay_rejected(self):
        chain = receive_chain()
        chain[0]["group_delay_ns"] = -1.0
        with self.assertRaises(ValueError):
            chain_group_delay_ns(chain)

    def test_delay_ripple_combines_as_a_root_sum_square(self):
        expected = math.sqrt(0.2 ** 2 + 0.5 ** 2 + 0.1 ** 2 + 0.3 ** 2)
        self.assertAlmostEqual(group_delay_ripple_ns(transmit_chain()), expected, places=12)

    def test_negative_delay_ripple_rejected(self):
        chain = receive_chain()
        chain[0]["group_delay_ripple_ns"] = -0.2
        with self.assertRaises(ValueError):
            group_delay_ripple_ns(chain)


class FigureOfMeritTests(unittest.TestCase):
    def test_a_lossless_chain_costs_nothing(self):
        chain = receive_chain()
        for stage in chain:
            stage["insertion_loss_db"] = 0.0
        self.assertAlmostEqual(figure_of_merit_penalty_db(chain, 50.0, 120.0), 0.0, places=12)

    def test_the_penalty_exceeds_the_bare_dissipation(self):
        chain = receive_chain()
        penalty = figure_of_merit_penalty_db(chain, 50.0, 120.0)
        self.assertGreater(penalty, cascade_insertion_loss_db(chain))

    def test_a_longer_chain_costs_more(self):
        short = figure_of_merit_penalty_db(receive_chain(), 50.0, 120.0)
        long_chain = figure_of_merit_penalty_db(transmit_chain(), 50.0, 120.0)
        self.assertGreater(long_chain, short)

    def test_zero_antenna_noise_temperature_rejected(self):
        with self.assertRaises(ValueError):
            figure_of_merit_penalty_db(receive_chain(), 0.0, 120.0)

    def test_zero_receiver_noise_temperature_rejected(self):
        with self.assertRaises(ValueError):
            figure_of_merit_penalty_db(receive_chain(), 50.0, 0.0)


class AssessmentTests(unittest.TestCase):
    def transmit_config(self):
        return {"chain": transmit_chain(), "direction": "transmit", "input_power_w": 200.0}

    def receive_config(self):
        return {
            "chain": receive_chain(),
            "direction": "receive",
            "antenna_noise_temperature_k": 50.0,
            "receiver_noise_temperature_k": 120.0,
        }

    def test_transmit_chain_is_compliant(self):
        result = assess_rf_chain(self.transmit_config())
        self.assertTrue(result["compliant"])
        self.assertEqual(result["findings"], [])

    def test_receive_chain_is_compliant(self):
        result = assess_rf_chain(self.receive_config())
        self.assertTrue(result["compliant"])
        self.assertIsNotNone(result["figure_of_merit_penalty_db"])

    def test_transmit_assessment_skips_the_figure_of_merit(self):
        result = assess_rf_chain(self.transmit_config())
        self.assertIsNone(result["figure_of_merit_penalty_db"])
        self.assertEqual(len(result["power_handling_margins"]), 4)

    def test_stage_kinds_are_reported_per_stage(self):
        result = assess_rf_chain(self.transmit_config())
        self.assertEqual(result["stage_kinds"]["OMT-01"], "orthomode-transducer")

    def test_raising_the_forward_power_breaks_the_handling_margin(self):
        config = self.transmit_config()
        config["input_power_w"] = 400.0
        result = assess_rf_chain(config)
        self.assertFalse(result["compliant"])
        self.assertTrue(any("handling margin" in finding for finding in result["findings"]))

    def test_a_lossy_chain_breaks_the_insertion_loss_allocation(self):
        config = self.transmit_config()
        config["chain"][1]["insertion_loss_db"] = 2.0
        result = assess_rf_chain(config)
        self.assertFalse(result["compliant"])
        self.assertTrue(any("insertion loss" in finding for finding in result["findings"]))

    def test_a_long_receive_chain_breaks_the_figure_of_merit_allocation(self):
        config = self.receive_config()
        config["chain"] = transmit_chain()
        result = assess_rf_chain(config)
        self.assertFalse(result["compliant"])
        self.assertTrue(
            any("figure-of-merit" in finding for finding in result["findings"])
        )

    def test_a_poorly_matched_chain_breaks_the_standing_wave_allocation(self):
        config = self.receive_config()
        for stage in config["chain"]:
            stage["return_loss_db"] = 10.0
        result = assess_rf_chain(config)
        self.assertFalse(result["compliant"])
        self.assertTrue(
            any("standing-wave-ratio" in finding for finding in result["findings"])
        )

    def test_a_rippling_interface_is_reported(self):
        config = self.receive_config()
        for stage in config["chain"]:
            stage["return_loss_db"] = 12.0
        config["limits"] = {"max_input_standing_wave_ratio": 9.0, "max_interface_ripple_db": 0.1}
        result = assess_rf_chain(config)
        self.assertTrue(any("ripples" in finding for finding in result["findings"]))

    def test_a_delay_ripple_exceedance_is_reported(self):
        config = self.receive_config()
        config["chain"][0]["group_delay_ripple_ns"] = 5.0
        result = assess_rf_chain(config)
        self.assertTrue(any("delay ripple" in finding for finding in result["findings"]))

    def test_unknown_direction_rejected(self):
        config = self.transmit_config()
        config["direction"] = "duplex"
        with self.assertRaises(ValueError):
            assess_rf_chain(config)

    def test_transmit_assessment_without_forward_power_rejected(self):
        config = self.transmit_config()
        del config["input_power_w"]
        with self.assertRaises(ValueError):
            assess_rf_chain(config)

    def test_unknown_allocation_key_rejected(self):
        config = self.transmit_config()
        config["limits"] = {"max_loss": 1.0}
        with self.assertRaises(ValueError):
            assess_rf_chain(config)

    def test_non_mapping_limits_rejected(self):
        config = self.transmit_config()
        config["limits"] = ["max_insertion_loss_db"]
        with self.assertRaises(ValueError):
            assess_rf_chain(config)

    def test_non_mapping_config_rejected(self):
        with self.assertRaises(ValueError):
            assess_rf_chain(transmit_chain())

    def test_tightened_allocation_turns_a_pass_into_a_finding(self):
        config = self.transmit_config()
        config["limits"] = {"max_insertion_loss_db": 0.5}
        result = assess_rf_chain(config)
        self.assertFalse(result["compliant"])


class ToleranceTests(unittest.TestCase):
    def test_representation_error_does_not_break_an_equal_budget(self):
        self.assertTrue(_le(0.1 + 0.2, 0.3))
        self.assertTrue(_ge(0.3, 0.1 + 0.2))

    def test_a_real_exceedance_is_still_caught(self):
        self.assertFalse(_le(0.31, 0.3))
        self.assertFalse(_ge(0.29, 0.3))


if __name__ == "__main__":
    unittest.main()
