"""Isochronous service conformance for a space communication link.

Anchor: ECSS-E-ST-50C clause 5.6.14.4 -- isochronous services.
Paraphrased into an implementable procedure; no standard text is reproduced.

The single normative item is that where an isochronous service is provided, the
deliveries it makes arrive on a fixed cadence -- not merely at the right average
rate. An average is the wrong instrument: a stream that slips a little on every
interval keeps a perfect average while walking steadily off the grid, and a
stream that alternates early and late keeps a perfect average while never being
on time. Both are graded here against the grid itself.

The model is deterministic and small:

  deviation   -- how far each delivery sits from its slot on an ideal grid of
                 the nominal period, anchored at a declared epoch or at the
                 first delivery;
  jitter      -- the peak-to-peak spread of those deviations, which is also the
                 playout buffer that would re-time the stream;
  rate error  -- the difference between the interval actually measured and the
                 nominal period, which is the part of a failure that grows with
                 the length of the run rather than staying bounded.

Sizing is the same model read backwards: the smallest tolerance the observed run
would have passed under, and the buffer needed to make it look on time.
"""

import math

__all__ = [
    "ISOCHRONOUS",
    "JITTER_EXCEEDED",
    "RATE_DRIFT",
    "REL_TOL",
    "validate_period",
    "validate_tolerance",
    "validate_delivery_times",
    "ideal_grid",
    "deviations",
    "peak_to_peak_jitter",
    "worst_deviation",
    "measured_period",
    "rate_error",
    "sustainable_rate_error",
    "minimum_tolerance",
    "required_playout_buffer_s",
    "required_playout_buffer_bits",
    "assess_isochronous_service",
]

ISOCHRONOUS = "isochronous"
JITTER_EXCEEDED = "jitter-exceeded"
RATE_DRIFT = "rate-drift"

# Relative tolerance for every bound comparison, so a run sized to sit exactly
# on the permitted jitter is accepted on every platform rather than on some.
REL_TOL = 1e-9


def _validate_number(value, name):
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise ValueError("%s must be a number" % name)
    number = float(value)
    if math.isnan(number) or math.isinf(number):
        raise ValueError("%s must be finite" % name)
    return number


def validate_period(value, name="nominal_period_s"):
    """Return a strictly positive nominal period in seconds."""
    period = _validate_number(value, name)
    if period <= 0.0:
        raise ValueError("%s must be greater than zero, got %r" % (name, value))
    return period


def validate_tolerance(value, name="jitter_tolerance_s"):
    """Return a non-negative jitter tolerance in seconds."""
    tolerance = _validate_number(value, name)
    if tolerance < 0.0:
        raise ValueError("%s must not be negative, got %r" % (name, value))
    return tolerance


def validate_delivery_times(values, name="delivery_times_s"):
    """Return at least two strictly increasing delivery times in seconds."""
    if isinstance(values, (str, bytes)) or not isinstance(values, (list, tuple)):
        raise ValueError("%s must be a list or tuple of times" % name)
    if len(values) < 2:
        raise ValueError("%s needs at least two deliveries to have a cadence" % name)
    times = [_validate_number(v, "%s[%d]" % (name, i)) for i, v in enumerate(values)]
    for index in range(1, len(times)):
        if times[index] <= times[index - 1]:
            raise ValueError(
                "%s must strictly increase; %s[%d] does not follow %s[%d]"
                % (name, name, index, name, index - 1)
            )
    return times


def ideal_grid(epoch_s, nominal_period_s, count):
    """Return the slot times an isochronous service of this period should hit."""
    epoch = _validate_number(epoch_s, "epoch_s")
    period = validate_period(nominal_period_s)
    if isinstance(count, bool) or not isinstance(count, int):
        raise ValueError("count must be an integer")
    if count < 1:
        raise ValueError("count must be at least one, got %r" % (count,))
    return [epoch + index * period for index in range(count)]


def deviations(delivery_times_s, nominal_period_s, epoch_s=None):
    """Return how far each delivery sits from its slot, in seconds.

    A positive value is late, a negative value is early. With no epoch given the
    grid is anchored at the first delivery, which is the honest default when the
    service has no declared start.
    """
    times = validate_delivery_times(delivery_times_s)
    period = validate_period(nominal_period_s)
    epoch = times[0] if epoch_s is None else _validate_number(epoch_s, "epoch_s")
    grid = ideal_grid(epoch, period, len(times))
    return [times[index] - grid[index] for index in range(len(times))]


def peak_to_peak_jitter(devs):
    """Return the spread between the latest and the earliest deviation."""
    if not devs:
        raise ValueError("devs must not be empty")
    return max(devs) - min(devs)


def worst_deviation(devs):
    """Return the largest deviation from a slot, ignoring its sign."""
    if not devs:
        raise ValueError("devs must not be empty")
    return max(abs(value) for value in devs)


def measured_period(delivery_times_s):
    """Return the interval the stream actually ran at, in seconds."""
    times = validate_delivery_times(delivery_times_s)
    return (times[-1] - times[0]) / float(len(times) - 1)


def rate_error(delivery_times_s, nominal_period_s):
    """Return measured interval less nominal period, in seconds per delivery."""
    period = validate_period(nominal_period_s)
    return measured_period(delivery_times_s) - period


def sustainable_rate_error(jitter_tolerance_s, count):
    """Return the per-delivery rate error a run of this length can absorb.

    None means the question is not asked: a single interval has no accumulation
    over which a rate error could exhaust the jitter budget.
    """
    tolerance = validate_tolerance(jitter_tolerance_s)
    if isinstance(count, bool) or not isinstance(count, int):
        raise ValueError("count must be an integer")
    if count < 2:
        return None
    return tolerance / float(count - 1)


def minimum_tolerance(delivery_times_s, nominal_period_s, epoch_s=None):
    """Return the smallest jitter tolerance this run would have passed under."""
    return worst_deviation(deviations(delivery_times_s, nominal_period_s, epoch_s))


def required_playout_buffer_s(delivery_times_s, nominal_period_s, epoch_s=None):
    """Return the seconds of playout buffer that would re-time this stream."""
    return peak_to_peak_jitter(deviations(delivery_times_s, nominal_period_s, epoch_s))


def required_playout_buffer_bits(buffer_s, source_bps):
    """Return the playout buffer in bits for a source running at this rate."""
    span = _validate_number(buffer_s, "buffer_s")
    if span < 0.0:
        raise ValueError("buffer_s must not be negative, got %r" % (buffer_s,))
    rate = _validate_number(source_bps, "source_bps")
    if rate < 0.0:
        raise ValueError("source_bps must not be negative, got %r" % (source_bps,))
    return span * rate


def assess_isochronous_service(
    delivery_times_s, nominal_period_s, jitter_tolerance_s, source_bps=0.0, epoch_s=None
):
    """Grade one observed run of an isochronous service against its cadence."""
    times = validate_delivery_times(delivery_times_s)
    period = validate_period(nominal_period_s)
    tolerance = validate_tolerance(jitter_tolerance_s)
    rate = _validate_number(source_bps, "source_bps")
    if rate < 0.0:
        raise ValueError("source_bps must not be negative, got %r" % (source_bps,))
    devs = deviations(times, period, epoch_s)
    worst = worst_deviation(devs)
    spread = peak_to_peak_jitter(devs)
    slack = tolerance + REL_TOL * max(tolerance, worst, 1.0)
    within = worst <= slack
    measured = measured_period(times)
    drift = measured - period
    sustainable = sustainable_rate_error(tolerance, len(times))
    drifting = (
        sustainable is not None
        and abs(drift) > sustainable + REL_TOL * max(sustainable, abs(drift), 1.0)
    )
    late_slots = [index for index, value in enumerate(devs) if value > slack]
    early_slots = [index for index, value in enumerate(devs) if value < -slack]
    if within:
        verdict = ISOCHRONOUS
    elif drifting:
        verdict = RATE_DRIFT
    else:
        verdict = JITTER_EXCEEDED
    findings = []
    if verdict == RATE_DRIFT:
        findings.append(
            "stream runs at %.9g s per delivery against a nominal %.9g s; the "
            "error accumulates and no buffer of fixed depth holds it"
            % (measured, period)
        )
        findings.append(
            "a run of %d deliveries absorbs at most %.9g s of rate error at this "
            "tolerance" % (len(times), sustainable)
        )
    elif verdict == JITTER_EXCEEDED:
        findings.append(
            "worst deviation %.9g s exceeds the %.9g s tolerance while the mean "
            "rate is within budget" % (worst, tolerance)
        )
        findings.append(
            "tolerance of at least %.9g s, or a playout buffer of %.9g s, makes "
            "this run conform" % (worst, spread)
        )
    return {
        "delivery_count": len(times),
        "nominal_period_s": period,
        "measured_period_s": measured,
        "jitter_tolerance_s": tolerance,
        "deviations_s": devs,
        "worst_deviation_s": worst,
        "peak_to_peak_jitter_s": spread,
        "rate_error_s": drift,
        "sustainable_rate_error_s": sustainable,
        "within_tolerance": within,
        "late_slots": late_slots,
        "early_slots": early_slots,
        "minimum_tolerance_s": worst,
        "required_playout_buffer_s": spread,
        "required_playout_buffer_bits": required_playout_buffer_bits(spread, rate),
        "verdict": verdict,
        "findings": findings,
    }
