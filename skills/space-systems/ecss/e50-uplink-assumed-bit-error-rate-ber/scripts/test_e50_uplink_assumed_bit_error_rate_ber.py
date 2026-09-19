#!/usr/bin/env python3
"""Gate 3 contract test for e50-uplink-assumed-bit-error-rate-ber.

stdlib unittest, offline, deterministic. Run:
    python3 test_e50_uplink_assumed_bit_error_rate_ber.py
"""

import decimal
import unittest

from e50_uplink_assumed_bit_error_rate_ber_logic import (
    INCONSISTENT,
    OPTIMISTIC,
    SOUND,
    STATED,
    UNSTATED,
    assess_assumed_uplink_ber,
    conditions_not_covered,
    decades_of_conservatism,
    derived_figures_disagreeing,
    normalise_conditions,
    parse_ber,
    same_rate,
    scaled_rate,
    validate_condition,
    worst_case_condition,
)

CONDITIONS = (
    {"name": "beginning-of-pass-low-elevation", "ber": {"mantissa": "8", "exponent": -6}},
    {"name": "mid-pass-high-elevation", "ber": "1E-9"},
    {"name": "rain-fade-worst-month", "ber": {"mantissa": "2", "exponent": -5}},
)
ASSUMED = "1E-4"


class TestRateParsing(unittest.TestCase):
    def test_a_mantissa_and_exponent_scale_exactly(self):
        self.assertEqual(scaled_rate("1", -5), decimal.Decimal("1E-5"))

    def test_a_boolean_is_not_a_rate(self):
        with self.assertRaises(ValueError):
            parse_ber(True)

    def test_a_rate_of_zero_is_refused(self):
        with self.assertRaises(ValueError):
            parse_ber("0")

    def test_a_rate_at_one_half_is_not_a_working_link(self):
        with self.assertRaises(ValueError):
            parse_ber("0.5")

    def test_an_absurdly_small_rate_is_refused_as_a_unit_mistake(self):
        with self.assertRaises(ValueError):
            parse_ber("1E-40")

    def test_a_non_integer_exponent_is_refused(self):
        with self.assertRaises(ValueError):
            scaled_rate("1", 2.5)

    def test_the_same_rate_written_two_ways_is_one_assumption(self):
        self.assertTrue(same_rate("1E-5", {"mantissa": "0.1", "exponent": -4}))

    def test_two_rates_a_decade_apart_are_not_the_same(self):
        self.assertFalse(same_rate("1E-5", "1E-6"))

    def test_a_float_rate_round_trips_without_binary_drift(self):
        self.assertTrue(same_rate(1e-5, "1E-5"))


class TestConditions(unittest.TestCase):
    def test_a_condition_without_a_name_is_refused(self):
        with self.assertRaises(ValueError):
            validate_condition({"ber": "1E-6"})

    def test_a_duplicate_condition_name_is_refused(self):
        with self.assertRaises(ValueError):
            normalise_conditions([CONDITIONS[0], dict(CONDITIONS[0])])

    def test_an_empty_condition_list_is_refused(self):
        with self.assertRaises(ValueError):
            normalise_conditions([])

    def test_conditions_come_back_in_name_order(self):
        names = [c["name"] for c in normalise_conditions(CONDITIONS)]
        self.assertEqual(names, sorted(names))

    def test_the_worst_condition_is_the_highest_rate_not_the_first(self):
        name, rate = worst_case_condition(CONDITIONS)
        self.assertEqual(name, "rain-fade-worst-month")
        self.assertEqual(rate, decimal.Decimal("2E-5"))


class TestCoverage(unittest.TestCase):
    def test_a_conservative_assumption_covers_every_condition(self):
        self.assertEqual(conditions_not_covered(ASSUMED, CONDITIONS), ())

    def test_a_mid_pass_assumption_leaves_the_worst_condition_uncovered(self):
        self.assertEqual(
            conditions_not_covered("1E-6", CONDITIONS),
            ("beginning-of-pass-low-elevation", "rain-fade-worst-month"),
        )

    def test_an_assumption_equal_to_the_worst_condition_covers_it(self):
        self.assertEqual(conditions_not_covered("2E-5", CONDITIONS), ())

    def test_the_conservatism_margin_is_reported_in_decades(self):
        self.assertAlmostEqual(decades_of_conservatism("1E-4", "1E-6"), 2.0, places=9)

    def test_an_assumption_equal_to_the_reference_has_no_margin(self):
        self.assertAlmostEqual(decades_of_conservatism("1E-5", "1E-5"), 0.0, places=9)


class TestDerivedFigures(unittest.TestCase):
    def test_a_figure_using_the_assumption_does_not_disagree(self):
        figures = ({"name": "uplink-frame-rejection-rate", "ber_used": "1E-4"},)
        self.assertEqual(derived_figures_disagreeing(ASSUMED, figures), ())

    def test_a_figure_using_a_friendlier_rate_is_named(self):
        figures = (
            {"name": "uplink-frame-rejection-rate", "ber_used": "1E-4"},
            {"name": "corrupted-uplink-frame-acceptance", "ber_used": "1E-7"},
        )
        self.assertEqual(
            derived_figures_disagreeing(ASSUMED, figures),
            ("corrupted-uplink-frame-acceptance",),
        )

    def test_a_figure_that_never_recorded_its_rate_is_named(self):
        figures = ({"name": "uplink-frame-rejection-rate"},)
        self.assertEqual(
            derived_figures_disagreeing(ASSUMED, figures),
            ("uplink-frame-rejection-rate",),
        )

    def test_an_unnamed_derived_figure_is_refused(self):
        with self.assertRaises(ValueError):
            derived_figures_disagreeing(ASSUMED, [{"ber_used": "1E-4"}])


class TestAssessment(unittest.TestCase):
    def test_a_stated_covering_and_inherited_assumption_is_sound(self):
        report = assess_assumed_uplink_ber(
            ASSUMED,
            CONDITIONS,
            ({"name": "uplink-frame-rejection-rate", "ber_used": "1E-4"},),
        )
        self.assertEqual(report["verdict"], SOUND)
        self.assertTrue(report["compliant"])
        self.assertEqual(report["statement"], STATED)

    def test_an_absent_assumption_is_unstated_and_not_compliant(self):
        report = assess_assumed_uplink_ber(None, CONDITIONS)
        self.assertEqual(report["verdict"], UNSTATED)
        self.assertFalse(report["compliant"])
        self.assertIsNone(report["assumed_ber"])

    def test_an_assumption_beaten_by_a_condition_is_optimistic(self):
        report = assess_assumed_uplink_ber("1E-6", CONDITIONS)
        self.assertEqual(report["verdict"], OPTIMISTIC)
        self.assertIn("rain-fade-worst-month", report["uncovered_conditions"])

    def test_a_derived_figure_on_another_rate_makes_the_case_inconsistent(self):
        report = assess_assumed_uplink_ber(
            ASSUMED,
            CONDITIONS,
            ({"name": "corrupted-uplink-frame-acceptance", "ber_used": "1E-8"},),
        )
        self.assertEqual(report["verdict"], INCONSISTENT)
        self.assertEqual(
            report["inconsistent_derived_figures"],
            ("corrupted-uplink-frame-acceptance",),
        )

    def test_an_optimistic_assumption_outranks_an_inconsistent_figure(self):
        report = assess_assumed_uplink_ber(
            "1E-6",
            CONDITIONS,
            ({"name": "corrupted-uplink-frame-acceptance", "ber_used": "1E-8"},),
        )
        self.assertEqual(report["verdict"], OPTIMISTIC)

    def test_the_worst_case_condition_is_reported_alongside_the_verdict(self):
        report = assess_assumed_uplink_ber(ASSUMED, CONDITIONS)
        self.assertEqual(report["worst_case_condition"], "rain-fade-worst-month")
        self.assertEqual(
            decimal.Decimal(report["worst_case_ber"]), decimal.Decimal("2E-5")
        )

    def test_the_downlink_is_not_governed_by_this_clause(self):
        with self.assertRaises(ValueError):
            assess_assumed_uplink_ber(ASSUMED, CONDITIONS, (), "downlink")


if __name__ == "__main__":
    unittest.main()
