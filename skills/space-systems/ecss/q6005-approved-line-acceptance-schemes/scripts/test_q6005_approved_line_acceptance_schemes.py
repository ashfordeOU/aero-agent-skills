#!/usr/bin/env python3
"""Gate 3 contract test for q6005-approved-line-acceptance-schemes.

Offline, stdlib unittest. Exercises the profile validation, the approved-line
entry condition, the per-option entry conditions, the board quorum and role
check, the annual sample burden and the recommendation of ECSS-Q-ST-60-05C
clause 12.2 as paraphrased in the logic module. The capability index lands
exactly on its floor in the boundary case, so that case is asserted through
the tolerant comparison in the logic rather than by a strict inequality that
libm could round either way between build host and CI runner.
"""

import os
import sys
import unittest

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from q6005_approved_line_acceptance_schemes_logic import (  # noqa: E402
    BOARD_QUORUM,
    MIN_CAPABILITY_INDEX,
    MIN_MONITORED_LOTS,
    PRODUCTION_LOT_CONTROL,
    REQUIRED_BOARD_ROLES,
    REVIEW_BOARD_PROCESS_CONTROL,
    annual_sample_burden,
    assess_acceptance_scheme_options,
    available_schemes,
    board_is_quorate,
    board_roles_present,
    recommend_scheme,
    scheme_gaps,
    validate_profile,
)


def profile(**overrides):
    """A supplier meeting the entry conditions of both options."""
    base = {
        "approved_line": True,
        "approval_reference": "LINE-APPROVAL-2291",
        "batch_size": 200,
        "units_available_for_sampling": 40,
        "per_lot_sample_size": 22,
        "acceptance_test_facility": True,
        "monitored_consecutive_lots": 18,
        "process_capability_index": 1.60,
        "review_board_roles": list(REQUIRED_BOARD_ROLES),
        "reversion_criteria_defined": True,
        "lots_per_year": 12,
    }
    base.update(overrides)
    return base


class ProfileValidationTests(unittest.TestCase):
    def test_complete_profile_normalises(self):
        normalised = validate_profile(profile())
        self.assertTrue(normalised["approved_line"])
        self.assertEqual(normalised["per_lot_sample_size"], 22)

    def test_non_mapping_profile_is_refused(self):
        with self.assertRaises(ValueError):
            validate_profile([("approved_line", True)])

    def test_absent_evidence_normalises_to_empty_not_an_error(self):
        normalised = validate_profile({})
        self.assertFalse(normalised["approved_line"])
        self.assertEqual(normalised["monitored_consecutive_lots"], 0)
        self.assertEqual(normalised["review_board_roles"], set())

    def test_non_boolean_flag_is_refused(self):
        with self.assertRaises(ValueError):
            validate_profile(profile(approved_line="yes"))

    def test_negative_lot_count_is_refused(self):
        with self.assertRaises(ValueError):
            validate_profile(profile(lots_per_year=-1))

    def test_negative_capability_index_is_refused(self):
        with self.assertRaises(ValueError):
            validate_profile(profile(process_capability_index=-0.5))

    def test_string_of_roles_is_not_a_role_list(self):
        with self.assertRaises(ValueError):
            validate_profile(profile(review_board_roles="manufacturer-quality-assurance"))

    def test_blank_role_name_is_refused(self):
        with self.assertRaises(ValueError):
            validate_profile(profile(review_board_roles=["   "]))

    def test_sample_larger_than_the_batch_is_refused(self):
        with self.assertRaises(ValueError):
            validate_profile(profile(batch_size=10, per_lot_sample_size=40))

    def test_role_names_are_matched_case_and_separator_insensitively(self):
        roles = [r.replace("-", " ").upper() for r in REQUIRED_BOARD_ROLES]
        self.assertEqual(len(board_roles_present(profile(review_board_roles=roles))), 4)


class EntryConditionTests(unittest.TestCase):
    def test_unapproved_line_closes_both_options(self):
        unapproved = profile(approved_line=False)
        self.assertEqual(available_schemes(unapproved), [])
        for scheme in (PRODUCTION_LOT_CONTROL, REVIEW_BOARD_PROCESS_CONTROL):
            self.assertTrue(any("not an approved" in g for g in scheme_gaps(unapproved, scheme)))

    def test_approved_line_without_a_reference_is_a_gap(self):
        gaps = scheme_gaps(profile(approval_reference=None), PRODUCTION_LOT_CONTROL)
        self.assertTrue(any("no reference" in g for g in gaps))

    def test_compliant_supplier_has_both_options_open(self):
        self.assertEqual(
            available_schemes(profile()),
            [PRODUCTION_LOT_CONTROL, REVIEW_BOARD_PROCESS_CONTROL],
        )

    def test_unknown_scheme_name_is_refused(self):
        with self.assertRaises(ValueError):
            scheme_gaps(profile(), "whatever-scheme")


class LotControlEntryTests(unittest.TestCase):
    def test_no_sample_size_closes_the_per_lot_option(self):
        gaps = scheme_gaps(profile(per_lot_sample_size=0), PRODUCTION_LOT_CONTROL)
        self.assertTrue(any("sample size" in g for g in gaps))

    def test_lot_too_small_to_yield_the_sample_closes_the_option(self):
        gaps = scheme_gaps(profile(units_available_for_sampling=5), PRODUCTION_LOT_CONTROL)
        self.assertTrue(any("yields 5 units" in g for g in gaps))

    def test_missing_test_facility_closes_the_option(self):
        gaps = scheme_gaps(profile(acceptance_test_facility=False), PRODUCTION_LOT_CONTROL)
        self.assertTrue(any("test facility" in g for g in gaps))

    def test_monitoring_shortfalls_do_not_close_the_per_lot_option(self):
        thin = profile(monitored_consecutive_lots=0, review_board_roles=[])
        self.assertEqual(scheme_gaps(thin, PRODUCTION_LOT_CONTROL), [])


class MonitoringEntryTests(unittest.TestCase):
    def test_short_monitoring_history_closes_the_option(self):
        short = profile(monitored_consecutive_lots=MIN_MONITORED_LOTS - 1)
        self.assertTrue(
            any("consecutive monitored" in g for g in scheme_gaps(short, REVIEW_BOARD_PROCESS_CONTROL))
        )

    def test_capability_exactly_on_the_floor_is_accepted(self):
        at_floor = profile(process_capability_index=MIN_CAPABILITY_INDEX)
        self.assertIn(REVIEW_BOARD_PROCESS_CONTROL, available_schemes(at_floor))

    def test_capability_below_the_floor_closes_the_option(self):
        low = profile(process_capability_index=1.0)
        self.assertTrue(
            any("capability index" in g for g in scheme_gaps(low, REVIEW_BOARD_PROCESS_CONTROL))
        )

    def test_board_short_of_quorum_closes_the_option(self):
        thin_board = profile(review_board_roles=list(REQUIRED_BOARD_ROLES[:2]))
        self.assertFalse(board_is_quorate(thin_board))
        self.assertNotIn(REVIEW_BOARD_PROCESS_CONTROL, available_schemes(thin_board))

    def test_quorate_board_without_the_customer_member_still_closes_the_option(self):
        no_customer = profile(
            review_board_roles=[r for r in REQUIRED_BOARD_ROLES if r != "customer-product-assurance"]
        )
        self.assertTrue(board_is_quorate(no_customer))
        gaps = scheme_gaps(no_customer, REVIEW_BOARD_PROCESS_CONTROL)
        self.assertTrue(any("customer product assurance" in g for g in gaps))

    def test_quorum_is_a_count_of_the_required_roles(self):
        self.assertEqual(BOARD_QUORUM, 3)
        self.assertTrue(board_is_quorate(profile(review_board_roles=list(REQUIRED_BOARD_ROLES[:3]))))

    def test_absent_reversion_criterion_closes_the_option(self):
        gaps = scheme_gaps(profile(reversion_criteria_defined=False), REVIEW_BOARD_PROCESS_CONTROL)
        self.assertTrue(any("per-lot testing" in g for g in gaps))


class BurdenAndRecommendationTests(unittest.TestCase):
    def test_annual_burden_is_the_sample_times_the_lot_rate(self):
        self.assertEqual(annual_sample_burden(profile()), 264)

    def test_burden_is_zero_when_the_line_builds_nothing(self):
        self.assertEqual(annual_sample_burden(profile(lots_per_year=0)), 0)

    def test_continuous_line_with_both_options_is_pointed_at_monitoring(self):
        result = recommend_scheme(profile())
        self.assertEqual(result["scheme"], REVIEW_BOARD_PROCESS_CONTROL)
        self.assertIn("264", result["rationale"])

    def test_occasional_line_with_both_options_is_pointed_at_per_lot_testing(self):
        result = recommend_scheme(profile(lots_per_year=2))
        self.assertEqual(result["scheme"], PRODUCTION_LOT_CONTROL)

    def test_single_open_option_is_recommended_on_that_ground_alone(self):
        result = recommend_scheme(profile(monitored_consecutive_lots=0))
        self.assertEqual(result["scheme"], PRODUCTION_LOT_CONTROL)
        self.assertIn("only option", result["rationale"])

    def test_no_open_option_recommends_nothing(self):
        result = recommend_scheme(profile(approved_line=False))
        self.assertIsNone(result["scheme"])


class AssessmentTests(unittest.TestCase):
    def test_compliant_supplier_report_is_complete(self):
        report = assess_acceptance_scheme_options(profile())
        self.assertTrue(report["approved_line"])
        self.assertEqual(len(report["available_schemes"]), 2)
        self.assertTrue(report["board_quorate"])
        self.assertTrue(report["continuous_production"])
        self.assertFalse(report["falls_to_project_validation"])

    def test_unapproved_supplier_is_sent_to_the_project_validated_route(self):
        report = assess_acceptance_scheme_options(profile(approved_line=False))
        self.assertTrue(report["falls_to_project_validation"])
        self.assertIsNone(report["recommended_scheme"])

    def test_gaps_are_reported_for_every_option_not_only_the_chosen_one(self):
        report = assess_acceptance_scheme_options(
            profile(monitored_consecutive_lots=1, acceptance_test_facility=False)
        )
        self.assertTrue(report["gaps"][PRODUCTION_LOT_CONTROL])
        self.assertTrue(report["gaps"][REVIEW_BOARD_PROCESS_CONTROL])
        self.assertEqual(report["available_schemes"], [])

    def test_report_names_the_approval_reference_it_relied_on(self):
        report = assess_acceptance_scheme_options(profile())
        self.assertEqual(report["approval_reference"], "LINE-APPROVAL-2291")


if __name__ == "__main__":
    unittest.main(verbosity=2)
