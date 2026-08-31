"""Gate 3 contract test for real_cycle_effects.py (stdlib unittest only).

Run directly from the repo root:
    python3 scripts/test_real_cycle_effects.py
No network, no third-party imports. Asserts the real (non-ideal)
Brayton cycle relations: component isentropic efficiencies, the real
thermal efficiency, the actual SFC, and the combustor pressure-loss
penalty, including the ideal-cycle recovery and the non-physical
input rejections.
"""

import unittest

import real_cycle_effects as rce

T1 = 288.15   # K, sea-level standard inlet
T3 = 1500.0   # K, turbine inlet temperature
PR = 20.0     # overall pressure ratio
GAMMA = 1.4   # air-standard ratio of specific heats
LHV = 43.2e6  # J/kg, kerosene-class lower heating value
ETA_C = 0.85  # compressor isentropic efficiency
ETA_T = 0.88  # turbine isentropic efficiency


class CompressorExitTemperatureTest(unittest.TestCase):
    def test_eta_1_recovers_ideal_exit(self):
        ideal = T1 * PR ** ((GAMMA - 1.0) / GAMMA)
        self.assertAlmostEqual(
            rce.compressor_exit_temperature(T1, PR, GAMMA, 1.0),
            ideal, places=6)

    def test_matches_task_formula(self):
        t2 = rce.compressor_exit_temperature(T1, PR, GAMMA, ETA_C)
        expected = T1 * (1.0 + (PR ** ((GAMMA - 1.0) / GAMMA) - 1.0) / ETA_C)
        self.assertAlmostEqual(t2, expected, places=6)

    def test_real_exit_hotter_than_ideal(self):
        real = rce.compressor_exit_temperature(T1, PR, GAMMA, ETA_C)
        ideal = rce.compressor_exit_temperature(T1, PR, GAMMA, 1.0)
        self.assertGreater(real, ideal)

    def test_units_are_kelvin(self):
        t2 = rce.compressor_exit_temperature(T1, PR, GAMMA, ETA_C)
        self.assertGreater(t2, 500.0)   # ~747 K at PR 20
        self.assertLess(t2, 1000.0)

    def test_rejects_eta_c_above_1(self):
        with self.assertRaises(ValueError):
            rce.compressor_exit_temperature(T1, PR, GAMMA, 1.01)

    def test_rejects_nonpositive_eta_c(self):
        with self.assertRaises(ValueError):
            rce.compressor_exit_temperature(T1, PR, GAMMA, 0.0)
        with self.assertRaises(ValueError):
            rce.compressor_exit_temperature(T1, PR, GAMMA, -0.5)

    def test_rejects_bad_pr_and_t1(self):
        with self.assertRaises(ValueError):
            rce.compressor_exit_temperature(T1, 1.0, GAMMA, ETA_C)
        with self.assertRaises(ValueError):
            rce.compressor_exit_temperature(0.0, PR, GAMMA, ETA_C)


class TurbineExitTemperatureTest(unittest.TestCase):
    def test_eta_1_recovers_ideal_exit(self):
        ideal = T3 / PR ** ((GAMMA - 1.0) / GAMMA)
        self.assertAlmostEqual(
            rce.turbine_exit_temperature(T3, PR, GAMMA, 1.0),
            ideal, places=6)

    def test_matches_task_formula(self):
        t4 = rce.turbine_exit_temperature(T3, PR, GAMMA, ETA_T)
        t4s = T3 / PR ** ((GAMMA - 1.0) / GAMMA)
        expected = T3 - ETA_T * (T3 - t4s)
        self.assertAlmostEqual(t4, expected, places=6)

    def test_real_exit_hotter_than_ideal(self):
        real = rce.turbine_exit_temperature(T3, PR, GAMMA, ETA_T)
        ideal = rce.turbine_exit_temperature(T3, PR, GAMMA, 1.0)
        self.assertGreater(real, ideal)

    def test_rejects_eta_t_above_1(self):
        with self.assertRaises(ValueError):
            rce.turbine_exit_temperature(T3, PR, GAMMA, 1.01)

    def test_rejects_bad_inputs(self):
        with self.assertRaises(ValueError):
            rce.turbine_exit_temperature(T3, PR, GAMMA, 0.0)
        with self.assertRaises(ValueError):
            rce.turbine_exit_temperature(0.0, PR, GAMMA, ETA_T)


class RealThermalEfficiencyTest(unittest.TestCase):
    def test_ideal_cycle_recovery(self):
        t2 = rce.compressor_exit_temperature(T1, PR, GAMMA, 1.0)
        t4 = rce.turbine_exit_temperature(T3, PR, GAMMA, 1.0)
        eta = rce.real_thermal_efficiency(T1, t2, T3, t4)
        self.assertAlmostEqual(
            eta, 1.0 - PR ** ((1.0 - GAMMA) / GAMMA), places=6)

    def test_real_efficiency_below_ideal(self):
        t2 = rce.compressor_exit_temperature(T1, PR, GAMMA, 1.0)
        t4 = rce.turbine_exit_temperature(T3, PR, GAMMA, 1.0)
        eta_ideal = rce.real_thermal_efficiency(T1, t2, T3, t4)
        t2r = rce.compressor_exit_temperature(T1, PR, GAMMA, ETA_C)
        t4r = rce.turbine_exit_temperature(T3, PR, GAMMA, ETA_T)
        eta_real = rce.real_thermal_efficiency(T1, t2r, T3, t4r)
        self.assertLess(eta_real, eta_ideal)

    def test_real_efficiency_physical_band(self):
        t2 = rce.compressor_exit_temperature(T1, PR, GAMMA, ETA_C)
        t4 = rce.turbine_exit_temperature(T3, PR, GAMMA, ETA_T)
        eta = rce.real_thermal_efficiency(T1, t2, T3, t4)
        self.assertGreater(eta, 0.0)
        self.assertLess(eta, 1.0)
        self.assertGreater(eta, 0.30)   # realistic band ~0.40

    def test_rejects_unphysical_state_order(self):
        with self.assertRaises(ValueError):
            rce.real_thermal_efficiency(T1, T3 + 100.0, T3, 800.0)
        with self.assertRaises(ValueError):
            rce.real_thermal_efficiency(T1, 400.0, 1500.0, T1)
        with self.assertRaises(ValueError):
            rce.real_thermal_efficiency(T1, 400.0, 1500.0, 1600.0)


class SfcTest(unittest.TestCase):
    def test_exact_3600_formula(self):
        self.assertAlmostEqual(
            rce.sfc_from_efficiency(0.4, LHV), 3600.0 / (0.4 * LHV), places=12)

    def test_sfc_decreases_with_efficiency(self):
        self.assertLess(
            rce.sfc_from_efficiency(0.5, LHV),
            rce.sfc_from_efficiency(0.4, LHV))

    def test_sfc_positive(self):
        self.assertGreater(rce.sfc_from_efficiency(0.4, LHV), 0.0)

    def test_thrust_sfc_formula_and_band(self):
        sfc_t = rce.sfc_thrust(0.4, LHV, 600.0)
        self.assertAlmostEqual(sfc_t, 1000.0 * 600.0 / (0.4 * LHV), places=12)
        # Realistic turbojet thrust SFC band, kg/(kN*s): ~0.014 to 0.05
        self.assertGreater(sfc_t, 0.01)
        self.assertLess(sfc_t, 0.05)

    def test_sfc_rejects_bad_inputs(self):
        with self.assertRaises(ValueError):
            rce.sfc_from_efficiency(0.0, LHV)
        with self.assertRaises(ValueError):
            rce.sfc_from_efficiency(1.1, LHV)
        with self.assertRaises(ValueError):
            rce.sfc_from_efficiency(0.4, 0.0)
        with self.assertRaises(ValueError):
            rce.sfc_thrust(0.4, LHV, 0.0)


class PressureLossTest(unittest.TestCase):
    def test_loss_reduces_effective_pr(self):
        pr_eff = rce.pressure_loss_penalty(PR, 0.05)
        self.assertAlmostEqual(pr_eff, 19.0, places=6)
        self.assertLess(pr_eff, PR)

    def test_zero_loss_is_identity(self):
        self.assertAlmostEqual(rce.pressure_loss_penalty(PR, 0.0), PR, places=6)

    def test_loss_rejects_bad_inputs(self):
        with self.assertRaises(ValueError):
            rce.pressure_loss_penalty(PR, 1.0)
        with self.assertRaises(ValueError):
            rce.pressure_loss_penalty(PR, -0.1)
        with self.assertRaises(ValueError):
            rce.pressure_loss_penalty(1.0, 0.05)

    def test_loss_reduces_real_efficiency(self):
        eta_clean = rce.cycle_efficiency_with_losses(
            T1, T3, PR, GAMMA, ETA_C, ETA_T, 0.0)
        eta_lossy = rce.cycle_efficiency_with_losses(
            T1, T3, PR, GAMMA, ETA_C, ETA_T, 0.05)
        self.assertGreater(eta_clean, eta_lossy)


class EfficiencySensitivityTest(unittest.TestCase):
    def test_component_efficiency_derivatives_positive(self):
        sens = rce.efficiency_sensitivity()
        self.assertGreater(sens["d_eta_d_eta_c"], 0.0)
        self.assertGreater(sens["d_eta_d_eta_t"], 0.0)
        self.assertLess(sens["d_eta_d_loss"], 0.0)

    def test_base_efficiency_reference_value(self):
        sens = rce.efficiency_sensitivity()
        self.assertAlmostEqual(sens["eta_base"], 0.399, places=2)

    def test_ideal_limit_flatness(self):
        # Moving eta_c toward 1.0 from below always improves efficiency,
        # and the gain vanishes as the cycle approaches ideal.
        eta_99 = rce.cycle_efficiency_with_losses(
            T1, T3, PR, GAMMA, 0.99, ETA_T, 0.0)
        eta_100 = rce.cycle_efficiency_with_losses(
            T1, T3, PR, GAMMA, 1.0, ETA_T, 0.0)
        self.assertGreater(eta_100, eta_99)


if __name__ == "__main__":
    unittest.main()
