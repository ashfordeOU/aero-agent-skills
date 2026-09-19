"""Contract tests for the clause 5.1.3 device engineering flow logic."""

import unittest

from e2040_device_engineering_development_flow_logic import (
    MILESTONE_PHASE,
    MILESTONE_SEQUENCE,
    PHASE_SEQUENCE,
    activities_by_milestone,
    assess_development_flow,
    build_activity_index,
    dependency_violations,
    longest_dependency_chain,
    milestone_index,
    milestone_phase,
    milestones_without_closure,
    normalize_milestone,
    validate_activity,
    validate_flow,
)

FULL_FLOW = ["prr", "srr", "pdr", "cdr", "qr", "ar"]


def base_activities():
    return [
        {"id": "ACT-REQ", "closes_at": "srr", "title": "device requirements baseline"},
        {"id": "ACT-ARCH", "closes_at": "pdr", "depends_on": ["ACT-REQ"]},
        {"id": "ACT-DETAIL", "closes_at": "cdr", "depends_on": ["ACT-ARCH"]},
        {"id": "ACT-QUAL", "closes_at": "qr", "depends_on": ["ACT-DETAIL"]},
        {"id": "ACT-ACCEPT", "closes_at": "ar", "depends_on": ["ACT-QUAL"]},
        {"id": "ACT-FEAS", "closes_at": "prr"},
    ]


class MilestoneTests(unittest.TestCase):
    def test_canonical_milestone_passes_through(self):
        self.assertEqual(normalize_milestone("cdr"), "cdr")

    def test_spelled_out_review_is_folded(self):
        self.assertEqual(normalize_milestone("Critical Design Review"), "cdr")

    def test_delivery_review_folds_to_acceptance(self):
        self.assertEqual(normalize_milestone("delivery-review"), "ar")

    def test_index_follows_the_review_order(self):
        self.assertLess(milestone_index("pdr"), milestone_index("cdr"))

    def test_every_milestone_maps_to_a_phase(self):
        for milestone in MILESTONE_SEQUENCE:
            self.assertIn(MILESTONE_PHASE[milestone], PHASE_SEQUENCE)

    def test_phase_lookup_folds_the_spelling(self):
        self.assertEqual(milestone_phase("Qualification Review"), "phase-d")

    def test_unknown_milestone_rejected(self):
        with self.assertRaises(ValueError):
            normalize_milestone("go-no-go")

    def test_blank_milestone_rejected(self):
        with self.assertRaises(ValueError):
            normalize_milestone("  ")


class FlowTests(unittest.TestCase):
    def test_full_flow_is_accepted(self):
        self.assertEqual(validate_flow(FULL_FLOW), FULL_FLOW)

    def test_reduced_flow_is_accepted(self):
        self.assertEqual(validate_flow(["srr", "cdr", "ar"]), ["srr", "cdr", "ar"])

    def test_spellings_are_folded_in_the_flow(self):
        self.assertEqual(
            validate_flow(["Preliminary Design Review", "cdr"]), ["pdr", "cdr"]
        )

    def test_out_of_order_flow_rejected(self):
        with self.assertRaises(ValueError):
            validate_flow(["cdr", "pdr"])

    def test_repeated_milestone_rejected(self):
        with self.assertRaises(ValueError):
            validate_flow(["pdr", "pdr"])

    def test_empty_flow_rejected(self):
        with self.assertRaises(ValueError):
            validate_flow([])

    def test_string_flow_rejected(self):
        with self.assertRaises(ValueError):
            validate_flow("pdr")


class ActivityTests(unittest.TestCase):
    def test_activity_is_folded(self):
        record = validate_activity({"id": " A1 ", "closes_at": "Critical Design Review"})
        self.assertEqual(record["id"], "A1")
        self.assertEqual(record["closes_at"], "cdr")

    def test_dependencies_default_to_empty(self):
        self.assertEqual(validate_activity({"id": "A1", "closes_at": "cdr"})["depends_on"], [])

    def test_missing_closes_at_rejected(self):
        with self.assertRaises(ValueError):
            validate_activity({"id": "A1"})

    def test_self_dependency_rejected(self):
        with self.assertRaises(ValueError):
            validate_activity({"id": "A1", "closes_at": "cdr", "depends_on": ["A1"]})

    def test_repeated_dependency_rejected(self):
        with self.assertRaises(ValueError):
            validate_activity(
                {"id": "A1", "closes_at": "cdr", "depends_on": ["A2", "A2"]}
            )

    def test_string_dependency_list_rejected(self):
        with self.assertRaises(ValueError):
            validate_activity({"id": "A1", "closes_at": "cdr", "depends_on": "A2"})

    def test_duplicate_activity_id_rejected(self):
        activities = base_activities()
        activities.append(dict(activities[0]))
        with self.assertRaises(ValueError):
            build_activity_index(activities)

    def test_index_holds_every_activity(self):
        self.assertEqual(len(build_activity_index(base_activities())), 6)


class GroupingTests(unittest.TestCase):
    def test_grouping_uses_the_declared_flow(self):
        index = build_activity_index(base_activities())
        grouped = activities_by_milestone(index, FULL_FLOW)["grouped"]
        self.assertEqual(set(grouped), set(FULL_FLOW))

    def test_activity_lands_on_its_milestone(self):
        index = build_activity_index(base_activities())
        grouped = activities_by_milestone(index, FULL_FLOW)["grouped"]
        self.assertEqual(grouped["cdr"], ["ACT-DETAIL"])

    def test_activity_outside_a_reduced_flow_is_named(self):
        index = build_activity_index(base_activities())
        result = activities_by_milestone(index, ["srr", "pdr", "cdr"])
        self.assertIn("ACT-QUAL", result["outside_the_flow"])

    def test_milestone_with_no_activity_is_named(self):
        activities = [a for a in base_activities() if a["closes_at"] != "prr"]
        index = build_activity_index(activities)
        self.assertEqual(milestones_without_closure(index, FULL_FLOW), ["prr"])

    def test_full_coverage_leaves_no_empty_milestone(self):
        index = build_activity_index(base_activities())
        self.assertEqual(milestones_without_closure(index, FULL_FLOW), [])


class DependencyTests(unittest.TestCase):
    def test_well_ordered_activities_have_no_violation(self):
        index = build_activity_index(base_activities())
        self.assertEqual(dependency_violations(index)["violations"], [])

    def test_activity_gated_before_its_dependency_is_flagged(self):
        activities = base_activities()
        activities[1]["closes_at"] = "prr"
        index = build_activity_index(activities)
        violations = dependency_violations(index)["violations"]
        self.assertEqual(violations[0]["activity"], "ACT-ARCH")

    def test_same_milestone_dependency_is_allowed(self):
        activities = base_activities()
        activities[1]["closes_at"] = "srr"
        index = build_activity_index(activities)
        self.assertEqual(dependency_violations(index)["violations"], [])

    def test_unknown_dependency_is_reported(self):
        activities = base_activities()
        activities[0]["depends_on"] = ["ACT-GHOST"]
        index = build_activity_index(activities)
        self.assertEqual(
            dependency_violations(index)["unknown_dependencies"][0]["dependency"],
            "ACT-GHOST",
        )

    def test_longest_chain_runs_the_whole_development(self):
        index = build_activity_index(base_activities())
        self.assertEqual(
            longest_dependency_chain(index),
            ["ACT-REQ", "ACT-ARCH", "ACT-DETAIL", "ACT-QUAL", "ACT-ACCEPT"],
        )

    def test_independent_activities_give_a_chain_of_one(self):
        index = build_activity_index(
            [{"id": "A1", "closes_at": "cdr"}, {"id": "A2", "closes_at": "qr"}]
        )
        self.assertEqual(len(longest_dependency_chain(index)), 1)

    def test_dependency_loop_rejected(self):
        index = build_activity_index(
            [
                {"id": "A1", "closes_at": "cdr", "depends_on": ["A2"]},
                {"id": "A2", "closes_at": "cdr", "depends_on": ["A1"]},
            ]
        )
        with self.assertRaises(ValueError):
            longest_dependency_chain(index)

    def test_empty_index_gives_an_empty_chain(self):
        self.assertEqual(longest_dependency_chain({}), [])


class AssessmentTests(unittest.TestCase):
    def _spec(self, **overrides):
        spec = {"flow": list(FULL_FLOW), "activities": base_activities()}
        spec.update(overrides)
        return spec

    def test_complete_flow_is_compliant(self):
        result = assess_development_flow(self._spec())
        self.assertTrue(result["compliant"])
        self.assertEqual(result["findings"], [])

    def test_phases_are_reported_alongside_the_flow(self):
        result = assess_development_flow(self._spec())
        self.assertEqual(result["phases"][0], "phase-a")
        self.assertEqual(result["phases"][-1], "phase-d")

    def test_longest_chain_length_is_reported(self):
        result = assess_development_flow(self._spec())
        self.assertEqual(result["longest_chain_length"], 5)

    def test_omitted_milestone_is_flagged(self):
        activities = [a for a in base_activities() if a["closes_at"] != "prr"]
        result = assess_development_flow(
            self._spec(flow=["srr", "pdr", "cdr", "qr", "ar"], activities=activities)
        )
        self.assertFalse(result["compliant"])
        self.assertTrue(any("omits prr" in f for f in result["findings"]))

    def test_activity_outside_the_flow_is_flagged(self):
        result = assess_development_flow(self._spec(flow=["srr", "pdr", "cdr"]))
        self.assertTrue(any("does not hold" in f for f in result["findings"]))

    def test_empty_milestone_is_flagged(self):
        activities = [a for a in base_activities() if a["closes_at"] != "prr"]
        result = assess_development_flow(self._spec(activities=activities))
        self.assertIn("prr", result["milestones_without_closure"])

    def test_dependency_violation_is_flagged(self):
        activities = base_activities()
        activities[3]["closes_at"] = "pdr"
        result = assess_development_flow(self._spec(activities=activities))
        self.assertTrue(result["dependency_violations"])
        self.assertFalse(result["compliant"])

    def test_unknown_dependency_is_flagged(self):
        activities = base_activities()
        activities[0]["depends_on"] = ["ACT-GHOST"]
        result = assess_development_flow(self._spec(activities=activities))
        self.assertTrue(result["unknown_dependencies"])

    def test_empty_activity_set_rejected(self):
        with self.assertRaises(ValueError):
            assess_development_flow({"flow": FULL_FLOW, "activities": []})

    def test_missing_flow_key_rejected(self):
        with self.assertRaises(ValueError):
            assess_development_flow({"activities": base_activities()})

    def test_non_mapping_spec_rejected(self):
        with self.assertRaises(ValueError):
            assess_development_flow(["flow"])

    def test_out_of_order_flow_rejected_by_the_assessment(self):
        with self.assertRaises(ValueError):
            assess_development_flow(self._spec(flow=["cdr", "srr"]))


if __name__ == "__main__":
    unittest.main()
