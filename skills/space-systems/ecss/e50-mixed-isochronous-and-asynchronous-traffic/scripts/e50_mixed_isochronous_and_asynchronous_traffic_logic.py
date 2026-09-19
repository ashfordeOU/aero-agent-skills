"""Sharing one space link between isochronous and asynchronous traffic.

Anchor: ECSS-E-ST-50C clause 5.6.9 -- mixed isochronous and asynchronous
traffic. Paraphrased into an implementable procedure; no standard text is
reproduced.

The single normative item is that a communication system carrying both kinds
of traffic serves each without destroying the other. Isochronous flows arrive
on a fixed cadence and are useless late; asynchronous traffic can wait but must
not be starved. Both share one link, so the design has to state three things
and be held to them:

  reservation -- the capacity and the slot time the periodic flows take out of
                 the link before anything else is scheduled;
  jitter      -- the departure spread an isochronous frame suffers because a
                 non-preemptive asynchronous transfer was already on the wire;
  starvation  -- the wait an asynchronous frame sees behind the reserved slots,
                 and whether the capacity left can ever clear its offered load.

A design that protects the cadence by leaving no usable capacity for
best-effort traffic has not solved the clause, it has picked a side.
"""

import math

__all__ = [
    "BOTH_SERVED",
    "CADENCE_LOST",
    "ASYNC_STARVED",
    "REL_TOL",
    "validate_rate",
    "validate_positive_rate",
    "validate_period",
    "validate_bits",
    "normalize_flows",
    "isochronous_load_bps",
    "reserved_slot_fraction",
    "spare_capacity_bps",
    "blocking_delay_s",
    "worst_case_jitter_s",
    "async_wait_s",
    "required_link_rate_bps",
    "max_async_unit_bits",
    "assess_mixed_traffic",
]

BOTH_SERVED = "both-served"
CADENCE_LOST = "cadence-lost"
ASYNC_STARVED = "asynchronous-starved"

# Relative tolerance for every bound comparison, so a design sized to land
# exactly on a limit is accepted on every platform rather than on some of them.
REL_TOL = 1e-9


def _validate_number(value, name):
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise ValueError("%s must be a number" % name)
    number = float(value)
    if math.isnan(number) or math.isinf(number):
        raise ValueError("%s must be finite" % name)
    return number


def validate_rate(value, name="rate_bps"):
    """Return a non-negative rate in bits per second."""
    rate = _validate_number(value, name)
    if rate < 0.0:
        raise ValueError("%s must not be negative, got %r" % (name, value))
    return rate


def validate_positive_rate(value, name="link_bps"):
    """Return a strictly positive rate in bits per second."""
    rate = _validate_number(value, name)
    if rate <= 0.0:
        raise ValueError("%s must be greater than zero, got %r" % (name, value))
    return rate


def validate_period(value, name="period_s"):
    """Return a strictly positive period in seconds."""
    period = _validate_number(value, name)
    if period <= 0.0:
        raise ValueError("%s must be greater than zero, got %r" % (name, value))
    return period


def validate_bits(value, name="bits"):
    """Return a non-negative size in bits."""
    size = _validate_number(value, name)
    if size < 0.0:
        raise ValueError("%s must not be negative, got %r" % (name, value))
    return size


def normalize_flows(flows):
    """Return validated isochronous flows as (name, period_s, frame_bits)."""
    if isinstance(flows, (str, bytes)) or not isinstance(flows, (list, tuple)):
        raise ValueError("flows must be a sequence of isochronous flow entries")
    if not flows:
        raise ValueError("flows must not be empty: there is no cadence to protect")
    seen = set()
    out = []
    for entry in flows:
        if isinstance(entry, dict):
            for key in ("name", "period_s", "frame_bits"):
                if key not in entry:
                    raise ValueError("an isochronous flow mapping needs %r" % key)
            name, period, frame = entry["name"], entry["period_s"], entry["frame_bits"]
        elif isinstance(entry, (list, tuple)) and len(entry) == 3:
            name, period, frame = entry
        else:
            raise ValueError("a flow entry must be (name, period_s, frame_bits) or a mapping")
        if not isinstance(name, str) or not name.strip():
            raise ValueError("flow name must be a non-empty string")
        key = name.strip()
        if key in seen:
            raise ValueError("duplicate flow name %r: two entries size the same cadence" % key)
        seen.add(key)
        out.append(
            (
                key,
                validate_period(period, "flow %r period_s" % key),
                validate_bits(frame, "flow %r frame_bits" % key),
            )
        )
    return out


def isochronous_load_bps(flows):
    """Return the mean rate the periodic flows take out of the link."""
    return sum(frame / period for _name, period, frame in normalize_flows(flows))


def reserved_slot_fraction(flows, link_bps):
    """Return the share of link time the periodic flows occupy."""
    link = validate_positive_rate(link_bps)
    return isochronous_load_bps(flows) / link


def spare_capacity_bps(flows, link_bps):
    """Return the capacity left for best-effort traffic.

    Never negative: an over-subscribed reservation leaves nothing, and a
    negative figure there reads as capacity that can be lent out.
    """
    link = validate_positive_rate(link_bps)
    spare = link - isochronous_load_bps(flows)
    if spare < 0.0:
        return 0.0
    return spare


def blocking_delay_s(async_unit_bits, link_bps, preemptible=False):
    """Return the delay a transfer unit already on the wire imposes.

    A preemptible link can interrupt the best-effort transfer, so the periodic
    frame waits for nothing; a non-preemptible one waits for the whole unit.
    """
    unit = validate_bits(async_unit_bits, "async_unit_bits")
    link = validate_positive_rate(link_bps)
    if preemptible:
        return 0.0
    return unit / link


def worst_case_jitter_s(async_unit_bits, link_bps, preemptible=False):
    """Return the cadence spread the asynchronous traffic injects.

    One frame can leave immediately and the next can wait a whole blocking
    interval, so the spread between successive departures is that interval.
    """
    return blocking_delay_s(async_unit_bits, link_bps, preemptible)


def async_wait_s(async_unit_bits, flows, link_bps):
    """Return the time a best-effort unit takes once the reservation is paid.

    None means it never completes: the periodic flows have taken the whole
    link, so there is no capacity left to carry it at all.
    """
    unit = validate_bits(async_unit_bits, "async_unit_bits")
    spare = spare_capacity_bps(flows, link_bps)
    if spare <= 0.0:
        return None
    if unit == 0.0:
        return 0.0
    return unit / spare


def required_link_rate_bps(flows, async_offered_bps, jitter_budget_s=None, async_unit_bits=0.0):
    """Return the link rate that carries both loads inside the jitter budget."""
    offered = validate_rate(async_offered_bps, "async_offered_bps")
    throughput_need = isochronous_load_bps(flows) + offered
    if jitter_budget_s is None:
        return throughput_need
    budget = validate_period(jitter_budget_s, "jitter_budget_s")
    unit = validate_bits(async_unit_bits, "async_unit_bits")
    jitter_need = unit / budget
    return max(throughput_need, jitter_need)


def max_async_unit_bits(link_bps, jitter_budget_s):
    """Return the largest best-effort transfer unit the jitter budget allows."""
    link = validate_positive_rate(link_bps)
    budget = validate_period(jitter_budget_s, "jitter_budget_s")
    return link * budget


def assess_mixed_traffic(
    flows,
    link_bps,
    async_offered_bps,
    async_unit_bits,
    jitter_budget_s,
    preemptible=False,
):
    """Assess one shared link against both the cadence and the best-effort load."""
    pairs = normalize_flows(flows)
    link = validate_positive_rate(link_bps)
    offered = validate_rate(async_offered_bps, "async_offered_bps")
    unit = validate_bits(async_unit_bits, "async_unit_bits")
    budget = validate_period(jitter_budget_s, "jitter_budget_s")
    reserved = sum(frame / period for _name, period, frame in pairs)
    spare = link - reserved
    if spare < 0.0:
        spare = 0.0
    jitter = blocking_delay_s(unit, link, preemptible)
    jitter_tolerance = REL_TOL * max(budget, 1.0)
    cadence_held = jitter <= budget + jitter_tolerance and reserved <= link * (1.0 + REL_TOL)
    spare_tolerance = REL_TOL * max(offered, 1.0)
    async_served = offered <= spare + spare_tolerance
    if not cadence_held:
        verdict = CADENCE_LOST
    elif not async_served:
        verdict = ASYNC_STARVED
    else:
        verdict = BOTH_SERVED
    findings = []
    if reserved > link * (1.0 + REL_TOL):
        findings.append(
            "periodic flows reserve %.6g bit/s of a %.6g bit/s link; the cadence cannot "
            "be met at all" % (reserved, link)
        )
    elif jitter > budget + jitter_tolerance:
        findings.append(
            "a %.6g bit best-effort unit blocks the cadence for %.6g s against a %.6g s "
            "budget; segment it below %.6g bit or make the link preemptible"
            % (unit, jitter, budget, max_async_unit_bits(link, budget))
        )
    if not async_served:
        findings.append(
            "best-effort load of %.6g bit/s exceeds the %.6g bit/s left after the "
            "reservation" % (offered, spare)
        )
    return {
        "flows": [
            {"name": name, "period_s": period, "frame_bits": frame, "rate_bps": frame / period}
            for name, period, frame in pairs
        ],
        "link_bps": link,
        "isochronous_bps": reserved,
        "reserved_fraction": reserved / link,
        "spare_bps": spare,
        "async_offered_bps": offered,
        "async_unit_bits": unit,
        "preemptible": bool(preemptible),
        "worst_case_jitter_s": jitter,
        "jitter_budget_s": budget,
        "jitter_margin_s": budget - jitter,
        "async_wait_s": async_wait_s(unit, pairs, link),
        "max_async_unit_bits": max_async_unit_bits(link, budget),
        "required_link_bps": required_link_rate_bps(pairs, offered, budget, unit),
        "cadence_held": cadence_held,
        "async_served": async_served,
        "verdict": verdict,
        "findings": findings,
    }
