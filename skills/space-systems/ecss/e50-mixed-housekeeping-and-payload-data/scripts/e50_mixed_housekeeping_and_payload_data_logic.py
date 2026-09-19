"""Sharing one downlink between housekeeping telemetry and payload data.

Anchor: ECSS-E-ST-50C clause 5.6.10 -- mixed housekeeping and payload data.
Paraphrased into an implementable procedure; no standard text is reproduced.

The single normative item is that housekeeping and payload data sharing one
communication system each keep their service. They are opposites: housekeeping
is a small, strictly periodic report whose value collapses when it is late,
payload is a large, patient bulk transfer whose value is throughput. Putting
them on one link makes three quantities decide the design:

  reservation  -- the rate housekeeping takes out of the link, frame over
                  cadence, before any payload is scheduled;
  latency      -- the delay a payload transfer unit already on the wire
                  imposes on the next housekeeping report;
  throughput   -- what payload actually gets once housekeeping is paid, and
                  whether the mission volume still fits the contact.

A design that protects the cadence by starving the payload has not met the
clause, and neither has one that meets the volume with a housekeeping report
that arrives after the anomaly it was meant to explain.
"""

import math

__all__ = [
    "BOTH_SERVED",
    "CADENCE_LATE",
    "PAYLOAD_SHORTFALL",
    "REL_TOL",
    "validate_rate",
    "validate_positive_rate",
    "validate_period",
    "validate_bits",
    "housekeeping_rate_bps",
    "housekeeping_share",
    "payload_capacity_bps",
    "payload_unit_blocking_s",
    "housekeeping_latency_s",
    "payload_volume_bits",
    "max_payload_unit_bits",
    "required_link_rate_bps",
    "assess_mixed_downlink",
]

BOTH_SERVED = "both-served"
CADENCE_LATE = "housekeeping-late"
PAYLOAD_SHORTFALL = "payload-shortfall"

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


def housekeeping_rate_bps(hk_frame_bits, hk_period_s):
    """Return the mean rate the housekeeping cadence takes off the link."""
    frame = validate_bits(hk_frame_bits, "hk_frame_bits")
    period = validate_period(hk_period_s, "hk_period_s")
    return frame / period


def housekeeping_share(hk_frame_bits, hk_period_s, link_bps):
    """Return the share of the link the housekeeping cadence occupies."""
    link = validate_positive_rate(link_bps)
    return housekeeping_rate_bps(hk_frame_bits, hk_period_s) / link


def payload_capacity_bps(hk_frame_bits, hk_period_s, link_bps):
    """Return the rate payload actually gets once housekeeping is paid.

    Never negative: a cadence that over-subscribes the link leaves the payload
    nothing, and a negative figure there reads as capacity to lend out.
    """
    link = validate_positive_rate(link_bps)
    spare = link - housekeeping_rate_bps(hk_frame_bits, hk_period_s)
    if spare < 0.0:
        return 0.0
    return spare


def payload_unit_blocking_s(payload_unit_bits, link_bps, preemptible=False):
    """Return the delay a payload transfer unit on the wire imposes.

    A link that can interrupt the payload transfer holds housekeeping for
    nothing; one that cannot holds it for the whole unit.
    """
    unit = validate_bits(payload_unit_bits, "payload_unit_bits")
    link = validate_positive_rate(link_bps)
    if preemptible:
        return 0.0
    return unit / link


def housekeeping_latency_s(hk_frame_bits, payload_unit_bits, link_bps, preemptible=False):
    """Return the worst-case delay from housekeeping ready to housekeeping sent.

    It is the payload unit it has to wait behind plus its own serialisation:
    being scheduled first is not the same as being on the wire.
    """
    frame = validate_bits(hk_frame_bits, "hk_frame_bits")
    link = validate_positive_rate(link_bps)
    return payload_unit_blocking_s(payload_unit_bits, link, preemptible) + frame / link


def payload_volume_bits(hk_frame_bits, hk_period_s, link_bps, contact_s):
    """Return the payload volume a contact of this length can carry."""
    contact = validate_period(contact_s, "contact_s")
    return payload_capacity_bps(hk_frame_bits, hk_period_s, link_bps) * contact


def max_payload_unit_bits(hk_frame_bits, link_bps, latency_budget_s):
    """Return the largest payload unit the housekeeping latency budget allows.

    Zero means no unit fits: the housekeeping frame alone already serialises
    past the budget, so segmenting the payload cannot save it.
    """
    frame = validate_bits(hk_frame_bits, "hk_frame_bits")
    link = validate_positive_rate(link_bps)
    budget = validate_period(latency_budget_s, "latency_budget_s")
    room = link * budget - frame
    if room < 0.0:
        return 0.0
    return room


def required_link_rate_bps(
    hk_frame_bits, hk_period_s, payload_offered_bps, payload_unit_bits=0.0, latency_budget_s=None
):
    """Return the link rate that carries both services inside the budgets."""
    frame = validate_bits(hk_frame_bits, "hk_frame_bits")
    offered = validate_rate(payload_offered_bps, "payload_offered_bps")
    throughput_need = housekeeping_rate_bps(frame, hk_period_s) + offered
    if latency_budget_s is None:
        return throughput_need
    budget = validate_period(latency_budget_s, "latency_budget_s")
    unit = validate_bits(payload_unit_bits, "payload_unit_bits")
    latency_need = (unit + frame) / budget
    return max(throughput_need, latency_need)


def assess_mixed_downlink(
    hk_frame_bits,
    hk_period_s,
    link_bps,
    payload_offered_bps,
    payload_unit_bits,
    hk_latency_budget_s,
    preemptible=False,
):
    """Assess one shared downlink against the cadence and the payload volume."""
    frame = validate_bits(hk_frame_bits, "hk_frame_bits")
    period = validate_period(hk_period_s, "hk_period_s")
    link = validate_positive_rate(link_bps)
    offered = validate_rate(payload_offered_bps, "payload_offered_bps")
    unit = validate_bits(payload_unit_bits, "payload_unit_bits")
    budget = validate_period(hk_latency_budget_s, "hk_latency_budget_s")
    hk_rate = frame / period
    spare = link - hk_rate
    if spare < 0.0:
        spare = 0.0
    latency = housekeeping_latency_s(frame, unit, link, preemptible)
    latency_tolerance = REL_TOL * max(budget, 1.0)
    cadence_ok = latency <= budget + latency_tolerance and hk_rate <= link * (1.0 + REL_TOL)
    payload_tolerance = REL_TOL * max(offered, 1.0)
    payload_ok = offered <= spare + payload_tolerance
    if not cadence_ok:
        verdict = CADENCE_LATE
    elif not payload_ok:
        verdict = PAYLOAD_SHORTFALL
    else:
        verdict = BOTH_SERVED
    allowed_unit = max_payload_unit_bits(frame, link, budget)
    findings = []
    if hk_rate > link * (1.0 + REL_TOL):
        findings.append(
            "housekeeping alone asks %.6g bit/s of a %.6g bit/s link; the cadence itself "
            "does not fit" % (hk_rate, link)
        )
    elif not cadence_ok:
        if allowed_unit == 0.0:
            findings.append(
                "the %.6g bit housekeeping frame serialises past the %.6g s budget on its "
                "own; segmenting the payload cannot recover it" % (frame, budget)
            )
        else:
            findings.append(
                "housekeeping waits %.6g s against a %.6g s budget; cap the payload "
                "transfer unit at %.6g bit or make the link preemptible"
                % (latency, budget, allowed_unit)
            )
    if not payload_ok:
        findings.append(
            "payload offers %.6g bit/s against the %.6g bit/s left after the cadence"
            % (offered, spare)
        )
    return {
        "hk_frame_bits": frame,
        "hk_period_s": period,
        "hk_rate_bps": hk_rate,
        "hk_share": hk_rate / link,
        "link_bps": link,
        "payload_capacity_bps": spare,
        "payload_offered_bps": offered,
        "payload_unit_bits": unit,
        "preemptible": bool(preemptible),
        "hk_latency_s": latency,
        "hk_latency_budget_s": budget,
        "hk_latency_margin_s": budget - latency,
        "max_payload_unit_bits": allowed_unit,
        "required_link_bps": required_link_rate_bps(frame, period, offered, unit, budget),
        "cadence_ok": cadence_ok,
        "payload_ok": payload_ok,
        "verdict": verdict,
        "findings": findings,
    }
