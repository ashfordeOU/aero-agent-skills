"""Essential-telemetry acquisition assessment.

Anchor: ECSS-E-ST-50C clause 5.5.2 (essential telemetry -- the designated
minimum set that lets the ground establish spacecraft health and diagnose an
anomaly). Paraphrased into an implementable procedure; no standard text is
reproduced.

Procedure implemented here
--------------------------
1. Validate every candidate essential-telemetry parameter: health category,
   bits per sample, sample rate, the mission phases it is available in, and
   whether its acquisition depends on the nominal on-board processing chain.
2. Check that every mandated health category has at least one parameter
   behind it, and report the categories that do not.
3. Check that every parameter is available in every declared mission phase,
   safe and contingency modes included, and report the gaps per parameter.
4. Flag the parameters whose acquisition path depends on the nominal
   processing chain: a processor reset removes them exactly when they are
   needed.
5. Aggregate the encoded rate (bits per sample times sample rate, grossed up
   by the transport overhead factor) and compare it with the guaranteed
   emergency downlink capacity.
"""

import math

__all__ = [
    "RATE_TOLERANCE_BPS",
    "DEFAULT_HEALTH_CATEGORIES",
    "validate_parameter",
    "validate_parameter_set",
    "parameter_bit_rate_bps",
    "aggregate_bit_rate_bps",
    "uncovered_categories",
    "phase_gaps",
    "chain_dependent_parameters",
    "capacity_headroom_bps",
    "fits_capacity",
    "assess_essential_telemetry",
]

# The capacity comparison is a sum of products against a declared bound: an
# aggregate that is physically exactly the capacity can land a few ULPs on the
# wrong side. Absorb the representation error here instead of inflating the
# guaranteed capacity.
RATE_TOLERANCE_BPS = 1e-9

# Health categories a spacecraft-level essential set is expected to carry.
# Overridable per mission through the spec.
DEFAULT_HEALTH_CATEGORIES = (
    "power",
    "thermal",
    "attitude",
    "command-link",
    "on-board-computer",
)


def _require_text(value, label):
    """Return a non-empty stripped string or raise."""
    if not isinstance(value, str):
        raise ValueError("%s must be a string, got %r" % (label, value))
    text = value.strip()
    if not text:
        raise ValueError("%s must not be empty" % label)
    return text


def _require_positive(value, label):
    """Return a positive finite float or raise."""
    if not isinstance(value, (int, float)) or isinstance(value, bool):
        raise ValueError("%s must be a real number, got %r" % (label, value))
    number = float(value)
    if not math.isfinite(number):
        raise ValueError("%s must be finite" % label)
    if number <= 0.0:
        raise ValueError("%s must be positive, got %g" % (label, number))
    return number


def _require_phase_set(value, label):
    """Return a frozenset of declared phase names or raise."""
    if isinstance(value, str) or not isinstance(value, (list, tuple, set, frozenset)):
        raise ValueError("%s must be a sequence of phase names, got %r" % (label, value))
    phases = set()
    for item in value:
        phases.add(_require_text(item, "%s entry" % label))
    if not phases:
        raise ValueError("%s must name at least one mission phase" % label)
    return frozenset(phases)


def validate_parameter(param):
    """Return a normalised essential-telemetry parameter record."""
    if not isinstance(param, dict):
        raise ValueError("parameter must be a mapping, got %r" % (param,))
    for key in ("name", "category", "bits_per_sample", "sample_rate_hz", "phases"):
        if key not in param:
            raise ValueError("parameter missing required key '%s'" % key)
    bits = param["bits_per_sample"]
    if not isinstance(bits, int) or isinstance(bits, bool):
        raise ValueError("bits_per_sample must be an integer, got %r" % (bits,))
    if bits <= 0:
        raise ValueError("bits_per_sample must be positive, got %d" % bits)
    dependent = param.get("chain_dependent", False)
    if not isinstance(dependent, bool):
        raise ValueError("chain_dependent must be a boolean, got %r" % (dependent,))
    return {
        "name": _require_text(param["name"], "name"),
        "category": _require_text(param["category"], "category"),
        "bits_per_sample": bits,
        "sample_rate_hz": _require_positive(param["sample_rate_hz"], "sample_rate_hz"),
        "phases": _require_phase_set(param["phases"], "phases"),
        "chain_dependent": dependent,
    }


def validate_parameter_set(parameters):
    """Return the validated parameter list; names must be unique and non-empty."""
    if isinstance(parameters, dict) or not isinstance(parameters, (list, tuple)):
        raise ValueError("parameters must be a sequence of parameter mappings")
    if not parameters:
        raise ValueError("the essential-telemetry set must not be empty")
    records = [validate_parameter(item) for item in parameters]
    seen = set()
    for record in records:
        if record["name"] in seen:
            raise ValueError("duplicate parameter name '%s'" % record["name"])
        seen.add(record["name"])
    return records


def parameter_bit_rate_bps(param):
    """Return the encoded payload rate of one parameter in bit/s."""
    record = validate_parameter(param)
    return record["bits_per_sample"] * record["sample_rate_hz"]


def aggregate_bit_rate_bps(parameters, overhead_factor=1.0):
    """Return the overhead-grossed aggregate rate of the whole set in bit/s."""
    records = validate_parameter_set(parameters)
    factor = _require_positive(overhead_factor, "overhead_factor")
    if factor < 1.0:
        raise ValueError("overhead_factor must be at least 1.0, got %g" % factor)
    payload = 0.0
    for record in records:
        payload += record["bits_per_sample"] * record["sample_rate_hz"]
    return payload * factor


def uncovered_categories(parameters, required_categories=DEFAULT_HEALTH_CATEGORIES):
    """Return the mandated health categories with no parameter behind them."""
    records = validate_parameter_set(parameters)
    if isinstance(required_categories, str) or \
            not isinstance(required_categories, (list, tuple, set, frozenset)):
        raise ValueError("required_categories must be a sequence of category names")
    wanted = [_require_text(item, "required category") for item in required_categories]
    if not wanted:
        raise ValueError("required_categories must name at least one category")
    present = set(record["category"] for record in records)
    return [name for name in wanted if name not in present]


def phase_gaps(parameters, mission_phases):
    """Return {parameter name: sorted missing phases} for incomplete coverage."""
    records = validate_parameter_set(parameters)
    declared = _require_phase_set(mission_phases, "mission_phases")
    gaps = {}
    for record in records:
        missing = sorted(declared - record["phases"])
        if missing:
            gaps[record["name"]] = missing
    return gaps


def chain_dependent_parameters(parameters):
    """Return the names whose acquisition depends on the nominal processing chain."""
    records = validate_parameter_set(parameters)
    return [r["name"] for r in records if r["chain_dependent"]]


def capacity_headroom_bps(aggregate_bps, capacity_bps):
    """Return capacity minus aggregate, in bit/s (negative means an overrun)."""
    aggregate = _require_positive(aggregate_bps, "aggregate_bps")
    capacity = _require_positive(capacity_bps, "capacity_bps")
    return capacity - aggregate


def fits_capacity(aggregate_bps, capacity_bps):
    """Return True when the aggregate rate fits the guaranteed capacity."""
    headroom = capacity_headroom_bps(aggregate_bps, capacity_bps)
    if math.isclose(headroom, 0.0, rel_tol=0.0, abs_tol=RATE_TOLERANCE_BPS):
        return True
    return headroom > 0.0


def assess_essential_telemetry(spec):
    """Run the full clause 5.5.2 essential-telemetry assessment.

    spec keys: parameters, mission_phases, emergency_capacity_bps, optional
    overhead_factor and required_categories.
    """
    if not isinstance(spec, dict):
        raise ValueError("spec must be a mapping")
    for key in ("parameters", "mission_phases", "emergency_capacity_bps"):
        if key not in spec:
            raise ValueError("spec missing required key '%s'" % key)
    records = validate_parameter_set(spec["parameters"])
    categories = spec.get("required_categories", DEFAULT_HEALTH_CATEGORIES)
    overhead = spec.get("overhead_factor", 1.0)
    capacity = _require_positive(spec["emergency_capacity_bps"], "emergency_capacity_bps")

    missing_categories = uncovered_categories(records, categories)
    gaps = phase_gaps(records, spec["mission_phases"])
    dependent = chain_dependent_parameters(records)
    aggregate = aggregate_bit_rate_bps(records, overhead)
    headroom = capacity_headroom_bps(aggregate, capacity)
    within = fits_capacity(aggregate, capacity)

    findings = []
    for name in missing_categories:
        findings.append("health category '%s' has no essential-telemetry parameter" % name)
    for name in sorted(gaps):
        findings.append(
            "parameter '%s' is not acquirable in mission phase(s): %s"
            % (name, ", ".join(gaps[name]))
        )
    for name in dependent:
        findings.append(
            "parameter '%s' is acquired through the nominal processing chain; "
            "a processor reset silences it" % name
        )
    if not within:
        findings.append(
            "aggregate essential-telemetry rate %.6g bit/s exceeds the guaranteed "
            "emergency capacity %.6g bit/s" % (aggregate, capacity)
        )

    return {
        "parameter_rates_bps": dict(
            (r["name"], r["bits_per_sample"] * r["sample_rate_hz"]) for r in records
        ),
        "aggregate_bps": aggregate,
        "capacity_bps": capacity,
        "headroom_bps": headroom,
        "within_capacity": within,
        "uncovered_categories": missing_categories,
        "phase_gaps": gaps,
        "chain_dependent": dependent,
        "compliant": not findings,
        "findings": findings,
    }
