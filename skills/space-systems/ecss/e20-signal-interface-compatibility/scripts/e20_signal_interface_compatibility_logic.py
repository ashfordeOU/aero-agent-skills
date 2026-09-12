#!/usr/bin/env python3
"""ECSS-E-ST-20C clause 4.1.2 -- signal interface electrical compatibility.

Deterministic, offline, stdlib-only helpers that check whether a source
unit and a load unit can share a signal interface: the interface family
is categorized first, then the source/load impedance relationship, the
loaded signal level, the high- and low-side noise margins and the loop
current are computed and compared against the family's requirements.

Modelling assumptions (documented so a reviewer can challenge them):
  * The source is represented as an ideal open-circuit level behind a
    single real output impedance; the load as a single real input
    impedance in parallel with its threshold detector.
  * The high level is divided by the source/load divider. The low level
    is taken as declared: a driven low is sunk by the source rather
    than developed across the divider, so it is not scaled here.
  * Impedances are real (ohms). Reactive termination effects are out of
    scope for this clause-level screening check.

No network, no third-party imports, no randomness.
"""

FAMILY_ALIASES = {
    "bi-level-discrete": "bi-level-discrete",
    "bi-level": "bi-level-discrete",
    "discrete": "bi-level-discrete",
    "analog-measurement": "analog-measurement",
    "analog": "analog-measurement",
    "serial-data-line": "serial-data-line",
    "serial": "serial-data-line",
    "data-line": "serial-data-line",
    "pulse-command": "pulse-command",
    "pulse": "pulse-command",
}

# Per-family interface rules.
#   min_ratio        : minimum load/source impedance ratio (level-driven)
#   match_tolerance  : fractional termination tolerance (line-driven)
#   margin_floor_v   : minimum acceptable noise margin, volts
FAMILY_RULES = {
    "bi-level-discrete": {
        "min_ratio": 10.0,
        "match_tolerance": None,
        "margin_floor_v": 0.4,
    },
    "analog-measurement": {
        "min_ratio": 100.0,
        "match_tolerance": None,
        "margin_floor_v": 0.1,
    },
    "serial-data-line": {
        "min_ratio": None,
        "match_tolerance": 0.10,
        "margin_floor_v": 0.2,
    },
    "pulse-command": {
        "min_ratio": 10.0,
        "match_tolerance": None,
        "margin_floor_v": 0.5,
    },
}

REQUIRED_SOURCE_KEYS = (
    "open_circuit_high_v",
    "driven_low_v",
    "output_impedance_ohm",
    "drive_capability_a",
)
REQUIRED_LOAD_KEYS = (
    "input_high_threshold_v",
    "input_low_threshold_v",
    "input_impedance_ohm",
)


def _number(value, label):
    """Return value as float, rejecting bools and non-numeric input."""
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise ValueError("%s must be a real number, got %r" % (label, value))
    return float(value)


def categorize_signal_interface(kind):
    """Map a free-form interface name onto one of the four families."""
    if not isinstance(kind, str):
        raise ValueError("interface kind must be a string, got %r" % (kind,))
    key = kind.strip().lower().replace("_", "-").replace(" ", "-")
    if not key:
        raise ValueError("interface kind must not be empty")
    if key not in FAMILY_ALIASES:
        raise ValueError(
            "uncategorized interface kind %r; expected one of %s"
            % (kind, sorted(set(FAMILY_ALIASES.values())))
        )
    return FAMILY_ALIASES[key]


def divider_voltage(open_circuit_v, source_ohm, load_ohm):
    """Voltage across the load of a source/load resistive divider."""
    voc = _number(open_circuit_v, "open_circuit_v")
    zs = _number(source_ohm, "source_ohm")
    zl = _number(load_ohm, "load_ohm")
    if zs < 0.0:
        raise ValueError("source_ohm must not be negative, got %r" % (source_ohm,))
    if zl <= 0.0:
        raise ValueError("load_ohm must be > 0, got %r" % (load_ohm,))
    return voc * zl / (zs + zl)


def loop_current_a(open_circuit_v, source_ohm, load_ohm):
    """Series loop current at the loaded operating point, amperes."""
    voc = _number(open_circuit_v, "open_circuit_v")
    zs = _number(source_ohm, "source_ohm")
    zl = _number(load_ohm, "load_ohm")
    if zs < 0.0:
        raise ValueError("source_ohm must not be negative, got %r" % (source_ohm,))
    if zl <= 0.0:
        raise ValueError("load_ohm must be > 0, got %r" % (load_ohm,))
    return voc / (zs + zl)


def noise_margins(loaded_high_v, driven_low_v, high_threshold_v, low_threshold_v):
    """High- and low-side noise margins for a level-driven interface."""
    vh = _number(loaded_high_v, "loaded_high_v")
    vl = _number(driven_low_v, "driven_low_v")
    th = _number(high_threshold_v, "high_threshold_v")
    tl = _number(low_threshold_v, "low_threshold_v")
    if vh <= vl:
        raise ValueError("loaded high level must exceed the driven low level")
    if th <= tl:
        raise ValueError("high threshold must exceed the low threshold")
    return {"high_margin_v": vh - th, "low_margin_v": tl - vl}


def check_impedance_relationship(family, source_ohm, load_ohm):
    """Findings for the impedance rule that applies to this family."""
    if family not in FAMILY_RULES:
        raise ValueError("uncategorized interface family %r" % (family,))
    zs = _number(source_ohm, "source_ohm")
    zl = _number(load_ohm, "load_ohm")
    if zs <= 0.0:
        raise ValueError("source_ohm must be > 0, got %r" % (source_ohm,))
    if zl <= 0.0:
        raise ValueError("load_ohm must be > 0, got %r" % (load_ohm,))
    rules = FAMILY_RULES[family]
    findings = []
    ratio = zl / zs
    if rules["match_tolerance"] is not None:
        deviation = abs(zl - zs) / zs
        if deviation > rules["match_tolerance"]:
            findings.append(
                "termination mismatch: load %.1f ohm deviates %.1f%% from "
                "source %.1f ohm (limit %.1f%%)"
                % (zl, deviation * 100.0, zs, rules["match_tolerance"] * 100.0)
            )
        return {"ratio": ratio, "deviation": deviation, "findings": findings}
    if ratio < rules["min_ratio"]:
        findings.append(
            "impedance ratio %.2f below the %.1f required for %s"
            % (ratio, rules["min_ratio"], family)
        )
    return {"ratio": ratio, "deviation": None, "findings": findings}


def _require_keys(mapping, keys, label):
    if not isinstance(mapping, dict):
        raise ValueError("%s must be a mapping, got %r" % (label, type(mapping).__name__))
    missing = [k for k in keys if k not in mapping]
    if missing:
        raise ValueError("%s missing required keys: %s" % (label, ", ".join(sorted(missing))))


def assess_signal_interface(interface):
    """Full clause 4.1.2 screening of one source/load signal interface."""
    if not isinstance(interface, dict):
        raise ValueError("interface must be a mapping")
    for key in ("id", "kind", "source", "load"):
        if key not in interface:
            raise ValueError("interface missing required key %r" % (key,))
    family = categorize_signal_interface(interface["kind"])
    source = interface["source"]
    load = interface["load"]
    _require_keys(source, REQUIRED_SOURCE_KEYS, "source")
    _require_keys(load, REQUIRED_LOAD_KEYS, "load")

    zs = _number(source["output_impedance_ohm"], "output_impedance_ohm")
    zl = _number(load["input_impedance_ohm"], "input_impedance_ohm")
    imp = check_impedance_relationship(family, zs, zl)
    findings = list(imp["findings"])

    loaded_high = divider_voltage(source["open_circuit_high_v"], zs, zl)
    margins = noise_margins(
        loaded_high,
        source["driven_low_v"],
        load["input_high_threshold_v"],
        load["input_low_threshold_v"],
    )
    floor = FAMILY_RULES[family]["margin_floor_v"]
    for side in ("high_margin_v", "low_margin_v"):
        value = margins[side]
        if value <= 0.0:
            findings.append(
                "%s is %.3f V: the receiver cannot resolve the level" % (side, value)
            )
        elif value < floor:
            findings.append(
                "%s is %.3f V, below the %.3f V floor for %s" % (side, value, floor, family)
            )

    current = loop_current_a(source["open_circuit_high_v"], zs, zl)
    capability = _number(source["drive_capability_a"], "drive_capability_a")
    if capability <= 0.0:
        raise ValueError("drive_capability_a must be > 0, got %r" % (capability,))
    if current > capability:
        findings.append(
            "loop current %.4f A exceeds the %.4f A source drive capability"
            % (current, capability)
        )

    return {
        "id": interface["id"],
        "family": family,
        "impedance_ratio": imp["ratio"],
        "loaded_high_v": loaded_high,
        "high_margin_v": margins["high_margin_v"],
        "low_margin_v": margins["low_margin_v"],
        "loop_current_a": current,
        "findings": findings,
        "compatible": not findings,
    }


def assess_interface_set(interfaces):
    """Assess a list of interfaces and summarise the incompatible ones."""
    if not isinstance(interfaces, list):
        raise ValueError("interfaces must be a list")
    if not interfaces:
        raise ValueError("interfaces must not be empty")
    results = [assess_signal_interface(item) for item in interfaces]
    seen = set()
    for result in results:
        if result["id"] in seen:
            raise ValueError("duplicate interface id %r" % (result["id"],))
        seen.add(result["id"])
    incompatible = [r["id"] for r in results if not r["compatible"]]
    return {
        "assessed": len(results),
        "incompatible": incompatible,
        "results": results,
        "all_compatible": not incompatible,
    }
