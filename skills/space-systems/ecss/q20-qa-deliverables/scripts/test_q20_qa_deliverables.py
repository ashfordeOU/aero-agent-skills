"""Contract tests for the quality assurance deliverables-per-review logic."""

import unittest

from q20_qa_deliverables_logic import (
    DELIVERABLES,
    MATURITY_LADDER,
    READINESS_TOLERANCE,
    REVIEW_SEQUENCE,
    clears_threshold,
    day_difference,
    deliverable_entry,
    deliverables_for_review,
    delivery_schedule,
    evaluate_review,
    first_blocking_review,
    maturity_rank,
    normalise_identifier,
    normalise_review,
    normalise_scope,
    owed_at_review,
    parse_day,
    required_maturity,
    review_index,
    review_readiness,
)

FULL_SCOPE = ("software", "procured-items", "ground-support-equipment")


def _submission(document, maturity, submitted_on=None):
    record = {"document": document, "maturity": maturity}
    if submitted_on is not None:
        record["submitted_on"] = submitted_on
    return record


def _complete(review, scope=None, submitted_on=None):
    return [
        _submission(item["document"], item["maturity"], submitted_on)
        for item in deliverables_for_review(review, scope)
    ]


class NormaliseTests(unittest.TestCase):
    def test_identifier_trimmed_and_lowercased(self):
        self.assertEqual(normalise_identifier(" CDR ", "review"), "cdr")

    def test_identifier_non_string_rejected(self):
        with self.assertRaises(ValueError):
            normalise_identifier(4, "review")

    def test_review_alias_resolved(self):
        self.assertEqual(normalise_review("Critical-Design-Review"), "cdr")

    def test_unknown_review_rejected(self):
        with self.assertRaises(ValueError):
            normalise_review("mid-term-chat")

    def test_review_index_follows_the_sequence(self):
        self.assertLess(review_index("pdr"), review_index("cdr"))

    def test_maturity_ladder_ranks_upwards(self):
        self.assertLess(maturity_rank("draft"), maturity_rank("approved"))

    def test_unknown_maturity_rejected(self):
        with self.assertRaises(ValueError):
            maturity_rank("nearly-there")

    def test_scope_normalised_and_sorted(self):
        self.assertEqual(normalise_scope(["Software", "software"]), ("software",))

    def test_empty_scope_allowed(self):
        self.assertEqual(normalise_scope(None), ())

    def test_unknown_scope_flag_rejected(self):
        with self.assertRaises(ValueError):
            normalise_scope(["hardware-in-the-loop"])

    def test_non_sequence_scope_rejected(self):
        with self.assertRaises(ValueError):
            normalise_scope("software")


class MappingTests(unittest.TestCase):
    def test_entry_returned_for_a_known_document(self):
        entry = deliverable_entry("quality-assurance-plan")
        self.assertEqual(entry["first_review"], "prr")
        self.assertGreater(entry["lead_days"], 0)

    def test_unknown_document_rejected(self):
        with self.assertRaises(ValueError):
            deliverable_entry("weekly-newsletter")

    def test_every_row_names_reviews_in_the_sequence(self):
        for document in DELIVERABLES:
            entry = deliverable_entry(document)
            self.assertIn(entry["first_review"], REVIEW_SEQUENCE, document)
            self.assertIn(entry["approved_by_review"], REVIEW_SEQUENCE, document)

    def test_no_row_is_approved_before_it_is_first_owed(self):
        for document in DELIVERABLES:
            entry = deliverable_entry(document)
            self.assertLessEqual(
                review_index(entry["first_review"]),
                review_index(entry["approved_by_review"]),
                document,
            )

    def test_every_maturity_in_the_schedule_is_on_the_ladder(self):
        for review in REVIEW_SEQUENCE:
            for item in deliverables_for_review(review, FULL_SCOPE):
                self.assertIn(item["maturity"], MATURITY_LADDER)


class OwedTests(unittest.TestCase):
    def test_document_not_owed_before_its_first_review(self):
        self.assertFalse(owed_at_review("critical-item-list", "srr"))

    def test_document_owed_at_its_first_review(self):
        self.assertTrue(owed_at_review("critical-item-list", "pdr"))

    def test_recurring_document_owed_in_between(self):
        self.assertTrue(owed_at_review("nonconformance-status-list", "qr"))

    def test_one_shot_document_skips_the_middle(self):
        self.assertFalse(owed_at_review("quality-assurance-plan", "srr"))

    def test_document_not_owed_after_approval(self):
        self.assertFalse(owed_at_review("quality-assurance-plan", "qr"))

    def test_maturity_starts_at_draft(self):
        self.assertEqual(required_maturity("critical-item-list", "pdr"), "draft")

    def test_maturity_reaches_approved_at_the_closing_review(self):
        self.assertEqual(required_maturity("critical-item-list", "cdr"), "approved")

    def test_intermediate_review_owes_issued(self):
        self.assertEqual(
            required_maturity("nonconformance-status-list", "cdr"), "issued"
        )

    def test_single_review_document_owes_approved_at_once(self):
        self.assertEqual(required_maturity("end-item-data-package", "ar"), "approved")

    def test_maturity_of_an_unowed_document_rejected(self):
        with self.assertRaises(ValueError):
            required_maturity("end-item-data-package", "pdr")


class ScheduleTests(unittest.TestCase):
    def test_first_review_owes_the_plan_alone(self):
        owed = deliverables_for_review("prr")
        self.assertEqual([item["document"] for item in owed],
                         ["quality-assurance-plan"])

    def test_software_scope_adds_rows(self):
        without = len(deliverables_for_review("srr"))
        with_software = len(deliverables_for_review("srr", ["software"]))
        self.assertEqual(with_software, without + 1)

    def test_scope_gated_row_absent_without_the_flag(self):
        documents = [item["document"] for item in deliverables_for_review("cdr")]
        self.assertNotIn("software-problem-report-list", documents)

    def test_schedule_covers_every_review(self):
        schedule = delivery_schedule(FULL_SCOPE)
        self.assertEqual(sorted(schedule), sorted(REVIEW_SEQUENCE))

    def test_every_review_owes_something(self):
        schedule = delivery_schedule()
        for review in REVIEW_SEQUENCE:
            self.assertTrue(schedule[review], review)

    def test_deliverables_are_listed_once_each(self):
        owed = deliverables_for_review("ar", FULL_SCOPE)
        names = [item["document"] for item in owed]
        self.assertEqual(len(names), len(set(names)))


class DayArithmeticTests(unittest.TestCase):
    def test_iso_day_parsed(self):
        self.assertEqual(parse_day("2026-09-19", "day"), (2026, 9, 19))

    def test_leap_day_accepted(self):
        self.assertEqual(parse_day("2024-02-29", "day"), (2024, 2, 29))

    def test_non_leap_day_rejected(self):
        with self.assertRaises(ValueError):
            parse_day("2026-02-29", "day")

    def test_short_form_rejected(self):
        with self.assertRaises(ValueError):
            parse_day("2026-9-19", "day")

    def test_difference_within_a_month(self):
        self.assertEqual(day_difference("2026-09-19", "2026-09-05"), 14)

    def test_difference_across_a_month_boundary(self):
        self.assertEqual(day_difference("2026-03-01", "2026-02-01"), 28)

    def test_difference_across_a_leap_boundary(self):
        self.assertEqual(day_difference("2024-03-01", "2024-02-01"), 29)

    def test_difference_across_a_year_boundary(self):
        self.assertEqual(day_difference("2027-01-01", "2026-12-25"), 7)

    def test_difference_is_signed(self):
        self.assertEqual(day_difference("2026-09-05", "2026-09-19"), -14)


class EvaluateReviewTests(unittest.TestCase):
    def test_complete_set_satisfies_the_review(self):
        result = evaluate_review("cdr", _complete("cdr"))
        self.assertEqual(result["findings"], [])
        self.assertEqual(result["satisfied_count"], result["owed_count"])

    def test_missing_deliverable_reported(self):
        submissions = _complete("cdr")[1:]
        result = evaluate_review("cdr", submissions)
        self.assertEqual(len(result["missing"]), 1)

    def test_immature_deliverable_reported(self):
        submissions = _complete("cdr")
        submissions[0] = _submission(submissions[0]["document"], "draft")
        result = evaluate_review("cdr", submissions)
        self.assertEqual(len(result["immature"]), 1)

    def test_exceeding_the_owed_maturity_is_accepted(self):
        submissions = [
            _submission(item["document"], "approved")
            for item in deliverables_for_review("cdr")
        ]
        result = evaluate_review("cdr", submissions)
        self.assertEqual(result["findings"], [])

    def test_unplanned_deliverable_listed_not_failed(self):
        submissions = _complete("cdr")
        submissions.append(_submission("end-item-data-package", "approved"))
        result = evaluate_review("cdr", submissions)
        self.assertEqual(result["unplanned"], ["end-item-data-package"])
        self.assertEqual(result["findings"], [])

    def test_late_delivery_reported_when_a_review_date_is_given(self):
        submissions = _complete("cdr", submitted_on="2026-09-18")
        result = evaluate_review("cdr", submissions, None, "2026-09-19")
        self.assertTrue(result["late"])

    def test_timely_delivery_is_silent(self):
        submissions = _complete("cdr", submitted_on="2026-06-01")
        result = evaluate_review("cdr", submissions, None, "2026-09-19")
        self.assertEqual(result["late"], [])

    def test_lead_time_ignored_without_a_review_date(self):
        submissions = _complete("cdr", submitted_on="2026-09-18")
        result = evaluate_review("cdr", submissions)
        self.assertEqual(result["late"], [])

    def test_duplicate_submission_rejected(self):
        submissions = _complete("cdr")
        submissions.append(dict(submissions[0]))
        with self.assertRaises(ValueError):
            evaluate_review("cdr", submissions)

    def test_submission_without_a_maturity_rejected(self):
        with self.assertRaises(ValueError):
            evaluate_review("cdr", [{"document": "critical-item-list"}])

    def test_non_sequence_submissions_rejected(self):
        with self.assertRaises(ValueError):
            evaluate_review("cdr", {"document": "critical-item-list"})

    def test_empty_submission_set_leaves_everything_missing(self):
        result = evaluate_review("cdr", [])
        self.assertEqual(len(result["missing"]), result["owed_count"])


class ReadinessTests(unittest.TestCase):
    def test_complete_review_scores_one(self):
        result = evaluate_review("cdr", _complete("cdr"))
        self.assertAlmostEqual(review_readiness(result), 1.0, places=12)

    def test_empty_review_scores_zero(self):
        result = evaluate_review("cdr", [])
        self.assertAlmostEqual(review_readiness(result), 0.0, places=12)

    def test_partial_review_scores_the_fraction(self):
        owed = deliverables_for_review("cdr")
        submissions = _complete("cdr")[:-1]
        result = evaluate_review("cdr", submissions)
        self.assertAlmostEqual(
            review_readiness(result), (len(owed) - 1) / float(len(owed)), places=12
        )

    def test_malformed_result_rejected(self):
        with self.assertRaises(ValueError):
            review_readiness({"owed_count": 3})

    def test_threshold_hit_exactly_clears(self):
        self.assertTrue(clears_threshold(0.8, 0.8))

    def test_threshold_hit_within_tolerance_clears(self):
        self.assertTrue(clears_threshold(0.8 - READINESS_TOLERANCE / 2.0, 0.8))

    def test_below_threshold_does_not_clear(self):
        self.assertFalse(clears_threshold(0.5, 0.8))

    def test_threshold_outside_the_unit_interval_rejected(self):
        with self.assertRaises(ValueError):
            clears_threshold(0.5, 1.5)


class RollupTests(unittest.TestCase):
    def _all_complete(self, scope=None):
        return {
            review: _complete(review, scope) for review in REVIEW_SEQUENCE
        }

    def test_complete_programme_has_no_blocking_review(self):
        rolled = first_blocking_review(self._all_complete())
        self.assertIsNone(rolled["first_blocking_review"])
        self.assertEqual(len(rolled["rollup"]), len(REVIEW_SEQUENCE))

    def test_first_gap_is_the_blocking_review(self):
        submitted = self._all_complete()
        submitted["pdr"] = submitted["pdr"][:-1]
        submitted["qr"] = []
        rolled = first_blocking_review(submitted)
        self.assertEqual(rolled["first_blocking_review"], "pdr")

    def test_a_lower_threshold_can_unblock_a_review(self):
        submitted = self._all_complete()
        submitted["cdr"] = submitted["cdr"][:-1]
        strict = first_blocking_review(submitted)
        lenient = first_blocking_review(submitted, None, 0.5)
        self.assertEqual(strict["first_blocking_review"], "cdr")
        self.assertIsNone(lenient["first_blocking_review"])

    def test_scope_flags_carry_into_the_rollup(self):
        submitted = self._all_complete()
        rolled = first_blocking_review(submitted, ["software"])
        self.assertEqual(rolled["first_blocking_review"], "srr")

    def test_review_dates_drive_the_lead_time_check(self):
        submitted = {
            review: _complete(review, submitted_on="2026-09-18")
            for review in REVIEW_SEQUENCE
        }
        rolled = first_blocking_review(
            submitted, None, 1.0, {"prr": "2026-09-19"}
        )
        self.assertEqual(rolled["first_blocking_review"], "prr")

    def test_non_mapping_submission_set_rejected(self):
        with self.assertRaises(ValueError):
            first_blocking_review([])

    def test_non_mapping_review_dates_rejected(self):
        with self.assertRaises(ValueError):
            first_blocking_review(self._all_complete(), None, 1.0, ["2026-09-19"])


if __name__ == "__main__":
    unittest.main()
