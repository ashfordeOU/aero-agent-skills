#!/usr/bin/env python3
"""Antenna characterisation parameter-set logic.

Anchor: ECSS-E-ST-20C clause 7.2.2.5 (list of parameters covered by an
antenna characterisation, from beam-coverage and directivity through to
boresight). Paraphrased into an implementable procedure; no standard text is
reproduced.

Offline, deterministic, Python standard library only.
"""

import math

# Relative tolerance used to absorb floating-point representation error when a
# value sits exactly on a specified bound. It never widens the engineering
# limit: it only prevents a few ULPs of a sum or a logarithm from turning a
# physically compliant value into a violation.
REL_TOL = 1e-9
ABS_TOL = 1e-12

# Beam solid-angle constant for the two-principal-plane directivity estimate
# (square degrees in a sphere, reduced by the usual aperture-efficiency-free
# beam-shape factor).
BEAM_SOLID_ANGLE_DEG2 = 41253.0

FAMILY_BEAM_COVERAGE = "beam-coverage"
FAMILY_DIRECTIVITY = "directivity-and-antenna-gain"
FAMILY_POLARISATION = "polarisation-purity"
FAMILY_BORESIGHT = "boresight-pointing"
FAMILY_PORT = "port-matching"

_PARAMETER_FAMILY = {
    "coverage-area": FAMILY_BEAM_COVERAGE,
    "edge-of-coverage-level": FAMILY_BEAM_COVERAGE,
    "half-power-beamwidth": FAMILY_BEAM_COVERAGE,
    "scan-range": FAMILY_BEAM_COVERAGE,
    "directivity": FAMILY_DIRECTIVITY,
    "peak-antenna-gain": FAMILY_DIRECTIVITY,
    "radiation-efficiency": FAMILY_DIRECTIVITY,
    "side-lobe-level": FAMILY_DIRECTIVITY,
    "axial-ratio": FAMILY_POLARISATION,
    "cross-polar-discrimination": FAMILY_POLARISATION,
    "polarisation-sense": FAMILY_POLARISATION,
    "boresight-direction": FAMILY_BORESIGHT,
    "boresight-pointing-error": FAMILY_BORESIGHT,
    "beam-pointing-stability": FAMILY_BORESIGHT,
    "input-vswr": FAMILY_PORT,
    "operating-bandwidth": FAMILY_PORT,
    "port-isolation": FAMILY_PORT,
}

_ALIASES = {
    "hpbw": "half-power-beamwidth",
    "beamwidth": "half-power-beamwidth",
    "half power beamwidth": "half-power-beamwidth",
    "eoc": "edge-of-coverage-level",
    "edge-of-coverage": "edge-of-coverage-level",
    "gain": "peak-antenna-gain",
    "peak-gain": "peak-antenna-gain",
    "antenna-gain": "peak-antenna-gain",
    "efficiency": "radiation-efficiency",
    "sll": "side-lobe-level",
    "sidelobe-level": "side-lobe-level",
    "ar": "axial-ratio",
    "xpd": "cross-polar-discrimination",
    "cross-polarisation-discrimination": "cross-polar-discrimination",
    "polarisation": "polarisation-sense",
    "boresight": "boresight-direction",
    "pointing-error": "boresight-pointing-error",
    "vswr": "input-vswr",
    "isolation": "port-isolation",
    "bandwidth": "operating-bandwidth",
}

# Direction of the specified bound for each canonical numeric parameter.
# "max" - the declared value must not exceed the bound.
# "min" - the declared value must not fall below the bound.
_BOUND_DIRECTION = {
    "edge-of-coverage-level": "min",
    "half-power-beamwidth": "min",
    "scan-range": "min",
    "directivity": "min",
    "peak-antenna-gain": "min",
    "radiation-efficiency": "min",
    "side-lobe-level": "max",
    "axial-ratio": "max",
    "cross-polar-discrimination": "min",
    "boresight-pointing-error": "max",
    "beam-pointing-stability": "max",
    "input-vswr": "max",
    "operating-bandwidth": "min",
    "port-isolation": "min",
}

_FUNCTION_REQUIREMENTS = {
    "telecommand-reception": (
        "coverage-area",
        "edge-of-coverage-level",
        "axial-ratio",
        "input-vswr",
        "operating-bandwidth",
    ),
    "telemetry-transmission": (
        "coverage-area",
        "edge-of-coverage-level",
        "peak-antenna-gain",
        "axial-ratio",
        "input-vswr",
        "operating-bandwidth",
    ),
    "payload-downlink": (
        "half-power-beamwidth",
        "peak-antenna-gain",
        "radiation-efficiency",
        "side-lobe-level",
        "boresight-direction",
        "boresight-pointing-error",
        "input-vswr",
        "operating-bandwidth",
    ),
    "navigation-signal": (
        "coverage-area",
        "edge-of-coverage-level",
        "peak-antenna-gain",
        "axial-ratio",
        "cross-polar-discrimination",
        "polarisation-sense",
        "boresight-direction",
        "boresight-pointing-error",
        "operating-bandwidth",
    ),
    "inter-satellite-link": (
        "half-power-beamwidth",
        "peak-antenna-gain",
        "side-lobe-level",
        "scan-range",
        "boresight-pointing-error",
        "beam-pointing-stability",
        "input-vswr",
        "port-isolation",
    ),
}


def _require_number(value, label):
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise ValueError("%s must be a real number, got %r" % (label, value))
    value = float(value)
    if math.isnan(value) or math.isinf(value):
        raise ValueError("%s must be finite, got %r" % (label, value))
    return value


def normalise_parameter(name):
    """Return the canonical parameter name for a declared entry.

    Resolves the common abbreviations. Raises ValueError for an entry that is
    not a recognised antenna-characterisation parameter, so an unknown token
    never reaches the completeness or compliance steps.
    """
    if not isinstance(name, str):
        raise ValueError("parameter name must be a string, got %r" % (name,))
    token = name.strip().lower().replace("_", "-")
    token = "-".join(part for part in token.split() if part) if " " in token else token
    if not token:
        raise ValueError("parameter name must not be empty")
    if token in _PARAMETER_FAMILY:
        return token
    if token in _ALIASES:
        return _ALIASES[token]
    raise ValueError("unrecognised antenna-characterisation parameter %r" % (name,))


def parameter_family(name):
    """Return the family of a declared parameter (clause 7.2.2.5 grouping)."""
    return _PARAMETER_FAMILY[normalise_parameter(name)]


def required_parameters(antenna_function):
    """Return the mandatory parameter-set for an antenna-function."""
    if not isinstance(antenna_function, str):
        raise ValueError("antenna_function must be a string, got %r" % (antenna_function,))
    key = antenna_function.strip().lower().replace("_", "-")
    if key not in _FUNCTION_REQUIREMENTS:
        raise ValueError(
            "unknown antenna-function %r; known: %s"
            % (antenna_function, ", ".join(sorted(_FUNCTION_REQUIREMENTS)))
        )
    return tuple(_FUNCTION_REQUIREMENTS[key])


def check_parameter_set(declared, antenna_function):
    """Difference the declared parameter names against the mandatory set.

    Returns a report with the normalised declared names, the missing mandatory
    names, the families covered and a completeness verdict.
    """
    if not isinstance(declared, (list, tuple, set, frozenset)):
        raise ValueError("declared must be a sequence of parameter names")
    normalised = sorted({normalise_parameter(item) for item in declared})
    if not normalised:
        raise ValueError("declared parameter-set must not be empty")
    mandatory = required_parameters(antenna_function)
    missing = sorted(set(mandatory) - set(normalised))
    families = sorted({_PARAMETER_FAMILY[item] for item in normalised})
    required_families = sorted({_PARAMETER_FAMILY[item] for item in mandatory})
    uncovered = sorted(set(required_families) - set(families))
    return {
        "antenna-function": antenna_function.strip().lower().replace("_", "-"),
        "declared": normalised,
        "mandatory": sorted(mandatory),
        "missing": missing,
        "families-covered": families,
        "families-uncovered": uncovered,
        "complete": not missing,
    }


def directivity_dbi_from_beamwidths(hpbw_az_deg, hpbw_el_deg):
    """Directivity in dBi from the two principal half-power-beamwidths."""
    az = _require_number(hpbw_az_deg, "hpbw_az_deg")
    el = _require_number(hpbw_el_deg, "hpbw_el_deg")
    for label, value in (("hpbw_az_deg", az), ("hpbw_el_deg", el)):
        if value <= 0.0:
            raise ValueError("%s must be positive, got %r" % (label, value))
        if value >= 360.0:
            raise ValueError("%s must be below 360 deg, got %r" % (label, value))
    return 10.0 * math.log10(BEAM_SOLID_ANGLE_DEG2 / (az * el))


def antenna_gain_dbi(directivity_dbi, radiation_efficiency):
    """Peak-antenna-gain in dBi: directivity reduced by radiation-efficiency."""
    directivity = _require_number(directivity_dbi, "directivity_dbi")
    eta = _require_number(radiation_efficiency, "radiation_efficiency")
    if not 0.0 < eta <= 1.0:
        raise ValueError("radiation_efficiency must lie in (0, 1], got %r" % (eta,))
    return directivity + 10.0 * math.log10(eta)


def cross_polar_discrimination_db(axial_ratio_db):
    """Cross-polar-discrimination in dB derived from an axial-ratio in dB.

    A zero axial-ratio is ideal circular polarisation and yields an unbounded
    discrimination, reported as positive infinity.
    """
    ar_db = _require_number(axial_ratio_db, "axial_ratio_db")
    if ar_db < 0.0:
        raise ValueError("axial_ratio_db must not be negative, got %r" % (ar_db,))
    if ar_db == 0.0:
        return float("inf")
    ar_linear = 10.0 ** (ar_db / 20.0)
    return 20.0 * math.log10((ar_linear + 1.0) / (ar_linear - 1.0))


def boresight_pointing_error_budget(contributors, allowable_deg):
    """Root-sum-square the boresight-pointing-error contributors.

    contributors: mapping of contributor name -> magnitude in degrees.
    Returns the total, the remaining allowance and a compliance verdict that
    treats a total equal to the allowable, to within representation error, as
    compliant.
    """
    if not isinstance(contributors, dict) or not contributors:
        raise ValueError("contributors must be a non-empty mapping")
    allowable = _require_number(allowable_deg, "allowable_deg")
    if allowable <= 0.0:
        raise ValueError("allowable_deg must be positive, got %r" % (allowable,))
    total_sq = 0.0
    for label, magnitude in contributors.items():
        value = _require_number(magnitude, "contributor %r" % (label,))
        if value < 0.0:
            raise ValueError("contributor %r must not be negative" % (label,))
        total_sq += value * value
    total = math.sqrt(total_sq)
    compliant = total <= allowable or math.isclose(
        total, allowable, rel_tol=REL_TOL, abs_tol=ABS_TOL
    )
    return {
        "contributors": dict(sorted(contributors.items())),
        "total-deg": total,
        "allowable-deg": allowable,
        "remaining-deg": allowable - total,
        "compliant": compliant,
    }


def evaluate_parameter_record(record):
    """Judge one declared parameter value against its specified bound.

    record: mapping with "name", "value" and "bound"; the bound direction is
    taken from the canonical table unless the record overrides "direction".
    """
    if not isinstance(record, dict):
        raise ValueError("record must be a mapping, got %r" % (record,))
    name = normalise_parameter(record.get("name"))
    if name not in _BOUND_DIRECTION:
        raise ValueError("parameter %r carries no numeric bound" % (name,))
    value = _require_number(record.get("value"), "value of %r" % (name,))
    bound = _require_number(record.get("bound"), "bound of %r" % (name,))
    direction = record.get("direction", _BOUND_DIRECTION[name])
    if direction not in ("min", "max"):
        raise ValueError("direction must be 'min' or 'max', got %r" % (direction,))
    on_bound = math.isclose(value, bound, rel_tol=REL_TOL, abs_tol=ABS_TOL)
    if direction == "max":
        compliant = value <= bound or on_bound
        margin = bound - value
    else:
        compliant = value >= bound or on_bound
        margin = value - bound
    return {
        "name": name,
        "family": _PARAMETER_FAMILY[name],
        "value": value,
        "bound": bound,
        "direction": direction,
        "margin": margin,
        "compliant": compliant,
    }


def check_derived_consistency(declared_value, derived_value, tolerance_db):
    """Compare a declared quantity with the value derived from its siblings."""
    declared = _require_number(declared_value, "declared_value")
    derived = _require_number(derived_value, "derived_value")
    tol = _require_number(tolerance_db, "tolerance_db")
    if tol < 0.0:
        raise ValueError("tolerance_db must not be negative, got %r" % (tol,))
    delta = abs(declared - derived)
    consistent = delta <= tol or math.isclose(delta, tol, rel_tol=REL_TOL, abs_tol=ABS_TOL)
    return {
        "declared": declared,
        "derived": derived,
        "delta": delta,
        "tolerance": tol,
        "consistent": consistent,
    }


def assess_parameter_set(antenna_function, records, pointing_budget=None):
    """Full clause 7.2.2.5 assessment for one antenna.

    records: sequence of parameter records as accepted by
    evaluate_parameter_record, plus any non-numeric declared names supplied as
    plain strings.
    """
    if not isinstance(records, (list, tuple)):
        raise ValueError("records must be a sequence")
    if not records:
        raise ValueError("records must not be empty")
    declared_names = []
    evaluations = []
    for item in records:
        if isinstance(item, str):
            declared_names.append(normalise_parameter(item))
            continue
        evaluation = evaluate_parameter_record(item)
        declared_names.append(evaluation["name"])
        evaluations.append(evaluation)
    coverage = check_parameter_set(declared_names, antenna_function)
    findings = []
    for name in coverage["missing"]:
        findings.append("missing mandatory parameter: %s" % name)
    for evaluation in evaluations:
        if not evaluation["compliant"]:
            findings.append(
                "%s violates its %s bound (value %.6g, bound %.6g)"
                % (evaluation["name"], evaluation["direction"], evaluation["value"],
                   evaluation["bound"])
            )
    budget = None
    if pointing_budget is not None:
        if not isinstance(pointing_budget, dict):
            raise ValueError("pointing_budget must be a mapping")
        budget = boresight_pointing_error_budget(
            pointing_budget.get("contributors"), pointing_budget.get("allowable_deg")
        )
        if not budget["compliant"]:
            findings.append(
                "boresight-pointing-error budget exceeds the allowable "
                "(total %.6g deg, allowable %.6g deg)"
                % (budget["total-deg"], budget["allowable-deg"])
            )
    return {
        "coverage": coverage,
        "evaluations": evaluations,
        "pointing-budget": budget,
        "findings": findings,
        "compliant": not findings,
    }
