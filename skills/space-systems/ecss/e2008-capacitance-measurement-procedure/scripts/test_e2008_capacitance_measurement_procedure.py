#!/usr/bin/env python3
"""Contract test for the capacitance equipment preparation leaf (offline)."""

import copy
import unittest

from e2008_capacitance_measurement_procedure_logic import (
    EQUIPMENT_NOT_READY,
    EQUIPMENT_READY,
    MAX_COMPENSATION_FREQUENCY_OFFSET,
    MAX_REFERENCE_DEVIATION_PPM,
    PREPARATION_STEPS,
    assess_equipment_readiness,
    calibration_days_remaining,
    compensation_frequency_offset,
    days_since_calibration,
    incomplete_steps,
    missing_evidence,
    out_of_order_steps,
    preparation_sequence,
    reference_deviation_ppm,
    settling_margin_seconds,
    step_position,
    temperature_within_band,
    unrecognised_steps,
    warm_up_margin_minutes,
)

REFERENCE_NOMINAL_F = 1.0e-9

READY_CASE = {
    "completed_steps": list(PREPARATION_STEPS),
    "calibration_date": "2026-03-10",
    "test_date": "2026-09-14",
    "calibration_interval_days": 365,
    "test_frequency_hz": 1000.0,
    "compensation_frequency_hz": 1000.0,
    "warm_up_elapsed_min": 45.0,
    "warm_up_required_min": 30.0,
    "bias_settling_elapsed_s": 60.0,
    "bias_settling_required_s": 30.0,
    "ambient_temperature_c": 23.0,
    "temperature_band_c": {"minimum_c": 21.0, "maximum_c": 25.0},
    "reference_nominal_f": REFERENCE_NOMINAL_F,
    "reference_measured_f": REFERENCE_NOMINAL_F * 1.0001,
}


def _case(**overrides):
    case = copy.deepcopy(READY_CASE)
    case.update(overrides)
    return case


def _finding_matching(result, fragment):
    return [f for f in result["findings"] if fragment in f]


class SequenceTests(unittest.TestCase):
    def test_the_sequence_warms_the_instrument_before_it_compensates(self):
        self.assertEqual(preparation_sequence()[0], "instrument-warm-up")
        self.assertLess(
            step_position("instrument-warm-up"),
            step_position("fixture-open-compensation"),
        )

    def test_the_reference_check_closes_the_sequence(self):
        self.assertEqual(preparation_sequence()[-1], "reference-capacitor-check")

    def test_open_compensation_precedes_short_and_load(self):
        self.assertLess(
            step_position("fixture-open-compensation"),
            step_position("fixture-short-compensation"),
        )
        self.assertLess(
            step_position("fixture-short-compensation"),
            step_position("fixture-load-compensation"),
        )

    def test_an_unknown_step_name_is_refused(self):
        with self.assertRaises(ValueError):
            step_position("coffee-break")

    def test_a_full_ordered_record_owes_nothing(self):
        record = list(PREPARATION_STEPS)
        self.assertEqual(incomplete_steps(record), ())
        self.assertEqual(out_of_order_steps(record), ())
        self.assertEqual(unrecognised_steps(record), ())

    def test_a_dropped_step_is_reported_as_incomplete(self):
        record = [s for s in PREPARATION_STEPS if s != "reference-capacitor-check"]
        self.assertEqual(incomplete_steps(record), ("reference-capacitor-check",))

    def test_a_swapped_compensation_pair_is_reported_out_of_order(self):
        record = [
            "instrument-warm-up",
            "fixture-short-compensation",
            "fixture-open-compensation",
            "fixture-load-compensation",
            "bias-source-settling",
            "reference-capacitor-check",
        ]
        self.assertEqual(out_of_order_steps(record), ("fixture-open-compensation",))

    def test_a_foreign_entry_is_reported_but_does_not_shift_the_order(self):
        record = list(PREPARATION_STEPS) + ["coffee-break"]
        self.assertEqual(unrecognised_steps(record), ("coffee-break",))
        self.assertEqual(out_of_order_steps(record), ())

    def test_a_record_that_is_not_a_sequence_is_refused(self):
        with self.assertRaises(ValueError):
            incomplete_steps("instrument-warm-up")


class CalibrationTests(unittest.TestCase):
    def test_the_elapsed_days_are_counted_from_the_calibration(self):
        self.assertEqual(days_since_calibration("2026-03-10", "2026-09-14"), 188)

    def test_a_test_date_before_the_calibration_is_refused(self):
        with self.assertRaises(ValueError):
            days_since_calibration("2026-09-14", "2026-03-10")

    def test_a_malformed_date_is_refused(self):
        with self.assertRaises(ValueError):
            days_since_calibration("10-03-2026", "2026-09-14")

    def test_the_remaining_validity_is_the_interval_less_the_elapsed_days(self):
        self.assertEqual(
            calibration_days_remaining("2026-03-10", "2026-09-14", 365), 177
        )

    def test_a_calibration_that_runs_out_on_the_test_date_has_nothing_left(self):
        self.assertEqual(
            calibration_days_remaining("2026-03-10", "2026-09-14", 188), 0
        )

    def test_a_non_integer_calibration_interval_is_refused(self):
        with self.assertRaises(ValueError):
            calibration_days_remaining("2026-03-10", "2026-09-14", 365.0)

    def test_a_zero_calibration_interval_is_refused(self):
        with self.assertRaises(ValueError):
            calibration_days_remaining("2026-03-10", "2026-09-14", 0)


class PreparationTermTests(unittest.TestCase):
    def test_a_compensation_at_the_test_frequency_has_no_offset(self):
        self.assertAlmostEqual(
            compensation_frequency_offset(1000.0, 1000.0), 0.0, places=12
        )

    def test_the_offset_is_measured_against_the_test_frequency(self):
        self.assertAlmostEqual(
            compensation_frequency_offset(1200.0, 1000.0), 0.2, places=12
        )

    def test_a_zero_test_frequency_is_refused(self):
        with self.assertRaises(ValueError):
            compensation_frequency_offset(1000.0, 0.0)

    def test_the_warm_up_margin_is_the_elapsed_less_the_required_time(self):
        self.assertAlmostEqual(warm_up_margin_minutes(45.0, 30.0), 15.0, places=12)

    def test_a_negative_elapsed_warm_up_is_refused(self):
        with self.assertRaises(ValueError):
            warm_up_margin_minutes(-1.0, 30.0)

    def test_the_settling_margin_can_be_negative(self):
        self.assertAlmostEqual(settling_margin_seconds(10.0, 30.0), -20.0, places=12)

    def test_the_reference_deviation_keeps_its_sign(self):
        self.assertAlmostEqual(
            reference_deviation_ppm(REFERENCE_NOMINAL_F * 1.0001, REFERENCE_NOMINAL_F),
            100.0,
            places=6,
        )
        self.assertAlmostEqual(
            reference_deviation_ppm(REFERENCE_NOMINAL_F * 0.9999, REFERENCE_NOMINAL_F),
            -100.0,
            places=6,
        )

    def test_a_zero_nominal_reference_is_refused(self):
        with self.assertRaises(ValueError):
            reference_deviation_ppm(REFERENCE_NOMINAL_F, 0.0)

    def test_the_temperature_band_includes_its_own_edges(self):
        band = {"minimum_c": 21.0, "maximum_c": 25.0}
        self.assertTrue(temperature_within_band(21.0, band))
        self.assertTrue(temperature_within_band(25.0, band))
        self.assertFalse(temperature_within_band(25.5, band))

    def test_an_inverted_temperature_band_is_refused(self):
        with self.assertRaises(ValueError):
            temperature_within_band(23.0, {"minimum_c": 25.0, "maximum_c": 21.0})

    def test_a_temperature_band_that_is_not_a_mapping_is_refused(self):
        with self.assertRaises(ValueError):
            temperature_within_band(23.0, (21.0, 25.0))


class ReadinessTests(unittest.TestCase):
    def test_a_fully_prepared_bench_is_ready(self):
        result = assess_equipment_readiness(_case())
        self.assertTrue(result["ready"])
        self.assertEqual(result["verdict"], EQUIPMENT_READY)
        self.assertEqual(result["findings"], [])

    def test_a_reference_exactly_on_the_ppm_gate_still_passes(self):
        measured = REFERENCE_NOMINAL_F * (1.0 + MAX_REFERENCE_DEVIATION_PPM * 1.0e-6)
        result = assess_equipment_readiness(_case(reference_measured_f=measured))
        self.assertAlmostEqual(
            result["reference_deviation_ppm"], MAX_REFERENCE_DEVIATION_PPM, places=6
        )
        self.assertEqual(_finding_matching(result, "reference capacitor"), [])
        self.assertTrue(result["ready"])

    def test_a_compensation_exactly_on_the_offset_tolerance_still_passes(self):
        compensation = 1000.0 * (1.0 + MAX_COMPENSATION_FREQUENCY_OFFSET)
        result = assess_equipment_readiness(
            _case(compensation_frequency_hz=compensation)
        )
        self.assertAlmostEqual(
            result["compensation_frequency_offset"],
            MAX_COMPENSATION_FREQUENCY_OFFSET,
            places=12,
        )
        self.assertEqual(_finding_matching(result, "compensation was taken"), [])
        self.assertTrue(result["ready"])

    def test_an_expired_calibration_stops_the_bench(self):
        result = assess_equipment_readiness(_case(calibration_interval_days=60))
        self.assertFalse(result["ready"])
        self.assertEqual(result["verdict"], EQUIPMENT_NOT_READY)
        self.assertTrue(_finding_matching(result, "calibration expired"))

    def test_a_compensation_at_another_frequency_stops_the_bench(self):
        result = assess_equipment_readiness(_case(compensation_frequency_hz=1200.0))
        self.assertTrue(_finding_matching(result, "compensation was taken"))

    def test_a_cold_instrument_stops_the_bench(self):
        result = assess_equipment_readiness(_case(warm_up_elapsed_min=10.0))
        self.assertTrue(_finding_matching(result, "warm-up"))
        self.assertAlmostEqual(result["warm_up_margin_minutes"], -20.0, places=12)

    def test_an_unsettled_bias_source_stops_the_bench(self):
        result = assess_equipment_readiness(_case(bias_settling_elapsed_s=10.0))
        self.assertTrue(_finding_matching(result, "settling"))

    def test_an_ambient_outside_the_band_stops_the_bench(self):
        result = assess_equipment_readiness(_case(ambient_temperature_c=30.0))
        self.assertTrue(_finding_matching(result, "ambient"))
        self.assertFalse(result["temperature_within_band"])

    def test_a_reference_drifted_low_is_caught_by_its_magnitude(self):
        result = assess_equipment_readiness(
            _case(reference_measured_f=REFERENCE_NOMINAL_F * 0.999)
        )
        self.assertTrue(_finding_matching(result, "reference capacitor"))
        self.assertLess(result["reference_deviation_ppm"], 0.0)

    def test_an_unfinished_sequence_stops_the_bench(self):
        record = [s for s in PREPARATION_STEPS if s != "bias-source-settling"]
        result = assess_equipment_readiness(_case(completed_steps=record))
        self.assertTrue(_finding_matching(result, "still owed"))

    def test_a_sequence_run_out_of_order_stops_the_bench(self):
        record = [
            "fixture-open-compensation",
            "instrument-warm-up",
            "fixture-short-compensation",
            "fixture-load-compensation",
            "bias-source-settling",
            "reference-capacitor-check",
        ]
        result = assess_equipment_readiness(_case(completed_steps=record))
        self.assertTrue(_finding_matching(result, "out of sequence"))
        self.assertIn("instrument-warm-up", result["out_of_order_steps"])

    def test_a_foreign_step_is_reported_on_the_bench_too(self):
        record = list(PREPARATION_STEPS) + ["coffee-break"]
        result = assess_equipment_readiness(_case(completed_steps=record))
        self.assertTrue(_finding_matching(result, "outside the sequence"))

    def test_missing_evidence_names_the_absent_input(self):
        case = _case()
        del case["reference_nominal_f"]
        self.assertEqual(missing_evidence(case), ("reference_nominal_f",))

    def test_absent_evidence_stops_the_assessment(self):
        case = _case()
        del case["temperature_band_c"]
        with self.assertRaises(ValueError):
            assess_equipment_readiness(case)

    def test_a_case_that_is_not_a_mapping_is_refused(self):
        with self.assertRaises(ValueError):
            assess_equipment_readiness("ready")


if __name__ == "__main__":
    unittest.main()
