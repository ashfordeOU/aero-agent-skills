"""Contract test for rocket_turbopump_logic (rocket-turbopump leaf).

Deterministic, offline, stdlib only. Run: python3 test_rocket_turbopump.py
Covers the LOX worked-example anchors, scaling and round-trip
identities, the verdict boundary and flip, and ValueError rejection of
non-physical inputs.
"""

import math
import unittest

import rocket_turbopump_logic as rtl

G0 = rtl.G0
OMEGA = rtl.omega_from_rpm(18000)  # 1884.9556 rad/s


class TestOmegaConversion(unittest.TestCase):
    def test_omega_anchor_18000_rpm(self):
        self.assertAlmostEqual(rtl.omega_from_rpm(18000), 1884.96, delta=0.1)

    def test_omega_exact_scale(self):
        # 3000 rpm is 50 rev/s, exactly 100 * pi rad/s.
        self.assertAlmostEqual(rtl.omega_from_rpm(3000), 100.0 * math.pi,
                               places=9)

    def test_omega_linear_in_rpm(self):
        self.assertAlmostEqual(
            rtl.omega_from_rpm(9000), OMEGA / 2.0, places=9)


class TestHeadRise(unittest.TestCase):
    def test_head_rise_anchor_lox(self):
        self.assertAlmostEqual(rtl.head_rise_m(10e6, 1141), 893.70, delta=0.1)

    def test_head_rise_round_trip(self):
        head = rtl.head_rise_m(10e6, 1141)
        self.assertAlmostEqual(head * 1141 * G0, 10e6, places=3)

    def test_head_rise_linear_in_pressure_difference(self):
        self.assertAlmostEqual(
            rtl.head_rise_m(20e6, 1141), 2.0 * rtl.head_rise_m(10e6, 1141),
            places=9)


class TestSpecificSpeed(unittest.TestCase):
    def test_specific_speed_anchor(self):
        self.assertAlmostEqual(rtl.specific_speed(1884.96, 0.04, 893.70),
                               0.4162, delta=0.001)

    def test_specific_speed_proportional_to_omega(self):
        s_high = rtl.specific_speed(OMEGA, 0.04, 893.70)
        s_low = rtl.specific_speed(OMEGA / 2.0, 0.04, 893.70)
        self.assertAlmostEqual(s_high / s_low, 2.0, places=9)

    def test_specific_speed_scales_with_sqrt_flow(self):
        s_high = rtl.specific_speed(OMEGA, 0.04, 893.70)
        s_low = rtl.specific_speed(OMEGA, 0.01, 893.70)
        self.assertAlmostEqual(s_high / s_low, 2.0, places=9)


class TestImpellerGeometry(unittest.TestCase):
    def test_tip_speed_anchor(self):
        self.assertAlmostEqual(rtl.impeller_tip_speed(893.70, 0.55),
                               126.23, delta=0.1)

    def test_tip_speed_scales_with_sqrt_head(self):
        u1 = rtl.impeller_tip_speed(893.70)
        u4 = rtl.impeller_tip_speed(4.0 * 893.70)
        self.assertAlmostEqual(u4 / u1, 2.0, places=9)

    def test_diameter_anchor(self):
        self.assertAlmostEqual(rtl.impeller_diameter(126.23, 1884.96),
                               0.1339, delta=0.001)

    def test_diameter_inversely_proportional_to_omega(self):
        d_high = rtl.impeller_diameter(126.23, OMEGA)
        d_low = rtl.impeller_diameter(126.23, OMEGA / 2.0)
        self.assertAlmostEqual(d_low / d_high, 2.0, places=9)

    def test_diameter_round_trip_tip_speed(self):
        d = rtl.impeller_diameter(126.23, OMEGA)
        self.assertAlmostEqual(OMEGA * d / 2.0, 126.23, places=6)


class TestPumpPower(unittest.TestCase):
    def test_pump_power_anchor(self):
        self.assertAlmostEqual(rtl.pump_power(0.04, 10e6, 0.68),
                               588235, delta=10)

    def test_pump_power_proportional_to_flow(self):
        p1 = rtl.pump_power(0.04, 10e6, 0.68)
        p2 = rtl.pump_power(0.08, 10e6, 0.68)
        self.assertAlmostEqual(p2 / p1, 2.0, places=9)

    def test_pump_power_inversely_proportional_to_efficiency(self):
        p1 = rtl.pump_power(0.04, 10e6, 0.68)
        p2 = rtl.pump_power(0.04, 10e6, 1.0)
        self.assertAlmostEqual(p2 * 1.0, 0.04 * 10e6, places=3)
        self.assertAlmostEqual(p1 * 0.68, p2, places=3)


class TestSuctionPerformance(unittest.TestCase):
    def test_npsh_anchor(self):
        self.assertAlmostEqual(rtl.npsh_available(0.5e6, 0.03e6, 1141),
                               42.00, delta=0.01)

    def test_npsh_linear_in_pressure_difference(self):
        npsh = rtl.npsh_available(0.5e6, 0.03e6, 1141)
        npsh_warm = rtl.npsh_available(0.5e6, 0.2e6, 1141)
        self.assertAlmostEqual(npsh - npsh_warm,
                               0.17e6 / (1141 * G0), places=9)

    def test_suction_specific_speed_anchor(self):
        self.assertAlmostEqual(
            rtl.suction_specific_speed(1884.96, 0.04, 42.00),
            4.123, delta=0.01)

    def test_suction_specific_speed_grows_as_npsh_falls(self):
        s_high = rtl.suction_specific_speed(OMEGA, 0.04, 42.00)
        s_low = rtl.suction_specific_speed(OMEGA, 0.04, 42.00 / 4.0)
        # Quartering the NPSH shrinks the (G0*NPSH)**0.75 denominator by
        # 4**0.75, so S grows by the same factor.
        self.assertAlmostEqual(s_low / s_high, 4.0 ** 0.75, places=9)


class TestCavitationVerdict(unittest.TestCase):
    def test_verdict_flips_below_s_crit(self):
        self.assertEqual(rtl.cavitation_verdict(4.123), "acceptable")
        self.assertEqual(rtl.cavitation_verdict(3.0), "acceptable")
        self.assertEqual(rtl.cavitation_verdict(2.999), "cavitation-risk")
        self.assertEqual(rtl.cavitation_verdict(1.9), "cavitation-risk")

    def test_verdict_honors_custom_s_crit(self):
        self.assertEqual(rtl.cavitation_verdict(4.123, s_crit=4.5),
                         "cavitation-risk")
        self.assertEqual(rtl.cavitation_verdict(4.123, s_crit=2.0),
                         "acceptable")


class TestSizePumpChain(unittest.TestCase):
    def test_size_pump_anchor_chain(self):
        res = rtl.size_pump(18000, 0.04, 10e6, 1141, 0.68, 0.5e6, 0.03e6)
        self.assertAlmostEqual(res["omega"], 1884.96, delta=0.1)
        self.assertAlmostEqual(res["head_m"], 893.70, delta=0.1)
        self.assertAlmostEqual(res["specific_speed"], 0.4162, delta=0.001)
        self.assertAlmostEqual(res["tip_speed_ms"], 126.23, delta=0.1)
        self.assertAlmostEqual(res["diameter_m"], 0.1339, delta=0.001)
        self.assertAlmostEqual(res["power_W"], 588235, delta=10)
        self.assertAlmostEqual(res["npsh_m"], 42.00, delta=0.01)
        self.assertAlmostEqual(res["suction_specific_speed"], 4.123,
                               delta=0.01)
        self.assertEqual(res["verdict"], "acceptable")

    def test_size_pump_flip_case_to_cavitation_risk(self):
        # Inlet pressure raised to 1.0 MPa pushes the available NPSH to
        # about 86.7 m, where the suction specific speed drops below the
        # 3.0 limit and the verdict flips.
        res = rtl.size_pump(18000, 0.04, 10e6, 1141, 0.68, 1.0e6, 0.03e6)
        self.assertAlmostEqual(res["npsh_m"], 86.69, delta=0.01)
        self.assertLess(res["suction_specific_speed"], 3.0)
        self.assertAlmostEqual(res["suction_specific_speed"], 2.3945,
                               delta=0.001)
        self.assertEqual(res["verdict"], "cavitation-risk")

    def test_size_pump_agrees_with_individual_functions(self):
        rpm, q, dp, rho, eta, pin, pv = 18000, 0.04, 10e6, 1141, 0.68, \
            0.5e6, 0.03e6
        res = rtl.size_pump(rpm, q, dp, rho, eta, pin, pv)
        omega = rtl.omega_from_rpm(rpm)
        self.assertEqual(res["omega"], omega)
        self.assertEqual(res["head_m"], rtl.head_rise_m(dp, rho))
        self.assertEqual(res["specific_speed"],
                         rtl.specific_speed(omega, q, res["head_m"]))
        self.assertEqual(res["tip_speed_ms"],
                         rtl.impeller_tip_speed(res["head_m"]))
        self.assertEqual(res["diameter_m"],
                         rtl.impeller_diameter(res["tip_speed_ms"], omega))
        self.assertEqual(res["power_W"], rtl.pump_power(q, dp, eta))
        self.assertEqual(res["npsh_m"],
                         rtl.npsh_available(pin, pv, rho))
        self.assertEqual(res["suction_specific_speed"],
                         rtl.suction_specific_speed(omega, q, res["npsh_m"]))
        self.assertEqual(res["verdict"], "acceptable")


class TestValueErrorRejection(unittest.TestCase):
    def test_valueerror_rpm_nonpositive(self):
        for rpm in (0, -18000):
            with self.assertRaises(ValueError):
                rtl.omega_from_rpm(rpm)

    def test_valueerror_volume_flow_nonpositive(self):
        for q in (0, -0.04):
            with self.assertRaises(ValueError):
                rtl.specific_speed(OMEGA, q, 893.70)
            with self.assertRaises(ValueError):
                rtl.pump_power(q, 10e6, 0.68)
            with self.assertRaises(ValueError):
                rtl.suction_specific_speed(OMEGA, q, 42.00)

    def test_valueerror_pressure_rise_nonpositive(self):
        for dp in (0, -10e6):
            with self.assertRaises(ValueError):
                rtl.head_rise_m(dp, 1141)
            with self.assertRaises(ValueError):
                rtl.pump_power(0.04, dp, 0.68)

    def test_valueerror_density_nonpositive(self):
        for rho in (0, -1141):
            with self.assertRaises(ValueError):
                rtl.head_rise_m(10e6, rho)
            with self.assertRaises(ValueError):
                rtl.npsh_available(0.5e6, 0.03e6, rho)

    def test_valueerror_efficiency_out_of_range(self):
        for eta in (0, -0.5, 1.2):
            with self.assertRaises(ValueError):
                rtl.pump_power(0.04, 10e6, eta)

    def test_valueerror_inlet_at_or_below_vapor_pressure(self):
        with self.assertRaises(ValueError):
            rtl.npsh_available(0.03e6, 0.03e6, 1141)
        with self.assertRaises(ValueError):
            rtl.npsh_available(0.02e6, 0.5e6, 1141)

    def test_valueerror_geometry_inputs_nonpositive(self):
        for psi in (0, -0.55):
            with self.assertRaises(ValueError):
                rtl.impeller_tip_speed(893.70, psi)
        for h in (0, -893.70):
            with self.assertRaises(ValueError):
                rtl.impeller_tip_speed(h)
            with self.assertRaises(ValueError):
                rtl.specific_speed(OMEGA, 0.04, h)
        for n in (0, -42.00):
            with self.assertRaises(ValueError):
                rtl.suction_specific_speed(OMEGA, 0.04, n)
        with self.assertRaises(ValueError):
            rtl.impeller_diameter(126.23, 0)
        with self.assertRaises(ValueError):
            rtl.suction_specific_speed(-1.0, 0.04, 42.00)

    def test_valueerror_propagates_through_size_pump(self):
        with self.assertRaises(ValueError):
            rtl.size_pump(0, 0.04, 10e6, 1141, 0.68, 0.5e6, 0.03e6)
        with self.assertRaises(ValueError):
            rtl.size_pump(18000, 0.04, 10e6, 1141, 0.0, 0.5e6, 0.03e6)
        with self.assertRaises(ValueError):
            rtl.size_pump(18000, 0.04, 10e6, 1141, 0.68, 0.01e6, 0.03e6)


if __name__ == "__main__":
    unittest.main()
