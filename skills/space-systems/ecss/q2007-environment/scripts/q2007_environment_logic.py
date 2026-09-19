"""Infrastructure suitability and work-environment control in a test centre.

Anchor: ECSS-Q-ST-20-07C clauses 5.5.1 and 5.5.2 (paraphrased into an
implementable procedure; no standard text is reproduced).

Two questions are answered here and they are deliberately kept apart,
because a centre can pass one and fail the other:

A. Suitability (5.5.1). Can this facility hold the environment the test
   asks for at all? The facility declares a capability band per parameter;
   the test declares a required band. The capability band has to contain
   the required band, and the amount by which it does is the containment
   margin -- the room the operator has before the facility is running at
   its own limit. A facility whose capability exactly equals the
   requirement is suitable and has no margin, and those are different
   statements that a single pass/fail hides.

B. Control (5.5.2). Does the facility actually hold it during the test?
   The monitored series for each parameter is checked against the required
   band: how many readings sit outside it, on which side, by how much, and
   how long the longest unbroken excursion lasted. A parameter monitored
   too rarely to see an excursion is a finding in its own right even when
   every recorded reading is inside the band.

Power quality is handled the same way but the band is derived rather than
declared: a nominal value plus a tolerance in percent becomes an absolute
band, so a 230 V supply held to 10 percent is compared as 207 V to 253 V.
Media (a purge gas, a coolant, a vacuum pumping line) are treated as
ordinary parameters with their own bands, because the failure mode --
drifting out of band unobserved -- is identical.

Float care: every band comparison carries a relative tolerance, so a
reading that lands exactly on a limit is inside it on any platform. Limits
derived by multiplication (the power-quality bands) are the reason this
matters; a strict comparison there is a portability defect, not a
tightening of the requirement.

Stdlib only, offline, deterministic.
"""

PARAMETER_UNITS = {
    "air-temperature": "degC",
    "relative-humidity": "percent",
    "supply-voltage": "V",
    "supply-frequency": "Hz",
    "purge-gas-dew-point": "degC",
    "chilled-water-temperature": "degC",
    "cleanroom-overpressure": "Pa",
}
VALID_PARAMETERS = tuple(sorted(PARAMETER_UNITS))

# A band limit is compared with this relative slack so a reading sitting
# exactly on a derived limit is inside the band on every platform.
BAND_RELATIVE_TOLERANCE = 1.0e-9
# Absolute floor for the slack, for parameters whose limits pass through
# zero (a dew point, an overpressure) where a relative slack vanishes.
BAND_ABSOLUTE_TOLERANCE = 1.0e-9

FINDING_NOT_CONTAINED_LOW = "facility-capability-above-the-required-lower-limit"
FINDING_NOT_CONTAINED_HIGH = "facility-capability-below-the-required-upper-limit"
FINDING_NO_CAPABILITY = "facility-declares-no-capability-for-the-parameter"
FINDING_NO_MONITORING = "parameter-not-monitored"
FINDING_INTERVAL_TOO_LONG = "monitoring-interval-longer-than-required"
FINDING_EXCURSION = "monitored-value-outside-the-required-band"


def _numeric(label, value):
    if not isinstance(value, (int, float)) or isinstance(value, bool):
        raise ValueError("%s must be numeric, got %r" % (label, value))
    return float(value)


def _slack(reference):
    return max(BAND_ABSOLUTE_TOLERANCE, abs(reference) * BAND_RELATIVE_TOLERANCE)


def validate_parameter(name):
    """Confirm a parameter name is one this procedure knows."""
    if name not in PARAMETER_UNITS:
        raise ValueError(
            "unknown parameter %r (expected one of %s)"
            % (name, ", ".join(VALID_PARAMETERS))
        )
    return name


def validate_band(label, band):
    """Validate a (lower, upper) band and return it as a float pair."""
    if isinstance(band, (str, bytes)) or not isinstance(band, (list, tuple)):
        raise ValueError("%s must be a (lower, upper) pair, got %r" % (label, band))
    if len(band) != 2:
        raise ValueError("%s must have exactly two limits, got %r" % (label, band))
    lower = _numeric("%s lower limit" % label, band[0])
    upper = _numeric("%s upper limit" % label, band[1])
    if lower > upper:
        raise ValueError(
            "%s lower limit %r is above its upper limit %r" % (label, lower, upper)
        )
    return (lower, upper)


def band_from_tolerance(nominal, tolerance_percent):
    """Absolute band around a nominal value held to a percentage tolerance."""
    centre = _numeric("nominal", nominal)
    pct = _numeric("tolerance_percent", tolerance_percent)
    if pct < 0:
        raise ValueError("tolerance_percent must not be negative, got %r" % (pct,))
    if pct > 100:
        raise ValueError("tolerance_percent above 100 leaves no band, got %r" % (pct,))
    span = abs(centre) * pct / 100.0
    return (centre - span, centre + span)


def band_contains(outer, inner):
    """True when the outer band covers the inner band, limits included."""
    outer_low, outer_high = validate_band("outer band", outer)
    inner_low, inner_high = validate_band("inner band", inner)
    return (
        outer_low <= inner_low + _slack(inner_low)
        and outer_high >= inner_high - _slack(inner_high)
    )


def containment_margin(outer, inner):
    """Room left at each end of the outer band, (lower, upper)."""
    outer_low, outer_high = validate_band("outer band", outer)
    inner_low, inner_high = validate_band("inner band", inner)
    return (inner_low - outer_low, outer_high - inner_high)


def value_in_band(value, band):
    """True when a reading sits inside the band, limits included."""
    reading = _numeric("value", value)
    lower, upper = validate_band("band", band)
    return lower - _slack(lower) <= reading <= upper + _slack(upper)


def band_utilisation(value, band):
    """How far a reading sits from the band centre, as a fraction of half-width."""
    reading = _numeric("value", value)
    lower, upper = validate_band("band", band)
    half_width = (upper - lower) / 2.0
    if half_width <= 0.0:
        raise ValueError("a band of zero width has no utilisation")
    centre = (upper + lower) / 2.0
    return abs(reading - centre) / half_width


def excursions(readings, band):
    """Every reading outside the band, with the side and the magnitude."""
    if isinstance(readings, (str, bytes)) or not isinstance(readings, (list, tuple)):
        raise ValueError("readings must be a list or tuple")
    lower, upper = validate_band("band", band)
    out = []
    for index, raw in enumerate(readings):
        value = _numeric("reading %d" % index, raw)
        if value < lower - _slack(lower):
            out.append(
                {
                    "index": index,
                    "value": value,
                    "side": "below",
                    "magnitude": lower - value,
                }
            )
        elif value > upper + _slack(upper):
            out.append(
                {
                    "index": index,
                    "value": value,
                    "side": "above",
                    "magnitude": value - upper,
                }
            )
    return out


def longest_excursion_seconds(readings, band, sample_interval_s):
    """Duration of the longest unbroken run of out-of-band readings."""
    interval = _numeric("sample_interval_s", sample_interval_s)
    if interval <= 0:
        raise ValueError("sample_interval_s must be positive, got %r" % (interval,))
    out_indices = {e["index"] for e in excursions(readings, band)}
    longest = 0
    run = 0
    for index in range(len(readings)):
        if index in out_indices:
            run += 1
            longest = max(longest, run)
        else:
            run = 0
    return longest * interval


def assess_parameter(spec):
    """Assess one parameter for suitability and for control."""
    if not isinstance(spec, dict):
        raise ValueError("parameter spec must be a mapping")
    name = validate_parameter(spec.get("parameter"))
    required = validate_band("%s required band" % name, spec.get("required_band"))
    capability = spec.get("capability_band")
    findings = []
    margin = None
    if capability is None:
        findings.append(FINDING_NO_CAPABILITY)
    else:
        capability = validate_band("%s capability band" % name, capability)
        margin = containment_margin(capability, required)
        if not band_contains(capability, required):
            if margin[0] < 0:
                findings.append(FINDING_NOT_CONTAINED_LOW)
            if margin[1] < 0:
                findings.append(FINDING_NOT_CONTAINED_HIGH)
    readings = spec.get("readings", [])
    if isinstance(readings, (str, bytes)) or not isinstance(readings, (list, tuple)):
        raise ValueError("%s readings must be a list or tuple" % name)
    interval = spec.get("sample_interval_s")
    required_interval = spec.get("required_interval_s")
    worst = None
    out = []
    if not readings:
        findings.append(FINDING_NO_MONITORING)
    else:
        out = excursions(readings, required)
        if out:
            findings.append(FINDING_EXCURSION)
        worst = max(band_utilisation(r, required) for r in readings)
    if interval is not None and required_interval is not None:
        interval = _numeric("%s sample_interval_s" % name, interval)
        required_interval = _numeric("%s required_interval_s" % name, required_interval)
        if interval > required_interval + _slack(required_interval):
            findings.append(FINDING_INTERVAL_TOO_LONG)
    duration = None
    if readings and interval is not None:
        duration = longest_excursion_seconds(readings, required, interval)
    return {
        "parameter": name,
        "unit": PARAMETER_UNITS[name],
        "required_band": required,
        "capability_band": capability,
        "containment_margin": margin,
        "excursions": out,
        "longest_excursion_s": duration,
        "worst_band_utilisation": worst,
        "findings": findings,
        "controlled": not findings,
    }


def assess_work_environment(specs):
    """Run the full clause 5.5.1-5.5.2 assessment over a facility."""
    if not isinstance(specs, list) or not specs:
        raise ValueError("specs must be a non-empty list")
    results = []
    seen = set()
    for spec in specs:
        result = assess_parameter(spec)
        if result["parameter"] in seen:
            raise ValueError("duplicate parameter %r" % (result["parameter"],))
        seen.add(result["parameter"])
        results.append(result)
    uncontrolled = [r["parameter"] for r in results if not r["controlled"]]
    unsuitable = [
        r["parameter"]
        for r in results
        if FINDING_NOT_CONTAINED_LOW in r["findings"]
        or FINDING_NOT_CONTAINED_HIGH in r["findings"]
        or FINDING_NO_CAPABILITY in r["findings"]
    ]
    return {
        "parameters": results,
        "unsuitable_parameters": unsuitable,
        "uncontrolled_parameters": uncontrolled,
        "suitable": not unsuitable,
        "controlled": not uncontrolled,
    }
