"""Airborne particle qualification planning and grading for a cleanroom.

Anchor: the facility interface of particle contamination monitoring, where a
programme coordinates the airborne particle qualification of the room
(ISO 14644-1 sample plan) and its re-qualification cadence (ISO 14644-2).
Paraphrased into an implementable procedure; no standard text is reproduced.

Procedure implemented here
--------------------------
1. Validate the room, the target class, the reference particle sizes and the
   counter flow rate.
2. Derive the limit concentration at each reference size from the target
   class and the programme size exponent.
3. Determine the minimum sample location count from the floor area, using the
   programme location table when supplied and the area square-root rule
   otherwise.
4. Size the single sample: the volume that collects the required particle
   count at the tightest limit, raised to the volume floor, and the sampling
   time that volume needs at the counter flow rate.
5. Grade each reported location against the per-size limits.
6. Check location coverage, per-location sampled volume, and the
   re-qualification interval for the target class.
"""

import math

__all__ = [
    "CONCENTRATION_TOLERANCE",
    "DEFAULT_SIZE_EXPONENT",
    "DEFAULT_REFERENCE_SIZE_UM",
    "MIN_PARTICLES_PER_SAMPLE",
    "MIN_SAMPLE_VOLUME_L",
    "MIN_SAMPLE_TIME_S",
    "TIGHT_CLASS_CEILING",
    "TIGHT_CLASS_INTERVAL_DAYS",
    "LOOSE_CLASS_INTERVAL_DAYS",
    "validate_class",
    "validate_size_um",
    "limit_concentration",
    "minimum_sample_locations",
    "single_sample_volume_l",
    "sampling_time_s",
    "location_concentration",
    "grade_location",
    "requalification_interval_days",
    "assess_cleanroom_qualification",
]

# A measured concentration can land a few ULP either side of its limit when the
# limit itself came out of a power. Absorb the representation error here.
CONCENTRATION_TOLERANCE = 1e-9

# The allowed concentration falls with particle size along this exponent.
DEFAULT_SIZE_EXPONENT = 2.08
# The size the class number itself is anchored to, in micrometres.
DEFAULT_REFERENCE_SIZE_UM = 0.1

# A sample is meaningful only when a room at its limit would deliver at least
# this many particles into it.
MIN_PARTICLES_PER_SAMPLE = 20.0
# Floors that apply on top of the derived sample size.
MIN_SAMPLE_VOLUME_L = 2.0
MIN_SAMPLE_TIME_S = 60.0

# Re-qualification cadence: the tighter classes are re-qualified more often.
TIGHT_CLASS_CEILING = 5
TIGHT_CLASS_INTERVAL_DAYS = 183
LOOSE_CLASS_INTERVAL_DAYS = 365

_LITRES_PER_CUBIC_METRE = 1000.0


def validate_class(iso_class):
    """Return the target class as a float, rejecting a negative or absurd one."""
    if not isinstance(iso_class, (int, float)) or isinstance(iso_class, bool):
        raise ValueError("iso_class must be a real number")
    value = float(iso_class)
    if not math.isfinite(value):
        raise ValueError("iso_class must be finite")
    if value < 1.0 or value > 9.0:
        raise ValueError("iso_class must lie between 1 and 9, got %r" % (iso_class,))
    return value


def validate_size_um(diameter_um):
    """Return a positive finite reference particle size in micrometres."""
    if not isinstance(diameter_um, (int, float)) or isinstance(diameter_um, bool):
        raise ValueError("diameter_um must be a real number")
    value = float(diameter_um)
    if not math.isfinite(value) or value <= 0.0:
        raise ValueError("diameter_um must be positive and finite, got %r" % (diameter_um,))
    return value


def limit_concentration(iso_class, diameter_um, exponent=DEFAULT_SIZE_EXPONENT,
                        anchor_um=DEFAULT_REFERENCE_SIZE_UM):
    """Return the allowed concentration in particles per cubic metre."""
    level = validate_class(iso_class)
    size = validate_size_um(diameter_um)
    anchor = validate_size_um(anchor_um)
    if not isinstance(exponent, (int, float)) or isinstance(exponent, bool):
        raise ValueError("exponent must be a real number")
    power = float(exponent)
    if not math.isfinite(power) or power <= 0.0:
        raise ValueError("exponent must be positive and finite")
    return (10.0 ** level) * ((anchor / size) ** power)


def minimum_sample_locations(area_m2, location_table=None):
    """Return the minimum number of sample locations for a floor area.

    location_table, when supplied, is the programme table as a sequence of
    (max_area_m2, locations) pairs; the first entry whose area bound holds the
    room wins. Without a table the area square-root rule is used.
    """
    if not isinstance(area_m2, (int, float)) or isinstance(area_m2, bool):
        raise ValueError("area_m2 must be a real number")
    area = float(area_m2)
    if not math.isfinite(area) or area <= 0.0:
        raise ValueError("area_m2 must be positive and finite, got %r" % (area_m2,))
    if location_table is None:
        return max(1, int(math.ceil(math.sqrt(area))))
    if not isinstance(location_table, (list, tuple)) or not location_table:
        raise ValueError("location_table must be a non-empty sequence of (max_area, n) pairs")
    entries = []
    for index, item in enumerate(location_table):
        if not isinstance(item, (list, tuple)) or len(item) != 2:
            raise ValueError("location_table[%d] must be a (max_area_m2, locations) pair" % index)
        bound, count = item
        if not isinstance(bound, (int, float)) or isinstance(bound, bool):
            raise ValueError("location_table[%d] max_area_m2 must be a real number" % index)
        if not isinstance(count, int) or isinstance(count, bool) or count < 1:
            raise ValueError("location_table[%d] locations must be a positive integer" % index)
        entries.append((float(bound), count))
    entries.sort(key=lambda pair: pair[0])
    for bound, count in entries:
        if area <= bound:
            return count
    raise ValueError(
        "floor area %g m2 is beyond the largest tabulated area %g m2" % (area, entries[-1][0])
    )


def single_sample_volume_l(limit_per_m3, min_particles=MIN_PARTICLES_PER_SAMPLE,
                           floor_l=MIN_SAMPLE_VOLUME_L):
    """Return the volume in litres a single sample must draw."""
    for label, value in (("limit_per_m3", limit_per_m3), ("min_particles", min_particles),
                         ("floor_l", floor_l)):
        if not isinstance(value, (int, float)) or isinstance(value, bool):
            raise ValueError("%s must be a real number" % label)
        if not math.isfinite(float(value)) or float(value) <= 0.0:
            raise ValueError("%s must be positive and finite, got %r" % (label, value))
    derived = float(min_particles) / float(limit_per_m3) * _LITRES_PER_CUBIC_METRE
    return max(derived, float(floor_l))


def sampling_time_s(volume_l, flow_rate_lpm, min_time_s=MIN_SAMPLE_TIME_S):
    """Return the sampling time in seconds for a volume at a counter flow rate."""
    for label, value in (("volume_l", volume_l), ("flow_rate_lpm", flow_rate_lpm),
                         ("min_time_s", min_time_s)):
        if not isinstance(value, (int, float)) or isinstance(value, bool):
            raise ValueError("%s must be a real number" % label)
        if not math.isfinite(float(value)) or float(value) <= 0.0:
            raise ValueError("%s must be positive and finite, got %r" % (label, value))
    derived = float(volume_l) / float(flow_rate_lpm) * 60.0
    return max(derived, float(min_time_s))


def location_concentration(count, volume_l):
    """Return the concentration in particles per cubic metre for one location."""
    if not isinstance(count, (int, float)) or isinstance(count, bool):
        raise ValueError("count must be a real number")
    particles = float(count)
    if not math.isfinite(particles) or particles < 0.0:
        raise ValueError("count must be finite and non-negative, got %r" % (count,))
    if not isinstance(volume_l, (int, float)) or isinstance(volume_l, bool):
        raise ValueError("volume_l must be a real number")
    volume = float(volume_l)
    if not math.isfinite(volume) or volume <= 0.0:
        raise ValueError("volume_l must be positive and finite, got %r" % (volume_l,))
    return particles / (volume / _LITRES_PER_CUBIC_METRE)


def grade_location(location, limits, required_volume_l):
    """Return the per-size verdict for one reported sample location.

    location keys: id, volume_l, counts (mapping reference size -> count).
    limits is a mapping of reference size -> allowed concentration.
    """
    if not isinstance(location, dict):
        raise ValueError("location must be a mapping")
    for key in ("id", "volume_l", "counts"):
        if key not in location:
            raise ValueError("location missing required key '%s'" % key)
    if not isinstance(location["counts"], dict) or not location["counts"]:
        raise ValueError("location counts must be a non-empty mapping of size -> count")
    volume = location["volume_l"]
    if not isinstance(volume, (int, float)) or isinstance(volume, bool):
        raise ValueError("location volume_l must be a real number")
    volume = float(volume)
    if not math.isfinite(volume) or volume <= 0.0:
        raise ValueError("location volume_l must be positive and finite")
    required = float(required_volume_l)
    per_size = {}
    within = True
    for size, count in sorted(location["counts"].items()):
        size_um = validate_size_um(size)
        if size_um not in limits:
            raise ValueError("no limit supplied for reference size %g um" % size_um)
        measured = location_concentration(count, volume)
        allowed = float(limits[size_um])
        ok = measured <= allowed + CONCENTRATION_TOLERANCE
        within = within and ok
        per_size[size_um] = {
            "measured_per_m3": measured,
            "limit_per_m3": allowed,
            "within_limit": ok,
        }
    volume_ok = volume >= required - CONCENTRATION_TOLERANCE
    return {
        "id": location["id"],
        "volume_l": volume,
        "required_volume_l": required,
        "volume_sufficient": volume_ok,
        "per_size": per_size,
        "within_limits": within,
        "acceptable": within and volume_ok,
    }


def requalification_interval_days(iso_class, tight_days=TIGHT_CLASS_INTERVAL_DAYS,
                                  loose_days=LOOSE_CLASS_INTERVAL_DAYS,
                                  tight_ceiling=TIGHT_CLASS_CEILING):
    """Return the interval before the room must be qualified again."""
    level = validate_class(iso_class)
    for label, value in (("tight_days", tight_days), ("loose_days", loose_days)):
        if not isinstance(value, (int, float)) or isinstance(value, bool):
            raise ValueError("%s must be a real number" % label)
        if not math.isfinite(float(value)) or float(value) <= 0.0:
            raise ValueError("%s must be positive and finite" % label)
    return float(tight_days) if level <= float(tight_ceiling) else float(loose_days)


def assess_cleanroom_qualification(spec):
    """Plan and grade the airborne particle qualification of one room.

    spec keys: area_m2, iso_class, reference_sizes_um, flow_rate_lpm,
    locations, facility_interval_days; optional location_table,
    size_exponent, min_particles, volume_floor_l, min_time_s.
    """
    if not isinstance(spec, dict):
        raise ValueError("spec must be a mapping")
    required_keys = ("area_m2", "iso_class", "reference_sizes_um", "flow_rate_lpm",
                     "locations", "facility_interval_days")
    for key in required_keys:
        if key not in spec:
            raise ValueError("spec missing required key '%s'" % key)
    sizes = spec["reference_sizes_um"]
    if not isinstance(sizes, (list, tuple)) or not sizes:
        raise ValueError("reference_sizes_um must be a non-empty sequence")
    level = validate_class(spec["iso_class"])
    exponent = spec.get("size_exponent", DEFAULT_SIZE_EXPONENT)
    limits = {}
    for size in sizes:
        size_um = validate_size_um(size)
        limits[size_um] = limit_concentration(level, size_um, exponent)
    tightest = min(limits.values())
    volume = single_sample_volume_l(
        tightest,
        spec.get("min_particles", MIN_PARTICLES_PER_SAMPLE),
        spec.get("volume_floor_l", MIN_SAMPLE_VOLUME_L),
    )
    duration = sampling_time_s(
        volume, spec["flow_rate_lpm"], spec.get("min_time_s", MIN_SAMPLE_TIME_S)
    )
    required_locations = minimum_sample_locations(
        spec["area_m2"], spec.get("location_table")
    )
    locations = spec["locations"]
    if not isinstance(locations, (list, tuple)):
        raise ValueError("locations must be a sequence of location records")
    graded = [grade_location(item, limits, volume) for item in locations]
    interval = requalification_interval_days(level)
    facility = spec["facility_interval_days"]
    if not isinstance(facility, (int, float)) or isinstance(facility, bool):
        raise ValueError("facility_interval_days must be a real number")
    facility = float(facility)
    if not math.isfinite(facility) or facility <= 0.0:
        raise ValueError("facility_interval_days must be positive and finite")
    findings = []
    if len(graded) < required_locations:
        findings.append(
            "campaign reported %d sample locations; the floor area requires %d"
            % (len(graded), required_locations)
        )
    for record in graded:
        if not record["volume_sufficient"]:
            findings.append(
                "location %s sampled %.4f litres against the required %.4f"
                % (record["id"], record["volume_l"], record["required_volume_l"])
            )
        if not record["within_limits"]:
            findings.append("location %s exceeds the class limit" % record["id"])
    if facility > interval + CONCENTRATION_TOLERANCE:
        findings.append(
            "facility re-qualifies every %.1f days; class %g allows %.1f"
            % (facility, level, interval)
        )
    return {
        "iso_class": level,
        "limits_per_m3": limits,
        "required_locations": required_locations,
        "reported_locations": len(graded),
        "single_sample_volume_l": volume,
        "sampling_time_s": duration,
        "locations": graded,
        "requalification_interval_days": interval,
        "facility_interval_days": facility,
        "qualified": not findings,
        "findings": findings,
    }
