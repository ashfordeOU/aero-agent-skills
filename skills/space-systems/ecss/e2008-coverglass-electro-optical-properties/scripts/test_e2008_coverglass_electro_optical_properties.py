"""Contract tests for the clause 8.7.3 coverglass resistivity characterization."""

import math
import unittest

from e2008_coverglass_electro_optical_properties_logic import (
    BULK_PROPERTY,
    CONCENTRIC_RING,
    DEFAULT_CHARACTERIZATION_POLICY,
    OUTSIDE_DECLARED_BAND,
    PROPERTIES_CHARACTERIZED,
    PROPERTY_SET_INCOMPLETE,
    RECTANGULAR_BAR,
    REQUIREMENT_NOT_ESTABLISHED,
    SURFACE_PROPERTY,
    assess_electro_optical_properties,
    bulk_volume_resistivity_ohm_m,
    concentric_ring_geometry_factor,
    meets_surface_ceiling,
    rectangular_bar_geometry_factor,
    reduce_article,
    spread_decades,
    spread_ratio,
    surface_geometry_factor,
    surface_resistivity_ohm_per_square,
    validate_characterization_policy,
    validate_declared_band,
    within_band,
)

BULK_MIN = 1.0e12
BULK_MAX = 1.0e15
SURFACE_CEILING = 1.0e9


def _policy(**overrides):
    policy = dict(DEFAULT_CHARACTERIZATION_POLICY)
    policy.update(overrides)
    return policy


def _band(**overrides):
    band = {
        "drawing_reference": "CAD-5182 issue B",
        "bulk_min_ohm_m": BULK_MIN,
        "bulk_max_ohm_m": BULK_MAX,
        "surface_max_ohm_per_square": SURFACE_CEILING,
    }
    band.update(overrides)
    return band


def _article(identifier="cg-01", bulk=1.0e13, surface=2.0e8, coated=True):
    return {
        "id": identifier,
        "coating_present": coated,
        "bulk_measurement": {"resistivity_ohm_m": bulk},
        "surface_measurement": {"resistivity_ohm_per_square": surface},
    }


def _case(**overrides):
    case = {
        "declared_band": _band(),
        "articles": [
            _article("cg-01", 1.0e13, 2.0e8),
            _article("cg-02", 2.0e13, 3.0e8),
        ],
    }
    case.update(overrides)
    return case


class PolicyTests(unittest.TestCase):
    def test_default_policy_validates(self):
        self.assertIs(
            validate_characterization_policy(DEFAULT_CHARACTERIZATION_POLICY),
            DEFAULT_CHARACTERIZATION_POLICY,
        )

    def test_a_non_mapping_policy_rejected(self):
        with self.assertRaises(ValueError):
            validate_characterization_policy("decades")

    def test_a_zero_spread_allowance_rejected(self):
        with self.assertRaises(ValueError):
            validate_characterization_policy(_policy(max_article_spread_decades=0.0))

    def test_a_non_boolean_ceiling_requirement_rejected(self):
        with self.assertRaises(ValueError):
            validate_characterization_policy(
                _policy(require_surface_ceiling_when_coated="yes")
            )


class ReductionTests(unittest.TestCase):
    def test_bulk_resistivity_is_resistance_times_area_over_thickness(self):
        self.assertAlmostEqual(
            bulk_volume_resistivity_ohm_m(2.0e15, 1.0e-4, 2.0e-4) / 1.0e15,
            1.0,
            places=12,
        )

    def test_a_zero_thickness_rejected(self):
        with self.assertRaises(ValueError):
            bulk_volume_resistivity_ohm_m(1.0e15, 1.0e-4, 0.0)

    def test_a_negative_resistance_rejected(self):
        with self.assertRaises(ValueError):
            bulk_volume_resistivity_ohm_m(-1.0, 1.0e-4, 1.0e-4)

    def test_the_ring_geometry_factor_follows_the_radius_ratio(self):
        self.assertAlmostEqual(
            concentric_ring_geometry_factor(1.0e-2, 2.0e-2),
            2.0 * math.pi / math.log(2.0),
            places=9,
        )

    def test_rings_that_touch_are_rejected(self):
        with self.assertRaises(ValueError):
            concentric_ring_geometry_factor(2.0e-2, 2.0e-2)

    def test_the_bar_geometry_factor_is_width_over_gap(self):
        self.assertAlmostEqual(
            rectangular_bar_geometry_factor(5.0e-2, 1.0e-2), 5.0, places=12
        )

    def test_a_zero_electrode_gap_rejected(self):
        with self.assertRaises(ValueError):
            rectangular_bar_geometry_factor(5.0e-2, 0.0)

    def test_surface_resistivity_is_resistance_times_the_geometry_factor(self):
        self.assertAlmostEqual(
            surface_resistivity_ohm_per_square(1.0e8, 5.0) / 5.0e8, 1.0, places=12
        )

    def test_an_unknown_electrode_arrangement_rejected(self):
        with self.assertRaises(ValueError):
            surface_geometry_factor({"arrangement": "four-point-probe"})

    def test_a_bar_geometry_record_reduces(self):
        factor = surface_geometry_factor(
            {
                "arrangement": RECTANGULAR_BAR,
                "electrode_width_m": 4.0e-2,
                "electrode_gap_m": 2.0e-2,
            }
        )
        self.assertAlmostEqual(factor, 2.0, places=12)

    def test_a_ring_geometry_record_reduces(self):
        factor = surface_geometry_factor(
            {
                "arrangement": CONCENTRIC_RING,
                "inner_radius_m": 1.0e-2,
                "outer_radius_m": math.e * 1.0e-2,
            }
        )
        self.assertAlmostEqual(factor, 2.0 * math.pi, places=9)

    def test_an_article_reduces_from_raw_geometry(self):
        article = {
            "id": "cg-07",
            "coating_present": True,
            "bulk_measurement": {
                "resistance_ohm": 2.0e15,
                "electrode_area_m2": 1.0e-4,
                "thickness_m": 2.0e-4,
            },
            "surface_measurement": {
                "resistance_ohm": 1.0e8,
                "geometry": {
                    "arrangement": RECTANGULAR_BAR,
                    "electrode_width_m": 4.0e-2,
                    "electrode_gap_m": 2.0e-2,
                },
            },
        }
        entry = reduce_article(article)
        self.assertAlmostEqual(
            entry["bulk_volume_resistivity_ohm_m"] / 1.0e15, 1.0, places=12
        )
        self.assertAlmostEqual(
            entry["surface_resistivity_ohm_per_square"] / 2.0e8, 1.0, places=12
        )
        self.assertTrue(entry["properties_complete"])

    def test_a_missing_surface_measurement_is_named(self):
        article = _article()
        del article["surface_measurement"]
        entry = reduce_article(article)
        self.assertEqual(entry["missing_properties"], (SURFACE_PROPERTY,))
        self.assertFalse(entry["properties_complete"])

    def test_a_missing_bulk_measurement_is_named(self):
        article = _article()
        del article["bulk_measurement"]
        entry = reduce_article(article)
        self.assertEqual(entry["missing_properties"], (BULK_PROPERTY,))

    def test_a_non_boolean_coating_flag_rejected(self):
        article = _article()
        article["coating_present"] = "coated"
        with self.assertRaises(ValueError):
            reduce_article(article)

    def test_a_blank_article_id_rejected(self):
        with self.assertRaises(ValueError):
            reduce_article(_article("   "))


class BandTests(unittest.TestCase):
    def test_a_referenced_band_validates(self):
        reference, low, high, ceiling = validate_declared_band(_band())
        self.assertEqual(reference, "CAD-5182 issue B")
        self.assertAlmostEqual(low / BULK_MIN, 1.0, places=12)
        self.assertAlmostEqual(high / BULK_MAX, 1.0, places=12)
        self.assertAlmostEqual(ceiling / SURFACE_CEILING, 1.0, places=12)

    def test_an_inverted_band_rejected(self):
        with self.assertRaises(ValueError):
            validate_declared_band(_band(bulk_min_ohm_m=BULK_MAX, bulk_max_ohm_m=BULK_MIN))

    def test_a_band_with_no_ceiling_validates(self):
        _reference, _low, _high, ceiling = validate_declared_band(
            _band(surface_max_ohm_per_square=None)
        )
        self.assertIsNone(ceiling)

    def test_a_value_inside_the_band_passes(self):
        self.assertTrue(within_band(1.0e13, BULK_MIN, BULK_MAX))

    def test_a_value_exactly_on_the_lower_edge_passes(self):
        self.assertAlmostEqual(BULK_MIN / BULK_MIN, 1.0, places=12)
        self.assertTrue(within_band(BULK_MIN, BULK_MIN, BULK_MAX))

    def test_a_value_exactly_on_the_upper_edge_passes(self):
        self.assertTrue(within_band(BULK_MAX, BULK_MIN, BULK_MAX))

    def test_a_value_below_the_band_fails(self):
        self.assertFalse(within_band(1.0e9, BULK_MIN, BULK_MAX))

    def test_a_coating_at_its_ceiling_meets_it(self):
        self.assertTrue(meets_surface_ceiling(SURFACE_CEILING, SURFACE_CEILING))

    def test_a_coating_above_its_ceiling_does_not_meet_it(self):
        self.assertFalse(meets_surface_ceiling(1.0e11, SURFACE_CEILING))


class SpreadTests(unittest.TestCase):
    def test_the_spread_ratio_is_largest_over_smallest(self):
        self.assertAlmostEqual(spread_ratio([2.0, 20.0, 5.0]), 10.0, places=12)

    def test_an_empty_population_rejected(self):
        with self.assertRaises(ValueError):
            spread_ratio([])

    def test_a_decade_of_spread_reads_as_one(self):
        self.assertAlmostEqual(spread_decades([1.0e12, 1.0e13]), 1.0, places=9)

    def test_an_identical_population_has_no_spread(self):
        self.assertAlmostEqual(spread_decades([5.0e12, 5.0e12]), 0.0, places=12)


class AssessmentTests(unittest.TestCase):
    def test_a_complete_in_band_subgroup_is_characterized(self):
        result = assess_electro_optical_properties(_case())
        self.assertEqual(result["verdict"], PROPERTIES_CHARACTERIZED)
        self.assertEqual(result["findings"], [])

    def test_the_drawing_reference_travels_with_the_verdict(self):
        result = assess_electro_optical_properties(_case())
        self.assertEqual(result["drawing_reference"], "CAD-5182 issue B")

    def test_no_declared_band_leaves_the_criterion_unestablished(self):
        case = _case()
        del case["declared_band"]
        result = assess_electro_optical_properties(case)
        self.assertEqual(result["verdict"], REQUIREMENT_NOT_ESTABLISHED)

    def test_a_blank_drawing_reference_leaves_it_unestablished(self):
        result = assess_electro_optical_properties(
            _case(declared_band=_band(drawing_reference="  "))
        )
        self.assertEqual(result["verdict"], REQUIREMENT_NOT_ESTABLISHED)

    def test_a_half_populated_article_stops_at_incomplete(self):
        case = _case()
        del case["articles"][1]["surface_measurement"]
        result = assess_electro_optical_properties(case)
        self.assertEqual(result["verdict"], PROPERTY_SET_INCOMPLETE)
        self.assertEqual(result["incomplete_ids"], ("cg-02",))

    def test_an_incomplete_record_does_not_pass_on_the_half_measured(self):
        case = _case()
        del case["articles"][0]["bulk_measurement"]
        result = assess_electro_optical_properties(case)
        self.assertNotEqual(result["verdict"], PROPERTIES_CHARACTERIZED)
        self.assertEqual(result["outside_band_ids"], ())

    def test_a_bulk_figure_outside_the_band_is_named(self):
        case = _case()
        case["articles"][1]["bulk_measurement"]["resistivity_ohm_m"] = 1.0e9
        result = assess_electro_optical_properties(case)
        self.assertEqual(result["verdict"], OUTSIDE_DECLARED_BAND)
        self.assertEqual(result["outside_band_ids"], ("cg-02",))

    def test_a_coating_above_its_ceiling_is_named(self):
        case = _case()
        case["articles"][0]["surface_measurement"][
            "resistivity_ohm_per_square"
        ] = 1.0e11
        result = assess_electro_optical_properties(case)
        self.assertEqual(result["verdict"], OUTSIDE_DECLARED_BAND)
        self.assertIn("cg-01", result["outside_band_ids"])

    def test_an_uncoated_article_is_not_held_to_the_coating_ceiling(self):
        case = _case()
        case["articles"][0]["coating_present"] = False
        case["articles"][0]["surface_measurement"][
            "resistivity_ohm_per_square"
        ] = 1.0e14
        result = assess_electro_optical_properties(case)
        self.assertEqual(result["verdict"], PROPERTIES_CHARACTERIZED)
        self.assertTrue(any("cg-01" in note for note in result["advisories"]))

    def test_a_coated_article_with_no_declared_ceiling_stops_the_assessment(self):
        result = assess_electro_optical_properties(
            _case(declared_band=_band(surface_max_ohm_per_square=None))
        )
        self.assertEqual(result["verdict"], REQUIREMENT_NOT_ESTABLISHED)

    def test_a_relaxed_policy_reports_a_ceilingless_coating_as_advisory(self):
        result = assess_electro_optical_properties(
            _case(declared_band=_band(surface_max_ohm_per_square=None)),
            _policy(require_surface_ceiling_when_coated=False),
        )
        self.assertEqual(result["verdict"], PROPERTIES_CHARACTERIZED)
        self.assertTrue(result["advisories"])

    def test_a_wide_spread_inside_the_band_raises_an_advisory_only(self):
        case = _case()
        case["articles"][1]["bulk_measurement"]["resistivity_ohm_m"] = 1.0e15
        result = assess_electro_optical_properties(case)
        self.assertEqual(result["verdict"], PROPERTIES_CHARACTERIZED)
        self.assertAlmostEqual(result["bulk_spread_decades"], 2.0, places=9)
        self.assertEqual(result["advisories"], [])

    def test_a_spread_beyond_the_expectation_is_advised(self):
        case = _case()
        case["articles"][1]["bulk_measurement"]["resistivity_ohm_m"] = 1.0e15
        result = assess_electro_optical_properties(
            case, _policy(max_article_spread_decades=1.0)
        )
        self.assertEqual(result["verdict"], PROPERTIES_CHARACTERIZED)
        self.assertTrue(any("bulk" in note for note in result["advisories"]))

    def test_a_duplicate_article_id_rejected(self):
        case = _case()
        case["articles"][1]["id"] = "cg-01"
        with self.assertRaises(ValueError):
            assess_electro_optical_properties(case)

    def test_an_empty_measured_population_rejected(self):
        with self.assertRaises(ValueError):
            assess_electro_optical_properties(_case(articles=[]))

    def test_a_missing_articles_record_rejected(self):
        case = _case()
        del case["articles"]
        with self.assertRaises(ValueError):
            assess_electro_optical_properties(case)

    def test_a_non_mapping_case_rejected(self):
        with self.assertRaises(ValueError):
            assess_electro_optical_properties(["declared_band"])

    def test_both_spread_figures_are_reported(self):
        result = assess_electro_optical_properties(_case())
        self.assertIsNotNone(result["bulk_spread_decades"])
        self.assertIsNotNone(result["surface_spread_decades"])


if __name__ == "__main__":
    unittest.main()
