"""Contract tests for the clause 7.3.8 test matrix review item logic."""

import unittest

from q6012_test_matrix_review_item_logic import (
    METHODS,
    activities_for_requirement,
    admissible_activities,
    assess_test_matrix_review,
    condition_gaps,
    coverage_fraction,
    normalise_matrix,
    orphan_activities,
    unknown_requirement_references,
    unverified_requirements,
    validate_activity,
    validate_requirement,
)

CORNERS = ["cold", "ambient", "hot"]


def requirements():
    return [
        {
            "id": "R-01",
            "conditions": CORNERS,
            "methods_allowed": ["test"],
            "critical": True,
        },
        {
            "id": "R-02",
            "conditions": ["ambient"],
            "methods_allowed": ["test", "analysis"],
        },
        {
            "id": "R-03",
            "conditions": ["ambient"],
            "methods_allowed": ["inspection", "review-of-design"],
        },
    ]


def activities():
    return [
        {
            "id": "A-01",
            "method": "test",
            "covers": ["R-01", "R-02"],
            "conditions": ["cold", "ambient", "hot"],
            "pass_criteria": True,
        },
        {
            "id": "A-02",
            "method": "inspection",
            "covers": ["R-03"],
            "conditions": ["ambient"],
            "pass_criteria": True,
        },
    ]


class ValidateRequirementTests(unittest.TestCase):
    def test_identifiers_are_normalised(self):
        record = validate_requirement(requirements()[0])
        self.assertEqual(record["id"], "r-01")
        self.assertEqual(record["conditions"], ["cold", "ambient", "hot"])

    def test_critical_defaults_to_false(self):
        self.assertFalse(validate_requirement(requirements()[1])["critical"])

    def test_repeated_condition_is_collapsed(self):
        requirement = requirements()[1]
        requirement["conditions"] = ["ambient", "Ambient"]
        self.assertEqual(validate_requirement(requirement)["conditions"], ["ambient"])

    def test_unknown_method_rejected(self):
        requirement = requirements()[1]
        requirement["methods_allowed"] = ["demonstration"]
        with self.assertRaises(ValueError):
            validate_requirement(requirement)

    def test_empty_condition_set_rejected(self):
        requirement = requirements()[1]
        requirement["conditions"] = []
        with self.assertRaises(ValueError):
            validate_requirement(requirement)

    def test_missing_key_rejected(self):
        requirement = requirements()[1]
        del requirement["methods_allowed"]
        with self.assertRaises(ValueError):
            validate_requirement(requirement)

    def test_non_boolean_critical_flag_rejected(self):
        requirement = requirements()[1]
        requirement["critical"] = "yes"
        with self.assertRaises(ValueError):
            validate_requirement(requirement)


class ValidateActivityTests(unittest.TestCase):
    def test_returns_normalised_record(self):
        record = validate_activity(activities()[0])
        self.assertEqual(record["id"], "a-01")
        self.assertEqual(record["method"], "test")
        self.assertEqual(record["covers"], ["r-01", "r-02"])

    def test_activity_may_cover_nothing_yet(self):
        activity = activities()[1]
        activity["covers"] = []
        self.assertEqual(validate_activity(activity)["covers"], [])

    def test_unknown_method_rejected(self):
        activity = activities()[1]
        activity["method"] = "hand-waving"
        with self.assertRaises(ValueError):
            validate_activity(activity)

    def test_non_boolean_pass_criteria_rejected(self):
        activity = activities()[1]
        activity["pass_criteria"] = 1
        with self.assertRaises(ValueError):
            validate_activity(activity)

    def test_missing_key_rejected(self):
        activity = activities()[1]
        del activity["conditions"]
        with self.assertRaises(ValueError):
            validate_activity(activity)

    def test_every_method_name_is_accepted(self):
        for method in METHODS:
            activity = activities()[1]
            activity["method"] = method
            self.assertEqual(validate_activity(activity)["method"], method)


class NormaliseMatrixTests(unittest.TestCase):
    def test_returns_both_validated_lists(self):
        reqs, acts = normalise_matrix(requirements(), activities())
        self.assertEqual(len(reqs), 3)
        self.assertEqual(len(acts), 2)

    def test_repeated_requirement_id_rejected(self):
        reqs = requirements() + [requirements()[0]]
        with self.assertRaises(ValueError):
            normalise_matrix(reqs, activities())

    def test_repeated_activity_id_rejected(self):
        acts = activities() + [activities()[0]]
        with self.assertRaises(ValueError):
            normalise_matrix(requirements(), acts)

    def test_empty_requirement_list_rejected(self):
        with self.assertRaises(ValueError):
            normalise_matrix([], activities())

    def test_empty_activity_list_is_allowed_and_leaves_everything_open(self):
        reqs, acts = normalise_matrix(requirements(), [])
        self.assertEqual(acts, [])
        self.assertEqual(len(unverified_requirements(reqs, acts)), 3)


class TraceTests(unittest.TestCase):
    def setUp(self):
        self.reqs, self.acts = normalise_matrix(requirements(), activities())

    def test_forward_trace_finds_the_naming_activity(self):
        named = activities_for_requirement(self.reqs[0], self.acts)
        self.assertEqual([a["id"] for a in named], ["a-01"])

    def test_inadmissible_method_is_named_but_not_admissible(self):
        acts = activities()
        acts[0]["method"] = "analysis"
        reqs, acts = normalise_matrix(requirements(), acts)
        self.assertEqual(len(activities_for_requirement(reqs[0], acts)), 1)
        self.assertEqual(admissible_activities(reqs[0], acts), [])

    def test_activity_without_pass_criteria_is_not_admissible(self):
        acts = activities()
        acts[0]["pass_criteria"] = False
        reqs, acts = normalise_matrix(requirements(), acts)
        self.assertEqual(admissible_activities(reqs[0], acts), [])

    def test_condition_gaps_report_the_missing_corners(self):
        acts = activities()
        acts[0]["conditions"] = ["ambient"]
        reqs, acts = normalise_matrix(requirements(), acts)
        self.assertEqual(condition_gaps(reqs[0], acts), ["cold", "hot"])

    def test_no_condition_gap_when_activities_union_to_the_full_set(self):
        acts = activities()
        acts[0]["conditions"] = ["cold", "ambient"]
        acts.append(
            {
                "id": "A-03",
                "method": "test",
                "covers": ["R-01"],
                "conditions": ["hot"],
                "pass_criteria": True,
            }
        )
        reqs, acts = normalise_matrix(requirements(), acts)
        self.assertEqual(condition_gaps(reqs[0], acts), [])

    def test_inadmissible_activity_does_not_contribute_conditions(self):
        acts = activities()
        acts[0]["conditions"] = ["cold", "ambient"]
        acts.append(
            {
                "id": "A-03",
                "method": "analysis",
                "covers": ["R-01"],
                "conditions": ["hot"],
                "pass_criteria": True,
            }
        )
        reqs, acts = normalise_matrix(requirements(), acts)
        self.assertEqual(condition_gaps(reqs[0], acts), ["hot"])

    def test_unverified_reports_a_requirement_nothing_names(self):
        reqs, acts = normalise_matrix(requirements(), activities()[:1])
        open_items = unverified_requirements(reqs, acts)
        self.assertEqual([i["id"] for i in open_items], ["r-03"])
        self.assertIn("no verification activity", open_items[0]["reason"])

    def test_orphan_activity_is_reported(self):
        acts = activities()
        acts.append(
            {
                "id": "A-99",
                "method": "analysis",
                "covers": [],
                "conditions": ["ambient"],
                "pass_criteria": True,
            }
        )
        reqs, acts = normalise_matrix(requirements(), acts)
        self.assertEqual(orphan_activities(reqs, acts), ["a-99"])

    def test_unknown_reference_is_reported_and_is_not_an_orphan(self):
        acts = activities()
        acts[1]["covers"] = ["R-03", "R-77"]
        reqs, acts = normalise_matrix(requirements(), acts)
        self.assertEqual(unknown_requirement_references(reqs, acts), [("a-02", "r-77")])
        self.assertEqual(orphan_activities(reqs, acts), [])


class CoverageFractionTests(unittest.TestCase):
    def test_full_coverage_is_one(self):
        self.assertAlmostEqual(coverage_fraction(4, 4), 1.0, places=9)

    def test_partial_coverage(self):
        self.assertAlmostEqual(coverage_fraction(3, 2), 2.0 / 3.0, places=9)

    def test_zero_closed_is_zero(self):
        self.assertAlmostEqual(coverage_fraction(3, 0), 0.0, places=9)

    def test_empty_requirement_set_rejected(self):
        with self.assertRaises(ValueError):
            coverage_fraction(0, 0)

    def test_closed_above_total_rejected(self):
        with self.assertRaises(ValueError):
            coverage_fraction(3, 4)

    def test_negative_count_rejected(self):
        with self.assertRaises(ValueError):
            coverage_fraction(3, -1)

    def test_boolean_count_rejected(self):
        with self.assertRaises(ValueError):
            coverage_fraction(3, True)


class AssessTestMatrixReviewTests(unittest.TestCase):
    def _spec(self, **overrides):
        spec = {"requirements": requirements(), "activities": activities()}
        spec.update(overrides)
        return spec

    def test_complete_matrix_closes(self):
        result = assess_test_matrix_review(self._spec())
        self.assertEqual(result["disposition"], "closed")
        self.assertEqual(result["findings"], [])
        self.assertAlmostEqual(result["coverage"], 1.0, places=9)
        self.assertAlmostEqual(result["critical_coverage"], 1.0, places=9)

    def test_missing_activity_opens_the_item_and_lowers_coverage(self):
        result = assess_test_matrix_review(self._spec(activities=activities()[:1]))
        self.assertEqual(result["disposition"], "open")
        self.assertAlmostEqual(result["coverage"], 2.0 / 3.0, places=9)

    def test_critical_coverage_is_reported_apart(self):
        acts = activities()
        acts[0]["covers"] = ["R-02"]
        result = assess_test_matrix_review(self._spec(activities=acts))
        self.assertAlmostEqual(result["critical_coverage"], 0.0, places=9)
        self.assertAlmostEqual(result["coverage"], 2.0 / 3.0, places=9)

    def test_critical_coverage_is_none_when_nothing_is_critical(self):
        reqs = requirements()
        reqs[0]["critical"] = False
        self.assertIsNone(assess_test_matrix_review(self._spec(requirements=reqs))["critical_coverage"])

    def test_wrong_method_opens_the_requirement(self):
        acts = activities()
        acts[1]["method"] = "analysis"
        result = assess_test_matrix_review(self._spec(activities=acts))
        self.assertEqual(result["disposition"], "open")
        self.assertTrue(any("inadmissible" in f for f in result["findings"]))

    def test_condition_gap_opens_the_requirement_and_names_the_corners(self):
        acts = activities()
        acts[0]["conditions"] = ["ambient"]
        result = assess_test_matrix_review(self._spec(activities=acts))
        self.assertTrue(any("cold, hot" in f for f in result["findings"]))

    def test_activity_without_criteria_is_its_own_finding(self):
        acts = activities()
        acts[1]["pass_criteria"] = False
        result = assess_test_matrix_review(self._spec(activities=acts))
        self.assertEqual(result["activities_without_criteria"], ["a-02"])
        self.assertTrue(any("measurable pass criteria" in f for f in result["findings"]))

    def test_orphan_activity_opens_the_item_even_at_full_coverage(self):
        acts = activities()
        acts.append(
            {
                "id": "A-99",
                "method": "analysis",
                "covers": [],
                "conditions": ["ambient"],
                "pass_criteria": True,
            }
        )
        result = assess_test_matrix_review(self._spec(activities=acts))
        self.assertAlmostEqual(result["coverage"], 1.0, places=9)
        self.assertEqual(result["disposition"], "open")

    def test_every_open_requirement_is_reported_not_just_the_first(self):
        result = assess_test_matrix_review(self._spec(activities=[]))
        self.assertEqual(len(result["unverified"]), 3)

    def test_missing_spec_key_rejected(self):
        spec = self._spec()
        del spec["activities"]
        with self.assertRaises(ValueError):
            assess_test_matrix_review(spec)

    def test_non_mapping_spec_rejected(self):
        with self.assertRaises(ValueError):
            assess_test_matrix_review(["requirements"])


if __name__ == "__main__":
    unittest.main()
