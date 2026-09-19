"""Accuracy of a time reference distributed to the users that need it.

Anchor: ECSS-E-ST-50C clause 5.7.2.8 -- time distribution.
Paraphrased into an implementable procedure; no standard text is reproduced.

The single normative item is that a time reference is distributed to the
users that need it inside a stated accuracy. That is an end-to-end budget,
not a property of the master clock, so it is evaluated at the consumer:

  chain      -- every distribution hop between the reference and the user
                contributes an uncompensated transport delay, a share of the
                path asymmetry, a share of the timestamp quantization, and a
                random jitter;
  holdover   -- between two distribution messages the consumer runs on its own
                oscillator and walks away from the reference at its drift rate;
  verdict    -- the sum of the two against the accuracy that consumer needs.

Systematic terms add linearly because they are biases that do not cancel;
random terms combine root-sum-square because they are independent. Sizing is
the same model read backwards: the longest distribution period that still
leaves a consumer inside its required accuracy.
"""

import math

__all__ = [
    "WITHIN",
    "EXCEEDED",
    "REL_TOL",
    "HOP_KEYS",
    "validate_nonnegative",
    "validate_positive",
    "validate_hop",
    "hop_error_ns",
    "chain_error_ns",
    "holdover_error_ns",
    "distribution_error_ns",
    "max_distribution_period_s",
    "assess_distribution",
]

WITHIN = "within-accuracy"
EXCEEDED = "accuracy-exceeded"

# Relative tolerance on the accuracy comparison, so a budget that lands exactly
# on the required accuracy reads the same on every build host.
REL_TOL = 1e-9

HOP_KEYS = frozenset(
    [
        "name",
        "delay_ns",
        "compensated",
        "residual_ns",
        "asymmetry_ns",
        "quantization_ns",
        "jitter_ns",
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


def validate_hop(hop):
    """Return one normalized distribution hop.

    A hop declared compensated carries the residual left by the compensation,
    not the whole transport delay; an uncompensated hop carries the delay
    itself, because nothing removed it.
    """
    if not isinstance(hop, dict):
        raise ValueError("hop must be a mapping")
    unknown = sorted(set(hop) - HOP_KEYS)
    if unknown:
        raise ValueError("unknown hop keys: %s" % ", ".join(unknown))
    name = hop.get("name")
    if not isinstance(name, str) or not name.strip():
        raise ValueError("hop name must be a non-empty string")
    compensated = hop.get("compensated", False)
    if not isinstance(compensated, bool):
        raise ValueError("hop %s: compensated must be a boolean" % name)
    return {
        "name": name.strip(),
        "delay_ns": validate_nonnegative(hop.get("delay_ns", 0.0), "delay_ns"),
        "compensated": compensated,
        "residual_ns": validate_nonnegative(hop.get("residual_ns", 0.0), "residual_ns"),
        "asymmetry_ns": validate_nonnegative(
            hop.get("asymmetry_ns", 0.0), "asymmetry_ns"
        ),
        "quantization_ns": validate_nonnegative(
            hop.get("quantization_ns", 0.0), "quantization_ns"
        ),
        "jitter_ns": validate_nonnegative(hop.get("jitter_ns", 0.0), "jitter_ns"),
    }


def hop_error_ns(hop):
    """Return the (systematic, random) nanosecond contribution of one hop."""
    item = validate_hop(hop)
    transport = item["residual_ns"] if item["compensated"] else item["delay_ns"]
    systematic = transport + item["asymmetry_ns"] / 2.0 + item["quantization_ns"] / 2.0
    return systematic, item["jitter_ns"]


def chain_error_ns(hops):
    """Return the budget of a distribution chain, hop by hop."""
    if not isinstance(hops, (list, tuple)) or not hops:
        raise ValueError("hops must be a non-empty sequence")
    systematic = 0.0
    variance = 0.0
    breakdown = []
    for hop in hops:
        sys_ns, rnd_ns = hop_error_ns(hop)
        systematic += sys_ns
        variance += rnd_ns * rnd_ns
        breakdown.append(
            {"name": validate_hop(hop)["name"], "systematic_ns": sys_ns, "random_ns": rnd_ns}
        )
    random_ns = math.sqrt(variance)
    return {
        "hops": len(breakdown),
        "systematic_ns": systematic,
        "random_ns": random_ns,
        "total_ns": systematic + random_ns,
        "breakdown": breakdown,
    }


def holdover_error_ns(drift_ppm, period_s):
    """Return the error a consumer accumulates between distribution messages."""
    drift = validate_nonnegative(drift_ppm, "drift_ppm")
    period = validate_positive(period_s, "period_s")
    return drift * period * 1000.0


def distribution_error_ns(hops, drift_ppm, period_s):
    """Return the end-to-end error delivered to one consumer."""
    chain = chain_error_ns(hops)
    holdover = holdover_error_ns(drift_ppm, period_s)
    total = chain["systematic_ns"] + holdover + chain["random_ns"]
    return {
        "chain_systematic_ns": chain["systematic_ns"],
        "chain_random_ns": chain["random_ns"],
        "holdover_ns": holdover,
        "total_ns": total,
        "breakdown": chain["breakdown"],
    }


def max_distribution_period_s(hops, drift_ppm, required_ns):
    """Return the longest distribution period that keeps a consumer inside spec.

    Zero means the chain on its own already spends the whole allowance, so no
    distribution period saves it. None means the period is not the constraint:
    a consumer with no declared drift does not walk away between messages.
    """
    required = validate_positive(required_ns, "required_ns")
    drift = validate_nonnegative(drift_ppm, "drift_ppm")
    chain = chain_error_ns(hops)
    budget = required - chain["total_ns"]
    if budget <= 0.0:
        return 0.0
    if drift == 0.0:
        return None
    return budget / (drift * 1000.0)


def assess_distribution(consumers):
    """Grade every consumer of the distributed reference against its accuracy."""
    if not isinstance(consumers, (list, tuple)) or not consumers:
        raise ValueError("consumers must be a non-empty sequence")
    results = []
    findings = []
    for consumer in consumers:
        if not isinstance(consumer, dict):
            raise ValueError("consumer must be a mapping")
        name = consumer.get("name")
        if not isinstance(name, str) or not name.strip():
            raise ValueError("consumer name must be a non-empty string")
        required = validate_positive(consumer.get("required_ns"), "required_ns")
        budget = distribution_error_ns(
            consumer.get("hops"),
            consumer.get("drift_ppm", 0.0),
            consumer.get("period_s"),
        )
        tolerance = REL_TOL * required
        within = budget["total_ns"] <= required + tolerance
        longest = max_distribution_period_s(
            consumer.get("hops"), consumer.get("drift_ppm", 0.0), required
        )
        entry = {
            "name": name.strip(),
            "required_ns": required,
            "total_ns": budget["total_ns"],
            "margin_ns": required - budget["total_ns"],
            "holdover_ns": budget["holdover_ns"],
            "chain_systematic_ns": budget["chain_systematic_ns"],
            "chain_random_ns": budget["chain_random_ns"],
            "max_period_s": longest,
            "within": within,
        }
        results.append(entry)
        if not within:
            if longest == 0.0:
                findings.append(
                    "%s: the chain alone spends %.6g ns of a %.6g ns allowance; "
                    "shortening the distribution period cannot recover it"
                    % (name.strip(), budget["chain_systematic_ns"] + budget["chain_random_ns"], required)
                )
            else:
                findings.append(
                    "%s: %.6g ns against a %.6g ns allowance; a distribution "
                    "period of at most %.6g s holds it"
                    % (name.strip(), budget["total_ns"], required, longest)
                )
    worst = min(results, key=lambda r: r["margin_ns"])
    return {
        "consumers": results,
        "worst_consumer": worst["name"],
        "worst_margin_ns": worst["margin_ns"],
        "verdict": WITHIN if all(r["within"] for r in results) else EXCEEDED,
        "findings": findings,
    }
