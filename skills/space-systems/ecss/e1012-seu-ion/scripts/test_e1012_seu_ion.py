#!/usr/bin/env python3
"""Stdlib unittest contract test for e1012_seu_ion_logic.

ECSS-E-ST-10-12C §9.4.1.2 — heavy-ion SEU/MCU/SMU rate prediction: Weibull
cross-section, RPP integration, IRPP chord-length correction, MCU/SMU
derivation, upset-type categorization, and design-margin assessment.

Run: python3 test_e1012_seu_ion.py
Must print OK. Offline, deterministic, stdlib only.
"""

import math
import os
import sys
import unittest

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from e1012_seu_ion_logic import (  # noqa: E402
    DEFAULT_MARGIN_FACTOR,
    SECONDS_PER_DAY,
    SEUError,
    assess_design_margin,
    cauchy_mean_chord_length,
    categorize_upset_event,
    check_saturation_coverage,
    derive_mcu_smu_rates,
    environment_supports_upset,
    evaluate_all,
    evaluate_device,
    irpp_effective_let,
    irpp_seu_rate,
    rpp_mean_chord_length,
    rpp_seu_rate,
    saturation_ratio,
    seu_findings,
    spectrum_max_let,
    trapezoidal_integration,
    weibull_cross_section,
)

LTH = 5.0
WIDTH = 10.0
SHAPE = 2.0
SIGMA_SAT = 1.0e-4

LET_SPECTRUM = [(0.0, 1.0e-3), (10.0, 1.0e-3)]

# RPP expected rate: 5 * 1e-3 * sigma_sat * (1 - exp(-0.25)) * 86400
RPP_EXPECTED = 9.55580617131531e-03


def device_spec(**overrides):
    spec = {
        "device_id": "MEM1",
        "weibull": {"let_threshold": LTH, "width": WIDTH,
                    "shape": SHAPE, "sigma_sat": SIGMA_SAT},
        "mcu_fraction": 0.2,
        "smu_fraction": 0.5,
        "requirement_rate": 0.5,
    }
    spec.update(overrides)
    return spec


class TestWeibullCrossSection(unittest.TestCase):
    def test_zero_below_and_at_threshold(self):
        self.assertEqual(weibull_cross_section(4.9, LTH, WIDTH, SHAPE, SIGMA_SAT), 0.0)
        self.assertEqual(weibull_cross_section(LTH, LTH, WIDTH, SHAPE, SIGMA_SAT), 0.0)

    def test_above_threshold_matches_closed_form(self):
        expected = SIGMA_SAT * (1.0 - math.exp(-0.25))
        sigma = weibull_cross_section(10.0, LTH, WIDTH, SHAPE, SIGMA_SAT)
        self.assertAlmostEqual(sigma, expected, places=15)

    def test_monotonic_and_bounded(self):
        values = [weibull_cross_section(l, LTH, WIDTH, SHAPE, SIGMA_SAT)
                  for l in (0.0, 5.0, 6.0, 10.0, 20.0, 100.0)]
        for earlier, later in zip(values, values[1:]):
            self.assertLessEqual(earlier, later)
        for value in values:
            self.assertLessEqual(value, SIGMA_SAT)

    def test_large_let_approaches_saturation(self):
        sigma = weibull_cross_section(1000.0, LTH, WIDTH, SHAPE, SIGMA_SAT)
        self.assertAlmostEqual(sigma, SIGMA_SAT, places=12)

    def test_invalid_parameters_raise(self):
        for args in ((10.0, 0.0, WIDTH, SHAPE, SIGMA_SAT),
                     (10.0, -1.0, WIDTH, SHAPE, SIGMA_SAT),
                     (10.0, LTH, 0.0, SHAPE, SIGMA_SAT),
                     (10.0, LTH, WIDTH, 0.0, SIGMA_SAT),
                     (10.0, LTH, WIDTH, SHAPE, 0.0),
                     (-1.0, LTH, WIDTH, SHAPE, SIGMA_SAT)):
            with self.assertRaises(SEUError):
                weibull_cross_section(*args)


class TestSaturationScreening(unittest.TestCase):
    def test_ratio_near_unity_when_tested_to_high_let(self):
        ratio = saturation_ratio([1.0, 60.0], 1.0, 5.0, 2.0, SIGMA_SAT)
        self.assertGreater(ratio, 0.99)

    def test_coverage_true_for_full_range(self):
        self.assertTrue(check_saturation_coverage([1.0, 60.0], 1.0, 5.0, 2.0, SIGMA_SAT))

    def test_coverage_false_for_partial_range(self):
        self.assertFalse(check_saturation_coverage([1.0, 3.0], 1.0, 5.0, 2.0, SIGMA_SAT))

    def test_partial_range_ratio_below_threshold(self):
        ratio = saturation_ratio([1.0, 3.0], 1.0, 5.0, 2.0, SIGMA_SAT)
        self.assertLess(ratio, 0.99)
        self.assertAlmostEqual(ratio, 1.0 - math.exp(-0.16), places=12)

    def test_empty_let_list_raises(self):
        with self.assertRaises(SEUError):
            saturation_ratio([], 1.0, 5.0, 2.0, SIGMA_SAT)

    def test_non_positive_tolerance_raises(self):
        with self.assertRaises(SEUError):
            check_saturation_coverage([1.0, 60.0], 1.0, 5.0, 2.0, SIGMA_SAT, 0.0)


class TestSensitiveVolumeGeometry(unittest.TestCase):
    def test_cauchy_formula_for_unit_cube(self):
        self.assertAlmostEqual(cauchy_mean_chord_length(1.0, 6.0), 4.0 / 6.0, places=15)

    def test_rpp_mean_chord_for_unit_cube(self):
        self.assertAlmostEqual(rpp_mean_chord_length(1.0, 1.0, 1.0), 4.0 / 6.0, places=15)

    def test_rpp_mean_chord_for_elongated_box(self):
        # V = 2*1*1 = 2, A = 2*(2 + 1 + 2) = 10 -> 4V/A = 0.8
        self.assertAlmostEqual(rpp_mean_chord_length(2.0, 1.0, 1.0), 0.8, places=15)

    def test_invalid_geometry_raises(self):
        with self.assertRaises(SEUError):
            cauchy_mean_chord_length(0.0, 6.0)
        with self.assertRaises(SEUError):
            cauchy_mean_chord_length(1.0, 0.0)
        with self.assertRaises(SEUError):
            rpp_mean_chord_length(0.0, 1.0, 1.0)

    def test_irpp_effective_let_scales_by_depth_over_chord(self):
        # depth 1.0 / mean chord 2/3 = 1.5
        self.assertAlmostEqual(irpp_effective_let(10.0, 1.0, 2.0 / 3.0), 15.0, places=12)

    def test_irpp_effective_let_zero_let_stays_zero(self):
        self.assertEqual(irpp_effective_let(0.0, 1.0, 2.0 / 3.0), 0.0)

    def test_irpp_effective_let_invalid_input_raises(self):
        with self.assertRaises(SEUError):
            irpp_effective_let(10.0, 0.0, 0.5)
        with self.assertRaises(SEUError):
            irpp_effective_let(10.0, 1.0, 0.0)
        with self.assertRaises(SEUError):
            irpp_effective_let(-1.0, 1.0, 0.5)


class TestTrapezoidalIntegration(unittest.TestCase):
    def test_unit_rectangle(self):
        self.assertAlmostEqual(trapezoidal_integration([0.0, 1.0], [1.0, 1.0]), 1.0)

    def test_triangle(self):
        self.assertAlmostEqual(
            trapezoidal_integration([0.0, 1.0, 2.0], [0.0, 2.0, 0.0]), 2.0
        )

    def test_invalid_inputs_raise(self):
        with self.assertRaises(SEUError):
            trapezoidal_integration([0.0, 1.0], [1.0])
        with self.assertRaises(SEUError):
            trapezoidal_integration([0.0], [1.0])
        with self.assertRaises(SEUError):
            trapezoidal_integration([0.0, 0.0], [1.0, 1.0])
        with self.assertRaises(SEUError):
            trapezoidal_integration([1.0, 0.0], [1.0, 1.0])


class TestEnvironmentScreening(unittest.TestCase):
    def test_spectrum_max_let(self):
        self.assertAlmostEqual(spectrum_max_let(LET_SPECTRUM), 10.0)

    def test_supports_upset_when_peak_exceeds_threshold(self):
        self.assertTrue(environment_supports_upset(LET_SPECTRUM, LTH))

    def test_does_not_support_upset_when_peak_below_threshold(self):
        self.assertFalse(environment_supports_upset([(0.0, 1.0), (4.0, 1.0)], LTH))

    def test_invalid_threshold_raises(self):
        with self.assertRaises(SEUError):
            environment_supports_upset(LET_SPECTRUM, 0.0)

    def test_empty_spectrum_raises(self):
        with self.assertRaises(SEUError):
            spectrum_max_let([])

    def test_negative_flux_raises(self):
        with self.assertRaises(SEUError):
            spectrum_max_let([(0.0, 1.0), (10.0, -1.0)])


class TestRppRate(unittest.TestCase):
    def test_rpp_rate_matches_hand_calculation(self):
        rate = rpp_seu_rate(LET_SPECTRUM, LTH, WIDTH, SHAPE, SIGMA_SAT)
        self.assertAlmostEqual(rate, RPP_EXPECTED, places=7)

    def test_rpp_rate_zero_below_threshold_spectrum(self):
        rate = rpp_seu_rate([(0.0, 1.0), (4.0, 1.0)], LTH, WIDTH, SHAPE, SIGMA_SAT)
        self.assertEqual(rate, 0.0)

    def test_rpp_scales_with_seconds_per_day(self):
        daily = rpp_seu_rate(LET_SPECTRUM, LTH, WIDTH, SHAPE, SIGMA_SAT)
        per_second = rpp_seu_rate(LET_SPECTRUM, LTH, WIDTH, SHAPE, SIGMA_SAT,
                                  seconds_per_day=1.0)
        self.assertAlmostEqual(daily, per_second * SECONDS_PER_DAY, places=18)

    def test_rpp_invalid_weibull_raises(self):
        with self.assertRaises(SEUError):
            rpp_seu_rate(LET_SPECTRUM, 0.0, WIDTH, SHAPE, SIGMA_SAT)

    def test_rpp_zero_seconds_per_day_raises(self):
        with self.assertRaises(SEUError):
            rpp_seu_rate(LET_SPECTRUM, LTH, WIDTH, SHAPE, SIGMA_SAT, seconds_per_day=0.0)

    def test_rpp_flat_saturation_estimate_is_higher(self):
        # A flat sigma_sat over the spectrum overstates the rate relative to
        # the Weibull roll-on.
        flat = trapezoidal_integration([0.0, 10.0],
                                       [SIGMA_SAT * 1.0e-3, SIGMA_SAT * 1.0e-3])
        flat_rate = flat * SECONDS_PER_DAY
        self.assertGreater(flat_rate,
                           rpp_seu_rate(LET_SPECTRUM, LTH, WIDTH, SHAPE, SIGMA_SAT))


class TestIrppRate(unittest.TestCase):
    def test_irpp_exceeds_rpp_when_ratio_above_unity(self):
        # depth / mean chord = 1 / (2/3) = 1.5 -> effective LET is enhanced
        rpp = rpp_seu_rate(LET_SPECTRUM, LTH, WIDTH, SHAPE, SIGMA_SAT)
        irpp = irpp_seu_rate(LET_SPECTRUM, LTH, WIDTH, SHAPE, SIGMA_SAT,
                             sensitive_depth_cm=1.0, mean_chord_cm=2.0 / 3.0)
        self.assertGreater(irpp, rpp)

    def test_irpp_below_rpp_when_ratio_below_unity(self):
        # depth / mean chord = 0.5 / (2/3) = 0.75
        rpp = rpp_seu_rate(LET_SPECTRUM, LTH, WIDTH, SHAPE, SIGMA_SAT)
        irpp = irpp_seu_rate(LET_SPECTRUM, LTH, WIDTH, SHAPE, SIGMA_SAT,
                             sensitive_depth_cm=0.5, mean_chord_cm=2.0 / 3.0)
        self.assertLess(irpp, rpp)

    def test_irpp_matches_rpp_when_ratio_is_unity(self):
        rpp = rpp_seu_rate(LET_SPECTRUM, LTH, WIDTH, SHAPE, SIGMA_SAT)
        irpp = irpp_seu_rate(LET_SPECTRUM, LTH, WIDTH, SHAPE, SIGMA_SAT,
                             sensitive_depth_cm=1.0, mean_chord_cm=1.0)
        self.assertAlmostEqual(irpp, rpp, places=15)

    def test_irpp_rate_scales_with_seconds_per_day(self):
        params = (LTH, WIDTH, SHAPE, SIGMA_SAT)
        daily = irpp_seu_rate(LET_SPECTRUM, *params, 1.0, 2.0 / 3.0)
        per_second = irpp_seu_rate(LET_SPECTRUM, *params, 1.0, 2.0 / 3.0,
                                   seconds_per_day=1.0)
        self.assertAlmostEqual(daily, per_second * SECONDS_PER_DAY, places=18)

    def test_irpp_invalid_geometry_raises(self):
        with self.assertRaises(SEUError):
            irpp_seu_rate(LET_SPECTRUM, LTH, WIDTH, SHAPE, SIGMA_SAT, 0.0, 0.5)
        with self.assertRaises(SEUError):
            irpp_seu_rate(LET_SPECTRUM, LTH, WIDTH, SHAPE, SIGMA_SAT, 1.0, 0.0)


class TestUpsetTypeCategorization(unittest.TestCase):
    def test_single_cell_is_seu(self):
        self.assertEqual(categorize_upset_event(1, 8, False), "SEU")
        self.assertEqual(categorize_upset_event(1, 8, True), "SEU")

    def test_multi_cell_same_word_is_smu(self):
        self.assertEqual(categorize_upset_event(3, 8, True), "SMU")

    def test_multi_cell_across_words_is_mcu(self):
        self.assertEqual(categorize_upset_event(3, 8, False), "MCU")

    def test_full_word_is_smu(self):
        self.assertEqual(categorize_upset_event(8, 8, True), "SMU")

    def test_zero_bits_raises(self):
        with self.assertRaises(SEUError):
            categorize_upset_event(0, 8, False)

    def test_zero_word_width_raises(self):
        with self.assertRaises(SEUError):
            categorize_upset_event(2, 0, True)

    def test_single_word_event_cannot_exceed_word_width(self):
        with self.assertRaises(SEUError):
            categorize_upset_event(9, 8, True)


class TestMcuSmuDerivation(unittest.TestCase):
    def test_rates_derived_from_fractions(self):
        rates = derive_mcu_smu_rates(2.0, 0.5, 0.5)
        self.assertAlmostEqual(rates["seu_rate"], 2.0)
        self.assertAlmostEqual(rates["mcu_rate"], 1.0)
        self.assertAlmostEqual(rates["smu_rate"], 0.5)
        self.assertAlmostEqual(rates["uncorrectable_rate"], 0.5)

    def test_zero_fractions_give_zero_derived_rates(self):
        rates = derive_mcu_smu_rates(3.0, 0.0, 0.0)
        self.assertEqual(rates["mcu_rate"], 0.0)
        self.assertEqual(rates["smu_rate"], 0.0)

    def test_zero_seu_rate_gives_zero_derived_rates(self):
        rates = derive_mcu_smu_rates(0.0, 1.0, 1.0)
        self.assertEqual(rates["mcu_rate"], 0.0)
        self.assertEqual(rates["smu_rate"], 0.0)

    def test_uncorrectable_rate_equals_smu_rate(self):
        rates = derive_mcu_smu_rates(10.0, 0.2, 0.75)
        self.assertAlmostEqual(rates["uncorrectable_rate"], rates["smu_rate"], places=15)

    def test_negative_seu_rate_raises(self):
        with self.assertRaises(SEUError):
            derive_mcu_smu_rates(-1.0, 0.2, 0.5)

    def test_fraction_above_one_raises(self):
        with self.assertRaises(SEUError):
            derive_mcu_smu_rates(1.0, 1.5, 0.5)
        with self.assertRaises(SEUError):
            derive_mcu_smu_rates(1.0, 0.5, 1.5)

    def test_negative_fraction_raises(self):
        with self.assertRaises(SEUError):
            derive_mcu_smu_rates(1.0, -0.1, 0.5)


class TestDesignMargin(unittest.TestCase):
    def test_exact_ten_times_margin_is_compliant(self):
        # requirement 0.625 / predicted 0.0625 = 10 exactly
        margin = assess_design_margin(0.0625, 0.625)
        self.assertAlmostEqual(margin["margin_ratio"], 10.0, places=12)
        self.assertTrue(margin["requirement_met"])
        self.assertTrue(margin["margin_met"])
        self.assertTrue(margin["compliant"])
        self.assertIsNone(margin["finding"])
        self.assertEqual(margin["margin_factor"], DEFAULT_MARGIN_FACTOR)

    def test_passes_requirement_but_margin_below_factor_is_flagged(self):
        # 0.5 / 0.125 = 4 -> inside requirement but only 4x margin
        margin = assess_design_margin(0.125, 0.5)
        self.assertAlmostEqual(margin["margin_ratio"], 4.0, places=12)
        self.assertTrue(margin["requirement_met"])
        self.assertFalse(margin["margin_met"])
        self.assertFalse(margin["compliant"])
        self.assertEqual(margin["finding"]["issue"], "margin_below_factor")

    def test_rate_above_requirement_is_flagged(self):
        margin = assess_design_margin(0.75, 0.5)
        self.assertFalse(margin["requirement_met"])
        self.assertFalse(margin["compliant"])
        self.assertEqual(margin["finding"]["issue"], "seu_rate_exceeds_requirement")

    def test_zero_predicted_rate_passes_with_infinite_margin(self):
        margin = assess_design_margin(0.0, 0.5)
        self.assertTrue(math.isinf(margin["margin_ratio"]))
        self.assertTrue(margin["compliant"])
        self.assertIsNone(margin["finding"])

    def test_custom_margin_factor_relaxes_check(self):
        margin = assess_design_margin(0.125, 0.5, margin_factor=4.0)
        self.assertTrue(margin["margin_met"])
        self.assertTrue(margin["compliant"])

    def test_smu_rate_label_is_reported(self):
        margin = assess_design_margin(0.0625, 0.625, rate_label="SMU")
        self.assertEqual(margin["rate_label"], "SMU")

    def test_invalid_inputs_raise(self):
        with self.assertRaises(SEUError):
            assess_design_margin(-1.0, 1.0)
        with self.assertRaises(SEUError):
            assess_design_margin(0.1, 0.0)
        with self.assertRaises(SEUError):
            assess_design_margin(0.1, 1.0, margin_factor=0.0)


class TestEvaluateDeviceRpp(unittest.TestCase):
    def test_rpp_evaluation_rates(self):
        result = evaluate_device(device_spec(), LET_SPECTRUM)
        self.assertEqual(result["method"], "RPP")
        self.assertFalse(result["environment_limited"])
        self.assertAlmostEqual(result["seu_rate"], RPP_EXPECTED, places=7)
        self.assertAlmostEqual(result["mcu_rate"], RPP_EXPECTED * 0.2, places=12)
        self.assertAlmostEqual(result["smu_rate"], RPP_EXPECTED * 0.1, places=12)

    def test_seu_rate_assessed_without_edac(self):
        result = evaluate_device(device_spec(), LET_SPECTRUM)
        self.assertEqual(result["assessed_rate_label"], "SEU")
        self.assertAlmostEqual(result["assessed_rate"], result["seu_rate"], places=15)

    def test_smu_rate_assessed_with_edac(self):
        result = evaluate_device(device_spec(edac=True), LET_SPECTRUM)
        self.assertEqual(result["assessed_rate_label"], "SMU")
        self.assertAlmostEqual(result["assessed_rate"], result["smu_rate"], places=15)

    def test_generous_requirement_is_compliant(self):
        result = evaluate_device(device_spec(requirement_rate=0.5), LET_SPECTRUM)
        self.assertTrue(result["margin"]["compliant"])
        self.assertIsNone(result["finding"])

    def test_insufficient_margin_is_flagged(self):
        result = evaluate_device(device_spec(requirement_rate=0.05), LET_SPECTRUM)
        self.assertFalse(result["margin"]["compliant"])
        self.assertEqual(result["finding"]["issue"], "margin_below_factor")

    def test_rate_above_requirement_is_flagged(self):
        result = evaluate_device(device_spec(requirement_rate=0.005), LET_SPECTRUM)
        self.assertEqual(result["finding"]["issue"], "seu_rate_exceeds_requirement")

    def test_environment_limited_result_is_zero_rate(self):
        spectrum = [(0.0, 1.0), (4.0, 1.0)]
        result = evaluate_device(device_spec(), spectrum)
        self.assertTrue(result["environment_limited"])
        self.assertEqual(result["seu_rate"], 0.0)
        self.assertEqual(result["mcu_rate"], 0.0)
        self.assertEqual(result["smu_rate"], 0.0)
        self.assertIsNone(result["finding"])

    def test_unknown_method_raises(self):
        with self.assertRaises(SEUError):
            evaluate_device(device_spec(), LET_SPECTRUM, method="MONTE_CARLO")

    def test_missing_weibull_parameter_raises(self):
        spec = device_spec()
        del spec["weibull"]["shape"]
        with self.assertRaises(SEUError):
            evaluate_device(spec, LET_SPECTRUM)

    def test_missing_weibull_block_raises(self):
        spec = device_spec()
        del spec["weibull"]
        with self.assertRaises(SEUError):
            evaluate_device(spec, LET_SPECTRUM)

    def test_missing_mcu_fraction_raises(self):
        spec = device_spec()
        del spec["mcu_fraction"]
        with self.assertRaises(SEUError):
            evaluate_device(spec, LET_SPECTRUM)

    def test_missing_smu_fraction_raises(self):
        spec = device_spec()
        del spec["smu_fraction"]
        with self.assertRaises(SEUError):
            evaluate_device(spec, LET_SPECTRUM)

    def test_missing_requirement_raises(self):
        spec = device_spec()
        del spec["requirement_rate"]
        with self.assertRaises(SEUError):
            evaluate_device(spec, LET_SPECTRUM)

    def test_non_dict_spec_raises(self):
        with self.assertRaises(SEUError):
            evaluate_device("MEM1", LET_SPECTRUM)


class TestEvaluateDeviceIrpp(unittest.TestCase):
    def test_irpp_uses_geometry_and_raises_the_rate(self):
        spec = device_spec()
        spec["sensitive_volume"] = {"x_cm": 1.0, "y_cm": 1.0, "z_cm": 1.0,
                                    "depth_cm": 1.0}
        irpp = evaluate_device(spec, LET_SPECTRUM, method="IRPP")
        rpp = evaluate_device(device_spec(), LET_SPECTRUM, method="RPP")
        self.assertEqual(irpp["method"], "IRPP")
        self.assertGreater(irpp["seu_rate"], rpp["seu_rate"])

    def test_irpp_accepts_explicit_mean_chord(self):
        spec = device_spec()
        spec["sensitive_volume"] = {"depth_cm": 1.0, "mean_chord_cm": 1.0}
        result = evaluate_device(spec, LET_SPECTRUM, method="IRPP")
        rpp = evaluate_device(device_spec(), LET_SPECTRUM, method="RPP")
        self.assertAlmostEqual(result["seu_rate"], rpp["seu_rate"], places=15)

    def test_irpp_accepts_volume_and_area(self):
        spec = device_spec()
        spec["sensitive_volume"] = {"depth_cm": 1.0, "volume_cm3": 1.0,
                                    "surface_area_cm2": 6.0}
        result = evaluate_device(spec, LET_SPECTRUM, method="IRPP")
        self.assertGreater(result["seu_rate"], 0.0)

    def test_irpp_missing_sensitive_volume_raises(self):
        with self.assertRaises(SEUError):
            evaluate_device(device_spec(), LET_SPECTRUM, method="IRPP")

    def test_irpp_volume_without_geometry_raises(self):
        spec = device_spec()
        spec["sensitive_volume"] = {"depth_cm": 1.0}
        with self.assertRaises(SEUError):
            evaluate_device(spec, LET_SPECTRUM, method="IRPP")

    def test_irpp_missing_depth_raises(self):
        spec = device_spec()
        spec["sensitive_volume"] = {"x_cm": 1.0, "y_cm": 1.0, "z_cm": 1.0}
        with self.assertRaises(SEUError):
            evaluate_device(spec, LET_SPECTRUM, method="IRPP")


class TestEvaluateAll(unittest.TestCase):
    def test_order_preserved_and_findings_collected(self):
        devices = [
            device_spec(device_id="A", requirement_rate=0.5),
            device_spec(device_id="B", requirement_rate=0.05),
        ]
        results = evaluate_all(devices, LET_SPECTRUM)
        self.assertEqual([r["device_id"] for r in results], ["A", "B"])
        findings = seu_findings(results)
        self.assertEqual(len(findings), 1)
        self.assertEqual(findings[0]["issue"], "margin_below_factor")

    def test_all_passing_gives_no_findings(self):
        devices = [device_spec(device_id="A", requirement_rate=0.5)]
        self.assertEqual(seu_findings(evaluate_all(devices, LET_SPECTRUM)), [])

    def test_environment_limited_devices_give_no_findings(self):
        devices = [device_spec(device_id="A", requirement_rate=1.0e-9)]
        results = evaluate_all(devices, [(0.0, 1.0), (4.0, 1.0)])
        self.assertEqual(seu_findings(results), [])

    def test_empty_device_list(self):
        self.assertEqual(evaluate_all([], LET_SPECTRUM), [])

    def test_invalid_device_raises(self):
        devices = [device_spec(), {"device_id": "BAD"}]
        with self.assertRaises(SEUError):
            evaluate_all(devices, LET_SPECTRUM)


if __name__ == "__main__":
    unittest.main()
