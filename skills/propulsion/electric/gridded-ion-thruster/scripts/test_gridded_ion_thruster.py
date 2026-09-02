#!/usr/bin/env python3
"""Gate 3 contract test: gridded ion thruster performance logic.

Exercises scripts/gridded_ion_thruster_logic.py (stdlib unittest,
offline, deterministic). Contract: docs/harness-contract.md gate 3.
Covers the standard electrostatic gridded (Kaufman type) model step by
step: ion exhaust velocity and specific impulse from the net beam
voltage, Child-Langmuir space-charge-limited current density and the
perveance-margin beam current, thrust from the beam current with the
optional divergence efficiency, the power chain (beam power, total
input power) and the thrust-from-power sizing bridge, the 1100 V worked
example contract (thrust within 1% of the bridge value, rocket-equation
propellant mass), the gridded vs hall comparison at equal power, and
invalid-input review: non-positive voltage, gap, area, current, power,
mass and out-of-range efficiency or perveance margin must raise
ValueError.
"""

import math
import os
import sys
import unittest

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import gridded_ion_thruster_logic as git  # noqa: E402

XENON_MASS = git.xenon_ion_mass()      # kg
KRYPTON_MASS = git.ion_mass_from_u(83.798)  # kg

# Worked example operating point (SKILL.md).
V_NET = 1100.0       # net beam voltage, V
GAP = 0.8e-3         # effective screen-to-accelerator gap, m
A_EXTRACT = 0.028    # extraction area, m^2
ETA_GRID = 0.68      # grid transparency
ETA_PERV = 0.6       # perveance margin
ETA_D = 0.985        # divergence efficiency (cos mean half-angle)
ETA_T = 0.65         # total efficiency
ETA_POWER = 0.66     # power chain efficiency (thruster plus PPU)


class WorkedExampleTest(unittest.TestCase):
    def test_exhaust_velocity_1100v(self):
        # v_i = sqrt(2*e*V/m): xenon at 1100 V.
        v = git.exhaust_velocity(V_NET, XENON_MASS)
        expected = math.sqrt(2.0 * git.E_CHARGE * V_NET / XENON_MASS)
        self.assertAlmostEqual(v, expected, places=9)
        self.assertAlmostEqual(v, 40208.797, delta=0.5)

    def test_isp_1100v_in_sanity_band(self):
        # Gridded thrusters reach 3000-4500 s at 1000-1500 V net.
        isp = git.isp_from_net_voltage(V_NET, XENON_MASS)
        self.assertAlmostEqual(isp, 4100.1562, delta=0.1)
        self.assertGreaterEqual(isp, 3000.0)
        self.assertLessEqual(isp, 4500.0)

    def test_child_langmuir_density_1100v(self):
        j_cl = git.child_langmuir_density(V_NET, GAP, XENON_MASS)
        expected = (4.0 * git.EPS0 / 9.0) * math.sqrt(
            2.0 * git.E_CHARGE / XENON_MASS) * V_NET ** 1.5 / (GAP * GAP)
        self.assertAlmostEqual(j_cl, expected, places=9)
        self.assertAlmostEqual(j_cl, 271.957, delta=0.1)

    def test_beam_current_from_perveance(self):
        i_b = git.beam_current_from_perveance(
            V_NET, GAP, A_EXTRACT, ETA_GRID, ETA_PERV, XENON_MASS)
        # I_b = eta_perv * J_CL * A_extract * eta_grid.
        expected = ETA_PERV * 271.95685 * A_EXTRACT * ETA_GRID
        self.assertAlmostEqual(i_b, expected, delta=0.01)
        self.assertAlmostEqual(i_b, 3.1068, delta=0.01)

    def test_thrust_from_beam_current(self):
        t = git.thrust_from_beam_current(
            git.beam_current_from_perveance(
                V_NET, GAP, A_EXTRACT, ETA_GRID, ETA_PERV, XENON_MASS),
            V_NET, XENON_MASS, ETA_D)
        self.assertAlmostEqual(t, 0.167439, delta=0.001)
        # Sanity band: a 2.3-5 kW class thruster gives 100-250 mN.
        self.assertGreaterEqual(t, 0.100)
        self.assertLessEqual(t, 0.250)

    def test_power_chain(self):
        i_b = git.beam_current_from_perveance(
            V_NET, GAP, A_EXTRACT, ETA_GRID, ETA_PERV, XENON_MASS)
        p_b = git.beam_power(i_b, V_NET)
        self.assertAlmostEqual(p_b, 3417.52, delta=1.0)
        p_total = git.total_power(p_b, ETA_POWER)
        self.assertAlmostEqual(p_total, 5178.06, delta=1.0)

    def test_sizing_bridge_self_consistent_within_1pct(self):
        # Beam-side thrust and the sizing bridge agree at eta_T = 0.65.
        i_b = git.beam_current_from_perveance(
            V_NET, GAP, A_EXTRACT, ETA_GRID, ETA_PERV, XENON_MASS)
        t_beam = git.thrust_from_beam_current(i_b, V_NET, XENON_MASS, ETA_D)
        p_total = git.total_power(git.beam_power(i_b, V_NET), ETA_POWER)
        isp = git.isp_from_net_voltage(V_NET, XENON_MASS)
        t_bridge = git.thrust_from_power(p_total, ETA_T, isp)
        self.assertLess(abs(t_beam - t_bridge) / t_beam, 0.01)

    def test_thrust_to_power_in_sanity_band(self):
        # Gridded thrust-to-power on total input power: 25-45 mN/kW.
        i_b = git.beam_current_from_perveance(
            V_NET, GAP, A_EXTRACT, ETA_GRID, ETA_PERV, XENON_MASS)
        t = git.thrust_from_beam_current(i_b, V_NET, XENON_MASS, ETA_D)
        p_total = git.total_power(git.beam_power(i_b, V_NET), ETA_POWER)
        tp = git.thrust_to_power(t, p_total) * 1.0e6  # mN/kW
        self.assertAlmostEqual(tp, 32.34, delta=0.5)
        self.assertGreaterEqual(tp, 25.0)
        self.assertLessEqual(tp, 45.0)

    def test_propellant_mass_and_identity(self):
        isp = git.isp_from_net_voltage(V_NET, XENON_MASS)
        m_prop = git.propellant_mass_for_delta_v(2000.0, 1000.0, isp)
        self.assertAlmostEqual(m_prop, 50.9982, delta=0.5)
        self.assertAlmostEqual((1000.0 + m_prop) / 1000.0,
                               math.exp(2000.0 / (git.G0 * isp)), places=9)


class ExhaustAndIspTest(unittest.TestCase):
    def test_velocity_scales_with_sqrt_voltage(self):
        v1 = git.exhaust_velocity(1100.0, XENON_MASS)
        v4 = git.exhaust_velocity(4400.0, XENON_MASS)
        self.assertAlmostEqual(v4 / v1, 2.0, places=9)

    def test_isp_is_velocity_over_g0(self):
        v = git.exhaust_velocity(1100.0, XENON_MASS)
        self.assertAlmostEqual(git.isp_from_net_voltage(1100.0, XENON_MASS),
                               v / git.G0, places=9)

    def test_ion_masses(self):
        self.assertAlmostEqual(XENON_MASS, 2.1801727822e-25, places=33)
        self.assertAlmostEqual(KRYPTON_MASS, 1.3914993092e-25, places=33)

    def test_non_positive_inputs_raise(self):
        with self.assertRaises(ValueError):
            git.exhaust_velocity(0.0, XENON_MASS)
        with self.assertRaises(ValueError):
            git.exhaust_velocity(1100.0, 0.0)
        with self.assertRaises(ValueError):
            git.isp_from_net_voltage(-300.0, XENON_MASS)
        with self.assertRaises(ValueError):
            git.ion_mass_from_u(0.0)


class ChildLangmuirTest(unittest.TestCase):
    def test_density_scales_as_v15(self):
        j1 = git.child_langmuir_density(1100.0, GAP, XENON_MASS)
        j2 = git.child_langmuir_density(2200.0, GAP, XENON_MASS)
        self.assertAlmostEqual(j2 / j1, 2.0 ** 1.5, places=9)

    def test_density_inverse_square_gap(self):
        j1 = git.child_langmuir_density(1100.0, GAP, XENON_MASS)
        j2 = git.child_langmuir_density(1100.0, 2.0 * GAP, XENON_MASS)
        self.assertAlmostEqual(j2 / j1, 0.25, places=9)

    def test_beam_current_linear_in_margin_and_transparency(self):
        base = git.beam_current_from_perveance(
            V_NET, GAP, A_EXTRACT, ETA_GRID, ETA_PERV, XENON_MASS)
        half = git.beam_current_from_perveance(
            V_NET, GAP, A_EXTRACT, ETA_GRID, 0.3, XENON_MASS)
        self.assertAlmostEqual(half, base / 2.0, places=9)
        low_trans = git.beam_current_from_perveance(
            V_NET, GAP, A_EXTRACT, 0.5, ETA_PERV, XENON_MASS)
        self.assertAlmostEqual(low_trans, base * 0.5 / ETA_GRID, places=9)

    def test_invalid_inputs_raise(self):
        with self.assertRaises(ValueError):
            git.child_langmuir_density(0.0, GAP, XENON_MASS)
        with self.assertRaises(ValueError):
            git.child_langmuir_density(V_NET, 0.0, XENON_MASS)
        with self.assertRaises(ValueError):
            git.beam_current_from_perveance(V_NET, GAP, A_EXTRACT,
                                            ETA_GRID, 0.0, XENON_MASS)
        with self.assertRaises(ValueError):
            git.beam_current_from_perveance(V_NET, GAP, A_EXTRACT,
                                            ETA_GRID, 1.2, XENON_MASS)
        with self.assertRaises(ValueError):
            git.beam_current_from_perveance(V_NET, GAP, 0.0,
                                            ETA_GRID, ETA_PERV, XENON_MASS)
        with self.assertRaises(ValueError):
            git.beam_current_from_perveance(V_NET, GAP, A_EXTRACT,
                                            1.1, ETA_PERV, XENON_MASS)


class ThrustAndPowerChainTest(unittest.TestCase):
    def test_thrust_scales_with_beam_current(self):
        t1 = git.thrust_from_beam_current(2.0, V_NET, XENON_MASS, ETA_D)
        t2 = git.thrust_from_beam_current(4.0, V_NET, XENON_MASS, ETA_D)
        self.assertAlmostEqual(t2, 2.0 * t1, places=9)

    def test_divergence_efficiency_applied(self):
        t_ideal = git.thrust_from_beam_current(2.0, V_NET, XENON_MASS)
        t_div = git.thrust_from_beam_current(2.0, V_NET, XENON_MASS, ETA_D)
        self.assertAlmostEqual(t_div, t_ideal * ETA_D, places=9)

    def test_thrust_from_power_scaling(self):
        isp = git.isp_from_net_voltage(V_NET, XENON_MASS)
        t1 = git.thrust_from_power(5000.0, ETA_T, isp)
        t2 = git.thrust_from_power(10000.0, ETA_T, isp)
        self.assertAlmostEqual(t2, 2.0 * t1, places=9)

    def test_beam_and_total_power_identity(self):
        p_b = git.beam_power(3.0, V_NET)
        self.assertAlmostEqual(p_b, 3300.0, places=9)
        self.assertAlmostEqual(git.total_power(p_b, 0.66), 5000.0, places=6)

    def test_mass_flow_from_thrust(self):
        isp = git.isp_from_net_voltage(V_NET, XENON_MASS)
        t = git.thrust_from_beam_current(
            git.beam_current_from_perveance(
                V_NET, GAP, A_EXTRACT, ETA_GRID, ETA_PERV, XENON_MASS),
            V_NET, XENON_MASS, ETA_D)
        mdot = git.mass_flow_from_thrust(t, isp)
        self.assertAlmostEqual(mdot, t / (git.G0 * isp), places=12)
        self.assertAlmostEqual(mdot, 4.162e-6, delta=1e-8)

    def test_invalid_inputs_raise(self):
        with self.assertRaises(ValueError):
            git.thrust_from_power(0.0, ETA_T, 4100.0)
        with self.assertRaises(ValueError):
            git.thrust_from_power(5000.0, 0.0, 4100.0)
        with self.assertRaises(ValueError):
            git.thrust_from_power(5000.0, 1.5, 4100.0)
        with self.assertRaises(ValueError):
            git.thrust_from_beam_current(0.0, V_NET, XENON_MASS)
        with self.assertRaises(ValueError):
            git.beam_power(2.0, -V_NET)
        with self.assertRaises(ValueError):
            git.total_power(0.0, 0.66)
        with self.assertRaises(ValueError):
            git.mass_flow_from_thrust(0.0, 4100.0)


class RocketEquationTest(unittest.TestCase):
    def test_known_propellant_mass(self):
        m_prop = git.propellant_mass_for_delta_v(2000.0, 1000.0, 4100.1562)
        self.assertAlmostEqual(m_prop, 50.9982, places=2)

    def test_rocket_equation_identity(self):
        m_prop = git.propellant_mass_for_delta_v(2000.0, 1000.0, 4100.1562)
        self.assertAlmostEqual((1000.0 + m_prop) / 1000.0,
                               math.exp(2000.0 / (git.G0 * 4100.1562)),
                               places=9)

    def test_zero_delta_v_gives_zero(self):
        self.assertEqual(
            git.propellant_mass_for_delta_v(0.0, 1000.0, 4100.0), 0.0)

    def test_invalid_inputs_raise(self):
        with self.assertRaises(ValueError):
            git.propellant_mass_for_delta_v(2000.0, 0.0, 4100.0)
        with self.assertRaises(ValueError):
            git.propellant_mass_for_delta_v(-100.0, 1000.0, 4100.0)
        with self.assertRaises(ValueError):
            git.propellant_mass_for_delta_v(2000.0, 1000.0, 0.0)


class GriddedVsHallTest(unittest.TestCase):
    def test_comparison_directions_at_equal_power(self):
        # 5000 W, gridded Isp 4100 s eta 0.65 vs hall Isp 1600 s eta 0.5.
        cmp_ = git.gridded_vs_hall_compare(5000.0, 4100.0, 1600.0,
                                           0.65, 0.5)
        # Gridded: higher Isp, lower thrust, far lower mass flow.
        self.assertGreater(cmp_["isp_ratio_gridded_over_hall"], 1.0)
        self.assertLess(cmp_["thrust_ratio_gridded_over_hall"], 1.0)
        self.assertLess(cmp_["mass_flow_ratio_gridded_over_hall"], 1.0)

    def test_comparison_values(self):
        cmp_ = git.gridded_vs_hall_compare(5000.0, 4100.0, 1600.0,
                                           0.65, 0.5)
        self.assertAlmostEqual(cmp_["power"], 5000.0, places=9)
        self.assertAlmostEqual(cmp_["gridded"]["thrust"], 0.16166,
                               delta=1e-4)
        self.assertAlmostEqual(cmp_["hall"]["thrust"], 0.31866,
                               delta=1e-4)
        self.assertAlmostEqual(cmp_["thrust_ratio_gridded_over_hall"],
                               0.5073, delta=1e-3)
        self.assertAlmostEqual(cmp_["isp_ratio_gridded_over_hall"],
                               2.5625, places=4)
        # Gridded burns about one fifth the propellant flow of the hall.
        self.assertAlmostEqual(cmp_["mass_flow_ratio_gridded_over_hall"],
                               0.19798, delta=1e-3)
        # Thrust-to-power: hall higher per kilowatt, gridded higher Isp.
        self.assertGreater(cmp_["hall"]["thrust_to_power"],
                           cmp_["gridded"]["thrust_to_power"])

    def test_invalid_inputs_raise(self):
        with self.assertRaises(ValueError):
            git.gridded_vs_hall_compare(0.0, 4100.0, 1600.0, 0.65, 0.5)
        with self.assertRaises(ValueError):
            git.gridded_vs_hall_compare(5000.0, 4100.0, 1600.0, 0.0, 0.5)
        with self.assertRaises(ValueError):
            git.gridded_vs_hall_compare(5000.0, -4100.0, 1600.0, 0.65, 0.5)
        with self.assertRaises(ValueError):
            git.gridded_vs_hall_compare(5000.0, 4100.0, 1600.0, 0.65, 1.1)


if __name__ == "__main__":
    unittest.main(verbosity=2)
