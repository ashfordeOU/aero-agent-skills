#!/usr/bin/env python3
"""Gate 3 contract test for e2007-susceptibility-signal-modulation.

stdlib unittest, offline, deterministic. Run:
    python3 test_e2007_susceptibility_signal_modulation.py
"""

import math
import unittest

from e2007_susceptibility_signal_modulation_logic import (
    CATEGORY_AGREED_DEVIATION,
    CATEGORY_CONFORMING,
    CATEGORY_NON_CONFORMING,
    DEFAULT_DUTY_CYCLE,
    DEFAULT_PULSE_RATE_HZ,
    MODULATION_CONTINUOUS,
    MODULATION_PULSE,
    MODULATION_THRESHOLD_HZ,
    RECOGNIZED_MODULATIONS,
    RECOGNIZED_RUN_TYPES,
    assess_signal_modulation,
    at_or_above,
    grade_injection_point,
    grade_injection_schedule,
    injected_peak_level_dbuv,
    normalize_modulation,
    normalize_run_type,
    peak_to_average_ratio_db,
    required_modulation,
    validate_injection_point,
    validate_run_configuration,
    validate_schedule,
    within,
)


def good_config(**over):
    record = {
        "run_type": "radiated-susceptibility",
        "modulation_threshold_hz": MODULATION_THRESHOLD_HZ,
        "default_pulse_rate_hz": DEFAULT_PULSE_RATE_HZ,
        "default_duty_cycle": DEFAULT_DUTY_CYCLE,
    }
    record.update(over)
    return record


def cw_point(**over):
    record = {
        "frequency_hz": 30.0e3,
        "modulation": MODULATION_CONTINUOUS,
        "average_level_dbuv": 120.0,
    }
    record.update(over)
    return record


def pulse_point(**over):
    record = {
        "frequency_hz": 1.0e6,
        "modulation": MODULATION_PULSE,
        "average_level_dbuv": 118.0,
        "pulse_rate_hz": DEFAULT_PULSE_RATE_HZ,
        "duty_cycle": DEFAULT_DUTY_CYCLE,
    }
    record.update(over)
    return record


def good_schedule():
    return [
        cw_point(frequency_hz=1.0e3),
        cw_point(frequency_hz=50.0e3),
        pulse_point(frequency_hz=200.0e3),
        pulse_point(frequency_hz=10.0e6),
    ]


class TestRecognizedVocabulary(unittest.TestCase):
    def test_every_recognized_modulation_normalizes(self):
        for name in RECOGNIZED_MODULATIONS:
            self.assertEqual(normalize_modulation(name.upper()), name)

    def test_unrecognized_modulation_rejected(self):
        with self.assertRaises(ValueError):
            normalize_modulation("square-chirp")

    def test_non_string_modulation_rejected(self):
        with self.assertRaises(ValueError):
            normalize_modulation(1000)

    def test_every_recognized_run_type_normalizes(self):
        for name in RECOGNIZED_RUN_TYPES:
            self.assertEqual(normalize_run_type(" %s " % name), name)

    def test_unrecognized_run_type_rejected(self):
        with self.assertRaises(ValueError):
            normalize_run_type("emission-sweep")


class TestRequiredModulation(unittest.TestCase):
    def test_below_threshold_is_continuous_wave(self):
        self.assertEqual(required_modulation(30.0e3), MODULATION_CONTINUOUS)

    def test_above_threshold_is_pulse_modulated(self):
        self.assertEqual(required_modulation(400.0e3), MODULATION_PULSE)

    def test_exactly_at_the_threshold_is_pulse_modulated(self):
        # The threshold frequency itself sits inside the pulse-modulated band.
        self.assertAlmostEqual(MODULATION_THRESHOLD_HZ, 100000.0, places=9)
        self.assertEqual(
            required_modulation(MODULATION_THRESHOLD_HZ), MODULATION_PULSE
        )

    def test_just_below_the_threshold_is_continuous_wave(self):
        self.assertEqual(required_modulation(99.0e3), MODULATION_CONTINUOUS)

    def test_an_agreed_threshold_moves_the_band_edge(self):
        self.assertEqual(
            required_modulation(60.0e3, threshold_hz=50.0e3), MODULATION_PULSE
        )

    def test_zero_frequency_rejected(self):
        with self.assertRaises(ValueError):
            required_modulation(0.0)

    def test_negative_threshold_rejected(self):
        with self.assertRaises(ValueError):
            required_modulation(1.0e6, threshold_hz=-1.0)

    def test_non_numeric_frequency_rejected(self):
        with self.assertRaises(ValueError):
            required_modulation("1 MHz")


class TestPeakToAverage(unittest.TestCase):
    def test_half_duty_puts_the_peak_three_decibels_up(self):
        self.assertAlmostEqual(
            peak_to_average_ratio_db(0.5), 3.0102999566398121, places=9
        )

    def test_tenth_duty_puts_the_peak_ten_decibels_up(self):
        self.assertAlmostEqual(peak_to_average_ratio_db(0.1), 10.0, places=9)

    def test_full_duty_leaves_the_peak_at_the_average(self):
        self.assertAlmostEqual(peak_to_average_ratio_db(1.0), 0.0, places=9)

    def test_peak_level_adds_the_ratio_to_the_average(self):
        self.assertAlmostEqual(
            injected_peak_level_dbuv(118.0, 0.5), 121.0102999566398121, places=9
        )

    def test_zero_duty_rejected(self):
        with self.assertRaises(ValueError):
            peak_to_average_ratio_db(0.0)

    def test_duty_above_unity_rejected(self):
        with self.assertRaises(ValueError):
            peak_to_average_ratio_db(1.2)


class TestPointValidation(unittest.TestCase):
    def test_continuous_wave_point_normalizes(self):
        record = validate_injection_point(cw_point())
        self.assertEqual(record["modulation"], MODULATION_CONTINUOUS)
        self.assertIsNone(record["duty_cycle"])

    def test_pulse_point_normalizes(self):
        record = validate_injection_point(pulse_point())
        self.assertAlmostEqual(record["pulse_rate_hz"], 1000.0)
        self.assertAlmostEqual(record["duty_cycle"], 0.5)

    def test_continuous_wave_point_with_duty_cycle_rejected(self):
        with self.assertRaises(ValueError):
            validate_injection_point(cw_point(duty_cycle=0.5))

    def test_pulse_point_without_duty_cycle_rejected(self):
        record = pulse_point()
        del record["duty_cycle"]
        with self.assertRaises(ValueError):
            validate_injection_point(record)

    def test_pulse_rate_at_or_above_the_carrier_rejected(self):
        with self.assertRaises(ValueError):
            validate_injection_point(
                pulse_point(frequency_hz=900.0, pulse_rate_hz=1000.0)
            )

    def test_zero_frequency_point_rejected(self):
        with self.assertRaises(ValueError):
            validate_injection_point(cw_point(frequency_hz=0.0))

    def test_missing_level_rejected(self):
        record = cw_point()
        del record["average_level_dbuv"]
        with self.assertRaises(ValueError):
            validate_injection_point(record)

    def test_agreed_deviation_without_justification_rejected(self):
        with self.assertRaises(ValueError):
            validate_injection_point(cw_point(frequency_hz=1.0e6, deviation_agreed=True))

    def test_non_boolean_agreement_flag_rejected(self):
        with self.assertRaises(ValueError):
            validate_injection_point(cw_point(deviation_agreed="yes"))

    def test_non_mapping_point_rejected(self):
        with self.assertRaises(ValueError):
            validate_injection_point(["1 MHz pulse"])


class TestPointGrading(unittest.TestCase):
    def test_default_pulse_point_conforms(self):
        graded = grade_injection_point(pulse_point())
        self.assertEqual(graded["category"], CATEGORY_CONFORMING)
        self.assertEqual(graded["reasons"], [])

    def test_continuous_wave_below_the_threshold_conforms(self):
        graded = grade_injection_point(cw_point())
        self.assertEqual(graded["category"], CATEGORY_CONFORMING)
        self.assertAlmostEqual(graded["peak_to_average_db"], 0.0, places=9)

    def test_continuous_wave_above_the_threshold_is_non_conforming(self):
        graded = grade_injection_point(cw_point(frequency_hz=2.0e6))
        self.assertEqual(graded["category"], CATEGORY_NON_CONFORMING)
        self.assertTrue(any("continuous-wave" in r for r in graded["reasons"]))

    def test_justified_departure_is_an_agreed_deviation(self):
        graded = grade_injection_point(
            cw_point(
                frequency_hz=2.0e6,
                deviation_agreed=True,
                deviation_justification="receiver demodulator needs an unmodulated carrier",
            )
        )
        self.assertEqual(graded["category"], CATEGORY_AGREED_DEVIATION)

    def test_duty_cycle_on_the_tolerance_edge_still_conforms(self):
        # 0.52 - 0.5 is 0.020000000000000018 in binary floating point, so a
        # duty cycle exactly on the 0.02 tolerance edge reads outside it.
        self.assertAlmostEqual(abs(0.52 - DEFAULT_DUTY_CYCLE), 0.02, places=9)
        graded = grade_injection_point(pulse_point(duty_cycle=0.52))
        self.assertEqual(graded["category"], CATEGORY_CONFORMING)

    def test_duty_cycle_well_outside_the_tolerance_is_non_conforming(self):
        graded = grade_injection_point(pulse_point(duty_cycle=0.20))
        self.assertEqual(graded["category"], CATEGORY_NON_CONFORMING)
        self.assertTrue(any("duty cycle" in r for r in graded["reasons"]))

    def test_pulse_rate_on_the_tolerance_edge_still_conforms(self):
        graded = grade_injection_point(pulse_point(pulse_rate_hz=1050.0))
        self.assertEqual(graded["category"], CATEGORY_CONFORMING)

    def test_pulse_rate_well_outside_the_tolerance_is_non_conforming(self):
        graded = grade_injection_point(pulse_point(pulse_rate_hz=400.0))
        self.assertEqual(graded["category"], CATEGORY_NON_CONFORMING)

    def test_peak_level_of_a_half_duty_point_is_three_decibels_up(self):
        graded = grade_injection_point(pulse_point(average_level_dbuv=100.0))
        self.assertAlmostEqual(
            graded["peak_level_dbuv"], 103.0102999566398121, places=9
        )

    def test_bad_default_duty_cycle_rejected(self):
        with self.assertRaises(ValueError):
            grade_injection_point(pulse_point(), duty_cycle=0.0)


class TestScheduleGrading(unittest.TestCase):
    def test_clean_schedule_is_acceptable(self):
        report = grade_injection_schedule(good_schedule())
        self.assertTrue(report["acceptable"])
        self.assertEqual(report["counts"][CATEGORY_CONFORMING], 4)
        self.assertIsNone(report["first_non_conforming"])

    def test_first_non_conforming_point_is_reported(self):
        points = good_schedule()
        points[2] = cw_point(frequency_hz=200.0e3)
        points[3] = cw_point(frequency_hz=10.0e6)
        report = grade_injection_schedule(points)
        self.assertFalse(report["acceptable"])
        self.assertAlmostEqual(
            report["first_non_conforming"]["frequency_hz"], 200.0e3
        )

    def test_empty_schedule_rejected(self):
        with self.assertRaises(ValueError):
            validate_schedule([])

    def test_non_list_schedule_rejected(self):
        with self.assertRaises(ValueError):
            validate_schedule({"frequency_hz": 1.0e6})

    def test_decreasing_frequencies_rejected(self):
        points = good_schedule()
        points[3]["frequency_hz"] = 100.0e3
        with self.assertRaises(ValueError):
            validate_schedule(points)

    def test_duplicate_frequencies_rejected(self):
        points = good_schedule()
        points[1]["frequency_hz"] = points[0]["frequency_hz"]
        with self.assertRaises(ValueError):
            validate_schedule(points)


class TestAssessment(unittest.TestCase):
    def test_clean_run_is_accepted(self):
        report = assess_signal_modulation(good_config(), good_schedule())
        self.assertEqual(report["verdict"], "schedule-accepted")
        self.assertEqual(report["findings"], [])
        self.assertEqual(report["configuration"]["run_type"], "radiated-susceptibility")

    def test_undeclared_departure_rejects_the_run(self):
        points = good_schedule()
        points[3] = pulse_point(frequency_hz=10.0e6, duty_cycle=0.15)
        report = assess_signal_modulation(good_config(), points)
        self.assertEqual(report["verdict"], "schedule-rejected")
        self.assertTrue(
            any("undeclared modulation departure" in f for f in report["findings"])
        )

    def test_agreed_departure_is_a_limitation_not_a_finding(self):
        points = good_schedule()
        points[3] = pulse_point(
            frequency_hz=10.0e6,
            duty_cycle=0.15,
            deviation_agreed=True,
            deviation_justification="pulsed radar victim graded at its own duty cycle",
        )
        report = assess_signal_modulation(good_config(), points)
        self.assertEqual(report["verdict"], "schedule-accepted")
        self.assertTrue(
            any("agreed modulation deviation" in l for l in report["limitations"])
        )

    def test_agreed_threshold_moves_the_whole_schedule(self):
        points = [cw_point(frequency_hz=60.0e3)]
        clean = assess_signal_modulation(good_config(), points)
        self.assertEqual(clean["verdict"], "schedule-accepted")
        moved = assess_signal_modulation(
            good_config(modulation_threshold_hz=50.0e3), points
        )
        self.assertEqual(moved["verdict"], "schedule-rejected")

    def test_bad_configuration_rejected(self):
        with self.assertRaises(ValueError):
            validate_run_configuration(good_config(default_duty_cycle=1.0))

    def test_non_mapping_configuration_rejected(self):
        with self.assertRaises(ValueError):
            validate_run_configuration("radiated susceptibility, 1 kHz pulse")

    def test_helpers_absorb_float_error_only(self):
        self.assertTrue(at_or_above(1.0, 1.0))
        self.assertFalse(at_or_above(0.5, 1.0))
        self.assertTrue(within(0.5, 0.5, 0.0))
        self.assertFalse(within(0.6, 0.5, 0.01))
        with self.assertRaises(ValueError):
            within(0.5, 0.5, -1.0)

    def test_logarithm_is_used_without_a_boundary_assertion(self):
        # Guards gate 8: the ratio is compared with assertAlmostEqual, never
        # with a strict inequality against the value it lands on.
        self.assertAlmostEqual(
            peak_to_average_ratio_db(0.5), -10.0 * math.log10(0.5), places=9
        )


if __name__ == "__main__":
    unittest.main(verbosity=1)
