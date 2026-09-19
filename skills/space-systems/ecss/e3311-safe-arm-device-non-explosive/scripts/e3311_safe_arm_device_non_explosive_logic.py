#!/usr/bin/env python3
"""Non-explosive safe-and-arm device function and interface assessment.

Anchor: ECSS-E-ST-33-11C clause 4.10.11. The procedure below is a
paraphrase into implementable steps; no standard text is reproduced.

A non-explosive safe-and-arm device has no explosive train to
misalign, so everything it does it does electrically. That moves the
whole safety case onto three things a reviewer can actually count:

Inhibits
    How many independent interruptions sit in the firing path while
    the device is safe? Independence is the word that carries the
    requirement. Two relay contacts driven from one coil, or two
    switches on one ground return, are two inhibits on the drawing and
    one inhibit in the failure tree. The count that matters is the
    number of distinct common-cause groups among the inhibits that are
    actually active in the safe state.

Functions
    The device has to interrupt the firing energy, report its position
    from the interrupter rather than from the command it was given,
    accept manual safing without relying on the power it may have
    lost, accept remote arm and disarm, expose its inhibit states to
    telemetry, and hold its state through a power interruption. The
    set is closed; silence is a gap.

Interfaces
    Command, monitor, primary power, firing output and manual safing
    are declared separately, and the connector that carries a command
    must not be the connector that carries the firing output. Sharing
    one shell is how a command harness fault becomes a firing event.

Timing and life are graded alongside: arming and safing each have a
limit, and the device has a qualified number of arm/safe cycles that
the mission profile must fit inside.

Standard library only, offline, deterministic.
"""

from __future__ import annotations

import math

SA_FUNCTIONS = (
    "interrupt-firing-energy-path-in-safe",
    "indicate-position-from-interrupter",
    "manual-safing-without-primary-power",
    "remote-arm-and-disarm-command",
    "inhibit-state-telemetry",
    "state-retained-through-power-loss",
)

SA_INTERFACES = (
    "command",
    "monitor",
    "primary-power",
    "firing-output",
    "manual-safing",
)

INDICATION_SOURCES = (
    "interrupter-position",
    "commanded-state",
    "drive-coil-current",
)

ACCEPTED_INDICATION_SOURCE = "interrupter-position"

VERDICT_MET = "safe-arm-device-requirements-met"
VERDICT_NOT_MET = "safe-arm-device-requirements-not-met"

DEFAULT_SAFE_ARM_POLICY = {
    "required_independent_inhibits": 2,
    "max_arm_time_s": 1.0,
    "max_safing_time_s": 2.0,
    "min_qualified_cycles": 50,
    "required_functions": SA_FUNCTIONS,
    "required_interfaces": SA_INTERFACES,
    "separate_command_and_firing_connectors": True,
}

_REL_TOL = 1e-9
_ABS_TOL = 1e-12


def _is_finite_number(value):
    return (
        isinstance(value, (int, float))
        and not isinstance(value, bool)
        and math.isfinite(value)
    )


def _require_positive(name, value):
    if not _is_finite_number(value):
        raise ValueError("%s must be a finite number, got %r" % (name, value))
    if value <= 0.0:
        raise ValueError("%s must be greater than zero, got %r" % (name, value))
    return float(value)


def _require_count(name, value, minimum=0):
    if not isinstance(value, int) or isinstance(value, bool):
        raise ValueError("%s must be an integer, got %r" % (name, value))
    if value < minimum:
        raise ValueError("%s must be at least %d, got %r" % (name, minimum, value))
    return value


def _require_bool(name, value):
    if not isinstance(value, bool):
        raise ValueError("%s must be a boolean, got %r" % (name, value))
    return value


def _require_choice(name, value, allowed):
    if value not in allowed:
        raise ValueError(
            "%s must be one of %s, got %r" % (name, ", ".join(allowed), value)
        )
    return value


def _require_identifier(name, value):
    if not isinstance(value, str) or not value.strip():
        raise ValueError("%s must be a non-empty string, got %r" % (name, value))
    return value.strip()


def _at_most(value, limit):
    """value <= limit, absorbing floating-point representation error."""
    return value <= limit or math.isclose(
        value, limit, rel_tol=_REL_TOL, abs_tol=_ABS_TOL
    )


def validate_safe_arm_policy(policy):
    """Check a safe-and-arm policy carries sane counts and limits."""
    if not isinstance(policy, dict):
        raise ValueError("policy must be a mapping, got %r" % (policy,))
    _require_count(
        "required_independent_inhibits",
        policy.get("required_independent_inhibits"),
        minimum=1,
    )
    _require_positive("max_arm_time_s", policy.get("max_arm_time_s"))
    _require_positive("max_safing_time_s", policy.get("max_safing_time_s"))
    _require_count("min_qualified_cycles", policy.get("min_qualified_cycles"), minimum=1)
    functions = policy.get("required_functions")
    if not isinstance(functions, (list, tuple)) or not functions:
        raise ValueError("policy required_functions must be a non-empty sequence")
    for function in functions:
        _require_choice("required function", function, SA_FUNCTIONS)
    interfaces = policy.get("required_interfaces")
    if not isinstance(interfaces, (list, tuple)) or not interfaces:
        raise ValueError("policy required_interfaces must be a non-empty sequence")
    for interface in interfaces:
        _require_choice("required interface", interface, SA_INTERFACES)
    _require_bool(
        "separate_command_and_firing_connectors",
        policy.get("separate_command_and_firing_connectors"),
    )
    return policy


def independent_inhibit_groups(inhibits):
    """Group the inhibits active in the safe state by common cause.

    An inhibit with no declared common-cause group stands alone. Two
    inhibits sharing a group collapse into one, because the single
    cause that defeats one defeats the other.
    """
    if not isinstance(inhibits, (list, tuple)) or not inhibits:
        raise ValueError("inhibits must be a non-empty sequence")
    seen_ids = set()
    groups = {}
    standalone = []
    for index, inhibit in enumerate(inhibits):
        if not isinstance(inhibit, dict):
            raise ValueError("inhibits[%d] must be a mapping, got %r" % (index, inhibit))
        identifier = _require_identifier("inhibits[%d].id" % index, inhibit.get("id"))
        if identifier in seen_ids:
            raise ValueError("inhibit id %s is declared twice" % identifier)
        seen_ids.add(identifier)
        active = inhibit.get("active_in_safe")
        if active is None:
            raise ValueError("inhibit %s does not declare active_in_safe" % identifier)
        _require_bool("inhibit %s active_in_safe" % identifier, active)
        if not active:
            continue
        group = inhibit.get("common_cause_group")
        if group is None:
            standalone.append(identifier)
        else:
            key = _require_identifier(
                "inhibit %s common_cause_group" % identifier, group
            )
            groups.setdefault(key, []).append(identifier)
    return {
        "standalone": sorted(standalone),
        "grouped": {key: sorted(v) for key, v in groups.items()},
        "independent_count": len(standalone) + len(groups),
    }


def assess_inhibits(inhibits, policy=DEFAULT_SAFE_ARM_POLICY):
    """Grade the independent inhibit count held while the device is safe."""
    validate_safe_arm_policy(policy)
    grouping = independent_inhibit_groups(inhibits)
    required = policy["required_independent_inhibits"]
    count = grouping["independent_count"]
    findings = []
    if count < required:
        findings.append(
            "only %d independent inhibit(s) are active in the safe state, "
            "against a required %d" % (count, required)
        )
    for key, members in sorted(grouping["grouped"].items()):
        if len(members) > 1:
            findings.append(
                "inhibits %s share the common cause %s and count once"
                % (", ".join(members), key)
            )
    return {
        "part": "inhibits",
        "independent_count": count,
        "required_count": required,
        "standalone": grouping["standalone"],
        "grouped": grouping["grouped"],
        "compliant": count >= required,
        "findings": findings,
    }


def assess_functions(functions, policy=DEFAULT_SAFE_ARM_POLICY):
    """Walk the closed set of device functions."""
    validate_safe_arm_policy(policy)
    if not isinstance(functions, dict):
        raise ValueError("functions must be a mapping, got %r" % (functions,))
    for key in functions:
        _require_choice("device function", key, SA_FUNCTIONS)
    present = []
    absent = []
    for function in policy["required_functions"]:
        state = functions.get(function)
        if state is None:
            raise ValueError("device function %s is undeclared" % function)
        _require_bool("device function %s" % function, state)
        (present if state else absent).append(function)
    findings = [
        "required safe-and-arm function not implemented: %s" % function
        for function in absent
    ]
    return {
        "part": "functions",
        "functions_present": present,
        "functions_absent": absent,
        "compliant": not absent,
        "findings": findings,
    }


def assess_position_indication(indication_source):
    """Accept only an indication driven by the interrupter itself."""
    source = _require_choice(
        "indication_source", indication_source, INDICATION_SOURCES
    )
    findings = []
    if source != ACCEPTED_INDICATION_SOURCE:
        findings.append(
            "position indication is derived from %s; it has to be read from "
            "the interrupter position, otherwise a stuck interrupter reports "
            "the state it was told to reach" % source
        )
    return {
        "part": "position-indication",
        "indication_source": source,
        "compliant": not findings,
        "findings": findings,
    }


def assess_interfaces(interfaces, policy=DEFAULT_SAFE_ARM_POLICY):
    """Check every interface is declared and kept off the firing shell."""
    validate_safe_arm_policy(policy)
    if not isinstance(interfaces, dict):
        raise ValueError("interfaces must be a mapping, got %r" % (interfaces,))
    for key in interfaces:
        _require_choice("device interface", key, SA_INTERFACES)
    connectors = {}
    for interface in policy["required_interfaces"]:
        connector = interfaces.get(interface)
        if connector is None:
            raise ValueError("device interface %s is undeclared" % interface)
        connectors[interface] = _require_identifier(
            "interface %s connector" % interface, connector
        )
    findings = []
    if policy["separate_command_and_firing_connectors"]:
        firing = connectors.get("firing-output")
        for interface in ("command", "monitor"):
            if firing is not None and connectors.get(interface) == firing:
                findings.append(
                    "the %s interface shares connector %s with the firing "
                    "output; a fault on the %s harness reaches the firing line"
                    % (interface, firing, interface)
                )
    return {
        "part": "interfaces",
        "connectors": connectors,
        "compliant": not findings,
        "findings": findings,
    }


def assess_timing_and_life(case, policy=DEFAULT_SAFE_ARM_POLICY):
    """Grade arming time, safing time and qualified cycle life."""
    validate_safe_arm_policy(policy)
    if not isinstance(case, dict):
        raise ValueError("timing case must be a mapping, got %r" % (case,))
    arm_time = _require_positive("arm_time_s", case.get("arm_time_s"))
    safing_time = _require_positive("safing_time_s", case.get("safing_time_s"))
    qualified = _require_count(
        "qualified_cycles", case.get("qualified_cycles"), minimum=1
    )
    planned = _require_count("planned_cycles", case.get("planned_cycles"), minimum=1)
    findings = []
    if not _at_most(arm_time, policy["max_arm_time_s"]):
        findings.append(
            "arming takes %.4g s, above the allowed %.4g s"
            % (arm_time, policy["max_arm_time_s"])
        )
    if not _at_most(safing_time, policy["max_safing_time_s"]):
        findings.append(
            "safing takes %.4g s, above the allowed %.4g s"
            % (safing_time, policy["max_safing_time_s"])
        )
    if qualified < policy["min_qualified_cycles"]:
        findings.append(
            "the device is qualified for %d arm/safe cycles, below the "
            "required %d" % (qualified, policy["min_qualified_cycles"])
        )
    if planned > qualified:
        findings.append(
            "the operations plan uses %d arm/safe cycles against %d qualified"
            % (planned, qualified)
        )
    return {
        "part": "timing-and-life",
        "arm_time_s": arm_time,
        "safing_time_s": safing_time,
        "qualified_cycles": qualified,
        "planned_cycles": planned,
        "compliant": not findings,
        "findings": findings,
    }


def assess_safe_arm_device(case, policy=DEFAULT_SAFE_ARM_POLICY):
    """Full clause 4.10.11 walk with an overall verdict."""
    validate_safe_arm_policy(policy)
    if not isinstance(case, dict):
        raise ValueError("case must be a mapping, got %r" % (case,))
    parts = {
        "inhibits": assess_inhibits(case.get("inhibits"), policy),
        "functions": assess_functions(case.get("functions") or {}, policy),
        "position-indication": assess_position_indication(
            case.get("indication_source")
        ),
        "interfaces": assess_interfaces(case.get("interfaces") or {}, policy),
        "timing-and-life": assess_timing_and_life(
            case.get("timing_and_life") or {}, policy
        ),
    }
    findings = []
    failed = []
    for name in (
        "inhibits",
        "functions",
        "position-indication",
        "interfaces",
        "timing-and-life",
    ):
        result = parts[name]
        findings.extend(result["findings"])
        if not result["compliant"]:
            failed.append(name)
    return {
        "parts": parts,
        "failed_parts": failed,
        "compliant": not failed,
        "verdict": VERDICT_NOT_MET if failed else VERDICT_MET,
        "findings": findings,
    }
