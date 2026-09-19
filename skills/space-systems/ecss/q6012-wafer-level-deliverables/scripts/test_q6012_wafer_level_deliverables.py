"""Contract tests for the clause 10.2.6 wafer batch deliverable handover."""

import unittest

from q6012_wafer_level_deliverables_logic import (
    DELIVERABLE_KEYS,
    SUPPLY_STATUSES,
    USABLE_STATUS,
    assess_wafer_deliverables,
    completeness_fraction,
    deliverable_titles,
    delivery_findings,
    reconcile_delivery,
    required_deliverables,
    validate_case,
    validate_supplied,
)

REVISION = "C"


def case_spec(**overrides):
    spec = {
        "batch_id": "WB-4402",
        "batch_revision": REVISION,
        "delivered_as_die": True,
        "map_requested": False,
        "radiation_environment": False,
        "first_lot": False,
        "process_changed": False,
        "deviations_raised": False,
    }
    spec.update(overrides)
    return spec


def supply_for(case, status=USABLE_STATUS, revision=REVISION, drop=(), override=None):
    rows = []
    for entry in required_deliverables(validate_case(case)):
        if entry["item"] in drop:
            continue
        rows.append(
            {"item": entry["item"], "status": status, "revision": revision}
        )
    for item, fields in (override or {}).items():
        for row in rows:
            if row["item"] == item:
                row.update(fields)
    return rows


def handover_spec(**overrides):
    case = case_spec(**{k: v for k, v in overrides.items() if k != "supplied"})
    spec = dict(case)
    spec["supplied"] = overrides.get("supplied", supply_for(case))
    return spec


class RegistryTests(unittest.TestCase):
    def test_deliverable_keys_are_unique(self):
        self.assertEqual(len(DELIVERABLE_KEYS), len(set(DELIVERABLE_KEYS)))

    def test_every_key_has_a_title(self):
        self.assertEqual(set(deliverable_titles()), set(DELIVERABLE_KEYS))

    def test_issued_is_the_only_usable_status(self):
        self.assertIn(USABLE_STATUS, SUPPLY_STATUSES)
        self.assertEqual(USABLE_STATUS, "issued")

    def test_statuses_cover_the_ways_a_document_can_be_unusable(self):
        for token in ("draft", "unsigned", "superseded", "absent"):
            self.assertIn(token, SUPPLY_STATUSES)


class RequiredSetTests(unittest.TestCase):
    def test_baseline_batch_owes_the_always_items(self):
        keys = [e["item"] for e in required_deliverables(validate_case(case_spec()))]
        for key in (
            "certificate-of-conformity",
            "wafer-lot-identification",
            "acceptance-measurement-data",
            "process-monitor-limits",
            "visual-inspection-record",
        ):
            self.assertIn(key, keys)

    def test_die_handover_pulls_in_the_map_and_the_handling_instruction(self):
        keys = [e["item"] for e in required_deliverables(validate_case(case_spec()))]
        self.assertIn("wafer-map", keys)
        self.assertIn("storage-and-handling-instruction", keys)

    def test_wafer_level_handover_drops_the_die_form_items(self):
        case = validate_case(case_spec(delivered_as_die=False))
        keys = [e["item"] for e in required_deliverables(case)]
        self.assertNotIn("storage-and-handling-instruction", keys)
        self.assertNotIn("wafer-map", keys)

    def test_map_on_the_order_pulls_the_map_back_in(self):
        case = validate_case(case_spec(delivered_as_die=False, map_requested=True))
        keys = [e["item"] for e in required_deliverables(case)]
        self.assertIn("wafer-map", keys)

    def test_radiation_environment_pulls_in_the_evaluation_data(self):
        case = validate_case(case_spec(radiation_environment=True))
        keys = [e["item"] for e in required_deliverables(case)]
        self.assertIn("radiation-evaluation-data", keys)

    def test_first_lot_and_process_change_pull_in_their_reports(self):
        case = validate_case(case_spec(first_lot=True, process_changed=True))
        keys = [e["item"] for e in required_deliverables(case)]
        self.assertIn("first-lot-qualification-report", keys)
        self.assertIn("process-change-notice", keys)

    def test_deviations_pull_in_the_waiver_list(self):
        case = validate_case(case_spec(deviations_raised=True))
        keys = [e["item"] for e in required_deliverables(case)]
        self.assertIn("deviation-and-waiver-list", keys)

    def test_every_required_item_carries_a_reason(self):
        for entry in required_deliverables(validate_case(case_spec())):
            self.assertTrue(entry["reason"])

    def test_required_deliverables_rejects_a_raw_spec(self):
        with self.assertRaises(ValueError):
            required_deliverables({"batch_id": "X", "batch_revision": "A"})


class ValidateCaseTests(unittest.TestCase):
    def test_flags_default_when_absent(self):
        case = validate_case({"batch_id": "B", "batch_revision": "A"})
        self.assertTrue(case["delivered_as_die"])
        self.assertFalse(case["first_lot"])

    def test_non_mapping_spec_rejected(self):
        with self.assertRaises(ValueError):
            validate_case(["batch_id"])

    def test_missing_revision_rejected(self):
        with self.assertRaises(ValueError):
            validate_case({"batch_id": "B"})

    def test_empty_batch_id_rejected(self):
        with self.assertRaises(ValueError):
            validate_case(case_spec(batch_id="  "))

    def test_unknown_key_rejected_rather_than_ignored(self):
        with self.assertRaises(ValueError):
            validate_case(case_spec(radiaton_environment=True))

    def test_non_boolean_flag_rejected(self):
        with self.assertRaises(ValueError):
            validate_case(case_spec(first_lot="yes"))


class ValidateSuppliedTests(unittest.TestCase):
    def test_supplied_items_are_returned_in_registry_order(self):
        rows = list(reversed(supply_for(case_spec())))
        items = [r["item"] for r in validate_supplied(rows)]
        self.assertEqual(items, [k for k in DELIVERABLE_KEYS if k in set(items)])

    def test_unknown_deliverable_rejected(self):
        with self.assertRaises(ValueError):
            validate_supplied([{"item": "lunch-menu", "status": "issued"}])

    def test_unknown_status_rejected(self):
        with self.assertRaises(ValueError):
            validate_supplied([{"item": "wafer-map", "status": "printed"}])

    def test_duplicate_deliverable_rejected(self):
        rows = [
            {"item": "wafer-map", "status": "issued", "revision": REVISION},
            {"item": "wafer-map", "status": "draft", "revision": REVISION},
        ]
        with self.assertRaises(ValueError):
            validate_supplied(rows)

    def test_unknown_field_rejected(self):
        with self.assertRaises(ValueError):
            validate_supplied([{"item": "wafer-map", "status": "issued",
                                "pages": 3}])

    def test_non_sequence_rejected(self):
        with self.assertRaises(ValueError):
            validate_supplied({"item": "wafer-map"})


class ReconcileTests(unittest.TestCase):
    def test_complete_handover_satisfies_everything(self):
        case = validate_case(case_spec())
        result = reconcile_delivery(case, validate_supplied(supply_for(case_spec())))
        self.assertEqual(result["missing"], [])
        self.assertEqual(result["unusable"], [])
        self.assertAlmostEqual(completeness_fraction(result), 1.0, places=9)

    def test_missing_item_is_named(self):
        case = validate_case(case_spec())
        rows = supply_for(case_spec(), drop=("wafer-map",))
        result = reconcile_delivery(case, validate_supplied(rows))
        self.assertEqual([m["item"] for m in result["missing"]], ["wafer-map"])
        self.assertLess(completeness_fraction(result), 1.0)

    def test_draft_document_is_unusable_not_satisfied(self):
        case = validate_case(case_spec())
        rows = supply_for(case_spec(),
                          override={"certificate-of-conformity": {"status": "draft"}})
        result = reconcile_delivery(case, validate_supplied(rows))
        self.assertEqual(
            [u["item"] for u in result["unusable"]], ["certificate-of-conformity"]
        )
        self.assertTrue(any("draft" in u["reason"] for u in result["unusable"]))

    def test_right_document_at_the_wrong_revision_is_unusable(self):
        case = validate_case(case_spec())
        rows = supply_for(case_spec(),
                          override={"wafer-map": {"revision": "B"}})
        result = reconcile_delivery(case, validate_supplied(rows))
        self.assertEqual([u["item"] for u in result["unusable"]], ["wafer-map"])
        self.assertTrue(any("revision" in u["reason"] for u in result["unusable"]))

    def test_unsigned_document_is_unusable(self):
        case = validate_case(case_spec())
        rows = supply_for(case_spec(),
                          override={"visual-inspection-record": {"status": "unsigned"}})
        result = reconcile_delivery(case, validate_supplied(rows))
        self.assertTrue(any("unsigned" in u["reason"] for u in result["unusable"]))

    def test_surplus_item_is_reported_without_being_counted(self):
        case = validate_case(case_spec())
        rows = supply_for(case_spec()) + [
            {"item": "radiation-evaluation-data", "status": "issued",
             "revision": REVISION}
        ]
        result = reconcile_delivery(case, validate_supplied(rows))
        self.assertEqual(
            [s["item"] for s in result["surplus"]], ["radiation-evaluation-data"]
        )
        self.assertAlmostEqual(completeness_fraction(result), 1.0, places=9)

    def test_reconcile_rejects_a_raw_case(self):
        with self.assertRaises(ValueError):
            reconcile_delivery({"batch_id": "B"}, [])

    def test_completeness_rejects_a_foreign_mapping(self):
        with self.assertRaises(ValueError):
            completeness_fraction({"satisfied": []})

    def test_findings_reject_a_foreign_mapping(self):
        with self.assertRaises(ValueError):
            delivery_findings({"satisfied": []})


class AssessmentTests(unittest.TestCase):
    def test_complete_handover_accepts_the_batch(self):
        result = assess_wafer_deliverables(handover_spec())
        self.assertTrue(result["accepted"])
        self.assertEqual(result["disposition"], "accept-batch")
        self.assertEqual(result["findings"], [])

    def test_missing_item_withholds_the_batch(self):
        spec = handover_spec(supplied=supply_for(case_spec(), drop=("wafer-map",)))
        result = assess_wafer_deliverables(spec)
        self.assertFalse(result["accepted"])
        self.assertEqual(result["disposition"], "withhold-batch")

    def test_surplus_alone_does_not_withhold_the_batch(self):
        rows = supply_for(case_spec()) + [
            {"item": "process-change-notice", "status": "issued", "revision": REVISION}
        ]
        result = assess_wafer_deliverables(handover_spec(supplied=rows))
        self.assertTrue(result["accepted"])
        self.assertTrue(any("does not owe it" in f for f in result["findings"]))

    def test_radiation_batch_without_its_data_is_withheld(self):
        case = case_spec(radiation_environment=True)
        rows = supply_for(case, drop=("radiation-evaluation-data",))
        spec = dict(case)
        spec["supplied"] = rows
        result = assess_wafer_deliverables(spec)
        self.assertEqual(result["disposition"], "withhold-batch")
        self.assertTrue(any("Radiation" in f for f in result["findings"]))

    def test_completeness_fraction_is_reported(self):
        spec = handover_spec(supplied=supply_for(case_spec(), drop=("wafer-map",)))
        result = assess_wafer_deliverables(spec)
        required = len(result["required"])
        self.assertAlmostEqual(
            result["completeness_fraction"],
            (required - 1) / float(required),
            places=9,
        )

    def test_assessment_requires_the_supplied_key(self):
        with self.assertRaises(ValueError):
            assess_wafer_deliverables(case_spec())

    def test_assessment_rejects_an_unknown_case_key(self):
        spec = handover_spec()
        spec["frist_lot"] = True
        with self.assertRaises(ValueError):
            assess_wafer_deliverables(spec)


if __name__ == "__main__":
    unittest.main()
