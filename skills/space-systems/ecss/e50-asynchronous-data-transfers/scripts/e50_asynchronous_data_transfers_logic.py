"""Asynchronous data transfers inside a cyclic on-board network schedule.

Anchor: ECSS-E-ST-50C clause 5.7.1.4 -- asynchronous data transfers on the
on-board communication network. Paraphrased into an implementable procedure;
no standard text is reproduced.

The single normative item asks that the network also carry transfers that
arrive when they arrive: file downloads, event reports, payload dumps, anything
with no reserved slot. On a network whose cycle is already reserved for
synchronous command and control, those transfers live entirely in whatever the
cycle has left, and the question is whether what is left is enough:

  spare window  -- the cycle minus the synchronous reservation, the only time
                   an asynchronous transfer can ever use;
  capacity      -- that window at the link rate, per cycle and sustained;
  segmentation  -- whether the largest message fits one window or has to be
                   cut across several cycles;
  start delay   -- the worst wait before a transfer that becomes ready at the
                   wrong moment gets any of the medium at all;
  completion    -- the whole transfer across as many cycles as it needs.

Sizing is the same model read backwards: the spare window a single-window
transfer needs, and the link rate that would deliver it inside the window the
cycle already has.
"""

import math

__all__ = [
    "ACCOMMODATED",
    "SEGMENTATION_REQUIRED",
    "STARVED",
    "NO_SPARE_WINDOW",
    "REL_TOL",
    "validate_positive",
    "validate_nonnegative",
    "validate_reservation",
    "spare_window_s",
    "window_capacity_bits",
    "sustained_capacity_bps",
    "segments_required",
    "worst_case_start_delay_s",
    "transfer_completion_s",
    "required_spare_time_s",
    "required_link_rate_bps",
    "assess_asynchronous_transfers",
]

ACCOMMODATED = "accommodated"
SEGMENTATION_REQUIRED = "segmentation-required"
STARVED = "starved"
NO_SPARE_WINDOW = "no-spare-window"

# Relative tolerance for the window-fit and capacity comparisons, so a transfer
# sized to exactly fill one spare window needs one segment on every host.
REL_TOL = 1e-9


def _validate_number(value, name):
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise ValueError("%s must be a number" % name)
    number = float(value)
    if math.isnan(number) or math.isinf(number):
        raise ValueError("%s must be finite" % name)
    return number


def validate_positive(value, name):
    """Return a strictly positive float."""
    number = _validate_number(value, name)
    if number <= 0.0:
        raise ValueError("%s must be greater than zero, got %r" % (name, value))
    return number


def validate_nonnegative(value, name):
    """Return a float that is zero or above."""
    number = _validate_number(value, name)
    if number < 0.0:
        raise ValueError("%s must not be negative, got %r" % (name, value))
    return number


def validate_reservation(reserved_s, cycle_s):
    """Return the synchronous reservation, refusing one longer than the cycle.

    A reservation past the end of its own cycle is not a heavily loaded
    network, it is a contradiction carried in from the schedule that produced
    it, and clamping it here would hide the defect one clause upstream.
    """
    cycle = validate_positive(cycle_s, "cycle_s")
    reserved = validate_nonnegative(reserved_s, "reserved_s")
    if reserved > cycle + REL_TOL * max(1.0, cycle):
        raise ValueError(
            "reserved_s %r exceeds the %r s control cycle" % (reserved_s, cycle_s)
        )
    return min(reserved, cycle)


def _snapped_ceil(value):
    if value <= 0.0:
        return 0
    nearest = math.floor(value + 0.5)
    if abs(value - nearest) <= REL_TOL * max(1.0, abs(value)):
        return int(nearest)
    return int(math.ceil(value))


def spare_window_s(cycle_s, reserved_s):
    """Return the time per cycle asynchronous traffic may use."""
    cycle = validate_positive(cycle_s, "cycle_s")
    reserved = validate_reservation(reserved_s, cycle)
    return max(cycle - reserved, 0.0)


def window_capacity_bits(spare_s, rate_bps):
    """Return the bits one spare window can carry."""
    spare = validate_nonnegative(spare_s, "spare_s")
    rate = validate_positive(rate_bps, "rate_bps")
    return spare * rate


def sustained_capacity_bps(capacity_bits, cycle_s):
    """Return the long-run asynchronous throughput the cycle leaves."""
    capacity = validate_nonnegative(capacity_bits, "capacity_bits")
    cycle = validate_positive(cycle_s, "cycle_s")
    return capacity / cycle


def segments_required(total_bits, capacity_bits):
    """Return how many spare windows one message has to be cut across.

    None means it can never be sent: the cycle leaves no spare window at all,
    so no number of segments delivers it.
    """
    total = validate_positive(total_bits, "total_bits")
    capacity = validate_nonnegative(capacity_bits, "capacity_bits")
    if capacity <= 0.0:
        return None
    return max(1, _snapped_ceil(total / capacity))


def worst_case_start_delay_s(cycle_s, reserved_s):
    """Return the longest wait before an asynchronous transfer gets the medium."""
    cycle = validate_positive(cycle_s, "cycle_s")
    return validate_reservation(reserved_s, cycle)


def transfer_completion_s(total_bits, rate_bps, cycle_s, reserved_s):
    """Return the worst-case time to finish one asynchronous message.

    None means it never finishes: there is no spare window to send it in.
    """
    total = validate_positive(total_bits, "total_bits")
    rate = validate_positive(rate_bps, "rate_bps")
    cycle = validate_positive(cycle_s, "cycle_s")
    reserved = validate_reservation(reserved_s, cycle)
    spare = max(cycle - reserved, 0.0)
    if spare <= 0.0:
        return None
    airtime = total / rate
    segments = max(1, _snapped_ceil(airtime / spare))
    last = airtime - (segments - 1) * spare
    if last < 0.0:
        last = 0.0
    return reserved + (segments - 1) * cycle + last


def required_spare_time_s(total_bits, rate_bps):
    """Return the spare window a single-window transfer of this size needs."""
    total = validate_positive(total_bits, "total_bits")
    rate = validate_positive(rate_bps, "rate_bps")
    return total / rate


def required_link_rate_bps(total_bits, spare_s):
    """Return the link rate that fits this message in the window already there.

    None means no rate helps: the cycle leaves no window for it to fit in.
    """
    total = validate_positive(total_bits, "total_bits")
    spare = validate_nonnegative(spare_s, "spare_s")
    if spare <= 0.0:
        return None
    return total / spare


def assess_asynchronous_transfers(cycle_s, reserved_s, rate_bps, message_bits,
                                  overhead_bits=0.0, offered_rate_bps=None):
    """Decide whether the cycle's leftovers carry the asynchronous traffic."""
    cycle = validate_positive(cycle_s, "cycle_s")
    reserved = validate_reservation(reserved_s, cycle)
    rate = validate_positive(rate_bps, "rate_bps")
    payload = validate_positive(message_bits, "message_bits")
    overhead = validate_nonnegative(overhead_bits, "overhead_bits")
    total = payload + overhead
    spare = max(cycle - reserved, 0.0)
    capacity = window_capacity_bits(spare, rate)
    sustained = sustained_capacity_bps(capacity, cycle)
    segments = segments_required(total, capacity)
    completion = transfer_completion_s(total, rate, cycle, reserved)
    offered = None
    if offered_rate_bps is not None:
        offered = validate_nonnegative(offered_rate_bps, "offered_rate_bps")
    findings = []
    if spare <= 0.0:
        verdict = NO_SPARE_WINDOW
        findings.append(
            "the synchronous schedule reserves the whole %.6g s cycle, so no "
            "asynchronous transfer can ever start" % cycle
        )
    elif offered is not None and sustained + REL_TOL * max(1.0, sustained) < offered:
        verdict = STARVED
        findings.append(
            "sustained asynchronous capacity is %.6g bit/s against %.6g bit/s "
            "offered, so the backlog grows every cycle" % (sustained, offered)
        )
    elif segments is not None and segments > 1:
        verdict = SEGMENTATION_REQUIRED
        findings.append(
            "the largest message needs %d spare windows, so it must be "
            "segmented and reassembled across %d cycles" % (segments, segments)
        )
        findings.append(
            "a spare window of at least %.6g s, or a link rate of at least "
            "%.6g bit/s, delivers it in one cycle"
            % (required_spare_time_s(total, rate), required_link_rate_bps(total, spare))
        )
    else:
        verdict = ACCOMMODATED
    if offered is None:
        findings.append(
            "no offered asynchronous rate was declared, so this is a latency "
            "result only and says nothing about sustained throughput"
        )
    return {
        "cycle_s": cycle,
        "reserved_s": reserved,
        "spare_window_s": spare,
        "window_capacity_bits": capacity,
        "sustained_capacity_bps": sustained,
        "offered_rate_bps": offered,
        "message_bits": total,
        "segments_required": segments,
        "worst_case_start_delay_s": reserved,
        "completion_s": completion,
        "fits_one_window": segments == 1,
        "required_spare_time_s": required_spare_time_s(total, rate),
        "required_link_rate_bps": required_link_rate_bps(total, spare),
        "verdict": verdict,
        "findings": findings,
    }
