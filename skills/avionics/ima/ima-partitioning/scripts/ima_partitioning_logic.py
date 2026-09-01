#!/usr/bin/env python3
"""ARINC 653 integrated modular avionics partition logic (stdlib only, deterministic, offline).

Implements, from common engineering practice (paraphrased; the ARINC 653
specification text is proprietary ARINC/SAE ITC material and is not
reproduced here):

- Partition schedule feasibility: within one major frame (MAF) of
  duration maf_ms, each partition i is allocated a window of duration
  d_i ms that repeats every period p_i ms. The frame repeats evenly
  only when every period divides the MAF (the MAF is a common multiple
  of all periods), so a partition with period p_i executes
  MAF / p_i windows per frame. The frame load is the sum of
  d_i x MAF / p_i and must not exceed the MAF; equivalently the
  utilization sum of d_i / p_i must be at most 1. Each window duration
  must also fit inside its own period slot (d_i <= p_i).

- Sampling port latency: a sampling port carries the latest message
  (freshness semantics), written once per sending period and read by
  the receiving partition. Worst-case latency is one sending period
  plus the wire transmission time of the message.

- Queuing port latency: a queuing port carries messages in FIFO order
  with a bounded queue depth; when the queue holds n messages the
  worst-case delivery time is n sending periods plus the transmission
  time of the final message.

Units: durations and periods in milliseconds, message sizes in bytes,
bit rate in bits per second, latency in milliseconds.
"""


def transmission_time_ms(message_bytes, bit_rate_bps):
    """Wire transmission time of one message in milliseconds.

    message_bytes x 8 / bit_rate_bps seconds, scaled to milliseconds.
    Worked: 100 bytes at 100 Mbps is 800 / 1e8 = 8e-6 s = 0.008 ms.
    Raises ValueError for a non-positive bit rate or a negative message
    size.
    """
    if bit_rate_bps <= 0:
        raise ValueError("bit rate must be positive")
    if message_bytes < 0:
        raise ValueError("message size must be non-negative")
    return message_bytes * 8.0 / bit_rate_bps * 1000.0


def frame_load_ms(maf_ms, partitions):
    """Allocated time within one major frame in milliseconds.

    partitions is a list of (name, duration_ms, period_ms) tuples. Each
    partition with period p executes MAF / p windows per frame, so its
    frame allocation is duration x MAF / p. A partition whose period
    does not divide the MAF contributes nothing here (the caller flags
    it as a violation).
    """
    if maf_ms <= 0:
        raise ValueError("major frame duration must be positive")
    load = 0.0
    for _, duration_ms, period_ms in partitions:
        if period_ms <= 0:
            raise ValueError("partition period must be positive")
        if maf_ms % period_ms == 0:
            load += duration_ms * (maf_ms / period_ms)
    return load


def utilization(partitions):
    """Processor utilization, the sum of d_i / p_i over the partitions."""
    return sum(duration_ms / period_ms for _, duration_ms, period_ms in partitions)


def schedule_feasibility(maf_ms, partitions):
    """Partition schedule feasibility verdict as a dict.

    Returns keys: ok, utilization, frame_load_ms, slack_ms, and
    violations (a list of message strings, empty when feasible). The
    schedule is feasible when every partition period is positive and
    divides the MAF, every window duration is positive and fits inside
    its period slot, and the frame load does not exceed the MAF.
    Invalid numeric inputs (non-positive MAF, period, or duration)
    raise ValueError; a valid but over-subscribed or misaligned
    schedule returns ok False with the violations listed.
    """
    if maf_ms <= 0:
        raise ValueError("major frame duration must be positive")
    for name, duration_ms, period_ms in partitions:
        if period_ms <= 0:
            raise ValueError("%s: period must be positive" % name)
        if duration_ms <= 0:
            raise ValueError("%s: duration must be positive" % name)

    violations = []
    for name, duration_ms, period_ms in partitions:
        if maf_ms % period_ms != 0:
            violations.append(
                "%s: period %s ms does not divide the major frame %s ms"
                % (name, period_ms, maf_ms)
            )
        elif duration_ms > period_ms:
            violations.append(
                "%s: duration %s ms exceeds its period slot %s ms"
                % (name, duration_ms, period_ms)
            )

    load = frame_load_ms(maf_ms, partitions)
    util = utilization(partitions)
    if load > maf_ms:
        violations.append(
            "frame load %s ms exceeds the major frame %s ms" % (load, maf_ms)
        )
    ok = not violations and load <= maf_ms
    return {
        "ok": ok,
        "utilization": util,
        "frame_load_ms": load,
        "slack_ms": max(0.0, maf_ms - load),
        "violations": violations,
    }


class PartitionSchedule:
    """A cyclic partition schedule for one major frame.

    Attributes: maf_ms, partitions (the list of (name, duration_ms,
    period_ms) tuples), utilization, frame_load_ms, slack_ms, feasible
    (bool), and violations (list of strings). Construction validates
    the inputs exactly as schedule_feasibility does.
    """

    def __init__(self, maf_ms, partitions):
        self.maf_ms = maf_ms
        self.partitions = list(partitions)
        result = schedule_feasibility(maf_ms, partitions)
        self.utilization = result["utilization"]
        self.frame_load_ms = result["frame_load_ms"]
        self.slack_ms = result["slack_ms"]
        self.feasible = result["ok"]
        self.violations = result["violations"]

    def as_dict(self):
        """Plain dict view of the schedule for a configuration record."""
        return {
            "maf_ms": self.maf_ms,
            "utilization": self.utilization,
            "frame_load_ms": self.frame_load_ms,
            "slack_ms": self.slack_ms,
            "feasible": self.feasible,
            "violations": list(self.violations),
        }


def sampling_port_latency_ms(period_ms, message_bytes, bit_rate_bps,
                             port_message_size=None):
    """Worst-case sampling port latency in milliseconds.

    One sending period plus the wire transmission time of the message.
    Worked: period 10 ms with a 100-byte message at 100 Mbps gives
    10 + 0.008 = 10.008 ms. When port_message_size is given, a message
    larger than the port capacity raises ValueError.
    """
    if period_ms <= 0:
        raise ValueError("sampling period must be positive")
    if port_message_size is not None and message_bytes > port_message_size:
        raise ValueError(
            "message size %s exceeds port capacity %s"
            % (message_bytes, port_message_size)
        )
    return period_ms + transmission_time_ms(message_bytes, bit_rate_bps)


def queuing_port_latency_ms(period_ms, message_bytes, bit_rate_bps,
                            queue_depth, port_message_size=None):
    """Worst-case queuing port latency in milliseconds.

    queue_depth sending periods plus the transmission time of the final
    message; the depth is the number of messages in the queue when the
    new message is appended. Worked: depth 4 at period 10 ms with a
    100-byte message at 100 Mbps gives 4 x 10 + 0.008 = 40.008 ms.
    When port_message_size is given, a message larger than the port
    capacity raises ValueError.
    """
    if period_ms <= 0:
        raise ValueError("queuing period must be positive")
    if queue_depth < 1:
        raise ValueError("queue depth must be at least 1")
    if port_message_size is not None and message_bytes > port_message_size:
        raise ValueError(
            "message size %s exceeds port capacity %s"
            % (message_bytes, port_message_size)
        )
    return queue_depth * period_ms + transmission_time_ms(message_bytes,
                                                          bit_rate_bps)
