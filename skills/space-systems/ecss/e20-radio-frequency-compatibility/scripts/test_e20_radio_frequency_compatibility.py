#!/usr/bin/env python3
"""Gate 3 contract test: ECSS-E-ST-20C clause 6.3.6 radio frequency
compatibility of antenna-connected equipment.

Exercises scripts/e20_radio_frequency_compatibility_logic.py (stdlib
unittest, offline). Contract: an antenna-connected unit maps to exactly
one role and an unrecognized unit raises; a victim with no receive role
and an emitter with no transmit role are reported; coupled power is the
transmit power less isolation and front-end rejection, with a negative
loss raising; the interference margin is the susceptibility threshold
less the coupled power against a required minimum; intermodulation
products are generated to a chosen order, ordered deterministically,
and screened against the victim receive band with the edges included;
the noise-floor degradation is the decibel rise from the summed
interference against the mission budget; a limit met exactly within
representation error passes; and the aggregated review is compatible
only when every finding list is empty.
"""

import math
import os
import sys
import unittest

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import e20_radio_frequency_compatibility_logic as rf  # noqa: E402


def _quiet_emitters():
    return [
        {
            "emitter_id": "TM-TX-1",
            "equipment_kind": "telemetry_transmitter",
            "frequency_hz": 2245.0e6,
            "transmit_power_dbm": 33.0,
            "isolation_db": 90.0,
            "filter_rejection_db": 60.0,
        },
        {
            "emitter_id": "PL-TX-1",
            "equipment_kind": "payload_downlink_transmitter",
            "frequency_hz": 8200.0e6,
            "transmit_power_dbm": 40.0,
            "isolation_db": 100.0,
            "filter_rejection_db": 60.0,
        },
    ]


def _clean_scenario():
    """A telecommand receiver compatible with both onboard emitters."""
    return {
        "victim_id": "TC-RX-A",
        "victim_kind": "telecommand_receiver",
        "band_low_hz": 2089.0e6,
        "band_high_hz": 2091.0e6,
        "susceptibility_threshold_dbm": -110.0,
        "noise_floor_dbm": -100.0,
        "emitters": _quiet_emitters(),
    }


class TestCategorizeRfEquipment(unittest.TestCase):
    def test_telemetry_unit_is_a_transmitter(self):
        self.assertEqual(
            rf.categorize_rf_equipment("telemetry_transmitter"), "transmitter"
        )

    def test_telecommand_unit_is_a_receiver(self):
        self.assertEqual(
            rf.categorize_rf_equipment("telecommand_receiver"), "receiver"
        )

    def test_transponder_is_a_transceiver(self):
        self.assertEqual(
            rf.categorize_rf_equipment("coherent_transponder"), "transceiver"
        )

    def test_roles_are_disjoint(self):
        self.assertEqual(
            rf.TRANSMIT_ONLY_KINDS & rf.RECEIVE_ONLY_KINDS, frozenset()
        )
        self.assertEqual(
            rf.TRANSMIT_ONLY_KINDS & rf.TRANSCEIVER_KINDS, frozenset()
        )
        self.assertEqual(
            rf.RECEIVE_ONLY_KINDS & rf.TRANSCEIVER_KINDS, frozenset()
        )

    def test_unrecognized_unit_raises(self):
        with self.assertRaises(ValueError):
            rf.categorize_rf_equipment("star_tracker")

    def test_transceiver_can_both_emit_and_receive(self):
        self.assertTrue(rf.can_emit("inter_satellite_link_terminal"))
        self.assertTrue(rf.can_receive("inter_satellite_link_terminal"))

    def test_receiver_cannot_emit(self):
        self.assertFalse(rf.can_emit("radiometer_receiver"))

    def test_transmitter_cannot_receive(self):
        self.assertFalse(rf.can_receive("beacon_transmitter"))


class TestRoleFindings(unittest.TestCase):
    def test_consistent_roles_yield_no_finding(self):
        self.assertEqual(
            rf.role_findings(
                "TC-RX-A", "telecommand_receiver", _quiet_emitters()
            ),
            [],
        )

    def test_victim_without_receive_role_is_flagged(self):
        findings = rf.role_findings(
            "TC-RX-A", "beacon_transmitter", _quiet_emitters()
        )
        self.assertEqual(len(findings), 1)
        self.assertEqual(
            findings[0]["issue"], "victim_unit_has_no_receive_role"
        )

    def test_emitter_without_transmit_role_is_flagged(self):
        emitters = _quiet_emitters()
        emitters[0]["equipment_kind"] = "radiometer_receiver"
        findings = rf.role_findings(
            "TC-RX-A", "telecommand_receiver", emitters
        )
        self.assertEqual(len(findings), 1)
        self.assertEqual(
            findings[0]["issue"], "emitter_unit_has_no_transmit_role"
        )
        self.assertEqual(findings[0]["emitter"], "TM-TX-1")

    def test_unrecognized_emitter_raises(self):
        emitters = _quiet_emitters()
        emitters[1]["equipment_kind"] = "reaction_wheel"
        with self.assertRaises(ValueError):
            rf.role_findings("TC-RX-A", "telecommand_receiver", emitters)


class TestPowerConversion(unittest.TestCase):
    def test_thirty_dbm_is_one_watt(self):
        self.assertAlmostEqual(rf.dbm_to_watt(30.0), 1.0, places=9)

    def test_zero_dbm_is_one_milliwatt(self):
        self.assertAlmostEqual(rf.dbm_to_watt(0.0), 1.0e-3, places=12)

    def test_watt_to_dbm_round_trips(self):
        self.assertAlmostEqual(
            rf.watt_to_dbm(rf.dbm_to_watt(-117.0)), -117.0, places=9
        )

    def test_non_finite_dbm_raises(self):
        with self.assertRaises(ValueError):
            rf.dbm_to_watt(float("inf"))

    def test_zero_watt_has_no_decibel_value(self):
        with self.assertRaises(ValueError):
            rf.watt_to_dbm(0.0)

    def test_two_equal_powers_sum_to_three_decibels_more(self):
        self.assertAlmostEqual(
            rf.combined_interference_dbm([-100.0, -100.0]),
            -100.0 + 10.0 * math.log10(2.0),
            places=9,
        )

    def test_empty_power_list_raises(self):
        with self.assertRaises(ValueError):
            rf.combined_interference_dbm([])


class TestCoupledPower(unittest.TestCase):
    def test_coupled_power_subtracts_both_losses(self):
        self.assertAlmostEqual(
            rf.coupled_power_dbm(33.0, 90.0, 60.0), -117.0, places=9
        )

    def test_zero_losses_pass_the_transmit_power_through(self):
        self.assertAlmostEqual(
            rf.coupled_power_dbm(10.0, 0.0, 0.0), 10.0, places=9
        )

    def test_negative_isolation_raises(self):
        with self.assertRaises(ValueError):
            rf.coupled_power_dbm(33.0, -1.0, 60.0)

    def test_negative_rejection_raises(self):
        with self.assertRaises(ValueError):
            rf.coupled_power_dbm(33.0, 90.0, -1.0)

    def test_non_finite_transmit_power_raises(self):
        with self.assertRaises(ValueError):
            rf.coupled_power_dbm(float("nan"), 90.0, 60.0)

    def test_margin_is_threshold_less_coupled_power(self):
        self.assertAlmostEqual(
            rf.interference_margin_db(-117.0, -110.0), 7.0, places=9
        )

    def test_margin_is_negative_when_the_victim_is_overdriven(self):
        self.assertAlmostEqual(
            rf.interference_margin_db(-100.0, -110.0), -10.0, places=9
        )

    def test_non_finite_threshold_raises(self):
        with self.assertRaises(ValueError):
            rf.interference_margin_db(-117.0, float("inf"))


class TestNoiseFloorDegradation(unittest.TestCase):
    def test_interference_equal_to_noise_adds_three_decibels(self):
        self.assertAlmostEqual(
            rf.noise_floor_degradation_db(-100.0, -100.0),
            10.0 * math.log10(2.0),
            places=9,
        )

    def test_interference_far_below_noise_is_negligible(self):
        self.assertAlmostEqual(
            rf.noise_floor_degradation_db(-100.0, -140.0), 0.0, places=3
        )

    def test_interference_ten_decibels_above_noise(self):
        self.assertAlmostEqual(
            rf.noise_floor_degradation_db(-100.0, -90.0),
            10.0 * math.log10(11.0),
            places=9,
        )

    def test_degradation_grows_with_interference(self):
        low = rf.noise_floor_degradation_db(-100.0, -120.0)
        high = rf.noise_floor_degradation_db(-100.0, -105.0)
        self.assertGreater(high, low)

    def test_non_finite_noise_floor_raises(self):
        with self.assertRaises(ValueError):
            rf.noise_floor_degradation_db(float("nan"), -110.0)


class TestIntermodulationProducts(unittest.TestCase):
    def test_second_order_products_are_sum_and_difference(self):
        products = rf.intermodulation_products_hz(1000.0e6, 1500.0e6, 2)
        self.assertEqual(
            sorted(p["frequency_hz"] for p in products),
            [500.0e6, 2500.0e6],
        )

    def test_fifth_order_generates_twenty_products(self):
        products = rf.intermodulation_products_hz(2245.0e6, 8200.0e6, 5)
        self.assertEqual(len(products), 20)

    def test_zero_difference_is_dropped(self):
        products = rf.intermodulation_products_hz(1000.0e6, 1000.0e6, 5)
        self.assertEqual(len(products), 18)
        for product in products:
            self.assertGreater(product["frequency_hz"], 0.0)

    def test_products_are_sorted_by_frequency(self):
        products = rf.intermodulation_products_hz(1000.0e6, 1500.0e6, 4)
        frequencies = [p["frequency_hz"] for p in products]
        self.assertEqual(frequencies, sorted(frequencies))

    def test_generation_is_deterministic(self):
        first = rf.intermodulation_products_hz(1000.0e6, 1500.0e6, 4)
        second = rf.intermodulation_products_hz(1000.0e6, 1500.0e6, 4)
        self.assertEqual(first, second)

    def test_order_is_the_coefficient_sum(self):
        products = rf.intermodulation_products_hz(1000.0e6, 1500.0e6, 3)
        for product in products:
            self.assertEqual(
                product["order"], sum(product["coefficients"])
            )

    def test_non_positive_frequency_raises(self):
        with self.assertRaises(ValueError):
            rf.intermodulation_products_hz(0.0, 1500.0e6, 3)

    def test_order_below_two_raises(self):
        with self.assertRaises(ValueError):
            rf.intermodulation_products_hz(1000.0e6, 1500.0e6, 1)

    def test_non_integer_order_raises(self):
        with self.assertRaises(ValueError):
            rf.intermodulation_products_hz(1000.0e6, 1500.0e6, 3.5)


class TestProductsInBand(unittest.TestCase):
    def test_product_inside_the_band_is_kept(self):
        products = rf.intermodulation_products_hz(4180.0e6, 2090.0e6, 2)
        inside = rf.products_in_band(products, 2089.0e6, 2091.0e6)
        self.assertEqual(len(inside), 1)
        self.assertAlmostEqual(
            inside[0]["frequency_hz"], 2090.0e6, places=0
        )

    def test_products_outside_the_band_are_dropped(self):
        products = rf.intermodulation_products_hz(2245.0e6, 8200.0e6, 5)
        self.assertEqual(
            rf.products_in_band(products, 2089.0e6, 2091.0e6), []
        )

    def test_band_edge_is_inclusive(self):
        products = [{"frequency_hz": 2089.0e6, "order": 2, "coefficients": (1, 1)}]
        self.assertEqual(
            len(rf.products_in_band(products, 2089.0e6, 2091.0e6)), 1
        )

    def test_edge_product_built_from_sums_is_kept(self):
        # 0.1 + 0.2 lands a few units above 0.3; the same happens to a
        # product sitting on a band edge it physically falls on.
        products = [
            {
                "frequency_hz": (0.1 + 0.2) * 1.0e10,
                "order": 2,
                "coefficients": (1, 1),
            }
        ]
        self.assertEqual(
            len(rf.products_in_band(products, 1.0e9, 0.3 * 1.0e10)), 1
        )

    def test_inverted_band_raises(self):
        with self.assertRaises(ValueError):
            rf.products_in_band([], 2091.0e6, 2089.0e6)

    def test_non_positive_lower_edge_raises(self):
        with self.assertRaises(ValueError):
            rf.products_in_band([], 0.0, 2091.0e6)


class TestIntermodulationFindings(unittest.TestCase):
    def test_clear_band_yields_no_finding(self):
        self.assertEqual(
            rf.intermodulation_findings(
                "TC-RX-A", _quiet_emitters(), 2089.0e6, 2091.0e6, 5
            ),
            [],
        )

    def test_in_band_product_is_flagged_with_its_pair(self):
        emitters = _quiet_emitters()
        emitters[0]["frequency_hz"] = 4180.0e6
        emitters[1]["frequency_hz"] = 2090.0e6
        findings = rf.intermodulation_findings(
            "TC-RX-A", emitters, 2089.0e6, 2091.0e6, 2
        )
        self.assertEqual(len(findings), 1)
        self.assertEqual(
            findings[0]["issue"], "intermodulation_product_in_receive_band"
        )
        self.assertEqual(findings[0]["emitters"], ("TM-TX-1", "PL-TX-1"))
        self.assertEqual(findings[0]["order"], 2)

    def test_single_emitter_has_no_pair(self):
        self.assertEqual(
            rf.intermodulation_findings(
                "TC-RX-A", _quiet_emitters()[:1], 2089.0e6, 2091.0e6, 5
            ),
            [],
        )


class TestCouplingFindings(unittest.TestCase):
    def test_quiet_emitters_yield_no_finding(self):
        self.assertEqual(
            rf.coupling_findings("TC-RX-A", _quiet_emitters(), -110.0, 6.0),
            [],
        )

    def test_loud_emitter_is_flagged(self):
        emitters = _quiet_emitters()
        emitters[0]["isolation_db"] = 30.0
        findings = rf.coupling_findings(
            "TC-RX-A", emitters, -110.0, 6.0
        )
        self.assertEqual(len(findings), 1)
        self.assertEqual(
            findings[0]["issue"], "insufficient_interference_margin"
        )
        self.assertAlmostEqual(findings[0]["coupled_dbm"], -57.0, places=6)

    def test_margin_exactly_at_the_requirement_passes(self):
        emitters = _quiet_emitters()[:1]
        emitters[0]["transmit_power_dbm"] = 33.0
        emitters[0]["isolation_db"] = 90.0
        emitters[0]["filter_rejection_db"] = 60.0
        # coupled = -117 dBm, threshold -110 dBm, margin exactly 7 dB.
        self.assertEqual(
            rf.coupling_findings("TC-RX-A", emitters, -110.0, 7.0), []
        )

    def test_non_positive_required_margin_raises(self):
        with self.assertRaises(ValueError):
            rf.coupling_findings("TC-RX-A", _quiet_emitters(), -110.0, 0.0)

    def test_negative_isolation_raises_through_coupling_findings(self):
        emitters = _quiet_emitters()
        emitters[1]["isolation_db"] = -5.0
        with self.assertRaises(ValueError):
            rf.coupling_findings("TC-RX-A", emitters, -110.0, 6.0)


class TestPerformanceFindings(unittest.TestCase):
    def test_quiet_scenario_meets_the_mission_criterion(self):
        self.assertEqual(
            rf.performance_findings(
                "TC-RX-A", _quiet_emitters(), -100.0, 0.5
            ),
            [],
        )

    def test_loud_scenario_breaks_the_mission_criterion(self):
        emitters = _quiet_emitters()
        emitters[0]["isolation_db"] = 40.0
        findings = rf.performance_findings(
            "TC-RX-A", emitters, -100.0, 0.5
        )
        self.assertEqual(len(findings), 1)
        self.assertEqual(
            findings[0]["issue"], "noise_floor_degradation_above_budget"
        )
        self.assertGreater(findings[0]["degradation_db"], 0.5)

    def test_aggregate_effect_exceeds_any_single_emitter(self):
        emitters = _quiet_emitters()
        single = rf.noise_floor_degradation_db(-100.0, -117.0)
        pair = rf.noise_floor_degradation_db(
            -100.0,
            rf.combined_interference_dbm([-117.0, -120.0]),
        )
        self.assertGreater(pair, single)
        self.assertEqual(
            rf.performance_findings("TC-RX-A", emitters, -100.0, 0.5), []
        )

    def test_empty_emitter_list_raises(self):
        with self.assertRaises(ValueError):
            rf.performance_findings("TC-RX-A", [], -100.0, 0.5)

    def test_non_positive_degradation_budget_raises(self):
        with self.assertRaises(ValueError):
            rf.performance_findings(
                "TC-RX-A", _quiet_emitters(), -100.0, 0.0
            )

    def test_degradation_exactly_at_budget_passes(self):
        emitters = _quiet_emitters()[:1]
        coupled = rf.coupled_power_dbm(
            emitters[0]["transmit_power_dbm"],
            emitters[0]["isolation_db"],
            emitters[0]["filter_rejection_db"],
        )
        budget = rf.noise_floor_degradation_db(-100.0, coupled)
        self.assertEqual(
            rf.performance_findings("TC-RX-A", emitters, -100.0, budget), []
        )


class TestRfCompatibilityReview(unittest.TestCase):
    def test_clean_scenario_is_compatible(self):
        review = rf.rf_compatibility_review(_clean_scenario())
        self.assertTrue(rf.is_rf_compatible(review))

    def test_review_carries_all_four_finding_lists(self):
        review = rf.rf_compatibility_review(_clean_scenario())
        self.assertEqual(
            sorted(review),
            ["coupling", "intermodulation", "performance", "roles"],
        )

    def test_loud_emitter_breaks_compatibility(self):
        scenario = _clean_scenario()
        scenario["emitters"][0]["isolation_db"] = 30.0
        review = rf.rf_compatibility_review(scenario)
        self.assertFalse(rf.is_rf_compatible(review))
        self.assertEqual(len(review["coupling"]), 1)
        self.assertEqual(review["roles"], [])

    def test_in_band_product_breaks_compatibility(self):
        scenario = _clean_scenario()
        scenario["emitters"][0]["frequency_hz"] = 4180.0e6
        scenario["emitters"][1]["frequency_hz"] = 2090.0e6
        scenario["max_product_order"] = 2
        review = rf.rf_compatibility_review(scenario)
        self.assertEqual(len(review["intermodulation"]), 1)
        self.assertEqual(review["coupling"], [])

    def test_wrong_victim_role_breaks_compatibility(self):
        scenario = _clean_scenario()
        scenario["victim_kind"] = "telemetry_transmitter"
        review = rf.rf_compatibility_review(scenario)
        self.assertEqual(len(review["roles"]), 1)
        self.assertFalse(rf.is_rf_compatible(review))

    def test_default_budgets_are_applied_when_absent(self):
        scenario = _clean_scenario()
        review = rf.rf_compatibility_review(scenario)
        self.assertTrue(rf.is_rf_compatible(review))
        self.assertAlmostEqual(rf.DEFAULT_REQUIRED_MARGIN_DB, 6.0, places=9)
        self.assertAlmostEqual(rf.DEFAULT_MAX_DEGRADATION_DB, 0.5, places=9)

    def test_review_does_not_mutate_the_scenario(self):
        scenario = _clean_scenario()
        snapshot = dict(scenario["emitters"][0])
        rf.rf_compatibility_review(scenario)
        self.assertEqual(scenario["emitters"][0], snapshot)

    def test_review_is_deterministic(self):
        first = rf.rf_compatibility_review(_clean_scenario())
        second = rf.rf_compatibility_review(_clean_scenario())
        self.assertEqual(first, second)

    def test_unrecognized_unit_raises_through_review(self):
        scenario = _clean_scenario()
        scenario["victim_kind"] = "magnetometer"
        with self.assertRaises(ValueError):
            rf.rf_compatibility_review(scenario)

    def test_inverted_band_raises_through_review(self):
        scenario = _clean_scenario()
        scenario["band_high_hz"] = 1000.0e6
        with self.assertRaises(ValueError):
            rf.rf_compatibility_review(scenario)


if __name__ == "__main__":
    unittest.main()
