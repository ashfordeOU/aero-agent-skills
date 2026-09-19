"""Slot schedule for synchronous command and control on an on-board network.

Anchor: ECSS-E-ST-50C clause 5.7.1.3 -- synchronous command and control on the
on-board communication network. Paraphrased into an implementable procedure;
no standard text is reproduced.

The single normative item asks that the network support command and control
exchanges that are SYNCHRONOUS: each one recurs on its own fixed period, lands
in a reserved place inside a repeating control cycle, and arrives with a
bounded deviation from its nominal instant. That is a schedule, and a schedule
is either laid out or it is not:

  slot          -- payload plus protocol overhead at the link rate, plus the
                   guard time that separates it from its neighbours;
  harmonics     -- a repetition period only fits a cycle when the cycle is a
                   whole multiple of it, or the period a whole multiple of the
                   cycle; anything else cannot be placed at all;
  reservation   -- the worst cycle's slots added up, which is what the cycle
                   has to hold;
  phase error   -- guard plus slot-placement granularity plus the error of the
                   time reference, which is what "synchronous" costs in
                   practice;
  spare         -- the time the cycle has left, which is the whole budget any
                   asynchronous traffic can ever run in.

Sizing is the same model read backwards: the link rate that would make an
oversubscribed cycle fit.
"""

import math

__all__ = [
    "SCHEDULABLE",
    "OVERSUBSCRIBED",
    "NON_HARMONIC",
    "PHASE_ERROR_EXCEEDED",
    "REL_TOL",
    "validate_positive",
    "validate_nonnegative",
    "validate_exchanges",
    "slot_duration_s",
    "is_harmonic",
    "slots_in_worst_cycle",
    "reserved_time_s",
    "synchronous_utilisation",
    "spare_time_s",
    "delivery_phase_error_s",
    "required_link_rate_bps",
    "assess_synchronous_schedule",
]

SCHEDULABLE = "schedulable"
OVERSUBSCRIBED = "oversubscribed"
NON_HARMONIC = "non-harmonic"
PHASE_ERROR_EXCEEDED = "phase-error-exceeded"

# Relative tolerance for the harmonic test and for the cycle-fit comparison, so
# a schedule laid out to exactly fill its cycle is accepted on every host.
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


def validate_exchanges(exchanges, name="exchanges"):
    """Return the command and control exchanges as (name, bits, period) triples.

    An empty set is refused: a control cycle with nothing synchronous in it is
    not a degenerate schedule, it is a missing input.
    """
    if exchanges is None or isinstance(exchanges, (dict, str, bytes)):
        raise ValueError("%s must be a sequence of exchange mappings" % name)
    checked = []
    seen = set()
    for index, exchange in enumerate(exchanges):
        if not isinstance(exchange, dict):
            raise ValueError("%s[%d] must be a mapping" % (name, index))
        missing = {"name", "bits", "period_s"} - set(exchange)
        if missing:
            raise ValueError(
                "%s[%d] is missing %s" % (name, index, ", ".join(sorted(missing)))
            )
        label = exchange["name"]
        if not isinstance(label, str) or not label.strip():
            raise ValueError("%s[%d].name must be a non-empty string" % (name, index))
        if label in seen:
            raise ValueError("%s has two exchanges named %r" % (name, label))
        seen.add(label)
        bits = validate_positive(exchange["bits"], "%s[%d].bits" % (name, index))
        period = validate_positive(
            exchange["period_s"], "%s[%d].period_s" % (name, index)
        )
        checked.append((label, bits, period))
    if not checked:
        raise ValueError("%s must contain at least one exchange" % name)
    return checked


def _near_integer(value):
    nearest = math.floor(value + 0.5)
    return abs(value - nearest) <= REL_TOL * max(1.0, abs(value))


def _snapped_ceil(value):
    if value <= 0.0:
        return 0
    nearest = math.floor(value + 0.5)
    if abs(value - nearest) <= REL_TOL * max(1.0, abs(value)):
        return int(nearest)
    return int(math.ceil(value))


def slot_duration_s(bits, overhead_bits, rate_bps, guard_s=0.0):
    """Return the time one reserved slot occupies, guard time included."""
    payload = validate_positive(bits, "bits")
    overhead = validate_nonnegative(overhead_bits, "overhead_bits")
    rate = validate_positive(rate_bps, "rate_bps")
    guard = validate_nonnegative(guard_s, "guard_s")
    return (payload + overhead) / rate + guard


def is_harmonic(period_s, cycle_s):
    """Say whether a repetition period can be placed in this control cycle."""
    period = validate_positive(period_s, "period_s")
    cycle = validate_positive(cycle_s, "cycle_s")
    return _near_integer(cycle / period) or _near_integer(period / cycle)


def slots_in_worst_cycle(period_s, cycle_s):
    """Return how many slots the busiest cycle has to hold for one exchange.

    An exchange slower than the cycle still needs a whole slot in the cycles it
    does occur in, so the worst cycle holds one, never a fraction of one.
    """
    period = validate_positive(period_s, "period_s")
    cycle = validate_positive(cycle_s, "cycle_s")
    return max(1, _snapped_ceil(cycle / period))


def reserved_time_s(exchanges, cycle_s, rate_bps, overhead_bits=0.0, guard_s=0.0):
    """Return the time the busiest control cycle reserves for synchronous traffic."""
    checked = validate_exchanges(exchanges)
    cycle = validate_positive(cycle_s, "cycle_s")
    total = 0.0
    for _, bits, period in checked:
        slot = slot_duration_s(bits, overhead_bits, rate_bps, guard_s)
        total += slots_in_worst_cycle(period, cycle) * slot
    return total


def synchronous_utilisation(reserved_s, cycle_s):
    """Return the fraction of the control cycle the synchronous schedule takes."""
    reserved = validate_nonnegative(reserved_s, "reserved_s")
    cycle = validate_positive(cycle_s, "cycle_s")
    return reserved / cycle


def spare_time_s(reserved_s, cycle_s):
    """Return the time left in the cycle, never below zero."""
    reserved = validate_nonnegative(reserved_s, "reserved_s")
    cycle = validate_positive(cycle_s, "cycle_s")
    return max(cycle - reserved, 0.0)


def delivery_phase_error_s(guard_s=0.0, granularity_s=0.0, time_reference_error_s=0.0):
    """Return the worst deviation of a command from its nominal instant."""
    guard = validate_nonnegative(guard_s, "guard_s")
    granularity = validate_nonnegative(granularity_s, "granularity_s")
    reference = validate_nonnegative(time_reference_error_s, "time_reference_error_s")
    return guard + granularity + reference


def required_link_rate_bps(exchanges, cycle_s, overhead_bits=0.0, guard_s=0.0):
    """Return the link rate that makes this schedule fit its cycle.

    None means no rate helps: the guard time alone already fills the cycle, so
    the fix is fewer slots or a longer cycle, not a faster link.
    """
    checked = validate_exchanges(exchanges)
    cycle = validate_positive(cycle_s, "cycle_s")
    overhead = validate_nonnegative(overhead_bits, "overhead_bits")
    guard = validate_nonnegative(guard_s, "guard_s")
    bits_total = 0.0
    guard_total = 0.0
    for _, bits, period in checked:
        slots = slots_in_worst_cycle(period, cycle)
        bits_total += slots * (bits + overhead)
        guard_total += slots * guard
    remaining = cycle - guard_total
    if remaining <= 0.0:
        return None
    return bits_total / remaining


def assess_synchronous_schedule(exchanges, cycle_s, rate_bps, overhead_bits=0.0,
                                guard_s=0.0, granularity_s=0.0,
                                time_reference_error_s=0.0,
                                phase_error_budget_s=None):
    """Lay out one control cycle and say whether it holds together."""
    checked = validate_exchanges(exchanges)
    cycle = validate_positive(cycle_s, "cycle_s")
    rate = validate_positive(rate_bps, "rate_bps")
    guard = validate_nonnegative(guard_s, "guard_s")
    breakdown = []
    off_harmonic = []
    reserved = 0.0
    for label, bits, period in checked:
        slot = slot_duration_s(bits, overhead_bits, rate, guard)
        slots = slots_in_worst_cycle(period, cycle)
        reserved += slots * slot
        harmonic = is_harmonic(period, cycle)
        if not harmonic:
            off_harmonic.append(label)
        breakdown.append({
            "name": label,
            "bits": bits,
            "period_s": period,
            "slot_duration_s": slot,
            "slots_per_cycle": slots,
            "harmonic": harmonic,
        })
    utilisation = synchronous_utilisation(reserved, cycle)
    spare = spare_time_s(reserved, cycle)
    phase_error = delivery_phase_error_s(guard, granularity_s, time_reference_error_s)
    budget = None
    if phase_error_budget_s is not None:
        budget = validate_nonnegative(phase_error_budget_s, "phase_error_budget_s")
    fits = reserved <= cycle + REL_TOL * max(1.0, cycle)
    findings = []
    if off_harmonic:
        verdict = NON_HARMONIC
        findings.append(
            "period of %s divides neither into nor by the %.6g s control cycle, "
            "so no fixed slot exists for it" % (", ".join(off_harmonic), cycle)
        )
    elif not fits:
        verdict = OVERSUBSCRIBED
        needed = required_link_rate_bps(checked_as_mappings(checked), cycle,
                                        overhead_bits, guard)
        findings.append(
            "the busiest cycle reserves %.6g s against a %.6g s cycle, so the "
            "schedule cannot be laid out" % (reserved, cycle)
        )
        if needed is None:
            findings.append(
                "no link rate fixes this: guard time alone fills the cycle, so "
                "drop slots or lengthen the cycle"
            )
        else:
            findings.append(
                "a link rate of at least %.6g bit/s, or a cycle of at least "
                "%.6g s, holds this schedule" % (needed, reserved)
            )
    elif budget is not None and phase_error > budget + REL_TOL * max(1.0, budget):
        verdict = PHASE_ERROR_EXCEEDED
        findings.append(
            "the schedule fits, but a %.6g s worst phase error exceeds the "
            "%.6g s budget" % (phase_error, budget)
        )
    else:
        verdict = SCHEDULABLE
    return {
        "cycle_s": cycle,
        "rate_bps": rate,
        "reserved_s": reserved,
        "spare_s": spare,
        "utilisation": utilisation,
        "phase_error_s": phase_error,
        "phase_error_budget_s": budget,
        "fits": fits,
        "required_rate_bps": required_link_rate_bps(
            checked_as_mappings(checked), cycle, overhead_bits, guard
        ),
        "exchanges": breakdown,
        "verdict": verdict,
        "findings": findings,
    }


def checked_as_mappings(checked):
    """Turn validated triples back into mappings the public helpers accept."""
    return [
        {"name": label, "bits": bits, "period_s": period}
        for label, bits, period in checked
    ]
