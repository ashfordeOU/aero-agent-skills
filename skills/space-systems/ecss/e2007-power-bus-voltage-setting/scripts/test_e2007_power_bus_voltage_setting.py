"""Contract tests for the clause 5.2.12 supply-extreme selection logic."""

import copy
import unittest

from e2007_power_bus_voltage_setting_logic import (
    LEVEL_TOLERANCE_DB,
    assess_bus_voltage_setting,
    common_grid,
    emission_envelope,
    interpolate_limit,
    run_statistics,
    select_governing_setting,
    validate_extremes,
    validate_run,
    validate_sweep,
    validate_voltage,
)

GRID = (150.0e3, 1.0e6, 10.0e6, 50.0e6)

LOW_RUN = {
    "setting": "lower-extreme",
    "voltage_v": 22.0,
    "sweep": [(150.0e3, 50.0), (1.0e6, 58.0), (10.0e6, 44.0), (50.0e6, 40.0)],
}
HIGH_RUN = {
    "setting": "upper-extreme",
    "voltage_v": 34.0,
    "sweep": [(150.0e3, 46.0), (1.0e6, 55.0), (10.0e6, 41.0), (50.0e6, 37.0)],
}

# A limit line the clean pair of runs sits comfortably below.
EASY_LIMIT = [(100.0e3, 70.0), (50.0e6, 64.0)]
# A limit line the lower-extreme run breaks around 1 MHz.
TIGHT_LIMIT = [(100.0e3, 55.0), (50.0e6, 50.0)]


class VoltageTests(unittest.TestCase):
    def test_voltage_is_returned_as_a_float(self):
        self.assertAlmostEqual(validate_voltage(28), 28.0, places=9)

    def test_zero_voltage_rejected(self):
        with self.assertRaises(ValueError):
            validate_voltage(0.0)

    def test_negative_voltage_rejected(self):
        with self.assertRaises(ValueError):
            validate_voltage(-22.0)

    def test_boolean_voltage_rejected(self):
        with self.assertRaises(ValueError):
            validate_voltage(True)

    def test_non_finite_voltage_rejected(self):
        with self.assertRaises(ValueError):
            validate_voltage(float("inf"))

    def test_extremes_are_returned_in_order(self):
        self.assertEqual(validate_extremes(22, 34), (22.0, 34.0))

    def test_equal_extremes_rejected(self):
        with self.assertRaises(ValueError):
            validate_extremes(28.0, 28.0)

    def test_inverted_extremes_rejected(self):
        with self.assertRaises(ValueError):
            validate_extremes(34.0, 22.0)


class SweepTests(unittest.TestCase):
    def test_sweep_is_normalized_to_float_pairs(self):
        sweep = validate_sweep([(1, 10), (2, 12)])
        self.assertAlmostEqual(sweep[0][0], 1.0, places=9)
        self.assertAlmostEqual(sweep[1][1], 12.0, places=9)

    def test_single_point_sweep_rejected(self):
        with self.assertRaises(ValueError):
            validate_sweep([(1.0e6, 50.0)])

    def test_non_advancing_sweep_rejected(self):
        with self.assertRaises(ValueError):
            validate_sweep([(1.0e6, 50.0), (1.0e6, 52.0)])

    def test_descending_sweep_rejected(self):
        with self.assertRaises(ValueError):
            validate_sweep([(2.0e6, 50.0), (1.0e6, 52.0)])

    def test_non_positive_frequency_rejected(self):
        with self.assertRaises(ValueError):
            validate_sweep([(0.0, 50.0), (1.0e6, 52.0)])

    def test_malformed_point_rejected(self):
        with self.assertRaises(ValueError):
            validate_sweep([(1.0e6, 50.0), (2.0e6,)])

    def test_non_finite_level_rejected(self):
        with self.assertRaises(ValueError):
            validate_sweep([(1.0e6, float("nan")), (2.0e6, 52.0)])

    def test_mapping_instead_of_sequence_rejected(self):
        with self.assertRaises(ValueError):
            validate_sweep({"1e6": 50.0})


class RunRecordTests(unittest.TestCase):
    def test_run_is_normalized(self):
        record = validate_run(LOW_RUN)
        self.assertEqual(record["setting"], "lower-extreme")
        self.assertAlmostEqual(record["voltage_v"], 22.0, places=9)

    def test_unknown_run_key_rejected(self):
        run = dict(LOW_RUN, operator="lab")
        with self.assertRaises(ValueError):
            validate_run(run)

    def test_missing_run_key_rejected(self):
        run = dict(LOW_RUN)
        del run["sweep"]
        with self.assertRaises(ValueError):
            validate_run(run)

    def test_blank_setting_label_rejected(self):
        with self.assertRaises(ValueError):
            validate_run(dict(LOW_RUN, setting="  "))


class GridTests(unittest.TestCase):
    def test_common_grid_is_returned(self):
        self.assertEqual(common_grid([LOW_RUN, HIGH_RUN]), GRID)

    def test_different_point_count_rejected(self):
        short = copy.deepcopy(HIGH_RUN)
        short["sweep"] = short["sweep"][:3]
        with self.assertRaises(ValueError):
            common_grid([LOW_RUN, short])

    def test_shifted_grid_rejected(self):
        shifted = copy.deepcopy(HIGH_RUN)
        shifted["sweep"][2] = (11.0e6, 41.0)
        with self.assertRaises(ValueError):
            common_grid([LOW_RUN, shifted])

    def test_duplicate_setting_label_rejected(self):
        with self.assertRaises(ValueError):
            common_grid([LOW_RUN, dict(HIGH_RUN, setting="lower-extreme")])

    def test_empty_run_set_rejected(self):
        with self.assertRaises(ValueError):
            common_grid([])


class LimitLineTests(unittest.TestCase):
    def test_tabulated_endpoint_is_returned_exactly(self):
        self.assertAlmostEqual(interpolate_limit(EASY_LIMIT, 100.0e3), 70.0, places=9)

    def test_upper_endpoint_is_returned_exactly(self):
        self.assertAlmostEqual(interpolate_limit(EASY_LIMIT, 50.0e6), 64.0, places=9)

    def test_geometric_midpoint_is_the_arithmetic_mean(self):
        value = interpolate_limit([(1.0e5, 80.0), (1.0e7, 40.0)], 1.0e6)
        self.assertAlmostEqual(value, 60.0, places=9)

    def test_below_the_tabulated_range_refused(self):
        with self.assertRaises(ValueError):
            interpolate_limit(EASY_LIMIT, 10.0e3)

    def test_above_the_tabulated_range_refused(self):
        with self.assertRaises(ValueError):
            interpolate_limit(EASY_LIMIT, 100.0e6)

    def test_non_positive_frequency_refused(self):
        with self.assertRaises(ValueError):
            interpolate_limit(EASY_LIMIT, -1.0)


class EnvelopeTests(unittest.TestCase):
    def test_envelope_has_one_point_per_grid_frequency(self):
        self.assertEqual(len(emission_envelope([LOW_RUN, HIGH_RUN])), len(GRID))

    def test_dominant_run_holds_every_envelope_point(self):
        envelope = emission_envelope([LOW_RUN, HIGH_RUN])
        self.assertTrue(all(point["setting"] == "lower-extreme" for point in envelope))

    def test_envelope_takes_the_worst_level_at_each_frequency(self):
        crossing = copy.deepcopy(HIGH_RUN)
        crossing["sweep"][1] = (1.0e6, 62.0)
        envelope = emission_envelope([LOW_RUN, crossing])
        self.assertAlmostEqual(envelope[1]["level_dbuv"], 62.0, places=9)
        self.assertEqual(envelope[1]["setting"], "upper-extreme")
        self.assertEqual(envelope[0]["setting"], "lower-extreme")

    def test_tie_goes_to_the_lower_voltage(self):
        twin = copy.deepcopy(HIGH_RUN)
        twin["sweep"] = list(LOW_RUN["sweep"])
        envelope = emission_envelope([twin, LOW_RUN])
        self.assertTrue(all(point["setting"] == "lower-extreme" for point in envelope))

    def test_envelope_carries_the_voltage_of_its_setting(self):
        envelope = emission_envelope([LOW_RUN, HIGH_RUN])
        self.assertAlmostEqual(envelope[0]["voltage_v"], 22.0, places=9)


class StatisticsTests(unittest.TestCase):
    def test_maximum_level_is_reported_per_run(self):
        statistics = run_statistics([LOW_RUN, HIGH_RUN])
        self.assertAlmostEqual(statistics[0]["max_level_dbuv"], 58.0, places=9)
        self.assertAlmostEqual(statistics[1]["max_level_dbuv"], 55.0, places=9)

    def test_envelope_point_count_is_reported(self):
        statistics = run_statistics([LOW_RUN, HIGH_RUN])
        self.assertEqual(statistics[0]["envelope_points"], len(GRID))
        self.assertEqual(statistics[1]["envelope_points"], 0)

    def test_exceedance_is_negative_below_a_generous_limit(self):
        statistics = run_statistics([LOW_RUN, HIGH_RUN], EASY_LIMIT)
        self.assertLess(statistics[0]["max_exceedance_db"], 0.0)

    def test_exceedance_is_positive_against_a_tight_limit(self):
        statistics = run_statistics([LOW_RUN, HIGH_RUN], TIGHT_LIMIT)
        self.assertGreater(statistics[0]["max_exceedance_db"], 0.0)

    def test_exceedance_is_absent_when_no_limit_is_declared(self):
        statistics = run_statistics([LOW_RUN, HIGH_RUN])
        self.assertIsNone(statistics[0]["max_exceedance_db"])


class GoverningSettingTests(unittest.TestCase):
    # Run A is the louder run in absolute terms; run B sits closer to a limit
    # that falls steeply with frequency, so the two rankings disagree.
    RUN_A = {"setting": "lower-extreme", "voltage_v": 22.0,
             "sweep": [(1.0e5, 70.0), (1.0e7, 30.0)]}
    RUN_B = {"setting": "upper-extreme", "voltage_v": 34.0,
             "sweep": [(1.0e5, 60.0), (1.0e7, 38.0)]}
    STEEP_LIMIT = [(1.0e5, 80.0), (1.0e7, 40.0)]

    def test_dominant_run_governs(self):
        governing = select_governing_setting([LOW_RUN, HIGH_RUN])
        self.assertEqual(governing["setting"], "lower-extreme")

    def test_absolute_level_ranks_the_louder_run_first(self):
        governing = select_governing_setting([self.RUN_A, self.RUN_B])
        self.assertEqual(governing["setting"], "lower-extreme")

    def test_a_limit_line_can_move_the_governing_setting(self):
        governing = select_governing_setting([self.RUN_A, self.RUN_B], self.STEEP_LIMIT)
        self.assertEqual(governing["setting"], "upper-extreme")
        self.assertAlmostEqual(governing["max_exceedance_db"], -2.0, places=9)

    def test_identical_runs_break_the_tie_on_the_lower_voltage(self):
        twin = copy.deepcopy(HIGH_RUN)
        twin["sweep"] = list(LOW_RUN["sweep"])
        governing = select_governing_setting([twin, LOW_RUN])
        self.assertEqual(governing["setting"], "lower-extreme")

    def test_tolerance_is_a_representation_allowance_not_a_margin(self):
        self.assertLess(LEVEL_TOLERANCE_DB, 1e-6)


class AssessmentTests(unittest.TestCase):
    def _spec(self, **overrides):
        spec = {
            "runs": [copy.deepcopy(LOW_RUN), copy.deepcopy(HIGH_RUN)],
            "declared_extremes": (22.0, 34.0),
            "limit_line": EASY_LIMIT,
            "reported_setting": "lower-extreme",
        }
        spec.update(overrides)
        return spec

    def test_clean_campaign_is_compliant(self):
        result = assess_bus_voltage_setting(self._spec())
        self.assertTrue(result["compliant"])
        self.assertEqual(result["findings"], [])
        self.assertEqual(result["governing"]["setting"], "lower-extreme")

    def test_unexercised_extreme_is_a_finding(self):
        spec = self._spec(runs=[copy.deepcopy(LOW_RUN)])
        result = assess_bus_voltage_setting(spec)
        self.assertFalse(result["compliant"])
        self.assertIn("never exercised", result["findings"][0])

    def test_run_at_neither_extreme_is_a_finding(self):
        nominal = copy.deepcopy(HIGH_RUN)
        nominal["setting"] = "nominal"
        nominal["voltage_v"] = 28.0
        spec = self._spec(runs=[copy.deepcopy(LOW_RUN), nominal])
        result = assess_bus_voltage_setting(spec)
        self.assertTrue(any("neither declared extreme" in f for f in result["findings"]))

    def test_wrong_reported_setting_is_a_finding(self):
        result = assess_bus_voltage_setting(self._spec(reported_setting="upper-extreme"))
        self.assertTrue(any("governing setting" in f for f in result["findings"]))

    def test_crossing_runs_require_the_envelope(self):
        crossing = copy.deepcopy(HIGH_RUN)
        crossing["sweep"][1] = (1.0e6, 62.0)
        result = assess_bus_voltage_setting(
            self._spec(runs=[copy.deepcopy(LOW_RUN), crossing], reported_setting=None)
        )
        self.assertTrue(any("is not worst at" in f for f in result["findings"]))

    def test_envelope_above_the_limit_is_reported(self):
        result = assess_bus_voltage_setting(self._spec(limit_line=TIGHT_LIMIT))
        self.assertGreater(result["over_limit_count"], 0)
        self.assertTrue(any("above the limit" in f for f in result["findings"]))

    def test_no_limit_line_leaves_the_exceedance_count_at_zero(self):
        spec = self._spec()
        del spec["limit_line"]
        result = assess_bus_voltage_setting(spec)
        self.assertEqual(result["over_limit_count"], 0)
        self.assertTrue(result["compliant"])

    def test_non_mapping_spec_rejected(self):
        with self.assertRaises(ValueError):
            assess_bus_voltage_setting(["runs"])

    def test_missing_declared_extremes_rejected(self):
        spec = self._spec()
        del spec["declared_extremes"]
        with self.assertRaises(ValueError):
            assess_bus_voltage_setting(spec)

    def test_malformed_declared_extremes_rejected(self):
        with self.assertRaises(ValueError):
            assess_bus_voltage_setting(self._spec(declared_extremes=(22.0,)))

    def test_blank_reported_setting_rejected(self):
        with self.assertRaises(ValueError):
            assess_bus_voltage_setting(self._spec(reported_setting="   "))

    def test_statistics_cover_every_run(self):
        result = assess_bus_voltage_setting(self._spec())
        self.assertEqual(len(result["statistics"]), 2)
        self.assertEqual(len(result["envelope"]), len(GRID))


if __name__ == "__main__":
    unittest.main()
