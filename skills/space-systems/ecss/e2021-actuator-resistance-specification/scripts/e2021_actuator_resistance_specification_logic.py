#!/usr/bin/env python3
"""Actuator resistance specification under ECSS-E-ST-20-21C clause 5.6.1.

Paraphrased, implementable procedure (no verbatim standard text):

* What has to be stated for an actuator is the highest resistance it can
  present, and it has to be stated across the whole operating temperature
  and condition range rather than at one convenient point.
* The highest resistance is at one end of the temperature range, and
  which end depends on the sign of the temperature coefficient. A
  positive coefficient puts it at the hot end; a negative one puts it at
  the cold end, which is the case a hot-end-only measurement misses
  entirely.
* Temperature is not the only contributor. The build tolerance of the
  element, the allowance for ageing over the mission, and the contact and
  lead resistance the interface adds all sit on top, and the last two are
  absolute rather than proportional so they matter most on a
  low-resistance actuator.
* The stated maximum has to bound that stack. A declaration that repeats
  the reference value is a datasheet number that has had no stack applied
  to it at all, and it is reported as such rather than merely failing by
  a small amount.
* The declaration also carries a range, and a range narrower than the
  operating range does not cover the mission. The firing current is
  computed from this maximum, so a resistance stated over the wrong range
  propagates straight into an interface that was never verified.

Stdlib only, offline, deterministic. Arithmetic is restricted to the four
basic operations, and the bounding comparison runs through a named
tolerance so a declaration landing exactly on the computed maximum does
not turn on the last bit of a product.
"""

import math

# Named tolerance absorbing representation error in a resistance comparison.
# It is NOT an engineering allowance: no declared maximum is relaxed by it.
RESISTANCE_EPS = 1e-9

HOT_END = "hot-end"
COLD_END = "cold-end"
WORST_CASE_ENDS = (HOT_END, COLD_END)

DEFAULT_RESISTANCE_SPEC = {
    "build_tolerance_fraction": 0.05,
    "ageing_allowance_fraction": 0.02,
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
        value, floor_value, rel_tol=0.0, abs_tol=RESISTANCE_EPS
    )


def resolve_spec(overrides=None):
    """Merge caller overrides onto the standard resistance stack allowances."""
    spec = dict(DEFAULT_RESISTANCE_SPEC)
    if overrides is None:
        return spec
    if not isinstance(overrides, dict):
        raise ValueError("spec overrides must be a mapping, got %r" % (overrides,))
    for key, value in overrides.items():
        if key not in DEFAULT_RESISTANCE_SPEC:
            raise ValueError("unrecognized resistance specification key %r" % (key,))
        number = _require_number(value, "spec %r" % key)
        if number < 0.0:
            raise ValueError("spec %r must not be negative, got %r" % (key, value))
        spec[key] = number
    return spec


def resistance_at_temperature(
    reference_ohm, reference_temperature_c, coefficient_per_k, temperature_c
):
    """Element resistance at one temperature, from its reference point."""
    reference_ohm = _require_number(reference_ohm, "reference resistance")
    reference_temperature_c = _require_number(
        reference_temperature_c, "reference temperature"
    )
    coefficient_per_k = _require_number(
        coefficient_per_k, "temperature coefficient"
    )
    temperature_c = _require_number(temperature_c, "temperature")
    if reference_ohm <= 0.0:
        raise ValueError(
            "reference resistance must be positive, got %r" % (reference_ohm,)
        )
    value = reference_ohm * (
        1.0 + coefficient_per_k * (temperature_c - reference_temperature_c)
    )
    if value <= 0.0:
        raise ValueError(
            "temperature coefficient drives the resistance to %r at %r degC; "
            "the linear model does not hold over this range"
            % (value, temperature_c)
        )
    return value


def worst_case_end(coefficient_per_k):
    """Which end of the operating range carries the highest resistance."""
    coefficient_per_k = _require_number(
        coefficient_per_k, "temperature coefficient"
    )
    return HOT_END if coefficient_per_k >= 0.0 else COLD_END


def operating_range(actuator):
    """Validate and return the operating temperature range in degrees Celsius."""
    if not isinstance(actuator, dict):
        raise ValueError("actuator must be a mapping, got %r" % (actuator,))
    low = _require_number(
        actuator.get("operating_temperature_min_c"), "'operating_temperature_min_c'"
    )
    high = _require_number(
        actuator.get("operating_temperature_max_c"), "'operating_temperature_max_c'"
    )
    if high < low:
        raise ValueError(
            "operating temperature maximum %r is below its minimum %r" % (high, low)
        )
    return low, high


def range_coverage_gaps(actuator):
    """Ends of the operating range the declared range fails to reach."""
    op_low, op_high = operating_range(actuator)
    declared_low = actuator.get("declared_temperature_min_c", op_low)
    declared_high = actuator.get("declared_temperature_max_c", op_high)
    declared_low = _require_number(declared_low, "'declared_temperature_min_c'")
    declared_high = _require_number(declared_high, "'declared_temperature_max_c'")
    if declared_high < declared_low:
        raise ValueError(
            "declared temperature maximum %r is below its minimum %r"
            % (declared_high, declared_low)
        )
    gaps = []
    if not _at_least(op_low, declared_low):
        gaps.append(COLD_END)
    if not _at_least(declared_high, op_high):
        gaps.append(HOT_END)
    return gaps


def resistance_adders_ohm(actuator):
    """Absolute contributions the interface adds to the element resistance."""
    if not isinstance(actuator, dict):
        raise ValueError("actuator must be a mapping, got %r" % (actuator,))
    total = 0.0
    for key in ("contact_resistance_ohm", "lead_resistance_ohm"):
        value = _require_number(actuator.get(key, 0.0), "'%s'" % key)
        if value < 0.0:
            raise ValueError("%r must not be negative, got %r" % (key, value))
        total += value
    return total


def maximum_resistance_ohm(actuator, spec=None):
    """Highest resistance across the full operating temperature and conditions."""
    resolved = resolve_spec(spec)
    op_low, op_high = operating_range(actuator)
    reference = _require_number(
        actuator.get("reference_resistance_ohm"), "'reference_resistance_ohm'"
    )
    reference_temperature = _require_number(
        actuator.get("reference_temperature_c"), "'reference_temperature_c'"
    )
    coefficient = _require_number(
        actuator.get("temperature_coefficient_per_k"),
        "'temperature_coefficient_per_k'",
    )
    end = worst_case_end(coefficient)
    temperature = op_high if end == HOT_END else op_low
    at_temperature = resistance_at_temperature(
        reference, reference_temperature, coefficient, temperature
    )
    stacked = (
        at_temperature
        * (1.0 + resolved["build_tolerance_fraction"])
        * (1.0 + resolved["ageing_allowance_fraction"])
    )
    return {
        "worst_case_end": end,
        "worst_case_temperature_c": temperature,
        "reference_resistance_ohm": reference,
        "resistance_at_worst_case_ohm": at_temperature,
        "stacked_resistance_ohm": stacked,
        "adders_ohm": resistance_adders_ohm(actuator),
        "maximum_resistance_ohm": stacked + resistance_adders_ohm(actuator),
    }


def looks_like_the_reference_value(declared_ohm, reference_ohm):
    """True when a declaration simply repeats the reference resistance."""
    declared_ohm = _require_number(declared_ohm, "declared maximum")
    reference_ohm = _require_number(reference_ohm, "reference resistance")
    return math.isclose(declared_ohm, reference_ohm, rel_tol=1e-9, abs_tol=0.0)


def evaluate_actuator(actuator, spec=None):
    """Specification verdict for one actuator resistance declaration."""
    if not isinstance(actuator, dict):
        raise ValueError("actuator must be a mapping, got %r" % (actuator,))
    name = _require_text(actuator.get("name"), "actuator 'name'")
    computed = maximum_resistance_ohm(actuator, spec)
    declared = _require_number(
        actuator.get("declared_max_resistance_ohm", computed["maximum_resistance_ohm"]),
        "actuator %r declared maximum resistance" % name,
    )
    if declared <= 0.0:
        raise ValueError(
            "actuator %r declared maximum must be positive, got %r" % (name, declared)
        )
    coefficient = _require_number(
        actuator.get("temperature_coefficient_per_k"),
        "'temperature_coefficient_per_k'",
    )
    bounds = _at_least(declared, computed["maximum_resistance_ohm"])
    nominal_only = looks_like_the_reference_value(
        declared, computed["reference_resistance_ohm"]
    ) and coefficient != 0.0
    gaps = range_coverage_gaps(actuator)
    result = dict(computed)
    result.update(
        {
            "name": name,
            "declared_max_resistance_ohm": declared,
            "bounds_worst_case": bounds,
            "shortfall_ohm": max(0.0, computed["maximum_resistance_ohm"] - declared),
            "margin_ohm": declared - computed["maximum_resistance_ohm"],
            "stated_at_nominal_only": nominal_only,
            "range_coverage_gaps": gaps,
            "specified": bounds and not nominal_only and not gaps,
        }
    )
    return result


def tightest_actuator(results):
    """The declaration holding the least margin over its own worst case."""
    if not isinstance(results, (list, tuple)) or not results:
        raise ValueError("results must be a non-empty sequence")
    tightest = results[0]
    for result in results[1:]:
        if result["margin_ohm"] < tightest["margin_ohm"]:
            tightest = result
    return tightest


def specification_status(findings):
    """Gate token for the finding list of one resistance specification."""
    if not isinstance(findings, (list, tuple)):
        raise ValueError("findings must be a sequence, got %r" % (findings,))
    return "resistance-specified" if not findings else "hold-resistance-specification"


def evaluate_specification(config):
    """End-to-end clause 5.6.1 assessment over a set of actuator declarations."""
    if not isinstance(config, dict):
        raise ValueError("config must be a mapping")
    if "actuators" not in config:
        raise ValueError("config missing required key 'actuators'")
    actuators = config["actuators"]
    if not isinstance(actuators, (list, tuple)) or not actuators:
        raise ValueError("actuators must be a non-empty sequence")
    spec = resolve_spec(config.get("spec"))
    results = [evaluate_actuator(a, config.get("spec")) for a in actuators]
    names = [result["name"] for result in results]
    if len(set(names)) != len(names):
        raise ValueError("actuator names must be unique, got %r" % (names,))

    findings = []
    for result in results:
        if not result["bounds_worst_case"]:
            findings.append(
                "%s declares %.6f ohm against a worst case of %.6f ohm"
                % (
                    result["name"],
                    result["declared_max_resistance_ohm"],
                    result["maximum_resistance_ohm"],
                )
            )
        if result["stated_at_nominal_only"]:
            findings.append(
                "%s repeats its reference resistance with no temperature or condition stack"
                % (result["name"],)
            )
        for gap in result["range_coverage_gaps"]:
            findings.append(
                "%s declares a range that does not reach the %s of its operating range"
                % (result["name"], gap)
            )
    tightest = tightest_actuator(results)
    return {
        "spec": spec,
        "actuators": results,
        "tightest_actuator": tightest,
        "tightest_margin_ohm": tightest["margin_ohm"],
        "findings": findings,
        "status": specification_status(findings),
        "specified": not findings,
    }
