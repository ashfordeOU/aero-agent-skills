"""Handling, packaging and storage of Class 2 EEE parts.

Anchor: ECSS-Q-ST-60C clause 5.4 (procedures for handling, packaging and
storing Class 2 parts so they are not damaged or degraded). Paraphrased into
an implementable procedure; no standard text is reproduced.

Procedure implemented here
--------------------------
1. Band the part by the electrostatic discharge voltage it withstands and read
   the protection level and the measures that band owes.
2. Walk the custody chain leg by leg -- receipt, bonded store, kitting, line
   issue, return to store -- and grade every leg against the protection the
   location it passed through actually held. The chain is only as good as its
   weakest leg, and one open bench undoes every protected one.
3. Accumulate the minutes a moisture-sensitive part spent outside dry storage
   across the whole chain and test them against its open-air budget. Time in a
   dry cabinet does not count against the budget.
4. Return the store temperature and humidity as margins to their nearest
   limits rather than as a pass or a fail, so a lot sitting just inside its
   limits is visibly different from one in the middle of them.
5. Read the re-inspection clock, then rank every finding into one disposition:
   fit-for-issue, issue-with-actions, or quarantine-for-reconditioning.
"""

import math

__all__ = [
    "BOUND_TOLERANCE",
    "ESD_BANDS",
    "PROTECTION_MEASURES",
    "LOCATION_PROTECTION_LEVEL",
    "DEFAULT_OPEN_AIR_BUDGET_MINUTES",
    "OPEN_AIR_WARNING_FRACTION",
    "DEFAULT_STORE_LIMITS",
    "REINSPECTION_INTERVAL_MONTHS",
    "esd_band",
    "required_protection_measures",
    "location_protection_level",
    "grade_leg",
    "grade_custody_chain",
    "open_air_budget_state",
    "environment_margins",
    "reinspection_due",
    "assess_handling_chain",
]

# Margins, consumed fractions and accumulated minutes are quotients and sums of
# measured values; a case meant to land exactly on a limit can sit a few ULP
# either side of it. Absorb the representation error here, never by moving the
# limit itself.
BOUND_TOLERANCE = 1e-9

# Bands by the electrostatic discharge voltage the part withstands, ordered
# from the most sensitive upwards. The upper bound is inclusive; the last band
# carries no upper bound.
ESD_BANDS = (
    (250.0, "esd-very-sensitive", 3),
    (1000.0, "esd-sensitive", 2),
    (None, "esd-standard", 1),
)

# What each protection level owes. Levels are cumulative: level 3 carries
# everything level 2 carries, and level 2 everything level 1 carries.
PROTECTION_MEASURES = {
    1: ("static-shielding-bag",),
    2: ("static-shielding-bag", "grounded-wrist-strap", "dissipative-worksurface"),
    3: (
        "static-shielding-bag",
        "grounded-wrist-strap",
        "dissipative-worksurface",
        "air-ionizer",
        "continuous-ground-monitoring",
    ),
}

# The protection level each kind of location actually holds. A location the
# register does not carry is refused: an ungraded location cannot be compared
# with the level the part owes.
LOCATION_PROTECTION_LEVEL = {
    "open-bench": 0,
    "goods-inwards-counter": 1,
    "sealed-transport-container": 2,
    "esd-protected-bench": 2,
    "kitting-cell": 2,
    "bonded-store": 3,
    "protected-assembly-area": 3,
}

DEFAULT_OPEN_AIR_BUDGET_MINUTES = 480.0
OPEN_AIR_WARNING_FRACTION = 0.8

DEFAULT_STORE_LIMITS = {
    "temperature_min_c": 10.0,
    "temperature_max_c": 30.0,
    "humidity_max_pct": 60.0,
}

REINSPECTION_INTERVAL_MONTHS = 24.0


def _positive_int(value, label):
    """Return value as a positive integer, refusing anything else."""
    if isinstance(value, bool) or not isinstance(value, int):
        raise ValueError("%s must be an integer, got %r" % (label, value))
    if value <= 0:
        raise ValueError("%s must be positive, got %d" % (label, value))
    return value


def _positive_real(value, label):
    """Return value as a finite positive float, refusing anything else."""
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise ValueError("%s must be a real number, got %r" % (label, value))
    value = float(value)
    if not math.isfinite(value):
        raise ValueError("%s must be finite, got %r" % (label, value))
    if value <= 0.0:
        raise ValueError("%s must be positive, got %r" % (label, value))
    return value


def _non_negative_real(value, label):
    """Return value as a finite non-negative float, refusing anything else."""
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise ValueError("%s must be a real number, got %r" % (label, value))
    value = float(value)
    if not math.isfinite(value):
        raise ValueError("%s must be finite, got %r" % (label, value))
    if value < 0.0:
        raise ValueError("%s must not be negative, got %r" % (label, value))
    return value


def _real(value, label):
    """Return value as a finite float, refusing anything else."""
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise ValueError("%s must be a real number, got %r" % (label, value))
    value = float(value)
    if not math.isfinite(value):
        raise ValueError("%s must be finite, got %r" % (label, value))
    return value


def _clean_token(value, label):
    """Return a stripped lower-cased non-empty token, refusing anything else."""
    if not isinstance(value, str) or not value.strip():
        raise ValueError("%s must be a non-empty string" % label)
    return value.strip().lower()


def _at_most(value, bound):
    """Return True when value sits at or under bound, tolerant of float noise."""
    return value < bound or math.isclose(
        value, bound, rel_tol=BOUND_TOLERANCE, abs_tol=BOUND_TOLERANCE
    )


def _at_least(value, bound):
    """Return True when value sits at or above bound, tolerant of float noise."""
    return value > bound or math.isclose(
        value, bound, rel_tol=BOUND_TOLERANCE, abs_tol=BOUND_TOLERANCE
    )


def esd_band(withstand_volts):
    """Return the band and protection level a withstand voltage earns.

    A part that survives less is owed more, so the bands run from the most
    sensitive upwards and the first band whose upper bound the part does not
    exceed is the one it sits in.
    """
    volts = _positive_real(withstand_volts, "withstand_volts")
    for upper, name, level in ESD_BANDS:
        if upper is None or _at_most(volts, upper):
            return {
                "withstand_volts": volts,
                "band": name,
                "required_level": level,
            }
    raise ValueError("no band covers a withstand of %r V" % (volts,))


def required_protection_measures(level):
    """Return the measures a protection level owes."""
    level = _positive_int(level, "level")
    if level not in PROTECTION_MEASURES:
        raise ValueError(
            "protection level %d is not in the measure register" % level
        )
    return PROTECTION_MEASURES[level]


def location_protection_level(location, register=None):
    """Return the protection level a kind of location actually holds."""
    if register is None:
        register = LOCATION_PROTECTION_LEVEL
    if not isinstance(register, dict) or not register:
        raise ValueError("register must be a non-empty mapping of location to level")
    name = _clean_token(location, "location")
    if name not in register:
        raise ValueError(
            "location '%s' is not a graded handling location; grade it before a "
            "custody leg through it is credited" % name
        )
    level = register[name]
    if isinstance(level, bool) or not isinstance(level, int) or level < 0:
        raise ValueError("protection level for '%s' must be a non-negative integer" % name)
    return level


def grade_leg(leg, required_level, register=None):
    """Grade one custody leg against the protection the part owes.

    leg keys: location, open_air_minutes, and an optional dry_storage flag.
    Minutes spent in dry storage are still custody but do not spend the
    open-air budget, which is what the budget is about.
    """
    if not isinstance(leg, dict):
        raise ValueError("leg must be a mapping")
    required_level = _positive_int(required_level, "required_level")
    for key in ("location", "open_air_minutes"):
        if key not in leg:
            raise ValueError("custody leg missing key '%s'" % key)
    location = _clean_token(leg["location"], "leg location")
    held = location_protection_level(location, register)
    minutes = _non_negative_real(leg["open_air_minutes"], "open_air_minutes")
    dry = bool(leg.get("dry_storage", False))
    shortfall = max(0, required_level - held)
    return {
        "location": location,
        "level_held": held,
        "level_required": required_level,
        "shortfall": shortfall,
        "open_air_minutes": 0.0 if dry else minutes,
        "dry_storage": dry,
    }


def grade_custody_chain(legs, required_level, register=None):
    """Grade every custody leg and find the weakest one.

    The chain is not an average. One leg across an open bench exposes the part
    exactly as much as if the whole chain had been run that way, so the weakest
    leg is reported rather than a mean protection level.
    """
    if not isinstance(legs, (list, tuple)) or not legs:
        raise ValueError("legs must be a non-empty sequence of custody legs")
    graded = []
    for index, leg in enumerate(legs):
        entry = grade_leg(leg, required_level, register)
        entry["sequence"] = index
        graded.append(entry)
    weakest = max(graded, key=lambda entry: (entry["shortfall"], entry["sequence"]))
    return {
        "legs": graded,
        "weakest_leg": weakest,
        "worst_shortfall": weakest["shortfall"],
        "legs_below_requirement": tuple(
            entry["location"] for entry in graded if entry["shortfall"] > 0
        ),
        "open_air_minutes": sum(entry["open_air_minutes"] for entry in graded),
    }


def open_air_budget_state(
    consumed_minutes,
    budget_minutes=DEFAULT_OPEN_AIR_BUDGET_MINUTES,
    warning_fraction=OPEN_AIR_WARNING_FRACTION,
):
    """Return how much of the open-air budget the chain has spent."""
    consumed = _non_negative_real(consumed_minutes, "consumed_minutes")
    budget = _positive_real(budget_minutes, "budget_minutes")
    warning = _positive_real(warning_fraction, "warning_fraction")
    if warning > 1.0:
        raise ValueError(
            "warning_fraction must sit at or under the budget, got %r" % (warning,)
        )
    fraction = consumed / budget
    return {
        "consumed_minutes": consumed,
        "budget_minutes": budget,
        "remaining_minutes": budget - consumed,
        "fraction_consumed": fraction,
        "exhausted": not _at_most(fraction, 1.0),
        "near_exhaustion": _at_least(fraction, warning) and _at_most(fraction, 1.0),
    }


def environment_margins(temperature_c, humidity_pct, limits=None):
    """Return the store environment as margins to its nearest limits.

    A margin of one means the reading sits in the middle of its allowed band;
    zero means it sits exactly on a limit; a negative margin means it is
    outside. The magnitude is what separates a logged note from reconditioning.
    """
    if limits is None:
        limits = DEFAULT_STORE_LIMITS
    if not isinstance(limits, dict):
        raise ValueError("limits must be a mapping of store limits")
    for key in ("temperature_min_c", "temperature_max_c", "humidity_max_pct"):
        if key not in limits:
            raise ValueError("limits missing key '%s'" % key)
    low = _real(limits["temperature_min_c"], "temperature_min_c")
    high = _real(limits["temperature_max_c"], "temperature_max_c")
    if not high > low:
        raise ValueError(
            "temperature limits must widen upwards, got %r to %r" % (low, high)
        )
    humidity_limit = _positive_real(limits["humidity_max_pct"], "humidity_max_pct")
    temperature = _real(temperature_c, "temperature_c")
    humidity = _non_negative_real(humidity_pct, "humidity_pct")
    half_span = (high - low) / 2.0
    temperature_margin = min(temperature - low, high - temperature) / half_span
    humidity_margin = (humidity_limit - humidity) / humidity_limit
    return {
        "temperature_c": temperature,
        "humidity_pct": humidity,
        "temperature_margin": temperature_margin,
        "humidity_margin": humidity_margin,
        "within_limits": _at_least(temperature_margin, 0.0)
        and _at_least(humidity_margin, 0.0),
    }


def reinspection_due(months_since_inspection, interval=REINSPECTION_INTERVAL_MONTHS):
    """Return True when the stored lot has reached its re-inspection interval."""
    months = _non_negative_real(months_since_inspection, "months_since_inspection")
    interval = _positive_real(interval, "interval")
    return _at_least(months, interval)


def assess_handling_chain(spec):
    """Run the clause 5.4 handling and storage assessment for one Class 2 lot.

    Required spec keys: withstand_volts, custody_legs, store_temperature_c,
    store_humidity_pct, months_since_inspection. Optional:
    open_air_budget_minutes, warning_fraction, store_limits,
    reinspection_interval_months, location_register.
    """
    if not isinstance(spec, dict):
        raise ValueError("spec must be a mapping")
    required = (
        "withstand_volts",
        "custody_legs",
        "store_temperature_c",
        "store_humidity_pct",
        "months_since_inspection",
    )
    for key in required:
        if key not in spec:
            raise ValueError("spec missing required key '%s'" % key)
    band = esd_band(spec["withstand_volts"])
    chain = grade_custody_chain(
        spec["custody_legs"], band["required_level"], spec.get("location_register")
    )
    budget = open_air_budget_state(
        chain["open_air_minutes"],
        spec.get("open_air_budget_minutes", DEFAULT_OPEN_AIR_BUDGET_MINUTES),
        spec.get("warning_fraction", OPEN_AIR_WARNING_FRACTION),
    )
    environment = environment_margins(
        spec["store_temperature_c"],
        spec["store_humidity_pct"],
        spec.get("store_limits"),
    )
    due = reinspection_due(
        spec["months_since_inspection"],
        spec.get("reinspection_interval_months", REINSPECTION_INTERVAL_MONTHS),
    )

    result = {
        "esd_band": band,
        "owed_measures": required_protection_measures(band["required_level"]),
        "custody_chain": chain,
        "open_air_budget": budget,
        "store_environment": environment,
        "reinspection_due": due,
    }

    quarantine = []
    actions = []

    if chain["worst_shortfall"] >= 2:
        quarantine.append(
            "custody leg through '%s' held protection level %d against the %d this "
            "part owes"
            % (
                chain["weakest_leg"]["location"],
                chain["weakest_leg"]["level_held"],
                band["required_level"],
            )
        )
    elif chain["worst_shortfall"] == 1:
        actions.append(
            "custody leg through '%s' was one protection level short"
            % chain["weakest_leg"]["location"]
        )
    if budget["exhausted"]:
        quarantine.append(
            "open-air exposure of %.1f minute(s) is over the %.1f minute budget"
            % (budget["consumed_minutes"], budget["budget_minutes"])
        )
    elif budget["near_exhaustion"]:
        actions.append(
            "open-air exposure has spent %.0f%% of its budget"
            % (100.0 * budget["fraction_consumed"])
        )
    if not environment["within_limits"]:
        quarantine.append(
            "store environment is outside its limits at %.1f C and %.1f %% relative "
            "humidity" % (environment["temperature_c"], environment["humidity_pct"])
        )
    if due:
        actions.append("the stored lot has reached its re-inspection interval")

    if quarantine:
        result["disposition"] = "quarantine-for-reconditioning"
        result["reasons"] = quarantine + actions
        return result
    if actions:
        result["disposition"] = "issue-with-actions"
        result["reasons"] = actions
        return result
    result["disposition"] = "fit-for-issue"
    result["reasons"] = [
        "every custody leg held at least protection level %d and the open-air "
        "budget is %.0f%% spent"
        % (band["required_level"], 100.0 * budget["fraction_consumed"])
    ]
    return result
