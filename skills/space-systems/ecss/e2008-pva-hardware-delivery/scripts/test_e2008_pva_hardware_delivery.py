#!/usr/bin/env python3
"""Contract test for PVA hardware delivery with documentation (offline)."""

import copy
import unittest

from e2008_pva_hardware_delivery_logic import (
    CONFORMANCE_STATES,
    DEFAULT_DELIVERY_POLICY,
    DELIVERY_HELD,
    DELIVERY_RELEASABLE,
    DOCUMENT_LOT_MISMATCH,
    DOCUMENT_NOT_ISSUED,
    DOCUMENT_RELEASED,
    ITEM_HELD,
    ITEM_SHIPPABLE,
    ITEM_SHIPPABLE_ON_WAIVER,
    REQUIRED_DELIVERY_DOCUMENTS,
    assess_delivery,
    assess_delivery_document,
    assess_delivery_item,
    documentation_status,
    reconcile_delivery_quantity,
    required_delivery_documents,
    validate_delivery_policy,
)

LOT = "pva-lot-14"
STANDARD = "build standard issue c"


def _package(lot=LOT, **overrides):
    package = [
        {"name": name, "status": "issued", "lot_reference": lot}
        for name in REQUIRED_DELIVERY_DOCUMENTS
    ]
    for entry in package:
        if entry["name"] in overrides:
            entry.update(overrides[entry["name"]])
    return package


def _item(serial, conformance="conforming", build_standard=STANDARD):
    return {
        "serial": serial,
        "conformance": conformance,
        "build_standard": build_standard,
    }


def _case(**overrides):
    case = {
        "lot_reference": LOT,
        "build_standard": STANDARD,
        "ordered_quantity": 4,
        "items": [_item("sn-01"), _item("sn-02"), _item("sn-03"), _item("sn-04")],
        "documentation": _package(),
    }
    case.update(overrides)
    return case


class PolicyTests(unittest.TestCase):
    def test_default_policy_validates(self):
        self.assertIs(
            validate_delivery_policy(DEFAULT_DELIVERY_POLICY), DEFAULT_DELIVERY_POLICY
        )

    def test_policy_covers_every_conformance_state(self):
        for state in CONFORMANCE_STATES:
            self.assertIn(state, DEFAULT_DELIVERY_POLICY["conformance_disposition"])

    def test_non_mapping_policy_rejected(self):
        with self.assertRaises(ValueError):
            validate_delivery_policy("ship it")

    def test_policy_with_zero_delivered_fraction_rejected(self):
        broken = copy.deepcopy(DEFAULT_DELIVERY_POLICY)
        broken["min_delivered_fraction"] = 0.0
        with self.assertRaises(ValueError):
            validate_delivery_policy(broken)

    def test_policy_with_non_boolean_partial_flag_rejected(self):
        broken = copy.deepcopy(DEFAULT_DELIVERY_POLICY)
        broken["allow_partial_delivery"] = "yes"
        with self.assertRaises(ValueError):
            validate_delivery_policy(broken)

    def test_policy_missing_a_conformance_state_rejected(self):
        broken = copy.deepcopy(DEFAULT_DELIVERY_POLICY)
        del broken["conformance_disposition"]["open-non-conformance"]
        with self.assertRaises(ValueError):
            validate_delivery_policy(broken)

    def test_policy_with_an_unknown_disposition_rejected(self):
        broken = copy.deepcopy(DEFAULT_DELIVERY_POLICY)
        broken["conformance_disposition"]["conforming"] = "probably-fine"
        with self.assertRaises(ValueError):
            validate_delivery_policy(broken)


class DocumentTests(unittest.TestCase):
    def test_required_set_is_the_documentation_package(self):
        self.assertEqual(required_delivery_documents(), REQUIRED_DELIVERY_DOCUMENTS)
        self.assertIn("certificate-of-conformity", required_delivery_documents())

    def test_issued_document_citing_the_shipping_lot_is_released(self):
        record = assess_delivery_document(
            {
                "name": "certificate-of-conformity",
                "status": "issued",
                "lot_reference": LOT,
            },
            LOT,
        )
        self.assertEqual(record["verdict"], DOCUMENT_RELEASED)
        self.assertEqual(record["findings"], [])

    def test_draft_document_is_not_issued(self):
        record = assess_delivery_document(
            {
                "name": "acceptance-test-report",
                "status": "draft",
                "lot_reference": LOT,
            },
            LOT,
        )
        self.assertEqual(record["verdict"], DOCUMENT_NOT_ISSUED)
        self.assertTrue(any("draft" in f for f in record["findings"]))

    def test_document_citing_another_lot_is_a_mismatch(self):
        record = assess_delivery_document(
            {
                "name": "as-built-configuration-record",
                "status": "issued",
                "lot_reference": "pva-lot-13",
            },
            LOT,
        )
        self.assertEqual(record["verdict"], DOCUMENT_LOT_MISMATCH)

    def test_unknown_document_name_rejected(self):
        with self.assertRaises(ValueError):
            assess_delivery_document(
                {"name": "packing-note", "status": "issued", "lot_reference": LOT}, LOT
            )

    def test_unknown_document_status_rejected(self):
        with self.assertRaises(ValueError):
            assess_delivery_document(
                {
                    "name": "parts-and-materials-list",
                    "status": "nearly-ready",
                    "lot_reference": LOT,
                },
                LOT,
            )

    def test_document_without_a_cited_lot_rejected(self):
        with self.assertRaises(ValueError):
            assess_delivery_document(
                {
                    "name": "non-conformance-record",
                    "status": "issued",
                    "lot_reference": "   ",
                },
                LOT,
            )


class DocumentationPackageTests(unittest.TestCase):
    def test_full_package_is_complete(self):
        status = documentation_status(_package(), LOT)
        self.assertTrue(status["complete"])
        self.assertTrue(status["accepted"])
        self.assertAlmostEqual(status["released_fraction"], 1.0, places=9)
        self.assertEqual(status["absent_documents"], [])

    def test_absent_document_lowers_the_released_share(self):
        package = [
            entry
            for entry in _package()
            if entry["name"] != "handling-and-storage-instruction"
        ]
        status = documentation_status(package, LOT)
        self.assertFalse(status["complete"])
        self.assertEqual(
            status["absent_documents"], ["handling-and-storage-instruction"]
        )
        self.assertAlmostEqual(status["released_fraction"], 5.0 / 6.0, places=9)

    def test_draft_document_is_not_counted_as_released(self):
        status = documentation_status(
            _package(**{"certificate-of-conformity": {"status": "draft"}}), LOT
        )
        self.assertFalse(status["complete"])
        self.assertAlmostEqual(status["released_fraction"], 5.0 / 6.0, places=9)

    def test_package_for_the_wrong_lot_is_not_released(self):
        status = documentation_status(_package(lot="pva-lot-13"), LOT)
        self.assertFalse(status["complete"])
        self.assertAlmostEqual(status["released_fraction"], 0.0, places=9)
        self.assertTrue(any("cites lot" in f for f in status["findings"]))

    def test_policy_may_accept_an_incomplete_package(self):
        policy = copy.deepcopy(DEFAULT_DELIVERY_POLICY)
        policy["require_full_documentation"] = False
        package = [
            entry for entry in _package() if entry["name"] != "non-conformance-record"
        ]
        status = documentation_status(package, LOT, policy)
        self.assertFalse(status["complete"])
        self.assertTrue(status["accepted"])

    def test_repeated_document_rejected(self):
        package = _package() + [
            {
                "name": "certificate-of-conformity",
                "status": "issued",
                "lot_reference": LOT,
            }
        ]
        with self.assertRaises(ValueError):
            documentation_status(package, LOT)

    def test_non_sequence_package_rejected(self):
        with self.assertRaises(ValueError):
            documentation_status({"name": "certificate-of-conformity"}, LOT)


class ItemTests(unittest.TestCase):
    def test_conforming_item_is_shippable(self):
        record = assess_delivery_item(_item("sn-01"), STANDARD)
        self.assertEqual(record["verdict"], ITEM_SHIPPABLE)
        self.assertEqual(record["findings"], [])

    def test_waived_item_ships_on_the_waiver(self):
        record = assess_delivery_item(
            _item("sn-02", conformance="waived-non-conformance"), STANDARD
        )
        self.assertEqual(record["verdict"], ITEM_SHIPPABLE_ON_WAIVER)
        self.assertTrue(any("dispositioned" in f for f in record["findings"]))

    def test_open_non_conformance_holds_the_item(self):
        record = assess_delivery_item(
            _item("sn-03", conformance="open-non-conformance"), STANDARD
        )
        self.assertEqual(record["verdict"], ITEM_HELD)

    def test_wrong_build_standard_holds_an_otherwise_clean_item(self):
        record = assess_delivery_item(
            _item("sn-04", build_standard="build standard issue b"), STANDARD
        )
        self.assertEqual(record["verdict"], ITEM_HELD)
        self.assertTrue(any("built to" in f for f in record["findings"]))

    def test_unknown_conformance_state_rejected(self):
        with self.assertRaises(ValueError):
            assess_delivery_item(_item("sn-05", conformance="probably-fine"), STANDARD)

    def test_item_without_a_serial_rejected(self):
        with self.assertRaises(ValueError):
            assess_delivery_item(_item("  "), STANDARD)

    def test_non_mapping_item_rejected(self):
        with self.assertRaises(ValueError):
            assess_delivery_item("sn-01", STANDARD)


class QuantityTests(unittest.TestCase):
    def test_full_shipment_is_complete(self):
        result = reconcile_delivery_quantity(4, 4)
        self.assertTrue(result["complete"])
        self.assertTrue(result["acceptable"])
        self.assertAlmostEqual(result["delivered_fraction"], 1.0, places=9)

    def test_share_exactly_on_the_partial_limit_is_accepted(self):
        result = reconcile_delivery_quantity(10, 9)
        self.assertAlmostEqual(result["delivered_fraction"], 0.90, places=9)
        self.assertAlmostEqual(result["required_fraction"], 0.90, places=9)
        self.assertFalse(result["complete"])
        self.assertTrue(result["acceptable"])

    def test_share_below_the_partial_limit_is_refused(self):
        result = reconcile_delivery_quantity(10, 8)
        self.assertFalse(result["acceptable"])
        self.assertTrue(any("falls below" in f for f in result["findings"]))

    def test_partial_shipment_refused_when_policy_forbids_it(self):
        policy = copy.deepcopy(DEFAULT_DELIVERY_POLICY)
        policy["allow_partial_delivery"] = False
        result = reconcile_delivery_quantity(10, 9, policy)
        self.assertFalse(result["acceptable"])
        self.assertTrue(any("not allowed" in f for f in result["findings"]))

    def test_over_delivery_is_reported_but_still_complete(self):
        result = reconcile_delivery_quantity(4, 5)
        self.assertTrue(result["over_delivery"])
        self.assertTrue(result["complete"])
        self.assertTrue(any("offered against" in f for f in result["findings"]))

    def test_zero_ordered_quantity_rejected(self):
        with self.assertRaises(ValueError):
            reconcile_delivery_quantity(0, 0)

    def test_fractional_ordered_quantity_rejected(self):
        with self.assertRaises(ValueError):
            reconcile_delivery_quantity(4.5, 4)

    def test_negative_shippable_count_rejected(self):
        with self.assertRaises(ValueError):
            reconcile_delivery_quantity(4, -1)


class DeliveryTests(unittest.TestCase):
    def test_clean_delivery_is_releasable(self):
        result = assess_delivery(_case())
        self.assertEqual(result["verdict"], DELIVERY_RELEASABLE)
        self.assertEqual(result["findings"], [])
        self.assertEqual(result["shippable_count"], 4)

    def test_waived_item_still_ships_with_the_lot(self):
        case = _case(
            items=[
                _item("sn-01"),
                _item("sn-02", conformance="waived-non-conformance"),
                _item("sn-03"),
                _item("sn-04"),
            ]
        )
        result = assess_delivery(case)
        self.assertEqual(result["verdict"], DELIVERY_RELEASABLE)
        self.assertEqual(
            result["grouped_by_verdict"][ITEM_SHIPPABLE_ON_WAIVER], ["sn-02"]
        )

    def test_one_held_item_drops_the_lot_below_the_partial_limit(self):
        case = _case(
            items=[
                _item("sn-01"),
                _item("sn-02", conformance="open-non-conformance"),
                _item("sn-03"),
                _item("sn-04"),
            ]
        )
        result = assess_delivery(case)
        self.assertEqual(result["verdict"], DELIVERY_HELD)
        self.assertEqual(result["held_serials"], ["sn-02"])
        self.assertAlmostEqual(result["quantity"]["delivered_fraction"], 0.75, places=9)

    def test_draft_certificate_holds_a_full_crate(self):
        case = _case(
            documentation=_package(**{"certificate-of-conformity": {"status": "draft"}})
        )
        result = assess_delivery(case)
        self.assertEqual(result["verdict"], DELIVERY_HELD)
        self.assertTrue(result["quantity"]["acceptable"])
        self.assertFalse(result["documentation"]["complete"])

    def test_documentation_for_another_lot_holds_the_delivery(self):
        result = assess_delivery(_case(documentation=_package(lot="pva-lot-13")))
        self.assertEqual(result["verdict"], DELIVERY_HELD)
        self.assertAlmostEqual(
            result["documentation"]["released_fraction"], 0.0, places=9
        )

    def test_delivery_groups_items_by_verdict(self):
        case = _case(
            items=[
                _item("sn-01"),
                _item("sn-02", build_standard="build standard issue b"),
                _item("sn-03"),
                _item("sn-04"),
            ]
        )
        grouped = assess_delivery(case)["grouped_by_verdict"]
        self.assertEqual(grouped[ITEM_HELD], ["sn-02"])
        self.assertEqual(len(grouped[ITEM_SHIPPABLE]), 3)

    def test_repeated_serial_rejected(self):
        case = _case(items=[_item("sn-01"), _item("sn-01")], ordered_quantity=2)
        with self.assertRaises(ValueError):
            assess_delivery(case)

    def test_delivery_without_items_rejected(self):
        with self.assertRaises(ValueError):
            assess_delivery(_case(items=[]))

    def test_delivery_without_a_lot_reference_rejected(self):
        with self.assertRaises(ValueError):
            assess_delivery(_case(lot_reference=""))

    def test_non_mapping_case_rejected(self):
        with self.assertRaises(ValueError):
            assess_delivery([_item("sn-01")])


if __name__ == "__main__":
    unittest.main()
