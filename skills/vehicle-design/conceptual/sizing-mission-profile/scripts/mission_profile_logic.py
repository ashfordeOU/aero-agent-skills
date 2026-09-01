#!/usr/bin/env python3
"""Design mission profile definition and block fuel/time estimation logic.

Common-knowledge summary (standards-map.yaml, far-25: gated false):
conceptual aircraft sizing defines the design mission as an ordered list
of segments, each with a distinct fuel model, then sums segment fuels
into block fuel and segment times into block time. The mission fuel
fraction is block fuel divided by takeoff weight, and the required fuel
weight is block fuel plus the reserve fuel called up by the applicable
reserve rule (45 minute hold at 1500 ft plus 5 percent contingency, or
FAR 121 style alternate plus 30 minute hold).

Segment fuel models:
- taxi, takeoff, descent: fuel flow (lb/hr) times segment time (hr).
- climb: fuel flow times time, or a fraction of the segment start
  weight when only a climb fuel fraction is known.
- cruise: Breguet range equation, W_fuel = W_start * (1 - exp(-R /
  (V * TSFC * (L/D)))).
- loiter, reserve: Breguet endurance equation, W_fuel = W_start *
  (1 - exp(-E * TSFC / (L/D))).

Units are US customary, consistent with the transport-category sizing
practice the equations come from: weight W in lb, range R in nautical
miles, speed V in knots (nm/hr), time E in hours, TSFC in lb fuel per
lbf thrust per hour (treated as 1/hr with lbf and lb weight numerically
equal on Earth), lift-to-drag ratio L/D unitless. Invalid inputs raise
ValueError throughout.
"""

import math

# Segment types with distinct fuel models, in the order a design
# mission is normally flown.
SEGMENT_TYPES = ("taxi", "takeoff", "climb", "cruise", "descent",
                 "loiter", "reserve")

# Reserve rule names.
RESERVE_RULES = ("hold45_5pct", "far121")


def _require_positive(value, name):
    if value is None or value <= 0:
        raise ValueError("%s must be positive, got %r" % (name, value))
    return value


def _require_number(value, name):
    if value is None:
        raise ValueError("%s is required, got None" % (name,))
    return value


def breguet_cruise_fuel(R_nm, V_kt, TSFC, LD, W_start):
    """Fuel burned in a cruise segment (lb) by the Breguet range equation.

    W_fuel = W_start * (1 - exp(-R / (V * TSFC * (L/D)))): R_nm the
    cruise range in nautical miles, V_kt the cruise true airspeed in
    knots, TSFC the thrust specific fuel consumption in lb fuel per lbf
    thrust per hour, LD the lift-to-drag ratio, W_start the weight at
    segment start in lb. The fuel fraction falls out of the range
    equation solved for the weight ratio W_end/W_start.

    Raises ValueError if any input is not positive.
    """
    _require_positive(R_nm, "range R_nm")
    _require_positive(V_kt, "cruise speed V_kt")
    _require_positive(TSFC, "thrust specific fuel consumption TSFC")
    _require_positive(LD, "lift-to-drag ratio LD")
    _require_positive(W_start, "segment start weight W_start")
    return W_start * (1.0 - math.exp(-R_nm / (V_kt * TSFC * LD)))


def breguet_loiter_fuel(E_hr, TSFC, LD, W_start):
    """Fuel burned in a loiter or hold segment (lb) by Breguet endurance.

    W_fuel = W_start * (1 - exp(-E * TSFC / (L/D))): E_hr the loiter
    endurance in hours, TSFC in lb fuel per lbf thrust per hour, LD the
    lift-to-drag ratio in the holding configuration, W_start the weight
    at segment start in lb. Used for the loiter segment and for reserve
    holds such as 45 minutes at 1500 ft.

    Raises ValueError if any input is not positive.
    """
    _require_positive(E_hr, "loiter endurance E_hr")
    _require_positive(TSFC, "thrust specific fuel consumption TSFC")
    _require_positive(LD, "lift-to-drag ratio LD")
    _require_positive(W_start, "segment start weight W_start")
    return W_start * (1.0 - math.exp(-E_hr * TSFC / LD))


def segment_fuel(seg_type, W_start, params):
    """Fuel burned in one mission segment (lb) by segment type.

    seg_type is one of SEGMENT_TYPES and params is a dict:
    - taxi, takeoff, descent: {'fuel_flow': lb/hr, 'time': hr}.
    - climb: {'fuel_flow': lb/hr, 'time': hr} for a time-based model,
      or {'fraction': fuel fraction of W_start} for a fraction model.
    - cruise: {'R_nm': nm, 'V_kt': kt, 'TSFC': lb/lbf/hr, 'LD': -}.
    - loiter, reserve: {'E_hr': hr, 'TSFC': lb/lbf/hr, 'LD': -}.

    Returns the fuel burned in lb. Raises ValueError for an unknown
    segment type or missing/invalid parameters.
    """
    if seg_type not in SEGMENT_TYPES:
        raise ValueError("unknown segment type %r, expected one of %s"
                         % (seg_type, ", ".join(SEGMENT_TYPES)))
    _require_positive(W_start, "segment start weight W_start")
    if seg_type in ("taxi", "takeoff", "descent"):
        flow = _require_positive(params.get("fuel_flow"), "fuel_flow")
        time = _require_positive(params.get("time"), "time")
        return flow * time
    if seg_type == "climb":
        if "fraction" in params:
            frac = params["fraction"]
            if frac <= 0 or frac >= 1:
                raise ValueError(
                    "climb fuel fraction must be in (0, 1), got %r" % (frac,))
            return W_start * frac
        flow = _require_positive(params.get("fuel_flow"), "fuel_flow")
        time = _require_positive(params.get("time"), "time")
        return flow * time
    if seg_type == "cruise":
        return breguet_cruise_fuel(
            _require_positive(params.get("R_nm"), "R_nm"),
            _require_positive(params.get("V_kt"), "V_kt"),
            _require_positive(params.get("TSFC"), "TSFC"),
            _require_positive(params.get("LD"), "LD"),
            W_start)
    # loiter and reserve both use the endurance equation.
    return breguet_loiter_fuel(
        _require_positive(params.get("E_hr"), "E_hr"),
        _require_positive(params.get("TSFC"), "TSFC"),
        _require_positive(params.get("LD"), "LD"),
        W_start)


def _segment_time(seg, fuel, W_start):
    """Segment time in hours: explicit 'time' key, 'time' in params, or
    derived from params.

    Cruise time derives from range over speed (R_nm / V_kt); loiter and
    reserve time is the endurance E_hr. Taxi, takeoff, climb, and
    descent use the 'time' param (hr) their fuel model already needs.
    Raises ValueError when the time cannot be determined.
    """
    params = seg.get("params", {})
    if seg.get("time") is not None:
        t = seg["time"]
    elif params.get("time") is not None:
        t = params["time"]
    else:
        t = None
    if t is not None:
        if t <= 0:
            raise ValueError("segment time must be positive, got %r" % (t,))
        return t
    seg_type = seg["type"]
    if seg_type == "cruise":
        return (_require_positive(params.get("R_nm"), "R_nm")
                / _require_positive(params.get("V_kt"), "V_kt"))
    if seg_type in ("loiter", "reserve"):
        return _require_positive(params.get("E_hr"), "E_hr")
    raise ValueError(
        "segment %r has no time; add a 'time' key (hr) or endurance/range "
        "params" % (seg_type,))


def block_fuel_and_time(segments, W_start):
    """Block fuel (lb) and block time (hr) for an ordered mission profile.

    segments is a list of dicts, each with 'type', 'params', and an
    optional 'time' key (hr); segment fuel is computed by segment_fuel
    and the weight carried into each segment is the start weight minus
    the fuel burned in all earlier segments, so the Breguet segments
    burn from their true segment start weight. Block time is the sum of
    segment times, explicit or derived (cruise R/V, loiter E_hr).

    Returns a dict: block_fuel_lb, block_time_hr, end_weight_lb,
    segment_fuels (list in segment order), segment_times (list in
    segment order). Raises ValueError for an empty segment list, an
    unknown segment type, or invalid parameters.
    """
    if not segments:
        raise ValueError("segments must not be empty")
    _require_positive(W_start, "takeoff weight W_start")
    weight = W_start
    fuels = []
    times = []
    for seg in segments:
        seg_type = seg.get("type")
        if seg_type not in SEGMENT_TYPES:
            raise ValueError("unknown segment type %r" % (seg_type,))
        params = seg.get("params", {})
        fuel = segment_fuel(seg_type, weight, params)
        fuels.append(fuel)
        times.append(_segment_time(seg, fuel, weight))
        weight -= fuel
    if weight <= 0:
        raise ValueError("mission burns more fuel than the start weight")
    return {
        "block_fuel_lb": sum(fuels),
        "block_time_hr": sum(times),
        "end_weight_lb": weight,
        "segment_fuels": fuels,
        "segment_times": times,
    }


def reserve_fuel(W_start, rule="hold45_5pct", params=None):
    """Reserve fuel (lb) required by a reserve rule, burned from W_start.

    Rules (params is a dict):
    - hold45_5pct: 45 minute hold at 1500 ft plus 5 percent contingency
      on the trip fuel. params: TSFC, LD, trip_fuel (lb); E_hr defaults
      to 0.75 hr and contingency to 0.05. Returns the hold fuel from
      the endurance equation plus contingency * trip_fuel.
    - far121: alternate airport fuel plus a 30 minute hold at 1500 ft
      above the alternate (FAR 121.645 style). params: alternate_fuel
      (lb), TSFC, LD; E_hr defaults to 0.5 hr. Returns alternate_fuel
      plus the hold fuel.

    Raises ValueError for an unknown rule or missing/invalid params.
    """
    if rule not in RESERVE_RULES:
        raise ValueError("unknown reserve rule %r, expected one of %s"
                         % (rule, ", ".join(RESERVE_RULES)))
    _require_positive(W_start, "reserve start weight W_start")
    if params is None:
        params = {}
    TSFC = _require_positive(params.get("TSFC"), "TSFC")
    LD = _require_positive(params.get("LD"), "LD")
    if rule == "hold45_5pct":
        E_hr = params.get("E_hr", 0.75)
        contingency = params.get("contingency", 0.05)
        trip_fuel = _require_positive(params.get("trip_fuel"), "trip_fuel")
        if E_hr <= 0 or contingency < 0:
            raise ValueError("E_hr must be positive and contingency non-negative")
        hold = breguet_loiter_fuel(E_hr, TSFC, LD, W_start)
        return hold + contingency * trip_fuel
    # far121
    alternate_fuel = _require_positive(
        params.get("alternate_fuel"), "alternate_fuel")
    E_hr = params.get("E_hr", 0.5)
    if E_hr <= 0:
        raise ValueError("E_hr must be positive")
    hold = breguet_loiter_fuel(E_hr, TSFC, LD, W_start)
    return alternate_fuel + hold


def mission_fuel_fraction(segments, W_start):
    """Mission fuel fraction: block fuel divided by takeoff weight.

    The fraction of the takeoff weight burned as trip fuel over the
    design mission, the quantity the sizing weight fraction method
    chains segment by segment. Returns block_fuel_lb / W_start.

    Raises ValueError for an empty segment list or non-positive inputs.
    """
    if not segments:
        raise ValueError("segments must not be empty")
    _require_positive(W_start, "takeoff weight W_start")
    block = block_fuel_and_time(segments, W_start)
    return block["block_fuel_lb"] / W_start


def payload_range_trade_point(W_TO, OEW, W_payload, W_fuel_capacity,
                              V_kt, TSFC, LD):
    """Payload-range trade point: range at which full fuel meets payload.

    The trade point is the knee of the payload-range curve: the range
    flown at the design payload when the fuel on board equals the
    minimum of the tank capacity and the fuel the takeoff weight allows
    with payload and operating empty weight on board. Range comes from
    the Breguet range equation solved for range at that fuel,
    R = V * TSFC * LD * ln(W_TO / (W_TO - W_fuel_trade)).

    Returns a dict: fuel_lb, range_nm, payload_lb. Raises ValueError if
    payload plus OEW reaches or exceeds W_TO or any input is invalid.
    """
    _require_positive(W_TO, "takeoff weight W_TO")
    _require_positive(OEW, "operating empty weight OEW")
    _require_positive(W_payload, "payload W_payload")
    _require_positive(W_fuel_capacity, "fuel capacity W_fuel_capacity")
    _require_positive(V_kt, "cruise speed V_kt")
    _require_positive(TSFC, "thrust specific fuel consumption TSFC")
    _require_positive(LD, "lift-to-drag ratio LD")
    if OEW + W_payload >= W_TO:
        raise ValueError("OEW plus payload reaches the takeoff weight; "
                         "no fuel can be carried")
    fuel = min(W_fuel_capacity, W_TO - OEW - W_payload)
    if fuel <= 0:
        raise ValueError("no fuel can be carried at this payload")
    weight_ratio = W_TO / (W_TO - fuel)
    if weight_ratio <= 1.0:
        raise ValueError("trade point weight ratio must exceed 1")
    return {
        "fuel_lb": fuel,
        "range_nm": V_kt * TSFC * LD * math.log(weight_ratio),
        "payload_lb": W_payload,
    }


def required_fuel(segments, W_start, reserve_rule="hold45_5pct",
                  reserve_params=None):
    """Required fuel weight (lb) including reserves for a design mission.

    Block fuel and block time come from block_fuel_and_time; the
    reserve burns from the landing weight (start weight minus block
    fuel) under reserve_rule. For hold45_5pct the trip_fuel contingency
    base defaults to the block fuel when not given in reserve_params.

    Returns a dict: block_fuel_lb, block_time_hr, landing_weight_lb,
    reserve_fuel_lb, required_fuel_lb. Raises ValueError on invalid
    segments, rules, or parameters.
    """
    block = block_fuel_and_time(segments, W_start)
    landing = block["end_weight_lb"]
    params = dict(reserve_params) if reserve_params else {}
    if reserve_rule == "hold45_5pct" and "trip_fuel" not in params:
        params["trip_fuel"] = block["block_fuel_lb"]
    reserve = reserve_fuel(landing, rule=reserve_rule, params=params)
    return {
        "block_fuel_lb": block["block_fuel_lb"],
        "block_time_hr": block["block_time_hr"],
        "landing_weight_lb": landing,
        "reserve_fuel_lb": reserve,
        "required_fuel_lb": block["block_fuel_lb"] + reserve,
    }
