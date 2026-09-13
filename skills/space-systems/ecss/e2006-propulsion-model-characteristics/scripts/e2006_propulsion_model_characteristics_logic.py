#!/usr/bin/env python3
"""Propulsion model characteristics - ECSS-E-ST-20-06C clause 11.3.2.

Deterministic, offline, stdlib-only audit of the model declaration behind a
spacecraft/electric-propulsion interaction simulation: categorize every
declared element into its family, list the required elements nothing covers,
check the mesh cell-size against the Debye-length of the declared plasma,
reconcile the declared beam-current with the declared thrust and
beam-voltage, sum the grounding return-path resistance against its limit and
check that the structure potential is free to float.

Standard is cited as an anchor only; no normative text is reproduced.
"""

import math

VACUUM_PERMITTIVITY_F_PER_M = 8.8541878128e-12
ELEMENTARY_CHARGE_C = 1.602176634e-19
ATOMIC_MASS_UNIT_KG = 1.66053906660e-27

# Every recognized model element and the family it belongs to.
MODEL_ELEMENTS = {
    "spacecraft-outer-envelope": "outer-geometry",
    "solar-array-panel-geometry": "outer-geometry",
    "thruster-location-and-orientation": "outer-geometry",
    "sensitive-surface-geometry": "outer-geometry",
    "appendage-boom-geometry": "outer-geometry",
    "beam-ion-energy-distribution": "thruster-source",
    "beam-current-and-divergence": "thruster-source",
    "neutral-efflux-source": "thruster-source",
    "charge-exchange-ion-source": "thruster-source",
    "neutralizer-electron-source": "thruster-source",
    "solar-array-string-voltage-distribution": "power-subsystem",
    "exposed-conductor-inventory": "power-subsystem",
    "biased-surface-potentials": "power-subsystem",
    "harness-routing": "power-subsystem",
    "structure-ground-reference": "grounding-reference",
    "grounding-return-path-resistance": "grounding-reference",
    "neutralizer-coupling-to-plasma": "grounding-reference",
    "floating-potential-boundary-condition": "grounding-reference",
}

# Elements the clause enumerates as required, per family. Recognized elements
# absent from this table are optional (booms, harness routing, ...).
REQUIRED_ELEMENTS = {
    "outer-geometry": (
        "spacecraft-outer-envelope",
        "solar-array-panel-geometry",
        "thruster-location-and-orientation",
        "sensitive-surface-geometry",
    ),
    "thruster-source": (
        "beam-ion-energy-distribution",
        "beam-current-and-divergence",
        "neutral-efflux-source",
        "charge-exchange-ion-source",
        "neutralizer-electron-source",
    ),
    "power-subsystem": (
        "solar-array-string-voltage-distribution",
        "exposed-conductor-inventory",
        "biased-surface-potentials",
    ),
    "grounding-reference": (
        "structure-ground-reference",
        "grounding-return-path-resistance",
        "neutralizer-coupling-to-plasma",
        "floating-potential-boundary-condition",
    ),
}

# Potential boundary conditions a declaration may state.
POTENTIAL_BOUNDARY_CONDITIONS = {
    "floating": True,
    "clamped-to-chamber-wall": False,
    "fixed-at-zero": False,
}

DEFAULT_CELLS_PER_DEBYE = 1.0
DEFAULT_BEAM_CURRENT_REL_TOL = 0.05

# Named tolerance that absorbs floating-point representation error on an
# exact-boundary comparison. It never widens an engineering limit.
BOUNDARY_REL_TOL = 1.0e-9


def _not_above(value, limit):
    """True when value is at or below limit, absorbing representation error."""
    return value <= limit or math.isclose(value, limit, rel_tol=BOUNDARY_REL_TOL)


def categorize_model_element(element_id):
    """Return the model family of a declared element identifier."""
    if not isinstance(element_id, str) or not element_id.strip():
        raise ValueError("element_id must be a non-empty string")
    key = element_id.strip().lower()
    if key not in MODEL_ELEMENTS:
        raise ValueError(
            "uncategorized model element %r; expected one of %s"
            % (element_id, sorted(MODEL_ELEMENTS))
        )
    return MODEL_ELEMENTS[key]


def element_is_required(element_id):
    """True when the element is one the clause enumerates as required."""
    family = categorize_model_element(element_id)
    return element_id.strip().lower() in REQUIRED_ELEMENTS[family]


def missing_model_elements(declared_elements):
    """Required elements, per family, that no declaration covers."""
    if not isinstance(declared_elements, (list, tuple)):
        raise ValueError("declared_elements must be a list of element identifiers")
    covered = set()
    for element in declared_elements:
        categorize_model_element(element)
        covered.add(element.strip().lower())
    missing = {}
    for family, required in REQUIRED_ELEMENTS.items():
        gap = [item for item in required if item not in covered]
        if gap:
            missing[family] = sorted(gap)
    return missing


def debye_length(plasma_density_m3, electron_temperature_ev):
    """Electron Debye length [m] of the declared plasma."""
    if plasma_density_m3 is None or plasma_density_m3 <= 0.0:
        raise ValueError("plasma_density_m3 must be > 0")
    if electron_temperature_ev is None or electron_temperature_ev <= 0.0:
        raise ValueError("electron_temperature_ev must be > 0")
    numerator = (
        VACUUM_PERMITTIVITY_F_PER_M
        * electron_temperature_ev
        * ELEMENTARY_CHARGE_C
    )
    denominator = plasma_density_m3 * ELEMENTARY_CHARGE_C ** 2
    return math.sqrt(numerator / denominator)


def mesh_resolution(
    cell_size_m,
    plasma_density_m3,
    electron_temperature_ev,
    cells_per_debye=DEFAULT_CELLS_PER_DEBYE,
):
    """Check the mesh cell-size against the Debye-length of the plasma."""
    if cell_size_m is None or cell_size_m <= 0.0:
        raise ValueError("cell_size_m must be > 0")
    if cells_per_debye is None or cells_per_debye <= 0.0:
        raise ValueError("cells_per_debye must be > 0")
    length = debye_length(plasma_density_m3, electron_temperature_ev)
    limit = length / cells_per_debye
    return {
        "debye_length_m": length,
        "cell_size_limit_m": limit,
        "cell_size_m": cell_size_m,
        "debye_resolved": _not_above(cell_size_m, limit),
        "cells_per_debye_achieved": length / cell_size_m,
    }


def beam_current_from_thrust(thrust_n, beam_voltage_v, ion_mass_amu):
    """Beam current [A] implied by a thrust at a beam voltage."""
    if thrust_n is None or thrust_n <= 0.0:
        raise ValueError("thrust_n must be > 0")
    if beam_voltage_v is None or beam_voltage_v <= 0.0:
        raise ValueError("beam_voltage_v must be > 0")
    if ion_mass_amu is None or ion_mass_amu <= 0.0:
        raise ValueError("ion_mass_amu must be > 0")
    ion_mass = ion_mass_amu * ATOMIC_MASS_UNIT_KG
    exhaust_speed = math.sqrt(
        2.0 * ELEMENTARY_CHARGE_C * beam_voltage_v / ion_mass
    )
    return thrust_n * ELEMENTARY_CHARGE_C / (ion_mass * exhaust_speed)


def beam_current_consistency(
    declared_current_a,
    thrust_n,
    beam_voltage_v,
    ion_mass_amu,
    relative_tolerance=DEFAULT_BEAM_CURRENT_REL_TOL,
):
    """Compare a declared beam current with the one the thrust implies."""
    if declared_current_a is None or declared_current_a <= 0.0:
        raise ValueError("declared_current_a must be > 0")
    if relative_tolerance is None or relative_tolerance < 0.0:
        raise ValueError("relative_tolerance must be >= 0")
    expected = beam_current_from_thrust(thrust_n, beam_voltage_v, ion_mass_amu)
    error = abs(declared_current_a - expected) / expected
    return {
        "expected_current_a": expected,
        "declared_current_a": declared_current_a,
        "relative_error": error,
        "consistent": _not_above(error, relative_tolerance),
    }


def grounding_return_resistance(segments):
    """Total series resistance [ohm] of the grounding return path."""
    if not isinstance(segments, (list, tuple)) or not segments:
        raise ValueError("segments must be a non-empty list")
    total = 0.0
    for segment in segments:
        if not isinstance(segment, dict):
            raise ValueError("every grounding segment must be a mapping")
        value = segment.get("resistance_ohm")
        if (
            value is None
            or not isinstance(value, (int, float))
            or isinstance(value, bool)
            or value < 0.0
        ):
            raise ValueError(
                "segment %r needs a non-negative resistance_ohm"
                % (segment.get("id"),)
            )
        total += float(value)
    return total


def grounding_path_within_limit(total_resistance_ohm, limit_ohm):
    """True when the summed return-path resistance is at or below its limit."""
    if total_resistance_ohm is None or total_resistance_ohm < 0.0:
        raise ValueError("total_resistance_ohm must be >= 0")
    if limit_ohm is None or limit_ohm <= 0.0:
        raise ValueError("limit_ohm must be > 0")
    return _not_above(total_resistance_ohm, limit_ohm)


def potential_reference_floats(boundary_condition):
    """True when the declared structure potential reference is free to float."""
    if not isinstance(boundary_condition, str) or not boundary_condition.strip():
        raise ValueError("boundary_condition must be a non-empty string")
    key = boundary_condition.strip().lower()
    if key not in POTENTIAL_BOUNDARY_CONDITIONS:
        raise ValueError(
            "unrecognized potential boundary condition %r; expected one of %s"
            % (boundary_condition, sorted(POTENTIAL_BOUNDARY_CONDITIONS))
        )
    return POTENTIAL_BOUNDARY_CONDITIONS[key]


def assess_propulsion_model(model):
    """Aggregate clause 11.3.2 audit of one interaction-simulation model."""
    if not isinstance(model, dict):
        raise ValueError("model must be a mapping")
    elements = model.get("elements")
    if not isinstance(elements, (list, tuple)) or not elements:
        raise ValueError("model must declare a non-empty 'elements' list")
    seen = set()
    for element in elements:
        categorize_model_element(element)
        key = element.strip().lower()
        if key in seen:
            raise ValueError("duplicate model element %r" % (element,))
        seen.add(key)
    findings = []
    missing = missing_model_elements(elements)
    for family in sorted(missing):
        findings.append(
            "family %s is missing required elements: %s"
            % (family, ", ".join(missing[family]))
        )
    mesh = mesh_resolution(
        model.get("cell_size_m"),
        model.get("plasma_density_m3"),
        model.get("electron_temperature_ev"),
        model.get("cells_per_debye", DEFAULT_CELLS_PER_DEBYE),
    )
    if not mesh["debye_resolved"]:
        findings.append(
            "mesh cell-size %.4e m exceeds the Debye-length limit %.4e m"
            % (mesh["cell_size_m"], mesh["cell_size_limit_m"])
        )
    beam = beam_current_consistency(
        model.get("declared_beam_current_a"),
        model.get("thrust_n"),
        model.get("beam_voltage_v"),
        model.get("ion_mass_amu"),
        model.get("beam_current_rel_tol", DEFAULT_BEAM_CURRENT_REL_TOL),
    )
    if not beam["consistent"]:
        findings.append(
            "declared beam-current %.4f A differs from the thrust-implied "
            "%.4f A by %.1f%%"
            % (
                beam["declared_current_a"],
                beam["expected_current_a"],
                100.0 * beam["relative_error"],
            )
        )
    resistance = grounding_return_resistance(model.get("grounding_segments"))
    limit = model.get("max_grounding_resistance_ohm")
    within = grounding_path_within_limit(resistance, limit)
    if not within:
        findings.append(
            "grounding return-path resistance %.4f ohm exceeds the limit "
            "%.4f ohm" % (resistance, limit)
        )
    floats = potential_reference_floats(
        model.get("potential_boundary_condition", "floating")
    )
    if not floats:
        findings.append(
            "structure potential is %s, so the model cannot reproduce a "
            "free-flying reference"
            % model.get("potential_boundary_condition")
        )
    return {
        "families_declared": sorted({categorize_model_element(e) for e in elements}),
        "missing_elements": missing,
        "mesh": mesh,
        "beam_current": beam,
        "grounding_resistance_ohm": resistance,
        "grounding_within_limit": within,
        "potential_reference_floats": floats,
        "findings": findings,
        "representative": not findings,
    }
