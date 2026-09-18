"""Contract tests for the clause 5.4.3.5.1 hysteresis width logic."""

import unittest

from e2020_undervoltage_hysteresis_width_logic import (
    WIDTH_TOLERANCE_V,
    assess_hysteresis_width,
    declared_separation_v,
    hysteresis_declared,
    required_width_v,
    separation_fraction,
    threshold_placement_findings,
    validate_fraction,
    validate_voltage,
    width_margin_v,
    worst_case_separation_v,
)

# A 28 V regulated main bus. The trip point sits at 21.0 V and the enable
# point at 23.0 V, so the declared separation is 2.0 V. The two tolerances
# subtract 0.5 V between them, leaving a worst case of exactly 1.5 V; the
# 5 percent minimum on a 28 V bus asks for 1.4 V.
BASE = {
    "trip_v": 21.0,
    "enable_v": 23.0,
    "nominal_v": 28.0,
    "trip_tolerance_v": 0.2,
    "enable_tolerance_v": 0.3,
    "minimum_fraction": 0.05,
}


def spec(**overrides):
    merged = dict(BASE)
    merged.update(overrides)
    return merged


class VoltageValidationTests(unittest.TestCase):
    def test_positive_value_returned_as_float(self):
        self.assertEqual(validate_voltage(21, "trip_v"), 21.0)

    def test_zero_rejected_unless_allowed(self):
        with self.assertRaises(ValueError):
            validate_voltage(0.0, "trip_v")
        self.assertEqual(validate_voltage(0.0, "tolerance", allow_zero=True), 0.0)

    def test_negative_voltage_rejected(self):
        with self.assertRaises(ValueError):
            validate_voltage(-0.5, "trip_v")

    def test_boolean_rejected_as_a_voltage(self):
        with self.assertRaises(ValueError):
            validate_voltage(True, "trip_v")

    def test_non_finite_voltage_rejected(self):
        with self.assertRaises(ValueError):
            validate_voltage(float("nan"), "trip_v")

    def test_string_voltage_rejected(self):
        with self.assertRaises(ValueError):
            validate_voltage("21", "trip_v")


class FractionValidationTests(unittest.TestCase):
    def test_fraction_returned_as_float(self):
        self.assertAlmostEqual(validate_fraction(0.05, "minimum_fraction"), 0.05, places=9)

    def test_percentage_value_rejected(self):
        with self.assertRaises(ValueError):
            validate_fraction(5.0, "minimum_fraction")

    def test_negative_fraction_rejected(self):
        with self.assertRaises(ValueError):
            validate_fraction(-0.01, "minimum_fraction")

    def test_boolean_fraction_rejected(self):
        with self.assertRaises(ValueError):
            validate_fraction(False, "minimum_fraction")


class SeparationTests(unittest.TestCase):
    def test_separation_is_the_threshold_difference(self):
        self.assertAlmostEqual(declared_separation_v(21.0, 23.0), 2.0, places=9)

    def test_coincident_thresholds_give_a_zero_separation(self):
        self.assertAlmostEqual(declared_separation_v(21.0, 21.0), 0.0, places=9)

    def test_enable_below_trip_rejected(self):
        with self.assertRaises(ValueError):
            declared_separation_v(21.0, 20.0)

    def test_separation_fraction_refers_to_the_nominal_bus(self):
        self.assertAlmostEqual(separation_fraction(21.0, 22.4, 28.0), 0.05, places=9)

    def test_hysteresis_presence_is_reported(self):
        self.assertTrue(hysteresis_declared(21.0, 23.0))
        self.assertFalse(hysteresis_declared(21.0, 21.0))


class WorstCaseTests(unittest.TestCase):
    def test_both_tolerances_subtract_together(self):
        self.assertAlmostEqual(
            worst_case_separation_v(21.0, 23.0, 0.2, 0.3), 1.5, places=9
        )

    def test_zero_tolerance_leaves_the_declared_separation(self):
        self.assertAlmostEqual(
            worst_case_separation_v(21.0, 23.0, 0.0, 0.0), 2.0, places=9
        )

    def test_tolerance_stack_wider_than_the_gap_leaves_nothing(self):
        self.assertAlmostEqual(
            worst_case_separation_v(21.0, 23.0, 1.5, 1.0), 0.0, places=9
        )

    def test_negative_tolerance_rejected(self):
        with self.assertRaises(ValueError):
            worst_case_separation_v(21.0, 23.0, -0.1, 0.3)


class RequiredWidthTests(unittest.TestCase):
    def test_fraction_is_referred_to_the_nominal_bus(self):
        self.assertAlmostEqual(required_width_v(28.0, 0.05), 1.4, places=9)

    def test_absolute_floor_binds_when_it_is_larger(self):
        self.assertAlmostEqual(required_width_v(28.0, 0.05, 1.5), 1.5, places=9)

    def test_fraction_binds_when_it_is_larger(self):
        self.assertAlmostEqual(required_width_v(100.0, 0.05, 1.5), 5.0, places=9)

    def test_percentage_style_minimum_rejected(self):
        with self.assertRaises(ValueError):
            required_width_v(28.0, 5.0)

    def test_margin_is_worst_case_minus_requirement(self):
        self.assertAlmostEqual(width_margin_v(1.5, 1.4), 0.1, places=9)


class PlacementTests(unittest.TestCase):
    def test_thresholds_below_nominal_give_no_finding(self):
        self.assertEqual(threshold_placement_findings(21.0, 23.0, 28.0), [])

    def test_enable_point_at_nominal_is_unreachable(self):
        findings = threshold_placement_findings(21.0, 28.0, 28.0)
        self.assertEqual(len(findings), 1)
        self.assertIn("never be crossed", findings[0])

    def test_trip_point_at_nominal_acts_on_a_healthy_bus(self):
        findings = threshold_placement_findings(28.0, 29.0, 28.0)
        self.assertEqual(len(findings), 2)

    def test_placement_rejects_a_bad_nominal_bus(self):
        with self.assertRaises(ValueError):
            threshold_placement_findings(21.0, 23.0, 0.0)


class AssessmentTests(unittest.TestCase):
    def test_sufficient_width_is_compliant(self):
        result = assess_hysteresis_width(spec())
        self.assertEqual(result["verdict"], "compliant")
        self.assertEqual(result["findings"], [])
        self.assertTrue(result["width_sufficient"])

    def test_worst_case_is_reported_after_tolerance(self):
        result = assess_hysteresis_width(spec())
        self.assertAlmostEqual(result["declared_separation_v"], 2.0, places=9)
        self.assertAlmostEqual(result["worst_case_separation_v"], 1.5, places=9)

    def test_width_exactly_on_the_requirement_is_accepted(self):
        result = assess_hysteresis_width(spec(absolute_floor_v=1.5))
        self.assertAlmostEqual(result["width_margin_v"], 0.0, places=9)
        self.assertTrue(result["width_sufficient"])
        self.assertEqual(result["verdict"], "compliant")

    def test_absolute_floor_can_turn_a_pass_into_a_shortfall(self):
        result = assess_hysteresis_width(spec(absolute_floor_v=1.8))
        self.assertEqual(result["verdict"], "non-compliant")
        self.assertAlmostEqual(result["width_margin_v"], -0.3, places=9)

    def test_tolerance_stack_alone_can_fail_a_generous_gap(self):
        result = assess_hysteresis_width(
            spec(trip_tolerance_v=0.9, enable_tolerance_v=0.8)
        )
        self.assertEqual(result["verdict"], "non-compliant")
        self.assertAlmostEqual(result["worst_case_separation_v"], 0.3, places=9)

    def test_fully_consumed_gap_is_named_in_the_findings(self):
        result = assess_hysteresis_width(
            spec(trip_tolerance_v=1.2, enable_tolerance_v=1.0)
        )
        self.assertAlmostEqual(result["worst_case_separation_v"], 0.0, places=9)
        self.assertTrue(any("consumes the whole" in f for f in result["findings"]))

    def test_absent_hysteresis_falls_outside_the_clause(self):
        result = assess_hysteresis_width(spec(enable_v=21.0))
        self.assertEqual(result["verdict"], "not-applicable")
        self.assertFalse(result["hysteresis_declared"])
        self.assertTrue(any("does not apply" in f for f in result["findings"]))

    def test_unreachable_enable_point_fails_however_wide_the_gap(self):
        result = assess_hysteresis_width(spec(enable_v=29.0))
        self.assertEqual(result["verdict"], "non-compliant")
        self.assertTrue(any("never be crossed" in f for f in result["findings"]))

    def test_enable_below_trip_is_an_input_error(self):
        with self.assertRaises(ValueError):
            assess_hysteresis_width(spec(enable_v=20.0))

    def test_separation_percentage_of_nominal_is_reported(self):
        result = assess_hysteresis_width(spec(enable_v=22.4))
        self.assertAlmostEqual(
            result["declared_separation_pct_nominal"], 5.0, places=9
        )

    def test_missing_key_rejected(self):
        broken = spec()
        del broken["nominal_v"]
        with self.assertRaises(ValueError):
            assess_hysteresis_width(broken)

    def test_non_mapping_spec_rejected(self):
        with self.assertRaises(ValueError):
            assess_hysteresis_width([21.0, 23.0])

    def test_same_design_on_a_higher_bus_needs_a_wider_gap(self):
        on_28 = assess_hysteresis_width(spec())
        on_100 = assess_hysteresis_width(spec(nominal_v=100.0, enable_v=80.0, trip_v=70.0))
        self.assertEqual(on_28["verdict"], "compliant")
        self.assertAlmostEqual(on_100["required_width_v"], 5.0, places=9)
        self.assertEqual(on_100["verdict"], "compliant")

    def test_tolerance_constant_is_representation_sized(self):
        self.assertLess(WIDTH_TOLERANCE_V, 1e-6)


if __name__ == "__main__":
    unittest.main()
