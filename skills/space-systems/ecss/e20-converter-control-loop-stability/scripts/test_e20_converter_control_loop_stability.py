#!/usr/bin/env python3
"""Gate 3 contract test: ECSS-E-ST-20C clause 5.7.5 converter and
regulator control-loop stability margins.

Exercises scripts/e20_converter_control_loop_stability_logic.py (stdlib
unittest, offline). Contract: a loop kind maps to exactly one category
and an unrecognized kind raises; the category carries a default margin
pair that a project requirement overrides field by field, rejecting a
negative or unknown target; the worst-case corner set is the full
combination of the declared extremes and a single-valued or
unrecognized axis raises; the open-loop magnitude and phase follow the
pole, zero, right-half-plane-zero and transport-delay contributions,
checked against closed-form values at the break frequencies; the gain
crossover is the unity-magnitude frequency and the phase crossover is
the minus-one-hundred-and-eighty-degree frequency, with a band that
brackets neither raising and an absent phase crossover giving an
unbounded gain margin; and the aggregated review is compliant only when
the coverage and margin lists are both empty.
"""

import math
import os
import sys
import unittest

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import e20_converter_control_loop_stability_logic as cls  # noqa: E402

# A single dominant pole with 20 dB of gain: unity magnitude sits at
# sqrt(10^2 - 1) = sqrt(99) Hz and the phase there is -atan(sqrt(99)).
ANALYTIC_MODEL = {"dc_gain_db": 20.0, "pole_hz": [1.0]}
ANALYTIC_BAND = (0.1, 1000.0)
ANALYTIC_CROSSOVER_HZ = 9.949874371066199
ANALYTIC_PHASE_MARGIN_DEG = 95.73917039

# A compensated switching-converter loop: dominant pole, compensation
# zero, two parasitic poles and a 2 us modulator delay.
CLEAN_MODEL = {
    "dc_gain_db": 76.0,
    "pole_hz": [1.0, 5000.0, 20000.0],
    "zero_hz": [1500.0],
    "delay_s": 2.0e-6,
}
# The same loop at a high-gain corner: 14 dB more loop gain pushes the
# crossover into the delay-dominated region and the margin is lost.
HOT_GAIN_MODEL = {
    "dc_gain_db": 90.0,
    "pole_hz": [1.0, 5000.0, 20000.0],
    "zero_hz": [1500.0],
    "delay_s": 2.0e-6,
}

CORNER_AXES = {
    "temperature": ["cold", "hot"],
    "input_voltage": ["min", "max"],
    "load": ["min", "max"],
}


def _corner_models(model):
    """One loop model per enumerated worst-case corner."""
    return {
        cls.corner_label(corner): dict(model)
        for corner in cls.enumerate_worst_case_corners(CORNER_AXES)
    }


def _clean_case():
    return {
        "loop_id": "EPS-BCR-LOOP-01",
        "loop_kind": "buck_converter",
        "corner_axes": CORNER_AXES,
        "corner_models": _corner_models(CLEAN_MODEL),
        "search_band_hz": (1.0, 1.0e6),
    }


class CategorizeLoopKindTests(unittest.TestCase):
    def test_buck_converter_is_a_switching_converter(self):
        self.assertEqual(
            cls.categorize_loop_kind("buck_converter"), "switching_converter"
        )

    def test_battery_charge_regulator_is_a_switching_converter(self):
        self.assertEqual(
            cls.categorize_loop_kind("battery_charge_regulator"),
            "switching_converter",
        )

    def test_low_dropout_regulator_is_a_linear_regulator(self):
        self.assertEqual(
            cls.categorize_loop_kind("low_dropout_regulator"), "linear_regulator"
        )

    def test_main_bus_voltage_loop_is_a_bus_control_loop(self):
        self.assertEqual(
            cls.categorize_loop_kind("main_bus_voltage_control_loop"),
            "bus_control_loop",
        )

    def test_every_kind_maps_to_exactly_one_category(self):
        families = (
            cls.SWITCHING_CONVERTER_KINDS,
            cls.LINEAR_REGULATOR_KINDS,
            cls.BUS_CONTROL_LOOP_KINDS,
        )
        for index, family in enumerate(families):
            for other in families[index + 1:]:
                self.assertEqual(family & other, frozenset())

    def test_unrecognized_kind_raises(self):
        with self.assertRaises(ValueError):
            cls.categorize_loop_kind("thermostat_loop")

    def test_missing_kind_raises(self):
        with self.assertRaises(ValueError):
            cls.categorize_loop_kind(None)


class MarginTargetTests(unittest.TestCase):
    def test_switching_converter_defaults(self):
        targets = cls.required_margin_targets("switching_converter")
        self.assertAlmostEqual(targets["phase_margin_deg"], 45.0, places=9)
        self.assertAlmostEqual(targets["gain_margin_db"], 6.0, places=9)

    def test_linear_regulator_demands_more_than_a_switcher(self):
        linear = cls.required_margin_targets("linear_regulator")
        switching = cls.required_margin_targets("switching_converter")
        self.assertGreater(
            linear["phase_margin_deg"], switching["phase_margin_deg"]
        )
        self.assertGreater(linear["gain_margin_db"], switching["gain_margin_db"])

    def test_requirement_overrides_one_field_and_keeps_the_other(self):
        targets = cls.required_margin_targets(
            "switching_converter", {"phase_margin_deg": 55.0}
        )
        self.assertAlmostEqual(targets["phase_margin_deg"], 55.0, places=9)
        self.assertAlmostEqual(targets["gain_margin_db"], 6.0, places=9)

    def test_defaults_are_not_mutated_by_an_override(self):
        cls.required_margin_targets("switching_converter", {"phase_margin_deg": 55.0})
        self.assertAlmostEqual(
            cls.DEFAULT_MARGIN_TARGETS["switching_converter"]["phase_margin_deg"],
            45.0,
            places=9,
        )

    def test_unknown_category_raises(self):
        with self.assertRaises(ValueError):
            cls.required_margin_targets("analog_filter")

    def test_unknown_target_name_raises(self):
        with self.assertRaises(ValueError):
            cls.required_margin_targets(
                "switching_converter", {"modulus_margin_db": 4.0}
            )

    def test_negative_target_raises(self):
        with self.assertRaises(ValueError):
            cls.required_margin_targets(
                "switching_converter", {"phase_margin_deg": -5.0}
            )

    def test_boolean_target_raises(self):
        with self.assertRaises(ValueError):
            cls.required_margin_targets(
                "switching_converter", {"phase_margin_deg": True}
            )

    def test_requirement_that_is_not_a_mapping_raises(self):
        with self.assertRaises(ValueError):
            cls.required_margin_targets("switching_converter", [45.0, 6.0])


class CornerEnumerationTests(unittest.TestCase):
    def test_three_two_valued_axes_give_eight_corners(self):
        self.assertEqual(len(cls.enumerate_worst_case_corners(CORNER_AXES)), 8)

    def test_corner_labels_are_unique_and_ordered(self):
        labels = [
            cls.corner_label(corner)
            for corner in cls.enumerate_worst_case_corners(CORNER_AXES)
        ]
        self.assertEqual(len(set(labels)), 8)
        self.assertEqual(labels[0], "temperature=cold,input_voltage=min,load=min")

    def test_missing_axis_raises(self):
        axes = dict(CORNER_AXES)
        del axes["load"]
        with self.assertRaises(ValueError):
            cls.enumerate_worst_case_corners(axes)

    def test_unrecognized_axis_raises(self):
        axes = dict(CORNER_AXES)
        axes["radiation"] = ["bol", "eol"]
        with self.assertRaises(ValueError):
            cls.enumerate_worst_case_corners(axes)

    def test_single_valued_axis_raises(self):
        axes = dict(CORNER_AXES)
        axes["temperature"] = ["nominal"]
        with self.assertRaises(ValueError):
            cls.enumerate_worst_case_corners(axes)

    def test_repeated_extreme_raises(self):
        axes = dict(CORNER_AXES)
        axes["load"] = ["min", "min"]
        with self.assertRaises(ValueError):
            cls.enumerate_worst_case_corners(axes)

    def test_empty_axis_mapping_raises(self):
        with self.assertRaises(ValueError):
            cls.enumerate_worst_case_corners({})

    def test_corner_label_missing_axis_raises(self):
        with self.assertRaises(ValueError):
            cls.corner_label({"temperature": "cold"})


class FrequencyResponseTests(unittest.TestCase):
    def test_single_pole_drops_three_decibels_at_its_break(self):
        model = {"dc_gain_db": 0.0, "pole_hz": [100.0]}
        self.assertAlmostEqual(cls.loop_gain_db(model, 100.0), -3.0102999566, places=8)

    def test_two_coincident_poles_drop_six_decibels(self):
        model = {"dc_gain_db": 0.0, "pole_hz": [100.0, 100.0]}
        self.assertAlmostEqual(cls.loop_gain_db(model, 100.0), -6.0205999132, places=8)

    def test_single_pole_lags_forty_five_degrees_at_its_break(self):
        model = {"dc_gain_db": 0.0, "pole_hz": [100.0]}
        self.assertAlmostEqual(cls.loop_phase_deg(model, 100.0), -45.0, places=9)

    def test_zero_lifts_three_decibels_and_leads_forty_five_degrees(self):
        model = {"dc_gain_db": 0.0, "pole_hz": [1.0e9], "zero_hz": [100.0]}
        self.assertAlmostEqual(cls.loop_gain_db(model, 100.0), 3.0102999566, places=6)
        self.assertAlmostEqual(cls.loop_phase_deg(model, 100.0), 45.0, places=4)

    def test_right_half_plane_zero_lifts_gain_but_lags_phase(self):
        model = {"dc_gain_db": 0.0, "pole_hz": [1.0e9], "rhp_zero_hz": 100.0}
        self.assertAlmostEqual(cls.loop_gain_db(model, 100.0), 3.0102999566, places=6)
        self.assertAlmostEqual(cls.loop_phase_deg(model, 100.0), -45.0, places=4)

    def test_transport_delay_is_all_pass_and_lags_in_proportion(self):
        model = {"dc_gain_db": 0.0, "pole_hz": [1.0e9], "delay_s": 1.0e-3}
        self.assertAlmostEqual(cls.loop_gain_db(model, 100.0), 0.0, places=6)
        self.assertAlmostEqual(cls.loop_phase_deg(model, 100.0), -36.0, places=4)

    def test_gain_falls_monotonically_above_the_dominant_pole(self):
        previous = cls.loop_gain_db(CLEAN_MODEL, 100.0)
        for frequency in (1000.0, 10000.0, 100000.0):
            current = cls.loop_gain_db(CLEAN_MODEL, frequency)
            self.assertLess(current, previous)
            previous = current

    def test_zero_frequency_raises(self):
        with self.assertRaises(ValueError):
            cls.loop_gain_db(CLEAN_MODEL, 0.0)

    def test_negative_frequency_raises(self):
        with self.assertRaises(ValueError):
            cls.loop_phase_deg(CLEAN_MODEL, -10.0)

    def test_model_without_poles_raises(self):
        with self.assertRaises(ValueError):
            cls.loop_gain_db({"dc_gain_db": 10.0, "pole_hz": []}, 100.0)

    def test_non_positive_pole_raises(self):
        with self.assertRaises(ValueError):
            cls.loop_gain_db({"dc_gain_db": 10.0, "pole_hz": [0.0]}, 100.0)

    def test_negative_delay_raises(self):
        model = {"dc_gain_db": 0.0, "pole_hz": [100.0], "delay_s": -1.0e-6}
        with self.assertRaises(ValueError):
            cls.loop_phase_deg(model, 100.0)

    def test_model_that_is_not_a_mapping_raises(self):
        with self.assertRaises(ValueError):
            cls.loop_gain_db([60.0, 1.0], 100.0)

    def test_non_finite_dc_gain_raises(self):
        with self.assertRaises(ValueError):
            cls.loop_gain_db({"dc_gain_db": float("inf"), "pole_hz": [1.0]}, 10.0)


class CrossoverTests(unittest.TestCase):
    def test_analytic_gain_crossover_matches_closed_form(self):
        self.assertAlmostEqual(
            cls.gain_crossover_hz(ANALYTIC_MODEL, ANALYTIC_BAND),
            ANALYTIC_CROSSOVER_HZ,
            places=6,
        )

    def test_magnitude_is_unity_at_the_reported_gain_crossover(self):
        crossover = cls.gain_crossover_hz(CLEAN_MODEL, (1.0, 1.0e6))
        self.assertAlmostEqual(cls.loop_gain_db(CLEAN_MODEL, crossover), 0.0, places=6)

    def test_analytic_phase_margin_matches_closed_form(self):
        self.assertAlmostEqual(
            cls.phase_margin_deg(ANALYTIC_MODEL, ANALYTIC_BAND),
            ANALYTIC_PHASE_MARGIN_DEG,
            places=4,
        )

    def test_band_starting_below_unity_gain_raises(self):
        with self.assertRaises(ValueError):
            cls.gain_crossover_hz(ANALYTIC_MODEL, (100.0, 1000.0))

    def test_band_ending_above_unity_gain_raises(self):
        with self.assertRaises(ValueError):
            cls.gain_crossover_hz(ANALYTIC_MODEL, (0.1, 5.0))

    def test_inverted_band_raises(self):
        with self.assertRaises(ValueError):
            cls.gain_crossover_hz(CLEAN_MODEL, (1.0e6, 1.0))

    def test_band_that_is_not_a_pair_raises(self):
        with self.assertRaises(ValueError):
            cls.gain_crossover_hz(CLEAN_MODEL, 1000.0)

    def test_phase_is_minus_one_eighty_at_the_reported_phase_crossover(self):
        model = {"dc_gain_db": 0.0, "pole_hz": [1.0], "delay_s": 1.0e-3}
        crossover = cls.phase_crossover_hz(model, (0.1, 1000.0))
        self.assertIsNotNone(crossover)
        self.assertAlmostEqual(cls.loop_phase_deg(model, crossover), -180.0, places=6)

    def test_single_pole_loop_has_no_phase_crossover(self):
        self.assertIsNone(cls.phase_crossover_hz(ANALYTIC_MODEL, ANALYTIC_BAND))

    def test_absent_phase_crossover_gives_an_unbounded_gain_margin(self):
        self.assertTrue(
            math.isinf(cls.gain_margin_db(ANALYTIC_MODEL, ANALYTIC_BAND))
        )

    def test_band_starting_past_minus_one_eighty_raises(self):
        model = {"dc_gain_db": 0.0, "pole_hz": [1.0], "delay_s": 1.0e-3}
        with self.assertRaises(ValueError):
            cls.phase_crossover_hz(model, (1000.0, 10000.0))

    def test_clean_loop_holds_a_practical_margin_pair(self):
        band = (1.0, 1.0e6)
        self.assertGreater(cls.phase_margin_deg(CLEAN_MODEL, band), 45.0)
        self.assertLess(cls.phase_margin_deg(CLEAN_MODEL, band), 60.0)
        self.assertGreater(cls.gain_margin_db(CLEAN_MODEL, band), 6.0)

    def test_high_gain_corner_pushes_the_crossover_up(self):
        band = (1.0, 1.0e6)
        self.assertGreater(
            cls.gain_crossover_hz(HOT_GAIN_MODEL, band),
            cls.gain_crossover_hz(CLEAN_MODEL, band),
        )


class CornerEvaluationTests(unittest.TestCase):
    def test_clean_corner_reports_no_finding(self):
        targets = cls.required_margin_targets("switching_converter")
        result = cls.evaluate_corner_margins("c1", CLEAN_MODEL, targets, (1.0, 1.0e6))
        self.assertEqual(result["findings"], [])

    def test_high_gain_corner_reports_both_margins(self):
        targets = cls.required_margin_targets("switching_converter")
        result = cls.evaluate_corner_margins(
            "c1", HOT_GAIN_MODEL, targets, (1.0, 1.0e6)
        )
        self.assertEqual(len(result["findings"]), 2)

    def test_target_exactly_on_the_achieved_margin_is_compliant(self):
        band = (1.0, 1.0e6)
        achieved = cls.phase_margin_deg(CLEAN_MODEL, band)
        targets = {"phase_margin_deg": achieved, "gain_margin_db": 0.0}
        result = cls.evaluate_corner_margins("c1", CLEAN_MODEL, targets, band)
        self.assertEqual(result["findings"], [])

    def test_target_one_representation_step_above_is_still_compliant(self):
        band = (1.0, 1.0e6)
        achieved = cls.phase_margin_deg(CLEAN_MODEL, band)
        targets = {
            "phase_margin_deg": achieved + 1.0e-10,
            "gain_margin_db": 0.0,
        }
        result = cls.evaluate_corner_margins("c1", CLEAN_MODEL, targets, band)
        self.assertEqual(result["findings"], [])

    def test_target_meaningfully_above_the_achieved_margin_fails(self):
        band = (1.0, 1.0e6)
        achieved = cls.phase_margin_deg(CLEAN_MODEL, band)
        targets = {"phase_margin_deg": achieved + 0.5, "gain_margin_db": 0.0}
        result = cls.evaluate_corner_margins("c1", CLEAN_MODEL, targets, band)
        self.assertEqual(len(result["findings"]), 1)

    def test_targets_missing_a_field_raises(self):
        with self.assertRaises(ValueError):
            cls.evaluate_corner_margins(
                "c1", CLEAN_MODEL, {"phase_margin_deg": 45.0}, (1.0, 1.0e6)
            )


class AssessmentTests(unittest.TestCase):
    def test_clean_case_is_compliant_over_all_eight_corners(self):
        result = cls.assess_control_loop_stability(_clean_case())
        self.assertTrue(result["compliant"])
        self.assertEqual(result["corner_count"], 8)
        self.assertEqual(len(result["corner_results"]), 8)
        self.assertEqual(result["coverage_findings"], [])
        self.assertEqual(result["margin_findings"], [])

    def test_reported_category_follows_the_loop_kind(self):
        result = cls.assess_control_loop_stability(_clean_case())
        self.assertEqual(result["category"], "switching_converter")

    def test_missing_corner_model_is_a_coverage_finding(self):
        case = _clean_case()
        dropped = "temperature=cold,input_voltage=max,load=min"
        del case["corner_models"][dropped]
        result = cls.assess_control_loop_stability(case)
        self.assertFalse(result["compliant"])
        self.assertEqual(len(result["coverage_findings"]), 1)
        self.assertIn(dropped, result["coverage_findings"][0])
        self.assertEqual(len(result["corner_results"]), 7)

    def test_untraceable_corner_model_is_a_coverage_finding(self):
        case = _clean_case()
        case["corner_models"]["temperature=warm,input_voltage=min,load=min"] = dict(
            CLEAN_MODEL
        )
        result = cls.assess_control_loop_stability(case)
        self.assertFalse(result["compliant"])
        self.assertEqual(len(result["coverage_findings"]), 1)

    def test_one_degraded_corner_fails_the_whole_loop(self):
        case = _clean_case()
        degraded = "temperature=cold,input_voltage=max,load=min"
        case["corner_models"][degraded] = dict(HOT_GAIN_MODEL)
        result = cls.assess_control_loop_stability(case)
        self.assertFalse(result["compliant"])
        self.assertEqual(result["coverage_findings"], [])
        self.assertTrue(
            any(degraded in finding for finding in result["margin_findings"])
        )

    def test_a_stricter_requirement_can_fail_a_clean_loop(self):
        case = _clean_case()
        case["requirement"] = {"phase_margin_deg": 70.0}
        result = cls.assess_control_loop_stability(case)
        self.assertFalse(result["compliant"])
        self.assertEqual(len(result["margin_findings"]), 8)

    def test_missing_loop_id_raises(self):
        case = _clean_case()
        case["loop_id"] = "  "
        with self.assertRaises(ValueError):
            cls.assess_control_loop_stability(case)

    def test_unknown_loop_kind_raises(self):
        case = _clean_case()
        case["loop_kind"] = "reaction_wheel_loop"
        with self.assertRaises(ValueError):
            cls.assess_control_loop_stability(case)

    def test_empty_corner_models_raises(self):
        case = _clean_case()
        case["corner_models"] = {}
        with self.assertRaises(ValueError):
            cls.assess_control_loop_stability(case)

    def test_case_that_is_not_a_mapping_raises(self):
        with self.assertRaises(ValueError):
            cls.assess_control_loop_stability("EPS-BCR-LOOP-01")


if __name__ == "__main__":
    unittest.main()
