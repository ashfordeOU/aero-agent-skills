#!/usr/bin/env python3
"""Contract test for the device final review gate (offline)."""

import copy
import unittest

from e2040_validation_qualification_acceptance_review_logic import (
    CRITICALITY_CATEGORIES,
    DEFAULT_ENVELOPE_RATIO,
    GATE_HELD,
    GATE_OPEN,
    GATE_OPEN_WITH_ACTIONS,
    STREAMS,
    envelope_compliant,
    envelope_ratio,
    model_admissibility_findings,
    normalise_items,
    open_action_budget,
    plan_final_review,
    stream_closure,
    validate_evidence_item,
)

CLEAN_ITEMS = [
    {"id": "V-01", "stream": "validation", "state": "closed",
     "model_kind": "engineering-model"},
    {"id": "V-02", "stream": "validation", "state": "closed",
     "model_kind": "flight-model"},
    {"id": "Q-01", "stream": "qualification", "state": "closed",
     "model_kind": "qualification-model"},
    {"id": "Q-02", "stream": "qualification", "state": "closed",
     "model_kind": "protoflight-model"},
    {"id": "A-01", "stream": "acceptance", "state": "closed",
     "model_kind": "flight-model"},
]

CLEAN_CASE = {
    "device_id": "DEV-4471",
    "criticality": "category-1",
    "items": CLEAN_ITEMS,
    "qualification_level": 14.1,
    "acceptance_level": 11.28,
}


def _case(**overrides):
    case = copy.deepcopy(CLEAN_CASE)
    case.update(overrides)
    return case


def _items(**changes):
    items = copy.deepcopy(CLEAN_ITEMS)
    for item in items:
        if item["id"] in changes:
            item.update(changes[item["id"]])
    return items


class EvidenceItemTests(unittest.TestCase):
    def test_a_clean_item_normalises(self):
        entry = validate_evidence_item(CLEAN_ITEMS[0])
        self.assertEqual(entry["id"], "V-01")
        self.assertEqual(entry["stream"], "validation")
        self.assertIsNone(entry["deviation_reference"])

    def test_a_waived_item_keeps_its_deviation_reference(self):
        entry = validate_evidence_item(
            {"id": "A-09", "stream": "acceptance", "state": "waived",
             "model_kind": "flight-model", "deviation_reference": " DEV-77 "}
        )
        self.assertEqual(entry["deviation_reference"], "DEV-77")

    def test_a_waiver_without_a_deviation_is_rejected(self):
        with self.assertRaises(ValueError):
            validate_evidence_item(
                {"id": "A-09", "stream": "acceptance", "state": "waived",
                 "model_kind": "flight-model"}
            )

    def test_an_unknown_stream_is_rejected(self):
        with self.assertRaises(ValueError):
            validate_evidence_item(
                {"id": "X-1", "stream": "assurance", "state": "closed",
                 "model_kind": "flight-model"}
            )

    def test_an_unknown_state_is_rejected(self):
        with self.assertRaises(ValueError):
            validate_evidence_item(
                {"id": "X-1", "stream": "acceptance", "state": "nearly",
                 "model_kind": "flight-model"}
            )

    def test_an_item_without_an_id_is_rejected(self):
        with self.assertRaises(ValueError):
            validate_evidence_item(
                {"id": "  ", "stream": "acceptance", "state": "closed",
                 "model_kind": "flight-model"}
            )

    def test_a_non_mapping_item_is_rejected(self):
        with self.assertRaises(ValueError):
            validate_evidence_item("A-01 closed")

    def test_a_duplicate_item_id_is_rejected(self):
        with self.assertRaises(ValueError):
            normalise_items(CLEAN_ITEMS + [copy.deepcopy(CLEAN_ITEMS[0])])

    def test_an_empty_item_list_is_rejected(self):
        with self.assertRaises(ValueError):
            normalise_items([])


class StreamClosureTests(unittest.TestCase):
    def test_a_fully_closed_stream_reports_unit_fraction(self):
        result = stream_closure(CLEAN_ITEMS, "qualification")
        self.assertEqual(result["required"], 2)
        self.assertEqual(result["closed"], 2)
        self.assertAlmostEqual(result["closed_fraction"], 1.0, places=12)

    def test_an_open_item_lowers_the_closed_fraction(self):
        items = _items(**{"V-02": {"state": "open"}})
        result = stream_closure(items, "validation")
        self.assertEqual(result["open"], 1)
        self.assertAlmostEqual(result["closed_fraction"], 0.5, places=12)

    def test_every_stream_is_scored_separately(self):
        fractions = {s: stream_closure(CLEAN_ITEMS, s)["closed_fraction"]
                     for s in STREAMS}
        self.assertEqual(sorted(fractions), sorted(STREAMS))

    def test_a_stream_with_no_evidence_is_rejected(self):
        items = [i for i in copy.deepcopy(CLEAN_ITEMS)
                 if i["stream"] != "acceptance"]
        with self.assertRaises(ValueError):
            stream_closure(items, "acceptance")

    def test_an_unknown_stream_is_rejected(self):
        with self.assertRaises(ValueError):
            stream_closure(CLEAN_ITEMS, "integration")


class ModelAdmissibilityTests(unittest.TestCase):
    def test_a_clean_package_raises_no_model_finding(self):
        self.assertEqual(model_admissibility_findings(CLEAN_ITEMS), [])

    def test_qualification_on_an_engineering_model_is_a_finding(self):
        items = _items(**{"Q-01": {"model_kind": "engineering-model"}})
        findings = model_admissibility_findings(items)
        self.assertEqual(len(findings), 1)
        self.assertIn("Q-01", findings[0])

    def test_acceptance_on_the_qualification_article_is_a_finding(self):
        items = _items(**{"A-01": {"model_kind": "qualification-model"}})
        self.assertTrue(
            any("A-01" in f for f in model_admissibility_findings(items))
        )

    def test_validation_admits_every_model_kind(self):
        items = _items(**{"V-01": {"model_kind": "protoflight-model"}})
        self.assertEqual(model_admissibility_findings(items), [])


class EnvelopeTests(unittest.TestCase):
    def test_ratio_is_the_quotient_of_the_two_levels(self):
        self.assertAlmostEqual(envelope_ratio(14.1, 11.28), 1.25, places=9)

    def test_a_ratio_exactly_on_the_requirement_is_compliant(self):
        self.assertTrue(envelope_compliant(14.1, 11.28, 1.25))

    def test_a_ratio_below_the_requirement_is_not_compliant(self):
        self.assertFalse(envelope_compliant(12.0, 11.28, 1.25))

    def test_a_generous_ratio_is_compliant(self):
        self.assertTrue(envelope_compliant(20.0, 10.0, DEFAULT_ENVELOPE_RATIO))

    def test_a_zero_acceptance_level_is_rejected(self):
        with self.assertRaises(ValueError):
            envelope_ratio(14.1, 0.0)

    def test_a_non_numeric_level_is_rejected(self):
        with self.assertRaises(ValueError):
            envelope_ratio("14.1 g", 11.28)


class BudgetTests(unittest.TestCase):
    def test_the_top_category_tolerates_no_open_action(self):
        self.assertEqual(open_action_budget("category-1"), 0)

    def test_the_budget_never_shrinks_as_criticality_falls(self):
        budgets = [open_action_budget(c) for c in CRITICALITY_CATEGORIES]
        self.assertEqual(budgets, sorted(budgets))

    def test_an_unknown_category_is_rejected(self):
        with self.assertRaises(ValueError):
            open_action_budget("category-0")


class PlanTests(unittest.TestCase):
    def test_a_clean_package_opens_the_gate(self):
        result = plan_final_review(CLEAN_CASE)
        self.assertEqual(result["verdict"], GATE_OPEN)
        self.assertIsNone(result["binding_finding"])
        self.assertTrue(result["envelope_compliant"])
        self.assertAlmostEqual(result["envelope_ratio"], 1.25, places=9)

    def test_not_started_evidence_holds_the_gate(self):
        result = plan_final_review(_case(items=_items(**{"A-01": {"state": "not-started"}})))
        self.assertEqual(result["verdict"], GATE_HELD)
        self.assertEqual(result["binding_finding"], "not-started-evidence")

    def test_the_wrong_model_kind_holds_the_gate(self):
        result = plan_final_review(
            _case(items=_items(**{"Q-01": {"model_kind": "engineering-model"}}))
        )
        self.assertEqual(result["verdict"], GATE_HELD)
        self.assertEqual(result["binding_finding"], "model-kind-not-admitted")

    def test_a_short_envelope_holds_the_gate(self):
        result = plan_final_review(_case(qualification_level=12.0))
        self.assertEqual(result["verdict"], GATE_HELD)
        self.assertEqual(result["binding_finding"], "envelope-ratio-not-met")

    def test_a_missing_envelope_pair_holds_the_gate(self):
        case = _case()
        del case["qualification_level"]
        result = plan_final_review(case)
        self.assertEqual(result["binding_finding"], "envelope-not-demonstrated")
        self.assertIsNone(result["envelope_compliant"])

    def test_an_open_action_over_budget_holds_the_gate(self):
        result = plan_final_review(_case(items=_items(**{"V-02": {"state": "open"}})))
        self.assertEqual(result["verdict"], GATE_HELD)
        self.assertEqual(result["binding_finding"], "open-actions-over-budget")

    def test_an_open_action_within_budget_opens_against_actions(self):
        result = plan_final_review(
            _case(criticality="category-3", items=_items(**{"V-02": {"state": "open"}}))
        )
        self.assertEqual(result["verdict"], GATE_OPEN_WITH_ACTIONS)
        self.assertEqual(result["binding_finding"], "open-actions-within-budget")
        self.assertEqual(result["open_total"], 1)

    def test_a_waiver_alone_opens_against_actions(self):
        items = _items(**{"V-02": {"state": "waived", "deviation_reference": "DEV-12"}})
        result = plan_final_review(_case(items=items))
        self.assertEqual(result["verdict"], GATE_OPEN_WITH_ACTIONS)
        self.assertEqual(result["binding_finding"], "waiver-outstanding")
        self.assertEqual(result["waived_total"], 1)

    def test_a_missing_stream_is_rejected(self):
        items = [i for i in copy.deepcopy(CLEAN_ITEMS) if i["stream"] != "acceptance"]
        with self.assertRaises(ValueError):
            plan_final_review(_case(items=items))

    def test_a_non_mapping_case_is_rejected(self):
        with self.assertRaises(ValueError):
            plan_final_review("category-1")

    def test_an_unknown_criticality_is_rejected(self):
        with self.assertRaises(ValueError):
            plan_final_review(_case(criticality="cat-1"))

    def test_the_verdict_always_carries_its_closures(self):
        result = plan_final_review(CLEAN_CASE)
        self.assertEqual(sorted(result["closures"]), sorted(STREAMS))


if __name__ == "__main__":
    unittest.main()
