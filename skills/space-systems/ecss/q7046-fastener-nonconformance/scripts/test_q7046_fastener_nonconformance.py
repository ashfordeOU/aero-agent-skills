#!/usr/bin/env python3
"""Contract test for fastener lot nonconformance handling (offline)."""

import copy
import unittest

from q7046_fastener_nonconformance_logic import (
    CRITICALITIES,
    DEFECT_CLASSES,
    DISPOSITION_REWORK,
    DISPOSITION_SCRAP,
    DISPOSITION_USE_AS_IS,
    IRRECOVERABLE_DEFECTS,
    MAX_REPLATING_CYCLES,
    SCOPE_LOT,
    SCOPE_SHARED_PROCESS,
    SCOPE_SUPPLIER_STOCK,
    approvals_required,
    disposition_case,
    permitted_dispositions,
    quarantine_scope,
    replating_available,
    scrap_actions,
)

GOOD_CASE = {
    "lot_id": "LOT-4471",
    "defect_class": "dimensional",
    "criticality": "minor",
    "defect_origin": "single-lot-operation",
    "traceability_intact": True,
    "replating_cycles_used": 0,
    "quantity_installed": 0,
    "proposed_disposition": "use-as-is",
}


def _case(**overrides):
    case = copy.deepcopy(GOOD_CASE)
    case.update(overrides)
    return case


class QuarantineScopeTests(unittest.TestCase):
    def test_a_single_lot_operation_is_contained_by_its_lot(self):
        self.assertEqual(
            quarantine_scope("single-lot-operation", True)["scope"], SCOPE_LOT
        )

    def test_a_heat_defect_reaches_every_lot_sharing_the_record(self):
        for origin in ("heat", "heat-treatment-charge", "plating-batch"):
            self.assertEqual(
                quarantine_scope(origin, True)["scope"], SCOPE_SHARED_PROCESS
            )

    def test_broken_traceability_widens_the_hold_to_all_supplier_stock(self):
        result = quarantine_scope("single-lot-operation", False)
        self.assertEqual(result["scope"], SCOPE_SUPPLIER_STOCK)
        self.assertIn("cannot resolve", result["reason"])

    def test_an_unestablished_origin_cannot_be_narrowed(self):
        self.assertEqual(
            quarantine_scope("unknown", True)["scope"], SCOPE_SUPPLIER_STOCK
        )

    def test_unknown_origin_name_rejected(self):
        with self.assertRaises(ValueError):
            quarantine_scope("probably-the-forge", True)

    def test_non_boolean_traceability_flag_rejected(self):
        with self.assertRaises(ValueError):
            quarantine_scope("heat", "yes")


class PermittedDispositionTests(unittest.TestCase):
    def test_a_metal_property_defect_can_never_be_reworked(self):
        for defect in IRRECOVERABLE_DEFECTS:
            for criticality in CRITICALITIES:
                options = permitted_dispositions(defect, criticality)
                self.assertNotIn(DISPOSITION_REWORK, options)
                self.assertNotIn(DISPOSITION_USE_AS_IS, options)
                self.assertIn(DISPOSITION_SCRAP, options)

    def test_a_coating_defect_may_be_reworked_while_cycles_remain(self):
        options = permitted_dispositions("coating", "major", 0)
        self.assertIn(DISPOSITION_REWORK, options)

    def test_a_coating_defect_loses_rework_once_the_cycles_are_spent(self):
        options = permitted_dispositions("coating", "major", MAX_REPLATING_CYCLES)
        self.assertNotIn(DISPOSITION_REWORK, options)

    def test_a_critical_dimensional_defect_is_scrap_or_return_only(self):
        options = permitted_dispositions("dimensional", "critical")
        self.assertEqual(sorted(options), ["return-to-supplier", "scrap"])

    def test_a_minor_dimensional_defect_may_be_used_as_is(self):
        self.assertIn(DISPOSITION_USE_AS_IS,
                      permitted_dispositions("dimensional", "minor"))

    def test_a_marking_defect_may_be_reworked(self):
        self.assertIn(DISPOSITION_REWORK,
                      permitted_dispositions("marking", "critical"))

    def test_every_defect_class_leaves_at_least_one_route(self):
        for defect in DEFECT_CLASSES:
            for criticality in CRITICALITIES:
                self.assertTrue(permitted_dispositions(defect, criticality))

    def test_unknown_defect_class_rejected(self):
        with self.assertRaises(ValueError):
            permitted_dispositions("looks-odd", "minor")

    def test_negative_replating_cycles_rejected(self):
        with self.assertRaises(ValueError):
            permitted_dispositions("coating", "minor", -1)


class ReplatingTests(unittest.TestCase):
    def test_a_fresh_part_has_cycles_available(self):
        self.assertTrue(replating_available(0))

    def test_a_part_at_the_cycle_limit_has_none_left(self):
        self.assertFalse(replating_available(MAX_REPLATING_CYCLES))

    def test_a_part_past_the_cycle_limit_has_none_left(self):
        self.assertFalse(replating_available(MAX_REPLATING_CYCLES + 3))


class ApprovalTests(unittest.TestCase):
    def test_every_disposition_needs_the_review_board(self):
        for disposition in ("use-as-is", "rework", "repair",
                            "return-to-supplier", "scrap"):
            self.assertIn(
                "nonconformance-review-board",
                approvals_required(disposition, "major"),
            )

    def test_keeping_the_part_pulls_in_the_customer(self):
        self.assertIn("customer", approvals_required("use-as-is", "major"))
        self.assertIn("customer", approvals_required("repair", "minor"))

    def test_returning_the_part_does_not_pull_in_the_customer(self):
        self.assertNotIn(
            "customer", approvals_required("return-to-supplier", "critical")
        )

    def test_scrapping_a_critical_part_is_witnessed(self):
        self.assertIn(
            "quality-assurance-witness-of-mutilation",
            approvals_required("scrap", "critical"),
        )

    def test_unknown_disposition_rejected(self):
        with self.assertRaises(ValueError):
            approvals_required("set-aside-for-now", "minor")


class ScrapActionTests(unittest.TestCase):
    def test_scrap_is_a_physical_act_not_a_record_state(self):
        actions = scrap_actions("minor")
        self.assertTrue(any("mutilate" in a for a in actions))

    def test_a_critical_scrap_adds_a_witness_step(self):
        self.assertGreater(len(scrap_actions("critical")), len(scrap_actions("minor")))


class DispositionCaseTests(unittest.TestCase):
    def test_a_permitted_disposition_is_accepted_with_its_approvals(self):
        result = disposition_case(GOOD_CASE)
        self.assertEqual(result["verdict"], "disposition-accepted")
        self.assertIn("customer", result["approvals_required"])

    def test_a_disposition_outside_the_options_is_refused(self):
        result = disposition_case(
            _case(defect_class="material-property", proposed_disposition="rework")
        )
        self.assertEqual(result["verdict"], "disposition-refused")
        self.assertFalse(result["approvals_required"])

    def test_no_proposal_leaves_the_case_awaiting_a_disposition(self):
        case = _case()
        del case["proposed_disposition"]
        result = disposition_case(case)
        self.assertEqual(result["verdict"], "awaiting-disposition")
        self.assertIsNone(result["proposed_disposition"])

    def test_installed_parts_raise_a_recall_finding(self):
        result = disposition_case(_case(quantity_installed=6))
        self.assertTrue(any("already installed" in f for f in result["findings"]))

    def test_scrap_carries_its_physical_actions_into_the_case(self):
        result = disposition_case(
            _case(defect_class="material-property", proposed_disposition="scrap")
        )
        self.assertIn("scrap_actions", result)

    def test_broken_traceability_widens_the_case_quarantine(self):
        result = disposition_case(_case(traceability_intact=False))
        self.assertEqual(result["quarantine_scope"], SCOPE_SUPPLIER_STOCK)

    def test_a_case_without_a_lot_id_is_rejected(self):
        with self.assertRaises(ValueError):
            disposition_case(_case(lot_id=""))

    def test_a_non_mapping_case_is_rejected(self):
        with self.assertRaises(ValueError):
            disposition_case("bolts look wrong")

    def test_a_case_with_an_unknown_criticality_is_rejected(self):
        with self.assertRaises(ValueError):
            disposition_case(_case(criticality="fairly-important"))


if __name__ == "__main__":
    unittest.main()
