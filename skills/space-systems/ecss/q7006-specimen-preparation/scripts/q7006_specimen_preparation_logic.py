"""Specimen preparation for a particle and UV radiation degradation test.

Anchor: ECSS-Q-ST-70-06C, test-item clause -- how many coupons an irradiation
campaign needs, which of them are exposed and which are held back as unexposed
references, how a coupon has to be sized so that it sits inside the uniform
part of the beam, and how many exposure runs the coupon population implies.
Paraphrased into an implementable procedure; no standard text is reproduced.

Procedure implemented here
--------------------------
1. Validate each property to be measured: whether reading it consumes the
   coupon, and whether it can be read in place without breaking vacuum.
2. Count the exposed coupons a property needs. A destructive reading consumes
   one set of replicates at every measurement point; a non-destructive
   reading re-reads the same set at every point.
3. Count the matching unexposed reference coupons, which follow the same
   thermal and vacuum history in the dark so that ageing is separable from
   the exposure.
4. Fit a coupon into the uniform area of the beam, trying both orientations
   and honouring the edge keep-out and the gap between neighbours.
5. Divide the coupon population by what fits in one run to get the number of
   exposure runs, and report every finding that would make the population
   unusable.
"""

import math

__all__ = [
    "MINIMUM_REPLICATES",
    "FIT_TOLERANCE_MM",
    "validate_property",
    "exposed_coupons_for_property",
    "reference_coupons_for_property",
    "coupon_area_mm2",
    "coupons_per_run",
    "run_count",
    "population_findings",
    "plan_specimens",
]

# A degradation curve read on fewer than three coupons cannot separate the
# material's response from a single preparation or mounting accident.
MINIMUM_REPLICATES = 3

# Dimensional comparisons are made to this tolerance so that a coupon cut to
# exactly the keep-out limit is not rejected by representation error.
FIT_TOLERANCE_MM = 1e-9


def _real(value, label, allow_zero=False):
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise ValueError("%s must be a real number, got %r" % (label, value))
    number = float(value)
    if not math.isfinite(number):
        raise ValueError("%s must be finite, got %r" % (label, value))
    if number < 0.0 or (number == 0.0 and not allow_zero):
        raise ValueError("%s must be positive, got %r" % (label, value))
    return number


def _count(value, label, minimum=1):
    if isinstance(value, bool) or not isinstance(value, int):
        raise ValueError("%s must be an integer, got %r" % (label, value))
    if value < minimum:
        raise ValueError("%s must be at least %d, got %d" % (label, minimum, value))
    return value


def validate_property(prop):
    """Return a normalised record for one property the campaign measures."""
    if not isinstance(prop, dict):
        raise ValueError("each property must be a mapping")
    for key in ("name", "destructive"):
        if key not in prop:
            raise ValueError("property missing required key '%s'" % key)
    name = prop["name"]
    if not isinstance(name, str) or not name.strip():
        raise ValueError("property name must be a non-empty string")
    if not isinstance(prop["destructive"], bool):
        raise ValueError("property '%s': destructive must be a boolean" % name)
    in_situ = prop.get("in_situ", False)
    if not isinstance(in_situ, bool):
        raise ValueError("property '%s': in_situ must be a boolean" % name)
    if prop["destructive"] and in_situ:
        raise ValueError(
            "property '%s' cannot be both destructive and read in place" % name
        )
    replicates = _count(prop.get("replicates", MINIMUM_REPLICATES), "replicates")
    return {
        "name": name.strip(),
        "destructive": prop["destructive"],
        "in_situ": in_situ,
        "replicates": replicates,
    }


def exposed_coupons_for_property(prop, measurement_points):
    """Return how many exposed coupons this property consumes."""
    record = validate_property(prop)
    points = _count(measurement_points, "measurement_points")
    if record["destructive"]:
        return record["replicates"] * points
    return record["replicates"]


def reference_coupons_for_property(prop, measurement_points):
    """Return how many unexposed reference coupons this property needs."""
    record = validate_property(prop)
    points = _count(measurement_points, "measurement_points")
    if record["destructive"]:
        return record["replicates"] * points
    if record["in_situ"]:
        return 0
    return record["replicates"]


def coupon_area_mm2(dimensions_mm):
    """Return the planform area of a rectangular coupon in mm^2."""
    if not isinstance(dimensions_mm, (list, tuple)) or len(dimensions_mm) != 2:
        raise ValueError("dimensions_mm must be a (length, width) pair")
    length = _real(dimensions_mm[0], "coupon length")
    width = _real(dimensions_mm[1], "coupon width")
    return length * width


def coupons_per_run(coupon_mm, uniform_area_mm, gap_mm=0.0, edge_keep_out_mm=0.0):
    """Return how many coupons fit inside the uniform beam area in one run."""
    if not isinstance(coupon_mm, (list, tuple)) or len(coupon_mm) != 2:
        raise ValueError("coupon_mm must be a (length, width) pair")
    if not isinstance(uniform_area_mm, (list, tuple)) or len(uniform_area_mm) != 2:
        raise ValueError("uniform_area_mm must be a (length, width) pair")
    c_long = _real(coupon_mm[0], "coupon length")
    c_short = _real(coupon_mm[1], "coupon width")
    u_long = _real(uniform_area_mm[0], "uniform area length")
    u_short = _real(uniform_area_mm[1], "uniform area width")
    gap = _real(gap_mm, "gap_mm", allow_zero=True)
    keep_out = _real(edge_keep_out_mm, "edge_keep_out_mm", allow_zero=True)
    usable_long = u_long - 2.0 * keep_out
    usable_short = u_short - 2.0 * keep_out
    if usable_long <= 0.0 or usable_short <= 0.0:
        return 0
    best = 0
    for along, across in ((c_long, c_short), (c_short, c_long)):
        rows = math.floor((usable_long + gap) / (along + gap) + FIT_TOLERANCE_MM)
        cols = math.floor((usable_short + gap) / (across + gap) + FIT_TOLERANCE_MM)
        best = max(best, int(max(rows, 0)) * int(max(cols, 0)))
    return best


def run_count(total_coupons, per_run):
    """Return the number of exposure runs the coupon population needs."""
    total = _count(total_coupons, "total_coupons", minimum=0)
    capacity = _count(per_run, "per_run", minimum=0)
    if total == 0:
        return 0
    if capacity == 0:
        raise ValueError("no coupon fits the uniform beam area; capacity is zero")
    return -(-total // capacity)


def population_findings(records, coupon_mm, uniform_area_mm, capacity):
    """Return the findings that make a prepared coupon population unusable."""
    findings = []
    if not records:
        findings.append("no property is measured; the campaign has no coupon demand")
    for record in records:
        if record["replicates"] < MINIMUM_REPLICATES:
            findings.append(
                "property '%s' carries %d replicates, below the minimum of %d"
                % (record["name"], record["replicates"], MINIMUM_REPLICATES)
            )
    if capacity == 0:
        findings.append(
            "coupon %.1f x %.1f mm does not fit the uniform area %.1f x %.1f mm"
            % (coupon_mm[0], coupon_mm[1], uniform_area_mm[0], uniform_area_mm[1])
        )
    return findings


def plan_specimens(spec):
    """Plan the coupon population for a radiation degradation campaign.

    spec keys: properties, measurement_points, coupon_mm, uniform_area_mm,
    optional gap_mm, edge_keep_out_mm, spare_fraction.
    """
    if not isinstance(spec, dict):
        raise ValueError("spec must be a mapping")
    for key in ("properties", "measurement_points", "coupon_mm", "uniform_area_mm"):
        if key not in spec:
            raise ValueError("spec missing required key '%s'" % key)
    properties = spec["properties"]
    if not isinstance(properties, (list, tuple)):
        raise ValueError("spec['properties'] must be a sequence")
    points = _count(spec["measurement_points"], "measurement_points")
    records = [validate_property(prop) for prop in properties]
    names = [record["name"] for record in records]
    if len(set(names)) != len(names):
        raise ValueError("property names must be unique within one campaign")
    spare_fraction = _real(spec.get("spare_fraction", 0.0), "spare_fraction", allow_zero=True)
    if spare_fraction > 1.0:
        raise ValueError("spare_fraction must lie in [0, 1]")
    per_property = []
    exposed = 0
    references = 0
    for record, prop in zip(records, properties):
        exposed_here = exposed_coupons_for_property(prop, points)
        reference_here = reference_coupons_for_property(prop, points)
        per_property.append(
            {
                "name": record["name"],
                "destructive": record["destructive"],
                "in_situ": record["in_situ"],
                "replicates": record["replicates"],
                "exposed": exposed_here,
                "reference": reference_here,
            }
        )
        exposed += exposed_here
        references += reference_here
    spares = int(math.ceil(exposed * spare_fraction - FIT_TOLERANCE_MM))
    exposed_total = exposed + spares
    capacity = coupons_per_run(
        spec["coupon_mm"],
        spec["uniform_area_mm"],
        spec.get("gap_mm", 0.0),
        spec.get("edge_keep_out_mm", 0.0),
    )
    findings = population_findings(
        records, spec["coupon_mm"], spec["uniform_area_mm"], capacity
    )
    runs = run_count(exposed_total, capacity) if capacity else 0
    return {
        "properties": per_property,
        "measurement_points": points,
        "exposed_coupons": exposed_total,
        "spare_coupons": spares,
        "reference_coupons": references,
        "total_coupons": exposed_total + references,
        "coupons_per_run": capacity,
        "exposure_runs": runs,
        "coupon_area_mm2": coupon_area_mm2(spec["coupon_mm"]),
        "findings": findings,
        "ready": not findings,
    }
