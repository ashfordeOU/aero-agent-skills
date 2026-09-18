"""Contract tests for the clause 5.4.14.4 contact discharge procedure logic."""

import unittest

from e2007_contact_discharge_test_procedure_logic import (
    CALIBRATION_OMITTED,
    CALIBRATION_OUT_OF_TOLERANCE,
    CALIBRATION_PASSED,
    DEFAULT_CALIBRATION_VALIDITY_H,
    MIN_DISCHARGES_PER_POINT,
    MIN_INTERVAL_S,
    OUT_OF_TOLERANCE,
    STEP_APPLY,
    STEP_CALIBRATE,
    STEP_RECOVER,
    STEP_STABILISE,
    VERDICT_CONFORMING,
    VERDICT_NONCONFORMING,
    VERDICT_WITH_LIMITATIONS,
    WITHIN_TOLERANCE,
    assess_contact_discharge_procedure,
    bench_time_s,
    build_application_plan,
    categorize_amplitude,
    effective_interval_s,
    grade_calibration,
    nominal_waveform,
    normalize_polarity,
    relative_deviation,
    resolve_coefficients,
    resolve_tolerances,
    rise_time_is_admissible,
    total_discharges,
    validate_levels,
    validate_points,
    validate_polarities,
    validate_rise_time_band,
    validate_run,
)


def make_calibration(**overrides):
    """Return a well-formed measured waveform calibration at four kilovolts."""
    calibration = {
        "state": "measured",
        "level_kv": 4.0,
        "measured_first_peak_a": 15.0,
        "measured_current_at_30ns_a": 8.0,
        "measured_current_at_60ns_a": 4.0,
        "measured_rise_time_s": 0.8e-9,
        "age_h": 2.0,
    }
    calibration.update(overrides)
    return calibration


def make_run(**overrides):
    """Return a well-formed two-point, two-polarity, four-level run."""
    run = {
        "stabilisation_dwell_s": 900.0,
        "required_stabilisation_s": 600.0,
        "declared_interval_s": 2.0,
        "generator_recharge_s": 1.5,
        "discharges_per_point": 10,
        "per_point_overhead_s": 30.0,
        "unit_monitored": True,
        "discharge_points": ["chassis-face-A", "connector-shell-J3"],
        "polarities": ["positive", "negative"],
        "levels_kv": [2.0, 4.0, 6.0, 8.0],
    }
    run.update(overrides)
    return run


class PolarityTests(unittest.TestCase):
    def test_polarity_synonyms_collapse(self):
        self.assertEqual(normalize_polarity("+"), "positive")
        self.assertEqual(normalize_polarity(" NEG "), "negative")

    def test_unknown_polarity_rejected(self):
        with self.assertRaises(ValueError):
            normalize_polarity("alternating")

    def test_non_string_polarity_rejected(self):
        with self.assertRaises(ValueError):
            normalize_polarity(1)

    def test_duplicate_polarity_rejected(self):
        with self.assertRaises(ValueError):
            validate_polarities(["positive", "+"])

    def test_empty_polarity_set_rejected(self):
        with self.assertRaises(ValueError):
            validate_polarities([])


class WaveformTargetTests(unittest.TestCase):
    def test_nominal_target_scales_with_the_level(self):
        target = nominal_waveform(4.0)
        self.assertAlmostEqual(target["first_peak_a"], 15.0, places=9)
        self.assertAlmostEqual(target["current_at_30ns_a"], 8.0, places=9)
        self.assertAlmostEqual(target["current_at_60ns_a"], 4.0, places=9)

    def test_target_is_linear_in_the_level(self):
        low = nominal_waveform(2.0)
        high = nominal_waveform(8.0)
        self.assertAlmostEqual(
            high["first_peak_a"] / low["first_peak_a"], 4.0, places=9
        )

    def test_zero_level_rejected(self):
        with self.assertRaises(ValueError):
            nominal_waveform(0.0)

    def test_custom_coefficients_are_honoured(self):
        target = nominal_waveform(
            4.0,
            {
                "first_peak_a_per_kv": 4.0,
                "current_at_30ns_a_per_kv": 2.0,
                "current_at_60ns_a_per_kv": 1.0,
            },
        )
        self.assertAlmostEqual(target["first_peak_a"], 16.0, places=9)

    def test_unknown_coefficient_key_rejected(self):
        with self.assertRaises(ValueError):
            resolve_coefficients(
                {
                    "first_peak_a_per_kv": 3.75,
                    "current_at_30ns_a_per_kv": 2.0,
                    "current_at_60ns_a_per_kv": 1.0,
                    "current_at_90ns_a_per_kv": 0.5,
                }
            )

    def test_negative_coefficient_rejected(self):
        with self.assertRaises(ValueError):
            resolve_coefficients(
                {
                    "first_peak_a_per_kv": -3.75,
                    "current_at_30ns_a_per_kv": 2.0,
                    "current_at_60ns_a_per_kv": 1.0,
                }
            )

    def test_tolerance_outside_the_unit_interval_rejected(self):
        with self.assertRaises(ValueError):
            resolve_tolerances(
                {
                    "first_peak_a": 1.5,
                    "current_at_30ns_a": 0.3,
                    "current_at_60ns_a": 0.3,
                }
            )


class AmplitudeGradingTests(unittest.TestCase):
    def test_exact_reading_is_within_tolerance(self):
        self.assertEqual(categorize_amplitude(15.0, 15.0, 0.15), WITHIN_TOLERANCE)

    def test_reading_exactly_on_the_tolerance_is_within(self):
        self.assertEqual(categorize_amplitude(17.25, 15.0, 0.15), WITHIN_TOLERANCE)

    def test_reading_past_the_tolerance_is_out(self):
        self.assertEqual(categorize_amplitude(18.0, 15.0, 0.15), OUT_OF_TOLERANCE)

    def test_deviation_sign_follows_the_reading(self):
        self.assertAlmostEqual(relative_deviation(18.0, 15.0), 0.2, places=9)
        self.assertAlmostEqual(relative_deviation(12.0, 15.0), -0.2, places=9)

    def test_negative_reading_rejected(self):
        with self.assertRaises(ValueError):
            relative_deviation(-1.0, 15.0)

    def test_zero_nominal_rejected(self):
        with self.assertRaises(ValueError):
            relative_deviation(15.0, 0.0)


class RiseTimeTests(unittest.TestCase):
    def test_edge_inside_the_band_is_admissible(self):
        self.assertTrue(rise_time_is_admissible(0.8e-9))

    def test_edge_exactly_on_the_lower_edge_is_admissible(self):
        self.assertTrue(rise_time_is_admissible(0.6e-9))

    def test_slow_edge_is_not_admissible(self):
        self.assertFalse(rise_time_is_admissible(2.0e-9))

    def test_inverted_rise_time_band_rejected(self):
        with self.assertRaises(ValueError):
            validate_rise_time_band((1.0e-9, 0.6e-9))

    def test_zero_rise_time_rejected(self):
        with self.assertRaises(ValueError):
            rise_time_is_admissible(0.0)


class CalibrationGradingTests(unittest.TestCase):
    def test_clean_calibration_passes(self):
        graded = grade_calibration(make_calibration())
        self.assertEqual(graded["state"], CALIBRATION_PASSED)
        self.assertEqual(graded["findings"], [])

    def test_omitted_calibration_is_a_limitation_not_a_finding(self):
        graded = grade_calibration({"state": "omitted"})
        self.assertEqual(graded["state"], CALIBRATION_OMITTED)
        self.assertEqual(graded["findings"], [])
        self.assertEqual(len(graded["limitations"]), 1)

    def test_peak_out_of_tolerance_is_a_finding(self):
        graded = grade_calibration(make_calibration(measured_first_peak_a=20.0))
        self.assertEqual(graded["state"], CALIBRATION_OUT_OF_TOLERANCE)
        self.assertTrue(any("first peak" in f for f in graded["findings"]))

    def test_slow_edge_is_a_finding(self):
        graded = grade_calibration(make_calibration(measured_rise_time_s=3.0e-9))
        self.assertFalse(graded["rise_time_admissible"])
        self.assertEqual(graded["state"], CALIBRATION_OUT_OF_TOLERANCE)

    def test_expired_calibration_is_a_finding(self):
        graded = grade_calibration(
            make_calibration(age_h=DEFAULT_CALIBRATION_VALIDITY_H + 10.0)
        )
        self.assertTrue(graded["expired"])
        self.assertTrue(any("validity window" in f for f in graded["findings"]))

    def test_calibration_exactly_at_the_validity_limit_is_not_expired(self):
        graded = grade_calibration(
            make_calibration(age_h=DEFAULT_CALIBRATION_VALIDITY_H)
        )
        self.assertFalse(graded["expired"])

    def test_unknown_calibration_state_rejected(self):
        with self.assertRaises(ValueError):
            grade_calibration({"state": "probably-fine"})

    def test_missing_reading_rejected(self):
        calibration = make_calibration()
        del calibration["measured_current_at_30ns_a"]
        with self.assertRaises(ValueError):
            grade_calibration(calibration)

    def test_negative_age_rejected(self):
        with self.assertRaises(ValueError):
            grade_calibration(make_calibration(age_h=-1.0))


class IntervalTests(unittest.TestCase):
    def test_declared_interval_wins_when_it_is_slowest(self):
        self.assertAlmostEqual(effective_interval_s(5.0, 1.5), 5.0, places=9)

    def test_recharge_time_wins_when_it_is_slowest(self):
        self.assertAlmostEqual(effective_interval_s(1.2, 3.0), 3.0, places=9)

    def test_floor_wins_when_both_are_fast(self):
        self.assertAlmostEqual(effective_interval_s(0.2, 0.3), MIN_INTERVAL_S, places=9)

    def test_zero_recharge_rejected(self):
        with self.assertRaises(ValueError):
            effective_interval_s(2.0, 0.0)


class RunValidationTests(unittest.TestCase):
    def test_well_formed_run_normalizes(self):
        record = validate_run(make_run())
        self.assertEqual(record["discharges_per_point"], 10)
        self.assertEqual(record["polarities"], ["negative", "positive"])

    def test_descending_levels_rejected(self):
        with self.assertRaises(ValueError):
            validate_levels([8.0, 6.0, 4.0])

    def test_repeated_level_rejected(self):
        with self.assertRaises(ValueError):
            validate_levels([2.0, 2.0])

    def test_duplicate_point_rejected(self):
        with self.assertRaises(ValueError):
            validate_points(["chassis-face-A", "chassis-face-A"])

    def test_blank_point_label_rejected(self):
        with self.assertRaises(ValueError):
            validate_points(["  "])

    def test_fractional_discharge_count_rejected(self):
        with self.assertRaises(ValueError):
            validate_run(make_run(discharges_per_point=10.5))

    def test_boolean_dwell_rejected(self):
        with self.assertRaises(ValueError):
            validate_run(make_run(stabilisation_dwell_s=True))

    def test_negative_overhead_rejected(self):
        with self.assertRaises(ValueError):
            validate_run(make_run(per_point_overhead_s=-1.0))

    def test_non_boolean_monitoring_flag_rejected(self):
        with self.assertRaises(ValueError):
            validate_run(make_run(unit_monitored="watched"))


class PlanTests(unittest.TestCase):
    def test_plan_opens_with_stabilise_and_closes_with_recover(self):
        plan = build_application_plan(make_run())
        self.assertEqual(plan[0]["step"], STEP_STABILISE)
        self.assertEqual(plan[-1]["step"], STEP_RECOVER)

    def test_plan_carries_a_calibrate_step_when_it_was_measured(self):
        plan = build_application_plan(make_run(), CALIBRATION_PASSED)
        self.assertEqual(plan[1]["step"], STEP_CALIBRATE)

    def test_plan_drops_the_calibrate_step_when_it_was_omitted(self):
        plan = build_application_plan(make_run(), CALIBRATION_OMITTED)
        self.assertNotIn(STEP_CALIBRATE, [s["step"] for s in plan])

    def test_application_steps_ascend_in_level(self):
        plan = build_application_plan(make_run())
        levels = [s["level_kv"] for s in plan if s["step"] == STEP_APPLY]
        self.assertEqual(levels, sorted(levels))

    def test_every_point_and_polarity_appears_at_every_level(self):
        plan = build_application_plan(make_run())
        applied = [s for s in plan if s["step"] == STEP_APPLY]
        self.assertEqual(len(applied), 2 * 2 * 4)

    def test_unknown_calibration_state_rejected_by_the_plan(self):
        with self.assertRaises(ValueError):
            build_application_plan(make_run(), "maybe")

    def test_total_discharges_is_the_product(self):
        self.assertEqual(total_discharges(make_run()), 2 * 2 * 4 * 10)

    def test_bench_time_covers_dwell_events_and_overheads(self):
        run = make_run()
        expected = 900.0 + 160 * 2.0 + 16 * 30.0
        self.assertAlmostEqual(bench_time_s(run, 2.0), expected, places=6)

    def test_zero_interval_rejected_by_bench_time(self):
        with self.assertRaises(ValueError):
            bench_time_s(make_run(), 0.0)


class AssessmentTests(unittest.TestCase):
    def test_clean_run_is_conforming(self):
        result = assess_contact_discharge_procedure(make_run(), make_calibration())
        self.assertEqual(result["verdict"], VERDICT_CONFORMING)
        self.assertEqual(result["findings"], [])

    def test_short_dwell_is_a_finding(self):
        result = assess_contact_discharge_procedure(
            make_run(stabilisation_dwell_s=60.0), make_calibration()
        )
        self.assertFalse(result["stabilisation_is_adequate"])
        self.assertEqual(result["verdict"], VERDICT_NONCONFORMING)

    def test_short_interval_is_stretched_to_the_recharge_time(self):
        result = assess_contact_discharge_procedure(
            make_run(declared_interval_s=0.2), make_calibration()
        )
        self.assertTrue(result["interval_was_stretched"])
        self.assertAlmostEqual(result["effective_interval_s"], 1.5, places=9)

    def test_interval_falls_back_to_the_floor_when_both_are_fast(self):
        result = assess_contact_discharge_procedure(
            make_run(declared_interval_s=0.2, generator_recharge_s=0.3),
            make_calibration(),
        )
        self.assertTrue(result["interval_was_stretched"])
        self.assertAlmostEqual(result["effective_interval_s"], MIN_INTERVAL_S, places=9)

    def test_too_few_discharges_is_a_finding(self):
        result = assess_contact_discharge_procedure(
            make_run(discharges_per_point=MIN_DISCHARGES_PER_POINT - 1),
            make_calibration(),
        )
        self.assertFalse(result["discharges_per_point_is_adequate"])
        self.assertEqual(result["verdict"], VERDICT_NONCONFORMING)

    def test_unwatched_unit_is_a_finding(self):
        result = assess_contact_discharge_procedure(
            make_run(unit_monitored=False), make_calibration()
        )
        self.assertTrue(any("not watched" in f for f in result["findings"]))

    def test_single_polarity_is_a_limitation(self):
        result = assess_contact_discharge_procedure(
            make_run(polarities=["positive"]), make_calibration()
        )
        self.assertEqual(result["verdict"], VERDICT_WITH_LIMITATIONS)
        self.assertTrue(any("half of the exposure" in n for n in result["limitations"]))

    def test_omitted_calibration_is_a_limitation_not_a_failure(self):
        result = assess_contact_discharge_procedure(
            make_run(), {"state": "omitted"}
        )
        self.assertEqual(result["verdict"], VERDICT_WITH_LIMITATIONS)
        self.assertEqual(result["calibration"]["state"], CALIBRATION_OMITTED)

    def test_out_of_tolerance_calibration_fails_the_run(self):
        result = assess_contact_discharge_procedure(
            make_run(), make_calibration(measured_first_peak_a=25.0)
        )
        self.assertEqual(result["verdict"], VERDICT_NONCONFORMING)

    def test_bench_time_uses_the_effective_interval(self):
        result = assess_contact_discharge_procedure(
            make_run(declared_interval_s=0.2), make_calibration()
        )
        expected = 900.0 + 160 * 1.5 + 16 * 30.0
        self.assertAlmostEqual(result["bench_time_s"], expected, places=6)

    def test_total_discharges_is_reported(self):
        result = assess_contact_discharge_procedure(make_run(), make_calibration())
        self.assertEqual(result["total_discharges"], 160)

    def test_assessment_is_deterministic(self):
        first = assess_contact_discharge_procedure(make_run(), make_calibration())
        second = assess_contact_discharge_procedure(make_run(), make_calibration())
        self.assertEqual(first["verdict"], second["verdict"])
        self.assertEqual(first["findings"], second["findings"])
        self.assertEqual(first["bench_time_s"], second["bench_time_s"])


if __name__ == "__main__":
    unittest.main(verbosity=2)
