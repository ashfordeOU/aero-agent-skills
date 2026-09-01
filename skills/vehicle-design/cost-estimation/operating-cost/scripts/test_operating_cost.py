#!/usr/bin/env python3
"""Gate 3 contract test: direct operating cost estimation.

Exercises scripts/operating_cost_logic.py (stdlib unittest, offline).
Contract: docs/harness-contract.md gate 3 - fuel, crew, maintenance
(labor plus material), insurance, landing and navigation fee, DOC per
flight, and DOC per flight hour; invalid inputs raise ValueError.
Units: costs in one currency unit, block fuel in kg, fuel price per
kg, rates as unitless fractions, times in hours.
"""

import os
import sys
import unittest

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import operating_cost_logic as ocl  # noqa: E402


class FuelCostPerFlightTest(unittest.TestCase):
    def test_analytic_fuel_cost(self):
        # 8000 kg * 0.8 /kg = 6400
        self.assertEqual(ocl.fuel_cost_per_flight(8000.0, 0.8), 6400.0)

    def test_higher_fuel_price_raises_cost(self):
        self.assertGreater(
            ocl.fuel_cost_per_flight(8000.0, 1.0),
            ocl.fuel_cost_per_flight(8000.0, 0.8),
        )

    def test_invalid_inputs_raise(self):
        with self.assertRaises(ValueError):
            ocl.fuel_cost_per_flight(0, 0.8)
        with self.assertRaises(ValueError):
            ocl.fuel_cost_per_flight(8000.0, 0)


class CrewCostPerFlightTest(unittest.TestCase):
    def test_analytic_crew_cost(self):
        # 2.5 h * 4 crew * 60 /h = 600
        self.assertEqual(ocl.crew_cost_per_flight(2.5, 4.0, 60.0), 600.0)

    def test_bigger_crew_raises_cost(self):
        self.assertGreater(
            ocl.crew_cost_per_flight(2.5, 5.0, 60.0),
            ocl.crew_cost_per_flight(2.5, 4.0, 60.0),
        )

    def test_invalid_inputs_raise(self):
        with self.assertRaises(ValueError):
            ocl.crew_cost_per_flight(0, 4.0, 60.0)
        with self.assertRaises(ValueError):
            ocl.crew_cost_per_flight(2.5, 0, 60.0)
        with self.assertRaises(ValueError):
            ocl.crew_cost_per_flight(2.5, 4.0, 0)


class MaintenanceCostPerFlightTest(unittest.TestCase):
    def test_analytic_maintenance_cost(self):
        # 2.5 h * 12 mmh/fh * 50 /h * (1 + 0.5) = 1500 * 1.5 = 2250
        self.assertEqual(
            ocl.maintenance_cost_per_flight(2.5, 12.0, 50.0, 0.5), 2250.0
        )

    def test_zero_material_factor_is_labor_only(self):
        self.assertEqual(
            ocl.maintenance_cost_per_flight(2.5, 12.0, 50.0, 0.0), 1500.0
        )

    def test_higher_mmh_raises_cost(self):
        self.assertGreater(
            ocl.maintenance_cost_per_flight(2.5, 14.0, 50.0, 0.5),
            ocl.maintenance_cost_per_flight(2.5, 12.0, 50.0, 0.5),
        )

    def test_invalid_inputs_raise(self):
        with self.assertRaises(ValueError):
            ocl.maintenance_cost_per_flight(0, 12.0, 50.0, 0.5)
        with self.assertRaises(ValueError):
            ocl.maintenance_cost_per_flight(2.5, 0, 50.0, 0.5)
        with self.assertRaises(ValueError):
            ocl.maintenance_cost_per_flight(2.5, 12.0, 0, 0.5)
        with self.assertRaises(ValueError):
            ocl.maintenance_cost_per_flight(2.5, 12.0, 50.0, -0.1)


class InsuranceCostPerFlightTest(unittest.TestCase):
    def test_analytic_insurance_cost(self):
        # 50e6 * 0.01 * (2.5 / 3000) = 500000 * 0.0008333 = 416.67
        self.assertAlmostEqual(
            ocl.insurance_cost_per_flight(50e6, 0.01, 3000.0, 2.5), 416.6667, places=4
        )

    def test_low_utilization_raises_per_flight_cost(self):
        self.assertGreater(
            ocl.insurance_cost_per_flight(50e6, 0.01, 2000.0, 2.5),
            ocl.insurance_cost_per_flight(50e6, 0.01, 3000.0, 2.5),
        )

    def test_invalid_inputs_raise(self):
        with self.assertRaises(ValueError):
            ocl.insurance_cost_per_flight(0, 0.01, 3000.0, 2.5)
        with self.assertRaises(ValueError):
            ocl.insurance_cost_per_flight(50e6, 0, 3000.0, 2.5)
        with self.assertRaises(ValueError):
            ocl.insurance_cost_per_flight(50e6, 0.01, 0, 2.5)
        with self.assertRaises(ValueError):
            ocl.insurance_cost_per_flight(50e6, 0.01, 3000.0, 0)


class LandingFeesPerFlightTest(unittest.TestCase):
    def test_analytic_fees(self):
        self.assertEqual(ocl.landing_fees_per_flight(800.0, 200.0), 1000.0)

    def test_zero_fees_allowed(self):
        self.assertEqual(ocl.landing_fees_per_flight(0.0, 0.0), 0.0)

    def test_invalid_inputs_raise(self):
        with self.assertRaises(ValueError):
            ocl.landing_fees_per_flight(-1.0, 200.0)
        with self.assertRaises(ValueError):
            ocl.landing_fees_per_flight(800.0, -1.0)


class DocRollupTest(unittest.TestCase):
    def _example_elements(self):
        fuel = ocl.fuel_cost_per_flight(8000.0, 0.8)
        crew = ocl.crew_cost_per_flight(2.5, 4.0, 60.0)
        maint = ocl.maintenance_cost_per_flight(2.5, 12.0, 50.0, 0.5)
        ins = ocl.insurance_cost_per_flight(50e6, 0.01, 3000.0, 2.5)
        fees = ocl.landing_fees_per_flight(800.0, 200.0)
        return fuel, crew, maint, ins, fees

    def test_analytic_doc_per_flight(self):
        # 6400 + 600 + 2250 + 416.6667 + 1000 = 10666.6667
        total = ocl.doc_per_flight(*self._example_elements())
        self.assertAlmostEqual(total, 10666.6667, places=4)

    def test_analytic_doc_per_flight_hour(self):
        total = ocl.doc_per_flight(*self._example_elements())
        self.assertAlmostEqual(ocl.doc_per_flight_hour(total, 2.5), 4266.6667, places=4)

    def test_zero_fees_rollup(self):
        fuel, crew, maint, ins, _ = self._example_elements()
        total = ocl.doc_per_flight(fuel, crew, maint, ins, 0.0)
        self.assertAlmostEqual(total, fuel + crew + maint + ins, places=6)

    def test_invalid_inputs_raise(self):
        with self.assertRaises(ValueError):
            ocl.doc_per_flight(-1.0, 600.0, 2250.0, 416.67, 1000.0)
        with self.assertRaises(ValueError):
            ocl.doc_per_flight_hour(10666.67, 0)
        with self.assertRaises(ValueError):
            ocl.doc_per_flight_hour(-100.0, 2.5)


if __name__ == "__main__":
    unittest.main(verbosity=2)
