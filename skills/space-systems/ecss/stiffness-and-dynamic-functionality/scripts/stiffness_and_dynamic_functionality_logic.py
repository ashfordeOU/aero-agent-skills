#!/usr/bin/env python3
"""ECSS-E-ST-32C clauses 4.3.5-4.3.6 stiffness, alignment stability,
and dynamic-behaviour (frequency separation) assessment
(paraphrase, not copy).

Common-knowledge summary (standards-map.yaml, ecss: gated false): the
structures standard's stiffness and dynamic clauses require that each
structural axis meets a minimum fundamental natural frequency derived
from the launch-vehicle interface specification; that the separation
between structural mode frequencies and excitation frequencies (rotating
equipment, control system, launch environment) satisfies a required
fractional margin; that the retained modes in the finite-element model
account for a minimum fraction of translational modal effective mass in
each direction so that the model adequately represents the dynamic
response; and that alignment drift at sensitive interfaces under the
combined thermal and mechanical in-orbit environment remains within the
pointing or performance budget. This module implements the four
deterministic checks: fundamental frequency per axis, fractional
frequency separation margin, modal effective mass fraction, and
alignment stability. It does not define the launcher interface
requirements, the finite-element modelling procedure, or the thermal
model that generates the load inputs.
"""

VALID_AXIS_TYPES = frozenset({"axial", "lateral", "rotational"})
VALID_DIRECTIONS = frozenset({"x", "y", "z"})

DEFAULT_REQUIRED_MODAL_MASS_FRACTION = 0.90


def check_fundamental_frequency(axis, fundamental_freq_hz, minimum_required_hz):
    """Violation list for the fundamental natural frequency on one structural axis.

    axis: one of VALID_AXIS_TYPES ("axial", "lateral", "rotational").
    fundamental_freq_hz: predicted or measured fundamental natural frequency (Hz).
    minimum_required_hz: the minimum allowable frequency from the launch-vehicle
    interface or the system structural requirement (Hz).

    Returns a list with one violation dict when the frequency falls below the
    minimum, or an empty list when the requirement is met.
    Raises ValueError for an unrecognized axis or a non-positive frequency value.
    """
    if axis not in VALID_AXIS_TYPES:
        raise ValueError(
            "unrecognized axis %r under E-ST-32C clause 4.3.5; "
            "expected one of %s" % (axis, sorted(VALID_AXIS_TYPES))
        )
    if fundamental_freq_hz <= 0:
        raise ValueError(
            "fundamental_freq_hz must be > 0, got %r" % (fundamental_freq_hz,)
        )
    if minimum_required_hz <= 0:
        raise ValueError(
            "minimum_required_hz must be > 0, got %r" % (minimum_required_hz,)
        )
    if fundamental_freq_hz < minimum_required_hz:
        return [
            {
                "issue": "fundamental_frequency_below_minimum",
                "axis": axis,
                "fundamental_freq_hz": fundamental_freq_hz,
                "minimum_required_hz": minimum_required_hz,
                "shortfall_hz": minimum_required_hz - fundamental_freq_hz,
            }
        ]
    return []


def compute_frequency_separation_margin(structure_freq_hz, excitation_freq_hz):
    """Fractional separation between a structural mode frequency and an excitation
    frequency: (f_structure - f_excitation) / f_excitation.

    A positive value means the structural frequency is above the excitation.
    A negative value means the structural frequency is below the excitation.
    Either sign can be problematic depending on the margin convention; the
    caller supplies the required_margin and interprets the sign.
    Raises ValueError if either frequency is <= 0.
    """
    if structure_freq_hz <= 0:
        raise ValueError(
            "structure_freq_hz must be > 0, got %r" % (structure_freq_hz,)
        )
    if excitation_freq_hz <= 0:
        raise ValueError(
            "excitation_freq_hz must be > 0, got %r" % (excitation_freq_hz,)
        )
    return (structure_freq_hz - excitation_freq_hz) / excitation_freq_hz


def check_frequency_separation(
    mode_id, structure_freq_hz, excitation_freq_hz, required_margin
):
    """Violation list for one structural mode vs. one excitation frequency.

    mode_id: identifier for the structural mode being checked.
    structure_freq_hz: frequency of the structural mode (Hz).
    excitation_freq_hz: frequency of the excitation source (Hz).
    required_margin: minimum acceptable fractional separation (dimensionless,
    non-negative). The check is a simple threshold on the computed margin;
    the sign convention follows compute_frequency_separation_margin.

    Returns a list with one violation dict when the margin is insufficient,
    or an empty list when the margin is met.
    Raises ValueError for non-positive frequencies or a negative required_margin.
    """
    if required_margin < 0:
        raise ValueError(
            "required_margin must be >= 0, got %r" % (required_margin,)
        )
    margin = compute_frequency_separation_margin(structure_freq_hz, excitation_freq_hz)
    if margin < required_margin:
        return [
            {
                "issue": "insufficient_frequency_separation",
                "mode_id": mode_id,
                "structure_freq_hz": structure_freq_hz,
                "excitation_freq_hz": excitation_freq_hz,
                "computed_margin": margin,
                "required_margin": required_margin,
            }
        ]
    return []


def check_modal_mass_fraction(
    direction,
    effective_mass_fraction,
    required_fraction=DEFAULT_REQUIRED_MODAL_MASS_FRACTION,
):
    """Violation list for modal effective mass coverage in one direction.

    direction: one of VALID_DIRECTIONS ("x", "y", "z").
    effective_mass_fraction: fraction of total translational effective mass
    captured by the retained modes in this direction (0.0 to 1.0).
    required_fraction: minimum acceptable coverage fraction (default 0.90).

    A shortfall means the modal model is not complete enough to represent the
    dynamic response in this direction; additional modes must be retained.
    Returns a list with one violation dict on shortfall, or an empty list.
    Raises ValueError for direction outside VALID_DIRECTIONS, fractions outside
    their valid ranges.
    """
    if direction not in VALID_DIRECTIONS:
        raise ValueError(
            "unrecognized direction %r; expected one of %s"
            % (direction, sorted(VALID_DIRECTIONS))
        )
    if not (0.0 <= effective_mass_fraction <= 1.0):
        raise ValueError(
            "effective_mass_fraction must be in [0, 1], got %r"
            % (effective_mass_fraction,)
        )
    if not (0.0 < required_fraction <= 1.0):
        raise ValueError(
            "required_fraction must be in (0, 1], got %r" % (required_fraction,)
        )
    if effective_mass_fraction < required_fraction:
        return [
            {
                "issue": "insufficient_modal_mass_fraction",
                "direction": direction,
                "effective_mass_fraction": effective_mass_fraction,
                "required_fraction": required_fraction,
                "shortfall": required_fraction - effective_mass_fraction,
            }
        ]
    return []


def check_alignment_stability(component_id, alignment_error_arcsec, allowable_arcsec):
    """Violation list for alignment stability at one structural interface.

    component_id: identifier for the alignment-critical component or interface.
    alignment_error_arcsec: predicted alignment drift under the combined
    thermal and mechanical in-orbit load environment (arc-seconds).
    allowable_arcsec: maximum allowable drift derived from the pointing or
    performance budget (arc-seconds, must be > 0).

    Returns a list with one violation dict when the drift exceeds the allowable,
    or an empty list when within tolerance.
    Raises ValueError for a negative alignment_error or a non-positive allowable.
    """
    if alignment_error_arcsec < 0:
        raise ValueError(
            "alignment_error_arcsec must be >= 0, got %r" % (alignment_error_arcsec,)
        )
    if allowable_arcsec <= 0:
        raise ValueError(
            "allowable_arcsec must be > 0, got %r" % (allowable_arcsec,)
        )
    if alignment_error_arcsec > allowable_arcsec:
        return [
            {
                "issue": "alignment_stability_exceeded",
                "component_id": component_id,
                "alignment_error_arcsec": alignment_error_arcsec,
                "allowable_arcsec": allowable_arcsec,
                "excess_arcsec": alignment_error_arcsec - allowable_arcsec,
            }
        ]
    return []


def stiffness_dynamic_review(assessment):
    """Full ECSS-E-ST-32C clauses 4.3.5-4.3.6 stiffness and dynamic assessment.

    assessment: {
        "structure_id": str,
        "fundamental_frequencies": [
            {"axis": str, "freq_hz": float, "minimum_hz": float}, ...
        ],
        "frequency_separation_checks": [
            {
                "mode_id": str,
                "structure_freq_hz": float,
                "excitation_freq_hz": float,
                "required_margin": float,
            }, ...
        ],
        "modal_mass_fractions": [
            {
                "direction": str,
                "fraction": float,
                "required_fraction": float,   # optional, default 0.90
            }, ...
        ],
        "alignment_checks": [
            {
                "component_id": str,
                "error_arcsec": float,
                "allowable_arcsec": float,
            }, ...
        ],
    }

    Returns {
        "fundamental_frequency": [...],
        "frequency_separation": [...],
        "modal_mass": [...],
        "alignment": [...],
    }
    Each list contains violation dicts (empty list means compliant for that
    category). Raises ValueError for any invalid input.
    """
    ff_violations = []
    for entry in assessment.get("fundamental_frequencies", []):
        ff_violations.extend(
            check_fundamental_frequency(entry["axis"], entry["freq_hz"], entry["minimum_hz"])
        )

    fs_violations = []
    for entry in assessment.get("frequency_separation_checks", []):
        fs_violations.extend(
            check_frequency_separation(
                entry["mode_id"],
                entry["structure_freq_hz"],
                entry["excitation_freq_hz"],
                entry["required_margin"],
            )
        )

    mm_violations = []
    for entry in assessment.get("modal_mass_fractions", []):
        mm_violations.extend(
            check_modal_mass_fraction(
                entry["direction"],
                entry["fraction"],
                entry.get("required_fraction", DEFAULT_REQUIRED_MODAL_MASS_FRACTION),
            )
        )

    align_violations = []
    for entry in assessment.get("alignment_checks", []):
        align_violations.extend(
            check_alignment_stability(
                entry["component_id"],
                entry["error_arcsec"],
                entry["allowable_arcsec"],
            )
        )

    return {
        "fundamental_frequency": ff_violations,
        "frequency_separation": fs_violations,
        "modal_mass": mm_violations,
        "alignment": align_violations,
    }


def is_stiffness_dynamic_compliant(review):
    """True when all violation categories in a stiffness_dynamic_review result are
    empty -- the structure satisfies clauses 4.3.5-4.3.6 for this assessment."""
    return all(len(violations) == 0 for violations in review.values())
