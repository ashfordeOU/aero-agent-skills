#!/usr/bin/env python3
"""Contract test for the coverglass reflectance bandwidth requirement (offline)."""

import copy
import unittest

from e2008_reflectance_bandwidth_requirement_logic import (
    ARITHMETIC_CENTRE,
    DEFAULT_BANDWIDTH_POLICY,
    FRACTION_UNIT,
    GEOMETRIC_CENTRE,
    IMPLAUSIBLE_FRACTION_CEILING,
    MEETS_DRAWING,
    OUTSIDE_TOLERANCE,
    PERCENT_UNIT,
    REQUIREMENT_NOT_ESTABLISHED,
    assess_article_bandwidth,
    assess_bandwidth_requirement,
    band_figures,
    measured_bandwidth,
    normalise_bandwidth,
    validate_bandwidth_policy,
    validate_bandwidth_unit,
    validate_centre_convention,
    validate_drawing_requirement,
)

# On-target band: arithmetic centre 500 nm, span 200 nm, bandwidth 0.40.
ON_TARGET = (400.0, 600.0)
ON_UPPER_BOUND = (395.0, 605.0)   # span 210 nm -> 0.42
ON_LOWER_BOUND = (405.0, 595.0)   # span 190 nm -> 0.38
TOO_WIDE = (390.0, 610.0)         # span 220 nm -> 0.44
DRIFTED = (440.0, 660.0)          # span 220 nm, centre 550 nm -> 0.40

REQUIREMENT = {
    "drawing_reference": "SCD-CG-4417 rev D",
    "bandwidth": 0.40,
    "bandwidth_unit": FRACTION_UNIT,
    "tolerance": 0.02,
    "centre_nm": 500.0,
}


def _policy(**overrides):
    policy = dict(DEFAULT_BANDWIDTH_POLICY)
    policy.update(overrides)
    return policy


def _requirement(**overrides):
    requirement = dict(REQUIREMENT)
    requirement.update(overrides)
    return requirement


def _edges(article_id, band):
    return {"article_id": article_id, "cut_on_nm": band[0], "cut_off_nm": band[1]}


def _reported(article_id, bandwidth, unit=FRACTION_UNIT):
    return {"article_id": article_id, "bandwidth": bandwidth, "bandwidth_unit": unit}


def _lot(articles=None, requirement=None, lot_id="LOT-8751"):
    return {
        "lot_id": lot_id,
        "requirement": copy.deepcopy(REQUIREMENT if requirement is None else requirement),
        "articles": copy.deepcopy(articles)
        if articles is not None
        else [_edges("CG-01", ON_TARGET)],
    }


class PolicyTests(unittest.TestCase):
    def test_default_policy_validates(self):
        self.assertIs(
            validate_bandwidth_policy(DEFAULT_BANDWIDTH_POLICY), DEFAULT_BANDWIDTH_POLICY
        )

    def test_non_mapping_policy_rejected(self):
        with self.assertRaises(ValueError):
            validate_bandwidth_policy("default")

    def test_unknown_convention_in_policy_rejected(self):
        with self.assertRaises(ValueError):
            validate_bandwidth_policy(_policy(centre_convention="harmonic-mean"))

    def test_statement_tolerance_of_one_rejected(self):
        with self.assertRaises(ValueError):
            validate_bandwidth_policy(_policy(statement_relative_tolerance=1.0))

    def test_non_positive_spread_advisory_rejected(self):
        with self.assertRaises(ValueError):
            validate_bandwidth_policy(_policy(spread_advisory_fraction=0.0))

    def test_single_article_spread_advisory_rejected(self):
        with self.assertRaises(ValueError):
            validate_bandwidth_policy(_policy(min_articles_for_spread_advisory=1))

    def test_convention_is_case_insensitive(self):
        self.assertEqual(validate_centre_convention(" Arithmetic-Mean "), ARITHMETIC_CENTRE)

    def test_unknown_unit_rejected(self):
        with self.assertRaises(ValueError):
            validate_bandwidth_unit("per-mille")


class UnitTests(unittest.TestCase):
    def test_percentage_normalises_to_a_fraction(self):
        self.assertAlmostEqual(normalise_bandwidth(40.0, PERCENT_UNIT), 0.4, places=9)

    def test_fraction_passes_through(self):
        self.assertAlmostEqual(normalise_bandwidth(0.4, FRACTION_UNIT), 0.4, places=9)

    def test_percentage_typed_as_a_fraction_is_refused(self):
        with self.assertRaises(ValueError):
            normalise_bandwidth(IMPLAUSIBLE_FRACTION_CEILING, FRACTION_UNIT)

    def test_non_positive_bandwidth_refused(self):
        with self.assertRaises(ValueError):
            normalise_bandwidth(0.0, FRACTION_UNIT)


class BandFigureTests(unittest.TestCase):
    def test_span_and_both_centres_for_the_reference_band(self):
        figures = band_figures(*ON_TARGET)
        self.assertAlmostEqual(figures["span_nm"], 200.0, places=9)
        self.assertAlmostEqual(figures["arithmetic_centre_nm"], 500.0, places=9)
        self.assertAlmostEqual(figures["geometric_centre_nm"], 489.8979485566356, places=9)

    def test_arithmetic_bandwidth_of_the_reference_band(self):
        self.assertAlmostEqual(band_figures(*ON_TARGET)["arithmetic_bandwidth"], 0.4, places=9)

    def test_geometric_bandwidth_sits_above_the_arithmetic_one(self):
        figures = band_figures(*ON_TARGET)
        self.assertGreater(
            figures["geometric_bandwidth"] - figures["arithmetic_bandwidth"], 0.005
        )

    def test_inverted_band_rejected(self):
        with self.assertRaises(ValueError):
            band_figures(600.0, 400.0)

    def test_non_positive_edge_rejected(self):
        with self.assertRaises(ValueError):
            band_figures(0.0, 600.0)


class MeasurementTests(unittest.TestCase):
    def test_edges_resolve_on_the_arithmetic_convention(self):
        resolved = measured_bandwidth(_edges("CG-01", ON_TARGET), ARITHMETIC_CENTRE)
        self.assertEqual(resolved["source"], "edges")
        self.assertAlmostEqual(resolved["fractional_bandwidth"], 0.4, places=9)
        self.assertAlmostEqual(resolved["centre_nm"], 500.0, places=9)

    def test_edges_resolve_differently_on_the_geometric_convention(self):
        resolved = measured_bandwidth(_edges("CG-01", ON_TARGET), GEOMETRIC_CENTRE)
        self.assertAlmostEqual(
            resolved["fractional_bandwidth"], 0.408248290463863, places=9
        )

    def test_reported_article_resolves_without_a_centre(self):
        resolved = measured_bandwidth(_reported("CG-02", 0.41), ARITHMETIC_CENTRE)
        self.assertEqual(resolved["source"], "reported")
        self.assertIsNone(resolved["centre_nm"])
        self.assertIsNone(resolved["convention_gap"])

    def test_edges_with_a_consistent_reported_figure_are_accepted(self):
        article = _edges("CG-03", ON_TARGET)
        article["bandwidth"] = 40.0
        article["bandwidth_unit"] = PERCENT_UNIT
        resolved = measured_bandwidth(article, ARITHMETIC_CENTRE)
        self.assertAlmostEqual(resolved["fractional_bandwidth"], 0.4, places=9)

    def test_edges_with_a_disagreeing_reported_figure_are_refused(self):
        article = _edges("CG-04", ON_TARGET)
        article["bandwidth"] = 0.44
        with self.assertRaises(ValueError):
            measured_bandwidth(article, ARITHMETIC_CENTRE)

    def test_article_with_neither_edges_nor_a_figure_refused(self):
        with self.assertRaises(ValueError):
            measured_bandwidth({"article_id": "CG-05"}, ARITHMETIC_CENTRE)

    def test_non_mapping_article_refused(self):
        with self.assertRaises(ValueError):
            measured_bandwidth("CG-05", ARITHMETIC_CENTRE)


class RequirementTests(unittest.TestCase):
    def test_absent_requirement_resolves_to_none(self):
        self.assertIsNone(validate_drawing_requirement(None))

    def test_blank_drawing_reference_resolves_to_none(self):
        self.assertIsNone(validate_drawing_requirement(_requirement(drawing_reference=" ")))

    def test_non_mapping_requirement_refused(self):
        with self.assertRaises(ValueError):
            validate_drawing_requirement("SCD-CG-4417")

    def test_fraction_and_percentage_declarations_resolve_alike(self):
        as_fraction = validate_drawing_requirement(_requirement())
        as_percent = validate_drawing_requirement(
            _requirement(bandwidth=40.0, bandwidth_unit=PERCENT_UNIT, tolerance=2.0)
        )
        self.assertAlmostEqual(
            as_fraction["bandwidth_fraction"], as_percent["bandwidth_fraction"], places=9
        )
        self.assertAlmostEqual(
            as_fraction["upper_bound"], as_percent["upper_bound"], places=9
        )

    def test_bounds_are_derived_from_the_declaration(self):
        resolved = validate_drawing_requirement(_requirement())
        self.assertAlmostEqual(resolved["lower_bound"], 0.38, places=9)
        self.assertAlmostEqual(resolved["upper_bound"], 0.42, places=9)

    def test_zero_tolerance_on_both_sides_refused(self):
        with self.assertRaises(ValueError):
            validate_drawing_requirement(_requirement(tolerance=0.0))

    def test_lower_tolerance_reaching_zero_bandwidth_refused(self):
        with self.assertRaises(ValueError):
            validate_drawing_requirement(
                _requirement(tolerance_minus=0.5, tolerance_plus=0.02)
            )

    def test_drawing_convention_overrides_the_policy_default(self):
        resolved = validate_drawing_requirement(
            _requirement(centre_convention=GEOMETRIC_CENTRE)
        )
        self.assertEqual(resolved["centre_convention"], GEOMETRIC_CENTRE)


class ArticleTests(unittest.TestCase):
    def setUp(self):
        self.resolved = validate_drawing_requirement(_requirement())

    def test_on_target_article_is_within_tolerance(self):
        result = assess_article_bandwidth(_edges("CG-01", ON_TARGET), self.resolved)
        self.assertTrue(result["within_tolerance"])
        self.assertAlmostEqual(result["deviation"], 0.0, places=9)
        self.assertAlmostEqual(result["measured_percent"], 40.0, places=9)

    def test_article_exactly_on_the_upper_bound_is_admissible(self):
        result = assess_article_bandwidth(_edges("CG-02", ON_UPPER_BOUND), self.resolved)
        self.assertTrue(result["within_tolerance"])
        self.assertAlmostEqual(result["tolerance_consumed_fraction"], 1.0, places=9)

    def test_article_exactly_on_the_lower_bound_is_admissible(self):
        result = assess_article_bandwidth(_edges("CG-03", ON_LOWER_BOUND), self.resolved)
        self.assertTrue(result["within_tolerance"])

    def test_article_past_the_upper_bound_is_not_admissible(self):
        result = assess_article_bandwidth(_edges("CG-04", TOO_WIDE), self.resolved)
        self.assertFalse(result["within_tolerance"])

    def test_tolerance_consumed_uses_the_side_specific_allowance(self):
        resolved = validate_drawing_requirement(
            _requirement(tolerance_plus=0.10, tolerance_minus=0.02)
        )
        high = assess_article_bandwidth(_reported("CG-05", 0.42), resolved)
        low = assess_article_bandwidth(_reported("CG-06", 0.39), resolved)
        self.assertAlmostEqual(high["tolerance_consumed_fraction"], 0.2, places=9)
        self.assertAlmostEqual(low["tolerance_consumed_fraction"], 0.5, places=9)

    def test_article_without_an_identifier_refused(self):
        article = _edges("  ", ON_TARGET)
        with self.assertRaises(ValueError):
            assess_article_bandwidth(article, self.resolved)

    def test_unresolved_requirement_cannot_be_used_for_an_article(self):
        with self.assertRaises(ValueError):
            assess_article_bandwidth(_edges("CG-07", ON_TARGET), None)


class LotTests(unittest.TestCase):
    def test_declaration_without_a_drawing_reference_closes_the_assessment(self):
        lot = _lot(requirement=_requirement(drawing_reference=""))
        result = assess_bandwidth_requirement(lot)
        self.assertEqual(result["verdict"], REQUIREMENT_NOT_ESTABLISHED)
        self.assertEqual(result["articles"], [])

    def test_lot_on_the_declared_figure_meets_the_drawing(self):
        result = assess_bandwidth_requirement(_lot())
        self.assertEqual(result["verdict"], MEETS_DRAWING)
        self.assertEqual(result["articles_outside_tolerance"], [])
        self.assertEqual(result["advisories"], [])

    def test_one_failing_article_fails_the_lot(self):
        lot = _lot(
            [
                _edges("CG-A", ON_TARGET),
                _edges("CG-B", TOO_WIDE),
                _edges("CG-C", ON_TARGET),
            ]
        )
        result = assess_bandwidth_requirement(lot)
        self.assertEqual(result["verdict"], OUTSIDE_TOLERANCE)
        self.assertEqual(result["articles_outside_tolerance"], ["CG-B"])
        self.assertTrue(result["findings"])

    def test_worst_article_named_by_absolute_deviation(self):
        lot = _lot(
            [
                _reported("CG-A", 0.405),
                _reported("CG-B", 0.385),
                _reported("CG-C", 0.41),
            ]
        )
        result = assess_bandwidth_requirement(lot)
        self.assertEqual(result["worst_article_id"], "CG-B")

    def test_mean_and_spread_reported_for_the_lot(self):
        lot = _lot(
            [_reported("CG-A", 0.39), _reported("CG-B", 0.40), _reported("CG-C", 0.41)]
        )
        result = assess_bandwidth_requirement(lot)
        self.assertAlmostEqual(result["mean_bandwidth"], 0.4, places=9)
        self.assertAlmostEqual(result["spread"], 0.02, places=9)

    def test_a_translated_band_passes_the_ratio_and_raises_a_drift_advisory(self):
        lot = _lot([_edges("CG-A", DRIFTED), _edges("CG-B", DRIFTED)])
        result = assess_bandwidth_requirement(lot)
        self.assertEqual(result["verdict"], MEETS_DRAWING)
        self.assertTrue(any("drift" in note for note in result["advisories"]))
        self.assertAlmostEqual(result["mean_centre_nm"], 550.0, places=9)

    def test_a_band_on_the_declared_centre_raises_no_drift_advisory(self):
        lot = _lot([_edges("CG-A", ON_TARGET), _edges("CG-B", ON_TARGET)])
        result = assess_bandwidth_requirement(lot)
        self.assertFalse(any("drift" in note for note in result["advisories"]))

    def test_a_wide_band_raises_the_convention_sensitivity_advisory(self):
        requirement = _requirement(bandwidth=0.80, tolerance=0.02, centre_nm=500.0)
        lot = _lot([_edges("CG-A", (300.0, 700.0))], requirement=requirement)
        result = assess_bandwidth_requirement(lot)
        self.assertEqual(result["verdict"], MEETS_DRAWING)
        self.assertTrue(any("conventions differ" in note for note in result["advisories"]))

    def test_a_narrow_band_raises_no_convention_sensitivity_advisory(self):
        result = assess_bandwidth_requirement(_lot([_edges("CG-A", ON_TARGET)]))
        self.assertFalse(any("conventions differ" in note for note in result["advisories"]))

    def test_wide_scatter_raises_a_spread_advisory_inside_tolerance(self):
        lot = _lot(
            [_reported("CG-A", 0.385), _reported("CG-B", 0.40), _reported("CG-C", 0.415)]
        )
        result = assess_bandwidth_requirement(lot)
        self.assertEqual(result["verdict"], MEETS_DRAWING)
        self.assertTrue(any("ordinary scatter" in note for note in result["advisories"]))

    def test_duplicate_article_identifiers_refused(self):
        lot = _lot([_reported("CG-A", 0.40), _reported("CG-A", 0.41)])
        with self.assertRaises(ValueError):
            assess_bandwidth_requirement(lot)

    def test_empty_article_list_refused(self):
        with self.assertRaises(ValueError):
            assess_bandwidth_requirement(_lot([]))

    def test_lot_without_an_identifier_refused(self):
        lot = _lot()
        lot["lot_id"] = ""
        with self.assertRaises(ValueError):
            assess_bandwidth_requirement(lot)

    def test_non_mapping_lot_refused(self):
        with self.assertRaises(ValueError):
            assess_bandwidth_requirement("LOT-8751")

    def test_percentage_declaration_gives_the_same_verdict(self):
        lot = _lot(
            requirement=_requirement(
                bandwidth=40.0, bandwidth_unit=PERCENT_UNIT, tolerance=2.0
            )
        )
        result = assess_bandwidth_requirement(lot)
        self.assertEqual(result["verdict"], MEETS_DRAWING)
        self.assertEqual(result["declared_unit"], PERCENT_UNIT)

    def test_input_is_not_mutated_by_the_assessment(self):
        lot = _lot([_edges("CG-A", ON_TARGET), _reported("CG-B", 0.41)])
        before = copy.deepcopy(lot)
        assess_bandwidth_requirement(lot)
        self.assertEqual(lot, before)


if __name__ == "__main__":
    unittest.main()
