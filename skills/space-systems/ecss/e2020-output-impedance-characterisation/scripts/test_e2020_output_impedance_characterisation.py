#!/usr/bin/env python3
"""Contract test for the output impedance characterisation (offline)."""

import copy
import math
import unittest

from e2020_output_impedance_characterisation_logic import (
    ADVISORY_PEAK,
    ADVISORY_UNDECLARED,
    DEFAULT_CHARACTERISATION_POLICY,
    FINDING_BAND_HIGH,
    FINDING_BAND_LOW,
    FINDING_MISSING_CLASS,
    FINDING_PHASE,
    FINDING_RESOLUTION,
    FINDING_STEP,
    VERDICT_COMPLETE,
    VERDICT_INCOMPLETE,
    assess_class_sweep,
    characterise_output_impedance,
    covers_band,
    db_ohm_to_ohms,
    decades_spanned,
    largest_adjacent_ratio,
    ohms_to_db_ohm,
    peak_impedance,
    points_per_decade,
    validate_characterisation_policy,
    validate_point,
    validate_sweep,
)

BAND_LOW_HZ = 12.0
BAND_HIGH_HZ = 9.0e4

DECLARED_CLASSES = ("lcl-a", "lcl-b", "lcl-c")


def _log_sweep(f_start=10.0, f_stop=1.0e5, per_decade=10, scale=1.0, phase_deg=-45.0):
    """A log-spaced gain-and-phase sweep, built the same way every run."""
    decades = math.log10(f_stop / f_start)
    count = int(round(decades * per_decade))
    rows = []
    for k in range(count + 1):
        freq = f_start * (10.0 ** (k / float(per_decade)))
        magnitude = scale * (
            0.05 + 0.25 * math.exp(-((math.log10(freq) - 3.0) ** 2))
        )
        rows.append(
            {
                "frequency_hz": freq,
                "magnitude_ohm": magnitude,
                "phase_deg": phase_deg,
            }
        )
    return rows


def _sweeps():
    return {
        "lcl-a": _log_sweep(scale=0.6),
        "lcl-b": _log_sweep(scale=0.8),
        "lcl-c": _log_sweep(scale=1.0),
    }


class PolicyTests(unittest.TestCase):
    def test_default_policy_validates(self):
        self.assertIs(
            validate_characterisation_policy(DEFAULT_CHARACTERISATION_POLICY),
            DEFAULT_CHARACTERISATION_POLICY,
        )

    def test_non_mapping_policy_rejected(self):
        with self.assertRaises(ValueError):
            validate_characterisation_policy("default")

    def test_resolution_floor_below_one_rejected(self):
        policy = dict(DEFAULT_CHARACTERISATION_POLICY, points_per_decade_floor=0.4)
        with self.assertRaises(ValueError):
            validate_characterisation_policy(policy)

    def test_step_limit_at_unity_rejected(self):
        policy = dict(DEFAULT_CHARACTERISATION_POLICY, max_adjacent_frequency_ratio=1.0)
        with self.assertRaises(ValueError):
            validate_characterisation_policy(policy)

    def test_phase_bound_beyond_a_full_turn_rejected(self):
        policy = dict(DEFAULT_CHARACTERISATION_POLICY, phase_bound_deg=400.0)
        with self.assertRaises(ValueError):
            validate_characterisation_policy(policy)

    def test_zero_peak_ceiling_rejected(self):
        policy = dict(
            DEFAULT_CHARACTERISATION_POLICY, peak_magnitude_advisory_ceiling_ohm=0.0
        )
        with self.assertRaises(ValueError):
            validate_characterisation_policy(policy)


class ConversionTests(unittest.TestCase):
    def test_one_ohm_is_zero_db_ohm(self):
        self.assertAlmostEqual(ohms_to_db_ohm(1.0), 0.0, places=9)

    def test_ten_ohm_is_twenty_db_ohm(self):
        self.assertAlmostEqual(ohms_to_db_ohm(10.0), 20.0, places=9)

    def test_conversion_round_trips(self):
        self.assertAlmostEqual(db_ohm_to_ohms(ohms_to_db_ohm(0.37)), 0.37, places=9)

    def test_zero_db_ohm_is_one_ohm(self):
        self.assertAlmostEqual(db_ohm_to_ohms(0.0), 1.0, places=9)

    def test_non_positive_magnitude_has_no_db_value(self):
        with self.assertRaises(ValueError):
            ohms_to_db_ohm(0.0)

    def test_non_numeric_db_value_rejected(self):
        with self.assertRaises(ValueError):
            db_ohm_to_ohms("-6 dB")


class PointTests(unittest.TestCase):
    def test_nominal_point_validates(self):
        row = validate_point(
            {"frequency_hz": 100.0, "magnitude_ohm": 0.2, "phase_deg": -30.0}
        )
        self.assertAlmostEqual(row["phase_deg"], -30.0, places=9)

    def test_point_missing_phase_rejected(self):
        with self.assertRaises(ValueError):
            validate_point({"frequency_hz": 100.0, "magnitude_ohm": 0.2})

    def test_negative_magnitude_rejected(self):
        with self.assertRaises(ValueError):
            validate_point(
                {"frequency_hz": 100.0, "magnitude_ohm": -0.2, "phase_deg": 0.0}
            )

    def test_boolean_frequency_rejected(self):
        with self.assertRaises(ValueError):
            validate_point(
                {"frequency_hz": True, "magnitude_ohm": 0.2, "phase_deg": 0.0}
            )

    def test_non_mapping_point_rejected(self):
        with self.assertRaises(ValueError):
            validate_point("100 Hz")


class SweepValidationTests(unittest.TestCase):
    def test_nominal_sweep_validates(self):
        rows = validate_sweep(_log_sweep())
        self.assertEqual(len(rows), 41)

    def test_single_point_sweep_rejected(self):
        with self.assertRaises(ValueError):
            validate_sweep(_log_sweep()[:1])

    def test_descending_sweep_rejected(self):
        rows = _log_sweep()
        rows.reverse()
        with self.assertRaises(ValueError):
            validate_sweep(rows)

    def test_repeated_frequency_rejected(self):
        rows = _log_sweep()
        rows[5]["frequency_hz"] = rows[4]["frequency_hz"]
        with self.assertRaises(ValueError):
            validate_sweep(rows)

    def test_mapping_instead_of_a_sequence_rejected(self):
        with self.assertRaises(ValueError):
            validate_sweep(_log_sweep()[0])

    def test_a_broken_point_breaks_the_sweep(self):
        rows = _log_sweep()
        del rows[3]["magnitude_ohm"]
        with self.assertRaises(ValueError):
            validate_sweep(rows)


class MetricTests(unittest.TestCase):
    def test_decades_spanned_matches_the_sweep_span(self):
        self.assertAlmostEqual(decades_spanned(_log_sweep()), 4.0, places=9)

    def test_points_per_decade_matches_the_construction(self):
        self.assertAlmostEqual(points_per_decade(_log_sweep()), 10.0, places=9)

    def test_a_sparser_sweep_reports_fewer_points_per_decade(self):
        dense = points_per_decade(_log_sweep(per_decade=20))
        sparse = points_per_decade(_log_sweep(per_decade=5))
        self.assertGreater(dense, sparse)

    def test_largest_adjacent_ratio_matches_the_spacing(self):
        widest = largest_adjacent_ratio(_log_sweep(per_decade=10))
        self.assertAlmostEqual(widest, 10.0 ** 0.1, places=9)

    def test_a_ratio_sitting_exactly_on_the_limit_is_accepted(self):
        limit = float(DEFAULT_CHARACTERISATION_POLICY["max_adjacent_frequency_ratio"])
        rows = [
            {"frequency_hz": 10.0, "magnitude_ohm": 0.1, "phase_deg": 0.0},
            {"frequency_hz": 10.0 * limit, "magnitude_ohm": 0.1, "phase_deg": 0.0},
        ]
        self.assertAlmostEqual(largest_adjacent_ratio(rows), limit, places=9)
        result = assess_class_sweep("lcl-a", rows, 10.0, 10.0 * limit)
        self.assertTrue(result["step_limit_met"])

    def test_peak_reports_the_worst_magnitude_and_its_frequency(self):
        peak = peak_impedance(_log_sweep())
        self.assertAlmostEqual(peak["magnitude_ohm"], 0.30, places=9)
        self.assertAlmostEqual(peak["frequency_hz"], 1000.0, places=6)

    def test_peak_carries_its_own_db_ohm_value(self):
        peak = peak_impedance(_log_sweep())
        self.assertAlmostEqual(
            peak["magnitude_db_ohm"], ohms_to_db_ohm(peak["magnitude_ohm"]), places=9
        )

    def test_band_coverage_reports_both_edges(self):
        low_ok, high_ok = covers_band(_log_sweep(), BAND_LOW_HZ, BAND_HIGH_HZ)
        self.assertTrue(low_ok)
        self.assertTrue(high_ok)

    def test_band_edges_exactly_on_the_sweep_ends_are_covered(self):
        rows = [
            {"frequency_hz": 10.0, "magnitude_ohm": 0.1, "phase_deg": 0.0},
            {"frequency_hz": 14.0, "magnitude_ohm": 0.1, "phase_deg": 0.0},
        ]
        self.assertEqual(covers_band(rows, 10.0, 14.0), (True, True))

    def test_band_that_does_not_ascend_rejected(self):
        with self.assertRaises(ValueError):
            covers_band(_log_sweep(), 1.0e5, 10.0)


class AssessmentTests(unittest.TestCase):
    def test_nominal_sweep_is_complete(self):
        result = assess_class_sweep("lcl-c", _log_sweep(), BAND_LOW_HZ, BAND_HIGH_HZ)
        self.assertTrue(result["complete"])
        self.assertEqual(result["findings"], [])

    def test_sweep_starting_inside_the_band_misses_the_lower_edge(self):
        result = assess_class_sweep(
            "lcl-c", _log_sweep(f_start=100.0), BAND_LOW_HZ, BAND_HIGH_HZ
        )
        self.assertFalse(result["reaches_lower_edge"])
        self.assertTrue(any(FINDING_BAND_LOW in f for f in result["findings"]))

    def test_sweep_stopping_inside_the_band_misses_the_upper_edge(self):
        result = assess_class_sweep(
            "lcl-c", _log_sweep(f_stop=1.0e4), BAND_LOW_HZ, BAND_HIGH_HZ
        )
        self.assertFalse(result["reaches_upper_edge"])
        self.assertTrue(any(FINDING_BAND_HIGH in f for f in result["findings"]))

    def test_a_sparse_sweep_fails_the_resolution_floor(self):
        result = assess_class_sweep(
            "lcl-c", _log_sweep(per_decade=5), BAND_LOW_HZ, BAND_HIGH_HZ
        )
        self.assertFalse(result["resolution_met"])
        self.assertTrue(result["step_limit_met"])
        self.assertTrue(any(FINDING_RESOLUTION in f for f in result["findings"]))

    def test_a_hole_in_a_dense_sweep_fails_the_step_limit(self):
        rows = _log_sweep(per_decade=20)
        del rows[30:34]
        result = assess_class_sweep("lcl-c", rows, BAND_LOW_HZ, BAND_HIGH_HZ)
        self.assertTrue(result["resolution_met"])
        self.assertFalse(result["step_limit_met"])
        self.assertTrue(any(FINDING_STEP in f for f in result["findings"]))

    def test_a_phase_beyond_the_bound_is_a_finding(self):
        rows = _log_sweep()
        rows[12]["phase_deg"] = -260.0
        result = assess_class_sweep("lcl-c", rows, BAND_LOW_HZ, BAND_HIGH_HZ)
        self.assertFalse(result["phase_within_bound"])
        self.assertTrue(any(FINDING_PHASE in f for f in result["findings"]))

    def test_a_phase_exactly_on_the_bound_is_accepted(self):
        rows = _log_sweep()
        rows[12]["phase_deg"] = float(
            DEFAULT_CHARACTERISATION_POLICY["phase_bound_deg"]
        )
        result = assess_class_sweep("lcl-c", rows, BAND_LOW_HZ, BAND_HIGH_HZ)
        self.assertTrue(result["phase_within_bound"])
        self.assertTrue(result["complete"])

    def test_a_tall_peak_raises_an_advisory_not_a_finding(self):
        result = assess_class_sweep(
            "lcl-c", _log_sweep(scale=4.0), BAND_LOW_HZ, BAND_HIGH_HZ
        )
        self.assertTrue(result["complete"])
        self.assertEqual(result["findings"], [])
        self.assertTrue(any(ADVISORY_PEAK in a for a in result["advisories"]))

    def test_a_peak_exactly_on_the_advisory_ceiling_stays_quiet(self):
        ceiling = float(
            DEFAULT_CHARACTERISATION_POLICY["peak_magnitude_advisory_ceiling_ohm"]
        )
        rows = [
            {"frequency_hz": 10.0, "magnitude_ohm": 0.2, "phase_deg": 0.0},
            {"frequency_hz": 14.0, "magnitude_ohm": ceiling, "phase_deg": 0.0},
        ]
        result = assess_class_sweep("lcl-a", rows, 10.0, 14.0)
        self.assertAlmostEqual(result["peak"]["magnitude_ohm"], ceiling, places=9)
        self.assertEqual(result["advisories"], [])

    def test_blank_class_name_rejected(self):
        with self.assertRaises(ValueError):
            assess_class_sweep("  ", _log_sweep(), BAND_LOW_HZ, BAND_HIGH_HZ)

    def test_assessment_reports_the_span_it_looked_at(self):
        result = assess_class_sweep("lcl-c", _log_sweep(), BAND_LOW_HZ, BAND_HIGH_HZ)
        self.assertEqual(result["point_count"], 41)
        self.assertAlmostEqual(result["first_frequency_hz"], 10.0, places=9)


class CharacterisationTests(unittest.TestCase):
    def test_every_declared_class_delivered_is_complete(self):
        result = characterise_output_impedance(
            _sweeps(), DECLARED_CLASSES, BAND_LOW_HZ, BAND_HIGH_HZ
        )
        self.assertEqual(result["verdict"], VERDICT_COMPLETE)
        self.assertEqual(result["findings"], [])
        self.assertEqual(len(result["complete_classes"]), 3)

    def test_a_missing_class_is_a_finding(self):
        sweeps = _sweeps()
        del sweeps["lcl-b"]
        result = characterise_output_impedance(
            sweeps, DECLARED_CLASSES, BAND_LOW_HZ, BAND_HIGH_HZ
        )
        self.assertEqual(result["verdict"], VERDICT_INCOMPLETE)
        self.assertEqual(result["missing_classes"], ["lcl-b"])
        self.assertTrue(any(FINDING_MISSING_CLASS in f for f in result["findings"]))

    def test_an_undeclared_dataset_is_only_an_advisory(self):
        sweeps = _sweeps()
        sweeps["lcl-z"] = _log_sweep(scale=0.4)
        result = characterise_output_impedance(
            sweeps, DECLARED_CLASSES, BAND_LOW_HZ, BAND_HIGH_HZ
        )
        self.assertEqual(result["verdict"], VERDICT_COMPLETE)
        self.assertTrue(any(ADVISORY_UNDECLARED in a for a in result["advisories"]))

    def test_one_short_sweep_turns_the_whole_delivery_incomplete(self):
        sweeps = _sweeps()
        sweeps["lcl-a"] = _log_sweep(f_stop=1.0e4, scale=0.6)
        result = characterise_output_impedance(
            sweeps, DECLARED_CLASSES, BAND_LOW_HZ, BAND_HIGH_HZ
        )
        self.assertEqual(result["verdict"], VERDICT_INCOMPLETE)
        self.assertNotIn("lcl-a", result["complete_classes"])
        self.assertIn("lcl-b", result["complete_classes"])

    def test_every_delivered_class_gets_an_assessment_row(self):
        result = characterise_output_impedance(
            _sweeps(), DECLARED_CLASSES, BAND_LOW_HZ, BAND_HIGH_HZ
        )
        self.assertEqual(len(result["assessments"]), 3)

    def test_sweeps_must_arrive_as_a_mapping(self):
        with self.assertRaises(ValueError):
            characterise_output_impedance(
                [_log_sweep()], DECLARED_CLASSES, BAND_LOW_HZ, BAND_HIGH_HZ
            )

    def test_an_empty_class_list_is_refused(self):
        with self.assertRaises(ValueError):
            characterise_output_impedance(
                _sweeps(), (), BAND_LOW_HZ, BAND_HIGH_HZ
            )

    def test_a_repeated_declared_class_is_refused(self):
        with self.assertRaises(ValueError):
            characterise_output_impedance(
                _sweeps(), ("lcl-a", "lcl-a"), BAND_LOW_HZ, BAND_HIGH_HZ
            )

    def test_a_string_instead_of_a_class_list_is_refused(self):
        with self.assertRaises(ValueError):
            characterise_output_impedance(
                _sweeps(), "lcl-a", BAND_LOW_HZ, BAND_HIGH_HZ
            )

    def test_a_tighter_resolution_floor_can_fail_a_delivered_sweep(self):
        strict = dict(DEFAULT_CHARACTERISATION_POLICY, points_per_decade_floor=16.0)
        result = characterise_output_impedance(
            _sweeps(), DECLARED_CLASSES, BAND_LOW_HZ, BAND_HIGH_HZ, strict
        )
        self.assertEqual(result["verdict"], VERDICT_INCOMPLETE)
        self.assertTrue(any(FINDING_RESOLUTION in f for f in result["findings"]))

    def test_the_input_sweeps_are_not_mutated(self):
        sweeps = _sweeps()
        before = copy.deepcopy(sweeps)
        characterise_output_impedance(
            sweeps, DECLARED_CLASSES, BAND_LOW_HZ, BAND_HIGH_HZ
        )
        self.assertEqual(sweeps, before)


if __name__ == "__main__":
    unittest.main()
