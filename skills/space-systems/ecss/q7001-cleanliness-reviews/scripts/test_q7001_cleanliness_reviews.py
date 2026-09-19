#!/usr/bin/env python3
"""Contract test for cleanliness inputs to readiness reviews (offline)."""

import copy
import unittest

from q7001_cleanliness_reviews_logic import (
    ACTION_SEVERITIES,
    ACTION_WEIGHTS,
    CDR,
    FAR,
    MRR,
    PDR,
    REVIEW_ITEMS,
    REVIEW_TYPES,
    SENSITIVITY_CRITICAL,
    SENSITIVITY_LEVELS,
    SENSITIVITY_SENSITIVE,
    SENSITIVITY_STANDARD,
    SEVERITY_MAJOR,
    SEVERITY_MINOR,
    SEVERITY_OBSERVATION,
    TRR,
    VERDICT_CONDITIONAL,
    VERDICT_NOT_READY,
    VERDICT_READY,
    action_load,
    assess_cleanliness_review,
    normalise_action,
    pack_shortfall,
    required_items,
    submitted_set,
)

FULL_CDR_PACK = sorted(required_items(CDR, SENSITIVITY_STANDARD))

CASE = {
    "item": "star-tracker-baffle",
    "review": CDR,
    "sensitivity": SENSITIVITY_STANDARD,
    "submitted": FULL_CDR_PACK,
    "actions": [
        {"id": "CC-011", "severity": SEVERITY_OBSERVATION, "closed": False},
        {"id": "CC-012", "severity": SEVERITY_MAJOR, "closed": True},
    ],
}


def _case(**overrides):
    case = copy.deepcopy(CASE)
    case.update(overrides)
    return case


class PackDerivationTests(unittest.TestCase):
    def test_every_review_type_owes_a_pack(self):
        for review in REVIEW_TYPES:
            self.assertTrue(required_items(review, SENSITIVITY_STANDARD))

    def test_the_pack_is_a_function_of_the_review(self):
        self.assertNotEqual(
            sorted(required_items(PDR, SENSITIVITY_STANDARD)),
            sorted(required_items(TRR, SENSITIVITY_STANDARD)),
        )

    def test_a_design_review_wants_the_budget_apportionment(self):
        self.assertIn(
            "contamination-budget-apportionment",
            required_items(PDR, SENSITIVITY_STANDARD),
        )

    def test_a_test_readiness_review_wants_the_incoming_measurement(self):
        self.assertIn(
            "incoming-cleanliness-measurement",
            required_items(TRR, SENSITIVITY_STANDARD),
        )

    def test_acceptance_wants_the_open_nonconformance_list(self):
        self.assertIn(
            "open-contamination-nonconformance-list",
            required_items(FAR, SENSITIVITY_STANDARD),
        )

    def test_sensitive_hardware_adds_the_sensitivity_analysis(self):
        base = required_items(CDR, SENSITIVITY_STANDARD)
        wider = required_items(CDR, SENSITIVITY_SENSITIVE)
        self.assertNotIn("contamination-sensitivity-analysis", base)
        self.assertIn("contamination-sensitivity-analysis", wider)

    def test_critical_hardware_also_owes_the_end_of_life_prediction(self):
        wider = required_items(CDR, SENSITIVITY_CRITICAL)
        self.assertTrue(wider["end-of-life-performance-prediction"])

    def test_sensitivity_never_shrinks_the_pack(self):
        for review in REVIEW_TYPES:
            base = set(required_items(review, SENSITIVITY_STANDARD))
            for level in SENSITIVITY_LEVELS:
                self.assertTrue(base.issubset(set(required_items(review, level))))

    def test_unknown_review_rejected(self):
        with self.assertRaises(ValueError):
            required_items("mission-close-out-review", SENSITIVITY_STANDARD)

    def test_unknown_sensitivity_rejected(self):
        with self.assertRaises(ValueError):
            required_items(CDR, "very-sensitive")

    def test_every_review_declares_at_least_one_mandatory_item(self):
        for review in REVIEW_TYPES:
            self.assertTrue(any(REVIEW_ITEMS[review].values()))


class ShortfallTests(unittest.TestCase):
    def test_a_full_pack_leaves_nothing_absent(self):
        result = pack_shortfall(CDR, SENSITIVITY_STANDARD, FULL_CDR_PACK)
        self.assertEqual(result["missing_mandatory"], ())
        self.assertEqual(result["missing_supporting"], ())
        self.assertAlmostEqual(result["mandatory_completeness"], 1.0, places=9)

    def test_a_missing_mandatory_item_is_named(self):
        pack = [n for n in FULL_CDR_PACK if n != "contamination-transport-model"]
        result = pack_shortfall(CDR, SENSITIVITY_STANDARD, pack)
        self.assertEqual(
            result["missing_mandatory"], ("contamination-transport-model",)
        )

    def test_a_missing_supporting_item_does_not_count_as_mandatory(self):
        pack = [
            n for n in FULL_CDR_PACK if n != "materials-outgassing-screening-record"
        ]
        result = pack_shortfall(CDR, SENSITIVITY_STANDARD, pack)
        self.assertEqual(result["missing_mandatory"], ())
        self.assertEqual(
            result["missing_supporting"], ("materials-outgassing-screening-record",)
        )
        self.assertAlmostEqual(result["mandatory_completeness"], 1.0, places=9)

    def test_completeness_counts_mandatory_items_only(self):
        pack = [n for n in FULL_CDR_PACK if n != "contamination-requirements"]
        result = pack_shortfall(CDR, SENSITIVITY_STANDARD, pack)
        self.assertEqual(result["mandatory_total"], 5)
        self.assertEqual(result["mandatory_held"], 4)
        self.assertAlmostEqual(result["mandatory_completeness"], 0.8, places=9)

    def test_extra_material_is_reported_not_credited(self):
        result = pack_shortfall(
            CDR, SENSITIVITY_STANDARD, FULL_CDR_PACK + ["thermal-model-report"]
        )
        self.assertEqual(result["extra_submitted"], ("thermal-model-report",))
        self.assertAlmostEqual(result["mandatory_completeness"], 1.0, places=9)

    def test_an_empty_pack_holds_no_mandatory_item(self):
        result = pack_shortfall(CDR, SENSITIVITY_STANDARD, [])
        self.assertEqual(result["mandatory_held"], 0)
        self.assertAlmostEqual(result["mandatory_completeness"], 0.0, places=9)

    def test_submitted_must_be_a_list(self):
        with self.assertRaises(ValueError):
            submitted_set("contamination-requirements")

    def test_blank_submitted_entry_rejected(self):
        with self.assertRaises(ValueError):
            submitted_set(["contamination-requirements", "  "])


class ActionLoadTests(unittest.TestCase):
    def test_a_closed_action_carries_no_load(self):
        result = action_load([{"id": "CC-001", "severity": SEVERITY_MAJOR, "closed": True}])
        self.assertEqual(result["open_total"], 0)
        self.assertFalse(result["has_major"])

    def test_an_open_major_is_visible(self):
        result = action_load([{"id": "CC-002", "severity": SEVERITY_MAJOR}])
        self.assertTrue(result["has_major"])
        self.assertEqual(result["weighted_load"], ACTION_WEIGHTS[SEVERITY_MAJOR])

    def test_several_minors_weigh_less_than_a_major_veto(self):
        minors = action_load(
            [{"id": "CC-00%d" % i, "severity": SEVERITY_MINOR} for i in range(3)]
        )
        self.assertFalse(minors["has_major"])
        self.assertEqual(minors["weighted_load"], 6)

    def test_an_observation_adds_no_weight(self):
        result = action_load([{"id": "CC-003", "severity": SEVERITY_OBSERVATION}])
        self.assertEqual(result["weighted_load"], 0)
        self.assertEqual(result["open_total"], 1)

    def test_every_severity_has_a_weight(self):
        for severity in ACTION_SEVERITIES:
            self.assertIn(severity, ACTION_WEIGHTS)

    def test_no_actions_is_a_clear_load(self):
        self.assertEqual(action_load(None)["open_total"], 0)

    def test_unknown_severity_rejected(self):
        with self.assertRaises(ValueError):
            normalise_action({"id": "CC-004", "severity": "critical"})

    def test_action_without_an_id_rejected(self):
        with self.assertRaises(ValueError):
            normalise_action({"severity": SEVERITY_MINOR})

    def test_non_boolean_closed_flag_rejected(self):
        with self.assertRaises(ValueError):
            normalise_action({"id": "CC-005", "severity": SEVERITY_MINOR, "closed": "no"})

    def test_actions_must_be_a_list(self):
        with self.assertRaises(ValueError):
            action_load({"id": "CC-006", "severity": SEVERITY_MINOR})


class ReviewVerdictTests(unittest.TestCase):
    def test_a_complete_pack_with_no_open_action_is_ready(self):
        result = assess_cleanliness_review(CASE)
        self.assertEqual(result["verdict"], VERDICT_READY)
        self.assertTrue(result["ready"])

    def test_a_missing_supporting_item_makes_it_conditional(self):
        pack = [
            n for n in FULL_CDR_PACK if n != "materials-outgassing-screening-record"
        ]
        result = assess_cleanliness_review(_case(submitted=pack))
        self.assertEqual(result["verdict"], VERDICT_CONDITIONAL)
        self.assertTrue(result["gate_may_open"])

    def test_a_missing_mandatory_item_stops_the_gate(self):
        pack = [n for n in FULL_CDR_PACK if n != "contamination-transport-model"]
        result = assess_cleanliness_review(_case(submitted=pack))
        self.assertEqual(result["verdict"], VERDICT_NOT_READY)
        self.assertFalse(result["gate_may_open"])

    def test_an_open_major_action_stops_the_gate_on_a_full_pack(self):
        result = assess_cleanliness_review(
            _case(actions=[{"id": "CC-020", "severity": SEVERITY_MAJOR}])
        )
        self.assertEqual(result["verdict"], VERDICT_NOT_READY)
        self.assertTrue(any("major" in b for b in result["blocking"]))

    def test_open_minors_make_it_conditional_not_ready(self):
        result = assess_cleanliness_review(
            _case(actions=[{"id": "CC-021", "severity": SEVERITY_MINOR}])
        )
        self.assertEqual(result["verdict"], VERDICT_CONDITIONAL)

    def test_a_thick_pack_does_not_buy_off_a_mandatory_gap(self):
        pack = [n for n in FULL_CDR_PACK if n != "contamination-requirements"]
        pack += ["annex-a", "annex-b", "annex-c", "annex-d"]
        result = assess_cleanliness_review(_case(submitted=pack))
        self.assertEqual(result["verdict"], VERDICT_NOT_READY)

    def test_critical_hardware_can_fail_a_pack_that_passes_as_standard(self):
        standard = assess_cleanliness_review(CASE)
        critical = assess_cleanliness_review(_case(sensitivity=SENSITIVITY_CRITICAL))
        self.assertEqual(standard["verdict"], VERDICT_READY)
        self.assertEqual(critical["verdict"], VERDICT_NOT_READY)

    def test_blocking_and_conditions_are_reported_together(self):
        pack = ["contamination-requirements"]
        result = assess_cleanliness_review(
            _case(submitted=pack, actions=[{"id": "CC-030", "severity": SEVERITY_MINOR}])
        )
        self.assertGreaterEqual(len(result["blocking"]), 3)
        self.assertGreaterEqual(len(result["conditions"]), 1)

    def test_a_manufacturing_review_needs_the_training_record(self):
        pack = sorted(required_items(MRR, SENSITIVITY_STANDARD))
        pack = [n for n in pack if n != "personnel-training-record"]
        result = assess_cleanliness_review(_case(review=MRR, submitted=pack))
        self.assertIn("personnel-training-record", result["pack"]["missing_mandatory"])

    def test_non_mapping_case_rejected(self):
        with self.assertRaises(ValueError):
            assess_cleanliness_review("critical-design-review")

    def test_missing_review_type_rejected(self):
        case = _case()
        del case["review"]
        with self.assertRaises(ValueError):
            assess_cleanliness_review(case)

    def test_missing_item_name_rejected(self):
        case = _case()
        del case["item"]
        with self.assertRaises(ValueError):
            assess_cleanliness_review(case)


if __name__ == "__main__":
    unittest.main()
