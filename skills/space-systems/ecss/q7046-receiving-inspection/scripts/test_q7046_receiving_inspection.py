#!/usr/bin/env python3
"""Contract test for fastener receiving inspection (offline)."""

import copy
import unittest

from q7046_receiving_inspection_logic import (
    CRITICALITIES,
    DISPOSITION_ACCEPT,
    DISPOSITION_QUARANTINE,
    DISPOSITION_REJECT,
    DISPOSITION_RETEST,
    DOC_CONFORMITY,
    DOC_MATERIAL,
    DOC_TRACEABILITY,
    INSPECTION_LEVELS,
    LEVEL_NORMAL,
    LEVEL_REDUCED,
    LEVEL_TIGHTENED,
    acceptance_number,
    assess_receiving,
    dimensional_verdict,
    document_findings,
    marking_verdict,
    required_documents,
    retest_required,
    sample_size,
)

TOLERANCES = {
    "head-height-mm": (5.3, 0.15, 0.0),
    "shank-diameter-mm": (7.96, 0.04, 0.0),
    "thread-length-mm": (22.0, 0.5, 0.5),
}

MEASUREMENTS = {
    "head-height-mm": 5.28,
    "shank-diameter-mm": 7.95,
    "thread-length-mm": 22.1,
}

GOOD_CASE = {
    "criticality": "structural",
    "lot_size": 500,
    "inspection_level": LEVEL_NORMAL,
    "ordered_class": "10.9",
    "marking": {
        "property_class": "10.9",
        "manufacturer_id": "SUP-41",
        "lot_code": "L-2209",
    },
    "documents_present": list(required_documents("structural")),
    "tolerances": TOLERANCES,
    "measurements": MEASUREMENTS,
    "non_conforming_parts": 0,
}


def _case(**overrides):
    case = copy.deepcopy(GOOD_CASE)
    case.update(overrides)
    return case


class SamplePlanTests(unittest.TestCase):
    def test_sample_grows_with_the_lot(self):
        self.assertGreater(sample_size(5000), sample_size(50))

    def test_tightened_level_draws_more_than_normal(self):
        self.assertGreater(
            sample_size(500, LEVEL_TIGHTENED), sample_size(500, LEVEL_NORMAL)
        )

    def test_reduced_level_draws_fewer_than_normal(self):
        self.assertLess(
            sample_size(500, LEVEL_REDUCED), sample_size(500, LEVEL_NORMAL)
        )

    def test_sample_never_exceeds_the_lot(self):
        for lot in range(1, 40):
            for level in INSPECTION_LEVELS:
                self.assertLessEqual(sample_size(lot, level), lot)

    def test_sample_is_monotone_in_the_lot(self):
        previous = 0
        for lot in (1, 8, 9, 25, 26, 90, 91, 280, 281, 1200, 1201, 10000, 10001):
            current = sample_size(lot)
            self.assertGreaterEqual(current, previous)
            previous = current

    def test_a_very_large_lot_falls_in_the_last_band(self):
        self.assertEqual(sample_size(500000, LEVEL_NORMAL), 50)

    def test_zero_lot_rejected(self):
        with self.assertRaises(ValueError):
            sample_size(0)

    def test_unknown_inspection_level_rejected(self):
        with self.assertRaises(ValueError):
            sample_size(500, "vibes")


class AllowanceTests(unittest.TestCase):
    def test_a_fracture_critical_lot_allows_no_defective(self):
        self.assertEqual(acceptance_number(5000, "fracture-critical"), 0)

    def test_minor_hardware_allows_more_than_structural(self):
        self.assertGreaterEqual(
            acceptance_number(10000, "non-structural"),
            acceptance_number(10000, "structural"),
        )

    def test_allowance_is_never_negative(self):
        for lot in (1, 50, 500, 5000):
            for criticality in CRITICALITIES:
                self.assertGreaterEqual(acceptance_number(lot, criticality), 0)


class DocumentTests(unittest.TestCase):
    def test_a_fracture_critical_lot_owes_traceability(self):
        self.assertIn(DOC_TRACEABILITY, required_documents("fracture-critical"))

    def test_minor_hardware_owes_fewer_documents(self):
        self.assertLess(
            len(required_documents("non-structural")),
            len(required_documents("structural")),
        )

    def test_a_conformity_certificate_is_owed_by_every_criticality(self):
        for criticality in CRITICALITIES:
            self.assertIn(DOC_CONFORMITY, required_documents(criticality))

    def test_a_complete_delivery_has_no_missing_documents(self):
        result = document_findings(
            "structural", required_documents("structural")
        )
        self.assertTrue(result["complete"])

    def test_a_missing_document_is_named(self):
        present = [
            d for d in required_documents("structural") if d != DOC_MATERIAL
        ]
        result = document_findings("structural", present)
        self.assertEqual(result["missing"], [DOC_MATERIAL])

    def test_documents_given_as_a_string_rejected(self):
        with self.assertRaises(ValueError):
            document_findings("structural", DOC_CONFORMITY)


class MarkingTests(unittest.TestCase):
    def test_a_correct_marking_conforms(self):
        outcome = marking_verdict(
            {"property_class": "10.9", "manufacturer_id": "SUP-41"},
            "10.9",
            "structural",
        )
        self.assertTrue(outcome["conforming"])

    def test_a_class_that_disagrees_with_the_order_is_reported(self):
        outcome = marking_verdict(
            {"property_class": "8.8", "manufacturer_id": "SUP-41"},
            "10.9",
            "structural",
        )
        self.assertFalse(outcome["class_agrees"])
        self.assertTrue(any("different product" in f for f in outcome["findings"]))

    def test_a_missing_manufacturer_identifier_is_a_finding(self):
        outcome = marking_verdict(
            {"property_class": "10.9"}, "10.9", "structural"
        )
        self.assertFalse(outcome["conforming"])

    def test_a_fracture_critical_lot_needs_a_lot_code_on_the_part(self):
        outcome = marking_verdict(
            {"property_class": "10.9", "manufacturer_id": "SUP-41"},
            "10.9",
            "fracture-critical",
        )
        self.assertFalse(outcome["conforming"])

    def test_an_unreadable_marking_is_reported_as_unreadable(self):
        outcome = marking_verdict(None, "10.9", "structural")
        self.assertFalse(outcome["readable"])

    def test_a_marking_given_as_a_string_rejected(self):
        with self.assertRaises(ValueError):
            marking_verdict("10.9 SUP-41", "10.9", "structural")

    def test_an_empty_ordered_class_rejected(self):
        with self.assertRaises(ValueError):
            marking_verdict({"property_class": "10.9"}, "", "structural")


class DimensionTests(unittest.TestCase):
    def test_a_sample_inside_every_band_conforms(self):
        result = dimensional_verdict(MEASUREMENTS, TOLERANCES)
        self.assertTrue(result["conforming"])

    def test_a_value_on_the_lower_limit_conforms(self):
        measurements = dict(MEASUREMENTS)
        measurements["shank-diameter-mm"] = 7.96 - 0.04
        result = dimensional_verdict(measurements, TOLERANCES)
        self.assertEqual(result["out_of_tolerance"], [])

    def test_a_value_on_the_upper_limit_conforms(self):
        measurements = dict(MEASUREMENTS)
        measurements["thread-length-mm"] = 22.0 + 0.5
        result = dimensional_verdict(measurements, TOLERANCES)
        self.assertEqual(result["out_of_tolerance"], [])

    def test_a_value_outside_its_band_is_named(self):
        measurements = dict(MEASUREMENTS)
        measurements["head-height-mm"] = 5.6
        result = dimensional_verdict(measurements, TOLERANCES)
        self.assertEqual(result["out_of_tolerance"], ["head-height-mm"])

    def test_an_unmeasured_feature_is_a_coverage_gap_not_a_pass(self):
        measurements = dict(MEASUREMENTS)
        del measurements["thread-length-mm"]
        result = dimensional_verdict(measurements, TOLERANCES)
        self.assertEqual(result["unmeasured"], ["thread-length-mm"])
        self.assertFalse(result["conforming"])

    def test_a_reading_with_no_tolerance_is_reported_separately(self):
        measurements = dict(MEASUREMENTS)
        measurements["paint-gloss"] = 3.0
        result = dimensional_verdict(measurements, TOLERANCES)
        self.assertEqual(result["unexpected_features"], ["paint-gloss"])

    def test_an_empty_tolerance_set_rejected(self):
        with self.assertRaises(ValueError):
            dimensional_verdict(MEASUREMENTS, {})

    def test_a_malformed_tolerance_band_rejected(self):
        with self.assertRaises(ValueError):
            dimensional_verdict({"a": 1.0}, {"a": (1.0, 0.1)})

    def test_a_negative_tolerance_magnitude_rejected(self):
        with self.assertRaises(ValueError):
            dimensional_verdict({"a": 1.0}, {"a": (1.0, -0.1, 0.1)})


class RetestTriggerTests(unittest.TestCase):
    def test_a_fracture_critical_lot_always_owes_a_retest(self):
        self.assertTrue(retest_required("fracture-critical", False, True)["required"])

    def test_a_missing_document_triggers_a_retest(self):
        self.assertTrue(retest_required("structural", True, True)["required"])

    def test_an_unreadable_marking_triggers_a_retest(self):
        self.assertTrue(retest_required("structural", False, False)["required"])

    def test_a_clean_structural_delivery_owes_no_retest(self):
        self.assertFalse(retest_required("structural", False, True)["required"])

    def test_every_trigger_carries_its_reason(self):
        outcome = retest_required("fracture-critical", True, False)
        self.assertEqual(len(outcome["reasons"]), 3)


class DispositionTests(unittest.TestCase):
    def test_a_clean_delivery_is_released(self):
        self.assertEqual(
            assess_receiving(_case())["disposition"], DISPOSITION_ACCEPT
        )

    def test_a_missing_document_quarantines_rather_than_rejects(self):
        present = [
            d for d in required_documents("structural") if d != DOC_MATERIAL
        ]
        result = assess_receiving(_case(documents_present=present))
        self.assertEqual(result["disposition"], DISPOSITION_QUARANTINE)

    def test_a_wrong_class_mark_rejects_the_lot(self):
        case = _case(
            marking={
                "property_class": "8.8",
                "manufacturer_id": "SUP-41",
                "lot_code": "L-1",
            }
        )
        self.assertEqual(assess_receiving(case)["disposition"], DISPOSITION_REJECT)

    def test_an_unreadable_mark_holds_for_a_retest_rather_than_rejecting(self):
        result = assess_receiving(_case(marking=None))
        self.assertEqual(result["disposition"], DISPOSITION_RETEST)

    def test_a_performed_retest_releases_an_unreadable_mark(self):
        result = assess_receiving(_case(marking=None, retest_performed=True))
        self.assertEqual(result["disposition"], DISPOSITION_ACCEPT)

    def test_a_readable_but_incomplete_mark_quarantines(self):
        case = _case(marking={"property_class": "10.9"})
        self.assertEqual(
            assess_receiving(case)["disposition"], DISPOSITION_QUARANTINE
        )

    def test_an_out_of_tolerance_feature_rejects(self):
        measurements = dict(MEASUREMENTS)
        measurements["head-height-mm"] = 5.9
        result = assess_receiving(_case(measurements=measurements))
        self.assertEqual(result["disposition"], DISPOSITION_REJECT)

    def test_one_non_conforming_part_rejects_a_fracture_critical_lot(self):
        case = _case(
            criticality="fracture-critical",
            documents_present=required_documents("fracture-critical"),
            non_conforming_parts=1,
            retest_performed=True,
        )
        self.assertEqual(assess_receiving(case)["disposition"], DISPOSITION_REJECT)

    def test_a_fracture_critical_lot_with_no_retest_is_held(self):
        case = _case(
            criticality="fracture-critical",
            documents_present=required_documents("fracture-critical"),
        )
        self.assertEqual(assess_receiving(case)["disposition"], DISPOSITION_RETEST)

    def test_an_unmeasured_feature_quarantines_the_lot(self):
        measurements = dict(MEASUREMENTS)
        del measurements["thread-length-mm"]
        result = assess_receiving(_case(measurements=measurements))
        self.assertEqual(result["disposition"], DISPOSITION_QUARANTINE)

    def test_more_non_conforming_parts_than_the_sample_rejected(self):
        with self.assertRaises(ValueError):
            assess_receiving(_case(non_conforming_parts=10000))

    def test_missing_lot_size_rejected(self):
        case = _case()
        del case["lot_size"]
        with self.assertRaises(ValueError):
            assess_receiving(case)

    def test_missing_tolerances_rejected(self):
        case = _case()
        del case["tolerances"]
        with self.assertRaises(ValueError):
            assess_receiving(case)

    def test_non_mapping_case_rejected(self):
        with self.assertRaises(ValueError):
            assess_receiving("a box of bolts turned up")


if __name__ == "__main__":
    unittest.main()
