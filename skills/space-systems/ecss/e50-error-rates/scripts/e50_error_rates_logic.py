"""Error-rate budgeting for a ground network data path.

Anchor: ECSS-E-ST-50C clause 5.8.4 -- error rates on the ground network.
Paraphrased into an implementable procedure; no standard text is reproduced.

The single normative item is that the ground network delivers data at or below
a stated error rate. A stated rate is only usable once three questions are
answered with the same arithmetic:

  composition   -- a path is a chain of segments, and the end-to-end error
                   rate is one minus the probability that every segment passes
                   the unit intact;
  granularity   -- an error rate quoted per bit and an error rate quoted per
                   frame are different numbers, and the conversion is
                   1 - (1 - ber) ** bits, not ber * bits;
  apportionment -- an end-to-end requirement is met by segments, so the useful
                   inverse is the per-segment rate each hop has to hold.

Volume figures over a pass (errored bits, errored blocks, errored seconds) turn
the rate into something an operator can compare with a log, and the headroom is
reported as a ratio and in decibels so it can be read either way.
"""

import math

__all__ = [
    "COMPLIANT",
    "MARGINAL",
    "NON_COMPLIANT",
    "REL_TOL",
    "validate_probability",
    "validate_bits",
    "validate_duration",
    "validate_margin_factor",
    "block_error_rate",
    "chain_error_rate",
    "allocate_segment_error_rate",
    "expected_errored_bits",
    "expected_errored_blocks",
    "errored_second_ratio",
    "margin_ratio",
    "margin_db",
    "assess_error_rates",
]

COMPLIANT = "compliant"
MARGINAL = "marginal"
NON_COMPLIANT = "non-compliant"

# Relative tolerance for every comparison against a bound, so a path sized to
# land exactly on its requirement is graded the same way on every platform.
REL_TOL = 1e-9


def _validate_number(value, name):
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise ValueError("%s must be a number" % name)
    number = float(value)
    if math.isnan(number) or math.isinf(number):
        raise ValueError("%s must be finite" % name)
    return number


def validate_probability(value, name="probability"):
    """Return an error rate in the closed interval zero to one."""
    p = _validate_number(value, name)
    if p < 0.0 or p > 1.0:
        raise ValueError("%s must lie between 0 and 1, got %r" % (name, value))
    return p


def validate_bits(value, name="bits"):
    """Return a strictly positive bit count."""
    bits = _validate_number(value, name)
    if bits <= 0.0:
        raise ValueError("%s must be greater than zero, got %r" % (name, value))
    return bits


def validate_duration(value, name="duration_s"):
    """Return a strictly positive duration in seconds."""
    duration = _validate_number(value, name)
    if duration <= 0.0:
        raise ValueError("%s must be greater than zero, got %r" % (name, value))
    return duration


def validate_margin_factor(value, name="margin_factor"):
    """Return a headroom factor of one or more.

    A factor of one means the requirement itself is the only bound and the
    marginal band is empty, which is a legitimate choice but has to be stated.
    """
    factor = _validate_number(value, name)
    if factor < 1.0:
        raise ValueError("%s must be at least 1, got %r" % (name, value))
    return factor


def block_error_rate(ber, block_bits):
    """Return the probability that a block of this size carries an error.

    Computed through log1p and expm1 so a small bit error rate over a large
    block neither vanishes nor saturates.
    """
    p = validate_probability(ber, "ber")
    bits = validate_bits(block_bits, "block_bits")
    if p == 0.0:
        return 0.0
    if p == 1.0:
        return 1.0
    return -math.expm1(bits * math.log1p(-p))


def chain_error_rate(segment_rates):
    """Return the end-to-end error rate of segments crossed in series."""
    if isinstance(segment_rates, (str, bytes)) or not isinstance(
        segment_rates, (list, tuple)
    ):
        raise ValueError("segment_rates must be a list or tuple of error rates")
    if len(segment_rates) == 0:
        raise ValueError("segment_rates must name at least one segment")
    total = 0.0
    for index, rate in enumerate(segment_rates):
        q = validate_probability(rate, "segment_rates[%d]" % index)
        if q == 1.0:
            return 1.0
        total += math.log1p(-q)
    return -math.expm1(total)


def allocate_segment_error_rate(end_to_end_target, segments):
    """Return the equal per-segment rate that composes to the target."""
    target = validate_probability(end_to_end_target, "end_to_end_target")
    if isinstance(segments, bool) or not isinstance(segments, int):
        raise ValueError("segments must be an integer count")
    if segments < 1:
        raise ValueError("segments must be at least 1, got %r" % (segments,))
    if target == 0.0:
        return 0.0
    if target == 1.0:
        return 1.0
    return -math.expm1(math.log1p(-target) / segments)


def expected_errored_bits(ber, rate_bps, duration_s):
    """Return the bits expected to arrive in error over a pass."""
    p = validate_probability(ber, "ber")
    rate = validate_bits(rate_bps, "rate_bps")
    duration = validate_duration(duration_s)
    return p * rate * duration


def expected_errored_blocks(ber, block_bits, blocks):
    """Return the blocks expected to arrive in error out of a count."""
    count = validate_bits(blocks, "blocks")
    return block_error_rate(ber, block_bits) * count


def errored_second_ratio(ber, rate_bps):
    """Return the fraction of seconds that carry at least one error."""
    return block_error_rate(ber, validate_bits(rate_bps, "rate_bps"))


def margin_ratio(achieved_rate, required_rate):
    """Return how many times better than its requirement a path is.

    None means the ratio is unbounded: the path shows no errors at all, and a
    finite headroom figure there would be an invention.
    """
    achieved = validate_probability(achieved_rate, "achieved_rate")
    required = validate_probability(required_rate, "required_rate")
    if required == 0.0:
        raise ValueError("required_rate of zero admits no finite margin")
    if achieved == 0.0:
        return None
    return required / achieved


def margin_db(achieved_rate, required_rate):
    """Return the headroom of a path in decibels, or None when unbounded."""
    ratio = margin_ratio(achieved_rate, required_rate)
    if ratio is None:
        return None
    return 10.0 * math.log10(ratio)


def assess_error_rates(
    segment_rates,
    required_end_to_end,
    block_bits=None,
    rate_bps=None,
    duration_s=None,
    margin_factor=2.0,
):
    """Grade a ground network path against its end-to-end error requirement."""
    required = validate_probability(required_end_to_end, "required_end_to_end")
    factor = validate_margin_factor(margin_factor)
    achieved = chain_error_rate(segment_rates)
    segments = len(segment_rates)
    goal = required / factor
    tolerance = REL_TOL * max(required, 1e-300)
    if achieved <= goal + tolerance:
        verdict = COMPLIANT
    elif achieved <= required + tolerance:
        verdict = MARGINAL
    else:
        verdict = NON_COMPLIANT
    findings = []
    if verdict == NON_COMPLIANT:
        findings.append(
            "path composes to %.6g against a requirement of %.6g; the network "
            "does not meet the stated error rate" % (achieved, required)
        )
    elif verdict == MARGINAL:
        findings.append(
            "path composes to %.6g and meets %.6g, but holds less than the "
            "factor of %.6g of headroom asked for" % (achieved, required, factor)
        )
    per_segment = allocate_segment_error_rate(goal, segments)
    if verdict != COMPLIANT:
        findings.append(
            "each of the %d segments has to hold %.6g or better for the path to "
            "reach the target with its headroom" % (segments, per_segment)
        )
    worst_index = None
    worst_rate = -1.0
    for index, rate in enumerate(segment_rates):
        value = float(rate)
        if value > worst_rate:
            worst_rate = value
            worst_index = index
    result = {
        "segments": segments,
        "segment_rates": [float(r) for r in segment_rates],
        "achieved_end_to_end": achieved,
        "required_end_to_end": required,
        "margin_factor": factor,
        "goal_with_margin": goal,
        "margin_ratio": margin_ratio(achieved, required) if required > 0.0 else None,
        "margin_db": margin_db(achieved, required) if required > 0.0 else None,
        "per_segment_allocation": per_segment,
        "worst_segment_index": worst_index,
        "worst_segment_rate": worst_rate,
        "verdict": verdict,
        "findings": findings,
    }
    if block_bits is not None:
        result["block_error_rate"] = block_error_rate(achieved, block_bits)
    if rate_bps is not None and duration_s is not None:
        result["errored_bits_per_pass"] = expected_errored_bits(
            achieved, rate_bps, duration_s
        )
        result["errored_second_ratio"] = errored_second_ratio(achieved, rate_bps)
    return result
