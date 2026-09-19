#!/usr/bin/env python3
"""Power provisions, arm-plug receptacle and safe/arm/test plug assessment.

Anchor: ECSS-E-ST-33-11C clauses 4.10.6 to 4.10.10. The procedure below
is a paraphrase into implementable steps; no standard text is
reproduced.

The clauses cover the part of an explosive subsystem a technician can
physically touch on the pad: the power that reaches the bridgewires,
the receptacle the arming plug goes into, and the family of plugs that
take turns in it.

Three questions are asked, and they are independent of each other:

Power provisions
    Does the firing source actually deliver the all-fire current to
    every initiator it has to fire at once, once the source resistance
    and the harness resistance have taken their share? The bridges sit
    in parallel, so adding initiators lowers the load resistance and
    raises the total current while lowering the current each bridge
    receives. A design that passes with one initiator can fail with
    four.

Arm receptacle
    Is the receptacle reachable, uniquely keyed, shorting when
    unmated, retained, and left until last? The provisions are a
    closed set, so silence is a gap rather than an implicit pass.

Plug set
    Are the safe, arm and test plugs distinguishable by keying and by
    identification colour, and does the mating matrix keep the test
    plug out of the arm receptacle? Cross-mating is the failure the
    keying exists to prevent.

Standard library only, offline, deterministic.
"""

from __future__ import annotations

import math

PLUG_KINDS = ("safe-plug", "arm-plug", "test-plug")

RECEPTACLE_IDS = ("arm-receptacle", "test-receptacle")

EXPECTED_MATING = {
    "safe-plug": "arm-receptacle",
    "arm-plug": "arm-receptacle",
    "test-plug": "test-receptacle",
}

RECEPTACLE_PROVISIONS = (
    "arm-receptacle-externally-accessible",
    "arm-receptacle-uniquely-keyed",
    "arm-receptacle-shorts-firing-line-when-unmated",
    "arm-receptacle-captive-retention",
    "arm-receptacle-armed-as-last-operation",
)

VERDICT_MET = "power-plug-provisions-met"
VERDICT_NOT_MET = "power-plug-provisions-not-met"

DEFAULT_POWER_PLUG_POLICY = {
    "all_fire_current_margin": 1.5,
    "line_drop_fraction_limit": 0.25,
    "required_receptacle_provisions": RECEPTACLE_PROVISIONS,
    "require_distinct_keying": True,
    "require_distinct_colour": True,
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


def _require_non_negative(name, value):
    if not _is_finite_number(value):
        raise ValueError("%s must be a finite number, got %r" % (name, value))
    if value < 0.0:
        raise ValueError("%s must not be negative, got %r" % (name, value))
    return float(value)


def _require_count(name, value):
    if not isinstance(value, int) or isinstance(value, bool):
        raise ValueError("%s must be an integer, got %r" % (name, value))
    if value < 1:
        raise ValueError("%s must be at least one, got %r" % (name, value))
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


def _at_least(value, limit):
    """value >= limit, absorbing floating-point representation error.

    A design sized exactly onto its requirement can land a few units in
    the last place below it once the division has run. The requirement
    itself is never relaxed; only the comparison tolerates that.
    """
    return value >= limit or math.isclose(
        value, limit, rel_tol=_REL_TOL, abs_tol=_ABS_TOL
    )


def _at_most(value, limit):
    """value <= limit, absorbing floating-point representation error."""
    return value <= limit or math.isclose(
        value, limit, rel_tol=_REL_TOL, abs_tol=_ABS_TOL
    )


def validate_power_plug_policy(policy):
    """Check a provisions policy carries sane limits for all three parts."""
    if not isinstance(policy, dict):
        raise ValueError("policy must be a mapping, got %r" % (policy,))
    margin = _require_positive(
        "all_fire_current_margin", policy.get("all_fire_current_margin")
    )
    if margin < 1.0:
        raise ValueError(
            "all_fire_current_margin must be at least unity, got %g" % margin
        )
    fraction = _require_positive(
        "line_drop_fraction_limit", policy.get("line_drop_fraction_limit")
    )
    if fraction >= 1.0:
        raise ValueError(
            "line_drop_fraction_limit must stay below unity, got %g" % fraction
        )
    provisions = policy.get("required_receptacle_provisions")
    if not isinstance(provisions, (list, tuple)) or not provisions:
        raise ValueError(
            "policy required_receptacle_provisions must be a non-empty sequence"
        )
    for provision in provisions:
        _require_choice("receptacle provision", provision, RECEPTACLE_PROVISIONS)
    _require_bool("require_distinct_keying", policy.get("require_distinct_keying"))
    _require_bool("require_distinct_colour", policy.get("require_distinct_colour"))
    return policy


def firing_loop_resistance_ohm(
    source_resistance_ohm, harness_resistance_ohm, bridge_resistance_ohm, initiator_count
):
    """Loop resistance seen by the source with n bridges in parallel."""
    source = _require_non_negative("source_resistance_ohm", source_resistance_ohm)
    harness = _require_non_negative("harness_resistance_ohm", harness_resistance_ohm)
    bridge = _require_positive("bridge_resistance_ohm", bridge_resistance_ohm)
    count = _require_count("initiator_count", initiator_count)
    return source + harness + (bridge / float(count))


def delivered_bridge_current_a(
    source_voltage_v,
    source_resistance_ohm,
    harness_resistance_ohm,
    bridge_resistance_ohm,
    initiator_count,
):
    """Current reaching each bridge when n initiators fire together."""
    voltage = _require_positive("source_voltage_v", source_voltage_v)
    loop = firing_loop_resistance_ohm(
        source_resistance_ohm,
        harness_resistance_ohm,
        bridge_resistance_ohm,
        initiator_count,
    )
    count = _require_count("initiator_count", initiator_count)
    total_current = voltage / loop
    return total_current / float(count)


def line_drop_fraction(
    source_resistance_ohm, harness_resistance_ohm, bridge_resistance_ohm, initiator_count
):
    """Share of the source voltage lost outside the bridges."""
    source = _require_non_negative("source_resistance_ohm", source_resistance_ohm)
    harness = _require_non_negative("harness_resistance_ohm", harness_resistance_ohm)
    loop = firing_loop_resistance_ohm(
        source_resistance_ohm,
        harness_resistance_ohm,
        bridge_resistance_ohm,
        initiator_count,
    )
    return (source + harness) / loop


def assess_power_provisions(case, policy=DEFAULT_POWER_PLUG_POLICY):
    """Grade the firing power source against the all-fire demand."""
    validate_power_plug_policy(policy)
    if not isinstance(case, dict):
        raise ValueError("power case must be a mapping, got %r" % (case,))
    all_fire = _require_positive("all_fire_current_a", case.get("all_fire_current_a"))
    count = _require_count("initiator_count", case.get("initiator_count"))
    delivered = delivered_bridge_current_a(
        case.get("source_voltage_v"),
        case.get("source_resistance_ohm"),
        case.get("harness_resistance_ohm"),
        case.get("bridge_resistance_ohm"),
        count,
    )
    drop = line_drop_fraction(
        case.get("source_resistance_ohm"),
        case.get("harness_resistance_ohm"),
        case.get("bridge_resistance_ohm"),
        count,
    )
    required = all_fire * policy["all_fire_current_margin"]
    findings = []
    current_ok = _at_least(delivered, required)
    if not current_ok:
        findings.append(
            "delivered bridge current %.4g A is below the required %.4g A "
            "(all-fire %.4g A times a margin of %.2f) with %d initiator(s) "
            "firing together" % (delivered, required, all_fire, policy["all_fire_current_margin"], count)
        )
    drop_ok = _at_most(drop, policy["line_drop_fraction_limit"])
    if not drop_ok:
        findings.append(
            "source and harness take %.1f%% of the firing voltage, above the "
            "allowed %.1f%%" % (100.0 * drop, 100.0 * policy["line_drop_fraction_limit"])
        )
    return {
        "part": "power-provisions",
        "initiator_count": count,
        "delivered_current_a": delivered,
        "required_current_a": required,
        "line_drop_fraction": drop,
        "compliant": not findings,
        "findings": findings,
    }


def assess_arm_receptacle(provisions, policy=DEFAULT_POWER_PLUG_POLICY):
    """Walk the closed set of arm-receptacle provisions."""
    validate_power_plug_policy(policy)
    if not isinstance(provisions, dict):
        raise ValueError("provisions must be a mapping, got %r" % (provisions,))
    for key in provisions:
        _require_choice("receptacle provision", key, RECEPTACLE_PROVISIONS)
    present = []
    absent = []
    for provision in policy["required_receptacle_provisions"]:
        state = provisions.get(provision)
        if state is None:
            raise ValueError("receptacle provision %s is undeclared" % provision)
        _require_bool("receptacle provision %s" % provision, state)
        (present if state else absent).append(provision)
    findings = [
        "required arm-receptacle provision not implemented: %s" % provision
        for provision in absent
    ]
    return {
        "part": "arm-receptacle",
        "provisions_present": present,
        "provisions_absent": absent,
        "compliant": not absent,
        "findings": findings,
    }


def assess_plug_set(plugs, policy=DEFAULT_POWER_PLUG_POLICY):
    """Grade keying, identification colour and the mating matrix."""
    validate_power_plug_policy(policy)
    if not isinstance(plugs, dict):
        raise ValueError("plugs must be a mapping, got %r" % (plugs,))
    for key in plugs:
        _require_choice("plug kind", key, PLUG_KINDS)
    missing = [kind for kind in PLUG_KINDS if kind not in plugs]
    if missing:
        raise ValueError("plug set is missing: %s" % ", ".join(missing))
    keying = {}
    colours = {}
    findings = []
    for kind in PLUG_KINDS:
        entry = plugs[kind]
        if not isinstance(entry, dict):
            raise ValueError("plug %s must be a mapping, got %r" % (kind, entry))
        code = entry.get("keying_code")
        if not isinstance(code, str) or not code.strip():
            raise ValueError("plug %s needs a non-empty keying_code" % kind)
        colour = entry.get("identification_colour")
        if not isinstance(colour, str) or not colour.strip():
            raise ValueError("plug %s needs a non-empty identification_colour" % kind)
        mates = entry.get("mates_with")
        if not isinstance(mates, (list, tuple)) or not mates:
            raise ValueError("plug %s needs a non-empty mates_with sequence" % kind)
        for target in mates:
            _require_choice("plug %s mating target" % kind, target, RECEPTACLE_IDS)
        keying.setdefault(code, []).append(kind)
        colours.setdefault(colour, []).append(kind)
        expected = EXPECTED_MATING[kind]
        extra = [t for t in mates if t != expected]
        if extra:
            findings.append(
                "%s can enter %s; it is only allowed into the %s"
                % (kind, ", ".join(sorted(set(extra))), expected)
            )
        if expected not in mates:
            findings.append(
                "%s does not mate with its own %s" % (kind, expected)
            )
    if policy["require_distinct_keying"]:
        for code, kinds in sorted(keying.items()):
            if len(kinds) > 1:
                findings.append(
                    "keying code %s is shared by %s; cross-mating is not "
                    "prevented mechanically" % (code, ", ".join(sorted(kinds)))
                )
    if policy["require_distinct_colour"]:
        for colour, kinds in sorted(colours.items()):
            if len(kinds) > 1:
                findings.append(
                    "identification colour %s is shared by %s; the plugs are "
                    "not distinguishable by eye" % (colour, ", ".join(sorted(kinds)))
                )
    return {
        "part": "plug-set",
        "keying_codes": {code: sorted(kinds) for code, kinds in keying.items()},
        "identification_colours": {c: sorted(k) for c, k in colours.items()},
        "compliant": not findings,
        "findings": findings,
    }


def assess_power_plug_receptacle_provisions(case, policy=DEFAULT_POWER_PLUG_POLICY):
    """Full clause 4.10.6 to 4.10.10 walk with an overall verdict."""
    validate_power_plug_policy(policy)
    if not isinstance(case, dict):
        raise ValueError("case must be a mapping, got %r" % (case,))
    parts = {
        "power-provisions": assess_power_provisions(
            case.get("power_provisions") or {}, policy
        ),
        "arm-receptacle": assess_arm_receptacle(
            case.get("receptacle_provisions") or {}, policy
        ),
        "plug-set": assess_plug_set(case.get("plugs") or {}, policy),
    }
    findings = []
    failed = []
    for name in ("power-provisions", "arm-receptacle", "plug-set"):
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
