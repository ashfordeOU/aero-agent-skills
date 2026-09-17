#!/usr/bin/env python3
"""Contract test for Class 3 inspection outcome recording (offline)."""

import copy
import os
import sys
import unittest

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from q60_class_3_inspection_documentation_logic import (  # noqa: E402
    CLASS_3_INSPECTION_ACTIVITIES,
    DEFAULT_CLASS3_DOCUMENTATION_POLICY,
    OUTCOMES_NOT_RECONSTRUCTABLE,
    OUTCOMES_PARTIALLY_RECORDED,
    OUTCOMES_RECORDED,
    QUANTITY_FIELDS,
    RECORDING_AUTHORITIES,
    SELF_DECLARATION_AUTHORITY,
    acceptance_yield,
    compile_class3_inspection_outcomes,
    coverage_meets_floor,
    defective_records,
    group_records_by_activity,
    ordered_activities,
    outcome_coverage,
    reconciled_activities,
    reconciliation_residual,
    record_activity,
    record_defects,
    recording_disposition,
    required_retention_years,
    stated_quantities,
    unrecorded_activities,
    validate_documentation_policy,
)

MISSION_YEARS = 5.0


def _record(activity, **overrides):
    record = {
        "activity": activity,
        "lot_identity": "LOT-2026-114",
        "recording_authority": "project-quality-assurance",
        "evidence_reference": "EV-%s" % activity,
        "inspected": 100,
        "accepted": 100,
        "rejected": 0,
        "deferred": 0,
        "retention_years": 10.0,
    }
    record.update(overrides)
    return record


CLEAN_RECORDS = [_record(activity) for activity in CLASS_3_INSPECTION_ACTIVITIES]

CLEAN_CASE = {
    "performed_activities": list(CLASS_3_INSPECTION_ACTIVITIES),
    "records": CLEAN_RECORDS,
    "mission_duration_years": MISSION_YEARS,
}


def _case(**overrides):
    case = copy.deepcopy(CLEAN_CASE)
    case.update(overrides)
    return case


class PolicyTests(unittest.TestCase):
    def test_defaults_are_returned_when_no_policy_is_given(self):
        self.assertEqual(
            validate_documentation_policy(), DEFAULT_CLASS3_DOCUMENTATION_POLICY
        )

    def test_an_unknown_policy_key_is_rejected(self):
        with self.assertRaises(ValueError):
            validate_documentation_policy({"audit_window_days": 30})

    def test_a_coverage_floor_above_one_is_rejected(self):
        with self.assertRaises(ValueError):
            validate_documentation_policy({"outcome_coverage_floor": 1.5})

    def test_a_non_boolean_countersignature_flag_is_rejected(self):
        with self.assertRaises(ValueError):
            validate_documentation_policy(
                {"require_countersigned_self_declaration": "yes"}
            )

    def test_class_3_sets_a_lower_coverage_floor_than_full_coverage(self):
        self.assertLess(
            DEFAULT_CLASS3_DOCUMENTATION_POLICY["outcome_coverage_floor"], 1.0
        )


class ActivityTests(unittest.TestCase):
    def test_activities_come_back_in_audit_order(self):
        shuffled = list(reversed(CLASS_3_INSPECTION_ACTIVITIES))
        self.assertEqual(
            ordered_activities(shuffled), tuple(CLASS_3_INSPECTION_ACTIVITIES)
        )

    def test_a_repeated_activity_is_listed_once(self):
        self.assertEqual(
            ordered_activities(["incoming-inspection", "incoming-inspection"]),
            ("incoming-inspection",),
        )

    def test_an_unknown_activity_is_rejected(self):
        with self.assertRaises(ValueError):
            ordered_activities(["paint-inspection"])

    def test_an_empty_activity_list_is_rejected(self):
        with self.assertRaises(ValueError):
            ordered_activities([])

    def test_a_record_names_the_activity_it_covers(self):
        self.assertEqual(
            record_activity(_record("incoming-inspection")), "incoming-inspection"
        )

    def test_a_record_with_no_activity_is_rejected(self):
        with self.assertRaises(ValueError):
            record_activity({"lot_identity": "LOT-1"})

    def test_records_group_under_their_activity(self):
        grouped = group_records_by_activity(CLEAN_RECORDS)
        self.assertEqual(len(grouped), len(CLASS_3_INSPECTION_ACTIVITIES))


class QuantityTests(unittest.TestCase):
    def test_all_four_counts_are_read_back(self):
        quantities = stated_quantities(_record("incoming-inspection"))
        self.assertEqual(sorted(quantities), sorted(QUANTITY_FIELDS))

    def test_a_missing_count_is_rejected(self):
        record = _record("incoming-inspection")
        del record["rejected"]
        with self.assertRaises(ValueError):
            stated_quantities(record)

    def test_a_negative_count_is_rejected(self):
        with self.assertRaises(ValueError):
            stated_quantities(_record("incoming-inspection", rejected=-1))

    def test_a_boolean_count_is_rejected(self):
        with self.assertRaises(ValueError):
            stated_quantities(_record("incoming-inspection", deferred=True))

    def test_a_reconciling_record_has_a_zero_residual(self):
        self.assertEqual(reconciliation_residual(_record("incoming-inspection")), 0)

    def test_an_unaccounted_part_shows_in_the_residual(self):
        record = _record("incoming-inspection", accepted=98, rejected=1)
        self.assertEqual(reconciliation_residual(record), 1)


class RetentionTests(unittest.TestCase):
    def test_required_retention_outlives_the_mission(self):
        self.assertGreater(required_retention_years(MISSION_YEARS), MISSION_YEARS)

    def test_the_margin_is_policy_driven(self):
        self.assertAlmostEqual(
            required_retention_years(MISSION_YEARS, {"retention_margin_years": 4.0}),
            MISSION_YEARS + 4.0,
            places=9,
        )

    def test_a_zero_mission_duration_is_rejected(self):
        with self.assertRaises(ValueError):
            required_retention_years(0.0)

    def test_a_retention_exactly_on_its_requirement_is_no_defect(self):
        needed = required_retention_years(MISSION_YEARS)
        record = _record("incoming-inspection", retention_years=needed)
        self.assertEqual(record_defects(record, MISSION_YEARS), ())

    def test_a_short_retention_is_a_defect(self):
        record = _record("incoming-inspection", retention_years=1.0)
        self.assertIn("retention-below-required-period", record_defects(record, MISSION_YEARS))

    def test_a_record_with_no_retention_period_is_a_defect(self):
        record = _record("incoming-inspection")
        del record["retention_years"]
        self.assertIn("no-stated-retention-period", record_defects(record, MISSION_YEARS))

    def test_policy_can_drop_the_retention_requirement(self):
        record = _record("incoming-inspection", retention_years=1.0)
        self.assertEqual(
            record_defects(record, MISSION_YEARS, {"require_retention_period": False}),
            (),
        )


class RecordDefectTests(unittest.TestCase):
    def test_a_complete_record_carries_no_defect(self):
        self.assertEqual(record_defects(_record("incoming-inspection"), MISSION_YEARS), ())

    def test_a_record_with_no_lot_identity_is_defective(self):
        record = _record("incoming-inspection", lot_identity="  ")
        self.assertIn("no-traceable-lot-identity", record_defects(record, MISSION_YEARS))

    def test_an_outside_recording_authority_is_defective(self):
        record = _record("incoming-inspection", recording_authority="a visiting intern")
        self.assertIn(
            "unrecognised-recording-authority", record_defects(record, MISSION_YEARS)
        )

    def test_an_uncountersigned_self_declaration_is_defective(self):
        record = _record(
            "incoming-inspection", recording_authority=SELF_DECLARATION_AUTHORITY
        )
        self.assertIn(
            "self-declaration-without-countersignature",
            record_defects(record, MISSION_YEARS),
        )

    def test_a_countersigned_self_declaration_is_accepted(self):
        record = _record(
            "incoming-inspection",
            recording_authority=SELF_DECLARATION_AUTHORITY,
            countersigned_by="project-quality-assurance",
        )
        self.assertEqual(record_defects(record, MISSION_YEARS), ())

    def test_policy_can_drop_the_countersignature_requirement(self):
        record = _record(
            "incoming-inspection", recording_authority=SELF_DECLARATION_AUTHORITY
        )
        self.assertEqual(
            record_defects(
                record,
                MISSION_YEARS,
                {"require_countersigned_self_declaration": False},
            ),
            (),
        )

    def test_a_record_with_no_evidence_reference_is_defective(self):
        record = _record("incoming-inspection", evidence_reference=None)
        self.assertIn("no-evidence-reference", record_defects(record, MISSION_YEARS))

    def test_quantities_that_do_not_reconcile_are_defective(self):
        record = _record("incoming-inspection", accepted=90)
        self.assertIn(
            "quantities-do-not-reconcile", record_defects(record, MISSION_YEARS)
        )

    def test_a_rejection_without_a_nonconformance_reference_is_defective(self):
        record = _record("incoming-inspection", accepted=98, rejected=2)
        self.assertIn(
            "rejected-quantity-without-nonconformance-reference",
            record_defects(record, MISSION_YEARS),
        )

    def test_a_referenced_rejection_is_accepted(self):
        record = _record(
            "incoming-inspection",
            accepted=98,
            rejected=2,
            nonconformance_reference="NCR-2026-07",
        )
        self.assertEqual(record_defects(record, MISSION_YEARS), ())

    def test_a_deferred_quantity_left_open_is_defective(self):
        record = _record("incoming-inspection", accepted=97, deferred=3)
        self.assertIn(
            "deferred-quantity-left-open", record_defects(record, MISSION_YEARS)
        )

    def test_a_closed_deferral_is_accepted(self):
        record = _record(
            "incoming-inspection",
            accepted=97,
            deferred=3,
            deferral_closure_reference="DEF-2026-02",
        )
        self.assertEqual(record_defects(record, MISSION_YEARS), ())

    def test_every_catalogued_authority_is_recognised(self):
        for authority in RECORDING_AUTHORITIES:
            record = _record(
                "incoming-inspection",
                recording_authority=authority,
                countersigned_by="project-quality-assurance",
            )
            self.assertNotIn(
                "unrecognised-recording-authority",
                record_defects(record, MISSION_YEARS),
            )

    def test_defective_records_report_their_index_and_activity(self):
        records = list(CLEAN_RECORDS)
        records[1] = _record(records[1]["activity"], lot_identity=None)
        found = defective_records(records, MISSION_YEARS)
        self.assertEqual(found[0]["index"], 1)
        self.assertEqual(found[0]["activity"], records[1]["activity"])


class CoverageTests(unittest.TestCase):
    def test_a_full_clean_set_covers_every_activity(self):
        self.assertAlmostEqual(
            outcome_coverage(
                CLASS_3_INSPECTION_ACTIVITIES, CLEAN_RECORDS, MISSION_YEARS
            ),
            1.0,
            places=9,
        )

    def test_a_defective_record_does_not_cover_its_activity(self):
        records = [_record(a) for a in CLASS_3_INSPECTION_ACTIVITIES]
        records[0] = _record(records[0]["activity"], evidence_reference=None)
        covered = reconciled_activities(
            CLASS_3_INSPECTION_ACTIVITIES, records, MISSION_YEARS
        )
        self.assertNotIn(CLASS_3_INSPECTION_ACTIVITIES[0], covered)

    def test_a_second_clean_record_rescues_a_defective_one(self):
        records = [_record(a) for a in CLASS_3_INSPECTION_ACTIVITIES]
        records.append(_record(CLASS_3_INSPECTION_ACTIVITIES[0], evidence_reference=None))
        self.assertAlmostEqual(
            outcome_coverage(
                CLASS_3_INSPECTION_ACTIVITIES, records, MISSION_YEARS
            ),
            1.0,
            places=9,
        )

    def test_an_activity_with_no_record_is_named(self):
        records = CLEAN_RECORDS[1:]
        self.assertEqual(
            unrecorded_activities(CLASS_3_INSPECTION_ACTIVITIES, records),
            (CLASS_3_INSPECTION_ACTIVITIES[0],),
        )

    def test_a_coverage_exactly_on_the_floor_meets_it(self):
        floor = DEFAULT_CLASS3_DOCUMENTATION_POLICY["outcome_coverage_floor"]
        self.assertTrue(coverage_meets_floor(floor))

    def test_a_coverage_below_the_floor_does_not_meet_it(self):
        floor = DEFAULT_CLASS3_DOCUMENTATION_POLICY["outcome_coverage_floor"]
        self.assertFalse(coverage_meets_floor(floor - 0.1))

    def test_yield_is_accepted_over_presented(self):
        records = [_record("incoming-inspection", accepted=90, rejected=10,
                           nonconformance_reference="NCR-1")]
        self.assertAlmostEqual(acceptance_yield(records), 0.9, places=9)

    def test_a_programme_that_presented_nothing_has_no_yield(self):
        records = [
            _record("incoming-inspection", inspected=0, accepted=0)
        ]
        with self.assertRaises(ValueError):
            acceptance_yield(records)


class DispositionTests(unittest.TestCase):
    def test_zero_coverage_is_not_reconstructable(self):
        self.assertEqual(
            recording_disposition(0.0, True), OUTCOMES_NOT_RECONSTRUCTABLE
        )

    def test_full_coverage_with_every_activity_recorded_is_recorded(self):
        self.assertEqual(recording_disposition(1.0, False), OUTCOMES_RECORDED)

    def test_an_unrecorded_activity_downgrades_a_passing_coverage(self):
        self.assertEqual(
            recording_disposition(1.0, True), OUTCOMES_PARTIALLY_RECORDED
        )

    def test_coverage_below_the_floor_is_partially_recorded(self):
        self.assertEqual(
            recording_disposition(0.4, False), OUTCOMES_PARTIALLY_RECORDED
        )


class CompileTests(unittest.TestCase):
    def test_the_reference_programme_records_its_outcomes(self):
        result = compile_class3_inspection_outcomes(CLEAN_CASE)
        self.assertEqual(result["disposition"], OUTCOMES_RECORDED)
        self.assertEqual(result["findings"], [])

    def test_a_missing_activity_record_is_a_finding(self):
        result = compile_class3_inspection_outcomes(_case(records=CLEAN_RECORDS[1:]))
        self.assertEqual(result["disposition"], OUTCOMES_PARTIALLY_RECORDED)
        self.assertIn(CLASS_3_INSPECTION_ACTIVITIES[0], result["unrecorded_activities"])

    def test_a_programme_with_no_usable_record_is_not_reconstructable(self):
        records = [
            _record(a, lot_identity=None, evidence_reference=None)
            for a in CLASS_3_INSPECTION_ACTIVITIES
        ]
        result = compile_class3_inspection_outcomes(_case(records=records))
        self.assertEqual(result["disposition"], OUTCOMES_NOT_RECONSTRUCTABLE)

    def test_a_low_yield_is_an_advisory_and_not_a_finding(self):
        records = [
            _record(a, accepted=70, rejected=30, nonconformance_reference="NCR-1")
            for a in CLASS_3_INSPECTION_ACTIVITIES
        ]
        result = compile_class3_inspection_outcomes(_case(records=records))
        self.assertEqual(result["disposition"], OUTCOMES_RECORDED)
        self.assertTrue(result["advisories"])

    def test_a_yield_exactly_on_the_advisory_floor_raises_nothing(self):
        floor = DEFAULT_CLASS3_DOCUMENTATION_POLICY["acceptance_yield_advisory_floor"]
        accepted = int(round(100 * floor))
        records = [
            _record(
                a,
                accepted=accepted,
                rejected=100 - accepted,
                nonconformance_reference="NCR-1",
            )
            for a in CLASS_3_INSPECTION_ACTIVITIES
        ]
        result = compile_class3_inspection_outcomes(_case(records=records))
        self.assertAlmostEqual(result["acceptance_yield"], floor, places=9)
        self.assertEqual(result["advisories"], [])

    def test_the_required_retention_is_reported(self):
        result = compile_class3_inspection_outcomes(CLEAN_CASE)
        self.assertAlmostEqual(
            result["required_retention_years"],
            required_retention_years(MISSION_YEARS),
            places=9,
        )

    def test_a_shorter_programme_can_still_be_recorded(self):
        subset = list(CLASS_3_INSPECTION_ACTIVITIES[:2])
        result = compile_class3_inspection_outcomes(
            _case(
                performed_activities=subset,
                records=[_record(a) for a in subset],
            )
        )
        self.assertEqual(result["disposition"], OUTCOMES_RECORDED)

    def test_a_case_missing_a_field_is_rejected(self):
        case = _case()
        del case["mission_duration_years"]
        with self.assertRaises(ValueError):
            compile_class3_inspection_outcomes(case)

    def test_a_non_mapping_case_is_rejected(self):
        with self.assertRaises(ValueError):
            compile_class3_inspection_outcomes(["records"])


if __name__ == "__main__":
    unittest.main()
