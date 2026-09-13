#!/usr/bin/env python3
"""ECSS-E-ST-20-06C clause 7.1 -- secondary arcs on a photovoltaic array.

Deterministic, offline, stdlib-only implementation of the clause 7.1
description: place a recorded discharge event in the non-sustained,
temporary-sustained or permanent-sustained family from its duration and
how it ended, decide where on the array the clause 7 provisions apply,
evaluate the arc-sustaining threshold for the site conditions, size the
capacitive energy released by a non-sustained flashover, and derive the
provisions a credible sustained arc imposes.

Paraphrased procedure; no verbatim standard text. The clause is the
anchor only.
"""

import math

# --- event families ------------------------------------------------------

ARC_CATEGORIES = ("non-sustained", "temporary-sustained", "permanent-sustained")

ARC_CATEGORY_NOTES = {
    "non-sustained": (
        "flashover of the stored surface charge that stops on its own once "
        "that charge is spent; the generator never takes the arc over"
    ),
    "temporary-sustained": (
        "the generator feeds the arc after the primary event, then the arc "
        "extinguishes on its own before the string is disconnected"
    ),
    "permanent-sustained": (
        "the generator keeps the arc alive until the string is disconnected "
        "or the bus is removed; the site is normally lost"
    ),
}

TERMINATIONS = {
    "self-extinction": "self",
    "string-disconnection": "external",
    "bus-power-removal": "external",
    "still-arcing-at-record-end": "external",
}

NON_SUSTAINED_MAX_S = 1.0e-3

# --- array geography -----------------------------------------------------

ARRAY_LOCATIONS = {
    "cell-to-cell-gap": True,
    "string-to-string-gap": True,
    "cell-interconnect": True,
    "coverglass-edge": True,
    "panel-edge-conductor": True,
    "array-bus-bar": True,
    "encapsulated-harness": False,
    "internal-power-electronics": False,
    "battery-interface": False,
}

# arc-sustaining threshold: string current (A) -> minimum gap potential (V)
SUSTAINING_THRESHOLD_TABLE = (
    (0.10, 130.0),
    (0.25, 100.0),
    (0.50, 80.0),
    (1.00, 60.0),
    (2.00, 45.0),
    (4.00, 35.0),
)

SITE_CONDITION_FACTORS = {
    "pristine": 1.00,
    "contaminated": 0.85,
    "carbonized-track": 0.60,
}

GAP_REFERENCE_MM = 1.0
GAP_EXPONENT = 0.5
GAP_FACTOR_CAP = 3.0

PROVISIONS = {
    "sustained-arc-credible": (
        "increase-the-conductor-gap",
        "limit-the-string-to-string-potential",
        "fill-or-encapsulate-the-gap",
        "qualify-the-section-by-secondary-arc-testing",
    ),
    "non-sustained-only": (
        "confirm-the-flashover-energy-against-the-site-damage-limit",
        "retain-the-primary-discharge-count-in-the-analysis",
    ),
    "provisions-not-applicable": (),
}


def _positive(value, label):
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise ValueError("%s must be numeric" % label)
    if math.isnan(value) or math.isinf(value):
        raise ValueError("%s must be finite" % label)
    if value <= 0.0:
        raise ValueError("%s must be positive, got %g" % (label, value))
    return float(value)


def arc_category_note(category):
    """Return the short phenomenological note for an arc family."""
    if category not in ARC_CATEGORY_NOTES:
        raise ValueError("unknown secondary-arc family '%s'" % (category,))
    return ARC_CATEGORY_NOTES[category]


def termination_kind(termination):
    """Return 'self' or 'external' for how an arc event ended."""
    if not isinstance(termination, str):
        raise ValueError("termination must be a string, got %r" % (termination,))
    try:
        return TERMINATIONS[termination]
    except KeyError:
        raise ValueError("unknown arc termination '%s'" % termination)


def categorize_arc_event(event):
    """Place one recorded discharge event in its secondary-arc family."""
    if not isinstance(event, dict):
        raise ValueError("event must be a mapping")
    for key in ("duration_s", "terminated_by"):
        if key not in event:
            raise ValueError("event missing required key '%s'" % key)
    duration = _positive(event["duration_s"], "event duration")
    kind = termination_kind(event["terminated_by"])
    if kind == "external":
        return "permanent-sustained"
    if duration < NON_SUSTAINED_MAX_S or math.isclose(
        duration, NON_SUSTAINED_MAX_S, rel_tol=1e-12
    ):
        return "non-sustained"
    return "temporary-sustained"


def is_sustained(category):
    """True for the two families in which the generator feeds the arc."""
    if category not in ARC_CATEGORIES:
        raise ValueError("unknown secondary-arc family '%s'" % (category,))
    return category != "non-sustained"


def sustaining_threshold_voltage(string_current_a):
    """Minimum gap potential able to sustain an arc at a string current.

    Below the lowest tabulated current the generator cannot feed an arc at
    any potential, so the threshold is unbounded; above the highest
    tabulated current the threshold holds at the tabulated floor.
    """
    current = _positive(string_current_a, "string current")
    low_current, low_voltage = SUSTAINING_THRESHOLD_TABLE[0]
    high_current, high_voltage = SUSTAINING_THRESHOLD_TABLE[-1]
    if current < low_current and not math.isclose(current, low_current, rel_tol=1e-12):
        return math.inf
    if current >= high_current:
        return high_voltage
    for (c0, v0), (c1, v1) in zip(
        SUSTAINING_THRESHOLD_TABLE, SUSTAINING_THRESHOLD_TABLE[1:]
    ):
        if c0 <= current <= c1:
            span = math.log(c1 / c0)
            weight = math.log(current / c0) / span
            return math.exp(math.log(v0) + weight * (math.log(v1) - math.log(v0)))
    return low_voltage


def site_threshold_voltage(string_current_a, gap_mm, site_condition="pristine"):
    """Arc-sustaining threshold corrected for gap width and site condition."""
    base = sustaining_threshold_voltage(string_current_a)
    gap = _positive(gap_mm, "conductor gap")
    if site_condition not in SITE_CONDITION_FACTORS:
        raise ValueError("unknown site condition '%s'" % (site_condition,))
    if base == math.inf:
        return math.inf
    gap_factor = min((gap / GAP_REFERENCE_MM) ** GAP_EXPONENT, GAP_FACTOR_CAP)
    return base * gap_factor * SITE_CONDITION_FACTORS[site_condition]


def provisions_apply(location, plasma_exposed, differential_voltage_v,
                     string_current_a):
    """Decide whether the clause 7 array provisions reach a given site."""
    if location not in ARRAY_LOCATIONS:
        raise ValueError("unknown array location '%s'" % (location,))
    if not isinstance(plasma_exposed, bool):
        raise ValueError("plasma_exposed must be boolean")
    voltage = _positive(differential_voltage_v, "differential potential")
    current = _positive(string_current_a, "string current")
    if not ARRAY_LOCATIONS[location]:
        return {"applies": False, "reason": "site-is-not-an-array-surface"}
    if not plasma_exposed:
        return {"applies": False, "reason": "no-plasma-access-to-trigger-a-primary-event"}
    floor_current = SUSTAINING_THRESHOLD_TABLE[0][0]
    floor_voltage = SUSTAINING_THRESHOLD_TABLE[-1][1]
    if current < floor_current and not math.isclose(
        current, floor_current, rel_tol=1e-12
    ):
        return {"applies": False, "reason": "string-current-cannot-feed-an-arc"}
    if voltage < floor_voltage and not math.isclose(
        voltage, floor_voltage, rel_tol=1e-12
    ):
        return {"applies": False, "reason": "differential-potential-below-the-arc-floor"}
    return {"applies": True, "reason": "clause-7-provisions-apply"}


def flashover_energy_j(site_capacitance_f, differential_voltage_v):
    """Capacitive energy released by a non-sustained flashover, in joules."""
    capacitance = _positive(site_capacitance_f, "site capacitance")
    voltage = _positive(differential_voltage_v, "differential potential")
    return 0.5 * capacitance * voltage ** 2


def energy_within_limit(energy_j, limit_j):
    """True when a flashover energy sits at or below the site damage limit.

    The energy is a product of squared floating-point quantities, so an
    exactly compliant site can land a few units in the last place high;
    that representation error is absorbed here rather than by raising the
    damage limit.
    """
    energy = _positive(energy_j, "flashover energy")
    limit = _positive(limit_j, "damage limit")
    return energy < limit or math.isclose(energy, limit, rel_tol=1e-12)


def evaluate_string_pair(pair):
    """Categorise the secondary-arc risk of one adjacent-conductor pair."""
    if not isinstance(pair, dict):
        raise ValueError("pair must be a mapping")
    for key in ("location", "plasma_exposed", "differential_voltage_v",
                "string_current_a", "gap_mm"):
        if key not in pair:
            raise ValueError("pair missing required key '%s'" % key)
    applicability = provisions_apply(
        pair["location"],
        pair["plasma_exposed"],
        pair["differential_voltage_v"],
        pair["string_current_a"],
    )
    if not applicability["applies"]:
        return {
            "location": pair["location"],
            "risk": "provisions-not-applicable",
            "reason": applicability["reason"],
            "threshold_v": None,
            "provisions": PROVISIONS["provisions-not-applicable"],
        }
    threshold = site_threshold_voltage(
        pair["string_current_a"], pair["gap_mm"],
        pair.get("site_condition", "pristine"),
    )
    voltage = float(pair["differential_voltage_v"])
    credible = threshold != math.inf and (
        voltage > threshold or math.isclose(voltage, threshold, rel_tol=1e-12)
    )
    risk = "sustained-arc-credible" if credible else "non-sustained-only"
    return {
        "location": pair["location"],
        "risk": risk,
        "reason": applicability["reason"],
        "threshold_v": threshold,
        "provisions": PROVISIONS[risk],
    }


def required_provisions(risk):
    """Return the provisions a risk category imposes on the design."""
    if risk not in PROVISIONS:
        raise ValueError("unknown secondary-arc risk category '%s'" % (risk,))
    return PROVISIONS[risk]


def assess_array_section(section):
    """Aggregate the clause 7.1 picture over every conductor pair of a section."""
    if not isinstance(section, dict):
        raise ValueError("section must be a mapping")
    pairs = section.get("pairs")
    if not isinstance(pairs, (list, tuple)) or not pairs:
        raise ValueError("section must carry a non-empty 'pairs' list")
    results = [evaluate_string_pair(p) for p in pairs]
    credible = [r for r in results if r["risk"] == "sustained-arc-credible"]
    findings = [
        "%s: a sustained secondary arc is credible above %.1f V"
        % (r["location"], r["threshold_v"]) for r in credible
    ]

    events = section.get("events", [])
    if not isinstance(events, (list, tuple)):
        raise ValueError("'events' must be a list when present")
    categories = [categorize_arc_event(e) for e in events]
    for event, category in zip(events, categories):
        if is_sustained(category):
            findings.append(
                "recorded event lasting %.4g s is %s"
                % (float(event["duration_s"]), category)
            )

    provisions = []
    for result in results:
        for item in result["provisions"]:
            if item not in provisions:
                provisions.append(item)

    return {
        "pair_results": results,
        "event_categories": categories,
        "sustained_arc_credible": bool(credible),
        "findings": findings,
        "provisions": provisions,
        "clear": not findings,
    }
