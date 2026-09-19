"""Power flux density limits for a space link downlink.

Anchor: ECSS-E-ST-50C clause 5.6.12.4 -- requirements on the power flux density
a space link produces at the surface of the Earth. Paraphrased into an
implementable procedure; no standard text is reproduced.

Two normative obligations are implemented:
  (a) the flux density the downlink produces at the surface stays under the
      limit that applies at the angle of arrival, and that limit is a schedule
      over arrival angle rather than one number -- a downlink compliant at the
      horizon can be well over the limit at high elevation;
  (b) the value compared against the limit is referred to the reference
      bandwidth the limit is specified in, so a measurement taken in a
      different bandwidth is converted before it is graded rather than after
      someone notices.

Decibel values are carried through so the arithmetic is add and subtract
wherever it can be. The one logarithm the physics needs -- spreading power over
a bandwidth or a sphere -- is confined to two helpers, and every verdict is
decided with a decibel tolerance so a value landing exactly on a limit comes
out the same way on every platform.
"""

import math

__all__ = [
    "WITHIN_LIMIT",
    "MARGIN_SHORT",
    "LIMIT_EXCEEDED",
    "TOL_DB",
    "DEFAULT_REQUIRED_MARGIN_DB",
    "DEFAULT_LIMIT_SCHEDULE",
    "validate_elevation",
    "validate_bandwidth",
    "validate_decibels",
    "normalize_limit_schedule",
    "pfd_limit_dbw_per_m2",
    "spreading_loss_db",
    "pfd_at_surface_dbw_per_m2",
    "bandwidth_referral_db",
    "refer_to_reference_bandwidth",
    "assess_pfd",
    "assess_pfd_profile",
]

WITHIN_LIMIT = "within-limit"
MARGIN_SHORT = "margin-short"
LIMIT_EXCEEDED = "limit-exceeded"

# Decibel tolerance for every limit comparison. A flux density that should sit
# exactly on its limit must not be failed by the last bit of a logarithm.
TOL_DB = 1e-9

# Coordination margin the assessment asks for before calling a downlink
# comfortable. Meeting a flux limit with nothing to spare is meeting it once.
DEFAULT_REQUIRED_MARGIN_DB = 1.0

# A limit schedule shaped the way flux limits are usually written: flat at low
# arrival angles, rising linearly through a transition, flat again above it.
# Breakpoints are (arrival angle in degrees, limit in dB(W/m2) per reference
# bandwidth). Callers override it with the schedule their band actually carries.
DEFAULT_LIMIT_SCHEDULE = (
    (0.0, -150.0),
    (5.0, -150.0),
    (25.0, -140.0),
    (90.0, -140.0),
)


def _validate_number(value, name):
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise ValueError("%s must be a number" % name)
    number = float(value)
    if math.isnan(number) or math.isinf(number):
        raise ValueError("%s must be finite" % name)
    return number


def validate_decibels(value, name="level_db"):
    """Return a finite decibel value."""
    return _validate_number(value, name)


def validate_elevation(value, name="arrival_angle_deg"):
    """Return an angle of arrival above the horizontal plane, in degrees."""
    angle = _validate_number(value, name)
    if angle < 0.0 or angle > 90.0:
        raise ValueError(
            "%s must lie between 0 and 90 degrees, got %r" % (name, value)
        )
    return angle


def validate_bandwidth(value, name="bandwidth_hz"):
    """Return a strictly positive bandwidth in hertz."""
    bandwidth = _validate_number(value, name)
    if bandwidth <= 0.0:
        raise ValueError("%s must be greater than zero, got %r" % (name, value))
    return bandwidth


def validate_range(value, name="slant_range_m"):
    """Return a strictly positive slant range in metres."""
    distance = _validate_number(value, name)
    if distance <= 0.0:
        raise ValueError("%s must be greater than zero, got %r" % (name, value))
    return distance


def normalize_limit_schedule(schedule=DEFAULT_LIMIT_SCHEDULE):
    """Return the limit schedule as sorted, distinct arrival-angle breakpoints."""
    if isinstance(schedule, dict) or not isinstance(schedule, (list, tuple)):
        raise ValueError("schedule must be a list or tuple of breakpoints")
    if len(schedule) < 2:
        raise ValueError("schedule needs at least two breakpoints to interpolate")
    points = []
    for entry in schedule:
        if isinstance(entry, dict):
            if "arrival_angle_deg" not in entry or "limit_dbw_per_m2" not in entry:
                raise ValueError(
                    "schedule breakpoint needs arrival_angle_deg and limit_dbw_per_m2"
                )
            angle = entry["arrival_angle_deg"]
            limit = entry["limit_dbw_per_m2"]
        elif isinstance(entry, (list, tuple)) and len(entry) == 2:
            angle, limit = entry
        else:
            raise ValueError("schedule breakpoint must be a pair or a mapping")
        points.append(
            (validate_elevation(angle), validate_decibels(limit, "limit_dbw_per_m2"))
        )
    points.sort(key=lambda item: item[0])
    for index in range(1, len(points)):
        if points[index][0] <= points[index - 1][0]:
            raise ValueError("schedule breakpoints must have distinct arrival angles")
    return points


def pfd_limit_dbw_per_m2(arrival_angle_deg, schedule=DEFAULT_LIMIT_SCHEDULE):
    """Return the flux limit that applies at this angle of arrival.

    Between breakpoints the limit is interpolated linearly in decibels against
    the angle; outside the declared range it is held at the end value.
    """
    points = normalize_limit_schedule(schedule)
    angle = validate_elevation(arrival_angle_deg)
    if angle <= points[0][0]:
        return points[0][1]
    if angle >= points[-1][0]:
        return points[-1][1]
    for index in range(1, len(points)):
        low_angle, low_limit = points[index - 1]
        high_angle, high_limit = points[index]
        if angle <= high_angle:
            span = high_angle - low_angle
            fraction = (angle - low_angle) / span
            return low_limit + fraction * (high_limit - low_limit)
    return points[-1][1]


def spreading_loss_db(slant_range_m):
    """Return the decibel spreading of a watt over a sphere at this range."""
    distance = validate_range(slant_range_m)
    return 10.0 * math.log10(4.0 * math.pi * distance * distance)


def pfd_at_surface_dbw_per_m2(eirp_dbw, slant_range_m):
    """Return the flux density a downlink of this EIRP puts on the surface."""
    eirp = validate_decibels(eirp_dbw, "eirp_dbw")
    return eirp - spreading_loss_db(slant_range_m)


def bandwidth_referral_db(measured_bandwidth_hz, reference_bandwidth_hz):
    """Return the correction taking a measurement to the reference bandwidth.

    A measurement taken in a bandwidth no wider than the reference already has
    all of its power inside the reference bandwidth, so no correction applies.
    A measurement taken in a wider bandwidth spread that power out, and only
    the reference-bandwidth share of it counts against the limit.
    """
    measured = validate_bandwidth(measured_bandwidth_hz, "measured_bandwidth_hz")
    reference = validate_bandwidth(reference_bandwidth_hz, "reference_bandwidth_hz")
    if measured <= reference * (1.0 + TOL_DB):
        return 0.0
    return 10.0 * math.log10(reference / measured)


def refer_to_reference_bandwidth(
    pfd_dbw_per_m2, measured_bandwidth_hz, reference_bandwidth_hz
):
    """Return the flux density restated in the limit's reference bandwidth."""
    pfd = validate_decibels(pfd_dbw_per_m2, "pfd_dbw_per_m2")
    return pfd + bandwidth_referral_db(measured_bandwidth_hz, reference_bandwidth_hz)


def assess_pfd(
    observation,
    reference_bandwidth_hz,
    schedule=DEFAULT_LIMIT_SCHEDULE,
    required_margin_db=DEFAULT_REQUIRED_MARGIN_DB,
):
    """Grade one flux density observation against the limit at its arrival angle.

    The observation carries the flux density, the bandwidth it was measured in
    and the angle of arrival. The bandwidth referral happens here rather than
    in the caller, because a value graded in the wrong bandwidth is the defect
    this clause exists to prevent.
    """
    if not isinstance(observation, dict):
        raise ValueError("observation must be a mapping")
    for key in ("pfd_dbw_per_m2", "measured_bandwidth_hz", "arrival_angle_deg"):
        if key not in observation:
            raise ValueError("observation is missing %s" % key)
    margin_required = validate_decibels(required_margin_db, "required_margin_db")
    if margin_required < 0.0:
        raise ValueError("required_margin_db must not be negative")

    angle = validate_elevation(observation["arrival_angle_deg"])
    referral = bandwidth_referral_db(
        observation["measured_bandwidth_hz"], reference_bandwidth_hz
    )
    referred = (
        validate_decibels(observation["pfd_dbw_per_m2"], "pfd_dbw_per_m2") + referral
    )
    limit = pfd_limit_dbw_per_m2(angle, schedule)
    margin = limit - referred

    if margin < -TOL_DB:
        verdict = LIMIT_EXCEEDED
    elif margin < margin_required - TOL_DB:
        verdict = MARGIN_SHORT
    else:
        verdict = WITHIN_LIMIT

    return {
        "arrival_angle_deg": angle,
        "measured_pfd_dbw_per_m2": float(observation["pfd_dbw_per_m2"]),
        "bandwidth_referral_db": referral,
        "referred_pfd_dbw_per_m2": referred,
        "limit_dbw_per_m2": limit,
        "margin_db": margin,
        "compliant": margin >= -TOL_DB,
        "verdict": verdict,
    }


def assess_pfd_profile(
    observations,
    reference_bandwidth_hz,
    schedule=DEFAULT_LIMIT_SCHEDULE,
    required_margin_db=DEFAULT_REQUIRED_MARGIN_DB,
):
    """Grade a whole arrival-angle profile and report the angle that governs.

    The governing case is the smallest margin across the profile, which is not
    in general the highest flux density: the limit moves with the angle too,
    so the worst angle has to be found rather than assumed.
    """
    if isinstance(observations, dict) or not isinstance(observations, (list, tuple)):
        raise ValueError("observations must be a list or tuple of mappings")
    if not observations:
        raise ValueError("observations must not be empty")

    results = []
    exceeded = []
    thin = []
    governing = None
    for observation in observations:
        result = assess_pfd(
            observation, reference_bandwidth_hz, schedule, required_margin_db
        )
        results.append(result)
        if governing is None or result["margin_db"] < governing["margin_db"]:
            governing = result
        if result["verdict"] == LIMIT_EXCEEDED:
            exceeded.append(result)
        elif result["verdict"] == MARGIN_SHORT:
            thin.append(result)

    if exceeded:
        verdict = LIMIT_EXCEEDED
    elif thin:
        verdict = MARGIN_SHORT
    else:
        verdict = WITHIN_LIMIT

    findings = []
    for result in exceeded:
        findings.append(
            "flux density at %.6g degrees is %.6g dB over the limit"
            % (result["arrival_angle_deg"], -result["margin_db"])
        )
    for result in thin:
        findings.append(
            "flux density at %.6g degrees clears the limit by only %.6g dB"
            % (result["arrival_angle_deg"], result["margin_db"])
        )

    return {
        "results": results,
        "governing": governing,
        "governing_angle_deg": governing["arrival_angle_deg"],
        "worst_margin_db": governing["margin_db"],
        "exceedance_count": len(exceeded),
        "compliant": not exceeded,
        "verdict": verdict,
        "findings": findings,
    }
