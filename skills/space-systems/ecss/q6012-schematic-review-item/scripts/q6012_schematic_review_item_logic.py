"""Schematic review item of a die-form MMIC design review.

Anchor: ECSS-Q-ST-60-12C clause 7.3.3 (design review -- the schematic item).
Paraphrased into an implementable procedure; no standard text is reproduced.

Procedure implemented here
--------------------------
1. Validate the schematic package: the device list, the net list and the
   foundry scalable-model validity window the review grades sizing against.
2. Device sizing. Each active device is drawn as a unit gate width repeated
   over a finger count; the review quantity is the total gate periphery
   W = unit_gate_width_um * finger_count / 1000 in mm. A device is gradeable
   only while all three of unit gate width, finger count and total periphery
   sit inside the foundry model validity window, because outside it the
   scalable model is being extrapolated and the simulated performance behind
   the schematic has no basis.
3. Bias arrangement. The quiescent point is derived from the drawn bias feed,
   not from the intended supply: the feed resistance drops the rail, so
   Vds = Vdd - Id * R_feed. That operating point is then graded three ways --
   drain voltage against the derated maximum rating, drain current density
   Id / W against the process window for the intended operating class, and
   dissipation density Vds * Id / W against the thermal limit of the process.
4. Connectivity. Every declared device terminal has to appear on a net, every
   net has to reach at least two connections, and every bias net has to carry
   a decoupling element, otherwise the diagram cannot be reviewed as drawn.
5. The item passes only when sizing, bias and connectivity are all clean; each
   failure is emitted as a named finding so the review can action it.
"""

import math

__all__ = [
    "COMPARISON_TOLERANCE",
    "total_gate_periphery_mm",
    "check_device_sizing",
    "bias_operating_point",
    "check_bias_arrangement",
    "check_connectivity",
    "review_device",
    "review_schematic",
]

# Sizing and bias limits are graded with inclusive bounds. A drawn value that
# is meant to sit exactly on a bound can land a few ULPs either side once it
# has been through a unit conversion, so absorb the representation error here
# rather than by loosening the foundry limit itself.
COMPARISON_TOLERANCE = 1e-9

_DEFAULT_TERMINALS = ("gate", "drain", "source")


def _real(label, value):
    """Return value as a finite float or raise."""
    if not isinstance(value, (int, float)) or isinstance(value, bool):
        raise ValueError("%s must be a real number" % label)
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


def _fraction(label, value):
    """Return a derating factor in (0, 1] or raise."""
    out = _positive(label, value)
    if out > 1.0:
        raise ValueError("%s must not exceed 1, got %r" % (label, value))
    return out


def _text(label, value):
    """Return a non-empty stripped identifier or raise."""
    if not isinstance(value, str):
        raise ValueError("%s must be a string" % label)
    out = value.strip()
    if not out:
        raise ValueError("%s must not be empty" % label)
    return out


def _bounds(label, value):
    """Return an ordered (low, high) pair of positive bounds or raise."""
    if not isinstance(value, (list, tuple)) or len(value) != 2:
        raise ValueError("%s must be a (low, high) pair" % label)
    low = _positive("%s low bound" % label, value[0])
    high = _positive("%s high bound" % label, value[1])
    if low > high:
        raise ValueError("%s low bound %g exceeds high bound %g" % (label, low, high))
    return (low, high)


def _at_or_below(value, limit):
    """True when value is within the limit, an exact landing counted as inside."""
    if value <= limit:
        return True
    return math.isclose(value, limit, rel_tol=0.0, abs_tol=COMPARISON_TOLERANCE)


def _at_or_above(value, limit):
    """True when value reaches the limit, an exact landing counted as inside."""
    if value >= limit:
        return True
    return math.isclose(value, limit, rel_tol=0.0, abs_tol=COMPARISON_TOLERANCE)


def _inside(value, bounds):
    """True when value lies within the inclusive bounds pair."""
    low, high = bounds
    return _at_or_above(value, low) and _at_or_below(value, high)


def total_gate_periphery_mm(unit_gate_width_um, finger_count):
    """Return the total gate periphery in mm of a multi-finger active device."""
    width = _positive("unit_gate_width_um", unit_gate_width_um)
    if not isinstance(finger_count, int) or isinstance(finger_count, bool):
        raise ValueError("finger_count must be an integer, got %r" % (finger_count,))
    if finger_count < 1:
        raise ValueError("finger_count must be at least 1, got %d" % finger_count)
    return width * finger_count / 1000.0


def check_device_sizing(device, model_limits):
    """Grade one drawn device against the foundry scalable-model window."""
    if not isinstance(device, dict):
        raise ValueError("device must be a mapping")
    if not isinstance(model_limits, dict):
        raise ValueError("model_limits must be a mapping")
    reference = _text("device reference", device.get("reference", ""))
    width = _positive("%s unit_gate_width_um" % reference, device.get("unit_gate_width_um"))
    fingers = device.get("finger_count")
    periphery = total_gate_periphery_mm(width, fingers)

    width_bounds = _bounds("unit_gate_width_um limits", model_limits.get("unit_gate_width_um"))
    periphery_bounds = _bounds(
        "total_periphery_mm limits", model_limits.get("total_periphery_mm")
    )
    finger_bounds = model_limits.get("finger_count")
    if not isinstance(finger_bounds, (list, tuple)) or len(finger_bounds) != 2:
        raise ValueError("finger_count limits must be a (low, high) pair")
    low_fingers, high_fingers = finger_bounds
    for label, item in (("low", low_fingers), ("high", high_fingers)):
        if not isinstance(item, int) or isinstance(item, bool):
            raise ValueError("finger_count %s bound must be an integer" % label)
    if low_fingers < 1 or low_fingers > high_fingers:
        raise ValueError("finger_count limits must be an ordered pair of positive integers")

    findings = []
    if not _inside(width, width_bounds):
        findings.append(
            "%s: unit gate width %g um is outside the model window [%g, %g] um"
            % (reference, width, width_bounds[0], width_bounds[1])
        )
    if fingers < low_fingers or fingers > high_fingers:
        findings.append(
            "%s: finger count %d is outside the model window [%d, %d]"
            % (reference, fingers, low_fingers, high_fingers)
        )
    if not _inside(periphery, periphery_bounds):
        findings.append(
            "%s: total gate periphery %g mm is outside the model window [%g, %g] mm"
            % (reference, periphery, periphery_bounds[0], periphery_bounds[1])
        )
    return {
        "reference": reference,
        "unit_gate_width_um": width,
        "finger_count": fingers,
        "total_periphery_mm": periphery,
        "sizing_gradeable": not findings,
        "findings": findings,
    }


def bias_operating_point(supply_v, feed_resistance_ohm, drain_current_ma, total_periphery_mm):
    """Return the quiescent point the drawn bias feed actually produces."""
    supply = _positive("supply_v", supply_v)
    feed = _real("feed_resistance_ohm", feed_resistance_ohm)
    if feed < 0.0:
        raise ValueError("feed_resistance_ohm must not be negative, got %r" % (feed_resistance_ohm,))
    current_ma = _positive("drain_current_ma", drain_current_ma)
    periphery = _positive("total_periphery_mm", total_periphery_mm)
    drop = current_ma / 1000.0 * feed
    vds = supply - drop
    if vds <= 0.0:
        raise ValueError(
            "bias feed drop %g V collapses the drain node at supply %g V" % (drop, supply)
        )
    dissipation_mw = vds * current_ma
    return {
        "supply_v": supply,
        "feed_resistance_ohm": feed,
        "feed_drop_v": drop,
        "drain_current_ma": current_ma,
        "drain_voltage_v": vds,
        "total_periphery_mm": periphery,
        "current_density_ma_per_mm": current_ma / periphery,
        "dissipation_mw": dissipation_mw,
        "dissipation_density_mw_per_mm": dissipation_mw / periphery,
    }


def check_bias_arrangement(point, policy, reference="device"):
    """Grade a quiescent point against the derating and process bias policy."""
    if not isinstance(point, dict):
        raise ValueError("point must be a mapping produced by bias_operating_point")
    if not isinstance(policy, dict):
        raise ValueError("policy must be a mapping")
    for key in ("drain_voltage_v", "current_density_ma_per_mm", "dissipation_density_mw_per_mm"):
        if key not in point:
            raise ValueError("point missing required key '%s'" % key)
    label = _text("reference", reference)
    rated = _positive("max_drain_voltage_v", policy.get("max_drain_voltage_v"))
    factor = _fraction("derating_factor", policy.get("derating_factor"))
    window = _bounds(
        "current_density_window_ma_per_mm", policy.get("current_density_window_ma_per_mm")
    )
    thermal = _positive(
        "max_dissipation_mw_per_mm", policy.get("max_dissipation_mw_per_mm")
    )
    derated = rated * factor

    findings = []
    vds = point["drain_voltage_v"]
    if not _at_or_below(vds, derated):
        findings.append(
            "%s: drain voltage %g V exceeds the derated maximum %g V (%g V rated at %g)"
            % (label, vds, derated, rated, factor)
        )
    density = point["current_density_ma_per_mm"]
    if not _inside(density, window):
        findings.append(
            "%s: drain current density %g mA/mm is outside the class window [%g, %g] mA/mm"
            % (label, density, window[0], window[1])
        )
    heat = point["dissipation_density_mw_per_mm"]
    if not _at_or_below(heat, thermal):
        findings.append(
            "%s: dissipation density %g mW/mm exceeds the process limit %g mW/mm"
            % (label, heat, thermal)
        )
    return {
        "reference": label,
        "derated_drain_voltage_v": derated,
        "bias_acceptable": not findings,
        "findings": findings,
    }


def check_connectivity(devices, nets):
    """Grade the drawn diagram for floating nets, orphan terminals and decoupling."""
    if not isinstance(devices, (list, tuple)) or not devices:
        raise ValueError("devices must be a non-empty sequence")
    if not isinstance(nets, (list, tuple)) or not nets:
        raise ValueError("nets must be a non-empty sequence")

    connected = set()
    findings = []
    seen_nets = set()
    for index, net in enumerate(nets):
        if not isinstance(net, dict):
            raise ValueError("nets[%d] must be a mapping" % index)
        name = _text("nets[%d] name" % index, net.get("name", ""))
        if name in seen_nets:
            raise ValueError("net '%s' is declared twice" % name)
        seen_nets.add(name)
        kind = _text("nets[%d] kind" % index, net.get("kind", "")).lower()
        if kind not in ("signal", "bias", "ground"):
            raise ValueError(
                "net '%s' kind must be signal, bias or ground, got %r" % (name, net.get("kind"))
            )
        connections = net.get("connections")
        if not isinstance(connections, (list, tuple)):
            raise ValueError("net '%s' connections must be a sequence" % name)
        pins = [_text("net '%s' connection" % name, item) for item in connections]
        for pin in pins:
            connected.add(pin.lower())
        if len(pins) < 2:
            findings.append(
                "net '%s' reaches %d connection(s); a net that goes nowhere cannot be reviewed"
                % (name, len(pins))
            )
        if kind == "bias":
            decoupled = net.get("decoupled")
            if not isinstance(decoupled, bool):
                raise ValueError("bias net '%s' must declare a boolean 'decoupled'" % name)
            if not decoupled:
                findings.append("bias net '%s' carries no decoupling element" % name)

    seen_devices = set()
    for index, device in enumerate(devices):
        if not isinstance(device, dict):
            raise ValueError("devices[%d] must be a mapping" % index)
        reference = _text("devices[%d] reference" % index, device.get("reference", ""))
        if reference.lower() in seen_devices:
            raise ValueError("device reference '%s' is used twice" % reference)
        seen_devices.add(reference.lower())
        terminals = device.get("terminals", _DEFAULT_TERMINALS)
        if not isinstance(terminals, (list, tuple)) or not terminals:
            raise ValueError("device '%s' terminals must be a non-empty sequence" % reference)
        for terminal in terminals:
            pin = "%s.%s" % (reference, _text("terminal of '%s'" % reference, terminal))
            if pin.lower() not in connected:
                findings.append("device terminal %s is not on any net" % pin)
    return {
        "net_count": len(seen_nets),
        "device_count": len(seen_devices),
        "connectivity_clean": not findings,
        "findings": findings,
    }


def review_device(device, model_limits, policy):
    """Run the sizing and bias grading for one device of the schematic."""
    sizing = check_device_sizing(device, model_limits)
    point = bias_operating_point(
        device.get("supply_v"),
        device.get("feed_resistance_ohm"),
        device.get("drain_current_ma"),
        sizing["total_periphery_mm"],
    )
    bias = check_bias_arrangement(point, policy, sizing["reference"])
    return {
        "reference": sizing["reference"],
        "sizing": sizing,
        "operating_point": point,
        "bias": bias,
        "findings": list(sizing["findings"]) + list(bias["findings"]),
        "acceptable": sizing["sizing_gradeable"] and bias["bias_acceptable"],
    }


def review_schematic(package):
    """Run the whole clause 7.3.3 schematic review item over a design package.

    package keys: devices (each carrying reference, unit_gate_width_um,
    finger_count, supply_v, feed_resistance_ohm, drain_current_ma and an
    optional terminals list), nets, model_limits, bias_policy.
    """
    if not isinstance(package, dict):
        raise ValueError("package must be a mapping")
    for key in ("devices", "nets", "model_limits", "bias_policy"):
        if key not in package:
            raise ValueError("package missing required key '%s'" % key)
    devices = package["devices"]
    if not isinstance(devices, (list, tuple)) or not devices:
        raise ValueError("package['devices'] must be a non-empty sequence")

    reviewed = [
        review_device(device, package["model_limits"], package["bias_policy"])
        for device in devices
    ]
    connectivity = check_connectivity(devices, package["nets"])
    findings = []
    for record in reviewed:
        findings.extend(record["findings"])
    findings.extend(connectivity["findings"])
    return {
        "devices": reviewed,
        "connectivity": connectivity,
        "findings": findings,
        "worst_dissipation_density_mw_per_mm": max(
            record["operating_point"]["dissipation_density_mw_per_mm"] for record in reviewed
        ),
        "item_passed": not findings,
    }
