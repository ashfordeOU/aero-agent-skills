#!/usr/bin/env python3
"""Floating conductive part exceptions (ECSS-E-ST-20-06C clause 6.3.2).

Paraphrased, implementable procedure -- no standard text is reproduced.

A conductive part that is not tied to the structural reference may be left
that way only while it stays small in three independent senses:

    exposed area          A     <= A_max
    capacitance           C     <= C_max
    stored energy    0.5*C*V^2  <= E_max

where V is the potential the part actually floats to -- the environment
value, or the lower value a leakage path to the structural reference
clamps it to. All three criteria are evaluated and every failure is
reported, because the failing set is what tells a designer whether to
shrink the part, thicken its standoff, or add a bleed path.

Stdlib only, offline, deterministic.
"""

import math

__all__ = [
    "REL_TOL",
    "VACUUM_PERMITTIVITY",
    "DEFAULT_EXCEPTION_LIMITS",
    "ENERGY_BAND_UPSET_J",
    "ENERGY_BAND_DAMAGE_J",
    "default_exception_limits",
    "resolve_exception_limits",
    "parallel_plate_capacitance",
    "isolated_body_capacitance",
    "resolve_capacitance",
    "leakage_clamped_potential",
    "bounding_floating_potential",
    "stored_energy",
    "peak_discharge_current",
    "categorize_energy_band",
    "within_limit",
    "evaluate_floating_part",
    "assess_floating_inventory",
]

# Relative tolerance applied when a computed quantity meets a limit exactly.
# Quantities such as 0.5 * C * V^2 are products of powers of ten and can land
# a few ULPs above the algebraic value; the tolerance absorbs that
# representation error. The project limit itself is never raised.
REL_TOL = 1e-9

VACUUM_PERMITTIVITY = 8.8541878128e-12  # F/m

# Project exception limits. Overridable per programme via
# resolve_exception_limits(); these are the defaults the leaf assumes.
DEFAULT_EXCEPTION_LIMITS = {
    "max_exposed_area_m2": 1.0e-4,
    "max_capacitance_f": 1.0e-10,
    "max_stored_energy_j": 1.0e-6,
}

# Energy bands used to prioritise a refused part (engineering aid only).
ENERGY_BAND_UPSET_J = 1.0e-6
ENERGY_BAND_DAMAGE_J = 1.0e-3

_REQUIRED_PART_KEYS = ("id", "exposed_area_m2")
_CAPACITANCE_FORMS = (
    "capacitance_f",
    "standoff_gap_m",
    "equivalent_radius_m",
)
_KNOWN_PART_KEYS = set(_REQUIRED_PART_KEYS) | set(_CAPACITANCE_FORMS) | {
    "relative_permittivity",
    "leakage_resistance_ohm",
    "discharge_rise_time_s",
}


def _as_float(name, value):
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise ValueError("%s must be a real number, got %r" % (name, value))
    out = float(value)
    if not math.isfinite(out):
        raise ValueError("%s must be finite, got %r" % (name, value))
    return out


def _require_positive(name, value):
    out = _as_float(name, value)
    if out <= 0.0:
        raise ValueError("%s must be > 0, got %r" % (name, value))
    return out


def _require_non_negative(name, value):
    out = _as_float(name, value)
    if out < 0.0:
        raise ValueError("%s must be >= 0, got %r" % (name, value))
    return out


def default_exception_limits():
    """Fresh copy of the default clause 6.3.2 exception limits."""
    return dict(DEFAULT_EXCEPTION_LIMITS)


def resolve_exception_limits(overrides=None):
    """Merge programme overrides onto the default exception limits."""
    limits = default_exception_limits()
    if overrides is None:
        return limits
    if not isinstance(overrides, dict):
        raise ValueError("overrides must be a mapping")
    unknown = sorted(set(overrides) - set(limits))
    if unknown:
        raise ValueError("unknown exception limit(s): %s" % ", ".join(unknown))
    for key, value in overrides.items():
        limits[key] = _require_positive(key, value)
    return limits


def parallel_plate_capacitance(area_m2, gap_m, relative_permittivity=1.0):
    """Capacitance (F) of a plate-like part standing off the structure."""
    area = _require_positive("area_m2", area_m2)
    gap = _require_positive("gap_m", gap_m)
    eps_r = _require_positive("relative_permittivity", relative_permittivity)
    if eps_r < 1.0:
        raise ValueError("relative_permittivity must be >= 1.0, got %r" % (relative_permittivity,))
    return VACUUM_PERMITTIVITY * eps_r * area / gap


def isolated_body_capacitance(equivalent_radius_m):
    """Self-capacitance (F) of a compact isolated body: 4 pi eps0 r."""
    radius = _require_positive("equivalent_radius_m", equivalent_radius_m)
    return 4.0 * math.pi * VACUUM_PERMITTIVITY * radius


def resolve_capacitance(part):
    """Capacitance (F) to the structural reference from one declared form.

    Exactly one of capacitance_f, standoff_gap_m or equivalent_radius_m must
    be present. Zero forms leaves the criterion unevaluated (a finding);
    two forms invite a silent contradiction.
    """
    if not isinstance(part, dict):
        raise ValueError("part must be a mapping")
    declared = [form for form in _CAPACITANCE_FORMS if part.get(form) is not None]
    if not declared:
        raise ValueError(
            "part declares no capacitance form; expected one of %s"
            % ", ".join(_CAPACITANCE_FORMS)
        )
    if len(declared) > 1:
        raise ValueError(
            "part declares %d capacitance forms (%s); exactly one is allowed"
            % (len(declared), ", ".join(declared))
        )
    form = declared[0]
    if form == "capacitance_f":
        return _require_positive("capacitance_f", part["capacitance_f"])
    if form == "equivalent_radius_m":
        if part.get("relative_permittivity") is not None:
            raise ValueError(
                "relative_permittivity applies to a standoff gap, not an equivalent radius"
            )
        return isolated_body_capacitance(part["equivalent_radius_m"])
    return parallel_plate_capacitance(
        part.get("exposed_area_m2"),
        part["standoff_gap_m"],
        relative_permittivity=part.get("relative_permittivity", 1.0),
    )


def leakage_clamped_potential(current_density_a_m2, exposed_area_m2, leakage_resistance_ohm):
    """Potential (V) a leakage path to the structural reference clamps to."""
    j = _require_non_negative("current_density_a_m2", current_density_a_m2)
    area = _require_positive("exposed_area_m2", exposed_area_m2)
    resistance = _require_positive("leakage_resistance_ohm", leakage_resistance_ohm)
    return j * area * resistance


def bounding_floating_potential(
    environment_potential_v,
    current_density_a_m2=0.0,
    exposed_area_m2=None,
    leakage_resistance_ohm=None,
):
    """Potential (V) the part actually floats to.

    The environment value, or the lower clamped value when a designed
    leakage path to the structural reference exists.
    """
    environment = _require_positive("environment_potential_v", abs(environment_potential_v))
    if leakage_resistance_ohm is None:
        return environment
    if exposed_area_m2 is None:
        raise ValueError("a leakage path needs exposed_area_m2 to compute the collected current")
    clamped = leakage_clamped_potential(
        current_density_a_m2, exposed_area_m2, leakage_resistance_ohm
    )
    return min(environment, clamped)


def stored_energy(capacitance_f, potential_v):
    """Electrostatic energy (J) stored on the floating part: 0.5 C V^2."""
    capacitance = _require_positive("capacitance_f", capacitance_f)
    potential = _as_float("potential_v", potential_v)
    return 0.5 * capacitance * potential * potential


def peak_discharge_current(capacitance_f, potential_v, rise_time_s):
    """Peak current (A) the stored charge delivers over a rise time: C V / t."""
    capacitance = _require_positive("capacitance_f", capacitance_f)
    potential = abs(_as_float("potential_v", potential_v))
    rise = _require_positive("rise_time_s", rise_time_s)
    return capacitance * potential / rise


def categorize_energy_band(energy_j):
    """Prioritisation band for a stored energy (engineering aid, not a verdict)."""
    energy = _require_non_negative("energy_j", energy_j)
    if energy < ENERGY_BAND_UPSET_J:
        return "benign"
    if energy < ENERGY_BAND_DAMAGE_J:
        return "upset-credible"
    return "damage-credible"


def within_limit(value, limit):
    """True when value <= limit, absorbing float representation error."""
    v = _require_non_negative("value", value)
    lim = _require_positive("limit", limit)
    if v <= lim:
        return True
    return math.isclose(v, lim, rel_tol=REL_TOL, abs_tol=0.0)


def evaluate_floating_part(
    part,
    environment_potential_v,
    current_density_a_m2=0.0,
    limits=None,
    default_rise_time_s=1.0e-8,
):
    """Decide the clause 6.3.2 exception for one isolated conductive part."""
    if not isinstance(part, dict):
        raise ValueError("part must be a mapping, got %r" % (type(part).__name__,))
    unknown = sorted(set(part) - _KNOWN_PART_KEYS)
    if unknown:
        raise ValueError("part has unknown keys: %s" % ", ".join(unknown))
    for key in _REQUIRED_PART_KEYS:
        if key not in part:
            raise ValueError("part is missing required key '%s'" % key)
    part_id = part["id"]
    if not isinstance(part_id, str) or not part_id.strip():
        raise ValueError("part id must be a non-empty string, got %r" % (part_id,))

    resolved_limits = resolve_exception_limits(limits)
    area = _require_positive("exposed_area_m2", part["exposed_area_m2"])
    capacitance = resolve_capacitance(part)
    potential = bounding_floating_potential(
        environment_potential_v,
        current_density_a_m2=current_density_a_m2,
        exposed_area_m2=area,
        leakage_resistance_ohm=part.get("leakage_resistance_ohm"),
    )
    energy = stored_energy(capacitance, potential)
    rise_time = part.get("discharge_rise_time_s", default_rise_time_s)
    current = peak_discharge_current(capacitance, potential, rise_time)

    criteria = {
        "exposed-area": within_limit(area, resolved_limits["max_exposed_area_m2"]),
        "capacitance": within_limit(capacitance, resolved_limits["max_capacitance_f"]),
        "stored-energy": within_limit(energy, resolved_limits["max_stored_energy_j"]),
    }
    failed = sorted(name for name, ok in criteria.items() if not ok)
    return {
        "id": part_id,
        "exposed_area_m2": area,
        "capacitance_f": capacitance,
        "floating_potential_v": potential,
        "stored_energy_j": energy,
        "peak_discharge_current_a": current,
        "energy_band": categorize_energy_band(energy),
        "criteria": criteria,
        "failed_criteria": failed,
        "clamped_by_leakage_path": part.get("leakage_resistance_ohm") is not None,
        "disposition": "exception-granted" if not failed else "grounding-required",
    }


def assess_floating_inventory(
    parts,
    environment_potential_v,
    current_density_a_m2=0.0,
    limits=None,
    default_rise_time_s=1.0e-8,
):
    """Aggregate clause 6.3.2 decisions over an inventory of floating parts."""
    if not isinstance(parts, (list, tuple)):
        raise ValueError("parts must be a list or tuple")
    if not parts:
        raise ValueError("parts must not be empty")
    evaluations = []
    seen = set()
    for part in parts:
        evaluation = evaluate_floating_part(
            part,
            environment_potential_v,
            current_density_a_m2=current_density_a_m2,
            limits=limits,
            default_rise_time_s=default_rise_time_s,
        )
        if evaluation["id"] in seen:
            raise ValueError("duplicate part id '%s'" % evaluation["id"])
        seen.add(evaluation["id"])
        evaluations.append(evaluation)

    counts = {"exception-granted": 0, "grounding-required": 0}
    for evaluation in evaluations:
        counts[evaluation["disposition"]] += 1
    driver_counts = {}
    for evaluation in evaluations:
        for name in evaluation["failed_criteria"]:
            driver_counts[name] = driver_counts.get(name, 0) + 1
    worst = max(evaluations, key=lambda e: e["stored_energy_j"])
    return {
        "evaluations": evaluations,
        "counts": counts,
        "failure_drivers": driver_counts,
        "highest_energy_id": worst["id"],
        "highest_energy_j": worst["stored_energy_j"],
        "grounding_required": sorted(
            e["id"] for e in evaluations if e["disposition"] == "grounding-required"
        ),
        "compliant": counts["grounding-required"] == 0,
    }
