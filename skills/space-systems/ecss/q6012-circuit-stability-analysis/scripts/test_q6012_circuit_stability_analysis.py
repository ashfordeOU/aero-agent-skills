#!/usr/bin/env python3
"""Contract test for the MMIC circuit stability demonstration (offline)."""

import cmath
import copy
import math
import unittest

from q6012_circuit_stability_analysis_logic import (
    ENVELOPE_CLEAR,
    LOAD_PLANE,
    MARGINALLY_STABLE,
    OSCILLATION_RISK,
    POTENTIALLY_UNSTABLE,
    SOURCE_PLANE,
    SPAN_INSUFFICIENT,
    STABLE_OVER_SPAN,
    UNCONDITIONALLY_STABLE,
    analyze_point,
    analyze_stability,
    as_reflection,
    determinant,
    mu_factor,
    required_analysis_span_hz,
    rollett_k,
    span_coverage,
    stability_category,
    stability_circle,
    termination_is_stable,
    validate_s_parameters,
)

# An in-band gain stage: modest reflections, low reverse transmission.
STABLE_S = {
    "s11": (0.3, -45.0),
    "s12": (0.1, 0.0),
    "s21": (2.0, 60.0),
    "s22": (0.2, -30.0),
}

# The same stage decades below its band: far more gain than the design
# needs, and the matching networks no longer control the terminations.
HOT_S = {
    "s11": (0.9, -30.0),
    "s12": (0.05, 10.0),
    "s21": (12.0, 150.0),
    "s22": (0.8, -20.0),
}

# A matrix built from real entries so the boundary lands exactly on one
# on every platform: s11*s22 = 0.25, s12*s21 = -0.75, so the determinant
# is exactly 1 and the Rollett factor is exactly 1.
MARGINAL_S = {"s11": 0.5, "s12": 0.1, "s21": -7.5, "s22": 0.5}

SAFE_LOAD_TERMINATIONS = [0j, (0.1, 20.0), (0.15, -40.0), (0.2, 90.0)]
SAFE_SOURCE_TERMINATIONS = [0j, (0.1, 20.0), (0.6, 0.0)]
HAZARDOUS_TERMINATION = (0.9, 180.0)

BAND_LOW_HZ = 2.0e9
BAND_HIGH_HZ = 4.0e9

FULL_SPAN_POINTS = [
    {"frequency_hz": 2.0e7, "s": STABLE_S},
    {"frequency_hz": 2.0e9, "s": STABLE_S},
    {"frequency_hz": 4.0e9, "s": STABLE_S},
    {"frequency_hz": 8.0e9, "s": STABLE_S},
]

GOOD_CASE = {
    "points": FULL_SPAN_POINTS,
    "band_low_hz": BAND_LOW_HZ,
    "band_high_hz": BAND_HIGH_HZ,
    "load_terminations": SAFE_LOAD_TERMINATIONS,
    "source_terminations": SAFE_SOURCE_TERMINATIONS,
}


def _case(base, **overrides):
    case = copy.deepcopy(base)
    case.update(overrides)
    return case


def _hot_low_end():
    points = copy.deepcopy(FULL_SPAN_POINTS)
    points[0] = {"frequency_hz": 2.0e7, "s": HOT_S}
    return points


class ReflectionInputTests(unittest.TestCase):
    def test_a_magnitude_angle_pair_becomes_a_complex_value(self):
        value = as_reflection((0.5, 90.0))
        self.assertAlmostEqual(value.real, 0.0, places=9)
        self.assertAlmostEqual(value.imag, 0.5, places=9)

    def test_a_complex_value_passes_through(self):
        self.assertEqual(as_reflection(0.3 + 0.4j), 0.3 + 0.4j)

    def test_a_real_number_becomes_a_real_reflection(self):
        self.assertEqual(as_reflection(-0.25), complex(-0.25, 0.0))

    def test_a_negative_magnitude_rejected(self):
        with self.assertRaises(ValueError):
            as_reflection((-0.5, 90.0))

    def test_a_three_element_pair_rejected(self):
        with self.assertRaises(ValueError):
            as_reflection((0.5, 90.0, 1.0))

    def test_a_scattering_matrix_missing_an_entry_rejected(self):
        bad = dict(STABLE_S)
        del bad["s12"]
        with self.assertRaises(ValueError):
            validate_s_parameters(bad)

    def test_a_zero_reverse_path_rejected(self):
        with self.assertRaises(ValueError):
            validate_s_parameters(dict(STABLE_S, s12=0j))

    def test_a_non_mapping_matrix_rejected(self):
        with self.assertRaises(ValueError):
            validate_s_parameters("s2p file")


class StabilityFactorTests(unittest.TestCase):
    def test_determinant_of_the_marginal_matrix_is_exactly_one(self):
        self.assertAlmostEqual(abs(determinant(MARGINAL_S)), 1.0, places=9)

    def test_rollett_factor_of_the_marginal_matrix_is_exactly_one(self):
        self.assertAlmostEqual(rollett_k(MARGINAL_S), 1.0, places=9)

    def test_the_in_band_stage_is_unconditionally_stable(self):
        self.assertEqual(stability_category(STABLE_S), UNCONDITIONALLY_STABLE)

    def test_the_low_frequency_stage_is_potentially_unstable(self):
        self.assertEqual(stability_category(HOT_S), POTENTIALLY_UNSTABLE)

    def test_a_matrix_on_the_boundary_is_reported_marginal(self):
        self.assertEqual(stability_category(MARGINAL_S), MARGINALLY_STABLE)

    def test_the_stable_stage_has_both_mu_factors_above_one(self):
        self.assertGreater(mu_factor(STABLE_S, LOAD_PLANE), 1.0)
        self.assertGreater(mu_factor(STABLE_S, SOURCE_PLANE), 1.0)

    def test_the_hot_stage_has_both_mu_factors_below_one(self):
        self.assertLess(mu_factor(HOT_S, LOAD_PLANE), 1.0)
        self.assertLess(mu_factor(HOT_S, SOURCE_PLANE), 1.0)

    def test_mu_is_the_distance_to_the_nearest_unstable_point(self):
        # For a circle that does not enclose the centre of the plane, the
        # geometric factor is exactly the gap between them.
        circle = stability_circle(STABLE_S, SOURCE_PLANE)
        self.assertFalse(circle["encircles_origin"])
        self.assertAlmostEqual(
            mu_factor(STABLE_S, SOURCE_PLANE),
            abs(circle["centre"]) - circle["radius"],
            places=9,
        )

    def test_an_unknown_plane_rejected(self):
        with self.assertRaises(ValueError):
            mu_factor(STABLE_S, "gate")


class StabilityCircleTests(unittest.TestCase):
    def test_the_hot_load_circle_encircles_the_centre_of_the_plane(self):
        circle = stability_circle(HOT_S, LOAD_PLANE)
        self.assertTrue(circle["encircles_origin"])
        self.assertTrue(circle["origin_is_stable"])

    def test_a_matched_termination_is_stable_on_the_hot_stage(self):
        self.assertTrue(termination_is_stable(0j, stability_circle(HOT_S, LOAD_PLANE)))

    def test_a_high_reflection_termination_is_unstable_on_the_hot_stage(self):
        self.assertFalse(
            termination_is_stable(
                HAZARDOUS_TERMINATION, stability_circle(HOT_S, LOAD_PLANE)
            )
        )

    def test_a_termination_on_the_circle_itself_does_not_pass(self):
        circle = stability_circle(HOT_S, LOAD_PLANE)
        # step outward from the centre along the direction that keeps the
        # landing point inside the passive region
        on_circle = circle["centre"] + cmath.rect(circle["radius"], math.pi)
        self.assertLess(abs(on_circle), 1.0)
        self.assertFalse(termination_is_stable(on_circle, circle))

    def test_an_active_termination_rejected(self):
        with self.assertRaises(ValueError):
            termination_is_stable((1.4, 0.0), stability_circle(HOT_S, LOAD_PLANE))

    def test_a_circle_without_a_complex_centre_rejected(self):
        with self.assertRaises(ValueError):
            termination_is_stable(0j, {"centre": 0.5, "radius": 1.0})

    def test_a_circle_with_a_negative_radius_rejected(self):
        with self.assertRaises(ValueError):
            termination_is_stable(0j, {"centre": 0j, "radius": -1.0})


class SpanTests(unittest.TestCase):
    def test_required_span_reaches_two_decades_below_the_band(self):
        required = required_analysis_span_hz(BAND_LOW_HZ, BAND_HIGH_HZ)
        self.assertAlmostEqual(required["required_low_hz"], 2.0e7, places=3)

    def test_required_span_reaches_twice_the_top_of_the_band(self):
        required = required_analysis_span_hz(BAND_LOW_HZ, BAND_HIGH_HZ)
        self.assertAlmostEqual(required["required_high_hz"], 8.0e9, places=3)

    def test_an_analysis_exactly_on_both_edges_covers_the_span(self):
        coverage = span_coverage(2.0e7, 8.0e9, BAND_LOW_HZ, BAND_HIGH_HZ)
        self.assertTrue(coverage["compliant"])
        self.assertEqual(coverage["findings"], [])

    def test_an_analysis_stopping_at_the_band_edge_misses_both_sides(self):
        coverage = span_coverage(BAND_LOW_HZ, BAND_HIGH_HZ, BAND_LOW_HZ, BAND_HIGH_HZ)
        self.assertFalse(coverage["compliant"])
        self.assertFalse(coverage["covers_low"])
        self.assertFalse(coverage["covers_high"])
        self.assertEqual(len(coverage["findings"]), 2)

    def test_a_deeper_low_reach_is_demanded_by_more_decades(self):
        required = required_analysis_span_hz(BAND_LOW_HZ, BAND_HIGH_HZ, decades_below=3.0)
        self.assertAlmostEqual(required["required_low_hz"], 2.0e6, places=3)

    def test_an_inverted_band_rejected(self):
        with self.assertRaises(ValueError):
            required_analysis_span_hz(BAND_HIGH_HZ, BAND_LOW_HZ)

    def test_a_factor_above_below_one_rejected(self):
        with self.assertRaises(ValueError):
            required_analysis_span_hz(BAND_LOW_HZ, BAND_HIGH_HZ, factor_above=0.5)

    def test_an_inverted_analysed_span_rejected(self):
        with self.assertRaises(ValueError):
            span_coverage(8.0e9, 2.0e7, BAND_LOW_HZ, BAND_HIGH_HZ)


class AnalyzePointTests(unittest.TestCase):
    def test_a_stable_point_reports_no_findings(self):
        result = analyze_point({"frequency_hz": 2.0e9, "s": STABLE_S})
        self.assertEqual(result["category"], UNCONDITIONALLY_STABLE)
        self.assertEqual(result["findings"], [])
        self.assertEqual(result["unstable_terminations"], [])

    def test_a_hot_point_with_safe_terminations_reports_no_unstable_ones(self):
        result = analyze_point(
            {"frequency_hz": 2.0e7, "s": HOT_S},
            SAFE_LOAD_TERMINATIONS,
            SAFE_SOURCE_TERMINATIONS,
        )
        self.assertEqual(result["category"], POTENTIALLY_UNSTABLE)
        self.assertEqual(result["unstable_terminations"], [])

    def test_a_hot_point_names_the_termination_that_would_oscillate(self):
        result = analyze_point(
            {"frequency_hz": 2.0e7, "s": HOT_S},
            SAFE_LOAD_TERMINATIONS + [HAZARDOUS_TERMINATION],
            [],
        )
        self.assertEqual(len(result["unstable_terminations"]), 1)
        self.assertEqual(result["unstable_terminations"][0]["plane"], LOAD_PLANE)

    def test_a_hot_point_with_no_declared_envelope_raises_a_finding(self):
        result = analyze_point({"frequency_hz": 2.0e7, "s": HOT_S})
        self.assertTrue(any("no termination envelope" in f for f in result["findings"]))

    def test_a_point_without_a_frequency_rejected(self):
        with self.assertRaises(ValueError):
            analyze_point({"s": STABLE_S})

    def test_a_point_with_a_negative_frequency_rejected(self):
        with self.assertRaises(ValueError):
            analyze_point({"frequency_hz": -2.0e9, "s": STABLE_S})

    def test_a_non_sequence_termination_list_rejected(self):
        with self.assertRaises(ValueError):
            analyze_point({"frequency_hz": 2.0e7, "s": HOT_S}, "matched", [])


class AnalyzeStabilityTests(unittest.TestCase):
    def test_an_unconditionally_stable_sweep_passes(self):
        result = analyze_stability(GOOD_CASE)
        self.assertEqual(result["verdict"], STABLE_OVER_SPAN)
        self.assertTrue(result["stable"])
        self.assertTrue(result["unconditional_everywhere"])
        self.assertEqual(result["findings"], [])

    def test_a_hot_low_end_with_a_clear_envelope_is_conditionally_stable(self):
        result = analyze_stability(_case(GOOD_CASE, points=_hot_low_end()))
        self.assertEqual(result["verdict"], ENVELOPE_CLEAR)
        self.assertTrue(result["stable"])
        self.assertFalse(result["unconditional_everywhere"])

    def test_a_hazardous_termination_turns_the_sweep_into_a_risk(self):
        result = analyze_stability(
            _case(
                GOOD_CASE,
                points=_hot_low_end(),
                load_terminations=SAFE_LOAD_TERMINATIONS + [HAZARDOUS_TERMINATION],
            )
        )
        self.assertEqual(result["verdict"], OSCILLATION_RISK)
        self.assertFalse(result["stable"])
        self.assertEqual(len(result["unstable_terminations"]), 1)

    def test_a_hot_low_end_with_no_envelope_is_a_risk(self):
        case = _case(GOOD_CASE, points=_hot_low_end())
        del case["load_terminations"]
        del case["source_terminations"]
        result = analyze_stability(case)
        self.assertEqual(result["verdict"], OSCILLATION_RISK)

    def test_a_sweep_that_stops_at_the_band_edges_cannot_conclude(self):
        points = [
            {"frequency_hz": BAND_LOW_HZ, "s": STABLE_S},
            {"frequency_hz": BAND_HIGH_HZ, "s": STABLE_S},
        ]
        result = analyze_stability(_case(GOOD_CASE, points=points))
        self.assertEqual(result["verdict"], SPAN_INSUFFICIENT)
        self.assertFalse(result["stable"])
        self.assertFalse(result["span"]["compliant"])

    def test_the_worst_frequency_is_the_one_with_the_lowest_mu(self):
        result = analyze_stability(_case(GOOD_CASE, points=_hot_low_end()))
        self.assertAlmostEqual(result["worst_frequency_hz"], 2.0e7, places=3)
        self.assertLess(result["worst_mu_load"], 1.0)

    def test_every_analysed_point_is_reported_back(self):
        result = analyze_stability(GOOD_CASE)
        self.assertEqual(len(result["points"]), len(FULL_SPAN_POINTS))

    def test_points_out_of_frequency_order_rejected(self):
        points = list(reversed(copy.deepcopy(FULL_SPAN_POINTS)))
        with self.assertRaises(ValueError):
            analyze_stability(_case(GOOD_CASE, points=points))

    def test_duplicate_frequencies_rejected(self):
        points = [
            {"frequency_hz": 2.0e7, "s": STABLE_S},
            {"frequency_hz": 2.0e7, "s": STABLE_S},
        ]
        with self.assertRaises(ValueError):
            analyze_stability(_case(GOOD_CASE, points=points))

    def test_an_empty_sweep_rejected(self):
        with self.assertRaises(ValueError):
            analyze_stability(_case(GOOD_CASE, points=[]))

    def test_a_non_mapping_case_rejected(self):
        with self.assertRaises(ValueError):
            analyze_stability("an s2p sweep")

    def test_a_case_without_a_band_rejected(self):
        case = _case(GOOD_CASE)
        del case["band_low_hz"]
        del case["band_high_hz"]
        with self.assertRaises(ValueError):
            analyze_stability(case)

    def test_widening_the_required_span_can_only_remove_coverage(self):
        deep = analyze_stability(_case(GOOD_CASE, decades_below=4.0))
        self.assertEqual(deep["verdict"], SPAN_INSUFFICIENT)
        self.assertTrue(analyze_stability(GOOD_CASE)["span"]["compliant"])


if __name__ == "__main__":
    unittest.main()
