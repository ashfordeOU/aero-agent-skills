#!/usr/bin/env python3
"""Contract test for class 2 self-made wound magnetic parts (offline)."""

import copy
import os
import sys
import unittest

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from q60_class_2_self_made_magnetics_logic import (  # noqa: E402
    BASE_SCREENING_SEQUENCE,
    CONSTRUCTIONS,
    CONSTRUCTION_SCREENING,
    DEFAULT_MAGNETICS_POLICY,
    DESIGN_NONCONFORMING,
    INSULATION_CLASS_RATINGS_C,
    MAGNETICS_NOT_ADMISSIBLE,
    PRACTICE_SATISFIED,
    SCREENING_OUTSTANDING,
    admissibility_gaps,
    assess_class2_self_made_magnetics,
    copper_loss_w,
    core_loss_w,
    flux_utilisation,
    hot_spot_margin_c,
    hot_spot_temperature_c,
    peak_flux_density_t,
    screening_sequence,
    temperature_rise_c,
    validate_magnetics_case,
    validate_magnetics_policy,
    winding_current_density,
    winding_resistance_ohm,
    window_fill_factor,
)

BASE_CASE = {
    "part_reference": "house-wound-transformer-01",
    "wire_specification": "wire-spec-01",
    "core_specification": "core-spec-01",
    "winding_procedure": "wp-01",
    "applied_voltage_v": 28.0,
    "pulse_duration_s": 1.0e-5,
    "turns": 30,
    "core_area_mm2": 50.0,
    "saturation_flux_t": 0.39,
    "conductor_area_mm2": 0.5,
    "window_area_mm2": 50.0,
    "rms_current_a": 1.5,
    "mean_turn_length_mm": 60.0,
    "winding_temperature_c": 85.0,
    "steinmetz_k": 5.0,
    "frequency_khz": 50.0,
    "core_volume_mm3": 5000.0,
    "frequency_exponent": 1.3,
    "flux_exponent": 2.4,
    "thermal_resistance_c_per_w": 25.0,
    "ambient_temperature_c": 60.0,
    "insulation_class": "class-f",
    "construction": "vacuum-impregnated",
    "flight_lot_size": 12,
}

CLEAN_CASE = dict(BASE_CASE)
CLEAN_CASE["screening_completed"] = screening_sequence(BASE_CASE)


def _case(**overrides):
    case = copy.deepcopy(BASE_CASE)
    case.update(overrides)
    if "screening_completed" not in overrides:
        case["screening_completed"] = screening_sequence(case)
    return case


class PolicyTests(unittest.TestCase):
    def test_default_policy_round_trips(self):
        self.assertEqual(validate_magnetics_policy(None), DEFAULT_MAGNETICS_POLICY)

    def test_policy_override_is_merged(self):
        merged = validate_magnetics_policy({"max_flux_utilisation": 0.5})
        self.assertAlmostEqual(merged["max_flux_utilisation"], 0.5, places=9)
        self.assertAlmostEqual(
            merged["max_window_fill"],
            DEFAULT_MAGNETICS_POLICY["max_window_fill"],
            places=9,
        )

    def test_unknown_policy_key_rejected(self):
        with self.assertRaises(ValueError):
            validate_magnetics_policy({"max_flux": 0.5})

    def test_flux_utilisation_above_one_rejected(self):
        with self.assertRaises(ValueError):
            validate_magnetics_policy({"max_flux_utilisation": 1.4})

    def test_window_fill_above_one_rejected(self):
        with self.assertRaises(ValueError):
            validate_magnetics_policy({"max_window_fill": 1.2})

    def test_a_fractional_lot_floor_rejected(self):
        with self.assertRaises(ValueError):
            validate_magnetics_policy({"min_lot_for_destructive_sample": 2.5})

    def test_non_boolean_operator_flag_rejected(self):
        with self.assertRaises(ValueError):
            validate_magnetics_policy({"require_certified_operator": "yes"})

    def test_non_mapping_policy_rejected(self):
        with self.assertRaises(ValueError):
            validate_magnetics_policy("default")


class AdmissibilityTests(unittest.TestCase):
    def test_a_fully_documented_part_has_no_gap(self):
        self.assertEqual(admissibility_gaps(BASE_CASE), ())

    def test_a_missing_wire_specification_is_a_gap(self):
        gaps = admissibility_gaps(dict(BASE_CASE, wire_specification=None))
        self.assertIn("wire-specification", gaps)

    def test_a_blank_winding_procedure_is_a_gap(self):
        gaps = admissibility_gaps(dict(BASE_CASE, winding_procedure="   "))
        self.assertIn("qualified-winding-procedure", gaps)

    def test_class_two_does_not_demand_a_certified_operator(self):
        self.assertEqual(admissibility_gaps(dict(BASE_CASE)), ())

    def test_policy_may_demand_a_certified_operator(self):
        gaps = admissibility_gaps(
            BASE_CASE, {"require_certified_operator": True}
        )
        self.assertIn("certified-winding-operator", gaps)

    def test_a_named_operator_closes_that_gap(self):
        gaps = admissibility_gaps(
            dict(BASE_CASE, operator_certification="cert-4471"),
            {"require_certified_operator": True},
        )
        self.assertEqual(gaps, ())

    def test_a_non_mapping_case_rejected(self):
        with self.assertRaises(ValueError):
            admissibility_gaps("house-wound-transformer-01")


class FluxTests(unittest.TestCase):
    def test_flux_follows_the_volt_second_product(self):
        self.assertAlmostEqual(
            peak_flux_density_t(28.0, 1.0e-5, 30, 50.0),
            28.0 * 1.0e-5 / (30 * 50.0e-6),
            places=9,
        )

    def test_more_turns_lower_the_flux(self):
        few = peak_flux_density_t(28.0, 1.0e-5, 30, 50.0)
        many = peak_flux_density_t(28.0, 1.0e-5, 60, 50.0)
        self.assertAlmostEqual(many, few / 2.0, places=9)

    def test_a_bigger_core_lowers_the_flux(self):
        small = peak_flux_density_t(28.0, 1.0e-5, 30, 50.0)
        large = peak_flux_density_t(28.0, 1.0e-5, 30, 100.0)
        self.assertAlmostEqual(large, small / 2.0, places=9)

    def test_a_fractional_turn_count_rejected(self):
        with self.assertRaises(ValueError):
            peak_flux_density_t(28.0, 1.0e-5, 30.5, 50.0)

    def test_a_zero_core_area_rejected(self):
        with self.assertRaises(ValueError):
            peak_flux_density_t(28.0, 1.0e-5, 30, 0.0)

    def test_utilisation_is_peak_over_saturation(self):
        self.assertAlmostEqual(flux_utilisation(0.2, 0.4), 0.5, places=9)

    def test_a_zero_saturation_figure_rejected(self):
        with self.assertRaises(ValueError):
            flux_utilisation(0.2, 0.0)


class WindingTests(unittest.TestCase):
    def test_fill_is_the_conductor_over_the_window(self):
        self.assertAlmostEqual(window_fill_factor(30, 0.5, 50.0), 0.3, places=9)

    def test_a_full_window_reports_unity(self):
        self.assertAlmostEqual(window_fill_factor(30, 0.5, 15.0), 1.0, places=9)

    def test_a_zero_window_rejected(self):
        with self.assertRaises(ValueError):
            window_fill_factor(30, 0.5, 0.0)

    def test_current_density_is_current_over_section(self):
        self.assertAlmostEqual(winding_current_density(1.5, 0.5), 3.0, places=9)

    def test_a_zero_conductor_section_rejected(self):
        with self.assertRaises(ValueError):
            winding_current_density(1.5, 0.0)

    def test_resistance_follows_the_copper_length(self):
        short = winding_resistance_ohm(30, 60.0, 0.5, 20.0)
        long_winding = winding_resistance_ohm(60, 60.0, 0.5, 20.0)
        self.assertAlmostEqual(long_winding, short * 2.0, places=9)

    def test_resistance_rises_with_temperature(self):
        cold = winding_resistance_ohm(30, 60.0, 0.5, 20.0)
        hot = winding_resistance_ohm(30, 60.0, 0.5, 85.0)
        expected = cold * (
            1.0 + DEFAULT_MAGNETICS_POLICY["copper_temperature_coefficient"] * 65.0
        )
        self.assertAlmostEqual(hot, expected, places=9)

    def test_resistance_at_the_reference_temperature_takes_no_factor(self):
        cold = winding_resistance_ohm(30, 60.0, 0.5, 20.0)
        expected = (
            DEFAULT_MAGNETICS_POLICY["copper_resistivity_ohm_m"]
            * (30 * 60.0e-3)
            / (0.5e-6)
        )
        self.assertAlmostEqual(cold, expected, places=9)

    def test_a_temperature_driving_the_factor_non_positive_rejected(self):
        with self.assertRaises(ValueError):
            winding_resistance_ohm(30, 60.0, 0.5, -300.0)


class LossTests(unittest.TestCase):
    def test_copper_loss_is_current_squared_times_resistance(self):
        self.assertAlmostEqual(copper_loss_w(2.0, 0.25), 1.0, places=9)

    def test_zero_current_dissipates_nothing_in_the_copper(self):
        self.assertAlmostEqual(copper_loss_w(0.0, 0.25), 0.0, places=9)

    def test_negative_resistance_rejected(self):
        with self.assertRaises(ValueError):
            copper_loss_w(2.0, -0.25)

    def test_unit_exponents_reduce_the_core_law_to_a_product(self):
        self.assertAlmostEqual(
            core_loss_w(2.0, 3.0, 4.0, 1000.0, 1.0, 1.0),
            2.0 * 3.0 * 4.0 * 1.0 / 1000.0,
            places=9,
        )

    def test_core_loss_scales_with_the_volume(self):
        small = core_loss_w(5.0, 50.0, 0.2, 5000.0, 1.3, 2.4)
        large = core_loss_w(5.0, 50.0, 0.2, 10000.0, 1.3, 2.4)
        self.assertAlmostEqual(large, small * 2.0, places=9)

    def test_core_loss_rises_steeply_with_the_flux(self):
        low = core_loss_w(5.0, 50.0, 0.1, 5000.0, 1.3, 2.4)
        high = core_loss_w(5.0, 50.0, 0.2, 5000.0, 1.3, 2.4)
        self.assertGreater(high, low * 4.0)

    def test_a_zero_flux_has_no_core_law_value(self):
        with self.assertRaises(ValueError):
            core_loss_w(5.0, 50.0, 0.0, 5000.0, 1.3, 2.4)

    def test_a_non_positive_exponent_rejected(self):
        with self.assertRaises(ValueError):
            core_loss_w(5.0, 50.0, 0.2, 5000.0, 0.0, 2.4)


class ThermalTests(unittest.TestCase):
    def test_rise_is_loss_over_the_thermal_path(self):
        self.assertAlmostEqual(temperature_rise_c(0.4, 25.0), 10.0, places=9)

    def test_no_loss_produces_no_rise(self):
        self.assertAlmostEqual(temperature_rise_c(0.0, 25.0), 0.0, places=9)

    def test_hot_spot_sits_above_the_ambient(self):
        self.assertAlmostEqual(hot_spot_temperature_c(60.0, 10.0), 70.0, places=9)

    def test_margin_holds_the_class_derating_back(self):
        self.assertAlmostEqual(hot_spot_margin_c(100.0, "class-f"), 40.0, places=9)

    def test_margin_is_negative_past_the_derated_rating(self):
        self.assertAlmostEqual(hot_spot_margin_c(150.0, "class-f"), -10.0, places=9)

    def test_a_hotter_insulation_class_buys_margin(self):
        self.assertGreater(
            hot_spot_margin_c(100.0, "class-h"), hot_spot_margin_c(100.0, "class-b")
        )

    def test_an_unknown_insulation_class_rejected(self):
        with self.assertRaises(ValueError):
            hot_spot_margin_c(100.0, "class-z")

    def test_a_negative_rise_rejected(self):
        with self.assertRaises(ValueError):
            hot_spot_temperature_c(60.0, -5.0)


class ScreeningTests(unittest.TestCase):
    def test_every_part_takes_the_base_sequence(self):
        sequence = screening_sequence(BASE_CASE)
        for step in BASE_SCREENING_SEQUENCE:
            self.assertIn(step, sequence)

    def test_an_impregnated_part_owes_a_penetration_check(self):
        self.assertIn(
            "impregnation-penetration-verification", screening_sequence(BASE_CASE)
        )

    def test_a_potted_part_owes_a_void_inspection(self):
        sequence = screening_sequence(dict(BASE_CASE, construction="potted"))
        self.assertIn("void-free-encapsulation-inspection", sequence)

    def test_an_unpotted_part_owes_a_varnish_check(self):
        sequence = screening_sequence(dict(BASE_CASE, construction="unpotted"))
        self.assertIn("varnish-coverage-verification", sequence)

    def test_a_lot_large_enough_is_sampled_destructively(self):
        self.assertIn("destructive-lot-sample-analysis", screening_sequence(BASE_CASE))

    def test_a_lot_too_small_to_sample_is_screened_whole(self):
        sequence = screening_sequence(dict(BASE_CASE, flight_lot_size=2))
        self.assertIn("full-lot-nondestructive-screening", sequence)
        self.assertNotIn("destructive-lot-sample-analysis", sequence)

    def test_every_construction_carries_its_own_step(self):
        for construction in CONSTRUCTIONS:
            sequence = screening_sequence(
                dict(BASE_CASE, construction=construction)
            )
            for step in CONSTRUCTION_SCREENING[construction]:
                self.assertIn(step, sequence)


class DispositionTests(unittest.TestCase):
    def test_a_complete_part_satisfies_recognised_practice(self):
        result = assess_class2_self_made_magnetics(CLEAN_CASE)
        self.assertEqual(result["disposition"], PRACTICE_SATISFIED)
        self.assertEqual(result["findings"], [])

    def test_a_missing_foundation_makes_the_part_inadmissible(self):
        result = assess_class2_self_made_magnetics(_case(core_specification=None))
        self.assertEqual(result["disposition"], MAGNETICS_NOT_ADMISSIBLE)
        self.assertIn("core-specification", result["admissibility_gaps"])

    def test_a_missing_screening_step_is_outstanding(self):
        result = assess_class2_self_made_magnetics(
            _case(screening_completed=["winding-visual-inspection"])
        )
        self.assertEqual(result["disposition"], SCREENING_OUTSTANDING)
        self.assertIn(
            "interwinding-insulation-resistance", result["screening_outstanding"]
        )

    def test_a_flux_utilisation_exactly_on_the_limit_is_compliant(self):
        peak = peak_flux_density_t(28.0, 1.0e-5, 30, 50.0)
        result = assess_class2_self_made_magnetics(
            _case(saturation_flux_t=peak / 0.6)
        )
        self.assertAlmostEqual(result["flux_utilisation"], 0.6, places=9)
        self.assertEqual(result["disposition"], PRACTICE_SATISFIED)

    def test_a_saturating_core_is_nonconforming(self):
        result = assess_class2_self_made_magnetics(_case(saturation_flux_t=0.2))
        self.assertEqual(result["disposition"], DESIGN_NONCONFORMING)
        self.assertGreater(result["flux_utilisation"], 0.6)

    def test_a_window_fill_exactly_on_the_limit_is_compliant(self):
        result = assess_class2_self_made_magnetics(_case(window_area_mm2=37.5))
        self.assertAlmostEqual(result["window_fill_factor"], 0.4, places=9)
        self.assertEqual(result["disposition"], PRACTICE_SATISFIED)

    def test_an_overfilled_window_is_nonconforming(self):
        result = assess_class2_self_made_magnetics(_case(window_area_mm2=25.0))
        self.assertEqual(result["disposition"], DESIGN_NONCONFORMING)

    def test_a_current_density_exactly_on_the_limit_is_compliant(self):
        result = assess_class2_self_made_magnetics(_case(rms_current_a=2.0))
        self.assertAlmostEqual(result["current_density_a_per_mm2"], 4.0, places=9)
        self.assertEqual(result["disposition"], PRACTICE_SATISFIED)

    def test_an_overloaded_winding_is_nonconforming(self):
        result = assess_class2_self_made_magnetics(_case(rms_current_a=3.0))
        self.assertEqual(result["disposition"], DESIGN_NONCONFORMING)

    def test_a_hot_spot_exactly_on_the_derated_rating_is_compliant(self):
        baseline = assess_class2_self_made_magnetics(CLEAN_CASE)
        allowed = INSULATION_CLASS_RATINGS_C["class-f"] - 15.0
        resistance = (allowed - BASE_CASE["ambient_temperature_c"]) / baseline[
            "total_loss_w"
        ]
        result = assess_class2_self_made_magnetics(
            _case(thermal_resistance_c_per_w=resistance)
        )
        self.assertAlmostEqual(result["hot_spot_margin_c"], 0.0, places=9)
        self.assertEqual(result["disposition"], PRACTICE_SATISFIED)

    def test_an_overheated_winding_is_nonconforming(self):
        result = assess_class2_self_made_magnetics(
            _case(thermal_resistance_c_per_w=600.0)
        )
        self.assertEqual(result["disposition"], DESIGN_NONCONFORMING)
        self.assertLess(result["hot_spot_margin_c"], 0.0)

    def test_a_cooler_insulation_class_can_turn_the_same_design(self):
        hot = assess_class2_self_made_magnetics(
            _case(thermal_resistance_c_per_w=400.0, insulation_class="class-a")
        )
        tolerant = assess_class2_self_made_magnetics(
            _case(thermal_resistance_c_per_w=400.0, insulation_class="class-c")
        )
        self.assertEqual(hot["disposition"], DESIGN_NONCONFORMING)
        self.assertEqual(tolerant["disposition"], PRACTICE_SATISFIED)

    def test_inadmissibility_outranks_a_design_finding(self):
        result = assess_class2_self_made_magnetics(
            _case(wire_specification=None, saturation_flux_t=0.2)
        )
        self.assertEqual(result["disposition"], MAGNETICS_NOT_ADMISSIBLE)

    def test_a_design_finding_outranks_an_outstanding_screen(self):
        result = assess_class2_self_made_magnetics(
            _case(saturation_flux_t=0.2, screening_completed=[])
        )
        self.assertEqual(result["disposition"], DESIGN_NONCONFORMING)

    def test_case_missing_a_field_rejected(self):
        case = _case()
        del case["core_volume_mm3"]
        with self.assertRaises(ValueError):
            assess_class2_self_made_magnetics(case)

    def test_an_unknown_construction_rejected(self):
        with self.assertRaises(ValueError):
            assess_class2_self_made_magnetics(_case(construction="tape-wound"))

    def test_a_non_sequence_screening_record_rejected(self):
        with self.assertRaises(ValueError):
            assess_class2_self_made_magnetics(
                _case(screening_completed="winding-visual-inspection")
            )

    def test_case_validation_accepts_the_reference_case(self):
        self.assertIs(validate_magnetics_case(CLEAN_CASE), CLEAN_CASE)

    def test_every_construction_is_routable(self):
        for construction in CONSTRUCTIONS:
            result = assess_class2_self_made_magnetics(
                _case(construction=construction)
            )
            self.assertEqual(result["disposition"], PRACTICE_SATISFIED)

    def test_every_insulation_class_is_routable(self):
        for insulation in INSULATION_CLASS_RATINGS_C:
            result = assess_class2_self_made_magnetics(
                _case(insulation_class=insulation)
            )
            self.assertEqual(result["disposition"], PRACTICE_SATISFIED)


if __name__ == "__main__":
    unittest.main()
