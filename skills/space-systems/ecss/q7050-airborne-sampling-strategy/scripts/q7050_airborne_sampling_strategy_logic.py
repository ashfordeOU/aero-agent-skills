"""Airborne sampling strategy for cleanroom particle monitoring.

Anchor: ECSS-Q-ST-70-50C airborne clause -- deciding how many sampling
locations a zone carries, how much air each one has to draw, at what flow
rate and therefore for how long. Paraphrased into an implementable procedure;
no standard text is reproduced.

Procedure implemented here
--------------------------
1. Size the sampling locations from the zone floor area, either by the
   square-root rule or from a caller-supplied area-to-location table, never
   below a stated minimum and never below what the operator asked for.
2. Derive the minimum single-sample volume from the class limit at the
   considered size, so that a compliant zone still yields enough counted
   particles for the reading to mean something, subject to a floor volume.
3. Turn that volume into a sampling duration at the counter's flow rate, with
   a minimum duration so a high-flow counter cannot reduce a sample to a
   few seconds.
4. Total the campaign: air drawn per location, air drawn for the zone, and
   the occupancy time the run costs the facility.
5. Report the findings the strategy raises: a flow rate outside the counter's
   calibrated band, a duration driven to its floor, and a location count the
   operator cut below the derived value.
"""

import math

__all__ = [
    "MIN_LOCATIONS",
    "FLOOR_SAMPLE_VOLUME_L",
    "MIN_SAMPLE_DURATION_MIN",
    "TARGET_PARTICLE_COUNT",
    "DURATION_TOLERANCE_MIN",
    "validate_area_m2",
    "validate_limit_per_m3",
    "validate_flow_rate_lpm",
    "location_count_from_area",
    "location_count_from_table",
    "minimum_sample_volume_l",
    "sampling_duration_min",
    "plan_location_sampling",
    "assess_sampling_strategy",
]

# A zone is never sampled at a single point.
MIN_LOCATIONS = 2

# No sample is smaller than this, whatever the class limit allows.
FLOOR_SAMPLE_VOLUME_L = 2.0

# No sample is shorter than this, whatever the flow rate allows.
MIN_SAMPLE_DURATION_MIN = 1.0

# Particles a single sample should be able to collect at the class limit for
# the reading to carry statistical weight.
TARGET_PARTICLE_COUNT = 20.0

# Durations are a ratio: an exact equality can land a few ULPs off.
DURATION_TOLERANCE_MIN = 1e-9


def validate_area_m2(area_m2):
    """Return the validated zone floor area in square metres."""
    if not isinstance(area_m2, (int, float)) or isinstance(area_m2, bool):
        raise ValueError("area_m2 must be a real number, got %r" % (area_m2,))
    value = float(area_m2)
    if not math.isfinite(value):
        raise ValueError("area_m2 must be finite")
    if value <= 0.0:
        raise ValueError("area_m2 must be positive, got %g" % value)
    return value


def validate_limit_per_m3(limit_per_m3):
    """Return the validated class concentration limit in particles per cubic metre."""
    if not isinstance(limit_per_m3, (int, float)) or isinstance(limit_per_m3, bool):
        raise ValueError("limit_per_m3 must be a real number, got %r" % (limit_per_m3,))
    value = float(limit_per_m3)
    if not math.isfinite(value):
        raise ValueError("limit_per_m3 must be finite")
    if value <= 0.0:
        raise ValueError("limit_per_m3 must be positive, got %g" % value)
    return value


def validate_flow_rate_lpm(flow_rate_lpm):
    """Return the validated counter flow rate in litres per minute."""
    if not isinstance(flow_rate_lpm, (int, float)) or isinstance(flow_rate_lpm, bool):
        raise ValueError("flow_rate_lpm must be a real number, got %r" % (flow_rate_lpm,))
    value = float(flow_rate_lpm)
    if not math.isfinite(value):
        raise ValueError("flow_rate_lpm must be finite")
    if value <= 0.0:
        raise ValueError("flow_rate_lpm must be positive, got %g" % value)
    return value


def location_count_from_area(area_m2, requested=None):
    """Return the sampling location count derived from the zone floor area."""
    area = validate_area_m2(area_m2)
    derived = int(math.ceil(math.sqrt(area) - 1e-12))
    count = max(derived, MIN_LOCATIONS)
    if requested is None:
        return count
    if not isinstance(requested, int) or isinstance(requested, bool):
        raise ValueError("requested must be an integer, got %r" % (requested,))
    if requested < 1:
        raise ValueError("requested must be at least 1, got %d" % requested)
    return max(count, requested)


def location_count_from_table(area_m2, table):
    """Return the location count from a caller-supplied (max_area, count) table."""
    area = validate_area_m2(area_m2)
    if not isinstance(table, (list, tuple)) or not table:
        raise ValueError("table must be a non-empty sequence of (max_area_m2, count) pairs")
    rows = []
    for i, item in enumerate(table):
        if not isinstance(item, (list, tuple)) or len(item) != 2:
            raise ValueError("table[%d] must be a (max_area_m2, count) pair" % i)
        bound, count = item
        bound = validate_area_m2(bound)
        if not isinstance(count, int) or isinstance(count, bool) or count < 1:
            raise ValueError("table[%d] count must be an integer of at least 1" % i)
        rows.append((bound, count))
    for i in range(1, len(rows)):
        if rows[i][0] <= rows[i - 1][0]:
            raise ValueError("table area bounds must strictly increase (row %d)" % i)
        if rows[i][1] < rows[i - 1][1]:
            raise ValueError("table counts must not decrease with area (row %d)" % i)
    for bound, count in rows:
        if area <= bound or math.isclose(area, bound, rel_tol=1e-12, abs_tol=0.0):
            return max(count, MIN_LOCATIONS)
    raise ValueError(
        "area %g m2 is above the largest tabulated bound %g m2; extend the table"
        % (area, rows[-1][0])
    )


def minimum_sample_volume_l(limit_per_m3, target_count=TARGET_PARTICLE_COUNT):
    """Return the smallest single-sample volume in litres worth drawing."""
    limit = validate_limit_per_m3(limit_per_m3)
    if not isinstance(target_count, (int, float)) or isinstance(target_count, bool):
        raise ValueError("target_count must be a real number, got %r" % (target_count,))
    target = float(target_count)
    if not math.isfinite(target) or target <= 0.0:
        raise ValueError("target_count must be positive and finite, got %r" % (target_count,))
    volume = target / limit * 1000.0
    if volume < FLOOR_SAMPLE_VOLUME_L:
        return FLOOR_SAMPLE_VOLUME_L
    return volume


def sampling_duration_min(volume_l, flow_rate_lpm):
    """Return the sampling duration in minutes for a volume at a flow rate."""
    if not isinstance(volume_l, (int, float)) or isinstance(volume_l, bool):
        raise ValueError("volume_l must be a real number, got %r" % (volume_l,))
    volume = float(volume_l)
    if not math.isfinite(volume) or volume <= 0.0:
        raise ValueError("volume_l must be positive and finite, got %r" % (volume_l,))
    flow = validate_flow_rate_lpm(flow_rate_lpm)
    duration = volume / flow
    if duration < MIN_SAMPLE_DURATION_MIN and not math.isclose(
        duration, MIN_SAMPLE_DURATION_MIN, rel_tol=0.0, abs_tol=DURATION_TOLERANCE_MIN
    ):
        return MIN_SAMPLE_DURATION_MIN
    return duration


def plan_location_sampling(limit_per_m3, flow_rate_lpm, target_count=TARGET_PARTICLE_COUNT):
    """Return the per-location sampling record: volume, duration, air drawn."""
    volume = minimum_sample_volume_l(limit_per_m3, target_count)
    duration = sampling_duration_min(volume, flow_rate_lpm)
    flow = validate_flow_rate_lpm(flow_rate_lpm)
    drawn = duration * flow
    return {
        "minimum_volume_l": volume,
        "duration_min": duration,
        "air_drawn_l": drawn,
        "flow_rate_lpm": flow,
        "volume_floor_applied": math.isclose(
            volume, FLOOR_SAMPLE_VOLUME_L, rel_tol=1e-12, abs_tol=0.0
        ),
        "duration_floor_applied": math.isclose(
            duration, MIN_SAMPLE_DURATION_MIN, rel_tol=0.0, abs_tol=DURATION_TOLERANCE_MIN
        ),
    }


def assess_sampling_strategy(spec):
    """Build and grade the airborne sampling strategy for one zone.

    spec keys: area_m2, limit_per_m3, flow_rate_lpm; optional
    requested_locations, location_table, target_count,
    flow_rate_band (min, max).
    """
    if not isinstance(spec, dict):
        raise ValueError("spec must be a mapping")
    for key in ("area_m2", "limit_per_m3", "flow_rate_lpm"):
        if key not in spec:
            raise ValueError("spec missing required key '%s'" % key)
    area = validate_area_m2(spec["area_m2"])
    flow = validate_flow_rate_lpm(spec["flow_rate_lpm"])
    requested = spec.get("requested_locations")

    table = spec.get("location_table")
    if table is None:
        locations = location_count_from_area(area, requested)
        derived = location_count_from_area(area)
    else:
        derived = location_count_from_table(area, table)
        locations = derived
        if requested is not None:
            if not isinstance(requested, int) or isinstance(requested, bool):
                raise ValueError("requested_locations must be an integer")
            locations = max(derived, requested)

    record = plan_location_sampling(
        spec["limit_per_m3"], flow, spec.get("target_count", TARGET_PARTICLE_COUNT)
    )

    findings = []
    band = spec.get("flow_rate_band")
    if band is not None:
        if not isinstance(band, (list, tuple)) or len(band) != 2:
            raise ValueError("flow_rate_band must be a (min, max) pair")
        low = validate_flow_rate_lpm(band[0])
        high = validate_flow_rate_lpm(band[1])
        if low > high:
            raise ValueError("flow_rate_band lower bound %g exceeds upper bound %g" % (low, high))
        if flow < low or flow > high:
            findings.append(
                "flow rate %g L/min is outside the calibrated band [%g, %g] L/min"
                % (flow, low, high)
            )
    if record["duration_floor_applied"]:
        findings.append(
            "sample duration is held at the %g min floor; the flow rate reaches the "
            "volume sooner than a representative sample allows"
            % MIN_SAMPLE_DURATION_MIN
        )
    if record["volume_floor_applied"]:
        findings.append(
            "sample volume is held at the %g L floor; the class limit is loose enough "
            "that the statistical target is met almost immediately"
            % FLOOR_SAMPLE_VOLUME_L
        )
    if requested is not None and isinstance(requested, int) and requested < derived:
        findings.append(
            "operator asked for %d locations; the floor area derives %d, so the "
            "derived count stands" % (requested, derived)
        )

    return {
        "area_m2": area,
        "locations": locations,
        "derived_locations": derived,
        "minimum_volume_l": record["minimum_volume_l"],
        "duration_min": record["duration_min"],
        "air_per_location_l": record["air_drawn_l"],
        "zone_air_l": record["air_drawn_l"] * locations,
        "zone_duration_min": record["duration_min"] * locations,
        "findings": findings,
        "acceptable": not findings,
    }
