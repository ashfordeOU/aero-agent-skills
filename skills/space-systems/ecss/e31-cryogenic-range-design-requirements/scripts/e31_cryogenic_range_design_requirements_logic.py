"""Cryogenic-range design constraints for a thermal control item.

Anchor: ECSS-E-ST-31 clause 4.2.3 and its cryogenic annex -- the additional
constraints that apply once an item operates below the cryogenic range
boundary: temperature sensing that still resolves the cold end, control
hardware qualified that low, interface gradients held inside their allowable,
and material properties widened by the scatter they acquire in the cold.
Paraphrased into an implementable procedure; no standard text is reproduced.

Procedure implemented here
--------------------------
1. Admit only an item whose operating range reaches below the boundary.
2. Check sensor span coverage and cold-end sensitivity.
3. Grow a mechanical thermostat deadband below its qualification floor and
   compare it with the allowable control band.
4. Compare the interface gradient with its allowable.
5. Widen each material property into a scatter band.
6. Propagate the conductivity band into a conduction heat-leak band.
7. Size the cooler against the high end of that band.
"""

import math

__all__ = [
    "CRYOGENIC_UPPER_K",
    "TEMPERATURE_TOLERANCE_K",
    "RELATIVE_TOLERANCE",
    "CRYOGENIC_SCATTER_FACTOR",
    "DEADBAND_GROWTH_FACTOR",
    "CONTROL_ELECTRONIC",
    "CONTROL_MECHANICAL",
    "CONTROL_KINDS",
    "validate_operating_range",
    "assess_sensor",
    "assess_thermostat",
    "assess_gradient",
    "property_scatter_band",
    "conduction_heat_leak_band",
    "size_cooler",
    "assess_cryogenic_item",
]

CRYOGENIC_UPPER_K = 200.0

# Bands and margins are differences of products; absorb representation error
# at a boundary here rather than by relaxing a requirement.
TEMPERATURE_TOLERANCE_K = 1e-9
RELATIVE_TOLERANCE = 1e-12

# Property data below the boundary is measured on fewer samples and scatters
# more between lots, so the declared room-temperature scatter is multiplied by
# this factor before the band is built.
CRYOGENIC_SCATTER_FACTOR = 2.5

# A mechanical thermostat below its qualification floor stiffens and its
# deadband widens; this is the multiplier applied per kelvin of shortfall,
# capped by the growth cap so the model stays bounded.
DEADBAND_GROWTH_FACTOR = 0.05
DEADBAND_GROWTH_CAP = 6.0

CONTROL_MECHANICAL = "mechanical-thermostat"
CONTROL_ELECTRONIC = "electronic-controller"
CONTROL_KINDS = (CONTROL_MECHANICAL, CONTROL_ELECTRONIC)


def _real(label, value):
    """Return value as a finite float or raise ValueError."""
    if not isinstance(value, (int, float)) or isinstance(value, bool):
        raise ValueError("%s must be a real number, got %r" % (label, value))
    v = float(value)
    if not math.isfinite(v):
        raise ValueError("%s must be finite, got %r" % (label, value))
    return v


def _positive(label, value):
    v = _real(label, value)
    if v <= 0.0:
        raise ValueError("%s must be positive, got %r" % (label, value))
    return v


def _non_negative(label, value):
    v = _real(label, value)
    if v < 0.0:
        raise ValueError("%s must not be negative, got %r" % (label, value))
    return v


def validate_operating_range(minimum_k, maximum_k):
    """Return a validated operating range that reaches into the cryogenic range."""
    low = _positive("minimum_k", minimum_k)
    high = _positive("maximum_k", maximum_k)
    if high < low:
        raise ValueError("maximum_k %g must not be below minimum_k %g" % (high, low))
    if low >= CRYOGENIC_UPPER_K - TEMPERATURE_TOLERANCE_K:
        raise ValueError(
            "operating range [%g, %g] K never reaches below the cryogenic "
            "boundary %g K; the cryogenic constraints do not apply"
            % (low, high, CRYOGENIC_UPPER_K)
        )
    return {"minimum_k": low, "maximum_k": high}


def assess_sensor(sensor, operating_range):
    """Check a temperature sensor for span coverage and cold-end sensitivity."""
    if not isinstance(sensor, dict):
        raise ValueError("sensor must be a mapping")
    usable_min = _positive("sensor usable_min_k", sensor.get("usable_min_k"))
    usable_max = _positive("sensor usable_max_k", sensor.get("usable_max_k"))
    if usable_max <= usable_min:
        raise ValueError("sensor usable_max_k must be strictly above usable_min_k")
    margin = _non_negative("sensor required_margin_k", sensor.get("required_margin_k", 0.0))
    sensitivity = _positive(
        "sensor sensitivity_v_per_k", sensor.get("sensitivity_v_per_k")
    )
    floor = _positive(
        "sensor min_sensitivity_v_per_k", sensor.get("min_sensitivity_v_per_k")
    )
    findings = []
    covers_cold = usable_min <= operating_range["minimum_k"] - margin + TEMPERATURE_TOLERANCE_K
    covers_hot = usable_max >= operating_range["maximum_k"] + margin - TEMPERATURE_TOLERANCE_K
    if not covers_cold:
        findings.append(
            "sensor span starts at %g K, above the cold end %g K less the %g K margin"
            % (usable_min, operating_range["minimum_k"], margin)
        )
    if not covers_hot:
        findings.append(
            "sensor span ends at %g K, below the hot end %g K plus the %g K margin"
            % (usable_max, operating_range["maximum_k"], margin)
        )
    resolves = sensitivity >= floor * (1.0 - RELATIVE_TOLERANCE)
    if not resolves:
        findings.append(
            "cold-end sensitivity %g V/K is below the control floor %g V/K"
            % (sensitivity, floor)
        )
    return {
        "covers_range": covers_cold and covers_hot,
        "resolves_cold_end": resolves,
        "acceptable": covers_cold and covers_hot and resolves,
        "findings": findings,
    }


def assess_thermostat(controller, setpoint_k, allowable_band_k):
    """Grow a mechanical deadband in the cold and compare with the control band."""
    if not isinstance(controller, dict):
        raise ValueError("controller must be a mapping")
    kind = controller.get("kind")
    if kind not in CONTROL_KINDS:
        raise ValueError(
            "controller kind must be one of %s, got %r" % (", ".join(CONTROL_KINDS), kind)
        )
    nominal = _positive("controller deadband_k", controller.get("deadband_k"))
    setpoint = _positive("setpoint_k", setpoint_k)
    allowable = _positive("allowable_band_k", allowable_band_k)
    findings = []
    growth = 1.0
    if kind == CONTROL_MECHANICAL:
        floor = _positive(
            "controller qualification_floor_k", controller.get("qualification_floor_k")
        )
        shortfall = floor - setpoint
        if shortfall > 0.0:
            growth = 1.0 + DEADBAND_GROWTH_FACTOR * shortfall
            if growth > DEADBAND_GROWTH_CAP:
                growth = DEADBAND_GROWTH_CAP
            findings.append(
                "set point %g K is %g K below the mechanical qualification floor "
                "%g K; the deadband widens by a factor of %g"
                % (setpoint, shortfall, floor, growth)
            )
    effective = nominal * growth
    holds = effective <= allowable * (1.0 + RELATIVE_TOLERANCE)
    if not holds:
        findings.append(
            "effective deadband %g K exceeds the allowable control band %g K; an "
            "electronic controller is required rather than a tighter set point"
            % (effective, allowable)
        )
    return {
        "kind": kind,
        "nominal_deadband_k": nominal,
        "growth_factor": growth,
        "effective_deadband_k": effective,
        "allowable_band_k": allowable,
        "acceptable": holds,
        "electronic_controller_required": not holds,
        "findings": findings,
    }


def assess_gradient(gradient_k, allowable_gradient_k):
    """Compare an interface temperature gradient with its allowable."""
    gradient = _non_negative("gradient_k", gradient_k)
    allowable = _positive("allowable_gradient_k", allowable_gradient_k)
    margin = allowable - gradient
    return {
        "gradient_k": gradient,
        "allowable_gradient_k": allowable,
        "margin_k": margin,
        "acceptable": margin >= -TEMPERATURE_TOLERANCE_K,
        "findings": []
        if margin >= -TEMPERATURE_TOLERANCE_K
        else ["interface gradient exceeds its allowable by %g K" % (-margin)],
    }


def property_scatter_band(nominal, scatter_fraction, temperature_k):
    """Return the low and high bounds of a material property in the cold."""
    value = _positive("nominal", nominal)
    scatter = _real("scatter_fraction", scatter_fraction)
    if scatter < 0.0 or scatter >= 1.0:
        raise ValueError("scatter_fraction must lie in [0, 1), got %r" % (scatter_fraction,))
    temperature = _positive("temperature_k", temperature_k)
    effective = scatter
    if temperature < CRYOGENIC_UPPER_K - TEMPERATURE_TOLERANCE_K:
        effective = scatter * CRYOGENIC_SCATTER_FACTOR
        if effective >= 1.0:
            effective = 0.999999
    return {
        "nominal": value,
        "effective_scatter": effective,
        "low": value * (1.0 - effective),
        "high": value * (1.0 + effective),
    }


def conduction_heat_leak_band(conductivity_band, area_m2, length_m, delta_t_k):
    """Turn a conductivity band into a conduction heat-leak band in watts."""
    if not isinstance(conductivity_band, dict):
        raise ValueError("conductivity_band must be a mapping")
    for key in ("low", "high"):
        if key not in conductivity_band:
            raise ValueError("conductivity_band missing '%s'" % key)
    low_k = _positive("conductivity low", conductivity_band["low"])
    high_k = _positive("conductivity high", conductivity_band["high"])
    if high_k < low_k:
        raise ValueError("conductivity high must not be below low")
    area = _positive("area_m2", area_m2)
    length = _positive("length_m", length_m)
    delta = _non_negative("delta_t_k", delta_t_k)
    factor = area * delta / length
    return {"low_w": low_k * factor, "high_w": high_k * factor}


def size_cooler(heat_leak_band, parasitic_w=0.0, contingency_fraction=0.0):
    """Return the cooler capacity required at the high end of the leak band."""
    if not isinstance(heat_leak_band, dict) or "high_w" not in heat_leak_band:
        raise ValueError("heat_leak_band must be a mapping carrying 'high_w'")
    high = _non_negative("heat_leak high_w", heat_leak_band["high_w"])
    parasitic = _non_negative("parasitic_w", parasitic_w)
    contingency = _real("contingency_fraction", contingency_fraction)
    if contingency < 0.0 or contingency >= 1.0:
        raise ValueError(
            "contingency_fraction must lie in [0, 1), got %r" % (contingency_fraction,)
        )
    return (high + parasitic) * (1.0 + contingency)


def assess_cryogenic_item(spec):
    """Apply every cryogenic constraint to one thermal control item.

    spec keys: minimum_k, maximum_k, sensor, controller, setpoint_k,
    allowable_band_k, gradient_k, allowable_gradient_k, conductivity_w_mk,
    conductivity_scatter_fraction, area_m2, length_m, delta_t_k, and the
    optional parasitic_w and contingency_fraction consumed by size_cooler.
    """
    if not isinstance(spec, dict):
        raise ValueError("spec must be a mapping")
    required = (
        "minimum_k",
        "maximum_k",
        "sensor",
        "controller",
        "setpoint_k",
        "allowable_band_k",
        "gradient_k",
        "allowable_gradient_k",
        "conductivity_w_mk",
        "conductivity_scatter_fraction",
        "area_m2",
        "length_m",
        "delta_t_k",
    )
    for key in required:
        if key not in spec:
            raise ValueError("spec missing required key '%s'" % key)
    operating = validate_operating_range(spec["minimum_k"], spec["maximum_k"])
    sensor = assess_sensor(spec["sensor"], operating)
    controller = assess_thermostat(
        spec["controller"], spec["setpoint_k"], spec["allowable_band_k"]
    )
    gradient = assess_gradient(spec["gradient_k"], spec["allowable_gradient_k"])
    band = property_scatter_band(
        spec["conductivity_w_mk"],
        spec["conductivity_scatter_fraction"],
        operating["minimum_k"],
    )
    leak = conduction_heat_leak_band(
        band, spec["area_m2"], spec["length_m"], spec["delta_t_k"]
    )
    capacity_w = size_cooler(
        leak,
        parasitic_w=spec.get("parasitic_w", 0.0),
        contingency_fraction=spec.get("contingency_fraction", 0.0),
    )
    findings = (
        list(sensor["findings"]) + list(controller["findings"]) + list(gradient["findings"])
    )
    constraints = {
        "sensor": sensor["acceptable"],
        "controller": controller["acceptable"],
        "gradient": gradient["acceptable"],
    }
    return {
        "operating_range": operating,
        "sensor": sensor,
        "controller": controller,
        "gradient": gradient,
        "conductivity_band": band,
        "heat_leak_band_w": leak,
        "required_cooler_capacity_w": capacity_w,
        "constraints": constraints,
        "failed_constraints": sorted(k for k, ok in constraints.items() if not ok),
        "acceptable": all(constraints.values()),
        "findings": findings,
    }
