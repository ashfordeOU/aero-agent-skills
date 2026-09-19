"""Contract tests for the airborne particle counting logic."""

import unittest

from q7050_airborne_particle_counting_logic import (
    CONCENTRATION_TOLERANCE_REL,
    MAX_SIZE_UM,
    MIN_SIZE_UM,
    assess_airborne_counting,
    class_limit_per_m3,
    concentration_per_m3,
    evaluate_location,
    instrument_resolves,
    round_significant,
    validate_class,
    validate_size_um,
    validate_volume_l,
)


class RoundSignificantTests(unittest.TestCase):
    def test_three_digits_of_a_mid_value(self):
        self.assertAlmostEqual(round_significant(3516.757246163559), 3520.0, places=9)

    def test_large_value_keeps_its_magnitude(self):
        self.assertAlmostEqual(round_significant(23651441.168), 23700000.0, places=6)

    def test_small_value_keeps_its_magnitude(self):
        self.assertAlmostEqual(round_significant(0.0123456), 0.0123, places=12)

    def test_zero_is_returned_unchanged(self):
        self.assertAlmostEqual(round_significant(0.0), 0.0, places=12)

    def test_digit_count_is_honoured(self):
        self.assertAlmostEqual(round_significant(1234.5, 2), 1200.0, places=9)

    def test_zero_digits_rejected(self):
        with self.assertRaises(ValueError):
            round_significant(1234.5, 0)

    def test_non_finite_value_rejected(self):
        with self.assertRaises(ValueError):
            round_significant(float("nan"))


class ValidationTests(unittest.TestCase):
    def test_class_is_returned_as_a_float(self):
        self.assertAlmostEqual(validate_class(7), 7.0)

    def test_fractional_class_is_allowed(self):
        self.assertAlmostEqual(validate_class(4.5), 4.5)

    def test_class_below_range_rejected(self):
        with self.assertRaises(ValueError):
            validate_class(0.5)

    def test_class_above_range_rejected(self):
        with self.assertRaises(ValueError):
            validate_class(9.5)

    def test_boolean_class_rejected(self):
        with self.assertRaises(ValueError):
            validate_class(True)

    def test_size_at_the_lower_bound_is_accepted(self):
        self.assertAlmostEqual(validate_size_um(MIN_SIZE_UM), MIN_SIZE_UM, places=12)

    def test_size_at_the_upper_bound_is_accepted(self):
        self.assertAlmostEqual(validate_size_um(MAX_SIZE_UM), MAX_SIZE_UM, places=12)

    def test_size_below_the_relation_span_rejected(self):
        with self.assertRaises(ValueError):
            validate_size_um(0.05)

    def test_size_above_the_relation_span_rejected(self):
        with self.assertRaises(ValueError):
            validate_size_um(10.0)

    def test_zero_volume_rejected(self):
        with self.assertRaises(ValueError):
            validate_volume_l(0.0)


class ClassLimitTests(unittest.TestCase):
    def test_reference_size_returns_the_decade(self):
        self.assertAlmostEqual(class_limit_per_m3(5, 0.1), 100000.0, places=6)

    def test_half_micron_limit_of_a_mid_class(self):
        self.assertAlmostEqual(class_limit_per_m3(5, 0.5), 3520.0, places=6)

    def test_one_micron_limit_of_a_mid_class(self):
        self.assertAlmostEqual(class_limit_per_m3(5, 1.0), 832.0, places=6)

    def test_a_decade_of_class_is_a_decade_of_limit(self):
        ratio = class_limit_per_m3(6, 0.5) / class_limit_per_m3(5, 0.5)
        self.assertAlmostEqual(ratio, 10.0, places=9)

    def test_limit_falls_as_the_considered_size_rises(self):
        self.assertGreater(class_limit_per_m3(7, 0.5), class_limit_per_m3(7, 5.0))

    def test_fractional_class_sits_between_its_neighbours(self):
        middle = class_limit_per_m3(4.5, 0.5)
        self.assertGreater(middle, class_limit_per_m3(4, 0.5))
        self.assertLess(middle, class_limit_per_m3(5, 0.5))

    def test_out_of_span_size_refused(self):
        with self.assertRaises(ValueError):
            class_limit_per_m3(5, 0.02)


class ConcentrationTests(unittest.TestCase):
    def test_one_litre_scales_to_a_cubic_metre(self):
        self.assertAlmostEqual(concentration_per_m3(1.0, 1.0), 1000.0, places=9)

    def test_twenty_eight_litre_sample(self):
        self.assertAlmostEqual(concentration_per_m3(100.0, 28.3), 3533.568904593639, places=6)

    def test_zero_counts_is_a_real_reading(self):
        self.assertAlmostEqual(concentration_per_m3(0.0, 28.3), 0.0, places=12)

    def test_negative_counts_rejected(self):
        with self.assertRaises(ValueError):
            concentration_per_m3(-1.0, 28.3)

    def test_zero_volume_rejected(self):
        with self.assertRaises(ValueError):
            concentration_per_m3(10.0, 0.0)


class InstrumentTests(unittest.TestCase):
    def test_counter_below_the_size_resolves_it(self):
        self.assertTrue(instrument_resolves(0.5, 0.3))

    def test_counter_at_the_size_resolves_it(self):
        self.assertTrue(instrument_resolves(0.5, 0.5))

    def test_counter_above_the_size_does_not(self):
        self.assertFalse(instrument_resolves(0.3, 0.5))

    def test_zero_instrument_size_rejected(self):
        with self.assertRaises(ValueError):
            instrument_resolves(0.5, 0.0)


class LocationTests(unittest.TestCase):
    def test_counts_and_volume_are_graded(self):
        record = evaluate_location(
            {"location": "L1", "counts": 50.0, "volume_l": 28.3}, 5, 0.5
        )
        self.assertTrue(record["compliant"])
        self.assertAlmostEqual(record["limit_per_m3"], 3520.0, places=6)

    def test_a_reported_concentration_is_used_directly(self):
        record = evaluate_location(
            {"location": "L2", "concentration_per_m3": 4000.0}, 5, 0.5
        )
        self.assertFalse(record["compliant"])

    def test_a_reading_exactly_on_the_limit_is_compliant(self):
        limit = class_limit_per_m3(5, 0.5)
        record = evaluate_location(
            {"location": "L3", "concentration_per_m3": limit}, 5, 0.5
        )
        self.assertTrue(record["compliant"])
        self.assertAlmostEqual(record["utilisation"], 1.0, places=9)

    def test_margin_is_the_signed_headroom(self):
        record = evaluate_location(
            {"location": "L4", "concentration_per_m3": 3000.0}, 5, 0.5
        )
        self.assertAlmostEqual(record["margin_per_m3"], 520.0, places=6)

    def test_missing_volume_rejected(self):
        with self.assertRaises(ValueError):
            evaluate_location({"location": "L5", "counts": 50.0}, 5, 0.5)

    def test_empty_location_name_rejected(self):
        with self.assertRaises(ValueError):
            evaluate_location({"location": "  ", "counts": 1.0, "volume_l": 1.0}, 5, 0.5)

    def test_non_mapping_reading_rejected(self):
        with self.assertRaises(ValueError):
            evaluate_location(["L6"], 5, 0.5)


class AssessmentTests(unittest.TestCase):
    def _spec(self, **overrides):
        spec = {
            "iso_class": 7,
            "size_um": 0.5,
            "instrument_min_size_um": 0.3,
            "readings": [
                {"location": "L1", "counts": 2000.0, "volume_l": 28.3},
                {"location": "L2", "counts": 2500.0, "volume_l": 28.3},
                {"location": "L3", "concentration_per_m3": 120000.0},
            ],
        }
        spec.update(overrides)
        return spec

    def test_a_clean_run_is_compliant(self):
        result = assess_airborne_counting(self._spec())
        self.assertTrue(result["compliant"])
        self.assertEqual(result["findings"], [])

    def test_worst_location_is_the_highest_utilisation(self):
        result = assess_airborne_counting(self._spec())
        self.assertEqual(result["worst_location"]["location"], "L3")

    def test_one_result_per_reading(self):
        result = assess_airborne_counting(self._spec())
        self.assertEqual(len(result["results"]), 3)

    def test_an_over_limit_location_is_named(self):
        spec = self._spec()
        spec["readings"][0]["counts"] = 100000.0
        result = assess_airborne_counting(spec)
        self.assertIn("L1", result["failed_locations"])
        self.assertFalse(result["compliant"])

    def test_a_counter_that_cannot_reach_the_channel_is_flagged(self):
        result = assess_airborne_counting(self._spec(size_um=0.2))
        self.assertTrue(any("resolves down to" in f for f in result["findings"]))

    def test_a_duplicated_location_is_flagged(self):
        spec = self._spec()
        spec["readings"].append(dict(spec["readings"][0]))
        result = assess_airborne_counting(spec)
        self.assertTrue(any("more than once" in f for f in result["findings"]))

    def test_a_tighter_class_fails_the_same_air(self):
        loose = assess_airborne_counting(self._spec(iso_class=7))
        tight = assess_airborne_counting(self._spec(iso_class=5))
        self.assertTrue(loose["compliant"])
        self.assertFalse(tight["compliant"])

    def test_empty_reading_set_rejected(self):
        with self.assertRaises(ValueError):
            assess_airborne_counting(self._spec(readings=[]))

    def test_missing_key_rejected(self):
        spec = self._spec()
        del spec["size_um"]
        with self.assertRaises(ValueError):
            assess_airborne_counting(spec)

    def test_non_mapping_spec_rejected(self):
        with self.assertRaises(ValueError):
            assess_airborne_counting(["iso_class"])

    def test_tolerance_is_relative_and_tiny(self):
        self.assertLess(CONCENTRATION_TOLERANCE_REL, 1e-6)


if __name__ == "__main__":
    unittest.main()
