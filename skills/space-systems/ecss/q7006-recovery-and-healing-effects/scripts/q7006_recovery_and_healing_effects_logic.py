"""Particle and UV radiation testing: recovery and healing after exposure.

Anchor: ECSS-Q-ST-70-06C, the evaluation clause of particle and UV
radiation testing for space materials (paraphrased into an implementable
procedure; no standard text is reproduced).

Procedure implemented here:

1. Part of what an irradiation does comes back. Colour centres in
   glasses and coatings bleach thermally and optically, so a property
   read out days after the beam stopped is not the property the beam
   left behind.
2. Recovery is read off a post-exposure series measured against elapsed
   time. Each point becomes a degradation relative to the pristine
   value, and the recovered fraction is how much of the as-irradiated
   degradation has gone.
3. What is left when the series stops moving is the permanent, unhealed
   degradation. It is the floor the material will never come back
   above, and it is a different quantity from the as-irradiated value.
4. Between those two, the approach is exponential. A time constant
   derived from one post-exposure point, the as-irradiated value and the
   permanent floor turns the series into a number a designer can use.
5. Recovery may only be credited when the mission actually offers the
   quiet time for it to happen. A continuously irradiated surface never
   gets that time, so its design value is the as-irradiated degradation;
   an intermittently irradiated one gets credit only when its quiet
   interval is long against the recovery half-time.
6. A series that moves away from the pristine value, or past it, is a
   measurement artefact, not healing, and is reported as a finding.

Stdlib only, offline, deterministic.
"""

import math

DIRECTIONS = ("increase-is-degradation", "decrease-is-degradation")

EXPOSURE_REGIMES = ("continuous", "intermittent")

# Recovery may be credited only when the quiet interval runs at least
# this many recovery half-times.
MIN_QUIET_HALF_TIMES = 3.0

# A recovered fraction is a ratio of decimal-literal differences, so a
# value sitting exactly on a bound can land a few units in the last place
# past it. This tolerance absorbs that representation error only.
RECOVERY_TOLERANCE = 1.0e-12


def _numeric(label, value, minimum=None):
    """Return value as a float, raising on anything that is not a number."""
    if not isinstance(value, (int, float)) or isinstance(value, bool):
        raise ValueError("%s must be numeric, got %r" % (label, value))
    val = float(value)
    if minimum is not None and val < minimum - RECOVERY_TOLERANCE:
        raise ValueError("%s must be >= %r, got %r" % (label, minimum, value))
    return val


def _text(label, value):
    if not isinstance(value, str) or not value.strip():
        raise ValueError("%s must be a non-empty string" % label)
    return value.strip()


def _direction(value):
    direction = _text("direction", value)
    if direction not in DIRECTIONS:
        raise ValueError("unknown degradation direction %r" % (direction,))
    return direction


def degradation_at(pristine, value, direction):
    """Degradation of one post-exposure reading against the pristine value."""
    start = _numeric("pristine", pristine)
    now = _numeric("value", value)
    if _direction(direction) == "increase-is-degradation":
        return now - start
    return start - now


def recovered_fraction(as_irradiated_degradation, current_degradation):
    """Fraction of the as-irradiated degradation that has healed away."""
    d0 = _numeric("as_irradiated_degradation", as_irradiated_degradation)
    now = _numeric("current_degradation", current_degradation)
    if abs(d0) <= RECOVERY_TOLERANCE:
        raise ValueError("nothing was induced, so nothing can recover")
    return (d0 - now) / d0


def normalize_recovery_series(series, pristine, direction):
    """Turn a post-exposure series into ordered (hours, degradation) pairs."""
    if not isinstance(series, (list, tuple)) or not series:
        raise ValueError("recovery series must be a non-empty sequence")
    direction = _direction(direction)
    points = []
    seen = []
    for entry in series:
        if not isinstance(entry, dict):
            raise ValueError("each recovery point must be a mapping")
        hours = _numeric("elapsed_h", entry.get("elapsed_h"), 0.0)
        for other in seen:
            if abs(other - hours) <= RECOVERY_TOLERANCE:
                raise ValueError("two recovery points share elapsed time %r" % (hours,))
        seen.append(hours)
        points.append((hours, degradation_at(pristine, entry.get("value"), direction)))
    points.sort(key=lambda p: p[0])
    return points


def series_is_monotonic(points):
    """True when every step of a recovery series heals or holds."""
    if not isinstance(points, (list, tuple)) or len(points) < 2:
        raise ValueError("a monotonic check needs at least two points")
    for (_, earlier), (_, later) in zip(points, points[1:]):
        if later > earlier + RECOVERY_TOLERANCE:
            return False
    return True


def permanent_degradation(points):
    """The unhealed degradation the series settles on."""
    if not isinstance(points, (list, tuple)) or not points:
        raise ValueError("a permanent floor needs at least one point")
    return points[-1][1]


def recovery_time_constant(elapsed_h, degradation, as_irradiated, permanent):
    """Exponential time constant of the approach to the permanent floor."""
    hours = _numeric("elapsed_h", elapsed_h, 0.0)
    if hours <= 0.0:
        raise ValueError("elapsed_h must be greater than zero")
    now = _numeric("degradation", degradation)
    d0 = _numeric("as_irradiated", as_irradiated)
    floor = _numeric("permanent", permanent)
    span = d0 - floor
    if abs(span) <= RECOVERY_TOLERANCE:
        raise ValueError("nothing recovers, so there is no time constant")
    remaining = (now - floor) / span
    if remaining <= 0.0 or remaining >= 1.0:
        raise ValueError(
            "remaining fraction %r is outside the recovering range" % (remaining,)
        )
    return -hours / math.log(remaining)


def recovery_half_time(time_constant_h):
    """Time for half of the recoverable part to heal away."""
    tau = _numeric("time_constant_h", time_constant_h, 0.0)
    if tau <= 0.0:
        raise ValueError("time_constant_h must be greater than zero")
    return tau * math.log(2.0)


def recovery_credit_reasons(record):
    """Reasons the mission cannot be credited with the observed healing."""
    if not isinstance(record, dict):
        raise ValueError("record must be a mapping")
    regime = _text("exposure_regime", record.get("exposure_regime"))
    if regime not in EXPOSURE_REGIMES:
        raise ValueError("unknown exposure regime %r" % (regime,))
    reasons = []
    if regime == "continuous":
        reasons.append("continuous-exposure-leaves-no-quiet-time-to-heal-in")
        return reasons
    quiet = _numeric("quiet_interval_h", record.get("quiet_interval_h"), 0.0)
    half_time = _numeric("recovery_half_time_h", record.get("recovery_half_time_h"), 0.0)
    if half_time <= 0.0:
        raise ValueError("recovery_half_time_h must be greater than zero")
    if quiet + RECOVERY_TOLERANCE < MIN_QUIET_HALF_TIMES * half_time:
        reasons.append("quiet-interval-too-short-against-the-recovery-half-time")
    return reasons


def recovery_credit_admissible(record):
    """True when the design may use the recovered value instead of the raw one."""
    return not recovery_credit_reasons(record)


def assess_recovery(record):
    """Assess the recovery and healing behaviour of one irradiated property."""
    if not isinstance(record, dict):
        raise ValueError("record must be a mapping")

    name = _text("property", record.get("property"))
    direction = _direction(record.get("direction"))
    pristine = _numeric("pristine_value", record.get("pristine_value"))
    as_irradiated = degradation_at(
        pristine, record.get("as_irradiated_value"), direction
    )
    points = normalize_recovery_series(
        record.get("recovery_series"), pristine, direction
    )

    findings = []
    if all(hours <= RECOVERY_TOLERANCE for hours, _ in points):
        findings.append("recovery-series-has-no-point-after-the-exposure")

    if len(points) < 2:
        findings.append("recovery-series-too-short-to-show-a-trend")
        monotonic = True
    else:
        monotonic = series_is_monotonic(points)
        if not monotonic:
            findings.append("recovery-series-moves-away-from-the-pristine-value")

    floor = permanent_degradation(points)
    if floor < -RECOVERY_TOLERANCE:
        findings.append("series-recovered-past-the-pristine-value")

    healed = recovered_fraction(as_irradiated, floor)

    time_constant = None
    half_time = None
    if monotonic and len(points) >= 2:
        for hours, degradation in points[:-1]:
            try:
                time_constant = recovery_time_constant(
                    hours, degradation, as_irradiated, floor
                )
            except ValueError:
                continue
            half_time = recovery_half_time(time_constant)
            break
    if time_constant is None:
        findings.append("no-point-usable-for-a-recovery-time-constant")

    credit_record = {
        "exposure_regime": record.get("exposure_regime"),
        "quiet_interval_h": record.get("quiet_interval_h", 0.0),
        "recovery_half_time_h": (
            half_time if half_time is not None else record.get("recovery_half_time_h", 1.0)
        ),
    }
    credit_reasons = recovery_credit_reasons(credit_record)
    credited = not credit_reasons

    claimed = record.get("credit_claimed", False)
    if not isinstance(claimed, bool):
        raise ValueError("credit_claimed must be true or false")
    if claimed and not credited:
        findings.append("recovery-credit-claimed-but-not-admissible")

    design_degradation = floor if credited else as_irradiated

    return {
        "property": name,
        "as_irradiated_degradation": as_irradiated,
        "permanent_degradation": floor,
        "recovered_fraction": healed,
        "recovery_time_constant_h": time_constant,
        "recovery_half_time_h": half_time,
        "credit_admissible": credited,
        "credit_reasons": credit_reasons,
        "design_degradation": design_degradation,
        "findings": findings,
        "evaluated": not findings,
    }
