#!/usr/bin/env python3
"""Pure-Python model of the NASA JPL F Prime (F´) component framework.

Models and validates an F´ flight software component architecture:

  - Component definitions: name, kind (active | queued | passive), typed
    input/output ports (plus serial interfaces), registered commands with
    opcodes, telemetry channels, and severity-flagged events.
  - Component validation: opcode uniqueness, port name uniqueness,
    supported kinds, supported telemetry types, F´ event severities,
    the active component input-port rule, and the passive component
    no-command rule.
  - Topology connections: typed output-to-input connections with
    data-type equality checks (serial interfaces match any type),
    dangling-port checks, direction checks, and self-loop rejection.
  - Rate groups: clocked dispatch schedules that tick component input
    ports at a frequency in Hz; every active/queued input port must be
    dispatched by exactly one driver (one incoming connection or one
    rate group), and passive ports invoked from two rate groups warn.
  - Deterministic dispatch simulation: per master cycle each due rate
    group invokes its input ports in order; scheduled components emit
    the master cycle index on their output ports, deliveries cascade
    over connections, telemetry samples carry a per-channel sequence
    counter, commands arrive on the command path and log, and events
    log with severity.
  - Scaffold manifest: a validated definition expands into the files a
    developer would codegen from (class name, header guard, port method
    stubs, command dispatch entries, telemetry channel list).

Stdlib only. No network. Deterministic. See the leaf SKILL.md for the
stated model rules; this module enforces them consistently.

F´ is NASA JPL open-source flight software (github/nasa/fprime,
Apache-2.0). Component kinds and mechanisms follow F´ vocabulary:
active components own a thread and queue and are dispatched by the
framework, queued components carry a queue without their own thread,
and passive components run inline in the caller's context.
"""

COMPONENT_KINDS = ("active", "queued", "passive")

# Telemetry and typed port payload types the model supports.
TLM_TYPES = ("U8", "U16", "U32", "I32", "F32", "F64", "string")
# Ports may also declare a serial interface, which carries dynamic
# payloads and therefore type-matches any partner port.
PORT_TYPES = TLM_TYPES + ("serial",)

SEVERITIES = ("FATAL", "HIGH", "LOW", "INFO", "DEBUG")

OPCODE_MIN = 0
OPCODE_MAX = 0xFFFF

INT_TYPES = ("U8", "U16", "U32", "I32")
FLOAT_TYPES = ("F32", "F64")


def _check_name(value, label):
    """Reject empty or non-string names."""
    if not isinstance(value, str) or not value.strip():
        raise ValueError("%s must be a non-empty string, got %r" % (label, value))
    return value.strip()


def type_accepts(value, data_type):
    """True when a sample value fits a declared telemetry or port type.

    Integer types accept ints (not bools), float types accept ints and
    floats, and the string type accepts str.
    """
    if data_type in INT_TYPES:
        return isinstance(value, int) and not isinstance(value, bool)
    if data_type in FLOAT_TYPES:
        return isinstance(value, (int, float)) and not isinstance(value, bool)
    if data_type == "string":
        return isinstance(value, str)
    return True  # serial: any payload


def component(name, kind, ports=None, commands=None,
              telemetry=None, events=None):
    """Build a component definition dict with empty defaults."""
    return {
        "name": name,
        "kind": kind,
        "ports": list(ports or []),
        "commands": list(commands or []),
        "telemetry": list(telemetry or []),
        "events": list(events or []),
    }


def conn(comp_from, port_from, comp_to, port_to):
    """Build one typed connection dict: producer output to consumer input."""
    return {"from": (comp_from, port_from), "to": (comp_to, port_to)}


def rate_group(name, hz, ports):
    """Build one rate group dict that ticks input ports at hz (Hz)."""
    return {"name": name, "hz": float(hz), "ports": list(ports)}


def validate_component(defn):
    """Return a list of issue strings for one component definition.

    Stated model rules, enforced consistently:
      - name is required; kind must be active, queued or passive.
      - port names are unique; port directions are input or output;
        port data types are drawn from PORT_TYPES (serial marks a
        serial interface).
      - command names are unique and command opcodes are unique
        integers in OPCODE_MIN..OPCODE_MAX.
      - telemetry channel names are unique and channel types come from
        TLM_TYPES (channels never use serial).
      - event names are unique and severities come from
        (FATAL, HIGH, LOW, INFO, DEBUG).
      - active components must declare at least one input port: the
        framework dispatches them, and a thread with no dispatch entry
        cannot run.
      - passive components must not declare commands: commands arrive
        asynchronously on the framework command path, which requires a
        queue; passive components have neither thread nor queue.
    """
    issues = []
    name = defn.get("name")
    if not isinstance(name, str) or not name.strip():
        issues.append("component missing name")
        return issues
    name = name.strip()

    kind = defn.get("kind")
    if kind not in COMPONENT_KINDS:
        issues.append(
            "component '%s': unsupported kind %r, use one of %s"
            % (name, kind, ", ".join(COMPONENT_KINDS))
        )

    ports = defn.get("ports") or []
    port_names = []
    for p in ports:
        pname = p.get("name")
        if not isinstance(pname, str) or not pname.strip():
            issues.append("component '%s': port missing name" % name)
            continue
        pname = pname.strip()
        if pname in port_names:
            issues.append(
                "component '%s': duplicate port name '%s'" % (name, pname)
            )
        port_names.append(pname)
        if p.get("direction") not in ("input", "output"):
            issues.append(
                "component '%s': port '%s' direction must be input or output"
                % (name, pname)
            )
        if p.get("data_type") not in PORT_TYPES:
            issues.append(
                "component '%s': port '%s' unsupported data type %r"
                % (name, pname, p.get("data_type"))
            )

    commands = defn.get("commands") or []
    cmd_names = []
    cmd_opcodes = {}
    for c in commands:
        cname = c.get("name")
        opcode = c.get("opcode")
        if not isinstance(cname, str) or not cname.strip():
            issues.append("component '%s': command missing name" % name)
        else:
            cname = cname.strip()
            if cname in cmd_names:
                issues.append(
                    "component '%s': duplicate command name '%s'"
                    % (name, cname)
                )
            cmd_names.append(cname)
        if (isinstance(opcode, bool) or not isinstance(opcode, int)
                or not (OPCODE_MIN <= opcode <= OPCODE_MAX)):
            issues.append(
                "component '%s': command '%s' opcode %r out of range "
                "%d..%d (0x%04X..0x%04X)"
                % (name, cname, opcode, OPCODE_MIN, OPCODE_MAX,
                   OPCODE_MIN, OPCODE_MAX)
            )
        else:
            if opcode in cmd_opcodes:
                issues.append(
                    "component '%s': duplicate command opcode 0x%04X "
                    "(commands '%s' and '%s')"
                    % (name, opcode, cmd_opcodes[opcode], cname)
                )
            cmd_opcodes[opcode] = cname

    telemetry = defn.get("telemetry") or []
    tlm_names = []
    for ch in telemetry:
        chname = ch.get("name")
        if not isinstance(chname, str) or not chname.strip():
            issues.append("component '%s': telemetry channel missing name" % name)
            continue
        chname = chname.strip()
        if chname in tlm_names:
            issues.append(
                "component '%s': duplicate telemetry channel name '%s'"
                % (name, chname)
            )
        tlm_names.append(chname)
        if ch.get("type") not in TLM_TYPES:
            issues.append(
                "component '%s': telemetry channel '%s' unsupported type %r, "
                "use one of %s"
                % (name, chname, ch.get("type"), ", ".join(TLM_TYPES))
            )

    events = defn.get("events") or []
    event_names = []
    for e in events:
        ename = e.get("name")
        if not isinstance(ename, str) or not ename.strip():
            issues.append("component '%s': event missing name" % name)
            continue
        ename = ename.strip()
        if ename in event_names:
            issues.append(
                "component '%s': duplicate event name '%s'" % (name, ename)
            )
        event_names.append(ename)
        if e.get("severity") not in SEVERITIES:
            issues.append(
                "component '%s': event '%s' unsupported severity %r, use one "
                "of %s"
                % (name, ename, e.get("severity"), ", ".join(SEVERITIES))
            )

    input_ports = [p["name"] for p in ports
                   if p.get("direction") == "input"
                   and isinstance(p.get("name"), str)]
    if kind == "active" and not input_ports:
        issues.append(
            "component '%s': active components must declare at least one "
            "input port (the framework dispatches them)" % name
        )

    if kind == "passive" and commands:
        issues.append(
            "component '%s': passive components must not declare commands; "
            "commands arrive asynchronously and require a queue (%d "
            "declared)" % (name, len(commands))
        )

    return issues


def _defs_index(defs):
    """Map component name to its definition; ValueError on unknown."""
    index = {}
    for d in defs:
        dname = d.get("name")
        if isinstance(dname, str) and dname.strip():
            index[dname.strip()] = d
    return index


def _port_lookup(defn, pname):
    """Return the port dict for pname or None."""
    for p in defn.get("ports") or []:
        if p.get("name") == pname:
            return p
    return None


def validate_connections(defs, connections):
    """Return issue strings for a connection list against the defs.

    A connection is {"from": (comp, port), "to": (comp, port)} and
    carries typed data from one component output port to another
    component's input port. Stated rules:
      - referenced components exist and ports exist (no dangling refs);
      - the from end is an output port, the to end is an input port
        (no connection to an output);
      - data types match, unless either side is a serial interface
        (serial carries dynamic payloads and matches any type);
      - no self-loop (a component never feeds its own input port).
    """
    issues = []
    index = _defs_index(defs)
    for c in connections:
        (cfrom, pfrom), (cto, pto) = c["from"], c["to"]
        for (comp, port) in (cfrom, pfrom), (cto, pto):
            if not isinstance(comp, str) or not comp.strip():
                issues.append("connection references a missing component name")
                return issues
        if cfrom not in index:
            issues.append(
                "connection from unknown component '%s'" % cfrom
            )
            continue
        if cto not in index:
            issues.append("connection to unknown component '%s'" % cto)
            continue
        fdefn, tdefn = index[cfrom], index[cto]
        fport = _port_lookup(fdefn, pfrom)
        tport = _port_lookup(tdefn, pto)
        if fport is None:
            issues.append(
                "connection from '%s': port '%s' not declared" % (cfrom, pfrom)
            )
            continue
        if tport is None:
            issues.append(
                "connection to '%s': port '%s' not declared" % (cto, pto)
            )
            continue
        if fport.get("direction") != "output":
            issues.append(
                "connection from '%s.%s': source port must be an output"
                % (cfrom, pfrom)
            )
        if tport.get("direction") != "input":
            issues.append(
                "connection to '%s.%s': destination port must be an input"
                % (cto, pto)
            )
        if cfrom == cto:
            issues.append(
                "self-loop connection '%s.%s' -> '%s.%s' is not allowed"
                % (cfrom, pfrom, cto, pto)
            )
        ftype = fport.get("data_type")
        ttype = tport.get("data_type")
        if ftype != ttype and "serial" not in (ftype, ttype):
            issues.append(
                "connection type mismatch '%s.%s' (%s) -> '%s.%s' (%s)"
                % (cfrom, pfrom, ftype, cto, pto, ttype)
            )
    return issues


def _incoming_connections(connections):
    """Map destination (comp, port) to the list of source comps."""
    incoming = {}
    for c in connections:
        (cfrom, _pfrom), (cto, pto) = c["from"], c["to"]
        incoming.setdefault((cto, pto), []).append(cfrom)
    return incoming


def validate_rate_groups(defs, connections, rate_groups):
    """Validate rate group schedules; return (issues, warnings).

    A rate group dict is {"name": str, "hz": float, "ports": [(comp,
    input_port), ...]} and ticks each listed input port every cycle of
    the group. Stated rules:
      - group names are unique and group hz values are positive;
      - every listed entry names a declared input port (a rate group
        invokes input ports, never outputs);
      - dispatch coverage: every input port of an active or queued
        component must be dispatched by exactly one driver: one
        incoming connection or one rate group. Zero drivers means the
        port is orphaned, more than one means double dispatch.
      - a passive input port listed in two or more rate groups warns
        (its handler would run in two timing contexts); a passive
        input port with no driver at all warns as dead code.
    """
    issues = []
    warnings = []
    index = _defs_index(defs)

    names = []
    for g in rate_groups:
        gname = g.get("name")
        if not isinstance(gname, str) or not gname.strip():
            issues.append("rate group missing name")
            continue
        gname = gname.strip()
        if gname in names:
            issues.append("duplicate rate group name '%s'" % gname)
        names.append(gname)
        hz = g.get("hz")
        if not isinstance(hz, (int, float)) or isinstance(hz, bool) \
                or not hz > 0:
            issues.append(
                "rate group '%s': hz must be a positive number, got %r"
                % (gname, hz)
            )
        for (comp, port) in g.get("ports") or []:
            if comp not in index:
                issues.append(
                    "rate group '%s': unknown component '%s'"
                    % (gname, comp)
                )
                continue
            p = _port_lookup(index[comp], port)
            if p is None:
                issues.append(
                    "rate group '%s': component '%s' has no port '%s'"
                    % (gname, comp, port)
                )
                continue
            if p.get("direction") != "input":
                issues.append(
                    "rate group '%s': '%s.%s' is not an input port "
                    "(rate groups invoke input ports)"
                    % (gname, comp, port)
                )

    # Dispatch driver coverage for active/queued input ports.
    group_membership = {}  # (comp, port) -> [group names]
    for g in rate_groups:
        gname = g.get("name")
        for (comp, port) in (g.get("ports") or []):
            if isinstance(gname, str) and gname.strip() \
                    and comp in index \
                    and _port_lookup(index[comp], port) is not None:
                group_membership.setdefault((comp, port), []).append(
                    gname.strip()
                )
    incoming = _incoming_connections(connections)

    for d in defs:
        dname = d.get("name")
        if not isinstance(dname, str):
            continue
        kind = d.get("kind")
        for p in d.get("ports") or []:
            if p.get("direction") != "input":
                continue
            pname = p.get("name")
            if not isinstance(pname, str):
                continue
            key = (dname, pname)
            n_groups = len(group_membership.get(key, ()))
            n_conns = len(incoming.get(key, ()))
            if kind in ("active", "queued"):
                drivers = n_groups + n_conns
                if drivers == 0:
                    issues.append(
                        "input port '%s.%s' has no dispatch driver: add it "
                        "to one rate group or connect one output to it"
                        % (dname, pname)
                    )
                elif drivers > 1:
                    issues.append(
                        "input port '%s.%s' has %d dispatch drivers "
                        "(%d rate group(s), %d connection(s)); exactly one "
                        "is allowed" % (dname, pname, drivers, n_groups,
                                        n_conns)
                    )
            else:  # passive: sync ports run inline in the caller context
                if n_groups > 1:
                    warnings.append(
                        "passive input port '%s.%s' is invoked by %d rate "
                        "groups; its handler runs in multiple timing "
                        "contexts" % (dname, pname, n_groups)
                    )
                if n_groups == 0 and n_conns == 0:
                    warnings.append(
                        "passive input port '%s.%s' has no dispatch driver "
                        "(dead port)" % (dname, pname)
                    )

    return issues, warnings


def validate_topology(defs, connections, rate_groups):
    """Umbrella validator: component, connection and rate group checks."""
    issues = []
    for i, d in enumerate(defs):
        for msg in validate_component(d):
            issues.append("component %d: %s" % (i, msg))
    issues.extend(validate_connections(defs, connections))
    rg_issues, warnings = validate_rate_groups(defs, connections, rate_groups)
    issues.extend(rg_issues)
    return {"issues": issues, "warnings": warnings}


class Simulation:
    """Clocked dispatch simulation of a validated F´ topology.

    The master clock ticks at base_hz (default: the fastest declared
    rate group). Each rate group runs every round(base_hz / hz) master
    ticks. On a tick, due rate groups dispatch their listed input ports
    in order (sorted by period, then group name, then listed order).

    Deterministic toy behavior, documented as the model's semantics:
      - every dispatch records an invocation (cycle, group, comp, port);
      - the dispatched component emits the master cycle index on each
        of its declared output ports;
      - each emission follows its connections and records a delivery
        (cycle, from_comp, from_port, to_comp, to_port, value);
      - when the destination declares a telemetry channel whose name
        matches the destination port name, the delivered value is
        auto-sampled onto that channel with a per-channel sequence
        counter;
      - commands are sent through send_command and log on the command
        path with their opcode; events log with severity via
        raise_event; extra telemetry samples can be recorded with
        record_telemetry.

    Construction validates the whole topology and raises ValueError on
    any issue, so the simulation only ever runs over a clean model.
    """

    def __init__(self, defs, connections, rate_groups, base_hz=None):
        verdict = validate_topology(defs, connections, rate_groups)
        if verdict["issues"]:
            raise ValueError(
                "topology invalid, cannot simulate: " + "; ".join(
                    verdict["issues"]
                )
            )
        self.defs = defs
        self.connections = list(connections)
        self.rate_groups = list(rate_groups)
        self.index = _defs_index(defs)

        hzs = [g["hz"] for g in rate_groups if isinstance(
            g.get("hz"), (int, float))]
        if base_hz is None:
            base_hz = max(hzs) if hzs else 1.0
        self.base_hz = float(base_hz)

        self.schedule = []
        for g in rate_groups:
            period = max(1, int(round(self.base_hz / float(g["hz"]))))
            self.schedule.append(
                {"name": g["name"], "period": period,
                 "ports": list(g["ports"])}
            )
        self.schedule.sort(key=lambda s: (s["period"], s["name"]))

        self.cycle = 0
        self.invocations = []    # rate group dispatches
        self.deliveries = []     # connection data flow
        self.samples = []        # telemetry samples with seq counters
        self.command_log = []    # arrived commands
        self.event_log = []      # raised events
        self._seq = {}           # channel -> last sequence number
        self._channel_map = {}   # (comp, channel) -> type
        for d in defs:
            dname = d.get("name")
            for ch in d.get("telemetry") or []:
                self._channel_map[(dname, ch["name"])] = ch["type"]

    def _next_seq(self, key):
        self._seq[key] = self._seq.get(key, -1) + 1
        return self._seq[key]

    def run(self, cycles):
        """Run `cycles` master clock ticks; returns the new cycle count."""
        for _ in range(cycles):
            self._tick()
            self.cycle += 1
        return self.cycle

    def _tick(self):
        for s in self.schedule:
            if self.cycle % s["period"] == 0:
                for (comp, port) in s["ports"]:
                    self.invocations.append({
                        "cycle": self.cycle, "group": s["name"],
                        "comp": comp, "port": port,
                    })
                    self._emit(comp, self.cycle)

    def _emit(self, comp, tick_value):
        """Dispatch outputs of `comp`; the toy emits the master tick."""
        defn = self.index[comp]
        for p in defn.get("ports") or []:
            if p.get("direction") != "output":
                continue
            outport = p["name"]
            for c in self.connections:
                (cfrom, pfrom), (cto, pto) = c["from"], c["to"]
                if cfrom != comp or pfrom != outport:
                    continue
                self.deliveries.append({
                    "cycle": self.cycle, "from_comp": cfrom,
                    "from_port": pfrom, "to_comp": cto, "to_port": pto,
                    "value": tick_value,
                })
                if (cto, pto) in self._channel_map:
                    self.samples.append({
                        "cycle": self.cycle, "comp": cto,
                        "channel": pto, "value": tick_value,
                        "seq": self._next_seq((cto, pto)),
                    })

    def _command_lookup(self, comp, command):
        """Resolve a command by name or opcode; returns the entry."""
        defn = self.index.get(comp)
        if defn is None:
            raise ValueError("unknown component '%s'" % comp)
        if defn.get("kind") == "passive":
            raise ValueError(
                "passive component '%s' cannot receive commands" % comp
            )
        for c in defn.get("commands") or []:
            if c["name"] == command or c["opcode"] == command:
                return c
        raise ValueError(
            "component '%s' has no command matching %r" % (comp, command)
        )

    def send_command(self, comp, command):
        """Deliver a command (name or opcode) on the command path.

        Validates the command and records the arrival with its opcode
        and the current cycle. Returns the log entry.
        """
        entry = self._command_lookup(comp, command)
        log = {
            "cycle": self.cycle, "comp": comp, "name": entry["name"],
            "opcode": entry["opcode"],
        }
        self.command_log.append(log)
        return log

    def raise_event(self, comp, event_name):
        """Raise a declared event; logs it with its severity."""
        defn = self.index.get(comp)
        if defn is None:
            raise ValueError("unknown component '%s'" % comp)
        for e in defn.get("events") or []:
            if e["name"] == event_name:
                log = {
                    "cycle": self.cycle, "comp": comp, "name": event_name,
                    "severity": e["severity"],
                }
                self.event_log.append(log)
                return log
        raise ValueError(
            "component '%s' has no event named '%s'" % (comp, event_name)
        )

    def record_telemetry(self, comp, channel, value):
        """Record one telemetry sample with a per-channel sequence counter.

        Raises ValueError when the channel is undeclared or the value
        does not fit the declared type.
        """
        key = (comp, channel)
        if key not in self._channel_map:
            raise ValueError(
                "component '%s' has no telemetry channel '%s'"
                % (comp, channel)
            )
        dtype = self._channel_map[key]
        if not type_accepts(value, dtype):
            raise ValueError(
                "telemetry value %r does not fit channel '%s.%s' of type %s"
                % (value, comp, channel, dtype)
            )
        sample = {
            "cycle": self.cycle, "comp": comp, "channel": channel,
            "value": value, "seq": self._next_seq(key),
        }
        self.samples.append(sample)
        return sample


def generate_manifest(defn):
    """Expand a validated component definition into a scaffold manifest.

    Returns a dict with the structured scaffold (class name, header
    guard, port method stubs, command dispatch entries, telemetry
    channel list) plus ready-to-fill source file texts (model file,
    header, implementation) a developer would codegen from. This proves
    the model; it is not full F´ codegen. Raises ValueError when the
    definition is not clean.
    """
    issues = validate_component(defn)
    if issues:
        raise ValueError(
            "cannot generate manifest for invalid component: "
            + "; ".join(issues)
        )
    name = defn["name"]
    class_name = name + "Component"
    guard = "".join(ch for ch in name.upper() if ch.isalnum() or ch == "_")
    guard += "_COMPONENT_HPP"

    ctype = {
        "U8": "U8", "U16": "U16", "U32": "U32", "I32": "I32",
        "F32": "F32", "F64": "F64", "string": "Fw::String",
        "serial": "Fw::SerialBuffer",
    }

    input_ports = [p for p in defn.get("ports") or []
                   if p.get("direction") == "input"]
    output_ports = [p for p in defn.get("ports") or []
                    if p.get("direction") == "output"]

    # Port method stubs: handlers for input ports, invoke helpers for
    # output ports.
    port_method_stubs = []
    for p in input_ports:
        port_method_stubs.append(
            "void on_%s(%s value);" % (p["name"], ctype[p["data_type"]])
        )
    for p in output_ports:
        port_method_stubs.append(
            "void %s_out(U32 portNum, %s value);"
            % (p["name"], ctype[p["data_type"]])
        )

    command_dispatch = []
    for c in defn.get("commands") or []:
        command_dispatch.append({
            "opcode": c["opcode"], "name": c["name"],
            "entry": "case 0x%04X: /* %s */ do_%s(); break;"
                     % (c["opcode"], c["name"], c["name"].lower()),
        })

    telemetry_channels = [{"name": ch["name"], "type": ch["type"]}
                          for ch in defn.get("telemetry") or []]
    events = [{"name": e["name"], "severity": e["severity"]}
              for e in defn.get("events") or []]

    # FPP-style component model text.
    model_lines = ["%s component %s {" % (defn["kind"], name)]
    for p in input_ports:
        model_lines.append(
            "  async input port %s: %s" % (p["name"], p["data_type"])
        )
    for p in output_ports:
        model_lines.append(
            "  output port %s: %s" % (p["name"], p["data_type"])
        )
    for c in defn.get("commands") or []:
        model_lines.append(
            "  async command %s opcode 0x%04X" % (c["name"], c["opcode"])
        )
    for ch in defn.get("telemetry") or []:
        model_lines.append("  telemetry %s: %s" % (ch["name"], ch["type"]))
    for e in defn.get("events") or []:
        model_lines.append(
            "  event %s severity %s" % (e["name"], e["severity"])
        )
    model_lines.append("}")
    model_text = "\n".join(model_lines) + "\n"

    header_lines = [
        "#ifndef %s" % guard,
        "#define %s" % guard,
        "",
        "// Scaffold header for F´ component %s (model manifest, not "
        "full codegen)." % name,
        "",
        "class %s {" % class_name,
        "public:",
        "  // Telemetry channel list",
    ]
    for ch in defn.get("telemetry") or []:
        header_lines.append("  %s %s; // channel" % (ch["type"], ch["name"]))
    header_lines.append("")
    header_lines.append("  // Port method stubs")
    for stub in port_method_stubs:
        header_lines.append("  " + stub)
    header_lines.append("};")
    header_lines.append("")
    header_lines.append("#endif // %s" % guard)
    header_text = "\n".join(header_lines) + "\n"

    impl_lines = [
        "// Scaffold implementation for F´ component %s." % name,
        "#include \"%sComponentBase.hpp\"" % name,
        "",
        "void %s::%s_ComponentInit() {" % (class_name, name),
        "  // Register commands and telemetry channels here.",
        "}",
        "",
        "// Command dispatch entries",
        "void %s::dispatchCommand(U32 opcode) {" % class_name,
        "  switch (opcode) {",
    ]
    for c in command_dispatch:
        impl_lines.append("    " + c["entry"])
    impl_lines.extend([
        "    default: break;",
        "  }",
        "}",
        "",
    ])
    for stub in port_method_stubs:
        if stub.startswith("void on_"):
            # "void on_run(U32 value);" -> "void SignalGenComponent::on_run(U32 value) {"
            decl = stub[len("void "):].rstrip(";")
            impl_lines.append(
                "void %s::%s {" % (class_name, decl)
            )
            impl_lines.append("  // handler body")
            impl_lines.append("}")
            impl_lines.append("")
    impl_text = "\n".join(impl_lines) + "\n"

    files = [
        {"path": "%s.fpp" % name, "content": model_text},
        {"path": "%sComponentBase.hpp" % name, "content": header_text},
        {"path": "%sComponentBase.cpp" % name, "content": impl_text},
    ]

    return {
        "component": name,
        "class_name": class_name,
        "header_guard": guard,
        "port_method_stubs": port_method_stubs,
        "command_dispatch": command_dispatch,
        "telemetry_channels": telemetry_channels,
        "events": events,
        "files": files,
    }
