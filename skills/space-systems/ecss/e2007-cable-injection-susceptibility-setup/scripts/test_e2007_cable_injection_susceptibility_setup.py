#!/usr/bin/env python3
"""Gate 3 contract test for e2007-cable-injection-susceptibility-setup.

stdlib unittest, offline, deterministic. Run:
    python3 test_e2007_cable_injection_susceptibility_setup.py
"""

import unittest

from e2007_cable_injection_susceptibility_setup_logic import (
    APERTURE_MULTIPLE,
    CONFORMING,
    DECLARED_DEVIATION,
    NONCONFORMING,
    SPEED_OF_LIGHT_M_S,
    VERDICT_CONFORMING,
    VERDICT_NONCONFORMING,
    VERDICT_WITH_DEVIATIONS,
    WAVELENGTH_FRACTION,
    apply_setup_deltas,
    assess_injection_setup,
    band_margin,
    calibration_error_db,
    categorize_parameter,
    governing_parameter,
    harness_resonance_hz,
    maximum_probe_separation_m,
    minimum_probe_separation_m,
    probe_separation_m,
    validate_band,
    validate_bench,
)

BAND_HIGH_HZ = 5.0e7


def baseline():
    return {
        "bond_resistance_ohm": (0.0, 0.0025),
        "harness_height_m": (0.03, 0.07),
        "harness_length_m": (0.5, 2.0),
        "injection_probe_to_eut_m": (0.05, 0.60),
        "monitor_probe_to_eut_m": (0.02, 0.30),
    }


def good_bench(**over):
    record = {
        "coupling_method": "current-injection-probe",
        "level_control": "closed-loop-monitored",
        "band_high_hz": BAND_HIGH_HZ,
        "bench_common_mode_impedance_ohm": 100.0,
        "calibration_fixture_impedance_ohm": 100.0,
        "harness_height_m": 0.05,
        "harness_length_m": 1.0,
        "injection_probe_to_eut_m": 0.30,
        "monitor_probe_to_eut_m": 0.05,
        "probe_aperture_m": 0.05,
        "bond_resistance_ohm": 0.001,
        "declared_deviations": (),
    }
    record.update(over)
    return record


def assess(**over):
    return assess_injection_setup(good_bench(**over), baseline())


class TestBenchValidation(unittest.TestCase):
    def test_a_good_bench_normalizes(self):
        bench = validate_bench(good_bench())
        self.assertEqual(bench["coupling_method"], "current-injection-probe")
        self.assertAlmostEqual(bench["harness_length_m"], 1.0, places=9)

    def test_the_coupling_method_token_is_case_normalized(self):
        bench = validate_bench(good_bench(coupling_method="Capacitive-Coupling-Clamp"))
        self.assertEqual(bench["coupling_method"], "capacitive-coupling-clamp")

    def test_an_unknown_coupling_method_is_rejected(self):
        with self.assertRaises(ValueError):
            validate_bench(good_bench(coupling_method="hand-wound-loop"))

    def test_an_unknown_level_control_is_rejected(self):
        with self.assertRaises(ValueError):
            validate_bench(good_bench(level_control="by-eye"))

    def test_a_zero_harness_length_is_rejected(self):
        with self.assertRaises(ValueError):
            validate_bench(good_bench(harness_length_m=0.0))

    def test_a_negative_bond_resistance_is_rejected(self):
        with self.assertRaises(ValueError):
            validate_bench(good_bench(bond_resistance_ohm=-0.001))

    def test_a_zero_bond_resistance_is_accepted(self):
        bench = validate_bench(good_bench(bond_resistance_ohm=0.0))
        self.assertAlmostEqual(bench["bond_resistance_ohm"], 0.0, places=12)

    def test_a_missing_field_is_rejected(self):
        record = good_bench()
        del record["probe_aperture_m"]
        with self.assertRaises(ValueError):
            validate_bench(record)

    def test_a_boolean_band_ceiling_is_rejected(self):
        with self.assertRaises(ValueError):
            validate_bench(good_bench(band_high_hz=True))

    def test_declared_deviations_as_a_bare_string_is_rejected(self):
        with self.assertRaises(ValueError):
            validate_bench(good_bench(declared_deviations="harness_length_m"))

    def test_a_declared_deviation_on_an_ungraded_parameter_is_rejected(self):
        with self.assertRaises(ValueError):
            validate_bench(good_bench(declared_deviations=("probe_aperture_m",)))


class TestBandsAndDeltas(unittest.TestCase):
    def test_bands_pass_through_when_no_delta_is_declared(self):
        bands = apply_setup_deltas(baseline(), None)
        self.assertAlmostEqual(bands["harness_length_m"][1], 2.0, places=9)

    def test_a_delta_moves_the_band_edge_it_names(self):
        bands = apply_setup_deltas(
            baseline(), {"harness_length_m": {"maximum_delta": 1.0}}
        )
        self.assertAlmostEqual(bands["harness_length_m"][1], 3.0, places=9)
        self.assertAlmostEqual(bands["harness_length_m"][0], 0.5, places=9)

    def test_an_unknown_delta_parameter_is_refused(self):
        with self.assertRaises(ValueError):
            apply_setup_deltas(baseline(), {"room_humidity_pct": {"maximum_delta": 1.0}})

    def test_an_unknown_delta_key_is_refused(self):
        with self.assertRaises(ValueError):
            apply_setup_deltas(baseline(), {"harness_length_m": {"scale": 2.0}})

    def test_a_delta_that_collapses_a_band_is_refused(self):
        with self.assertRaises(ValueError):
            apply_setup_deltas(baseline(), {"harness_height_m": {"minimum_delta": 0.05}})

    def test_an_inverted_baseline_band_is_refused(self):
        bands = baseline()
        bands["harness_length_m"] = (2.0, 0.5)
        with self.assertRaises(ValueError):
            apply_setup_deltas(bands, None)

    def test_an_unknown_baseline_parameter_is_refused(self):
        bands = baseline()
        bands["chamber_volume_m3"] = (10.0, 40.0)
        with self.assertRaises(ValueError):
            apply_setup_deltas(bands, None)

    def test_a_band_must_be_a_pair(self):
        with self.assertRaises(ValueError):
            validate_band((0.1, 0.2, 0.3), "harness_length_m")


class TestParameterGrading(unittest.TestCase):
    def test_a_value_inside_the_band_conforms(self):
        self.assertEqual(categorize_parameter(1.0, (0.5, 2.0)), CONFORMING)

    def test_a_value_landing_on_the_upper_edge_conforms(self):
        self.assertEqual(categorize_parameter(2.0, (0.5, 2.0)), CONFORMING)

    def test_an_undeclared_excursion_is_nonconforming(self):
        self.assertEqual(categorize_parameter(2.4, (0.5, 2.0)), NONCONFORMING)

    def test_a_declared_excursion_is_a_declared_deviation(self):
        self.assertEqual(categorize_parameter(2.4, (0.5, 2.0), True), DECLARED_DEVIATION)

    def test_the_band_margin_at_the_centre_is_one_half(self):
        self.assertAlmostEqual(band_margin(1.25, (0.5, 2.0)), 0.5, places=9)

    def test_the_band_margin_outside_the_band_is_negative(self):
        self.assertLess(band_margin(2.9, (0.5, 2.0)), 0.0)

    def test_the_governing_parameter_is_the_tightest_one(self):
        self.assertEqual(
            governing_parameter(validate_bench(good_bench()), baseline()),
            "monitor_probe_to_eut_m",
        )


class TestCouplingGeometry(unittest.TestCase):
    def test_the_separation_is_the_gap_between_the_two_probes(self):
        self.assertAlmostEqual(
            probe_separation_m(validate_bench(good_bench())), 0.25, places=9
        )

    def test_the_minimum_separation_is_a_multiple_of_the_aperture(self):
        self.assertAlmostEqual(
            minimum_probe_separation_m(0.05, APERTURE_MULTIPLE), 0.075, places=9
        )

    def test_an_aperture_multiple_below_unity_is_rejected(self):
        with self.assertRaises(ValueError):
            minimum_probe_separation_m(0.05, 0.5)

    def test_the_maximum_separation_is_a_fraction_of_a_wavelength(self):
        self.assertAlmostEqual(
            maximum_probe_separation_m(BAND_HIGH_HZ, WAVELENGTH_FRACTION),
            WAVELENGTH_FRACTION * SPEED_OF_LIGHT_M_S / BAND_HIGH_HZ,
            places=12,
        )

    def test_a_wavelength_fraction_past_a_whole_wavelength_is_rejected(self):
        with self.assertRaises(ValueError):
            maximum_probe_separation_m(BAND_HIGH_HZ, 1.5)

    def test_a_zero_band_ceiling_is_rejected(self):
        with self.assertRaises(ValueError):
            maximum_probe_separation_m(0.0)

    def test_the_harness_resonance_is_the_quarter_wave_of_its_length(self):
        self.assertAlmostEqual(
            harness_resonance_hz(1.0), SPEED_OF_LIGHT_M_S / 4.0, places=3
        )

    def test_a_longer_harness_resonates_lower(self):
        self.assertLess(harness_resonance_hz(4.0), harness_resonance_hz(1.0))

    def test_a_zero_harness_length_is_rejected(self):
        with self.assertRaises(ValueError):
            harness_resonance_hz(0.0)

    def test_a_jig_matching_the_bench_carries_no_calibration_error(self):
        self.assertAlmostEqual(calibration_error_db(100.0, 100.0), 0.0, places=9)

    def test_a_tenfold_impedance_is_twenty_decibels_of_error(self):
        self.assertAlmostEqual(calibration_error_db(1000.0, 100.0), 20.0, places=9)

    def test_a_zero_bench_impedance_is_rejected(self):
        with self.assertRaises(ValueError):
            calibration_error_db(100.0, 0.0)


class TestSetupAssessment(unittest.TestCase):
    def test_a_good_bench_is_setup_conforming(self):
        report = assess()
        self.assertEqual(report["findings"], [])
        self.assertEqual(report["limitations"], [])
        self.assertEqual(report["verdict"], VERDICT_CONFORMING)
        self.assertTrue(report["probe_order_is_right"])
        self.assertTrue(report["probe_separation_is_adequate"])
        self.assertTrue(report["band_is_below_resonance"])
        self.assertTrue(report["calibration_is_adequate"])

    def test_the_report_names_the_governing_parameter(self):
        self.assertEqual(assess()["governing_parameter"], "monitor_probe_to_eut_m")

    def test_an_undeclared_harness_height_is_a_finding(self):
        report = assess(harness_height_m=0.12)
        self.assertEqual(report["categories"]["harness_height_m"], NONCONFORMING)
        self.assertEqual(report["verdict"], VERDICT_NONCONFORMING)
        self.assertEqual(len(report["findings"]), 1)

    def test_the_same_height_declared_becomes_a_limitation(self):
        report = assess(
            harness_height_m=0.12, declared_deviations=("harness_height_m",)
        )
        self.assertEqual(report["categories"]["harness_height_m"], DECLARED_DEVIATION)
        self.assertEqual(report["findings"], [])
        self.assertEqual(report["verdict"], VERDICT_WITH_DEVIATIONS)
        self.assertEqual(len(report["limitations"]), 1)

    def test_a_delta_widening_the_band_rescues_the_height(self):
        report = assess_injection_setup(
            good_bench(harness_height_m=0.12),
            baseline(),
            {"harness_height_m": {"maximum_delta": 0.08}},
        )
        self.assertEqual(report["categories"]["harness_height_m"], CONFORMING)
        self.assertEqual(report["verdict"], VERDICT_CONFORMING)

    def test_probes_in_the_wrong_order_are_a_finding(self):
        report = assess(injection_probe_to_eut_m=0.05, monitor_probe_to_eut_m=0.25)
        self.assertFalse(report["probe_order_is_right"])
        self.assertEqual(report["verdict"], VERDICT_NONCONFORMING)

    def test_probes_too_close_together_are_a_finding(self):
        report = assess(injection_probe_to_eut_m=0.09, monitor_probe_to_eut_m=0.05)
        self.assertTrue(report["probe_order_is_right"])
        self.assertFalse(report["probe_separation_is_adequate"])
        self.assertEqual(report["verdict"], VERDICT_NONCONFORMING)

    def test_probes_too_far_apart_are_a_finding(self):
        report = assess(injection_probe_to_eut_m=0.60, monitor_probe_to_eut_m=0.02)
        self.assertFalse(report["probe_separation_is_adequate"])
        self.assertEqual(report["categories"]["injection_probe_to_eut_m"], CONFORMING)
        self.assertEqual(report["verdict"], VERDICT_NONCONFORMING)

    def test_a_band_reaching_past_the_harness_resonance_is_a_finding(self):
        report = assess(harness_length_m=1.9)
        self.assertFalse(report["band_is_below_resonance"])
        self.assertEqual(report["categories"]["harness_length_m"], CONFORMING)
        self.assertEqual(len(report["findings"]), 1)

    def test_an_open_loop_level_with_a_mismatched_jig_is_a_finding(self):
        report = assess(
            level_control="open-loop-calibrated",
            calibration_fixture_impedance_ohm=200.0,
        )
        self.assertFalse(report["calibration_is_adequate"])
        self.assertEqual(report["verdict"], VERDICT_NONCONFORMING)

    def test_the_same_mismatch_closed_loop_is_only_a_limitation(self):
        report = assess(calibration_fixture_impedance_ohm=200.0)
        self.assertFalse(report["calibration_is_adequate"])
        self.assertEqual(report["findings"], [])
        self.assertEqual(report["verdict"], VERDICT_WITH_DEVIATIONS)

    def test_a_capacitive_clamp_is_carried_as_a_limitation(self):
        report = assess(coupling_method="capacitive-coupling-clamp")
        self.assertEqual(report["findings"], [])
        self.assertEqual(len(report["limitations"]), 1)
        self.assertEqual(report["verdict"], VERDICT_WITH_DEVIATIONS)

    def test_a_negative_calibration_tolerance_is_rejected(self):
        with self.assertRaises(ValueError):
            assess_injection_setup(
                good_bench(), baseline(), calibration_tolerance_db=-1.0
            )

    def test_the_assessment_propagates_a_bench_error(self):
        with self.assertRaises(ValueError):
            assess(probe_aperture_m=0.0)


if __name__ == "__main__":
    unittest.main()
