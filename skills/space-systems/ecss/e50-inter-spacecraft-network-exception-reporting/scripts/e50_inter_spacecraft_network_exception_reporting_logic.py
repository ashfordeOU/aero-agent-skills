"""Exception reporting on an inter-spacecraft network.

Anchor: ECSS-E-ST-50C clause 5.7.4.4 -- inter-spacecraft network exception
reporting. Paraphrased into an implementable procedure; no standard text is
reproduced.

The single normative item is that the network reports its exceptions to the
entity that manages it. Reporting is only real if the report arrives, so the
assessment follows an exception through the three places one is lost:

  latency     -- detection, queueing, propagation across the network and
                 relay forwarding, against the time that severity is allowed
                 to stay unreported;
  retention   -- exceptions raised while the path to the manager is down have
                 to be held until it returns, which is a store size;
  suppression -- a rate limiter protecting the link discards whatever it does
                 not pass, and a discarded exception is an unreported one.

Severity groups matter to the third of these: a limiter shared across groups
lets a storm of routine reports crowd out the one report that mattered, so
the model treats a shared limiter and a per-group limiter as different
designs and says which one is in front of it.
"""

import math

__all__ = [
    "REPORTED",
    "LOST",
    "SEVERITY_ORDER",
    "REL_TOL",
    "FLOW_KEYS",
    "validate_nonnegative",
    "validate_positive",
    "validate_count",
    "validate_severity",
    "validate_flow",
    "reporting_latency_s",
    "retention_bits",
    "sustainable_rate_per_s",
    "suppressed_per_s",
    "highest_severity",
    "assess_exception_reporting",
]

REPORTED = "exceptions-reported"
LOST = "exceptions-lost"

# Severity groups, most urgent first. The order decides which group a shared
# rate limiter is allowed to damage, and the answer is none of them.
SEVERITY_ORDER = {"alarm": 0, "warning": 1, "notice": 2}

REL_TOL = 1e-9

FLOW_KEYS = frozenset(
    [
        "severity",
        "rate_per_s",
        "record_bits",
        "detection_s",
        "queueing_s",
        "hops",
        "hop_latency_s",
        "forwarding_s",
        "required_latency_s",
    ]
)


def _number(value, name):
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise ValueError("%s must be a number" % name)
    number = float(value)
    if math.isnan(number) or math.isinf(number):
        raise ValueError("%s must be finite" % name)
    return number


def validate_nonnegative(value, name="value"):
    """Return a non-negative float."""
    number = _number(value, name)
    if number < 0.0:
        raise ValueError("%s must not be negative, got %r" % (name, value))
    return number


def validate_positive(value, name="value"):
    """Return a strictly positive float."""
    number = _number(value, name)
    if number <= 0.0:
        raise ValueError("%s must be greater than zero, got %r" % (name, value))
    return number


def validate_count(value, name="count"):
    """Return a strictly positive whole count."""
    if isinstance(value, bool) or not isinstance(value, int):
        raise ValueError("%s must be a whole number" % name)
    if value <= 0:
        raise ValueError("%s must be greater than zero, got %r" % (name, value))
    return value


def validate_severity(value):
    """Return a known severity group name."""
    if not isinstance(value, str):
        raise ValueError("severity must be a string")
    name = value.strip().lower()
    if name not in SEVERITY_ORDER:
        raise ValueError(
            "unknown severity %r; expected one of %s"
            % (value, ", ".join(sorted(SEVERITY_ORDER, key=SEVERITY_ORDER.get)))
        )
    return name


def validate_flow(flow):
    """Return one normalized exception flow, grouped by severity."""
    if not isinstance(flow, dict):
        raise ValueError("flow must be a mapping")
    unknown = sorted(set(flow) - FLOW_KEYS)
    if unknown:
        raise ValueError("unknown flow keys: %s" % ", ".join(unknown))
    return {
        "severity": validate_severity(flow.get("severity")),
        "rate_per_s": validate_nonnegative(flow.get("rate_per_s", 0.0), "rate_per_s"),
        "record_bits": validate_positive(flow.get("record_bits"), "record_bits"),
        "detection_s": validate_nonnegative(flow.get("detection_s", 0.0), "detection_s"),
        "queueing_s": validate_nonnegative(flow.get("queueing_s", 0.0), "queueing_s"),
        "hops": validate_count(flow.get("hops", 1), "hops"),
        "hop_latency_s": validate_nonnegative(
            flow.get("hop_latency_s", 0.0), "hop_latency_s"
        ),
        "forwarding_s": validate_nonnegative(
            flow.get("forwarding_s", 0.0), "forwarding_s"
        ),
        "required_latency_s": validate_positive(
            flow.get("required_latency_s"), "required_latency_s"
        ),
    }


def reporting_latency_s(detection_s, queueing_s, hops, hop_latency_s, forwarding_s):
    """Return how long an exception takes to reach the managing entity."""
    detect = validate_nonnegative(detection_s, "detection_s")
    queue = validate_nonnegative(queueing_s, "queueing_s")
    count = validate_count(hops, "hops")
    latency = validate_nonnegative(hop_latency_s, "hop_latency_s")
    forward = validate_nonnegative(forwarding_s, "forwarding_s")
    return detect + queue + count * latency + forward


def retention_bits(rate_per_s, outage_s, record_bits):
    """Return the store an outage of this length asks for."""
    rate = validate_nonnegative(rate_per_s, "rate_per_s")
    outage = validate_positive(outage_s, "outage_s")
    record = validate_positive(record_bits, "record_bits")
    return rate * outage * record


def sustainable_rate_per_s(store_bits, outage_s, record_bits):
    """Return the exception rate a given store survives across an outage."""
    store = validate_nonnegative(store_bits, "store_bits")
    outage = validate_positive(outage_s, "outage_s")
    record = validate_positive(record_bits, "record_bits")
    return store / (outage * record)


def suppressed_per_s(offered_per_s, limit_per_s):
    """Return the exceptions per second a rate limiter discards."""
    offered = validate_nonnegative(offered_per_s, "offered_per_s")
    limit = validate_nonnegative(limit_per_s, "limit_per_s")
    excess = offered - limit
    if excess <= 0.0:
        return 0.0
    return excess


def highest_severity(flows):
    """Return the most urgent severity group present among the flows."""
    normalized = [validate_flow(flow) for flow in flows]
    if not normalized:
        raise ValueError("flows must be a non-empty sequence")
    return min(normalized, key=lambda f: SEVERITY_ORDER[f["severity"]])["severity"]


def assess_exception_reporting(
    flows, outage_s, store_bits, limit_per_s, limiter_per_severity=False
):
    """Grade the exception reporting of one inter-spacecraft network."""
    if not isinstance(flows, (list, tuple)) or not flows:
        raise ValueError("flows must be a non-empty sequence")
    if not isinstance(limiter_per_severity, bool):
        raise ValueError("limiter_per_severity must be a boolean")
    outage = validate_positive(outage_s, "outage_s")
    store = validate_nonnegative(store_bits, "store_bits")
    limit = validate_nonnegative(limit_per_s, "limit_per_s")
    normalized = [validate_flow(flow) for flow in flows]

    findings = []
    per_flow = []
    needed_bits = 0.0
    offered_total = 0.0
    for flow in normalized:
        latency = reporting_latency_s(
            flow["detection_s"],
            flow["queueing_s"],
            flow["hops"],
            flow["hop_latency_s"],
            flow["forwarding_s"],
        )
        allowance = flow["required_latency_s"]
        latency_ok = latency <= allowance + REL_TOL * allowance
        held = retention_bits(flow["rate_per_s"], outage, flow["record_bits"])
        needed_bits += held
        offered_total += flow["rate_per_s"]
        dropped = (
            suppressed_per_s(flow["rate_per_s"], limit) if limiter_per_severity else 0.0
        )
        entry = {
            "severity": flow["severity"],
            "latency_s": latency,
            "required_latency_s": allowance,
            "latency_margin_s": allowance - latency,
            "latency_within_allowance": latency_ok,
            "retention_bits": held,
            "suppressed_per_s": dropped,
        }
        per_flow.append(entry)
        if not latency_ok:
            findings.append(
                "%s exceptions reach the manager in %.6g s against a %.6g s "
                "allowance" % (flow["severity"], latency, allowance)
            )
        if dropped > 0.0:
            findings.append(
                "%s limiter discards %.6g exception/s; a discarded exception is "
                "never reported" % (flow["severity"], dropped)
            )

    shared_dropped = (
        0.0 if limiter_per_severity else suppressed_per_s(offered_total, limit)
    )
    if shared_dropped > 0.0:
        findings.append(
            "one limiter shared across severity groups discards %.6g "
            "exception/s of a %.6g exception/s offered load, so a routine storm "
            "can crowd out an %s report; give each severity group its own share"
            % (shared_dropped, offered_total, highest_severity(normalized))
        )

    retention_ok = needed_bits <= store + REL_TOL * max(store, needed_bits, 1.0)
    if not retention_ok:
        worst = max(normalized, key=lambda f: f["record_bits"])
        findings.append(
            "holding %.6g s of exceptions needs %.6g bit against a %.6g bit "
            "store; either provide that store or hold the offered rate at "
            "%.6g exception/s"
            % (
                outage,
                needed_bits,
                store,
                sustainable_rate_per_s(store, outage, worst["record_bits"]),
            )
        )

    latency_ok_all = all(e["latency_within_allowance"] for e in per_flow)
    suppression_ok = shared_dropped == 0.0 and all(
        e["suppressed_per_s"] == 0.0 for e in per_flow
    )
    return {
        "flows": per_flow,
        "outage_s": outage,
        "store_bits": store,
        "required_store_bits": needed_bits,
        "offered_per_s": offered_total,
        "limit_per_s": limit,
        "limiter_per_severity": limiter_per_severity,
        "shared_limiter_suppressed_per_s": shared_dropped,
        "highest_severity": highest_severity(normalized),
        "latency_ok": latency_ok_all,
        "retention_ok": retention_ok,
        "suppression_ok": suppression_ok,
        "verdict": REPORTED
        if (latency_ok_all and retention_ok and suppression_ok)
        else LOST,
        "findings": findings,
    }
