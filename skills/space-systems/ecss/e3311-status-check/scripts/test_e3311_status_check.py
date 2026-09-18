"""Contract test for the e3311 status-check leaf (stdlib unittest)."""

import math
import unittest

from e3311_status_check_logic import (
    ARMING_PHASES,
    DEFAULT_STATUS_POLICY,
    VERDICT_MET,
    VERDICT_NOT_MET,
    assess_barrier_agreement,
    assess_indication_availability,
    assess_indication_independence,
    assess_monitor_current,
    assess_status_check,
    monitor_current_margin_db,
    resolve_indicated_state,
    validate_channel,
    validate_channels,
    validate_status_policy,
)


def channel(cid="CH-A", principle="mechanical-microswitch", source="bus-a", **kw):
    record = {
        "id": cid,
        "principle": principle,
        "power_source": source,
        "reading": "safe",
        "monitor_current_a": 0.005,
    }
    record.update(kw)
    return record


def channels(**kw):
    pair = [
        channel("CH-A", "mechanical-microswitch", "bus-a"),
        channel("CH-B", "magnetic-proximity", "bus-b"),
    ]
    if kw.get("reading"):
        for record in pair:
            record["reading"] = kw["reading"]
    return pair


def availability(**kw):
    phases = {phase: True for phase in ARMING_PHASES}
    phases.update(kw)
    return phases


def full_case(**kw):
    case = {
        "no_fire_current_a": 1.0,
        "channels": channels(),
        "barrier_position": "barrier-interposed",
        "availability": availability(),
    }
    case.update(kw)
    return case


class TestPolicyValidation(unittest.TestCase):
    def test_default_policy_is_valid(self):
        self.assertIs(
            validate_status_policy(DEFAULT_STATUS_POLICY), DEFAULT_STATUS_POLICY
        )

    def test_non_mapping_policy_raises(self):
        with self.assertRaises(ValueError):
            validate_status_policy(("minimum_channels", 2))

    def test_zero_minimum_channels_raises(self):
        with self.assertRaises(ValueError):
            validate_status_policy(dict(DEFAULT_STATUS_POLICY, minimum_channels=0))

    def test_a_boolean_channel_count_raises(self):
        with self.assertRaises(ValueError):
            validate_status_policy(dict(DEFAULT_STATUS_POLICY, minimum_channels=True))

    def test_a_monitor_fraction_at_unity_raises(self):
        with self.assertRaises(ValueError):
            validate_status_policy(
                dict(DEFAULT_STATUS_POLICY, monitor_current_fraction=1.0)
            )

    def test_more_principles_than_channels_raises(self):
        with self.assertRaises(ValueError):
            validate_status_policy(
                dict(
                    DEFAULT_STATUS_POLICY,
                    minimum_channels=1,
                    distinct_principles_required=2,
                )
            )

    def test_an_unknown_required_phase_raises(self):
        with self.assertRaises(ValueError):
            validate_status_policy(
                dict(DEFAULT_STATUS_POLICY, required_phases=("after-flight",))
            )


class TestChannelValidation(unittest.TestCase):
    def test_a_valid_channel_normalizes(self):
        record = validate_channel(channel())
        self.assertEqual(record["id"], "CH-A")
        self.assertFalse(record["routed_through_initiation_circuit"])

    def test_an_empty_id_raises(self):
        with self.assertRaises(ValueError):
            validate_channel(channel(""))

    def test_an_unknown_principle_raises(self):
        with self.assertRaises(ValueError):
            validate_channel(channel(principle="operator-opinion"))

    def test_an_unknown_reading_raises(self):
        with self.assertRaises(ValueError):
            validate_channel(channel(reading="probably-safe"))

    def test_a_blank_power_source_raises(self):
        with self.assertRaises(ValueError):
            validate_channel(channel(source="  "))

    def test_a_negative_monitor_current_raises(self):
        with self.assertRaises(ValueError):
            validate_channel(channel(monitor_current_a=-0.001))

    def test_a_non_boolean_routing_flag_raises(self):
        with self.assertRaises(ValueError):
            validate_channel(channel(routed_through_initiation_circuit="yes"))

    def test_duplicate_channel_ids_raise(self):
        with self.assertRaises(ValueError):
            validate_channels([channel("CH-A"), channel("CH-A", "magnetic-proximity", "bus-b")])

    def test_an_empty_channel_list_raises(self):
        with self.assertRaises(ValueError):
            validate_channels([])

    def test_a_non_list_channel_set_raises(self):
        with self.assertRaises(ValueError):
            validate_channels(channel())


class TestStateResolution(unittest.TestCase):
    def test_unanimous_channels_resolve(self):
        result = resolve_indicated_state(channels())
        self.assertEqual(result["state"], "safe")
        self.assertTrue(result["unanimous"])

    def test_unanimous_armed_channels_resolve_armed(self):
        result = resolve_indicated_state(channels(reading="armed"))
        self.assertEqual(result["state"], "armed")

    def test_disagreeing_channels_resolve_indeterminate(self):
        pair = channels()
        pair[1]["reading"] = "armed"
        result = resolve_indicated_state(pair)
        self.assertEqual(result["state"], "indeterminate")
        self.assertFalse(result["unanimous"])

    def test_a_silent_channel_forces_indeterminate_even_when_others_agree(self):
        pair = channels()
        pair[1]["reading"] = "no-signal"
        result = resolve_indicated_state(pair)
        self.assertEqual(result["state"], "indeterminate")
        self.assertEqual(result["silent_channels"], ["CH-B"])

    def test_every_reading_is_reported_by_channel(self):
        result = resolve_indicated_state(channels())
        self.assertEqual(sorted(result["readings"]), ["CH-A", "CH-B"])

    def test_an_in_transit_agreement_resolves_in_transit(self):
        result = resolve_indicated_state(channels(reading="in-transit"))
        self.assertEqual(result["state"], "in-transit")


class TestMonitorCurrent(unittest.TestCase):
    def test_a_low_monitoring_current_passes(self):
        result = assess_monitor_current(1.0, channels())
        self.assertTrue(result["compliant"])
        self.assertAlmostEqual(result["allowed_current_a"], 0.1, places=12)

    def test_a_current_exactly_on_the_allowance_passes(self):
        pair = channels()
        pair[0]["monitor_current_a"] = 0.1
        result = assess_monitor_current(1.0, pair)
        self.assertTrue(result["compliant"])

    def test_an_excessive_current_fails_and_names_the_channel(self):
        pair = channels()
        pair[0]["monitor_current_a"] = 0.4
        result = assess_monitor_current(1.0, pair)
        self.assertFalse(result["compliant"])
        self.assertFalse(result["channels"]["CH-A"]["compliant"])
        self.assertTrue(result["channels"]["CH-B"]["compliant"])

    def test_a_zero_current_channel_reports_an_infinite_margin(self):
        pair = channels()
        pair[0]["monitor_current_a"] = 0.0
        result = assess_monitor_current(1.0, pair)
        self.assertTrue(math.isinf(result["channels"]["CH-A"]["margin_db"]))

    def test_routing_through_the_initiation_circuit_is_a_finding(self):
        pair = channels()
        pair[0]["routed_through_initiation_circuit"] = True
        result = assess_monitor_current(1.0, pair)
        self.assertFalse(result["compliant"])

    def test_the_margin_uses_the_voltage_decade(self):
        self.assertAlmostEqual(monitor_current_margin_db(1.0, 0.1), 20.0, places=9)

    def test_a_zero_no_fire_current_raises(self):
        with self.assertRaises(ValueError):
            assess_monitor_current(0.0, channels())


class TestIndependence(unittest.TestCase):
    def test_two_distinct_channels_pass(self):
        result = assess_indication_independence(channels())
        self.assertTrue(result["compliant"])

    def test_a_single_channel_fails_the_count_and_the_principles(self):
        result = assess_indication_independence([channel("CH-A")])
        self.assertFalse(result["compliant"])
        self.assertGreaterEqual(len(result["findings"]), 2)

    def test_a_shared_sensing_principle_fails(self):
        pair = [
            channel("CH-A", "mechanical-microswitch", "bus-a"),
            channel("CH-B", "mechanical-microswitch", "bus-b"),
        ]
        result = assess_indication_independence(pair)
        self.assertFalse(result["compliant"])
        self.assertEqual(result["distinct_principles"], ["mechanical-microswitch"])

    def test_a_shared_power_source_fails(self):
        pair = [
            channel("CH-A", "mechanical-microswitch", "bus-a"),
            channel("CH-B", "magnetic-proximity", "bus-a"),
        ]
        result = assess_indication_independence(pair)
        self.assertFalse(result["compliant"])
        self.assertEqual(result["distinct_power_sources"], ["bus-a"])

    def test_the_channel_count_is_reported(self):
        result = assess_indication_independence(channels())
        self.assertEqual(result["channel_count"], 2)


class TestBarrierAgreement(unittest.TestCase):
    def test_safe_agrees_with_an_interposed_barrier(self):
        result = assess_barrier_agreement("safe", "barrier-interposed")
        self.assertTrue(result["compliant"])

    def test_armed_agrees_with_an_aligned_barrier(self):
        result = assess_barrier_agreement("armed", "barrier-aligned")
        self.assertTrue(result["compliant"])

    def test_safe_against_an_aligned_barrier_fails(self):
        result = assess_barrier_agreement("safe", "barrier-aligned")
        self.assertFalse(result["compliant"])
        self.assertEqual(result["expected_barrier_position"], "barrier-interposed")

    def test_an_indeterminate_indication_cannot_agree(self):
        result = assess_barrier_agreement("indeterminate", "barrier-interposed")
        self.assertFalse(result["compliant"])
        self.assertIsNone(result["expected_barrier_position"])

    def test_an_unknown_barrier_position_raises(self):
        with self.assertRaises(ValueError):
            assess_barrier_agreement("safe", "barrier-missing")

    def test_an_unknown_indicated_state_raises(self):
        with self.assertRaises(ValueError):
            assess_barrier_agreement("probably-safe", "barrier-interposed")


class TestAvailability(unittest.TestCase):
    def test_a_complete_phase_set_passes(self):
        result = assess_indication_availability(availability())
        self.assertTrue(result["compliant"])

    def test_a_gap_during_arming_is_named(self):
        result = assess_indication_availability(availability(**{"during-arming": False}))
        self.assertFalse(result["compliant"])
        self.assertEqual(result["unavailable_phases"], ["during-arming"])

    def test_an_undeclared_phase_raises(self):
        phases = availability()
        del phases["after-arming"]
        with self.assertRaises(ValueError):
            assess_indication_availability(phases)

    def test_an_unknown_phase_key_raises(self):
        with self.assertRaises(ValueError):
            assess_indication_availability(availability(**{"after-flight": True}))

    def test_a_non_mapping_phase_set_raises(self):
        with self.assertRaises(ValueError):
            assess_indication_availability(["before-arming"])


class TestFullAssessment(unittest.TestCase):
    def test_a_sound_indication_is_met(self):
        report = assess_status_check(full_case())
        self.assertEqual(report["verdict"], VERDICT_MET)
        self.assertEqual(report["failed_checks"], [])
        self.assertEqual(report["indicated_state"], "safe")

    def test_disagreeing_channels_break_the_barrier_check(self):
        case = full_case()
        case["channels"][1]["reading"] = "armed"
        report = assess_status_check(case)
        self.assertEqual(report["verdict"], VERDICT_NOT_MET)
        self.assertEqual(report["failed_checks"], ["barrier-agreement"])
        self.assertEqual(report["indicated_state"], "indeterminate")

    def test_a_shared_power_source_breaks_independence_alone(self):
        case = full_case()
        case["channels"][1]["power_source"] = "bus-a"
        report = assess_status_check(case)
        self.assertEqual(report["failed_checks"], ["independence"])

    def test_several_failures_are_all_named_in_order(self):
        case = full_case()
        case["channels"][1]["power_source"] = "bus-a"
        case["availability"] = availability(**{"during-arming": False})
        report = assess_status_check(case)
        self.assertEqual(report["failed_checks"], ["independence", "availability"])

    def test_every_check_appears_in_the_report(self):
        report = assess_status_check(full_case())
        for name in (
            "independence",
            "monitor-current",
            "barrier-agreement",
            "availability",
        ):
            self.assertIn(name, report["checks"])

    def test_a_non_mapping_case_raises(self):
        with self.assertRaises(ValueError):
            assess_status_check("safe")

    def test_a_missing_barrier_position_raises(self):
        case = full_case()
        del case["barrier_position"]
        with self.assertRaises(ValueError):
            assess_status_check(case)


if __name__ == "__main__":
    unittest.main()
