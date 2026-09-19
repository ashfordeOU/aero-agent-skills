"""Two-way time synchronization across an inter-spacecraft link.

Anchor: ECSS-E-ST-50C clause 5.7.4.5 -- time synchronization.
Paraphrased into an implementable procedure; no standard text is reproduced.

The single normative item is that the spacecraft sharing an inter-spacecraft
network keep their clocks synchronized to one another. Two things decide
whether they do, and both are computable from a single exchange:

  estimate  -- how well one synchronization exchange pins the offset between
               the two clocks, limited by path asymmetry, by the motion of
               the two spacecraft during the exchange, by timestamp
               resolution and by jitter;
  interval  -- how far the two clocks walk apart at their relative drift rate
               before the next exchange puts them back.

The four-timestamp exchange cancels the reciprocal part of the path, so what
is left is the part that is not reciprocal. Sizing is the same model read
backwards: the longest synchronization interval that still holds the pair
inside the coordination window it was given.
"""

import math

__all__ = [
    "HELD",
    "LOST",
    "SPEED_OF_LIGHT_MPS",
    "REL_TOL",
    "validate_nonnegative",
    "validate_positive",
    "validate_exchange",
    "round_trip_s",
    "turnaround_s",
    "one_way_delay_s",
    "clock_offset_s",
    "motion_asymmetry_s",
    "estimate_error_ns",
    "drift_error_ns",
    "max_sync_interval_s",
    "assess_synchronization",
]

HELD = "synchronization-held"
LOST = "synchronization-lost"

SPEED_OF_LIGHT_MPS = 299792458.0

# Relative tolerance on the coordination-window comparison, so a budget that
# lands exactly on the window reads the same on every build host.
REL_TOL = 1e-9


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


def validate_exchange(t1, t2, t3, t4):
    """Return the four timestamps of one synchronization exchange.

    t1 and t4 are read on the initiator's clock, t2 and t3 on the responder's.
    Time runs forward in each frame independently, so t4 must follow t1 and t3
    must not precede t2; an offset between the two clocks is the quantity being
    measured and is never itself an error.
    """
    a1 = _number(t1, "t1")
    b2 = _number(t2, "t2")
    b3 = _number(t3, "t3")
    a4 = _number(t4, "t4")
    if a4 <= a1:
        raise ValueError("t4 must follow t1 on the initiator clock")
    if b3 < b2:
        raise ValueError("t3 must not precede t2 on the responder clock")
    return a1, b2, b3, a4


def turnaround_s(t1, t2, t3, t4):
    """Return how long the responder held the exchange."""
    _, b2, b3, _ = validate_exchange(t1, t2, t3, t4)
    return b3 - b2


def round_trip_s(t1, t2, t3, t4):
    """Return the two-way propagation time, responder hold time removed."""
    a1, b2, b3, a4 = validate_exchange(t1, t2, t3, t4)
    trip = (a4 - a1) - (b3 - b2)
    if trip < 0.0:
        raise ValueError("responder held the exchange longer than the round trip")
    return trip


def one_way_delay_s(t1, t2, t3, t4):
    """Return the one-way delay the reciprocal model assumes."""
    return round_trip_s(t1, t2, t3, t4) / 2.0


def clock_offset_s(t1, t2, t3, t4):
    """Return the responder clock offset relative to the initiator."""
    a1, b2, b3, a4 = validate_exchange(t1, t2, t3, t4)
    round_trip_s(t1, t2, t3, t4)
    return ((b2 - a1) + (b3 - a4)) / 2.0


def motion_asymmetry_s(range_rate_mps, hold_s):
    """Return the path asymmetry the relative motion opens during the exchange.

    The range the reply travels differs from the range the request travelled by
    the closing or opening motion over the time the responder held the
    exchange; only the magnitude matters to the budget.
    """
    rate = _number(range_rate_mps, "range_rate_mps")
    hold = validate_nonnegative(hold_s, "hold_s")
    return abs(rate) * hold / SPEED_OF_LIGHT_MPS


def estimate_error_ns(
    path_asymmetry_s, range_rate_mps, hold_s, timestamp_resolution_s, jitter_ns
):
    """Return the error one synchronization exchange leaves in the offset."""
    asymmetry = validate_nonnegative(path_asymmetry_s, "path_asymmetry_s")
    resolution = validate_nonnegative(timestamp_resolution_s, "timestamp_resolution_s")
    jitter = validate_nonnegative(jitter_ns, "jitter_ns")
    motion = motion_asymmetry_s(range_rate_mps, hold_s)
    systematic_ns = (asymmetry / 2.0 + motion / 2.0 + resolution / 2.0) * 1e9
    return {
        "path_asymmetry_ns": asymmetry / 2.0 * 1e9,
        "motion_asymmetry_ns": motion / 2.0 * 1e9,
        "resolution_ns": resolution / 2.0 * 1e9,
        "jitter_ns": jitter,
        "systematic_ns": systematic_ns,
        "total_ns": systematic_ns + jitter,
    }


def drift_error_ns(relative_drift_ppm, interval_s):
    """Return how far the pair walks apart between synchronizations."""
    drift = validate_nonnegative(relative_drift_ppm, "relative_drift_ppm")
    interval = validate_positive(interval_s, "interval_s")
    return drift * interval * 1000.0


def max_sync_interval_s(estimate_ns, relative_drift_ppm, required_ns):
    """Return the longest interval that still holds the pair inside the window.

    Zero means the exchange itself already spends the whole window, so
    synchronizing more often cannot recover it. None means the interval is not
    the constraint, because the pair has no declared relative drift.
    """
    estimate = validate_nonnegative(estimate_ns, "estimate_ns")
    drift = validate_nonnegative(relative_drift_ppm, "relative_drift_ppm")
    required = validate_positive(required_ns, "required_ns")
    budget = required - estimate
    if budget <= 0.0:
        return 0.0
    if drift == 0.0:
        return None
    return budget / (drift * 1000.0)


def assess_synchronization(
    t1,
    t2,
    t3,
    t4,
    path_asymmetry_s,
    range_rate_mps,
    timestamp_resolution_s,
    jitter_ns,
    relative_drift_ppm,
    interval_s,
    required_ns,
):
    """Grade one synchronized inter-spacecraft pair against its window."""
    offset = clock_offset_s(t1, t2, t3, t4)
    hold = turnaround_s(t1, t2, t3, t4)
    estimate = estimate_error_ns(
        path_asymmetry_s, range_rate_mps, hold, timestamp_resolution_s, jitter_ns
    )
    drift = drift_error_ns(relative_drift_ppm, interval_s)
    required = validate_positive(required_ns, "required_ns")
    total = estimate["total_ns"] + drift
    within = total <= required + REL_TOL * required
    longest = max_sync_interval_s(estimate["total_ns"], relative_drift_ppm, required)
    findings = []
    if not within:
        if longest == 0.0:
            findings.append(
                "the exchange itself leaves %.6g ns of a %.6g ns window; "
                "synchronizing more often cannot recover it"
                % (estimate["total_ns"], required)
            )
        else:
            findings.append(
                "the pair holds %.6g ns against a %.6g ns window; an interval "
                "of at most %.6g s meets it" % (total, required, longest)
            )
    if estimate["motion_asymmetry_ns"] > estimate["path_asymmetry_ns"]:
        findings.append(
            "relative motion contributes %.6g ns, more than the static path "
            "asymmetry at %.6g ns; shortening the responder hold time is the "
            "cheaper fix"
            % (estimate["motion_asymmetry_ns"], estimate["path_asymmetry_ns"])
        )
    return {
        "offset_s": offset,
        "round_trip_s": round_trip_s(t1, t2, t3, t4),
        "one_way_delay_s": one_way_delay_s(t1, t2, t3, t4),
        "hold_s": hold,
        "estimate": estimate,
        "drift_ns": drift,
        "total_ns": total,
        "required_ns": required,
        "margin_ns": required - total,
        "max_interval_s": longest,
        "within": within,
        "verdict": HELD if within else LOST,
        "findings": findings,
    }
