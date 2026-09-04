"""Contract test for aircraft-oxygen-system-sizing (wave-35).

Deterministic stdlib unittest, offline. Run with:

    python3 scripts/test_aircraft_oxygen_system_sizing.py

Covers the 150 passenger / 6 crew / 1800 psi reference transport
worked example, scaling identities, standard-condition mass round
trip, convenience dict keys and ValueError rejection of every
non-physical input class.
"""

import os
import sys
import unittest

sys.path.insert(
    0, os.path.join(os.path.dirname(os.path.abspath(__file__)))
)

import aircraft_oxygen_system_sizing_logic as o2


class TestPassengerDemand(unittest.TestCase):
    def test_worked_example_volume(self):
        """150 passengers at 5.0 SLPM for 22 min give 16500 SL."""
        result = o2.passenger_demand(150)
        self.assertAlmostEqual(result["volume_sl"], 16500.0, delta=1e-1)

    def test_worked_example_mass(self):
        """150 passenger demand mass is 23.58 kg within 1e-1."""
        result = o2.passenger_demand(150)
        self.assertAlmostEqual(result["mass_kg"], 23.58, delta=1e-1)

    def test_doubling_passengers_doubles_volume(self):
        """Doubling the passenger count doubles demand volume."""
        one = o2.passenger_demand(150)
        two = o2.passenger_demand(300)
        self.assertAlmostEqual(two["volume_sl"], 2.0 * one["volume_sl"])

    def test_doubling_passengers_doubles_mass(self):
        """Doubling the passenger count doubles demand mass."""
        one = o2.passenger_demand(150)
        two = o2.passenger_demand(300)
        self.assertAlmostEqual(two["mass_kg"], 2.0 * one["mass_kg"])

    def test_custom_flow_and_duration(self):
        """Explicit flow and duration scale the demand linearly."""
        result = o2.passenger_demand(100, flow_slpm=4.0, duration_min=10.0)
        self.assertAlmostEqual(result["volume_sl"], 4000.0)
        self.assertAlmostEqual(result["mass_kg"], 4000.0 * 1.429e-3)

    def test_zero_duration_raises(self):
        """A zero protection duration is non-physical."""
        with self.assertRaises(ValueError):
            o2.passenger_demand(150, duration_min=0.0)

    def test_zero_flow_raises(self):
        """A zero flow rate is non-physical."""
        with self.assertRaises(ValueError):
            o2.passenger_demand(150, flow_slpm=0.0)

    def test_zero_passengers_raises(self):
        """A zero passenger count is non-physical."""
        with self.assertRaises(ValueError):
            o2.passenger_demand(0)

    def test_negative_passengers_raises(self):
        """A negative passenger count is non-physical."""
        with self.assertRaises(ValueError):
            o2.passenger_demand(-5)


class TestGeneratorUnits(unittest.TestCase):
    def test_worked_example_units(self):
        """150 passengers need 150 generator units."""
        self.assertEqual(o2.generator_units(150), 150)

    def test_single_passenger(self):
        """One passenger needs one generator unit."""
        self.assertEqual(o2.generator_units(1), 1)

    def test_zero_passengers_raises(self):
        """A zero passenger count is non-physical."""
        with self.assertRaises(ValueError):
            o2.generator_units(0)

    def test_negative_passengers_raises(self):
        """A negative passenger count is non-physical."""
        with self.assertRaises(ValueError):
            o2.generator_units(-1)


class TestCrewDemand(unittest.TestCase):
    def test_worked_example_volume(self):
        """6 crew at 2.5 SLPM for 120 min give 1800 SL."""
        result = o2.crew_demand(6)
        self.assertAlmostEqual(result["volume_sl"], 1800.0, delta=1e-2)

    def test_worked_example_mass(self):
        """6 crew demand mass is 2.57 kg within 1e-2."""
        result = o2.crew_demand(6)
        self.assertAlmostEqual(result["mass_kg"], 2.57, delta=1e-2)

    def test_zero_crew_raises(self):
        """A zero crew count is non-physical."""
        with self.assertRaises(ValueError):
            o2.crew_demand(0)

    def test_negative_flow_raises(self):
        """A negative flow rate is non-physical."""
        with self.assertRaises(ValueError):
            o2.crew_demand(6, flow_slpm=-1.0)

    def test_negative_duration_raises(self):
        """A negative duration is non-physical."""
        with self.assertRaises(ValueError):
            o2.crew_demand(6, duration_min=-2.0)


class TestBottleVolume(unittest.TestCase):
    def test_worked_example_volume_l(self):
        """Crew oxygen at 1800 psi fits 15.52 L within 1e-2."""
        result = o2.bottle_volume(2.5722, 1800)
        self.assertAlmostEqual(result["volume_l"], 15.52, delta=1e-2)

    def test_worked_example_volume_m3(self):
        """Crew bottle volume is 0.01552 m3 within 1e-2."""
        result = o2.bottle_volume(2.5722, 1800)
        self.assertAlmostEqual(result["volume_m3"], 0.01552, delta=1e-2)

    def test_litres_are_m3_times_1000(self):
        """volume_l equals volume_m3 times 1000."""
        result = o2.bottle_volume(2.5722, 1800)
        self.assertAlmostEqual(result["volume_l"], 1000.0 * result["volume_m3"])

    def test_doubling_pressure_halves_volume(self):
        """Volume is inversely proportional to service pressure."""
        one = o2.bottle_volume(2.5722, 1800)
        two = o2.bottle_volume(2.5722, 3600)
        self.assertAlmostEqual(two["volume_m3"], one["volume_m3"] / 2.0)

    def test_doubling_mass_doubles_volume(self):
        """Volume is proportional to stored mass at fixed pressure."""
        one = o2.bottle_volume(2.5722, 1800)
        two = o2.bottle_volume(5.1444, 1800)
        self.assertAlmostEqual(two["volume_m3"], 2.0 * one["volume_m3"])

    def test_zero_mass_raises(self):
        """Zero stored mass is non-physical."""
        with self.assertRaises(ValueError):
            o2.bottle_volume(0.0, 1800)

    def test_negative_mass_raises(self):
        """Negative stored mass is non-physical."""
        with self.assertRaises(ValueError):
            o2.bottle_volume(-1.0, 1800)

    def test_zero_pressure_raises(self):
        """Zero service pressure is non-physical."""
        with self.assertRaises(ValueError):
            o2.bottle_volume(2.5722, 0.0)

    def test_zero_temperature_raises(self):
        """Zero storage temperature is non-physical."""
        with self.assertRaises(ValueError):
            o2.bottle_volume(2.5722, 1800, temperature_k=0.0)

    def test_negative_temperature_raises(self):
        """Negative storage temperature is non-physical."""
        with self.assertRaises(ValueError):
            o2.bottle_volume(2.5722, 1800, temperature_k=-10.0)


class TestIdentitiesAndSummary(unittest.TestCase):
    def test_mass_round_trip_one_standard_litre(self):
        """1 SL of oxygen masses exactly 1.429e-3 kg."""
        result = o2.passenger_demand(1, flow_slpm=1.0, duration_min=1.0)
        self.assertAlmostEqual(result["volume_sl"], 1.0)
        self.assertAlmostEqual(result["mass_kg"], 1.429e-3)

    def test_mass_is_volume_times_density(self):
        """mass_kg equals volume_sl times 1.429e-3 exactly."""
        pax = o2.passenger_demand(150)
        self.assertAlmostEqual(pax["mass_kg"], pax["volume_sl"] * 1.429e-3)
        crew = o2.crew_demand(6)
        self.assertAlmostEqual(crew["mass_kg"], crew["volume_sl"] * 1.429e-3)

    def test_determinism(self):
        """Identical inputs give identical outputs."""
        first = o2.oxygen_summary(150, 6, 1800)
        second = o2.oxygen_summary(150, 6, 1800)
        self.assertEqual(first, second)

    def test_summary_dict_keys(self):
        """oxygen_summary keys match the documented contract exactly."""
        result = o2.oxygen_summary(150, 6, 1800)
        self.assertEqual(
            set(result.keys()),
            {
                "passenger_demand_sl",
                "passenger_mass_kg",
                "generator_units",
                "crew_demand_sl",
                "crew_mass_kg",
                "bottle_volume_m3",
                "bottle_volume_l",
                "total_mass_kg",
            },
        )

    def test_summary_worked_example(self):
        """Reference transport summary values land on the spec bounds."""
        result = o2.oxygen_summary(150, 6, 1800)
        self.assertEqual(result["generator_units"], 150)
        self.assertAlmostEqual(result["passenger_demand_sl"], 16500.0, delta=1e-1)
        self.assertAlmostEqual(result["passenger_mass_kg"], 23.58, delta=1e-1)
        self.assertAlmostEqual(result["crew_demand_sl"], 1800.0, delta=1e-2)
        self.assertAlmostEqual(result["crew_mass_kg"], 2.57, delta=1e-2)
        self.assertAlmostEqual(result["bottle_volume_l"], 15.52, delta=1e-2)
        self.assertAlmostEqual(
            result["total_mass_kg"],
            result["passenger_mass_kg"] + result["crew_mass_kg"],
        )

    def test_summary_value_errors_propagate(self):
        """Non-physical inputs raise through the summary function."""
        with self.assertRaises(ValueError):
            o2.oxygen_summary(0, 6, 1800)
        with self.assertRaises(ValueError):
            o2.oxygen_summary(150, 0, 1800)
        with self.assertRaises(ValueError):
            o2.oxygen_summary(150, 6, -2000)


if __name__ == "__main__":
    unittest.main()
