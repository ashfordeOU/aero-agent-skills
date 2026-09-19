#!/usr/bin/env python3
"""Contract test for the ECSS-Q-ST-60-05 clause 10.3.2 thermography leaf.

Offline, deterministic, stdlib unittest.
Run: python3 test_q6005_thermographic_screening_test.py
"""

import unittest

from q6005_thermographic_screening_test_logic import (
    ACCEPTANCE_INDEX,
    COLD_SITE_RATIO,
    CRITICAL_EXCURSION_RATIO,
    KELVIN_OFFSET,
    MAJOR_EXCURSION_RATIO,
    MANDATORY_SETUP_CONDITIONS,
    MAXIMUM_SURFACE_TEMPERATURE_C,
    MINIMUM_PIXELS_ACROSS_FEATURE,
    MINIMUM_STABILIZATION_SECONDS,
    MINOR_EXCURSION_RATIO,
    SETUP_CONDITIONS,
    SETUP_STATE_CREDIT,
    SITE_CATEGORIES,
    THERMOGRAPHIC_TOLERANCE,
    VERDICTS,
    assess_setup_condition,
    assess_thermographic_screen,
    categorize_site,
    corrected_surface_temperature_c,
    excursion_ratio,
    pixels_across_feature,
    resolution_is_adequate,
    setup_condition_weight,
    setup_index,
    setup_state_credit,
    temperature_rise_k,
)

REFERENCE_C = 22.0
PREDICTED_RISE_K = 20.0
OPTIONAL_CONDITION = "reflected-background-temperature-recorded"
MANDATORY_CONDITION = "detector-resolves-the-smallest-feature"


def every_condition(state="met-and-recorded", **overrides):
    """Every setup condition in one state, with named exceptions."""
    states = {name: state for name in SETUP_CONDITIONS}
    states.update(overrides)
    return states


def site(site_id="S-1", rise=PREDICTED_RISE_K, predicted=PREDICTED_RISE_K):
    """One imaged site, described by the rise it showed."""
    return {
        "site_id": site_id,
        "surface_temperature_c": REFERENCE_C + rise,
        "predicted_rise_k": predicted,
    }


def run(**overrides):
    """Grade one thermographic screening run."""
    case = {
        "unit_id": "HYB-TG-1",
        "reference_temperature_c": REFERENCE_C,
        "stabilization_seconds": MINIMUM_STABILIZATION_SECONDS * 2.0,
        "sites": [site("S-1"), site("S-2", rise=18.0)],
        "setup": every_condition(),
    }
    case.update(overrides)
    return assess_thermographic_screen(**case)


class ResolutionTests(unittest.TestCase):
    def test_a_feature_spans_its_size_over_the_pixel_pitch(self):
        self.assertAlmostEqual(pixels_across_feature(75.0, 25.0), 3.0, places=9)

    def test_a_finer_pitch_puts_more_pixels_on_the_same_feature(self):
        self.assertGreater(
            pixels_across_feature(75.0, 10.0), pixels_across_feature(75.0, 25.0)
        )

    def test_a_zero_pixel_pitch_is_rejected(self):
        with self.assertRaises(ValueError):
            pixels_across_feature(75.0, 0.0)

    def test_a_feature_exactly_on_the_pixel_floor_is_resolved(self):
        pitch = 25.0
        feature = MINIMUM_PIXELS_ACROSS_FEATURE * pitch
        self.assertAlmostEqual(
            pixels_across_feature(feature, pitch), MINIMUM_PIXELS_ACROSS_FEATURE, places=9
        )
        self.assertTrue(resolution_is_adequate(feature, pitch))

    def test_a_feature_under_the_pixel_floor_is_not_resolved(self):
        self.assertFalse(resolution_is_adequate(50.0, 25.0))


class RadiometryTests(unittest.TestCase):
    def test_a_perfect_emitter_needs_no_correction(self):
        self.assertAlmostEqual(
            corrected_surface_temperature_c(50.0, 1.0, 25.0), 50.0, places=6
        )

    def test_a_dull_surface_is_hotter_than_the_camera_indicated(self):
        corrected = corrected_surface_temperature_c(50.0, 0.9, 25.0)
        self.assertGreater(corrected, 50.5)

    def test_a_lower_emissivity_moves_the_correction_further(self):
        near_black = corrected_surface_temperature_c(50.0, 0.95, 25.0)
        dull = corrected_surface_temperature_c(50.0, 0.7, 25.0)
        self.assertGreater(dull, near_black)

    def test_a_zero_emissivity_is_rejected(self):
        with self.assertRaises(ValueError):
            corrected_surface_temperature_c(50.0, 0.0, 25.0)

    def test_an_emissivity_above_one_is_rejected(self):
        with self.assertRaises(ValueError):
            corrected_surface_temperature_c(50.0, 1.2, 25.0)

    def test_a_background_hotter_than_the_reading_is_an_input_error(self):
        with self.assertRaises(ValueError):
            corrected_surface_temperature_c(30.0, 0.2, 400.0)

    def test_a_reading_below_absolute_zero_is_rejected(self):
        with self.assertRaises(ValueError):
            corrected_surface_temperature_c(-300.0, 1.0, 25.0)

    def test_the_kelvin_offset_is_the_published_one(self):
        self.assertAlmostEqual(KELVIN_OFFSET, 273.15, places=9)


class SiteGradingTests(unittest.TestCase):
    def test_a_rise_is_measured_against_the_reference_not_against_zero(self):
        self.assertAlmostEqual(temperature_rise_k(42.0, REFERENCE_C), 20.0, places=9)

    def test_a_biased_site_below_the_reference_is_an_input_error(self):
        with self.assertRaises(ValueError):
            temperature_rise_k(REFERENCE_C - 5.0, REFERENCE_C)

    def test_a_zero_predicted_rise_is_rejected(self):
        with self.assertRaises(ValueError):
            excursion_ratio(10.0, 0.0)

    def test_a_site_on_its_prediction_is_nominal(self):
        self.assertEqual(categorize_site(site(), REFERENCE_C), "nominal-site")

    def test_every_returned_category_is_published(self):
        self.assertIn(categorize_site(site(), REFERENCE_C), SITE_CATEGORIES)

    def test_a_site_exactly_on_the_minor_ratio_is_a_minor_hot_spot(self):
        rise = PREDICTED_RISE_K * MINOR_EXCURSION_RATIO
        self.assertAlmostEqual(
            excursion_ratio(rise, PREDICTED_RISE_K), MINOR_EXCURSION_RATIO, places=9
        )
        self.assertEqual(categorize_site(site(rise=rise), REFERENCE_C), "minor-hot-spot")

    def test_a_site_on_the_major_ratio_is_a_major_hot_spot(self):
        rise = PREDICTED_RISE_K * MAJOR_EXCURSION_RATIO
        self.assertEqual(categorize_site(site(rise=rise), REFERENCE_C), "major-hot-spot")

    def test_a_site_on_the_critical_ratio_is_a_critical_hot_spot(self):
        rise = PREDICTED_RISE_K * CRITICAL_EXCURSION_RATIO
        self.assertEqual(categorize_site(site(rise=rise), REFERENCE_C), "critical-hot-spot")

    def test_the_absolute_surface_limit_outranks_a_healthy_prediction(self):
        rise = MAXIMUM_SURFACE_TEMPERATURE_C - REFERENCE_C
        graded = categorize_site(site(rise=rise, predicted=rise), REFERENCE_C)
        self.assertEqual(graded, "critical-hot-spot")

    def test_a_site_far_colder_than_predicted_is_an_anomaly_not_a_pass(self):
        rise = PREDICTED_RISE_K * COLD_SITE_RATIO * 0.5
        self.assertEqual(categorize_site(site(rise=rise), REFERENCE_C), "cold-site-anomaly")

    def test_a_site_without_an_identifier_is_rejected(self):
        bad = site()
        del bad["site_id"]
        with self.assertRaises(ValueError):
            categorize_site(bad, REFERENCE_C)


class SetupGradingTests(unittest.TestCase):
    def test_every_condition_carries_a_positive_weight(self):
        for name in SETUP_CONDITIONS:
            self.assertGreater(setup_condition_weight(name), 0.0)

    def test_every_mandatory_condition_is_a_published_condition(self):
        for name in MANDATORY_SETUP_CONDITIONS:
            self.assertIn(name, SETUP_CONDITIONS)

    def test_an_unknown_setup_condition_is_rejected(self):
        with self.assertRaises(ValueError):
            setup_condition_weight("camera-was-warmed-up")

    def test_an_unknown_setup_state_is_rejected(self):
        with self.assertRaises(ValueError):
            setup_state_credit("probably-fine")

    def test_a_met_condition_earns_its_full_weight(self):
        record = assess_setup_condition(OPTIONAL_CONDITION, "met-and-recorded")
        self.assertAlmostEqual(
            record["weighted_credit"], SETUP_CONDITIONS[OPTIONAL_CONDITION], places=9
        )
        self.assertEqual(record["findings"], [])

    def test_an_unmet_mandatory_condition_is_marked_missing(self):
        record = assess_setup_condition(MANDATORY_CONDITION, "not-met")
        self.assertTrue(record["mandatory_missing"])
        self.assertIn("mandatory-setup-condition-not-met", record["findings"])

    def test_a_full_setup_reaches_a_full_index(self):
        records = [assess_setup_condition(n, "met-and-recorded") for n in SETUP_CONDITIONS]
        self.assertAlmostEqual(setup_index(records), 1.0, places=9)

    def test_an_empty_setup_is_rejected(self):
        with self.assertRaises(ValueError):
            setup_index([])


class WholeScreenTests(unittest.TestCase):
    def test_every_verdict_returned_is_one_of_the_published_verdicts(self):
        self.assertIn(run()["verdict"], VERDICTS)

    def test_a_clean_run_on_a_well_behaved_unit_passes(self):
        result = run()
        self.assertEqual(result["verdict"], "thermographic-screen-passed")
        self.assertTrue(result["unit_passed"])
        self.assertEqual(result["findings"], [])
        self.assertAlmostEqual(result["setup_index"], 1.0, places=9)

    def test_a_detector_that_cannot_resolve_the_feature_invalidates_the_screen(self):
        result = run(setup=every_condition(**{MANDATORY_CONDITION: "not-met"}))
        self.assertEqual(result["verdict"], "thermographic-screen-invalid")
        self.assertFalse(result["unit_passed"])

    def test_a_short_stabilization_dwell_invalidates_the_screen(self):
        result = run(stabilization_seconds=MINIMUM_STABILIZATION_SECONDS / 4.0)
        self.assertFalse(result["stabilization_met"])
        self.assertEqual(result["verdict"], "thermographic-screen-invalid")

    def test_a_declared_dwell_cannot_override_a_short_measured_one(self):
        result = run(
            stabilization_seconds=1.0,
            setup=every_condition(
                **{"thermal-stabilization-dwell-completed": "met-and-recorded"}
            ),
        )
        self.assertEqual(result["verdict"], "thermographic-screen-invalid")

    def test_a_dwell_exactly_on_the_floor_is_met(self):
        result = run(stabilization_seconds=MINIMUM_STABILIZATION_SECONDS)
        self.assertTrue(result["stabilization_met"])
        self.assertEqual(result["verdict"], "thermographic-screen-passed")

    def test_a_thin_setup_record_falls_under_the_acceptance_index(self):
        result = run(
            setup=every_condition(
                **{
                    OPTIONAL_CONDITION: "not-met",
                    "reference-ambient-temperature-recorded": "not-met",
                }
            )
        )
        self.assertLess(result["setup_index"], ACCEPTANCE_INDEX)
        self.assertEqual(result["verdict"], "thermographic-screen-invalid")

    def test_an_unrecorded_optional_condition_leaves_the_screen_open(self):
        result = run(setup=every_condition(**{OPTIONAL_CONDITION: "met-not-recorded"}))
        self.assertEqual(
            result["verdict"], "thermographic-screen-passed-with-open-actions"
        )
        self.assertTrue(result["unit_passed"])

    def test_a_major_hot_spot_rejects_the_unit(self):
        result = run(sites=[site(rise=PREDICTED_RISE_K * MAJOR_EXCURSION_RATIO)])
        self.assertEqual(result["verdict"], "unit-rejected-on-thermographic-screen")

    def test_a_minor_hot_spot_leaves_the_unit_passed_with_open_actions(self):
        result = run(sites=[site(rise=PREDICTED_RISE_K * MINOR_EXCURSION_RATIO)])
        self.assertEqual(
            result["verdict"], "thermographic-screen-passed-with-open-actions"
        )

    def test_a_cold_site_rejects_the_unit_as_readily_as_a_hot_one(self):
        result = run(sites=[site(rise=1.0)])
        self.assertEqual(result["verdict"], "unit-rejected-on-thermographic-screen")

    def test_an_invalid_setup_outranks_a_rejecting_site(self):
        result = run(
            sites=[site(rise=PREDICTED_RISE_K * CRITICAL_EXCURSION_RATIO)],
            setup=every_condition(**{MANDATORY_CONDITION: "not-met"}),
        )
        self.assertEqual(result["verdict"], "thermographic-screen-invalid")

    def test_a_repeated_site_identifier_is_rejected(self):
        with self.assertRaises(ValueError):
            run(sites=[site("S-1"), site("S-1", rise=19.0)])

    def test_a_screen_with_no_imaged_site_is_rejected(self):
        with self.assertRaises(ValueError):
            run(sites=[])

    def test_an_unknown_setup_condition_in_the_input_is_rejected(self):
        with self.assertRaises(ValueError):
            run(setup=every_condition(**{"lens-was-clean": "met-and-recorded"}))

    def test_a_blank_unit_identifier_is_rejected(self):
        with self.assertRaises(ValueError):
            run(unit_id="  ")

    def test_a_negative_stabilization_time_is_rejected(self):
        with self.assertRaises(ValueError):
            run(stabilization_seconds=-1.0)


class ConstantsTests(unittest.TestCase):
    def test_the_tolerance_is_small_enough_to_separate_the_bounds(self):
        self.assertLess(THERMOGRAPHIC_TOLERANCE, 1e-6)

    def test_the_excursion_ratios_rank_in_the_order_they_are_read(self):
        self.assertLess(COLD_SITE_RATIO, MINOR_EXCURSION_RATIO)
        self.assertLess(MINOR_EXCURSION_RATIO, MAJOR_EXCURSION_RATIO)
        self.assertLess(MAJOR_EXCURSION_RATIO, CRITICAL_EXCURSION_RATIO)

    def test_the_setup_credits_span_the_published_scale(self):
        self.assertAlmostEqual(max(SETUP_STATE_CREDIT.values()), 1.0, places=9)
        self.assertAlmostEqual(min(SETUP_STATE_CREDIT.values()), 0.0, places=9)

    def test_the_acceptance_index_sits_under_a_full_setup(self):
        self.assertLess(ACCEPTANCE_INDEX, 1.0)


if __name__ == "__main__":
    unittest.main()
