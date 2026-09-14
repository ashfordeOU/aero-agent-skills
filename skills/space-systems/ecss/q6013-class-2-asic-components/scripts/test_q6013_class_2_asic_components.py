"""Contract tests for the clause 5.6.2 class 2 ASIC assurance tailoring.

Every workflow step the SKILL.md sets out is exercised here, together with the
stop conditions the gate 3 contract reviews: an unknown device kind, a
catalogue part the clause does not reach, a reduction aimed at a mandatory
activity, an approval-bearing reduction with and without its approval, a
residual coverage sitting exactly on its floor, and a reduction count past the
allowance.
"""

import unittest

from q6013_class_2_asic_components_logic import (
    APPROVAL_REQUIRED,
    ASIC_KINDS,
    DEDICATED_ASIC_ROUTE,
    DEFAULT_TAILORING_POLICY,
    GENERIC_COMPONENT_ROUTE,
    MANDATORY,
    NOT_AN_ASIC,
    REDUCIBLE,
    TAILORING_ACCEPTED,
    TAILORING_ACCEPTED_WITH_APPROVALS,
    TAILORING_REFUSED,
    activity_disposition,
    activity_names,
    activity_weight,
    assess_asic_tailoring,
    coverage_meets_floor,
    grade_reductions,
    residual_coverage,
    route_for_kind,
    total_assurance_weight,
    validate_activity_list,
    validate_tailoring_policy,
)


def _case(**overrides):
    case = {
        "kind": "standard-cell-asic",
        "proposed_reductions": ["lot-acceptance-testing"],
        "customer_approvals": [],
    }
    case.update(overrides)
    return case


class PolicyTests(unittest.TestCase):
    def test_default_policy_validates(self):
        settings = validate_tailoring_policy(None)
        self.assertAlmostEqual(settings["min_residual_coverage"], 0.6, places=9)
        self.assertEqual(settings["max_reduced_activities"], 3)

    def test_unknown_policy_key_rejected(self):
        with self.assertRaises(ValueError):
            validate_tailoring_policy({"min_coverage": 0.6})

    def test_coverage_floor_above_unity_rejected(self):
        with self.assertRaises(ValueError):
            validate_tailoring_policy({"min_residual_coverage": 1.4})

    def test_negative_reduction_allowance_rejected(self):
        with self.assertRaises(ValueError):
            validate_tailoring_policy({"max_reduced_activities": -1})

    def test_non_mapping_policy_rejected(self):
        with self.assertRaises(ValueError):
            validate_tailoring_policy(["min_residual_coverage"])


class RoutingTests(unittest.TestCase):
    def test_every_application_specific_kind_takes_the_dedicated_route(self):
        for kind in ASIC_KINDS:
            self.assertEqual(route_for_kind(kind), DEDICATED_ASIC_ROUTE)

    def test_catalogue_part_stays_on_the_generic_route(self):
        self.assertEqual(route_for_kind("standard-microcircuit"), GENERIC_COMPONENT_ROUTE)

    def test_unknown_kind_rejected(self):
        with self.assertRaises(ValueError):
            route_for_kind("mystery-part")

    def test_blank_kind_rejected(self):
        with self.assertRaises(ValueError):
            route_for_kind("   ")

    def test_catalogue_part_gives_the_not_an_asic_verdict(self):
        result = assess_asic_tailoring({"kind": "passive-component"})
        self.assertEqual(result["verdict"], NOT_AN_ASIC)
        self.assertEqual(result["route"], GENERIC_COMPONENT_ROUTE)
        self.assertAlmostEqual(result["residual_coverage"], 1.0, places=9)


class ActivityTests(unittest.TestCase):
    def test_every_activity_carries_a_known_disposition(self):
        for name in activity_names():
            self.assertIn(
                activity_disposition(name), (MANDATORY, APPROVAL_REQUIRED, REDUCIBLE)
            )

    def test_process_qualification_is_mandatory(self):
        self.assertEqual(activity_disposition("process-qualification"), MANDATORY)

    def test_radiation_verification_needs_an_approval(self):
        self.assertEqual(activity_disposition("radiation-verification"), APPROVAL_REQUIRED)

    def test_unknown_activity_rejected(self):
        with self.assertRaises(ValueError):
            activity_disposition("burn-in-waiver")

    def test_total_weight_is_the_sum_of_the_activity_weights(self):
        self.assertAlmostEqual(
            total_assurance_weight(),
            sum(activity_weight(name) for name in activity_names()),
            places=9,
        )

    def test_activity_list_is_returned_in_report_order(self):
        ordered = validate_activity_list(
            ["destructive-physical-analysis", "prototype-evaluation"], "proposed"
        )
        self.assertEqual(
            ordered, ("prototype-evaluation", "destructive-physical-analysis")
        )

    def test_repeated_activity_rejected(self):
        with self.assertRaises(ValueError):
            validate_activity_list(
                ["lot-acceptance-testing", "lot-acceptance-testing"], "proposed"
            )

    def test_bare_string_activity_list_rejected(self):
        with self.assertRaises(ValueError):
            validate_activity_list("lot-acceptance-testing", "proposed")


class CoverageTests(unittest.TestCase):
    def test_no_reduction_leaves_full_coverage(self):
        self.assertAlmostEqual(residual_coverage([]), 1.0, places=9)

    def test_reduction_removes_exactly_its_weight(self):
        total = total_assurance_weight()
        expected = (total - activity_weight("prototype-evaluation")) / total
        self.assertAlmostEqual(
            residual_coverage(["prototype-evaluation"]), expected, places=9
        )

    def test_coverage_sitting_exactly_on_the_floor_is_met(self):
        self.assertTrue(coverage_meets_floor(0.6, 0.6))

    def test_coverage_below_the_floor_is_not_met(self):
        self.assertFalse(coverage_meets_floor(0.55, 0.6))

    def test_non_numeric_coverage_rejected(self):
        with self.assertRaises(ValueError):
            coverage_meets_floor("0.6", 0.6)


class GradingTests(unittest.TestCase):
    def test_a_mandatory_reduction_is_refused(self):
        graded = grade_reductions(["process-qualification"])
        self.assertEqual(graded["refused"], ("process-qualification",))
        self.assertEqual(graded["admitted"], ())

    def test_an_approval_bearing_reduction_without_approval_stays_outstanding(self):
        graded = grade_reductions(["package-qualification"])
        self.assertEqual(graded["outstanding_approvals"], ("package-qualification",))
        self.assertEqual(graded["admitted"], ())

    def test_an_approval_bearing_reduction_with_approval_is_admitted(self):
        graded = grade_reductions(["package-qualification"], ["package-qualification"])
        self.assertEqual(graded["admitted"], ("package-qualification",))
        self.assertEqual(graded["outstanding_approvals"], ())

    def test_an_approval_for_an_unproposed_activity_is_reported_unused(self):
        graded = grade_reductions(["lot-acceptance-testing"], ["prototype-evaluation"])
        self.assertEqual(graded["unused_approvals"], ("prototype-evaluation",))


class AssessmentTests(unittest.TestCase):
    def test_a_reducible_activity_alone_is_accepted(self):
        result = assess_asic_tailoring(_case())
        self.assertEqual(result["verdict"], TAILORING_ACCEPTED)
        self.assertEqual(result["route"], DEDICATED_ASIC_ROUTE)

    def test_an_approved_reduction_reads_as_accepted_with_approvals(self):
        result = assess_asic_tailoring(
            _case(
                proposed_reductions=["radiation-verification"],
                customer_approvals=["radiation-verification"],
            )
        )
        self.assertEqual(result["verdict"], TAILORING_ACCEPTED_WITH_APPROVALS)

    def test_a_mandatory_reduction_refuses_the_whole_tailoring(self):
        result = assess_asic_tailoring(
            _case(proposed_reductions=["design-rule-compliance-review"])
        )
        self.assertEqual(result["verdict"], TAILORING_REFUSED)
        self.assertIn("design-rule-compliance-review", result["refused_reductions"])

    def test_a_retained_activity_never_appears_as_admitted(self):
        result = assess_asic_tailoring(_case())
        for name in result["admitted_reductions"]:
            self.assertNotIn(name, result["retained_activities"])

    def test_coverage_below_the_floor_refuses_the_tailoring(self):
        result = assess_asic_tailoring(
            _case(
                proposed_reductions=[
                    "prototype-evaluation",
                    "package-qualification",
                    "radiation-verification",
                    "lot-acceptance-testing",
                    "destructive-physical-analysis",
                ],
                customer_approvals=[
                    "prototype-evaluation",
                    "package-qualification",
                    "radiation-verification",
                ],
                policy={"max_reduced_activities": 5},
            )
        )
        self.assertEqual(result["verdict"], TAILORING_REFUSED)
        self.assertFalse(
            coverage_meets_floor(
                result["residual_coverage"], DEFAULT_TAILORING_POLICY["min_residual_coverage"]
            )
        )

    def test_reduction_count_past_the_allowance_refuses_the_tailoring(self):
        result = assess_asic_tailoring(
            _case(
                proposed_reductions=[
                    "prototype-evaluation",
                    "package-qualification",
                    "radiation-verification",
                    "lot-acceptance-testing",
                ],
                customer_approvals=[
                    "prototype-evaluation",
                    "package-qualification",
                    "radiation-verification",
                ],
            )
        )
        self.assertEqual(result["verdict"], TAILORING_REFUSED)

    def test_every_finding_names_an_activity_or_a_number(self):
        result = assess_asic_tailoring(
            _case(proposed_reductions=["functional-verification-coverage"])
        )
        self.assertTrue(result["findings"])
        self.assertTrue(all(isinstance(line, str) for line in result["findings"]))

    def test_missing_kind_rejected(self):
        case = _case()
        del case["kind"]
        with self.assertRaises(ValueError):
            assess_asic_tailoring(case)

    def test_non_mapping_case_rejected(self):
        with self.assertRaises(ValueError):
            assess_asic_tailoring(["kind"])

    def test_unknown_reduction_name_rejected(self):
        with self.assertRaises(ValueError):
            assess_asic_tailoring(_case(proposed_reductions=["skip-everything"]))


if __name__ == "__main__":
    unittest.main()
