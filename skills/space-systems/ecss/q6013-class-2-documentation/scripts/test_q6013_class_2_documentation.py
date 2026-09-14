"""Contract tests for the clause 5.7 class 2 commercial parts documentation.

Every workflow step the SKILL.md sets out is exercised here, together with the
stop conditions the gate 3 contract reviews: a refused retention policy, a
record with no issue or no approving authority, a mandatory type the package
never produced, a supplier-held record with no access undertaking, a credited
completeness judged at its floor under a named tolerance, a retention below the
whole-year floor, and a record expiring before the horizon the project has to
reach.
"""

import datetime
import unittest

from q6013_class_2_documentation_logic import (
    COMMERCIAL_PARTS_CONTROL_PLAN,
    DECLARED_COMMERCIAL_PARTS_LIST,
    DEFAULT_DOCUMENTATION_POLICY,
    DERATING_AND_RADIATION_JUSTIFICATION,
    MANDATORY_RECORD_TYPES,
    NONCONFORMANCE_AND_ALERT_LOG,
    PACKAGE_COVERAGE_SHORTFALL,
    PACKAGE_MEETS_CLASS_TWO,
    PACKAGE_NOT_ESTABLISHED,
    PROCUREMENT_AND_SOURCE_RECORD,
    PROJECT_CUSTODY,
    RECORD_CONTROL_NOT_DEMONSTRATED,
    RETENTION_NOT_SUFFICIENT,
    SCREENING_AND_LOT_ACCEPTANCE_DATA,
    SUPPLIER_CUSTODY,
    absent_record_types,
    assess_documentation_package,
    package_completeness,
    record_credit,
    records_below_retention_floor,
    records_expiring_before_horizon,
    retention_end_date,
    uncontrolled_records,
    unreachable_record_types,
    validate_activity,
    validate_documentation_policy,
    validate_record,
    validate_records,
)

HORIZON = "2041-06-30"


def _policy(**overrides):
    policy = dict(DEFAULT_DOCUMENTATION_POLICY)
    policy.update(overrides)
    return policy


def _record(record_type, **overrides):
    record = {
        "type": record_type,
        "identifier": "REC-%s" % record_type[:6].upper(),
        "issue": "2",
        "approving_authority": "product-assurance-manager",
        "date": "2026-03-11",
        "custody": PROJECT_CUSTODY,
        "access_undertaking": False,
        "retention_years": 16,
    }
    record.update(overrides)
    return record


def _records(**per_type):
    entries = []
    for record_type in MANDATORY_RECORD_TYPES:
        entries.append(_record(record_type, **per_type.get(record_type, {})))
    return entries


def _activity(**overrides):
    activity = {
        "part_number": "CDS-1042-KJ",
        "project": "intermediate-class commercial parts control",
        "retention_horizon": HORIZON,
    }
    activity.update(overrides)
    return activity


def _case(**overrides):
    case = {"activity": _activity(), "records": _records()}
    case.update(overrides)
    return case


class PolicyTests(unittest.TestCase):
    def test_default_policy_validates(self):
        self.assertIs(
            validate_documentation_policy(DEFAULT_DOCUMENTATION_POLICY),
            DEFAULT_DOCUMENTATION_POLICY,
        )

    def test_completeness_floor_above_one_refused(self):
        with self.assertRaises(ValueError):
            validate_documentation_policy(_policy(min_completeness=1.2))

    def test_supplier_credit_of_one_refused(self):
        with self.assertRaises(ValueError):
            validate_documentation_policy(_policy(supplier_held_credit=1.0))

    def test_negative_supplier_credit_refused(self):
        with self.assertRaises(ValueError):
            validate_documentation_policy(_policy(supplier_held_credit=-0.25))

    def test_fractional_retention_floor_refused(self):
        with self.assertRaises(ValueError):
            validate_documentation_policy(_policy(min_retention_years=10.5))

    def test_non_mapping_policy_refused(self):
        with self.assertRaises(ValueError):
            validate_documentation_policy(["min_completeness"])


class ActivityTests(unittest.TestCase):
    def test_a_good_activity_reads_back_its_horizon(self):
        record = validate_activity(_activity())
        self.assertEqual(record["retention_horizon"], datetime.date(2041, 6, 30))

    def test_blank_part_number_refused(self):
        with self.assertRaises(ValueError):
            validate_activity(_activity(part_number="  "))

    def test_an_impossible_horizon_date_refused(self):
        with self.assertRaises(ValueError):
            validate_activity(_activity(retention_horizon="2041-02-30"))

    def test_a_non_iso_horizon_refused(self):
        with self.assertRaises(ValueError):
            validate_activity(_activity(retention_horizon="30 June 2041"))


class RecordValidationTests(unittest.TestCase):
    def test_a_good_record_reads_back_its_custody(self):
        entry = validate_record(_record(COMMERCIAL_PARTS_CONTROL_PLAN))
        self.assertEqual(entry["custody"], PROJECT_CUSTODY)
        self.assertEqual(entry["retention_years"], 16)

    def test_an_unrecognised_record_type_refused(self):
        with self.assertRaises(ValueError):
            validate_record(_record(COMMERCIAL_PARTS_CONTROL_PLAN, type="parts-vibes-log"))

    def test_an_unrecognised_custody_refused(self):
        with self.assertRaises(ValueError):
            validate_record(
                _record(COMMERCIAL_PARTS_CONTROL_PLAN, custody="somewhere-in-a-drive")
            )

    def test_a_negative_retention_refused(self):
        with self.assertRaises(ValueError):
            validate_record(
                _record(COMMERCIAL_PARTS_CONTROL_PLAN, retention_years=-3)
            )

    def test_a_type_declared_twice_refused(self):
        with self.assertRaises(ValueError):
            validate_records(
                [
                    _record(COMMERCIAL_PARTS_CONTROL_PLAN),
                    _record(COMMERCIAL_PARTS_CONTROL_PLAN),
                ]
            )

    def test_an_empty_package_refused(self):
        with self.assertRaises(ValueError):
            validate_records([])

    def test_a_record_with_no_issue_is_uncontrolled(self):
        records = _records(**{NONCONFORMANCE_AND_ALERT_LOG: {"issue": ""}})
        self.assertEqual(uncontrolled_records(records), (NONCONFORMANCE_AND_ALERT_LOG,))

    def test_a_record_with_no_approving_authority_is_uncontrolled(self):
        records = _records(
            **{PROCUREMENT_AND_SOURCE_RECORD: {"approving_authority": "   "}}
        )
        self.assertEqual(uncontrolled_records(records), (PROCUREMENT_AND_SOURCE_RECORD,))


class CustodyCreditTests(unittest.TestCase):
    def test_a_project_held_record_counts_in_full(self):
        self.assertAlmostEqual(
            record_credit(_record(COMMERCIAL_PARTS_CONTROL_PLAN)), 1.0, places=9
        )

    def test_a_supplier_held_record_with_access_counts_at_the_fraction(self):
        record = _record(
            SCREENING_AND_LOT_ACCEPTANCE_DATA,
            custody=SUPPLIER_CUSTODY,
            access_undertaking=True,
        )
        self.assertAlmostEqual(record_credit(record), 0.5, places=9)

    def test_a_supplier_held_record_with_no_access_counts_as_nothing(self):
        record = _record(
            SCREENING_AND_LOT_ACCEPTANCE_DATA,
            custody=SUPPLIER_CUSTODY,
            access_undertaking=False,
        )
        self.assertAlmostEqual(record_credit(record), 0.0, places=9)

    def test_the_undertaking_requirement_may_be_waived_by_policy(self):
        record = _record(
            SCREENING_AND_LOT_ACCEPTANCE_DATA,
            custody=SUPPLIER_CUSTODY,
            access_undertaking=False,
        )
        self.assertAlmostEqual(
            record_credit(record, _policy(require_access_undertaking=False)),
            0.5,
            places=9,
        )

    def test_a_complete_project_held_package_is_whole(self):
        self.assertAlmostEqual(package_completeness(_records()), 1.0, places=9)
        self.assertEqual(absent_record_types(_records()), ())
        self.assertEqual(unreachable_record_types(_records()), ())

    def test_one_supplier_held_type_lowers_the_credited_completeness(self):
        records = _records(
            **{
                SCREENING_AND_LOT_ACCEPTANCE_DATA: {
                    "custody": SUPPLIER_CUSTODY,
                    "access_undertaking": True,
                }
            }
        )
        self.assertAlmostEqual(
            package_completeness(records),
            (len(MANDATORY_RECORD_TYPES) - 0.5) / len(MANDATORY_RECORD_TYPES),
            places=9,
        )

    def test_a_dropped_type_is_named_and_lowers_the_completeness(self):
        records = [
            record
            for record in _records()
            if record["type"] != DERATING_AND_RADIATION_JUSTIFICATION
        ]
        self.assertEqual(
            absent_record_types(records), (DERATING_AND_RADIATION_JUSTIFICATION,)
        )
        self.assertAlmostEqual(
            package_completeness(records),
            (len(MANDATORY_RECORD_TYPES) - 1) / len(MANDATORY_RECORD_TYPES),
            places=9,
        )

    def test_an_unreachable_supplier_record_is_named(self):
        records = _records(
            **{
                NONCONFORMANCE_AND_ALERT_LOG: {
                    "custody": SUPPLIER_CUSTODY,
                    "access_undertaking": False,
                }
            }
        )
        self.assertEqual(
            unreachable_record_types(records), (NONCONFORMANCE_AND_ALERT_LOG,)
        )


class RetentionTests(unittest.TestCase):
    def test_retention_runs_in_whole_calendar_years(self):
        record = _record(
            COMMERCIAL_PARTS_CONTROL_PLAN, date="2026-03-11", retention_years=15
        )
        self.assertEqual(retention_end_date(record), datetime.date(2041, 3, 11))

    def test_a_leap_day_record_holds_to_the_twenty_eighth(self):
        record = _record(
            COMMERCIAL_PARTS_CONTROL_PLAN, date="2024-02-29", retention_years=17
        )
        self.assertEqual(retention_end_date(record), datetime.date(2041, 2, 28))

    def test_a_zero_retention_ends_on_its_own_date(self):
        record = _record(
            COMMERCIAL_PARTS_CONTROL_PLAN, date="2026-03-11", retention_years=0
        )
        self.assertEqual(retention_end_date(record), datetime.date(2026, 3, 11))

    def test_a_short_retention_is_named_against_the_floor(self):
        records = _records(**{DECLARED_COMMERCIAL_PARTS_LIST: {"retention_years": 4}})
        self.assertEqual(
            records_below_retention_floor(records), (DECLARED_COMMERCIAL_PARTS_LIST,)
        )

    def test_a_long_retention_from_an_early_record_can_still_expire(self):
        records = _records(
            **{
                PROCUREMENT_AND_SOURCE_RECORD: {
                    "date": "2019-01-04",
                    "retention_years": 12,
                }
            }
        )
        self.assertEqual(records_below_retention_floor(records), ())
        self.assertEqual(
            records_expiring_before_horizon(records, HORIZON),
            (PROCUREMENT_AND_SOURCE_RECORD,),
        )

    def test_a_retention_landing_on_the_horizon_reaches_it(self):
        records = _records(
            **{
                PROCUREMENT_AND_SOURCE_RECORD: {
                    "date": "2026-06-30",
                    "retention_years": 15,
                }
            }
        )
        self.assertEqual(records_expiring_before_horizon(records, HORIZON), ())


class AssessmentTests(unittest.TestCase):
    def test_a_sound_package_meets_the_class(self):
        result = assess_documentation_package(_case())
        self.assertEqual(result["verdict"], PACKAGE_MEETS_CLASS_TWO)
        self.assertAlmostEqual(result["package_completeness"], 1.0, places=9)
        self.assertEqual(result["advisories"], [])

    def test_an_absent_package_is_not_established(self):
        case = _case()
        del case["records"]
        result = assess_documentation_package(case)
        self.assertEqual(result["verdict"], PACKAGE_NOT_ESTABLISHED)
        self.assertTrue(result["findings"])

    def test_an_uncontrolled_record_closes_before_any_counting(self):
        records = _records(**{COMMERCIAL_PARTS_CONTROL_PLAN: {"identifier": ""}})
        result = assess_documentation_package(_case(records=records))
        self.assertEqual(result["verdict"], RECORD_CONTROL_NOT_DEMONSTRATED)
        self.assertIsNone(result["package_completeness"])

    def test_one_supplier_held_type_still_clears_the_floor(self):
        records = _records(
            **{
                SCREENING_AND_LOT_ACCEPTANCE_DATA: {
                    "custody": SUPPLIER_CUSTODY,
                    "access_undertaking": True,
                }
            }
        )
        result = assess_documentation_package(_case(records=records))
        self.assertEqual(result["verdict"], PACKAGE_MEETS_CLASS_TWO)
        self.assertEqual(len(result["advisories"]), 1)

    def test_two_supplier_held_types_fall_below_the_floor(self):
        records = _records(
            **{
                SCREENING_AND_LOT_ACCEPTANCE_DATA: {
                    "custody": SUPPLIER_CUSTODY,
                    "access_undertaking": True,
                },
                PROCUREMENT_AND_SOURCE_RECORD: {
                    "custody": SUPPLIER_CUSTODY,
                    "access_undertaking": True,
                },
            }
        )
        result = assess_documentation_package(_case(records=records))
        self.assertEqual(result["verdict"], PACKAGE_COVERAGE_SHORTFALL)

    def test_a_package_exactly_on_its_completeness_floor_passes(self):
        records = _records(
            **{
                SCREENING_AND_LOT_ACCEPTANCE_DATA: {
                    "custody": SUPPLIER_CUSTODY,
                    "access_undertaking": True,
                }
            }
        )
        floor = (len(MANDATORY_RECORD_TYPES) - 0.5) / len(MANDATORY_RECORD_TYPES)
        result = assess_documentation_package(
            _case(records=records), _policy(min_completeness=floor)
        )
        self.assertEqual(result["verdict"], PACKAGE_MEETS_CLASS_TWO)
        self.assertAlmostEqual(result["package_completeness"], floor, places=9)

    def test_every_absent_type_is_named_not_only_the_first(self):
        records = [
            record
            for record in _records()
            if record["type"]
            not in (DERATING_AND_RADIATION_JUSTIFICATION, NONCONFORMANCE_AND_ALERT_LOG)
        ]
        result = assess_documentation_package(_case(records=records))
        self.assertEqual(result["verdict"], PACKAGE_COVERAGE_SHORTFALL)
        self.assertEqual(len(result["absent_record_types"]), 2)

    def test_an_unreachable_supplier_record_counts_as_absent(self):
        records = _records(
            **{
                DERATING_AND_RADIATION_JUSTIFICATION: {
                    "custody": SUPPLIER_CUSTODY,
                    "access_undertaking": False,
                }
            }
        )
        result = assess_documentation_package(_case(records=records))
        self.assertEqual(result["verdict"], PACKAGE_COVERAGE_SHORTFALL)
        self.assertEqual(
            result["unreachable_record_types"], (DERATING_AND_RADIATION_JUSTIFICATION,)
        )

    def test_a_short_retention_closes_the_assessment(self):
        records = _records(**{NONCONFORMANCE_AND_ALERT_LOG: {"retention_years": 3}})
        result = assess_documentation_package(_case(records=records))
        self.assertEqual(result["verdict"], RETENTION_NOT_SUFFICIENT)
        self.assertEqual(
            result["records_below_retention_floor"], (NONCONFORMANCE_AND_ALERT_LOG,)
        )

    def test_a_retention_and_a_horizon_finding_are_both_kept(self):
        records = _records(
            **{
                NONCONFORMANCE_AND_ALERT_LOG: {
                    "date": "2020-05-02",
                    "retention_years": 3,
                }
            }
        )
        result = assess_documentation_package(_case(records=records))
        self.assertEqual(result["verdict"], RETENTION_NOT_SUFFICIENT)
        self.assertEqual(len(result["findings"]), 2)

    def test_the_horizon_travels_from_the_activity_not_the_policy(self):
        records = _records(
            **{
                DECLARED_COMMERCIAL_PARTS_LIST: {
                    "date": "2026-03-11",
                    "retention_years": 11,
                }
            }
        )
        early = assess_documentation_package(
            _case(records=records, activity=_activity(retention_horizon="2036-01-01"))
        )
        self.assertEqual(early["verdict"], PACKAGE_MEETS_CLASS_TWO)
        late = assess_documentation_package(_case(records=records))
        self.assertEqual(late["verdict"], RETENTION_NOT_SUFFICIENT)

    def test_non_mapping_case_refused(self):
        with self.assertRaises(ValueError):
            assess_documentation_package(["records"])


if __name__ == "__main__":
    unittest.main()
