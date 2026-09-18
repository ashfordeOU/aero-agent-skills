"""Full-scale coverage of the current telemetry on a protected power output.

Anchor: ECSS-E-ST-20-20C clause 5.2.8.3.1 (the telemetry range has to reach at
least the maximum limitation current of the protection device). Paraphrased
into an implementable procedure; no standard text is reproduced.

Procedure implemented here
--------------------------
1. Build the worst-case maximum limitation current of the protection device
   from its class current, the ratio at which it limits, and the arithmetic
   sum of the declared spread contributors (initial tolerance, temperature,
   ageing, radiation, supply).
2. Refer the converter span of the telemetry chain back through the amplifier
   gain and the shunt resistance to obtain the current the chain reports at
   full scale, taking the zero-current output voltage off the usable span and
   honouring an amplifier clip level when the amplifier saturates first.
3. Name the element that clips first, because raising the converter reference
   does nothing for a chain the amplifier bounds.
4. Compare the full-scale current with the worst-case maximum limitation
   current, report the headroom, and report the telemetry resolution so a
   chain that only just reaches the limit is visible as such.
"""

import math

__all__ = [
    "COVERAGE_TOLERANCE_A",
    "SPREAD_CONTRIBUTORS",
    "limitation_band",
    "worst_case_limitation_current",
    "telemetry_full_scale_current",
    "telemetry_resolution_a",
    "headroom_fraction",
    "assess_full_scale_coverage",
]

# Coverage is an inequality between two currents that a design can place
# exactly on top of each other. Absorb the representation error here instead
# of relaxing the engineering requirement.
COVERAGE_TOLERANCE_A = 1e-9

# Spread contributors recognised on a protection device limitation figure.
SPREAD_CONTRIBUTORS = (
    "tolerance",
    "temperature",
    "ageing",
    "radiation",
    "supply",
)


def _real(label, value):
    """Return value as a finite float or raise."""
    if not isinstance(value, (int, float)) or isinstance(value, bool):
        raise ValueError("%s must be a real number, got %r" % (label, value))
    out = float(value)
    if not math.isfinite(out):
        raise ValueError("%s must be finite, got %r" % (label, value))
    return out


def _positive(label, value):
    """Return value as a strictly positive finite float or raise."""
    out = _real(label, value)
    if out <= 0.0:
        raise ValueError("%s must be positive, got %r" % (label, value))
    return out


def _non_negative(label, value):
    """Return value as a non-negative finite float or raise."""
    out = _real(label, value)
    if out < 0.0:
        raise ValueError("%s must be non-negative, got %r" % (label, value))
    return out


def _spread_sum(contributors):
    """Return the arithmetic sum of the declared fractional spreads."""
    if contributors is None:
        return 0.0
    if not isinstance(contributors, dict):
        raise ValueError("contributors must be a mapping of name to fraction")
    total = 0.0
    for name, fraction in contributors.items():
        if not isinstance(name, str) or not name.strip():
            raise ValueError("contributor name must be a non-empty string")
        key = name.strip().lower()
        if key not in SPREAD_CONTRIBUTORS:
            raise ValueError(
                "unknown contributor '%s'; recognised: %s"
                % (name, ", ".join(SPREAD_CONTRIBUTORS))
            )
        value = _non_negative("contributor '%s'" % key, fraction)
        if value >= 1.0:
            raise ValueError(
                "contributor '%s' is a fraction below 1.0, got %r" % (key, fraction)
            )
        total += value
    if total >= 1.0:
        raise ValueError(
            "summed contributor spread %g reaches or passes 1.0; the limitation "
            "band would collapse through zero" % total
        )
    return total


def limitation_band(class_current_a, limitation_ratio, contributors=None):
    """Return the (minimum, maximum) limitation current of the protection device.

    The limitation ratio is the multiple of the class current at which the
    device goes into limiting; it can never sit below the class current, since
    a device that limits under its own class rating is mis-specified.
    """
    class_current = _positive("class_current_a", class_current_a)
    ratio = _positive("limitation_ratio", limitation_ratio)
    if ratio < 1.0:
        raise ValueError(
            "limitation_ratio %g places the limitation current below the class "
            "current; the device would limit inside its own rating" % ratio
        )
    spread = _spread_sum(contributors)
    nominal = class_current * ratio
    return (nominal * (1.0 - spread), nominal * (1.0 + spread))


def worst_case_limitation_current(class_current_a, limitation_ratio, contributors=None):
    """Return the maximum limitation current the telemetry has to reach."""
    return limitation_band(class_current_a, limitation_ratio, contributors)[1]


def telemetry_full_scale_current(shunt_ohm, gain, converter_span_v,
                                 zero_output_v=0.0, amplifier_clip_v=None):
    """Return the full-scale current of the telemetry chain and its limiting element.

    The usable span is what is left of the converter span above the
    zero-current output voltage, bounded by the amplifier clip level when one
    is declared and lower.
    """
    shunt = _positive("shunt_ohm", shunt_ohm)
    amp_gain = _positive("gain", gain)
    span = _positive("converter_span_v", converter_span_v)
    zero_v = _non_negative("zero_output_v", zero_output_v)
    if zero_v >= span:
        raise ValueError(
            "zero_output_v %g leaves no span below the converter span %g"
            % (zero_v, span)
        )
    limiting_element = "converter"
    ceiling_v = span
    if amplifier_clip_v is not None:
        clip = _positive("amplifier_clip_v", amplifier_clip_v)
        if clip <= zero_v:
            raise ValueError(
                "amplifier_clip_v %g sits at or below the zero-current output "
                "voltage %g; the chain reports nothing" % (clip, zero_v)
            )
        if clip < span:
            ceiling_v = clip
            limiting_element = "amplifier"
    usable_v = ceiling_v - zero_v
    return {
        "full_scale_current_a": usable_v / (shunt * amp_gain),
        "usable_span_v": usable_v,
        "ceiling_v": ceiling_v,
        "limiting_element": limiting_element,
    }


def telemetry_resolution_a(full_scale_current_a, bits):
    """Return the current represented by one converter code."""
    full_scale = _positive("full_scale_current_a", full_scale_current_a)
    if not isinstance(bits, int) or isinstance(bits, bool):
        raise ValueError("bits must be an integer, got %r" % (bits,))
    if bits < 1 or bits > 32:
        raise ValueError("bits must lie between 1 and 32, got %d" % bits)
    return full_scale / float((1 << bits) - 1)


def headroom_fraction(full_scale_current_a, required_current_a):
    """Return the fraction by which full scale passes the required current."""
    full_scale = _positive("full_scale_current_a", full_scale_current_a)
    required = _positive("required_current_a", required_current_a)
    return (full_scale - required) / required


def assess_full_scale_coverage(spec):
    """Run the clause 5.2.8.3.1 full-scale coverage assessment.

    spec keys: class_current_a, limitation_ratio, shunt_ohm, gain,
    converter_span_v; optional contributors, zero_output_v, amplifier_clip_v,
    bits, required_resolution_a.
    """
    if not isinstance(spec, dict):
        raise ValueError("spec must be a mapping")
    for key in ("class_current_a", "limitation_ratio", "shunt_ohm", "gain",
                "converter_span_v"):
        if key not in spec:
            raise ValueError("spec missing required key '%s'" % key)
    required = worst_case_limitation_current(
        spec["class_current_a"],
        spec["limitation_ratio"],
        spec.get("contributors"),
    )
    chain = telemetry_full_scale_current(
        spec["shunt_ohm"],
        spec["gain"],
        spec["converter_span_v"],
        spec.get("zero_output_v", 0.0),
        spec.get("amplifier_clip_v"),
    )
    full_scale = chain["full_scale_current_a"]
    covered = full_scale > required or math.isclose(
        full_scale, required, rel_tol=0.0, abs_tol=COVERAGE_TOLERANCE_A
    )
    findings = []
    if not covered:
        findings.append(
            "telemetry full scale %.4f A stops below the worst-case maximum "
            "limitation current %.4f A; the reported current saturates before "
            "the device limits" % (full_scale, required)
        )
        if chain["limiting_element"] == "amplifier":
            findings.append(
                "the amplifier clips at %.4f V before the converter span is "
                "used; raising the converter reference would not extend the "
                "range" % chain["ceiling_v"]
            )
    resolution = None
    if "bits" in spec:
        resolution = telemetry_resolution_a(full_scale, spec["bits"])
        if "required_resolution_a" in spec:
            allowed = _positive(
                "required_resolution_a", spec["required_resolution_a"]
            )
            coarser = resolution > allowed and not math.isclose(
                resolution, allowed, rel_tol=0.0, abs_tol=COVERAGE_TOLERANCE_A
            )
            if coarser:
                findings.append(
                    "one code is %.6f A against a required %.6f A; the range "
                    "was bought with resolution" % (resolution, allowed)
                )
    return {
        "required_current_a": required,
        "full_scale_current_a": full_scale,
        "limiting_element": chain["limiting_element"],
        "usable_span_v": chain["usable_span_v"],
        "headroom_fraction": headroom_fraction(full_scale, required),
        "resolution_a": resolution,
        "covered": covered,
        "compliant": covered and not findings,
        "findings": findings,
    }
