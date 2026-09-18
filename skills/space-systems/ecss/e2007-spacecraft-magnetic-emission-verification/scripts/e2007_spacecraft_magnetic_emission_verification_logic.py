"""Spacecraft steady magnetic emission verification by analysis and test.

Anchor: ECSS-E-ST-20-07C clause 5.3.6 (paraphrased into an implementable
procedure; no standard text is reproduced).

Procedure implemented here:

1. Build the analysis side of the verification: validate every declared
   unit dipole contribution, vector-sum the moments so that cancelling
   axes really cancel, and root-sum-square the contribution
   uncertainties, because they are independent and adding them
   arithmetically would inflate the budget past any achievable limit.
2. Expand the summed moment by the declared coverage factor to obtain
   the analysis worst case the vehicle has to be shown against.
3. Bring in the test side: the measured system residual moment, itself
   expanded by its own measurement uncertainty.
4. Reconcile the two. A measured moment above the analysis worst case
   means the budget missed a contributor; an analysis worst case far
   above the measured value means the model is not representative even
   though it is conservative. Both are findings, because the clause is
   satisfied by analysis AND test agreeing, not by either one alone.
5. Project the governing moment to the far-field flux density at the
   declared evaluation radius and orientation and compare it with the
   vehicle steady-emission limit.
6. Refuse a verification whose evidence set is missing the analysis or
   the test leg, and flag a budget with no measured contributor at all.

Field model: the far-field of a magnetic dipole of moment m at radius r
and polar angle theta from the moment axis has magnitude

    B = (mu0 / 4pi) * m * sqrt(1 + 3 cos^2(theta)) / r^3

with mu0 / 4pi = 1e-7 T*m/A. Working in nanotesla, the leading constant
is exactly 100 nT*m^3/(A*m^2), which is why every quantity here is
carried in nT rather than T: a spacecraft limit sits at tens of nT and a
tesla-valued float leaves no significant digits for a comparison.

Stdlib only, offline, deterministic.
"""

import math

# (mu0 / 4pi) expressed so that a moment in A*m^2 at a radius in m gives
# a flux density directly in nanotesla.
DIPOLE_CONSTANT_NT_M3_PER_AM2 = 100.0

METHOD_MEASURED = "measured"
METHOD_ANALYSIS = "analysis"
METHOD_SIMILARITY = "similarity"
VALID_METHODS = (METHOD_MEASURED, METHOD_ANALYSIS, METHOD_SIMILARITY)

# Coverage factor applied to a root-sum-squared moment uncertainty to
# obtain the worst case the budget is held against.
MOMENT_COVERAGE_FACTOR = 2.0

# An analysis worst case more than this many times the measured system
# moment is conservative but unrepresentative: the model has not been
# validated by the test it is meant to be reconciled with.
MAX_RECONCILIATION_RATIO = 3.0

# A moment is a sum of signed components and a flux density is a product
# of a moment with an inverse cube, so a design sitting exactly on a
# limit can land a few units in the last place above it. These
# tolerances are far below any magnetometer resolution and absorb that
# representation error without relaxing the limit itself.
MOMENT_TOLERANCE_AM2 = 1.0e-12
FIELD_TOLERANCE_NT = 1.0e-9


def _numeric(label, value, minimum=None):
    if not isinstance(value, (int, float)) or isinstance(value, bool):
        raise ValueError("%s must be numeric, got %r" % (label, value))
    value = float(value)
    if value != value or value in (float("inf"), float("-inf")):
        raise ValueError("%s must be finite, got %r" % (label, value))
    if minimum is not None and value < minimum:
        raise ValueError("%s must be >= %r, got %r" % (label, minimum, value))
    return value


def _boolean(label, value):
    if not isinstance(value, bool):
        raise ValueError("%s must be a boolean, got %r" % (label, value))
    return value


def validate_source(source):
    """Validate one dipole contributor and return a normalized copy."""
    if not isinstance(source, dict):
        raise ValueError("source must be a mapping")
    source_id = source.get("id")
    if not isinstance(source_id, str) or not source_id.strip():
        raise ValueError("source needs a non-empty string id")
    method = source.get("method")
    if method not in VALID_METHODS:
        raise ValueError(
            "source %s has unknown method %r (expected one of %s)"
            % (source_id, method, ", ".join(VALID_METHODS))
        )
    moment = source.get("moment_am2")
    if not isinstance(moment, (list, tuple)) or len(moment) != 3:
        raise ValueError(
            "source %s moment_am2 must be a three-component sequence" % source_id
        )
    components = [
        _numeric("source %s moment component" % source_id, c) for c in moment
    ]
    uncertainty = _numeric(
        "source %s uncertainty_am2" % source_id, source.get("uncertainty_am2", 0.0), 0.0
    )
    return {
        "id": source_id,
        "method": method,
        "moment_am2": tuple(components),
        "uncertainty_am2": uncertainty,
        "compensated": _boolean(
            "source %s compensated" % source_id, source.get("compensated", False)
        ),
    }


def validate_sources(sources):
    """Validate a contributor list and refuse a duplicate identifier."""
    if not isinstance(sources, list) or not sources:
        raise ValueError("sources must be a non-empty list")
    seen = set()
    normalized = []
    for source in sources:
        norm = validate_source(source)
        if norm["id"] in seen:
            raise ValueError("duplicate source id %r" % (norm["id"],))
        seen.add(norm["id"])
        normalized.append(norm)
    return normalized


def vector_sum_moment(sources):
    """Vector sum of the contributor moments, in A*m^2."""
    normalized = validate_sources(sources)
    totals = [0.0, 0.0, 0.0]
    for source in normalized:
        for axis in range(3):
            totals[axis] += source["moment_am2"][axis]
    return tuple(totals)


def moment_magnitude(vector):
    """Magnitude of a three-component moment, in A*m^2."""
    if not isinstance(vector, (list, tuple)) or len(vector) != 3:
        raise ValueError("vector must be a three-component sequence")
    components = [_numeric("moment component", c) for c in vector]
    return math.sqrt(sum(c * c for c in components))


def combined_uncertainty_am2(sources):
    """Root-sum-square of the independent contributor uncertainties."""
    normalized = validate_sources(sources)
    total = 0.0
    for source in normalized:
        total += source["uncertainty_am2"] * source["uncertainty_am2"]
    return math.sqrt(total)


def analysis_worst_case_am2(sources, coverage_factor=MOMENT_COVERAGE_FACTOR):
    """Summed moment expanded by the covered budget uncertainty."""
    factor = _numeric("coverage_factor", coverage_factor, 0.0)
    magnitude = moment_magnitude(vector_sum_moment(sources))
    return magnitude + factor * combined_uncertainty_am2(sources)


def far_field_flux_density_nt(moment_am2, distance_m, angle_deg=0.0):
    """Dipole far-field flux density in nanotesla."""
    moment = _numeric("moment_am2", moment_am2, 0.0)
    distance = _numeric("distance_m", distance_m)
    if distance <= 0.0:
        raise ValueError("distance_m must be positive, got %r" % (distance,))
    angle = _numeric("angle_deg", angle_deg)
    if angle < 0.0 or angle > 180.0:
        raise ValueError("angle_deg must lie in [0, 180], got %r" % (angle,))
    cosine = math.cos(math.radians(angle))
    shape = math.sqrt(1.0 + 3.0 * cosine * cosine)
    return (
        DIPOLE_CONSTANT_NT_M3_PER_AM2
        * moment
        * shape
        / (distance * distance * distance)
    )


def measured_worst_case_am2(
    measured_moment_am2, measurement_uncertainty_am2=0.0,
    coverage_factor=MOMENT_COVERAGE_FACTOR,
):
    """Measured system moment expanded by its own measurement uncertainty."""
    measured = _numeric("measured_moment_am2", measured_moment_am2, 0.0)
    uncertainty = _numeric(
        "measurement_uncertainty_am2", measurement_uncertainty_am2, 0.0
    )
    factor = _numeric("coverage_factor", coverage_factor, 0.0)
    return measured + factor * uncertainty


def reconcile_analysis_and_test(analysis_am2, measured_am2):
    """Findings from comparing the analysis worst case with the test result."""
    analysis = _numeric("analysis_am2", analysis_am2, 0.0)
    measured = _numeric("measured_am2", measured_am2, 0.0)
    findings = []
    if measured > analysis + MOMENT_TOLERANCE_AM2:
        findings.append("measured-moment-above-the-analysis-worst-case")
    if measured > 0.0 and analysis > MAX_RECONCILIATION_RATIO * measured:
        findings.append("analysis-worst-case-outside-the-reconciliation-band")
    if measured == 0.0 and analysis > MOMENT_TOLERANCE_AM2:
        findings.append("analysis-worst-case-outside-the-reconciliation-band")
    return findings


def check_evidence_coverage(case):
    """Findings for a verification missing the analysis or the test leg."""
    if not isinstance(case, dict):
        raise ValueError("case must be a mapping")
    findings = []
    if not _boolean("analysis_complete", case.get("analysis_complete", False)):
        findings.append("steady-emission-not-covered-by-analysis")
    if not _boolean("test_complete", case.get("test_complete", False)):
        findings.append("steady-emission-not-covered-by-test")
    return findings


def check_budget_provenance(sources):
    """Findings for a budget with no measured contributor behind it."""
    normalized = validate_sources(sources)
    methods = set(source["method"] for source in normalized)
    findings = []
    if METHOD_MEASURED not in methods:
        findings.append("no-contributor-moment-is-measured")
    if methods == set((METHOD_SIMILARITY,)):
        findings.append("budget-rests-on-similarity-only")
    return findings


def check_field_limit(field_nt, limit_nt):
    """Findings for a flux density above the vehicle steady-emission limit."""
    field = _numeric("field_nt", field_nt, 0.0)
    limit = _numeric("limit_nt", limit_nt)
    if limit <= 0.0:
        raise ValueError("limit_nt must be positive, got %r" % (limit,))
    if field > limit + FIELD_TOLERANCE_NT:
        return ["steady-magnetic-emission-above-the-vehicle-limit"]
    return []


def assess_magnetic_emission(case):
    """Assess one vehicle steady magnetic emission case against clause 5.3.6."""
    if not isinstance(case, dict):
        raise ValueError("case must be a mapping")
    sources = case.get("sources")
    coverage = _numeric(
        "coverage_factor", case.get("coverage_factor", MOMENT_COVERAGE_FACTOR), 0.0
    )
    summed = vector_sum_moment(sources)
    summed_magnitude = moment_magnitude(summed)
    uncertainty = combined_uncertainty_am2(sources)
    analysis = analysis_worst_case_am2(sources, coverage)

    measured_input = case.get("measured_moment_am2")
    findings = list(check_evidence_coverage(case))
    findings.extend(check_budget_provenance(sources))
    if measured_input is None:
        measured = None
        governing = analysis
        findings.append("no-measured-system-moment-on-record")
    else:
        measured = measured_worst_case_am2(
            measured_input, case.get("measurement_uncertainty_am2", 0.0), coverage
        )
        findings.extend(reconcile_analysis_and_test(analysis, measured))
        governing = analysis if analysis >= measured else measured

    distance = case.get("evaluation_distance_m")
    angle = case.get("evaluation_angle_deg", 0.0)
    field = far_field_flux_density_nt(governing, distance, angle)
    limit = case.get("limit_nt")
    findings.extend(check_field_limit(field, limit))
    return {
        "summed_moment_am2": summed,
        "summed_magnitude_am2": summed_magnitude,
        "budget_uncertainty_am2": uncertainty,
        "analysis_worst_case_am2": analysis,
        "measured_worst_case_am2": measured,
        "governing_moment_am2": governing,
        "field_nt": field,
        "limit_nt": _numeric("limit_nt", limit),
        "findings": findings,
        "compliant": not findings,
    }
