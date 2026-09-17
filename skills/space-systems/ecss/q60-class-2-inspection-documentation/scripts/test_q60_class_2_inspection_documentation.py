"""Contract tests for the clause 5.7 class 2 inspection outcome logic."""

import unittest

from q60_class_2_inspection_documentation_logic import (
    ACCEPTANCE_YIELD_ADVISORY_FLOOR,
    BOUND_TOLERANCE,
    CLASS_2_INSPECTION_ACTIVITIES,
    OUTCOME_COVERAGE_FLOOR,
    QUANTITY_FIELDS,
    RECORDING_AUTHORITIES,
    acceptance_yield,
    compile_class_2_inspection_outcomes,
    coverage_meets_floor,
    defective_records,
    group_records_by_activity,
    ordered_activities,
    outcome_coverage,
    recording_disposition,
    reconciled_activities,
    reconciliation_residual,
    record_activity,
    record_defects,
    stated_quantities,
    unrecorded_activities,
)

PERFORMED = ["incoming-inspection", "lot-acceptance-test",
             "screening-verification"]


def _record(**over):
    base = {
        "record_id": "OR-6052-001",
        "activity": "incoming-inspection",
        "lot_code": "LOT-6052-B",
        "recording_authority": "project-quality-assurance",
        "evidence_reference": "inspection-log-6052-001",
        "inspected": 100.0,
        "accepted": 100.0,
        "rejected": 0.0,
        "deferred": 0.0,
    }
    base.update(over)
    return base


def _programme(**over):
    base = {
        "programme_id": "CLASS-2-PARTS-6052",
        "activities_performed": list(PERFORMED),
        "records": [
            _record(),
            _record(record_id="OR-6052-002", activity="lot-acceptance-test",
                    recording_authority="delegated-inspector",
                    evidence_reference="lat-report-6052-002"),
            _record(record_id="OR-6052-003", activity="screening-verification",
                    recording_authority="component-manufacturer",
                    evidence_reference="screening-data-6052-003"),
        ],
    }
    base.update(over)
    return base


class ActivityOrderTests(unittest.TestCase):
    def test_activities_come_back_in_audit_order(self):
        ordered = ordered_activities(["delivery-acceptance-review",
                                      "incoming-inspection"])
        self.assertEqual(ordered, ["incoming-inspection",
                                   "delivery-acceptance-review"])

    def test_activity_names_compare_case_insensitively(self):
        self.assertEqual(ordered_activities(["INCOMING-INSPECTION"]),
                         ["incoming-inspection"])

    def test_an_unknown_activity_is_rejected(self):
        with self.assertRaises(ValueError):
            ordered_activities(["corridor-walkthrough"])

    def test_a_repeated_activity_is_rejected(self):
        with self.assertRaises(ValueError):
            ordered_activities(["incoming-inspection", "incoming-inspection"])

    def test_a_bare_string_is_not_a_sequence_of_activities(self):
        with self.assertRaises(ValueError):
            ordered_activities("incoming-inspection")

    def test_every_listed_activity_is_orderable(self):
        ordered = ordered_activities(list(CLASS_2_INSPECTION_ACTIVITIES))
        self.assertEqual(ordered, list(CLASS_2_INSPECTION_ACTIVITIES))


class RecordActivityTests(unittest.TestCase):
    def test_a_named_activity_comes_back_folded(self):
        self.assertEqual(
            record_activity(_record(activity="INCOMING-INSPECTION")),
            "incoming-inspection")

    def test_a_record_naming_nothing_covers_no_activity(self):
        self.assertIsNone(record_activity(_record(activity="   ")))

    def test_a_record_naming_something_unrecognised_covers_no_activity(self):
        self.assertIsNone(record_activity(_record(activity="corridor-chat")))

    def test_a_record_must_be_a_mapping(self):
        with self.assertRaises(ValueError):
            record_activity("OR-6052-001")


class QuantityTests(unittest.TestCase):
    def test_four_counts_come_back_as_floats(self):
        counts = stated_quantities(_record())
        self.assertEqual(sorted(counts), sorted(QUANTITY_FIELDS))

    def test_a_missing_count_is_rejected(self):
        record = _record()
        del record["deferred"]
        with self.assertRaises(ValueError):
            stated_quantities(record)

    def test_a_negative_count_is_rejected(self):
        with self.assertRaises(ValueError):
            stated_quantities(_record(rejected=-1.0))

    def test_a_non_numeric_count_is_rejected(self):
        with self.assertRaises(ValueError):
            stated_quantities(_record(accepted="one hundred"))

    def test_a_boolean_is_not_a_count(self):
        with self.assertRaises(ValueError):
            stated_quantities(_record(rejected=True))

    def test_a_balanced_record_has_no_residual(self):
        self.assertAlmostEqual(reconciliation_residual(_record()), 0.0, places=9)

    def test_an_unaccounted_part_shows_as_a_positive_residual(self):
        residual = reconciliation_residual(_record(accepted=97.0))
        self.assertAlmostEqual(residual, 3.0, places=9)

    def test_over_accounting_shows_as_a_negative_residual(self):
        residual = reconciliation_residual(_record(rejected=5.0))
        self.assertAlmostEqual(residual, -5.0, places=9)

    def test_a_split_outcome_reconciles(self):
        record = _record(accepted=90.0, rejected=10.0,
                         nonconformance_reference="NCR-6052-04")
        self.assertAlmostEqual(reconciliation_residual(record), 0.0, places=9)


class RecordDefectTests(unittest.TestCase):
    def test_a_sound_record_carries_no_defects(self):
        self.assertEqual(record_defects(_record()), [])

    def test_an_unrecognised_activity_is_a_defect(self):
        self.assertIn("activity-not-recognised",
                      record_defects(_record(activity="corridor-chat")))

    def test_a_missing_lot_identity_is_a_defect(self):
        self.assertIn("lot-identity-not-traceable",
                      record_defects(_record(lot_code="")))

    def test_an_unnamed_recording_authority_is_a_defect(self):
        self.assertIn("recording-authority-not-named",
                      record_defects(_record(recording_authority=None)))

    def test_an_authority_outside_the_accepted_list_is_a_defect(self):
        self.assertIn("recording-authority-not-accepted",
                      record_defects(_record(recording_authority="visiting-guest")))

    def test_an_authority_matches_case_insensitively(self):
        self.assertEqual(
            record_defects(_record(recording_authority="PROJECT-Quality-Assurance")),
            [])

    def test_a_narrowed_authority_list_rejects_a_supplier_record(self):
        defects = record_defects(
            _record(recording_authority="component-manufacturer"),
            ["project-quality-assurance"])
        self.assertIn("recording-authority-not-accepted", defects)

    def test_a_missing_evidence_reference_is_a_defect(self):
        self.assertIn("evidence-reference-missing",
                      record_defects(_record(evidence_reference="  ")))

    def test_unstated_quantities_short_circuit_the_quantity_tests(self):
        record = _record()
        del record["inspected"]
        defects = record_defects(record)
        self.assertIn("quantities-not-stated", defects)
        self.assertNotIn("quantities-do-not-reconcile", defects)

    def test_an_unreconciled_record_is_a_defect(self):
        self.assertIn("quantities-do-not-reconcile",
                      record_defects(_record(accepted=95.0)))

    def test_an_empty_inspection_is_a_defect(self):
        defects = record_defects(_record(inspected=0.0, accepted=0.0))
        self.assertIn("no-quantity-inspected", defects)

    def test_a_rejected_quantity_needs_a_nonconformance_reference(self):
        defects = record_defects(_record(accepted=90.0, rejected=10.0))
        self.assertIn("rejected-quantity-without-nonconformance-reference", defects)

    def test_a_referenced_rejection_is_sound(self):
        record = _record(accepted=90.0, rejected=10.0,
                         nonconformance_reference="NCR-6052-04")
        self.assertEqual(record_defects(record), [])

    def test_a_deferred_quantity_leaves_the_outcome_open(self):
        record = _record(accepted=90.0, deferred=10.0)
        self.assertIn("deferred-quantity-still-open", record_defects(record))

    def test_defects_accumulate(self):
        record = _record(activity="", lot_code="", recording_authority="",
                         evidence_reference="")
        self.assertEqual(len(record_defects(record)), 4)

    def test_the_authority_list_must_be_a_sequence(self):
        with self.assertRaises(ValueError):
            record_defects(_record(), "project-quality-assurance")

    def test_an_empty_authority_list_is_rejected(self):
        with self.assertRaises(ValueError):
            record_defects(_record(), [])

    def test_the_default_authority_list_is_the_published_one(self):
        self.assertEqual(
            record_defects(_record(recording_authority=RECORDING_AUTHORITIES[-1])),
            [])


class GroupingTests(unittest.TestCase):
    def test_records_group_under_the_activity_they_cover(self):
        grouped = group_records_by_activity(_programme()["records"])
        self.assertEqual(len(grouped["incoming-inspection"]), 1)

    def test_an_unrecognised_record_is_grouped_rather_than_dropped(self):
        grouped = group_records_by_activity([_record(activity="corridor-chat")])
        self.assertIn(None, grouped)

    def test_two_records_for_one_activity_group_together(self):
        grouped = group_records_by_activity([_record(), _record(record_id="OR-B")])
        self.assertEqual(len(grouped["incoming-inspection"]), 2)

    def test_records_must_be_a_sequence(self):
        with self.assertRaises(ValueError):
            group_records_by_activity(_record())


class CoverageTests(unittest.TestCase):
    def test_a_covered_programme_has_no_unrecorded_activity(self):
        programme = _programme()
        self.assertEqual(
            unrecorded_activities(programme["activities_performed"],
                                  programme["records"]), [])

    def test_an_activity_with_no_record_is_named(self):
        programme = _programme()
        missing = unrecorded_activities(programme["activities_performed"],
                                        programme["records"][:2])
        self.assertEqual(missing, ["screening-verification"])

    def test_unrecorded_activities_come_back_in_audit_order(self):
        missing = unrecorded_activities(PERFORMED, [])
        indexes = [CLASS_2_INSPECTION_ACTIVITIES.index(n) for n in missing]
        self.assertEqual(indexes, sorted(indexes))

    def test_a_defective_record_still_counts_as_a_record(self):
        records = list(_programme()["records"])
        records[2] = _record(record_id="OR-6052-003",
                             activity="screening-verification",
                             evidence_reference=None)
        self.assertEqual(unrecorded_activities(PERFORMED, records), [])

    def test_a_defective_record_does_not_reconcile_its_activity(self):
        records = list(_programme()["records"])
        records[2] = _record(record_id="OR-6052-003",
                             activity="screening-verification",
                             evidence_reference=None)
        self.assertNotIn("screening-verification",
                         reconciled_activities(PERFORMED, records))

    def test_one_sound_record_among_defective_ones_covers_the_activity(self):
        records = [_record(evidence_reference=None), _record(record_id="OR-B")]
        self.assertEqual(reconciled_activities(["incoming-inspection"], records),
                         ["incoming-inspection"])

    def test_defective_records_are_listed_with_their_reference(self):
        findings = defective_records([_record(lot_code="")])
        self.assertEqual(findings[0]["record"], "OR-6052-001")

    def test_a_record_without_an_identifier_falls_back_to_its_position(self):
        findings = defective_records([_record(record_id=None, lot_code="")])
        self.assertEqual(findings[0]["record"], "record-0")

    def test_a_clean_record_set_reports_no_findings(self):
        self.assertEqual(defective_records(_programme()["records"]), [])

    def test_a_fully_covered_programme_reads_one(self):
        programme = _programme()
        self.assertAlmostEqual(
            outcome_coverage(programme["activities_performed"],
                             programme["records"]), 1.0, places=9)

    def test_an_uncovered_programme_reads_zero(self):
        self.assertAlmostEqual(outcome_coverage(PERFORMED, []), 0.0, places=9)

    def test_two_of_three_activities_read_two_thirds(self):
        programme = _programme()
        value = outcome_coverage(programme["activities_performed"],
                                 programme["records"][:2])
        self.assertAlmostEqual(value, 2.0 / 3.0, places=9)

    def test_an_empty_performed_list_is_rejected(self):
        with self.assertRaises(ValueError):
            outcome_coverage([], [])


class FloorTests(unittest.TestCase):
    def test_full_coverage_meets_the_floor(self):
        self.assertTrue(coverage_meets_floor(1.0))

    def test_coverage_exactly_on_the_floor_meets_it(self):
        self.assertTrue(coverage_meets_floor(OUTCOME_COVERAGE_FLOOR))

    def test_nine_covered_of_ten_meets_the_floor(self):
        self.assertTrue(coverage_meets_floor(9.0 / 10.0))

    def test_two_thirds_does_not_meet_the_floor(self):
        self.assertFalse(coverage_meets_floor(2.0 / 3.0))

    def test_a_coverage_above_one_is_rejected(self):
        with self.assertRaises(ValueError):
            coverage_meets_floor(1.5)

    def test_a_negative_coverage_is_rejected(self):
        with self.assertRaises(ValueError):
            coverage_meets_floor(-0.1)

    def test_the_tolerance_is_the_documented_size(self):
        self.assertAlmostEqual(BOUND_TOLERANCE, 1e-9, places=12)


class YieldTests(unittest.TestCase):
    def test_a_clean_programme_yields_one(self):
        self.assertAlmostEqual(acceptance_yield(_programme()["records"]), 1.0,
                               places=9)

    def test_a_rejection_lowers_the_yield(self):
        records = [_record(accepted=90.0, rejected=10.0,
                           nonconformance_reference="NCR-6052-04")]
        self.assertAlmostEqual(acceptance_yield(records), 0.9, places=9)

    def test_the_yield_is_pooled_across_records(self):
        records = [
            _record(),
            _record(record_id="OR-B", inspected=100.0, accepted=80.0,
                    rejected=20.0, nonconformance_reference="NCR-6052-05"),
        ]
        self.assertAlmostEqual(acceptance_yield(records), 0.9, places=9)

    def test_a_record_stating_no_quantity_contributes_nothing(self):
        partial = _record(record_id="OR-C")
        del partial["accepted"]
        self.assertAlmostEqual(acceptance_yield([_record(), partial]), 1.0,
                               places=9)

    def test_a_record_set_stating_nothing_has_no_yield(self):
        partial = _record()
        del partial["accepted"]
        with self.assertRaises(ValueError):
            acceptance_yield([partial])

    def test_an_empty_inspection_has_no_yield(self):
        with self.assertRaises(ValueError):
            acceptance_yield([_record(inspected=0.0, accepted=0.0)])

    def test_the_advisory_floor_is_the_documented_size(self):
        self.assertAlmostEqual(ACCEPTANCE_YIELD_ADVISORY_FLOOR, 0.95, places=9)


class DispositionTests(unittest.TestCase):
    def test_an_unrecorded_activity_makes_the_set_unreconstructable(self):
        self.assertEqual(
            recording_disposition(["screening-verification"], 1.0),
            "outcomes-not-reconstructable")

    def test_a_coverage_shortfall_reads_as_partially_recorded(self):
        self.assertEqual(recording_disposition([], 2.0 / 3.0),
                         "outcomes-partially-recorded")

    def test_a_covered_set_reads_as_recorded(self):
        self.assertEqual(recording_disposition([], 1.0), "outcomes-recorded")

    def test_the_unrecorded_list_must_be_a_sequence(self):
        with self.assertRaises(ValueError):
            recording_disposition("screening-verification", 1.0)


class CompilationTests(unittest.TestCase):
    def test_a_sound_programme_is_audit_ready(self):
        result = compile_class_2_inspection_outcomes(_programme())
        self.assertTrue(result["audit_ready"])
        self.assertEqual(result["disposition"], "outcomes-recorded")

    def test_a_missing_record_is_named_and_blocks_the_audit(self):
        programme = _programme()
        programme["records"] = programme["records"][:2]
        result = compile_class_2_inspection_outcomes(programme)
        self.assertEqual(result["unrecorded_activities"],
                         ["screening-verification"])
        self.assertFalse(result["audit_ready"])

    def test_a_defective_record_is_reported_with_its_defects(self):
        programme = _programme()
        programme["records"][0] = _record(lot_code="")
        result = compile_class_2_inspection_outcomes(programme)
        self.assertIn("lot-identity-not-traceable",
                      result["defective_records"][0]["defects"])

    def test_a_low_yield_raises_an_advisory_and_not_a_defect(self):
        programme = _programme()
        programme["records"][0] = _record(accepted=80.0, rejected=20.0,
                                          nonconformance_reference="NCR-6052-09")
        result = compile_class_2_inspection_outcomes(programme)
        self.assertIn("acceptance-yield-below-advisory-floor",
                      result["advisories"])
        self.assertEqual(result["defective_records"], [])

    def test_a_high_yield_raises_no_advisory(self):
        result = compile_class_2_inspection_outcomes(_programme())
        self.assertEqual(result["advisories"], [])

    def test_the_yield_is_reported(self):
        result = compile_class_2_inspection_outcomes(_programme())
        self.assertAlmostEqual(result["acceptance_yield"], 1.0, places=9)

    def test_coverage_is_reported(self):
        programme = _programme()
        programme["records"] = programme["records"][:2]
        result = compile_class_2_inspection_outcomes(programme)
        self.assertAlmostEqual(result["outcome_coverage"], 2.0 / 3.0, places=9)

    def test_the_performed_activities_come_back_in_audit_order(self):
        result = compile_class_2_inspection_outcomes(_programme())
        indexes = [CLASS_2_INSPECTION_ACTIVITIES.index(n)
                   for n in result["activities_performed"]]
        self.assertEqual(indexes, sorted(indexes))

    def test_a_narrowed_authority_list_reaches_the_records(self):
        programme = _programme(accepted_authorities=["project-quality-assurance"])
        result = compile_class_2_inspection_outcomes(programme)
        self.assertEqual(len(result["defective_records"]), 2)

    def test_a_programme_with_no_performed_activity_is_rejected(self):
        with self.assertRaises(ValueError):
            compile_class_2_inspection_outcomes(
                _programme(activities_performed=[]))

    def test_the_programme_must_be_a_mapping(self):
        with self.assertRaises(ValueError):
            compile_class_2_inspection_outcomes([_programme()])


if __name__ == "__main__":
    unittest.main(verbosity=1)
