#!/usr/bin/env python3
"""Gate 3 contract test: F Prime (F´) component framework model.

Runs with the stdlib unittest runner only; fully offline and
deterministic. Exercises scripts/fprime_component_logic.py:
component validation rules (opcodes, ports, kinds, telemetry types,
event severities, active input rule, passive no-command rule),
connection validation (type match, dangling refs, direction,
self-loops, serial interfaces), rate group schedule validation
(dispatch driver coverage, passive double invocation warnings), the
deterministic clocked dispatch simulation (invocations, deliveries,
telemetry sequence counters, command log, event log), and the scaffold
manifest generator.

Run: python3 test_fprime_component.py
"""

import os
import sys
import unittest

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import fprime_component_logic as fprime  # noqa: E402


def signal_gen_defn():
    """Worked example producer: active, 1 Hz run port, U32 output."""
    return fprime.component(
        "SignalGen", "active",
        ports=[
            {"direction": "input", "name": "run", "data_type": "U32"},
            {"direction": "output", "name": "tlmOut", "data_type": "U32"},
        ],
        commands=[{"name": "reset", "opcode": 0x01}],
        events=[{"name": "started", "severity": "INFO"},
                {"name": "fault", "severity": "HIGH"}],
    )


def data_logger_defn(dtype="U32"):
    """Worked example consumer: queued logger with a U32 log channel."""
    return fprime.component(
        "DataLogger", "queued",
        ports=[{"direction": "input", "name": "logIn", "data_type": dtype}],
        telemetry=[{"name": "logIn", "type": dtype}],
    )


def worked_example():
    """The leaf worked example: SignalGen.tlmOut -> DataLogger.logIn."""
    defs = [signal_gen_defn(), data_logger_defn()]
    conns = [fprime.conn("SignalGen", "tlmOut", "DataLogger", "logIn")]
    groups = [fprime.rate_group("1Hz", 1.0, [("SignalGen", "run")])]
    return defs, conns, groups


class ComponentValidationTests(unittest.TestCase):
    """Contract: component definitions follow the stated model rules."""

    def test_worked_example_components_are_clean(self):
        self.assertEqual(fprime.validate_component(signal_gen_defn()), [])
        self.assertEqual(fprime.validate_component(data_logger_defn()), [])

    def test_missing_name_reported(self):
        issues = fprime.validate_component({"kind": "passive"})
        self.assertTrue(any("component missing name" in i for i in issues))

    def test_unsupported_kind_reported(self):
        defn = fprime.component("X", "reactive")
        self.assertIn("unsupported kind 'reactive'",
                      fprime.validate_component(defn)[0])

    def test_duplicate_port_names_reported(self):
        defn = fprime.component(
            "X", "passive",
            ports=[
                {"direction": "input", "name": "inA", "data_type": "U32"},
                {"direction": "output", "name": "inA", "data_type": "U32"},
            ],
        )
        issues = fprime.validate_component(defn)
        self.assertTrue(any("duplicate port name 'inA'" in i
                            for i in issues))

    def test_port_direction_type_and_serial_rules(self):
        defn = fprime.component(
            "X", "passive",
            ports=[{"direction": "sideways", "name": "p1",
                    "data_type": "U32"}],
        )
        issues = fprime.validate_component(defn)
        self.assertTrue(any("direction must be input or output" in i
                            for i in issues))
        defn2 = fprime.component(
            "X", "passive",
            ports=[{"direction": "input", "name": "p1",
                    "data_type": "INT64"}],
        )
        issues2 = fprime.validate_component(defn2)
        self.assertTrue(any("unsupported data type 'INT64'" in i
                            for i in issues2))
        # A serial interface port is a legal passive declaration.
        defn3 = fprime.component(
            "X", "passive",
            ports=[{"direction": "input", "name": "serIn",
                    "data_type": "serial"}],
        )
        self.assertEqual(fprime.validate_component(defn3), [])

    def test_duplicate_command_opcode_and_name_reported(self):
        defn = fprime.component(
            "SignalGen", "active",
            ports=[{"direction": "input", "name": "run",
                    "data_type": "U32"}],
            commands=[{"name": "reset", "opcode": 0x01},
                      {"name": "reboot", "opcode": 0x01}],
        )
        issues = fprime.validate_component(defn)
        self.assertTrue(any(
            "duplicate command opcode 0x0001 (commands 'reset' and 'reboot')"
            in i for i in issues))
        # Same name on two opcodes is equally an error.
        defn2 = fprime.component(
            "SignalGen", "active",
            ports=[{"direction": "input", "name": "run",
                    "data_type": "U32"}],
            commands=[{"name": "reset", "opcode": 0x01},
                      {"name": "reset", "opcode": 0x02}],
        )
        issues2 = fprime.validate_component(defn2)
        self.assertTrue(any("duplicate command name 'reset'" in i
                            for i in issues2))

    def test_out_of_range_opcode_reported(self):
        for bad in (-1, 0x10000, "1", True):
            defn = fprime.component(
                "X", "active",
                ports=[{"direction": "input", "name": "run",
                        "data_type": "U32"}],
                commands=[{"name": "reset", "opcode": bad}],
            )
            issues = fprime.validate_component(defn)
            self.assertTrue(any("opcode" in i and "out of range" in i
                                for i in issues),
                            "expected opcode issue for %r" % (bad,))

    def test_telemetry_channel_rules(self):
        defn = fprime.component(
            "X", "passive",
            telemetry=[{"name": "volt", "type": "REAL"},
                       {"name": "volt", "type": "U32"}],
        )
        issues = fprime.validate_component(defn)
        self.assertTrue(any("unsupported type 'REAL'" in i for i in issues))
        self.assertTrue(any("duplicate telemetry channel name 'volt'" in i
                            for i in issues))

    def test_bad_event_severity_reported(self):
        defn = fprime.component(
            "X", "passive",
            events=[{"name": "warn", "severity": "WARNING"}],
        )
        issues = fprime.validate_component(defn)
        self.assertTrue(any(
            "event 'warn' unsupported severity 'WARNING'" in i
            for i in issues))

    def test_active_without_input_port_reported(self):
        defn = fprime.component(
            "SignalGen", "active",
            ports=[{"direction": "output", "name": "tlmOut",
                    "data_type": "U32"}],
        )
        issues = fprime.validate_component(defn)
        self.assertTrue(any(
            "active components must declare at least one input port" in i
            for i in issues))

    def test_passive_with_commands_reported(self):
        defn = fprime.component(
            "Sink", "passive",
            ports=[{"direction": "input", "name": "sinkIn",
                    "data_type": "U32"}],
            commands=[{"name": "store", "opcode": 0x10}],
        )
        issues = fprime.validate_component(defn)
        self.assertTrue(any(
            "passive components must not declare commands" in i
            for i in issues))


class ConnectionValidationTests(unittest.TestCase):
    """Contract: typed port connections carry output to input data."""

    def test_typed_connection_matches_clean(self):
        defs, conns, _groups = worked_example()
        self.assertEqual(fprime.validate_connections(defs, conns), [])

    def test_wrong_type_connection_reported(self):
        defs = [signal_gen_defn(), data_logger_defn(dtype="F32")]
        conns = [fprime.conn("SignalGen", "tlmOut", "DataLogger", "logIn")]
        issues = fprime.validate_connections(defs, conns)
        self.assertTrue(any(
            "connection type mismatch 'SignalGen.tlmOut' (U32) -> "
            "'DataLogger.logIn' (F32)" in i for i in issues))

    def test_dangling_references_reported(self):
        defs, conns, _ = worked_example()
        conns = conns + [fprime.conn("Ghost", "out", "DataLogger", "logIn")]
        issues = fprime.validate_connections(defs, conns)
        self.assertTrue(any("connection from unknown component 'Ghost'" in i
                            for i in issues))
        # A declared component with an undeclared port is a dangling ref.
        conns2 = [fprime.conn("SignalGen", "nope", "DataLogger", "logIn")]
        issues2 = fprime.validate_connections(defs, conns2)
        self.assertTrue(any(
            "connection from 'SignalGen': port 'nope' not declared" in i
            for i in issues2))

    def test_direction_rules(self):
        defs, conns, _ = worked_example()
        # Source is an input port: not allowed.
        issues = fprime.validate_connections(
            defs, [fprime.conn("DataLogger", "logIn", "SignalGen", "run")]
        )
        self.assertTrue(any("source port must be an output" in i
                            for i in issues))
        # Destination is an output port: not allowed.
        tap = fprime.component(
            "Tap", "passive",
            ports=[{"direction": "output", "name": "tapOut",
                    "data_type": "U32"}],
        )
        issues2 = fprime.validate_connections(
            defs + [tap],
            [fprime.conn("SignalGen", "tlmOut", "Tap", "tapOut")],
        )
        self.assertTrue(any("destination port must be an input" in i
                            for i in issues2))

    def test_self_loop_reported(self):
        # DataLogger feeding its own input through an output of itself.
        defn = fprime.component(
            "Loop", "active",
            ports=[
                {"direction": "input", "name": "run", "data_type": "U32"},
                {"direction": "output", "name": "echo", "data_type": "U32"},
            ],
        )
        issues = fprime.validate_connections(
            [defn], [fprime.conn("Loop", "echo", "Loop", "run")]
        )
        self.assertTrue(any("self-loop connection" in i for i in issues))

    def test_serial_interface_matches_any_type(self):
        ser = fprime.component(
            "Uplink", "active",
            ports=[
                {"direction": "input", "name": "run", "data_type": "U32"},
                {"direction": "output", "name": "packet",
                 "data_type": "serial"},
            ],
        )
        consumer = fprime.component(
            "Loader", "queued",
            ports=[{"direction": "input", "name": "loadIn",
                    "data_type": "serial"}],
        )
        issues = fprime.validate_connections(
            [ser, consumer],
            [fprime.conn("Uplink", "packet", "Loader", "loadIn")],
        )
        self.assertEqual(issues, [])


class RateGroupTests(unittest.TestCase):
    """Contract: rate groups schedule input ports at a clock rate."""

    def test_worked_example_schedule_clean(self):
        defs, conns, groups = worked_example()
        verdict = fprime.validate_topology(defs, conns, groups)
        self.assertEqual(verdict["issues"], [])
        self.assertEqual(verdict["warnings"], [])

    def test_orphaned_active_input_reported(self):
        defn = data_logger_defn()
        issues, _warnings = fprime.validate_rate_groups([defn], [], [])
        self.assertTrue(any(
            "input port 'DataLogger.logIn' has no dispatch driver" in i
            for i in issues))

    def test_double_driver_reported(self):
        # Rate group plus incoming connection: two dispatch drivers.
        defs, conns, groups = worked_example()
        groups = groups + [fprime.rate_group("1HzB", 2.0,
                                             [("DataLogger", "logIn")])]
        issues, _warnings = fprime.validate_rate_groups(defs, conns, groups)
        self.assertTrue(any(
            "input port 'DataLogger.logIn' has 2 dispatch drivers" in i
            for i in issues))
        # Two incoming connections into one queued input: also two drivers.
        a = fprime.component(
            "A", "active",
            ports=[
                {"direction": "input", "name": "run", "data_type": "U32"},
                {"direction": "output", "name": "outA", "data_type": "U32"},
            ],
        )
        c = fprime.component(
            "C", "active",
            ports=[
                {"direction": "input", "name": "run", "data_type": "U32"},
                {"direction": "output", "name": "outC", "data_type": "U32"},
            ],
        )
        log = data_logger_defn()
        conns2 = [fprime.conn("A", "outA", "DataLogger", "logIn"),
                  fprime.conn("C", "outC", "DataLogger", "logIn")]
        groups2 = [fprime.rate_group("1Hz", 1.0, [("A", "run"),
                                                  ("C", "run")])]
        issues2, _w = fprime.validate_rate_groups([a, c, log], conns2, groups2)
        self.assertTrue(any(
            "input port 'DataLogger.logIn' has 2 dispatch drivers" in i
            for i in issues2))

    def test_passive_port_warnings(self):
        sink = fprime.component(
            "Sink", "passive",
            ports=[{"direction": "input", "name": "sinkIn",
                    "data_type": "U32"}],
        )
        groups = [fprime.rate_group("1Hz", 1.0, [("Sink", "sinkIn")]),
                  fprime.rate_group("2Hz", 2.0, [("Sink", "sinkIn")])]
        issues, warnings = fprime.validate_rate_groups([sink], [], groups)
        self.assertEqual(issues, [])
        self.assertTrue(any(
            "passive input port 'Sink.sinkIn' is invoked by 2 rate groups" in w
            for w in warnings))
        # A passive input nothing ever calls is dead code: a warning.
        sink2 = fprime.component(
            "Sink", "passive",
            ports=[{"direction": "input", "name": "sinkIn",
                    "data_type": "U32"}],
        )
        issues2, warnings2 = fprime.validate_rate_groups([sink2], [], [])
        self.assertEqual(issues2, [])
        self.assertTrue(any(
            "passive input port 'Sink.sinkIn' has no dispatch driver" in w
            for w in warnings2))

    def test_rate_group_hz_and_name_rules(self):
        defs, conns, _ = worked_example()
        bad_hz = [fprime.rate_group("1Hz", 0.0, [("SignalGen", "run")])]
        issues, _w = fprime.validate_rate_groups(defs, conns, bad_hz)
        self.assertTrue(any("hz must be a positive number" in i
                            for i in issues))
        dup = [fprime.rate_group("1Hz", 1.0, [("SignalGen", "run")]),
               fprime.rate_group("1Hz", 2.0, [("SignalGen", "run")])]
        issues2, _w2 = fprime.validate_rate_groups(defs, conns, dup)
        self.assertTrue(any("duplicate rate group name '1Hz'" in i
                            for i in issues2))

    def test_rate_group_entry_rules(self):
        defs, conns, _ = worked_example()
        dangling = [fprime.rate_group("1Hz", 1.0, [("Ghost", "run")])]
        issues, _w = fprime.validate_rate_groups(defs, conns, dangling)
        self.assertTrue(any("unknown component 'Ghost'" in i
                            for i in issues))
        # Output ports cannot be scheduled.
        out_entry = [fprime.rate_group("1Hz", 1.0,
                                       [("SignalGen", "tlmOut")])]
        issues2, _w2 = fprime.validate_rate_groups(defs, conns, out_entry)
        self.assertTrue(any(
            "'SignalGen.tlmOut' is not an input port" in i for i in issues2))


class SimulationTests(unittest.TestCase):
    """Contract: the clocked dispatch loop is deterministic."""

    def test_worked_example_dispatch_records(self):
        defs, conns, groups = worked_example()
        sim = fprime.Simulation(defs, conns, groups)
        sim.run(3)  # three 1 Hz master cycles
        self.assertEqual(
            [i["cycle"] for i in sim.invocations], [0, 1, 2]
        )
        self.assertTrue(all(i["group"] == "1Hz" and i["comp"] == "SignalGen"
                            and i["port"] == "run"
                            for i in sim.invocations))
        self.assertEqual(
            [d["value"] for d in sim.deliveries], [0, 1, 2]
        )
        self.assertTrue(all(
            d["from_comp"] == "SignalGen" and d["from_port"] == "tlmOut"
            and d["to_comp"] == "DataLogger" and d["to_port"] == "logIn"
            for d in sim.deliveries))
        # Telemetry auto-samples with a per-channel sequence counter.
        self.assertEqual(
            [s["value"] for s in sim.samples], [0, 1, 2]
        )
        self.assertEqual([s["seq"] for s in sim.samples], [0, 1, 2])
        self.assertTrue(all(s["channel"] == "logIn"
                            for s in sim.samples))

    def test_simulation_rejects_invalid_topology(self):
        defs = [signal_gen_defn(), data_logger_defn(dtype="F32")]
        conns = [fprime.conn("SignalGen", "tlmOut", "DataLogger", "logIn")]
        groups = [fprime.rate_group("1Hz", 1.0, [("SignalGen", "run")])]
        with self.assertRaises(ValueError) as ctx:
            fprime.Simulation(defs, conns, groups)
        self.assertIn("connection type mismatch", str(ctx.exception))

    def test_commands_arrive_and_log_with_opcode(self):
        defs, conns, groups = worked_example()
        sim = fprime.Simulation(defs, conns, groups)
        sim.run(2)
        entry = sim.send_command("SignalGen", "reset")
        self.assertEqual(
            entry, {"cycle": 2, "comp": "SignalGen", "name": "reset",
                    "opcode": 0x01}
        )
        # Opcode form works identically.
        entry2 = sim.send_command("SignalGen", 0x01)
        self.assertEqual(entry2["opcode"], 0x01)
        self.assertEqual(len(sim.command_log), 2)

    def test_unknown_command_and_component_raise(self):
        defs, conns, groups = worked_example()
        sim = fprime.Simulation(defs, conns, groups)
        with self.assertRaises(ValueError):
            sim.send_command("SignalGen", "noSuchCommand")
        with self.assertRaises(ValueError):
            sim.send_command("Ghost", "reset")
        with self.assertRaises(ValueError):
            sim.send_command("SignalGen", 0x77)
        # The command path is async: a passive component rejects it.
        sink = fprime.component(
            "Sink", "passive",
            ports=[{"direction": "input", "name": "sinkIn",
                    "data_type": "U32"}],
        )
        sim2 = fprime.Simulation([sink], [], [])
        with self.assertRaises(ValueError) as ctx:
            sim2.send_command("Sink", "store")
        self.assertIn("cannot receive commands", str(ctx.exception))

    def test_events_log_with_declared_severity(self):
        defs, conns, groups = worked_example()
        sim = fprime.Simulation(defs, conns, groups)
        sim.run(1)
        entry = sim.raise_event("SignalGen", "fault")
        self.assertEqual(
            entry, {"cycle": 1, "comp": "SignalGen", "name": "fault",
                    "severity": "HIGH"}
        )
        with self.assertRaises(ValueError):
            sim.raise_event("SignalGen", "nope")
        with self.assertRaises(ValueError):
            sim.raise_event("Ghost", "fault")

    def test_telemetry_sample_sequence_and_type_checks(self):
        defs, conns, groups = worked_example()
        sim = fprime.Simulation(defs, conns, groups)
        sim.run(2)
        sample = sim.record_telemetry("DataLogger", "logIn", 9)
        self.assertEqual(sample["seq"], 2)  # auto-samples took seq 0, 1
        self.assertEqual(sample["value"], 9)
        with self.assertRaises(ValueError):
            sim.record_telemetry("DataLogger", "logIn", "not-a-number")
        with self.assertRaises(ValueError):
            sim.record_telemetry("DataLogger", "missing", 1)
        with self.assertRaises(ValueError):
            sim.record_telemetry("Ghost", "logIn", 1)

    def test_multi_rate_group_master_clock(self):
        a = fprime.component(
            "A", "active",
            ports=[
                {"direction": "input", "name": "runA", "data_type": "U32"},
                {"direction": "output", "name": "outA", "data_type": "U32"},
            ],
        )
        b = fprime.component(
            "B", "active",
            ports=[
                {"direction": "input", "name": "runB", "data_type": "U32"},
                {"direction": "output", "name": "outB", "data_type": "U32"},
            ],
        )
        sink = fprime.component(
            "Sink", "passive",
            ports=[{"direction": "input", "name": "sinkIn",
                    "data_type": "U32"}],
        )
        defs = [a, b, sink]
        conns = [fprime.conn("A", "outA", "Sink", "sinkIn"),
                 fprime.conn("B", "outB", "Sink", "sinkIn")]
        groups = [fprime.rate_group("10Hz", 10.0, [("A", "runA")]),
                  fprime.rate_group("1Hz", 1.0, [("B", "runB")])]
        sim = fprime.Simulation(defs, conns, groups)  # base_hz = 10
        sim.run(10)
        self.assertEqual(sim.cycle, 10)
        by_group = {}
        for inv in sim.invocations:
            by_group[inv["group"]] = by_group.get(inv["group"], 0) + 1
        self.assertEqual(by_group, {"10Hz": 10, "1Hz": 1})
        self.assertEqual(
            [d["value"] for d in sim.deliveries
             if d["from_comp"] == "A"], list(range(10))
        )
        self.assertEqual(
            [d["value"] for d in sim.deliveries
             if d["from_comp"] == "B"], [0]
        )

    def test_warnings_do_not_block_simulation(self):
        sink = fprime.component(
            "Sink", "passive",
            ports=[{"direction": "input", "name": "sinkIn",
                    "data_type": "U32"}],
        )
        groups = [fprime.rate_group("1Hz", 1.0, [("Sink", "sinkIn")]),
                  fprime.rate_group("2Hz", 2.0, [("Sink", "sinkIn")])]
        sim = fprime.Simulation([sink], [], groups)
        self.assertEqual(sim.run(2), 2)
        # base_hz 2: 2 Hz group ticks every tick, 1 Hz group at tick 0.
        self.assertEqual(
            [i["cycle"] for i in sim.invocations], [0, 0, 1]
        )


class ManifestTests(unittest.TestCase):
    """Contract: generate_manifest expands a clean definition."""

    def test_manifest_structure_worked_example(self):
        manifest = fprime.generate_manifest(signal_gen_defn())
        self.assertEqual(manifest["component"], "SignalGen")
        self.assertEqual(manifest["class_name"], "SignalGenComponent")
        self.assertEqual(manifest["header_guard"],
                         "SIGNALGEN_COMPONENT_HPP")
        self.assertEqual(
            manifest["port_method_stubs"],
            ["void on_run(U32 value);",
             "void tlmOut_out(U32 portNum, U32 value);"],
        )
        self.assertEqual(
            manifest["command_dispatch"],
            [{"opcode": 0x01, "name": "reset",
              "entry": "case 0x0001: /* reset */ do_reset(); break;"}],
        )
        self.assertEqual([f["path"] for f in manifest["files"]],
                         ["SignalGen.fpp", "SignalGenComponentBase.hpp",
                          "SignalGenComponentBase.cpp"])

    def test_manifest_file_contents(self):
        manifest = fprime.generate_manifest(signal_gen_defn())
        by_path = {f["path"]: f["content"] for f in manifest["files"]}
        hpp = by_path["SignalGenComponentBase.hpp"]
        cpp = by_path["SignalGenComponentBase.cpp"]
        fpp = by_path["SignalGen.fpp"]
        self.assertIn("SIGNALGEN_COMPONENT_HPP", hpp)
        self.assertIn("void on_run(U32 value);", hpp)
        self.assertIn("async input port run: U32", fpp)
        self.assertIn("async command reset opcode 0x0001", fpp)
        self.assertIn("case 0x0001: /* reset */ do_reset(); break;", cpp)
        self.assertIn("SignalGenComponent::dispatchCommand", cpp)

    def test_manifest_lists_channels_and_events(self):
        manifest = fprime.generate_manifest(data_logger_defn())
        self.assertEqual(manifest["telemetry_channels"],
                         [{"name": "logIn", "type": "U32"}])
        self.assertIn("telemetry logIn: U32",
                      manifest["files"][0]["content"])
        sg = fprime.generate_manifest(signal_gen_defn())
        self.assertEqual(sg["events"],
                         [{"name": "started", "severity": "INFO"},
                          {"name": "fault", "severity": "HIGH"}])

    def test_manifest_rejects_invalid_definition(self):
        bad = fprime.component(
            "SignalGen", "active",
            ports=[{"direction": "output", "name": "tlmOut",
                    "data_type": "U32"}],
            commands=[{"name": "reset", "opcode": 0x01},
                      {"name": "reboot", "opcode": 0x01}],
        )
        with self.assertRaises(ValueError) as ctx:
            fprime.generate_manifest(bad)
        self.assertIn("duplicate command opcode", str(ctx.exception))


if __name__ == "__main__":
    unittest.main(verbosity=2)
