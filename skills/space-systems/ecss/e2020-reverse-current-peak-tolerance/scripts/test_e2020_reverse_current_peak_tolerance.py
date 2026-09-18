"""Contract tests for the clause 5.4.1.2.1 reverse current peak tolerance logic."""

import unittest

from e2020_reverse_current_peak_tolerance_logic import (
    CAPABILITY_STATES,
    LIMITER_CATEGORIES,
    PEAK_TOLERANCE_A,
    REPETITION_DERATING_FLOOR,
    REPETITION_DERATING_PER_EVENT,
    REVERSE_CLAUSE_CATEGORIES,
    assess_reverse_current_peak,
    duration_derating_factor,
    normalise_capability,
    normalise_category,
    peak_margin_a,
    repetition_derating_factor,
    required_rated_multiple,
    tolerated_reverse_peak_a,
    validate_channel,
    validate_transient,
)

# A latching channel rated to withstand four times its 1 A limitation current
# for 10 ms in reverse, with the capability called for.
BASE_CHANNEL = {
    "category": "latching",
    "reverse_capability": "applicable",
    "nominal_limitation_current_a": 1.0,
    "rated_peak_multiple": 4.0,
    "rated_peak_duration_ms": 10.0,
}

# A single 2 A pulse inside the rated duration.
BASE_TRANSIENT = {
    "peak_current_a": 2.0,
    "duration_ms": 5.0,
    "repetitions": 1,
}


def channel(**overrides):
    merged = dict(BASE_CHANNEL)
    merged.update(overrides)
    return merged


def transient(**overrides):
    merged = dict(BASE_TRANSIENT)
    merged.update(overrides)
    return merged


class NormalisationTests(unittest.TestCase):
    def test_category_aliases_are_folded(self):
        self.assertEqual(normalise_category("LCL"), "latching")
        self.assertEqual(normalise_category(" fcl "), "foldback")

    def test_unknown_category_rejected(self):
        with self.assertRaises(ValueError):
            normalise_category("relay")

    def test_non_string_category_rejected(self):
        with self.assertRaises(ValueError):
            normalise_category(7)

    def test_capability_aliases_are_folded(self):
        self.assertEqual(normalise_capability("required"), "applicable")
        self.assertEqual(normalise_capability("NOT-REQUIRED"), "not-applicable")

    def test_unknown_capability_rejected(self):
        with self.assertRaises(ValueError):
            normalise_capability("maybe")

    def test_vocabularies_are_fixed(self):
        self.assertEqual(REVERSE_CLAUSE_CATEGORIES, ("latching",))
        self.assertEqual(CAPABILITY_STATES, ("applicable", "not-applicable"))
        self.assertIn("foldback", LIMITER_CATEGORIES)


class ValidationTests(unittest.TestCase):
    def test_valid_channel_is_canonicalised(self):
        validated = validate_channel(channel(category="lcl"))
        self.assertEqual(validated["category"], "latching")
        self.assertAlmostEqual(validated["rated_peak_multiple"], 4.0, places=9)

    def test_non_mapping_channel_rejected(self):
        with self.assertRaises(ValueError):
            validate_channel(["latching"])

    def test_missing_rated_duration_rejected(self):
        broken = channel()
        del broken["rated_peak_duration_ms"]
        with self.assertRaises(ValueError):
            validate_channel(broken)

    def test_zero_limitation_current_rejected(self):
        with self.assertRaises(ValueError):
            validate_channel(channel(nominal_limitation_current_a=0.0))

    def test_boolean_multiple_rejected(self):
        with self.assertRaises(ValueError):
            validate_channel(channel(rated_peak_multiple=True))

    def test_negative_peak_current_rejected(self):
        with self.assertRaises(ValueError):
            validate_transient(transient(peak_current_a=-2.0))

    def test_non_integer_repetitions_rejected(self):
        with self.assertRaises(ValueError):
            validate_transient(transient(repetitions=2.5))

    def test_zero_repetitions_rejected(self):
        with self.assertRaises(ValueError):
            validate_transient(transient(repetitions=0))

    def test_missing_transient_key_rejected(self):
        broken = transient()
        del broken["duration_ms"]
        with self.assertRaises(ValueError):
            validate_transient(broken)


class DeratingTests(unittest.TestCase):
    def test_pulse_inside_the_rated_duration_keeps_the_full_rating(self):
        self.assertAlmostEqual(duration_derating_factor(5.0, 10.0), 1.0, places=9)

    def test_pulse_exactly_on_the_rated_duration_keeps_the_full_rating(self):
        self.assertAlmostEqual(duration_derating_factor(10.0, 10.0), 1.0, places=9)

    def test_quadruple_duration_halves_the_tolerated_peak(self):
        self.assertAlmostEqual(duration_derating_factor(40.0, 10.0), 0.5, places=9)

    def test_duration_derating_rejects_a_zero_pulse(self):
        with self.assertRaises(ValueError):
            duration_derating_factor(0.0, 10.0)

    def test_single_event_carries_no_repetition_derating(self):
        self.assertAlmostEqual(repetition_derating_factor(1), 1.0, places=9)

    def test_repetition_derating_erodes_linearly(self):
        self.assertAlmostEqual(
            repetition_derating_factor(3),
            1.0 - 2.0 * REPETITION_DERATING_PER_EVENT,
            places=9,
        )

    def test_repetition_derating_stops_at_its_floor(self):
        self.assertAlmostEqual(
            repetition_derating_factor(40), REPETITION_DERATING_FLOOR, places=9
        )

    def test_repetition_derating_rejects_a_non_integer_count(self):
        with self.assertRaises(ValueError):
            repetition_derating_factor("three")


class ToleratedPeakTests(unittest.TestCase):
    def test_tolerated_peak_is_the_rating_when_nothing_derates(self):
        value = tolerated_reverse_peak_a(
            validate_channel(channel()), validate_transient(transient())
        )
        self.assertAlmostEqual(value, 4.0, places=9)

    def test_long_pulse_lowers_the_tolerated_peak(self):
        value = tolerated_reverse_peak_a(
            validate_channel(channel()),
            validate_transient(transient(duration_ms=40.0)),
        )
        self.assertAlmostEqual(value, 2.0, places=9)

    def test_margin_is_tolerated_less_applied(self):
        value = peak_margin_a(
            validate_channel(channel()),
            validate_transient(transient(peak_current_a=3.0)),
        )
        self.assertAlmostEqual(value, 1.0, places=9)

    def test_required_multiple_names_the_rating_the_transient_needs(self):
        value = required_rated_multiple(
            validate_channel(channel()),
            validate_transient(transient(peak_current_a=6.0)),
        )
        self.assertAlmostEqual(value, 6.0, places=9)

    def test_required_multiple_grows_with_a_long_pulse(self):
        value = required_rated_multiple(
            validate_channel(channel()),
            validate_transient(transient(peak_current_a=6.0, duration_ms=40.0)),
        )
        self.assertAlmostEqual(value, 12.0, places=9)


class AssessmentTests(unittest.TestCase):
    def test_transient_inside_the_rating_is_compliant(self):
        result = assess_reverse_current_peak(channel(), transient())
        self.assertEqual(result["verdict"], "compliant")
        self.assertTrue(result["tolerant"])
        self.assertEqual(result["findings"], [])

    def test_peak_exactly_on_the_tolerated_value_is_accepted(self):
        result = assess_reverse_current_peak(
            channel(), transient(peak_current_a=4.0)
        )
        self.assertAlmostEqual(result["peak_margin_a"], 0.0, places=9)
        self.assertEqual(result["verdict"], "compliant")

    def test_peak_above_the_rating_is_non_compliant(self):
        result = assess_reverse_current_peak(
            channel(), transient(peak_current_a=6.0)
        )
        self.assertEqual(result["verdict"], "non-compliant")
        self.assertTrue(any("exceeds" in f for f in result["findings"]))

    def test_long_pulse_can_fail_a_peak_that_the_headline_rating_covers(self):
        result = assess_reverse_current_peak(
            channel(), transient(peak_current_a=3.0, duration_ms=40.0)
        )
        self.assertAlmostEqual(result["rated_peak_a"], 4.0, places=9)
        self.assertAlmostEqual(result["tolerated_peak_a"], 2.0, places=9)
        self.assertEqual(result["verdict"], "non-compliant")

    def test_repetitions_erode_the_reported_tolerated_peak(self):
        result = assess_reverse_current_peak(
            channel(), transient(repetitions=3)
        )
        self.assertAlmostEqual(result["repetition_derating_factor"], 0.9, places=9)
        self.assertAlmostEqual(result["tolerated_peak_a"], 3.6, places=9)

    def test_repetition_floor_is_reported_as_a_finding(self):
        result = assess_reverse_current_peak(
            channel(), transient(repetitions=20)
        )
        self.assertEqual(result["verdict"], "non-compliant")
        self.assertTrue(any("floor" in f for f in result["findings"]))

    def test_rating_below_the_limitation_current_is_a_finding(self):
        result = assess_reverse_current_peak(
            channel(rated_peak_multiple=0.5),
            transient(peak_current_a=0.2),
        )
        self.assertEqual(result["verdict"], "non-compliant")
        self.assertTrue(any("below the channel" in f for f in result["findings"]))

    def test_foldback_category_is_reported_out_of_scope(self):
        result = assess_reverse_current_peak(channel(category="foldback"), transient())
        self.assertEqual(result["verdict"], "out-of-scope")
        self.assertFalse(result["in_scope"])

    def test_channel_without_reverse_capability_is_out_of_scope_and_names_the_gap(self):
        result = assess_reverse_current_peak(
            channel(reverse_capability="not-required"), transient()
        )
        self.assertEqual(result["verdict"], "out-of-scope")
        self.assertTrue(any("bounded by nothing" in f for f in result["findings"]))

    def test_out_of_scope_still_reports_the_derated_numbers(self):
        result = assess_reverse_current_peak(
            channel(reverse_capability="none"),
            transient(duration_ms=40.0),
        )
        self.assertAlmostEqual(result["duration_derating_factor"], 0.5, places=9)
        self.assertAlmostEqual(result["tolerated_peak_a"], 2.0, places=9)

    def test_peak_tolerance_is_representation_sized(self):
        self.assertLess(PEAK_TOLERANCE_A, 1e-6)


if __name__ == "__main__":
    unittest.main()
