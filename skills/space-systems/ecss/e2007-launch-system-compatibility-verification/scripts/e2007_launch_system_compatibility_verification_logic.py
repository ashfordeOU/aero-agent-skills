#!/usr/bin/env python3
"""Launch-system electromagnetic compatibility verification and its waiver.

Anchor: ECSS-E-ST-20-07C clause 5.3.3 (launch-system compatibility
verification, waived when the spacecraft stays unpowered for the whole
ascent phase). The clause is paraphrased into an implementable
procedure; no standard text is reproduced.

Model used throughout:
  ascent window      -> liftoff to separation, a single closed interval
  powered-state      -> every unit declares phases covering that window
  waiver             -> granted only when the union of declared phases
                        covers the window for every unit AND no phase
                        leaves the unpowered state
  open requirement   -> when the waiver fails, the launcher radiated
                        emission margin is sized and a verification
                        method is named per surviving powered state

Stdlib only, deterministic, offline.
"""

import math

# --- powered states ---------------------------------------------------------

STATE_UNPOWERED = "unpowered"
STATE_PASSIVE = "passively-powered"
STATE_ACTIVE = "actively-powered"
STATE_RF = "rf-transmitting"

POWER_STATES = (STATE_UNPOWERED, STATE_PASSIVE, STATE_ACTIVE, STATE_RF)

POWER_STATE_ALIASES = {
    "unpowered": STATE_UNPOWERED,
    "off": STATE_UNPOWERED,
    "no-power": STATE_UNPOWERED,
    "power-off": STATE_UNPOWERED,
    "passively-powered": STATE_PASSIVE,
    "survival-heater": STATE_PASSIVE,
    "thermostat-heater": STATE_PASSIVE,
    "battery-trickle": STATE_PASSIVE,
    "actively-powered": STATE_ACTIVE,
    "bus-powered": STATE_ACTIVE,
    "avionics-on": STATE_ACTIVE,
    "rf-transmitting": STATE_RF,
    "transmitter-on": STATE_RF,
    "beacon-on": STATE_RF,
}

# The waiver of clause 5.3.3 rests on one state and one state only.
WAIVER_COMPATIBLE_STATES = (STATE_UNPOWERED,)

VERIFICATION_METHODS = ("inspection", "analysis", "similarity", "test")

METHODS_BY_STATE = {
    STATE_UNPOWERED: ("inspection",),
    STATE_PASSIVE: ("analysis", "test"),
    STATE_ACTIVE: ("test",),
    STATE_RF: ("test",),
}

TIME_TOLERANCE_S = 1e-9
MARGIN_TOLERANCE_DB = 1e-9


def _finite_number(value, label):
    if not isinstance(value, (int, float)) or isinstance(value, bool):
        raise ValueError("%s must be numeric" % label)
    value = float(value)
    if math.isnan(value) or math.isinf(value):
        raise ValueError("%s must be finite" % label)
    return value


# --- state categorization ---------------------------------------------------


def power_state_kind(raw_state):
    """Resolve a declared powered state to one of the four recognised kinds."""
    key = str(raw_state).strip().lower()
    if not key:
        raise ValueError("powered state must not be blank")
    if key not in POWER_STATE_ALIASES:
        raise ValueError("unrecognised powered state: %r" % (raw_state,))
    return POWER_STATE_ALIASES[key]


def state_permits_waiver(raw_state):
    """True when a state is compatible with the clause 5.3.3 waiver."""
    return power_state_kind(raw_state) in WAIVER_COMPATIBLE_STATES


# --- ascent window and intervals -------------------------------------------


def normalize_ascent_window(raw):
    """Normalize the liftoff-to-separation ascent window."""
    if not isinstance(raw, dict):
        raise ValueError("ascent window must be a mapping")
    liftoff = _finite_number(raw.get("liftoff_s"), "liftoff time")
    separation = _finite_number(raw.get("separation_s"), "separation time")
    if separation <= liftoff:
        raise ValueError("separation must occur after liftoff")
    return {"liftoff_s": liftoff, "separation_s": separation}


def clip_interval_to_window(start_s, end_s, window):
    """Clip one declared interval to the ascent window, or None if outside."""
    start = _finite_number(start_s, "phase start")
    end = _finite_number(end_s, "phase end")
    if end <= start:
        raise ValueError("phase end must follow phase start")
    low = max(start, window["liftoff_s"])
    high = min(end, window["separation_s"])
    if high <= low:
        return None
    return (low, high)


def merge_intervals(intervals):
    """Merge a set of intervals into sorted, non-overlapping spans."""
    if not isinstance(intervals, (list, tuple)):
        raise ValueError("intervals must be a list or tuple")
    spans = []
    for item in intervals:
        if not isinstance(item, (list, tuple)) or len(item) != 2:
            raise ValueError("each interval must be a (start, end) pair")
        start = _finite_number(item[0], "interval start")
        end = _finite_number(item[1], "interval end")
        if end <= start:
            raise ValueError("interval end must follow interval start")
        spans.append((start, end))
    spans.sort()
    merged = []
    for start, end in spans:
        if merged and start <= merged[-1][1] + TIME_TOLERANCE_S:
            if end > merged[-1][1]:
                merged[-1] = (merged[-1][0], end)
        else:
            merged.append((start, end))
    return tuple(merged)


def uncovered_gaps(intervals, window):
    """Parts of the ascent window no declared interval covers."""
    merged = merge_intervals(intervals)
    gaps = []
    cursor = window["liftoff_s"]
    for start, end in merged:
        if start > cursor + TIME_TOLERANCE_S:
            gaps.append((cursor, start))
        if end > cursor:
            cursor = end
    if cursor < window["separation_s"] - TIME_TOLERANCE_S:
        gaps.append((cursor, window["separation_s"]))
    return tuple(gaps)


def total_duration_s(intervals):
    """Total covered time of a set of intervals, overlaps counted once."""
    return sum(end - start for start, end in merge_intervals(intervals))


# --- unit records -----------------------------------------------------------


def normalize_unit(raw, window):
    """Normalize one spacecraft unit and its declared ascent phases."""
    if not isinstance(raw, dict):
        raise ValueError("unit record must be a mapping")
    unit_id = str(raw.get("id", "")).strip()
    if not unit_id:
        raise ValueError("unit record must carry a non-blank id")
    phases = raw.get("phases")
    if not isinstance(phases, (list, tuple)) or not phases:
        raise ValueError("unit %s declares no ascent phases" % unit_id)
    normalized = []
    for phase in phases:
        if not isinstance(phase, dict):
            raise ValueError("phase record must be a mapping")
        state = power_state_kind(phase.get("state"))
        clipped = clip_interval_to_window(
            phase.get("start_s"), phase.get("end_s"), window
        )
        if clipped is None:
            continue
        normalized.append(
            {"start_s": clipped[0], "end_s": clipped[1], "state": state}
        )
    if not normalized:
        raise ValueError("unit %s declares no phase inside the ascent window" % unit_id)
    normalized.sort(key=lambda p: p["start_s"])
    return {"id": unit_id, "phases": tuple(normalized)}


def unit_coverage_gaps(unit, window):
    """Ascent time for which a unit declares no state at all."""
    return uncovered_gaps(
        [(p["start_s"], p["end_s"]) for p in unit["phases"]], window
    )


def unit_powered_intervals(unit):
    """Intervals in which a unit is in any state other than unpowered."""
    return tuple(
        (p["start_s"], p["end_s"])
        for p in unit["phases"]
        if p["state"] != STATE_UNPOWERED
    )


def unit_powered_duration_s(unit):
    """Total time a unit spends outside the unpowered state."""
    intervals = unit_powered_intervals(unit)
    if not intervals:
        return 0.0
    return total_duration_s(list(intervals))


def unit_states(unit):
    """The distinct states a unit passes through, in canonical order."""
    seen = set(p["state"] for p in unit["phases"])
    return tuple(s for s in POWER_STATES if s in seen)


# --- waiver -----------------------------------------------------------------


def waiver_assessment(units, window):
    """Decide whether the clause 5.3.3 testing waiver may be granted."""
    if not isinstance(units, (list, tuple)) or not units:
        raise ValueError("at least one spacecraft unit record is required")
    normalized = [normalize_unit(u, window) for u in units]
    uncovered = []
    powered = []
    total_powered = 0.0
    for unit in normalized:
        if unit_coverage_gaps(unit, window):
            uncovered.append(unit["id"])
        duration = unit_powered_duration_s(unit)
        total_powered += duration
        if duration > 0.0:
            powered.append((unit["id"], unit_states(unit)))
    granted = not uncovered and not powered
    reasons = []
    for unit_id in uncovered:
        reasons.append("ascent-coverage-incomplete:%s" % unit_id)
    for unit_id, states in powered:
        for state in states:
            if state != STATE_UNPOWERED:
                reasons.append("unit-powered-during-ascent:%s:%s" % (unit_id, state))
    return {
        "granted": granted,
        "units": tuple(u["id"] for u in normalized),
        "uncovered_units": tuple(uncovered),
        "powered_units": tuple(u for u, _ in powered),
        "powered_duration_s": total_powered,
        "reasons": tuple(reasons),
    }


def required_verification_methods(states):
    """Verification methods owed by a set of surviving powered states."""
    if not isinstance(states, (list, tuple, set, frozenset)):
        raise ValueError("states must be a list, tuple or set")
    owed = set()
    for state in states:
        owed.update(METHODS_BY_STATE[power_state_kind(state)])
    return tuple(m for m in VERIFICATION_METHODS if m in owed)


# --- emission margin --------------------------------------------------------


def radiated_emission_margin_db(emission_dbuv_per_m, launcher_limit_dbuv_per_m):
    """Margin of the launcher susceptibility limit over spacecraft emission."""
    emission = _finite_number(emission_dbuv_per_m, "spacecraft emission")
    limit = _finite_number(launcher_limit_dbuv_per_m, "launcher limit")
    return limit - emission


def meets_required_margin_db(achieved_db, required_db, tolerance=MARGIN_TOLERANCE_DB):
    """True when an achieved margin reaches the required one.

    Both sides are sums and differences of decibel quantities, so an
    exactly compliant case can land a unit in the last place below the
    requirement. The representation error is absorbed here; the required
    margin itself is never lowered.
    """
    achieved = _finite_number(achieved_db, "achieved margin")
    required = _finite_number(required_db, "required margin")
    if tolerance < 0.0:
        raise ValueError("tolerance must not be negative")
    return achieved > required or math.isclose(
        achieved, required, rel_tol=0.0, abs_tol=tolerance
    )


# --- top-level verification -------------------------------------------------


def verify_launch_system_compatibility(config):
    """Run the clause 5.3.3 launch-system compatibility verification."""
    if not isinstance(config, dict):
        raise ValueError("configuration must be a mapping")
    window = normalize_ascent_window(config.get("ascent_window"))
    waiver = waiver_assessment(config.get("units"), window)

    findings = list(waiver["reasons"])
    margin_db = None
    margin_ok = None

    if waiver["granted"]:
        methods = required_verification_methods([STATE_UNPOWERED])
    else:
        surviving = set()
        for raw_unit in config.get("units"):
            unit = normalize_unit(raw_unit, window)
            for state in unit_states(unit):
                surviving.add(state)
        methods = required_verification_methods(surviving)
        emission = config.get("emission")
        if not isinstance(emission, dict):
            raise ValueError(
                "an emission record is required once the waiver is refused"
            )
        margin_db = radiated_emission_margin_db(
            emission.get("emission_dbuv_per_m"),
            emission.get("launcher_limit_dbuv_per_m"),
        )
        margin_ok = meets_required_margin_db(
            margin_db, emission.get("required_margin_db")
        )
        if not margin_ok:
            findings.append("launcher-emission-margin-shortfall")

    return {
        "ascent_duration_s": window["separation_s"] - window["liftoff_s"],
        "waiver_granted": waiver["granted"],
        "powered_duration_s": waiver["powered_duration_s"],
        "uncovered_units": waiver["uncovered_units"],
        "powered_units": waiver["powered_units"],
        "required_methods": methods,
        "emission_margin_db": margin_db,
        "margin_ok": margin_ok,
        "findings": tuple(findings),
        "acceptable": not findings,
    }
