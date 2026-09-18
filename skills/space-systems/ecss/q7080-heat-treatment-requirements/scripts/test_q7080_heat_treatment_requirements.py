#!/usr/bin/env python3
"""Contract test for post-build heat-treatment verification (offline)."""

import copy
import unittest

from q7080_heat_treatment_requirements_logic import (
    SOAK_STEP_TYPES,
    VERDICT_ACCEPT,
    VERDICT_REJECT,
    VERDICT_REVIEW,
    assess_heat_treatment,
    check_sequence,
    coldest_envelope,
    furnace_survey_status,
    grade_step,
    max_ramp_rate,
    peak_temperature,
    soak_dwell_minutes,
    validate_traces,
)


def make_trace(target_c, hold_min, ramp_c_per_min=5.0, start_c=25.0, offset_c=0.0,
               sample_min=10.0):
    """Synthetic load-thermocouple trace: ramp, hold at target, then cool."""
    samples = []
    minute = 0.0
    temp = start_c
    samples.append((minute, temp + offset_c))
    while temp < target_c - 5.0:
        minute += sample_min
        temp = min(target_c, temp + ramp_c_per_min * sample_min)
        samples.append((minute, temp + offset_c))
    end = minute + hold_min
    while minute < end:
        minute += sample_min
        samples.append((minute, target_c + offset_c))
    minute += sample_min
    samples.append((minute, start_c + offset_c))
    return samples


RELIEF_REQUIREMENT = {
    "target_c": 300.0,
    "band_c": 10.0,
    "min_dwell_min": 120.0,
    "max_ramp_c_per_min": 5.0,
    "atmospheres": ("vacuum", "argon"),
}

QUENCH_REQUIREMENT = {
    "target_c": 60.0,
    "band_c": 10.0,
    "min_dwell_min": 5.0,
    "atmospheres": ("air", "argon", "nitrogen", "vacuum"),
    "max_quench_transfer_s": 12.0,
}

QUENCH_TRACE = [
    (0.0, 530.0),
    (0.4, 180.0),
    (1.0, 62.0),
    (6.0, 60.0),
    (12.0, 58.0),
]

GOOD_CASE = {
    "steps": [
        {
            "type": "stress-relief",
            "atmosphere": "argon",
            "traces": [make_trace(300.0, 120.0), make_trace(300.0, 120.0, offset_c=-4.0)],
        }
    ],
    "requirements": {"stress-relief": RELIEF_REQUIREMENT},
    "plate_removal_index": 1,
    "days_since_survey": 100.0,
    "max_interval_days": 365.0,
    "load_thermocouples": 3,
    "required_thermocouples": 3,
}


def _case(**overrides):
    case = copy.deepcopy(GOOD_CASE)
    case.update(overrides)
    return case


class TraceValidationTests(unittest.TestCase):
    def test_traces_returned_as_float_pairs(self):
        cleaned = validate_traces([[(0, 25), (10, 300)]])
        self.assertEqual(cleaned, [[(0.0, 25.0), (10.0, 300.0)]])

    def test_empty_trace_set_rejected(self):
        with self.assertRaises(ValueError):
            validate_traces([])

    def test_single_sample_trace_rejected(self):
        with self.assertRaises(ValueError):
            validate_traces([[(0.0, 25.0)]])

    def test_non_increasing_time_base_rejected(self):
        with self.assertRaises(ValueError):
            validate_traces([[(0.0, 25.0), (0.0, 300.0)]])

    def test_traces_on_different_time_bases_rejected(self):
        with self.assertRaises(ValueError):
            validate_traces([[(0.0, 25.0), (10.0, 300.0)],
                             [(0.0, 25.0), (11.0, 300.0)]])

    def test_traces_of_different_length_rejected(self):
        with self.assertRaises(ValueError):
            validate_traces([[(0.0, 25.0), (10.0, 300.0)],
                             [(0.0, 25.0), (10.0, 300.0), (20.0, 300.0)]])

    def test_malformed_sample_rejected(self):
        with self.assertRaises(ValueError):
            validate_traces([[(0.0, 25.0), (10.0,)]])


class EnvelopeTests(unittest.TestCase):
    def test_envelope_takes_the_colder_couple_sample_by_sample(self):
        envelope = coldest_envelope(
            [[(0.0, 25.0), (10.0, 300.0)], [(0.0, 20.0), (10.0, 310.0)]]
        )
        self.assertEqual(envelope, [(0.0, 20.0), (10.0, 300.0)])

    def test_peak_is_the_hottest_envelope_sample(self):
        self.assertAlmostEqual(peak_temperature(make_trace(300.0, 60.0)), 300.0, places=9)


class SoakDwellTests(unittest.TestCase):
    def test_dwell_equals_the_hold_at_temperature(self):
        dwell = soak_dwell_minutes(make_trace(300.0, 120.0), 300.0, 10.0)
        self.assertAlmostEqual(dwell, 120.0, places=9)

    def test_sample_exactly_on_the_band_edge_counts_as_inside(self):
        envelope = [(0.0, 290.0), (30.0, 295.0), (60.0, 310.0)]
        self.assertAlmostEqual(soak_dwell_minutes(envelope, 300.0, 10.0), 60.0, places=9)

    def test_overshoot_breaks_the_soak_as_surely_as_a_shortfall(self):
        envelope = make_trace(320.0, 120.0)
        self.assertAlmostEqual(soak_dwell_minutes(envelope, 300.0, 10.0), 0.0, places=9)

    def test_longest_contiguous_run_wins_over_the_total(self):
        envelope = [(0.0, 300.0), (10.0, 350.0), (20.0, 300.0), (60.0, 300.0)]
        self.assertAlmostEqual(soak_dwell_minutes(envelope, 300.0, 10.0), 40.0, places=9)

    def test_zero_band_rejected(self):
        with self.assertRaises(ValueError):
            soak_dwell_minutes(make_trace(300.0, 60.0), 300.0, 0.0)

    def test_cold_couple_outside_the_band_gives_no_dwell(self):
        envelope = coldest_envelope(
            [make_trace(300.0, 120.0), make_trace(300.0, 120.0, offset_c=-15.0)]
        )
        self.assertAlmostEqual(soak_dwell_minutes(envelope, 300.0, 10.0), 0.0, places=9)


class RampTests(unittest.TestCase):
    def test_approach_ramp_matches_the_declared_rate(self):
        rate = max_ramp_rate(make_trace(300.0, 60.0, ramp_c_per_min=5.0), 300.0, 10.0)
        self.assertAlmostEqual(rate, 5.0, places=9)

    def test_faster_approach_is_reported(self):
        rate = max_ramp_rate(make_trace(300.0, 60.0, ramp_c_per_min=12.0), 300.0, 10.0)
        self.assertAlmostEqual(rate, 12.0, places=9)

    def test_rate_inside_the_band_is_not_an_approach_ramp(self):
        envelope = [(0.0, 295.0), (10.0, 305.0), (20.0, 300.0)]
        self.assertAlmostEqual(max_ramp_rate(envelope, 300.0, 10.0), 0.0, places=9)

    def test_single_sample_envelope_rejected(self):
        with self.assertRaises(ValueError):
            max_ramp_rate([(0.0, 25.0)], 300.0, 10.0)


class GradeStepTests(unittest.TestCase):
    def _step(self, **overrides):
        step = {
            "type": "stress-relief",
            "atmosphere": "argon",
            "traces": [make_trace(300.0, 120.0)],
        }
        step.update(overrides)
        return step

    def test_compliant_soak_accepts_with_no_findings(self):
        record = grade_step(self._step(), RELIEF_REQUIREMENT)
        self.assertEqual(record["verdict"], VERDICT_ACCEPT)
        self.assertEqual(record["findings"], [])

    def test_dwell_exactly_on_the_requirement_accepts(self):
        requirement = dict(RELIEF_REQUIREMENT, min_dwell_min=120.0)
        record = grade_step(self._step(), requirement)
        self.assertAlmostEqual(record["dwell_min"], 120.0, places=9)
        self.assertEqual(record["verdict"], VERDICT_ACCEPT)

    def test_short_dwell_rejects(self):
        step = self._step(traces=[make_trace(300.0, 60.0)])
        record = grade_step(step, RELIEF_REQUIREMENT)
        self.assertEqual(record["verdict"], VERDICT_REJECT)
        self.assertTrue(any("dwell" in text for text in record["findings"]))

    def test_overshoot_rejects(self):
        step = self._step(traces=[make_trace(330.0, 180.0)])
        record = grade_step(step, RELIEF_REQUIREMENT)
        self.assertEqual(record["verdict"], VERDICT_REJECT)
        self.assertTrue(any("overshot" in text for text in record["findings"]))

    def test_fast_ramp_rejects(self):
        step = self._step(traces=[make_trace(300.0, 120.0, ramp_c_per_min=12.0)])
        record = grade_step(step, RELIEF_REQUIREMENT)
        self.assertEqual(record["verdict"], VERDICT_REJECT)
        self.assertTrue(any("ramp" in text for text in record["findings"]))

    def test_unprotected_atmosphere_rejects(self):
        record = grade_step(self._step(atmosphere="air"), RELIEF_REQUIREMENT)
        self.assertEqual(record["verdict"], VERDICT_REJECT)

    def test_unknown_atmosphere_rejected_as_input(self):
        with self.assertRaises(ValueError):
            grade_step(self._step(atmosphere="helium"), RELIEF_REQUIREMENT)

    def test_unknown_step_type_rejected_as_input(self):
        with self.assertRaises(ValueError):
            grade_step(self._step(type="polishing"), RELIEF_REQUIREMENT)

    def test_missing_requirement_field_rejected(self):
        requirement = dict(RELIEF_REQUIREMENT)
        del requirement["min_dwell_min"]
        with self.assertRaises(ValueError):
            grade_step(self._step(), requirement)

    def test_quench_graded_on_immersion_not_on_a_soak_overshoot(self):
        step = {
            "type": "quench",
            "atmosphere": "air",
            "traces": [QUENCH_TRACE],
            "quench_transfer_s": 8.0,
        }
        record = grade_step(step, QUENCH_REQUIREMENT)
        self.assertFalse(record["graded_as_soak"])
        self.assertEqual(record["verdict"], VERDICT_ACCEPT)

    def test_quench_transfer_over_the_window_rejects(self):
        step = {
            "type": "quench",
            "atmosphere": "air",
            "traces": [QUENCH_TRACE],
            "quench_transfer_s": 40.0,
        }
        record = grade_step(step, QUENCH_REQUIREMENT)
        self.assertEqual(record["verdict"], VERDICT_REJECT)
        self.assertTrue(any("transfer" in text for text in record["findings"]))

    def test_quench_without_a_measured_transfer_rejected(self):
        step = {"type": "quench", "atmosphere": "air", "traces": [QUENCH_TRACE]}
        with self.assertRaises(ValueError):
            grade_step(step, QUENCH_REQUIREMENT)

    def test_soak_types_exclude_the_quench(self):
        self.assertNotIn("quench", SOAK_STEP_TYPES)


class SequenceTests(unittest.TestCase):
    def test_relief_before_plate_removal_accepts(self):
        result = check_sequence(["stress-relief"], plate_removal_index=1)
        self.assertEqual(result["verdict"], VERDICT_ACCEPT)

    def test_plate_removal_before_relief_rejects(self):
        result = check_sequence(["stress-relief"], plate_removal_index=0)
        self.assertEqual(result["verdict"], VERDICT_REJECT)
        self.assertTrue(any("plate" in text for text in result["findings"]))

    def test_route_without_stress_relief_rejects(self):
        result = check_sequence(["solution", "quench", "ageing"])
        self.assertEqual(result["verdict"], VERDICT_REJECT)

    def test_ageing_before_solution_rejects(self):
        result = check_sequence(
            ["stress-relief", "ageing", "solution", "quench"], plate_removal_index=1
        )
        self.assertEqual(result["verdict"], VERDICT_REJECT)

    def test_solution_without_quench_rejects(self):
        result = check_sequence(
            ["stress-relief", "solution", "ageing"], plate_removal_index=1
        )
        self.assertEqual(result["verdict"], VERDICT_REJECT)

    def test_quench_not_directly_after_solution_rejects(self):
        result = check_sequence(
            ["stress-relief", "solution", "ageing", "quench"], plate_removal_index=1
        )
        self.assertEqual(result["verdict"], VERDICT_REJECT)

    def test_repeated_solution_is_a_review(self):
        result = check_sequence(
            ["stress-relief", "solution", "quench", "solution", "quench"],
            plate_removal_index=1,
        )
        self.assertEqual(result["verdict"], VERDICT_REVIEW)

    def test_ageing_before_hip_is_a_review(self):
        result = check_sequence(
            ["stress-relief", "ageing", "hot-isostatic-pressing"],
            plate_removal_index=1,
        )
        self.assertEqual(result["verdict"], VERDICT_REVIEW)

    def test_plate_removal_index_outside_the_route_rejected(self):
        with self.assertRaises(ValueError):
            check_sequence(["stress-relief"], plate_removal_index=4)

    def test_empty_route_rejected(self):
        with self.assertRaises(ValueError):
            check_sequence([])


class FurnaceSurveyTests(unittest.TestCase):
    def test_current_survey_accepts(self):
        result = furnace_survey_status(100.0, 365.0, 3, 3)
        self.assertEqual(result["verdict"], VERDICT_ACCEPT)

    def test_survey_exactly_at_the_interval_still_accepts_as_a_review(self):
        result = furnace_survey_status(365.0, 365.0, 3, 3)
        self.assertEqual(result["verdict"], VERDICT_REVIEW)

    def test_lapsed_survey_rejects(self):
        result = furnace_survey_status(400.0, 365.0, 3, 3)
        self.assertEqual(result["verdict"], VERDICT_REJECT)

    def test_survey_close_to_lapsing_is_a_review(self):
        result = furnace_survey_status(340.0, 365.0, 3, 3)
        self.assertEqual(result["verdict"], VERDICT_REVIEW)

    def test_too_few_load_thermocouples_rejects(self):
        result = furnace_survey_status(10.0, 365.0, 1, 3)
        self.assertEqual(result["verdict"], VERDICT_REJECT)

    def test_non_integer_thermocouple_count_rejected(self):
        with self.assertRaises(ValueError):
            furnace_survey_status(10.0, 365.0, 2.5, 3)


class AssessHeatTreatmentTests(unittest.TestCase):
    def test_compliant_route_accepts_with_no_findings(self):
        result = assess_heat_treatment(_case())
        self.assertEqual(result["verdict"], VERDICT_ACCEPT)
        self.assertEqual(result["findings"], [])
        self.assertEqual(result["driving_steps"], [])

    def test_step_without_a_declared_recipe_rejected(self):
        case = _case()
        case["requirements"] = {"solution": RELIEF_REQUIREMENT}
        with self.assertRaises(ValueError):
            assess_heat_treatment(case)

    def test_driving_step_is_named(self):
        case = _case()
        case["steps"][0]["traces"] = [make_trace(300.0, 30.0)]
        result = assess_heat_treatment(case)
        self.assertEqual(result["verdict"], VERDICT_REJECT)
        self.assertIn("stress-relief", result["driving_steps"])

    def test_furnace_finding_reaches_the_top_level(self):
        result = assess_heat_treatment(_case(days_since_survey=500.0))
        self.assertEqual(result["verdict"], VERDICT_REJECT)
        self.assertIn("furnace", result["driving_steps"])

    def test_sequence_finding_reaches_the_top_level(self):
        result = assess_heat_treatment(_case(plate_removal_index=0))
        self.assertEqual(result["verdict"], VERDICT_REJECT)
        self.assertIn("sequence", result["driving_steps"])

    def test_non_mapping_case_rejected(self):
        with self.assertRaises(ValueError):
            assess_heat_treatment(["stress-relief"])

    def test_empty_step_list_rejected(self):
        with self.assertRaises(ValueError):
            assess_heat_treatment(_case(steps=[]))


if __name__ == "__main__":
    unittest.main()
