"""Contract tests for the clause 5.2.7.5.1 faulted start-up logic."""

import math
import unittest

from e2020_startup_into_faulted_output_logic import (
    ABSOLUTE_ZERO_C,
    ENERGY_TOLERANCE_J,
    POWER_TOLERANCE_W,
    TEMPERATURE_TOLERANCE_C,
    assess_fault_case,
    assess_startup_into_fault,
    categorize_fault,
    junction_temperature_c,
    operating_point,
    prospective_current_a,
    pulse_energy_j,
    validate_bus,
    validate_fault,
    validate_limiter,
    worst_case_limit_current_a,
)

# A 5 A latching limiter on a 28 V regulated bus, 10 ms before it latches off.
LIMITER = {
    "limit_current_a": 5.0,
    "trip_delay_s": 0.010,
    "max_dissipation_w": 200.0,
    "max_junction_temperature_c": 125.0,
    "thermal_resistance_c_per_w": 0.4,
    "current_limit_tolerance": 0.0,
    "max_pulse_energy_j": 2.0,
}
BUS = {"bus_voltage_v": 28.0, "baseplate_temperature_c": 40.0}
SHORT = {"id": "hard-short", "fault_resistance_ohm": 0.0}
OVERLOAD = {"id": "partial-overload", "fault_resistance_ohm": 2.0}
GOOD_LOAD = {"id": "rated-load", "fault_resistance_ohm": 10.0}


class ValidateLimiterTests(unittest.TestCase):
    def test_returns_normalised_ratings(self):
        record = validate_limiter(LIMITER)
        self.assertAlmostEqual(record["limit_current_a"], 5.0, places=9)
        self.assertAlmostEqual(record["current_limit_tolerance"], 0.0, places=9)

    def test_absent_pulse_energy_rating_is_none_not_zero(self):
        spec = dict(LIMITER)
        del spec["max_pulse_energy_j"]
        self.assertIsNone(validate_limiter(spec)["max_pulse_energy_j"])

    def test_zero_limit_current_rejected(self):
        with self.assertRaises(ValueError):
            validate_limiter(dict(LIMITER, limit_current_a=0.0))

    def test_zero_trip_delay_rejected(self):
        with self.assertRaises(ValueError):
            validate_limiter(dict(LIMITER, trip_delay_s=0.0))

    def test_negative_thermal_resistance_rejected(self):
        with self.assertRaises(ValueError):
            validate_limiter(dict(LIMITER, thermal_resistance_c_per_w=-0.1))

    def test_junction_rating_below_absolute_zero_rejected(self):
        with self.assertRaises(ValueError):
            validate_limiter(
                dict(LIMITER, max_junction_temperature_c=ABSOLUTE_ZERO_C - 1.0)
            )

    def test_tolerance_of_one_or_more_rejected(self):
        with self.assertRaises(ValueError):
            validate_limiter(dict(LIMITER, current_limit_tolerance=1.0))

    def test_missing_rating_rejected(self):
        spec = dict(LIMITER)
        del spec["max_dissipation_w"]
        with self.assertRaises(ValueError):
            validate_limiter(spec)

    def test_non_mapping_limiter_rejected(self):
        with self.assertRaises(ValueError):
            validate_limiter(["limit_current_a", 5.0])


class ValidateBusAndFaultTests(unittest.TestCase):
    def test_baseplate_defaults_when_not_declared(self):
        record = validate_bus({"bus_voltage_v": 28.0})
        self.assertAlmostEqual(record["baseplate_temperature_c"], 20.0, places=9)

    def test_zero_bus_voltage_rejected(self):
        with self.assertRaises(ValueError):
            validate_bus({"bus_voltage_v": 0.0})

    def test_hard_short_resistance_of_zero_accepted(self):
        record = validate_fault(SHORT)
        self.assertAlmostEqual(record["total_resistance_ohm"], 0.0, places=12)

    def test_harness_resistance_adds_in_series(self):
        record = validate_fault(
            {"fault_resistance_ohm": 0.0, "harness_resistance_ohm": 0.25}
        )
        self.assertAlmostEqual(record["total_resistance_ohm"], 0.25, places=12)

    def test_negative_fault_resistance_rejected(self):
        with self.assertRaises(ValueError):
            validate_fault({"fault_resistance_ohm": -1.0})

    def test_zero_fault_duration_rejected(self):
        with self.assertRaises(ValueError):
            validate_fault({"fault_resistance_ohm": 1.0, "fault_duration_s": 0.0})

    def test_fault_without_resistance_rejected(self):
        with self.assertRaises(ValueError):
            validate_fault({"id": "x"})


class ProspectiveCurrentTests(unittest.TestCase):
    def test_finite_resistance_gives_ohms_law(self):
        self.assertAlmostEqual(prospective_current_a(28.0, 2.0), 14.0, places=9)

    def test_hard_short_is_unbounded_not_a_division_error(self):
        self.assertTrue(math.isinf(prospective_current_a(28.0, 0.0)))

    def test_negative_resistance_rejected(self):
        with self.assertRaises(ValueError):
            prospective_current_a(28.0, -1.0)

    def test_limit_band_top_carries_the_tolerance(self):
        record = validate_limiter(dict(LIMITER, current_limit_tolerance=0.1))
        self.assertAlmostEqual(worst_case_limit_current_a(record), 5.5, places=9)

    def test_limit_band_top_equals_the_limit_when_no_tolerance_declared(self):
        self.assertAlmostEqual(worst_case_limit_current_a(LIMITER), 5.0, places=9)


class CategorizeFaultTests(unittest.TestCase):
    def test_unbounded_current_is_a_short(self):
        self.assertEqual(categorize_fault(math.inf, 5.0), "short")

    def test_ten_times_the_limit_is_a_short_at_the_boundary(self):
        self.assertEqual(categorize_fault(50.0, 5.0), "short")

    def test_between_the_limit_and_the_short_multiple_is_an_overload(self):
        self.assertEqual(categorize_fault(14.0, 5.0), "overload")

    def test_at_the_limit_is_inside_the_rating(self):
        self.assertEqual(categorize_fault(5.0, 5.0), "within-rating")

    def test_short_multiple_of_one_rejected(self):
        with self.assertRaises(ValueError):
            categorize_fault(50.0, 5.0, short_multiple=1.0)

    def test_nan_current_rejected(self):
        with self.assertRaises(ValueError):
            categorize_fault(float("nan"), 5.0)


class OperatingPointTests(unittest.TestCase):
    def test_hard_short_puts_the_whole_bus_across_the_element(self):
        point = operating_point(LIMITER, BUS, SHORT)
        self.assertTrue(point["limiting"])
        self.assertAlmostEqual(point["element_voltage_v"], 28.0, places=9)
        self.assertAlmostEqual(point["dissipation_w"], 140.0, places=9)

    def test_partial_overload_splits_the_bus_with_the_fault(self):
        point = operating_point(LIMITER, BUS, OVERLOAD)
        self.assertTrue(point["limiting"])
        self.assertAlmostEqual(point["output_voltage_v"], 10.0, places=9)
        self.assertAlmostEqual(point["element_voltage_v"], 18.0, places=9)
        self.assertAlmostEqual(point["dissipation_w"], 90.0, places=9)

    def test_load_inside_the_rating_does_not_drive_limiting(self):
        point = operating_point(LIMITER, BUS, GOOD_LOAD)
        self.assertFalse(point["limiting"])
        self.assertAlmostEqual(point["output_current_a"], 2.8, places=9)

    def test_limit_tolerance_raises_the_dissipation_of_a_short(self):
        point = operating_point(dict(LIMITER, current_limit_tolerance=0.1), BUS, SHORT)
        self.assertAlmostEqual(point["dissipation_w"], 154.0, places=9)

    def test_element_voltage_never_goes_negative(self):
        point = operating_point(LIMITER, BUS, {"fault_resistance_ohm": 5.6})
        self.assertGreaterEqual(point["element_voltage_v"], 0.0)


class ThermalTests(unittest.TestCase):
    def test_junction_rises_above_the_baseplate(self):
        self.assertAlmostEqual(junction_temperature_c(140.0, 0.4, 40.0), 96.0, places=9)

    def test_zero_thermal_resistance_leaves_the_baseplate(self):
        self.assertAlmostEqual(junction_temperature_c(140.0, 0.0, 40.0), 40.0, places=9)

    def test_negative_dissipation_rejected(self):
        with self.assertRaises(ValueError):
            junction_temperature_c(-1.0, 0.4, 40.0)

    def test_pulse_energy_is_power_times_hold(self):
        self.assertAlmostEqual(pulse_energy_j(140.0, 0.010), 1.4, places=9)

    def test_negative_hold_time_rejected(self):
        with self.assertRaises(ValueError):
            pulse_energy_j(140.0, -0.001)


class AssessFaultCaseTests(unittest.TestCase):
    def test_short_inside_every_rating_passes(self):
        case = assess_fault_case(LIMITER, BUS, SHORT)
        self.assertTrue(case["within_rating"])
        self.assertEqual(case["fault_kind"], "short")
        self.assertAlmostEqual(case["junction_temperature_c"], 96.0, places=9)

    def test_dissipation_above_the_rating_is_a_finding(self):
        case = assess_fault_case(dict(LIMITER, max_dissipation_w=100.0), BUS, SHORT)
        self.assertFalse(case["within_rating"])
        self.assertTrue(any("dissipates" in f for f in case["findings"]))

    def test_dissipation_exactly_at_the_rating_is_not_a_finding(self):
        case = assess_fault_case(dict(LIMITER, max_dissipation_w=140.0), BUS, SHORT)
        self.assertAlmostEqual(case["dissipation_margin_w"], 0.0, places=9)
        self.assertTrue(case["within_rating"])

    def test_junction_above_the_rating_is_a_finding(self):
        case = assess_fault_case(
            dict(LIMITER, max_junction_temperature_c=90.0), BUS, SHORT
        )
        self.assertTrue(any("junction reaches" in f for f in case["findings"]))

    def test_junction_exactly_at_the_rating_is_not_a_finding(self):
        case = assess_fault_case(
            dict(LIMITER, max_junction_temperature_c=96.0), BUS, SHORT
        )
        self.assertAlmostEqual(case["thermal_margin_c"], 0.0, places=9)
        self.assertTrue(case["within_rating"])

    def test_pulse_energy_above_the_rating_is_a_finding(self):
        case = assess_fault_case(dict(LIMITER, max_pulse_energy_j=1.0), BUS, SHORT)
        self.assertTrue(any("carried over" in f for f in case["findings"]))

    def test_pulse_energy_exactly_at_the_rating_is_not_a_finding(self):
        case = assess_fault_case(dict(LIMITER, max_pulse_energy_j=1.4), BUS, SHORT)
        self.assertAlmostEqual(case["energy_margin_j"], 0.0, places=9)
        self.assertTrue(case["within_rating"])

    def test_no_energy_rating_leaves_the_margin_unset_rather_than_zero(self):
        spec = dict(LIMITER)
        del spec["max_pulse_energy_j"]
        case = assess_fault_case(spec, BUS, SHORT)
        self.assertIsNone(case["energy_margin_j"])

    def test_fault_clearing_before_the_trip_delay_shortens_the_hold(self):
        case = assess_fault_case(
            LIMITER, BUS, dict(SHORT, fault_duration_s=0.004)
        )
        self.assertAlmostEqual(case["hold_time_s"], 0.004, places=9)
        self.assertAlmostEqual(case["pulse_energy_j"], 0.56, places=9)

    def test_fault_outlasting_the_trip_delay_holds_for_the_trip_delay(self):
        case = assess_fault_case(LIMITER, BUS, dict(SHORT, fault_duration_s=5.0))
        self.assertAlmostEqual(case["hold_time_s"], 0.010, places=9)

    def test_load_inside_the_rating_reports_that_it_exercises_nothing(self):
        case = assess_fault_case(LIMITER, BUS, GOOD_LOAD)
        self.assertFalse(case["within_rating"])
        self.assertTrue(any("does not start the unit" in f for f in case["findings"]))

    def test_colder_baseplate_buys_thermal_margin(self):
        warm = assess_fault_case(LIMITER, BUS, SHORT)
        cold = assess_fault_case(
            LIMITER, dict(BUS, baseplate_temperature_c=-10.0), SHORT
        )
        self.assertAlmostEqual(
            cold["thermal_margin_c"] - warm["thermal_margin_c"], 50.0, places=9
        )


class AssessStartupIntoFaultTests(unittest.TestCase):
    def _spec(self, **over):
        spec = {"limiter": LIMITER, "bus": BUS, "faults": [SHORT, OVERLOAD]}
        spec.update(over)
        return spec

    def test_short_and_overload_inside_rating_is_compliant(self):
        result = assess_startup_into_fault(self._spec())
        self.assertTrue(result["compliant"])
        self.assertEqual(result["fault_kinds"], ["overload", "short"])

    def test_worst_case_is_the_hard_short(self):
        result = assess_startup_into_fault(self._spec())
        self.assertEqual(result["worst_case"]["fault_id"], "hard-short")

    def test_a_set_without_a_short_is_a_coverage_finding(self):
        result = assess_startup_into_fault(self._spec(faults=[OVERLOAD]))
        self.assertFalse(result["compliant"])
        self.assertTrue(any("no hard short" in f for f in result["findings"]))

    def test_a_set_without_an_overload_is_a_coverage_finding(self):
        result = assess_startup_into_fault(self._spec(faults=[SHORT]))
        self.assertFalse(result["compliant"])
        self.assertTrue(any("no overload" in f for f in result["findings"]))

    def test_rating_breach_propagates_to_the_set_verdict(self):
        result = assess_startup_into_fault(
            self._spec(limiter=dict(LIMITER, max_junction_temperature_c=50.0))
        )
        self.assertFalse(result["compliant"])

    def test_duplicate_fault_ids_rejected(self):
        with self.assertRaises(ValueError):
            assess_startup_into_fault(self._spec(faults=[SHORT, dict(OVERLOAD, id="hard-short")]))

    def test_empty_fault_set_rejected(self):
        with self.assertRaises(ValueError):
            assess_startup_into_fault(self._spec(faults=[]))

    def test_missing_spec_key_rejected(self):
        spec = self._spec()
        del spec["bus"]
        with self.assertRaises(ValueError):
            assess_startup_into_fault(spec)

    def test_non_mapping_spec_rejected(self):
        with self.assertRaises(ValueError):
            assess_startup_into_fault("limiter")

    def test_tolerances_stay_representation_sized(self):
        self.assertLess(POWER_TOLERANCE_W, 1e-6)
        self.assertLess(TEMPERATURE_TOLERANCE_C, 1e-6)
        self.assertLess(ENERGY_TOLERANCE_J, 1e-6)


if __name__ == "__main__":
    unittest.main()
