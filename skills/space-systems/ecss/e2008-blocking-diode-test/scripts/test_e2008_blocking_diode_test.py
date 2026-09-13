#!/usr/bin/env python3
"""Contract test for the blocking diode reverse-current test (offline).

Walks the clause workflow step by step: the cold-case open-circuit
voltage the string can reach, the worst-case reverse bias built from it,
the adequacy screen that refuses an under-stressed bench, the referral
of a measured leakage to the reference junction temperature, the
grouping of each diode against the acceptance numbers, the parasitic
loss the population carries, and the verdict that has to stop a campaign
whose bench never reached the flight condition. This is the gate 3
review evidence for the leaf.
"""

import copy
import unittest

from e2008_blocking_diode_test_logic import (
    ABOVE_LIMIT,
    BLOCKING_DIODE_TEST_FAILED,
    BLOCKING_DIODE_TEST_NOT_EVALUATED,
    BLOCKING_DIODE_TEST_PASSED,
    DEFAULT_BLOCKING_DIODE_POLICY,
    REVERSE_CONDUCTING,
    REVERSE_CURRENT_CATEGORIES,
    WITHIN_LIMIT,
    categorize_reverse_current,
    cell_open_circuit_voltage_v,
    evaluate_blocking_diode,
    evaluate_blocking_diode_test,
    parasitic_reverse_power_w,
    reverse_bias_adequacy,
    scale_reverse_current_ua,
    validate_blocking_diode_policy,
    worst_case_reverse_bias_v,
)

FLIGHT_CASE = {
    "cells_in_series": 24,
    "voc_at_reference_v": 2.7,
    "reference_temperature_c": 28.0,
    "coldest_illuminated_temperature_c": -100.0,
    "temperature_coefficient_v_per_k": -0.006,
    "beginning_of_life_margin": 0.02,
}

REQUIRED_BIAS_V = worst_case_reverse_bias_v(FLIGHT_CASE)


def _diode(identifier, current_ua, junction_c=55.0):
    return {
        "id": identifier,
        "measured_reverse_current_ua": current_ua,
        "junction_temperature_c": junction_c,
    }


def _campaign(diodes, applied_v=120.0):
    return {
        "flight_case": copy.deepcopy(FLIGHT_CASE),
        "applied_reverse_voltage_v": applied_v,
        "diodes": list(diodes),
    }


SOUND_CAMPAIGN = _campaign(
    [_diode("d1", 12.0), _diode("d2", 11.0), _diode("d3", 12.5), _diode("d4", 10.5)]
)


class PolicyTests(unittest.TestCase):
    def test_default_policy_validates(self):
        self.assertIs(
            validate_blocking_diode_policy(DEFAULT_BLOCKING_DIODE_POLICY),
            DEFAULT_BLOCKING_DIODE_POLICY,
        )

    def test_non_mapping_policy_rejected(self):
        with self.assertRaises(ValueError):
            validate_blocking_diode_policy("default")

    def test_zero_reverse_current_limit_rejected(self):
        broken = copy.deepcopy(DEFAULT_BLOCKING_DIODE_POLICY)
        broken["max_reverse_current_ua"] = 0.0
        with self.assertRaises(ValueError):
            validate_blocking_diode_policy(broken)

    def test_conduction_threshold_below_the_limit_rejected(self):
        broken = copy.deepcopy(DEFAULT_BLOCKING_DIODE_POLICY)
        broken["reverse_conduction_current_ua"] = 10.0
        with self.assertRaises(ValueError):
            validate_blocking_diode_policy(broken)

    def test_zero_doubling_interval_rejected(self):
        broken = copy.deepcopy(DEFAULT_BLOCKING_DIODE_POLICY)
        broken["leakage_doubling_interval_k"] = 0.0
        with self.assertRaises(ValueError):
            validate_blocking_diode_policy(broken)

    def test_negative_loss_budget_rejected(self):
        broken = copy.deepcopy(DEFAULT_BLOCKING_DIODE_POLICY)
        broken["max_parasitic_loss_w"] = -1.0
        with self.assertRaises(ValueError):
            validate_blocking_diode_policy(broken)


class CellVoltageTests(unittest.TestCase):
    def test_reference_temperature_returns_the_reference_voltage(self):
        self.assertAlmostEqual(
            cell_open_circuit_voltage_v(2.7, 28.0, 28.0, -0.006), 2.7, places=12
        )

    def test_cold_raises_the_open_circuit_voltage(self):
        cold = cell_open_circuit_voltage_v(2.7, 28.0, -100.0, -0.006)
        self.assertAlmostEqual(cold, 2.7 + 0.006 * 128.0, places=12)

    def test_hot_lowers_the_open_circuit_voltage(self):
        hot = cell_open_circuit_voltage_v(2.7, 28.0, 90.0, -0.006)
        self.assertAlmostEqual(hot, 2.7 - 0.006 * 62.0, places=12)

    def test_non_negative_temperature_coefficient_rejected(self):
        with self.assertRaises(ValueError):
            cell_open_circuit_voltage_v(2.7, 28.0, -100.0, 0.006)

    def test_zero_reference_voltage_rejected(self):
        with self.assertRaises(ValueError):
            cell_open_circuit_voltage_v(0.0, 28.0, -100.0, -0.006)

    def test_temperature_that_collapses_the_voltage_rejected(self):
        with self.assertRaises(ValueError):
            cell_open_circuit_voltage_v(2.7, 28.0, 528.0, -0.006)

    def test_non_numeric_temperature_rejected(self):
        with self.assertRaises(ValueError):
            cell_open_circuit_voltage_v(2.7, 28.0, "cold", -0.006)


class WorstCaseBiasTests(unittest.TestCase):
    def test_series_count_multiplies_the_cell_voltage(self):
        case = copy.deepcopy(FLIGHT_CASE)
        case["beginning_of_life_margin"] = 0.0
        cell = cell_open_circuit_voltage_v(2.7, 28.0, -100.0, -0.006)
        self.assertAlmostEqual(
            worst_case_reverse_bias_v(case), 24 * cell, places=12
        )

    def test_margin_lifts_the_required_bias(self):
        case = copy.deepcopy(FLIGHT_CASE)
        case["beginning_of_life_margin"] = 0.0
        bare = worst_case_reverse_bias_v(case)
        self.assertAlmostEqual(REQUIRED_BIAS_V, bare * 1.02, places=12)

    def test_missing_margin_defaults_to_none_applied(self):
        case = copy.deepcopy(FLIGHT_CASE)
        del case["beginning_of_life_margin"]
        cell = cell_open_circuit_voltage_v(2.7, 28.0, -100.0, -0.006)
        self.assertAlmostEqual(worst_case_reverse_bias_v(case), 24 * cell, places=12)

    def test_zero_cells_in_series_rejected(self):
        case = copy.deepcopy(FLIGHT_CASE)
        case["cells_in_series"] = 0
        with self.assertRaises(ValueError):
            worst_case_reverse_bias_v(case)

    def test_fractional_cell_count_rejected(self):
        case = copy.deepcopy(FLIGHT_CASE)
        case["cells_in_series"] = 24.5
        with self.assertRaises(ValueError):
            worst_case_reverse_bias_v(case)

    def test_negative_margin_rejected(self):
        case = copy.deepcopy(FLIGHT_CASE)
        case["beginning_of_life_margin"] = -0.05
        with self.assertRaises(ValueError):
            worst_case_reverse_bias_v(case)


class BiasAdequacyTests(unittest.TestCase):
    def test_bias_above_the_requirement_is_adequate(self):
        result = reverse_bias_adequacy(120.0, REQUIRED_BIAS_V)
        self.assertTrue(result["adequate"])
        self.assertAlmostEqual(result["shortfall_v"], 0.0, places=12)
        self.assertEqual(result["findings"], [])

    def test_bias_exactly_on_the_requirement_is_adequate(self):
        result = reverse_bias_adequacy(REQUIRED_BIAS_V, REQUIRED_BIAS_V)
        self.assertTrue(result["adequate"])
        self.assertAlmostEqual(result["coverage_ratio"], 1.0, places=9)

    def test_bias_below_the_requirement_is_named_in_the_findings(self):
        result = reverse_bias_adequacy(50.0, REQUIRED_BIAS_V)
        self.assertFalse(result["adequate"])
        self.assertAlmostEqual(result["shortfall_v"], REQUIRED_BIAS_V - 50.0, places=9)
        self.assertTrue(
            any("below the worst-case" in note for note in result["findings"])
        )

    def test_zero_applied_bias_rejected(self):
        with self.assertRaises(ValueError):
            reverse_bias_adequacy(0.0, REQUIRED_BIAS_V)


class LeakageScalingTests(unittest.TestCase):
    def test_same_temperature_leaves_the_current_alone(self):
        self.assertAlmostEqual(
            scale_reverse_current_ua(12.0, 60.0, 60.0, 10.0), 12.0, places=12
        )

    def test_one_doubling_interval_doubles_the_current(self):
        self.assertAlmostEqual(
            scale_reverse_current_ua(12.0, 50.0, 60.0, 10.0), 24.0, places=12
        )

    def test_one_interval_colder_halves_the_current(self):
        self.assertAlmostEqual(
            scale_reverse_current_ua(12.0, 70.0, 60.0, 10.0), 6.0, places=12
        )

    def test_zero_leakage_stays_zero(self):
        self.assertAlmostEqual(
            scale_reverse_current_ua(0.0, 20.0, 60.0, 10.0), 0.0, places=12
        )

    def test_negative_leakage_rejected(self):
        with self.assertRaises(ValueError):
            scale_reverse_current_ua(-1.0, 50.0, 60.0, 10.0)

    def test_zero_doubling_interval_rejected(self):
        with self.assertRaises(ValueError):
            scale_reverse_current_ua(12.0, 50.0, 60.0, 0.0)


class CategoryTests(unittest.TestCase):
    def test_small_leakage_is_within_limit(self):
        self.assertEqual(categorize_reverse_current(12.0), WITHIN_LIMIT)

    def test_leakage_exactly_on_the_limit_is_within_limit(self):
        limit = DEFAULT_BLOCKING_DIODE_POLICY["max_reverse_current_ua"]
        referred = scale_reverse_current_ua(limit / 2.0, 50.0, 60.0, 10.0)
        self.assertAlmostEqual(referred, limit, places=9)
        self.assertEqual(categorize_reverse_current(referred), WITHIN_LIMIT)

    def test_leakage_past_the_limit_is_grouped_above_limit(self):
        self.assertEqual(categorize_reverse_current(200.0), ABOVE_LIMIT)

    def test_gross_leakage_is_reverse_conducting(self):
        self.assertEqual(categorize_reverse_current(1500.0), REVERSE_CONDUCTING)

    def test_every_category_is_reachable(self):
        seen = {
            categorize_reverse_current(value) for value in (1.0, 200.0, 1500.0)
        }
        self.assertEqual(seen, set(REVERSE_CURRENT_CATEGORIES))


class PowerTests(unittest.TestCase):
    def test_loss_is_bias_times_total_current(self):
        self.assertAlmostEqual(
            parasitic_reverse_power_w(100.0, 120.0), 0.012, places=12
        )

    def test_no_leakage_gives_no_loss(self):
        self.assertAlmostEqual(parasitic_reverse_power_w(0.0, 120.0), 0.0, places=12)

    def test_zero_bias_rejected(self):
        with self.assertRaises(ValueError):
            parasitic_reverse_power_w(100.0, 0.0)


class DiodeTests(unittest.TestCase):
    def test_cool_bench_reading_is_referred_upwards(self):
        record = evaluate_blocking_diode(_diode("d1", 12.0, 50.0))
        self.assertAlmostEqual(record["referred_reverse_current_ua"], 24.0, places=12)
        self.assertTrue(record["acceptable"])

    def test_referral_can_turn_a_passing_raw_reading_into_a_reject(self):
        record = evaluate_blocking_diode(_diode("d9", 30.0, 40.0))
        self.assertAlmostEqual(record["referred_reverse_current_ua"], 120.0, places=12)
        self.assertEqual(record["category"], ABOVE_LIMIT)
        self.assertFalse(record["acceptable"])

    def test_reverse_conducting_diode_is_called_out(self):
        record = evaluate_blocking_diode(_diode("d7", 2000.0, 60.0))
        self.assertEqual(record["category"], REVERSE_CONDUCTING)
        self.assertTrue(
            any("no longer blocks" in note for note in record["findings"])
        )

    def test_non_mapping_diode_rejected(self):
        with self.assertRaises(ValueError):
            evaluate_blocking_diode("12 microamps")


class CampaignTests(unittest.TestCase):
    def test_sound_campaign_passes(self):
        result = evaluate_blocking_diode_test(SOUND_CAMPAIGN)
        self.assertEqual(result["verdict"], BLOCKING_DIODE_TEST_PASSED)
        self.assertTrue(result["compliant"])
        self.assertEqual(result["rejected_diode_ids"], [])
        self.assertTrue(result["bias_adequate"])

    def test_one_leaky_diode_fails_and_is_named(self):
        campaign = _campaign(
            [_diode("d1", 12.0), _diode("d2", 11.0), _diode("d3", 400.0, 60.0)]
        )
        result = evaluate_blocking_diode_test(campaign)
        self.assertEqual(result["verdict"], BLOCKING_DIODE_TEST_FAILED)
        self.assertEqual(result["rejected_diode_ids"], ["d3"])

    def test_under_stressed_bench_is_not_evaluated(self):
        campaign = _campaign(
            [_diode("d1", 12.0), _diode("d2", 11.0)], applied_v=50.0
        )
        result = evaluate_blocking_diode_test(campaign)
        self.assertEqual(result["verdict"], BLOCKING_DIODE_TEST_NOT_EVALUATED)
        self.assertIsNone(result["compliant"])
        self.assertTrue(
            any("under-stressed" in note for note in result["findings"])
        )

    def test_bench_exactly_at_the_worst_case_is_evaluated(self):
        campaign = _campaign(
            [_diode("d1", 12.0), _diode("d2", 11.0)], applied_v=REQUIRED_BIAS_V
        )
        result = evaluate_blocking_diode_test(campaign)
        self.assertTrue(result["bias_adequate"])
        self.assertEqual(result["verdict"], BLOCKING_DIODE_TEST_PASSED)

    def test_loss_budget_can_fail_an_otherwise_clean_population(self):
        policy = copy.deepcopy(DEFAULT_BLOCKING_DIODE_POLICY)
        policy["max_parasitic_loss_w"] = 1e-6
        result = evaluate_blocking_diode_test(SOUND_CAMPAIGN, policy)
        self.assertFalse(result["compliant"])
        self.assertTrue(
            any("parasitic reverse loss" in note for note in result["findings"])
        )
        self.assertEqual(result["rejected_diode_ids"], [])

    def test_total_referred_current_is_the_sum_of_the_population(self):
        result = evaluate_blocking_diode_test(SOUND_CAMPAIGN)
        expected = sum(
            record["referred_reverse_current_ua"] for record in result["diodes"]
        )
        self.assertAlmostEqual(
            result["total_referred_reverse_current_ua"], expected, places=12
        )

    def test_campaign_without_diodes_rejected(self):
        campaign = copy.deepcopy(SOUND_CAMPAIGN)
        campaign["diodes"] = []
        with self.assertRaises(ValueError):
            evaluate_blocking_diode_test(campaign)

    def test_campaign_without_a_flight_case_rejected(self):
        campaign = copy.deepcopy(SOUND_CAMPAIGN)
        del campaign["flight_case"]
        with self.assertRaises(ValueError):
            evaluate_blocking_diode_test(campaign)

    def test_non_mapping_campaign_rejected(self):
        with self.assertRaises(ValueError):
            evaluate_blocking_diode_test("four diodes, all quiet")


if __name__ == "__main__":
    unittest.main()
