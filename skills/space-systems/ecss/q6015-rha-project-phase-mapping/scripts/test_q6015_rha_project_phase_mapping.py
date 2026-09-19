"""Contract tests for the clause 4.4 assurance-to-phase mapping logic."""

import unittest

from q6015_rha_project_phase_mapping_logic import (
    ACTIVITY_WINDOWS,
    PHASE_SEQUENCE,
    activity_window,
    compare_phases,
    map_phase_plan,
    missing_deliverables,
    normalize_activity,
    normalize_phase,
    owed_deliverables,
    phase_deliverables,
    phase_index,
    place_activities,
    place_activity,
    precedence_findings,
)

GOOD_PLAN = {
    "activities": {
        "mission-environment-definition": "0",
        "preliminary-radiation-requirements": "A",
        "requirements-consolidation": "B",
        "early-part-screening": "B",
        "shielding-concept-assessment": "B",
        "part-characterization-testing": "C",
        "equipment-shielding-assessment": "C",
        "hardness-assurance-baseline-freeze": "C",
    },
    "through_phase": "C",
    "deliverables": [
        "mission-environment-specification",
        "preliminary-radiation-requirements-set",
        "consolidated-radiation-requirements",
        "shielding-concept-report",
        "radiation-analysis-report",
        "hardness-assurance-baseline",
    ],
}


class PhaseTokenTests(unittest.TestCase):
    def test_bare_letter_is_canonical(self):
        self.assertEqual(normalize_phase("c"), "C")

    def test_phase_prefix_is_stripped(self):
        self.assertEqual(normalize_phase("Phase B"), "B")

    def test_phase_zero_survives(self):
        self.assertEqual(normalize_phase("phase 0"), "0")

    def test_unknown_phase_rejected(self):
        with self.assertRaises(ValueError):
            normalize_phase("F")

    def test_empty_phase_rejected(self):
        with self.assertRaises(ValueError):
            normalize_phase("   ")

    def test_non_string_phase_rejected(self):
        with self.assertRaises(ValueError):
            normalize_phase(3)

    def test_index_follows_the_sequence(self):
        self.assertEqual(phase_index("0"), 0)
        self.assertEqual(phase_index("E"), len(PHASE_SEQUENCE) - 1)

    def test_comparison_orders_phases(self):
        self.assertEqual(compare_phases("B", "C"), -1)
        self.assertEqual(compare_phases("C", "C"), 0)
        self.assertEqual(compare_phases("D", "A"), 1)


class ActivityWindowTests(unittest.TestCase):
    def test_activity_name_is_normalised(self):
        self.assertEqual(
            normalize_activity("  Early Part  Screening "), "early-part-screening"
        )

    def test_window_is_inclusive_pair(self):
        self.assertEqual(activity_window("early-part-screening"), ("A", "B"))

    def test_freeze_is_pinned_to_one_phase(self):
        earliest, latest = activity_window("hardness-assurance-baseline-freeze")
        self.assertEqual(earliest, latest)

    def test_unknown_activity_rejected(self):
        with self.assertRaises(ValueError):
            activity_window("radiation-tea-break")

    def test_every_window_is_ordered_and_in_sequence(self):
        for activity, (earliest, latest) in ACTIVITY_WINDOWS.items():
            self.assertIn(earliest, PHASE_SEQUENCE, activity)
            self.assertIn(latest, PHASE_SEQUENCE, activity)
            self.assertLessEqual(phase_index(earliest), phase_index(latest), activity)


class PlacementTests(unittest.TestCase):
    def test_activity_inside_its_window_is_in_window(self):
        record = place_activity("part-characterization-testing", "B")
        self.assertEqual(record["status"], "in-window")

    def test_activity_before_its_window_is_too_early(self):
        record = place_activity("flight-lot-verification-testing", "B")
        self.assertEqual(record["status"], "too-early")

    def test_activity_after_its_window_is_too_late(self):
        record = place_activity("mission-environment-definition", "C")
        self.assertEqual(record["status"], "too-late")

    def test_window_edges_are_inside_the_window(self):
        self.assertEqual(place_activity("early-part-screening", "A")["status"], "in-window")
        self.assertEqual(place_activity("early-part-screening", "B")["status"], "in-window")

    def test_placements_are_ordered_by_phase(self):
        placements = place_activities(GOOD_PLAN["activities"])
        indices = [phase_index(rec["phase"]) for rec in placements]
        self.assertEqual(indices, sorted(indices))

    def test_empty_activity_set_rejected(self):
        with self.assertRaises(ValueError):
            place_activities({})

    def test_non_mapping_activity_set_rejected(self):
        with self.assertRaises(ValueError):
            place_activities(["mission-environment-definition"])


class PrecedenceTests(unittest.TestCase):
    def test_correct_order_has_no_finding(self):
        self.assertEqual(precedence_findings(place_activities(GOOD_PLAN["activities"])), [])

    def test_consumer_before_producer_is_flagged(self):
        placements = place_activities(
            {
                "requirements-consolidation": "B",
                "part-characterization-testing": "B",
                "hardness-assurance-baseline-freeze": "C",
                "flight-lot-verification-testing": "C",
                "radiation-action-closeout": "D",
                "equipment-shielding-assessment": "C",
                "shielding-concept-assessment": "C",
            }
        )
        findings = precedence_findings(placements)
        self.assertEqual(len(findings), 0)

    def test_inverted_pair_is_reported(self):
        placements = [
            {"activity": "mission-environment-definition", "phase": "B"},
            {"activity": "preliminary-radiation-requirements", "phase": "A"},
        ]
        findings = precedence_findings(placements)
        self.assertEqual(len(findings), 1)
        self.assertIn("preliminary-radiation-requirements", findings[0])

    def test_same_phase_pair_is_allowed(self):
        placements = [
            {"activity": "mission-environment-definition", "phase": "A"},
            {"activity": "preliminary-radiation-requirements", "phase": "A"},
        ]
        self.assertEqual(precedence_findings(placements), [])

    def test_pair_with_one_side_absent_is_not_graded(self):
        placements = [{"activity": "radiation-action-closeout", "phase": "D"}]
        self.assertEqual(precedence_findings(placements), [])

    def test_malformed_placement_rejected(self):
        with self.assertRaises(ValueError):
            precedence_findings([{"activity": "radiation-action-closeout"}])


class DeliverableTests(unittest.TestCase):
    def test_phase_deliverables_are_returned(self):
        self.assertIn("hardness-assurance-baseline", phase_deliverables("C"))

    def test_owed_set_accumulates_from_phase_zero(self):
        owed = owed_deliverables("B")
        self.assertIn("mission-environment-specification", owed)
        self.assertIn("shielding-concept-report", owed)
        self.assertNotIn("radiation-analysis-report", owed)

    def test_declared_deliverable_is_not_missing(self):
        missing = missing_deliverables(
            ["Mission Environment Specification"], "0"
        )
        self.assertEqual(missing, [])

    def test_absent_deliverable_is_reported_in_owed_order(self):
        missing = missing_deliverables(["mission-environment-specification"], "B")
        self.assertEqual(
            missing,
            [
                "preliminary-radiation-requirements-set",
                "consolidated-radiation-requirements",
                "shielding-concept-report",
            ],
        )

    def test_non_sequence_deliverables_rejected(self):
        with self.assertRaises(ValueError):
            missing_deliverables("mission-environment-specification", "A")

    def test_non_string_deliverable_rejected(self):
        with self.assertRaises(ValueError):
            missing_deliverables([7], "A")


class PlanMappingTests(unittest.TestCase):
    def test_complete_plan_is_compliant(self):
        result = map_phase_plan(GOOD_PLAN)
        self.assertTrue(result["compliant"])
        self.assertEqual(result["findings"], [])

    def test_out_of_phase_activity_fails_the_plan(self):
        plan = dict(GOOD_PLAN)
        activities = dict(GOOD_PLAN["activities"])
        activities["mission-environment-definition"] = "C"
        plan["activities"] = activities
        result = map_phase_plan(plan)
        self.assertFalse(result["compliant"])
        self.assertEqual(len(result["out_of_phase"]), 1)

    def test_missing_deliverable_fails_the_plan(self):
        plan = dict(GOOD_PLAN)
        plan["deliverables"] = GOOD_PLAN["deliverables"][:-1]
        result = map_phase_plan(plan)
        self.assertFalse(result["compliant"])
        self.assertEqual(result["missing_deliverables"], ["hardness-assurance-baseline"])

    def test_through_phase_limits_what_is_owed(self):
        plan = dict(GOOD_PLAN)
        plan["through_phase"] = "A"
        plan["deliverables"] = [
            "mission-environment-specification",
            "preliminary-radiation-requirements-set",
        ]
        activities = {
            "mission-environment-definition": "0",
            "preliminary-radiation-requirements": "A",
        }
        plan["activities"] = activities
        result = map_phase_plan(plan)
        self.assertEqual(result["missing_deliverables"], [])

    def test_missing_plan_key_rejected(self):
        plan = dict(GOOD_PLAN)
        del plan["through_phase"]
        with self.assertRaises(ValueError):
            map_phase_plan(plan)

    def test_non_mapping_plan_rejected(self):
        with self.assertRaises(ValueError):
            map_phase_plan(["activities"])

    def test_unknown_activity_in_plan_rejected(self):
        plan = dict(GOOD_PLAN)
        plan["activities"] = {"paint-the-spacecraft": "B"}
        with self.assertRaises(ValueError):
            map_phase_plan(plan)


if __name__ == "__main__":
    unittest.main()
