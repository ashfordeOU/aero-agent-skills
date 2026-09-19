"""Construction of a particle contamination monitoring plan.

Anchor: ECSS-Q-ST-70-50C programme clause -- producing the monitoring plan
that states where particle monitoring is done, by which method, and how often.
Paraphrased into an implementable procedure; no standard text is reproduced.

Procedure implemented here
--------------------------
1. Validate each declared zone: identifier, floor area, declared cleanroom
   class, the methods assigned to it and the criticality of the work done in
   it.
2. Size the sampling locations of each zone from its floor area, never fewer
   than a stated minimum, and never fewer than the operator asked for.
3. Set the interval of each method from its base period shortened by the
   criticality of the zone, floored at one day so a plan cannot ask for a
   continuous campaign it cannot staff.
4. Count the occurrences each method yields across the campaign and total the
   samples the plan commits to, so the plan carries its own workload.
5. Report the findings a plan raises on its own: a duplicated zone, a zone
   with no method, a method that yields fewer than two occurrences across the
   campaign, and a declared class with no airborne counting behind it.
"""

import math

__all__ = [
    "METHODS",
    "BASE_INTERVAL_DAYS",
    "CRITICALITY_FACTORS",
    "MIN_LOCATIONS",
    "MIN_OCCURRENCES",
    "validate_identifier",
    "validate_area_m2",
    "validate_method",
    "validate_criticality",
    "validate_campaign_days",
    "location_count",
    "interval_days",
    "occurrences",
    "plan_zone",
    "build_plan",
    "plan_totals",
    "assess_monitoring_plan",
]

METHODS = ("airborne-count", "surface-fallout", "tape-lift")

# Base revisit period of each method for routine work, in days.
BASE_INTERVAL_DAYS = {
    "airborne-count": 30.0,
    "surface-fallout": 14.0,
    "tape-lift": 90.0,
}

# Criticality shortens the interval; it never lengthens it.
CRITICALITY_FACTORS = {
    "routine": 1.0,
    "elevated": 2.0,
    "critical": 4.0,
}

# A zone is never sampled at a single point, however small it is.
MIN_LOCATIONS = 2

# A single sample is a snapshot, not a trend; a plan owes at least two.
MIN_OCCURRENCES = 2

# Intervals are a ratio of days: an exact equality can land a few ULPs on the
# wrong side. Absorb the representation error here.
INTERVAL_TOLERANCE_DAYS = 1e-9


def validate_identifier(value, label="zone_id"):
    """Return the validated, stripped identifier string."""
    if not isinstance(value, str):
        raise ValueError("%s must be a string, got %r" % (label, value))
    text = value.strip()
    if not text:
        raise ValueError("%s must not be empty" % label)
    return text


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


def validate_method(method):
    """Return the validated monitoring method name."""
    if not isinstance(method, str):
        raise ValueError("method must be a string, got %r" % (method,))
    value = method.strip().lower()
    if value not in METHODS:
        raise ValueError("method must be one of %s, got %r" % (", ".join(METHODS), method))
    return value


def validate_criticality(criticality):
    """Return the validated criticality band of the work done in a zone."""
    if not isinstance(criticality, str):
        raise ValueError("criticality must be a string, got %r" % (criticality,))
    value = criticality.strip().lower()
    if value not in CRITICALITY_FACTORS:
        raise ValueError(
            "criticality must be one of %s, got %r"
            % (", ".join(sorted(CRITICALITY_FACTORS)), criticality)
        )
    return value


def validate_campaign_days(days):
    """Return the validated campaign duration in days."""
    if not isinstance(days, (int, float)) or isinstance(days, bool):
        raise ValueError("campaign_days must be a real number, got %r" % (days,))
    value = float(days)
    if not math.isfinite(value):
        raise ValueError("campaign_days must be finite")
    if value <= 0.0:
        raise ValueError("campaign_days must be positive, got %g" % value)
    return value


def location_count(area_m2, requested=None):
    """Return the number of sampling locations a zone of this area carries."""
    area = validate_area_m2(area_m2)
    derived = int(math.ceil(math.sqrt(area) - 1e-12))
    count = max(derived, MIN_LOCATIONS)
    if requested is not None:
        if not isinstance(requested, int) or isinstance(requested, bool):
            raise ValueError("requested location count must be an integer, got %r" % (requested,))
        if requested < 1:
            raise ValueError("requested location count must be at least 1, got %d" % requested)
        count = max(count, requested)
    return count


def interval_days(method, criticality):
    """Return the revisit interval of a method in a zone of this criticality."""
    name = validate_method(method)
    band = validate_criticality(criticality)
    value = BASE_INTERVAL_DAYS[name] / CRITICALITY_FACTORS[band]
    return max(value, 1.0)


def occurrences(campaign_days, interval):
    """Return how many times a method at this interval runs across a campaign."""
    days = validate_campaign_days(campaign_days)
    if not isinstance(interval, (int, float)) or isinstance(interval, bool):
        raise ValueError("interval must be a real number, got %r" % (interval,))
    step = float(interval)
    if not math.isfinite(step) or step <= 0.0:
        raise ValueError("interval must be positive and finite, got %r" % (interval,))
    ratio = days / step
    whole = math.floor(ratio)
    if abs(ratio - (whole + 1.0)) <= INTERVAL_TOLERANCE_DAYS:
        whole = whole + 1.0
    return int(whole) + 1


def plan_zone(zone, campaign_days):
    """Return the plan entries for one zone, one entry per assigned method."""
    if not isinstance(zone, dict):
        raise ValueError("zone must be a mapping")
    for key in ("zone_id", "area_m2", "methods", "criticality"):
        if key not in zone:
            raise ValueError("zone missing required key '%s'" % key)
    zone_id = validate_identifier(zone["zone_id"])
    area = validate_area_m2(zone["area_m2"])
    band = validate_criticality(zone["criticality"])
    methods = zone["methods"]
    if not isinstance(methods, (list, tuple)):
        raise ValueError("zone %r: methods must be a sequence" % zone_id)
    locations = location_count(area, zone.get("requested_locations"))
    days = validate_campaign_days(campaign_days)
    entries = []
    seen = []
    for method in methods:
        name = validate_method(method)
        if name in seen:
            continue
        seen.append(name)
        step = interval_days(name, band)
        runs = occurrences(days, step)
        entries.append(
            {
                "zone_id": zone_id,
                "method": name,
                "locations": locations,
                "interval_days": step,
                "occurrences": runs,
                "samples": locations * runs,
                "criticality": band,
                "iso_class": zone.get("iso_class"),
            }
        )
    return entries


def build_plan(zones, campaign_days):
    """Return the ordered plan entries for every declared zone."""
    if not isinstance(zones, (list, tuple)) or not zones:
        raise ValueError("zones must be a non-empty sequence of zone mappings")
    entries = []
    for zone in zones:
        entries.extend(plan_zone(zone, campaign_days))
    return entries


def plan_totals(entries):
    """Return the total samples and the per-method sample counts of a plan."""
    if not isinstance(entries, (list, tuple)):
        raise ValueError("entries must be a sequence of plan entries")
    per_method = {name: 0 for name in METHODS}
    total = 0
    for entry in entries:
        if not isinstance(entry, dict) or "method" not in entry or "samples" not in entry:
            raise ValueError("each entry must carry 'method' and 'samples'")
        per_method[validate_method(entry["method"])] += int(entry["samples"])
        total += int(entry["samples"])
    return {"total_samples": total, "per_method": per_method}


def assess_monitoring_plan(spec):
    """Build the monitoring plan and report the findings it raises.

    spec keys: zones (sequence of zone mappings), campaign_days.
    """
    if not isinstance(spec, dict):
        raise ValueError("spec must be a mapping")
    for key in ("zones", "campaign_days"):
        if key not in spec:
            raise ValueError("spec missing required key '%s'" % key)
    zones = spec["zones"]
    if not isinstance(zones, (list, tuple)) or not zones:
        raise ValueError("spec['zones'] must be a non-empty sequence")
    days = validate_campaign_days(spec["campaign_days"])

    findings = []
    seen_ids = []
    for zone in zones:
        if not isinstance(zone, dict) or "zone_id" not in zone:
            raise ValueError("each zone must be a mapping carrying 'zone_id'")
        zone_id = validate_identifier(zone["zone_id"])
        if zone_id in seen_ids:
            findings.append("zone %r is declared more than once in the plan" % zone_id)
        else:
            seen_ids.append(zone_id)
        methods = zone.get("methods")
        if not methods:
            findings.append("zone %r carries no monitoring method" % zone_id)
        if zone.get("iso_class") is not None and "airborne-count" not in (methods or []):
            findings.append(
                "zone %r declares a cleanroom class with no airborne counting behind it" % zone_id
            )

    entries = build_plan(zones, days)
    for entry in entries:
        if entry["occurrences"] < MIN_OCCURRENCES:
            findings.append(
                "zone %r %s yields %d occurrence over a %g day campaign; a trend needs at least %d"
                % (entry["zone_id"], entry["method"], entry["occurrences"], days, MIN_OCCURRENCES)
            )

    totals = plan_totals(entries)
    return {
        "campaign_days": days,
        "entries": entries,
        "zone_count": len(seen_ids),
        "total_samples": totals["total_samples"],
        "per_method": totals["per_method"],
        "complete": not findings,
        "findings": findings,
    }
