"""Holding torque and force dimensioning for latched and braked states.

Anchor: ECSS-E-ST-33-01 clause 4.7.5.3.3 (paraphrased into an
implementable procedure; no standard text is reproduced). The factor
values below are a declared, overridable project policy table in the
shape the clause calls for, not a transcription of the standard.

Procedure implemented here:

1. Treat every held state as its own case. A mechanism can be latched
   at the end of deployment, held on a powered brake during slew, held
   on an unpowered brake after a power loss and held by self-locking
   gearing at rest; the capability and the disturbance differ in each,
   so one holding margin for the mechanism means nothing.
2. Apply the minimum uncertainty factors in both directions at once.
   The declared holding capability is knocked down, and the declared
   disturbing torque or force is raised. Applying only one of the two
   halves the intended conservatism, and the clause asks for both.
3. Price the state kind and the knowledge basis separately. A positive
   mechanical latch retains more of its capability than a friction
   clamp or a magnetic detent, and a capability measured on
   flight-standard hardware is knocked down less than one estimated
   from heritage.
4. Refuse to credit a powered brake in a state where power is not
   available. The capability is not degraded in that case, it is
   absent, so the effective capability is zero and the state is
   reported as unheld.
5. Require every held state to have been assessed at the life points
   the mechanism is dimensioned for, and report the governing state.

Stdlib only, offline, deterministic.
"""

# Held-state kinds, with the share of declared capability each retains
# before the knowledge basis is priced, and the minimum uplift each
# puts on the disturbing load.
MIN_CAPABILITY_RETENTION_BY_KIND = {
    "latched-mechanical": 0.90,
    "brake-powered": 0.80,
    "detent-magnetic": 0.75,
    "brake-unpowered": 0.70,
    "self-locking-gearing": 0.65,
    "friction-clamp": 0.60,
}
MIN_DISTURBANCE_UPLIFT_BY_KIND = {
    "latched-mechanical": 1.50,
    "brake-powered": 2.00,
    "detent-magnetic": 2.00,
    "brake-unpowered": 2.00,
    "self-locking-gearing": 2.00,
    "friction-clamp": 3.00,
}
VALID_STATE_KINDS = tuple(sorted(MIN_CAPABILITY_RETENTION_BY_KIND))

# Kinds that only hold while the mechanism is powered.
POWER_DEPENDENT_KINDS = ("brake-powered",)

# How the capability and disturbance figures were obtained, and the
# severity that basis adds. It reduces the retained capability and
# raises the disturbance by the same factor.
SEVERITY_BY_BASIS = {
    "measured-on-flight-standard-hardware": 1.00,
    "measured-on-representative-hardware": 1.10,
    "analysed-with-validated-model": 1.25,
    "estimated-from-heritage": 1.50,
}
VALID_BASES = tuple(sorted(SEVERITY_BY_BASIS))

VALID_LIFE_POINTS = ("begin-of-life", "end-of-life")
VALID_UNITS = ("torque-nm", "force-n")

# Factors are products and quotients of floats, so a declared value
# written to exactly its floor can land a few units in the last place
# the wrong side of it. These tolerances absorb that.
FACTOR_TOLERANCE = 1.0e-12
MARGIN_TOLERANCE = 1.0e-12

VERDICT_POSITIVE = "positive"
VERDICT_ZERO = "zero"
VERDICT_NEGATIVE = "negative"


def _numeric(label, value, minimum=None, maximum=None):
    if not isinstance(value, (int, float)) or isinstance(value, bool):
        raise ValueError("%s must be numeric, got %r" % (label, value))
    value = float(value)
    if minimum is not None and value < minimum:
        raise ValueError("%s must be >= %r, got %r" % (label, minimum, value))
    if maximum is not None and value > maximum:
        raise ValueError("%s must be <= %r, got %r" % (label, maximum, value))
    return value


def _identifier(label, value):
    if not isinstance(value, str) or not value.strip():
        raise ValueError("%s must be a non-empty string" % label)
    return value.strip()


def minimum_holding_factors(state_kind, basis):
    """Minimum capability retention and disturbance uplift for a held state."""
    if state_kind not in MIN_CAPABILITY_RETENTION_BY_KIND:
        raise ValueError(
            "unknown state kind %r (expected one of %s)"
            % (state_kind, ", ".join(VALID_STATE_KINDS))
        )
    if basis not in SEVERITY_BY_BASIS:
        raise ValueError(
            "unknown knowledge basis %r (expected one of %s)"
            % (basis, ", ".join(VALID_BASES))
        )
    severity = SEVERITY_BY_BASIS[basis]
    return {
        "capability_retention": MIN_CAPABILITY_RETENTION_BY_KIND[state_kind] / severity,
        "disturbance_uplift": MIN_DISTURBANCE_UPLIFT_BY_KIND[state_kind] * severity,
    }


def state_needs_power(state_kind):
    """True when the held state only holds while the mechanism is powered."""
    if state_kind not in MIN_CAPABILITY_RETENTION_BY_KIND:
        raise ValueError(
            "unknown state kind %r (expected one of %s)"
            % (state_kind, ", ".join(VALID_STATE_KINDS))
        )
    return state_kind in POWER_DEPENDENT_KINDS


def validate_held_state(state):
    """Validate one held-state record and return a normalized copy."""
    if not isinstance(state, dict):
        raise ValueError("held state must be a mapping")
    sid = _identifier("held state id", state.get("id"))
    kind = state.get("kind")
    if kind not in MIN_CAPABILITY_RETENTION_BY_KIND:
        raise ValueError(
            "held state %s has unknown kind %r (expected one of %s)"
            % (sid, kind, ", ".join(VALID_STATE_KINDS))
        )
    basis = state.get("basis")
    if basis not in SEVERITY_BY_BASIS:
        raise ValueError(
            "held state %s has unknown basis %r (expected one of %s)"
            % (sid, basis, ", ".join(VALID_BASES))
        )
    capability = _numeric(
        "held state %s holding_capability" % sid, state.get("holding_capability"), 0.0
    )
    if capability <= 0.0:
        raise ValueError("held state %s holding_capability must be positive" % sid)
    disturbance = _numeric(
        "held state %s disturbing_load" % sid, state.get("disturbing_load"), 0.0
    )
    if disturbance <= 0.0:
        raise ValueError("held state %s disturbing_load must be positive" % sid)
    power_available = state.get("power_available", True)
    if not isinstance(power_available, bool):
        raise ValueError("held state %s power_available must be a boolean" % sid)
    retention = state.get("declared_capability_retention")
    if retention is not None:
        retention = _numeric(
            "held state %s declared_capability_retention" % sid, retention, 0.0, 1.0
        )
        if retention <= 0.0:
            raise ValueError(
                "held state %s declared_capability_retention must be positive" % sid
            )
    uplift = state.get("declared_disturbance_uplift")
    if uplift is not None:
        uplift = _numeric(
            "held state %s declared_disturbance_uplift" % sid, uplift, 1.0
        )
    life_points = state.get("life_points", [])
    if not isinstance(life_points, (list, tuple)):
        raise ValueError("held state %s life_points must be a sequence" % sid)
    for point in life_points:
        if point not in VALID_LIFE_POINTS:
            raise ValueError("held state %s has unknown life point %r" % (sid, point))
    return {
        "id": sid,
        "kind": kind,
        "basis": basis,
        "holding_capability": capability,
        "disturbing_load": disturbance,
        "power_available": power_available,
        "declared_capability_retention": retention,
        "declared_disturbance_uplift": uplift,
        "life_points": [str(p) for p in life_points],
    }


def applied_holding_factors(state):
    """Return (factors, findings) after holding declared values to the floor."""
    norm = validate_held_state(state)
    floor = minimum_holding_factors(norm["kind"], norm["basis"])
    findings = []
    retention = norm["declared_capability_retention"]
    if retention is None:
        retention = floor["capability_retention"]
    elif retention > floor["capability_retention"] + FACTOR_TOLERANCE:
        findings.append("declared-capability-retention-above-minimum-severity")
        retention = floor["capability_retention"]
    uplift = norm["declared_disturbance_uplift"]
    if uplift is None:
        uplift = floor["disturbance_uplift"]
    elif uplift < floor["disturbance_uplift"] - FACTOR_TOLERANCE:
        findings.append("declared-disturbance-uplift-below-minimum")
        uplift = floor["disturbance_uplift"]
    return (
        {"capability_retention": retention, "disturbance_uplift": uplift},
        findings,
    )


def effective_holding_capability(state):
    """Return (capability, findings) after retention and the power check."""
    norm = validate_held_state(state)
    factors, findings = applied_holding_factors(norm)
    if state_needs_power(norm["kind"]) and not norm["power_available"]:
        findings = list(findings)
        findings.append("powered-hold-credited-in-an-unpowered-state")
        return 0.0, findings
    return norm["holding_capability"] * factors["capability_retention"], findings


def factored_disturbing_load(state):
    """Disturbing torque or force after its minimum uplift is applied."""
    norm = validate_held_state(state)
    factors, _ = applied_holding_factors(norm)
    return norm["disturbing_load"] * factors["disturbance_uplift"]


def holding_margin(effective_capability, factored_disturbance):
    """Effective holding capability over the factored disturbance, minus one."""
    capability = _numeric("effective_capability", effective_capability, 0.0)
    disturbance = _numeric("factored_disturbance", factored_disturbance, 0.0)
    if disturbance <= 0.0:
        raise ValueError("factored_disturbance must be positive")
    return capability / disturbance - 1.0


def margin_verdict(margin):
    """Group a holding margin within representation tolerance."""
    margin = _numeric("margin", margin)
    if margin > MARGIN_TOLERANCE:
        return VERDICT_POSITIVE
    if margin < -MARGIN_TOLERANCE:
        return VERDICT_NEGATIVE
    return VERDICT_ZERO


def life_coverage_findings(state, required_life_points):
    """Findings about the life points a held state was assessed at."""
    norm = validate_held_state(state)
    if not isinstance(required_life_points, (list, tuple)) or not required_life_points:
        raise ValueError("required_life_points must be a non-empty sequence")
    findings = []
    for point in required_life_points:
        if point not in VALID_LIFE_POINTS:
            raise ValueError("unknown required life point %r" % (point,))
        if point not in norm["life_points"]:
            findings.append("not-assessed-at:%s" % point)
    return findings


def assess_held_state(state, required_life_points=VALID_LIFE_POINTS):
    """Assess one held state against clause 4.7.5.3.3."""
    norm = validate_held_state(state)
    capability, findings = effective_holding_capability(norm)
    findings = list(findings)
    disturbance = factored_disturbing_load(norm)
    margin = holding_margin(capability, disturbance)
    verdict = margin_verdict(margin)
    if verdict == VERDICT_NEGATIVE:
        findings.append("holding-margin-negative")
    findings.extend(life_coverage_findings(norm, required_life_points))
    return {
        "id": norm["id"],
        "kind": norm["kind"],
        "basis": norm["basis"],
        "effective_capability": capability,
        "factored_disturbance": disturbance,
        "holding_margin": margin,
        "verdict": verdict,
        "findings": findings,
        "compliant": not findings,
    }


def assess_holding_dimensioning(mechanism):
    """Assess every held state of one mechanism."""
    if not isinstance(mechanism, dict):
        raise ValueError("mechanism must be a mapping")
    mid = _identifier("mechanism id", mechanism.get("id"))
    units = mechanism.get("units")
    if units not in VALID_UNITS:
        raise ValueError(
            "mechanism %s has unknown units %r (expected one of %s)"
            % (mid, units, ", ".join(VALID_UNITS))
        )
    required = mechanism.get("required_life_points", list(VALID_LIFE_POINTS))
    states = mechanism.get("held_states")
    if not isinstance(states, list) or not states:
        raise ValueError("mechanism %s needs a non-empty held_states list" % mid)
    results = []
    seen = set()
    for state in states:
        result = assess_held_state(state, required)
        if result["id"] in seen:
            raise ValueError("duplicate held state id %r" % (result["id"],))
        seen.add(result["id"])
        results.append(result)
    governing = min(results, key=lambda r: r["holding_margin"])
    failing = [r["id"] for r in results if not r["compliant"]]
    unheld = [r["id"] for r in results if r["effective_capability"] == 0.0]
    return {
        "mechanism_id": mid,
        "units": units,
        "required_life_points": list(required),
        "held_states": results,
        "governing_state_id": governing["id"],
        "governing_margin": governing["holding_margin"],
        "unheld_state_ids": unheld,
        "non_compliant_state_ids": failing,
        "compliant": not failing,
    }
