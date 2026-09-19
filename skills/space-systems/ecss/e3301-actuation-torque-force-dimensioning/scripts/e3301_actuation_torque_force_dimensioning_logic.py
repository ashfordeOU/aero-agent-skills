"""Actuation torque and force dimensioning for a spacecraft mechanism.

Anchor: ECSS-E-ST-33-01 clause 4.7.5.3.2 (paraphrased into an
implementable procedure; no standard text is reproduced).

Procedure implemented here:

1. Compare capability against demand at stations, not once. The
   available torque of an actuator varies with position, temperature,
   bus voltage and age; the resistive torque varies with position and
   wear. A single comparison at one operating point says nothing about
   where the two curves cross.
2. Derate the available torque at each station. The nominal capability
   is reduced by the worst bus voltage the mechanism is qualified to,
   the temperature extreme it operates at, the degradation it has
   accumulated by that life point, and any supply current limit. Each
   deration is a factor at or below unity, and an end-of-life station
   that declares no degradation deration has not been shown to be an
   end-of-life station at all.
3. Take the motorization margin at each station as the available
   torque over the factored resistive torque, minus one, and hold it
   against the margin the project requires.
4. Require the station schedule to cover the travel range at every
   life point, with no gap wide enough to hide a crossing.
5. Report the governing station and life point, so the redesign is
   aimed at the place where the mechanism is actually short.

Stdlib only, offline, deterministic.
"""

VALID_LIFE_POINTS = ("begin-of-life", "end-of-life")

VALID_UNITS = ("torque-nm", "force-n")

# Derations that may be applied to the nominal available capability.
# Each is a factor at or below unity.
VALID_DERATION_KEYS = (
    "low-bus-voltage",
    "temperature-extreme",
    "end-of-life-degradation",
    "supply-current-limit",
)

# A station at end of life owes this deration explicitly.
END_OF_LIFE_DERATION_KEY = "end-of-life-degradation"

# Widest travel gap a station schedule may leave, as a share of the
# declared range, with an absolute floor for very short travels.
MAX_TRAVEL_GAP_FRACTION = 0.10
MIN_TRAVEL_GAP = 1.0

# A gap that lands exactly on the allowed width is a pass. The width is a
# product of floats, so the comparison is relaxed by a relative tolerance
# rather than tested strictly.
GAP_RELATIVE_TOLERANCE = 1.0e-12

# A motorization margin is a quotient of floats minus one, so a station
# sized exactly to its demand can land a few units in the last place
# either side of the requirement. This tolerance absorbs that.
MARGIN_TOLERANCE = 1.0e-12

VERDICT_POSITIVE = "positive"
VERDICT_ZERO = "zero"
VERDICT_NEGATIVE = "negative"


def _numeric(label, value, minimum=None, maximum=None):
    if not isinstance(value, (int, float)) or isinstance(value, bool):
        raise ValueError("%s must be numeric, got %r" % (label, value))
    value = float(value)
    if minimum is not None and value < minimum:
        raise ValueError("%s must be >= %r, got %r" % (label, minimum, value))
    if maximum is not None and value > maximum:
        raise ValueError("%s must be <= %r, got %r" % (label, maximum, value))
    return value


def _identifier(label, value):
    if not isinstance(value, str) or not value.strip():
        raise ValueError("%s must be a non-empty string" % label)
    return value.strip()


def validate_derations(derations, label="derations"):
    """Validate a deration mapping and return a normalized copy."""
    if derations is None:
        return {}
    if not isinstance(derations, dict):
        raise ValueError("%s must be a mapping" % label)
    normalized = {}
    for key, value in derations.items():
        if key not in VALID_DERATION_KEYS:
            raise ValueError(
                "%s has unknown deration %r (expected one of %s)"
                % (label, key, ", ".join(VALID_DERATION_KEYS))
            )
        factor = _numeric("%s %s" % (label, key), value, 0.0, 1.0)
        if factor <= 0.0:
            raise ValueError("%s %s must be positive" % (label, key))
        normalized[key] = factor
    return normalized


def available_capability(nominal_capability, derations):
    """Nominal capability reduced by every declared deration."""
    nominal = _numeric("nominal_capability", nominal_capability, 0.0)
    if nominal <= 0.0:
        raise ValueError("nominal_capability must be positive")
    normalized = validate_derations(derations)
    value = nominal
    for key in sorted(normalized):
        value *= normalized[key]
    return value


def motorization_margin(available, factored_resistive):
    """Available capability over the factored resistive demand, minus one."""
    avail = _numeric("available", available, 0.0)
    demand = _numeric("factored_resistive", factored_resistive, 0.0)
    if demand <= 0.0:
        raise ValueError("factored_resistive must be positive")
    return avail / demand - 1.0


def margin_verdict(margin, required_margin=0.0):
    """Group a margin against its requirement within representation tolerance."""
    margin = _numeric("margin", margin)
    required = _numeric("required_margin", required_margin, 0.0)
    delta = margin - required
    if delta > MARGIN_TOLERANCE:
        return VERDICT_POSITIVE
    if delta < -MARGIN_TOLERANCE:
        return VERDICT_NEGATIVE
    return VERDICT_ZERO


def validate_station(station):
    """Validate one travel station and return a normalized copy."""
    if not isinstance(station, dict):
        raise ValueError("station must be a mapping")
    sid = _identifier("station id", station.get("id"))
    position = _numeric("station %s travel_position" % sid, station.get("travel_position"), 0.0)
    life_point = station.get("life_point")
    if life_point not in VALID_LIFE_POINTS:
        raise ValueError(
            "station %s has unknown life_point %r (expected one of %s)"
            % (sid, life_point, ", ".join(VALID_LIFE_POINTS))
        )
    nominal = _numeric(
        "station %s nominal_capability" % sid, station.get("nominal_capability"), 0.0
    )
    if nominal <= 0.0:
        raise ValueError("station %s nominal_capability must be positive" % sid)
    demand = _numeric(
        "station %s factored_resistive" % sid, station.get("factored_resistive"), 0.0
    )
    if demand <= 0.0:
        raise ValueError("station %s factored_resistive must be positive" % sid)
    derations = validate_derations(
        station.get("derations"), "station %s derations" % sid
    )
    return {
        "id": sid,
        "travel_position": position,
        "life_point": life_point,
        "nominal_capability": nominal,
        "factored_resistive": demand,
        "derations": derations,
    }


def assess_station(station, required_margin=0.0):
    """Assess one travel station against clause 4.7.5.3.2."""
    norm = validate_station(station)
    required = _numeric("required_margin", required_margin, 0.0)
    available = available_capability(norm["nominal_capability"], norm["derations"])
    margin = motorization_margin(available, norm["factored_resistive"])
    verdict = margin_verdict(margin, required)
    findings = []
    if verdict == VERDICT_NEGATIVE:
        findings.append("motorization-margin-below-requirement")
    if (
        norm["life_point"] == "end-of-life"
        and END_OF_LIFE_DERATION_KEY not in norm["derations"]
    ):
        findings.append("end-of-life-degradation-not-applied")
    return {
        "id": norm["id"],
        "travel_position": norm["travel_position"],
        "life_point": norm["life_point"],
        "available_capability": available,
        "factored_resistive": norm["factored_resistive"],
        "motorization_margin": margin,
        "verdict": verdict,
        "findings": findings,
        "compliant": not findings,
    }


def travel_coverage_findings(stations, travel_range, life_point):
    """Findings about how one life point's stations cover the travel range."""
    span = _numeric("travel_range", travel_range, 0.0)
    if span <= 0.0:
        raise ValueError("travel_range must be positive")
    if life_point not in VALID_LIFE_POINTS:
        raise ValueError("unknown life_point %r" % (life_point,))
    positions = sorted(
        validate_station(s)["travel_position"]
        for s in stations
        if validate_station(s)["life_point"] == life_point
    )
    if not positions:
        return ["no-station-at:%s" % life_point]
    findings = []
    allowed_gap = max(MIN_TRAVEL_GAP, MAX_TRAVEL_GAP_FRACTION * span)
    allowed_gap *= 1.0 + GAP_RELATIVE_TOLERANCE
    if positions[0] > allowed_gap:
        findings.append("travel-start-not-covered:%s" % life_point)
    if span - positions[-1] > allowed_gap:
        findings.append("travel-end-not-covered:%s" % life_point)
    for low, high in zip(positions, positions[1:]):
        if high - low > allowed_gap:
            findings.append("travel-gap-wider-than-allowed:%s" % life_point)
            break
    return findings


def assess_actuation_dimensioning(function_record):
    """Assess the actuation dimensioning of one mechanism function."""
    if not isinstance(function_record, dict):
        raise ValueError("function_record must be a mapping")
    fid = _identifier("function id", function_record.get("id"))
    units = function_record.get("units")
    if units not in VALID_UNITS:
        raise ValueError(
            "function %s has unknown units %r (expected one of %s)"
            % (fid, units, ", ".join(VALID_UNITS))
        )
    travel_range = _numeric(
        "function %s travel_range" % fid, function_record.get("travel_range"), 0.0
    )
    if travel_range <= 0.0:
        raise ValueError("function %s travel_range must be positive" % fid)
    required_margin = _numeric(
        "function %s required_margin" % fid,
        function_record.get("required_margin", 0.0),
        0.0,
    )
    required_life_points = function_record.get(
        "required_life_points", list(VALID_LIFE_POINTS)
    )
    if not isinstance(required_life_points, (list, tuple)) or not required_life_points:
        raise ValueError("function %s needs a non-empty required_life_points" % fid)
    stations = function_record.get("stations")
    if not isinstance(stations, list) or not stations:
        raise ValueError("function %s needs a non-empty stations list" % fid)

    results = []
    seen = set()
    for station in stations:
        result = assess_station(station, required_margin)
        if result["id"] in seen:
            raise ValueError("duplicate station id %r" % (result["id"],))
        seen.add(result["id"])
        results.append(result)

    coverage = []
    for life_point in required_life_points:
        coverage.extend(travel_coverage_findings(stations, travel_range, life_point))

    governing = min(results, key=lambda r: r["motorization_margin"])
    failing = [r["id"] for r in results if not r["compliant"]]
    return {
        "function_id": fid,
        "units": units,
        "travel_range": travel_range,
        "required_margin": required_margin,
        "stations": results,
        "coverage_findings": coverage,
        "governing_station_id": governing["id"],
        "governing_life_point": governing["life_point"],
        "governing_margin": governing["motorization_margin"],
        "non_compliant_station_ids": failing,
        "compliant": not failing and not coverage,
    }
