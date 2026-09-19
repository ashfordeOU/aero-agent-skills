"""Contract tests for the ECSS-Q-ST-70-53C property-degradation evaluation."""

import unittest

from q7053_property_degradation_assessment_logic import (
    CATEGORIES,
    FUNCTIONAL,
    GAIN_LIMITED,
    LIMIT_TOLERANCE,
    LOSS_LIMITED,
    MECHANICAL,
    PHYSICAL,
    TWO_SIDED,
    adverse_fraction,
    assess_property_degradation,
    governing_property,
    grade_property,
    relative_change,
    rollup_by_category,
    validate_property_record,
)


def _prop(**overrides):
    record = {
        "name": "tensile-strength",
        "category": MECHANICAL,
        "direction": LOSS_LIMITED,
        "allowable_change": 0.10,
        "baseline": 50.0,
        "exposed": 48.0,
    }
    record.update(overrides)
    return record


class ValidateRecordTests(unittest.TestCase):
    def test_valid_record_is_normalised(self):
        item = validate_property_record(_prop(name="  tensile-strength  "))
        self.assertEqual(item["name"], "tensile-strength")
        self.assertAlmostEqual(item["resolution"], 0.0)

    def test_unknown_category_rejected(self):
        with self.assertRaises(ValueError):
            validate_property_record(_prop(category="chemical"))

    def test_unknown_direction_rejected(self):
        with self.assertRaises(ValueError):
            validate_property_record(_prop(direction="either-way"))

    def test_zero_baseline_rejected(self):
        with self.assertRaises(ValueError):
            validate_property_record(_prop(baseline=0.0))

    def test_negative_exposed_rejected(self):
        with self.assertRaises(ValueError):
            validate_property_record(_prop(exposed=-1.0))

    def test_non_positive_allowable_rejected(self):
        with self.assertRaises(ValueError):
            validate_property_record(_prop(allowable_change=0.0))

    def test_negative_resolution_rejected(self):
        with self.assertRaises(ValueError):
            validate_property_record(_prop(resolution=-0.1))

    def test_missing_key_rejected(self):
        record = _prop()
        del record["baseline"]
        with self.assertRaises(ValueError):
            validate_property_record(record)

    def test_boolean_baseline_rejected(self):
        with self.assertRaises(ValueError):
            validate_property_record(_prop(baseline=True))

    def test_non_mapping_record_rejected(self):
        with self.assertRaises(ValueError):
            validate_property_record(["tensile-strength"])


class RelativeChangeTests(unittest.TestCase):
    def test_loss_is_negative(self):
        change, limited = relative_change(50.0, 45.0)
        self.assertAlmostEqual(change, -0.10)
        self.assertFalse(limited)

    def test_gain_is_positive(self):
        change, _ = relative_change(50.0, 55.0)
        self.assertAlmostEqual(change, 0.10)

    def test_difference_inside_resolution_collapses_to_zero(self):
        change, limited = relative_change(50.0, 50.4, resolution=0.5)
        self.assertAlmostEqual(change, 0.0)
        self.assertTrue(limited)

    def test_difference_exactly_at_resolution_is_absorbed(self):
        change, limited = relative_change(50.0, 50.5, resolution=0.5)
        self.assertAlmostEqual(change, 0.0)
        self.assertTrue(limited)

    def test_difference_beyond_resolution_survives(self):
        change, limited = relative_change(50.0, 51.0, resolution=0.5)
        self.assertAlmostEqual(change, 0.02)
        self.assertFalse(limited)

    def test_non_positive_baseline_rejected(self):
        with self.assertRaises(ValueError):
            relative_change(0.0, 10.0)


class AdverseFractionTests(unittest.TestCase):
    def test_loss_limited_counts_only_the_loss(self):
        self.assertAlmostEqual(adverse_fraction(LOSS_LIMITED, -0.12), 0.12)

    def test_loss_limited_ignores_a_gain(self):
        self.assertAlmostEqual(adverse_fraction(LOSS_LIMITED, 0.12), 0.0)

    def test_gain_limited_counts_only_the_gain(self):
        self.assertAlmostEqual(adverse_fraction(GAIN_LIMITED, 0.07), 0.07)

    def test_gain_limited_ignores_a_loss(self):
        self.assertAlmostEqual(adverse_fraction(GAIN_LIMITED, -0.07), 0.0)

    def test_two_sided_uses_the_magnitude(self):
        self.assertAlmostEqual(adverse_fraction(TWO_SIDED, -0.03), 0.03)
        self.assertAlmostEqual(adverse_fraction(TWO_SIDED, 0.03), 0.03)

    def test_unknown_direction_rejected(self):
        with self.assertRaises(ValueError):
            adverse_fraction("downward", -0.1)


class GradePropertyTests(unittest.TestCase):
    def test_loss_inside_limit_is_within(self):
        record = grade_property(_prop(exposed=48.0))
        self.assertTrue(record["within_limit"])
        self.assertAlmostEqual(record["adverse_fraction"], 0.04)

    def test_loss_outside_limit_is_not_within(self):
        record = grade_property(_prop(exposed=40.0))
        self.assertFalse(record["within_limit"])
        self.assertAlmostEqual(record["utilisation"], 2.0)

    def test_exact_limit_is_within(self):
        record = grade_property(_prop(exposed=45.0, allowable_change=0.10))
        self.assertTrue(record["within_limit"])
        self.assertAlmostEqual(record["utilisation"], 1.0, places=9)

    def test_favourable_gain_on_loss_limited_property_passes(self):
        record = grade_property(_prop(exposed=60.0))
        self.assertTrue(record["within_limit"])
        self.assertAlmostEqual(record["adverse_fraction"], 0.0)

    def test_resolution_limited_property_is_marked(self):
        record = grade_property(_prop(exposed=49.99, resolution=0.05))
        self.assertTrue(record["resolution_limited"])
        self.assertAlmostEqual(record["adverse_fraction"], 0.0)

    def test_margin_fraction_is_reported(self):
        record = grade_property(_prop(exposed=48.0))
        self.assertAlmostEqual(record["margin_fraction"], 0.06)


class RollupTests(unittest.TestCase):
    def _graded(self):
        return [
            grade_property(_prop(name="tensile-strength", exposed=48.0)),
            grade_property(_prop(name="elongation", exposed=44.0, allowable_change=0.20)),
            grade_property(_prop(name="mass", category=PHYSICAL,
                                 direction=GAIN_LIMITED, allowable_change=0.01,
                                 baseline=100.0, exposed=100.9)),
            grade_property(_prop(name="insulation-resistance", category=FUNCTIONAL,
                                 direction=LOSS_LIMITED, allowable_change=0.30,
                                 baseline=1000.0, exposed=900.0)),
        ]

    def test_every_category_appears_in_the_rollup(self):
        rollup = rollup_by_category(self._graded())
        self.assertEqual(sorted(rollup), sorted(CATEGORIES))

    def test_measured_counts_are_grouped_correctly(self):
        rollup = rollup_by_category(self._graded())
        self.assertEqual(rollup[MECHANICAL]["measured"], 2)
        self.assertEqual(rollup[PHYSICAL]["measured"], 1)
        self.assertEqual(rollup[FUNCTIONAL]["measured"], 1)

    def test_worst_property_in_a_category_is_by_utilisation(self):
        rollup = rollup_by_category(self._graded())
        self.assertEqual(rollup[MECHANICAL]["worst_property"], "elongation")

    def test_empty_graded_set_rejected(self):
        with self.assertRaises(ValueError):
            rollup_by_category([])

    def test_unknown_category_in_graded_record_rejected(self):
        with self.assertRaises(ValueError):
            rollup_by_category([{"category": "thermal", "within_limit": True,
                                 "utilisation": 0.1, "name": "x"}])

    def test_governing_property_is_highest_utilisation(self):
        governing = governing_property(self._graded())
        self.assertEqual(governing["name"], "mass")

    def test_governing_tie_breaks_on_name(self):
        first = grade_property(_prop(name="zeta", exposed=45.0))
        second = grade_property(_prop(name="alpha", exposed=45.0))
        self.assertEqual(governing_property([first, second])["name"], "alpha")

    def test_governing_rejects_malformed_record(self):
        with self.assertRaises(ValueError):
            governing_property([{"name": "x"}])


class AssessmentTests(unittest.TestCase):
    def _spec(self, **overrides):
        spec = {
            "item_id": "PN-1042-polyimide-harness",
            "properties": [
                _prop(name="tensile-strength", exposed=48.0),
                _prop(name="mass", category=PHYSICAL, direction=GAIN_LIMITED,
                      allowable_change=0.02, baseline=100.0, exposed=100.5),
                _prop(name="insulation-resistance", category=FUNCTIONAL,
                      direction=LOSS_LIMITED, allowable_change=0.30,
                      baseline=1000.0, exposed=900.0),
            ],
        }
        spec.update(overrides)
        return spec

    def test_full_coverage_within_limits_is_acceptable(self):
        result = assess_property_degradation(self._spec())
        self.assertTrue(result["acceptable"])
        self.assertEqual(result["findings"], [])

    def test_item_id_is_carried_through(self):
        result = assess_property_degradation(self._spec())
        self.assertEqual(result["item_id"], "PN-1042-polyimide-harness")

    def test_over_limit_property_is_a_finding(self):
        spec = self._spec()
        spec["properties"][0] = _prop(name="tensile-strength", exposed=40.0)
        result = assess_property_degradation(spec)
        self.assertFalse(result["acceptable"])
        self.assertEqual(len(result["findings"]), 1)

    def test_missing_category_is_a_coverage_finding(self):
        spec = self._spec(properties=[_prop(name="tensile-strength", exposed=48.0)])
        result = assess_property_degradation(spec)
        self.assertFalse(result["categories_complete"])
        self.assertEqual(len(result["findings"]), 2)

    def test_duplicate_property_name_rejected(self):
        spec = self._spec()
        spec["properties"].append(_prop(name="tensile-strength", exposed=49.0))
        with self.assertRaises(ValueError):
            assess_property_degradation(spec)

    def test_empty_property_list_rejected(self):
        with self.assertRaises(ValueError):
            assess_property_degradation(self._spec(properties=[]))

    def test_non_mapping_spec_rejected(self):
        with self.assertRaises(ValueError):
            assess_property_degradation(["properties"])

    def test_missing_properties_key_rejected(self):
        with self.assertRaises(ValueError):
            assess_property_degradation({"item_id": "x"})

    def test_limit_tolerance_is_small_and_positive(self):
        self.assertGreater(LIMIT_TOLERANCE, 0.0)
        self.assertLess(LIMIT_TOLERANCE, 1e-6)


if __name__ == "__main__":
    unittest.main()
