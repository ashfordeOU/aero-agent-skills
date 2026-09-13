#!/usr/bin/env python3
"""Gate 3 contract test for e2007-esd-related-emi-control.

Stdlib unittest, offline, deterministic. Run:
    python3 test_e2007_esd_related_emi_control.py
"""

import math
import unittest

from e2007_esd_related_emi_control_logic import (
    DEFAULT_REQUIRED_MARGIN_DB,
    EVENT_FAMILIES,
    REQUIRED_PROVISIONS,
    arc_pulse,
    assess_esd_emi_control,
    assess_event,
    categorize_event,
    check_transient_compatibility,
    coupled_transient_voltage,
    emi_margin_db,
    missing_provisions,
    worst_case_record,
)


def good_victim(**over):
    victim = {
        "id": "obc-harness",
        "transfer_impedance_ohm_per_m": 0.01,
        "exposed_length_m": 1.5,
        "shield_effectiveness_db": 20.0,
        "susceptibility_threshold_v": 20.0,
    }
    victim.update(over)
    return victim


def good_event(**over):
    event = {
        "id": "esd-01",
        "kind": "surface-arc",
        "capacitance_f": 1.0e-9,
        "breakdown_voltage_v": 1000.0,
        "arc_resistance_ohm": 50.0,
        "provisions": [
            "surface-conductivity-control",
            "chassis-bonding",
            "shield-termination",
        ],
        "victim": good_victim(),
    }
    event.update(over)
    return event


class TestCategorizeEvent(unittest.TestCase):
    def test_surface_arc_family(self):
        self.assertEqual(categorize_event("surface-arc"), "surface-charging-arc")

    def test_blow_off_maps_to_surface_family(self):
        self.assertEqual(categorize_event("blow-off-discharge"), "surface-charging-arc")

    def test_internal_arc_family(self):
        self.assertEqual(categorize_event("deep-dielectric-arc"), "internal-charging-arc")

    def test_triboelectric_family(self):
        self.assertEqual(
            categorize_event("deployment-separation"), "triboelectric-separation-event"
        )

    def test_ground_handling_family(self):
        self.assertEqual(categorize_event("human-body-model"), "ground-handling-event")

    def test_case_and_whitespace_normalised(self):
        self.assertEqual(categorize_event("  Internal-Arc "), "internal-charging-arc")

    def test_every_known_kind_maps_to_a_provision_set(self):
        for kind in EVENT_FAMILIES:
            self.assertIn(categorize_event(kind), REQUIRED_PROVISIONS)

    def test_uncategorized_kind_rejected(self):
        with self.assertRaises(ValueError):
            categorize_event("plasma-wake-arc")

    def test_empty_kind_rejected(self):
        with self.assertRaises(ValueError):
            categorize_event("   ")

    def test_non_string_kind_rejected(self):
        with self.assertRaises(ValueError):
            categorize_event(7)


class TestArcPulse(unittest.TestCase):
    def setUp(self):
        self.pulse = arc_pulse(1.0e-9, 1000.0, 50.0)

    def test_peak_current_is_voltage_over_resistance(self):
        self.assertAlmostEqual(self.pulse["peak_current_a"], 20.0, places=9)

    def test_transferred_charge(self):
        self.assertAlmostEqual(self.pulse["transferred_charge_c"], 1.0e-6, places=12)

    def test_stored_energy(self):
        self.assertAlmostEqual(self.pulse["stored_energy_j"], 5.0e-4, places=10)

    def test_time_constant(self):
        self.assertAlmostEqual(self.pulse["time_constant_s"], 5.0e-8, places=14)

    def test_pulse_duration_is_decay_to_ten_percent(self):
        self.assertAlmostEqual(
            self.pulse["pulse_duration_s"], 5.0e-8 * math.log(10.0), places=14
        )

    def test_corner_frequency(self):
        self.assertAlmostEqual(
            self.pulse["corner_frequency_hz"], 1.0 / (2.0 * math.pi * 5.0e-8), places=3
        )

    def test_smaller_capacitance_raises_corner_frequency(self):
        lower = arc_pulse(1.0e-9, 1000.0, 50.0)["corner_frequency_hz"]
        higher = arc_pulse(1.0e-10, 1000.0, 50.0)["corner_frequency_hz"]
        self.assertGreater(higher, lower)

    def test_zero_capacitance_rejected(self):
        with self.assertRaises(ValueError):
            arc_pulse(0.0, 1000.0, 50.0)

    def test_negative_voltage_rejected(self):
        with self.assertRaises(ValueError):
            arc_pulse(1.0e-9, -1000.0, 50.0)

    def test_zero_resistance_rejected(self):
        with self.assertRaises(ValueError):
            arc_pulse(1.0e-9, 1000.0, 0.0)

    def test_non_numeric_rejected(self):
        with self.assertRaises(ValueError):
            arc_pulse("1n", 1000.0, 50.0)

    def test_non_finite_rejected(self):
        with self.assertRaises(ValueError):
            arc_pulse(float("inf"), 1000.0, 50.0)


class TestCoupledTransient(unittest.TestCase):
    def test_unshielded_open_circuit_value(self):
        self.assertAlmostEqual(
            coupled_transient_voltage(20.0, 0.01, 1.5, 0.0), 0.3, places=12
        )

    def test_twenty_db_shield_divides_by_ten(self):
        self.assertAlmostEqual(
            coupled_transient_voltage(20.0, 0.01, 1.5, 20.0), 0.03, places=12
        )

    def test_shield_effectiveness_is_monotonic(self):
        low = coupled_transient_voltage(20.0, 0.01, 1.5, 10.0)
        high = coupled_transient_voltage(20.0, 0.01, 1.5, 40.0)
        self.assertLess(high, low)

    def test_zero_current_rejected(self):
        with self.assertRaises(ValueError):
            coupled_transient_voltage(0.0, 0.01, 1.5, 20.0)

    def test_negative_transfer_impedance_rejected(self):
        with self.assertRaises(ValueError):
            coupled_transient_voltage(20.0, -0.01, 1.5, 20.0)

    def test_zero_length_rejected(self):
        with self.assertRaises(ValueError):
            coupled_transient_voltage(20.0, 0.01, 0.0, 20.0)

    def test_negative_shield_effectiveness_rejected(self):
        with self.assertRaises(ValueError):
            coupled_transient_voltage(20.0, 0.01, 1.5, -3.0)


class TestEmiMargin(unittest.TestCase):
    def test_factor_of_ten_is_twenty_db(self):
        self.assertAlmostEqual(emi_margin_db(20.0, 2.0), 20.0, places=9)

    def test_exceeded_threshold_gives_negative_margin(self):
        self.assertLess(emi_margin_db(1.0, 10.0), 0.0)

    def test_zero_coupled_voltage_rejected(self):
        with self.assertRaises(ValueError):
            emi_margin_db(20.0, 0.0)

    def test_negative_threshold_rejected(self):
        with self.assertRaises(ValueError):
            emi_margin_db(-20.0, 2.0)


class TestTransientCompatibility(unittest.TestCase):
    def test_comfortable_case_is_compliant(self):
        out = check_transient_compatibility(20.0, 0.03)
        self.assertTrue(out["compliant"])
        self.assertAlmostEqual(out["shortfall_db"], 0.0, places=12)

    def test_exactly_on_limit_case_is_compliant(self):
        coupled = coupled_transient_voltage(20.0, 0.01, 1.5, 20.0)
        threshold = coupled * (10.0 ** (DEFAULT_REQUIRED_MARGIN_DB / 20.0))
        out = check_transient_compatibility(threshold, coupled)
        self.assertAlmostEqual(out["achieved_margin_db"], DEFAULT_REQUIRED_MARGIN_DB, places=9)
        self.assertTrue(out["compliant"])

    def test_short_case_reports_shortfall(self):
        out = check_transient_compatibility(0.05, 0.03)
        self.assertFalse(out["compliant"])
        self.assertGreater(out["shortfall_db"], 0.0)

    def test_custom_required_margin_honoured(self):
        out = check_transient_compatibility(20.0, 0.03, required_margin_db=60.0)
        self.assertFalse(out["compliant"])

    def test_negative_required_margin_rejected(self):
        with self.assertRaises(ValueError):
            check_transient_compatibility(20.0, 0.03, required_margin_db=-1.0)


class TestProvisions(unittest.TestCase):
    def test_complete_provision_set_has_no_gaps(self):
        self.assertEqual(
            missing_provisions(
                "surface-charging-arc",
                ["surface-conductivity-control", "chassis-bonding", "shield-termination"],
            ),
            (),
        )

    def test_gap_is_reported(self):
        gaps = missing_provisions("internal-charging-arc", ["chassis-bonding"])
        self.assertIn("dielectric-shielding-control", gaps)
        self.assertIn("transient-filtering", gaps)

    def test_provision_matching_is_case_insensitive(self):
        self.assertEqual(
            missing_provisions(
                "triboelectric-separation-event",
                ["Static-Dissipative-Material", " CHASSIS-BONDING "],
            ),
            (),
        )

    def test_unknown_family_rejected(self):
        with self.assertRaises(ValueError):
            missing_provisions("plasma-family", ["chassis-bonding"])

    def test_bare_string_provision_list_rejected(self):
        with self.assertRaises(ValueError):
            missing_provisions("surface-charging-arc", "chassis-bonding")

    def test_non_string_provision_entry_rejected(self):
        with self.assertRaises(ValueError):
            missing_provisions("surface-charging-arc", ["chassis-bonding", 3])


class TestAssessEvent(unittest.TestCase):
    def test_good_event_is_compliant(self):
        record = assess_event(good_event())
        self.assertTrue(record["compliant"])
        self.assertEqual(record["family"], "surface-charging-arc")
        self.assertEqual(record["findings"], ())

    def test_coupled_voltage_matches_hand_calculation(self):
        record = assess_event(good_event())
        self.assertAlmostEqual(record["coupled_voltage_v"], 0.03, places=12)

    def test_missing_provision_produces_a_finding(self):
        record = assess_event(good_event(provisions=["chassis-bonding"]))
        self.assertFalse(record["compliant"])
        self.assertEqual(len(record["missing_provisions"]), 2)

    def test_susceptible_victim_produces_a_finding(self):
        record = assess_event(
            good_event(victim=good_victim(susceptibility_threshold_v=0.031))
        )
        self.assertFalse(record["compliant"])
        self.assertTrue(any("emi-margin" in f for f in record["findings"]))

    def test_missing_event_key_rejected(self):
        broken = good_event()
        del broken["arc_resistance_ohm"]
        with self.assertRaises(ValueError):
            assess_event(broken)

    def test_missing_victim_key_rejected(self):
        victim = good_victim()
        del victim["exposed_length_m"]
        with self.assertRaises(ValueError):
            assess_event(good_event(victim=victim))

    def test_non_mapping_event_rejected(self):
        with self.assertRaises(ValueError):
            assess_event(["esd-01"])


class TestAssessCampaign(unittest.TestCase):
    def setUp(self):
        self.events = [
            good_event(),
            good_event(
                id="esd-02",
                kind="human-body-model",
                capacitance_f=100.0e-12,
                breakdown_voltage_v=4000.0,
                arc_resistance_ohm=1500.0,
                provisions=[
                    "controlled-handling-area",
                    "operator-bonding",
                    "transient-filtering",
                ],
                victim=good_victim(id="pcdu-harness", shield_effectiveness_db=30.0),
            ),
        ]

    def test_all_clean_campaign_is_compliant(self):
        out = assess_esd_emi_control(self.events)
        self.assertTrue(out["compliant"])
        self.assertEqual(out["event_count"], 2)
        self.assertEqual(out["findings"], ())

    def test_driving_event_is_the_worst_margin(self):
        out = assess_esd_emi_control(self.events)
        margins = {r["event_id"]: r["margin"]["achieved_margin_db"] for r in out["records"]}
        self.assertEqual(out["driving_event_id"], min(margins, key=margins.get))
        self.assertAlmostEqual(out["worst_margin_db"], min(margins.values()), places=12)

    def test_one_bad_event_fails_the_campaign(self):
        bad = good_event(id="esd-03", provisions=[])
        out = assess_esd_emi_control(self.events + [bad])
        self.assertFalse(out["compliant"])
        self.assertEqual(len(out["findings"]), 3)

    def test_empty_campaign_rejected(self):
        with self.assertRaises(ValueError):
            assess_esd_emi_control([])

    def test_duplicate_event_id_rejected(self):
        with self.assertRaises(ValueError):
            assess_esd_emi_control([good_event(), good_event()])

    def test_blank_event_id_rejected(self):
        with self.assertRaises(ValueError):
            assess_esd_emi_control([good_event(id="  ")])

    def test_non_iterable_campaign_rejected(self):
        with self.assertRaises(ValueError):
            assess_esd_emi_control(good_event())

    def test_repeat_run_is_deterministic(self):
        first = assess_esd_emi_control(self.events)
        second = assess_esd_emi_control(self.events)
        self.assertEqual(first["findings"], second["findings"])
        self.assertAlmostEqual(first["worst_margin_db"], second["worst_margin_db"], places=12)

    def test_worst_case_record_needs_records(self):
        with self.assertRaises(ValueError):
            worst_case_record([])


if __name__ == "__main__":
    unittest.main()
