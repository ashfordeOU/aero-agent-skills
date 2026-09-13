#!/usr/bin/env python3
"""Gate 3 contract test for the ECSS-E-ST-20C clause 7.2.2.3.4
beam-forming-network characterisation logic. Stdlib unittest, offline,
deterministic."""

import math
import unittest

from e20_beam_forming_network_characterisation_logic import (
    BUDGET_TOLERANCE_DB,
    assess_beam_forming_network,
    beam_pointing_shift_deg,
    categorize_network_topology,
    excitation_error_statistics,
    gain_loss_from_errors,
    input_port_match,
    insertion_loss_budget,
    phase_quantisation_effects,
    realized_excitations,
)


def uniform_commanded(count, amplitude_db=0.0, phase_deg=0.0):
    return [{"amplitude_db": amplitude_db, "phase_deg": phase_deg} for _ in range(count)]


def clean_paths(count):
    return [{} for _ in range(count)]


class TopologyCategoryTests(unittest.TestCase):
    def test_corporate_tree_is_corporate_family(self):
        self.assertEqual(
            categorize_network_topology("corporate_divider_tree"), "corporate"
        )

    def test_series_feed_is_series_family(self):
        self.assertEqual(
            categorize_network_topology("series_travelling_wave_feed"), "series"
        )

    def test_butler_matrix_is_matrix_family(self):
        self.assertEqual(categorize_network_topology("butler_matrix"), "matrix")

    def test_switched_lens_is_switched_family(self):
        self.assertEqual(
            categorize_network_topology("switched_lens_network"), "switched"
        )

    def test_topology_lookup_ignores_case_and_padding(self):
        self.assertEqual(categorize_network_topology("  Butler_Matrix "), "matrix")

    def test_unknown_topology_is_rejected(self):
        with self.assertRaises(ValueError):
            categorize_network_topology("magic_beam_box")

    def test_empty_topology_is_rejected(self):
        with self.assertRaises(ValueError):
            categorize_network_topology("   ")

    def test_non_string_topology_is_rejected(self):
        with self.assertRaises(ValueError):
            categorize_network_topology(7)


class RealizedExcitationTests(unittest.TestCase):
    def test_clean_paths_reproduce_the_commanded_drive(self):
        out = realized_excitations(uniform_commanded(4, -3.0, 30.0), clean_paths(4))
        self.assertEqual(len(out), 4)
        for item in out:
            self.assertAlmostEqual(item["amplitude_db"], -3.0)
            self.assertAlmostEqual(item["phase_deg"], 30.0)

    def test_insertion_loss_subtracts_from_the_element_amplitude(self):
        out = realized_excitations(
            uniform_commanded(2), [{"insertion_loss_db": 1.5}, {"insertion_loss_db": 2.5}]
        )
        self.assertAlmostEqual(out[0]["amplitude_db"], -1.5)
        self.assertAlmostEqual(out[1]["amplitude_db"], -2.5)

    def test_linear_amplitude_follows_the_decibel_value(self):
        out = realized_excitations(uniform_commanded(1, -6.0), clean_paths(1))
        self.assertAlmostEqual(out[0]["amplitude_linear"], 10.0 ** (-0.3), places=9)

    def test_phase_is_folded_into_the_half_open_interval(self):
        out = realized_excitations(
            [{"amplitude_db": 0.0, "phase_deg": 170.0}], [{"phase_error_deg": 30.0}]
        )
        self.assertAlmostEqual(out[0]["phase_deg"], -160.0)

    def test_length_mismatch_is_rejected(self):
        with self.assertRaises(ValueError):
            realized_excitations(uniform_commanded(3), clean_paths(2))

    def test_empty_commanded_sequence_is_rejected(self):
        with self.assertRaises(ValueError):
            realized_excitations([], [])

    def test_negative_insertion_loss_is_rejected(self):
        with self.assertRaises(ValueError):
            realized_excitations(uniform_commanded(1), [{"insertion_loss_db": -0.2}])

    def test_non_mapping_entry_is_rejected(self):
        with self.assertRaises(ValueError):
            realized_excitations([("amplitude_db", 0.0)], clean_paths(1))

    def test_non_numeric_amplitude_is_rejected(self):
        with self.assertRaises(ValueError):
            realized_excitations([{"amplitude_db": "0 dB"}], clean_paths(1))


class ExcitationStatisticTests(unittest.TestCase):
    def test_error_free_network_has_zero_statistics(self):
        stats = excitation_error_statistics(
            realized_excitations(uniform_commanded(8), clean_paths(8))
        )
        self.assertEqual(stats["element_count"], 8)
        self.assertAlmostEqual(stats["rms_amplitude_error_db"], 0.0)
        self.assertAlmostEqual(stats["residual_rms_phase_error_deg"], 0.0)
        self.assertAlmostEqual(stats["phase_slope_deg_per_element"], 0.0)

    def test_uniform_loss_is_an_offset_not_an_excitation_error(self):
        paths = [{"insertion_loss_db": 2.0} for _ in range(6)]
        stats = excitation_error_statistics(
            realized_excitations(uniform_commanded(6), paths)
        )
        self.assertAlmostEqual(stats["common_amplitude_offset_db"], -2.0)
        self.assertAlmostEqual(stats["rms_amplitude_error_db"], 0.0)
        self.assertAlmostEqual(stats["rms_relative_amplitude_error"], 0.0)

    def test_linear_phase_gradient_is_captured_as_a_slope(self):
        paths = [{"phase_error_deg": 5.0 * i} for i in range(5)]
        stats = excitation_error_statistics(
            realized_excitations(uniform_commanded(5), paths)
        )
        self.assertAlmostEqual(stats["phase_slope_deg_per_element"], 5.0, places=9)
        self.assertAlmostEqual(stats["residual_rms_phase_error_deg"], 0.0, places=9)

    def test_alternating_phase_error_is_residual_not_slope(self):
        paths = [{"phase_error_deg": 4.0 if i % 2 == 0 else -4.0} for i in range(4)]
        stats = excitation_error_statistics(
            realized_excitations(uniform_commanded(4), paths)
        )
        self.assertAlmostEqual(abs(stats["phase_slope_deg_per_element"]), 1.6, places=9)
        self.assertGreater(stats["residual_rms_phase_error_deg"], 3.0)

    def test_single_element_network_reports_no_slope(self):
        stats = excitation_error_statistics(
            realized_excitations(uniform_commanded(1), [{"phase_error_deg": 12.0}])
        )
        self.assertAlmostEqual(stats["phase_slope_deg_per_element"], 0.0)

    def test_amplitude_scatter_produces_a_relative_error(self):
        paths = [{"amplitude_error_db": 1.0}, {"amplitude_error_db": -1.0}]
        stats = excitation_error_statistics(
            realized_excitations(uniform_commanded(2), paths)
        )
        self.assertGreater(stats["rms_relative_amplitude_error"], 0.10)
        self.assertAlmostEqual(stats["rms_amplitude_error_db"], 1.0, places=9)

    def test_empty_realized_sequence_is_rejected(self):
        with self.assertRaises(ValueError):
            excitation_error_statistics([])

    def test_realized_entry_missing_commanded_reference_is_rejected(self):
        with self.assertRaises(ValueError):
            excitation_error_statistics([{"amplitude_db": 0.0, "phase_deg": 0.0}])


class GainLossTests(unittest.TestCase):
    def test_no_error_means_no_gain_loss(self):
        self.assertAlmostEqual(gain_loss_from_errors(0.0, 0.0), 0.0)

    def test_phase_error_follows_the_ruze_exponential(self):
        sigma = math.radians(20.0)
        expected = -10.0 * math.log10(math.exp(-sigma * sigma))
        self.assertAlmostEqual(gain_loss_from_errors(0.0, 20.0), expected, places=12)

    def test_amplitude_error_costs_efficiency(self):
        expected = -10.0 * math.log10(1.0 / (1.0 + 0.1 * 0.1))
        self.assertAlmostEqual(gain_loss_from_errors(0.1, 0.0), expected, places=12)

    def test_gain_loss_grows_with_phase_error(self):
        self.assertGreater(
            gain_loss_from_errors(0.0, 30.0), gain_loss_from_errors(0.0, 10.0)
        )

    def test_negative_amplitude_error_is_rejected(self):
        with self.assertRaises(ValueError):
            gain_loss_from_errors(-0.01, 5.0)

    def test_negative_phase_error_is_rejected(self):
        with self.assertRaises(ValueError):
            gain_loss_from_errors(0.0, -5.0)


class QuantisationTests(unittest.TestCase):
    def test_four_bit_shifter_step_and_residual(self):
        result = phase_quantisation_effects(4)
        self.assertEqual(result["state_count"], 16)
        self.assertAlmostEqual(result["least_significant_step_deg"], 22.5)
        self.assertAlmostEqual(
            result["residual_rms_phase_error_deg"], 22.5 / math.sqrt(12.0), places=12
        )

    def test_quantisation_lobe_drops_six_decibels_per_bit(self):
        five = phase_quantisation_effects(5)["peak_quantisation_lobe_db"]
        six = phase_quantisation_effects(6)["peak_quantisation_lobe_db"]
        self.assertAlmostEqual(five - six, 20.0 * math.log10(2.0), places=12)

    def test_more_bits_cost_less_gain(self):
        self.assertLess(
            phase_quantisation_effects(6)["gain_loss_db"],
            phase_quantisation_effects(3)["gain_loss_db"],
        )

    def test_zero_bits_is_rejected(self):
        with self.assertRaises(ValueError):
            phase_quantisation_effects(0)

    def test_excessive_bit_count_is_rejected(self):
        with self.assertRaises(ValueError):
            phase_quantisation_effects(64)

    def test_boolean_bit_count_is_rejected(self):
        with self.assertRaises(ValueError):
            phase_quantisation_effects(True)

    def test_fractional_bit_count_is_rejected(self):
        with self.assertRaises(ValueError):
            phase_quantisation_effects(4.5)


class PointingTests(unittest.TestCase):
    def test_no_gradient_means_no_shift(self):
        self.assertAlmostEqual(beam_pointing_shift_deg(0.0, 0.5), 0.0)

    def test_half_wavelength_spacing_gradient_matches_the_closed_form(self):
        expected = math.degrees(math.asin(math.radians(18.0) / math.pi))
        self.assertAlmostEqual(beam_pointing_shift_deg(18.0, 0.5), expected, places=12)

    def test_shift_is_measured_from_the_commanded_scan_angle(self):
        shift = beam_pointing_shift_deg(9.0, 0.5, 30.0)
        self.assertGreater(shift, 0.0)
        self.assertLess(shift, 5.0)

    def test_negative_gradient_shifts_the_other_way(self):
        self.assertAlmostEqual(
            beam_pointing_shift_deg(-18.0, 0.5), -beam_pointing_shift_deg(18.0, 0.5)
        )

    def test_zero_spacing_is_rejected(self):
        with self.assertRaises(ValueError):
            beam_pointing_shift_deg(5.0, 0.0)

    def test_scan_angle_beyond_the_hemisphere_is_rejected(self):
        with self.assertRaises(ValueError):
            beam_pointing_shift_deg(5.0, 0.5, 120.0)

    def test_gradient_driving_the_beam_invisible_is_rejected(self):
        with self.assertRaises(ValueError):
            beam_pointing_shift_deg(400.0, 0.5, 80.0)


class InsertionLossBudgetTests(unittest.TestCase):
    def test_stages_sum_and_leave_margin(self):
        budget = insertion_loss_budget(
            [
                {"name": "divider", "loss_db": 0.6},
                {"name": "phase-shifter", "loss_db": 1.2},
                {"name": "line", "loss_db": 0.4},
            ],
            2.5,
        )
        self.assertAlmostEqual(budget["total_loss_db"], 2.2)
        self.assertAlmostEqual(budget["margin_db"], 0.3)
        self.assertTrue(budget["compliant"])

    def test_exact_allocation_from_summed_terms_stays_compliant(self):
        # 0.1 + 0.1 + 0.1 lands a few ULPs above 0.3 in binary floating
        # point; the hardware is exactly on allocation, so the comparison
        # absorbs the representation error without widening the limit.
        stages = [{"loss_db": 0.1} for _ in range(3)]
        self.assertGreater(sum(s["loss_db"] for s in stages), 0.3)
        budget = insertion_loss_budget(stages, 0.3)
        self.assertTrue(budget["compliant"])
        self.assertLessEqual(abs(budget["margin_db"]), BUDGET_TOLERANCE_DB)

    def test_overspend_is_reported(self):
        budget = insertion_loss_budget([{"loss_db": 3.0}], 2.5)
        self.assertFalse(budget["compliant"])
        self.assertAlmostEqual(budget["margin_db"], -0.5)

    def test_empty_stage_list_is_rejected(self):
        with self.assertRaises(ValueError):
            insertion_loss_budget([], 1.0)

    def test_negative_stage_loss_is_rejected(self):
        with self.assertRaises(ValueError):
            insertion_loss_budget([{"loss_db": -0.1}], 1.0)

    def test_negative_allocation_is_rejected(self):
        with self.assertRaises(ValueError):
            insertion_loss_budget([{"loss_db": 0.1}], -1.0)

    def test_missing_loss_value_is_rejected(self):
        with self.assertRaises(ValueError):
            insertion_loss_budget([{"name": "divider"}], 1.0)


class InputMatchTests(unittest.TestCase):
    def test_identical_reflections_add_coherently(self):
        match = input_port_match(
            [{"magnitude": 0.1, "phase_deg": 0.0} for _ in range(4)], 1.5
        )
        self.assertAlmostEqual(match["reflection_magnitude"], 0.1, places=12)
        self.assertAlmostEqual(match["vswr"], 1.1 / 0.9, places=12)
        self.assertTrue(match["compliant"])

    def test_opposed_reflections_cancel(self):
        match = input_port_match(
            [
                {"magnitude": 0.2, "phase_deg": 0.0},
                {"magnitude": 0.2, "phase_deg": 180.0},
            ]
        )
        self.assertAlmostEqual(match["reflection_magnitude"], 0.0, places=12)
        self.assertAlmostEqual(match["vswr"], 1.0, places=12)

    def test_return_loss_matches_the_reflection_magnitude(self):
        match = input_port_match([{"magnitude": 0.01, "phase_deg": 0.0}])
        self.assertAlmostEqual(match["return_loss_db"], 40.0, places=9)

    def test_high_reflection_breaks_the_vswr_limit(self):
        match = input_port_match([{"magnitude": 0.5, "phase_deg": 0.0}], 1.5)
        self.assertFalse(match["compliant"])
        self.assertAlmostEqual(match["vswr"], 3.0, places=12)

    def test_magnitude_outside_the_unit_interval_is_rejected(self):
        with self.assertRaises(ValueError):
            input_port_match([{"magnitude": 1.4, "phase_deg": 0.0}])

    def test_unity_reflection_is_rejected(self):
        with self.assertRaises(ValueError):
            input_port_match([{"magnitude": 1.0, "phase_deg": 0.0}])

    def test_vswr_limit_below_unity_is_rejected(self):
        with self.assertRaises(ValueError):
            input_port_match([{"magnitude": 0.1}], 0.8)

    def test_empty_reflection_list_is_rejected(self):
        with self.assertRaises(ValueError):
            input_port_match([])


class AssessmentTests(unittest.TestCase):
    def healthy_spec(self):
        return {
            "topology": "corporate_divider_tree",
            "commanded": uniform_commanded(8),
            "path_errors": clean_paths(8),
            "element_spacing_wavelengths": 0.5,
            "phase_shifter_bits": 6,
            "loss_stages": [{"name": "divider", "loss_db": 1.0}],
            "loss_allocation_db": 2.0,
            "element_reflections": [{"magnitude": 0.05, "phase_deg": 0.0}] * 8,
            "vswr_limit": 1.5,
            "gain_loss_allocation_db": 0.5,
            "pointing_allocation_deg": 0.1,
        }

    def test_healthy_network_is_compliant(self):
        result = assess_beam_forming_network(self.healthy_spec())
        self.assertTrue(result["compliant"])
        self.assertEqual(result["findings"], [])
        self.assertEqual(result["topology_family"], "corporate")

    def test_quantisation_loss_is_added_to_the_excitation_loss(self):
        spec = self.healthy_spec()
        without = dict(spec, phase_shifter_bits=None)
        self.assertGreater(
            assess_beam_forming_network(spec)["gain_loss_db"],
            assess_beam_forming_network(without)["gain_loss_db"],
        )

    def test_random_phase_scatter_breaks_the_gain_allocation(self):
        spec = self.healthy_spec()
        spec["path_errors"] = [
            {"phase_error_deg": 25.0 if i % 2 else -25.0} for i in range(8)
        ]
        result = assess_beam_forming_network(spec)
        self.assertFalse(result["compliant"])
        self.assertTrue(any("gain loss" in f for f in result["findings"]))

    def test_phase_gradient_breaks_the_pointing_allocation(self):
        spec = self.healthy_spec()
        spec["path_errors"] = [{"phase_error_deg": 3.0 * i} for i in range(8)]
        result = assess_beam_forming_network(spec)
        self.assertFalse(result["compliant"])
        self.assertTrue(any("beam-pointing" in f for f in result["findings"]))

    def test_loss_overspend_is_a_finding(self):
        spec = self.healthy_spec()
        spec["loss_stages"] = [{"name": "divider", "loss_db": 3.4}]
        result = assess_beam_forming_network(spec)
        self.assertFalse(result["compliant"])
        self.assertTrue(any("insertion loss" in f for f in result["findings"]))

    def test_input_mismatch_is_a_finding(self):
        spec = self.healthy_spec()
        spec["element_reflections"] = [{"magnitude": 0.4, "phase_deg": 0.0}] * 8
        result = assess_beam_forming_network(spec)
        self.assertFalse(result["compliant"])
        self.assertTrue(any("vswr" in f for f in result["findings"]))

    def test_missing_required_key_is_rejected(self):
        spec = self.healthy_spec()
        del spec["loss_allocation_db"]
        with self.assertRaises(ValueError):
            assess_beam_forming_network(spec)

    def test_non_mapping_spec_is_rejected(self):
        with self.assertRaises(ValueError):
            assess_beam_forming_network(["corporate_divider_tree"])

    def test_negative_gain_allocation_is_rejected(self):
        spec = self.healthy_spec()
        spec["gain_loss_allocation_db"] = -1.0
        with self.assertRaises(ValueError):
            assess_beam_forming_network(spec)

    def test_unknown_topology_stops_the_assessment(self):
        spec = self.healthy_spec()
        spec["topology"] = "hand_wired_harness"
        with self.assertRaises(ValueError):
            assess_beam_forming_network(spec)


if __name__ == "__main__":
    unittest.main()
