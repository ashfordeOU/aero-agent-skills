#!/usr/bin/env python3
"""Gate 3 contract test for q6005-production-lot-control-option.

Offline, stdlib unittest. Exercises the lot and group validation, the
per-group allocation out of one production lot, the destructive accounting,
the per-group and per-lot disposition, the resubmission limit and the
consecutive-reject suspension of ECSS-Q-ST-60-05C clause 12.2.1 as
paraphrased in the logic module. Sampling fractions are exact quotients of
small integers, so they are asserted with assertAlmostEqual rather than a
strict inequality that libm could round either way between build host and CI
runner.
"""

import os
import sys
import unittest

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from q6005_production_lot_control_option_logic import (  # noqa: E402
    CONSECUTIVE_REJECT_LIMIT,
    DEFAULT_TEST_GROUPS,
    MAX_RESUBMISSIONS,
    allocate_lot_samples,
    campaign_status,
    deliverable_after_acceptance,
    group_disposition,
    lot_disposition,
    lot_sampling_fraction,
    plan_production_lot_control,
    resubmission_allowed,
    units_destroyed,
    validate_lot_size,
    validate_test_groups,
)

CLEAN_RESULTS = {
    "electrical-acceptance": 0,
    "environmental-acceptance": 0,
    "destructive-physical-analysis": 0,
}


class LotValidationTests(unittest.TestCase):
    def test_positive_lot_size_is_returned(self):
        self.assertEqual(validate_lot_size(120), 120)

    def test_zero_or_negative_lot_is_refused(self):
        for bad in (0, -12):
            with self.assertRaises(ValueError):
                validate_lot_size(bad)

    def test_boolean_lot_size_is_refused(self):
        with self.assertRaises(ValueError):
            validate_lot_size(True)

    def test_float_lot_size_is_refused(self):
        with self.assertRaises(ValueError):
            validate_lot_size(120.0)


class GroupValidationTests(unittest.TestCase):
    def test_default_groups_validate(self):
        self.assertEqual(len(validate_test_groups()), 3)

    def test_empty_group_set_is_refused(self):
        with self.assertRaises(ValueError):
            validate_test_groups([])

    def test_duplicate_group_name_is_refused(self):
        duplicated = list(DEFAULT_TEST_GROUPS) + [dict(DEFAULT_TEST_GROUPS[0])]
        with self.assertRaises(ValueError):
            validate_test_groups(duplicated)

    def test_group_without_a_name_is_refused(self):
        with self.assertRaises(ValueError):
            validate_test_groups([{"sample_size": 5}])

    def test_acceptance_number_at_the_sample_size_is_refused(self):
        with self.assertRaises(ValueError):
            validate_test_groups([{"name": "g", "sample_size": 4, "acceptance_number": 4}])

    def test_non_boolean_destructive_flag_is_refused(self):
        with self.assertRaises(ValueError):
            validate_test_groups([{"name": "g", "sample_size": 4, "destructive": "yes"}])

    def test_group_names_normalise_case_and_separator(self):
        normalised = validate_test_groups([{"name": "Electrical Acceptance", "sample_size": 4}])
        self.assertEqual(normalised[0]["name"], "electrical-acceptance")


class AllocationTests(unittest.TestCase):
    def test_allocation_sums_every_group_sample(self):
        allocation = allocate_lot_samples(200)
        self.assertEqual(allocation["units_committed"], 32)

    def test_only_destructive_groups_reduce_the_deliverable(self):
        self.assertEqual(units_destroyed(200), 2)
        self.assertEqual(deliverable_after_acceptance(200), 198)

    def test_non_destructive_samples_return_to_stock(self):
        self.assertEqual(allocate_lot_samples(200)["units_returned_to_stock"], 30)

    def test_lot_too_small_to_feed_its_own_groups_is_refused(self):
        with self.assertRaises(ValueError):
            allocate_lot_samples(20)

    def test_lot_exactly_covering_the_commitment_is_allowed(self):
        allocation = allocate_lot_samples(32)
        self.assertEqual(allocation["units_committed"], 32)
        self.assertEqual(allocation["deliverable_after_acceptance"], 30)

    def test_sampling_fraction_is_the_commitment_over_the_lot(self):
        self.assertAlmostEqual(lot_sampling_fraction(320), 0.1, places=9)

    def test_full_commitment_lot_samples_the_whole_lot(self):
        self.assertAlmostEqual(lot_sampling_fraction(32), 1.0, places=9)


class GroupDispositionTests(unittest.TestCase):
    def test_clean_group_accepts(self):
        outcome = group_disposition(DEFAULT_TEST_GROUPS[0], 0)
        self.assertEqual(outcome["disposition"], "accept")

    def test_any_failure_rejects_a_zero_acceptance_group(self):
        self.assertEqual(group_disposition(DEFAULT_TEST_GROUPS[0], 1)["disposition"], "reject")

    def test_failures_at_the_acceptance_number_still_accept(self):
        group = {"name": "g", "sample_size": 20, "acceptance_number": 2}
        self.assertTrue(group_disposition(group, 2)["accepted"])

    def test_more_failures_than_units_sampled_is_refused(self):
        with self.assertRaises(ValueError):
            group_disposition(DEFAULT_TEST_GROUPS[1], 9)


class LotDispositionTests(unittest.TestCase):
    def test_clean_lot_is_accepted(self):
        outcome = lot_disposition(200, CLEAN_RESULTS)
        self.assertEqual(outcome["disposition"], "accept")
        self.assertEqual(outcome["deliverable_after_acceptance"], 198)

    def test_one_failing_group_refuses_the_whole_lot(self):
        results = dict(CLEAN_RESULTS, **{"environmental-acceptance": 1})
        outcome = lot_disposition(200, results)
        self.assertEqual(outcome["disposition"], "reject")
        self.assertEqual(outcome["failing_groups"], ["environmental-acceptance"])
        self.assertEqual(outcome["deliverable_after_acceptance"], 0)

    def test_group_with_no_result_is_unverified_not_accepted(self):
        results = dict(CLEAN_RESULTS)
        del results["destructive-physical-analysis"]
        outcome = lot_disposition(200, results)
        self.assertEqual(outcome["disposition"], "reject")
        self.assertEqual(outcome["unreported_groups"], ["destructive-physical-analysis"])

    def test_result_naming_a_group_outside_the_plan_is_refused(self):
        results = dict(CLEAN_RESULTS, **{"radiation-acceptance": 0})
        with self.assertRaises(ValueError):
            lot_disposition(200, results)

    def test_results_must_be_a_mapping(self):
        with self.assertRaises(ValueError):
            lot_disposition(200, [("electrical-acceptance", 0)])

    def test_result_keys_are_matched_case_and_separator_insensitively(self):
        results = {k.replace("-", " ").upper(): v for k, v in CLEAN_RESULTS.items()}
        self.assertEqual(lot_disposition(200, results)["disposition"], "accept")


class CampaignTests(unittest.TestCase):
    def test_empty_history_retains_the_entitlement(self):
        status = campaign_status([])
        self.assertEqual(status["entitlement"], "retained")
        self.assertTrue(status["may_submit_next_lot"])

    def test_isolated_rejects_do_not_suspend_the_line(self):
        status = campaign_status(["reject", "accept", "reject", "accept"])
        self.assertEqual(status["lots_rejected"], 2)
        self.assertEqual(status["consecutive_rejects"], 0)
        self.assertEqual(status["entitlement"], "retained")

    def test_consecutive_rejects_at_the_limit_suspend_the_line(self):
        status = campaign_status(["accept"] + ["reject"] * CONSECUTIVE_REJECT_LIMIT)
        self.assertEqual(status["entitlement"], "suspended")
        self.assertFalse(status["may_submit_next_lot"])

    def test_an_accept_clears_the_consecutive_run(self):
        status = campaign_status(["reject", "reject", "accept"])
        self.assertEqual(status["consecutive_rejects"], 0)
        self.assertEqual(status["entitlement"], "retained")

    def test_unknown_disposition_value_is_refused(self):
        with self.assertRaises(ValueError):
            campaign_status(["accept", "pending"])

    def test_string_history_is_not_a_sequence_of_dispositions(self):
        with self.assertRaises(ValueError):
            campaign_status("accept")

    def test_resubmission_is_allowed_up_to_the_limit(self):
        self.assertTrue(resubmission_allowed(MAX_RESUBMISSIONS))
        self.assertFalse(resubmission_allowed(MAX_RESUBMISSIONS + 1))

    def test_negative_prior_submission_count_is_refused(self):
        with self.assertRaises(ValueError):
            resubmission_allowed(-1)


class PlanTests(unittest.TestCase):
    def test_workable_plan_reports_no_findings(self):
        plan = plan_production_lot_control({"lot_size": 200, "results": CLEAN_RESULTS})
        self.assertTrue(plan["plan_is_workable"])
        self.assertEqual(plan["lot_disposition"], "accept")
        self.assertEqual(plan["findings"], [])
        self.assertAlmostEqual(plan["sampling_fraction"], 0.16, places=9)

    def test_order_taking_the_whole_lot_is_short_by_the_destructive_sample(self):
        plan = plan_production_lot_control({"lot_size": 200, "deliverable_quantity": 200})
        self.assertEqual(plan["deliverable_shortfall"], 2)
        self.assertFalse(plan["plan_is_workable"])

    def test_failing_group_appears_in_the_findings(self):
        results = dict(CLEAN_RESULTS, **{"electrical-acceptance": 3})
        plan = plan_production_lot_control({"lot_size": 200, "results": results})
        self.assertEqual(plan["lot_disposition"], "reject")
        self.assertTrue(any("electrical-acceptance" in f for f in plan["findings"]))

    def test_suspended_line_is_reported_even_on_a_clean_lot(self):
        plan = plan_production_lot_control(
            {"lot_size": 200, "results": CLEAN_RESULTS, "lot_history": ["reject", "reject"]}
        )
        self.assertEqual(plan["lot_disposition"], "accept")
        self.assertEqual(plan["campaign"]["entitlement"], "suspended")
        self.assertFalse(plan["plan_is_workable"])

    def test_rejected_lot_out_of_resubmissions_is_flagged(self):
        results = dict(CLEAN_RESULTS, **{"electrical-acceptance": 1})
        plan = plan_production_lot_control(
            {"lot_size": 200, "results": results, "prior_submissions": 5}
        )
        self.assertFalse(plan["may_resubmit"])
        self.assertTrue(any("resubmissions" in f for f in plan["findings"]))

    def test_missing_lot_size_is_refused(self):
        with self.assertRaises(ValueError):
            plan_production_lot_control({"results": CLEAN_RESULTS})

    def test_non_mapping_spec_is_refused(self):
        with self.assertRaises(ValueError):
            plan_production_lot_control([("lot_size", 200)])


if __name__ == "__main__":
    unittest.main(verbosity=2)
