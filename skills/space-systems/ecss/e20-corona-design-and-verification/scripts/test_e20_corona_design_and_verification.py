#!/usr/bin/env python3
"""Gate 3 contract test for e20-corona-design-and-verification.

Offline, deterministic, stdlib unittest only.
"""

import math
import unittest

from e20_corona_design_and_verification_logic import (
    COMPARISON_TOLERANCE,
    DETECTION_METHODS,
    SEEDING_SOURCES,
    VERIFICATION_ROUTES,
    applied_peak_voltage_v,
    assess_corona_design,
    categorize_verification_route,
    corona_margin_db,
    corona_onset_power_w,
    critical_band_covered,
    default_margin_allowance_db,
    evaluate_corona_item,
    reflection_coefficient,
    required_onset_voltage_v,
    resolve_margin_allowance_db,
    route_profile,
)


def sample_item(**overrides):
    item = {
        "id": "output-multiplexer",
        "applied_power_w": 60.0,
        "impedance_ohm": 50.0,
        "vswr": 1.3,
        "onset_voltage_v": 150.0,
        "route": "flight-standard-test",
        "detection_method": "forward-reverse-power-nulling",
        "seeding_source": "radioactive-source",
        "verification_band_pa": (0.5, 5000.0),
        "critical_band_pa": (10.0, 2000.0),
    }
    item.update(overrides)
    return item


class RouteCategoryTests(unittest.TestCase):
    def test_canonical_route_resolves_to_itself(self):
        self.assertEqual(
            categorize_verification_route("numerical-analysis"), "numerical-analysis"
        )

    def test_flight_model_alias_resolves(self):
        self.assertEqual(
            categorize_verification_route("flight-model-test"), "flight-standard-test"
        )

    def test_simulation_alias_resolves(self):
        self.assertEqual(categorize_verification_route("simulation"), "numerical-analysis")

    def test_heritage_alias_resolves(self):
        self.assertEqual(
            categorize_verification_route("heritage"), "heritage-similarity"
        )

    def test_route_lookup_is_case_insensitive(self):
        self.assertEqual(
            categorize_verification_route("  Flight-Standard-Test "),
            "flight-standard-test",
        )

    def test_unrecognized_route_raises(self):
        with self.assertRaises(ValueError):
            categorize_verification_route("expert-opinion")

    def test_non_string_route_raises(self):
        with self.assertRaises(ValueError):
            categorize_verification_route(None)


class AllowanceTests(unittest.TestCase):
    def test_flight_standard_route_earns_the_smallest_allowance(self):
        self.assertAlmostEqual(default_margin_allowance_db("flight-standard-test"), 3.0)

    def test_heritage_route_earns_the_largest_allowance(self):
        self.assertAlmostEqual(default_margin_allowance_db("heritage-similarity"), 8.0)

    def test_weaker_evidence_always_earns_more_headroom(self):
        ordered = sorted(
            VERIFICATION_ROUTES.items(),
            key=lambda pair: pair[1]["evidence_strength"],
            reverse=True,
        )
        allowances = [profile["default_allowance_db"] for _, profile in ordered]
        self.assertEqual(allowances, sorted(allowances))

    def test_route_profile_is_a_copy(self):
        profile = route_profile("numerical-analysis")
        profile["default_allowance_db"] = 0.0
        self.assertAlmostEqual(default_margin_allowance_db("numerical-analysis"), 6.0)

    def test_absent_agreement_falls_back_to_the_default(self):
        resolved = resolve_margin_allowance_db("representative-model-test")
        self.assertAlmostEqual(resolved["allowance_db"], 4.5)
        self.assertFalse(resolved["relaxed"])
        self.assertEqual(resolved["findings"], [])

    def test_agreed_allowance_above_the_default_stands(self):
        resolved = resolve_margin_allowance_db("flight-standard-test", 5.0)
        self.assertAlmostEqual(resolved["allowance_db"], 5.0)
        self.assertFalse(resolved["relaxed"])
        self.assertEqual(resolved["findings"], [])

    def test_agreed_allowance_equal_to_the_default_is_not_a_relaxation(self):
        resolved = resolve_margin_allowance_db("flight-standard-test", 3.0)
        self.assertFalse(resolved["relaxed"])
        self.assertEqual(resolved["findings"], [])

    def test_relaxed_allowance_without_agreement_is_a_finding(self):
        resolved = resolve_margin_allowance_db("flight-standard-test", 1.5)
        self.assertTrue(resolved["relaxed"])
        self.assertEqual(len(resolved["findings"]), 1)

    def test_relaxed_allowance_with_agreement_on_record_is_accepted(self):
        resolved = resolve_margin_allowance_db(
            "flight-standard-test", 1.5, "RFW-0042"
        )
        self.assertTrue(resolved["relaxed"])
        self.assertEqual(resolved["findings"], [])

    def test_negative_agreed_allowance_raises(self):
        with self.assertRaises(ValueError):
            resolve_margin_allowance_db("flight-standard-test", -0.5)

    def test_unknown_route_raises_in_resolution(self):
        with self.assertRaises(ValueError):
            resolve_margin_allowance_db("hand-waving", 3.0)


class VoltageAndPowerTests(unittest.TestCase):
    def test_matched_chain_has_no_reflection(self):
        self.assertAlmostEqual(reflection_coefficient(1.0), 0.0)

    def test_three_to_one_mismatch_reflects_half_the_amplitude(self):
        self.assertAlmostEqual(reflection_coefficient(3.0), 0.5)

    def test_mismatch_below_unity_raises(self):
        with self.assertRaises(ValueError):
            reflection_coefficient(0.5)

    def test_matched_peak_voltage_follows_the_power_relation(self):
        self.assertAlmostEqual(
            applied_peak_voltage_v(50.0, 50.0), math.sqrt(2.0 * 50.0 * 50.0)
        )

    def test_mismatch_raises_the_peak_voltage(self):
        matched = applied_peak_voltage_v(50.0, 50.0, 1.0)
        mismatched = applied_peak_voltage_v(50.0, 50.0, 3.0)
        self.assertAlmostEqual(mismatched, matched * 1.5)

    def test_non_positive_power_raises(self):
        with self.assertRaises(ValueError):
            applied_peak_voltage_v(0.0, 50.0)

    def test_non_positive_impedance_raises(self):
        with self.assertRaises(ValueError):
            applied_peak_voltage_v(50.0, 0.0)

    def test_onset_power_follows_the_square_of_the_onset_voltage(self):
        self.assertAlmostEqual(corona_onset_power_w(100.0, 50.0), 100.0)

    def test_onset_power_rejects_a_non_positive_voltage(self):
        with self.assertRaises(ValueError):
            corona_onset_power_w(0.0, 50.0)

    def test_onset_power_rejects_a_non_positive_impedance(self):
        with self.assertRaises(ValueError):
            corona_onset_power_w(100.0, -50.0)

    def test_doubling_the_onset_voltage_is_about_six_decibels(self):
        self.assertAlmostEqual(corona_margin_db(200.0, 100.0), 6.0206, places=4)

    def test_equal_voltages_give_zero_margin(self):
        self.assertAlmostEqual(corona_margin_db(100.0, 100.0), 0.0)

    def test_applied_above_onset_gives_a_negative_margin(self):
        self.assertLess(corona_margin_db(80.0, 100.0), 0.0)

    def test_margin_rejects_a_non_positive_onset(self):
        with self.assertRaises(ValueError):
            corona_margin_db(0.0, 100.0)

    def test_margin_rejects_a_non_positive_applied_voltage(self):
        with self.assertRaises(ValueError):
            corona_margin_db(100.0, 0.0)


class DesignTargetTests(unittest.TestCase):
    def test_zero_allowance_targets_the_applied_voltage_itself(self):
        applied = applied_peak_voltage_v(60.0, 50.0, 1.3)
        self.assertAlmostEqual(required_onset_voltage_v(60.0, 50.0, 1.3, 0.0), applied)

    def test_six_decibel_allowance_roughly_doubles_the_target(self):
        applied = applied_peak_voltage_v(60.0, 50.0, 1.0)
        target = required_onset_voltage_v(60.0, 50.0, 1.0, 6.0206)
        self.assertAlmostEqual(target / applied, 2.0, places=4)

    def test_target_round_trips_through_the_margin(self):
        target = required_onset_voltage_v(60.0, 50.0, 1.3, 4.0)
        applied = applied_peak_voltage_v(60.0, 50.0, 1.3)
        self.assertAlmostEqual(corona_margin_db(target, applied), 4.0, places=9)

    def test_negative_allowance_raises(self):
        with self.assertRaises(ValueError):
            required_onset_voltage_v(60.0, 50.0, 1.3, -1.0)


class CriticalBandCoverageTests(unittest.TestCase):
    def test_sweep_wider_than_the_critical_band_covers_it(self):
        coverage = critical_band_covered((0.5, 5000.0), (10.0, 2000.0))
        self.assertTrue(coverage["covered"])
        self.assertEqual(coverage["uncovered"], [])

    def test_identical_bands_are_covered(self):
        coverage = critical_band_covered((10.0, 2000.0), (10.0, 2000.0))
        self.assertTrue(coverage["covered"])

    def test_sweep_starting_too_high_leaves_the_low_side_unexercised(self):
        coverage = critical_band_covered((100.0, 5000.0), (10.0, 2000.0))
        self.assertFalse(coverage["covered"])
        self.assertEqual(len(coverage["uncovered"]), 1)
        self.assertAlmostEqual(coverage["uncovered"][0][0], 10.0)

    def test_sweep_stopping_too_low_leaves_the_high_side_unexercised(self):
        coverage = critical_band_covered((0.5, 500.0), (10.0, 2000.0))
        self.assertFalse(coverage["covered"])
        self.assertEqual(len(coverage["uncovered"]), 1)
        self.assertAlmostEqual(coverage["uncovered"][0][1], 2000.0)

    def test_narrow_sweep_leaves_both_sides_unexercised(self):
        coverage = critical_band_covered((100.0, 500.0), (10.0, 2000.0))
        self.assertFalse(coverage["covered"])
        self.assertEqual(len(coverage["uncovered"]), 2)

    def test_vacuum_only_sweep_never_reaches_the_critical_band(self):
        coverage = critical_band_covered((1.0e-6, 1.0e-4), (10.0, 2000.0))
        self.assertFalse(coverage["covered"])

    def test_malformed_band_raises(self):
        with self.assertRaises(ValueError):
            critical_band_covered((1.0,), (10.0, 2000.0))

    def test_inverted_band_raises(self):
        with self.assertRaises(ValueError):
            critical_band_covered((5000.0, 0.5), (10.0, 2000.0))

    def test_non_positive_band_edge_raises(self):
        with self.assertRaises(ValueError):
            critical_band_covered((0.0, 5000.0), (10.0, 2000.0))


class ItemEvaluationTests(unittest.TestCase):
    def test_well_designed_item_is_compliant(self):
        result = evaluate_corona_item(sample_item())
        self.assertTrue(result["compliant"])
        self.assertEqual(result["findings"], [])
        self.assertGreater(result["margin_db"], 3.0)

    def test_reported_onset_power_matches_the_onset_voltage(self):
        result = evaluate_corona_item(sample_item())
        self.assertAlmostEqual(result["onset_power_w"], 150.0 ** 2 / 100.0)

    def test_item_reports_the_onset_voltage_the_design_must_reach(self):
        result = evaluate_corona_item(sample_item())
        self.assertLess(result["required_onset_voltage_v"], result["onset_voltage_v"])

    def test_thin_margin_is_a_finding(self):
        result = evaluate_corona_item(sample_item(onset_voltage_v=100.0))
        self.assertFalse(result["compliant"])
        self.assertTrue(any("corona margin" in text for text in result["findings"]))

    def test_margin_exactly_at_the_allowance_is_compliant(self):
        probe = evaluate_corona_item(sample_item(agreed_allowance_db=0.0))
        item = sample_item(agreed_allowance_db=probe["margin_db"])
        result = evaluate_corona_item(item)
        self.assertTrue(result["compliant"])

    def test_margin_a_hair_under_the_allowance_is_a_finding(self):
        probe = evaluate_corona_item(sample_item(agreed_allowance_db=0.0))
        item = sample_item(agreed_allowance_db=probe["margin_db"] + 0.25)
        result = evaluate_corona_item(item)
        self.assertFalse(result["compliant"])

    def test_measurement_route_without_a_detection_method_is_a_finding(self):
        item = sample_item()
        del item["detection_method"]
        result = evaluate_corona_item(item)
        self.assertFalse(result["compliant"])

    def test_unrecognized_detection_method_is_a_finding(self):
        result = evaluate_corona_item(sample_item(detection_method="eyeball"))
        self.assertFalse(result["compliant"])

    def test_measurement_route_without_seeding_is_a_finding(self):
        item = sample_item()
        del item["seeding_source"]
        result = evaluate_corona_item(item)
        self.assertTrue(
            any("seed-electron" in text for text in result["findings"])
        )

    def test_unrecognized_seeding_source_is_a_finding(self):
        result = evaluate_corona_item(sample_item(seeding_source="ambient-cosmic-rays"))
        self.assertFalse(result["compliant"])

    def test_measurement_route_without_a_sweep_on_record_is_a_finding(self):
        item = sample_item()
        del item["verification_band_pa"]
        result = evaluate_corona_item(item)
        self.assertFalse(result["compliant"])
        self.assertIsNone(result["coverage"])

    def test_sweep_that_misses_the_critical_band_is_a_finding(self):
        result = evaluate_corona_item(sample_item(verification_band_pa=(0.5, 50.0)))
        self.assertFalse(result["compliant"])
        self.assertFalse(result["coverage"]["covered"])

    def test_analysis_route_needs_no_seeding_or_detection(self):
        result = evaluate_corona_item(
            {
                "id": "feed-horn",
                "applied_power_w": 60.0,
                "impedance_ohm": 50.0,
                "vswr": 1.3,
                "onset_voltage_v": 250.0,
                "route": "numerical-analysis",
            }
        )
        self.assertTrue(result["compliant"])
        self.assertAlmostEqual(result["allowance_db"], 6.0)

    def test_analysis_route_carries_the_larger_allowance(self):
        analysis = evaluate_corona_item(sample_item(route="numerical-analysis", onset_voltage_v=250.0))
        measured = evaluate_corona_item(sample_item(onset_voltage_v=250.0))
        self.assertGreater(analysis["allowance_db"], measured["allowance_db"])

    def test_relaxed_allowance_without_agreement_reaches_the_item_findings(self):
        result = evaluate_corona_item(sample_item(agreed_allowance_db=1.0))
        self.assertFalse(result["compliant"])
        self.assertTrue(any("relaxed" in text for text in result["findings"]))

    def test_relaxed_allowance_with_agreement_clears(self):
        result = evaluate_corona_item(
            sample_item(agreed_allowance_db=1.0, agreement_reference="WAIVER-17")
        )
        self.assertTrue(result["compliant"])

    def test_missing_required_key_raises(self):
        item = sample_item()
        del item["onset_voltage_v"]
        with self.assertRaises(ValueError):
            evaluate_corona_item(item)

    def test_unknown_route_on_an_item_raises(self):
        with self.assertRaises(ValueError):
            evaluate_corona_item(sample_item(route="gut-feel"))


class ChainAssessmentTests(unittest.TestCase):
    def test_clean_chain_is_compliant(self):
        report = assess_corona_design(
            [
                sample_item(),
                sample_item(id="feed-horn", onset_voltage_v=300.0),
            ]
        )
        self.assertTrue(report["compliant"])
        self.assertEqual(report["findings"], [])

    def test_driving_item_is_the_one_with_the_least_headroom(self):
        report = assess_corona_design(
            [
                sample_item(),
                sample_item(id="feed-horn", onset_voltage_v=300.0),
            ]
        )
        self.assertEqual(report["driving_item"], "output-multiplexer")

    def test_worst_margin_is_the_minimum_over_the_chain(self):
        report = assess_corona_design(
            [
                sample_item(),
                sample_item(id="feed-horn", onset_voltage_v=300.0),
            ]
        )
        margins = [evaluation["margin_db"] for evaluation in report["items"]]
        self.assertAlmostEqual(report["worst_margin_db"], min(margins))

    def test_weakest_evidence_strength_is_reported(self):
        report = assess_corona_design(
            [
                sample_item(),
                sample_item(
                    id="feed-horn", onset_voltage_v=300.0, route="heritage-similarity"
                ),
            ]
        )
        self.assertEqual(report["weakest_evidence_strength"], 0)

    def test_one_bad_item_fails_the_chain(self):
        report = assess_corona_design(
            [sample_item(), sample_item(id="feed-horn", onset_voltage_v=95.0)]
        )
        self.assertFalse(report["compliant"])
        self.assertTrue(report["findings"])

    def test_duplicate_item_identifier_raises(self):
        with self.assertRaises(ValueError):
            assess_corona_design([sample_item(), sample_item()])

    def test_empty_chain_raises(self):
        with self.assertRaises(ValueError):
            assess_corona_design([])

    def test_catalogues_are_populated_and_tolerance_is_representation_scale(self):
        self.assertIn("forward-reverse-power-nulling", DETECTION_METHODS)
        self.assertIn("ultraviolet-illumination", SEEDING_SOURCES)
        self.assertLess(COMPARISON_TOLERANCE, 1.0e-6)


if __name__ == "__main__":
    unittest.main()
