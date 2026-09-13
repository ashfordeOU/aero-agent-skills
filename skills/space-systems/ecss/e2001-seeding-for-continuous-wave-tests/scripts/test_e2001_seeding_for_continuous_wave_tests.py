#!/usr/bin/env python3
"""Contract test for clause 6.5.2 seeding under continuous-wave drive."""

import math
import unittest

from e2001_seeding_for_continuous_wave_tests_logic import (
    MODE_CONTINUOUS,
    MODE_REPETITIVE,
    assess_cw_seeding,
    categorize_seed_source,
    decay_corrected_emission,
    effective_seed_rate,
    evaluate_drive_step,
    initiation_probability,
    mean_seed_interval,
    required_dwell,
    seed_electron_fluence,
)


def make_source(**overrides):
    source = {
        "kind": "ultraviolet-lamp",
        "emission_rate_per_s": 2000.0,
        "transport_fraction": 0.5,
        "gap_capture_fraction": 1.0,
    }
    source.update(overrides)
    return source


def make_beta_source(**overrides):
    source = {
        "kind": "beta-emitter",
        "emission_rate_per_s": 4.0e6,
        "half_life_days": 100.0,
        "elapsed_days": 200.0,
        "transport_fraction": 0.25,
        "gap_capture_fraction": 0.4,
    }
    source.update(overrides)
    return source


def make_plan(**overrides):
    plan = {
        "source": make_source(),
        "gap_area_cm2": 1.0,
        "max_fluence_per_cm2": 1.0e12,
        "seed_source_in_drive_path": False,
        "confidence": 0.99,
        "steps": [
            {"step_id": "step-1", "forward_power_w": 10.0, "dwell_s": 60.0},
            {"step_id": "step-2", "forward_power_w": 20.0, "dwell_s": 60.0},
        ],
    }
    plan.update(overrides)
    return plan


class SeedSourceCategoryTests(unittest.TestCase):
    def test_ultraviolet_lamp_emits_continuously(self):
        category = categorize_seed_source(make_source())
        self.assertEqual(category["emission_mode"], MODE_CONTINUOUS)
        self.assertAlmostEqual(category["emission_duty"], 1.0, places=12)

    def test_beta_emitter_is_marked_as_decaying(self):
        category = categorize_seed_source(make_beta_source())
        self.assertTrue(category["decaying"])

    def test_direct_current_gun_emits_continuously(self):
        category = categorize_seed_source(make_source(kind="electron-gun-dc"))
        self.assertEqual(category["emission_mode"], MODE_CONTINUOUS)
        self.assertFalse(category["decaying"])

    def test_repetitively_pulsed_gun_carries_its_own_duty(self):
        source = make_source(kind="electron-gun-pulsed", emission_duty=0.2)
        category = categorize_seed_source(source)
        self.assertEqual(category["emission_mode"], MODE_REPETITIVE)
        self.assertAlmostEqual(category["emission_duty"], 0.2, places=12)

    def test_pulsed_gun_without_a_declared_duty_is_rejected(self):
        with self.assertRaises(ValueError):
            categorize_seed_source(make_source(kind="electron-gun-pulsed"))

    def test_duty_above_unity_is_rejected(self):
        with self.assertRaises(ValueError):
            categorize_seed_source(make_source(kind="electron-gun-pulsed", emission_duty=1.4))

    def test_zero_duty_is_rejected(self):
        with self.assertRaises(ValueError):
            categorize_seed_source(make_source(kind="electron-gun-pulsed", emission_duty=0.0))

    def test_continuous_source_may_restate_unity_duty(self):
        category = categorize_seed_source(make_source(emission_duty=1.0))
        self.assertEqual(category["emission_mode"], MODE_CONTINUOUS)

    def test_continuous_source_declaring_a_partial_duty_is_rejected(self):
        with self.assertRaises(ValueError):
            categorize_seed_source(make_source(emission_duty=0.5))

    def test_unknown_source_kind_is_rejected(self):
        with self.assertRaises(ValueError):
            categorize_seed_source(make_source(kind="thermionic-filament"))

    def test_missing_source_kind_is_rejected(self):
        source = make_source()
        del source["kind"]
        with self.assertRaises(ValueError):
            categorize_seed_source(source)

    def test_source_that_is_not_a_mapping_is_rejected(self):
        with self.assertRaises(ValueError):
            categorize_seed_source("ultraviolet-lamp")


class DecayCorrectionTests(unittest.TestCase):
    def test_one_half_life_halves_the_emission(self):
        self.assertAlmostEqual(decay_corrected_emission(1000.0, 50.0, 50.0), 500.0, places=9)

    def test_two_half_lives_quarter_the_emission(self):
        self.assertAlmostEqual(decay_corrected_emission(1000.0, 50.0, 100.0), 250.0, places=9)

    def test_no_elapsed_interval_leaves_the_emission_unchanged(self):
        self.assertAlmostEqual(decay_corrected_emission(1000.0, 50.0, 0.0), 1000.0, places=9)

    def test_partial_half_life_follows_the_exponential_law(self):
        expected = 1000.0 * math.pow(2.0, -0.5)
        self.assertAlmostEqual(decay_corrected_emission(1000.0, 50.0, 25.0), expected, places=9)

    def test_zero_half_life_is_rejected(self):
        with self.assertRaises(ValueError):
            decay_corrected_emission(1000.0, 0.0, 10.0)

    def test_negative_elapsed_interval_is_rejected(self):
        with self.assertRaises(ValueError):
            decay_corrected_emission(1000.0, 50.0, -1.0)

    def test_zero_initial_emission_is_rejected(self):
        with self.assertRaises(ValueError):
            decay_corrected_emission(0.0, 50.0, 10.0)

    def test_boolean_emission_is_rejected(self):
        with self.assertRaises(ValueError):
            decay_corrected_emission(True, 50.0, 10.0)

    def test_infinite_half_life_is_rejected(self):
        with self.assertRaises(ValueError):
            decay_corrected_emission(1000.0, float("inf"), 10.0)


class EffectiveSeedRateTests(unittest.TestCase):
    def test_continuous_source_rate_is_the_product_of_the_fractions(self):
        self.assertAlmostEqual(effective_seed_rate(make_source()), 1000.0, places=9)

    def test_decaying_source_rate_includes_the_decay_correction(self):
        self.assertAlmostEqual(effective_seed_rate(make_beta_source()), 1.0e5, places=6)

    def test_pulsed_source_rate_is_derated_by_its_duty(self):
        source = make_source(kind="electron-gun-pulsed", emission_duty=0.25)
        self.assertAlmostEqual(effective_seed_rate(source), 250.0, places=9)

    def test_missing_transport_fraction_is_rejected(self):
        source = make_source()
        del source["transport_fraction"]
        with self.assertRaises(ValueError):
            effective_seed_rate(source)

    def test_zero_transport_fraction_is_rejected(self):
        with self.assertRaises(ValueError):
            effective_seed_rate(make_source(transport_fraction=0.0))

    def test_transport_fraction_above_unity_is_rejected(self):
        with self.assertRaises(ValueError):
            effective_seed_rate(make_source(transport_fraction=1.5))

    def test_capture_fraction_above_unity_is_rejected(self):
        with self.assertRaises(ValueError):
            effective_seed_rate(make_source(gap_capture_fraction=1.2))

    def test_decaying_source_without_a_half_life_is_rejected(self):
        source = make_beta_source()
        del source["half_life_days"]
        with self.assertRaises(ValueError):
            effective_seed_rate(source)

    def test_decaying_source_with_a_negative_elapsed_interval_is_rejected(self):
        with self.assertRaises(ValueError):
            effective_seed_rate(make_beta_source(elapsed_days=-5.0))

    def test_zero_emission_rate_is_rejected(self):
        with self.assertRaises(ValueError):
            effective_seed_rate(make_source(emission_rate_per_s=0.0))


class SeedIntervalTests(unittest.TestCase):
    def test_interval_is_the_reciprocal_of_the_rate(self):
        self.assertAlmostEqual(mean_seed_interval(250.0), 0.004, places=12)

    def test_zero_rate_is_rejected(self):
        with self.assertRaises(ValueError):
            mean_seed_interval(0.0)

    def test_negative_rate_is_rejected(self):
        with self.assertRaises(ValueError):
            mean_seed_interval(-3.0)

    def test_boolean_rate_is_rejected(self):
        with self.assertRaises(ValueError):
            mean_seed_interval(True)


class InitiationProbabilityTests(unittest.TestCase):
    def test_one_mean_interval_gives_the_expected_probability(self):
        self.assertAlmostEqual(initiation_probability(2.0, 0.5), 1.0 - math.exp(-1.0), places=12)

    def test_probability_rises_with_a_longer_dwell(self):
        short = initiation_probability(5.0, 0.1)
        long_dwell = initiation_probability(5.0, 1.0)
        self.assertGreater(long_dwell, short)

    def test_a_very_long_dwell_approaches_certainty(self):
        self.assertAlmostEqual(initiation_probability(100.0, 10.0), 1.0, places=12)

    def test_zero_dwell_is_rejected(self):
        with self.assertRaises(ValueError):
            initiation_probability(10.0, 0.0)

    def test_negative_dwell_is_rejected(self):
        with self.assertRaises(ValueError):
            initiation_probability(10.0, -1.0)

    def test_zero_rate_is_rejected_for_the_probability(self):
        with self.assertRaises(ValueError):
            initiation_probability(0.0, 1.0)


class RequiredDwellTests(unittest.TestCase):
    def test_required_dwell_at_unit_rate(self):
        self.assertAlmostEqual(required_dwell(1.0, 0.99), 4.605170185988091, places=12)

    def test_required_dwell_scales_inversely_with_the_rate(self):
        self.assertAlmostEqual(required_dwell(10.0, 0.99), 0.4605170185988091, places=12)

    def test_required_dwell_round_trips_to_the_confidence(self):
        needed = required_dwell(7.0, 0.95)
        self.assertAlmostEqual(initiation_probability(7.0, needed), 0.95, places=12)

    def test_confidence_of_one_is_rejected(self):
        with self.assertRaises(ValueError):
            required_dwell(1.0, 1.0)

    def test_confidence_of_zero_is_rejected(self):
        with self.assertRaises(ValueError):
            required_dwell(1.0, 0.0)

    def test_negative_confidence_is_rejected(self):
        with self.assertRaises(ValueError):
            required_dwell(1.0, -0.2)

    def test_boolean_confidence_is_rejected(self):
        with self.assertRaises(ValueError):
            required_dwell(1.0, True)


class DriveStepTests(unittest.TestCase):
    def test_generous_dwell_raises_no_finding(self):
        result = evaluate_drive_step(
            {"step_id": "step-1", "forward_power_w": 40.0, "dwell_s": 30.0}, 100.0
        )
        self.assertEqual(result["findings"], [])
        self.assertTrue(result["sufficient"])

    def test_short_dwell_is_flagged(self):
        result = evaluate_drive_step(
            {"step_id": "step-1", "forward_power_w": 40.0, "dwell_s": 0.001}, 1.0
        )
        self.assertEqual(result["findings"], ["seeding-confidence-not-reached"])

    def test_dwell_assembled_a_hair_under_the_requirement_is_accepted(self):
        needed = required_dwell(1.0, 0.99)
        dwell = 0.129 + 4.4761701859880905
        self.assertLess(dwell, needed)
        result = evaluate_drive_step(
            {"step_id": "step-1", "forward_power_w": 40.0, "dwell_s": dwell}, 1.0
        )
        self.assertTrue(result["sufficient"])
        self.assertEqual(result["findings"], [])

    def test_step_records_its_initiation_probability(self):
        result = evaluate_drive_step(
            {"step_id": "step-1", "forward_power_w": 40.0, "dwell_s": 0.5}, 2.0
        )
        self.assertAlmostEqual(result["initiation_probability"], 1.0 - math.exp(-1.0), places=12)

    def test_missing_step_identifier_is_rejected(self):
        with self.assertRaises(ValueError):
            evaluate_drive_step({"forward_power_w": 40.0, "dwell_s": 30.0}, 100.0)

    def test_zero_dwell_step_is_rejected(self):
        with self.assertRaises(ValueError):
            evaluate_drive_step(
                {"step_id": "step-1", "forward_power_w": 40.0, "dwell_s": 0.0}, 100.0
            )

    def test_zero_forward_power_step_is_rejected(self):
        with self.assertRaises(ValueError):
            evaluate_drive_step(
                {"step_id": "step-1", "forward_power_w": 0.0, "dwell_s": 30.0}, 100.0
            )


class FluenceTests(unittest.TestCase):
    def test_fluence_is_rate_times_exposure_over_area(self):
        self.assertAlmostEqual(seed_electron_fluence(1000.0, 4.0, 8.0), 2000.0, places=9)

    def test_zero_area_is_rejected(self):
        with self.assertRaises(ValueError):
            seed_electron_fluence(1000.0, 0.0, 8.0)

    def test_zero_exposure_is_rejected(self):
        with self.assertRaises(ValueError):
            seed_electron_fluence(1000.0, 4.0, 0.0)

    def test_zero_rate_is_rejected_for_the_fluence(self):
        with self.assertRaises(ValueError):
            seed_electron_fluence(0.0, 4.0, 8.0)


class RunAssessmentTests(unittest.TestCase):
    def test_nominal_run_is_compliant(self):
        report = assess_cw_seeding(make_plan())
        self.assertTrue(report["compliant"])
        self.assertAlmostEqual(report["seed_rate_per_s"], 1000.0, places=9)
        self.assertAlmostEqual(report["total_dwell_s"], 120.0, places=9)

    def test_short_dwell_step_is_named_in_the_findings(self):
        plan = make_plan(
            source=make_source(emission_rate_per_s=2.0, transport_fraction=0.5),
            steps=[
                {"step_id": "step-1", "forward_power_w": 10.0, "dwell_s": 0.5},
                {"step_id": "step-2", "forward_power_w": 20.0, "dwell_s": 60.0},
            ],
        )
        report = assess_cw_seeding(plan)
        self.assertIn("step-1:seeding-confidence-not-reached", report["findings"])
        self.assertFalse(report["compliant"])

    def test_excess_seed_fluence_is_flagged(self):
        plan = make_plan(gap_area_cm2=2.0, max_fluence_per_cm2=100.0)
        report = assess_cw_seeding(plan)
        self.assertIn("seed-electron-fluence-exceeds-limit", report["findings"])

    def test_fluence_a_hair_over_the_limit_is_absorbed(self):
        plan = make_plan(
            gap_area_cm2=2.0,
            max_fluence_per_cm2=300.0,
            steps=[
                {"step_id": "step-1", "forward_power_w": 10.0, "dwell_s": 0.1},
                {"step_id": "step-2", "forward_power_w": 20.0, "dwell_s": 0.2},
                {"step_id": "step-3", "forward_power_w": 30.0, "dwell_s": 0.3},
            ],
        )
        report = assess_cw_seeding(plan)
        self.assertGreater(report["fluence_per_cm2"], 300.0)
        self.assertTrue(report["compliant"])

    def test_source_left_in_the_drive_path_is_flagged(self):
        report = assess_cw_seeding(make_plan(seed_source_in_drive_path=True))
        self.assertIn("seed-source-obstructs-drive-path", report["findings"])

    def test_run_without_a_drive_step_is_rejected(self):
        with self.assertRaises(ValueError):
            assess_cw_seeding(make_plan(steps=[]))

    def test_steps_that_are_not_a_list_are_rejected(self):
        with self.assertRaises(ValueError):
            assess_cw_seeding(make_plan(steps={"step_id": "step-1"}))

    def test_duplicate_step_identifier_is_rejected(self):
        plan = make_plan(
            steps=[
                {"step_id": "step-1", "forward_power_w": 10.0, "dwell_s": 60.0},
                {"step_id": "step-1", "forward_power_w": 20.0, "dwell_s": 60.0},
            ]
        )
        with self.assertRaises(ValueError):
            assess_cw_seeding(plan)

    def test_forward_power_that_does_not_rise_is_rejected(self):
        plan = make_plan(
            steps=[
                {"step_id": "step-1", "forward_power_w": 30.0, "dwell_s": 60.0},
                {"step_id": "step-2", "forward_power_w": 20.0, "dwell_s": 60.0},
            ]
        )
        with self.assertRaises(ValueError):
            assess_cw_seeding(plan)

    def test_missing_gap_area_is_rejected(self):
        plan = make_plan()
        del plan["gap_area_cm2"]
        with self.assertRaises(ValueError):
            assess_cw_seeding(plan)

    def test_missing_drive_path_flag_is_rejected(self):
        plan = make_plan()
        del plan["seed_source_in_drive_path"]
        with self.assertRaises(ValueError):
            assess_cw_seeding(plan)

    def test_decaying_source_run_carries_the_corrected_rate(self):
        report = assess_cw_seeding(make_plan(source=make_beta_source()))
        self.assertAlmostEqual(report["seed_rate_per_s"], 1.0e5, places=6)

    def test_mean_seed_interval_is_reported(self):
        report = assess_cw_seeding(make_plan())
        self.assertAlmostEqual(report["mean_seed_interval_s"], 0.001, places=12)

    def test_every_step_is_scored(self):
        report = assess_cw_seeding(make_plan())
        self.assertEqual(len(report["steps"]), 2)


if __name__ == "__main__":
    unittest.main()
