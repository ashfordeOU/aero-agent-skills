"""Junction temperature and heat-flow-path analysis for die-form MMICs.

Anchor: ECSS-Q-ST-60-12C clause 7.2.5 (thermal analysis -- predicting junction
temperatures and the heat flow paths through the die and its mounting).
Paraphrased into an implementable procedure; no standard text is reproduced.

Procedure implemented here
--------------------------
1. Validate the dissipating source footprint and the mounting stack beneath it:
   each layer's thickness, thermal conductivity and, for a die-attach layer,
   its void fraction.
2. Walk the stack from the source downwards, letting the heat spread outwards
   through each layer at the declared spreading angle, and compute the
   conduction resistance of every layer over the footprint it actually sees.
3. Sum the layer resistances into a source-to-reference thermal resistance and
   name the layer that dominates the heat flow path.
4. Raise the reference temperature by the dissipated power through that
   resistance to obtain the mean junction temperature.
5. Apply the peak-to-mean non-uniformity of a multi-finger active area, where
   each finger is warmed by its neighbours, to obtain the peak channel
   temperature from the mean junction temperature.
6. Grade the peak against the derated limit and report findings: a limit
   exceeded, a die-attach void fraction beyond what the process allows, and a
   single layer carrying an unreasonable share of the total resistance.
"""

import math

__all__ = [
    "TEMPERATURE_TOLERANCE_C",
    "DEFAULT_SPREAD_ANGLE_DEG",
    "MAX_VOID_FRACTION",
    "DOMINANT_LAYER_SHARE",
    "validate_positive",
    "validate_void_fraction",
    "effective_conductivity",
    "spreading_resistance_k_per_w",
    "layer_footprint_um",
    "stack_resistance",
    "junction_temperature_c",
    "finger_peak_to_mean_factor",
    "peak_channel_temperature_c",
    "derated_limit_c",
    "assess_mmic_thermal",
]

# Temperature comparisons are sums of computed floats; a case that is
# physically exactly on the limit can land a few ULPs on the wrong side.
# Absorb the representation error here, never by raising the limit.
TEMPERATURE_TOLERANCE_C = 1e-9

# Heat leaving a small source into a thick layer spreads outwards; 45 degrees
# is the conventional cone used when no solver result is available.
DEFAULT_SPREAD_ANGLE_DEG = 45.0

# A die-attach layer with more voiding than this is a process finding, not a
# thermal input to be derated and accepted.
MAX_VOID_FRACTION = 0.10

# A single layer carrying more than this share of the total resistance is the
# lever the design has, and is reported so the effort goes to the right place.
DOMINANT_LAYER_SHARE = 0.60


def validate_positive(label, value):
    """Return value as a strictly positive finite float, or raise ValueError."""
    if not isinstance(value, (int, float)) or isinstance(value, bool):
        raise ValueError("%s must be a real number, got %r" % (label, value))
    number = float(value)
    if not math.isfinite(number):
        raise ValueError("%s must be finite, got %r" % (label, value))
    if number <= 0.0:
        raise ValueError("%s must be strictly positive, got %r" % (label, value))
    return number


def validate_void_fraction(value):
    """Return a void fraction as a float in [0, 1), or raise ValueError."""
    if not isinstance(value, (int, float)) or isinstance(value, bool):
        raise ValueError("void_fraction must be a real number, got %r" % (value,))
    number = float(value)
    if not math.isfinite(number):
        raise ValueError("void_fraction must be finite, got %r" % (value,))
    if number < 0.0 or number >= 1.0:
        raise ValueError("void_fraction must lie in [0, 1), got %r" % (value,))
    return number


def effective_conductivity(conductivity_w_mk, void_fraction=0.0):
    """Return the conductivity in W/mK left after voiding removes contact area."""
    conductivity = validate_positive("conductivity_w_mk", conductivity_w_mk)
    voids = validate_void_fraction(void_fraction)
    return conductivity * (1.0 - voids)


def spreading_resistance_k_per_w(width_um, length_um, thickness_um,
                                 conductivity_w_mk, spread_angle_deg=DEFAULT_SPREAD_ANGLE_DEG):
    """Return the conduction resistance in K/W of one layer with heat spreading.

    The rectangular source of width_um by length_um expands on every side by
    the layer thickness times the tangent of the spreading angle. The integral
    of the resulting truncated pyramid has a closed form for the general
    rectangle and a separate one for a square source.
    """
    width = validate_positive("width_um", width_um)
    length = validate_positive("length_um", length_um)
    thickness = validate_positive("thickness_um", thickness_um)
    conductivity = validate_positive("conductivity_w_mk", conductivity_w_mk)
    if not isinstance(spread_angle_deg, (int, float)) or isinstance(spread_angle_deg, bool):
        raise ValueError("spread_angle_deg must be a real number, got %r" % (spread_angle_deg,))
    angle = float(spread_angle_deg)
    if not math.isfinite(angle) or angle < 0.0 or angle >= 90.0:
        raise ValueError("spread_angle_deg must lie in [0, 90), got %r" % (spread_angle_deg,))

    a = width * 1.0e-6
    b = length * 1.0e-6
    t = thickness * 1.0e-6
    growth = 2.0 * t * math.tan(math.radians(angle))
    if growth <= 0.0:
        # No spreading: a plain prism of the source footprint.
        return t / (conductivity * a * b)
    if math.isclose(a, b, rel_tol=1e-12, abs_tol=0.0):
        return t / (conductivity * a * (a + growth))
    # Integrating dz / (k (a + u z)(b + u z)) over the layer thickness, with
    # u = 2 tan(phi) and growth = u t. Both factors change sign together when
    # the source is taller than it is wide, so the result stays positive.
    return (
        t
        / (conductivity * growth * (b - a))
        * math.log((b * (a + growth)) / (a * (b + growth)))
    )


def layer_footprint_um(width_um, length_um, thickness_um,
                       spread_angle_deg=DEFAULT_SPREAD_ANGLE_DEG):
    """Return the (width, length) in um the heat occupies after crossing a layer."""
    width = validate_positive("width_um", width_um)
    length = validate_positive("length_um", length_um)
    thickness = validate_positive("thickness_um", thickness_um)
    if not isinstance(spread_angle_deg, (int, float)) or isinstance(spread_angle_deg, bool):
        raise ValueError("spread_angle_deg must be a real number, got %r" % (spread_angle_deg,))
    angle = float(spread_angle_deg)
    if not math.isfinite(angle) or angle < 0.0 or angle >= 90.0:
        raise ValueError("spread_angle_deg must lie in [0, 90), got %r" % (spread_angle_deg,))
    growth = 2.0 * thickness * math.tan(math.radians(angle))
    return (width + growth, length + growth)


def stack_resistance(source_width_um, source_length_um, layers,
                     spread_angle_deg=DEFAULT_SPREAD_ANGLE_DEG):
    """Return per-layer records and the total source-to-reference resistance.

    layers is an ordered sequence of mappings from the source downwards, each
    with 'name', 'thickness_um', 'conductivity_w_mk' and an optional
    'void_fraction'.
    """
    if not isinstance(layers, (list, tuple)) or not layers:
        raise ValueError("layers must be a non-empty ordered sequence")
    width = validate_positive("source_width_um", source_width_um)
    length = validate_positive("source_length_um", source_length_um)
    records = []
    seen = set()
    total = 0.0
    for index, layer in enumerate(layers):
        if not isinstance(layer, dict):
            raise ValueError("layers[%d] must be a mapping" % index)
        name = layer.get("name")
        if not isinstance(name, str) or not name.strip():
            raise ValueError("layers[%d] requires a non-empty 'name'" % index)
        if name in seen:
            raise ValueError("duplicate layer name '%s'" % name)
        seen.add(name)
        voids = validate_void_fraction(layer.get("void_fraction", 0.0))
        conductivity = effective_conductivity(layer.get("conductivity_w_mk"), voids)
        thickness = validate_positive("layers[%d].thickness_um" % index, layer.get("thickness_um"))
        resistance = spreading_resistance_k_per_w(
            width, length, thickness, conductivity, spread_angle_deg
        )
        total += resistance
        records.append(
            {
                "name": name,
                "thickness_um": thickness,
                "conductivity_w_mk": conductivity,
                "void_fraction": voids,
                "entry_width_um": width,
                "entry_length_um": length,
                "resistance_k_per_w": resistance,
            }
        )
        width, length = layer_footprint_um(width, length, thickness, spread_angle_deg)
    for record in records:
        record["share_of_total"] = record["resistance_k_per_w"] / total
    return {
        "layers": records,
        "total_resistance_k_per_w": total,
        "exit_width_um": width,
        "exit_length_um": length,
    }


def junction_temperature_c(reference_temperature_c, power_w, resistance_k_per_w):
    """Return the mean junction temperature in degC above a reference surface."""
    if not isinstance(reference_temperature_c, (int, float)) or isinstance(
        reference_temperature_c, bool
    ):
        raise ValueError("reference_temperature_c must be a real number")
    reference = float(reference_temperature_c)
    if not math.isfinite(reference):
        raise ValueError("reference_temperature_c must be finite")
    if reference <= -273.15:
        raise ValueError("reference_temperature_c is below absolute zero, got %r" % (reference,))
    power = validate_positive("power_w", power_w)
    resistance = validate_positive("resistance_k_per_w", resistance_k_per_w)
    return reference + power * resistance


def finger_peak_to_mean_factor(finger_count, pitch_um, substrate_thickness_um):
    """Return the peak-to-mean temperature non-uniformity of a multi-finger area.

    Every finger is warmed by every other one, with the contribution falling as
    the in-plane separation grows relative to the substrate thickness the heat
    travels through. The stack resistance already carries the mean rise of the
    whole active area, so what is wanted here is how much hotter the worst
    finger runs than that mean. A single finger, and a symmetric pair, are
    uniform by construction and return exactly one.
    """
    if not isinstance(finger_count, int) or isinstance(finger_count, bool):
        raise ValueError("finger_count must be an integer, got %r" % (finger_count,))
    if finger_count < 1:
        raise ValueError("finger_count must be at least one, got %d" % finger_count)
    pitch = validate_positive("pitch_um", pitch_um)
    thickness = validate_positive("substrate_thickness_um", substrate_thickness_um)
    if finger_count == 1:
        return 1.0
    rises = []
    for i in range(finger_count):
        rise = 1.0
        for j in range(finger_count):
            if i == j:
                continue
            separation = abs(i - j) * pitch
            rise += 1.0 / (1.0 + separation / thickness)
        rises.append(rise)
    mean = sum(rises) / float(finger_count)
    return max(rises) / mean


def peak_channel_temperature_c(reference_temperature_c, power_w, resistance_k_per_w,
                               coupling_factor):
    """Return the peak channel temperature in degC including mutual heating."""
    factor = validate_positive("coupling_factor", coupling_factor)
    if factor < 1.0:
        raise ValueError("coupling_factor cannot cool the die, got %r" % (coupling_factor,))
    mean = junction_temperature_c(reference_temperature_c, power_w, resistance_k_per_w)
    rise = mean - float(reference_temperature_c)
    return float(reference_temperature_c) + rise * factor


def derated_limit_c(limit_temperature_c, derating_margin_c):
    """Return the derated junction-temperature limit in degC."""
    if not isinstance(limit_temperature_c, (int, float)) or isinstance(limit_temperature_c, bool):
        raise ValueError("limit_temperature_c must be a real number")
    limit = float(limit_temperature_c)
    if not math.isfinite(limit):
        raise ValueError("limit_temperature_c must be finite")
    if not isinstance(derating_margin_c, (int, float)) or isinstance(derating_margin_c, bool):
        raise ValueError("derating_margin_c must be a real number")
    margin = float(derating_margin_c)
    if not math.isfinite(margin) or margin < 0.0:
        raise ValueError("derating_margin_c must be non-negative and finite, got %r" % (margin,))
    if margin >= limit + 273.15:
        raise ValueError("derating_margin_c removes the whole temperature range")
    return limit - margin


def assess_mmic_thermal(spec):
    """Run the full clause 7.2.5 junction-temperature assessment.

    spec keys: source_width_um, source_length_um, layers, power_w,
    reference_temperature_c, limit_temperature_c, derating_margin_c;
    optional spread_angle_deg, finger_count, finger_pitch_um,
    substrate_thickness_um.
    """
    if not isinstance(spec, dict):
        raise ValueError("spec must be a mapping")
    required_keys = (
        "source_width_um",
        "source_length_um",
        "layers",
        "power_w",
        "reference_temperature_c",
        "limit_temperature_c",
        "derating_margin_c",
    )
    for key in required_keys:
        if key not in spec:
            raise ValueError("spec missing required key '%s'" % key)

    angle = spec.get("spread_angle_deg", DEFAULT_SPREAD_ANGLE_DEG)
    stack = stack_resistance(
        spec["source_width_um"], spec["source_length_um"], spec["layers"], angle
    )
    total = stack["total_resistance_k_per_w"]
    power = validate_positive("power_w", spec["power_w"])
    reference = spec["reference_temperature_c"]

    finger_count = spec.get("finger_count", 1)
    if finger_count == 1:
        coupling = 1.0
    else:
        coupling = finger_peak_to_mean_factor(
            finger_count,
            spec.get("finger_pitch_um"),
            spec.get("substrate_thickness_um"),
        )

    mean_tj = junction_temperature_c(reference, power, total)
    peak_tj = peak_channel_temperature_c(reference, power, total, coupling)
    limit = derated_limit_c(spec["limit_temperature_c"], spec["derating_margin_c"])
    margin = limit - peak_tj

    dominant = max(stack["layers"], key=lambda r: r["resistance_k_per_w"])
    findings = []
    if peak_tj > limit + TEMPERATURE_TOLERANCE_C:
        findings.append(
            "peak channel temperature %.3f degC exceeds the derated limit of %.3f degC"
            % (peak_tj, limit)
        )
    for record in stack["layers"]:
        if record["void_fraction"] > MAX_VOID_FRACTION + TEMPERATURE_TOLERANCE_C:
            findings.append(
                "layer '%s' carries a void fraction of %.3f, beyond the %.3f the "
                "attach process allows" % (record["name"], record["void_fraction"], MAX_VOID_FRACTION)
            )
    if dominant["share_of_total"] > DOMINANT_LAYER_SHARE:
        findings.append(
            "layer '%s' carries %.1f%% of the source-to-reference resistance and is "
            "the lever on junction temperature"
            % (dominant["name"], 100.0 * dominant["share_of_total"])
        )

    return {
        "layers": stack["layers"],
        "total_resistance_k_per_w": total,
        "exit_width_um": stack["exit_width_um"],
        "exit_length_um": stack["exit_length_um"],
        "coupling_factor": coupling,
        "mean_junction_temperature_c": mean_tj,
        "peak_channel_temperature_c": peak_tj,
        "derated_limit_c": limit,
        "margin_c": margin,
        "dominant_layer": dominant["name"],
        "findings": findings,
        "compliant": peak_tj <= limit + TEMPERATURE_TOLERANCE_C,
    }
