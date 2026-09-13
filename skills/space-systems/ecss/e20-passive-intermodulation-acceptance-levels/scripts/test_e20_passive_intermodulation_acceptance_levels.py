#!/usr/bin/env python3
"""Gate 3 contract test -- ECSS-E-ST-20C clause 7.4.2 acceptance levels."""

import math
import unittest

import e20_passive_intermodulation_acceptance_levels_logic as logic

HALF_POWER_DB = 10.0 * math.log10(2.0)


def victim_band(**overrides):
    band = {
        "name": "rx-l-band",
        "f_low_hz": 1.5e9,
        "f_high_hz": 1.56e9,
        "noise_floor_dbm": -128.0,
        "allowed_inr_db": -6.0,
        "isolation_db": 85.0,
    }
    band.update(overrides)
    return band


def carrier_plan(**overrides):
    plan = {
        "carrier_frequencies_hz": [1.80e9, 1.83e9],
        "carrier_powers_dbm": [40.0, 40.0],
    }
    plan.update(overrides)
    return plan


class TestPowerConversions(unittest.TestCase):
    def test_dbm_to_mw_zero_dbm_is_one_milliwatt(self):
        self.assertAlmostEqual(logic.dbm_to_mw(0.0), 1.0, places=12)

    def test_dbm_to_mw_thirty_dbm_is_one_watt(self):
        self.assertAlmostEqual(logic.dbm_to_mw(30.0), 1000.0, places=9)

    def test_mw_to_dbm_round_trip(self):
        self.assertAlmostEqual(logic.mw_to_dbm(logic.dbm_to_mw(-54.25)), -54.25, places=10)

    def test_mw_to_dbm_rejects_zero_power(self):
        with self.assertRaises(ValueError):
            logic.mw_to_dbm(0.0)

    def test_mw_to_dbm_rejects_negative_power(self):
        with self.assertRaises(ValueError):
            logic.mw_to_dbm(-1.0)

    def test_dbm_to_mw_rejects_non_numeric(self):
        with self.assertRaises(ValueError):
            logic.dbm_to_mw("-54")

    def test_dbm_to_mw_rejects_nan(self):
        with self.assertRaises(ValueError):
            logic.dbm_to_mw(float("nan"))

    def test_power_sum_of_two_equal_levels_adds_three_db(self):
        self.assertAlmostEqual(
            logic.power_sum_dbm([-60.0, -60.0]), -60.0 + HALF_POWER_DB, places=10
        )

    def test_power_sum_of_single_level_is_that_level(self):
        self.assertAlmostEqual(logic.power_sum_dbm([-71.5]), -71.5, places=10)

    def test_power_sum_dominated_by_strongest_contribution(self):
        self.assertAlmostEqual(logic.power_sum_dbm([-60.0, -90.0]), -59.99566, places=4)

    def test_power_sum_rejects_empty_sequence(self):
        with self.assertRaises(ValueError):
            logic.power_sum_dbm([])

    def test_power_sum_rejects_non_numeric_entry(self):
        with self.assertRaises(ValueError):
            logic.power_sum_dbm([-60.0, None])


class TestTolerableInterference(unittest.TestCase):
    def test_tolerable_level_is_noise_floor_plus_allowance(self):
        self.assertAlmostEqual(
            logic.tolerable_interference_dbm(-128.0, -6.0), -134.0, places=10
        )

    def test_zero_allowance_is_accepted_at_the_boundary(self):
        self.assertAlmostEqual(
            logic.tolerable_interference_dbm(-120.0, 0.0), -120.0, places=10
        )

    def test_positive_allowance_is_rejected(self):
        with self.assertRaises(ValueError):
            logic.tolerable_interference_dbm(-128.0, 1.0)

    def test_implausibly_deep_allowance_is_rejected(self):
        with self.assertRaises(ValueError):
            logic.tolerable_interference_dbm(-128.0, -61.0)

    def test_deepest_credible_allowance_is_accepted(self):
        self.assertAlmostEqual(
            logic.tolerable_interference_dbm(-128.0, -60.0), -188.0, places=10
        )

    def test_non_finite_noise_floor_is_rejected(self):
        with self.assertRaises(ValueError):
            logic.tolerable_interference_dbm(float("inf"), -6.0)


class TestReferencePlaneTransfer(unittest.TestCase):
    def test_acceptance_level_adds_isolation_and_removes_uncertainty_and_margin(self):
        self.assertAlmostEqual(
            logic.acceptance_level_dbm(-134.0, 85.0, 2.0, 3.0), -54.0, places=10
        )

    def test_zero_uncertainty_and_margin_leave_the_isolated_level(self):
        self.assertAlmostEqual(
            logic.acceptance_level_dbm(-134.0, 85.0, 0.0, 0.0), -49.0, places=10
        )

    def test_negative_isolation_is_rejected(self):
        with self.assertRaises(ValueError):
            logic.acceptance_level_dbm(-134.0, -1.0, 2.0, 3.0)

    def test_negative_measurement_uncertainty_is_rejected(self):
        with self.assertRaises(ValueError):
            logic.acceptance_level_dbm(-134.0, 85.0, -2.0, 3.0)

    def test_negative_design_margin_is_rejected(self):
        with self.assertRaises(ValueError):
            logic.acceptance_level_dbm(-134.0, 85.0, 2.0, -3.0)


class TestVictimBandValidation(unittest.TestCase):
    def test_valid_band_is_normalised(self):
        record = logic.validate_victim_band(victim_band())
        self.assertEqual(record["name"], "rx-l-band")
        self.assertAlmostEqual(record["isolation_db"], 85.0, places=10)

    def test_non_mapping_band_is_rejected(self):
        with self.assertRaises(ValueError):
            logic.validate_victim_band(["rx-l-band"])

    def test_missing_name_is_rejected(self):
        band = victim_band()
        del band["name"]
        with self.assertRaises(ValueError):
            logic.validate_victim_band(band)

    def test_blank_name_is_rejected(self):
        with self.assertRaises(ValueError):
            logic.validate_victim_band(victim_band(name="   "))

    def test_non_positive_lower_edge_is_rejected(self):
        with self.assertRaises(ValueError):
            logic.validate_victim_band(victim_band(f_low_hz=0.0))

    def test_inverted_band_edges_are_rejected(self):
        with self.assertRaises(ValueError):
            logic.validate_victim_band(victim_band(f_low_hz=1.6e9, f_high_hz=1.5e9))

    def test_equal_band_edges_are_rejected(self):
        with self.assertRaises(ValueError):
            logic.validate_victim_band(victim_band(f_high_hz=1.5e9))

    def test_negative_isolation_is_rejected(self):
        with self.assertRaises(ValueError):
            logic.validate_victim_band(victim_band(isolation_db=-3.0))

    def test_missing_noise_floor_is_rejected(self):
        band = victim_band()
        del band["noise_floor_dbm"]
        with self.assertRaises(ValueError):
            logic.validate_victim_band(band)


class TestCarrierPlanValidation(unittest.TestCase):
    def test_two_equal_carriers_give_a_three_db_aggregate(self):
        plan = logic.validate_carrier_plan(carrier_plan())
        self.assertEqual(plan["carrier_count"], 2)
        self.assertAlmostEqual(
            plan["aggregate_power_dbm"], 40.0 + HALF_POWER_DB, places=10
        )
        self.assertAlmostEqual(plan["max_carrier_power_dbm"], 40.0, places=10)

    def test_transmit_span_is_taken_from_the_carriers(self):
        plan = logic.validate_carrier_plan(carrier_plan())
        self.assertAlmostEqual(plan["f_low_hz"], 1.80e9, places=3)
        self.assertAlmostEqual(plan["f_high_hz"], 1.83e9, places=3)

    def test_single_carrier_plan_is_rejected(self):
        with self.assertRaises(ValueError):
            logic.validate_carrier_plan(
                carrier_plan(carrier_frequencies_hz=[1.8e9], carrier_powers_dbm=[40.0])
            )

    def test_length_mismatch_is_rejected(self):
        with self.assertRaises(ValueError):
            logic.validate_carrier_plan(carrier_plan(carrier_powers_dbm=[40.0]))

    def test_duplicate_carrier_frequencies_are_rejected(self):
        with self.assertRaises(ValueError):
            logic.validate_carrier_plan(
                carrier_plan(carrier_frequencies_hz=[1.8e9, 1.8e9])
            )

    def test_non_positive_carrier_frequency_is_rejected(self):
        with self.assertRaises(ValueError):
            logic.validate_carrier_plan(
                carrier_plan(carrier_frequencies_hz=[0.0, 1.83e9])
            )

    def test_non_mapping_plan_is_rejected(self):
        with self.assertRaises(ValueError):
            logic.validate_carrier_plan([1.8e9, 1.83e9])

    def test_missing_power_list_is_rejected(self):
        plan = carrier_plan()
        del plan["carrier_powers_dbm"]
        with self.assertRaises(ValueError):
            logic.validate_carrier_plan(plan)


class TestDerivation(unittest.TestCase):
    def test_derivation_carries_both_planes(self):
        derived = logic.derive_acceptance_levels([victim_band()], 2.0, 3.0)
        self.assertEqual(len(derived), 1)
        self.assertAlmostEqual(
            derived[0]["tolerable_interference_dbm"], -134.0, places=10
        )
        self.assertAlmostEqual(derived[0]["acceptance_level_dbm"], -54.0, places=10)

    def test_two_bands_derive_independently(self):
        derived = logic.derive_acceptance_levels(
            [victim_band(), victim_band(name="rx-s-band", isolation_db=95.0)], 2.0, 3.0
        )
        self.assertAlmostEqual(derived[1]["acceptance_level_dbm"], -44.0, places=10)

    def test_empty_band_list_is_rejected(self):
        with self.assertRaises(ValueError):
            logic.derive_acceptance_levels([], 2.0, 3.0)

    def test_duplicate_band_name_is_rejected(self):
        with self.assertRaises(ValueError):
            logic.derive_acceptance_levels([victim_band(), victim_band()], 2.0, 3.0)

    def test_negative_uncertainty_is_rejected(self):
        with self.assertRaises(ValueError):
            logic.derive_acceptance_levels([victim_band()], -1.0, 3.0)


class TestReconciliation(unittest.TestCase):
    def test_supplier_below_requirement_is_agreed(self):
        result = logic.reconcile_level(-60.0, -54.0)
        self.assertEqual(result["status"], logic.STATUS_AGREED)
        self.assertAlmostEqual(result["agreed_level_dbm"], -60.0, places=10)
        self.assertAlmostEqual(result["exceedance_db"], 0.0, places=10)

    def test_supplier_equal_to_requirement_is_agreed_at_the_boundary(self):
        requirement = logic.acceptance_level_dbm(-134.0, 85.0, 2.0, 3.0)
        result = logic.reconcile_level(requirement, requirement)
        self.assertEqual(result["status"], logic.STATUS_AGREED)

    def test_supplier_inside_negotiation_band_is_negotiable(self):
        result = logic.reconcile_level(-52.0, -54.0, negotiation_band_db=3.0)
        self.assertEqual(result["status"], logic.STATUS_NEGOTIABLE)
        self.assertAlmostEqual(result["exceedance_db"], 2.0, places=10)

    def test_supplier_at_the_negotiation_edge_is_still_negotiable(self):
        result = logic.reconcile_level(-51.0, -54.0, negotiation_band_db=3.0)
        self.assertEqual(result["status"], logic.STATUS_NEGOTIABLE)

    def test_supplier_beyond_negotiation_band_needs_a_waiver(self):
        result = logic.reconcile_level(-50.0, -54.0, negotiation_band_db=3.0)
        self.assertEqual(result["status"], logic.STATUS_WAIVER_REQUIRED)

    def test_stricter_of_the_two_levels_governs(self):
        result = logic.reconcile_level(-50.0, -54.0, negotiation_band_db=10.0)
        self.assertAlmostEqual(result["agreed_level_dbm"], -54.0, places=10)

    def test_negative_negotiation_band_is_rejected(self):
        with self.assertRaises(ValueError):
            logic.reconcile_level(-60.0, -54.0, negotiation_band_db=-1.0)

    def test_non_numeric_supplier_level_is_rejected(self):
        with self.assertRaises(ValueError):
            logic.reconcile_level("-60", -54.0)


class TestPlanValidity(unittest.TestCase):
    def test_identical_plan_raises_no_finding(self):
        self.assertEqual(logic.check_plan_validity(carrier_plan(), carrier_plan()), [])

    def test_extra_carrier_is_a_finding(self):
        flown = carrier_plan(
            carrier_frequencies_hz=[1.80e9, 1.81e9, 1.83e9],
            carrier_powers_dbm=[40.0, 40.0, 40.0],
        )
        findings = logic.check_plan_validity(carrier_plan(), flown)
        self.assertTrue(any("carrier count" in f for f in findings))

    def test_raised_carrier_power_is_a_finding(self):
        flown = carrier_plan(carrier_powers_dbm=[43.0, 43.0])
        findings = logic.check_plan_validity(carrier_plan(), flown)
        self.assertTrue(any("per-carrier-power" in f for f in findings))

    def test_carrier_outside_the_agreed_span_is_a_finding(self):
        flown = carrier_plan(carrier_frequencies_hz=[1.80e9, 1.90e9])
        findings = logic.check_plan_validity(carrier_plan(), flown)
        self.assertTrue(any("outside the agreed transmit span" in f for f in findings))

    def test_lower_flown_power_raises_no_finding(self):
        flown = carrier_plan(carrier_powers_dbm=[37.0, 37.0])
        self.assertEqual(logic.check_plan_validity(carrier_plan(), flown), [])

    def test_invalid_as_flown_plan_is_rejected(self):
        with self.assertRaises(ValueError):
            logic.check_plan_validity(carrier_plan(), {"carrier_frequencies_hz": [1e9]})


class TestFullAssessment(unittest.TestCase):
    def test_compliant_case_is_agreed(self):
        result = logic.assess_acceptance_agreement(
            [victim_band()],
            carrier_plan(),
            {"rx-l-band": -60.0},
            2.0,
            3.0,
            expected_products_dbm={"rx-l-band": [-70.0, -72.0]},
        )
        self.assertTrue(result["agreed"])
        self.assertEqual(result["bands"][0]["status"], logic.STATUS_AGREED)
        self.assertAlmostEqual(result["bands"][0]["agreed_level_dbm"], -60.0, places=10)

    def test_aggregate_exactly_at_the_agreed_level_is_agreed(self):
        agreed = -54.0
        product = agreed - HALF_POWER_DB
        result = logic.assess_acceptance_agreement(
            [victim_band()],
            carrier_plan(),
            {"rx-l-band": agreed},
            2.0,
            3.0,
            expected_products_dbm={"rx-l-band": [product, product]},
        )
        self.assertTrue(result["agreed"])
        self.assertAlmostEqual(
            result["bands"][0]["aggregate_product_dbm"], agreed, places=9
        )

    def test_aggregate_above_the_agreed_level_is_a_finding(self):
        result = logic.assess_acceptance_agreement(
            [victim_band()],
            carrier_plan(),
            {"rx-l-band": -54.0},
            2.0,
            3.0,
            expected_products_dbm={"rx-l-band": [-54.0, -54.0]},
        )
        self.assertFalse(result["agreed"])
        self.assertTrue(
            any("exceeds agreed" in f for f in result["bands"][0]["findings"])
        )

    def test_supplier_waiver_blocks_the_agreement(self):
        result = logic.assess_acceptance_agreement(
            [victim_band()], carrier_plan(), {"rx-l-band": -40.0}, 2.0, 3.0
        )
        self.assertFalse(result["agreed"])
        self.assertEqual(result["bands"][0]["status"], logic.STATUS_WAIVER_REQUIRED)

    def test_as_flown_plan_growth_blocks_the_agreement(self):
        result = logic.assess_acceptance_agreement(
            [victim_band()],
            carrier_plan(),
            {"rx-l-band": -60.0},
            2.0,
            3.0,
            as_flown_plan=carrier_plan(carrier_powers_dbm=[44.0, 44.0]),
        )
        self.assertFalse(result["agreed"])
        self.assertTrue(result["plan_findings"])

    def test_band_without_a_supplier_level_is_rejected(self):
        with self.assertRaises(ValueError):
            logic.assess_acceptance_agreement(
                [victim_band()], carrier_plan(), {}, 2.0, 3.0
            )

    def test_non_mapping_supplier_levels_are_rejected(self):
        with self.assertRaises(ValueError):
            logic.assess_acceptance_agreement(
                [victim_band()], carrier_plan(), [-60.0], 2.0, 3.0
            )

    def test_non_mapping_expected_products_are_rejected(self):
        with self.assertRaises(ValueError):
            logic.assess_acceptance_agreement(
                [victim_band()],
                carrier_plan(),
                {"rx-l-band": -60.0},
                2.0,
                3.0,
                expected_products_dbm=[-70.0],
            )

    def test_two_victim_bands_are_reported_separately(self):
        result = logic.assess_acceptance_agreement(
            [victim_band(), victim_band(name="rx-s-band", isolation_db=95.0)],
            carrier_plan(),
            {"rx-l-band": -60.0, "rx-s-band": -50.0},
            2.0,
            3.0,
        )
        self.assertEqual(len(result["bands"]), 2)
        self.assertTrue(result["bands"][0]["agreed"])
        self.assertTrue(result["bands"][1]["agreed"])


if __name__ == "__main__":
    unittest.main()
