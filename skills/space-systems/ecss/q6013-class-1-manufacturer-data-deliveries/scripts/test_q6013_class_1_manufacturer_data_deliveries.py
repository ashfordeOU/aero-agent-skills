"""Contract tests for the clause 4.3.11 delivered-data-package logic."""

import unittest

from q6013_class_1_manufacturer_data_deliveries_logic import (
    COVERAGE_TOLERANCE,
    REQUIRED_DELIVERABLES,
    assess_data_delivery,
    coverage_fraction,
    date_code_in_window,
    deliverable_states,
    delivery_verdict,
    item_findings,
    missing_deliverables,
    normalize_lot_code,
    parse_date_code,
    validate_delivery_item,
)

LOT = {
    "lot_code": "LOT-4471-B",
    "lot_units": 500,
    "date_code_window": ("2312", "2338"),
    "required_coverage": 1.0,
}


def _item(kind, **over):
    base = {
        "kind": kind,
        "state": "delivered",
        "lot_code": "LOT-4471-B",
        "date_code": "2320",
        "units_covered": 500,
        "signed": True,
        "data_type": "variables",
    }
    base.update(over)
    return base


def _full_package(**over):
    items = [
        _item("conformance-certificate", data_type=None),
        _item("lot-electrical-test-data"),
        _item("screening-test-data"),
        _item("traceability-record", data_type=None),
        _item("process-change-statement", data_type=None),
    ]
    package = {"lot": dict(LOT), "items": items}
    package.update(over)
    return package


class LotCodeTests(unittest.TestCase):
    def test_separators_and_case_are_normalised(self):
        self.assertEqual(normalize_lot_code(" lot-4471/b "), "LOT4471B")

    def test_two_written_forms_of_one_lot_compare_equal(self):
        self.assertEqual(normalize_lot_code("LOT 4471 B"), normalize_lot_code("lot-4471-b"))

    def test_empty_lot_code_rejected(self):
        with self.assertRaises(ValueError):
            normalize_lot_code("   ")

    def test_punctuation_only_lot_code_rejected(self):
        with self.assertRaises(ValueError):
            normalize_lot_code("---")

    def test_non_string_lot_code_rejected(self):
        with self.assertRaises(ValueError):
            normalize_lot_code(4471)


class DateCodeTests(unittest.TestCase):
    def test_year_and_week_are_split(self):
        self.assertEqual(parse_date_code("2320"), (23, 20))

    def test_week_zero_rejected(self):
        with self.assertRaises(ValueError):
            parse_date_code("2300")

    def test_week_beyond_fifty_three_rejected(self):
        with self.assertRaises(ValueError):
            parse_date_code("2354")

    def test_short_date_code_rejected(self):
        with self.assertRaises(ValueError):
            parse_date_code("231")

    def test_window_contains_its_own_edges(self):
        self.assertTrue(date_code_in_window("2312", ("2312", "2338")))
        self.assertTrue(date_code_in_window("2338", ("2312", "2338")))

    def test_earlier_date_code_falls_outside_the_window(self):
        self.assertFalse(date_code_in_window("2248", ("2312", "2338")))

    def test_backwards_window_rejected(self):
        with self.assertRaises(ValueError):
            date_code_in_window("2320", ("2338", "2312"))


class DeliveryItemTests(unittest.TestCase):
    def test_delivered_item_is_normalised(self):
        record = validate_delivery_item(_item("conformance-certificate"))
        self.assertEqual(record["lot_code"], "LOT4471B")
        self.assertEqual(record["units_covered"], 500)
        self.assertTrue(record["signed"])

    def test_waived_item_needs_a_waiver_reference(self):
        with self.assertRaises(ValueError):
            validate_delivery_item({"kind": "screening-test-data", "state": "waived"})

    def test_waived_item_keeps_its_reference(self):
        record = validate_delivery_item(
            {"kind": "screening-test-data", "state": "waived", "waiver_reference": "DEV-18"}
        )
        self.assertEqual(record["waiver_reference"], "DEV-18")
        self.assertEqual(record["units_covered"], 0)

    def test_unknown_state_rejected(self):
        with self.assertRaises(ValueError):
            validate_delivery_item(_item("traceability-record", state="maybe"))

    def test_unknown_data_type_rejected(self):
        with self.assertRaises(ValueError):
            validate_delivery_item(_item("screening-test-data", data_type="summary"))

    def test_non_boolean_signature_rejected(self):
        with self.assertRaises(ValueError):
            validate_delivery_item(_item("conformance-certificate", signed="yes"))

    def test_negative_unit_count_rejected(self):
        with self.assertRaises(ValueError):
            validate_delivery_item(_item("screening-test-data", units_covered=-1))

    def test_item_must_be_a_mapping(self):
        with self.assertRaises(ValueError):
            validate_delivery_item(["conformance-certificate"])


class CoverageTests(unittest.TestCase):
    def test_full_lot_coverage_is_unity(self):
        self.assertAlmostEqual(coverage_fraction(500, 500), 1.0, places=9)

    def test_partial_coverage(self):
        self.assertAlmostEqual(coverage_fraction(125, 500), 0.25, places=9)

    def test_coverage_beyond_the_lot_rejected(self):
        with self.assertRaises(ValueError):
            coverage_fraction(501, 500)

    def test_empty_lot_rejected(self):
        with self.assertRaises(ValueError):
            coverage_fraction(0, 0)


class ItemFindingTests(unittest.TestCase):
    def test_conforming_record_raises_nothing(self):
        record = validate_delivery_item(_item("lot-electrical-test-data"))
        self.assertEqual(item_findings(record, LOT), [])

    def test_foreign_lot_code_is_critical(self):
        record = validate_delivery_item(_item("screening-test-data", lot_code="LOT-4472-B"))
        findings = item_findings(record, LOT)
        self.assertEqual([f["severity"] for f in findings], ["critical"])

    def test_unsigned_certificate_is_major(self):
        record = validate_delivery_item(_item("conformance-certificate", signed=False))
        severities = [f["severity"] for f in item_findings(record, LOT)]
        self.assertIn("major", severities)

    def test_attributes_only_test_data_is_major(self):
        record = validate_delivery_item(
            _item("lot-electrical-test-data", data_type="attributes")
        )
        messages = [f["message"] for f in item_findings(record, LOT)]
        self.assertTrue(any("measured values" in m for m in messages))

    def test_short_coverage_is_major(self):
        record = validate_delivery_item(_item("screening-test-data", units_covered=499))
        severities = [f["severity"] for f in item_findings(record, LOT)]
        self.assertIn("major", severities)

    def test_coverage_exactly_at_the_required_value_passes(self):
        lot = dict(LOT, required_coverage=0.5)
        record = validate_delivery_item(_item("screening-test-data", units_covered=250))
        self.assertAlmostEqual(
            coverage_fraction(250, lot["lot_units"]), lot["required_coverage"], places=9
        )
        self.assertEqual(item_findings(record, lot), [])

    def test_tolerance_is_small_enough_to_keep_a_real_shortfall(self):
        self.assertAlmostEqual(COVERAGE_TOLERANCE, 1e-9, places=12)
        record = validate_delivery_item(_item("screening-test-data", units_covered=450))
        severities = [f["severity"] for f in item_findings(record, LOT)]
        self.assertIn("major", severities)

    def test_date_code_outside_the_purchased_window_is_minor(self):
        record = validate_delivery_item(_item("traceability-record", date_code="2248"))
        severities = [f["severity"] for f in item_findings(record, LOT)]
        self.assertEqual(severities, ["minor"])

    def test_undeclared_data_type_on_test_data_is_minor(self):
        record = validate_delivery_item(_item("screening-test-data", data_type=None))
        severities = [f["severity"] for f in item_findings(record, LOT)]
        self.assertEqual(severities, ["minor"])


class DeliverableStateTests(unittest.TestCase):
    def test_absent_kinds_are_reported(self):
        records = [validate_delivery_item(_item("conformance-certificate"))]
        self.assertIn("screening-test-data", missing_deliverables(records))

    def test_waived_is_not_absent(self):
        records = [
            validate_delivery_item(
                {"kind": "screening-test-data", "state": "waived", "waiver_reference": "DEV-18"}
            )
        ]
        states = deliverable_states(records)
        self.assertEqual(states["screening-test-data"], "waived")
        self.assertNotIn("screening-test-data", missing_deliverables(records))

    def test_empty_required_set_rejected(self):
        with self.assertRaises(ValueError):
            deliverable_states([], required=[])


class VerdictTests(unittest.TestCase):
    def test_no_findings_accepts(self):
        self.assertEqual(delivery_verdict([]), "accepted")

    def test_minor_finding_keeps_the_package_with_actions(self):
        self.assertEqual(
            delivery_verdict([{"severity": "minor", "kind": "x", "message": "m"}]),
            "accepted-with-actions",
        )

    def test_critical_finding_rejects(self):
        self.assertEqual(
            delivery_verdict([{"severity": "critical", "kind": "x", "message": "m"}]),
            "rejected",
        )

    def test_finding_without_severity_rejected(self):
        with self.assertRaises(ValueError):
            delivery_verdict([{"kind": "x"}])


class AssessmentTests(unittest.TestCase):
    def test_complete_package_is_accepted(self):
        result = assess_data_delivery(_full_package())
        self.assertTrue(result["accepted"])
        self.assertEqual(result["findings"], [])
        self.assertEqual(result["missing"], [])

    def test_missing_kind_rejects_and_is_named(self):
        package = _full_package()
        package["items"] = [i for i in package["items"] if i["kind"] != "screening-test-data"]
        result = assess_data_delivery(package)
        self.assertEqual(result["verdict"], "rejected")
        self.assertEqual(result["missing"], ["screening-test-data"])

    def test_findings_are_ranked_critical_first(self):
        package = _full_package()
        package["items"][1]["lot_code"] = "LOT-9999-Z"
        package["items"][3]["date_code"] = "2248"
        result = assess_data_delivery(package)
        self.assertEqual(result["findings"][0]["severity"], "critical")
        self.assertEqual(result["findings"][-1]["severity"], "minor")

    def test_not_applicable_is_not_a_free_pass(self):
        package = _full_package()
        package["items"][2] = {"kind": "screening-test-data", "state": "not-applicable"}
        result = assess_data_delivery(package)
        severities = [f["severity"] for f in result["findings"]]
        self.assertIn("major", severities)
        self.assertEqual(result["missing"], [])

    def test_waiver_is_recorded_without_rejecting(self):
        package = _full_package()
        package["items"][4] = {
            "kind": "process-change-statement",
            "state": "waived",
            "waiver_reference": "DEV-22",
        }
        result = assess_data_delivery(package)
        self.assertEqual(result["verdict"], "accepted-with-actions")

    def test_required_kinds_default_to_the_class_one_set(self):
        result = assess_data_delivery(_full_package())
        self.assertEqual(sorted(result["deliverable_states"]), sorted(REQUIRED_DELIVERABLES))

    def test_zero_size_lot_rejected(self):
        package = _full_package()
        package["lot"]["lot_units"] = 0
        with self.assertRaises(ValueError):
            assess_data_delivery(package)

    def test_coverage_outside_the_unit_interval_rejected(self):
        package = _full_package()
        package["lot"]["required_coverage"] = 1.5
        with self.assertRaises(ValueError):
            assess_data_delivery(package)

    def test_missing_package_key_rejected(self):
        with self.assertRaises(ValueError):
            assess_data_delivery({"lot": dict(LOT)})

    def test_package_must_be_a_mapping(self):
        with self.assertRaises(ValueError):
            assess_data_delivery([_full_package()])


if __name__ == "__main__":
    unittest.main(verbosity=1)
