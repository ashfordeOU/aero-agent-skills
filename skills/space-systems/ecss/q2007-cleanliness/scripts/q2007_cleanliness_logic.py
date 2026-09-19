"""Cleanliness and contamination control in a space test centre.

Anchor: ECSS-Q-ST-20-07C clause 5.5.3 (paraphrased into an implementable
procedure; no standard text is reproduced).

Procedure implemented here:

1. Every activity in the test centre declares the airborne cleanliness
   class it has to be performed in and, where the hardware is exposed, the
   surface cleanliness level its surfaces have to be kept to. An activity
   that declares neither is a finding on its own: "clean enough" is not a
   level and cannot be monitored.
2. The airborne limit is computed, not looked up in prose. For an ISO
   airborne particulate class N and a particle size D in micrometres the
   admissible concentration is

       C = 10**N * (0.1 / D) ** 2.08   particles per cubic metre

   which reproduces the published table -- class 5 at 0.5 um lands on
   about 3.5e3 particles per cubic metre, class 8 at 5.0 um on about
   2.9e4 -- to the three significant figures the table itself carries.
3. Surface cleanliness is a level number with an obscuration limit
   expressed as percentage area coverage. The levels are ordered: a lower
   level number is a cleaner surface, so an activity asking for level 300
   is not satisfied by a surface certified to level 500.
4. Monitoring is graded separately from conformance. An activity whose
   counts are all inside the limit but which is sampled less often than
   its own requirement has not demonstrated control; the clean record is
   evidence about the sampling interval, not about the air.
5. Each activity reports its margin ratio -- the limit divided by the
   worst count seen -- so a cell that is conforming at 98 percent of its
   limit is visibly different from one at 10 percent.
6. The centre rolls up to the tightest class in use, the non-conforming
   activities and the monitoring gaps.

Float care: the airborne limit is a power expression and is not exactly
representable, so a count is compared against it with a relative slack. A
count landing exactly on the limit therefore conforms on every platform.
The slack is far below any counter's resolution and does not relax the
class.

Stdlib only, offline, deterministic.
"""

MIN_ISO_CLASS = 1
MAX_ISO_CLASS = 9
MIN_PARTICLE_SIZE_UM = 0.1
MAX_PARTICLE_SIZE_UM = 5.0

# Exponent of the published airborne particulate class formula.
PARTICLE_SIZE_EXPONENT = 2.08
REFERENCE_PARTICLE_SIZE_UM = 0.1

# Surface cleanliness level -> obscuration limit, percentage area coverage.
# A lower level number is a cleaner surface.
SURFACE_LEVEL_OBSCURATION_PCT = {
    100: 0.0186,
    200: 0.0577,
    300: 0.162,
    400: 0.281,
    500: 0.454,
    750: 1.105,
    1000: 2.164,
}
VALID_SURFACE_LEVELS = tuple(sorted(SURFACE_LEVEL_OBSCURATION_PCT))

# A count is compared against a power-derived limit with this relative
# slack, so a count exactly on the limit conforms on every platform.
COUNT_RELATIVE_TOLERANCE = 1.0e-9

FINDING_NO_LEVEL = "activity-declares-no-cleanliness-level"
FINDING_COUNT_ABOVE_LIMIT = "particle-count-above-the-class-limit"
FINDING_NO_MONITORING = "no-cleanliness-monitoring-record"
FINDING_INTERVAL_TOO_LONG = "monitoring-interval-longer-than-required"
FINDING_SURFACE_ABOVE_LIMIT = "surface-obscuration-above-the-level-limit"
FINDING_SURFACE_LEVEL_TOO_COARSE = "certified-surface-level-coarser-than-required"


def _numeric(label, value, minimum=None):
    if not isinstance(value, (int, float)) or isinstance(value, bool):
        raise ValueError("%s must be numeric, got %r" % (label, value))
    if minimum is not None and value < minimum:
        raise ValueError("%s must be >= %r, got %r" % (label, minimum, value))
    return float(value)


def _text(label, value):
    if not isinstance(value, str) or not value.strip():
        raise ValueError("%s must be a non-empty string, got %r" % (label, value))
    return value.strip()


def iso_class_limit(iso_class, particle_size_um):
    """Admissible airborne particle concentration, particles per cubic metre."""
    if not isinstance(iso_class, int) or isinstance(iso_class, bool):
        raise ValueError("iso_class must be an integer, got %r" % (iso_class,))
    if not MIN_ISO_CLASS <= iso_class <= MAX_ISO_CLASS:
        raise ValueError(
            "iso_class %d is outside the %d-%d range"
            % (iso_class, MIN_ISO_CLASS, MAX_ISO_CLASS)
        )
    size = _numeric("particle_size_um", particle_size_um)
    if not MIN_PARTICLE_SIZE_UM <= size <= MAX_PARTICLE_SIZE_UM:
        raise ValueError(
            "particle_size_um %r is outside the %r-%r range this formula covers"
            % (size, MIN_PARTICLE_SIZE_UM, MAX_PARTICLE_SIZE_UM)
        )
    return (10.0 ** iso_class) * (
        (REFERENCE_PARTICLE_SIZE_UM / size) ** PARTICLE_SIZE_EXPONENT
    )


def count_conforms(count_per_m3, limit_per_m3):
    """True when a count sits at or below the limit, slack included."""
    count = _numeric("count_per_m3", count_per_m3, 0.0)
    limit = _numeric("limit_per_m3", limit_per_m3, 0.0)
    return count <= limit * (1.0 + COUNT_RELATIVE_TOLERANCE)


def margin_ratio(count_per_m3, limit_per_m3):
    """Limit divided by the count: above 1 is room, below 1 is an exceedance."""
    count = _numeric("count_per_m3", count_per_m3, 0.0)
    limit = _numeric("limit_per_m3", limit_per_m3, 0.0)
    if count <= 0.0:
        raise ValueError("a zero count has no margin ratio")
    return limit / count


def surface_obscuration_limit_pct(level):
    """Obscuration limit for a surface cleanliness level, percentage area."""
    if not isinstance(level, int) or isinstance(level, bool):
        raise ValueError("level must be an integer, got %r" % (level,))
    if level not in SURFACE_LEVEL_OBSCURATION_PCT:
        raise ValueError(
            "unknown surface level %d (expected one of %s)"
            % (level, ", ".join(str(v) for v in VALID_SURFACE_LEVELS))
        )
    return SURFACE_LEVEL_OBSCURATION_PCT[level]


def surface_level_meets(required_level, certified_level):
    """True when the certified level is at least as clean as the required one."""
    surface_obscuration_limit_pct(required_level)
    surface_obscuration_limit_pct(certified_level)
    return certified_level <= required_level


def tightest_class(activities):
    """Lowest airborne class number declared across a set of activities."""
    declared = []
    for activity in activities:
        norm = validate_activity(activity)
        if norm["required_iso_class"] is not None:
            declared.append(norm["required_iso_class"])
    if not declared:
        raise ValueError("no activity declares an airborne cleanliness class")
    return min(declared)


def validate_activity(record):
    """Validate one test-centre activity record and return a normalized copy."""
    if not isinstance(record, dict):
        raise ValueError("activity record must be a mapping")
    activity_id = _text("activity id", record.get("id"))
    iso_class = record.get("required_iso_class")
    size = record.get("particle_size_um", 0.5)
    if iso_class is not None:
        size = _numeric("activity %s particle_size_um" % activity_id, size)
        iso_class_limit(iso_class, size)
    counts = record.get("counts_per_m3", [])
    if isinstance(counts, (str, bytes)) or not isinstance(counts, (list, tuple)):
        raise ValueError("activity %s counts_per_m3 must be a sequence" % activity_id)
    normalized_counts = [
        _numeric("activity %s count" % activity_id, c, 0.0) for c in counts
    ]
    interval = record.get("monitoring_interval_h")
    if interval is not None:
        interval = _numeric("activity %s monitoring_interval_h" % activity_id,
                            interval, 0.0)
        if interval <= 0:
            raise ValueError(
                "activity %s monitoring_interval_h must be positive" % activity_id
            )
    required_interval = record.get("required_interval_h")
    if required_interval is not None:
        required_interval = _numeric(
            "activity %s required_interval_h" % activity_id, required_interval, 0.0
        )
    required_surface = record.get("required_surface_level")
    if required_surface is not None:
        surface_obscuration_limit_pct(required_surface)
    certified_surface = record.get("certified_surface_level")
    if certified_surface is not None:
        surface_obscuration_limit_pct(certified_surface)
    obscuration = record.get("measured_obscuration_pct")
    if obscuration is not None:
        obscuration = _numeric(
            "activity %s measured_obscuration_pct" % activity_id, obscuration, 0.0
        )
    return {
        "id": activity_id,
        "required_iso_class": iso_class,
        "particle_size_um": size if iso_class is not None else None,
        "counts_per_m3": normalized_counts,
        "monitoring_interval_h": interval,
        "required_interval_h": required_interval,
        "required_surface_level": required_surface,
        "certified_surface_level": certified_surface,
        "measured_obscuration_pct": obscuration,
    }


def assess_activity(record):
    """Assess one activity against clause 5.5.3."""
    norm = validate_activity(record)
    findings = []
    limit = None
    worst = None
    ratio = None
    if norm["required_iso_class"] is None and norm["required_surface_level"] is None:
        findings.append(FINDING_NO_LEVEL)
    if norm["required_iso_class"] is not None:
        limit = iso_class_limit(norm["required_iso_class"], norm["particle_size_um"])
        if not norm["counts_per_m3"]:
            findings.append(FINDING_NO_MONITORING)
        else:
            worst = max(norm["counts_per_m3"])
            if not count_conforms(worst, limit):
                findings.append(FINDING_COUNT_ABOVE_LIMIT)
            if worst > 0.0:
                ratio = margin_ratio(worst, limit)
    if (
        norm["monitoring_interval_h"] is not None
        and norm["required_interval_h"] is not None
        and norm["monitoring_interval_h"]
        > norm["required_interval_h"] * (1.0 + COUNT_RELATIVE_TOLERANCE)
    ):
        findings.append(FINDING_INTERVAL_TOO_LONG)
    surface_limit = None
    if norm["required_surface_level"] is not None:
        surface_limit = surface_obscuration_limit_pct(norm["required_surface_level"])
        if norm["certified_surface_level"] is not None and not surface_level_meets(
            norm["required_surface_level"], norm["certified_surface_level"]
        ):
            findings.append(FINDING_SURFACE_LEVEL_TOO_COARSE)
        if norm["measured_obscuration_pct"] is not None and norm[
            "measured_obscuration_pct"
        ] > surface_limit * (1.0 + COUNT_RELATIVE_TOLERANCE):
            findings.append(FINDING_SURFACE_ABOVE_LIMIT)
    return {
        "id": norm["id"],
        "required_iso_class": norm["required_iso_class"],
        "particle_size_um": norm["particle_size_um"],
        "airborne_limit_per_m3": limit,
        "worst_count_per_m3": worst,
        "margin_ratio": ratio,
        "surface_obscuration_limit_pct": surface_limit,
        "findings": findings,
        "conforming": not findings,
    }


def assess_test_centre_cleanliness(activities):
    """Run the full clause 5.5.3 assessment over a test centre."""
    if not isinstance(activities, list) or not activities:
        raise ValueError("activities must be a non-empty list")
    results = []
    seen = set()
    for activity in activities:
        result = assess_activity(activity)
        if result["id"] in seen:
            raise ValueError("duplicate activity id %r" % (result["id"],))
        seen.add(result["id"])
        results.append(result)
    non_conforming = [r["id"] for r in results if not r["conforming"]]
    classed = [r["required_iso_class"] for r in results
               if r["required_iso_class"] is not None]
    return {
        "activities": results,
        "non_conforming_ids": non_conforming,
        "monitoring_gap_ids": [
            r["id"]
            for r in results
            if FINDING_NO_MONITORING in r["findings"]
            or FINDING_INTERVAL_TOO_LONG in r["findings"]
        ],
        "tightest_iso_class": min(classed) if classed else None,
        "conforming": not non_conforming,
    }
