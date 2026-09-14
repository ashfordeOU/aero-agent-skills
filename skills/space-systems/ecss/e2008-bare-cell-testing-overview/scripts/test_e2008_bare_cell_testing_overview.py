#!/usr/bin/env python3
"""Contract test for the bare solar cell test programme (offline)."""

import copy
import unittest

from e2008_bare_cell_testing_overview_logic import (
    DESTRUCTIVE_ACTIVITIES,
    PROCUREMENT_MIN_SAMPLE,
    PROGRAMME_ACCEPTABLE,
    PROGRAMME_NOT_ACCEPTABLE,
    PROGRAMME_WITH_FINDINGS,
    PURPOSES,
    QUALIFICATION_MIN_SAMPLE,
    REQUIRED_ACTIVITIES,
    SPECIMEN_KINDS,
    assess_bare_cell_programme,
    ceil_sqrt,
    evaluate_activity,
    policy_sample_size,
    programme_coverage,
    qualification_share,
    specimen_allowed,
)

LOT_SIZE = 100

QUAL_ACTIVITIES = [
    {
        "name": name,
        "purpose": "qualification",
        "specimen": "qualification-lot-cell",
        "sample_size": 6,
    }
    for name in REQUIRED_ACTIVITIES["qualification"]
]

PROC_ACTIVITIES = [
    {
        "name": name,
        "purpose": "procurement",
        "specimen": "procurement-lot-sample-cell",
        "sample_size": 10,
    }
    for name in REQUIRED_ACTIVITIES["procurement"]
]

FULL_PROGRAMME = QUAL_ACTIVITIES + PROC_ACTIVITIES


def _spec(**overrides):
    item = {"lot_size": LOT_SIZE, "activities": copy.deepcopy(FULL_PROGRAMME)}
    for key, value in overrides.items():
        if value is None and key in item:
            del item[key]
        else:
            item[key] = value
    return item


def _without(name, purpose):
    return [
        copy.deepcopy(a)
        for a in FULL_PROGRAMME
        if not (a["name"] == name and a["purpose"] == purpose)
    ]


def _with_change(name, purpose, **changes):
    out = []
    for activity in copy.deepcopy(FULL_PROGRAMME):
        if activity["name"] == name and activity["purpose"] == purpose:
            activity.update(changes)
        out.append(activity)
    return out


class CeilSqrtTests(unittest.TestCase):
    def test_a_perfect_square_returns_its_exact_root(self):
        self.assertEqual(ceil_sqrt(144), 12)

    def test_one_above_a_perfect_square_rounds_up(self):
        self.assertEqual(ceil_sqrt(145), 13)

    def test_the_smallest_lot_needs_one_specimen_by_the_square_rule(self):
        self.assertEqual(ceil_sqrt(1), 1)

    def test_a_non_positive_count_is_rejected(self):
        with self.assertRaises(ValueError):
            ceil_sqrt(0)

    def test_a_float_count_is_rejected(self):
        with self.assertRaises(ValueError):
            ceil_sqrt(144.0)


class PolicySampleSizeTests(unittest.TestCase):
    def test_a_procurement_sample_grows_with_the_batch(self):
        self.assertEqual(policy_sample_size(400, "procurement"), 20)

    def test_a_small_batch_still_owes_the_procurement_floor(self):
        self.assertEqual(policy_sample_size(9, "procurement"), PROCUREMENT_MIN_SAMPLE)

    def test_a_qualification_sample_does_not_grow_with_the_batch(self):
        small = policy_sample_size(50, "qualification")
        large = policy_sample_size(5000, "qualification")
        self.assertEqual(small, QUALIFICATION_MIN_SAMPLE)
        self.assertEqual(small, large)

    def test_a_sample_floor_never_exceeds_the_lot_it_is_drawn_from(self):
        self.assertEqual(policy_sample_size(3, "qualification"), 3)

    def test_an_unknown_errand_is_rejected(self):
        with self.assertRaises(ValueError):
            policy_sample_size(100, "marketing")


class SpecimenTests(unittest.TestCase):
    def test_a_qualification_lot_cell_answers_a_qualification_question(self):
        self.assertTrue(specimen_allowed("qualification", "qualification-lot-cell")["allowed"])

    def test_a_procurement_sample_cannot_answer_a_qualification_question(self):
        result = specimen_allowed("qualification", "procurement-lot-sample-cell")
        self.assertFalse(result["allowed"])
        self.assertIn("qualification", result["reason"])

    def test_a_delivered_cell_is_never_a_test_article(self):
        for purpose in PURPOSES:
            self.assertFalse(specimen_allowed(purpose, "delivered-cell")["allowed"])

    def test_a_witness_cell_serves_either_errand(self):
        for purpose in PURPOSES:
            self.assertTrue(specimen_allowed(purpose, "witness-cell")["allowed"])

    def test_a_destructive_activity_on_a_procurement_sample_is_allowed_but_noted(self):
        result = specimen_allowed(
            "procurement", "procurement-lot-sample-cell", DESTRUCTIVE_ACTIVITIES[0]
        )
        self.assertTrue(result["allowed"])
        self.assertIn("consumes", result["reason"])

    def test_an_unknown_specimen_kind_is_rejected(self):
        with self.assertRaises(ValueError):
            specimen_allowed("qualification", "cell-from-the-drawer")

    def test_every_declared_specimen_kind_resolves(self):
        for specimen in SPECIMEN_KINDS:
            result = specimen_allowed("qualification", specimen)
            self.assertIn("allowed", result)


class ActivityTests(unittest.TestCase):
    def test_a_well_placed_activity_is_acceptable(self):
        record = evaluate_activity(QUAL_ACTIVITIES[0], LOT_SIZE)
        self.assertTrue(record["acceptable"])
        self.assertEqual(record["findings"], [])

    def test_an_undersized_sample_is_reported_against_the_policy_floor(self):
        activity = dict(PROC_ACTIVITIES[0])
        activity["sample_size"] = 4
        record = evaluate_activity(activity, LOT_SIZE)
        self.assertFalse(record["sample_adequate"])
        self.assertEqual(record["policy_sample_size"], 10)

    def test_a_sample_larger_than_the_lot_is_reported(self):
        activity = dict(PROC_ACTIVITIES[0])
        activity["sample_size"] = 500
        record = evaluate_activity(activity, LOT_SIZE)
        self.assertFalse(record["acceptable"])
        self.assertTrue(any("draws" in f for f in record["findings"]))

    def test_a_destructive_activity_on_a_delivered_cell_is_not_acceptable(self):
        activity = dict(QUAL_ACTIVITIES[0])
        activity["name"] = "thermal-cycling"
        activity["specimen"] = "delivered-cell"
        record = evaluate_activity(activity, LOT_SIZE)
        self.assertFalse(record["specimen_allowed"])
        self.assertTrue(record["destructive"])

    def test_an_activity_outside_the_required_set_is_carried_as_supplementary(self):
        activity = dict(QUAL_ACTIVITIES[0])
        activity["name"] = "photoluminescence-mapping"
        record = evaluate_activity(activity, LOT_SIZE)
        self.assertTrue(record["off_required_list"])
        self.assertTrue(record["acceptable"])

    def test_a_missing_activity_key_is_rejected(self):
        activity = dict(QUAL_ACTIVITIES[0])
        del activity["specimen"]
        with self.assertRaises(ValueError):
            evaluate_activity(activity, LOT_SIZE)

    def test_a_blank_activity_name_is_rejected(self):
        activity = dict(QUAL_ACTIVITIES[0])
        activity["name"] = "   "
        with self.assertRaises(ValueError):
            evaluate_activity(activity, LOT_SIZE)

    def test_a_zero_sample_size_is_rejected(self):
        activity = dict(QUAL_ACTIVITIES[0])
        activity["sample_size"] = 0
        with self.assertRaises(ValueError):
            evaluate_activity(activity, LOT_SIZE)


class CoverageTests(unittest.TestCase):
    def test_a_full_programme_covers_both_errands(self):
        records = [evaluate_activity(a, LOT_SIZE) for a in FULL_PROGRAMME]
        coverage = programme_coverage(records)
        self.assertAlmostEqual(coverage["qualification"]["fraction"], 1.0, places=9)
        self.assertAlmostEqual(coverage["procurement"]["fraction"], 1.0, places=9)

    def test_a_dropped_activity_is_named_in_the_missing_list(self):
        records = [evaluate_activity(a, LOT_SIZE)
                   for a in _without("reverse-bias", "qualification")]
        coverage = programme_coverage(records)
        self.assertEqual(coverage["qualification"]["missing"], ["reverse-bias"])

    def test_coverage_is_a_share_of_the_errands_own_required_set(self):
        records = [evaluate_activity(a, LOT_SIZE) for a in PROC_ACTIVITIES]
        coverage = programme_coverage(records)
        self.assertAlmostEqual(coverage["qualification"]["fraction"], 0.0, places=9)
        self.assertAlmostEqual(coverage["procurement"]["fraction"], 1.0, places=9)

    def test_an_unacceptable_activity_does_not_count_towards_coverage(self):
        activities = _with_change(
            "thermal-cycling", "qualification", specimen="delivered-cell"
        )
        records = [evaluate_activity(a, LOT_SIZE) for a in activities]
        coverage = programme_coverage(records)
        self.assertIn("thermal-cycling", coverage["qualification"]["missing"])

    def test_the_qualification_share_counts_activities_not_specimens(self):
        records = [evaluate_activity(a, LOT_SIZE) for a in FULL_PROGRAMME]
        expected = float(len(REQUIRED_ACTIVITIES["qualification"])) / float(
            len(FULL_PROGRAMME)
        )
        self.assertAlmostEqual(qualification_share(records), expected, places=9)

    def test_an_empty_programme_has_no_share_to_report(self):
        with self.assertRaises(ValueError):
            qualification_share([])


class ProgrammeTests(unittest.TestCase):
    def test_a_full_well_placed_programme_is_acceptable(self):
        result = assess_bare_cell_programme(_spec())
        self.assertEqual(result["verdict"], PROGRAMME_ACCEPTABLE)
        self.assertEqual(result["findings"], [])

    def test_a_gap_in_one_errand_makes_the_programme_unacceptable(self):
        result = assess_bare_cell_programme(
            _spec(activities=_without("humidity-exposure", "qualification"))
        )
        self.assertEqual(result["verdict"], PROGRAMME_NOT_ACCEPTABLE)
        self.assertTrue(any("qualification coverage" in f for f in result["findings"]))

    def test_a_programme_can_serve_one_errand_only_when_it_says_so(self):
        result = assess_bare_cell_programme(
            _spec(activities=copy.deepcopy(PROC_ACTIVITIES), errands=["procurement"])
        )
        self.assertEqual(result["verdict"], PROGRAMME_ACCEPTABLE)
        self.assertAlmostEqual(result["qualification_share"], 0.0, places=9)

    def test_a_supplementary_activity_is_a_finding_not_a_block(self):
        extra = copy.deepcopy(FULL_PROGRAMME)
        extra.append(
            {
                "name": "photoluminescence-mapping",
                "purpose": "qualification",
                "specimen": "qualification-lot-cell",
                "sample_size": 6,
            }
        )
        result = assess_bare_cell_programme(_spec(activities=extra))
        self.assertEqual(result["verdict"], PROGRAMME_WITH_FINDINGS)

    def test_an_undersized_procurement_sample_blocks_the_programme(self):
        result = assess_bare_cell_programme(
            _spec(activities=_with_change(
                "electrical-performance", "procurement", sample_size=4
            ))
        )
        self.assertEqual(result["verdict"], PROGRAMME_NOT_ACCEPTABLE)

    def test_a_duplicated_activity_for_one_errand_is_rejected(self):
        doubled = copy.deepcopy(FULL_PROGRAMME)
        doubled.append(copy.deepcopy(PROC_ACTIVITIES[0]))
        with self.assertRaises(ValueError):
            assess_bare_cell_programme(_spec(activities=doubled))

    def test_a_relaxed_coverage_threshold_is_honoured_exactly_at_the_bound(self):
        activities = _without("ultraviolet-exposure", "qualification")
        required = float(len(REQUIRED_ACTIVITIES["qualification"]) - 1) / float(
            len(REQUIRED_ACTIVITIES["qualification"])
        )
        result = assess_bare_cell_programme(
            _spec(activities=activities, required_coverage=required)
        )
        self.assertAlmostEqual(
            result["coverage"]["qualification"]["fraction"], required, places=9
        )
        self.assertEqual(result["verdict"], PROGRAMME_ACCEPTABLE)

    def test_a_coverage_threshold_outside_the_unit_interval_is_rejected(self):
        with self.assertRaises(ValueError):
            assess_bare_cell_programme(_spec(required_coverage=1.5))

    def test_an_empty_activity_list_is_rejected(self):
        with self.assertRaises(ValueError):
            assess_bare_cell_programme(_spec(activities=[]))

    def test_an_unknown_errand_is_rejected(self):
        with self.assertRaises(ValueError):
            assess_bare_cell_programme(_spec(errands=["marketing"]))

    def test_a_non_mapping_spec_is_rejected(self):
        with self.assertRaises(ValueError):
            assess_bare_cell_programme(["lot_size", 100])


if __name__ == "__main__":
    unittest.main(verbosity=1)
