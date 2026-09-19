#!/usr/bin/env python3
"""Actuator interface compatibility conditions under ECSS-E-ST-20-21C
clause 5.4.1.

Paraphrased, implementable procedure (no verbatim standard text):

* An actuator electronics output and the actuator it drives are compatible
  only when the current that actually flows on firing lands inside the
  window the interface specifies -- above the floor that guarantees the
  actuator functions, below the ceiling the interface is allowed to
  present.
* The current is set by a loop, not by the actuator alone. The drive
  voltage the electronics presents divides across its own source
  resistance, the harness between the two, and the actuator itself, so
  every one of those three carries a spread and every spread moves the
  current.
* Compatibility is therefore a corner question. The high-current corner
  is the highest drive voltage against the lowest total loop resistance;
  the low-current corner is the lowest drive voltage against the highest
  total loop resistance. A nominal sum sits between the two and can be
  comfortably inside a window that both corners fall outside.
* A violated corner has a constructive answer. Requiring the low corner to
  reach the floor sets a lowest admissible drive voltage; requiring the
  high corner to stay under the ceiling sets a highest admissible one.
  When the first exceeds the second, no drive voltage closes the case and
  the resistance spread itself, not the supply, is the thing to tighten.

Stdlib only, offline, deterministic. Arithmetic is restricted to the four
basic operations so a corner current is reproduced bit for bit on any
platform; the window comparisons still run through a named tolerance so an
exact-equality case does not turn on the last bit.
"""

import math

# Named tolerance absorbing representation error in a current comparison.
# It is NOT an engineering allowance: the specified window is never widened.
CURRENT_EPS = 1e-9

LOW_CORNER = "low-current-corner"
HIGH_CORNER = "high-current-corner"
CORNERS = (LOW_CORNER, HIGH_CORNER)

DEFAULT_INTERFACE_SPEC = {
    "min_firing_current_a": 3.5,
    "max_firing_current_a": 8.0,
}


def _require_number(value, label):
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise ValueError("%s must be a real number, got %r" % (label, value))
    if math.isnan(value) or math.isinf(value):
        raise ValueError("%s must be finite, got %r" % (label, value))
    return float(value)


def _require_text(value, label):
    if not isinstance(value, str) or not value.strip():
        raise ValueError("%s must be a non-empty string, got %r" % (label, value))
    return value


def _at_least(value, floor_value):
    """True when value reaches floor_value, absorbing representation error."""
    return value >= floor_value or math.isclose(
        value, floor_value, rel_tol=0.0, abs_tol=CURRENT_EPS
    )


def _at_most(value, ceiling_value):
    """True when value stays under ceiling_value, absorbing representation error."""
    return value <= ceiling_value or math.isclose(
        value, ceiling_value, rel_tol=0.0, abs_tol=CURRENT_EPS
    )


def resolve_spec(overrides=None):
    """Merge caller overrides onto the standard interface current window."""
    spec = dict(DEFAULT_INTERFACE_SPEC)
    if overrides is None:
        return spec
    if not isinstance(overrides, dict):
        raise ValueError("spec overrides must be a mapping, got %r" % (overrides,))
    for key, value in overrides.items():
        if key not in DEFAULT_INTERFACE_SPEC:
            raise ValueError("unrecognized interface specification key %r" % (key,))
        number = _require_number(value, "spec %r" % key)
        if number <= 0.0:
            raise ValueError("spec %r must be positive, got %r" % (key, value))
        spec[key] = number
    if spec["min_firing_current_a"] >= spec["max_firing_current_a"]:
        raise ValueError(
            "firing current window is empty: floor %r is not below ceiling %r"
            % (spec["min_firing_current_a"], spec["max_firing_current_a"])
        )
    return spec


def resistance_band(band, label):
    """Validate a (minimum, maximum) resistance spread in ohm."""
    if not isinstance(band, dict):
        raise ValueError("%s must be a mapping, got %r" % (label, band))
    low = _require_number(band.get("min_ohm"), "%s 'min_ohm'" % label)
    high = _require_number(band.get("max_ohm"), "%s 'max_ohm'" % label)
    if low < 0.0:
        raise ValueError("%s minimum must not be negative, got %r" % (label, low))
    if high < low:
        raise ValueError(
            "%s maximum %r is below its minimum %r" % (label, high, low)
        )
    return low, high


def loop_resistance(actuator_ohm, harness_ohm, source_ohm):
    """Total resistance the firing current sees around the loop."""
    actuator_ohm = _require_number(actuator_ohm, "actuator resistance")
    harness_ohm = _require_number(harness_ohm, "harness resistance")
    source_ohm = _require_number(source_ohm, "source resistance")
    for label, value in (
        ("actuator resistance", actuator_ohm),
        ("harness resistance", harness_ohm),
        ("source resistance", source_ohm),
    ):
        if value < 0.0:
            raise ValueError("%s must not be negative, got %r" % (label, value))
    total = actuator_ohm + harness_ohm + source_ohm
    if total <= 0.0:
        raise ValueError("total loop resistance must be positive, got %r" % (total,))
    return total


def firing_current(drive_voltage_v, loop_ohm):
    """Current delivered into a loop of this resistance at this drive voltage."""
    drive_voltage_v = _require_number(drive_voltage_v, "drive voltage")
    loop_ohm = _require_number(loop_ohm, "loop resistance")
    if drive_voltage_v <= 0.0:
        raise ValueError("drive voltage must be positive, got %r" % (drive_voltage_v,))
    if loop_ohm <= 0.0:
        raise ValueError("loop resistance must be positive, got %r" % (loop_ohm,))
    return drive_voltage_v / loop_ohm


def _drive_band(line):
    low = _require_number(line.get("drive_voltage_min_v"), "'drive_voltage_min_v'")
    high = _require_number(line.get("drive_voltage_max_v"), "'drive_voltage_max_v'")
    if low <= 0.0:
        raise ValueError("drive voltage minimum must be positive, got %r" % (low,))
    if high < low:
        raise ValueError(
            "drive voltage maximum %r is below its minimum %r" % (high, low)
        )
    return low, high


def corner_currents(line):
    """The two currents a compatibility statement has to be taken on."""
    if not isinstance(line, dict):
        raise ValueError("line must be a mapping, got %r" % (line,))
    v_low, v_high = _drive_band(line)
    a_low, a_high = resistance_band(line.get("actuator_resistance"), "actuator_resistance")
    h_low, h_high = resistance_band(line.get("harness_resistance"), "harness_resistance")
    s_low, s_high = resistance_band(line.get("source_resistance"), "source_resistance")
    loop_min = loop_resistance(a_low, h_low, s_low)
    loop_max = loop_resistance(a_high, h_high, s_high)
    return {
        "loop_resistance_min_ohm": loop_min,
        "loop_resistance_max_ohm": loop_max,
        "drive_voltage_min_v": v_low,
        "drive_voltage_max_v": v_high,
        HIGH_CORNER: firing_current(v_high, loop_min),
        LOW_CORNER: firing_current(v_low, loop_max),
    }


def admissible_drive_band(corners, spec=None):
    """Drive voltage band that would put both corners inside the window."""
    if not isinstance(corners, dict):
        raise ValueError("corners must be a mapping, got %r" % (corners,))
    for key in ("loop_resistance_min_ohm", "loop_resistance_max_ohm"):
        if key not in corners:
            raise ValueError("corners missing required key %r" % (key,))
    resolved = resolve_spec(spec)
    lowest = resolved["min_firing_current_a"] * corners["loop_resistance_max_ohm"]
    highest = resolved["max_firing_current_a"] * corners["loop_resistance_min_ohm"]
    return {
        "lowest_admissible_drive_v": lowest,
        "highest_admissible_drive_v": highest,
        "feasible": _at_most(lowest, highest),
    }


def evaluate_line(line, spec=None):
    """Compatibility verdict for one actuator drive line."""
    resolved = resolve_spec(spec)
    if not isinstance(line, dict):
        raise ValueError("line must be a mapping, got %r" % (line,))
    name = _require_text(line.get("name"), "line 'name'")
    corners = corner_currents(line)
    high_current = corners[HIGH_CORNER]
    low_current = corners[LOW_CORNER]
    floor_ok = _at_least(low_current, resolved["min_firing_current_a"])
    ceiling_ok = _at_most(high_current, resolved["max_firing_current_a"])
    violated = []
    if not floor_ok:
        violated.append(LOW_CORNER)
    if not ceiling_ok:
        violated.append(HIGH_CORNER)
    band = admissible_drive_band(corners, spec)
    result = dict(corners)
    result.update(
        {
            "name": name,
            "min_firing_current_a": resolved["min_firing_current_a"],
            "max_firing_current_a": resolved["max_firing_current_a"],
            "floor_shortfall_a": max(
                0.0, resolved["min_firing_current_a"] - low_current
            ),
            "ceiling_excess_a": max(
                0.0, high_current - resolved["max_firing_current_a"]
            ),
            "violated_corners": violated,
            "compatible": not violated,
            "admissible_drive_band": band,
        }
    )
    return result


def resistance_spread_is_admissible(line, spec=None):
    """True when some drive voltage exists that satisfies both corners."""
    return admissible_drive_band(corner_currents(line), spec)["feasible"]


def worst_line(results):
    """The line holding the least current headroom inside the window."""
    if not isinstance(results, (list, tuple)) or not results:
        raise ValueError("results must be a non-empty sequence")
    worst = results[0]
    worst_headroom = line_headroom_a(worst)
    for result in results[1:]:
        headroom = line_headroom_a(result)
        if headroom < worst_headroom:
            worst, worst_headroom = result, headroom
    return worst


def line_headroom_a(result):
    """Smallest distance in ampere from either corner to its own limit."""
    if not isinstance(result, dict):
        raise ValueError("result must be a mapping, got %r" % (result,))
    for key in (LOW_CORNER, HIGH_CORNER, "min_firing_current_a", "max_firing_current_a"):
        if key not in result:
            raise ValueError("result missing required key %r" % (key,))
    below = result[LOW_CORNER] - result["min_firing_current_a"]
    above = result["max_firing_current_a"] - result[HIGH_CORNER]
    return below if below < above else above


def compatibility_status(findings):
    """Gate token for the finding list of one compatibility assessment."""
    if not isinstance(findings, (list, tuple)):
        raise ValueError("findings must be a sequence, got %r" % (findings,))
    return "interface-compatible" if not findings else "hold-interface-compatibility"


def evaluate_interface(config):
    """End-to-end clause 5.4.1 compatibility assessment for a set of lines."""
    if not isinstance(config, dict):
        raise ValueError("config must be a mapping")
    if "lines" not in config:
        raise ValueError("config missing required key 'lines'")
    lines = config["lines"]
    if not isinstance(lines, (list, tuple)) or not lines:
        raise ValueError("lines must be a non-empty sequence")
    spec = resolve_spec(config.get("spec"))
    results = [evaluate_line(line, config.get("spec")) for line in lines]
    names = [result["name"] for result in results]
    if len(set(names)) != len(names):
        raise ValueError("line names must be unique, got %r" % (names,))

    findings = []
    for result in results:
        if LOW_CORNER in result["violated_corners"]:
            findings.append(
                "%s falls %.6f A short of the firing current floor at its low corner"
                % (result["name"], result["floor_shortfall_a"])
            )
        if HIGH_CORNER in result["violated_corners"]:
            findings.append(
                "%s exceeds the firing current ceiling by %.6f A at its high corner"
                % (result["name"], result["ceiling_excess_a"])
            )
        if not result["admissible_drive_band"]["feasible"]:
            findings.append(
                "%s has a resistance spread no drive voltage can satisfy"
                % (result["name"],)
            )
    worst = worst_line(results)
    return {
        "spec": spec,
        "lines": results,
        "worst_line": worst,
        "worst_line_headroom_a": line_headroom_a(worst),
        "findings": findings,
        "status": compatibility_status(findings),
        "compatible": not findings,
    }
