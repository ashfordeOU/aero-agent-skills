#!/usr/bin/env python3
"""Contract test for the capacitance signal acquisition leaf (offline)."""

import copy
import math
import unittest

from e2008_capacitance_signal_measurement_method_logic import (
    ACCEPTED_TECHNIQUES,
    ACQUISITION_ACCEPTED,
    ACQUISITION_NOT_ACCEPTED,
    ALTERNATIVE_TECHNIQUES,
    MAX_SHUNT_BURDEN_FRACTION,
    MIN_CORNER_DECADES_ABOVE_TEST,
    MIN_SIGNAL_TO_NOISE_DB,
    SHUNT_TECHNIQUE,
    acquisition_corner_frequency_hz,
    assess_signal_acquisition,
    cell_reactance_ohm,
    corner_decades_above,
    justification_recorded,
    missing_evidence,
    required_evidence,
    sense_burden_fraction,
    shunt_inductive_corner_hz,
    signal_to_noise_db,
    signal_voltage_v,
    technique_is_preferred,
)

CELL_CAPACITANCE_F = 4.7e-7

SHUNT_CASE = {
    "technique": "shunt",
    "cell_capacitance_f": CELL_CAPACITANCE_F,
    "test_frequency_hz": 1000.0,
    "sense_resistance_ohm": 1.0,
    "input_capacitance_f": 1.0e-10,
    "shunt_inductance_h": 1.0e-9,
    "signal_current_a": 1.0e-3,
    "amplifier_noise_voltage_v": 1.0e-5,
}

TRANSFORMER_CASE = {
    "technique": "current-transformer",
    "cell_capacitance_f": CELL_CAPACITANCE_F,
    "test_frequency_hz": 1000.0,
    "sense_resistance_ohm": 1.0,
    "input_capacitance_f": 1.0e-10,
    "pickup_bandwidth_hz": 1.0e6,
    "signal_current_a": 1.0e-3,
    "amplifier_noise_voltage_v": 1.0e-5,
    "justification": "the cell return leg is bonded to the chamber, so a shunt would lift the reference",
}


def _shunt(**overrides):
    case = copy.deepcopy(SHUNT_CASE)
    case.update(overrides)
    return case


def _transformer(**overrides):
    case = copy.deepcopy(TRANSFORMER_CASE)
    case.update(overrides)
    return case


def _finding_matching(result, fragment):
    return [f for f in result["findings"] if fragment in f]


class TechniquePreferenceTests(unittest.TestCase):
    def test_the_shunt_is_the_preferred_technique(self):
        self.assertTrue(technique_is_preferred(SHUNT_TECHNIQUE))

    def test_every_named_alternative_is_not_preferred(self):
        for technique in ALTERNATIVE_TECHNIQUES:
            self.assertFalse(technique_is_preferred(technique))

    def test_the_shunt_heads_the_accepted_technique_list(self):
        self.assertEqual(ACCEPTED_TECHNIQUES[0], SHUNT_TECHNIQUE)

    def test_an_unknown_technique_is_refused(self):
        with self.assertRaises(ValueError):
            technique_is_preferred("oscilloscope-guess")


class EvidenceTests(unittest.TestCase):
    def test_a_shunt_owes_its_self_inductance(self):
        self.assertIn("shunt_inductance_h", required_evidence(SHUNT_TECHNIQUE))

    def test_an_alternative_owes_a_justification_and_a_bandwidth(self):
        owed = required_evidence("current-transformer")
        self.assertIn("justification", owed)
        self.assertIn("pickup_bandwidth_hz", owed)

    def test_an_alternative_is_not_asked_for_shunt_self_inductance(self):
        self.assertNotIn("shunt_inductance_h", required_evidence("rogowski-coil"))

    def test_missing_evidence_names_the_absent_inputs(self):
        case = _shunt()
        del case["shunt_inductance_h"]
        self.assertEqual(
            missing_evidence(SHUNT_TECHNIQUE, case), ("shunt_inductance_h",)
        )

    def test_missing_evidence_refuses_a_case_that_is_not_a_mapping(self):
        with self.assertRaises(ValueError):
            missing_evidence(SHUNT_TECHNIQUE, "shunt")


class ElectricalTermTests(unittest.TestCase):
    def test_the_cell_reactance_follows_the_capacitive_law(self):
        expected = 1.0 / (2.0 * math.pi * 1000.0 * CELL_CAPACITANCE_F)
        self.assertAlmostEqual(
            cell_reactance_ohm(CELL_CAPACITANCE_F, 1000.0), expected, places=12
        )

    def test_a_zero_capacitance_is_refused(self):
        with self.assertRaises(ValueError):
            cell_reactance_ohm(0.0, 1000.0)

    def test_a_boolean_capacitance_is_refused(self):
        with self.assertRaises(ValueError):
            cell_reactance_ohm(True, 1000.0)

    def test_the_burden_fraction_is_the_sense_share_of_the_loop(self):
        self.assertAlmostEqual(sense_burden_fraction(2.0, 400.0), 0.005, places=12)

    def test_a_negative_sense_resistance_is_refused(self):
        with self.assertRaises(ValueError):
            sense_burden_fraction(-1.0, 400.0)

    def test_the_acquisition_corner_is_set_by_the_sense_node_load(self):
        expected = 1.0 / (2.0 * math.pi * 1.0 * 1.0e-10)
        self.assertAlmostEqual(
            acquisition_corner_frequency_hz(1.0, 1.0e-10), expected, places=3
        )

    def test_a_zero_input_capacitance_is_refused(self):
        with self.assertRaises(ValueError):
            acquisition_corner_frequency_hz(1.0, 0.0)

    def test_the_shunt_inductive_corner_is_resistance_over_inductance(self):
        expected = 1.0 / (2.0 * math.pi * 1.0e-9)
        self.assertAlmostEqual(
            shunt_inductive_corner_hz(1.0, 1.0e-9), expected, places=3
        )

    def test_a_shunt_with_no_measurable_inductance_has_an_unbounded_corner(self):
        self.assertEqual(shunt_inductive_corner_hz(1.0, 0.0), math.inf)

    def test_a_negative_shunt_inductance_is_refused(self):
        with self.assertRaises(ValueError):
            shunt_inductive_corner_hz(1.0, -1.0e-9)

    def test_one_exact_decade_of_corner_headroom_reads_as_one(self):
        self.assertAlmostEqual(corner_decades_above(10000.0, 1000.0), 1.0, places=9)

    def test_an_unbounded_corner_gives_unbounded_headroom(self):
        self.assertEqual(corner_decades_above(math.inf, 1000.0), math.inf)

    def test_the_signal_voltage_is_the_current_through_the_sense_element(self):
        self.assertAlmostEqual(signal_voltage_v(1.0e-3, 2.0), 2.0e-3, places=12)

    def test_a_hundredfold_signal_over_noise_is_forty_decibels(self):
        self.assertAlmostEqual(signal_to_noise_db(1.0e-3, 1.0e-5), 40.0, places=9)

    def test_a_zero_noise_floor_is_refused(self):
        with self.assertRaises(ValueError):
            signal_to_noise_db(1.0e-3, 0.0)

    def test_a_written_justification_counts_and_whitespace_does_not(self):
        self.assertTrue(justification_recorded("bonded return leg"))
        self.assertFalse(justification_recorded("   "))

    def test_a_justification_that_is_not_text_is_refused(self):
        with self.assertRaises(ValueError):
            justification_recorded(7)


class AssessmentTests(unittest.TestCase):
    def test_a_well_sized_shunt_path_is_accepted(self):
        result = assess_signal_acquisition(_shunt())
        self.assertTrue(result["accepted"])
        self.assertEqual(result["verdict"], ACQUISITION_ACCEPTED)
        self.assertEqual(result["findings"], [])
        self.assertTrue(result["preferred_technique"])

    def test_a_heavy_sense_element_raises_a_burden_finding(self):
        result = assess_signal_acquisition(_shunt(sense_resistance_ohm=20.0))
        self.assertFalse(result["accepted"])
        self.assertEqual(result["verdict"], ACQUISITION_NOT_ACCEPTED)
        self.assertTrue(_finding_matching(result, "loop impedance"))
        self.assertGreater(
            result["detail"]["sense_burden_fraction"], MAX_SHUNT_BURDEN_FRACTION
        )

    def test_a_corner_exactly_one_decade_up_is_not_a_finding(self):
        case = _shunt(
            test_frequency_hz=1.0e6,
            cell_capacitance_f=4.7e-9,
            sense_resistance_ohm=0.5,
            input_capacitance_f=1.0 / (2.0 * math.pi * 1.0e7 * 0.5),
            shunt_inductance_h=1.0e-12,
        )
        result = assess_signal_acquisition(case)
        self.assertAlmostEqual(
            result["detail"]["acquisition_corner_decades_above_test"],
            MIN_CORNER_DECADES_ABOVE_TEST,
            places=9,
        )
        self.assertEqual(_finding_matching(result, "acquisition corner"), [])
        self.assertTrue(result["accepted"])

    def test_a_loaded_sense_node_raises_an_acquisition_corner_finding(self):
        result = assess_signal_acquisition(_shunt(input_capacitance_f=1.0e-4))
        self.assertTrue(_finding_matching(result, "acquisition corner"))
        self.assertFalse(result["accepted"])

    def test_a_self_inductive_shunt_raises_its_own_finding(self):
        result = assess_signal_acquisition(_shunt(shunt_inductance_h=1.0e-3))
        self.assertTrue(_finding_matching(result, "self-inductance"))
        self.assertFalse(result["accepted"])

    def test_a_signal_inside_the_noise_raises_a_margin_finding(self):
        result = assess_signal_acquisition(_shunt(signal_current_a=1.0e-6))
        self.assertTrue(_finding_matching(result, "noise floor"))
        self.assertLess(result["detail"]["signal_to_noise_db"], MIN_SIGNAL_TO_NOISE_DB)

    def test_a_justified_alternative_with_enough_bandwidth_is_accepted(self):
        result = assess_signal_acquisition(_transformer())
        self.assertTrue(result["accepted"])
        self.assertFalse(result["preferred_technique"])
        self.assertTrue(result["detail"]["justification_recorded"])

    def test_an_unjustified_alternative_is_not_accepted(self):
        result = assess_signal_acquisition(_transformer(justification="   "))
        self.assertFalse(result["accepted"])
        self.assertTrue(_finding_matching(result, "recorded justification"))

    def test_a_narrow_pickup_bandwidth_is_a_finding(self):
        result = assess_signal_acquisition(_transformer(pickup_bandwidth_hz=5000.0))
        self.assertTrue(_finding_matching(result, "pickup bandwidth"))
        self.assertFalse(result["accepted"])

    def test_a_shunt_case_without_its_inductance_stops_the_assessment(self):
        case = _shunt()
        del case["shunt_inductance_h"]
        with self.assertRaises(ValueError):
            assess_signal_acquisition(case)

    def test_an_alternative_without_a_justification_key_stops_the_assessment(self):
        case = _transformer()
        del case["justification"]
        with self.assertRaises(ValueError):
            assess_signal_acquisition(case)

    def test_a_case_that_is_not_a_mapping_is_refused(self):
        with self.assertRaises(ValueError):
            assess_signal_acquisition("shunt")

    def test_the_verdict_string_tracks_the_accepted_flag(self):
        good = assess_signal_acquisition(_shunt())
        bad = assess_signal_acquisition(_shunt(sense_resistance_ohm=20.0))
        self.assertEqual(good["verdict"], ACQUISITION_ACCEPTED)
        self.assertEqual(bad["verdict"], ACQUISITION_NOT_ACCEPTED)


if __name__ == "__main__":
    unittest.main()
