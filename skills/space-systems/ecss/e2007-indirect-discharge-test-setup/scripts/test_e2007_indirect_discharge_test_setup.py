#!/usr/bin/env python3
"""Gate 3 contract test for e2007-indirect-discharge-test-setup.

stdlib unittest, offline, deterministic. Run:
    python3 test_e2007_indirect_discharge_test_setup.py
"""

import math
import unittest

from e2007_indirect_discharge_test_setup_logic import (
    BLEED_MULTIPLE,
    CONFORMING,
    DECLARED_DEVIATION,
    NONCONFORMING,
    RESIDUAL_NOTICE_FRACTION,
    VERDICT_CONFORMING,
    VERDICT_NONCONFORMING,
    VERDICT_WITH_DEVIATIONS,
    apply_setup_deltas,
    assess_indirect_discharge_setup,
    band_margin,
    bleeder_time_constant_s,
    categorize_parameter,
    governing_parameter,
    required_bleed_time_s,
    required_plane_span_m,
    residual_plane_fraction,
    residual_plane_voltage_v,
    validate_band,
    validate_bench,
)

PLANE_CAPACITANCE_F = 100.0e-12
BLEEDER_OHM = 470.0e3
BLEEDER_COUNT = 2.0


def baseline():
    return {
        "bleeder_resistance_ohm": (100.0e3, 1.0e6),
        "bond_resistance_ohm": (0.0, 0.01),
        "cable_to_plane_separation_m": (0.05, 0.5),
        "coupling_plane_distance_m": (0.05, 0.2),
        "coupling_plane_overhang_m": (0.05, 0.3),
        "insulating_support_thickness_m": (0.005, 0.05),
    }


def good_bench(**over):
    record = {
        "plane_type": "horizontal-coupling-plane",
        "bleeder_resistance_ohm": BLEEDER_OHM,
        "bleeder_count": BLEEDER_COUNT,
        "bond_resistance_ohm": 0.0025,
        "cable_to_plane_separation_m": 0.1,
        "charge_voltage_v": 4000.0,
        "coupling_plane_capacitance_f": PLANE_CAPACITANCE_F,
        "coupling_plane_distance_m": 0.1,
        "coupling_plane_overhang_m": 0.1,
        "coupling_plane_span_m": 1.0,
        "discharge_interval_s": 1.0,
        "insulating_support_thickness_m": 0.02,
        "unit_span_m": 0.4,
        "declared_deviations": (),
    }
    record.update(over)
    return record


def assess(**over):
    return assess_indirect_discharge_setup(good_bench(**over), baseline(), None)


def nominal_tau():
    return bleeder_time_constant_s(BLEEDER_OHM, BLEEDER_COUNT, PLANE_CAPACITANCE_F)


class TestBenchValidation(unittest.TestCase):
    def test_good_bench_normalizes(self):
        bench = validate_bench(good_bench())
        self.assertEqual(bench["plane_type"], "horizontal-coupling-plane")
        self.assertAlmostEqual(bench["coupling_plane_distance_m"], 0.1, places=9)

    def test_plane_type_token_is_case_normalized(self):
        bench = validate_bench(good_bench(plane_type="Vertical-Coupling-Plane"))
        self.assertEqual(bench["plane_type"], "vertical-coupling-plane")

    def test_unknown_plane_type_is_rejected(self):
        with self.assertRaises(ValueError):
            validate_bench(good_bench(plane_type="diagonal-plane"))

    def test_zero_plane_span_is_rejected(self):
        with self.assertRaises(ValueError):
            validate_bench(good_bench(coupling_plane_span_m=0.0))

    def test_negative_bond_resistance_is_rejected(self):
        with self.assertRaises(ValueError):
            validate_bench(good_bench(bond_resistance_ohm=-0.001))

    def test_zero_bond_resistance_is_accepted(self):
        bench = validate_bench(good_bench(bond_resistance_ohm=0.0))
        self.assertAlmostEqual(bench["bond_resistance_ohm"], 0.0, places=12)

    def test_fractional_bleeder_count_is_rejected(self):
        with self.assertRaises(ValueError):
            validate_bench(good_bench(bleeder_count=1.5))

    def test_zero_bleeder_count_is_rejected(self):
        with self.assertRaises(ValueError):
            validate_bench(good_bench(bleeder_count=0.0))

    def test_missing_field_is_rejected(self):
        record = good_bench()
        del record["discharge_interval_s"]
        with self.assertRaises(ValueError):
            validate_bench(record)

    def test_boolean_interval_is_rejected(self):
        with self.assertRaises(ValueError):
            validate_bench(good_bench(discharge_interval_s=True))

    def test_declared_deviations_as_a_bare_string_is_rejected(self):
        with self.assertRaises(ValueError):
            validate_bench(good_bench(declared_deviations="bond_resistance_ohm"))

    def test_declared_deviation_on_an_ungraded_parameter_is_rejected(self):
        with self.assertRaises(ValueError):
            validate_bench(good_bench(declared_deviations=("charge_voltage_v",)))


class TestBandsAndDeltas(unittest.TestCase):
    def test_bands_pass_through_when_no_delta_is_declared(self):
        bands = apply_setup_deltas(baseline(), None)
        self.assertAlmostEqual(bands["coupling_plane_distance_m"][1], 0.2, places=9)

    def test_a_delta_moves_the_band_edge_it_names(self):
        bands = apply_setup_deltas(
            baseline(), {"coupling_plane_distance_m": {"maximum_delta": 0.1}}
        )
        self.assertAlmostEqual(bands["coupling_plane_distance_m"][1], 0.3, places=9)
        self.assertAlmostEqual(bands["coupling_plane_distance_m"][0], 0.05, places=9)

    def test_unknown_delta_parameter_is_refused(self):
        with self.assertRaises(ValueError):
            apply_setup_deltas(baseline(), {"plane_paint_colour": {"maximum_delta": 1.0}})

    def test_unknown_delta_key_is_refused(self):
        with self.assertRaises(ValueError):
            apply_setup_deltas(baseline(), {"coupling_plane_distance_m": {"scale": 2.0}})

    def test_a_delta_that_collapses_a_band_is_refused(self):
        with self.assertRaises(ValueError):
            apply_setup_deltas(
                baseline(), {"coupling_plane_distance_m": {"minimum_delta": 0.2}}
            )

    def test_inverted_baseline_band_is_refused(self):
        bands = baseline()
        bands["coupling_plane_distance_m"] = (0.2, 0.05)
        with self.assertRaises(ValueError):
            apply_setup_deltas(bands, None)

    def test_unknown_baseline_parameter_is_refused(self):
        bands = baseline()
        bands["room_humidity_pct"] = (30.0, 60.0)
        with self.assertRaises(ValueError):
            apply_setup_deltas(bands, None)

    def test_band_must_be_a_pair(self):
        with self.assertRaises(ValueError):
            validate_band((0.1, 0.2, 0.3), "coupling_plane_distance_m")


class TestParameterGrading(unittest.TestCase):
    def test_value_inside_the_band_conforms(self):
        self.assertEqual(categorize_parameter(0.1, (0.05, 0.2)), CONFORMING)

    def test_value_landing_on_the_upper_edge_conforms(self):
        self.assertEqual(categorize_parameter(0.2, (0.05, 0.2)), CONFORMING)

    def test_undeclared_excursion_is_nonconforming(self):
        self.assertEqual(categorize_parameter(0.35, (0.05, 0.2)), NONCONFORMING)

    def test_declared_excursion_is_a_declared_deviation(self):
        self.assertEqual(
            categorize_parameter(0.35, (0.05, 0.2), True), DECLARED_DEVIATION
        )

    def test_band_margin_at_the_centre_is_one_half(self):
        self.assertAlmostEqual(band_margin(0.125, (0.05, 0.2)), 0.5, places=9)

    def test_band_margin_outside_the_band_is_negative(self):
        self.assertLess(band_margin(0.4, (0.05, 0.2)), 0.0)

    def test_governing_parameter_is_the_tightest_one(self):
        self.assertEqual(
            governing_parameter(validate_bench(good_bench()), baseline()),
            "cable_to_plane_separation_m",
        )


class TestPlaneAndBleeder(unittest.TestCase):
    def test_required_span_adds_the_overhang_on_both_sides(self):
        self.assertAlmostEqual(required_plane_span_m(0.4, 0.1), 0.6, places=9)

    def test_zero_overhang_leaves_the_footprint(self):
        self.assertAlmostEqual(required_plane_span_m(0.4, 0.0), 0.4, places=9)

    def test_negative_overhang_is_rejected(self):
        with self.assertRaises(ValueError):
            required_plane_span_m(0.4, -0.01)

    def test_zero_unit_span_is_rejected(self):
        with self.assertRaises(ValueError):
            required_plane_span_m(0.0, 0.1)

    def test_bleeder_chain_is_the_series_resistance_times_the_capacitance(self):
        self.assertAlmostEqual(
            bleeder_time_constant_s(BLEEDER_OHM, BLEEDER_COUNT, PLANE_CAPACITANCE_F),
            BLEEDER_OHM * 2.0 * PLANE_CAPACITANCE_F,
            places=15,
        )

    def test_a_second_bleeder_doubles_the_time_constant(self):
        one = bleeder_time_constant_s(BLEEDER_OHM, 1.0, PLANE_CAPACITANCE_F)
        two = bleeder_time_constant_s(BLEEDER_OHM, 2.0, PLANE_CAPACITANCE_F)
        self.assertAlmostEqual(two / one, 2.0, places=9)

    def test_fractional_bleeder_count_is_rejected_in_the_derivation(self):
        with self.assertRaises(ValueError):
            bleeder_time_constant_s(BLEEDER_OHM, 2.5, PLANE_CAPACITANCE_F)

    def test_required_bleed_time_is_the_declared_multiple(self):
        self.assertAlmostEqual(
            required_bleed_time_s(2.0e-4, 5.0), 1.0e-3, places=12
        )

    def test_bleed_multiple_below_unity_is_rejected(self):
        with self.assertRaises(ValueError):
            required_bleed_time_s(2.0e-4, 0.5)

    def test_residual_fraction_at_one_time_constant_is_one_over_e(self):
        self.assertAlmostEqual(
            residual_plane_fraction(1.0e-3, 1.0e-3), 1.0 / math.e, places=12
        )

    def test_residual_fraction_at_zero_interval_is_unity(self):
        self.assertAlmostEqual(residual_plane_fraction(0.0, 1.0e-3), 1.0, places=12)

    def test_residual_fraction_at_the_bleed_rule_is_exp_minus_the_multiple(self):
        tau = nominal_tau()
        interval = required_bleed_time_s(tau)
        self.assertAlmostEqual(
            residual_plane_fraction(interval, tau),
            math.exp(-BLEED_MULTIPLE),
            places=12,
        )

    def test_residual_voltage_scales_with_the_charge_voltage(self):
        self.assertAlmostEqual(
            residual_plane_voltage_v(4000.0, 1.0e-3, 1.0e-3),
            4000.0 / math.e,
            places=9,
        )

    def test_negative_interval_is_rejected(self):
        with self.assertRaises(ValueError):
            residual_plane_fraction(-1.0, 1.0e-3)


class TestSetupAssessment(unittest.TestCase):
    def test_good_bench_is_setup_conforming(self):
        report = assess()
        self.assertEqual(report["findings"], [])
        self.assertEqual(report["limitations"], [])
        self.assertEqual(report["verdict"], VERDICT_CONFORMING)
        self.assertTrue(report["plane_span_is_adequate"])
        self.assertTrue(report["bleed_interval_is_adequate"])

    def test_report_names_the_governing_parameter(self):
        self.assertEqual(assess()["governing_parameter"], "cable_to_plane_separation_m")

    def test_report_carries_the_derived_span_and_bleed_numbers(self):
        report = assess()
        self.assertAlmostEqual(report["required_plane_span_m"], 0.6, places=9)
        self.assertAlmostEqual(
            report["bleeder_time_constant_s"], nominal_tau(), places=15
        )

    def test_an_undeclared_far_plane_is_a_finding(self):
        report = assess(coupling_plane_distance_m=0.4)
        self.assertEqual(
            report["categories"]["coupling_plane_distance_m"], NONCONFORMING
        )
        self.assertEqual(report["verdict"], VERDICT_NONCONFORMING)
        self.assertEqual(len(report["findings"]), 1)

    def test_the_same_plane_declared_becomes_a_limitation(self):
        report = assess(
            coupling_plane_distance_m=0.4,
            declared_deviations=("coupling_plane_distance_m",),
        )
        self.assertEqual(
            report["categories"]["coupling_plane_distance_m"], DECLARED_DEVIATION
        )
        self.assertEqual(report["findings"], [])
        self.assertEqual(report["verdict"], VERDICT_WITH_DEVIATIONS)
        self.assertEqual(len(report["limitations"]), 1)

    def test_a_delta_widening_the_band_rescues_the_far_plane(self):
        report = assess_indirect_discharge_setup(
            good_bench(coupling_plane_distance_m=0.4),
            baseline(),
            {"coupling_plane_distance_m": {"maximum_delta": 0.3}},
        )
        self.assertEqual(report["categories"]["coupling_plane_distance_m"], CONFORMING)
        self.assertEqual(report["verdict"], VERDICT_CONFORMING)

    def test_a_plane_smaller_than_the_footprint_is_a_finding(self):
        report = assess(coupling_plane_span_m=0.5)
        self.assertFalse(report["plane_span_is_adequate"])
        self.assertEqual(report["verdict"], VERDICT_NONCONFORMING)

    def test_a_plane_exactly_covering_the_footprint_is_accepted(self):
        report = assess(coupling_plane_span_m=required_plane_span_m(0.4, 0.1))
        self.assertTrue(report["plane_span_is_adequate"])

    def test_an_interval_shorter_than_the_bleed_time_is_a_finding(self):
        report = assess(discharge_interval_s=nominal_tau())
        self.assertFalse(report["bleed_interval_is_adequate"])
        self.assertEqual(report["verdict"], VERDICT_NONCONFORMING)

    def test_an_interval_on_the_bleed_rule_is_accepted_with_residual_charge(self):
        interval = required_bleed_time_s(nominal_tau())
        report = assess(discharge_interval_s=interval)
        self.assertTrue(report["bleed_interval_is_adequate"])
        self.assertEqual(report["findings"], [])
        self.assertGreater(report["residual_plane_fraction"], RESIDUAL_NOTICE_FRACTION)
        self.assertEqual(report["verdict"], VERDICT_CONFORMING)
        self.assertEqual(len(report["limitations"]), 1)

    def test_a_long_interval_leaves_no_residual_worth_reporting(self):
        report = assess()
        self.assertLess(report["residual_plane_fraction"], RESIDUAL_NOTICE_FRACTION)

    def test_a_vertical_plane_is_carried_as_a_limitation(self):
        report = assess(plane_type="vertical-coupling-plane")
        self.assertEqual(report["findings"], [])
        self.assertEqual(report["verdict"], VERDICT_CONFORMING)
        self.assertEqual(len(report["limitations"]), 1)

    def test_a_bleeder_outside_its_band_is_a_finding(self):
        report = assess(bleeder_resistance_ohm=10.0e6)
        self.assertEqual(
            report["categories"]["bleeder_resistance_ohm"], NONCONFORMING
        )
        self.assertEqual(report["verdict"], VERDICT_NONCONFORMING)

    def test_assessment_propagates_a_bench_error(self):
        with self.assertRaises(ValueError):
            assess(coupling_plane_capacitance_f=0.0)


if __name__ == "__main__":
    unittest.main()
