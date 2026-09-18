"""Heat-treatment state control for stress-corrosion-cracking resistance.

Anchor: ECSS-Q-ST-70-36C, the selection clauses that tie the SCC resistance of
an alloy to its temper or heat-treatment condition and require that condition
to be the one actually delivered. Paraphrased into an implementable procedure;
no standard text is reproduced.

Procedure implemented here
--------------------------
1. Look the specified alloy-and-temper state up in the resistance registry and
   read the rating that state carries.
2. Grade the verification reading that evidences the state -- electrical
   conductivity for the age-hardened aluminium tempers, hardness for the
   quench-and-tempered steels -- against the acceptance window of the
   specified temper, inclusively at both ends.
3. When the reading falls outside that window, search the registry for the
   temper of the same alloy whose window the reading does fall in; naming the
   substituted state is what makes the finding actionable.
4. Report a disposition: the state is evidenced, the reading is out of window,
   or the reading matches a different and less resistant temper than the one
   the drawing calls for.
"""

import math

__all__ = [
    "WINDOW_TOLERANCE",
    "RESISTANCE_CATEGORIES",
    "TEMPER_REGISTRY",
    "normalize_state",
    "registry_entry",
    "resistance_for_state",
    "verification_property",
    "acceptance_window",
    "within_window",
    "matching_tempers",
    "assess_state",
    "assess_states",
]

# A reading an inspector records exactly on a window edge is inside the
# window. Absorb the representation error here rather than widening the edge.
WINDOW_TOLERANCE = 1e-9

RESISTANCE_CATEGORIES = ("high", "medium", "low")

# Alloy-and-temper states, the SCC resistance each carries, and the property
# whose reading evidences the state with its inclusive acceptance window.
#   property "conductivity" is in %IACS, "hardness" is in HRC.
TEMPER_REGISTRY = {
    ("aluminium-7xxx", "t6"): {
        "resistance": "low",
        "property": "conductivity",
        "window": (30.0, 35.0),
        "note": "peak-aged, highest strength and the least resistant of the family",
    },
    ("aluminium-7xxx", "t73"): {
        "resistance": "high",
        "property": "conductivity",
        "window": (40.0, 43.0),
        "note": "fully overaged, resistance bought with a strength give-back",
    },
    ("aluminium-7xxx", "t76"): {
        "resistance": "medium",
        "property": "conductivity",
        "window": (38.0, 39.5),
        "note": "partially overaged, intermediate on both strength and resistance",
    },
    ("aluminium-2xxx", "t3"): {
        "resistance": "low",
        "property": "conductivity",
        "window": (28.0, 32.0),
        "note": "naturally aged after cold work, susceptible short-transverse",
    },
    ("aluminium-2xxx", "t8"): {
        "resistance": "medium",
        "property": "conductivity",
        "window": (36.0, 40.0),
        "note": "artificially aged after cold work, better than the naturally aged state",
    },
    ("low-alloy-steel", "tempered-high"): {
        "resistance": "high",
        "property": "hardness",
        "window": (26.0, 32.0),
        "note": "tempered back far enough that the susceptibility falls away",
    },
    ("low-alloy-steel", "tempered-low"): {
        "resistance": "low",
        "property": "hardness",
        "window": (40.0, 52.0),
        "note": "high hardness retained, treated as susceptible",
    },
    ("stainless-steel-austenitic", "solution-annealed"): {
        "resistance": "high",
        "property": "hardness",
        "window": (70.0, 90.0),
        "note": "hardness read on the HRB scale for the annealed austenitic state",
    },
    ("stainless-steel-precipitation", "h1150"): {
        "resistance": "high",
        "property": "hardness",
        "window": (28.0, 34.0),
        "note": "double-overaged condition, the resistant end of the family",
    },
    ("stainless-steel-precipitation", "h900"): {
        "resistance": "low",
        "property": "hardness",
        "window": (40.0, 47.0),
        "note": "peak-aged condition, the susceptible end of the family",
    },
}

_ALLOY_ALIASES = {
    "7xxx": "aluminium-7xxx",
    "al-7xxx": "aluminium-7xxx",
    "aluminum-7xxx": "aluminium-7xxx",
    "2xxx": "aluminium-2xxx",
    "al-2xxx": "aluminium-2xxx",
    "aluminum-2xxx": "aluminium-2xxx",
    "steel": "low-alloy-steel",
    "cres-austenitic": "stainless-steel-austenitic",
    "austenitic-stainless": "stainless-steel-austenitic",
    "ph-stainless": "stainless-steel-precipitation",
}

_TEMPER_ALIASES = {
    "t651": "t6",
    "t7351": "t73",
    "t7651": "t76",
    "t351": "t3",
    "t851": "t8",
    "annealed": "solution-annealed",
}


def _token(value, label):
    """Return a lower-cased dash-normalized token, or raise."""
    if not isinstance(value, str):
        raise ValueError("%s must be a string, got %r" % (label, type(value).__name__))
    text = value.strip().lower().replace("_", "-").replace(" ", "-")
    if not text:
        raise ValueError("%s must not be blank" % label)
    return text


def normalize_state(alloy, temper):
    """Return the canonical (alloy, temper) key for a declared state."""
    alloy_token = _token(alloy, "alloy")
    alloy_token = _ALLOY_ALIASES.get(alloy_token, alloy_token)
    temper_token = _token(temper, "temper")
    temper_token = _TEMPER_ALIASES.get(temper_token, temper_token)
    return (alloy_token, temper_token)


def registry_entry(alloy, temper):
    """Return the registry record for a state, raising when it is unknown."""
    key = normalize_state(alloy, temper)
    if key not in TEMPER_REGISTRY:
        known = sorted(t for (a, t) in TEMPER_REGISTRY if a == key[0])
        if known:
            raise ValueError(
                "temper %r is not registered for alloy %s; registered tempers are %s"
                % (temper, key[0], ", ".join(known))
            )
        raise ValueError("alloy %r is not registered for temper-state control" % (alloy,))
    return dict(TEMPER_REGISTRY[key])


def resistance_for_state(alloy, temper):
    """Return the SCC resistance rating the state carries."""
    return registry_entry(alloy, temper)["resistance"]


def verification_property(alloy, temper):
    """Return the property whose reading evidences the state."""
    return registry_entry(alloy, temper)["property"]


def acceptance_window(alloy, temper):
    """Return the inclusive (low, high) acceptance window for the state."""
    return tuple(registry_entry(alloy, temper)["window"])


def _reading(value):
    """Return a finite, positive verification reading."""
    if not isinstance(value, (int, float)) or isinstance(value, bool):
        raise ValueError("reading must be a real number")
    number = float(value)
    if not math.isfinite(number):
        raise ValueError("reading must be finite")
    if number <= 0.0:
        raise ValueError("reading must be positive, got %r" % (value,))
    return number


def within_window(reading, window):
    """Return True when a reading sits inside an inclusive window.

    Both edges belong to the window. An intended exact equality is resolved by
    the named tolerance, never by moving the edge.
    """
    if not isinstance(window, (list, tuple)) or len(window) != 2:
        raise ValueError("window must be a (low, high) pair")
    low = float(window[0])
    high = float(window[1])
    if not math.isfinite(low) or not math.isfinite(high):
        raise ValueError("window edges must be finite")
    if low > high:
        raise ValueError("window low edge %g exceeds high edge %g" % (low, high))
    value = _reading(reading)
    at_low = math.isclose(value, low, rel_tol=0.0, abs_tol=WINDOW_TOLERANCE)
    at_high = math.isclose(value, high, rel_tol=0.0, abs_tol=WINDOW_TOLERANCE)
    return bool(at_low or at_high or (low < value < high))


def matching_tempers(alloy, reading):
    """Return the tempers of an alloy whose window the reading falls in."""
    alloy_token = _token(alloy, "alloy")
    alloy_token = _ALLOY_ALIASES.get(alloy_token, alloy_token)
    value = _reading(reading)
    matches = []
    for (registered_alloy, temper), entry in sorted(TEMPER_REGISTRY.items()):
        if registered_alloy != alloy_token:
            continue
        if within_window(value, entry["window"]):
            matches.append(temper)
    return matches


def assess_state(record):
    """Assess one declared state against its verification reading."""
    if not isinstance(record, dict):
        raise ValueError("record must be a mapping")
    for key in ("id", "alloy", "temper", "reading"):
        if key not in record:
            raise ValueError("record missing required key %r" % key)
    item_id = _token(record["id"], "record id")
    alloy, temper = normalize_state(record["alloy"], record["temper"])
    entry = registry_entry(alloy, temper)
    window = tuple(entry["window"])
    reading = _reading(record["reading"])
    in_window = within_window(reading, window)
    matches = [t for t in matching_tempers(alloy, reading) if t != temper]
    findings = []
    if in_window:
        disposition = "state-evidenced"
    elif matches:
        disposition = "temper-substitution"
        substituted = matches[0]
        substituted_rating = TEMPER_REGISTRY[(alloy, substituted)]["resistance"]
        findings.append(
            "reading %g for %s sits in the %s window, not the specified %s; the "
            "delivered state is rated %s against the specified %s"
            % (
                reading,
                item_id,
                substituted,
                temper,
                substituted_rating,
                entry["resistance"],
            )
        )
    else:
        disposition = "reading-out-of-window"
        findings.append(
            "reading %g for %s falls outside the %s window [%g, %g] and matches no "
            "other registered temper of %s" % (reading, item_id, temper, window[0], window[1], alloy)
        )
    return {
        "id": item_id,
        "alloy": alloy,
        "temper": temper,
        "resistance": entry["resistance"],
        "property": entry["property"],
        "window": window,
        "reading": reading,
        "within_window": in_window,
        "substituted_tempers": matches,
        "disposition": disposition,
        "note": entry["note"],
        "findings": findings,
    }


def assess_states(records):
    """Assess a list of declared states and aggregate the dispositions."""
    if not isinstance(records, (list, tuple)) or not records:
        raise ValueError("records must be a non-empty sequence of mappings")
    assessed = []
    seen = set()
    for record in records:
        result = assess_state(record)
        if result["id"] in seen:
            raise ValueError("duplicate record id %r" % result["id"])
        seen.add(result["id"])
        assessed.append(result)
    evidenced = [r for r in assessed if r["disposition"] == "state-evidenced"]
    substituted = [r for r in assessed if r["disposition"] == "temper-substitution"]
    out_of_window = [r for r in assessed if r["disposition"] == "reading-out-of-window"]
    findings = []
    for result in assessed:
        findings.extend(result["findings"])
    return {
        "records": assessed,
        "evidenced_count": len(evidenced),
        "substitution_count": len(substituted),
        "out_of_window_count": len(out_of_window),
        "compliant": not findings,
        "findings": findings,
    }
