"""Contract tests for the clause 6.3.2 class 3 order-documentation logic."""

import unittest

from q6013_class_3_procurement_specification_logic import (
    CARRIERS,
    COMPLETENESS_TOLERANCE,
    PROJECT_CONTROLLED_CARRIERS,
    REQUIRED_CONTENT,
    assess_class3_specification,
    collect_content,
    completeness_figures,
    grade_content_item,
    permitted_carriers,
    validate_completeness_policy,
    validate_content_declaration,
    validate_specification_header,
)

POLICY = {"completeness_floor": 1.0}
HEADER = {
    "identifier": "PS-COTS-114",
    "issue": "2",
    "approving_authority": "product assurance manager",
}
DATA_SHEET = {"document": "MFR-DS-77120", "issue": "C"}


def _entry(item, carrier="purchase-specification", location="section 4.2", citation=None):
    record = {"item": item, "carrier": carrier, "location": location}
    if citation is not None:
        record["citation"] = citation
    return record


def _full_content():
    return [_entry(name) for name, _ in REQUIRED_CONTENT]


def _case(**overrides):
    case = {
        "policy": dict(POLICY),
        "specification": dict(HEADER),
        "content": _full_content(),
    }
    case.update(overrides)
    return case


class RegisterTests(unittest.TestCase):
    def test_every_required_item_has_at_least_one_permitted_carrier(self):
        for name, carriers in REQUIRED_CONTENT:
            self.assertTrue(carriers, name)

    def test_no_required_item_is_listed_twice(self):
        names = [name for name, _ in REQUIRED_CONTENT]
        self.assertEqual(len(set(names)), len(names))

    def test_temperature_range_may_not_rest_on_the_data_sheet(self):
        self.assertNotIn("manufacturer-data-sheet",
                         permitted_carriers("ordered-operating-temperature-range"))

    def test_acceptance_route_is_restricted_to_project_controlled_carriers(self):
        self.assertEqual(permitted_carriers("acceptance-route-for-the-delivery"),
                         tuple(PROJECT_CONTROLLED_CARRIERS))

    def test_parameter_limits_may_rest_on_the_data_sheet(self):
        self.assertIn("manufacturer-data-sheet", permitted_carriers("electrical-parameter-limits"))

    def test_item_outside_the_register_rejected(self):
        with self.assertRaises(ValueError):
            permitted_carriers("delivery-lead-time")


class PolicyTests(unittest.TestCase):
    def test_floor_returned_as_a_float(self):
        self.assertAlmostEqual(
            validate_completeness_policy({"completeness_floor": 0.75})["completeness_floor"],
            0.75, places=9,
        )

    def test_zero_floor_rejected(self):
        with self.assertRaises(ValueError):
            validate_completeness_policy({"completeness_floor": 0.0})

    def test_floor_above_one_rejected(self):
        with self.assertRaises(ValueError):
            validate_completeness_policy({"completeness_floor": 1.2})

    def test_non_numeric_floor_rejected(self):
        with self.assertRaises(ValueError):
            validate_completeness_policy({"completeness_floor": "high"})


class HeaderTests(unittest.TestCase):
    def test_complete_header_is_identified(self):
        header = validate_specification_header(dict(HEADER))
        self.assertTrue(header["identified"])
        self.assertEqual(header["missing"], [])

    def test_header_without_an_issue_is_not_identified(self):
        header = validate_specification_header(dict(HEADER, issue=""))
        self.assertFalse(header["identified"])
        self.assertIn("issue", header["missing"])

    def test_absent_header_returns_none(self):
        self.assertIsNone(validate_specification_header(None))

    def test_non_mapping_header_rejected(self):
        with self.assertRaises(ValueError):
            validate_specification_header("PS-COTS-114 issue 2")

    def test_non_string_header_field_rejected(self):
        with self.assertRaises(ValueError):
            validate_specification_header(dict(HEADER, issue=2))


class DeclarationTests(unittest.TestCase):
    def test_declaration_returned_normalized(self):
        record = validate_content_declaration(
            {"item": "Storage Condition Or Shelf Life", "carrier": "Order Text",
             "location": "order line 7"}
        )
        self.assertEqual(record["item"], "storage-condition-or-shelf-life")
        self.assertEqual(record["carrier"], "order-text")

    def test_unknown_carrier_rejected(self):
        with self.assertRaises(ValueError):
            validate_content_declaration(
                {"item": "storage-condition-or-shelf-life", "carrier": "a supplier email"}
            )

    def test_missing_carrier_key_rejected(self):
        with self.assertRaises(ValueError):
            validate_content_declaration({"item": "storage-condition-or-shelf-life"})

    def test_citation_with_both_halves_is_locked(self):
        record = validate_content_declaration(
            _entry("electrical-parameter-limits", "manufacturer-data-sheet",
                   citation=dict(DATA_SHEET))
        )
        self.assertTrue(record["citation_locked"])

    def test_citation_without_an_issue_is_not_locked(self):
        record = validate_content_declaration(
            _entry("electrical-parameter-limits", "manufacturer-data-sheet",
                   citation={"document": "MFR-DS-77120", "issue": ""})
        )
        self.assertFalse(record["citation_locked"])

    def test_non_mapping_citation_rejected(self):
        with self.assertRaises(ValueError):
            validate_content_declaration(
                {"item": "electrical-parameter-limits",
                 "carrier": "manufacturer-data-sheet", "citation": "the data sheet"}
            )

    def test_repeated_item_declaration_rejected(self):
        with self.assertRaises(ValueError):
            collect_content([_entry("storage-condition-or-shelf-life"),
                             _entry("storage-condition-or-shelf-life")])

    def test_non_sequence_content_rejected(self):
        with self.assertRaises(ValueError):
            collect_content(_entry("storage-condition-or-shelf-life"))


class GradingTests(unittest.TestCase):
    def test_specification_carrier_with_an_identified_header_is_covered(self):
        graded = grade_content_item(
            "acceptance-route-for-the-delivery",
            validate_content_declaration(_entry("acceptance-route-for-the-delivery")),
            validate_specification_header(dict(HEADER)),
        )
        self.assertEqual(graded["state"], "covered")
        self.assertTrue(graded["covered"])

    def test_undeclared_item_is_absent(self):
        graded = grade_content_item(
            "acceptance-route-for-the-delivery", None,
            validate_specification_header(dict(HEADER)),
        )
        self.assertEqual(graded["state"], "absent")

    def test_temperature_range_on_the_data_sheet_is_a_misplaced_item(self):
        graded = grade_content_item(
            "ordered-operating-temperature-range",
            validate_content_declaration(
                _entry("ordered-operating-temperature-range", "manufacturer-data-sheet",
                       citation=dict(DATA_SHEET))
            ),
            validate_specification_header(dict(HEADER)),
        )
        self.assertEqual(graded["state"], "carrier-not-permitted")

    def test_unissued_data_sheet_citation_is_not_locked(self):
        graded = grade_content_item(
            "electrical-parameter-limits",
            validate_content_declaration(
                _entry("electrical-parameter-limits", "manufacturer-data-sheet",
                       citation={"document": "MFR-DS-77120", "issue": ""})
            ),
            validate_specification_header(dict(HEADER)),
        )
        self.assertEqual(graded["state"], "citation-not-locked")

    def test_specification_carrier_with_no_specification_is_unidentified(self):
        graded = grade_content_item(
            "acceptance-route-for-the-delivery",
            validate_content_declaration(_entry("acceptance-route-for-the-delivery")),
            None,
        )
        self.assertEqual(graded["state"], "carrier-not-identified")
        self.assertIn("no specification declared", graded["reason"])

    def test_declaration_with_no_location_is_untraceable(self):
        graded = grade_content_item(
            "nonconformance-notification-requirement",
            validate_content_declaration(
                _entry("nonconformance-notification-requirement", "order-text", location="")
            ),
            validate_specification_header(dict(HEADER)),
        )
        self.assertEqual(graded["state"], "location-not-cited")

    def test_empty_graded_list_rejected(self):
        with self.assertRaises(ValueError):
            completeness_figures([])


class AssessmentTests(unittest.TestCase):
    def test_fully_specified_order_is_acceptable(self):
        result = assess_class3_specification(_case())
        self.assertEqual(result["verdict"], "order documentation meets class 3 expectations")
        self.assertTrue(result["acceptable"])
        self.assertEqual(result["findings"], [])
        self.assertAlmostEqual(result["figures"]["completeness"], 1.0, places=9)

    def test_mixed_carriers_are_all_acceptable_when_permitted(self):
        content = [
            _entry("manufacturer-part-number-and-variant", "order-text", "order line 1"),
            _entry("electrical-parameter-limits", "manufacturer-data-sheet",
                   "table 2", dict(DATA_SHEET)),
            _entry("ordered-operating-temperature-range", "order-text", "order line 2"),
            _entry("acceptance-route-for-the-delivery", "order-text", "order line 3"),
            _entry("marking-and-lot-traceability-requirement", "order-text", "order line 4"),
            _entry("packaging-and-esd-protection-requirement", "manufacturer-data-sheet",
                   "section 9", dict(DATA_SHEET)),
            _entry("storage-condition-or-shelf-life", "manufacturer-data-sheet",
                   "section 10", dict(DATA_SHEET)),
            _entry("nonconformance-notification-requirement", "order-text", "order line 5"),
        ]
        result = assess_class3_specification(_case(specification=None, content=content))
        self.assertTrue(result["acceptable"])
        self.assertEqual(result["figures"]["data_sheet_items"], 3)
        self.assertAlmostEqual(result["figures"]["data_sheet_share"], 3.0 / 8.0, places=9)

    def test_no_content_at_all_closes_on_not_declared(self):
        result = assess_class3_specification(_case(content=[]))
        self.assertEqual(result["verdict"], "order documentation not declared")
        self.assertEqual(len(result["absent_items"]), len(REQUIRED_CONTENT))

    def test_misplaced_item_outranks_an_absent_one_in_the_verdict(self):
        content = [
            _entry("acceptance-route-for-the-delivery", "manufacturer-data-sheet",
                   "section 3", dict(DATA_SHEET))
        ]
        result = assess_class3_specification(_case(content=content))
        self.assertEqual(result["verdict"],
                         "required content carried where the class does not permit it")
        self.assertEqual(result["misplaced_items"], ["acceptance-route-for-the-delivery"])

    def test_absent_item_is_named_and_the_order_is_not_acceptable(self):
        content = [e for e in _full_content()
                   if e["item"] != "marking-and-lot-traceability-requirement"]
        result = assess_class3_specification(_case(content=content))
        self.assertEqual(result["verdict"], "required content absent")
        self.assertEqual(result["absent_items"], ["marking-and-lot-traceability-requirement"])

    def test_unidentified_specification_makes_every_specification_item_untraceable(self):
        result = assess_class3_specification(_case(specification={"identifier": "PS-COTS-114"}))
        self.assertEqual(result["verdict"], "required content not traceable to an identified carrier")
        self.assertEqual(len(result["untraceable_items"]), len(REQUIRED_CONTENT))

    def test_extraneous_declaration_is_its_own_finding(self):
        content = _full_content() + [_entry("delivery-lead-time", "order-text", "order line 9")]
        result = assess_class3_specification(_case(content=content))
        self.assertEqual(result["extraneous_declarations"], ["delivery-lead-time"])
        self.assertTrue(any("not required content" in f for f in result["findings"]))

    def test_completeness_exactly_on_the_floor_raises_no_floor_finding(self):
        content = [e for e in _full_content()
                   if e["item"] != "storage-condition-or-shelf-life"]
        result = assess_class3_specification(
            _case(policy={"completeness_floor": 7.0 / 8.0}, content=content)
        )
        self.assertAlmostEqual(result["figures"]["completeness"],
                               result["policy"]["completeness_floor"], places=9)
        self.assertFalse(any("below the declared floor" in f for f in result["findings"]))

    def test_every_finding_is_carried_not_only_the_first(self):
        result = assess_class3_specification(_case(content=[]))
        self.assertEqual(len(result["findings"]), len(REQUIRED_CONTENT) + 1)
        self.assertTrue(any("below the declared floor" in f for f in result["findings"]))

    def test_data_sheet_share_is_zero_when_nothing_is_covered(self):
        result = assess_class3_specification(_case(content=[]))
        self.assertAlmostEqual(result["figures"]["data_sheet_share"], 0.0, places=9)

    def test_missing_case_key_rejected(self):
        case = _case()
        del case["content"]
        with self.assertRaises(ValueError):
            assess_class3_specification(case)

    def test_non_mapping_case_rejected(self):
        with self.assertRaises(ValueError):
            assess_class3_specification(["policy"])

    def test_carrier_list_covers_every_declared_carrier_token(self):
        for _, carriers in REQUIRED_CONTENT:
            for carrier in carriers:
                self.assertIn(carrier, CARRIERS)

    def test_tolerance_is_small_enough_to_be_representation_only(self):
        self.assertLess(COMPLETENESS_TOLERANCE, 1e-6)


if __name__ == "__main__":
    unittest.main()
