"""Diode heat pipe verification: forward transport, reverse leak and mode switch.

Anchor: ECSS-E-ST-31-02C clause 5.5.5.2c (the performance verification a diode
heat pipe owes: transport capability in the forward direction, the heat that
still leaks in reverse mode, and the time and energy the switch between the
two modes costs). Paraphrased into an implementable procedure; no standard
text is reproduced.

Procedure implemented here
--------------------------
1. Read the forward transport capability at the operating temperature from the
   tabulated curve and grade it against the requirement.
2. Derive the forward and reverse conductances from measured heat and
   temperature difference, and reduce the pair to a diodicity ratio graded
   against the required ratio.
3. Grade the reverse-mode heat leak at the reverse temperature difference
   against the allowance the cold side can absorb.
4. Find the mode-switch time from the sampled reverse power transient: the
   instant after which the reverse power stays at or below the settled
   threshold, interpolated between the bracketing samples.
5. Integrate the sampled reverse power over the transient by the trapezoidal
   rule to get the switch energy, and grade it against the energy budget.
"""

import math

__all__ = [
    "RATIO_TOLERANCE",
    "validate_curve",
    "interpolate_curve",
    "forward_transport_check",
    "conductance_w_per_k",
    "diodicity_ratio",
    "reverse_heat_leak_w",
    "validate_transient",
    "mode_switch_time_s",
    "switch_energy_j",
    "assess_diode_heat_pipe",
]

# Ratios and budgets are specified to land exactly on their limits; absorb
# only the representation error of the comparison.
RATIO_TOLERANCE = 1e-9


def _real(value, label, positive=True):
    if not isinstance(value, (int, float)) or isinstance(value, bool):
        raise ValueError("%s must be a real number, got %r" % (label, value))
    out = float(value)
    if not math.isfinite(out):
        raise ValueError("%s must be finite, got %r" % (label, value))
    if positive and out <= 0.0:
        raise ValueError("%s must be positive, got %g" % (label, out))
    return out


def validate_curve(curve, name="forward transport curve"):
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


def interpolate_curve(curve, temperature_c, name="forward transport curve"):
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


def forward_transport_check(curve, temperature_c, required_w):
    """Grade the forward transport capability against the requirement."""
    capability = interpolate_curve(curve, temperature_c)
    required = _real(required_w, "required_w")
    ratio = capability / required
    compliant = ratio > 1.0 or math.isclose(ratio, 1.0, rel_tol=RATIO_TOLERANCE, abs_tol=0.0)
    return {
        "temperature_c": float(temperature_c),
        "capability_w": capability,
        "required_w": required,
        "ratio": ratio,
        "compliant": compliant,
    }


def conductance_w_per_k(heat_w, delta_t_k):
    """Return the end-to-end conductance implied by a heat flow and a rise."""
    heat = _real(heat_w, "heat_w", positive=False)
    if heat < 0.0:
        raise ValueError("heat_w must not be negative, got %g" % heat)
    delta = _real(delta_t_k, "delta_t_k")
    return heat / delta


def diodicity_ratio(forward_conductance, reverse_conductance, required_ratio):
    """Grade the ratio of forward to reverse conductance."""
    forward = _real(forward_conductance, "forward_conductance")
    reverse = _real(reverse_conductance, "reverse_conductance")
    required = _real(required_ratio, "required_ratio")
    if required < 1.0:
        raise ValueError("required_ratio must be at least 1.0, got %g" % required)
    ratio = forward / reverse
    compliant = ratio > required or math.isclose(
        ratio, required, rel_tol=RATIO_TOLERANCE, abs_tol=0.0
    )
    return {
        "forward_conductance": forward,
        "reverse_conductance": reverse,
        "ratio": ratio,
        "required_ratio": required,
        "compliant": compliant,
    }


def reverse_heat_leak_w(reverse_conductance, reverse_delta_t_k, allowed_w):
    """Grade the heat a reversed diode heat pipe still passes backwards."""
    conductance = _real(reverse_conductance, "reverse_conductance", positive=False)
    if conductance < 0.0:
        raise ValueError("reverse_conductance must not be negative, got %g" % conductance)
    delta = _real(reverse_delta_t_k, "reverse_delta_t_k", positive=False)
    if delta < 0.0:
        raise ValueError("reverse_delta_t_k must not be negative, got %g" % delta)
    allowed = _real(allowed_w, "allowed_w")
    leak = conductance * delta
    compliant = leak < allowed or math.isclose(
        leak, allowed, rel_tol=RATIO_TOLERANCE, abs_tol=0.0
    )
    return {"leak_w": leak, "allowed_w": allowed, "compliant": compliant}


def validate_transient(samples):
    """Return validated (time_s, reverse_power_w) samples, increasing in time."""
    if not isinstance(samples, (list, tuple)) or len(samples) < 2:
        raise ValueError("samples must be a sequence of at least two (time_s, power_w) pairs")
    points = []
    for index, item in enumerate(samples):
        if not isinstance(item, (list, tuple)) or len(item) != 2:
            raise ValueError("samples[%d] must be a (time_s, power_w) pair" % index)
        time_s = _real(item[0], "samples[%d] time_s" % index, positive=False)
        power = _real(item[1], "samples[%d] power_w" % index, positive=False)
        if time_s < 0.0:
            raise ValueError("samples[%d] time_s must not be negative, got %g" % (index, time_s))
        if power < 0.0:
            raise ValueError("samples[%d] power_w must not be negative, got %g" % (index, power))
        points.append((time_s, power))
    for index in range(1, len(points)):
        if points[index][0] <= points[index - 1][0]:
            raise ValueError("samples times must strictly increase (index %d)" % index)
    return points


def mode_switch_time_s(samples, settled_threshold_w):
    """Return the time at which the reverse power settles at or below the threshold.

    The switch is complete at the first crossing after which the transient
    never rises back above the threshold: an early dip that later recovers is
    not a completed switch.
    """
    points = validate_transient(samples)
    threshold = _real(settled_threshold_w, "settled_threshold_w", positive=False)
    if threshold < 0.0:
        raise ValueError("settled_threshold_w must not be negative, got %g" % threshold)
    settled_index = None
    for index in range(len(points)):
        if all(power <= threshold for _, power in points[index:]):
            settled_index = index
            break
    if settled_index is None:
        raise ValueError(
            "reverse power never settles at or below %g W within the sampled transient"
            % threshold
        )
    if settled_index == 0:
        return points[0][0]
    # The sample before the settled index is, by construction, the one that
    # kept the transient unsettled, so it sits strictly above the threshold
    # while the settled sample sits at or below it: the bracket is real and
    # the denominator cannot vanish.
    t0, p0 = points[settled_index - 1]
    t1, p1 = points[settled_index]
    fraction = (p0 - threshold) / (p0 - p1)
    return t0 + fraction * (t1 - t0)


def switch_energy_j(samples, until_time_s=None):
    """Integrate the sampled reverse power by the trapezoidal rule."""
    points = validate_transient(samples)
    if until_time_s is None:
        limit = points[-1][0]
    else:
        limit = _real(until_time_s, "until_time_s", positive=False)
        if limit < points[0][0]:
            raise ValueError(
                "until_time_s %g precedes the first sample at %g s" % (limit, points[0][0])
            )
        if limit > points[-1][0]:
            raise ValueError(
                "until_time_s %g runs past the last sample at %g s" % (limit, points[-1][0])
            )
    energy = 0.0
    for index in range(1, len(points)):
        t0, p0 = points[index - 1]
        t1, p1 = points[index]
        if t0 >= limit:
            break
        if t1 <= limit:
            energy += 0.5 * (p0 + p1) * (t1 - t0)
        else:
            fraction = (limit - t0) / (t1 - t0)
            p_mid = p0 + fraction * (p1 - p0)
            energy += 0.5 * (p0 + p_mid) * (limit - t0)
            break
    return energy


def assess_diode_heat_pipe(spec):
    """Run the full clause 5.5.5.2c diode heat pipe verification.

    spec keys: forward_curve, operating_temperature_c, required_forward_w,
    forward_heat_w, forward_delta_t_k, reverse_heat_w, reverse_delta_t_k,
    required_diodicity, reverse_service_delta_t_k, allowed_reverse_leak_w,
    transient_samples, settled_threshold_w, allowed_switch_time_s,
    allowed_switch_energy_j.
    """
    if not isinstance(spec, dict):
        raise ValueError("spec must be a mapping")
    required_keys = (
        "forward_curve",
        "operating_temperature_c",
        "required_forward_w",
        "forward_heat_w",
        "forward_delta_t_k",
        "reverse_heat_w",
        "reverse_delta_t_k",
        "required_diodicity",
        "reverse_service_delta_t_k",
        "allowed_reverse_leak_w",
        "transient_samples",
        "settled_threshold_w",
        "allowed_switch_time_s",
        "allowed_switch_energy_j",
    )
    for key in required_keys:
        if key not in spec:
            raise ValueError("spec missing required key '%s'" % key)
    forward = forward_transport_check(
        spec["forward_curve"], spec["operating_temperature_c"], spec["required_forward_w"]
    )
    forward_g = conductance_w_per_k(spec["forward_heat_w"], spec["forward_delta_t_k"])
    reverse_g = conductance_w_per_k(spec["reverse_heat_w"], spec["reverse_delta_t_k"])
    diodicity = diodicity_ratio(forward_g, reverse_g, spec["required_diodicity"])
    leak = reverse_heat_leak_w(
        reverse_g, spec["reverse_service_delta_t_k"], spec["allowed_reverse_leak_w"]
    )
    switch_time = mode_switch_time_s(spec["transient_samples"], spec["settled_threshold_w"])
    allowed_time = _real(spec["allowed_switch_time_s"], "allowed_switch_time_s")
    time_ok = switch_time < allowed_time or math.isclose(
        switch_time, allowed_time, rel_tol=RATIO_TOLERANCE, abs_tol=0.0
    )
    energy = switch_energy_j(spec["transient_samples"], switch_time)
    allowed_energy = _real(spec["allowed_switch_energy_j"], "allowed_switch_energy_j")
    energy_ok = energy < allowed_energy or math.isclose(
        energy, allowed_energy, rel_tol=RATIO_TOLERANCE, abs_tol=0.0
    )
    findings = []
    if not forward["compliant"]:
        findings.append(
            "forward transport carries %.4f of the requirement at %g degC"
            % (forward["ratio"], forward["temperature_c"])
        )
    if not diodicity["compliant"]:
        findings.append(
            "diodicity ratio %.4f falls short of the required %.4f"
            % (diodicity["ratio"], diodicity["required_ratio"])
        )
    if not leak["compliant"]:
        findings.append(
            "reverse-mode heat leak %.4f W exceeds the allowed %.4f W"
            % (leak["leak_w"], leak["allowed_w"])
        )
    if not time_ok:
        findings.append(
            "mode switch takes %.4f s against an allowed %.4f s" % (switch_time, allowed_time)
        )
    if not energy_ok:
        findings.append(
            "mode switch leaks %.4f J against an allowed %.4f J" % (energy, allowed_energy)
        )
    return {
        "forward": forward,
        "forward_conductance": forward_g,
        "reverse_conductance": reverse_g,
        "diodicity": diodicity,
        "reverse_leak": leak,
        "switch_time_s": switch_time,
        "allowed_switch_time_s": allowed_time,
        "switch_time_compliant": time_ok,
        "switch_energy_j": energy,
        "allowed_switch_energy_j": allowed_energy,
        "switch_energy_compliant": energy_ok,
        "findings": findings,
        "compliant": not findings,
    }
