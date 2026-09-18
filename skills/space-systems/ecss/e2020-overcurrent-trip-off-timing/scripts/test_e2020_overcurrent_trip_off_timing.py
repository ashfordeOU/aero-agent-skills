"""Contract tests for the clause 5.2.4.1.1 switch-off timing assessment.

Every workflow step the SKILL.md sets out is exercised here, together with
the stop conditions the gate 3 contract reviews: a table that reverses or
buys time at a harder overcurrent, a measurement with no declared limit to
index it against, a ratio below the first row and past the last, a
switch-off that never happened, and a trip landing exactly on each edge of
its interpolated window.
"""

import unittest

from e2020_overcurrent_trip_off_timing_logic import (
    CURRENT_LIMIT_NOT_ESTABLISHED,
    DID_NOT_SWITCH_OFF,
    TRIP_NOT_REQUIRED,
    TRIP_TIME_TABLE_NOT_ESTABLISHED,
    TRIP_TIMING_OUT_OF_BAND,
    TRIP_TIMING_WITHIN_BAND,
    TRIPPED_TOO_EARLY,
    TRIPPED_TOO_LATE,
    WITHIN_TRIP_TIME_BAND,
    assess_overcurrent_trip_timing,
    bracket_rows,
    deviation_fraction,
    measurement_verdicts,
    overcurrent_ratio,
    switch_off_verdict,
    trip_time_band,
    validate_measurement,
    validate_trip_time_row,
    validate_trip_time_table,
    worst_measurement,
)

LIMIT_A = 2.0


def _table():
    return [
        {"current_ratio": 1.15, "min_trip_time_s": 0.5, "max_trip_time_s": 10.0},
        {"current_ratio": 1.50, "min_trip_time_s": 0.1, "max_trip_time_s": 2.0},
        {"current_ratio": 2.00, "min_trip_time_s": 0.01, "max_trip_time_s": 0.2},
        {"current_ratio": 4.00, "min_trip_time_s": 0.001, "max_trip_time_s": 0.02},
    ]


def _event(**overrides):
    event = {
        "id": "oc-01",
        "measured_current_a": 3.0,
        "switched_off": True,
        "measured_trip_time_s": 0.5,
    }
    event.update(overrides)
    return event


def _case(**overrides):
    case = {
        "trip_time_table": _table(),
        "limit_current_a": LIMIT_A,
        "measurements": [_event()],
    }
    case.update(overrides)
    return case


class TableTests(unittest.TestCase):
    def test_the_reference_table_validates(self):
        rows = validate_trip_time_table(_table())
        self.assertEqual(len(rows), 4)

    def test_a_single_row_table_is_refused(self):
        with self.assertRaises(ValueError):
            validate_trip_time_table(_table()[:1])

    def test_a_row_at_or_below_the_limit_is_refused(self):
        with self.assertRaises(ValueError):
            validate_trip_time_row(
                {"current_ratio": 1.0, "min_trip_time_s": 1.0, "max_trip_time_s": 2.0}
            )

    def test_a_row_whose_maximum_undercuts_its_minimum_is_refused(self):
        with self.assertRaises(ValueError):
            validate_trip_time_row(
                {"current_ratio": 1.5, "min_trip_time_s": 2.0, "max_trip_time_s": 1.0}
            )

    def test_a_table_that_reverses_in_ratio_is_refused(self):
        table = _table()
        table[2]["current_ratio"] = 1.2
        with self.assertRaises(ValueError):
            validate_trip_time_table(table)

    def test_a_harder_overcurrent_cannot_buy_more_time(self):
        table = _table()
        table[2]["max_trip_time_s"] = 5.0
        with self.assertRaises(ValueError):
            validate_trip_time_table(table)

    def test_a_non_sequence_table_is_refused(self):
        with self.assertRaises(ValueError):
            validate_trip_time_table({"current_ratio": 1.5})


class BandTests(unittest.TestCase):
    def test_the_ratio_is_the_current_over_the_declared_limit(self):
        self.assertAlmostEqual(overcurrent_ratio(3.0, LIMIT_A), 1.5, places=9)

    def test_a_zero_limit_is_refused(self):
        with self.assertRaises(ValueError):
            overcurrent_ratio(3.0, 0.0)

    def test_a_ratio_below_the_table_demands_no_switch_off(self):
        self.assertIsNone(bracket_rows(1.05, _table()))
        self.assertIsNone(trip_time_band(1.05, _table()))

    def test_a_ratio_on_a_tabulated_row_returns_that_row(self):
        band = trip_time_band(1.5, _table())
        self.assertAlmostEqual(band["min_trip_time_s"], 0.1, places=9)
        self.assertAlmostEqual(band["max_trip_time_s"], 2.0, places=9)
        self.assertFalse(band["clamped_to_last_row"])

    def test_a_ratio_between_rows_is_interpolated(self):
        band = trip_time_band(1.75, _table())
        self.assertAlmostEqual(band["min_trip_time_s"], 0.055, places=9)
        self.assertAlmostEqual(band["max_trip_time_s"], 1.1, places=9)

    def test_a_ratio_past_the_table_is_held_at_the_last_row(self):
        band = trip_time_band(6.0, _table())
        self.assertAlmostEqual(band["min_trip_time_s"], 0.001, places=9)
        self.assertAlmostEqual(band["max_trip_time_s"], 0.02, places=9)
        self.assertTrue(band["clamped_to_last_row"])

    def test_a_deviation_is_zero_inside_the_window(self):
        band = trip_time_band(1.5, _table())
        self.assertAlmostEqual(deviation_fraction(0.5, band), 0.0, places=12)

    def test_a_late_deviation_is_measured_against_the_maximum(self):
        band = trip_time_band(1.5, _table())
        self.assertAlmostEqual(deviation_fraction(3.0, band), 0.5, places=9)

    def test_an_early_deviation_is_measured_against_the_minimum(self):
        band = trip_time_band(1.5, _table())
        self.assertAlmostEqual(deviation_fraction(0.05, band), 0.5, places=9)


class MeasurementTests(unittest.TestCase):
    def test_a_blank_event_id_is_refused(self):
        with self.assertRaises(ValueError):
            validate_measurement(_event(id="  "))

    def test_a_non_boolean_switch_off_flag_is_refused(self):
        with self.assertRaises(ValueError):
            validate_measurement(_event(switched_off="yes"))

    def test_a_trip_time_on_an_event_that_never_tripped_is_refused(self):
        with self.assertRaises(ValueError):
            validate_measurement(_event(switched_off=False))

    def test_an_event_that_tripped_needs_a_trip_time(self):
        event = _event()
        del event["measured_trip_time_s"]
        with self.assertRaises(ValueError):
            validate_measurement(event)

    def test_a_duplicate_event_id_is_refused(self):
        with self.assertRaises(ValueError):
            measurement_verdicts([_event(), _event()], LIMIT_A, _table())

    def test_an_empty_event_list_is_refused(self):
        with self.assertRaises(ValueError):
            measurement_verdicts([], LIMIT_A, _table())


class VerdictTests(unittest.TestCase):
    def test_a_trip_inside_the_window_is_compliant(self):
        verdict = switch_off_verdict(_event(), LIMIT_A, _table())
        self.assertEqual(verdict["outcome"], WITHIN_TRIP_TIME_BAND)
        self.assertTrue(verdict["compliant"])

    def test_a_trip_exactly_on_the_minimum_is_compliant(self):
        verdict = switch_off_verdict(
            _event(measured_trip_time_s=0.1), LIMIT_A, _table()
        )
        self.assertEqual(verdict["outcome"], WITHIN_TRIP_TIME_BAND)
        self.assertAlmostEqual(verdict["deviation_fraction"], 0.0, places=12)

    def test_a_trip_exactly_on_the_maximum_is_compliant(self):
        verdict = switch_off_verdict(
            _event(measured_trip_time_s=2.0), LIMIT_A, _table()
        )
        self.assertEqual(verdict["outcome"], WITHIN_TRIP_TIME_BAND)

    def test_a_trip_before_the_minimum_is_too_early(self):
        verdict = switch_off_verdict(
            _event(measured_trip_time_s=0.02), LIMIT_A, _table()
        )
        self.assertEqual(verdict["outcome"], TRIPPED_TOO_EARLY)
        self.assertFalse(verdict["compliant"])

    def test_a_trip_after_the_maximum_is_too_late(self):
        verdict = switch_off_verdict(
            _event(measured_trip_time_s=4.0), LIMIT_A, _table()
        )
        self.assertEqual(verdict["outcome"], TRIPPED_TOO_LATE)

    def test_an_event_below_the_table_needs_no_trip(self):
        verdict = switch_off_verdict(
            _event(measured_current_a=2.1, switched_off=False, measured_trip_time_s=None),
            LIMIT_A,
            _table(),
        )
        self.assertEqual(verdict["outcome"], TRIP_NOT_REQUIRED)
        self.assertTrue(verdict["compliant"])

    def test_a_limiter_that_never_opened_is_non_compliant(self):
        verdict = switch_off_verdict(
            _event(switched_off=False, measured_trip_time_s=None), LIMIT_A, _table()
        )
        self.assertEqual(verdict["outcome"], DID_NOT_SWITCH_OFF)
        self.assertFalse(verdict["compliant"])


class AssessmentTests(unittest.TestCase):
    def test_the_nominal_case_is_within_the_band(self):
        result = assess_overcurrent_trip_timing(_case())
        self.assertEqual(result["verdict"], TRIP_TIMING_WITHIN_BAND)
        self.assertEqual(result["findings"], [])

    def test_a_missing_table_closes_the_assessment(self):
        case = _case()
        del case["trip_time_table"]
        result = assess_overcurrent_trip_timing(case)
        self.assertEqual(result["verdict"], TRIP_TIME_TABLE_NOT_ESTABLISHED)

    def test_a_missing_current_limit_closes_the_assessment(self):
        case = _case()
        del case["limit_current_a"]
        result = assess_overcurrent_trip_timing(case)
        self.assertEqual(result["verdict"], CURRENT_LIMIT_NOT_ESTABLISHED)

    def test_a_late_event_is_reported_out_of_band(self):
        result = assess_overcurrent_trip_timing(
            _case(measurements=[_event(measured_trip_time_s=6.0)])
        )
        self.assertEqual(result["verdict"], TRIP_TIMING_OUT_OF_BAND)
        self.assertIn("oc-01", result["findings"][0])

    def test_the_worst_event_is_the_widest_relative_miss(self):
        result = assess_overcurrent_trip_timing(
            _case(
                measurements=[
                    _event(id="oc-01", measured_trip_time_s=3.0),
                    _event(id="oc-02", measured_trip_time_s=8.0),
                ]
            )
        )
        self.assertEqual(result["worst_measurement_id"], "oc-02")
        self.assertAlmostEqual(result["worst_deviation_fraction"], 3.0, places=9)

    def test_an_event_past_the_table_is_advised(self):
        result = assess_overcurrent_trip_timing(
            _case(
                measurements=[
                    _event(measured_current_a=12.0, measured_trip_time_s=0.01)
                ]
            )
        )
        self.assertTrue(
            any("past the last tabulated row" in note for note in result["advisories"])
        )

    def test_a_trip_below_the_table_is_advised_not_failed(self):
        result = assess_overcurrent_trip_timing(
            _case(
                measurements=[
                    _event(measured_current_a=2.1, measured_trip_time_s=4.0)
                ]
            )
        )
        self.assertEqual(result["verdict"], TRIP_TIMING_WITHIN_BAND)
        self.assertTrue(
            any("no switch-off was demanded" in note for note in result["advisories"])
        )

    def test_a_limiter_left_conducting_is_reported(self):
        result = assess_overcurrent_trip_timing(
            _case(
                measurements=[
                    _event(switched_off=False, measured_trip_time_s=None)
                ]
            )
        )
        self.assertEqual(result["verdict"], TRIP_TIMING_OUT_OF_BAND)
        self.assertIn("left the limiter conducting", result["findings"][0])

    def test_the_worst_measurement_helper_refuses_an_empty_set(self):
        with self.assertRaises(ValueError):
            worst_measurement([])

    def test_a_non_mapping_case_is_refused(self):
        with self.assertRaises(ValueError):
            assess_overcurrent_trip_timing(["trip_time_table"])


if __name__ == "__main__":
    unittest.main()
