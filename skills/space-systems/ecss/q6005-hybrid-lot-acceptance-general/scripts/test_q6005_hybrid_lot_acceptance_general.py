#!/usr/bin/env python3
"""Gate 3 contract test for q6005-hybrid-lot-acceptance-general.

Offline, stdlib unittest. Exercises the sample-rule validation, the integer
round-up of a proportional sample size, the destructive demand against the
lot and the contract quantity, the per-group grading and the batch
disposition of ECSS-Q-ST-60-05C clause 12.1 as paraphrased in the logic
module. The destructive burden lands exactly on simple fractions, so it is
asserted with assertAlmostEqual rather than a strict inequality that could
round either way between the build host and the CI runner.
"""

import os
import sys
import unittest

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from q6005_hybrid_lot_acceptance_general_logic import (  # noqa: E402
    SAMPLE_RULE_KINDS,
    assess_lot_acceptance_arrangement,
    deliverable_after_sampling,
    destructive_burden_ratio,
    destructive_demand,
    grade_group,
    required_sample_size,
    size_groups,
    validate_group,
    validate_lot,
    validate_rule,
)

FIXED_4 = {"kind": "fixed", "units": 4}
PROPORTIONAL = {"kind": "proportional", "permille": 20, "minimum": 2, "maximum": 20}


def group(group_id="A", rule=None, **overrides):
    record = {
        "group_id": group_id,
        "sample_rule": dict(rule) if rule else dict(FIXED_4),
        "destructive": True,
        "accept_number": 0,
    }
    record.update(overrides)
    return record


def lot(**overrides):
    """A batch of 100 hybrids with one destructive group of four, all passed."""
    spec = {
        "lot_size": 100,
        "contract_delivery_quantity": 80,
        "groups": [group(units_drawn=4, units_failed=0)],
    }
    spec.update(overrides)
    return spec


class RuleValidationTests(unittest.TestCase):
    def test_rule_must_be_a_mapping_naming_a_known_kind(self):
        with self.assertRaises(ValueError):
            validate_rule("fixed")
        with self.assertRaises(ValueError):
            validate_rule({"units": 4})
        with self.assertRaises(ValueError):
            validate_rule({"kind": "stratified", "units": 4})

    def test_both_recognised_rule_kinds_validate(self):
        self.assertEqual(sorted(SAMPLE_RULE_KINDS), ["fixed", "proportional"])
        self.assertEqual(validate_rule(FIXED_4)["kind"], "fixed")
        self.assertEqual(validate_rule(PROPORTIONAL)["kind"], "proportional")

    def test_a_fixed_rule_needs_a_positive_unit_count(self):
        with self.assertRaises(ValueError):
            validate_rule({"kind": "fixed", "units": 0})
        with self.assertRaises(ValueError):
            validate_rule({"kind": "fixed", "units": True})

    def test_a_share_above_the_whole_lot_is_refused(self):
        with self.assertRaises(ValueError):
            validate_rule({"kind": "proportional", "permille": 1200})

    def test_an_inverted_floor_and_ceiling_is_refused(self):
        with self.assertRaises(ValueError):
            validate_rule(
                {"kind": "proportional", "permille": 20, "minimum": 10, "maximum": 5}
            )


class SampleSizeTests(unittest.TestCase):
    def test_a_fixed_rule_ignores_the_lot_size(self):
        self.assertEqual(required_sample_size(FIXED_4, 50), 4)
        self.assertEqual(required_sample_size(FIXED_4, 5000), 4)

    def test_a_proportional_share_that_divides_exactly_adds_no_extra_unit(self):
        # Two percent of five hundred is ten, and integer arithmetic keeps it
        # ten. Taking the same share in floating point lands just above ten
        # and rounds up to eleven.
        self.assertEqual(required_sample_size(PROPORTIONAL, 500), 10)

    def test_a_proportional_share_rounds_up_when_it_does_not_divide(self):
        self.assertEqual(required_sample_size(PROPORTIONAL, 501), 11)

    def test_the_floor_protects_a_small_lot(self):
        self.assertEqual(required_sample_size(PROPORTIONAL, 10), 2)

    def test_the_ceiling_protects_a_large_lot(self):
        self.assertEqual(required_sample_size(PROPORTIONAL, 5000), 20)

    def test_a_non_positive_lot_size_is_refused(self):
        with self.assertRaises(ValueError):
            required_sample_size(FIXED_4, 0)


class ArrangementTests(unittest.TestCase):
    def test_lot_header_requires_a_positive_size_and_some_groups(self):
        with self.assertRaises(ValueError):
            validate_lot({"lot_size": 0, "groups": [group()]})
        with self.assertRaises(ValueError):
            validate_lot({"lot_size": 100, "groups": []})
        with self.assertRaises(ValueError):
            validate_lot({"lot_size": 100})

    def test_duplicate_group_ids_are_refused(self):
        with self.assertRaises(ValueError):
            size_groups({"lot_size": 100, "groups": [group("A"), group("A")]})

    def test_only_destructive_groups_consume_the_lot(self):
        spec = {
            "lot_size": 100,
            "groups": [group("A"), group("B", destructive=False)],
        }
        self.assertEqual(destructive_demand(spec), 4)
        self.assertEqual(deliverable_after_sampling(spec), 96)

    def test_the_burden_is_the_destructive_demand_over_the_lot(self):
        self.assertAlmostEqual(destructive_burden_ratio(lot()), 0.04, places=9)

    def test_a_group_reporting_more_failures_than_units_is_refused(self):
        with self.assertRaises(ValueError):
            validate_group(group(units_drawn=4, units_failed=5))

    def test_a_non_boolean_destructive_flag_is_refused(self):
        with self.assertRaises(ValueError):
            validate_group(group(destructive="yes"))


class GroupGradingTests(unittest.TestCase):
    def test_an_undrawn_group_is_not_yet_graded(self):
        sized = size_groups({"lot_size": 100, "groups": [group()]})
        self.assertEqual(grade_group(sized[0])["status"], "not-drawn")

    def test_a_drawn_group_without_a_result_is_not_yet_graded(self):
        sized = size_groups({"lot_size": 100, "groups": [group(units_drawn=4)]})
        self.assertEqual(grade_group(sized[0])["status"], "not-graded")

    def test_a_short_sample_does_not_speak_for_the_lot(self):
        sized = size_groups(
            {"lot_size": 100, "groups": [group(units_drawn=2, units_failed=0)]}
        )
        graded = grade_group(sized[0])
        self.assertEqual(graded["status"], "short-sample")
        self.assertIn("against 4 required", graded["reason"])

    def test_failures_beyond_the_accept_number_fail_the_group(self):
        sized = size_groups(
            {"lot_size": 100, "groups": [group(units_drawn=4, units_failed=1)]}
        )
        self.assertEqual(grade_group(sized[0])["status"], "failed")

    def test_failures_within_the_accept_number_pass_the_group(self):
        sized = size_groups(
            {
                "lot_size": 100,
                "groups": [group(accept_number=1, units_drawn=4, units_failed=1)],
            }
        )
        self.assertEqual(grade_group(sized[0])["status"], "passed")

    def test_an_unsized_group_cannot_be_graded(self):
        with self.assertRaises(ValueError):
            grade_group(validate_group(group()))


class DispositionTests(unittest.TestCase):
    def test_a_fully_passed_arrangement_accepts_the_lot(self):
        result = assess_lot_acceptance_arrangement(lot())
        self.assertEqual(result["disposition"], "lot-accepted")
        self.assertTrue(result["accepted"])
        self.assertEqual(result["deliverable_after_sampling"], 96)

    def test_a_failed_group_rejects_the_lot(self):
        result = assess_lot_acceptance_arrangement(
            lot(groups=[group(units_drawn=4, units_failed=2)])
        )
        self.assertEqual(result["disposition"], "lot-rejected")
        self.assertEqual(result["failed_groups"], ["A"])

    def test_a_short_sample_invalidates_the_sampling_before_any_verdict(self):
        result = assess_lot_acceptance_arrangement(
            lot(groups=[group(units_drawn=1, units_failed=1)])
        )
        self.assertEqual(result["disposition"], "sampling-not-valid")
        self.assertFalse(result["accepted"])

    def test_an_unstarted_arrangement_reports_the_plan_not_a_verdict(self):
        result = assess_lot_acceptance_arrangement(lot(groups=[group()]))
        self.assertEqual(result["disposition"], "sampling-not-complete")
        self.assertEqual(result["pending_groups"], ["A"])
        self.assertEqual(result["arrangement"][0]["required_units"], 4)

    def test_sampling_that_eats_the_lot_is_not_a_feasible_plan(self):
        result = assess_lot_acceptance_arrangement(
            {
                "lot_size": 6,
                "contract_delivery_quantity": 4,
                "groups": [group("A", rule={"kind": "fixed", "units": 8})],
            }
        )
        self.assertEqual(result["disposition"], "sampling-plan-not-feasible")
        self.assertTrue(any("from a lot of" in b for b in result["blockers"]))

    def test_sampling_that_breaks_the_delivery_quantity_is_not_feasible(self):
        result = assess_lot_acceptance_arrangement(
            lot(contract_delivery_quantity=98, groups=[group(units_drawn=4, units_failed=0)])
        )
        self.assertEqual(result["disposition"], "sampling-plan-not-feasible")
        self.assertTrue(any("contract quantity" in b for b in result["blockers"]))

    def test_a_non_destructive_group_does_not_reduce_the_deliverables(self):
        result = assess_lot_acceptance_arrangement(
            lot(
                contract_delivery_quantity=96,
                groups=[
                    group("A", units_drawn=4, units_failed=0),
                    group("B", destructive=False, units_drawn=4, units_failed=0),
                ],
            )
        )
        self.assertEqual(result["disposition"], "lot-accepted")
        self.assertEqual(result["destructive_demand"], 4)

    def test_the_burden_ratio_is_reported_with_the_arrangement(self):
        result = assess_lot_acceptance_arrangement(lot())
        self.assertAlmostEqual(result["destructive_burden_ratio"], 0.04, places=9)

    def test_a_malformed_lot_is_refused(self):
        with self.assertRaises(ValueError):
            assess_lot_acceptance_arrangement({"lot_size": 100, "groups": {}})
        with self.assertRaises(ValueError):
            assess_lot_acceptance_arrangement("a lot of one hundred")


if __name__ == "__main__":
    unittest.main(verbosity=2)
