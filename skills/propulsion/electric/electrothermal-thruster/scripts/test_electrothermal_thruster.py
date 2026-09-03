"""Contract tests for electrothermal_thruster_logic.py (wave-24R).

Runs offline, stdlib unittest only: python3 test_electrothermal_thruster.py
Anchors the resistojet worked example from the leaf spec: P_elec 1000 W,
NH3, T_0 1200 K, T_in 300 K, eta_heat 0.85, eta_nozzle 0.9 giving
P_heat 850 W, mdot 4.52e-4 kg/s, v_e 2125 m/s, F 0.96 N, Isp 217 s and
the ideal thrust-efficiency identity eta_t = eta_heat * eta_nozzle.
"""

import math
import unittest

from electrothermal_thruster_logic import (
    ARCJET_ISP_BAND,
    RESISTOJET_ISP_BAND,
    electrothermal_performance,
    exhaust_velocity_ideal,
    mass_flow_from_heating,
    operating_band_verdict,
    propellant_properties,
    specific_impulse,
    thrust_efficiency,
    thrust_from_mass_flow,
    thrust_to_power,
    useful_heating_power,
)

P_ELEC = 1000.0
T0 = 1200.0
T_IN = 300.0
ETA_HEAT = 0.85
ETA_NOZZLE = 0.9
CP_NH3 = 2090.0


class TestHeating(unittest.TestCase):
    def test_useful_heating_power_anchor(self):
        self.assertAlmostEqual(useful_heating_power(0.85, 1000.0), 850.0, places=6)

    def test_useful_heating_power_linear(self):
        self.assertAlmostEqual(useful_heating_power(0.7, 500.0), 350.0, places=6)

    def test_mass_flow_anchor(self):
        mdot = mass_flow_from_heating(850.0, CP_NH3, 1200.0, 300.0)
        self.assertAlmostEqual(mdot, 4.52e-4, delta=1e-6)

    def test_mass_flow_scales_with_power(self):
        m1 = mass_flow_from_heating(850.0, CP_NH3, 1200.0, 300.0)
        m2 = mass_flow_from_heating(1700.0, CP_NH3, 1200.0, 300.0)
        self.assertAlmostEqual(m2 / m1, 2.0, places=9)

    def test_mass_flow_inverse_cp(self):
        m_nh3 = mass_flow_from_heating(850.0, 2090.0, 1200.0, 300.0)
        m_n2 = mass_flow_from_heating(850.0, 1040.0, 1200.0, 300.0)
        self.assertGreater(m_n2, m_nh3)


class TestExhaustAndThrust(unittest.TestCase):
    def test_exhaust_velocity_anchor(self):
        v_e = exhaust_velocity_ideal(CP_NH3, ETA_NOZZLE, T0)
        self.assertAlmostEqual(v_e, 2125.0, delta=1.0)

    def test_sqrt_t0_scaling(self):
        v1 = exhaust_velocity_ideal(CP_NH3, ETA_NOZZLE, 1200.0)
        v2 = exhaust_velocity_ideal(CP_NH3, ETA_NOZZLE, 4800.0)
        self.assertAlmostEqual(v2 / v1, 2.0, places=6)

    def test_specific_impulse_anchor(self):
        v_e = exhaust_velocity_ideal(CP_NH3, ETA_NOZZLE, T0)
        self.assertAlmostEqual(specific_impulse(v_e), 217.0, delta=1.0)

    def test_thrust_from_mass_flow_anchor(self):
        mdot = mass_flow_from_heating(850.0, CP_NH3, 1200.0, 300.0)
        v_e = exhaust_velocity_ideal(CP_NH3, ETA_NOZZLE, 1200.0)
        f = thrust_from_mass_flow(mdot, v_e)
        self.assertAlmostEqual(f, 0.96, delta=0.01)
        self.assertAlmostEqual(f * 1000.0, 960.0, delta=10.0)

    def test_thrust_linear_in_mass_flow(self):
        mdot = mass_flow_from_heating(850.0, CP_NH3, 1200.0, 300.0)
        v_e = exhaust_velocity_ideal(CP_NH3, ETA_NOZZLE, 1200.0)
        f1 = thrust_from_mass_flow(mdot, v_e)
        f2 = thrust_from_mass_flow(2.0 * mdot, v_e)
        self.assertAlmostEqual(f2 / f1, 2.0, places=9)


class TestEfficiency(unittest.TestCase):
    def test_thrust_efficiency_identity(self):
        # Ideal-model identity including inlet plenum enthalpy: the
        # vacuum exhaust velocity credits the full chamber enthalpy
        # cp*T0, of which cp*T_in entered with the flow, so
        # eta_t = eta_heat * eta_nozzle * T0 / (T0 - T_in). At the
        # anchor: 0.85 * 0.9 * 1200 / 900 = 1.02 exactly.
        mdot = mass_flow_from_heating(850.0, CP_NH3, 1200.0, 300.0)
        v_e = exhaust_velocity_ideal(CP_NH3, ETA_NOZZLE, 1200.0)
        f = thrust_from_mass_flow(mdot, v_e)
        eta_t = thrust_efficiency(f, mdot, 1000.0)
        self.assertAlmostEqual(
            eta_t, ETA_HEAT * ETA_NOZZLE * T0 / (T0 - T_IN), places=6
        )

    def test_thrust_to_power_anchor(self):
        mdot = mass_flow_from_heating(850.0, CP_NH3, 1200.0, 300.0)
        v_e = exhaust_velocity_ideal(CP_NH3, ETA_NOZZLE, 1200.0)
        f = thrust_from_mass_flow(mdot, v_e)
        tp = thrust_to_power(f, 1000.0)
        self.assertAlmostEqual(tp * 1e6, 960.0, delta=10.0)

    def test_efficiency_below_one_at_moderate_nozzle(self):
        # With eta_nozzle = 0.5 the jet-power efficiency stays below
        # one: 0.85 * 0.5 * 1200 / 900 = 0.5667.
        r = electrothermal_performance(1000.0, 1200.0, 300.0, "NH3",
                                       eta_heat=0.85, eta_nozzle=0.5)
        self.assertLessEqual(r["thrust_efficiency"], 1.0)
        self.assertAlmostEqual(r["thrust_efficiency"],
                               0.85 * 0.5 * 1200.0 / 900.0, places=6)


class TestOperatingPoint(unittest.TestCase):
    def test_performance_summary_keys(self):
        r = electrothermal_performance(1000.0, 1200.0, 300.0, "NH3")
        for key in ("mass_flow", "exhaust_velocity", "thrust",
                    "specific_impulse", "thrust_efficiency",
                    "thrust_to_power_mn_kw", "p_heat", "band_verdict"):
            self.assertIn(key, r)

    def test_performance_resistojet_anchor(self):
        r = electrothermal_performance(1000.0, 1200.0, 300.0, "NH3",
                                       eta_heat=0.85, eta_nozzle=0.9,
                                       family="resistojet")
        self.assertAlmostEqual(r["p_heat"], 850.0, places=6)
        self.assertAlmostEqual(r["mass_flow"], 4.52e-4, delta=1e-6)
        self.assertAlmostEqual(r["exhaust_velocity"], 2125.0, delta=1.0)
        self.assertAlmostEqual(r["thrust"], 0.96, delta=0.01)
        self.assertAlmostEqual(r["specific_impulse"], 217.0, delta=1.0)
        # eta_t = eta_heat * eta_nozzle * T0 / (T0 - T_in) = 1.02 at
        # the anchor (inlet-enthalpy-corrected ideal identity).
        self.assertAlmostEqual(
            r["thrust_efficiency"],
            r["eta_heat"] * r["eta_nozzle"] * T0 / (T0 - T_IN), places=6
        )
        self.assertIn("inside", r["band_verdict"])

    def test_higher_t0_higher_isp(self):
        r1 = electrothermal_performance(1000.0, 1200.0, 300.0, "NH3")
        r2 = electrothermal_performance(1000.0, 1500.0, 300.0, "NH3")
        self.assertGreater(r2["specific_impulse"], r1["specific_impulse"])

    def test_arcjet_defaults_lower_eta_heat(self):
        r = electrothermal_performance(500.0, 1800.0, 300.0, "N2",
                                       family="arcjet")
        self.assertAlmostEqual(r["eta_heat"], 0.7, places=6)

    def test_arcjet_higher_isp_than_resistojet(self):
        rr = electrothermal_performance(500.0, 1200.0, 300.0, "NH3",
                                        family="resistojet")
        ra = electrothermal_performance(500.0, 2200.0, 300.0, "NH3",
                                        family="arcjet")
        self.assertGreater(ra["specific_impulse"], rr["specific_impulse"])


class TestPropellantsAndBands(unittest.TestCase):
    def test_propellant_table_values(self):
        self.assertEqual(propellant_properties("NH3"), (2090.0, 1.31))
        self.assertEqual(propellant_properties("N2"), (1040.0, 1.40))
        self.assertEqual(propellant_properties("H2"), (14300.0, 1.41))
        self.assertEqual(propellant_properties("He"), (5190.0, 1.67))

    def test_resistojet_band_constants(self):
        self.assertEqual(RESISTOJET_ISP_BAND, (200.0, 350.0))
        self.assertEqual(ARCJET_ISP_BAND, (400.0, 700.0))

    def test_band_verdict_inside_and_outside(self):
        self.assertIn("inside", operating_band_verdict(217.0, "resistojet"))
        self.assertIn("outside", operating_band_verdict(500.0, "resistojet"))
        self.assertIn("inside", operating_band_verdict(500.0, "arcjet"))


class TestValueErrors(unittest.TestCase):
    def test_power_nonpositive(self):
        with self.assertRaises(ValueError):
            electrothermal_performance(0.0, 1200.0, 300.0, "NH3")
        with self.assertRaises(ValueError):
            electrothermal_performance(-100.0, 1200.0, 300.0, "NH3")

    def test_temperature_order(self):
        with self.assertRaises(ValueError):
            electrothermal_performance(1000.0, 300.0, 300.0, "NH3")
        with self.assertRaises(ValueError):
            electrothermal_performance(1000.0, 200.0, 300.0, "NH3")

    def test_unknown_propellant_and_family(self):
        with self.assertRaises(ValueError):
            propellant_properties("Xe")
        with self.assertRaises(ValueError):
            electrothermal_performance(1000.0, 1200.0, 300.0, "argon")
        with self.assertRaises(ValueError):
            electrothermal_performance(1000.0, 1200.0, 300.0, "NH3",
                                       family="ion")

    def test_eta_out_of_range(self):
        with self.assertRaises(ValueError):
            useful_heating_power(0.0, 1000.0)
        with self.assertRaises(ValueError):
            useful_heating_power(1.5, 1000.0)
        with self.assertRaises(ValueError):
            exhaust_velocity_ideal(2090.0, 0.0, 1200.0)
        with self.assertRaises(ValueError):
            exhaust_velocity_ideal(2090.0, 1.5, 1200.0)

    def test_nonfinite_inputs(self):
        with self.assertRaises(ValueError):
            electrothermal_performance(float("nan"), 1200.0, 300.0, "NH3")
        with self.assertRaises(ValueError):
            useful_heating_power(float("inf"), 1000.0)
        with self.assertRaises(ValueError):
            operating_band_verdict(float("nan"), "resistojet")


if __name__ == "__main__":
    unittest.main()
