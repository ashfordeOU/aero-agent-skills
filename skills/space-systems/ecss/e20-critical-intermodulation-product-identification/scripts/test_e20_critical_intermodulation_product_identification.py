#!/usr/bin/env python3
"""Gate 3 contract test -- ECSS-E-ST-20C clause 7.4.3 critical products."""

import unittest

import e20_critical_intermodulation_product_identification_logic as logic

CARRIERS = [1.80e9, 1.83e9]
# Third-order products of the pair: 2*f1 - f2 and 2*f2 - f1.
LOW_PRODUCT_HZ = 2 * CARRIERS[0] - CARRIERS[1]   # 1.770 GHz
HIGH_PRODUCT_HZ = 2 * CARRIERS[1] - CARRIERS[0]  # 1.860 GHz


def band(**overrides):
    record = {
        "name": "rx-low",
        "kind": "receive",
        "f_low_hz": 1.7695e9,
        "f_high_hz": 1.7705e9,
        "guard_hz": 0.0,
    }
    record.update(overrides)
    return record


class TestCarrierValidation(unittest.TestCase):
    def test_valid_carrier_list_is_normalised(self):
        self.assertEqual(logic.validate_carrier_frequencies(CARRIERS), CARRIERS)

    def test_integer_frequencies_become_floats(self):
        self.assertEqual(
            logic.validate_carrier_frequencies([1800000000, 1830000000]), CARRIERS
        )

    def test_non_list_carrier_input_is_rejected(self):
        with self.assertRaises(ValueError):
            logic.validate_carrier_frequencies(1.8e9)

    def test_single_carrier_is_rejected(self):
        with self.assertRaises(ValueError):
            logic.validate_carrier_frequencies([1.8e9])

    def test_too_many_carriers_are_rejected(self):
        with self.assertRaises(ValueError):
            logic.validate_carrier_frequencies([1.0e9 + i * 1e6 for i in range(9)])

    def test_duplicate_carrier_frequencies_are_rejected(self):
        with self.assertRaises(ValueError):
            logic.validate_carrier_frequencies([1.8e9, 1.8e9])

    def test_non_positive_carrier_frequency_is_rejected(self):
        with self.assertRaises(ValueError):
            logic.validate_carrier_frequencies([0.0, 1.83e9])

    def test_non_numeric_carrier_frequency_is_rejected(self):
        with self.assertRaises(ValueError):
            logic.validate_carrier_frequencies(["1.8e9", 1.83e9])


class TestCoefficientArithmetic(unittest.TestCase):
    def test_order_is_the_absolute_coefficient_sum(self):
        self.assertEqual(logic.intermodulation_order((2, -1)), 3)

    def test_order_of_a_seventh_order_set(self):
        self.assertEqual(logic.intermodulation_order((4, -3)), 7)

    def test_signed_sum_marks_a_near_carrier_product(self):
        self.assertEqual(logic.signed_coefficient_sum((2, -1)), 1)

    def test_signed_sum_of_a_harmonic_region_product(self):
        self.assertEqual(logic.signed_coefficient_sum((2, 1)), 3)

    def test_empty_coefficient_set_is_rejected(self):
        with self.assertRaises(ValueError):
            logic.intermodulation_order(())

    def test_float_coefficient_is_rejected(self):
        with self.assertRaises(ValueError):
            logic.intermodulation_order((2.0, -1))

    def test_boolean_coefficient_is_rejected(self):
        with self.assertRaises(ValueError):
            logic.intermodulation_order((True, -1))

    def test_product_frequency_of_the_low_third_order_line(self):
        self.assertAlmostEqual(
            logic.product_frequency_hz(CARRIERS, (2, -1)), LOW_PRODUCT_HZ, places=3
        )

    def test_product_frequency_of_the_high_third_order_line(self):
        self.assertAlmostEqual(
            logic.product_frequency_hz(CARRIERS, (-1, 2)), HIGH_PRODUCT_HZ, places=3
        )

    def test_coefficient_count_must_match_carrier_count(self):
        with self.assertRaises(ValueError):
            logic.product_frequency_hz(CARRIERS, (2, -1, 1))


class TestMirrorResolution(unittest.TestCase):
    def test_mirror_flips_every_coefficient(self):
        self.assertEqual(logic.mirror_coefficients((2, -1)), (-2, 1))

    def test_mirror_of_the_mirror_is_the_original(self):
        self.assertEqual(
            logic.mirror_coefficients(logic.mirror_coefficients((3, -2))), (3, -2)
        )

    def test_exactly_one_member_of_a_mirror_pair_is_physical(self):
        first = logic.is_physical_product(CARRIERS, (2, -1))
        second = logic.is_physical_product(CARRIERS, (-2, 1))
        self.assertTrue(first)
        self.assertFalse(second)

    def test_the_physical_member_can_be_the_negative_first_coefficient_one(self):
        self.assertTrue(logic.is_physical_product(CARRIERS, (-1, 2)))
        self.assertFalse(logic.is_physical_product(CARRIERS, (1, -2)))

    def test_direct_current_beat_is_not_physical(self):
        self.assertFalse(logic.is_physical_product([1.0e9, 2.0e9], (2, -1)))

    def test_mirror_of_a_direct_current_beat_is_not_physical_either(self):
        self.assertFalse(logic.is_physical_product([1.0e9, 2.0e9], (-2, 1)))


class TestLatticeCount(unittest.TestCase):
    def test_two_carriers_to_third_order(self):
        self.assertEqual(logic.lattice_point_count(2, 3), 25)

    def test_two_carriers_to_fifth_order(self):
        self.assertEqual(logic.lattice_point_count(2, 5), 61)

    def test_three_carriers_to_fifth_order(self):
        self.assertEqual(logic.lattice_point_count(3, 5), 231)

    def test_zero_order_is_the_single_origin_point(self):
        self.assertEqual(logic.lattice_point_count(3, 0), 1)

    def test_negative_order_is_rejected(self):
        with self.assertRaises(ValueError):
            logic.lattice_point_count(2, -1)

    def test_non_integer_carrier_count_is_rejected(self):
        with self.assertRaises(ValueError):
            logic.lattice_point_count(2.0, 3)


class TestEnumeration(unittest.TestCase):
    def test_third_order_pair_enumeration_is_complete(self):
        sets = logic.enumerate_coefficient_sets(2, 3)
        self.assertIn((2, -1), sets)
        self.assertIn((-1, 2), sets)
        self.assertEqual(len(sets), 12)

    def test_both_members_of_each_mirror_pair_are_present(self):
        sets = logic.enumerate_coefficient_sets(2, 3)
        for coeffs in sets:
            self.assertIn(logic.mirror_coefficients(coeffs), sets)

    def test_every_set_respects_the_order_window(self):
        for coeffs in logic.enumerate_coefficient_sets(2, 5):
            self.assertGreaterEqual(logic.intermodulation_order(coeffs), 3)
            self.assertLessEqual(logic.intermodulation_order(coeffs), 5)

    def test_odd_order_only_excludes_the_even_orders(self):
        for coeffs in logic.enumerate_coefficient_sets(2, 5):
            self.assertEqual(logic.intermodulation_order(coeffs) % 2, 1)

    def test_all_orders_mode_includes_an_even_order_set(self):
        sets = logic.enumerate_coefficient_sets(2, 4, odd_order_only=False)
        self.assertIn((2, -2), sets)

    def test_enumeration_is_sorted_by_order(self):
        orders = [
            logic.intermodulation_order(c) for c in logic.enumerate_coefficient_sets(2, 7)
        ]
        self.assertEqual(orders, sorted(orders))

    def test_enumeration_is_deterministic(self):
        self.assertEqual(
            logic.enumerate_coefficient_sets(3, 5), logic.enumerate_coefficient_sets(3, 5)
        )

    def test_minimum_order_below_three_is_rejected(self):
        with self.assertRaises(ValueError):
            logic.enumerate_coefficient_sets(2, 5, min_order=2)

    def test_maximum_order_above_the_supported_bound_is_rejected(self):
        with self.assertRaises(ValueError):
            logic.enumerate_coefficient_sets(2, logic.MAX_SUPPORTED_ORDER + 1)

    def test_maximum_order_below_minimum_order_is_rejected(self):
        with self.assertRaises(ValueError):
            logic.enumerate_coefficient_sets(2, 3, min_order=5)

    def test_non_integer_maximum_order_is_rejected(self):
        with self.assertRaises(ValueError):
            logic.enumerate_coefficient_sets(2, 5.0)

    def test_carrier_count_outside_the_supported_range_is_rejected(self):
        with self.assertRaises(ValueError):
            logic.enumerate_coefficient_sets(1, 5)

    def test_explosive_search_is_refused_not_truncated(self):
        with self.assertRaises(ValueError):
            logic.enumerate_coefficient_sets(8, 15)


class TestBandChecks(unittest.TestCase):
    def test_valid_band_is_widened_by_its_guard(self):
        record = logic.validate_victim_band(band(guard_hz=1e6))
        self.assertAlmostEqual(record["widened_low_hz"], 1.7685e9, places=3)
        self.assertAlmostEqual(record["widened_high_hz"], 1.7715e9, places=3)

    def test_protected_band_kind_is_accepted(self):
        self.assertEqual(logic.validate_victim_band(band(kind="protected"))["kind"], "protected")

    def test_unknown_band_kind_is_rejected(self):
        with self.assertRaises(ValueError):
            logic.validate_victim_band(band(kind="downlink"))

    def test_inverted_band_edges_are_rejected(self):
        with self.assertRaises(ValueError):
            logic.validate_victim_band(band(f_low_hz=1.78e9, f_high_hz=1.77e9))

    def test_non_positive_lower_edge_is_rejected(self):
        with self.assertRaises(ValueError):
            logic.validate_victim_band(band(f_low_hz=0.0))

    def test_negative_guard_band_is_rejected(self):
        with self.assertRaises(ValueError):
            logic.validate_victim_band(band(guard_hz=-1.0))

    def test_missing_band_name_is_rejected(self):
        record = band()
        del record["name"]
        with self.assertRaises(ValueError):
            logic.validate_victim_band(record)

    def test_non_mapping_band_is_rejected(self):
        with self.assertRaises(ValueError):
            logic.validate_victim_band(("rx-low", 1.77e9))

    def test_product_inside_the_band_is_a_hit(self):
        self.assertTrue(logic.band_hit(LOW_PRODUCT_HZ, band()))

    def test_product_exactly_on_the_lower_edge_is_a_hit(self):
        self.assertTrue(logic.band_hit(LOW_PRODUCT_HZ, band(f_low_hz=LOW_PRODUCT_HZ)))

    def test_product_exactly_on_the_widened_edge_is_a_hit(self):
        edge_band = band(f_low_hz=LOW_PRODUCT_HZ + 1e6, f_high_hz=1.78e9, guard_hz=1e6)
        self.assertTrue(logic.band_hit(LOW_PRODUCT_HZ, edge_band))

    def test_product_outside_the_band_is_not_a_hit(self):
        self.assertFalse(logic.band_hit(HIGH_PRODUCT_HZ, band()))

    def test_margin_is_zero_inside_the_band(self):
        self.assertAlmostEqual(logic.frequency_margin_hz(LOW_PRODUCT_HZ, band()), 0.0, places=6)

    def test_margin_is_the_distance_to_the_nearest_edge(self):
        self.assertAlmostEqual(
            logic.frequency_margin_hz(1.7605e9, band()), 9.0e6, places=0
        )

    def test_margin_above_the_band_is_positive(self):
        self.assertAlmostEqual(
            logic.frequency_margin_hz(1.7805e9, band()), 10.0e6, places=0
        )

    def test_guard_band_shrinks_the_reported_margin(self):
        self.assertAlmostEqual(
            logic.frequency_margin_hz(1.7605e9, band(guard_hz=1e6)), 8.0e6, places=0
        )


class TestScreening(unittest.TestCase):
    def test_both_third_order_lines_are_found(self):
        bands = [
            band(),
            band(name="rx-high", kind="protected", f_low_hz=1.8595e9, f_high_hz=1.8605e9),
        ]
        hits = logic.screen_intermodulation_products(CARRIERS, bands, 7)
        found = {h["band"]: h for h in hits}
        self.assertEqual(set(found), {"rx-low", "rx-high"})
        self.assertEqual(found["rx-low"]["coefficients"], (2, -1))
        self.assertEqual(found["rx-high"]["coefficients"], (-1, 2))

    def test_every_hit_carries_its_order_and_signed_sum(self):
        hits = logic.screen_intermodulation_products(CARRIERS, [band()], 7)
        self.assertEqual(hits[0]["order"], 3)
        self.assertEqual(hits[0]["signed_sum"], 1)
        self.assertTrue(hits[0]["near_carrier"])

    def test_a_band_clear_of_every_product_reports_no_hit(self):
        clear = band(name="rx-clear", f_low_hz=1.20e9, f_high_hz=1.21e9)
        self.assertEqual(logic.screen_intermodulation_products(CARRIERS, [clear], 9), [])

    def test_fifth_order_line_is_found_when_the_third_order_one_misses(self):
        fifth = 3 * CARRIERS[0] - 2 * CARRIERS[1]
        target = band(name="rx-fifth", f_low_hz=fifth - 5e5, f_high_hz=fifth + 5e5)
        hits = logic.screen_intermodulation_products(CARRIERS, [target], 7)
        self.assertEqual(len(hits), 1)
        self.assertEqual(hits[0]["order"], 5)
        self.assertEqual(hits[0]["coefficients"], (3, -2))

    def test_guard_band_turns_a_near_miss_into_a_hit(self):
        near = band(name="rx-near", f_low_hz=LOW_PRODUCT_HZ + 2e6, f_high_hz=1.78e9)
        self.assertEqual(logic.screen_intermodulation_products(CARRIERS, [near], 7), [])
        near["guard_hz"] = 3e6
        self.assertEqual(len(logic.screen_intermodulation_products(CARRIERS, [near], 7)), 1)

    def test_hits_are_ranked_by_order(self):
        fifth = 3 * CARRIERS[0] - 2 * CARRIERS[1]
        wide = band(name="rx-wide", f_low_hz=fifth - 1e6, f_high_hz=LOW_PRODUCT_HZ + 1e6)
        hits = logic.screen_intermodulation_products(CARRIERS, [wide], 9)
        orders = [h["order"] for h in hits]
        self.assertEqual(orders, sorted(orders))
        self.assertEqual(orders[0], 3)

    def test_even_order_product_is_found_only_in_all_orders_mode(self):
        fourth = 2 * CARRIERS[1] - 2 * CARRIERS[0]
        target = band(name="rx-even", f_low_hz=fourth - 1e6, f_high_hz=fourth + 1e6)
        self.assertEqual(logic.screen_intermodulation_products(CARRIERS, [target], 5), [])
        hits = logic.screen_intermodulation_products(
            CARRIERS, [target], 5, odd_order_only=False
        )
        self.assertEqual(hits[0]["order"], 4)
        self.assertFalse(hits[0]["near_carrier"])

    def test_three_carrier_plan_is_screened(self):
        carriers = [1.80e9, 1.83e9, 1.86e9]
        product = carriers[0] + carriers[1] - carriers[2]
        target = band(name="rx-triple", f_low_hz=product - 1e6, f_high_hz=product + 1e6)
        hits = logic.screen_intermodulation_products(carriers, [target], 5)
        self.assertTrue(hits)
        self.assertEqual(hits[0]["order"], 3)

    def test_empty_band_list_is_rejected(self):
        with self.assertRaises(ValueError):
            logic.screen_intermodulation_products(CARRIERS, [], 7)

    def test_duplicate_band_names_are_rejected(self):
        with self.assertRaises(ValueError):
            logic.screen_intermodulation_products(CARRIERS, [band(), band()], 7)

    def test_invalid_carrier_plan_is_rejected(self):
        with self.assertRaises(ValueError):
            logic.screen_intermodulation_products([1.8e9], [band()], 7)


class TestLowestOrderAndSummary(unittest.TestCase):
    def test_lowest_order_of_an_empty_hit_list_is_none(self):
        self.assertIsNone(logic.lowest_critical_order([]))

    def test_lowest_order_can_be_taken_per_band(self):
        fifth = 3 * CARRIERS[0] - 2 * CARRIERS[1]
        bands = [
            band(),
            band(name="rx-fifth", f_low_hz=fifth - 5e5, f_high_hz=fifth + 5e5),
        ]
        hits = logic.screen_intermodulation_products(CARRIERS, bands, 7)
        self.assertEqual(logic.lowest_critical_order(hits, "rx-low"), 3)
        self.assertEqual(logic.lowest_critical_order(hits, "rx-fifth"), 5)
        self.assertEqual(logic.lowest_critical_order(hits), 3)

    def test_unknown_band_name_has_no_lowest_order(self):
        hits = logic.screen_intermodulation_products(CARRIERS, [band()], 7)
        self.assertIsNone(logic.lowest_critical_order(hits, "rx-absent"))

    def test_summary_reports_the_driver_order_and_per_band_counts(self):
        bands = [
            band(),
            band(name="rx-clear", f_low_hz=1.20e9, f_high_hz=1.21e9),
        ]
        summary = logic.summarize_screening(CARRIERS, bands, 7)
        self.assertTrue(summary["critical"])
        self.assertEqual(summary["lowest_critical_order"], 3)
        self.assertEqual(summary["carrier_count"], 2)
        self.assertEqual(summary["bands"][0]["hit_count"], 1)
        self.assertTrue(summary["bands"][0]["critical"])
        self.assertEqual(summary["bands"][1]["hit_count"], 0)
        self.assertFalse(summary["bands"][1]["critical"])
        self.assertIsNone(summary["bands"][1]["lowest_order"])

    def test_summary_limits_the_reported_critical_set(self):
        wide = band(name="rx-wide", f_low_hz=1.60e9, f_high_hz=2.00e9)
        summary = logic.summarize_screening(CARRIERS, [wide], 11)
        self.assertGreater(summary["bands"][0]["hit_count"], 5)
        self.assertEqual(len(summary["bands"][0]["critical_products"]), 5)

    def test_summary_of_a_clear_system_is_not_critical(self):
        clear = band(name="rx-clear", f_low_hz=1.20e9, f_high_hz=1.21e9)
        summary = logic.summarize_screening(CARRIERS, [clear], 9)
        self.assertFalse(summary["critical"])
        self.assertIsNone(summary["lowest_critical_order"])


if __name__ == "__main__":
    unittest.main()
