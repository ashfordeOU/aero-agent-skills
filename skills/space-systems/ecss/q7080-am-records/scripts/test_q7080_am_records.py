#!/usr/bin/env python3
"""Contract test for build records and traceability (offline)."""

import copy
import unittest

from q7080_am_records_logic import (
    BLANK,
    CORE_RECORD_FIELDS,
    DEFAULT_RECORD_POLICY,
    MISSING,
    PART_CLASSES,
    PRESENT,
    audit_build_record,
    blend_acceptable,
    completeness_score,
    field_status,
    powder_blend,
    required_fields,
    retention_status,
    traceability_gaps,
    validate_record_policy,
)

RECORD = {
    "build_id": "B-2026-014",
    "machine_id": "M-07",
    "parameter_set_id": "PS-ti64-60",
    "layer_thickness_mm": 0.06,
    "build_atmosphere": "argon",
    "powder_lots": [
        {"lot_id": "L-441", "mass_kg": 12.0, "reuse_generation": 0},
        {"lot_id": "L-392", "mass_kg": 8.0, "reuse_generation": 2},
    ],
    "build_layout_id": "BL-19",
    "operator_id": "OP-3",
    "inspection_result_ref": "INS-114",
    "witness_coupon_ref": ["WIT-51", "WIT-52"],
    "thermal_post_process_ref": "HIP-88",
    "approver_id": "AP-1",
}

INDEX = ("INS-114", "WIT-51", "WIT-52", "HIP-88")

CASE = {
    "part_class": "class-b",
    "record": RECORD,
    "document_index": INDEX,
    "years_held": 3,
}


def _record(**overrides):
    record = copy.deepcopy(RECORD)
    record.update(overrides)
    return record


def _case(**overrides):
    case = copy.deepcopy(CASE)
    case.update(overrides)
    return case


class PolicyTests(unittest.TestCase):
    def test_default_policy_validates(self):
        self.assertIs(
            validate_record_policy(DEFAULT_RECORD_POLICY), DEFAULT_RECORD_POLICY
        )

    def test_non_mapping_policy_rejected(self):
        with self.assertRaises(ValueError):
            validate_record_policy("default")

    def test_policy_missing_a_class_rejected(self):
        broken = copy.deepcopy(DEFAULT_RECORD_POLICY)
        del broken["retention_years"]["class-a"]
        with self.assertRaises(ValueError):
            validate_record_policy(broken)

    def test_out_of_range_virgin_limit_rejected(self):
        broken = copy.deepcopy(DEFAULT_RECORD_POLICY)
        broken["min_virgin_mass_fraction"]["class-a"] = 1.4
        with self.assertRaises(ValueError):
            validate_record_policy(broken)


class RequiredFieldTests(unittest.TestCase):
    def test_every_class_carries_the_core_fields(self):
        for part_class in PART_CLASSES:
            fields = required_fields(part_class)
            for core in CORE_RECORD_FIELDS:
                self.assertIn(core, fields)

    def test_the_demanding_class_owes_more(self):
        self.assertGreater(
            len(required_fields("class-a")), len(required_fields("class-c"))
        )

    def test_unknown_class_rejected(self):
        with self.assertRaises(ValueError):
            required_fields("class-z")


class FieldStatusTests(unittest.TestCase):
    def test_a_full_record_is_all_present(self):
        status = field_status(RECORD, "class-b")
        self.assertTrue(all(state == PRESENT for state in status.values()))
        self.assertAlmostEqual(completeness_score(status), 1.0, places=12)

    def test_an_absent_key_is_missing(self):
        record = _record()
        del record["machine_id"]
        status = field_status(record, "class-b")
        self.assertEqual(status["machine_id"], MISSING)

    def test_an_empty_string_is_blank_not_present(self):
        status = field_status(_record(operator_id="   "), "class-b")
        self.assertEqual(status["operator_id"], BLANK)

    def test_an_empty_list_is_blank_not_present(self):
        status = field_status(_record(powder_lots=[]), "class-b")
        self.assertEqual(status["powder_lots"], BLANK)

    def test_a_zero_value_is_present(self):
        status = field_status(_record(layer_thickness_mm=0.0), "class-b")
        self.assertEqual(status["layer_thickness_mm"], PRESENT)

    def test_score_falls_with_each_hole(self):
        record = _record()
        del record["machine_id"]
        full = completeness_score(field_status(RECORD, "class-b"))
        holed = completeness_score(field_status(record, "class-b"))
        self.assertLess(holed, full)

    def test_non_mapping_record_rejected(self):
        with self.assertRaises(ValueError):
            field_status("B-2026-014", "class-b")

    def test_empty_status_rejected(self):
        with self.assertRaises(ValueError):
            completeness_score({})


class PowderBlendTests(unittest.TestCase):
    def test_virgin_fraction_is_mass_weighted(self):
        blend = powder_blend(RECORD["powder_lots"])
        self.assertAlmostEqual(blend["virgin_mass_fraction"], 0.6, places=12)
        self.assertAlmostEqual(blend["total_mass_kg"], 20.0, places=12)

    def test_mean_generation_is_mass_weighted(self):
        blend = powder_blend(RECORD["powder_lots"])
        self.assertAlmostEqual(blend["mean_reuse_generation"], 0.8, places=12)

    def test_highest_generation_is_carried_separately(self):
        blend = powder_blend(RECORD["powder_lots"])
        self.assertEqual(blend["max_reuse_generation"], 2)

    def test_repeated_lot_rejected(self):
        with self.assertRaises(ValueError):
            powder_blend(
                [
                    {"lot_id": "L-441", "mass_kg": 5.0, "reuse_generation": 0},
                    {"lot_id": "L-441", "mass_kg": 5.0, "reuse_generation": 1},
                ]
            )

    def test_unnamed_lot_rejected(self):
        with self.assertRaises(ValueError):
            powder_blend([{"lot_id": "", "mass_kg": 5.0, "reuse_generation": 0}])

    def test_zero_mass_rejected(self):
        with self.assertRaises(ValueError):
            powder_blend([{"lot_id": "L-1", "mass_kg": 0.0, "reuse_generation": 0}])

    def test_fractional_generation_rejected(self):
        with self.assertRaises(ValueError):
            powder_blend([{"lot_id": "L-1", "mass_kg": 5.0, "reuse_generation": 1.5}])

    def test_empty_blend_rejected(self):
        with self.assertRaises(ValueError):
            powder_blend([])


class BlendLimitTests(unittest.TestCase):
    def test_blend_within_limits_is_acceptable(self):
        blend = powder_blend(RECORD["powder_lots"])
        self.assertTrue(blend_acceptable(blend, "class-b")["acceptable"])

    def test_thin_virgin_share_fails_the_demanding_class(self):
        blend = powder_blend(
            [
                {"lot_id": "L-1", "mass_kg": 2.0, "reuse_generation": 0},
                {"lot_id": "L-2", "mass_kg": 18.0, "reuse_generation": 1},
            ]
        )
        result = blend_acceptable(blend, "class-a")
        self.assertFalse(result["acceptable"])
        self.assertTrue(any("virgin" in f for f in result["findings"]))

    def test_virgin_share_exactly_on_the_limit_passes(self):
        blend = powder_blend(
            [
                {"lot_id": "L-1", "mass_kg": 10.0, "reuse_generation": 0},
                {"lot_id": "L-2", "mass_kg": 10.0, "reuse_generation": 1},
            ]
        )
        self.assertAlmostEqual(
            blend["virgin_mass_fraction"],
            DEFAULT_RECORD_POLICY["min_virgin_mass_fraction"]["class-a"],
            places=12,
        )
        self.assertTrue(blend_acceptable(blend, "class-a")["acceptable"])

    def test_over_reused_powder_fails(self):
        blend = powder_blend(
            [
                {"lot_id": "L-1", "mass_kg": 15.0, "reuse_generation": 0},
                {"lot_id": "L-2", "mass_kg": 5.0, "reuse_generation": 9},
            ]
        )
        result = blend_acceptable(blend, "class-a")
        self.assertFalse(result["acceptable"])
        self.assertTrue(any("reuse generation" in f for f in result["findings"]))

    def test_non_mapping_blend_rejected(self):
        with self.assertRaises(ValueError):
            blend_acceptable("virgin", "class-b")


class TraceabilityTests(unittest.TestCase):
    def test_resolved_references_leave_no_gap(self):
        self.assertEqual(traceability_gaps(RECORD, INDEX), [])

    def test_unresolved_reference_is_reported(self):
        gaps = traceability_gaps(_record(inspection_result_ref="INS-999"), INDEX)
        self.assertEqual(len(gaps), 1)
        self.assertEqual(gaps[0]["reference"], "INS-999")

    def test_each_member_of_a_reference_list_is_checked(self):
        gaps = traceability_gaps(
            _record(witness_coupon_ref=["WIT-51", "WIT-99"]), INDEX
        )
        self.assertEqual([gap["reference"] for gap in gaps], ["WIT-99"])

    def test_blank_reference_is_not_treated_as_a_link(self):
        self.assertEqual(traceability_gaps(_record(thermal_post_process_ref=""), INDEX), [])

    def test_non_string_reference_rejected(self):
        with self.assertRaises(ValueError):
            traceability_gaps(_record(inspection_result_ref=114), INDEX)

    def test_non_collection_index_rejected(self):
        with self.assertRaises(ValueError):
            traceability_gaps(RECORD, "INS-114")


class RetentionTests(unittest.TestCase):
    def test_record_inside_its_retention_is_not_disposable(self):
        status = retention_status(3, "class-b")
        self.assertFalse(status["disposable"])
        self.assertEqual(status["years_remaining"], 12)

    def test_record_past_its_retention_is_disposable(self):
        status = retention_status(25, "class-a")
        self.assertTrue(status["disposable"])
        self.assertEqual(status["years_remaining"], 0)

    def test_negative_years_rejected(self):
        with self.assertRaises(ValueError):
            retention_status(-1, "class-b")


class AuditTests(unittest.TestCase):
    def test_complete_record_closes(self):
        result = audit_build_record(CASE)
        self.assertTrue(result["complete"])
        self.assertEqual(result["verdict"], "record-complete-and-traceable")

    def test_missing_field_opens_the_record(self):
        record = _record()
        del record["parameter_set_id"]
        result = audit_build_record(_case(record=record))
        self.assertFalse(result["complete"])
        self.assertEqual(result["verdict"], "record-incomplete")
        self.assertIn("parameter_set_id", result["missing_fields"])

    def test_blank_field_is_separated_from_a_missing_one(self):
        result = audit_build_record(_case(record=_record(operator_id="")))
        self.assertIn("operator_id", result["blank_fields"])
        self.assertEqual(result["missing_fields"], [])

    def test_broken_reference_opens_the_record(self):
        result = audit_build_record(_case(record=_record(inspection_result_ref="INS-999")))
        self.assertFalse(result["complete"])
        self.assertEqual(len(result["traceability_gaps"]), 1)

    def test_bad_powder_history_is_its_own_verdict(self):
        record = _record(
            powder_lots=[
                {"lot_id": "L-1", "mass_kg": 1.0, "reuse_generation": 0},
                {"lot_id": "L-2", "mass_kg": 19.0, "reuse_generation": 2},
            ]
        )
        result = audit_build_record(_case(record=record))
        self.assertFalse(result["complete"])
        self.assertEqual(result["missing_fields"], [])
        self.assertEqual(result["verdict"], "material-history-unacceptable")

    def test_retention_is_reported_with_the_verdict(self):
        result = audit_build_record(_case(years_held=20))
        self.assertTrue(result["retention"]["disposable"])

    def test_every_class_is_auditable(self):
        for part_class in PART_CLASSES:
            result = audit_build_record(_case(part_class=part_class))
            self.assertEqual(result["part_class"], part_class)

    def test_non_mapping_case_rejected(self):
        with self.assertRaises(ValueError):
            audit_build_record("class-b")

    def test_case_without_a_record_rejected(self):
        with self.assertRaises(ValueError):
            audit_build_record({"part_class": "class-b"})


if __name__ == "__main__":
    unittest.main()
