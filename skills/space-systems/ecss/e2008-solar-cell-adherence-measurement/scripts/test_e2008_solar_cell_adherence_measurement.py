#!/usr/bin/env python3
"""Contract test for the cell-assembly adherence measurement (offline).

Walks the clause workflow step by step: the coupon representativeness
screen, the separation-stress and separation-mode reduction, the
population statistics and the one-sided lower tolerance bound, and the
acceptance gate that has to stop a campaign whose weak tail falls short
of the minimum. This is the gate 3 review evidence for the leaf.
"""

import copy
import unittest

from e2008_solar_cell_adherence_measurement_logic import (
    ADHERENCE_DEMONSTRATED,
    ADHERENCE_NOT_DEMONSTRATED,
    ADHERENCE_NOT_EVALUATED,
    COUPON_ATTRIBUTES,
    DEFAULT_ADHERENCE_POLICY,
    SEPARATION_MODES,
    TOLERANCE_FACTORS,
    adherence_statistics,
    adherence_strength_mpa,
    coupon_representativeness,
    evaluate_adherence_campaign,
    evaluate_coupon,
    interface_separation_fraction,
    lower_tolerance_bound_mpa,
    tolerance_factor,
    validate_adherence_policy,
)

PANEL_BUILD = {
    "substrate-facesheet": "cfrp-facesheet-0p15mm",
    "adhesive-designation": "space-grade-silicone-a",
    "adhesive-lot": "lot-2291",
    "cure-profile": "24h-ambient-then-2h-at-60c",
    "cell-assembly-type": "triple-junction-cic-100um-coverglass",
    "bonding-tool": "vacuum-bag-tool-3",
}


def _coupon(identifier, force_n, area_mm2=100.0, mode="cohesive-adhesive", **build):
    record = {
        "id": identifier,
        "peak_force_n": force_n,
        "bonded_area_mm2": area_mm2,
        "separation_mode": mode,
        "build": copy.deepcopy(PANEL_BUILD),
    }
    record["build"].update(build)
    return record


def _campaign(forces, modes=None, area_mm2=100.0):
    modes = modes or ["cohesive-adhesive"] * len(forces)
    return {
        "panel_build": copy.deepcopy(PANEL_BUILD),
        "coupons": [
            _coupon("c%d" % (index + 1), force, area_mm2, mode)
            for index, (force, mode) in enumerate(zip(forces, modes))
        ],
    }


SOUND_CAMPAIGN = _campaign([40.0, 41.0, 40.5, 39.5, 40.2])


class PolicyTests(unittest.TestCase):
    def test_default_policy_validates(self):
        self.assertIs(
            validate_adherence_policy(DEFAULT_ADHERENCE_POLICY),
            DEFAULT_ADHERENCE_POLICY,
        )

    def test_non_mapping_policy_rejected(self):
        with self.assertRaises(ValueError):
            validate_adherence_policy("default")

    def test_zero_required_minimum_rejected(self):
        broken = copy.deepcopy(DEFAULT_ADHERENCE_POLICY)
        broken["required_minimum_mpa"] = 0.0
        with self.assertRaises(ValueError):
            validate_adherence_policy(broken)

    def test_fractional_coupon_count_rejected(self):
        broken = copy.deepcopy(DEFAULT_ADHERENCE_POLICY)
        broken["min_coupon_count"] = 4.5
        with self.assertRaises(ValueError):
            validate_adherence_policy(broken)

    def test_interface_fraction_above_one_rejected(self):
        broken = copy.deepcopy(DEFAULT_ADHERENCE_POLICY)
        broken["max_interface_separation_fraction"] = 1.5
        with self.assertRaises(ValueError):
            validate_adherence_policy(broken)

    def test_non_boolean_tolerance_flag_rejected(self):
        broken = copy.deepcopy(DEFAULT_ADHERENCE_POLICY)
        broken["require_tolerance_bound"] = "yes"
        with self.assertRaises(ValueError):
            validate_adherence_policy(broken)


class RepresentativenessTests(unittest.TestCase):
    def test_matching_build_is_representative(self):
        result = coupon_representativeness(
            copy.deepcopy(PANEL_BUILD), copy.deepcopy(PANEL_BUILD)
        )
        self.assertTrue(result["representative"])
        self.assertEqual(result["mismatched_attributes"], [])
        self.assertEqual(result["findings"], [])

    def test_a_different_adhesive_lot_breaks_representativeness(self):
        coupon = copy.deepcopy(PANEL_BUILD)
        coupon["adhesive-lot"] = "lot-3004"
        result = coupon_representativeness(coupon, PANEL_BUILD)
        self.assertFalse(result["representative"])
        self.assertEqual(result["mismatched_attributes"], ["adhesive-lot"])

    def test_every_governing_attribute_is_compared(self):
        for attribute in COUPON_ATTRIBUTES:
            coupon = copy.deepcopy(PANEL_BUILD)
            coupon[attribute] = "something-else"
            result = coupon_representativeness(coupon, PANEL_BUILD)
            self.assertEqual(result["mismatched_attributes"], [attribute])

    def test_mismatch_is_named_in_the_findings(self):
        coupon = copy.deepcopy(PANEL_BUILD)
        coupon["cure-profile"] = "8h-ambient-only"
        result = coupon_representativeness(coupon, PANEL_BUILD)
        self.assertTrue(any("cure-profile" in note for note in result["findings"]))

    def test_missing_attribute_rejected(self):
        coupon = copy.deepcopy(PANEL_BUILD)
        del coupon["bonding-tool"]
        with self.assertRaises(ValueError):
            coupon_representativeness(coupon, PANEL_BUILD)

    def test_non_mapping_build_rejected(self):
        with self.assertRaises(ValueError):
            coupon_representativeness("as-panel", PANEL_BUILD)


class StrengthTests(unittest.TestCase):
    def test_strength_is_force_over_bonded_area(self):
        self.assertAlmostEqual(adherence_strength_mpa(40.0, 100.0), 0.4, places=12)

    def test_a_smaller_bonded_area_raises_the_stress(self):
        self.assertAlmostEqual(adherence_strength_mpa(40.0, 50.0), 0.8, places=12)

    def test_zero_bonded_area_rejected(self):
        with self.assertRaises(ValueError):
            adherence_strength_mpa(40.0, 0.0)

    def test_negative_force_rejected(self):
        with self.assertRaises(ValueError):
            adherence_strength_mpa(-40.0, 100.0)

    def test_non_numeric_force_rejected(self):
        with self.assertRaises(ValueError):
            adherence_strength_mpa("40 N", 100.0)


class CouponTests(unittest.TestCase):
    def test_cohesive_separation_is_a_bond_measurement(self):
        record = evaluate_coupon(_coupon("c1", 40.0), PANEL_BUILD)
        self.assertFalse(record["bond_strength_is_lower_bound"])
        self.assertAlmostEqual(record["strength_mpa"], 0.4, places=12)

    def test_facesheet_separation_is_only_a_lower_bound(self):
        record = evaluate_coupon(
            _coupon("c2", 40.0, mode="substrate-facesheet"), PANEL_BUILD
        )
        self.assertTrue(record["bond_strength_is_lower_bound"])
        self.assertTrue(any("lower bound" in note for note in record["findings"]))

    def test_cell_assembly_fracture_is_only_a_lower_bound(self):
        record = evaluate_coupon(
            _coupon("c3", 40.0, mode="cell-assembly-fracture"), PANEL_BUILD
        )
        self.assertTrue(record["bond_strength_is_lower_bound"])

    def test_every_recognized_mode_is_accepted(self):
        for mode in SEPARATION_MODES:
            record = evaluate_coupon(_coupon("c", 40.0, mode=mode), PANEL_BUILD)
            self.assertEqual(record["separation_mode"], mode)

    def test_unknown_separation_mode_rejected(self):
        with self.assertRaises(ValueError):
            evaluate_coupon(_coupon("c4", 40.0, mode="came-apart"), PANEL_BUILD)


class StatisticsTests(unittest.TestCase):
    def test_identical_coupons_have_no_spread(self):
        stats = adherence_statistics([0.4, 0.4, 0.4, 0.4])
        self.assertAlmostEqual(stats["mean_mpa"], 0.4, places=12)
        self.assertAlmostEqual(stats["std_dev_mpa"], 0.0, places=12)

    def test_mean_and_extremes_are_reported(self):
        stats = adherence_statistics([0.3, 0.4, 0.5])
        self.assertAlmostEqual(stats["mean_mpa"], 0.4, places=12)
        self.assertAlmostEqual(stats["min_mpa"], 0.3, places=12)
        self.assertAlmostEqual(stats["max_mpa"], 0.5, places=12)
        self.assertEqual(stats["count"], 3)

    def test_single_coupon_rejected(self):
        with self.assertRaises(ValueError):
            adherence_statistics([0.4])

    def test_empty_population_rejected(self):
        with self.assertRaises(ValueError):
            adherence_statistics([])

    def test_non_positive_strength_rejected(self):
        with self.assertRaises(ValueError):
            adherence_statistics([0.4, 0.0, 0.5])


class ToleranceBoundTests(unittest.TestCase):
    def test_factor_falls_as_the_sample_grows(self):
        sizes = sorted(TOLERANCE_FACTORS)
        for smaller, larger in zip(sizes, sizes[1:]):
            self.assertLess(TOLERANCE_FACTORS[larger], TOLERANCE_FACTORS[smaller])

    def test_intermediate_sample_takes_the_conservative_factor(self):
        self.assertAlmostEqual(tolerance_factor(11), TOLERANCE_FACTORS[10], places=12)

    def test_large_sample_uses_the_last_tabulated_factor(self):
        self.assertAlmostEqual(tolerance_factor(400), TOLERANCE_FACTORS[30], places=12)

    def test_too_few_coupons_for_a_bound_rejected(self):
        with self.assertRaises(ValueError):
            tolerance_factor(2)

    def test_non_integer_sample_size_rejected(self):
        with self.assertRaises(ValueError):
            tolerance_factor(7.5)

    def test_zero_spread_bound_equals_the_mean(self):
        self.assertAlmostEqual(
            lower_tolerance_bound_mpa([0.4] * 5), 0.4, places=12
        )

    def test_scatter_pushes_the_bound_below_the_mean(self):
        scattered = lower_tolerance_bound_mpa([0.40, 0.45, 0.50, 0.55, 0.60])
        self.assertLess(scattered, 0.30)


class SeparationMixTests(unittest.TestCase):
    def test_no_interface_separation_gives_zero(self):
        self.assertAlmostEqual(
            interface_separation_fraction(["cohesive-adhesive"] * 4), 0.0, places=12
        )

    def test_one_in_four_interface_separations(self):
        modes = ["cohesive-adhesive"] * 3 + ["adhesive-interface"]
        self.assertAlmostEqual(interface_separation_fraction(modes), 0.25, places=12)

    def test_empty_mode_sequence_rejected(self):
        with self.assertRaises(ValueError):
            interface_separation_fraction([])

    def test_unknown_mode_in_the_mix_rejected(self):
        with self.assertRaises(ValueError):
            interface_separation_fraction(["cohesive-adhesive", "unzipped"])


class CampaignTests(unittest.TestCase):
    def test_sound_campaign_is_demonstrated(self):
        result = evaluate_adherence_campaign(SOUND_CAMPAIGN)
        self.assertEqual(result["verdict"], ADHERENCE_DEMONSTRATED)
        self.assertTrue(result["compliant"])
        self.assertEqual(result["representative_count"], 5)
        self.assertAlmostEqual(result["interface_separation_fraction"], 0.0, places=12)

    def test_weak_coupon_fails_the_minimum(self):
        campaign = _campaign([40.0, 41.0, 40.5, 39.5, 20.0])
        result = evaluate_adherence_campaign(campaign)
        self.assertEqual(result["verdict"], ADHERENCE_NOT_DEMONSTRATED)
        self.assertFalse(result["compliant"])
        self.assertTrue(any("weakest coupon" in note for note in result["findings"]))

    def test_interface_separation_fails_the_mode_policy(self):
        campaign = _campaign(
            [40.0, 41.0, 40.5, 39.5, 40.2],
            modes=["cohesive-adhesive"] * 4 + ["adhesive-interface"],
        )
        result = evaluate_adherence_campaign(campaign)
        self.assertFalse(result["compliant"])
        self.assertTrue(
            any("interface separations" in note for note in result["findings"])
        )

    def test_unrepresentative_coupon_is_excluded_from_the_population(self):
        campaign = copy.deepcopy(SOUND_CAMPAIGN)
        campaign["coupons"][0]["build"]["adhesive-lot"] = "lot-9999"
        result = evaluate_adherence_campaign(campaign)
        self.assertEqual(result["excluded_coupon_ids"], ["c1"])
        self.assertEqual(result["representative_count"], 4)

    def test_every_coupon_unrepresentative_is_not_evaluated(self):
        campaign = copy.deepcopy(SOUND_CAMPAIGN)
        for coupon in campaign["coupons"]:
            coupon["build"]["bonding-tool"] = "bench-press"
        result = evaluate_adherence_campaign(campaign)
        self.assertEqual(result["verdict"], ADHERENCE_NOT_EVALUATED)
        self.assertIsNone(result["compliant"])
        self.assertIsNone(result["lower_tolerance_bound_mpa"])

    def test_too_few_coupons_is_not_demonstrated(self):
        campaign = _campaign([40.0, 41.0, 40.5])
        result = evaluate_adherence_campaign(campaign)
        self.assertEqual(result["verdict"], ADHERENCE_NOT_DEMONSTRATED)
        self.assertTrue(
            any("representative coupon(s)" in note for note in result["findings"])
        )

    def test_campaign_exactly_on_the_requirement_is_demonstrated(self):
        # 0.35 MPa reached through a quotient that need not land on the
        # acceptance number bit for bit.
        required = DEFAULT_ADHERENCE_POLICY["required_minimum_mpa"]
        area = 7.0
        campaign = _campaign([required * area] * 5, area_mm2=area)
        result = evaluate_adherence_campaign(campaign)
        self.assertAlmostEqual(result["min_mpa"], required, places=9)
        self.assertAlmostEqual(
            result["lower_tolerance_bound_mpa"], required, places=9
        )
        self.assertTrue(result["compliant"])
        self.assertEqual(result["verdict"], ADHERENCE_DEMONSTRATED)

    def test_scatter_alone_can_fail_the_tolerance_bound(self):
        campaign = _campaign([40.0, 45.0, 50.0, 55.0, 60.0])
        result = evaluate_adherence_campaign(campaign)
        self.assertAlmostEqual(result["min_mpa"], 0.4, places=12)
        self.assertFalse(result["compliant"])
        self.assertTrue(
            any("lower tolerance bound" in note for note in result["findings"])
        )

    def test_waiving_the_bound_passes_the_same_scattered_population(self):
        policy = copy.deepcopy(DEFAULT_ADHERENCE_POLICY)
        policy["require_tolerance_bound"] = False
        campaign = _campaign([40.0, 45.0, 50.0, 55.0, 60.0])
        result = evaluate_adherence_campaign(campaign, policy)
        self.assertTrue(result["compliant"])

    def test_campaign_without_coupons_rejected(self):
        campaign = copy.deepcopy(SOUND_CAMPAIGN)
        campaign["coupons"] = []
        with self.assertRaises(ValueError):
            evaluate_adherence_campaign(campaign)

    def test_campaign_without_a_panel_build_rejected(self):
        campaign = copy.deepcopy(SOUND_CAMPAIGN)
        del campaign["panel_build"]
        with self.assertRaises(ValueError):
            evaluate_adherence_campaign(campaign)

    def test_non_mapping_campaign_rejected(self):
        with self.assertRaises(ValueError):
            evaluate_adherence_campaign("five coupons, all good")


if __name__ == "__main__":
    unittest.main()
