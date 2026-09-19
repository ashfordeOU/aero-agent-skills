"""Contract tests for the clause 4.7.8.1 / 4.7.8.2 stability-margin logic."""

import math
import unittest

from e3301_control_system_gain_phase_margin_logic import (
    HALF_TURN_DEG,
    MARGIN_TOLERANCE,
    PHASE_TOLERANCE_DEG,
    REQUIRED_GAIN_MARGIN,
    REQUIRED_GAIN_MARGIN_DB,
    REQUIRED_PHASE_MARGIN_DEG,
    assess_control_margins,
    evaluate_case,
    from_db,
    gain_margin,
    interpolate_at_phase_crossover,
    interpolate_at_unity_gain,
    phase_margin_deg,
    to_db,
    validate_response,
    worst_case_margins,
)

# Nominal open loop: unity gain at 10 Hz with 60 degrees of phase margin, and
# the half-turn lag at 100 Hz where the magnitude is a fifth.
NOMINAL = [
    (1.0, 10.0, -90.0),
    (10.0, 1.0, -120.0),
    (100.0, 0.2, -180.0),
    (1000.0, 0.02, -240.0),
]

# Hot case: the same shape with less margin of both kinds.
HOT = [
    (1.0, 20.0, -100.0),
    (10.0, 1.0, -150.0),
    (100.0, 0.5, -180.0),
    (1000.0, 0.05, -250.0),
]

# End-of-life friction case: worse gain margin still.
COLD = [
    (1.0, 30.0, -95.0),
    (10.0, 1.0, -135.0),
    (100.0, 0.8, -180.0),
    (1000.0, 0.08, -245.0),
]


class ValidateResponseTests(unittest.TestCase):
    def test_returns_float_triples(self):
        points = validate_response(NOMINAL)
        self.assertEqual(len(points), 4)
        self.assertAlmostEqual(points[0][0], 1.0, places=9)

    def test_single_point_rejected(self):
        with self.assertRaises(ValueError):
            validate_response([(1.0, 10.0, -90.0)])

    def test_non_increasing_frequency_rejected(self):
        with self.assertRaises(ValueError):
            validate_response([(10.0, 10.0, -90.0), (1.0, 1.0, -120.0)])

    def test_zero_magnitude_rejected(self):
        with self.assertRaises(ValueError):
            validate_response([(1.0, 0.0, -90.0), (10.0, 1.0, -120.0)])

    def test_malformed_point_rejected(self):
        with self.assertRaises(ValueError):
            validate_response([(1.0, 10.0), (10.0, 1.0, -120.0)])

    def test_non_finite_phase_rejected(self):
        with self.assertRaises(ValueError):
            validate_response([(1.0, 10.0, float("nan")), (10.0, 1.0, -120.0)])

    def test_boolean_frequency_rejected(self):
        with self.assertRaises(ValueError):
            validate_response([(True, 10.0, -90.0), (10.0, 1.0, -120.0)])


class DecibelTests(unittest.TestCase):
    def test_factor_of_two_is_about_six_db(self):
        self.assertAlmostEqual(to_db(2.0), 6.020599913, places=6)

    def test_unity_is_zero_db(self):
        self.assertAlmostEqual(to_db(1.0), 0.0, places=12)

    def test_round_trip_through_decibels(self):
        self.assertAlmostEqual(from_db(to_db(0.37)), 0.37, places=12)

    def test_required_gain_margin_constants_agree(self):
        self.assertAlmostEqual(to_db(REQUIRED_GAIN_MARGIN), REQUIRED_GAIN_MARGIN_DB, places=12)

    def test_required_constants_are_the_documented_ones(self):
        self.assertAlmostEqual(REQUIRED_GAIN_MARGIN, 2.0, places=12)
        self.assertAlmostEqual(REQUIRED_PHASE_MARGIN_DEG, 30.0, places=12)
        self.assertAlmostEqual(HALF_TURN_DEG, -180.0, places=12)

    def test_zero_magnitude_has_no_decibel_value(self):
        with self.assertRaises(ValueError):
            to_db(0.0)


class CrossoverTests(unittest.TestCase):
    def test_unity_gain_at_a_tabulated_point(self):
        frequency, phase = interpolate_at_unity_gain(NOMINAL)
        self.assertAlmostEqual(frequency, 10.0, places=9)
        self.assertAlmostEqual(phase, -120.0, places=9)

    def test_unity_gain_between_two_points(self):
        response = [(1.0, 4.0, -90.0), (100.0, 0.25, -170.0)]
        frequency, phase = interpolate_at_unity_gain(response)
        self.assertAlmostEqual(frequency, 10.0, places=6)
        self.assertAlmostEqual(phase, -130.0, places=6)

    def test_response_never_reaching_unity_is_refused(self):
        with self.assertRaises(ValueError):
            interpolate_at_unity_gain([(1.0, 10.0, -90.0), (10.0, 5.0, -120.0)])

    def test_phase_crossover_at_a_tabulated_point(self):
        frequency, magnitude = interpolate_at_phase_crossover(NOMINAL)
        self.assertAlmostEqual(frequency, 100.0, places=9)
        self.assertAlmostEqual(magnitude, 0.2, places=12)

    def test_phase_crossover_between_two_points(self):
        response = [(10.0, 1.0, -160.0), (1000.0, 0.01, -200.0)]
        frequency, magnitude = interpolate_at_phase_crossover(response)
        self.assertAlmostEqual(frequency, 100.0, places=6)
        self.assertAlmostEqual(magnitude, 0.1, places=9)

    def test_response_never_reaching_the_half_turn_is_refused(self):
        with self.assertRaises(ValueError):
            interpolate_at_phase_crossover([(1.0, 10.0, -90.0), (10.0, 1.0, -120.0)])


class MarginTests(unittest.TestCase):
    def test_gain_margin_is_the_reciprocal_magnitude(self):
        result = gain_margin(NOMINAL)
        self.assertAlmostEqual(result["margin"], 5.0, places=9)
        self.assertAlmostEqual(result["frequency_hz"], 100.0, places=9)

    def test_gain_margin_in_decibels_matches_the_factor(self):
        result = gain_margin(NOMINAL)
        self.assertAlmostEqual(result["margin_db"], to_db(result["margin"]), places=9)

    def test_phase_margin_is_measured_from_the_half_turn(self):
        result = phase_margin_deg(NOMINAL)
        self.assertAlmostEqual(result["margin_deg"], 60.0, places=9)

    def test_hot_case_has_the_smaller_phase_margin(self):
        self.assertAlmostEqual(phase_margin_deg(HOT)["margin_deg"], 30.0, places=9)

    def test_gain_margin_exactly_at_the_requirement(self):
        result = gain_margin(HOT)
        self.assertAlmostEqual(result["margin"], REQUIRED_GAIN_MARGIN, places=9)

    def test_case_record_carries_both_margins(self):
        record = evaluate_case({"id": "NOMINAL", "response": NOMINAL})
        self.assertAlmostEqual(record["gain_margin"], 5.0, places=9)
        self.assertAlmostEqual(record["phase_margin_deg"], 60.0, places=9)

    def test_case_records_both_crossover_frequencies(self):
        record = evaluate_case({"id": "NOMINAL", "response": NOMINAL})
        self.assertAlmostEqual(record["gain_crossover_hz"], 10.0, places=9)
        self.assertAlmostEqual(record["phase_crossover_hz"], 100.0, places=9)

    def test_missing_case_key_rejected(self):
        with self.assertRaises(ValueError):
            evaluate_case({"id": "NOMINAL"})

    def test_non_mapping_case_rejected(self):
        with self.assertRaises(ValueError):
            evaluate_case(["NOMINAL"])

    def test_blank_case_id_rejected(self):
        with self.assertRaises(ValueError):
            evaluate_case({"id": "   ", "response": NOMINAL})


class WorstCaseTests(unittest.TestCase):
    def _cases(self):
        return [
            {"id": "NOMINAL", "response": NOMINAL},
            {"id": "HOT", "response": HOT},
            {"id": "COLD", "response": COLD},
        ]

    def test_all_cases_are_recorded(self):
        summary = worst_case_margins(self._cases())
        self.assertEqual(len(summary["records"]), 3)

    def test_worst_gain_case_is_the_cold_one(self):
        summary = worst_case_margins(self._cases())
        self.assertEqual(summary["worst_gain"]["id"], "COLD")
        self.assertAlmostEqual(summary["worst_gain"]["gain_margin"], 1.25, places=9)

    def test_worst_phase_case_is_the_hot_one(self):
        summary = worst_case_margins(self._cases())
        self.assertEqual(summary["worst_phase"]["id"], "HOT")
        self.assertAlmostEqual(summary["worst_phase"]["phase_margin_deg"], 30.0, places=9)

    def test_tie_is_broken_by_the_case_identifier(self):
        cases = [{"id": "B", "response": NOMINAL}, {"id": "A", "response": NOMINAL}]
        summary = worst_case_margins(cases)
        self.assertEqual(summary["worst_gain"]["id"], "A")

    def test_duplicate_case_id_rejected(self):
        with self.assertRaises(ValueError):
            worst_case_margins([{"id": "A", "response": NOMINAL},
                                {"id": "A", "response": HOT}])

    def test_empty_case_set_rejected(self):
        with self.assertRaises(ValueError):
            worst_case_margins([])


class AssessmentTests(unittest.TestCase):
    def _spec(self, **overrides):
        spec = {
            "cases": [
                {"id": "NOMINAL", "response": NOMINAL},
                {"id": "HOT", "response": HOT},
            ]
        }
        spec.update(overrides)
        return spec

    def test_both_margins_exactly_at_their_requirements_pass(self):
        result = assess_control_margins(self._spec())
        self.assertAlmostEqual(result["gain_margin"], REQUIRED_GAIN_MARGIN, places=9)
        self.assertAlmostEqual(result["phase_margin_deg"], REQUIRED_PHASE_MARGIN_DEG, places=9)
        self.assertTrue(result["gain_ok"])
        self.assertTrue(result["phase_ok"])
        self.assertTrue(result["compliant"])

    def test_boundary_sits_inside_the_named_tolerances(self):
        result = assess_control_margins(self._spec())
        self.assertLessEqual(abs(result["gain_margin"] - REQUIRED_GAIN_MARGIN),
                             MARGIN_TOLERANCE)
        self.assertLessEqual(abs(result["phase_margin_deg"] - REQUIRED_PHASE_MARGIN_DEG),
                             PHASE_TOLERANCE_DEG)

    def test_cold_case_fails_the_gain_requirement(self):
        spec = self._spec(cases=[{"id": "NOMINAL", "response": NOMINAL},
                                 {"id": "COLD", "response": COLD}])
        result = assess_control_margins(spec)
        self.assertFalse(result["gain_ok"])
        self.assertTrue(any("gain margin" in f for f in result["findings"]))

    def test_tightened_requirement_fails_a_passing_design(self):
        result = assess_control_margins(self._spec(required_phase_margin_deg=45.0))
        self.assertFalse(result["phase_ok"])

    def test_single_case_is_reported_as_insufficient_coverage(self):
        result = assess_control_margins(
            self._spec(cases=[{"id": "NOMINAL", "response": NOMINAL}])
        )
        self.assertFalse(result["compliant"])
        self.assertTrue(any("single case" in f for f in result["findings"]))

    def test_worst_case_identifiers_are_reported(self):
        result = assess_control_margins(self._spec())
        self.assertEqual(result["worst_gain_case"], "HOT")
        self.assertEqual(result["worst_phase_case"], "HOT")

    def test_gain_margin_in_decibels_is_reported(self):
        result = assess_control_margins(self._spec())
        self.assertAlmostEqual(result["gain_margin_db"], REQUIRED_GAIN_MARGIN_DB, places=9)

    def test_missing_cases_key_rejected(self):
        with self.assertRaises(ValueError):
            assess_control_margins({})

    def test_non_mapping_spec_rejected(self):
        with self.assertRaises(ValueError):
            assess_control_margins(["cases"])

    def test_non_positive_required_phase_margin_rejected(self):
        with self.assertRaises(ValueError):
            assess_control_margins(self._spec(required_phase_margin_deg=0.0))

    def test_non_positive_required_gain_margin_rejected(self):
        with self.assertRaises(ValueError):
            assess_control_margins(self._spec(required_gain_margin=0.0))

    def test_report_carries_one_record_per_case(self):
        result = assess_control_margins(self._spec())
        self.assertEqual(len(result["records"]), 2)
        self.assertTrue(all(math.isfinite(r["gain_margin"]) for r in result["records"]))


if __name__ == "__main__":
    unittest.main()
