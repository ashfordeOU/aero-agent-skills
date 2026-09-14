#!/usr/bin/env python3
"""Contract test for the coverglass reflectance bandwidth definition (offline)."""

import copy
import unittest

from e2008_reflectance_bandwidth_definition_logic import (
    ARITHMETIC_BANDWIDTH_CEILING,
    ARITHMETIC_CENTRE,
    DEFAULT_CENTRE_CONVENTION,
    FRACTION_UNIT,
    GEOMETRIC_CENTRE,
    IMPLAUSIBLE_FRACTION_CEILING,
    PERCENT_UNIT,
    band_centre_nm,
    band_edges_from_bandwidth,
    check_band_statement,
    describe_band,
    fractional_bandwidth,
    normalise_bandwidth_declaration,
    percent_bandwidth,
    validate_band_edges,
    validate_bandwidth_unit,
    validate_centre_convention,
)

# Reference band chosen so both conventions land on exact values:
# arithmetic centre 625 nm, geometric centre 500 nm, span 750 nm.
CUT_ON_NM = 250.0
CUT_OFF_NM = 1000.0
ARITHMETIC_BANDWIDTH = 1.2
GEOMETRIC_BANDWIDTH = 1.5

ROUND_TRIP_BANDS = (
    (250.0, 1000.0),
    (400.0, 600.0),
    (350.0, 1150.0),
    (490.0, 510.0),
    (300.0, 301.0),
)


class ConventionTests(unittest.TestCase):
    def test_default_convention_validates(self):
        self.assertEqual(
            validate_centre_convention(DEFAULT_CENTRE_CONVENTION), ARITHMETIC_CENTRE
        )

    def test_convention_is_case_and_space_insensitive(self):
        self.assertEqual(validate_centre_convention("  Geometric-Mean "), GEOMETRIC_CENTRE)

    def test_unknown_convention_rejected(self):
        with self.assertRaises(ValueError):
            validate_centre_convention("harmonic-mean")

    def test_non_string_convention_rejected(self):
        with self.assertRaises(ValueError):
            validate_centre_convention(2)

    def test_unknown_bandwidth_unit_rejected(self):
        with self.assertRaises(ValueError):
            validate_bandwidth_unit("per-mille")

    def test_percent_unit_accepted(self):
        self.assertEqual(validate_bandwidth_unit("Percent"), PERCENT_UNIT)


class EdgeTests(unittest.TestCase):
    def test_valid_edges_carry_the_span(self):
        edges = validate_band_edges(CUT_ON_NM, CUT_OFF_NM)
        self.assertAlmostEqual(edges["span_nm"], 750.0, places=9)

    def test_inverted_band_rejected(self):
        with self.assertRaises(ValueError):
            validate_band_edges(CUT_OFF_NM, CUT_ON_NM)

    def test_zero_span_band_rejected(self):
        with self.assertRaises(ValueError):
            validate_band_edges(500.0, 500.0)

    def test_non_positive_cut_on_rejected(self):
        with self.assertRaises(ValueError):
            validate_band_edges(0.0, 1000.0)

    def test_infinite_edge_rejected(self):
        with self.assertRaises(ValueError):
            validate_band_edges(250.0, float("inf"))

    def test_boolean_edge_rejected(self):
        with self.assertRaises(ValueError):
            validate_band_edges(True, 1000.0)


class CentreTests(unittest.TestCase):
    def test_arithmetic_centre_is_the_mean_of_the_edges(self):
        self.assertAlmostEqual(
            band_centre_nm(CUT_ON_NM, CUT_OFF_NM, ARITHMETIC_CENTRE), 625.0, places=9
        )

    def test_geometric_centre_is_the_root_of_the_product(self):
        self.assertAlmostEqual(
            band_centre_nm(CUT_ON_NM, CUT_OFF_NM, GEOMETRIC_CENTRE), 500.0, places=9
        )

    def test_arithmetic_centre_sits_above_the_geometric_one(self):
        arithmetic = band_centre_nm(CUT_ON_NM, CUT_OFF_NM, ARITHMETIC_CENTRE)
        geometric = band_centre_nm(CUT_ON_NM, CUT_OFF_NM, GEOMETRIC_CENTRE)
        self.assertGreater(arithmetic - geometric, 1.0)


class BandwidthTests(unittest.TestCase):
    def test_arithmetic_bandwidth_is_span_over_the_arithmetic_centre(self):
        self.assertAlmostEqual(
            fractional_bandwidth(CUT_ON_NM, CUT_OFF_NM, ARITHMETIC_CENTRE),
            ARITHMETIC_BANDWIDTH,
            places=9,
        )

    def test_geometric_bandwidth_is_span_over_the_geometric_centre(self):
        self.assertAlmostEqual(
            fractional_bandwidth(CUT_ON_NM, CUT_OFF_NM, GEOMETRIC_CENTRE),
            GEOMETRIC_BANDWIDTH,
            places=9,
        )

    def test_percent_is_a_hundred_times_the_fraction(self):
        self.assertAlmostEqual(
            percent_bandwidth(CUT_ON_NM, CUT_OFF_NM, ARITHMETIC_CENTRE), 120.0, places=9
        )

    def test_bandwidth_is_unchanged_when_both_edges_are_scaled(self):
        for factor in (0.5, 1.37, 4.0):
            self.assertAlmostEqual(
                fractional_bandwidth(
                    CUT_ON_NM * factor, CUT_OFF_NM * factor, ARITHMETIC_CENTRE
                ),
                ARITHMETIC_BANDWIDTH,
                places=9,
            )

    def test_arithmetic_bandwidth_stays_under_its_ceiling(self):
        value = fractional_bandwidth(1.0, 1.0e6, ARITHMETIC_CENTRE)
        self.assertLess(value, ARITHMETIC_BANDWIDTH_CEILING)

    def test_geometric_bandwidth_exceeds_the_arithmetic_one(self):
        self.assertGreater(
            GEOMETRIC_BANDWIDTH - ARITHMETIC_BANDWIDTH, 0.2
        )

    def test_the_two_bandwidths_differ_exactly_by_the_centre_ratio(self):
        described = describe_band(CUT_ON_NM, CUT_OFF_NM)
        self.assertAlmostEqual(
            described["geometric_fractional_bandwidth"]
            / described["arithmetic_fractional_bandwidth"],
            described["arithmetic_centre_nm"] / described["geometric_centre_nm"],
            places=9,
        )


class DescribeTests(unittest.TestCase):
    def test_description_carries_span_centre_and_both_units(self):
        described = describe_band(CUT_ON_NM, CUT_OFF_NM, ARITHMETIC_CENTRE)
        self.assertAlmostEqual(described["span_nm"], 750.0, places=9)
        self.assertAlmostEqual(described["centre_nm"], 625.0, places=9)
        self.assertAlmostEqual(described["fractional_bandwidth"], 1.2, places=9)
        self.assertAlmostEqual(described["percent_bandwidth"], 120.0, places=9)

    def test_description_reports_the_edge_ratio(self):
        described = describe_band(CUT_ON_NM, CUT_OFF_NM)
        self.assertAlmostEqual(described["edge_ratio"], 4.0, places=9)

    def test_description_carries_both_conventions_whichever_is_asked_for(self):
        as_arithmetic = describe_band(CUT_ON_NM, CUT_OFF_NM, ARITHMETIC_CENTRE)
        as_geometric = describe_band(CUT_ON_NM, CUT_OFF_NM, GEOMETRIC_CENTRE)
        self.assertAlmostEqual(
            as_arithmetic["geometric_fractional_bandwidth"],
            as_geometric["fractional_bandwidth"],
            places=9,
        )
        self.assertAlmostEqual(
            as_geometric["arithmetic_fractional_bandwidth"],
            as_arithmetic["fractional_bandwidth"],
            places=9,
        )

    def test_convention_separation_is_reported_for_the_reference_band(self):
        described = describe_band(CUT_ON_NM, CUT_OFF_NM)
        self.assertAlmostEqual(described["centre_convention_separation"], 0.25, places=9)

    def test_convention_separation_is_far_smaller_for_a_narrow_band(self):
        narrow = describe_band(490.0, 510.0)["centre_convention_separation"]
        wide = describe_band(CUT_ON_NM, CUT_OFF_NM)["centre_convention_separation"]
        self.assertLess(narrow, 0.001)
        self.assertGreater(wide - narrow, 0.2)


class InversionTests(unittest.TestCase):
    def test_arithmetic_inversion_returns_the_original_edges(self):
        edges = band_edges_from_bandwidth(
            ARITHMETIC_BANDWIDTH, 625.0, ARITHMETIC_CENTRE
        )
        self.assertAlmostEqual(edges["cut_on_nm"], CUT_ON_NM, places=9)
        self.assertAlmostEqual(edges["cut_off_nm"], CUT_OFF_NM, places=9)

    def test_geometric_inversion_returns_the_original_edges(self):
        edges = band_edges_from_bandwidth(
            GEOMETRIC_BANDWIDTH, 500.0, GEOMETRIC_CENTRE
        )
        self.assertAlmostEqual(edges["cut_on_nm"], CUT_ON_NM, places=9)
        self.assertAlmostEqual(edges["cut_off_nm"], CUT_OFF_NM, places=9)

    def test_inversion_accepts_a_percentage_declaration(self):
        edges = band_edges_from_bandwidth(120.0, 625.0, ARITHMETIC_CENTRE, PERCENT_UNIT)
        self.assertAlmostEqual(edges["cut_off_nm"], CUT_OFF_NM, places=9)

    def test_every_reference_band_survives_a_round_trip(self):
        for convention in (ARITHMETIC_CENTRE, GEOMETRIC_CENTRE):
            for cut_on, cut_off in ROUND_TRIP_BANDS:
                described = describe_band(cut_on, cut_off, convention)
                back = band_edges_from_bandwidth(
                    described["fractional_bandwidth"],
                    described["centre_nm"],
                    convention,
                )
                self.assertAlmostEqual(back["cut_on_nm"], cut_on, places=9)
                self.assertAlmostEqual(back["cut_off_nm"], cut_off, places=9)

    def test_arithmetic_inversion_at_the_ceiling_rejected(self):
        with self.assertRaises(ValueError):
            band_edges_from_bandwidth(
                ARITHMETIC_BANDWIDTH_CEILING, 625.0, ARITHMETIC_CENTRE
            )

    def test_non_positive_centre_rejected_by_the_inversion(self):
        with self.assertRaises(ValueError):
            band_edges_from_bandwidth(1.2, 0.0, ARITHMETIC_CENTRE)

    def test_geometric_inversion_accepts_a_bandwidth_above_the_arithmetic_ceiling(self):
        edges = band_edges_from_bandwidth(3.0, 500.0, GEOMETRIC_CENTRE, PERCENT_UNIT)
        self.assertGreater(edges["cut_off_nm"], edges["cut_on_nm"])


class DeclarationTests(unittest.TestCase):
    def test_percent_declaration_normalises_to_a_fraction(self):
        self.assertAlmostEqual(
            normalise_bandwidth_declaration(40.0, PERCENT_UNIT), 0.4, places=9
        )

    def test_fraction_declaration_passes_through(self):
        self.assertAlmostEqual(
            normalise_bandwidth_declaration(0.4, FRACTION_UNIT), 0.4, places=9
        )

    def test_percentage_typed_as_a_fraction_is_refused(self):
        with self.assertRaises(ValueError):
            normalise_bandwidth_declaration(
                IMPLAUSIBLE_FRACTION_CEILING + 1.0, FRACTION_UNIT, GEOMETRIC_CENTRE
            )

    def test_non_positive_declaration_refused(self):
        with self.assertRaises(ValueError):
            normalise_bandwidth_declaration(0.0, FRACTION_UNIT)

    def test_unknown_unit_refused_by_the_declaration(self):
        with self.assertRaises(ValueError):
            normalise_bandwidth_declaration(0.4, "nanometres")


class StatementTests(unittest.TestCase):
    def _statement(self, **overrides):
        statement = {
            "cut_on_nm": CUT_ON_NM,
            "cut_off_nm": CUT_OFF_NM,
            "centre_nm": 625.0,
            "bandwidth": 1.2,
            "bandwidth_unit": FRACTION_UNIT,
        }
        statement.update(overrides)
        return statement

    def test_a_self_consistent_statement_is_accepted(self):
        result = check_band_statement(self._statement())
        self.assertTrue(result["consistent"])
        self.assertEqual(result["findings"], [])

    def test_a_centre_from_the_wrong_convention_is_caught(self):
        result = check_band_statement(self._statement(centre_nm=500.0))
        self.assertFalse(result["consistent"])
        self.assertFalse(result["checks"]["centre_nm"]["agrees"])

    def test_a_bandwidth_from_the_wrong_convention_is_caught(self):
        result = check_band_statement(self._statement(bandwidth=1.5))
        self.assertFalse(result["consistent"])
        self.assertFalse(result["checks"]["bandwidth"]["agrees"])

    def test_the_same_numbers_agree_under_the_geometric_convention(self):
        result = check_band_statement(
            self._statement(centre_nm=500.0, bandwidth=1.5), GEOMETRIC_CENTRE
        )
        self.assertTrue(result["consistent"])

    def test_a_percentage_bandwidth_is_reconciled_against_the_edges(self):
        result = check_band_statement(
            self._statement(bandwidth=120.0, bandwidth_unit=PERCENT_UNIT)
        )
        self.assertTrue(result["consistent"])

    def test_absent_optional_fields_are_not_checked(self):
        statement = {"cut_on_nm": CUT_ON_NM, "cut_off_nm": CUT_OFF_NM}
        result = check_band_statement(statement)
        self.assertTrue(result["consistent"])
        self.assertEqual(result["checks"], {})

    def test_a_statement_without_edges_is_refused(self):
        with self.assertRaises(ValueError):
            check_band_statement({"centre_nm": 625.0, "bandwidth": 1.2})

    def test_a_non_mapping_statement_is_refused(self):
        with self.assertRaises(ValueError):
            check_band_statement("250 to 1000 nm")

    def test_a_non_positive_tolerance_is_refused(self):
        with self.assertRaises(ValueError):
            check_band_statement(self._statement(), ARITHMETIC_CENTRE, 0.0)

    def test_the_relative_difference_is_reported_with_its_sign(self):
        result = check_band_statement(self._statement(centre_nm=650.0))
        self.assertGreater(result["checks"]["centre_nm"]["relative_difference"], 0.0)

    def test_the_statement_is_not_mutated(self):
        statement = self._statement()
        before = copy.deepcopy(statement)
        check_band_statement(statement)
        self.assertEqual(statement, before)


if __name__ == "__main__":
    unittest.main()
