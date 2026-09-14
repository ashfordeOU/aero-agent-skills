"""Contract tests for clause 5.3.9 class 2 destructive physical sampling.

Every workflow step the SKILL.md sets out is exercised here, together with
the stop conditions the gate 3 contract reviews: a refused sampling policy,
a group with neither a teardown nor a credited report, a report that names
another date code or is too old or covers too little, a group its own sample
would consume, an unregistered defect code, a largest void above the total,
a single major defect calling for a second sample, and a second major
defect disposing of the group.
"""

import unittest

from q6013_class_2_destructive_physical_analysis_logic import (
    DEFAULT_DPA_POLICY,
    DPA_CONSTRUCTION_REJECTED,
    DPA_MEETS_CLASS_TWO_SCOPE,
    DPA_NOT_PERFORMED,
    DPA_RESAMPLE_REQUIRED,
    DPA_SAMPLE_NOT_FEASIBLE,
    GROUP_ACCEPTED,
    GROUP_ACCEPTED_WITH_RECORD,
    GROUP_NOT_SAMPLED,
    GROUP_REJECTED,
    GROUP_RESAMPLE_REQUIRED,
    MAJOR_DEFECTS,
    MINOR_DEFECTS,
    REQUIRED_CRITERIA,
    assess_destructive_physical_sampling,
    bond_pull_assessment,
    categorize_defect,
    categorize_defects,
    dpa_sample_size,
    group_disposition,
    group_sample_plan,
    manufacturer_credit_decision,
    validate_dpa_policy,
    validate_fraction,
    void_assessment,
)

VOID_LIMITS = {"total_limit": 0.5, "largest_limit": 0.15}


def _policy(**overrides):
    policy = dict(DEFAULT_DPA_POLICY)
    policy.update(overrides)
    return policy


def _report(**overrides):
    report = {
        "date_code": "2508",
        "signed": True,
        "age_months": 6,
        "criteria_covered": sorted(REQUIRED_CRITERIA),
    }
    report.update(overrides)
    return report


def _group(**overrides):
    group = {
        "date_code": "2508",
        "unit_count": 4000,
        "teardown_performed": True,
        "observed_defects": [],
        "total_void_fraction": 0.2,
        "largest_void_fraction": 0.05,
        "pull_values_g": [5.0, 5.4, 5.8, 6.1],
        "resample_performed": False,
    }
    group.update(overrides)
    return group


def _case(**overrides):
    case = {
        "groups": [_group()],
        "void_limits": dict(VOID_LIMITS),
        "bond_minimum_g": 3.0,
        "bond_mean_minimum_g": 4.0,
    }
    case.update(overrides)
    return case


class PolicyTests(unittest.TestCase):
    def test_default_policy_validates(self):
        self.assertIs(validate_dpa_policy(DEFAULT_DPA_POLICY), DEFAULT_DPA_POLICY)

    def test_policy_missing_a_key_is_refused(self):
        policy = dict(DEFAULT_DPA_POLICY)
        del policy["min_sample"]
        with self.assertRaises(ValueError):
            validate_dpa_policy(policy)

    def test_zero_sampling_fraction_is_refused(self):
        with self.assertRaises(ValueError):
            validate_dpa_policy(_policy(sample_fraction=0.0))

    def test_confirmation_sample_above_the_floor_is_refused(self):
        with self.assertRaises(ValueError):
            validate_dpa_policy(_policy(confirmation_sample=5, min_sample=2))

    def test_non_mapping_policy_is_refused(self):
        with self.assertRaises(ValueError):
            validate_dpa_policy(["sample_fraction"])

    def test_fraction_above_unity_is_refused(self):
        with self.assertRaises(ValueError):
            validate_fraction(1.5, "total_limit")


class CreditTests(unittest.TestCase):
    def test_a_covering_signed_recent_report_is_credited(self):
        decision = manufacturer_credit_decision(_report(), "2508")
        self.assertTrue(decision["credited"])

    def test_a_report_for_another_date_code_is_not_credited(self):
        decision = manufacturer_credit_decision(_report(date_code="2441"), "2508")
        self.assertFalse(decision["credited"])
        self.assertIn("2441", decision["reason"])

    def test_an_unsigned_report_is_not_credited(self):
        decision = manufacturer_credit_decision(_report(signed=False), "2508")
        self.assertFalse(decision["credited"])

    def test_a_report_past_the_age_limit_is_not_credited(self):
        decision = manufacturer_credit_decision(_report(age_months=40), "2508")
        self.assertFalse(decision["credited"])

    def test_a_report_on_the_age_limit_is_credited(self):
        limit = DEFAULT_DPA_POLICY["max_report_age_months"]
        decision = manufacturer_credit_decision(_report(age_months=limit), "2508")
        self.assertTrue(decision["credited"])

    def test_a_report_covering_too_few_criteria_is_not_credited(self):
        decision = manufacturer_credit_decision(
            _report(criteria_covered=["internal-visual", "package-seal"]), "2508"
        )
        self.assertFalse(decision["credited"])
        self.assertIn("die-attach-integrity", decision["reason"])

    def test_a_report_naming_an_unregistered_criterion_is_refused(self):
        with self.assertRaises(ValueError):
            manufacturer_credit_decision(
                _report(criteria_covered=["internal-visual", "vibration"]), "2508"
            )

    def test_no_report_is_not_credit(self):
        decision = manufacturer_credit_decision(None, "2508")
        self.assertFalse(decision["credited"])

    def test_policy_may_withdraw_credit_entirely(self):
        decision = manufacturer_credit_decision(
            _report(), "2508", _policy(allow_manufacturer_credit=False)
        )
        self.assertFalse(decision["credited"])


class SampleSizingTests(unittest.TestCase):
    def test_a_large_group_is_sampled_proportionally(self):
        self.assertEqual(dpa_sample_size(4000, False), 20)

    def test_a_small_group_falls_back_to_the_floor(self):
        self.assertEqual(dpa_sample_size(100, False), 2)

    def test_a_credited_group_owes_only_the_confirmation_sample(self):
        self.assertEqual(dpa_sample_size(4000, True), 1)

    def test_a_group_its_own_sample_consumes_is_flagged(self):
        plan = group_sample_plan(2, False)
        self.assertFalse(plan["feasible"])
        self.assertEqual(len(plan["findings"]), 1)

    def test_a_zero_sized_group_is_refused(self):
        with self.assertRaises(ValueError):
            dpa_sample_size(0, False)

    def test_a_non_boolean_credit_flag_is_refused(self):
        with self.assertRaises(ValueError):
            dpa_sample_size(4000, "yes")


class DefectRegisterTests(unittest.TestCase):
    def test_a_registered_major_defect_is_categorized_major(self):
        self.assertEqual(categorize_defect("die-crack"), "major")

    def test_a_registered_minor_defect_is_categorized_minor(self):
        self.assertEqual(categorize_defect("tool-mark-on-package"), "minor")

    def test_an_unregistered_defect_code_is_refused(self):
        with self.assertRaises(ValueError):
            categorize_defect("odd-looking-thing")

    def test_the_two_registers_do_not_overlap(self):
        self.assertEqual(MAJOR_DEFECTS & MINOR_DEFECTS, frozenset())

    def test_defects_are_grouped_and_deduplicated(self):
        grouped = categorize_defects(["die-crack", "die-crack", "lead-finish-blemish"])
        self.assertEqual(grouped["major"], ["die-crack"])
        self.assertEqual(grouped["minor"], ["lead-finish-blemish"])


class ConstructionCriteriaTests(unittest.TestCase):
    def test_voiding_inside_both_limits_passes(self):
        result = void_assessment(0.2, 0.05, VOID_LIMITS)
        self.assertTrue(result["within_limits"])

    def test_a_single_large_void_fails_while_the_total_passes(self):
        result = void_assessment(0.3, 0.25, VOID_LIMITS)
        self.assertFalse(result["within_limits"])
        self.assertEqual(result["defects"], ["die-attach-void-excess"])

    def test_a_total_void_exactly_on_its_limit_is_inside_it(self):
        result = void_assessment(0.1 + 0.4, 0.1, VOID_LIMITS)
        self.assertAlmostEqual(result["total_void_fraction"], 0.5, places=9)
        self.assertTrue(result["within_limits"])

    def test_a_largest_void_above_the_total_is_refused(self):
        with self.assertRaises(ValueError):
            void_assessment(0.1, 0.4, VOID_LIMITS)

    def test_inconsistent_void_limits_are_refused(self):
        with self.assertRaises(ValueError):
            void_assessment(0.2, 0.05, {"total_limit": 0.1, "largest_limit": 0.4})

    def test_a_weak_single_bond_fails_while_the_mean_passes(self):
        result = bond_pull_assessment([2.0, 6.0, 6.0, 6.0], 3.0, 4.0)
        self.assertFalse(result["within_limits"])
        self.assertEqual(result["defects"], ["bond-pull-below-limit"])

    def test_a_sample_drifting_low_on_average_fails(self):
        result = bond_pull_assessment([3.2, 3.3, 3.4, 3.5], 3.0, 4.0)
        self.assertFalse(result["within_limits"])

    def test_a_mean_landing_on_its_floor_is_inside_it(self):
        result = bond_pull_assessment([4.1, 3.9], 3.0, 4.0)
        self.assertAlmostEqual(result["mean_observed_g"], 4.0, places=9)
        self.assertTrue(result["within_limits"])

    def test_a_bond_floor_above_the_mean_floor_is_refused(self):
        with self.assertRaises(ValueError):
            bond_pull_assessment([5.0, 5.0], 6.0, 4.0)

    def test_an_empty_pull_sample_is_refused(self):
        with self.assertRaises(ValueError):
            bond_pull_assessment([], 3.0, 4.0)


class DispositionTests(unittest.TestCase):
    def test_a_clean_record_is_accepted(self):
        self.assertEqual(
            group_disposition({"major": [], "minor": []}, False), GROUP_ACCEPTED
        )

    def test_a_minor_observation_is_accepted_with_a_record(self):
        self.assertEqual(
            group_disposition({"major": [], "minor": ["tool-mark-on-package"]}, False),
            GROUP_ACCEPTED_WITH_RECORD,
        )

    def test_one_major_defect_calls_for_a_second_sample(self):
        self.assertEqual(
            group_disposition({"major": ["die-crack"], "minor": []}, False),
            GROUP_RESAMPLE_REQUIRED,
        )

    def test_a_major_defect_found_again_on_the_second_sample_rejects(self):
        self.assertEqual(
            group_disposition({"major": ["die-crack"], "minor": []}, True),
            GROUP_REJECTED,
        )

    def test_two_major_defects_reject_without_a_second_sample(self):
        self.assertEqual(
            group_disposition(
                {"major": ["die-crack", "package-seal-leak"], "minor": []}, False
            ),
            GROUP_REJECTED,
        )

    def test_policy_may_withdraw_the_second_sample_allowance(self):
        self.assertEqual(
            group_disposition(
                {"major": ["die-crack"], "minor": []}, False, _policy(allow_resample=False)
            ),
            GROUP_REJECTED,
        )


class AssessmentTests(unittest.TestCase):
    def test_a_clean_delivery_meets_the_class_scope(self):
        result = assess_destructive_physical_sampling(_case())
        self.assertEqual(result["verdict"], DPA_MEETS_CLASS_TWO_SCOPE)
        self.assertTrue(result["accepted"])
        self.assertEqual(result["total_sample"], 20)

    def test_a_credited_group_is_sampled_down_to_the_confirmation_sample(self):
        case = _case(groups=[_group(manufacturer_report=_report())])
        result = assess_destructive_physical_sampling(case)
        self.assertEqual(result["credited_date_codes"], ["2508"])
        self.assertEqual(result["total_sample"], 1)

    def test_a_group_with_no_teardown_and_no_credit_stops_the_assessment(self):
        case = _case(groups=[_group(teardown_performed=False)])
        result = assess_destructive_physical_sampling(case)
        self.assertEqual(result["verdict"], DPA_NOT_PERFORMED)
        self.assertEqual(result["groups"][0]["disposition"], GROUP_NOT_SAMPLED)

    def test_a_credited_group_needs_no_teardown_of_its_own(self):
        case = _case(
            groups=[_group(teardown_performed=False, manufacturer_report=_report())]
        )
        result = assess_destructive_physical_sampling(case)
        self.assertEqual(result["verdict"], DPA_MEETS_CLASS_TWO_SCOPE)

    def test_a_group_too_small_to_sample_stops_the_assessment(self):
        case = _case(groups=[_group(unit_count=2)])
        result = assess_destructive_physical_sampling(case)
        self.assertEqual(result["verdict"], DPA_SAMPLE_NOT_FEASIBLE)
        self.assertEqual(result["infeasible_date_codes"], ["2508"])

    def test_a_voiding_failure_becomes_a_registered_major_defect(self):
        case = _case(groups=[_group(total_void_fraction=0.7, largest_void_fraction=0.6)])
        result = assess_destructive_physical_sampling(case)
        self.assertIn("die-attach-void-excess", result["groups"][0]["defects"]["major"])
        self.assertEqual(result["verdict"], DPA_RESAMPLE_REQUIRED)

    def test_a_second_sample_still_showing_the_defect_rejects_the_delivery(self):
        case = _case(
            groups=[_group(observed_defects=["die-crack"], resample_performed=True)]
        )
        result = assess_destructive_physical_sampling(case)
        self.assertEqual(result["verdict"], DPA_CONSTRUCTION_REJECTED)

    def test_a_multi_date_code_delivery_is_sampled_group_by_group(self):
        case = _case(
            groups=[_group(), _group(date_code="2441", unit_count=1000)]
        )
        result = assess_destructive_physical_sampling(case)
        self.assertEqual(len(result["groups"]), 2)
        self.assertEqual(result["total_units"], 5000)
        self.assertTrue(any("spans 2 date codes" in f for f in result["findings"]))

    def test_a_repeated_date_code_is_refused(self):
        case = _case(groups=[_group(), _group()])
        with self.assertRaises(ValueError):
            assess_destructive_physical_sampling(case)

    def test_an_empty_delivery_is_refused(self):
        with self.assertRaises(ValueError):
            assess_destructive_physical_sampling(_case(groups=[]))

    def test_a_case_missing_the_bond_floors_is_refused(self):
        case = _case()
        del case["bond_mean_minimum_g"]
        with self.assertRaises(ValueError):
            assess_destructive_physical_sampling(case)

    def test_a_non_mapping_case_is_refused(self):
        with self.assertRaises(ValueError):
            assess_destructive_physical_sampling(["groups"])

    def test_a_minor_observation_travels_with_a_passing_verdict(self):
        case = _case(groups=[_group(observed_defects=["lead-finish-blemish"])])
        result = assess_destructive_physical_sampling(case)
        self.assertEqual(result["verdict"], DPA_MEETS_CLASS_TWO_SCOPE)
        self.assertEqual(result["groups"][0]["disposition"], GROUP_ACCEPTED_WITH_RECORD)


if __name__ == "__main__":
    unittest.main()
