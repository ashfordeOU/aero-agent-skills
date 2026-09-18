#!/usr/bin/env python3
"""Interface loads and terminations for ECSS-E-ST-20-07C clause 5.2.6.7.

Paraphrased, implementable procedure (no verbatim standard text):

* Every interface of the tested unit is terminated during an electromagnetic
  measurement, either in the real hardware the interface drives in flight or
  in an equivalent load that presents the same electrical termination to the
  interface. An interface left open is not a benign simplification: the open
  changes the current distribution on the harness and therefore changes the
  quantity being measured.
* Each termination is categorized before the run: real hardware, equivalent
  load, or unterminated. A termination whose kind is not recognized has no
  defined standing on the bench and is rejected rather than assumed benign.
* An equivalent load is only equivalent inside a declared tolerance. Its
  impedance magnitude is compared with the impedance of the hardware it
  replaces as a relative deviation, and its reactive character is compared as
  a phase deviation; a resistor that matches in magnitude but not in phase is
  a different termination.
* A power interface carries an additional obligation: the simulated load must
  draw the flight load current within tolerance, and the load bank must be
  rated above the power it will dissipate by a stated margin, or the load
  drifts during the sweep and the measurement drifts with it.
* Any open termination or out-of-tolerance equivalent load holds the run: the
  measurement does not start until the finding list is empty.

Stdlib only, offline, deterministic.
"""

import math

# Named tolerance absorbing binary representation error in ohm, ampere,
# degree and percentage sums. It is NOT an engineering allowance: the
# termination tolerances themselves are never widened.
TERM_EPS = 1e-9

REAL_HARDWARE = "real-hardware"
EQUIVALENT_LOAD = "equivalent-load"
UNTERMINATED = "unterminated"

# Declared termination kind -> termination category.
TERMINATION_CATEGORY = {
    "flight-unit": REAL_HARDWARE,
    "flight-spare": REAL_HARDWARE,
    "qualification-model": REAL_HARDWARE,
    "load-simulator": EQUIVALENT_LOAD,
    "resistive-load-bank": EQUIVALENT_LOAD,
    "rf-termination": EQUIVALENT_LOAD,
    "data-bus-terminator": EQUIVALENT_LOAD,
    "open-circuit": UNTERMINATED,
    "left-disconnected": UNTERMINATED,
}

INTERFACE_KINDS = ("power", "signal", "rf", "data-bus")

DEFAULT_TERMINATION_SPEC = {
    "impedance_tolerance_percent": 10.0,
    "phase_tolerance_deg": 10.0,
    "load_current_tolerance_percent": 5.0,
    "load_rating_margin_factor": 1.25,
    "min_real_hardware_fraction": 0.0,
}


def _require_number(value, label):
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise ValueError("%s must be a real number, got %r" % (label, value))
    if math.isnan(value) or math.isinf(value):
        raise ValueError("%s must be finite, got %r" % (label, value))
    return float(value)


def _not_above(value, limit):
    """True when value does not exceed limit, absorbing representation error."""
    return value <= limit or math.isclose(value, limit, rel_tol=0.0, abs_tol=TERM_EPS)


def _at_least(value, floor_value):
    """True when value reaches floor_value, absorbing representation error."""
    return value >= floor_value or math.isclose(
        value, floor_value, rel_tol=0.0, abs_tol=TERM_EPS
    )


def resolve_spec(overrides=None):
    """Merge caller overrides onto the standard termination specification."""
    spec = dict(DEFAULT_TERMINATION_SPEC)
    if overrides is None:
        return spec
    if not isinstance(overrides, dict):
        raise ValueError("spec overrides must be a mapping, got %r" % (overrides,))
    for key, value in overrides.items():
        if key not in DEFAULT_TERMINATION_SPEC:
            raise ValueError("unrecognized termination specification key %r" % (key,))
        number = _require_number(value, "spec %r" % key)
        if number < 0.0:
            raise ValueError("spec %r must not be negative, got %r" % (key, value))
        spec[key] = number
    return spec


def categorize_termination(interface):
    """Map one interface record to its termination category."""
    if not isinstance(interface, dict):
        raise ValueError("interface must be a mapping, got %r" % (interface,))
    name = interface.get("name")
    if not isinstance(name, str) or not name.strip():
        raise ValueError("interface needs a non-empty 'name', got %r" % (name,))
    kind = interface.get("kind")
    if kind not in INTERFACE_KINDS:
        raise ValueError(
            "interface %r has unrecognized kind %r (expected one of %s)"
            % (name, kind, ", ".join(INTERFACE_KINDS))
        )
    termination = interface.get("termination")
    if termination not in TERMINATION_CATEGORY:
        raise ValueError(
            "interface %r has unrecognized termination %r (expected one of %s)"
            % (name, termination, ", ".join(sorted(TERMINATION_CATEGORY)))
        )
    return TERMINATION_CATEGORY[termination]


def categorize_interfaces(interfaces):
    """Categorize the whole interface list of one tested unit."""
    if not isinstance(interfaces, (list, tuple)) or not interfaces:
        raise ValueError("interfaces must be a non-empty sequence")
    categorized = []
    names = []
    for interface in interfaces:
        category = categorize_termination(interface)
        categorized.append(
            {
                "name": interface["name"],
                "kind": interface["kind"],
                "termination": interface["termination"],
                "category": category,
            }
        )
        names.append(interface["name"])
    if len(set(names)) != len(names):
        raise ValueError("interface names must be unique, got %r" % (names,))
    return categorized


def impedance_deviation_percent(actual_ohm, reference_ohm):
    """Relative deviation of an equivalent load from the hardware it replaces."""
    actual_ohm = _require_number(actual_ohm, "actual_ohm")
    reference_ohm = _require_number(reference_ohm, "reference_ohm")
    if reference_ohm <= 0.0:
        raise ValueError("reference_ohm must be positive, got %r" % (reference_ohm,))
    if actual_ohm <= 0.0:
        raise ValueError("actual_ohm must be positive, got %r" % (actual_ohm,))
    return abs(actual_ohm - reference_ohm) / reference_ohm * 100.0


def check_equivalent_load(interface, spec=None):
    """Check one equivalent load against the impedance it stands in for."""
    spec = resolve_spec(spec)
    if not isinstance(interface, dict):
        raise ValueError("interface must be a mapping, got %r" % (interface,))
    name = interface.get("name")
    if not isinstance(name, str) or not name.strip():
        raise ValueError("interface needs a non-empty 'name', got %r" % (name,))
    deviation = impedance_deviation_percent(
        interface.get("actual_impedance_ohm"), interface.get("reference_impedance_ohm")
    )
    reference_phase = _require_number(
        interface.get("reference_phase_deg", 0.0), "%s reference_phase_deg" % name
    )
    actual_phase = _require_number(
        interface.get("actual_phase_deg", 0.0), "%s actual_phase_deg" % name
    )
    for label, value in (("reference_phase_deg", reference_phase), ("actual_phase_deg", actual_phase)):
        if abs(value) > 90.0:
            raise ValueError(
                "%s %s must lie within +/-90 degrees, got %r" % (name, label, value)
            )
    phase_deviation = abs(actual_phase - reference_phase)
    return {
        "name": name,
        "impedance_deviation_percent": deviation,
        "impedance_tolerance_percent": spec["impedance_tolerance_percent"],
        "impedance_ok": _not_above(deviation, spec["impedance_tolerance_percent"]),
        "phase_deviation_deg": phase_deviation,
        "phase_tolerance_deg": spec["phase_tolerance_deg"],
        "phase_ok": _not_above(phase_deviation, spec["phase_tolerance_deg"]),
    }


def load_rating_margin(load_rating_w, dissipated_w):
    """Ratio of the rating of a load bank to the power it must dissipate."""
    load_rating_w = _require_number(load_rating_w, "load_rating_w")
    dissipated_w = _require_number(dissipated_w, "dissipated_w")
    if load_rating_w <= 0.0:
        raise ValueError("load_rating_w must be positive, got %r" % (load_rating_w,))
    if dissipated_w <= 0.0:
        raise ValueError("dissipated_w must be positive, got %r" % (dissipated_w,))
    return load_rating_w / dissipated_w


def check_power_interface(interface, spec=None):
    """Check a simulated power load for current fidelity and thermal rating."""
    spec = resolve_spec(spec)
    if not isinstance(interface, dict):
        raise ValueError("interface must be a mapping, got %r" % (interface,))
    name = interface.get("name")
    if not isinstance(name, str) or not name.strip():
        raise ValueError("interface needs a non-empty 'name', got %r" % (name,))
    flight = _require_number(
        interface.get("flight_load_current_a"), "%s flight_load_current_a" % name
    )
    simulated = _require_number(
        interface.get("simulated_load_current_a"), "%s simulated_load_current_a" % name
    )
    voltage = _require_number(interface.get("interface_voltage_v"), "%s interface_voltage_v" % name)
    rating = _require_number(interface.get("load_rating_w"), "%s load_rating_w" % name)
    if flight <= 0.0:
        raise ValueError("%s flight_load_current_a must be positive, got %r" % (name, flight))
    if simulated <= 0.0:
        raise ValueError(
            "%s simulated_load_current_a must be positive, got %r" % (name, simulated)
        )
    if voltage <= 0.0:
        raise ValueError("%s interface_voltage_v must be positive, got %r" % (name, voltage))
    current_deviation = abs(simulated - flight) / flight * 100.0
    dissipated = voltage * simulated
    margin = load_rating_margin(rating, dissipated)
    return {
        "name": name,
        "current_deviation_percent": current_deviation,
        "current_tolerance_percent": spec["load_current_tolerance_percent"],
        "current_ok": _not_above(current_deviation, spec["load_current_tolerance_percent"]),
        "dissipated_w": dissipated,
        "load_rating_w": rating,
        "rating_margin": margin,
        "required_margin": spec["load_rating_margin_factor"],
        "rating_ok": _at_least(margin, spec["load_rating_margin_factor"]),
    }


def unterminated_interfaces(categorized):
    """Names of the interfaces left without any termination."""
    if not isinstance(categorized, (list, tuple)):
        raise ValueError("categorized must be a sequence, got %r" % (categorized,))
    return [c["name"] for c in categorized if c["category"] == UNTERMINATED]


def real_hardware_fraction(categorized):
    """Share of interfaces terminated in real hardware rather than a stand-in."""
    if not isinstance(categorized, (list, tuple)) or not categorized:
        raise ValueError("categorized must be a non-empty sequence")
    real = sum(1 for c in categorized if c["category"] == REAL_HARDWARE)
    return real / float(len(categorized))


def termination_readiness(findings):
    """Gate token for the finding list of one termination review."""
    if not isinstance(findings, (list, tuple)):
        raise ValueError("findings must be a sequence, got %r" % (findings,))
    return "ready-for-measurement" if not findings else "hold-terminations"


def evaluate_terminations(config):
    """End-to-end clause 5.2.6.7 termination check for one tested unit."""
    if not isinstance(config, dict):
        raise ValueError("config must be a mapping")
    if "interfaces" not in config:
        raise ValueError("config missing required key 'interfaces'")
    spec = resolve_spec(config.get("spec"))
    categorized = categorize_interfaces(config["interfaces"])
    by_name = {i["name"]: i for i in config["interfaces"]}

    equivalent_checks = []
    power_checks = []
    findings = []

    for entry in categorized:
        record = by_name[entry["name"]]
        if entry["category"] == UNTERMINATED:
            findings.append("interface %s left without a termination" % entry["name"])
            continue
        if entry["category"] == EQUIVALENT_LOAD:
            check = check_equivalent_load(record, config.get("spec"))
            equivalent_checks.append(check)
            if not check["impedance_ok"]:
                findings.append(
                    "equivalent load on %s outside the impedance tolerance" % entry["name"]
                )
            if not check["phase_ok"]:
                findings.append(
                    "equivalent load on %s outside the phase tolerance" % entry["name"]
                )
            if entry["kind"] == "power":
                power = check_power_interface(record, config.get("spec"))
                power_checks.append(power)
                if not power["current_ok"]:
                    findings.append(
                        "simulated load on %s does not draw the flight load current"
                        % entry["name"]
                    )
                if not power["rating_ok"]:
                    findings.append(
                        "load bank on %s is not rated above its dissipation by the required margin"
                        % entry["name"]
                    )

    fraction = real_hardware_fraction(categorized)
    if not _at_least(fraction, spec["min_real_hardware_fraction"]):
        findings.append(
            "too few interfaces terminated in real hardware for the declared configuration"
        )

    return {
        "interfaces": categorized,
        "equivalent_load_checks": equivalent_checks,
        "power_interface_checks": power_checks,
        "unterminated": unterminated_interfaces(categorized),
        "real_hardware_fraction": fraction,
        "findings": findings,
        "status": termination_readiness(findings),
        "ready": not findings,
    }
