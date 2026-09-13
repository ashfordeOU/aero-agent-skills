#!/usr/bin/env python3
"""Contract test for the string capacitance method leaf (offline)."""

import copy
import math
import unittest

from e2008_assembly_capacitance_measurement_process_logic import (
    ACCEPTED_METHODS,
    FREQUENCY_DOMAIN,
    FREQUENCY_DOMAIN_METHODS,
    MAX_DISSIPATION_FACTOR,
    MAX_STRAY_FRACTION,
    METHOD_ACCEPTED,
    METHOD_NOT_ACCEPTED,
    MIN_RECORD_WINDOW_TIME_CONSTANTS,
    MIN_SAMPLES_PER_TIME_CONSTANT,
    TIME_DOMAIN,
    TIME_DOMAIN_METHODS,
    assess_capacitance_method,
    capacitive_reactance_ohm,
    combined_uncertainty_fraction,
    discharge_time_constant_s,
    dissipation_factor,
    method_domain,
    missing_evidence,
    nominate_single_method,
    reactance_within_instrument_band,
    record_window_time_constants,
    required_evidence,
    samples_per_time_constant,
    stray_capacitance_fraction,
)

STRING_CAPACITANCE_F = 2.2e-7

BRIDGE_CASE = {
    "nominated_method": "lcr-bridge",
    "expected_capacitance_f": STRING_CAPACITANCE_F,
    "test_frequency_hz": 1000.0,
    "leakage_conductance_s": 1.0e-8,
    "instrument_reactance_band_ohm": {"minimum_ohm": 1.0, "maximum_ohm": 1.0e7},
    "stray_capacitance_f": 5.0e-9,
    "instrument_accuracy_fraction": 0.01,
    "fixture_repeatability_fraction": 0.005,
    "required_uncertainty_fraction": 0.05,
}

DISCHARGE_CASE = {
    "nominated_method": "resistive-discharge",
    "expected_capacitance_f": STRING_CAPACITANCE_F,
    "discharge_resistance_ohm": 1.0e5,
    "recorder_sample_rate_hz": 1.0e6,
    "record_window_s": 1.0,
    "stray_capacitance_f": 5.0e-9,
    "instrument_accuracy_fraction": 0.01,
    "fixture_repeatability_fraction": 0.005,
    "required_uncertainty_fraction": 0.05,
}


def _bridge(**overrides):
    case = copy.deepcopy(BRIDGE_CASE)
    case.update(overrides)
    return case


def _discharge(**overrides):
    case = copy.deepcopy(DISCHARGE_CASE)
    case.update(overrides)
    return case


class MethodDomainTests(unittest.TestCase):
    def test_a_bridge_is_a_frequency_domain_method(self):
        self.assertEqual(method_domain("lcr-bridge"), FREQUENCY_DOMAIN)
        self.assertEqual(method_domain("impedance-analyser"), FREQUENCY_DOMAIN)

    def test_a_discharge_is_a_time_domain_method(self):
        self.assertEqual(method_domain("resistive-discharge"), TIME_DOMAIN)
        self.assertEqual(method_domain("constant-current-charge"), TIME_DOMAIN)

    def test_every_accepted_method_sits_in_exactly_one_domain(self):
        self.assertEqual(
            set(FREQUENCY_DOMAIN_METHODS) & set(TIME_DOMAIN_METHODS), set()
        )
        for method in ACCEPTED_METHODS:
            self.assertIn(method_domain(method), (FREQUENCY_DOMAIN, TIME_DOMAIN))

    def test_an_unaccepted_method_has_no_domain(self):
        with self.assertRaises(ValueError):
            method_domain("multimeter-continuity-check")

    def test_the_two_domains_require_different_evidence(self):
        frequency_side = set(required_evidence("lcr-bridge"))
        time_side = set(required_evidence("resistive-discharge"))
        self.assertIn("test_frequency_hz", frequency_side)
        self.assertNotIn("test_frequency_hz", time_side)
        self.assertIn("recorder_sample_rate_hz", time_side)
        self.assertNotIn("recorder_sample_rate_hz", frequency_side)


class SingleMethodTests(unittest.TestCase):
    def test_one_named_method_is_the_nomination(self):
        self.assertEqual(nominate_single_method("lcr-bridge"), "lcr-bridge")

    def test_a_single_element_sequence_is_also_accepted(self):
        self.assertEqual(
            nominate_single_method(["constant-current-charge"]),
            "constant-current-charge",
        )

    def test_two_methods_left_open_are_refused(self):
        with self.assertRaises(ValueError):
            nominate_single_method(["lcr-bridge", "resistive-discharge"])

    def test_an_empty_nomination_is_refused(self):
        with self.assertRaises(ValueError):
            nominate_single_method([])

    def test_a_nomination_that_is_not_a_name_is_refused(self):
        with self.assertRaises(ValueError):
            nominate_single_method({"method": "lcr-bridge"})

    def test_a_single_but_unaccepted_method_is_refused(self):
        with self.assertRaises(ValueError):
            nominate_single_method(["ohmmeter-reading"])


class FrequencyDomainQuantityTests(unittest.TestCase):
    def test_reactance_follows_the_article_and_the_frequency(self):
        value = capacitive_reactance_ohm(STRING_CAPACITANCE_F, 1000.0)
        self.assertAlmostEqual(
            value, 1.0 / (2.0 * math.pi * 1000.0 * STRING_CAPACITANCE_F), places=9
        )

    def test_a_higher_frequency_lowers_the_reactance(self):
        low = capacitive_reactance_ohm(STRING_CAPACITANCE_F, 100.0)
        high = capacitive_reactance_ohm(STRING_CAPACITANCE_F, 10000.0)
        self.assertGreater(low, high)

    def test_a_zero_frequency_cannot_form_a_reactance(self):
        with self.assertRaises(ValueError):
            capacitive_reactance_ohm(STRING_CAPACITANCE_F, 0.0)

    def test_a_lossless_article_has_no_dissipation(self):
        self.assertAlmostEqual(
            dissipation_factor(STRING_CAPACITANCE_F, 1000.0, 0.0), 0.0, places=12
        )

    def test_leakage_raises_the_dissipation_factor(self):
        leaky = dissipation_factor(STRING_CAPACITANCE_F, 1000.0, 1.0e-4)
        tight = dissipation_factor(STRING_CAPACITANCE_F, 1000.0, 1.0e-8)
        self.assertGreater(leaky, tight)

    def test_a_negative_leakage_conductance_is_refused(self):
        with self.assertRaises(ValueError):
            dissipation_factor(STRING_CAPACITANCE_F, 1000.0, -1.0e-8)

    def test_a_reactance_on_the_instrument_ceiling_is_still_in_band(self):
        band = {"minimum_ohm": 1.0, "maximum_ohm": 1.0e7}
        self.assertTrue(reactance_within_instrument_band(1.0e7, band))
        self.assertTrue(reactance_within_instrument_band(1.0, band))

    def test_a_reactance_beyond_the_instrument_ceiling_is_out_of_band(self):
        band = {"minimum_ohm": 1.0, "maximum_ohm": 1.0e4}
        self.assertFalse(reactance_within_instrument_band(1.0e6, band))

    def test_an_inverted_instrument_band_is_refused(self):
        with self.assertRaises(ValueError):
            reactance_within_instrument_band(
                100.0, {"minimum_ohm": 1.0e7, "maximum_ohm": 1.0}
            )

    def test_a_band_that_is_not_a_mapping_is_refused(self):
        with self.assertRaises(ValueError):
            reactance_within_instrument_band(100.0, (1.0, 1.0e7))


class TimeDomainQuantityTests(unittest.TestCase):
    def test_the_decay_constant_is_the_resistor_times_the_article(self):
        self.assertAlmostEqual(
            discharge_time_constant_s(STRING_CAPACITANCE_F, 1.0e5),
            STRING_CAPACITANCE_F * 1.0e5,
            places=12,
        )

    def test_a_zero_discharge_resistance_is_refused(self):
        with self.assertRaises(ValueError):
            discharge_time_constant_s(STRING_CAPACITANCE_F, 0.0)

    def test_samples_inside_a_decay_constant_follow_the_sample_rate(self):
        tau = discharge_time_constant_s(STRING_CAPACITANCE_F, 1.0e5)
        self.assertAlmostEqual(
            samples_per_time_constant(tau, 1.0e6), tau * 1.0e6, places=6
        )

    def test_a_window_of_one_decay_constant_is_reported_as_one(self):
        self.assertAlmostEqual(
            record_window_time_constants(0.022, 0.022), 1.0, places=9
        )

    def test_a_non_numeric_sample_rate_is_refused(self):
        with self.assertRaises(ValueError):
            samples_per_time_constant(0.022, "1 MHz")


class UncertaintyTests(unittest.TestCase):
    def test_terms_combine_as_a_root_sum_of_squares(self):
        self.assertAlmostEqual(
            combined_uncertainty_fraction((0.03, 0.04)), 0.05, places=9
        )

    def test_a_single_term_is_carried_through_unchanged(self):
        self.assertAlmostEqual(
            combined_uncertainty_fraction((0.02,)), 0.02, places=9
        )

    def test_an_empty_term_list_is_refused(self):
        with self.assertRaises(ValueError):
            combined_uncertainty_fraction(())

    def test_a_term_above_unity_is_refused(self):
        with self.assertRaises(ValueError):
            combined_uncertainty_fraction((1.4, 0.01))

    def test_the_stray_share_is_the_fixture_over_the_article(self):
        self.assertAlmostEqual(
            stray_capacitance_fraction(5.0e-9, STRING_CAPACITANCE_F),
            5.0e-9 / STRING_CAPACITANCE_F,
            places=12,
        )

    def test_a_zero_article_capacitance_cannot_carry_a_stray_share(self):
        with self.assertRaises(ValueError):
            stray_capacitance_fraction(5.0e-9, 0.0)


class EvidenceTests(unittest.TestCase):
    def test_a_complete_bridge_case_is_missing_nothing(self):
        self.assertEqual(missing_evidence("lcr-bridge", BRIDGE_CASE), ())

    def test_a_bridge_case_without_a_frequency_is_incomplete(self):
        case = _bridge()
        del case["test_frequency_hz"]
        self.assertEqual(
            missing_evidence("lcr-bridge", case), ("test_frequency_hz",)
        )

    def test_time_domain_evidence_does_not_satisfy_a_bridge(self):
        self.assertTrue(missing_evidence("lcr-bridge", DISCHARGE_CASE))

    def test_missing_evidence_stops_the_assessment(self):
        case = _discharge()
        del case["recorder_sample_rate_hz"]
        with self.assertRaises(ValueError):
            assess_capacitance_method(case)


class AssessmentTests(unittest.TestCase):
    def test_a_sound_bridge_measurement_is_accepted(self):
        result = assess_capacitance_method(BRIDGE_CASE)
        self.assertEqual(result["verdict"], METHOD_ACCEPTED)
        self.assertTrue(result["accepted"])
        self.assertEqual(result["findings"], [])
        self.assertEqual(result["domain"], FREQUENCY_DOMAIN)

    def test_a_sound_discharge_measurement_is_accepted(self):
        result = assess_capacitance_method(DISCHARGE_CASE)
        self.assertEqual(result["verdict"], METHOD_ACCEPTED)
        self.assertEqual(result["domain"], TIME_DOMAIN)
        self.assertGreater(
            result["domain_detail"]["samples_per_time_constant"],
            MIN_SAMPLES_PER_TIME_CONSTANT,
        )

    def test_a_reactance_outside_the_instrument_band_is_a_finding(self):
        result = assess_capacitance_method(
            _bridge(
                instrument_reactance_band_ohm={
                    "minimum_ohm": 1.0,
                    "maximum_ohm": 100.0,
                }
            )
        )
        self.assertEqual(result["verdict"], METHOD_NOT_ACCEPTED)
        self.assertTrue(any("instrument band" in f for f in result["findings"]))

    def test_a_lossy_article_is_a_finding_against_the_bridge(self):
        result = assess_capacitance_method(_bridge(leakage_conductance_s=1.0e-3))
        self.assertEqual(result["verdict"], METHOD_NOT_ACCEPTED)
        self.assertTrue(any("dissipation factor" in f for f in result["findings"]))
        self.assertGreater(
            result["domain_detail"]["dissipation_factor"], MAX_DISSIPATION_FACTOR
        )

    def test_a_slow_recorder_cannot_reconstruct_the_decay(self):
        result = assess_capacitance_method(_discharge(recorder_sample_rate_hz=100.0))
        self.assertEqual(result["verdict"], METHOD_NOT_ACCEPTED)
        self.assertTrue(any("decay constant" in f for f in result["findings"]))

    def test_a_short_record_window_truncates_the_decay(self):
        result = assess_capacitance_method(_discharge(record_window_s=0.05))
        self.assertEqual(result["verdict"], METHOD_NOT_ACCEPTED)
        self.assertTrue(any("record window" in f for f in result["findings"]))
        self.assertLess(
            result["domain_detail"]["record_window_time_constants"],
            MIN_RECORD_WINDOW_TIME_CONSTANTS,
        )

    def test_a_window_landing_exactly_on_the_minimum_is_accepted(self):
        tau = STRING_CAPACITANCE_F * 1.0e5
        result = assess_capacitance_method(
            _discharge(record_window_s=MIN_RECORD_WINDOW_TIME_CONSTANTS * tau)
        )
        self.assertAlmostEqual(
            result["domain_detail"]["record_window_time_constants"],
            MIN_RECORD_WINDOW_TIME_CONSTANTS,
            places=9,
        )
        self.assertEqual(result["verdict"], METHOD_ACCEPTED)

    def test_a_dominant_fixture_stray_is_a_finding_in_either_domain(self):
        bridge = assess_capacitance_method(_bridge(stray_capacitance_f=4.0e-8))
        discharge = assess_capacitance_method(_discharge(stray_capacitance_f=4.0e-8))
        for result in (bridge, discharge):
            self.assertEqual(result["verdict"], METHOD_NOT_ACCEPTED)
            self.assertTrue(any("stray and lead" in f for f in result["findings"]))
            self.assertGreater(
                result["stray_capacitance_fraction"], MAX_STRAY_FRACTION
            )

    def test_a_tight_uncertainty_requirement_is_not_met_by_this_fixture(self):
        result = assess_capacitance_method(_bridge(required_uncertainty_fraction=0.01))
        self.assertEqual(result["verdict"], METHOD_NOT_ACCEPTED)
        self.assertFalse(result["uncertainty_met"])
        self.assertTrue(any("combined uncertainty" in f for f in result["findings"]))

    def test_the_uncertainty_is_the_root_sum_of_the_three_terms(self):
        result = assess_capacitance_method(BRIDGE_CASE)
        expected = math.sqrt(
            0.01 ** 2 + (5.0e-9 / STRING_CAPACITANCE_F) ** 2 + 0.005 ** 2
        )
        self.assertAlmostEqual(
            result["combined_uncertainty_fraction"], expected, places=12
        )

    def test_two_open_methods_stop_the_assessment(self):
        with self.assertRaises(ValueError):
            assess_capacitance_method(
                _bridge(nominated_method=["lcr-bridge", "impedance-analyser"])
            )

    def test_a_case_that_is_not_a_mapping_is_refused(self):
        with self.assertRaises(ValueError):
            assess_capacitance_method("lcr-bridge")


if __name__ == "__main__":
    unittest.main()
