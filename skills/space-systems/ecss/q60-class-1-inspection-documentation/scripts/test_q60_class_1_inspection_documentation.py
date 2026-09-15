"""Contract tests for the clause 4.7 inspection documentation logic."""

import unittest

from q60_class_1_inspection_documentation_logic import (
    BOUND_TOLERANCE,
    INSPECTION_ACTIVITIES,
    RETENTION_REQUIREMENT_YEARS,
    compile_class_1_inspection_records,
    defective_records,
    documentation_completeness,
    documentation_disposition,
    group_records_by_activity,
    ordered_activities,
    record_activity,
    record_defects,
    retention_shortfall_years,
    sound_activities,
    unrecorded_activities,
)

AUTHORISED = ["QA-Inspector-14", "QA-Inspector-27"]

PERFORMED = ["incoming-inspection", "lot-acceptance-test",
             "destructive-physical-analysis"]


def _record(**over):
    base = {
        "record_id": "IR-6070-001",
        "activity": "incoming-inspection",
        "lot_code": "LOT-6070-C",
        "outcome": "pass",
        "signatory": "QA-Inspector-14",
        "evidence_reference": "photo-set-6070-001",
    }
    base.update(over)
    return base


def _programme(**over):
    base = {
        "programme_id": "CLASS-1-PARTS-6070",
        "activities_performed": list(PERFORMED),
        "records": [
            _record(),
            _record(record_id="IR-6070-002", activity="lot-acceptance-test",
                    evidence_reference="test-log-6070-002"),
            _record(record_id="IR-6070-003",
                    activity="destructive-physical-analysis",
                    signatory="QA-Inspector-27",
                    evidence_reference="dpa-report-6070-003"),
        ],
        "authorised_signatories": list(AUTHORISED),
        "retention_years": 12.0,
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
            ordered_activities(["tea-break-review"])

    def test_a_repeated_activity_is_rejected(self):
        with self.assertRaises(ValueError):
            ordered_activities(["incoming-inspection", "incoming-inspection"])

    def test_a_bare_string_is_not_a_sequence_of_activities(self):
        with self.assertRaises(ValueError):
            ordered_activities("incoming-inspection")

    def test_every_listed_activity_is_orderable(self):
        ordered = ordered_activities(list(INSPECTION_ACTIVITIES))
        self.assertEqual(ordered, list(INSPECTION_ACTIVITIES))


class RecordActivityTests(unittest.TestCase):
    def test_a_named_activity_is_returned_folded(self):
        self.assertEqual(record_activity(_record(activity="INCOMING-INSPECTION")),
                         "incoming-inspection")

    def test_a_record_naming_nothing_covers_no_activity(self):
        self.assertIsNone(record_activity(_record(activity="  ")))

    def test_a_record_naming_something_unrecognised_covers_no_activity(self):
        self.assertIsNone(record_activity(_record(activity="corridor-chat")))

    def test_a_record_must_be_a_mapping(self):
        with self.assertRaises(ValueError):
            record_activity("IR-6070-001")


class RecordDefectTests(unittest.TestCase):
    def test_a_complete_record_carries_no_defects(self):
        self.assertEqual(record_defects(_record(), AUTHORISED), [])

    def test_an_unrecognised_activity_is_a_defect(self):
        defects = record_defects(_record(activity="corridor-chat"), AUTHORISED)
        self.assertIn("activity-not-recognised", defects)

    def test_a_missing_lot_identity_is_a_defect(self):
        defects = record_defects(_record(lot_code=""), AUTHORISED)
        self.assertIn("lot-identity-not-traceable", defects)

    def test_an_unstated_outcome_is_a_defect(self):
        defects = record_defects(_record(outcome=None), AUTHORISED)
        self.assertIn("outcome-not-stated", defects)

    def test_an_outcome_outside_the_vocabulary_is_a_defect(self):
        defects = record_defects(_record(outcome="probably fine"), AUTHORISED)
        self.assertIn("outcome-not-stated", defects)

    def test_an_unnamed_signatory_is_a_defect(self):
        defects = record_defects(_record(signatory=""), AUTHORISED)
        self.assertIn("signatory-not-named", defects)

    def test_a_signatory_outside_the_authorised_list_is_a_defect(self):
        defects = record_defects(_record(signatory="Visiting-Contractor"),
                                 AUTHORISED)
        self.assertIn("signatory-not-authorised", defects)

    def test_a_signatory_matches_case_insensitively(self):
        defects = record_defects(_record(signatory="qa-inspector-14"), AUTHORISED)
        self.assertEqual(defects, [])

    def test_a_missing_evidence_reference_is_a_defect(self):
        defects = record_defects(_record(evidence_reference=None), AUTHORISED)
        self.assertIn("evidence-reference-missing", defects)

    def test_a_failed_outcome_without_a_disposition_is_a_defect(self):
        defects = record_defects(_record(outcome="fail"), AUTHORISED)
        self.assertIn("failed-outcome-without-disposition", defects)

    def test_a_failed_outcome_with_a_disposition_is_sound(self):
        defects = record_defects(
            _record(outcome="fail", nonconformance_disposition="NCR-6070-11-scrap"),
            AUTHORISED)
        self.assertEqual(defects, [])

    def test_a_pending_outcome_is_flagged_as_still_open(self):
        defects = record_defects(_record(outcome="pending"), AUTHORISED)
        self.assertIn("outcome-still-open", defects)

    def test_defects_accumulate(self):
        defects = record_defects(
            _record(activity="", lot_code="", outcome=None, signatory="",
                    evidence_reference=""), AUTHORISED)
        self.assertEqual(len(defects), 5)

    def test_the_authorised_list_must_be_a_sequence(self):
        with self.assertRaises(ValueError):
            record_defects(_record(), "QA-Inspector-14")


class GroupingTests(unittest.TestCase):
    def test_records_group_under_the_activity_they_cover(self):
        grouped = group_records_by_activity(_programme()["records"])
        self.assertEqual(len(grouped["incoming-inspection"]), 1)

    def test_an_unrecognised_record_is_grouped_rather_than_dropped(self):
        grouped = group_records_by_activity([_record(activity="corridor-chat")])
        self.assertIn(None, grouped)

    def test_two_records_for_one_activity_group_together(self):
        records = [_record(), _record(record_id="IR-6070-004")]
        grouped = group_records_by_activity(records)
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
        missing = unrecorded_activities(
            programme["activities_performed"], programme["records"][:2])
        self.assertEqual(missing, ["destructive-physical-analysis"])

    def test_unrecorded_activities_come_back_in_audit_order(self):
        missing = unrecorded_activities(PERFORMED, [])
        indexes = [INSPECTION_ACTIVITIES.index(name) for name in missing]
        self.assertEqual(indexes, sorted(indexes))

    def test_a_defective_record_still_counts_as_a_record(self):
        programme = _programme()
        records = list(programme["records"])
        records[2] = _record(record_id="IR-6070-003",
                             activity="destructive-physical-analysis",
                             evidence_reference=None)
        missing = unrecorded_activities(programme["activities_performed"], records)
        self.assertEqual(missing, [])

    def test_a_defective_record_does_not_make_its_activity_sound(self):
        programme = _programme()
        records = list(programme["records"])
        records[2] = _record(record_id="IR-6070-003",
                             activity="destructive-physical-analysis",
                             evidence_reference=None)
        sound = sound_activities(programme["activities_performed"], records,
                                 AUTHORISED)
        self.assertNotIn("destructive-physical-analysis", sound)

    def test_one_sound_record_among_defective_ones_covers_the_activity(self):
        records = [_record(evidence_reference=None), _record(record_id="IR-B")]
        sound = sound_activities(["incoming-inspection"], records, AUTHORISED)
        self.assertEqual(sound, ["incoming-inspection"])

    def test_defective_records_are_listed_with_their_reference(self):
        findings = defective_records([_record(lot_code="")], AUTHORISED)
        self.assertEqual(findings[0]["record"], "IR-6070-001")

    def test_a_record_without_an_identifier_falls_back_to_its_position(self):
        findings = defective_records([_record(record_id=None, lot_code="")],
                                     AUTHORISED)
        self.assertEqual(findings[0]["record"], "record-0")

    def test_a_clean_record_set_reports_no_findings(self):
        self.assertEqual(defective_records(_programme()["records"], AUTHORISED), [])


class RetentionTests(unittest.TestCase):
    def test_a_long_retention_leaves_no_shortfall(self):
        self.assertAlmostEqual(retention_shortfall_years(12.0), 0.0, places=9)

    def test_retention_exactly_at_the_requirement_leaves_no_shortfall(self):
        self.assertAlmostEqual(
            retention_shortfall_years(RETENTION_REQUIREMENT_YEARS), 0.0, places=9)

    def test_a_short_retention_reports_the_gap(self):
        self.assertAlmostEqual(retention_shortfall_years(4.0), 6.0, places=9)

    def test_a_zero_retention_reports_the_whole_requirement(self):
        self.assertAlmostEqual(retention_shortfall_years(0.0),
                               RETENTION_REQUIREMENT_YEARS, places=9)

    def test_a_negative_retention_is_rejected(self):
        with self.assertRaises(ValueError):
            retention_shortfall_years(-1.0)

    def test_a_non_numeric_retention_is_rejected(self):
        with self.assertRaises(ValueError):
            retention_shortfall_years("12")


class CompletenessTests(unittest.TestCase):
    def test_a_fully_documented_programme_reads_one(self):
        programme = _programme()
        self.assertAlmostEqual(
            documentation_completeness(programme["activities_performed"],
                                       programme["records"], AUTHORISED),
            1.0, places=9)

    def test_an_undocumented_programme_reads_zero(self):
        self.assertAlmostEqual(
            documentation_completeness(PERFORMED, [], AUTHORISED), 0.0, places=9)

    def test_two_of_three_activities_read_two_thirds(self):
        programme = _programme()
        value = documentation_completeness(programme["activities_performed"],
                                           programme["records"][:2], AUTHORISED)
        self.assertAlmostEqual(value, 2.0 / 3.0, places=9)

    def test_an_empty_performed_list_is_rejected(self):
        with self.assertRaises(ValueError):
            documentation_completeness([], [], AUTHORISED)

    def test_the_tolerance_is_the_documented_size(self):
        self.assertAlmostEqual(BOUND_TOLERANCE, 1e-9, places=12)


class DispositionTests(unittest.TestCase):
    def test_a_retention_shortfall_overrides_a_clean_record_set(self):
        self.assertEqual(documentation_disposition([], [], 6.0),
                         "documentation-not-auditable")

    def test_an_unrecorded_activity_reads_as_incomplete(self):
        self.assertEqual(
            documentation_disposition(["destructive-physical-analysis"], [], 0.0),
            "documentation-incomplete")

    def test_a_defective_record_reads_as_incomplete(self):
        self.assertEqual(
            documentation_disposition([], [{"record": "IR-1", "defects": ["x"]}], 0.0),
            "documentation-incomplete")

    def test_a_clean_retained_record_set_reads_as_complete(self):
        self.assertEqual(documentation_disposition([], [], 0.0),
                         "documentation-complete")

    def test_the_unrecorded_list_must_be_a_sequence(self):
        with self.assertRaises(ValueError):
            documentation_disposition("incoming-inspection", [], 0.0)


class CompilationTests(unittest.TestCase):
    def test_a_sound_programme_is_audit_ready(self):
        result = compile_class_1_inspection_records(_programme())
        self.assertTrue(result["audit_ready"])
        self.assertEqual(result["disposition"], "documentation-complete")

    def test_a_missing_record_is_named_and_blocks_the_audit(self):
        programme = _programme()
        programme["records"] = programme["records"][:2]
        result = compile_class_1_inspection_records(programme)
        self.assertEqual(result["unrecorded_activities"],
                         ["destructive-physical-analysis"])
        self.assertFalse(result["audit_ready"])

    def test_a_defective_record_is_reported_with_its_defects(self):
        programme = _programme()
        programme["records"][0] = _record(lot_code="")
        result = compile_class_1_inspection_records(programme)
        self.assertIn("lot-identity-not-traceable",
                      result["defective_records"][0]["defects"])

    def test_a_short_retention_makes_the_set_unauditable(self):
        result = compile_class_1_inspection_records(_programme(retention_years=3.0))
        self.assertEqual(result["disposition"], "documentation-not-auditable")
        self.assertAlmostEqual(result["retention_shortfall_years"], 7.0, places=9)

    def test_completeness_is_reported(self):
        programme = _programme()
        programme["records"] = programme["records"][:2]
        result = compile_class_1_inspection_records(programme)
        self.assertAlmostEqual(result["documentation_completeness"], 2.0 / 3.0,
                               places=9)

    def test_the_performed_activities_come_back_in_audit_order(self):
        result = compile_class_1_inspection_records(_programme())
        indexes = [INSPECTION_ACTIVITIES.index(name)
                   for name in result["activities_performed"]]
        self.assertEqual(indexes, sorted(indexes))

    def test_a_programme_with_no_performed_activity_is_rejected(self):
        with self.assertRaises(ValueError):
            compile_class_1_inspection_records(_programme(activities_performed=[]))

    def test_the_programme_must_be_a_mapping(self):
        with self.assertRaises(ValueError):
            compile_class_1_inspection_records([_programme()])


if __name__ == "__main__":
    unittest.main(verbosity=1)
