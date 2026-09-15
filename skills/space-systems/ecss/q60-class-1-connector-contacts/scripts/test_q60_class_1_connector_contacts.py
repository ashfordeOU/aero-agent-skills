#!/usr/bin/env python3
"""Contract test for class 1 removable contact sourcing (offline)."""

import copy
import os
import sys
import unittest

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from q60_class_1_connector_contacts_logic import (  # noqa: E402
    APPLICATION_MISMATCH,
    CONTACT_ACCEPTED,
    CONTACT_FINISHES,
    CONTACT_SIZES,
    DEFAULT_CONTACT_POLICY,
    INTERMIX_NOT_QUALIFIED,
    SOURCE_NOT_APPROVED,
    TOOLING_ITEMS,
    TOOLING_NOT_QUALIFIED,
    TRACEABILITY_INCOMPLETE,
    TRACEABILITY_ITEMS,
    accommodated_gauge_range,
    assess_contact_sourcing,
    contact_current_margin_a,
    derated_contact_current_a,
    intermix_findings,
    manufacturer_is_approved,
    missing_tooling_controls,
    missing_traceability,
    normalize_manufacturer,
    rated_contact_current_a,
    validate_contact_case,
    validate_contact_policy,
    wire_gauge_is_accommodated,
)

FULL_TRACEABILITY = {
    "manufacturer_lot_code": "LOT-4471",
    "date_code": "2541",
    "certificate_of_conformance": "CoC-8812",
    "detail_specification_reference": "DS-CTC-20",
}

FULL_TOOLING = {
    "crimp_tool_identifier": "TOOL-114",
    "positioner_identifier": "POS-20",
    "tool_calibration_record": "CAL-2026-03",
    "crimp_acceptance_record": "PULL-2026-03-11",
}

CLEAN_CASE = {
    "contact_manufacturer": "Approved Contacts GmbH",
    "connector_manufacturer": "Approved Contacts GmbH",
    "contact_size": "20",
    "contact_finish": "gold-over-nickel",
    "wire_awg": 22,
    "applied_current_a": 2.0,
    "approved_manufacturers": ["Approved Contacts GmbH", "Second Source SA"],
    "traceability": dict(FULL_TRACEABILITY),
    "tooling": dict(FULL_TOOLING),
}


def _case(**overrides):
    case = copy.deepcopy(CLEAN_CASE)
    case.update(overrides)
    return case


class PolicyTests(unittest.TestCase):
    def test_default_policy_round_trips(self):
        self.assertEqual(validate_contact_policy(None), DEFAULT_CONTACT_POLICY)

    def test_policy_override_is_merged(self):
        merged = validate_contact_policy({"current_derating_factor": 0.4})
        self.assertAlmostEqual(merged["current_derating_factor"], 0.4, places=9)
        self.assertTrue(merged["require_tooling_qualification"])

    def test_unknown_policy_key_rejected(self):
        with self.assertRaises(ValueError):
            validate_contact_policy({"derate": 0.5})

    def test_derating_factor_above_one_rejected(self):
        with self.assertRaises(ValueError):
            validate_contact_policy({"current_derating_factor": 1.4})

    def test_non_positive_derating_factor_rejected(self):
        with self.assertRaises(ValueError):
            validate_contact_policy({"current_derating_factor": 0.0})

    def test_non_boolean_policy_flag_rejected(self):
        with self.assertRaises(ValueError):
            validate_contact_policy({"require_tooling_qualification": "yes"})

    def test_class_one_admits_no_waiver_by_default(self):
        self.assertFalse(DEFAULT_CONTACT_POLICY["allow_unapproved_source_waiver"])


class ApprovalTests(unittest.TestCase):
    def test_name_folding_ignores_case_and_spacing(self):
        self.assertEqual(
            normalize_manufacturer("  Approved   Contacts  GmbH "),
            normalize_manufacturer("approved contacts gmbh"),
        )

    def test_listed_manufacturer_is_approved(self):
        self.assertTrue(
            manufacturer_is_approved(
                "approved contacts gmbh", ["Approved Contacts GmbH"]
            )
        )

    def test_unlisted_manufacturer_is_not_approved(self):
        self.assertFalse(
            manufacturer_is_approved("Bench Spares Ltd", ["Approved Contacts GmbH"])
        )

    def test_blank_manufacturer_rejected(self):
        with self.assertRaises(ValueError):
            manufacturer_is_approved("   ", ["Approved Contacts GmbH"])

    def test_empty_approved_list_rejected(self):
        with self.assertRaises(ValueError):
            manufacturer_is_approved("Approved Contacts GmbH", [])

    def test_string_instead_of_a_list_rejected(self):
        with self.assertRaises(ValueError):
            manufacturer_is_approved(
                "Approved Contacts GmbH", "Approved Contacts GmbH"
            )


class RecordTests(unittest.TestCase):
    def test_complete_traceability_leaves_no_gap(self):
        self.assertEqual(missing_traceability(FULL_TRACEABILITY), ())

    def test_absent_lot_code_is_a_gap(self):
        record = dict(FULL_TRACEABILITY)
        del record["manufacturer_lot_code"]
        self.assertIn("manufacturer_lot_code", missing_traceability(record))

    def test_blank_certificate_is_a_gap(self):
        record = dict(FULL_TRACEABILITY)
        record["certificate_of_conformance"] = "  "
        self.assertIn("certificate_of_conformance", missing_traceability(record))

    def test_unknown_traceability_item_rejected(self):
        with self.assertRaises(ValueError):
            missing_traceability({"supplier_invoice": "INV-1"})

    def test_complete_tooling_leaves_no_gap(self):
        self.assertEqual(missing_tooling_controls(FULL_TOOLING), ())

    def test_absent_calibration_record_is_a_gap(self):
        record = dict(FULL_TOOLING)
        del record["tool_calibration_record"]
        self.assertIn("tool_calibration_record", missing_tooling_controls(record))

    def test_unknown_tooling_item_rejected(self):
        with self.assertRaises(ValueError):
            missing_tooling_controls({"bench_notes": "ok"})

    def test_empty_records_report_every_item(self):
        self.assertEqual(len(missing_traceability({})), len(TRACEABILITY_ITEMS))
        self.assertEqual(len(missing_tooling_controls({})), len(TOOLING_ITEMS))

    def test_non_mapping_record_rejected(self):
        with self.assertRaises(ValueError):
            missing_traceability("LOT-4471")


class GaugeTests(unittest.TestCase):
    def test_size_twenty_accommodates_twenty_two_gauge(self):
        self.assertTrue(wire_gauge_is_accommodated("20", 22))

    def test_size_twenty_rejects_a_sixteen_gauge_conductor(self):
        self.assertFalse(wire_gauge_is_accommodated("20", 16))

    def test_size_twenty_rejects_a_twenty_eight_gauge_conductor(self):
        self.assertFalse(wire_gauge_is_accommodated("20", 28))

    def test_gauge_range_is_reported_largest_first(self):
        largest, smallest = accommodated_gauge_range("16")
        self.assertLess(largest, smallest)

    def test_unknown_contact_size_rejected(self):
        with self.assertRaises(ValueError):
            accommodated_gauge_range("30")

    def test_non_integer_gauge_rejected(self):
        with self.assertRaises(ValueError):
            wire_gauge_is_accommodated("20", 22.5)

    def test_non_positive_gauge_rejected(self):
        with self.assertRaises(ValueError):
            wire_gauge_is_accommodated("20", 0)

    def test_size_lookup_tolerates_surrounding_space(self):
        self.assertEqual(accommodated_gauge_range(" 20 "), accommodated_gauge_range("20"))


class CurrentTests(unittest.TestCase):
    def test_rated_current_comes_from_the_size_table(self):
        self.assertAlmostEqual(rated_contact_current_a("20"), 7.5, places=9)

    def test_default_derating_halves_the_rating(self):
        self.assertAlmostEqual(derated_contact_current_a("20"), 3.75, places=9)

    def test_explicit_derating_factor_is_applied(self):
        self.assertAlmostEqual(
            derated_contact_current_a("16", 0.5), 6.5, places=9
        )

    def test_margin_is_allowance_less_applied(self):
        self.assertAlmostEqual(
            contact_current_margin_a("20", 2.0), 1.75, places=9
        )

    def test_margin_is_zero_exactly_on_the_allowance(self):
        self.assertAlmostEqual(
            contact_current_margin_a("20", 3.75), 0.0, places=9
        )

    def test_margin_is_negative_above_the_allowance(self):
        self.assertLess(contact_current_margin_a("20", 6.0), 0.0)

    def test_derating_factor_above_one_rejected(self):
        with self.assertRaises(ValueError):
            derated_contact_current_a("20", 1.5)

    def test_negative_applied_current_rejected(self):
        with self.assertRaises(ValueError):
            contact_current_margin_a("20", -1.0)

    def test_every_size_has_a_rating_and_a_gauge_range(self):
        for size in CONTACT_SIZES:
            self.assertGreater(rated_contact_current_a(size), 0.0)
            largest, smallest = accommodated_gauge_range(size)
            self.assertLess(largest, smallest)


class IntermixTests(unittest.TestCase):
    def test_same_maker_is_not_an_intermix(self):
        result = intermix_findings(CLEAN_CASE)
        self.assertFalse(result["intermixed"])
        self.assertTrue(result["qualified"])

    def test_different_maker_without_evidence_is_unqualified(self):
        result = intermix_findings(_case(connector_manufacturer="Shell Works SA"))
        self.assertTrue(result["intermixed"])
        self.assertFalse(result["qualified"])

    def test_different_maker_with_evidence_is_qualified(self):
        result = intermix_findings(
            _case(
                connector_manufacturer="Shell Works SA",
                intermix_qualification_reference="QR-2026-19",
            )
        )
        self.assertTrue(result["qualified"])
        self.assertEqual(result["findings"], [])

    def test_policy_can_stand_down_the_intermix_requirement(self):
        result = intermix_findings(
            _case(connector_manufacturer="Shell Works SA"),
            {"require_intermix_qualification": False},
        )
        self.assertTrue(result["qualified"])

    def test_non_mapping_case_rejected(self):
        with self.assertRaises(ValueError):
            intermix_findings("Approved Contacts GmbH")


class SourcingTests(unittest.TestCase):
    def test_clean_case_is_accepted(self):
        result = assess_contact_sourcing(CLEAN_CASE)
        self.assertEqual(result["verdict"], CONTACT_ACCEPTED)
        self.assertTrue(result["accepted"])
        self.assertEqual(result["findings"], [])

    def test_unapproved_source_outranks_every_other_finding(self):
        result = assess_contact_sourcing(
            _case(
                contact_manufacturer="Bench Spares Ltd",
                wire_awg=16,
                traceability={},
            )
        )
        self.assertEqual(result["verdict"], SOURCE_NOT_APPROVED)
        self.assertFalse(result["source_approved"])

    def test_traceability_gap_blocks_an_approved_source(self):
        record = dict(FULL_TRACEABILITY)
        del record["date_code"]
        result = assess_contact_sourcing(_case(traceability=record))
        self.assertEqual(result["verdict"], TRACEABILITY_INCOMPLETE)

    def test_unqualified_intermix_blocks_acceptance(self):
        result = assess_contact_sourcing(
            _case(connector_manufacturer="Shell Works SA")
        )
        self.assertEqual(result["verdict"], INTERMIX_NOT_QUALIFIED)

    def test_wrong_gauge_is_an_application_mismatch(self):
        result = assess_contact_sourcing(_case(wire_awg=16))
        self.assertEqual(result["verdict"], APPLICATION_MISMATCH)
        self.assertFalse(result["wire_gauge_accommodated"])

    def test_overcurrent_is_an_application_mismatch(self):
        result = assess_contact_sourcing(_case(applied_current_a=6.0))
        self.assertEqual(result["verdict"], APPLICATION_MISMATCH)
        self.assertFalse(result["current_within_allowance"])

    def test_current_exactly_on_the_allowance_is_accepted(self):
        result = assess_contact_sourcing(_case(applied_current_a=3.75))
        self.assertTrue(result["current_within_allowance"])
        self.assertAlmostEqual(result["current_margin_a"], 0.0, places=9)
        self.assertEqual(result["verdict"], CONTACT_ACCEPTED)

    def test_missing_tooling_record_blocks_acceptance(self):
        record = dict(FULL_TOOLING)
        del record["crimp_acceptance_record"]
        result = assess_contact_sourcing(_case(tooling=record))
        self.assertEqual(result["verdict"], TOOLING_NOT_QUALIFIED)

    def test_tooling_requirement_can_be_stood_down_by_policy(self):
        result = assess_contact_sourcing(
            _case(tooling={}), {"require_tooling_qualification": False}
        )
        self.assertEqual(result["verdict"], CONTACT_ACCEPTED)

    def test_waiver_policy_lets_an_unapproved_source_report_downstream(self):
        result = assess_contact_sourcing(
            _case(
                contact_manufacturer="Bench Spares Ltd",
                connector_manufacturer="Bench Spares Ltd",
            ),
            {"allow_unapproved_source_waiver": True},
        )
        self.assertEqual(result["verdict"], CONTACT_ACCEPTED)
        self.assertFalse(result["source_approved"])
        self.assertTrue(result["findings"])

    def test_case_missing_a_field_rejected(self):
        case = _case()
        del case["applied_current_a"]
        with self.assertRaises(ValueError):
            assess_contact_sourcing(case)

    def test_unknown_contact_finish_rejected(self):
        with self.assertRaises(ValueError):
            assess_contact_sourcing(_case(contact_finish="tin"))

    def test_every_listed_finish_is_accepted(self):
        for finish in CONTACT_FINISHES:
            result = assess_contact_sourcing(_case(contact_finish=finish))
            self.assertEqual(result["verdict"], CONTACT_ACCEPTED)

    def test_case_validation_accepts_the_reference_case(self):
        self.assertIs(validate_contact_case(CLEAN_CASE), CLEAN_CASE)

    def test_derated_allowance_is_reported(self):
        result = assess_contact_sourcing(CLEAN_CASE)
        self.assertAlmostEqual(
            result["derated_current_allowance_a"], 3.75, places=9
        )


if __name__ == "__main__":
    unittest.main()
