"""Contract tests for the clause 5.8.2 test-centre nonconformance logic."""

import unittest

from q2007_nc_control_logic import (
    APPROVAL_NEEDED,
    DISPOSITIONS,
    HOUR_TOLERANCE,
    REPORTING_DEADLINE_H,
    assess_campaign,
    assess_nonconformance,
    categorize_severity,
    disposition_authority,
    overstress_ratio,
    report_timeliness,
    reporting_deadline_h,
    retest_scope,
    validate_disposition,
)

BASE = {
    "id": "NCR-011",
    "detected_h": 10.0,
    "reported_h": 12.0,
    "disposition": "rework",
    "total_phases": 3,
    "affected_phases": [],
    "closed": True,
}


def nc(**overrides):
    out = dict(BASE)
    out.update(overrides)
    return out


class OverstressTests(unittest.TestCase):
    def test_ratio_is_the_quotient(self):
        self.assertAlmostEqual(overstress_ratio(12.0, 10.0), 1.2)

    def test_ratio_exactly_at_the_limit(self):
        self.assertAlmostEqual(overstress_ratio(10.0, 10.0), 1.0, places=9)

    def test_zero_limit_rejected(self):
        with self.assertRaises(ValueError):
            overstress_ratio(10.0, 0.0)

    def test_negative_applied_rejected(self):
        with self.assertRaises(ValueError):
            overstress_ratio(-1.0, 10.0)

    def test_non_numeric_applied_rejected(self):
        with self.assertRaises(ValueError):
            overstress_ratio("12", 10.0)


class SeverityTests(unittest.TestCase):
    def test_plain_anomaly_is_minor(self):
        self.assertEqual(categorize_severity(nc()), "minor")

    def test_safety_effect_is_major(self):
        self.assertEqual(categorize_severity(nc(safety_affected=True)), "major")

    def test_requirement_violation_is_major(self):
        self.assertEqual(categorize_severity(nc(requirement_violated=True)), "major")

    def test_level_past_the_limit_is_major(self):
        self.assertEqual(
            categorize_severity(nc(applied_level=11.0, limit_level=10.0)), "major"
        )

    def test_level_exactly_on_the_limit_is_not_overstress(self):
        self.assertEqual(
            categorize_severity(nc(applied_level=10.0, limit_level=10.0)), "minor"
        )

    def test_invalidated_conditions_are_major(self):
        self.assertEqual(
            categorize_severity(nc(conditions_invalidated=True, affected_phases=["soak"])),
            "major",
        )

    def test_non_boolean_flag_rejected(self):
        with self.assertRaises(ValueError):
            categorize_severity(nc(safety_affected="yes"))

    def test_non_mapping_rejected(self):
        with self.assertRaises(ValueError):
            categorize_severity(["NCR-011"])


class DeadlineAndAuthorityTests(unittest.TestCase):
    def test_major_deadline_is_the_shorter_one(self):
        self.assertAlmostEqual(
            reporting_deadline_h("major"), REPORTING_DEADLINE_H["major"]
        )
        self.assertLess(REPORTING_DEADLINE_H["major"], REPORTING_DEADLINE_H["minor"])

    def test_unknown_severity_rejected(self):
        with self.assertRaises(ValueError):
            reporting_deadline_h("catastrophic")

    def test_major_escalates_to_the_customer(self):
        self.assertIn("customer", disposition_authority("major"))

    def test_minor_stays_with_the_centre(self):
        self.assertIn("test centre", disposition_authority("minor"))

    def test_unknown_severity_has_no_authority(self):
        with self.assertRaises(ValueError):
            disposition_authority("moderate")


class TimelinessTests(unittest.TestCase):
    def test_prompt_report_is_timely(self):
        self.assertTrue(report_timeliness(10.0, 12.0, "major")["timely"])

    def test_report_exactly_on_the_deadline_is_timely(self):
        record = report_timeliness(0.0, REPORTING_DEADLINE_H["major"], "major")
        self.assertAlmostEqual(
            record["elapsed_h"], REPORTING_DEADLINE_H["major"], places=9
        )
        self.assertTrue(record["timely"])

    def test_late_report_is_not_timely(self):
        self.assertFalse(report_timeliness(0.0, 48.0, "major")["timely"])

    def test_the_same_delay_is_timely_for_a_minor_anomaly(self):
        self.assertTrue(report_timeliness(0.0, 48.0, "minor")["timely"])

    def test_report_before_detection_rejected(self):
        with self.assertRaises(ValueError):
            report_timeliness(12.0, 10.0, "minor")

    def test_negative_detection_hour_rejected(self):
        with self.assertRaises(ValueError):
            report_timeliness(-1.0, 10.0, "minor")

    def test_tolerance_is_representation_sized(self):
        self.assertAlmostEqual(HOUR_TOLERANCE, 1e-9, places=12)


class RetestScopeTests(unittest.TestCase):
    def test_no_retest_when_nothing_was_invalidated(self):
        self.assertEqual(retest_scope(nc()), "none")

    def test_overstress_forces_a_full_retest(self):
        self.assertEqual(
            retest_scope(nc(applied_level=13.0, limit_level=10.0)), "full"
        )

    def test_one_invalidated_phase_forces_a_partial_retest(self):
        self.assertEqual(
            retest_scope(nc(conditions_invalidated=True, affected_phases=["soak"])),
            "partial",
        )

    def test_every_phase_invalidated_forces_a_full_retest(self):
        self.assertEqual(
            retest_scope(
                nc(
                    conditions_invalidated=True,
                    affected_phases=["ramp", "soak", "recovery"],
                )
            ),
            "full",
        )

    def test_repeated_phase_names_collapse(self):
        self.assertEqual(
            retest_scope(
                nc(conditions_invalidated=True, affected_phases=["soak", "soak"])
            ),
            "partial",
        )

    def test_invalidated_conditions_with_no_named_phase_rejected(self):
        with self.assertRaises(ValueError):
            retest_scope(nc(conditions_invalidated=True))

    def test_more_affected_phases_than_the_run_has_rejected(self):
        with self.assertRaises(ValueError):
            retest_scope(
                nc(
                    total_phases=1,
                    conditions_invalidated=True,
                    affected_phases=["ramp", "soak"],
                )
            )

    def test_blank_phase_name_rejected(self):
        with self.assertRaises(ValueError):
            retest_scope(nc(conditions_invalidated=True, affected_phases=["  "]))


class DispositionTests(unittest.TestCase):
    def test_rework_of_a_minor_anomaly_is_acceptable(self):
        self.assertTrue(validate_disposition("minor", "rework")["acceptable"])

    def test_use_as_is_on_a_major_anomaly_needs_agreement(self):
        record = validate_disposition("major", "use-as-is", False)
        self.assertTrue(record["approval_required"])
        self.assertFalse(record["acceptable"])

    def test_use_as_is_on_a_major_anomaly_with_agreement_is_acceptable(self):
        self.assertTrue(validate_disposition("major", "use-as-is", True)["acceptable"])

    def test_use_as_is_on_a_minor_anomaly_needs_no_agreement(self):
        record = validate_disposition("minor", "use-as-is", False)
        self.assertFalse(record["approval_required"])
        self.assertTrue(record["acceptable"])

    def test_scrap_needs_no_agreement_even_when_major(self):
        self.assertFalse(
            validate_disposition("major", "scrap", False)["approval_required"]
        )

    def test_unknown_disposition_rejected(self):
        with self.assertRaises(ValueError):
            validate_disposition("minor", "ignore")

    def test_non_boolean_approval_rejected(self):
        with self.assertRaises(ValueError):
            validate_disposition("major", "repair", "yes")

    def test_repair_is_in_the_approval_set(self):
        self.assertIn("repair", APPROVAL_NEEDED)
        self.assertIn("repair", DISPOSITIONS)


class NonconformanceAssessmentTests(unittest.TestCase):
    def test_clean_minor_record_is_acceptable(self):
        record = assess_nonconformance(nc())
        self.assertTrue(record["acceptable"])
        self.assertEqual(record["severity"], "minor")

    def test_late_major_report_is_a_finding(self):
        record = assess_nonconformance(
            nc(safety_affected=True, detected_h=0.0, reported_h=72.0)
        )
        self.assertFalse(record["acceptable"])

    def test_owed_retest_not_dispositioned_is_a_finding(self):
        record = assess_nonconformance(
            nc(conditions_invalidated=True, affected_phases=["soak"])
        )
        self.assertEqual(record["retest_scope"], "partial")
        self.assertFalse(record["acceptable"])

    def test_owed_retest_performed_clears_the_finding(self):
        record = assess_nonconformance(
            nc(
                conditions_invalidated=True,
                affected_phases=["soak"],
                retest_performed=True,
                disposition="rework",
                customer_approved=True,
            )
        )
        self.assertTrue(record["acceptable"])

    def test_closed_with_findings_adds_a_finding(self):
        record = assess_nonconformance(
            nc(safety_affected=True, disposition="use-as-is", closed=True)
        )
        self.assertIn("closed with findings", " ".join(record["findings"]))

    def test_missing_key_rejected(self):
        bad = nc()
        del bad["disposition"]
        with self.assertRaises(ValueError):
            assess_nonconformance(bad)

    def test_blank_id_rejected(self):
        with self.assertRaises(ValueError):
            assess_nonconformance(nc(id="  "))


class CampaignTests(unittest.TestCase):
    def test_clean_campaign_may_close_out(self):
        result = assess_campaign([nc(), nc(id="NCR-012")])
        self.assertTrue(result["close_out_permitted"])
        self.assertEqual(result["minor_count"], 2)

    def test_open_record_blocks_close_out(self):
        result = assess_campaign([nc(closed=False)])
        self.assertFalse(result["close_out_permitted"])
        self.assertEqual(result["open_count"], 1)

    def test_major_and_minor_are_counted_apart(self):
        result = assess_campaign(
            [nc(), nc(id="NCR-013", safety_affected=True, customer_approved=True)]
        )
        self.assertEqual(result["major_count"], 1)
        self.assertEqual(result["minor_count"], 1)

    def test_late_reports_are_counted(self):
        result = assess_campaign(
            [nc(id="NCR-014", safety_affected=True, detected_h=0.0, reported_h=96.0)]
        )
        self.assertEqual(result["late_report_count"], 1)

    def test_duplicate_id_rejected(self):
        with self.assertRaises(ValueError):
            assess_campaign([nc(), nc()])

    def test_non_sequence_rejected(self):
        with self.assertRaises(ValueError):
            assess_campaign(nc())

    def test_empty_campaign_is_clean(self):
        result = assess_campaign([])
        self.assertTrue(result["close_out_permitted"])
        self.assertEqual(result["records"], [])


if __name__ == "__main__":
    unittest.main(verbosity=2)
