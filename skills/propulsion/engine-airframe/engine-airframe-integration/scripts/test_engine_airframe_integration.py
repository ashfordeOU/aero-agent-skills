#!/usr/bin/env python3
"""Gate 3 contract test: engine-airframe-integration logic (stdlib unittest).

Exercises scripts/engine_airframe_integration_logic.py offline with
the stdlib unittest runner only. Covers the worked anchor ledger
(mdot_0 = 100 kg/s, mdot_e = 102 kg/s, Vj = 600 m/s, V0 = 250 m/s,
fully expanded nozzle, rho = 0.36, Cd_nac = 0.35, A_nac = 1.2 m^2,
Cd_pyl = 0.30, A_pyl = 0.5 m^2, bleed 1.5 kg/s, accessory 500 kW),
term scaling with mass flow and velocity, bleed and accessory
reduction of net thrust, the pressure term, misalignment, and
ValueError on invalid inputs.
"""

import os
import sys
import unittest

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import engine_airframe_integration_logic as eai

ANCHOR = dict(
    mdot_0=100.0,
    mdot_e=102.0,
    Vj=600.0,
    V0=250.0,
    Pe=101325.0,
    P0=101325.0,
    Ae=0.4,
    rho=0.36,
    Cd_nac=0.35,
    A_nac=1.2,
    Cd_pyl=0.30,
    A_pyl=0.5,
    mdot_b=1.5,
    P_extract=500000.0,
)


class InstalledThrustLedgerTest(unittest.TestCase):
    def test_hand_computed_terms(self):
        s = eai.thrust_drag_summary(theta_deg=0.0, **ANCHOR)
        # Fg = 102*600 = 61200 N (fully expanded: pressure term 0)
        self.assertAlmostEqual(s["Fg"], 61200.0, delta=1e-6)
        # D_ram = 100*250 = 25000 N
        self.assertAlmostEqual(s["D_ram"], 25000.0, delta=1e-6)
        # F_uninst = 61200 - 25000 = 36200 N
        self.assertAlmostEqual(s["F_uninst"], 36200.0, delta=1e-6)
        # D_nac = 0.5*0.36*250^2*0.35*1.2 = 4725 N
        self.assertAlmostEqual(s["D_nac"], 4725.0, delta=1e-6)
        # D_pyl = 0.5*0.36*250^2*0.30*0.5 = 1687.5 N
        self.assertAlmostEqual(s["D_pyl"], 1687.5, delta=1e-6)
        # dF_b = 1.5*(600-250) = 525 N
        self.assertAlmostEqual(s["dF_b"], 525.0, delta=1e-6)
        # dF_a = 500000/250 = 2000 N
        self.assertAlmostEqual(s["dF_a"], 2000.0, delta=1e-6)
        # F_inst = 36200 - 4725 - 1687.5 - 525 - 2000 = 27262.5 N
        self.assertAlmostEqual(s["F_inst"], 27262.5, delta=1e-6)

    def test_installed_below_uninstalled_by_expected_amount(self):
        s = eai.thrust_drag_summary(theta_deg=0.0, **ANCHOR)
        self.assertLess(s["F_inst"], s["F_uninst"])
        self.assertAlmostEqual(
            s["F_uninst"] - s["F_inst"],
            s["D_nac"] + s["D_pyl"] + s["dF_b"] + s["dF_a"],
            delta=1e-6,
        )
        # loss fraction = 1 - 27262.5/36200 = 0.246889...
        self.assertAlmostEqual(
            s["loss_fraction"], 1.0 - 27262.5 / 36200.0, delta=1e-9
        )
        self.assertAlmostEqual(s["loss_fraction"], 0.2469, delta=1e-3)


class ScalingTest(unittest.TestCase):
    def test_ram_drag_linear_in_mass_flow_and_velocity(self):
        d1 = eai.intake_momentum_drag(100.0, 250.0)
        # Doubling the captured flow doubles the ram drag.
        self.assertAlmostEqual(eai.intake_momentum_drag(200.0, 250.0), 2.0 * d1, delta=1e-9)
        # Doubling the flight velocity doubles the ram drag.
        self.assertAlmostEqual(eai.intake_momentum_drag(100.0, 500.0), 2.0 * d1, delta=1e-9)

    def test_external_drag_quadratic_in_velocity_linear_in_area(self):
        base = eai.nacelle_drag(0.36, 250.0, 0.35, 1.2)
        # Doubling V0 quadruples the dynamic-pressure term.
        self.assertAlmostEqual(eai.nacelle_drag(0.36, 500.0, 0.35, 1.2), 4.0 * base, delta=1e-9)
        # Doubling the reference area doubles the term.
        self.assertAlmostEqual(eai.nacelle_drag(0.36, 250.0, 0.35, 2.4), 2.0 * base, delta=1e-9)
        # Pylon shares the same quadratic form.
        self.assertAlmostEqual(
            eai.pylon_drag(0.36, 500.0, 0.30, 0.5),
            4.0 * eai.pylon_drag(0.36, 250.0, 0.30, 0.5),
            delta=1e-9,
        )

    def test_bleed_and_accessory_reduce_installed_thrust(self):
        base = eai.thrust_drag_summary(theta_deg=0.0, **ANCHOR)
        # Doubling the bleed flow doubles the bleed loss.
        more_bleed = dict(ANCHOR, mdot_b=3.0)
        s = eai.thrust_drag_summary(theta_deg=0.0, **more_bleed)
        self.assertAlmostEqual(s["dF_b"], 2.0 * base["dF_b"], delta=1e-9)
        # Doubling the accessory power doubles the accessory loss.
        more_power = dict(ANCHOR, P_extract=1000000.0)
        s2 = eai.thrust_drag_summary(theta_deg=0.0, **more_power)
        self.assertAlmostEqual(s2["dF_a"], 2.0 * base["dF_a"], delta=1e-9)
        # Each off-take reduces installed thrust by exactly its term.
        self.assertAlmostEqual(
            base["F_inst"] - s["F_inst"], base["dF_b"], delta=1e-6
        )
        self.assertAlmostEqual(
            base["F_inst"] - s2["F_inst"], base["dF_a"], delta=1e-6
        )


class PressureTermAndMisalignmentTest(unittest.TestCase):
    def test_pressure_term_adds_gross_thrust(self):
        # Underexpanded nozzle: (Pe - P0)*Ae adds to the momentum term.
        Fg_bal = eai.gross_thrust(102.0, 600.0, Pe=101325.0, P0=101325.0, Ae=0.4)
        Fg_und = eai.gross_thrust(102.0, 600.0, Pe=120000.0, P0=101325.0, Ae=0.4)
        self.assertAlmostEqual(Fg_bal, 61200.0, delta=1e-6)
        self.assertAlmostEqual(Fg_und, Fg_bal + (120000.0 - 101325.0) * 0.4, delta=1e-6)

    def test_misalignment_trims_axial_thrust(self):
        s = eai.thrust_drag_summary(theta_deg=2.0, **ANCHOR)
        self.assertAlmostEqual(
            s["F_axial"], 27262.5 * 0.999390827, delta=0.1
        )
        self.assertLess(s["F_axial"], s["F_inst"])
        self.assertAlmostEqual(
            s["F_axial"], eai.axial_thrust(27262.5, 2.0), delta=1e-6
        )


class InvalidInputTest(unittest.TestCase):
    def test_raises(self):
        with self.assertRaises(ValueError):
            eai.gross_thrust(0.0, 600.0)  # zero exhaust flow
        with self.assertRaises(ValueError):
            eai.gross_thrust(102.0, 0.0)  # zero jet velocity
        with self.assertRaises(ValueError):
            eai.gross_thrust(102.0, 600.0, Ae=-0.4)  # negative area
        with self.assertRaises(ValueError):
            eai.intake_momentum_drag(0.0, 250.0)  # zero captured flow
        with self.assertRaises(ValueError):
            eai.intake_momentum_drag(100.0, 0.0)  # zero flight velocity
        with self.assertRaises(ValueError):
            eai.uninstalled_net_thrust(20000.0, 25000.0)  # ram exceeds gross
        with self.assertRaises(ValueError):
            eai.nacelle_drag(0.0, 250.0, 0.35, 1.2)  # zero density
        with self.assertRaises(ValueError):
            eai.nacelle_drag(0.36, 250.0, -0.35, 1.2)  # negative Cd
        with self.assertRaises(ValueError):
            eai.pylon_drag(0.36, 250.0, 0.30, 0.0)  # zero area
        with self.assertRaises(ValueError):
            eai.bleed_thrust_loss(-1.0, 600.0, 250.0)  # negative bleed flow
        with self.assertRaises(ValueError):
            eai.bleed_thrust_loss(1.5, 200.0, 250.0)  # jet slower than flight
        with self.assertRaises(ValueError):
            eai.accessory_thrust_loss(-500000.0, 250.0)  # negative power
        with self.assertRaises(ValueError):
            eai.axial_thrust(1000.0, 90.0)  # misalignment at 90 deg
        with self.assertRaises(ValueError):
            eai.installed_thrust(100.0, 40.0, 40.0, 40.0, 40.0)  # losses exceed
        with self.assertRaises(ValueError):
            eai.thrust_drag_summary(theta_deg=-1.0, **ANCHOR)  # negative angle


class DemonstrationTest(unittest.TestCase):
    def test_demonstrate_runs_and_returns_anchor_ledger(self):
        s = eai.demonstrate()
        self.assertIsInstance(s, dict)
        self.assertAlmostEqual(s["F_inst"], 27262.5, delta=1e-6)


if __name__ == "__main__":
    unittest.main()
