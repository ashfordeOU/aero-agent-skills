#!/usr/bin/env python3
"""Gate 3 contract test for e20-battery-cell-rating-limits (offline, stdlib)."""

import copy
import unittest

from e20_battery_cell_rating_limits_logic import (
    apply_derating,
    assess_operating_envelope,
    c_rate,
    check_current,
    check_temperature,
    check_voltage,
    evaluate_operating_point,
    validate_cell_ratings,
)

BASE_RATINGS = {
    "chemistry": "lithium-ion",
    "capacity_ah": 5.0,
    "temperature_c": {
        "charge": (0.0, 45.0),
        "discharge": (-20.0, 60.0),
        "storage": (-30.0, 35.0),
    },
    "voltage_v": {"max_charge": 4.10, "min_discharge": 2.75},
    "current_a": {
        "max_charge": 2.5,
        "max_discharge": 10.0,
        "max_storage_leakage": 0.05,
    },
}

DERATING = {
    "voltage_factor": 0.98,
    "current_factor": 0.80,
    "temperature_margin_k": 5.0,
}


def ratings(**overrides):
    value = copy.deepcopy(BASE_RATINGS)
    value.update(copy.deepcopy(overrides))
    return value


def charge_point(**overrides):
    point = {
        "id": "OP-1",
        "mode": "charge",
        "temperature_c": 20.0,
        "voltage_v": 4.05,
        "current_a": 2.0,
    }
    point.update(overrides)
    return point


def discharge_point(**overrides):
    point = {
        "id": "OP-2",
        "mode": "discharge",
        "temperature_c": 10.0,
        "voltage_v": 3.60,
        "current_a": 5.0,
    }
    point.update(overrides)
    return point


class ValidateRatingsTests(unittest.TestCase):
    def test_normalizes_a_complete_rating_set(self):
        value = validate_cell_ratings(ratings())
        self.assertEqual(value["chemistry"], "lithium-ion")
        self.assertAlmostEqual(value["capacity_ah"], 5.0, places=6)
        self.assertEqual(value["temperature_c"]["charge"], (0.0, 45.0))
        self.assertFalse(value["derated"])

    def test_storage_leakage_limit_defaults_when_absent(self):
        value = validate_cell_ratings(
            ratings(current_a={"max_charge": 2.5, "max_discharge": 10.0})
        )
        self.assertGreater(value["current_a"]["max_storage_leakage"], 0.0)

    def test_missing_chemistry_raises(self):
        with self.assertRaises(ValueError):
            validate_cell_ratings(ratings(chemistry="  "))

    def test_non_positive_capacity_raises(self):
        with self.assertRaises(ValueError):
            validate_cell_ratings(ratings(capacity_ah=0.0))

    def test_missing_temperature_mode_raises(self):
        with self.assertRaises(ValueError):
            validate_cell_ratings(
                ratings(
                    temperature_c={
                        "charge": (0.0, 45.0),
                        "discharge": (-20.0, 60.0),
                    }
                )
            )

    def test_inverted_temperature_window_raises(self):
        broken = ratings()
        broken["temperature_c"]["charge"] = (45.0, 0.0)
        with self.assertRaises(ValueError):
            validate_cell_ratings(broken)

    def test_temperature_window_that_is_not_a_pair_raises(self):
        broken = ratings()
        broken["temperature_c"]["storage"] = (-30.0,)
        with self.assertRaises(ValueError):
            validate_cell_ratings(broken)

    def test_discharge_floor_above_charge_ceiling_raises(self):
        with self.assertRaises(ValueError):
            validate_cell_ratings(
                ratings(voltage_v={"max_charge": 2.70, "min_discharge": 2.75})
            )

    def test_missing_current_mapping_raises(self):
        broken = ratings()
        del broken["current_a"]
        with self.assertRaises(ValueError):
            validate_cell_ratings(broken)

    def test_non_positive_charge_current_raises(self):
        with self.assertRaises(ValueError):
            validate_cell_ratings(
                ratings(current_a={"max_charge": 0.0, "max_discharge": 10.0})
            )

    def test_non_mapping_rating_set_raises(self):
        with self.assertRaises(ValueError):
            validate_cell_ratings("lithium-ion")


class DeratingTests(unittest.TestCase):
    def test_policy_tightens_every_parameter(self):
        derated = apply_derating(ratings(), DERATING)
        self.assertTrue(derated["derated"])
        self.assertAlmostEqual(derated["voltage_v"]["max_charge"], 4.018, places=6)
        self.assertAlmostEqual(
            derated["voltage_v"]["min_discharge"], 2.806122, places=4
        )
        self.assertAlmostEqual(derated["current_a"]["max_charge"], 2.0, places=6)
        self.assertAlmostEqual(derated["current_a"]["max_discharge"], 8.0, places=6)
        self.assertEqual(derated["temperature_c"]["charge"], (5.0, 40.0))

    def test_empty_policy_leaves_the_envelope_unchanged(self):
        derated = apply_derating(ratings(), {})
        self.assertAlmostEqual(derated["voltage_v"]["max_charge"], 4.10, places=6)
        self.assertEqual(derated["temperature_c"]["discharge"], (-20.0, 60.0))

    def test_voltage_factor_that_collapses_the_window_raises(self):
        with self.assertRaises(ValueError):
            apply_derating(ratings(), {"voltage_factor": 0.60})

    def test_temperature_margin_that_collapses_a_window_raises(self):
        with self.assertRaises(ValueError):
            apply_derating(ratings(), {"temperature_margin_k": 40.0})

    def test_factor_above_unity_raises(self):
        with self.assertRaises(ValueError):
            apply_derating(ratings(), {"current_factor": 1.2})

    def test_factor_of_zero_raises(self):
        with self.assertRaises(ValueError):
            apply_derating(ratings(), {"voltage_factor": 0.0})

    def test_negative_temperature_margin_raises(self):
        with self.assertRaises(ValueError):
            apply_derating(ratings(), {"temperature_margin_k": -1.0})

    def test_non_mapping_policy_raises(self):
        with self.assertRaises(ValueError):
            apply_derating(ratings(), 0.8)


class CRateTests(unittest.TestCase):
    def test_c_rate_is_current_over_capacity(self):
        self.assertAlmostEqual(c_rate(2.5, 5.0), 0.5, places=6)

    def test_zero_capacity_raises(self):
        with self.assertRaises(ValueError):
            c_rate(2.5, 0.0)

    def test_negative_current_raises(self):
        with self.assertRaises(ValueError):
            c_rate(-1.0, 5.0)


class TemperatureCheckTests(unittest.TestCase):
    def test_temperature_inside_the_window(self):
        verdict = check_temperature(20.0, "charge", ratings())
        self.assertTrue(verdict["within_limits"])
        self.assertAlmostEqual(verdict["margin"], 20.0, places=6)
        self.assertAlmostEqual(verdict["normalized_margin"], 0.444444, places=4)

    def test_temperature_exactly_on_the_lower_limit_passes(self):
        verdict = check_temperature(0.0, "charge", ratings())
        self.assertTrue(verdict["within_limits"])
        self.assertAlmostEqual(verdict["margin"], 0.0, places=9)

    def test_temperature_below_the_charge_window_fails(self):
        verdict = check_temperature(-5.0, "charge", ratings())
        self.assertFalse(verdict["within_limits"])
        self.assertAlmostEqual(verdict["margin"], -5.0, places=6)

    def test_same_temperature_can_pass_discharge_and_fail_charge(self):
        self.assertFalse(check_temperature(-5.0, "charge", ratings())["within_limits"])
        self.assertTrue(
            check_temperature(-5.0, "discharge", ratings())["within_limits"]
        )

    def test_unknown_mode_raises(self):
        with self.assertRaises(ValueError):
            check_temperature(20.0, "trickle", ratings())

    def test_non_numeric_temperature_raises(self):
        with self.assertRaises(ValueError):
            check_temperature("20", "charge", ratings())


class VoltageCheckTests(unittest.TestCase):
    def test_charge_mode_is_bounded_above_only(self):
        verdict = check_voltage(4.05, "charge", ratings())
        self.assertIsNone(verdict["lower_limit"])
        self.assertTrue(verdict["within_limits"])
        self.assertAlmostEqual(verdict["margin"], 0.05, places=6)

    def test_voltage_exactly_on_the_charge_ceiling_passes(self):
        verdict = check_voltage(4.10, "charge", ratings())
        self.assertTrue(verdict["within_limits"])
        self.assertAlmostEqual(verdict["margin"], 0.0, places=9)

    def test_overvoltage_on_charge_fails(self):
        verdict = check_voltage(4.25, "charge", ratings())
        self.assertFalse(verdict["within_limits"])
        self.assertAlmostEqual(verdict["margin"], -0.15, places=6)

    def test_discharge_mode_is_bounded_both_ways(self):
        verdict = check_voltage(3.60, "discharge", ratings())
        self.assertAlmostEqual(verdict["lower_limit"], 2.75, places=6)
        self.assertAlmostEqual(verdict["upper_limit"], 4.10, places=6)
        self.assertTrue(verdict["within_limits"])

    def test_undervoltage_on_discharge_fails(self):
        verdict = check_voltage(2.70, "discharge", ratings())
        self.assertFalse(verdict["within_limits"])
        self.assertAlmostEqual(verdict["margin"], -0.05, places=6)

    def test_non_positive_voltage_raises(self):
        with self.assertRaises(ValueError):
            check_voltage(0.0, "discharge", ratings())


class CurrentCheckTests(unittest.TestCase):
    def test_charge_current_within_limit_reports_c_rate(self):
        verdict = check_current(2.0, "charge", ratings())
        self.assertTrue(verdict["within_limits"])
        self.assertAlmostEqual(verdict["c_rate"], 0.4, places=6)

    def test_charge_current_over_limit_fails(self):
        verdict = check_current(3.0, "charge", ratings())
        self.assertFalse(verdict["within_limits"])
        self.assertAlmostEqual(verdict["margin"], -0.5, places=6)

    def test_discharge_limit_is_higher_than_the_charge_limit(self):
        self.assertTrue(check_current(8.0, "discharge", ratings())["within_limits"])
        self.assertFalse(check_current(8.0, "charge", ratings())["within_limits"])

    def test_discharge_current_exactly_on_the_limit_passes(self):
        verdict = check_current(10.0, "discharge", ratings())
        self.assertTrue(verdict["within_limits"])
        self.assertAlmostEqual(verdict["c_rate"], 2.0, places=6)

    def test_storage_mode_allows_only_leakage(self):
        self.assertFalse(check_current(0.06, "storage", ratings())["within_limits"])
        self.assertTrue(check_current(0.02, "storage", ratings())["within_limits"])

    def test_negative_current_raises(self):
        with self.assertRaises(ValueError):
            check_current(-2.0, "charge", ratings())


class OperatingPointTests(unittest.TestCase):
    def test_clean_point_passes_and_names_its_limiting_parameter(self):
        record = evaluate_operating_point(charge_point(), ratings())
        self.assertTrue(record["within_limits"])
        self.assertEqual(record["exceedances"], ())
        self.assertEqual(record["limiting_parameter"], "voltage")
        self.assertAlmostEqual(
            record["limiting_normalized_margin"], 0.012195, places=5
        )

    def test_every_violated_parameter_is_listed(self):
        record = evaluate_operating_point(
            charge_point(temperature_c=-10.0, voltage_v=4.30, current_a=3.0),
            ratings(),
        )
        self.assertFalse(record["within_limits"])
        self.assertEqual(len(record["exceedances"]), 3)

    def test_missing_parameter_raises(self):
        point = charge_point()
        del point["current_a"]
        with self.assertRaises(ValueError):
            evaluate_operating_point(point, ratings())

    def test_unknown_mode_raises(self):
        with self.assertRaises(ValueError):
            evaluate_operating_point(charge_point(mode="float"), ratings())

    def test_missing_identifier_raises(self):
        with self.assertRaises(ValueError):
            evaluate_operating_point(charge_point(id=""), ratings())

    def test_non_mapping_point_raises(self):
        with self.assertRaises(ValueError):
            evaluate_operating_point(["OP-1"], ratings())


class EnvelopeTests(unittest.TestCase):
    def test_duty_profile_inside_the_base_envelope(self):
        result = assess_operating_envelope(
            [charge_point(), discharge_point()], ratings()
        )
        self.assertTrue(result["within_envelope"])
        self.assertEqual(result["worst_point_id"], "OP-1")
        self.assertEqual(result["worst_parameter"], "voltage")
        self.assertFalse(result["ratings"]["derated"])

    def test_derating_turns_a_passing_point_into_a_finding(self):
        result = assess_operating_envelope(
            [charge_point(), discharge_point()], ratings(), DERATING
        )
        self.assertFalse(result["within_envelope"])
        self.assertTrue(result["ratings"]["derated"])
        self.assertEqual(len(result["findings"]), 1)
        self.assertIn("voltage in charge", result["findings"][0])

    def test_current_exactly_on_a_derated_limit_still_passes(self):
        result = assess_operating_envelope(
            [charge_point(voltage_v=3.90)], ratings(), DERATING
        )
        self.assertTrue(result["within_envelope"])

    def test_duplicate_point_identifier_raises(self):
        with self.assertRaises(ValueError):
            assess_operating_envelope(
                [charge_point(), charge_point()], ratings()
            )

    def test_empty_duty_profile_raises(self):
        with self.assertRaises(ValueError):
            assess_operating_envelope([], ratings())

    def test_invalid_rating_set_raises(self):
        with self.assertRaises(ValueError):
            assess_operating_envelope([charge_point()], ratings(capacity_ah=-1.0))


if __name__ == "__main__":
    unittest.main()
