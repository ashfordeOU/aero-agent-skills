#!/usr/bin/env python3
"""Gate 3 contract test for e2007-cable-injection-susceptibility-procedure.

stdlib unittest, offline, deterministic. Run:
    python3 test_e2007_cable_injection_susceptibility_procedure.py
"""

import unittest

from e2007_cable_injection_susceptibility_procedure_logic import (
    HARNESS_BUNDLE_OVERALL,
    HARNESS_CATEGORIES,
    HARNESS_POWER_PRIMARY,
    STEP_AT_REQUIRED_LEVEL,
    STEP_IMMUNE,
    STEP_LEVEL_NOT_REACHED,
    STEP_SUSCEPTIBLE,
    VERDICT_RUN_INVALID,
    VERDICT_RUN_VALID,
    WARM_UP_AT_BOUND,
    WARM_UP_SETTLED,
    WARM_UP_SHORT,
    achievable_current_a,
    assess_cable_injection_procedure,
    assess_warm_up,
    at_least,
    dwell_time_s,
    forward_power_w,
    grade_step,
    normalize_harness_category,
    plan_step_drive,
    run_duration_s,
    step_count,
    step_frequencies_hz,
)


def procedure(**over):
    record = {
        "harness_category": HARNESS_POWER_PRIMARY,
        "warm_up_s": 900.0,
        "response_time_s": 0.4,
        "monitor_interval_s": 0.05,
        "minimum_dwell_s": 0.2,
        "samples_per_dwell": 3,
        "dwell_s": 1.0,
        "settle_s": 0.1,
        "power_limit_w": 400.0,
        "modulation_states": 2,
        "indications": {},
    }
    record.update(over)
    return record


def spec(**over):
    record = {
        "start_hz": 1.0e5,
        "stop_hz": 4.0e5,
        "step_fraction": 0.5,
        "required_current_a": 0.2,
        "calibration_a_per_sqrt_w": 0.02,
        "required_warm_up_s": 600.0,
    }
    record.update(over)
    return record


class TestHarnessCategory(unittest.TestCase):
    def test_every_category_normalizes(self):
        for category in HARNESS_CATEGORIES:
            self.assertEqual(normalize_harness_category(category.upper()), category)

    def test_whitespace_is_trimmed(self):
        self.assertEqual(
            normalize_harness_category("  bundle-overall "), HARNESS_BUNDLE_OVERALL
        )

    def test_unrecognized_category_rejected(self):
        with self.assertRaises(ValueError):
            normalize_harness_category("fibre-optic")

    def test_non_string_category_rejected(self):
        with self.assertRaises(ValueError):
            normalize_harness_category(7)


class TestStepFrequencies(unittest.TestCase):
    def test_first_step_is_the_bottom_of_the_range(self):
        steps = step_frequencies_hz(1.0e5, 4.0e5, 0.5)
        self.assertAlmostEqual(steps[0], 1.0e5, places=6)

    def test_last_step_is_exactly_the_top_of_the_range(self):
        steps = step_frequencies_hz(1.0e5, 4.0e5, 0.5)
        self.assertEqual(steps[-1], 4.0e5)

    def test_increment_is_the_permitted_fraction_of_the_lower_frequency(self):
        steps = step_frequencies_hz(1.0e5, 4.0e5, 0.5)
        self.assertAlmostEqual(steps[1] / steps[0], 1.5, places=9)

    def test_steps_advance_monotonically(self):
        steps = step_frequencies_hz(1.0e4, 1.0e8, 0.1)
        for lower, upper in zip(steps, steps[1:]):
            self.assertLess(lower, upper)

    def test_a_finer_fraction_gives_more_steps(self):
        coarse = step_count(1.0e5, 1.0e6, 0.5)
        fine = step_count(1.0e5, 1.0e6, 0.05)
        self.assertGreater(fine, coarse)

    def test_inverted_range_rejected(self):
        with self.assertRaises(ValueError):
            step_frequencies_hz(4.0e5, 1.0e5, 0.5)

    def test_zero_fraction_rejected(self):
        with self.assertRaises(ValueError):
            step_frequencies_hz(1.0e5, 4.0e5, 0.0)

    def test_fraction_above_one_rejected(self):
        with self.assertRaises(ValueError):
            step_frequencies_hz(1.0e5, 4.0e5, 1.5)

    def test_non_positive_start_rejected(self):
        with self.assertRaises(ValueError):
            step_frequencies_hz(0.0, 4.0e5, 0.5)


class TestDwellTime(unittest.TestCase):
    def test_response_time_governs_when_it_is_the_longest(self):
        self.assertAlmostEqual(dwell_time_s(0.9, 0.05, 0.2, 3), 0.9, places=9)

    def test_monitor_sampling_governs_when_it_is_the_longest(self):
        self.assertAlmostEqual(dwell_time_s(0.1, 0.2, 0.05, 3), 0.6, places=9)

    def test_declared_floor_governs_when_it_is_the_longest(self):
        self.assertAlmostEqual(dwell_time_s(0.1, 0.02, 2.0, 3), 2.0, places=9)

    def test_zero_monitor_interval_rejected(self):
        with self.assertRaises(ValueError):
            dwell_time_s(0.1, 0.0, 0.2, 3)

    def test_fractional_sample_count_rejected(self):
        with self.assertRaises(ValueError):
            dwell_time_s(0.1, 0.05, 0.2, 2.5)

    def test_negative_response_time_rejected(self):
        with self.assertRaises(ValueError):
            dwell_time_s(-0.1, 0.05, 0.2, 3)


class TestWarmUp(unittest.TestCase):
    def test_generous_warm_up_is_settled(self):
        self.assertEqual(assess_warm_up(1200.0, 600.0)["grade"], WARM_UP_SETTLED)

    def test_warm_up_on_the_bound_is_carried_as_such(self):
        self.assertEqual(assess_warm_up(600.0, 600.0)["grade"], WARM_UP_AT_BOUND)

    def test_short_warm_up_is_graded_short(self):
        result = assess_warm_up(300.0, 600.0)
        self.assertEqual(result["grade"], WARM_UP_SHORT)
        self.assertAlmostEqual(result["shortfall_s"], 300.0, places=9)

    def test_settled_warm_up_reports_no_shortfall(self):
        self.assertAlmostEqual(assess_warm_up(900.0, 600.0)["shortfall_s"], 0.0, places=9)

    def test_non_positive_requirement_rejected(self):
        with self.assertRaises(ValueError):
            assess_warm_up(900.0, 0.0)


class TestDrive(unittest.TestCase):
    def test_forward_power_follows_the_square_of_the_current(self):
        self.assertAlmostEqual(forward_power_w(0.2, 0.02), 100.0, places=9)

    def test_achievable_current_inverts_the_calibration(self):
        self.assertAlmostEqual(achievable_current_a(100.0, 0.02), 0.2, places=9)

    def test_power_and_current_round_trip(self):
        current = achievable_current_a(forward_power_w(0.35, 0.011), 0.011)
        self.assertAlmostEqual(current, 0.35, places=9)

    def test_ample_amplifier_delivers_the_required_level(self):
        plan = plan_step_drive(0.2, 0.02, 400.0)
        self.assertTrue(plan["level_reached"])
        self.assertAlmostEqual(plan["delivered_current_a"], 0.2, places=9)

    def test_amplifier_exactly_on_the_requirement_still_delivers(self):
        plan = plan_step_drive(0.2, 0.02, 100.0)
        self.assertTrue(plan["level_reached"])
        self.assertAlmostEqual(plan["shortfall_a"], 0.0, places=9)

    def test_short_amplifier_caps_the_delivered_current(self):
        plan = plan_step_drive(0.2, 0.02, 25.0)
        self.assertFalse(plan["level_reached"])
        self.assertAlmostEqual(plan["delivered_current_a"], 0.1, places=9)
        self.assertAlmostEqual(plan["shortfall_a"], 0.1, places=9)

    def test_zero_calibration_rejected(self):
        with self.assertRaises(ValueError):
            plan_step_drive(0.2, 0.0, 400.0)

    def test_negative_power_limit_rejected(self):
        with self.assertRaises(ValueError):
            plan_step_drive(0.2, 0.02, -1.0)


class TestStepGrading(unittest.TestCase):
    def test_quiet_step_at_the_required_level_is_immune(self):
        self.assertEqual(grade_step(0.2, 0.2, None), STEP_IMMUNE)

    def test_quiet_step_under_the_required_level_proves_nothing(self):
        self.assertEqual(grade_step(0.2, 0.1, None), STEP_LEVEL_NOT_REACHED)

    def test_indication_well_under_the_required_level_is_susceptible(self):
        self.assertEqual(grade_step(0.2, 0.2, 0.12), STEP_SUSCEPTIBLE)

    def test_indication_on_the_required_level_is_carried_as_at_level(self):
        self.assertEqual(grade_step(0.2, 0.2, 0.2), STEP_AT_REQUIRED_LEVEL)

    def test_indication_above_what_was_delivered_rejected(self):
        with self.assertRaises(ValueError):
            grade_step(0.2, 0.2, 0.5)

    def test_at_level_fraction_outside_its_range_rejected(self):
        with self.assertRaises(ValueError):
            grade_step(0.2, 0.2, 0.2, at_level_fraction=1.0)


class TestRunDuration(unittest.TestCase):
    def test_duration_counts_every_modulation_state_at_every_step(self):
        self.assertAlmostEqual(run_duration_s(10, 1.0, 0.1, 2), 21.0, places=9)

    def test_settle_time_is_charged_once_per_step(self):
        self.assertAlmostEqual(run_duration_s(4, 2.0, 0.5, 1), 10.0, places=9)

    def test_fractional_step_count_rejected(self):
        with self.assertRaises(ValueError):
            run_duration_s(4.5, 2.0, 0.5, 1)

    def test_zero_modulation_states_rejected(self):
        with self.assertRaises(ValueError):
            run_duration_s(4, 2.0, 0.5, 0)


class TestAtLeast(unittest.TestCase):
    def test_value_on_the_floor_counts_as_reaching_it(self):
        self.assertTrue(at_least(0.2, 0.2))

    def test_value_a_hair_under_the_floor_is_absorbed(self):
        self.assertTrue(at_least(0.2 - 1e-12, 0.2))

    def test_value_clearly_under_the_floor_does_not_reach_it(self):
        self.assertFalse(at_least(0.19, 0.2))


class TestProcedureAssessment(unittest.TestCase):
    def test_clean_run_is_valid(self):
        report = assess_cable_injection_procedure(procedure(), spec())
        self.assertEqual(report["verdict"], VERDICT_RUN_VALID)
        self.assertEqual(report["findings"], [])

    def test_step_list_spans_the_declared_range(self):
        report = assess_cable_injection_procedure(procedure(), spec())
        self.assertAlmostEqual(report["frequencies_hz"][0], 1.0e5, places=6)
        self.assertEqual(report["frequencies_hz"][-1], 4.0e5)
        self.assertEqual(report["step_count"], len(report["frequencies_hz"]))

    def test_short_warm_up_invalidates_the_run(self):
        report = assess_cable_injection_procedure(
            procedure(warm_up_s=60.0), spec()
        )
        self.assertEqual(report["verdict"], VERDICT_RUN_INVALID)
        self.assertTrue(any("warm-up" in f for f in report["findings"]))

    def test_short_dwell_is_a_finding(self):
        report = assess_cable_injection_procedure(procedure(dwell_s=0.01), spec())
        self.assertFalse(report["dwell_ok"])
        self.assertTrue(any("dwell" in f for f in report["findings"]))

    def test_short_dwell_is_stretched_in_the_duration_budget(self):
        report = assess_cable_injection_procedure(procedure(dwell_s=0.01), spec())
        self.assertAlmostEqual(
            report["run_duration_s"],
            run_duration_s(report["step_count"], report["required_dwell_s"], 0.1, 2),
            places=9,
        )

    def test_limited_amplifier_leaves_every_step_ungraded(self):
        report = assess_cable_injection_procedure(
            procedure(power_limit_w=25.0), spec()
        )
        self.assertEqual(report["verdict"], VERDICT_RUN_INVALID)
        self.assertEqual(report["ungraded_steps"], report["step_count"])
        self.assertTrue(any("carry no immunity result" in l for l in report["limitations"]))

    def test_an_indication_under_the_level_names_a_governing_step(self):
        report = assess_cable_injection_procedure(
            procedure(indications={1: 0.09, 2: 0.15}), spec()
        )
        self.assertEqual(report["verdict"], VERDICT_RUN_INVALID)
        self.assertEqual(report["governing_step"]["step"], 1)
        self.assertAlmostEqual(
            report["governing_step"]["indication_current_a"], 0.09, places=9
        )

    def test_indication_on_the_level_is_a_limitation_not_a_finding(self):
        report = assess_cable_injection_procedure(
            procedure(indications={0: 0.2}), spec()
        )
        self.assertEqual(report["verdict"], VERDICT_RUN_VALID)
        self.assertTrue(any("sitting on the required level" in l for l in report["limitations"]))

    def test_quiet_run_has_no_governing_step(self):
        report = assess_cable_injection_procedure(procedure(), spec())
        self.assertIsNone(report["governing_step"])

    def test_every_step_carries_its_own_grade(self):
        report = assess_cable_injection_procedure(procedure(), spec())
        self.assertTrue(all(rec["grade"] == STEP_IMMUNE for rec in report["steps"]))

    def test_non_mapping_procedure_rejected(self):
        with self.assertRaises(ValueError):
            assess_cable_injection_procedure([], spec())

    def test_non_mapping_indications_rejected(self):
        with self.assertRaises(ValueError):
            assess_cable_injection_procedure(procedure(indications=[]), spec())

    def test_missing_specification_field_rejected(self):
        broken = spec()
        del broken["required_current_a"]
        with self.assertRaises(ValueError):
            assess_cable_injection_procedure(procedure(), broken)

    def test_unrecognized_harness_category_rejected(self):
        with self.assertRaises(ValueError):
            assess_cable_injection_procedure(
                procedure(harness_category="waveguide"), spec()
            )


if __name__ == "__main__":
    unittest.main()
