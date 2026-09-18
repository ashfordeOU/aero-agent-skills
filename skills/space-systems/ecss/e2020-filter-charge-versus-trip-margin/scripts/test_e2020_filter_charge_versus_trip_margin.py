"""Contract tests for the clause 5.4.2.3.1 filter-charge separation assessment.

Every workflow step the SKILL.md sets out is exercised here, together with
the stop conditions the gate 3 contract reviews: each governing number
pushed to the end of the band that slows charging, a shortest trip time
taken from a family rather than a single row, a separation landing exactly
on the required factor, and a case that clears the factor at nominal while
tripping on switch-on at the corner.
"""

import unittest

from e2020_filter_charge_versus_trip_margin_logic import (
    BUS_VOLTAGE_NOT_ESTABLISHED,
    CHARGE_MARGIN_MET,
    CHARGE_MARGIN_NOT_MET,
    FILTER_CAPACITANCE_NOT_ESTABLISHED,
    LIMITATION_CURRENT_NOT_ESTABLISHED,
    REQUIRED_MARGIN_NOT_ESTABLISHED,
    TRIP_TIME_NOT_ESTABLISHED,
    assess_filter_charge_margin,
    charge_margin_fraction,
    charge_to_trip_ratio,
    evaluate_conditions,
    filter_charge_time,
    margin_is_met,
    nominal_conditions,
    shortest_trip_time,
    worst_case_bus_voltage,
    worst_case_capacitance,
    worst_case_conditions,
    worst_case_limitation_current,
)


def _case(**overrides):
    case = {
        "filter_capacitance_f": 100.0e-6,
        "capacitance_tolerance_fraction": 0.20,
        "capacitance_ageing_fraction": 0.10,
        "bus_voltage_v": 28.0,
        "bus_voltage_upper_tolerance_fraction": 0.10,
        "limitation_current_a": 1.0,
        "limitation_current_tolerance_fraction": 0.10,
        "trip_times_s": [0.01, 0.05],
        "trip_time_tolerance_fraction": 0.20,
        "required_margin_factor": 1.5,
    }
    case.update(overrides)
    return case


class CapacitanceTests(unittest.TestCase):
    def test_tolerance_and_drift_both_raise_the_demand(self):
        self.assertAlmostEqual(
            worst_case_capacitance(100.0e-6, 0.20, 0.10), 132.0e-6, places=12
        )

    def test_no_allowances_leaves_the_schematic_value(self):
        self.assertAlmostEqual(
            worst_case_capacitance(100.0e-6), 100.0e-6, places=12
        )

    def test_a_zero_capacitance_is_refused(self):
        with self.assertRaises(ValueError):
            worst_case_capacitance(0.0, 0.2, 0.1)

    def test_a_negative_tolerance_is_refused(self):
        with self.assertRaises(ValueError):
            worst_case_capacitance(100.0e-6, -0.1)

    def test_a_tolerance_of_one_or_more_is_refused(self):
        with self.assertRaises(ValueError):
            worst_case_limitation_current(1.0, 1.0)


class CurrentAndVoltageTests(unittest.TestCase):
    def test_the_limitation_current_is_taken_at_the_bottom_of_its_band(self):
        self.assertAlmostEqual(
            worst_case_limitation_current(1.0, 0.10), 0.9, places=12
        )

    def test_the_bus_voltage_is_taken_at_the_top_of_its_band(self):
        self.assertAlmostEqual(worst_case_bus_voltage(28.0, 0.10), 30.8, places=9)

    def test_a_zero_limitation_current_is_refused(self):
        with self.assertRaises(ValueError):
            worst_case_limitation_current(0.0)

    def test_a_non_numeric_bus_voltage_is_refused(self):
        with self.assertRaises(ValueError):
            worst_case_bus_voltage("28 V")


class TripTimeTests(unittest.TestCase):
    def test_the_fastest_row_of_the_family_governs(self):
        self.assertAlmostEqual(shortest_trip_time([0.05, 0.01, 0.2]), 0.01, places=12)

    def test_the_trip_time_tolerance_shortens_it_further(self):
        self.assertAlmostEqual(
            shortest_trip_time([0.01, 0.05], 0.20), 0.008, places=12
        )

    def test_a_single_declared_trip_time_is_accepted(self):
        self.assertAlmostEqual(shortest_trip_time(0.01), 0.01, places=12)

    def test_an_empty_trip_time_family_is_refused(self):
        with self.assertRaises(ValueError):
            shortest_trip_time([])

    def test_a_non_positive_trip_time_is_refused(self):
        with self.assertRaises(ValueError):
            shortest_trip_time([0.01, 0.0])

    def test_a_string_trip_time_family_is_refused(self):
        with self.assertRaises(ValueError):
            shortest_trip_time("10 ms")


class ChargeTimeTests(unittest.TestCase):
    def test_the_charge_time_is_the_charge_over_the_limitation_current(self):
        self.assertAlmostEqual(
            filter_charge_time(100.0e-6, 30.0, 1.0), 3.0e-3, places=12
        )

    def test_a_weaker_limiter_charges_more_slowly(self):
        self.assertAlmostEqual(
            filter_charge_time(100.0e-6, 30.0, 0.5), 6.0e-3, places=12
        )

    def test_a_zero_current_is_refused(self):
        with self.assertRaises(ValueError):
            filter_charge_time(100.0e-6, 30.0, 0.0)

    def test_the_separation_counts_charge_times_inside_the_trip(self):
        self.assertAlmostEqual(charge_to_trip_ratio(9.0e-3, 3.0e-3), 3.0, places=9)

    def test_a_zero_charge_time_is_refused(self):
        with self.assertRaises(ValueError):
            charge_to_trip_ratio(9.0e-3, 0.0)

    def test_the_margin_is_the_surplus_over_the_required_factor(self):
        self.assertAlmostEqual(charge_margin_fraction(3.0, 2.0), 0.5, places=9)

    def test_a_separation_exactly_on_the_factor_is_met(self):
        self.assertTrue(margin_is_met(3.0, 3.0))
        self.assertAlmostEqual(charge_margin_fraction(3.0, 3.0), 0.0, places=12)

    def test_a_separation_below_the_factor_is_not_met(self):
        self.assertFalse(margin_is_met(2.5, 3.0))


class ConditionTests(unittest.TestCase):
    def test_the_nominal_set_applies_no_allowances(self):
        conditions = nominal_conditions(_case())
        self.assertAlmostEqual(conditions["capacitance_f"], 100.0e-6, places=12)
        self.assertAlmostEqual(conditions["voltage_v"], 28.0, places=9)
        self.assertAlmostEqual(conditions["current_a"], 1.0, places=9)
        self.assertAlmostEqual(conditions["trip_time_s"], 0.01, places=12)

    def test_the_worst_case_set_moves_every_number_the_slow_way(self):
        conditions = worst_case_conditions(_case())
        self.assertAlmostEqual(conditions["capacitance_f"], 132.0e-6, places=12)
        self.assertAlmostEqual(conditions["voltage_v"], 30.8, places=9)
        self.assertAlmostEqual(conditions["current_a"], 0.9, places=12)
        self.assertAlmostEqual(conditions["trip_time_s"], 0.008, places=12)

    def test_the_worst_case_charges_more_slowly_than_the_nominal(self):
        required = 1.5
        nominal = evaluate_conditions(nominal_conditions(_case()), required)
        worst = evaluate_conditions(worst_case_conditions(_case()), required)
        self.assertLess(nominal["charge_time_s"], worst["charge_time_s"])
        self.assertLess(worst["charge_to_trip_ratio"], nominal["charge_to_trip_ratio"])

    def test_a_non_mapping_condition_set_is_refused(self):
        with self.assertRaises(ValueError):
            evaluate_conditions(["capacitance_f"], 1.5)


class AssessmentTests(unittest.TestCase):
    def test_the_reference_case_clears_the_required_factor(self):
        result = assess_filter_charge_margin(_case())
        self.assertEqual(result["verdict"], CHARGE_MARGIN_MET)
        self.assertEqual(result["findings"], [])
        self.assertAlmostEqual(
            result["worst_case"]["charge_time_s"], 132.0e-6 * 30.8 / 0.9, places=12
        )

    def test_a_missing_capacitance_closes_the_assessment(self):
        case = _case()
        del case["filter_capacitance_f"]
        self.assertEqual(
            assess_filter_charge_margin(case)["verdict"],
            FILTER_CAPACITANCE_NOT_ESTABLISHED,
        )

    def test_a_missing_limitation_current_closes_the_assessment(self):
        case = _case()
        del case["limitation_current_a"]
        self.assertEqual(
            assess_filter_charge_margin(case)["verdict"],
            LIMITATION_CURRENT_NOT_ESTABLISHED,
        )

    def test_a_missing_bus_voltage_closes_the_assessment(self):
        case = _case()
        del case["bus_voltage_v"]
        self.assertEqual(
            assess_filter_charge_margin(case)["verdict"], BUS_VOLTAGE_NOT_ESTABLISHED
        )

    def test_a_missing_trip_time_closes_the_assessment(self):
        case = _case()
        del case["trip_times_s"]
        self.assertEqual(
            assess_filter_charge_margin(case)["verdict"], TRIP_TIME_NOT_ESTABLISHED
        )

    def test_a_missing_required_factor_closes_the_assessment(self):
        case = _case()
        del case["required_margin_factor"]
        self.assertEqual(
            assess_filter_charge_margin(case)["verdict"],
            REQUIRED_MARGIN_NOT_ESTABLISHED,
        )

    def test_a_demanding_factor_is_missed_at_the_corner(self):
        result = assess_filter_charge_margin(_case(required_margin_factor=3.0))
        self.assertEqual(result["verdict"], CHARGE_MARGIN_NOT_MET)
        self.assertIn("at the corner", result["findings"][0])

    def test_a_nominal_only_pass_is_called_out(self):
        result = assess_filter_charge_margin(_case(required_margin_factor=3.0))
        self.assertTrue(
            any("nominal-only case" in note for note in result["advisories"])
        )

    def test_a_missing_drift_allowance_is_advised(self):
        case = _case()
        del case["capacitance_ageing_fraction"]
        result = assess_filter_charge_margin(case)
        self.assertTrue(
            any("beginning-of-life" in note for note in result["advisories"])
        )

    def test_a_declared_drift_allowance_raises_no_such_advisory(self):
        result = assess_filter_charge_margin(_case())
        self.assertFalse(
            any("beginning-of-life" in note for note in result["advisories"])
        )

    def test_a_factor_of_one_leaves_no_separation_and_is_advised(self):
        result = assess_filter_charge_margin(_case(required_margin_factor=1.0))
        self.assertTrue(
            any("leaves no separation" in note for note in result["advisories"])
        )

    def test_a_separation_landing_on_the_factor_still_passes(self):
        result = assess_filter_charge_margin(
            {
                "filter_capacitance_f": 100.0e-6,
                "bus_voltage_v": 30.0,
                "limitation_current_a": 1.0,
                "trip_times_s": [0.009],
                "required_margin_factor": 3.0,
                "capacitance_ageing_fraction": 0.0,
            }
        )
        self.assertEqual(result["verdict"], CHARGE_MARGIN_MET)
        self.assertAlmostEqual(
            result["worst_case"]["margin_fraction"], 0.0, places=12
        )

    def test_a_thin_corner_pass_is_advised(self):
        result = assess_filter_charge_margin(
            {
                "filter_capacitance_f": 100.0e-6,
                "bus_voltage_v": 30.0,
                "limitation_current_a": 1.0,
                "trip_times_s": [0.009],
                "required_margin_factor": 2.9,
                "capacitance_ageing_fraction": 0.0,
            }
        )
        self.assertTrue(
            any("clears the required factor by only" in note
                for note in result["advisories"])
        )

    def test_a_non_mapping_case_is_refused(self):
        with self.assertRaises(ValueError):
            assess_filter_charge_margin(["filter_capacitance_f"])


if __name__ == "__main__":
    unittest.main()
