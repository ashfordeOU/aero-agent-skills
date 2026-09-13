#!/usr/bin/env python3
"""Gate 3 contract test for e20-gas-discharge-general-requirements.

Offline, deterministic, stdlib unittest only.
"""

import math
import unittest

from e20_gas_discharge_general_requirements_logic import (
    COMPARISON_TOLERANCE,
    DEFAULT_SECONDARY_EMISSION,
    ENVIRONMENT_PHASES,
    REQUIRED_ENVELOPE_PHASES,
    assess_gas_discharge_freedom,
    breakdown_voltage_v,
    categorize_environment_phase,
    discharge_margin_db,
    discharge_onset_power_w,
    envelope_coverage,
    evaluate_phase_freedom,
    gas_coefficients,
    peak_envelope_power_w,
    similarity_minimum,
    worst_case_pressure_pa,
)


def sample_item(**overrides):
    item = {
        "id": "tt-c-diplexer",
        "gas": "air",
        "gap_m": 2.0e-3,
        "carrier_powers_w": [1.0, 1.0],
        "vswr": 1.2,
        "tolerance_db": 0.5,
        "reference_onset_w": 20000.0,
        "reference_pressure_pa": 101325.0,
        "reference_gap_m": 2.0e-3,
    }
    item.update(overrides)
    return item


def full_envelope():
    return [
        {"phase": "ground-ambient", "pressure_low_pa": 90000.0, "pressure_high_pa": 105000.0},
        {"phase": "ascent-venting", "pressure_low_pa": 1.0, "pressure_high_pa": 90000.0},
        {"phase": "early-orbit-outgassing", "pressure_low_pa": 1.0e-4, "pressure_high_pa": 5.0},
        {"phase": "on-station-vacuum", "pressure_low_pa": 1.0e-8, "pressure_high_pa": 1.0e-6},
    ]


class GasCoefficientTests(unittest.TestCase):
    def test_air_coefficients_returned(self):
        coeff = gas_coefficients("air")
        self.assertAlmostEqual(coeff["a_per_pa_m"], 11.25)
        self.assertAlmostEqual(coeff["b_v_per_pa_m"], 273.75)

    def test_gas_lookup_is_case_insensitive(self):
        self.assertEqual(gas_coefficients("ARGON"), gas_coefficients("argon"))

    def test_returned_mapping_is_a_copy(self):
        coeff = gas_coefficients("nitrogen")
        coeff["a_per_pa_m"] = 0.0
        self.assertAlmostEqual(gas_coefficients("nitrogen")["a_per_pa_m"], 9.0)

    def test_unknown_gas_raises(self):
        with self.assertRaises(ValueError):
            gas_coefficients("xenon-plasma")

    def test_empty_gas_name_raises(self):
        with self.assertRaises(ValueError):
            gas_coefficients("   ")


class PhaseCategoryTests(unittest.TestCase):
    def test_ground_phase_is_dense_gas(self):
        self.assertEqual(categorize_environment_phase("ground-ambient"), "dense-gas")

    def test_ascent_phase_is_transitional(self):
        self.assertEqual(categorize_environment_phase("ascent-venting"), "transitional")

    def test_on_station_phase_is_vacuum(self):
        self.assertEqual(categorize_environment_phase("on-station-vacuum"), "vacuum")

    def test_every_catalogued_phase_resolves(self):
        for phase in ENVIRONMENT_PHASES:
            self.assertIn(
                categorize_environment_phase(phase),
                {"dense-gas", "transitional", "vacuum"},
            )

    def test_unrecognized_phase_raises(self):
        with self.assertRaises(ValueError):
            categorize_environment_phase("lunar-night")

    def test_non_string_phase_raises(self):
        with self.assertRaises(ValueError):
            categorize_environment_phase(7)


class SimilarityCurveTests(unittest.TestCase):
    def test_minimum_voltage_matches_closed_form(self):
        pd_min, voltage_min = similarity_minimum("air")
        self.assertAlmostEqual(voltage_min, 273.75 * pd_min, places=9)

    def test_voltage_at_the_minimum_product_equals_the_minimum(self):
        pd_min, voltage_min = similarity_minimum("air")
        gap = 1.0e-3
        computed = breakdown_voltage_v(pd_min / gap, gap, "air")
        self.assertAlmostEqual(computed, voltage_min, places=6)

    def test_minimum_is_a_true_minimum_of_the_curve(self):
        pd_min, voltage_min = similarity_minimum("air")
        gap = 1.0e-3
        for factor in (0.5, 0.8, 1.5, 4.0):
            self.assertGreater(
                breakdown_voltage_v(pd_min * factor / gap, gap, "air"), voltage_min
            )

    def test_dense_branch_rises_with_pressure(self):
        low = breakdown_voltage_v(10000.0, 1.0e-3, "air")
        high = breakdown_voltage_v(101325.0, 1.0e-3, "air")
        self.assertGreater(high, low)

    def test_long_mean_free_path_branch_has_no_finite_breakdown(self):
        self.assertTrue(math.isinf(breakdown_voltage_v(1.0e-6, 1.0e-3, "air")))

    def test_similarity_law_depends_on_the_product_only(self):
        first = breakdown_voltage_v(1000.0, 2.0e-3, "air")
        second = breakdown_voltage_v(2000.0, 1.0e-3, "air")
        self.assertAlmostEqual(first, second, places=9)

    def test_zero_pressure_raises(self):
        with self.assertRaises(ValueError):
            breakdown_voltage_v(0.0, 1.0e-3, "air")

    def test_negative_gap_raises(self):
        with self.assertRaises(ValueError):
            breakdown_voltage_v(1000.0, -1.0e-3, "air")

    def test_zero_secondary_emission_raises_in_voltage(self):
        with self.assertRaises(ValueError):
            breakdown_voltage_v(1000.0, 1.0e-3, "air", 0.0)

    def test_zero_secondary_emission_raises_in_minimum(self):
        with self.assertRaises(ValueError):
            similarity_minimum("air", 0.0)


class WorstCasePressureTests(unittest.TestCase):
    def test_interior_minimum_is_selected_over_the_edges(self):
        gap = 2.0e-3
        pd_min, _ = similarity_minimum("air")
        worst = worst_case_pressure_pa(1.0, 90000.0, gap, "air")
        self.assertAlmostEqual(worst, pd_min / gap, places=9)
        self.assertGreater(worst, 1.0)
        self.assertLess(worst, 90000.0)

    def test_band_entirely_above_the_minimum_clamps_to_the_low_edge(self):
        worst = worst_case_pressure_pa(90000.0, 105000.0, 2.0e-3, "air")
        self.assertAlmostEqual(worst, 90000.0)

    def test_band_entirely_below_the_minimum_clamps_to_the_high_edge(self):
        worst = worst_case_pressure_pa(1.0e-8, 1.0e-6, 2.0e-3, "air")
        self.assertAlmostEqual(worst, 1.0e-6)

    def test_widening_the_gap_moves_the_worst_case_to_lower_pressure(self):
        narrow = worst_case_pressure_pa(1.0, 90000.0, 1.0e-3, "air")
        wide = worst_case_pressure_pa(1.0, 90000.0, 4.0e-3, "air")
        self.assertLess(wide, narrow)

    def test_inverted_band_raises(self):
        with self.assertRaises(ValueError):
            worst_case_pressure_pa(500.0, 100.0, 1.0e-3, "air")

    def test_non_positive_low_edge_raises(self):
        with self.assertRaises(ValueError):
            worst_case_pressure_pa(0.0, 100.0, 1.0e-3, "air")

    def test_non_positive_gap_raises(self):
        with self.assertRaises(ValueError):
            worst_case_pressure_pa(1.0, 100.0, 0.0, "air")


class PeakEnvelopePowerTests(unittest.TestCase):
    def test_single_matched_carrier_returns_its_own_power(self):
        self.assertAlmostEqual(peak_envelope_power_w([100.0]), 100.0)

    def test_carriers_add_coherently_at_the_worst_instant(self):
        self.assertAlmostEqual(peak_envelope_power_w([100.0, 100.0]), 400.0)

    def test_unequal_carriers_use_amplitude_addition(self):
        self.assertAlmostEqual(peak_envelope_power_w([100.0, 25.0]), 225.0)

    def test_mismatch_uplift_follows_the_standing_wave_factor(self):
        expected = 100.0 * (1.0 + (2.0 - 1.0) / (2.0 + 1.0)) ** 2
        self.assertAlmostEqual(peak_envelope_power_w([100.0], vswr=2.0), expected)

    def test_tolerance_stack_applies_in_decibels(self):
        self.assertAlmostEqual(
            peak_envelope_power_w([100.0], tolerance_db=3.0), 100.0 * 10.0 ** 0.3
        )

    def test_empty_carrier_set_raises(self):
        with self.assertRaises(ValueError):
            peak_envelope_power_w([])

    def test_non_positive_carrier_raises(self):
        with self.assertRaises(ValueError):
            peak_envelope_power_w([100.0, 0.0])

    def test_vswr_below_unity_raises(self):
        with self.assertRaises(ValueError):
            peak_envelope_power_w([100.0], vswr=0.9)

    def test_negative_tolerance_raises(self):
        with self.assertRaises(ValueError):
            peak_envelope_power_w([100.0], tolerance_db=-1.0)


class OnsetScalingTests(unittest.TestCase):
    def test_scaling_to_the_reference_point_is_the_identity(self):
        onset = discharge_onset_power_w(
            4000.0, 101325.0, 2.0e-3, 101325.0, 2.0e-3, "air"
        )
        self.assertAlmostEqual(onset, 4000.0, places=6)

    def test_onset_collapses_near_the_curve_minimum(self):
        pd_min, _ = similarity_minimum("air")
        onset = discharge_onset_power_w(
            4000.0, 101325.0, 2.0e-3, pd_min / 2.0e-3, 2.0e-3, "air"
        )
        self.assertLess(onset, 4000.0)
        self.assertGreater(onset, 0.0)

    def test_onset_is_unbounded_on_the_no_breakdown_branch(self):
        onset = discharge_onset_power_w(
            4000.0, 101325.0, 2.0e-3, 1.0e-8, 2.0e-3, "air"
        )
        self.assertTrue(math.isinf(onset))

    def test_onset_follows_the_square_of_the_voltage_ratio(self):
        ratio = breakdown_voltage_v(5000.0, 2.0e-3, "air") / breakdown_voltage_v(
            101325.0, 2.0e-3, "air"
        )
        onset = discharge_onset_power_w(
            4000.0, 101325.0, 2.0e-3, 5000.0, 2.0e-3, "air"
        )
        self.assertAlmostEqual(onset, 4000.0 * ratio ** 2, places=6)

    def test_non_positive_reference_onset_raises(self):
        with self.assertRaises(ValueError):
            discharge_onset_power_w(0.0, 101325.0, 2.0e-3, 1000.0, 2.0e-3, "air")

    def test_reference_on_the_no_breakdown_branch_raises(self):
        with self.assertRaises(ValueError):
            discharge_onset_power_w(4000.0, 1.0e-8, 2.0e-3, 1000.0, 2.0e-3, "air")


class MarginTests(unittest.TestCase):
    def test_factor_of_two_is_about_three_decibels(self):
        self.assertAlmostEqual(discharge_margin_db(200.0, 100.0), 3.0103, places=4)

    def test_equal_powers_give_zero_margin(self):
        self.assertAlmostEqual(discharge_margin_db(100.0, 100.0), 0.0)

    def test_applied_above_onset_gives_a_negative_margin(self):
        self.assertLess(discharge_margin_db(50.0, 100.0), 0.0)

    def test_unbounded_onset_gives_an_unbounded_margin(self):
        self.assertTrue(math.isinf(discharge_margin_db(math.inf, 100.0)))

    def test_zero_applied_power_raises(self):
        with self.assertRaises(ValueError):
            discharge_margin_db(100.0, 0.0)

    def test_zero_onset_power_raises(self):
        with self.assertRaises(ValueError):
            discharge_margin_db(0.0, 100.0)


class PhaseEvaluationTests(unittest.TestCase):
    def test_vacuum_phase_is_free_of_discharge(self):
        result = evaluate_phase_freedom(
            sample_item(),
            {"phase": "on-station-vacuum", "pressure_low_pa": 1.0e-8, "pressure_high_pa": 1.0e-6},
            6.0,
        )
        self.assertTrue(result["compliant"])
        self.assertEqual(result["regime"], "vacuum")
        self.assertEqual(result["findings"], [])

    def test_ascent_phase_is_evaluated_at_an_interior_pressure(self):
        result = evaluate_phase_freedom(
            sample_item(),
            {"phase": "ascent-venting", "pressure_low_pa": 1.0, "pressure_high_pa": 90000.0},
            6.0,
        )
        self.assertGreater(result["worst_case_pressure_pa"], 1.0)
        self.assertLess(result["worst_case_pressure_pa"], 90000.0)

    def test_high_power_item_fails_the_transitional_phase(self):
        item = sample_item(carrier_powers_w=[400.0, 400.0])
        result = evaluate_phase_freedom(
            item,
            {"phase": "ascent-venting", "pressure_low_pa": 1.0, "pressure_high_pa": 90000.0},
            6.0,
        )
        self.assertFalse(result["compliant"])
        self.assertEqual(len(result["findings"]), 1)

    def test_exactly_meeting_the_required_margin_is_compliant(self):
        item = sample_item(carrier_powers_w=[100.0], vswr=1.0, tolerance_db=0.0)
        phase = {
            "phase": "ground-ambient",
            "pressure_low_pa": 101325.0,
            "pressure_high_pa": 101325.0,
        }
        probe = evaluate_phase_freedom(item, phase, 0.0)
        result = evaluate_phase_freedom(item, phase, probe["margin_db"])
        self.assertTrue(result["compliant"])

    def test_margin_a_hair_above_the_requirement_is_compliant(self):
        item = sample_item(carrier_powers_w=[100.0], vswr=1.0, tolerance_db=0.0)
        phase = {
            "phase": "ground-ambient",
            "pressure_low_pa": 101325.0,
            "pressure_high_pa": 101325.0,
        }
        probe = evaluate_phase_freedom(item, phase, 0.0)
        result = evaluate_phase_freedom(item, phase, probe["margin_db"] - 1.0e-12)
        self.assertTrue(result["compliant"])

    def test_negative_required_margin_raises(self):
        with self.assertRaises(ValueError):
            evaluate_phase_freedom(
                sample_item(),
                {"phase": "ground-ambient", "pressure_low_pa": 9.0e4, "pressure_high_pa": 1.05e5},
                -1.0,
            )

    def test_item_missing_a_gap_raises(self):
        item = sample_item()
        del item["gap_m"]
        with self.assertRaises(ValueError):
            evaluate_phase_freedom(
                item,
                {"phase": "ground-ambient", "pressure_low_pa": 9.0e4, "pressure_high_pa": 1.05e5},
                6.0,
            )

    def test_phase_record_missing_a_band_raises(self):
        with self.assertRaises(ValueError):
            evaluate_phase_freedom(sample_item(), {"phase": "ground-ambient"}, 6.0)

    def test_item_with_no_declared_power_raises(self):
        item = sample_item()
        del item["carrier_powers_w"]
        with self.assertRaises(ValueError):
            evaluate_phase_freedom(
                item,
                {"phase": "ground-ambient", "pressure_low_pa": 9.0e4, "pressure_high_pa": 1.05e5},
                6.0,
            )


class EnvelopeCoverageTests(unittest.TestCase):
    def test_complete_envelope_reports_no_gap(self):
        coverage = envelope_coverage(list(REQUIRED_ENVELOPE_PHASES))
        self.assertTrue(coverage["complete"])
        self.assertEqual(coverage["missing"], [])

    def test_missing_transitional_phase_is_reported(self):
        coverage = envelope_coverage(["ground-ambient", "on-station-vacuum"])
        self.assertFalse(coverage["complete"])
        self.assertIn("ascent-venting", coverage["missing"])
        self.assertIn("early-orbit-outgassing", coverage["missing"])

    def test_extra_phases_do_not_break_coverage(self):
        coverage = envelope_coverage(
            list(REQUIRED_ENVELOPE_PHASES) + ["planetary-atmosphere"]
        )
        self.assertTrue(coverage["complete"])

    def test_duplicate_phase_raises(self):
        with self.assertRaises(ValueError):
            envelope_coverage(["ground-ambient", "ground-ambient"])

    def test_unrecognized_phase_raises(self):
        with self.assertRaises(ValueError):
            envelope_coverage(["ground-ambient", "solar-conjunction"])

    def test_non_sequence_raises(self):
        with self.assertRaises(ValueError):
            envelope_coverage("ground-ambient")


class AssessmentTests(unittest.TestCase):
    def test_compliant_item_over_the_full_envelope(self):
        report = assess_gas_discharge_freedom(sample_item(), full_envelope(), 6.0)
        self.assertTrue(report["compliant"])
        self.assertEqual(report["findings"], [])
        self.assertEqual(len(report["phases"]), 4)
        self.assertTrue(report["coverage"]["complete"])

    def test_worst_margin_ignores_the_unbounded_vacuum_phase(self):
        report = assess_gas_discharge_freedom(sample_item(), full_envelope(), 6.0)
        self.assertFalse(math.isinf(report["worst_margin_db"]))

    def test_overpowered_item_is_not_compliant(self):
        report = assess_gas_discharge_freedom(
            sample_item(carrier_powers_w=[500.0, 500.0]), full_envelope(), 6.0
        )
        self.assertFalse(report["compliant"])
        self.assertTrue(report["findings"])

    def test_partial_envelope_is_a_finding_even_when_every_phase_passes(self):
        phases = [
            record
            for record in full_envelope()
            if record["phase"] in ("ground-ambient", "on-station-vacuum")
        ]
        report = assess_gas_discharge_freedom(sample_item(), phases, 6.0)
        self.assertFalse(report["compliant"])
        self.assertTrue(
            all(evaluation["compliant"] for evaluation in report["phases"])
        )
        self.assertEqual(len(report["findings"]), 2)

    def test_item_identifier_is_carried_into_the_report(self):
        report = assess_gas_discharge_freedom(sample_item(), full_envelope(), 6.0)
        self.assertEqual(report["item"], "tt-c-diplexer")

    def test_empty_phase_list_raises(self):
        with self.assertRaises(ValueError):
            assess_gas_discharge_freedom(sample_item(), [], 6.0)

    def test_tolerance_constant_is_representation_scale_only(self):
        self.assertLess(COMPARISON_TOLERANCE, 1.0e-6)
        self.assertGreater(DEFAULT_SECONDARY_EMISSION, 0.0)


if __name__ == "__main__":
    unittest.main()
