#!/usr/bin/env python3
"""Gate 3 contract test: infrared thermography inspection math.

Exercises scripts/thermography_logic.py (stdlib unittest, offline).
Contract: docs/harness-contract.md gate 3 - surface temperature rise
of a semi-infinite solid under a constant heat flux
(delta_T = (2 * q / k) * sqrt(alpha * t / pi), alpha = k / (rho * c)),
heating pulse energy density as the inverse, absolute and normalized
thermal contrast, characteristic diffusion time t = z^2 / alpha,
time of maximum contrast estimate t_max ~ z^2 / (2 * alpha), and a
detectability verdict against a noise floor (snr >= 2 detectable).

All expected values are hand-computed (see each docstring) and were
checked at authoring time.
"""

import os
import sys
import unittest

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import thermography_logic as tl  # noqa: E402

ALUMINUM = {"k": 167.0, "rho": 2700.0, "c": 900.0}
CFRP = {"k": 0.6, "rho": 1600.0, "c": 1000.0}


class SurfaceTemperatureRiseTest(unittest.TestCase):
    def test_aluminum_100_kw_m2_0_1_s(self):
        # alpha = 167 / (2700 * 900) = 6.8724e-5 m^2/s;
        # delta_T = (2 * 1e5 / 167) * sqrt(6.8724e-5 * 0.1 / pi)
        #         = 1197.6 * 1.4790e-3 = 1.7714 K.
        self.assertAlmostEqual(
            tl.surface_temperature_rise(1e5, 0.1, ALUMINUM), 1.7714, places=3
        )

    def test_cfrp_20_kw_m2_1_s(self):
        # alpha = 0.6 / (1600 * 1000) = 3.75e-7 m^2/s;
        # delta_T = (2 * 2e4 / 0.6) * sqrt(3.75e-7 / pi)
        #         = 66666.7 * 3.4549e-4 = 23.033 K.
        self.assertAlmostEqual(
            tl.surface_temperature_rise(2e4, 1.0, CFRP), 23.033, places=2
        )

    def test_rise_grows_with_sqrt_time(self):
        # Doubling the time raises the rise by sqrt(2) = 1.4142.
        t1 = tl.surface_temperature_rise(1e5, 0.1, ALUMINUM)
        t2 = tl.surface_temperature_rise(1e5, 0.2, ALUMINUM)
        self.assertAlmostEqual(t2 / t1, 2.0 ** 0.5, places=4)

    def test_zero_time_is_zero_rise(self):
        self.assertEqual(tl.surface_temperature_rise(1e5, 0.0, ALUMINUM), 0.0)

    def test_non_positive_flux_raises(self):
        with self.assertRaises(ValueError):
            tl.surface_temperature_rise(0.0, 0.1, ALUMINUM)
        with self.assertRaises(ValueError):
            tl.surface_temperature_rise(-1e5, 0.1, ALUMINUM)

    def test_negative_time_raises(self):
        with self.assertRaises(ValueError):
            tl.surface_temperature_rise(1e5, -0.1, ALUMINUM)

    def test_non_finite_flux_raises(self):
        with self.assertRaises(ValueError):
            tl.surface_temperature_rise(float("nan"), 0.1, ALUMINUM)

    def test_invalid_properties_raise(self):
        with self.assertRaises(ValueError):
            tl.surface_temperature_rise(1e5, 0.1, {"k": 167.0, "rho": 2700.0})
        with self.assertRaises(ValueError):
            tl.surface_temperature_rise(1e5, 0.1, {"k": 0.0, "rho": 2700.0, "c": 900.0})
        with self.assertRaises(ValueError):
            tl.surface_temperature_rise(1e5, 0.1, {"k": 167.0, "rho": -1.0, "c": 900.0})
        with self.assertRaises(ValueError):
            tl.surface_temperature_rise(1e5, 0.1, {"k": 167.0, "rho": 2700.0, "c": float("nan")})


class HeatingPulseEnergyDensityTest(unittest.TestCase):
    def test_cfrp_23_k_rise_needs_20_kw_m2(self):
        # q = 23.033 * 0.6 * sqrt(pi / 3.75e-7) / 2
        #   = 13.820 * 1447.2 = 20000 W/m^2.
        self.assertAlmostEqual(
            tl.heating_pulse_energy_density(23.033, 1.0, CFRP), 20000.0, delta=5.0
        )

    def test_round_trip_with_surface_temperature_rise(self):
        # Inverting the forward solution returns the original flux.
        q = 2e4
        rise = tl.surface_temperature_rise(q, 1.0, CFRP)
        self.assertAlmostEqual(
            tl.heating_pulse_energy_density(rise, 1.0, CFRP), q, delta=1.0
        )

    def test_zero_target_rise_is_zero_energy(self):
        self.assertEqual(tl.heating_pulse_energy_density(0.0, 1.0, CFRP), 0.0)

    def test_negative_target_rise_raises(self):
        with self.assertRaises(ValueError):
            tl.heating_pulse_energy_density(-1.0, 1.0, CFRP)

    def test_non_positive_time_raises(self):
        with self.assertRaises(ValueError):
            tl.heating_pulse_energy_density(23.0, 0.0, CFRP)
        with self.assertRaises(ValueError):
            tl.heating_pulse_energy_density(23.0, -1.0, CFRP)

    def test_invalid_properties_raise(self):
        with self.assertRaises(ValueError):
            tl.heating_pulse_energy_density(23.0, 1.0, {"k": 0.6, "rho": 1600.0})


class ThermalContrastTest(unittest.TestCase):
    def test_hotter_defect_is_positive_contrast(self):
        # 2.2 K defect region minus 1.5 K sound region = 0.7 K.
        self.assertAlmostEqual(tl.thermal_contrast(1.5, 2.2), 0.7, places=9)

    def test_colder_defect_is_negative_contrast(self):
        self.assertAlmostEqual(tl.thermal_contrast(2.2, 1.5), -0.7, places=9)

    def test_equal_temperatures_zero_contrast(self):
        self.assertEqual(tl.thermal_contrast(1.5, 1.5), 0.0)

    def test_non_finite_raises(self):
        with self.assertRaises(ValueError):
            tl.thermal_contrast(float("nan"), 2.2)
        with self.assertRaises(ValueError):
            tl.thermal_contrast(1.5, float("inf"))


class NormalizedThermalContrastTest(unittest.TestCase):
    def test_normalized_contrast(self):
        # (2.2 - 1.5) / 1.5 = 0.7 / 1.5 = 0.4667.
        self.assertAlmostEqual(
            tl.normalized_thermal_contrast(1.5, 2.2), 0.4667, places=3
        )

    def test_non_positive_sound_raises(self):
        with self.assertRaises(ValueError):
            tl.normalized_thermal_contrast(0.0, 2.2)
        with self.assertRaises(ValueError):
            tl.normalized_thermal_contrast(-1.5, 2.2)

    def test_non_finite_raises(self):
        with self.assertRaises(ValueError):
            tl.normalized_thermal_contrast(1.5, float("nan"))


class CharacteristicDiffusionTimeTest(unittest.TestCase):
    def test_cfrp_2_mm_depth(self):
        # (2e-3)^2 / 3.75e-7 = 4e-6 / 3.75e-7 = 10.667 s.
        self.assertAlmostEqual(
            tl.characteristic_diffusion_time(2e-3, 3.75e-7), 10.667, places=2
        )

    def test_aluminum_1_mm_depth(self):
        # (1e-3)^2 / 6.8724e-5 = 1e-6 / 6.8724e-5 = 1.4551e-2 s.
        self.assertAlmostEqual(
            tl.characteristic_diffusion_time(1e-3, 6.8724e-5), 1.4551e-2, places=5
        )

    def test_non_positive_inputs_raise(self):
        with self.assertRaises(ValueError):
            tl.characteristic_diffusion_time(0.0, 3.75e-7)
        with self.assertRaises(ValueError):
            tl.characteristic_diffusion_time(-2e-3, 3.75e-7)
        with self.assertRaises(ValueError):
            tl.characteristic_diffusion_time(2e-3, 0.0)
        with self.assertRaises(ValueError):
            tl.characteristic_diffusion_time(2e-3, -3.75e-7)


class TimeOfMaxContrastTest(unittest.TestCase):
    def test_cfrp_2_mm_depth_peak_about_5_33_s(self):
        # t_max ~ z^2 / (2 * alpha) = 4e-6 / (2 * 3.75e-7) = 5.333 s.
        self.assertAlmostEqual(
            tl.time_of_max_contrast(2e-3, 3.75e-7), 5.333, places=2
        )

    def test_aluminum_1_mm_depth_peak_about_7_3_ms(self):
        # t_max = 1e-6 / (2 * 6.8724e-5) = 7.2755e-3 s.
        self.assertAlmostEqual(
            tl.time_of_max_contrast(1e-3, 6.8724e-5), 7.2755e-3, places=5
        )

    def test_deeper_defect_peaks_later(self):
        deep = tl.time_of_max_contrast(4e-3, 3.75e-7)
        shallow = tl.time_of_max_contrast(2e-3, 3.75e-7)
        self.assertGreater(deep, shallow)

    def test_non_positive_depth_raises(self):
        with self.assertRaises(ValueError):
            tl.time_of_max_contrast(0.0, 3.75e-7)

    def test_non_positive_diffusivity_raises(self):
        with self.assertRaises(ValueError):
            tl.time_of_max_contrast(2e-3, 0.0)


class DetectabilityVerdictTest(unittest.TestCase):
    def test_contrast_above_2x_noise_is_detectable(self):
        # snr = 0.5 / 0.1 = 5.0 >= 2.0.
        v = tl.detectability_verdict(0.5, 0.1)
        self.assertTrue(v["detectable"])
        self.assertEqual(v["verdict"], "DETECTABLE")
        self.assertAlmostEqual(v["snr"], 5.0, places=9)

    def test_contrast_below_2x_noise_is_not_detectable(self):
        # snr = 0.15 / 0.1 = 1.5 < 2.0.
        v = tl.detectability_verdict(0.15, 0.1)
        self.assertFalse(v["detectable"])
        self.assertEqual(v["verdict"], "NOT DETECTABLE")

    def test_min_snr_1_0_flags_marginal_contrast_detectable(self):
        # snr = 1.5 >= 1.0 with the lowered threshold.
        v = tl.detectability_verdict(0.15, 0.1, min_snr=1.0)
        self.assertTrue(v["detectable"])

    def test_negative_contrast_is_never_detectable(self):
        v = tl.detectability_verdict(-0.2, 0.1)
        self.assertFalse(v["detectable"])

    def test_zero_contrast_is_not_detectable(self):
        self.assertFalse(tl.detectability_verdict(0.0, 0.1)["detectable"])

    def test_non_positive_noise_floor_raises(self):
        with self.assertRaises(ValueError):
            tl.detectability_verdict(0.5, 0.0)
        with self.assertRaises(ValueError):
            tl.detectability_verdict(0.5, -0.1)

    def test_non_positive_min_snr_raises(self):
        with self.assertRaises(ValueError):
            tl.detectability_verdict(0.5, 0.1, min_snr=0.0)
        with self.assertRaises(ValueError):
            tl.detectability_verdict(0.5, 0.1, min_snr=-1.0)

    def test_non_finite_contrast_raises(self):
        with self.assertRaises(ValueError):
            tl.detectability_verdict(float("nan"), 0.1)


if __name__ == "__main__":
    unittest.main()
