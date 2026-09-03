"""Contract test for ice-protection-sizing (vehicle-design/sizing).

Deterministic, offline, stdlib unittest. Run with:
    python3 test_ice_protection_sizing.py
from this directory, or
    python3 skills/vehicle-design/sizing/ice-protection-sizing/scripts/test_ice_protection_sizing.py
from the repository root. Exits 0 when all tests pass.

Covers the worked example (wing leading edge protected band, M = 0.78 at
T = 218 K, LWC 0.44 g/m3, MVD 20 micron), the correlation trends, the
freezing fraction limits, the round-trip identity of the running-wet
surface temperature, and ValueError rejection of non-physical inputs.
"""

import os
import sys
import unittest

_HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, _HERE)

import ice_protection_sizing_logic as m

# Worked example inputs (transport wing leading edge protected band).
CHORD = 0.45          # m protected band chord
SPAN = 12.0           # m protected segment span
BAND_FRACTION = 0.08
MACH = 0.78
T_INF = 218.0         # K
V = 235.0             # m/s
LWC = 0.44e-3         # kg/m3
MVD = 20.0            # micron
RHO = 0.365           # kg/m3 ISA density near the flight altitude

# Module-real worked-example outputs (from the logic module itself).
EXPECT_T_TOT = 244.5262
EXPECT_T_KIN = 26.5262
EXPECT_ETA = 0.815959
EXPECT_M_WDOT = 0.037967
EXPECT_H_C = 169.04553
EXPECT_Q_CONV = 9322.86
EXPECT_Q_EVAP = 1318811.81
EXPECT_Q_REQ_EVAP = 1521160.66
EXPECT_P_EVAP = 1314282.81
EXPECT_Q_RW = 4838.72
EXPECT_P_RW = 4180.65
EXPECT_P_DEICE = 8493.12
EXPECT_AREA = 0.864
EXPECT_BLEED_RW = 0.017930
EXPECT_BLEED_EVAP = 5.636828


class TotalTemperatureTests(unittest.TestCase):
    def test_total_temperature_worked_example_value(self):
        self.assertAlmostEqual(m.total_temperature(T_INF, MACH),
                               EXPECT_T_TOT, delta=0.01)
        self.assertEqual(m.total_temperature(T_INF, 0.0), T_INF)

    def test_kinetic_temperature_rise_consistency_and_zero_mach(self):
        self.assertAlmostEqual(m.kinetic_temperature_rise(T_INF, MACH),
                               EXPECT_T_KIN, delta=0.01)
        tot = m.total_temperature(T_INF, MACH)
        self.assertAlmostEqual(tot - T_INF,
                               m.kinetic_temperature_rise(T_INF, MACH),
                               places=6)
        self.assertEqual(m.kinetic_temperature_rise(T_INF, 0.0), 0.0)

    def test_total_temperature_rejects_bad_inputs(self):
        for bad in (0.0, -5.0):
            with self.assertRaises(ValueError):
                m.total_temperature(bad, 0.5)
        with self.assertRaises(ValueError):
            m.total_temperature(T_INF, -0.1)


class CatchEfficiencyTests(unittest.TestCase):
    def test_catch_efficiency_worked_example_value_in_band(self):
        eta = m.catch_efficiency(MVD, V, CHORD)
        self.assertAlmostEqual(eta, EXPECT_ETA, places=4)
        self.assertGreater(eta, 0.5)
        self.assertLess(eta, 0.9)

    def test_catch_efficiency_monotone_trends(self):
        eta_20 = m.catch_efficiency(20.0, 235.0, CHORD)
        self.assertGreater(m.catch_efficiency(40.0, 235.0, CHORD), eta_20)
        self.assertGreater(m.catch_efficiency(20.0, 300.0, CHORD), eta_20)
        self.assertLess(m.catch_efficiency(20.0, 235.0, 0.9), eta_20)

    def test_catch_efficiency_capped_at_one_for_large_mvd_and_airspeed(self):
        self.assertEqual(m.catch_efficiency(60.0, 300.0, 0.2), 1.0)

    def test_catch_efficiency_zero_at_zero_airspeed(self):
        self.assertEqual(m.catch_efficiency(MVD, 0.0, CHORD), 0.0)

    def test_catch_efficiency_rejects_bad_inputs(self):
        for bad_mvd in (0.0, -2.0):
            with self.assertRaises(ValueError):
                m.catch_efficiency(bad_mvd, V, CHORD)
        with self.assertRaises(ValueError):
            m.catch_efficiency(MVD, -5.0, CHORD)
        for bad_chord in (0.0, -0.1):
            with self.assertRaises(ValueError):
                m.catch_efficiency(MVD, V, bad_chord)


class WaterCatchRateTests(unittest.TestCase):
    def test_water_catch_rate_worked_example_value(self):
        eta = m.catch_efficiency(MVD, V, CHORD)
        self.assertAlmostEqual(m.water_catch_rate(eta, LWC, V, CHORD),
                               EXPECT_M_WDOT, places=5)

    def test_water_catch_rate_linear_scaling(self):
        eta = m.catch_efficiency(MVD, V, CHORD)
        base = m.water_catch_rate(eta, LWC, V, CHORD)
        self.assertAlmostEqual(m.water_catch_rate(eta, 2.0 * LWC, V, CHORD),
                               2.0 * base, places=8)
        self.assertAlmostEqual(m.water_catch_rate(eta, LWC, 2.0 * V, CHORD),
                               2.0 * base, places=8)
        self.assertAlmostEqual(m.water_catch_rate(eta, LWC, V, 2.0 * CHORD),
                               2.0 * base, places=8)

    def test_water_catch_rate_rejects_bad_inputs(self):
        eta = m.catch_efficiency(MVD, V, CHORD)
        with self.assertRaises(ValueError):
            m.water_catch_rate(eta, -1e-4, V, CHORD)
        with self.assertRaises(ValueError):
            m.water_catch_rate(eta, LWC, -1.0, CHORD)
        with self.assertRaises(ValueError):
            m.water_catch_rate(eta, LWC, V, 0.0)
        for bad_eta in (-0.1, 1.2):
            with self.assertRaises(ValueError):
                m.water_catch_rate(bad_eta, LWC, V, CHORD)


class FreezingFractionTests(unittest.TestCase):
    def test_freezing_fraction_zero_at_and_above_freeze(self):
        self.assertEqual(m.freezing_fraction(m.T_FREEZE), 0.0)
        self.assertEqual(m.freezing_fraction(300.0), 0.0)

    def test_freezing_fraction_between_zero_and_one_below_freeze(self):
        n = m.freezing_fraction(268.15)
        self.assertAlmostEqual(n, 0.062665, places=4)
        self.assertGreater(n, 0.0)
        self.assertLess(n, 1.0)

    def test_freezing_fraction_capped_at_one_for_cold_surface(self):
        self.assertEqual(m.freezing_fraction(180.0), 1.0)

    def test_freezing_fraction_rejects_nonpositive_temperature(self):
        for bad in (0.0, -10.0):
            with self.assertRaises(ValueError):
                m.freezing_fraction(bad)


class ConvectiveCoefficientTests(unittest.TestCase):
    def test_convective_heat_transfer_coefficient_worked_example_value(self):
        t_film = 0.5 * (m.T_FREEZE + T_INF)
        self.assertAlmostEqual(m.convective_heat_transfer_coefficient(
            V, RHO, CHORD, t_film), EXPECT_H_C, delta=0.05)

    def test_hc_trends_with_airspeed_density_and_chord(self):
        t_film = 0.5 * (m.T_FREEZE + T_INF)
        h_base = m.convective_heat_transfer_coefficient(V, RHO, CHORD, t_film)
        self.assertGreater(m.convective_heat_transfer_coefficient(
            300.0, RHO, CHORD, t_film), h_base)
        self.assertGreater(m.convective_heat_transfer_coefficient(
            V, 0.6, CHORD, t_film), h_base)
        self.assertLess(m.convective_heat_transfer_coefficient(
            V, RHO, 1.2, t_film), h_base)
        self.assertEqual(m.convective_heat_transfer_coefficient(
            0.0, RHO, CHORD, t_film), 0.0)

    def test_hc_rejects_bad_inputs(self):
        t_film = 0.5 * (m.T_FREEZE + T_INF)
        with self.assertRaises(ValueError):
            m.convective_heat_transfer_coefficient(-1.0, RHO, CHORD, t_film)
        for bad_rho in (0.0, -0.1):
            with self.assertRaises(ValueError):
                m.convective_heat_transfer_coefficient(V, bad_rho, CHORD,
                                                       t_film)
        with self.assertRaises(ValueError):
            m.convective_heat_transfer_coefficient(V, RHO, 0.0, t_film)
        with self.assertRaises(ValueError):
            m.convective_heat_transfer_coefficient(V, RHO, CHORD, 0.0)


class ConvectiveLossTests(unittest.TestCase):
    def test_convective_heat_loss_worked_example_value(self):
        t_film = 0.5 * (m.T_FREEZE + T_INF)
        h_c = m.convective_heat_transfer_coefficient(V, RHO, CHORD, t_film)
        self.assertAlmostEqual(m.convective_heat_loss(
            h_c, m.T_FREEZE, T_INF), EXPECT_Q_CONV, delta=1.0)
        self.assertEqual(m.convective_heat_loss(h_c, T_INF, T_INF), 0.0)

    def test_convective_heat_loss_rejects_bad_inputs(self):
        t_film = 0.5 * (m.T_FREEZE + T_INF)
        h_c = m.convective_heat_transfer_coefficient(V, RHO, CHORD, t_film)
        with self.assertRaises(ValueError):
            m.convective_heat_loss(-1.0, m.T_FREEZE, T_INF)
        for bad_t in (0.0, -50.0):
            with self.assertRaises(ValueError):
                m.convective_heat_loss(h_c, bad_t, T_INF)
            with self.assertRaises(ValueError):
                m.convective_heat_loss(h_c, m.T_FREEZE, bad_t)


class EvaporativeLossTests(unittest.TestCase):
    def test_evaporative_heat_loss_worked_example_value_and_scaling(self):
        eta = m.catch_efficiency(MVD, V, CHORD)
        m_evap = m.water_catch_rate(eta, LWC, V, CHORD) * SPAN
        self.assertAlmostEqual(m.evaporative_heat_loss(m_evap, EXPECT_AREA),
                               EXPECT_Q_EVAP, delta=100.0)
        q1 = m.evaporative_heat_loss(0.1, 2.0)
        self.assertAlmostEqual(m.evaporative_heat_loss(0.2, 2.0),
                               2.0 * q1, places=6)

    def test_evaporative_heat_loss_rejects_bad_inputs(self):
        with self.assertRaises(ValueError):
            m.evaporative_heat_loss(-0.01, 2.0)
        for bad_area in (0.0, -1.0):
            with self.assertRaises(ValueError):
                m.evaporative_heat_loss(0.1, bad_area)


class EvaporativeAntiIceTests(unittest.TestCase):
    def test_anti_ice_evaporative_heat_flux_worked_example_value(self):
        t_film = 0.5 * (m.T_FREEZE + T_INF)
        h_c = m.convective_heat_transfer_coefficient(V, RHO, CHORD, t_film)
        eta = m.catch_efficiency(MVD, V, CHORD)
        m_evap = m.water_catch_rate(eta, LWC, V, CHORD) * SPAN
        q = m.anti_ice_evaporative_heat_flux(h_c, m.T_EVAP_SURFACE, T_INF,
                                             m_evap, EXPECT_AREA)
        self.assertAlmostEqual(q, EXPECT_Q_REQ_EVAP, delta=500.0)

    def test_evaporative_flux_decomposes_into_conv_evap_sensible(self):
        t_film = 0.5 * (m.T_FREEZE + T_INF)
        h_c = m.convective_heat_transfer_coefficient(V, RHO, CHORD, t_film)
        m_evap = 0.1
        area = 2.0
        t_surf = m.T_EVAP_SURFACE
        q_conv = m.convective_heat_loss(h_c, t_surf, T_INF)
        q_evap = m.evaporative_heat_loss(m_evap, area)
        q_sens = m_evap * m.CP_WATER * (t_surf - T_INF) / area
        q = m.anti_ice_evaporative_heat_flux(h_c, t_surf, T_INF, m_evap, area)
        self.assertAlmostEqual(q, q_conv + q_evap + q_sens, places=6)


class RunningWetTests(unittest.TestCase):
    def test_running_wet_heat_flux_at_freeze_limit_value(self):
        t_film = 0.5 * (m.T_FREEZE + T_INF)
        h_c = m.convective_heat_transfer_coefficient(V, RHO, CHORD, t_film)
        t_kin = m.kinetic_temperature_rise(T_INF, MACH)
        q = m.running_wet_heat_flux(h_c, m.T_FREEZE, T_INF, t_kin)
        self.assertAlmostEqual(q, EXPECT_Q_RW, delta=1.0)

    def test_running_wet_surface_temperature_round_trip_and_freeze_limit(
            self):
        t_film = 0.5 * (m.T_FREEZE + T_INF)
        h_c = m.convective_heat_transfer_coefficient(V, RHO, CHORD, t_film)
        t_kin = m.kinetic_temperature_rise(T_INF, MACH)
        t_target = 278.15
        q = m.running_wet_heat_flux(h_c, t_target, T_INF, t_kin)
        self.assertAlmostEqual(
            m.running_wet_surface_temperature(q, h_c, T_INF, t_kin),
            t_target, places=6)
        q_frz = m.running_wet_heat_flux(h_c, m.T_FREEZE, T_INF, t_kin)
        t_surf = m.running_wet_surface_temperature(q_frz, h_c, T_INF, t_kin)
        self.assertAlmostEqual(t_surf, m.T_FREEZE, places=6)
        self.assertEqual(m.freezing_fraction(t_surf), 0.0)

    def test_running_wet_surface_temperature_rejects_bad_inputs(self):
        t_film = 0.5 * (m.T_FREEZE + T_INF)
        h_c = m.convective_heat_transfer_coefficient(V, RHO, CHORD, t_film)
        with self.assertRaises(ValueError):
            m.running_wet_surface_temperature(-1.0, h_c, T_INF, 10.0)
        for bad_hc in (0.0, -1.0):
            with self.assertRaises(ValueError):
                m.running_wet_surface_temperature(1000.0, bad_hc, T_INF, 10.0)
        with self.assertRaises(ValueError):
            m.running_wet_surface_temperature(1000.0, h_c, 0.0, 10.0)
        with self.assertRaises(ValueError):
            m.running_wet_surface_temperature(1000.0, h_c, T_INF, -1.0)


class DeIceAndPowerTests(unittest.TestCase):
    def test_de_ice_heat_flux_value_at_shed_temperature(self):
        t_film = 0.5 * (m.T_FREEZE + T_INF)
        h_c = m.convective_heat_transfer_coefficient(V, RHO, CHORD, t_film)
        q = m.de_ice_heat_flux(h_c, T_INF)
        self.assertAlmostEqual(q,
                               m.convective_heat_loss(h_c, m.T_SHED, T_INF),
                               places=6)
        self.assertAlmostEqual(m.required_power(q, EXPECT_AREA),
                               EXPECT_P_DEICE, delta=1.0)

    def test_required_power_and_protected_area_worked_example_values(self):
        area = m.protected_area(CHORD, SPAN, BAND_FRACTION)
        self.assertAlmostEqual(area, EXPECT_AREA, places=6)
        t_film = 0.5 * (m.T_FREEZE + T_INF)
        h_c = m.convective_heat_transfer_coefficient(V, RHO, CHORD, t_film)
        t_kin = m.kinetic_temperature_rise(T_INF, MACH)
        q_rw = m.running_wet_heat_flux(h_c, m.T_FREEZE, T_INF, t_kin)
        self.assertAlmostEqual(m.required_power(q_rw, area),
                               EXPECT_P_RW, delta=1.0)
        eta = m.catch_efficiency(MVD, V, CHORD)
        m_evap = m.water_catch_rate(eta, LWC, V, CHORD) * SPAN
        q_evap_mode = m.anti_ice_evaporative_heat_flux(
            h_c, m.T_EVAP_SURFACE, T_INF, m_evap, area)
        self.assertAlmostEqual(m.required_power(q_evap_mode, area),
                               EXPECT_P_EVAP, delta=500.0)

    def test_required_power_scales_with_area(self):
        p1 = m.required_power(5000.0, 1.0)
        self.assertAlmostEqual(m.required_power(5000.0, 3.0),
                               3.0 * p1, places=6)

    def test_required_power_and_area_reject_bad_inputs(self):
        with self.assertRaises(ValueError):
            m.required_power(-100.0, 1.0)
        for bad_area in (0.0, -1.0):
            with self.assertRaises(ValueError):
                m.required_power(100.0, bad_area)
        for bad_chord in (0.0, -1.0):
            with self.assertRaises(ValueError):
                m.protected_area(bad_chord, SPAN, BAND_FRACTION)
        for bad_span in (0.0, -1.0):
            with self.assertRaises(ValueError):
                m.protected_area(CHORD, bad_span, BAND_FRACTION)
        for bad_frac in (0.0, -0.1, 1.5):
            with self.assertRaises(ValueError):
                m.protected_area(CHORD, SPAN, bad_frac)


class BleedFlowTests(unittest.TestCase):
    def test_bleed_mass_flow_worked_example_values_and_scaling(self):
        m_rw = m.bleed_mass_flow(EXPECT_P_RW, m.CP_AIR, 450.0, T_INF)
        self.assertAlmostEqual(m_rw, EXPECT_BLEED_RW, places=5)
        m_evap = m.bleed_mass_flow(EXPECT_P_EVAP, m.CP_AIR, 450.0, T_INF)
        self.assertAlmostEqual(m_evap, EXPECT_BLEED_EVAP, places=3)
        b1 = m.bleed_mass_flow(1000.0, m.CP_AIR, 450.0, 218.0)
        self.assertAlmostEqual(m.bleed_mass_flow(2000.0, m.CP_AIR, 450.0,
                                                 218.0), 2.0 * b1, places=8)

    def test_bleed_mass_flow_rejects_bad_inputs(self):
        with self.assertRaises(ValueError):
            m.bleed_mass_flow(-100.0, m.CP_AIR, 450.0, 218.0)
        with self.assertRaises(ValueError):
            m.bleed_mass_flow(1000.0, 0.0, 450.0, 218.0)
        with self.assertRaises(ValueError):
            m.bleed_mass_flow(1000.0, m.CP_AIR, 218.0, 218.0)
        with self.assertRaises(ValueError):
            m.bleed_mass_flow(1000.0, m.CP_AIR, 200.0, 218.0)
        for bad_t in (0.0, -10.0):
            with self.assertRaises(ValueError):
                m.bleed_mass_flow(1000.0, m.CP_AIR, 450.0, bad_t)


class ProtectVerdictTests(unittest.TestCase):
    def test_protect_verdict_protect_flag_and_noncritical_modes(self):
        area = m.protected_area(CHORD, SPAN, BAND_FRACTION)
        verdict_ok = m.protect_verdict(area, EXPECT_P_RW, 1.5e6, True)
        self.assertTrue(verdict_ok["protect"])
        self.assertTrue(verdict_ok["icing_critical"])
        verdict_short = m.protect_verdict(area, EXPECT_P_EVAP, 100e3, True)
        self.assertFalse(verdict_short["protect"])
        self.assertIn("exceeds", verdict_short["reason"])
        verdict_nc = m.protect_verdict(area, EXPECT_P_RW, 0.0, False)
        self.assertFalse(verdict_nc["protect"])
        self.assertFalse(verdict_nc["icing_critical"])

    def test_protect_verdict_rejects_bad_inputs(self):
        with self.assertRaises(ValueError):
            m.protect_verdict(1.0, 100.0, -1.0, True)
        with self.assertRaises(ValueError):
            m.protect_verdict(0.0, 100.0, 1000.0, True)
        with self.assertRaises(ValueError):
            m.protect_verdict(1.0, -100.0, 1000.0, True)


if __name__ == "__main__":
    unittest.main()
