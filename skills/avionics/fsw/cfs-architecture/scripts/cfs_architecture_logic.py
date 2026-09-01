#!/usr/bin/env python3
"""Pure-Python model of NASA core Flight Software (cFS) architecture.

Implements the cFS software bus (SB) publish/subscribe message routing
with 16-bit message IDs, the event service (EVS) event log with severity
levels, the classic cFS app lifecycle (APP_Init / APP_Execute / APP_Data),
a scheduled telemetry app, and a telemetry pipeline that stamps monotonic
sequence counters.

Design mirror:
  - CFE_SB: apps register with register_app(), subscribe to message IDs
    with subscribe(), publish payloads with publish(), and route_messages()
    drains the publish queue FIFO, delivering each message to every
    subscriber in subscription order.
  - CFE_EVS: EventLog.log(app, severity, message) appends a severity
    flagged entry; an unknown severity raises ValueError.
  - CFE_ES / CFE_TBL / CFE_TIME / CFE_FS are described in SKILL.md and
    references/cfs-architecture-notes.md; the simulation focuses on the
    SB and EVS core apps plus the app lifecycle pattern.

Message IDs are 16-bit (0x0000-0xFFFF), the classic cFS layout: command
traffic occupies 0x0000-0x0FFF and telemetry 0x1000-0xFFFF, with the
upper bits carrying an app tag and the lower bits the message number
within that app (e.g. 0x1900 = app 0x19, message 0x00). Modern cFE
(6.7+) widened the message ID to 32 bits; this module implements the
classic 16-bit model per the skill contract.

Stdlib only. No network. Deterministic.
"""

MSG_ID_MIN = 0x0000
MSG_ID_MAX = 0xFFFF

SEVERITIES = ("DEBUG", "INFO", "EVENT", "ERROR", "CRITICAL")


def _check_msg_id(msg_id):
    """Reject anything that is not an integer in the 16-bit range."""
    if isinstance(msg_id, bool) or not isinstance(msg_id, int):
        raise ValueError("message id must be an integer, got %r" % (msg_id,))
    if not (MSG_ID_MIN <= msg_id <= MSG_ID_MAX):
        raise ValueError(
            "message id 0x%X out of 16-bit range 0x0000-0xFFFF" % msg_id
        )


class SoftwareBus:
    """CFE_SB model: register / subscribe / publish / route, FIFO ordered.

    Deliveries are recorded as (app_name, msg_id, payload) triples in
    route order; because the queue is drained FIFO and each message is
    delivered to every subscriber, each app sees exactly the messages it
    subscribed to, in publish order.
    """

    def __init__(self, event_log=None):
        self._apps = {}            # app name -> registration order index
        self._subscribers = {}     # msg_id -> [app_name, ...] subscribe order
        self._queue = []           # [(msg_id, payload)] in publish order
        self._delivered = []       # [(app, msg_id, payload)] in route order
        self._event_log = event_log

    def register_app(self, app_name):
        """Register an app with the bus (CFE_ES app startup step)."""
        if not isinstance(app_name, str) or not app_name:
            raise ValueError("app name must be a non-empty string")
        if app_name in self._apps:
            raise ValueError("app already registered: %s" % app_name)
        self._apps[app_name] = len(self._apps)
        if self._event_log is not None:
            self._event_log.log(app_name, "INFO", "registered with SB")
        return app_name

    def subscribe(self, app_name, msg_id):
        """Subscribe an app to a message ID (CFE_SB_Subscribe)."""
        _check_msg_id(msg_id)
        if app_name not in self._apps:
            raise ValueError("app not registered: %s" % app_name)
        subs = self._subscribers.setdefault(msg_id, [])
        if app_name not in subs:
            subs.append(app_name)
        if self._event_log is not None:
            self._event_log.log(
                app_name, "INFO", "subscribed to 0x%04X" % msg_id
            )

    def publish(self, msg_id, payload):
        """Publish a payload on a message ID (CFE_SB_SendMsg).

        Raises ValueError when the message ID has no subscribers, the
        cFS equivalent of sending to an unallocated message ID.
        """
        _check_msg_id(msg_id)
        if msg_id not in self._subscribers:
            raise ValueError(
                "publish to unknown message id 0x%04X (no subscribers)"
                % msg_id
            )
        self._queue.append((msg_id, payload))
        if self._event_log is not None:
            self._event_log.log("SB", "DEBUG", "queued 0x%04X" % msg_id)

    def route_messages(self):
        """Drain the queue FIFO; deliver to every subscriber in subscribe
        order. Returns the number of deliveries made in this drain."""
        routed = 0
        while self._queue:
            msg_id, payload = self._queue.pop(0)
            for app_name in self._subscribers.get(msg_id, ()):
                self._delivered.append((app_name, msg_id, payload))
                routed += 1
            if self._event_log is not None:
                self._event_log.log("SB", "DEBUG", "routed 0x%04X" % msg_id)
        return routed

    def pending(self):
        """Number of queued, not yet routed, messages."""
        return len(self._queue)

    def deliveries(self, app_name=None, msg_id=None):
        """Delivered (app, msg_id, payload) triples, optionally filtered."""
        out = self._delivered
        if app_name is not None:
            out = [d for d in out if d[0] == app_name]
        if msg_id is not None:
            out = [d for d in out if d[1] == msg_id]
        return list(out)

    def subscribers(self, msg_id):
        """Apps subscribed to a message ID, in subscribe order."""
        return list(self._subscribers.get(msg_id, ()))


class EventLog:
    """CFE_EVS model: severity-flagged event log with filtering."""

    SEVERITIES = SEVERITIES

    def __init__(self):
        self._entries = []

    def log(self, app_name, severity, message):
        """Append one event entry (CFE_EVS_SendEvent)."""
        if severity not in self.SEVERITIES:
            raise ValueError(
                "unknown severity %r; use one of %s"
                % (severity, ", ".join(self.SEVERITIES))
            )
        entry = {
            "app": app_name,
            "severity": severity,
            "message": message,
            "seq": len(self._entries),
        }
        self._entries.append(entry)
        return entry

    def entries(self, severity=None, app_name=None):
        """Event entries, optionally filtered by severity and app."""
        out = self._entries
        if severity is not None:
            out = [e for e in out if e["severity"] == severity]
        if app_name is not None:
            out = [e for e in out if e["app"] == app_name]
        return list(out)

    def count(self, severity=None):
        """Number of entries, optionally filtered by severity."""
        return len(self.entries(severity=severity))

    def __len__(self):
        return len(self._entries)


def telemetry_pipeline(bus, app_name, tlm_msg_id, payloads, start_seq=0):
    """Publish telemetry payloads stamped with monotonic sequence counters.

    Mirrors CFE_SB_TlmHdr.SeqCnt: every telemetry message on a message ID
    carries an incrementing sequence counter, one per message. Returns the
    list of (msg_id, payload, seq) stamped triples.
    """
    stamped = []
    for i, payload in enumerate(payloads):
        seq = start_seq + i
        stamped.append((tlm_msg_id, payload, seq))
        bus.publish(tlm_msg_id, {"seq": seq, "data": payload})
    bus.route_messages()
    return stamped


def app_skeleton_template():
    """Return the classic cFS app skeleton as source text.

    The canonical cFS app lifecycle: the main function calls APP_Init
    once, then loops on APP_Execute; APP_Execute routes pending software
    bus messages and calls APP_Data for the per-cycle work. This is the
    APP_Init / APP_Execute / APP_Data pattern used by every cFS app.
    """
    return (
        "class MyApp:\n"
        "    # Classic cFS lifecycle: APP_Init once, then loop APP_Execute.\n"
        "    def APP_Init(self, bus, cmd_msg_id, tlm_msg_id):\n"
        "        # One-time startup: register with SB, subscribe to commands.\n"
        "        self.bus = bus\n"
        "        self.tlm_msg_id = tlm_msg_id\n"
        "        self.seq = 0\n"
        "        bus.register_app('MYAPP')\n"
        "        bus.subscribe('MYAPP', cmd_msg_id)\n"
        "\n"
        "    def APP_Execute(self):\n"
        "        # Per-cycle body: route pending messages, then cycle work.\n"
        "        self.bus.route_messages()\n"
        "        self.APP_Data()\n"
        "\n"
        "    def APP_Data(self):\n"
        "        # Process the latest command, then publish telemetry.\n"
        "        self.bus.publish(\n"
        "            self.tlm_msg_id, {'seq': self.seq, 'data': self.state}\n"
        "        )\n"
        "        self.seq += 1\n"
    )


class ScheduledTelemetryApp:
    """Demo cFS app: publishes telemetry every N cycles on a schedule.

    Follows the classic pattern: APP_Init registers and subscribes,
    APP_Execute routes messages and runs the cycle, APP_Data publishes
    one telemetry message stamped with a sequence counter whenever the
    cycle counter hits the configured period.
    """

    def __init__(self, name, bus, cmd_msg_id, tlm_msg_id, period):
        self.name = name
        self.bus = bus
        self.cmd_msg_id = cmd_msg_id
        self.tlm_msg_id = tlm_msg_id
        self.period = period
        self.seq = 0
        self.cycle = 0
        self.commands = []

    def APP_Init(self):
        """One-time startup: register and subscribe to commands."""
        self.bus.register_app(self.name)
        self.bus.subscribe(self.name, self.cmd_msg_id)

    def APP_Execute(self):
        """Per-cycle body: route pending messages, publish on schedule."""
        self.bus.route_messages()
        if self.cycle % self.period == 0:
            self.APP_Data()
        self.cycle += 1

    def APP_Data(self):
        """Publish one telemetry message with the sequence counter."""
        self.bus.publish(
            self.tlm_msg_id, {"seq": self.seq, "cycle": self.cycle}
        )
        self.seq += 1
