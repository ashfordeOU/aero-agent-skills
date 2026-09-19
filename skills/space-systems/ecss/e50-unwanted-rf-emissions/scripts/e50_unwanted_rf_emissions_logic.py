"""Unwanted RF emission assessment for a space link transmitter.

Anchor: ECSS-E-ST-50C clause 5.6.12.3 -- requirements on the unwanted emissions
a space link transmitter produces. Paraphrased into an implementable procedure;
no standard text is reproduced.

One normative obligation is implemented: the emissions a transmitter produces
outside the bandwidth its wanted signal necessarily occupies are held below the
limits that apply to them. Doing that means deciding, for each emission
component, which domain it falls in -- inside the necessary bandwidth, in the
out-of-band domain immediately around it, or out in the spurious domain -- and
then measuring it against the limit for that domain, because the domains carry
different limits and an emission graded against the wrong one is graded wrong.

Levels are carried in decibels relative to the carrier throughout, so the
arithmetic is add and subtract and the result is reproducible across platforms.
Domain boundaries are decided with a tolerance, so a component sitting exactly
on a boundary is placed the same way everywhere.
"""

import math

__all__ = [
    "IN_BAND",
    "OUT_OF_BAND",
    "SPURIOUS",
    "WITHIN_LIMITS",
    "MARGIN_SHORT",
    "LIMITS_EXCEEDED",
    "OUT_OF_BAND_EDGE_RATIO",
    "REL_TOL",
    "DEFAULT_REQUIRED_MARGIN_DB",
    "validate_frequency",
    "validate_bandwidth",
    "validate_level_dbc",
    "normalize_mask",
    "mask_limit_dbc",
    "emission_domain",
    "assess_emission",
    "assess_emission_set",
]

IN_BAND = "in-band"
OUT_OF_BAND = "out-of-band"
SPURIOUS = "spurious"

WITHIN_LIMITS = "within-limits"
MARGIN_SHORT = "margin-short"
LIMITS_EXCEEDED = "limits-exceeded"

# The out-of-band domain runs from the edge of the necessary bandwidth out to
# this multiple of that bandwidth either side of the carrier. Beyond it the
# spurious domain begins and a different limit applies.
OUT_OF_BAND_EDGE_RATIO = 2.5

REL_TOL = 1e-9

# Design margin the assessment asks for before it calls an emission comfortable.
# A component that meets its limit with nothing to spare meets it only on the
# day it was measured.
DEFAULT_REQUIRED_MARGIN_DB = 3.0


def _validate_number(value, name):
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise ValueError("%s must be a number" % name)
    number = float(value)
    if math.isnan(number) or math.isinf(number):
        raise ValueError("%s must be finite" % name)
    return number


def validate_frequency(value, name="frequency_hz"):
    """Return a strictly positive frequency in hertz."""
    frequency = _validate_number(value, name)
    if frequency <= 0.0:
        raise ValueError("%s must be greater than zero, got %r" % (name, value))
    return frequency


def validate_bandwidth(value, name="necessary_bandwidth_hz"):
    """Return a strictly positive bandwidth in hertz."""
    bandwidth = _validate_number(value, name)
    if bandwidth <= 0.0:
        raise ValueError("%s must be greater than zero, got %r" % (name, value))
    return bandwidth


def validate_level_dbc(value, name="level_dbc"):
    """Return a level in decibels relative to the carrier.

    A positive level means an emission stronger than the carrier itself. That
    is physically possible only as a measurement or bookkeeping error on a
    transmitter, so it is rejected rather than quietly graded.
    """
    level = _validate_number(value, name)
    if level > 0.0:
        raise ValueError(
            "%s must not exceed 0 dBc; an unwanted emission stronger than the "
            "carrier is a measurement error, got %r" % (name, value)
        )
    return level


def normalize_mask(points):
    """Return the out-of-band spectral mask as sorted breakpoints.

    Each breakpoint is an offset expressed in multiples of the necessary
    bandwidth paired with the limit in dBc that applies there. Between
    breakpoints the limit is interpolated; outside them it is held flat.
    """
    if isinstance(points, dict) or not isinstance(points, (list, tuple)):
        raise ValueError("mask must be a list or tuple of breakpoints")
    if len(points) < 2:
        raise ValueError("mask needs at least two breakpoints to interpolate")
    normalized = []
    for point in points:
        if isinstance(point, dict):
            if "offset_ratio" not in point or "limit_dbc" not in point:
                raise ValueError("mask breakpoint needs offset_ratio and limit_dbc")
            offset = point["offset_ratio"]
            limit = point["limit_dbc"]
        elif isinstance(point, (list, tuple)) and len(point) == 2:
            offset, limit = point
        else:
            raise ValueError("mask breakpoint must be a pair or a mapping")
        offset = _validate_number(offset, "offset_ratio")
        if offset < 0.0:
            raise ValueError("offset_ratio must not be negative, got %r" % offset)
        normalized.append((offset, validate_level_dbc(limit, "limit_dbc")))
    normalized.sort(key=lambda item: item[0])
    for index in range(1, len(normalized)):
        if normalized[index][0] <= normalized[index - 1][0]:
            raise ValueError("mask breakpoints must have distinct offsets")
    return normalized


def mask_limit_dbc(mask, offset_ratio):
    """Return the mask limit at an offset given in multiples of the bandwidth."""
    breakpoints = normalize_mask(mask)
    offset = _validate_number(offset_ratio, "offset_ratio")
    if offset < 0.0:
        raise ValueError("offset_ratio must not be negative, got %r" % offset_ratio)
    if offset <= breakpoints[0][0]:
        return breakpoints[0][1]
    if offset >= breakpoints[-1][0]:
        return breakpoints[-1][1]
    for index in range(1, len(breakpoints)):
        low_offset, low_limit = breakpoints[index - 1]
        high_offset, high_limit = breakpoints[index]
        if offset <= high_offset:
            span = high_offset - low_offset
            fraction = (offset - low_offset) / span
            return low_limit + fraction * (high_limit - low_limit)
    return breakpoints[-1][1]


def emission_domain(centre_hz, necessary_bandwidth_hz, frequency_hz):
    """Return which emission domain a component at this frequency falls in."""
    centre = validate_frequency(centre_hz, "centre_hz")
    bandwidth = validate_bandwidth(necessary_bandwidth_hz)
    frequency = validate_frequency(frequency_hz, "frequency_hz")
    offset = abs(frequency - centre)
    tolerance = REL_TOL * bandwidth
    if offset <= bandwidth / 2.0 + tolerance:
        return IN_BAND
    if offset <= OUT_OF_BAND_EDGE_RATIO * bandwidth + tolerance:
        return OUT_OF_BAND
    return SPURIOUS


def assess_emission(
    component,
    centre_hz,
    necessary_bandwidth_hz,
    mask,
    spurious_limit_dbc,
    required_margin_db=DEFAULT_REQUIRED_MARGIN_DB,
):
    """Assess one measured emission component against the limit for its domain.

    An in-band component is the wanted emission, not an unwanted one, so it is
    reported and not graded -- applying the out-of-band mask inside the
    necessary bandwidth fails the carrier against its own transmitter.
    """
    if not isinstance(component, dict):
        raise ValueError("component must be a mapping with frequency_hz and level_dbc")
    for key in ("frequency_hz", "level_dbc"):
        if key not in component:
            raise ValueError("component is missing %s" % key)
    centre = validate_frequency(centre_hz, "centre_hz")
    bandwidth = validate_bandwidth(necessary_bandwidth_hz)
    frequency = validate_frequency(component["frequency_hz"], "frequency_hz")
    level = validate_level_dbc(component["level_dbc"])
    spurious_limit = validate_level_dbc(spurious_limit_dbc, "spurious_limit_dbc")
    margin_required = _validate_number(required_margin_db, "required_margin_db")
    if margin_required < 0.0:
        raise ValueError("required_margin_db must not be negative")

    domain = emission_domain(centre, bandwidth, frequency)
    offset_hz = abs(frequency - centre)
    offset_ratio = offset_hz / bandwidth

    if domain == IN_BAND:
        return {
            "frequency_hz": frequency,
            "level_dbc": level,
            "offset_hz": offset_hz,
            "offset_ratio": offset_ratio,
            "domain": domain,
            "limit_dbc": None,
            "margin_db": None,
            "graded": False,
            "compliant": True,
            "comfortable": True,
        }

    if domain == OUT_OF_BAND:
        limit = mask_limit_dbc(mask, offset_ratio)
    else:
        limit = spurious_limit

    margin = limit - level
    compliant = margin >= -REL_TOL
    comfortable = margin >= margin_required - REL_TOL
    return {
        "frequency_hz": frequency,
        "level_dbc": level,
        "offset_hz": offset_hz,
        "offset_ratio": offset_ratio,
        "domain": domain,
        "limit_dbc": limit,
        "margin_db": margin,
        "graded": True,
        "compliant": compliant,
        "comfortable": comfortable,
    }


def assess_emission_set(
    components,
    centre_hz,
    necessary_bandwidth_hz,
    mask,
    spurious_limit_dbc,
    required_margin_db=DEFAULT_REQUIRED_MARGIN_DB,
):
    """Assess a whole measured emission set and report the governing verdict.

    Three outcomes are separated: every graded component clears its limit with
    the design margin; every component clears its limit but at least one has
    less margin than asked for; or at least one component is over its limit.
    """
    if isinstance(components, dict) or not isinstance(components, (list, tuple)):
        raise ValueError("components must be a list or tuple of mappings")
    if not components:
        raise ValueError("components must not be empty")

    results = []
    counts = {IN_BAND: 0, OUT_OF_BAND: 0, SPURIOUS: 0}
    exceedances = []
    thin = []
    worst_margin = None
    worst_component = None

    for component in components:
        result = assess_emission(
            component,
            centre_hz,
            necessary_bandwidth_hz,
            mask,
            spurious_limit_dbc,
            required_margin_db,
        )
        results.append(result)
        counts[result["domain"]] += 1
        if not result["graded"]:
            continue
        if worst_margin is None or result["margin_db"] < worst_margin:
            worst_margin = result["margin_db"]
            worst_component = result
        if not result["compliant"]:
            exceedances.append(result)
        elif not result["comfortable"]:
            thin.append(result)

    if exceedances:
        verdict = LIMITS_EXCEEDED
    elif thin:
        verdict = MARGIN_SHORT
    else:
        verdict = WITHIN_LIMITS

    findings = []
    for result in exceedances:
        findings.append(
            "%s emission at %.6g Hz is %.6g dB over its limit"
            % (result["domain"], result["frequency_hz"], -result["margin_db"])
        )
    for result in thin:
        findings.append(
            "%s emission at %.6g Hz clears its limit by only %.6g dB"
            % (result["domain"], result["frequency_hz"], result["margin_db"])
        )

    return {
        "results": results,
        "domain_counts": counts,
        "graded_count": counts[OUT_OF_BAND] + counts[SPURIOUS],
        "exceedance_count": len(exceedances),
        "worst_margin_db": worst_margin,
        "worst_component": worst_component,
        "compliant": not exceedances,
        "verdict": verdict,
        "findings": findings,
    }
