"""Contract test for the crimp process qualification leaf (unittest)."""

import unittest

from q7026_process_qualification_logic import (
    CONDITIONAL,
    NOT_QUALIFIED,
    QUALIFIED,
    assess_qualification,
    grade_run,
    grade_sample,
    group_samples_by_run,
    longest_consecutive_conforming,
    process_centring,
    requalification_due,
    validate_sample,
    validate_specification,
)


def spec(**kw):
    s = {
        "terminal_part_number": "M39029-58-360",
        "conductor_construction": "awg-22-19-strand-silver-plated",
        "tool_setting": "selector-5",
        "crimp_height_min_mm": 1.30,
        "crimp_height_max_mm": 1.50,
        "pull_off_minimum_n": 90.0,
        "samples_per_run": 3,
        "consecutive_runs_required": 3,
        "validity_days": 365,
        "requalification_triggers": [
            "die-regrind",
            "tool-replacement",
            "setting-change",
            "conductor-construction-change",
        ],
    }
    s.update(kw)
    return s


def sample(run_index=1, height=1.40, force=118.0, visual=True):
    return {
        "run_index": run_index,
        "crimp_height_mm": height,
        "pull_off_force_n": force,
        "visual_pass": visual,
    }


def campaign(runs=(1, 2, 3), per_run=3, height=1.40):
    made = []
    for index in runs:
        for _ in range(per_run):
            made.append(sample(run_index=index, height=height))
    return made


class TestSpecificationValidation(unittest.TestCase):
    def test_a_non_mapping_specification_raises(self):
        with self.assertRaises(ValueError):
            validate_specification("q-st-70-26")

    def test_an_inverted_crimp_height_window_raises(self):
        with self.assertRaises(ValueError):
            validate_specification(
                spec(crimp_height_min_mm=1.50, crimp_height_max_mm=1.30)
            )

    def test_a_collapsed_crimp_height_window_raises(self):
        with self.assertRaises(ValueError):
            validate_specification(
                spec(crimp_height_min_mm=1.40, crimp_height_max_mm=1.40)
            )

    def test_a_zero_pull_off_minimum_raises(self):
        with self.assertRaises(ValueError):
            validate_specification(spec(pull_off_minimum_n=0.0))

    def test_a_zero_consecutive_run_requirement_raises(self):
        with self.assertRaises(ValueError):
            validate_specification(spec(consecutive_runs_required=0))

    def test_a_non_list_trigger_set_raises(self):
        with self.assertRaises(ValueError):
            validate_specification(spec(requalification_triggers="die-regrind"))

    def test_the_terminal_part_number_is_folded_to_upper_case(self):
        checked = validate_specification(spec(terminal_part_number="m39029-58-360"))
        self.assertEqual(checked["terminal_part_number"], "M39029-58-360")


class TestSampleValidation(unittest.TestCase):
    def test_a_non_mapping_sample_raises(self):
        with self.assertRaises(ValueError):
            validate_sample([1, 1.40, 118.0])

    def test_a_zero_run_index_raises(self):
        with self.assertRaises(ValueError):
            validate_sample(sample(run_index=0))

    def test_a_non_integer_run_index_raises(self):
        with self.assertRaises(ValueError):
            validate_sample(sample(run_index=1.5))

    def test_a_non_boolean_visual_result_raises(self):
        with self.assertRaises(ValueError):
            validate_sample(sample(visual="ok"))

    def test_a_negative_force_raises(self):
        with self.assertRaises(ValueError):
            validate_sample(sample(force=-1.0))


class TestSampleGrading(unittest.TestCase):
    def test_a_good_sample_passes_on_all_three_measures(self):
        graded = grade_sample(sample(), spec())
        self.assertTrue(graded["pass"])
        self.assertEqual(graded["reasons"], [])

    def test_a_crimp_height_exactly_on_the_lower_bound_passes(self):
        graded = grade_sample(sample(height=1.30), spec())
        self.assertTrue(graded["height_pass"])

    def test_a_crimp_height_exactly_on_the_upper_bound_passes(self):
        graded = grade_sample(sample(height=1.50), spec())
        self.assertTrue(graded["height_pass"])

    def test_a_crimp_height_above_the_window_fails(self):
        graded = grade_sample(sample(height=1.62), spec())
        self.assertFalse(graded["pass"])
        self.assertIn("crimp-height-outside-the-window", graded["reasons"])

    def test_a_force_exactly_on_the_minimum_passes(self):
        self.assertTrue(grade_sample(sample(force=90.0), spec())["force_pass"])

    def test_a_good_height_does_not_rescue_a_weak_pull(self):
        graded = grade_sample(sample(force=61.0), spec())
        self.assertTrue(graded["height_pass"])
        self.assertFalse(graded["pass"])

    def test_a_failed_visual_fails_a_dimensionally_perfect_sample(self):
        graded = grade_sample(sample(visual=False), spec())
        self.assertTrue(graded["height_pass"])
        self.assertFalse(graded["pass"])


class TestRunGrading(unittest.TestCase):
    def test_samples_are_grouped_by_their_setup_run(self):
        runs = group_samples_by_run(campaign())
        self.assertEqual(sorted(runs), [1, 2, 3])
        self.assertEqual(len(runs[1]), 3)

    def test_an_empty_campaign_raises(self):
        with self.assertRaises(ValueError):
            group_samples_by_run([])

    def test_a_full_conforming_run_conforms(self):
        result = grade_run([sample(), sample(), sample()], spec())
        self.assertTrue(result["conforming"])

    def test_a_short_run_does_not_conform(self):
        result = grade_run([sample(), sample()], spec())
        self.assertFalse(result["conforming"])
        self.assertIn(
            "fewer-samples-than-the-declared-run-size", result["reasons"]
        )

    def test_one_bad_sample_takes_the_whole_run_out(self):
        result = grade_run(
            [sample(), sample(), sample(force=20.0)], spec()
        )
        self.assertFalse(result["conforming"])
        self.assertEqual(result["failures"], 1)


class TestConsecutiveRuns(unittest.TestCase):
    def test_three_consecutive_conforming_runs_count_as_three(self):
        results = {
            1: {"conforming": True},
            2: {"conforming": True},
            3: {"conforming": True},
        }
        self.assertEqual(longest_consecutive_conforming(results), 3)

    def test_a_failed_run_breaks_the_streak(self):
        results = {
            1: {"conforming": True},
            2: {"conforming": False},
            3: {"conforming": True},
            4: {"conforming": True},
        }
        self.assertEqual(longest_consecutive_conforming(results), 2)

    def test_a_gap_in_the_run_indices_breaks_the_streak(self):
        results = {
            1: {"conforming": True},
            2: {"conforming": True},
            7: {"conforming": True},
        }
        self.assertEqual(longest_consecutive_conforming(results), 2)

    def test_an_empty_run_set_raises(self):
        with self.assertRaises(ValueError):
            longest_consecutive_conforming({})


class TestCentring(unittest.TestCase):
    def test_a_campaign_at_the_window_centre_is_centred(self):
        centring = process_centring(campaign(height=1.40), spec())
        self.assertAlmostEqual(centring["mean_height_mm"], 1.40, places=9)
        self.assertTrue(centring["centred"])

    def test_a_campaign_hugging_the_upper_bound_is_not_centred(self):
        self.assertFalse(
            process_centring(campaign(height=1.49), spec())["centred"]
        )

    def test_a_campaign_exactly_on_the_centred_band_edge_still_counts(self):
        centring = process_centring(campaign(height=1.45), spec())
        self.assertAlmostEqual(centring["window_centre_mm"], 1.40, places=9)
        self.assertTrue(centring["centred"])


class TestQualificationVerdict(unittest.TestCase):
    def test_a_clean_campaign_qualifies(self):
        report = assess_qualification(spec(), campaign())
        self.assertEqual(report["verdict"], QUALIFIED)
        self.assertEqual(report["consecutive_conforming_runs"], 3)

    def test_one_good_batch_does_not_qualify(self):
        report = assess_qualification(spec(), campaign(runs=(1,)))
        self.assertEqual(report["verdict"], NOT_QUALIFIED)
        self.assertIn("too-few-consecutive-conforming-runs", report["reasons"])

    def test_good_runs_cherry_picked_around_a_bad_one_do_not_qualify(self):
        made = campaign(runs=(1, 3, 4))
        report = assess_qualification(spec(), made)
        self.assertEqual(report["verdict"], NOT_QUALIFIED)

    def test_an_edge_hugging_but_conforming_campaign_qualifies_with_a_finding(self):
        report = assess_qualification(spec(), campaign(height=1.49))
        self.assertEqual(report["verdict"], CONDITIONAL)
        self.assertTrue(report["qualified"])
        self.assertIn(
            "process-centred-near-a-crimp-height-window-edge", report["findings"]
        )

    def test_a_non_conforming_run_names_its_index_in_the_reasons(self):
        made = campaign(runs=(1, 2))
        made.append(sample(run_index=3, force=10.0))
        made.append(sample(run_index=3))
        made.append(sample(run_index=3))
        report = assess_qualification(spec(), made)
        self.assertTrue(
            any(r.startswith("run-3-") for r in report["reasons"])
        )

    def test_the_combination_names_terminal_conductor_and_setting(self):
        report = assess_qualification(spec(), campaign())
        self.assertIn("M39029-58-360", report["combination"])
        self.assertIn("selector-5", report["combination"])


class TestRequalification(unittest.TestCase):
    def test_a_fresh_qualification_is_not_due(self):
        due = requalification_due(spec(), "2026-06-01", "2026-09-19")
        self.assertFalse(due["due"])

    def test_an_elapsed_validity_period_falls_due(self):
        due = requalification_due(spec(), "2024-01-01", "2026-09-19")
        self.assertTrue(due["due"])
        self.assertIn("validity-period-elapsed", due["reasons"])

    def test_the_last_day_of_validity_is_still_inside_it(self):
        due = requalification_due(spec(), "2025-09-19", "2026-09-19")
        self.assertEqual(due["elapsed_days"], 365)
        self.assertFalse(due["due"])

    def test_a_declared_change_falls_due_inside_the_validity_period(self):
        due = requalification_due(
            spec(), "2026-06-01", "2026-09-19", ["die-regrind"]
        )
        self.assertTrue(due["due"])
        self.assertIn("declared-trigger-die-regrind", due["reasons"])

    def test_an_undeclared_change_does_not_fall_due_on_its_own(self):
        due = requalification_due(
            spec(), "2026-06-01", "2026-09-19", ["bench-moved-to-another-room"]
        )
        self.assertFalse(due["due"])

    def test_a_check_date_before_the_qualification_raises(self):
        with self.assertRaises(ValueError):
            requalification_due(spec(), "2026-09-19", "2026-06-01")

    def test_a_non_list_change_set_raises(self):
        with self.assertRaises(ValueError):
            requalification_due(spec(), "2026-06-01", "2026-09-19", "die-regrind")


if __name__ == "__main__":
    unittest.main()
