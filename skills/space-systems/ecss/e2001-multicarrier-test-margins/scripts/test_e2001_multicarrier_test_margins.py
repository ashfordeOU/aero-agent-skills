#!/usr/bin/env python3
"""Gate 3 contract test for e2001-multicarrier-test-margins.

Stdlib unittest, offline, deterministic. Run:
    python3 test_e2001_multicarrier_test_margins.py
"""

import math
import unittest

from e2001_multicarrier_test_margins_logic import (
    HERITAGE_LEVELS,
    ITEM_TYPES,
    MAX_SAMPLE_RELIEF_DB,
    MIN_TEST_MARGIN_DB,
    MODEL_PHILOSOPHIES,
    TEST_LEVEL_COMPONENT,
    TEST_LEVEL_EQUIPMENT,
    assess_campaign,
    assess_test_case,
    check_facility_headroom,
    from_dbw,
    peak_envelope_power_w,
    required_test_level_dbw,
    resolve_test_margin,
    sample_count_relief_db,
    to_dbw,
)


def case(article_id="omux-qm", item="output-multiplexer",
         heritage="flight-proven-recurring",
         model="dedicated-qualification-model", carriers=(50.0, 50.0),
         sample_count=1, facility_dbw=40.0):
    out = {
        "article_id": article_id,
        "item_type": item,
        "heritage": heritage,
        "model_philosophy": model,
        "carrier_powers_w": list(carriers),
        "facility_max_dbw": facility_dbw,
    }
    if sample_count is not None:
        out["sample_count"] = sample_count
    return out


class TestPeakEnvelopePower(unittest.TestCase):
    def test_two_equal_carriers_give_four_times_single_carrier_power(self):
        self.assertAlmostEqual(peak_envelope_power_w([50.0, 50.0]), 200.0)

    def test_sixteen_equal_carriers_scale_with_the_count_squared(self):
        self.assertAlmostEqual(peak_envelope_power_w([3.0] * 16), 3.0 * 256.0)

    def test_unequal_carriers_add_as_voltages(self):
        expected = (math.sqrt(80.0) + math.sqrt(20.0)) ** 2
        self.assertAlmostEqual(peak_envelope_power_w([80.0, 20.0]), expected)

    def test_single_carrier_is_refused_as_not_multicarrier(self):
        with self.assertRaises(ValueError):
            peak_envelope_power_w([100.0])

    def test_non_sequence_carrier_set_is_refused(self):
        with self.assertRaises(ValueError):
            peak_envelope_power_w("50,50")

    def test_zero_carrier_power_is_refused(self):
        with self.assertRaises(ValueError):
            peak_envelope_power_w([50.0, 0.0])

    def test_negative_carrier_power_is_refused(self):
        with self.assertRaises(ValueError):
            peak_envelope_power_w([50.0, -25.0])

    def test_non_numeric_carrier_power_is_refused(self):
        with self.assertRaises(ValueError):
            peak_envelope_power_w([50.0, None])


class TestDecibelHelpers(unittest.TestCase):
    def test_one_watt_is_zero_decibel_watt(self):
        self.assertAlmostEqual(to_dbw(1.0), 0.0)

    def test_two_hundred_watt_matches_its_logarithm(self):
        self.assertAlmostEqual(to_dbw(200.0), 10.0 * math.log10(200.0))

    def test_decibel_watt_round_trips_back_to_watt(self):
        self.assertAlmostEqual(from_dbw(to_dbw(37.5)), 37.5)

    def test_zero_watt_has_no_decibel_value(self):
        with self.assertRaises(ValueError):
            to_dbw(0.0)

    def test_non_numeric_level_is_refused(self):
        with self.assertRaises(ValueError):
            from_dbw("40")


class TestSampleCountRelief(unittest.TestCase):
    def test_a_single_article_earns_no_relief(self):
        self.assertAlmostEqual(sample_count_relief_db(1), 0.0)

    def test_a_second_article_earns_the_per_article_relief(self):
        self.assertAlmostEqual(sample_count_relief_db(2), 0.5)

    def test_relief_is_capped_however_many_articles_are_tested(self):
        self.assertAlmostEqual(sample_count_relief_db(3), MAX_SAMPLE_RELIEF_DB)
        self.assertAlmostEqual(sample_count_relief_db(9), MAX_SAMPLE_RELIEF_DB)

    def test_zero_articles_is_refused(self):
        with self.assertRaises(ValueError):
            sample_count_relief_db(0)

    def test_fractional_article_count_is_refused(self):
        with self.assertRaises(ValueError):
            sample_count_relief_db(2.5)

    def test_boolean_article_count_is_refused(self):
        with self.assertRaises(ValueError):
            sample_count_relief_db(True)


class TestTestMarginResolution(unittest.TestCase):
    def test_recurring_qualification_article_owes_its_base_margin(self):
        resolved = resolve_test_margin(
            "output-multiplexer", "flight-proven-recurring",
            "dedicated-qualification-model", 1
        )
        self.assertAlmostEqual(resolved["test_margin_db"], 6.0)
        self.assertEqual(resolved["test_level"], TEST_LEVEL_EQUIPMENT)
        self.assertEqual(resolved["findings"], [])
        self.assertEqual(resolved["notes"], [])

    def test_component_article_carries_the_component_test_level(self):
        resolved = resolve_test_margin(
            "waveguide-filter-component", "flight-proven-recurring",
            "dedicated-qualification-model", 1
        )
        self.assertEqual(resolved["test_level"], TEST_LEVEL_COMPONENT)

    def test_high_power_chain_owes_more_than_a_receive_chain(self):
        high = resolve_test_margin(
            "high-power-transmit-chain", "flight-proven-recurring",
            "dedicated-qualification-model", 1
        )
        low = resolve_test_margin(
            "low-power-receive-chain", "flight-proven-recurring",
            "dedicated-qualification-model", 1
        )
        self.assertGreater(high["test_margin_db"], low["test_margin_db"])

    def test_heritage_increment_orders_recurring_modified_and_new(self):
        margins = [
            resolve_test_margin(
                "waveguide-filter-component", h,
                "dedicated-qualification-model", 1
            )["test_margin_db"]
            for h in ("flight-proven-recurring", "modified-design", "new-design")
        ]
        self.assertLess(margins[0], margins[1])
        self.assertLess(margins[1], margins[2])

    def test_less_representative_build_standard_costs_more_margin(self):
        qualification = resolve_test_margin(
            "output-multiplexer", "new-design",
            "dedicated-qualification-model", 1
        )
        engineering = resolve_test_margin(
            "output-multiplexer", "new-design", "engineering-model", 1
        )
        self.assertAlmostEqual(
            engineering["test_margin_db"] - qualification["test_margin_db"],
            MODEL_PHILOSOPHIES["engineering-model"]["adder_db"],
        )

    def test_testing_more_articles_earns_relief(self):
        one = resolve_test_margin(
            "output-multiplexer", "new-design",
            "dedicated-qualification-model", 1
        )
        three = resolve_test_margin(
            "output-multiplexer", "new-design",
            "dedicated-qualification-model", 3
        )
        self.assertAlmostEqual(
            one["test_margin_db"] - three["test_margin_db"], MAX_SAMPLE_RELIEF_DB
        )

    def test_relief_cannot_drive_the_margin_below_the_floor(self):
        resolved = resolve_test_margin(
            "low-power-receive-chain", "flight-proven-recurring",
            "dedicated-qualification-model", 3
        )
        self.assertAlmostEqual(resolved["computed_margin_db"], 2.0)
        self.assertAlmostEqual(resolved["test_margin_db"], MIN_TEST_MARGIN_DB)
        self.assertEqual(len(resolved["notes"]), 1)
        self.assertIn("floor", resolved["notes"][0])

    def test_margin_landing_exactly_on_the_floor_is_not_clamped(self):
        resolved = resolve_test_margin(
            "low-power-receive-chain", "flight-proven-recurring",
            "dedicated-qualification-model", 2
        )
        self.assertAlmostEqual(resolved["test_margin_db"], MIN_TEST_MARGIN_DB)
        self.assertEqual(resolved["notes"], [])

    def test_breadboard_article_cannot_close_the_requirement(self):
        resolved = resolve_test_margin(
            "output-multiplexer", "new-design", "breadboard", 1
        )
        self.assertEqual(len(resolved["findings"]), 1)
        self.assertIn("build standard", resolved["findings"][0])

    def test_every_article_type_resolves_for_every_heritage_level(self):
        for item in ITEM_TYPES:
            for heritage in HERITAGE_LEVELS:
                with self.subTest(item=item, heritage=heritage):
                    resolved = resolve_test_margin(
                        item, heritage, "dedicated-qualification-model", 1
                    )
                    self.assertGreaterEqual(
                        resolved["test_margin_db"], MIN_TEST_MARGIN_DB
                    )

    def test_article_type_is_matched_case_and_whitespace_insensitively(self):
        resolved = resolve_test_margin(
            " Output-Multiplexer ", "New-Design",
            " Protoflight-Model ", 1
        )
        self.assertEqual(resolved["item_type"], "output-multiplexer")
        self.assertEqual(resolved["model_philosophy"], "protoflight-model")

    def test_uncategorized_article_type_is_refused(self):
        with self.assertRaises(ValueError):
            resolve_test_margin(
                "mystery-box", "new-design", "dedicated-qualification-model", 1
            )

    def test_uncategorized_heritage_level_is_refused(self):
        with self.assertRaises(ValueError):
            resolve_test_margin(
                "output-multiplexer", "mostly-proven",
                "dedicated-qualification-model", 1
            )

    def test_uncategorized_model_philosophy_is_refused(self):
        with self.assertRaises(ValueError):
            resolve_test_margin(
                "output-multiplexer", "new-design", "sketch-model", 1
            )


class TestRequiredLevelAndFacility(unittest.TestCase):
    def test_required_level_is_the_envelope_raised_by_the_margin(self):
        self.assertAlmostEqual(required_test_level_dbw(23.0, 6.0), 29.0)

    def test_negative_margin_is_refused(self):
        with self.assertRaises(ValueError):
            required_test_level_dbw(23.0, -1.0)

    def test_non_numeric_envelope_is_refused(self):
        with self.assertRaises(ValueError):
            required_test_level_dbw("23", 6.0)

    def test_facility_above_the_requirement_reports_positive_headroom(self):
        result = check_facility_headroom(29.0, 32.0)
        self.assertTrue(result["sufficient"])
        self.assertAlmostEqual(result["headroom_db"], 3.0)

    def test_facility_below_the_requirement_is_insufficient(self):
        result = check_facility_headroom(29.0, 27.5)
        self.assertFalse(result["sufficient"])
        self.assertAlmostEqual(result["headroom_db"], -1.5)

    def test_facility_exactly_at_the_requirement_is_sufficient(self):
        result = check_facility_headroom(29.0, 29.0)
        self.assertTrue(result["sufficient"])
        self.assertAlmostEqual(result["headroom_db"], 0.0)

    def test_non_numeric_facility_ceiling_is_refused(self):
        with self.assertRaises(ValueError):
            check_facility_headroom(29.0, None)


class TestArticleAssessment(unittest.TestCase):
    def test_article_within_facility_capability_is_testable(self):
        result = assess_test_case(case())
        self.assertTrue(result["testable"])
        self.assertEqual(result["findings"], [])
        self.assertAlmostEqual(result["test_margin_db"], 6.0)
        self.assertAlmostEqual(
            result["required_test_level_dbw"],
            result["peak_envelope_power_dbw"] + 6.0,
        )

    def test_required_level_in_watt_matches_its_decibel_value(self):
        result = assess_test_case(case())
        self.assertAlmostEqual(
            result["required_test_level_w"],
            from_dbw(result["required_test_level_dbw"]),
        )

    def test_facility_short_of_the_required_level_is_a_finding(self):
        result = assess_test_case(case(facility_dbw=25.0))
        self.assertFalse(result["testable"])
        self.assertFalse(result["facility_sufficient"])
        self.assertTrue(any("facility ceiling" in f for f in result["findings"]))

    def test_facility_landing_a_hair_short_through_rounding_still_passes(self):
        # The campaign ceiling is quoted the way it is sized: one carrier plus
        # the twenty-log envelope factor plus the margin. The logic reaches the
        # same level through the summed root-powers, which lands a few units in
        # the last place higher. That is representation error, not a shortfall.
        quoted = 10.0 * math.log10(3.0) + 20.0 * math.log10(16.0) + 6.0
        result = assess_test_case(
            case(
                item="high-power-transmit-chain",
                carriers=tuple([3.0] * 16),
                facility_dbw=quoted,
            )
        )
        self.assertGreater(result["required_test_level_dbw"], quoted)
        self.assertTrue(result["facility_sufficient"])
        self.assertAlmostEqual(result["facility_headroom_db"], 0.0)
        self.assertTrue(result["testable"])

    def test_breadboard_article_is_not_testable_even_with_headroom(self):
        result = assess_test_case(case(model="breadboard", facility_dbw=60.0))
        self.assertTrue(result["facility_sufficient"])
        self.assertFalse(result["testable"])

    def test_default_sample_count_is_a_single_article(self):
        result = assess_test_case(case(sample_count=None))
        self.assertAlmostEqual(result["sample_relief_db"], 0.0)

    def test_article_with_a_single_carrier_is_refused(self):
        with self.assertRaises(ValueError):
            assess_test_case(case(carriers=(120.0,)))

    def test_article_without_an_identifier_is_refused(self):
        bad = case()
        bad["article_id"] = ""
        with self.assertRaises(ValueError):
            assess_test_case(bad)

    def test_non_mapping_article_is_refused(self):
        with self.assertRaises(ValueError):
            assess_test_case(["omux-qm"])

    def test_carrier_count_is_reported(self):
        result = assess_test_case(case(carriers=(20.0, 20.0, 20.0)))
        self.assertEqual(result["carrier_count"], 3)


class TestCampaignAggregation(unittest.TestCase):
    def test_campaign_with_every_article_testable(self):
        result = assess_campaign([case("omux-qm"), case("filter-qm",
                                  item="waveguide-filter-component")])
        self.assertTrue(result["testable"])
        self.assertEqual(result["article_count"], 2)
        self.assertEqual(result["blocked_articles"], [])

    def test_campaign_reports_the_highest_required_level(self):
        result = assess_campaign(
            [
                case("omux-qm", carriers=(50.0, 50.0)),
                case("chain-qm", item="high-power-transmit-chain",
                     carriers=(50.0, 50.0, 50.0), facility_dbw=45.0),
            ]
        )
        levels = [a["required_test_level_dbw"] for a in result["articles"]]
        self.assertAlmostEqual(result["highest_required_level_dbw"], max(levels))

    def test_campaign_lists_every_blocked_article(self):
        result = assess_campaign(
            [
                case("omux-qm"),
                case("bb-1", model="breadboard"),
                case("filter-qm", item="waveguide-filter-component",
                     facility_dbw=20.0),
            ]
        )
        self.assertFalse(result["testable"])
        self.assertEqual(result["blocked_articles"], ["bb-1", "filter-qm"])
        self.assertTrue(all(":" in f for f in result["findings"]))

    def test_duplicate_article_identifier_is_refused(self):
        with self.assertRaises(ValueError):
            assess_campaign([case("omux-qm"), case("omux-qm")])

    def test_empty_campaign_is_refused(self):
        with self.assertRaises(ValueError):
            assess_campaign([])

    def test_non_sequence_campaign_is_refused(self):
        with self.assertRaises(ValueError):
            assess_campaign("omux-qm")


if __name__ == "__main__":
    unittest.main()
