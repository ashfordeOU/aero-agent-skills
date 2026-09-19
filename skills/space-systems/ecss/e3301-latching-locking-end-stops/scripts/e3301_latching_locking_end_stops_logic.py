"""Latching, locking and end stops over the full travel of a mechanism.

Anchor: ECSS-E-ST-33-01 clauses 4.7.5.4.3 and 4.7.5.4.4 (paraphrased
into an implementable procedure; no standard text is reproduced). The
energy factor below is a declared, overridable project policy value in
the shape the clause calls for.

Procedure implemented here:

1. Size each end stop on the energy that actually arrives at it, not on
   the load it would see in a static push. The moving assembly brings
   its kinetic energy; any spring still extending over the travel left
   after contact adds its stored energy; and a drive that keeps
   pushing into the stop adds the work it does over that same residual
   travel.
2. Raise the arriving energy by the policy energy factor, and grade the
   declared absorption capability against it. A declared factor below
   the floor is replaced by the floor and reported.
3. Require a stop at every travel limit the mechanism can actually
   reach. A limit that the design says is unreachable has to be argued
   in writing; an unreached limit with no stop is a finding.
4. Check that the latch capture window is where the assembly actually
   arrives, and that the worst-case overshoot does not carry it past
   the far edge of that window. A latch that the assembly flies past
   has not been shown to latch.
5. Check the locked state itself: the locking preload has to exceed the
   disturbance it holds against, and the state has to be observable, so
   that a mechanism reported as locked can be shown to be locked.

Stdlib only, offline, deterministic.
"""

# Travel limits an end stop can sit at.
VALID_TRAVEL_LIMITS = ("start", "end")

# Minimum factor applied to the energy arriving at a stop.
MIN_ENERGY_FACTOR = 1.5

# Energies and margins are products and quotients of floats, so a value
# written exactly to its bound can land a few units in the last place
# the wrong side of it. These tolerances absorb that.
FACTOR_TOLERANCE = 1.0e-12
MARGIN_TOLERANCE = 1.0e-12

VERDICT_POSITIVE = "positive"
VERDICT_ZERO = "zero"
VERDICT_NEGATIVE = "negative"


def _numeric(label, value, minimum=None):
    if not isinstance(value, (int, float)) or isinstance(value, bool):
        raise ValueError("%s must be numeric, got %r" % (label, value))
    value = float(value)
    if minimum is not None and value < minimum:
        raise ValueError("%s must be >= %r, got %r" % (label, minimum, value))
    return value


def _identifier(label, value):
    if not isinstance(value, str) or not value.strip():
        raise ValueError("%s must be a non-empty string" % label)
    return value.strip()


def _boolean(label, value):
    if not isinstance(value, bool):
        raise ValueError("%s must be a boolean, got %r" % (label, value))
    return value


def kinetic_energy(inertia, approach_rate):
    """Kinetic energy of the moving assembly arriving at a stop."""
    j = _numeric("inertia", inertia, 0.0)
    if j <= 0.0:
        raise ValueError("inertia must be positive")
    rate = _numeric("approach_rate", approach_rate, 0.0)
    return 0.5 * j * rate * rate


def work_over_residual_travel(effort, residual_travel):
    """Work a constant torque or force does over the travel left at contact."""
    value = _numeric("effort", effort, 0.0)
    travel = _numeric("residual_travel", residual_travel, 0.0)
    return value * travel


def margin_verdict(margin):
    """Group a margin within representation tolerance."""
    margin = _numeric("margin", margin)
    if margin > MARGIN_TOLERANCE:
        return VERDICT_POSITIVE
    if margin < -MARGIN_TOLERANCE:
        return VERDICT_NEGATIVE
    return VERDICT_ZERO


def validate_end_stop(stop):
    """Validate one end-stop record and return a normalized copy."""
    if not isinstance(stop, dict):
        raise ValueError("end stop must be a mapping")
    sid = _identifier("end stop id", stop.get("id"))
    limit = stop.get("travel_limit")
    if limit not in VALID_TRAVEL_LIMITS:
        raise ValueError(
            "end stop %s has unknown travel_limit %r (expected one of %s)"
            % (sid, limit, ", ".join(VALID_TRAVEL_LIMITS))
        )
    inertia = _numeric("end stop %s inertia" % sid, stop.get("inertia"), 0.0)
    if inertia <= 0.0:
        raise ValueError("end stop %s inertia must be positive" % sid)
    rate = _numeric("end stop %s approach_rate" % sid, stop.get("approach_rate"), 0.0)
    residual = _numeric(
        "end stop %s residual_travel" % sid, stop.get("residual_travel", 0.0), 0.0
    )
    spring = _numeric(
        "end stop %s stored_spring_effort" % sid,
        stop.get("stored_spring_effort", 0.0),
        0.0,
    )
    drive = _numeric(
        "end stop %s residual_drive_effort" % sid,
        stop.get("residual_drive_effort", 0.0),
        0.0,
    )
    capacity = _numeric(
        "end stop %s absorption_capacity" % sid, stop.get("absorption_capacity"), 0.0
    )
    if capacity <= 0.0:
        raise ValueError("end stop %s absorption_capacity must be positive" % sid)
    declared_factor = stop.get("declared_energy_factor")
    if declared_factor is not None:
        declared_factor = _numeric(
            "end stop %s declared_energy_factor" % sid, declared_factor, 1.0
        )
    return {
        "id": sid,
        "travel_limit": limit,
        "inertia": inertia,
        "approach_rate": rate,
        "residual_travel": residual,
        "stored_spring_effort": spring,
        "residual_drive_effort": drive,
        "absorption_capacity": capacity,
        "declared_energy_factor": declared_factor,
    }


def applied_energy_factor(stop):
    """Return (factor, findings) after holding a declared factor to the floor."""
    norm = validate_end_stop(stop)
    declared = norm["declared_energy_factor"]
    if declared is None:
        return MIN_ENERGY_FACTOR, []
    if declared < MIN_ENERGY_FACTOR - FACTOR_TOLERANCE:
        return MIN_ENERGY_FACTOR, ["declared-energy-factor-below-minimum"]
    return declared, []


def arriving_energy(stop):
    """Energy arriving at a stop, broken into its three sources."""
    norm = validate_end_stop(stop)
    kinetic = kinetic_energy(norm["inertia"], norm["approach_rate"])
    spring = work_over_residual_travel(
        norm["stored_spring_effort"], norm["residual_travel"]
    )
    driven = work_over_residual_travel(
        norm["residual_drive_effort"], norm["residual_travel"]
    )
    return {
        "kinetic": kinetic,
        "stored_spring": spring,
        "driven": driven,
        "total": kinetic + spring + driven,
    }


def required_absorption_energy(stop):
    """Arriving energy raised by the applied energy factor."""
    norm = validate_end_stop(stop)
    factor, _ = applied_energy_factor(norm)
    return arriving_energy(norm)["total"] * factor


def assess_end_stop(stop):
    """Assess one end stop against the energy-absorption requirement."""
    norm = validate_end_stop(stop)
    factor, findings = applied_energy_factor(norm)
    findings = list(findings)
    energy = arriving_energy(norm)
    required = energy["total"] * factor
    if required <= 0.0:
        findings.append("no-arriving-energy-declared")
        margin = None
        verdict = None
    else:
        margin = norm["absorption_capacity"] / required - 1.0
        verdict = margin_verdict(margin)
        if verdict == VERDICT_NEGATIVE:
            findings.append("absorption-capacity-below-required-energy")
    return {
        "id": norm["id"],
        "travel_limit": norm["travel_limit"],
        "energy": energy,
        "applied_energy_factor": factor,
        "required_energy": required,
        "absorption_capacity": norm["absorption_capacity"],
        "energy_margin": margin,
        "verdict": verdict,
        "findings": findings,
        "compliant": not findings,
    }


def validate_latch(latch):
    """Validate one latching or locking record and return a normalized copy."""
    if not isinstance(latch, dict):
        raise ValueError("latch must be a mapping")
    lid = _identifier("latch id", latch.get("id"))
    window = latch.get("capture_window")
    if not isinstance(window, (list, tuple)) or len(window) != 2:
        raise ValueError("latch %s capture_window must be a pair" % lid)
    low = _numeric("latch %s capture_window start" % lid, window[0])
    high = _numeric("latch %s capture_window end" % lid, window[1])
    if not high > low:
        raise ValueError("latch %s capture_window must be non-empty" % lid)
    arrival = _numeric("latch %s arrival_position" % lid, latch.get("arrival_position"))
    overshoot = _numeric(
        "latch %s overshoot" % lid, latch.get("overshoot", 0.0), 0.0
    )
    preload = _numeric("latch %s lock_preload" % lid, latch.get("lock_preload"), 0.0)
    if preload <= 0.0:
        raise ValueError("latch %s lock_preload must be positive" % lid)
    disturbance = _numeric(
        "latch %s disturbing_load" % lid, latch.get("disturbing_load"), 0.0
    )
    if disturbance <= 0.0:
        raise ValueError("latch %s disturbing_load must be positive" % lid)
    indicated = _boolean(
        "latch %s status_indication" % lid, latch.get("status_indication", False)
    )
    return {
        "id": lid,
        "capture_window": (low, high),
        "arrival_position": arrival,
        "overshoot": overshoot,
        "lock_preload": preload,
        "disturbing_load": disturbance,
        "status_indication": indicated,
    }


def capture_findings(latch):
    """Findings about whether the assembly arrives inside the capture window."""
    norm = validate_latch(latch)
    low, high = norm["capture_window"]
    arrival = norm["arrival_position"]
    findings = []
    if arrival < low - MARGIN_TOLERANCE or arrival > high + MARGIN_TOLERANCE:
        findings.append("arrival-outside-capture-window")
    if arrival + norm["overshoot"] > high + MARGIN_TOLERANCE:
        findings.append("overshoot-carries-past-capture-window")
    return findings


def preload_margin(latch):
    """Locking preload over the disturbance it holds against, minus one."""
    norm = validate_latch(latch)
    return norm["lock_preload"] / norm["disturbing_load"] - 1.0


def assess_latch(latch):
    """Assess one latching and locking arrangement."""
    norm = validate_latch(latch)
    findings = capture_findings(norm)
    margin = preload_margin(norm)
    verdict = margin_verdict(margin)
    if verdict == VERDICT_NEGATIVE:
        findings.append("locking-preload-below-disturbance")
    if not norm["status_indication"]:
        findings.append("locked-state-not-indicated")
    return {
        "id": norm["id"],
        "capture_window": norm["capture_window"],
        "arrival_position": norm["arrival_position"],
        "overshoot": norm["overshoot"],
        "preload_margin": margin,
        "verdict": verdict,
        "status_indication": norm["status_indication"],
        "findings": findings,
        "compliant": not findings,
    }


def assess_latching_and_end_stops(mechanism):
    """Assess the latching, locking and end-stop design of one mechanism."""
    if not isinstance(mechanism, dict):
        raise ValueError("mechanism must be a mapping")
    mid = _identifier("mechanism id", mechanism.get("id"))
    travel_range = _numeric(
        "mechanism %s travel_range" % mid, mechanism.get("travel_range"), 0.0
    )
    if travel_range <= 0.0:
        raise ValueError("mechanism %s travel_range must be positive" % mid)
    reachable = mechanism.get("reachable_limits", list(VALID_TRAVEL_LIMITS))
    if not isinstance(reachable, (list, tuple)) or not reachable:
        raise ValueError("mechanism %s needs a non-empty reachable_limits" % mid)
    for limit in reachable:
        if limit not in VALID_TRAVEL_LIMITS:
            raise ValueError("mechanism %s has unknown travel limit %r" % (mid, limit))
    stops = mechanism.get("end_stops")
    if not isinstance(stops, list) or not stops:
        raise ValueError("mechanism %s needs a non-empty end_stops list" % mid)
    latches = mechanism.get("latches", [])
    if not isinstance(latches, list):
        raise ValueError("mechanism %s latches must be a list" % mid)

    stop_results = []
    seen_stops = set()
    covered = set()
    for stop in stops:
        result = assess_end_stop(stop)
        if result["id"] in seen_stops:
            raise ValueError("duplicate end stop id %r" % (result["id"],))
        seen_stops.add(result["id"])
        covered.add(result["travel_limit"])
        stop_results.append(result)

    latch_results = []
    seen_latches = set()
    for latch in latches:
        result = assess_latch(latch)
        if result["id"] in seen_latches:
            raise ValueError("duplicate latch id %r" % (result["id"],))
        seen_latches.add(result["id"])
        latch_results.append(result)

    coverage = [
        "no-end-stop-at:%s" % limit for limit in reachable if limit not in covered
    ]
    failing_stops = [r["id"] for r in stop_results if not r["compliant"]]
    failing_latches = [r["id"] for r in latch_results if not r["compliant"]]
    return {
        "mechanism_id": mid,
        "travel_range": travel_range,
        "reachable_limits": list(reachable),
        "end_stops": stop_results,
        "latches": latch_results,
        "coverage_findings": coverage,
        "non_compliant_end_stop_ids": failing_stops,
        "non_compliant_latch_ids": failing_latches,
        "compliant": not (coverage or failing_stops or failing_latches),
    }
