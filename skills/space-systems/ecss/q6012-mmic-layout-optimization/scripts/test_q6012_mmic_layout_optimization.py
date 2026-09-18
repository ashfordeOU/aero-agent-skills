"""Contract tests for the clause 7.2.10 MMIC arrangement trade.

Every workflow step - candidate validation, the three metrics, the constraint
gate that can stop a candidate, the normalisation and the weighted review - has
its own case, so a regression in one step cannot hide behind another. Expected
metric values are worked out by hand from the arrangement and written as
literals here, so the test does not re-run the code it is judging. Offline,
stdlib unittest only.
"""

import math
import unittest

from q6012_mmic_layout_optimization_logic import (
    CONSTRAINT_TOLERANCE,
    combining_length_um,
    die_area_mm2,
    evaluate_candidate,
    feasibility,
    interconnect_loss_db,
    normalise_metric,
    optimise_layout,
    peak_channel_temperature_c,
    thermal_spreading_resistance,
    validate_candidate,
    validate_constraints,
    validate_model,
    validate_weights,
    weighted_score,
)

MODEL = {
    "baseplate_temperature_c": 60.0,
    "cell_thermal_resistance_k_per_w": 25.0,
    "reference_pitch_um": 50.0,
    "coupling_coefficient": 0.2,
    "loss_db_per_mm": 0.6,
}

# Four cells on a 20 um pitch: smallest die, shortest combining run, hottest
# centre cell. Hand-worked: mutual = 0.2*25*50 * (1/20 + 1/20 + 1/40) = 31.25,
# so Rth_eff = 56.25 K/W and T_peak = 60 + (4/4)*56.25 = 116.25 C.
TIGHT = {
    "name": "tight",
    "cells": 4,
    "cell_pitch_um": 20.0,
    "die_width_um": 800.0,
    "die_height_um": 600.0,
    "dissipated_power_w": 4.0,
    "feed_length_um": 100.0,
}

# The same four cells on a 100 um pitch: cooler, but a wider die and a longer
# combining run. Hand-worked: mutual = 250 * (1/100 + 1/100 + 1/200) = 6.25,
# Rth_eff = 31.25 K/W, T_peak = 91.25 C.
SPREAD = {
    "name": "spread",
    "cells": 4,
    "cell_pitch_um": 100.0,
    "die_width_um": 1200.0,
    "die_height_um": 600.0,
    "dissipated_power_w": 4.0,
    "feed_length_um": 100.0,
}

TIGHT_AREA = 0.48
TIGHT_TEMP = 116.25
TIGHT_LOSS = 0.096
SPREAD_AREA = 0.72
SPREAD_TEMP = 91.25
SPREAD_LOSS = 0.24


def candidate(base, **overrides):
    out = dict(base)
    out.update(overrides)
    return out


class ValidateCandidateTests(unittest.TestCase):
    def test_normalises_and_fills_defaults(self):
        record = validate_candidate(candidate(TIGHT, feed_length_um=0))
        self.assertEqual(record["combining_factor"], 1.0)
        self.assertEqual(record["feed_length_um"], 0.0)

    def test_zero_cells_rejected(self):
        with self.assertRaises(ValueError):
            validate_candidate(candidate(TIGHT, cells=0))

    def test_fractional_cell_count_rejected(self):
        with self.assertRaises(ValueError):
            validate_candidate(candidate(TIGHT, cells=4.5))

    def test_zero_pitch_rejected(self):
        with self.assertRaises(ValueError):
            validate_candidate(candidate(TIGHT, cell_pitch_um=0.0))

    def test_negative_power_rejected(self):
        with self.assertRaises(ValueError):
            validate_candidate(candidate(TIGHT, dissipated_power_w=-1.0))

    def test_cells_walking_off_the_die_rejected(self):
        with self.assertRaises(ValueError):
            validate_candidate(candidate(TIGHT, cell_pitch_um=400.0))

    def test_cells_exactly_filling_the_die_accepted(self):
        record = validate_candidate(
            candidate(TIGHT, cells=5, cell_pitch_um=200.0, die_width_um=800.0)
        )
        self.assertEqual(record["cells"], 5)

    def test_blank_name_rejected(self):
        with self.assertRaises(ValueError):
            validate_candidate(candidate(TIGHT, name=""))

    def test_missing_key_rejected(self):
        broken = dict(TIGHT)
        del broken["die_height_um"]
        with self.assertRaises(ValueError):
            validate_candidate(broken)

    def test_non_mapping_rejected(self):
        with self.assertRaises(ValueError):
            validate_candidate(["tight"])


class ValidateModelAndInputsTests(unittest.TestCase):
    def test_model_normalises(self):
        tech = validate_model(MODEL)
        self.assertAlmostEqual(tech["coupling_coefficient"], 0.2, places=9)

    def test_negative_baseplate_temperature_allowed(self):
        tech = validate_model(dict(MODEL, baseplate_temperature_c=-40.0))
        self.assertAlmostEqual(tech["baseplate_temperature_c"], -40.0, places=9)

    def test_coupling_above_one_rejected(self):
        with self.assertRaises(ValueError):
            validate_model(dict(MODEL, coupling_coefficient=1.4))

    def test_missing_model_key_rejected(self):
        broken = dict(MODEL)
        del broken["reference_pitch_um"]
        with self.assertRaises(ValueError):
            validate_model(broken)

    def test_constraints_default_to_empty(self):
        self.assertEqual(validate_constraints(None), {})

    def test_negative_area_budget_rejected(self):
        with self.assertRaises(ValueError):
            validate_constraints({"max_die_area_mm2": -1.0})

    def test_default_weights_are_equal_thirds(self):
        weights = validate_weights(None)
        self.assertAlmostEqual(weights["die_area_mm2"], 1.0 / 3.0, places=9)

    def test_weights_that_do_not_sum_to_one_rejected(self):
        with self.assertRaises(ValueError):
            validate_weights({"die_area_mm2": 0.5,
                              "peak_channel_temperature_c": 0.5,
                              "insertion_loss_db": 0.5})

    def test_unknown_weight_metric_rejected(self):
        with self.assertRaises(ValueError):
            validate_weights({"die_area_mm2": 0.25,
                              "peak_channel_temperature_c": 0.25,
                              "insertion_loss_db": 0.25,
                              "yield": 0.25})

    def test_zero_weight_rejected(self):
        with self.assertRaises(ValueError):
            validate_weights({"die_area_mm2": 0.0,
                              "peak_channel_temperature_c": 0.5,
                              "insertion_loss_db": 0.5})


class MetricTests(unittest.TestCase):
    def test_die_area_converts_microns_to_square_millimetres(self):
        self.assertAlmostEqual(die_area_mm2(800.0, 600.0), 0.48, places=9)

    def test_combining_length_counts_gaps_not_cells(self):
        self.assertAlmostEqual(
            combining_length_um(4, 20.0, 1.0, 100.0), 160.0, places=9
        )

    def test_a_single_cell_has_only_the_feed(self):
        self.assertAlmostEqual(
            combining_length_um(1, 20.0, 1.0, 100.0), 100.0, places=9
        )

    def test_combining_factor_lengthens_the_run(self):
        self.assertAlmostEqual(
            combining_length_um(4, 20.0, 1.5, 0.0), 90.0, places=9
        )

    def test_spreading_resistance_of_a_lone_cell_is_its_own(self):
        self.assertAlmostEqual(
            thermal_spreading_resistance(25.0, 1, 20.0, 50.0, 0.2), 25.0, places=9
        )

    def test_uncoupled_cells_do_not_heat_each_other(self):
        self.assertAlmostEqual(
            thermal_spreading_resistance(25.0, 4, 20.0, 50.0, 0.0), 25.0, places=9
        )

    def test_tight_pitch_spreading_matches_the_hand_calculation(self):
        self.assertAlmostEqual(
            thermal_spreading_resistance(25.0, 4, 20.0, 50.0, 0.2), 56.25, places=9
        )

    def test_opening_the_pitch_lowers_the_spreading_resistance(self):
        tight = thermal_spreading_resistance(25.0, 4, 20.0, 50.0, 0.2)
        spread = thermal_spreading_resistance(25.0, 4, 100.0, 50.0, 0.2)
        self.assertLess(spread, tight)

    def test_peak_channel_temperature_matches_the_hand_calculation(self):
        self.assertAlmostEqual(
            peak_channel_temperature_c(60.0, 4.0, 4, 56.25), 116.25, places=9
        )

    def test_interconnect_loss_scales_with_length(self):
        self.assertAlmostEqual(interconnect_loss_db(160.0, 0.6), 0.096, places=9)

    def test_a_zero_length_run_is_lossless(self):
        self.assertAlmostEqual(interconnect_loss_db(0.0, 0.6), 0.0, places=9)

    def test_negative_length_rejected(self):
        with self.assertRaises(ValueError):
            interconnect_loss_db(-10.0, 0.6)


class EvaluateCandidateTests(unittest.TestCase):
    def test_tight_metrics_match_the_hand_calculation(self):
        record = evaluate_candidate(TIGHT, MODEL)
        self.assertAlmostEqual(record["die_area_mm2"], TIGHT_AREA, places=9)
        self.assertAlmostEqual(record["peak_channel_temperature_c"], TIGHT_TEMP,
                               places=9)
        self.assertAlmostEqual(record["insertion_loss_db"], TIGHT_LOSS, places=9)

    def test_spread_metrics_match_the_hand_calculation(self):
        record = evaluate_candidate(SPREAD, MODEL)
        self.assertAlmostEqual(record["die_area_mm2"], SPREAD_AREA, places=9)
        self.assertAlmostEqual(record["peak_channel_temperature_c"], SPREAD_TEMP,
                               places=9)
        self.assertAlmostEqual(record["insertion_loss_db"], SPREAD_LOSS, places=9)

    def test_the_trade_pulls_in_opposite_directions(self):
        tight = evaluate_candidate(TIGHT, MODEL)
        spread = evaluate_candidate(SPREAD, MODEL)
        self.assertLess(spread["peak_channel_temperature_c"],
                        tight["peak_channel_temperature_c"])
        self.assertGreater(spread["insertion_loss_db"], tight["insertion_loss_db"])
        self.assertGreater(spread["die_area_mm2"], tight["die_area_mm2"])


class FeasibilityTests(unittest.TestCase):
    def test_no_constraints_accepts_everything(self):
        ok, reasons = feasibility(evaluate_candidate(TIGHT, MODEL), None)
        self.assertTrue(ok)
        self.assertEqual(reasons, [])

    def test_temperature_ceiling_stops_the_hot_arrangement(self):
        ok, reasons = feasibility(evaluate_candidate(TIGHT, MODEL),
                                  {"max_channel_temperature_c": 95.0})
        self.assertFalse(ok)
        self.assertEqual(len(reasons), 1)

    def test_a_candidate_exactly_on_the_ceiling_is_kept(self):
        ok, _ = feasibility(evaluate_candidate(SPREAD, MODEL),
                            {"max_channel_temperature_c": SPREAD_TEMP})
        self.assertTrue(ok)

    def test_a_candidate_exactly_on_the_area_budget_is_kept(self):
        ok, _ = feasibility(evaluate_candidate(TIGHT, MODEL),
                            {"max_die_area_mm2": TIGHT_AREA})
        self.assertTrue(ok)

    def test_every_broken_constraint_is_reported(self):
        ok, reasons = feasibility(
            evaluate_candidate(SPREAD, MODEL),
            {"max_channel_temperature_c": 80.0, "max_die_area_mm2": 0.5,
             "max_insertion_loss_db": 0.1},
        )
        self.assertFalse(ok)
        self.assertEqual(len(reasons), 3)

    def test_record_without_metrics_rejected(self):
        with self.assertRaises(ValueError):
            feasibility({"name": "tight"}, None)

    def test_constraint_tolerance_stays_negligible(self):
        self.assertLess(CONSTRAINT_TOLERANCE, 1e-6)


class ScoringTests(unittest.TestCase):
    def test_the_best_value_of_a_metric_normalises_to_one(self):
        self.assertAlmostEqual(normalise_metric(0.48, 0.48), 1.0, places=9)

    def test_a_worse_value_costs_more_than_one(self):
        self.assertAlmostEqual(normalise_metric(0.72, 0.48), 1.5, places=9)

    def test_zero_reference_rejected(self):
        with self.assertRaises(ValueError):
            normalise_metric(0.48, 0.0)

    def test_weighted_score_of_an_all_best_candidate_is_one(self):
        score = weighted_score(
            {"die_area_mm2": 1.0, "peak_channel_temperature_c": 1.0,
             "insertion_loss_db": 1.0},
            None,
        )
        self.assertAlmostEqual(score, 1.0, places=9)

    def test_weighted_score_missing_a_metric_rejected(self):
        with self.assertRaises(ValueError):
            weighted_score({"die_area_mm2": 1.0}, None)


class OptimiseLayoutTests(unittest.TestCase):
    def test_equal_weights_keep_the_compact_arrangement(self):
        result = optimise_layout([TIGHT, SPREAD], MODEL)
        self.assertEqual(result["selected"]["name"], "tight")
        self.assertAlmostEqual(
            result["selected"]["score"],
            (1.0 + TIGHT_TEMP / SPREAD_TEMP + 1.0) / 3.0,
            places=9,
        )

    def test_a_thermally_weighted_trade_flips_the_selection(self):
        result = optimise_layout(
            [TIGHT, SPREAD], MODEL, None,
            {"die_area_mm2": 0.05, "peak_channel_temperature_c": 0.9,
             "insertion_loss_db": 0.05},
        )
        self.assertEqual(result["selected"]["name"], "spread")

    def test_ranking_is_ordered_by_score(self):
        result = optimise_layout([SPREAD, TIGHT], MODEL)
        scores = [entry["score"] for entry in result["ranking"]]
        self.assertEqual(scores, sorted(scores))

    def test_a_rejected_candidate_is_kept_with_its_reason(self):
        result = optimise_layout([TIGHT, SPREAD], MODEL,
                                 {"max_channel_temperature_c": 95.0})
        self.assertEqual(result["selected"]["name"], "spread")
        self.assertEqual([r["name"] for r in result["rejected"]], ["tight"])
        self.assertTrue(result["findings"])

    def test_a_lone_survivor_is_flagged_as_an_unweighed_trade(self):
        result = optimise_layout([TIGHT, SPREAD], MODEL,
                                 {"max_channel_temperature_c": 95.0})
        self.assertTrue(any("only one arrangement" in f for f in result["findings"]))

    def test_no_survivor_returns_no_selection(self):
        result = optimise_layout([TIGHT, SPREAD], MODEL,
                                 {"max_channel_temperature_c": 70.0})
        self.assertIsNone(result["selected"])
        self.assertEqual(result["ranking"], [])
        self.assertEqual(len(result["rejected"]), 2)

    def test_every_candidate_is_reported_whether_or_not_it_survived(self):
        result = optimise_layout([TIGHT, SPREAD], MODEL,
                                 {"max_channel_temperature_c": 95.0})
        self.assertEqual([r["name"] for r in result["records"]],
                         ["spread", "tight"])

    def test_duplicate_candidate_name_rejected(self):
        with self.assertRaises(ValueError):
            optimise_layout([TIGHT, dict(TIGHT)], MODEL)

    def test_empty_candidate_set_rejected(self):
        with self.assertRaises(ValueError):
            optimise_layout([], MODEL)

    def test_scores_are_finite_for_every_survivor(self):
        result = optimise_layout([TIGHT, SPREAD], MODEL)
        self.assertTrue(all(math.isfinite(e["score"]) for e in result["feasible"]))


if __name__ == "__main__":
    unittest.main()
