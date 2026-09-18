"""Contract tests for the ECSS-Q-ST-70-29 odour-assessment logic."""

import unittest

from q7029_odour_assessment_logic import (
    DEFAULT_ACCEPTANCE_RATING,
    SCALE_MAX,
    VERDICT_ACCEPTABLE,
    VERDICT_NOT_ACCEPTABLE,
    VERDICT_NOT_GRADED,
    assess_odour,
    grade_mean,
    mean_rating,
    qualified_scores,
    score_dispersion,
    validate_entry,
    validate_score,
    veto_scores,
)


def sheet(scores, qualified=None):
    qualified = qualified or {}
    return [
        {"judge": "j%d" % (i + 1), "score": s, "qualified": qualified.get(i + 1, True)}
        for i, s in enumerate(scores)
    ]


class ScaleTests(unittest.TestCase):
    def test_whole_step_accepted(self):
        self.assertAlmostEqual(validate_score(2.0), 2.0, places=9)

    def test_half_step_accepted(self):
        self.assertAlmostEqual(validate_score(1.5), 1.5, places=9)

    def test_scale_floor_accepted(self):
        self.assertAlmostEqual(validate_score(0.0), 0.0, places=9)

    def test_scale_ceiling_accepted(self):
        self.assertAlmostEqual(validate_score(SCALE_MAX), 4.0, places=9)

    def test_score_above_the_scale_rejected(self):
        with self.assertRaises(ValueError):
            validate_score(5.0)

    def test_negative_score_rejected(self):
        with self.assertRaises(ValueError):
            validate_score(-0.5)

    def test_quarter_step_rejected(self):
        with self.assertRaises(ValueError):
            validate_score(1.25)

    def test_boolean_score_rejected(self):
        with self.assertRaises(ValueError):
            validate_score(True)


class EntryTests(unittest.TestCase):
    def test_entry_is_normalised(self):
        record = validate_entry({"judge": " j1 ", "score": 2.0})
        self.assertEqual(record["judge"], "j1")
        self.assertTrue(record["qualified"])

    def test_missing_score_rejected(self):
        with self.assertRaises(ValueError):
            validate_entry({"judge": "j1"})

    def test_empty_judge_rejected(self):
        with self.assertRaises(ValueError):
            validate_entry({"judge": "  ", "score": 2.0})

    def test_non_boolean_qualification_rejected(self):
        with self.assertRaises(ValueError):
            validate_entry({"judge": "j1", "score": 2.0, "qualified": "yes"})


class QualificationTests(unittest.TestCase):
    def test_unqualified_judges_are_dropped(self):
        kept, dropped = qualified_scores(sheet([1.0, 2.0, 3.0], {2: False}))
        self.assertEqual(len(kept), 2)
        self.assertEqual(dropped, ["j2"])

    def test_all_qualified_drops_nobody(self):
        kept, dropped = qualified_scores(sheet([1.0, 2.0]))
        self.assertEqual(len(kept), 2)
        self.assertEqual(dropped, [])

    def test_duplicate_judge_rejected(self):
        entries = [{"judge": "j1", "score": 1.0}, {"judge": "j1", "score": 2.0}]
        with self.assertRaises(ValueError):
            qualified_scores(entries)

    def test_empty_sheet_rejected(self):
        with self.assertRaises(ValueError):
            qualified_scores([])


class StatisticTests(unittest.TestCase):
    def test_mean_of_a_uniform_panel(self):
        self.assertAlmostEqual(mean_rating([2.0, 2.0, 2.0]), 2.0, places=9)

    def test_mean_of_a_mixed_panel(self):
        self.assertAlmostEqual(mean_rating([1.0, 2.0, 3.0, 2.0]), 2.0, places=9)

    def test_mean_of_an_empty_panel_rejected(self):
        with self.assertRaises(ValueError):
            mean_rating([])

    def test_dispersion_of_an_agreed_panel_is_zero(self):
        self.assertAlmostEqual(score_dispersion([2.0, 2.0, 2.0, 2.0]), 0.0, places=9)

    def test_dispersion_of_a_split_panel(self):
        # sample standard deviation of 0, 4 is sqrt(8) = 2.828...
        self.assertAlmostEqual(score_dispersion([0.0, 4.0]), 8.0 ** 0.5, places=9)

    def test_dispersion_needs_two_scores(self):
        with self.assertRaises(ValueError):
            score_dispersion([2.0])

    def test_veto_picks_the_top_of_scale_judges(self):
        kept, _ = qualified_scores(sheet([1.0, 4.0, 2.0]))
        self.assertEqual(veto_scores(kept), ["j2"])

    def test_no_veto_below_the_top_of_scale(self):
        kept, _ = qualified_scores(sheet([1.0, 3.5, 2.0]))
        self.assertEqual(veto_scores(kept), [])


class GradeMeanTests(unittest.TestCase):
    def test_mean_below_the_rating_passes(self):
        self.assertTrue(grade_mean(1.5))

    def test_mean_exactly_on_the_rating_passes(self):
        self.assertAlmostEqual(DEFAULT_ACCEPTANCE_RATING, 2.5, places=9)
        self.assertTrue(grade_mean(DEFAULT_ACCEPTANCE_RATING))

    def test_mean_above_the_rating_fails(self):
        self.assertFalse(grade_mean(3.0))

    def test_rating_outside_the_scale_rejected(self):
        with self.assertRaises(ValueError):
            grade_mean(2.0, 9.0)


class AssessOdourTests(unittest.TestCase):
    def test_agreed_low_panel_is_acceptable(self):
        result = assess_odour({"entries": sheet([1.0, 1.5, 1.0, 1.5, 2.0])})
        self.assertEqual(result["verdict"], VERDICT_ACCEPTABLE)
        self.assertTrue(result["acceptable"])
        self.assertEqual(result["findings"], [])

    def test_mean_and_dispersion_are_reported(self):
        result = assess_odour({"entries": sheet([2.0, 2.0, 2.0, 2.0, 2.0])})
        self.assertAlmostEqual(result["mean_rating"], 2.0, places=9)
        self.assertAlmostEqual(result["dispersion"], 0.0, places=9)

    def test_mean_exactly_on_the_rating_is_acceptable(self):
        result = assess_odour({"entries": sheet([2.5, 2.5, 2.5, 2.5, 2.5])})
        self.assertAlmostEqual(result["mean_rating"], result["acceptance_rating"], places=9)
        self.assertTrue(result["acceptable"])

    def test_mean_above_the_rating_is_not_acceptable(self):
        result = assess_odour({"entries": sheet([3.0, 3.0, 3.0, 3.0, 3.0])})
        self.assertEqual(result["verdict"], VERDICT_NOT_ACCEPTABLE)
        self.assertEqual(len(result["findings"]), 1)

    def test_split_panel_fails_on_dispersion_despite_a_low_mean(self):
        result = assess_odour({"entries": sheet([0.0, 0.0, 0.0, 3.5, 3.5])})
        self.assertTrue(grade_mean(result["mean_rating"], result["acceptance_rating"]))
        self.assertFalse(result["acceptable"])
        self.assertTrue(any("dispersion" in f for f in result["findings"]))

    def test_single_top_of_scale_score_vetoes_a_low_mean(self):
        result = assess_odour({"entries": sheet([0.0, 0.0, 0.0, 0.0, 4.0]),
                               "dispersion_limit": 4.0})
        self.assertEqual(result["veto_judges"], ["j5"])
        self.assertFalse(result["acceptable"])

    def test_short_qualified_panel_is_not_graded(self):
        result = assess_odour({"entries": sheet([1.0, 1.0, 1.0, 1.0, 1.0],
                                                {1: False, 2: False})})
        self.assertEqual(result["verdict"], VERDICT_NOT_GRADED)
        self.assertIsNone(result["mean_rating"])
        self.assertEqual(result["qualified_panel_size"], 3)

    def test_dropped_judges_raise_a_finding(self):
        result = assess_odour({"entries": sheet([1.0, 1.0, 1.0, 1.0, 1.0, 1.0],
                                                {3: False})})
        self.assertEqual(result["dropped_judges"], ["j3"])
        self.assertTrue(any("not currently qualified" in f for f in result["findings"]))

    def test_dropped_judge_score_does_not_move_the_mean(self):
        result = assess_odour({"entries": sheet([1.0, 1.0, 1.0, 1.0, 1.0, 4.0],
                                                {6: False})})
        self.assertAlmostEqual(result["mean_rating"], 1.0, places=9)
        self.assertEqual(result["veto_judges"], [])

    def test_missing_entries_key_rejected(self):
        with self.assertRaises(ValueError):
            assess_odour({"min_panel": 5})

    def test_non_mapping_spec_rejected(self):
        with self.assertRaises(ValueError):
            assess_odour(["entries"])

    def test_min_panel_below_two_rejected(self):
        with self.assertRaises(ValueError):
            assess_odour({"entries": sheet([1.0, 1.0]), "min_panel": 1})

    def test_non_positive_dispersion_limit_rejected(self):
        with self.assertRaises(ValueError):
            assess_odour({"entries": sheet([1.0, 1.0]), "dispersion_limit": 0.0})


if __name__ == "__main__":
    unittest.main()
