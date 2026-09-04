"""Offline contract test for ndt-personnel-qualification (wave-32).

Deterministic stdlib unittest: due-date month arithmetic with clamping,
certification-currency truth table, upgrade-eligibility rules, the
Level I supervision rule, the qualification_review convenience dict and
ValueError rejections. Run: python3 scripts/test_ndt_personnel_qualification.py
"""

import os
import sys
import unittest

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import ndt_personnel_qualification_logic as logic


class TestNdtPersonnelQualification(unittest.TestCase):
    """Contract tests for NDT personnel certification governance."""

    # --- recertification due date -------------------------------------

    def test_recert_default_interval_worked_example(self):
        self.assertEqual(logic.recert_due_date("2023-06-15"), "2026-06-15")

    def test_recert_custom_interval(self):
        self.assertEqual(logic.recert_due_date("2023-06-15", 24), "2025-06-15")

    def test_recert_interval_zero_raises(self):
        with self.assertRaises(ValueError):
            logic.recert_due_date("2023-06-15", 0)

    def test_recert_interval_negative_raises(self):
        with self.assertRaises(ValueError):
            logic.recert_due_date("2023-06-15", -3)

    def test_recert_interval_non_integer_raises(self):
        with self.assertRaises(ValueError):
            logic.recert_due_date("2023-06-15", 12.0)

    # --- vision due date -----------------------------------------------

    def test_vision_default_interval_worked_example(self):
        self.assertEqual(logic.vision_due_date("2026-02-01"), "2027-02-01")

    def test_vision_custom_interval(self):
        self.assertEqual(logic.vision_due_date("2026-02-01", 24), "2028-02-01")

    def test_vision_interval_zero_raises(self):
        with self.assertRaises(ValueError):
            logic.vision_due_date("2026-02-01", 0)

    # --- month-add clamping --------------------------------------------

    def test_clamp_short_month(self):
        self.assertEqual(logic.recert_due_date("2026-01-31", 1), "2026-02-28")

    def test_clamp_leap_year_february(self):
        self.assertEqual(logic.recert_due_date("2024-01-31", 1), "2024-02-29")

    def test_clamp_non_leap_february(self):
        self.assertEqual(logic.recert_due_date("2023-01-31", 1), "2023-02-28")

    def test_year_boundary_rollover(self):
        self.assertEqual(logic.vision_due_date("2025-11-30", 3), "2026-02-28")

    # --- malformed dates -----------------------------------------------

    def test_malformed_date_raises(self):
        for bad in ("2023/06/15", "2023-13-01", "2023-02-30", "not-a-date", ""):
            with self.assertRaises(ValueError):
                logic.recert_due_date(bad)

    def test_non_canonical_date_raises(self):
        with self.assertRaises(ValueError):
            logic.vision_due_date("2026-2-01")
        with self.assertRaises(ValueError):
            logic.recert_due_date(20230615)

    # --- certification status truth table ------------------------------

    def test_status_current_within_window(self):
        self.assertEqual(
            logic.certification_status(
                "2023-06-15", "2026-12-01", "2026-11-01", "2026-09-04"
            ),
            "current",
        )

    def test_status_recert_due_worked_example(self):
        self.assertEqual(
            logic.certification_status(
                "2023-06-15", "2026-06-15", "2027-02-01", "2026-09-04"
            ),
            "recert-due",
        )

    def test_status_vision_due_only(self):
        self.assertEqual(
            logic.certification_status(
                "2023-06-15", "2027-06-15", "2026-06-01", "2026-09-04"
            ),
            "vision-due",
        )

    def test_status_recert_and_vision_due(self):
        self.assertEqual(
            logic.certification_status(
                "2023-06-15", "2026-06-15", "2026-08-01", "2026-09-04"
            ),
            "recert-and-vision-due",
        )

    def test_status_today_on_due_date_is_current(self):
        self.assertEqual(
            logic.certification_status(
                "2023-06-15", "2026-09-04", "2026-12-01", "2026-09-04"
            ),
            "current",
        )

    def test_status_malformed_date_raises(self):
        for slot in range(4):
            args = ["2023-06-15", "2026-06-15", "2027-02-01", "2026-09-04"]
            args[slot] = "bad"
            with self.assertRaises(ValueError):
                logic.certification_status(*args)

    # --- upgrade eligibility -------------------------------------------

    def test_upgrade_eligible_met_and_short_worked_example(self):
        self.assertTrue(logic.upgrade_eligible("ii", "iii", 720, 700, 26, 24, True))
        self.assertFalse(
            logic.upgrade_eligible("ii", "iii", 600, 700, 20, 24, False)
        )

    def test_upgrade_requires_all_of_hours_months_exam(self):
        self.assertFalse(logic.upgrade_eligible("ii", "iii", 720, 700, 26, 24, False))
        self.assertFalse(logic.upgrade_eligible("ii", "iii", 600, 700, 30, 24, True))
        self.assertFalse(logic.upgrade_eligible("ii", "iii", 720, 700, 20, 24, True))

    def test_upgrade_i_to_ii_allowed(self):
        self.assertTrue(logic.upgrade_eligible("i", "ii", 100, 80, 10, 8, True))

    def test_upgrade_non_adjacent_target_raises(self):
        with self.assertRaises(ValueError):
            logic.upgrade_eligible("i", "iii", 720, 700, 26, 24, True)
        with self.assertRaises(ValueError):
            logic.upgrade_eligible("iii", "ii", 720, 700, 26, 24, True)

    def test_upgrade_same_level_raises(self):
        with self.assertRaises(ValueError):
            logic.upgrade_eligible("ii", "ii", 720, 700, 26, 24, True)

    def test_upgrade_unknown_level_raises(self):
        with self.assertRaises(ValueError):
            logic.upgrade_eligible("iv", "iii", 720, 700, 26, 24, True)

    def test_upgrade_negative_hours_or_months_raises(self):
        for bad_args in (
            (-1, 700, 26, 24),
            (720, -1, 26, 24),
            (720, 700, -1, 24),
            (720, 700, 26, -1),
        ):
            with self.assertRaises(ValueError):
                logic.upgrade_eligible("ii", "iii", *bad_args, True)

    # --- supervision rule ----------------------------------------------

    def test_supervision_level_one_requires_supervisor(self):
        self.assertTrue(logic.supervision_valid("i", "ii"))
        self.assertTrue(logic.supervision_valid("i", "iii"))
        self.assertFalse(logic.supervision_valid("i", "i"))

    def test_supervision_level_two_and_three_work_independently(self):
        for operator in ("ii", "iii"):
            for supervisor in ("i", "ii", "iii"):
                self.assertTrue(logic.supervision_valid(operator, supervisor))

    def test_supervision_unknown_level_raises(self):
        with self.assertRaises(ValueError):
            logic.supervision_valid("iv", "ii")
        with self.assertRaises(ValueError):
            logic.supervision_valid("i", "iv")

    # --- qualification_review convenience ------------------------------

    def test_review_worked_example_dict(self):
        review = logic.qualification_review(
            "2023-06-15",
            "2026-02-01",
            "2026-09-04",
            "ii",
            "iii",
            upgrade_inputs={
                "target_level": "iii",
                "held_hours": 600,
                "required_hours": 700,
                "held_months": 20,
                "required_months": 24,
                "exam_passed": False,
            },
        )
        self.assertEqual(
            sorted(review.keys()),
            [
                "certification_status",
                "recert_due_date_iso",
                "supervision_ok",
                "upgrade_eligible",
                "vision_due_date_iso",
            ],
        )
        self.assertEqual(review["certification_status"], "recert-due")
        self.assertEqual(review["recert_due_date_iso"], "2026-06-15")
        self.assertEqual(review["vision_due_date_iso"], "2027-02-01")
        self.assertTrue(review["supervision_ok"])
        self.assertFalse(review["upgrade_eligible"])

    def test_review_without_upgrade_inputs(self):
        review = logic.qualification_review(
            "2023-06-15", "2026-02-01", "2026-09-04", "i", "ii"
        )
        self.assertIsNone(review["upgrade_eligible"])
        self.assertEqual(review["certification_status"], "recert-due")
        self.assertTrue(review["supervision_ok"])

    def test_review_error_propagation(self):
        with self.assertRaises(ValueError):
            logic.qualification_review(
                "2023-06-15",
                "2026-02-01",
                "2026-09-04",
                "ii",
                "iii",
                upgrade_inputs={"target_level": "iii"},
            )
        with self.assertRaises(ValueError):
            logic.qualification_review(
                "2023-06-15", "2026-02-01", "2026-09-04", "ii", "iv"
            )

    def test_review_met_upgrade_flips_verdict(self):
        review = logic.qualification_review(
            "2023-06-15",
            "2026-02-01",
            "2026-09-04",
            "ii",
            "iii",
            upgrade_inputs={
                "target_level": "iii",
                "held_hours": 720,
                "required_hours": 700,
                "held_months": 26,
                "required_months": 24,
                "exam_passed": True,
            },
        )
        self.assertTrue(review["upgrade_eligible"])

    # --- determinism ----------------------------------------------------

    def test_deterministic_run_to_run(self):
        args = ("2023-06-15", "2026-02-01", "2026-09-04", "ii", "iii")
        self.assertEqual(logic.qualification_review(*args), logic.qualification_review(*args))


if __name__ == "__main__":
    unittest.main()
