"""Protective packaging and storage arrangements for bare dies awaiting assembly.

Anchor: ECSS-Q-ST-60-12C clause 10.2.5 (the carriers the dies sit in, the seal
around them, and the handling and storage conditions kept over them between
delivery and the assembly that finally uses them).
Paraphrased into an implementable procedure; no standard text is reproduced.

Procedure implemented here
--------------------------
1. Validate the storage arrangement: the carrier, the seal, whether desiccant
   and a humidity indicator are inside it, the store's temperature and
   humidity, and how much of the dies' out-of-seal floor life has been spent.
2. Score each protective barrier the arrangement provides on its own terms -
   mechanical from the carrier, moisture from the seal and its contents,
   electrostatic from the carrier material, environmental from the store.
3. Take the weakest barrier as the protection the arrangement actually gives,
   and name it. A gel pack inside an unsealed box is an unsealed box.
4. Track floor life in whole days so the arithmetic is exact: a batch whose
   floor life is exactly spent needs a bake, not a rounding argument.
5. Raise a finding for every barrier that has failed, and pair each finding
   with the action that restores it, so the batch is returned with a route
   back to usable rather than a verdict.
6. Decide whether the batch may go to assembly as it stands, may go once the
   actions are done, or is not adequately stored at all.
"""

__all__ = [
    "CARRIER_TYPES",
    "SEAL_TYPES",
    "BARRIERS",
    "ADEQUATE_INDEX",
    "CONDITIONAL_INDEX",
    "TEMPERATURE_ALLOWANCE_C",
    "DEFAULT_TEMPERATURE_LIMITS_C",
    "DEFAULT_HUMIDITY_LIMIT_PERCENT",
    "carrier_profile",
    "seal_profile",
    "validate_arrangement",
    "temperature_score",
    "humidity_score",
    "barrier_scores",
    "protection_index",
    "governing_barrier",
    "remaining_floor_life",
    "bake_required",
    "storage_findings",
    "required_actions",
    "assess_die_storage",
]

# carrier key -> mechanical protection score, electrostatic dissipative.
_CARRIER_REGISTRY = (
    ("waffle-pack", 0.90, True),
    ("gel-pack", 0.85, True),
    ("tape-and-reel", 0.80, True),
    ("wafer-frame-tape", 0.70, True),
    ("loose-tray", 0.20, False),
)

# seal key -> moisture barrier score, desiccant expected, indicator expected.
_SEAL_REGISTRY = (
    ("vacuum-moisture-barrier-bag", 0.95, True, True),
    ("dry-nitrogen-bag", 0.90, True, True),
    ("heat-sealed-barrier-bag", 0.85, True, True),
    ("resealable-bag", 0.40, False, False),
    ("unsealed", 0.00, False, False),
)

CARRIER_TYPES = tuple(entry[0] for entry in _CARRIER_REGISTRY)
SEAL_TYPES = tuple(entry[0] for entry in _SEAL_REGISTRY)

# Barrier order is also the tie-break order when two barriers score the same,
# so the governing barrier is reproducible run to run.
BARRIERS = ("mechanical", "moisture", "electrostatic", "environmental")

ADEQUATE_INDEX = 0.70
CONDITIONAL_INDEX = 0.40

# How far outside its band the store temperature has to drift before the
# environmental barrier is scored at zero.
TEMPERATURE_ALLOWANCE_C = 20.0

DEFAULT_TEMPERATURE_LIMITS_C = (15.0, 30.0)
DEFAULT_HUMIDITY_LIMIT_PERCENT = 60.0

_SCORE_TOLERANCE = 1e-9

_REQUIRED_KEYS = (
    "batch_id",
    "carrier",
    "seal",
    "storage_temperature_c",
    "storage_humidity_percent",
    "days_since_seal_opened",
    "floor_life_days",
)

_OPTIONAL_DEFAULTS = {
    "desiccant_present": False,
    "humidity_indicator_present": False,
    "moisture_sensitive": True,
    "die_count": 1,
}


def carrier_profile(key):
    """Return the mechanical score and electrostatic standing of a carrier."""
    for name, mechanical, dissipative in _CARRIER_REGISTRY:
        if name == key:
            return {"mechanical": mechanical, "dissipative": dissipative}
    raise ValueError("unknown carrier type '%s'" % (key,))


def seal_profile(key):
    """Return the moisture score and the contents a seal is expected to carry."""
    for name, moisture, desiccant, indicator in _SEAL_REGISTRY:
        if name == key:
            return {
                "moisture": moisture,
                "desiccant_expected": desiccant,
                "indicator_expected": indicator,
            }
    raise ValueError("unknown seal type '%s'" % (key,))


def _as_number(value, label):
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise ValueError("%s must be a real number" % label)
    return float(value)


def _as_whole(value, label):
    if isinstance(value, bool) or not isinstance(value, int):
        raise ValueError("%s must be a whole number of days" % label)
    if value < 0:
        raise ValueError("%s must not be negative" % label)
    return value


def validate_arrangement(spec):
    """Return the normalised storage arrangement built from spec."""
    if not isinstance(spec, dict):
        raise ValueError("storage arrangement must be a mapping")
    for key in _REQUIRED_KEYS:
        if key not in spec:
            raise ValueError("storage arrangement missing required key '%s'" % key)
    allowed = set(_REQUIRED_KEYS) | set(_OPTIONAL_DEFAULTS) | {
        "temperature_limits_c",
        "humidity_limit_percent",
    }
    for key in spec:
        if key not in allowed:
            raise ValueError("storage arrangement carries unknown key '%s'" % key)

    batch_id = spec["batch_id"]
    if not isinstance(batch_id, str) or not batch_id.strip():
        raise ValueError("batch_id must be a non-empty string")

    carrier = spec["carrier"]
    if not isinstance(carrier, str):
        raise ValueError("carrier must be a string token")
    carrier = carrier.strip().lower()
    carrier_profile(carrier)

    seal = spec["seal"]
    if not isinstance(seal, str):
        raise ValueError("seal must be a string token")
    seal = seal.strip().lower()
    seal_profile(seal)

    limits = spec.get("temperature_limits_c", DEFAULT_TEMPERATURE_LIMITS_C)
    if not isinstance(limits, (list, tuple)) or len(limits) != 2:
        raise ValueError("temperature_limits_c must be a lower and upper pair")
    lower = _as_number(limits[0], "lower temperature limit")
    upper = _as_number(limits[1], "upper temperature limit")
    if not lower < upper:
        raise ValueError("temperature limits are inverted or empty")

    humidity_limit = _as_number(
        spec.get("humidity_limit_percent", DEFAULT_HUMIDITY_LIMIT_PERCENT),
        "humidity_limit_percent",
    )
    if not 0.0 < humidity_limit < 100.0:
        raise ValueError("humidity_limit_percent must sit strictly inside 0 to 100")

    humidity = _as_number(spec["storage_humidity_percent"], "storage_humidity_percent")
    if humidity < 0.0 or humidity > 100.0:
        raise ValueError("storage_humidity_percent must sit between 0 and 100")

    arrangement = {
        "batch_id": batch_id.strip(),
        "carrier": carrier,
        "seal": seal,
        "storage_temperature_c": _as_number(
            spec["storage_temperature_c"], "storage_temperature_c"
        ),
        "storage_humidity_percent": humidity,
        "days_since_seal_opened": _as_whole(
            spec["days_since_seal_opened"], "days_since_seal_opened"
        ),
        "floor_life_days": _as_whole(spec["floor_life_days"], "floor_life_days"),
        "temperature_limits_c": (lower, upper),
        "humidity_limit_percent": humidity_limit,
    }
    if arrangement["floor_life_days"] < 1:
        raise ValueError("floor_life_days must be at least 1")

    for key, default in _OPTIONAL_DEFAULTS.items():
        value = spec.get(key, default)
        if key == "die_count":
            if isinstance(value, bool) or not isinstance(value, int):
                raise ValueError("die_count must be an integer")
            if value < 1:
                raise ValueError("die_count must be at least 1")
            arrangement[key] = value
        else:
            if not isinstance(value, bool):
                raise ValueError("%s must be a boolean" % key)
            arrangement[key] = value
    return arrangement


def _require_arrangement(arrangement):
    if not isinstance(arrangement, dict):
        raise ValueError("arrangement must be a normalised storage arrangement")
    for key in ("carrier", "seal", "temperature_limits_c", "humidity_limit_percent"):
        if key not in arrangement:
            raise ValueError("arrangement is not normalised: missing '%s'" % key)
    if not isinstance(arrangement["temperature_limits_c"], tuple):
        raise ValueError(
            "arrangement is not normalised: limits must come from validate_arrangement"
        )
    return arrangement


def temperature_score(temperature_c, limits):
    """Return the environmental score the store temperature earns, 0 to 1."""
    if not isinstance(limits, (list, tuple)) or len(limits) != 2:
        raise ValueError("limits must be a lower and upper pair")
    lower = _as_number(limits[0], "lower temperature limit")
    upper = _as_number(limits[1], "upper temperature limit")
    if not lower < upper:
        raise ValueError("temperature limits are inverted or empty")
    value = _as_number(temperature_c, "temperature")
    if value < lower:
        excess = lower - value
    elif value > upper:
        excess = value - upper
    else:
        return 1.0
    return max(0.0, 1.0 - excess / TEMPERATURE_ALLOWANCE_C)


def humidity_score(humidity_percent, limit_percent):
    """Return the environmental score the store humidity earns, 0 to 1."""
    limit = _as_number(limit_percent, "humidity limit")
    if not 0.0 < limit < 100.0:
        raise ValueError("humidity limit must sit strictly inside 0 to 100")
    value = _as_number(humidity_percent, "humidity")
    if value < 0.0 or value > 100.0:
        raise ValueError("humidity must sit between 0 and 100")
    if value <= limit:
        return 1.0
    return max(0.0, 1.0 - (value - limit) / (100.0 - limit))


def barrier_scores(arrangement):
    """Return the score each protective barrier earns, keyed by barrier name."""
    _require_arrangement(arrangement)
    carrier = carrier_profile(arrangement["carrier"])
    seal = seal_profile(arrangement["seal"])
    moisture = seal["moisture"]
    if seal["desiccant_expected"] and not arrangement["desiccant_present"]:
        moisture = moisture / 2.0
    if seal["indicator_expected"] and not arrangement["humidity_indicator_present"]:
        moisture = moisture * 0.8
    if not arrangement["moisture_sensitive"]:
        moisture = max(moisture, ADEQUATE_INDEX)
    environmental = min(
        temperature_score(
            arrangement["storage_temperature_c"], arrangement["temperature_limits_c"]
        ),
        humidity_score(
            arrangement["storage_humidity_percent"],
            arrangement["humidity_limit_percent"],
        ),
    )
    return {
        "mechanical": carrier["mechanical"],
        "moisture": moisture,
        "electrostatic": 1.0 if carrier["dissipative"] else 0.0,
        "environmental": environmental,
    }


def protection_index(arrangement):
    """Return the weakest barrier's score: the protection actually provided."""
    scores = barrier_scores(arrangement)
    return min(scores[name] for name in BARRIERS)


def governing_barrier(arrangement):
    """Return the name of the weakest barrier, ties broken on declared order."""
    scores = barrier_scores(arrangement)
    weakest = min(scores[name] for name in BARRIERS)
    for name in BARRIERS:
        if abs(scores[name] - weakest) <= _SCORE_TOLERANCE:
            return name
    return BARRIERS[0]


def remaining_floor_life(arrangement):
    """Return the whole days of out-of-seal floor life still unspent.

    Negative when the batch has been out of its seal longer than the floor
    life allows.
    """
    _require_arrangement(arrangement)
    return arrangement["floor_life_days"] - arrangement["days_since_seal_opened"]


def bake_required(arrangement):
    """Return True when the floor life is spent or overspent."""
    return remaining_floor_life(arrangement) <= 0


def storage_findings(arrangement):
    """Return every finding the storage arrangement raises."""
    _require_arrangement(arrangement)
    carrier = carrier_profile(arrangement["carrier"])
    seal = seal_profile(arrangement["seal"])
    findings = []
    if not carrier["dissipative"]:
        findings.append(
            "carrier '%s' is not electrostatic dissipative; bare die is handled "
            "without its package to protect it" % arrangement["carrier"]
        )
    if arrangement["moisture_sensitive"] and arrangement["seal"] == "unsealed":
        findings.append(
            "moisture sensitive dies are stored unsealed; the carrier gives no "
            "moisture barrier at all"
        )
    if seal["desiccant_expected"] and not arrangement["desiccant_present"]:
        findings.append(
            "seal '%s' is expected to hold desiccant and none is recorded"
            % arrangement["seal"]
        )
    if seal["indicator_expected"] and not arrangement["humidity_indicator_present"]:
        findings.append(
            "seal '%s' carries no humidity indicator, so a breached bag cannot be "
            "told from an intact one" % arrangement["seal"]
        )
    lower, upper = arrangement["temperature_limits_c"]
    if (
        arrangement["storage_temperature_c"] < lower
        or arrangement["storage_temperature_c"] > upper
    ):
        findings.append(
            "store temperature %.1f C sits outside the %.1f to %.1f C band"
            % (arrangement["storage_temperature_c"], lower, upper)
        )
    if arrangement["storage_humidity_percent"] > arrangement["humidity_limit_percent"]:
        findings.append(
            "store humidity %.1f%% exceeds the %.1f%% ceiling"
            % (
                arrangement["storage_humidity_percent"],
                arrangement["humidity_limit_percent"],
            )
        )
    if bake_required(arrangement):
        findings.append(
            "out-of-seal floor life is spent: %d of %d days used"
            % (
                arrangement["days_since_seal_opened"],
                arrangement["floor_life_days"],
            )
        )
    return findings


def required_actions(arrangement):
    """Return the actions that restore the arrangement, in the order to do them."""
    _require_arrangement(arrangement)
    carrier = carrier_profile(arrangement["carrier"])
    seal = seal_profile(arrangement["seal"])
    actions = []
    if not carrier["dissipative"]:
        actions.append("transfer the dies into an electrostatic dissipative carrier")
    if arrangement["moisture_sensitive"] and arrangement["seal"] == "unsealed":
        actions.append("seal the carrier into a moisture barrier bag")
    if seal["desiccant_expected"] and not arrangement["desiccant_present"]:
        actions.append("re-seal the bag with fresh desiccant")
    if seal["indicator_expected"] and not arrangement["humidity_indicator_present"]:
        actions.append("add a humidity indicator card inside the bag")
    lower, upper = arrangement["temperature_limits_c"]
    out_of_band = (
        arrangement["storage_temperature_c"] < lower
        or arrangement["storage_temperature_c"] > upper
        or arrangement["storage_humidity_percent"]
        > arrangement["humidity_limit_percent"]
    )
    if out_of_band:
        actions.append("return the batch to a store inside the declared conditions")
    if bake_required(arrangement):
        actions.append("bake the dies before they are released to assembly")
    return actions


def assess_die_storage(spec):
    """Run the full clause 10.2.5 die packaging and storage assessment."""
    arrangement = validate_arrangement(spec)
    scores = barrier_scores(arrangement)
    index = min(scores[name] for name in BARRIERS)
    findings = storage_findings(arrangement)
    actions = required_actions(arrangement)
    if index < CONDITIONAL_INDEX - _SCORE_TOLERANCE:
        verdict = "inadequate"
    elif findings:
        verdict = "conditionally-adequate"
    else:
        verdict = "adequate"
    return {
        "arrangement": arrangement,
        "barrier_scores": scores,
        "protection_index": index,
        "governing_barrier": governing_barrier(arrangement),
        "remaining_floor_life_days": remaining_floor_life(arrangement),
        "bake_required": bake_required(arrangement),
        "findings": findings,
        "required_actions": actions,
        "verdict": verdict,
        "release_to_assembly": verdict == "adequate" and not actions,
    }
