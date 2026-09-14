#!/usr/bin/env python3
"""Contract test for the coverglass reflectance cut-off requirement (offline)."""

import copy
import unittest

from e2008_reflectance_cut_off_requirement_logic import (
    ABSOLUTE_LEVEL,
    DEFAULT_CUT_OFF_POLICY,
    MEETS_DRAWING,
    OUTSIDE_TOLERANCE,
    PLATEAU_FRACTION,
    REQUIREMENT_NOT_ESTABLISHED,
    assess_article_cut_off,
    assess_cut_off_requirement,
    crossing_level,
    cut_off_wavelength_nm,
    normalise_spectrum,
    plateau_reflectance,
    validate_cut_off_policy,
    validate_drawing_requirement,
)

# A band that plateaus at 0.75 and falls linearly to zero between 500 nm and
# 600 nm. Half of that plateau is 0.375, which the flank crosses at 550 nm.
BAND = [
    (300.0, 0.0),
    (350.0, 0.25),
    (400.0, 0.75),
    (450.0, 0.75),
    (500.0, 0.75),
    (600.0, 0.0),
    (650.0, 0.0),
]

EXPECTED_CUT_OFF_NM = 550.0

REQUIREMENT = {
    "drawing_reference": "SCD-CG-4417 rev D",
    "cut_off_nm": 550.0,
    "tolerance_nm": 5.0,
}


def _policy(**overrides):
    policy = dict(DEFAULT_CUT_OFF_POLICY)
    policy.update(overrides)
    return policy


def _requirement(**overrides):
    requirement = dict(REQUIREMENT)
    requirement.update(overrides)
    return requirement


def _article(article_id="CG-01", **overrides):
    article = {"article_id": article_id, "spectrum": copy.deepcopy(BAND)}
    article.update(overrides)
    return article


def _reported(article_id, cut_off_nm):
    return {"article_id": article_id, "cut_off_nm": cut_off_nm}


def _lot(articles=None, requirement=None, lot_id="LOT-8751"):
    return {
        "lot_id": lot_id,
        "requirement": copy.deepcopy(REQUIREMENT if requirement is None else requirement),
        "articles": copy.deepcopy(articles) if articles is not None else [_article()],
    }


class PolicyTests(unittest.TestCase):
    def test_default_policy_validates(self):
        self.assertIs(
            validate_cut_off_policy(DEFAULT_CUT_OFF_POLICY), DEFAULT_CUT_OFF_POLICY
        )

    def test_non_mapping_policy_rejected(self):
        with self.assertRaises(ValueError):
            validate_cut_off_policy("default")

    def test_unknown_crossing_convention_rejected(self):
        with self.assertRaises(ValueError):
            validate_cut_off_policy(_policy(crossing_convention="steepest-slope"))

    def test_crossing_fraction_above_one_rejected(self):
        with self.assertRaises(ValueError):
            validate_cut_off_policy(_policy(crossing_fraction=1.4))

    def test_two_point_scan_policy_rejected(self):
        with self.assertRaises(ValueError):
            validate_cut_off_policy(_policy(min_spectrum_points=2))

    def test_bias_advisory_needs_at_least_two_articles(self):
        with self.assertRaises(ValueError):
            validate_cut_off_policy(_policy(min_articles_for_bias_advisory=1))


class RequirementTests(unittest.TestCase):
    def test_absent_requirement_resolves_to_none(self):
        self.assertIsNone(validate_drawing_requirement(None))

    def test_blank_drawing_reference_resolves_to_none(self):
        self.assertIsNone(validate_drawing_requirement(_requirement(drawing_reference="  ")))

    def test_missing_drawing_reference_resolves_to_none(self):
        requirement = _requirement()
        del requirement["drawing_reference"]
        self.assertIsNone(validate_drawing_requirement(requirement))

    def test_non_mapping_requirement_rejected(self):
        with self.assertRaises(ValueError):
            validate_drawing_requirement("SCD-CG-4417")

    def test_zero_tolerance_on_both_sides_rejected(self):
        with self.assertRaises(ValueError):
            validate_drawing_requirement(
                _requirement(tolerance_nm=0.0)
            )

    def test_lower_tolerance_reaching_zero_wavelength_rejected(self):
        with self.assertRaises(ValueError):
            validate_drawing_requirement(
                _requirement(tolerance_minus_nm=600.0, tolerance_plus_nm=5.0, tolerance_nm=None)
            )

    def test_shorthand_tolerance_fills_both_sides(self):
        resolved = validate_drawing_requirement(_requirement())
        self.assertAlmostEqual(resolved["lower_bound_nm"], 545.0, places=9)
        self.assertAlmostEqual(resolved["upper_bound_nm"], 555.0, places=9)

    def test_asymmetric_tolerance_is_kept_apart(self):
        resolved = validate_drawing_requirement(
            {
                "drawing_reference": "SCD-CG-4417 rev D",
                "cut_off_nm": 550.0,
                "tolerance_plus_nm": 10.0,
                "tolerance_minus_nm": 2.0,
            }
        )
        self.assertAlmostEqual(resolved["lower_bound_nm"], 548.0, places=9)
        self.assertAlmostEqual(resolved["upper_bound_nm"], 560.0, places=9)


class SpectrumTests(unittest.TestCase):
    def test_pairs_and_mappings_normalise_alike(self):
        as_mappings = [
            {"wavelength_nm": w, "reflectance": r} for w, r in BAND
        ]
        self.assertEqual(normalise_spectrum(BAND), normalise_spectrum(as_mappings))

    def test_short_scan_rejected(self):
        with self.assertRaises(ValueError):
            normalise_spectrum(BAND[:3])

    def test_non_increasing_wavelengths_rejected(self):
        scrambled = list(BAND)
        scrambled[4], scrambled[5] = scrambled[5], scrambled[4]
        with self.assertRaises(ValueError):
            normalise_spectrum(scrambled)

    def test_reflectance_above_unity_rejected(self):
        broken = list(BAND)
        broken[3] = (450.0, 1.2)
        with self.assertRaises(ValueError):
            normalise_spectrum(broken)

    def test_non_positive_wavelength_rejected(self):
        broken = list(BAND)
        broken[0] = (0.0, 0.0)
        with self.assertRaises(ValueError):
            normalise_spectrum(broken)

    def test_malformed_sample_rejected(self):
        broken = list(BAND)
        broken[2] = (400.0, 0.75, "extra")
        with self.assertRaises(ValueError):
            normalise_spectrum(broken)


class PlateauTests(unittest.TestCase):
    def test_plateau_averages_the_run_and_does_not_take_the_peak_alone(self):
        spiked = [
            (300.0, 0.0),
            (350.0, 0.25),
            (400.0, 0.75),
            (450.0, 0.80),
            (500.0, 0.75),
            (600.0, 0.0),
            (650.0, 0.0),
        ]
        plateau = plateau_reflectance(normalise_spectrum(spiked))
        self.assertAlmostEqual(plateau["peak_reflectance"], 0.80, places=9)
        self.assertAlmostEqual(plateau["plateau_reflectance"], 0.7666666666666667, places=9)
        self.assertEqual(plateau["plateau_sample_count"], 3)

    def test_band_that_never_reflects_is_rejected(self):
        flat = [(300.0 + 50.0 * i, 0.05) for i in range(6)]
        with self.assertRaises(ValueError):
            plateau_reflectance(normalise_spectrum(flat))

    def test_half_plateau_level_is_half_the_plateau(self):
        plateau = plateau_reflectance(normalise_spectrum(BAND))
        self.assertAlmostEqual(crossing_level(plateau), 0.375, places=9)

    def test_absolute_convention_uses_the_policy_level(self):
        plateau = plateau_reflectance(normalise_spectrum(BAND))
        level = crossing_level(
            plateau,
            _policy(crossing_convention=ABSOLUTE_LEVEL, absolute_crossing_level=0.5),
        )
        self.assertAlmostEqual(level, 0.5, places=9)

    def test_level_at_or_above_the_plateau_rejected(self):
        plateau = plateau_reflectance(normalise_spectrum(BAND))
        with self.assertRaises(ValueError):
            crossing_level(
                plateau,
                _policy(crossing_convention=ABSOLUTE_LEVEL, absolute_crossing_level=1.0),
            )


class CutOffDerivationTests(unittest.TestCase):
    def test_cut_off_interpolated_between_bracketing_samples(self):
        derived = cut_off_wavelength_nm(BAND)
        self.assertAlmostEqual(derived["cut_off_nm"], EXPECTED_CUT_OFF_NM, places=9)
        self.assertAlmostEqual(derived["bracket_low_nm"], 500.0, places=9)
        self.assertAlmostEqual(derived["bracket_high_nm"], 600.0, places=9)

    def test_cut_off_does_not_move_with_flank_sampling(self):
        denser = [
            (300.0, 0.0),
            (350.0, 0.25),
            (400.0, 0.75),
            (450.0, 0.75),
            (500.0, 0.75),
            (525.0, 0.5625),
            (600.0, 0.0),
            (650.0, 0.0),
        ]
        self.assertAlmostEqual(
            cut_off_wavelength_nm(denser)["cut_off_nm"],
            cut_off_wavelength_nm(BAND)["cut_off_nm"],
            places=9,
        )

    def test_sample_landing_on_the_level_is_taken_as_the_edge(self):
        on_level = [
            (300.0, 0.0),
            (350.0, 0.25),
            (400.0, 0.75),
            (450.0, 0.75),
            (500.0, 0.75),
            (550.0, 0.375),
            (600.0, 0.0),
        ]
        self.assertAlmostEqual(
            cut_off_wavelength_nm(on_level)["cut_off_nm"], 550.0, places=9
        )

    def test_scan_that_stops_before_the_flank_is_rejected(self):
        truncated = [
            (300.0, 0.0),
            (350.0, 0.25),
            (400.0, 0.75),
            (450.0, 0.75),
            (500.0, 0.75),
        ]
        with self.assertRaises(ValueError):
            cut_off_wavelength_nm(truncated)

    def test_a_lower_crossing_fraction_moves_the_edge_outward(self):
        quarter = cut_off_wavelength_nm(
            BAND, _policy(crossing_convention=PLATEAU_FRACTION, crossing_fraction=0.25)
        )
        self.assertAlmostEqual(quarter["cut_off_nm"], 575.0, places=9)


class ArticleTests(unittest.TestCase):
    def setUp(self):
        self.resolved = validate_drawing_requirement(_requirement())

    def test_article_on_the_drawing_value_is_within_tolerance(self):
        result = assess_article_cut_off(_article(), self.resolved)
        self.assertTrue(result["within_tolerance"])
        self.assertAlmostEqual(result["deviation_nm"], 0.0, places=9)
        self.assertAlmostEqual(result["tolerance_consumed_fraction"], 0.0, places=9)

    def test_article_exactly_on_the_upper_bound_is_admissible(self):
        result = assess_article_cut_off(_reported("CG-02", 555.0), self.resolved)
        self.assertTrue(result["within_tolerance"])
        self.assertAlmostEqual(result["tolerance_consumed_fraction"], 1.0, places=9)

    def test_article_past_the_upper_bound_is_not_admissible(self):
        result = assess_article_cut_off(_reported("CG-03", 556.5), self.resolved)
        self.assertFalse(result["within_tolerance"])

    def test_article_past_the_lower_bound_is_not_admissible(self):
        result = assess_article_cut_off(_reported("CG-04", 543.0), self.resolved)
        self.assertFalse(result["within_tolerance"])

    def test_tolerance_consumed_uses_the_side_specific_allowance(self):
        resolved = validate_drawing_requirement(
            {
                "drawing_reference": "SCD-CG-4417 rev D",
                "cut_off_nm": 550.0,
                "tolerance_plus_nm": 10.0,
                "tolerance_minus_nm": 2.0,
            }
        )
        high = assess_article_cut_off(_reported("CG-05", 552.0), resolved)
        low = assess_article_cut_off(_reported("CG-06", 549.0), resolved)
        self.assertAlmostEqual(high["tolerance_consumed_fraction"], 0.2, places=9)
        self.assertAlmostEqual(low["tolerance_consumed_fraction"], 0.5, places=9)

    def test_reported_cut_off_is_used_when_no_spectrum_is_supplied(self):
        result = assess_article_cut_off(_reported("CG-07", 551.0), self.resolved)
        self.assertEqual(result["derivation"]["source"], "reported")

    def test_spectrum_is_preferred_over_a_reported_value(self):
        article = _article(article_id="CG-08", cut_off_nm=520.0)
        result = assess_article_cut_off(article, self.resolved)
        self.assertEqual(result["derivation"]["source"], "spectrum")
        self.assertAlmostEqual(result["measured_cut_off_nm"], EXPECTED_CUT_OFF_NM, places=9)

    def test_article_without_an_identifier_rejected(self):
        with self.assertRaises(ValueError):
            assess_article_cut_off(_article(article_id="  "), self.resolved)

    def test_unresolved_requirement_cannot_be_used_for_an_article(self):
        with self.assertRaises(ValueError):
            assess_article_cut_off(_article(), None)


class LotTests(unittest.TestCase):
    def test_requirement_without_a_drawing_reference_closes_the_assessment(self):
        lot = _lot(requirement=_requirement(drawing_reference=""))
        result = assess_cut_off_requirement(lot)
        self.assertEqual(result["verdict"], REQUIREMENT_NOT_ESTABLISHED)
        self.assertEqual(result["articles"], [])

    def test_lot_on_the_drawing_value_meets_it(self):
        result = assess_cut_off_requirement(_lot())
        self.assertEqual(result["verdict"], MEETS_DRAWING)
        self.assertEqual(result["articles_outside_tolerance"], [])

    def test_one_failing_article_fails_the_lot(self):
        lot = _lot(
            [_reported("CG-A", 551.0), _reported("CG-B", 562.0), _reported("CG-C", 549.0)]
        )
        result = assess_cut_off_requirement(lot)
        self.assertEqual(result["verdict"], OUTSIDE_TOLERANCE)
        self.assertEqual(result["articles_outside_tolerance"], ["CG-B"])
        self.assertTrue(result["findings"])

    def test_worst_article_is_named_by_absolute_deviation(self):
        lot = _lot(
            [_reported("CG-A", 551.0), _reported("CG-B", 546.0), _reported("CG-C", 552.0)]
        )
        result = assess_cut_off_requirement(lot)
        self.assertEqual(result["worst_article_id"], "CG-B")

    def test_mean_and_spread_reported_for_the_lot(self):
        lot = _lot(
            [_reported("CG-A", 548.0), _reported("CG-B", 550.0), _reported("CG-C", 552.0)]
        )
        result = assess_cut_off_requirement(lot)
        self.assertAlmostEqual(result["mean_cut_off_nm"], 550.0, places=9)
        self.assertAlmostEqual(result["spread_nm"], 4.0, places=9)

    def test_wide_spread_raises_an_advisory_even_inside_tolerance(self):
        lot = _lot(
            [_reported("CG-A", 545.0), _reported("CG-B", 550.0), _reported("CG-C", 555.0)]
        )
        result = assess_cut_off_requirement(lot)
        self.assertEqual(result["verdict"], MEETS_DRAWING)
        self.assertTrue(any("spans" in note for note in result["advisories"]))

    def test_one_sided_offset_raises_a_run_bias_advisory(self):
        lot = _lot(
            [_reported("CG-A", 553.0), _reported("CG-B", 553.5), _reported("CG-C", 554.0)]
        )
        result = assess_cut_off_requirement(lot)
        self.assertEqual(result["verdict"], MEETS_DRAWING)
        self.assertTrue(any("run bias" in note for note in result["advisories"]))

    def test_deviations_straddling_the_value_raise_no_bias_advisory(self):
        lot = _lot(
            [_reported("CG-A", 553.0), _reported("CG-B", 550.5), _reported("CG-C", 547.5)]
        )
        result = assess_cut_off_requirement(lot)
        self.assertFalse(any("run bias" in note for note in result["advisories"]))

    def test_duplicate_article_identifiers_rejected(self):
        lot = _lot([_reported("CG-A", 550.0), _reported("CG-A", 551.0)])
        with self.assertRaises(ValueError):
            assess_cut_off_requirement(lot)

    def test_empty_article_list_rejected(self):
        with self.assertRaises(ValueError):
            assess_cut_off_requirement(_lot([]))

    def test_lot_without_an_identifier_rejected(self):
        lot = _lot()
        lot["lot_id"] = ""
        with self.assertRaises(ValueError):
            assess_cut_off_requirement(lot)

    def test_non_mapping_lot_rejected(self):
        with self.assertRaises(ValueError):
            assess_cut_off_requirement("LOT-8751")

    def test_input_is_not_mutated_by_the_assessment(self):
        lot = _lot([_article("CG-A"), _reported("CG-B", 551.0)])
        before = copy.deepcopy(lot)
        assess_cut_off_requirement(lot)
        self.assertEqual(lot, before)


if __name__ == "__main__":
    unittest.main()
