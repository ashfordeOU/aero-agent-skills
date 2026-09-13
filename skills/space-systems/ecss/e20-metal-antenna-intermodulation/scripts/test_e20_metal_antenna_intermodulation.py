#!/usr/bin/env python3
"""Contract test for the metal based antenna intermodulation leaf.

Offline, deterministic, python3 standard library only.
Run: python3 test_e20_metal_antenna_intermodulation.py
"""

import math
import unittest

import e20_metal_antenna_intermodulation_logic as logic


def _carrier_set():
    return [
        {"frequency_hz": 1.8153e9, "power_dbm": 43.0},
        {"frequency_hz": 2.0271e9, "power_dbm": 43.0},
    ]


def _bands(allowance_db=0.5):
    return [
        {
            "label": "service-receive-band",
            "low_hz": 1.60e9,
            "high_hz": 1.61e9,
            "allowed_degradation_db": allowance_db,
        }
    ]


class JunctionCategorization(unittest.TestCase):
    def test_loose_contact_is_high_risk_and_owes_a_control_action(self):
        report = logic.categorize_pim_source("loose-metal-contact")
        self.assertEqual(report["risk"], "high")
        self.assertTrue(report["control_required"])
        self.assertIsNotNone(report["finding"])

    def test_recorded_mitigation_clears_the_finding(self):
        report = logic.categorize_pim_source("loose-metal-contact", True)
        self.assertIsNone(report["finding"])

    def test_welded_joint_is_low_risk_and_owes_nothing(self):
        report = logic.categorize_pim_source("welded-joint")
        self.assertEqual(report["risk"], "low")
        self.assertFalse(report["control_required"])
        self.assertIsNone(report["finding"])

    def test_ferromagnetic_plating_is_high_risk(self):
        self.assertEqual(
            logic.categorize_pim_source("ferromagnetic-plating")["risk"], "high"
        )

    def test_oxidised_surface_is_elevated_risk(self):
        self.assertEqual(
            logic.categorize_pim_source("oxidised-surface")["risk"], "elevated"
        )

    def test_case_and_whitespace_are_normalised(self):
        report = logic.categorize_pim_source("  Brazed-Joint  ")
        self.assertEqual(report["source_type"], "brazed-joint")

    def test_uncategorized_family_is_rejected(self):
        with self.assertRaises(ValueError):
            logic.categorize_pim_source("gold-plated-unicorn-horn")

    def test_empty_source_type_is_rejected(self):
        with self.assertRaises(ValueError):
            logic.categorize_pim_source("   ")

    def test_non_string_source_type_is_rejected(self):
        with self.assertRaises(ValueError):
            logic.categorize_pim_source(17)

    def test_non_boolean_mitigation_flag_is_rejected(self):
        with self.assertRaises(ValueError):
            logic.categorize_pim_source("welded-joint", "yes")


class ProductEnumeration(unittest.TestCase):
    def test_third_order_difference_product_is_present(self):
        products = logic.intermodulation_products([1.8e9, 2.0e9], max_order=3)
        frequencies = [p["frequency_hz"] for p in products]
        self.assertTrue(
            any(math.isclose(f, 1.6e9, rel_tol=1e-12) for f in frequencies)
        )

    def test_third_order_product_carries_order_three(self):
        products = logic.intermodulation_products([1.8e9, 2.0e9], max_order=3)
        hit = [p for p in products if math.isclose(p["frequency_hz"], 1.6e9, rel_tol=1e-12)]
        self.assertEqual(hit[0]["order"], 3)

    def test_every_product_frequency_is_positive(self):
        products = logic.intermodulation_products([1.8e9, 2.0e9], max_order=5)
        self.assertTrue(all(p["frequency_hz"] > 0.0 for p in products))

    def test_products_are_sorted_by_frequency(self):
        products = logic.intermodulation_products([1.8e9, 2.0e9], max_order=5)
        frequencies = [p["frequency_hz"] for p in products]
        self.assertEqual(frequencies, sorted(frequencies))

    def test_raising_the_order_never_removes_products(self):
        low = logic.intermodulation_products([1.8e9, 2.0e9], max_order=3)
        high = logic.intermodulation_products([1.8e9, 2.0e9], max_order=5)
        self.assertGreater(len(high), len(low))

    def test_three_carriers_produce_more_products_than_two(self):
        two = logic.intermodulation_products([1.8e9, 2.0e9], max_order=5)
        three = logic.intermodulation_products([1.8e9, 2.0e9, 2.2e9], max_order=5)
        self.assertGreater(len(three), len(two))

    def test_single_carrier_is_rejected(self):
        with self.assertRaises(ValueError):
            logic.intermodulation_products([1.8e9])

    def test_more_than_six_carriers_is_rejected(self):
        with self.assertRaises(ValueError):
            logic.intermodulation_products([1e9 * k for k in range(1, 9)])

    def test_zero_carrier_frequency_is_rejected(self):
        with self.assertRaises(ValueError):
            logic.intermodulation_products([0.0, 2.0e9])

    def test_negative_carrier_frequency_is_rejected(self):
        with self.assertRaises(ValueError):
            logic.intermodulation_products([-1.8e9, 2.0e9])

    def test_non_sequence_carrier_input_is_rejected(self):
        with self.assertRaises(ValueError):
            logic.intermodulation_products("1.8e9, 2.0e9")

    def test_min_order_below_two_is_rejected(self):
        with self.assertRaises(ValueError):
            logic.intermodulation_products([1.8e9, 2.0e9], max_order=5, min_order=1)

    def test_max_order_below_min_order_is_rejected(self):
        with self.assertRaises(ValueError):
            logic.intermodulation_products([1.8e9, 2.0e9], max_order=2, min_order=3)

    def test_max_order_above_the_supported_ceiling_is_rejected(self):
        with self.assertRaises(ValueError):
            logic.intermodulation_products([1.8e9, 2.0e9], max_order=13)

    def test_non_integer_max_order_is_rejected(self):
        with self.assertRaises(ValueError):
            logic.intermodulation_products([1.8e9, 2.0e9], max_order=5.5)


class BandMembership(unittest.TestCase):
    def test_in_band_product_is_kept_with_its_band_label(self):
        products = logic.intermodulation_products([1.8153e9, 2.0271e9], max_order=3)
        hits = logic.products_in_receive_bands(products, _bands())
        self.assertTrue(hits)
        self.assertEqual(hits[0]["band"], "service-receive-band")

    def test_out_of_band_products_are_dropped(self):
        products = logic.intermodulation_products([1.8e9, 2.0e9], max_order=3)
        bands = [
            {
                "label": "empty-window",
                "low_hz": 9.0e9,
                "high_hz": 9.1e9,
                "allowed_degradation_db": 0.5,
            }
        ]
        self.assertEqual(logic.products_in_receive_bands(products, bands), [])

    def test_band_edge_absorbs_the_rounding_of_a_summed_frequency(self):
        f1, f2 = 1.8153e9, 2.0271e9
        edge = 2.0 * f1 - f2
        products = logic.intermodulation_products([f1, f2], max_order=3)
        bands = [
            {
                "label": "edge-band",
                "low_hz": edge,
                "high_hz": edge + 1.0e6,
                "allowed_degradation_db": 0.5,
            }
        ]
        hits = logic.products_in_receive_bands(products, bands)
        self.assertTrue(any(h["order"] == 3 for h in hits))

    def test_band_with_high_below_low_is_rejected(self):
        with self.assertRaises(ValueError):
            logic.products_in_receive_bands(
                [{"frequency_hz": 1.6e9}],
                [{"label": "bad", "low_hz": 2.0e9, "high_hz": 1.0e9}],
            )

    def test_band_without_a_label_is_rejected(self):
        with self.assertRaises(ValueError):
            logic.products_in_receive_bands(
                [{"frequency_hz": 1.6e9}],
                [{"low_hz": 1.0e9, "high_hz": 2.0e9}],
            )

    def test_empty_band_list_is_rejected(self):
        with self.assertRaises(ValueError):
            logic.products_in_receive_bands([{"frequency_hz": 1.6e9}], [])

    def test_product_without_a_frequency_is_rejected(self):
        with self.assertRaises(ValueError):
            logic.products_in_receive_bands([{"order": 3}], _bands())


class ProductLevelScaling(unittest.TestCase):
    def test_equal_tones_reduce_to_the_order_times_delta_law(self):
        level = logic.intermodulation_product_power_dbm(
            (2, -1), [46.0, 46.0], 43.0, -120.0
        )
        self.assertAlmostEqual(level, -120.0 + 3 * 3.0, places=9)

    def test_at_the_reference_the_measured_level_is_returned(self):
        level = logic.intermodulation_product_power_dbm(
            (2, -1), [43.0, 43.0], 43.0, -120.0
        )
        self.assertAlmostEqual(level, -120.0, places=9)

    def test_unequal_tones_weight_each_carrier_by_its_coefficient(self):
        level = logic.intermodulation_product_power_dbm(
            (2, -1), [45.0, 43.0], 43.0, -120.0
        )
        self.assertAlmostEqual(level, -116.0, places=9)

    def test_dropping_tone_power_lowers_the_product(self):
        level = logic.intermodulation_product_power_dbm(
            (2, -1), [40.0, 40.0], 43.0, -120.0
        )
        self.assertAlmostEqual(level, -129.0, places=9)

    def test_length_mismatch_is_rejected(self):
        with self.assertRaises(ValueError):
            logic.intermodulation_product_power_dbm((2, -1), [43.0], 43.0, -120.0)

    def test_empty_coefficients_are_rejected(self):
        with self.assertRaises(ValueError):
            logic.intermodulation_product_power_dbm((), [], 43.0, -120.0)

    def test_non_integer_coefficient_is_rejected(self):
        with self.assertRaises(ValueError):
            logic.intermodulation_product_power_dbm((2.0, -1), [43.0, 43.0], 43.0, -120.0)

    def test_first_order_combination_is_rejected(self):
        with self.assertRaises(ValueError):
            logic.intermodulation_product_power_dbm((1, 0), [43.0, 43.0], 43.0, -120.0)

    def test_non_finite_carrier_power_is_rejected(self):
        with self.assertRaises(ValueError):
            logic.intermodulation_product_power_dbm(
                (2, -1), [float("inf"), 43.0], 43.0, -120.0
            )


class NoiseFloorAndDegradation(unittest.TestCase):
    def test_one_hertz_noiseless_floor_matches_the_thermal_density(self):
        floor = logic.receiver_noise_floor_dbm(1.0, 0.0)
        self.assertAlmostEqual(floor, -173.975, places=3)

    def test_bandwidth_decade_raises_the_floor_by_ten_decibels(self):
        narrow = logic.receiver_noise_floor_dbm(1.0e6, 3.0)
        wide = logic.receiver_noise_floor_dbm(1.0e7, 3.0)
        self.assertAlmostEqual(wide - narrow, 10.0, places=9)

    def test_noise_figure_adds_directly_to_the_floor(self):
        base = logic.receiver_noise_floor_dbm(1.0e6, 0.0)
        noisy = logic.receiver_noise_floor_dbm(1.0e6, 4.5)
        self.assertAlmostEqual(noisy - base, 4.5, places=9)

    def test_zero_bandwidth_is_rejected(self):
        with self.assertRaises(ValueError):
            logic.receiver_noise_floor_dbm(0.0, 3.0)

    def test_negative_noise_figure_is_rejected(self):
        with self.assertRaises(ValueError):
            logic.receiver_noise_floor_dbm(1.0e6, -1.0)

    def test_zero_noise_temperature_is_rejected(self):
        with self.assertRaises(ValueError):
            logic.receiver_noise_floor_dbm(1.0e6, 3.0, 0.0)

    def test_interferer_at_the_floor_costs_three_decibels(self):
        self.assertAlmostEqual(
            logic.noise_floor_degradation_db(-110.0, -110.0), 3.0103, places=4
        )

    def test_interferer_far_below_the_floor_is_negligible(self):
        self.assertLess(logic.noise_floor_degradation_db(-150.0, -110.0), 0.001)

    def test_interferer_ten_decibels_above_the_floor_costs_ten_point_four(self):
        self.assertAlmostEqual(
            logic.noise_floor_degradation_db(-100.0, -110.0), 10.4139, places=4
        )

    def test_two_equal_levels_combine_three_decibels_higher(self):
        self.assertAlmostEqual(
            logic.combine_powers_dbm([-120.0, -120.0]), -116.9897, places=4
        )

    def test_one_level_combines_to_itself(self):
        self.assertAlmostEqual(logic.combine_powers_dbm([-120.0]), -120.0, places=9)

    def test_empty_level_list_is_rejected(self):
        with self.assertRaises(ValueError):
            logic.combine_powers_dbm([])


class WholeAssessment(unittest.TestCase):
    def _run(self, allowance_db=0.5, reference_pim_dbm=-140.0, junctions=None):
        return logic.assess_metal_antenna_pim(
            carriers=_carrier_set(),
            receive_bands=_bands(allowance_db),
            junctions=junctions if junctions is not None else [
                {"source_type": "welded-joint"}
            ],
            reference_pim_dbm=reference_pim_dbm,
            reference_carrier_power_dbm=43.0,
            transmit_to_receive_isolation_db=20.0,
            receiver_bandwidth_hz=2.0e6,
            receiver_noise_figure_db=3.0,
            max_order=3,
        )

    def test_a_quiet_antenna_is_compliant(self):
        result = self._run(reference_pim_dbm=-160.0)
        self.assertTrue(result["compliant"])
        self.assertEqual(result["findings"], [])

    def test_a_noisy_junction_level_breaks_the_band_allowance(self):
        result = self._run(reference_pim_dbm=-80.0)
        self.assertFalse(result["compliant"])
        self.assertTrue(any("degrades by" in f for f in result["findings"]))

    def test_the_critical_product_is_reported_with_its_band(self):
        result = self._run(reference_pim_dbm=-120.0)
        self.assertTrue(result["critical_products"])
        self.assertEqual(
            result["critical_products"][0]["band"], "service-receive-band"
        )

    def test_isolation_is_subtracted_from_the_junction_level(self):
        result = self._run(reference_pim_dbm=-120.0)
        entry = result["critical_products"][0]
        self.assertAlmostEqual(
            entry["pim_at_junction_dbm"] - entry["pim_at_receiver_dbm"], 20.0, places=9
        )

    def test_an_uncontrolled_high_risk_junction_is_a_finding(self):
        result = self._run(
            reference_pim_dbm=-160.0,
            junctions=[{"source_type": "loose-metal-contact"}],
        )
        self.assertFalse(result["compliant"])
        self.assertTrue(any("control action" in f for f in result["findings"]))

    def test_a_mitigated_high_risk_junction_is_not_a_finding(self):
        result = self._run(
            reference_pim_dbm=-160.0,
            junctions=[
                {"source_type": "loose-metal-contact", "mitigation_on_record": True}
            ],
        )
        self.assertTrue(result["compliant"])

    def test_an_allowance_a_hair_under_the_computed_value_still_passes(self):
        loud = self._run(reference_pim_dbm=-90.0)
        degradation = loud["bands"][0]["degradation_db"]
        tight = self._run(reference_pim_dbm=-90.0, allowance_db=degradation - 1e-12)
        self.assertTrue(tight["bands"][0]["compliant"])

    def test_an_allowance_half_a_decibel_under_fails(self):
        loud = self._run(reference_pim_dbm=-90.0)
        degradation = loud["bands"][0]["degradation_db"]
        self.assertGreater(degradation, 0.6)
        tight = self._run(reference_pim_dbm=-90.0, allowance_db=degradation - 0.5)
        self.assertFalse(tight["bands"][0]["compliant"])

    def test_band_combination_is_at_least_as_loud_as_any_single_product(self):
        result = self._run(reference_pim_dbm=-120.0)
        loudest = max(e["pim_at_receiver_dbm"] for e in result["critical_products"])
        self.assertGreaterEqual(
            result["bands"][0]["combined_pim_at_receiver_dbm"] + 1e-9, loudest
        )

    def test_a_single_carrier_assessment_is_rejected(self):
        with self.assertRaises(ValueError):
            logic.assess_metal_antenna_pim(
                carriers=[{"frequency_hz": 1.8e9, "power_dbm": 43.0}],
                receive_bands=_bands(),
                junctions=[],
                reference_pim_dbm=-140.0,
                reference_carrier_power_dbm=43.0,
                transmit_to_receive_isolation_db=20.0,
                receiver_bandwidth_hz=2.0e6,
                receiver_noise_figure_db=3.0,
            )

    def test_negative_isolation_is_rejected(self):
        with self.assertRaises(ValueError):
            logic.assess_metal_antenna_pim(
                carriers=_carrier_set(),
                receive_bands=_bands(),
                junctions=[],
                reference_pim_dbm=-140.0,
                reference_carrier_power_dbm=43.0,
                transmit_to_receive_isolation_db=-5.0,
                receiver_bandwidth_hz=2.0e6,
                receiver_noise_figure_db=3.0,
            )

    def test_a_band_without_an_allowance_is_rejected(self):
        bands = [{"label": "no-allowance", "low_hz": 1.60e9, "high_hz": 1.61e9}]
        with self.assertRaises(ValueError):
            logic.assess_metal_antenna_pim(
                carriers=_carrier_set(),
                receive_bands=bands,
                junctions=[],
                reference_pim_dbm=-140.0,
                reference_carrier_power_dbm=43.0,
                transmit_to_receive_isolation_db=20.0,
                receiver_bandwidth_hz=2.0e6,
                receiver_noise_figure_db=3.0,
            )

    def test_a_carrier_that_is_not_a_mapping_is_rejected(self):
        with self.assertRaises(ValueError):
            logic.assess_metal_antenna_pim(
                carriers=[1.8e9, 2.0e9],
                receive_bands=_bands(),
                junctions=[],
                reference_pim_dbm=-140.0,
                reference_carrier_power_dbm=43.0,
                transmit_to_receive_isolation_db=20.0,
                receiver_bandwidth_hz=2.0e6,
                receiver_noise_figure_db=3.0,
            )

    def test_a_junction_entry_that_is_not_a_mapping_is_rejected(self):
        with self.assertRaises(ValueError):
            logic.assess_metal_antenna_pim(
                carriers=_carrier_set(),
                receive_bands=_bands(),
                junctions=["welded-joint"],
                reference_pim_dbm=-140.0,
                reference_carrier_power_dbm=43.0,
                transmit_to_receive_isolation_db=20.0,
                receiver_bandwidth_hz=2.0e6,
                receiver_noise_figure_db=3.0,
            )


if __name__ == "__main__":
    unittest.main()
