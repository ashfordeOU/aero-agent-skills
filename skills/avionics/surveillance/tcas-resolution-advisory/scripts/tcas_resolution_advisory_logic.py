"""TCAS II resolution advisory logic (DO-185B style summary model).

Pure stdlib implementation of the TCAS II threat detection chain used to
evaluate a resolution advisory for an own aircraft against one intruder:
sensitivity level selection from the own altitude band, the modified tau
closing time metric with the DMOD term, the horizontal threat test and the
altitude test, and the climb or descend advisory sense from the intruder
position.

The module constants are paraphrased DO-185B summary values (tau, DMOD and
ALIM per sensitivity level) for teaching and routing, never a reproduction
of the MOPS tables. Units: range in nautical miles, range rate in nautical
miles per second, altitude in feet, times in seconds.
"""

from __future__ import annotations

import math

# TCAS II sensitivity level parameters (paraphrased DO-185B summary values).
SENSITIVITY_TABLE = {
    2: {"tau": 20.0, "dmod": 0.30, "alim": 300.0},
    3: {"tau": 25.0, "dmod": 0.33, "alim": 300.0},
    4: {"tau": 30.0, "dmod": 0.48, "alim": 300.0},
    5: {"tau": 40.0, "dmod": 0.75, "alim": 350.0},
    6: {"tau": 45.0, "dmod": 1.00, "alim": 400.0},
    7: {"tau": 48.0, "dmod": 1.10, "alim": 600.0},
}

# Own altitude bands as (lower inclusive, upper exclusive, level); the top
# band is open at the upper end.
ALTITUDE_BANDS = [
    (0, 1000, 2),
    (1000, 2350, 3),
    (2350, 5000, 4),
    (5000, 10000, 5),
    (10000, 20000, 6),
    (20000, math.inf, 7),
]


def sensitivity_level(own_altitude_ft):
    """Return the TCAS II sensitivity level for the own altitude in feet.

    The first altitude band with an upper bound strictly greater than the
    altitude applies (lower bound inclusive, upper bound exclusive), so a
    band edge belongs to the higher band. Raises ValueError on a negative
    altitude.
    """
    if own_altitude_ft < 0:
        raise ValueError("own altitude must be non-negative")
    for lower, upper, level in ALTITUDE_BANDS:
        if own_altitude_ft < upper:
            return level
    raise ValueError("own altitude exceeds the sensitivity table range")


def modified_tau(range_nmi, range_rate_nmi_s, dmod_nmi):
    """Return the modified tau closing time in seconds for one encounter.

    tau_mod = -(range_nmi**2 - dmod_nmi**2) / (range_nmi * range_rate_nmi_s)
    applies to closing encounters only, so range_rate_nmi_s must be
    negative. When the range already lies at or inside the DMOD cylinder
    the encounter is an immediate threat and tau_mod returns 0.0.

    Raises ValueError when the range or the DMOD is non-positive or when
    the range rate is not negative (the encounter is not closing).
    """
    if range_nmi <= 0:
        raise ValueError("range must be positive")
    if dmod_nmi <= 0:
        raise ValueError("dmod must be positive")
    if range_rate_nmi_s >= 0:
        raise ValueError("range rate must be negative for a closing encounter")
    if range_nmi <= dmod_nmi:
        return 0.0
    return -(range_nmi ** 2 - dmod_nmi ** 2) / (range_nmi * range_rate_nmi_s)


def threat_verdict(range_nmi, range_rate_nmi_s, own_altitude_ft, intruder_altitude_ft):
    """Return the threat verdict dict for one own-intruder encounter.

    Selects the sensitivity level from the own altitude, then applies the
    horizontal threat test (modified tau against the tau threshold) and the
    altitude test (vertical separation magnitude against ALIM). A closing
    encounter that passes both tests is a threat whose sense is climb when
    the intruder sits below the own aircraft and descend when it sits
    above. A non-closing encounter reports reason "not-closing" without a
    modified tau.

    Returns a dict holding sensitivity_level, tau_threshold, dmod, alim,
    modified_tau, threat and the applicable sense or reason fields.
    """
    level = sensitivity_level(own_altitude_ft)
    params = SENSITIVITY_TABLE[level]
    vertical_separation_ft = intruder_altitude_ft - own_altitude_ft
    result = {
        "sensitivity_level": level,
        "tau_threshold": params["tau"],
        "dmod": params["dmod"],
        "alim": params["alim"],
    }
    if range_rate_nmi_s >= 0:
        result["modified_tau"] = None
        result["threat"] = False
        result["reason"] = "not-closing"
        return result
    tau_mod = modified_tau(range_nmi, range_rate_nmi_s, params["dmod"])
    result["modified_tau"] = tau_mod
    result["vertical_separation_ft"] = vertical_separation_ft
    horizontal_ok = tau_mod <= params["tau"]
    vertical_ok = abs(vertical_separation_ft) <= params["alim"]
    if horizontal_ok and vertical_ok:
        sense = "descend" if vertical_separation_ft > 0 else "climb"
        result["threat"] = True
        result["sense"] = sense
    else:
        reason = "tau-exceeded" if not horizontal_ok else "altitude-exceeded"
        result["threat"] = False
        result["reason"] = reason
    return result


def ra_sense(intruder_altitude_ft, own_altitude_ft):
    """Return the resolution advisory sense for the own aircraft.

    Descend when the intruder is above the own aircraft, climb when the
    intruder is at or below it: the advisory moves the own aircraft away
    from the intruder, and a tie at equal altitude resolves to climb.
    """
    if intruder_altitude_ft > own_altitude_ft:
        return "descend"
    return "climb"


def evaluate_encounter(range_nmi, range_rate_nmi_s, own_altitude_ft, intruder_altitude_ft):
    """Return the full resolution advisory evaluation for one encounter.

    Runs the sensitivity selection, the modified tau metric, the threat
    verdict and the advisory sense on already-measured range, range rate
    and altitude state. Returns sensitivity_level, modified_tau, threat,
    the reason or the sense, the resolution_advisory ("climb", "descend"
    or "none") and the active parameters. ValueErrors propagate unchanged.
    """
    verdict = threat_verdict(range_nmi, range_rate_nmi_s, own_altitude_ft, intruder_altitude_ft)
    result = {
        "sensitivity_level": verdict["sensitivity_level"],
        "modified_tau": verdict.get("modified_tau"),
        "threat": verdict["threat"],
        "resolution_advisory": verdict["sense"] if verdict["threat"] else "none",
        "parameters": {
            "tau": verdict["tau_threshold"],
            "dmod": verdict["dmod"],
            "alim": verdict["alim"],
        },
    }
    if verdict["threat"]:
        result["sense"] = verdict["sense"]
    else:
        result["reason"] = verdict["reason"]
    return result
