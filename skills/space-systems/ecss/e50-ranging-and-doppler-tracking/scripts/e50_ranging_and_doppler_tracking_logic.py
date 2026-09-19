"""Radiometric ranging and Doppler tracking on a space link.

Anchor: ECSS-E-ST-50C clause 5.6.14.7 -- ranging and Doppler tracking.
Paraphrased into an implementable procedure; no standard text is reproduced.

The single normative item is that the communication system supports radiometric
ranging and Doppler tracking of the spacecraft. Supporting it is not the same as
providing a measurement: a two-way range observation is only a range once its
ambiguity is resolved, and a two-way Doppler observation is only a range rate
once the carrier is inside the receiver's tracking bandwidth.

Both halves reduce to closed-form geometry:

  range       -- half the round-trip light time in metres, modulo the interval
                 the ranging code can distinguish, which repeats every half a
                 code period in range;
  ambiguity   -- resolved from an a-priori range, and resolvable only while the
                 a-priori uncertainty is smaller than half that interval;
  range rate  -- recovered from the two-way Doppler shift through the
                 transponder turnaround ratio, and trackable only while the
                 shift fits inside the receiver's bandwidth.

Reading the same relations backwards sizes the design: the tracking bandwidth a
stated worst-case range rate demands, and the range resolution a chip rate buys.
"""

import math

__all__ = [
    "SPEED_OF_LIGHT_M_PER_S",
    "TRACKABLE",
    "RANGE_AMBIGUOUS",
    "DOPPLER_OUT_OF_BAND",
    "REL_TOL",
    "validate_time",
    "validate_frequency",
    "validate_distance",
    "validate_turnaround_ratio",
    "range_from_round_trip",
    "round_trip_from_range",
    "unambiguous_range_m",
    "range_resolution_m",
    "ambiguity_number",
    "resolve_range",
    "ambiguity_resolvable",
    "two_way_doppler_hz",
    "range_rate_from_doppler",
    "within_tracking_bandwidth",
    "required_tracking_bandwidth_hz",
    "assess_tracking",
]

SPEED_OF_LIGHT_M_PER_S = 299792458.0

TRACKABLE = "trackable"
RANGE_AMBIGUOUS = "range-ambiguous"
DOPPLER_OUT_OF_BAND = "doppler-out-of-band"

# Relative tolerance for every bound comparison, so a geometry sized to sit
# exactly on a limit is accepted on every platform rather than on some of them.
REL_TOL = 1e-9


def _validate_number(value, name):
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise ValueError("%s must be a number" % name)
    number = float(value)
    if math.isnan(number) or math.isinf(number):
        raise ValueError("%s must be finite" % name)
    return number


def validate_time(value, name="time_s"):
    """Return a strictly positive interval in seconds."""
    interval = _validate_number(value, name)
    if interval <= 0.0:
        raise ValueError("%s must be greater than zero, got %r" % (name, value))
    return interval


def validate_frequency(value, name="frequency_hz"):
    """Return a strictly positive frequency in hertz."""
    frequency = _validate_number(value, name)
    if frequency <= 0.0:
        raise ValueError("%s must be greater than zero, got %r" % (name, value))
    return frequency


def validate_distance(value, name="distance_m"):
    """Return a non-negative distance in metres."""
    distance = _validate_number(value, name)
    if distance < 0.0:
        raise ValueError("%s must not be negative, got %r" % (name, value))
    return distance


def validate_turnaround_ratio(value, name="turnaround_ratio"):
    """Return a strictly positive transponder turnaround ratio."""
    ratio = _validate_number(value, name)
    if ratio <= 0.0:
        raise ValueError("%s must be greater than zero, got %r" % (name, value))
    return ratio


def range_from_round_trip(round_trip_s):
    """Return the one-way range implied by a round-trip light time."""
    return SPEED_OF_LIGHT_M_PER_S * validate_time(round_trip_s, "round_trip_s") / 2.0


def round_trip_from_range(range_m):
    """Return the round-trip light time a one-way range implies."""
    return 2.0 * validate_distance(range_m, "range_m") / SPEED_OF_LIGHT_M_PER_S


def unambiguous_range_m(code_period_s):
    """Return the range interval a ranging code of this period can distinguish.

    The code repeats, so the measurement repeats with it: half a code period in
    round-trip time is one full interval in one-way range.
    """
    return SPEED_OF_LIGHT_M_PER_S * validate_time(code_period_s, "code_period_s") / 2.0


def range_resolution_m(chip_rate_hz):
    """Return the finest range step a ranging code of this chip rate resolves."""
    return SPEED_OF_LIGHT_M_PER_S / (2.0 * validate_frequency(chip_rate_hz, "chip_rate_hz"))


def ambiguity_number(measured_m, apriori_m, ambiguity_m):
    """Return how many whole intervals separate the measurement from the a-priori."""
    measured = validate_distance(measured_m, "measured_m")
    apriori = validate_distance(apriori_m, "apriori_m")
    interval = validate_time(ambiguity_m, "ambiguity_m")
    # floor(x + 0.5) rather than round(): banker's rounding would send a
    # measurement exactly half an interval away to an even count on some inputs
    # and an odd one on others, which is not a property a range should have.
    return int(math.floor((apriori - measured) / interval + 0.5))


def resolve_range(measured_m, apriori_m, ambiguity_m):
    """Return the measured range lifted onto the interval the a-priori sits in."""
    measured = validate_distance(measured_m, "measured_m")
    interval = validate_time(ambiguity_m, "ambiguity_m")
    return measured + ambiguity_number(measured, apriori_m, interval) * interval


def ambiguity_resolvable(apriori_uncertainty_m, ambiguity_m):
    """Return whether an a-priori this uncertain can pick the right interval.

    It can while the uncertainty stays inside half an interval; past that the
    a-priori is as likely to name a neighbouring interval as the right one.
    """
    uncertainty = validate_distance(apriori_uncertainty_m, "apriori_uncertainty_m")
    interval = validate_time(ambiguity_m, "ambiguity_m")
    half = interval / 2.0
    return uncertainty <= half + REL_TOL * max(half, uncertainty, 1.0)


def two_way_doppler_hz(range_rate_mps, uplink_hz, turnaround_ratio):
    """Return the two-way Doppler shift a range rate produces on the downlink.

    Negative range rate is closing, which raises the received frequency, so the
    shift comes out positive.
    """
    rate = _validate_number(range_rate_mps, "range_rate_mps")
    uplink = validate_frequency(uplink_hz, "uplink_hz")
    ratio = validate_turnaround_ratio(turnaround_ratio)
    return -2.0 * rate * ratio * uplink / SPEED_OF_LIGHT_M_PER_S


def range_rate_from_doppler(doppler_hz, uplink_hz, turnaround_ratio):
    """Return the range rate a measured two-way Doppler shift implies."""
    shift = _validate_number(doppler_hz, "doppler_hz")
    uplink = validate_frequency(uplink_hz, "uplink_hz")
    ratio = validate_turnaround_ratio(turnaround_ratio)
    return -shift * SPEED_OF_LIGHT_M_PER_S / (2.0 * ratio * uplink)


def within_tracking_bandwidth(doppler_hz, tracking_bandwidth_hz):
    """Return whether a Doppler shift fits inside a receiver's tracking band."""
    shift = abs(_validate_number(doppler_hz, "doppler_hz"))
    bandwidth = validate_frequency(tracking_bandwidth_hz, "tracking_bandwidth_hz")
    half = bandwidth / 2.0
    return shift <= half + REL_TOL * max(half, shift, 1.0)


def required_tracking_bandwidth_hz(max_range_rate_mps, uplink_hz, turnaround_ratio):
    """Return the tracking bandwidth a stated worst-case range rate demands."""
    return 2.0 * abs(two_way_doppler_hz(max_range_rate_mps, uplink_hz, turnaround_ratio))


def assess_tracking(
    round_trip_s,
    code_period_s,
    range_rate_mps,
    uplink_hz,
    turnaround_ratio,
    tracking_bandwidth_hz,
    chip_rate_hz,
    apriori_range_m=None,
    apriori_uncertainty_m=0.0,
):
    """Grade one radiometric tracking geometry against the link that measures it."""
    round_trip = validate_time(round_trip_s, "round_trip_s")
    interval = unambiguous_range_m(code_period_s)
    observed = range_from_round_trip(round_trip)
    folded = math.fmod(observed, interval)
    if folded < 0.0:
        folded = folded + interval
    resolution = range_resolution_m(chip_rate_hz)
    shift = two_way_doppler_hz(range_rate_mps, uplink_hz, turnaround_ratio)
    in_band = within_tracking_bandwidth(shift, tracking_bandwidth_hz)
    needed_bandwidth = required_tracking_bandwidth_hz(
        range_rate_mps, uplink_hz, turnaround_ratio
    )
    recovered_rate = range_rate_from_doppler(shift, uplink_hz, turnaround_ratio)
    beyond = observed > interval + REL_TOL * max(observed, interval, 1.0)
    resolvable = False
    resolved = None
    if apriori_range_m is not None:
        resolvable = ambiguity_resolvable(apriori_uncertainty_m, interval)
        if resolvable:
            resolved = resolve_range(folded, apriori_range_m, interval)
    elif not beyond:
        resolved = folded
    findings = []
    if not in_band:
        findings.append(
            "two-way Doppler of %.9g Hz does not fit a %.9g Hz tracking band; "
            "the carrier is lost before any range rate is measured"
            % (shift, validate_frequency(tracking_bandwidth_hz, "tracking_bandwidth_hz"))
        )
        findings.append(
            "a tracking bandwidth of at least %.9g Hz covers this range rate"
            % (needed_bandwidth,)
        )
    if beyond and resolved is None:
        findings.append(
            "range of %.9g m is beyond the %.9g m the code distinguishes, and no "
            "a-priori able to pick the interval is available" % (observed, interval)
        )
        findings.append(
            "an a-priori range known to better than %.9g m, or a code period of "
            "at least %.9g s, resolves it"
            % (interval / 2.0, 2.0 * observed / SPEED_OF_LIGHT_M_PER_S)
        )
    if not in_band:
        verdict = DOPPLER_OUT_OF_BAND
    elif beyond and resolved is None:
        verdict = RANGE_AMBIGUOUS
    else:
        verdict = TRACKABLE
    return {
        "round_trip_s": round_trip,
        "observed_range_m": observed,
        "unambiguous_range_m": interval,
        "folded_range_m": folded,
        "beyond_unambiguous_interval": beyond,
        "ambiguity_resolvable": resolvable,
        "resolved_range_m": resolved,
        "range_resolution_m": resolution,
        "two_way_doppler_hz": shift,
        "range_rate_mps": recovered_rate,
        "within_tracking_bandwidth": in_band,
        "required_tracking_bandwidth_hz": needed_bandwidth,
        "verdict": verdict,
        "findings": findings,
    }
