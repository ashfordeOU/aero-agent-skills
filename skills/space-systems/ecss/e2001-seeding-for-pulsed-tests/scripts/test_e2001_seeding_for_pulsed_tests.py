#!/usr/bin/env python3
"""Contract test for clause 6.5.3 seeding under pulsed drive."""

import math
import unittest

from e2001_seeding_for_pulsed_tests_logic import (
    SYNC_FREE_RUNNING,
    SYNC_PULSE_LOCKED,
    assess_pulsed_seeding,
    build_up_cycles_required,
    categorize_seed_synchronization,
    cumulative_initiation_probability,
    cycles_in_pulse,
    duty_cycle,
    evaluate_pulsed_step,
    pulses_in_dwell,
    required_pulse_count,
    seed_electrons_per_pulse,
    synchronization_findings,
)


def make_free_source(**overrides):
    source = {"synchronization": "free-running", "delivered_rate_per_s": 1.0e6}
    source.update(overrides)
    return source


def make_gated_source(**overrides):
    source = {
        "synchronization": "pulse-synchronized",
        "burst_population": 50.0,
        "gate_advance_s": 5.0e-7,
        "electron_transit_s": 2.0e-7,
    }
    source.update(overrides)
    return source


def make_step(**overrides):
    step = {
        "step_id": "step-1",
        "pulse_width_s": 1.0e-6,
        "pulse_period_s": 1.0e-4,
        "dwell_s": 1.0,
        "carrier_frequency_hz": 2.0e9,
        "growth_per_cycle": 1.05,
        "detectable_population": 1.0e6,
    }
    step.update(overrides)
    return step


def make_plan(**overrides):
    plan = {
        "source": make_free_source(),
        "confidence": 0.99,
        "residual_clearing_s": 1.0e-5,
        "max_duty": 0.5,
        "steps": [make_step(), make_step(step_id="step-2", pulse_width_s=2.0e-6)],
    }
    plan.update(overrides)
    return plan


class DutyCycleTests(unittest.TestCase):
    def test_nominal_duty_cycle(self):
        self.assertAlmostEqual(duty_cycle(1.0e-6, 1.0e-4), 0.01, places=12)

    def test_width_equal_to_the_period_gives_unity_duty(self):
        self.assertAlmostEqual(duty_cycle(1.0e-6, 1.0e-6), 1.0, places=12)

    def test_width_beyond_the_period_is_rejected(self):
        with self.assertRaises(ValueError):
            duty_cycle(2.0e-6, 1.0e-6)

    def test_zero_pulse_width_is_rejected(self):
        with self.assertRaises(ValueError):
            duty_cycle(0.0, 1.0e-4)

    def test_zero_pulse_period_is_rejected(self):
        with self.assertRaises(ValueError):
            duty_cycle(1.0e-6, 0.0)

    def test_negative_pulse_width_is_rejected(self):
        with self.assertRaises(ValueError):
            duty_cycle(-1.0e-6, 1.0e-4)

    def test_boolean_pulse_width_is_rejected(self):
        with self.assertRaises(ValueError):
            duty_cycle(True, 1.0e-4)

    def test_non_finite_pulse_period_is_rejected(self):
        with self.assertRaises(ValueError):
            duty_cycle(1.0e-6, float("nan"))


class PulseCountTests(unittest.TestCase):
    def test_whole_pulses_in_a_dwell(self):
        self.assertEqual(pulses_in_dwell(1.0, 1.0e-4), 10000)

    def test_a_partial_pulse_is_not_counted(self):
        self.assertEqual(pulses_in_dwell(2.5e-4, 1.0e-4), 2)

    def test_dwell_shorter_than_one_period_is_rejected(self):
        with self.assertRaises(ValueError):
            pulses_in_dwell(5.0e-5, 1.0e-4)

    def test_zero_dwell_is_rejected(self):
        with self.assertRaises(ValueError):
            pulses_in_dwell(0.0, 1.0e-4)

    def test_zero_period_is_rejected_for_the_count(self):
        with self.assertRaises(ValueError):
            pulses_in_dwell(1.0, 0.0)


class CarrierCycleTests(unittest.TestCase):
    def test_cycles_in_one_on_time(self):
        self.assertAlmostEqual(cycles_in_pulse(1.0e-6, 2.0e9), 2000.0, places=6)

    def test_zero_width_has_no_cycles(self):
        with self.assertRaises(ValueError):
            cycles_in_pulse(0.0, 2.0e9)

    def test_zero_carrier_frequency_is_rejected(self):
        with self.assertRaises(ValueError):
            cycles_in_pulse(1.0e-6, 0.0)


class BuildUpTests(unittest.TestCase):
    def test_cycles_needed_to_reach_a_detectable_population(self):
        self.assertAlmostEqual(
            build_up_cycles_required(1.05, 1.0e6), 283.16179691438606, places=9
        )

    def test_stronger_growth_needs_fewer_cycles(self):
        self.assertLess(
            build_up_cycles_required(1.20, 1.0e6), build_up_cycles_required(1.05, 1.0e6)
        )

    def test_unit_growth_never_builds_up(self):
        with self.assertRaises(ValueError):
            build_up_cycles_required(1.0, 1.0e6)

    def test_growth_below_unity_is_rejected(self):
        with self.assertRaises(ValueError):
            build_up_cycles_required(0.8, 1.0e6)

    def test_single_electron_detection_threshold_is_rejected(self):
        with self.assertRaises(ValueError):
            build_up_cycles_required(1.05, 1.0)

    def test_detection_threshold_below_one_electron_is_rejected(self):
        with self.assertRaises(ValueError):
            build_up_cycles_required(1.05, 0.5)


class SynchronizationCategoryTests(unittest.TestCase):
    def test_free_running_source_is_recognised(self):
        category = categorize_seed_synchronization(make_free_source())
        self.assertEqual(category["synchronization"], SYNC_FREE_RUNNING)
        self.assertFalse(category["gated"])

    def test_gated_source_is_recognised(self):
        category = categorize_seed_synchronization(make_gated_source())
        self.assertEqual(category["synchronization"], SYNC_PULSE_LOCKED)
        self.assertTrue(category["gated"])

    def test_free_running_source_without_a_rate_is_rejected(self):
        source = make_free_source()
        del source["delivered_rate_per_s"]
        with self.assertRaises(ValueError):
            categorize_seed_synchronization(source)

    def test_gated_source_without_a_burst_population_is_rejected(self):
        source = make_gated_source()
        del source["burst_population"]
        with self.assertRaises(ValueError):
            categorize_seed_synchronization(source)

    def test_gated_source_without_a_transit_time_is_rejected(self):
        source = make_gated_source()
        del source["electron_transit_s"]
        with self.assertRaises(ValueError):
            categorize_seed_synchronization(source)

    def test_negative_gate_advance_is_rejected(self):
        with self.assertRaises(ValueError):
            categorize_seed_synchronization(make_gated_source(gate_advance_s=-1.0e-7))

    def test_unknown_synchronization_mode_is_rejected(self):
        with self.assertRaises(ValueError):
            categorize_seed_synchronization(make_free_source(synchronization="drifting"))

    def test_source_that_is_not_a_mapping_is_rejected(self):
        with self.assertRaises(ValueError):
            categorize_seed_synchronization(["free-running"])


class ElectronsPerPulseTests(unittest.TestCase):
    def test_free_running_delivery_scales_with_the_on_time(self):
        self.assertAlmostEqual(
            seed_electrons_per_pulse(make_free_source(), 1.0e-6), 1.0, places=12
        )

    def test_a_longer_on_time_collects_more_electrons(self):
        self.assertAlmostEqual(
            seed_electrons_per_pulse(make_free_source(), 2.0e-6), 2.0, places=12
        )

    def test_gated_burst_delivers_its_population_regardless_of_on_time(self):
        self.assertAlmostEqual(
            seed_electrons_per_pulse(make_gated_source(), 1.0e-8), 50.0, places=12
        )

    def test_zero_on_time_is_rejected(self):
        with self.assertRaises(ValueError):
            seed_electrons_per_pulse(make_free_source(), 0.0)

    def test_negative_delivered_rate_is_rejected(self):
        with self.assertRaises(ValueError):
            seed_electrons_per_pulse(make_free_source(delivered_rate_per_s=-5.0), 1.0e-6)


class SynchronizationFindingTests(unittest.TestCase):
    def test_free_running_source_raises_no_timing_finding(self):
        self.assertEqual(synchronization_findings(make_free_source(), 1.0e-6, 1.0e-4), [])

    def test_well_timed_burst_raises_no_finding(self):
        self.assertEqual(synchronization_findings(make_gated_source(), 1.0e-6, 1.0e-4), [])

    def test_gate_advance_a_hair_under_the_transit_time_is_accepted(self):
        advance = 0.85 * 1e-6 - 0.65 * 1e-6
        self.assertLess(advance, 2.0e-7)
        source = make_gated_source(gate_advance_s=advance)
        self.assertEqual(synchronization_findings(source, 1.0e-6, 1.0e-4), [])

    def test_burst_launched_too_late_is_flagged(self):
        source = make_gated_source(gate_advance_s=1.0e-8)
        self.assertIn(
            "seed-burst-arrives-after-field-rise",
            synchronization_findings(source, 1.0e-6, 1.0e-4),
        )

    def test_burst_launched_inside_the_preceding_pulse_is_flagged(self):
        source = make_gated_source(gate_advance_s=1.5e-6)
        self.assertIn(
            "seed-burst-launched-inside-preceding-pulse",
            synchronization_findings(source, 1.0e-6, 2.0e-6),
        )

    def test_width_beyond_the_period_is_rejected_in_the_timing_check(self):
        with self.assertRaises(ValueError):
            synchronization_findings(make_gated_source(), 2.0e-6, 1.0e-6)


class CumulativeProbabilityTests(unittest.TestCase):
    def test_probability_over_a_short_train(self):
        self.assertAlmostEqual(
            cumulative_initiation_probability(1.0, 5), 1.0 - math.exp(-5.0), places=12
        )

    def test_probability_rises_with_the_pulse_count(self):
        self.assertGreater(
            cumulative_initiation_probability(1.0, 10),
            cumulative_initiation_probability(1.0, 5),
        )

    def test_zero_electrons_per_pulse_is_rejected(self):
        with self.assertRaises(ValueError):
            cumulative_initiation_probability(0.0, 5)

    def test_fractional_pulse_count_is_rejected(self):
        with self.assertRaises(ValueError):
            cumulative_initiation_probability(1.0, 5.5)

    def test_zero_pulse_count_is_rejected(self):
        with self.assertRaises(ValueError):
            cumulative_initiation_probability(1.0, 0)

    def test_boolean_pulse_count_is_rejected(self):
        with self.assertRaises(ValueError):
            cumulative_initiation_probability(1.0, True)


class RequiredPulseCountTests(unittest.TestCase):
    def test_single_electron_per_pulse_needs_five_pulses(self):
        self.assertEqual(required_pulse_count(1.0, 0.99), 5)

    def test_an_exact_requirement_is_not_rounded_up(self):
        per_pulse = -math.log(0.01) / 5.0
        self.assertEqual(required_pulse_count(per_pulse, 0.99), 5)

    def test_representation_error_does_not_inflate_the_requirement(self):
        per_pulse = 2.302585092994045
        self.assertGreater(math.ceil(-math.log(0.01) / per_pulse), 2)
        self.assertEqual(required_pulse_count(per_pulse, 0.99), 2)

    def test_a_large_burst_needs_a_single_pulse(self):
        self.assertEqual(required_pulse_count(50.0, 0.99), 1)

    def test_confidence_of_one_is_rejected(self):
        with self.assertRaises(ValueError):
            required_pulse_count(1.0, 1.0)

    def test_confidence_of_zero_is_rejected(self):
        with self.assertRaises(ValueError):
            required_pulse_count(1.0, 0.0)

    def test_zero_electrons_per_pulse_is_rejected_for_the_requirement(self):
        with self.assertRaises(ValueError):
            required_pulse_count(0.0, 0.99)


class PulsedStepTests(unittest.TestCase):
    def test_nominal_free_running_step_is_sufficient(self):
        result = evaluate_pulsed_step(make_step(), make_free_source())
        self.assertTrue(result["sufficient"])
        self.assertEqual(result["findings"], [])

    def test_nominal_gated_step_is_sufficient(self):
        result = evaluate_pulsed_step(make_step(), make_gated_source())
        self.assertTrue(result["sufficient"])

    def test_too_few_pulses_is_flagged(self):
        result = evaluate_pulsed_step(make_step(dwell_s=3.0e-4), make_free_source())
        self.assertIn("seeding-confidence-not-reached", result["findings"])

    def test_pulse_too_short_for_build_up_is_flagged(self):
        result = evaluate_pulsed_step(make_step(pulse_width_s=1.0e-8), make_free_source())
        self.assertIn("pulse-too-short-for-avalanche-build-up", result["findings"])

    def test_off_time_short_of_residual_clearing_is_flagged(self):
        result = evaluate_pulsed_step(
            make_step(), make_free_source(), residual_clearing_s=1.0e-3
        )
        self.assertIn("off-time-short-of-residual-clearing", result["findings"])

    def test_duty_outside_the_pulsed_regime_is_flagged(self):
        step = make_step(pulse_width_s=8.0e-7, pulse_period_s=1.0e-6, dwell_s=1.0e-3)
        result = evaluate_pulsed_step(step, make_free_source())
        self.assertIn("drive-duty-outside-pulsed-regime", result["findings"])

    def test_step_reports_its_duty_and_pulse_count(self):
        result = evaluate_pulsed_step(make_step(), make_free_source())
        self.assertAlmostEqual(result["duty_cycle"], 0.01, places=12)
        self.assertEqual(result["pulse_count"], 10000)
        self.assertEqual(result["required_pulse_count"], 5)

    def test_step_reports_its_carrier_cycle_budget(self):
        result = evaluate_pulsed_step(make_step(), make_free_source())
        self.assertAlmostEqual(result["carrier_cycles_per_pulse"], 2000.0, places=6)
        self.assertAlmostEqual(result["required_build_up_cycles"], 283.16179691438606, places=9)

    def test_missing_step_identifier_is_rejected(self):
        step = make_step()
        del step["step_id"]
        with self.assertRaises(ValueError):
            evaluate_pulsed_step(step, make_free_source())

    def test_zero_pulse_width_step_is_rejected(self):
        with self.assertRaises(ValueError):
            evaluate_pulsed_step(make_step(pulse_width_s=0.0), make_free_source())

    def test_negative_residual_clearing_time_is_rejected(self):
        with self.assertRaises(ValueError):
            evaluate_pulsed_step(make_step(), make_free_source(), residual_clearing_s=-1.0e-6)

    def test_zero_maximum_duty_is_rejected(self):
        with self.assertRaises(ValueError):
            evaluate_pulsed_step(make_step(), make_free_source(), max_duty=0.0)

    def test_maximum_duty_above_unity_is_rejected(self):
        with self.assertRaises(ValueError):
            evaluate_pulsed_step(make_step(), make_free_source(), max_duty=1.5)

    def test_missing_growth_per_cycle_is_rejected(self):
        step = make_step()
        del step["growth_per_cycle"]
        with self.assertRaises(ValueError):
            evaluate_pulsed_step(step, make_free_source())


class RunAssessmentTests(unittest.TestCase):
    def test_nominal_run_is_compliant(self):
        report = assess_pulsed_seeding(make_plan())
        self.assertTrue(report["compliant"])
        self.assertEqual(report["step_count"], 2)
        self.assertEqual(report["synchronization"], SYNC_FREE_RUNNING)

    def test_findings_carry_the_step_identifier(self):
        plan = make_plan(steps=[make_step(dwell_s=3.0e-4)])
        report = assess_pulsed_seeding(plan)
        self.assertIn("step-1:seeding-confidence-not-reached", report["findings"])
        self.assertFalse(report["compliant"])

    def test_gated_run_reports_its_synchronization(self):
        report = assess_pulsed_seeding(make_plan(source=make_gated_source()))
        self.assertEqual(report["synchronization"], SYNC_PULSE_LOCKED)
        self.assertTrue(report["compliant"])

    def test_mistimed_gated_run_is_flagged_per_step(self):
        plan = make_plan(source=make_gated_source(gate_advance_s=1.0e-9))
        report = assess_pulsed_seeding(plan)
        self.assertIn("step-1:seed-burst-arrives-after-field-rise", report["findings"])

    def test_run_without_a_step_is_rejected(self):
        with self.assertRaises(ValueError):
            assess_pulsed_seeding(make_plan(steps=[]))

    def test_steps_that_are_not_a_list_are_rejected(self):
        with self.assertRaises(ValueError):
            assess_pulsed_seeding(make_plan(steps=make_step()))

    def test_duplicate_step_identifier_is_rejected(self):
        with self.assertRaises(ValueError):
            assess_pulsed_seeding(make_plan(steps=[make_step(), make_step()]))

    def test_run_without_a_source_is_rejected(self):
        plan = make_plan()
        del plan["source"]
        with self.assertRaises(ValueError):
            assess_pulsed_seeding(plan)

    def test_every_step_is_scored(self):
        report = assess_pulsed_seeding(make_plan())
        self.assertEqual(len(report["steps"]), 2)


if __name__ == "__main__":
    unittest.main()
