#!/usr/bin/env python3
"""ECSS-E-ST-32C clause 4.6.2.10 buckling onset analysis verification
with HB-32-24 knockdown factor interplay (paraphrase, not copy).

Common-knowledge summary (standards-map.yaml, ecss: gated false): the
ECSS structures standard's buckling clause requires that classical
theoretical buckling loads be reduced by empirically derived knockdown
factors before comparison to applied loads. Knockdown factors account for
geometric imperfections, boundary-condition uncertainties, and load-
introduction effects that cause real structures to buckle below the
classical prediction. Different structural forms carry distinct knockdown
factor ranges: flat plates and stiffened panels (plate mode), cylindrical
and conical shells (shell mode, most imperfection-sensitive), slender
axially loaded members (column mode), and thin-walled open sections
experiencing local flange or web buckling (crippling mode). HB-32-24
provides empirical data and certified correlations for each mode. The
reserve factor -- critical load divided by the product of the applied
load and the factor of safety -- must be at least 1.0 for compliance.
This module implements geometry categorization, knockdown factor bounding
and validation, critical load computation, reserve factor calculation,
and per-component violation aggregation; it does not define the specific
test-correlated knockdown factor values that the analyst selects from
HB-32-24, nor the classical theoretical buckling load derivations.
"""

BUCKLING_MODES = frozenset({"plate", "shell", "column", "crippling"})

GEOMETRY_TO_MODE = {
    "flat_plate": "plate",
    "stiffened_panel": "plate",
    "cylindrical_shell": "shell",
    "conical_shell": "shell",
    "column": "column",
    "beam_column": "column",
    "angle_section": "crippling",
    "channel_section": "crippling",
    "z_section": "crippling",
    "hat_section": "crippling",
}

# HB-32-24 common-knowledge knockdown factor bounds: (lower_bound, upper_bound).
# Shells are most sensitive to imperfections and carry the widest range.
# All factors are physically bounded by (0, 1].
KNOCKDOWN_BOUNDS = {
    "plate": (0.5, 1.0),
    "shell": (0.1, 1.0),
    "column": (0.5, 1.0),
    "crippling": (0.3, 1.0),
}

MINIMUM_RESERVE_FACTOR = 1.0


def categorize_geometry(geometry_type):
    """Buckling mode for a structural geometry type: one of 'plate',
    'shell', 'column', or 'crippling'. Raises ValueError for an
    unrecognized geometry type."""
    if geometry_type not in GEOMETRY_TO_MODE:
        raise ValueError(
            "unrecognized geometry type %r under "
            "E-ST-32C clause 4.6.2.10" % (geometry_type,)
        )
    return GEOMETRY_TO_MODE[geometry_type]


def knockdown_factor_bounds(buckling_mode):
    """(lower_bound, upper_bound) knockdown factor range for a buckling
    mode per HB-32-24 common-knowledge bounds. Raises ValueError for an
    unrecognized mode."""
    if buckling_mode not in KNOCKDOWN_BOUNDS:
        raise ValueError(
            "unrecognized buckling mode %r" % (buckling_mode,)
        )
    return KNOCKDOWN_BOUNDS[buckling_mode]


def validate_knockdown_factor(knockdown_factor, buckling_mode):
    """True when knockdown_factor lies within the HB-32-24 bounds for the
    given mode. Raises ValueError when the factor is outside (0, 1], below
    the mode's lower bound, or the mode is unrecognized."""
    if knockdown_factor <= 0 or knockdown_factor > 1.0:
        raise ValueError(
            "knockdown_factor must be in (0, 1]: got %r" % (knockdown_factor,)
        )
    lo, _hi = knockdown_factor_bounds(buckling_mode)
    if knockdown_factor < lo:
        raise ValueError(
            "knockdown_factor %r is below the HB-32-24 lower bound %.1f "
            "for mode %r -- additional test correlation required"
            % (knockdown_factor, lo, buckling_mode)
        )
    return True


def critical_buckling_load(classical_load_n, knockdown_factor):
    """Critical buckling load (N): classical_load_n multiplied by
    knockdown_factor. Raises ValueError for a non-positive classical load
    or a knockdown factor outside (0, 1]."""
    if classical_load_n <= 0:
        raise ValueError(
            "classical_load_n must be > 0: got %r" % (classical_load_n,)
        )
    if knockdown_factor <= 0 or knockdown_factor > 1.0:
        raise ValueError(
            "knockdown_factor must be in (0, 1]: got %r" % (knockdown_factor,)
        )
    return classical_load_n * knockdown_factor


def reserve_factor(critical_load_n, applied_load_n, factor_of_safety):
    """Reserve factor for buckling onset: critical_load_n divided by
    (applied_load_n * factor_of_safety). Raises ValueError for non-positive
    loads or a factor of safety below 1.0."""
    if critical_load_n <= 0:
        raise ValueError("critical_load_n must be > 0: got %r" % (critical_load_n,))
    if applied_load_n <= 0:
        raise ValueError("applied_load_n must be > 0: got %r" % (applied_load_n,))
    if factor_of_safety < 1.0:
        raise ValueError(
            "factor_of_safety must be >= 1.0: got %r" % (factor_of_safety,)
        )
    return critical_load_n / (applied_load_n * factor_of_safety)


def buckling_status(rf_value):
    """'adequate' when the reserve factor meets or exceeds the minimum
    threshold (1.0); 'margin_deficient' when it does not."""
    if rf_value >= MINIMUM_RESERVE_FACTOR:
        return "adequate"
    return "margin_deficient"


def buckling_component_review(component):
    """Full clause 4.6.2.10 buckling review for one structural component.

    component: {
        "component_id": str,
        "geometry_type": str,
        "classical_load_n": float,   -- classical theoretical buckling load (N)
        "knockdown_factor": float,   -- analyst-selected factor in (0, 1]
        "applied_load_n": float,     -- design applied compressive load (N)
        "factor_of_safety": float,   -- >= 1.0
    }
    Returns {
        "component_id": str,
        "buckling_mode": str,
        "critical_load_n": float,
        "reserve_factor": float,
        "status": str,
        "violations": list[dict],
    }.
    Raises ValueError for an unrecognized geometry type or physically
    inadmissible inputs. Does not mutate component.
    """
    component_id = component["component_id"]
    geometry_type = component["geometry_type"]
    classical_load_n = component["classical_load_n"]
    kdf = component["knockdown_factor"]
    applied_load_n = component["applied_load_n"]
    fos = component["factor_of_safety"]

    violations = []

    buckling_mode = categorize_geometry(geometry_type)

    try:
        validate_knockdown_factor(kdf, buckling_mode)
    except ValueError as exc:
        violations.append({
            "issue": "knockdown_factor_out_of_bounds",
            "component": component_id,
            "detail": str(exc),
        })

    crit_load = critical_buckling_load(classical_load_n, kdf)
    rf = reserve_factor(crit_load, applied_load_n, fos)
    status = buckling_status(rf)

    if status == "margin_deficient":
        violations.append({
            "issue": "buckling_margin_deficient",
            "component": component_id,
            "reserve_factor": rf,
        })

    return {
        "component_id": component_id,
        "buckling_mode": buckling_mode,
        "critical_load_n": crit_load,
        "reserve_factor": rf,
        "status": status,
        "violations": violations,
    }


def is_buckling_compliant(review):
    """True when the component review has no violations -- all knockdown
    factor bounds are satisfied and the reserve factor is adequate."""
    return len(review["violations"]) == 0
