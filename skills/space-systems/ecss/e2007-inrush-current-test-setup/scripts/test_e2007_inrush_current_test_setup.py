#!/usr/bin/env python3
"""Gate 3 contract test for e2007-inrush-current-test-setup.

stdlib unittest, offline, deterministic. Run:
    python3 test_e2007_inrush_current_test_setup.py
"""

import math
import unittest

from e2007_inrush_current_test_setup_logic import (
    CONFORMING,
    DECLARED_DEVIATION,
    NONCONFORMING,
    RISE_BANDWIDTH_PRODUCT,
    VERDICT_CONFORMING,
    VERDICT_NONCONFORMING,
    VERDICT_WITH_DEVIATIONS,
    apply_setup_deltas,
    assess_inrush_setup,
    band_margin,
    categorize_parameter,
    chain_bandwidth_hz,
    chain_rise_time_s,
    governing_parameter,
    required_chain_bandwidth_hz,
    required_record_length_s,
    required_sample_rate_hz,
    validate_band,
    validate_bench,
)

SURGE_RISE_S = 1.0e-5
SETTLING_TAU_S = 1.0e-3


def baseline():
    return {
        "bond_resistance_ohm": (0.0, 0.01),
        "lead_height_m": (0.03, 0.07),
        "lead_length_m": (0.5, 2.0),
        "probe_to_connector_m": (0.02, 0.10),
        "source_impedance_ohm": (0.0, 0.5),
    }


def good_bench(**over):
    record = {
        "probe_type": "current-probe",
        "bus_voltage_v": 28.0,
        "lead_length_m": 1.0,
        "lead_height_m": 0.05,
        "probe_to_connector_m": 0.05,
        "source_impedance_ohm": 0.05,
        "bond_resistance_ohm": 0.0025,
        "probe_bandwidth_hz": 2.0e6,
        "recorder_bandwidth_hz": 100.0e6,
        "sample_rate_hz": 100.0e6,
        "record_length_s": 0.05,
        "declared_deviations": (),
    }
    record.update(over)
    return record


def assess(**over):
    return assess_inrush_setup(
        good_bench(**over),
        baseline(),
        None,
        SURGE_RISE_S,
        SETTLING_TAU_S,
    )


class TestBenchValidation(unittest.TestCase):
    def test_good_bench_normalizes(self):
        bench = validate_bench(good_bench())
        self.assertEqual(bench["probe_type"], "current-probe")
        self.assertAlmostEqual(bench["lead_length_m"], 1.0, places=9)

    def test_probe_type_token_is_case_normalized(self):
        bench = validate_bench(good_bench(probe_type="Current-Shunt"))
        self.assertEqual(bench["probe_type"], "current-shunt")

    def test_unknown_probe_type_is_rejected(self):
        with self.assertRaises(ValueError):
            validate_bench(good_bench(probe_type="rogowski-guess"))

    def test_zero_lead_length_is_rejected(self):
        with self.assertRaises(ValueError):
            validate_bench(good_bench(lead_length_m=0.0))

    def test_negative_bond_resistance_is_rejected(self):
        with self.assertRaises(ValueError):
            validate_bench(good_bench(bond_resistance_ohm=-0.001))

    def test_zero_bond_resistance_is_accepted(self):
        bench = validate_bench(good_bench(bond_resistance_ohm=0.0))
        self.assertAlmostEqual(bench["bond_resistance_ohm"], 0.0, places=12)

    def test_missing_field_is_rejected(self):
        record = good_bench()
        del record["record_length_s"]
        with self.assertRaises(ValueError):
            validate_bench(record)

    def test_boolean_sample_rate_is_rejected(self):
        with self.assertRaises(ValueError):
            validate_bench(good_bench(sample_rate_hz=True))

    def test_declared_deviations_as_a_bare_string_is_rejected(self):
        with self.assertRaises(ValueError):
            validate_bench(good_bench(declared_deviations="lead_length_m"))

    def test_declared_deviation_on_an_ungraded_parameter_is_rejected(self):
        with self.assertRaises(ValueError):
            validate_bench(good_bench(declared_deviations=("bus_voltage_v",)))


class TestBandsAndDeltas(unittest.TestCase):
    def test_bands_pass_through_when_no_delta_is_declared(self):
        bands = apply_setup_deltas(baseline(), None)
        self.assertAlmostEqual(bands["lead_length_m"][1], 2.0, places=9)

    def test_a_delta_moves_the_band_edge_it_names(self):
        bands = apply_setup_deltas(
            baseline(), {"lead_length_m": {"maximum_delta": 1.0}}
        )
        self.assertAlmostEqual(bands["lead_length_m"][1], 3.0, places=9)
        self.assertAlmostEqual(bands["lead_length_m"][0], 0.5, places=9)

    def test_unknown_delta_parameter_is_refused(self):
        with self.assertRaises(ValueError):
            apply_setup_deltas(baseline(), {"cable_colour": {"maximum_delta": 1.0}})

    def test_unknown_delta_key_is_refused(self):
        with self.assertRaises(ValueError):
            apply_setup_deltas(baseline(), {"lead_length_m": {"scale": 2.0}})

    def test_a_delta_that_collapses_a_band_is_refused(self):
        with self.assertRaises(ValueError):
            apply_setup_deltas(
                baseline(), {"lead_height_m": {"minimum_delta": 0.05}}
            )

    def test_inverted_baseline_band_is_refused(self):
        bands = baseline()
        bands["lead_length_m"] = (2.0, 0.5)
        with self.assertRaises(ValueError):
            apply_setup_deltas(bands, None)

    def test_unknown_baseline_parameter_is_refused(self):
        bands = baseline()
        bands["room_humidity_pct"] = (30.0, 60.0)
        with self.assertRaises(ValueError):
            apply_setup_deltas(bands, None)

    def test_band_must_be_a_pair(self):
        with self.assertRaises(ValueError):
            validate_band((0.1, 0.2, 0.3), "lead_length_m")


class TestParameterGrading(unittest.TestCase):
    def test_value_inside_the_band_conforms(self):
        self.assertEqual(categorize_parameter(1.0, (0.5, 2.0)), CONFORMING)

    def test_value_landing_on_the_upper_edge_conforms(self):
        self.assertEqual(categorize_parameter(2.0, (0.5, 2.0)), CONFORMING)

    def test_undeclared_excursion_is_nonconforming(self):
        self.assertEqual(categorize_parameter(2.4, (0.5, 2.0)), NONCONFORMING)

    def test_declared_excursion_is_a_declared_deviation(self):
        self.assertEqual(
            categorize_parameter(2.4, (0.5, 2.0), True), DECLARED_DEVIATION
        )

    def test_band_margin_at_the_centre_is_one_half(self):
        self.assertAlmostEqual(band_margin(1.25, (0.5, 2.0)), 0.5, places=9)

    def test_band_margin_outside_the_band_is_negative(self):
        self.assertLess(band_margin(2.9, (0.5, 2.0)), 0.0)

    def test_governing_parameter_is_the_tightest_one(self):
        self.assertEqual(
            governing_parameter(validate_bench(good_bench()), baseline()),
            "source_impedance_ohm",
        )


class TestMeasurementChain(unittest.TestCase):
    def test_equal_bandwidths_add_in_quadrature(self):
        single = RISE_BANDWIDTH_PRODUCT / 1.0e6
        rise = chain_rise_time_s(1.0e6, 1.0e6)
        self.assertAlmostEqual(rise / single, math.sqrt(2.0), places=9)

    def test_a_much_faster_recorder_leaves_the_probe_governing(self):
        probe_rise = RISE_BANDWIDTH_PRODUCT / 1.0e6
        rise = chain_rise_time_s(1.0e6, 1.0e9)
        self.assertAlmostEqual(rise / probe_rise, 1.0, places=6)

    def test_chain_bandwidth_sits_below_the_slower_instrument(self):
        self.assertLess(chain_bandwidth_hz(2.0e6, 100.0e6), 2.0e6)

    def test_zero_probe_bandwidth_is_rejected(self):
        with self.assertRaises(ValueError):
            chain_rise_time_s(0.0, 100.0e6)

    def test_required_chain_bandwidth_scales_with_the_speed_factor(self):
        one = required_chain_bandwidth_hz(SURGE_RISE_S, 1.0)
        three = required_chain_bandwidth_hz(SURGE_RISE_S, 3.0)
        self.assertAlmostEqual(three / one, 3.0, places=9)

    def test_speed_factor_below_unity_is_rejected(self):
        with self.assertRaises(ValueError):
            required_chain_bandwidth_hz(SURGE_RISE_S, 0.5)

    def test_one_sample_per_rise_time_gives_the_reciprocal_rate(self):
        self.assertAlmostEqual(
            required_sample_rate_hz(RISE_BANDWIDTH_PRODUCT, 1.0), 1.0, places=9
        )

    def test_required_sample_rate_is_linear_in_the_sample_count(self):
        few = required_sample_rate_hz(2.0e6, 2.0)
        many = required_sample_rate_hz(2.0e6, 8.0)
        self.assertAlmostEqual(many / few, 4.0, places=9)

    def test_required_record_length_is_the_settling_multiple(self):
        self.assertAlmostEqual(
            required_record_length_s(2.0e-3, 5.0), 10.0e-3, places=9
        )

    def test_non_positive_settling_constant_is_rejected(self):
        with self.assertRaises(ValueError):
            required_record_length_s(0.0)


class TestSetupAssessment(unittest.TestCase):
    def test_good_bench_is_setup_conforming(self):
        report = assess()
        self.assertEqual(report["findings"], [])
        self.assertEqual(report["verdict"], VERDICT_CONFORMING)
        self.assertTrue(report["bandwidth_is_adequate"])
        self.assertTrue(report["sample_rate_is_adequate"])
        self.assertTrue(report["record_length_is_adequate"])

    def test_report_names_the_governing_parameter(self):
        self.assertEqual(assess()["governing_parameter"], "source_impedance_ohm")

    def test_undeclared_long_lead_is_a_finding(self):
        report = assess(lead_length_m=3.5)
        self.assertEqual(report["categories"]["lead_length_m"], NONCONFORMING)
        self.assertEqual(report["verdict"], VERDICT_NONCONFORMING)
        self.assertEqual(len(report["findings"]), 1)

    def test_the_same_lead_declared_becomes_a_limitation(self):
        report = assess(
            lead_length_m=3.5, declared_deviations=("lead_length_m",)
        )
        self.assertEqual(report["categories"]["lead_length_m"], DECLARED_DEVIATION)
        self.assertEqual(report["findings"], [])
        self.assertEqual(report["verdict"], VERDICT_WITH_DEVIATIONS)
        self.assertEqual(len(report["limitations"]), 1)

    def test_a_delta_widening_the_band_rescues_the_long_lead(self):
        report = assess_inrush_setup(
            good_bench(lead_length_m=3.5),
            baseline(),
            {"lead_length_m": {"maximum_delta": 2.0}},
            SURGE_RISE_S,
            SETTLING_TAU_S,
        )
        self.assertEqual(report["categories"]["lead_length_m"], CONFORMING)
        self.assertEqual(report["verdict"], VERDICT_CONFORMING)

    def test_a_slow_probe_is_reported_as_a_bandwidth_finding(self):
        report = assess(probe_bandwidth_hz=1.0e4)
        self.assertFalse(report["bandwidth_is_adequate"])
        self.assertEqual(report["verdict"], VERDICT_NONCONFORMING)

    def test_a_sample_rate_below_the_derived_rate_is_a_finding(self):
        report = assess(sample_rate_hz=1.0e6)
        self.assertFalse(report["sample_rate_is_adequate"])
        self.assertGreater(report["required_sample_rate_hz"], 1.0e6)

    def test_a_record_ending_before_settling_is_a_finding(self):
        report = assess(record_length_s=1.0e-4)
        self.assertFalse(report["record_length_is_adequate"])
        self.assertAlmostEqual(
            report["required_record_length_s"], 5.0e-3, places=9
        )

    def test_a_shunt_in_a_zero_impedance_source_is_a_limitation(self):
        report = assess(probe_type="current-shunt", source_impedance_ohm=0.0)
        self.assertEqual(report["findings"], [])
        self.assertEqual(len(report["limitations"]), 1)

    def test_assessment_propagates_a_bench_error(self):
        with self.assertRaises(ValueError):
            assess(probe_bandwidth_hz=0.0)


if __name__ == "__main__":
    unittest.main()
