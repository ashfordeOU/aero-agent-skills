"""Contract tests for the clause 5.3.4 pre-seal inspection logic.

The cases follow the workflow one step at a time: applicability by package
family, the day parsing the ordering questions rest on, the seal-day boundary
that makes a late record void, the notice lead time, the delegation approval
this class allows, the graded defect gate and the disposition that stops a lot
in front of the seal. Each limit is exercised on both sides.
"""

import unittest

from q6013_class_2_precap_inspection_logic import (
    CAVITY_FAMILIES,
    CRITICAL_ACCEPT_NUMBER,
    CUSTOMER_AGENTS,
    DELEGATION_AGENTS,
    SOLID_FAMILIES,
    assess_precap_inspection,
    defect_record,
    delegation_record,
    notice_record,
    package_needs_precap,
    parse_day,
    timing_record,
)


def _spec(**overrides):
    spec = {
        "package_family": "hermetic-cavity",
        "lot_size": 300,
        "sample_size": 20,
        "defects": {"critical": 0, "major": 0, "minor": 1},
        "accept_numbers": {"major": 1, "minor": 2},
        "inspection": {"agent": "customer-representative"},
        "notice_date": "2026-03-02",
        "inspection_date": "2026-03-18",
        "seal_date": "2026-03-20",
        "agreed_lead_days": 10,
    }
    spec.update(overrides)
    return spec


class ApplicabilityTests(unittest.TestCase):
    def test_cavity_family_needs_the_inspection(self):
        self.assertTrue(package_needs_precap("hermetic-cavity"))

    def test_solid_family_does_not(self):
        self.assertFalse(package_needs_precap("solid-encapsulated"))

    def test_family_name_normalised(self):
        self.assertTrue(package_needs_precap("Metal_Can"))

    def test_unknown_family_rejected(self):
        with self.assertRaises(ValueError):
            package_needs_precap("wafer-on-tape")

    def test_family_sets_do_not_overlap(self):
        self.assertEqual(set(CAVITY_FAMILIES) & set(SOLID_FAMILIES), set())


class DayTests(unittest.TestCase):
    def test_parses_a_well_formed_day(self):
        self.assertEqual(parse_day("seal_date", "2026-03-20"), (2026, 3, 20))

    def test_month_thirteen_rejected(self):
        with self.assertRaises(ValueError):
            parse_day("seal_date", "2026-13-01")

    def test_day_past_month_end_rejected(self):
        with self.assertRaises(ValueError):
            parse_day("seal_date", "2026-04-31")

    def test_short_form_rejected(self):
        with self.assertRaises(ValueError):
            parse_day("seal_date", "2026-3-2")

    def test_non_string_rejected(self):
        with self.assertRaises(ValueError):
            parse_day("seal_date", 20260320)


class TimingTests(unittest.TestCase):
    def test_inspection_before_seal_stands(self):
        record = timing_record("2026-03-18", "2026-03-20")
        self.assertEqual(record["days_before_seal"], 2)
        self.assertTrue(record["before_seal"])
        self.assertFalse(record["void"])

    def test_inspection_on_the_seal_day_is_void(self):
        record = timing_record("2026-03-20", "2026-03-20")
        self.assertTrue(record["void"])

    def test_inspection_after_the_seal_is_void(self):
        record = timing_record("2026-03-21", "2026-03-20")
        self.assertTrue(record["void"])
        self.assertEqual(record["days_before_seal"], -1)

    def test_day_difference_spans_a_month_end(self):
        record = timing_record("2026-02-26", "2026-03-02")
        self.assertEqual(record["days_before_seal"], 4)

    def test_day_difference_spans_a_leap_day(self):
        record = timing_record("2024-02-28", "2024-03-01")
        self.assertEqual(record["days_before_seal"], 2)


class NoticeTests(unittest.TestCase):
    def test_ample_notice_is_adequate(self):
        record = notice_record("2026-03-02", "2026-03-20", 10)
        self.assertEqual(record["actual_lead_days"], 18)
        self.assertTrue(record["adequate"])

    def test_notice_exactly_on_the_agreed_lead_is_adequate(self):
        record = notice_record("2026-03-10", "2026-03-20", 10)
        self.assertEqual(record["actual_lead_days"], 10)
        self.assertTrue(record["adequate"])

    def test_short_notice_is_a_finding(self):
        record = notice_record("2026-03-18", "2026-03-20", 10)
        self.assertFalse(record["adequate"])

    def test_negative_agreed_lead_rejected(self):
        with self.assertRaises(ValueError):
            notice_record("2026-03-10", "2026-03-20", -1)


class DelegationTests(unittest.TestCase):
    def test_customer_needs_no_approval_reference(self):
        record = delegation_record({"agent": "customer"})
        self.assertFalse(record["delegated"])
        self.assertTrue(record["accepted"])

    def test_delegate_with_reference_and_issue_accepted(self):
        record = delegation_record(
            {
                "agent": "manufacturer-quality",
                "approval_reference": "PA-PROC-4412",
                "approval_issue": "C",
            }
        )
        self.assertTrue(record["delegated"])
        self.assertTrue(record["accepted"])

    def test_delegate_without_issue_refused(self):
        record = delegation_record(
            {"agent": "third-party-inspection-agency", "approval_reference": "PA-PROC-4412"}
        )
        self.assertFalse(record["accepted"])

    def test_delegate_with_blank_reference_refused(self):
        record = delegation_record(
            {"agent": "manufacturer-quality", "approval_reference": "   ", "approval_issue": "C"}
        )
        self.assertFalse(record["accepted"])

    def test_unknown_agent_rejected(self):
        with self.assertRaises(ValueError):
            delegation_record({"agent": "a-passing-colleague"})

    def test_missing_agent_rejected(self):
        with self.assertRaises(ValueError):
            delegation_record({})

    def test_agent_sets_do_not_overlap(self):
        self.assertEqual(set(CUSTOMER_AGENTS) & set(DELEGATION_AGENTS), set())


class DefectTests(unittest.TestCase):
    def test_clean_sample_accepts(self):
        record = defect_record(300, 20, {"critical": 0, "major": 0, "minor": 0})
        self.assertTrue(record["accepted"])
        self.assertEqual(record["rejecting_grades"], [])

    def test_one_critical_defect_rejects(self):
        record = defect_record(
            300, 20, {"critical": 1, "major": 0, "minor": 0}, {"major": 5, "minor": 5}
        )
        self.assertFalse(record["accepted"])
        self.assertEqual(record["rejecting_grades"], ["critical"])

    def test_critical_accept_number_cannot_be_raised(self):
        with self.assertRaises(ValueError):
            defect_record(300, 20, {"critical": 0, "major": 0, "minor": 0}, {"critical": 1})

    def test_critical_accept_number_is_zero(self):
        self.assertEqual(CRITICAL_ACCEPT_NUMBER, 0)

    def test_major_on_its_accept_number_accepts(self):
        record = defect_record(300, 20, {"critical": 0, "major": 2, "minor": 0}, {"major": 2})
        self.assertTrue(record["accepted"])

    def test_major_over_its_accept_number_rejects(self):
        record = defect_record(300, 20, {"critical": 0, "major": 3, "minor": 0}, {"major": 2})
        self.assertFalse(record["accepted"])

    def test_every_rejecting_grade_named_not_only_the_first(self):
        record = defect_record(300, 20, {"critical": 1, "major": 4, "minor": 4}, {"major": 1, "minor": 1})
        self.assertEqual(record["rejecting_grades"], ["critical", "major", "minor"])

    def test_percent_of_sample_is_exact_for_a_round_ratio(self):
        record = defect_record(300, 20, {"critical": 0, "major": 1, "minor": 0}, {"major": 2})
        self.assertAlmostEqual(record["grades"]["major"]["percent_of_sample"], 5.0, places=9)

    def test_sample_larger_than_lot_rejected(self):
        with self.assertRaises(ValueError):
            defect_record(10, 11, {"critical": 0, "major": 0, "minor": 0})

    def test_defects_exceeding_the_sample_rejected(self):
        with self.assertRaises(ValueError):
            defect_record(300, 5, {"critical": 2, "major": 2, "minor": 2})

    def test_missing_defect_grade_rejected(self):
        with self.assertRaises(ValueError):
            defect_record(300, 20, {"critical": 0, "major": 0})


class AssessmentTests(unittest.TestCase):
    def test_clean_inspection_releases_for_seal(self):
        result = assess_precap_inspection(_spec())
        self.assertTrue(result["accepted"])
        self.assertEqual(result["disposition"], "release-for-seal")
        self.assertEqual(result["findings"], [])

    def test_solid_package_is_not_applicable_rather_than_waived(self):
        result = assess_precap_inspection({"package_family": "solid-encapsulated"})
        self.assertEqual(result["disposition"], "not-applicable-no-cavity")
        self.assertFalse(result["applicable"])
        self.assertTrue(any("not the same as a waiver" in f for f in result["findings"]))

    def test_inspection_after_the_seal_holds_the_lot(self):
        result = assess_precap_inspection(_spec(inspection_date="2026-03-22"))
        self.assertFalse(result["accepted"])
        self.assertEqual(result["disposition"], "hold-before-seal")
        self.assertTrue(any("void rather than late" in f for f in result["findings"]))

    def test_short_notice_holds_the_lot(self):
        result = assess_precap_inspection(_spec(notice_date="2026-03-19"))
        self.assertFalse(result["accepted"])
        self.assertTrue(any("could not have arranged to attend" in f for f in result["findings"]))

    def test_unapproved_delegation_holds_the_lot(self):
        result = assess_precap_inspection(_spec(inspection={"agent": "manufacturer-quality"}))
        self.assertFalse(result["accepted"])
        self.assertTrue(any("no approved procedure reference" in f for f in result["findings"]))

    def test_approved_delegation_is_allowed_at_this_class(self):
        result = assess_precap_inspection(
            _spec(
                inspection={
                    "agent": "manufacturer-quality",
                    "approval_reference": "PA-PROC-4412",
                    "approval_issue": "C",
                }
            )
        )
        self.assertTrue(result["accepted"])

    def test_critical_defect_holds_the_lot(self):
        result = assess_precap_inspection(_spec(defects={"critical": 1, "major": 0, "minor": 0}))
        self.assertFalse(result["accepted"])
        self.assertTrue(any(f.startswith("critical defects") for f in result["findings"]))

    def test_every_failing_check_reported_together(self):
        result = assess_precap_inspection(
            _spec(
                inspection_date="2026-03-25",
                notice_date="2026-03-19",
                inspection={"agent": "third-party-inspection-agency"},
                defects={"critical": 1, "major": 0, "minor": 0},
            )
        )
        self.assertEqual(len(result["findings"]), 4)

    def test_missing_required_key_rejected(self):
        spec = _spec()
        del spec["seal_date"]
        with self.assertRaises(ValueError):
            assess_precap_inspection(spec)

    def test_non_mapping_spec_rejected(self):
        with self.assertRaises(ValueError):
            assess_precap_inspection(["not", "a", "mapping"])


if __name__ == "__main__":
    unittest.main()
