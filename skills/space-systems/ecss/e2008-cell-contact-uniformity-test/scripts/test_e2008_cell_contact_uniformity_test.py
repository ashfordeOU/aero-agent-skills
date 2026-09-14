#!/usr/bin/env python3
"""Contract tests for the clause 7.5.9 contact uniformity logic (offline)."""

import copy
import unittest

from e2008_cell_contact_uniformity_test_logic import (
    CONTACT_FEATURES,
    DEFAULT_UNIFORMITY_POLICY,
    MODE_GRADIENT,
    MODE_OUTLIER,
    MODE_SCATTER,
    MODE_WITHIN_LIMITS,
    NON_UNIFORMITY_MODES,
    NON_UNIFORM_VERDICT,
    SAMPLE_INADEQUATE,
    UNIFORM_VERDICT,
    assess_bare_cell_contact_uniformity,
    assess_feature_uniformity,
    dominant_non_uniformity_mode,
    map_span_mm,
    normalise_thickness_map,
    point_deviations,
    sample_adequacy,
    thickness_gradient,
    thickness_statistics,
    validate_uniformity_policy,
    worst_point_deviation,
)

FEATURE_LENGTH_MM = 52.0

EVEN_MAP = [
    (0.0, 8.00),
    (10.0, 8.05),
    (20.0, 7.96),
    (30.0, 8.02),
    (40.0, 7.98),
    (50.0, 8.01),
]

RAMPED_MAP = [
    (0.0, 7.0),
    (10.0, 7.4),
    (20.0, 7.8),
    (30.0, 8.2),
    (40.0, 8.6),
    (50.0, 9.0),
]

ONE_THIN_SPOT_MAP = [
    (0.0, 8.0),
    (10.0, 8.0),
    (20.0, 8.0),
    (30.0, 6.0),
    (40.0, 8.0),
    (50.0, 8.0),
]

SCATTERED_MAP = [
    (0.0, 9.2),
    (10.0, 6.8),
    (20.0, 8.0),
    (30.0, 8.0),
    (40.0, 6.8),
    (50.0, 9.2),
]

CLUSTERED_MAP = [
    (0.0, 8.0),
    (2.0, 8.02),
    (4.0, 7.99),
    (6.0, 8.01),
    (8.0, 8.0),
    (10.0, 8.03),
]


def _feature(**overrides):
    case = {
        "feature": "front-bus-bar",
        "feature_length_mm": FEATURE_LENGTH_MM,
        "readings": copy.deepcopy(EVEN_MAP),
    }
    case.update(overrides)
    return case


def _cell(*features):
    return {
        "cell_identifier": "coupon-14",
        "features": list(features) if features else [_feature()],
    }


class PolicyTests(unittest.TestCase):
    def test_default_policy_normalises(self):
        limits = validate_uniformity_policy()
        self.assertEqual(
            limits["minimum_points_per_feature"],
            DEFAULT_UNIFORMITY_POLICY["minimum_points_per_feature"],
        )
        self.assertAlmostEqual(limits["minimum_uniformity_ratio"], 0.80, places=9)

    def test_an_unknown_policy_key_is_refused(self):
        with self.assertRaises(ValueError):
            validate_uniformity_policy({"maximum_thickness_um": 9.0})

    def test_a_fraction_limit_above_one_is_refused(self):
        with self.assertRaises(ValueError):
            validate_uniformity_policy({"minimum_uniformity_ratio": 1.4})

    def test_a_single_point_minimum_is_refused(self):
        with self.assertRaises(ValueError):
            validate_uniformity_policy({"minimum_points_per_feature": 1})

    def test_a_non_mapping_policy_is_refused(self):
        with self.assertRaises(ValueError):
            validate_uniformity_policy("default")


class MapValidationTests(unittest.TestCase):
    def test_readings_are_ordered_along_the_feature(self):
        mapped = normalise_thickness_map([(30.0, 8.0), (10.0, 8.1), (20.0, 7.9)])
        self.assertEqual([position for position, _ in mapped], [10.0, 20.0, 30.0])

    def test_mapping_form_readings_are_accepted(self):
        mapped = normalise_thickness_map(
            [
                {"position_mm": 0.0, "thickness_um": 8.0},
                {"position_mm": 5.0, "thickness_um": 8.1},
            ]
        )
        self.assertEqual(len(mapped), 2)
        self.assertAlmostEqual(mapped[1][1], 8.1, places=9)

    def test_two_readings_at_one_position_are_refused(self):
        with self.assertRaises(ValueError):
            normalise_thickness_map([(4.0, 8.0), (4.0, 8.2), (9.0, 8.1)])

    def test_a_zero_thickness_reading_is_refused(self):
        with self.assertRaises(ValueError):
            normalise_thickness_map([(0.0, 8.0), (10.0, 0.0)])

    def test_a_negative_position_is_refused(self):
        with self.assertRaises(ValueError):
            normalise_thickness_map([(-1.0, 8.0), (10.0, 8.0)])

    def test_a_single_reading_is_not_a_map(self):
        with self.assertRaises(ValueError):
            normalise_thickness_map([(0.0, 8.0)])

    def test_map_span_is_first_to_last_position(self):
        self.assertAlmostEqual(map_span_mm(EVEN_MAP), 50.0, places=9)


class SampleAdequacyTests(unittest.TestCase):
    def test_a_wide_dense_map_speaks_for_the_feature(self):
        adequacy = sample_adequacy(EVEN_MAP, FEATURE_LENGTH_MM)
        self.assertTrue(adequacy["adequate"])
        self.assertEqual(adequacy["findings"], [])

    def test_a_map_clustered_at_one_end_is_inadequate(self):
        adequacy = sample_adequacy(CLUSTERED_MAP, FEATURE_LENGTH_MM)
        self.assertFalse(adequacy["adequate"])
        self.assertTrue(
            any("of the feature" in finding for finding in adequacy["findings"])
        )

    def test_too_few_readings_is_inadequate(self):
        adequacy = sample_adequacy(
            [(0.0, 8.0), (25.0, 8.0), (50.0, 8.0)], FEATURE_LENGTH_MM
        )
        self.assertFalse(adequacy["adequate"])

    def test_a_span_exactly_on_the_policy_floor_is_accepted(self):
        readings = [(0.0, 8.0), (10.0, 8.0), (20.0, 8.0), (30.0, 8.0), (40.0, 8.0)]
        adequacy = sample_adequacy(readings, 50.0, {"minimum_position_span_fraction": 0.8})
        self.assertAlmostEqual(adequacy["span_fraction"], 0.8, places=9)
        self.assertTrue(adequacy["adequate"])

    def test_a_reading_beyond_the_declared_feature_is_refused(self):
        with self.assertRaises(ValueError):
            sample_adequacy(EVEN_MAP, 20.0)

    def test_a_zero_feature_length_is_refused(self):
        with self.assertRaises(ValueError):
            sample_adequacy(EVEN_MAP, 0.0)


class StatisticsTests(unittest.TestCase):
    def test_an_even_map_has_a_high_uniformity_ratio(self):
        statistics = thickness_statistics(EVEN_MAP)
        self.assertAlmostEqual(statistics["uniformity_ratio"], 7.96 / 8.05, places=9)
        self.assertEqual(statistics["point_count"], 6)

    def test_the_range_is_the_thickest_less_the_thinnest(self):
        statistics = thickness_statistics(RAMPED_MAP)
        self.assertAlmostEqual(statistics["range_um"], 2.0, places=9)

    def test_a_perfectly_flat_map_has_no_spread(self):
        statistics = thickness_statistics([(0.0, 8.0), (10.0, 8.0), (20.0, 8.0)])
        self.assertAlmostEqual(statistics["coefficient_of_variation"], 0.0, places=9)
        self.assertAlmostEqual(statistics["uniformity_ratio"], 1.0, places=9)

    def test_point_deviations_are_signed_and_sum_to_nothing(self):
        deviations = [value for _, value in point_deviations(RAMPED_MAP)]
        self.assertAlmostEqual(sum(deviations), 0.0, places=9)
        self.assertAlmostEqual(min(deviations), -0.125, places=9)

    def test_worst_point_deviation_is_the_largest_magnitude(self):
        self.assertAlmostEqual(worst_point_deviation(RAMPED_MAP), 0.125, places=9)


class GradientTests(unittest.TestCase):
    def test_a_ramped_map_fits_a_clear_slope(self):
        gradient = thickness_gradient(RAMPED_MAP)
        self.assertAlmostEqual(gradient["slope_um_per_mm"], 0.04, places=9)
        self.assertAlmostEqual(gradient["end_to_end_drift_um"], 2.0, places=9)
        self.assertAlmostEqual(gradient["drift_fraction"], 0.25, places=9)

    def test_a_symmetric_scatter_fits_no_slope(self):
        gradient = thickness_gradient(SCATTERED_MAP)
        self.assertAlmostEqual(gradient["slope_um_per_mm"], 0.0, places=9)
        self.assertAlmostEqual(gradient["drift_fraction"], 0.0, places=9)

    def test_a_ramped_map_leaves_no_residual_scatter(self):
        gradient = thickness_gradient(RAMPED_MAP)
        self.assertAlmostEqual(gradient["residual_stdev_um"], 0.0, places=9)

    def test_the_trimmed_scale_drops_the_largest_residual(self):
        gradient = thickness_gradient(ONE_THIN_SPOT_MAP)
        trimmed = gradient["trimmed_residual_stdev_um"]
        plain = gradient["residual_stdev_um"]
        worst = max(abs(residual) for residual in gradient["residuals_um"])
        self.assertLess(trimmed, 0.5 * plain)
        self.assertGreater(worst / trimmed, 4.0)
        self.assertLess(worst / plain, 2.0)

    def test_a_two_point_map_has_no_residual_scale(self):
        gradient = thickness_gradient([(0.0, 8.0), (10.0, 9.0)])
        self.assertAlmostEqual(gradient["residual_stdev_um"], 0.0, places=9)
        self.assertAlmostEqual(gradient["trimmed_residual_stdev_um"], 0.0, places=9)


class ModeTests(unittest.TestCase):
    def test_an_even_map_names_no_mode(self):
        self.assertEqual(dominant_non_uniformity_mode(EVEN_MAP), MODE_WITHIN_LIMITS)

    def test_a_drifting_map_is_named_a_gradient(self):
        self.assertEqual(dominant_non_uniformity_mode(RAMPED_MAP), MODE_GRADIENT)

    def test_one_thin_spot_is_named_an_outlier(self):
        self.assertEqual(dominant_non_uniformity_mode(ONE_THIN_SPOT_MAP), MODE_OUTLIER)

    def test_symmetric_spread_is_named_scatter(self):
        self.assertEqual(dominant_non_uniformity_mode(SCATTERED_MAP), MODE_SCATTER)

    def test_every_mode_is_a_declared_mode(self):
        for readings in (EVEN_MAP, RAMPED_MAP, ONE_THIN_SPOT_MAP, SCATTERED_MAP):
            self.assertIn(dominant_non_uniformity_mode(readings), NON_UNIFORMITY_MODES)


class FeatureAssessmentTests(unittest.TestCase):
    def test_an_even_feature_qualifies(self):
        result = assess_feature_uniformity(_feature())
        self.assertEqual(result["verdict"], UNIFORM_VERDICT)
        self.assertTrue(result["uniform"])
        self.assertEqual(result["findings"], [])

    def test_a_drifting_feature_fails_and_names_the_drift(self):
        result = assess_feature_uniformity(_feature(readings=RAMPED_MAP))
        self.assertEqual(result["verdict"], NON_UNIFORM_VERDICT)
        self.assertEqual(result["non_uniformity_mode"], MODE_GRADIENT)
        self.assertTrue(any("drifts" in finding for finding in result["findings"]))

    def test_an_inadequate_map_is_not_reported_as_a_pass_or_a_fail(self):
        result = assess_feature_uniformity(_feature(readings=CLUSTERED_MAP))
        self.assertEqual(result["verdict"], SAMPLE_INADEQUATE)
        self.assertFalse(result["uniform"])

    def test_an_unknown_contact_feature_is_refused(self):
        with self.assertRaises(ValueError):
            assess_feature_uniformity(_feature(feature="edge-seal"))

    def test_a_non_mapping_feature_case_is_refused(self):
        with self.assertRaises(ValueError):
            assess_feature_uniformity("front-bus-bar")

    def test_every_declared_feature_name_is_accepted(self):
        for feature in CONTACT_FEATURES:
            result = assess_feature_uniformity(_feature(feature=feature))
            self.assertEqual(result["feature"], feature)


class CellAssessmentTests(unittest.TestCase):
    def test_a_cell_with_even_features_qualifies(self):
        case = _cell(
            _feature(feature="front-bus-bar"),
            _feature(feature="rear-contact"),
        )
        result = assess_bare_cell_contact_uniformity(case)
        self.assertEqual(result["verdict"], UNIFORM_VERDICT)
        self.assertTrue(result["uniform"])
        self.assertEqual(result["modes_observed"], ())

    def test_one_bad_feature_carries_the_cell_verdict(self):
        case = _cell(
            _feature(feature="front-bus-bar"),
            _feature(feature="front-grid-finger", readings=RAMPED_MAP),
        )
        result = assess_bare_cell_contact_uniformity(case)
        self.assertEqual(result["verdict"], NON_UNIFORM_VERDICT)
        self.assertEqual(result["features_non_uniform"], ("front-grid-finger",))
        self.assertIn(MODE_GRADIENT, result["modes_observed"])

    def test_an_inadequate_map_outranks_a_non_uniform_one(self):
        case = _cell(
            _feature(feature="front-bus-bar", readings=CLUSTERED_MAP),
            _feature(feature="front-grid-finger", readings=RAMPED_MAP),
        )
        result = assess_bare_cell_contact_uniformity(case)
        self.assertEqual(result["verdict"], SAMPLE_INADEQUATE)
        self.assertEqual(result["features_inadequate"], ("front-bus-bar",))

    def test_the_same_feature_may_not_be_mapped_twice(self):
        case = _cell(_feature(), _feature())
        with self.assertRaises(ValueError):
            assess_bare_cell_contact_uniformity(case)

    def test_a_cell_with_no_features_is_refused(self):
        with self.assertRaises(ValueError):
            assess_bare_cell_contact_uniformity({"features": []})

    def test_a_non_mapping_cell_case_is_refused(self):
        with self.assertRaises(ValueError):
            assess_bare_cell_contact_uniformity(["front-bus-bar"])

    def test_the_worst_spread_across_features_is_reported(self):
        case = _cell(
            _feature(feature="front-bus-bar"),
            _feature(feature="rear-contact", readings=SCATTERED_MAP),
        )
        result = assess_bare_cell_contact_uniformity(case)
        self.assertAlmostEqual(
            result["worst_coefficient_of_variation"],
            thickness_statistics(SCATTERED_MAP)["coefficient_of_variation"],
            places=9,
        )



class WorkflowOrderTests(unittest.TestCase):
    """The clause runs as ordered steps and the adequacy gate is the first.

    A map that cannot speak for the feature must stop the workflow before
    any spread figure is reported as a result, however bad that spread
    looks, because the spread belongs to the part of the contact the map
    happened to cover.
    """

    CLUSTERED_RAMP = [
        (0.0, 7.0),
        (2.0, 7.4),
        (4.0, 7.8),
        (6.0, 8.2),
        (8.0, 8.6),
        (10.0, 9.0),
    ]

    def test_the_adequacy_gate_stops_a_map_that_also_looks_non_uniform(self):
        result = assess_feature_uniformity(_feature(readings=self.CLUSTERED_RAMP))
        self.assertEqual(result["verdict"], SAMPLE_INADEQUATE)
        self.assertEqual(result["non_uniformity_mode"], MODE_GRADIENT)
        self.assertTrue(
            any("of the feature" in finding for finding in result["findings"])
        )

    def test_an_absent_measurement_outranks_a_measured_failure(self):
        case = _cell(
            _feature(feature="front-bus-bar", readings=RAMPED_MAP),
            _feature(feature="front-grid-finger", readings=self.CLUSTERED_RAMP),
            _feature(feature="rear-contact"),
        )
        result = assess_bare_cell_contact_uniformity(case)
        self.assertEqual(result["verdict"], SAMPLE_INADEQUATE)
        self.assertEqual(result["features_inadequate"], ("front-grid-finger",))
        self.assertEqual(result["features_non_uniform"], ("front-bus-bar",))

    def test_every_step_of_the_workflow_reports_its_own_section(self):
        result = assess_feature_uniformity(_feature())
        for section in (
            "sample_adequacy",
            "statistics",
            "gradient",
            "non_uniformity_mode",
            "verdict",
        ):
            self.assertIn(section, result)


if __name__ == "__main__":
    unittest.main()
