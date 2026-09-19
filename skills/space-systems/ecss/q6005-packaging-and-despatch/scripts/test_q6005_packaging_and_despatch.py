#!/usr/bin/env python3
"""Contract test for the ECSS-Q-ST-60-05 clause 13.3 packaging-and-despatch leaf.

Offline, deterministic, stdlib unittest.
Run: python3 test_q6005_packaging_and_despatch.py
"""

import unittest

from q6005_packaging_and_despatch_logic import (
    ACCEPTANCE_PACKING_INDEX,
    ESD_SENSITIVITY_BANDS,
    INITIAL_MOISTURE_G_PER_LITRE,
    MANDATORY_PACKING_PROVISIONS,
    PACKAGING_PROTECTION_LEVEL,
    PACKING_PROVISION_WEIGHTS,
    PACKING_TOLERANCE,
    PROVISION_STATE_CREDIT,
    TRANSPORT_MODES,
    VERDICTS,
    assess_packaging_and_despatch,
    assess_provision,
    cushion_findings,
    despatch_findings,
    esd_protection_is_sufficient,
    moisture_findings,
    normalize_provision,
    packaging_protection_level,
    packing_provision_index,
    packing_provision_weight,
    provision_state_credit,
    required_cushion_thickness_mm,
    required_desiccant_units,
    required_esd_protection_level,
    transport_envelope,
)

SPARE_PROVISION = "unpacking-and-receiving-instruction"


def limits(**overrides):
    """The storage temperature range the product is qualified over."""
    record = {"min_storage_temp_c": -55.0, "max_storage_temp_c": 125.0}
    record.update(overrides)
    return record


def device(**overrides):
    """A sensitive hybrid with a wide storage range."""
    record = {"withstand_volts": 200.0, "limits": limits()}
    record.update(overrides)
    return record


def packaging(**overrides):
    """A shielded bag around a dissipative rigid carrier."""
    record = {"build": "shielding-bag-with-dissipative-rigid-carrier"}
    record.update(overrides)
    return record


def drop(**overrides):
    """A one metre drop the units can take at 100 g."""
    record = {
        "drop_height_mm": 1000.0,
        "allowable_deceleration_g": 100.0,
        "cushion_efficiency": 0.4,
        "fitted_thickness_mm": 30.0,
    }
    record.update(overrides)
    return record


def moisture(**overrides):
    """A barrier with enough desiccant for the declared storage period."""
    record = {
        "internal_volume_litres": 2.0,
        "barrier_transmission_g_per_month": 0.2,
        "storage_months": 12.0,
        "unit_capacity_g": 6.0,
        "fitted_units": 1,
        "humidity_indicator_fitted": True,
    }
    record.update(overrides)
    return record


def container(**overrides):
    """A vented outer container, labelled and with its packing list."""
    record = {
        "sealed": True,
        "pressure_vented": True,
        "packing_list_enclosed": True,
        "electrostatic_label_applied": True,
    }
    record.update(overrides)
    return record


def despatch(**overrides):
    """A road shipment in a vented container."""
    record = {"mode": "road-freight", "container": container()}
    record.update(overrides)
    return record


def specified_provisions(**states):
    """Every packing provision specified, with named exceptions."""
    provisions = []
    for name in sorted(PACKING_PROVISION_WEIGHTS):
        entry = {"provision": name, "state": "specified"}
        if name in states:
            entry["state"] = states[name]
        provisions.append(entry)
    return provisions


def run(**overrides):
    """Grade one packing and despatch arrangement."""
    case = {
        "shipment_id": "HYB-1234-SHP-07",
        "device": device(),
        "packaging": packaging(),
        "drop": drop(),
        "moisture": moisture(),
        "despatch": despatch(),
        "provisions": specified_provisions(),
    }
    case.update(overrides)
    return assess_packaging_and_despatch(**case)


class ElectrostaticTests(unittest.TestCase):
    def test_the_most_sensitive_band_demands_the_highest_level(self):
        self.assertEqual(required_esd_protection_level(100.0), ESD_SENSITIVITY_BANDS[0][1])

    def test_a_voltage_exactly_on_a_band_edge_stays_in_that_band(self):
        edge, level = ESD_SENSITIVITY_BANDS[0]
        self.assertEqual(required_esd_protection_level(edge), level)

    def test_a_robust_part_demands_less_than_a_sensitive_one(self):
        self.assertLess(
            required_esd_protection_level(8000.0), required_esd_protection_level(100.0)
        )

    def test_a_non_positive_withstand_voltage_is_rejected(self):
        with self.assertRaises(ValueError):
            required_esd_protection_level(0.0)

    def test_an_unknown_packaging_build_is_rejected(self):
        with self.assertRaises(ValueError):
            packaging_protection_level("a-padded-envelope")

    def test_an_ordinary_bag_provides_no_protection(self):
        self.assertEqual(packaging_protection_level("ordinary-polyethylene-bag"), 0)

    def test_a_dissipative_bag_is_not_enough_for_a_sensitive_part(self):
        self.assertFalse(esd_protection_is_sufficient("dissipative-bag", 100.0))

    def test_a_shielded_carrier_is_enough_for_a_sensitive_part(self):
        self.assertTrue(
            esd_protection_is_sufficient("shielding-bag-with-dissipative-rigid-carrier", 100.0)
        )

    def test_a_dissipative_bag_is_enough_for_a_robust_part(self):
        self.assertTrue(esd_protection_is_sufficient("dissipative-bag", 3000.0))


class CushionTests(unittest.TestCase):
    def test_the_thickness_follows_the_published_drop_relation(self):
        self.assertAlmostEqual(
            required_cushion_thickness_mm(1000.0, 100.0, 0.5), 1000.0 / (100.0 * 0.5), places=9
        )

    def test_a_higher_drop_needs_a_thicker_cushion(self):
        self.assertGreater(
            required_cushion_thickness_mm(1200.0, 100.0, 0.4),
            required_cushion_thickness_mm(600.0, 100.0, 0.4),
        )

    def test_a_tougher_unit_needs_a_thinner_cushion(self):
        self.assertLess(
            required_cushion_thickness_mm(1000.0, 200.0, 0.4),
            required_cushion_thickness_mm(1000.0, 100.0, 0.4),
        )

    def test_an_efficiency_above_one_is_rejected(self):
        with self.assertRaises(ValueError):
            required_cushion_thickness_mm(1000.0, 100.0, 1.4)

    def test_a_zero_drop_height_is_rejected(self):
        with self.assertRaises(ValueError):
            required_cushion_thickness_mm(0.0, 100.0, 0.4)

    def test_a_cushion_exactly_on_the_required_thickness_is_sufficient(self):
        required = required_cushion_thickness_mm(1000.0, 100.0, 0.4)
        result = cushion_findings(1000.0, 100.0, 0.4, required)
        self.assertTrue(result["sufficient"])
        self.assertAlmostEqual(result["margin_mm"], 0.0, places=9)

    def test_a_thin_cushion_is_reported(self):
        result = cushion_findings(1000.0, 100.0, 0.4, 10.0)
        self.assertFalse(result["sufficient"])
        self.assertIn("cushion-thinner-than-the-declared-drop-demands", result["findings"])


class MoistureTests(unittest.TestCase):
    def test_the_demand_adds_the_sealed_in_moisture_to_the_ingress(self):
        demand = required_desiccant_units(2.0, 0.2, 12.0, 6.0)
        self.assertAlmostEqual(
            demand["moisture_demand_g"],
            INITIAL_MOISTURE_G_PER_LITRE * 2.0 + 0.2 * 12.0,
            places=9,
        )

    def test_the_units_are_counted_up_never_down(self):
        demand = required_desiccant_units(2.0, 0.2, 12.0, 3.0)
        self.assertEqual(demand["required_units"], 2)

    def test_a_demand_landing_exactly_on_a_unit_does_not_buy_another(self):
        demand = required_desiccant_units(1.0, 0.0, 1.0, INITIAL_MOISTURE_G_PER_LITRE)
        self.assertEqual(demand["required_units"], 1)

    def test_a_longer_storage_period_needs_more_desiccant(self):
        short = required_desiccant_units(2.0, 0.5, 6.0, 3.0)["required_units"]
        long_stay = required_desiccant_units(2.0, 0.5, 36.0, 3.0)["required_units"]
        self.assertGreater(long_stay, short)

    def test_a_zero_unit_capacity_is_rejected(self):
        with self.assertRaises(ValueError):
            required_desiccant_units(2.0, 0.2, 12.0, 0.0)

    def test_a_negative_barrier_transmission_is_rejected(self):
        with self.assertRaises(ValueError):
            required_desiccant_units(2.0, -0.2, 12.0, 6.0)

    def test_enough_desiccant_with_an_indicator_raises_nothing(self):
        demand = required_desiccant_units(2.0, 0.2, 12.0, 6.0)
        self.assertTrue(moisture_findings(demand, 1, True)["sufficient"])

    def test_a_desiccant_shortfall_is_counted(self):
        demand = required_desiccant_units(2.0, 0.5, 36.0, 3.0)
        result = moisture_findings(demand, 1, True)
        self.assertGreater(result["shortfall_units"], 0)
        self.assertIn("desiccant-below-the-moisture-demand", result["findings"])

    def test_desiccant_with_no_indicator_is_reported(self):
        demand = required_desiccant_units(2.0, 0.2, 12.0, 6.0)
        self.assertIn(
            "desiccant-enclosed-with-no-humidity-indicator",
            moisture_findings(demand, 1, False)["findings"],
        )

    def test_a_fractional_desiccant_count_is_rejected(self):
        demand = required_desiccant_units(2.0, 0.2, 12.0, 6.0)
        with self.assertRaises(ValueError):
            moisture_findings(demand, 1.5, True)


class DespatchTests(unittest.TestCase):
    def test_every_published_mode_states_a_rising_envelope(self):
        for mode in TRANSPORT_MODES:
            envelope = transport_envelope(mode)
            self.assertLess(envelope["min_temp_c"], envelope["max_temp_c"], mode)

    def test_an_unknown_transport_mode_is_rejected(self):
        with self.assertRaises(ValueError):
            transport_envelope("carrier-pigeon")

    def test_a_road_shipment_inside_the_product_limits_raises_nothing(self):
        result = despatch_findings("road-freight", limits(), container())
        self.assertTrue(result["acceptable"])

    def test_a_cold_leg_below_the_product_limit_is_reported(self):
        result = despatch_findings("air-freight", limits(min_storage_temp_c=-10.0), container())
        self.assertIn("transport-cold-end-below-the-product-limit", result["findings"])

    def test_a_hot_leg_above_the_product_limit_is_reported(self):
        result = despatch_findings("sea-freight", limits(max_storage_temp_c=40.0), container())
        self.assertIn("transport-hot-end-above-the-product-limit", result["findings"])

    def test_a_sealed_unvented_container_is_refused_for_an_air_leg(self):
        result = despatch_findings(
            "air-freight", limits(), container(pressure_vented=False)
        )
        self.assertIn(
            "sealed-container-not-vented-for-a-reduced-pressure-leg", result["findings"]
        )

    def test_an_unvented_container_is_fine_on_the_road(self):
        result = despatch_findings("road-freight", limits(), container(pressure_vented=False))
        self.assertTrue(result["acceptable"])

    def test_a_shipment_with_no_packing_list_is_reported(self):
        result = despatch_findings(
            "road-freight", limits(), container(packing_list_enclosed=False)
        )
        self.assertIn("no-packing-list-enclosed-with-the-shipment", result["findings"])

    def test_a_container_with_no_electrostatic_label_is_reported(self):
        result = despatch_findings(
            "road-freight", limits(), container(electrostatic_label_applied=False)
        )
        self.assertIn("no-electrostatic-handling-label-on-the-container", result["findings"])

    def test_a_product_range_that_does_not_rise_is_rejected(self):
        with self.assertRaises(ValueError):
            despatch_findings("road-freight", limits(max_storage_temp_c=-80.0), container())


class ProvisionTests(unittest.TestCase):
    def test_every_mandatory_provision_carries_a_published_weight(self):
        for name in MANDATORY_PACKING_PROVISIONS:
            self.assertIn(name, PACKING_PROVISION_WEIGHTS)

    def test_an_unknown_packing_provision_is_rejected(self):
        with self.assertRaises(ValueError):
            packing_provision_weight("bubble-wrap-because-it-is-fun")

    def test_an_unknown_provision_state_is_rejected(self):
        with self.assertRaises(ValueError):
            provision_state_credit("we-usually-do-that")

    def test_a_provision_nobody_mentioned_defaults_to_not_specified(self):
        self.assertEqual(
            normalize_provision({"provision": SPARE_PROVISION})["state"], "not-specified"
        )

    def test_a_specified_provision_earns_its_full_weight(self):
        record = assess_provision({"provision": SPARE_PROVISION, "state": "specified"})
        self.assertAlmostEqual(
            record["weighted_credit"], PACKING_PROVISION_WEIGHTS[SPARE_PROVISION], places=9
        )

    def test_a_missing_mandatory_provision_is_marked_missing(self):
        record = assess_provision({"provision": "electrostatic-protective-packaging"})
        self.assertTrue(record["mandatory_missing"])

    def test_a_fully_specified_arrangement_reaches_a_full_index(self):
        records = [assess_provision(entry) for entry in specified_provisions()]
        self.assertAlmostEqual(packing_provision_index(records), 1.0, places=9)

    def test_an_empty_provision_set_is_rejected(self):
        with self.assertRaises(ValueError):
            packing_provision_index([])


class WholeShipmentTests(unittest.TestCase):
    def test_a_sound_arrangement_passes_with_no_findings(self):
        result = run()
        self.assertEqual(result["verdict"], "packaging-and-despatch-acceptable")
        self.assertTrue(result["shipment_released"])
        self.assertEqual(result["findings"], [])
        self.assertAlmostEqual(result["packing_provision_index"], 1.0, places=9)

    def test_every_verdict_returned_is_one_of_the_published_verdicts(self):
        self.assertIn(run()["verdict"], VERDICTS)

    def test_an_arrangement_missing_a_mandatory_provision_is_incomplete(self):
        result = run(
            provisions=specified_provisions(
                **{"electrostatic-protective-packaging": "not-specified"}
            )
        )
        self.assertEqual(result["verdict"], "packaging-and-despatch-assessment-incomplete")

    def test_a_bag_below_the_demanded_protection_level_rejects_the_shipment(self):
        result = run(packaging=packaging(build="dissipative-bag"))
        self.assertEqual(result["verdict"], "packaging-and-despatch-rejected")
        self.assertFalse(result["esd_protection_sufficient"])

    def test_a_thin_cushion_rejects_the_shipment(self):
        result = run(drop=drop(fitted_thickness_mm=5.0))
        self.assertEqual(result["verdict"], "packaging-and-despatch-rejected")

    def test_a_desiccant_shortfall_rejects_the_shipment(self):
        result = run(moisture=moisture(storage_months=60.0, unit_capacity_g=2.0))
        self.assertEqual(result["verdict"], "packaging-and-despatch-rejected")
        self.assertGreater(result["desiccant"]["shortfall_units"], 0)

    def test_an_unvented_air_shipment_rejects_the_arrangement(self):
        result = run(
            despatch=despatch(mode="air-freight", container=container(pressure_vented=False))
        )
        self.assertEqual(result["verdict"], "packaging-and-despatch-rejected")

    def test_an_observation_on_an_optional_provision_leaves_open_actions(self):
        result = run(
            provisions=specified_provisions(**{SPARE_PROVISION: "specified-with-observation"})
        )
        self.assertEqual(
            result["verdict"], "packaging-and-despatch-acceptable-with-open-actions"
        )
        self.assertTrue(result["shipment_released"])

    def test_a_provision_nobody_listed_is_graded_as_not_specified(self):
        result = run(provisions=[{"provision": SPARE_PROVISION, "state": "specified"}])
        states = {r["provision"]: r["state"] for r in result["provisions"]}
        self.assertEqual(states["packing-list-enclosed"], "not-specified")
        self.assertEqual(len(result["provisions"]), len(PACKING_PROVISION_WEIGHTS))

    def test_a_repeated_packing_provision_is_rejected(self):
        with self.assertRaises(ValueError):
            run(
                provisions=specified_provisions()
                + [{"provision": SPARE_PROVISION, "state": "specified"}]
            )

    def test_a_blank_shipment_identifier_is_rejected(self):
        with self.assertRaises(ValueError):
            run(shipment_id="  ")

    def test_a_drop_record_that_is_not_a_mapping_is_rejected(self):
        with self.assertRaises(ValueError):
            run(drop=[1000.0, 100.0])


class ConstantsTests(unittest.TestCase):
    def test_the_tolerance_is_small_enough_to_separate_the_bounds(self):
        self.assertLess(PACKING_TOLERANCE, 1e-6)

    def test_the_provision_credits_span_the_published_scale(self):
        self.assertAlmostEqual(max(PROVISION_STATE_CREDIT.values()), 1.0, places=9)
        self.assertAlmostEqual(min(PROVISION_STATE_CREDIT.values()), 0.0, places=9)

    def test_the_acceptance_index_sits_under_a_fully_specified_arrangement(self):
        self.assertLess(ACCEPTANCE_PACKING_INDEX, 1.0)

    def test_the_sensitivity_bands_rise_and_their_levels_fall(self):
        for earlier, later in zip(ESD_SENSITIVITY_BANDS, ESD_SENSITIVITY_BANDS[1:]):
            self.assertLess(earlier[0], later[0])
            self.assertGreater(earlier[1], later[1])

    def test_some_packaging_build_reaches_the_highest_demanded_level(self):
        self.assertIn(
            max(level for _, level in ESD_SENSITIVITY_BANDS),
            set(PACKAGING_PROTECTION_LEVEL.values()),
        )


if __name__ == "__main__":
    unittest.main()
