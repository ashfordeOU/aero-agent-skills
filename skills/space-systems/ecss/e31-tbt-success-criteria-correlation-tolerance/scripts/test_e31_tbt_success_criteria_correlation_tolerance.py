"""Contract tests for the clause 4.5.3.2 correlation success-criteria logic."""

import unittest

from e31_tbt_success_criteria_correlation_tolerance_logic import (
    CRITERION_TOLERANCE,
    GATE_NAMES,
    grade_correlation,
    mark_against_band,
    partition_sensors,
    sensor_deviation_k,
    validate_sensor_record,
    weighted_bias_k,
    weighted_exceedance_fraction,
    weighted_spread_k,
)


def sensor(name, predicted, measured, **extra):
    record = {"name": name, "predicted_k": predicted, "measured_k": measured}
    record.update(extra)
    return record


CLEAN_SET = [
    sensor("trp-payload", 301.0, 300.0, weight=5.0),
    sensor("trp-structure-a", 289.0, 290.0),
    sensor("trp-structure-b", 275.5, 275.0),
]


class RecordValidationTests(unittest.TestCase):
    def test_record_round_trips_with_defaults(self):
        record = validate_sensor_record(sensor("trp-a", 300.0, 299.0))
        self.assertAlmostEqual(record["weight"], 1.0, places=12)
        self.assertFalse(record["excluded"])

    def test_declared_weight_is_kept(self):
        record = validate_sensor_record(sensor("trp-a", 300.0, 299.0, weight=4.0))
        self.assertAlmostEqual(record["weight"], 4.0, places=12)

    def test_blank_name_rejected(self):
        with self.assertRaises(ValueError):
            validate_sensor_record(sensor("  ", 300.0, 299.0))

    def test_non_absolute_temperature_rejected(self):
        with self.assertRaises(ValueError):
            validate_sensor_record(sensor("trp-a", 300.0, 0.0))

    def test_zero_weight_rejected(self):
        with self.assertRaises(ValueError):
            validate_sensor_record(sensor("trp-a", 300.0, 299.0, weight=0.0))

    def test_non_boolean_exclusion_rejected(self):
        with self.assertRaises(ValueError):
            validate_sensor_record(sensor("trp-a", 300.0, 299.0, excluded="yes"))

    def test_missing_key_rejected(self):
        with self.assertRaises(ValueError):
            validate_sensor_record({"name": "trp-a", "predicted_k": 300.0})

    def test_deviation_is_predicted_minus_measured(self):
        self.assertAlmostEqual(
            sensor_deviation_k(sensor("trp-a", 305.0, 300.0)), 5.0, places=12
        )

    def test_negative_deviation_when_the_model_runs_cold(self):
        self.assertAlmostEqual(
            sensor_deviation_k(sensor("trp-a", 295.0, 300.0)), -5.0, places=12
        )


class PartitionTests(unittest.TestCase):
    def test_clean_set_grades_everything(self):
        partition = partition_sensors(CLEAN_SET)
        self.assertEqual(len(partition["graded"]), 3)
        self.assertEqual(partition["excluded"], [])
        self.assertEqual(partition["findings"], [])

    def test_justified_exclusion_is_separated_without_a_finding(self):
        records = list(CLEAN_SET) + [
            sensor("trp-detached", 300.0, 260.0, excluded=True,
                   exclusion_reason="sensor debonded during pump-down")
        ]
        partition = partition_sensors(records)
        self.assertEqual(len(partition["excluded"]), 1)
        self.assertEqual(partition["findings"], [])

    def test_unjustified_exclusion_is_a_finding(self):
        records = list(CLEAN_SET) + [
            sensor("trp-detached", 300.0, 260.0, excluded=True)
        ]
        partition = partition_sensors(records)
        self.assertEqual(len(partition["findings"]), 1)
        self.assertIn("no recorded reason", partition["findings"][0])

    def test_blank_reason_is_not_a_reason(self):
        records = list(CLEAN_SET) + [
            sensor("trp-detached", 300.0, 260.0, excluded=True, exclusion_reason="  ")
        ]
        self.assertEqual(len(partition_sensors(records)["findings"]), 1)

    def test_excluding_everything_is_refused(self):
        with self.assertRaises(ValueError):
            partition_sensors([
                sensor("trp-a", 300.0, 260.0, excluded=True, exclusion_reason="x")
            ])

    def test_duplicate_sensor_name_rejected(self):
        with self.assertRaises(ValueError):
            partition_sensors([
                sensor("trp-a", 300.0, 299.0), sensor("trp-a", 301.0, 300.0)
            ])

    def test_empty_set_rejected(self):
        with self.assertRaises(ValueError):
            partition_sensors([])


class BandTests(unittest.TestCase):
    def test_sensor_inside_the_band_is_marked_within(self):
        marked = mark_against_band([sensor("trp-a", 301.0, 300.0)], 2.0)
        self.assertTrue(marked[0]["within_band"])

    def test_sensor_outside_the_band_is_marked_out(self):
        marked = mark_against_band([sensor("trp-a", 305.0, 300.0)], 2.0)
        self.assertFalse(marked[0]["within_band"])

    def test_sensor_exactly_on_the_band_edge_is_within(self):
        marked = mark_against_band([sensor("trp-a", 302.0, 300.0)], 2.0)
        self.assertTrue(marked[0]["within_band"])

    def test_band_is_symmetric(self):
        marked = mark_against_band([sensor("trp-a", 298.0, 300.0)], 2.0)
        self.assertTrue(marked[0]["within_band"])

    def test_zero_band_rejected(self):
        with self.assertRaises(ValueError):
            mark_against_band([sensor("trp-a", 300.0, 300.0)], 0.0)

    def test_empty_graded_set_rejected(self):
        with self.assertRaises(ValueError):
            mark_against_band([], 2.0)


class StatisticsTests(unittest.TestCase):
    def test_exceedance_is_zero_for_a_clean_set(self):
        marked = mark_against_band(CLEAN_SET, 2.0)
        self.assertAlmostEqual(weighted_exceedance_fraction(marked), 0.0, places=12)

    def test_exceedance_is_spent_by_weight_not_headcount(self):
        records = [
            sensor("trp-payload", 310.0, 300.0, weight=5.0),
            sensor("s1", 290.0, 290.0),
            sensor("s2", 290.0, 290.0),
        ]
        marked = mark_against_band(records, 2.0)
        self.assertAlmostEqual(
            weighted_exceedance_fraction(marked), 5.0 / 7.0, places=12
        )

    def test_headcount_would_have_read_one_third(self):
        records = [
            sensor("trp-payload", 310.0, 300.0, weight=5.0),
            sensor("s1", 290.0, 290.0),
            sensor("s2", 290.0, 290.0),
        ]
        marked = mark_against_band(records, 2.0)
        self.assertGreater(weighted_exceedance_fraction(marked), 1.0 / 3.0)

    def test_bias_of_a_uniformly_high_model(self):
        records = [sensor("a", 305.0, 300.0), sensor("b", 295.0, 290.0)]
        marked = mark_against_band(records, 10.0)
        self.assertAlmostEqual(weighted_bias_k(marked), 5.0, places=12)
        self.assertAlmostEqual(weighted_spread_k(marked), 0.0, places=12)

    def test_scattered_model_has_no_bias_and_a_large_spread(self):
        records = [sensor("a", 315.0, 300.0), sensor("b", 275.0, 290.0)]
        marked = mark_against_band(records, 20.0)
        self.assertAlmostEqual(weighted_bias_k(marked), 0.0, places=12)
        self.assertAlmostEqual(weighted_spread_k(marked), 15.0, places=12)

    def test_weighting_pulls_the_bias_towards_the_heavy_sensor(self):
        records = [
            sensor("heavy", 310.0, 300.0, weight=9.0),
            sensor("light", 300.0, 300.0),
        ]
        marked = mark_against_band(records, 20.0)
        self.assertAlmostEqual(weighted_bias_k(marked), 9.0, places=12)

    def test_exceedance_rejects_a_malformed_record(self):
        with self.assertRaises(ValueError):
            weighted_exceedance_fraction([{"weight": 1.0}])

    def test_bias_rejects_a_malformed_record(self):
        with self.assertRaises(ValueError):
            weighted_bias_k([{"weight": 1.0}])

    def test_empty_statistics_rejected(self):
        with self.assertRaises(ValueError):
            weighted_bias_k([])


class VerdictTests(unittest.TestCase):
    CRITERIA = {
        "tolerance_k": 2.0,
        "exceedance_budget": 0.1,
        "bias_tolerance_k": 1.0,
        "spread_tolerance_k": 2.0,
        "max_excluded_fraction": 0.2,
    }

    def _criteria(self, **overrides):
        criteria = dict(self.CRITERIA)
        criteria.update(overrides)
        return criteria

    def test_correlated_campaign_passes(self):
        result = grade_correlation(CLEAN_SET, self._criteria())
        self.assertEqual(result["verdict"], "pass")
        self.assertEqual(result["failed_gates"], [])

    def test_band_breach_beyond_the_budget_fails(self):
        records = [
            sensor("trp-payload", 310.0, 300.0, weight=5.0),
            sensor("s1", 290.0, 290.0),
        ]
        result = grade_correlation(records, self._criteria(bias_tolerance_k=None))
        self.assertEqual(result["verdict"], "fail")
        self.assertIn("per_sensor_band", result["failed_gates"])

    def test_budget_exactly_spent_still_passes(self):
        records = [
            sensor("out", 305.0, 300.0),
            sensor("in-a", 290.0, 290.0),
            sensor("in-b", 280.0, 280.0),
            sensor("in-c", 270.0, 270.0),
        ]
        result = grade_correlation(records, {
            "tolerance_k": 2.0, "exceedance_budget": 0.25
        })
        self.assertAlmostEqual(result["exceedance_fraction"], 0.25, places=12)
        self.assertEqual(result["verdict"], "pass")

    def test_uniform_offset_fails_on_bias_alone(self):
        records = [sensor("a", 303.0, 300.0), sensor("b", 293.0, 290.0)]
        result = grade_correlation(records, {
            "tolerance_k": 5.0, "bias_tolerance_k": 1.0
        })
        self.assertEqual(result["failed_gates"], ["bias"])

    def test_scatter_fails_on_spread_while_the_bias_passes(self):
        records = [sensor("a", 304.0, 300.0), sensor("b", 286.0, 290.0)]
        result = grade_correlation(records, {
            "tolerance_k": 5.0, "bias_tolerance_k": 1.0, "spread_tolerance_k": 2.0
        })
        self.assertEqual(result["failed_gates"], ["spread"])
        self.assertAlmostEqual(result["bias_k"], 0.0, places=12)

    def test_bias_exactly_on_the_allowance_passes(self):
        records = [sensor("a", 301.0, 300.0), sensor("b", 291.0, 290.0)]
        result = grade_correlation(records, {
            "tolerance_k": 5.0, "bias_tolerance_k": 1.0
        })
        self.assertEqual(result["verdict"], "pass")

    def test_unjustified_exclusion_fails_the_exclusion_gate(self):
        records = list(CLEAN_SET) + [sensor("dropped", 320.0, 300.0, excluded=True)]
        result = grade_correlation(records, self._criteria())
        self.assertIn("exclusion_record", result["failed_gates"])

    def test_excessive_exclusion_weight_fails_its_own_gate(self):
        records = [
            sensor("kept", 300.0, 300.0),
            sensor("dropped", 320.0, 300.0, weight=4.0, excluded=True,
                   exclusion_reason="sensor debonded"),
        ]
        result = grade_correlation(records, self._criteria())
        self.assertIn("excluded_weight", result["failed_gates"])
        self.assertAlmostEqual(result["excluded_weight_fraction"], 0.8, places=12)

    def test_justified_exclusion_inside_the_cap_passes(self):
        records = list(CLEAN_SET) + [
            sensor("dropped", 320.0, 300.0, excluded=True,
                   exclusion_reason="sensor debonded")
        ]
        result = grade_correlation(records, self._criteria(max_excluded_fraction=0.5))
        self.assertEqual(result["verdict"], "pass")
        self.assertEqual(result["excluded"], ["dropped"])

    def test_worst_sensor_is_named(self):
        records = [
            sensor("mild", 301.0, 300.0),
            sensor("bad", 312.0, 300.0),
        ]
        result = grade_correlation(records, {"tolerance_k": 20.0})
        self.assertEqual(result["worst_sensor"], "bad")
        self.assertAlmostEqual(result["worst_deviation_k"], 12.0, places=12)

    def test_several_gates_can_fail_together(self):
        records = [
            sensor("a", 320.0, 300.0),
            sensor("b", 260.0, 290.0),
            sensor("dropped", 300.0, 300.0, excluded=True),
        ]
        result = grade_correlation(records, self._criteria())
        self.assertGreaterEqual(len(result["failed_gates"]), 3)
        self.assertEqual(result["verdict"], "fail")

    def test_missing_tolerance_rejected(self):
        with self.assertRaises(ValueError):
            grade_correlation(CLEAN_SET, {"exceedance_budget": 0.1})

    def test_budget_above_one_rejected(self):
        with self.assertRaises(ValueError):
            grade_correlation(CLEAN_SET, self._criteria(exceedance_budget=1.5))

    def test_non_mapping_criteria_rejected(self):
        with self.assertRaises(ValueError):
            grade_correlation(CLEAN_SET, ["tolerance_k"])

    def test_gate_vocabulary_is_stable(self):
        self.assertEqual(len(GATE_NAMES), 5)
        self.assertIn("per_sensor_band", GATE_NAMES)

    def test_criterion_tolerance_is_tight(self):
        self.assertLess(CRITERION_TOLERANCE, 1.0e-6)


if __name__ == "__main__":
    unittest.main()
