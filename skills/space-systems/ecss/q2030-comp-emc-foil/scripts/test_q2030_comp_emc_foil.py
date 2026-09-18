#!/usr/bin/env python3
"""Contract test for the complementary conductive-foil EMC shielding leaf."""

import math
import unittest

from q2030_comp_emc_foil_logic import (
    assess_foil_shield,
    evaluate_foil_application,
    evaluate_foil_termination,
    foil_thickness_adequate,
    helical_pitch_mm,
    inductive_reactance_ohm,
    layers_over_a_point,
    pigtail_inductance_nh,
    skin_depth_mm,
    tape_length_required_mm,
    termination_penalty_db,
)

COPPER_RESISTIVITY = 1.68e-8


def good_application(**overrides):
    spec = {
        "tape_width_mm": 25.0,
        "overlap_fraction": 0.50,
        "foil_thickness_mm": 0.050,
        "resistivity_ohm_m": COPPER_RESISTIVITY,
        "relative_permeability": 1.0,
        "lowest_frequency_hz": 2.0e6,
        "required_skin_depths": 1.0,
        "required_layers": 2.0,
        "conductive_face_inward": True,
        "bundle_length_mm": 1000.0,
        "bundle_circumference_mm": 60.0,
    }
    spec.update(overrides)
    return spec


def good_termination(**overrides):
    spec = {
        "drain_wire_present": True,
        "drain_continuous_with_foil": True,
        "pigtail_length_mm": 10.0,
        "inductance_per_mm_nh": 1.0,
        "highest_frequency_hz": 1.0e7,
        "reference_impedance_ohm": 1.0,
        "allowed_penalty_db": 6.0,
    }
    spec.update(overrides)
    return spec


class TestSkinDepth(unittest.TestCase):
    def test_copper_at_one_megahertz(self):
        self.assertAlmostEqual(skin_depth_mm(COPPER_RESISTIVITY, 1.0, 1.0e6), 0.0652341146, places=9)

    def test_a_hundredfold_lower_frequency_is_ten_times_deeper(self):
        low = skin_depth_mm(COPPER_RESISTIVITY, 1.0, 1.0e4)
        high = skin_depth_mm(COPPER_RESISTIVITY, 1.0, 1.0e6)
        self.assertAlmostEqual(low, 10.0 * high, places=9)

    def test_a_permeable_foil_is_shallower(self):
        plain = skin_depth_mm(COPPER_RESISTIVITY, 1.0, 1.0e6)
        permeable = skin_depth_mm(COPPER_RESISTIVITY, 100.0, 1.0e6)
        self.assertAlmostEqual(permeable * 10.0, plain, places=9)

    def test_zero_frequency_raises(self):
        with self.assertRaises(ValueError):
            skin_depth_mm(COPPER_RESISTIVITY, 1.0, 0.0)

    def test_non_numeric_resistivity_raises(self):
        with self.assertRaises(ValueError):
            skin_depth_mm("1.68e-8", 1.0, 1.0e6)


class TestThicknessAdequacy(unittest.TestCase):
    def test_thicker_than_one_skin_depth_is_adequate(self):
        self.assertTrue(foil_thickness_adequate(0.100, 0.065, 1.0))

    def test_exactly_one_skin_depth_is_adequate(self):
        self.assertTrue(foil_thickness_adequate(0.065, 0.065, 1.0))

    def test_thinner_than_the_requirement_is_not_adequate(self):
        self.assertFalse(foil_thickness_adequate(0.020, 0.065, 1.0))

    def test_a_three_skin_depth_requirement_bites(self):
        self.assertFalse(foil_thickness_adequate(0.100, 0.065, 3.0))

    def test_zero_thickness_raises(self):
        with self.assertRaises(ValueError):
            foil_thickness_adequate(0.0, 0.065, 1.0)


class TestWrapGeometry(unittest.TestCase):
    def test_half_overlap_halves_the_pitch(self):
        self.assertAlmostEqual(helical_pitch_mm(25.0, 0.50), 12.5, places=9)

    def test_no_overlap_advances_a_full_width(self):
        self.assertAlmostEqual(helical_pitch_mm(25.0, 0.0), 25.0, places=9)

    def test_half_overlap_gives_two_layers(self):
        self.assertAlmostEqual(layers_over_a_point(25.0, 0.50), 2.0, places=9)

    def test_two_thirds_overlap_gives_three_layers(self):
        self.assertAlmostEqual(layers_over_a_point(30.0, 2.0 / 3.0), 3.0, places=9)

    def test_quarter_overlap_falls_short_of_two_layers(self):
        self.assertLess(layers_over_a_point(25.0, 0.25), 2.0)

    def test_full_overlap_raises(self):
        with self.assertRaises(ValueError):
            helical_pitch_mm(25.0, 1.0)

    def test_negative_overlap_raises(self):
        with self.assertRaises(ValueError):
            layers_over_a_point(25.0, -0.1)


class TestTapeLength(unittest.TestCase):
    def test_tape_length_follows_the_helix(self):
        expected = (1000.0 / 12.5) * math.hypot(60.0, 12.5)
        self.assertAlmostEqual(
            tape_length_required_mm(1000.0, 60.0, 25.0, 0.50), expected, places=9
        )

    def test_more_overlap_consumes_more_tape(self):
        light = tape_length_required_mm(1000.0, 60.0, 25.0, 0.25)
        heavy = tape_length_required_mm(1000.0, 60.0, 25.0, 0.75)
        self.assertLess(light, heavy)

    def test_zero_bundle_length_raises(self):
        with self.assertRaises(ValueError):
            tape_length_required_mm(0.0, 60.0, 25.0, 0.50)


class TestPigtail(unittest.TestCase):
    def test_inductance_scales_with_length(self):
        self.assertAlmostEqual(pigtail_inductance_nh(50.0, 1.0), 50.0, places=9)

    def test_a_zero_length_pigtail_has_no_inductance(self):
        self.assertAlmostEqual(pigtail_inductance_nh(0.0), 0.0, places=12)

    def test_negative_length_raises(self):
        with self.assertRaises(ValueError):
            pigtail_inductance_nh(-5.0)

    def test_reactance_is_two_pi_f_l(self):
        self.assertAlmostEqual(
            inductive_reactance_ohm(50.0, 1.0e8), 2.0 * math.pi * 1.0e8 * 50.0e-9, places=9
        )

    def test_zero_inductance_has_no_reactance(self):
        self.assertAlmostEqual(inductive_reactance_ohm(0.0, 1.0e8), 0.0, places=12)

    def test_negative_inductance_raises(self):
        with self.assertRaises(ValueError):
            inductive_reactance_ohm(-1.0, 1.0e8)


class TestTerminationPenalty(unittest.TestCase):
    def test_a_circumferential_termination_costs_nothing(self):
        self.assertAlmostEqual(termination_penalty_db(0.0, 1.0), 0.0, places=12)

    def test_a_reactance_equal_to_the_reference_costs_six_decibels(self):
        self.assertAlmostEqual(termination_penalty_db(1.0, 1.0), 6.0205999132, places=9)

    def test_a_ninefold_reactance_costs_twenty_decibels(self):
        self.assertAlmostEqual(termination_penalty_db(9.0, 1.0), 20.0, places=9)

    def test_penalty_rises_with_reactance(self):
        self.assertLess(termination_penalty_db(2.0, 1.0), termination_penalty_db(20.0, 1.0))

    def test_negative_reactance_raises(self):
        with self.assertRaises(ValueError):
            termination_penalty_db(-1.0, 1.0)

    def test_zero_reference_impedance_raises(self):
        with self.assertRaises(ValueError):
            termination_penalty_db(1.0, 0.0)


class TestEvaluateApplication(unittest.TestCase):
    def test_sound_application_has_no_finding(self):
        self.assertTrue(evaluate_foil_application(good_application())["conforming"])

    def test_thin_foil_at_a_low_frequency_is_a_finding(self):
        result = evaluate_foil_application(good_application(lowest_frequency_hz=1.0e4))
        self.assertFalse(result["thickness_adequate"])
        self.assertFalse(result["conforming"])

    def test_light_overlap_is_a_finding(self):
        self.assertFalse(evaluate_foil_application(good_application(overlap_fraction=0.20))["conforming"])

    def test_tape_applied_carrier_side_inward_is_a_finding(self):
        result = evaluate_foil_application(good_application(conductive_face_inward=False))
        self.assertFalse(result["conforming"])

    def test_pitch_and_layers_are_reported(self):
        result = evaluate_foil_application(good_application())
        self.assertAlmostEqual(result["pitch_mm"], 12.5, places=9)
        self.assertAlmostEqual(result["layers_over_a_point"], 2.0, places=9)

    def test_tape_length_is_reported(self):
        result = evaluate_foil_application(good_application())
        self.assertGreater(result["tape_length_required_mm"], 1000.0)

    def test_missing_application_key_raises(self):
        spec = good_application()
        del spec["overlap_fraction"]
        with self.assertRaises(ValueError):
            evaluate_foil_application(spec)


class TestEvaluateTermination(unittest.TestCase):
    def test_short_pigtail_inside_the_allowance_conforms(self):
        self.assertTrue(evaluate_foil_termination(good_termination())["conforming"])

    def test_long_pigtail_at_a_high_frequency_is_a_finding(self):
        result = evaluate_foil_termination(
            good_termination(pigtail_length_mm=100.0, highest_frequency_hz=1.0e8)
        )
        self.assertFalse(result["conforming"])

    def test_absent_drain_wire_is_a_finding(self):
        self.assertFalse(evaluate_foil_termination(good_termination(drain_wire_present=False))["conforming"])

    def test_discontinuous_drain_wire_is_a_finding(self):
        result = evaluate_foil_termination(good_termination(drain_continuous_with_foil=False))
        self.assertFalse(result["conforming"])

    def test_penalty_is_reported_in_decibels(self):
        result = evaluate_foil_termination(good_termination())
        self.assertAlmostEqual(
            result["penalty_db"],
            termination_penalty_db(inductive_reactance_ohm(10.0, 1.0e7), 1.0),
            places=9,
        )

    def test_negative_allowance_raises(self):
        with self.assertRaises(ValueError):
            evaluate_foil_termination(good_termination(allowed_penalty_db=-1.0))

    def test_missing_termination_key_raises(self):
        spec = good_termination()
        del spec["highest_frequency_hz"]
        with self.assertRaises(ValueError):
            evaluate_foil_termination(spec)


class TestAssessFoilShield(unittest.TestCase):
    def test_clean_run_is_compliant(self):
        report = assess_foil_shield(
            {"application": good_application(), "termination": good_termination()}
        )
        self.assertTrue(report["compliant"])
        self.assertEqual(report["findings"], [])

    def test_application_finding_fails_the_run(self):
        report = assess_foil_shield(
            {
                "application": good_application(overlap_fraction=0.10),
                "termination": good_termination(),
            }
        )
        self.assertFalse(report["compliant"])

    def test_termination_finding_fails_the_run(self):
        report = assess_foil_shield(
            {
                "application": good_application(),
                "termination": good_termination(
                    pigtail_length_mm=150.0, highest_frequency_hz=1.0e8
                ),
            }
        )
        self.assertFalse(report["compliant"])

    def test_both_halves_are_reported(self):
        report = assess_foil_shield(
            {"application": good_application(), "termination": good_termination()}
        )
        self.assertIn("skin_depth_mm", report["application"])
        self.assertIn("penalty_db", report["termination"])

    def test_missing_half_raises(self):
        with self.assertRaises(ValueError):
            assess_foil_shield({"application": good_application()})

    def test_non_mapping_spec_raises(self):
        with self.assertRaises(ValueError):
            assess_foil_shield(["application"])


if __name__ == "__main__":
    unittest.main()
