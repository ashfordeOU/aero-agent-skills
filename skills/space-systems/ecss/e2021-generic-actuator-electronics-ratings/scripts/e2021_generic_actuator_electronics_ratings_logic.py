#!/usr/bin/env python3
"""Generic actuator electronics output ratings under ECSS-E-ST-20-21C
clause 5.5.4.

Paraphrased, implementable procedure (no verbatim standard text):

* An actuator electronics meant to be reused across projects is
  recommended to carry an output power and an output current capability
  that a later actuator will still fit inside. Rating it to the loads of
  the first project is what makes the second project redesign it.
* Each load's demand is taken at its own worst corner: the lowest
  resistance it can present against the highest drive voltage the design
  permits. The nominal resistance and the nominal bus give a demand no
  qualification case ever exercises.
* Actuators that fire together are one demand, not several. The current
  a driver has to source is the sum over the simultaneously fired group,
  so the envelope is taken over groups and a salvo of two initiators
  outranks either of them alone.
* The margin is a design allowance applied once, at the envelope. Adding
  it per load and again at the envelope compounds it and buys hardware
  nobody asked for; leaving it out entirely rates the unit at exactly the
  demand it has already seen.
* A generic rating has a second condition beyond covering today's family:
  it is recommended to reach the generic capability figure, so the design
  stays reusable when the next actuator is heavier than any in hand.
* Each rating names the group that drove it, because that is the load to
  renegotiate when the rating turns out to be unaffordable.

Stdlib only, offline, deterministic. Arithmetic is restricted to the four
basic operations, and every rating comparison runs through a named
tolerance so a declared rating landing exactly on a requirement does not
turn on the last bit of a product.
"""

import math

# Named tolerance absorbing representation error in a rating comparison.
# It is NOT a design allowance: the declared margin is the only allowance.
RATING_EPS = 1e-9

OUTPUT_CURRENT = "output-current"
OUTPUT_POWER = "output-power"
RATED_QUANTITIES = (OUTPUT_CURRENT, OUTPUT_POWER)

DEFAULT_RATING_SPEC = {
    "design_margin_fraction": 0.25,
    "recommended_output_current_a": 10.0,
    "recommended_output_power_w": 200.0,
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
        value, floor_value, rel_tol=0.0, abs_tol=RATING_EPS
    )


def resolve_spec(overrides=None):
    """Merge caller overrides onto the recommended generic rating baseline."""
    spec = dict(DEFAULT_RATING_SPEC)
    if overrides is None:
        return spec
    if not isinstance(overrides, dict):
        raise ValueError("spec overrides must be a mapping, got %r" % (overrides,))
    for key, value in overrides.items():
        if key not in DEFAULT_RATING_SPEC:
            raise ValueError("unrecognized rating specification key %r" % (key,))
        number = _require_number(value, "spec %r" % key)
        if key == "design_margin_fraction":
            if number < 0.0:
                raise ValueError(
                    "design_margin_fraction must not be negative, got %r" % (value,)
                )
        elif number <= 0.0:
            raise ValueError("spec %r must be positive, got %r" % (key, value))
        spec[key] = number
    return spec


def load_demand(load):
    """Current and power one actuator load asks of the driver at its corner."""
    if not isinstance(load, dict):
        raise ValueError("load must be a mapping, got %r" % (load,))
    name = _require_text(load.get("name"), "load 'name'")
    group = _require_text(load.get("group", name), "load 'group'")
    resistance = _require_number(
        load.get("resistance_min_ohm"), "load %r minimum resistance" % name
    )
    voltage = _require_number(
        load.get("drive_voltage_max_v"), "load %r maximum drive voltage" % name
    )
    if resistance <= 0.0:
        raise ValueError(
            "load %r minimum resistance must be positive, got %r" % (name, resistance)
        )
    if voltage <= 0.0:
        raise ValueError(
            "load %r maximum drive voltage must be positive, got %r" % (name, voltage)
        )
    current = voltage / resistance
    return {
        "name": name,
        "group": group,
        "resistance_min_ohm": resistance,
        "drive_voltage_max_v": voltage,
        "current_a": current,
        "power_w": voltage * current,
    }


def group_demands(loads):
    """Demands summed over each simultaneously fired group."""
    if not isinstance(loads, (list, tuple)) or not loads:
        raise ValueError("loads must be a non-empty sequence")
    demands = [load_demand(load) for load in loads]
    names = [demand["name"] for demand in demands]
    if len(set(names)) != len(names):
        raise ValueError("load names must be unique, got %r" % (names,))
    grouped = {}
    for demand in demands:
        entry = grouped.setdefault(
            demand["group"], {"group": demand["group"], "members": [],
                              "current_a": 0.0, "power_w": 0.0}
        )
        entry["members"].append(demand["name"])
        entry["current_a"] += demand["current_a"]
        entry["power_w"] += demand["power_w"]
    return [grouped[key] for key in sorted(grouped)]


def family_envelope(loads):
    """Highest simultaneous current and power the load family can ask for."""
    groups = group_demands(loads)
    current_driver = groups[0]
    power_driver = groups[0]
    for entry in groups[1:]:
        if entry["current_a"] > current_driver["current_a"]:
            current_driver = entry
        if entry["power_w"] > power_driver["power_w"]:
            power_driver = entry
    return {
        "groups": groups,
        "envelope_current_a": current_driver["current_a"],
        "envelope_power_w": power_driver["power_w"],
        "current_sizing_group": current_driver["group"],
        "power_sizing_group": power_driver["group"],
    }


def apply_margin(value, margin_fraction):
    """Design allowance applied once, at the envelope."""
    value = _require_number(value, "envelope value")
    margin_fraction = _require_number(margin_fraction, "design margin fraction")
    if value < 0.0:
        raise ValueError("envelope value must not be negative, got %r" % (value,))
    if margin_fraction < 0.0:
        raise ValueError(
            "design margin fraction must not be negative, got %r" % (margin_fraction,)
        )
    return value * (1.0 + margin_fraction)


def grade_rating(declared, required, recommended):
    """Grade one declared rating against the family and the generic baseline."""
    declared = _require_number(declared, "declared rating")
    required = _require_number(required, "required rating")
    recommended = _require_number(recommended, "recommended rating")
    if declared <= 0.0:
        raise ValueError("declared rating must be positive, got %r" % (declared,))
    covers_family = _at_least(declared, required)
    meets_baseline = _at_least(declared, recommended)
    return {
        "declared": declared,
        "required": required,
        "recommended": recommended,
        "covers_family": covers_family,
        "meets_generic_baseline": meets_baseline,
        "family_shortfall": max(0.0, required - declared),
        "baseline_shortfall": max(0.0, recommended - declared),
        "adequate": covers_family and meets_baseline,
    }


def rating_status(findings):
    """Gate token for the finding list of one rating assessment."""
    if not isinstance(findings, (list, tuple)):
        raise ValueError("findings must be a sequence, got %r" % (findings,))
    return "generic-ratings-adequate" if not findings else "hold-generic-ratings"


def evaluate_ratings(config):
    """End-to-end clause 5.5.4 rating assessment for a reusable driver."""
    if not isinstance(config, dict):
        raise ValueError("config must be a mapping")
    if "loads" not in config:
        raise ValueError("config missing required key 'loads'")
    spec = resolve_spec(config.get("spec"))
    envelope = family_envelope(config["loads"])
    required_current = apply_margin(
        envelope["envelope_current_a"], spec["design_margin_fraction"]
    )
    required_power = apply_margin(
        envelope["envelope_power_w"], spec["design_margin_fraction"]
    )
    declared_current = config.get("declared_output_current_a", required_current)
    declared_power = config.get("declared_output_power_w", required_power)
    current_grade = grade_rating(
        declared_current, required_current, spec["recommended_output_current_a"]
    )
    power_grade = grade_rating(
        declared_power, required_power, spec["recommended_output_power_w"]
    )

    findings = []
    if not current_grade["covers_family"]:
        findings.append(
            "declared output current %.6f A is %.6f A short of the %s group demand with margin"
            % (
                current_grade["declared"],
                current_grade["family_shortfall"],
                envelope["current_sizing_group"],
            )
        )
    if not current_grade["meets_generic_baseline"]:
        findings.append(
            "declared output current %.6f A is below the recommended generic capability"
            % (current_grade["declared"],)
        )
    if not power_grade["covers_family"]:
        findings.append(
            "declared output power %.6f W is %.6f W short of the %s group demand with margin"
            % (
                power_grade["declared"],
                power_grade["family_shortfall"],
                envelope["power_sizing_group"],
            )
        )
    if not power_grade["meets_generic_baseline"]:
        findings.append(
            "declared output power %.6f W is below the recommended generic capability"
            % (power_grade["declared"],)
        )

    return {
        "spec": spec,
        "envelope": envelope,
        OUTPUT_CURRENT: current_grade,
        OUTPUT_POWER: power_grade,
        "current_sizing_group": envelope["current_sizing_group"],
        "power_sizing_group": envelope["power_sizing_group"],
        "findings": findings,
        "status": rating_status(findings),
        "adequate": not findings,
    }
