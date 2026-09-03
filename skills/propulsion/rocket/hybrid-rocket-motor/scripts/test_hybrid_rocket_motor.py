"""Contract test for hybrid_rocket_motor_logic (hybrid-rocket-motor leaf).

Deterministic, offline, stdlib only. Run: python3 test_hybrid_rocket_motor.py
"""

import math
import unittest

import hybrid_rocket_motor_logic as hrm

G0 = hrm.G0

# Worked example inputs: lab-scale HTPB/N2O hybrid, oxidizer flow 0.3 kg/s,
# initial port diameter 40 mm, grain length 600 mm, throat sized for 3.0 MPa
# at ignition.
M_DOT_O = 0.3
R_INITIAL = 0.02
R_FINAL = 0.03
LENGTH = 0.6
FUEL = "HTPB-N2O"
# Throat area sized so the initial station sits at 3.0 MPa.
PROPS_N2O = hrm.fuel_properties("HTPB-N2O")
AREA_THROAT = (M_DOT_O + PROPS_N2O["rho_f"] * hrm.regression_rate(
    M_DOT_O / hrm.port_area_circular(R_INITIAL), FUEL) *
    hrm.burn_area_cylindrical(R_INITIAL, LENGTH)) * PROPS_N2O["c_star"] / 3.0e6


def assert_close(test, actual, expected, rel=1.0e-9):
    test.assertAlmostEqual(actual / expected, 1.0, delta=rel)


class TestFuelRegistry(unittest.TestCase):
    def test_htpb_n2o_properties(self):
        props = hrm.fuel_properties("HTPB-N2O")
        self.assertEqual(props["a"], 1.2e-4)
        self.assertEqual(props["n"], 0.55)
        self.assertEqual(props["m"], -0.20)
        self.assertEqual(props["L_ref"], 0.6)
        self.assertEqual(props["rho_f"], 920.0)
        self.assertEqual(props["c_star"], 1500.0)

    def test_htpb_lox_properties(self):
        props = hrm.fuel_properties("HTPB-LOX")
        self.assertEqual(props["a"], 1.8e-4)
        self.assertEqual(props["n"], 0.50)
        self.assertEqual(props["m"], -0.15)
        self.assertEqual(props["c_star"], 1750.0)

    def test_unknown_fuel_raises(self):
        for bad in ("HTPB", "N2O", "polyurethane", "", None, 3):
            with self.assertRaises(ValueError):
                hrm.fuel_properties(bad)
            with self.assertRaises(ValueError):
                hrm.regression_rate(100.0, bad)


class TestRegressionRate(unittest.TestCase):
    def test_worked_example_rate(self):
        g_o0 = hrm.oxidizer_mass_flux(M_DOT_O,
                                      hrm.port_area_circular(R_INITIAL))
        self.assertAlmostEqual(g_o0, 238.73241463784296, places=9)
        r_dot = hrm.regression_rate(g_o0, FUEL)
        assert_close(self, r_dot, 2.437993317732393e-3)
        # Reference length form equals the plain form at L_ref.
        assert_close(self, hrm.regression_rate_at_length(g_o0, FUEL, LENGTH),
                     r_dot)

    def test_rate_monotone_in_flux(self):
        r1 = hrm.regression_rate(100.0, FUEL)
        r2 = hrm.regression_rate(300.0, FUEL)
        self.assertGreater(r2, r1)
        self.assertGreater(r1, 0.0)

    def test_rate_power_law_scaling(self):
        g = 150.0
        r_dot = hrm.regression_rate(g, FUEL)
        assert_close(self, hrm.regression_rate(2.0 * g, FUEL) / r_dot,
                     2.0 ** 0.55)

    def test_rate_length_scaling(self):
        g = 200.0
        base = hrm.regression_rate(g, FUEL)
        longer = hrm.regression_rate_at_length(g, FUEL, 1.2)
        # (1.2 / 0.6) ** -0.20 = 2 ** -0.20
        assert_close(self, longer / base, 2.0 ** -0.20)

    def test_nonpositive_flux_raises(self):
        for bad in (0.0, -10.0, float("nan"), float("inf")):
            with self.assertRaises(ValueError):
                hrm.regression_rate(bad, FUEL)
        with self.assertRaises(ValueError):
            hrm.regression_rate_at_length(100.0, FUEL, 0.0)
        with self.assertRaises(ValueError):
            hrm.regression_rate_at_length(100.0, FUEL, -0.5)


class TestFluxAndAreas(unittest.TestCase):
    def test_worked_example_flux(self):
        area = hrm.port_area_circular(R_INITIAL)
        self.assertAlmostEqual(area, 0.0012566370614359175, places=12)
        assert_close(self, hrm.oxidizer_mass_flux(M_DOT_O, area),
                     238.73241463784296)

    def test_flux_identity(self):
        for m_dot_o, area in ((0.5, 2.0e-3), (0.1, 5.0e-4), (2.0, 1.0e-2)):
            g = hrm.oxidizer_mass_flux(m_dot_o, area)
            assert_close(self, g * area, m_dot_o)

    def test_port_area_values(self):
        self.assertAlmostEqual(hrm.port_area_circular(0.02),
                               0.0012566370614359175, places=12)
        self.assertAlmostEqual(hrm.port_area_circular(0.03),
                               0.0028274333882308137, places=12)

    def test_burn_area_values(self):
        self.assertAlmostEqual(hrm.burn_area_cylindrical(0.02, 0.6),
                               0.07539822368615504, places=12)
        self.assertAlmostEqual(hrm.burn_area_cylindrical(0.03, 0.6),
                               0.11309733552923254, places=12)

    def test_area_value_errors(self):
        with self.assertRaises(ValueError):
            hrm.port_area_circular(0.0)
        with self.assertRaises(ValueError):
            hrm.port_area_circular(-1.0)
        with self.assertRaises(ValueError):
            hrm.burn_area_cylindrical(0.02, 0.0)
        with self.assertRaises(ValueError):
            hrm.oxidizer_mass_flux(0.0, 1.0e-3)
        with self.assertRaises(ValueError):
            hrm.oxidizer_mass_flux(0.3, 0.0)
        with self.assertRaises(ValueError):
            hrm.oxidizer_mass_flux(0.3, -1.0e-3)


class TestFuelFlowAndOF(unittest.TestCase):
    def test_worked_example_fuel_flow(self):
        r_dot = hrm.regression_rate_at_length(
            hrm.oxidizer_mass_flux(M_DOT_O, hrm.port_area_circular(R_INITIAL)),
            FUEL, LENGTH)
        m_dot_f = hrm.fuel_mass_flow(PROPS_N2O["rho_f"], r_dot,
                                     hrm.burn_area_cylindrical(R_INITIAL,
                                                               LENGTH))
        self.assertAlmostEqual(m_dot_f, 0.16911473627447918, places=9)

    def test_worked_example_of(self):
        r_dot = hrm.regression_rate_at_length(
            hrm.oxidizer_mass_flux(M_DOT_O, hrm.port_area_circular(R_INITIAL)),
            FUEL, LENGTH)
        m_dot_f = hrm.fuel_mass_flow(PROPS_N2O["rho_f"], r_dot,
                                     hrm.burn_area_cylindrical(R_INITIAL,
                                                               LENGTH))
        self.assertAlmostEqual(hrm.of_ratio(M_DOT_O, m_dot_f),
                               1.7739435758755489, places=9)

    def test_of_identity(self):
        m_dot_f = 0.15
        of = hrm.of_ratio(M_DOT_O, m_dot_f)
        assert_close(self, of * m_dot_f, M_DOT_O)

    def test_fuel_flow_value_errors(self):
        with self.assertRaises(ValueError):
            hrm.fuel_mass_flow(0.0, 1.0e-3, 0.1)
        with self.assertRaises(ValueError):
            hrm.fuel_mass_flow(920.0, -1.0e-3, 0.1)
        with self.assertRaises(ValueError):
            hrm.fuel_mass_flow(920.0, 1.0e-3, -0.1)
        with self.assertRaises(ValueError):
            hrm.of_ratio(0.0, 0.1)
        with self.assertRaises(ValueError):
            hrm.of_ratio(M_DOT_O, 0.0)


class TestChamberAndThrust(unittest.TestCase):
    def test_worked_example_chamber_pressure(self):
        m_dot_f = hrm.fuel_mass_flow(
            PROPS_N2O["rho_f"],
            hrm.regression_rate_at_length(
                hrm.oxidizer_mass_flux(M_DOT_O,
                                       hrm.port_area_circular(R_INITIAL)),
                FUEL, LENGTH),
            hrm.burn_area_cylindrical(R_INITIAL, LENGTH))
        p_c = hrm.chamber_pressure(M_DOT_O + m_dot_f, PROPS_N2O["c_star"],
                                   AREA_THROAT)
        self.assertAlmostEqual(p_c, 3.0e6, places=0)

    def test_pressure_identity(self):
        for m_dot, c_star, a_t in ((0.5, 1500.0, 2.5e-4),
                                   (0.3, 1750.0, 1.5e-4)):
            p_c = hrm.chamber_pressure(m_dot, c_star, a_t)
            assert_close(self, p_c * a_t / c_star, m_dot)

    def test_worked_example_thrust(self):
        m_dot_f = hrm.fuel_mass_flow(
            PROPS_N2O["rho_f"],
            hrm.regression_rate_at_length(
                hrm.oxidizer_mass_flux(M_DOT_O,
                                       hrm.port_area_circular(R_INITIAL)),
                FUEL, LENGTH),
            hrm.burn_area_cylindrical(R_INITIAL, LENGTH))
        p_c = hrm.chamber_pressure(M_DOT_O + m_dot_f, PROPS_N2O["c_star"],
                                   AREA_THROAT)
        f = hrm.thrust(hrm.THRUST_COEFF_DEFAULT, p_c, AREA_THROAT)
        self.assertAlmostEqual(f, 985.1409461764063, places=3)

    def test_thrust_scaling(self):
        f = hrm.thrust(1.4, 3.0e6, AREA_THROAT)
        assert_close(self, hrm.thrust(1.5, 3.0e6, AREA_THROAT) / f, 1.5 / 1.4)
        assert_close(self, hrm.thrust(1.4, 6.0e6, AREA_THROAT) / f, 2.0)

    def test_chamber_thrust_value_errors(self):
        with self.assertRaises(ValueError):
            hrm.chamber_pressure(0.0, 1500.0, 2.5e-4)
        with self.assertRaises(ValueError):
            hrm.chamber_pressure(0.5, 0.0, 2.5e-4)
        with self.assertRaises(ValueError):
            hrm.chamber_pressure(0.5, 1500.0, 0.0)
        with self.assertRaises(ValueError):
            hrm.thrust(0.0, 3.0e6, 2.5e-4)
        with self.assertRaises(ValueError):
            hrm.thrust(1.4, -3.0e6, 2.5e-4)
        with self.assertRaises(ValueError):
            hrm.thrust(1.4, 3.0e6, -2.5e-4)


class TestBurnTimeImpulse(unittest.TestCase):
    def test_worked_example_burn_time(self):
        summary = hrm.hybrid_motor_summary(M_DOT_O, FUEL, R_INITIAL,
                                           R_FINAL, LENGTH, AREA_THROAT)
        self.assertAlmostEqual(summary["burn_time"], 5.242862927095063,
                               places=6)

    def test_burn_time_identity(self):
        r_dot_avg = 1.9073548439193593e-3
        t_b = hrm.burn_time(R_FINAL - R_INITIAL, r_dot_avg)
        assert_close(self, t_b, 5.242862927095063)
        assert_close(self, t_b * r_dot_avg, R_FINAL - R_INITIAL)

    def test_burn_time_value_errors(self):
        with self.assertRaises(ValueError):
            hrm.burn_time(0.0, 1.0e-3)
        with self.assertRaises(ValueError):
            hrm.burn_time(-0.01, 1.0e-3)
        with self.assertRaises(ValueError):
            hrm.burn_time(0.01, 0.0)

    def test_worked_example_impulse_and_fuel(self):
        summary = hrm.hybrid_motor_summary(M_DOT_O, FUEL, R_INITIAL,
                                           R_FINAL, LENGTH, AREA_THROAT)
        self.assertAlmostEqual(summary["total_impulse"], 5123.870746090533,
                               places=2)
        self.assertAlmostEqual(summary["fuel_consumed"], 0.8670795723907829,
                               places=9)
        # Total impulse equals the mid-burn thrust times the burn time.
        assert_close(self, summary["total_impulse"],
                     summary["mid"]["thrust"] * summary["burn_time"])
        # Fuel mass balance: average fuel flow times burn time equals the
        # fuel consumed from the port growth.
        assert_close(self, summary["mid"]["m_dot_f"] * summary["burn_time"],
                     summary["fuel_consumed"])
        self.assertEqual(summary["mass_balance_error"], 0.0)


class TestOFShift(unittest.TestCase):
    def test_worked_example_shift(self):
        shift = hrm.of_shift(M_DOT_O, FUEL, PROPS_N2O["rho_f"], R_INITIAL,
                             R_FINAL, LENGTH)
        self.assertAlmostEqual(shift["of_initial"], 1.7739435758755489,
                               places=9)
        self.assertAlmostEqual(shift["of_final"], 1.8473489069022604,
                               places=9)
        self.assertAlmostEqual(shift["shift"], 0.07340533102671154,
                               places=9)
        self.assertEqual(shift["direction"], "increases")

    def test_shift_grows_with_open_port(self):
        for r_f in (0.025, 0.035, 0.05):
            shift = hrm.of_shift(M_DOT_O, FUEL, PROPS_N2O["rho_f"],
                                 R_INITIAL, r_f, LENGTH)
            self.assertGreater(shift["of_final"], shift["of_initial"])
            self.assertEqual(shift["direction"], "increases")

    def test_flux_compensation_holds_of_flat(self):
        # For an exponent n = 0.50 the fuel flow scales as r^(1 - 2n) = r^0,
        # so the port growth compensates the flux decay exactly and the O/F
        # ratio holds flat over the burn (the HTPB/LOX record).
        shift = hrm.of_shift(M_DOT_O, "HTPB-LOX", 920.0, R_INITIAL, 0.05,
                             LENGTH)
        self.assertLess(abs(shift["shift"]), 1.0e-9)
        self.assertEqual(shift["direction"], "holds")

    def test_shift_value_errors(self):
        with self.assertRaises(ValueError):
            hrm.of_shift(M_DOT_O, FUEL, 0.0, R_INITIAL, R_FINAL, LENGTH)
        with self.assertRaises(ValueError):
            hrm.of_shift(M_DOT_O, FUEL, 920.0, 0.0, R_FINAL, LENGTH)
        with self.assertRaises(ValueError):
            hrm.of_shift(M_DOT_O, FUEL, 920.0, R_FINAL, R_FINAL, LENGTH)
        with self.assertRaises(ValueError):
            hrm.of_shift(M_DOT_O, FUEL, 920.0, R_FINAL, R_INITIAL, LENGTH)


class TestSummary(unittest.TestCase):
    def test_worked_example_summary_stations(self):
        summary = hrm.hybrid_motor_summary(M_DOT_O, FUEL, R_INITIAL,
                                           R_FINAL, LENGTH, AREA_THROAT)
        self.assertAlmostEqual(summary["initial"]["p_c"], 3.0e6, places=0)
        self.assertAlmostEqual(summary["initial"]["of"],
                               1.7739435758755489, places=9)
        self.assertAlmostEqual(summary["final"]["of"], 1.8473489069022604,
                               places=9)
        self.assertAlmostEqual(summary["final"]["p_c"], 2957026.343772793,
                               places=0)
        self.assertAlmostEqual(summary["mid"]["thrust"], 977.3039687172482,
                               places=3)

    def test_summary_pressure_decays_while_of_rises(self):
        summary = hrm.hybrid_motor_summary(M_DOT_O, FUEL, R_INITIAL,
                                           R_FINAL, LENGTH, AREA_THROAT)
        p_c = [summary[s]["p_c"] for s in ("initial", "mid", "final")]
        of = [summary[s]["of"] for s in ("initial", "mid", "final")]
        self.assertTrue(all(p_c[i] > p_c[i + 1] for i in range(2)))
        self.assertTrue(all(of[i] < of[i + 1] for i in range(2)))
        self.assertIn(FUEL, summary["verdict"])

    def test_summary_defaults_match_explicit(self):
        explicit = hrm.hybrid_motor_summary(M_DOT_O, FUEL, R_INITIAL,
                                            R_FINAL, LENGTH, AREA_THROAT,
                                            rho_f=920.0, c_star=1500.0,
                                            thrust_coeff=1.4)
        defaulted = hrm.hybrid_motor_summary(M_DOT_O, FUEL, R_INITIAL,
                                             R_FINAL, LENGTH, AREA_THROAT)
        self.assertEqual(explicit["initial"]["p_c"],
                         defaulted["initial"]["p_c"])
        self.assertEqual(explicit["burn_time"], defaulted["burn_time"])
        self.assertEqual(explicit["total_impulse"],
                         defaulted["total_impulse"])

    def test_summary_throat_mass_balance(self):
        summary = hrm.hybrid_motor_summary(M_DOT_O, "HTPB-LOX", R_INITIAL,
                                           R_FINAL, LENGTH, 2.0e-4)
        # Chamber pressure closes the choked nozzle discharge identity.
        m_tot = summary["final"]["m_dot_total"]
        assert_close(self,
                     hrm.chamber_pressure(m_tot, 1750.0, 2.0e-4),
                     summary["final"]["p_c"])
        self.assertLess(summary["of_shift"]["shift"], 1.0e-9)

    def test_summary_value_errors(self):
        with self.assertRaises(ValueError):
            hrm.hybrid_motor_summary(M_DOT_O, "magma", R_INITIAL, R_FINAL,
                                     LENGTH, AREA_THROAT)
        with self.assertRaises(ValueError):
            hrm.hybrid_motor_summary(M_DOT_O, FUEL, 0.0, R_FINAL, LENGTH,
                                     AREA_THROAT)
        with self.assertRaises(ValueError):
            hrm.hybrid_motor_summary(M_DOT_O, FUEL, R_FINAL, R_INITIAL,
                                     LENGTH, AREA_THROAT)
        with self.assertRaises(ValueError):
            hrm.hybrid_motor_summary(M_DOT_O, FUEL, R_INITIAL, R_FINAL,
                                     LENGTH, 0.0)
        with self.assertRaises(ValueError):
            hrm.hybrid_motor_summary(0.0, FUEL, R_INITIAL, R_FINAL, LENGTH,
                                     AREA_THROAT)
        with self.assertRaises(ValueError):
            hrm.hybrid_motor_summary(M_DOT_O, FUEL, R_INITIAL, R_FINAL,
                                     LENGTH, AREA_THROAT, rho_f=-1.0)


if __name__ == "__main__":
    unittest.main()
