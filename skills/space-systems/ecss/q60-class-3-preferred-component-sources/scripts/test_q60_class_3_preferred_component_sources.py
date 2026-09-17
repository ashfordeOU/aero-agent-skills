#!/usr/bin/env python3
"""Contract test for the Class 3 preferred component sources (offline)."""

import copy
import unittest

from q60_class_3_preferred_component_sources_logic import (
    ACTIVITY_EFFORT,
    ACTIVITY_LEAD_WEEKS,
    PREFERRED_EFFORT_CEILING,
    QUALIFICATION_ACTIVITIES,
    SOURCE_ACCEPTABLE_WITH_EFFORT,
    SOURCE_INADMISSIBLE,
    SOURCE_NOT_SCHEDULABLE,
    SOURCE_PREFERRED,
    SOURCE_TIERS,
    TOTAL_EFFORT,
    assess_candidate,
    dominant_activity,
    effort_index,
    outstanding_activities,
    qualification_effort,
    qualification_lead_weeks,
    rank_candidates,
    required_activities,
    select_preferred_source,
)

QUALIFIED = {
    "reference": "qpl-ldo-regulator",
    "source_tier": "qualified-to-a-recognised-standard",
    "evidence_on_file": ["lot-traceability-reconstruction"],
    "traceable_to_single_lot": True,
}

CATALOGUE = {
    "reference": "space-catalogue-ldo-regulator",
    "source_tier": "manufacturer-space-catalogue",
    "evidence_on_file": [],
    "traceable_to_single_lot": True,
}

AUTOMOTIVE = {
    "reference": "automotive-ldo-regulator",
    "source_tier": "automotive-or-industrial-qualified",
    "evidence_on_file": ["lot-traceability-reconstruction"],
    "traceable_to_single_lot": True,
}

COMMERCIAL = {
    "reference": "catalogue-distributor-ldo-regulator",
    "source_tier": "commercial-uncharacterised",
    "evidence_on_file": [],
    "traceable_to_single_lot": False,
}


def _shortlist(*candidates):
    return {
        "function": "3v3-point-of-load-regulation",
        "weeks_available": 40.0,
        "candidates": [copy.deepcopy(candidate) for candidate in candidates],
    }


class ActivityTableTests(unittest.TestCase):
    def test_every_activity_carries_an_effort_and_a_lead_time(self):
        self.assertEqual(set(ACTIVITY_EFFORT), set(QUALIFICATION_ACTIVITIES))
        self.assertEqual(set(ACTIVITY_LEAD_WEEKS), set(QUALIFICATION_ACTIVITIES))

    def test_total_effort_is_the_sum_of_the_activities(self):
        self.assertAlmostEqual(TOTAL_EFFORT, sum(ACTIVITY_EFFORT.values()), places=9)

    def test_a_qualified_source_owes_least(self):
        self.assertLess(
            len(required_activities("qualified-to-a-recognised-standard")),
            len(required_activities("commercial-uncharacterised")),
        )

    def test_an_uncharacterised_source_owes_everything(self):
        self.assertEqual(
            set(required_activities("commercial-uncharacterised")),
            set(QUALIFICATION_ACTIVITIES),
        )

    def test_requirements_come_back_in_activity_order(self):
        for tier in SOURCE_TIERS:
            activities = required_activities(tier)
            order = [QUALIFICATION_ACTIVITIES.index(a) for a in activities]
            self.assertEqual(order, sorted(order))

    def test_unknown_tier_rejected(self):
        with self.assertRaises(ValueError):
            required_activities("bought-on-an-auction-site")


class OutstandingWorkTests(unittest.TestCase):
    def test_evidence_removes_an_activity_from_the_list(self):
        self.assertEqual(outstanding_activities(QUALIFIED), ())

    def test_evidence_does_not_reduce_an_activity_it_does_not_cover(self):
        outstanding = outstanding_activities(AUTOMOTIVE)
        self.assertIn("radiation-characterisation", outstanding)
        self.assertNotIn("lot-traceability-reconstruction", outstanding)

    def test_effort_is_the_weighted_sum_of_what_is_owed(self):
        expected = sum(
            ACTIVITY_EFFORT[activity] for activity in outstanding_activities(CATALOGUE)
        )
        self.assertAlmostEqual(qualification_effort(CATALOGUE), expected, places=9)

    def test_lead_time_adds_up_because_upscreening_runs_on_one_lot(self):
        expected = sum(
            ACTIVITY_LEAD_WEEKS[activity]
            for activity in outstanding_activities(CATALOGUE)
        )
        self.assertAlmostEqual(qualification_lead_weeks(CATALOGUE), expected, places=9)

    def test_effort_index_is_a_share_of_a_wholly_uncharacterised_source(self):
        self.assertAlmostEqual(
            effort_index(CATALOGUE),
            qualification_effort(CATALOGUE) / TOTAL_EFFORT,
            places=9,
        )

    def test_a_source_owing_nothing_has_no_dominant_activity(self):
        self.assertIsNone(dominant_activity(QUALIFIED))

    def test_the_dominant_activity_is_the_costliest_one_owed(self):
        self.assertEqual(dominant_activity(CATALOGUE), "radiation-characterisation")

    def test_unknown_evidence_activity_rejected(self):
        candidate = dict(CATALOGUE, evidence_on_file=["astrology"])
        with self.assertRaises(ValueError):
            outstanding_activities(candidate)

    def test_a_bare_string_of_evidence_rejected(self):
        candidate = dict(CATALOGUE, evidence_on_file="burn-in")
        with self.assertRaises(ValueError):
            outstanding_activities(candidate)

    def test_missing_traceability_flag_rejected(self):
        candidate = dict(CATALOGUE)
        del candidate["traceable_to_single_lot"]
        with self.assertRaises(ValueError):
            outstanding_activities(candidate)

    def test_unnamed_candidate_rejected(self):
        candidate = dict(CATALOGUE)
        del candidate["reference"]
        with self.assertRaises(ValueError):
            outstanding_activities(candidate)


class CandidateGradingTests(unittest.TestCase):
    def test_a_fully_qualified_source_is_preferred(self):
        graded = assess_candidate(QUALIFIED, 40.0)
        self.assertEqual(graded["verdict"], SOURCE_PREFERRED)
        self.assertAlmostEqual(graded["effort_index"], 0.0, places=9)

    def test_a_catalogue_source_is_acceptable_with_added_qualification(self):
        graded = assess_candidate(CATALOGUE, 40.0)
        self.assertEqual(graded["verdict"], SOURCE_ACCEPTABLE_WITH_EFFORT)
        self.assertTrue(graded["selectable"])

    def test_an_untraceable_source_is_inadmissible_whatever_the_schedule(self):
        graded = assess_candidate(COMMERCIAL, 400.0)
        self.assertEqual(graded["verdict"], SOURCE_INADMISSIBLE)
        self.assertFalse(graded["selectable"])

    def test_a_programme_longer_than_the_schedule_is_not_schedulable(self):
        graded = assess_candidate(AUTOMOTIVE, 4.0)
        self.assertEqual(graded["verdict"], SOURCE_NOT_SCHEDULABLE)
        self.assertFalse(graded["selectable"])

    def test_a_programme_landing_exactly_on_the_date_still_fits(self):
        weeks = qualification_lead_weeks(CATALOGUE)
        graded = assess_candidate(CATALOGUE, weeks)
        self.assertTrue(graded["schedulable"])
        self.assertAlmostEqual(graded["lead_time_weeks"], weeks, places=9)

    def test_the_effort_ceiling_separates_preferred_from_acceptable(self):
        self.assertGreater(effort_index(CATALOGUE), PREFERRED_EFFORT_CEILING)
        self.assertLess(effort_index(QUALIFIED), PREFERRED_EFFORT_CEILING)

    def test_zero_weeks_available_rejected(self):
        with self.assertRaises(ValueError):
            assess_candidate(CATALOGUE, 0.0)

    def test_non_numeric_schedule_rejected(self):
        with self.assertRaises(ValueError):
            assess_candidate(CATALOGUE, "soon")


class RankingTests(unittest.TestCase):
    def test_the_least_added_work_ranks_first(self):
        outcome = rank_candidates(
            [copy.deepcopy(AUTOMOTIVE), copy.deepcopy(CATALOGUE), copy.deepcopy(QUALIFIED)],
            40.0,
        )
        self.assertEqual(
            [entry["reference"] for entry in outcome["ranked"]],
            [QUALIFIED["reference"], CATALOGUE["reference"], AUTOMOTIVE["reference"]],
        )

    def test_inadmissible_candidates_never_reach_the_ranking(self):
        outcome = rank_candidates(
            [copy.deepcopy(COMMERCIAL), copy.deepcopy(CATALOGUE)], 40.0
        )
        self.assertEqual(len(outcome["ranked"]), 1)
        self.assertEqual(len(outcome["graded"]), 2)

    def test_a_duplicate_candidate_rejected(self):
        with self.assertRaises(ValueError):
            rank_candidates([copy.deepcopy(CATALOGUE), copy.deepcopy(CATALOGUE)], 40.0)

    def test_an_empty_shortlist_rejected(self):
        with self.assertRaises(ValueError):
            rank_candidates([], 40.0)

    def test_a_tie_on_effort_is_broken_by_lead_time_then_by_name(self):
        first = dict(CATALOGUE, reference="zeta-catalogue-part")
        second = dict(CATALOGUE, reference="alpha-catalogue-part")
        outcome = rank_candidates([first, second], 40.0)
        self.assertEqual(outcome["ranked"][0]["reference"], "alpha-catalogue-part")


class SelectionTests(unittest.TestCase):
    def test_the_shortlist_picks_the_cheapest_admissible_source(self):
        result = select_preferred_source(_shortlist(AUTOMOTIVE, CATALOGUE, QUALIFIED))
        self.assertEqual(result["selected"], QUALIFIED["reference"])
        self.assertEqual(result["runner_up"], CATALOGUE["reference"])
        self.assertTrue(result["acceptable"])

    def test_the_margin_is_the_effort_between_the_top_two(self):
        result = select_preferred_source(_shortlist(CATALOGUE, QUALIFIED))
        self.assertAlmostEqual(
            result["effort_margin"], qualification_effort(CATALOGUE), places=9
        )

    def test_a_single_candidate_has_no_runner_up(self):
        result = select_preferred_source(_shortlist(CATALOGUE))
        self.assertIsNone(result["runner_up"])
        self.assertIsNone(result["effort_margin"])

    def test_an_untraceable_candidate_is_reported_as_a_finding(self):
        result = select_preferred_source(_shortlist(COMMERCIAL, CATALOGUE))
        self.assertTrue(any("single production lot" in text for text in result["findings"]))

    def test_a_shortlist_of_untraceable_sources_selects_nothing(self):
        result = select_preferred_source(_shortlist(COMMERCIAL))
        self.assertIsNone(result["selected"])
        self.assertEqual(result["verdict"], SOURCE_INADMISSIBLE)
        self.assertFalse(result["acceptable"])

    def test_a_shortlist_that_cannot_fit_the_schedule_selects_nothing(self):
        case = _shortlist(AUTOMOTIVE, CATALOGUE)
        case["weeks_available"] = 2.0
        result = select_preferred_source(case)
        self.assertIsNone(result["selected"])
        self.assertEqual(result["verdict"], SOURCE_NOT_SCHEDULABLE)

    def test_each_outstanding_activity_becomes_an_action(self):
        result = select_preferred_source(_shortlist(CATALOGUE))
        self.assertEqual(
            len(result["actions"]), len(outstanding_activities(CATALOGUE))
        )

    def test_a_tie_between_the_top_two_is_reported(self):
        first = dict(CATALOGUE, reference="zeta-catalogue-part")
        second = dict(CATALOGUE, reference="alpha-catalogue-part")
        result = select_preferred_source(_shortlist(first, second))
        self.assertTrue(any("same effort" in text for text in result["findings"]))

    def test_missing_function_rejected(self):
        case = _shortlist(CATALOGUE)
        del case["function"]
        with self.assertRaises(ValueError):
            select_preferred_source(case)

    def test_non_mapping_case_rejected(self):
        with self.assertRaises(ValueError):
            select_preferred_source([CATALOGUE])


if __name__ == "__main__":
    unittest.main(verbosity=0)
