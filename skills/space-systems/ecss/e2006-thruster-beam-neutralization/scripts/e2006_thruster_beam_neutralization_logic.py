#!/usr/bin/env python3
"""Exhaust-beam neutralization logic for ECSS-E-ST-20-06C clause 11.2.2.

Offline, deterministic, standard-library only. The module implements the
neutralization argument in the form it is assessed: the emitted
ion-beam current is balanced against the neutralizer electron current and
the charge-exchange backflow, the residual net emitted current is driven
across the plasma-contact conductance to give the platform floating
potential, and that potential -- together with the neutralizer coupling
voltage, the beam/emitter firing sequence and the emitter inventory --
decides whether the beam is neutralized by design.

No standard text is reproduced; the clause is cited as the anchor only.
"""

import math

__all__ = [
    "categorize_neutralization_architecture",
    "neutralizer_current_balance",
    "floating_potential_v",
    "check_potential_allowance",
    "check_coupling_voltage",
    "check_ignition_sequence",
    "check_emitter_redundancy",
    "assess_thruster_neutralization",
    "assess_propulsion_neutralization",
]

# Representation tolerance for at-the-limit comparisons. It absorbs the
# few ULPs a difference or a quotient can land above an exact limit; the
# engineering allowance itself is never widened.
_REL_TOL = 1e-9
_ABS_TOL = 1e-12

ARCHITECTURE_ALIASES = {
    "dedicated-neutralizer": "dedicated-neutralizer",
    "dedicated": "dedicated-neutralizer",
    "one-per-thruster": "dedicated-neutralizer",
    "shared-neutralizer": "shared-neutralizer",
    "shared": "shared-neutralizer",
    "cluster-neutralizer": "shared-neutralizer",
    "self-neutralizing": "self-neutralizing",
    "self": "self-neutralizing",
    "integrated-emitter": "self-neutralizing",
}

# Architectures that rely on a distinct electron emitter being present.
ARCHITECTURES_NEEDING_EMITTER = frozenset(
    ("dedicated-neutralizer", "shared-neutralizer")
)

# Electron-to-ion current ratio at or above which the beam is electron-rich.
MIN_NEUTRALIZATION_RATIO = 1.0

# Default allowance on the emitter-to-plasma coupling voltage magnitude.
DEFAULT_COUPLING_VOLTAGE_ALLOWANCE_V = 20.0

# Findings that record a robustness observation rather than a clause breach.
ADVISORY_FINDINGS = frozenset(("single-string-electron-emitter",))


def _number(name, value):
    """Return value as a finite float or raise ValueError."""
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise ValueError("%s must be a real number, got %r" % (name, value))
    out = float(value)
    if not math.isfinite(out):
        raise ValueError("%s must be finite, got %r" % (name, value))
    return out


def _non_negative(name, value):
    out = _number(name, value)
    if out < 0.0:
        raise ValueError("%s must be >= 0, got %r" % (name, value))
    return out


def _positive(name, value):
    out = _number(name, value)
    if out <= 0.0:
        raise ValueError("%s must be > 0, got %r" % (name, value))
    return out


def _at_or_below(value, limit):
    """True when value is below limit or equal to it within representation."""
    return value <= limit or math.isclose(
        value, limit, rel_tol=_REL_TOL, abs_tol=_ABS_TOL
    )


def _at_or_above(value, limit):
    """True when value is above limit or equal to it within representation."""
    return value >= limit or math.isclose(
        value, limit, rel_tol=_REL_TOL, abs_tol=_ABS_TOL
    )


def categorize_neutralization_architecture(architecture):
    """Normalize a neutralization architecture name.

    Returns one of dedicated-neutralizer, shared-neutralizer,
    self-neutralizing. An unrecognized architecture is rejected.
    """
    if not isinstance(architecture, str):
        raise ValueError(
            "architecture must be a string, got %r" % (architecture,)
        )
    key = architecture.strip().lower().replace("_", "-").replace(" ", "-")
    if not key:
        raise ValueError("architecture must not be empty")
    if key not in ARCHITECTURE_ALIASES:
        raise ValueError(
            "uncategorized neutralization architecture %r; expected one of %s"
            % (architecture, ", ".join(sorted(set(ARCHITECTURE_ALIASES.values()))))
        )
    return ARCHITECTURE_ALIASES[key]


def neutralizer_current_balance(
    beam_current_a, neutralizer_current_a, backflow_current_a=0.0
):
    """Balance emitted ion current against emitted electron current.

    net_emitted_current_a is the positive charge the platform loses per
    second: the ion beam, less the electron current the emitter returns,
    less the charge-exchange ions that flow back onto the platform.
    """
    beam = _positive("beam_current_a", beam_current_a)
    electrons = _non_negative("neutralizer_current_a", neutralizer_current_a)
    backflow = _non_negative("backflow_current_a", backflow_current_a)
    if backflow > beam:
        raise ValueError(
            "backflow_current_a (%r) cannot exceed beam_current_a (%r)"
            % (backflow_current_a, beam_current_a)
        )
    net = beam - electrons - backflow
    ratio = electrons / beam
    return {
        "beam_current_a": beam,
        "neutralizer_current_a": electrons,
        "backflow_current_a": backflow,
        "net_emitted_current_a": net,
        "neutralization_ratio": ratio,
        "electron_rich": _at_or_above(ratio, MIN_NEUTRALIZATION_RATIO),
    }


def floating_potential_v(net_emitted_current_a, plasma_contact_conductance_s):
    """Steady platform potential driven by the residual emitted current.

    Positive net emission of positive charge drives the platform negative,
    so the returned potential carries the opposite sign to the current.
    """
    net = _number("net_emitted_current_a", net_emitted_current_a)
    conductance = _positive(
        "plasma_contact_conductance_s", plasma_contact_conductance_s
    )
    return -net / conductance


def check_potential_allowance(potential_v, allowable_magnitude_v):
    """Compare a signed floating potential against a magnitude allowance."""
    potential = _number("potential_v", potential_v)
    allowance = _positive("allowable_magnitude_v", allowable_magnitude_v)
    magnitude = abs(potential)
    return {
        "potential_v": potential,
        "magnitude_v": magnitude,
        "allowable_magnitude_v": allowance,
        "margin_v": allowance - magnitude,
        "compliant": _at_or_below(magnitude, allowance),
    }


def check_coupling_voltage(
    coupling_voltage_v, allowable_magnitude_v=DEFAULT_COUPLING_VOLTAGE_ALLOWANCE_V
):
    """Compare the emitter-to-plasma coupling voltage against its allowance."""
    coupling = _number("coupling_voltage_v", coupling_voltage_v)
    allowance = _positive("allowable_magnitude_v", allowable_magnitude_v)
    magnitude = abs(coupling)
    return {
        "coupling_voltage_v": coupling,
        "magnitude_v": magnitude,
        "allowable_magnitude_v": allowance,
        "margin_v": allowance - magnitude,
        "compliant": _at_or_below(magnitude, allowance),
    }


def check_ignition_sequence(emitter_ignition_s, beam_on_s, required_lead_s):
    """Check the emitter ignites at least required_lead_s before beam-on."""
    ignition = _number("emitter_ignition_s", emitter_ignition_s)
    beam_on = _number("beam_on_s", beam_on_s)
    required = _non_negative("required_lead_s", required_lead_s)
    lead = beam_on - ignition
    return {
        "emitter_ignition_s": ignition,
        "beam_on_s": beam_on,
        "lead_s": lead,
        "required_lead_s": required,
        "compliant": _at_or_above(lead, required),
    }


def check_emitter_redundancy(architecture, emitter_count):
    """Check the emitter inventory declared for an architecture."""
    category = categorize_neutralization_architecture(architecture)
    if isinstance(emitter_count, bool) or not isinstance(emitter_count, int):
        raise ValueError(
            "emitter_count must be an integer, got %r" % (emitter_count,)
        )
    if emitter_count < 0:
        raise ValueError("emitter_count must be >= 0, got %r" % (emitter_count,))
    needs_emitter = category in ARCHITECTURES_NEEDING_EMITTER
    findings = []
    observations = []
    if needs_emitter and emitter_count < 1:
        findings.append("no-electron-emitter-declared")
    elif needs_emitter and emitter_count < 2:
        observations.append("single-string-electron-emitter")
    return {
        "architecture": category,
        "emitter_count": emitter_count,
        "emitter_required": needs_emitter,
        "findings": findings,
        "observations": observations,
    }


def assess_thruster_neutralization(thruster):
    """Assess one thruster against the clause 11.2.2 design provisions."""
    if not isinstance(thruster, dict):
        raise ValueError("thruster must be a mapping, got %r" % (type(thruster),))
    required = (
        "id",
        "architecture",
        "beam_current_a",
        "neutralizer_current_a",
        "plasma_contact_conductance_s",
        "allowable_potential_v",
    )
    missing = [key for key in required if key not in thruster]
    if missing:
        raise ValueError(
            "thruster record is missing required key(s): %s" % ", ".join(missing)
        )
    identifier = thruster["id"]
    if not isinstance(identifier, str) or not identifier.strip():
        raise ValueError("thruster id must be a non-empty string, got %r" % (identifier,))
    category = categorize_neutralization_architecture(thruster["architecture"])
    balance = neutralizer_current_balance(
        thruster["beam_current_a"],
        thruster["neutralizer_current_a"],
        thruster.get("backflow_current_a", 0.0),
    )
    potential = floating_potential_v(
        balance["net_emitted_current_a"], thruster["plasma_contact_conductance_s"]
    )
    potential_check = check_potential_allowance(
        potential, thruster["allowable_potential_v"]
    )
    findings = []
    observations = []
    if not balance["electron_rich"]:
        findings.append("beam-not-electron-rich")
    if not potential_check["compliant"]:
        findings.append("floating-potential-exceeds-allowance")

    coupling_check = None
    if thruster.get("coupling_voltage_v") is None:
        findings.append("neutralizer-coupling-voltage-not-recorded")
    else:
        coupling_check = check_coupling_voltage(
            thruster["coupling_voltage_v"],
            thruster.get(
                "allowable_coupling_voltage_v",
                DEFAULT_COUPLING_VOLTAGE_ALLOWANCE_V,
            ),
        )
        if not coupling_check["compliant"]:
            findings.append("neutralizer-coupling-voltage-exceeds-allowance")

    sequence_check = None
    if thruster.get("emitter_ignition_s") is None or thruster.get("beam_on_s") is None:
        findings.append("ignition-sequence-not-recorded")
    else:
        sequence_check = check_ignition_sequence(
            thruster["emitter_ignition_s"],
            thruster["beam_on_s"],
            thruster.get("required_lead_s", 0.0),
        )
        if not sequence_check["compliant"]:
            findings.append("beam-precedes-neutralizer-ignition")

    redundancy = check_emitter_redundancy(
        category, thruster.get("emitter_count", 1 if category in ARCHITECTURES_NEEDING_EMITTER else 0)
    )
    findings.extend(redundancy["findings"])
    observations.extend(redundancy["observations"])

    blocking = [item for item in findings if item not in ADVISORY_FINDINGS]
    return {
        "id": identifier,
        "architecture": category,
        "balance": balance,
        "floating_potential_v": potential,
        "potential_check": potential_check,
        "coupling_check": coupling_check,
        "sequence_check": sequence_check,
        "redundancy": redundancy,
        "findings": blocking,
        "observations": observations,
        "compliant": not blocking,
    }


def assess_propulsion_neutralization(thrusters):
    """Aggregate the clause 11.2.2 verdict across a propulsion set."""
    if isinstance(thrusters, (str, bytes, dict)) or not isinstance(
        thrusters, (list, tuple)
    ):
        raise ValueError("thrusters must be a list of mappings")
    if not thrusters:
        raise ValueError("thrusters must not be empty")
    results = []
    seen = set()
    for thruster in thrusters:
        result = assess_thruster_neutralization(thruster)
        if result["id"] in seen:
            raise ValueError("duplicate thruster id %r" % (result["id"],))
        seen.add(result["id"])
        results.append(result)
    noncompliant = [item["id"] for item in results if not item["compliant"]]
    return {
        "thruster_count": len(results),
        "compliant_count": len(results) - len(noncompliant),
        "noncompliant_ids": noncompliant,
        "results": results,
        "findings_by_thruster": {
            item["id"]: list(item["findings"]) for item in results
        },
        "compliant": not noncompliant,
    }
