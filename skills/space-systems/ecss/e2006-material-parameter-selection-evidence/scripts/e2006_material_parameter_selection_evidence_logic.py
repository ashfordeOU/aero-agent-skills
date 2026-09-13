#!/usr/bin/env python3
"""Material parameter evidence for spacecraft-charging decisions --
ECSS-E-ST-20-06C clause 6.8.2 (paraphrased procedure).

Offline, deterministic, stdlib only. The clause requires the electrical
material properties that drive a charging decision to rest on measured data,
either declared by the material maker or obtained during the material
selection campaign. This module grades a parameter dossier: provenance,
physical admissibility, unit agreement, coverage of the mission environment,
and whether the decay behaviour of the material makes generic reference data
inadmissible.
"""

import math

REL_TOL = 1e-9
ABS_TOL = 1e-12

VACUUM_PERMITTIVITY_F_PER_M = 8.8541878128e-12

# Canonical parameter -> (unit, physically admissible lower, upper).
PARAMETER_SPECS = {
    "bulk-resistivity": ("ohm-m", 1.0e-8, 1.0e22),
    "surface-resistivity": ("ohm-per-square", 1.0e-3, 1.0e22),
    "relative-permittivity": ("dimensionless", 1.0, 1.0e3),
    "secondary-emission-yield-peak": ("dimensionless", 0.05, 1.0e2),
    "photoemission-yield": ("ampere-per-square-metre", 1.0e-9, 1.0e-3),
    "dielectric-thickness": ("metre", 1.0e-9, 1.0e-1),
}

PARAMETER_ALIASES = {
    "bulk-resistivity": "bulk-resistivity",
    "volume-resistivity": "bulk-resistivity",
    "surface-resistivity": "surface-resistivity",
    "sheet-resistivity": "surface-resistivity",
    "relative-permittivity": "relative-permittivity",
    "dielectric-constant": "relative-permittivity",
    "secondary-emission-yield-peak": "secondary-emission-yield-peak",
    "peak-secondary-yield": "secondary-emission-yield-peak",
    "photoemission-yield": "photoemission-yield",
    "photoelectron-yield": "photoemission-yield",
    "dielectric-thickness": "dielectric-thickness",
    "layer-thickness": "dielectric-thickness",
}

# Provenance categories, strongest first.
SOURCE_ALIASES = {
    "selection-campaign-measurement": "selection-measured",
    "selection-measurement": "selection-measured",
    "sample-measurement": "selection-measured",
    "maker-measured-datasheet": "maker-declared",
    "manufacturer-datasheet": "maker-declared",
    "supplier-declared-measurement": "maker-declared",
    "handbook-generic-value": "generic-reference",
    "textbook-value": "generic-reference",
    "engineering-estimate": "unsubstantiated",
    "analogy-from-similar-material": "unsubstantiated",
}

SOURCE_RANK = {
    "selection-measured": 3,
    "maker-declared": 2,
    "generic-reference": 1,
    "unsubstantiated": 0,
}

# Parameters a material must carry, by the role it plays in the charging
# assessment.
ROLE_REQUIREMENTS = {
    "exposed-dielectric-surface": (
        "bulk-resistivity",
        "surface-resistivity",
        "relative-permittivity",
        "secondary-emission-yield-peak",
        "photoemission-yield",
        "dielectric-thickness",
    ),
    "conductive-external-coating": (
        "surface-resistivity",
        "secondary-emission-yield-peak",
        "photoemission-yield",
    ),
    "internal-dielectric": (
        "bulk-resistivity",
        "relative-permittivity",
        "dielectric-thickness",
    ),
}

# A material whose charge-decay constant is a significant fraction of the
# charging timescale drives the result; generic reference data is then
# inadmissible and a selection-campaign measurement is demanded.
DECAY_DRIVING_FRACTION = 0.1


def _le(value, bound):
    return value <= bound or math.isclose(value, bound, rel_tol=REL_TOL, abs_tol=ABS_TOL)


def _ge(value, bound):
    return value >= bound or math.isclose(value, bound, rel_tol=REL_TOL, abs_tol=ABS_TOL)


def _finite_number(label, value):
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise ValueError("%s must be numeric, got %r" % (label, value))
    value = float(value)
    if not math.isfinite(value):
        raise ValueError("%s must be finite" % label)
    return value


def normalize_parameter(name):
    """Map a dossier parameter name onto its canonical key."""
    if not isinstance(name, str):
        raise ValueError("parameter name must be a string, got %r" % (name,))
    key = name.strip().lower().replace("_", "-")
    if not key:
        raise ValueError("parameter name must not be blank")
    if key not in PARAMETER_ALIASES:
        raise ValueError("unrecognized material parameter %r" % (name,))
    return PARAMETER_ALIASES[key]


def parameter_spec(name):
    """Return {unit, lower, upper} for a parameter, canonical or aliased."""
    canonical = normalize_parameter(name)
    unit, lower, upper = PARAMETER_SPECS[canonical]
    return {"parameter": canonical, "unit": unit, "lower": lower, "upper": upper}


def categorize_evidence_source(source):
    """Map a provenance string onto a provenance category.

    An uncategorized provenance is rejected rather than demoted, so an
    unfamiliar dossier wording never silently counts as measured data.
    """
    if not isinstance(source, str):
        raise ValueError("evidence source must be a string, got %r" % (source,))
    key = source.strip().lower().replace("_", "-")
    if not key:
        raise ValueError("evidence source must not be blank")
    if key in SOURCE_ALIASES:
        return SOURCE_ALIASES[key]
    if key in SOURCE_RANK:
        return key
    raise ValueError("unrecognized evidence source %r" % (source,))


def charge_decay_time_constant(bulk_resistivity_ohm_m, relative_permittivity):
    """Dielectric relaxation constant tau = eps0 * eps_r * rho, in seconds."""
    rho = _finite_number("bulk_resistivity_ohm_m", bulk_resistivity_ohm_m)
    eps_r = _finite_number("relative_permittivity", relative_permittivity)
    if rho <= 0.0:
        raise ValueError("bulk_resistivity_ohm_m must be positive")
    if eps_r < 1.0:
        raise ValueError("relative_permittivity must be at least 1.0")
    return VACUUM_PERMITTIVITY_F_PER_M * eps_r * rho


def required_provenance(tau_seconds, charging_timescale_s):
    """Decide the weakest provenance admissible for the driving parameters.

    When the relaxation constant reaches a tenth of the charging timescale the
    material holds charge across the event and its resistivity drives the
    answer: only a selection-campaign measurement is admissible. Otherwise a
    maker-declared measurement suffices.
    """
    tau = _finite_number("tau_seconds", tau_seconds)
    timescale = _finite_number("charging_timescale_s", charging_timescale_s)
    if tau < 0.0:
        raise ValueError("tau_seconds must not be negative")
    if timescale <= 0.0:
        raise ValueError("charging_timescale_s must be positive")
    if _ge(tau, DECAY_DRIVING_FRACTION * timescale):
        return "selection-measured"
    return "maker-declared"


def validate_parameter_record(record):
    """Validate one parameter record and return its graded form.

    Raises ValueError on a structurally unusable record: not a mapping,
    unknown parameter, non-numeric or non-finite value, value outside the
    physically admissible range, or a unit that disagrees with the parameter.
    Weak provenance and missing measurement conditions are findings, not
    exceptions -- they are the output of the assessment.
    """
    if not isinstance(record, dict):
        raise ValueError("parameter record must be a mapping, got %r" % (type(record).__name__,))
    spec = parameter_spec(record.get("parameter"))
    value = _finite_number("value", record.get("value"))
    if not (_ge(value, spec["lower"]) and _le(value, spec["upper"])):
        raise ValueError(
            "%s value %.6g outside the admissible %.6g..%.6g %s"
            % (spec["parameter"], value, spec["lower"], spec["upper"], spec["unit"])
        )
    unit = record.get("unit")
    if unit is not None and unit != spec["unit"]:
        raise ValueError(
            "%s reported in %r but the assessment works in %r"
            % (spec["parameter"], unit, spec["unit"])
        )
    provenance = categorize_evidence_source(record.get("source"))
    findings = []
    if provenance == "unsubstantiated":
        findings.append("%s rests on an unsubstantiated value, not measured data" % spec["parameter"])
    elif provenance == "generic-reference":
        findings.append("%s rests on generic reference data rather than a measurement" % spec["parameter"])
    method = record.get("method")
    if provenance in ("maker-declared", "selection-measured"):
        if not isinstance(method, str) or not method.strip():
            findings.append("%s measurement states no method" % spec["parameter"])
    return {
        "parameter": spec["parameter"],
        "value": value,
        "unit": spec["unit"],
        "provenance": provenance,
        "rank": SOURCE_RANK[provenance],
        "findings": findings,
        "acceptable": SOURCE_RANK[provenance] >= SOURCE_RANK["maker-declared"] and not findings,
    }


def environment_coverage(measured_range_c, mission_range_c):
    """Check that the measurement conditions span the mission temperatures.

    Both arguments are (low, high) in degrees Celsius. Raises ValueError on a
    malformed or inverted range.
    """
    ranges = {}
    for label, pair in (("measured_range_c", measured_range_c), ("mission_range_c", mission_range_c)):
        if not isinstance(pair, (list, tuple)) or len(pair) != 2:
            raise ValueError("%s must be a (low, high) pair" % label)
        low = _finite_number(label + " low", pair[0])
        high = _finite_number(label + " high", pair[1])
        if low > high:
            raise ValueError("%s is inverted (%g > %g)" % (label, low, high))
        ranges[label] = (low, high)
    m_low, m_high = ranges["measured_range_c"]
    s_low, s_high = ranges["mission_range_c"]
    findings = []
    if not _le(m_low, s_low):
        findings.append("measurement stops at %g C, mission reaches %g C on the cold side" % (m_low, s_low))
    if not _ge(m_high, s_high):
        findings.append("measurement stops at %g C, mission reaches %g C on the hot side" % (m_high, s_high))
    return {"covered": not findings, "findings": findings}


def required_parameters_for_role(role):
    """Parameters a material in this role must carry, as a tuple."""
    if not isinstance(role, str):
        raise ValueError("role must be a string, got %r" % (role,))
    key = role.strip().lower().replace("_", "-")
    if key not in ROLE_REQUIREMENTS:
        raise ValueError("unrecognized material role %r" % (role,))
    return ROLE_REQUIREMENTS[key]


def assess_material_evidence(material):
    """Grade one material's parameter dossier against clause 6.8.2.

    material keys: id, role, records (list), mission_range_c,
    charging_timescale_s (optional, default one substorm timescale).
    """
    if not isinstance(material, dict):
        raise ValueError("material must be a mapping, got %r" % (type(material).__name__,))
    ident = material.get("id")
    if not isinstance(ident, str) or not ident.strip():
        raise ValueError("material needs a non-blank string id")
    required = required_parameters_for_role(material.get("role"))
    raw_records = material.get("records")
    if not isinstance(raw_records, (list, tuple)) or not raw_records:
        raise ValueError("material %s carries no parameter records" % ident)
    graded = {}
    findings = []
    for raw in raw_records:
        entry = validate_parameter_record(raw)
        if entry["parameter"] in graded:
            raise ValueError("duplicate record for %s on material %s" % (entry["parameter"], ident))
        graded[entry["parameter"]] = entry
        findings.extend(entry["findings"])
    missing = [p for p in required if p not in graded]
    for parameter in missing:
        findings.append("%s required for this role and absent from the dossier" % parameter)
    coverage = environment_coverage(
        material.get("measured_range_c", (-273.0, 1000.0)),
        material.get("mission_range_c", (-100.0, 60.0)),
    )
    findings.extend(coverage["findings"])
    tau = None
    if "bulk-resistivity" in graded and "relative-permittivity" in graded:
        tau = charge_decay_time_constant(
            graded["bulk-resistivity"]["value"], graded["relative-permittivity"]["value"]
        )
        needed = required_provenance(tau, material.get("charging_timescale_s", 1.0e3))
        if SOURCE_RANK[graded["bulk-resistivity"]["provenance"]] < SOURCE_RANK[needed]:
            findings.append(
                "bulk-resistivity drives the decay behaviour (tau %.3g s) and needs %s provenance"
                % (tau, needed)
            )
    return {
        "id": ident,
        "role": material.get("role"),
        "parameters": sorted(graded),
        "missing": missing,
        "decay_time_constant_s": tau,
        "weakest_rank": min(e["rank"] for e in graded.values()),
        "status": "evidence-sufficient" if not findings else "evidence-insufficient",
        "findings": findings,
    }


def summarize_material_set(materials):
    """Roll per-material verdicts into a selection-campaign statement."""
    if not isinstance(materials, (list, tuple)) or not materials:
        raise ValueError("materials must be a non-empty list")
    results = [assess_material_evidence(m) for m in materials]
    insufficient = [r["id"] for r in results if r["status"] == "evidence-insufficient"]
    return {
        "materials": results,
        "sufficient_count": len(results) - len(insufficient),
        "insufficient_ids": insufficient,
        "campaign_closed": not insufficient,
    }
