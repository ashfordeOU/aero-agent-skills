"""Contract test for the crimp operator certification leaf (unittest)."""

import unittest

from q7026_operator_certification_logic import (
    CERTIFIED,
    EXPIRED,
    LAPSED,
    NOT_QUALIFIED,
    VISION_OVERDUE,
    assess_operator,
    assess_operator_pool,
    certification_state,
    days_since,
    grade_sample,
    missing_training_modules,
    practice_state,
    sample_coverage,
    validate_operator,
    validate_scheme,
    vision_check_state,
)

AS_OF = "2026-09-19"


def scheme(**kw):
    s = {
        "required_training_modules": [
            "crimp-theory-and-defect-recognition",
            "hand-tool-operation-and-die-selection",
            "pull-test-and-sample-preparation",
        ],
        "samples_per_combination": 3,
        "combinations": [
            {"combination": "m39029-58-360/awg-22", "minimum_pull_off_n": 90.0},
            {"combination": "m39029-56-348/awg-20", "minimum_pull_off_n": 140.0},
        ],
        "vision_check_validity_days": 365,
        "recertification_interval_days": 730,
        "recertification_notice_days": 60,
        "practice_currency_days": 90,
    }
    s.update(kw)
    return s


def samples(per=3, force_a=118.0, force_b=170.0, visual=True):
    made = []
    for _ in range(per):
        made.append(
            {
                "combination": "m39029-58-360/awg-22",
                "pull_off_force_n": force_a,
                "visual_pass": visual,
            }
        )
        made.append(
            {
                "combination": "m39029-56-348/awg-20",
                "pull_off_force_n": force_b,
                "visual_pass": visual,
            }
        )
    return made


def operator(**kw):
    o = {
        "operator_id": "OP-0072",
        "training_modules": [
            "crimp-theory-and-defect-recognition",
            "hand-tool-operation-and-die-selection",
            "pull-test-and-sample-preparation",
        ],
        "samples": samples(),
        "certification_date": "2026-03-02",
        "vision_check_date": "2026-05-04",
        "last_crimp_date": "2026-09-10",
    }
    o.update(kw)
    return o


class TestSchemeValidation(unittest.TestCase):
    def test_a_non_mapping_scheme_raises(self):
        with self.assertRaises(ValueError):
            validate_scheme("q-st-70-26")

    def test_an_empty_training_module_list_raises(self):
        with self.assertRaises(ValueError):
            validate_scheme(scheme(required_training_modules=[]))

    def test_an_empty_combination_list_raises(self):
        with self.assertRaises(ValueError):
            validate_scheme(scheme(combinations=[]))

    def test_a_duplicated_combination_raises(self):
        with self.assertRaises(ValueError):
            validate_scheme(
                scheme(
                    combinations=[
                        {"combination": "a/b", "minimum_pull_off_n": 90.0},
                        {"combination": "A/B", "minimum_pull_off_n": 95.0},
                    ]
                )
            )

    def test_a_zero_sample_requirement_raises(self):
        with self.assertRaises(ValueError):
            validate_scheme(scheme(samples_per_combination=0))

    def test_a_notice_period_longer_than_the_interval_raises(self):
        with self.assertRaises(ValueError):
            validate_scheme(scheme(recertification_notice_days=900))


class TestOperatorValidation(unittest.TestCase):
    def test_a_non_mapping_operator_raises(self):
        with self.assertRaises(ValueError):
            validate_operator(["OP-0072"])

    def test_a_non_iso_certification_date_raises(self):
        with self.assertRaises(ValueError):
            validate_operator(operator(certification_date="last March"))

    def test_a_non_boolean_visual_result_raises(self):
        with self.assertRaises(ValueError):
            validate_operator(
                operator(
                    samples=[
                        {
                            "combination": "m39029-58-360/awg-22",
                            "pull_off_force_n": 118.0,
                            "visual_pass": "ok",
                        }
                    ]
                )
            )

    def test_a_missing_operator_identifier_raises(self):
        with self.assertRaises(ValueError):
            validate_operator(operator(operator_id="  "))

    def test_an_absent_last_crimp_date_is_kept_as_unknown(self):
        checked = validate_operator(operator(last_crimp_date=None))
        self.assertIsNone(checked["last_crimp_date"])


class TestTraining(unittest.TestCase):
    def test_a_complete_training_record_leaves_nothing_outstanding(self):
        self.assertEqual(missing_training_modules(operator(), scheme()), [])

    def test_an_incomplete_training_record_names_the_module(self):
        missing = missing_training_modules(
            operator(
                training_modules=["crimp-theory-and-defect-recognition"]
            ),
            scheme(),
        )
        self.assertIn("pull-test-and-sample-preparation", missing)

    def test_training_modules_are_compared_case_insensitively(self):
        missing = missing_training_modules(
            operator(
                training_modules=[
                    "Crimp-Theory-And-Defect-Recognition",
                    "hand-tool-operation-and-die-selection",
                    "pull-test-and-sample-preparation",
                ]
            ),
            scheme(),
        )
        self.assertEqual(missing, [])


class TestSampleGrading(unittest.TestCase):
    def test_an_undeclared_combination_raises(self):
        with self.assertRaises(ValueError):
            grade_sample(
                {
                    "combination": "something/else",
                    "pull_off_force_n": 118.0,
                    "visual_pass": True,
                },
                scheme(),
            )

    def test_a_sample_at_exactly_the_minimum_passes_the_pull_test(self):
        graded = grade_sample(
            {
                "combination": "m39029-58-360/awg-22",
                "pull_off_force_n": 90.0,
                "visual_pass": True,
            },
            scheme(),
        )
        self.assertTrue(graded["pull_pass"])
        self.assertAlmostEqual(graded["minimum_n"], 90.0, places=9)

    def test_a_sample_below_the_minimum_fails(self):
        graded = grade_sample(
            {
                "combination": "m39029-58-360/awg-22",
                "pull_off_force_n": 71.0,
                "visual_pass": True,
            },
            scheme(),
        )
        self.assertFalse(graded["pass"])

    def test_a_visual_failure_fails_a_strong_sample(self):
        graded = grade_sample(
            {
                "combination": "m39029-58-360/awg-22",
                "pull_off_force_n": 250.0,
                "visual_pass": False,
            },
            scheme(),
        )
        self.assertTrue(graded["pull_pass"])
        self.assertFalse(graded["pass"])


class TestSampleCoverage(unittest.TestCase):
    def test_a_full_sample_set_is_complete(self):
        self.assertTrue(sample_coverage(operator(), scheme())["complete"])

    def test_samples_are_counted_per_combination_not_in_total(self):
        piled = [
            {
                "combination": "m39029-58-360/awg-22",
                "pull_off_force_n": 118.0,
                "visual_pass": True,
            }
        ] * 30
        coverage = sample_coverage(operator(samples=piled), scheme())
        self.assertIn("m39029-56-348/awg-20", coverage["gaps"])

    def test_too_few_samples_on_a_combination_is_a_gap(self):
        coverage = sample_coverage(operator(samples=samples(per=2)), scheme())
        self.assertEqual(len(coverage["gaps"]), 2)

    def test_one_failed_sample_spoils_an_otherwise_full_set(self):
        made = samples()
        made[0] = dict(made[0], visual_pass=False)
        coverage = sample_coverage(operator(samples=made), scheme())
        self.assertIn("m39029-58-360/awg-22", coverage["gaps"])

    def test_an_empty_sample_set_gaps_every_combination(self):
        coverage = sample_coverage(operator(samples=[]), scheme())
        self.assertEqual(len(coverage["gaps"]), 2)


class TestClocks(unittest.TestCase):
    def test_a_future_reference_date_raises(self):
        with self.assertRaises(ValueError):
            days_since("2027-01-01", AS_OF)

    def test_a_live_vision_check_is_valid(self):
        self.assertTrue(vision_check_state(operator(), scheme(), AS_OF)["valid"])

    def test_an_old_vision_check_is_not(self):
        self.assertFalse(
            vision_check_state(
                operator(vision_check_date="2025-01-04"), scheme(), AS_OF
            )["valid"]
        )

    def test_a_vision_check_exactly_on_its_interval_is_still_valid(self):
        state = vision_check_state(
            operator(vision_check_date="2025-09-19"), scheme(), AS_OF
        )
        self.assertEqual(state["elapsed_days"], 365)
        self.assertTrue(state["valid"])

    def test_a_recent_certification_is_valid_and_not_due_soon(self):
        state = certification_state(operator(), scheme(), AS_OF)
        self.assertTrue(state["valid"])
        self.assertFalse(state["due_soon"])

    def test_a_certification_inside_the_notice_period_is_due_soon(self):
        state = certification_state(
            operator(certification_date="2024-10-01"), scheme(), AS_OF
        )
        self.assertTrue(state["valid"])
        self.assertTrue(state["due_soon"])

    def test_an_overrun_certification_is_not_valid(self):
        self.assertFalse(
            certification_state(
                operator(certification_date="2023-01-01"), scheme(), AS_OF
            )["valid"]
        )

    def test_a_recent_crimp_keeps_practice_current(self):
        self.assertTrue(practice_state(operator(), scheme(), AS_OF)["current"])

    def test_an_operator_who_never_crimped_is_not_current(self):
        state = practice_state(operator(last_crimp_date=None), scheme(), AS_OF)
        self.assertIsNone(state["elapsed_days"])
        self.assertFalse(state["current"])

    def test_a_long_gap_since_the_last_crimp_lapses_practice(self):
        self.assertFalse(
            practice_state(
                operator(last_crimp_date="2026-01-05"), scheme(), AS_OF
            )["current"]
        )


class TestDisposition(unittest.TestCase):
    def test_a_complete_current_operator_may_crimp(self):
        result = assess_operator(operator(), scheme(), AS_OF)
        self.assertEqual(result["disposition"], CERTIFIED)
        self.assertTrue(result["may_crimp"])

    def test_outstanding_training_outranks_every_clock(self):
        result = assess_operator(
            operator(
                training_modules=["crimp-theory-and-defect-recognition"],
                certification_date="2023-01-01",
            ),
            scheme(),
            AS_OF,
        )
        self.assertEqual(result["disposition"], NOT_QUALIFIED)

    def test_an_incomplete_sample_set_is_not_a_qualification(self):
        result = assess_operator(
            operator(samples=samples(per=1)), scheme(), AS_OF
        )
        self.assertEqual(result["disposition"], NOT_QUALIFIED)
        self.assertIn("qualification-sample-set-incomplete", result["reasons"])

    def test_an_expired_certification_routes_to_requalification(self):
        result = assess_operator(
            operator(certification_date="2023-01-01"), scheme(), AS_OF
        )
        self.assertEqual(result["disposition"], EXPIRED)

    def test_an_overdue_vision_check_suspends_rather_than_requalifies(self):
        result = assess_operator(
            operator(vision_check_date="2024-05-04"), scheme(), AS_OF
        )
        self.assertEqual(result["disposition"], VISION_OVERDUE)
        self.assertFalse(result["may_crimp"])

    def test_a_lapsed_practice_suspends_pending_refresher_samples(self):
        result = assess_operator(
            operator(last_crimp_date="2026-01-05"), scheme(), AS_OF
        )
        self.assertEqual(result["disposition"], LAPSED)

    def test_a_due_soon_certification_is_a_finding_not_a_block(self):
        result = assess_operator(
            operator(certification_date="2024-10-01"), scheme(), AS_OF
        )
        self.assertEqual(result["disposition"], CERTIFIED)
        self.assertIn(
            "recertification-due-inside-the-notice-period", result["findings"]
        )


class TestPoolRollUp(unittest.TestCase):
    def test_an_empty_pool_raises(self):
        with self.assertRaises(ValueError):
            assess_operator_pool([], scheme(), AS_OF)

    def test_the_pool_separates_suspension_from_requalification(self):
        report = assess_operator_pool(
            [
                operator(operator_id="OP-1"),
                operator(operator_id="OP-2", last_crimp_date="2026-01-05"),
                operator(operator_id="OP-3", certification_date="2023-01-01"),
            ],
            scheme(),
            AS_OF,
        )
        self.assertEqual(report["may_crimp"], ["OP-1"])
        self.assertEqual(report["suspended"], ["OP-2"])
        self.assertEqual(report["requalify"], ["OP-3"])

    def test_a_bench_with_nobody_current_cannot_crimp(self):
        report = assess_operator_pool(
            [operator(last_crimp_date="2026-01-05")], scheme(), AS_OF
        )
        self.assertFalse(report["bench_can_crimp"])


if __name__ == "__main__":
    unittest.main()
