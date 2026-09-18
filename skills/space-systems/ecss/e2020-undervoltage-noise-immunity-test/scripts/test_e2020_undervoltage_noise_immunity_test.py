"""Contract tests for the clause 5.4.3.4.1 undervoltage noise immunity logic."""

import unittest

from e2020_undervoltage_noise_immunity_test_logic import (
    DEFAULT_AMPLITUDE_FACTOR,
    DEFAULT_DWELL_FACTOR,
    MIN_REPETITIONS,
    amplitude_headroom_v,
    assess_noise_immunity_test,
    grade_runs,
    required_dwell_s,
    required_step_amplitude_v,
    slew_rate_v_per_s,
    step_levels,
    validate_noise,
    validate_stimulus,
    validate_threshold,
)

# A twenty-eight volt operating point tripping at twenty-four, with half a
# volt of sensing uncertainty: the trip band starts at 24.5 V and the step has
# 3.5 V of headroom above it.
THRESHOLD = {"trip_threshold_v": 24.0, "sensing_uncertainty_v": 0.5}

NOISE = {
    "noise_envelope_v": 1.0,
    "ripple_peak_to_peak_v": 0.4,
    "disturbance_slew_v_per_s": 100000.0,
}

STIMULUS = {
    "start_voltage_v": 28.0,
    "step_amplitude_v": 3.0,
    "edge_time_s": 1e-5,
    "dwell_s": 0.010,
    "repetitions": 5,
}

RUNS = [{"run": "r%d" % i, "tripped": False} for i in range(1, 6)]


def spec(threshold=None, noise=None, runs=None, response_s=0.002, **stim):
    stimulus = dict(STIMULUS)
    stimulus.update(stim)
    out = {
        "threshold": dict(threshold if threshold is not None else THRESHOLD),
        "noise": dict(noise if noise is not None else NOISE),
        "stimulus": stimulus,
        "detector_response_time_s": response_s,
    }
    if runs is not None:
        out["runs"] = [dict(r) for r in runs]
    return out


class ValidationTests(unittest.TestCase):
    def test_non_mapping_threshold_rejected(self):
        with self.assertRaises(ValueError):
            validate_threshold([24.0])

    def test_missing_threshold_key_rejected(self):
        with self.assertRaises(ValueError):
            validate_threshold({"trip_threshold_v": 24.0})

    def test_negative_sensing_uncertainty_rejected(self):
        with self.assertRaises(ValueError):
            validate_threshold(dict(THRESHOLD, sensing_uncertainty_v=-0.2))

    def test_missing_noise_key_rejected(self):
        partial = dict(NOISE)
        del partial["disturbance_slew_v_per_s"]
        with self.assertRaises(ValueError):
            validate_noise(partial)

    def test_zero_disturbance_slew_rejected(self):
        with self.assertRaises(ValueError):
            validate_noise(dict(NOISE, disturbance_slew_v_per_s=0.0))

    def test_missing_stimulus_key_rejected(self):
        partial = dict(STIMULUS)
        del partial["dwell_s"]
        with self.assertRaises(ValueError):
            validate_stimulus(partial)

    def test_zero_dwell_rejected(self):
        with self.assertRaises(ValueError):
            validate_stimulus(dict(STIMULUS, dwell_s=0.0))

    def test_non_integer_repetitions_rejected(self):
        with self.assertRaises(ValueError):
            validate_stimulus(dict(STIMULUS, repetitions=4.5))

    def test_boolean_repetitions_rejected(self):
        with self.assertRaises(ValueError):
            validate_stimulus(dict(STIMULUS, repetitions=True))

    def test_a_step_that_reaches_zero_volts_rejected(self):
        with self.assertRaises(ValueError):
            validate_stimulus(dict(STIMULUS, step_amplitude_v=28.0))

    def test_runs_must_be_a_sequence(self):
        with self.assertRaises(ValueError):
            grade_runs({"run": "r1", "tripped": False})

    def test_run_with_a_non_boolean_result_rejected(self):
        with self.assertRaises(ValueError):
            grade_runs([{"run": "r1", "tripped": "no"}])

    def test_duplicate_run_name_rejected(self):
        with self.assertRaises(ValueError):
            grade_runs([{"run": "r1", "tripped": False}, {"run": "r1", "tripped": False}])

    def test_missing_top_level_key_rejected(self):
        bad = spec()
        del bad["detector_response_time_s"]
        with self.assertRaises(ValueError):
            assess_noise_immunity_test(bad)


class ArithmeticTests(unittest.TestCase):
    def test_required_amplitude_takes_half_the_peak_to_peak_ripple(self):
        needed = required_step_amplitude_v(validate_noise(NOISE))
        self.assertAlmostEqual(needed, 2.4, places=9)

    def test_amplitude_factor_scales_the_requirement(self):
        needed = required_step_amplitude_v(validate_noise(NOISE), 3.0)
        self.assertAlmostEqual(needed, 3.6, places=9)

    def test_step_levels_are_the_start_and_the_start_less_the_amplitude(self):
        upper, lower = step_levels(28.0, 3.0)
        self.assertAlmostEqual(upper, 28.0, places=9)
        self.assertAlmostEqual(lower, 25.0, places=9)

    def test_headroom_sits_above_the_trip_band_not_the_threshold(self):
        self.assertAlmostEqual(amplitude_headroom_v(28.0, 24.0, 0.5), 3.5, places=9)

    def test_slew_rate_is_the_amplitude_over_the_edge_time(self):
        self.assertAlmostEqual(slew_rate_v_per_s(3.0, 1e-5), 300000.0, places=3)

    def test_required_dwell_outlasts_the_detection_chain(self):
        self.assertAlmostEqual(required_dwell_s(0.002), 0.003, places=9)

    def test_declared_constants(self):
        self.assertAlmostEqual(DEFAULT_AMPLITUDE_FACTOR, 2.0, places=9)
        self.assertAlmostEqual(DEFAULT_DWELL_FACTOR, 1.5, places=9)
        self.assertEqual(MIN_REPETITIONS, 3)

    def test_grade_runs_counts_and_names_the_trips(self):
        count, tripped = grade_runs(
            [{"run": "r1", "tripped": False}, {"run": "r2", "tripped": True}]
        )
        self.assertEqual(count, 2)
        self.assertEqual(tripped, ["r2"])


class AssessmentTests(unittest.TestCase):
    def test_nominal_specification_and_runs_are_compliant(self):
        result = assess_noise_immunity_test(spec(runs=RUNS))
        self.assertEqual(result["verdict"], "compliant")
        self.assertEqual(result["findings"], [])
        self.assertTrue(result["immunity_demonstrated"])

    def test_a_step_landing_exactly_on_the_trip_band_still_clears_it(self):
        result = assess_noise_immunity_test(spec(step_amplitude_v=3.5))
        self.assertAlmostEqual(result["lower_level_v"], result["trip_band_v"], places=9)
        self.assertTrue(result["clears_trip_band"])

    def test_a_step_into_the_trip_band_is_a_genuine_undervoltage(self):
        result = assess_noise_immunity_test(spec(step_amplitude_v=4.0, runs=RUNS))
        self.assertFalse(result["clears_trip_band"])
        self.assertEqual(result["verdict"], "non-compliant")
        self.assertEqual(len(result["findings"]), 1)
        self.assertIn("not a noise one", result["findings"][0])

    def test_an_understressed_step_is_reported(self):
        result = assess_noise_immunity_test(spec(step_amplitude_v=1.5, runs=RUNS))
        self.assertFalse(result["amplitude_sufficient"])
        self.assertEqual(result["verdict"], "non-compliant")
        self.assertIn("disturbance envelope", " | ".join(result["findings"]))

    def test_an_envelope_beyond_the_headroom_names_the_threshold_placement(self):
        noisy = dict(NOISE, noise_envelope_v=2.0)
        result = assess_noise_immunity_test(spec(noise=noisy, runs=RUNS))
        self.assertFalse(result["demonstrable"])
        self.assertAlmostEqual(result["required_amplitude_v"], 4.4, places=9)
        self.assertAlmostEqual(result["amplitude_headroom_v"], 3.5, places=9)
        self.assertIn(
            "too close to the operating point", " | ".join(result["findings"])
        )

    def test_a_dwell_shorter_than_the_detection_chain_is_reported(self):
        result = assess_noise_immunity_test(spec(dwell_s=0.001, runs=RUNS))
        self.assertFalse(result["dwell_sufficient"])
        self.assertAlmostEqual(result["required_dwell_s"], 0.003, places=9)
        self.assertIn("still settling", " | ".join(result["findings"]))

    def test_a_dwell_exactly_on_the_required_value_is_sufficient(self):
        needed = required_dwell_s(0.002)
        result = assess_noise_immunity_test(spec(dwell_s=needed, runs=RUNS))
        self.assertAlmostEqual(result["required_dwell_s"], needed, places=9)
        self.assertTrue(result["dwell_sufficient"])
        self.assertEqual(result["verdict"], "compliant")

    def test_a_slow_edge_is_reported(self):
        result = assess_noise_immunity_test(spec(edge_time_s=1e-3, runs=RUNS))
        self.assertFalse(result["edge_sufficient"])
        self.assertIn("gentler event", " | ".join(result["findings"]))

    def test_an_edge_exactly_at_the_disturbance_rate_is_sufficient(self):
        result = assess_noise_immunity_test(spec(edge_time_s=3.0 / 100000.0, runs=RUNS))
        self.assertAlmostEqual(result["slew_rate_v_per_s"], 100000.0, places=3)
        self.assertTrue(result["edge_sufficient"])

    def test_a_single_application_is_not_a_demonstration(self):
        result = assess_noise_immunity_test(
            spec(repetitions=1, runs=[{"run": "r1", "tripped": False}])
        )
        self.assertFalse(result["repeated_enough"])
        self.assertIn("repeated result", " | ".join(result["findings"]))

    def test_one_tripped_run_fails_the_demonstration(self):
        runs = [dict(r) for r in RUNS]
        runs[2]["tripped"] = True
        result = assess_noise_immunity_test(spec(runs=runs))
        self.assertTrue(result["design_sound"])
        self.assertFalse(result["immunity_demonstrated"])
        self.assertEqual(result["tripped_runs"], ["r3"])
        self.assertIn("reacting to noise", " | ".join(result["findings"]))

    def test_fewer_runs_than_declared_applications_is_reported(self):
        result = assess_noise_immunity_test(spec(runs=RUNS[:2]))
        self.assertEqual(result["run_count"], 2)
        self.assertFalse(result["immunity_demonstrated"])
        self.assertIn("declared applications", " | ".join(result["findings"]))

    def test_a_specification_without_runs_grades_the_design_only(self):
        result = assess_noise_immunity_test(spec())
        self.assertFalse(result["runs_graded"])
        self.assertTrue(result["design_sound"])
        self.assertFalse(result["immunity_demonstrated"])
        self.assertEqual(result["verdict"], "compliant")

    def test_a_start_level_already_inside_the_trip_band_is_reported(self):
        low_start = spec(start_voltage_v=24.2, step_amplitude_v=1.0)
        result = assess_noise_immunity_test(low_start)
        self.assertFalse(result["clears_trip_band"])
        self.assertIn("already inside", " | ".join(result["findings"]))

    def test_every_finding_is_a_non_empty_string(self):
        result = assess_noise_immunity_test(spec(step_amplitude_v=1.5, runs=RUNS))
        self.assertTrue(result["findings"])
        for finding in result["findings"]:
            self.assertIsInstance(finding, str)
            self.assertTrue(finding.strip())


if __name__ == "__main__":
    unittest.main()
