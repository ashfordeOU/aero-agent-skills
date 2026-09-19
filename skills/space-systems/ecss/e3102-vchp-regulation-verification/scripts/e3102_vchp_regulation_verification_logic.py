"""Variable conductance heat pipe regulation verification.

Anchor: ECSS-E-ST-31-02C clause 5.5.5.2b (the performance verification a
variable conductance heat pipe owes: maximum transport capability, off-mode
heat leak with the condenser blocked, reservoir thermal resistance, and the
passive or active regulation of the evaporator temperature). Paraphrased into
an implementable procedure; no standard text is reproduced.

Procedure implemented here
--------------------------
1. Read the maximum transport capability at the design temperature from the
   tabulated curve and grade it against the requirement.
2. Bound the off-mode heat leak: with the non-condensable gas front pushed
   over the full condenser, what still crosses is axial conduction through the
   envelope and wick, which is a conductance times a temperature difference.
3. Derive the reservoir thermal resistance from the measured rise the
   reservoir shows for a known parasitic heat input, and grade it against the
   specified maximum -- a reservoir loosely tied to its control temperature
   cannot hold the gas front where the control law wants it.
4. Reduce the recorded operating points to the evaporator temperature swing
   and grade it against the control band, naming the two points that produced
   it.
5. For an actively controlled reservoir, size the heater power the setpoint
   demands at the coldest sink and grade it against the available budget; a
   passive unit must meet the band with no heater power at all.
6. Estimate the condenser blockage fraction at the lowest power point and
   grade it against the blockage the reservoir was sized for.
"""

import math

__all__ = [
    "BAND_TOLERANCE",
    "REGULATION_MODES",
    "validate_curve",
    "interpolate_curve",
    "maximum_transport_check",
    "axial_conductance_w_per_k",
    "off_mode_heat_leak_w",
    "reservoir_resistance_k_per_w",
    "regulation_swing",
    "active_reservoir_heater_w",
    "condenser_blockage_fraction",
    "assess_vchp_regulation",
]

# Bands, resistances and powers are specified to land exactly on their limits.
# Absorb only the representation error of the comparison.
BAND_TOLERANCE = 1e-9

REGULATION_MODES = ("passive", "active")


def _real(value, label, positive=True):
    if not isinstance(value, (int, float)) or isinstance(value, bool):
        raise ValueError("%s must be a real number, got %r" % (label, value))
    out = float(value)
    if not math.isfinite(out):
        raise ValueError("%s must be finite, got %r" % (label, value))
    if positive and out <= 0.0:
        raise ValueError("%s must be positive, got %g" % (label, out))
    return out


def validate_curve(curve, name="transport curve"):
    """Return validated (temperature_c, value) points, increasing in temperature."""
    if not isinstance(curve, (list, tuple)) or len(curve) < 2:
        raise ValueError("%s needs at least two (temperature_c, value) points" % name)
    points = []
    for index, item in enumerate(curve):
        if not isinstance(item, (list, tuple)) or len(item) != 2:
            raise ValueError("%s[%d] must be a (temperature_c, value) pair" % (name, index))
        temp = _real(item[0], "%s[%d] temperature_c" % (name, index), positive=False)
        value = _real(item[1], "%s[%d] value" % (name, index), positive=False)
        if value < 0.0:
            raise ValueError("%s[%d] value must not be negative, got %g" % (name, index, value))
        points.append((temp, value))
    for index in range(1, len(points)):
        if points[index][0] <= points[index - 1][0]:
            raise ValueError("%s temperatures must strictly increase (index %d)" % (name, index))
    return points


def interpolate_curve(curve, temperature_c, name="transport curve"):
    """Linearly interpolate a curve at a temperature; refuse to extrapolate."""
    points = validate_curve(curve, name)
    temp = _real(temperature_c, "temperature_c", positive=False)
    low, high = points[0][0], points[-1][0]
    if temp < low or temp > high:
        raise ValueError(
            "%s is tabulated over [%g, %g] degC; %g is outside it, extrapolation refused"
            % (name, low, high, temp)
        )
    for index in range(1, len(points)):
        x0, y0 = points[index - 1]
        x1, y1 = points[index]
        if temp <= x1:
            if temp == x0:
                return y0
            if temp == x1:
                return y1
            fraction = (temp - x0) / (x1 - x0)
            return y0 + fraction * (y1 - y0)
    return points[-1][1]


def maximum_transport_check(curve, design_temperature_c, required_w):
    """Grade the maximum transport capability at the design temperature."""
    capability = interpolate_curve(curve, design_temperature_c, name="vchp transport curve")
    required = _real(required_w, "required_w")
    ratio = capability / required
    compliant = ratio > 1.0 or math.isclose(ratio, 1.0, rel_tol=BAND_TOLERANCE, abs_tol=0.0)
    return {
        "design_temperature_c": float(design_temperature_c),
        "capability_w": capability,
        "required_w": required,
        "ratio": ratio,
        "compliant": compliant,
    }


def axial_conductance_w_per_k(conductivity_w_per_m_k, cross_section_m2, length_m):
    """Return the axial conduction conductance of the envelope and wick path."""
    k = _real(conductivity_w_per_m_k, "conductivity_w_per_m_k")
    area = _real(cross_section_m2, "cross_section_m2")
    length = _real(length_m, "length_m")
    return k * area / length


def off_mode_heat_leak_w(conductance_w_per_k, delta_t_k, allowed_w):
    """Grade the heat that still crosses a fully blocked condenser."""
    conductance = _real(conductance_w_per_k, "conductance_w_per_k", positive=False)
    if conductance < 0.0:
        raise ValueError("conductance_w_per_k must not be negative, got %g" % conductance)
    delta = _real(delta_t_k, "delta_t_k", positive=False)
    if delta < 0.0:
        raise ValueError("delta_t_k must not be negative, got %g" % delta)
    allowed = _real(allowed_w, "allowed_w")
    leak = conductance * delta
    compliant = leak < allowed or math.isclose(
        leak, allowed, rel_tol=BAND_TOLERANCE, abs_tol=0.0
    )
    return {"leak_w": leak, "allowed_w": allowed, "compliant": compliant}


def reservoir_resistance_k_per_w(delta_t_k, heat_w, maximum_k_per_w):
    """Derive the reservoir thermal resistance and grade it against its limit."""
    delta = _real(delta_t_k, "delta_t_k", positive=False)
    if delta < 0.0:
        raise ValueError("delta_t_k must not be negative, got %g" % delta)
    heat = _real(heat_w, "heat_w")
    maximum = _real(maximum_k_per_w, "maximum_k_per_w")
    resistance = delta / heat
    compliant = resistance < maximum or math.isclose(
        resistance, maximum, rel_tol=BAND_TOLERANCE, abs_tol=0.0
    )
    return {
        "resistance_k_per_w": resistance,
        "maximum_k_per_w": maximum,
        "compliant": compliant,
    }


def regulation_swing(points, band_k):
    """Return the evaporator temperature swing across the recorded points."""
    if not isinstance(points, (list, tuple)) or len(points) < 2:
        raise ValueError("points must be a sequence of at least two operating points")
    band = _real(band_k, "band_k", positive=False)
    if band < 0.0:
        raise ValueError("band_k must not be negative, got %g" % band)
    records = []
    for index, point in enumerate(points):
        if not isinstance(point, dict):
            raise ValueError("points[%d] must be a mapping" % index)
        for key in ("power_w", "sink_c", "evaporator_c"):
            if key not in point:
                raise ValueError("points[%d] missing '%s'" % (index, key))
        records.append(
            {
                "name": point.get("name", "point-%d" % index),
                "power_w": _real(point["power_w"], "points[%d] power_w" % index,
                                 positive=False),
                "sink_c": _real(point["sink_c"], "points[%d] sink_c" % index, positive=False),
                "evaporator_c": _real(
                    point["evaporator_c"], "points[%d] evaporator_c" % index, positive=False
                ),
            }
        )
    coldest = min(records, key=lambda r: r["evaporator_c"])
    hottest = max(records, key=lambda r: r["evaporator_c"])
    swing = hottest["evaporator_c"] - coldest["evaporator_c"]
    compliant = swing < band or math.isclose(swing, band, rel_tol=0.0, abs_tol=BAND_TOLERANCE)
    return {
        "swing_k": swing,
        "band_k": band,
        "coldest_point": coldest,
        "hottest_point": hottest,
        "compliant": compliant,
    }


def active_reservoir_heater_w(reservoir_conductance_w_per_k, setpoint_c, coldest_sink_c,
                              available_heater_w):
    """Size the reservoir heater an actively controlled unit demands."""
    conductance = _real(
        reservoir_conductance_w_per_k, "reservoir_conductance_w_per_k", positive=False
    )
    if conductance < 0.0:
        raise ValueError(
            "reservoir_conductance_w_per_k must not be negative, got %g" % conductance
        )
    setpoint = _real(setpoint_c, "setpoint_c", positive=False)
    sink = _real(coldest_sink_c, "coldest_sink_c", positive=False)
    available = _real(available_heater_w, "available_heater_w", positive=False)
    if available < 0.0:
        raise ValueError("available_heater_w must not be negative, got %g" % available)
    demand = conductance * (setpoint - sink)
    if demand < 0.0:
        demand = 0.0
    compliant = demand < available or math.isclose(
        demand, available, rel_tol=BAND_TOLERANCE, abs_tol=0.0
    )
    return {"demand_w": demand, "available_w": available, "compliant": compliant}


def condenser_blockage_fraction(power_w, full_power_w, maximum_blockage):
    """Return the condenser fraction the gas front blocks at a reduced power."""
    power = _real(power_w, "power_w", positive=False)
    if power < 0.0:
        raise ValueError("power_w must not be negative, got %g" % power)
    full = _real(full_power_w, "full_power_w")
    if power > full:
        raise ValueError(
            "power_w %g exceeds the full-power reference %g" % (power, full)
        )
    maximum = _real(maximum_blockage, "maximum_blockage", positive=False)
    if maximum < 0.0 or maximum > 1.0:
        raise ValueError("maximum_blockage must sit in [0, 1], got %g" % maximum)
    fraction = 1.0 - power / full
    compliant = fraction < maximum or math.isclose(
        fraction, maximum, rel_tol=0.0, abs_tol=BAND_TOLERANCE
    )
    return {
        "blockage_fraction": fraction,
        "maximum_blockage": maximum,
        "compliant": compliant,
    }


def assess_vchp_regulation(spec):
    """Run the full clause 5.5.5.2b variable conductance heat pipe verification.

    spec keys: transport_curve, design_temperature_c, required_transport_w,
    off_mode_conductance_w_per_k, off_mode_delta_t_k, allowed_off_mode_leak_w,
    reservoir_delta_t_k, reservoir_heat_w, maximum_reservoir_resistance_k_per_w,
    operating_points, control_band_k, regulation_mode, and for an active mode
    reservoir_conductance_w_per_k, reservoir_setpoint_c, available_heater_w.
    Optional: full_power_w and maximum_blockage for the reservoir sizing check.
    """
    if not isinstance(spec, dict):
        raise ValueError("spec must be a mapping")
    required_keys = (
        "transport_curve",
        "design_temperature_c",
        "required_transport_w",
        "off_mode_conductance_w_per_k",
        "off_mode_delta_t_k",
        "allowed_off_mode_leak_w",
        "reservoir_delta_t_k",
        "reservoir_heat_w",
        "maximum_reservoir_resistance_k_per_w",
        "operating_points",
        "control_band_k",
        "regulation_mode",
    )
    for key in required_keys:
        if key not in spec:
            raise ValueError("spec missing required key '%s'" % key)
    mode = spec["regulation_mode"]
    if not isinstance(mode, str) or mode.strip().lower() not in REGULATION_MODES:
        raise ValueError(
            "regulation_mode must be one of %s, got %r" % (", ".join(REGULATION_MODES), mode)
        )
    mode = mode.strip().lower()
    transport = maximum_transport_check(
        spec["transport_curve"], spec["design_temperature_c"], spec["required_transport_w"]
    )
    off_mode = off_mode_heat_leak_w(
        spec["off_mode_conductance_w_per_k"],
        spec["off_mode_delta_t_k"],
        spec["allowed_off_mode_leak_w"],
    )
    reservoir = reservoir_resistance_k_per_w(
        spec["reservoir_delta_t_k"],
        spec["reservoir_heat_w"],
        spec["maximum_reservoir_resistance_k_per_w"],
    )
    swing = regulation_swing(spec["operating_points"], spec["control_band_k"])
    findings = []
    if not transport["compliant"]:
        findings.append(
            "maximum transport at %g degC carries %.4f of the requirement"
            % (transport["design_temperature_c"], transport["ratio"])
        )
    if not off_mode["compliant"]:
        findings.append(
            "off-mode heat leak %.4f W exceeds the allowed %.4f W"
            % (off_mode["leak_w"], off_mode["allowed_w"])
        )
    if not reservoir["compliant"]:
        findings.append(
            "reservoir resistance %.4f K/W exceeds the maximum %.4f K/W"
            % (reservoir["resistance_k_per_w"], reservoir["maximum_k_per_w"])
        )
    if not swing["compliant"]:
        findings.append(
            "evaporator swing %.4f K between '%s' and '%s' exceeds the %.4f K band"
            % (
                swing["swing_k"],
                swing["coldest_point"]["name"],
                swing["hottest_point"]["name"],
                swing["band_k"],
            )
        )
    heater = None
    if mode == "active":
        for key in (
            "reservoir_conductance_w_per_k",
            "reservoir_setpoint_c",
            "available_heater_w",
        ):
            if key not in spec:
                raise ValueError("active regulation needs spec key '%s'" % key)
        coldest_sink = min(float(p["sink_c"]) for p in spec["operating_points"])
        heater = active_reservoir_heater_w(
            spec["reservoir_conductance_w_per_k"],
            spec["reservoir_setpoint_c"],
            coldest_sink,
            spec["available_heater_w"],
        )
        if not heater["compliant"]:
            findings.append(
                "reservoir heater demand %.4f W exceeds the available %.4f W"
                % (heater["demand_w"], heater["available_w"])
            )
    blockage = None
    if "full_power_w" in spec and "maximum_blockage" in spec:
        lowest = min(float(p["power_w"]) for p in spec["operating_points"])
        blockage = condenser_blockage_fraction(
            lowest, spec["full_power_w"], spec["maximum_blockage"]
        )
        if not blockage["compliant"]:
            findings.append(
                "condenser blockage %.4f at the lowest power exceeds the reservoir "
                "sizing limit %.4f"
                % (blockage["blockage_fraction"], blockage["maximum_blockage"])
            )
    return {
        "regulation_mode": mode,
        "transport": transport,
        "off_mode": off_mode,
        "reservoir": reservoir,
        "regulation": swing,
        "heater": heater,
        "blockage": blockage,
        "findings": findings,
        "compliant": not findings,
    }
