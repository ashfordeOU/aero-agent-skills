"""Contract test for the cold gas thruster sizing logic (stdlib unittest).

Run offline: python3 scripts/test_cold_gas_thruster.py
Covers the wave-29 worked example anchors for a 25 MPa, 0.03 m3,
293 K nitrogen plenum with a 0.5 mm throat at 65 s Isp blowing down
to 2 MPa, the linear m_dot pressure scaling round trip, the
isothermal decay shape, the size_thruster chain and ValueError
rejection of non-physical inputs. Deterministic, offline, under 20 s.
"""

import math
import os
import sys
import unittest

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import cold_gas_thruster_logic as cg

P0 = 25e6          # plenum pressure, Pa
V = 0.03           # plenum volume, m3
T = 293.0          # temperature, K
D = 0.5e-3         # throat diameter, m
ISP = 65.0         # specific impulse, s
P_MIN = 2e6        # minimum usable pressure, Pa


class ColdGasThrusterAnchorsTest(unittest.TestCase):
    """Worked-example anchors from the wave-29 spec."""

    def test_cf_const_value(self):
        self.assertAlmostEqual(cg.CF_CONST, 0.039746, delta=1e-5)

    def test_throat_area_anchor(self):
        area = math.pi * D ** 2 / 4.0
        self.assertAlmostEqual(area, 1.9635e-7, delta=1e-12)

    def test_choked_mass_flow_anchor(self):
        mdot = cg.choked_mass_flow(P0, T, math.pi * D ** 2 / 4.0)
        self.assertAlmostEqual(mdot, 0.011398, delta=1e-5)

    def test_thrust_anchor(self):
        mdot = cg.choked_mass_flow(P0, T, math.pi * D ** 2 / 4.0)
        self.assertAlmostEqual(cg.thrust(mdot, ISP), 7.265, delta=0.01)

    def test_tank_gas_mass_anchor(self):
        self.assertAlmostEqual(
            cg.tank_gas_mass(P0, V, T), 8.6244, delta=0.001)

    def test_time_constant_anchor(self):
        mdot = cg.choked_mass_flow(P0, T, math.pi * D ** 2 / 4.0)
        tau = cg.blowdown_time_constant(
            cg.tank_gas_mass(P0, V, T), mdot)
        self.assertAlmostEqual(tau, 756.7, delta=0.5)

    def test_pressure_history_anchor(self):
        mdot = cg.choked_mass_flow(P0, T, math.pi * D ** 2 / 4.0)
        tau = cg.blowdown_time_constant(
            cg.tank_gas_mass(P0, V, T), mdot)
        p30 = cg.pressure_at_time(P0, 30.0, tau)
        self.assertAlmostEqual(p30 / 1e6, 24.028, delta=0.01)

    def test_operating_time_anchor(self):
        mdot = cg.choked_mass_flow(P0, T, math.pi * D ** 2 / 4.0)
        tau = cg.blowdown_time_constant(
            cg.tank_gas_mass(P0, V, T), mdot)
        t_op = cg.operating_time(P0, P_MIN, tau)
        self.assertAlmostEqual(t_op, 1911.1, delta=1.0)

    def test_total_impulse_anchor(self):
        m0 = cg.tank_gas_mass(P0, V, T)
        mf = cg.tank_gas_mass(P_MIN, V, T)
        self.assertAlmostEqual(mf, 0.68995, delta=0.001)
        self.assertAlmostEqual(
            cg.total_impulse(ISP, m0, mf), 5057.7, delta=1.0)

    def test_mass_flow_at_pmin_anchor(self):
        mdot_min = cg.choked_mass_flow(
            P_MIN, T, math.pi * D ** 2 / 4.0)
        self.assertAlmostEqual(mdot_min, 0.000912, delta=1e-5)

    def test_thrust_at_pmin_anchor(self):
        mdot_min = cg.choked_mass_flow(
            P_MIN, T, math.pi * D ** 2 / 4.0)
        self.assertAlmostEqual(cg.thrust(mdot_min, ISP), 0.581,
                               delta=0.01)


class ColdGasThrusterScalingTest(unittest.TestCase):
    """Round trips and model shape checks."""

    def _tau(self):
        mdot = cg.choked_mass_flow(P0, T, math.pi * D ** 2 / 4.0)
        return cg.blowdown_time_constant(
            cg.tank_gas_mass(P0, V, T), mdot)

    def test_mdot_scales_linearly_with_pressure(self):
        base = cg.choked_mass_flow(P0, T, math.pi * D ** 2 / 4.0)
        doubled = cg.choked_mass_flow(
            2.0 * P0, T, math.pi * D ** 2 / 4.0)
        self.assertAlmostEqual(doubled, 2.0 * base, delta=1e-9)
        half = cg.choked_mass_flow(
            0.5 * P0, T, math.pi * D ** 2 / 4.0)
        self.assertAlmostEqual(half, 0.5 * base, delta=1e-9)

    def test_tank_gas_mass_scales_with_pressure(self):
        self.assertAlmostEqual(
            cg.tank_gas_mass(2.0 * P0, V, T),
            2.0 * cg.tank_gas_mass(P0, V, T), delta=1e-9)

    def test_isothermal_pressure_decay_shape(self):
        tau = self._tau()
        p_at_tau = cg.pressure_at_time(P0, tau, tau)
        self.assertAlmostEqual(p_at_tau, P0 / math.e, delta=1.0)
        p_at_2tau = cg.pressure_at_time(P0, 2.0 * tau, tau)
        self.assertAlmostEqual(p_at_2tau, P0 / math.e ** 2, delta=1.0)

    def test_pressure_decay_is_monotonic(self):
        tau = self._tau()
        early = cg.pressure_at_time(P0, 100.0, tau)
        late = cg.pressure_at_time(P0, 1000.0, tau)
        self.assertGreater(early, late)
        self.assertGreater(early, P_MIN)

    def test_pressure_at_zero_time_is_p0(self):
        tau = self._tau()
        self.assertAlmostEqual(
            cg.pressure_at_time(P0, 0.0, tau), P0, delta=1e-6)

    def test_thrust_identity(self):
        mdot = cg.choked_mass_flow(P0, T, math.pi * D ** 2 / 4.0)
        self.assertAlmostEqual(
            cg.thrust(mdot, ISP), mdot * ISP * cg.G0, delta=1e-9)

    def test_nitrogen_defaults_match_explicit_gas(self):
        area = math.pi * D ** 2 / 4.0
        default = cg.choked_mass_flow(P0, T, area)
        explicit = cg.choked_mass_flow(
            P0, T, area, gamma=cg.GAMMA_N2, gas_const=cg.R_N2)
        self.assertEqual(default, explicit)

    def test_size_thruster_full_chain(self):
        res = cg.size_thruster(P0, V, T, D, ISP, P_MIN)
        expected_keys = {
            "throat_area", "mass_flow0", "thrust_N", "tank_mass_kg",
            "time_constant_s", "pressure_at_tquery",
            "operating_time_s", "total_impulse_Ns", "mass_at_pmin"}
        self.assertEqual(set(res), expected_keys)
        self.assertAlmostEqual(res["throat_area"], 1.9635e-7,
                               delta=1e-12)
        self.assertAlmostEqual(res["mass_flow0"], 0.011398, delta=1e-5)
        self.assertAlmostEqual(res["thrust_N"], 7.265, delta=0.01)
        self.assertAlmostEqual(res["tank_mass_kg"], 8.6244,
                               delta=0.001)
        self.assertAlmostEqual(res["time_constant_s"], 756.7,
                               delta=0.5)
        self.assertAlmostEqual(res["pressure_at_tquery"] / 1e6,
                               24.028, delta=0.01)
        self.assertAlmostEqual(res["operating_time_s"], 1911.1,
                               delta=1.0)
        self.assertAlmostEqual(res["total_impulse_Ns"], 5057.7,
                               delta=1.0)
        self.assertAlmostEqual(res["mass_at_pmin"], 0.68995,
                               delta=0.001)


class ColdGasThrusterValueErrorTest(unittest.TestCase):
    """Non-physical inputs are rejected."""

    def test_choked_mass_flow_zero_pressure(self):
        with self.assertRaises(ValueError):
            cg.choked_mass_flow(0.0, T, math.pi * D ** 2 / 4.0)

    def test_choked_mass_flow_zero_temperature(self):
        with self.assertRaises(ValueError):
            cg.choked_mass_flow(P0, 0.0, math.pi * D ** 2 / 4.0)

    def test_choked_mass_flow_zero_throat_area(self):
        with self.assertRaises(ValueError):
            cg.choked_mass_flow(P0, T, 0.0)

    def test_thrust_zero_isp(self):
        with self.assertRaises(ValueError):
            cg.thrust(0.01, 0.0)

    def test_thrust_negative_mass_flow(self):
        with self.assertRaises(ValueError):
            cg.thrust(-1.0, ISP)

    def test_tank_gas_mass_zero_pressure_and_volume(self):
        with self.assertRaises(ValueError):
            cg.tank_gas_mass(0.0, V, T)
        with self.assertRaises(ValueError):
            cg.tank_gas_mass(P0, 0.0, T)

    def test_blowdown_time_constant_zero_flow(self):
        with self.assertRaises(ValueError):
            cg.blowdown_time_constant(8.6, 0.0)

    def test_pressure_at_time_negative_time_and_tau(self):
        with self.assertRaises(ValueError):
            cg.pressure_at_time(P0, -1.0, 756.7)
        with self.assertRaises(ValueError):
            cg.pressure_at_time(P0, 10.0, 0.0)

    def test_operating_time_pmin_above_p0(self):
        with self.assertRaises(ValueError):
            cg.operating_time(P0, 30e6, 756.7)
        with self.assertRaises(ValueError):
            cg.operating_time(P0, 0.0, 756.7)

    def test_total_impulse_final_mass_above_initial(self):
        with self.assertRaises(ValueError):
            cg.total_impulse(ISP, 1.0, 2.0)

    def test_size_thruster_negative_tquery_and_bad_pmin(self):
        with self.assertRaises(ValueError):
            cg.size_thruster(P0, V, T, D, ISP, P_MIN, t_query=-5.0)
        with self.assertRaises(ValueError):
            cg.size_thruster(P0, V, T, D, ISP, 30e6)
        with self.assertRaises(ValueError):
            cg.size_thruster(P0, V, T, 0.0, ISP, P_MIN)


if __name__ == "__main__":
    unittest.main()
