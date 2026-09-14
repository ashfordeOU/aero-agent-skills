"""Contract tests for the clause 7.5.3 bare cell electrical performance logic."""

import unittest

from e2008_bare_cell_electrical_performance_logic import (
    DEFAULT_REFERENCE_IRRADIANCE_W_M2,
    DEFAULT_REFERENCE_TEMPERATURE_C,
    FILL_FACTOR_CEILING,
    FILL_FACTOR_FLOOR,
    IRRADIANCE_TOLERANCE_FRACTION,
    TEMPERATURE_TOLERANCE_C,
    assess_bare_cell_electrical_performance,
    conditions_within_window,
    conversion_efficiency,
    design_power_w,
    evaluate_cell,
    fill_factor,
    fill_factor_plausible,
    lot_statistics,
    maximum_power_w,
)

LIMITS = {"min_pmpp_w": 1.0, "min_efficiency": 0.25}


def _cell(cell_id="CELL-01", impp_a=0.480, **overrides):
    cell = {
        "id": cell_id,
        "isc_a": 0.510,
        "voc_v": 2.700,
        "impp_a": impp_a,
        "vmpp_v": 2.400,
        "area_cm2": 30.18,
        "irradiance_w_m2": DEFAULT_REFERENCE_IRRADIANCE_W_M2,
        "temperature_c": DEFAULT_REFERENCE_TEMPERATURE_C,
    }
    cell.update(overrides)
    return cell


def _spec(**overrides):
    spec = {
        "cells": [
            _cell("CELL-01", 0.480),
            _cell("CELL-02", 0.478),
            _cell("CELL-03", 0.482),
            _cell("CELL-04", 0.479),
            _cell("CELL-05", 0.481),
        ],
        "limits": dict(LIMITS),
    }
    spec.update(overrides)
    return spec


class PowerAndFillFactorTests(unittest.TestCase):
    def test_maximum_power_is_the_product_of_its_two_coordinates(self):
        self.assertAlmostEqual(maximum_power_w(0.48, 2.4), 1.152, places=9)

    def test_fill_factor_is_the_power_ratio_against_the_two_extremes(self):
        value = fill_factor(0.510, 2.700, 0.480, 2.400)
        self.assertAlmostEqual(value, (0.480 * 2.400) / (0.510 * 2.700), places=9)

    def test_ideal_square_curve_returns_unity_fill_factor(self):
        self.assertAlmostEqual(fill_factor(0.5, 2.5, 0.5, 2.5), 1.0, places=9)

    def test_peak_current_above_short_circuit_is_rejected(self):
        with self.assertRaises(ValueError):
            fill_factor(0.400, 2.700, 0.480, 2.400)

    def test_peak_voltage_above_open_circuit_is_rejected(self):
        with self.assertRaises(ValueError):
            fill_factor(0.510, 2.300, 0.480, 2.400)

    def test_boolean_current_is_rejected(self):
        with self.assertRaises(ValueError):
            maximum_power_w(True, 2.4)

    def test_zero_voltage_is_rejected(self):
        with self.assertRaises(ValueError):
            maximum_power_w(0.48, 0.0)


class EfficiencyTests(unittest.TestCase):
    def test_efficiency_is_power_over_the_incident_flux(self):
        value = conversion_efficiency(1.152, 30.18, DEFAULT_REFERENCE_IRRADIANCE_W_M2)
        expected = 1.152 / (DEFAULT_REFERENCE_IRRADIANCE_W_M2 * 30.18 * 1.0e-4)
        self.assertAlmostEqual(value, expected, places=9)

    def test_doubling_the_area_halves_the_efficiency(self):
        one = conversion_efficiency(1.152, 30.0)
        two = conversion_efficiency(1.152, 60.0)
        self.assertAlmostEqual(two * 2.0, one, places=9)

    def test_negative_area_is_rejected(self):
        with self.assertRaises(ValueError):
            conversion_efficiency(1.152, -30.0)


class ConditionWindowTests(unittest.TestCase):
    def test_reading_at_reference_conditions_is_inside_the_window(self):
        self.assertTrue(
            conditions_within_window(
                DEFAULT_REFERENCE_IRRADIANCE_W_M2, DEFAULT_REFERENCE_TEMPERATURE_C
            )
        )

    def test_reading_exactly_on_the_temperature_edge_is_inside(self):
        edge = DEFAULT_REFERENCE_TEMPERATURE_C + TEMPERATURE_TOLERANCE_C
        self.assertTrue(
            conditions_within_window(DEFAULT_REFERENCE_IRRADIANCE_W_M2, edge)
        )

    def test_reading_far_off_irradiance_is_outside(self):
        far = DEFAULT_REFERENCE_IRRADIANCE_W_M2 * (
            1.0 + 5.0 * IRRADIANCE_TOLERANCE_FRACTION
        )
        self.assertFalse(
            conditions_within_window(far, DEFAULT_REFERENCE_TEMPERATURE_C)
        )

    def test_hot_reading_is_outside_the_window(self):
        hot = DEFAULT_REFERENCE_TEMPERATURE_C + 4.0 * TEMPERATURE_TOLERANCE_C
        self.assertFalse(
            conditions_within_window(DEFAULT_REFERENCE_IRRADIANCE_W_M2, hot)
        )


class PlausibilityTests(unittest.TestCase):
    def test_value_exactly_on_the_floor_is_plausible(self):
        self.assertTrue(fill_factor_plausible(FILL_FACTOR_FLOOR))

    def test_value_exactly_on_the_ceiling_is_plausible(self):
        self.assertTrue(fill_factor_plausible(FILL_FACTOR_CEILING))

    def test_value_far_below_the_floor_is_not_plausible(self):
        self.assertFalse(fill_factor_plausible(0.10))

    def test_inverted_plausibility_band_is_rejected(self):
        with self.assertRaises(ValueError):
            fill_factor_plausible(0.80, 0.95, 0.50)


class LotStatisticsTests(unittest.TestCase):
    def test_mean_and_extremes_of_a_known_lot(self):
        stats = lot_statistics([1.0, 2.0, 3.0, 4.0, 5.0])
        self.assertEqual(stats["count"], 5)
        self.assertAlmostEqual(stats["mean"], 3.0, places=9)
        self.assertAlmostEqual(stats["minimum"], 1.0, places=9)
        self.assertAlmostEqual(stats["maximum"], 5.0, places=9)

    def test_sample_spread_uses_the_n_minus_one_divisor(self):
        stats = lot_statistics([2.0, 4.0, 4.0, 4.0, 5.0, 5.0, 7.0, 9.0])
        self.assertAlmostEqual(stats["spread"], 2.138089935299395, places=9)

    def test_single_measurement_has_no_spread(self):
        stats = lot_statistics([1.2])
        self.assertAlmostEqual(stats["spread"], 0.0, places=9)

    def test_empty_lot_is_rejected(self):
        with self.assertRaises(ValueError):
            lot_statistics([])

    def test_non_sequence_lot_is_rejected(self):
        with self.assertRaises(ValueError):
            lot_statistics({"pmpp_w": 1.2})


class DesignPowerTests(unittest.TestCase):
    def test_design_power_is_the_lower_statistical_bound(self):
        stats = {"mean": 1.20, "spread": 0.01, "minimum": 1.18}
        self.assertAlmostEqual(design_power_w(stats, 3.0), 1.20 - 3.0 * 0.01, places=9)

    def test_design_power_never_rises_above_the_worst_measured_cell(self):
        stats = {"mean": 1.20, "spread": 0.0, "minimum": 1.05}
        self.assertAlmostEqual(design_power_w(stats, 3.0), 1.05, places=9)

    def test_missing_statistic_is_rejected(self):
        with self.assertRaises(ValueError):
            design_power_w({"mean": 1.2, "spread": 0.01})


class CellEvaluationTests(unittest.TestCase):
    def test_good_cell_conforms(self):
        record = evaluate_cell(_cell(), LIMITS)
        self.assertTrue(record["conforms"])
        self.assertAlmostEqual(record["pmpp_w"], 0.480 * 2.400, places=9)

    def test_weak_cell_is_reported_below_the_declared_power(self):
        record = evaluate_cell(_cell(impp_a=0.200), LIMITS)
        self.assertFalse(record["meets_power"])
        self.assertFalse(record["conforms"])

    def test_cell_read_off_window_is_a_finding(self):
        record = evaluate_cell(_cell(temperature_c=60.0), LIMITS)
        self.assertFalse(record["conditions_within_window"])
        self.assertTrue(any("window" in item for item in record["findings"]))

    def test_missing_cell_key_is_rejected(self):
        cell = _cell()
        del cell["area_cm2"]
        with self.assertRaises(ValueError):
            evaluate_cell(cell, LIMITS)

    def test_empty_cell_id_is_rejected(self):
        with self.assertRaises(ValueError):
            evaluate_cell(_cell(id="   "), LIMITS)


class LotAssessmentTests(unittest.TestCase):
    def test_clean_lot_is_valid(self):
        result = assess_bare_cell_electrical_performance(_spec())
        self.assertTrue(result["valid"])
        self.assertEqual(result["cells_assessed"], 5)
        self.assertEqual(result["cells_rejected"], 0)

    def test_design_power_sits_at_or_below_the_worst_cell(self):
        result = assess_bare_cell_electrical_performance(_spec())
        worst = result["power_statistics"]["minimum"]
        self.assertLessEqual(result["design_power_w"], worst)

    def test_short_lot_cannot_support_a_design_decision(self):
        result = assess_bare_cell_electrical_performance(
            _spec(cells=[_cell("CELL-01"), _cell("CELL-02")])
        )
        self.assertFalse(result["valid"])
        self.assertTrue(any("sizing case" in item for item in result["findings"]))

    def test_one_weak_cell_is_counted_as_rejected(self):
        cells = _spec()["cells"]
        cells[2] = _cell("CELL-03", 0.150)
        result = assess_bare_cell_electrical_performance(_spec(cells=cells))
        self.assertEqual(result["cells_rejected"], 1)
        self.assertFalse(result["valid"])

    def test_duplicate_cell_id_is_rejected(self):
        cells = _spec()["cells"]
        cells[4] = _cell("CELL-01", 0.481)
        with self.assertRaises(ValueError):
            assess_bare_cell_electrical_performance(_spec(cells=cells))

    def test_empty_cell_sequence_is_rejected(self):
        with self.assertRaises(ValueError):
            assess_bare_cell_electrical_performance(_spec(cells=[]))

    def test_non_mapping_spec_is_rejected(self):
        with self.assertRaises(ValueError):
            assess_bare_cell_electrical_performance(["cells"])

    def test_zero_minimum_lot_size_is_rejected(self):
        with self.assertRaises(ValueError):
            assess_bare_cell_electrical_performance(_spec(min_lot_size=0))

    def test_wider_bound_lowers_the_design_power(self):
        tight = assess_bare_cell_electrical_performance(_spec(sigma_multiplier=0.0))
        wide = assess_bare_cell_electrical_performance(_spec(sigma_multiplier=6.0))
        self.assertLess(wide["design_power_w"], tight["design_power_w"])


if __name__ == "__main__":
    unittest.main()
