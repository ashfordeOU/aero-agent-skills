#!/usr/bin/env python3
"""Gate 3 contract test: ECSS-E-ST-20C clause 5.7.6 payload-to-primary-
bus interaction verification.

Exercises scripts/e20_payload_bus_interaction_verification_logic.py
(stdlib unittest, offline). Contract: a case kind maps to exactly one
family and an unrecognized kind raises; the mandatory field list
follows the family and a field that is absent or empty is reported;
the inrush peak is the bus voltage over the limiting resistance, the
decay constant is that resistance times the input capacitance, and the
time above a threshold is the constant scaled by the logarithm of the
peak over the threshold, zero when the peak never reaches it; the load
step sag is the step current over the bus capacitance times the angular
control bandwidth, with the harness drop added, checked against the bus
lower limit and the payload undervoltage lockout; the fault current is
the bus voltage over the fault path, the clearing time is inverse
square in that current floored by the device response time and
unbounded at or below the rating, and the let-through energy is the
current squared times the clearing time; a quantity sitting exactly on
its limit is compliant; and the campaign is verified only when the
coverage and case lists are both empty.
"""

import math
import os
import sys
import unittest

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import e20_payload_bus_interaction_verification_logic as pbi  # noqa: E402


def _inrush_fields(**overrides):
    fields = {
        "bus_voltage_v": 28.0,
        "limiter_resistance_ohm": 2.8,
        "load_capacitance_f": 470.0e-6,
        "allowed_peak_inrush_a": 12.0,
        "protection_trip_current_a": 8.0,
        "protection_trip_delay_s": 5.0e-4,
    }
    fields.update(overrides)
    return fields


def _undervoltage_fields(**overrides):
    fields = {
        "bus_voltage_v": 28.0,
        "step_current_a": 8.0,
        "bus_capacitance_f": 2200.0e-6,
        "control_bandwidth_hz": 2000.0,
        "harness_resistance_ohm": 0.05,
        "bus_lower_limit_v": 26.0,
        "payload_undervoltage_lockout_v": 22.0,
    }
    fields.update(overrides)
    return fields


def _failure_fields(**overrides):
    fields = {
        "bus_voltage_v": 28.0,
        "fault_resistance_ohm": 0.05,
        "harness_resistance_ohm": 0.15,
        "protection_rated_current_a": 5.0,
        "protection_i2t_a2s": 2.0,
        "protection_minimum_clearing_time_s": 5.0e-5,
        "containment_time_s": 1.0e-3,
        "containment_outcome": "payload_isolated",
        "allowed_let_through_a2s": 3.0,
    }
    fields.update(overrides)
    return fields


def _case(case_id, case_kind, fields):
    return {"case_id": case_id, "case_kind": case_kind, "declared_fields": fields}


def _clean_campaign():
    return {
        "payload_id": "PLD-IMAGER-A",
        "agreed_failure_cases": ["payload_short_circuit", "payload_overcurrent"],
        "cases": [
            _case("IR-01", "cold_start_inrush", _inrush_fields()),
            _case("UV-01", "load_step_undervoltage", _undervoltage_fields()),
            _case("FC-01", "payload_short_circuit", _failure_fields()),
        ],
    }


class CategorizeCaseTests(unittest.TestCase):
    def test_cold_start_is_an_inrush_case(self):
        self.assertEqual(pbi.categorize_test_case("cold_start_inrush"), "inrush")

    def test_eclipse_entry_is_an_undervoltage_case(self):
        self.assertEqual(
            pbi.categorize_test_case("eclipse_entry_undervoltage"), "undervoltage"
        )

    def test_internal_latch_up_is_an_agreed_failure_case(self):
        self.assertEqual(
            pbi.categorize_test_case("payload_internal_latch_up"), "agreed_failure"
        )

    def test_families_do_not_overlap(self):
        families = (
            pbi.INRUSH_CASE_KINDS,
            pbi.UNDERVOLTAGE_CASE_KINDS,
            pbi.FAILURE_CASE_KINDS,
        )
        for index, family in enumerate(families):
            for other in families[index + 1:]:
                self.assertEqual(family & other, frozenset())

    def test_unrecognized_kind_raises(self):
        with self.assertRaises(ValueError):
            pbi.categorize_test_case("thermal_vacuum_soak")

    def test_missing_kind_raises(self):
        with self.assertRaises(ValueError):
            pbi.categorize_test_case(None)


class MandatoryFieldTests(unittest.TestCase):
    def test_inrush_field_list_is_complete(self):
        fields = pbi.required_case_fields("inrush")
        self.assertEqual(len(fields), 6)
        self.assertIn("limiter_resistance_ohm", fields)

    def test_failure_field_list_includes_containment(self):
        self.assertIn("containment_time_s", pbi.required_case_fields("agreed_failure"))

    def test_unknown_family_raises(self):
        with self.assertRaises(ValueError):
            pbi.required_case_fields("radiation")

    def test_absent_field_is_reported(self):
        fields = _inrush_fields()
        del fields["load_capacitance_f"]
        self.assertEqual(
            pbi.missing_case_fields("inrush", fields), ["load_capacitance_f"]
        )

    def test_empty_field_is_reported(self):
        fields = _inrush_fields(protection_trip_delay_s=None)
        self.assertEqual(
            pbi.missing_case_fields("inrush", fields), ["protection_trip_delay_s"]
        )

    def test_complete_sheet_reports_nothing(self):
        self.assertEqual(pbi.missing_case_fields("inrush", _inrush_fields()), [])

    def test_missing_fields_are_sorted(self):
        fields = _undervoltage_fields()
        del fields["step_current_a"]
        del fields["bus_lower_limit_v"]
        self.assertEqual(
            pbi.missing_case_fields("undervoltage", fields),
            ["bus_lower_limit_v", "step_current_a"],
        )

    def test_field_sheet_that_is_not_a_mapping_raises(self):
        with self.assertRaises(ValueError):
            pbi.missing_case_fields("inrush", ["bus_voltage_v"])


class InrushMathTests(unittest.TestCase):
    def test_peak_is_voltage_over_limiting_resistance(self):
        self.assertAlmostEqual(pbi.peak_inrush_current_a(28.0, 2.8), 10.0, places=9)

    def test_zero_limiting_resistance_raises(self):
        with self.assertRaises(ValueError):
            pbi.peak_inrush_current_a(28.0, 0.0)

    def test_negative_bus_voltage_raises(self):
        with self.assertRaises(ValueError):
            pbi.peak_inrush_current_a(-28.0, 2.8)

    def test_time_constant_is_resistance_times_capacitance(self):
        self.assertAlmostEqual(
            pbi.inrush_time_constant_s(2.8, 470.0e-6), 0.001316, places=12
        )

    def test_zero_capacitance_raises(self):
        with self.assertRaises(ValueError):
            pbi.inrush_time_constant_s(2.8, 0.0)

    def test_peak_below_threshold_spends_no_time_above_it(self):
        self.assertAlmostEqual(
            pbi.inrush_time_above_a(6.0, 8.0, 0.001316), 0.0, places=12
        )

    def test_peak_exactly_at_threshold_spends_no_time_above_it(self):
        self.assertAlmostEqual(
            pbi.inrush_time_above_a(8.0, 8.0, 0.001316), 0.0, places=12
        )

    def test_time_above_threshold_matches_closed_form(self):
        self.assertAlmostEqual(
            pbi.inrush_time_above_a(10.0, 8.0, 0.001316), 2.9365691e-4, places=10
        )

    def test_decay_reaches_the_threshold_at_the_reported_time(self):
        tau = 0.001316
        elapsed = pbi.inrush_time_above_a(10.0, 8.0, tau)
        self.assertAlmostEqual(10.0 * math.exp(-elapsed / tau), 8.0, places=9)

    def test_non_positive_time_constant_raises(self):
        with self.assertRaises(ValueError):
            pbi.inrush_time_above_a(10.0, 8.0, 0.0)


class InrushCaseTests(unittest.TestCase):
    def test_clean_inrush_case_reports_nothing(self):
        result = pbi.evaluate_inrush_case(_case("IR-01", "cold_start_inrush", _inrush_fields()))
        self.assertEqual(result["findings"], [])
        self.assertAlmostEqual(result["peak_current_a"], 10.0, places=9)

    def test_peak_above_the_interface_allowance_is_a_finding(self):
        fields = _inrush_fields(allowed_peak_inrush_a=8.0)
        result = pbi.evaluate_inrush_case(_case("IR-02", "cold_start_inrush", fields))
        self.assertEqual(len(result["findings"]), 1)
        self.assertIn("peak current", result["findings"][0])

    def test_time_above_threshold_outlasting_the_trip_delay_is_a_finding(self):
        fields = _inrush_fields(protection_trip_delay_s=1.0e-5)
        result = pbi.evaluate_inrush_case(_case("IR-03", "cold_start_inrush", fields))
        self.assertEqual(len(result["findings"]), 1)
        self.assertIn("trip delay", result["findings"][0])

    def test_settling_time_exactly_on_its_limit_is_compliant(self):
        # 5 * 2.2 ohm * 680 uF evaluates a few bits above 7.48 ms; the
        # case is physically on the limit, so the comparison absorbs it.
        fields = _inrush_fields(
            limiter_resistance_ohm=2.2,
            load_capacitance_f=680.0e-6,
            allowed_peak_inrush_a=13.0,
            protection_trip_current_a=10.0,
            max_settling_time_s=0.00748,
        )
        result = pbi.evaluate_inrush_case(_case("IR-04", "cold_start_inrush", fields))
        self.assertGreater(result["settling_time_s"], 0.00748)
        self.assertEqual(result["findings"], [])

    def test_settling_time_past_its_limit_is_a_finding(self):
        fields = _inrush_fields(max_settling_time_s=0.004)
        result = pbi.evaluate_inrush_case(_case("IR-05", "cold_start_inrush", fields))
        self.assertEqual(len(result["findings"]), 1)
        self.assertIn("settling time", result["findings"][0])

    def test_incomplete_sheet_reports_the_fields_and_stops(self):
        fields = _inrush_fields()
        del fields["limiter_resistance_ohm"]
        result = pbi.evaluate_inrush_case(_case("IR-06", "cold_start_inrush", fields))
        self.assertEqual(len(result["findings"]), 1)
        self.assertNotIn("peak_current_a", result)


class UndervoltageTests(unittest.TestCase):
    def test_sag_matches_closed_form(self):
        self.assertAlmostEqual(
            pbi.transient_bus_sag_v(8.0, 2200.0e-6, 2000.0), 0.2893726238, places=9
        )

    def test_sag_scales_linearly_with_the_step(self):
        single = pbi.transient_bus_sag_v(4.0, 2200.0e-6, 2000.0)
        double = pbi.transient_bus_sag_v(8.0, 2200.0e-6, 2000.0)
        self.assertAlmostEqual(double, 2.0 * single, places=12)

    def test_zero_control_bandwidth_raises(self):
        with self.assertRaises(ValueError):
            pbi.transient_bus_sag_v(8.0, 2200.0e-6, 0.0)

    def test_minimum_voltage_matches_closed_form(self):
        self.assertAlmostEqual(
            pbi.minimum_transient_bus_voltage_v(28.0, 8.0, 2200.0e-6, 2000.0, 0.05),
            27.3106273762,
            places=9,
        )

    def test_harness_resistance_deepens_the_dip(self):
        without = pbi.minimum_transient_bus_voltage_v(
            28.0, 8.0, 2200.0e-6, 2000.0, 0.0
        )
        with_harness = pbi.minimum_transient_bus_voltage_v(
            28.0, 8.0, 2200.0e-6, 2000.0, 0.05
        )
        self.assertAlmostEqual(without - with_harness, 0.4, places=9)

    def test_negative_harness_resistance_raises(self):
        with self.assertRaises(ValueError):
            pbi.minimum_transient_bus_voltage_v(
                28.0, 8.0, 2200.0e-6, 2000.0, -0.05
            )

    def test_clean_undervoltage_case_reports_nothing(self):
        result = pbi.evaluate_undervoltage_case(
            _case("UV-01", "load_step_undervoltage", _undervoltage_fields())
        )
        self.assertEqual(result["findings"], [])

    def test_dip_below_the_bus_lower_limit_is_a_finding(self):
        fields = _undervoltage_fields(bus_lower_limit_v=27.5)
        result = pbi.evaluate_undervoltage_case(
            _case("UV-02", "load_step_undervoltage", fields)
        )
        self.assertEqual(len(result["findings"]), 1)
        self.assertIn("bus lower limit", result["findings"][0])

    def test_dip_below_the_payload_lockout_is_a_separate_finding(self):
        fields = _undervoltage_fields(
            bus_lower_limit_v=27.5, payload_undervoltage_lockout_v=27.4
        )
        result = pbi.evaluate_undervoltage_case(
            _case("UV-03", "load_step_undervoltage", fields)
        )
        self.assertEqual(len(result["findings"]), 2)

    def test_limit_exactly_at_the_transient_minimum_is_compliant(self):
        minimum = pbi.minimum_transient_bus_voltage_v(
            28.0, 8.0, 2200.0e-6, 2000.0, 0.05
        )
        fields = _undervoltage_fields(bus_lower_limit_v=minimum)
        result = pbi.evaluate_undervoltage_case(
            _case("UV-04", "load_step_undervoltage", fields)
        )
        self.assertEqual(result["findings"], [])

    def test_limit_one_representation_step_above_is_still_compliant(self):
        minimum = pbi.minimum_transient_bus_voltage_v(
            28.0, 8.0, 2200.0e-6, 2000.0, 0.05
        )
        fields = _undervoltage_fields(bus_lower_limit_v=minimum + 1.0e-12)
        result = pbi.evaluate_undervoltage_case(
            _case("UV-05", "load_step_undervoltage", fields)
        )
        self.assertEqual(result["findings"], [])

    def test_limit_meaningfully_above_the_minimum_is_a_finding(self):
        minimum = pbi.minimum_transient_bus_voltage_v(
            28.0, 8.0, 2200.0e-6, 2000.0, 0.05
        )
        fields = _undervoltage_fields(bus_lower_limit_v=minimum + 0.05)
        result = pbi.evaluate_undervoltage_case(
            _case("UV-06", "load_step_undervoltage", fields)
        )
        self.assertEqual(len(result["findings"]), 1)

    def test_recharge_beyond_the_ride_through_is_a_finding(self):
        fields = _undervoltage_fields(
            source_recovery_current_a=0.2, payload_ride_through_s=1.0e-6
        )
        result = pbi.evaluate_undervoltage_case(
            _case("UV-07", "load_step_undervoltage", fields)
        )
        self.assertEqual(len(result["findings"]), 1)
        self.assertIn("ride-through", result["findings"][0])

    def test_recharge_is_not_computed_without_both_declarations(self):
        fields = _undervoltage_fields(source_recovery_current_a=0.2)
        result = pbi.evaluate_undervoltage_case(
            _case("UV-08", "load_step_undervoltage", fields)
        )
        self.assertIsNone(result["recharge_time_s"])
        self.assertEqual(result["findings"], [])

    def test_incomplete_sheet_reports_the_fields_and_stops(self):
        fields = _undervoltage_fields()
        del fields["control_bandwidth_hz"]
        result = pbi.evaluate_undervoltage_case(
            _case("UV-09", "load_step_undervoltage", fields)
        )
        self.assertEqual(len(result["findings"]), 1)
        self.assertNotIn("sag_v", result)


class FailureCaseTests(unittest.TestCase):
    def test_fault_current_matches_closed_form(self):
        self.assertAlmostEqual(pbi.fault_current_a(28.0, 0.05, 0.15), 140.0, places=9)

    def test_zero_fault_path_raises(self):
        with self.assertRaises(ValueError):
            pbi.fault_current_a(28.0, 0.0, 0.0)

    def test_negative_fault_resistance_raises(self):
        with self.assertRaises(ValueError):
            pbi.fault_current_a(28.0, -0.05, 0.15)

    def test_clearing_time_is_inverse_square_in_the_fault_current(self):
        self.assertAlmostEqual(
            pbi.protection_clearing_time_s(140.0, 5.0, 2.0, 5.0e-5),
            1.02040816e-4,
            places=10,
        )

    def test_clearing_time_is_floored_by_the_device_response(self):
        self.assertAlmostEqual(
            pbi.protection_clearing_time_s(140.0, 5.0, 2.0, 5.0e-4),
            5.0e-4,
            places=12,
        )

    def test_current_at_the_rating_never_clears(self):
        self.assertTrue(
            math.isinf(pbi.protection_clearing_time_s(5.0, 5.0, 2.0, 5.0e-5))
        )

    def test_current_below_the_rating_never_clears(self):
        self.assertTrue(
            math.isinf(pbi.protection_clearing_time_s(4.0, 5.0, 2.0, 5.0e-5))
        )

    def test_let_through_energy_is_current_squared_times_time(self):
        self.assertAlmostEqual(
            pbi.let_through_energy_a2s(140.0, 1.0e-4), 1.96, places=9
        )

    def test_let_through_energy_of_a_non_clearing_fault_raises(self):
        with self.assertRaises(ValueError):
            pbi.let_through_energy_a2s(140.0, math.inf)

    def test_clean_failure_case_reports_nothing(self):
        result = pbi.evaluate_failure_case(
            _case("FC-01", "payload_short_circuit", _failure_fields()),
            ["payload_short_circuit"],
        )
        self.assertEqual(result["findings"], [])
        self.assertAlmostEqual(result["fault_current_a"], 140.0, places=9)

    def test_case_off_the_agreed_list_is_a_finding(self):
        result = pbi.evaluate_failure_case(
            _case("FC-02", "payload_reverse_energy", _failure_fields()),
            ["payload_short_circuit"],
        )
        self.assertEqual(len(result["findings"]), 1)
        self.assertIn("agreed failure", result["findings"][0])

    def test_fault_the_protection_never_clears_is_a_finding(self):
        fields = _failure_fields(fault_resistance_ohm=6.85)
        result = pbi.evaluate_failure_case(
            _case("FC-03", "payload_short_circuit", fields),
            ["payload_short_circuit"],
        )
        self.assertEqual(len(result["findings"]), 1)
        self.assertIn("never cleared", result["findings"][0])

    def test_clearing_time_past_containment_is_a_finding(self):
        fields = _failure_fields(containment_time_s=5.0e-5)
        result = pbi.evaluate_failure_case(
            _case("FC-04", "payload_short_circuit", fields),
            ["payload_short_circuit"],
        )
        self.assertEqual(len(result["findings"]), 1)
        self.assertIn("containment requirement", result["findings"][0])

    def test_let_through_energy_exactly_on_its_allowance_is_compliant(self):
        # 2.5 A2s through a 140 A fault evaluates a few bits above the
        # allowance; the case is physically on the limit.
        fields = _failure_fields(
            protection_i2t_a2s=2.5, allowed_let_through_a2s=2.5
        )
        result = pbi.evaluate_failure_case(
            _case("FC-05", "payload_short_circuit", fields),
            ["payload_short_circuit"],
        )
        self.assertGreater(result["let_through_a2s"], 2.5)
        self.assertEqual(result["findings"], [])

    def test_let_through_energy_past_its_allowance_is_a_finding(self):
        fields = _failure_fields(allowed_let_through_a2s=1.0)
        result = pbi.evaluate_failure_case(
            _case("FC-06", "payload_short_circuit", fields),
            ["payload_short_circuit"],
        )
        self.assertEqual(len(result["findings"]), 1)
        self.assertIn("let-through", result["findings"][0])

    def test_uncategorized_containment_outcome_is_a_finding(self):
        fields = _failure_fields(containment_outcome="looked fine on the scope")
        result = pbi.evaluate_failure_case(
            _case("FC-07", "payload_short_circuit", fields),
            ["payload_short_circuit"],
        )
        self.assertEqual(len(result["findings"]), 1)
        self.assertIn("containment outcome", result["findings"][0])

    def test_agreed_list_that_is_not_a_sequence_raises(self):
        with self.assertRaises(ValueError):
            pbi.evaluate_failure_case(
                _case("FC-08", "payload_short_circuit", _failure_fields()),
                "payload_short_circuit",
            )


class CampaignTests(unittest.TestCase):
    def test_clean_campaign_is_verified(self):
        result = pbi.verify_payload_bus_interaction(_clean_campaign())
        self.assertTrue(result["verified"])
        self.assertEqual(result["coverage_findings"], [])
        self.assertEqual(result["case_findings"], [])

    def test_campaign_reports_case_count_and_families(self):
        result = pbi.verify_payload_bus_interaction(_clean_campaign())
        self.assertEqual(result["case_count"], 3)
        self.assertEqual(
            result["families_covered"],
            ["agreed_failure", "inrush", "undervoltage"],
        )

    def test_missing_family_is_a_coverage_finding(self):
        campaign = _clean_campaign()
        campaign["cases"] = campaign["cases"][:2]
        result = pbi.verify_payload_bus_interaction(campaign)
        self.assertFalse(result["verified"])
        self.assertEqual(len(result["coverage_findings"]), 1)
        self.assertIn("agreed_failure", result["coverage_findings"][0])

    def test_one_failing_case_fails_the_campaign(self):
        campaign = _clean_campaign()
        campaign["cases"][0]["declared_fields"]["allowed_peak_inrush_a"] = 5.0
        result = pbi.verify_payload_bus_interaction(campaign)
        self.assertFalse(result["verified"])
        self.assertEqual(result["coverage_findings"], [])
        self.assertEqual(len(result["case_findings"]), 1)

    def test_duplicate_case_id_raises(self):
        campaign = _clean_campaign()
        campaign["cases"][1]["case_id"] = "IR-01"
        with self.assertRaises(ValueError):
            pbi.verify_payload_bus_interaction(campaign)

    def test_case_without_an_identifier_raises(self):
        campaign = _clean_campaign()
        campaign["cases"][0]["case_id"] = "   "
        with self.assertRaises(ValueError):
            pbi.verify_payload_bus_interaction(campaign)

    def test_empty_case_list_raises(self):
        campaign = _clean_campaign()
        campaign["cases"] = []
        with self.assertRaises(ValueError):
            pbi.verify_payload_bus_interaction(campaign)

    def test_missing_payload_identifier_raises(self):
        campaign = _clean_campaign()
        campaign["payload_id"] = ""
        with self.assertRaises(ValueError):
            pbi.verify_payload_bus_interaction(campaign)

    def test_empty_agreed_failure_list_raises(self):
        campaign = _clean_campaign()
        campaign["agreed_failure_cases"] = []
        with self.assertRaises(ValueError):
            pbi.verify_payload_bus_interaction(campaign)

    def test_agreed_list_naming_a_non_failure_kind_raises(self):
        campaign = _clean_campaign()
        campaign["agreed_failure_cases"] = ["cold_start_inrush"]
        with self.assertRaises(ValueError):
            pbi.verify_payload_bus_interaction(campaign)

    def test_unrecognized_case_kind_raises(self):
        campaign = _clean_campaign()
        campaign["cases"][0]["case_kind"] = "vibration_sweep"
        with self.assertRaises(ValueError):
            pbi.verify_payload_bus_interaction(campaign)

    def test_campaign_that_is_not_a_mapping_raises(self):
        with self.assertRaises(ValueError):
            pbi.verify_payload_bus_interaction(["PLD-IMAGER-A"])


if __name__ == "__main__":
    unittest.main()
