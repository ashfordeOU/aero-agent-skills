#!/usr/bin/env python3
"""Contract test for the clause 7.2.3.2 secondary-arc coupon campaign logic."""

import unittest

from e2006_secondary_arc_test_characteristics_logic import (
    BASE_TRIGGERED_ARCS_PER_POINT,
    DIMENSION_TOLERANCE_FRACTION,
    NON_SUSTAINED_DURATION_LIMIT_S,
    arc_duration_from_timestamps,
    build_test_matrix,
    campaign_arc_budget,
    categorize_arc_event,
    coupon_representativeness_deviations,
    evaluate_campaign,
    evaluate_point_result,
    required_triggered_arcs,
    validate_coupon,
)


def flight_article(**overrides):
    article = {
        "id": "flight-wing-1",
        "strings": 4,
        "cells_per_string": 6,
        "conductor_gap_mm": 0.60,
        "coverglass_thickness_um": 100.0,
        "interconnect_type": "silver-mesh",
        "adhesive_type": "silicone",
        "harness_routing": "rear-face-bundled",
    }
    article.update(overrides)
    return article


def coupon(**overrides):
    sample = flight_article(id="coupon-a", strings=4)
    sample.update(overrides)
    return sample


def arc_event(duration_s, current_a=0.4):
    return {"duration_s": duration_s, "current_a": current_a}


class CouponValidationTests(unittest.TestCase):
    def test_valid_coupon_is_normalized(self):
        item = validate_coupon(coupon())
        self.assertEqual(item["id"], "coupon-a")
        self.assertAlmostEqual(item["conductor_gap_mm"], 0.60, places=9)

    def test_material_names_are_normalized_to_lower_case(self):
        item = validate_coupon(coupon(interconnect_type="Silver-Mesh"))
        self.assertEqual(item["interconnect_type"], "silver-mesh")

    def test_single_string_coupon_is_rejected(self):
        with self.assertRaises(ValueError):
            validate_coupon(coupon(strings=1))

    def test_single_cell_string_is_rejected(self):
        with self.assertRaises(ValueError):
            validate_coupon(coupon(cells_per_string=1))

    def test_missing_id_is_rejected(self):
        sample = coupon()
        del sample["id"]
        with self.assertRaises(ValueError):
            validate_coupon(sample)

    def test_zero_conductor_gap_is_rejected(self):
        with self.assertRaises(ValueError):
            validate_coupon(coupon(conductor_gap_mm=0.0))

    def test_non_string_adhesive_is_rejected(self):
        with self.assertRaises(ValueError):
            validate_coupon(coupon(adhesive_type=17))

    def test_non_mapping_coupon_is_rejected(self):
        with self.assertRaises(ValueError):
            validate_coupon("coupon-a")

    def test_boolean_string_count_is_rejected(self):
        with self.assertRaises(ValueError):
            validate_coupon(coupon(strings=True))


class RepresentativenessTests(unittest.TestCase):
    def test_matching_coupon_has_no_deviations(self):
        self.assertEqual(
            coupon_representativeness_deviations(coupon(), flight_article()), []
        )

    def test_gap_inside_tolerance_is_representative(self):
        self.assertEqual(
            coupon_representativeness_deviations(
                coupon(conductor_gap_mm=0.61), flight_article()
            ),
            [],
        )

    def test_gap_exactly_at_tolerance_is_absorbed(self):
        # 0.63 mm against a 0.60 mm flight gap is exactly the 5 % allowance,
        # but the relative deviation lands a few ULP above it in binary.
        relative = abs(0.63 - 0.60) / 0.60
        self.assertGreater(relative, DIMENSION_TOLERANCE_FRACTION)
        self.assertEqual(
            coupon_representativeness_deviations(
                coupon(conductor_gap_mm=0.63), flight_article()
            ),
            [],
        )

    def test_gap_outside_tolerance_is_a_deviation(self):
        deviations = coupon_representativeness_deviations(
            coupon(conductor_gap_mm=0.90), flight_article()
        )
        self.assertEqual(len(deviations), 1)
        self.assertEqual(deviations[0]["field"], "conductor_gap_mm")
        self.assertAlmostEqual(deviations[0]["relative_deviation"], 0.5, places=9)

    def test_coverglass_deviation_is_reported(self):
        deviations = coupon_representativeness_deviations(
            coupon(coverglass_thickness_um=150.0), flight_article()
        )
        self.assertEqual(deviations[0]["field"], "coverglass_thickness_um")

    def test_different_interconnect_is_a_deviation(self):
        deviations = coupon_representativeness_deviations(
            coupon(interconnect_type="copper-tab"), flight_article()
        )
        self.assertEqual(deviations[0]["field"], "interconnect_type")
        self.assertIsNone(deviations[0]["relative_deviation"])

    def test_different_harness_routing_is_a_deviation(self):
        deviations = coupon_representativeness_deviations(
            coupon(harness_routing="front-face-taped"), flight_article()
        )
        self.assertEqual(deviations[0]["field"], "harness_routing")

    def test_fewer_strings_than_flight_is_a_deviation(self):
        deviations = coupon_representativeness_deviations(
            coupon(strings=2), flight_article()
        )
        self.assertEqual(deviations[0]["field"], "strings")

    def test_more_strings_than_flight_is_acceptable(self):
        self.assertEqual(
            coupon_representativeness_deviations(coupon(strings=8), flight_article()), []
        )

    def test_several_deviations_are_all_reported(self):
        deviations = coupon_representativeness_deviations(
            coupon(conductor_gap_mm=1.2, adhesive_type="epoxy"), flight_article()
        )
        fields = sorted(d["field"] for d in deviations)
        self.assertEqual(fields, ["adhesive_type", "conductor_gap_mm"])


class TestMatrixTests(unittest.TestCase):
    def test_matrix_is_the_full_grid(self):
        matrix = build_test_matrix([50.0, 100.0], [0.5, 1.0, 2.0])
        self.assertEqual(len(matrix), 6)
        self.assertAlmostEqual(matrix[0]["voltage_v"], 50.0, places=9)
        self.assertAlmostEqual(matrix[-1]["current_a"], 2.0, places=9)

    def test_empty_voltage_list_is_rejected(self):
        with self.assertRaises(ValueError):
            build_test_matrix([], [0.5])

    def test_duplicate_current_point_is_rejected(self):
        with self.assertRaises(ValueError):
            build_test_matrix([50.0], [0.5, 0.5])

    def test_voltage_above_the_ceiling_is_rejected(self):
        with self.assertRaises(ValueError):
            build_test_matrix([500.0], [0.5])

    def test_negative_current_point_is_rejected(self):
        with self.assertRaises(ValueError):
            build_test_matrix([50.0], [-0.5])

    def test_point_away_from_the_boundary_uses_the_base_count(self):
        self.assertEqual(
            required_triggered_arcs({"voltage_v": 30.0}, 100.0),
            BASE_TRIGGERED_ARCS_PER_POINT,
        )

    def test_point_near_the_boundary_is_doubled(self):
        self.assertEqual(
            required_triggered_arcs({"voltage_v": 105.0}, 100.0),
            BASE_TRIGGERED_ARCS_PER_POINT * 2,
        )

    def test_point_exactly_at_the_band_edge_is_doubled(self):
        self.assertEqual(
            required_triggered_arcs({"voltage_v": 115.0}, 100.0),
            BASE_TRIGGERED_ARCS_PER_POINT * 2,
        )

    def test_custom_base_count_is_honoured(self):
        self.assertEqual(required_triggered_arcs({"voltage_v": 30.0}, 100.0, base=25), 25)

    def test_zero_base_count_is_rejected(self):
        with self.assertRaises(ValueError):
            required_triggered_arcs({"voltage_v": 30.0}, 100.0, base=0)

    def test_point_without_voltage_is_rejected(self):
        with self.assertRaises(ValueError):
            required_triggered_arcs({"current_a": 1.0}, 100.0)

    def test_budget_sums_over_the_matrix(self):
        matrix = build_test_matrix([30.0, 105.0], [1.0])
        self.assertEqual(
            campaign_arc_budget(matrix, 100.0), BASE_TRIGGERED_ARCS_PER_POINT * 3
        )

    def test_budget_rejects_an_empty_matrix(self):
        with self.assertRaises(ValueError):
            campaign_arc_budget([], 100.0)


class ArcEventTests(unittest.TestCase):
    def test_short_event_is_non_sustained(self):
        self.assertEqual(categorize_arc_event(2.0e-4, 0.4), "non-sustained")

    def test_event_exactly_at_the_millisecond_limit_is_non_sustained(self):
        self.assertEqual(
            categorize_arc_event(NON_SUSTAINED_DURATION_LIMIT_S, 0.4), "non-sustained"
        )

    def test_timestamp_difference_at_the_limit_is_absorbed(self):
        # A 1.2 ms to 2.2 ms window is exactly 1 ms physically, but the
        # difference lands two ULP above the limit in binary.
        duration = arc_duration_from_timestamps(0.0012, 0.0022)
        self.assertGreater(duration, NON_SUSTAINED_DURATION_LIMIT_S)
        self.assertEqual(categorize_arc_event(duration, 0.4), "non-sustained")

    def test_mid_length_event_is_temporary_sustained(self):
        self.assertEqual(categorize_arc_event(0.25, 0.4), "temporary-sustained")

    def test_long_event_is_permanent_sustained(self):
        self.assertEqual(categorize_arc_event(12.0, 0.4), "permanent-sustained")

    def test_current_below_the_floor_is_not_an_arc(self):
        self.assertEqual(categorize_arc_event(5.0, 0.001), "below-detection")

    def test_detection_floor_can_be_overridden(self):
        self.assertEqual(
            categorize_arc_event(5.0, 0.05, detection_floor_a=0.1), "below-detection"
        )

    def test_negative_duration_is_rejected(self):
        with self.assertRaises(ValueError):
            categorize_arc_event(-1.0, 0.4)

    def test_negative_current_is_rejected(self):
        with self.assertRaises(ValueError):
            categorize_arc_event(1.0, -0.4)

    def test_reversed_timestamps_are_rejected(self):
        with self.assertRaises(ValueError):
            arc_duration_from_timestamps(0.004, 0.002)

    def test_duration_from_timestamps_is_the_difference(self):
        self.assertAlmostEqual(
            arc_duration_from_timestamps(1.0, 1.5), 0.5, places=9
        )


class PointResultTests(unittest.TestCase):
    def test_point_with_enough_clean_arcs_passes(self):
        events = [arc_event(3.0e-4) for _ in range(10)]
        result = evaluate_point_result({"voltage_v": 30.0}, events, 100.0)
        self.assertTrue(result["passed"])
        self.assertEqual(result["triggered_arcs"], 10)
        self.assertEqual(result["sustained_events"], 0)

    def test_point_short_of_the_arc_budget_fails(self):
        events = [arc_event(3.0e-4) for _ in range(4)]
        result = evaluate_point_result({"voltage_v": 30.0}, events, 100.0)
        self.assertFalse(result["arc_count_met"])
        self.assertFalse(result["passed"])

    def test_sustained_event_fails_the_point(self):
        events = [arc_event(3.0e-4) for _ in range(9)] + [arc_event(0.4)]
        result = evaluate_point_result({"voltage_v": 30.0}, events, 100.0)
        self.assertTrue(result["arc_count_met"])
        self.assertEqual(result["sustained_events"], 1)
        self.assertFalse(result["passed"])

    def test_below_detection_events_do_not_count_as_triggered(self):
        events = [arc_event(3.0e-4, current_a=0.0005) for _ in range(10)]
        result = evaluate_point_result({"voltage_v": 30.0}, events, 100.0)
        self.assertEqual(result["triggered_arcs"], 0)
        self.assertEqual(result["category_counts"]["below-detection"], 10)

    def test_near_boundary_point_needs_the_doubled_budget(self):
        events = [arc_event(3.0e-4) for _ in range(10)]
        result = evaluate_point_result({"voltage_v": 105.0}, events, 100.0)
        self.assertEqual(result["required_arcs"], 20)
        self.assertFalse(result["arc_count_met"])

    def test_non_sequence_events_are_rejected(self):
        with self.assertRaises(ValueError):
            evaluate_point_result({"voltage_v": 30.0}, "ten-arcs", 100.0)

    def test_non_mapping_event_is_rejected(self):
        with self.assertRaises(ValueError):
            evaluate_point_result({"voltage_v": 30.0}, [0.0003], 100.0)


class CampaignTests(unittest.TestCase):
    def setUp(self):
        self.matrix = build_test_matrix([30.0, 60.0], [1.0])
        self.clean = [[arc_event(3.0e-4) for _ in range(10)] for _ in self.matrix]
        self.coupons = [coupon(id="coupon-a"), coupon(id="coupon-b")]

    def test_clean_campaign_passes(self):
        result = evaluate_campaign(
            self.coupons, flight_article(), self.matrix, self.clean, 100.0
        )
        self.assertTrue(result["campaign_passed"])
        self.assertEqual(result["findings"], [])
        self.assertEqual(result["arc_budget"], 20)

    def test_non_representative_coupon_fails_the_campaign(self):
        coupons = [coupon(id="coupon-a"), coupon(id="coupon-b", conductor_gap_mm=1.5)]
        result = evaluate_campaign(
            coupons, flight_article(), self.matrix, self.clean, 100.0
        )
        self.assertFalse(result["campaign_passed"])
        self.assertIn("coupon-not-representative", result["findings"])
        self.assertEqual(result["non_representative_coupons"], ["coupon-b"])

    def test_sustained_event_fails_the_campaign(self):
        results = [list(events) for events in self.clean]
        results[1][0] = arc_event(4.0)
        result = evaluate_campaign(
            self.coupons, flight_article(), self.matrix, results, 100.0
        )
        self.assertFalse(result["campaign_passed"])
        self.assertIn("sustained-arc-recorded", result["findings"])
        self.assertEqual(result["sustained_points_v"], [60.0])

    def test_short_arc_budget_fails_the_campaign(self):
        results = [self.clean[0], self.clean[1][:3]]
        result = evaluate_campaign(
            self.coupons, flight_article(), self.matrix, results, 100.0
        )
        self.assertIn("arc-budget-not-reached", result["findings"])
        self.assertEqual(result["incomplete_points_v"], [60.0])

    def test_single_coupon_campaign_is_rejected(self):
        with self.assertRaises(ValueError):
            evaluate_campaign(
                [coupon()], flight_article(), self.matrix, self.clean, 100.0
            )

    def test_result_count_mismatch_is_rejected(self):
        with self.assertRaises(ValueError):
            evaluate_campaign(
                self.coupons, flight_article(), self.matrix, self.clean[:1], 100.0
            )

    def test_empty_matrix_is_rejected(self):
        with self.assertRaises(ValueError):
            evaluate_campaign(self.coupons, flight_article(), [], [], 100.0)

    def test_non_sequence_coupons_are_rejected(self):
        with self.assertRaises(ValueError):
            evaluate_campaign(
                "coupon-a", flight_article(), self.matrix, self.clean, 100.0
            )


if __name__ == "__main__":
    unittest.main()
