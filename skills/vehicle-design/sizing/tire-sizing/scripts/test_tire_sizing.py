#!/usr/bin/env python3
"""Contract test for the tire sizing logic (gate 3).

Stdlib unittest only. Pins the worked cases from the SKILL.md domain
quick reference, the boundary cases, and the invalid inputs that must
raise ValueError.
"""

import unittest

from tire_sizing_logic import (
    footprint_area_sqin,
    kg_to_lb,
    required_number_of_tires,
    rolling_radius_inches,
    static_load_per_tire,
    tire_diameter_inches,
    tire_width_inches,
)


class TestUnitConversion(unittest.TestCase):
    def test_kg_to_lb_worked(self):
        self.assertAlmostEqual(kg_to_lb(18525.0), 40840.6341, places=3)

    def test_kg_to_lb_roundtrip(self):
        self.assertAlmostEqual(kg_to_lb(1000.0) / 2.2046226218487757, 1000.0, places=9)

    def test_kg_to_lb_invalid(self):
        with self.assertRaises(ValueError):
            kg_to_lb(0.0)
        with self.assertRaises(ValueError):
            kg_to_lb(-5.0)


class TestStaticLoadPerTire(unittest.TestCase):
    def test_worked_main_gear(self):
        # 78 t transport, 0.95 of the weight on the main gear, 4 main
        # tires: 78000 * 0.95 / 4 = 18525 kg per tire.
        self.assertAlmostEqual(static_load_per_tire(78000.0, 0.95, 4), 18525.0, places=6)

    def test_worked_nose_gear(self):
        # 0.10 of the weight on the nose gear, 2 nose tires.
        self.assertAlmostEqual(static_load_per_tire(78000.0, 0.10, 2), 3900.0, places=6)

    def test_single_tire_and_full_fraction(self):
        # Boundary: one tire on the gear carrying the whole weight.
        self.assertAlmostEqual(static_load_per_tire(1000.0, 1.0, 1), 1000.0, places=6)

    def test_invalid_inputs(self):
        with self.assertRaises(ValueError):
            static_load_per_tire(0.0, 0.9, 2)  # zero takeoff weight
        with self.assertRaises(ValueError):
            static_load_per_tire(-1.0, 0.9, 2)  # negative takeoff weight
        with self.assertRaises(ValueError):
            static_load_per_tire(78000.0, 0.0, 2)  # zero gear fraction
        with self.assertRaises(ValueError):
            static_load_per_tire(78000.0, -0.1, 2)  # negative gear fraction
        with self.assertRaises(ValueError):
            static_load_per_tire(78000.0, 1.1, 2)  # fraction above 1
        with self.assertRaises(ValueError):
            static_load_per_tire(78000.0, 0.9, 0)  # no tires
        with self.assertRaises(ValueError):
            static_load_per_tire(78000.0, 0.9, -2)  # negative tire count
        with self.assertRaises(ValueError):
            static_load_per_tire(78000.0, 0.9, 2.5)  # non-integer tire count


class TestTireDimensions(unittest.TestCase):
    def test_diameter_worked(self):
        # 40840.63 lb per tire -> D = 1.63 * P**0.315 = 46.20 in.
        self.assertAlmostEqual(
            tire_diameter_inches(40840.6341), 46.2042, places=3
        )

    def test_width_worked(self):
        # W = 0.40 * P**0.36 = 18.28 in.
        self.assertAlmostEqual(tire_width_inches(40840.6341), 18.2832, places=3)

    def test_diameter_metric(self):
        # 46.204 in is 1173.6 mm.
        self.assertAlmostEqual(tire_diameter_inches(40840.6341) * 25.4, 1173.5874, places=2)

    def test_diameter_monotonic(self):
        # A heavier tire must be larger.
        self.assertGreater(
            tire_diameter_inches(50000.0), tire_diameter_inches(40840.6341)
        )

    def test_invalid_inputs(self):
        with self.assertRaises(ValueError):
            tire_diameter_inches(0.0)
        with self.assertRaises(ValueError):
            tire_diameter_inches(-1.0)
        with self.assertRaises(ValueError):
            tire_diameter_inches(1000.0, coeff=0.0)
        with self.assertRaises(ValueError):
            tire_width_inches(0.0)
        with self.assertRaises(ValueError):
            tire_width_inches(-5.0)
        with self.assertRaises(ValueError):
            tire_width_inches(1000.0, coeff=-1.0)


class TestFootprint(unittest.TestCase):
    def test_worked(self):
        # 40840.63 lb at 200 psi -> 204.20 sq in contact area.
        self.assertAlmostEqual(
            footprint_area_sqin(40840.6341, 200.0), 204.2032, places=3
        )

    def test_higher_pressure_smaller_footprint(self):
        self.assertLess(
            footprint_area_sqin(40840.6341, 220.0),
            footprint_area_sqin(40840.6341, 200.0),
        )

    def test_invalid_inputs(self):
        with self.assertRaises(ValueError):
            footprint_area_sqin(0.0, 200.0)
        with self.assertRaises(ValueError):
            footprint_area_sqin(40840.6341, 0.0)
        with self.assertRaises(ValueError):
            footprint_area_sqin(40840.6341, -10.0)


class TestRollingRadius(unittest.TestCase):
    def test_worked(self):
        # Half of 46.204 in.
        self.assertAlmostEqual(rolling_radius_inches(46.2042), 23.1021, places=3)

    def test_invalid_inputs(self):
        with self.assertRaises(ValueError):
            rolling_radius_inches(0.0)
        with self.assertRaises(ValueError):
            rolling_radius_inches(-1.0)


class TestRequiredNumberOfTires(unittest.TestCase):
    def test_worked_main_gear(self):
        # 163362.54 lb on the main gear at 45000 lb per tire -> 4 tires.
        self.assertEqual(required_number_of_tires(163362.5363, 45000.0), 4)

    def test_exact_multiple_boundary(self):
        # Exactly 3 tires: 90000 / 30000 = 3, no rounding up.
        self.assertEqual(required_number_of_tires(90000.0, 30000.0), 3)

    def test_rounds_up(self):
        # 90001 lb at 30000 lb per tire -> 4 tires.
        self.assertEqual(required_number_of_tires(90001.0, 30000.0), 4)

    def test_invalid_inputs(self):
        with self.assertRaises(ValueError):
            required_number_of_tires(0.0, 30000.0)
        with self.assertRaises(ValueError):
            required_number_of_tires(90000.0, 0.0)
        with self.assertRaises(ValueError):
            required_number_of_tires(-1.0, 30000.0)


if __name__ == "__main__":
    unittest.main()
