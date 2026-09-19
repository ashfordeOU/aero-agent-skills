"""Heat pipe transport capability verification against temperature, bends and tilt.

Anchor: ECSS-E-ST-31-02C clause 5.5.5.2a (the performance verification a
constant-conductance heat pipe owes: transport capability as a function of
operating temperature, and the degradation that bending and adverse tilt
impose on it). Paraphrased into an implementable procedure; no standard text
is reproduced.

Procedure implemented here
--------------------------
1. Read the transport capability of the pipe at the operating temperature from
   its tabulated power-length curve, refusing to extrapolate off the ends.
2. Convert that power-length rating into a power at the pipe's own effective
   transport length.
3. Subtract the capability the adverse evaporator elevation consumes, through
   the tilt sensitivity of the wick, and report exhaustion rather than a
   negative capability.
4. Apply the knockdown each bend costs, scaled by how close the bend radius
   sits to the qualified minimum, and refuse a bend tighter than that minimum.
5. Compare the surviving capability with the required transport at every
   declared operating point and retain the worst one.
"""

import math

__all__ = [
    "MARGIN_TOLERANCE",
    "validate_curve",
    "interpolate_curve",
    "capability_at_temperature",
    "power_from_power_length",
    "tilt_penalty_w",
    "bend_knockdown_factor",
    "predicted_capability_w",
    "capability_margin",
    "assess_heat_pipe_performance",
]

# Required transport and predicted capability are frequently specified to land
# on each other exactly. Absorb only the representation error of the ratio.
MARGIN_TOLERANCE = 1e-9


def _real(value, label, positive=True):
    if not isinstance(value, (int, float)) or isinstance(value, bool):
        raise ValueError("%s must be a real number, got %r" % (label, value))
    out = float(value)
    if not math.isfinite(out):
        raise ValueError("%s must be finite, got %r" % (label, value))
    if positive and out <= 0.0:
        raise ValueError("%s must be positive, got %g" % (label, out))
    return out


def validate_curve(curve, name="capability curve"):
    """Return validated (temperature_c, capability) points, increasing in temperature.

    Temperatures may be negative; the capability ordinate may not, and a zero
    ordinate is the legitimate statement that the pipe does not work there.
    """
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
            raise ValueError(
                "%s temperatures must strictly increase (index %d)" % (name, index)
            )
    return points


def interpolate_curve(curve, temperature_c, name="capability curve"):
    """Linearly interpolate a capability curve; refuse to extrapolate."""
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


def capability_at_temperature(curve, temperature_c):
    """Return the power-length transport rating (W*m) at an operating temperature."""
    return interpolate_curve(curve, temperature_c, name="transport capability curve")


def power_from_power_length(rating_wm, effective_length_m):
    """Convert a power-length rating into a transportable power at a length."""
    rating = _real(rating_wm, "rating_wm", positive=False)
    if rating < 0.0:
        raise ValueError("rating_wm must not be negative, got %g" % rating)
    length = _real(effective_length_m, "effective_length_m")
    return rating / length


def tilt_penalty_w(tilt_sensitivity_w_per_mm, adverse_elevation_mm):
    """Return the capability the adverse evaporator elevation consumes, in watts.

    A negative elevation is a gravity-aided orientation. It is not credited
    here: the qualified capability is the one the pipe shows against gravity,
    so a favourable tilt contributes a zero penalty, not a bonus.
    """
    sensitivity = _real(tilt_sensitivity_w_per_mm, "tilt_sensitivity_w_per_mm", positive=False)
    if sensitivity < 0.0:
        raise ValueError(
            "tilt_sensitivity_w_per_mm must not be negative, got %g" % sensitivity
        )
    elevation = _real(adverse_elevation_mm, "adverse_elevation_mm", positive=False)
    if elevation <= 0.0:
        return 0.0
    return sensitivity * elevation


def bend_knockdown_factor(bend_count, bend_radius_mm, minimum_bend_radius_mm,
                          knockdown_per_bend):
    """Return the multiplicative capability factor a bend set imposes.

    The per-bend loss is scaled by how close the bend sits to the qualified
    minimum radius: a bend at the minimum costs the full declared knockdown,
    a generous radius costs proportionally less.
    """
    if not isinstance(bend_count, int) or isinstance(bend_count, bool):
        raise ValueError("bend_count must be an integer, got %r" % (bend_count,))
    if bend_count < 0:
        raise ValueError("bend_count must not be negative, got %d" % bend_count)
    minimum = _real(minimum_bend_radius_mm, "minimum_bend_radius_mm")
    knockdown = _real(knockdown_per_bend, "knockdown_per_bend", positive=False)
    if knockdown < 0.0 or knockdown >= 1.0:
        raise ValueError(
            "knockdown_per_bend must sit in [0, 1), got %g" % knockdown
        )
    if bend_count == 0:
        return 1.0
    radius = _real(bend_radius_mm, "bend_radius_mm")
    if radius < minimum and not math.isclose(radius, minimum, rel_tol=1e-12, abs_tol=0.0):
        raise ValueError(
            "bend radius %g mm is tighter than the qualified minimum %g mm"
            % (radius, minimum)
        )
    per_bend = knockdown * (minimum / radius)
    factor = 1.0
    for _ in range(bend_count):
        factor *= 1.0 - per_bend
    return factor


def predicted_capability_w(spec, temperature_c, adverse_elevation_mm):
    """Return the capability record of the pipe at one operating point."""
    if not isinstance(spec, dict):
        raise ValueError("spec must be a mapping")
    for key in ("capability_curve", "effective_length_m", "tilt_sensitivity_w_per_mm"):
        if key not in spec:
            raise ValueError("spec missing required key '%s'" % key)
    rating = capability_at_temperature(spec["capability_curve"], temperature_c)
    base = power_from_power_length(rating, spec["effective_length_m"])
    penalty = tilt_penalty_w(spec["tilt_sensitivity_w_per_mm"], adverse_elevation_mm)
    after_tilt = base - penalty
    exhausted = after_tilt <= 0.0
    if exhausted:
        after_tilt = 0.0
    factor = bend_knockdown_factor(
        spec.get("bend_count", 0),
        spec.get("bend_radius_mm", spec.get("minimum_bend_radius_mm", 1.0)),
        spec.get("minimum_bend_radius_mm", 1.0),
        spec.get("knockdown_per_bend", 0.0),
    )
    return {
        "temperature_c": float(temperature_c),
        "adverse_elevation_mm": float(adverse_elevation_mm),
        "rating_wm": rating,
        "base_capability_w": base,
        "tilt_penalty_w": penalty,
        "bend_factor": factor,
        "capability_w": after_tilt * factor,
        "capillary_limit_exhausted": exhausted,
    }


def capability_margin(capability_w, required_w):
    """Return the capability-to-requirement ratio and the compliance verdict."""
    capability = _real(capability_w, "capability_w", positive=False)
    if capability < 0.0:
        raise ValueError("capability_w must not be negative, got %g" % capability)
    required = _real(required_w, "required_w")
    ratio = capability / required
    compliant = ratio > 1.0 or math.isclose(ratio, 1.0, rel_tol=MARGIN_TOLERANCE, abs_tol=0.0)
    return {"capability_w": capability, "required_w": required, "ratio": ratio,
            "compliant": compliant}


def assess_heat_pipe_performance(spec):
    """Run the full clause 5.5.5.2a heat pipe performance verification.

    spec keys: capability_curve, effective_length_m, tilt_sensitivity_w_per_mm,
    operating_points (sequence of {temperature_c, adverse_elevation_mm,
    required_w}), optional bend_count, bend_radius_mm, minimum_bend_radius_mm,
    knockdown_per_bend.
    """
    if not isinstance(spec, dict):
        raise ValueError("spec must be a mapping")
    points = spec.get("operating_points")
    if not isinstance(points, (list, tuple)) or not points:
        raise ValueError("spec['operating_points'] must be a non-empty sequence")
    records = []
    for index, point in enumerate(points):
        if not isinstance(point, dict):
            raise ValueError("operating_points[%d] must be a mapping" % index)
        for key in ("temperature_c", "adverse_elevation_mm", "required_w"):
            if key not in point:
                raise ValueError("operating_points[%d] missing '%s'" % (index, key))
        record = predicted_capability_w(
            spec, point["temperature_c"], point["adverse_elevation_mm"]
        )
        record.update(capability_margin(record["capability_w"], point["required_w"]))
        record["name"] = point.get("name", "point-%d" % index)
        records.append(record)
    worst = records[0]
    for record in records[1:]:
        if record["ratio"] < worst["ratio"] and not math.isclose(
            record["ratio"], worst["ratio"], rel_tol=1e-12, abs_tol=0.0
        ):
            worst = record
    findings = []
    for record in records:
        if record["capillary_limit_exhausted"]:
            findings.append(
                "operating point '%s' exhausts the capillary limit at %g mm adverse tilt"
                % (record["name"], record["adverse_elevation_mm"])
            )
        if not record["compliant"]:
            findings.append(
                "operating point '%s' carries %.4f of its required transport"
                % (record["name"], record["ratio"])
            )
    return {
        "records": records,
        "worst_point": worst,
        "findings": findings,
        "compliant": not findings,
    }
