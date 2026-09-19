"""Mission-phase breakdown and per-phase thermal environment inputs.

Anchor: ECSS-E-ST-31 clause 4.1 -- enumerating the mission phases a thermal
control subsystem is designed against, from ground handling and pre-launch
through ascent, transfer, docking and operations to descent and post-landing,
and attaching to each phase the environment inputs its role demands.
Paraphrased into an implementable procedure; no standard text is reproduced.

Procedure implemented here
--------------------------
1. Validate each phase: name, role, start and end.
2. Detect gaps and overlaps in the ordered timeline.
3. Compare the roles present with the roles the mission profile requires.
4. Check each phase for the environment inputs its role demands.
5. Range-check every environment value that is present.
6. Build the mission sink-temperature envelope and attribute both ends.
7. Report coverage arithmetic and every finding.
"""

import math

__all__ = [
    "ROLE_GROUND",
    "ROLE_PRE_LAUNCH",
    "ROLE_ASCENT",
    "ROLE_TRANSFER",
    "ROLE_DOCKED",
    "ROLE_OPERATIONAL",
    "ROLE_DESCENT",
    "ROLE_POST_LANDING",
    "PHASE_ROLES",
    "ATMOSPHERIC_ROLES",
    "ORBITAL_ROLES",
    "GROUND_ROLES",
    "REQUIRED_INPUTS",
    "TIME_TOLERANCE_H",
    "validate_phase",
    "validate_phase_set",
    "timeline_findings",
    "missing_roles",
    "missing_environment_inputs",
    "sink_envelope",
    "define_mission_thermal_environment",
]

ROLE_GROUND = "ground"
ROLE_PRE_LAUNCH = "pre-launch"
ROLE_ASCENT = "ascent"
ROLE_TRANSFER = "transfer"
ROLE_DOCKED = "docked"
ROLE_OPERATIONAL = "operational"
ROLE_DESCENT = "descent"
ROLE_POST_LANDING = "post-landing"

PHASE_ROLES = (
    ROLE_GROUND,
    ROLE_PRE_LAUNCH,
    ROLE_ASCENT,
    ROLE_TRANSFER,
    ROLE_DOCKED,
    ROLE_OPERATIONAL,
    ROLE_DESCENT,
    ROLE_POST_LANDING,
)

GROUND_ROLES = (ROLE_GROUND, ROLE_PRE_LAUNCH, ROLE_POST_LANDING)
ATMOSPHERIC_ROLES = (ROLE_ASCENT, ROLE_DESCENT)
ORBITAL_ROLES = (ROLE_TRANSFER, ROLE_DOCKED, ROLE_OPERATIONAL)

# Environment inputs each role has to declare before an analysis case can be
# built for it. Every role carries a sink temperature and a conducted
# interface load; the rest follow the physics of the role.
_COMMON = ("sink_temperature_k", "conducted_interface_w")
REQUIRED_INPUTS = {
    ROLE_GROUND: _COMMON + ("ambient_temperature_k",),
    ROLE_PRE_LAUNCH: _COMMON + ("ambient_temperature_k", "ground_conditioning_w"),
    ROLE_ASCENT: _COMMON + ("aerothermal_flux_w_m2",),
    ROLE_TRANSFER: _COMMON + ("solar_flux_w_m2", "albedo_fraction", "planetary_ir_w_m2"),
    ROLE_DOCKED: _COMMON
    + ("solar_flux_w_m2", "albedo_fraction", "planetary_ir_w_m2", "partner_interface_w"),
    ROLE_OPERATIONAL: _COMMON
    + ("solar_flux_w_m2", "albedo_fraction", "planetary_ir_w_m2"),
    ROLE_DESCENT: _COMMON + ("aerothermal_flux_w_m2",),
    ROLE_POST_LANDING: _COMMON + ("ambient_temperature_k",),
}

# Phase durations are summed and differenced; absorb representation error at a
# boundary here rather than by widening a phase.
TIME_TOLERANCE_H = 1e-9

_NON_NEGATIVE_KEYS = (
    "solar_flux_w_m2",
    "planetary_ir_w_m2",
    "aerothermal_flux_w_m2",
    "ground_conditioning_w",
)
_POSITIVE_KEYS = ("sink_temperature_k", "ambient_temperature_k")
_UNIT_KEYS = ("albedo_fraction",)


def _real(label, value):
    """Return value as a finite float or raise ValueError."""
    if not isinstance(value, (int, float)) or isinstance(value, bool):
        raise ValueError("%s must be a real number, got %r" % (label, value))
    v = float(value)
    if not math.isfinite(v):
        raise ValueError("%s must be finite, got %r" % (label, value))
    return v


def _positive(label, value):
    v = _real(label, value)
    if v <= 0.0:
        raise ValueError("%s must be positive, got %r" % (label, value))
    return v


def _non_negative(label, value):
    v = _real(label, value)
    if v < 0.0:
        raise ValueError("%s must not be negative, got %r" % (label, value))
    return v


def _unit_closed(label, value):
    v = _real(label, value)
    if v < 0.0 or v > 1.0:
        raise ValueError("%s must lie in [0, 1], got %r" % (label, value))
    return v


def validate_phase(phase):
    """Return one validated mission phase with its range-checked environment."""
    if not isinstance(phase, dict):
        raise ValueError("phase must be a mapping")
    name = phase.get("name")
    if not isinstance(name, str) or not name.strip():
        raise ValueError("phase needs a non-empty name")
    role = phase.get("role")
    if role not in PHASE_ROLES:
        raise ValueError(
            "phase %r role must be one of %s, got %r"
            % (name, ", ".join(PHASE_ROLES), role)
        )
    start = _real("start_h of %s" % name, phase.get("start_h"))
    end = _real("end_h of %s" % name, phase.get("end_h"))
    if end <= start:
        raise ValueError("phase %r must end strictly after it starts" % name)
    environment = phase.get("environment", {})
    if not isinstance(environment, dict):
        raise ValueError("environment of %s must be a mapping" % name)
    checked = {}
    for key, value in environment.items():
        label = "%s of %s" % (key, name)
        if key in _POSITIVE_KEYS:
            checked[key] = _positive(label, value)
        elif key in _UNIT_KEYS:
            checked[key] = _unit_closed(label, value)
        elif key in _NON_NEGATIVE_KEYS:
            checked[key] = _non_negative(label, value)
        else:
            checked[key] = _real(label, value)
    return {
        "name": name.strip(),
        "role": role,
        "start_h": start,
        "end_h": end,
        "duration_h": end - start,
        "environment": checked,
    }


def validate_phase_set(phases):
    """Return the validated phases sorted by start time."""
    if not isinstance(phases, (list, tuple)) or not phases:
        raise ValueError("the mission needs at least one phase")
    out = [validate_phase(p) for p in phases]
    seen = set()
    for phase in out:
        if phase["name"] in seen:
            raise ValueError("duplicate phase name %r" % phase["name"])
        seen.add(phase["name"])
    out.sort(key=lambda p: (p["start_h"], p["name"]))
    return out


def timeline_findings(phases):
    """Return the gaps and overlaps in an ordered phase timeline."""
    gaps = []
    overlaps = []
    for i in range(1, len(phases)):
        previous = phases[i - 1]
        current = phases[i]
        delta = current["start_h"] - previous["end_h"]
        if delta > TIME_TOLERANCE_H:
            gaps.append(
                {
                    "after": previous["name"],
                    "before": current["name"],
                    "gap_h": delta,
                }
            )
        elif delta < -TIME_TOLERANCE_H:
            overlaps.append(
                {
                    "first": previous["name"],
                    "second": current["name"],
                    "overlap_h": -delta,
                }
            )
    return gaps, overlaps


def missing_roles(phases, required_roles):
    """Return the required phase roles that no phase in the set covers."""
    if not isinstance(required_roles, (list, tuple)) or not required_roles:
        raise ValueError("required_roles must be a non-empty sequence")
    for role in required_roles:
        if role not in PHASE_ROLES:
            raise ValueError("unknown required role %r" % (role,))
    present = {p["role"] for p in phases}
    return [role for role in required_roles if role not in present]


def missing_environment_inputs(phase):
    """Return the environment keys the phase's role demands but does not carry."""
    demanded = REQUIRED_INPUTS[phase["role"]]
    return [key for key in demanded if key not in phase["environment"]]


def sink_envelope(phases):
    """Return the mission sink-temperature envelope and the driving phases."""
    declared = [p for p in phases if "sink_temperature_k" in p["environment"]]
    if not declared:
        return None
    coldest = min(declared, key=lambda p: (p["environment"]["sink_temperature_k"], p["name"]))
    hottest = max(declared, key=lambda p: (p["environment"]["sink_temperature_k"], p["name"]))
    return {
        "minimum_k": coldest["environment"]["sink_temperature_k"],
        "minimum_phase": coldest["name"],
        "maximum_k": hottest["environment"]["sink_temperature_k"],
        "maximum_phase": hottest["name"],
        "declared_phases": len(declared),
    }


def define_mission_thermal_environment(spec):
    """Build and audit the mission-phase thermal environment definition.

    spec keys: phases (sequence), required_roles (sequence of role names).
    """
    if not isinstance(spec, dict):
        raise ValueError("spec must be a mapping")
    for key in ("phases", "required_roles"):
        if key not in spec:
            raise ValueError("spec missing required key '%s'" % key)
    phases = validate_phase_set(spec["phases"])
    absent_roles = missing_roles(phases, spec["required_roles"])
    gaps, overlaps = timeline_findings(phases)
    findings = []
    records = []
    for phase in phases:
        gaps_in_inputs = missing_environment_inputs(phase)
        records.append(
            {
                "name": phase["name"],
                "role": phase["role"],
                "start_h": phase["start_h"],
                "end_h": phase["end_h"],
                "duration_h": phase["duration_h"],
                "missing_inputs": gaps_in_inputs,
                "ready_for_analysis": not gaps_in_inputs,
            }
        )
    incomplete = [r["name"] for r in records if not r["ready_for_analysis"]]
    if absent_roles:
        findings.append(
            "no phase covers the required role(s): %s" % ", ".join(absent_roles)
        )
    for gap in gaps:
        findings.append(
            "timeline gap of %g h between %s and %s; the item exists during it"
            % (gap["gap_h"], gap["after"], gap["before"])
        )
    for overlap in overlaps:
        findings.append(
            "phases %s and %s overlap by %g h; two environments claim the same interval"
            % (overlap["first"], overlap["second"], overlap["overlap_h"])
        )
    if incomplete:
        findings.append(
            "environment inputs missing for: %s" % ", ".join(sorted(incomplete))
        )
    span = phases[-1]["end_h"] - phases[0]["start_h"]
    covered = sum(p["duration_h"] for p in phases)
    return {
        "phases": records,
        "phase_count": len(records),
        "span_h": span,
        "covered_h": covered,
        "uncovered_h": sum(g["gap_h"] for g in gaps),
        "gaps": gaps,
        "overlaps": overlaps,
        "missing_roles": absent_roles,
        "sink_envelope": sink_envelope(phases),
        "complete": not findings,
        "findings": findings,
    }
