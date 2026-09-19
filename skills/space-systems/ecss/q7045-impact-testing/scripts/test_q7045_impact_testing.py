"""Contract tests for the Charpy V-notch impact assessment logic.

The cases read an impact set the way a reviewer does: whether the bars were
full size or sub-size and what requirement that scales to, whether the set
average and every individual bar clear their floors, whether the bars were at
the stated temperature when the pendulum landed, and whether the readings sat
in the usable part of the machine.
"""

import unittest

from q7045_impact_testing_logic import (
    CAPACITY_BAND,
    INDIVIDUAL_FRACTION,
    MAX_TRANSFER_S,
    MIN_SOAK_MIN,
    SPECIMEN_WIDTHS_MM,
    TEMPERATURE_TOLERANCE_C,
    assess_impact_test,
    capacity_findings,
    condition_findings,
    required_average_j,
    required_individual_j,
    set_average_j,
    subsize_factor,
    temperature_findings,
)

FULL_REQUIREMENT = 27.0
ENERGIES = (40.0, 45.0, 38.0)
CAPACITY = 300.0


def _spec(**overrides):
    spec = {
        "energies_j": list(ENERGIES),
        "width_mm": 10.0,
        "full_size_requirement_j": FULL_REQUIREMENT,
        "specified_temperature_c": -40.0,
        "measured_temperatures_c": [-40.5, -39.8, -41.0],
        "soak_minutes": 15.0,
        "transfer_seconds": 3.0,
        "machine_capacity_j": CAPACITY,
    }
    spec.update(overrides)
    return spec


class SpecimenWidthTests(unittest.TestCase):
    def test_full_size_bar_has_unit_factor(self):
        self.assertAlmostEqual(subsize_factor(10.0), 1.0, places=9)

    def test_three_quarter_bar_scales_to_three_quarters(self):
        self.assertAlmostEqual(subsize_factor(7.5), 0.75, places=9)

    def test_quarter_bar_scales_to_a_quarter(self):
        self.assertAlmostEqual(subsize_factor(2.5), 0.25, places=9)

    def test_four_standard_widths_are_covered(self):
        self.assertEqual(len(SPECIMEN_WIDTHS_MM), 4)

    def test_non_standard_width_rejected(self):
        with self.assertRaises(ValueError):
            subsize_factor(6.0)

    def test_zero_width_rejected(self):
        with self.assertRaises(ValueError):
            subsize_factor(0.0)


class RequirementTests(unittest.TestCase):
    def test_full_size_requirement_is_unscaled(self):
        self.assertAlmostEqual(
            required_average_j(FULL_REQUIREMENT, 10.0), FULL_REQUIREMENT, places=9
        )

    def test_subsize_requirement_scales_with_the_width(self):
        self.assertAlmostEqual(required_average_j(FULL_REQUIREMENT, 7.5), 20.25,
                               places=9)

    def test_individual_floor_is_a_fraction_of_the_average(self):
        floor = required_individual_j(20.0)
        self.assertAlmostEqual(floor, 20.0 * INDIVIDUAL_FRACTION, places=9)

    def test_non_positive_requirement_rejected(self):
        with self.assertRaises(ValueError):
            required_average_j(0.0, 10.0)

    def test_set_average_of_three_bars(self):
        self.assertAlmostEqual(set_average_j(ENERGIES), 41.0, places=9)

    def test_two_bar_set_rejected(self):
        with self.assertRaises(ValueError):
            set_average_j((40.0, 45.0))

    def test_negative_energy_rejected(self):
        with self.assertRaises(ValueError):
            set_average_j((40.0, 45.0, -1.0))


class ConditionTests(unittest.TestCase):
    def test_bars_inside_tolerance_are_silent(self):
        self.assertEqual(temperature_findings(-40.0, [-40.5, -39.8, -41.0]), [])

    def test_bar_exactly_at_the_tolerance_is_silent(self):
        self.assertEqual(
            temperature_findings(-40.0, [-40.0 - TEMPERATURE_TOLERANCE_C]), []
        )

    def test_warm_bar_is_reported(self):
        notes = temperature_findings(-40.0, [-40.0, -34.0])
        self.assertEqual(len(notes), 1)
        self.assertIn("specimen 1", notes[0])

    def test_empty_temperature_list_rejected(self):
        with self.assertRaises(ValueError):
            temperature_findings(-40.0, [])

    def test_good_conditioning_is_silent(self):
        self.assertEqual(condition_findings(15.0, 3.0), [])

    def test_short_soak_is_reported(self):
        notes = condition_findings(MIN_SOAK_MIN / 2.0, 3.0)
        self.assertEqual(len(notes), 1)
        self.assertIn("soak", notes[0])

    def test_slow_transfer_is_reported(self):
        notes = condition_findings(15.0, MAX_TRANSFER_S * 2.0)
        self.assertEqual(len(notes), 1)
        self.assertIn("transfer", notes[0])

    def test_transfer_exactly_at_the_limit_is_silent(self):
        self.assertEqual(condition_findings(15.0, MAX_TRANSFER_S), [])

    def test_unmeasured_conditions_raise_nothing(self):
        self.assertEqual(condition_findings(), [])


class CapacityTests(unittest.TestCase):
    def test_readings_inside_the_usable_range_are_silent(self):
        self.assertEqual(capacity_findings(ENERGIES, CAPACITY), [])

    def test_reading_too_low_for_the_pendulum_is_reported(self):
        notes = capacity_findings((10.0, 40.0, 45.0), CAPACITY)
        self.assertEqual(len(notes), 1)
        self.assertIn("specimen 0", notes[0])

    def test_reading_too_high_for_the_pendulum_is_reported(self):
        notes = capacity_findings((40.0, 45.0, 280.0), CAPACITY)
        self.assertEqual(len(notes), 1)

    def test_reading_exactly_at_the_lower_bound_is_silent(self):
        low = CAPACITY_BAND[0]
        self.assertEqual(capacity_findings((CAPACITY * low,), CAPACITY), [])

    def test_zero_capacity_rejected(self):
        with self.assertRaises(ValueError):
            capacity_findings(ENERGIES, 0.0)

    def test_empty_reading_list_rejected(self):
        with self.assertRaises(ValueError):
            capacity_findings([], CAPACITY)


class AssessmentTests(unittest.TestCase):
    def test_clean_set_is_accepted(self):
        result = assess_impact_test(_spec())
        self.assertTrue(result["set_accepted"])
        self.assertEqual(result["findings"], [])

    def test_reported_average_and_floors(self):
        result = assess_impact_test(_spec())
        self.assertAlmostEqual(result["set_average_j"], 41.0, places=9)
        self.assertAlmostEqual(result["required_average_j"], FULL_REQUIREMENT,
                               places=9)
        self.assertAlmostEqual(result["lowest_j"], 38.0, places=9)

    def test_subsize_set_is_judged_against_a_smaller_requirement(self):
        result = assess_impact_test(
            _spec(width_mm=5.0, energies_j=[16.0, 18.0, 15.0],
                  measured_temperatures_c=[-40.0, -40.0, -40.0],
                  machine_capacity_j=150.0)
        )
        self.assertAlmostEqual(result["required_average_j"], 13.5, places=9)
        self.assertTrue(result["set_accepted"])

    def test_set_exactly_at_the_average_requirement_is_accepted(self):
        result = assess_impact_test(
            _spec(energies_j=[FULL_REQUIREMENT] * 3,
                  measured_temperatures_c=[-40.0] * 3,
                  machine_capacity_j=100.0)
        )
        self.assertTrue(result["set_accepted"])

    def test_one_brittle_bar_is_not_averaged_away(self):
        result = assess_impact_test(
            _spec(energies_j=[60.0, 60.0, 10.0],
                  measured_temperatures_c=[-40.0] * 3)
        )
        self.assertFalse(result["set_accepted"])
        self.assertIn("individual floor", " ".join(result["findings"]))

    def test_low_set_average_is_reported(self):
        result = assess_impact_test(
            _spec(energies_j=[22.0, 23.0, 21.0],
                  measured_temperatures_c=[-40.0] * 3)
        )
        self.assertFalse(result["set_accepted"])
        self.assertIn("set average", result["findings"][0])

    def test_warm_bar_makes_the_set_unaccepted(self):
        result = assess_impact_test(
            _spec(measured_temperatures_c=[-40.0, -30.0, -40.0])
        )
        self.assertFalse(result["set_accepted"])

    def test_temperature_list_length_mismatch_rejected(self):
        with self.assertRaises(ValueError):
            assess_impact_test(_spec(measured_temperatures_c=[-40.0]))

    def test_slow_transfer_makes_the_set_unaccepted(self):
        result = assess_impact_test(_spec(transfer_seconds=12.0))
        self.assertFalse(result["set_accepted"])

    def test_lateral_expansion_below_the_minimum_is_reported(self):
        result = assess_impact_test(
            _spec(lateral_expansions_mm=[0.50, 0.20, 0.55],
                  minimum_lateral_expansion_mm=0.38)
        )
        self.assertFalse(result["set_accepted"])
        self.assertIn("laterally", " ".join(result["findings"]))

    def test_lateral_expansion_above_the_minimum_is_accepted(self):
        result = assess_impact_test(
            _spec(lateral_expansions_mm=[0.50, 0.45, 0.55],
                  minimum_lateral_expansion_mm=0.38)
        )
        self.assertTrue(result["set_accepted"])

    def test_unmeasured_lateral_expansion_with_a_minimum_is_reported(self):
        result = assess_impact_test(_spec(minimum_lateral_expansion_mm=0.38))
        self.assertFalse(result["set_accepted"])
        self.assertIn("no expansion was", " ".join(result["findings"]))

    def test_expansion_without_a_minimum_rejected(self):
        with self.assertRaises(ValueError):
            assess_impact_test(_spec(lateral_expansions_mm=[0.5, 0.5, 0.5]))

    def test_missing_spec_key_rejected(self):
        spec = _spec()
        del spec["width_mm"]
        with self.assertRaises(ValueError):
            assess_impact_test(spec)

    def test_non_mapping_spec_rejected(self):
        with self.assertRaises(ValueError):
            assess_impact_test(["energies"])


if __name__ == "__main__":
    unittest.main()
