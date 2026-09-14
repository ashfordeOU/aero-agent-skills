"""Contract tests for the clause 7.3.2.2.2 bare-cell current recording run.

Every workflow step the SKILL.md sets out is exercised here, together with
the stop conditions the gate 3 contract reviews: a refused conditions
policy, a bench off the reference irradiance, a cell outside the
temperature band, an unstated or drifted load voltage, and a reading that
puts more current on load than at short circuit.
"""

import unittest

from e2008_bare_cell_acceptance_measurement_process_logic import (
    CELL_READINGS_INCONSISTENT,
    CURRENTS_RECORDED,
    DEFAULT_CONDITIONS_POLICY,
    ILLUMINATION_CONDITIONS_INVALID,
    TEST_VOLTAGE_NOT_STATED,
    TEST_VOLTAGE_SETPOINT_OFF,
    current_at_reference_conditions_a,
    current_density_a_per_m2,
    irradiance_corrected_current_a,
    irradiance_deviation_fraction,
    irradiance_within_tolerance,
    reading_consistent,
    record_bare_cell_currents,
    temperature_corrected_current_a,
    temperature_within_band,
    test_voltage_setpoint_deviation_v,
    test_voltage_setpoint_valid,
    validate_cell_reading,
    validate_conditions_policy,
    validate_illumination,
)

REFERENCE_IRRADIANCE = 1367.0
REFERENCE_TEMPERATURE = 25.0


def _policy(**overrides):
    policy = dict(DEFAULT_CONDITIONS_POLICY)
    policy.update(overrides)
    return policy


def _cells():
    return [
        {
            "id": "bc-01",
            "short_circuit_current_a": 0.504,
            "current_at_test_voltage_a": 0.489,
            "current_temperature_coefficient_per_c": 0.0005,
            "illuminated_area_m2": 0.0030,
        },
        {
            "id": "bc-02",
            "short_circuit_current_a": 0.498,
            "current_at_test_voltage_a": 0.481,
            "current_temperature_coefficient_per_c": 0.0005,
            "illuminated_area_m2": 0.0030,
        },
    ]


def _case(**overrides):
    case = {
        "illumination": {
            "irradiance_w_per_m2": REFERENCE_IRRADIANCE,
            "cell_temperature_c": REFERENCE_TEMPERATURE,
        },
        "stated_test_voltage_v": 2.35,
        "voltage_setpoint_v": 2.35,
        "cells": _cells(),
    }
    case.update(overrides)
    return case


class PolicyTests(unittest.TestCase):
    def test_default_policy_validates(self):
        self.assertIs(
            validate_conditions_policy(DEFAULT_CONDITIONS_POLICY),
            DEFAULT_CONDITIONS_POLICY,
        )

    def test_non_mapping_policy_rejected(self):
        with self.assertRaises(ValueError):
            validate_conditions_policy("reference_irradiance_w_per_m2")

    def test_inverted_temperature_band_rejected(self):
        with self.assertRaises(ValueError):
            validate_conditions_policy(
                _policy(min_cell_temperature_c=40.0, max_cell_temperature_c=10.0)
            )

    def test_reference_temperature_outside_its_own_band_rejected(self):
        with self.assertRaises(ValueError):
            validate_conditions_policy(
                _policy(min_cell_temperature_c=30.0, max_cell_temperature_c=40.0)
            )

    def test_irradiance_tolerance_above_one_rejected(self):
        with self.assertRaises(ValueError):
            validate_conditions_policy(_policy(irradiance_tolerance_fraction=1.5))

    def test_zero_voltage_tolerance_rejected(self):
        with self.assertRaises(ValueError):
            validate_conditions_policy(_policy(test_voltage_tolerance_v=0.0))


class IlluminationTests(unittest.TestCase):
    def test_illumination_is_read_back(self):
        irradiance, temperature = validate_illumination(
            {"irradiance_w_per_m2": 1350.0, "cell_temperature_c": 24.0}
        )
        self.assertAlmostEqual(irradiance, 1350.0, places=9)
        self.assertAlmostEqual(temperature, 24.0, places=9)

    def test_dark_bench_rejected(self):
        with self.assertRaises(ValueError):
            validate_illumination(
                {"irradiance_w_per_m2": 0.0, "cell_temperature_c": 25.0}
            )

    def test_missing_cell_temperature_rejected(self):
        with self.assertRaises(ValueError):
            validate_illumination({"irradiance_w_per_m2": 1367.0})

    def test_deviation_is_zero_at_the_reference(self):
        self.assertAlmostEqual(
            irradiance_deviation_fraction(REFERENCE_IRRADIANCE), 0.0, places=12
        )

    def test_deviation_is_symmetric_about_the_reference(self):
        low = irradiance_deviation_fraction(REFERENCE_IRRADIANCE * 0.99)
        high = irradiance_deviation_fraction(REFERENCE_IRRADIANCE * 1.01)
        self.assertAlmostEqual(low, high, places=9)

    def test_a_bench_exactly_on_the_tolerance_is_admitted(self):
        edge = REFERENCE_IRRADIANCE * (1.0 + 0.02)
        self.assertTrue(irradiance_within_tolerance(edge))

    def test_a_bench_beyond_the_tolerance_is_refused(self):
        self.assertFalse(
            irradiance_within_tolerance(REFERENCE_IRRADIANCE * 1.05)
        )

    def test_a_temperature_on_the_band_edge_is_admitted(self):
        self.assertTrue(temperature_within_band(30.0))

    def test_a_temperature_beyond_the_band_is_refused(self):
        self.assertFalse(temperature_within_band(45.0))


class CorrectionTests(unittest.TestCase):
    def test_irradiance_correction_scales_linearly(self):
        value = irradiance_corrected_current_a(0.5, 1200.0, 1367.0)
        self.assertAlmostEqual(value, 0.5 * (1367.0 / 1200.0), places=12)

    def test_irradiance_correction_at_the_reference_changes_nothing(self):
        value = irradiance_corrected_current_a(0.5, 1367.0, 1367.0)
        self.assertAlmostEqual(value, 0.5, places=12)

    def test_a_dark_measured_irradiance_rejected(self):
        with self.assertRaises(ValueError):
            irradiance_corrected_current_a(0.5, 0.0, 1367.0)

    def test_a_warm_cell_corrects_downwards(self):
        value = temperature_corrected_current_a(0.5, 35.0, 25.0, 0.0005)
        self.assertAlmostEqual(value, 0.5 / (1.0 + 0.0005 * 10.0), places=12)

    def test_temperature_correction_at_the_reference_changes_nothing(self):
        value = temperature_corrected_current_a(0.5, 25.0, 25.0, 0.0005)
        self.assertAlmostEqual(value, 0.5, places=12)

    def test_a_coefficient_that_inverts_the_current_rejected(self):
        with self.assertRaises(ValueError):
            temperature_corrected_current_a(0.5, 125.0, 25.0, -0.02)

    def test_both_corrections_compose(self):
        value = current_at_reference_conditions_a(0.5, 1200.0, 35.0, 0.0005)
        expected = (0.5 * (1367.0 / 1200.0)) / (1.0 + 0.0005 * 10.0)
        self.assertAlmostEqual(value, expected, places=12)

    def test_current_density_divides_by_the_illuminated_area(self):
        self.assertAlmostEqual(
            current_density_a_per_m2(0.6, 0.003), 200.0, places=9
        )

    def test_zero_illuminated_area_rejected(self):
        with self.assertRaises(ValueError):
            current_density_a_per_m2(0.6, 0.0)


class SetpointAndReadingTests(unittest.TestCase):
    def test_setpoint_deviation_is_the_absolute_distance(self):
        self.assertAlmostEqual(
            test_voltage_setpoint_deviation_v(2.353, 2.35), 0.003, places=9
        )

    def test_a_setpoint_inside_tolerance_is_valid(self):
        self.assertTrue(test_voltage_setpoint_valid(2.353, 2.35))

    def test_a_setpoint_outside_tolerance_is_refused(self):
        self.assertFalse(test_voltage_setpoint_valid(2.40, 2.35))

    def test_a_cell_reading_is_read_back_in_full(self):
        identifier, short_circuit, at_voltage, coefficient, area = (
            validate_cell_reading(_cells()[0])
        )
        self.assertEqual(identifier, "bc-01")
        self.assertAlmostEqual(short_circuit, 0.504, places=9)
        self.assertAlmostEqual(at_voltage, 0.489, places=9)
        self.assertAlmostEqual(coefficient, 0.0005, places=12)
        self.assertAlmostEqual(area, 0.0030, places=9)

    def test_a_blank_cell_id_rejected(self):
        cell = _cells()[0]
        cell["id"] = "   "
        with self.assertRaises(ValueError):
            validate_cell_reading(cell)

    def test_a_negative_short_circuit_current_rejected(self):
        cell = _cells()[0]
        cell["short_circuit_current_a"] = -0.5
        with self.assertRaises(ValueError):
            validate_cell_reading(cell)

    def test_an_on_load_current_below_short_circuit_is_consistent(self):
        self.assertTrue(reading_consistent(0.504, 0.489))

    def test_an_equal_pair_is_admitted(self):
        self.assertTrue(reading_consistent(0.5, 0.5))

    def test_an_on_load_current_above_short_circuit_is_refused(self):
        self.assertFalse(reading_consistent(0.48, 0.51))


class RunTests(unittest.TestCase):
    def test_a_clean_run_records_the_currents(self):
        result = record_bare_cell_currents(_case())
        self.assertEqual(result["verdict"], CURRENTS_RECORDED)
        self.assertEqual(result["findings"], [])
        self.assertEqual(len(result["cell_records"]), 2)

    def test_the_reference_run_leaves_the_currents_unchanged(self):
        result = record_bare_cell_currents(_case())
        first = result["cell_records"][0]
        self.assertAlmostEqual(
            first["short_circuit_current_a"],
            first["measured_short_circuit_current_a"],
            places=12,
        )

    def test_the_mean_currents_are_reported(self):
        result = record_bare_cell_currents(_case())
        self.assertAlmostEqual(
            result["mean_short_circuit_current_a"], (0.504 + 0.498) / 2.0, places=12
        )
        self.assertAlmostEqual(
            result["mean_current_at_test_voltage_a"], (0.489 + 0.481) / 2.0, places=12
        )

    def test_an_off_irradiance_bench_invalidates_the_conditions(self):
        result = record_bare_cell_currents(
            _case(
                illumination={
                    "irradiance_w_per_m2": REFERENCE_IRRADIANCE * 1.08,
                    "cell_temperature_c": REFERENCE_TEMPERATURE,
                }
            )
        )
        self.assertEqual(result["verdict"], ILLUMINATION_CONDITIONS_INVALID)
        self.assertTrue(result["findings"])

    def test_a_hot_cell_invalidates_the_conditions(self):
        result = record_bare_cell_currents(
            _case(
                illumination={
                    "irradiance_w_per_m2": REFERENCE_IRRADIANCE,
                    "cell_temperature_c": 48.0,
                }
            )
        )
        self.assertEqual(result["verdict"], ILLUMINATION_CONDITIONS_INVALID)

    def test_an_unstated_test_voltage_closes_the_run(self):
        case = _case()
        del case["stated_test_voltage_v"]
        result = record_bare_cell_currents(case)
        self.assertEqual(result["verdict"], TEST_VOLTAGE_NOT_STATED)

    def test_a_drifted_setpoint_closes_the_run(self):
        result = record_bare_cell_currents(_case(voltage_setpoint_v=2.45))
        self.assertEqual(result["verdict"], TEST_VOLTAGE_SETPOINT_OFF)
        self.assertAlmostEqual(
            result["voltage_setpoint_deviation_v"], 0.1, places=9
        )

    def test_a_swapped_channel_is_caught(self):
        cells = _cells()
        cells[1]["current_at_test_voltage_a"] = 0.6
        result = record_bare_cell_currents(_case(cells=cells))
        self.assertEqual(result["verdict"], CELL_READINGS_INCONSISTENT)
        self.assertTrue(any("bc-02" in note for note in result["findings"]))

    def test_a_duplicate_cell_id_rejected(self):
        cells = _cells()
        cells[1]["id"] = "bc-01"
        with self.assertRaises(ValueError):
            record_bare_cell_currents(_case(cells=cells))

    def test_an_empty_presented_population_rejected(self):
        with self.assertRaises(ValueError):
            record_bare_cell_currents(_case(cells=[]))

    def test_a_missing_illumination_record_rejected(self):
        case = _case()
        del case["illumination"]
        with self.assertRaises(ValueError):
            record_bare_cell_currents(case)

    def test_non_mapping_case_rejected(self):
        with self.assertRaises(ValueError):
            record_bare_cell_currents(["illumination"])

    def test_current_density_travels_with_each_record(self):
        result = record_bare_cell_currents(_case())
        for entry in result["cell_records"]:
            self.assertGreater(
                entry["short_circuit_current_density_a_per_m2"], 1.0
            )


if __name__ == "__main__":
    unittest.main()
