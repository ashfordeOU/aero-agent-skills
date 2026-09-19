"""Contract test for the experience-summary-report-task leaf (stdlib unittest)."""

import unittest

from e2040_experience_summary_report_task_logic import (
    COMPLETENESS_TOLERANCE,
    DISPOSITIONS,
    EVENT_KINDS,
    EVENT_TOPIC,
    MANDATED_TOPICS,
    SIGNIFICANCE_WEIGHT,
    assess_experience_summary_report,
    completeness_index,
    event_capture,
    report_applicability,
    topic_coverage,
    validate_event,
    validate_report,
)

REQUEST = "contract change note CCN-14"


def report(topics=None, issue="issued"):
    return {"topics": list(topics if topics is not None else MANDATED_TOPICS), "issue": issue}


AUTO = object()


def event(eid="EV-1", kind="anomaly", significance="major", carried=AUTO):
    return {
        "id": eid,
        "kind": kind,
        "significance": significance,
        "carried_into": EVENT_TOPIC[kind] if carried is AUTO else carried,
    }


def clean_spec(**kw):
    spec = {
        "customer_requested": True,
        "request_reference": REQUEST,
        "report": report(),
        "events": [event("EV-1"), event("EV-2", kind="tool-defect", significance="minor")],
    }
    spec.update(kw)
    return spec


class TestApplicability(unittest.TestCase):
    def test_request_makes_the_report_required(self):
        self.assertTrue(report_applicability(True, REQUEST)["required"])

    def test_no_request_means_nothing_is_owed(self):
        decision = report_applicability(False)
        self.assertFalse(decision["required"])
        self.assertIsNone(decision["request_reference"])

    def test_request_without_a_reference_raises(self):
        with self.assertRaises(ValueError):
            report_applicability(True)

    def test_reference_without_a_request_raises(self):
        with self.assertRaises(ValueError):
            report_applicability(False, REQUEST)

    def test_non_boolean_request_raises(self):
        with self.assertRaises(ValueError):
            report_applicability("yes", REQUEST)


class TestValidateEvent(unittest.TestCase):
    def test_kind_is_lower_cased(self):
        self.assertEqual(validate_event(event(kind="anomaly"))["kind"], "anomaly")

    def test_every_declared_kind_maps_to_a_mandated_topic(self):
        for kind in EVENT_KINDS:
            self.assertIn(EVENT_TOPIC[kind], MANDATED_TOPICS)

    def test_unknown_kind_raises(self):
        with self.assertRaises(ValueError):
            validate_event({"id": "EV-1", "kind": "vibes", "significance": "minor"})

    def test_unknown_significance_raises(self):
        with self.assertRaises(ValueError):
            validate_event(event(significance="catastrophic"))

    def test_blank_event_id_raises(self):
        with self.assertRaises(ValueError):
            validate_event(event(""))

    def test_uncarried_event_keeps_none(self):
        self.assertIsNone(validate_event(event(carried=None))["carried_into"])

    def test_owning_topic_is_resolved_from_the_kind(self):
        self.assertEqual(validate_event(event(kind="waiver"))["owning_topic"], "design-issues")


class TestValidateReport(unittest.TestCase):
    def test_topics_are_sorted_and_lower_cased(self):
        checked = validate_report({"topics": ["Tool-Issues", "design-issues"]})
        self.assertEqual(checked["topics"], ["design-issues", "tool-issues"])

    def test_topic_outside_the_mandated_set_raises(self):
        with self.assertRaises(ValueError):
            validate_report({"topics": ["catering-notes"]})

    def test_repeated_topic_raises(self):
        with self.assertRaises(ValueError):
            validate_report({"topics": ["design-issues", "design-issues"]})

    def test_topics_as_string_raises(self):
        with self.assertRaises(ValueError):
            validate_report({"topics": "design-issues"})

    def test_unknown_issue_state_raises(self):
        with self.assertRaises(ValueError):
            validate_report({"topics": ["design-issues"], "issue": "almost"})

    def test_issue_defaults_to_draft(self):
        self.assertEqual(validate_report({"topics": ["design-issues"]})["issue"], "draft")


class TestTopicCoverage(unittest.TestCase):
    def test_all_topics_written_is_fraction_one(self):
        self.assertAlmostEqual(topic_coverage(report())["topic_fraction"], 1.0, places=9)

    def test_missing_topic_is_named(self):
        topics = [t for t in MANDATED_TOPICS if t != "reuse-recommendations"]
        coverage = topic_coverage(report(topics))
        self.assertEqual(coverage["missing_topics"], ["reuse-recommendations"])

    def test_half_the_topics_gives_a_fraction_below_one(self):
        coverage = topic_coverage(report(list(MANDATED_TOPICS)[:3]))
        self.assertAlmostEqual(coverage["topic_fraction"], 0.5, places=9)


class TestEventCapture(unittest.TestCase):
    def test_empty_log_is_treated_as_captured(self):
        capture = event_capture([], MANDATED_TOPICS)
        self.assertAlmostEqual(capture["event_fraction"], 1.0, places=9)

    def test_all_events_captured_is_fraction_one(self):
        capture = event_capture([event("EV-1"), event("EV-2")], MANDATED_TOPICS)
        self.assertAlmostEqual(capture["event_fraction"], 1.0, places=9)

    def test_uncarried_event_is_named(self):
        capture = event_capture([event("EV-1", carried=None)], MANDATED_TOPICS)
        self.assertEqual(capture["uncarried_event_ids"], ["EV-1"])
        self.assertAlmostEqual(capture["event_fraction"], 0.0, places=9)

    def test_event_filed_under_the_wrong_topic_is_named(self):
        capture = event_capture(
            [event("EV-1", kind="anomaly", carried="tool-issues")], MANDATED_TOPICS
        )
        self.assertEqual(capture["misfiled_event_ids"], ["EV-1"])

    def test_event_carried_into_an_unwritten_topic_is_named(self):
        written = [t for t in MANDATED_TOPICS if t != "anomalies-and-resolution"]
        capture = event_capture([event("EV-1", kind="anomaly")], written)
        self.assertEqual(capture["carried_into_unwritten_topic_ids"], ["EV-1"])

    def test_a_major_event_weighs_more_than_a_minor_one(self):
        capture = event_capture(
            [
                event("EV-1", significance="major", carried=None),
                event("EV-2", kind="tool-defect", significance="minor"),
            ],
            MANDATED_TOPICS,
        )
        expected = SIGNIFICANCE_WEIGHT["minor"] / float(
            SIGNIFICANCE_WEIGHT["minor"] + SIGNIFICANCE_WEIGHT["major"]
        )
        self.assertAlmostEqual(capture["event_fraction"], expected, places=9)

    def test_losing_a_minor_event_costs_less_than_losing_a_major_one(self):
        lost_minor = event_capture(
            [
                event("EV-1", significance="major"),
                event("EV-2", kind="tool-defect", significance="minor", carried=None),
            ],
            MANDATED_TOPICS,
        )
        lost_major = event_capture(
            [
                event("EV-1", significance="major", carried=None),
                event("EV-2", kind="tool-defect", significance="minor"),
            ],
            MANDATED_TOPICS,
        )
        self.assertGreater(lost_minor["event_fraction"], lost_major["event_fraction"])

    def test_event_carried_into_a_topic_outside_the_mandated_set_raises(self):
        with self.assertRaises(ValueError):
            event_capture([event("EV-1", carried="catering-notes")], MANDATED_TOPICS)

    def test_duplicate_event_id_raises(self):
        with self.assertRaises(ValueError):
            event_capture([event("EV-1"), event("EV-1")], MANDATED_TOPICS)

    def test_written_topics_as_string_raises(self):
        with self.assertRaises(ValueError):
            event_capture([event("EV-1")], "design-issues")


class TestCompletenessIndex(unittest.TestCase):
    def test_both_measures_one_gives_unity(self):
        self.assertAlmostEqual(completeness_index(1.0, 1.0), 1.0, places=9)

    def test_events_carry_the_larger_weight(self):
        self.assertAlmostEqual(completeness_index(0.0, 1.0), 0.6, places=9)

    def test_fraction_above_one_raises(self):
        with self.assertRaises(ValueError):
            completeness_index(1.0, 1.5)

    def test_boolean_fraction_raises(self):
        with self.assertRaises(ValueError):
            completeness_index(True, 1.0)


class TestAssessment(unittest.TestCase):
    def test_complete_requested_report_is_complete(self):
        result = assess_experience_summary_report(clean_spec())
        self.assertEqual(result["disposition"], "complete")
        self.assertEqual(result["findings"], [])
        self.assertAlmostEqual(result["completeness_index"], 1.0, places=9)

    def test_no_request_and_no_report_is_not_required(self):
        result = assess_experience_summary_report({"customer_requested": False})
        self.assertEqual(result["disposition"], "not-required")
        self.assertEqual(result["findings"], [])
        self.assertIsNone(result["completeness_index"])

    def test_report_offered_without_a_request_stays_not_required(self):
        result = assess_experience_summary_report(
            {"customer_requested": False, "report": report(), "events": []}
        )
        self.assertEqual(result["disposition"], "not-required")
        self.assertTrue(result["findings"])

    def test_request_with_no_report_is_incomplete(self):
        result = assess_experience_summary_report(
            {"customer_requested": True, "request_reference": REQUEST}
        )
        self.assertEqual(result["disposition"], "incomplete")
        self.assertAlmostEqual(result["completeness_index"], 0.0, places=9)

    def test_missing_topic_makes_the_report_incomplete(self):
        spec = clean_spec(report=report([t for t in MANDATED_TOPICS if t != "tool-issues"]))
        result = assess_experience_summary_report(spec)
        self.assertEqual(result["disposition"], "incomplete")
        self.assertEqual(result["missing_topics"], ["tool-issues"])

    def test_uncarried_major_event_makes_the_report_incomplete(self):
        spec = clean_spec(events=[event("EV-1", carried=None)])
        result = assess_experience_summary_report(spec)
        self.assertEqual(result["disposition"], "incomplete")
        self.assertEqual(result["uncarried_event_ids"], ["EV-1"])

    def test_draft_report_is_incomplete_even_with_full_coverage(self):
        spec = clean_spec(report=report(issue="draft"))
        result = assess_experience_summary_report(spec)
        self.assertEqual(result["disposition"], "incomplete")
        self.assertAlmostEqual(result["completeness_index"], 1.0, places=9)

    def test_every_disposition_returned_is_declared(self):
        result = assess_experience_summary_report(clean_spec())
        self.assertIn(result["disposition"], DISPOSITIONS)

    def test_missing_spec_key_raises(self):
        with self.assertRaises(ValueError):
            assess_experience_summary_report({"report": report()})

    def test_non_mapping_spec_raises(self):
        with self.assertRaises(ValueError):
            assess_experience_summary_report([clean_spec()])

    def test_tolerance_is_small_and_positive(self):
        self.assertGreater(COMPLETENESS_TOLERANCE, 0.0)
        self.assertLess(COMPLETENESS_TOLERANCE, 1e-6)


if __name__ == "__main__":
    unittest.main()
