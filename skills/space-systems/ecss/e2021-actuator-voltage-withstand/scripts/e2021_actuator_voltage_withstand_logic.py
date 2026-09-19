#!/usr/bin/env python3
"""Actuator input-voltage withstand on either drive side (ECSS-E-ST-20-21C 5.6.2).

Offline, deterministic, standard library only. The ECSS clause is cited as
the anchor; the procedure below is a paraphrase into implementable logic.

Model
-----
A dual-redundant actuator is reachable through a nominal side and a
redundant side. The clause duty is that the actuator tolerates the full
input voltage arriving through either one, so the assessment is run per
side and never on a single "bus voltage" figure:

* the worst-case source voltage is the bus upper envelope, not the bus
  nominal, because withstand is a maximum-stress case;
* the terminal voltage each side imposes follows from the divider formed
  by that side's line resistance and the actuator resistance, so the
  worst case takes the SMALLEST credible line resistance -- a large drop
  protects the actuator, and assuming it is unconservative;
* the two sides are rarely symmetric (harness length, slip rings, series
  switches), so the governing side is the one with the lower drop;
* cross-strapping adds a third case the per-side view misses. With both
  sides energised the two line resistances appear in parallel, the drop
  falls again and the terminal voltage rises above either single-side
  value, which is the case that actually breaks a part sized on one side.

Current, dissipation and the commanded duration are graded against the
declared ratings alongside the voltage, because an actuator that holds
off the voltage can still fail on continuous power.
"""

import math

# The two drive sides the clause names; both must be declared.
REQUIRED_SIDES = ("nominal", "redundant")
# Drive sides differing by more than this in terminal voltage are reported.
ASYMMETRY_RATIO = 1.05
# Comparisons absorb representation error only; ratings are never widened.
REL_TOL = 1e-12
ABS_TOL = 1e-18

_REQUIRED_KEYS = (
    "bus_nominal_v",
    "actuator_resistance_ohm",
    "sides",
    "rated_voltage_v",
)
_OPTIONAL_KEYS = (
    "bus_upper_tolerance",
    "transient_v",
    "rated_current_a",
    "rated_power_w",
    "rated_duration_s",
    "command_duration_s",
    "check_dual_energisation",
)


def _as_float(name, value):
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise ValueError("%s must be a real number, got %r" % (name, value))
    out = float(value)
    if math.isnan(out) or math.isinf(out):
        raise ValueError("%s must be finite, got %r" % (name, value))
    return out


def _positive(name, value):
    out = _as_float(name, value)
    if out <= 0.0:
        raise ValueError("%s must be > 0, got %g" % (name, out))
    return out


def _non_negative(name, value):
    out = _as_float(name, value)
    if out < 0.0:
        raise ValueError("%s must be >= 0, got %g" % (name, out))
    return out


def within_limit(value, limit):
    """True when ``value`` is at or under ``limit``.

    The tolerance absorbs representation error carried by a divider or a
    product of floats; the declared rating itself is untouched.
    """
    value = _as_float("value", value)
    limit = _as_float("limit", limit)
    return value < limit or math.isclose(
        value, limit, rel_tol=REL_TOL, abs_tol=ABS_TOL
    )


def worst_case_source_voltage_v(bus_nominal_v, upper_tolerance=0.0, transient_v=0.0):
    """Highest voltage the bus can present, tolerance and transient included."""
    bus = _positive("bus_nominal_v", bus_nominal_v)
    tolerance = _non_negative("upper_tolerance", upper_tolerance)
    if tolerance >= 1.0:
        raise ValueError(
            "upper_tolerance is a fraction of the nominal bus, got %g" % tolerance
        )
    transient = _non_negative("transient_v", transient_v)
    return bus * (1.0 + tolerance) + transient


def terminal_voltage_v(source_voltage_v, line_resistance_ohm, actuator_resistance_ohm):
    """Voltage reaching the actuator terminals through one drive path."""
    source = _positive("source_voltage_v", source_voltage_v)
    line = _non_negative("line_resistance_ohm", line_resistance_ohm)
    actuator = _positive("actuator_resistance_ohm", actuator_resistance_ohm)
    return source * actuator / (actuator + line)


def parallel_resistance_ohm(first_ohm, second_ohm):
    """Two drive paths energised together present their parallel resistance."""
    first = _non_negative("first_ohm", first_ohm)
    second = _non_negative("second_ohm", second_ohm)
    total = first + second
    if total <= 0.0:
        return 0.0
    return first * second / total


def actuator_current_a(terminal_v, actuator_resistance_ohm):
    """Current drawn by the actuator at a given terminal voltage."""
    terminal = _non_negative("terminal_v", terminal_v)
    actuator = _positive("actuator_resistance_ohm", actuator_resistance_ohm)
    return terminal / actuator


def dissipation_w(current_a, actuator_resistance_ohm):
    """Steady dissipation in the actuator winding."""
    current = _non_negative("current_a", current_a)
    actuator = _positive("actuator_resistance_ohm", actuator_resistance_ohm)
    return current * current * actuator


def withstand_margin_ratio(rating, applied):
    """How much of the rating is left: 1.0 means exactly at the rating."""
    rated = _positive("rating", rating)
    stress = _positive("applied", applied)
    return rated / stress


def categorize_withstand(applied, rating):
    """Name the stress regime of one applied value against its rating."""
    stress = _non_negative("applied", applied)
    rated = _positive("rating", rating)
    if math.isclose(stress, rated, rel_tol=REL_TOL, abs_tol=ABS_TOL):
        return "at-rating"
    if stress < rated:
        return "within-rating"
    return "over-rating"


def _validate_sides(sides):
    if not isinstance(sides, dict):
        raise ValueError("sides must be a mapping of side name to drive data")
    missing = [name for name in REQUIRED_SIDES if name not in sides]
    if missing:
        raise ValueError(
            "sides must declare both drive paths, missing: %s" % ", ".join(missing)
        )
    extra = sorted(set(sides) - set(REQUIRED_SIDES))
    if extra:
        raise ValueError("unknown drive side(s): %s" % ", ".join(extra))
    resolved = {}
    for name in REQUIRED_SIDES:
        entry = sides[name]
        if not isinstance(entry, dict):
            raise ValueError("side %r must be a mapping" % name)
        unknown = sorted(set(entry) - {"line_resistance_ohm"})
        if unknown:
            raise ValueError(
                "side %r has unknown keys: %s" % (name, ", ".join(unknown))
            )
        if "line_resistance_ohm" not in entry:
            raise ValueError("side %r must declare line_resistance_ohm" % name)
        resolved[name] = _non_negative(
            "sides[%s].line_resistance_ohm" % name, entry["line_resistance_ohm"]
        )
    return resolved


def evaluate_actuator_withstand(spec):
    """Full clause 5.6.2 withstand assessment of one dual-fed actuator.

    Returns the per-side terminal voltage, current and dissipation, the
    governing side, the both-sides-energised case, the findings and the
    verdict.
    """
    if not isinstance(spec, dict):
        raise ValueError("spec must be a mapping of bus, actuator and side data")
    known = set(_REQUIRED_KEYS) | set(_OPTIONAL_KEYS)
    unknown = sorted(set(spec) - known)
    if unknown:
        raise ValueError("unknown spec keys: %s" % ", ".join(unknown))
    missing = [key for key in _REQUIRED_KEYS if key not in spec]
    if missing:
        raise ValueError("spec missing required keys: %s" % ", ".join(missing))

    actuator_ohm = _positive("actuator_resistance_ohm", spec["actuator_resistance_ohm"])
    rated_voltage = _positive("rated_voltage_v", spec["rated_voltage_v"])
    source = worst_case_source_voltage_v(
        spec["bus_nominal_v"],
        spec.get("bus_upper_tolerance", 0.0),
        spec.get("transient_v", 0.0),
    )
    line_ohm = _validate_sides(spec["sides"])

    findings = []
    per_side = {}
    for name in REQUIRED_SIDES:
        terminal = terminal_voltage_v(source, line_ohm[name], actuator_ohm)
        current = actuator_current_a(terminal, actuator_ohm)
        power = dissipation_w(current, actuator_ohm)
        per_side[name] = {
            "line_resistance_ohm": line_ohm[name],
            "terminal_voltage_v": terminal,
            "current_a": current,
            "dissipation_w": power,
            "withstand_category": categorize_withstand(terminal, rated_voltage),
            "voltage_margin_ratio": withstand_margin_ratio(rated_voltage, terminal),
        }
        if not within_limit(terminal, rated_voltage):
            findings.append(
                {
                    "code": "terminal-voltage-over-rating",
                    "side": name,
                    "terminal_voltage_v": terminal,
                    "rated_voltage_v": rated_voltage,
                    "detail": "%s side imposes %.3f V on a %.3f V part"
                    % (name, terminal, rated_voltage),
                }
            )
        if "rated_current_a" in spec:
            rated_current = _positive("rated_current_a", spec["rated_current_a"])
            if not within_limit(current, rated_current):
                findings.append(
                    {
                        "code": "current-over-rating",
                        "side": name,
                        "current_a": current,
                        "rated_current_a": rated_current,
                        "detail": "%s side draws %.3f A against a %.3f A rating"
                        % (name, current, rated_current),
                    }
                )
        if "rated_power_w" in spec:
            rated_power = _positive("rated_power_w", spec["rated_power_w"])
            if not within_limit(power, rated_power):
                findings.append(
                    {
                        "code": "dissipation-over-rating",
                        "side": name,
                        "dissipation_w": power,
                        "rated_power_w": rated_power,
                        "detail": "%s side dissipates %.3f W against a %.3f W rating"
                        % (name, power, rated_power),
                    }
                )

    governing = max(
        REQUIRED_SIDES, key=lambda name: per_side[name]["terminal_voltage_v"]
    )
    weakest = min(
        REQUIRED_SIDES, key=lambda name: per_side[name]["terminal_voltage_v"]
    )
    asymmetry = (
        per_side[governing]["terminal_voltage_v"]
        / per_side[weakest]["terminal_voltage_v"]
    )
    if asymmetry > ASYMMETRY_RATIO:
        findings.append(
            {
                "code": "drive-side-asymmetry",
                "governing_side": governing,
                "asymmetry_ratio": asymmetry,
                "detail": "the two sides differ by %.1f %% in terminal voltage, so a "
                "single-side qualification does not cover both"
                % (100.0 * (asymmetry - 1.0)),
            }
        )

    dual = None
    if spec.get("check_dual_energisation", True):
        pair_ohm = parallel_resistance_ohm(
            line_ohm["nominal"], line_ohm["redundant"]
        )
        terminal = terminal_voltage_v(source, pair_ohm, actuator_ohm)
        current = actuator_current_a(terminal, actuator_ohm)
        dual = {
            "line_resistance_ohm": pair_ohm,
            "terminal_voltage_v": terminal,
            "current_a": current,
            "dissipation_w": dissipation_w(current, actuator_ohm),
            "withstand_category": categorize_withstand(terminal, rated_voltage),
        }
        if not within_limit(terminal, rated_voltage):
            findings.append(
                {
                    "code": "dual-side-voltage-over-rating",
                    "terminal_voltage_v": terminal,
                    "rated_voltage_v": rated_voltage,
                    "detail": "with both sides energised the drop halves and the "
                    "terminal sees %.3f V against a %.3f V rating"
                    % (terminal, rated_voltage),
                }
            )

    if "command_duration_s" in spec:
        commanded = _positive("command_duration_s", spec["command_duration_s"])
        if "rated_duration_s" not in spec:
            raise ValueError(
                "command_duration_s given without rated_duration_s: the commanded "
                "time cannot be graded against an undeclared withstand duration"
            )
        rated_duration = _positive("rated_duration_s", spec["rated_duration_s"])
        if not within_limit(commanded, rated_duration):
            findings.append(
                {
                    "code": "command-longer-than-rated-duration",
                    "command_duration_s": commanded,
                    "rated_duration_s": rated_duration,
                    "detail": "commanded for %.3f s against a %.3f s withstand time"
                    % (commanded, rated_duration),
                }
            )

    return {
        "source_voltage_v": source,
        "per_side": per_side,
        "governing_side": governing,
        "asymmetry_ratio": asymmetry,
        "dual_energisation": dual,
        "findings": findings,
        "compliant": not findings,
    }
