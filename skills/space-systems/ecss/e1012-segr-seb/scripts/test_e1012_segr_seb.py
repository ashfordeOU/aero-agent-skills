"""
Gate-3 contract tests for e1012-segr-seb.

Run: python3 test_e1012_segr_seb.py
Must print OK.  stdlib unittest only.  Offline, deterministic.
"""

import math
import unittest

from e1012_segr_seb_logic import (
    validate_weibull_params,
    weibull_cross_section,
    check_bias_margin,
    compute_rate_heavy_ion,
    categorize_device,
    categorize_orbit_environment,
    scale_spectrum,
    margin_to_requirement,
    assess_seb,
    assess_segr,
)


class TestValidateWeibullParams(unittest.TestCase):
    def test_valid_params_no_exception(self):
        validate_weibull_params(1e-4, 10.0, 5.0, 2.0)

    def test_zero_sigma_sat_raises(self):
        with self.assertRaises(ValueError):
            validate_weibull_params(0.0, 10.0, 5.0, 2.0)

    def test_negative_sigma_sat_raises(self):
        with self.assertRaises(ValueError):
            validate_weibull_params(-1e-4, 10.0, 5.0, 2.0)

    def test_negative_let_th_raises(self):
        with self.assertRaises(ValueError):
            validate_weibull_params(1e-4, -1.0, 5.0, 2.0)

    def test_zero_w_raises(self):
        with self.assertRaises(ValueError):
            validate_weibull_params(1e-4, 10.0, 0.0, 2.0)

    def test_zero_s_raises(self):
        with self.assertRaises(ValueError):
            validate_weibull_params(1e-4, 10.0, 5.0, 0.0)

    def test_zero_let_th_is_valid(self):
        validate_weibull_params(1e-4, 0.0, 5.0, 2.0)


class TestWeibullCrossSection(unittest.TestCase):
    def _params(self):
        return {"sigma_sat": 1e-4, "let_th": 10.0, "w": 5.0, "s": 2.0}

    def test_below_threshold_returns_zero(self):
        self.assertEqual(weibull_cross_section(5.0, **self._params()), 0.0)

    def test_at_threshold_returns_zero(self):
        self.assertEqual(weibull_cross_section(10.0, **self._params()), 0.0)

    def test_above_threshold_positive(self):
        val = weibull_cross_section(20.0, **self._params())
        self.assertGreater(val, 0.0)

    def test_approaches_sigma_sat_at_high_let(self):
        val = weibull_cross_section(1000.0, **self._params())
        self.assertAlmostEqual(val, 1e-4, places=10)

    def test_monotonically_increasing_above_threshold(self):
        p = self._params()
        v1 = weibull_cross_section(15.0, **p)
        v2 = weibull_cross_section(20.0, **p)
        v3 = weibull_cross_section(30.0, **p)
        self.assertLess(v1, v2)
        self.assertLess(v2, v3)

    def test_invalid_params_propagated(self):
        with self.assertRaises(ValueError):
            weibull_cross_section(20.0, sigma_sat=-1.0, let_th=10.0, w=5.0, s=2.0)


class TestCheckBiasMargin(unittest.TestCase):
    def test_well_below_threshold_is_safe(self):
        result = check_bias_margin(20.0, 40.0)
        self.assertFalse(result["above_threshold"])
        self.assertAlmostEqual(result["margin_fraction"], 0.5)

    def test_at_threshold_is_above(self):
        result = check_bias_margin(40.0, 40.0)
        self.assertTrue(result["above_threshold"])
        self.assertAlmostEqual(result["margin_fraction"], 0.0)

    def test_above_threshold_negative_margin(self):
        result = check_bias_margin(50.0, 40.0)
        self.assertTrue(result["above_threshold"])
        self.assertLess(result["margin_fraction"], 0.0)

    def test_zero_threshold_raises(self):
        with self.assertRaises(ValueError):
            check_bias_margin(10.0, 0.0)

    def test_negative_threshold_raises(self):
        with self.assertRaises(ValueError):
            check_bias_margin(10.0, -5.0)


class TestComputeRateHeavyIon(unittest.TestCase):
    def _base_spectrum(self):
        return [(5.0, 1e3), (15.0, 1e3), (30.0, 1e2)]

    def test_all_below_threshold_gives_zero(self):
        spectrum = [(1.0, 1e3), (5.0, 1e3)]
        rate = compute_rate_heavy_ion(spectrum, 1e-4, 10.0, 5.0, 2.0)
        self.assertAlmostEqual(rate, 0.0)

    def test_rate_positive_above_threshold(self):
        rate = compute_rate_heavy_ion(self._base_spectrum(), 1e-4, 10.0, 5.0, 2.0)
        self.assertGreater(rate, 0.0)

    def test_higher_flux_gives_higher_rate(self):
        lo = compute_rate_heavy_ion([(10.0, 1e1), (30.0, 1e1)], 1e-4, 8.0, 5.0, 2.0)
        hi = compute_rate_heavy_ion([(10.0, 1e4), (30.0, 1e4)], 1e-4, 8.0, 5.0, 2.0)
        self.assertGreater(hi, lo)

    def test_single_point_raises(self):
        with self.assertRaises(ValueError):
            compute_rate_heavy_ion([(15.0, 1e3)], 1e-4, 10.0, 5.0, 2.0)

    def test_negative_let_raises(self):
        with self.assertRaises(ValueError):
            compute_rate_heavy_ion([(-1.0, 1e3), (20.0, 1e3)], 1e-4, 10.0, 5.0, 2.0)

    def test_negative_flux_raises(self):
        with self.assertRaises(ValueError):
            compute_rate_heavy_ion([(10.0, -1.0), (20.0, 1e3)], 1e-4, 10.0, 5.0, 2.0)

    def test_rate_scales_linearly_with_sigma_sat(self):
        sp = [(15.0, 1e3), (30.0, 1e3)]
        r1 = compute_rate_heavy_ion(sp, 1e-4, 10.0, 5.0, 2.0)
        r2 = compute_rate_heavy_ion(sp, 2e-4, 10.0, 5.0, 2.0)
        self.assertAlmostEqual(r2 / r1, 2.0, places=10)


class TestCategorizeDevice(unittest.TestCase):
    def test_mosfet_has_segr_and_seb(self):
        info = categorize_device("power_mosfet")
        self.assertIn("SEGR", info["applicable_effects"])
        self.assertIn("SEB", info["applicable_effects"])

    def test_bipolar_has_seb_only(self):
        info = categorize_device("bipolar_transistor")
        self.assertIn("SEB", info["applicable_effects"])
        self.assertNotIn("SEGR", info["applicable_effects"])

    def test_unknown_device_raises(self):
        with self.assertRaises(ValueError):
            categorize_device("resistor")

    def test_returns_device_type(self):
        info = categorize_device("power_mosfet")
        self.assertEqual(info["device_type"], "power_mosfet")


class TestCategorizeOrbitEnvironment(unittest.TestCase):
    def test_all_known_orbits_return_dict(self):
        for orbit in ["geo", "meo", "leo_polar", "leo_equatorial", "interplanetary"]:
            info = categorize_orbit_environment(orbit)
            self.assertIn("flux_scale", info)
            self.assertIn("description", info)
            self.assertIsInstance(info["flux_scale"], float)

    def test_meo_flux_scale_greater_than_geo(self):
        meo = categorize_orbit_environment("meo")["flux_scale"]
        geo = categorize_orbit_environment("geo")["flux_scale"]
        self.assertGreater(meo, geo)

    def test_leo_equatorial_lowest_scale(self):
        eq = categorize_orbit_environment("leo_equatorial")["flux_scale"]
        for orbit in ["geo", "meo", "leo_polar", "interplanetary"]:
            self.assertLess(eq, categorize_orbit_environment(orbit)["flux_scale"])

    def test_unknown_orbit_raises(self):
        with self.assertRaises(ValueError):
            categorize_orbit_environment("deep_space_unknown")


class TestScaleSpectrum(unittest.TestCase):
    def test_scale_doubles_flux(self):
        sp = [(10.0, 1.0), (20.0, 2.0)]
        scaled = scale_spectrum(sp, 2.0)
        self.assertAlmostEqual(scaled[0][1], 2.0)
        self.assertAlmostEqual(scaled[1][1], 4.0)

    def test_let_values_unchanged(self):
        sp = [(15.0, 3.0), (25.0, 7.0)]
        scaled = scale_spectrum(sp, 5.0)
        self.assertEqual(scaled[0][0], 15.0)
        self.assertEqual(scaled[1][0], 25.0)

    def test_zero_scale_zeroes_flux(self):
        sp = [(10.0, 5.0), (20.0, 3.0)]
        scaled = scale_spectrum(sp, 0.0)
        for _, flux in scaled:
            self.assertEqual(flux, 0.0)

    def test_negative_scale_raises(self):
        with self.assertRaises(ValueError):
            scale_spectrum([(10.0, 1.0)], -1.0)

    def test_original_list_not_mutated(self):
        sp = [(10.0, 1.0)]
        _ = scale_spectrum(sp, 3.0)
        self.assertEqual(sp[0][1], 1.0)


class TestMarginToRequirement(unittest.TestCase):
    def test_passing_rate_positive_margin(self):
        margin = margin_to_requirement(1e-9, 1e-7)
        self.assertGreater(margin, 0.0)

    def test_failing_rate_negative_margin(self):
        margin = margin_to_requirement(1e-5, 1e-7)
        self.assertLess(margin, 0.0)

    def test_zero_rate_returns_inf(self):
        self.assertEqual(margin_to_requirement(0.0, 1e-7), float("inf"))

    def test_rate_equals_requirement_zero_margin(self):
        margin = margin_to_requirement(1e-7, 1e-7)
        self.assertAlmostEqual(margin, 0.0, places=10)

    def test_zero_requirement_raises(self):
        with self.assertRaises(ValueError):
            margin_to_requirement(1e-9, 0.0)

    def test_negative_rate_raises(self):
        with self.assertRaises(ValueError):
            margin_to_requirement(-1.0, 1e-7)

    def test_known_value(self):
        margin = margin_to_requirement(1e-9, 1e-7)
        self.assertAlmostEqual(margin, 2.0, places=10)


class TestAssessSEB(unittest.TestCase):
    _SP = [(5.0, 1e3), (20.0, 1e3), (60.0, 1e2)]

    def test_returns_seb_effect(self):
        result = assess_seb("power_mosfet", 20.0, 40.0, self._SP, 1e-6, 5.0, 8.0, 2.0)
        self.assertEqual(result["effect"], "SEB")

    def test_bipolar_allowed_for_seb(self):
        result = assess_seb("bipolar_transistor", 20.0, 40.0, self._SP, 1e-6, 5.0, 8.0, 2.0)
        self.assertEqual(result["device_type"], "bipolar_transistor")

    def test_unknown_device_raises(self):
        with self.assertRaises(ValueError):
            assess_seb("diode", 20.0, 40.0, self._SP, 1e-6, 5.0, 8.0, 2.0)

    def test_rate_day_is_86400x_rate_s(self):
        result = assess_seb("power_mosfet", 20.0, 40.0, self._SP, 1e-6, 5.0, 8.0, 2.0)
        self.assertAlmostEqual(
            result["rate_per_device_day"],
            result["rate_per_device_s"] * 86400.0,
            places=6,
        )

    def test_passes_with_generous_requirement(self):
        result = assess_seb(
            "power_mosfet", 20.0, 40.0, self._SP, 1e-6, 5.0, 8.0, 2.0,
            rate_requirement=1.0, design_margin=1.0,
        )
        self.assertTrue(result["passes_rate_req"])

    def test_fails_with_tight_requirement(self):
        result = assess_seb(
            "power_mosfet", 20.0, 40.0, self._SP, 1e-2, 5.0, 8.0, 2.0,
            rate_requirement=1e-20, design_margin=1.0,
        )
        self.assertFalse(result["passes_rate_req"])

    def test_effective_requirement_includes_margin(self):
        result = assess_seb(
            "power_mosfet", 20.0, 40.0, self._SP, 1e-6, 5.0, 8.0, 2.0,
            rate_requirement=1e-6, design_margin=10.0,
        )
        self.assertAlmostEqual(result["effective_requirement"], 1e-7, places=20)

    def test_bias_check_populated(self):
        result = assess_seb("power_mosfet", 20.0, 40.0, self._SP, 1e-6, 5.0, 8.0, 2.0)
        self.assertIn("above_threshold", result["bias_check"])
        self.assertFalse(result["bias_check"]["above_threshold"])


class TestAssessSEGR(unittest.TestCase):
    _SP = [(5.0, 1e3), (20.0, 1e3), (60.0, 1e2)]

    def test_returns_segr_effect(self):
        result = assess_segr("power_mosfet", 5.0, 20.0, self._SP, 1e-5, 8.0, 6.0, 2.0)
        self.assertEqual(result["effect"], "SEGR")

    def test_bipolar_raises_for_segr(self):
        with self.assertRaises(ValueError):
            assess_segr("bipolar_transistor", 5.0, 20.0, self._SP, 1e-5, 8.0, 6.0, 2.0)

    def test_log10_margin_positive_when_passing(self):
        result = assess_segr(
            "power_mosfet", 5.0, 20.0, self._SP, 1e-6, 8.0, 6.0, 2.0,
            rate_requirement=1.0, design_margin=1.0,
        )
        self.assertGreater(result["log10_margin"], 0.0)

    def test_device_type_preserved(self):
        result = assess_segr("power_mosfet", 5.0, 20.0, self._SP, 1e-5, 8.0, 6.0, 2.0)
        self.assertEqual(result["device_type"], "power_mosfet")

    def test_weibull_params_in_result(self):
        result = assess_segr("power_mosfet", 5.0, 20.0, self._SP, 1e-5, 8.0, 6.0, 2.0)
        wp = result["weibull_params"]
        self.assertAlmostEqual(wp["sigma_sat"], 1e-5)
        self.assertAlmostEqual(wp["let_th"], 8.0)


if __name__ == "__main__":
    unittest.main()
