"""Contract tests for the outgassing instrument calibration logic.

The cases follow the instrument set onto the run: the calendar arithmetic that
fixes when a calibration runs out, the days left on the run day, the ratio
between the tolerance an instrument polices and the uncertainty it carries,
the balance division against the mass change being looked for, and the
quadrature budget the whole chain comes to.
"""

import unittest
from datetime import date

from q7002_equipment_calibration_logic import (
    DEFAULT_DUE_SOON_DAYS,
    DEFAULT_MIN_UNCERTAINTY_RATIO,
    DEFAULT_RESOLUTION_DIVISOR,
    add_months,
    assess_equipment_calibration,
    balance_readability_finding,
    calibration_due_day,
    calibration_findings,
    capability_findings,
    combined_uncertainty,
    days_remaining,
    parse_day,
    test_uncertainty_ratio,
)


def _instrument(identifier="balance", **overrides):
    record = {
        "id": identifier,
        "last_calibration": "2026-03-01",
        "interval_months": 12,
        "tolerance": 1.0,
        "uncertainty": 0.1,
    }
    record.update(overrides)
    return record


class ParseDayTests(unittest.TestCase):
    def test_iso_day_parses(self):
        self.assertEqual(parse_day("2026-03-01"), date(2026, 3, 1))

    def test_date_passes_through(self):
        self.assertEqual(parse_day(date(2026, 3, 1)), date(2026, 3, 1))

    def test_leap_day_accepted(self):
        self.assertEqual(parse_day("2024-02-29"), date(2024, 2, 29))

    def test_non_leap_day_rejected(self):
        with self.assertRaises(ValueError):
            parse_day("2026-02-29")

    def test_month_thirteen_rejected(self):
        with self.assertRaises(ValueError):
            parse_day("2026-13-01")

    def test_free_text_rejected(self):
        with self.assertRaises(ValueError):
            parse_day("March 2026")


class AddMonthsTests(unittest.TestCase):
    def test_twelve_months_is_a_year(self):
        self.assertEqual(add_months("2026-03-01", 12), date(2027, 3, 1))

    def test_month_end_falls_back_to_a_short_month(self):
        self.assertEqual(add_months("2026-01-31", 1), date(2026, 2, 28))

    def test_month_end_reaches_a_leap_day(self):
        self.assertEqual(add_months("2024-01-31", 1), date(2024, 2, 29))

    def test_crossing_the_year_boundary(self):
        self.assertEqual(add_months("2026-11-15", 3), date(2027, 2, 15))

    def test_zero_months_is_the_same_day(self):
        self.assertEqual(add_months("2026-03-01", 0), date(2026, 3, 1))

    def test_negative_months_rejected(self):
        with self.assertRaises(ValueError):
            add_months("2026-03-01", -1)

    def test_non_integer_months_rejected(self):
        with self.assertRaises(ValueError):
            add_months("2026-03-01", 1.5)


class DueDayTests(unittest.TestCase):
    def test_due_day_is_the_interval_later(self):
        self.assertEqual(calibration_due_day("2026-03-01", 12), date(2027, 3, 1))

    def test_zero_interval_rejected(self):
        with self.assertRaises(ValueError):
            calibration_due_day("2026-03-01", 0)

    def test_days_remaining_is_signed(self):
        self.assertEqual(days_remaining("2026-03-10", "2026-03-01"), 9)
        self.assertEqual(days_remaining("2026-03-01", "2026-03-10"), -9)


class CalibrationCurrencyTests(unittest.TestCase):
    def test_current_instrument_is_silent(self):
        self.assertEqual(calibration_findings([_instrument()], "2026-06-01"), [])

    def test_expired_instrument_is_flagged(self):
        notes = calibration_findings([_instrument()], "2027-06-01")
        self.assertEqual(len(notes), 1)
        self.assertIn("ran out of calibration", notes[0])

    def test_instrument_due_soon_is_flagged(self):
        notes = calibration_findings([_instrument()], "2027-02-20")
        self.assertEqual(len(notes), 1)
        self.assertIn("day(s) of calibration left", notes[0])

    def test_the_due_soon_window_is_inclusive(self):
        run = "2027-03-01"
        due = calibration_due_day("2026-03-01", 12)
        self.assertEqual(days_remaining(due, run), 0)
        self.assertEqual(len(calibration_findings([_instrument()], run)), 1)

    def test_each_instrument_is_reported(self):
        notes = calibration_findings(
            [_instrument("balance"), _instrument("gauge", last_calibration="2020-01-01")],
            "2027-06-01",
        )
        self.assertEqual(len(notes), 2)

    def test_empty_instrument_set_rejected(self):
        with self.assertRaises(ValueError):
            calibration_findings([], "2026-06-01")

    def test_missing_field_rejected(self):
        item = _instrument()
        del item["interval_months"]
        with self.assertRaises(ValueError):
            calibration_findings([item], "2026-06-01")

    def test_negative_window_rejected(self):
        with self.assertRaises(ValueError):
            calibration_findings([_instrument()], "2026-06-01", -5)


class CapabilityTests(unittest.TestCase):
    def test_ratio_is_tolerance_over_uncertainty(self):
        self.assertAlmostEqual(test_uncertainty_ratio(1.0, 0.25), 4.0)

    def test_capable_instrument_is_silent(self):
        self.assertEqual(capability_findings([_instrument()]), [])

    def test_ratio_exactly_on_the_floor_is_accepted(self):
        item = _instrument(tolerance=1.0, uncertainty=0.25)
        self.assertAlmostEqual(
            test_uncertainty_ratio(1.0, 0.25), DEFAULT_MIN_UNCERTAINTY_RATIO, places=9
        )
        self.assertEqual(capability_findings([item]), [])

    def test_coarse_instrument_is_flagged(self):
        item = _instrument("thermocouple", tolerance=1.0, uncertainty=0.8)
        notes = capability_findings([item])
        self.assertEqual(len(notes), 1)
        self.assertIn("thermocouple", notes[0])

    def test_zero_uncertainty_rejected(self):
        with self.assertRaises(ValueError):
            test_uncertainty_ratio(1.0, 0.0)

    def test_negative_tolerance_rejected(self):
        with self.assertRaises(ValueError):
            test_uncertainty_ratio(-1.0, 0.1)


class ReadabilityTests(unittest.TestCase):
    def test_fine_balance_is_silent(self):
        self.assertIsNone(balance_readability_finding(0.000001, 0.5))

    def test_division_exactly_at_the_limit_is_accepted(self):
        change = 0.5
        readability = change / DEFAULT_RESOLUTION_DIVISOR
        self.assertIsNone(balance_readability_finding(readability, change))

    def test_coarse_balance_is_flagged(self):
        note = balance_readability_finding(0.1, 0.5)
        self.assertIn("cannot resolve", note)

    def test_zero_division_rejected(self):
        with self.assertRaises(ValueError):
            balance_readability_finding(0.0, 0.5)

    def test_zero_change_rejected(self):
        with self.assertRaises(ValueError):
            balance_readability_finding(0.001, 0.0)


class BudgetTests(unittest.TestCase):
    def test_quadrature_of_three_and_four_is_five(self):
        self.assertAlmostEqual(combined_uncertainty([3.0, 4.0]), 5.0, places=12)

    def test_single_component_is_itself(self):
        self.assertAlmostEqual(combined_uncertainty([0.25]), 0.25, places=12)

    def test_budget_is_below_the_arithmetic_sum(self):
        self.assertLess(combined_uncertainty([3.0, 4.0]), 7.0)

    def test_zero_component_is_allowed(self):
        self.assertAlmostEqual(combined_uncertainty([0.0, 4.0]), 4.0, places=12)

    def test_negative_component_rejected(self):
        with self.assertRaises(ValueError):
            combined_uncertainty([-1.0, 4.0])

    def test_empty_budget_rejected(self):
        with self.assertRaises(ValueError):
            combined_uncertainty([])


class AssessmentTests(unittest.TestCase):
    def _spec(self, **overrides):
        spec = {
            "instruments": [
                _instrument("balance", tolerance=0.002, uncertainty=0.0004),
                _instrument("specimen-thermocouple", tolerance=1.0, uncertainty=0.2),
                _instrument("collector-thermocouple", tolerance=1.0, uncertainty=0.2),
                _instrument("pressure-gauge", tolerance=0.0005, uncertainty=0.0001),
            ],
            "run_day": "2026-06-01",
            "balance_readability_mg": 0.000001,
            "resolved_mass_change_mg": 0.5,
        }
        spec.update(overrides)
        return spec

    def test_ready_instrument_set_is_usable(self):
        result = assess_equipment_calibration(self._spec())
        self.assertTrue(result["usable"])
        self.assertEqual(result["findings"], [])

    def test_ratios_are_reported_per_instrument(self):
        result = assess_equipment_calibration(self._spec())
        self.assertAlmostEqual(result["uncertainty_ratios"]["balance"], 5.0, places=9)

    def test_days_to_due_are_reported(self):
        result = assess_equipment_calibration(self._spec())
        self.assertEqual(result["days_to_due"]["pressure-gauge"], 273)

    def test_expired_thermocouple_makes_the_set_unusable(self):
        spec = self._spec()
        spec["instruments"][1]["last_calibration"] = "2024-01-01"
        result = assess_equipment_calibration(spec)
        self.assertFalse(result["usable"])
        self.assertTrue(any("specimen-thermocouple" in note for note in result["findings"]))

    def test_coarse_balance_division_is_reported(self):
        result = assess_equipment_calibration(self._spec(balance_readability_mg=0.2))
        self.assertFalse(result["usable"])
        self.assertTrue(any("cannot resolve" in note for note in result["findings"]))

    def test_budget_is_computed_when_components_are_given(self):
        result = assess_equipment_calibration(
            self._spec(budget_components=[0.0003, 0.0004])
        )
        self.assertAlmostEqual(result["combined_uncertainty"], 0.0005, places=12)

    def test_budget_beyond_its_tolerance_is_flagged(self):
        result = assess_equipment_calibration(
            self._spec(budget_components=[0.0003, 0.0004], budget_tolerance=0.001)
        )
        self.assertFalse(result["usable"])
        self.assertTrue(
            any("combined measurement uncertainty" in note for note in result["findings"])
        )

    def test_budget_is_absent_when_no_components_are_given(self):
        result = assess_equipment_calibration(self._spec())
        self.assertIsNone(result["combined_uncertainty"])

    def test_missing_key_rejected(self):
        spec = self._spec()
        del spec["run_day"]
        with self.assertRaises(ValueError):
            assess_equipment_calibration(spec)

    def test_due_soon_window_can_be_narrowed(self):
        spec = self._spec(run_day="2027-02-20")
        wide = assess_equipment_calibration(spec)
        narrow = assess_equipment_calibration(dict(spec, due_soon_days=1))
        self.assertGreater(len(wide["findings"]), len(narrow["findings"]))
        self.assertEqual(DEFAULT_DUE_SOON_DAYS, 30)


if __name__ == "__main__":
    unittest.main()
