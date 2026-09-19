"""Contract test for the in-situ versus ex-situ read-out leaf (stdlib unittest)."""

import unittest

from q7006_in_situ_vs_ex_situ_logic import (
    INERT_ATMOSPHERES,
    MAX_BREAKS_TO_AIR,
    MAX_RECOVERED_FRACTION,
    MAX_TRANSFER_HUMIDITY_PCT,
    MODE_EX_SITU,
    MODE_IN_SITU,
    assess_measurement_allocation,
    decide_measurement_mode,
    handling_controls,
    in_situ_reasons,
    in_situ_required,
    max_transfer_time,
    recovered_fraction_during_transfer,
    recovery_risk_ratio,
    validate_property,
)


def prop(**kw):
    record = {
        "property": "solar-absorptance",
        "recovery_half_time_h": 240.0,
        "air_sensitive": False,
        "moisture_sensitive": False,
        "light_sensitive": False,
        "in_situ_instrument_available": True,
        "transfer_time_h": 2.0,
        "transfer_atmosphere": "dry-nitrogen",
        "transfer_humidity_pct": 5.0,
        "breaks_to_air": 1,
    }
    record.update(kw)
    return record


class TestValidation(unittest.TestCase):
    def test_a_well_formed_record_normalizes(self):
        item = validate_property(prop())
        self.assertEqual(item["property"], "solar-absorptance")
        self.assertAlmostEqual(item["transfer_time_h"], 2.0, places=9)

    def test_an_unknown_transfer_atmosphere_raises(self):
        with self.assertRaises(ValueError):
            validate_property(prop(transfer_atmosphere="helium-purge"))

    def test_a_fractional_opening_count_raises(self):
        with self.assertRaises(ValueError):
            validate_property(prop(breaks_to_air=1.5))

    def test_a_negative_transfer_time_raises(self):
        with self.assertRaises(ValueError):
            validate_property(prop(transfer_time_h=-1.0))

    def test_a_zero_recovery_half_time_raises(self):
        with self.assertRaises(ValueError):
            validate_property(prop(recovery_half_time_h=0.0))

    def test_a_non_boolean_sensitivity_flag_raises(self):
        with self.assertRaises(ValueError):
            validate_property(prop(air_sensitive="yes"))

    def test_a_property_with_no_recovery_keeps_a_none_half_time(self):
        item = validate_property(prop(recovery_half_time_h=None))
        self.assertIsNone(item["recovery_half_time_h"])


class TestRecoveryArithmetic(unittest.TestCase):
    def test_a_transfer_of_one_half_time_is_one_risk_ratio(self):
        self.assertAlmostEqual(recovery_risk_ratio(240.0, 240.0), 1.0, places=9)

    def test_half_the_change_is_back_after_one_half_time(self):
        self.assertAlmostEqual(
            recovered_fraction_during_transfer(240.0, 240.0), 0.5, places=9
        )

    def test_nothing_has_recovered_at_zero_transfer_time(self):
        self.assertAlmostEqual(
            recovered_fraction_during_transfer(0.0, 240.0), 0.0, places=9
        )

    def test_the_transfer_ceiling_lands_exactly_on_the_recovered_fraction(self):
        ceiling = max_transfer_time(240.0)
        self.assertAlmostEqual(
            recovered_fraction_during_transfer(ceiling, 240.0),
            MAX_RECOVERED_FRACTION,
            places=9,
        )

    def test_a_zero_half_time_has_no_risk_ratio(self):
        with self.assertRaises(ValueError):
            recovery_risk_ratio(2.0, 0.0)


class TestInSituDrivers(unittest.TestCase):
    def test_a_slow_recovering_property_can_be_read_out_ex_situ(self):
        self.assertFalse(in_situ_required(prop()))
        self.assertEqual(in_situ_reasons(prop()), [])

    def test_a_fast_bleaching_property_has_to_be_read_out_in_situ(self):
        reasons = in_situ_reasons(prop(recovery_half_time_h=1.0))
        self.assertIn("recovery-during-transfer-exceeds-the-ceiling", reasons)

    def test_a_transfer_exactly_on_the_ceiling_does_not_force_in_situ(self):
        ceiling = max_transfer_time(240.0)
        self.assertEqual(in_situ_reasons(prop(transfer_time_h=ceiling)), [])

    def test_an_air_sensitive_surface_carried_through_air_forces_in_situ(self):
        reasons = in_situ_reasons(prop(air_sensitive=True, transfer_atmosphere="air"))
        self.assertIn("air-sensitive-surface-transferred-through-air", reasons)

    def test_an_inert_container_clears_the_air_sensitivity(self):
        for atmosphere in INERT_ATMOSPHERES:
            self.assertEqual(
                in_situ_reasons(prop(air_sensitive=True, transfer_atmosphere=atmosphere)),
                [],
            )

    def test_a_damp_transfer_of_a_moisture_sensitive_surface_forces_in_situ(self):
        reasons = in_situ_reasons(
            prop(
                moisture_sensitive=True,
                transfer_humidity_pct=MAX_TRANSFER_HUMIDITY_PCT + 20.0,
            )
        )
        self.assertIn("moisture-sensitive-surface-above-the-humidity-ceiling", reasons)

    def test_humidity_exactly_on_the_ceiling_is_accepted(self):
        self.assertEqual(
            in_situ_reasons(
                prop(
                    moisture_sensitive=True,
                    transfer_humidity_pct=MAX_TRANSFER_HUMIDITY_PCT,
                )
            ),
            [],
        )

    def test_too_many_chamber_openings_force_in_situ(self):
        reasons = in_situ_reasons(prop(breaks_to_air=MAX_BREAKS_TO_AIR + 2))
        self.assertIn("more-chamber-openings-than-the-handling-ceiling", reasons)


class TestControls(unittest.TestCase):
    def test_a_recovering_property_carries_a_transfer_time_ceiling(self):
        self.assertIn("transfer-time-ceiling", handling_controls(prop()))

    def test_an_air_sensitive_property_carries_a_sealed_container(self):
        self.assertIn(
            "inert-or-evacuated-transfer-container",
            handling_controls(prop(air_sensitive=True)),
        )

    def test_a_photo_bleaching_property_carries_a_light_tight_container(self):
        self.assertIn(
            "light-tight-transfer-container",
            handling_controls(prop(light_sensitive=True)),
        )

    def test_every_ex_situ_read_out_carries_an_opening_ceiling(self):
        self.assertIn(
            "chamber-opening-count-ceiling",
            handling_controls(prop(recovery_half_time_h=None)),
        )


class TestDecision(unittest.TestCase):
    def test_a_stable_property_is_decided_ex_situ_with_controls(self):
        decision = decide_measurement_mode(prop())
        self.assertEqual(decision["mode"], MODE_EX_SITU)
        self.assertIn("transfer-time-ceiling", decision["handling_controls"])
        self.assertEqual(decision["findings"], [])

    def test_a_bleaching_property_with_an_instrument_is_decided_in_situ(self):
        decision = decide_measurement_mode(prop(recovery_half_time_h=1.0))
        self.assertEqual(decision["mode"], MODE_IN_SITU)
        self.assertEqual(decision["handling_controls"], [])

    def test_a_bleaching_property_with_no_instrument_is_a_finding(self):
        decision = decide_measurement_mode(
            prop(recovery_half_time_h=1.0, in_situ_instrument_available=False)
        )
        self.assertEqual(decision["mode"], MODE_EX_SITU)
        self.assertIn(
            "in-situ-read-out-required-but-no-instrument-in-the-facility",
            decision["findings"],
        )

    def test_the_decision_reports_the_recovered_fraction_it_used(self):
        decision = decide_measurement_mode(prop(transfer_time_h=240.0))
        self.assertAlmostEqual(
            decision["recovered_fraction_during_transfer"], 0.5, places=9
        )


class TestAllocation(unittest.TestCase):
    def test_a_planned_allocation_is_sound(self):
        result = assess_measurement_allocation(
            {
                "plan_id": "UV-2026-012",
                "properties": [prop(), prop(property="optical-transmittance")],
                "planned_controls": [
                    "transfer-time-ceiling",
                    "chamber-opening-count-ceiling",
                ],
            }
        )
        self.assertTrue(result["allocation_sound"])
        self.assertEqual(result["in_situ_properties"], [])
        self.assertEqual(len(result["ex_situ_properties"]), 2)

    def test_an_unplanned_mandated_control_is_a_finding(self):
        result = assess_measurement_allocation(
            {
                "properties": [prop(air_sensitive=True)],
                "planned_controls": ["transfer-time-ceiling"],
            }
        )
        self.assertIn("mandated-handling-control-not-planned", result["findings"])
        self.assertIn(
            "inert-or-evacuated-transfer-container", result["unplanned_controls"]
        )

    def test_a_mixed_allocation_splits_the_properties(self):
        result = assess_measurement_allocation(
            {
                "properties": [
                    prop(),
                    prop(property="optical-transmittance", recovery_half_time_h=1.0),
                ],
                "planned_controls": [
                    "transfer-time-ceiling",
                    "chamber-opening-count-ceiling",
                ],
            }
        )
        self.assertEqual(result["in_situ_properties"], ["optical-transmittance"])
        self.assertEqual(result["ex_situ_properties"], ["solar-absorptance"])

    def test_a_repeated_property_raises(self):
        with self.assertRaises(ValueError):
            assess_measurement_allocation({"properties": [prop(), prop()]})

    def test_a_non_mapping_plan_raises(self):
        with self.assertRaises(ValueError):
            assess_measurement_allocation(["UV-2026-012"])

    def test_an_empty_property_set_raises(self):
        with self.assertRaises(ValueError):
            assess_measurement_allocation({"properties": []})


if __name__ == "__main__":
    unittest.main()
