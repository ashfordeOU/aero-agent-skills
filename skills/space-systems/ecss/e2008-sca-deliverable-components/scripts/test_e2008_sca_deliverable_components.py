#!/usr/bin/env python3
"""Contract test for deliverable solar cell assembly components (offline)."""

import copy
import unittest

from e2008_sca_deliverable_components_logic import (
    CONCESSION,
    DELIVERABLE,
    DISPOSITION_RANK,
    DOCUMENT_STATES,
    INSPECTION_OUTCOMES,
    LOT_RELEASABLE,
    LOT_RELEASABLE_WITH_CONCESSIONS,
    LOT_WITHHELD,
    STANDING_CURRENT,
    STANDING_NONE,
    STANDING_OFF_ISSUE,
    WITHHELD,
    assess_delivery_lot,
    disposition_unit,
    document_standing,
    inspection_completeness,
)

REQUIRED = ["visual", "electrical-performance", "dimensional"]

CLEAN_RECORDS = [
    {"kind": "visual", "outcome": "passed"},
    {"kind": "electrical-performance", "outcome": "passed"},
    {"kind": "dimensional", "outcome": "passed"},
]

UNIT_A = {
    "serial": "SCA-0001",
    "document_state": "approved",
    "approved_issue": "C",
    "build_issue": "C",
    "inspections": CLEAN_RECORDS,
}

UNIT_B = {
    "serial": "SCA-0002",
    "document_state": "approved",
    "approved_issue": "C",
    "build_issue": "C",
    "inspections": CLEAN_RECORDS,
}


def _variant(base, **overrides):
    item = copy.deepcopy(base)
    for key, value in overrides.items():
        if value is None and key in item:
            del item[key]
        else:
            item[key] = value
    return item


class DocumentStandingTests(unittest.TestCase):
    def test_approved_document_at_the_build_issue_governs(self):
        result = document_standing("approved", "C", "C")
        self.assertEqual(result["standing"], STANDING_CURRENT)
        self.assertEqual(result["findings"], [])

    def test_a_draft_document_governs_nothing(self):
        result = document_standing("draft", "C", "C")
        self.assertEqual(result["standing"], STANDING_NONE)
        self.assertTrue(any("draft" in f for f in result["findings"]))

    def test_a_withdrawn_document_governs_nothing(self):
        self.assertEqual(
            document_standing("withdrawn", "C", "C")["standing"], STANDING_NONE
        )

    def test_a_superseded_document_needs_the_delta_dispositioned(self):
        result = document_standing("superseded", "D", "C")
        self.assertEqual(result["standing"], STANDING_OFF_ISSUE)
        self.assertTrue(any("superseded" in f for f in result["findings"]))

    def test_a_build_to_the_wrong_issue_of_an_approved_document_is_off_issue(self):
        result = document_standing("approved", "C", "B")
        self.assertEqual(result["standing"], STANDING_OFF_ISSUE)
        self.assertTrue(any("did not approve" in f for f in result["findings"]))

    def test_an_unknown_document_state_is_rejected(self):
        with self.assertRaises(ValueError):
            document_standing("pending-maybe", "C", "C")

    def test_a_blank_build_issue_is_rejected(self):
        with self.assertRaises(ValueError):
            document_standing("approved", "C", "   ")

    def test_every_declared_document_state_is_handled(self):
        for state in DOCUMENT_STATES:
            self.assertIn(
                document_standing(state, "C", "C")["standing"],
                (STANDING_CURRENT, STANDING_OFF_ISSUE, STANDING_NONE),
            )


class InspectionCompletenessTests(unittest.TestCase):
    def test_a_full_clean_record_set_is_complete(self):
        result = inspection_completeness(CLEAN_RECORDS, REQUIRED)
        self.assertEqual(result["missing"], [])
        self.assertAlmostEqual(result["completeness"], 1.0, places=9)

    def test_an_inspection_with_no_record_is_named_missing(self):
        result = inspection_completeness(CLEAN_RECORDS[:2], REQUIRED)
        self.assertEqual(result["missing"], ["dimensional"])
        self.assertTrue(any("not a pass" in f for f in result["findings"]))

    def test_a_listed_inspection_with_no_result_is_not_a_pass(self):
        records = CLEAN_RECORDS[:2] + [
            {"kind": "dimensional", "outcome": "not-performed"}
        ]
        result = inspection_completeness(records, REQUIRED)
        self.assertEqual(result["unperformed"], ["dimensional"])
        self.assertEqual(result["missing"], [])

    def test_a_failed_inspection_is_reported_separately_from_a_missing_one(self):
        records = CLEAN_RECORDS[:2] + [{"kind": "dimensional", "outcome": "failed"}]
        result = inspection_completeness(records, REQUIRED)
        self.assertEqual(result["failed"], ["dimensional"])
        self.assertEqual(result["missing"], [])

    def test_completeness_counts_only_the_inspections_the_process_calls_for(self):
        records = CLEAN_RECORDS + [{"kind": "extra-photo", "outcome": "passed"}]
        result = inspection_completeness(records, REQUIRED)
        self.assertEqual(result["off_process"], ["extra-photo"])
        self.assertAlmostEqual(result["completeness"], 1.0, places=9)

    def test_partial_completeness_is_a_share_not_a_flag(self):
        result = inspection_completeness(CLEAN_RECORDS[:1], REQUIRED)
        self.assertAlmostEqual(result["completeness"], 1.0 / 3.0, places=9)

    def test_a_process_requiring_no_inspection_is_rejected(self):
        with self.assertRaises(ValueError):
            inspection_completeness(CLEAN_RECORDS, [])

    def test_a_duplicated_inspection_record_is_rejected(self):
        records = CLEAN_RECORDS + [{"kind": "visual", "outcome": "failed"}]
        with self.assertRaises(ValueError):
            inspection_completeness(records, REQUIRED)

    def test_an_unknown_inspection_outcome_is_rejected(self):
        with self.assertRaises(ValueError):
            inspection_completeness([{"kind": "visual", "outcome": "probably"}], REQUIRED)

    def test_every_declared_outcome_is_accepted_as_input(self):
        for outcome in INSPECTION_OUTCOMES:
            result = inspection_completeness(
                [{"kind": "visual", "outcome": outcome}], ["visual"]
            )
            self.assertEqual(len(result["required"]), 1)


class UnitDispositionTests(unittest.TestCase):
    def test_a_clean_unit_on_the_approved_issue_is_deliverable(self):
        result = disposition_unit(UNIT_A, REQUIRED)
        self.assertEqual(result["disposition"], DELIVERABLE)
        self.assertEqual(result["findings"], [])

    def test_an_off_issue_build_with_a_concession_releases_on_it(self):
        unit = _variant(UNIT_A, build_issue="B", concession_reference="CON-118")
        result = disposition_unit(unit, REQUIRED)
        self.assertEqual(result["disposition"], CONCESSION)
        self.assertEqual(result["concession_reference"], "CON-118")

    def test_an_off_issue_build_without_a_concession_is_withheld(self):
        result = disposition_unit(_variant(UNIT_A, build_issue="B"), REQUIRED)
        self.assertEqual(result["disposition"], WITHHELD)
        self.assertTrue(any("nothing to release it on" in f for f in result["findings"]))

    def test_a_draft_process_document_withholds_the_unit(self):
        result = disposition_unit(_variant(UNIT_A, document_state="draft"), REQUIRED)
        self.assertEqual(result["disposition"], WITHHELD)

    def test_a_failed_inspection_is_not_a_matter_a_concession_can_carry(self):
        records = CLEAN_RECORDS[:2] + [{"kind": "dimensional", "outcome": "failed"}]
        unit = _variant(UNIT_A, inspections=records, concession_reference="CON-118")
        result = disposition_unit(unit, REQUIRED)
        self.assertEqual(result["disposition"], WITHHELD)
        self.assertTrue(any("not a matter a concession" in f for f in result["findings"]))

    def test_a_missing_inspection_withholds_the_unit(self):
        unit = _variant(UNIT_A, inspections=CLEAN_RECORDS[:2])
        self.assertEqual(disposition_unit(unit, REQUIRED)["disposition"], WITHHELD)

    def test_a_needless_concession_is_flagged_not_acted_on(self):
        unit = _variant(UNIT_A, concession_reference="CON-900")
        result = disposition_unit(unit, REQUIRED)
        self.assertEqual(result["disposition"], DELIVERABLE)
        self.assertTrue(any("need none" in f for f in result["findings"]))

    def test_a_blank_concession_reference_is_rejected(self):
        unit = _variant(UNIT_A, build_issue="B", concession_reference="  ")
        with self.assertRaises(ValueError):
            disposition_unit(unit, REQUIRED)

    def test_a_unit_without_a_serial_is_rejected(self):
        with self.assertRaises(ValueError):
            disposition_unit(_variant(UNIT_A, serial=None), REQUIRED)

    def test_a_non_mapping_unit_is_rejected(self):
        with self.assertRaises(ValueError):
            disposition_unit("SCA-0001", REQUIRED)


class DeliveryLotTests(unittest.TestCase):
    def test_a_clean_lot_releases_outright(self):
        case = {"lot_id": "LOT-77", "units": [UNIT_A, UNIT_B], "required_inspections": REQUIRED}
        result = assess_delivery_lot(case)
        self.assertEqual(result["verdict"], LOT_RELEASABLE)
        self.assertAlmostEqual(result["release_share"], 1.0, places=9)
        self.assertEqual(result["withheld_units"], [])

    def test_one_concession_unit_makes_the_lot_releasable_with_concessions(self):
        unit = _variant(UNIT_B, build_issue="B", concession_reference="CON-118")
        case = {"lot_id": "LOT-77", "units": [UNIT_A, unit], "required_inspections": REQUIRED}
        result = assess_delivery_lot(case)
        self.assertEqual(result["verdict"], LOT_RELEASABLE_WITH_CONCESSIONS)
        self.assertEqual(result["concession_units"], ["SCA-0002"])

    def test_a_withheld_unit_below_the_required_share_withholds_the_lot(self):
        unit = _variant(UNIT_B, inspections=CLEAN_RECORDS[:2])
        case = {
            "lot_id": "LOT-77",
            "units": [UNIT_A, unit],
            "required_inspections": REQUIRED,
            "required_release_share": 1.0,
        }
        result = assess_delivery_lot(case)
        self.assertEqual(result["verdict"], LOT_WITHHELD)
        self.assertEqual(result["withheld_units"], ["SCA-0002"])
        self.assertAlmostEqual(result["release_share"], 0.5, places=9)

    def test_a_release_share_landing_on_its_requirement_is_met(self):
        unit = _variant(UNIT_B, inspections=CLEAN_RECORDS[:2])
        case = {
            "lot_id": "LOT-77",
            "units": [UNIT_A, unit],
            "required_inspections": REQUIRED,
            "required_release_share": 0.5,
        }
        result = assess_delivery_lot(case)
        self.assertEqual(result["verdict"], LOT_RELEASABLE_WITH_CONCESSIONS)
        self.assertAlmostEqual(result["release_share"], 0.5, places=9)

    def test_the_weakest_unit_is_named_for_the_lot(self):
        unit = _variant(UNIT_B, inspections=CLEAN_RECORDS[:1])
        case = {"lot_id": "LOT-77", "units": [UNIT_A, unit], "required_inspections": REQUIRED}
        self.assertEqual(assess_delivery_lot(case)["weakest_unit"], "SCA-0002")

    def test_an_out_of_range_required_share_is_rejected(self):
        case = {
            "lot_id": "LOT-77",
            "units": [UNIT_A],
            "required_inspections": REQUIRED,
            "required_release_share": 1.4,
        }
        with self.assertRaises(ValueError):
            assess_delivery_lot(case)

    def test_a_duplicated_serial_in_the_lot_is_rejected(self):
        case = {
            "lot_id": "LOT-77",
            "units": [UNIT_A, copy.deepcopy(UNIT_A)],
            "required_inspections": REQUIRED,
        }
        with self.assertRaises(ValueError):
            assess_delivery_lot(case)

    def test_an_empty_lot_is_rejected(self):
        with self.assertRaises(ValueError):
            assess_delivery_lot(
                {"lot_id": "LOT-77", "units": [], "required_inspections": REQUIRED}
            )

    def test_a_lot_without_an_identifier_is_rejected(self):
        with self.assertRaises(ValueError):
            assess_delivery_lot({"units": [UNIT_A], "required_inspections": REQUIRED})

    def test_every_unit_disposition_is_ranked(self):
        case = {"lot_id": "LOT-77", "units": [UNIT_A, UNIT_B], "required_inspections": REQUIRED}
        for assessment in assess_delivery_lot(case)["assessments"]:
            self.assertIn(assessment["disposition"], DISPOSITION_RANK)


if __name__ == "__main__":
    unittest.main()
