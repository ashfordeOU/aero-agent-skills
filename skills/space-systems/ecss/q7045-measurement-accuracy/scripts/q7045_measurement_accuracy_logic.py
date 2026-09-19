"""Measurement-accuracy budget for metallic mechanical testing.

Anchor: ECSS-Q-ST-70-45 equipment clause -- the accuracy the force, strain,
displacement and temperature channels of a mechanical test have to hold, and
what that accuracy becomes once it is carried into a reported property.
Paraphrased into an implementable procedure; no standard text is reproduced.

Procedure implemented here
--------------------------
1. Grade each measuring channel against the accuracy limit that applies to it,
   keeping a relative limit relative and an absolute limit absolute.
2. Turn a declared resolution or a declared half-width into the standard
   uncertainty it contributes, so a digital step and a drift band can sit in
   the same budget.
3. Combine independent contributions in quadrature into a combined standard
   uncertainty and expand it with a coverage factor.
4. Propagate the channel uncertainties into the reported properties: a stress
   carries the force channel and twice the diameter, a modulus carries force,
   strain, gauge length and area together.
5. Name the dominant contributor, compare the expanded relative uncertainty
   against the target the property owes, and state whether the chain supports
   the number that is about to be reported.
"""

import math

__all__ = [
    "DEFAULT_RELATIVE_LIMITS_PCT",
    "DEFAULT_TEMPERATURE_LIMIT_K",
    "DEFAULT_COVERAGE_FACTOR",
    "BUDGET_TOLERANCE",
    "resolution_standard_uncertainty",
    "rectangular_standard_uncertainty",
    "combine_in_quadrature",
    "expanded_uncertainty",
    "relative_percent",
    "area_relative_uncertainty_pct",
    "stress_relative_uncertainty_pct",
    "modulus_relative_uncertainty_pct",
    "channel_findings",
    "dominant_contributor",
    "assess_measurement_accuracy",
]

# Relative accuracy limits, in percent of reading, for the channels that carry
# a relative specification.
DEFAULT_RELATIVE_LIMITS_PCT = {
    "force": 1.0,
    "strain": 1.0,
    "displacement": 1.0,
    "diameter": 0.5,
    "gauge_length": 1.0,
}

# The temperature channel carries an absolute limit in kelvin, not a relative
# one: a two-kelvin error is two kelvin whether the soak is at 100 K or 900 K.
DEFAULT_TEMPERATURE_LIMIT_K = 2.0

# Coverage factor for an expanded uncertainty at roughly ninety-five percent.
DEFAULT_COVERAGE_FACTOR = 2.0

# A budget comparison is a comparison of two floats built by square roots. A
# figure that is physically exactly on its target can land a few ULP either
# side, so absorb the representation error instead of moving the target.
BUDGET_TOLERANCE = 1e-12

_SQRT_3 = math.sqrt(3.0)


def _non_negative(label, value):
    if not isinstance(value, (int, float)) or isinstance(value, bool):
        raise ValueError("%s must be a real number, got %r" % (label, value))
    number = float(value)
    if not math.isfinite(number):
        raise ValueError("%s must be finite, got %r" % (label, value))
    if number < 0.0:
        raise ValueError("%s must not be negative, got %r" % (label, value))
    return number


def _positive(label, value):
    number = _non_negative(label, value)
    if number == 0.0:
        raise ValueError("%s must be positive, got %r" % (label, value))
    return number


def resolution_standard_uncertainty(resolution):
    """Return the standard uncertainty a digital step of this size contributes.

    A reading quantised to a step is uniform over that step, whose half-width
    is half the step, so the standard uncertainty is the step over two root
    three -- not the step itself, and not half of it.
    """
    step = _non_negative("resolution", resolution)
    return step / (2.0 * _SQRT_3)


def rectangular_standard_uncertainty(half_width):
    """Return the standard uncertainty of a band quoted as plus or minus a half-width."""
    width = _non_negative("half_width", half_width)
    return width / _SQRT_3


def combine_in_quadrature(components):
    """Combine independent standard uncertainties into a combined one."""
    if not isinstance(components, (list, tuple)) or not components:
        raise ValueError("components must be a non-empty sequence of uncertainties")
    total = 0.0
    for index, item in enumerate(components):
        value = _non_negative("components[%d]" % index, item)
        total += value * value
    return math.sqrt(total)


def expanded_uncertainty(standard, coverage_factor=DEFAULT_COVERAGE_FACTOR):
    """Expand a standard uncertainty by a coverage factor."""
    value = _non_negative("standard", standard)
    k = _positive("coverage_factor", coverage_factor)
    if k < 1.0 or k > 3.0:
        raise ValueError("coverage_factor must lie between one and three, got %r" % (coverage_factor,))
    return k * value


def relative_percent(absolute, value):
    """Return an absolute uncertainty as a percentage of the value it sits on."""
    if not isinstance(value, (int, float)) or isinstance(value, bool):
        raise ValueError("value must be a real number, got %r" % (value,))
    magnitude = abs(float(value))
    if not math.isfinite(magnitude) or magnitude == 0.0:
        raise ValueError("value must be non-zero and finite, got %r" % (value,))
    return 100.0 * _non_negative("absolute", absolute) / magnitude


def area_relative_uncertainty_pct(diameter_relative_pct):
    """Return the relative uncertainty of a circular area from its diameter.

    Area goes as the square of the diameter, so the relative uncertainty
    doubles; halving it because two diameters were averaged is a different
    correction and does not belong here.
    """
    return 2.0 * _non_negative("diameter_relative_pct", diameter_relative_pct)


def stress_relative_uncertainty_pct(force_relative_pct, diameter_relative_pct):
    """Return the relative uncertainty of an engineering stress."""
    force = _non_negative("force_relative_pct", force_relative_pct)
    area = area_relative_uncertainty_pct(diameter_relative_pct)
    return combine_in_quadrature([force, area])


def modulus_relative_uncertainty_pct(force_relative_pct, strain_relative_pct,
                                     gauge_length_relative_pct=0.0,
                                     diameter_relative_pct=0.0):
    """Return the relative uncertainty of a modulus taken from a slope."""
    force = _non_negative("force_relative_pct", force_relative_pct)
    strain = _non_negative("strain_relative_pct", strain_relative_pct)
    length = _non_negative("gauge_length_relative_pct", gauge_length_relative_pct)
    area = area_relative_uncertainty_pct(diameter_relative_pct)
    return combine_in_quadrature([force, strain, length, area])


def channel_findings(channels, relative_limits=None,
                     temperature_limit_k=DEFAULT_TEMPERATURE_LIMIT_K):
    """Grade each channel against the accuracy limit that applies to it.

    channels: mapping of channel name to its error. A relative channel carries
    {"relative_pct": x}; the temperature channel carries {"absolute_k": x}.
    """
    if not isinstance(channels, dict) or not channels:
        raise ValueError("channels must be a non-empty mapping of channel name to error")
    limits = dict(DEFAULT_RELATIVE_LIMITS_PCT)
    if relative_limits is not None:
        if not isinstance(relative_limits, dict):
            raise ValueError("relative_limits must be a mapping")
        for name, limit in relative_limits.items():
            limits[name] = _positive("relative limit for '%s'" % name, limit)
    temp_limit = _positive("temperature_limit_k", temperature_limit_k)
    findings = []
    graded = {}
    for name, record in channels.items():
        if not isinstance(record, dict):
            raise ValueError("channel '%s' must be a mapping" % name)
        if "absolute_k" in record:
            error = _non_negative("channel '%s' absolute_k" % name, record["absolute_k"])
            within = error < temp_limit or math.isclose(
                error, temp_limit, rel_tol=0.0, abs_tol=BUDGET_TOLERANCE
            )
            graded[name] = {"error": error, "limit": temp_limit, "unit": "K", "within": within}
            if not within:
                findings.append(
                    "channel '%s' is %.3f K out against a %.3f K limit" % (name, error, temp_limit)
                )
            continue
        if "relative_pct" not in record:
            raise ValueError("channel '%s' needs 'relative_pct' or 'absolute_k'" % name)
        error = _non_negative("channel '%s' relative_pct" % name, record["relative_pct"])
        if name not in limits:
            raise ValueError("no accuracy limit declared for channel '%s'" % name)
        limit = limits[name]
        within = error < limit or math.isclose(
            error, limit, rel_tol=0.0, abs_tol=BUDGET_TOLERANCE
        )
        graded[name] = {"error": error, "limit": limit, "unit": "%", "within": within}
        if not within:
            findings.append(
                "channel '%s' is %.3f%% out against a %.3f%% limit" % (name, error, limit)
            )
    return {"graded": graded, "findings": findings}


def dominant_contributor(contributions):
    """Return the name of the largest contribution in a budget."""
    if not isinstance(contributions, dict) or not contributions:
        raise ValueError("contributions must be a non-empty mapping of name to magnitude")
    best_name = None
    best_value = -1.0
    for name in sorted(contributions):
        value = _non_negative("contribution '%s'" % name, contributions[name])
        if value > best_value:
            best_name = name
            best_value = value
    return best_name


def assess_measurement_accuracy(spec):
    """Run the whole measurement-accuracy assessment for one reported property.

    spec keys: channels, property (one of 'stress' or 'modulus'),
    target_expanded_pct, and optionally relative_limits, temperature_limit_k,
    coverage_factor, resolution_contributions (mapping name to a resolution in
    the same relative percent), drift_half_widths (same shape).
    """
    if not isinstance(spec, dict):
        raise ValueError("spec must be a mapping")
    for key in ("channels", "property", "target_expanded_pct"):
        if key not in spec:
            raise ValueError("spec missing required key '%s'" % key)
    prop = spec["property"]
    if prop not in ("stress", "modulus"):
        raise ValueError("property must be 'stress' or 'modulus', got %r" % (prop,))
    target = _positive("target_expanded_pct", spec["target_expanded_pct"])

    graded = channel_findings(
        spec["channels"],
        spec.get("relative_limits"),
        spec.get("temperature_limit_k", DEFAULT_TEMPERATURE_LIMIT_K),
    )
    findings = list(graded["findings"])

    def _channel(name):
        record = graded["graded"].get(name)
        if record is None:
            raise ValueError("property '%s' needs a '%s' channel" % (prop, name))
        if record["unit"] != "%":
            raise ValueError("channel '%s' must carry a relative error" % name)
        return record["error"]

    if prop == "stress":
        contributions = {
            "force": _channel("force"),
            "area-from-diameter": area_relative_uncertainty_pct(_channel("diameter")),
        }
        combined = stress_relative_uncertainty_pct(_channel("force"), _channel("diameter"))
    else:
        contributions = {
            "force": _channel("force"),
            "strain": _channel("strain"),
            "gauge-length": _channel("gauge_length"),
            "area-from-diameter": area_relative_uncertainty_pct(_channel("diameter")),
        }
        combined = modulus_relative_uncertainty_pct(
            _channel("force"),
            _channel("strain"),
            _channel("gauge_length"),
            _channel("diameter"),
        )

    extra = []
    for name, step in (spec.get("resolution_contributions") or {}).items():
        value = resolution_standard_uncertainty(step)
        contributions["resolution:" + str(name)] = value
        extra.append(value)
    for name, half_width in (spec.get("drift_half_widths") or {}).items():
        value = rectangular_standard_uncertainty(half_width)
        contributions["drift:" + str(name)] = value
        extra.append(value)
    if extra:
        combined = combine_in_quadrature([combined] + extra)

    k = spec.get("coverage_factor", DEFAULT_COVERAGE_FACTOR)
    expanded = expanded_uncertainty(combined, k)
    supported = expanded < target or math.isclose(
        expanded, target, rel_tol=0.0, abs_tol=BUDGET_TOLERANCE
    )
    if not supported:
        findings.append(
            "expanded relative uncertainty %.4f%% on the %s exceeds the %.4f%% target"
            % (expanded, prop, target)
        )
    return {
        "graded_channels": graded["graded"],
        "contributions": contributions,
        "dominant": dominant_contributor(contributions),
        "combined_standard_pct": combined,
        "coverage_factor": float(k),
        "expanded_pct": expanded,
        "target_expanded_pct": target,
        "supported": supported and not graded["findings"],
        "findings": findings,
    }
