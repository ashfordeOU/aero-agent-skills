"""Contract tests for the ECSS-Q-ST-70-01C cleanliness equipment-control logic."""

import datetime
import math
import unittest

from q7001_measurement_equipment_control_logic import (
    DUE_SOON_DAYS,
    MIN_SENSITIVITY_RATIO,
    MIN_TOLERANCE_UNCERTAINTY_RATIO,
    add_calendar_months,
    assess_equipment_set,
    assess_instrument,
    calibration_due_date,
    calibration_status,
    combine_uncertainty,
    days_until_due,
    sensitivity_is_adequate,
    sensitivity_ratio,
    sizing_error_is_acceptable,
    tolerance_uncertainty_ratio,
)


def instrument(**overrides):
    record = {
        "id": "NVR-BAL-01",
        "last_calibration": "2026-03-15",
        "interval_months": 12,
        "required_value": 1.0,
        "detection_floor": 0.1,
    }
    record.update(overrides)
    return record


class CalendarTests(unittest.TestCase):
    def test_twelve_months_lands_on_the_same_day(self):
        self.assertEqual(
            add_calendar_months("2026-03-15", 12), datetime.date(2027, 3, 15)
        )

    def test_month_end_is_clamped_into_a_short_month(self):
        self.assertEqual(
            add_calendar_months("2026-01-31", 1), datetime.date(2026, 2, 28)
        )

    def test_leap_year_february_takes_the_twenty_ninth(self):
        self.assertEqual(
            add_calendar_months("2028-01-31", 1), datetime.date(2028, 2, 29)
        )

    def test_december_rolls_the_year(self):
        self.assertEqual(
            add_calendar_months("2026-12-10", 1), datetime.date(2027, 1, 10)
        )

    def test_a_date_object_is_accepted(self):
        self.assertEqual(
            add_calendar_months(datetime.date(2026, 6, 1), 6),
            datetime.date(2026, 12, 1),
        )

    def test_zero_months_rejected(self):
        with self.assertRaises(ValueError):
            add_calendar_months("2026-03-15", 0)

    def test_non_integer_months_rejected(self):
        with self.assertRaises(ValueError):
            add_calendar_months("2026-03-15", 12.5)

    def test_malformed_date_rejected(self):
        with self.assertRaises(ValueError):
            add_calendar_months("15/03/2026", 12)

    def test_due_date_is_the_month_walk(self):
        self.assertEqual(
            calibration_due_date("2026-03-15", 6), datetime.date(2026, 9, 15)
        )


class CurrencyTests(unittest.TestCase):
    def test_days_left_counted_to_the_reference_date(self):
        self.assertEqual(days_until_due("2026-03-15", 12, "2027-03-05"), 10)

    def test_days_left_is_negative_after_expiry(self):
        self.assertEqual(days_until_due("2026-03-15", 12, "2027-03-25"), -10)

    def test_status_in_date_well_before_expiry(self):
        self.assertEqual(calibration_status("2026-03-15", 12, "2026-06-01"), "in-date")

    def test_status_due_soon_inside_the_window(self):
        self.assertEqual(
            calibration_status("2026-03-15", 12, "2027-03-05"), "due-soon"
        )

    def test_status_overdue_after_expiry(self):
        self.assertEqual(
            calibration_status("2026-03-15", 12, "2027-04-01"), "overdue"
        )

    def test_status_on_the_due_day_itself_is_due_soon(self):
        self.assertEqual(
            calibration_status("2026-03-15", 12, "2027-03-15"), "due-soon"
        )

    def test_due_soon_window_boundary(self):
        reference = datetime.date(2027, 3, 15) - datetime.timedelta(days=DUE_SOON_DAYS)
        self.assertEqual(
            calibration_status("2026-03-15", 12, reference), "due-soon"
        )


class SensitivityTests(unittest.TestCase):
    def test_ratio_is_required_over_floor(self):
        self.assertAlmostEqual(sensitivity_ratio(1.0, 0.1), 10.0, places=9)

    def test_adequate_when_well_clear(self):
        self.assertTrue(sensitivity_is_adequate(1.0, 0.1))

    def test_inadequate_when_the_floor_is_close(self):
        self.assertFalse(sensitivity_is_adequate(1.0, 0.5))

    def test_ratio_exactly_at_the_minimum_is_adequate(self):
        floor = 1.0 / MIN_SENSITIVITY_RATIO
        self.assertTrue(sensitivity_is_adequate(1.0, floor))

    def test_declared_minimum_ratio_is_used(self):
        self.assertFalse(sensitivity_is_adequate(1.0, 0.1, 20.0))

    def test_zero_floor_rejected(self):
        with self.assertRaises(ValueError):
            sensitivity_ratio(1.0, 0.0)

    def test_negative_required_value_rejected(self):
        with self.assertRaises(ValueError):
            sensitivity_ratio(-1.0, 0.1)


class UncertaintyTests(unittest.TestCase):
    def test_quadrature_of_a_three_four_pair(self):
        self.assertAlmostEqual(combine_uncertainty([3.0, 4.0]), 5.0, places=9)

    def test_single_component_is_itself(self):
        self.assertAlmostEqual(combine_uncertainty([0.2]), 0.2, places=9)

    def test_quadrature_is_below_the_arithmetic_sum(self):
        self.assertLess(combine_uncertainty([3.0, 4.0]), 7.0)

    def test_zero_components_are_allowed_inside_the_set(self):
        self.assertAlmostEqual(combine_uncertainty([0.0, 0.5]), 0.5, places=9)

    def test_empty_component_set_rejected(self):
        with self.assertRaises(ValueError):
            combine_uncertainty([])

    def test_negative_component_rejected(self):
        with self.assertRaises(ValueError):
            combine_uncertainty([0.2, -0.1])

    def test_tolerance_ratio_is_the_quotient(self):
        self.assertAlmostEqual(tolerance_uncertainty_ratio(1.0, 0.2), 5.0, places=9)

    def test_zero_uncertainty_ratio_rejected(self):
        with self.assertRaises(ValueError):
            tolerance_uncertainty_ratio(1.0, 0.0)


class SizingTests(unittest.TestCase):
    def test_small_sizing_error_is_acceptable(self):
        self.assertTrue(sizing_error_is_acceptable(0.2, 5.0))

    def test_large_sizing_error_is_refused(self):
        self.assertFalse(sizing_error_is_acceptable(1.5, 5.0))

    def test_error_exactly_at_the_fraction_is_acceptable(self):
        self.assertTrue(sizing_error_is_acceptable(0.5, 5.0))

    def test_negative_sizing_error_rejected(self):
        with self.assertRaises(ValueError):
            sizing_error_is_acceptable(-0.1, 5.0)

    def test_zero_bin_width_rejected(self):
        with self.assertRaises(ValueError):
            sizing_error_is_acceptable(0.1, 0.0)


class AssessInstrumentTests(unittest.TestCase):
    def test_healthy_instrument_is_usable(self):
        entry = assess_instrument(instrument(), "2026-06-01")
        self.assertTrue(entry["usable"])
        self.assertEqual(entry["calibration_status"], "in-date")
        self.assertEqual(entry["findings"], [])

    def test_overdue_instrument_is_blocked(self):
        entry = assess_instrument(instrument(), "2027-05-01")
        self.assertFalse(entry["usable"])
        self.assertTrue(any("expired" in item for item in entry["findings"]))

    def test_due_soon_is_reported_without_hiding_the_days(self):
        entry = assess_instrument(instrument(), "2027-03-05")
        self.assertEqual(entry["calibration_status"], "due-soon")
        self.assertEqual(entry["days_until_due"], 10)

    def test_coarse_floor_blocks_the_instrument(self):
        entry = assess_instrument(
            instrument(detection_floor=0.9), "2026-06-01"
        )
        self.assertFalse(entry["sensitivity_adequate"])
        self.assertFalse(entry["usable"])

    def test_uncertainty_budget_is_combined_when_given(self):
        entry = assess_instrument(
            instrument(uncertainty_components=[0.03, 0.04]), "2026-06-01"
        )
        self.assertAlmostEqual(entry["combined_uncertainty"], 0.05, places=9)

    def test_low_tolerance_to_uncertainty_ratio_is_flagged(self):
        entry = assess_instrument(
            instrument(uncertainty_components=[0.3, 0.4], tolerance=1.0),
            "2026-06-01",
        )
        self.assertAlmostEqual(entry["tolerance_uncertainty_ratio"], 2.0, places=9)
        self.assertFalse(entry["usable"])

    def test_adequate_tolerance_to_uncertainty_ratio_passes(self):
        entry = assess_instrument(
            instrument(uncertainty_components=[0.1], tolerance=1.0), "2026-06-01"
        )
        self.assertAlmostEqual(
            entry["tolerance_uncertainty_ratio"], 10.0, places=9
        )
        self.assertTrue(entry["usable"])

    def test_ratio_at_the_minimum_is_not_flagged(self):
        entry = assess_instrument(
            instrument(
                uncertainty_components=[1.0 / MIN_TOLERANCE_UNCERTAINTY_RATIO],
                tolerance=1.0,
            ),
            "2026-06-01",
        )
        self.assertTrue(entry["usable"])

    def test_counter_sizing_error_is_graded(self):
        entry = assess_instrument(
            instrument(id="OPC-01", sizing_error_um=1.5, smallest_bin_um=5.0),
            "2026-06-01",
        )
        self.assertFalse(entry["sizing_acceptable"])
        self.assertFalse(entry["usable"])

    def test_sizing_error_without_a_bin_width_rejected(self):
        with self.assertRaises(ValueError):
            assess_instrument(instrument(sizing_error_um=1.5), "2026-06-01")

    def test_untraceable_instrument_is_blocked(self):
        entry = assess_instrument(instrument(traceable=False), "2026-06-01")
        self.assertFalse(entry["usable"])
        self.assertTrue(any("traceable" in item for item in entry["findings"]))

    def test_missing_key_rejected(self):
        record = instrument()
        del record["detection_floor"]
        with self.assertRaises(ValueError):
            assess_instrument(record, "2026-06-01")

    def test_empty_identifier_rejected(self):
        with self.assertRaises(ValueError):
            assess_instrument(instrument(id="  "), "2026-06-01")

    def test_non_mapping_instrument_rejected(self):
        with self.assertRaises(ValueError):
            assess_instrument(["NVR-BAL-01"], "2026-06-01")


class AssessSetTests(unittest.TestCase):
    def test_clean_set_is_usable(self):
        summary = assess_equipment_set(
            {
                "instruments": [instrument(), instrument(id="OPC-01")],
                "reference_date": "2026-06-01",
            }
        )
        self.assertTrue(summary["set_usable"])
        self.assertAlmostEqual(summary["usable_fraction"], 1.0, places=9)

    def test_one_blocked_instrument_blocks_the_set(self):
        summary = assess_equipment_set(
            {
                "instruments": [
                    instrument(),
                    instrument(id="OPC-01", detection_floor=0.9),
                ],
                "reference_date": "2026-06-01",
            }
        )
        self.assertFalse(summary["set_usable"])
        self.assertEqual(summary["blocked"], ["OPC-01"])
        self.assertAlmostEqual(summary["usable_fraction"], 0.5, places=9)

    def test_findings_are_aggregated(self):
        summary = assess_equipment_set(
            {
                "instruments": [
                    instrument(traceable=False),
                    instrument(id="OPC-01", detection_floor=0.9),
                ],
                "reference_date": "2026-06-01",
            }
        )
        self.assertEqual(len(summary["findings"]), 2)

    def test_duplicate_instrument_id_rejected(self):
        with self.assertRaises(ValueError):
            assess_equipment_set(
                {
                    "instruments": [instrument(), instrument()],
                    "reference_date": "2026-06-01",
                }
            )

    def test_empty_instrument_set_rejected(self):
        with self.assertRaises(ValueError):
            assess_equipment_set(
                {"instruments": [], "reference_date": "2026-06-01"}
            )

    def test_missing_reference_date_rejected(self):
        with self.assertRaises(ValueError):
            assess_equipment_set({"instruments": [instrument()]})

    def test_non_mapping_spec_rejected(self):
        with self.assertRaises(ValueError):
            assess_equipment_set(["instruments"])

    def test_quadrature_keeps_the_budget_below_the_sum(self):
        entry = assess_instrument(
            instrument(uncertainty_components=[0.03, 0.04]), "2026-06-01"
        )
        self.assertLess(entry["combined_uncertainty"], 0.07)
        self.assertAlmostEqual(
            entry["combined_uncertainty"], math.hypot(0.03, 0.04), places=12
        )


if __name__ == "__main__":
    unittest.main()
