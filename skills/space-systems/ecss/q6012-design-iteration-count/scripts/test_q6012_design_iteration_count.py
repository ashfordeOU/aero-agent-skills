"""Contract tests for the clause 7.1.3 design-cycle planning logic."""

import unittest

from q6012_design_iteration_count_logic import (
    CONVERGENCE_FACTORS,
    NOVELTY_FLOORS,
    convergence_factor,
    iterations_for_gap,
    novelty_floor,
    plan_iterations,
    residual_gap_db,
    schedule_capacity,
)


def clean_spec(**overrides):
    spec = {
        "initial_gap_db": 4.0,
        "acceptance_gap_db": 0.25,
        "model_maturity": "process-calibrated",
        "novelty": "derivative",
        "planned_cycles": 4,
        "available_weeks": 80.0,
        "cycle_weeks": 16.0,
        "front_end_weeks": 8.0,
    }
    spec.update(overrides)
    return spec


class ConvergenceFactorTests(unittest.TestCase):
    def test_calibrated_model_closes_more_per_cycle(self):
        self.assertLess(
            convergence_factor("measured-calibrated"),
            convergence_factor("vendor-default"),
        )

    def test_token_is_normalised(self):
        self.assertAlmostEqual(
            convergence_factor("  Vendor_Default "),
            CONVERGENCE_FACTORS["vendor-default"],
            places=9,
        )

    def test_every_factor_is_a_strict_contraction(self):
        for name, value in CONVERGENCE_FACTORS.items():
            self.assertGreater(value, 0.0, name)
            self.assertLess(value, 1.0, name)

    def test_unknown_maturity_rejected(self):
        with self.assertRaises(ValueError):
            convergence_factor("guessed")

    def test_non_string_maturity_rejected(self):
        with self.assertRaises(ValueError):
            convergence_factor(0.4)

    def test_empty_maturity_rejected(self):
        with self.assertRaises(ValueError):
            convergence_factor("   ")


class NoveltyFloorTests(unittest.TestCase):
    def test_heritage_floor_is_lowest(self):
        self.assertEqual(novelty_floor("qualified-heritage"), 1)

    def test_new_design_floor_is_highest(self):
        self.assertEqual(
            novelty_floor("new-design"), max(NOVELTY_FLOORS.values())
        )

    def test_token_is_normalised(self):
        self.assertEqual(novelty_floor(" New_Design "), 3)

    def test_unknown_novelty_rejected(self):
        with self.assertRaises(ValueError):
            novelty_floor("mostly-new")


class IterationsForGapTests(unittest.TestCase):
    def test_gap_already_inside_acceptance_needs_no_cycle(self):
        self.assertEqual(iterations_for_gap(0.2, 0.25, 0.4), 0)

    def test_gap_exactly_on_acceptance_needs_no_cycle(self):
        self.assertEqual(iterations_for_gap(0.25, 0.25, 0.4), 0)

    def test_one_cycle_when_one_contraction_suffices(self):
        self.assertEqual(iterations_for_gap(1.0, 0.5, 0.4), 1)

    def test_exact_power_of_the_factor_is_not_rounded_up_a_cycle(self):
        # 0.5**3 == 0.125 exactly; a naive ceil of the log ratio can return 4.
        self.assertEqual(iterations_for_gap(1.0, 0.125, 0.5), 3)

    def test_slower_convergence_needs_more_cycles(self):
        fast = iterations_for_gap(4.0, 0.25, 0.25)
        slow = iterations_for_gap(4.0, 0.25, 0.8)
        self.assertGreater(slow, fast)

    def test_zero_initial_gap_needs_no_cycle(self):
        self.assertEqual(iterations_for_gap(0.0, 0.25, 0.4), 0)

    def test_factor_at_unity_rejected(self):
        with self.assertRaises(ValueError):
            iterations_for_gap(4.0, 0.25, 1.0)

    def test_factor_above_unity_rejected(self):
        with self.assertRaises(ValueError):
            iterations_for_gap(4.0, 0.25, 1.2)

    def test_zero_acceptance_gap_rejected(self):
        with self.assertRaises(ValueError):
            iterations_for_gap(4.0, 0.0, 0.4)

    def test_negative_initial_gap_rejected(self):
        with self.assertRaises(ValueError):
            iterations_for_gap(-1.0, 0.25, 0.4)

    def test_non_numeric_gap_rejected(self):
        with self.assertRaises(ValueError):
            iterations_for_gap("4", 0.25, 0.4)

    def test_boolean_gap_rejected(self):
        with self.assertRaises(ValueError):
            iterations_for_gap(True, 0.25, 0.4)


class ResidualGapTests(unittest.TestCase):
    def test_zero_cycles_leaves_the_initial_gap(self):
        self.assertAlmostEqual(residual_gap_db(4.0, 0.4, 0), 4.0, places=9)

    def test_one_cycle_applies_the_factor_once(self):
        self.assertAlmostEqual(residual_gap_db(4.0, 0.5, 1), 2.0, places=9)

    def test_three_cycles_apply_the_factor_three_times(self):
        self.assertAlmostEqual(residual_gap_db(1.0, 0.5, 3), 0.125, places=9)

    def test_the_required_cycle_count_reaches_acceptance(self):
        cycles = iterations_for_gap(4.0, 0.25, 0.4)
        self.assertLessEqual(residual_gap_db(4.0, 0.4, cycles), 0.25)

    def test_one_cycle_short_does_not_reach_acceptance(self):
        cycles = iterations_for_gap(4.0, 0.25, 0.4)
        self.assertGreater(residual_gap_db(4.0, 0.4, cycles - 1), 0.25)

    def test_negative_cycles_rejected(self):
        with self.assertRaises(ValueError):
            residual_gap_db(4.0, 0.4, -1)

    def test_non_integer_cycles_rejected(self):
        with self.assertRaises(ValueError):
            residual_gap_db(4.0, 0.4, 2.5)


class ScheduleCapacityTests(unittest.TestCase):
    def test_capacity_is_whole_cycles_after_the_front_end(self):
        self.assertEqual(schedule_capacity(80.0, 16.0, 8.0), 4)

    def test_exact_fit_is_not_rounded_down(self):
        self.assertEqual(schedule_capacity(48.0, 16.0, 0.0), 3)

    def test_partial_cycle_does_not_count(self):
        self.assertEqual(schedule_capacity(47.0, 16.0, 0.0), 2)

    def test_front_end_longer_than_the_schedule_leaves_no_capacity(self):
        self.assertEqual(schedule_capacity(10.0, 16.0, 20.0), 0)

    def test_zero_cycle_length_rejected(self):
        with self.assertRaises(ValueError):
            schedule_capacity(80.0, 0.0, 8.0)

    def test_negative_available_weeks_rejected(self):
        with self.assertRaises(ValueError):
            schedule_capacity(-4.0, 16.0, 0.0)

    def test_negative_front_end_rejected(self):
        with self.assertRaises(ValueError):
            schedule_capacity(80.0, 16.0, -1.0)


class PlanIterationsTests(unittest.TestCase):
    def test_adequate_plan_supports_the_freeze(self):
        result = plan_iterations(clean_spec())
        self.assertTrue(result["freeze_supported"])
        self.assertEqual(result["findings"], [])

    def test_required_count_is_the_larger_of_closure_and_floor(self):
        result = plan_iterations(clean_spec())
        self.assertEqual(
            result["required_cycles"],
            max(result["closure_cycles"], result["novelty_floor"]),
        )

    def test_novelty_floor_can_drive_the_requirement(self):
        result = plan_iterations(
            clean_spec(initial_gap_db=0.3, novelty="new-design", planned_cycles=3)
        )
        self.assertEqual(result["closure_cycles"], 1)
        self.assertEqual(result["required_cycles"], 3)

    def test_short_plan_is_reported_against_the_floor(self):
        result = plan_iterations(
            clean_spec(initial_gap_db=0.3, novelty="new-design", planned_cycles=1)
        )
        self.assertFalse(result["freeze_supported"])
        self.assertTrue(any("novelty floor" in f for f in result["findings"]))

    def test_short_plan_is_reported_against_gap_closure(self):
        result = plan_iterations(
            clean_spec(model_maturity="extrapolated", planned_cycles=2)
        )
        self.assertFalse(result["freeze_supported"])
        self.assertTrue(any("gap closure" in f for f in result["findings"]))

    def test_schedule_shortfall_is_its_own_finding(self):
        result = plan_iterations(clean_spec(available_weeks=30.0))
        self.assertFalse(result["freeze_supported"])
        self.assertTrue(any("schedule carries only" in f for f in result["findings"]))

    def test_plan_beyond_the_schedule_is_reported(self):
        result = plan_iterations(clean_spec(planned_cycles=6))
        self.assertTrue(any("exceeds the" in f for f in result["findings"]))

    def test_residual_gap_matches_the_planned_cycle_count(self):
        spec = clean_spec(planned_cycles=2)
        result = plan_iterations(spec)
        self.assertAlmostEqual(
            result["residual_gap_db"],
            residual_gap_db(spec["initial_gap_db"], result["convergence_factor"], 2),
            places=9,
        )

    def test_residual_exactly_on_acceptance_counts_as_closed(self):
        # 1.0 * 0.25**2 lands exactly on the acceptance gap; the boundary is a
        # representation question, so it is absorbed and not a shortfall.
        result = plan_iterations(
            clean_spec(
                initial_gap_db=1.0,
                acceptance_gap_db=0.0625,
                model_maturity="measured-calibrated",
                planned_cycles=2,
                available_weeks=64.0,
                front_end_weeks=0.0,
            )
        )
        self.assertAlmostEqual(result["residual_gap_db"], 0.0625, places=9)
        self.assertEqual(result["closure_cycles"], 2)
        self.assertTrue(result["gap_closed"])
        self.assertTrue(result["freeze_supported"])

    def test_slower_model_raises_the_required_cycle_count(self):
        fast = plan_iterations(clean_spec(model_maturity="measured-calibrated"))
        slow = plan_iterations(clean_spec(model_maturity="extrapolated"))
        self.assertGreater(slow["required_cycles"], fast["required_cycles"])

    def test_negative_planned_cycles_rejected(self):
        with self.assertRaises(ValueError):
            plan_iterations(clean_spec(planned_cycles=-1))

    def test_non_integer_planned_cycles_rejected(self):
        with self.assertRaises(ValueError):
            plan_iterations(clean_spec(planned_cycles=3.5))

    def test_missing_spec_key_rejected(self):
        spec = clean_spec()
        del spec["cycle_weeks"]
        with self.assertRaises(ValueError):
            plan_iterations(spec)

    def test_non_mapping_spec_rejected(self):
        with self.assertRaises(ValueError):
            plan_iterations(["initial_gap_db"])

    def test_unknown_novelty_rejected_by_the_assessment(self):
        with self.assertRaises(ValueError):
            plan_iterations(clean_spec(novelty="somewhat-new"))


if __name__ == "__main__":
    unittest.main()
