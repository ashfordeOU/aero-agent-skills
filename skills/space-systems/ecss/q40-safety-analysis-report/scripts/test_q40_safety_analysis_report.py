"""Contract tests for the clause 7.5 safety analysis report logic."""

import unittest

from q40_safety_analysis_report_logic import (
    HAZARD_STATUSES,
    REPORT_SECTIONS,
    SEVERITY_ORDER,
    STATUS_RANK,
    assess_hazard_report,
    assess_safety_analysis_report,
    derived_status,
    section_gaps,
    trace_causes,
    uncovered_critical_items,
    unverified_controls,
    validate_hazard_report,
    validate_sections,
    validate_severity,
    validate_status,
)

MODES = ("fm-101", "fm-102")
EVENTS = ("be-201",)


def hazard(identifier="hz-1", severity="critical", causes=None, controls=None,
           verifications=None, status=None):
    """Build a hazard report record with sensible defaults."""
    record = {
        "id": identifier,
        "title": "loss of pressure control",
        "severity": severity,
        "causes": causes if causes is not None else [{"id": "c1", "reference": "fm-101"}],
        "controls": controls if controls is not None else ["relief-valve"],
        "verifications": verifications if verifications is not None
        else {"relief-valve": "qual-test-qt-7"},
    }
    if status is not None:
        record["status"] = status
    return record


class SectionTests(unittest.TestCase):
    def test_hazard_reports_sit_inside_the_section_order(self):
        self.assertIn("hazard-reports", REPORT_SECTIONS)

    def test_full_section_list_has_no_gaps(self):
        gaps = section_gaps(list(REPORT_SECTIONS))
        self.assertEqual(gaps["missing"], ())
        self.assertTrue(gaps["ordered"])

    def test_missing_section_is_reported(self):
        gaps = section_gaps([name for name in REPORT_SECTIONS if name != "conclusions"])
        self.assertEqual(gaps["missing"], ("conclusions",))

    def test_out_of_order_sections_are_reported(self):
        shuffled = list(REPORT_SECTIONS)
        shuffled[0], shuffled[1] = shuffled[1], shuffled[0]
        self.assertFalse(section_gaps(shuffled)["ordered"])

    def test_unknown_section_rejected(self):
        with self.assertRaises(ValueError):
            validate_sections(["introduction", "appendix-of-photographs"])

    def test_repeated_section_rejected(self):
        with self.assertRaises(ValueError):
            validate_sections(["introduction", "introduction"])


class TokenTests(unittest.TestCase):
    def test_severity_is_trimmed_and_lowered(self):
        self.assertEqual(validate_severity(" Critical "), "critical")

    def test_unknown_severity_rejected(self):
        with self.assertRaises(ValueError):
            validate_severity("severe")

    def test_statuses_run_weakest_first(self):
        self.assertEqual(HAZARD_STATUSES, ("open", "controlled", "closed"))

    def test_status_rank_follows_the_status_order(self):
        self.assertLess(STATUS_RANK["open"], STATUS_RANK["closed"])

    def test_unknown_status_rejected(self):
        with self.assertRaises(ValueError):
            validate_status("mitigated")

    def test_severity_order_is_most_severe_first(self):
        self.assertEqual(SEVERITY_ORDER[0], "catastrophic")


class HazardValidationTests(unittest.TestCase):
    def test_valid_record_normalises_identifiers(self):
        record = validate_hazard_report(hazard(identifier=" HZ-9 "))
        self.assertEqual(record["id"], "hz-9")

    def test_unknown_hazard_key_rejected(self):
        bad = hazard()
        bad["owner"] = "propulsion"
        with self.assertRaises(ValueError):
            validate_hazard_report(bad)

    def test_empty_cause_list_rejected(self):
        with self.assertRaises(ValueError):
            validate_hazard_report(hazard(causes=[]))

    def test_repeated_cause_rejected(self):
        with self.assertRaises(ValueError):
            validate_hazard_report(
                hazard(causes=[{"id": "c1", "reference": "fm-101"},
                               {"id": "c1", "reference": "be-201"}])
            )

    def test_unknown_cause_key_rejected(self):
        with self.assertRaises(ValueError):
            validate_hazard_report(hazard(causes=[{"id": "c1", "origin": "fmea"}]))

    def test_verification_of_an_unlisted_control_rejected(self):
        with self.assertRaises(ValueError):
            validate_hazard_report(
                hazard(controls=["relief-valve"], verifications={"burst-disc": "qt-9"})
            )

    def test_repeated_control_rejected(self):
        with self.assertRaises(ValueError):
            validate_hazard_report(hazard(controls=["relief-valve", "Relief-Valve"]))

    def test_blank_title_rejected(self):
        bad = hazard()
        bad["title"] = "   "
        with self.assertRaises(ValueError):
            validate_hazard_report(bad)


class TraceabilityTests(unittest.TestCase):
    def test_cause_referencing_a_failure_mode_is_traced(self):
        record = validate_hazard_report(hazard())
        self.assertEqual(trace_causes(record, MODES, EVENTS), ())

    def test_cause_referencing_a_basic_event_is_traced(self):
        record = validate_hazard_report(hazard(causes=[{"id": "c1", "reference": "be-201"}]))
        self.assertEqual(trace_causes(record, MODES, EVENTS), ())

    def test_cause_with_no_reference_is_untraced(self):
        record = validate_hazard_report(hazard(causes=[{"id": "c1"}]))
        self.assertEqual(trace_causes(record, MODES, EVENTS), ("c1",))

    def test_cause_referencing_an_unknown_output_is_untraced(self):
        record = validate_hazard_report(hazard(causes=[{"id": "c1", "reference": "fm-999"}]))
        self.assertEqual(trace_causes(record, MODES, EVENTS), ("c1",))

    def test_non_sequence_failure_modes_rejected(self):
        record = validate_hazard_report(hazard())
        with self.assertRaises(ValueError):
            trace_causes(record, "fm-101", EVENTS)


class ControlVerificationTests(unittest.TestCase):
    def test_verified_control_is_not_reported(self):
        record = validate_hazard_report(hazard())
        self.assertEqual(unverified_controls(record), ())

    def test_control_without_verification_is_reported(self):
        record = validate_hazard_report(
            hazard(controls=["relief-valve", "burst-disc"],
                   verifications={"relief-valve": "qt-7"})
        )
        self.assertEqual(unverified_controls(record), ("burst-disc",))

    def test_no_controls_derives_open(self):
        record = validate_hazard_report(hazard(controls=[], verifications={}))
        self.assertEqual(derived_status(record), "open")

    def test_unverified_control_derives_controlled(self):
        record = validate_hazard_report(hazard(controls=["burst-disc"], verifications={}))
        self.assertEqual(derived_status(record), "controlled")

    def test_fully_verified_controls_derive_closed(self):
        record = validate_hazard_report(hazard())
        self.assertEqual(derived_status(record), "closed")


class CriticalItemTests(unittest.TestCase):
    def test_item_named_as_a_cause_is_covered(self):
        record = validate_hazard_report(hazard())
        self.assertEqual(uncovered_critical_items(["fm-101"], [record]), ())

    def test_item_no_hazard_names_is_uncovered(self):
        record = validate_hazard_report(hazard())
        self.assertEqual(uncovered_critical_items(["fm-102"], [record]), ("fm-102",))

    def test_duplicate_items_reported_once(self):
        record = validate_hazard_report(hazard())
        self.assertEqual(uncovered_critical_items(["fm-102", "FM-102"], [record]), ("fm-102",))

    def test_non_sequence_item_list_rejected(self):
        record = validate_hazard_report(hazard())
        with self.assertRaises(ValueError):
            uncovered_critical_items("fm-102", [record])


class AssessHazardTests(unittest.TestCase):
    def test_clean_hazard_report_has_no_findings(self):
        row = assess_hazard_report(hazard(status="closed"), MODES, EVENTS)
        self.assertEqual(row["findings"], [])
        self.assertEqual(row["derived_status"], "closed")

    def test_untraced_cause_is_a_finding(self):
        row = assess_hazard_report(hazard(causes=[{"id": "c1"}]), MODES, EVENTS)
        self.assertTrue(any("traces to no failure mode" in f for f in row["findings"]))

    def test_unverified_control_is_a_finding(self):
        row = assess_hazard_report(
            hazard(controls=["burst-disc"], verifications={}), MODES, EVENTS
        )
        self.assertTrue(any("no verification" in f for f in row["findings"]))

    def test_status_declared_above_the_content_is_a_finding(self):
        row = assess_hazard_report(
            hazard(controls=["burst-disc"], verifications={}, status="closed"), MODES, EVENTS
        )
        self.assertTrue(any("supports only controlled" in f for f in row["findings"]))

    def test_status_declared_below_the_content_is_accepted(self):
        row = assess_hazard_report(hazard(status="open"), MODES, EVENTS)
        self.assertEqual(row["findings"], [])


class ReportTests(unittest.TestCase):
    def test_complete_report_is_closable(self):
        result = assess_safety_analysis_report(
            {
                "sections": list(REPORT_SECTIONS),
                "hazards": [hazard(status="closed")],
                "failure_modes": MODES,
                "basic_events": EVENTS,
                "critical_items": ["fm-101"],
            }
        )
        self.assertEqual(result["verdict"], "report-complete")
        self.assertTrue(result["closable"])

    def test_missing_section_is_a_finding(self):
        result = assess_safety_analysis_report(
            {
                "sections": [name for name in REPORT_SECTIONS if name != "conclusions"],
                "hazards": [hazard(status="closed")],
                "failure_modes": MODES,
                "basic_events": EVENTS,
            }
        )
        self.assertTrue(any("omits the conclusions" in f for f in result["findings"]))

    def test_uncovered_critical_item_is_a_finding(self):
        result = assess_safety_analysis_report(
            {
                "sections": list(REPORT_SECTIONS),
                "hazards": [hazard(status="closed")],
                "failure_modes": MODES,
                "basic_events": EVENTS,
                "critical_items": ["fm-102"],
            }
        )
        self.assertTrue(any("covered by no hazard report" in f for f in result["findings"]))

    def test_open_hazard_blocks_closure(self):
        result = assess_safety_analysis_report(
            {
                "sections": list(REPORT_SECTIONS),
                "hazards": [hazard(controls=[], verifications={})],
                "failure_modes": MODES,
                "basic_events": EVENTS,
            }
        )
        self.assertFalse(result["closable"])
        self.assertTrue(any("cannot be closed" in f for f in result["findings"]))

    def test_hazard_rows_do_not_leak_the_internal_record(self):
        result = assess_safety_analysis_report(
            {
                "sections": list(REPORT_SECTIONS),
                "hazards": [hazard(status="closed")],
                "failure_modes": MODES,
                "basic_events": EVENTS,
            }
        )
        self.assertNotIn("record", result["hazards"][0])

    def test_duplicate_hazard_id_rejected(self):
        with self.assertRaises(ValueError):
            assess_safety_analysis_report(
                {
                    "sections": list(REPORT_SECTIONS),
                    "hazards": [hazard(), hazard(identifier="HZ-1")],
                    "failure_modes": MODES,
                    "basic_events": EVENTS,
                }
            )

    def test_empty_hazard_list_rejected(self):
        with self.assertRaises(ValueError):
            assess_safety_analysis_report(
                {"sections": list(REPORT_SECTIONS), "hazards": []}
            )

    def test_missing_spec_key_rejected(self):
        with self.assertRaises(ValueError):
            assess_safety_analysis_report({"sections": list(REPORT_SECTIONS)})

    def test_non_mapping_spec_rejected(self):
        with self.assertRaises(ValueError):
            assess_safety_analysis_report([hazard()])


if __name__ == "__main__":
    unittest.main()
