"""Gate 3 contract test for the combustion-chamber-design leaf.

Pins the worked LOX/RP-1 example (7.0 MPa, 0.02 m^2 throat, 80 kg/s),
the theoretical c-star ceiling, the round trips, and the invalid-input
boundaries. Stdlib unittest, offline, deterministic.
"""

import math
import unittest

from combustion_chamber_design_logic import (
    G0,
    chamber_volume,
    characteristic_velocity,
    contraction_ratio,
    nozzle_throat_radius,
    theoretical_cstar,
    throat_area_from_flow,
    thrust_coefficient,
    thrust_from_cf,
    vacuum_specific_impulse,
)

PC = 7.0e6  # Pa, 7.0 MPa chamber pressure
AT = 0.02  # m^2 throat area
MDOT = 80.0  # kg/s propellant mass flow
F = 252000.0  # N vacuum-class thrust


class TestCharacteristicVelocity(unittest.TestCase):
    def test_worked_lox_rp1(self):
        self.assertAlmostEqual(characteristic_velocity(PC, AT, MDOT), 1750.0, places=1)

    def test_scales_with_pressure(self):
        # c* is proportional to Pc at fixed At and mdot (defining form).
        self.assertAlmostEqual(
            characteristic_velocity(2 * PC, AT, MDOT), 3500.0, places=1
        )

    def test_invalid_inputs(self):
        for args in [
            (0.0, AT, MDOT),
            (-1.0, AT, MDOT),
            (PC, 0.0, MDOT),
            (PC, AT, 0.0),
            (PC, AT, -5.0),
        ]:
            with self.assertRaises(ValueError):
                characteristic_velocity(*args)


class TestTheoreticalCstar(unittest.TestCase):
    def test_worked_lox_rp1(self):
        # Tc = 3670 K, Mw = 23 kg/kmol, gamma = 1.20
        self.assertAlmostEqual(
            theoretical_cstar(3670.0, 23.0, 1.20), 1776.2, delta=1.0
        )

    def test_delivered_below_theoretical(self):
        delivered = characteristic_velocity(PC, AT, MDOT)
        ideal = theoretical_cstar(3670.0, 23.0, 1.20)
        self.assertLess(delivered, ideal)
        self.assertAlmostEqual(delivered / ideal, 0.9853, places=3)

    def test_gamma_boundaries(self):
        # 5/3 (monatomic limit) is allowed; anything above is not.
        self.assertGreater(theoretical_cstar(3670.0, 23.0, 5.0 / 3.0), 0.0)
        for gamma in [1.0, 0.9, 1.7, 2.0]:
            with self.assertRaises(ValueError):
                theoretical_cstar(3670.0, 23.0, gamma)

    def test_invalid_inputs(self):
        for args in [(0.0, 23.0, 1.2), (-1.0, 23.0, 1.2), (3670.0, 0.0, 1.2)]:
            with self.assertRaises(ValueError):
                theoretical_cstar(*args)


class TestThrustCoefficient(unittest.TestCase):
    def test_worked_vacuum_class(self):
        self.assertAlmostEqual(thrust_coefficient(F, PC, AT), 1.8, places=4)

    def test_round_trip(self):
        cf = thrust_coefficient(F, PC, AT)
        self.assertAlmostEqual(thrust_from_cf(cf, PC, AT), F, places=1)

    def test_invalid_inputs(self):
        for args in [(0.0, PC, AT), (F, 0.0, AT), (F, PC, 0.0), (-1.0, PC, AT)]:
            with self.assertRaises(ValueError):
                thrust_coefficient(*args)
        for args in [(0.0, PC, AT), (1.8, -1.0, AT), (1.8, PC, 0.0)]:
            with self.assertRaises(ValueError):
                thrust_from_cf(*args)


class TestThroatAreaSizing(unittest.TestCase):
    def test_worked_round_trip(self):
        at = throat_area_from_flow(MDOT, 1750.0, PC)
        self.assertAlmostEqual(at, AT, places=6)
        self.assertAlmostEqual(
            characteristic_velocity(PC, at, MDOT), 1750.0, places=1
        )

    def test_invalid_inputs(self):
        for args in [(0.0, 1750.0, PC), (80.0, 0.0, PC), (80.0, 1750.0, 0.0)]:
            with self.assertRaises(ValueError):
                throat_area_from_flow(*args)


class TestChamberGeometry(unittest.TestCase):
    def test_contraction_ratio(self):
        self.assertAlmostEqual(contraction_ratio(0.07, AT), 3.5, places=4)

    def test_contraction_must_converge(self):
        with self.assertRaises(ValueError):
            contraction_ratio(AT, AT)
        with self.assertRaises(ValueError):
            contraction_ratio(0.015, AT)

    def test_chamber_volume_from_lstar(self):
        self.assertAlmostEqual(chamber_volume(0.9, AT), 0.018, places=6)

    def test_throat_radius(self):
        self.assertAlmostEqual(nozzle_throat_radius(AT), math.sqrt(AT / math.pi), places=6)
        self.assertAlmostEqual(nozzle_throat_radius(AT), 0.0798, places=3)

    def test_invalid_inputs(self):
        with self.assertRaises(ValueError):
            chamber_volume(0.0, AT)
        with self.assertRaises(ValueError):
            chamber_volume(0.9, -1.0)
        with self.assertRaises(ValueError):
            nozzle_throat_radius(0.0)


class TestVacuumSpecificImpulse(unittest.TestCase):
    def test_worked(self):
        self.assertAlmostEqual(vacuum_specific_impulse(F, MDOT), 321.21, places=2)
        self.assertAlmostEqual(vacuum_specific_impulse(F, MDOT), F / (MDOT * G0), places=6)

    def test_invalid_inputs(self):
        for args in [(0.0, MDOT), (F, 0.0), (-1.0, MDOT)]:
            with self.assertRaises(ValueError):
                vacuum_specific_impulse(*args)


if __name__ == "__main__":
    unittest.main()
