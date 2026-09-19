"""Contract tests for the ECSS-Q-ST-70-53C post-exposure functionality check."""

import unittest

from q7053_hardware_functionality_check_logic import (
    BOUND_TOLERANCE,
    CRITICALITY_WEIGHTS,
    MISSION_CRITICAL,
    NON_CRITICAL,
    SAFETY_CRITICAL,
    actuation_margin,
    assess_hardware_functionality,
    functional_index,
    grade_function,
    margin_to_nearest_bound,
    sample_within_window,
    validate_function_record,
)


def _fn(**overrides):
    record = {
        "name": "latch-actuation-time-s",
        "criticality": MISSION_CRITICAL,
        "min": 0.5,
        "max": 2.0,
        "measured": 1.0,
    }
    record.update(overrides)
    return record


class ValidateRecordTests(unittest.TestCase):
    def test_single_measurement_becomes_a_one_sample_series(self):
        item = validate_function_record(_fn())
        self.assertEqual(item["samples"], [1.0])

    def test_series_is_preserved(self):
        item = validate_function_record(_fn(measured=None, samples=[1.0, 1.1]))
        self.assertEqual(item["samples"], [1.0, 1.1])

    def test_one_sided_floor_is_allowed(self):
        item = validate_function_record(
            {"name": "insulation-resistance-mohm", "criticality": SAFETY_CRITICAL,
             "min": 100.0, "measured": 150.0}
        )
        self.assertIsNone(item["max"])

    def test_record_with_no_bound_rejected(self):
        with self.assertRaises(ValueError):
            validate_function_record({"name": "x", "criticality": NON_CRITICAL,
                                      "measured": 1.0})

    def test_inverted_window_rejected(self):
        with self.assertRaises(ValueError):
            validate_function_record(_fn(min=3.0, max=1.0))

    def test_unknown_criticality_rejected(self):
        with self.assertRaises(ValueError):
            validate_function_record(_fn(criticality="nice-to-have"))

    def test_empty_name_rejected(self):
        with self.assertRaises(ValueError):
            validate_function_record(_fn(name="   "))

    def test_no_measurement_rejected(self):
        record = _fn()
        del record["measured"]
        with self.assertRaises(ValueError):
            validate_function_record(record)

    def test_empty_series_rejected(self):
        with self.assertRaises(ValueError):
            validate_function_record(_fn(measured=None, samples=[]))

    def test_negative_resolution_rejected(self):
        with self.assertRaises(ValueError):
            validate_function_record(_fn(resolution=-0.1))

    def test_half_a_mechanism_pair_rejected(self):
        with self.assertRaises(ValueError):
            validate_function_record(_fn(available_drive=10.0))

    def test_non_mapping_record_rejected(self):
        with self.assertRaises(ValueError):
            validate_function_record(["latch"])


class WindowTests(unittest.TestCase):
    def test_value_inside_a_two_sided_window(self):
        self.assertTrue(sample_within_window(1.0, 0.5, 2.0))

    def test_value_below_a_floor_fails(self):
        self.assertFalse(sample_within_window(0.4, 0.5, 2.0))

    def test_value_above_a_ceiling_fails(self):
        self.assertFalse(sample_within_window(2.4, 0.5, 2.0))

    def test_value_exactly_on_a_bound_passes(self):
        self.assertTrue(sample_within_window(2.0, 0.5, 2.0))

    def test_one_sided_floor_ignores_a_high_reading(self):
        self.assertTrue(sample_within_window(1.0e6, 100.0, None))

    def test_one_sided_ceiling_ignores_a_low_reading(self):
        self.assertTrue(sample_within_window(1.0e-9, None, 1.0e-6))

    def test_resolution_absorbs_a_reading_just_past_the_bound(self):
        self.assertTrue(sample_within_window(2.03, 0.5, 2.0, resolution=0.05))

    def test_resolution_does_not_absorb_a_real_breach(self):
        self.assertFalse(sample_within_window(2.4, 0.5, 2.0, resolution=0.05))

    def test_window_with_no_bound_rejected(self):
        with self.assertRaises(ValueError):
            sample_within_window(1.0, None, None)

    def test_negative_resolution_rejected(self):
        with self.assertRaises(ValueError):
            sample_within_window(1.0, 0.5, 2.0, resolution=-0.1)

    def test_margin_is_the_distance_to_the_nearest_bound(self):
        self.assertAlmostEqual(margin_to_nearest_bound(1.0, 0.5, 2.0), 0.5)

    def test_margin_is_negative_outside_the_window(self):
        self.assertAlmostEqual(margin_to_nearest_bound(2.5, 0.5, 2.0), -0.5)

    def test_margin_on_a_one_sided_floor(self):
        self.assertAlmostEqual(margin_to_nearest_bound(150.0, 100.0, None), 50.0)


class ActuationMarginTests(unittest.TestCase):
    def test_margin_against_a_factored_load(self):
        self.assertAlmostEqual(actuation_margin(10.0, 4.0, 2.0), 0.25)

    def test_exactly_sufficient_drive_gives_zero_margin(self):
        self.assertAlmostEqual(actuation_margin(8.0, 4.0, 2.0), 0.0, places=9)

    def test_insufficient_drive_gives_a_negative_margin(self):
        self.assertAlmostEqual(actuation_margin(6.0, 4.0, 2.0), -0.25)

    def test_unit_factor_is_the_default(self):
        self.assertAlmostEqual(actuation_margin(10.0, 5.0), 1.0)

    def test_zero_resisting_load_rejected(self):
        with self.assertRaises(ValueError):
            actuation_margin(10.0, 0.0, 2.0)

    def test_zero_factor_rejected(self):
        with self.assertRaises(ValueError):
            actuation_margin(10.0, 4.0, 0.0)

    def test_non_positive_drive_rejected(self):
        with self.assertRaises(ValueError):
            actuation_margin(-10.0, 4.0, 2.0)


class GradeFunctionTests(unittest.TestCase):
    def test_healthy_series_passes(self):
        record = grade_function(_fn(measured=None, samples=[1.0, 1.1, 0.9]))
        self.assertTrue(record["within_window"])
        self.assertFalse(record["intermittent"])

    def test_single_excursion_in_a_healthy_mean_is_intermittent(self):
        record = grade_function(_fn(measured=None, samples=[1.0, 2.5, 1.0]))
        self.assertTrue(record["intermittent"])
        self.assertAlmostEqual(record["worst_sample"], 2.5)
        self.assertTrue(record["mean_within_window"])

    def test_a_series_outside_the_window_throughout_is_not_intermittent(self):
        record = grade_function(_fn(measured=None, samples=[3.0, 3.1]))
        self.assertFalse(record["within_window"])
        self.assertFalse(record["intermittent"])

    def test_worst_sample_is_the_furthest_excursion(self):
        record = grade_function(_fn(measured=None, samples=[1.0, 2.2, 3.0, 1.0]))
        self.assertAlmostEqual(record["worst_sample"], 3.0)

    def test_margin_reported_is_the_worst_over_the_series(self):
        record = grade_function(_fn(measured=None, samples=[1.0, 1.9]))
        self.assertAlmostEqual(record["margin_to_bound"], 0.1)

    def test_weight_follows_the_criticality(self):
        record = grade_function(_fn(criticality=SAFETY_CRITICAL))
        self.assertAlmostEqual(record["weight"], CRITICALITY_WEIGHTS[SAFETY_CRITICAL])

    def test_mechanism_margin_is_carried_on_the_record(self):
        record = grade_function(
            _fn(available_drive=10.0, resisting_load=4.0, load_factor=2.0)
        )
        self.assertAlmostEqual(record["actuation_margin"], 0.25)

    def test_non_mechanism_has_no_actuation_margin(self):
        self.assertIsNone(grade_function(_fn())["actuation_margin"])


class IndexTests(unittest.TestCase):
    def test_all_passing_gives_unity(self):
        graded = [grade_function(_fn()), grade_function(_fn(name="second"))]
        self.assertAlmostEqual(functional_index(graded), 1.0)

    def test_index_is_weighted_by_criticality(self):
        graded = [
            grade_function(_fn(name="critical-path", criticality=SAFETY_CRITICAL)),
            grade_function(_fn(name="nice-path", criticality=NON_CRITICAL,
                               measured=9.0)),
        ]
        self.assertAlmostEqual(functional_index(graded), 0.75)

    def test_empty_graded_set_rejected(self):
        with self.assertRaises(ValueError):
            functional_index([])

    def test_malformed_graded_record_rejected(self):
        with self.assertRaises(ValueError):
            functional_index([{"name": "x"}])


class AssessmentTests(unittest.TestCase):
    def _spec(self, **overrides):
        spec = {
            "assembly_id": "MECH-2207-release-latch",
            "functions": [
                {"name": "insulation-resistance-mohm", "criticality": SAFETY_CRITICAL,
                 "min": 100.0, "measured": 150.0},
                _fn(measured=None, samples=[1.0, 1.1, 0.9]),
                {"name": "release-drive-margin", "criticality": MISSION_CRITICAL,
                 "min": 0.5, "max": 2.0, "measured": 1.2,
                 "available_drive": 10.0, "resisting_load": 4.0, "load_factor": 2.0},
            ],
        }
        spec.update(overrides)
        return spec

    def test_healthy_assembly_is_acceptable(self):
        result = assess_hardware_functionality(self._spec())
        self.assertTrue(result["acceptable"])
        self.assertEqual(result["findings"], [])
        self.assertAlmostEqual(result["functional_index"], 1.0)

    def test_assembly_id_is_carried_through(self):
        result = assess_hardware_functionality(self._spec())
        self.assertEqual(result["assembly_id"], "MECH-2207-release-latch")

    def test_safety_critical_loss_rejects_regardless_of_the_index(self):
        spec = self._spec(index_threshold=0.5)
        spec["functions"][0]["measured"] = 10.0
        result = assess_hardware_functionality(spec)
        self.assertTrue(result["safety_critical_loss"])
        self.assertFalse(result["acceptable"])

    def test_intermittency_is_reported_separately_from_a_plain_failure(self):
        spec = self._spec()
        spec["functions"][1] = _fn(measured=None, samples=[1.0, 2.5, 1.0])
        result = assess_hardware_functionality(spec)
        self.assertTrue(any("intermittent" in f for f in result["findings"]))

    def test_negative_actuation_margin_rejects(self):
        spec = self._spec()
        spec["functions"][2]["available_drive"] = 6.0
        result = assess_hardware_functionality(spec)
        self.assertFalse(result["acceptable"])
        self.assertTrue(any("actuation margin" in f for f in result["findings"]))

    def test_index_below_threshold_is_a_finding(self):
        spec = self._spec(index_threshold=1.0)
        spec["functions"][1] = _fn(measured=9.0)
        result = assess_hardware_functionality(spec)
        self.assertFalse(result["index_met"])

    def test_index_exactly_at_threshold_is_met(self):
        spec = self._spec(index_threshold=0.75)
        spec["functions"] = [
            {"name": "critical-path", "criticality": SAFETY_CRITICAL,
             "min": 0.5, "max": 2.0, "measured": 1.0},
            {"name": "nice-path", "criticality": NON_CRITICAL,
             "min": 0.5, "max": 2.0, "measured": 9.0},
        ]
        result = assess_hardware_functionality(spec)
        self.assertAlmostEqual(result["functional_index"], 0.75, places=9)
        self.assertTrue(result["index_met"])

    def test_duplicate_function_name_rejected(self):
        spec = self._spec()
        spec["functions"].append(_fn())
        with self.assertRaises(ValueError):
            assess_hardware_functionality(spec)

    def test_empty_function_list_rejected(self):
        with self.assertRaises(ValueError):
            assess_hardware_functionality(self._spec(functions=[]))

    def test_missing_functions_key_rejected(self):
        with self.assertRaises(ValueError):
            assess_hardware_functionality({"assembly_id": "x"})

    def test_non_mapping_spec_rejected(self):
        with self.assertRaises(ValueError):
            assess_hardware_functionality(["functions"])

    def test_out_of_range_threshold_rejected(self):
        with self.assertRaises(ValueError):
            assess_hardware_functionality(self._spec(index_threshold=1.5))

    def test_bound_tolerance_is_small_and_positive(self):
        self.assertGreater(BOUND_TOLERANCE, 0.0)
        self.assertLess(BOUND_TOLERANCE, 1e-6)


if __name__ == "__main__":
    unittest.main()
