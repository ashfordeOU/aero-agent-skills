#!/usr/bin/env python3
"""Contract test for the pulsed-simulator working standard leaf (offline)."""

import copy
import math
import unittest

from e2008_working_standards_with_pulsed_simulators_logic import (
    ADEQUATE_VERDICT,
    DEFAULT_ACCEPTANCE_LIMITS,
    INADEQUATE_VERDICT,
    LOAD_CONNECTIONS,
    STANDARD_GRADES,
    assess_pulsed_response,
    flash_repeatability_percent,
    residual_response_error,
    response_time_constant_us,
    settling_time_us,
    shunt_voltage_fraction,
    shunt_voltage_v,
    validate_acceptance_limits,
    validate_pulse,
    validate_standard,
    window_defects,
)

FAST_STANDARD = {
    "id": "WS-014",
    "grade": "working-standard",
    "load_connection": "four-wire-shunt",
    "capacitance_uf": 0.5,
    "series_resistance_ohm": 0.05,
    "shunt_resistance_ohm": 0.01,
    "short_circuit_current_a": 0.45,
    "open_circuit_voltage_v": 2.6,
}

SLOW_STANDARD = {
    "id": "WS-Slow",
    "grade": "working-standard",
    "load_connection": "four-wire-shunt",
    "capacitance_uf": 500.0,
    "series_resistance_ohm": 0.59,
    "shunt_resistance_ohm": 0.01,
    "short_circuit_current_a": 0.45,
    "open_circuit_voltage_v": 2.6,
}

GOOD_PULSE = {
    "plateau_start_ms": 1.0,
    "plateau_end_ms": 6.0,
    "window_start_ms": 2.0,
    "window_length_ms": 1.0,
    "plateau_ripple_percent": 0.4,
}

STEADY_READINGS = (0.4501, 0.4503, 0.4502)


def _standard(**changes):
    record = copy.deepcopy(FAST_STANDARD)
    record.update(changes)
    return record


def _slow(**changes):
    record = copy.deepcopy(SLOW_STANDARD)
    record.update(changes)
    return record


def _pulse(**changes):
    record = copy.deepcopy(GOOD_PULSE)
    record.update(changes)
    return record


def _defect_names(defects):
    return {entry["defect"] for entry in defects}


class StandardValidationTests(unittest.TestCase):
    def test_a_well_formed_standard_is_normalised(self):
        entry = validate_standard(_standard(id="  WS-014 "))
        self.assertEqual(entry["id"], "WS-014")
        self.assertEqual(entry["load_connection"], "four-wire-shunt")

    def test_the_load_connection_defaults_to_a_four_wire_shunt(self):
        record = _standard()
        del record["load_connection"]
        self.assertEqual(validate_standard(record)["load_connection"], "four-wire-shunt")

    def test_every_declared_connection_and_grade_is_accepted(self):
        for connection in LOAD_CONNECTIONS:
            for grade in STANDARD_GRADES:
                entry = validate_standard(_standard(load_connection=connection, grade=grade))
                self.assertEqual(entry["load_connection"], connection)
                self.assertEqual(entry["grade"], grade)

    def test_an_unknown_load_connection_is_rejected(self):
        with self.assertRaises(ValueError):
            validate_standard(_standard(load_connection="crocodile-clip"))

    def test_zero_capacitance_is_rejected(self):
        with self.assertRaises(ValueError):
            validate_standard(_standard(capacitance_uf=0.0))

    def test_a_negative_series_resistance_is_rejected(self):
        with self.assertRaises(ValueError):
            validate_standard(_standard(series_resistance_ohm=-0.01))

    def test_a_non_mapping_standard_is_rejected(self):
        with self.assertRaises(ValueError):
            validate_standard("WS-014")

    def test_an_empty_identifier_is_rejected(self):
        with self.assertRaises(ValueError):
            validate_standard(_standard(id="   "))


class PulseValidationTests(unittest.TestCase):
    def test_a_well_formed_pulse_derives_its_window_end_and_length(self):
        flash = validate_pulse(GOOD_PULSE)
        self.assertAlmostEqual(flash["window_end_ms"], 3.0, places=9)
        self.assertAlmostEqual(flash["plateau_length_ms"], 5.0, places=9)

    def test_the_ripple_defaults_to_zero_when_not_reported(self):
        record = _pulse()
        del record["plateau_ripple_percent"]
        self.assertAlmostEqual(validate_pulse(record)["plateau_ripple_percent"], 0.0, places=12)

    def test_a_plateau_that_ends_before_it_starts_is_rejected(self):
        with self.assertRaises(ValueError):
            validate_pulse(_pulse(plateau_end_ms=0.5))

    def test_a_window_with_no_length_is_rejected(self):
        with self.assertRaises(ValueError):
            validate_pulse(_pulse(window_length_ms=0.0))

    def test_a_non_mapping_pulse_is_rejected(self):
        with self.assertRaises(ValueError):
            validate_pulse([1.0, 6.0])


class ResponseMathTests(unittest.TestCase):
    def test_the_time_constant_is_the_loop_resistance_times_the_capacitance(self):
        tau = response_time_constant_us(FAST_STANDARD)
        self.assertAlmostEqual(tau, (0.05 + 0.01) * 0.5, places=12)

    def test_the_settling_time_is_the_constant_times_the_log_of_the_tolerance(self):
        tau = response_time_constant_us(FAST_STANDARD)
        settle = settling_time_us(FAST_STANDARD, 0.001)
        self.assertAlmostEqual(settle, tau * math.log(1000.0), places=12)

    def test_a_tighter_tolerance_demands_a_longer_settling(self):
        loose = settling_time_us(FAST_STANDARD, 0.01)
        tight = settling_time_us(FAST_STANDARD, 0.0001)
        self.assertLess(loose, tight)

    def test_a_tolerance_of_one_or_more_is_rejected(self):
        with self.assertRaises(ValueError):
            settling_time_us(FAST_STANDARD, 1.0)

    def test_the_residual_error_at_zero_delay_is_the_whole_step(self):
        self.assertAlmostEqual(residual_response_error(FAST_STANDARD, 0.0), 1.0, places=12)

    def test_the_residual_error_at_the_settling_time_equals_the_tolerance(self):
        settle = settling_time_us(FAST_STANDARD, 0.001)
        self.assertAlmostEqual(residual_response_error(FAST_STANDARD, settle), 0.001, places=9)

    def test_the_residual_error_falls_as_the_delay_grows(self):
        tau = response_time_constant_us(FAST_STANDARD)
        early = residual_response_error(FAST_STANDARD, tau)
        late = residual_response_error(FAST_STANDARD, 5.0 * tau)
        self.assertLess(late, early)

    def test_a_negative_delay_is_rejected(self):
        with self.assertRaises(ValueError):
            residual_response_error(FAST_STANDARD, -1.0)

    def test_the_shunt_voltage_is_the_current_through_the_shunt(self):
        self.assertAlmostEqual(shunt_voltage_v(FAST_STANDARD), 0.0045, places=12)
        self.assertAlmostEqual(
            shunt_voltage_fraction(FAST_STANDARD), 0.0045 / 2.6, places=12
        )

    def test_identical_flashes_spread_by_nothing(self):
        self.assertAlmostEqual(flash_repeatability_percent((0.45, 0.45, 0.45)), 0.0, places=12)

    def test_the_spread_is_the_range_over_the_mean(self):
        spread = flash_repeatability_percent((0.44, 0.46))
        self.assertAlmostEqual(spread, 0.02 / 0.45 * 100.0, places=9)

    def test_a_single_flash_cannot_give_a_spread(self):
        with self.assertRaises(ValueError):
            flash_repeatability_percent((0.45,))

    def test_a_non_positive_reading_is_rejected(self):
        with self.assertRaises(ValueError):
            flash_repeatability_percent((0.45, 0.0))


class LimitValidationTests(unittest.TestCase):
    def test_the_default_limits_validate(self):
        self.assertIs(
            validate_acceptance_limits(DEFAULT_ACCEPTANCE_LIMITS), DEFAULT_ACCEPTANCE_LIMITS
        )

    def test_a_missing_limit_is_rejected(self):
        broken = dict(DEFAULT_ACCEPTANCE_LIMITS)
        del broken["plateau_ripple_percent"]
        with self.assertRaises(ValueError):
            validate_acceptance_limits(broken)

    def test_a_shunt_fraction_of_one_is_rejected(self):
        broken = dict(DEFAULT_ACCEPTANCE_LIMITS)
        broken["shunt_voltage_fraction"] = 1.0
        with self.assertRaises(ValueError):
            validate_acceptance_limits(broken)

    def test_a_non_mapping_limit_set_is_rejected(self):
        with self.assertRaises(ValueError):
            validate_acceptance_limits(["settling_tolerance"])


class WindowDefectTests(unittest.TestCase):
    def test_a_sound_reading_reports_no_defect(self):
        self.assertEqual(window_defects(FAST_STANDARD, GOOD_PULSE), [])

    def test_a_two_wire_shunt_is_reported_on_its_own(self):
        defects = window_defects(_standard(load_connection="two-wire-shunt"), GOOD_PULSE)
        self.assertEqual(_defect_names(defects), {"two-wire-shunt-load"})

    def test_a_window_opening_before_the_plateau_is_reported(self):
        defects = window_defects(FAST_STANDARD, _pulse(window_start_ms=0.5))
        self.assertIn("window-opens-before-plateau", _defect_names(defects))

    def test_a_window_closing_after_the_plateau_is_reported(self):
        defects = window_defects(FAST_STANDARD, _pulse(window_length_ms=6.0))
        self.assertIn("window-closes-after-plateau", _defect_names(defects))

    def test_a_window_ending_exactly_on_the_plateau_edge_is_accepted(self):
        defects = window_defects(FAST_STANDARD, _pulse(window_start_ms=5.0, window_length_ms=1.0))
        self.assertEqual(defects, [])

    def test_a_standard_too_slow_for_the_window_is_reported(self):
        defects = window_defects(SLOW_STANDARD, GOOD_PULSE)
        self.assertIn("settling-not-complete", _defect_names(defects))

    def test_a_plateau_too_short_for_settling_plus_window_is_reported(self):
        defects = window_defects(
            SLOW_STANDARD,
            _pulse(plateau_end_ms=2.0, window_start_ms=1.0, window_length_ms=0.5),
        )
        self.assertIn("plateau-too-short-to-settle", _defect_names(defects))

    def test_a_shunt_lifting_the_cell_off_short_circuit_is_reported(self):
        defects = window_defects(_standard(shunt_resistance_ohm=0.2), GOOD_PULSE)
        self.assertIn("shunt-voltage-off-short-circuit", _defect_names(defects))

    def test_a_rippling_plateau_is_reported(self):
        defects = window_defects(FAST_STANDARD, _pulse(plateau_ripple_percent=2.5))
        self.assertIn("plateau-ripple-out-of-band", _defect_names(defects))

    def test_a_ripple_exactly_on_the_band_is_accepted(self):
        defects = window_defects(FAST_STANDARD, _pulse(plateau_ripple_percent=1.0))
        self.assertEqual(defects, [])


class AssessmentTests(unittest.TestCase):
    def test_a_sound_reading_is_accepted(self):
        result = assess_pulsed_response(
            {"standard": FAST_STANDARD, "pulse": GOOD_PULSE, "flash_readings": STEADY_READINGS}
        )
        self.assertEqual(result["verdict"], ADEQUATE_VERDICT)
        self.assertTrue(result["adequate"])
        self.assertEqual(result["findings"], [])
        self.assertEqual(result["standard"], "WS-014")

    def test_the_assessment_reports_the_settling_it_actually_had(self):
        result = assess_pulsed_response({"standard": FAST_STANDARD, "pulse": GOOD_PULSE})
        self.assertAlmostEqual(result["available_settling_us"], 1000.0, places=9)
        self.assertIsNone(result["flash_repeatability_percent"])

    def test_scattered_flashes_fail_the_assessment(self):
        result = assess_pulsed_response(
            {
                "standard": FAST_STANDARD,
                "pulse": GOOD_PULSE,
                "flash_readings": (0.44, 0.46, 0.45),
            }
        )
        self.assertEqual(result["verdict"], INADEQUATE_VERDICT)
        self.assertTrue(any("repeatability" in f for f in result["findings"]))
        self.assertAlmostEqual(
            result["flash_repeatability_percent"], 0.02 / 0.45 * 100.0, places=9
        )

    def test_a_slow_standard_fails_the_assessment(self):
        result = assess_pulsed_response({"standard": SLOW_STANDARD, "pulse": GOOD_PULSE})
        self.assertEqual(result["verdict"], INADEQUATE_VERDICT)
        self.assertFalse(result["adequate"])
        self.assertTrue(any("settling-not-complete" in f for f in result["findings"]))

    def test_a_slow_standard_still_reports_a_residual_between_zero_and_one(self):
        result = assess_pulsed_response({"standard": SLOW_STANDARD, "pulse": GOOD_PULSE})
        self.assertLess(result["residual_response_error"], 1.0)
        self.assertGreater(result["residual_response_error"], 0.0)

    def test_a_non_mapping_case_is_rejected(self):
        with self.assertRaises(ValueError):
            assess_pulsed_response(["WS-014"])

    def test_a_case_with_no_pulse_is_rejected(self):
        with self.assertRaises(ValueError):
            assess_pulsed_response({"standard": FAST_STANDARD})

    def test_a_case_with_no_standard_is_rejected(self):
        with self.assertRaises(ValueError):
            assess_pulsed_response({"pulse": GOOD_PULSE})


if __name__ == "__main__":
    unittest.main()
