"""Contract tests for the Annex I experience summary report data-item logic."""

import unittest

from e2040_experience_summary_report_data_item_logic import (
    NARRATIVE_PARTS,
    REQUIRED_SECTIONS,
    TRACEABILITY_TOLERANCE,
    assess_experience_report,
    captured_anomaly_ids,
    lesson_gaps,
    missing_sections,
    priority_index,
    rank_lessons,
    severity_weighted_traceability,
    uncaptured_anomalies,
    validate_anomalies,
    validate_anomaly,
    validate_index,
    validate_lesson,
    validate_lessons,
)

ALL_SECTIONS = list(REQUIRED_SECTIONS)

ANOMALIES = [
    {"id": "AN-1", "severity": 5, "phase": "qualification"},
    {"id": "AN-2", "severity": 2, "phase": "breadboard"},
    {"id": "AN-3", "severity": 3, "phase": "engineering-model"},
]


def lesson(identifier="LL-1", occurrence=3, impact=4, detection=2, links=("AN-1",), **parts):
    record = {
        "id": identifier,
        "occurrence": occurrence,
        "impact": impact,
        "detection_difficulty": detection,
        "anomaly_ids": list(links),
        "observation": "the supply rail collapsed under a cold start",
        "cause": "the soft-start capacitor was sized for room temperature only",
        "recommendation": "size soft-start at the cold survival limit",
        "owner": "power-electronics-lead",
    }
    record.update(parts)
    return record


class SectionTests(unittest.TestCase):
    def test_complete_section_list_has_no_gap(self):
        self.assertEqual(missing_sections(ALL_SECTIONS), [])

    def test_absent_anomaly_history_is_named(self):
        partial = [s for s in ALL_SECTIONS if s != "anomaly-history"]
        self.assertEqual(missing_sections(partial), ["anomaly-history"])

    def test_section_match_ignores_case(self):
        self.assertEqual(missing_sections([s.upper() for s in ALL_SECTIONS]), [])

    def test_non_sequence_section_list_rejected(self):
        with self.assertRaises(ValueError):
            missing_sections(None)


class AnomalyTests(unittest.TestCase):
    def test_normalized_entry_keeps_the_phase(self):
        record = validate_anomaly(ANOMALIES[0])
        self.assertEqual(record["phase"], "qualification")

    def test_severity_above_the_scale_rejected(self):
        with self.assertRaises(ValueError):
            validate_anomaly({"id": "AN-9", "severity": 9, "phase": "qualification"})

    def test_fractional_severity_rejected(self):
        with self.assertRaises(ValueError):
            validate_anomaly({"id": "AN-9", "severity": 2.5, "phase": "qualification"})

    def test_missing_phase_rejected(self):
        with self.assertRaises(ValueError):
            validate_anomaly({"id": "AN-9", "severity": 2})

    def test_duplicate_anomaly_identifier_rejected(self):
        with self.assertRaises(ValueError):
            validate_anomalies(ANOMALIES + [dict(ANOMALIES[0])])

    def test_empty_history_rejected(self):
        with self.assertRaises(ValueError):
            validate_anomalies([])

    def test_index_inside_the_scale_accepted(self):
        self.assertEqual(validate_index(4, "impact"), 4)

    def test_boolean_index_rejected(self):
        with self.assertRaises(ValueError):
            validate_index(True, "impact")


class LessonTests(unittest.TestCase):
    def setUp(self):
        self.known = set(r["id"] for r in validate_anomalies(ANOMALIES))

    def test_complete_lesson_has_no_gap(self):
        record = validate_lesson(lesson(), self.known)
        self.assertEqual(lesson_gaps(record), [])

    def test_missing_owner_is_a_gap(self):
        record = validate_lesson(lesson(owner=None), self.known)
        self.assertEqual(lesson_gaps(record), ["owner"])

    def test_blank_cause_counts_as_absent(self):
        record = validate_lesson(lesson(cause="   "), self.known)
        self.assertIn("cause", lesson_gaps(record))

    def test_every_narrative_part_is_checked(self):
        blanks = dict((part, None) for part in NARRATIVE_PARTS)
        record = validate_lesson(lesson(**blanks), self.known)
        self.assertEqual(lesson_gaps(record), list(NARRATIVE_PARTS))

    def test_link_to_an_unlisted_anomaly_rejected(self):
        with self.assertRaises(ValueError):
            validate_lesson(lesson(links=("AN-404",)), self.known)

    def test_links_are_deduplicated(self):
        record = validate_lesson(lesson(links=("AN-1", "AN-1")), self.known)
        self.assertEqual(record["anomaly_ids"], ["AN-1"])

    def test_duplicate_lesson_identifier_rejected(self):
        with self.assertRaises(ValueError):
            validate_lessons([lesson("LL-1"), lesson("LL-1")], self.known)

    def test_non_sequence_links_rejected(self):
        with self.assertRaises(ValueError):
            validate_lesson(lesson(links="AN-1"), self.known)

    def test_non_string_narrative_part_rejected(self):
        with self.assertRaises(ValueError):
            validate_lesson(lesson(owner=7), self.known)


class PriorityTests(unittest.TestCase):
    def test_index_is_the_three_factor_product(self):
        self.assertEqual(priority_index(lesson(occurrence=3, impact=4, detection=2)), 24)

    def test_detection_difficulty_changes_the_order(self):
        seen_coming = lesson("LL-1", 2, 5, 1)
        invisible = lesson("LL-2", 2, 3, 3)
        self.assertGreater(priority_index(invisible), priority_index(seen_coming))

    def test_ranking_is_by_descending_index(self):
        order = rank_lessons([lesson("LL-1", 1, 1, 1), lesson("LL-2", 5, 5, 5)])
        self.assertEqual(order, ["LL-2", "LL-1"])

    def test_tie_is_broken_by_identifier(self):
        order = rank_lessons([lesson("LL-9", 2, 2, 2), lesson("LL-2", 2, 2, 2)])
        self.assertEqual(order, ["LL-2", "LL-9"])

    def test_ranking_is_stable_across_input_order(self):
        first = rank_lessons([lesson("LL-9", 2, 2, 2), lesson("LL-2", 2, 2, 2)])
        second = rank_lessons([lesson("LL-2", 2, 2, 2), lesson("LL-9", 2, 2, 2)])
        self.assertEqual(first, second)

    def test_index_out_of_scale_rejected(self):
        with self.assertRaises(ValueError):
            priority_index({"occurrence": 6, "impact": 2, "detection_difficulty": 2})

    def test_empty_lesson_set_cannot_be_ranked(self):
        with self.assertRaises(ValueError):
            rank_lessons([])


class TraceabilityTests(unittest.TestCase):
    def setUp(self):
        self.anomalies = validate_anomalies(ANOMALIES)
        self.known = set(r["id"] for r in self.anomalies)

    def test_captured_set_is_the_union_of_the_links(self):
        lessons = validate_lessons(
            [lesson("LL-1", links=("AN-1",)), lesson("LL-2", links=("AN-2",))], self.known
        )
        self.assertEqual(captured_anomaly_ids(lessons), {"AN-1", "AN-2"})

    def test_traceability_is_severity_weighted(self):
        lessons = validate_lessons([lesson("LL-1", links=("AN-1",))], self.known)
        self.assertAlmostEqual(
            severity_weighted_traceability(self.anomalies, lessons), 0.5, places=9
        )

    def test_capturing_the_minor_anomalies_does_not_read_as_coverage(self):
        lessons = validate_lessons([lesson("LL-1", links=("AN-2", "AN-3"))], self.known)
        self.assertAlmostEqual(
            severity_weighted_traceability(self.anomalies, lessons), 0.5, places=9
        )

    def test_full_capture_is_one(self):
        lessons = validate_lessons(
            [lesson("LL-1", links=("AN-1", "AN-2", "AN-3"))], self.known
        )
        self.assertAlmostEqual(
            severity_weighted_traceability(self.anomalies, lessons), 1.0, places=9
        )

    def test_uncaptured_anomalies_are_listed_in_history_order(self):
        lessons = validate_lessons([lesson("LL-1", links=("AN-2",))], self.known)
        self.assertEqual(uncaptured_anomalies(self.anomalies, lessons), ["AN-1", "AN-3"])

    def test_empty_history_cannot_be_traced(self):
        lessons = validate_lessons([lesson("LL-1")], self.known)
        with self.assertRaises(ValueError):
            severity_weighted_traceability([], lessons)


class AssessmentTests(unittest.TestCase):
    def _report(self, **overrides):
        report = {
            "sections": list(ALL_SECTIONS),
            "anomalies": [dict(a) for a in ANOMALIES],
            "lessons": [lesson("LL-1", links=("AN-1", "AN-2", "AN-3"))],
            "required_traceability": 1.0,
        }
        report.update(overrides)
        return report

    def test_complete_report_is_compliant(self):
        result = assess_experience_report(self._report())
        self.assertTrue(result["compliant"])
        self.assertEqual(result["findings"], [])
        self.assertAlmostEqual(result["traceability"], 1.0, places=9)

    def test_top_lesson_is_reported_with_its_index(self):
        result = assess_experience_report(
            self._report(
                lessons=[
                    lesson("LL-1", 1, 1, 1, links=("AN-1", "AN-2", "AN-3")),
                    lesson("LL-2", 5, 5, 4, links=("AN-1",)),
                ]
            )
        )
        self.assertEqual(result["top_lesson"], "LL-2")
        self.assertEqual(result["top_priority_index"], 100)

    def test_uncaptured_anomaly_is_a_finding(self):
        result = assess_experience_report(
            self._report(lessons=[lesson("LL-1", links=("AN-1",))], required_traceability=0.0)
        )
        self.assertEqual(result["uncaptured_anomalies"], ["AN-2", "AN-3"])
        self.assertFalse(result["compliant"])

    def test_incomplete_lesson_is_a_finding(self):
        result = assess_experience_report(
            self._report(
                lessons=[lesson("LL-1", links=("AN-1", "AN-2", "AN-3"), recommendation=None)]
            )
        )
        self.assertEqual(result["incomplete_lessons"], ["LL-1"])
        self.assertTrue(any("recommendation" in f for f in result["findings"]))

    def test_traceability_exactly_at_the_required_level_is_met(self):
        result = assess_experience_report(
            self._report(
                lessons=[lesson("LL-1", links=("AN-1",))], required_traceability=0.5
            )
        )
        self.assertTrue(result["traceability_met"])
        self.assertLessEqual(
            abs(result["traceability"] - result["required_traceability"]),
            TRACEABILITY_TOLERANCE,
        )

    def test_traceability_below_the_required_level_is_a_finding(self):
        result = assess_experience_report(
            self._report(
                lessons=[lesson("LL-1", links=("AN-2",))], required_traceability=0.9
            )
        )
        self.assertFalse(result["traceability_met"])
        self.assertTrue(any("below the required" in f for f in result["findings"]))

    def test_absent_section_is_a_finding(self):
        sections = [s for s in ALL_SECTIONS if s != "lessons-learned"]
        result = assess_experience_report(self._report(sections=sections))
        self.assertEqual(result["missing_sections"], ["lessons-learned"])

    def test_required_traceability_outside_unit_interval_rejected(self):
        with self.assertRaises(ValueError):
            assess_experience_report(self._report(required_traceability=2.0))

    def test_missing_report_key_rejected(self):
        report = self._report()
        del report["lessons"]
        with self.assertRaises(ValueError):
            assess_experience_report(report)

    def test_non_mapping_report_rejected(self):
        with self.assertRaises(ValueError):
            assess_experience_report("report")


if __name__ == "__main__":
    unittest.main()
