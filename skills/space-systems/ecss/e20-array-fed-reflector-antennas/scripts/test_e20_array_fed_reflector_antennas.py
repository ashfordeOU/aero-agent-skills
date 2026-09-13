#!/usr/bin/env python3
"""Contract test for the clause 7.2.2.2.4 array-fed reflector leaf.

stdlib unittest, offline, deterministic. Run: python3 test_e20_array_fed_reflector_antennas.py
"""

import math
import unittest

from e20_array_fed_reflector_antennas_logic import (
    _ge,
    assess_array_fed_reflector,
    beam_deviation_factor,
    beam_gain_budget,
    beam_squint_deg,
    beamwidth_deg,
    categorize_feed_arrangement,
    feed_cluster_efficiency,
    illumination_efficiency,
    provision_coverage,
    reflector_gain_dbi,
    scan_loss_db,
    spillover_efficiency,
    surface_efficiency,
    total_aperture_efficiency,
)


def both_families():
    return [
        {"id": "REF-01", "family": "reflector", "verified": True},
        {"id": "ARR-01", "family": "radiating-array", "verified": True},
    ]


def reflector_block():
    return {
        "diameter_wavelengths": 100.0,
        "f_over_d": 0.35,
        "surface_rms_wavelengths": 0.005,
        "edge_taper_db": 12.0,
    }


def feed_block():
    return {
        "element_amplitudes": [1.0, 1.0, 1.0, 1.0],
        "feeds_per_beam": 4,
        "network_loss_db": 0.5,
    }


def base_config():
    return {
        "reflector": reflector_block(),
        "feed_array": feed_block(),
        "beams": [
            {"id": "B1", "lateral_offset_wavelengths": 0.0, "required_gain_dbi": 47.0},
            {"id": "B2", "lateral_offset_wavelengths": 0.3, "required_gain_dbi": 47.0},
        ],
        "provisions": both_families(),
    }


class ProvisionCoverageTests(unittest.TestCase):
    def test_both_families_declared_and_verified(self):
        result = provision_coverage(both_families())
        self.assertTrue(result["complete"])
        self.assertEqual(result["missing_families"], [])

    def test_reflector_only_dossier_is_incomplete(self):
        result = provision_coverage([{"id": "REF-01", "family": "reflector", "verified": True}])
        self.assertFalse(result["complete"])
        self.assertEqual(result["missing_families"], ["radiating-array"])

    def test_array_only_dossier_is_incomplete(self):
        result = provision_coverage(
            [{"id": "ARR-01", "family": "radiating-array", "verified": True}]
        )
        self.assertEqual(result["missing_families"], ["reflector"])

    def test_declared_but_unverified_provision_is_listed(self):
        entries = both_families()
        entries[1]["verified"] = False
        result = provision_coverage(entries)
        self.assertEqual(result["unverified"], ["ARR-01"])
        self.assertFalse(result["complete"])

    def test_empty_provision_list_rejected(self):
        with self.assertRaises(ValueError):
            provision_coverage([])

    def test_non_list_provisions_rejected(self):
        with self.assertRaises(ValueError):
            provision_coverage("REF-01")

    def test_duplicate_provision_id_rejected(self):
        entries = both_families()
        entries[1]["id"] = "REF-01"
        with self.assertRaises(ValueError):
            provision_coverage(entries)

    def test_unknown_provision_family_rejected(self):
        with self.assertRaises(ValueError):
            provision_coverage([{"id": "X", "family": "structure", "verified": True}])

    def test_non_boolean_verified_flag_rejected(self):
        with self.assertRaises(ValueError):
            provision_coverage([{"id": "X", "family": "reflector", "verified": "yes"}])

    def test_provision_without_id_rejected(self):
        with self.assertRaises(ValueError):
            provision_coverage([{"family": "reflector", "verified": True}])

    def test_non_mapping_provision_rejected(self):
        with self.assertRaises(ValueError):
            provision_coverage(["REF-01"])


class FeedArrangementTests(unittest.TestCase):
    def test_one_feed_forms_a_single_feed_beam(self):
        self.assertEqual(categorize_feed_arrangement(1), "single-feed-per-beam")

    def test_seven_feeds_form_a_multiple_feed_beam(self):
        self.assertEqual(categorize_feed_arrangement(7), "multiple-feed-per-beam")

    def test_zero_feeds_rejected(self):
        with self.assertRaises(ValueError):
            categorize_feed_arrangement(0)

    def test_fractional_feed_count_rejected(self):
        with self.assertRaises(ValueError):
            categorize_feed_arrangement(2.5)

    def test_boolean_feed_count_rejected(self):
        with self.assertRaises(ValueError):
            categorize_feed_arrangement(True)


class ReflectorEfficiencyTests(unittest.TestCase):
    def test_perfect_surface_is_lossless(self):
        self.assertAlmostEqual(surface_efficiency(0.0), 1.0, places=12)

    def test_surface_error_costs_efficiency(self):
        self.assertAlmostEqual(
            surface_efficiency(0.01), math.exp(-((4.0 * math.pi * 0.01) ** 2)), places=12
        )
        self.assertLess(surface_efficiency(0.02), surface_efficiency(0.01))

    def test_negative_surface_error_rejected(self):
        with self.assertRaises(ValueError):
            surface_efficiency(-0.001)

    def test_surface_error_beyond_the_small_error_regime_rejected(self):
        with self.assertRaises(ValueError):
            surface_efficiency(0.4)

    def test_almost_uniform_illumination_is_almost_ideal(self):
        self.assertAlmostEqual(illumination_efficiency(1.0e-6), 1.0, places=6)

    def test_deep_taper_tends_to_the_parabolic_limit(self):
        self.assertAlmostEqual(illumination_efficiency(100.0), 0.75, places=4)

    def test_illumination_efficiency_falls_with_taper(self):
        self.assertLess(illumination_efficiency(15.0), illumination_efficiency(8.0))

    def test_zero_edge_taper_rejected(self):
        with self.assertRaises(ValueError):
            illumination_efficiency(0.0)

    def test_spillover_at_ten_db_taper(self):
        self.assertAlmostEqual(spillover_efficiency(10.0), 0.9, places=12)

    def test_spillover_at_twenty_db_taper(self):
        self.assertAlmostEqual(spillover_efficiency(20.0), 0.99, places=12)

    def test_spillover_improves_with_taper(self):
        self.assertGreater(spillover_efficiency(15.0), spillover_efficiency(8.0))

    def test_negative_edge_taper_rejected(self):
        with self.assertRaises(ValueError):
            spillover_efficiency(-3.0)

    def test_illumination_and_spillover_trade_to_an_interior_optimum(self):
        amplitudes = [1.0, 1.0]
        mid = total_aperture_efficiency(0.0, 11.0, amplitudes)
        under = total_aperture_efficiency(0.0, 3.0, amplitudes)
        over = total_aperture_efficiency(0.0, 30.0, amplitudes)
        self.assertGreater(mid, under)
        self.assertGreater(mid, over)

    def test_extra_efficiency_above_unity_rejected(self):
        with self.assertRaises(ValueError):
            total_aperture_efficiency(0.0, 12.0, [1.0], extra_efficiency=1.2)

    def test_extra_efficiency_at_zero_rejected(self):
        with self.assertRaises(ValueError):
            total_aperture_efficiency(0.0, 12.0, [1.0], extra_efficiency=0.0)


class FeedClusterTests(unittest.TestCase):
    def test_uniform_cluster_is_fully_efficient(self):
        self.assertAlmostEqual(feed_cluster_efficiency([1.0, 1.0, 1.0, 1.0]), 1.0, places=12)

    def test_tapered_cluster_value(self):
        self.assertAlmostEqual(feed_cluster_efficiency([1.0, 0.5]), 0.9, places=12)

    def test_empty_cluster_rejected(self):
        with self.assertRaises(ValueError):
            feed_cluster_efficiency([])

    def test_negative_amplitude_rejected(self):
        with self.assertRaises(ValueError):
            feed_cluster_efficiency([1.0, -0.5])

    def test_unexcited_cluster_rejected(self):
        with self.assertRaises(ValueError):
            feed_cluster_efficiency([0.0, 0.0])


class OffsetFeedTests(unittest.TestCase):
    def test_beam_deviation_factor_value(self):
        k = 1.0 / (4.0 * 0.35)
        expected = (1.0 + 0.36 * k * k) / (1.0 + k * k)
        self.assertAlmostEqual(beam_deviation_factor(0.35), expected, places=12)

    def test_deeper_dish_deviates_more(self):
        self.assertLess(beam_deviation_factor(0.35), beam_deviation_factor(1.0))

    def test_beam_deviation_factor_never_exceeds_unity(self):
        for ratio in (0.25, 0.5, 1.0, 3.0):
            self.assertLess(beam_deviation_factor(ratio), 1.0)

    def test_zero_focal_ratio_rejected(self):
        with self.assertRaises(ValueError):
            beam_deviation_factor(0.0)

    def test_focal_ratio_outside_the_model_range_rejected(self):
        with self.assertRaises(ValueError):
            beam_deviation_factor(50.0)

    def test_centred_feed_produces_no_squint(self):
        self.assertAlmostEqual(beam_squint_deg(0.0, 35.0, 0.35), 0.0, places=12)

    def test_squint_grows_with_lateral_offset(self):
        self.assertGreater(beam_squint_deg(2.0, 35.0, 0.35), beam_squint_deg(1.0, 35.0, 0.35))

    def test_squint_value(self):
        expected = math.degrees(math.atan(2.0 / 35.0)) * beam_deviation_factor(0.35)
        self.assertAlmostEqual(beam_squint_deg(2.0, 35.0, 0.35), expected, places=12)

    def test_negative_offset_rejected(self):
        with self.assertRaises(ValueError):
            beam_squint_deg(-1.0, 35.0, 0.35)

    def test_zero_focal_length_rejected(self):
        with self.assertRaises(ValueError):
            beam_squint_deg(1.0, 0.0, 0.35)

    def test_beamwidth_value(self):
        self.assertAlmostEqual(beamwidth_deg(100.0), 0.659, places=9)

    def test_zero_diameter_beamwidth_rejected(self):
        with self.assertRaises(ValueError):
            beamwidth_deg(0.0)


class ScanLossTests(unittest.TestCase):
    def test_on_axis_beam_loses_nothing(self):
        self.assertAlmostEqual(scan_loss_db(0.0), 0.0, places=12)

    def test_scan_loss_is_quadratic(self):
        self.assertAlmostEqual(scan_loss_db(2.0, 0.4), 1.6, places=12)
        self.assertAlmostEqual(scan_loss_db(4.0, 0.4), 6.4, places=12)

    def test_negative_offset_rejected(self):
        with self.assertRaises(ValueError):
            scan_loss_db(-1.0)

    def test_offset_beyond_the_model_validity_rejected(self):
        with self.assertRaises(ValueError):
            scan_loss_db(25.0)

    def test_negative_coefficient_rejected(self):
        with self.assertRaises(ValueError):
            scan_loss_db(1.0, -0.2)

    def test_reflector_gain_value(self):
        expected = 10.0 * math.log10(0.6 * (math.pi * 100.0) ** 2)
        self.assertAlmostEqual(reflector_gain_dbi(100.0, 0.6), expected, places=9)

    def test_efficiency_above_unity_rejected(self):
        with self.assertRaises(ValueError):
            reflector_gain_dbi(100.0, 1.4)

    def test_zero_diameter_gain_rejected(self):
        with self.assertRaises(ValueError):
            reflector_gain_dbi(0.0, 0.6)


class BeamBudgetTests(unittest.TestCase):
    def test_budget_subtracts_every_loss_term(self):
        budget = beam_gain_budget(
            {"id": "B1", "lateral_offset_wavelengths": 0.3, "required_gain_dbi": 47.0},
            reflector_block(),
            feed_block(),
        )
        self.assertAlmostEqual(
            budget["realized_gain_dbi"],
            budget["on_axis_gain_dbi"] - budget["scan_loss_db"] - budget["network_loss_db"],
            places=12,
        )

    def test_margin_is_realized_minus_required(self):
        budget = beam_gain_budget(
            {"id": "B1", "lateral_offset_wavelengths": 0.0, "required_gain_dbi": 40.0},
            reflector_block(),
            feed_block(),
        )
        self.assertAlmostEqual(
            budget["margin_db"], budget["realized_gain_dbi"] - 40.0, places=12
        )
        self.assertTrue(budget["meets_requirement"])

    def test_offset_beam_pays_scan_loss(self):
        centred = beam_gain_budget(
            {"id": "B1", "lateral_offset_wavelengths": 0.0, "required_gain_dbi": 40.0},
            reflector_block(),
            feed_block(),
        )
        offset = beam_gain_budget(
            {"id": "B2", "lateral_offset_wavelengths": 3.0, "required_gain_dbi": 40.0},
            reflector_block(),
            feed_block(),
        )
        self.assertGreater(offset["scan_loss_db"], centred["scan_loss_db"])
        self.assertLess(offset["realized_gain_dbi"], centred["realized_gain_dbi"])

    def test_arrangement_is_carried_into_the_budget(self):
        budget = beam_gain_budget(
            {"id": "B1", "lateral_offset_wavelengths": 0.0, "required_gain_dbi": 40.0},
            reflector_block(),
            feed_block(),
        )
        self.assertEqual(budget["arrangement"], "multiple-feed-per-beam")

    def test_beam_without_id_rejected(self):
        with self.assertRaises(ValueError):
            beam_gain_budget(
                {"lateral_offset_wavelengths": 0.0, "required_gain_dbi": 40.0},
                reflector_block(),
                feed_block(),
            )

    def test_negative_network_loss_rejected(self):
        feed = feed_block()
        feed["network_loss_db"] = -0.5
        with self.assertRaises(ValueError):
            beam_gain_budget(
                {"id": "B1", "lateral_offset_wavelengths": 0.0, "required_gain_dbi": 40.0},
                reflector_block(),
                feed,
            )

    def test_missing_required_gain_rejected(self):
        with self.assertRaises(ValueError):
            beam_gain_budget(
                {"id": "B1", "lateral_offset_wavelengths": 0.0},
                reflector_block(),
                feed_block(),
            )

    def test_non_mapping_reflector_rejected(self):
        with self.assertRaises(ValueError):
            beam_gain_budget(
                {"id": "B1", "required_gain_dbi": 40.0}, ["D=100"], feed_block()
            )


class AssessmentTests(unittest.TestCase):
    def test_well_formed_design_is_compliant(self):
        result = assess_array_fed_reflector(base_config())
        self.assertTrue(result["compliant"])
        self.assertEqual(result["findings"], [])

    def test_every_beam_gets_a_budget(self):
        result = assess_array_fed_reflector(base_config())
        self.assertEqual(len(result["beam_budgets"]), 2)
        self.assertEqual(result["worst_beam"], "B2")

    def test_raised_requirement_produces_a_finding(self):
        config = base_config()
        config["beams"][1]["required_gain_dbi"] = 60.0
        result = assess_array_fed_reflector(config)
        self.assertFalse(result["compliant"])
        self.assertTrue(any("beam B2" in finding for finding in result["findings"]))

    def test_missing_array_provisions_produce_a_finding(self):
        config = base_config()
        config["provisions"] = [{"id": "REF-01", "family": "reflector", "verified": True}]
        result = assess_array_fed_reflector(config)
        self.assertFalse(result["compliant"])
        self.assertTrue(
            any("radiating-array provision" in finding for finding in result["findings"])
        )

    def test_unverified_provision_produces_a_finding(self):
        config = base_config()
        config["provisions"][0]["verified"] = False
        result = assess_array_fed_reflector(config)
        self.assertFalse(result["compliant"])
        self.assertTrue(any("not verified" in finding for finding in result["findings"]))

    def test_duplicate_beam_id_rejected(self):
        config = base_config()
        config["beams"][1]["id"] = "B1"
        with self.assertRaises(ValueError):
            assess_array_fed_reflector(config)

    def test_empty_beam_list_rejected(self):
        config = base_config()
        config["beams"] = []
        with self.assertRaises(ValueError):
            assess_array_fed_reflector(config)

    def test_non_mapping_config_rejected(self):
        with self.assertRaises(ValueError):
            assess_array_fed_reflector(["reflector"])

    def test_missing_feed_array_block_rejected(self):
        config = base_config()
        del config["feed_array"]
        with self.assertRaises(ValueError):
            assess_array_fed_reflector(config)

    def test_a_larger_scan_loss_coefficient_costs_the_offset_beam(self):
        config = base_config()
        base = assess_array_fed_reflector(config)["beam_budgets"][1]["realized_gain_dbi"]
        config["scan_loss_coefficient"] = 4.0
        harsh = assess_array_fed_reflector(config)["beam_budgets"][1]["realized_gain_dbi"]
        self.assertLess(harsh, base)


class ToleranceTests(unittest.TestCase):
    def test_representation_error_does_not_fail_an_equal_requirement(self):
        self.assertTrue(_ge(0.1 + 0.2, 0.3))
        self.assertTrue(_ge(0.3, 0.1 + 0.2))

    def test_a_real_shortfall_is_still_caught(self):
        self.assertFalse(_ge(0.29, 0.3))


if __name__ == "__main__":
    unittest.main()
