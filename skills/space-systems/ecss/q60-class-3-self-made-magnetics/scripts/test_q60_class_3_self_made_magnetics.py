#!/usr/bin/env python3
"""Contract test for Class 3 self-made wound magnetic parts (offline)."""

import copy
import os
import sys
import unittest

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from q60_class_3_self_made_magnetics_logic import (  # noqa: E402
    BASE_SCREENING_SEQUENCE,
    CONSTRUCTION_FORMS,
    DEFAULT_CLASS3_MAGNETICS_POLICY,
    DESIGN_NONCONFORMING,
    INSULATION_TEMPERATURE_INDEX_C,
    PART_NOT_ADMISSIBLE,
    PRACTICE_SATISFIED,
    REQUIRED_FOUNDATIONS,
    SCREENING_OUTSTANDING,
    assess_class3_self_made_magnetics,
    copper_loss_w,
    core_loss_w,
    current_density_a_per_mm2,
    derated_insulation_limit_c,
    foundation_gaps,
    hot_spot_margin_k,
    outstanding_screening,
    peak_flux_density_t,
    required_dielectric_withstand_v,
    saturation_utilisation,
    screening_sequence,
    temperature_rise_k,
    validate_magnetics_case,
    validate_magnetics_policy,
    winding_resistance_ohm,
    window_fill_factor,
)

CLEAN_CASE = {
    "foundations_held": list(REQUIRED_FOUNDATIONS),
    "volt_seconds": 1.2e-3,
    "turns": 40,
    "core_area_mm2": 100.0,
    "saturation_flux_t": 0.4,
    "conductor_mm2": 0.5,
    "window_mm2": 60.0,
    "winding_current_a": 2.0,
    "cold_resistance_ohm": 0.12,
    "winding_temperature_c": 95.0,
    "steinmetz_k": 1.5,
    "steinmetz_alpha": 1.5,
    "steinmetz_beta": 2.6,
    "frequency_khz": 100.0,
    "core_volume_cm3": 5.0,
    "thermal_resistance_k_per_w": 25.0,
    "ambient_temperature_c": 70.0,
    "insulation_system": "class-f",
    "insulation_withstand_rating_v": 2500.0,
    "working_voltage_v": 300.0,
    "construction_form": "bobbin-wound",
    "flight_lot_size": 8,
    "screening_done": [],
}

FULL_SCREENING = screening_sequence("bobbin-wound", 8)


def _case(**overrides):
    case = copy.deepcopy(CLEAN_CASE)
    case.update(overrides)
    return case


def _screened(**overrides):
    return _case(screening_done=list(FULL_SCREENING), **overrides)


class PolicyTests(unittest.TestCase):
    def test_defaults_are_returned_when_no_policy_is_given(self):
        self.assertEqual(
            validate_magnetics_policy(), DEFAULT_CLASS3_MAGNETICS_POLICY
        )

    def test_an_unknown_policy_key_is_rejected(self):
        with self.assertRaises(ValueError):
            validate_magnetics_policy({"max_turns": 400})

    def test_a_fill_factor_limit_above_one_is_rejected(self):
        with self.assertRaises(ValueError):
            validate_magnetics_policy({"max_window_fill_factor": 1.3})

    def test_a_zero_lot_floor_is_rejected(self):
        with self.assertRaises(ValueError):
            validate_magnetics_policy({"destructive_sample_lot_floor": 0})

    def test_a_non_boolean_practice_flag_is_rejected(self):
        with self.assertRaises(ValueError):
            validate_magnetics_policy(
                {"require_recognised_practice_reference": "yes"}
            )


class FoundationTests(unittest.TestCase):
    def test_a_complete_set_leaves_no_gap(self):
        self.assertEqual(foundation_gaps(CLEAN_CASE), ())

    def test_a_missing_winding_procedure_is_named(self):
        held = [f for f in REQUIRED_FOUNDATIONS if f != "qualified-winding-procedure"]
        self.assertEqual(
            foundation_gaps(_case(foundations_held=held)),
            ("qualified-winding-procedure",),
        )

    def test_foundations_are_matched_case_insensitively(self):
        held = [f.upper() for f in REQUIRED_FOUNDATIONS]
        self.assertEqual(foundation_gaps(_case(foundations_held=held)), ())

    def test_policy_can_drop_the_recognised_practice_foundation(self):
        held = [
            f for f in REQUIRED_FOUNDATIONS if f != "recognised-practice-reference"
        ]
        self.assertEqual(
            foundation_gaps(
                _case(foundations_held=held),
                {"require_recognised_practice_reference": False},
            ),
            (),
        )

    def test_a_non_string_foundation_is_rejected(self):
        with self.assertRaises(ValueError):
            foundation_gaps(_case(foundations_held=[3]))


class FluxTests(unittest.TestCase):
    def test_flux_comes_from_the_volt_second_product(self):
        self.assertAlmostEqual(
            peak_flux_density_t(1.2e-3, 40, 100.0), 0.3, places=9
        )

    def test_more_turns_lower_the_flux(self):
        self.assertLess(
            peak_flux_density_t(1.2e-3, 80, 100.0),
            peak_flux_density_t(1.2e-3, 40, 100.0),
        )

    def test_zero_turns_are_rejected(self):
        with self.assertRaises(ValueError):
            peak_flux_density_t(1.2e-3, 0, 100.0)

    def test_a_non_integer_turn_count_is_rejected(self):
        with self.assertRaises(ValueError):
            peak_flux_density_t(1.2e-3, 40.5, 100.0)

    def test_utilisation_is_flux_over_saturation(self):
        self.assertAlmostEqual(saturation_utilisation(0.2, 0.4), 0.5, places=9)

    def test_a_zero_saturation_figure_is_rejected(self):
        with self.assertRaises(ValueError):
            saturation_utilisation(0.2, 0.0)


class WindingTests(unittest.TestCase):
    def test_fill_is_turns_times_conductor_over_window(self):
        self.assertAlmostEqual(window_fill_factor(40, 0.5, 100.0), 0.2, places=9)

    def test_a_zero_window_is_rejected(self):
        with self.assertRaises(ValueError):
            window_fill_factor(40, 0.5, 0.0)

    def test_current_density_is_current_over_conductor(self):
        self.assertAlmostEqual(
            current_density_a_per_mm2(3.0, 0.5), 6.0, places=9
        )

    def test_a_zero_conductor_is_rejected(self):
        with self.assertRaises(ValueError):
            current_density_a_per_mm2(3.0, 0.0)

    def test_a_hot_winding_has_more_resistance_than_a_cold_one(self):
        self.assertGreater(
            winding_resistance_ohm(0.12, 95.0), winding_resistance_ohm(0.12, 20.0)
        )

    def test_resistance_at_the_reference_temperature_is_the_cold_value(self):
        reference = DEFAULT_CLASS3_MAGNETICS_POLICY[
            "resistance_reference_temperature_c"
        ]
        self.assertAlmostEqual(
            winding_resistance_ohm(0.12, reference), 0.12, places=9
        )

    def test_a_temperature_off_the_modelled_range_is_rejected(self):
        with self.assertRaises(ValueError):
            winding_resistance_ohm(0.12, -400.0)

    def test_copper_loss_is_current_squared_times_resistance(self):
        self.assertAlmostEqual(copper_loss_w(2.0, 0.15), 0.6, places=9)

    def test_a_zero_resistance_is_rejected(self):
        with self.assertRaises(ValueError):
            copper_loss_w(2.0, 0.0)


class CoreLossTests(unittest.TestCase):
    def test_the_power_law_returns_watts(self):
        self.assertAlmostEqual(
            core_loss_w(1.0, 1.0, 1.0, 1.0, 1.0, 1000.0), 1.0, places=9
        )

    def test_core_loss_climbs_steeply_with_flux(self):
        low = core_loss_w(1.5, 1.5, 2.6, 100.0, 0.20, 5.0)
        high = core_loss_w(1.5, 1.5, 2.6, 100.0, 0.30, 5.0)
        self.assertGreater(high, low * 2.0)

    def test_core_loss_climbs_with_frequency(self):
        self.assertGreater(
            core_loss_w(1.5, 1.5, 2.6, 200.0, 0.30, 5.0),
            core_loss_w(1.5, 1.5, 2.6, 100.0, 0.30, 5.0),
        )

    def test_a_zero_exponent_is_rejected(self):
        with self.assertRaises(ValueError):
            core_loss_w(1.5, 0.0, 2.6, 100.0, 0.30, 5.0)

    def test_a_zero_volume_is_rejected(self):
        with self.assertRaises(ValueError):
            core_loss_w(1.5, 1.5, 2.6, 100.0, 0.30, 0.0)


class ThermalTests(unittest.TestCase):
    def test_rise_is_loss_times_thermal_resistance(self):
        self.assertAlmostEqual(temperature_rise_k(1.0, 25.0), 25.0, places=9)

    def test_a_zero_thermal_resistance_is_rejected(self):
        with self.assertRaises(ValueError):
            temperature_rise_k(1.0, 0.0)

    def test_the_derated_limit_sits_below_the_temperature_index(self):
        self.assertLess(
            derated_insulation_limit_c("class-f"),
            INSULATION_TEMPERATURE_INDEX_C["class-f"],
        )

    def test_an_unknown_insulation_system_is_rejected(self):
        with self.assertRaises(ValueError):
            derated_insulation_limit_c("class-z")

    def test_every_catalogued_insulation_system_is_priced(self):
        for system in INSULATION_TEMPERATURE_INDEX_C:
            self.assertGreater(derated_insulation_limit_c(system), 0.0)

    def test_the_margin_is_the_derated_limit_less_the_hot_spot(self):
        limit = derated_insulation_limit_c("class-f")
        self.assertAlmostEqual(
            hot_spot_margin_k(limit - 20.0, "class-f"), 20.0, places=9
        )

    def test_a_hot_spot_above_the_limit_gives_a_negative_margin(self):
        self.assertLess(hot_spot_margin_k(200.0, "class-f"), 0.0)


class DielectricTests(unittest.TestCase):
    def test_the_withstand_is_twice_working_plus_the_offset(self):
        self.assertAlmostEqual(
            required_dielectric_withstand_v(300.0), 1600.0, places=9
        )

    def test_a_negative_working_voltage_is_rejected(self):
        with self.assertRaises(ValueError):
            required_dielectric_withstand_v(-1.0)

    def test_the_offset_is_policy_driven(self):
        self.assertAlmostEqual(
            required_dielectric_withstand_v(300.0, {"dielectric_offset_v": 500.0}),
            1100.0,
            places=9,
        )


class ScreeningTests(unittest.TestCase):
    def test_the_base_sequence_is_always_owed(self):
        sequence = screening_sequence("bobbin-wound", 8)
        for step in BASE_SCREENING_SEQUENCE:
            self.assertIn(step, sequence)

    def test_a_potted_assembly_owes_a_radiographic_inspection(self):
        self.assertIn(
            "radiographic-inspection", screening_sequence("potted-assembly", 8)
        )

    def test_a_lot_at_the_floor_can_spare_a_destructive_sample(self):
        floor = DEFAULT_CLASS3_MAGNETICS_POLICY["destructive_sample_lot_floor"]
        self.assertIn(
            "destructive-sample-analysis", screening_sequence("bobbin-wound", floor)
        )

    def test_a_lot_below_the_floor_is_screened_whole_instead(self):
        floor = DEFAULT_CLASS3_MAGNETICS_POLICY["destructive_sample_lot_floor"]
        sequence = screening_sequence("bobbin-wound", floor - 1)
        self.assertIn("full-lot-screening-in-lieu-of-sample", sequence)
        self.assertNotIn("destructive-sample-analysis", sequence)

    def test_no_screening_step_is_listed_twice(self):
        sequence = screening_sequence("toroidal-wound", 8)
        self.assertEqual(len(sequence), len(set(sequence)))

    def test_an_unknown_construction_form_is_rejected(self):
        with self.assertRaises(ValueError):
            screening_sequence("glued-stack", 8)

    def test_a_zero_lot_is_rejected(self):
        with self.assertRaises(ValueError):
            screening_sequence("bobbin-wound", 0)

    def test_every_construction_form_adds_its_own_step(self):
        for form, step in CONSTRUCTION_FORMS.items():
            self.assertIn(step, screening_sequence(form, 8))

    def test_done_steps_are_subtracted(self):
        self.assertEqual(
            outstanding_screening("bobbin-wound", 8, FULL_SCREENING), ()
        )

    def test_a_missing_step_is_reported_outstanding(self):
        self.assertIn(
            "dielectric-withstand-test",
            outstanding_screening("bobbin-wound", 8, ["visual-inspection"]),
        )

    def test_a_non_string_done_step_is_rejected(self):
        with self.assertRaises(ValueError):
            outstanding_screening("bobbin-wound", 8, [5])


class AssessmentTests(unittest.TestCase):
    def test_a_fully_screened_reference_part_satisfies_practice(self):
        result = assess_class3_self_made_magnetics(_screened())
        self.assertEqual(result["disposition"], PRACTICE_SATISFIED)
        self.assertEqual(result["findings"], [])

    def test_an_unscreened_reference_part_owes_screening(self):
        result = assess_class3_self_made_magnetics(CLEAN_CASE)
        self.assertEqual(result["disposition"], SCREENING_OUTSTANDING)

    def test_a_missing_foundation_outranks_every_other_finding(self):
        result = assess_class3_self_made_magnetics(
            _case(foundations_held=[], saturation_flux_t=0.05)
        )
        self.assertEqual(result["disposition"], PART_NOT_ADMISSIBLE)

    def test_a_saturating_core_is_a_design_finding(self):
        result = assess_class3_self_made_magnetics(_screened(saturation_flux_t=0.32))
        self.assertEqual(result["disposition"], DESIGN_NONCONFORMING)
        self.assertFalse(result["flux_ok"])

    def test_a_flux_exactly_on_the_saturation_limit_is_acceptable(self):
        limit = DEFAULT_CLASS3_MAGNETICS_POLICY["max_saturation_utilisation"]
        result = assess_class3_self_made_magnetics(
            _screened(saturation_flux_t=0.3 / limit)
        )
        self.assertAlmostEqual(result["saturation_utilisation"], limit, places=9)
        self.assertTrue(result["flux_ok"])

    def test_an_overfilled_window_is_a_design_finding(self):
        result = assess_class3_self_made_magnetics(_screened(window_mm2=30.0))
        self.assertEqual(result["disposition"], DESIGN_NONCONFORMING)
        self.assertFalse(result["fill_ok"])

    def test_an_overdriven_winding_is_a_design_finding(self):
        result = assess_class3_self_made_magnetics(_screened(winding_current_a=5.0))
        self.assertEqual(result["disposition"], DESIGN_NONCONFORMING)
        self.assertFalse(result["current_density_ok"])

    def test_a_thin_thermal_margin_is_a_design_finding(self):
        result = assess_class3_self_made_magnetics(
            _screened(ambient_temperature_c=105.0, winding_temperature_c=140.0)
        )
        self.assertEqual(result["disposition"], DESIGN_NONCONFORMING)
        self.assertFalse(result["hot_spot_margin_ok"])

    def test_a_resistance_taken_below_the_hot_spot_is_a_finding(self):
        result = assess_class3_self_made_magnetics(_screened(winding_temperature_c=40.0))
        self.assertEqual(result["disposition"], DESIGN_NONCONFORMING)
        self.assertFalse(result["resistance_reference_ok"])

    def test_an_underrated_insulation_system_is_a_design_finding(self):
        result = assess_class3_self_made_magnetics(
            _screened(insulation_withstand_rating_v=900.0)
        )
        self.assertEqual(result["disposition"], DESIGN_NONCONFORMING)
        self.assertFalse(result["withstand_ok"])

    def test_an_insulation_rating_exactly_on_its_requirement_passes(self):
        needed = required_dielectric_withstand_v(CLEAN_CASE["working_voltage_v"])
        result = assess_class3_self_made_magnetics(
            _screened(insulation_withstand_rating_v=needed)
        )
        self.assertTrue(result["withstand_ok"])
        self.assertAlmostEqual(result["required_withstand_v"], needed, places=9)

    def test_a_design_finding_outranks_outstanding_screening(self):
        result = assess_class3_self_made_magnetics(_case(window_mm2=30.0))
        self.assertEqual(result["disposition"], DESIGN_NONCONFORMING)

    def test_a_small_lot_is_screened_whole_and_can_still_satisfy_practice(self):
        sequence = screening_sequence("bobbin-wound", 2)
        result = assess_class3_self_made_magnetics(
            _case(flight_lot_size=2, screening_done=list(sequence))
        )
        self.assertEqual(result["disposition"], PRACTICE_SATISFIED)
        self.assertIn("full-lot-screening-in-lieu-of-sample", result["screening_sequence"])

    def test_the_total_loss_is_the_sum_of_both_losses(self):
        result = assess_class3_self_made_magnetics(_screened())
        self.assertAlmostEqual(
            result["total_loss_w"],
            result["copper_loss_w"] + result["core_loss_w"],
            places=9,
        )

    def test_a_case_missing_a_field_is_rejected(self):
        case = _screened()
        del case["core_volume_cm3"]
        with self.assertRaises(ValueError):
            assess_class3_self_made_magnetics(case)

    def test_an_unknown_insulation_system_is_rejected_by_the_case(self):
        with self.assertRaises(ValueError):
            validate_magnetics_case(_screened(insulation_system="class-z"))

    def test_case_validation_returns_the_reference_case(self):
        case = _screened()
        self.assertIs(validate_magnetics_case(case), case)

    def test_every_construction_form_routes_to_a_disposition(self):
        for form in CONSTRUCTION_FORMS:
            sequence = screening_sequence(form, 8)
            result = assess_class3_self_made_magnetics(
                _case(construction_form=form, screening_done=list(sequence))
            )
            self.assertEqual(result["disposition"], PRACTICE_SATISFIED)


if __name__ == "__main__":
    unittest.main()
