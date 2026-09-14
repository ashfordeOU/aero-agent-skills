"""Selection and procurement of a Class 1 microwave monolithic integrated circuit.

Anchor: ECSS-Q-ST-60-13C clause 4.6.5 (microwave monolithic circuits selected
and bought under the highest assurance class). Paraphrased into an
implementable procedure; no standard text is reproduced.

Procedure implemented here
--------------------------
1. Group the supplier line by its space-evaluation standing and decide which
   procurement route that standing leaves open.
2. Compute the channel temperature of the die from the mounting-base
   temperature, the dissipated power and the thermal resistance, and compare
   it with the channel-temperature ceiling of the die technology.
3. Convert the achieved channel temperature into a median life through an
   Arrhenius model referenced to the supplier's demonstrated life point.
4. Grade the wafer-lot process-control-monitor readings against their limits.
5. Grade the RF parameter drift measured across the life or burn-in step.
6. Return a buy-as-is / buy-with-upscreening / reject disposition with the
   findings that drove it.
"""

import math

__all__ = [
    "BOLTZMANN_EV_PER_K",
    "TEMPERATURE_TOLERANCE_C",
    "CHANNEL_TEMPERATURE_LIMIT_C",
    "LINE_STANDING",
    "technology_channel_limit_c",
    "channel_temperature_c",
    "channel_temperature_margin_c",
    "median_life_hours",
    "pcm_lot_acceptance",
    "rf_drift_fraction",
    "procurement_route",
    "assess_mmic_procurement",
]

BOLTZMANN_EV_PER_K = 8.617333262e-5

# A channel-temperature margin is a difference of derived floats: an exactly
# satisfied ceiling can land a few ULPs on the wrong side. Absorb the
# representation error here instead of relaxing the derating ceiling.
TEMPERATURE_TOLERANCE_C = 1e-9

ABSOLUTE_ZERO_C = -273.15

# Channel-temperature ceilings applied to the die technology at the highest
# assurance class, in degrees celsius.
CHANNEL_TEMPERATURE_LIMIT_C = {
    "gaas-mesfet": 110.0,
    "gaas-phemt": 110.0,
    "gaas-hbt": 125.0,
    "inp-hemt": 110.0,
    "sige-hbt": 125.0,
    "gan-hemt": 160.0,
}

# How far each supplier line has been taken through space evaluation, and
# whether that standing on its own supports a direct purchase.
LINE_STANDING = {
    "space-qualified-line": True,
    "space-evaluated-line": True,
    "commercial-line": False,
}


def _real(value, label, positive=True, allow_zero=False):
    """Return value as a validated finite float."""
    if not isinstance(value, (int, float)) or isinstance(value, bool):
        raise ValueError("%s must be a real number, got %r" % (label, value))
    out = float(value)
    if not math.isfinite(out):
        raise ValueError("%s must be finite, got %r" % (label, value))
    if positive:
        if allow_zero:
            if out < 0.0:
                raise ValueError("%s must be non-negative, got %g" % (label, out))
        elif out <= 0.0:
            raise ValueError("%s must be positive, got %g" % (label, out))
    return out


def _kelvin(temp_c, label):
    """Return an absolute temperature in kelvin from a celsius input."""
    value = _real(temp_c, label, positive=False)
    if value <= ABSOLUTE_ZERO_C:
        raise ValueError("%s must be above absolute zero, got %g C" % (label, value))
    return value - ABSOLUTE_ZERO_C


def technology_channel_limit_c(technology):
    """Return the channel-temperature ceiling of a die technology."""
    if not isinstance(technology, str) or not technology.strip():
        raise ValueError("technology must be a non-empty string")
    key = technology.strip().lower()
    if key not in CHANNEL_TEMPERATURE_LIMIT_C:
        raise ValueError(
            "unknown die technology '%s'; expected one of %s"
            % (technology, ", ".join(sorted(CHANNEL_TEMPERATURE_LIMIT_C)))
        )
    return CHANNEL_TEMPERATURE_LIMIT_C[key]


def channel_temperature_c(base_temperature_c, dissipated_power_w,
                          thermal_resistance_c_per_w):
    """Return the channel temperature of the die in degrees celsius."""
    base = _real(base_temperature_c, "base_temperature_c", positive=False)
    if base <= ABSOLUTE_ZERO_C:
        raise ValueError("base_temperature_c must be above absolute zero")
    power = _real(dissipated_power_w, "dissipated_power_w", allow_zero=True)
    resistance = _real(thermal_resistance_c_per_w, "thermal_resistance_c_per_w",
                       allow_zero=True)
    return base + power * resistance


def channel_temperature_margin_c(technology, channel_temp_c):
    """Return the margin left to the ceiling and whether the die stays inside it."""
    limit = technology_channel_limit_c(technology)
    achieved = _real(channel_temp_c, "channel_temp_c", positive=False)
    if achieved <= ABSOLUTE_ZERO_C:
        raise ValueError("channel_temp_c must be above absolute zero")
    margin = limit - achieved
    return {
        "technology": technology.strip().lower(),
        "limit_c": limit,
        "channel_temp_c": achieved,
        "margin_c": margin,
        "within_limit": margin >= -TEMPERATURE_TOLERANCE_C,
    }


def median_life_hours(reference_life_hours, reference_channel_temp_c,
                      channel_temp_c, activation_energy_ev):
    """Return the median life at the achieved channel temperature."""
    reference = _real(reference_life_hours, "reference_life_hours")
    energy = _real(activation_energy_ev, "activation_energy_ev")
    t_ref = _kelvin(reference_channel_temp_c, "reference_channel_temp_c")
    t_use = _kelvin(channel_temp_c, "channel_temp_c")
    exponent = (energy / BOLTZMANN_EV_PER_K) * (1.0 / t_use - 1.0 / t_ref)
    return reference * math.exp(exponent)


def pcm_lot_acceptance(measurements, limits):
    """Grade wafer-lot process-control-monitor readings against their limits."""
    if not isinstance(measurements, dict) or not measurements:
        raise ValueError("measurements must be a non-empty mapping")
    if not isinstance(limits, dict) or not limits:
        raise ValueError("limits must be a non-empty mapping")
    out_of_limit = []
    graded = {}
    for name in sorted(measurements):
        if name not in limits:
            raise ValueError("no limit pair supplied for parameter '%s'" % name)
        value = _real(measurements[name], "measurement '%s'" % name, positive=False)
        bounds = limits[name]
        if not isinstance(bounds, (list, tuple)) or len(bounds) != 2:
            raise ValueError("limit for '%s' must be a (low, high) pair" % name)
        low = _real(bounds[0], "lower limit of '%s'" % name, positive=False)
        high = _real(bounds[1], "upper limit of '%s'" % name, positive=False)
        if low > high:
            raise ValueError("limits for '%s' are inverted (%g > %g)" % (name, low, high))
        inside = (value >= low - TEMPERATURE_TOLERANCE_C
                  and value <= high + TEMPERATURE_TOLERANCE_C)
        graded[name] = {"value": value, "low": low, "high": high, "inside": inside}
        if not inside:
            out_of_limit.append(name)
    return {
        "graded": graded,
        "out_of_limit": tuple(out_of_limit),
        "accepted": not out_of_limit,
    }


def rf_drift_fraction(initial_value, final_value):
    """Return the magnitude of the fractional drift of an RF parameter."""
    initial = _real(initial_value, "initial_value")
    final = _real(final_value, "final_value", positive=False)
    return abs(final - initial) / initial


def procurement_route(line_standing, has_lot_pcm_data, upscreening_available):
    """Group the supplier standing into the procurement route it leaves open."""
    if not isinstance(line_standing, str) or not line_standing.strip():
        raise ValueError("line_standing must be a non-empty string")
    key = line_standing.strip().lower()
    if key not in LINE_STANDING:
        raise ValueError(
            "unknown line standing '%s'; expected one of %s"
            % (line_standing, ", ".join(sorted(LINE_STANDING)))
        )
    for label, flag in (("has_lot_pcm_data", has_lot_pcm_data),
                        ("upscreening_available", upscreening_available)):
        if not isinstance(flag, bool):
            raise ValueError("%s must be a boolean" % label)
    if not has_lot_pcm_data:
        return "reject"
    if LINE_STANDING[key]:
        return "buy-as-is"
    if upscreening_available:
        return "buy-with-upscreening"
    return "reject"


def assess_mmic_procurement(spec):
    """Run the full clause 4.6.5 selection-and-procurement assessment.

    spec keys: technology, line_standing, has_lot_pcm_data, upscreening_available,
    base_temperature_c, dissipated_power_w, thermal_resistance_c_per_w,
    reference_life_hours, reference_channel_temp_c, activation_energy_ev,
    required_life_hours, pcm_measurements, pcm_limits, rf_initial, rf_final,
    allowed_rf_drift_fraction.
    """
    if not isinstance(spec, dict):
        raise ValueError("spec must be a mapping")
    required = (
        "technology",
        "line_standing",
        "has_lot_pcm_data",
        "upscreening_available",
        "base_temperature_c",
        "dissipated_power_w",
        "thermal_resistance_c_per_w",
        "reference_life_hours",
        "reference_channel_temp_c",
        "activation_energy_ev",
        "required_life_hours",
        "pcm_measurements",
        "pcm_limits",
        "rf_initial",
        "rf_final",
        "allowed_rf_drift_fraction",
    )
    for key in required:
        if key not in spec:
            raise ValueError("spec missing required key '%s'" % key)

    route = procurement_route(
        spec["line_standing"],
        spec["has_lot_pcm_data"],
        spec["upscreening_available"],
    )
    channel = channel_temperature_c(
        spec["base_temperature_c"],
        spec["dissipated_power_w"],
        spec["thermal_resistance_c_per_w"],
    )
    thermal = channel_temperature_margin_c(spec["technology"], channel)
    life = median_life_hours(
        spec["reference_life_hours"],
        spec["reference_channel_temp_c"],
        channel,
        spec["activation_energy_ev"],
    )
    required_life = _real(spec["required_life_hours"], "required_life_hours")
    pcm = pcm_lot_acceptance(spec["pcm_measurements"], spec["pcm_limits"])
    drift = rf_drift_fraction(spec["rf_initial"], spec["rf_final"])
    allowed_drift = _real(spec["allowed_rf_drift_fraction"],
                          "allowed_rf_drift_fraction", allow_zero=True)

    findings = []
    blocking = route == "reject"
    if blocking:
        findings.append(
            "supplier line '%s' does not support a Class 1 purchase on the evidence "
            "offered" % str(spec["line_standing"]).strip().lower()
        )

    if not thermal["within_limit"]:
        findings.append(
            "channel temperature %.3f C exceeds the %.1f C ceiling of %s by %.3f C"
            % (thermal["channel_temp_c"], thermal["limit_c"], thermal["technology"],
               -thermal["margin_c"])
        )
        blocking = True

    life_short = required_life - life
    if life_short > required_life * 1e-12:
        findings.append(
            "median life %.1f h at the achieved channel temperature is short of the "
            "required %.1f h" % (life, required_life)
        )
        blocking = True

    if not pcm["accepted"]:
        findings.append(
            "wafer-lot monitor readings outside limits: %s"
            % ", ".join(pcm["out_of_limit"])
        )
        blocking = True

    if drift - allowed_drift > 1e-12:
        findings.append(
            "RF parameter drift %.6f exceeds the allowed %.6f" % (drift, allowed_drift)
        )
        blocking = True

    if blocking:
        disposition = "reject"
    elif route == "buy-with-upscreening":
        disposition = "buy-with-upscreening"
        findings.append(
            "commercial line accepted only with the upscreening sequence applied"
        )
    else:
        disposition = "buy-as-is"

    return {
        "route": route,
        "thermal": thermal,
        "median_life_hours": life,
        "required_life_hours": required_life,
        "pcm": pcm,
        "rf_drift_fraction": drift,
        "allowed_rf_drift_fraction": allowed_drift,
        "disposition": disposition,
        "findings": findings,
    }
