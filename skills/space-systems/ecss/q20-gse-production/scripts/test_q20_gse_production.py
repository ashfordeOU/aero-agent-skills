"""Contract tests for the clause 5.8.3 GSE production assurance logic."""

import unittest

from q20_gse_production_logic import (
    INSPECTION_RESULTS,
    SUPPLIER_STATES,
    WITNESS_FUNCTIONS,
    assess_gse_production,
    completion_ratio,
    inspection_point_findings,
    normalize_token,
    operation_findings,
    procurement_findings,
    release_verdict,
    validate_inspection_point,
    validate_lot,
    validate_operation,
    validate_operation_set,
)

GOOD_LOT = {
    "id": "lot-1",
    "supplier_state": "approved",
    "inspection_result": "accepted",
    "conformity_certificate": True,
    "lot_traceable": True,
}

OPERATIONS = [
    {"id": "op-weld-frame", "sequence": 1, "completed": True, "process_qualification_days": 40,
     "operator_certification_days": 120},
    {"id": "op-assemble-rack", "sequence": 2, "completed": True, "process_qualification_days": 10,
     "operator_certification_days": 60},
    {"id": "op-integrate-harness", "sequence": 3, "completed": True, "process_qualification_days": 5,
     "operator_certification_days": 30},
]

POINTS = [
    {"id": "mip-1", "operation_id": "op-weld-frame", "required_witness": "quality-assurance",
     "witnessed_by": "quality-assurance", "completed": True},
    {"id": "mip-2", "operation_id": "op-integrate-harness", "required_witness": "customer",
     "witnessed_by": "customer", "completed": True},
]


def _spec(**overrides):
    spec = {
        "operations": [dict(o) for o in OPERATIONS],
        "inspection_points": [dict(p) for p in POINTS],
        "lots": [dict(GOOD_LOT)],
    }
    spec.update(overrides)
    return spec


class NormalizeTokenTests(unittest.TestCase):
    def test_identifier_case_folded(self):
        self.assertEqual(normalize_token("OP_Weld Frame"), "op-weld-frame")

    def test_blank_rejected(self):
        with self.assertRaises(ValueError):
            normalize_token(" ")

    def test_non_string_rejected(self):
        with self.assertRaises(ValueError):
            normalize_token(12)


class ValidateLotTests(unittest.TestCase):
    def test_lot_normalized(self):
        lot = validate_lot(GOOD_LOT)
        self.assertEqual(lot["supplier_state"], "approved")
        self.assertTrue(lot["lot_traceable"])

    def test_unknown_supplier_state_rejected(self):
        with self.assertRaises(ValueError):
            validate_lot(dict(GOOD_LOT, supplier_state="preferred"))

    def test_unknown_inspection_result_rejected(self):
        with self.assertRaises(ValueError):
            validate_lot(dict(GOOD_LOT, inspection_result="probably-fine"))

    def test_missing_key_rejected(self):
        with self.assertRaises(ValueError):
            validate_lot({"id": "lot-2", "supplier_state": "approved"})

    def test_vocabularies_are_distinct(self):
        self.assertEqual(set(SUPPLIER_STATES) & set(INSPECTION_RESULTS), set())


class ProcurementTests(unittest.TestCase):
    def test_clean_lot_yields_nothing(self):
        grouped = procurement_findings([GOOD_LOT])
        self.assertEqual(grouped["blocking"], [])
        self.assertEqual(grouped["actions"], [])

    def test_unapproved_supplier_blocks(self):
        grouped = procurement_findings([dict(GOOD_LOT, supplier_state="not-approved")])
        self.assertIn("not approved", grouped["blocking"][0])

    def test_conditional_supplier_without_surveillance_blocks(self):
        grouped = procurement_findings([dict(GOOD_LOT, supplier_state="conditionally-approved")])
        self.assertIn("no surveillance", grouped["blocking"][0])

    def test_conditional_supplier_with_surveillance_passes(self):
        grouped = procurement_findings(
            [dict(GOOD_LOT, supplier_state="conditionally-approved", surveillance_applied=True)]
        )
        self.assertEqual(grouped["blocking"], [])

    def test_rejected_incoming_inspection_blocks(self):
        grouped = procurement_findings([dict(GOOD_LOT, inspection_result="rejected")])
        self.assertTrue(any("rejected at incoming" in f for f in grouped["blocking"]))

    def test_pending_inspection_is_an_action(self):
        grouped = procurement_findings([dict(GOOD_LOT, inspection_result="pending")])
        self.assertEqual(grouped["blocking"], [])
        self.assertEqual(len(grouped["actions"]), 1)

    def test_missing_certificate_and_traceability_give_two_findings(self):
        grouped = procurement_findings(
            [dict(GOOD_LOT, conformity_certificate=False, lot_traceable=False)]
        )
        self.assertEqual(len(grouped["blocking"]), 2)

    def test_duplicate_lot_rejected(self):
        with self.assertRaises(ValueError):
            procurement_findings([dict(GOOD_LOT), dict(GOOD_LOT)])

    def test_no_lots_is_an_empty_result(self):
        self.assertEqual(procurement_findings(None), {"blocking": [], "actions": []})


class OperationTests(unittest.TestCase):
    def test_operation_defaults(self):
        operation = validate_operation({"id": "op-x", "sequence": 1})
        self.assertFalse(operation["completed"])
        self.assertEqual(operation["process_qualification_days"], 0)

    def test_zero_sequence_rejected(self):
        with self.assertRaises(ValueError):
            validate_operation({"id": "op-x", "sequence": 0})

    def test_duplicate_sequence_rejected(self):
        with self.assertRaises(ValueError):
            validate_operation_set(
                [{"id": "op-a", "sequence": 1}, {"id": "op-b", "sequence": 1}]
            )

    def test_duplicate_identifier_rejected(self):
        with self.assertRaises(ValueError):
            validate_operation_set(
                [{"id": "op-a", "sequence": 1}, {"id": "OP A", "sequence": 2}]
            )

    def test_set_is_returned_in_sequence_order(self):
        operations = validate_operation_set(
            [{"id": "op-b", "sequence": 2}, {"id": "op-a", "sequence": 1}]
        )
        self.assertEqual([o["id"] for o in operations], ["op-a", "op-b"])

    def test_empty_operation_set_rejected(self):
        with self.assertRaises(ValueError):
            validate_operation_set([])

    def test_in_order_build_is_clean(self):
        grouped = operation_findings(validate_operation_set(OPERATIONS))
        self.assertEqual(grouped["blocking"], [])

    def test_operation_run_past_an_incomplete_predecessor_blocks(self):
        operations = [dict(o) for o in OPERATIONS]
        operations[1]["completed"] = False
        grouped = operation_findings(validate_operation_set(operations))
        self.assertTrue(any("before the operation ahead" in f for f in grouped["blocking"]))

    def test_lapsed_process_qualification_blocks(self):
        operations = [dict(o) for o in OPERATIONS]
        operations[0]["process_qualification_days"] = -12
        grouped = operation_findings(validate_operation_set(operations))
        self.assertIn("lapsed by 12", grouped["blocking"][0])

    def test_lapsed_operator_certification_blocks(self):
        operations = [dict(o) for o in OPERATIONS]
        operations[2]["operator_certification_days"] = -1
        grouped = operation_findings(validate_operation_set(operations))
        self.assertTrue(any("operator whose certification" in f for f in grouped["blocking"]))

    def test_an_unstarted_operation_is_only_an_action(self):
        operations = [dict(o) for o in OPERATIONS]
        operations[2]["completed"] = False
        grouped = operation_findings(validate_operation_set(operations))
        self.assertEqual(grouped["blocking"], [])
        self.assertEqual(len(grouped["actions"]), 1)


class InspectionPointTests(unittest.TestCase):
    def test_point_normalized(self):
        point = validate_inspection_point(POINTS[0])
        self.assertEqual(point["required_witness"], "quality-assurance")

    def test_unknown_witness_function_rejected(self):
        with self.assertRaises(ValueError):
            validate_inspection_point(dict(POINTS[0], required_witness="the-boss"))

    def test_witness_vocabulary_covers_none(self):
        self.assertIn("none", WITNESS_FUNCTIONS)

    def test_witnessed_points_are_clean(self):
        operations = validate_operation_set(OPERATIONS)
        grouped = inspection_point_findings(POINTS, operations)
        self.assertEqual(grouped["blocking"], [])

    def test_point_on_an_unknown_operation_blocks(self):
        operations = validate_operation_set(OPERATIONS)
        points = [dict(POINTS[0], operation_id="op-paint")]
        grouped = inspection_point_findings(points, operations)
        self.assertIn("not an operation of this build", grouped["blocking"][0])

    def test_operation_completed_past_an_open_point_blocks(self):
        operations = validate_operation_set(OPERATIONS)
        points = [dict(POINTS[0], completed=False)]
        grouped = inspection_point_findings(points, operations)
        self.assertIn("completed past unfinished", grouped["blocking"][0])

    def test_open_point_on_an_unstarted_operation_is_an_action(self):
        operations = [dict(o) for o in OPERATIONS]
        operations[0]["completed"] = False
        validated = validate_operation_set(operations)
        points = [dict(POINTS[0], completed=False)]
        grouped = inspection_point_findings(points, validated)
        self.assertEqual(grouped["blocking"], [])
        self.assertEqual(len(grouped["actions"]), 1)

    def test_wrong_witness_function_blocks(self):
        operations = validate_operation_set(OPERATIONS)
        points = [dict(POINTS[1], witnessed_by="quality-assurance")]
        grouped = inspection_point_findings(points, operations)
        self.assertIn("needed a customer witness", grouped["blocking"][0])

    def test_unwitnessed_point_blocks(self):
        operations = validate_operation_set(OPERATIONS)
        points = [dict(POINTS[1], witnessed_by=None)]
        grouped = inspection_point_findings(points, operations)
        self.assertIn("records none", grouped["blocking"][0])

    def test_duplicate_point_rejected(self):
        operations = validate_operation_set(OPERATIONS)
        with self.assertRaises(ValueError):
            inspection_point_findings([dict(POINTS[0]), dict(POINTS[0])], operations)


class CompletionRatioTests(unittest.TestCase):
    def test_all_complete_is_unity(self):
        self.assertAlmostEqual(completion_ratio(POINTS), 1.0, places=9)

    def test_half_complete(self):
        points = [dict(POINTS[0]), dict(POINTS[1], completed=False)]
        self.assertAlmostEqual(completion_ratio(points), 0.5, places=9)

    def test_empty_point_set_rejected(self):
        with self.assertRaises(ValueError):
            completion_ratio([])

    def test_non_sequence_rejected(self):
        with self.assertRaises(ValueError):
            completion_ratio("mip-1")


class VerdictTests(unittest.TestCase):
    def test_clean_build_is_released(self):
        self.assertEqual(release_verdict([], []), "released")

    def test_actions_only_is_released_with_actions(self):
        self.assertEqual(release_verdict([], ["lot pending"]), "released-with-actions")

    def test_blocking_is_held(self):
        self.assertEqual(release_verdict(["lot rejected"], []), "held")

    def test_non_sequence_rejected(self):
        with self.assertRaises(ValueError):
            release_verdict([], "lot pending")


class AssessGseProductionTests(unittest.TestCase):
    def test_clean_build_is_released(self):
        result = assess_gse_production(_spec())
        self.assertEqual(result["verdict"], "released")
        self.assertTrue(result["releasable"])
        self.assertAlmostEqual(result["completion_ratio"], 1.0, places=9)

    def test_rejected_lot_holds_the_item(self):
        spec = _spec(lots=[dict(GOOD_LOT, inspection_result="rejected")])
        result = assess_gse_production(spec)
        self.assertEqual(result["verdict"], "held")

    def test_pending_lot_releases_with_actions(self):
        spec = _spec(lots=[dict(GOOD_LOT, inspection_result="pending")])
        result = assess_gse_production(spec)
        self.assertEqual(result["verdict"], "released-with-actions")
        self.assertTrue(result["releasable"])

    def test_lapsed_qualification_holds_the_item(self):
        spec = _spec()
        spec["operations"][1]["process_qualification_days"] = -3
        result = assess_gse_production(spec)
        self.assertEqual(result["verdict"], "held")

    def test_completion_shortfall_against_a_required_value_holds(self):
        spec = _spec(required_completion=1.0)
        spec["inspection_points"][1]["completed"] = False
        spec["operations"][2]["completed"] = False
        result = assess_gse_production(spec)
        self.assertAlmostEqual(result["completion_ratio"], 0.5, places=9)
        self.assertEqual(result["verdict"], "held")

    def test_required_completion_outside_unit_interval_rejected(self):
        with self.assertRaises(ValueError):
            assess_gse_production(_spec(required_completion=1.5))

    def test_missing_spec_key_rejected(self):
        spec = _spec()
        del spec["operations"]
        with self.assertRaises(ValueError):
            assess_gse_production(spec)

    def test_non_mapping_spec_rejected(self):
        with self.assertRaises(ValueError):
            assess_gse_production(["operations"])

    def test_findings_accumulate_across_procurement_and_build(self):
        spec = _spec(lots=[dict(GOOD_LOT, supplier_state="not-approved", lot_traceable=False)])
        spec["operations"][0]["operator_certification_days"] = -5
        spec["inspection_points"][1]["witnessed_by"] = "none"
        result = assess_gse_production(spec)
        self.assertGreaterEqual(len(result["blocking"]), 4)


if __name__ == "__main__":
    unittest.main()
