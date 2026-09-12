#!/usr/bin/env python3
"""ECSS-E-ST-32C clause 4.6.3 COSPE with homogeneous non-metallic liner
(paraphrase, not copy).

Common-knowledge summary (standards-map.yaml, ecss: gated false): the
ECSS structures standard clause 4.6.3 addresses composite overwrapped
pressure vessels whose liner is a homogeneous non-metallic material; the
liner carries the leak-tight pressure boundary while the composite overwrap
provides the structural load path; structural compliance requires the proof
pressure factor, effective burst pressure factor (after applying an
environmental degradation multiplier), liner strain at proof relative to the
liner allowable strain, and overwrap fiber volume fraction to each meet their
respective bounds. This module implements liner material categorization,
proof and burst factor checks, liner strain compatibility, fiber volume
fraction validation, and the aggregated compliance verdict; it does not
define test schedules, fracture mechanics crack-growth models, or
joint-efficiency calculations.
"""

# Recognized homogeneous non-metallic liner material families per
# ECSS-E-ST-32C clause 4.6.3.
NONMETALLIC_LINER_TYPES = frozenset(
    {"polymer", "elastomer", "thermoplastic", "thermoset", "fluoropolymer"}
)

# Minimum structural margin factors derived from ECSS structural design
# practice (ECSS-E-ST-32C common knowledge).
MIN_PROOF_FACTOR = 1.1   # proof_pressure / MAWP
MIN_BURST_FACTOR = 1.5   # (burst_pressure * degradation_factor) / MAWP

# Overwrap fiber volume fraction bounds; values outside this range indicate
# either fiber starvation (low) or resin starvation and elevated void content
# (high).
MIN_FIBER_VOLUME_FRACTION = 0.50
MAX_FIBER_VOLUME_FRACTION = 0.70


def categorize_liner_type(liner_material):
    """Material family for a liner type: always "nonmetallic" for a
    recognized entry. Raises ValueError for a liner material outside
    the known set."""
    if liner_material in NONMETALLIC_LINER_TYPES:
        return "nonmetallic"
    raise ValueError(
        "unrecognized non-metallic liner material %r under "
        "ECSS-E-ST-32C clause 4.6.3; recognized types: %s"
        % (liner_material, sorted(NONMETALLIC_LINER_TYPES))
    )


def check_proof_factor(proof_pressure, mawp):
    """Violation list (empty if compliant) for the proof pressure factor
    check. proof_pressure and mawp are scalar pressure values in
    consistent units. Raises ValueError for a non-positive MAWP."""
    if mawp <= 0:
        raise ValueError("mawp must be > 0; got %r" % (mawp,))
    factor = proof_pressure / mawp
    if factor < MIN_PROOF_FACTOR:
        return [
            {
                "issue": "proof_factor_below_minimum",
                "proof_factor": factor,
                "min_proof_factor": MIN_PROOF_FACTOR,
            }
        ]
    return []


def check_burst_factor(burst_pressure, mawp, degradation_factor=1.0):
    """Violation list (empty if compliant) for the effective burst pressure
    factor check. The effective burst factor is
    (burst_pressure * degradation_factor) / mawp. Raises ValueError for a
    non-positive MAWP or a degradation_factor outside (0, 1.0]."""
    if mawp <= 0:
        raise ValueError("mawp must be > 0; got %r" % (mawp,))
    if not (0.0 < degradation_factor <= 1.0):
        raise ValueError(
            "degradation_factor must be in (0, 1.0]; got %r" % (degradation_factor,)
        )
    effective_factor = (burst_pressure * degradation_factor) / mawp
    if effective_factor < MIN_BURST_FACTOR:
        return [
            {
                "issue": "burst_factor_below_minimum",
                "effective_burst_factor": effective_factor,
                "min_burst_factor": MIN_BURST_FACTOR,
                "degradation_factor": degradation_factor,
            }
        ]
    return []


def check_liner_strain(liner_strain_at_proof, liner_allowable_strain):
    """Violation list (empty if compliant) for liner strain compatibility.
    liner_strain_at_proof must not exceed liner_allowable_strain."""
    if liner_strain_at_proof > liner_allowable_strain:
        return [
            {
                "issue": "liner_strain_exceeds_allowable",
                "liner_strain_at_proof": liner_strain_at_proof,
                "liner_allowable_strain": liner_allowable_strain,
            }
        ]
    return []


def check_fiber_volume_fraction(fvf):
    """Violation list (empty if compliant) for the overwrap fiber volume
    fraction. Values below MIN_FIBER_VOLUME_FRACTION and above
    MAX_FIBER_VOLUME_FRACTION are each flagged independently."""
    violations = []
    if fvf < MIN_FIBER_VOLUME_FRACTION:
        violations.append(
            {
                "issue": "fiber_volume_fraction_below_minimum",
                "fvf": fvf,
                "min_fvf": MIN_FIBER_VOLUME_FRACTION,
            }
        )
    if fvf > MAX_FIBER_VOLUME_FRACTION:
        violations.append(
            {
                "issue": "fiber_volume_fraction_above_maximum",
                "fvf": fvf,
                "max_fvf": MAX_FIBER_VOLUME_FRACTION,
            }
        )
    return violations


def cospe_nonmetallic_liner_assessment(vessel):
    """Full ECSS-E-ST-32C clause 4.6.3 structural assessment for one
    COSPE vessel with a homogeneous non-metallic liner.

    vessel: {
        "liner_material":           str,    -- must be in NONMETALLIC_LINER_TYPES
        "proof_pressure":           float,  -- in consistent pressure units
        "burst_pressure":           float,
        "mawp":                     float,  -- maximum allowable working pressure
        "liner_strain_at_proof":    float,  -- strain at proof pressure
        "liner_allowable_strain":   float,  -- liner's allowable strain limit
        "fiber_volume_fraction":    float,  -- overwrap FVF (0–1)
        "degradation_factor":       float,  -- optional, default 1.0; (0, 1.0]
    }

    Returns {"violations": [...]}, where each entry is a dict with at
    least an "issue" key. Returns an empty list when all checks pass.
    Raises ValueError for unrecognized liner material or invalid inputs.
    Does not mutate the vessel dict.
    """
    categorize_liner_type(vessel["liner_material"])  # raises if unrecognized

    mawp = vessel["mawp"]
    degradation_factor = vessel.get("degradation_factor", 1.0)

    violations = []
    violations += check_proof_factor(vessel["proof_pressure"], mawp)
    violations += check_burst_factor(vessel["burst_pressure"], mawp, degradation_factor)
    violations += check_liner_strain(
        vessel["liner_strain_at_proof"],
        vessel["liner_allowable_strain"],
    )
    violations += check_fiber_volume_fraction(vessel["fiber_volume_fraction"])

    return {"violations": violations}


def is_cospe_compliant(assessment):
    """True when the cospe_nonmetallic_liner_assessment result contains no
    violations — the vessel satisfies clause 4.6.3 for this assessment."""
    return len(assessment["violations"]) == 0
