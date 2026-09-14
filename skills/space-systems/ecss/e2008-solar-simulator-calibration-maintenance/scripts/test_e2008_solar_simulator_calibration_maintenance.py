#!/usr/bin/env python3
"""Contract test for the solar-simulator upkeep fitness check (offline)."""

import copy
import unittest

from e2008_solar_simulator_calibration_maintenance_logic import (
    BEAM_QUALITIES,
    DEFAULT_SIMULATOR_BOUNDS,
    DEFAULT_UPKEEP_POLICY,
    GRADE_OUT_OF_RANGE,
    SIMULATOR_GRADES,
    UPKEEP_DUE,
    UPKEEP_DUE_SOON,
    UPKEEP_SERVICEABLE,
    VERDICT_CONDITIONAL,
    VERDICT_FIT,
    VERDICT_RECALIBRATE,
    VERDICT_SERVICE,
    assess_simulator_fitness,
    calibration_due_status,
    grade_meets_requirement,
    grade_percent_quality,
    grade_spectral_match,
    lamp_service_status,
    simulator_grade,
    validate_simulator_bounds,
    validate_upkeep_policy,
    worst_grade,
)

GOOD_BANDS = {"400-500nm": 1.02, "500-600nm": 0.98, "600-700nm": 1.05}
POOR_BANDS = {"400-500nm": 1.02, "500-600nm": 0.98, "600-700nm": 1.35}

HEALTHY_CASE = {
    "required_grade": "A",
    "spatial_non_uniformity_percent": 1.4,
    "temporal_instability_percent": 0.8,
    "spectral_match_ratios": GOOD_BANDS,
    "lamp_hours_run": 200.0,
    "days_since_reference_calibration": 40.0,
}


def _case(base, **overrides):
    case = copy.deepcopy(base)
    case.update(overrides)
    return case


class BoundsTests(unittest.TestCase):
    def test_default_bounds_validate(self):
        self.assertIs(
            validate_simulator_bounds(DEFAULT_SIMULATOR_BOUNDS),
            DEFAULT_SIMULATOR_BOUNDS,
        )

    def test_default_upkeep_policy_validates(self):
        self.assertIs(
            validate_upkeep_policy(DEFAULT_UPKEEP_POLICY), DEFAULT_UPKEEP_POLICY
        )

    def test_bounds_reject_a_non_monotone_grade_table(self):
        broken = copy.deepcopy(DEFAULT_SIMULATOR_BOUNDS)
        broken["spatial_non_uniformity_percent"]["C"] = 1.0
        with self.assertRaises(ValueError):
            validate_simulator_bounds(broken)

    def test_bounds_reject_a_missing_grade(self):
        broken = copy.deepcopy(DEFAULT_SIMULATOR_BOUNDS)
        del broken["temporal_instability_percent"]["B"]
        with self.assertRaises(ValueError):
            validate_simulator_bounds(broken)

    def test_bounds_reject_an_inverted_spectral_window(self):
        broken = copy.deepcopy(DEFAULT_SIMULATOR_BOUNDS)
        broken["spectral_match_ratio"]["A"] = (1.3, 0.8)
        with self.assertRaises(ValueError):
            validate_simulator_bounds(broken)

    def test_upkeep_policy_rejects_a_warning_fraction_above_one(self):
        broken = dict(DEFAULT_UPKEEP_POLICY, lamp_warning_fraction=1.5)
        with self.assertRaises(ValueError):
            validate_upkeep_policy(broken)

    def test_upkeep_policy_rejects_a_non_mapping(self):
        with self.assertRaises(ValueError):
            validate_upkeep_policy("default")


class GradingTests(unittest.TestCase):
    def test_percent_quality_grades_by_band(self):
        table = DEFAULT_SIMULATOR_BOUNDS["spatial_non_uniformity_percent"]
        self.assertEqual(grade_percent_quality(1.0, table), "A")
        self.assertEqual(grade_percent_quality(3.0, table), "B")
        self.assertEqual(grade_percent_quality(8.0, table), "C")

    def test_percent_quality_exactly_on_a_bound_keeps_the_better_grade(self):
        table = DEFAULT_SIMULATOR_BOUNDS["spatial_non_uniformity_percent"]
        self.assertEqual(grade_percent_quality(2.0, table), "A")
        self.assertEqual(grade_percent_quality(5.0, table), "B")

    def test_percent_quality_beyond_every_bound_is_out_of_range(self):
        table = DEFAULT_SIMULATOR_BOUNDS["temporal_instability_percent"]
        self.assertEqual(grade_percent_quality(14.0, table), GRADE_OUT_OF_RANGE)

    def test_percent_quality_rejects_a_negative_value(self):
        with self.assertRaises(ValueError):
            grade_percent_quality(
                -1.0, DEFAULT_SIMULATOR_BOUNDS["temporal_instability_percent"]
            )

    def test_spectral_match_takes_the_worst_band(self):
        result = grade_spectral_match(
            POOR_BANDS, DEFAULT_SIMULATOR_BOUNDS["spectral_match_ratio"]
        )
        self.assertEqual(result["grade"], "B")
        self.assertEqual(result["per_band"]["600-700nm"], "B")
        self.assertEqual(result["per_band"]["500-600nm"], "A")

    def test_spectral_match_on_a_window_edge_keeps_the_better_grade(self):
        result = grade_spectral_match(
            {"one": 1.25, "two": 0.75},
            DEFAULT_SIMULATOR_BOUNDS["spectral_match_ratio"],
        )
        self.assertEqual(result["grade"], "A")

    def test_spectral_match_rejects_an_empty_band_set(self):
        with self.assertRaises(ValueError):
            grade_spectral_match({}, DEFAULT_SIMULATOR_BOUNDS["spectral_match_ratio"])

    def test_spectral_match_rejects_a_non_positive_ratio(self):
        with self.assertRaises(ValueError):
            grade_spectral_match(
                {"one": 0.0}, DEFAULT_SIMULATOR_BOUNDS["spectral_match_ratio"]
            )

    def test_worst_grade_orders_the_letters(self):
        self.assertEqual(worst_grade(["A", "C", "B"]), "C")
        self.assertEqual(worst_grade(["A", "A"]), "A")

    def test_worst_grade_lets_out_of_range_beat_every_letter(self):
        self.assertEqual(
            worst_grade(["A", GRADE_OUT_OF_RANGE, "C"]), GRADE_OUT_OF_RANGE
        )

    def test_worst_grade_rejects_an_unknown_grade(self):
        with self.assertRaises(ValueError):
            worst_grade(["A", "D"])

    def test_worst_grade_rejects_an_empty_collection(self):
        with self.assertRaises(ValueError):
            worst_grade([])

    def test_requirement_comparison_is_ordered(self):
        self.assertTrue(grade_meets_requirement("A", "B"))
        self.assertTrue(grade_meets_requirement("B", "B"))
        self.assertFalse(grade_meets_requirement("C", "B"))
        self.assertFalse(grade_meets_requirement(GRADE_OUT_OF_RANGE, "C"))

    def test_requirement_comparison_rejects_an_unknown_requirement(self):
        with self.assertRaises(ValueError):
            grade_meets_requirement("A", GRADE_OUT_OF_RANGE)

    def test_beam_grade_is_the_worst_of_the_three_qualities(self):
        result = simulator_grade(
            {
                "spatial_non_uniformity_percent": 1.0,
                "temporal_instability_percent": 0.5,
                "spectral_match_ratios": POOR_BANDS,
            }
        )
        self.assertEqual(result["grade"], "B")
        self.assertEqual(sorted(result["per_quality"]), sorted(BEAM_QUALITIES))

    def test_beam_grade_rejects_a_missing_quality(self):
        with self.assertRaises(ValueError):
            simulator_grade(
                {
                    "spatial_non_uniformity_percent": 1.0,
                    "spectral_match_ratios": GOOD_BANDS,
                }
            )


class UpkeepTests(unittest.TestCase):
    def test_fresh_lamp_is_serviceable(self):
        result = lamp_service_status(100.0, 1000.0, 0.8)
        self.assertEqual(result["status"], UPKEEP_SERVICEABLE)
        self.assertAlmostEqual(result["hours_remaining"], 900.0, places=9)

    def test_lamp_inside_the_warning_fraction_is_due_soon(self):
        self.assertEqual(
            lamp_service_status(900.0, 1000.0, 0.8)["status"], UPKEEP_DUE_SOON
        )

    def test_lamp_exactly_on_its_rated_life_is_not_yet_past_it(self):
        result = lamp_service_status(1000.0, 1000.0, 0.8)
        self.assertEqual(result["status"], UPKEEP_DUE_SOON)
        self.assertAlmostEqual(result["fraction_used"], 1.0, places=9)

    def test_lamp_past_its_rated_life_is_due(self):
        self.assertEqual(
            lamp_service_status(1100.0, 1000.0, 0.8)["status"], UPKEEP_DUE
        )

    def test_lamp_rejects_a_negative_hour_count(self):
        with self.assertRaises(ValueError):
            lamp_service_status(-5.0, 1000.0)

    def test_calibration_interval_tracks_the_same_three_states(self):
        self.assertEqual(
            calibration_due_status(10.0, 180.0, 0.9)["status"], UPKEEP_SERVICEABLE
        )
        self.assertEqual(
            calibration_due_status(175.0, 180.0, 0.9)["status"], UPKEEP_DUE_SOON
        )
        self.assertEqual(
            calibration_due_status(200.0, 180.0, 0.9)["status"], UPKEEP_DUE
        )

    def test_calibration_rejects_a_missing_day_count(self):
        with self.assertRaises(ValueError):
            calibration_due_status(None, 180.0)


class FitnessTests(unittest.TestCase):
    def test_healthy_simulator_is_fit_for_measurement(self):
        result = assess_simulator_fitness(HEALTHY_CASE)
        self.assertEqual(result["verdict"], VERDICT_FIT)
        self.assertEqual(result["achieved_grade"], "A")
        self.assertTrue(result["usable_for_measurement"])
        self.assertEqual(result["findings"], [])

    def test_a_beam_short_of_the_required_grade_is_conditional(self):
        result = assess_simulator_fitness(
            _case(HEALTHY_CASE, spectral_match_ratios=POOR_BANDS)
        )
        self.assertEqual(result["achieved_grade"], "B")
        self.assertFalse(result["meets_required_grade"])
        self.assertEqual(result["verdict"], VERDICT_CONDITIONAL)
        self.assertFalse(result["usable_for_measurement"])

    def test_the_same_beam_passes_when_the_task_demands_less(self):
        result = assess_simulator_fitness(
            _case(HEALTHY_CASE, spectral_match_ratios=POOR_BANDS, required_grade="B")
        )
        self.assertTrue(result["meets_required_grade"])
        self.assertEqual(result["verdict"], VERDICT_FIT)

    def test_an_overdue_reference_calibration_forces_recalibration(self):
        result = assess_simulator_fitness(
            _case(HEALTHY_CASE, days_since_reference_calibration=400.0)
        )
        self.assertEqual(result["verdict"], VERDICT_RECALIBRATE)
        self.assertTrue(any("past its interval" in f for f in result["findings"]))

    def test_an_expired_lamp_outranks_an_overdue_calibration(self):
        result = assess_simulator_fitness(
            _case(
                HEALTHY_CASE,
                lamp_hours_run=1400.0,
                days_since_reference_calibration=400.0,
            )
        )
        self.assertEqual(result["verdict"], VERDICT_SERVICE)

    def test_a_beam_outside_every_bound_needs_service(self):
        result = assess_simulator_fitness(
            _case(HEALTHY_CASE, temporal_instability_percent=25.0)
        )
        self.assertEqual(result["achieved_grade"], GRADE_OUT_OF_RANGE)
        self.assertEqual(result["verdict"], VERDICT_SERVICE)

    def test_a_lamp_warning_alone_is_conditional(self):
        result = assess_simulator_fitness(_case(HEALTHY_CASE, lamp_hours_run=900.0))
        self.assertEqual(result["verdict"], VERDICT_CONDITIONAL)
        self.assertTrue(any("warning fraction" in f for f in result["findings"]))

    def test_the_spectral_grade_is_reported_band_by_band(self):
        result = assess_simulator_fitness(
            _case(HEALTHY_CASE, spectral_match_ratios=POOR_BANDS)
        )
        self.assertEqual(sorted(result["spectral_per_band"]), sorted(POOR_BANDS))

    def test_a_shorter_agreed_calibration_interval_is_honoured(self):
        result = assess_simulator_fitness(
            _case(HEALTHY_CASE, reference_calibration_interval_days=30.0)
        )
        self.assertEqual(result["verdict"], VERDICT_RECALIBRATE)

    def test_fitness_rejects_an_unknown_required_grade(self):
        with self.assertRaises(ValueError):
            assess_simulator_fitness(_case(HEALTHY_CASE, required_grade="AA"))

    def test_fitness_rejects_a_non_mapping_case(self):
        with self.assertRaises(ValueError):
            assess_simulator_fitness("simulator")

    def test_fitness_rejects_a_missing_lamp_hour_count(self):
        case = _case(HEALTHY_CASE)
        del case["lamp_hours_run"]
        with self.assertRaises(ValueError):
            assess_simulator_fitness(case)

    def test_every_grade_is_accepted_as_a_requirement(self):
        for grade in SIMULATOR_GRADES:
            result = assess_simulator_fitness(_case(HEALTHY_CASE, required_grade=grade))
            self.assertEqual(result["required_grade"], grade)


if __name__ == "__main__":
    unittest.main()
