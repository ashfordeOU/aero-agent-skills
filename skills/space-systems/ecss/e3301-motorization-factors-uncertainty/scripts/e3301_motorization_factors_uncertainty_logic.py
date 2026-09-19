"""Minimum uncertainty factors on mechanism resistive torques and forces.

Anchor: ECSS-E-ST-33-01 clause 4.7.5.3.1 (paraphrased into an
implementable procedure; no standard text is reproduced). The factor
values below are a declared, overridable project policy table in the
shape the clause calls for, not a transcription of the standard.

Procedure implemented here:

1. Break the actuation function into its resistive contributions.
   Friction, harness resistance, adhesion and stiction, seal and
   lubricant drag, spring hysteresis, latch release and the inertia the
   actuator has to accelerate are separate line items because each one
   is known to a different accuracy.
2. Give each contribution the minimum uncertainty factor its own kind
   and its own knowledge basis carry. A contribution measured on
   flight-standard hardware carries the least, one estimated from
   heritage the most, and a kind that scatters badly in service carries
   more than a kind that does not.
3. Apply the factor contribution by contribution. Factoring the sum
   once with a single number lets a well-known term subsidise a badly
   known one, which is the outcome the per-kind table exists to stop.
4. Require every contribution to have been evaluated at the life points
   the function is dimensioned for and over its whole range of travel.
   A value taken at begin of life at mid-stroke is not the worst case
   and cannot stand in for it.
5. Report the factored total, the uncertainty allowance it contains and
   the contribution that dominates, so the reader can see which
   measurement would buy the most back.

Stdlib only, offline, deterministic.
"""

# Resistive kinds an actuation function is built from, with the minimum
# uncertainty factor each carries before the knowledge basis is priced.
MIN_FACTOR_BY_KIND = {
    "dry-friction": 3.00,
    "lubricated-friction": 2.00,
    "harness-cable-resistance": 3.00,
    "adhesion-stiction": 3.00,
    "seal-drag": 3.00,
    "viscous-damping": 2.00,
    "spring-hysteresis": 1.50,
    "latch-release": 2.00,
    "inertia": 1.20,
}
VALID_KINDS = tuple(sorted(MIN_FACTOR_BY_KIND))

# How the contribution was obtained, and the uplift that basis adds on
# top of the per-kind minimum.
UPLIFT_BY_BASIS = {
    "measured-on-flight-standard-hardware": 1.00,
    "measured-on-representative-hardware": 1.10,
    "analysed-with-validated-model": 1.25,
    "estimated-from-heritage": 1.50,
}
VALID_BASES = tuple(sorted(UPLIFT_BY_BASIS))

# Life points an actuation function is dimensioned at.
VALID_LIFE_POINTS = ("begin-of-life", "end-of-life")

# Units an actuation function can be budgeted in. A rotary function is
# budgeted in torque and a linear one in force; the two never mix
# inside one function.
VALID_UNITS = ("torque-nm", "force-n")

# Widest travel gap a station schedule may leave, as a share of the
# declared range, with an absolute floor so a very short travel is not
# forced into an absurd number of stations.
MAX_TRAVEL_GAP_FRACTION = 0.10
MIN_TRAVEL_GAP = 1.0

# A gap that lands exactly on the allowed width is a pass. The width is a
# product of floats, so the comparison is relaxed by a relative tolerance
# rather than tested strictly.
GAP_RELATIVE_TOLERANCE = 1.0e-12

# A factored contribution is a product of floats, so a declared factor
# sitting exactly on its minimum can land a few units in the last place
# below it. This tolerance stops that being reported as a shortfall.
FACTOR_TOLERANCE = 1.0e-12


def _numeric(label, value, minimum=None):
    if not isinstance(value, (int, float)) or isinstance(value, bool):
        raise ValueError("%s must be numeric, got %r" % (label, value))
    value = float(value)
    if minimum is not None and value < minimum:
        raise ValueError("%s must be >= %r, got %r" % (label, minimum, value))
    return value


def _identifier(label, value):
    if not isinstance(value, str) or not value.strip():
        raise ValueError("%s must be a non-empty string" % label)
    return value.strip()


def minimum_uncertainty_factor(kind, basis):
    """Minimum uncertainty factor for a resistive kind on a knowledge basis."""
    if kind not in MIN_FACTOR_BY_KIND:
        raise ValueError(
            "unknown resistive kind %r (expected one of %s)"
            % (kind, ", ".join(VALID_KINDS))
        )
    if basis not in UPLIFT_BY_BASIS:
        raise ValueError(
            "unknown knowledge basis %r (expected one of %s)"
            % (basis, ", ".join(VALID_BASES))
        )
    return MIN_FACTOR_BY_KIND[kind] * UPLIFT_BY_BASIS[basis]


def validate_contribution(contribution):
    """Validate one resistive contribution and return a normalized copy."""
    if not isinstance(contribution, dict):
        raise ValueError("contribution must be a mapping")
    cid = _identifier("contribution id", contribution.get("id"))
    kind = contribution.get("kind")
    if kind not in MIN_FACTOR_BY_KIND:
        raise ValueError(
            "contribution %s has unknown kind %r (expected one of %s)"
            % (cid, kind, ", ".join(VALID_KINDS))
        )
    basis = contribution.get("basis")
    if basis not in UPLIFT_BY_BASIS:
        raise ValueError(
            "contribution %s has unknown basis %r (expected one of %s)"
            % (cid, basis, ", ".join(VALID_BASES))
        )
    nominal = _numeric("contribution %s nominal_value" % cid, contribution.get("nominal_value"), 0.0)
    declared = contribution.get("declared_factor")
    if declared is not None:
        declared = _numeric("contribution %s declared_factor" % cid, declared, 1.0)
    life_points = contribution.get("life_points", [])
    if not isinstance(life_points, (list, tuple)):
        raise ValueError("contribution %s life_points must be a sequence" % cid)
    for point in life_points:
        if point not in VALID_LIFE_POINTS:
            raise ValueError(
                "contribution %s has unknown life point %r" % (cid, point)
            )
    worst_case = contribution.get("worst_case_over_travel", False)
    if not isinstance(worst_case, bool):
        raise ValueError(
            "contribution %s worst_case_over_travel must be a boolean" % cid
        )
    stations = contribution.get("travel_stations", [])
    if not isinstance(stations, (list, tuple)):
        raise ValueError("contribution %s travel_stations must be a sequence" % cid)
    stations = [
        _numeric("contribution %s travel station" % cid, s) for s in stations
    ]
    return {
        "id": cid,
        "kind": kind,
        "basis": basis,
        "nominal_value": nominal,
        "declared_factor": declared,
        "life_points": [str(p) for p in life_points],
        "worst_case_over_travel": worst_case,
        "travel_stations": sorted(stations),
    }


def applied_uncertainty_factor(contribution):
    """Return (factor, findings) after holding a declared factor to the floor."""
    norm = validate_contribution(contribution)
    floor = minimum_uncertainty_factor(norm["kind"], norm["basis"])
    findings = []
    declared = norm["declared_factor"]
    if declared is None:
        return floor, findings
    if declared < floor - FACTOR_TOLERANCE:
        findings.append("declared-factor-below-minimum")
        return floor, findings
    return declared, findings


def factored_value(contribution):
    """Resistive contribution after its uncertainty factor is applied."""
    norm = validate_contribution(contribution)
    factor, _ = applied_uncertainty_factor(norm)
    return norm["nominal_value"] * factor


def travel_coverage_findings(contribution, travel_range):
    """Findings about how a contribution covers the declared travel range."""
    norm = validate_contribution(contribution)
    span = _numeric("travel_range", travel_range, 0.0)
    if span <= 0.0:
        raise ValueError("travel_range must be positive")
    if norm["worst_case_over_travel"]:
        return []
    stations = norm["travel_stations"]
    if not stations:
        return ["travel-coverage-not-declared"]
    findings = []
    allowed_gap = max(MIN_TRAVEL_GAP, MAX_TRAVEL_GAP_FRACTION * span)
    allowed_gap *= 1.0 + GAP_RELATIVE_TOLERANCE
    if stations[0] > allowed_gap:
        findings.append("travel-start-not-covered")
    if span - stations[-1] > allowed_gap:
        findings.append("travel-end-not-covered")
    for low, high in zip(stations, stations[1:]):
        if high - low > allowed_gap:
            findings.append("travel-gap-wider-than-allowed")
            break
    return findings


def life_coverage_findings(contribution, required_life_points):
    """Findings about the life points a contribution was evaluated at."""
    norm = validate_contribution(contribution)
    if not isinstance(required_life_points, (list, tuple)) or not required_life_points:
        raise ValueError("required_life_points must be a non-empty sequence")
    findings = []
    for point in required_life_points:
        if point not in VALID_LIFE_POINTS:
            raise ValueError("unknown required life point %r" % (point,))
        if point not in norm["life_points"]:
            findings.append("not-evaluated-at:%s" % point)
    return findings


def assess_contribution(contribution, travel_range, required_life_points):
    """Assess one resistive contribution against clause 4.7.5.3.1."""
    norm = validate_contribution(contribution)
    factor, findings = applied_uncertainty_factor(norm)
    findings = list(findings)
    findings.extend(life_coverage_findings(norm, required_life_points))
    findings.extend(travel_coverage_findings(norm, travel_range))
    return {
        "id": norm["id"],
        "kind": norm["kind"],
        "basis": norm["basis"],
        "nominal_value": norm["nominal_value"],
        "minimum_factor": minimum_uncertainty_factor(norm["kind"], norm["basis"]),
        "applied_factor": factor,
        "factored_value": norm["nominal_value"] * factor,
        "findings": findings,
        "compliant": not findings,
    }


def assess_motorization_uncertainty(function_record):
    """Build the factored resistive budget of one actuation function."""
    if not isinstance(function_record, dict):
        raise ValueError("function_record must be a mapping")
    fid = _identifier("function id", function_record.get("id"))
    units = function_record.get("units")
    if units not in VALID_UNITS:
        raise ValueError(
            "function %s has unknown units %r (expected one of %s)"
            % (fid, units, ", ".join(VALID_UNITS))
        )
    travel_range = _numeric("function %s travel_range" % fid, function_record.get("travel_range"), 0.0)
    if travel_range <= 0.0:
        raise ValueError("function %s travel_range must be positive" % fid)
    required = function_record.get("required_life_points", list(VALID_LIFE_POINTS))
    contributions = function_record.get("contributions")
    if not isinstance(contributions, list) or not contributions:
        raise ValueError("function %s needs a non-empty contributions list" % fid)
    results = []
    seen = set()
    for contribution in contributions:
        result = assess_contribution(contribution, travel_range, required)
        if result["id"] in seen:
            raise ValueError("duplicate contribution id %r" % (result["id"],))
        seen.add(result["id"])
        results.append(result)
    nominal_total = sum(r["nominal_value"] for r in results)
    factored_total = sum(r["factored_value"] for r in results)
    dominant = max(results, key=lambda r: r["factored_value"])
    failing = [r["id"] for r in results if not r["compliant"]]
    return {
        "function_id": fid,
        "units": units,
        "travel_range": travel_range,
        "required_life_points": list(required),
        "contributions": results,
        "nominal_total": nominal_total,
        "factored_total": factored_total,
        "uncertainty_allowance": factored_total - nominal_total,
        "dominant_contribution_id": dominant["id"],
        "non_compliant_ids": failing,
        "compliant": not failing,
    }
