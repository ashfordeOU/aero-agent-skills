#!/usr/bin/env python3
"""Gate 3 contract test for e2001-seeding-effectiveness-verification.

Offline, deterministic, stdlib unittest only.
"""

import math
import os
import statistics
import sys
import unittest

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import e2001_seeding_effectiveness_verification_logic as logic  # noqa: E402

GOOD_RUNS = [
    {"measured_threshold_w": 122.0, "onset_latency_s": 2.0},
    {"measured_threshold_w": 118.5, "onset_latency_s": 3.5},
    {"measured_threshold_w": 125.0, "onset_latency_s": 1.8},
]

PLANNED = {"frequency_hz": 12.0e9, "gap_mm": 0.6, "pressure_pa": 1.2e-5}
VALIDATION = {"frequency_hz": 12.0e9, "gap_mm": 0.6, "pressure_pa": 1.0e-5}
TOLERANCES = {"frequency_hz": 0.05, "gap_mm": 0.1, "pressure_pa": 0.25}


def base_spec(**over):
    spec = {
        "reference_threshold_w": 120.0,
        "reference_uncertainty_db": 0.5,
        "facility_uncertainty_db": 0.8,
        "runs": [dict(run) for run in GOOD_RUNS],
        "max_spread_db": 1.0,
        "max_onset_latency_s": 10.0,
        "validation_conditions": dict(VALIDATION),
        "planned_conditions": dict(PLANNED),
        "condition_tolerances": dict(TOLERANCES),
    }
    spec.update(over)
    return spec


class OffsetAndBand(unittest.TestCase):
    def test_identical_threshold_reads_zero_offset(self):
        self.assertAlmostEqual(logic.offset_db(120.0, 120.0), 0.0, places=12)

    def test_doubled_threshold_reads_three_decibel(self):
        self.assertAlmostEqual(logic.offset_db(240.0, 120.0), 3.0102999566, places=9)

    def test_halved_threshold_reads_minus_three_decibel(self):
        self.assertAlmostEqual(logic.offset_db(60.0, 120.0), -3.0102999566, places=9)

    def test_zero_measured_threshold_rejected(self):
        with self.assertRaises(ValueError):
            logic.offset_db(0.0, 120.0)

    def test_negative_measured_threshold_rejected(self):
        with self.assertRaises(ValueError):
            logic.offset_db(-5.0, 120.0)

    def test_zero_reference_threshold_rejected(self):
        with self.assertRaises(ValueError):
            logic.offset_db(120.0, 0.0)

    def test_non_numeric_threshold_rejected(self):
        with self.assertRaises(ValueError):
            logic.offset_db("120", 120.0)

    def test_band_combines_uncertainties_in_quadrature(self):
        self.assertAlmostEqual(logic.acceptance_band_db(0.3, 0.4), 0.5, places=12)

    def test_band_with_one_zero_term_is_the_other_term(self):
        self.assertAlmostEqual(logic.acceptance_band_db(0.8, 0.0), 0.8, places=12)

    def test_band_is_order_independent(self):
        self.assertAlmostEqual(
            logic.acceptance_band_db(0.5, 0.8),
            logic.acceptance_band_db(0.8, 0.5),
            places=15,
        )

    def test_negative_sample_uncertainty_rejected(self):
        with self.assertRaises(ValueError):
            logic.acceptance_band_db(-0.5, 0.8)

    def test_negative_facility_uncertainty_rejected(self):
        with self.assertRaises(ValueError):
            logic.acceptance_band_db(0.5, -0.8)


class OffsetCategorization(unittest.TestCase):
    def test_small_offset_sits_inside_the_band(self):
        self.assertEqual(logic.categorize_offset(0.2, 0.94), logic.WITHIN_BAND)

    def test_high_offset_names_weak_seeding(self):
        self.assertEqual(logic.categorize_offset(2.2, 0.94), logic.WEAK_SEEDING)

    def test_low_offset_names_a_suspect_sample(self):
        self.assertEqual(logic.categorize_offset(-1.76, 0.94), logic.SAMPLE_SUSPECT)

    def test_offset_exactly_at_the_band_edge_is_inside(self):
        self.assertEqual(logic.categorize_offset(0.94, 0.94), logic.WITHIN_BAND)

    def test_representation_error_at_the_band_edge_is_absorbed(self):
        # 0.1 + 0.2 lands one ULP above the 0,3 dB band; still compliant.
        self.assertEqual(logic.categorize_offset(0.1 + 0.2, 0.3), logic.WITHIN_BAND)

    def test_negative_band_rejected(self):
        with self.assertRaises(ValueError):
            logic.categorize_offset(0.2, -0.94)

    def test_non_numeric_offset_rejected(self):
        with self.assertRaises(ValueError):
            logic.categorize_offset("0.2", 0.94)


class RunSetValidation(unittest.TestCase):
    def test_valid_runs_are_normalised(self):
        out = logic.validate_runs(GOOD_RUNS)
        self.assertEqual(len(out), 3)
        self.assertAlmostEqual(out[0]["measured_threshold_w"], 122.0, places=12)
        self.assertAlmostEqual(out[0]["onset_latency_s"], 2.0, places=12)

    def test_runs_without_latency_are_accepted(self):
        out = logic.validate_runs([{"measured_threshold_w": 120.0}], min_runs=1)
        self.assertNotIn("onset_latency_s", out[0])

    def test_empty_run_set_rejected(self):
        with self.assertRaises(ValueError):
            logic.validate_runs([])

    def test_non_sequence_run_set_rejected(self):
        with self.assertRaises(ValueError):
            logic.validate_runs({"measured_threshold_w": 120.0})

    def test_non_dict_run_rejected(self):
        with self.assertRaises(ValueError):
            logic.validate_runs([120.0])

    def test_run_without_threshold_rejected(self):
        with self.assertRaises(ValueError):
            logic.validate_runs([{"onset_latency_s": 2.0}])

    def test_zero_threshold_run_rejected(self):
        with self.assertRaises(ValueError):
            logic.validate_runs([{"measured_threshold_w": 0.0}])

    def test_negative_latency_rejected(self):
        with self.assertRaises(ValueError):
            logic.validate_runs(
                [{"measured_threshold_w": 120.0, "onset_latency_s": -1.0}]
            )

    def test_non_integer_min_runs_rejected(self):
        with self.assertRaises(ValueError):
            logic.validate_runs(GOOD_RUNS, min_runs=3.0)

    def test_zero_min_runs_rejected(self):
        with self.assertRaises(ValueError):
            logic.validate_runs(GOOD_RUNS, min_runs=0)

    def test_offsets_are_produced_per_run(self):
        offsets = logic.offsets_for_runs(GOOD_RUNS, 120.0)
        self.assertEqual(len(offsets), 3)
        self.assertAlmostEqual(offsets[0], 0.07178584627123376, places=12)
        self.assertLess(offsets[1], 0.0)


class RunStatistics(unittest.TestCase):
    def test_spread_is_peak_to_peak(self):
        self.assertAlmostEqual(logic.spread_db([-0.5, 0.2, 0.9]), 1.4, places=12)

    def test_spread_of_one_run_is_zero(self):
        self.assertAlmostEqual(logic.spread_db([0.4]), 0.0, places=12)

    def test_deviation_of_one_run_is_zero(self):
        self.assertAlmostEqual(logic.deviation_db([0.4]), 0.0, places=12)

    def test_deviation_matches_the_sample_deviation(self):
        values = [-0.5, 0.2, 0.9]
        self.assertAlmostEqual(
            logic.deviation_db(values), statistics.stdev(values), places=12
        )

    def test_spread_rejects_an_empty_set(self):
        with self.assertRaises(ValueError):
            logic.spread_db([])

    def test_deviation_rejects_an_empty_set(self):
        with self.assertRaises(ValueError):
            logic.deviation_db([])

    def test_spread_rejects_a_non_numeric_entry(self):
        with self.assertRaises(ValueError):
            logic.spread_db([0.2, "0.9"])

    def test_repeatability_inside_the_limit_passes(self):
        self.assertTrue(logic.repeatability_ok(0.23, 1.0))

    def test_repeatability_at_the_limit_passes_through_representation_error(self):
        self.assertTrue(logic.repeatability_ok(0.1 + 0.2, 0.3))

    def test_repeatability_above_the_limit_fails(self):
        self.assertFalse(logic.repeatability_ok(1.4, 1.0))

    def test_zero_spread_limit_rejected(self):
        with self.assertRaises(ValueError):
            logic.repeatability_ok(0.2, 0.0)

    def test_negative_spread_rejected(self):
        with self.assertRaises(ValueError):
            logic.repeatability_ok(-0.2, 1.0)


class LatencyAndMargin(unittest.TestCase):
    def test_latency_inside_the_limit_passes(self):
        self.assertTrue(logic.latency_ok(2.0, 10.0))

    def test_latency_at_the_limit_passes_through_representation_error(self):
        self.assertTrue(logic.latency_ok(0.1 + 0.2, 0.3))

    def test_latency_above_the_limit_fails(self):
        self.assertFalse(logic.latency_ok(45.0, 10.0))

    def test_negative_latency_rejected(self):
        with self.assertRaises(ValueError):
            logic.latency_ok(-1.0, 10.0)

    def test_zero_latency_limit_rejected(self):
        with self.assertRaises(ValueError):
            logic.latency_ok(2.0, 0.0)

    def test_margin_is_the_band_less_the_worst_offset(self):
        self.assertAlmostEqual(
            logic.seeding_margin_db([-0.5, 0.2, 0.4], 0.94), 0.54, places=12
        )

    def test_margin_goes_negative_when_a_run_leaves_the_band(self):
        self.assertLess(logic.seeding_margin_db([-0.2, 2.2], 0.94), 0.0)

    def test_margin_rejects_an_empty_set(self):
        with self.assertRaises(ValueError):
            logic.seeding_margin_db([], 0.94)


class ConditionRepresentativeness(unittest.TestCase):
    def test_identical_conditions_are_representative(self):
        out = logic.conditions_representative(PLANNED, PLANNED, TOLERANCES)
        self.assertTrue(out["representative"])

    def test_pressure_inside_tolerance_is_representative(self):
        out = logic.conditions_representative(VALIDATION, PLANNED, TOLERANCES)
        self.assertTrue(out["representative"])
        self.assertAlmostEqual(
            out["detail"]["pressure_pa"]["deviation"], 1.0 / 6.0, places=9
        )

    def test_gap_outside_tolerance_is_not_representative(self):
        drift = dict(VALIDATION)
        drift["gap_mm"] = 0.9
        out = logic.conditions_representative(drift, PLANNED, TOLERANCES)
        self.assertFalse(out["representative"])
        self.assertFalse(out["detail"]["gap_mm"]["representative"])

    def test_deviation_exactly_at_tolerance_is_representative(self):
        # |0,66 - 0,6| / 0,6 lands a few ULPs above the 0,1 tolerance.
        drift = dict(VALIDATION)
        drift["gap_mm"] = 0.66
        out = logic.conditions_representative(drift, PLANNED, TOLERANCES)
        self.assertGreater(out["detail"]["gap_mm"]["deviation"], 0.1)
        self.assertTrue(out["detail"]["gap_mm"]["representative"])
        self.assertTrue(out["representative"])

    def test_unknown_condition_key_rejected(self):
        drift = dict(VALIDATION)
        drift["humidity_pc"] = 40.0
        with self.assertRaises(ValueError):
            logic.conditions_representative(drift, PLANNED, TOLERANCES)

    def test_missing_condition_key_rejected(self):
        drift = dict(VALIDATION)
        del drift["gap_mm"]
        with self.assertRaises(ValueError):
            logic.conditions_representative(drift, PLANNED, TOLERANCES)

    def test_non_dict_conditions_rejected(self):
        with self.assertRaises(ValueError):
            logic.conditions_representative(["12e9"], PLANNED, TOLERANCES)

    def test_zero_tolerance_rejected(self):
        bad = dict(TOLERANCES)
        bad["gap_mm"] = 0.0
        with self.assertRaises(ValueError):
            logic.conditions_representative(VALIDATION, PLANNED, bad)

    def test_tolerance_above_unity_rejected(self):
        bad = dict(TOLERANCES)
        bad["gap_mm"] = 1.5
        with self.assertRaises(ValueError):
            logic.conditions_representative(VALIDATION, PLANNED, bad)

    def test_zero_planned_value_rejected(self):
        bad = dict(PLANNED)
        bad["gap_mm"] = 0.0
        with self.assertRaises(ValueError):
            logic.conditions_representative(VALIDATION, bad, TOLERANCES)


class FullVerification(unittest.TestCase):
    def test_healthy_validation_demonstrates_the_seeding(self):
        out = logic.verify_seeding_effectiveness(base_spec())
        self.assertTrue(out["seeding_effective"])
        self.assertEqual(out["findings"], [])
        self.assertEqual(len(out["runs"]), 3)

    def test_reported_band_spread_and_margin(self):
        out = logic.verify_seeding_effectiveness(base_spec())
        self.assertAlmostEqual(out["acceptance_band_db"], math.hypot(0.5, 0.8), places=12)
        self.assertAlmostEqual(out["spread_db"], 0.23191662661933754, places=10)
        self.assertAlmostEqual(out["seeding_margin_db"], 0.7661104436013442, places=10)
        self.assertGreater(out["deviation_db"], 0.0)

    def test_every_run_is_categorized_inside_the_band(self):
        out = logic.verify_seeding_effectiveness(base_spec())
        for report in out["runs"]:
            self.assertEqual(report["category"], logic.WITHIN_BAND)
            self.assertTrue(report["latency_ok"])

    def test_high_threshold_run_signals_weak_seeding(self):
        runs = [dict(run) for run in GOOD_RUNS]
        runs[1]["measured_threshold_w"] = 200.0
        out = logic.verify_seeding_effectiveness(base_spec(runs=runs, max_spread_db=5.0))
        self.assertIn("measured-threshold-above-acceptance-band", out["findings"])
        self.assertFalse(out["seeding_effective"])
        self.assertEqual(out["runs"][1]["category"], logic.WEAK_SEEDING)

    def test_low_threshold_run_points_at_the_reference_sample(self):
        runs = [dict(run) for run in GOOD_RUNS]
        runs[0]["measured_threshold_w"] = 80.0
        out = logic.verify_seeding_effectiveness(base_spec(runs=runs, max_spread_db=5.0))
        self.assertIn("measured-threshold-below-acceptance-band", out["findings"])
        self.assertEqual(out["runs"][0]["category"], logic.SAMPLE_SUSPECT)

    def test_wide_spread_is_flagged_even_inside_the_band(self):
        runs = [
            {"measured_threshold_w": 120.0, "onset_latency_s": 2.0},
            {"measured_threshold_w": 145.0, "onset_latency_s": 2.0},
            {"measured_threshold_w": 100.0, "onset_latency_s": 2.0},
        ]
        out = logic.verify_seeding_effectiveness(
            base_spec(runs=runs, max_spread_db=0.5, reference_uncertainty_db=1.5,
                      facility_uncertainty_db=1.5)
        )
        self.assertIn("run-to-run-spread-above-limit", out["findings"])

    def test_long_onset_latency_is_flagged(self):
        runs = [dict(run) for run in GOOD_RUNS]
        runs[2]["onset_latency_s"] = 45.0
        out = logic.verify_seeding_effectiveness(base_spec(runs=runs))
        self.assertIn("detection-onset-latency-above-limit", out["findings"])
        self.assertFalse(out["runs"][2]["latency_ok"])

    def test_non_representative_conditions_are_flagged(self):
        drift = dict(VALIDATION)
        drift["frequency_hz"] = 20.0e9
        out = logic.verify_seeding_effectiveness(base_spec(validation_conditions=drift))
        self.assertIn("validation-conditions-not-representative", out["findings"])

    def test_run_set_shorter_than_the_declared_minimum_is_flagged(self):
        out = logic.verify_seeding_effectiveness(
            base_spec(runs=[dict(GOOD_RUNS[0]), dict(GOOD_RUNS[1])])
        )
        self.assertIn("insufficient-validation-runs", out["findings"])
        self.assertFalse(out["seeding_effective"])

    def test_a_lowered_minimum_accepts_a_shorter_run_set(self):
        out = logic.verify_seeding_effectiveness(
            base_spec(runs=[dict(GOOD_RUNS[0]), dict(GOOD_RUNS[1])], min_runs=2)
        )
        self.assertNotIn("insufficient-validation-runs", out["findings"])
        self.assertTrue(out["seeding_effective"])

    def test_a_single_run_meets_a_minimum_of_one(self):
        out = logic.verify_seeding_effectiveness(
            base_spec(runs=[dict(GOOD_RUNS[0])], min_runs=1)
        )
        self.assertTrue(out["seeding_effective"])
        self.assertAlmostEqual(out["spread_db"], 0.0, places=12)
        self.assertAlmostEqual(out["deviation_db"], 0.0, places=12)

    def test_findings_are_reported_once_each(self):
        runs = [
            {"measured_threshold_w": 200.0, "onset_latency_s": 2.0},
            {"measured_threshold_w": 205.0, "onset_latency_s": 2.0},
            {"measured_threshold_w": 210.0, "onset_latency_s": 2.0},
        ]
        out = logic.verify_seeding_effectiveness(base_spec(runs=runs))
        self.assertEqual(
            out["findings"].count("measured-threshold-above-acceptance-band"), 1
        )

    def test_runs_without_latency_do_not_raise(self):
        runs = [{"measured_threshold_w": item["measured_threshold_w"]} for item in GOOD_RUNS]
        out = logic.verify_seeding_effectiveness(base_spec(runs=runs))
        self.assertTrue(out["seeding_effective"])
        self.assertIsNone(out["runs"][0]["onset_latency_s"])

    def test_missing_spec_key_rejected(self):
        spec = base_spec()
        del spec["max_spread_db"]
        with self.assertRaises(ValueError):
            logic.verify_seeding_effectiveness(spec)

    def test_non_dict_spec_rejected(self):
        with self.assertRaises(ValueError):
            logic.verify_seeding_effectiveness("reference-sample")

    def test_zero_reference_threshold_in_spec_rejected(self):
        with self.assertRaises(ValueError):
            logic.verify_seeding_effectiveness(base_spec(reference_threshold_w=0.0))


if __name__ == "__main__":
    unittest.main()
