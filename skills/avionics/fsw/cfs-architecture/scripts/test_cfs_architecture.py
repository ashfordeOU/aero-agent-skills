#!/usr/bin/env python3
"""Gate 3 contract test: cFS architecture simulation logic.

Runs with the stdlib unittest runner only; fully offline and
deterministic. Exercises scripts/cfs_architecture_logic.py:
SoftwareBus register/subscribe/publish/route with 16-bit message IDs,
publish-order delivery isolation between apps, unknown message ID
rejection, EventLog severity filtering, the telemetry pipeline sequence
counters, and the classic app skeleton.

Run: python3 test_cfs_architecture.py
"""

import os
import sys
import unittest

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import cfs_architecture_logic as cfs  # noqa: E402


class SoftwareBusIsolationTests(unittest.TestCase):
    """Contract: two apps on different message IDs get only their own
    messages, in publish order."""

    def test_two_apps_receive_only_their_messages_in_publish_order(self):
        bus = cfs.SoftwareBus()
        bus.register_app("ACS")
        bus.register_app("EPS")
        bus.subscribe("ACS", 0x1900)  # app 0x19, message 0x00
        bus.subscribe("EPS", 0x1901)  # app 0x19, message 0x01

        bus.publish(0x1900, {"cmd": "rate_damp"})
        bus.publish(0x1901, {"cmd": "battery_charge"})
        bus.publish(0x1900, {"cmd": "slew"})
        bus.publish(0x1901, {"cmd": "heater_off"})

        routed = bus.route_messages()

        acs = bus.deliveries("ACS")
        eps = bus.deliveries("EPS")
        self.assertEqual(routed, 4)
        # Each app sees only its own message ID.
        self.assertTrue(all(mid == 0x1900 for _, mid, _ in acs))
        self.assertTrue(all(mid == 0x1901 for _, mid, _ in eps))
        # Payloads arrive in publish order, interleaved on the bus.
        self.assertEqual(
            [p for _, _, p in acs], [{"cmd": "rate_damp"}, {"cmd": "slew"}]
        )
        self.assertEqual(
            [p for _, _, p in eps],
            [{"cmd": "battery_charge"}, {"cmd": "heater_off"}],
        )

    def test_delivery_order_matches_publish_order_across_apps(self):
        bus = cfs.SoftwareBus()
        bus.register_app("A")
        bus.register_app("B")
        bus.subscribe("A", 0x2000)
        bus.subscribe("B", 0x2001)

        for i in range(3):
            bus.publish(0x2000, "a%d" % i)
            bus.publish(0x2001, "b%d" % i)
        bus.route_messages()

        self.assertEqual(
            [p for _, _, p in bus.deliveries("A")], ["a0", "a1", "a2"]
        )
        self.assertEqual(
            [p for _, _, p in bus.deliveries("B")], ["b0", "b1", "b2"]
        )

    def test_unknown_msg_id_publish_raises_value_error(self):
        bus = cfs.SoftwareBus()
        bus.register_app("A")
        bus.subscribe("A", 0x1900)
        # 0x1902 has no subscribers: publishing to it is an error.
        with self.assertRaises(ValueError):
            bus.publish(0x1902, {"cmd": "nobody_listens"})
        self.assertEqual(bus.pending(), 0)

    def test_out_of_range_msg_id_rejected(self):
        bus = cfs.SoftwareBus()
        bus.register_app("A")
        for bad in (-1, 0x10000, 65536):
            with self.assertRaises(ValueError):
                bus.subscribe("A", bad)
            with self.assertRaises(ValueError):
                bus.publish(bad, "x")

    def test_non_integer_msg_id_rejected(self):
        bus = cfs.SoftwareBus()
        bus.register_app("A")
        for bad in ("0x1900", 3.5, None, True):
            with self.assertRaises(ValueError):
                bus.subscribe("A", bad)

    def test_duplicate_register_raises_value_error(self):
        bus = cfs.SoftwareBus()
        bus.register_app("ACS")
        with self.assertRaises(ValueError):
            bus.register_app("ACS")

    def test_subscribe_unregistered_app_raises_value_error(self):
        bus = cfs.SoftwareBus()
        with self.assertRaises(ValueError):
            bus.subscribe("GHOST", 0x1900)

    def test_multiple_subscribers_receive_same_message(self):
        bus = cfs.SoftwareBus()
        bus.register_app("GNC")
        bus.register_app("FDIR")
        bus.subscribe("GNC", 0x1900)
        bus.subscribe("FDIR", 0x1900)
        bus.publish(0x1900, {"cmd": "slew"})
        bus.route_messages()
        self.assertEqual(len(bus.deliveries("GNC")), 1)
        self.assertEqual(len(bus.deliveries("FDIR")), 1)
        self.assertEqual(bus.subscribers(0x1900), ["GNC", "FDIR"])


class EventLogTests(unittest.TestCase):
    """Contract: event service log records severity-flagged entries."""

    def test_severity_levels_recorded_in_order(self):
        log = cfs.EventLog()
        log.log("ACS", "INFO", "started")
        log.log("ACS", "ERROR", "sensor fault")
        log.log("FDIR", "CRITICAL", "attitude excursion")
        self.assertEqual(len(log), 3)
        self.assertEqual(
            [e["severity"] for e in log.entries()],
            ["INFO", "ERROR", "CRITICAL"],
        )

    def test_severity_filtering(self):
        log = cfs.EventLog()
        log.log("ACS", "DEBUG", "loop tick")
        log.log("ACS", "ERROR", "sensor fault")
        log.log("EPS", "ERROR", "undervoltage")
        self.assertEqual(log.count(severity="ERROR"), 2)
        self.assertEqual(log.count(severity="DEBUG"), 1)
        self.assertEqual(
            [e["app"] for e in log.entries(severity="ERROR")],
            ["ACS", "EPS"],
        )

    def test_invalid_severity_raises_value_error(self):
        log = cfs.EventLog()
        with self.assertRaises(ValueError):
            log.log("ACS", "WARN", "not a cFS severity")


class TelemetryPipelineTests(unittest.TestCase):
    """Contract: telemetry pipeline stamps sequence counters."""

    def test_telemetry_pipeline_stamps_sequence_counters(self):
        bus = cfs.SoftwareBus()
        bus.register_app("GNC")
        bus.register_app("TEL")
        bus.subscribe("TEL", 0x1902)  # telemetry msg id, app 0x19 msg 0x02

        stamped = cfs.telemetry_pipeline(
            bus, "GNC", 0x1902, ["quat1", "quat2", "quat3"]
        )

        self.assertEqual([s for _, _, s in stamped], [0, 1, 2])
        self.assertTrue(all(mid == 0x1902 for mid, _, _ in stamped))
        # Subscriber received the stamped telemetry in publish order.
        received = bus.deliveries("TEL")
        self.assertEqual(
            [p["seq"] for _, _, p in received], [0, 1, 2]
        )
        self.assertEqual(
            [p["data"] for _, _, p in received],
            ["quat1", "quat2", "quat3"],
        )

    def test_telemetry_pipeline_start_seq_offset(self):
        bus = cfs.SoftwareBus()
        bus.register_app("GNC")
        bus.register_app("TEL")
        bus.subscribe("TEL", 0x1902)
        stamped = cfs.telemetry_pipeline(
            bus, "GNC", 0x1902, ["a", "b"], start_seq=7
        )
        self.assertEqual([s for _, _, s in stamped], [7, 8])


class AppSkeletonTests(unittest.TestCase):
    """Contract: the classic APP_Init / APP_Execute / APP_Data pattern."""

    def test_template_contains_classic_lifecycle_methods(self):
        tpl = cfs.app_skeleton_template()
        for method in ("APP_Init", "APP_Execute", "APP_Data"):
            self.assertIn(method, tpl)
        self.assertIn("register_app", tpl)
        self.assertIn("subscribe", tpl)

    def test_scheduled_app_publishes_telemetry_on_period(self):
        bus = cfs.SoftwareBus()
        gnc = cfs.ScheduledTelemetryApp(
            "GNC", bus, cmd_msg_id=0x1800, tlm_msg_id=0x1902, period=2
        )
        bus.register_app("TEL")
        bus.subscribe("TEL", 0x1902)
        gnc.APP_Init()

        for _ in range(5):  # cycles 0..4
            gnc.APP_Execute()
        bus.route_messages()  # flush the final publish

        received = bus.deliveries("TEL")
        self.assertEqual(len(received), 3)  # cycles 0, 2, 4
        self.assertEqual([p["seq"] for _, _, p in received], [0, 1, 2])
        self.assertEqual(
            [p["cycle"] for _, _, p in received], [0, 2, 4]
        )


if __name__ == "__main__":
    unittest.main(verbosity=2)
