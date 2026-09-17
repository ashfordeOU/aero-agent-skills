#!/usr/bin/env python3
"""Contract test for the Class 2 preferred component sources leaf (offline)."""

import copy
import unittest

from q60_class_2_preferred_component_sources_logic import (
    ACCEPTED_DEPARTURE_REASONS,
    CANDIDATE_CAMPAIGN,
    CANDIDATE_READY,
    CANDIDATE_UPSCREENING,
    DEFAULT_CAMPAIGN_INDEX_CEILING,
    DEFAULT_STEP_CATALOGUE,
    PACKAGE_STYLES,
    SELECTION_JUSTIFIED,
    SELECTION_LEAST_EFFORT,
    SELECTION_UNJUSTIFIED,
    applicable_steps,
    assess_selection,
    grade_candidate,
    rank_candidates,
    residual_qualification_burden,
    validate_step_catalogue,
)

HERMETIC_STEPS = applicable_steps("hermetic")
PLASTIC_STEPS = applicable_steps("non-hermetic")

READY_PART = {
    "part_reference": "u-2001",
    "package_style": "hermetic",
    "evidence_held": list(HERMETIC_STEPS),
}

NEAR_READY_PART = {
    "part_reference": "u-2002",
    "package_style": "hermetic",
    "evidence_held": [s for s in HERMETIC_STEPS if s != "lot-traceability-record"],
}

BARE_PART = {
    "part_reference": "u-2003",
    "package_style": "hermetic",
    "evidence_held": [],
}

SELECTION = {
    "slot": "bus-controller",
    "chosen_reference": "u-2001",
    "candidates": [READY_PART, NEAR_READY_PART, BARE_PART],
}


def _candidate(base, **overrides):
    item = copy.deepcopy(dict(base))
    item.update(overrides)
    return item


def _selection(**overrides):
    item = copy.deepcopy(SELECTION)
    item.update(overrides)
    return item


class CatalogueTests(unittest.TestCase):
    def test_default_catalogue_validates(self):
        self.assertIs(
            validate_step_catalogue(DEFAULT_STEP_CATALOGUE), DEFAULT_STEP_CATALOGUE
        )

    def test_empty_catalogue_rejected(self):
        with self.assertRaises(ValueError):
            validate_step_catalogue({})

    def test_catalogue_entry_without_effort_rejected(self):
        broken = copy.deepcopy(DEFAULT_STEP_CATALOGUE)
        del broken["burn-in-screen"]["effort"]
        with self.assertRaises(ValueError):
            validate_step_catalogue(broken)

    def test_zero_effort_step_rejected(self):
        broken = copy.deepcopy(DEFAULT_STEP_CATALOGUE)
        broken["burn-in-screen"]["effort"] = 0.0
        with self.assertRaises(ValueError):
            validate_step_catalogue(broken)

    def test_negative_lead_rejected(self):
        broken = copy.deepcopy(DEFAULT_STEP_CATALOGUE)
        broken["burn-in-screen"]["lead_weeks"] = -1.0
        with self.assertRaises(ValueError):
            validate_step_catalogue(broken)

    def test_unknown_package_style_in_catalogue_rejected(self):
        broken = copy.deepcopy(DEFAULT_STEP_CATALOGUE)
        broken["burn-in-screen"]["package_styles"] = ("potted",)
        with self.assertRaises(ValueError):
            validate_step_catalogue(broken)

    def test_fractional_sample_count_rejected(self):
        broken = copy.deepcopy(DEFAULT_STEP_CATALOGUE)
        broken["destructive-physical-analysis"]["samples"] = 6.5
        with self.assertRaises(ValueError):
            validate_step_catalogue(broken)


class ApplicabilityTests(unittest.TestCase):
    def test_seal_test_applies_to_hermetic_only(self):
        self.assertIn("seal-and-leak-screen", HERMETIC_STEPS)
        self.assertNotIn("seal-and-leak-screen", PLASTIC_STEPS)

    def test_moisture_characterisation_applies_to_plastic_only(self):
        self.assertIn("moisture-sensitivity-characterisation", PLASTIC_STEPS)
        self.assertNotIn("moisture-sensitivity-characterisation", HERMETIC_STEPS)

    def test_shared_steps_appear_on_both_styles(self):
        for step in ("burn-in-screen", "radiation-lot-acceptance"):
            self.assertIn(step, HERMETIC_STEPS)
            self.assertIn(step, PLASTIC_STEPS)

    def test_applicable_steps_are_ordered(self):
        self.assertEqual(list(HERMETIC_STEPS), sorted(HERMETIC_STEPS))

    def test_both_package_styles_are_scoped(self):
        for style in PACKAGE_STYLES:
            self.assertTrue(applicable_steps(style))

    def test_unknown_style_rejected(self):
        with self.assertRaises(ValueError):
            applicable_steps("potted")


class BurdenTests(unittest.TestCase):
    def test_fully_evidenced_source_leaves_nothing(self):
        burden = residual_qualification_burden(READY_PART)
        self.assertEqual(burden["missing_steps"], ())
        self.assertAlmostEqual(burden["residual_effort"], 0.0, places=9)
        self.assertAlmostEqual(burden["residual_index"], 0.0, places=9)

    def test_one_missing_step_costs_its_own_effort(self):
        burden = residual_qualification_burden(NEAR_READY_PART)
        self.assertEqual(burden["missing_steps"], ("lot-traceability-record",))
        self.assertAlmostEqual(burden["residual_effort"], 2.0, places=9)

    def test_bare_source_leaves_the_whole_applicable_set(self):
        burden = residual_qualification_burden(BARE_PART)
        self.assertEqual(burden["missing_steps"], HERMETIC_STEPS)
        self.assertAlmostEqual(
            burden["residual_index"], 1.0, places=9
        )

    def test_campaign_lead_is_the_longest_missing_step_not_their_sum(self):
        candidate = _candidate(
            BARE_PART,
            evidence_held=[
                s
                for s in HERMETIC_STEPS
                if s not in ("burn-in-screen", "radiation-lot-acceptance")
            ],
        )
        burden = residual_qualification_burden(candidate)
        self.assertAlmostEqual(burden["campaign_lead_weeks"], 12.0, places=9)

    def test_sample_devices_are_summed_across_missing_steps(self):
        candidate = _candidate(
            BARE_PART,
            evidence_held=[
                s
                for s in HERMETIC_STEPS
                if s
                not in ("destructive-physical-analysis", "radiation-lot-acceptance")
            ],
        )
        burden = residual_qualification_burden(candidate)
        self.assertEqual(burden["sample_devices_consumed"], 17)

    def test_a_fully_evidenced_source_needs_no_campaign_weeks(self):
        burden = residual_qualification_burden(READY_PART)
        self.assertAlmostEqual(burden["campaign_lead_weeks"], 0.0, places=9)

    def test_evidence_outside_the_package_scope_is_not_credited(self):
        candidate = _candidate(
            BARE_PART,
            package_style="non-hermetic",
            evidence_held=["seal-and-leak-screen"],
        )
        burden = residual_qualification_burden(candidate)
        self.assertEqual(burden["evidence_outside_scope"], ("seal-and-leak-screen",))
        self.assertAlmostEqual(burden["residual_index"], 1.0, places=9)

    def test_the_two_styles_are_scored_against_their_own_totals(self):
        hermetic = residual_qualification_burden(BARE_PART)
        plastic = residual_qualification_burden(
            _candidate(BARE_PART, package_style="non-hermetic")
        )
        self.assertEqual(len(hermetic["applicable_steps"]), 8)
        self.assertEqual(len(plastic["applicable_steps"]), 7)
        self.assertAlmostEqual(hermetic["residual_index"], 1.0, places=9)
        self.assertAlmostEqual(plastic["residual_index"], 1.0, places=9)

    def test_evidence_for_an_unknown_step_rejected(self):
        with self.assertRaises(ValueError):
            residual_qualification_burden(
                _candidate(BARE_PART, evidence_held=["vibration-screen"])
            )

    def test_evidence_held_must_be_a_sequence(self):
        with self.assertRaises(ValueError):
            residual_qualification_burden(
                _candidate(BARE_PART, evidence_held="burn-in-screen")
            )

    def test_candidate_without_a_reference_rejected(self):
        with self.assertRaises(ValueError):
            residual_qualification_burden(_candidate(BARE_PART, part_reference=" "))

    def test_non_mapping_candidate_rejected(self):
        with self.assertRaises(ValueError):
            residual_qualification_burden("u-2003")


class DispositionTests(unittest.TestCase):
    def test_fully_evidenced_source_arrives_qualified(self):
        self.assertEqual(grade_candidate(READY_PART)["disposition"], CANDIDATE_READY)

    def test_small_gap_is_an_upscreening_run(self):
        self.assertEqual(
            grade_candidate(NEAR_READY_PART)["disposition"], CANDIDATE_UPSCREENING
        )

    def test_large_gap_is_a_full_campaign(self):
        self.assertEqual(grade_candidate(BARE_PART)["disposition"], CANDIDATE_CAMPAIGN)

    def test_an_index_exactly_on_the_ceiling_stays_an_upscreening_run(self):
        burden = grade_candidate(NEAR_READY_PART)
        ceiling = burden["residual_index"]
        graded = grade_candidate(NEAR_READY_PART, DEFAULT_STEP_CATALOGUE, ceiling)
        self.assertAlmostEqual(graded["residual_index"], ceiling, places=9)
        self.assertEqual(graded["disposition"], CANDIDATE_UPSCREENING)

    def test_campaign_finding_names_the_part(self):
        graded = grade_candidate(BARE_PART)
        self.assertTrue(any("u-2003" in f for f in graded["findings"]))

    def test_out_of_scope_evidence_raises_a_finding(self):
        graded = grade_candidate(
            _candidate(
                BARE_PART,
                package_style="non-hermetic",
                evidence_held=["particle-impact-noise-screen"],
            )
        )
        self.assertTrue(
            any("particle-impact-noise-screen" in f for f in graded["findings"])
        )

    def test_ceiling_above_unity_rejected(self):
        with self.assertRaises(ValueError):
            grade_candidate(BARE_PART, DEFAULT_STEP_CATALOGUE, 1.4)

    def test_default_ceiling_sits_inside_the_scale(self):
        self.assertGreater(DEFAULT_CAMPAIGN_INDEX_CEILING, 0.0)
        self.assertLess(DEFAULT_CAMPAIGN_INDEX_CEILING, 1.0)


class RankingTests(unittest.TestCase):
    def test_least_burden_ranks_first(self):
        ranked = rank_candidates([BARE_PART, NEAR_READY_PART, READY_PART])
        self.assertEqual(ranked[0]["part_reference"], "u-2001")
        self.assertEqual(ranked[-1]["part_reference"], "u-2003")

    def test_ranking_is_stable_for_equal_burdens(self):
        twin = _candidate(READY_PART, part_reference="u-2009")
        ranked = rank_candidates([twin, READY_PART])
        self.assertEqual(
            [item["part_reference"] for item in ranked], ["u-2001", "u-2009"]
        )

    def test_a_repeated_reference_rejected(self):
        with self.assertRaises(ValueError):
            rank_candidates([READY_PART, _candidate(READY_PART)])

    def test_empty_candidate_list_rejected(self):
        with self.assertRaises(ValueError):
            rank_candidates([])


class SelectionTests(unittest.TestCase):
    def test_taking_the_cheapest_source_is_the_preferred_route(self):
        result = assess_selection(SELECTION)
        self.assertEqual(result["verdict"], SELECTION_LEAST_EFFORT)
        self.assertTrue(result["preferred"])
        self.assertAlmostEqual(result["effort_penalty"], 0.0, places=9)

    def test_a_step_away_with_an_accepted_reason_is_carried(self):
        result = assess_selection(
            _selection(
                chosen_reference="u-2002",
                departure_reason="cheaper-source-obsolete",
            )
        )
        self.assertEqual(result["verdict"], SELECTION_JUSTIFIED)
        self.assertTrue(result["preferred"])
        self.assertAlmostEqual(result["effort_penalty"], 2.0, places=9)

    def test_a_step_away_with_no_reason_is_not_carried(self):
        result = assess_selection(_selection(chosen_reference="u-2002"))
        self.assertEqual(result["verdict"], SELECTION_UNJUSTIFIED)
        self.assertFalse(result["preferred"])

    def test_a_reason_outside_the_accepted_set_is_not_carried(self):
        result = assess_selection(
            _selection(
                chosen_reference="u-2003",
                departure_reason="the-buyer-preferred-it",
            )
        )
        self.assertEqual(result["verdict"], SELECTION_UNJUSTIFIED)

    def test_every_accepted_reason_carries_a_departure(self):
        for reason in ACCEPTED_DEPARTURE_REASONS:
            result = assess_selection(
                _selection(chosen_reference="u-2002", departure_reason=reason)
            )
            self.assertEqual(result["verdict"], SELECTION_JUSTIFIED)

    def test_findings_name_the_cheaper_candidate_that_was_passed_over(self):
        result = assess_selection(_selection(chosen_reference="u-2003"))
        self.assertTrue(any("u-2001" in f for f in result["findings"]))

    def test_lead_penalty_is_reported_in_weeks(self):
        result = assess_selection(_selection(chosen_reference="u-2003"))
        self.assertAlmostEqual(result["lead_penalty_weeks"], 12.0, places=9)

    def test_the_ranking_is_returned_with_the_verdict(self):
        result = assess_selection(SELECTION)
        self.assertEqual(result["ranking"], ["u-2001", "u-2002", "u-2003"])

    def test_a_chosen_part_outside_the_candidate_set_rejected(self):
        with self.assertRaises(ValueError):
            assess_selection(_selection(chosen_reference="u-9999"))

    def test_selection_without_a_slot_rejected(self):
        with self.assertRaises(ValueError):
            assess_selection(_selection(slot=""))

    def test_non_mapping_selection_rejected(self):
        with self.assertRaises(ValueError):
            assess_selection("bus-controller")


if __name__ == "__main__":
    unittest.main(verbosity=1)
