#!/usr/bin/env python3
"""Stdlib unittest contract test for e1012_set_logic.

ECSS-E-ST-10C §9.4.1.7 — SET rate prediction: Weibull cross-section
evaluation, heavy-ion trapezoidal integration over the differential LET
spectrum, proton threshold integration, the neutron rate formula, total rate
summation, and budget compliance.

Run: python3 test_e1012_set.py
Must print OK. Offline, deterministic, stdlib only.
"""

import math
import os
import sys
import unittest

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from e1012_set_logic import (  # noqa: E402
    HEAVY_ION,
    NEUTRON,
    PROTON,
    SECONDS_PER_DAY,
    SETError,
    check_set_budget,
    evaluate_all,
    evaluate_device,
    heavy_ion_set_rate,
    neutron_set_rate,
    proton_cross_section,
    proton_set_rate,
    set_findings,
    total_set_rate,
    trapezoidal_integration,
    weibull_cross_section,
)

# Reference Weibull device used throughout the numeric checks.
LTH = 5.0
WIDTH = 10.0
SHAPE = 2.0
SIGMA_SAT = 1.0e-4

# Differential LET spectrum: 1e-3 particles/(cm²·s·MeV·cm²/mg) at both points.
LET_SPECTRUM = [(0.0, 1.0e-3), (10.0, 1.0e-3)]

# Differential proton energy spectrum.
PROTON_SPECTRUM = [(0.0, 1.0e-3), (100.0, 1.0e-3)]


def weibull_reference(let):
    """Closed-form reference value of the Weibull cross-section model."""
    if let <= LTH:
        return 0.0
    return SIGMA_SAT * (1.0 - math.exp(-(((let - LTH) / WIDTH) ** SHAPE)))


def reference_device(device_id="U1", budget=100.0):
    spec = {
        "device_id": device_id,
        "heavy_ion": {"let_threshold": LTH, "sigma_sat": SIGMA_SAT,
                      "width": WIDTH, "shape": SHAPE},
        "proton": {"energy_threshold": 30.0, "sigma_sat": 1.0e-6},
        "neutron": {"sigma_n": 1.0e-6},
    }
    if budget is not None:
        spec["set_budget"] = budget
    return spec


REFERENCE_ENVIRONMENT = {
    "let_spectrum": LET_SPECTRUM,
    "proton_spectrum": PROTON_SPECTRUM,
    "neutron_flux": 1.0e2,
}


class TestWeibullCrossSection(unittest.TestCase):
    def test_zero_below_threshold(self):
        self.assertEqual(weibull_cross_section(4.9, LTH, SIGMA_SAT, WIDTH, SHAPE), 0.0)

    def test_zero_at_threshold(self):
        self.assertEqual(weibull_cross_section(LTH, LTH, SIGMA_SAT, WIDTH, SHAPE), 0.0)

    def test_value_above_threshold_matches_reference(self):
        sigma = weibull_cross_section(10.0, LTH, SIGMA_SAT, WIDTH, SHAPE)
        self.assertAlmostEqual(sigma, weibull_reference(10.0), places=15)

    def test_known_midpoint_value(self):
        # sigma(10) = 1e-4 * (1 - exp(-0.25)) = 2.2119921693e-05 cm²/device
        sigma = weibull_cross_section(10.0, LTH, SIGMA_SAT, WIDTH, SHAPE)
        self.assertAlmostEqual(sigma, 2.2119921692859512e-05, places=15)

    def test_monotonic_rise_with_let(self):
        values = [weibull_cross_section(l, LTH, SIGMA_SAT, WIDTH, SHAPE)
                  for l in (0.0, 5.0, 6.0, 10.0, 20.0, 50.0)]
        for earlier, later in zip(values, values[1:]):
            self.assertLessEqual(earlier, later)

    def test_never_exceeds_saturation(self):
        for let in (1.0, 5.0, 10.0, 100.0, 1000.0):
            sigma = weibull_cross_section(let, LTH, SIGMA_SAT, WIDTH, SHAPE)
            self.assertLessEqual(sigma, SIGMA_SAT)

    def test_large_let_approaches_saturation(self):
        sigma = weibull_cross_section(1000.0, LTH, SIGMA_SAT, WIDTH, SHAPE)
        self.assertAlmostEqual(sigma, SIGMA_SAT, places=12)

    def test_zero_let_threshold_raises(self):
        with self.assertRaises(SETError):
            weibull_cross_section(10.0, 0.0, SIGMA_SAT, WIDTH, SHAPE)

    def test_negative_let_threshold_raises(self):
        with self.assertRaises(SETError):
            weibull_cross_section(10.0, -1.0, SIGMA_SAT, WIDTH, SHAPE)

    def test_zero_sigma_sat_raises(self):
        with self.assertRaises(SETError):
            weibull_cross_section(10.0, LTH, 0.0, WIDTH, SHAPE)

    def test_zero_width_raises(self):
        with self.assertRaises(SETError):
            weibull_cross_section(10.0, LTH, SIGMA_SAT, 0.0, SHAPE)

    def test_zero_shape_raises(self):
        with self.assertRaises(SETError):
            weibull_cross_section(10.0, LTH, SIGMA_SAT, WIDTH, 0.0)

    def test_negative_let_raises(self):
        with self.assertRaises(SETError):
            weibull_cross_section(-1.0, LTH, SIGMA_SAT, WIDTH, SHAPE)


class TestProtonCrossSection(unittest.TestCase):
    def test_zero_below_threshold(self):
        self.assertEqual(proton_cross_section(20.0, 30.0, 1.0e-6), 0.0)

    def test_saturation_at_threshold(self):
        self.assertEqual(proton_cross_section(30.0, 30.0, 1.0e-6), 1.0e-6)

    def test_saturation_above_threshold(self):
        self.assertEqual(proton_cross_section(200.0, 30.0, 1.0e-6), 1.0e-6)

    def test_zero_energy_is_below_threshold(self):
        self.assertEqual(proton_cross_section(0.0, 30.0, 1.0e-6), 0.0)

    def test_zero_threshold_raises(self):
        with self.assertRaises(SETError):
            proton_cross_section(10.0, 0.0, 1.0e-6)

    def test_zero_sigma_sat_raises(self):
        with self.assertRaises(SETError):
            proton_cross_section(10.0, 30.0, 0.0)

    def test_negative_energy_raises(self):
        with self.assertRaises(SETError):
            proton_cross_section(-1.0, 30.0, 1.0e-6)


class TestTrapezoidalIntegration(unittest.TestCase):
    def test_unit_rectangle(self):
        self.assertAlmostEqual(trapezoidal_integration([0.0, 1.0], [1.0, 1.0]), 1.0)

    def test_triangle(self):
        # (0,0) -> (1,2) -> (2,0): 1 + 1 = 2
        self.assertAlmostEqual(
            trapezoidal_integration([0.0, 1.0, 2.0], [0.0, 2.0, 0.0]), 2.0
        )

    def test_length_mismatch_raises(self):
        with self.assertRaises(SETError):
            trapezoidal_integration([0.0, 1.0], [1.0])

    def test_single_point_raises(self):
        with self.assertRaises(SETError):
            trapezoidal_integration([0.0], [1.0])

    def test_empty_raises(self):
        with self.assertRaises(SETError):
            trapezoidal_integration([], [])

    def test_non_increasing_abscissae_raise(self):
        with self.assertRaises(SETError):
            trapezoidal_integration([0.0, 0.0], [1.0, 1.0])
        with self.assertRaises(SETError):
            trapezoidal_integration([1.0, 0.0], [1.0, 1.0])


class TestHeavyIonSetRate(unittest.TestCase):
    def test_rate_matches_hand_calculation(self):
        # 5 * 1e-3 * sigma(10) * 86400 = 9.5558061713e-03 events/device/day
        rate = heavy_ion_set_rate(LET_SPECTRUM, {"let_threshold": LTH,
                                                "sigma_sat": SIGMA_SAT,
                                                "width": WIDTH, "shape": SHAPE})
        self.assertAlmostEqual(rate, 9.55580617131531e-03, places=7)

    def test_rate_scales_with_seconds_per_day(self):
        params = {"let_threshold": LTH, "sigma_sat": SIGMA_SAT,
                  "width": WIDTH, "shape": SHAPE}
        daily = heavy_ion_set_rate(LET_SPECTRUM, params)
        per_second = heavy_ion_set_rate(LET_SPECTRUM, params, seconds_per_day=1.0)
        self.assertAlmostEqual(daily, per_second * SECONDS_PER_DAY, places=18)

    def test_zero_rate_when_spectrum_below_threshold(self):
        rate = heavy_ion_set_rate(
            [(0.0, 1.0), (4.0, 1.0)],
            {"let_threshold": LTH, "sigma_sat": SIGMA_SAT, "width": WIDTH,
             "shape": SHAPE},
        )
        self.assertEqual(rate, 0.0)

    def test_weibull_roll_on_is_below_flat_saturation_estimate(self):
        params = {"let_threshold": LTH, "sigma_sat": SIGMA_SAT,
                  "width": WIDTH, "shape": SHAPE}
        weibull_rate = heavy_ion_set_rate(LET_SPECTRUM, params)
        # A flat sigma_sat over the whole spectrum overpredicts the risk.
        flat_rate = trapezoidal_integration(
            [0.0, 10.0], [SIGMA_SAT * 1.0e-3, SIGMA_SAT * 1.0e-3]
        ) * SECONDS_PER_DAY
        self.assertLess(weibull_rate, flat_rate)
        self.assertAlmostEqual(flat_rate, 8.64e-02, places=12)

    def test_missing_weibull_parameter_raises(self):
        with self.assertRaises(SETError):
            heavy_ion_set_rate(LET_SPECTRUM, {"let_threshold": LTH,
                                             "sigma_sat": SIGMA_SAT,
                                             "width": WIDTH})

    def test_non_dict_weibull_raises(self):
        with self.assertRaises(SETError):
            heavy_ion_set_rate(LET_SPECTRUM, (LTH, SIGMA_SAT, WIDTH, SHAPE))

    def test_empty_spectrum_raises(self):
        with self.assertRaises(SETError):
            heavy_ion_set_rate([], {"let_threshold": LTH, "sigma_sat": SIGMA_SAT,
                                    "width": WIDTH, "shape": SHAPE})

    def test_negative_flux_raises(self):
        with self.assertRaises(SETError):
            heavy_ion_set_rate(
                [(0.0, 1.0e-3), (10.0, -1.0e-3)],
                {"let_threshold": LTH, "sigma_sat": SIGMA_SAT, "width": WIDTH,
                 "shape": SHAPE},
            )

    def test_non_increasing_let_raises(self):
        with self.assertRaises(SETError):
            heavy_ion_set_rate(
                [(10.0, 1.0e-3), (10.0, 1.0e-3)],
                {"let_threshold": LTH, "sigma_sat": SIGMA_SAT, "width": WIDTH,
                 "shape": SHAPE},
            )

    def test_zero_seconds_per_day_raises(self):
        with self.assertRaises(SETError):
            heavy_ion_set_rate(
                LET_SPECTRUM,
                {"let_threshold": LTH, "sigma_sat": SIGMA_SAT, "width": WIDTH,
                 "shape": SHAPE},
                seconds_per_day=0.0,
            )

    def test_dict_spectrum_points_accepted(self):
        params = {"let_threshold": LTH, "sigma_sat": SIGMA_SAT,
                  "width": WIDTH, "shape": SHAPE}
        rate = heavy_ion_set_rate(
            [{"let": 0.0, "flux": 1.0e-3}, {"let": 10.0, "flux": 1.0e-3}], params
        )
        self.assertAlmostEqual(rate, 9.55580617131531e-03, places=7)


class TestProtonSetRate(unittest.TestCase):
    def test_rate_matches_hand_calculation(self):
        # sigma steps to 1e-6 above 30 MeV: 100 * (0 + 1e-9) / 2 * 86400
        rate = proton_set_rate(PROTON_SPECTRUM, 30.0, 1.0e-6)
        self.assertAlmostEqual(rate, 4.32e-03, places=12)

    def test_zero_rate_when_spectrum_below_threshold(self):
        rate = proton_set_rate([(0.0, 1.0), (20.0, 1.0)], 30.0, 1.0e-6)
        self.assertEqual(rate, 0.0)

    def test_rate_scales_with_sigma_sat(self):
        low = proton_set_rate(PROTON_SPECTRUM, 30.0, 1.0e-6)
        high = proton_set_rate(PROTON_SPECTRUM, 30.0, 2.0e-6)
        self.assertAlmostEqual(high, 2.0 * low, places=15)

    def test_zero_threshold_raises(self):
        with self.assertRaises(SETError):
            proton_set_rate(PROTON_SPECTRUM, 0.0, 1.0e-6)

    def test_negative_flux_raises(self):
        with self.assertRaises(SETError):
            proton_set_rate([(0.0, 1.0), (100.0, -1.0)], 30.0, 1.0e-6)

    def test_empty_spectrum_raises(self):
        with self.assertRaises(SETError):
            proton_set_rate([], 30.0, 1.0e-6)


class TestNeutronSetRate(unittest.TestCase):
    def test_rate_formula(self):
        # R = 1e-6 cm²/device * 100 particles/(cm²·s) * 86400 s/day
        self.assertAlmostEqual(neutron_set_rate(1.0e-6, 1.0e2), 8.64, places=12)

    def test_zero_flux_gives_zero_rate(self):
        self.assertEqual(neutron_set_rate(1.0e-6, 0.0), 0.0)

    def test_seconds_per_day_scaling(self):
        self.assertAlmostEqual(neutron_set_rate(1.0e-6, 1.0e2, seconds_per_day=1.0),
                               1.0e-4, places=18)

    def test_zero_cross_section_raises(self):
        with self.assertRaises(SETError):
            neutron_set_rate(0.0, 1.0e2)

    def test_negative_flux_raises(self):
        with self.assertRaises(SETError):
            neutron_set_rate(1.0e-6, -1.0)

    def test_negative_seconds_per_day_raises(self):
        with self.assertRaises(SETError):
            neutron_set_rate(1.0e-6, 1.0e2, seconds_per_day=-1.0)


class TestTotalSetRate(unittest.TestCase):
    def test_sums_three_contributions(self):
        self.assertAlmostEqual(total_set_rate(1.0, 2.0, 3.0), 6.0)

    def test_zero_contributions(self):
        self.assertEqual(total_set_rate(0.0, 0.0, 0.0), 0.0)

    def test_negative_heavy_ion_raises(self):
        with self.assertRaises(SETError):
            total_set_rate(-1.0, 2.0, 3.0)

    def test_negative_proton_raises(self):
        with self.assertRaises(SETError):
            total_set_rate(1.0, -2.0, 3.0)

    def test_negative_neutron_raises(self):
        with self.assertRaises(SETError):
            total_set_rate(1.0, 2.0, -3.0)


class TestCheckSetBudget(unittest.TestCase):
    def test_within_budget_is_compliant(self):
        result = check_set_budget("U1", 5.0, 10.0)
        self.assertTrue(result["compliant"])
        self.assertIsNone(result["finding"])
        self.assertAlmostEqual(result["exceedance"], -5.0)

    def test_at_budget_is_compliant(self):
        result = check_set_budget("U1", 10.0, 10.0)
        self.assertTrue(result["compliant"])

    def test_over_budget_is_a_finding(self):
        result = check_set_budget("U2", 12.0, 10.0)
        self.assertFalse(result["compliant"])
        self.assertAlmostEqual(result["exceedance"], 2.0)
        self.assertEqual(result["finding"]["issue"], "set_rate_budget_exceeded")
        self.assertEqual(result["finding"]["device_id"], "U2")

    def test_absent_budget_is_a_requirement_capture_gap(self):
        result = check_set_budget("U3", 1.0, None)
        self.assertFalse(result["compliant"])
        self.assertIsNone(result["budget_rate"])
        self.assertIsNone(result["exceedance"])
        self.assertEqual(result["finding"]["issue"], "budget_not_captured")

    def test_non_positive_budget_raises(self):
        with self.assertRaises(SETError):
            check_set_budget("U4", 1.0, 0.0)

    def test_negative_total_rate_raises(self):
        with self.assertRaises(SETError):
            check_set_budget("U5", -1.0, 10.0)


class TestEvaluateDevice(unittest.TestCase):
    def test_full_evaluation_sums_three_families(self):
        result = evaluate_device(reference_device(), REFERENCE_ENVIRONMENT)
        self.assertAlmostEqual(
            result["total_rate"],
            result["heavy_ion_rate"] + result["proton_rate"] + result["neutron_rate"],
            places=15,
        )

    def test_family_rates_match_standalone_calls(self):
        result = evaluate_device(reference_device(), REFERENCE_ENVIRONMENT)
        self.assertAlmostEqual(result["heavy_ion_rate"],
                               heavy_ion_set_rate(LET_SPECTRUM, {
                                   "let_threshold": LTH, "sigma_sat": SIGMA_SAT,
                                   "width": WIDTH, "shape": SHAPE}), places=15)
        self.assertAlmostEqual(result["proton_rate"],
                               proton_set_rate(PROTON_SPECTRUM, 30.0, 1.0e-6), places=15)
        self.assertAlmostEqual(result["neutron_rate"],
                               neutron_set_rate(1.0e-6, 1.0e2), places=15)

    def test_generous_budget_is_compliant(self):
        result = evaluate_device(reference_device(budget=100.0), REFERENCE_ENVIRONMENT)
        self.assertTrue(result["compliant"])
        self.assertIsNone(result["finding"])

    def test_tight_budget_is_not_compliant(self):
        result = evaluate_device(reference_device(budget=1.0e-6),
                                 REFERENCE_ENVIRONMENT)
        self.assertFalse(result["compliant"])
        self.assertEqual(result["finding"]["issue"], "set_rate_budget_exceeded")

    def test_device_without_budget_is_a_capture_gap(self):
        spec = reference_device()
        del spec["set_budget"]
        result = evaluate_device(spec, REFERENCE_ENVIRONMENT)
        self.assertFalse(result["compliant"])
        self.assertEqual(result["finding"]["issue"], "budget_not_captured")

    def test_missing_heavy_ion_record_raises(self):
        spec = reference_device()
        del spec[HEAVY_ION]
        with self.assertRaises(SETError):
            evaluate_device(spec, REFERENCE_ENVIRONMENT)

    def test_missing_proton_record_raises(self):
        spec = reference_device()
        del spec[PROTON]
        with self.assertRaises(SETError):
            evaluate_device(spec, REFERENCE_ENVIRONMENT)

    def test_missing_neutron_record_raises(self):
        spec = reference_device()
        del spec[NEUTRON]
        with self.assertRaises(SETError):
            evaluate_device(spec, REFERENCE_ENVIRONMENT)

    def test_missing_shape_parameter_raises(self):
        spec = reference_device()
        del spec[HEAVY_ION]["shape"]
        with self.assertRaises(SETError):
            evaluate_device(spec, REFERENCE_ENVIRONMENT)

    def test_missing_sigma_n_raises(self):
        spec = reference_device()
        spec[NEUTRON] = {}
        with self.assertRaises(SETError):
            evaluate_device(spec, REFERENCE_ENVIRONMENT)

    def test_missing_energy_threshold_raises(self):
        spec = reference_device()
        spec[PROTON] = {"sigma_sat": 1.0e-6}
        with self.assertRaises(SETError):
            evaluate_device(spec, REFERENCE_ENVIRONMENT)

    def test_missing_environment_let_spectrum_raises(self):
        env = dict(REFERENCE_ENVIRONMENT)
        del env["let_spectrum"]
        with self.assertRaises(SETError):
            evaluate_device(reference_device(), env)

    def test_missing_environment_neutron_flux_raises(self):
        env = dict(REFERENCE_ENVIRONMENT)
        del env["neutron_flux"]
        with self.assertRaises(SETError):
            evaluate_device(reference_device(), env)

    def test_device_spec_not_mutated(self):
        spec = reference_device()
        keys_before = set(spec.keys())
        evaluate_device(spec, REFERENCE_ENVIRONMENT)
        self.assertEqual(set(spec.keys()), keys_before)


class TestEvaluateAll(unittest.TestCase):
    def test_order_preserved_and_findings_collected(self):
        no_budget = reference_device("C")
        del no_budget["set_budget"]
        devices = [
            reference_device("A", budget=100.0),
            reference_device("B", budget=1.0e-6),
            no_budget,
        ]
        results = evaluate_all(devices, REFERENCE_ENVIRONMENT)
        self.assertEqual([r["device_id"] for r in results], ["A", "B", "C"])
        findings = set_findings(results)
        self.assertEqual(len(findings), 2)
        self.assertEqual({f["device_id"] for f in findings}, {"B", "C"})

    def test_all_passing_gives_no_findings(self):
        devices = [reference_device("A", budget=100.0),
                   reference_device("B", budget=100.0)]
        self.assertEqual(set_findings(evaluate_all(devices, REFERENCE_ENVIRONMENT)), [])

    def test_empty_device_list(self):
        self.assertEqual(evaluate_all([], REFERENCE_ENVIRONMENT), [])

    def test_invalid_device_raises(self):
        devices = [reference_device("A", budget=100.0), {"device_id": "B"}]
        with self.assertRaises(SETError):
            evaluate_all(devices, REFERENCE_ENVIRONMENT)


if __name__ == "__main__":
    unittest.main()
