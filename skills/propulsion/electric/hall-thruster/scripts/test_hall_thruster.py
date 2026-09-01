#!/usr/bin/env python3
"""Gate 3 contract test: Hall effect thruster performance logic.

Exercises scripts/hall_thruster_logic.py (stdlib unittest, offline,
deterministic). Contract: docs/harness-contract.md gate 3. Covers the
standard HET model step by step: thrust from mass flow and exhaust
velocity, ideal and effective exhaust velocity with utilization factors,
specific impulse, thrust-to-power ratio, the total efficiency
decomposition (mass, voltage, current utilization, divergence), beam
current from thrust and from ionized mass flow, discharge power and
current, anode vs total efficiency with the auxiliary power split,
xenon vs krypton propellant comparison, the 5 kW class sizing contract
(thrust within 1% of 0.32 N, rocket-equation propellant mass), and
invalid-input review: non-positive power, voltage, current, mass and
efficiency values must raise ValueError.
"""

import math
import os
import sys
import unittest

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import hall_thruster_logic as ht  # noqa: E402

XENON_MASS = ht.ion_mass_from_u(131.293)   # kg
KRYPTON_MASS = ht.ion_mass_from_u(83.798)  # kg


class ThrustFromPowerTest(unittest.TestCase):
    def test_5kw_contract_thrust(self):
        # 5 kW, eta_total 0.5, Isp 1600 s: T = 2*eta*P/(g0*Isp).
        t = ht.thrust_from_power(5000.0, 0.5, 1600.0)
        self.assertAlmostEqual(t, 0.3186613165556026, places=6)
        # Contract: within 1% of 0.32 N.
        self.assertLess(abs(t - 0.32) / 0.32, 0.01)

    def test_thrust_scales_with_power(self):
        t5 = ht.thrust_from_power(5000.0, 0.5, 1600.0)
        t10 = ht.thrust_from_power(10000.0, 0.5, 1600.0)
        self.assertAlmostEqual(t10, 2.0 * t5, places=9)

    def test_thrust_scales_with_efficiency(self):
        t = ht.thrust_from_power(5000.0, 0.25, 1600.0)
        self.assertAlmostEqual(t, ht.thrust_from_power(5000.0, 0.5, 1600.0) / 2.0,
                               places=9)

    def test_zero_power_raises(self):
        with self.assertRaises(ValueError):
            ht.thrust_from_power(0.0, 0.5, 1600.0)

    def test_negative_power_raises(self):
        with self.assertRaises(ValueError):
            ht.thrust_from_power(-100.0, 0.5, 1600.0)

    def test_invalid_efficiency_raises(self):
        with self.assertRaises(ValueError):
            ht.thrust_from_power(5000.0, 0.0, 1600.0)
        with self.assertRaises(ValueError):
            ht.thrust_from_power(5000.0, 1.5, 1600.0)

    def test_non_positive_isp_raises(self):
        with self.assertRaises(ValueError):
            ht.thrust_from_power(5000.0, 0.5, 0.0)


class ExhaustVelocityTest(unittest.TestCase):
    def test_ideal_exhaust_velocity_xenon(self):
        # v = sqrt(2*e*V/m): Xe at 270 V.
        v = ht.ideal_exhaust_velocity(270.0, XENON_MASS)
        expected = math.sqrt(2.0 * ht.E_CHARGE * 270.0 / XENON_MASS)
        self.assertAlmostEqual(v, expected, places=9)

    def test_effective_exhaust_velocity_utilization(self):
        ideal = ht.ideal_exhaust_velocity(270.0, XENON_MASS)
        ve = ht.exhaust_velocity(270.0, XENON_MASS, 0.85, 0.90)
        self.assertAlmostEqual(ve, ideal * 0.85 * 0.90, places=9)

    def test_isp_from_exhaust_velocity(self):
        ve = 15690.64  # g0 * 1600 s
        self.assertAlmostEqual(ht.isp_from_exhaust_velocity(ve), 1600.0,
                               places=1)

    def test_mass_flow_from_thrust(self):
        mdot = ht.mass_flow_from_thrust(0.3186613165556026, 1600.0)
        expected = 0.3186613165556026 / (ht.G0 * 1600.0)
        self.assertAlmostEqual(mdot, expected, places=12)
        self.assertAlmostEqual(mdot, 2.0309e-5, delta=1e-9)

    def test_thrust_from_mass_flow(self):
        mdot = ht.mass_flow_from_thrust(0.3186613165556026, 1600.0)
        t = ht.thrust_from_mass_flow(mdot, ht.G0 * 1600.0)
        self.assertAlmostEqual(t, 0.3186613165556026, places=6)

    def test_thrust_to_power(self):
        tp = ht.thrust_to_power(0.3186613165556026, 5000.0)
        self.assertAlmostEqual(tp, 6.373226331112051e-05, places=12)

    def test_invalid_mass_raises(self):
        with self.assertRaises(ValueError):
            ht.ideal_exhaust_velocity(270.0, 0.0)
        with self.assertRaises(ValueError):
            ht.thrust_from_mass_flow(0.0, 1000.0)


class EfficiencyDecompositionTest(unittest.TestCase):
    def test_total_efficiency_product(self):
        eta = ht.hall_thruster_efficiency(0.85, 0.90, 0.78, 0.84)
        self.assertAlmostEqual(eta, 0.85 * 0.90 * 0.78 * 0.84, places=12)
        self.assertAlmostEqual(eta, 0.501228, places=6)

    def test_efficiency_bounds(self):
        with self.assertRaises(ValueError):
            ht.hall_thruster_efficiency(0.0, 0.9, 0.78, 0.84)
        with self.assertRaises(ValueError):
            ht.hall_thruster_efficiency(0.85, 1.1, 0.78, 0.84)
        with self.assertRaises(ValueError):
            ht.hall_thruster_efficiency(0.85, 0.9, -0.1, 0.84)

    def test_anode_vs_total_efficiency(self):
        # Anode efficiency: T^2 / (2 m_dot P_d) for the 5 kW case.
        eta_a = ht.anode_efficiency(0.3186613165556026, 2.0309e-5, 5000.0)
        self.assertAlmostEqual(eta_a, 0.5, places=4)
        # Total efficiency with 300 W auxiliary power.
        eta_t = ht.total_efficiency_from_anode(eta_a, 5000.0, 5300.0)
        self.assertAlmostEqual(eta_t, eta_a * 5000.0 / 5300.0, places=9)

    def test_total_power_below_discharge_raises(self):
        with self.assertRaises(ValueError):
            ht.total_efficiency_from_anode(0.5, 5000.0, 4000.0)


class BeamAndDischargeTest(unittest.TestCase):
    def test_beam_current_round_trip(self):
        t = ht.thrust_from_power(5000.0, 0.5, 1600.0)
        ib = ht.beam_current(t, 270.0, XENON_MASS, 0.90)
        t_back = ht.thrust_from_beam_current(ib, 270.0, XENON_MASS, 0.90)
        self.assertAlmostEqual(t_back, t, places=9)

    def test_beam_current_from_mass_flow(self):
        mdot = ht.mass_flow_from_thrust(0.3186613165556026, 1600.0)
        ib = ht.beam_current_from_mass_flow(mdot, 0.85, XENON_MASS)
        expected = ht.E_CHARGE * 0.85 * mdot / XENON_MASS
        self.assertAlmostEqual(ib, expected, places=12)

    def test_discharge_power(self):
        p = ht.discharge_power(300.0, 16.6667)
        self.assertAlmostEqual(p, 5000.01, places=2)

    def test_discharge_current_from_beam(self):
        self.assertAlmostEqual(ht.discharge_current_from_beam(13.0, 0.78),
                               16.666666666666668, places=9)

    def test_invalid_discharge_inputs_raise(self):
        with self.assertRaises(ValueError):
            ht.discharge_power(0.0, 16.0)
        with self.assertRaises(ValueError):
            ht.discharge_power(300.0, -1.0)
        with self.assertRaises(ValueError):
            ht.beam_current(0.0, 270.0, XENON_MASS)


class PropellantMassTest(unittest.TestCase):
    def test_rocket_equation_identity(self):
        mp = ht.propellant_mass_for_delta_v(2000.0, 500.0, 1600.0)
        # m_final / m_dry = exp(dv / (g0 Isp)).
        self.assertAlmostEqual((500.0 + mp) / 500.0,
                               math.exp(2000.0 / (ht.G0 * 1600.0)), places=9)

    def test_known_propellant_mass(self):
        mp = ht.propellant_mass_for_delta_v(2000.0, 500.0, 1600.0)
        self.assertAlmostEqual(mp, 67.9722858677666, places=6)

    def test_zero_delta_v_gives_zero(self):
        self.assertEqual(ht.propellant_mass_for_delta_v(0.0, 500.0, 1600.0), 0.0)

    def test_invalid_inputs_raise(self):
        with self.assertRaises(ValueError):
            ht.propellant_mass_for_delta_v(2000.0, 0.0, 1600.0)
        with self.assertRaises(ValueError):
            ht.propellant_mass_for_delta_v(-100.0, 500.0, 1600.0)


class XenonKryptonTest(unittest.TestCase):
    def test_propellant_masses(self):
        self.assertAlmostEqual(XENON_MASS, 2.180171556711138e-25, places=33)
        self.assertAlmostEqual(KRYPTON_MASS, 1.391498527029468e-25, places=33)

    def test_comparison_values(self):
        cmp = ht.xenon_krypton_compare(270.0)
        xe = cmp["propellants"]["xenon"]
        kr = cmp["propellants"]["krypton"]
        self.assertEqual(xe["atomic_mass_u"], 131.293)
        self.assertEqual(kr["atomic_mass_u"], 83.798)
        self.assertAlmostEqual(xe["ionization_eV"], 12.1298, places=4)
        self.assertAlmostEqual(kr["ionization_eV"], 13.9996, places=4)
        # Krypton is lighter, so higher ideal exhaust velocity at 270 V.
        self.assertGreater(kr["ideal_exhaust_velocity"],
                           xe["ideal_exhaust_velocity"])
        self.assertAlmostEqual(cmp["exhaust_velocity_ratio_kr_over_xe"],
                               24935.076290279365 / 19920.798477299173,
                               places=9)

    def test_invalid_beam_voltage_raises(self):
        with self.assertRaises(ValueError):
            ht.xenon_krypton_compare(0.0)


if __name__ == "__main__":
    unittest.main(verbosity=2)
