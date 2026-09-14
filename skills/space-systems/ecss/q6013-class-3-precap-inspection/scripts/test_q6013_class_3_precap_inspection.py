"""Contract tests for the clause 6.3.4 class 3 pre-seal inspection logic.

The cases follow the workflow one step at a time: the invocation that decides
whether the inspection was ever owed, applicability by package family, the day
parsing the ordering rests on, the seal-day boundary that voids a late record,
the sample floor, the remote evidence routes this class allows, the graded
findings and the disposition that stops a lot in front of the seal. Each limit
is exercised on both sides.
"""

import unittest

from q6013_class_3_precap_inspection_logic import (
    CAVITY_FAMILIES,
    CRITICAL_ACCEPT_NUMBER,
    EVIDENCE_MODES,
    INVOCATION_SOURCES,
    MIN_SAMPLE_DEVICES,
    REMOTE_MODES,
    SOLID_FAMILIES,
    assess_precap_inspection,
    defect_record,
    evidence_mode_record,
    invocation_record,
    package_needs_precap,
    parse_day,
    required_sample_size,
    sample_record,
    timing_record,
)


def _spec(**overrides):
    spec = {
        "invoked_by": "procurement-specification",
        "package_family": "hermetic-cavity",
        "lot_size": 400,
        "sample_size": 10,
        "defects": {"critical": 0, "major": 0, "minor": 1},
        "accept_numbers": {"major": 1, "minor": 2},
        "inspection": {
            "mode": "on-site-witness",
            "report_reference": "QA-RPT-2210",
        },
        "inspection_date": "2026-05-12",
        "seal_date": "2026-05-15",
    }
    spec.update(overrides)
    return spec


class InvocationTests(unittest.TestCase):
    def test_procurement_specification_invokes_the_inspection(self):
        record = invocation_record("procurement-specification")
        self.assertTrue(record["invoked"])
        self.assertEqual(record["source"], "procurement-specification")

    def test_absent_invocation_means_never_owed(self):
        self.assertFalse(invocation_record(None)["invoked"])

    def test_explicit_none_token_means_never_owed(self):
        self.assertFalse(invocation_record("none")["invoked"])

    def test_invocation_source_normalised(self):
        record = invocation_record("Component_Control_Plan")
        self.assertEqual(record["source"], "component-control-plan")

    def test_unknown_invocation_source_rejected(self):
        with self.assertRaises(ValueError):
            invocation_record("a-phone-call")

    def test_every_known_source_invokes(self):
        for source in INVOCATION_SOURCES:
            self.assertTrue(invocation_record(source)["invoked"])


class ApplicabilityTests(unittest.TestCase):
    def test_cavity_family_can_be_inspected(self):
        self.assertTrue(package_needs_precap("hermetic-cavity"))

    def test_solid_family_cannot(self):
        self.assertFalse(package_needs_precap("plastic-overmoulded"))

    def test_family_name_normalised(self):
        self.assertTrue(package_needs_precap("Metal_Can"))

    def test_unknown_family_rejected(self):
        with self.assertRaises(ValueError):
            package_needs_precap("wafer-on-tape")

    def test_family_sets_do_not_overlap(self):
        self.assertEqual(set(CAVITY_FAMILIES) & set(SOLID_FAMILIES), set())


class DayTests(unittest.TestCase):
    def test_parses_a_well_formed_day(self):
        self.assertEqual(parse_day("seal_date", "2026-05-15"), (2026, 5, 15))

    def test_month_zero_rejected(self):
        with self.assertRaises(ValueError):
            parse_day("seal_date", "2026-00-15")

    def test_day_past_month_end_rejected(self):
        with self.assertRaises(ValueError):
            parse_day("seal_date", "2026-06-31")

    def test_short_form_rejected(self):
        with self.assertRaises(ValueError):
            parse_day("seal_date", "2026-5-1")

    def test_non_string_rejected(self):
        with self.assertRaises(ValueError):
            parse_day("seal_date", 20260515)


class TimingTests(unittest.TestCase):
    def test_inspection_before_seal_stands(self):
        record = timing_record("2026-05-12", "2026-05-15")
        self.assertEqual(record["days_before_seal"], 3)
        self.assertTrue(record["before_seal"])
        self.assertFalse(record["void"])

    def test_inspection_on_the_seal_day_is_void(self):
        self.assertTrue(timing_record("2026-05-15", "2026-05-15")["void"])

    def test_inspection_after_the_seal_is_void(self):
        record = timing_record("2026-05-18", "2026-05-15")
        self.assertTrue(record["void"])
        self.assertEqual(record["days_before_seal"], -3)

    def test_day_difference_spans_a_month_end(self):
        self.assertEqual(timing_record("2026-04-28", "2026-05-02")["days_before_seal"], 4)

    def test_day_difference_spans_a_leap_day(self):
        self.assertEqual(timing_record("2024-02-27", "2024-03-01")["days_before_seal"], 3)


class SampleSizingTests(unittest.TestCase):
    def test_share_of_a_large_lot(self):
        self.assertEqual(required_sample_size(400), 8)

    def test_share_rounds_up_rather_than_down(self):
        self.assertEqual(required_sample_size(401), 9)

    def test_small_lot_lifted_to_the_floor(self):
        self.assertEqual(required_sample_size(50), MIN_SAMPLE_DEVICES)

    def test_lot_smaller_than_the_floor_is_capped_at_the_lot(self):
        self.assertEqual(required_sample_size(2), 2)

    def test_zero_lot_rejected(self):
        with self.assertRaises(ValueError):
            required_sample_size(0)

    def test_sample_on_the_requirement_is_sufficient(self):
        record = sample_record(400, 8)
        self.assertTrue(record["sufficient"])
        self.assertEqual(record["shortfall"], 0)

    def test_sample_one_short_is_not_sufficient(self):
        record = sample_record(400, 7)
        self.assertFalse(record["sufficient"])
        self.assertEqual(record["shortfall"], 1)

    def test_sample_larger_than_the_lot_rejected(self):
        with self.assertRaises(ValueError):
            sample_record(20, 21)


class EvidenceModeTests(unittest.TestCase):
    def test_on_site_witness_needs_only_a_report_reference(self):
        record = evidence_mode_record(
            {"mode": "on-site-witness", "report_reference": "QA-RPT-2210"}
        )
        self.assertTrue(record["admissible"])
        self.assertFalse(record["remote"])

    def test_on_site_witness_without_a_record_refused(self):
        record = evidence_mode_record({"mode": "on-site-witness"})
        self.assertFalse(record["admissible"])
        self.assertIn("report_reference", record["missing"])

    def test_photographic_route_with_identified_devices_admissible(self):
        record = evidence_mode_record(
            {
                "mode": "remote-photographic-review",
                "report_reference": "QA-RPT-2211",
                "report_issue": "B",
                "device_positions_identified": True,
            }
        )
        self.assertTrue(record["admissible"])
        self.assertTrue(record["remote"])

    def test_photographic_route_without_identified_devices_refused(self):
        record = evidence_mode_record(
            {
                "mode": "remote-photographic-review",
                "report_reference": "QA-RPT-2211",
                "report_issue": "B",
            }
        )
        self.assertFalse(record["admissible"])
        self.assertIn("device_positions_identified", record["missing"])

    def test_remote_route_without_an_issue_refused(self):
        record = evidence_mode_record(
            {
                "mode": "remote-photographic-review",
                "report_reference": "QA-RPT-2211",
                "device_positions_identified": True,
            }
        )
        self.assertFalse(record["admissible"])
        self.assertIn("report_issue", record["missing"])

    def test_manufacturer_report_route_needs_the_procedure(self):
        record = evidence_mode_record(
            {
                "mode": "manufacturer-report-only",
                "report_reference": "QA-RPT-2212",
                "report_issue": "A",
            }
        )
        self.assertFalse(record["admissible"])
        self.assertIn("manufacturer_procedure_reference", record["missing"])

    def test_manufacturer_report_route_complete_is_admissible(self):
        record = evidence_mode_record(
            {
                "mode": "manufacturer-report-only",
                "report_reference": "QA-RPT-2212",
                "report_issue": "A",
                "manufacturer_procedure_reference": "MFG-PROC-77",
            }
        )
        self.assertTrue(record["admissible"])

    def test_unknown_mode_rejected(self):
        with self.assertRaises(ValueError):
            evidence_mode_record({"mode": "a-quick-look"})

    def test_missing_mode_rejected(self):
        with self.assertRaises(ValueError):
            evidence_mode_record({"report_reference": "QA-RPT-2210"})

    def test_non_boolean_identification_flag_rejected(self):
        with self.assertRaises(ValueError):
            evidence_mode_record(
                {
                    "mode": "remote-photographic-review",
                    "report_reference": "QA-RPT-2211",
                    "report_issue": "B",
                    "device_positions_identified": "yes",
                }
            )

    def test_remote_modes_are_a_subset_of_the_modes(self):
        self.assertTrue(set(REMOTE_MODES).issubset(set(EVIDENCE_MODES)))


class DefectTests(unittest.TestCase):
    def test_clean_sample_accepted(self):
        record = defect_record(10, {"critical": 0, "major": 0, "minor": 0})
        self.assertTrue(record["accepted"])
        self.assertEqual(record["rejecting_grades"], [])

    def test_one_critical_finding_rejects(self):
        record = defect_record(10, {"critical": 1, "major": 0, "minor": 0})
        self.assertFalse(record["accepted"])
        self.assertEqual(record["rejecting_grades"], ["critical"])

    def test_critical_accept_number_is_zero(self):
        record = defect_record(10, {"critical": 0, "major": 0, "minor": 0})
        self.assertEqual(record["grades"]["critical"]["accept_number"], CRITICAL_ACCEPT_NUMBER)

    def test_critical_accept_number_cannot_be_raised(self):
        with self.assertRaises(ValueError):
            defect_record(10, {"critical": 0, "major": 0, "minor": 0}, {"critical": 1})

    def test_major_on_its_accept_number_is_accepted(self):
        record = defect_record(10, {"critical": 0, "major": 1, "minor": 0}, {"major": 1})
        self.assertTrue(record["grades"]["major"]["accepted"])

    def test_major_one_over_its_accept_number_rejects(self):
        record = defect_record(10, {"critical": 0, "major": 2, "minor": 0}, {"major": 1})
        self.assertFalse(record["grades"]["major"]["accepted"])

    def test_percent_of_sample_reported_at_the_boundary(self):
        record = defect_record(8, {"critical": 0, "major": 1, "minor": 0}, {"major": 1})
        self.assertAlmostEqual(record["grades"]["major"]["percent_of_sample"], 12.5, places=9)

    def test_every_rejecting_grade_is_listed(self):
        record = defect_record(10, {"critical": 1, "major": 3, "minor": 4}, {"major": 1, "minor": 2})
        self.assertEqual(record["rejecting_grades"], ["critical", "major", "minor"])

    def test_findings_exceeding_the_sample_rejected(self):
        with self.assertRaises(ValueError):
            defect_record(3, {"critical": 2, "major": 2, "minor": 0})

    def test_missing_grade_rejected(self):
        with self.assertRaises(ValueError):
            defect_record(10, {"critical": 0, "major": 0})

    def test_negative_count_rejected(self):
        with self.assertRaises(ValueError):
            defect_record(10, {"critical": -1, "major": 0, "minor": 0})

    def test_boolean_count_rejected(self):
        with self.assertRaises(ValueError):
            defect_record(10, {"critical": True, "major": 0, "minor": 0})


class AssessmentTests(unittest.TestCase):
    def test_clean_inspection_releases_for_seal(self):
        result = assess_precap_inspection(_spec())
        self.assertTrue(result["accepted"])
        self.assertEqual(result["disposition"], "release-for-seal")
        self.assertEqual(result["findings"], [])

    def test_uninvoked_inspection_is_not_owed_rather_than_waived(self):
        result = assess_precap_inspection(
            {"package_family": "hermetic-cavity", "invoked_by": None}
        )
        self.assertEqual(result["disposition"], "not-invoked-at-this-class")
        self.assertFalse(result["applicable"])
        self.assertTrue(any("not a waiver" in f for f in result["findings"]))

    def test_solid_package_is_not_applicable(self):
        result = assess_precap_inspection(
            _spec(package_family="solid-encapsulated")
        )
        self.assertEqual(result["disposition"], "not-applicable-no-cavity")
        self.assertFalse(result["applicable"])

    def test_inspection_after_the_seal_holds_the_lot(self):
        result = assess_precap_inspection(_spec(inspection_date="2026-05-16"))
        self.assertFalse(result["accepted"])
        self.assertEqual(result["disposition"], "hold-before-seal")
        self.assertTrue(any("void rather than late" in f for f in result["findings"]))

    def test_short_sample_holds_the_lot(self):
        result = assess_precap_inspection(_spec(sample_size=5))
        self.assertFalse(result["accepted"])
        self.assertTrue(any("short by" in f for f in result["findings"]))

    def test_incomplete_remote_route_holds_the_lot(self):
        result = assess_precap_inspection(
            _spec(inspection={"mode": "manufacturer-report-only", "report_reference": "R-1"})
        )
        self.assertFalse(result["accepted"])
        self.assertTrue(any("nothing in the record can be reopened later" in f for f in result["findings"]))

    def test_complete_remote_route_is_allowed_at_this_class(self):
        result = assess_precap_inspection(
            _spec(
                inspection={
                    "mode": "remote-photographic-review",
                    "report_reference": "QA-RPT-2211",
                    "report_issue": "B",
                    "device_positions_identified": True,
                }
            )
        )
        self.assertTrue(result["accepted"])

    def test_critical_finding_holds_the_lot(self):
        result = assess_precap_inspection(
            _spec(defects={"critical": 1, "major": 0, "minor": 0})
        )
        self.assertFalse(result["accepted"])
        self.assertTrue(any(f.startswith("critical findings") for f in result["findings"]))

    def test_every_failing_check_reported_together(self):
        result = assess_precap_inspection(
            _spec(
                inspection_date="2026-05-20",
                sample_size=4,
                inspection={"mode": "manufacturer-report-only", "report_reference": "R-1"},
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
