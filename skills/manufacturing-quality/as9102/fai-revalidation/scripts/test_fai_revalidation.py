#!/usr/bin/env python3
"""Gate 3 contract test: first article inspection (FAI) revalidation.

Exercises scripts/fai_revalidation_logic.py (stdlib unittest,
offline). Contract: docs/harness-contract.md gate 3: the time-driven
due date from the last FAI date and the interval, the status verdict
(due, upcoming, current) with the days remaining, the change trigger
verdict (revalidation-required, new-fai-required, not-triggered), the
next revalidation date combining the schedule with a change date, and
the re-verification scope; invalid inputs raise ValueError. The
physically meaningful invariants: a due status never has positive
days remaining, a triggering change type always demands
revalidation, and the key characteristics always stay in scope.
"""

import datetime
import os
import sys
import unittest

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import fai_revalidation_logic as frl  # noqa: E402


class DueDateTest(unittest.TestCase):
    def test_annual_interval(self):
        self.assertEqual(frl.DEFAULT_INTERVAL_DAYS, 365)
        self.assertEqual(
            frl.revalidation_due_date(datetime.date(2025, 1, 1)),
            datetime.date(2026, 1, 1),
        )

    def test_custom_interval(self):
        self.assertEqual(
            frl.revalidation_due_date(datetime.date(2026, 3, 15), 180),
            datetime.date(2026, 9, 11),
        )

    def test_across_leap_year(self):
        self.assertEqual(
            frl.revalidation_due_date(datetime.date(2024, 2, 28), 365),
            datetime.date(2025, 2, 27),
        )

    def test_non_date_raises(self):
        with self.assertRaises(ValueError):
            frl.revalidation_due_date("2025-01-01")

    def test_non_positive_interval_raises(self):
        with self.assertRaises(ValueError):
            frl.revalidation_due_date(datetime.date(2025, 1, 1), 0)
        with self.assertRaises(ValueError):
            frl.revalidation_due_date(datetime.date(2025, 1, 1), -30)


class StatusTest(unittest.TestCase):
    def test_on_due_date_is_due(self):
        result = frl.revalidation_status(
            datetime.date(2025, 1, 1), datetime.date(2026, 1, 1)
        )
        self.assertEqual(result["status"], "due")
        self.assertEqual(result["days_remaining"], 0)

    def test_past_due_is_due(self):
        result = frl.revalidation_status(
            datetime.date(2025, 1, 1), datetime.date(2026, 2, 1)
        )
        self.assertEqual(result["status"], "due")
        self.assertLess(result["days_remaining"], 0)

    def test_within_window_is_upcoming(self):
        result = frl.revalidation_status(
            datetime.date(2025, 1, 1), datetime.date(2025, 12, 15)
        )
        self.assertEqual(result["status"], "upcoming")
        self.assertEqual(result["days_remaining"], 17)

    def test_at_window_edge_is_upcoming(self):
        result = frl.revalidation_status(
            datetime.date(2025, 1, 1), datetime.date(2025, 11, 2)
        )
        self.assertEqual(result["status"], "upcoming")
        self.assertEqual(result["days_remaining"], 60)

    def test_beyond_window_is_current(self):
        result = frl.revalidation_status(
            datetime.date(2025, 1, 1), datetime.date(2025, 11, 1)
        )
        self.assertEqual(result["status"], "current")
        self.assertEqual(result["days_remaining"], 61)

    def test_due_date_reported(self):
        result = frl.revalidation_status(
            datetime.date(2025, 1, 1), datetime.date(2025, 6, 1)
        )
        self.assertEqual(result["due_date"], datetime.date(2026, 1, 1))


class TriggerVerdictTest(unittest.TestCase):
    def test_trigger_types_require_revalidation(self):
        for ctype in sorted(frl.TRIGGER_TYPES):
            self.assertEqual(
                frl.change_trigger_verdict(ctype), "revalidation-required", ctype
            )

    def test_new_fai_types_not_revalidation(self):
        for ctype in sorted(frl.NEW_FAI_TYPES):
            self.assertEqual(
                frl.change_trigger_verdict(ctype), "new-fai-required", ctype
            )

    def test_no_change_not_triggered(self):
        self.assertEqual(frl.change_trigger_verdict("none"), "not-triggered")

    def test_unknown_type_raises(self):
        with self.assertRaises(ValueError):
            frl.change_trigger_verdict("electrical")

    def test_type_sets_disjoint_invariant(self):
        """A change type cannot be both a revalidation trigger and a
        new-FAI trigger."""
        self.assertTrue(frl.TRIGGER_TYPES.isdisjoint(frl.NEW_FAI_TYPES))


class NextDateTest(unittest.TestCase):
    def test_no_change_uses_schedule(self):
        self.assertEqual(
            frl.next_revalidation_date(datetime.date(2025, 1, 1), 365),
            datetime.date(2026, 1, 1),
        )

    def test_change_after_last_fai_pulls_schedule_later(self):
        self.assertEqual(
            frl.next_revalidation_date(
                datetime.date(2025, 1, 1), 365, change_date=datetime.date(2025, 6, 1)
            ),
            datetime.date(2026, 6, 1),
        )

    def test_change_before_last_fai_does_not_pull_earlier(self):
        self.assertEqual(
            frl.next_revalidation_date(
                datetime.date(2025, 6, 1), 365, change_date=datetime.date(2025, 1, 1)
            ),
            datetime.date(2026, 6, 1),
        )

    def test_non_date_change_raises(self):
        with self.assertRaises(ValueError):
            frl.next_revalidation_date(datetime.date(2025, 1, 1), 365, "2025-06-01")


class ScopeTest(unittest.TestCase):
    def test_affected_plus_key_characteristics(self):
        scope = frl.revalidation_scope(["hole diameter"], ["hole diameter", "surface finish"])
        self.assertEqual(scope, ["hole diameter", "surface finish"])

    def test_key_characteristics_always_in_scope(self):
        scope = frl.revalidation_scope([], ["surface finish", "hardness"])
        self.assertEqual(scope, ["surface finish", "hardness"])

    def test_order_preserved_affected_first(self):
        scope = frl.revalidation_scope(
            ["bore diameter", "wall thickness"], ["wall thickness", "hardness"]
        )
        self.assertEqual(scope, ["bore diameter", "wall thickness", "hardness"])

    def test_tuple_inputs_accepted(self):
        scope = frl.revalidation_scope(("bore diameter",), ("hardness",))
        self.assertEqual(scope, ["bore diameter", "hardness"])

    def test_non_list_raises(self):
        with self.assertRaises(ValueError):
            frl.revalidation_scope("bore diameter", [])
        with self.assertRaises(ValueError):
            frl.revalidation_scope([], "hardness")


class InvariantTest(unittest.TestCase):
    def test_due_status_never_positive_remaining(self):
        """Physically meaningful invariant: a due revalidation cannot
        have days remaining; the due date has passed or is today."""
        for days in (-30, 0):
            today = datetime.date(2026, 1, 1)
            # last FAI chosen so the due date lands `days` days from
            # today (on or before today for days <= 0).
            last = today - datetime.timedelta(days=365 - days)
            result = frl.revalidation_status(last, today)
            self.assertEqual(result["status"], "due")
            self.assertEqual(result["days_remaining"], days)

    def test_triggering_change_always_demands_revalidation(self):
        """Every type that triggers revalidation must yield the
        revalidation-required verdict."""
        for ctype in frl.TRIGGER_TYPES:
            self.assertEqual(frl.change_trigger_verdict(ctype), "revalidation-required")


if __name__ == "__main__":
    unittest.main(verbosity=2)
