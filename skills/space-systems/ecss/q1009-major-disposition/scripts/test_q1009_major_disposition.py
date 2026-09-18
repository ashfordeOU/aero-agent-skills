#!/usr/bin/env python3
"""Contract test for the major-nonconformance board disposition (offline)."""

import copy
import unittest

from q1009_major_disposition_logic import (
    CONCESSION_DISPOSITIONS,
    DISPOSITIONS,
    QUORUM_ROLES,
    VERDICT_CONDITIONAL,
    VERDICT_DEFERRED,
    VERDICT_GRANTED,
    VERDICT_INCOMPLETE,
    VERDICT_REFUSED,
    admissible_dispositions,
    board_quorum,
    concession_record,
    dispose_major_nonconformance,
    evaluate_conditions,
    requires_concession,
)

FULL_BOARD = [
    "customer-representative",
    "product-assurance",
    "engineering",
    "project-management",
]

CASE = {
    "ncr_id": "NCR-0412",
    "requirement_id": "REQ-STR-0180",
    "severity": "major",
    "quantity_affected": 3,
    "requested_disposition": "use-as-is",
    "justification": "measured gap is 0.2 mm under drawing, stress case reruns positive",
    "board_members": FULL_BOARD,
    "safety_impact": False,
    "interface_impact": False,
    "lifetime_impact": False,
    "rework_feasible": True,
    "repair_procedure_approved": False,
    "supplier_furnished": False,
    "conditions": [],
}

OPEN_CONDITION = {
    "id": "C1",
    "text": "rerun the load case with the as-built gap",
    "owner": "structures lead",
    "verification": "analysis report issue B",
    "closed": False,
}


def _case(**overrides):
    case = copy.deepcopy(CASE)
    case.update(overrides)
    return case


class QuorumTests(unittest.TestCase):
    def test_full_board_is_quorate(self):
        self.assertTrue(board_quorum(FULL_BOARD)["quorate"])

    def test_board_without_the_customer_is_not_quorate(self):
        result = board_quorum(["product-assurance", "engineering"])
        self.assertFalse(result["quorate"])
        self.assertIn("customer-representative", result["missing_roles"])

    def test_every_quorum_role_is_a_known_board_role(self):
        for role in QUORUM_ROLES:
            self.assertTrue(board_quorum(list(QUORUM_ROLES) + [role])["quorate"])

    def test_repeated_role_is_counted_once(self):
        result = board_quorum(FULL_BOARD + ["engineering"])
        self.assertEqual(len(result["roles_present"]), len(FULL_BOARD))

    def test_unknown_role_rejected(self):
        with self.assertRaises(ValueError):
            board_quorum(["customer-representative", "catering"])

    def test_empty_board_rejected(self):
        with self.assertRaises(ValueError):
            board_quorum([])

    def test_non_list_board_rejected(self):
        with self.assertRaises(ValueError):
            board_quorum("customer-representative")


class AdmissibilityTests(unittest.TestCase):
    def test_clean_item_admits_use_as_is(self):
        self.assertIn("use-as-is", admissible_dispositions(CASE)["admissible"])

    def test_safety_impact_closes_use_as_is_and_repair(self):
        options = admissible_dispositions(
            _case(safety_impact=True, repair_procedure_approved=True)
        )
        self.assertNotIn("use-as-is", options["admissible"])
        self.assertNotIn("repair", options["admissible"])
        self.assertIn("safety", options["blocked"]["use-as-is"])

    def test_interface_impact_closes_a_departure(self):
        options = admissible_dispositions(_case(interface_impact=True))
        self.assertNotIn("use-as-is", options["admissible"])

    def test_lifetime_impact_closes_a_departure(self):
        options = admissible_dispositions(_case(lifetime_impact=True))
        self.assertNotIn("use-as-is", options["admissible"])

    def test_scrap_is_always_admissible(self):
        options = admissible_dispositions(
            _case(
                safety_impact=True,
                interface_impact=True,
                lifetime_impact=True,
                rework_feasible=False,
            )
        )
        self.assertIn("scrap", options["admissible"])

    def test_repair_needs_an_approved_procedure(self):
        self.assertNotIn("repair", admissible_dispositions(CASE)["admissible"])
        self.assertIn(
            "repair",
            admissible_dispositions(_case(repair_procedure_approved=True))["admissible"],
        )

    def test_return_to_supplier_needs_a_furnishing_supplier(self):
        self.assertNotIn(
            "return-to-supplier", admissible_dispositions(CASE)["admissible"]
        )
        self.assertIn(
            "return-to-supplier",
            admissible_dispositions(_case(supplier_furnished=True))["admissible"],
        )

    def test_missing_impact_flag_rejected(self):
        case = _case()
        del case["safety_impact"]
        with self.assertRaises(ValueError):
            admissible_dispositions(case)

    def test_non_boolean_impact_flag_rejected(self):
        with self.assertRaises(ValueError):
            admissible_dispositions(_case(safety_impact="no"))


class ConcessionTests(unittest.TestCase):
    def test_use_as_is_and_repair_earn_a_concession(self):
        for disposition in CONCESSION_DISPOSITIONS:
            self.assertTrue(requires_concession(disposition))

    def test_rework_and_scrap_leave_no_departure(self):
        for disposition in ("rework", "scrap", "return-to-supplier"):
            self.assertFalse(requires_concession(disposition))

    def test_every_disposition_has_a_concession_answer(self):
        self.assertEqual(
            len([d for d in DISPOSITIONS if requires_concession(d)]),
            len(CONCESSION_DISPOSITIONS),
        )

    def test_concession_record_carries_quantity_and_requirement(self):
        record = concession_record(CASE, "use-as-is")
        self.assertEqual(record["quantity_affected"], 3)
        self.assertEqual(record["requirement_id"], "REQ-STR-0180")

    def test_no_record_for_a_conforming_outcome(self):
        self.assertIsNone(concession_record(CASE, "rework"))

    def test_concession_record_needs_a_justification(self):
        case = _case()
        del case["justification"]
        with self.assertRaises(ValueError):
            concession_record(case, "use-as-is")

    def test_unknown_disposition_rejected(self):
        with self.assertRaises(ValueError):
            requires_concession("melt-down")


class ConditionTests(unittest.TestCase):
    def test_no_conditions_is_all_closed(self):
        self.assertTrue(evaluate_conditions([])["all_closed"])

    def test_open_condition_is_reported(self):
        result = evaluate_conditions([OPEN_CONDITION])
        self.assertEqual(result["open_ids"], ("C1",))
        self.assertFalse(result["all_closed"])

    def test_closed_condition_clears(self):
        closed = dict(OPEN_CONDITION, closed=True)
        self.assertTrue(evaluate_conditions([closed])["all_closed"])

    def test_condition_without_an_owner_is_a_finding(self):
        result = evaluate_conditions([dict(OPEN_CONDITION, owner="")])
        self.assertTrue(any("owner" in f for f in result["findings"]))

    def test_condition_without_a_verification_is_a_finding(self):
        result = evaluate_conditions([dict(OPEN_CONDITION, verification=" ")])
        self.assertTrue(any("verifying" in f for f in result["findings"]))

    def test_duplicate_condition_id_rejected(self):
        with self.assertRaises(ValueError):
            evaluate_conditions([OPEN_CONDITION, dict(OPEN_CONDITION)])

    def test_condition_without_text_rejected(self):
        with self.assertRaises(ValueError):
            evaluate_conditions([dict(OPEN_CONDITION, text="")])


class DispositionTests(unittest.TestCase):
    def test_clean_case_is_granted_and_releasable(self):
        result = dispose_major_nonconformance(CASE)
        self.assertEqual(result["verdict"], VERDICT_GRANTED)
        self.assertEqual(result["granted_disposition"], "use-as-is")
        self.assertTrue(result["release_permitted"])
        self.assertIsNotNone(result["concession"])

    def test_open_condition_holds_the_release(self):
        result = dispose_major_nonconformance(_case(conditions=[OPEN_CONDITION]))
        self.assertEqual(result["verdict"], VERDICT_CONDITIONAL)
        self.assertFalse(result["release_permitted"])

    def test_inadmissible_request_is_refused_with_alternatives(self):
        result = dispose_major_nonconformance(_case(safety_impact=True))
        self.assertEqual(result["verdict"], VERDICT_REFUSED)
        self.assertIn("rework", result["admissible"])
        self.assertFalse(result["release_permitted"])

    def test_missing_quorum_defers_the_decision(self):
        result = dispose_major_nonconformance(
            _case(board_members=["product-assurance", "engineering"])
        )
        self.assertEqual(result["verdict"], VERDICT_DEFERRED)
        self.assertIsNone(result["granted_disposition"])

    def test_departure_without_justification_is_returned(self):
        case = _case()
        del case["justification"]
        result = dispose_major_nonconformance(case)
        self.assertEqual(result["verdict"], VERDICT_INCOMPLETE)
        self.assertFalse(result["release_permitted"])

    def test_rework_needs_no_justification(self):
        case = _case(requested_disposition="rework")
        del case["justification"]
        result = dispose_major_nonconformance(case)
        self.assertEqual(result["verdict"], VERDICT_GRANTED)
        self.assertIsNone(result["concession"])

    def test_minor_severity_is_the_wrong_board(self):
        with self.assertRaises(ValueError):
            dispose_major_nonconformance(_case(severity="minor"))

    def test_unknown_severity_rejected(self):
        with self.assertRaises(ValueError):
            dispose_major_nonconformance(_case(severity="cosmetic"))

    def test_zero_quantity_rejected(self):
        with self.assertRaises(ValueError):
            dispose_major_nonconformance(_case(quantity_affected=0))

    def test_boolean_quantity_rejected(self):
        with self.assertRaises(ValueError):
            dispose_major_nonconformance(_case(quantity_affected=True))

    def test_non_mapping_case_rejected(self):
        with self.assertRaises(ValueError):
            dispose_major_nonconformance("NCR-0412")

    def test_unknown_requested_disposition_rejected(self):
        with self.assertRaises(ValueError):
            dispose_major_nonconformance(_case(requested_disposition="ignore"))


if __name__ == "__main__":
    unittest.main()
