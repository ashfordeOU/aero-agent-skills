"""Error-rate budget for a spacecraft on-board network.

Anchor: ECSS-E-ST-50C clause 5.7.1.8 -- error rates on the on-board
communication network. Paraphrased into an implementable procedure; no
standard text is reproduced.

The single normative item asks that the network's error rate be stated and
met. A bit error rate on its own is not that statement: what a system suffers
is errored FRAMES, at the rate it actually sends them, and what survives the
frame check sequence is worse than either because nothing downstream will ever
notice it. The chain is:

  frame error rate  -- the chance at least one bit of a frame is wrong, which
                       is 1 - (1 - BER)^n and not n*BER once frames are long;
  errored frames    -- that rate at the frames per second the link carries;
  mean time between -- the operator-facing form of the same number, and
   errored frames      undefined rather than infinite on an error-free claim;
  residual rate     -- what slips past a frame check sequence of w bits, the
                       part no retransmission scheme will ever catch;
  mission exposure  -- residual errors expected across the whole mission,
                       which is the figure a data-integrity case rests on.

Sizing is the same chain read backwards: the bit error rate a target frame
error rate demands of the channel.
"""

import math

__all__ = [
    "WITHIN_BUDGET",
    "BER_EXCEEDED",
    "RESIDUAL_EXCEEDED",
    "REL_TOL",
    "validate_probability",
    "validate_positive",
    "validate_nonnegative",
    "validate_bit_count",
    "frame_error_rate",
    "frames_per_second",
    "errored_frames_per_second",
    "mean_time_between_errored_frames_s",
    "residual_undetected_error_rate",
    "undetected_errors_in",
    "required_bit_error_rate",
    "assess_error_rates",
]

WITHIN_BUDGET = "within-budget"
BER_EXCEEDED = "ber-exceeded"
RESIDUAL_EXCEEDED = "residual-exceeded"

# Relative tolerance, taken against the values themselves rather than against
# one, because every rate here is many orders of magnitude below unity and an
# absolute tolerance would wave through a budget missed by a factor of two.
REL_TOL = 1e-9


def _validate_number(value, name):
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise ValueError("%s must be a number" % name)
    number = float(value)
    if math.isnan(number) or math.isinf(number):
        raise ValueError("%s must be finite" % name)
    return number


def validate_probability(value, name):
    """Return a probability, refusing anything outside zero to one."""
    number = _validate_number(value, name)
    if number < 0.0 or number > 1.0:
        raise ValueError("%s must lie between 0 and 1, got %r" % (name, value))
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


def validate_bit_count(value, name, minimum=1):
    """Return a whole number of bits, refusing a fractional frame or field."""
    if isinstance(value, bool) or not isinstance(value, int):
        raise ValueError("%s must be an integer number of bits" % name)
    if value < minimum:
        raise ValueError("%s must be at least %d, got %r" % (name, minimum, value))
    return value


def _within(value, bound):
    """Say whether a value meets a bound, with a tolerance scaled to both."""
    return value <= bound + REL_TOL * max(abs(bound), abs(value))


def frame_error_rate(ber, frame_bits):
    """Return the chance a frame of this length carries at least one bad bit.

    Computed through log1p and expm1 rather than a power, because at the bit
    error rates a spacecraft link works at, (1 - ber)**n loses every
    significant digit of the answer to cancellation.
    """
    rate = validate_probability(ber, "ber")
    bits = validate_bit_count(frame_bits, "frame_bits")
    if rate <= 0.0:
        return 0.0
    if rate >= 1.0:
        return 1.0
    return -math.expm1(bits * math.log1p(-rate))


def frames_per_second(rate_bps, frame_bits):
    """Return how many frames a second the link carries."""
    rate = validate_positive(rate_bps, "rate_bps")
    bits = validate_bit_count(frame_bits, "frame_bits")
    return rate / bits


def errored_frames_per_second(fer, fps):
    """Return how many frames a second arrive damaged."""
    rate = validate_probability(fer, "fer")
    frames = validate_nonnegative(fps, "fps")
    return rate * frames


def mean_time_between_errored_frames_s(fer, fps):
    """Return the mean seconds between damaged frames.

    None means undefined, not infinite: either the channel was declared
    error-free or the link carries no frames, and quoting a number there
    invents a guarantee.
    """
    rate = validate_probability(fer, "fer")
    frames = validate_nonnegative(fps, "fps")
    errored = rate * frames
    if errored <= 0.0:
        return None
    return 1.0 / errored


def residual_undetected_error_rate(fer, fcs_bits):
    """Return the share of damaged frames a frame check sequence lets through.

    The usual engineering bound: a check sequence of w bits maps a damaged
    frame onto the correct syndrome with probability 2**-w. Computed with
    ldexp, which is exact, rather than a power of two built by multiplication.
    """
    rate = validate_probability(fer, "fer")
    width = validate_bit_count(fcs_bits, "fcs_bits", minimum=0)
    return rate * math.ldexp(1.0, -width)


def undetected_errors_in(duration_s, residual_rate, fps):
    """Return the residual errors expected across a span of mission time."""
    duration = validate_nonnegative(duration_s, "duration_s")
    residual = validate_probability(residual_rate, "residual_rate")
    frames = validate_nonnegative(fps, "fps")
    return residual * frames * duration


def required_bit_error_rate(target_fer, frame_bits):
    """Return the channel bit error rate a target frame error rate demands."""
    target = validate_probability(target_fer, "target_fer")
    bits = validate_bit_count(frame_bits, "frame_bits")
    if target <= 0.0:
        return 0.0
    if target >= 1.0:
        return 1.0
    return -math.expm1(math.log1p(-target) / bits)


def assess_error_rates(ber, frame_bits, rate_bps, fcs_bits=32,
                       mission_duration_s=0.0, required_ber=None,
                       required_residual_rate=None):
    """Grade one link against the error-rate budget written for it."""
    achieved_ber = validate_probability(ber, "ber")
    bits = validate_bit_count(frame_bits, "frame_bits")
    fps = frames_per_second(rate_bps, bits)
    fer = frame_error_rate(achieved_ber, bits)
    errored = errored_frames_per_second(fer, fps)
    mtbe = mean_time_between_errored_frames_s(fer, fps)
    residual = residual_undetected_error_rate(fer, fcs_bits)
    duration = validate_nonnegative(mission_duration_s, "mission_duration_s")
    exposure = undetected_errors_in(duration, residual, fps)
    ber_bound = None
    residual_bound = None
    findings = []
    if required_ber is not None:
        ber_bound = validate_probability(required_ber, "required_ber")
    if required_residual_rate is not None:
        residual_bound = validate_probability(
            required_residual_rate, "required_residual_rate"
        )
    ber_ok = ber_bound is None or _within(achieved_ber, ber_bound)
    residual_ok = residual_bound is None or _within(residual, residual_bound)
    if not ber_ok:
        verdict = BER_EXCEEDED
        findings.append(
            "channel bit error rate %.6g exceeds the required %.6g, so the "
            "frame error rate below it is already out of budget"
            % (achieved_ber, ber_bound)
        )
        findings.append(
            "a frame error rate of %.6g would need a bit error rate of %.6g "
            "on this frame length"
            % (fer, required_bit_error_rate(fer, bits))
        )
    elif not residual_ok:
        verdict = RESIDUAL_EXCEEDED
        findings.append(
            "residual undetected error rate %.6g exceeds the required %.6g "
            "even though the bit error rate is met; widen the frame check "
            "sequence or shorten the frame" % (residual, residual_bound)
        )
    else:
        verdict = WITHIN_BUDGET
    if achieved_ber <= 0.0:
        findings.append(
            "a zero bit error rate is a claim rather than a measurement, so "
            "the mean time between errored frames is undefined here"
        )
    if ber_bound is None and residual_bound is None:
        findings.append(
            "no required error rate was declared, so this is a computed budget "
            "and not a verdict against a requirement"
        )
    if duration <= 0.0:
        findings.append(
            "no mission duration was declared, so the residual error exposure "
            "is reported as zero and carries no integrity claim"
        )
    return {
        "ber": achieved_ber,
        "frame_bits": bits,
        "frames_per_second": fps,
        "frame_error_rate": fer,
        "errored_frames_per_second": errored,
        "mean_time_between_errored_frames_s": mtbe,
        "fcs_bits": validate_bit_count(fcs_bits, "fcs_bits", minimum=0),
        "residual_undetected_error_rate": residual,
        "mission_duration_s": duration,
        "undetected_errors_expected": exposure,
        "required_ber": ber_bound,
        "required_residual_rate": residual_bound,
        "ber_within_budget": ber_ok,
        "residual_within_budget": residual_ok,
        "verdict": verdict,
        "findings": findings,
    }
