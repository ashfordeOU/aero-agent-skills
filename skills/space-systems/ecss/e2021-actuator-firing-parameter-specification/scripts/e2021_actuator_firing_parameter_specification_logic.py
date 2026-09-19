"""Firing parameter specification for a current driven actuator.

Anchor: ECSS-E-ST-20-21C clause 5.3.1 (paraphrased into an
implementable procedure; no standard text is reproduced).

A current driven actuator is specified by a set of parameters, and two
of them define the whole safety argument. The no fire level is the
current the device is guaranteed NOT to actuate on, so everything the
rest of the spacecraft can leak into the bridge has to stay below it.
The all fire level is the current the device is guaranteed to actuate
on, so the firing circuit has to deliver above it. The band between
the two is not a design target, it is the region where the outcome is
simply not specified.

Procedure implemented here:

1. Validate the declared specification. Every parameter is a positive
   physical quantity, an unknown key is refused because a mistyped key
   silently drops the parameter it was meant to carry, and nothing is
   defaulted: a parameter that was not stated is reported as absent
   rather than guessed.
2. Check the internal consistency the two levels impose: the no fire
   level below the all fire level, the firing current above the all
   fire level, and the firing pulse at least as long as the duration
   the all fire level is specified over, because a current that is
   only applied for part of that time is not an all fire current.
3. Build the two margins the specification exists to support. The all
   fire margin is the firing current over the all fire level; the no
   fire margin is the no fire level over the largest current anything
   else can put through the bridge. Both are ratios against declared
   policy minima, not physical constants.
4. Derive the quantities a reviewer asks for next: the energy the
   firing pulse delivers into the bridge resistance, and the power the
   bridge dissipates while sitting at its no fire level.
5. Close with a completeness and consistency verdict listing every
   absent parameter and every finding.

Stdlib only, offline, deterministic.
"""

PARAMETER_UNITS = {
    "no_fire_current_a": "A",
    "all_fire_current_a": "A",
    "all_fire_duration_s": "s",
    "bridge_resistance_ohm": "ohm",
    "recommended_firing_current_a": "A",
    "firing_pulse_duration_s": "s",
    "maximum_monitoring_current_a": "A",
}

REQUIRED_PARAMETERS = (
    "no_fire_current_a",
    "all_fire_current_a",
    "all_fire_duration_s",
    "bridge_resistance_ohm",
    "recommended_firing_current_a",
    "firing_pulse_duration_s",
    "maximum_monitoring_current_a",
)

# Declared project policy, not a physical constant. The firing circuit
# is asked to sit well above the all fire level, and everything else
# well below the no fire level.
DEFAULT_MARGIN_POLICY = {
    "all_fire_margin_min": 1.5,
    "no_fire_margin_min": 2.0,
}

# A margin is a quotient of two declared floats, so a specification
# built to sit exactly on a policy minimum can land a few units in the
# last place either side of it. A part in a million million is far
# below any declared current tolerance and absorbs that representation
# error without relaxing the policy.
MARGIN_TOLERANCE = 1.0e-12

FINDING_PARAMETER_ABSENT = "firing-parameter-absent"
FINDING_NO_FIRE_NOT_BELOW_ALL_FIRE = "no-fire-not-below-all-fire"
FINDING_FIRING_BELOW_ALL_FIRE = "firing-current-not-above-all-fire"
FINDING_ALL_FIRE_MARGIN_SHORT = "all-fire-margin-short"
FINDING_NO_FIRE_MARGIN_SHORT = "no-fire-margin-short"
FINDING_PULSE_SHORTER_THAN_ALL_FIRE = "firing-pulse-shorter-than-all-fire-duration"


def _positive(label, value):
    if not isinstance(value, (int, float)) or isinstance(value, bool):
        raise ValueError("%s must be numeric, got %r" % (label, value))
    value = float(value)
    if value != value or value in (float("inf"), float("-inf")):
        raise ValueError("%s must be a finite number, got %r" % (label, value))
    if value <= 0.0:
        raise ValueError("%s must be positive, got %r" % (label, value))
    return value


def validate_specification(spec):
    """Validate a declared firing parameter set and normalize it."""
    if not isinstance(spec, dict):
        raise ValueError("specification must be a mapping, got %r" % (spec,))
    unknown = sorted(k for k in spec if k not in PARAMETER_UNITS)
    if unknown:
        raise ValueError(
            "unknown firing parameter(s): %s (expected from %s)"
            % (", ".join(unknown), ", ".join(REQUIRED_PARAMETERS))
        )
    return {key: _positive(key, spec[key]) for key in sorted(spec)}


def validate_policy(policy=None):
    """Validate the margin policy and fill in the declared default."""
    if policy is None:
        return dict(DEFAULT_MARGIN_POLICY)
    if not isinstance(policy, dict):
        raise ValueError("policy must be a mapping, got %r" % (policy,))
    unknown = sorted(k for k in policy if k not in DEFAULT_MARGIN_POLICY)
    if unknown:
        raise ValueError("unknown policy key(s): %s" % ", ".join(unknown))
    resolved = dict(DEFAULT_MARGIN_POLICY)
    for key, value in policy.items():
        minimum = _positive(key, value)
        if minimum < 1.0:
            raise ValueError("%s must be at least one, got %r" % (key, value))
        resolved[key] = minimum
    return resolved


def missing_parameters(spec):
    """Required parameters the specification does not state."""
    declared = validate_specification(spec)
    return tuple(p for p in REQUIRED_PARAMETERS if p not in declared)


def specification_completeness(spec):
    """Share of the required parameters that are stated."""
    stated = len(REQUIRED_PARAMETERS) - len(missing_parameters(spec))
    return stated / float(len(REQUIRED_PARAMETERS))


def all_fire_margin(spec):
    """Firing current over the all fire level."""
    declared = validate_specification(spec)
    for key in ("recommended_firing_current_a", "all_fire_current_a"):
        if key not in declared:
            raise ValueError("cannot build the all fire margin without %s" % key)
    return declared["recommended_firing_current_a"] / declared["all_fire_current_a"]


def no_fire_margin(spec):
    """No fire level over the largest current anything else can apply."""
    declared = validate_specification(spec)
    for key in ("no_fire_current_a", "maximum_monitoring_current_a"):
        if key not in declared:
            raise ValueError("cannot build the no fire margin without %s" % key)
    return declared["no_fire_current_a"] / declared["maximum_monitoring_current_a"]


def firing_pulse_energy_j(spec):
    """Energy the firing pulse delivers into the bridge resistance."""
    declared = validate_specification(spec)
    for key in (
        "recommended_firing_current_a",
        "bridge_resistance_ohm",
        "firing_pulse_duration_s",
    ):
        if key not in declared:
            raise ValueError("cannot compute the pulse energy without %s" % key)
    current = declared["recommended_firing_current_a"]
    return (
        current * current * declared["bridge_resistance_ohm"] * declared["firing_pulse_duration_s"]
    )


def no_fire_power_w(spec):
    """Power the bridge dissipates while sitting at its no fire level."""
    declared = validate_specification(spec)
    for key in ("no_fire_current_a", "bridge_resistance_ohm"):
        if key not in declared:
            raise ValueError("cannot compute the no fire power without %s" % key)
    current = declared["no_fire_current_a"]
    return current * current * declared["bridge_resistance_ohm"]


def _meets(value, minimum):
    """True when value reaches minimum, boundary cases absorbed."""
    return value >= minimum - abs(minimum) * MARGIN_TOLERANCE


def consistency_findings(spec, policy=None):
    """Findings against the internal consistency of the declared levels."""
    declared = validate_specification(spec)
    resolved = validate_policy(policy)
    findings = []
    have = declared.__contains__
    if have("no_fire_current_a") and have("all_fire_current_a"):
        if declared["no_fire_current_a"] >= declared["all_fire_current_a"]:
            findings.append(
                {
                    "code": FINDING_NO_FIRE_NOT_BELOW_ALL_FIRE,
                    "subject": "no_fire_current_a",
                    "detail": "the no fire level does not sit below the all fire "
                    "level, so no unspecified band exists between them",
                }
            )
    if have("recommended_firing_current_a") and have("all_fire_current_a"):
        ratio = all_fire_margin(declared)
        if declared["recommended_firing_current_a"] <= declared["all_fire_current_a"]:
            findings.append(
                {
                    "code": FINDING_FIRING_BELOW_ALL_FIRE,
                    "subject": "recommended_firing_current_a",
                    "detail": "the firing current does not exceed the all fire level",
                }
            )
        elif not _meets(ratio, resolved["all_fire_margin_min"]):
            findings.append(
                {
                    "code": FINDING_ALL_FIRE_MARGIN_SHORT,
                    "subject": "recommended_firing_current_a",
                    "detail": "all fire margin %.6f below the policy minimum %.6f"
                    % (ratio, resolved["all_fire_margin_min"]),
                }
            )
    if have("no_fire_current_a") and have("maximum_monitoring_current_a"):
        ratio = no_fire_margin(declared)
        if not _meets(ratio, resolved["no_fire_margin_min"]):
            findings.append(
                {
                    "code": FINDING_NO_FIRE_MARGIN_SHORT,
                    "subject": "maximum_monitoring_current_a",
                    "detail": "no fire margin %.6f below the policy minimum %.6f"
                    % (ratio, resolved["no_fire_margin_min"]),
                }
            )
    if have("firing_pulse_duration_s") and have("all_fire_duration_s"):
        if declared["firing_pulse_duration_s"] < declared["all_fire_duration_s"] * (
            1.0 - MARGIN_TOLERANCE
        ):
            findings.append(
                {
                    "code": FINDING_PULSE_SHORTER_THAN_ALL_FIRE,
                    "subject": "firing_pulse_duration_s",
                    "detail": "the firing pulse is shorter than the duration the "
                    "all fire level is specified over",
                }
            )
    return sorted(findings, key=lambda f: (f["code"], f["subject"]))


def assess_firing_parameter_specification(spec, policy=None):
    """Grade a declared current driven actuator firing specification."""
    declared = validate_specification(spec)
    resolved = validate_policy(policy)
    absent = missing_parameters(declared)
    findings = list(consistency_findings(declared, resolved))
    for parameter in absent:
        findings.append(
            {
                "code": FINDING_PARAMETER_ABSENT,
                "subject": parameter,
                "detail": "the specification states no %s in %s"
                % (parameter, PARAMETER_UNITS[parameter]),
            }
        )
    findings = sorted(findings, key=lambda f: (f["code"], f["subject"]))
    report = {
        "declared_parameters": tuple(sorted(declared)),
        "missing_parameters": absent,
        "completeness": specification_completeness(declared),
        "policy": resolved,
        "all_fire_margin": None,
        "no_fire_margin": None,
        "firing_pulse_energy_j": None,
        "no_fire_power_w": None,
        "findings": findings,
        "finding_codes": sorted({f["code"] for f in findings}),
        "compliant": not findings,
    }
    if not {"recommended_firing_current_a", "all_fire_current_a"} - set(declared):
        report["all_fire_margin"] = all_fire_margin(declared)
    if not {"no_fire_current_a", "maximum_monitoring_current_a"} - set(declared):
        report["no_fire_margin"] = no_fire_margin(declared)
    if not {
        "recommended_firing_current_a",
        "bridge_resistance_ohm",
        "firing_pulse_duration_s",
    } - set(declared):
        report["firing_pulse_energy_j"] = firing_pulse_energy_j(declared)
    if not {"no_fire_current_a", "bridge_resistance_ohm"} - set(declared):
        report["no_fire_power_w"] = no_fire_power_w(declared)
    return report
