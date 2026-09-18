"""Contract test for the q7030-operator-certification leaf (stdlib unittest)."""

import datetime
import unittest

from q7030_operator_certification_logic import (
    CERTIFICATION_VALIDITY_DAYS,
    CERTIFIED,
    CONTINUITY_WINDOW_DAYS,
    EXPIRED,
    MIN_PRACTICAL_WRAPS,
    MIN_THEORY_SCORE,
    NOT_QUALIFIED,
    PERMITTED,
    REFUSED,
    SUSPENDED,
    VISION_VALIDITY_DAYS,
    assess_operator,
    assignment_verdict,
    combination_key,
    days_between,
    endorsement_status,
    evidence_findings,
    validate_endorsement,
    validate_operator,
    vision_findings,
)

TODAY = datetime.date(2026, 9, 18)


def day(offset):
    return TODAY - datetime.timedelta(days=offset)


def endorsement(gauge=26, terminal_type="square-post", **kw):
    record = {
        "gauge": gauge,
        "terminal_type": terminal_type,
        "examination_date": day(30),
        "theory_score": 92,
        "practical_wraps_accepted": 12,
        "pull_tests_passed": 4,
        "last_production_date": day(5),
    }
    record.update(kw)
    return record


def operator(op_id="OP-11", endorsements=None, **kw):
    record = {
        "id": op_id,
        "vision_check_date": day(60),
        "endorsements": [endorsement()] if endorsements is None else endorsements,
    }
    record.update(kw)
    return record


class TestCombinationKey(unittest.TestCase):
    def test_a_key_is_the_gauge_and_the_terminal_type(self):
        self.assertEqual(combination_key(26, "square-post"), (26, "square-post"))

    def test_unknown_gauge_raises(self):
        with self.assertRaises(ValueError):
            combination_key(18, "square-post")

    def test_unknown_terminal_type_raises(self):
        with self.assertRaises(ValueError):
            combination_key(26, "solder-lug")

    def test_non_integer_gauge_raises(self):
        with self.assertRaises(ValueError):
            combination_key("26", "square-post")


class TestDates(unittest.TestCase):
    def test_days_between_counts_whole_days(self):
        self.assertEqual(days_between(day(10), TODAY), 10)

    def test_an_iso_string_is_accepted(self):
        self.assertEqual(days_between("2026-09-08", TODAY), 10)

    def test_a_malformed_string_raises(self):
        with self.assertRaises(ValueError):
            days_between("08/09/2026", TODAY)

    def test_a_non_date_raises(self):
        with self.assertRaises(ValueError):
            days_between(20260908, TODAY)


class TestValidation(unittest.TestCase):
    def test_non_mapping_endorsement_raises(self):
        with self.assertRaises(ValueError):
            validate_endorsement([26, "square-post"])

    def test_negative_theory_score_raises(self):
        with self.assertRaises(ValueError):
            validate_endorsement(endorsement(theory_score=-1))

    def test_last_production_defaults_to_the_examination(self):
        record = endorsement()
        del record["last_production_date"]
        norm = validate_endorsement(record)
        self.assertEqual(norm["last_production_date"], norm["examination_date"])

    def test_operator_needs_an_endorsement_list(self):
        with self.assertRaises(ValueError):
            validate_operator(operator(endorsements=[]))

    def test_blank_operator_id_raises(self):
        with self.assertRaises(ValueError):
            validate_operator(operator(""))

    def test_duplicate_combinations_raise(self):
        with self.assertRaises(ValueError):
            validate_operator(
                operator(endorsements=[endorsement(), endorsement()])
            )

    def test_two_different_combinations_are_accepted(self):
        norm = validate_operator(
            operator(endorsements=[endorsement(), endorsement(gauge=30)])
        )
        self.assertEqual(len(norm["endorsements"]), 2)


class TestEvidence(unittest.TestCase):
    def test_complete_evidence_raises_nothing(self):
        self.assertEqual(evidence_findings(endorsement()), [])

    def test_a_failing_theory_score_is_reported(self):
        findings = evidence_findings(endorsement(theory_score=MIN_THEORY_SCORE - 1))
        self.assertIn("theory-score-below-pass-mark", findings)

    def test_a_score_exactly_on_the_pass_mark_is_accepted(self):
        self.assertEqual(evidence_findings(endorsement(theory_score=MIN_THEORY_SCORE)), [])

    def test_too_few_practical_wraps_are_reported(self):
        findings = evidence_findings(
            endorsement(practical_wraps_accepted=MIN_PRACTICAL_WRAPS - 1)
        )
        self.assertIn("too-few-accepted-practical-wraps", findings)

    def test_too_few_pull_tests_are_reported(self):
        findings = evidence_findings(endorsement(pull_tests_passed=0))
        self.assertIn("too-few-passed-practical-pull-tests", findings)


class TestEndorsementStatus(unittest.TestCase):
    def test_a_fresh_worked_endorsement_is_current(self):
        status, findings = endorsement_status(endorsement(), TODAY)
        self.assertEqual(status, CERTIFIED)
        self.assertEqual(findings, [])

    def test_thin_evidence_is_not_qualified(self):
        status, _ = endorsement_status(endorsement(theory_score=10), TODAY)
        self.assertEqual(status, NOT_QUALIFIED)

    def test_an_old_examination_expires(self):
        old = endorsement(
            examination_date=day(CERTIFICATION_VALIDITY_DAYS + 1),
            last_production_date=day(1),
        )
        status, findings = endorsement_status(old, TODAY)
        self.assertEqual(status, EXPIRED)
        self.assertIn("certification-period-elapsed", findings)

    def test_an_examination_exactly_on_the_period_is_still_current(self):
        edge = endorsement(
            examination_date=day(CERTIFICATION_VALIDITY_DAYS),
            last_production_date=day(1),
        )
        status, _ = endorsement_status(edge, TODAY)
        self.assertEqual(status, CERTIFIED)

    def test_an_idle_combination_is_suspended(self):
        idle = endorsement(last_production_date=day(CONTINUITY_WINDOW_DAYS + 1))
        status, findings = endorsement_status(idle, TODAY)
        self.assertEqual(status, SUSPENDED)
        self.assertIn("continuity-window-elapsed-without-production", findings)

    def test_production_exactly_on_the_continuity_edge_is_current(self):
        edge = endorsement(last_production_date=day(CONTINUITY_WINDOW_DAYS))
        status, _ = endorsement_status(edge, TODAY)
        self.assertEqual(status, CERTIFIED)

    def test_an_examination_in_the_future_raises(self):
        with self.assertRaises(ValueError):
            endorsement_status(endorsement(examination_date=day(-5)), TODAY)


class TestVision(unittest.TestCase):
    def test_an_in_date_vision_check_raises_nothing(self):
        self.assertEqual(vision_findings(operator(), TODAY), [])

    def test_a_lapsed_vision_check_is_reported(self):
        lapsed = operator(vision_check_date=day(VISION_VALIDITY_DAYS + 1))
        self.assertIn("vision-check-out-of-date", vision_findings(lapsed, TODAY))

    def test_a_vision_check_in_the_future_raises(self):
        with self.assertRaises(ValueError):
            vision_findings(operator(vision_check_date=day(-1)), TODAY)


class TestAssessOperator(unittest.TestCase):
    def test_a_clean_file_lists_the_current_combination(self):
        assessed = assess_operator(operator(), TODAY)
        self.assertEqual(assessed["current_combinations"], [(26, "square-post")])

    def test_a_lapsed_vision_check_suspends_every_current_endorsement(self):
        lapsed = operator(vision_check_date=day(VISION_VALIDITY_DAYS + 2))
        assessed = assess_operator(lapsed, TODAY)
        self.assertEqual(assessed["current_combinations"], [])
        self.assertEqual(assessed["endorsements"][0]["status"], SUSPENDED)

    def test_endorsements_are_graded_independently(self):
        file_ = operator(
            endorsements=[
                endorsement(),
                endorsement(gauge=30, last_production_date=day(CONTINUITY_WINDOW_DAYS + 30)),
            ]
        )
        assessed = assess_operator(file_, TODAY)
        self.assertEqual(assessed["endorsements"][0]["status"], CERTIFIED)
        self.assertEqual(assessed["endorsements"][1]["status"], SUSPENDED)


class TestAssignment(unittest.TestCase):
    def test_a_current_endorsement_permits_the_assignment(self):
        verdict = assignment_verdict(operator(), 26, "square-post", TODAY)
        self.assertEqual(verdict["verdict"], PERMITTED)
        self.assertTrue(verdict["permitted"])

    def test_a_different_gauge_is_refused(self):
        verdict = assignment_verdict(operator(), 30, "square-post", TODAY)
        self.assertEqual(verdict["verdict"], REFUSED)
        self.assertIn("no-endorsement-for-this-combination", verdict["findings"])

    def test_a_different_terminal_type_is_refused(self):
        verdict = assignment_verdict(operator(), 26, "double-post", TODAY)
        self.assertFalse(verdict["permitted"])

    def test_a_suspended_endorsement_refuses_the_assignment(self):
        idle = operator(
            endorsements=[endorsement(last_production_date=day(CONTINUITY_WINDOW_DAYS + 10))]
        )
        verdict = assignment_verdict(idle, 26, "square-post", TODAY)
        self.assertEqual(verdict["status"], SUSPENDED)
        self.assertFalse(verdict["permitted"])

    def test_an_unknown_combination_in_the_question_raises(self):
        with self.assertRaises(ValueError):
            assignment_verdict(operator(), 26, "solder-lug", TODAY)


if __name__ == "__main__":
    unittest.main()
