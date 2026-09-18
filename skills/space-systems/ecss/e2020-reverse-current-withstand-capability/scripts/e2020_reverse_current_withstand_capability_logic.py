"""Reverse-current withstand capability of a power outlet, on-state and off-state.

Anchor: ECSS-E-ST-20-20C clause 5.2.11.1.1 -- the recommended tolerance of
current the load pushes back into an outlet, in the conducting state and in the
latched-off state alike. Paraphrased into an implementable procedure; no
standard text is reproduced.

Procedure implemented here
--------------------------
1. Validate the outlet rating, the holdup capacitance, the permitted output
   excursion and the clamp voltage, plus a pulse and a declared capability for
   each of the two states. Both states are required: a capability demonstrated
   in one of them says nothing about the other, because the return path is a
   different piece of the circuit in each.
2. Derive the recommended withstand level per state from the rated output
   current and the declared policy fractions, and compare the capability the
   design claims against it.
3. Convert the reverse pulse into the quantities the checks actually need:
   the charge it delivers, the energy the clamp absorbs at its clamping
   voltage, and the root-mean-square current a repetitive pulse train leaves in
   the return path. The conversion is driven by the declared pulse shape, since
   a triangular pulse of the same peak and duration carries half the charge of
   a rectangular one.
4. Raise the output-node excursion the charge drives into the holdup
   capacitance and compare it with the permitted excursion.
5. Grade each state on its own -- recommended-level coverage, applied peak,
   applied duration, node excursion and repetitive current -- and only then
   combine the two into an outlet verdict, so a state that fails is named.
6. Decide whether a blocking element is the answer, which it is exactly when
   the latched-off state cannot take the reverse current the load delivers.
"""

import math

__all__ = [
    "DEFAULT_WITHSTAND_POLICY",
    "PULSE_SHAPES",
    "RELATIVE_TOLERANCE",
    "STATES",
    "assess_reverse_current_withstand",
    "assess_state",
    "node_excursion_v",
    "pulse_shape_factors",
    "recommended_withstand_current_a",
    "reverse_charge_c",
    "reverse_energy_j",
    "rms_reverse_current_a",
    "validate_withstand_policy",
]

# The two states the clause asks about. Neither one covers the other.
STATES = ("on", "off")

# Shape factors for the reverse pulse. 'charge' multiplies peak*duration to get
# the delivered charge; 'mean_square' multiplies the squared peak to get the
# mean square over the pulse. An exponential pulse reads its duration as the
# decay time constant.
PULSE_SHAPES = {
    "rectangular": {"charge": 1.0, "mean_square": 1.0},
    "triangular": {"charge": 0.5, "mean_square": 1.0 / 3.0},
    "exponential": {"charge": 1.0, "mean_square": 0.5},
}

# Declared project policy: the share of the rated output current an outlet is
# recommended to tolerate back-fed in each state. A conducting outlet returns
# the current through its own pass element; a latched-off one has only whatever
# clamp or bypass the design provided, so the recommended level is lower.
DEFAULT_WITHSTAND_POLICY = {
    "recommended_fraction": {"on": 1.0, "off": 0.5},
}

RELATIVE_TOLERANCE = 1e-12


def _real(label, value):
    """Return value as a finite float or raise ValueError."""
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise ValueError("%s must be a real number, got %r" % (label, value))
    number = float(value)
    if not math.isfinite(number):
        raise ValueError("%s must be finite, got %r" % (label, value))
    return number


def _positive(label, value):
    """Return value as a strictly positive finite float."""
    number = _real(label, value)
    if number <= 0.0:
        raise ValueError("%s must be positive, got %g" % (label, number))
    return number


def _at_or_below(value, limit):
    """True when value is below limit or on it to within a relative tolerance."""
    return value < limit or math.isclose(
        value, limit, rel_tol=RELATIVE_TOLERANCE, abs_tol=0.0
    )


def _at_or_above(value, floor_value):
    """True when value is above the floor or on it to within a relative tolerance."""
    return value > floor_value or math.isclose(
        value, floor_value, rel_tol=RELATIVE_TOLERANCE, abs_tol=0.0
    )


def validate_withstand_policy(policy):
    """Return the policy after checking it covers both states with real fractions."""
    if not isinstance(policy, dict):
        raise ValueError("withstand policy must be a mapping")
    if "recommended_fraction" not in policy:
        raise ValueError("withstand policy missing required key 'recommended_fraction'")
    fractions = policy["recommended_fraction"]
    if not isinstance(fractions, dict):
        raise ValueError("recommended_fraction must be a mapping of state to fraction")
    for state in STATES:
        if state not in fractions:
            raise ValueError("recommended_fraction missing the '%s' state" % state)
        value = _real("recommended_fraction[%s]" % state, fractions[state])
        if value <= 0.0:
            raise ValueError("recommended_fraction[%s] must be positive, got %g" % (state, value))
    return policy


def recommended_withstand_current_a(rated_output_current_a, state, policy=None):
    """Return the reverse current the outlet is recommended to tolerate in a state."""
    rated = _positive("rated_output_current_a", rated_output_current_a)
    if state not in STATES:
        raise ValueError("state must be one of %s, got %r" % (", ".join(STATES), state))
    active = validate_withstand_policy(policy or DEFAULT_WITHSTAND_POLICY)
    return rated * float(active["recommended_fraction"][state])


def pulse_shape_factors(shape):
    """Return the charge and mean-square factors of a declared pulse shape."""
    if shape not in PULSE_SHAPES:
        raise ValueError(
            "pulse shape must be one of %s, got %r" % (", ".join(sorted(PULSE_SHAPES)), shape)
        )
    return PULSE_SHAPES[shape]


def reverse_charge_c(peak_a, duration_s, shape):
    """Return the charge a reverse pulse of this peak, duration and shape delivers."""
    peak = _positive("peak_a", peak_a)
    duration = _positive("duration_s", duration_s)
    return peak * duration * pulse_shape_factors(shape)["charge"]


def reverse_energy_j(peak_a, duration_s, shape, clamp_voltage_v):
    """Return the energy the clamp absorbs while it holds the reverse pulse."""
    clamp = _positive("clamp_voltage_v", clamp_voltage_v)
    return clamp * reverse_charge_c(peak_a, duration_s, shape)


def rms_reverse_current_a(peak_a, duration_s, period_s, shape):
    """Return the root-mean-square current of a repetitive reverse pulse train."""
    peak = _positive("peak_a", peak_a)
    duration = _positive("duration_s", duration_s)
    period = _positive("period_s", period_s)
    if period < duration and not math.isclose(
        period, duration, rel_tol=RELATIVE_TOLERANCE, abs_tol=0.0
    ):
        raise ValueError(
            "repetition period %g s is shorter than the pulse it repeats (%g s)"
            % (period, duration)
        )
    mean_square = pulse_shape_factors(shape)["mean_square"]
    return peak * math.sqrt(mean_square * duration / period)


def node_excursion_v(charge_c, capacitance_f):
    """Return the output-node voltage excursion a charge drives into the holdup."""
    charge = _positive("charge_c", charge_c)
    capacitance = _positive("capacitance_f", capacitance_f)
    return charge / capacitance


def _validate_pulse(pulse, state):
    """Return the validated pulse description for a state."""
    if not isinstance(pulse, dict):
        raise ValueError("the '%s' state needs a pulse mapping" % state)
    for key in ("peak_a", "duration_s", "shape"):
        if key not in pulse:
            raise ValueError("the '%s' state pulse is missing '%s'" % (state, key))
    _positive("%s pulse peak_a" % state, pulse["peak_a"])
    _positive("%s pulse duration_s" % state, pulse["duration_s"])
    pulse_shape_factors(pulse["shape"])
    if "period_s" in pulse:
        _positive("%s pulse period_s" % state, pulse["period_s"])
    return pulse


def _validate_capability(capability, state):
    """Return the validated declared capability for a state."""
    if not isinstance(capability, dict):
        raise ValueError("the '%s' state needs a capability mapping" % state)
    for key in ("withstand_current_a", "withstand_duration_s"):
        if key not in capability:
            raise ValueError("the '%s' state capability is missing '%s'" % (state, key))
    _positive("%s withstand_current_a" % state, capability["withstand_current_a"])
    _positive("%s withstand_duration_s" % state, capability["withstand_duration_s"])
    if "continuous_current_a" in capability:
        _positive("%s continuous_current_a" % state, capability["continuous_current_a"])
    return capability


def assess_state(state, pulse, capability, rated_output_current_a, capacitance_f,
                 excursion_limit_v, clamp_voltage_v, policy=None):
    """Grade one state against the reverse pulse the load delivers into it."""
    if state not in STATES:
        raise ValueError("state must be one of %s, got %r" % (", ".join(STATES), state))
    pulse = _validate_pulse(pulse, state)
    capability = _validate_capability(capability, state)
    capacitance = _positive("capacitance_f", capacitance_f)
    excursion_limit = _positive("excursion_limit_v", excursion_limit_v)

    recommended = recommended_withstand_current_a(rated_output_current_a, state, policy)
    peak = float(pulse["peak_a"])
    duration = float(pulse["duration_s"])
    shape = pulse["shape"]
    charge = reverse_charge_c(peak, duration, shape)
    energy = reverse_energy_j(peak, duration, shape, clamp_voltage_v)
    excursion = node_excursion_v(charge, capacitance)
    declared_current = float(capability["withstand_current_a"])
    declared_duration = float(capability["withstand_duration_s"])

    checks = [
        {
            "name": "%s-state-recommended-level-coverage" % state,
            "value": declared_current,
            "limit": recommended,
            "unit": "A",
            "passed": _at_or_above(declared_current, recommended),
        },
        {
            "name": "%s-state-applied-peak" % state,
            "value": peak,
            "limit": declared_current,
            "unit": "A",
            "passed": _at_or_below(peak, declared_current),
        },
        {
            "name": "%s-state-applied-duration" % state,
            "value": duration,
            "limit": declared_duration,
            "unit": "s",
            "passed": _at_or_below(duration, declared_duration),
        },
        {
            "name": "%s-state-output-node-excursion" % state,
            "value": excursion,
            "limit": excursion_limit,
            "unit": "V",
            "passed": _at_or_below(excursion, excursion_limit),
        },
    ]

    rms_current = None
    if "period_s" in pulse and "continuous_current_a" in capability:
        rms_current = rms_reverse_current_a(peak, duration, pulse["period_s"], shape)
        continuous = float(capability["continuous_current_a"])
        checks.append(
            {
                "name": "%s-state-repetitive-rms-current" % state,
                "value": rms_current,
                "limit": continuous,
                "unit": "A",
                "passed": _at_or_below(rms_current, continuous),
            }
        )

    findings = []
    for check in checks:
        if not check["passed"]:
            if check["name"].endswith("recommended-level-coverage"):
                findings.append(
                    "the %s-state capability %.4f A sits below the recommended level "
                    "%.4f A for this outlet rating" % (state, check["value"], check["limit"])
                )
            else:
                findings.append(
                    "%s is %.6f %s against a limit of %.6f %s"
                    % (
                        check["name"],
                        check["value"],
                        check["unit"],
                        check["limit"],
                        check["unit"],
                    )
                )

    return {
        "state": state,
        "recommended_withstand_current_a": recommended,
        "declared_withstand_current_a": declared_current,
        "declared_withstand_duration_s": declared_duration,
        "reverse_charge_c": charge,
        "clamp_energy_j": energy,
        "output_node_excursion_v": excursion,
        "repetitive_rms_current_a": rms_current,
        "checks": checks,
        "findings": findings,
        "tolerated": all(check["passed"] for check in checks),
    }


def assess_reverse_current_withstand(spec):
    """Run the clause 5.2.11.1.1 reverse-current assessment over both states.

    spec keys: rated_output_current_a, output_capacitance_f,
    excursion_limit_v, clamp_voltage_v, states (a mapping carrying an 'on' and
    an 'off' entry, each with a 'pulse' and a 'capability'), and optionally
    withstand_policy.
    """
    if not isinstance(spec, dict):
        raise ValueError("spec must be a mapping")
    for key in (
        "rated_output_current_a",
        "output_capacitance_f",
        "excursion_limit_v",
        "clamp_voltage_v",
        "states",
    ):
        if key not in spec:
            raise ValueError("spec missing required key '%s'" % key)
    states = spec["states"]
    if not isinstance(states, dict):
        raise ValueError("spec['states'] must be a mapping of state to case")
    for state in STATES:
        if state not in states:
            raise ValueError(
                "spec['states'] must cover both states; '%s' is missing and a "
                "capability in one state does not demonstrate the other" % state
            )

    policy = validate_withstand_policy(spec.get("withstand_policy", DEFAULT_WITHSTAND_POLICY))
    results = {}
    findings = []
    for state in STATES:
        case = states[state]
        if not isinstance(case, dict) or "pulse" not in case or "capability" not in case:
            raise ValueError("the '%s' state needs both a 'pulse' and a 'capability'" % state)
        results[state] = assess_state(
            state,
            case["pulse"],
            case["capability"],
            spec["rated_output_current_a"],
            spec["output_capacitance_f"],
            spec["excursion_limit_v"],
            spec["clamp_voltage_v"],
            policy,
        )
        findings.extend(results[state]["findings"])

    off_peak_check = [
        c for c in results["off"]["checks"] if c["name"] == "off-state-applied-peak"
    ][0]
    off_coverage_check = [
        c
        for c in results["off"]["checks"]
        if c["name"] == "off-state-recommended-level-coverage"
    ][0]
    blocking_needed = not (off_peak_check["passed"] and off_coverage_check["passed"])
    if blocking_needed:
        findings.append(
            "the latched-off outlet cannot take the reverse current the load delivers, "
            "so a blocking or bypass element in the return path is the design answer "
            "rather than a larger clamp"
        )

    tolerated = all(results[state]["tolerated"] for state in STATES)
    return {
        "verdict": "reverse-current-tolerated" if tolerated else "reverse-current-not-tolerated",
        "tolerated": tolerated,
        "states": results,
        "blocking_element_recommended": blocking_needed,
        "findings": findings,
    }
