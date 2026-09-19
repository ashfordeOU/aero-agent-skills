"""Link operation while the spacecraft tumbles.

Anchor: ECSS-E-ST-50C clause 5.6.11.2 -- operation during tumbling.
Paraphrased into an implementable procedure; no standard text is reproduced.

Two normative items, and they fail in different ways:

  1. the link can be established while the body is rotating, which is a
     geometry question: does the antenna beam, carried round by the spin,
     ever sweep across the ground station at all;
  2. each sweep lasts long enough to be useful, which is a timing question:
     the window has to contain the link setup and at least one message, and
     the outage between windows has to stay inside what the operations
     concept can absorb.

The geometry is a cone sweep. The spin carries the antenna boresight round a
cone of half-angle c about the rotation axis; the ground station sits at
aspect angle a from that axis. The separation between boresight and station
over one rotation phase p is

    cos(theta) = cos(a) cos(c) + sin(a) sin(c) cos(p)

and the link is up while theta stays inside the beam half-width. Inverting
that for the phase gives the visibility arc directly, which divided by the
tumble rate is the window and whose complement is the outage.

Degenerate geometries are real and are handled explicitly rather than by a
division that happens not to raise: a station on the spin axis, or a boresight
along it, sees a constant separation and is therefore visible always or never.
"""

import math

__all__ = [
    "OPERABLE",
    "NEVER_VISIBLE",
    "WINDOW_TOO_SHORT",
    "OUTAGE_TOO_LONG",
    "REL_TOL",
    "validate_angle_deg",
    "validate_beamwidth_deg",
    "validate_rate_deg_s",
    "validate_duration",
    "beam_separation_deg",
    "visibility_arc_deg",
    "rotation_period_s",
    "window_duration_s",
    "outage_duration_s",
    "duty_fraction",
    "messages_per_window",
    "required_beamwidth_deg",
    "max_tumble_rate_deg_s",
    "assess_tumbling_link",
]

OPERABLE = "operable"
NEVER_VISIBLE = "never-visible"
WINDOW_TOO_SHORT = "window-too-short"
OUTAGE_TOO_LONG = "outage-too-long"

# Relative tolerance for every bound comparison, so a geometry sized to land
# exactly on a limit is accepted on every platform rather than on some of them.
REL_TOL = 1e-9

# Below this the two sines are treated as a degenerate cone: the separation no
# longer varies with rotation phase and the sweep answer is all or nothing.
_DEGENERATE = 1e-12


def _validate_number(value, name):
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise ValueError("%s must be a number" % name)
    number = float(value)
    if math.isnan(number) or math.isinf(number):
        raise ValueError("%s must be finite" % name)
    return number


def validate_angle_deg(value, name="angle_deg"):
    """Return a cone or aspect angle in degrees, zero to one hundred eighty."""
    angle = _validate_number(value, name)
    if angle < 0.0 or angle > 180.0:
        raise ValueError("%s must lie between 0 and 180 degrees, got %r" % (name, value))
    return angle


def validate_beamwidth_deg(value, name="beamwidth_deg"):
    """Return a beam width in degrees, above zero and at most a full sphere."""
    width = _validate_number(value, name)
    if width <= 0.0 or width > 360.0:
        raise ValueError("%s must lie above 0 and at most 360 degrees, got %r" % (name, value))
    return width


def validate_rate_deg_s(value, name="tumble_rate_deg_s"):
    """Return a strictly positive tumble rate in degrees per second."""
    rate = _validate_number(value, name)
    if rate <= 0.0:
        raise ValueError("%s must be greater than zero, got %r" % (name, value))
    return rate


def validate_duration(value, name="seconds"):
    """Return a non-negative duration in seconds."""
    seconds = _validate_number(value, name)
    if seconds < 0.0:
        raise ValueError("%s must not be negative, got %r" % (name, value))
    return seconds


def beam_separation_deg(aspect_deg, cone_deg, phase_deg):
    """Return the boresight-to-station separation at one rotation phase."""
    aspect = math.radians(validate_angle_deg(aspect_deg, "aspect_deg"))
    cone = math.radians(validate_angle_deg(cone_deg, "cone_deg"))
    phase = math.radians(_validate_number(phase_deg, "phase_deg"))
    cosine = math.cos(aspect) * math.cos(cone) + math.sin(aspect) * math.sin(cone) * math.cos(phase)
    if cosine > 1.0:
        cosine = 1.0
    elif cosine < -1.0:
        cosine = -1.0
    return math.degrees(math.acos(cosine))


def visibility_arc_deg(aspect_deg, cone_deg, beamwidth_deg):
    """Return the rotation arc over which the station sits inside the beam.

    Zero means the beam never reaches the station and no amount of waiting
    helps; three hundred sixty means the station is inside the beam for the
    whole rotation and the tumble does not interrupt the link at all.
    """
    aspect = math.radians(validate_angle_deg(aspect_deg, "aspect_deg"))
    cone = math.radians(validate_angle_deg(cone_deg, "cone_deg"))
    half = math.radians(validate_beamwidth_deg(beamwidth_deg) / 2.0)
    swing = math.sin(aspect) * math.sin(cone)
    fixed = math.cos(aspect) * math.cos(cone)
    if swing <= _DEGENERATE:
        # Station on the spin axis, or boresight along it: the separation does
        # not move with phase, so the answer is all of the rotation or none.
        separation = math.acos(max(-1.0, min(1.0, fixed)))
        return 360.0 if separation <= half else 0.0
    ratio = (math.cos(half) - fixed) / swing
    if ratio >= 1.0:
        return 0.0
    if ratio <= -1.0:
        return 360.0
    return 2.0 * math.degrees(math.acos(ratio))


def rotation_period_s(tumble_rate_deg_s):
    """Return the time one full rotation takes."""
    return 360.0 / validate_rate_deg_s(tumble_rate_deg_s)


def window_duration_s(arc_deg, tumble_rate_deg_s):
    """Return how long one visibility arc lasts at this tumble rate."""
    arc = _validate_number(arc_deg, "arc_deg")
    if arc < 0.0 or arc > 360.0:
        raise ValueError("arc_deg must lie between 0 and 360, got %r" % arc_deg)
    return arc / validate_rate_deg_s(tumble_rate_deg_s)


def outage_duration_s(arc_deg, tumble_rate_deg_s):
    """Return the gap between two visibility windows.

    None means there is no next window: an arc of zero never comes round, and
    reporting that as a very long gap would imply the link returns.
    """
    arc = _validate_number(arc_deg, "arc_deg")
    if arc < 0.0 or arc > 360.0:
        raise ValueError("arc_deg must lie between 0 and 360, got %r" % arc_deg)
    rate = validate_rate_deg_s(tumble_rate_deg_s)
    if arc <= 0.0:
        return None
    return (360.0 - arc) / rate


def duty_fraction(arc_deg):
    """Return the share of each rotation the link is available."""
    arc = _validate_number(arc_deg, "arc_deg")
    if arc < 0.0 or arc > 360.0:
        raise ValueError("arc_deg must lie between 0 and 360, got %r" % arc_deg)
    return arc / 360.0


def messages_per_window(window_s, setup_s, message_s):
    """Return how many whole messages a window carries after setup is paid."""
    window = validate_duration(window_s, "window_s")
    setup = validate_duration(setup_s, "setup_s")
    message = validate_duration(message_s, "message_s")
    if message <= 0.0:
        raise ValueError("message_s must be greater than zero, got %r" % message_s)
    usable = window - setup
    if usable < 0.0:
        return 0
    return int(math.floor(usable / message + REL_TOL))


def required_beamwidth_deg(aspect_deg, cone_deg, arc_deg):
    """Return the beam width that yields this visibility arc for this geometry.

    None means the geometry cannot yield it with any beam on that cone: a
    degenerate cone gives all or nothing and a partial arc is not on offer.
    """
    aspect = math.radians(validate_angle_deg(aspect_deg, "aspect_deg"))
    cone = math.radians(validate_angle_deg(cone_deg, "cone_deg"))
    arc = _validate_number(arc_deg, "arc_deg")
    if arc <= 0.0 or arc > 360.0:
        raise ValueError("arc_deg must lie above 0 and at most 360, got %r" % arc_deg)
    swing = math.sin(aspect) * math.sin(cone)
    fixed = math.cos(aspect) * math.cos(cone)
    if swing <= _DEGENERATE:
        return None
    cosine = fixed + swing * math.cos(math.radians(arc / 2.0))
    cosine = max(-1.0, min(1.0, cosine))
    return 2.0 * math.degrees(math.acos(cosine))


def max_tumble_rate_deg_s(arc_deg, required_window_s):
    """Return the tumble rate at which this arc still lasts long enough."""
    arc = _validate_number(arc_deg, "arc_deg")
    if arc <= 0.0 or arc > 360.0:
        raise ValueError("arc_deg must lie above 0 and at most 360, got %r" % arc_deg)
    needed = _validate_number(required_window_s, "required_window_s")
    if needed <= 0.0:
        raise ValueError("required_window_s must be greater than zero, got %r" % required_window_s)
    return arc / needed


def assess_tumbling_link(
    aspect_deg,
    cone_deg,
    beamwidth_deg,
    tumble_rate_deg_s,
    setup_s,
    message_s,
    max_outage_s,
):
    """Assess one tumbling geometry against both obligations of the clause."""
    aspect = validate_angle_deg(aspect_deg, "aspect_deg")
    cone = validate_angle_deg(cone_deg, "cone_deg")
    width = validate_beamwidth_deg(beamwidth_deg)
    rate = validate_rate_deg_s(tumble_rate_deg_s)
    setup = validate_duration(setup_s, "setup_s")
    message = validate_duration(message_s, "message_s")
    if message <= 0.0:
        raise ValueError("message_s must be greater than zero, got %r" % message_s)
    outage_budget = validate_duration(max_outage_s, "max_outage_s")
    arc = visibility_arc_deg(aspect, cone, width)
    period = 360.0 / rate
    window = arc / rate
    outage = None if arc <= 0.0 else (360.0 - arc) / rate
    needed_window = setup + message
    window_tolerance = REL_TOL * max(needed_window, 1.0)
    reachable = arc > 0.0
    window_ok = reachable and window >= needed_window - window_tolerance
    outage_tolerance = REL_TOL * max(outage_budget, 1.0)
    outage_ok = reachable and (outage is None or outage <= outage_budget + outage_tolerance)
    if not reachable:
        verdict = NEVER_VISIBLE
    elif not window_ok:
        verdict = WINDOW_TOO_SHORT
    elif not outage_ok:
        verdict = OUTAGE_TOO_LONG
    else:
        verdict = OPERABLE
    findings = []
    if not reachable:
        findings.append(
            "a %.6g degree beam on a %.6g degree cone never reaches a station at %.6g "
            "degrees aspect; the tumble rate is not the problem" % (width, cone, aspect)
        )
    else:
        if not window_ok:
            findings.append(
                "window of %.6g s does not hold %.6g s of setup plus message; a tumble "
                "rate at or below %.6g deg/s would, and so would a wider beam"
                % (window, needed_window, max_tumble_rate_deg_s(arc, needed_window))
            )
        if outage is not None and outage > outage_budget + outage_tolerance:
            findings.append(
                "outage of %.6g s between windows exceeds the %.6g s the operations "
                "concept allows" % (outage, outage_budget)
            )
    return {
        "aspect_deg": aspect,
        "cone_deg": cone,
        "beamwidth_deg": width,
        "tumble_rate_deg_s": rate,
        "rotation_period_s": period,
        "visibility_arc_deg": arc,
        "window_s": window,
        "outage_s": outage,
        "duty_fraction": arc / 360.0,
        "required_window_s": needed_window,
        "window_margin_s": window - needed_window,
        "messages_per_window": messages_per_window(window, setup, message),
        "max_tumble_rate_deg_s": (
            max_tumble_rate_deg_s(arc, needed_window) if arc > 0.0 else None
        ),
        "required_beamwidth_deg": (
            required_beamwidth_deg(aspect, cone, min(360.0, rate * needed_window))
            if rate * needed_window <= 360.0
            else None
        ),
        "reachable": reachable,
        "window_ok": window_ok,
        "outage_ok": outage_ok,
        "verdict": verdict,
        "findings": findings,
    }
